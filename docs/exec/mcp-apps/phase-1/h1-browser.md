<!-- [输入] 当前 ToolMessagePart/result projection、Browser Client、Host adapter、sandbox route 与官方 AppServer。 -->
<!-- [输出] H1-01—H1-08 当前 lifecycle/security/visual evidence。 -->
<!-- [定位] Provider-free local-Chrome Browser evidence；不启用 production Apps。 -->
<!-- [同步] 2026-09-06：完成标准 DELETE、actor-effective shim 与 official `1.7.5` Host 验收。 -->

# H1 Browser Host 当前证据

- server-owned `mcpAppResult` 保留 `serverRef`、workspace scope、原始 tool、`toolCallId`、input、resource URI 和完整成功 `CallToolResult`；error result 只走普通 result/fallback。
- Browser Client 声明 UI extension capability，只连接同源 `/api/mcp-apps/{serverRef}`；Host 使用 `AppBridge`/`PostMessageTransport` 并独立读取 descriptor/resource，不重放首次工具。
- outer/inner iframe 都是 opaque `allow-scripts`，零 camera/microphone/geolocation/clipboard 权限；sandbox route 独立 origin、版本/revision 绑定、闭网 CSP 和严格 source/schema relay。
- close/reopen、refresh、Thread switch、runtime-policy-only `1:1→1:2`、plugin `1:2→2:2`、后续 lifecycle、feature disable→enable、forged source 和 teardown 都经过实际 Chrome；Host 等待 in-flight connect 后发送标准 DELETE，再关闭 Client；SDK initialize 先行 abort 时改用 fresh-signal bounded DELETE，Node adapter 也随 view expiry 回收无后续请求的 session。session/connector/lease 对应归零或归一，old Client 不跨 revision 复用。
- AppBridge 没有可自动转发的 Client；恶意 Phase 1 `tools/call` 得到 method-not-found 且上游调用数不变。Phase 2 低风险启用后才手动绑定 standard call。
- `ui/message` 到达 ToolMessagePart 的 Chat ingress；独立 coordinator 单测证明它与 composer/queued/retry 共用 conversation/editor/generation/dispatch 顺序。`window.im` 在认证 Host handshake 前不存在，之后也只暴露 actor-effective 的 sendFollowUpMessage/callTool/context；tool-only runtime-policy downgrade 会移除整个 `window.im` 而不降级 read-only Host。

Final command exit `0`：`3 passed (9.9s)`；真实 `unexpectedDiagnostics=[]`。Browser 请求仅落在 Host/sandbox origins，DOM、请求、配置和日志不含 relay URL 或 secret。预期的 opaque-origin localStorage denial、恶意调用 method-not-found、lifecycle 404/409 与插件禁用期 DELETE 503 单独计为正向证据。另一个隔离 actual-Chrome regression 验证 actor-effective tool-only `window.im`：exit `0`，`1 passed (1.6s)`。

运行期截图 `frontend/output/playwright/mcp-apps/official-1.7.5-production-host.png` 未纳入版本库（`1100×1026`、71,749 bytes、SHA-256 `86b1ff626509e5d8c5171c1f3a1bafa7b510a79603c98d3dac25b8a2e24be227`）。人工查看确认普通工具 Input/Output 卡和独立 Interactive tool result 面板同时可见，官方 Server Time、Get Server Time、Send Message、Send Log 均完成布局。
