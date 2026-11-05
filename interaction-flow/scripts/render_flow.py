#!/usr/bin/env python3
"""Render a temporary SVG for embedding in the final offline HTML."""

import argparse
from html import escape
import json
from pathlib import Path
import re
import sys
import unicodedata


FONT = 20
LINE_HEIGHT = 30
MARGIN = 48
LANE_WIDTH = 270
INK = "#25293d"
LINE = "#dce0ed"
ACCENT = "#4f46e5"
ASYNC = "#0f766e"
STATUS_LABELS = {"confirmed": "", "assumption": "假设：", "unresolved": "待确认："}
GROUP_LABELS = {"alt": "条件分支（只走命中的分支）", "parallel": "并行分支（上下排版不表示先后）", "loop": "循环", "optional": "可选阶段"}


def require_text(value, location):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string")


def validate(model):
    if not isinstance(model, dict):
        raise ValueError("The flow model must be an object")
    require_text(model.get("title"), "title")
    participants = model.get("participants")
    if not isinstance(participants, list) or not participants:
        raise ValueError("participants must be a non-empty array")
    actors = set()
    for index, actor in enumerate(participants):
        if not isinstance(actor, dict):
            raise ValueError(f"participants[{index}] must be an object")
        require_text(actor.get("id"), f"participants[{index}].id")
        require_text(actor.get("label"), f"participants[{index}].label")
        if actor["id"] in actors:
            raise ValueError(f"Duplicate participant ID: {actor['id']}")
        actors.add(actor["id"])
    identifiers = set()

    def check_steps(steps, location):
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"{location} must be a non-empty array")
        for index, step in enumerate(steps):
            here = f"{location}[{index}]"
            if not isinstance(step, dict):
                raise ValueError(f"{here} must be an object")
            kind = step.get("type")
            if kind not in {"message", "action", "note", "phase", *GROUP_LABELS}:
                raise ValueError(f"Unknown step type at {here}: {kind}")
            if step.get("status", "confirmed") not in STATUS_LABELS:
                raise ValueError(f"Unknown status at {here}")
            if "id" in step:
                require_text(step["id"], f"{here}.id")
                if step["id"] in identifiers:
                    raise ValueError(f"Duplicate step ID: {step['id']}")
                identifiers.add(step["id"])
            source = step.get("source", "")
            if not isinstance(source, str) and not (
                isinstance(source, list) and all(isinstance(item, str) for item in source)
            ):
                raise ValueError(f"{here}.source must be a string or an array of strings")
            if kind in {"alt", "parallel"}:
                branches = step.get("branches")
                if not isinstance(branches, list) or len(branches) < 2:
                    raise ValueError(f"{here}.branches must contain at least two branches")
                if "label" in step:
                    require_text(step["label"], f"{here}.label")
                for branch_index, branch in enumerate(branches):
                    branch_here = f"{here}.branches[{branch_index}]"
                    if not isinstance(branch, dict):
                        raise ValueError(f"{branch_here} must be an object")
                    require_text(branch.get("label"), f"{branch_here}.label")
                    check_steps(branch.get("steps"), f"{branch_here}.steps")
            else:
                require_text(step.get("label"), f"{here}.label")
                if kind in {"loop", "optional"}:
                    check_steps(step.get("steps"), f"{here}.steps")
                elif kind == "action":
                    if step.get("actor") not in actors:
                        raise ValueError(f"Unknown actor at {here}: {step.get('actor')}")
                elif kind == "message":
                    if step.get("from") not in actors or step.get("to") not in actors:
                        raise ValueError(f"Unknown message participant at {here}")
                    if step["from"] == step["to"]:
                        raise ValueError(f"Use action for self-processing at {here}")
                    if step.get("mode", "request") not in {"request", "response", "async"}:
                        raise ValueError(f"Unknown message mode at {here}")

    check_steps(model.get("steps"), "steps")


def width_units(value):
    total = 0
    for char in value:
        if unicodedata.combining(char):
            continue
        if unicodedata.east_asian_width(char) in {"W", "F"}:
            total += 1
        elif char in "MW@%":
            total += 0.96
        elif char.isascii() and char.isupper():
            total += 0.72
        elif char.isdigit():
            total += 0.64
        elif char.isspace():
            total += 0.35
        else:
            total += 0.60
    return total


def wrap(value, maximum, font=FONT):
    lines = []
    for paragraph in value.split("\n"):
        current = ""
        for token in re.findall(r"[A-Za-z0-9_./:@-]+|[ \t]+|.", paragraph):
            if width_units(token) * font > maximum:
                raise ValueError(
                    f"Identifier too wide for its lane: {token!r}. "
                    "Use a shorter display label and put the complete identifier in a note or explanation."
                )
            if current and width_units(current + token) * font > maximum:
                lines.append(current.rstrip())
                current = ""
            if not current and token.isspace():
                continue
            current += token
        lines.append(current.rstrip())
    return lines


def text_node(lines, center, baseline, maximum, color=INK, weight=400, font=FONT):
    attributes = (
        f'x="{center:.1f}" y="{baseline:.1f}" text-anchor="middle" '
        f'fill="{color}" font-size="{font}" font-weight="{weight}" '
        f'data-label-left="{center-maximum/2:.1f}" data-label-right="{center+maximum/2:.1f}"'
    )
    spans = "".join(
        f'<tspan x="{center:.1f}" dy="{LINE_HEIGHT if index else 0}">{escape(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return f"<text {attributes}>{spans}</text>"


def tooltip(step):
    source = step.get("source", "")
    if isinstance(source, list):
        source = "；".join(source)
    details = [source]
    if step.get("status", "confirmed") != "confirmed":
        details.append(STATUS_LABELS[step["status"]].rstrip("："))
    return f"<title>{escape('；'.join(item for item in details if item))}</title>"


class Renderer:
    def __init__(self, model):
        self.model = model
        self.width = max(1200, MARGIN * 2 + len(model["participants"]) * LANE_WIDTH)
        self.lane_width = (self.width - 2 * MARGIN) / len(model["participants"])
        self.positions = {
            actor["id"]: MARGIN + self.lane_width * (index + 0.5)
            for index, actor in enumerate(model["participants"])
        }
        self.parts = []
        self.y = 0
        self.number = 0

    def band(self, label, fill="#eef0fe", color=ACCENT, depth=0):
        left = MARGIN + depth * 10
        width = self.width - 2 * left
        lines = wrap(label, width - 40)
        height = 22 + len(lines) * LINE_HEIGHT
        self.parts.append(f'<rect x="{left}" y="{self.y}" width="{width}" height="{height}" rx="8" fill="{fill}"/>')
        self.parts.append(text_node(lines, self.width / 2, self.y + 32, width - 40, color, 500))
        self.y += height + 18

    def render_steps(self, steps, depth=0, inherited="confirmed"):
        for step in steps:
            status = step.get("status", inherited)
            kind = step["type"]
            color = "#a16207" if status != "confirmed" else ACCENT
            label = STATUS_LABELS[status] + step.get("label", "")
            step_attribute = f' data-step-id="{escape(step["id"], quote=True)}"' if "id" in step else ""
            self.parts.append(f"<g{step_attribute}>")
            self.parts.append(tooltip({**step, "status": status}))
            if kind in GROUP_LABELS:
                start = self.y
                frame_index = len(self.parts)
                self.parts.append("")
                group_label = GROUP_LABELS[kind]
                if step.get("label"):
                    group_label += " · " + step["label"]
                self.band(STATUS_LABELS[status] + group_label, color=color, depth=depth)
                if kind in {"alt", "parallel"}:
                    for branch_index, branch in enumerate(step["branches"]):
                        if branch_index:
                            self.parts.append(f'<line x1="{MARGIN+depth*10}" y1="{self.y}" x2="{self.width-MARGIN-depth*10}" y2="{self.y}" stroke="{LINE}" stroke-dasharray="6 4"/>')
                            self.y += 16
                        self.band(branch["label"], fill="#f5f7fb", color=INK, depth=depth+1)
                        self.render_steps(branch["steps"], depth+1, status)
                else:
                    self.render_steps(step["steps"], depth+1, status)
                self.y += 8
                self.parts[frame_index] = f'<rect x="{MARGIN+depth*10}" y="{start}" width="{self.width-2*MARGIN-depth*20}" height="{self.y-start}" rx="8" fill="none" stroke="{color}" stroke-width="1.5"/>'
                self.y += 20
            elif kind == "phase":
                self.band(label, color=color, depth=depth)
            elif kind == "note":
                self.band(label, fill="#fff8e7" if status != "confirmed" else "#f5f7fb", color="#a16207" if status != "confirmed" else "#62677e", depth=depth)
            elif kind == "action":
                self.number += 1
                identifier = step.get("id", f"{self.number:02d}")
                center = self.positions[step["actor"]]
                width = self.lane_width - 32
                lines = wrap(identifier + " " + label, width - 24)
                height = 22 + len(lines) * LINE_HEIGHT
                fill = "#fff8e7" if status != "confirmed" else "#f4f5fb"
                self.parts.append(f'<rect x="{center-width/2:.1f}" y="{self.y}" width="{width:.1f}" height="{height}" rx="8" fill="{fill}" stroke="{LINE}"/>')
                self.parts.append(text_node(lines, center, self.y + 32, width - 24))
                self.y += height + 28
            elif kind == "message":
                self.number += 1
                identifier = step.get("id", f"{self.number:02d}")
                x1, x2 = self.positions[step["from"]], self.positions[step["to"]]
                width = abs(x2 - x1) - 32
                center = (x1 + x2) / 2
                mode = step.get("mode", "request")
                label = identifier + " " + ("异步 · " if mode == "async" else "") + label
                lines = wrap(label, width)
                height = len(lines) * LINE_HEIGHT
                self.parts.append(f'<rect x="{center-width/2-5:.1f}" y="{self.y-5}" width="{width+10:.1f}" height="{height+12}" fill="#fff"/>')
                self.parts.append(text_node(lines, center, self.y + 23, width))
                arrow_y = self.y + height + 18
                if status == "confirmed" and mode == "async":
                    color = ASYNC
                marker = "pending" if status != "confirmed" else "async" if mode == "async" else "normal"
                dash = ' stroke-dasharray="7 5"' if mode == "response" else ""
                self.parts.append(f'<line x1="{x1:.1f}" y1="{arrow_y}" x2="{x2:.1f}" y2="{arrow_y}" stroke="{color}" stroke-width="2" marker-end="url(#arrow-{marker})"{dash}/>')
                if mode == "async":
                    self.parts.append(f'<circle cx="{x1:.1f}" cy="{arrow_y}" r="4" fill="{color}"/>')
                self.y = arrow_y + 34
            self.parts.append("</g>")

    def render(self):
        title_lines = wrap(self.model["title"], self.width - 2 * MARGIN, font=26)
        title_height = len(title_lines) * LINE_HEIGHT + 26
        actor_lines = [wrap(actor["label"], self.lane_width - 48, font=22) for actor in self.model["participants"]]
        header_height = max(len(lines) for lines in actor_lines) * LINE_HEIGHT + 26
        lane_start = title_height + header_height + 14
        self.y = lane_start + 26
        self.render_steps(self.model["steps"])
        content_end = self.y
        self.band("读图：实线为请求；虚线为返回；带圆点并标“异步”为事件或异步交互；步骤编号只用于定位。", fill="#f5f7fb", color="#62677e")
        self.band("条件框里的分支互斥；并行框的分支独立推进；“假设”和“待确认”不代表需求已明确。", fill="#f5f7fb", color="#62677e")
        height = self.y + 20
        sources = self.model.get("sources", [])
        if isinstance(sources, str):
            sources = [sources]
        source_text = "；".join(str(source) for source in sources)
        prefix = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{height}" viewBox="0 0 {self.width} {height}" role="img" aria-labelledby="flow-title flow-desc">',
            f'<title id="flow-title">{escape(self.model["title"])}</title>',
            f'<desc id="flow-desc">各列为参与方。同一顺序路径从上向下阅读，条件和并行分支以框标注。来源：{escape(source_text)}</desc>',
            "<defs>",
        ]
        for marker, color in [("normal", ACCENT), ("async", ASYNC), ("pending", "#a16207")]:
            prefix.append(f'<marker id="arrow-{marker}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>')
        prefix.extend(["</defs>", f'<rect width="{self.width}" height="{height}" fill="#fff"/>', '<g font-family="PingFang SC, Microsoft YaHei, sans-serif">'])
        prefix.append(text_node(title_lines, self.width / 2, 32, self.width - 2 * MARGIN, weight=600, font=26))
        for index, actor in enumerate(self.model["participants"]):
            center = self.positions[actor["id"]]
            left = MARGIN + index * self.lane_width
            prefix.append(f'<rect x="{left:.1f}" y="{lane_start}" width="{self.lane_width:.1f}" height="{content_end-lane_start}" fill="{"#fcfcff" if index % 2 == 0 else "#fff"}"/>')
            prefix.append(f'<line x1="{center:.1f}" y1="{lane_start}" x2="{center:.1f}" y2="{content_end}" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="6 7"/>')
            prefix.append(f'<rect x="{left+12:.1f}" y="{title_height}" width="{self.lane_width-24:.1f}" height="{header_height}" rx="9" fill="#eef0fe" stroke="{LINE}"/>')
            prefix.append(text_node(actor_lines[index], center, title_height + 33, self.lane_width - 48, weight=500, font=22))
        return "\n".join(prefix + self.parts + ["</g></svg>"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Temporary UTF-8 JSON flow model")
    parser.add_argument("-o", "--output", type=Path, help="Temporary SVG to embed in HTML; defaults to the input name with .svg")
    args = parser.parse_args()
    output = args.output or args.input.with_suffix(".svg")
    try:
        if output.resolve() == args.input.resolve():
            raise ValueError("The output must not replace the input model")
        model = json.loads(args.input.read_text(encoding="utf-8"))
        validate(model)
        svg = Renderer(model).render()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(svg, encoding="utf-8")
    except (OSError, ValueError, TypeError, RecursionError) as error:
        print(f"Cannot render flow: {error}", file=sys.stderr)
        return 1
    print(f"Rendered SVG: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
