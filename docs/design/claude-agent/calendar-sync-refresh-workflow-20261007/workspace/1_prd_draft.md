<!-- [Sync] 2026-10-07: 独立评审修正一次total、updatedAt强上下文失效及observed/loaded/verification分别去重；最新background成功事实同步，仍待复核。 -->
<!-- [Input] 当前连接器同步策略、公开 DTO、Calendar 快照读取与2026-10-07正常服务观察。 -->
<!-- [Output] 可见面板版本发现、极简正文及跨进程同步恢复能力缺口的待评审合同。 -->
<!-- [Pos] Calendar 同步发现增量设计证据；正文合同归现行 PRD/正式稿。 -->
<!-- [Sync] 2026-10-07: 仅设计与源码诊断，尚未实施或验收；浮空修复另行执行。 -->
# 1 PRD增量

Optimized Prompt：把同日快照不更新与文字拥挤转为可验证需求，复用当前索引/选择合同，不改变资源权限。

正常标题旁保留一次短total（partial明确已知数量）；正文为Refresh、非空组/标题链接/上游时间。partial0、连接错误和必要同步恢复保留；不显示常驻同步时间/coverage/重复计数/重复Open。版本检查仅可见，后台同步负责新资源发现。Admin缺owner/CAS/fencing，自动接管不属于当前可实施范围。正式规则直接在PRD§3.1，独立评审/代码/测试尚待。

复核修正：完整context含updatedAt，任何变化unknown并清空重读；不能以同版本代许可。observed/loaded/in-flight/verification分开，失败/409只下正常周期或显式刷新恢复。正常后台05:48已成功且今日UI可见，首次502和长期Admin依赖保留。
