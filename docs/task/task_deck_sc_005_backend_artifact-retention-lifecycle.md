# task_deck_sc_005_backend_artifact-retention-lifecycle

## 1. 任务标题

制品引用状态机、Legal Hold、90 天隔离与安全 Purge

## 2. 唯一映射与 Domain

| 字段 | 值 |
|---|---|
| Task ID | `TASK-DECK-SC-005` |
| 来源 Issue | `DECK-SC-005` |
| Paperclip TaskDesign Issue | [SUO-275](/SUO/issues/SUO-275) |
| Canonical design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.3-§4.2.4 |
| Domain | `backend` |
| 优先级 | P0 |
| 下游 Stage 映射键 | `stage4.supply_chain.DECK-SC-005` |

## 3. 任务目标与非目标

建立以精确 `artifact_digest` 为键的权威引用跟踪和留存状态机：有 release/lock/run/legal hold 引用时 `pinned`；零引用后进入至少 90 天 `recoverable`；期满并二次确认仍零引用才 `purge_eligible → purged`；revoked 进入 `quarantined` 且禁止新执行但保留取证。

非目标：不把卸载/撤销等同删除；不将节点 cache 计为权威留存；不选择冷存储供应商/RTO（由 SC-006）；不改写既有 release/run 历史。

## 4. 实现步骤

1. 定义 `ArtifactRetentionRecord`、分项引用、legal hold、状态转移、恢复引用和 append-only purge audit。
2. 按 published/deprecated/revoked release、runtime lock、Workflow Run、legal hold 分别跟踪引用；拒绝负数、丢失来源或无幂等键的更新。
3. 在事务边界内派生总引用与状态：任一权威引用存在即 `pinned`；revoked 优先 `quarantined`，禁止新执行但引用/字节不删除。
4. 总引用归零且无 legal hold 时记录 `recoverable_since` 和 `purge_not_before`；生产隔离期配置不得小于 90 天。
5. 期满转为 `purge_eligible`；物理删除前重新读取所有权威来源并做 compare-and-set，发现新引用/hold 立即回到 `pinned`/`quarantined`。
6. purge 后保留 digest、签名 proof ref、来源/引用清理审计、actor/reason/time；删除失败不得伪造 `purged`。
7. 提供状态/引用详情/legal hold 管理 API，所有 hold/purge 动作鉴权并审计。
8. 补齐引用竞态、90 天边界、legal hold、revoked、恢复、purge 失败和审计留存测试。

## 5. 涉及文件与写入边界

### 5.1 允许修改闭集

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/artifact_retention.py` | 新建 | retention/ref/legal-hold/purge audit 模型 |
| `backend/services/deck_plugin/artifact_reference_tracker.py` | 新建 | 权威分项引用与幂等更新 |
| `backend/services/deck_plugin/artifact_retention.py` | 新建 | 状态机、隔离计时、CAS purge guard |
| `backend/routers/deck_plugins.py` | 新建/修改 | 仅增加 retention 查询、legal hold 与受控 purge API |
| `backend/services/errors/error_registry.py` | 修改 | 仅增加引用/hold/purge 错误码 |
| `backend/database.py` | 修改 | 仅追加 retention/ref/hold/purge audit 表与约束 |
| `backend/tests/test_artifact_retention.py` | 新建 | 状态机、竞态、hold、purge 测试 |
| `output/evidence/deck-plugin/supply-chain/DECK-SC-005/**` | 生成 | 状态矩阵、竞态/审计测试证据 |

### 5.2 禁止修改范围

- 未列出的实现/测试、依赖/锁、部署配置和前端；
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`；
- 小于 90 天的 production 隔离期、基于 cache 的留存证明、撤销即删除；
- 绕过二次引用检查、删除 legal hold/审计、覆盖历史引用来源；
- 修改 SC-003 签名验证或 SC-006 冷存储 provider 实现。

## 6. 输入 / 输出与证据格式

输入：SC-003 verified digest/release、runtime lock、Workflow Run、release lifecycle、legal hold 命令、存储删除/恢复 adapter 结果。

输出：`retention_state=pinned|recoverable|purge_eligible|quarantined|purged`、`release_ref_count`、`lock_ref_count`、`run_ref_count`、`legal_hold_count`、`restore_source_ref`、隔离时间、不可变 purge audit。

证据每例包含 `test_case_id`、artifact digest、初始/最终状态、各引用计数、隔离时钟、并发版本、expected/actual reason code、run ID、commit SHA 和日志摘要。真实 purge 证据必须带删除 adapter receipt；测试不得对 production 制品执行删除。

## 7. 依赖、并行性与 StagePlanner 输入

- 直接前置：`TASK-DECK-SC-003`；基线合同：`task_deck_002_backend_runtime-lock.md`、`task_deck_003_backend_installation-lifecycle.md`、Workflow Run 审计事实。
- 下游：`TASK-DECK-SC-006`、`TASK-DECK-SC-008`。
- 可并行性：可与 `TASK-DECK-SC-004` 并行；model/DB、reference adapters、state machine 和 tests 可在状态枚举冻结后并行。
- 冻结点：权威引用源清单、90 天下限、revoked/quarantine 优先级、purge CAS guard 与审计 schema 冻结；引用源缺失时 production purge 禁用。
- Execute readiness：所有权威引用查询接口/一致性边界已定义；可控时钟、测试存储 adapter 和 legal hold 权限 owner 可用。

## 8. 验收条件

- [ ] 完整状态机与 `quarantined` 语义可执行且无非法跃迁。
- [ ] 四类引用分别追踪，任一引用/hold 存在时无法 purge。
- [ ] 零引用进入 `recoverable`，production `purge_not_before` 至少 90 天。
- [ ] purge 前二次确认并发新引用；竞态时 fail closed。
- [ ] revoked 禁止新执行但保留字节/证据；撤销不触发直接删除。
- [ ] 物理删除失败不写 `purged`；成功后保留 append-only 审计。
- [ ] 状态/引用/legal hold API 有鉴权、幂等与审计。

## 9. 最小测试 / 验证命令

```bash
backend/.venv/bin/python -m unittest backend.tests.test_artifact_retention
backend/.venv/bin/python -m compileall -q backend/models/artifact_retention.py backend/services/deck_plugin/artifact_reference_tracker.py backend/services/deck_plugin/artifact_retention.py backend/routers/deck_plugins.py
rg -n 'pinned|recoverable|purge_eligible|quarantined|legal_hold_count|purge_not_before' backend output/evidence/deck-plugin/supply-chain/DECK-SC-005
git diff --check -- backend/models/artifact_retention.py backend/services/deck_plugin/artifact_reference_tracker.py backend/services/deck_plugin/artifact_retention.py backend/routers/deck_plugins.py backend/services/errors/error_registry.py backend/database.py backend/tests/test_artifact_retention.py
```

## 10. 完成信号与回滚

完成信号：状态/竞态/hold/purge 测试全部通过，权威引用清单与审计可复核；SC-008 真实演练和独立复审尚未完成时仍不得 production-ready。

回滚：停止自动状态推进/物理 purge，保持制品 `pinned|recoverable|quarantined`；恢复最近稳定引用 tracker。不得回滚已保留引用、缩短隔离期、删除 proof/audit 或把未知引用视为零。

## 11. 风险与 Clarification

| 风险/澄清 | 处理 | Owner / action |
|---|---|---|
| 某权威引用源无法强一致查询 | 视为引用未知并禁止 purge | 对应 release/runtime/run owner：提供一致快照或保守 pin |
| 90 天时钟/时区漂移 | 使用服务端 UTC 与可控时钟测试 | 平台 owner：确认生产时间源和告警 |
| legal hold 权限/解除流程未定 | 默认只增不减，解除冻结 | 治理/合规 owner：批准 hold/release RBAC 与审计 |

## 12. Gate 声明

引用状态未知、hold 状态未知或恢复源不可读时一律禁止 purge/production-ready。本 task 的状态机实现不替代 SC-008 真实演练和独立复审。
