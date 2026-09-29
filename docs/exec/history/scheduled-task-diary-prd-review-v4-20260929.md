<!-- [Input] 现行 v4 Calendar/Chat PRD、结构骨架、UI/系统设计，及本轮 Calendar、Chat、ScheduledTask API 与 Tool 投影实现和验证回执。 -->
<!-- [Output] 定时任务 v4 的独立设计裁决、实施关闭审计、需求—设计—实现—测试追踪矩阵与剩余部署门禁。 -->
<!-- [Pos] v4 定时任务页面交互的现行评审和实现回执；v3 悬浮纸张视觉评审原文保存在 docs/exec/history。 -->
<!-- [Sync] 2026-09-29: v4 Calendar/Chat 纵向切片完成，独立设计结论保持“可直接实施”，并补录源码、类型、lint、build、Chrome 和后端合同回执。 -->

# 定时任务 Calendar / Chat v4 设计评审与实现关闭回执（2026-09-29）

## 文档导航

- [现行 PRD](../../prd/claude-agent/scheduled-task-diary-page-prd.md)
- [现行页面骨架](../../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)
- [现行 UI 设计与 HTML 原型](../../design/claude-agent/scheduled-task-diary-page-ui-design.md)
- [定时任务系统交互与执行设计](../../design/claude-agent/scheduled-task-loop-interaction-design.md)
- [上一版悬浮纸张视觉评审（历史）](./scheduled-task-diary-prd-review-v3-20260929.md)
- [更早的分卡评审与真实业务回执（历史）](./scheduled-task-diary-prd-review-v2-20260929.md)

## 1. 结论

**设计裁决：可直接实施。实施裁决：v4 页面纵向切片已完成并通过本轮技术验收。**

本轮实现覆盖五个用户界面：Calendar 顶部安排入口、轻量定时任务行、最近执行结果、独立编辑 Modal、Chat 内持久任务标记与右侧详情栏。实现继续使用既有 ScheduledTask day/get/history/update 接口、`create_scheduled_task` Tool 回执、Thread messages、`ChatMarkdown`、共享 `Modal` 与 Chat 导航边界；没有新增数据库 schema、API 路由、调度器、分享、通知、monthly、repeat-end 或第二套任务状态机。

正常 PostgreSQL capability、真实账户/真实模型和部署环境的真实业务验收仍是发布门禁。本回执记录的是当前代码候选的 provider-free 技术闭环，不把隔离 fixture 描述成真实业务数据验收。

## 2. 实现事实

| 范围 | 当前实现 | 失败处理与边界 |
| --- | --- | --- |
| Calendar 安排入口 | `CalendarPopup` 将非空自然语言交给 `App`；`ChatView` 打开 fresh Chat 并把文本放入可编辑、未发送的输入框 | 空白禁用；不直接创建定义，不自动发送 |
| 轻量任务列表 | 任务主体、编辑、更多为三个独立按钮；状态图标、标题、计划/下次运行保持一行信息层级 | 单任务错误留在该行；任务读取失败不阻断日记 |
| 任务菜单 | 复用既有 run/history/pause/resume/delete/restore 和 Thread 导航 | disabled action 不进入菜单键盘焦点；没有 share |
| 最近结果 | `ScheduledTaskResult` 合并 day 与 history，严格按 `created_at` 选择最新 trigger | 目标 Thread 或 final ID 缺失、读取失败、精确消息不存在时显示局部“结果不可用” |
| 结果正文 | 调用既有 full Thread message 读取，精确匹配同一 trigger 的 `final_message_id` 与 assistant role，再交给 `ChatMarkdown` | 不回退到最新 assistant，不用 source Thread 或最近浏览 Thread 替代 |
| 编辑 | 共享 `Modal` 承载 title、prompt、once/daily、日期、时间、IANA 时区及 stable footer | 本地字段错误、revision 冲突、DST missing/repeated time 和 API 失败都保留 desired 草稿；关闭直接丢弃未保存草稿，不增加确认弹窗 |
| Chat marker | `scheduledTaskMarkerModel.ts` 只接受完成的 `create_scheduled_task`、`ok=true`、`result.status=ok` 和合法 `scheduled_task` | malformed、失败 envelope、其他 Tool 继续走原 Tool 呈现；不解析 assistant prose |
| 刷新后 marker | `ChatMessageList` 对 final-only history 复用 `fetchClaudeThreadMessageProcess`，按 Thread/message ID 去重、取消，并限制同轮并发读取 | 单条 process 失败保留 final；显式展开可重试；marker 不依赖展开过程 |
| Chat 详情栏 | 详情打开后重读 current task 与 history，显示 effective 配置、prompt、latest trigger，并从该 trigger 打开目标 Thread | 详情 API 失败局部重试；marker 快照仅作加载前标题/规则后备 |
| 侧栏互斥 | `ChatView` 持有 scheduled task 选择；打开 scheduled/File/Subagent/TaskSession 任一类型时关闭其他选择 | 切换 Thread 或从 Calendar 建 fresh Chat 时关闭旧详情；窄屏使用右侧 Drawer 几何 |
| 滚动 | 桌面月历纸面固定；右侧任务/日记外层独立纵向滚动；结果正文与编辑内容各有自己的滚动容器 | 短视口月历自身可滚；内容不会撑动相邻月历 |

## 3. 独立评审结论

四项 P1 文档差距已经在实施前关闭，并由当前实现兑现：

1. final-only history 不再被误写成包含 Tool parts；历史 marker 经现有 message-process 接口自动恢复，实时与历史共用严格 decoder。
2. `ChatView` 是 scheduled/File/Subagent/TaskSession 右栏选择 owner；各入口双向关闭其他栏。
3. 编辑器没有伪造服务端不提供的 DST 偏移候选；错误保留 desired，并要求用户改成无歧义当地时刻。
4. v3 历史回执与 v4 当前回执分开保存；现行 E2E 已重写为 v4 DOM、交互和精确 ID 合同。

未发现为未来假设场景引入的通用 marker 框架、工作流引擎、通知服务或新状态。设计和实现保持最小业务切片。

## 4. 需求—设计—实现—测试追踪矩阵

| 需求 | 设计证据 | 实现证据 | 测试证据 | 状态 |
| --- | --- | --- | --- | --- |
| Calendar 安排入口进入 fresh Chat 草稿 | PRD §5.1；骨架 C4；UI §5.1 | `CalendarPopup` → `App` → `ChatView.requestedInput` | Calendar Chrome：草稿可编辑、未进入消息列表 | 通过 |
| 轻量任务列表与独立点击边界 | PRD §5.2；骨架 C5/C6；UI §5.2 | `ScheduledTaskCard` row 主按钮、edit、more | 桌面完整旅程、移动菜单键盘、平板/短视口 | 通过 |
| 既有菜单动作 | PRD §5.3；骨架 C7 | 复用 `updateScheduledTask` 和 history | edit conflict、pause/resume、run 重试、history、delete/restore | 通过 |
| 最新 trigger 结果页 | PRD §5.4；骨架 C8；UI §5.4 | LIST/RESULT 互斥；day/history 按 `created_at` 合并 | 完成态结果和独立 history 分页；活动态轮询终止 | 通过 |
| 精确 final message | PRD §5.4.3-6；系统时序 §7.3 | full message 读取后只接受 `id===final_message_id && role===assistant` | 目标 Thread 有更晚 assistant，结果仍显示指定旧 final；更晚消息不出现 | 通过 |
| 精确打开目标 Thread | PRD §3.3、§5.4.6、§5.7.6 | 结果和详情只传 latest trigger 的 `target_thread_id` | Calendar 与 Chat browser harness 均断言目标 Thread ID | 通过 |
| 独立编辑 Modal | PRD §5.5；骨架 C9；UI §5.5 | 共享 `Modal`、effective→desired、revision 冲突 | 独立 dialog、冲突后二次保存、DST repeated/missing、保存关闭 | 通过 |
| 严格 Tool success marker | PRD §5.6；骨架 H2/H3；UI §5.6 | 纯 decoder + owning assistant final 后 marker | object/string success；prose/其他 Tool/失败/malformed fail closed | 通过 |
| 刷新后持久 marker | PRD §5.6、§7.2 | final-only message 自动读取 process，去重/取消/重试 | Chrome：single-flight、失败后显式重试、不展开过程也恢复 marker | 通过 |
| 详情侧栏重读 effective/history | PRD §5.7；骨架 H4-H8；UI §5.7 | `ScheduledTaskDetailSidebar` 复用 get/history | Chrome：prompt、completed trigger、精确 Open conversation | 通过 |
| 右栏互斥和移动 Drawer | PRD §5.7、§10.2；骨架 §6.3/§7 | `ChatView` 单一选择 owner；响应式 CSS | TypeScript/build、源码状态转换审计；marker 详情浏览器旅程 | 通过（源码与组件浏览器证据） |
| 不伪造协议外能力 | PRD §2.3；骨架 §12；UI §12 | 无 share/monthly/notification/repeat-end/cron 字段或控件 | 请求 fixture 与 DOM 旅程无这些能力 | 通过 |
| 任务/日记滚动互不影响 | PRD §5、§10；UI §6 | 固定月历 + workspace 外滚动 + result/editor 内滚动 | 390/1024/1025/1440/短视口几何、滚动 owner、无横向溢出 | 通过 |
| 普通 Chat/Tool/调度回归 | PRD §13.5；系统设计测试门禁 | 未改后端状态机、SSE、resume/cancel 或 ScheduledTask DTO | Chat process/MCP App 6 项与调度 Tool/broker/consumer 40 项 | 通过（相关范围） |

## 5. 影响范围与测试资源

- 项目：Dream 前端和既有 Dream 后端合同测试；Admin 与共享 PostgreSQL schema 无代码变化。
- 前端模块：`CalendarPopup`、`App`、`ChatView`、`ChatPanel`、`ChatMessageList`、scheduled marker/detail 组件、i18n 与 browser fixtures。
- 既有流程风险：普通 Chat history process、TaskSession/Subagent/File 侧栏、Calendar 日记读取、ScheduledTask action DTO 和 Thread 导航。
- 数据风险：本轮 Chrome 旅程使用 production-shaped route fixture，不写真实数据库、账户、Thread、Run、日记或模型。
- 资源：复用本机 Chrome；临时 Vite/Next 端口与进程由 runner 所有并在结束时清理；不停止用户服务。

## 6. 验证回执

| 命令 | 退出码 | 关键输出 | 覆盖 |
| --- | ---: | --- | --- |
| `cd frontend && pnpm exec tsc --noEmit` | 0 | 无输出 | 前端类型合同 |
| `cd frontend && pnpm run lint` | 0 | `0 errors, 17 warnings`；warnings 为仓库现有 Hook dependency 清单 | 全前端 lint |
| 在隔离复制目录执行 `pnpm run build` | 0 | Next 16.1.6；compiled、TypeScript、3/3 static pages、traces 全通过 | 生产构建；未覆盖用户运行中的 `.next` |
| `cd frontend && E2E_WEB_BASE=http://127.0.0.1:5173 pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --reporter=line --workers=1` | 0 | `9 passed (31.6s)`；console/page/request 诊断为空 | Calendar v4 完整旅程、精确 final、断点、焦点恢复和失败分支 |
| `cd frontend && pnpm exec playwright test app/_dream/components/chat/__tests__/ScheduledTaskMarker.test.ts app/_dream/components/chat/__tests__/ChatHistoryProcessLazyLoad.browser.test.ts --reporter=line --workers=1` | 0 | `6 passed (2.8s)` | decoder、history process、整卡 marker、详情与目标 Thread |
| `cd backend && PYTHONPATH=. uv run --group dev python -m pytest -q tests/test_thread_tool.py tests/test_scheduled_task_consumer.py tests/test_session_projection_broker.py` | 0 | `40 passed in 15.53s` | Tool、broker、调度 consumer 与 fail-closed 合同 |

浏览器 runner 预检确认 Playwright 1.62.1 与本机 Chrome 可用；最终 `.last-run.json` 为 passed，无失败 trace。所有测试只清理本轮明确创建的进程、临时端口和构建复制目录。

## 7. 已修正的旧错误内容

1. 旧 E2E 的 trigger `final_message_id` 与消息 ID 不一致，仍可通过，因为当时没有验证结果正文；现 fixture 使用精确匹配，并增加更晚 assistant 消息防止“取最后一条”伪通过。
2. 历史分页 fixture 曾把历史记录时间造得比 active trigger 更新，导致卡片提前显示成功；历史时间已改为早于 active trigger，轮询终止断言现在有因果关系。
3. 一个分页场景只有一项任务和一篇日记，却强制底层 stack 必须溢出；改为验证独立 history Modal、正确滚动 owner 与安全边距，不再把内容长度当产品合同。
4. 后端首轮用 `uv run pytest` 时 console-script import path 导致 `tests` 包不可见；正式回执改用 `PYTHONPATH=. uv run --group dev python -m pytest`，未把 harness 调用错误算作产品失败。
5. 现行文档中“v4 未实施/待 E2E”已改为当前实现与验证事实；v3 原文保存在 history，不覆盖历史回执。

## 8. 剩余门禁

- 正常 PostgreSQL capability 是否已部署、目标账户权限、真实 worker 到期触发、真实模型正文和 Admin 可见 Run/Thread 记录未在本轮 provider-free 测试中验证。
- 这些属于部署/真实业务验收，不影响当前 v4 页面代码和隔离业务旅程通过；发布时仍必须按本仓库“本机真实业务测试协议”单独执行并保留正常业务记录。
- 当前实现没有数据库 schema 变化，因此不需要 Admin Drizzle migration，也没有 Dream runtime DDL 或 SQLite fallback。
