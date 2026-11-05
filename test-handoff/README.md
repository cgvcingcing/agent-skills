# Test Handoff

把需求材料整理成开发可填写、测试可直接使用的提测交接表，输出为离线单文件 HTML。

表单覆盖测试范围、开测配置、服务入口、日志、数据库与测试数据。整体采用白底、细分隔线和统一字号，模块、场景与多条说明按编号展示。P0 / P1 / P2、风险、待填项和预期结果用小标签及重点文字区分，正文保持深色。支持栏目及记录折叠、点击编辑、本机暂存、增删与撤销、JSON 导入导出、保存填写版 HTML 和打印。

点击栏目标题可单独展开或收起，“交接内容”旁可展开或收起全部章节。收起后仍显示条目数、优先级摘要、确认状态与关键提示。混合范围标为“含 P0”，每组下方可展开查看依据。颜色集中用于小标签、面板标题和关键语句，章节和记录标题按统一的字号、字重排列。

01—06 每章的记录均可单独或批量折叠，包含业务范围、配置、服务、日志、数据库和测试数据。业务范围收起后保留名称、优先级、本次范围和开发补充状态；其他记录保留名称和相应的已填标记。“开发补充”有独立标题和完整宽度，正文与场景统一为 15px 深色，本次范围放在下方。

展开记录后按简短的小标题组织字段，多条说明使用编号和细分隔线。SQL、Mongo、接口示例和日志检索命令使用宽代码区；竖线、引号、变量名与换行保持完整。原始填写内容保留，名称可在记录底部的“编辑名称”中修改。收起后的“已填”标记表示有内容，测试结论仍以实际验证为准。

基本信息、发布安排、限制、交接说明和材料依据也可折叠，长版本信息和确认说明会完整换行。目录跳转和“定位待填”会自动展开对应栏目及记录。各组折叠状态分别在本浏览器记住，保存填写版 HTML 时也会带上。打印时自动展开全部内容及优先级依据，结束后恢复原来的阅读状态。

## 安装

需要 Python 3，无第三方运行依赖。在项目目录执行：

```bash
python3 install.py
```

默认安装到 `~/.claude/skills/test-handoff` 和 `${CODEX_HOME:-~/.codex}/skills/test-handoff`。安装副本包含同一套技能正文、脚本和模板。安装器仅更新自己管理的目录，不修改全局配置。

```bash
python3 install.py --platform codex
python3 install.py --platform claude
python3 install.py --uninstall
```

## 使用

在 Codex 中输入：

```text
$test-handoff 根据这份需求生成开发提测填写表，输出到原文件所在目录。
```

在 Claude Code 中输入：

```text
/test-handoff 根据这份需求生成开发提测填写表，输出到原文件所在目录。
```

名称为 `test-handoff`，也支持按“生成提测填写表”“优化测试交接表”等请求自动匹配。若当前会话未刷新技能列表，新开会话后使用。

## 直接生成

```bash
python3 scripts/render_form.py --input examples/handoff.json -o example.html
python3 scripts/render_form.py --blank --title "需求名称" -o handoff.html
python3 scripts/render_form.py --from-html handoff.html -o handoff.html
python3 scripts/render_form.py --extract handoff.html -o content.json
python3 scripts/render_form.py --input merged-answers.json --fresh-draft -o handoff.html
python3 scripts/render_form.py --from-html handoff.html --read-only -o handoff_readonly.html
```

示例使用虚构业务数据，供了解字段格式。真实服务、库表、查询和优先级需要有材料依据；未知内容保留给开发填写。格式说明见 [references/form-data.md](references/form-data.md)。

只优化样式时会保留内嵌数据及文档 ID。将旧表已填写的答案迁入另一份模板时，以已填写文件为准，保留原文、行 ID、优先级、确认说明和限制条件；使用 `--fresh-draft` 生成新的暂存标识，避免浏览器旧草稿覆盖迁入内容。仍写着“待填写”的过期说明也要一并核对。

浏览器内尚未导出的填写内容会在原浏览器恢复；分享前点击“保存填写版 HTML”。旧自定义页面中不在内嵌数据里的说明，需要补入 JSON 后再生成。

引用 `test-handoff` 时，默认按正常流程生成或修改可编辑表单。只有主动要求“升级成只读版”“改成只读”或“把填写好的内容转成只读版本”，才执行只读收尾；仅说“已填好”“已确认”“最终版”或“升级样式”不会触发。讨论只读功能或修改技能规则，也不会转换 HTML 文件。已是只读版的文件在调整样式时继续保留只读状态。

只读收尾使用 `--read-only`。已填内容、优先级和确认说明原样保留，正文可选中复制，目录、折叠和打印照常使用；编辑、增删、导入和草稿恢复会停用。只读表示版本已锁定，测试结果仍以实际验证为准。默认另存只读版；覆盖原文件时先留可编辑备份。

## 项目文件

`SKILL.md` 是两平台共用的入口；`agents/openai.yaml` 提供 Codex 展示信息；`scripts/` 负责生成；`assets/` 保存离线模板；`references/` 说明数据格式；`examples/` 提供示例。

运行检查：

```bash
python3 -m unittest discover -s tests -v
```
