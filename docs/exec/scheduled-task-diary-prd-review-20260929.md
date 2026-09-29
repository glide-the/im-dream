<!-- [Input] 现行 v5 Calendar/Chat PRD、四阶段 html-design-workflow 产物、系统/UI 设计及 Dream/Admin 实现与验证回执。 -->
<!-- [Output] 定时任务 v5 的独立设计裁决、TaskSession 分类修正、需求—设计—实现—测试追踪矩阵与剩余部署门禁。 -->
<!-- [Pos] v5 定时任务页面交互的现行评审和实现回执；v4 关闭回执原文保存在 docs/exec/history。 -->
<!-- [Sync] 2026-09-29: 修正 Chat marker 测试与生产 Tool 名称、part 类型和顶层回执不一致的问题，并在正常本机账户的既有真实创建会话中复验刷新恢复与详情侧栏。 -->

# 定时任务 Calendar / Chat v5 设计评审与实现关闭回执（2026-09-29）

## 文档导航

- [现行 PRD](../prd/claude-agent/scheduled-task-diary-page-prd.md)
- [现行页面骨架](../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)
- [现行 UI 设计与 HTML 原型](../design/claude-agent/scheduled-task-diary-page-ui-design.md)
- [定时任务系统交互与执行设计](../design/claude-agent/scheduled-task-loop-interaction-design.md)
- [上一版 v4 关闭回执（历史）](./history/scheduled-task-diary-prd-review-v4-20260929.md)
- [上一版悬浮纸张视觉评审（历史）](./history/scheduled-task-diary-prd-review-v3-20260929.md)
- [更早的分卡评审与真实业务回执（历史）](./history/scheduled-task-diary-prd-review-v2-20260929.md)

## 1. 结论

**设计裁决：收敛后实施。实施裁决：v5 已按收敛方案完成；本回执以本轮重新运行的验证结果为准。**

v4 已覆盖 Calendar 顶部安排入口、轻量定时任务行、最近执行结果、独立编辑 Modal、Chat 内持久任务标记与右侧详情栏。独立复评发现一个产品语义缺口：Admin `task-session.links` 把 scheduled trigger 为执行复用的 `chat_task_session` 同时投影进通用 “Tasks created by this conversation”，而 Chat 详情只展示最近一次 target Thread。v5 在既有协议内修正这两个投影：通用 links 只返回普通独立 TaskSession；详情栏固定为“任务信息 → Conversations → 任务周期”，Conversations 置顶 source Thread 并列出所有具备 target Thread 的 trigger。

实现继续使用既有 ScheduledTask get/history、`create_scheduled_task` Tool 回执、Thread 导航和同一侧栏 owner；Admin 只在精确 `dream.chat-scheduled-link-lifecycle.v1` capability 存在时引用 scheduled trigger 表。没有新增数据库 schema、migration、API 路由、调度器、分享、通知、monthly、repeat-end 或第二套任务状态机。

正常 PostgreSQL capability、真实账户和真实模型已在用户创建的任务 `REAL-SCHEDULE-AUTO-E2E-20260929-1538` 上产生成功 Tool 回执。本轮修正后，在同一正常本机 Chat 页面完成刷新、重开来源会话、任务卡恢复和右侧详情读取；该任务计划在 22:38 到期，因此本轮 22:16 的复验不把未来的到期执行描述成已验证。隔离 fixture 只作为确定性回归，不能替代上述真实页面证据。

## 2. 实现事实

| 范围 | 当前实现 | 失败处理与边界 |
| --- | --- | --- |
| Calendar 安排入口 | `CalendarPopup` 将非空自然语言交给 `App`；`ChatView` 打开 fresh Chat 并把文本放入可编辑、未发送的输入框 | 空白禁用；不直接创建定义，不自动发送 |
| 轻量任务列表 | 任务主体、编辑、更多为三个独立按钮；状态图标、标题、计划/下次运行保持一行信息层级 | 单任务错误留在该行；任务读取失败不阻断日记 |
| 任务菜单 | 复用既有 run/history/pause/resume/delete/restore 和 Thread 导航 | disabled action 不进入菜单键盘焦点；没有 share |
| 最近结果 | `ScheduledTaskResult` 合并 day 与 history，严格按 `created_at` 选择最新 trigger | 目标 Thread 或 final ID 缺失、读取失败、精确消息不存在时显示局部“结果不可用” |
| 结果正文 | 调用既有 full Thread message 读取，精确匹配同一 trigger 的 `final_message_id` 与 assistant role，再交给 `ChatMarkdown` | 不回退到最新 assistant，不用 source Thread 或最近浏览 Thread 替代 |
| 编辑 | 共享 `Modal` 承载 title、prompt、once/daily、日期、时间、IANA 时区及 stable footer | 本地字段错误、revision 冲突、DST missing/repeated time 和 API 失败都保留 desired 草稿；关闭直接丢弃未保存草稿，不增加确认弹窗 |
| Chat marker | `scheduledTaskMarkerModel.ts` 只接受完成的短名 `create_scheduled_task` 或生产名 `mcp__user__create_scheduled_task`、回执顶层 `ok=true`、`status=ok` 和合法 `scheduled_task` | malformed、失败 envelope、其他 MCP namespace、旧测试误造的 `result` 双层包装、其他 Tool 继续走原 Tool 呈现；不解析 assistant prose |
| 刷新后 marker | `ChatMessageList` 对 final-only history 复用 `fetchClaudeThreadMessageProcess`，按 Thread/message ID 去重、取消，并限制同轮并发读取 | 单条 process 失败保留 final；显式展开可重试；marker 不依赖展开过程 |
| Chat 详情栏 | 详情打开后重读 current task 与 history，依次显示任务信息、Conversations、任务周期 | source 行绑定 `task.source_thread_id`；trigger 行按 `created_at` 倒序并绑定自身 `target_thread_id`；无 target 不伪造入口 |
| TaskSession 分类 | Admin `task-session.links` 对 source/created 两个方向排除被 `chat_scheduled_trigger.task_session_id` 引用的行 | 仅在精确 scheduled-link capability 存在时执行关联查询；普通独立 TaskSession 保持原协议 |
| 侧栏互斥 | `ChatView` 持有 scheduled task 选择；打开 scheduled/File/Subagent/TaskSession 任一类型时关闭其他选择 | 切换 Thread 或从 Calendar 建 fresh Chat 时关闭旧详情；窄屏使用右侧 Drawer 几何 |
| 滚动 | 桌面月历纸面固定；右侧任务/日记外层独立纵向滚动；结果正文与编辑内容各有自己的滚动容器 | 短视口月历自身可滚；内容不会撑动相邻月历 |

## 3. 独立评审结论

原 v4 的四项 P1 文档差距已经关闭；本轮又关闭两项投影缺口和一项真实协议回归缺口：

1. final-only history 不再被误写成包含 Tool parts；历史 marker 经现有 message-process 接口自动恢复，实时与历史共用严格 decoder。
2. `ChatView` 是 scheduled/File/Subagent/TaskSession 右栏选择 owner；各入口双向关闭其他栏。
3. 编辑器没有伪造服务端不提供的 DST 偏移候选；错误保留 desired，并要求用户改成无歧义当地时刻。
4. v3、v4 历史回执与 v5 当前回执分开保存；现行 E2E 使用当前 DOM、交互和精确 ID 合同。
5. scheduled trigger TaskSession 不再进入通用 created-task 列表；排除发生在 Admin 查询层，不靠前端标题或视觉去重。
6. 详情不再只暴露 latest trigger；source 与每次可导航执行都在 Conversations 内拥有独立整行入口。
7. 生产历史 part 是 `tool-invocation`，Tool 名是 `mcp__user__create_scheduled_task`，回执字段位于顶层；decoder 和回归 fixture 已对齐这三个真实协议事实，不再用短名、`dynamic-tool` 和 `result` 双层包装制造假通过。

未发现为未来假设场景引入的通用 marker 框架、工作流引擎、通知服务或新状态。设计和实现保持最小业务切片。

## 4. 需求—设计—实现—测试追踪矩阵

| 需求 | 设计证据 | 实现证据 | 测试证据 | 状态 |
| --- | --- | --- | --- | --- |
| Calendar 安排入口进入 fresh Chat 草稿 | PRD §5.1；骨架 C4；UI §5.1 | `CalendarPopup` → `App` → `ChatView.requestedInput` | Calendar Chrome：草稿可编辑、未进入消息列表 | 通过 |
| 轻量任务列表与独立点击边界 | PRD §5.2；骨架 C5/C6；UI §5.2 | `ScheduledTaskCard` row 主按钮、edit、more | 桌面完整旅程、移动菜单键盘、平板/短视口 | 通过 |
| 既有菜单动作 | PRD §5.3；骨架 C7 | 复用 `updateScheduledTask` 和 history | edit conflict、pause/resume、run 重试、history、delete/restore | 通过 |
| 最新 trigger 结果页 | PRD §5.4；骨架 C8；UI §5.4 | LIST/RESULT 互斥；day/history 按 `created_at` 合并 | 完成态结果和独立 history 分页；活动态轮询终止 | 通过 |
| 精确 final message | PRD §5.4.3-6；系统时序 §7.3 | full message 读取后只接受 `id===final_message_id && role===assistant` | 目标 Thread 有更晚 assistant，结果仍显示指定旧 final；更晚消息不出现 | 通过 |
| 精确打开目标 Thread | PRD §3.3、§5.4.6、§5.7.5 | Calendar 结果传 latest target；Chat Conversations 分别传 source 与各 trigger target | Calendar 与 Chat browser harness 分别断言对应 Thread ID | 通过 |
| 独立编辑 Modal | PRD §5.5；骨架 C9；UI §5.5 | 共享 `Modal`、effective→desired、revision 冲突 | 独立 dialog、冲突后二次保存、DST repeated/missing、保存关闭 | 通过 |
| 严格 Tool success marker | PRD §5.6；骨架 H2/H3；UI §5.6 | 纯 decoder + owning assistant final 后 marker | 生产 `mcp__user__create_scheduled_task` + `tool-invocation` + 顶层 success；prose/其他 namespace/失败/malformed/旧双层 fixture fail closed | 通过 |
| 刷新后持久 marker | PRD §5.6、§7.2 | final-only message 自动读取 process，去重/取消/重试 | Chrome：single-flight、失败后显式重试、不展开过程也恢复 marker | 通过 |
| 详情侧栏三段结构 | PRD §5.7；骨架 H4-H8；UI §5.7 | `ScheduledTaskDetailSidebar` 复用 get/history，依次渲染 task info、Conversations、task cycle | Chrome：三个标题顺序、source 与 run 精确导航 | 通过 |
| scheduled TaskSession 不进入通用列表 | PRD §3.3、§5.7.6；骨架 H7；UI §5.7 | `ChatThreadRepository.listTaskSessionLinks` 使用 correlated `NOT EXISTS` 过滤 scheduled trigger 引用 | Admin 隔离 PostgreSQL：普通 source/created 保留，scheduled source/created 排除 | 通过 |
| 右栏互斥和移动 Drawer | PRD §5.7、§10.2；骨架 §6.3/§7 | `ChatView` 单一选择 owner；响应式 CSS | TypeScript/build、源码状态转换审计；marker 详情浏览器旅程 | 通过（源码与组件浏览器证据） |
| 不伪造协议外能力 | PRD §2.3；骨架 §12；UI §12 | 无 share/monthly/notification/repeat-end/cron 字段或控件 | 请求 fixture 与 DOM 旅程无这些能力 | 通过 |
| 任务/日记滚动互不影响 | PRD §5、§10；UI §6 | 固定月历 + workspace 外滚动 + result/editor 内滚动 | 390/1024/1025/1440/短视口几何、滚动 owner、无横向溢出 | 通过 |
| 普通 Chat/Tool/调度回归 | PRD §13.5；系统设计测试门禁 | 未改后端状态机、SSE、resume/cancel 或 ScheduledTask DTO | Chat process/MCP App 6 项与调度 Tool/broker/consumer 40 项 | 通过（相关范围） |

## 5. 影响范围与测试资源

- 项目：Dream 前端、文档与 Admin Chat repository；共享 PostgreSQL schema 无变化。
- 前端模块：`CalendarPopup`、`App`、`ChatView`、`ChatPanel`、`ChatMessageList`、scheduled marker/detail 组件、i18n 与 browser fixtures。
- 既有流程风险：普通 Chat history process、普通 TaskSession source/created 导航、Subagent/File 侧栏、Calendar 日记读取、ScheduledTask history 和 Thread 导航。
- 数据风险：确定性 Chrome 旅程使用 production-shaped route fixture；真实页面复验只读取用户刚创建的正常任务、来源 Thread 和详情 API，没有新建第二个任务、修改计划、立即运行或清理正常业务记录。
- 资源：复用本机 Chrome；临时 Vite/Next 端口与进程由 runner 所有并在结束时清理；不停止用户服务。

## 6. 验证回执

| 命令 | 退出码 | 关键输出 | 覆盖 |
| --- | ---: | --- | --- |
| `cd frontend && pnpm exec tsc --noEmit` | 0 | 无输出 | 前端类型合同 |
| `cd frontend && pnpm run lint` | 0 | `0 errors, 17 warnings`；warnings 为仓库现有 Hook dependency 清单 | 全前端 lint |
| 在隔离复制目录执行 `pnpm run build` | 0 | Next 16.1.6；compiled、TypeScript、3/3 static pages、traces 全通过 | 生产构建；未覆盖用户运行中的 `.next` |
| `cd frontend && pnpm exec playwright test app/_dream/components/chat/__tests__/ScheduledTaskMarker.test.ts app/_dream/components/chat/__tests__/ChatHistoryProcessLazyLoad.browser.test.ts --reporter=line --workers=1` | 0 | `6 passed (4.9s)`；本机 Chrome，无跳过 | 真实 Tool 名/part/顶层回执、malformed fail closed、刷新恢复、详情三段结构和精确 Thread 导航 |
| 当前 Chrome `http://localhost:5173/story-workspace/chat`：重开来源 Thread → 读取精确 message-process → 查看 marker → 打开详情 | 0 | process HTTP 200；任务 `f329c591-cc57-4628-ab36-5f922412d12c` 显示卡片；侧栏显示任务信息、Conversations、任务周期 | 正常账户、正常 PostgreSQL、用户刚创建的真实任务；验证即时 UI 链路，不宣称 22:38 到期执行已发生 |
| `cd /Users/dmeck/project/ink-admin-memory && pnpm exec tsc --noEmit --incremental false` | 0 | 无输出 | Admin TypeScript 合同 |
| `cd /Users/dmeck/project/ink-admin-memory && pnpm exec eslint app/lib/dream/chatThreadRepository.ts app/lib/dream/chatScheduledTaskPostgres.integration.test.ts scripts/run-chat-scheduled-task-contract.mjs` | 0 | 无输出；`node --check` 亦为 0 | Admin 查询、集成 fixture 和隔离 runner 静态检查 |
| `cd /Users/dmeck/project/ink-admin-memory && pnpm build` | 0 | DB package 与 Next 16.1.6 compiled、TypeScript、20/20 static pages、traces 通过 | Admin 生产构建 |
| `cd /Users/dmeck/project/ink-admin-memory && node scripts/run-chat-scheduled-task-contract.mjs` | 0 | `73/73` migrations；`1 file, 4 tests passed`；`scheduled_chat_contract=passed`；自有库已停止并删除 | ordinary source/created 保留；scheduled source/created 排除；完整 trigger lifecycle 回归 |
| 对本轮 16 个变更 Markdown 扫描相对链接，并在两仓执行 `git diff --check` | 0 | `missing_local_links=0`；无 whitespace error | PRD、骨架、设计、历史索引与本轮回执 |

浏览器 runner 预检确认 Playwright 1.62.1 与本机 Chrome 可用；最终 `.last-run.json` 为 passed，无失败 trace。Admin runner 在 migration 前核对随机 `ink_scheduled_chat_test_*` 数据库名和 `current_database()`，测试后停止 embedded PostgreSQL 并删除自有目录。所有测试只清理本轮明确创建的进程、端口、数据库和构建复制目录；用户已有 5173/8765 服务保持运行。

Calendar、Tool、broker 和 consumer 本轮未改动；它们的 v4 `9 passed` 与后端 `40 passed` 回执保存在上一版历史关闭稿，本轮没有把历史结果描述成重新执行。

## 7. 已修正的旧错误内容

1. 旧 E2E 的 trigger `final_message_id` 与消息 ID 不一致，仍可通过，因为当时没有验证结果正文；现 fixture 使用精确匹配，并增加更晚 assistant 消息防止“取最后一条”伪通过。
2. 历史分页 fixture 曾把历史记录时间造得比 active trigger 更新，导致卡片提前显示成功；历史时间已改为早于 active trigger，轮询终止断言现在有因果关系。
3. 一个分页场景只有一项任务和一篇日记，却强制底层 stack 必须溢出；改为验证独立 history Modal、正确滚动 owner 与安全边距，不再把内容长度当产品合同。
4. 后端首轮用 `uv run pytest` 时 console-script import path 导致 `tests` 包不可见；正式回执改用 `PYTHONPATH=. uv run --group dev python -m pytest`，未把 harness 调用错误算作产品失败。
5. 现行文档中“v4 未实施/待 E2E”已改为当前实现与验证事实；v3 原文保存在 history，不覆盖历史回执。
6. v4 把 scheduled trigger 复用的 TaskSession 当成普通 created task；v5 在 Admin 查询层排除该关系，并保留普通 TaskSession 的 source/created 断言。
7. v4 详情只提供 latest target 的单一按钮；v5 将 source 与所有可导航 trigger 归入 Conversations，并逐行验证精确 Thread ID。
8. Admin 隔离测试首次因 `/private/tmp` 脚本无法解析仓库 `pg` 包而在建库前失败；修正 harness 依赖位置后迁移和产品断言通过，最终改为仓库内可复现 runner。
9. Chat marker 回归曾使用 `dynamic-tool`、短 Tool 名和 `{ ok, result: { status, scheduled_task } }`，而生产持久化协议实际是 `tool-invocation`、`mcp__user__create_scheduled_task` 和顶层 `{ ok, status, scheduled_task }`。旧 fixture 因此无法发现真实页面丢卡；本轮已按 message-process HTTP 200 的原始响应修正 decoder 与 fixture。

## 8. 剩余门禁

- 正常 PostgreSQL capability、目标账户权限、真实 Tool 创建和当前 Chat 任务卡/详情读取已经由同一正常业务记录验证；该一次性任务的 22:38 worker 到期触发、真实模型正文和新增 Run/target Thread 尚未发生，不能提前写成通过。
- 旧 v2 回执保留另一条已完成的真实到期执行证据；当前这条新任务仍应在到期后按本仓库“本机真实业务测试协议”复核并保留正常业务记录。
- 当前实现没有数据库 schema 变化，因此不需要 Admin Drizzle migration，也没有 Dream runtime DDL 或 SQLite fallback。
