<!-- [输入] 当前 pnpm lock 下 P0-01—P0-07 证据和唯一 P0-08 决策。 -->
<!-- [输出] Phase 0 当前证据索引、适用边界与 production 关闭状态。 -->
<!-- [范围] 只索引 provider-free 技术证据；不启用 production Apps。 -->
<!-- [同步] 2026-09-06：完成同一 current pnpm/source/Chrome 候选的 P0 重验。 -->

# MCP Apps Phase 0 当前证据索引

| ID | 当前结果 | 证据 | 结论 |
|---|---|---|---|
| P0-01 | pass | `evidence/p0-01-dependency-lock.md` | 唯一 pnpm lock 与精确版本一致。 |
| P0-02 | pass | `evidence/p0-02-browser-protocol.md`、redacted JSON trace | Browser 只经 IM endpoint 使用标准 MCP。 |
| P0-03 | pass | `evidence/p0-03-app-renderer-once.md`、trace | 完成结果挂载且首次调用不重放。 |
| P0-04 | pass | `evidence/p0-04-security-isolation.md`、redacted JSON trace | 当前 Chrome 正反向隔离与 teardown 通过。 |
| P0-05 | pass | `evidence/p0-05-locality.md` | Node locality 边界实测完成。 |
| P0-06 | pass | `evidence/p0-06-fresh-session.md` | fresh session 不依赖原 Agent 连接私有状态。 |
| P0-07 | pass | `evidence/p0-07-chat-roundtrip.md` | 完整 identity/result 在 refresh/reconnect 保留，无 schema 变化。 |
| P0-08 | Go | `p0-08-decision.yaml` | 只允许继续 Phase 1 技术验收。 |

当前候选全程 `production_apps_effective=false`。完整统一回执见 [Phase 0—3 当前候选技术验收](../current-candidate-validation.md)。

回滚只清理本轮具名 PoC 进程、端口、fixture 和临时输出；普通 MCP/Chat、数据库和用户改动保持不变。
