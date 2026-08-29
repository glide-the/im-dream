# Notion 搜索参考

读取 `.notion/index.json`，在当前 thread 已挂载的轻量索引中按 `title`、`page_id` 或 `url` 定位页面。不要用 Bash、外部 HTTP 请求或凭证文件访问 Notion。

索引只支持标题/ID/URL定位，不是正文全文搜索。找到目标 `page_id` 后，只有需要正文时才读取 `.notion/pages/<page_id>.json`。没有匹配项时说明“当前已挂载索引中没有结果”，不要扩大到未选择的 Notion 资源。
