# Exec Report: DECK-013 - 统一事件合同与审计

## 1. 执行上下文

- Task ID: `task_deck_013_backend_events-audit` / 逻辑任务 `DECK-013`
- Execute Issue: [SUO-330](/SUO/issues/SUO-330)
- 来源控制项: [SUO-217](/SUO/issues/SUO-217)
- 关联 Issue: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 `DECK-013`
- 关联设计稿: `docs/design/deck-plugin-voice-ink-dream-integration.md` §15.1、§15.2
- 关联 Task: `docs/task/task_deck_013_backend_events-audit.md`
- 关联 Stage: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` §21.2，Stage 4 / Wave 1
- 执行 Agent: `ExecTaskAgent` (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`)
- 执行时间: `2026-08-01T23:22:30+08:00`
- 执行锁: Paperclip harness 已为本 run checkout [SUO-330](/SUO/issues/SUO-330)，未重复 checkout
- 限域: development/test；本报告不声明 production-ready、多节点 ready 或真实消息中间件集成完成

### 工作树基线与冲突处理

执行前 `git status --short` 显示共享工作树已有大量未提交差异，包括 `backend/database.py` 中 Story Workspace review persistence、Deck Plugin、Workflow Run、runtime reconcile、Agent Session 等其他任务增量，以及多个 design/issue/task/stage/frontend 文件。处理方式：

- 未 reset、checkout、删除、格式化或覆盖任何既有差异。
- `backend/database.py` 仅加入 `create_event_tables()` 及 `create_tables()` 中的一次调用；未改写其他表、迁移或业务状态机。
- 实际写入严格限制在本 Task 六路径闭集。

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`
- 执行角色: `ExecTaskAgent`
- 输入 Issue: [SUO-330](/SUO/issues/SUO-330)，high / in_progress / standard
- 输入 Task: `task_deck_013_backend_events-audit`，backend，唯一映射 `DECK-013`
- 输入 Stage: Stage 4 / Wave 1；Stage §21.2 九项 readiness 对 task_013 全部为 ready
- 前置依赖: `DECK-007`、`DECK-009`；Stage 复核确认均满足
- 填充后的执行目标: 实现统一、严格、脱敏的事件 envelope；以 SQLite append-only events 表为权威来源；持久化后执行可重试的至少一次投递；消费者按 `event_id` 去重并按 `aggregate_version` 顺序处理
- 交付类型: backend implementation + unit/integration-style tests + 本唯一执行报告
- 关键约束: 不接入/改造消息中间件，不修改其他域生产者/消费者，不携带 prompt/secret/settings/用户邮箱，不声明 production-ready
- 允许范围: Task §11 所列 5 个实现/测试路径及本报告
- 禁止范围: 其他 `docs/exec/`、design/issue/task/stage、frontend、依赖锁、部署配置、其他业务域和未列明路径
- 验收条件: Task §9 全部 10 项原样纳入下方矩阵
- 测试要求: 指定 unittest 命令、`git diff --check`，并补充内存 SQLite schema 初始化检查
- 回滚要求: 仅回退本闭集；已有事件不得删除或改写，兼容回滚保留 events 表为只读审计证据
- 未满足准入项: 无

## 3. 模型生成的执行任务

- 任务目标: 交付 adapter-neutral 的最小事件基础设施，不越权修改业务状态机或真实消息设施。
- 实现范围:
  1. 严格 `EventEnvelope`、10 类点分命名事件与每类最小 payload 校验。
  2. 递归敏感字段和邮箱值拒绝，输出同一已验证 envelope 的 JSON-safe 前端投影。
  3. SQLite events 表、索引、唯一 aggregate version 和 UPDATE/DELETE 阻断触发器。
  4. persist-first emitter；同一 envelope 重试只保留一条审计记录但重新投递，从而形成至少一次语义。
  5. consumer 的 event ID 去重、aggregate 顺序、乱序暂存/自动 drain、超时缺口告警。
  6. 覆盖生成、持久化、投递失败重试、去重、顺序、脱敏、审计不可变和 schema 幂等测试。
- 文件范围: 仅下方 6 个文件。
- 验证方式: Task 指定 unittest、内存 SQLite schema smoke、`git diff --check`、实际路径核对。

## 4. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/models/events.py` | create | 新增严格 immutable envelope、10 类 `CanonicalEventType`、每类最小 payload 字段、递归脱敏与 JSON-safe projection |
| `backend/services/events/event_emitter.py` | create | 新增基于持久化历史自动分配 aggregate version、SQLite persist-first 写入、同 ID 幂等重投递、queue/projection adapter 注入及明确失败语义 |
| `backend/services/events/event_consumer.py` | create | 新增 event ID 去重、aggregate version 顺序、乱序 buffer/drain、stale/version 冲突拒绝和缺口超时告警 |
| `backend/database.py` | update | 最小追加 `events` 表、3 个索引、aggregate/version 唯一约束、UPDATE/DELETE append-only 触发器与幂等初始化入口 |
| `backend/tests/test_events.py` | create | 新增 12 项 unittest，覆盖 Task §8 规定场景及 schema/append-only 证据 |
| `docs/exec/exec_deck_013_backend_events-audit.md` | create | 唯一正式执行报告 |

### 变更摘要

- 数据库先写入并提交，随后调用可注入的 queue publisher 与 SSE/WebSocket projection publisher。
- publisher 失败时抛出带 `persisted=True` 的错误；调用方使用相同 envelope 重试会再次投递，但不会新增重复审计行。
- 同 aggregate 的版本取已持久化最大版本加一，数据库唯一约束作为并发冲突的最终防线。
- consumer 默认从版本 1 开始，可通过 `initial_versions` 接入调用方持久化 checkpoint；当前 task 不越权新增 consumer checkpoint 表。
- 脱敏验证递归拒绝 prompt、secret、token、credential、authorization、cookie、password、完整 settings 和 email 字段/值；ID/ref/hash/digest 形式的 prompt/secret/settings 引用允许。
- 前端投影不读取数据库原始以外的数据，也不二次拼接日志；它只序列化已经通过模型脱敏校验的 envelope。

## 5. 测试与验证

### 已执行测试

1. 指定目标测试：

   ```text
   PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_events -v
   Ran 12 tests in 0.039s
   OK
   ```

   结果：12 passed，0 failures，0 errors。

2. schema 集成 smoke：

   ```text
   PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -c '<in-memory create_tables + events/table trigger assertions>'
   events schema integrated
   ```

   结果：通过。命令同时输出仓库既有 `memory_workspace_defaults` 顶层导入 warning；`create_tables` 完成且 events 表与两个 append-only trigger 断言通过，此 warning 不由本 task 引入。

3. 差异检查：

   ```text
   git diff --check
   ```

   结果：通过，无输出。

### 自动化覆盖证据

| 场景 | 测试证据 |
|---|---|
| envelope 字段与 10 类事件 | `test_all_ten_canonical_event_contracts_validate` |
| 最小 payload 合同 | `test_payload_requires_minimum_contract_fields` |
| prompt/secret/token/settings/email 脱敏 | `test_sensitive_keys_and_email_values_are_rejected_recursively` |
| 发射 → 持久化 → projection | `test_persist_first_delivery_and_sanitized_projection` |
| 至少一次投递与同 ID 重试 | `test_retry_same_id_redelivers_without_duplicate_audit_row`、`test_delivery_failure_retains_authoritative_row_for_retry` |
| aggregate version 单调 | `test_aggregate_versions_follow_persisted_authority` |
| consumer 去重 | `test_duplicate_delivery_is_processed_once` |
| 乱序暂存与重排 | `test_out_of_order_events_are_buffered_and_drained` |
| 前置版本超时告警 | `test_missing_predecessor_emits_one_timeout_alert` |
| 数据库 append-only | `test_database_events_are_append_only` |
| schema 幂等与索引 | `test_schema_initialization_is_idempotent` + schema smoke |

### 未执行测试及原因

- 未接入真实 broker、SSE server 或 WebSocket server：Issue 明确禁止修改消息中间件和其他业务域生产/消费实现；本 task 通过注入 adapter 和脱敏 projection 证明合同可消费。
- 未运行全工作区测试：Task 只要求最小目标 unittest 与 diff 检查；共享工作树含多个并行任务差异，全量测试不能为本 task 提供更清晰归因。
- 未验证 production、多节点 consumer checkpoint、长期 retention/purge：均在本 Task development/test 闭集之外。

## 6. 验收矩阵

| # | Task §9 完成标志 | 结果 | 证据 |
|---|---|---|---|
| 1 | 统一事件 envelope 结构完整 | ✅ | 严格 `EventEnvelope` 全字段、timezone、版本与 ID 校验 |
| 2 | 10 类规范事件覆盖设计稿 §15.2 | ✅ | `CanonicalEventType` 恰好 10 类；逐类 payload 自动化验证 |
| 3 | 至少一次投递，按 `event_id` 去重 | ✅ | persist-first + 同 envelope 重投递；consumer duplicate test |
| 4 | 同 aggregate 的 `aggregate_version` 单调递增 | ✅ | persisted max + 1、数据库 UNIQUE、顺序测试 |
| 5 | 禁止 prompt、secret 或完整 settings | ✅ | 递归敏感字段/邮箱校验及负向测试 |
| 6 | SSE/WebSocket 可消费脱敏投影 | ✅ | `sanitized_projection()` + projection publisher 测试；真实 transport 不在授权范围 |
| 7 | 数据库审计事件是权威来源 | ✅ | 投递前提交 events；投递失败后行仍存在；UPDATE/DELETE 触发器阻断 |
| 8 | 单测覆盖生成、投递、去重、顺序 | ✅ | 12 项目标测试全部通过 |
| 9 | 变更仅位于 5 个实现/测试路径及唯一报告 | ✅ | 结束路径核对；未触碰其他任务路径 |
| 10 | 报告回填命令、结果、验收、diff 与回滚 | ✅ | 本报告 §5、§6、§8 |

## 7. 风险与阻塞

- 风险: `build_envelope()` 的 max+1 是单节点便利分配；并发竞争由数据库唯一约束拒绝并要求重建。Task 明确限于 development/test，不宣称多节点 allocator ready。
- 风险: consumer checkpoint 默认驻留于实例内存；调用方可用 `initial_versions` 恢复，但 production durable checkpoint 不在本闭集。
- 风险: 实际 broker/SSE/WebSocket adapter、真实业务事件生产点尚未连接；这些路径被当前 Issue 明确禁止修改。
- 风险: events 表 retention、archive、purge、cold recovery 仍受 `DECK-017` / production evidence gate 管理，本实现不删除历史事件。
- 阻塞: 无。本 Issue 所需 development/test 实现与最小验证已完成。
- 需要上游澄清的问题: 无；production adapter/checkpoint/retention 如需推进，应由上游建立独立授权 task。

## 8. 完成状态

- [x] 已完成实现
- [x] 已完成指定测试
- [x] 已记录全部变更与共享工作树处理
- [x] 已逐项满足 Task §9 十项完成标志
- [x] 已确认禁止范围未修改
- [x] 可进入 review / audit；Paperclip Issue 本身无剩余工作，可标记 `done`

## 9. 回滚建议

- 回滚文件: 仅 `backend/models/events.py`、`backend/services/events/event_emitter.py`、`backend/services/events/event_consumer.py`、`backend/database.py` 的 events 初始化最小区段、`backend/tests/test_events.py`。
- 不回滚/删除: 本正式报告；任何已经持久化的 `events` 行；承载既有审计证据的 events 表。
- 无数据环境: 可移除新增模块、测试，以及 `create_event_tables()` 和其调用。
- 已有数据环境: 先停止新 emitter/consumer，再回退调用代码；保留 events 表、索引和 append-only 保护为只读审计来源，不执行 DROP/DELETE/UPDATE。
- 回滚验证: 重跑目标 unittest（按回滚预期调整导入范围）和 `git diff --check`，确认其他 Workflow Run、Session、Deck Plugin 与 Story Workspace 差异未被改变。

## 10. 执行完成报告

SUO-330 的 development/test 交付已完成。事件合同、权威审计存储、至少一次重投递、consumer 去重/顺序/缺口告警、脱敏 projection 与测试证据均落在授权闭集内；未合并其他 task、未改写 design/issue/task/stage/frontend 或业务状态机，也未宣称 production-ready。
