#!/bin/bash
# Install this repository's skills into local agent skill directories.
# Defaults to Codex; pass --platform dsh to install into DSH instead.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PLATFORM="codex"
while [ $# -gt 0 ]; do
  case "$1" in
    --platform) PLATFORM="${2:-}"; shift 2 ;;
    --platform=*) PLATFORM="${1#*=}"; shift ;;
    -h|--help)
      echo "usage: $0 [--platform codex|dsh]"
      exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

case "$PLATFORM" in
  codex) SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills" ;;
  dsh) SKILLS_DIR="${DSH_HOME:-$HOME/.dsh}/skills" ;;
  *) echo "unsupported platform: $PLATFORM" >&2; exit 2 ;;
esac

mkdir -p "$SKILLS_DIR"
rm -rf "$SKILLS_DIR/extract-test-points" "$SKILLS_DIR/generate-test-cases"
cp -R "$PROJECT_ROOT/skill-extract-test-points" "$SKILLS_DIR/extract-test-points"
cp -R "$PROJECT_ROOT/skill-generate-test-cases" "$SKILLS_DIR/generate-test-cases"
echo "已安装到: $SKILLS_DIR"
