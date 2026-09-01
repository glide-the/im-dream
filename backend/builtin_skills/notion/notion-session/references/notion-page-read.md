# Notion 页面读取参考

使用内置 `Read` 读取 `.notion/pages/<page_id>.json`。`page_id` 必须来自当前 thread 的 `.notion/index.json` 或 `.notion/databases/<database_id>.json`。

## 返回内容

- `markdown`：Runtime hook 实时读取的 Markdown 正文。
- `page_id`、`title`、`url`、`last_edited`：来自当前 thread 的轻量索引。
- `snapshot`：本次 ID 授权校验使用的索引版本。

## 调用示例

```text
Read(".notion/pages/<page-id>.json")
```

不要遍历或猜测 ID，也不要读取 `.notion-home`。hook 会拒绝不在 thread 索引中的 ID。`NOTION_AUTH_REQUIRED` 时请用户在“资源链接”中重新连接；`NOTION_PERMISSION_DENIED` 时请用户在 Notion 中授予目标页面权限。
