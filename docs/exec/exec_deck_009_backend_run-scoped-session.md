# Exec Report: DECK-009 - ClaudeAgent Run-Scoped Session

## 1. 执行上下文

- Task ID: `DECK-009` / `task_deck_009_backend_run-scoped-session`
- 执行 Issue: `SUO-318`
- 关联 Issue: `SUO-217`；合同证据 `SUO-314`；Stage readiness `SUO-315`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.4/7.5/13.3/18；`docs/design/deck/design_002_deck-plugin-decision-gates.md` 的 `DECK-GATE-DEC-017/018/020`
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` v1.9，Stage 2 / Wave 4
- 直接前置: `SUO-312`（task_008，done）；前置报告 `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md`
- 执行 Agent: `ExecTaskAgent`
- 执行时间: 2026-08-01（Asia/Shanghai）
- Checkout: Paperclip harness 已为本 run 获取 single-assignee execution lock；未重复 checkout

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`（只读，未修改）
- 受控填充副本: `$PAPERCLIP_RUN_SCRATCH_DIR/TASK-REQUIREMENT-task_deck_009.filled.md`
- 模型执行任务: `$PAPERCLIP_RUN_SCRATCH_DIR/MODEL-EXECUTION-task_deck_009.md`
- 输入 Issue: `SUO-318` scoped wake payload；fallback fetch 不需要
- 输入 Task/Stage: task_009 §0–14；Stage v1.9 §20；task_008 task/exec；DEC-017/018/020
- 填充后的执行目标: 持久化、幂等 AgentSession；Session 激活 + Receipt/Session 联合绑定 + `queued → running` + transition 单事务；reload guard；Voice 消息级来源
- 关键约束: 只读消费 `read_receipt()` 与精确五字段 `read_workflow_readiness()`；不调用 task_008 写路径；单节点 `local_persistent`、development/test；production、多节点、临时 runtime 与真实二进制 fail closed
- 工作树基线: `$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_009.status.before`；共享树既有大量前序/并发差异

## 3. 模型生成的执行任务

- 定义 strict/frozen AgentSession、状态机、canonical settings/hash/request key 与脱敏约束。
- 在 SQLite 增量追加 Session 表、单 live Session partial unique、不可变/状态 trigger、Workflow Run 双绑定与 Voice 来源 guard。
- SessionManager 只读校验完整 Receipt、五字段 projection、数据库权威 lock/Receipt/entry、插件/能力/settings 精确集合。
- 以持久 row + lease 争抢同 key owner；adapter 固定 `allow_query=False`；同 key重放、竞争 key fail closed。
- RunService 在 `BEGIN IMMEDIATE` 中依次激活 Session、联合更新 Run、追加唯一 transition；三处失败点均 rollback。
- adapter/数据库失败执行结构化映射与幂等 terminate 补偿；补偿不确认时保留 `creating` ownership，阻止第二个 live Session。
- RemoteInteractionGuard 拒绝所有 run-scoped Session reload，仅允许 development/test 的显式 idle management smoke 诊断，且不写 readiness、不建 Receipt、不授权 production。
- Workflow Run 新写入保存 `source_voice_thread_id/source_message_id/source_message_time`，纳入 fingerprint/retry 并与 Session ID 隔离；历史 thread-only 行保持只读兼容。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/agent_session.py` | create | AgentSession/SessionStartResult、状态机、canonical settings/hash、终态与不可变绑定校验 |
| `backend/services/claude_agent/session_manager.py` | create | task_008 双 reader 只读消费、Receipt/lock/entry 校验、settings 生成、ownership/lease、adapter 启动、原子激活、失败补偿与终止映射 |
| `backend/services/claude_agent/remote_interaction_guard.py` | create | run/session reload 拒绝、受限 management smoke 诊断合同 |
| `backend/models/workflow_run.py` | update | Receipt + Session 联合生命周期；Voice thread/message/time 与 ID 隔离 |
| `backend/services/workflow/run_service.py` | update | Voice 来源 create/retry/fingerprint；Session-aware `queued → running` 单事务与绑定校验 |
| `backend/database.py` | update | 增量 schema upgrade、agent_sessions/索引/trigger、联合绑定/source guard |
| `backend/tests/test_agent_session.py` | create | 9 项定向测试，含同 key 并发、Receipt drift、三处 DB 失败、补偿、reload、终态和脱敏 |
| `backend/tests/test_workflow_run.py` | update | 联合启动 fixture、Voice 来源元组/幂等/不可变、既有状态机回归 |
| `backend/tests/test_runtime_plugin_reconcile.py` | update | 仅把 receipt-only running 联调对齐为 Receipt + creating Session 联合原子启动；task_008 其余断言保持 |
| `docs/exec/exec_deck_009_backend_run-scoped-session.md` | create | 本 task 唯一正式执行报告 |

禁止范围确认：未修改 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、其他 `docs/exec/`、`frontend/`、SSE endpoint、task_008 reconcile/materialization/runtime_plugin 源文件、Preflight 源文件、依赖锁或部署配置。共享树中这些路径的既有差异未清理、覆盖或归因于本 task。

## 5. 验收映射

| 验收项 | 结果 | 证据 |
|---|---|---|
| 独立 Issue / single assignee / execution lock | PASS | scoped wake + harness checkout；未重复请求 checkout |
| task_008 只读边界 | PASS | SessionManager 仅调用 `read_receipt()` / `read_workflow_readiness()`；闭集静态搜索无 reconcile/materialization/CLI/Receipt 写调用 |
| Session 全绑定不可变 | PASS | strict/frozen 模型 + `agent_sessions_immutable_binding` + partial unique/状态 trigger；篡改与终态复活测试拒绝 |
| 同 key 幂等/并发单 owner | PASS | 并发第二调用返回同 creating attempt，adapter start 仅 1 次；竞争受信 settings source 返回 `AGENT_SESSION_CREATE_CONFLICT` |
| 原子联合启动 | PASS | Session active、两个 Run binding、running、status_version、唯一 transition 同事务；成功仅一条 running transition |
| 三处数据库失败 rollback | PASS | `session_updated`、`status_updated`、`status_transition_written` 注入均保留 queued + NULL/NULL + creating rollback，随后 terminate 补偿并记 failed |
| adapter/terminate 失败映射 | PASS | adapter start 失败映射 Session/Run failed 且不绑定；terminate 未确认保留 live creating ownership 并拒绝竞争 attempt |
| 第一条 query 前完成 | PASS | adapter 唯一入口固定 `allow_query=False`；fake 捕获值仅 `[False]`；SessionManager 无 query 方法/调用 |
| settings/plugin set 不漂移与 reload guard | PASS | canonical settings 精确三 key、能力/插件/版本/digest exact；run-scoped 活动/历史 Session 均拒绝 reload |
| management smoke 限域 | PASS | 仅显式 idle management ID、已物化/缓存、版本/digest/capability 不变、development/test 可诊断；返回不写 readiness/Receipt、不授权 production |
| Voice 消息级来源与 ID 隔离 | PASS | 三者同空同有、timezone、fingerprint/retry/immutability 测试；thread/session ID 相等模型拒绝 |
| production/multi-node/ephemeral fail closed | PASS | Receipt/model/guard 仅接受 development/test、pool==environment、local_persistent；production/pool drift 定向拒绝 |

## 6. 测试与验证

| 命令 | Exit code | 结果 |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_agent_session -v` | 0 | 9/9 PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_workflow_run backend.tests.test_workflow_preflight backend.tests.test_runtime_plugin_reconcile -v` | 0 | 35/35 PASS（17 Workflow Run + 9 Preflight + 9 task_008） |
| Task 指定九文件 `py_compile` | 0 | PASS；pycache 定向 run scratch |
| Task 指定 `git diff --check` | 0 | PASS |
| Task 指定尾随空白 `rg` | 0 | PASS；无匹配 |
| 实现前后 `git status --short` 闭集核验 | 0 | PASS；本 task 新增/修改仅十个授权路径 |

测试输出中的 `Memory workspace config backfill skipped: No module named 'memory_workspace_defaults'` 是既有 `create_tables()` 非阻塞提示；全部 unittest 命令返回 exit code 0。

### 验证证据

- 完整 Receipt 与五字段 projection 分开读取；strict projection key 集合被锁定为精确五项。
- 完整 Receipt 同数据库 append-only Receipt/entry、权威 lock digest、artifact set、plugin/version/digest/capability、placement/policy 逐项比较。
- adapter start 参数捕获证明 `allow_query=False`；同 key 并发期间只有一个 start。
- 三处 transaction checkpoint 的失败注入都没有 running transition、部分 binding 或 active Session 留存。
- 补偿未确认场景的 row 保持 `creating + compensation_pending`，partial unique 阻止第二个 `creating|active` Session。
- management smoke 允许结果明确 `diagnostic_only=true`、`writes_readiness=false`、`creates_receipt=false`、`production_authorized=false`。

## 7. 共享工作树与路径闭集

- before 基线已保存于 `$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_009.status.before`；基线包含 `backend/database.py` 修改以及 Workflow Run/task_008 测试等前序文件。
- 本 Agent 未执行 `git add`、`git reset`、`git checkout`、清理或覆盖操作。
- 本轮期间共享树的 Git index 展示发生并发变化：若干前序新增路径由单文件 `A` 展示转为未跟踪目录/文件 `??`；文件内容仍可读且 44 项 task_009+前置测试全部通过。该 index 状态变化不是本 task 产出，不归因于 ExecTaskAgent。
- task_009 实际新增差异：三个新生产文件、`test_agent_session.py` 与本报告；实际增量修改：WorkflowRun 模型/服务、database、两个既有测试。
- 闭集外新增/修改均为 before 基线或共享树并发差异；未由本 Agent读取后改写或清理。
- 上游归档 owner/action：各既有 task owner 在其独立 Issue/归档流程中处理共享树 staging/commit；本 task 无需且不得代为整理 index。

## 8. 风险、阻塞与未验证项

- 阻塞: 无。
- 已验证限域: SQLite 单写者、development/test、单节点 persistent runtime、注入 fake adapter/management context。
- 未验证且明确不在本 task 授权内: 真实 Claude Code 二进制/SDK、真实 marketplace、production、多节点、临时 runtime、CAS/冷存储/restore/purge、production rollout。
- fake/smoke 结果仅证明端口合同与 fail-closed 编排，不构成 `production_ready` 证据。
- `DECK-GATE-DEC-017` 继续 conditional_frozen；legacy_unverified 只在 development/test 原样消费。
- Stage 3 Voice 来源卡片/运行详情和 Stage 4 事件审计/撤销 evidence 仍由对应后续 task owner 实现；本 Issue 无需创建越权 follow-up。

## 9. 完成状态

- [x] 已完成实现
- [x] 已完成 Session 定向测试
- [x] 已完成 Workflow Run/Preflight/task_008 前置回归
- [x] 已完成失败注入、静态、格式与路径闭集验证
- [x] 已记录共享树、风险、未验证项与回滚
- [x] 已满足本 task 全部验收条件
- [x] 可进入 review / audit

最终 Paperclip disposition：`SUO-318 = done`。本 Issue 内无剩余实现或验证工作。

## 10. 回滚建议

- 代码回滚: 删除三个 task_009 新生产文件与 `backend/tests/test_agent_session.py`；从 WorkflowRun 模型/服务、database 和两个既有测试中移除本报告列出的 task_009 增量区段；保留 task_006/007/008 既有内容。
- 数据回滚: 若环境已创建 `agent_sessions`，先阻止新 Session 并确认无 Workflow Run 绑定，再以受控迁移删除 task_009 trigger/index/table 和 `source_message_id/source_message_time` 新列的兼容迁移；不得 update/delete 既有 append-only Receipt/entry。
- 运行回滚: 保留 `runtime_load_receipts` 与历史 Run/Session 审计事实；不要复活终态 Session、清空已绑定 ID 或把 Voice thread 改作 Session ID。
- 注意事项: SQLite `ALTER TABLE` 列回滚需要专用迁移窗口和表重建方案；不得在共享工作树用破坏性 Git 命令代替数据库迁移。
