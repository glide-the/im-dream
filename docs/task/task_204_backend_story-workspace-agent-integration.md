# task_204_backend_story-workspace-agent-integration

## 1. 任务标题

Story Workspace Agent 产出数据接收与存储集成

## 2. 关联 Issue

- **Issue ID**: `SUO-201-BE-004`
- **Issue 标题**: Agent 产出数据接收与存储集成
- **类型**: backend
- **优先级**: P0
- **标签**: `agent`, `integration`, `sse`
- **来源设计稿**:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §10.2（与 claude-agent 服务的集成）
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-007`（核心工作流）
  - `docs/CLAUDE.md` §Thread Lifecycle
- **Issue 清单**: `docs/issue/ISSUES_story-workspace.md` §3 Issue 明细

## 3. 任务目标

实现 claude-agent 服务与 story-workspace 的数据集成。Agent 生成剧本/角色/场景后，通过内部 API 将数据存入 story-workspace 数据表，标记 `review_status='pending'` 和 `agent_generated=true`。需要复用现有 `claude-agent` 服务的 SSE 端点和 thread 机制。

**核心约束**：
- 与现有 `claude-agent` 服务集成不破坏现有 Chat / Deck 功能
- 错误处理：Agent 生成失败时记录日志，不阻塞用户现有操作
- 数据存入时自动设置 `agent_generated=true`，`review_status='pending'`
- 关联 `agent_session_id` 到 Chat thread ID
- 角色和场景数据与故事数据一并存入，自动建立关联

## 4. 实现步骤

### Step 1: 定义 Agent 最小数据契约

Agent 生成内容格式不固定，需定义最小数据契约以确保可存储：

**最小数据契约（Minimum Data Contract）**：

```python
class AgentStoryOutput(TypedDict):
    """Minimum data contract for Agent-generated story content."""
    title: str                    # 必填：故事标题
    description: str              # 可选：故事描述
    type: str                     # 可选：short / long / script / outline，默认 short
    content: str                  # 可选：故事内容（Markdown）
    characters: List[AgentCharacterOutput]  # 可选：角色列表
    scenes: List[AgentSceneOutput]          # 可选：场景列表

class AgentCharacterOutput(TypedDict):
    """Minimum data contract for Agent-generated character."""
    name: str                     # 必填：角色名称
    identity: str                 # 可选：角色身份/职业
    personality: str              # 可选：性格描述
    background: str               # 可选：背景故事
    catchphrase: str              # 可选：口头禅
    tags: List[str]               # 可选：性格标签

class AgentSceneOutput(TypedDict):
    """Minimum data contract for Agent-generated scene."""
    name: str                     # 必填：场景名称
    description: str              # 可选：场景描述
    order_index: int              # 可选：在故事中的顺序，默认 0
```

**数据契约规则**：
1. `title`（故事）和 `name`（角色/场景）是唯一必填字段
2. 所有可选字段缺失时，使用数据库默认值
3. Agent 输出超出契约的字段应被忽略（不报错）
4. 契约字段类型不匹配时，尝试类型转换；转换失败则使用默认值

### Step 2: 创建内部接收端点

在 `backend/routers/story-workspace.py` 中追加内部端点（用于 Agent 服务调用）：

#### `POST /api/story-workspace/internal/agent-output`

**功能**：接收 Agent 生成的故事/角色/场景数据，存入数据库

**请求体**：
```json
{
  "agent_session_id": "chat-thread-uuid",
  "user_id": 123,
  "workspace_id": "ws-uuid",
  "story": {
    "title": "午夜咖啡馆",
    "description": "一个发生在午夜咖啡馆的奇幻故事...",
    "type": "short",
    "content": "# 午夜咖啡馆\n\n深夜，咖啡馆里...",
    "characters": [
      {
        "name": "林小雨",
        "identity": "咖啡师",
        "personality": "温柔、内向",
        "tags": ["温柔", "内向", "细腻"]
      },
      {
        "name": "阿默",
        "identity": "记忆守护者",
        "personality": "神秘、安静",
        "tags": ["神秘", "安静", "古怪"]
      }
    ],
    "scenes": [
      {
        "name": "开场·雨夜",
        "description": "雨夜中的咖啡馆外景",
        "order_index": 0
      },
      {
        "name": "咖啡馆内景",
        "description": "温暖的咖啡馆内部",
        "order_index": 1
      }
    ]
  }
}
```

**实现逻辑**：

```python
@router.post("/internal/agent-output")
async def receive_agent_output(
    request: AgentOutputRequest,
    db: Database = Depends(get_db)
):
    """
    Receive Agent-generated content and store it in story-workspace tables.
    This endpoint is called by the claude-agent service after content generation.
    """
    try:
        # 1. 验证用户和工作区
        workspace = get_or_create_workspace(db, request.user_id, request.workspace_id)

        # 2. 生成业务标识
        story_identifier = generate_identifier("story")

        # 3. 插入故事主记录
        story_id = str(uuid.uuid4())
        db.execute("""
            INSERT INTO story_workspace_stories
            (id, identifier, title, description, status, review_status, type,
             content, author_id, workspace_id, character_count, scene_count,
             agent_generated, agent_session_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'draft', 'pending', ?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (story_id, story_identifier, request.story.title,
              request.story.description, request.story.type or 'short',
              request.story.content, request.user_id, workspace['id'],
              len(request.story.characters or []),
              len(request.story.scenes or []),
              request.agent_session_id))

        # 4. 插入角色记录
        character_ids = []
        for char_data in (request.story.characters or []):
            char_id = str(uuid.uuid4())
            char_identifier = generate_identifier("character")
            db.execute("""
                INSERT INTO story_workspace_characters
                (id, identifier, name, identity, personality, background,
                 catchphrase, tags, author_id, workspace_id, review_status,
                 agent_generated, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (char_id, char_identifier, char_data.name, char_data.identity,
                  char_data.personality, char_data.background,
                  char_data.catchphrase, json.dumps(char_data.tags or []),
                  request.user_id, workspace['id']))
            character_ids.append(char_id)

            # 4.1 建立故事-角色关联
            db.execute("""
                INSERT INTO story_workspace_story_characters
                (story_id, character_id, role_type, created_at)
                VALUES (?, ?, ' protagonist', CURRENT_TIMESTAMP)
            """, (story_id, char_id))

        # 5. 插入场景记录
        scene_ids = []
        for scene_data in (request.story.scenes or []):
            scene_id = str(uuid.uuid4())
            scene_identifier = generate_identifier("scene")
            db.execute("""
                INSERT INTO story_workspace_scenes
                (id, identifier, name, description, story_id, author_id,
                 workspace_id, order_index, review_status, agent_generated,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (scene_id, scene_identifier, scene_data.name, scene_data.description,
                  story_id, request.user_id, workspace['id'],
                  scene_data.order_index or 0))
            scene_ids.append(scene_id)

        # 6. 提交事务
        db.commit()

        # 7. 返回创建的资源 ID
        return {
            "success": True,
            "story_id": story_id,
            "character_ids": character_ids,
            "scene_ids": scene_ids
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store Agent output: {e}")
        raise HTTPException(status_code=500, detail="Failed to store Agent output")
```

### Step 3: 与 claude-agent 服务集成

在 `backend/claude_agent/` 目录下，找到 Agent 生成内容后的回调点，调用 story-workspace 内部端点：

**集成点分析**：

根据 `docs/CLAUDE.md`，claude-agent 服务的核心入口是：
- `POST /api/claude-agent` — SSE 流式端点
- Thread 生命周期：`chat_thread` 表存储会话

**集成方案**：

在 Agent 完成内容生成后（SSE 流结束），解析生成的内容，提取故事/角色/场景数据，调用内部存储端点。

```python
# backend/claude_agent/story_workspace_integration.py

import logging
from typing import Optional
from database import get_db

logger = logging.getLogger(__name__)

async def store_agent_output_to_workspace(
    thread_id: str,
    user_id: int,
    generated_content: dict
) -> Optional[dict]:
    """
    Store Agent-generated story content to story-workspace.
    Called after Agent finishes generating content in a chat thread.

    Args:
        thread_id: The chat thread ID (maps to agent_session_id)
        user_id: The user ID
        generated_content: Parsed story/character/scene data from Agent output

    Returns:
        dict with story_id, character_ids, scene_ids or None on failure
    """
    try:
        db = get_db()

        # Build the internal request payload
        payload = {
            "agent_session_id": thread_id,
            "user_id": user_id,
            "workspace_id": None,  # Will use default workspace
            "story": generated_content
        }

        # Direct database insertion (avoid HTTP loopback)
        result = _insert_agent_output(db, payload)
        db.commit()

        logger.info(f"Agent output stored: story_id={result['story_id']}")
        return result

    except Exception as e:
        logger.error(f"Failed to store Agent output to workspace: {e}")
        # Do not raise — Agent generation should not fail due to storage issues
        return None
    finally:
        db.close()

def _insert_agent_output(db, payload: dict) -> dict:
    """Direct database insertion logic (mirrors the internal endpoint)."""
    # ... (same SQL as Step 2)
    pass
```

### Step 4: 内容解析策略

Agent 生成的内容是自然语言文本，需要解析提取结构化数据。

**解析策略选项**：

| 策略 | 实现方式 | 优点 | 缺点 |
|------|----------|------|------|
| A. LLM 结构化输出 | 要求 Agent 输出 JSON | 结构化程度高 | 需要修改 Agent Prompt |
| B. 文本解析 + 启发式 | 解析 Markdown/文本 | 无需修改 Agent | 解析不可靠 |
| C. 混合策略 | Agent 输出带标记的文本，后端提取 | 平衡 | 需要约定标记格式 |

**推荐策略 C（混合策略）**：

在 Agent Prompt 中要求输出带标记的结构化内容：

```
当你生成剧本内容时，请在回复末尾附加以下格式的结构化数据：

<STORY_WORKSPACE_OUTPUT>
{
  "title": "故事标题",
  "description": "故事描述",
  "type": "short",
  "content": "完整故事内容（Markdown）",
  "characters": [
    {"name": "角色名", "identity": "身份", "personality": "性格", "tags": ["标签1"]}
  ],
  "scenes": [
    {"name": "场景名", "description": "场景描述", "order_index": 0}
  ]
}
</STORY_WORKSPACE_OUTPUT>
```

后端解析逻辑：

```python
def parse_agent_output(message_text: str) -> Optional[dict]:
    """Extract structured story data from Agent message text."""
    import re
    import json

    # Look for <STORY_WORKSPACE_OUTPUT> tag
    pattern = r'<STORY_WORKSPACE_OUTPUT>\s*(.*?)\s*</STORY_WORKSPACE_OUTPUT>'
    match = re.search(pattern, message_text, re.DOTALL)

    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        return data
    except json.JSONDecodeError:
        logger.warning("Failed to parse STORY_WORKSPACE_OUTPUT JSON")
        return None
```

### Step 5: 错误处理与降级

```python
async def safe_store_agent_output(thread_id: str, user_id: int, message_text: str):
    """
    Safely store Agent output with full error handling.
    Never raises — failures are logged but don't block the user.
    """
    try:
        # 1. Parse structured data from message
        parsed = parse_agent_output(message_text)
        if not parsed:
            logger.debug("No structured story data found in Agent output")
            return None

        # 2. Validate minimum data contract
        if not parsed.get("title"):
            logger.warning("Agent output missing required 'title' field")
            return None

        # 3. Store to database
        result = await store_agent_output_to_workspace(thread_id, user_id, parsed)
        return result

    except Exception as e:
        logger.error(f"Unexpected error storing Agent output: {e}", exc_info=True)
        return None
```

### Step 6: Dashboard 待审阅计数

确保存入后 Dashboard 可正确显示「待审阅」计数：

```python
# 此查询由前端 Dashboard 调用
# GET /api/story-workspace/stories?review_status=pending&per_page=1
# 前端只需 total 字段

# 或提供专用统计端点：
@router.get("/workspace/stats")
async def get_workspace_stats(db: Database = Depends(get_db), user = Depends(get_current_user)):
    """Get workspace statistics for Dashboard."""
    stats = db.execute("""
        SELECT
            COUNT(CASE WHEN review_status = 'pending' THEN 1 END) as pending_count,
            COUNT(CASE WHEN review_status = 'confirmed' THEN 1 END) as confirmed_count,
            COUNT(*) as total_count
        FROM story_workspace_stories
        WHERE author_id = ?
    """, (user.id,)).fetchone()

    return {
        "pending_count": stats["pending_count"],
        "confirmed_count": stats["confirmed_count"],
        "total_count": stats["total_count"]
    }
```

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/routers/story-workspace.py` | 追加内部接收端点 `/internal/agent-output` 和统计端点 `/workspace/stats` |
| `backend/claude_agent/story_workspace_integration.py` | **新文件**：Agent 产出解析与存储集成 |
| `backend/claude_agent/service.py` | 在 Agent 生成完成后调用存储集成 |
| `backend/database.py` | 复用现有数据库连接 |

## 6. 输入 / 输出说明

### 输入

- Agent 生成的自然语言文本（含 `<STORY_WORKSPACE_OUTPUT>` 标记的 JSON）
- `thread_id`: Chat thread ID（来自 `chat_thread` 表）
- `user_id`: 当前用户 ID
- 最小数据契约：至少包含 `title` 字段

### 输出

- 数据库记录：故事、角色、场景各一张表记录
- 关联记录：`story_workspace_story_characters`、`story_workspace_scene_characters`
- 响应：`{ success: true, story_id, character_ids, scene_ids }`
- Dashboard 统计：`{ pending_count, confirmed_count, total_count }`

## 7. 依赖项

| 依赖 | Issue ID | 类型 | 说明 |
|------|----------|------|------|
| `SUO-201-BE-001` | 数据库 Schema | 硬依赖 | 需要数据表存在才能存储 |
| `SUO-201-BE-002` | REST API | 软依赖 | 内部端点可独立实现，但建议在同一文件中 |
| `claude-agent` 服务 | 现有系统 | 现有 | 复用现有 SSE 端点和 thread 机制 |
| `chat_thread` 表 | 现有 | 现有 | `agent_session_id` 关联到 `chat_thread.id` |

## 8. 测试策略

### 8.1 Agent 输出解析测试

```python
def test_parse_agent_output_with_tag():
    """Test parsing structured data from Agent message."""
    message = """
    这是一个关于午夜咖啡馆的故事...

    <STORY_WORKSPACE_OUTPUT>
    {
      "title": "午夜咖啡馆",
      "description": "一个奇幻故事",
      "characters": [{"name": "林小雨", "identity": "咖啡师"}]
    }
    </STORY_WORKSPACE_OUTPUT>
    """
    result = parse_agent_output(message)
    assert result is not None
    assert result["title"] == "午夜咖啡馆"
    assert len(result["characters"]) == 1

def test_parse_agent_output_without_tag():
    """Test parsing message without structured data."""
    message = "这是一个普通的故事描述，没有结构化数据。"
    result = parse_agent_output(message)
    assert result is None
```

### 8.2 数据存储集成测试

```python
def test_store_agent_output(client, db, sample_user):
    """Test storing Agent output creates all records."""
    payload = {
        "agent_session_id": "thread-123",
        "user_id": sample_user["id"],
        "story": {
            "title": "测试故事",
            "description": "测试描述",
            "characters": [
                {"name": "角色A", "identity": "测试身份"}
            ],
            "scenes": [
                {"name": "场景1", "description": "场景描述"}
            ]
        }
    }

    response = client.post("/api/story-workspace/internal/agent-output", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["story_id"] is not None
    assert len(data["character_ids"]) == 1
    assert len(data["scene_ids"]) == 1

    # Verify database state
    story = db.execute("SELECT * FROM story_workspace_stories WHERE id = ?",
                      (data["story_id"],)).fetchone()
    assert story["review_status"] == "pending"
    assert story["agent_generated"] == 1
    assert story["agent_session_id"] == "thread-123"
```

### 8.3 最小数据契约测试

```python
def test_store_agent_output_minimal_data(client, sample_user):
    """Test storing Agent output with only required fields."""
    payload = {
        "agent_session_id": "thread-456",
        "user_id": sample_user["id"],
        "story": {
            "title": "仅标题的故事"
        }
    }

    response = client.post("/api/story-workspace/internal/agent-output", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
```

### 8.4 错误处理测试

```python
def test_store_agent_output_missing_title(client, sample_user):
    """Test that missing title is handled gracefully."""
    payload = {
        "agent_session_id": "thread-789",
        "user_id": sample_user["id"],
        "story": {
            "description": "没有标题"
        }
    }

    response = client.post("/api/story-workspace/internal/agent-output", json=payload)
    # Should either fail gracefully or use a default title
    assert response.status_code in [200, 400]

def test_store_agent_output_invalid_json(client, sample_user):
    """Test handling of invalid structured data."""
    # This tests the parse_agent_output function's resilience
    result = parse_agent_output("<STORY_WORKSPACE_OUTPUT>invalid json</STORY_WORKSPACE_OUTPUT>")
    assert result is None
```

### 8.5 Dashboard 统计测试

```python
def test_workspace_stats(client, auth_headers, pending_story, confirmed_story):
    """Test workspace statistics endpoint."""
    response = client.get("/api/story-workspace/workspace/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "pending_count" in data
    assert "confirmed_count" in data
    assert "total_count" in data
    assert data["pending_count"] >= 1
    assert data["confirmed_count"] >= 1
```

## 9. 完成标志

- [ ] Agent 生成剧本内容后，可调用 story-workspace API 存入数据
- [ ] 数据存入时自动设置 `agent_generated=true`，`review_status='pending'`
- [ ] 关联 `agent_session_id` 到 Chat thread ID
- [ ] 角色和场景数据与故事数据一并存入，自动建立关联
- [ ] 存入后 Dashboard 可正确显示「待审阅」计数（通过 `/workspace/stats` 或列表查询）
- [ ] 与现有 `claude-agent` 服务集成不破坏现有 Chat / Deck 功能
- [ ] 错误处理：Agent 生成失败时记录日志，不阻塞用户现有操作
- [ ] 最小数据契约定义并文档化（至少包含 title + 内容）
- [ ] Agent 产出解析测试通过
- [ ] 数据存储集成测试通过
- [ ] Dashboard 统计测试通过

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Agent 生成内容格式不固定** | 高 | 定义最小数据契约；使用 `<STORY_WORKSPACE_OUTPUT>` 标记约定；解析失败时优雅降级 |
| **Agent 生成与页面渲染的时序问题** | 高 | 数据库存储是同步的，页面轮询获取新数据；Agent 生成中状态由前端通过 SSE 感知 |
| **与现有 Chat/Deck 功能冲突** | 高 | 集成点为 Agent 生成完成后的回调，不影响现有 SSE 流；存储失败不阻塞用户操作 |
| **Agent Prompt 修改影响** | 中 | 结构化输出标记是附加的，不影响自然语言回复；若 Agent 不输出标记，则跳过存储 |
| **数据契约版本演进** | 中 | 契约字段使用可选设计；新增字段不影响旧数据；建议添加 `contract_version` 字段 |
| **内部端点安全性** | 中 | `/internal/*` 端点应限制为内部调用（同一进程内或带内部认证）；生产环境考虑添加 API Key |
| **同一 thread 多次生成** | 低 | 每次生成创建新故事记录（不覆盖）；`agent_session_id` 可重复，故事 ID 唯一 |

## 11. 下游执行提示

- **StagePlanner 注意**: 本任务依赖 `SUO-201-BE-001`（Schema）完成，但可与 `SUO-201-BE-002`（REST API）并行开发。Agent 集成端点是独立的内部端点。
- **与 claude-agent 服务的协作**: 本任务需要修改 `backend/claude_agent/service.py` 或相关文件，在 Agent 生成完成后调用存储逻辑。需与维护 claude-agent 服务的开发者协调集成点。
- **前端消费边界**: 前端 Dashboard 通过 `GET /api/story-workspace/workspace/stats` 或 `GET /api/story-workspace/stories?review_status=pending` 获取待审阅计数。响应格式需与 FrontendTaskAgent 对齐。
- **数据合同稳定性**: `agent_session_id` → `chat_thread.id` 的映射是核心契约。`chat_thread.id` 是 TEXT 类型，需确保类型一致。
- **E2E 验证点**: `SUO-201-SH-001`（E2E 联调）需验证：Agent 生成 → 数据库存储 → Dashboard 显示待审阅计数 → 表格展示新项 的完整链路。
