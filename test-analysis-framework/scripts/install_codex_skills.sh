#!/bin/bash
# Install this repository's skills into the local Codex skill directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CODEX_SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"

mkdir -p "$CODEX_SKILLS_DIR"
rm -rf "$CODEX_SKILLS_DIR/extract-test-points" "$CODEX_SKILLS_DIR/generate-test-cases"
cp -R "$PROJECT_ROOT/skill-extract-test-points" "$CODEX_SKILLS_DIR/extract-test-points"
cp -R "$PROJECT_ROOT/skill-generate-test-cases" "$CODEX_SKILLS_DIR/generate-test-cases"
echo "已安装到: $CODEX_SKILLS_DIR"
