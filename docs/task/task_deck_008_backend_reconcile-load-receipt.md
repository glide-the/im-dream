# task_deck_008_backend_reconcile-load-receipt

## 1. 任务标题

ClaudeAgent 声明式 Reconcile 与 Load Receipt

## 2. 关联 Issue

- **Issue ID**: `DECK-008`
- **Issue 标题**: ClaudeAgent 声明式 Reconcile 与 Load Receipt
- **类型**: backend
- **优先级**: P0
- **标签**: `claude-agent`, `reconcile`, `materialization`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.1, §7.2, §7.3, §7.4
  - `docs/design/plugin-remote-interaction.md` §4.2, §4.3, §4.4
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-008

## 3. 任务目标

在已完成的 Workflow Run 合同之上，实现 ClaudeAgent 的声明式 reconcile、单节点本地持久 runtime 物化与不可变 Load Receipt。运行主路径为 settings 意图 + headless reconcile，CLI 仅为受控备选。

本 task 的执行域被 `DECK-GATE-DEC-017/018` 限定为：

- 仅允许 `runtime_pool_id == runtime_environment_id` 且 `distribution_mode=local_persistent` 的单节点形态；
- 仍必须保留 digest 校验、scoped readiness、`runtime_node_id`、`artifact_set_hash`、`policy_revision` 和逐项 digest 语义；
- 不实现或宣称多节点调度、临时 runtime、marketplace 下载、共享 CAS/冷存储或真实留存；
- 不得以本 task 的通过声称 `production_ready` 已放行。

执行唯一责任人为 `ExecTaskAgent`；`backend` 只表示 domain，不是 Agent 名称。TaskDesignAgent 本次只冻结任务合同，不实现 Reconcile、Materialization、Load Receipt 或 Session。

## 4. 实现步骤

### Step 0: 执行准入与前置合同

`ExecTaskAgent` 开始实现前必须：

1. 读取并按当前单一执行 Issue 填充 `docs/task/TASK-REQUIREMENT-FORMAT.md`；填充应在执行上下文/受控副本中完成，源模板保持只读，不属于本 task 允许写入闭集。
2. 确认 Issue 层来源依赖 `DECK-002`、`DECK-006` 已可消费。
3. 确认 Stage 的更严格串行前置 `task_deck_007 → task_deck_008` 已满足；直接执行前置 [SUO-304](/SUO/issues/SUO-304) 已为 `done`。
4. 保留 [SUO-304](/SUO/issues/SUO-304) 已落地的 Workflow Run 表、trigger、模型、服务与测试；本 task 只追加自身表、索引、guard 和读取适配器，不覆盖或重写 Workflow Run 实现。
5. 记录 `git status --short` 基线。若允许路径已有无法安全合并的他人改动，停止受影响写入并通过执行 Issue 记录 owner/action。

TaskDesignAgent 不得代填上述 execute 模板，也不得因本 readiness 修订进入 execute。

### Step 1: 定义三维状态与受信运行上下文

在 `backend/models/runtime_plugin.py`（新建）中定义：

```python
class RuntimePlacementContext(BaseModel):
    workflow_run_id: str
    runtime_environment_id: str
    runtime_pool_id: str
    distribution_mode: Literal["local_persistent"]
    runtime_node_id: str
    artifact_set_hash: str
    policy_revision: str
    deployment_tier: Literal["development", "test"]

class RuntimePluginMaterialization(BaseModel):
    runtime_materialization_id: str     # rm_<uuid>
    runtime_environment_id: str
    runtime_pool_id: str
    runtime_node_id: str
    claude_code_plugin_id: str
    resolved_version: str
    artifact_digest: str                # lock 中期望值
    materialized_digest: str            # 对节点实际字节重算
    artifact_set_hash: str
    policy_revision: str

    # 三维状态（独立记录，不可合并）
    declaration_status: DeclarationStatus      # undeclared | declared | disabled
    materialization_status: MaterializationStatus  # missing | materializing | materialized | failed
    activation_status: ActivationStatus        # inactive | loadable | loaded | load_failed

    # 物化元数据
    materialization_key: str            # 见 Step 4 的规范化计算
    attempt_id: str                     # 每次 attempt 唯一
    attempt_count: int                  # 重试次数
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime

class DeclarationStatus(str, Enum):
    UNDECLARED = "undeclared"
    DECLARED = "declared"
    DISABLED = "disabled"

class MaterializationStatus(str, Enum):
    MISSING = "missing"
    MATERIALIZING = "materializing"
    MATERIALIZED = "materialized"
    FAILED = "failed"

class ActivationStatus(str, Enum):
    INACTIVE = "inactive"
    LOADABLE = "loadable"
    LOADED = "loaded"
    LOAD_FAILED = "load_failed"
```

`RuntimePlacementContext` 必须由受信 runtime/preflight 解析器注入，禁止从客户端 body、CLI stdout 或 settings 文件反向推导。本 task 只接受同时满足以下断言的上下文，否则 fail closed：

- `runtime_pool_id == runtime_environment_id`；
- `distribution_mode == "local_persistent"`；
- `runtime_node_id` 非空且指向当前唯一节点；
- `artifact_set_hash` 等于对 runtime lock 全部 required entries 的 `claude_code_plugin_id + resolved_version + artifact_digest` 按 plugin ID 排序后做 canonical JSON SHA-256 的结果；
- `policy_revision` 等于当前 preflight/runtime 受信上下文绑定的有效策略版本。
- `deployment_tier` 只能为 `development|test`；`DECK-GATE-DEC-017` 未放行前，production 请求必须 fail closed。

### Step 2: 实现声明式 Reconcile（主路径 A）

在 `backend/services/runtime_plugin/reconcile_service.py`（新建）中实现：

```python
class ReconcileService:
    async def declare_and_reconcile(
        self,
        runtime_lock: DeckRuntimePluginLock,
        placement_context: RuntimePlacementContext,
    ) -> ReconcileResult:
        """
        路径 A（主路径）：声明意图 + headless reconcile
        1. 将 runtime lock 中的插件写入 settings（enabledPlugins / extraKnownMarketplaces）
        2. 启动 headless 会话，env: CLAUDE_CODE_SYNC_PLUGIN_INSTALL=true
        3. 在选定 runtime_node_id 的 run-scoped headless load context 中同步等待 reconcile
        4. 在任何第一条 query 发出前校验 init.plugins 和逐项 digest/capability
        5. 返回结构化 ReconcileResult，供 Step 5 生成不可变 Load Receipt
        """
```

settings 写入是 runtime 副作用，不是对仓库 settings 文件的授权。写入目标、marketplace 别名和 plugin ID 必须来自 runtime lock 与受信 policy，不接受自由文本路径、repo 或 shell 片段。

Settings 写入格式：
```json
{
  "enabledPlugins": {
    "ink-dream-tools@voice-decks": true
  },
  "extraKnownMarketplaces": {
    "voice-decks": {
      "source": "github",
      "repo": "voice-decks/marketplace"
    }
  }
}
```

### Step 3: 实现受控 CLI 备选路径（路径 B）

```python
async def cli_install(
    self,
    claude_code_plugin_id: str,
    resolved_version: str,
    scope: Literal["project", "local"] = "project"
) -> CliResult:
    """
    路径 B（备选）：受控子进程执行
    1. 用注入的 CliSourcePolicy 校验 plugin ID、marketplace/source 和 scope 都在 allowlist
    2. 只以 argv 列表执行
       ["claude", "plugin", "install", plugin_id, "--scope", scope, "--json"]
    3. shell=False，不接受额外 flags；超时必须由配置注入且限制在 1..300 秒
    4. stdout 按固定 CliResult schema 解析；stderr/stdout 限长、脱敏，非 JSON、超限或未知字段均 fail closed
    5. 校验结构化输出中的 plugin ID 与 resolved version 与 runtime lock 一致
    6. 用注入的 CliAuditSink 记录 attempt_id、策略版本、argv 摘要、超时、exit code、输出摘要与结果
    """
```

`CliSourcePolicy`、`CliRunner`、`CliAuditSink` protocol 及默认受控实现必须收口在 `reconcile_service.py`；测试通过注入 fake 覆盖 allowlist 拒绝、列表参数、超时、结构化输出与审计证据。禁止为此新增闭集外 CLI 封装、通用 event/outbox 或 shell 工具。

### Step 4: 实现物化幂等合同

```python
async def materialize(
    self,
    placement_context: RuntimePlacementContext,
    claude_code_plugin_id: str,
    resolved_version: str,
    artifact_digest: str
) -> MaterializationResult:
    """
    物化幂等合同：
    1. materialization_key = sha256(canonical_json(
       runtime_environment_id, runtime_node_id, plugin_id,
       resolved_version, artifact_digest, policy_revision))
    2. 同一 key 同时只允许一个 reconcile owner
    3. 重复请求返回同一个 materialization/operation
    4. 通过注入 ArtifactProvider 只消费已按 digest 定位的 staged artifact；
       重算实际字节 SHA-256，匹配后原子发布到单节点版本化 cache
    5. 通过注入 RetentionEvidenceReader 消费 pin/recoverable 证明；
       缺失证明时禁止清理被历史 runtime lock/Workflow Run 引用的旧制品
    """
```

`ArtifactProvider` 只是输入端口，返回的 staged descriptor 至少包含 digest、`verification_status`、签名证明引用、`retention_state` 和 restore source 引用。本 task 不实现 marketplace 网络下载、共享 CAS、冷存储、restore/purge 或真实留存策略。开发/测试可显式消费 `legacy_unverified` 证明，但 Receipt 必须保留该状态且不得升级为 production-ready；`RetentionEvidenceReader` 不能把节点 cache 伪装成 `DECK-GATE-DEC-017` 留存证明。

### Step 5: 实现 Load Receipt 生成

```python
class RuntimeLoadReceipt(BaseModel):
    receipt_id: str                 # rlr_<uuid>，Receipt 内部唯一名称
    workflow_run_id: str
    runtime_plugin_lock_id: str
    runtime_plugin_lock_digest: str
    runtime_environment_id: str
    runtime_pool_id: str
    distribution_mode: Literal["local_persistent"]
    runtime_node_id: str
    artifact_set_hash: str
    policy_revision: str
    deployment_tier: Literal["development", "test"]
    scope: Literal["session"]
    readiness_state: Literal["session_loaded"]
    required_entries_ready: bool
    entries: list[LoadReceiptEntry]
    created_at: datetime

class LoadReceiptEntry(BaseModel):
    claude_code_plugin_id: str
    resolved_version: str
    artifact_digest: str             # runtime lock 期望 digest
    materialized_digest: str         # 对实际加载字节重算
    verification_status: str         # verified | legacy_unverified
    signature_bundle_ref: str | None
    retention_state: str
    restore_source_ref: str | None
    required: bool
    loaded_capabilities: list[str]
    load_status: str                # loaded | load_failed | skipped
    loaded_at: datetime
```

字段命名与验证来源冻结如下：

| 字段 | 唯一命名 / 权威来源 | 验证规则 |
|---|---|---|
| `receipt_id` | 由 task_008 服务端生成 `rlr_<uuid>` | Receipt 模型、表与 readiness projection 只使用 `receipt_id`；已有 `WorkflowRun.runtime_load_receipt_id` 只是对其的外键式引用，不是第二个 Receipt ID 字段 |
| `workflow_run_id` | [SUO-304](/SUO/issues/SUO-304) 已落地的 `workflow_runs.id` | 服务端读取，禁止信任客户端回传 |
| `runtime_plugin_lock_id` | 当前 Workflow Run 的不可变 lock 引用 | 必须与 run 记录完全相等 |
| `runtime_plugin_lock_digest` | `deck_runtime_plugin_locks.lock_json` | 解析 JSON，以 `sort_keys=True`、`separators=(",", ":")`、UTF-8、禁止 NaN 的 canonical bytes 计算 `sha256:<hex>`，必须与 `WorkflowRunService` 现有 `_lock_digest` 等价 |
| placement / artifact / policy 字段 | Step 1 的受信 `RuntimePlacementContext` | 禁止从 CLI 或 settings 输出推导；必须重算 `artifact_set_hash` 并执行单节点双条件 Gate |
| entries | runtime lock + 物化 digest 复验 + headless init/load 结构化输出 | 每个 required lock entry 正好有一项；plugin ID/version/期望 digest 匹配，实际 digest 相等，capability 覆盖锁定集 |
| `required_entries_ready` | task_008 服务端计算字段 | 不接受输入；仅当上下文 Gate 通过、`scope/state=session/session_loaded`、所有 required entries 逐项一致且 `loaded` 时为 `true` |

为兼容 `backend/models/workflow_run.py::RuntimeLoadReceiptReadiness` 和 `backend/services/workflow/run_service.py` 已落地就绪守卫，task_008 必须暴露显式的只读适配器，且只返回以下五个 key：

```python
def read_workflow_readiness(receipt_id: str) -> dict[str, object]:
    return {
        "receipt_id": receipt.receipt_id,
        "workflow_run_id": receipt.workflow_run_id,
        "runtime_plugin_lock_id": receipt.runtime_plugin_lock_id,
        "runtime_plugin_lock_digest": receipt.runtime_plugin_lock_digest,
        "required_entries_ready": receipt.required_entries_ready,
    }
```

禁止把完整 Receipt dict 直接传给现有 strict projection（其 `extra="forbid"`），也禁止修改 [SUO-304](/SUO/issues/SUO-304) 的五字段模型或就绪守卫。

### Step 6: 数据库增量追加

在 `backend/database.py` 末端按现有初始化风格追加本 task 专属表/索引/guard：

- `runtime_plugin_materializations`：保存三维状态、node/pool/environment、期望/实际 digest、artifact set、policy revision、幂等 key 与 attempt；
- `runtime_plugin_reconcile_attempts`：保存主路径/CLI 备选的结构化、脱敏审计证据；
- `runtime_load_receipts`：以 `receipt_id` 为主键，显式保存 Step 5 的 run/lock/digest/placement/deployment-tier/artifact/policy/scope/state/ready 字段；
- `runtime_load_receipt_entries`：以 `receipt_id + claude_code_plugin_id` 为唯一项，保存期望/实际 digest、verification/signature/retention/restore 证明引用、required、status、capability 和时间；
- 必要的 lookup/唯一索引、Receipt/entry append-only guard，以及一个只验证 `workflow_runs.runtime_load_receipt_id` 所引 Receipt 存在且绑定同 run 的增量 trigger。

不得删除、重建、重排或改写 [SUO-304](/SUO/issues/SUO-304) 已落地的 `workflow_runs`、`workflow_run_token_consumptions`、`workflow_run_transitions` 及其 trigger。不得在本 task 中新增通用 events/outbox/CAS/retention 表。

### Step 7: 与 task_009 的 Session 接口边界

Stage 唯一串行顺序为 `task_deck_007 → task_deck_008 → task_deck_009`。语义解释如下：

1. task_007 已实现 Run 与五字段 Receipt readiness 消费守卫，但不产生 Receipt。
2. task_008 在选定单节点上建立 **run-scoped headless load context**，生成完整 Receipt 和五字段 projection，但不创建/管理 `AgentSession`、不写 `agent_session_id`、不发送首条 query、不调用 Workflow Run 进入 `running`。
3. `session_loaded` 在本 task 只表示“已为本 `workflow_run_id` 在指定 `runtime_node_id` 完成逐项加载证明”，不表示 AgentSession 记录已存在或生命周期已激活。
4. task_009 的现有“执行 reconcile/生成 Receipt”伪代码必须解释为调用/消费 task_008 的接口，不得重新实现。task_009 校验 Receipt 后，创建绑定同一 node/artifact set/policy 的 `AgentSession`，再以 `receipt_id` 调用现有 `queued → running` 守卫。
5. 若 task_009 无法在同一 headless load context/node 上安全创建 Session，或节点在 `agent_session_id` 创建前变更，必须要求 task_008 创建新 attempt 和新 Receipt，不得篡改旧 Receipt。`agent_session_id` 创建后的迁移/重调度必须由 task_009 创建新 Session attempt。

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/runtime_plugin.py` | 新建 | 仅定义三维状态、单节点 placement、Receipt/entry 与严格验证模型 |
| `backend/services/runtime_plugin/reconcile_service.py` | 新建 | 仅实现 settings + headless reconcile、受控 CLI 端口/执行、Receipt 生成/读取与五字段 Workflow Run projection |
| `backend/services/runtime_plugin/materialization_manager.py` | 新建 | 仅实现单节点幂等协调、实际 digest 复验、原子发布与 Artifact/Retention 消费端口 |
| `backend/database.py` | 修改 | 仅在 [SUO-304](/SUO/issues/SUO-304) 已有初始化之后追加本 task 的 materialization/reconcile-attempt/receipt/entry 表、索引与 guard |
| `backend/tests/test_runtime_plugin_reconcile.py` | 新建 | 仅新增本 task 定向单元/集成测试，含真实 Receipt reader 与现有 Workflow Run 守卫联调 |
| `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md` | 新建或增量更新 | 仅 `ExecTaskAgent` 回填本 task 唯一正式执行报告；非实现例外 |

## 6. 输入 / 输出说明

**输入**：
- `DeckRuntimePluginLock`（来自 DECK-002）
- `WorkflowRun` 不可变引用与 `workflow_run_id`（来自已完成的 task_007 / [SUO-304](/SUO/issues/SUO-304)）
- `RuntimePlacementContext`（受信 resolver 注入，含 environment/pool/node/distribution/artifact/policy）
- Settings 写入端口、headless runner、CLI policy/runner/audit 端口
- `ArtifactProvider` 和 `RetentionEvidenceReader` 消费端口

**输出**：
- `MaterializationResult`（物化结果）
- 不可变 `RuntimeLoadReceipt` 与逐项记录
- 与 `RuntimeLoadReceiptReadiness` 严格兼容的五字段只读 projection
- 三维状态记录
- 结构化、脱敏 reconcile/CLI 审计证据

## 7. 依赖项

- **Issue 层来源依赖**: `DECK-002`（runtime lock）、`DECK-006`（preflight）；两者必须保留，不得因 Stage 串行而改写
- **Stage 直接串行前置**: `task_deck_007_backend_workflow-run.md → task_deck_008_backend_reconcile-load-receipt.md`
- **已完成直接执行前置**: [SUO-304](/SUO/issues/SUO-304)（Workflow Run）
- **下游依赖**: `DECK-009` / `task_deck_009_backend_run-scoped-session.md`（消费 Receipt 后创建 AgentSession）
- 需要与 Claude Code runtime 环境集成
- 需要 settings 受控写入权限与受信 runtime placement/policy 解析器

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | settings 意图写入格式正确 |
| 单元测试 | headless reconcile 同步完成 |
| 单元测试 | CLI allowlist、argv 列表/`shell=False`、1..300 秒超时、严格 JSON、限长脱敏与审计证据 |
| 单元测试 | 三维状态独立记录 |
| 单元测试 | 物化幂等（同一 key 返回同一结果） |
| 单元测试 | staged artifact 实际 digest 复验、原子发布；Retention evidence 缺失时 fail closed |
| 单元测试 | 只接受单节点双条件；pool/global 无 scope ready、多节点、临时 runtime 均拒绝 |
| 单元测试 | Load Receipt 字段完整、逐项 digest/capability 一致、append-only；`required_entries_ready` 只能服务端计算 |
| 集成测试 | 完整 Receipt 适配为五字段 projection，可被现有 Workflow Run 守卫消费；错 run/lock/digest/not-ready 均拒绝 |

精确验证命令（从项目根目录执行）：

```bash
# 本 task 定向测试
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_runtime_plugin_reconcile -v

# 最小前置回归：Workflow Run + Preflight
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_workflow_run backend.tests.test_workflow_preflight -v

# 静态语法检查（.pyc 定向 Paperclip run scratch，不污染仓库）
PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache-task-008" \
  .venv/bin/python -m py_compile \
  backend/models/runtime_plugin.py \
  backend/services/runtime_plugin/reconcile_service.py \
  backend/services/runtime_plugin/materialization_manager.py \
  backend/database.py \
  backend/tests/test_runtime_plugin_reconcile.py

# 允许路径格式/白空检查
git diff --check -- \
  backend/models/runtime_plugin.py \
  backend/services/runtime_plugin/reconcile_service.py \
  backend/services/runtime_plugin/materialization_manager.py \
  backend/database.py \
  backend/tests/test_runtime_plugin_reconcile.py \
  docs/exec/exec_deck_008_backend_reconcile-load-receipt.md

# 包含未跟踪新文件的尾随空白检查（无匹配时通过）
! rg -n '[[:blank:]]+$' \
  backend/models/runtime_plugin.py \
  backend/services/runtime_plugin/reconcile_service.py \
  backend/services/runtime_plugin/materialization_manager.py \
  backend/database.py \
  backend/tests/test_runtime_plugin_reconcile.py \
  docs/exec/exec_deck_008_backend_reconcile-load-receipt.md
```

路径闭集核验必须执行以下精确命令：

```bash
# 实现前
git status --short > "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_008.status.before"

# 实现与验证后
git status --short > "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_008.status.after"
diff -u \
  "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_008.status.before" \
  "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_008.status.after" || true
git status --short -- \
  backend/models/runtime_plugin.py \
  backend/services/runtime_plugin/reconcile_service.py \
  backend/services/runtime_plugin/materialization_manager.py \
  backend/database.py \
  backend/tests/test_runtime_plugin_reconcile.py \
  docs/exec/exec_deck_008_backend_reconcile-load-receipt.md
```

`diff -u` 是人可读证据，预期在有实现变更时产生差异，因此用 `|| true` 保留输出而不把“有预期差异”误判为测试失败。`ExecTaskAgent` 必须逐行判定新增差异是否只属于 §11 闭集，并在正式报告列出结果。共享工作树的既有差异不是本 task 产出，不得清理或归因。

无法执行任一命令时，`ExecTaskAgent` 必须在正式报告和执行 Issue 同时记录：完整命令、exit code/关键 stderr、环境或依赖原因、受影响验收项、替代证据与唯一 owner/action。未执行或失败的核心验收不得标记通过；无安全替代证据时按 Paperclip 规则设为 `blocked`。

## 9. 完成标志

- [ ] settings 意图写入 `enabledPlugins`/`extraKnownMarketplaces`
- [ ] headless reconcile 在第一条 query 前同步完成
- [ ] CLI 备选路径受控执行，校验来源、超时、输出和审计
- [ ] 三维状态独立记录，UI 显示"已声明但未物化"而非笼统"已安装"
- [ ] 物化幂等：`materialization_key` 唯一、实际 digest 复验、节点本地原子发布；旧制品留存仅消费权威 pin/recoverable 证明，不在本 task 实现真实留存
- [ ] Load Receipt 内唯一 `receipt_id` 逐项记录插件加载状态；`WorkflowRun.runtime_load_receipt_id` 只引用该值
- [ ] 完整 Receipt 保留 run/lock/digest、单节点 placement、`artifact_set_hash`、`policy_revision`、`scope=session`、`session_loaded` 与逐项 digest/evidence，并能严格投影为现有 Workflow Run 五字段 readiness 合同
- [ ] required 插件全部 `loaded` 后才能进入 `running`
- [ ] 与 task_009 的边界成立：本 task 不创建 Session/不转 `running`，task_009 消费 Receipt、创建同 node Session 后调用现有守卫
- [ ] 单元/集成测试覆盖 reconcile 成功/失败、CLI 控制面、幂等物化、Gate 拒绝、Load Receipt 生成与 Workflow Run 真实 reader 联调
- [ ] 本 task 定向测试、Workflow Run/Preflight 最小回归、`py_compile`、`git diff --check` 与路径闭集核验全部完成并留下证据

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| settings 写入失败导致 reconcile 无限重试 | 高 | 最大重试次数 + 指数退避 + 错误记录 |
| CLI 子进程注入攻击 | 高 | 禁止拼接用户输入；使用列表传参；校验来源 |
| marketplace/CAS 依赖不可用 | 高 | 只通过 `ArtifactProvider` 消费 staged artifact；超时/不可用进入 `materialization_status=failed`，不越权实现下载/冷恢复 |
| 留存证明被节点 cache 冒充 | 高 | 只消费权威 `RetentionEvidenceReader`；缺证据 fail closed，不声称 production-ready |
| 多节点/临时 runtime readiness 误报 | 高 | 强制 pool==environment + local_persistent 双条件、node/session scope 和逐项 digest；其他形态阻断 |
| 完整 Receipt 直接传给 strict Workflow Run projection | 高 | 用显式五字段 adapter；测试锁定 key 集合与错 run/lock/digest/ready 拒绝 |
| `session_loaded` 被误当作 AgentSession 已创建 | 高 | 冻结为 run-scoped headless load 证明；真实 Session 与转 `running` 唯一 owner 为 task_009 |
| `/plugin` 文本被误用 | 高 | 代码审查 + 测试断言：任何路径不得发送 `/plugin install` 文本 |
| 共享 `backend/database.py` 覆盖前序实现 | 高 | 仅在现有 Workflow Run 初始化后追加本 task 表/索引/guard；执行前后路径与差异核对 |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/models/runtime_plugin.py`（新建；仅本 task 状态、placement、Receipt/entry 模型）
- `backend/services/runtime_plugin/reconcile_service.py`（新建；仅 settings/headless reconcile、受控 CLI、Receipt/projection）
- `backend/services/runtime_plugin/materialization_manager.py`（新建；仅单节点幂等、digest 复验、原子发布与依赖消费端口）
- `backend/database.py`（修改；仅增量追加本 task 的 materialization/reconcile-attempt/receipt/entry 表、索引与 guard）
- `backend/tests/test_runtime_plugin_reconcile.py`（新建；仅本 task 定向单元/集成测试）

以上五个实现/测试路径与 §5 前五行一致；未列出的实现、测试或配置文件默认不授权。

唯一非实现写入例外：`ExecTaskAgent` 可新建或增量更新 `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md`，且只能回填本 task 的正式执行差异、验收/测试证据、路径闭集、回滚与风险。该例外不授权其他实现、模板、设计、Issue、Task 或 Stage 变更；其余 `docs/exec/` 仍全部禁止。

### 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `docs/exec/`，但上文精确列出的 `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md` 正式报告例外除外
- `frontend/`、Claude Code 二进制/SDK、marketplace 服务与 Paperclip Plugin worker 实现
- 除上述 5 个路径以外的任何实现、测试、依赖锁或部署配置
- `backend/models/workflow_run.py`、`backend/services/workflow/run_service.py`、`backend/tests/test_workflow_run.py`、`backend/models/workflow_preflight.py`、`backend/services/workflow/preflight_service.py`、`backend/tests/test_workflow_preflight.py`
- `backend/database.py` 中与本 task 四类表/索引/guard 无关的既有表或初始化逻辑；尤其禁止覆盖 [SUO-304](/SUO/issues/SUO-304) 的 Workflow Run 表/trigger
- marketplace 下载、共享 CAS/冷存储、restore/purge、真实留存策略、多节点调度或临时 runtime 分发
- 文本 `/plugin install` 成功路径、用户输入 shell 拼接、活动 run 热刷新，或借本 task 创建/管理 Session、写 `agent_session_id`、发送 query、改写 Workflow Run 状态机
- 修改 `docs/task/TASK-REQUIREMENT-FORMAT.md` 源模板；它仅由 `ExecTaskAgent` 在执行前读取并填充受控副本/执行上下文

## 12. 命名隔离声明

- 物化记录使用 `runtime_materialization_id` 前缀
- Receipt 对象主键唯一命名为 `receipt_id`，值使用 `rlr_` 前缀
- `runtime_load_receipt_id` 仅保留为已有 Workflow Run 对 `receipt_id` 的引用字段，禁止在 Receipt 模型/表内再定义同义 ID
- Claude Code Plugin 字段使用 `claude_code_plugin_*` 前缀

## 13. 未决决策引用

- `DECK-GATE-DEC-017`：`conditional_frozen`。本 task 必须重算实际 artifact digest 并消费受信签名/留存证明；不实现 marketplace/CAS/冷存储/真实留存。开发/测试可显式保留 `legacy_unverified` 但不得升级；production 请求在当前 Gate 下 fail closed，不得标记 `production_ready`。
- `DECK-GATE-DEC-018`：设计已冻结，但本 task 的 rollout 仅限 `runtime_pool_id == runtime_environment_id` 且 `distribution_mode=local_persistent` 的单节点特例。scoped readiness、`runtime_node_id`、`artifact_set_hash`、`policy_revision`、`session_loaded` 和逐项 digest 不得回滚；多节点/临时 runtime 仍为 rollout 阻断。
- 本 task 合同的通过只表示可进入后续 Stage/execute 审查，不表示上述任一 production Gate 获得批准。
