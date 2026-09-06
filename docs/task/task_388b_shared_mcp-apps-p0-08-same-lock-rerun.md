<!-- [输入] 当前 pnpm lock 下的 P0-02—P0-07 证据和 P0-04 重验。 -->
<!-- [输出] 唯一 P0-08 Go/No-Go 的技术判定规则。 -->
<!-- [定位] 历史 Task；当前判定由 task_411-03 承接。 -->
<!-- [同步] 2026-09-06：按同 lock 证据、一致性与生产关闭边界重建。 -->

# task_388b：P0-08 同 lock 重验

当前执行入口：[task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md)。

P0-08 只能基于同一当前候选的源码、pnpm lock、Chrome、Browser 入口和官方制品：

- P0-04 当前运行全部通过；
- P0-02/P0-03/P0-05/P0-06/P0-07 证据与当前指纹一致；
- trace 脱敏且可回读；
- 首次工具调用计数为 1；
- fallback、teardown 和 production-off 事实明确。

任一条件缺失、过期、异 lock 或真实失败即 No-Go。Go 只允许继续 Phase 1 当前候选验收，不启动 Phase 1 实现，不启用 production Apps，也不代表真实外部 Server 通过。
