# 子智能体任务展示实现记录

## 0. 2026-08-05 对话详情架构决策

- 不嵌套 `ChatPanel`：它拥有 `useChat`、输入区、工具确认、SSE 重连、发送/停止与滚动控制，会造成重复生命周期和线程状态污染。
- 不直接原样嵌入现有 `ChatMessageList`：当前组件会订阅父线程 SubAgent store，并带有交互式工具确认/编辑语义。实现应提取或参数化最小的 `ReadonlyMessageTimeline`，共享 Markdown、代码、工具展示组件，但不共享 transport 和写操作。
- 后端当前 `activity` 主动剔除 prompt、thinking、工具输入和成功结果，只能支持调试式时间线，不能满足真实对话。新增 `messages` 安全投影后，`summary/activity` 仅用于旧记录兼容。
- 原始 JSONL 记录顺序是事实来源；投影为每个可见 block 生成稳定 id/sequence，保留 tool call/result 关联，限制单条/总字节数并标注脱敏、截断与投影版本。
- 前端标准化逻辑必须是纯函数，负责 schema guard、稳定排序、重复事件折叠、迟到事件防回退和 legacy fallback；UI 不从自然语言猜测状态或最终结果。
- foreground 约束继续保留：Agent/Task 的 `run_in_background` 在 PreToolUse 与 can-use-tool 两条权限路径改为 `false`，使 child result 与 parent 最终回复保持同一 runner/SSE 生命周期。未来如恢复真正后台执行，必须先实现持久 completion watcher 与可恢复 parent continuation。

### 预计代码边界

| 文件 | 变更 |
| --- | --- |
| `backend/claude_agent/subagent_projection.py` | 新增安全 `messages` 投影、稳定 id/顺序、截断/兼容元数据 |
| `backend/tests/test_claude_agent_subagents.py` | 覆盖派发、文本、工具、终态、重复/未知/截断与旧记录 |
| `frontend/src/hooks/useThreadSubagents.ts` | 新消息类型、标准化/排序/legacy 转换 |
| `frontend/src/components/chat/ChatMessageList.tsx` | 提取或参数化只读消息渲染边界 |
| `frontend/src/components/chat/SubagentPanel.tsx` | 紧凑列表、header、只读时间线与状态反馈 |
| `frontend/src/i18n.ts` | 新增中英文消息/兼容/状态文案 |
| `.folder.md` | 同步共享组件与数据职责 |

## 1. 数据与展示

- 后端按 thread workspace 扫描 `.claude-home/projects/**/subagents/*.meta.json` 与有界 JSONL 首尾，投影 `running/completed/failed/cancelled`、摘要、耗时、`tool_call_id` 和最多 80 条脱敏 activity。activity 只保留 assistant 文本、工具名、生命周期与时间，不下发 user prompt、thinking、工具输入或成功工具输出。
- 顶部入口显示最近 Agent 头像及运行/完成计数；详情以与 `FileSidebar` 同层的右侧 `<aside>` 展示 active/completed/ended 分组。
- 当前实现的桌面侧栏默认宽度为 `30rem`（480px），左侧 resize rail 可拖动到约 352–768px，并根据 viewport 保留至少 360px 聊天区；宽度持久化到 localStorage，双击恢复默认值。关闭态宽度与 `min-width` 均为 0。
- `ChatMessageList` 对 `Agent`/旧名 `Task` 工具单独路由，不显示包含 agentId 的内部 launch/result envelope。聊天流改为任务胶囊按钮，点击后打开详情栏并按 `toolCallId` 定位高亮。
- 侧栏任务行本身为按钮；点击后在同一 `<aside>` 内进入执行详情，聊天任务胶囊也直接选择对应任务。详情标题栏提供返回列表按钮，任务刷新时保持选中项，选中项消失时安全回退列表。
- “最新结果”保留 assistant 最终文本中的 Markdown 换行，并复用聊天正文的 `ChatMarkdown` + `prose prose-chat` 渲染链；GFM 列表、标题、表格、代码块、链接和 Mermaid 与 `ChatMessageList` 行为一致。
- 详情栏采用系统无衬线操作界面字体，标题、元信息、Markdown 结果与 activity 时间线分别提升到清晰的字号层级；resize rail 支持 Pointer Events、左右方向键（Shift 加速）、Home/End 和双击复位，并暴露 `role="separator"`/ARIA value。

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
