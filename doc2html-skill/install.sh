#!/usr/bin/env bash
# doc2html-skill 安装器：按 PROTOCOL.md v1.5 把技能装配到 Claude Code / ZCode / DSH / Codex
# 用法：install.sh [--uninstall]
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
# 各平台安装根（全部 $HOME 相对，禁止机器特定绝对路径，见 PROTOCOL.md §2）
CLAUDE_SKILL="${HOME}/.claude/skills/doc-to-html"
ZCODE_SKILL="${HOME}/.zcode/skills/doc-to-html"
DSH_ROOT="${DSH_HOME:-${HOME}/.dsh}"
DSH_SKILL="${DSH_ROOT}/skills/doc-to-html"
CODEX_ROOT="${CODEX_HOME:-${HOME}/.codex}"
CODEX_SKILL="${CODEX_ROOT}/skills/doc-to-html"
CODEX_DIR="${CODEX_ROOT}/prompts/doc-to-html"
CODEX_PROMPT="${CODEX_ROOT}/prompts/doc-to-html.md"
CODEX_AGENTS="${CODEX_ROOT}/AGENTS.md"

uninstall() {
  echo "==> 卸载各平台安装副本（源项目不动）"
  rm -rf "${CLAUDE_SKILL}" "${ZCODE_SKILL}" "${DSH_SKILL}" "${CODEX_SKILL}" "${CODEX_DIR}" "${CODEX_PROMPT}"
  if [ -f "${CODEX_AGENTS}" ]; then
    python3 "${SRC}/scripts/update_codex_agents.py" "${CODEX_AGENTS}" --remove
  fi
  echo "完成卸载。"
  exit 0
}

[ "${1:-}" = "--uninstall" ] && uninstall

echo "==> 替换旧版安装副本（整目录替换，无历史残留）"
rm -f "${CODEX_PROMPT}"

# 保留其他安装器写入的版本记录，避免覆盖整个目录时丢掉安装来源信息
keep_receipts() { # $1=旧目录 $2=新目录
  for receipt in .skill-manager.json; do
    if [ -f "$1/$receipt" ]; then
      cp -p "$1/$receipt" "$2/$receipt"
    fi
  done
}

install_copy() { # $1=目标目录
  local wrapper="" previous=""
  if [ -d "$1" ] && [ ! -L "$1" ]; then
    wrapper="$(mktemp -d "${1%/*}/.doc-to-html-previous-XXXXXX")"
    previous="${wrapper}/old"
    mv "$1" "$previous"
  fi
  mkdir -p "$1/scripts"
  cp "${SRC}/scripts/md2html.py" "$1/scripts/md2html.py"
  cp "${SRC}/references/style-guide.md" "$1/style-guide.md"
  cp "${SRC}/PROTOCOL.md" "$1/PROTOCOL.md"
  chmod +x "$1/scripts/md2html.py" 2>/dev/null || true
  if [ -n "$wrapper" ]; then
    keep_receipts "$previous" "$1"
    rm -rf "$wrapper"
  fi
}

echo "==> Claude Code → ${CLAUDE_SKILL}"
install_copy "${CLAUDE_SKILL}"
cp "${SRC}/SKILL.md" "${CLAUDE_SKILL}/SKILL.md"

echo "==> ZCode → ${ZCODE_SKILL}"
install_copy "${ZCODE_SKILL}"
cp "${SRC}/SKILL.md" "${ZCODE_SKILL}/SKILL.md"

echo "==> DSH → ${DSH_SKILL}"
install_copy "${DSH_SKILL}"
cp "${SRC}/SKILL.md" "${DSH_SKILL}/SKILL.md"

echo "==> Codex skill → ${CODEX_SKILL}"
install_copy "${CODEX_SKILL}"
cp "${SRC}/SKILL.md" "${CODEX_SKILL}/SKILL.md"

echo "==> Codex 兼容提示词 → ${CODEX_PROMPT} + ${CODEX_DIR}"
install_copy "${CODEX_DIR}"
cp "${SRC}/codex/doc-to-html.prompt.md" "${CODEX_PROMPT}"

echo "==> 在 ${CODEX_AGENTS} 更新入口提示（仅修改托管块）"
python3 "${SRC}/scripts/update_codex_agents.py" "${CODEX_AGENTS}"

echo "==> 预热依赖（真实转换，装进各副本的 scripts/_vendor）"
for copy in "${CLAUDE_SKILL}" "${ZCODE_SKILL}" "${DSH_SKILL}" "${CODEX_SKILL}" "${CODEX_DIR}"; do
  if python3 "${copy}/scripts/md2html.py" "${SRC}/samples/sample.md" -o /tmp/doc2html_warmup.html --title warmup >/dev/null 2>&1; then
    echo "    ${copy} 依赖就绪。"
  else
    echo "    ${copy} 预热失败（离线环境？首次使用时会再尝试）。"
  fi
done
rm -f /tmp/doc2html_warmup.html

echo
echo "完成（PROTOCOL v1.5）。使用方式："
echo "  - Claude Code：直接说「把 xx 方案转成 HTML」，或 /doc-to-html"
echo "  - ZCode：      直接说「把 xx 方案转成 HTML」（新会话生效）"
echo "  - DSH：        直接说「把 xx 方案转成 HTML」，或 /doc-to-html"
echo '  - Codex：      会话内输入 $doc-to-html，或 /skills 中选择 doc-to-html'
echo '  - Codex 旧提示词：支持自定义 prompt 的 CLI 中输入 /prompts:doc-to-html'
echo '  - IDEA：       在项目目录启动会话，指定 docs/需求.md，默认生成同目录的 HTML'
echo "  - 卸载：       bash $0 --uninstall"
