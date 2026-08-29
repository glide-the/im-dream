# Notion 数据库查询参考

读取 `.notion/databases/<database_id>.json` 浏览当前 thread 已挂载数据库的页面 ID 清单。`database_id` 必须来自 `.notion/databases.json`。

该文件包含 `pages` 数组及 snapshot identity，只用于定位页面，不包含页面正文。需要某一行的完整正文时读取 `.notion/pages/<page_id>.json`，Runtime hook 会按需返回 Markdown。

当前正式协议不支持 Agent 自行构造任意远程 filter/sorts；如索引信息不足，应向用户说明并使用已挂载清单，不得通过 CLI、HTTP 或凭证文件绕过选择范围。
