# 个人技能库

统一维护需求解读、测试方案、测试点、测试用例、文档转换和开发提测交接技能。五个源项目保留原目录结构，在这个总仓库中一起维护，使用一个入口安装、更新和检查。

## 技能目录

| 技能 | 用途 | 调用 | 支持平台 |
| --- | --- | --- | --- |
| [文档转 HTML](doc2html-skill/SKILL.md) | Markdown、Word、PDF、方案截图转离线 HTML | `$doc-to-html` | Codex、Claude Code、ZCode |
| [交互闭环解读](interaction-flow/SKILL.md) | 梳理业务流程、模块联动和数据交互 | `$interaction-flow` | Codex、Claude Code |
| [需求转测试方案](spec2testplan-skill/SKILL.md) | 说明怎么测、先测什么、重点风险和优先级 | `$spec2testplan` | Codex、Claude Code |
| [提炼测试点](test-analysis-framework/skill-extract-test-points/SKILL.md) | 从需求材料提取可追溯测试点 | `$extract-test-points` | Codex |
| [生成测试用例](test-analysis-framework/skill-generate-test-cases/SKILL.md) | 根据测试点或需求生成用例和 XMind | `$generate-test-cases` | Codex |
| [开发提测交接表](test-handoff/SKILL.md) | 生成开发可填写的离线提测表 | `$test-handoff` | Codex、Claude Code |

表中列出 Codex 调用方式。Claude Code 使用对应的 `/技能标识` 调用。文件名、技能标识和原有调用方式保留。

`spec2testplan` 推荐使用 `doc-to-html` 生成默认的 HTML 方案，统一安装入口会将这项依赖一起纳入计划。

## 安装与使用

管理工具要求 Python 3.9+，只使用标准库；完整测试使用 Python 3.11。文档转换器首次运行时会准备自己的 Markdown 依赖。

```bash
git clone https://github.com/cgvcingcing/agent-skills.git
cd agent-skills

python3 manage.py list
python3 manage.py sync --dry-run
python3 manage.py sync
python3 manage.py check
```

安装后新开 agent 会话，在实际业务项目中使用技能。需求、原型和生成结果放在业务项目里，脚本与模板从已安装的技能目录读取。

日常修改和更新：

```bash
python3 manage.py status
python3 manage.py sync
python3 manage.py check
```

只更新一个技能或平台：

```bash
python3 manage.py sync test-handoff --platform claude --dry-run
python3 manage.py sync test-handoff --platform claude
python3 manage.py check test-handoff --platform claude
```

`install`、`update` 和 `sync` 都安装当前检出的源码版本。需要获取远程更新时，先处理本地修改并拉取总仓库，再运行 `sync`。

默认安装根目录沿用 `~/.codex`、`~/.claude` 和 `~/.zcode`，支持 `CODEX_HOME`、`CLAUDE_CONFIG_DIR`，也支持 `--codex-root`、`--claude-root`、`--zcode-root` 明确指定根目录。

## 状态与备份

`status` 显示源码提交、未提交状态和各平台的安装状态；加 `--json` 可查看缺失、修改和多出的文件。`check` 全部一致时退出码为 0，有差异时为 1，执行或配置错误时为 2。

| 状态 | 含义 |
| --- | --- |
| `ok` | 安装内容与源码一致，版本记录有效 |
| `missing` | 尚未安装 |
| `different` | 安装内容与当前源码存在差异 |
| `unrecorded` | 内容一致，尚未写入管理工具的版本记录 |
| `record_stale` | 版本记录需要更新 |
| `legacy_different` | Codex 兼容提示词入口需要同步 |
| `symlink` / `foreign` | 目标为软链接或其他内容，安装器会停止覆盖 |

安装副本中的 `.skill-manager.json` 记录总仓库提交和逐文件摘要。每次实际更新前，旧副本会保存在本地 `.state/backups/`，终端显示备份编号。更新中途失败时，会恢复已变更的目标。

需要恢复一次更新时：

```bash
python3 manage.py restore BACKUP_ID --dry-run
python3 manage.py restore BACKUP_ID
```

用实际备份编号替换 `BACKUP_ID`。恢复前也会备份当前版本；原先没有安装的目标会恢复为不存在。自定义过平台根目录时，恢复命令使用相同参数。

## 目录与维护方式

```text
agent-skills/
├── manage.py
├── skills.json
├── source-lock.json
├── scripts/check_workspace.py
├── tests/
├── ci/check-workflow.yml
├── doc2html-skill/
├── interaction-flow/
├── spec2testplan-skill/
├── test-analysis-framework/
└── test-handoff/
```

以后在这个总仓库修改技能、检查后提交。原仓库保留用于查阅历史；总仓库中的修改不自动回写原仓库。新增或调整安装资源时，同步更新 `skills.json`。

完整检查：

```bash
python3 scripts/check_workspace.py
```

检查会运行管理工具和各项目现有测试，再在临时目录验证全部平台的安装、版本记录和重复更新。

`ci/check-workflow.yml` 提供 GitHub Actions 配置模板。当前发布凭据缺少 `workflow` 权限，因此自动检查尚未启用。使用具有工作流写权限的凭据后，将模板复制到 `.github/workflows/check.yml` 并提交，即可在提交和拉取请求时运行相同检查。

## 导入来源

本仓库采用五个本地源项目的当前内容，包含用户确认纳入的未提交技能修改。导入共 82 个源文件；业务材料、历史报告、IDE 设置、Git 元数据和依赖缓存留在本地。

原仓库与基准提交、纳入的未提交文件及文件摘要记录在 [source-lock.json](source-lock.json)。原始提交历史保留在各来源仓库，导入后的修改由本仓库统一记录。

| 原仓库 | 总仓库中的目录 |
| --- | --- |
| [doc2html-skill](https://github.com/cgvcingcing/doc2html-skill) | `doc2html-skill/` |
| [interaction-flow](https://github.com/cgvcingcing/interaction-flow) | `interaction-flow/` |
| [spec2testplan-skill](https://github.com/cgvcingcing/spec2testplan-skill) | `spec2testplan-skill/` |
| [test-analysis-framework](https://github.com/cgvcingcing/test-analysis-framework) | `test-analysis-framework/` |
| [test-handoff](https://github.com/cgvcingcing/test-handoff) | `test-handoff/` |
