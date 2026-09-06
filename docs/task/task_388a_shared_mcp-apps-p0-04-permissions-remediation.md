<!-- [输入] DEC-002 与旧 npm lock 下的 P0-04 浏览器证据。 -->
<!-- [输出] P0-04 历史修复合同和当前 pnpm 候选的重验要求。 -->
<!-- [定位] 历史 Task；当前重验由 task_411-03 承接。 -->
<!-- [同步] 2026-09-06：保留权限、安全、生命周期和 no-replay 合同。 -->

# task_388a：P0-04 权限传播历史修复

旧候选曾验证最小 `ImMcpAppHostAdapter` 在 outer iframe 导航前写入 immutable sandbox/allow，并由 proxy 向 inner iframe应用相同策略。历史证据覆盖 requested/desired/effective/revision、geolocation 正向 probe、camera 拒绝、非法来源、teardown 和 no-replay。

当前 pnpm 候选必须在 [task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md) 中重新运行：

- 固定当前 pnpm lock、renderer/AppBridge/Playwright 和 Chrome 指纹；
- 验证两层 iframe allow、proxy `Permissions-Policy` 与 Host capabilities 一致；
- 验证允许与拒绝的真实 Web API 行为；
- 验证 invalid origin/message/policy/revision 拒绝；
- 验证 close、refresh、Thread switch、禁用和 revision 变化的 teardown；
- 证明首次工具调用没有重放；
- 保持普通结果和 production Apps 关闭。

旧 npm lock 证据不能替代当前运行。
