# task_deck_007_backend_workflow-run

## 1. 任务标题

Workflow Run 创建、状态与幂等重试

## 2. 关联 Issue

- **Issue ID**: `DECK-007`
- **Issue 标题**: Workflow Run 创建、状态与幂等重试
- **类型**: backend
- **优先级**: P0
- **标签**: `story-workspace`, `workflow-run`, `idempotency`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §11.1, §11.2, §11.3, §11.4
  - `docs/design/story-workspace/story-workspace-layout-design.md` §5.6
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-007

## 3. 任务目标

实现 Workflow Run 的创建、状态管理和幂等重试。保留 SUO-198 全部字段并新增 Deck Plugin 相关字段。冻结 workspace/actor 作用域、一次性 Preflight Token 与幂等重放的单事务合同，并在本 task 内保存最小、append-only 的运行状态 transition；通用事件 envelope、投递与消费仍由 `DECK-013` 实现。本 task 只消费 `DECK-008` 产出的 load receipt 就绪合同来保护合法状态流转，不实现 reconcile、materialization 或 load receipt 内部逻辑。

## 4. 实现步骤

### Step 1: 定义 Workflow Run 模型

在 `backend/models/workflow_run.py`（新建）中定义：

```python
class WorkflowRun(BaseModel):
    # SUO-198 保留字段
    workflow_run_id: str            # run_<uuid>
    deck_plugin_id: str
    deck_plugin_version: str
    workflow_definition_ref: str
    deck_runtime_snapshot_id: str
    status: RunStatus
    failed_step: Optional[str]
    error_code: Optional[str]
    retry_of_run_id: Optional[str]

    # 本文新增字段
    deck_plugin_manifest_hash: str
    deck_plugin_binding_id: str
    binding_revision: int
    runtime_plugin_lock_id: str
    runtime_load_receipt_id: Optional[str]
    workflow_preflight_id: str
    agent_session_id: Optional[str]
    source_voice_thread_id: Optional[str]
    workspace_id: str                 # 从认证 workspace 上下文派生，禁止客户端覆盖
    idempotency_key: str
    input_hash: str
    semantic_fingerprint: str         # 规范化运行语义摘要；仅服务端计算
    status_version: int               # 与 transition_seq 同步单调递增

    # 时间戳
    created_by: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class RunStatus(str, Enum):
    PREFLIGHT = "preflight"
    QUEUED = "queued"
    RUNNING = "running"
    OUTPUT_VALIDATING = "output_validating"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CONTINUING = "continuing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Step 2: 实现状态机

```text
preflight → queued → running → output_validating → pending_review → confirmed
                │              │                 │              ├→ continuing → completed
                │              │                 │              └→ completed
                │              │                 └→ rejected
                ├──────────────┴────────────────────────────────→ failed
                └───────────────────────────────────────────────→ cancelled
```

状态规则：
- `preflight` 失败通常留在独立 Preflight；若运行已原子创建，则只能转 `failed`
- `queued → running` 需要读取既有、不可变的 `runtime_load_receipt` 就绪投影，并验证 receipt 绑定当前 `workflow_run_id`、runtime lock/digest 且全部 required 项成功；`runtime_load_receipt_id` 只允许在该事务中从 `NULL` 赋值一次，之后不可变
- `running → output_validating → pending_review` 需要规范化结果完整校验并原子持久化
- `pending_review → confirmed → continuing/completed` 由用户确认触发；`pending_review → rejected` 终止当前 run，重新生成必须新建 run
- `pending_review` 是唯一 API 审阅态；`awaiting review` 仅可作为 UI 文案
- 任一终态不得恢复为非终态；重试创建新 run
- 每次创建或合法状态变化必须在同一数据库事务追加一条 `workflow_run_transitions`；状态更新成功但 transition 缺失、或 transition 成功但状态未更新都必须整体回滚
- 本 task 只定义并验证上述 receipt 驱动的状态守卫；receipt 生成、逐项校验、reconcile、materialization、缓存与 `runtime_load_receipts` 表均属于下游 `DECK-008`

本 task 消费的边界仅是 `DECK-008` 暴露的不可变 readiness 投影（receipt ID、workflow run ID、runtime lock ID/digest、`required_entries_ready`）；只校验投影绑定当前 run/lock 且 ready 为真，不解析 receipt entries、不重算物化/加载结论。

### Step 3: 实现幂等启动

```python
class WorkflowRunService:
    async def create_run(
        self,
        preflight_id: str,
        preflight_token: str,
        idempotency_key: str,
        source_voice_thread_id: Optional[str],
        actor_context: AuthenticatedActorContext
    ) -> WorkflowRun:
        """
        幂等创建 Workflow Run：
        1. 从认证上下文解析 workspace_id + actor_id；禁止信任请求体中的租户/actor。
        2. 开启事务并锁定 preflight/token 与幂等作用域；验证 token 签名、preflight_id、
           workspace/actor，以及 binding revision、input hash、Deck runtime snapshot、runtime lock
           等 claims。未映射的新 token 还必须满足当前未过期、passed、未消费；已映射 token
           的精确幂等重放按第 4 步处理，不因事后过期或 used 状态失去返回原 run 的能力。
        3. 计算 token digest 与 canonical semantic fingerprint。fingerprint 不包含 token 或
           preflight 记录 ID，至少覆盖 binding/release、workflow ref、input hash、runtime snapshot、
           runtime lock、plugin/version 和 source_voice_thread_id；语义相同的新 preflight 可判为重放。
        4. 同 (workspace_id, actor_id, idempotency_key)、同 fingerprint：在完成 token 真实性、
           actor/workspace/claims 校验后返回原 run。若是新的、当前有效且未消费 token，须在
           返回前将其原子映射/消费到原 run；已映射到该 run 的精确 token 重放不重新要求
           unused/未过期，但仍须匹配已保存的 digest、身份与 claims。
        5. 同 key 但 fingerprint 不同，或同 token 已映射到不同 key、actor、workspace、run
           或语义：fail closed，返回 409 IDEMPOTENCY_CONFLICT，不返回原 run 信息且不写新 run。
        6. 仅当 key 与 token 均未占用且 token 当前有效时，原子写入 workflow_runs、
           workflow_run_token_consumptions 映射和初始 transition（NULL → preflight），
           再按合法规则进入 queued。
        7. 任一步失败整体回滚；唯一约束竞态须重新进入上述判定矩阵，禁止先消费 token
           后无法幂等返回，也禁止先返回 run 再跳过 token/actor/workspace 校验。
        """
```

`preflight_token` 原文不得持久化、记录日志或回传；token digest 使用服务端密钥 HMAC/等价抗枚举摘要。`workflow_run_token_consumptions` 允许多个语义等价、已验证的 Preflight Token 映射到同一幂等 run，但每个 token digest 只能映射一次。幂等返回时，新 token 映射必须与返回判定同事务；首次创建时，run、token 映射和初始 transition 必须同事务。因此不会留下“已消费但无 run”或“已返回但 token 未绑定”的中间态。纯幂等返回不改变 run 状态、不得伪造 transition；只有首次创建或真实状态变化追加 transition。

### Step 4: 实现重试

```python
async def retry_run(
    self,
    workflow_run_id: str,
    actor: str
) -> WorkflowRun:
    """
    默认重试：
    1. 读取原 run 的来源字段（release、Deck runtime snapshot、runtime lock）
    2. 创建新 run，设置 retry_of_run_id = 原 run id
    3. 继承原 release、workflow ref、Deck runtime snapshot 和 runtime lock
    4. 新 run 走完整 preflight → run 流程

    若用户修改输入、选择其他 plugin/version、要求刷新 Deck runtime snapshot 或变更能力，
    属于新运行，不得伪装成同快照重试。
    """
```

### Step 5: 数据库表设计

在 `backend/database.py` 中追加：

```sql
CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,                    -- run_<uuid>
    workspace_id TEXT NOT NULL,             -- 来自认证 workspace 上下文；创建后不可变
    deck_plugin_id TEXT NOT NULL,
    deck_plugin_version TEXT NOT NULL,
    workflow_definition_ref TEXT NOT NULL,
    deck_runtime_snapshot_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'preflight',
    failed_step TEXT,
    error_code TEXT,
    retry_of_run_id TEXT,
    deck_plugin_manifest_hash TEXT NOT NULL,
    deck_plugin_binding_id TEXT NOT NULL,
    binding_revision INTEGER NOT NULL,
    runtime_plugin_lock_id TEXT NOT NULL,
    runtime_load_receipt_id TEXT,
    workflow_preflight_id TEXT NOT NULL,
    agent_session_id TEXT,
    source_voice_thread_id TEXT,
    idempotency_key TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    semantic_fingerprint TEXT NOT NULL,
    status_version INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (workflow_preflight_id) REFERENCES workflow_preflights(id),
    UNIQUE(workspace_id, created_by, idempotency_key)
);

-- 一次性 token 的原子消费/重放映射；原 token 永不落库。
CREATE TABLE IF NOT EXISTS workflow_run_token_consumptions (
    token_digest TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL,
    workflow_preflight_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    semantic_fingerprint TEXT NOT NULL,
    consumed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id),
    FOREIGN KEY (workflow_preflight_id) REFERENCES workflow_preflights(id)
);

-- DECK-007 的最小不可变 transition 存储；通用 events/outbox 不在本 task。
CREATE TABLE IF NOT EXISTS workflow_run_transitions (
    id TEXT PRIMARY KEY,                    -- wrt_<uuid>
    workflow_run_id TEXT NOT NULL,
    transition_seq INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    reason_code TEXT,
    failed_step TEXT,
    error_code TEXT,
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id),
    UNIQUE(workflow_run_id, transition_seq)
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_deck_plugin
    ON workflow_runs(deck_plugin_id, deck_plugin_version);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status
    ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_idempotency
    ON workflow_runs(workspace_id, created_by, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_retry
    ON workflow_runs(retry_of_run_id);

CREATE INDEX IF NOT EXISTS idx_workflow_run_token_consumptions_run
    ON workflow_run_token_consumptions(workflow_run_id);

CREATE INDEX IF NOT EXISTS idx_workflow_run_transitions_run
    ON workflow_run_transitions(workflow_run_id, transition_seq);

-- 通过数据库 guard/trigger（或当前数据库等价机制）拒绝 token consumption 与
-- transition 的 UPDATE/DELETE；二者只允许 INSERT。状态变化必须与
-- workflow_runs.status/status_version 更新处于同一事务。
```

### Step 6: 不可变性保证

- `workspace_id` 来自已认证 workspace 上下文，`created_by` 来自已认证 actor；二者与 `workflow_run_id`、幂等 key、semantic fingerprint 及所有来源/锁定字段创建后不可变
- token consumption 记录 append-only；每个 token digest 只能映射到一个 run/key/actor/workspace/fingerprint，语义相同的新 token 可在幂等返回前追加映射到原 run
- `runtime_load_receipt_id` 是唯一例外：创建时可为 `NULL`，只能在 receipt 驱动的 `queued → running` 事务中赋值一次，之后不可变
- 运行当前 `status`、`failed_step`、`error_code` 可以随合法状态流转更新；每次更新必须与 `status_version + 1` 及一条 append-only transition 原子提交
- `workflow_run_transitions` 是本 task 授权的最小必要历史存储：初始 `NULL → preflight` 与后续 old/new 状态、actor、reason/error、单调序号均不可更新或删除
- `DECK-013` 后续以该 transition 合同作为 `workflow.run.created` / `workflow.run.status_changed` 的审计输入，负责通用 `events` 表、event envelope、outbox/消息投递、去重、顺序与 SSE/WebSocket；本 task 不实现这些通用事件能力
- Deck binding、安装默认版本、Deck 当前运行配置的后续变化不得反写历史 run

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/workflow_run.py` | 新建 | Workflow Run、合法状态与最小 transition/readiness 合同 |
| `backend/services/workflow/run_service.py` | 新建 | Workflow Run 创建、幂等/token 原子判定、状态流转与重试服务 |
| `backend/database.py` | 修改 | 追加 `workflow_runs`、token consumption 与最小 append-only `workflow_run_transitions` 存储 |
| `backend/tests/test_workflow_run.py` | 新建 | Run、幂等/token、transition 与 receipt 状态守卫测试 |
| `docs/exec/exec_deck_007_backend_workflow-run.md` | 新建或增量更新 | 仅 `ExecTaskAgent` 回填本 task 唯一正式执行报告；非实现例外 |

## 6. 输入 / 输出说明

**输入**：
- `workflow_preflight_id` + `preflight_token`（来自 DECK-006）
- `idempotency_key`（客户端生成）
- `source_voice_thread_id`（可选）
- 已认证的 `workspace_id` + `actor_id` 上下文（服务端解析，不接受客户端覆盖）
- 状态流转时读取下游 `DECK-008` 产出的不可变 load receipt 就绪投影；单元测试使用 fake/stub，不实现 receipt 内部逻辑

**输出**：
- `WorkflowRun` 记录
- 服务端内部 append-only token consumption 映射（不得向 API 暴露 token/digest）
- append-only `WorkflowRunTransition` 最小历史记录
- 幂等冲突时返回 `409 IDEMPOTENCY_CONFLICT`

## 7. 依赖项

- **前置依赖**: `DECK-006`（Preflight）
- **下游依赖**: `DECK-008`, `DECK-009`, `DECK-013`, `DECK-015`
- 需要与 Deck runtime snapshot、ClaudeAgent session 紧密集成；只保存受控快照 ID 与脱敏摘要
- `DECK-008` 负责 reconcile/materialization/load receipt 的生成、存储与内部校验；本 task 仅冻结并单测 receipt 就绪投影驱动的 `queued → running` 守卫，真实 receipt 联调由 `DECK-008` 完成
- `DECK-013` 负责把本 task 的 append-only transition 投影为通用审计事件并完成投递/消费；不得反向要求本 task 新增通用事件实现路径

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 状态机流转（所有合法路径） |
| 单元测试 | 终态不可复活 |
| 单元测试 | `workspace_id` 由认证上下文派生且不可变；同 actor/key 在不同 workspace 不冲突，伪造 workspace 不生效 |
| 单元测试 | 幂等启动：同 workspace/actor/key、同语义在完整 token 绑定校验后返回原 run；新的等价有效 token 原子映射到原 run |
| 单元测试 | 幂等/token 冲突矩阵：同 key 不同语义，以及已消费 token 改用不同 key/actor/workspace/语义，均 fail closed 且不泄露原 run |
| 单元测试 | 原子失败注入：run、token 消费与初始 transition 任一写入失败全部回滚；重放仍可安全完成 |
| 单元测试 | 重试创建新 run，继承原来源 |
| 单元测试 | 改选 plugin/version 属于新运行 |
| 单元测试 | 并发创建（同一幂等作用域）仅产生一个 run、一次 token 消费和一条初始 transition |
| 单元测试 | 来源字段不可变性 |
| 单元测试 | 每次状态变化原子追加 transition、序号单调；直接 UPDATE/DELETE transition 被拒绝 |
| 单元测试 | fake/stub load receipt 匹配时允许 `queued → running` 并一次性写 receipt ID；缺失/错 run/错 lock/digest/required 失败时拒绝 |
| 集成测试 | 本 task 四个实现路径内的数据库幂等、token、run/transition 原子生命周期；真实 reconcile/materialization/load receipt 联调留给 `DECK-008` |

## 9. 完成标志

- [ ] Run 模型完整，保留 SUO-198 全部字段并新增设计稿 §11.1 字段
- [ ] `workspace_id` 从认证上下文派生、持久化且创建后不可变；唯一范围严格为 `workspace_id + created_by + idempotency_key`
- [ ] canonical semantic fingerprint 仅由服务端对冻结运行语义计算；不得包含 token/preflight 记录 ID，也不得接受客户端提交
- [ ] 状态机只允许规范流转；终态不可复活
- [ ] 启动请求携带 `idempotency_key`；同 workspace/actor/key、同 canonical 语义在完整 token 绑定校验后返回原 run，新的等价有效 token 在返回前原子映射到原 run
- [ ] 同 key 不同语义，或已消费 token 改用不同 key/actor/workspace/语义，统一 fail closed 且不新增/泄露 run
- [ ] 首次创建或幂等返回、token consumption 与必要 transition 原子提交；并发竞态只产生一个 run，失败不存在已消费 token 的孤儿状态
- [ ] 重试创建新 run，设置 `retry_of_run_id`，继承原 release/Deck runtime snapshot/runtime lock
- [ ] 改选插件、升级或 Deck 运行配置变更属于新运行，不得伪装成重试
- [ ] 运行来源、runtime lock、Deck runtime snapshot 创建后不可变；load receipt ID 仅允许从 `NULL` 一次性绑定后不可变
- [ ] 每次创建/状态变化与 append-only transition 原子提交；transition 不可更新/删除，可供 `DECK-013` 后续审计消费
- [ ] `queued → running` 的 load receipt 守卫可用 fake/stub 验证；未实现 reconcile/materialization/load receipt 内部逻辑
- [ ] 单元/集成测试覆盖 workspace 作用域、幂等/token 矩阵、原子回滚、状态流转、transition、重试、并发与 receipt 守卫

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 状态机非法流转导致数据不一致 | 高 | 所有状态变更通过服务方法，数据库 check 约束 |
| 幂等 key 冲突处理不当 | 高 | 唯一约束 + 服务端完整校验 |
| token 先消费或 run 先返回造成不可恢复重试/绑定绕过 | 高 | 单事务判定矩阵 + append-only token consumption 唯一映射 + 失败注入/并发测试 |
| 当前状态与审计历史分叉 | 高 | 状态、版本与 append-only transition 原子提交；数据库拒绝 transition 更新/删除 |
| 重试继承来源时参数被篡改 | 中 | 来源字段从原 run 复制，不接收客户端提交 |
| 并发创建导致重复 run | 中 | 数据库唯一约束 `UNIQUE(workspace_id, created_by, idempotency_key)` |
| 下游 receipt 合同被误实现在本 task | 中 | 只定义读取/就绪守卫与 fake 测试；真实 receipt 逻辑由 `DECK-008` 实现 |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/models/workflow_run.py`（仅新增 Workflow Run、合法状态与最小 transition 合同）
- `backend/services/workflow/run_service.py`（仅新增创建、workspace/actor + token 幂等原子判定、状态/transition 原子流转、receipt 就绪守卫与重试服务）
- `backend/database.py`（仅增量追加 `workflow_runs`、`workflow_run_token_consumptions`、最小 `workflow_run_transitions`、必要索引/唯一约束及 append-only guard；禁止新增通用 `events`/outbox 表）
- `backend/tests/test_workflow_run.py`（仅新增本 task 的 run、幂等/token、transition、重试、并发与 fake receipt 守卫测试）

上述四个实现路径与 §5 前四行一致；未列出的实现文件默认不授权。§5 第五行仅为下述正式执行报告例外。

唯一非实现写入例外：`ExecTaskAgent` 可新建或增量更新 `docs/exec/exec_deck_007_backend_workflow-run.md`，且只能回填本 task 的正式执行差异、测试证据、边界与风险。该例外不授权实现代码、模板、设计、Issue、Task 或 Stage 变更；其他 `docs/exec/` 文件仍禁止修改。

### 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`
- `docs/exec/`，但上文精确列出的 `docs/exec/exec_deck_007_backend_workflow-run.md` 正式报告例外除外
- `frontend/`、ClaudeAgent session/runtime 实现与 Deck Plugin binding/Preflight 服务
- 除上述 4 个路径以外的任何实现、测试、依赖锁或部署配置
- `backend/database.py` 中与 `workflow_runs` / `workflow_run_token_consumptions` / `workflow_run_transitions` 无关的既有表或初始化逻辑，以及通用 `events`/outbox 表
- 借本 task 改绑历史来源、复用终态 run、实现 Reconcile/Materialization/Load Receipt/Session、通用事件投递/消费，或扩大客户端可提交来源字段

## 12. 命名隔离声明

- Run 模型保留 SUO-198 字段不变
- Deck/Runtime/Workflow 领域字段继续使用 `deck_plugin_*`、`runtime_plugin_*`、`workflow_*` 前缀；租户、幂等与状态版本技术字段固定为 `workspace_id`、`idempotency_key`、`semantic_fingerprint`、`status_version`
- `agent_session_id` 为 ClaudeAgent 会话标识

## 13. 未决决策引用

- `DECK-019`: 安全撤销是否强制终止活动 run —— 影响 `CANCELLED` 状态的处理
- `DECK-020`: Voice chat 到 run session 的可见 UX —— 影响 `source_voice_thread_id` 的使用
