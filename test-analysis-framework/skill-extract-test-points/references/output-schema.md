# 测试点输出契约

Skill 1 的机器可读结果必须包含一个 `test_points` 数组。每条测试点至少包含：

- `id`：唯一测试点 ID，例如 `TP-001`
- `title`：测试点标题
- `dimension_priority`：`P0` 到 `P3`
- `requirement_id`：需求 ID
- `requirement_source`：可追溯的原文位置
- `description`、`precondition`、`input`、`expected`
- `suggested_methods`：测试设计方法数组

推荐的顶层结构：

```json
{
  "metadata": {
    "requirement_name": "需求名称",
    "generated_at": "2026-09-28T12:00:00+08:00",
    "version": "1.0"
  },
  "test_points": []
}
```

事实与推断使用 `info_type`、`source_facts` 和 `confidence` 标记。没有证据的内容放入待确认问题，不要写进测试点事实字段。
