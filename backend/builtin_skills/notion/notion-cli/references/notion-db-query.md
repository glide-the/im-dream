<!-- [Source] glide-the/ink-and-memory develop e3523db9; bundled under notion-cli on 2026-08-30. -->
<!-- [Input] Selected data-source IDs, property schema and query parameters. -->
<!-- [Output] Current ntn data-source query and schema-read commands. -->
<!-- [Pos] notion-cli database query reference. -->
<!-- [Sync] 2026-11-11: align endpoints, identifiers and single-line JSON with the production read classifier. -->

# Notion Database Query 参考

> 查询指定 Notion Data source 下的页面（Row Page）。连接器索引的 `database_id` 字段保存所选 Data source ID。命令中的 `--data` 使用单引号包裹的单行 JSON 对象。

## 目录

1. [基本查询](#基本查询)
2. [筛选条件](#筛选条件)
3. [复合筛选](#复合筛选)
4. [排序](#排序)
5. [分页](#分页)
6. [获取 Schema](#获取-schema)
7. [属性筛选类型参考](#属性筛选类型参考)
8. [返回结果说明](#返回结果说明)

---

## 基本查询

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{}'
```

## 筛选条件

### 按 Status 属性筛选（select 类型）

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{"filter":{"property":"Status","select":{"equals":"In Progress"}}}'
```

### 按日期筛选

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{"filter":{"property":"Due","date":{"on_or_before":"2026-06-30"}}}'
```

### 按标题包含关键词筛选

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{"filter":{"property":"Name","title":{"contains":"重构"}}}'
```

## 复合筛选

### AND 条件

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{"filter":{"and":[{"property":"Status","select":{"equals":"In Progress"}},{"property":"Due","date":{"on_or_before":"2026-06-30"}}]}}'
```

### OR 条件

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{"filter":{"or":[{"property":"Status","select":{"equals":"In Progress"}},{"property":"Status","select":{"equals":"Not Started"}}]}}'
```

## 排序

```bash
ntn api v1/data_sources/<data_source_id>/query --data '{"sorts":[{"property":"Due","direction":"ascending"},{"timestamp":"last_edited_time","direction":"descending"}]}'
```

## 分页

```bash
# 限制返回数量
ntn api v1/data_sources/<data_source_id>/query --data '{"page_size":10}'

# 翻页（使用上一次返回的 next_cursor）
ntn api v1/data_sources/<data_source_id>/query --data '{"page_size":10,"start_cursor":"<next_cursor>"}'
```

## 获取 Schema

读取 Data source 的属性 Schema，取得可筛选的字段：

```bash
ntn api v1/data_sources/<data_source_id>
```

## 属性筛选类型参考

| 属性类型 | 筛选关键字 | 支持的条件 |
|---------|-----------|-----------|
| `title` | `title` | `equals`, `contains`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty` |
| `rich_text` | `rich_text` | 同上 |
| `number` | `number` | `equals`, `greater_than`, `less_than`, `greater_than_or_equal_to`, `less_than_or_equal_to` |
| `select` | `select` | `equals`, `does_not_equal`, `is_empty`, `is_not_empty` |
| `multi_select` | `multi_select` | `contains`, `does_not_contain`, `is_empty`, `is_not_empty` |
| `date` | `date` | `equals`, `before`, `after`, `on_or_before`, `on_or_after`, `is_empty`, `is_not_empty` |
| `checkbox` | `checkbox` | `equals` (true/false) |
| `status` | `status` | `equals`, `does_not_equal` |

## 返回结果说明

### `/v1/data_sources/<data_source_id>/query` 返回

| 字段 | 说明 |
|------|------|
| `results` | Page 数组，每项包含 `id`、`properties`（属性值）、`created_time`、`last_edited_time` |
| `has_more` | 是否有更多结果 |
| `next_cursor` | 下一页游标 |

### `/v1/data_sources/<data_source_id>` 返回

| 字段 | 说明 |
|------|------|
| `id` | Data source UUID |
| `title` | Data source 标题 |
| `properties` | 属性 Schema 定义（字段名 → 类型配置） |

## 工作流建议

1. **从 `.notion/connector.json` 或 `.notion/databases/<database_id>.json` 取得所选 Data source ID 和标题**
2. **用 `/v1/data_sources/<data_source_id>` 获取属性 Schema，了解可筛选的字段**
3. **根据用户需求构建 filter 条件查询**
4. **如需查看某条记录的完整内容，结合 `references/notion-page-read.md` 使用**

## 使用限制

- 单次查询最大 `page_size` 为 100，超过需分页
- filter 中的 `property` 值必须与 Data source Schema 中的属性名完全匹配（区分大小写）
- Data source ID 来自连接器索引的 `database_id` 字段；沿用现有字段名读取

## API 参考

- [Query a data source](https://developers.notion.com/reference/query-a-data-source)
- [Retrieve a data source](https://developers.notion.com/reference/retrieve-a-data-source)
