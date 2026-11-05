# 测试分析框架 (Test Analysis Framework)

面向 Codex 的测试点提炼与测试用例生成工具集。

## 项目结构

```
test-analysis-framework/
├── skill-extract-test-points/      # Skill 1: 测试点提炼
├── skill-generate-test-cases/      # Skill 2: 测试用例生成
├── workspace/                       # 工作目录
│   ├── input/requirements/          # 需求输入
│   └── output/                      # 输出目录
└── README.md                        # 本文件
```

## 两个独立 Skill

### Skill 1: 测试点提炼 (extract-test-points)
从需求文档中提取结构化测试点，输出图文并茂的分析报告。

**输入格式**：
- 文档：Markdown, Word, PDF, Text
- 图片：PNG, JPG（原型图、截图）

**输出格式**：
- Markdown + Mermaid 图表（流程图、时序图、泳道图）
- 包含 JSON 数据块（供 Skill 2 使用）

**核心能力**：
- 8 维度测试点分类
- 自动生成可视化图表
- 需求追溯矩阵
- 覆盖度分析

### Skill 2: 测试用例生成 (generate-test-cases)
从测试点清单生成 XMind 思维导图格式的测试用例。

**输入格式**：
- 测试点清单（来自 Skill 1）
- 原始需求文档（独立使用）

**输出格式**：
- XMind 思维导图 (.xmind)

**核心能力**：
- 18 种测试设计方法
- 自动优先级判定
- 完整追溯关系
- 覆盖率验证

## 快速开始

### 在 Codex 中安装

把两个 skill 目录复制到 Codex 的 skill 目录（`CODEX_HOME` 未设置时使用 `~/.codex/skills`）：

```bash
./scripts/install_codex_skills.sh
```

重新打开 Codex 会话后，可以显式调用 `$extract-test-points` 或 `$generate-test-cases`，也可以使用“提炼测试点”“生成测试用例”等自然语言触发。两个目录里的 `agents/openai.yaml` 提供界面名称和默认提示词。

### 1. 提炼测试点

```bash
# 将需求文档放入工作目录
cp 你的需求.png workspace/input/requirements/

# 调用 Skill 1
在 Codex 中说："使用 $extract-test-points 分析 workspace/input/requirements 中的需求"
```

### 2. 生成测试用例

```bash
# Skill 1 输出会自动保存到 workspace/output/test-points/

# 调用 Skill 2
在 Codex 中说："使用 $generate-test-cases 根据测试点生成测试用例"
```

## 工作流

```
需求文档（截图/原型/PRD）
    ↓
[Skill 1] 测试点提炼
    ├─ 需求解析
    ├─ 测试点分类
    ├─ 图表生成
    ↓
测试点清单.md（含图表 + JSON）
    ↓
[用户评审/补充]
    ↓
[Skill 2] 测试用例生成
    ├─ 应用设计方法
    ├─ 生成用例
    ├─ 质量检查
    ↓
测试用例.xmind（思维导图）
```

## 脚本约定

- skill 脚本从各自 skill 目录解析，输入和输出从当前项目 `workspace/` 解析。
- XMind 输入统一支持用例数组和 `{ "test_cases": [...] }` 包装对象。
- Mermaid 生成器输出 Mermaid 文本，不负责渲染图片。
- 覆盖率检查会校验必填字段、步骤预期、重复用例 ID 和测试点覆盖率。

## 技术栈

- Python 3.11+
- 标准库（Mermaid 文本生成）
- pytesseract（OCR，可选）
- 标准库（XMind 生成）

## 许可

MIT License
# test-analysis-framework
