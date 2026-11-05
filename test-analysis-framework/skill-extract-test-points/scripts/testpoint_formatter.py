#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the shared test-point JSON into a reviewable Markdown report."""

import argparse
import json
from pathlib import Path


def load_points(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("test_points"), list):
        raise ValueError("输入必须是包含 test_points 数组的 JSON 对象")
    return data


def render(data: dict, template: Path | None = None) -> str:
    metadata = data.get("metadata", {})
    points = data["test_points"]
    lines = [f"# 测试点分析报告：{metadata.get('requirement_name', '未命名需求')}", "", "## 测试点矩阵", ""]
    lines.append("| ID | 标题 | 优先级 | 场景 | 需求来源 |")
    lines.append("|---|---|---|---|---|")
    for point in points:
        lines.append("| {id} | {title} | {priority} | {scenario} | {source} |".format(
            id=point.get("id", ""), title=point.get("title", "").replace("|", "\\|"),
            priority=point.get("dimension_priority", ""), scenario=point.get("dimension_scenario", ""),
            source=point.get("requirement_source", "").replace("|", "\\|")))
    lines.extend(["", "## 测试点数据（机器可读）", "", "```json", json.dumps(data, ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="格式化测试点 Markdown 报告")
    parser.add_argument("--input", required=True)
    parser.add_argument("--template", help="兼容旧命令；模板仅作为可选扩展点")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        data = load_points(Path(args.input))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(data, Path(args.template) if args.template else None), encoding="utf-8")
        print(f"已生成测试点报告: {output}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"格式化失败: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
