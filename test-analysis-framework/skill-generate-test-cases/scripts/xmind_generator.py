#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate an XMind 2.0 mind map from the project's test-case JSON contract."""

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring, indent


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _new_id(prefix: str = "topic") -> str:
    _new_id.counter += 1
    return f"{prefix}-{_new_id.counter}-{time.time_ns()}"
_new_id.counter = 0


def _make_topic(parent: Element, title: str, topic_id: str | None = None) -> Element:
    children = parent.find("children")
    if children is None:
        children = SubElement(parent, "children")
    topics = children.find("topics[@type='attached']")
    if topics is None:
        topics = SubElement(children, "topics", {"type": "attached"})
    topic = SubElement(topics, "topic", {"id": topic_id or _new_id()})
    SubElement(topic, "title").text = title
    return topic


def _find_child(parent: Element, title: str) -> Element | None:
    children = parent.find("children")
    if children is None:
        return None
    topics = children.find("topics[@type='attached']")
    if topics is None:
        return None
    for topic in topics.findall("topic"):
        if _text(topic.findtext("title")) == title:
            return topic
    return None


def _module_node(root: Element, modules: list[str]) -> Element:
    if len(modules) > 8:
        raise ValueError(f"模块层级超过 8 层: {modules}")
    current = root
    for module in modules:
        name = _text(module)
        if not name:
            continue
        current = _find_child(current, name) or _make_topic(current, name)
    return current


def _valid_case(case: dict) -> None:
    required = ("用例ID", "用例标题", "测试点ID", "需求ID", "设计方法", "步骤")
    missing = [key for key in required if not case.get(key)]
    if missing:
        raise ValueError(f"用例缺少必填字段: {', '.join(missing)}")
    if not isinstance(case["步骤"], list) or not case["步骤"]:
        raise ValueError(f"用例 {case.get('用例ID')} 至少需要一个步骤")
    for index, step in enumerate(case["步骤"], 1):
        if not isinstance(step, dict) or not _text(step.get("操作")) or not _text(step.get("预期", step.get("预期结果"))):
            raise ValueError(f"用例 {case.get('用例ID')} 第 {index} 步缺少操作或预期")


def normalize_cases(data) -> list[dict]:
    if isinstance(data, dict):
        data = data.get("test_cases", data.get("用例", []))
    if not isinstance(data, list):
        raise ValueError("输入必须是用例数组，或包含 test_cases 数组的对象")
    cases = []
    seen = set()
    for case in data:
        if not isinstance(case, dict):
            raise ValueError("每条用例必须是 JSON 对象")
        _valid_case(case)
        case_id = _text(case["用例ID"])
        if case_id in seen:
            raise ValueError(f"用例 ID 重复: {case_id}")
        seen.add(case_id)
        cases.append(case)
    if not cases:
        raise ValueError("输入中没有测试用例")
    return cases


def _add_case(parent: Element, case: dict) -> None:
    case_id = _text(case["用例ID"])
    priority = _text(case.get("优先级")).upper()
    prefix = f"tc-{priority.lower()}" if priority in {"P0", "P1", "P2", "P3"} else "tc"
    topic = _make_topic(parent, f"{prefix}: {_text(case['用例标题'])}", f"case-{case_id}")

    trace = (
        ("id", f"id: {case_id}"),
        ("tp", f"tp: {_text(case['测试点ID'])}"),
        ("req", f"req: {_text(case['需求ID'])}"),
        ("method", f"method: {_text(case['设计方法']) if isinstance(case['设计方法'], str) else '+'.join(map(str, case['设计方法']))}"),
    )
    for key, title in trace:
        _make_topic(topic, title, f"{case_id}-{key}")

    if _text(case.get("前置条件")):
        _make_topic(topic, f"pc: {_text(case['前置条件'])}", f"{case_id}-pc")
    for index, step in enumerate(case["步骤"], 1):
        action = _text(step["操作"])
        expected = _text(step.get("预期", step.get("预期结果")))
        step_topic = _make_topic(topic, action, f"{case_id}-step-{index}")
        _make_topic(step_topic, expected, f"{case_id}-expected-{index}")
    if _text(case.get("备注")):
        _make_topic(topic, f"rc: {_text(case['备注'])}", f"{case_id}-remark")
    if _text(case.get("标签")):
        _make_topic(topic, f"tag: {_text(case['标签'])}", f"{case_id}-tag")


def build_content(cases: list[dict], title: str) -> bytes:
    xmap = Element("xmap-content", {
        "version": "2.0",
        "xmlns": "urn:xmind:xmap:xmlns:content:2.0",
        "xmlns:fo": "http://www.w3.org/1999/XSL/Format",
        "xmlns:svg": "http://www.w3.org/2000/svg",
        "xmlns:xhtml": "http://www.w3.org/1999/xhtml",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
    })
    sheet = SubElement(xmap, "sheet", {"id": _new_id("sheet")})
    root = SubElement(sheet, "topic", {"id": _new_id("root")})
    SubElement(root, "title").text = title
    SubElement(sheet, "title").text = title
    for case in cases:
        modules = case.get("模块", [])
        modules = [modules] if isinstance(modules, str) else list(modules or [])
        _add_case(_module_node(root, modules), case)
    indent(xmap, space="  ")
    return tostring(xmap, encoding="utf-8", xml_declaration=True)


def build_manifest() -> bytes:
    manifest = Element("manifest", {"xmlns": "urn:xmind:xmap:xmlns:manifest:1.0"})
    SubElement(manifest, "file-entry", {"full-path": "content.xml", "media-type": "text/xml"})
    SubElement(manifest, "file-entry", {"full-path": "META-INF/", "media-type": ""})
    indent(manifest, space="  ")
    return tostring(manifest, encoding="utf-8", xml_declaration=True)


def load_json(path: str | None, raw: str | None):
    if raw:
        return json.loads(raw)
    if not path:
        raise ValueError("必须提供 --input/--file/--data 或 stdin")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def generate_xmind(cases: list[dict], output: Path, title: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("content.xml", build_content(cases, title))
        archive.writestr("META-INF/manifest.xml", build_manifest())


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 XMind 测试用例思维导图")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--title", default="测试用例")
    parser.add_argument("--input", "--file", dest="input_file", help="JSON 文件路径")
    parser.add_argument("-d", "--data", help="JSON 文本")
    args = parser.parse_args()
    try:
        data = load_json(args.input_file, args.data) if args.input_file or args.data else json.load(sys.stdin)
        cases = normalize_cases(data)
        generate_xmind(cases, Path(args.output), args.title)
        print(f"已生成 XMind: {args.output}（{len(cases)} 条用例）")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"生成失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
