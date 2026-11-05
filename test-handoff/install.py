#!/usr/bin/env python3
"""Install the self-contained skill for Claude Code and Codex."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
NAME = "test-handoff"
MARKER = ".test-handoff-install.json"
RESOURCES = ("SKILL.md", "agents", "scripts", "references", "assets", "examples")


def destinations(platform):
    home = Path.home()
    targets = {"claude": home / ".claude" / "skills" / NAME,
               "codex": Path(os.environ.get("CODEX_HOME") or home / ".codex").expanduser() / "skills" / NAME}
    return targets if platform == "both" else {platform: targets[platform]}


def managed(path):
    try:
        marker = json.loads((path / MARKER).read_text(encoding="utf-8"))
        return marker.get("name") == NAME and marker.get("installer") == "test-handoff"
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("both", "claude", "codex"), default="both")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    targets = destinations(args.platform)
    for path in targets.values():
        if path.is_symlink() or path.resolve() == ROOT:
            parser.error(f"Refusing to replace a symlink or source project: {path}")
        if path.exists() and not managed(path):
            parser.error(f"Directory is not managed by this installer: {path}")
    for platform, path in targets.items():
        if args.uninstall:
            if path.exists():
                shutil.rmtree(path)
                print(f"Removed {platform}: {path}")
            else:
                print(f"Already absent {platform}: {path}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        staging = path.with_name(path.name + ".installing")
        if staging.exists():
            parser.error(f"Staging directory already exists; inspect it before retrying: {staging}")
        staging.mkdir()
        try:
            for name in RESOURCES:
                source, dest = ROOT / name, staging / name
                if source.is_dir():
                    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
                else:
                    shutil.copy2(source, dest)
            (staging / MARKER).write_text(json.dumps({"name": NAME, "installer": "test-handoff", "version": 1,
                "installedAt": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n", encoding="utf-8")
            if path.exists():
                shutil.rmtree(path)
            staging.rename(path)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        print(f"Installed {platform}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
