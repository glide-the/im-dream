# task_203_backend_story-workspace-review-workflow

## 1. 任务标题

Story Workspace 审阅状态流转与批量操作 API

## 2. 关联 Issue

- **Issue ID**: `SUO-201-BE-003`
- **Issue 标题**: 审阅状态流转与批量操作 API
- **类型**: backend
- **优先级**: P0
- **标签**: `api`, `review`, `workflow`
- **来源设计稿**:
  - `docs/design/story-workspace/story-workspace-layout-design.md` §6.1（confirm/reject/archive 端点）
  - `docs/design/story-workspace/story-workspace-prd.md` §4.5.1–4.5.4（交互设计）
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-007`, `DEC-008`（核心工作流、用户不手动创建）
- **Issue 清单**: `docs/issue/ISSUES_story-workspace.md` §3 Issue 明细

## 3. 任务目标

实现审阅状态流转的核心 API：确认（confirm）、驳回（reject）、归档（archive）。包括单条审阅操作和批量审阅操作。状态流转需符合设计稿定义：pending → confirmed / rejected，confirmed 可进入后续执行流程，rejected 触发 Agent 重新生成。

**核心约束**：
- 批量操作仅允许对 `review_status='pending'` 的项执行
- 操作完成后返回更新后的数据列表
- 所有操作记录审计日志（可选，视现有系统能力）
- 确认操作需记录 `confirmed_at` 时间戳
- 驳回操作需保存 `review_notes`

## 4. 实现步骤

### Step 1: 在 `backend/routers/story-workspace.py` 中追加审阅端点

在现有 REST API 路由文件（`SUO-201-BE-002` 产出）中追加以下端点：

### Step 2: 实现故事审阅端点

#### `POST /api/story-workspace/stories/:id/confirm`

**功能**：确认审阅，将故事状态从 `pending` 变为 `confirmed`

**实现逻辑**：
1. 验证用户身份和故事所有权
2. 检查当前 `review_status` 是否为 `pending`
3. 若不为 `pending`，返回 400 Bad Request（"Item is not in pending review status"）
4. 更新字段：
   - `review_status = 'confirmed'`
   - `confirmed_at = CURRENT_TIMESTAMP`
   - `updated_at = CURRENT_TIMESTAMP`
5. 返回更新后的故事对象

**响应示例**：
```json
{
  "id": "story-uuid",
  "title": "午夜咖啡馆",
  "review_status": "confirmed",
  "confirmed_at": "2026-08-01T14:30:00Z",
  "updated_at": "2026-08-01T14:30:00Z"
}
```

#### `POST /api/story-workspace/stories/:id/reject`

**功能**：驳回故事，将状态从 `pending` 变为 `rejected`

**请求体**：
```json
{
  "review_notes": "角色设定需要更详细，场景描述过于简单"
}
```

**实现逻辑**：
1. 验证用户身份和故事所有权
2. 检查当前 `review_status` 是否为 `pending`
3. 更新字段：
   - `review_status = 'rejected'`
   - `review_notes = request.review_notes`
   - `updated_at = CURRENT_TIMESTAMP`
4. 返回更新后的故事对象

**验证规则**：
- `review_notes` 为可选字段，但建议前端在驳回时要求填写
- 最大长度 2000 字符

#### `POST /api/story-workspace/stories/:id/archive`

**功能**：归档故事，将 `status` 变为 `archived`

**实现逻辑**：
1. 验证用户身份和故事所有权
2. 更新字段：
   - `status = 'archived'`
   - `updated_at = CURRENT_TIMESTAMP`
3. 注意：归档不改变 `review_status`
4. 返回更新后的故事对象

### Step 3: 实现角色审阅端点

#### `POST /api/story-workspace/characters/:id/confirm`

- 角色确认审阅
- 更新 `review_status = 'confirmed'`
- 记录 `confirmed_at`

#### `POST /api/story-workspace/characters/:id/reject`

- 角色驳回
- 更新 `review_status = 'rejected'`
- 保存 `review_notes`

### Step 4: 实现场景审阅端点

#### `POST /api/story-workspace/scenes/:id/confirm`

- 场景确认审阅
- 更新 `review_status = 'confirmed'`
- 记录 `confirmed_at`

#### `POST /api/story-workspace/scenes/:id/reject`

- 场景驳回
- 更新 `review_status = 'rejected'`
- 保存 `review_notes`

### Step 5: 实现批量操作端点

#### `POST /api/story-workspace/batch`

**功能**：对多个项目进行批量审阅操作

**请求体**：
```json
{
  "action": "confirm",
  "ids": ["story-uuid-1", "story-uuid-2", "story-uuid-3"],
  "review_notes": "批量确认",
  "resource_type": "story"
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | ✅ | 操作类型：`confirm` / `reject` / `archive` |
| `ids` | string[] | ✅ | 目标 ID 列表（最大 100 条） |
| `review_notes` | string | ❌ | 驳回时的修改意见（action=reject 时建议必填） |
| `resource_type` | string | ✅ | 资源类型：`story` / `character` / `scene` |

**实现逻辑**：
1. 验证 `ids` 长度不超过 100
2. 验证 `action` 为允许值
3. 验证 `resource_type` 为允许值
4. 根据 `resource_type` 确定目标表
5. 执行批量更新 SQL（使用 `WHERE id IN (...)`）
6. **关键约束**：仅更新 `review_status = 'pending'` 的项
7. 返回操作结果统计：

**响应示例**：
```json
{
  "success": true,
  "action": "confirm",
  "resource_type": "story",
  "total_requested": 3,
  "total_updated": 3,
  "skipped_ids": [],
  "updated_items": [
    { "id": "story-uuid-1", "review_status": "confirmed", "confirmed_at": "2026-08-01T14:30:00Z" },
    { "id": "story-uuid-2", "review_status": "confirmed", "confirmed_at": "2026-08-01T14:30:00Z" },
    { "id": "story-uuid-3", "review_status": "confirmed", "confirmed_at": "2026-08-01T14:30:00Z" }
  ]
}
```

**批量更新 SQL 示例**：
```sql
UPDATE story_workspace_stories
SET review_status = 'confirmed',
    confirmed_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP
WHERE id IN (?, ?, ?)
  AND author_id = ?
  AND review_status = 'pending'
```

### Step 6: 实现审计日志（可选）

若现有系统有审计日志能力，在每次审阅操作后记录：

```python
def log_review_action(db, user_id: int, resource_type: str, resource_id: str,
                      action: str, previous_status: str, new_status: str,
                      review_notes: Optional[str] = None):
    """Log a review action for audit purposes."""
    # 若项目有 audit_log 表则写入，否则跳过
    pass
```

**审计日志字段**：
- `id`: UUID
- `user_id`: 操作者 ID
- `resource_type`: story / character / scene
- `resource_id`: 资源 ID
- `action`: confirm / reject / archive
- `previous_status`: 操作前状态
- `new_status`: 操作后状态
- `review_notes`: 修改意见
- `created_at`: 操作时间

### Step 7: 状态流转校验矩阵

| 当前状态 | confirm | reject | archive |
|----------|---------|--------|---------|
| `pending` | ✅ → confirmed | ✅ → rejected | ✅ → archived（status 字段） |
| `confirmed` | ❌ 400 | ❌ 400 | ✅ → archived |
| `rejected` | ✅ → confirmed | ❌ 400 | ✅ → archived |
| `archived` | ❌ 400 | ❌ 400 | ❌ 400 |

**注意**：
- `archive` 操作修改 `status` 字段（draft/published → archived），不影响 `review_status`
- `confirm` 和 `reject` 操作修改 `review_status` 字段

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/routers/story-workspace.py` | 追加审阅端点（在 `SUO-201-BE-002` 基础上扩展） |
| `backend/database.py` | 如需审计日志表，追加 `story_workspace_audit_log` 表 |
| `backend/tests/test_story_workspace_review.py` | **新文件**：审阅工作流测试 |

## 6. 输入 / 输出说明

### 输入

- 数据库表：`story_workspace_stories`, `story_workspace_characters`, `story_workspace_scenes`
- 认证信息：当前用户 `user_id`
- 请求体：`{ action, ids, review_notes?, resource_type }`
- URL 参数：`:id`（资源 ID）

### 输出

- 单条操作：更新后的资源对象
- 批量操作：操作结果统计 `{ success, action, resource_type, total_requested, total_updated, skipped_ids, updated_items }`
- 错误响应：400（状态不允许）、404（资源不存在）、403（无权访问）

## 7. 依赖项

| 依赖 | Issue ID | 类型 | 说明 |
|------|----------|------|------|
| `SUO-201-BE-002` | REST API 实现 | 硬依赖 | 审阅端点追加在现有 REST API 路由文件中 |
| `SUO-201-BE-001` | 数据库 Schema | 硬依赖 | 依赖数据表存在 |
| `SUO-201-SH-002` | 共享类型定义 | 软依赖 | 类型对齐，但可基于设计稿先行开发 |

## 8. 测试策略

### 8.1 确认审阅测试

```python
def test_confirm_story(client, auth_headers, pending_story):
    """Test confirming a pending story."""
    response = client.post(
        f"/api/story-workspace/stories/{pending_story['id']}/confirm",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["review_status"] == "confirmed"
    assert data["confirmed_at"] is not None

def test_confirm_already_confirmed_story(client, auth_headers, confirmed_story):
    """Test confirming an already confirmed story returns 400."""
    response = client.post(
        f"/api/story-workspace/stories/{confirmed_story['id']}/confirm",
        headers=auth_headers
    )
    assert response.status_code == 400
```

### 8.2 驳回审阅测试

```python
def test_reject_story(client, auth_headers, pending_story):
    """Test rejecting a pending story with review notes."""
    response = client.post(
        f"/api/story-workspace/stories/{pending_story['id']}/reject",
        json={"review_notes": "需要修改角色设定"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["review_status"] == "rejected"
    assert data["review_notes"] == "需要修改角色设定"
```

### 8.3 归档测试

```python
def test_archive_story(client, auth_headers, confirmed_story):
    """Test archiving a confirmed story."""
    response = client.post(
        f"/api/story-workspace/stories/{confirmed_story['id']}/archive",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"
```

### 8.4 批量操作测试

```python
def test_batch_confirm_stories(client, auth_headers, pending_stories):
    """Test batch confirming multiple pending stories."""
    ids = [s["id"] for s in pending_stories]
    response = client.post(
        "/api/story-workspace/batch",
        json={
            "action": "confirm",
            "resource_type": "story",
            "ids": ids
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == len(ids)
    assert data["total_updated"] == len(ids)
    assert len(data["skipped_ids"]) == 0

def test_batch_reject_skips_non_pending(client, auth_headers, mixed_stories):
    """Test batch operation skips non-pending items."""
    ids = [s["id"] for s in mixed_stories]
    response = client.post(
        "/api/story-workspace/batch",
        json={
            "action": "confirm",
            "resource_type": "story",
            "ids": ids
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_updated"] < data["total_requested"]
    assert len(data["skipped_ids"]) > 0
```

### 8.5 权限测试

```python
def test_review_other_user_story(client, auth_headers, other_user_pending_story):
    """Test that users cannot review other users' stories."""
    response = client.post(
        f"/api/story-workspace/stories/{other_user_pending_story['id']}/confirm",
        headers=auth_headers
    )
    assert response.status_code in [403, 404]
```

### 8.6 状态流转矩阵测试

```python
@pytest.mark.parametrize("current_status,action,expected_status,expected_code", [
    ("pending", "confirm", "confirmed", 200),
    ("pending", "reject", "rejected", 200),
    ("confirmed", "confirm", None, 400),  # Already confirmed
    ("confirmed", "reject", None, 400),   # Cannot reject confirmed
    ("rejected", "confirm", "confirmed", 200),  # Can re-confirm rejected
    ("rejected", "reject", None, 400),    # Already rejected
])
def test_status_transitions(client, auth_headers, story_factory, current_status, action, expected_status, expected_code):
    """Test all valid and invalid status transitions."""
    story = story_factory(review_status=current_status)
    response = client.post(
        f"/api/story-workspace/stories/{story['id']}/{action}",
        headers=auth_headers
    )
    assert response.status_code == expected_code
    if expected_status:
        assert response.json()["review_status"] == expected_status
```

## 9. 完成标志

- [ ] `POST /api/story-workspace/stories/:id/confirm` — 确认审阅，状态变为 `confirmed`，记录 `confirmed_at`
- [ ] `POST /api/story-workspace/stories/:id/reject` — 驳回，状态变为 `rejected`，保存 `review_notes`
- [ ] `POST /api/story-workspace/stories/:id/archive` — 归档，状态变为 `archived`
- [ ] `POST /api/story-workspace/characters/:id/confirm` — 角色确认
- [ ] `POST /api/story-workspace/characters/:id/reject` — 角色驳回
- [ ] `POST /api/story-workspace/scenes/:id/confirm` — 场景确认
- [ ] `POST /api/story-workspace/scenes/:id/reject` — 场景驳回
- [ ] `POST /api/story-workspace/batch` — 批量操作，支持 `action: 'confirm'|'reject'|'archive'`，`ids: []`，`review_notes?: string`
- [ ] 批量操作仅允许对 `review_status='pending'` 的项执行
- [ ] 操作完成后返回更新后的数据列表
- [ ] 所有操作记录审计日志（可选，视现有系统能力）
- [ ] 状态流转矩阵完整测试通过
- [ ] 权限测试通过

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **状态流转非法操作** | 中 | 严格的校验矩阵；非法操作返回 400；数据库层使用 `WHERE review_status = 'pending'` 防止竞态条件 |
| **批量操作竞态条件** | 中 | 使用事务包裹批量更新；SQLite 文件级锁天然处理并发 |
| **驳回后重新生成流程未定义** | 高 | 设计稿标记 `[CLARIFICATION_NEEDED]`。默认假设：通过同一 Chat 线程重新生成。本任务仅负责状态变更，不负责触发重新生成 |
| **已确认内容的后续执行未定义** | 中 | 设计稿标记 `[CLARIFICATION_NEEDED]`。默认假设：暂存，后续迭代定义。本任务仅负责状态变更 |
| **审计日志表不存在** | 低 | 审计日志为可选。若项目无审计日志基础设施，记录为技术债，后续迭代补充 |
| **批量操作大量数据性能** | 低 | 限制 `ids` 最大 100 条；使用单条 `UPDATE ... WHERE id IN (...)` SQL |

## 11. 允许与禁止修改范围

- **仅允许修改**：`backend/routers/story-workspace.py`、`backend/database.py`（如需审计日志表）、`backend/tests/test_story_workspace_review.py`。
- **禁止修改**：`docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、前端代码、数据库 schema 定义文件。
- **禁止行为**：不得把本 task 文档当作 execute 授权直接实现；不得修改设计稿或 Issue 清单。

## 12. 下游执行提示

- **StagePlanner 注意**: 本任务依赖 `SUO-201-BE-002`（REST API）完成。审阅端点是追加在现有路由文件中的，不是独立文件。
- **与前端协作点**: 前端审阅面板调用 `POST /.../confirm` 和 `POST /.../reject`。驳回时需传递 `review_notes`。批量操作时前端需收集选中项 ID 列表。
- **与 E2E 联调的关系**: `SUO-201-SH-001`（E2E 联调）依赖本任务完成。Stage 排期时需确保本任务在 E2E 之前完成。
- **数据合同稳定性**: `review_status` 枚举值（`pending` / `confirmed` / `rejected`）是前后端共享契约，变更需同步通知 FrontendTaskAgent。
- **共享类型对齐**: `BatchReviewRequest` / `BatchReviewResponse` 等类型应与 `SUO-201-SH-002` 的 Python 规范源保持一致。

## 12. 执行边界

### 允许修改范围
- `backend/routers/story-workspace.py` — 在 `SUO-201-BE-002` 已创建的 REST API 路由文件中追加审阅端点（confirm / reject / archive / batch）。
- `backend/database.py` — 如需新增 `story_workspace_audit_log` 审计日志表（可选，视现有系统能力）。
- `backend/tests/test_story_workspace_review.py` — **新文件**：审阅工作流的状态流转矩阵测试、批量操作测试、权限测试。

### 禁止修改范围
- ❌ `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` — 任何设计阶段产物。
- ❌ `docs/task/TASK-REQUIREMENT-FORMAT.md` — 提示词模板。
- ❌ 前端代码、前端 task 文件 — 不在本 Agent 职责范围内。
- ❌ `backend/routers/story-workspace.py` 中已有 CRUD 端点 — 仅追加审阅端点，不修改现有列表/详情/PATCH 逻辑。
- ❌ 现有 `claude-agent` 服务核心逻辑 — 本任务仅实现审阅状态流转，不修改 Agent SSE 流处理。
- ❌ 实现代码以外的任何文件 — 本 task 文档不是 execute 授权。

### 明确排除项（本期不在范围）
- **复杂画布编辑器** — 审阅操作仅针对数据表中的故事/角色/场景条目，不涉及画布/时间线可视化。
- **视频生成模块** — 审阅状态流转不涉及视频/镜头相关资源。
- **移动端适配** — 后端 API 不区分设备类型；但本期明确排除移动端/平板端适配需求，API 消费者假设为桌面端。
- **用户手动创建内容** — 审阅操作仅针对 `agent_generated=true` 的内容；用户手动创建的内容不在本期审阅工作流中（实际上本期不允许用户手动创建）。
- **实时协作** — 无并发编辑冲突解决机制；同一用户同一时间对同一资源的操作由 SQLite 文件级锁天然串行化。
- **四视角转面图** — 角色审阅不涉及多视角头像的审阅流程。
- **历史版本管理** — 确认/驳回/编辑不保留历史版本快照。
- **@提及系统** — 审阅备注为纯文本，不支持 @提及解析与通知。
- **计费/积分系统** — 审阅操作不触发积分消耗或计费逻辑。
- **驳回后自动触发 Agent 重新生成** — 本任务仅负责状态变更为 `rejected`，实际重新生成触发机制在后续迭代定义（设计稿 `[CLARIFICATION_NEEDED]`）。
- **已确认内容的下游执行** — 确认后内容仅暂存，后续执行流程（如 Deck 生成、发布）在后续迭代定义。
