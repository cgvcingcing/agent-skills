#!/usr/bin/env bash
# Install the shared skill for Codex and/or Claude Code.
set -euo pipefail

INTERACTION_FLOW_PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${INTERACTION_FLOW_PROJECT_DIR}/scripts/install_skill.py" "$@"
