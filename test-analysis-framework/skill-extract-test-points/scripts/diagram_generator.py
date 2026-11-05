#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mermaid 图表生成器
自动生成测试点分析中需要的各种 Mermaid 图表
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import argparse
import json
from pathlib import Path


class DiagramType(Enum):
    """图表类型枚举"""
    TREE = "tree"  # 功能模块树图
    FLOWCHART = "flowchart"  # 业务流程图
    SEQUENCE = "sequence"  # 接口调用时序图
    STATE = "state"  # 状态转换图
    PIE = "pie"  # 饼图


@dataclass
class ModuleNode:
    """模块节点"""
    id: str
    name: str
    children: List['ModuleNode'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class FlowStep:
    """流程步骤"""
    id: str
    text: str
    type: str = "process"  # process, decision, start, end
    next_steps: List[str] = None
    condition: Optional[str] = None  # 用于 decision 类型
    next_conditions: Dict[str, str] = None  # 每条出边的条件

    def __post_init__(self):
        if self.next_steps is None:
            self.next_steps = []
        if self.next_conditions is None:
            self.next_conditions = {}


@dataclass
class APICall:
    """接口调用"""
    from_actor: str
    to_actor: str
    message: str
    is_return: bool = False


@dataclass
class StateTransition:
    """状态转换"""
    from_state: str
    to_state: str
    event: str


class MermaidDiagramGenerator:
    """Mermaid 图表生成器"""

    def __init__(self):
        self.node_counter = 0

    def _get_node_id(self) -> str:
        """生成唯一节点 ID"""
        self.node_counter += 1
        return f"N{self.node_counter}"

    def generate_tree_diagram(self, root: ModuleNode, direction: str = "TD") -> str:
        """
        生成功能模块树图

        Args:
            root: 根节点
            direction: 方向 TD(上到下) / LR(左到右)

        Returns:
            Mermaid 图表代码
        """
        lines = [f"graph {direction}"]

        def traverse(node: ModuleNode, parent_id: Optional[str] = None):
            node_id = self._sanitize_id(node.id)
            node_text = self._escape_text(node.name)

            lines.append(f"    {node_id}[{node_text}]")
            if parent_id:
                lines.append(f"    {parent_id} --> {node_id}")

            for child in node.children:
                traverse(child, node_id)

        traverse(root)
        return "\n".join(lines)

    def generate_flowchart(self, steps: List[FlowStep], direction: str = "TD") -> str:
        """
        生成业务流程图

        Args:
            steps: 流程步骤列表
            direction: 方向 TD / LR

        Returns:
            Mermaid 图表代码
        """
        lines = [f"flowchart {direction}"]

        for step in steps:
            step_id = self._sanitize_id(step.id)
            step_text = self._escape_text(step.text)

            # 根据类型生成不同形状的节点
            if step.type == "start":
                lines.append(f"    {step_id}([{step_text}])")
            elif step.type == "end":
                lines.append(f"    {step_id}([{step_text}])")
            elif step.type == "decision":
                lines.append(f"    {step_id}{{{step_text}}}")
            else:  # process
                lines.append(f"    {step_id}[{step_text}]")

            # 添加连接关系
            for next_id in step.next_steps:
                next_id_clean = self._sanitize_id(next_id)
                condition = step.next_conditions.get(next_id) or step.condition
                if condition:
                    lines.append(f"    {step_id} -->|{self._escape_text(condition)}| {next_id_clean}")
                else:
                    lines.append(f"    {step_id} --> {next_id_clean}")

        return "\n".join(lines)

    def generate_sequence_diagram(self, calls: List[APICall], actors: List[str]) -> str:
        """
        生成接口调用时序图

        Args:
            calls: 接口调用列表
            actors: 参与者列表

        Returns:
            Mermaid 图表代码
        """
        lines = ["sequenceDiagram"]

        # 声明参与者
        for actor in actors:
            actor_clean = self._sanitize_actor(actor)
            lines.append(f"    participant {actor_clean} as {actor}")

        # 添加调用关系
        for call in calls:
            from_actor = self._sanitize_actor(call.from_actor)
            to_actor = self._sanitize_actor(call.to_actor)
            message = self._escape_text(call.message)

            if call.is_return:
                lines.append(f"    {from_actor}-->>{to_actor}: {message}")
            else:
                lines.append(f"    {from_actor}->>{to_actor}: {message}")

        return "\n".join(lines)

    def generate_state_diagram(self, transitions: List[StateTransition]) -> str:
        """
        生成状态转换图

        Args:
            transitions: 状态转换列表

        Returns:
            Mermaid 图表代码
        """
        lines = ["stateDiagram-v2"]

        # 收集所有状态
        states = set()
        for trans in transitions:
            states.add(trans.from_state)
            states.add(trans.to_state)

        # 添加转换关系
        for trans in transitions:
            from_state = self._sanitize_state(trans.from_state)
            to_state = self._sanitize_state(trans.to_state)
            event = self._escape_text(trans.event)

            if trans.from_state == "[*]" or trans.to_state == "[*]":
                # 起始或结束状态
                lines.append(f"    {from_state} --> {to_state}")
            else:
                lines.append(f"    {from_state} --> {to_state}: {event}")

        return "\n".join(lines)

    def generate_pie_chart(self, title: str, data: Dict[str, int]) -> str:
        """
        生成饼图

        Args:
            title: 图表标题
            data: 数据字典 {标签: 数值}

        Returns:
            Mermaid 图表代码
        """
        lines = [f'pie title {title}']

        for label, value in data.items():
            label_clean = self._escape_text(label)
            lines.append(f'    "{label_clean}" : {value}')

        return "\n".join(lines)

    def _sanitize_id(self, text: str) -> str:
        """清理 ID，移除特殊字符"""
        cleaned = "".join(c if c.isalnum() or c == "_" else "_" for c in str(text))
        return cleaned or "node"

    def _sanitize_actor(self, text: str) -> str:
        """清理参与者名称"""
        return text.replace(" ", "_").replace("-", "_")

    def _sanitize_state(self, text: str) -> str:
        """清理状态名称"""
        if text == "[*]":
            return text
        return text.replace(" ", "_").replace("-", "_")

    def _escape_text(self, text: str) -> str:
        """转义文本中的特殊字符"""
        # Mermaid 中需要转义的字符
        return text.replace('"', '\\"')


def _load_input(value: str) -> Any:
    """读取 JSON 文件或直接传入的 JSON 文本。"""
    path = Path(value)
    if path.exists() and path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"text": value}


def _diagram_from_data(data: Any, diagram_type: str) -> str:
    generator = MermaidDiagramGenerator()
    if isinstance(data, str):
        data = {"text": data}
    if not isinstance(data, dict):
        raise ValueError("图表输入必须是 JSON 对象")

    if diagram_type == "tree":
        def node(item: Dict[str, Any], fallback: str) -> ModuleNode:
            return ModuleNode(str(item.get("id", fallback)), str(item.get("name", item.get("text", fallback))),
                              [node(child, f"{fallback}_{i}") for i, child in enumerate(item.get("children", []), 1)])
        return generator.generate_tree_diagram(node(data, "root"), data.get("direction", "TD"))
    if diagram_type == "flowchart":
        raw_steps = data.get("steps")
        if not raw_steps:
            raw_steps = [{"id": "input", "text": data.get("text", "需求"), "type": "process"}]
        steps = [FlowStep(str(s["id"]), str(s.get("text", s["id"])), str(s.get("type", "process")),
                          list(s.get("next_steps", [])), s.get("condition"), dict(s.get("next_conditions", {})))
                 for s in raw_steps]
        return generator.generate_flowchart(steps, data.get("direction", "TD"))
    if diagram_type == "sequence":
        calls = [APICall(str(c["from_actor"]), str(c["to_actor"]), str(c.get("message", "")), bool(c.get("is_return", False)))
                 for c in data.get("calls", [])]
        return generator.generate_sequence_diagram(calls, [str(a) for a in data.get("actors", [])])
    if diagram_type == "state":
        transitions = [StateTransition(str(t["from_state"]), str(t["to_state"]), str(t.get("event", "")))
                       for t in data.get("transitions", [])]
        return generator.generate_state_diagram(transitions)
    if diagram_type == "pie":
        return generator.generate_pie_chart(str(data.get("title", "统计")), {str(k): int(v) for k, v in data.get("data", {}).items()})
    raise ValueError(f"不支持的图表类型: {diagram_type}")


def cli() -> int:
    parser = argparse.ArgumentParser(description="生成 Mermaid 图表")
    parser.add_argument("--input", required=True, help="JSON 文件路径、JSON 文本或普通文本")
    parser.add_argument("--type", choices=[item.value for item in DiagramType], required=True)
    parser.add_argument("--output", required=True, help="输出 .mmd 文件")
    args = parser.parse_args()
    try:
        diagram = _diagram_from_data(_load_input(args.input), args.type)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(diagram + "\n", encoding="utf-8")
        print(f"已生成 Mermaid 图表: {output}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"生成失败: {exc}")
        return 1


def demo():
    """演示各种图表的生成"""
    generator = MermaidDiagramGenerator()

    print("=" * 60)
    print("1. 功能模块树图")
    print("=" * 60)

    # 示例：功能模块树
    root = ModuleNode(
        id="system",
        name="订单系统",
        children=[
            ModuleNode(
                id="order",
                name="订单管理",
                children=[
                    ModuleNode(id="create", name="创建订单"),
                    ModuleNode(id="query", name="查询订单"),
                    ModuleNode(id="cancel", name="取消订单"),
                ]
            ),
            ModuleNode(
                id="payment",
                name="支付管理",
                children=[
                    ModuleNode(id="pay", name="在线支付"),
                    ModuleNode(id="refund", name="退款"),
                ]
            ),
        ]
    )

    tree_diagram = generator.generate_tree_diagram(root, direction="TD")
    print(f"```mermaid\n{tree_diagram}\n```\n")

    print("=" * 60)
    print("2. 业务流程图")
    print("=" * 60)

    # 示例：登录流程
    steps = [
        FlowStep(id="start", text="开始", type="start", next_steps=["input"]),
        FlowStep(id="input", text="用户输入账号密码", type="process", next_steps=["validate"]),
        FlowStep(id="validate", text="校验通过?", type="decision", next_steps=["success", "error"]),
        FlowStep(id="success", text="登录成功", type="process", next_steps=["end"]),
        FlowStep(id="error", text="显示错误提示", type="process", next_steps=["input"]),
        FlowStep(id="end", text="结束", type="end"),
    ]

    # 为 decision 节点添加条件
    steps[2].condition = "是"  # validate -> success

    flowchart = generator.generate_flowchart(steps, direction="TD")
    print(f"```mermaid\n{flowchart}\n```\n")

    print("=" * 60)
    print("3. 接口调用时序图")
    print("=" * 60)

    # 示例：下单接口调用链
    actors = ["App", "Node聚合", "订单服务", "库存服务"]
    calls = [
        APICall("App", "Node聚合", "POST /order/create"),
        APICall("Node聚合", "订单服务", "POST /v6/order/create"),
        APICall("订单服务", "Node聚合", "返回订单ID", is_return=True),
        APICall("Node聚合", "库存服务", "PUT /v6/inventory/deduct"),
        APICall("库存服务", "Node聚合", "返回成功", is_return=True),
        APICall("Node聚合", "App", "返回订单创建成功", is_return=True),
    ]

    sequence = generator.generate_sequence_diagram(calls, actors)
    print(f"```mermaid\n{sequence}\n```\n")

    print("=" * 60)
    print("4. 状态转换图")
    print("=" * 60)

    # 示例：订单状态流转
    transitions = [
        StateTransition("[*]", "待支付", "创建订单"),
        StateTransition("待支付", "已支付", "支付成功"),
        StateTransition("待支付", "已取消", "超时/取消"),
        StateTransition("已支付", "已发货", "商家发货"),
        StateTransition("已发货", "已收货", "用户确认收货"),
        StateTransition("已收货", "[*]", "完成"),
        StateTransition("已取消", "[*]", "完成"),
    ]

    state_diagram = generator.generate_state_diagram(transitions)
    print(f"```mermaid\n{state_diagram}\n```\n")

    print("=" * 60)
    print("5. 饼图")
    print("=" * 60)

    # 示例：测试点优先级分布
    priority_data = {
        "P0 核心": 15,
        "P1 主要": 35,
        "P2 次要": 30,
        "P3 边缘": 20,
    }

    pie_chart = generator.generate_pie_chart("测试点优先级分布", priority_data)
    print(f"```mermaid\n{pie_chart}\n```\n")


if __name__ == "__main__":
    raise SystemExit(cli())
