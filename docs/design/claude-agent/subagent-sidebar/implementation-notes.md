# 子智能体任务展示实现记录

## 1. 数据与展示

- 后端按 thread workspace 扫描 `.claude-home/projects/**/subagents/*.meta.json` 与有界 JSONL 首尾，投影 `running/completed/failed/cancelled`、摘要、耗时、`tool_call_id` 和最多 80 条脱敏 activity。activity 只保留 assistant 文本、工具名、生命周期与时间，不下发 user prompt、thinking、工具输入或成功工具输出。
- 顶部入口显示最近 Agent 头像及运行/完成计数；详情以与 `FileSidebar` 同层的右侧 `<aside>` 展示 active/completed/ended 分组。
- 当前实现的桌面侧栏宽度为 `26rem`，与参考图的信息密度和任务摘要长度匹配；关闭态宽度与 `min-width` 均为 0。
- `ChatMessageList` 对 `Agent`/旧名 `Task` 工具单独路由，不显示包含 agentId 的内部 launch/result envelope。聊天流改为任务胶囊按钮，点击后打开详情栏并按 `toolCallId` 定位高亮。
- 侧栏任务行本身为按钮；点击后在同一 `<aside>` 内进入执行详情，聊天任务胶囊也直接选择对应任务。详情标题栏提供返回列表按钮，任务刷新时保持选中项，选中项消失时安全回退列表。

## 2. Parent 无后续回复事故

实测主 transcript 的顺序为：

1. Parent 调用 `Agent{run_in_background:true}`。
2. 工具立刻返回 async launch metadata。
3. Parent 输出“正在后台运行”并结束 SDK turn。
4. Subagent 数秒后完成；CLI 把 completion notification 写入 parent transcript。
5. 此时应用侧已经收到 terminal `ResultMessage` 并关闭 SSE/EventBus，没有 active parent model 消费 completion notification，因此不会自动产生后续回复。

同时，后台 child 的工具确认通道可能随 parent turn 关闭，导致 child Read 等工具收到拒绝并提前停止。

## 3. 当前约束

`agent_runner.py` 在 PreToolUse 与 can_use_tool 输入边界将 `Agent`/`Task` 的 `run_in_background` 固定为 `false`。这样 child 工具执行、child 结果和 parent 最终回复处在同一个 runner/SSE 生命周期内。

该约束优先保证 Chat 的“发起子任务 → 等待结果 → 主 Agent 汇总回复”闭环。若未来恢复真正后台执行，必须先提供服务端 completion watcher、可恢复 parent continuation turn、幂等通知消费和跨进程 EventBus 路由，不能只依赖 CLI transcript notification。
