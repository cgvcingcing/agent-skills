# 流程模型与渲染约定

生成调用或消息时序泳道图时读取本文件。该模型用于表达参与方之间的交互，不作为普通业务流程或模块关系图的通用布局；这些图可按其目的直接绘制。分析仍以需求方案为准；脚本校验对象和图结构，不能证明业务正确或范围恰当。JSON 模型和渲染后的 SVG 都是临时文件，只用于生成最终单文件 HTML，验证后清理；来源和事实状态须随图或说明保留在 HTML 中。

## 模型

UTF-8 JSON 对象包含 `title`、`participants` 和 `steps`。参与方有唯一的 `id` 和显示 `label`，排列顺序由数组决定。`sources` 可记录图的整体来源。步骤有可选的稳定 `id`、`source` 和 `status`；`status` 为 `confirmed`（默认）、`assumption` 或 `unresolved`。后两种状态会在图上显示“假设”或“待确认”，来源会保留在 SVG 的悬停说明中。

`source` 使用能定位原材料的描述，例如“订单履约方案 §4.2”或“用户对审批分支的明确澄清”。模型里的说明不能代替没有提供的需求事实。纯排版标题不必独立引用。

| type | 必要字段 | 表达 |
| --- | --- | --- |
| `message` | `from`、`to`、`label` | 跨参与方交互，`mode` 为 `request`（默认）、`response`、`async` |
| `action` | `actor`、`label` | 参与方自身的处理或状态变化 |
| `note` | `label` | 条件、时点、完成标准或待确认说明 |
| `phase` | `label` | 阶段分隔，不代表系统动作 |
| `alt` | `branches` | 互斥条件分支，每个分支包含 `label` 和 `steps` |
| `parallel` | `branches` | 并行分支，每个分支包含 `label` 和 `steps` |
| `loop` | `label`、`steps` | 有材料支撑的循环或周期性处理 |
| `optional` | `label`、`steps` | 明确的可选处理 |

`message` 的两端必须是已声明且不同的参与方；同一参与方处理用 `action`。`alt` 和 `parallel` 至少有两个非空分支，分支里可嵌套动作、消息或其他组。未知 type、mode、status、参与方和重复步骤 ID 会报错，不会静默丢弃。

仅 `message` 和 `action` 按临时模型中的出现位置编号，或采用显式 `id`。条件分支中的编号用于定位，不表示两个互斥分支都会执行；并行分支之间也不因编号或上下排版形成先后关系。重复步骤与跨图衔接可用说明记录，不必复制整条链路。

`response` 用虚线箭头，`async` 用带圆点的箭头并标明“异步”，其他请求用实线箭头。异步消息仅表示这次交互的性质；接收后的业务处理、回调或结果事件仍需按材料建模。不要因画出发送箭头就认定接收或业务执行已经成功。

## 示例：纯服务链路

以下为演示图模型的虚构方案，不是项目需求。假定演示方案明确：结算服务发布事件，履约和通知服务独立消费；履约保存结果后发布结果事件，结算服务据此更新状态。只有真实材料包含这些规则时才能采用。

```json
{
  "title": "演示：结算事件后的服务协作",
  "sources": ["虚构演示方案，仅用于说明模型"],
  "participants": [
    {"id": "settlement", "label": "结算服务"},
    {"id": "events", "label": "事件通道"},
    {"id": "fulfilment", "label": "履约服务"},
    {"id": "notification", "label": "通知服务"}
  ],
  "steps": [
    {"type": "action", "actor": "settlement", "label": "结算完成，保存业务状态", "source": "演示方案：结算完成入口"},
    {"type": "message", "from": "settlement", "to": "events", "mode": "async", "label": "发布结算完成事件，携带 order_id", "source": "演示方案：关联字段"},
    {"type": "parallel", "branches": [
      {"label": "履约分支", "steps": [
        {"type": "message", "from": "events", "to": "fulfilment", "mode": "async", "label": "收到结算完成事件", "source": "演示方案：独立消费"},
        {"type": "action", "actor": "fulfilment", "label": "履约处理完成，保存结果", "source": "演示方案：履约结果"},
        {"type": "message", "from": "fulfilment", "to": "events", "mode": "async", "label": "发布履约完成事件，携带 order_id", "source": "演示方案：结果事件"},
        {"type": "message", "from": "events", "to": "settlement", "mode": "async", "label": "收到履约完成事件", "source": "演示方案：结算更新"},
        {"type": "action", "actor": "settlement", "label": "将履约状态更新为完成", "source": "演示方案：完成条件"}
      ]},
      {"label": "通知分支", "steps": [
        {"type": "message", "from": "events", "to": "notification", "mode": "async", "label": "收到结算完成事件", "source": "演示方案：独立消费"},
        {"type": "action", "actor": "notification", "label": "处理通知", "source": "演示方案：通知职责"}
      ]}
    ]},
    {"type": "note", "label": "演示方案以结算侧履约状态更新为完成，作为履约分支的结束信号；通知分支独立推进。", "source": "演示方案：范围和完成条件"}
  ]
}
```

## 渲染

定位本 SKILL.md 同目录的 `scripts/render_flow.py`，不要把本机用户名或项目根写进技能指令。输入模型和输出 SVG 均放在本次任务的专用临时目录。

```bash
python3 "<技能目录>/scripts/render_flow.py" "<临时目录>/flow.json" -o "<临时目录>/flow.svg"
```

`<技能目录>` 为本次加载的 `SKILL.md` 所在目录，`<临时目录>` 为本轮专用临时目录，执行前替换为实际路径，无需切换到技能安装目录。

默认图宽按参与方数量扩展，中文逐字换行，英文术语和事件编号尽量保持完整。过长的连续标识会提示缩短图中文字，把完整标识放在配套说明或宽幅 note 中；不要截断到改变含义。

参与方过多时优先按阶段或职责拆图；相邻图要保留一致的对象命名和衔接点。脚本支持单参与方的状态处理，也支持无人参与的服务链路。

SVG 和 JSON 均为过程文件。把 SVG 内嵌到最终 HTML，并将必要来源与事实状态保留在图或说明中；如用 Markdown 组装，组装稿也只放临时目录，验证后与图源一起清理。使用 Mermaid 等工具时也要检查实际渲染结果和分支语义，最终仍只保留一份离线 HTML。

## 语义检查

- C 端链路检查用户操作结束后是否还有系统处理，以及两者各自的结束点。
- B 端链路检查提交、审批、保存、发布、生效是否为不同状态，只保留方案规定的阶段。
- 微服务链路检查事件来源、关联实体、消费者职责、业务结果去向及最终完成信号；确认异步发送和局部成功没有被误当成整体成功。
- 所有链路都检查主干、条件分支和生命周期阶段能否衔接。缺少返回或完成信号时标出材料缺口，不补造 ACK、轮询、重试或补偿。
