#!/usr/bin/env python3
"""Install interaction-flow without changing global agent instructions."""

import argparse
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


PROJECT = Path(__file__).resolve().parent.parent
SKILL_NAME = "interaction-flow"
COMMON_FILES = (
    Path("SKILL.md"),
    Path("scripts/render_flow.py"),
    Path("references/flow-model.md"),
    Path("assets/output-template.md"),
)
CODEX_METADATA = Path("agents/openai.yaml")


def is_skill(path):
    entry = path / "SKILL.md"
    if not entry.is_file():
        return False
    content = entry.read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.S)
    return bool(frontmatter and re.search(
        r"(?m)^name:\s*(?:interaction-flow|\"interaction-flow\"|'interaction-flow')\s*$",
        frontmatter.group(1),
    ))


def related(left, right):
    return left == right or left in right.parents or right in left.parents


def check_target(target):
    if target.is_symlink():
        raise ValueError(f"Refusing to replace a symbolic-link skill directory: {target}")
    if related(PROJECT, target.resolve()):
        raise ValueError(f"The installation must not overlap the source project: {target}")
    if target.exists() and (not target.is_dir() or not is_skill(target)):
        raise ValueError(f"The destination is not an interaction-flow installation: {target}")


def install(platform, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".interaction-flow-stage-", dir=target.parent))
    backup = None
    try:
        files = list(COMMON_FILES)
        if platform == "codex":
            files.append(CODEX_METADATA)
        for relative in files:
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT / relative, destination)
        if target.exists():
            backup = Path(tempfile.mkdtemp(prefix=".interaction-flow-backup-", dir=target.parent))
            backup.rmdir()
            target.rename(backup)
        try:
            stage.rename(target)
        except OSError:
            if backup is not None:
                backup.rename(target)
                backup = None
            raise
        if backup is not None:
            shutil.rmtree(backup)
            backup = None
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(f"Installed {platform}: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("all", "codex", "claude"), default="all")
    parser.add_argument(
        "--codex-home", type=Path,
        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
        help="Codex configuration root; defaults to CODEX_HOME or ~/.codex",
    )
    parser.add_argument(
        "--claude-home", type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))),
        help="Claude Code configuration root; defaults to CLAUDE_CONFIG_DIR or ~/.claude",
    )
    args = parser.parse_args()
    targets = []
    if args.target in ("all", "codex"):
        targets.append(("codex", args.codex_home.expanduser().absolute() / "skills" / SKILL_NAME))
    if args.target in ("all", "claude"):
        targets.append(("claude", args.claude_home.expanduser().absolute() / "skills" / SKILL_NAME))
    try:
        required = list(COMMON_FILES) + ([CODEX_METADATA] if args.target in ("all", "codex") else [])
        for relative in required:
            if not (PROJECT / relative).is_file():
                raise ValueError(f"Missing source resource: {relative}")
        if not is_skill(PROJECT):
            raise ValueError("The source SKILL.md does not declare interaction-flow")
        for _, target in targets:
            check_target(target)
        for index, (_, target) in enumerate(targets):
            for _, other in targets[index + 1:]:
                if related(target.resolve(), other.resolve()):
                    raise ValueError("Codex and Claude Code must use separate skill directories")
        for platform, target in targets:
            install(platform, target)
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        return 1
    print("Invocation: Codex $interaction-flow; Claude Code /interaction-flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
