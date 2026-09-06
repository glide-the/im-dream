<!-- [输入] 旧 Phase 1 只读闭环合同、DEC-004/005 和后续 task_411-02 结果。 -->
<!-- [输出] Phase 1 历史范围、废止输入与当前技术证据入口。 -->
<!-- [定位] 历史 Task；task_411-02 的 canonical Runtime/Host 技术 preview 已完成。 -->
<!-- [同步] 2026-09-06：废止 self-built Server 入口，并链接当前 N1/C1/S1/M1/H1 结果。 -->

# task_302：MCP Apps Phase 1 只读闭环历史合同

当前结果入口：[task_411-02](./task_411-02_shared_mcp-apps-runtime-route-handler.md)、[Phase 1 当前证据](../exec/mcp-apps/phase-1/index.md) 与 [统一回执](../exec/mcp-apps/current-candidate-validation.md)。

## 保留的验收范围

- N1：根 Next workspace、单一 App Router、现有业务回归和 root standalone。
- C1：Python 服务身份、actor/workspace/Server/revision/expiry 与最小 secret 披露。
- S1：未修改的官方 `@modelcontextprotocol/server-basic-vanillajs@1.7.5`。
- M1：进程级 Runtime/Manager、同源标准 MCP endpoint、catalog 过滤、逐次重验、lifecycle 和脱敏诊断。
- H1：server-owned result identity、普通 fallback、Host adapter、双 iframe、sandbox/CSP、refresh/reconnect 和 teardown。
- Phase 1 页面工具调用为零；production Apps 始终关闭。

## 已废止输入

- repo-owned/self-built Phase 1 AppServer 与对应 fixture；
- `frontend/app/_dream/server/mcp-apps/**`；
- 嵌套 Next project 和旧 npm lock；
- 旧 Phase 1 screenshot、trace、decision 与 nested standalone 回执。

这些对象可用于历史追溯，不能作为当前实现、验收或回滚目标。

## 后续结果与当前边界

当前 canonical pnpm + official-AppServer 候选已提供 Backend、Node、Browser、Next standalone、官方离线制品和 result identity 的命令、退出码与可回读证据。无 Host、metadata 缺失、策略拒绝或 resource 失败时仍保留同次普通工具结果，不重放首次调用。

该完成状态只属于 provider-free 技术 preview；真实外部 Server、账号/OAuth、生产权限和运维回滚尚未验收，`productionAppsEffective=false`。
