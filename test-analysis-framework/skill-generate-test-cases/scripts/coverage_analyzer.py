#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check test-point coverage against the shared test-case JSON contract."""

from dataclasses import dataclass
from datetime import datetime
import argparse
import glob
import json
import re
from pathlib import Path
from typing import Dict, List


@dataclass
class CoverageStats:
    total_test_points: int
    covered_test_points: int
    coverage_rate: float
    total_test_cases: int
    invalid_cases: List[str]
    duplicate_case_ids: List[str]
    priority_distribution: Dict[str, int]
    method_distribution: Dict[str, int]
    uncovered_points: List[str]


class CoverageAnalyzer:
    def __init__(self):
        self.test_points: List[dict] = []
        self.test_cases: List[dict] = []
        self.coverage_map: Dict[str, List[str]] = {}

    @staticmethod
    def _paths(value: str) -> List[Path]:
        matches = [Path(item) for item in glob.glob(value)]
        return matches or [Path(value)]

    @staticmethod
    def load_test_points_from_md(md_file: Path) -> List[dict]:
        content = md_file.read_text(encoding="utf-8")
        matches = re.findall(r"\x60\x60\x60json\s*\n(.*?)\n\x60\x60\x60", content, re.DOTALL)
        if not matches:
            raise ValueError(f"未在文件 {md_file} 中找到 JSON 数据块")
        data = json.loads(matches[-1])
        points = data.get("test_points", []) if isinstance(data, dict) else []
        if not isinstance(points, list):
            raise ValueError(f"文件 {md_file} 的 test_points 必须是数组")
        return points

    @staticmethod
    def load_test_cases_from_json(json_file: Path) -> List[dict]:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("test_cases", data.get("用例", []))
        if not isinstance(data, list):
            raise ValueError(f"文件 {json_file} 必须是用例数组或包含 test_cases 数组的对象")
        return data

    @staticmethod
    def _validate_case(case: object) -> str | None:
        if not isinstance(case, dict):
            return "用例必须是对象"
        required = ("用例ID", "用例标题", "测试点ID", "需求ID", "设计方法", "步骤")
        missing = [key for key in required if not case.get(key)]
        if missing:
            return f"缺少字段: {', '.join(missing)}"
        steps = case.get("步骤")
        if not isinstance(steps, list) or not steps:
            return "步骤必须是非空数组"
        for index, step in enumerate(steps, 1):
            if not isinstance(step, dict) or not str(step.get("操作", "")).strip() or not str(step.get("预期", step.get("预期结果", ""))).strip():
                return f"第 {index} 步缺少操作或预期"
        return None

    def analyze_coverage(self, testpoints_file: Path | str, testcases_file: Path | str) -> CoverageStats:
        self.test_points = []
        self.test_cases = []
        self.coverage_map = {}
        invalid_cases: List[str] = []
        duplicate_ids: List[str] = []

        point_paths = self._paths(str(testpoints_file))
        case_paths = self._paths(str(testcases_file))
        if not all(path.exists() and path.is_file() for path in point_paths):
            missing = [str(path) for path in point_paths if not path.exists()]
            raise FileNotFoundError(f"测试点文件不存在: {', '.join(missing)}")
        if not all(path.exists() and path.is_file() for path in case_paths):
            missing = [str(path) for path in case_paths if not path.exists()]
            raise FileNotFoundError(f"测试用例文件不存在: {', '.join(missing)}")

        for path in point_paths:
            self.test_points.extend(self.load_test_points_from_md(path))
        for path in case_paths:
            self.test_cases.extend(self.load_test_cases_from_json(path))

        seen_case_ids = set()
        valid_cases = []
        for index, case in enumerate(self.test_cases, 1):
            error = self._validate_case(case)
            case_id = str(case.get("用例ID", f"index-{index}")) if isinstance(case, dict) else f"index-{index}"
            if error:
                invalid_cases.append(f"{case_id}: {error}")
                continue
            if case_id in seen_case_ids:
                duplicate_ids.append(case_id)
                continue
            seen_case_ids.add(case_id)
            valid_cases.append(case)

        self.test_cases = valid_cases
        for case in valid_cases:
            point_id = str(case["测试点ID"]).strip()
            self.coverage_map.setdefault(point_id, []).append(str(case["用例ID"]).strip())

        point_ids = [str(point.get("id", "")).strip() for point in self.test_points]
        uncovered = [point_id for point_id in point_ids if point_id and point_id not in self.coverage_map]
        covered = len(point_ids) - len(uncovered)
        rate = round(covered / len(point_ids) * 100, 2) if point_ids else 0.0

        priorities: Dict[str, int] = {}
        methods: Dict[str, int] = {}
        for case in valid_cases:
            priority = str(case.get("优先级") or "Unknown")
            priorities[priority] = priorities.get(priority, 0) + 1
            method_values = case.get("设计方法", [])
            method_values = [method_values] if isinstance(method_values, str) else method_values
            for method in method_values:
                methods[str(method)] = methods.get(str(method), 0) + 1

        return CoverageStats(
            total_test_points=len(point_ids),
            covered_test_points=covered,
            coverage_rate=rate,
            total_test_cases=len(valid_cases),
            invalid_cases=invalid_cases,
            duplicate_case_ids=duplicate_ids,
            priority_distribution=priorities,
            method_distribution=methods,
            uncovered_points=uncovered,
        )

    def generate_report(self, stats: CoverageStats, output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        details = {}
        for point in self.test_points:
            point_id = str(point.get("id", "")).strip()
            details[point_id] = {
                "测试点标题": point.get("title", ""),
                "优先级": point.get("dimension_priority", ""),
                "已覆盖": point_id in self.coverage_map,
                "关联用例": self.coverage_map.get(point_id, []),
            }
        report = {
            "生成时间": datetime.now().isoformat(),
            "覆盖率统计": {
                "测试点总数": stats.total_test_points,
                "已覆盖测试点": stats.covered_test_points,
                "覆盖率": stats.coverage_rate,
                "测试用例总数": stats.total_test_cases,
                "无效用例数": len(stats.invalid_cases),
                "重复用例ID数": len(stats.duplicate_case_ids),
            },
            "优先级分布": stats.priority_distribution,
            "设计方法分布": stats.method_distribution,
            "未覆盖测试点": stats.uncovered_points,
            "无效用例": stats.invalid_cases,
            "重复用例ID": stats.duplicate_case_ids,
            "覆盖详情": details,
        }
        output_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已生成覆盖率报告: {output_file}")

    def print_summary(self, stats: CoverageStats) -> None:
        print("=" * 60)
        print("测试覆盖率分析")
        print(f"测试点: {stats.covered_test_points}/{stats.total_test_points} ({stats.coverage_rate}%)")
        print(f"有效用例: {stats.total_test_cases}")
        print(f"无效用例: {len(stats.invalid_cases)}，重复 ID: {len(stats.duplicate_case_ids)}")
        if stats.uncovered_points:
            print("未覆盖测试点: " + ", ".join(stats.uncovered_points[:10]))
        print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="分析测试点覆盖率")
    parser.add_argument("--testpoints", required=True, help="测试点 Markdown 文件或 glob")
    parser.add_argument("--testcases", required=True, help="测试用例 JSON 文件或 glob")
    parser.add_argument("--output", required=True, help="报告 JSON 路径")
    args = parser.parse_args()
    try:
        analyzer = CoverageAnalyzer()
        stats = analyzer.analyze_coverage(args.testpoints, args.testcases)
        analyzer.print_summary(stats)
        analyzer.generate_report(stats, Path(args.output))
        if stats.invalid_cases or stats.duplicate_case_ids or stats.coverage_rate < 100:
            print("覆盖率或用例质量未达标")
            return 1
        print("覆盖率达标")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"分析失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
