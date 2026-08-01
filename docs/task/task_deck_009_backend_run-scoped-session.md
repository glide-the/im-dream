# task_deck_009_backend_run-scoped-session

## 1. 任务标题

ClaudeAgent Run-Scoped Session 与远程交互限制

## 2. 关联 Issue

- **Issue ID**: `DECK-009`
- **Issue 标题**: ClaudeAgent Run-Scoped Session 与远程交互限制
- **类型**: backend
- **优先级**: P0
- **标签**: `claude-agent`, `session`, `remote-interaction`
- **来源设计稿**:
  - `docs/design/deck-plugin-voice-ink-dream-integration.md` §7.4, §7.5, §8.2
  - `docs/design/deck-claude-agent.md`
- **Issue 清单**: `docs/issue/ISSUES_deck-plugin-voice-ink-dream-integration.md` §3 DECK-009

## 3. 任务目标

实现 ClaudeAgent 的 run-scoped session 管理和远程交互限制。为 Workflow Run 生成隔离的 run settings，会话启动时同步 reconcile 并校验加载结果。会话内插件集合固定到运行结束。

## 4. 实现步骤

### Step 1: 定义 Run-Scoped Session 模型

在 `backend/models/agent_session.py`（新建或扩展）中定义：

```python
class AgentSession(BaseModel):
    agent_session_id: str           # as_<uuid>
    workflow_run_id: str
    runtime_environment_id: str
    settings_json: str              -- 隔离的 run settings（仅含锁定插件）
    status: SessionStatus           -- creating | active | paused | terminated
    created_at: datetime
    started_at: Optional[datetime]
    terminated_at: Optional[datetime]

class SessionStatus(str, Enum):
    CREATING = "creating"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
```

### Step 2: 实现 Session 创建

在 `backend/services/claude_agent/session_manager.py`（新建或扩展）中实现：

```python
class AgentSessionManager:
    async def create_run_session(
        self,
        workflow_run: WorkflowRun,
        desk_snapshot: DeskConfigSnapshot,
        runtime_lock: DeckRuntimePluginLock
    ) -> AgentSession:
        """
        为 Workflow Run 创建隔离的 run-scoped session：
        1. 读取已冻结的 runtime_plugin_lock_id 和 desk_config_snapshot_id
        2. 生成隔离的 run settings：仅包含锁定插件、批准能力和 marketplace 引用
        3. 执行 headless reconcile（同步模式，完成前不得发送第一条 query）
        4. 校验加载结果并生成 runtime_load_receipt_id
        5. required 插件全部 loaded 后创建 agent_session_id
        6. Workflow Run 从 queued 进入 running
        """
```

Run settings 格式：
```json
{
  "enabledPlugins": {
    "ink-dream-tools@voice-decks": true
  },
  "extraKnownMarketplaces": {
    "voice-decks": { ... }
  },
  "pluginPolicy": {
    "allowedCapabilities": ["story.context.read", "story.result.produce"]
  }
}
```

### Step 3: 实现加载回执校验

```python
async def _verify_load_receipt(
    self,
    runtime_lock: DeckRuntimePluginLock,
    receipt: RuntimeLoadReceipt
) -> LoadVerificationResult:
    """
    逐项校验：
    - 每个 claude_code_plugin_id 存在
    - resolved_version 与 lock 一致
    - artifact_digest 与 lock 一致
    - required 插件的 load_status = loaded
    - loaded_capabilities 覆盖 lock 中的 capability_bindings
    """
```

### Step 4: 实现热刷新限制

```python
class RemoteInteractionGuard:
    async def guard_reload(
        self,
        workflow_run_id: str,
        proposed_plugins: list[str]
    ) -> GuardResult:
        """
        活跃 Workflow Run 禁止调用 apply_flag_settings/reload_plugins 改变能力集合。
        - 检查 workflow_run.status 是否为 running/awaiting_review/continuing
        - 若是，拒绝并返回 RUNTIME_PLUGIN_RELOAD_UNSUPPORTED
        - 已物化插件的空闲管理会话可热刷新以做 smoke
        """
```

### Step 5: Voice Thread 来源记录

```python
# 在 WorkflowRun 创建时：
if source_voice_thread_id:
    run.source_voice_thread_id = source_voice_thread_id
    # 但不直接复用为 agent_session_id
    # 原因：持久聊天线程可能已加载不同插件或旧 settings
```

### Step 6: 会话生命周期管理

```python
async def terminate_session(
    self,
    agent_session_id: str,
    reason: str
) -> None:
    """
    会话终止：
    - 正常完成：run → completed
    - 用户取消：run → cancelled
    - 安全撤销：run → cancelled，记录 SECURITY_REVOCATION
    - 错误：run → failed
    """
```

## 5. 涉及文件路径

| 路径 | 动作 | 说明 |
|---|---|---|
| `backend/models/agent_session.py` | 新建/修改 | Agent Session 模型 |
| `backend/services/claude_agent/session_manager.py` | 新建/修改 | Session 管理器 |
| `backend/services/claude_agent/remote_interaction_guard.py` | 新建 | 远程交互限制守卫 |
| `backend/tests/test_agent_session.py` | 新建 | Session 管理单元测试 |

## 6. 输入 / 输出说明

**输入**：
- `WorkflowRun`（来自 DECK-007）
- `DeskConfigSnapshot`（来自 DECK-006）
- `DeckRuntimePluginLock`（来自 DECK-002）
- `source_voice_thread_id`（可选）

**输出**：
- `AgentSession` 记录
- `RuntimeLoadReceipt`（来自 DECK-008）
- 会话状态事件

## 7. 依赖项

- **前置依赖**: `DECK-008`（Reconcile 与 Load Receipt）
- **下游依赖**: `DECK-013`（事件审计）
- 需要与现有 Claude Agent SSE 服务集成
- 需要与 `deck-claude-agent.md` 的 Voice chat/thread/Memory 能力协调

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | Run-scoped session 创建时仅包含锁定插件和批准能力 |
| 单元测试 | 第一条 query 前完成同步 reconcile 与 load receipt 校验 |
| 单元测试 | 会话内插件集合固定 |
| 单元测试 | 活跃 Workflow Run 禁止 apply_flag_settings/reload_plugins |
| 单元测试 | 已物化插件的空闲管理会话可热刷新 |
| 单元测试 | voice.thread_id 记录为 source_voice_thread_id，不直接复用 |
| 单元测试 | 配置/版本变更只为下一次运行创建新会话 |
| 集成测试 | 端到端 session 生命周期 |

## 9. 完成标志

- [ ] Run-scoped session 创建时仅包含锁定插件和批准能力
- [ ] 第一条 query 前完成同步 reconcile 与 load receipt 校验
- [ ] 会话内插件集合固定，配置/版本变更只为下一次运行创建新会话
- [ ] 活跃 Workflow Run 禁止 `apply_flag_settings`/`reload_plugins`
- [ ] 已物化插件的空闲管理会话可热刷新以做 smoke，结果不自动授权生产运行
- [ ] `voice.thread_id` 记录为 `source_voice_thread_id`，不直接复用
- [ ] 单元测试覆盖 session 隔离、热刷新限制、Voice thread 来源记录

## 10. 风险提示

| 风险 | 等级 | 缓解 |
|---|---|---|
| 现有 Claude Agent SSE 服务不兼容 run-scoped settings | 高 | 与现有服务协调；增量扩展而非替换 |
| session 创建超时导致 run 长时间 queued | 中 | 可配置超时；失败转 failed 并记录 |
| Voice thread 与 run session 体验割裂 | 中 | UI 保留来源链接；`DECK-020` 决策单确认文案 |
| 热刷新限制被绕过 | 高 | 服务端强制检查；代码审查 + 测试覆盖 |

## 11. 命名隔离声明

- Session 使用 `agent_session_id` 标识
- Voice thread 使用 `source_voice_thread_id` 标识（可选来源引用）
- 禁止混用两者

## 12. 未决决策引用

- `DECK-018`: 多节点/临时 runtime 分发策略 —— 影响 session 的 runtime_environment_id 分配
- `DECK-019`: 安全撤销是否强制终止活动 run —— 影响 session 终止策略
- `DECK-020`: Voice chat 到 run session 的可见 UX —— 影响 source_voice_thread_id 的展示方式
