<!-- [输入] DEC-002 与旧 npm lock 下的 P0-04 浏览器证据。 -->
<!-- [输出] P0-04 历史修复合同和当前 pnpm 候选结果入口。 -->
<!-- [定位] 历史 Task；task_411-03 已完成当前重验。 -->
<!-- [同步] 2026-09-06：保留安全合同并链接已完成的当前 P0-04 证据。 -->

# task_388a：P0-04 权限传播历史修复

旧候选曾验证最小 `ImMcpAppHostAdapter` 在 outer iframe 导航前写入 immutable sandbox/allow，并由 proxy 向 inner iframe应用相同策略。历史证据覆盖 requested/desired/effective/revision、geolocation 正向 probe、camera 拒绝、非法来源、teardown 和 no-replay。

当前 pnpm 候选已经在 [task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md) 中完成下列重验，实际结果见 [P0-04 当前证据](../exec/mcp-apps/phase-0/evidence/p0-04-security-isolation.md)：

- 固定当前 pnpm lock、renderer/AppBridge/Playwright 和 Chrome 指纹；
- 验证两层 iframe allow、proxy `Permissions-Policy` 与 Host capabilities 一致；
- 验证允许与拒绝的真实 Web API 行为；
- 验证 invalid origin/message/policy/revision 拒绝；
- 验证 close、refresh、Thread switch、禁用和 revision 变化的 teardown；
- 证明首次工具调用没有重放；
- 保持普通结果和 production Apps 关闭。

旧 npm lock 证据不能替代当前运行。当前 P0-04 为 pass，但只证明 provider-free 技术隔离；`productionAppsEffective=false`。
