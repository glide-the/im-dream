<!-- [输入] 旧 Phase 1 只读闭环合同、DEC-004/005 和当前 task_411-02。 -->
<!-- [输出] Phase 1 历史范围、废止输入与当前实现入口。 -->
<!-- [定位] 历史 Task；当前 Runtime/Host 实施由 task_411-02 承接。 -->
<!-- [同步] 2026-09-06：废止 self-built Server 实施入口，保留 N1/C1/S1/M1/H1 验收意图。 -->

# task_302：MCP Apps Phase 1 只读闭环历史合同

当前执行入口：[task_411-02](./task_411-02_shared_mcp-apps-runtime-route-handler.md)。

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

## 当前证据要求

当前候选必须同时提供 Backend、Node、Browser、Next standalone、官方离线制品和 result identity 的命令、退出码与可回读证据。无 Host、metadata 缺失、策略拒绝或 resource 失败时保留同次普通工具结果，不重放首次调用。
