<!-- [输入] task_302 历史范围、DEC-002/004/005 与 task_411-02。 -->
<!-- [输出] Phase 1 当前候选的 N1/C1/S1/M1/H1 技术要求摘要。 -->
<!-- [定位] 历史 requirement；当前实施以 task_411-02 为准。 -->
<!-- [同步] 2026-09-06：废止 self-built Server，保留只读、zero-call、fallback 与安全证据。 -->

# TASK-REQUIREMENT：Phase 1 当前候选

- 只使用根 `frontend/app/**` 和 `frontend/packages/mcp-apps-runtime/**`。
- Python 只返回指定 actor/workspace/Server 的短时最小配置，并在解密前校验 identity/revision/expiry。
- Node Runtime 持有进程级 `PersistentConnectorManager`；Route Handler 只薄委派标准 MCP GET/POST/DELETE。
- 官方 demo 必须是未修改的 `server-basic-vanillajs@1.7.5`，可从完整只读离线 artifact 安装和运行。
- Chat result identity 必须由 server-owned producer 生成，并在 live、persisted、Public DTO、refresh/reconnect 中一致。
- Browser 只访问 IM 同源 endpoint；页面、日志和错误不含上游 URL、headers、env 或 credential。
- Phase 1 不声明页面工具调用能力；所有 App `tools/call` 在 Host/Node 拒绝且上游计数为零。
- Host adapter 持有双 iframe、sandbox snapshot、CSP/Permissions-Policy、来源校验和 teardown。
- 所有 fallback 保留同次 ordinary result，首次工具调用不得重放。
- 每项验证记录命令、退出码、当前 lock/制品/Browser 指纹和清理结果；生产 Apps 保持关闭。

详细写入闭集和 R2 验收见 [task_411-02](./task_411-02_shared_mcp-apps-runtime-route-handler.md)。
