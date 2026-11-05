# interaction-flow 平台适配约定

## 共用内容与平台入口

| 平台 | 入口 | 显式调用 | 专属文件 |
| --- | --- | --- | --- |
| Codex | `~/.codex/skills/interaction-flow/SKILL.md` | `$interaction-flow` | `agents/openai.yaml` |
| Claude Code | `~/.claude/skills/interaction-flow/SKILL.md` | `/interaction-flow` | 无需额外入口 |

两端的 `SKILL.md`、渲染脚本、流程模型说明和输出模板逐字一致。Claude Code 使用原生 skill 目录，不额外复制到旧式 `commands/`，也不注入全局 `CLAUDE.md`。Codex 使用原生 skill 目录，不生成兼容 prompt。

`CODEX_HOME` 或 `--codex-home` 可改变 Codex 配置根目录；`CLAUDE_CONFIG_DIR` 或 `--claude-home` 可改变 Claude Code 配置根目录。命令行参数优先于环境变量。两端的技能目录须分开。

## 路径与安装

- 项目可放在任意目录。安装器以自身所在项目为源，不依赖调用时的工作目录。
- 运行时以已加载 `SKILL.md` 的父目录定位配套资源。用户需求与最终 HTML 的相对路径按业务项目当前目录解析；图源和其他过程文件使用本轮任务的专用临时目录。
- 技能及脚本不写入机器用户名或项目绝对路径。交付时可展示实际生成路径。
- `bash install.sh` 默认安装两端；`--target codex` 或 `--target claude` 只安装指定平台。
- 安装器只复制 `SKILL.md`、`scripts/render_flow.py`、`references/flow-model.md`、`assets/output-template.md`；Codex 额外复制 `agents/openai.yaml`。本约定、README、安装器和测试留在源项目。
- 更新以完整新副本替换本技能的旧目录，避免残留过期资源。只更新声明 `name: interaction-flow` 的现有安装；源项目、非本技能目录和目录符号链接不作为替换目标。
- 安装不触碰需求原材料、历史交付、其他技能或全局 agent 配置。

## 渲染接口

此接口生成的 SVG 仅用于组装最终 HTML，输入 JSON 和输出 SVG 都应放在本轮任务的专用临时目录。

```text
python3 <skill-directory>/scripts/render_flow.py <temporary-directory>/INPUT.json -o <temporary-directory>/OUTPUT.svg
```

底层脚本未指定输出时会在输入文件旁生成同名 SVG，因此输入模型也必须放在临时目录。模型字段、交互类型和来源记录按 [references/flow-model.md](references/flow-model.md)。SVG 不依赖网络；输入模型不会被覆盖。

## 交付约定

- 每次任务只交付一份自包含 HTML，多图、流程说明、来源依据和待确认问题均内嵌其中。
- 先按用户目的选择业务流程、模块联动或数据交互视图，同一主图保持同一层次；快速回顾场景先呈现完整业务主线，其他视角按需独立查看。图的范围止于用户关心的完成点。
- 图像、样式、脚本不依赖网络或旁置文件。HTML 不链接待清理的 Markdown、SVG、JSON 等过程文件。
- Markdown 说明、组装稿、JSON 模型、SVG、提取稿、截图和校验副本均为过程文件，不在交付目录另存。将最终 HTML 单独放在临时空目录，断网检查通过后，自动清理本轮专用临时目录。
- 清理只针对本轮生成并已整合进 HTML 的过程文件；保留用户原始输入与既有历史产物。项目文档和技能模板为维护资源，不作为业务交付件。

业务分析和图模型规则保持共用。修改公共技能内容或渲染行为后，运行安装验证并重新安装；不能只改某个平台副本。
