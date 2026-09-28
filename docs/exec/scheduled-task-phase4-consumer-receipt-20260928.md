<!-- [Input] Dream scheduled consumer implementation, isolated Admin HTTP/Drizzle runner and provider-free browser/backend checks. -->
<!-- [Output] Actual phase-four commands, outcomes, business-path evidence and remaining acceptance boundaries. -->
<!-- [Pos] Dream scheduled Chat technical receipt; no normal-account or real-model claim. -->
<!-- [Sync] 2026-09-28: record repeated isolated Admin/Dream journey, broad Chat regression and Calendar browser fixture. -->

# 定时 Chat 消费端与隔离验证回执

## 背景与问题

Dream 首期定时任务需要消费 Admin 所有的定义和触发记录，经当前用户授权的 Tool 创建任务，再由服务凭据领取并启动独立 Chat。此前 Dream 没有 `schedule.create` 的 broker 分发、后台领取或日期卡片。

## 目标与边界

本次验收覆盖单次/每日规则的严格输入、创建幂等、手动触发自动领取、TaskSession/目标 Thread/首条输入、同一 turn 的助手最终消息、日历日期与历史、revision 冲突、编辑、暂停/恢复、删除/撤销、重启后不重跑、缺 capability 拒绝和续租失败诊断。Admin 继续拥有 Drizzle、时间计算、领取租约、权限与结果核对；Dream 继续使用原 Chat 前置检查、ThreadFactory、Service、SSE 和持久化 owner。

技术验证使用命名的可删除隔离数据库、签名 fixture 身份和可控 SDK Runner。它没有调用真实模型，没有使用本机正常业务数据库或真实账户；浏览器阶段以拦截的同源 API 检查日历交互，未把浏览器夹具当作真实 Admin 响应。[可重复运行脚本](../../scripts/run-scheduled-chat-isolated-e2e.mjs)使用随机测试库名，并要求显式提供本机 Admin 根目录、Python、资源受众，以及本机维护库 URL 或可推导该连接的 Admin env 文件。

## 概念与规则的执行证据

| 节点 | 实际输入与判断 | 结果 |
| --- | --- | --- |
| Admin schema | 隔离数据库执行 Admin Drizzle migration，检查四项定时 schema capability | `73/73` migration，四项 capability 全部发布；测试后删除该命名数据库。 |
| Tool 创建 | 真实来源 Thread 的 `server-persistence idg_`，私有 broker 和 `scheduled-task.create` | 相同 Tool 调用键只得到同一定义；broker 只接收标题、提示词和单次/每日规则。 |
| 领取与派发 | 公开 `scheduled-task.run` 产生手动触发；另通过 Tool 创建下一个 UTC 整分钟到期的单次计划，生产 worker 以服务凭据自动 claim/prepare/start | 手动和到期触发分别建立目标 TaskSession、Thread、首条消息和固定 turn ID；无测试侧数据库时钟修改。 |
| 结果 | 生产 ThreadFactory/Service 经假 SDK Runner 完成，Admin `finish` 核对最终消息所属 Thread、`turnId` 与完成投影 | 两个触发均为 `succeeded`，目标 Thread 不同，模型替身共调用 `2` 次，公开消息接口可读首条输入与助手最终消息。 |
| 日历与修改 | Dream 公开 day/get/history/action 路由，另一用户 token，revision CAS | 日期、历史可读；他人 get 返回 `{task:null}`、history 返回 404；编辑、暂停、恢复、删除、撤销删除与冲突反馈通过。 |
| 重启与恢复 | 停止并重新启动消费 worker，查询已结算触发 | 模型替身调用次数仍为 `2`；启动回执不确定时仅重取原请求回执，续租失败进入状态待核查。 |

## 命令和退出码

| 命令 | 退出码 | 关键输出 |
| --- | ---: | --- |
| `node /private/tmp/ink-scheduled-cross-service-proof.mjs` | 0 | Admin migration `73/73`；Dream `backend/tests/probe_scheduled_task_http.py` 返回 `status=passed`、`due_once_trigger_settled=true`、`model_calls=2`；隔离库清理完成。仓库脚本以随机库名复跑相同场景。 |
| `node /private/tmp/run-scheduled-committed-proof.mjs`（仅向仓库脚本提供私有测试配置） | 0 | 实际执行 `node scripts/run-scheduled-chat-isolated-e2e.mjs`；生成 `ink_scheduled_cross_service_test_928f7dce7de9`，四项 capability，`due_once_trigger_settled=true`、手动键与重启去重、`model_calls=2`；命名数据库与自有 Next 进程清理完成。 |
| `node /private/tmp/run-scheduled-committed-proof.mjs`（仅提供 Admin 根目录、env 文件、Python 与资源受众，不传维护库 URL） | 0 | 最终仓库脚本再次通过；生成 `ink_scheduled_cross_service_test_d253caf02cc8`，四项 capability，`due_once_trigger_settled=true`、手动键与重启去重、`model_calls=2`；命名数据库清理完成。 |
| `node /private/tmp/ink-scheduled-admin-build-proof.mjs` | 0 | 在身份核对过的隔离库 `ink_scheduled_build_test_20260928a` 上执行 Admin migration `73/73` 和 `pnpm build`；Next 构建通过，命名库及本轮 `.next-e2e-scheduled-build-20260928a` 已清理。 |
| `PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest backend/tests/test_scheduled_task_consumer.py backend/tests/test_thread_tool.py backend/tests/test_admin_chat_routes.py backend/tests/test_server_claude_agent.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_claude_agent_service.py -q` | 0 | `253 passed, 13 subtests passed`。 |
| `PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest backend/tests/test_thread_tool.py backend/tests/test_admin_chat_routes.py backend/tests/test_server_claude_agent.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_thread_input_queue.py backend/tests/test_claude_resume_resolution.py backend/tests/test_claude_resume_runtime.py backend/tests/test_event_bus.py backend/tests/test_events.py -q` | 0 | `297 passed, 25 subtests passed`；覆盖普通 Chat SSE、Thread Tool、恢复、取消和事件流；本机 loopback 测试放行后通过。 |
| `PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest backend/tests/test_session_projection_broker.py -q` | 0 | `27 passed`，包含 `schedule.create` broker 往返；需要本机临时 loopback 端口。 |
| `pnpm exec tsc --noEmit --pretty false`（`frontend/`） | 0 | 无 TypeScript 错误。 |
| `pnpm build`（`frontend/`） | 0 | Next.js 16.1.6 生产构建与静态页面生成通过。 |
| `pnpm exec eslint app/_dream/App.tsx app/_dream/components/CalendarPopup.tsx app/_dream/api/scheduledTaskApi.ts app/_dream/i18n.ts`（`frontend/`） | 0 | 0 error；`App.tsx` 既有 14 条 Hook 依赖 warning。 |
| `python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py` | 1 | 工作树缺少 `backend/.venv`，前置脚本未通过；这是 runner 路径检查结果，不是页面或 API 失败。后续本机已安装 Chrome 启动检查通过。 |
| `npx playwright test e2e/scheduled-task-calendar.spec.ts --reporter=line --workers=1`（`frontend/`） | 0 | 本机 Chrome `1 passed (7.1s)`；覆盖日期卡片、历史、操作与普通笔记区域，API 为隔离 fixture。 |
| `node --check scripts/run-scheduled-chat-isolated-e2e.mjs` | 0 | 仓库隔离运行脚本语法通过。 |
| `python3` Markdown 相对链接检查（本轮修改的 19 个文档） | 0 | `markdown_files=19 missing_links=0`。 |
| `git diff --check` | 0 | 无空白错误。 |

Admin 的隔离 PostgreSQL 集成测试另验证到期计算、暂停/删除后的领取限制、租约回收、错误 turn final 拒绝及历史保留。完整公开入口与真实模型、正常业务账户的验收须遵守仓库的本机真实业务测试协议；本回执不代表该阶段已经执行。
