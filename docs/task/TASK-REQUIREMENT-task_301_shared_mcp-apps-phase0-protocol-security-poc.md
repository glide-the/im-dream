<!-- [输入] task_301 历史合同、当前 pnpm 候选和 task_411-03。 -->
<!-- [输出] P0 当前候选重验的技术要求摘要。 -->
<!-- [定位] 历史 requirement；当前实施以 task_411-03 为准。 -->
<!-- [同步] 2026-09-06：按 P0-01—08 的可观察验收重建输入。 -->

# TASK-REQUIREMENT：Phase 0 当前候选重验

1. 从当前 `frontend/pnpm-lock.yaml` 记录 P0-01 版本与 digest。
2. 使用当前源码、唯一 Browser 入口和本机兼容 Chrome运行 P0-02—P0-07。
3. P0-03 必须证明首次工具调用计数为 1。
4. P0-04 必须证明 outer/inner iframe、sandbox、CSP/Permissions-Policy、权限正反向 probe、来源拒绝与 teardown。
5. P0-05/P0-06 必须给出实际 topology 和 fresh session 结论。
6. P0-07 必须证明 refresh 后 Apps identity 与完整 result 保留，且无 schema 变更。
7. 原位写唯一 P0-08 Go/No-Go；旧 npm lock 结果只作历史对照。
8. 记录命令、退出码、版本/lock/Chrome/入口指纹、脱敏证据和清理结果。
9. 不启用 production Apps，不修改普通 MCP/Chat 语义，不停止非本轮服务。

当前写入与完整验收边界见 [task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md) 和 [技术执行计划](../stage/stage_mcp-apps-system-architecture.md)。
