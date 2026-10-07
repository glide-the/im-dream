<!-- [Input] Approved Codex repeat design, Admin v3 migration/contracts, Dream scheduled execution path, Calendar UI, and final validation receipts. -->
<!-- [Output] Post-implementation conformity review, current traceability matrix, test receipts, and explicit validation limits. -->
<!-- [Pos] Current implementation receipt; the pre-implementation review remains preserved in codex-repeat-and-run-options-review.md. -->
<!-- [Sync] 2026-10-07: verify the v3 recurrence, Thread mode, model snapshot, unattended tool policy, and browser vertical slice. -->

# Codex 风格周期与高级运行选项：实施后验收

## 1. 结论

**结论：纵向切片已实现并通过隔离业务 E2E。**

Admin 在既有 scheduled-task 表和 service 上发布 additive v3 capability；Dream 只消费精确 capability，并继续经现有 `ClaudeAgentThreadFactory.run_streaming()` 执行；前端在原 `CalendarPopup`、Chat 任务标记和详情侧栏中加入五类周期、二级高级日程、新聊天开关和模型。没有新增 Dream schema、浏览器 timer、第二套 Thread/Run/SSE 或部署环境分支。

本回执中的 PostgreSQL 与浏览器结果属于可重复的隔离技术/业务流程验证。它们没有写入用户正常业务数据库，也没有调用真实模型，因此不表述为真实业务数据验收或真实模型验收。

## 2. 影响范围

| 项目 | 模块 | 影响与隔离 |
|---|---|---|
| Admin | Drizzle schema、0077 migration、v3 DTO/time/service/handler/registry | 扩展 definition/trigger 快照、受限 RRULE、source/new Thread prepare；隔离 PostgreSQL 跑全量 78 个 migration。 |
| Dream backend | v3 Admin DTO、request auth、Coordinator、公开 Chat 路由、Thread Tool、tool approval policy | 复用现有 turn、resume、模型 resolver、EventBus、SSE 和持久化；后台失败不传播到普通 turn。 |
| Dream frontend | Calendar、scheduled API、Chat marker/detail/activity、i18n | 编辑正文独立滚动；高级日程二级弹窗；详情继续通过 target Thread/Turn 导航。 |
| 测试资源 | 本机 Chrome、现有 5173/8765 服务、隔离 embedded PostgreSQL | Playwright 与临时数据库均由 runner 退出/清理；没有停止用户已有服务。 |

## 3. 需求—设计—实现—测试追踪矩阵

| ID | 需求 | 设计 | 实现证据 | 验证状态 |
|---|---|---|---|---|
| T1 | 每小时、每天、工作日、每周、自定义 | PRD 3.2、4、5；设计 3.3、4 | `CalendarPopup.tsx` repeat preset；`scheduledTaskApi.ts` v3 union | Calendar E2E 13/13，顺序、选择、摘要和回显通过。 |
| T2 | 每 10 分钟持续执行 | PRD 3.2；设计 3.3 | Admin `interval` canonical rule；Dream Tool 结构化 rule | Admin time/PG 合同与 Calendar 10 分钟流程通过。 |
| T3 | 每小时与自定义小时 | PRD 3.2；设计 3.3 | Admin `hourly` parser/next-run；Calendar 高级日程 | Admin time 单测与浏览器 E2E 通过。 |
| T4 | 工作日/每周/IANA 时区 | PRD 3.2；设计 3.3 | Admin `weekly` + BYDAY；Calendar weekday fields | DST/weekly 合同与高级日程 E2E 通过。 |
| T5 | 二级高级日程 | PRD 5；设计 4 | `CalendarPopup` snapshot/apply/cancel secondary dialog | 桌面、移动和平板 E2E 通过。 |
| T6 | 关闭开关复用源 Thread | PRD 3.3；设计 3.4、5.1 | Admin source prepare；Dream verified scheduled resume | PG 集成覆盖 source Thread、输入/Turn 和结果关系。 |
| T7 | 开启后每次新聊天 | PRD 3.3；设计 5.1 | Admin TaskSession/new Thread prepare；UI switch | PG 集成覆盖 child Thread；E2E 校验提交 DTO。 |
| T8 | 同源并发去重 | PRD 3.3；设计 3.4、5.2 | partial unique open-target 与 `SCHEDULE_SOURCE_THREAD_BUSY` | PG 集成覆盖跨任务冲突和计划推进。 |
| T9 | 可调用模型选择 | PRD 3.4；设计 4、7.4 | Gateway model catalog；UI 精确 alias；Dream resolver | E2E 覆盖 model DTO；后端 Coordinator/route 回归通过。 |
| T10 | revision/trigger 模型快照 | PRD 3.1、3.4；设计 3.2 | Admin definition/trigger snapshot；prepare 回执 | PG 集成覆盖创建与编辑后的不同模型快照。 |
| T11 | v1/v2 兼容 | PRD 3.3、3.4；设计 3.2、9 | additive 0077 与独立 v3 capability；legacy null 分支 | 78/78 migration、v1/v2/v3 contract 集成通过。 |
| T12 | desired/effective/revision | PRD 3.1、4；设计 4、5.3、6 | Calendar desired draft、完整回执替换、冲突字段 | Calendar revision E2E 通过。 |
| T13 | 暂停/恢复/删除/立即运行/历史 | PRD 6、7；设计 6、10 | 复用既有 revision actions 与 trigger history | Calendar 全生命周期回归通过。 |
| T14 | source Thread 删除 | PRD 3.3；设计 7.1、9 | 保留 source FK cascade；新索引不改变 owner 关系 | schema contract 与 PG 集成通过。 |
| T15 | 重启恢复且不重复 | PRD 3.2；设计 5.2、6 | 复用 lease/state_unknown/reconcile；v3 快照 | PG 集成覆盖 unknown recovery 与 prepared input 复用。 |
| T16 | 普通 Chat/resume/cancel/SSE | 设计 2.2、9、10 | scheduled context 为 server-owned；ThreadFactory/Service/EventBus 未分叉 | Dream 会话与 resume 分组回归通过。 |
| T17 | 自动笔记/手动工具枚举 | interval PRD 3.4；工具设计 3.3、4、8 | `ToolApprovalPolicy`；write/insert auto，delete/reply/interactive/unknown deny | Runner 159 tests、170 subtests 通过。 |
| T18 | capability 缺失 fail closed | PRD 2.2、6；设计 7、8 | Dream 精确 v3 hashes/request auth，无 runtime DDL/fallback | request-auth/route 分组回归通过。 |
| T19 | 卡片、滚动与窄屏 | PRD 5；workflow Stage 2/4 | 浮层卡片、右侧/正文滚动边界、响应式 CSS | Chrome 桌面、移动、平板 E2E 通过。 |
| T20 | 文档、图示与目录同步 | AGENTS 图示合同；设计 5、6、12 | PRD 骨架、设计正常/异常时序和状态图、folder inventory | Markdown 链接、Mermaid parse 与 `git diff --check` 最终检查。 |

## 4. 测试回执

| 位置 | 完整命令 | 退出码 | 关键结果 |
|---|---|---:|---|
| Admin | `pnpm exec vitest run app/lib/dream/chatScheduledTaskTime.test.ts app/lib/dream/chatScheduledTaskRegistration.test.ts app/lib/db/chat-scheduled-task-v3-schema-contract.test.ts` | 0 | 3 files，12 tests passed。 |
| Admin | `node scripts/run-chat-scheduled-task-contract.mjs` | 0 | 78/78 migration；7 PG integration tests passed；`scheduled_chat_contract=passed`；隔离数据库已关闭。 |
| Admin | `pnpm exec tsc --noEmit` | 0 | 当前全仓 TypeScript 检查通过。 |
| Admin | `pnpm exec eslint packages/db/src/schema/dream.ts app/lib/dream/chatScheduledTaskDto.ts app/lib/dream/chatScheduledTaskTime.ts app/lib/dream/chatScheduledTaskService.ts app/lib/dream/chatScheduledTaskHandler.ts app/lib/dream/operationRegistry.ts app/lib/dream/chatScheduledTaskPostgres.integration.test.ts app/lib/dream/chatScheduledTaskRegistration.test.ts app/lib/dream/chatScheduledTaskTime.test.ts app/lib/db/chat-scheduled-task-v3-schema-contract.test.ts` | 0 | v3 schema/service/registry/test 0 error、0 warning。 |
| Dream backend | `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_scheduled_task_consumer.py tests/test_admin_request_auth.py tests/test_thread_tool.py tests/test_admin_chat_routes.py tests/test_server_claude_agent.py` | 0 | 175 passed，4 subtests passed。 |
| Dream backend | `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_claude_agent_thread_factory.py tests/test_claude_agent_service.py tests/test_claude_agent_thread_input_queue.py` | 0 | 116 passed，9 subtests passed。 |
| Dream backend | `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_claude_resume_runtime.py` | 0 | 4 passed；独立进程避免其它测试 SDK stub 污染。 |
| Dream backend | `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_claude_resume_resolution.py tests/test_event_bus.py tests/test_events.py` | 0 | 42 passed，12 subtests passed。 |
| Dream backend | `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_claude_agent_runner.py` | 0 | 159 passed，1 skipped，170 subtests passed；覆盖 scheduled exact auto/manual 与 violation marker。 |
| Frontend | `pnpm exec tsc --noEmit` | 0 | 无类型错误。 |
| Frontend | `pnpm exec eslint app/_dream/api/scheduledTaskApi.ts app/_dream/components/CalendarPopup.tsx app/_dream/components/chat/ScheduledTaskDetailSidebar.tsx app/_dream/components/chat/ScheduledTaskMarker.tsx app/_dream/components/chat/scheduledTaskMarkerModel.ts app/_dream/components/chat/__tests__/ScheduledTaskMarker.test.ts e2e/fixtures/calendarHarness.ts e2e/scheduled-task-calendar.spec.ts` | 0 | 0 error，0 warning。 |
| Frontend | `pnpm run build` | 0 | Next production build、TypeScript、static page、trace 全部完成。 |
| Frontend | `pnpm exec playwright test app/_dream/components/chat/__tests__/ScheduledTaskMarker.test.ts app/_dream/components/chat/__tests__/ScheduledTaskActivity.browser.test.ts app/_dream/components/chat/__tests__/TaskActivityPopover.browser.test.ts --workers=1 --reporter=line --output=test-results/scheduled-v3-focused-2` | 0 | 4 passed。 |
| Frontend | `E2E_WEB_BASE=http://127.0.0.1:5173 pnpm exec playwright test e2e/scheduled-task-calendar.spec.ts --workers=1 --reporter=line --output=test-results/scheduled-v3-calendar-20261007-final` | 0 | 13 passed；桌面、移动、平板和完整 Calendar 任务流程。 |
| Repository | `python frontend/test-results/scheduled-v3-calendar-20261007-final/check-docs.py` | 0 | 10 个当前 Markdown 本地引用全部存在。 |
| Repository | `node frontend/test-results/scheduled-v3-calendar-20261007-final/check-mermaid.mjs` | 0 | 本机 Chrome 中 4/4 Mermaid 正常解析。 |
| Both repositories | `git diff --check` | 0 | Dream 与 Admin 均无空白错误。 |

## 5. 已修正的旧错误

1. 旧 UI 只支持一次/每天/固定分钟；现在映射五项菜单并保留自定义分钟、小时、一次和多星期。
2. 旧 trigger 永久限制 target Thread 唯一，无法在源 Thread 连续运行；0077 改为按模式和 open 状态约束。
3. 旧执行只创建新 Thread；v3 通过同一 prepare/start/finish 状态机支持 source resume。
4. 旧 definition 没有模型快照；v3 保存 alias 并随 trigger 快照，执行时重新校验。
5. UI 最初把高级规则直接铺在主弹窗；现改为“重复 / 高级日程”两行和二级规则弹窗。
6. E2E 最初用模糊 `/高级/` 同时匹配两处入口；最终测试使用精确 accessible name，不改变产品行为。

## 6. 剩余限制

- 本轮没有向正常业务数据库写任务，也没有调用真实 Claude 模型；真实环境须先发布 Admin 0077/v3 capability，再按本机真实业务测试协议验收。
- `claude_agent_sdk` 会提示 `can_use_tool` 被 exact `allowed_tools` 先行解析；本实现的人工/自动策略由 `PreToolUse` exact policy 执行，sandbox runtime network ask 仍在 `can_use_tool` fail closed。Runner 回归锁定这两条通道。
