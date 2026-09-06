<!-- [输入] 旧 npm lock 下的 Phase 0 P0-01—P0-08 证据和 DEC-002。 -->
<!-- [输出] Phase 0 历史技术合同及其在当前 pnpm 候选中的重验边界。 -->
<!-- [定位] 历史 Task；当前重验由 task_411-03 承接。 -->
<!-- [同步] 2026-09-06：保留 P0 验收、历史证据和当前重验入口。 -->

# task_301：MCP Apps Phase 0 协议与安全 PoC

当前执行入口：[task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md)。

## 历史目标

在隔离、provider-free 环境完成 P0-01—P0-08，验证依赖锁、Browser→Node→Server 标准协议、resource 渲染一次性、iframe 权限、topology、fresh session 和 Chat roundtrip，并形成唯一 Go/No-Go。

## 历史证据边界

旧 npm lock 上的证据位于 [Phase 0 索引](../exec/mcp-apps/phase-0/index.md)。这些证据证明当时的源码、lock、Chrome 和入口；DEC-005 改为 pnpm workspace 后，不能作为当前候选通过结论。

## 当前重验要求

- P0-01 必须记录唯一 pnpm lock digest 和实际依赖树。
- P0-04 必须在当前 Host adapter、sandbox proxy 和兼容 Chrome 上验证 requested/desired/effective/revision、两层 iframe、CSP/Permissions-Policy、正反向 probe 与 teardown。
- P0-02/P0-03/P0-05/P0-06/P0-07 必须核对当前源码、lock、Browser 和入口指纹。
- P0-08 只在同一候选证据完整时为 Go；任一必要条件失败即 No-Go。
- 所有结果保持 production Apps 关闭。

## 回滚

只删除本轮隔离 PoC、trace 和具名临时资源；普通 MCP、Chat、数据库、用户数据与历史证据不变。
