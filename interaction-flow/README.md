# interaction-flow · 交互闭环解读

依据需求方案，按用户目的梳理业务流程、模块联动或数据交互，只输出一份内含主图、必要说明和来源依据的离线 HTML。

业务事实来自需求方案、关联原型和截图；分析假设与待确认问题单独标注。已有用户澄清按适用范围沿用。需要文档式排版时可配合 `doc-to-html`；需要测试设计时配合 `testcase-bdd-sdd`。

快速回顾项目时，先用一张业务主图讲清起点、关键判断与完成点。模块分工和数据交互按需独立呈现，接口、表字段、消息落库不混进业务节点；流程到达用户关心的终点就停止延伸。脚本 `render_flow.py` 用于调用与消息时序图，普通业务流程可直接绘制为 SVG 或 HTML/CSS。

## 安装

需要 Python 3.9 或以上版本，以及 Codex 或 Claude Code。安装和 SVG 渲染只使用 Python 标准库，不下载依赖。

在本项目目录运行：

```bash
bash install.sh
```

默认安装到两端的个人技能目录，重复执行会更新本技能的安装副本：

| 平台 | 默认安装目录 | 调用 |
| --- | --- | --- |
| Codex | `~/.codex/skills/interaction-flow/` | `$interaction-flow` |
| Claude Code | `~/.claude/skills/interaction-flow/` | `/interaction-flow` |

仅安装一端：

```bash
bash install.sh --target claude
bash install.sh --target codex
```

支持 `CODEX_HOME` 和 `CLAUDE_CONFIG_DIR`。也可以指定配置根目录，脚本会在其下创建 `skills/interaction-flow/`：

```bash
bash install.sh --target claude --claude-home "/path/to/claude-config"
bash install.sh --target codex --codex-home "/path/to/codex-config"
```

源项目与安装副本分开保存。安装器只替换本技能目录，不修改全局 `AGENTS.md`、`CLAUDE.md` 或其他技能；更新前先准备新副本，目录替换失败时恢复旧副本。安装后在新会话中使用。

## 使用

在存放需求材料的业务项目里启动 Codex 或 Claude Code。输入、输出的相对路径都以该业务项目目录为准，无需切换到本技能项目。

Codex：

```text
$interaction-flow 根据 docs/需求方案.html 梳理交互闭环，生成泳道图，输出到 outputs/flow。
```

Claude Code：

```text
/interaction-flow 根据 docs/需求方案.html 梳理交互闭环，生成泳道图，输出到 outputs/flow。
```

也可以直接说：“帮我看清这份方案里后台审批后怎样生效，画一张泳道图。”同样适用于用户操作、服务调用、事件回调和定时任务等入口。

无需另行指定 HTML：每次任务只保留一份最终 HTML，双击即可离线查看，多张图和全部说明都在同一文件内。流程模型 JSON、SVG、Markdown、提取稿和截图只放在本次任务的专用临时目录，验证完成后自动清理；交付目录不保留图源文件夹，也不留下指向过程文件的链接。用户原始输入和已有历史产物保持原样。

## 项目结构

```text
interaction-flow/
├── SKILL.md                   两端共用的技能入口
├── README.md                  安装与使用说明
├── PROTOCOL.md                平台路径与安装约定
├── install.sh                 双端安装入口
├── agents/openai.yaml         Codex 界面元数据
├── assets/output-template.md  HTML 内容组织模板
├── references/flow-model.md   图模型与读图规则
├── scripts/render_flow.py     临时 JSON → 待内嵌 SVG
├── scripts/install_skill.py   安装与更新逻辑
└── tests/test_install.py      隔离目录中的安装验证
```

`agents/openai.yaml` 只安装到 Codex；Claude Code 直接读取共用的 `SKILL.md` 和配套资源。渲染器根据本次加载的技能目录定位，不把机器路径写进技能。

这些 Markdown 文件是项目与技能的维护资源，不作为业务交付件。渲染脚本仅用于生成待内嵌的图，最终 HTML 必须包含全部图像、样式和脚本，并能在不携带过程文件时正常查看。

## 开发与验证

修改源项目后重新执行 `bash install.sh`，让两端使用相同版本的技能内容。不要直接改某个安装副本后把它当作源项目。

```bash
bash -n install.sh
python3 -m unittest discover -s tests -v
```

测试会在临时目录验证双端安装、单端安装、升级、路径中含空格或中文、配置根目录、源项目保护及已安装渲染器。不会改动实际个人技能目录，也不会调用付费模型服务。

Claude Code 加载规则参考[官方技能文档](https://code.claude.com/docs/en/skills)。平台布局和脚本接口见 [PROTOCOL.md](PROTOCOL.md)。
