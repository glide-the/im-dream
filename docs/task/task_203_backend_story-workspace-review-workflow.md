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
- 所有操作至少记录结构化审计日志；复用持久化审计能力仅在现有 Schema 已提供时可选，本 task 不新建或修改审计表
- 确认操作需记录 `confirmed_at` 时间戳
- 驳回操作需保存 `review_notes`

## 4. 实现步骤

### Step 1: 在 `backend/routers/story_workspace.py` 中追加审阅端点

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

### Step 6: 记录结构化审计信息（不修改 Schema）

每次审阅操作后记录以下结构化字段。当前仓库未提供可直接复用的 Story Workspace 持久化审计表，因此基线实现使用应用 logger；如果执行时已存在兼容的持久化 audit sink，只允许调用既有能力，不得在本 task 新增表、列、索引、migration 或初始化 DDL。

```python
def log_review_action(db, user_id: int, resource_type: str, resource_id: str,
                      action: str, previous_status: str, new_status: str,
                      review_notes: Optional[str] = None):
    """Log a review action for audit purposes."""
    logger.info(
        "story_workspace_review",
        extra={
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "previous_status": previous_status,
            "new_status": new_status,
            "has_review_notes": bool(review_notes),
        },
    )
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
| `rejected` | ❌ 400 | ❌ 400 | ✅ → archived |
| `archived` | ❌ 400 | ❌ 400 | ❌ 400 |

**注意**：
- `archive` 操作修改 `status` 字段（draft/published → archived），不影响 `review_status`
- 单条与批量 `confirm` / `reject` 都只允许当前 `review_status='pending'`；`rejected` 必须经独立的 Agent 重新生成流程产生新的 pending 版本，不得在本 task 直接再次 confirm
- 批量 `archive` 同样只处理请求集合中的 pending 项，以保持本 task 的“批量操作仅影响 pending”合同；单条 archive 可处理 pending / confirmed / rejected，但已 archived 返回 400

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/routers/story_workspace.py` | 追加审阅端点（在 `SUO-201-BE-002` 已交付的实际路由文件基础上扩展） |
| `backend/tests/test_story_workspace_review.py` | **新文件**：审阅工作流测试 |

**只读复用**：`backend/database.py` 的 `get_db()` 与既有 Schema；不得产生该文件 diff，不得新增 `story_workspace_audit_log` 或任何其他 DDL。

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
| `task_203a` / [SUO-317](/SUO/issues/SUO-317) | Character / Scene 审阅持久化 Schema 与 canonical contract | **硬依赖** | `task_203a` 的独立 execute 必须先完成四列迁移、contract tests 与 database hash 重冻结；仅完成 Task 定义文档不能解除依赖 |
| `SUO-201-SH-002` | 共享类型定义 | 软依赖 | 类型对齐，但可基于设计稿先行开发 |

**共享文件排他约束**：`task_204` 也会追加 `backend/routers/story_workspace.py`。这不是业务依赖，但属于 execute 写入冲突；按当前 Stage 顺序必须先完成 `task_204` 的共享路由变更及验证，再完成 `task_203a` 并由 StagePlanner 通过九项 readiness、重冻结 `backend/database.py` hash，之后才可开始 `task_203`。三者不得以共享 checkout 或并发写入绕过该 Gate；`task_203` 执行期间 database 与 canonical contract 均为只读冻结输入。

## 8. 测试策略

> §8.1～§8.6 的代码块用于固定行为断言；正式测试文件必须按 §8.7 的命名与仓库现有 `unittest.TestCase` 风格实现，并由所列命令实际发现和执行。

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

def test_batch_confirm_skips_non_pending(client, auth_headers, mixed_stories):
    """Test batch confirm skips non-pending items."""
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
cases = [
    ("pending", "confirm", "confirmed", 200),
    ("pending", "reject", "rejected", 200),
    ("confirmed", "confirm", None, 400),  # Already confirmed
    ("confirmed", "reject", None, 400),   # Cannot reject confirmed
    ("rejected", "confirm", None, 400),   # Must regenerate to a new pending version
    ("rejected", "reject", None, 400),    # Already rejected
]

# 在 unittest.TestCase 中以 subTest 遍历 cases；角色与场景复用同一矩阵。
for current_status, action, expected_status, expected_code in cases:
    with self.subTest(current_status=current_status, action=action):
        response = self.perform_review(current_status, action)
        self.assertEqual(response.status_code, expected_code)
        if expected_status:
            self.assertEqual(response.json()["review_status"], expected_status)
```

### 8.7 可执行命令与验收映射

从仓库根目录执行：

```bash
python -m py_compile backend/routers/story_workspace.py backend/tests/test_story_workspace_review.py
python -m unittest backend.tests.test_story_workspace_review -v
git diff --check -- backend/routers/story_workspace.py backend/tests/test_story_workspace_review.py
```

| 验收 ID | 验收条件 | 唯一对应测试/证据 |
|---|---|---|
| `AC-203-01` | story / character / scene 的 pending 项可 confirm/reject，confirm 写 `confirmed_at`，reject 保存最长 2000 字的 `review_notes` | `test_pending_confirm_and_reject_for_all_resource_types` |
| `AC-203-02` | confirmed / rejected / archived 均不可 confirm/reject；尤其 rejected → confirm 返回 400 | `test_non_pending_review_transition_matrix` |
| `AC-203-03` | 单条 story archive 对 pending/confirmed/rejected 可用、保留 `review_status`；重复 archive 返回 400 | `test_story_archive_matrix_preserves_review_status` |
| `AC-203-04` | batch 最多 100 项，只更新 pending，正确返回 `total_requested`、`total_updated`、`skipped_ids`、`updated_items` | `test_batch_pending_only_and_result_accounting` |
| `AC-203-05` | 未认证请求为 401；其他用户资源不可见/不可审阅（403 或 404，遵循现有基线） | `test_review_authentication_and_owner_isolation` |
| `AC-203-06` | 非法 action/resource_type、空 ids、超过 100 ids、超过 2000 字 review_notes 被拒绝且无部分写入 | `test_review_request_validation_is_atomic` |
| `AC-203-07` | 每次成功/拒绝操作记录结构化审计字段；不修改 `backend/database.py`，无 Schema diff | `test_review_action_emits_structured_audit_log` + 路径/diff 检查 |

测试文件采用仓库现有 `unittest` 风格；不得为了本 task 引入 pytest、修改依赖或从 `backend/` 目录执行会触发 `backend/types` 遮蔽 stdlib 的命令。

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
- [ ] `AC-203-01`～`AC-203-07` 均通过并在 execute report 中逐项回填证据
- [ ] 所有操作至少记录结构化审计日志；未新增审计表，`backend/database.py` 与 Schema 均无 diff
- [ ] 状态流转矩阵完整测试通过，`rejected -> confirm` 明确为 400
- [ ] 权限测试通过

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **状态流转非法操作** | 中 | 严格的校验矩阵；非法操作返回 400；数据库层使用 `WHERE review_status = 'pending'` 防止竞态条件 |
| **批量操作竞态条件** | 中 | 使用事务包裹批量更新；SQLite 文件级锁天然处理并发 |
| **驳回后重新生成流程未定义** | 高 | 设计稿标记 `[CLARIFICATION_NEEDED]`。默认假设：通过同一 Chat 线程重新生成。本任务仅负责状态变更，不负责触发重新生成 |
| **已确认内容的后续执行未定义** | 中 | 设计稿标记 `[CLARIFICATION_NEEDED]`。默认假设：暂存，后续迭代定义。本任务仅负责状态变更 |
| **持久化审计能力不存在** | 低 | 本 task 使用结构化应用日志并测试字段；持久化 audit sink 留给独立 Schema/审计任务，本 task 不修改 `backend/database.py` |
| **批量操作大量数据性能** | 低 | 限制 `ids` 最大 100 条；使用单条 `UPDATE ... WHERE id IN (...)` SQL |

## 11. 允许与禁止修改范围

- **仅允许修改**：`backend/routers/story_workspace.py`（只追加审阅端点/最小共享 helper）、`backend/tests/test_story_workspace_review.py`。
- **禁止修改**：`docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/`、前端代码、数据库 schema 定义文件。
- **禁止行为**：不得把本 task 文档当作 execute 授权直接实现；不得修改设计稿或 Issue 清单。

## 12. 下游执行提示

- **StagePlanner 注意**: 本任务依赖 `SUO-201-BE-002`（REST API）完成。审阅端点追加在实际文件 `backend/routers/story_workspace.py` 中，不是独立文件；并须与 `task_204` 对该共享文件的变更串行执行。
- **与前端协作点**: 前端审阅面板调用 `POST /.../confirm` 和 `POST /.../reject`。驳回时需传递 `review_notes`。批量操作时前端需收集选中项 ID 列表。
- **与 E2E 联调的关系**: `SUO-201-SH-001`（E2E 联调）依赖本任务完成。Stage 排期时需确保本任务在 E2E 之前完成。
- **数据合同稳定性**: `review_status` 枚举值（`pending` / `confirmed` / `rejected`）是前后端共享契约，变更需同步通知 FrontendTaskAgent。
- **共享类型对齐**: `BatchReviewRequest` / `BatchReviewResponse` 等类型应与 `SUO-201-SH-002` 的 Python 规范源保持一致。

## 12. 执行边界

### 允许修改范围
- `backend/routers/story_workspace.py` — 在 `SUO-201-BE-002` 已创建的 REST API 路由文件中追加审阅端点（confirm / reject / archive / batch）与本 task 私有的最小结构化日志 helper；不得改写已有 CRUD。
- `backend/tests/test_story_workspace_review.py` — **新文件**：审阅工作流的状态流转矩阵测试、批量操作测试、权限测试。

### 禁止修改范围
- ❌ `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` — 任何设计阶段产物。
- ❌ `docs/task/TASK-REQUIREMENT-FORMAT.md` — 提示词模板。
- ❌ 前端代码、前端 task 文件 — 不在本 Agent 职责范围内。
- ❌ `backend/routers/story_workspace.py` 中已有 CRUD 端点 — 仅追加审阅端点，不修改现有列表/详情/PATCH 逻辑。
- ❌ `backend/database.py` 与所有 Schema/migration — 仅允许读取并复用 `get_db()` 及既有表；不得新增/修改审计表、列、索引或初始化逻辑。
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

---

## 13. SUO-270 Execute Readiness Delta

### 准入项

- `SUO-264` 已交付并验证实际 `backend/routers/story_workspace.py`、11 条 Story Workspace 路由及 focused API tests；task_203 的 REST 基线硬依赖已满足。
- 仓库现有根目录 `unittest` 运行方式可复用，避免 `backend/types` 对 stdlib `types` 的已知遮蔽问题。

### 本次修正项

- 全文将不存在的连字符版路由路径归一为实际下划线路径 `backend/routers/story_workspace.py`。
- 将 rejected → confirm 统一为 400，并明确单条 archive 与 pending-only batch 的边界。
- 从写入闭集移除 `backend/database.py`；审计采用结构化日志，持久化审计与 Schema 变更留给独立任务。
- 建立 `AC-203-01`～`AC-203-07` 与单一测试/证据的一一映射及可执行命令。

### 仍阻塞项

- **task 文档自身：无。**
- **执行串行 Gate**：`task_204` 与本 task 共享 `backend/routers/story_workspace.py`；按当前 Stage 的 Wave 2 → Wave 3 顺序，`task_204` 未完成前本 task 不得启动。
- **StagePlanner 后续**：Stage §3/§7/§8/回滚文字仍使用连字符版 Python 路由路径，并未显式标注共享路由排他关系，且旧矩阵未表达 `backend/database.py` 只读边界；须由独立 StagePlanner 子单同步。本 Issue 不修改 Stage。
