<!-- [输入] 411-01 canonical root、DEC-002/004/005、Node/Host 设计和官方离线制品。 -->
<!-- [输出] sibling Node Runtime、薄 Route Handler、Python 最小投影、Chat result identity 和只读 Host 合同。 -->
<!-- [定位] 已完成 Phase 1 Runtime/Host 技术合同；不构成生产 Apps 许可。 -->
<!-- [同步] 2026-09-06：依据 54f3bbe5 与 C1/M1/H1 回执标记技术 preview 已完成。 -->

# task_411-02：MCP Apps Runtime、Route Handler 与只读 Host

配套 requirement：[TASK-REQUIREMENT-task_411-02_shared_mcp-apps-runtime-route-handler.md](./TASK-REQUIREMENT-task_411-02_shared_mcp-apps-runtime-route-handler.md)

## 当前状态

本工作项的 provider-free 技术 preview 已完成。`frontend/packages/mcp-apps-runtime/src/**` 是合法、独立、server-only 的唯一 Node Runtime owner；`frontend/app/api/mcp-apps/**` 只作薄 Route Handler，`frontend/app/_dream/**` 只拥有 Browser/Chat 模块。当前证据见 [C1/M1](../exec/mcp-apps/phase-1/c1-m1-contracts.md) 和 [H1](../exec/mcp-apps/phase-1/h1-browser.md)。真实外部 Server、凭证与生产运维尚未验收，`productionAppsEffective=false`。

## 1. 目标

建立唯一 `frontend/packages/mcp-apps-runtime/**` Node Runtime 和根 `frontend/app/api/mcp-apps/**` 薄 Route Handler；提供 Python 最小配置投影、server-owned Chat result identity、Browser Host、sandbox 和官方只读 demo 闭环。

## 2. 技术依赖

- 411-01 的根 workspace、单一 App Router 与现有业务行为成立。
- DEC-002 Host adapter/双 iframe、DEC-004 官方 demo、DEC-005 canonical tree。
- 官方 `server-basic-vanillajs@1.7.5` 的可回读离线 artifact。
- 当前 Backend/Node/Browser 测试工具和具名 run-owned scratch。
- `frontend/pnpm-lock.yaml` 在本工作项只读；最终重锁由 411-03 统一完成。

## 3. 实现范围

- `frontend/packages/mcp-apps-runtime/**`：contracts、config provider、SDK connector、process-scope manager、HTTP adapter、composition root 和 tests。
- `frontend/app/api/mcp-apps/**`、health/sandbox route：固定 Node runtime 的薄委派。
- `backend/claude_mcp/**` 与对应 router：服务身份、actor/workspace/Server/revision/expiry 和短时最小配置投影。
- Claude Agent/Chat 的最小 result identity producer、Public DTO、persistence 和 refresh consumer。
- `frontend/app/_dream/components/chat/mcp-apps/**` 与 `ToolMessagePart.tsx`：Browser Client、Host adapter、普通 fallback、双 iframe和生命周期。
- focused Backend/Node/Browser tests 和直接受影响的 docs/`.folder.md`。

## 4. 禁止范围

- `frontend/app/_dream/server/mcp-apps/**`、嵌套 Next、alias/dual-write、第二 manager 或 request-local manager。
- Browser 导入 server package、直连上游或接收 URL/headers/env/credential。
- 自建、patch、fork、vendor 官方 AppServer，或用旧 fixture 代替。
- Phase 2 正向页面调用、`ui/message`、`window.im`、新 Gateway/schema 和 production Apps。
- 改写 Agent turn、Thread、EventBus、SSE、resume/cancel、voice 或普通工具语义。

## 5. R2 验收

| ID | 验收 |
|---|---|
| R2-graph | 单向 package graph；server-only code 不进入 Browser/RSC bundle。 |
| R2-route | 标准 MCP GET/POST/DELETE、session、stream、cancel、close 与薄 Route Handler。 |
| R2-manager | process-scope manager；actor/workspace/Server/config/credential revision 隔离与复用。 |
| R2-python | 解密前拒绝越权、旧 revision、过期和禁用；只返回目标 Server 最小配置。 |
| R2-result-identity | server-owned binding 在 live、persisted、Public DTO、refresh 中一致；mismatch 只丢 Apps 投影。 |
| R2-official | 未修改官方 artifact 离线运行；Browser 零上游地址/credential。 |
| R2-host | descriptor/resource、双 iframe、sandbox/CSP、loading/error/fallback、refresh/reconnect 与 teardown。 |
| R2-negative | Phase 1 页面 `tools/call` 全拒绝且上游计数为零；非法 server/tool/URI/origin/message/revision 被拒绝。 |
| R2-gate | 当前候选 Backend/Node/Browser/Next 集成证据完整，production Apps 保持关闭。 |

## 6. 证据和生成物

测试 logs、screenshots、traces、tarball 解压、临时 HTML、端口和进程写入具名 run-owned scratch。既有 `frontend/.next/**` 和旧 exec/evidence 只作历史输入，不覆盖、不提交、不作为当前证据。

记录每个 R2 ID 的命令、退出码、关键输出、当前源码/制品/Browser 指纹、未运行项和清理结果。只停止或删除本轮记录的 PID、端口和 scratch。

## 7. 回滚

保持 production Apps 关闭，卸载 Host/iframe/Browser Client，拒绝旧 Node session，释放无引用 connector，并只删除本轮 Runtime/Route/Host 的可明确归属变更与资源。普通 MCP、Chat result、Python Agent turn、数据库和用户数据不变。
