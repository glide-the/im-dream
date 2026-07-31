# task_202_backend_story-workspace-rest-api

## 1. 任务标题

Story Workspace REST API 实现

## 2. 关联 Issue

- **Issue ID**: `SUO-201-BE-002`
- **Issue 标题**: Story Workspace REST API 实现
- **类型**: backend
- **优先级**: P0
- **标签**: `api`, `rest`, `crud`
- **来源设计稿**:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §6.1–6.2（API 路由设计、查询参数规范）
  - `docs/design/story-workspace/story-workspace-prd.md` §4.2（命名映射）
  - `docs/design/story-workspace/story-workspace-prd.md` §6.1–6.2（API 路由设计）
- **Issue 清单**: `docs/issue/ISSUES_story-workspace.md` §3 Issue 明细

## 3. 任务目标

实现 story-workspace 的 REST API 路由，包括工作区、故事、角色、场景的 CRUD 操作。支持列表查询（搜索、筛选、排序、分页）和详情查询。所有路由使用 `/api/story-workspace/*` 前缀。

**核心约束**：
- 复用现有全局 Auth 中间件进行用户认证
- 列表接口返回标准分页格式 `{ data, pagination: { page, per_page, total, total_pages } }`
- PATCH 更新接口用于用户编辑 Agent 生成内容
- 搜索使用 SQLite `LIKE`（项目使用 SQLite，无 `pg_trgm`）

## 4. 实现步骤

### Step 1: 创建 Router 文件

新建 `backend/routers/story-workspace.py`，使用 FastAPI `APIRouter`：

```python
from fastapi import APIRouter, Depends, Query, Request
from typing import Optional, List

router = APIRouter(prefix="/api/story-workspace", tags=["story-workspace"])
```

### Step 2: 实现工作区 API

#### `GET /api/story-workspace/workspace`

- 获取当前认证用户的工作区
- 若用户无工作区，自动创建一个默认工作区
- 响应：Workspace 对象

**响应示例**：
```json
{
  "id": "ws-uuid",
  "name": "默认工作区",
  "owner_id": 123,
  "settings": {},
  "created_at": "2026-08-01T10:00:00Z",
  "updated_at": "2026-08-01T10:00:00Z"
}
```

#### `PATCH /api/story-workspace/workspace/:id`

- 更新工作区设置
- Body: `{ name?: string, settings?: object }`
- 仅允许工作区所有者更新

### Step 3: 实现故事列表与详情 API

#### `GET /api/story-workspace/stories`

**查询参数**：

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `q` | string | 搜索关键词（标题 LIKE） | `q=咖啡` |
| `review_status` | string | 审阅状态筛选（逗号分隔多选） | `review_status=pending,confirmed` |
| `status` | string | 内容状态筛选 | `status=draft` |
| `type` | string | 类型筛选（逗号分隔多选） | `type=short,long` |
| `sort` | string | 排序字段 | `sort=updated_at` / `sort=created_at` / `sort=title` |
| `order` | string | 排序方向 | `order=desc` / `order=asc` |
| `page` | int | 页码（默认 1） | `page=1` |
| `per_page` | int | 每页条数（默认 20，最大 100） | `per_page=20` |

**实现逻辑**：
1. 从 auth 获取当前 `user_id`
2. 构建基础 SQL：`SELECT * FROM story_workspace_stories WHERE author_id = ?`
3. 若 `q` 存在：追加 `AND title LIKE '%' || ? || '%'`
4. 若 `review_status` 存在：解析逗号分隔值，追加 `AND review_status IN (?, ?, ...)`
5. 若 `status` 存在：同上 IN 查询
6. 若 `type` 存在：同上 IN 查询
7. 追加排序：`ORDER BY {sort} {order}`（sort 字段需白名单校验）
8. 分页：先 `COUNT(*)` 获取总数，再 `LIMIT ? OFFSET ?`
9. 返回标准分页格式

**响应格式**：
```json
{
  "data": [
    {
      "id": "story-uuid",
      "identifier": "story-001",
      "title": "午夜咖啡馆",
      "description": "一个发生在午夜咖啡馆的奇幻故事...",
      "status": "draft",
      "review_status": "pending",
      "type": "short",
      "character_count": 3,
      "scene_count": 5,
      "agent_generated": true,
      "agent_session_id": "thread-uuid",
      "created_at": "2026-08-01T10:00:00Z",
      "updated_at": "2026-08-01T10:00:00Z",
      "confirmed_at": null,
      "published_at": null
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

#### `GET /api/story-workspace/stories/:id`

- 返回故事详情，包含关联角色列表和关联场景列表
- 需验证 `author_id` 匹配当前用户

**响应扩展**：
```json
{
  "id": "story-uuid",
  "title": "午夜咖啡馆",
  ...,
  "characters": [
    { "id": "char-uuid", "name": "林小雨", "identity": "咖啡师" }
  ],
  "scenes": [
    { "id": "scene-uuid", "name": "开场·雨夜" }
  ]
}
```

#### `PATCH /api/story-workspace/stories/:id`

- 更新故事字段（用户编辑 Agent 生成内容）
- Body: `{ title?: string, description?: string, content?: string, type?: string }`
- 限制：不可修改 `review_status`、`agent_generated`、`agent_session_id`
- 自动更新 `updated_at`

### Step 4: 实现角色列表与详情 API

#### `GET /api/story-workspace/characters`

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词（名称 LIKE） |
| `review_status` | string | 审阅状态筛选 |
| `sort` | string | 排序字段（name / updated_at / created_at） |
| `order` | string | 排序方向 |
| `page` | int | 页码 |
| `per_page` | int | 每页条数 |

**响应字段**：
```json
{
  "data": [
    {
      "id": "char-uuid",
      "identifier": "char-001",
      "name": "林小雨",
      "avatar_url": null,
      "identity": "咖啡师",
      "personality": "温柔、内向",
      "tags": ["温柔", "内向", "细腻"],
      "story_count": 2,
      "review_status": "pending",
      "agent_generated": true,
      "created_at": "2026-08-01T10:00:00Z",
      "updated_at": "2026-08-01T10:00:00Z"
    }
  ],
  "pagination": { ... }
}
```

#### `GET /api/story-workspace/characters/:id`

- 返回角色详情，包含关联故事列表

#### `PATCH /api/story-workspace/characters/:id`

- 更新角色字段
- Body: `{ name?: string, identity?: string, personality?: string, background?: string, catchphrase?: string, tags?: string[], avatar_url?: string }`
- 限制：不可修改 `review_status`、`agent_generated`

### Step 5: 实现场景列表与详情 API

#### `GET /api/story-workspace/scenes`

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `q` | string | 搜索关键词（名称 LIKE） |
| `review_status` | string | 审阅状态筛选 |
| `story_id` | string | 按所属故事筛选 |
| `sort` | string | 排序字段 |
| `order` | string | 排序方向 |
| `page` | int | 页码 |
| `per_page` | int | 每页条数 |

#### `GET /api/story-workspace/scenes/:id`

- 返回场景详情，包含关联角色列表和所属故事信息

#### `PATCH /api/story-workspace/scenes/:id`

- 更新场景字段
- Body: `{ name?: string, description?: string, story_id?: string, order_index?: int }`

### Step 6: 在 `server.py` 中注册路由

```python
from routers.story_workspace import router as story_workspace_router

app.include_router(story_workspace_router)
```

### Step 7: 实现通用分页辅助函数

```python
def paginate_query(db, base_sql: str, count_sql: str, params: tuple,
                   page: int, per_page: int) -> dict:
    """Execute paginated query and return standard pagination format."""
    total = db.execute(count_sql, params).fetchone()[0]
    offset = (page - 1) * per_page
    rows = db.execute(base_sql + " LIMIT ? OFFSET ?", params + (per_page, offset)).fetchall()
    total_pages = (total + per_page - 1) // per_page
    return {
        "data": [row_to_dict(row) for row in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages
        }
    }
```

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/routers/story-workspace.py` | **新文件**：Story Workspace REST API 路由 |
| `backend/server.py` | 路由注册 |
| `backend/database.py` | 复用 `get_db()` 连接管理 |
| `backend/tests/test_story_workspace_api.py` | **新文件**：API 测试 |

## 6. 输入 / 输出说明

### 输入

- 数据库表：`story_workspace_workspaces`, `story_workspace_stories`, `story_workspace_characters`, `story_workspace_scenes`, `story_workspace_story_characters`, `story_workspace_scene_characters`
- 认证信息：当前用户 `user_id`（从现有 auth 中间件获取）
- 查询参数：`q`, `review_status`, `status`, `type`, `sort`, `order`, `page`, `per_page`

### 输出

- `backend/routers/story-workspace.py`：完整的 FastAPI Router，包含所有 CRUD 端点
- 标准分页响应格式：`{ data: T[], pagination: { page, per_page, total, total_pages } }`
- 详情响应：包含关联数据的完整对象

## 7. 依赖项

| 依赖 | Issue ID | 类型 | 说明 |
|------|----------|------|------|
| `SUO-201-BE-001` | 数据库 Schema | 硬依赖 | 所有 API 依赖数据库表存在 |
| `SUO-201-SH-002` | 共享类型定义 | 软依赖 | 类型定义对齐，但可基于设计稿先行开发 |
| 现有 Auth 中间件 | — | 现有 | 复用 `backend/routers/deps.py` 中的 `get_current_user` |

## 8. 测试策略

### 8.1 列表查询测试

```python
def test_get_stories_list(client, auth_headers):
    """Test stories list endpoint with pagination."""
    response = client.get("/api/story-workspace/stories", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert "page" in data["pagination"]
    assert "total" in data["pagination"]

def test_get_stories_with_filters(client, auth_headers):
    """Test stories list with review_status filter."""
    response = client.get(
        "/api/story-workspace/stories?review_status=pending",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    for story in data["data"]:
        assert story["review_status"] == "pending"

def test_get_stories_search(client, auth_headers):
    """Test stories search with q parameter."""
    response = client.get(
        "/api/story-workspace/stories?q=咖啡",
        headers=auth_headers
    )
    assert response.status_code == 200
```

### 8.2 详情查询测试

```python
def test_get_story_detail(client, auth_headers, sample_story):
    """Test story detail endpoint."""
    response = client.get(
        f"/api/story-workspace/stories/{sample_story['id']}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_story["id"]
    assert "characters" in data
    assert "scenes" in data
```

### 8.3 PATCH 更新测试

```python
def test_patch_story(client, auth_headers, sample_story):
    """Test story update endpoint."""
    response = client.patch(
        f"/api/story-workspace/stories/{sample_story['id']}",
        json={"title": "更新后的标题", "description": "更新后的描述"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "更新后的标题"
    assert data["updated_at"] > data["created_at"]

def test_patch_story_forbidden_fields(client, auth_headers, sample_story):
    """Test that review_status cannot be modified via PATCH."""
    response = client.patch(
        f"/api/story-workspace/stories/{sample_story['id']}",
        json={"review_status": "confirmed"},  # Should be ignored or rejected
        headers=auth_headers
    )
    # Should either 400 or ignore the field
    assert response.status_code in [200, 400]
```

### 8.4 权限测试

```python
def test_get_stories_unauthorized(client):
    """Test that unauthenticated requests are rejected."""
    response = client.get("/api/story-workspace/stories")
    assert response.status_code == 401

def test_get_other_user_story(client, auth_headers, other_user_story):
    """Test that users cannot access other users' stories."""
    response = client.get(
        f"/api/story-workspace/stories/{other_user_story['id']}",
        headers=auth_headers
    )
    assert response.status_code == 404  # or 403
```

## 9. 完成标志

- [ ] `GET /api/story-workspace/workspace` — 获取当前用户工作区
- [ ] `PATCH /api/story-workspace/workspace/:id` — 更新工作区设置
- [ ] `GET /api/story-workspace/stories` — 列表（支持 q/review_status/status/type/sort/order/page/per_page）
- [ ] `GET /api/story-workspace/stories/:id` — 详情（含关联角色/场景）
- [ ] `PATCH /api/story-workspace/stories/:id` — 更新（用户编辑 Agent 生成内容）
- [ ] `GET /api/story-workspace/characters` — 列表
- [ ] `GET /api/story-workspace/characters/:id` — 详情
- [ ] `PATCH /api/story-workspace/characters/:id` — 更新
- [ ] `GET /api/story-workspace/scenes` — 列表
- [ ] `GET /api/story-workspace/scenes/:id` — 详情
- [ ] `PATCH /api/story-workspace/scenes/:id` — 更新
- [ ] 列表接口返回标准分页格式 `{ data, pagination: { page, per_page, total, total_pages } }`
- [ ] API 认证复用现有全局 Auth 中间件
- [ ] 搜索使用 SQLite `LIKE`（非 pg_trgm）
- [ ] 所有测试通过

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **SQLite LIKE 搜索性能** | 中 | 标题字段已建 B-tree 索引；大数据量时考虑 FTS5 扩展 |
| **排序字段注入** | 中 | `sort` 参数必须白名单校验（仅允许 `updated_at`, `created_at`, `title` 等） |
| **N+1 查询** | 中 | 详情接口的关联数据使用 JOIN 一次性查询，避免多次往返 |
| **并发更新冲突** | 低 | SQLite 文件级锁天然处理并发；如需乐观锁，后续添加 `version` 字段 |
| **PATCH 字段越权修改** | 中 | 明确列出允许修改的字段白名单，拒绝 `review_status` / `agent_generated` 等敏感字段 |
| **分页深度性能** | 低 | `per_page` 最大限制 100；大数据量时考虑游标分页 |

## 11. 允许与禁止修改范围

- **仅允许修改**：`backend/routers/story-workspace.py`、`backend/server.py`、`backend/tests/test_story_workspace_api.py`；可复用 `backend/database.py` 的 `get_db()`。
- **禁止修改**：`docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、前端代码、数据库 schema 定义文件。
- **禁止行为**：不得把本 task 文档当作 execute 授权直接实现；不得修改设计稿或 Issue 清单。

## 12. 下游执行提示

- **StagePlanner 注意**: 本任务依赖 `SUO-201-BE-001`（Schema）完成。Stage 排期时需确保 Schema 任务先完成。
- **前端消费边界**: 前端通过 `GET /api/story-workspace/stories` 等接口消费数据。响应格式中的 `pagination` 结构是前后端共享契约，变更需同步通知 FrontendTaskAgent。
- **与审阅工作流的关系**: 本任务仅实现 CRUD 和列表查询。审阅状态流转（confirm/reject/archive）在 `SUO-201-BE-003` 中实现，但本任务需确保 `review_status` 字段在 PATCH 中不可被直接修改。
- **共享类型对齐**: API 请求/响应字段应与 `SUO-201-SH-002` 的 Python 规范源保持一致。

## 13. 执行边界（补充修订）

### 允许修改范围
- `backend/routers/story-workspace.py` — **新文件**：Story Workspace REST API 路由（FastAPI `APIRouter`），包含工作区、故事、角色、场景的 CRUD 端点。
- `backend/server.py` — 注册 `story_workspace_router`。
- `backend/tests/test_story_workspace_api.py` — **新文件**：API 测试（列表查询、详情查询、PATCH 更新、权限、搜索、筛选、分页）。
- 可在 `backend/routers/story-workspace.py` 中定义通用分页辅助函数（如 `paginate_query`）；若项目已有通用分页工具，优先复用。

### 禁止修改范围
- ❌ `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` — 任何设计阶段产物。
- ❌ `docs/task/TASK-REQUIREMENT-FORMAT.md` — 提示词模板。
- ❌ 前端代码、前端 task 文件 — 不在本 Agent 职责范围内。
- ❌ `backend/database.py` — 本任务不复用 `database.py` 做 Schema 修改（Schema 在 `SUO-201-BE-001` 中完成），仅复用 `get_db()` 连接管理。
- ❌ 现有 `claude-agent` 服务 — 不修改 SSE 流、thread 生命周期、Agent 调用逻辑。
- ❌ 实现代码以外的任何文件 — 本 task 文档不是 execute 授权。

### 明确排除项（本期不在范围）
- **复杂画布编辑器** — REST API 仅提供结构化数据的 CRUD，不提供画布/时间线可视化数据的专用端点。
- **视频生成模块** — API 不包含视频/镜头相关资源端点。
- **移动端适配** — 后端 API 不假设移动端消费者；本期明确排除移动端/平板端适配需求，API 消费者假设为桌面端（≥1280px）。
- **用户手动创建内容** — POST 创建端点不在本任务中；所有内容通过 Agent 集成通道（`SUO-201-BE-004`）写入，用户仅通过 PATCH 编辑 Agent 生成内容。
- **实时协作** — 无 WebSocket/Socket.io 实时推送端点；前端通过轮询刷新数据。
- **四视角转面图** — 角色 `avatar_url` 为单字符串，不上传/管理多视角资源。
- **历史版本管理** — PATCH 更新直接覆盖，不保留历史版本。
- **@提及系统** — 无提及解析、通知推送端点。
- **计费/积分系统** — API 调用不触发积分消耗记录。
- **DELETE 端点** — 本期不提供物理删除；归档通过 `status='archived'` 实现（在 `SUO-201-BE-003` 中处理）。
- **文件上传** — 角色头像 `avatar_url` 为外部 URL，本 API 不提供文件上传/存储端点。

---

## 14. 归属审计记录

> **审计事实**：本文件 `task_202_backend_story-workspace-rest-api.md` 最初由 `efe7040`（`task(story-workspace): SUO-202 前端任务文档家族`）并发提交，该 commit 同时包含了 9 份前端 task 文档和本份后端 task 文档。随后 `2b0f8ab`（`task(story-workspace): SUO-203 后端任务文档家族`）在生成后端 5 份 task 文档时，**未包含** `task_202` 的变更（该 commit 的 stat 仅显示 task_201、task_203、task_204、task_205）。
>
> **归属确认**：`SUO-201-BE-002`（Story Workspace REST API 实现）的主责 Agent 为 `BackendTaskAgent`。本 task 文档覆盖 BE-002 的全部后端职责：REST API 路由设计、CRUD 实现、分页/搜索/筛选逻辑、权限控制。FrontendTaskAgent 仅消费本 API，不负责 API 实现。
>
> **责任边界**：BackendTaskAgent 对以下 BE-002 内容承担明确责任：
> - `backend/routers/story-workspace.py` 的完整实现
> - `backend/server.py` 的路由注册
> - API 响应格式（含 `PaginatedResponse` 结构）的定义与稳定
> - 搜索/筛选/排序/分页的后端逻辑
> - PATCH 更新的字段白名单控制
> - API 测试 `backend/tests/test_story_workspace_api.py`
>
> 记录时间：2026-08-01 | 记录 Agent：BackendTaskAgent | Issue：SUO-205
