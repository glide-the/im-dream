<!-- [输入] 旧 npm lock 下的 Phase 0 P0-01—P0-08 证据和 DEC-002。 -->
<!-- [输出] Phase 0 历史技术合同、旧证据边界与当前 pnpm 结果入口。 -->
<!-- [定位] 历史 Task；task_411-03 已完成当前重验。 -->
<!-- [同步] 2026-09-06：保留旧 P0 事实并链接已完成的当前 pnpm 证据。 -->

# task_301：MCP Apps Phase 0 协议与安全 PoC

当前结果入口：[task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md) 与 [Phase 0 当前证据](../exec/mcp-apps/phase-0/index.md)。

## 历史目标

在隔离、provider-free 环境完成 P0-01—P0-08，验证依赖锁、Browser→Node→Server 标准协议、resource 渲染一次性、iframe 权限、topology、fresh session 和 Chat roundtrip，并形成唯一 Go/No-Go。

## 历史证据边界

旧 npm lock 上的证据位于 [task_301 历史执行回执](../exec/exec_task_301_mcp-apps-phase0-protocol-security-poc.md)。这些证据证明当时的源码、lock、Chrome 和入口；DEC-005 改为 pnpm workspace 后，不能作为当前候选通过结论。

## 后续重验结果

[Phase 0 当前证据](../exec/mcp-apps/phase-0/index.md) 已在唯一 pnpm lock、当前 Browser 入口和同一候选上覆盖 P0-01—P0-07，并形成 P0-08 `Go`。该结论只允许继续技术 preview；公开应用与生产仍为 `No-Go`，`productionAppsEffective=false`。

## 回滚

只删除本轮隔离 PoC、trace 和具名临时资源；普通 MCP、Chat、数据库、用户数据与历史证据不变。
