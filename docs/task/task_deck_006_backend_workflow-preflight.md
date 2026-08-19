# task_deck_006_backend_workflow-preflight

## 1. 任务标题

Story Workspace Workflow Preflight

## 2. 关联 Issue

- **Issue ID**: `DECK-006`
- **Issue 标题**: Story Workspace Workflow Preflight
- **类型**: backend
- **优先级**: P0
- **标签**: `story-workspace`, `preflight`, `execution`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §10.1, §10.2
  - `docs/design/deck/deck-integration-delta.md` §5.1, §7.2
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-006

## 3. 任务目标

实现 Story Workspace 的权威 Workflow Preflight。按固定顺序执行 preflight 检查，通过 Deck 生成或复用不可变 `DeckRuntimeSnapshot`，验证 runtime lock 的物化状态，签发一次性 preflight token。只有未过期且与当前 binding revision、输入 hash 一致的 preflight 才可创建 Workflow Run。

## 4. 实现步骤

### Step 1: 定义 Preflight 数据模型

在 `backend/models/workflow_preflight.py`（新建）中定义：

```python
class WorkflowPreflight(BaseModel):
    workflow_preflight_id: str      # pf_<uuid>
    deck_id: str
    binding_revision: int
    deck_plugin_id: str
    deck_plugin_version: str
    runtime_plugin_lock_id: str
    deck_runtime_profile_id: str
    deck_runtime_snapshot_id: Optional[str]
    input_hash: str
    status: PreflightStatus          # checking | passed | failed | expired
    error_code: Optional[str]
    failed_check: Optional[str]
    expires_at: datetime
    preflight_token: Optional[str]   # opaque-short-lived-token
    created_by: str
    created_at: datetime

class PreflightStatus(str, Enum):
    CHECKING = "checking"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"
```

### Step 2: 实现 8 步 Preflight 检查链

在 `backend/services/workflow/preflight_service.py`（新建）中实现：

```python
class PreflightService:
    async def execute_preflight(
        self,
        deck_id: str,
        binding_revision: int,
        input_data: dict,
        actor: str
    ) -> WorkflowPreflight:
        """
        按固定顺序执行 preflight：
        1. 身份、workspace、Deck 使用权限
        2. binding revision 与精确 release 可用性
        3. manifest/hash、workflow definition、输入/输出 schema
        4. host、ClaudeAgent、Claude Code、Deck runtime contract 兼容性
        5. 能力交集与来源策略
        6. 通过 Deck 创建或复用不可变 deck_runtime_snapshot_id
        7. 验证 runtime lock 的 declared/materialized/digest/load smoke
        8. 计算 input hash、过期时间并签发 preflight_token
        """
```

### Step 3: Deck Runtime Snapshot 创建/复用

```python
async def _create_or_reuse_deck_runtime_snapshot(
    self,
    deck_id: str,
    deck_runtime_profile_id: str,
    deck_runtime_snapshot_contract: str
) -> str:
    """
    通过单一 Deck API owner 按 runtime contract 创建或复用不可变快照。
    Story Workspace 只保存 deck_runtime_snapshot_id 与脱敏摘要，
    不复制 prompt、secret 或完整高敏配置。
    """
```

`DeckRuntimeSnapshot` 由 Deck 权威存储。`workflow_preflights` 只持久化受控 `deck_runtime_snapshot_id`、必要的脱敏摘要 hash 和版本引用；不得在 Ink-Dream 创建第二份配置快照表或独立配置 service/API namespace。

### Step 4: Runtime Lock 物化验证

```python
async def _verify_runtime_materialization(
    self,
    runtime_plugin_lock_id: str
) -> MaterializationResult:
    """
    验证 runtime lock 中每个 required 插件的物化状态：
    - declaration_status = declared
    - materialization_status = materialized
    - activation_status = loadable 或 loaded
    - artifact_digest 匹配
    """
```

### Step 5: Preflight Token 签发

```python
def _issue_preflight_token(
    self,
    preflight_id: str,
    binding_revision: int,
    input_hash: str,
    deck_runtime_snapshot_id: str,
    runtime_lock_id: str
) -> str:
    """
    签发一次性/有限次 token，绑定：
    - binding revision
    - input hash
    - Deck runtime snapshot
    - runtime lock
    有效期默认 5 分钟（可配置）。
    """
```

### Step 6: 与 SUO-198 状态语义对齐

- selection/execution 的大部分校验存在于独立 `WorkflowPreflight`
- 失败时不创建 ClaudeAgent session
- 成功提交时，Workflow Run 可以先以 `status=preflight` 原子持久化
- UI 的普通校验失败不伪造已启动 Agent 的运行记录

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/workflow_preflight.py` | 新建 | Preflight 模型 |
| `backend/services/workflow/preflight_service.py` | 新建 | Preflight 服务 |
| `backend/database.py` | 修改 | 仅追加 `workflow_preflights` 表及其 Deck snapshot 引用字段 |
| `backend/tests/test_workflow_preflight.py` | 新建 | Preflight 单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `deck_id` + `binding_revision`
- 工作流输入数据（用于计算 input hash）
- 用户身份/workspace 上下文

**输出**：
- `WorkflowPreflight` 记录
- `preflight_token`（通过时签发）
- 失败时的结构化错误码

## 7. 依赖项

- **前置依赖**: `DECK-002`（runtime lock）, `DECK-004`（兼容性判定）
- **下游依赖**: `DECK-007`（Workflow Run 创建）
- 需要 Deck 提供不可变运行快照生成/读取能力；对外保持单一 Deck owner/API namespace
- 需要 runtime materialization 状态查询

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | 8 步 preflight 各阶段失败（每步单独失败） |
| 单元测试 | token 签发与验证（绑定关系、过期） |
| 单元测试 | Deck runtime snapshot 创建/复用调用（幂等）以及本地不复制敏感配置 |
| 单元测试 | runtime lock 物化验证（declared/materialized/digest） |
| 单元测试 | 并发 preflight（同一 deck + binding revision） |
| 单元测试 | preflight 失败不创建伪运行记录 |
| 集成测试 | 端到端 preflight（通过/各种失败场景） |

## 9. 完成标志

- [ ] Preflight 顺序固定，失败即停止后续阶段
- [ ] 8 步 preflight 覆盖设计稿 §10.2 所有检查项
- [ ] 通过 Deck 创建或复用不可变 `deck_runtime_snapshot_id`
- [ ] 验证 runtime lock 的 declared/materialized/digest/load smoke
- [ ] 签发一次性/有限次 `preflight_token`，绑定 binding revision、input hash、Deck runtime snapshot 和 runtime lock
- [ ] preflight 失败不启动 ClaudeAgent；不创建伪运行记录
- [ ] 单元测试覆盖各 preflight 阶段失败、token 过期、并发 preflight

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| preflight 与 selection validation 逻辑重复 | 中 | selection validation 只做快速静态检查；preflight 做权威完整检查 |
| Deck runtime snapshot 创建失败阻塞所有运行 | 高 | 返回 `DECK_RUNTIME_CONFIG_INVALID` 或 `DECK_RUNTIME_CONFIG_UNAVAILABLE`，保留输入并给出 Deck owner 修复/重试指引 |
| token 泄露导致重放攻击 | 中 | token 一次性使用 + 短有效期 + 绑定所有关键参数 |
| 并发 preflight 导致重复 Deck runtime snapshot | 低 | Deck 端幂等创建：相同 profile/config/version/policy 输入复用已有 snapshot |

## 11. 允许修改范围与禁止修改范围

### 允许修改范围

- `backend/models/workflow_preflight.py`（仅新增 Preflight 模型）
- `backend/services/workflow/preflight_service.py`（仅新增固定顺序的 Preflight 服务与 token 校验）
- `backend/database.py`（仅增量追加 `workflow_preflights` 表、`deck_runtime_snapshot_id` 引用及其幂等初始化）
- `backend/tests/test_workflow_preflight.py`（仅新增本 task 的单元测试）

以上闭集与 §5“涉及文件路径”一致；未列出的文件默认不授权。

### 禁止修改范围

- `docs/design/`、`docs/issue/`、`docs/task/`、`docs/stage/`、`docs/exec/`
- `frontend/`、ClaudeAgent session/runtime 实现与 Deck Plugin 发布/安装服务
- 除上述 4 个路径以外的任何实现、测试、依赖锁或部署配置
- `backend/database.py` 中与本 task 两张表无关的既有表或初始化逻辑
- 绕过固定检查顺序、在 Preflight 失败后启动 Agent，或借本 task 改写 Workflow Run 状态机

## 12. 命名隔离声明

- preflight 对象使用 `workflow_preflight_*` 前缀
- Deck 运行快照统一使用 `deck_runtime_snapshot_*` 前缀；禁止本地复制 Deck 高敏配置
- 与 `deck_plugin_*`、`runtime_plugin_*` 保持隔离

## 13. 未决决策引用

- `DECK-018`: 多节点/临时 runtime 分发策略 —— 影响 runtime lock 物化验证的判定范围
