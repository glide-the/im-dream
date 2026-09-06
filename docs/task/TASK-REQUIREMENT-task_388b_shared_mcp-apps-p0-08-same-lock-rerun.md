<!-- [输入] task_388b、当前 P0-02—P0-07 证据和唯一 P0-08 文件。 -->
<!-- [输出] P0-08 当前候选判定与证据写入要求。 -->
<!-- [定位] 已执行的历史 requirement；当前结果以 Phase 0 索引为准。 -->
<!-- [同步] 2026-09-06：链接已完成的同 lock 判定并保留唯一记录和回滚。 -->

# TASK-REQUIREMENT：P0-08 当前候选

> 本 requirement 已执行，不是新的派工入口。当前同 lock P0-08 为 `Go`，见 [Phase 0 当前证据索引](../exec/mcp-apps/phase-0/index.md)；该结果不启用 production Apps，`productionAppsEffective=false`。

1. 核对当前源码、pnpm lock digest、依赖版本、Chrome 和唯一 Browser 入口。
2. 重跑 P0-04，并核对 P0-02/P0-03/P0-05/P0-06/P0-07 的同指纹证据。
3. 记录每个 ID 的命令、退出码、关键输出、trace 路径和未运行原因。
4. 只原位更新唯一 P0-08 Go/No-Go；不创建平行 decision。
5. 条件不完整时写 No-Go 和具体失败事实，不用旧 npm lock、旧截图或设计文档补证。
6. 两种结论都保留 ordinary fallback、隔离清理和 `production_apps_effective=false`。
