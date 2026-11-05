# 表单数据说明

渲染器接收 UTF-8 编码的 JSON。缺失字段留空，未提供的优先级使用 `待确认`。渲染器不从来源文件推导业务内容；由智能体读取材料并组织 JSON。

主章节和记录的折叠状态属于独立的浏览器阅读偏好，不属于回答或确认结论。六章都支持单条和批量折叠。偏好与数据 JSON 分开存储，并保留在导出的 HTML 标记中。记录偏好使用稳定的表名和行 ID；新增记录默认展开，删除记录时移除对应偏好。旧版仅包含存储或样例 ID 的偏好仍可兼容。JSON 导入导出保留匹配章节和记录的阅读状态；打印时临时展开全部层级、信息面板和来源依据。使用折叠功能无需增加 JSON 字段。

默认生成可编辑表单，即使所有章节都已确认也是如此。只有用户明确要求将已填写文件转为只读时，才使用 `--read-only`；填写完成或确认回答不会触发该模式。这个参数锁定用户提供的版本，保留其中的回答、ID 和确认状态。只读模式存放在 HTML 属性中，不是回答字段；后续使用 `--from-html` 渲染时会继续保留。只读版展示可选中复制的文字，不提供表单控件和编辑操作，也不恢复或保存回答草稿。其折叠偏好使用独立的浏览器键，浏览只读版不会改变可编辑表单的草稿。锁定版本不会把待确认章节改成已确认，也不表示测试通过。

## 主要字段

```json
{
  "meta": {"requirement": "示例项目", "change": "业务改动说明"},
  "tables": {
    "scope": [{
      "range": "业务范围",
      "module": "页面：功能 A、功能 B",
      "scenarios": "场景及预期结果\n另一场景及预期结果",
      "dependencies": "所需数据或开关",
      "priority": "待确认",
      "priorityNote": "",
      "decision": "待确认",
      "handoff": ""
    }]
  }
}
```

| 对象 | 字段 |
| --- | --- |
| `meta` | `requirement`, `ticket`, `environment`, `build`, `developer`, `tester`, `date`, `change` |
| `tables.scope` | `range`, `module`, `scenarios`, `dependencies`, `handoff`, `decision`, `priority`, `priorityNote` |
| `tables.config` | `key`, `purpose`, `reference`, `actual`, `operation` |
| `tables.services` | `name`, `role`, `entry`, `deployment`, `owner` |
| `tables.logs` | `scene`, `keywords`, `location`, `query`, `check` |
| `tables.database` | `object`, `storage`, `lookup`, `check`, `query` |
| `tables.samples` | `scene`, `example`, `expected`, `actual` |
| `extras` | `release`, `limits`, `conclusion` |

所有单元格的值都是字符串。模块之间使用 `、` 或换行分隔，以 `：` 结尾的简短前缀会成为页面标签。场景之间使用换行、中文分号或中文句号分隔；逗号仍保留在同一场景内。配置名称、接口入口和日志关键词使用换行分隔。SQL 可以写成多行，只作展示，不会执行。

所有记录采用白底、有标题的面板和统一的深色正文。模块、场景和其他密集内容显示为带浅分隔线的编号行。颜色仅用于小型语义标签和局部重点。SQL、Mongo 片段、HTTP 请求和日志检索命令使用宽代码区，开发准备说明中嵌入的查询也按此处理。这只改变展示方式，不进行查询校验；可编辑字符串和导出数据保持原样，命令始终不会执行。为保证排版可预期，命令单独成行，SQL 语句以分号结尾；引号内的分号留在同一语句中，管道符、引号、变量和反斜杠续行保留在命令内。标题显示的是已填状态，不是测试结果。记录原名称仍可通过“编辑名称”修改；带点号的配置前缀仅作视觉分隔，完整键名不变。

`priority` 可取 `待确认`、`含 P0`、`P0`、`P1`、`P2`。`decision` 可取 `待确认`、`本次必测`、`回归检查`、`不涉及`。两者分别记录。每个 `sections.<table-name>` 包含 `status`（`待补充`、`已确认` 或 `不涉及`）和字符串 `note`。没有依据时，不能把预填章节标为已确认。

标准化格式为 `test-handoff-form`，版本为 `1`。`documentId` 标识浏览器草稿，每行的 `_id` 用于编辑和删除。只调整样式时保留这些标识。使用另一份已填写文件替换模板内容时，保留该文件的行 ID，并通过 `--fresh-draft` 生成新文档 ID，避免旧草稿遮盖迁入的回答。新表单使用新 ID。浏览器导出包含完整的标准化结构。未包含优先级字段的旧导出仍可兼容；匹配的模板行提供优先级，没有匹配项时保留为待确认。

## 可选的展示说明

`_presentation` 保存项目专属的解释文字。这些内容留在数据文件中，通用技能资源不包含具体项目的信息。

```json
{
  "_presentation": {
    "badge": "示例数据 · 需要开发确认",
    "intros": {"config": "说明本项目的配置方式。"},
    "notices": {
      "config": [{"tone": "warning", "title": "开测前确认", "text": "确认本环境实际生效的配置值。"}],
      "database": [{"position": "after", "tone": "info", "title": "字段说明", "text": "响应字段仍需映射到真实存储。"}]
    },
    "modes": [{"label": "A", "title": "模式名称", "description": "适用条件", "config": "example.key=value", "recommended": false}],
    "sources": [{"name": "requirements.md §3", "note": "业务范围与验收标准"}]
  }
}
```

提醒默认放在相关表格前，设置 `position: "after"` 后放在表格后。配置模式可选，显示在配置表前；只有实际需求存在多种配置方式时才使用。全部展示内容都是纯文本，不接受 HTML。来源名称仅作为引用说明，不成为输出文件的外部依赖。

## 可选的行标签与重点标记

每行可以包含 `_display`。使用 `tag` 说明配置的作用，不能据此编造优先级。场景展示项按顺序对应拆分后的场景；标签概括原文，优先级标记与所属业务范围的优先级一样，需要有依据。

```json
{
  "_display": {
    "tag": {"text": "配置依赖", "tone": "warning"},
    "fields": {
      "scenarios": {
        "value": "原始场景文字",
        "items": [{
          "label": "可观察行为",
          "priority": "P0",
          "emphasis": [{"text": "关键短语", "tone": "critical"}]
        }]
      },
      "check": {
        "value": "原始检查说明",
        "emphasis": [{"text": "重点结果", "tone": "success"}]
      }
    }
  }
}
```

`tone` 可取 `critical`、`warning`、`info`、`success`。只有 `value` 与单元格文字完全一致时，展示元数据才生效，避免修改内容后仍把旧场景标签附在新文字上。展示元数据不改变原始字段值。重点标记集中在少量关键位置，避免整段着色。

## 更新旧自定义表单

`--extract` 只读取 `<script id="handoff-data" type="application/json">`。旧自定义表单可能在该脚本之外包含有用说明；重新渲染前检查这些说明，并迁入 `_presentation`。不要从原需求重新生成已填写表单而丢掉开发回答。仅保存在 localStorage 中的草稿没有嵌入磁盘文件；表单自身的 HTML 导出会嵌入当前回答，并使用新文档 ID 供分享。

迁移回答时，提取两份表单，根据字段内容识别已填写来源，不能只看文件名中的“new”等字样。迁移元信息、表格、章节确认、附加说明和展示元数据时，保留开发回答原文。按实际回答修正过期的 `_presentation` 提醒，同时保留部署与测试验证的限制说明。使用当前资源和 `--fresh-draft` 渲染后，将每个迁入字段与来源逐项比较。用户提供的来源文件保持原样。
