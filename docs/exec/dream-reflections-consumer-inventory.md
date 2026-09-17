<!-- [Input] Dream Reflections call graph and frozen Admin Registry99/0061 source. -->
<!-- [Output] Function-level migration inventory, final operation mapping and Dream consumer evidence. -->
<!-- [Pos] Reflections consumer execution record; production registration and runtime cutover are implemented. -->
<!-- [Sync] 2026-09-15: bind final Admin source, close Dream production PG callsites and record runtime gates. -->

# Dream Reflections consumer 迁移清单

## 当前状态

Dream消费端绑定Admin foundation `9111d6bc4f6c8d60add1dd2157cb76ab6ea8eb33`及最终Reflections提交`16a3d9b2796254fa525a966ca851de96d4373445`（tree `4ea27088b777163b0e615f963d4e63c32785d69f`）。Registry99的16项operation、identity/unified/reflection-persistence三项schema及artifact SHA-256 `2af7477c424a92c39a1d323b301ef698da147dfa4f1aeb4e8a2166f146981365`已经作为源码常量注册到生产`AdminRequestAuth`。

已接入的生产代码：

- `backend/services/admin_data/reflection_task_models.py`：7 项 OAuth 与 9 项后台操作的严格 Pydantic 输入输出，包括 worker-load `last_event_sequence`。
- `backend/services/admin_data/reflection_task_data.py`：16 项固定名称/权限/DTO形状、operation/schema hash及最终Admin source commit/tree；不接受live discovery替代源码合同。
- `backend/services/admin_data/reflection_task_runtime.py`：worker-load snapshot 专用 Session projection provider 与共享 workspace locator 校验。
- `AdminDataClient.reflection_task_receipt()`：后台写只按原 operation、原 request ID 和原 task ID 查询回执；absent 不触发第二次 POST。
- `backend/services/admin_data/reflection_section_persistence.py`：section-bound RTA、续期/撤销、Agent写屏障和snapshot Session broker；secret不进入CLI、MCP、文件或日志。
- `backend/reflections_agent.py`与公开Reflections/Reports路由：只调用typed Admin consumers；Dream保留调度、Agent、EventBus、SSE、解析和共享文件。

## Dream 迁移前函数级调用清单与最终映射

| Dream 调用点 | 当前 helper 与边界 | 当前语义和缺口 | 目标操作 |
| --- | --- | --- | --- |
| `routers.reflections.create_reflections_task_endpoint` | `create_reflection_task` 单次 INSERT/COMMIT；随后 `get_reflection_task` 独立读取 | 路由以当前用户 ID 创建；task ID 在 Dream 生成；create 与返回读取可能漂移 | `reflection-task.create`，直接使用同一 Admin UOW 返回的 task/results |
| 同上，`auto_start=true` | 进程内创建 bus，再创建后台 asyncio task | 调度仍由 Dream；不得保留浏览器 bearer | create 返回后调用 `reflection-task.start`，只把 task ID 交给后台 worker |
| `routers.reflections.start_reflections_task_endpoint` | 两次 owner-scoped `get_reflection_task`，中间启动后台 task | GET 读取与历史 task service adoption 分离；终态 report 缺失没有补偿 | `reflection-task.start`；`terminal=false` 才调度，`terminal && report_missing` 进入 report ensure 补偿 |
| `routers.reflections.get_reflections_task_endpoint` | owner-scoped task read 后独立 results read | 两个事务可能看到不同 revision；results 按 section/created/id | `reflection-task.get` 在一个 UOW 返回 task/results |
| `routers.reflections.get_reflections_task_results_endpoint` | owner-scoped task read 后独立 results read | 同上 | 复用 `reflection-task.get`，仅投影原公开 results response |
| `routers.reflections.get_latest_reflections_endpoint` | latest task 与 latest terminal results 为独立查询；results 又开启第二连接 | task 与 results 可属于不同时间快照；旧排序缺少 ID tie-break | `reflection-task.latest`；保留“最新 task + 最新 completed/partial results”产品语义并使用稳定 ID tie-break |
| `routers.reflections.stream_reflections_task_events_endpoint` | owner-scoped task read；无 bus 时读取 persisted events，有 bus 时只读内存 replay/live | 重启后新建空 bus 会漏历史；未知 Last-Event-ID 回放全量；旧结果按 sequence/created 排序 | OAuth `reflection-task.events` 读取历史；Dream bus 只做当前进程 live fan-out |
| `routers.reports.get_reports` | owner-scoped `get_analysis_reports` 单 SELECT | `created_at DESC`，raw JSON 在 Dream 解码；limit 未由闭合策略验证 | `analysis-report.list`，Admin 验证 limit 并返回 lossless `report_data_json` |
| `routers.reports.save_report` | `save_analysis_report` 单 INSERT/COMMIT | 普通页面保存，不可设置 task link；当前 dict body 宽松 | `analysis-report.save`，保持 `all_notes_text` 默认空字符串 |
| `TaskPersistenceObserver.on_event` | `append_reflection_task_event` 单 INSERT/COMMIT，按 ID `DO NOTHING` | 不校验同 ID 异内容；新进程 sequence 从 0；并发 publish 的 observer 调用可能乱序 | `reflection-event.append`，原 request ID 回执；task row lock 要求 max+1，exact replay 除外 |
| `get_or_create_reflection_event_bus` | 新 bus `_sequence=0` | 历史 task 恢复会与 0061 `(task_id,sequence)` 唯一约束冲突 | `worker-load.last_event_sequence` 初始化 bus；范围 `0..2147483647` |
| `_effective_prompt_files` | 静态 prompt + owner-scoped config SELECT | worker 重新查配置，不能保证一次任务使用不可变输入 | 只读 `worker-load.launch_snapshot.custom_prompts`，再由 Dream 合并静态 default |
| `_prepare_workspace` | Dream 写 Session metadata、语言、section prompt 与 analysis state 文件 | 文件仍归 Dream；旧 locator 只做字符串前缀检查；路径 metadata 另一次 DB update | 使用 worker-load 的 server-produced `workspace_path`，按配置 root/task/memory 做规范化等值校验，拒绝 root 下已存在的 symlink 组件后再按原权限行为写文件 |
| `ClaudeAgentReflectionsRunner.run_section` | `create_chat_thread` 单 INSERT/COMMIT | child Thread 与 task/section 没有事务绑定 | `reflection-section.begin` 原子创建/恢复 child Thread、section RUNNING 与 RTA |
| `_init_memory_workspace` | 再次查询 section config 后写 child workspace | 配置可能和 task launch snapshot 不同 | 只用同一 launch snapshot 合并结果；文件算法保持 |
| `_run_claude_agent_stream` | 直接调用现有 ThreadFactory | 当前 request 没有 Admin turn owner，Claude service 会走旧 DB fallback | 注入 server-only Reflections section persistence owner；保持 ThreadFactory/Runner/EventBus/SSE 入口 |
| `_parse_thread_results` | `list_chat_messages` 无 owner filter，按 created NULLS FIRST/id 排序 | transcript selector 是任意 Thread ID | `reflection-section.transcript`，Admin 从 task/section 绑定推导 child Thread |
| `ReflectionsTaskEngine.run` 初始读取 | `get_reflection_task(task_id)` 无 owner | 只依赖进程内 task lock，后台没有 service binding | `reflection-task.worker-load`，使用 `reflections:execute` service identity；不保留 OAuth bearer |
| `run` 顶层失败 | `update_reflection_task_status(FAILED)` 独立提交，再 publish failed | 无 CAS；Runtime 前失败可能遗留 section；event 是另一个提交 | `reflection-task.advance(action=fatal-fail)` 先持久化 task/sections，再 publish failed |
| `_assemble_context` ASSEMBLING | status UPDATE/COMMIT | 没有 expected revision | worker-load 在物化 snapshot 时完成 CREATED→ASSEMBLING |
| `_assemble_context` Session 读取 | owner ID + date range SELECT，`include_text=true` | worker 直接访问 PG；排序 `updated_at DESC`；正文在内存 | worker-load 一次性冻结 bounded Sessions、正文、labels、first line、stats |
| `_assemble_context` QUEUED | status/workspace/input snapshot UPDATE/COMMIT | snapshot 与 Session/config 读取不在一个事务；optional field 的 `None` 不清空 | `advance(action=context-ready, expected_revision)` |
| `_create_executor` RUNNING | status/started_at UPDATE/COMMIT | Python 生成秒级 UTC started payload，DB status 用独立写 | `advance(action=run-started, expected_revision)`；事件时间仍由 Dream bus 生成 |
| `_execute_task` section start | 先 publish event，无 section row CAS | section 状态只存在 task 汇总和文件中 | `reflection-section.begin(expected_revision=section.revision)` 后 publish started |
| `_execute_task` completed | `replace_reflection_section_results` 在一个连接内 DELETE+N INSERT+COMMIT | result 替换自身原子，但与 section 完成/authority revoke 分离 | `reflection-section.finish(outcome=completed)` 在一个 Admin UOW 校验 snapshot Session ID、替换 results、完成 section、撤销 RTA |
| `_execute_task` failed | 只更新文件并 publish | 没有持久 section failure | `reflection-section.finish(outcome=failed)` 原子完成 section 并撤销 RTA |
| `_finalize_task` | task terminal UPDATE/COMMIT | 无 revision CAS；section 汇总来自进程内列表 | `reflection-task.advance(action=finalize)` 从持久 section 状态计算 terminal |
| `_persist_analysis_report` | 再读 results，Dream 重组 report，另一次 INSERT/COMMIT | task terminal 与 report 非原子，重复 worker 可重复写 | `reflection-report.ensure`，task link partial unique，显式 start/recovery 可补偿 |
| `start_reflections_task` | `_RUNNING_TASKS` 去重 + asyncio task | 只保证单进程；跨进程由 Admin revision/section CAS 拒绝冲突 | 保留调度，所有写以 task/section revision 约束 |
| `create_reflections_task` wrapper | Dream 正规化 section 后直接 DB INSERT | production helper 保留 SQL | 路由改用 OAuth create 后删除调用；旧 helper 在 AST closure 后 fail-before-I/O/退役 |

## 原事务、排序、时间与失败语义

- `replace_reflection_section_results` 的 DELETE 与全部 INSERT 在一个 Dream 连接中提交；迁移后由 `reflection-section.finish(completed)` 保持这条原子边界，并把 section 状态与 RTA revoke 一起提交。
- 旧 task status、event、report 各自独立提交，没有 revision/row lock。Admin 候选以 task/section row lock、positive revision CAS 和 task-scoped receipt 替代；Dream 不复制事务状态机。
- 旧 `get task + list results`、`latest task + latest terminal results` 是多事务读取。Admin `get/latest` 在单个 UOW 投影，结果顺序由 Repository 固定。
- Session 来源按 owner/date/可选 IDs 过滤。Admin worker-load 把 Session 内容、统计和三项 custom prompt 放进内部 bounded snapshot；该正文不得进入 OAuth task DTO、receipt、audit 或日志。
- Dream 继续为实时事件生成 UTC timezone ISO 时间。事件 ID 固定为 `evt_{task_uuid_without_hyphens}_{sequence padded to at least 6}`；event sequence 为 `1..2147483647`，worker 高水位为 `0..2147483647`。
- 新bus必须从worker-load高水位恢复。并发publish按sequence串行调用必需的persistence observer；该observer失败时不推进sequence、不广播。可选展示observer继续隔离。
- OAuth event history 保持：已知 Last-Event-ID 返回其 sequence 之后的事件；未知 ID 返回全量。进程内 bus 只补充订阅后 live 事件，合并时按 sequence 去重。
- 所有 write 保留首次 request ID。若 POST 结果未知，只查该 request 的 receipt；后台 receipt 还必须带原 task ID。receipt absent/不可用时返回 `ADMIN_WRITE_RESULT_UNKNOWN`，禁止第二次 POST。

## Child Thread 与 RTA 组合边界

`reflection-section.begin` 返回的 `rta_...` 仅保存在 Dream server owner 内，绑定 task、section、child Thread、service、subject、TTL、maximum expiry 和 `dream:read,dream:write`。它只允许以下六项接口：

1. `chat-user-message.persist`
2. `chat-message.persist`
3. `chat-thread.get`
4. `chat-thread.update-session`
5. `thread-system-config.get`
6. `session.list`

RTA 不进入 CLI 环境、MCP 参数、workspace 文件、日志或公开 DTO，也不能复用 Chat 的 server-persistence grant。Session MCP 使用 worker-load snapshot 绑定的私有 loopback broker；其 provider 不调用 `session.list` 获取正文。section owner 负责 authority renew/revoke，并在 ThreadFactory Phase 4 排空持久化、broker 与续期资源。

## 已完成接线

1. 已复算并固定16个operation hash、0061 capability hash、artifact hash以及最终Admin commit/tree。
2. `bind_frozen_reflection_task_contracts()`在import时构造源码闭集，生产factory注册同一实例；能力缺失或漂移在领域I/O前失败。
3. 公开Reflections/Reports路由使用request OAuth consumer；后台Engine使用`reflections:execute` service identity consumer，二者都无Dream PG fallback。
4. section persistence owner通过共享`AdminAgentTurnPersistence`边界接入现有Service/ThreadFactory，Session provider固定使用launch snapshot。
5. EventBus按Admin high-water初始化，必需持久化先于sequence提交和fan-out；SSE先订阅再查询历史并按sequence去重。
6. 正常账户、真实PostgreSQL、真实模型和日常Admin可见性仍需按本机真实业务测试协议单独验收；provider-free结果不替代这些验收。

## Dream 技术验证回执

- `uv run --project . --with pytest python -m pytest tests/test_reflections_agent.py tests/test_admin_reflection_task_data.py tests/test_reflections_config_router.py tests/test_admin_data_boundary.py -q`：exit 0，97 passed。
- 扩大受影响回归加入Admin request auth、section config、turn persistence、Claude service与Chat routes：exit 0，267 passed，9 subtests passed。
- `python3 -m py_compile`覆盖16个本次Python生产/测试文件：exit 0。
- AST闭包检查`backend/reflections_agent.py`、`backend/routers/reflections.py`、`backend/routers/reports.py`：三文件均无`database` import或旧Reflections persistence helper调用，exit 0。
- 11个受影响Markdown文件的本地链接及Reflections inventory/stage文件存在性检查：exit 0；`git diff --check`：exit 0。
- 一次扩展命令加入`tests/test_server_claude_agent.py`后为exit 1：同一命令332 passed、9 subtests passed，27项失败全部来自该旧Chat路由suite直接调用已迁移handler时未注入`AdminChatData`，报`Depends`无`get_thread`。该suite不属于本次Reflections改动，未通过恢复`database`别名规避。

未执行正常Dream/Admin/PostgreSQL、真实账户、Google、真实模型或日常Admin后台可见性验收。
