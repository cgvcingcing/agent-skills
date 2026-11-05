#!/usr/bin/env python3
"""Render an editable or read-only test handoff form using only the standard library."""

import argparse
import copy
import html
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
META = ("requirement", "ticket", "environment", "build", "developer", "tester", "date", "change")
EXTRAS = ("release", "limits", "conclusion")
STATES = ("待补充", "已确认", "不涉及")


def read_schema():
    return json.loads((ASSETS / "form.schema.json").read_text(encoding="utf-8"))


def as_text(value, field):
    if not isinstance(value, str) or len(value) > 100000:
        raise ValueError(f"Invalid text field: {field}")
    return value


def normalize(raw, title=None):
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object")
    if raw.get("format", "test-handoff-form") != "test-handoff-form" or raw.get("version", 1) != 1:
        raise ValueError("Unsupported handoff data format or version")
    data = copy.deepcopy(raw)
    data.update(format="test-handoff-form", version=1)
    data["documentId"] = as_text(data.get("documentId") or str(uuid.uuid4()), "documentId")
    for name, fields in (("meta", META), ("extras", EXTRAS)):
        group = data.setdefault(name, {})
        if not isinstance(group, dict):
            raise ValueError(f"{name} must be an object")
        for key in fields:
            group[key] = as_text(group.get(key, ""), f"{name}.{key}")
    if title is not None:
        data["meta"]["requirement"] = title
    for key in ("tables", "sections"):
        if not isinstance(data.setdefault(key, {}), dict):
            raise ValueError(f"{key} must be an object")
    seen = set()
    for name, table in read_schema().items():
        rows = data["tables"].setdefault(name, [])
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValueError(f"Invalid row list: {name}")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Invalid row in {name}")
            row_id = row.get("_id")
            if not isinstance(row_id, str) or not row_id or row_id in seen:
                row_id = str(uuid.uuid4())
            seen.add(row_id)
            row["_id"] = row_id
            for col in table["columns"]:
                default = col["options"][0] if col["kind"] == "select" else ""
                row[col["key"]] = as_text(row.get(col["key"], default), f"{name}.{col['key']}")
                if col["kind"] == "select" and row[col["key"]] not in col["options"]:
                    raise ValueError(f"Invalid selection: {name}.{col['key']}")
        section = data["sections"].setdefault(name, {"status": STATES[0], "note": ""})
        if not isinstance(section, dict) or section.get("status", STATES[0]) not in STATES:
            raise ValueError(f"Invalid section status: {name}")
        section.setdefault("status", STATES[0])
        section["note"] = as_text(section.get("note", ""), f"sections.{name}.note")
    for key in ("_presentation",):
        if key in data and not isinstance(data[key], dict):
            raise ValueError(f"{key} must be an object")
    return data


def extract(path):
    source = Path(path).read_text(encoding="utf-8")
    match = re.search(r'<script\b[^>]*\bid=[\'\"]handoff-data[\'\"][^>]*>(.*?)</script\s*>', source, re.S | re.I)
    if not match:
        raise ValueError("No embedded handoff-data found in this HTML")
    return json.loads(match.group(1))


def esc(value):
    return html.escape(str(value), quote=True)


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def field(binding, label, hint, value, area=False, read_only=False):
    if read_only:
        return f'<div class="readonly-field" data-binding="{esc(binding)}" aria-label="{esc(label)}">{esc(value)}</div>'
    attr = f'class="field" data-binding="{esc(binding)}" aria-label="{esc(label)}" placeholder="{esc(hint)}"'
    return (f'<textarea {attr} rows="2">{esc(value)}</textarea>' if area
            else f'<input {attr} type="text" value="{esc(value)}">')


def meta_fields(data, read_only=False):
    labels = [
        ("requirement", "需求 / 项目", "需求名称"),
        ("ticket", "需求链接 / 编号", "需求或提测单的地址 / 编号"),
        ("environment", "测试环境 / 客户端", "环境、访问入口、客户端版本 / 平台"),
        ("build", "提测版本", "分支、构建号或版本标签"),
        ("developer", "开发负责人", "负责人及联系方式"),
        ("tester", "测试负责人", "测试负责人"),
        ("date", "提测日期 / 计划", "提测时间及计划测试窗口"),
        ("change", "本轮改动", "简要说明本轮业务变化"),
    ]
    return "\n".join(f'<div class="meta-item{" wide" if key == "change" else ""}"><span>{label}</span>'
                     + field("meta." + key, label, hint, data["meta"][key], key in ("ticket", "environment", "build", "change"), read_only) + "</div>"
                     for key, label, hint in labels)


def extra(data, key, label, hint, read_only=False):
    return f'<details class="extra-field extra-{key}" open><summary>{label}<span class="details-action" aria-hidden="true"></span></summary><div class="extra-body">' + field("extras." + key, label, hint, data["extras"][key], True, read_only) + "</div></details>"


def table_html(name, spec, read_only=False):
    columns = [c for c in spec["columns"] if not c.get("optional")]
    if name == "scope":
        columns = [dict(title=title, width=width) for title, width in [
            ("测试范围 / 优先级", 16), ("页面 / 功能模块", 20), ("业务场景与结果", 40), ("数据 / 配置依赖", 24)]]
    widths = sum(col["width"] for col in columns)
    cols = "".join(f'<col style="width:{col["width"] / widths * (100 if name == "scope" else 97):.2f}%">' for col in columns)
    headings = "".join(f'<th scope="col">{esc(col["title"])}</th>' for col in columns)
    if name != "scope" and not read_only:
        cols += '<col style="width:3%">'
        headings += '<th scope="col" class="actions-col"><span class="sr-only">操作</span></th>'
    table = f'<div class="tw"><table class="handoff-table table-{name}" data-table="{name}"><colgroup>{cols}</colgroup><thead><tr>{headings}</tr></thead><tbody></tbody></table></div>'
    if not read_only:
        table += f'\n<div class="table-bottom"><button class="add-row" type="button" data-add="{name}">＋ {esc(spec["add"])}</button><span>点击内容即可编辑，完成后自动恢复排版。</span></div>'
    return table


def render(raw, title=None, fresh_draft=False, read_only=False):
    data = normalize(raw, title)
    if fresh_draft:
        data["documentId"] = str(uuid.uuid4())
    schema = read_schema()
    project = data["meta"]["requirement"] or "待填写需求"
    toc, shortcuts, sections = [], [], []
    for i, (name, spec) in enumerate(schema.items(), 1):
        label = esc(spec["title"])
        toc.append(f'<a class="l2 fl-{i}" href="#section-{name}" data-target="section-{name}"><span class="nav-index">{i:02}</span><span class="lbl">{label}</span></a>')
        shortcuts.append(f'<a href="#section-{name}" data-shortcut="{name}"><span class="section-number">{i:02}</span><b>{label}</b><span class="section-state">待补充</span></a>')
        content = f'''<section class="form-section section-{name}" data-section="{name}" data-collapsed="false">
<h2 id="section-{name}" class="fl-{i}"><button type="button" class="section-toggle" data-toggle-section="{name}" aria-expanded="true" aria-controls="body-{name}"><span class="fl-badge">{i:02}</span><span class="section-heading-copy"><span class="section-title">{label}</span><span class="section-summary" data-section-summary="{name}"></span></span><span class="section-toggle-action"><span class="section-toggle-label">收起</span><svg class="section-chevron" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="m5 12 5-5 5 5"/></svg></span></button></h2>
<div class="section-body" id="body-{name}">'''
        content += f'<p class="section-intro" data-intro="{name}"></p><div data-presentation="{name}-before"></div>'
        if name == "scope":
            content += '''<div class="priority-overview"><div><b>范围优先级</b><span id="priority-summary" aria-live="polite"></span></div><p>“含 P0”表示这组中有核心场景。优先级依据可在每组下方展开；“本次范围”由开发另行确认。</p></div>'''
            content += '''<div class="range-controls"><span>业务范围</span><div class="section-controls" role="group" aria-label="业务范围展开与收起"><button type="button" id="expand-ranges">展开全部范围</button><button type="button" id="collapse-ranges">收起全部范围</button></div></div>'''
        if name != "scope":
            content += f'''<div class="record-controls"><span>点击记录标题可展开或收起</span><div class="section-controls" role="group" aria-label="{label}记录展开与收起"><button type="button" data-record-expand="{name}">展开全部记录</button><button type="button" data-record-collapse="{name}">收起全部记录</button></div></div>'''
        content += table_html(name, spec, read_only)
        content += f'<div data-presentation="{name}-after"></div>'
        if name == "config":
            content += extra(data, "release", "发布 / 恢复安排", "发布顺序、实际版本、生效检查、恢复配置及负责人", read_only)
        if name == "samples":
            content += '<div class="closing-grid">' + extra(data, "limits", "待确认范围 / 已知限制", "本次范围、已知问题、允许的差异与判断标准", read_only) + extra(data, "conclusion", "交接说明", "尚缺什么、由谁补、何时提供；需特别关注的业务风险", read_only) + "</div>"
        opts = "".join(f'<option>{x}</option>' for x in STATES)
        if read_only:
            confirmation = data["sections"][name]
            content += f'<div class="section-confirm" data-confirm="{name}"><div class="readonly-confirm-label">开发确认 <span class="readonly-status" data-section-status="{name}">{esc(confirmation["status"])}</span></div><div class="readonly-note" data-section-note="{name}" aria-label="{label}确认说明">{esc(confirmation["note"])}</div></div></div></section>'
        else:
            content += f'<div class="section-confirm" data-confirm="{name}"><label>开发确认 <select aria-label="{label}确认状态" data-section-status="{name}">{opts}</select></label><textarea rows="2" data-section-note="{name}" aria-label="{label}确认说明" placeholder="确认人 / 日期；选不涉及时说明原因"></textarea><div class="section-note-preview"></div></div></div></section>'
        sections.append(content)
    edit_actions = '' if read_only else '<button type="button" id="next-empty">定位待填</button><button type="button" id="export-json">导出数据</button><button type="button" id="import-json">导入数据</button>'
    save_action = '' if read_only else '<button class="primary" type="button" id="save-html">保存填写版 HTML</button>'
    import_field = '' if read_only else '<input id="import-file" type="file" accept="application/json,.json" hidden>'
    status = '只读版 · 内容已锁定' if read_only else '本机自动暂存'
    toolbar = f'<div class="toolbar"><div class="toolbar-status"><span class="live-dot"></span><span id="save-status" role="status">{status}</span></div><div class="toolbar-actions">{edit_actions}<button type="button" id="print-form">打印 / PDF</button>{save_action}</div>{import_field}</div>'
    replacements = {
        "TITLE": esc(project + (" · 测试交接只读版" if read_only else " · 测试交接填写表")), "PROJECT": esc(project),
        "READONLY": str(read_only).lower(), "TOOLBAR": toolbar,
        "CSS": (ASSETS / "form.css").read_text(encoding="utf-8") + "\n" + (ASSETS / "hierarchy.css").read_text(encoding="utf-8"),
        "APP": (ASSETS / "form.js").read_text(encoding="utf-8"),
        "SCHEMA": safe_json(schema), "DATA": safe_json(data),
        "TOC": "\n".join(toc), "META": meta_fields(data, read_only),
        "SHORTCUTS": "\n".join(shortcuts), "SECTIONS": "\n".join(sections),
    }
    template = (ASSETS / "form.html").read_text(encoding="utf-8")
    if read_only:
        template = re.sub(r'<details class="fill-note">.*?</details>\s*', '', template, flags=re.S)
        template = re.sub(r'<div id="toast".*?</div>\s*', '', template, flags=re.S)
        template = template.replace('测试交接填写表', '测试交接只读版').replace('开发填写 · 测试使用', '已确认版本 · 测试查阅')
        template = template.replace('分享前请保存填写版 HTML。', '可直接分享本文件。').replace('可离线填写与分享', '可离线查阅与分享')
        template = template.replace('请启用浏览器 JavaScript 后填写此表。', '请启用浏览器 JavaScript 后查阅完整内容。')
    return re.sub(r"@@([A-Z]+)@@", lambda m: replacements[m.group(1)], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Handoff JSON to render")
    source.add_argument("--blank", action="store_true", help="Create an empty developer form")
    source.add_argument("--from-html", type=Path, help="Update styling while preserving embedded handoff data")
    source.add_argument("--extract", type=Path, help="Extract embedded handoff JSON without rendering")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--title", help="Requirement/project name")
    parser.add_argument("--fresh-draft", action="store_true", help="Use a fresh browser draft ID when replacing or migrating answers")
    parser.add_argument("--read-only", action="store_true", help="Finalize the supplied answers without editing or browser draft restoration")
    args = parser.parse_args()
    try:
        if args.extract:
            result = json.dumps(extract(args.extract), ensure_ascii=False, indent=2) + "\n"
        else:
            if args.blank:
                raw = {"tables": {name: [{}] for name in read_schema()}}
            elif args.from_html:
                raw = extract(args.from_html)
            else:
                raw = json.loads(args.input.read_text(encoding="utf-8"))
            read_only = args.read_only or bool(args.from_html and re.search(
                r'<html\b[^>]*\bdata-read-only=[\'\"]true[\'\"]', args.from_html.read_text(encoding="utf-8"), re.I))
            result = render(raw, args.title, args.fresh_draft, read_only)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
        print(f"Created: {args.output.resolve()}")
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
