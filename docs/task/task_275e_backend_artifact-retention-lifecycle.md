# task_275e_backend_artifact-retention-lifecycle

> Task ID: `task_275e`
> Source Issue: `DECK-SC-005`
> Paperclip Issue: [SUO-275](/SUO/issues/SUO-275)
> Domain / Priority: `backend` / `P0`

## 1. 任务标题

制品权威引用状态机、90 天可恢复隔离与 Purge Gate

## 2. 关联 Issue

| 关联 | 内容 |
|---|---|
| 来源条目 | `DECK-SC-005` |
| Task-stage Issue | [SUO-275](/SUO/issues/SUO-275) |
| 来源编排 | [SUO-258](/SUO/issues/SUO-258) |
| Design | `docs/design/deck/design_002_deck-plugin-decision-gates.md` §4.2.1、§4.2.3 |
| 既有 task | `task_deck_002_backend_runtime-lock.md`、`task_deck_003_backend_installation-lifecycle.md` |
| Domain / Priority / 标签 | `backend` / P0 / `supply-chain`, `retention`, `state-machine`, `lifecycle` |

## 3. 任务目标

以不可变 artifact digest 为聚合键实现引用感知留存：published/deprecated/revoked release、runtime lock、Workflow Run、legal hold 任一引用存在即保留；全部权威引用归零且无 legal hold 后进入不少于 90 天的可恢复隔离；期满后 purge 前再次原子检查引用，删除字节但永久保留审计。revoked 制品隔离且禁止新执行，撤销不得触发删除。

本 task 不选择冷存储供应商、不执行季度恢复演练、不修改安全撤销策略。

## 4. 实现步骤

1. 定义按 `artifact_digest` 唯一的 retention record，分别追踪 `release_ref_count`、`lock_ref_count`、`run_ref_count`、`legal_hold_count` 和引用明细。
2. 仅从权威 release/lock/run/hold 写入边界接收幂等 reference event；禁止由 UI、cache 或 marketplace 标签直接改计数。
3. 实现状态机：
   - `pinned`：任一权威引用或 hold 存在；
   - `recoverable`：引用归零且无 hold，记录 `quarantine_started_at`/`purge_not_before`；
   - `purge_eligible`：不少于 90 天且恢复源仍可核验；
   - `purged`：物理字节已删，审计与证明保留；
   - `quarantined`：revoked，禁止新执行并保留取证字节/证明；引用与 hold 仍持续追踪。
4. 新引用在 recoverable/purge_eligible 阶段出现时，原子回到 `pinned` 并取消当前 purge eligibility。
5. purge 命令在同一事务中锁定 record、重新查询四类权威引用/hold、验证 90 天和 restore policy；任一条件不满足返回稳定拒绝码。
6. purge 成功后保留 digest、签名证明 ref、来源、删除时间/原因/actor、引用清理快照与 request ID；审计禁止更新/删除。
7. 提供查询状态/引用详情、建立/解除 legal hold 和显式 purge API；hold 操作需要授权与理由，解除不自动跳过隔离期。
8. 使用固定时钟、乱序/重复事件、并发新引用与 purge、revoked/hold 组合测试状态与原子性。

## 5. 涉及文件路径

| 路径 | 动作 | 最小变更 |
|---|---|---|
| `backend/models/artifact_retention.py` | 新建 | retention/reference/hold/purge audit 模型 |
| `backend/services/deck_plugin/artifact_reference_service.py` | 新建 | 权威引用幂等聚合 |
| `backend/services/deck_plugin/artifact_retention_service.py` | 新建 | 状态机、90 天计时、legal hold、purge Gate |
| `backend/routers/deck_plugin_retention.py` | 新建 | 查询/hold/purge 管理 API |
| `backend/services/deck_plugin/release_service.py` | 修改 | 仅发布 release reference event |
| `backend/services/deck_plugin/installation_service.py` | 修改 | 仅生命周期产生的权威 reference 变更 |
| `backend/database.py` | 修改 | retention/reference/hold/append-only audit 表与约束 |
| `backend/server.py` | 修改 | 仅注册 retention router |
| `backend/tests/test_deck_plugin_retention.py` | 新建 | 状态机、并发、hold、purge 测试 |

Workflow Run 的引用接入若实际 owner 路径不在上述闭集，执行者必须停止该接入并创建/引用由 run owner 承接的子任务；不得扩大到未知 run 实现文件。

## 6. 输入 / 输出说明

### 输入

```jsonc
{
  "artifact_digest": "sha256:...",
  "reference_type": "release|runtime_lock|workflow_run|legal_hold",
  "reference_id": "...",
  "operation": "add|remove",
  "event_id": "...",
  "occurred_at": "..."
}
```

### 输出

- `ArtifactRetentionRecord`：四类 count/details、`retention_state`、`quarantine_started_at`、`purge_not_before`、`restore_source_ref`；
- 拒绝码：`ARTIFACT_REFERENCED`、`ARTIFACT_LEGAL_HOLD_ACTIVE`、`ARTIFACT_QUARANTINE_NOT_EXPIRED`、`ARTIFACT_RESTORE_UNAVAILABLE`、`ARTIFACT_PURGE_RACE_DETECTED`；
- append-only purge/hold/reference audit。

## 7. 依赖项、可并行性与冻结点

- 直接依赖：`task_275c` 的 verified digest；与 `task_deck_003` installation 生命周期对齐。
- 下游：`task_275f`、`task_275h`。
- 与 `task_275d` 可逻辑并行；共享 `database.py` 时串行合并。
- Freeze point：四类权威引用源映射完整、90 天最小值不可被生产配置缩短、purge 原子二次检查通过。
- Workflow Run owner 未提供权威引用事件前，production purge 必须全局保持关闭。

## 8. 测试策略

最小命令：`python -m unittest backend.tests.test_deck_plugin_retention`

| 场景 | 通过标准 |
|---|---|
| 四类引用分别存在 | 任一项使 purge 拒绝并保持 pinned/quarantined |
| 重复/乱序 reference event | 幂等，无负计数或提前归零 |
| 零引用 | 进入 recoverable，`purge_not_before >= 90d` |
| 隔离期内新引用 | 原子回 pinned，旧 eligibility 失效 |
| legal hold | 零其他引用也拒绝 purge |
| 期满 purge 与并发新引用 | 至多一方成功；新引用存在时 purge 拒绝 |
| revoked | 禁止新执行但不删除字节/证明 |
| purge 成功 | 字节删除，审计仍可查且不可修改 |

使用固定时钟避免真实等待 90 天；另执行 `git diff --check --` 指定闭集。

## 9. 完成标志

- [ ] 四类权威引用分别追踪且明细可查询。
- [ ] 任一引用或 hold 存在时 purge 必须失败。
- [ ] 零引用无 hold 自动进入不少于 90 天 recoverable。
- [ ] 期满形成 purge_eligible，purge 前原子二次检查。
- [ ] revoked 制品隔离、禁新执行、不删除历史证据。
- [ ] purge 后保留 digest、actor、时间、原因与引用快照审计。
- [ ] 管理 API 有授权、结构化拒绝和审计。
- [ ] 并发、乱序、hold、隔离期与 revoked 测试通过。

## 10. 风险提示与回滚

| 风险 | 处理 / 回滚 |
|---|---|
| 只用聚合计数而无法追责 | 同时保存权威引用明细与 event id |
| 乱序事件造成负计数 | 以 reference identity 幂等 upsert/remove，不做盲加减 |
| 配置把生产隔离期缩短 | 校验生产下限 90 天，非法配置 fail closed |
| purge 与新引用竞争 | 锁/事务内二次查询；竞争时拒绝 purge |

回滚必须关闭 purge worker/API 并保持字节 pinned；不得删除已生成审计或把 recoverable 直接变为 purged。

## 11. 允许 / 禁止修改范围

- 允许：§5 精确闭集。
- 禁止：冷存储 provider 实现、季度演练、revocation 策略、前端、未列出的 Workflow Run 文件、依赖/部署配置。
- 禁止修改设计、Issue、task、Stage 或 Exec 文档。

## 12. StagePlanner / Execute Readiness

| 字段 | 值 |
|---|---|
| 前序 | `task_275c`, `task_deck_003` 合同 |
| 可并行 | 与 `task_275d` 逻辑并行；DB 合并串行 |
| Freeze point | 四类权威引用 + 90 天下限 + 原子 purge recheck |
| Execute readiness | run 引用 owner 接口、固定时钟、hold 权限与物理删除 adapter 明确 |
| 证据格式 | 精确测试报告、四类 reference snapshot、固定时钟边界记录、purge/hold append-only audit 与拒绝码 |
| Clarification owner/action | marketplace/制品平台 owner 确认 retention/purge adapter，Workflow Run owner 确认权威 run reference 事件；缺任一接口时关闭 production purge 并由 `CEOOrchestrator` 路由补齐 |
| 未满足 Gate | 冷恢复方案/承诺、真实 purge evidence、owner/reviewer 与复审 |

本 task 完成不等于 Stage 4 production Gate approve。
