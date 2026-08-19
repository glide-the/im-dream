# task_deck_015_backend_revocation-rollback

> **Task ID**: `task_deck_015_backend_revocation-rollback`
> **Readiness 修订 Issue**: [SUO-324](/SUO/issues/SUO-324)
> **Domain**: `backend`（仅用于分类，不代表执行 Agent 身份）
> **状态**: `pending_stage_recheck`
> **唯一执行责任人**: `ExecTaskAgent`
> **Stage 映射**: Stage 4 / Wave 1（独立 execute Issue、独立 checkout、独立验收）

## 1. 任务标题

安全撤销、回滚与降级路径

## 2. 关联 Issue

- **Issue ID**: `DECK-015`
- **Issue 标题**: 安全撤销、回滚与降级路径
- **类型**: backend
- **优先级**: P1
- **标签**: `security`, `rollback`, `degradation`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §6.2, §12.2, §12.3
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-015
- **Readiness 修订**: [SUO-324](/SUO/issues/SUO-324)

## 3. 任务目标

实现已冻结的安全撤销、回滚和降级路径。包括 `DISABLE` / `REVOKE` / `EMERGENCY` 的确定性行为矩阵、四类撤销 target 的影响解析、grace/hard-stop、幂等取消、通知/审计，以及仅在 manifest 明确声明 `degraded_modes` 时允许的降级规则。

`DECK-GATE-DEC-019` 已为 `frozen`：`DISABLE` 不终止既有 run；`REVOKE` 默认 60 秒、最大 300 秒 grace 后硬停；`EMERGENCY` 零 grace 立即硬停。设计冻结不表示 Stage 4 production Gate 已通过；真实 11 项 evidence pack、独立 reviewer 签署与 rollout 审批仍是生产阻断项。

未来实现仅由 `ExecTaskAgent` 在本 task 的独立 execute Issue 中执行；`backend` 仅是 domain。本 task 不与其他 Stage 3/4 task 合并 checkout 或共享正式报告。

## 4. 实现步骤

### Step 1: 定义行为矩阵

| 变化 | 新 binding / preflight / run | 已锁非终态 run（含 queued） | 已 running | 历史 |
|---|---|---|---|---|
| `DISABLE` | 阻止 | 不进入 `cancelling`，不发终止命令，按原逻辑继续 | 不终止，按原逻辑继续至终态 | 不变；允许授权 enable，不改历史 |
| `REVOKE` | 立即阻止 | CAS 进入 `cancelling`；默认 60 秒、允许 `0..300` 秒 grace，deadline 后 hard-stop | grace 内只允许安全 checkpoint/诊断；deadline 后 1 秒内 hard-stop，10 秒内确认终止或隔离 | 来源/制品取证保留，旧记录不可 unrevoke |
| `EMERGENCY` | 立即阻止 | CAS 进入 `cancelling`；零 grace，不等待 checkpoint，1 秒内 hard-stop | 立即 hard-stop，10 秒内确认终止或隔离 | 来源/制品取证保留，只能由 superseding release/policy + new run/session 恢复 |
| 升级中 | 旧 ready 可用，新版本阻止 | 按已锁旧版本执行 | 按已锁版本继续 | 不变 |
| 物化失败 | 阻止依赖该制品的新 run | 不进入 session | 不影响已经成功加载的会话，除非安全策略要求 | 不变 |
| Deck 当前运行配置修改 | 新 preflight 取新 snapshot | 已锁 snapshot 不变 | 不变 | 不变 |

安全路径终态只允许：收到 graceful/hard ack 后为 `cancelled`；runtime 异常且隔离确认后为 `failed`；终止/隔离未确认为 `cancelling`。屏障生效后禁止写 `completed`，并必须保留 `SECURITY_REVOCATION`、`revocation_id`、`termination_mode` 与相应 receipt/incident。

### Step 2: 实现撤销服务

在 `backend/services/deck_plugin/revocation_service.py`（新建）中实现：

```python
class RevocationLevel(str, Enum):
    DISABLE = "disable"         # 普通禁用
    REVOKE = "revoke"           # 安全撤销
    EMERGENCY = "emergency"     # 紧急撤销（最高等级）

class RevocationService:
    async def revoke(
        self,
        idempotency_key: str,
        level: RevocationLevel,
        target_type: str,           # release/digest/signing_identity/capability_policy
        target_key: str,
        environment_ids: list[str],
        tenant_or_project_ids: list[str],
        reason_code: str,
        incident_id: Optional[str], # REVOKE / EMERGENCY 必填
        requested_by: str,
        approved_by: Optional[str],
        requested_grace_seconds: Optional[int]
    ) -> RevocationResult:
        """
        执行撤销：
        1. 校验 DISABLE / REVOKE / EMERGENCY 的角色分离、最小 scope 与 break-glass
        2. 生成不可变 RevocationImpactManifest；scope 扩大必须创建新 revocation_id
        3. 绑定 effective_at、policy revision、60/300/0 秒 grace 与 deadline
        4. 按行为矩阵处理全部非终态 run，并持久化通知 outbox
        5. 记录 append-only 审计事件；重放返回原 revocation/impact manifest
        """

    async def _cancel_running_runs(
        self,
        revocation_id: str,
        impact_manifest_id: str,
        level: RevocationLevel,
        effective_at: datetime,
        grace_deadline_at: Optional[datetime]
    ) -> None:
        """
        安全撤销/紧急撤销时强制取消活动 run：
        - 按 impact manifest 处理全部非终态 run，先 CAS 为 cancelling
        - 以 (revocation_id, workflow_run_id) 去重，至少一次投递不得重复 kill/终态/通知
        - REVOKE 到期或 EMERGENCY 生效后发 hard-stop；未确认时保持 cancelling 并隔离
        - 记录 SECURITY_REVOCATION、command/receipt、termination_mode 和冲突/抑制事件
        """
```

角色合同：`DISABLE` 由 Deck Operator 在授权 scope 内发起/执行；`REVOKE` 要求异主体发起与批准、机器主体按签名 impact manifest 执行、独立审计复核；`EMERGENCY` 使用 15 分钟 JIT break-glass，并在 30 分钟内由异主体追认，失败必须升级 incident。人类主体不得直接调用 runtime kill，机器执行主体不得扩大签名 scope。

### Step 3: 实现降级规则

```python
class DegradationService:
    async def evaluate_degradation(
        self,
        manifest: DeckPluginManifestV1,
        missing_plugins: list[str],
        missing_capabilities: list[str]
    ) -> DegradationResult:
        """
        降级评估：
        1. 检查 manifest 是否声明 degraded_modes
        2. 确认缺失的是 optional 插件（非 required）
        3. 确认缺失能力不影响输出 schema
        4. 返回 degraded_mode_id 和替代步骤
        5. required 插件缺失、能力授权不足、安全撤销均禁止自动降级
        """
```

降级规则：
- optional Claude Code Plugin 缺失时可省略，但必须满足 manifest 定义的替代步骤
- 降级后的输出必须仍符合相同 story-workspace output schema
- preflight 响应必须显示 degraded mode、缺失能力和用户确认要求
- Workflow Run 必须保存实际 runtime load receipt 和 `degraded_mode_id`
- 默认示例 `degraded_modes=[]`，即不允许降级

### Step 4: 实现回滚路径

```python
async def rollback_installation(
    self,
    installation_id: str,
    target_version: str,
    actor: str
) -> RollbackResult:
    """
    回滚：
    1. 校验目标版本仍为 published/deprecated 且 installation 记录存在
    2. 校验 digest 完整
    3. 执行兼容性检查（目标版本与当前 host/runtime）
    4. 更新 default_version
    5. 已有 Deck binding 不自动迁移（仅影响下一次运行）
    6. 记录审计事件
    """
```

### Step 5: 审计要求

安全撤销必须记录：
- `revocation_id`、idempotency key、发起/批准/执行/复核主体、等级、规范化 scope、reason/incident、policy revision
- 不可变 `impact_manifest_id + manifest_sha256`、`effective_at`、grace/deadline、受影响 run/session/node 列表
- 每个 run 的 command/outbox/inbox/termination/isolation receipt、`SECURITY_REVOCATION`、`termination_mode`、终态或未确认 incident
- 持久化通知 outbox、最多六次固定退避投递、去重 receipt 与 delivery_failed incident；通知失败不得延迟撤销或 hard-stop
- 重复/并发抑制、CAS 冲突与 `RUN_TERMINAL_CONFLICT` 事件；所有记录 append-only，纠错只追加 superseding 记录

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/services/deck_plugin/revocation_service.py` | 新建 | 撤销服务 |
| `backend/services/deck_plugin/degradation_service.py` | 新建 | 降级服务 |
| `backend/services/deck_plugin/rollback_manager.py` | 新建 | 回滚管理器 |
| `backend/tests/test_revocation_rollback.py` | 新建 | 撤销/回滚/降级单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `idempotency_key`、`RevocationLevel`
- 规范化 `target_type + target_key`（release / digest / signing identity / capability policy）
- `environment_ids`、`tenant_or_project_ids`、`reason_code`、`incident_id`
- 发起/批准身份与可选 `requested_grace_seconds`

**输出**：
- `RevocationResult`（`revocation_id`、`impact_manifest_id`、生效时间、grace/deadline、已处理 run 列表）
- append-only 审计、取消/隔离/通知 receipt 与未确认 incident 引用

## 7. 依赖项

- **前置依赖**: `DECK-003`（Installation 生命周期）, `DECK-007`（Workflow Run）
- **下游依赖**: 无
- 需要与事件系统（DECK-013）集成

## 8. 测试策略

execute Issue 必须从仓库根核对 Python 入口及依赖环境，并逐字回填实际解释器、runner 与命令。当前仓库测试采用 `unittest` 风格，可直接复制的最小目标命令为 `PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -m unittest backend.tests.test_revocation_rollback -v`，同时执行 `git diff --check`；若 `.venv` 或命令不可用，必须在 execute Issue/正式报告记录通过 `backend/pyproject.toml`、现有 `backend/tests/test_*.py` 和既有 exec 报告发现 runner 的过程、失败输出及等价解释器命令，不得新增测试框架或伪报通过。

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | `DISABLE` / `REVOKE` / `EMERGENCY` 权限与行为矩阵；越权 scope fail closed |
| 单元测试 | `DISABLE` 阻止新 binding/preflight/run，但既有非终态 run 不进入 cancelling、不发终止命令 |
| 单元测试 | `REVOKE` 默认 60 秒、0/300 秒边界、deadline 后 hard-stop；`EMERGENCY` 零 grace 立即硬停 |
| 单元测试 | 四类 target 影响 manifest、scope 扩大、重复/并发与 `(revocation_id, workflow_run_id)` 幂等 |
| 单元测试 | `cancelled` / `failed` / `cancelling` 确定性映射；安全路径 `completed` 被拒并审计 |
| 单元测试 | 通知时序、六次退避、失败 incident；通知故障不延迟 hard-stop |
| 单元测试 | 降级仅在 manifest 声明 degraded_modes 时允许 |
| 单元测试 | 降级后输出仍符合相同 output schema |
| 单元测试 | required 插件缺失禁止自动降级 |
| 单元测试 | 升级失败保留旧版本 ready |
| 单元测试 | 回滚只影响 default/binding，不改历史 run |
| 集成测试 | 11 项 `Stage4RevocationEvidencePack` 场景逐项生成原始 test/event/command/receipt/audit ID；缺任一项即失败 |

## 9. 完成标志

- [ ] `DISABLE` / `REVOKE` / `EMERGENCY` 行为、角色、scope、grace/hard-stop、通知与审计矩阵符合已冻结 DECK-019
- [ ] `DISABLE` 阻止新 binding/preflight/run，不终止既有非终态 run，不删除历史
- [ ] `REVOKE` 与 `EMERGENCY` 按冻结时限取消活动 run，记录 `SECURITY_REVOCATION`、`revocation_id`、`termination_mode` 与 receipt
- [ ] 降级仅在 manifest 声明 `degraded_modes` 时允许
- [ ] 降级后输出仍符合相同 story-workspace output schema
- [ ] required 插件缺失、能力授权不足、安全撤销均禁止自动降级
- [ ] 升级失败保留旧版本 `ready`
- [ ] 单元测试覆盖撤销场景、降级路径、升级失败恢复
- [ ] 11 项 evidence pack 全部生成可追溯原始证据并由独立 reviewer 签署前，不得标记 Stage 4 production Gate 通过
- [ ] 实际变更只位于 §5 四个实现/测试路径及本 task 唯一正式报告路径
- [ ] execute Issue/正式报告逐项回填验证命令、结果、验收、diff 与回滚说明

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 强制取消活动 run 导致数据丢失 | 高 | DISABLE 不终止；REVOKE 受控 grace；EMERGENCY 仅 break-glass；全程 append-only 审计与 receipt |
| 降级被滥用绕过安全策略 | 高 | required 插件缺失禁止降级；安全撤销禁止降级 |
| 回滚到已不兼容的旧版本 | 中 | 回滚前执行兼容性检查 |
| 紧急撤销误触发 | 高 | 15 分钟 JIT break-glass、最小 scope、30 分钟异主体追认与失败 incident |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/services/deck_plugin/revocation_service.py`（仅新增禁用/撤销与审计编排）
- `backend/services/deck_plugin/degradation_service.py`（仅新增 manifest 声明范围内的降级判定）
- `backend/services/deck_plugin/rollback_manager.py`（仅新增显式回滚与兼容性前置检查）
- `backend/tests/test_revocation_rollback.py`（仅新增本 task 的单元测试）
- `docs/exec/exec_deck_015_backend_revocation-rollback.md`（仅允许 `ExecTaskAgent` 写入本 task 的唯一正式执行报告）

以上五个路径构成未来 execute 完整闭集；前四个与 §5“涉及文件路径”一致，最后一个仅为正式报告例外。未列出的文件默认不授权。

### 禁止修改范围

- `docs/exec/` 下除 `docs/exec/exec_deck_015_backend_revocation-rollback.md` 之外的全部路径
- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `frontend/`、安全策略/身份服务内部实现与 Workflow Run 状态机实现
- 除上述 4 个路径以外的任何实现、测试、依赖锁或部署配置
- 未在 manifest 声明的自动降级、required 插件/权限/安全撤销场景的降级
- 借本 task 重写历史 run、直接删除审计来源或扩大紧急撤销角色权限

### 当前修订阶段约束

[SUO-324](/SUO/issues/SUO-324) 只修订 task 合同，不授权执行上述闭集。未来 execute 必须由 `ExecTaskAgent` 在独立 Issue checkout 后实施；完成后由 StagePlanner 独立重跑 readiness，不得由本 task 自行宣布进入 execute、通过 Stage 4 Gate 或 production-ready。

## 12. 命名隔离声明

- 撤销等级：`DISABLE`、`REVOKE`、`EMERGENCY`
- 审计事件：`workflow.run.security_cancelled`
- 降级标识：`degraded_mode_id`

## 13. DECK-019 已冻结合同与剩余 Gate

- `DECK-019 / DECK-GATE-DEC-019`：`frozen`，依据 [SUO-267](/SUO/issues/SUO-267) 的具名 `approve` 与 [SUO-269](/SUO/issues/SUO-269) 的 canonical 状态回写；不再是等待决策的默认假设。
- 冻结合同：`DISABLE` 不终止既有 run；`REVOKE` 默认 60 秒、最大 300 秒 grace 后硬停；`EMERGENCY` 零 grace 立即硬停；安全路径终态与通知/幂等/append-only 审计按 §4 执行。
- Stage 4 production Gate 仍由真实 11 项 `Stage4RevocationEvidencePack`、独立 reviewer 签署和 rollout approver 明确批准共同阻断。设计冻结、单元测试通过或本 task 完成均不得替代这些证据。

## 14. 回滚边界

- 只回退 §11 允许的 revocation/degradation/rollback 实现与目标测试；不得删除或原地改写 revocation record、impact manifest、run 终态、outbox/inbox、termination/isolation/notification receipt 或历史来源。
- 误报通过新的 superseding policy/release 记录修复；`REVOKE` / `EMERGENCY` 不得 unrevoke，旧 run/session 不得复活。恢复必须重新签名、preflight、load receipt，并创建新 run/session。
- 非生产演练可按冻结设计关闭自动 hard-stop 并转人工处置，同时关闭新 run；production 中关闭 hard-stop 属安全降级，必须由安全 owner 走独立紧急变更，不在本 task 回滚授权内。
- 回滚前后执行 §8 的目标测试和 `git diff --check`，并在 `docs/exec/exec_deck_015_backend_revocation-rollback.md` 记录触发条件、变更路径、数据/审计保留、验证结果与剩余影响；正式报告本身不得在代码回滚中删除。
