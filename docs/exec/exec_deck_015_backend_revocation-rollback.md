# Exec Report: DECK-015 - 安全撤销、回滚与降级路径

> **执行状态**: completed（仅 development/test）
> **Production 状态**: **未通过 / 不得宣称 production-ready**
> **执行 Issue**: [SUO-332](/SUO/issues/SUO-332)
> **执行 Agent**: ExecTaskAgent
> **执行日期**: 2026-08-01（Asia/Shanghai）

## 1. 执行上下文

| 字段 | 值 |
|---|---|
| Task ID | `task_deck_015_backend_revocation-rollback` / logical `DECK-015` |
| 执行 Issue | [SUO-332](/SUO/issues/SUO-332) `[execute][deck-plugin][task_015] 实现 Revocation Rollback` |
| 来源控制项 | [SUO-217](/SUO/issues/SUO-217) |
| Parent / Ancestor | [SUO-217](/SUO/issues/SUO-217)；[SUO-216](/SUO/issues/SUO-216) |
| 关联 Task | `docs/task/task_deck_015_backend_revocation-rollback.md` |
| 关联设计 | `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.2、§12.2、§12.3；`docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.4 |
| 关联 Issue 清单 | `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 `DECK-015` |
| 关联 Stage | `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` §21.2，Stage 4 / Wave 1 |
| Checkout | harness 已为本 run 签出；未重复调用 checkout |
| Work mode / 优先级 | `standard` / `high` |
| 执行范围 | development/test；单节点本地持久化验证 |

### 1.1 执行前检查

- [x] task 任务内容存在且非空。
- [x] Issue、Task、Stage 映射唯一。
- [x] `docs/task/TASK-REQUIREMENT-FORMAT.md` 存在并已完整读取。
- [x] Task 设计引用和 `DECK-GATE-DEC-019` 冻结合同已读取。
- [x] harness 已取得执行锁。
- [x] 允许修改范围为精确五路径闭集。
- [x] 禁止修改范围、12 项验收口径、目标测试和回滚边界均已确认。
- [x] `backend/.venv/bin/python` 存在，可运行仓库既有 `unittest` runner。

### 1.2 工作树基线与冲突处理

执行前 `git status --short` 显示共享工作树存在大量既有 tracked/untracked 差异，涉及 backend、frontend 及 design/issue/task/stage/exec 文档。五个本 task 授权目标路径当时均不存在，未与既有差异重叠。

处理方式：只新建本报告与四个 Task 授权文件；未 reset、checkout、删除、格式化或覆盖任何既有差异。禁止范围内的既有差异均保持原样。

## 2. `TASK-REQUIREMENT-FORMAT.md` 填充摘要

| 模板字段 | 填充值 |
|---|---|
| 模板路径 | `docs/task/TASK-REQUIREMENT-FORMAT.md` |
| EXEC_AGENT_NAME | `ExecTaskAgent` |
| PAPERCLIP_ISSUE_ID / TITLE | `SUO-332` / `[execute][deck-plugin][task_015] 实现 Revocation Rollback` |
| SOURCE_ISSUE_ID | `SUO-217`，逻辑实现项 `DECK-015` |
| DOMAIN | `backend` |
| STATUS_AND_WORK_MODE | `in_progress / standard`（执行开始时） |
| TASK_DOCUMENT_PATH | `docs/task/task_deck_015_backend_revocation-rollback.md` |
| TASK_GOAL | 实现冻结的 DISABLE / REVOKE / EMERGENCY、确定性 impact manifest、grace/hard-stop、取消/通知幂等、受限降级和显式 future-only rollback |
| TASK_DEPENDENCIES | `DECK-003` Installation 生命周期；`DECK-007` Workflow Run；逻辑事件边界 `DECK-013` |
| STAGE_AND_WAVE | Stage 4 / Wave 1 |
| STAGE_ENTRY_CONDITIONS | Stage 1/2 Gate 已通过；task_003/task_007 已完成；§21.2 九项 readiness 通过 |
| PARALLELISM_CONSTRAINTS | 可与 task_013/task_014 并行，但必须独立 checkout、独立报告、不得合并写入范围 |
| GATE | `DECK-GATE-DEC-019` 设计 frozen；真实 11 项证据、独立 reviewer 签署和 rollout approval 仍阻断 production |
| UNMET_STAGE_CONDITIONS | development/test execute 无阻塞；production Gate 明确未满足且不属于本次放行 |
| STATIC / DIFF | AST/import 由目标测试覆盖；`git diff --check` |
| UNIT / INTEGRATION | `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_revocation_rollback -v`；同模块生成 11-case development evidence pack |
| E2E | N/A：本 task 禁止修改/接入生产身份服务、runtime kill provider 与部署配置；通过注入 adapter 的确定性集成夹具验证 |

### 2.1 写入边界（闭集）

| 路径 | 动作 | 最小允许变更 |
|---|---|---|
| `backend/services/deck_plugin/revocation_service.py` | 新建 | 撤销、impact、取消/通知 outbox、append-only SQLite repository、审计/evidence 合同 |
| `backend/services/deck_plugin/degradation_service.py` | 新建 | manifest 声明 + 服务端 mode catalog 的 fail-closed 降级判定 |
| `backend/services/deck_plugin/rollback_manager.py` | 新建 | 显式 rollback、digest/兼容性前置检查、future-only/audit 防护 |
| `backend/tests/test_revocation_rollback.py` | 新建 | 本 task 的 `unittest` 单元/集成测试与 development evidence pack |
| `docs/exec/exec_deck_015_backend_revocation-rollback.md` | 新建 | 本 task 唯一正式报告 |

禁止修改：其他 `docs/exec/`、`docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`frontend/`、身份/安全策略内部实现、Workflow Run 状态机、依赖锁、部署配置和未列明路径。

### 2.2 填充后的 Model Execution Instruction

仅实现上述单一 Task；保持现有 Workflow Run/身份服务边界，以注入 adapter 消费服务端授权和 Run CAS/termination 能力；撤销域自行持久化 barrier、manifest、command/notification outbox、receipt、incident、quarantine 与 append-only audit。只写五路径闭集，执行目标 unittest 和 diff 检查；任何 production reviewer/rollout Gate 缺失必须保留为未验证，不得扩大为 production-ready。

## 3. 模型生成的执行任务

1. 实现 `RevocationService` 及冻结的三等级行为、角色分离、四 target 规范化、最小 scope、impact hash、60/300/0 秒时限和安全终态防护。
2. 实现同提交边界的 SQLite barrier/manifest/cancel command/notification outbox、runtime inbox/termination/isolation receipt、incident、quarantine 和 append-only trigger；保留 in-memory adapter 供确定性测试。
3. 实现通知固定六次计划、取消 replay、scope 扩展/覆盖/强度串行规则、10 秒未确认 incident 和 `RUN_TERMINAL_CONFLICT`。
4. 实现仅在 manifest 声明且服务端 mode definition 精确匹配时允许的降级；required、权限不足、安全撤销、output schema 变化全部 fail closed。
5. 实现显式 rollback manager：published/deprecated、installed/ready、digest、host/runtime compatibility、runtime materialization 检查，只改 default version，不迁移 binding 或历史 run，并追加 actor audit。
6. 使用目标 `unittest` 覆盖上述合同并生成 11-case development evidence manifest；验证独立 reviewer 签名和 rollout approval 缺任一项时 production Gate 始终为 false。

## 4. 实现说明

### 4.1 撤销与取消

- `DISABLE`：提交未来操作阻断 barrier；既有 queued/running/history 不进入 `cancelling`，不生成 cancel command，不 quarantine。
- `REVOKE`：默认 60 秒，接受 `0..300` 秒；CAS 进入 `cancelling`，grace 内 graceful 请求，deadline 到期执行 hard-stop；重复 `(revocation_id, workflow_run_id)` 复用稳定 command/receipt。
- `EMERGENCY`：固定零 grace，验证最长 15 分钟 JIT break-glass，立即 hard-stop；未事前批准时记录 30 分钟追认 deadline，逾期生成 incident/freeze-principal action。
- hard-stop 发出后未在 10 秒内确认 termination 或 isolation 时保持 `cancelling` 并生成 `SECURITY_TERMINATION_UNCONFIRMED`；不伪造终态。
- 安全路径试图提交 `completed` 时拒绝并追加 `RUN_TERMINAL_CONFLICT`。
- 终态只映射为：ack → `cancelled`；runtime 异常且 isolation receipt 存在 → `failed`；未确认 → `cancelling`。

### 4.2 持久化、幂等与审计

- SQLite repository 在撤销域内部创建自有表，不修改共享 `backend/database.py`。
- barrier、immutable impact manifest、cancel command outbox、notification outbox 与 effective audit 在同一事务提交。
- revocation record、manifest、command、runtime receipt、audit、incident、quarantine 表由 SQLite trigger 拒绝 update/delete；notification outbox 只允许递增 delivery 状态，禁止删除。
- 相同 idempotency key + 相同语义返回原 revocation/manifest；不同语义返回冲突。
- 已被同级或更强同 scope 撤销覆盖时返回 `already_covered_by_revocation_id`；scope 扩大生成新 record 并填写 `extends_revocation_id`。
- impact manifest 对所有 ID 去重、排序，并生成 `sha256`；授权范围外解析不截断，直接 fail closed。
- 通知按 `0s / 30s / 2m / 10m / 30m / 2h` 最多六次；穷尽失败追加 delivery incident，绝不延迟 hard-stop。

### 4.3 降级

- manifest 的 `runtime.degraded_modes` 只是准入白名单；替代步骤、允许省略的 optional plugin/capability 和 output schema 由服务端 `DegradedModeDefinition` 提供。
- 选择最小权限且 ID 稳定的匹配 mode。
- 成功结果强制 `user_confirmation_required` 和 `runtime_load_receipt_required`，携带 `degraded_mode_id`。
- required/未知 plugin、授权不足、安全撤销、schema 变化或未声明 mode 均返回结构化拒绝。

### 4.4 回滚

- 仅接受当前 installation 已 ready、目标版本已安装且 release 为 published/deprecated。
- 校验 manifest hash 与 runtime lock 绑定、所有 sha256 digest 的语法和注入式真实 verifier、当前 host/runtime compatibility、materialization/load-smoke。
- 复用既有 InstallationService 的 revision/CAS 更新，仅切换 `default_version`。
- 回滚前后比较现有 binding/workflow run 投影，发现意外历史修改即失败；成功追加 actor/from/to audit event。
- 升级目标 load-smoke 失败时旧 `ready/default_version` 保持不变。

## 5. 实现变更记录

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/services/deck_plugin/revocation_service.py` | create | 三等级撤销、授权/impact/grace/terminal/notification/evidence 合同；in-memory + durable SQLite append-only repository |
| `backend/services/deck_plugin/degradation_service.py` | create | manifest + server catalogue 的受限降级 evaluator |
| `backend/services/deck_plugin/rollback_manager.py` | create | future-only rollback manager 与结构化错误/audit result |
| `backend/tests/test_revocation_rollback.py` | create | 15 个目标测试，覆盖撤销、降级、SQLite 持久化、回滚、升级失败和 11-case evidence pack |
| `docs/exec/exec_deck_015_backend_revocation-rollback.md` | create | 唯一正式执行报告 |

禁止范围确认：未修改 `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、其他 `docs/exec/`、`frontend/`、Workflow Run 状态机、安全策略/身份服务、依赖锁或部署配置。

## 6. 测试与验证

### 6.1 已执行命令

```text
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_revocation_rollback -v
```

结果：`Ran 15 tests in 0.041s — OK`。解释器为仓库既有 `backend/.venv/bin/python`（CPython 3.12）；未新增测试框架，且 `PYTHONDONTWRITEBYTECODE=1` 避免产生越界缓存文件。

测试过程中共享 `database.create_tables` 打印 `Memory workspace config backfill skipped: No module named 'memory_workspace_defaults'`；这是既有可选 backfill 的提示，未转化为 unittest failure，15 项均为 `ok`。

```text
git diff --check
```

结果：通过，无 whitespace error 输出。

### 6.2 目标测试覆盖

| 测试 | 覆盖 |
|---|---|
| `test_disable_blocks_new_operations_without_touching_active_or_history` | DISABLE 阻断未来操作、不取消既有 run、不改历史 |
| `test_revoke_default_grace_hard_stop_and_idempotent_replay` | 默认 60 秒、deadline hard-stop、相同 key/command/manifest replay |
| `test_grace_boundaries_role_separation_and_scope_fail_closed` | 0/300/301 边界、双人控制、最小 scope fail closed |
| `test_scope_expansion_creates_new_record_linked_to_original` | scope 扩大产生新 revocation 并关联 `extends_revocation_id` |
| `test_emergency_is_immediate_and_unconfirmed_waits_ten_seconds` | EMERGENCY 零 grace、15 分钟 JIT、10 秒未确认、30 分钟追认 |
| `test_terminal_mapping_conflict_guard_and_concurrent_suppression` | cancelled/failed/cancelling、isolation receipt、completed 冲突、更强升级/抑制 |
| `test_notification_six_attempts_fail_without_delaying_hard_stop` | 六次固定退避、delivery incident、通知失败不延迟 hard-stop |
| `test_four_target_manifest_is_sorted_hashed_and_scope_not_truncated` | 四 target、排序/hash 重放基础、跨授权影响不截断 |
| `test_sqlite_repository_persists_barrier_outboxes_and_append_only_audit` | 重启可读、command/notification/runtime receipt、quarantine、update/delete 拒绝 |
| `test_stage4_evidence_pack_requires_all_cases_reviewer_and_rollout` | 11-case pack、manifest hash、缺项失败、review/rollout Gate |
| `test_degradation_requires_manifest_declaration_and_same_schema` | manifest 声明、optional 替代步骤、相同 output schema、确认/load receipt |
| `test_required_permission_and_revocation_never_auto_degrade` | required、权限不足、安全撤销禁止自动降级 |
| `test_explicit_rollback_changes_only_default_and_appends_audit` | rollback 只切 default，binding/run 投影不变，actor audit |
| `test_rollback_fails_closed_on_digest_or_compatibility` | digest/compatibility fail closed，不切 default |
| `test_failed_upgrade_preserves_old_ready_default` | 升级 load-smoke 失败保留旧 ready/default |

### 6.3 Development evidence pack

本次通过测试生成的代表性 pack：

- `evidence_pack_id`: `s4rep_f0352e435c8aace6a0c6bf318d9bb66a`
- `evidence_manifest_sha256`: `sha256:f0352e435c8aace6a0c6bf318d9bb66a90111927ae0f625caaacd48000efacd0`
- `revocation_id`: `rev_8ebc6e193eed4974a620e7733c289912`
- `impact_manifest_id`: `rim_f4a16ca6cdb1e073afb0bea143941a4a`
- `impact manifest sha256`: `sha256:f4a16ca6cdb1e073afb0bea143941a4a9651c95be1be1a92e4e5955070235c24`
- representative command IDs: `scc_c9d63578bd1ed174b407f352826cea72`, `scc_53c3f299be2df9e9b0204bf0da829c46`
- representative event IDs: `evt_12d41ae3cb7e434ba4ffd246c6ce01fc`, `evt_60cb33cc1fec47a6afba34b73437fa7c`, `evt_e0304837bfdd42f88892970a4dab50f9`
- termination receipt IDs: `trr_22fedfc5f1ce69cdb879d9f2bda56242`, `trr_9c75ea41914e4c9ff4147ea74f1c810d`
- representative notification IDs: `ntf_0c1c92a2fa709a0084ac98a67b4fe99a`, `ntf_b58d43b79d7b9e1f8dd18a73c8143d89`

| 11 项 evidence case | 测试/原始证据入口 | Development 结果 |
|---|---|---|
| 三等级权限与行为矩阵 | `test_disable...`、`test_grace_boundaries...`、`test_emergency...` + revocation/manifest/event IDs | pass |
| 四目标影响解析 | `test_four_target_manifest...` + impact manifest/hash | pass |
| scope 扩大、重复与并发 | `test_scope_expansion...`、`test_revoke...replay`、`test_terminal...suppression` | pass |
| DISABLE 不中止 | `test_disable...` | pass |
| REVOKE grace→hard-stop | `test_revoke_default_grace...` + command/termination receipt | pass |
| EMERGENCY 立即硬停 | `test_emergency...` + hard-stop event/receipt | pass |
| 重复取消与至少一次投递 | `test_revoke...replay` + stable command/runtime receipt | pass |
| 终态映射与冲突防护 | `test_terminal_mapping...` + isolation/terminal-conflict event | pass |
| append-only 审计 | `test_sqlite_repository...` + trigger 拒绝证据 | pass |
| 通知时序与失败 | `test_notification_six_attempts...` + notification/incident IDs | pass |
| 隔离与 superseding 恢复合同 | quarantine 持久化、不可 unrevoke、pack Gate 测试；恢复要求保持为新 release/policy + new run/session | contract pass（非生产演练） |

证据边界：这些 ID 来自 development/test fixture run，证明实现和 evidence schema 可追溯；它们不是 production 环境演练证据。pack 内 `production_gate_satisfied=false`，因为没有独立 reviewer 签名和 rollout approval ID。

## 7. 验收结果

Stage §21.2 记载“12 项”；Task §9 当前正文显示 11 个 checklist bullet。为不删除原始条目，本报告将第一个复合条目拆为“行为矩阵”和“权限/scope/时限/审计”，得到以下 12 个可验证结果。

| # | 验收条件 | 结果 | 证据 |
|---:|---|---|---|
| 1 | DISABLE / REVOKE / EMERGENCY 确定性行为矩阵 | pass | 三等级目标测试 |
| 2 | 角色分离、scope、grace/hard-stop、通知与审计符合 frozen DECK-019 | pass（development/test） | authorization、scope、60/300/0、SQLite/outbox/receipt 测试 |
| 3 | DISABLE 阻止新操作，不取消既有非终态 run，不删历史 | pass | `test_disable...` |
| 4 | REVOKE / EMERGENCY 取消活动 run 并记录 SECURITY_REVOCATION/revocation_id/mode/receipt | pass | grace/emergency/terminal/SQLite tests |
| 5 | 仅 manifest 声明 degraded_modes 时允许降级 | pass | degradation declaration test |
| 6 | 降级后 output schema 保持相同 | pass | schema match/mismatch test |
| 7 | required、授权不足、安全撤销禁止自动降级 | pass | fail-closed degradation test |
| 8 | 升级失败保留旧版本 ready/default | pass | `test_failed_upgrade_preserves_old_ready_default` |
| 9 | 单元测试覆盖撤销、降级、升级失败恢复 | pass | 15/15 |
| 10 | 11 项 evidence contract 全部生成可追溯开发证据；未签署前不开放 production Gate | pass（Gate 保持关闭） | pack ID/hash/原始 ID；`production_gate_satisfied=false` |
| 11 | 实际变更仅位于四实现/测试路径及唯一报告 | pass | 文件清单与 scoped status |
| 12 | 报告逐项记录命令、结果、验收、diff 与回滚 | pass | 本报告 §5–§9 |

## 8. 风险、阻塞与未验证项

### 8.1 风险

- 真实身份/RBAC 服务、runtime kill/isolation provider、notification provider 和多节点执行并未接入；本实现通过 fail-closed 注入边界消费其服务端判定，未越权修改这些系统。
- rollback audit appender 与 InstallationService 由上层部署组合；生产必须使用持久化 audit adapter 并在部署验证中证明同事务/补偿语义。
- 本地 SQLite repository 证明单节点持久化和 append-only trigger；不等价于多节点一致性、WORM 基础设施或 production retention 认证。

### 8.2 阻塞

- 本次 development/test Task：无阻塞。
- Stage 4 production Gate：仍被真实环境 11 项 evidence、独立 reviewer 签名和 rollout approver 明确批准阻断。owner 为 Stage/Security reviewer 与 rollout approver；这不是本 Issue 可自行宣称完成的 production 放行。

### 8.3 未执行/未验证

- 未执行真实 production runtime hard-stop、node/session isolation 或安全值班通知。
- 未取得独立 reviewer 签名、rollout approval ID 或 production WORM/hash-chain 报告。
- 未运行全仓库测试；Task 只要求最小目标模块，且共享工作树存在大量其他未提交变更，扩大全仓验证会混入无关失败面。

## 9. 回滚建议

### 9.1 代码回滚

仅回退以下四个实现/测试文件的本 Task 变更；保留本报告作为执行证据：

- `backend/services/deck_plugin/revocation_service.py`
- `backend/services/deck_plugin/degradation_service.py`
- `backend/services/deck_plugin/rollback_manager.py`
- `backend/tests/test_revocation_rollback.py`

回滚前后均重新执行目标 unittest 与 `git diff --check`。不得回退、删除或原地改写已经落盘的 revocation record、impact manifest、command/notification/runtime receipt、incident、quarantine 或 audit event。

### 9.2 数据与安全回滚

- `DISABLE` 只能由授权 Deck Operator 对相同 scope 重新 enable，不改历史。
- `REVOKE` / `EMERGENCY` 不允许 unrevoke；误报必须追加 superseding policy/release，重新签名、preflight、load receipt，并创建新 run/session。
- 非生产演练可关闭自动 hard-stop 并转人工处置，同时阻断新 run；production 中关闭 hard-stop 必须走独立安全紧急变更，不属于本 Task 回滚授权。

## 10. 完成状态

- [x] 已完成实现。
- [x] 已完成目标测试。
- [x] 已记录全部 Task 文件变更。
- [x] 已满足 development/test 验收条件。
- [x] 已生成 11-case development evidence pack 并保留 production Gate=false。
- [x] 已确认禁止范围未被本 Task 修改。
- [x] 可结束本 execute Issue。
- [ ] 不可标记 Stage 4 production Gate 通过。
- [ ] 不可宣称 production-ready。

**最终建议**：本 execute Issue 可标记 `done`；后续 production review/audit 必须使用真实环境 evidence、独立 reviewer 签名和 rollout approval，不能复用本地 development pack 作为 production 放行证据。
