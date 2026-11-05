# 清理脚本使用说明

## 快速使用

```bash
cd /path/to/test-analysis-framework
./clean.sh
```

## 功能说明

清理脚本提供 7 种清理选项：

### 1. 清理临时文件
- 路径：`workspace/tmp/`
- 清理内容：
  - `cases_*.json` - 测试用例 JSON 文件
  - `coverage_report_*.json` - 覆盖率报告
- 适用场景：清理生成过程中的临时数据

### 2. 清理测试点输出
- 路径：`workspace/output/test-points/`
- 清理内容：
  - `test-points-*.md` - 测试点分析报告
- 适用场景：重新生成测试点

### 3. 清理测试用例输出
- 路径：`workspace/output/test-cases/`
- 清理内容：
  - `test-cases-*.xmind` - XMind 测试用例文件
- 适用场景：重新生成测试用例

### 4. 清理所有输出文件
- 包含：测试点 + 测试用例 + 临时文件
- 适用场景：完全重新生成所有产物

### 5. 清理输入文件
- 路径：`workspace/input/requirements/`
- 清理内容：
  - 所有需求文档（`.md`, `.png`, `.jpg` 等）
- ⚠️ 需要二次确认
- 适用场景：更换需求文档

### 6. 完全重置工作区
- 清理所有文件（包括输入、输出、临时、记忆）
- 保留目录结构
- ⚠️ 需要输入 `RESET` 确认
- 适用场景：项目归档或重新开始

### 7. 查看当前文件统计
- 显示各目录的文件数量
- 不做任何清理操作

## 安全机制

### 二次确认
- **清理输入文件**：需要输入 `yes` 确认
- **完全重置**：需要输入 `RESET` 确认

### 保护机制
- 仅清理 `workspace/` 目录下的文件
- 不删除项目结构和配置文件
- 不影响 `skill-extract-test-points/` 和 `skill-generate-test-cases/` 目录

## 示例

### 示例 1：清理临时文件后重新生成测试用例
```bash
./clean.sh
# 选择: 1 (清理临时文件)
# 然后在 Codex 中重新运行 Skill 2
```

### 示例 2：完全重新开始
```bash
./clean.sh
# 选择: 6 (完全重置工作区)
# 输入: RESET
# 然后放入新的需求文档，重新运行 Skill 1 和 Skill 2
```

### 示例 3：查看文件统计
```bash
./clean.sh
# 选择: 7 (查看当前文件统计)
```

## 快速清理命令

如果你不想使用交互式菜单，可以直接执行命令：

```bash
# 清理临时文件
rm -rf workspace/tmp/*

# 清理测试点输出
rm -rf workspace/output/test-points/*

# 清理测试用例输出
rm -rf workspace/output/test-cases/*

# 清理所有输出
rm -rf workspace/tmp/* workspace/output/test-points/* workspace/output/test-cases/*
```

## 恢复误删的文件

如果不小心删除了重要文件，可以：

1. **从 Git 恢复**（如果文件已提交）：
```bash
git checkout -- workspace/output/test-points/
```

2. **从备份恢复**（如果有备份）

3. **重新生成**：
```bash
# 使用 Codex 重新运行 Skill 1 和 Skill 2
```

---

**版本**：v1.0  
**创建日期**：2026-09-08
