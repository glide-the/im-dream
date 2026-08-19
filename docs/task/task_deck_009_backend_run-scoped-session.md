# task_deck_009_backend_run-scoped-session

## 1. 任务标题

ClaudeAgent Run-Scoped Session、原子启动与远程交互限制

## 2. 关联 Issue

- **Issue ID**: `DECK-009`
- **Issue 标题**: ClaudeAgent Run-Scoped Session 与远程交互限制
- **Task readiness Issue**: [SUO-314](/SUO/issues/SUO-314)
- **来源控制项**: [SUO-217](/SUO/issues/SUO-217)
- **类型 / Domain**: `backend`；`backend` 只表示 domain，不是 Agent 名称
- **优先级**: P0 / high
- **标签**: `claude-agent`, `session`, `remote-interaction`, `readiness`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.4、§7.5、§11、§13.3、§18
  - `docs/design/deck/design_002_deck-plugin-decision-gates.md`，重点 `DECK-GATE-DEC-017/018/020`
  - `docs/design/deck-claude-agent.md`
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 `DECK-009`
- **Stage**: `docs/stage/stage_deck-plugin-voice-ink-dream-integration.md` v1.8，Stage 2 / Wave 4

## 3. 任务目标

在已完成的 task_008 Receipt/readiness 合同之上，实现可持久化、可幂等恢复的 run-scoped `AgentSession`。Session 必须绑定同一 `workflow_run_id`、Receipt、runtime environment/node、artifact set 与 policy；只有 Session 已创建且 Receipt 校验通过时，才能在一个数据库事务中同时完成：

1. `AgentSession creating → active`；
2. `WorkflowRun.agent_session_id` 与 `runtime_load_receipt_id` 的一次性绑定；
3. `WorkflowRun queued → running` 与对应 transition 追加。

本 task **只消费** task_008 已落地的完整 Receipt reader 和五字段 Workflow Run readiness projection，不执行或重实现 materialization、reconcile、CLI、Receipt 生成/持久化。Session adapter 在返回 active handle 前不得发送第一条 query；会话内规范化插件集合与 settings hash 创建后不可变。

本 task 的执行域继续被 `DECK-GATE-DEC-017/018/020` 限定为：

- 只接受 `runtime_pool_id == runtime_environment_id`、`distribution_mode=local_persistent`、单一 `runtime_node_id`；
- 只允许 `deployment_tier=development|test`；production 必须 fail closed；
- 不实现或宣称多节点调度、临时 runtime、真实 marketplace/Claude Code 二进制、共享 CAS/冷存储、restore/purge 或 production-ready；
- Voice thread 与 run-scoped Session 是不同对象；Voice 来源必须保留消息级引用，绝不复用为 `agent_session_id`。

唯一实现责任人为 `ExecTaskAgent`。TaskDesignAgent 只冻结本文合同，不进入 execute，不修改实现或测试代码。

## 4. 实现步骤

### Step 0: Execute 准入与责任锁

`ExecTaskAgent` 开始任何实现写入前必须同时满足：

1. 存在一个只对应 `task_deck_009_backend_run-scoped-session.md` 的独立 Paperclip execute Issue；[SUO-314](/SUO/issues/SUO-314) 是 readiness 合同修订 Issue，不得直接作为 execute Issue 使用。
2. execute Issue 只有一个 assignee：`ExecTaskAgent`；`backend` 不得被解释为 Agent 身份。
3. Paperclip harness 或 `ExecTaskAgent` 已为当前 run checkout 该 execute Issue 并取得 execution lock；未取得 lock、发生 `409` 或存在第二 assignee 时禁止写入。
4. 直接执行前置 [SUO-312](/SUO/issues/SUO-312)（task_008）保持 `done`，并读取：
   - `docs/task/task_deck_008_backend_reconcile-load-receipt.md`
   - `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md`
   - 本文、Stage v1.8 和 `DECK-GATE-DEC-017/018/020`
5. 从只读源模板 `docs/task/TASK-REQUIREMENT-FORMAT.md` 创建当前 run scratch 下的受控填充副本；不得修改源模板。填充副本必须逐项带入 execute Issue、本文 §5/§11、验收、测试与工作树基线。
6. 记录 `git status --short` 基线。共享工作树已有差异不得清理、覆盖、重置或归因于本 task；允许路径若存在无法安全合并的他人改动，停止受影响写入并在 execute Issue 写明 owner/action。

### Step 1: 定义持久化 AgentSession 合同

在 `backend/models/agent_session.py`（新建）定义 strict、frozen 的 Session 模型。字段至少包括：

```python
class AgentSessionStatus(str, Enum):
    CREATING = "creating"
    ACTIVE = "active"
    TERMINATED = "terminated"
    FAILED = "failed"

class AgentSession(BaseModel):
    agent_session_id: str                 # as_<uuid>
    workflow_run_id: str                  # run_<uuid>
    runtime_load_receipt_id: str          # task_008 receipt_id
    runtime_environment_id: str
    runtime_pool_id: str
    distribution_mode: Literal["local_persistent"]
    runtime_node_id: str
    artifact_set_hash: str
    policy_revision: str
    deployment_tier: Literal["development", "test"]
    runtime_plugin_lock_id: str
    runtime_plugin_lock_digest: str
    settings_json: str                    # canonical、脱敏，不含 secret/token
    settings_hash: str                    # sha256:<64 hex>
    plugin_set_hash: str                  # plugin/version/digest/capability canonical hash
    session_request_key: str              # run + receipt + settings_hash 的 canonical hash
    attempt_number: int
    status: AgentSessionStatus
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    terminated_at: datetime | None
```

约束：

- `CREATING → ACTIVE|FAILED`、`ACTIVE → TERMINATED|FAILED`；`TERMINATED|FAILED` 为终态，禁止复活。
- `settings_json` 只允许 `enabledPlugins`、受信 marketplace 引用和批准能力投影；禁止保存 credential、secret、Voice system prompt、原消息正文或任意客户端注入字段。
- `settings_hash`、`plugin_set_hash`、Receipt/lock/placement/policy 绑定和 `session_request_key` 创建后不可变。
- 同一 `workflow_run_id` 任一时刻最多一个 `creating|active` Session。失败重试可创建新 attempt，但不得复活旧行；Receipt/node/artifact/policy 已变化时必须使用 task_008 生成的新 Receipt。
- Session ID 与 Voice thread ID 命名和语义隔离；任何 `agent_session_id == source_voice_thread_id` 的输入都必须拒绝。

### Step 2: 只读消费 task_008 Receipt/readiness

`backend/services/claude_agent/session_manager.py` 通过注入的 `ReconcileService` 只读接口消费：

- `read_receipt(receipt_id)`：读取完整、append-only `RuntimeLoadReceipt`；
- `read_workflow_readiness(receipt_id)`：读取现有 `RuntimeLoadReceiptReadiness` 所需的精确五字段 projection。

禁止调用或复制 `declare_and_reconcile()`、`cli_install()`、`create_load_receipt()`、`_persist_receipt()`、materialization manager 或任何 task_008 私有实现。

Session 创建前必须对完整 Receipt fail-closed 校验：

1. `receipt.workflow_run_id == workflow_run.workflow_run_id`；
2. lock ID/digest 同 Workflow Run 当前冻结 lock 与数据库权威 digest 一致；
3. `runtime_environment_id`、`runtime_pool_id`、`distribution_mode`、`runtime_node_id` 与当前受信 placement 一致；
4. `artifact_set_hash` 与按 lock required entries 重算的 canonical hash 一致；
5. `policy_revision` 同当前 preflight/runtime 受信策略一致；
6. `deployment_tier in {development,test}`、`scope=session`、`readiness_state=session_loaded`、`required_entries_ready=true`；
7. Receipt 每个 required entry 的 plugin ID、version、expected/materialized digest、capability 与 load status 同 lock/settings 精确一致；插件、版本、digest、能力不得多、少或扩大；
8. Session 必须在 Receipt 的同一 node/artifact set/policy 上启动。节点变化、Receipt 错绑或 Receipt 内容不一致时，拒绝创建并要求 task_008 产生新 attempt/new Receipt；禁止修改旧 Receipt。

五字段 projection 只传给 `WorkflowRunService` 的既有 readiness 守卫；禁止把完整 Receipt dict 传入 strict projection，也禁止扩大或修改 task_008 reader 的五字段接口。

### Step 3: 生成隔离、不可变的 run settings

Session manager 从冻结 lock、批准能力和受信 marketplace policy 生成 canonical settings：

```json
{
  "enabledPlugins": {
    "ink-dream-tools@voice-decks": true
  },
  "extraKnownMarketplaces": {
    "voice-decks": {
      "source": "trusted-server-resolved-reference"
    }
  },
  "pluginPolicy": {
    "allowedCapabilities": [
      "story.context.read",
      "story.result.produce"
    ]
  }
}
```

- 插件集合必须等于 lock 中 required/selected 插件的精确集合，能力必须等于审批、snapshot policy、用户/workspace 权限与 runtime 支持的交集；禁止由客户端或 Voice thread settings 补充。
- marketplace 引用必须来自 task_008 已使用的受信 source policy；本 task 不下载 marketplace，不调用真实 Claude Code CLI/SDK，不把 `/plugin` 文本当成功路径。
- canonical JSON 计算 `settings_hash`；plugin ID/version/digest/capability 排序后计算 `plugin_set_hash`。两个 hash 与完整绑定字段持久化并由数据库 guard 保持不可变。
- 当前 run 的 binding、version、snapshot、能力或配置变化不得反写 Session；变化只影响新 preflight/new run/new Session。

### Step 4: Session 创建幂等、并发与 adapter 边界

在 `session_manager.py` 内定义注入式 `RunSessionAdapter`，用于测试 fake 与后续真实 ClaudeAgent adapter 对接；不得修改现有 SSE endpoint 协议：

```python
class RunSessionAdapter(Protocol):
    async def start_session(
        self,
        *,
        agent_session_id: str,
        session_request_key: str,
        settings_json: str,
        runtime_node_id: str,
        allow_query: Literal[False],
    ) -> SessionStartResult: ...

    async def terminate_session(
        self,
        *,
        agent_session_id: str,
        reason_code: str,
    ) -> None: ...
```

幂等与并发语义：

1. `session_request_key = sha256(canonical(workflow_run_id, receipt_id, settings_hash))`。
2. 使用数据库事务和唯一约束争抢创建 ownership；同 key 并发只能有一个 owner 调用 adapter，其他调用返回同一个 `creating|active` attempt，或等待 owner 的持久结果后重放。
3. 同一 run 携带不同 Receipt/settings 的并发请求返回结构化 `AGENT_SESSION_CREATE_CONFLICT`，不得覆盖已有 attempt。
4. adapter 的 `start_session` 必须以 `agent_session_id/session_request_key` 幂等，并固定 `allow_query=False`。Session manager 本身不发送 query，也不提供绕过 readiness 的 query 路径。
5. `creating` attempt 需要有限 lease/timeout。owner 崩溃后的恢复必须基于持久行完成幂等重试或失败收敛；禁止永久占用、内存锁作为唯一真相源或静默创建第二个活动 Session。

### Step 5: 冻结 Receipt + Session + queued → running 的最小原子路径

修改 `backend/services/workflow/run_service.py` 的 `queued → running` 路径，使 `runtime_load_receipt_id` 与 `agent_session_id` 成为共同必填，并在一个 `BEGIN IMMEDIATE` 事务中完成：

1. 重新读取 workspace-scoped Workflow Run，确认仍为 `queued`、`status_version` 未变化，两个绑定字段仍为 `NULL`；
2. 重新消费五字段 Receipt readiness，执行既有 run/lock/digest/required-ready 守卫；
3. 读取 `agent_sessions` 中同 `agent_session_id` 的 `creating` 行，校验 run、Receipt、environment/node/artifact set/policy、lock digest、settings/plugin hashes 全部一致；
4. 将该 Session 更新为 `active` 并写 `started_at`；
5. 同一事务把 Workflow Run 更新为 `running`，一次性同时写入 `runtime_load_receipt_id`、`agent_session_id`、`started_at` 和递增的 `status_version`；
6. 同一事务追加唯一 `queued → running` transition；
7. 任一步失败全部 rollback，不允许出现 `running + NULL session`、`running + creating session`、只绑 Receipt、只绑 Session、重复 transition 或错 run/Receipt Session。

在 `backend/models/workflow_run.py` 同步冻结模型规则：

- `preflight|queued` 时两个绑定字段都必须为空；
- `running` 及其后续非终止启动状态必须同时拥有 Receipt 与 Session；
- 两个字段只能在 `queued → running` 同一状态版本中由 `NULL` 一次性赋值，之后不可修改或清空；
- 终态不可复活，既有状态机的其他合法流转不得借本 task 改写。

`backend/database.py` 只能增量追加：

- `agent_sessions` 表、必要索引、同 run 单 active/creating partial unique 约束；
- Session identity/settings/plugin-set/placement 不可变 trigger、状态流转/终态 guard；
- Workflow Run Receipt + Session 联合一次性绑定 guard，以及 Session 与 Receipt/run 同源 guard；
- `source_message_id/source_message_time` 的幂等 schema upgrade；
- 已有 Workflow Run、Preflight、task_008 四表/append-only Receipt trigger 不得删除、重建或放宽。

### Step 6: 失败回滚、补偿与状态映射

失败语义必须显式且可测试：

- Receipt/settings/placement 校验失败：不调用 adapter，不创建活动 Session；run 保持 `queued` 且两个绑定字段为空，返回具体 fail-closed error。
- adapter 启动失败/超时：attempt 转 `failed`；Workflow Run 通过既有合法路径从 `queued → failed`，`failed_step=agent_session_start`，`error_code` 使用结构化启动错误；不得绑定 Receipt/Session。
- adapter 已创建远端 Session、但最终数据库事务失败：先完整 rollback；随后以相同 `agent_session_id` 调用幂等 terminate 补偿。补偿成功则 attempt 记 `failed/terminated`；补偿无法确认时保留可恢复失败记录并拒绝创建第二个活动 Session。
- 数据库注入失败点（Session 更新后、Run 更新后、transition 写入后）均不得留下部分提交；重试必须返回已有完整成功结果或执行受控恢复。
- 用户取消：run 使用既有 `cancelled` 合法流转，Session 终止原因记录为 `USER_CANCELLED`。
- runtime/session 错误：run 使用 `failed`，保存 `failed_step/error_code`，Session 转 `failed`。
- 正常执行结束：Session 转 `terminated`；Workflow Run 的 `output_validating/pending_review/confirmed/completed` 业务流转仍由既有 Workflow Run/下游 owner 驱动，本 task 不把 Session 关闭直接伪装为业务完成。
- 安全撤销只消费已冻结的结构化 reason 并执行终止；撤销策略、11 项 evidence pack 和事件审计分别属于后续安全/审计 task，本 task 不扩大 production rollout。

### Step 7: 远程热刷新守卫与插件集合不可变

在 `backend/services/claude_agent/remote_interaction_guard.py` 实现 `RemoteInteractionGuard`：

```python
async def guard_reload(
    *,
    workflow_run_id: str | None,
    agent_session_id: str | None,
    proposed_plugins: list[PluginRef],
    proposed_capabilities: list[str],
) -> GuardResult:
    ...
```

强制规则：

- 任何 run-bound `creating|active` Session，及 `running|output_validating|pending_review|confirmed` Workflow Run，均拒绝 `apply_flag_settings`/`reload_plugins`，返回 `RUNTIME_PLUGIN_RELOAD_UNSUPPORTED`。
- 已终止/失败的 run-scoped Session 也不得复活或热刷新；配置/版本/digest/能力变化必须走新 preflight/new run/new Receipt/new Session。
- 仅 `workflow_run_id is None` 且 `agent_session_id` 明确属于空闲管理 smoke 上下文时，才可考虑热刷新；插件必须已物化，marketplace 已缓存，版本/digest/capability 未扩大，环境仍为 development/test。
- smoke 结果只返回诊断证据，不写 Workflow Run readiness、不创建 Receipt、不授权 production、不改变任何活动 Session。
- 新 marketplace、未物化版本、digest 变化、能力扩张或任何无法证明的上下文一律 fail closed；本 task 不调用真实 reload 二进制能力，仅冻结 guard/adapter 合同并以 fake 测试。

### Step 8: Voice 消息级来源与命名隔离

对新建 Voice 来源 Workflow Run，`backend/models/workflow_run.py`、`backend/services/workflow/run_service.py` 与 `backend/database.py` 必须共同保存不可变来源元组：

```text
source_voice_thread_id
source_message_id
source_message_time
```

- 新写入时三者必须同时提供或同时为空；普通非 Voice run 保留 `NULL`。
- `source_message_time` 必须为带时区的服务端验证时间值；不得保存原消息正文、Voice system prompt 或 secret。
- 来源元组加入 idempotency/semantic fingerprint；同 key 改变 thread、message ID 或 message time 必须冲突。
- retry 创建新 run 时完整继承原来源元组；历史 thread-only 行可只读兼容，不得猜测或伪造消息级来源。
- `source_voice_thread_id/source_message_id/source_message_time` 创建后不可变；任何一个都不得赋给 `agent_session_id`。
- 本 task 只冻结后端来源和 Session 隔离；`DECK-GATE-DEC-020` 的来源卡片、路由和文案由 Stage 3 前端 task 实现。

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/agent_session.py` | 新建 | strict/frozen AgentSession、状态、settings/plugin-set hash 与 binding 模型 |
| `backend/services/claude_agent/session_manager.py` | 新建 | 只读消费 task_008、生成 settings、幂等 Session 创建、原子启动编排与失败补偿 |
| `backend/services/claude_agent/remote_interaction_guard.py` | 新建 | 活动 run/session reload 拒绝与受限 management smoke 判定 |
| `backend/models/workflow_run.py` | 修改 | Receipt + Session 共同绑定生命周期规则；消息级来源字段 |
| `backend/services/workflow/run_service.py` | 修改 | Session-aware `queued → running` 原子事务、来源元组 create/retry/idempotency |
| `backend/database.py` | 修改 | 增量追加 agent_sessions、索引/trigger、联合绑定 guard、来源字段 schema upgrade |
| `backend/tests/test_agent_session.py` | 新建 | Session/Receipt/并发/热刷新/原子失败/来源定向测试 |
| `backend/tests/test_workflow_run.py` | 修改 | 更新并锁定联合绑定、来源元组、回归状态机测试 |
| `backend/tests/test_runtime_plugin_reconcile.py` | 修改 | 仅把 receipt-only `running` 集成断言对齐为 task_009 的 Receipt + Session 联合启动；不得改写 task_008 生成/不可变验收 |
| `docs/exec/exec_deck_009_backend_run-scoped-session.md` | 新建或增量更新 | 仅 `ExecTaskAgent` 回填本 task 唯一正式执行报告；非实现例外 |

只读消费、不授权修改：

- `backend/services/runtime_plugin/reconcile_service.py`
- task_008 模型/materialization 实现与 Receipt 表
- `backend/services/workflow/preflight_service.py` 与对应模型/测试
- 现有 ClaudeAgent SSE endpoint 与前端 chat 组件

## 6. 输入 / 输出说明

**输入**：

- `WorkflowRun`（必须为 workspace-scoped `queued`，两个绑定字段为空）
- task_008 `RuntimeLoadReceipt` 完整只读对象与五字段 readiness projection
- 冻结 `DeckRuntimePluginLock`、lock digest 与 `deck_runtime_snapshot_id`
- 受信 runtime placement/policy（environment/pool/node/distribution/artifact/policy/deployment tier）
- 批准能力交集与受信 marketplace 引用
- 可选完整 Voice 来源元组（thread/message/time）
- 注入式、幂等 `RunSessionAdapter`

**输出**：

- 持久化、不可变绑定的 `AgentSession` attempt
- canonical、脱敏 run settings 及 `settings_hash/plugin_set_hash`
- 原子绑定 Receipt + Session 后的 `running` Workflow Run 与唯一 transition
- 结构化 Session 启动/终止/热刷新拒绝结果
- 可供 task_013 消费的状态事实；本 task 不实现统一事件系统

## 7. 依赖项

- **Issue 层来源依赖**: `DECK-008`（Reconcile/Receipt）、`DECK-007`（Workflow Run）、`DECK-006`（Preflight）
- **Stage 串行链**: `task_deck_006 → task_deck_007 → task_deck_008 → task_deck_009`
- **已完成直接执行前置**: [SUO-312](/SUO/issues/SUO-312)，含 `docs/exec/exec_deck_008_backend_reconcile-load-receipt.md`
- **下游依赖**: `DECK-013`（统一事件与审计）及 Stage 3 来源展示
- **execute 调度依赖**: 独立 Paperclip execute Issue、single assignee `ExecTaskAgent`、当前 run checkout/execution lock

## 8. 测试策略

| 测试类型 | 可执行覆盖 |
|---|---|
| 单元测试 | Session 模型状态、终态、hash/placement/settings 不可变，secret/额外字段拒绝 |
| 单元测试 | settings 只含 lock 插件和批准能力；插件多/少、版本/digest/capability 漂移均拒绝 |
| 单元测试 | 完整 Receipt 的 run/lock/digest/environment/node/artifact/policy/scope/state/ready/entry 逐项绑定；任一错绑不调用 adapter |
| 单元测试 | 同 `session_request_key` 串行/并发返回同 attempt、adapter 只调用一次；竞争 Receipt/settings 返回冲突 |
| 单元测试 | `creating/active` 插件集合不可变；活动与已终止 run-scoped Session reload 均拒绝；受限 management smoke 不写 readiness |
| 单元测试 | Voice 来源元组三者同空同有、消息级幂等冲突、retry 继承、thread/session ID 不混用 |
| 失败注入 | adapter 失败/超时、Session 更新后、Run 更新后、transition 追加后的异常；无部分提交，补偿幂等 |
| 集成测试 | task_008 真实 Receipt + Session + Workflow Run 联合启动；成功仅一个 `queued → running` transition |
| 回归测试 | Workflow Run、Preflight、task_008 最小套件全部通过；task_008 不新增 reconcile/Receipt 副本 |

精确验证命令（从项目根目录执行）：

```bash
# 本 task 定向测试
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest backend.tests.test_agent_session -v

# 最小前置回归：Workflow Run + Preflight + task_008 Receipt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest \
  backend.tests.test_workflow_run \
  backend.tests.test_workflow_preflight \
  backend.tests.test_runtime_plugin_reconcile -v

# 静态语法检查（.pyc 定向 Paperclip run scratch，不污染仓库）
PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache-task-009" \
  .venv/bin/python -m py_compile \
  backend/models/agent_session.py \
  backend/services/claude_agent/session_manager.py \
  backend/services/claude_agent/remote_interaction_guard.py \
  backend/models/workflow_run.py \
  backend/services/workflow/run_service.py \
  backend/database.py \
  backend/tests/test_agent_session.py \
  backend/tests/test_workflow_run.py \
  backend/tests/test_runtime_plugin_reconcile.py

# 允许路径格式/白空检查
git diff --check -- \
  backend/models/agent_session.py \
  backend/services/claude_agent/session_manager.py \
  backend/services/claude_agent/remote_interaction_guard.py \
  backend/models/workflow_run.py \
  backend/services/workflow/run_service.py \
  backend/database.py \
  backend/tests/test_agent_session.py \
  backend/tests/test_workflow_run.py \
  backend/tests/test_runtime_plugin_reconcile.py \
  docs/exec/exec_deck_009_backend_run-scoped-session.md

# 包含未跟踪新文件的尾随空白检查（无匹配时通过）
! rg -n '[[:blank:]]+$' \
  backend/models/agent_session.py \
  backend/services/claude_agent/session_manager.py \
  backend/services/claude_agent/remote_interaction_guard.py \
  backend/models/workflow_run.py \
  backend/services/workflow/run_service.py \
  backend/database.py \
  backend/tests/test_agent_session.py \
  backend/tests/test_workflow_run.py \
  backend/tests/test_runtime_plugin_reconcile.py \
  docs/exec/exec_deck_009_backend_run-scoped-session.md
```

路径闭集核验必须执行：

```bash
# 实现前
git status --short > "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_009.status.before"

# 实现与验证后
git status --short > "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_009.status.after"
diff -u \
  "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_009.status.before" \
  "$PAPERCLIP_RUN_SCRATCH_DIR/task_deck_009.status.after" || true

git status --short -- \
  backend/models/agent_session.py \
  backend/services/claude_agent/session_manager.py \
  backend/services/claude_agent/remote_interaction_guard.py \
  backend/models/workflow_run.py \
  backend/services/workflow/run_service.py \
  backend/database.py \
  backend/tests/test_agent_session.py \
  backend/tests/test_workflow_run.py \
  backend/tests/test_runtime_plugin_reconcile.py \
  docs/exec/exec_deck_009_backend_run-scoped-session.md
```

`diff -u` 仅提供人可读证据，预期实现后有差异，因此保留 `|| true`。`ExecTaskAgent` 必须逐行判断新增差异是否属于 §11 闭集，并在正式报告记录。无法执行任一核心命令时，须同时在报告和 execute Issue 记录完整命令、exit code/关键 stderr、影响验收、替代证据与 owner/action；无安全替代证据时按 Paperclip 规则标记 `blocked`。

## 9. 完成标志

- [ ] 独立 execute Issue、唯一 `ExecTaskAgent` assignee 与 checkout/execution lock 均已验证
- [ ] Session 只读消费 task_008 的完整 Receipt 与五字段 readiness；未重实现 materialization/reconcile/CLI/Receipt
- [ ] `AgentSession` 已持久化，run/Receipt/lock/environment/node/artifact set/policy/settings/plugin set 绑定创建后不可变
- [ ] 同 key 幂等与并发只有一个创建 owner/adapter start；冲突语义 fail closed
- [ ] `creating → active`、两个 Workflow Run ID 绑定、`queued → running` 与 transition 在同一事务提交；失败无部分状态
- [ ] adapter 失败、数据库失败与补偿路径可恢复、可审计；Session/Run 终止与错误状态映射明确
- [ ] 第一条 query 之前已校验 task_008 Receipt、创建 active Session 并提交 `running`；Session manager 不提前发送 query
- [ ] 会话内插件/settings 集合固定；活动或历史 run-scoped Session 不可热刷新
- [ ] 仅 development/test 的空闲 management smoke 可通过守卫，且不写 readiness、不生成 Receipt、不授权 production
- [ ] Voice 来源包含 thread/message/time，不复用 Session ID；来源不可变且进入 idempotency fingerprint
- [ ] production、多节点、临时 runtime、真实 marketplace/Claude 二进制继续 fail closed
- [ ] 定向测试、Workflow Run/Preflight/task_008 回归、静态检查、格式检查和路径闭集核验均通过并留证
- [ ] 唯一正式报告 `docs/exec/exec_deck_009_backend_run-scoped-session.md` 已由 `ExecTaskAgent` 回填

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| Receipt 五字段 projection 不足以证明 node/artifact/policy | 高 | Session manager 同时只读完整 Receipt；五字段 projection 仅交给既有 Workflow Run 守卫 |
| Session 已远端启动但数据库提交失败 | 高 | 幂等 adapter key + 全事务 rollback + terminate 补偿 + 可恢复失败行；禁止第二个 active Session |
| 并发创建产生多个 Session 或重复 transition | 高 | 数据库 ownership/partial unique/CAS status_version；同 key 重放，冲突 key 拒绝 |
| Workflow Run 只绑 Receipt 或只绑 Session | 高 | 模型校验 + 联合 UPDATE + 数据库 trigger 三层约束 |
| 热刷新绕过导致能力漂移 | 高 | run/session 双重状态守卫；settings/plugin-set hash 不可变；新能力只能新 run |
| Voice thread 被当成 Agent session | 高 | ID 命名隔离、消息级来源元组、显式拒绝相等值与重试继承测试 |
| 既有 thread-only 数据无法补齐消息来源 | 中 | 历史只读兼容；新写入强制完整元组，禁止猜测回填 |
| task_008 回归测试仍假设 receipt-only 启动 | 中 | 仅最小修改该集成断言为 Receipt + Session 联合启动，保留 Receipt 生成/不可变验收 |
| 本地 fake 被误当真实 Claude/marketplace 证据 | 高 | 报告明确 test double 边界；production、多节点、临时 runtime 与真实二进制继续阻断 |
| 共享 `backend/database.py` 覆盖前序实现 | 高 | 只做增量 schema/trigger；执行前后 scoped diff；task_007/task_008 回归 |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围（实现/测试闭集）

- `backend/models/agent_session.py`（新建；仅本 task AgentSession 模型与校验）
- `backend/services/claude_agent/session_manager.py`（新建；仅 Session 创建/恢复/终止编排与 task_008 reader 消费）
- `backend/services/claude_agent/remote_interaction_guard.py`（新建；仅 reload guard 与 management smoke 判定）
- `backend/models/workflow_run.py`（修改；仅 Receipt + Session 联合生命周期与消息级来源）
- `backend/services/workflow/run_service.py`（修改；仅 Session-aware 原子启动、失败映射与来源元组）
- `backend/database.py`（修改；仅 agent_sessions、必要索引/trigger、联合绑定 guard、来源字段增量升级）
- `backend/tests/test_agent_session.py`（新建；仅本 task 定向单元/集成测试）
- `backend/tests/test_workflow_run.py`（修改；仅联合绑定/来源/既有状态机回归）
- `backend/tests/test_runtime_plugin_reconcile.py`（修改；仅更新 receipt-only `running` 集成断言；task_008 其余断言不得改写或放宽）

以上九个实现/测试路径与 §5 前九行一致；未列出的实现、测试、配置或生成物默认禁止。

唯一非实现写入例外：`ExecTaskAgent` 可新建或增量更新 `docs/exec/exec_deck_009_backend_run-scoped-session.md`，且只能记录本 task 的执行差异、验收/测试证据、路径闭集、失败补偿、回滚与风险。该例外不授权任何其他 `docs/exec/` 文件。

### 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `docs/exec/`，但上文精确报告例外除外
- `docs/task/TASK-REQUIREMENT-FORMAT.md` 源模板；只允许执行前复制到当前 run scratch 并填充副本
- `frontend/`、Voice chat UI、story-workspace UI、现有 ClaudeAgent SSE endpoint 协议
- `backend/services/runtime_plugin/reconcile_service.py`、`backend/services/runtime_plugin/materialization_manager.py`、`backend/models/runtime_plugin.py` 与 task_008 数据表/Receipt append-only trigger
- `backend/models/workflow_preflight.py`、`backend/services/workflow/preflight_service.py`、`backend/tests/test_workflow_preflight.py`
- 除 §11 闭集外的实现/测试、依赖锁、部署配置、生成物或其他 task 文档
- materialization、reconcile、CLI、Receipt 生成/修改，marketplace 下载，真实 Claude Code 二进制/SDK 能力，CAS/冷存储/restore/purge
- 多节点调度、临时 runtime、production rollout 或以 fake/smoke 结果宣称 `production_ready`
- 发送 `/plugin install` 文本、拼接用户 shell、活动 run/session 热刷新、修改既有 Session 插件集合
- 把 `source_voice_thread_id` 或 `source_message_id` 复用为 `agent_session_id`，或保存原消息正文、system prompt、secret、完整未脱敏 settings
- 借本 task 改写 `queued → running` 以外的 Workflow Run 状态机、Preflight 权威、task_008 Receipt schema 或 Stage 排期

## 12. 命名与不可变性声明

- Session 主键唯一使用 `agent_session_id`，值使用 `as_` 前缀。
- task_008 Receipt 主键继续唯一使用 `receipt_id`（`rlr_` 前缀）；`WorkflowRun.runtime_load_receipt_id` 只引用该值。
- Voice 来源分别使用 `source_voice_thread_id`、`source_message_id`、`source_message_time`；它们不是 Session 标识。
- `agent_session_id`、Receipt ID、Voice thread/message ID 不得相互赋值或建立同义别名。
- Session 的 Receipt/lock/placement/policy/settings/plugin-set 绑定和 Workflow Run 的来源元组创建后不可变。

## 13. Gate 与限域结论

- `DECK-GATE-DEC-017`：仍为 `conditional_frozen`。本 task 只消费 task_008 已保存的 digest/signature/retention 状态；不创建供应链证明。`legacy_unverified` 只可在 development/test 原样消费，production fail closed。
- `DECK-GATE-DEC-018`：设计已冻结，但本 task 只实现 `pool == environment + local_persistent + development|test` 的单节点特例。Receipt 与 Session 必须保留 node/artifact set/policy 语义；Session 前节点变化要求新 Receipt，Session 后禁止迁移/复活，多节点/临时 runtime rollout 继续阻断。
- `DECK-GATE-DEC-020`：设计已冻结。Voice chat 保留原线程，Workflow Run 与 AgentSession 独立；本 task 保存 thread/message/time 来源，Stage 3 才实现双向卡片、运行详情和文案。
- 本 task 通过只表示 Stage 2 / Wave 4 的 development/test 合同可验证，不表示 production、多节点、临时 runtime、真实 ClaudeAgent/marketplace 或任何 rollout Gate 已放行。

## 14. Readiness 判定

本文已冻结以下 execute 合同：

- task_008 Receipt/readiness 只读消费边界；
- Session 持久化、幂等/并发、插件集合不可变；
- `agent_session_id + runtime_load_receipt_id + queued → running + transition` 最小原子闭集；
- 失败 rollback/补偿与终止/错误状态映射；
- Voice 消息级来源与 Session 命名隔离；
- 精确实现/测试路径闭集和唯一正式报告例外；
- `ExecTaskAgent`、独立 execute Issue、single assignee 与 checkout lock 前置；
- development/test 单节点限域及 production/multi-node/ephemeral/真实二进制 fail-closed 边界。

若 execute Issue 缺失、single-assignee/checkout 不成立、task_008 Receipt 接口与本文不一致、允许路径存在无法安全合并的他人改动，或任一核心原子性测试无法通过，执行 Issue 必须标记 `blocked` 并写明唯一 owner/action；不得通过扩大路径、跳过测试或放宽 Gate 宣称完成。
