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

实现 Workflow Run 的创建、状态管理和幂等重试。保留 SUO-198 全部字段并新增 Deck Plugin 相关字段。实现规范状态机、幂等启动和重试语义。

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
    idempotency_key: str
    input_hash: str

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
- `queued → running` 需要 `runtime_load_receipt` 全部 required 项成功
- `running → output_validating → pending_review` 需要规范化结果完整校验并原子持久化
- `pending_review → confirmed → continuing/completed` 由用户确认触发；`pending_review → rejected` 终止当前 run，重新生成必须新建 run
- `pending_review` 是唯一 API 审阅态；`awaiting review` 仅可作为 UI 文案
- 任一终态不得恢复为非终态；重试创建新 run

### Step 3: 实现幂等启动

```python
class WorkflowRunService:
    async def create_run(
        self,
        preflight_id: str,
        preflight_token: str,
        idempotency_key: str,
        source_voice_thread_id: Optional[str],
        actor: str
    ) -> WorkflowRun:
        """
        幂等创建 Workflow Run：
        1. 验证 preflight_token（未过期、未使用、绑定参数匹配）
        2. 检查 idempotency_key（workspace_id + actor_id + key）
        3. 同 key、同 binding_revision、同 input_hash → 返回原 run
        4. 同 key 不同语义 → 409 IDEMPOTENCY_CONFLICT
        5. 原子创建 run 记录，状态 = preflight → queued
        """
```

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
    created_by TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    FOREIGN KEY (workflow_preflight_id) REFERENCES workflow_preflights(id),
    UNIQUE(workspace_id, created_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_deck_plugin
    ON workflow_runs(deck_plugin_id, deck_plugin_version);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status
    ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_idempotency
    ON workflow_runs(workspace_id, created_by, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_retry
    ON workflow_runs(retry_of_run_id);
```

### Step 6: 不可变性保证

- `workflow_run_id` 及所有来源/锁定字段创建后不可变
- 运行当前 `status`、`failed_step`、`error_code` 可以随合法状态流转更新
- 每次变化必须追加不可变事件
- Deck binding、安装默认版本、Deck 当前运行配置的后续变化不得反写历史 run

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/workflow_run.py` | 新建 | Workflow Run 模型 |
| `backend/services/workflow/run_service.py` | 新建 | Workflow Run 服务 |
| `backend/database.py` | 修改 | 追加 `workflow_runs` 表 |
| `backend/tests/test_workflow_run.py` | 新建 | Run 服务单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `workflow_preflight_id` + `preflight_token`（来自 DECK-006）
- `idempotency_key`（客户端生成）
- `source_voice_thread_id`（可选）

**输出**：
- `WorkflowRun` 记录
- 幂等冲突时返回 `409 IDEMPOTENCY_CONFLICT`

## 7. 依赖项

- **前置依赖**: `DECK-006`（Preflight）
- **下游依赖**: `DECK-008`, `DECK-009`, `DECK-013`, `DECK-015`
- 需要与 Deck runtime snapshot、ClaudeAgent session 紧密集成；只保存受控快照 ID 与脱敏摘要

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 状态机流转（所有合法路径） |
| 单元测试 | 终态不可复活 |
| 单元测试 | 幂等启动（同 key 返回原 run） |
| 单元测试 | 幂等冲突（同 key 不同语义返回 409） |
| 单元测试 | 重试创建新 run，继承原来源 |
| 单元测试 | 改选 plugin/version 属于新运行 |
| 单元测试 | 并发创建（同一 idempotency_key） |
| 单元测试 | 来源字段不可变性 |
| 集成测试 | 端到端 run 生命周期 |

## 9. 完成标志

- [ ] Run 模型完整，保留 SUO-198 全部字段并新增设计稿 §11.1 字段
- [ ] 状态机只允许规范流转；终态不可复活
- [ ] 启动请求携带 `idempotency_key`；同 key、同 binding、同 input 返回原 run
- [ ] 同 key 不同语义返回 `409 IDEMPOTENCY_CONFLICT`
- [ ] 重试创建新 run，设置 `retry_of_run_id`，继承原 release/Deck runtime snapshot/runtime lock
- [ ] 改选插件、升级或 Deck 运行配置变更属于新运行，不得伪装成重试
- [ ] 运行来源、runtime lock/load receipt、Deck runtime snapshot 创建后不可变
- [ ] 单元测试覆盖状态流转、幂等启动、重试、并发创建

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 状态机非法流转导致数据不一致 | 高 | 所有状态变更通过服务方法，数据库 check 约束 |
| 幂等 key 冲突处理不当 | 高 | 唯一约束 + 服务端完整校验 |
| 重试继承来源时参数被篡改 | 中 | 来源字段从原 run 复制，不接收客户端提交 |
| 并发创建导致重复 run | 中 | 数据库唯一约束 `UNIQUE(workspace_id, created_by, idempotency_key)` |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/models/workflow_run.py`（仅新增 Workflow Run 模型与合法状态定义）
- `backend/services/workflow/run_service.py`（仅新增创建、状态流转、幂等与重试服务）
- `backend/database.py`（仅增量追加 `workflow_runs` 表及其幂等初始化）
- `backend/tests/test_workflow_run.py`（仅新增本 task 的单元测试）

以上闭集与 §5“涉及文件路径”一致；未列出的文件默认不授权。

### 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`
- `frontend/`、ClaudeAgent session/runtime 实现与 Deck Plugin binding/Preflight 服务
- 除上述 4 个路径以外的任何实现、测试、依赖锁或部署配置
- `backend/database.py` 中与 `workflow_runs` 无关的既有表或初始化逻辑
- 借本 task 改绑历史来源、复用终态 run、实现 Reconcile/Session 或扩大客户端可提交来源字段

## 12. 命名隔离声明

- Run 模型保留 SUO-198 字段不变
- 新增字段使用 `deck_plugin_*`、`runtime_plugin_*`、`workflow_*` 前缀
- `agent_session_id` 为 ClaudeAgent 会话标识

## 13. 未决决策引用

- `DECK-019`: 安全撤销是否强制终止活动 run —— 影响 `CANCELLED` 状态的处理
- `DECK-020`: Voice chat 到 run session 的可见 UX —— 影响 `source_voice_thread_id` 的使用
