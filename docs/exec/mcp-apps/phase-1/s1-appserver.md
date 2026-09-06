<!-- [输入] 经验证离线缓存中的官方 `server-basic-vanillajs@1.7.5` 与上一版 `1.7.4`。 -->
<!-- [输出] S1-01 当前官方制品身份、协议、resource 和兼容矩阵证据。 -->
<!-- [定位] Provider-free official-artifact receipt；不代表真实业务 Server。 -->
<!-- [同步] 2026-09-06：以未修改官方发布制品替代旧 repo-owned fixture。 -->

# S1 官方 AppServer 证据

- 当前唯一目标：`@modelcontextprotocol/server-basic-vanillajs@1.7.5`，npm SHA-1 `855c0acd7df70d840b9fdb1bc0868a3f68288e7f`，本地制品 SHA-256 `4256fb45020e34a315733634779513572317885083a68eb6c1a3819e576f51ca`。
- 上一兼容目标：`1.7.4`；Inspector：`@modelcontextprotocol/inspector@2.5.0`。
- 官方源码、bundle、descriptor、resource 与 result 均未 patch/vendor；repo 只保存 artifact path/digest 和 provider-free harness。

当前与上一版都通过标准 Client `initialize`、`tools/list`、`resources/list`、`resources/read`、`tools/call` protocol smoke；Inspector CLI 的 `tools/list --app-info` 和 `resources/read` 得到 `get-time`、`ui://get-time/mcp-app.html`、标准 MCP App MIME 和原正文。

当前 `1.7.5` 还通过 Browser→真实 production Route Handler modules（由隔离 Vite HTTP adapter 加载）→Manager→audited relay→official Server 路径；实际 Next root shell 与 build/standalone 另有独立回执。Browser 不直接访问 relay/official endpoint，上游 header 只存在于 Node relay 侧；原始普通结果在无 Host 时仍可用。

Final Browser command exit `0`：`3 passed (9.9s)`（`1.7.4`/`1.7.5` protocol + `1.7.5` lifecycle）。
