<!-- [Sync] 2026-10-07: 独立评审修正一次total、updatedAt强上下文失效及observed/loaded/verification分别去重；最新background成功事实同步，仍待复核。 -->
<!-- [Input] 当前连接器同步策略、公开 DTO、Calendar 快照读取与2026-10-07正常服务观察。 -->
<!-- [Output] 可见面板版本发现、极简正文及跨进程同步恢复能力缺口的待评审合同。 -->
<!-- [Pos] Calendar 同步发现增量设计证据；正文合同归现行 PRD/正式稿。 -->
<!-- [Sync] 2026-10-07: 仅设计与源码诊断，尚未实施或验收；浮空修复另行执行。 -->
# 3 层级与逻辑增量

Optimized Prompt：映射真实DTO/状态owner，限定可见检查、并发和失败恢复。

公开connector DTO已有current_snapshot_version，前端normalizer新增nullable保留；reuse listConnectors(signal)、60秒日期timer。仅active/authenticated/document visible检查，完整context与成功loaded相同且无needsRead才不重读。任何updatedAt变化unknown，清空重读；同版本不能代许可。新版本重读本地documents，pending仅今天原索引ID校验；所有probe/read/verify均generation+context检查。hide取消probe，新读取不启动；完整同ctx才保留同日scroll/结果。observed检查记录与loaded成功记录分开，失败/409不推进loaded、不永久dedupe，只下一正常60秒周期或显式刷新再读；校验in-flight/完成键独立，不effect忙重试。临时错误/Retry-After、401/context清空沿用正式稿§4.6，不复制状态机。

syncing不是活跃writer证明；既有局部锁/operation timeout不能导出租约，自动恢复依赖Admin原子owner/lease/fencing。正式三图直接在稿内更新，前3图完整保存在pre-sync历史。
