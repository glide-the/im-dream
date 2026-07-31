# task_204_backend_story-workspace-agent-integration

## 1. 任务标题

Story Workspace Agent 产出数据接收与存储集成

## 2. 关联 Issue

- **Issue ID**: `SUO-201-BE-004`
- **Issue 标题**: Agent 产出数据接收与存储集成
- **类型**: `backend`
- **优先级**: P0
- **标签**: `agent`, `integration`, `sse`
- **来源设计稿**:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §5.1–5.5（数据表结构）
  - `docs/design/story-workspace/story-workspace-layout-design.md` §6.1（API 路由设计）
  - `docs/design/story-workspace/story-workspace-layout-design.md` §10.2（与 claude-agent 服务的集成）
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-007`, `DEC-008`（核心工作流、用户不手动创建）
  - `docs/CLAUDE.md` §Thread Lifecycle
- **Issue 清单**: `docs/issue/ISSUES_story-workspace.md` §3 Issue 明细

## 3. 任务目标

实现 `claude-agent` 服务与 `story-workspace` 数据表的集成通道：当 Agent 根据用户指令生成剧本、角色、场景后，将结构化数据安全地存入 story-workspace 表，并标记为 `review_status='pending'`、`agent_generated=true`，同时关联到对应的 Chat thread。Dashboard、故事/角色/场景列表随后可正确展示「待审阅」项。

**核心约束**：
- 不破坏现有 Chat / Deck 功能；Agent 集成是新增逻辑，不是替换。
- 数据写入必须幂等：同一 Agent 会话重复生成时，避免产生重复故事（以 `agent_session_id` + `title` 为去重键）。
- Agent 产出格式不固定，需定义最小数据契约（至少包含 `title` + 内容字段）。
- 错误处理：Agent 生成失败时记录日志，不阻塞用户现有操作。
- 项目使用 SQLite，所有写入通过 `database.py` 的 `get_db()` 连接完成。
- 所有业务标识使用 `story-workspace` 前缀（DEC-004）。

## 4. 实现步骤

### Step 1: 定义 Agent 产出最小数据契约

在 `backend/services/story-workspace/agent_integration.py` 中定义 Pydantic 模型，作为 Agent 产出内容的接收合同：

```python
class AgentStoryPayload(BaseModel):
    title: str
    description: Optional[str] = None
    type: Literal["short", "long", "script", "outline"] = "short"
    content: Optional[str] = None
    characters: list[AgentCharacterPayload] = []
    scenes: list[AgentScenePayload] = []

class AgentCharacterPayload(BaseModel):
    name: str
    identity: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    catchphrase: Optional[str] = None
    tags: list[str] = []

class AgentScenePayload(BaseModel):
    name: str
    description: Optional[str] = None
    order_index: int = 0
```

- 字段为最小必需集；Agent 可额外返回字段，但多余字段应被忽略或记录为警告。
- `title` / `name` 必填；缺失时整条记录应被拒绝并记录错误。
- 本契约需与 `SUO-201-SH-002` 产出的 `AgentStoryOutput` 类型对齐。

### Step 2: 创建内部接收服务

新建 `backend/services/story-workspace/agent_integration.py`：

```python
def store_agent_story_output(
    db: sqlite3.Connection,
    user_id: int,
    workspace_id: str,
    agent_session_id: str,
    payload: AgentStoryPayload,
) -> dict:
    """Persist one Agent-generated story bundle into story-workspace tables."""
```

实现逻辑：
1. 在事务中执行。
2. 生成 `story_id`（UUID v4）与 `identifier`（如 `story-{short_uuid}`）。
3. 先检查去重：
   ```sql
   SELECT id FROM story_workspace_stories
   WHERE agent_session_id = ? AND title = ? AND author_id = ?
   ```
   若已存在，则更新现有记录（视为重新生成）而非新建。
4. 插入 / 更新 `story_workspace_stories`。
5. 对每个角色：
   - 检查同一 `agent_session_id` + `name` 是否已存在，存在则更新，否则插入。
   - 写入 `story_workspace_characters`。
6. 对每个场景：
   - 写入 `story_workspace_scenes`。
7. 建立 `story_workspace_story_characters` 与 `story_workspace_scene_characters` 关联。
8. 更新冗余计数：`story_workspace_stories.character_count`、`scene_count`；`story_workspace_characters.story_count`；`story_workspace_scenes.character_count`。
9. 返回包含 `story_id`、`character_ids`、`scene_ids` 的结果字典。

### Step 3: 提供内部 REST 接收端点

在 `backend/routers/story-workspace.py` 中新增内部端点（仅由 claude-agent 服务调用，不建议前端直接调用）：

```python
@router.post("/api/story-workspace/internal/agent-output")
async def receive_agent_story_output(
    body: AgentStoryPayload,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
):
    """Receive Agent-generated story bundle and persist it."""
```

- 复用全局 Auth 中间件，确保 `user_id` 有效。
- 自动获取或创建当前用户的默认 `workspace_id`。
- `agent_session_id` 从请求 Header `X-Agent-Session-Id` 读取；缺失时返回 400。
- 调用 `store_agent_story_output()` 完成写入。
- 响应格式：
  ```json
  {
    "story_id": "story-uuid",
    "review_status": "pending",
    "character_ids": ["char-uuid-1", "char-uuid-2"],
    "scene_ids": ["scene-uuid-1", "scene-uuid-2"]
  }
  ```

### Step 4: 在 claude-agent 服务中调用集成端点

修改 `backend/claude_agent/service.py` 或 `backend/routers/claude_agent.py`：

- 在 Agent SSE 流处理中识别「生成剧本」类指令（简单关键字匹配或工具调用）。
- 当检测到 Agent 生成故事内容时，在流结束后（`message-final` 或 `finish`）调用内部 HTTP 客户端：
  ```python
  requests.post(
      "http://localhost:8000/api/story-workspace/internal/agent-output",
      json=parsed_payload,
      headers={"X-Agent-Session-Id": thread_id},
      timeout=30,
  )
  ```
- **推荐**：优先采用服务内函数调用（直接 import `store_agent_story_output`）而非 HTTP 自调用，以减少延迟和失败面；若架构要求解耦，再使用内部 HTTP。
- 记录调用结果与错误日志；错误不影响 SSE 流向用户返回的正常消息。

### Step 5: 错误处理与日志

```python
class AgentIntegrationError(Exception):
    """Raised when Agent output cannot be persisted."""
```

- JSON 解析失败：记录 `logger.warning`。
- 最小契约校验失败：记录具体字段。
- 数据库写入失败：记录异常并回滚事务；向 claude-agent 调用方返回 422，但不阻塞用户 Chat 体验。
- 添加 metrics / counter（可选）：`agent_story_stored_total`、`agent_story_store_failed_total`。

### Step 6: 幂等性与重新生成

- 去重键：`agent_session_id` + `title`（同一 Chat 线程内同标题视为同一故事）。
- 重新生成时：更新现有故事、角色的字段，删除旧关联并重建新关联。
- 保留 `created_at`，更新 `updated_at`。

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/services/story-workspace/agent_integration.py` | **新文件**：Agent 产出接收、解析、持久化服务 |
| `backend/routers/story-workspace.py` | 追加 `/api/story-workspace/internal/agent-output` 内部接收端点 |
| `backend/claude_agent/service.py` | 在 Agent SSE 流收尾处调用集成服务 |
| `backend/claude_agent/context_builder.py` | 可选：在系统提示中增加「生成剧本」输出格式指导 |
| `backend/database.py` | 复用 `get_db()` 连接 |
| `backend/tests/test_story_workspace_agent_integration.py` | **新文件**：集成测试 |

## 6. 输入 / 输出说明

### 输入

- Agent 生成的剧本结构化数据（JSON），至少包含 `title`。
- 当前用户 `user_id`（从 Auth 中间件获取）。
- Chat thread ID，作为 `agent_session_id`。
- 现有数据表：`story_workspace_workspaces`, `story_workspace_stories`, `story_workspace_characters`, `story_workspace_scenes`, `story_workspace_story_characters`, `story_workspace_scene_characters`。

### 输出

- `backend/services/story-workspace/agent_integration.py`：数据解析、校验、持久化函数。
- `backend/routers/story-workspace.py`：新增内部接收端点。
- 数据库记录：标记为 `agent_generated=true`、`review_status='pending'` 的故事、角色、场景及关联。
- Dashboard 可消费的「待审阅」计数数据。

## 7. 依赖项

| 依赖 | Issue ID | 类型 | 说明 |
|------|----------|------|------|
| `SUO-201-BE-001` | 数据库 Schema | 硬依赖 | 数据表必须已创建 |
| `SUO-201-SH-002` | 共享类型定义 | 软依赖 | Agent 产出 payload 类型应与共享类型对齐 |
| `claude-agent` 服务 | — | 现有 | 复用现有 SSE 端点和 thread 机制（`docs/CLAUDE.md`） |
| 现有 Auth 中间件 | — | 现有 | 复用 `backend/routers/deps.py` 中的 `get_current_user` |

## 8. 测试策略

### 8.1 最小契约校验测试

```python
def test_agent_story_payload_requires_title():
    with pytest.raises(ValidationError):
        AgentStoryPayload(description="没有标题")
```

### 8.2 幂等存储测试

```python
def test_store_agent_story_output_idempotent(db, user_id, workspace_id):
    payload = AgentStoryPayload(title="午夜咖啡馆", characters=[...], scenes=[...])
    result1 = store_agent_story_output(db, user_id, workspace_id, "thread-001", payload)
    result2 = store_agent_story_output(db, user_id, workspace_id, "thread-001", payload)
    assert result1["story_id"] == result2["story_id"]
```

### 8.3 关联关系测试

```python
def test_store_agent_story_output_creates_relations(db, user_id, workspace_id):
    payload = AgentStoryPayload(title="午夜咖啡馆", characters=[AgentCharacterPayload(name="林小雨")], scenes=[])
    result = store_agent_story_output(db, user_id, workspace_id, "thread-001", payload)
    assert len(result["character_ids"]) == 1
    rows = db.execute("SELECT * FROM story_workspace_story_characters WHERE story_id = ?", (result["story_id"],)).fetchall()
    assert len(rows) == 1
```

### 8.4 端点测试

```python
def test_receive_agent_story_output(client, auth_headers):
    response = client.post(
        "/api/story-workspace/internal/agent-output",
        json={"title": "午夜咖啡馆", "type": "short"},
        headers={**auth_headers, "X-Agent-Session-Id": "thread-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["review_status"] == "pending"
```

### 8.5 错误隔离测试

```python
def test_agent_integration_error_does_not_break_chat():
    """Simulate a store failure and verify the caller still returns a normal chat response."""
```

## 9. 完成标志

- [ ] `AgentStoryPayload`、`AgentCharacterPayload`、`AgentScenePayload` 最小契约模型定义完成。
- [ ] `store_agent_story_output()` 实现完整：故事、角色、场景写入 + 关联建立 + 冗余计数更新。
- [ ] 同一 `agent_session_id` + `title` 重复生成时幂等更新，不产生重复记录。
- [ ] `POST /api/story-workspace/internal/agent-output` 内部端点可用，要求 `X-Agent-Session-Id`。
- [ ] claude-agent 服务在合适时机调用集成服务，且不破坏现有 Chat SSE 流程。
- [ ] 写入的数据 `agent_generated=true`、`review_status='pending'`。
- [ ] Dashboard 通过 `GET /api/story-workspace/stories?review_status=pending` 能正确显示待审阅计数。
- [ ] 校验失败 / 写入失败时记录日志并返回明确错误，不阻塞用户现有操作。
- [ ] 新增/更新测试全部通过。

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Agent 输出格式不固定** | 高 | 定义最小数据契约，仅要求 `title`；多余字段忽略；校验失败时记录日志 |
| **同一 thread 重新生成导致重复数据** | 中 | 以 `agent_session_id` + `title` 为去重键，更新而非插入 |
| **Agent 生成与页面渲染的时序问题** | 中 | 数据落地即视为 pending；前端通过轮询获取；Agent 生成中状态由前端 Chat UI 承载 |
| **claude-agent 服务调用失败影响 Chat 体验** | 中 | 集成调用使用 try/except 隔离；错误仅记录，不向用户暴露异常 |
| **角色/场景关联错误** | 中 | 事务包裹写入；关联表主键防止重复关联 |
| **SQLite 并发写入** | 低 | WAL 模式已启用；事务内批量写入减少锁竞争 |
| **与 Deck 编辑器关系未明确** | 低 | 本期仅持久化 Agent 产出，不涉及 Deck 导出；后续迭代在独立任务中处理 |
| **shared 类型不同步** | 中 | `SUO-201-SH-002` 产出 canonical 类型后，本任务模型需与其对齐 |

## 11. 下游执行提示

- **StagePlanner 注意**: 本任务依赖 `SUO-201-BE-001`（Schema）完成，可与 `SUO-201-BE-002`（REST API）并行开发，但 E2E 验证需等待 `SUO-201-FE-004`（审阅面板）完成。
- **与 FrontendTaskAgent 协作**: 前端 Dashboard 通过 `review_status=pending` 筛选待审阅项；本任务确保该筛选返回正确数据。
- **与 claude-agent 团队协作**: 若未来 Agent 输出格式升级，需同步更新 `AgentStoryPayload` 契约。
- **共享类型对齐**: `SUO-201-SH-002` 产出的类型定义应与本任务的 Pydantic 模型保持一致；本任务可基于设计稿先行开发，后续对齐。

## 12. 执行边界

### 允许修改范围
- `backend/services/story-workspace/agent_integration.py` — **新文件**：Agent 产出接收、解析、持久化服务。
- `backend/routers/story-workspace.py` — 追加 `/api/story-workspace/internal/agent-output` 内部接收端点。
- `backend/claude_agent/service.py` 或 `backend/routers/claude_agent.py` — 在 Agent SSE 流收尾处增加调用集成服务的逻辑（优先采用服务内函数调用，而非 HTTP 自调用）。
- `backend/claude_agent/context_builder.py` — 可选：在系统提示中增加「生成剧本」输出格式指导。
- `backend/tests/test_story_workspace_agent_integration.py` — **新文件**：集成测试（最小契约校验、幂等存储、关联关系、错误隔离）。

### 禁止修改范围
- ❌ `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` — 任何设计阶段产物。
- ❌ `docs/task/TASK-REQUIREMENT-FORMAT.md` — 提示词模板。
- ❌ 前端代码、前端 task 文件 — 不在本 Agent 职责范围内。
- ❌ 现有 `claude-agent` SSE 流核心协议 — 不修改 SSE 消息格式、thread 生命周期、`/api/claude-agent` 端点本身的行为。
- ❌ 现有 Chat / Deck 功能 — Agent 集成是新增逻辑，不是替换；禁止破坏现有功能。
- ❌ `backend/routers/story-workspace.py` 中已有 CRUD 和审阅端点 — 仅追加内部接收端点，不修改现有逻辑。
- ❌ 实现代码以外的任何文件 — 本 task 文档不是 execute 授权。

### 明确排除项（本期不在范围）
- **复杂画布编辑器** — Agent 产出为结构化数据（故事/角色/场景），不生成画布/时间线可视化内容。
- **视频生成模块** — Agent 产出不包含视频/镜头数据；视频生成为后续迭代。
- **移动端适配** — Agent 集成通道与设备无关；但本期明确排除移动端/平板端适配需求。
- **用户手动创建内容** — Agent 集成仅处理 Agent 生成的内容；用户手动创建的内容不走本通道（实际上本期不允许用户手动创建）。
- **实时协作** — 同一 thread 的并发生成由 SQLite 事务串行化，无多用户协作机制。
- **四视角转面图** — Agent 角色产出仅包含单张头像信息，不涉及多视角。
- **历史版本管理** — 重新生成时更新现有记录，不保留旧版本。
- **@提及系统** — Agent 产出内容中不解析 @提及。
- **计费/积分系统** — Agent 生成不触发积分消耗记录。
- **与 Deck 编辑器打通** — 已确认内容暂存，不自动导出到 Deck；后续迭代在独立任务中处理（设计稿 `[CLARIFICATION_NEEDED]`）。
- **异步队列/消息中间件** — 使用同步调用（服务内函数调用或内部 HTTP），不引入 Redis/RabbitMQ 等中间件。
