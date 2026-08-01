# task_230_backend_review-gate-aggregation.md

> **Task ID**: `task_230`  
> **关联 Issue**: `SUO-230-BE-001` — `审阅 gate 服务端聚合与防绕过验证`  
> **上游 Issue**: `SUO-230` (Issue 清单 §2.3 / §3.3)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-018`, `DEC-010`, `DEC-014`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `TaskDesignAgent`  
> **增量来源**: `SUO-232` 传播 → `SUO-234` task 阶段

---

## 1. 任务标题

Story Workspace 审阅 Gate 服务端聚合与防绕过验证

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-230-BE-001` | 审阅 gate 服务端聚合与防绕过验证 | backend | P0 |

---

## 3. 任务目标

实现服务端审阅 gate 聚合校验与防绕过机制。以 `workflow_run_id` 为维度聚合全部必审故事、角色、场景的审阅状态；任一项为 `pending` 或 `rejected` 时，拒绝继续/结束请求。确认动作必须校验运行 ID 与审阅版本，拒绝过期版本。确认后继续/结束必须幂等。

**核心约束**：
- 这是安全关键任务；客户端 UI 锁定不能替代服务端校验
- `pending_review` 为 canonical 运行状态；不新增第二个 API 枚举
- 确认幂等通过数据库唯一约束或分布式锁实现
- 客户端直接请求继续/结束时，服务端以聚合审阅状态拒绝未全部确认的请求
- 若内容已确认但后续继续失败，确认事实不回滚；页面进入失败态，幂等重试继续动作

---

## 4. 实现步骤

### Step 1: 实现审阅状态聚合查询

**聚合查询接口**：
```python
GET /api/story-workspace/workflow-runs/:id/review-gate
```

**响应**：
```json
{
  "workflow_run_id": "run-uuid",
  "gate_status": "locked" | "unlocked",
  "required_reviews": 12,
  "confirmed_reviews": 8,
  "pending_reviews": 3,
  "rejected_reviews": 1,
  "items": [
    {
      "id": "story-uuid",
      "type": "story",
      "title": "午夜咖啡馆",
      "review_status": "pending",
      "review_version": "v1"
    }
  ]
}
```

**聚合逻辑**：
1. 根据 `workflow_run_id` 查询关联的全部 story、character、scene
2. 统计各审阅状态数量
3. Gate 判定：
   - `locked`: 任一必审项为 `pending` 或 `rejected`
   - `unlocked`: 全部必审项为 `confirmed`

### Step 2: 实现确认 API 版本校验

**确认端点增强**：
```python
POST /api/story-workspace/stories/:id/confirm
# 请求体增强
{
  "workflow_run_id": "run-uuid",
  "review_version": "v1"  # ← 新增：审阅版本校验
}
```

**服务端校验逻辑**：
1. 验证 `workflow_run_id` 与 story 的 `workflow_run_id` 匹配
2. 验证 `review_version` 未过期（与当前数据库版本一致）
3. 验证 story 当前 `review_status` 为 `pending`
4. 更新 `review_status` → `confirmed`，记录 `confirmed_at`
5. 返回更新后的 story 对象

**版本过期拒绝**：
- 若 `review_version` 与数据库不一致 → 返回 `409 CONFLICT`
- 错误码：`REVIEW_VERSION_EXPIRED`
- 错误消息："内容已更新，请刷新后重新审阅"

### Step 3: 实现继续/结束 API 与幂等控制

**继续/结束端点**：
```python
POST /api/story-workspace/workflow-runs/:id/continue
# 请求体
{
  "action": "continue" | "complete"
}
```

**服务端校验逻辑**：
1. 验证 `workflow_run_id` 存在且状态为 `confirmed`（全部必审项已确认）
2. 聚合查询：该 run 的全部必审项是否均为 `confirmed`
3. 若任一项为 `pending` 或 `rejected` → 返回 `403 FORBIDDEN`
4. 若全部确认 → 执行继续/结束动作

**幂等控制**：
- 使用数据库唯一约束：`UNIQUE(workflow_run_id, action)` 在 `workflow_run_continuations` 表
- 或使用分布式锁（Redis / 数据库行锁）
- 首次合法请求：执行继续/结束，记录 `continued_at`
- 重复请求：返回 `200 OK` + 已执行状态（幂等）
- 错误码：`CONTINUATION_ALREADY_EXECUTED`

### Step 4: 实现防绕过验证

**防绕过规则**：
1. 客户端直接调用 `POST /api/story-workspace/workflow-runs/:id/continue` 时，服务端必须执行聚合校验
2. 不得仅凭请求参数中的 `gate_status` 判断
3. 不得信任客户端发送的 "已确认" 标记
4. 每次继续/结束请求都必须重新查询数据库中的最新审阅状态

**驳回处理**：
- 驳回 API 保持基线行为：`POST /api/story-workspace/stories/:id/reject`
- 驳回后记录 `review_notes`，状态变为 `rejected`
- 驳回不触发继续/结束；gate 保持锁定
- 重新生成创建新 run attempt，默认沿用原锁定快照

### Step 5: 失败恢复

**已确认但继续失败**：
1. 确认事实不回滚（`review_status` 保持 `confirmed`）
2. `workflow_run` 状态变为 `failed`，记录 `error_code` + `failed_step`
3. 前端进入 `story-workspace-failed` 状态
4. 用户可幂等重试继续动作（同一 `workflow_run_id`）

---

## 5. 涉及文件路径

**新增文件**：
- `backend/src/routes/story-workspace/review-gate.ts`（或等效路径）— 审阅 gate 路由
- `backend/src/services/story-workspace/review-gate.service.ts` — 聚合校验服务

**修改文件**（增量适配）：
- `backend/src/routes/story-workspace/review.ts`（或等效路径）— 确认端点增强版本校验
- `backend/src/services/story-workspace/workflow-run.service.ts` — 追加继续/结束幂等控制

**复用文件**（只读）：
- `backend/src/routes/story-workspace/stories.ts` — 基线故事路由（`task_202`）
- `backend/src/services/story-workspace/review.service.ts` — 基线审阅服务（`task_203`）

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §3.6.2 Gate 规则
- 布局设计稿 §2.4.3 Gate 状态与不可绕过规则
- Issue 清单 §3.3 `SUO-230-BE-001` 明细
- 既有 `task_202_backend_story-workspace-rest-api.md` 的 REST API 基线
- 既有 `task_203_backend_story-workspace-review-workflow.md` 的审阅状态流转基线

**输出**：
- 审阅 gate 聚合查询 API：`GET /api/story-workspace/workflow-runs/:id/review-gate`
- 增强确认 API：追加 `workflow_run_id` + `review_version` 校验
- 继续/结束 API：`POST /api/story-workspace/workflow-runs/:id/continue`（带幂等控制）
- 防绕过验证逻辑：每次继续/结束请求重新聚合校验

---

## 7. 依赖项

| 依赖 | Issue ID | 状态 | 说明 |
|---|---|---|---|
| `task_201` (BE-001 数据库 Schema) | `SUO-201-BE-001` | ✅ 基线稳定 | 提供数据表 |
| `task_202` (BE-002 REST API) | `SUO-201-BE-002` | ✅ 基线稳定 | 提供 REST API 基线；本任务增强 confirm 端点 |
| `task_203` (BE-003 审阅状态流转) | `SUO-201-BE-003` | ✅ 基线稳定 | 提供审阅状态流转基线；本任务追加 gate 聚合 |
| `task_226_backend_workflow-binding-run-schema` | `SUO-226-BE-001` | ⏳ 需先完成 | 提供 workflow_run 数据模型 |
| `task_226_backend_workflow-run-api` | `SUO-226-BE-004` | ⏳ 需先完成 | 提供 run 创建与管理 API |
| `task_205` (SH-002 共享类型) | `SUO-201-SH-002` | ✅ 基线稳定 | 提供类型定义基线 |

**本任务被依赖**：
- `task_230_shared_idempotency-e2e.md` — E2E 测试需要服务端聚合 API

---

## 8. 测试策略

1. **聚合查询测试**：
   ```python
   def test_review_gate_aggregation(client, auth_headers, workflow_run_with_items):
       """Test review gate aggregates all required items."""
       response = client.get(
           f"/api/story-workspace/workflow-runs/{workflow_run_id}/review-gate",
           headers=auth_headers
       )
       assert response.status_code == 200
       data = response.json()
       assert data["gate_status"] == "locked"  # 部分 pending
       assert data["required_reviews"] == 3
       assert data["pending_reviews"] == 1
   ```

2. **版本校验测试**：
   ```python
   def test_confirm_with_expired_version(client, auth_headers, story):
       """Test confirm with expired review version is rejected."""
       response = client.post(
           f"/api/story-workspace/stories/{story['id']}/confirm",
           json={"workflow_run_id": "run-uuid", "review_version": "expired-v1"},
           headers=auth_headers
       )
       assert response.status_code == 409
       assert response.json()["error_code"] == "REVIEW_VERSION_EXPIRED"
   ```

3. **防绕过测试**：
   ```python
   def test_continue_with_pending_items(client, auth_headers, workflow_run):
       """Test continue request is rejected when items are pending."""
       response = client.post(
           f"/api/story-workspace/workflow-runs/{workflow_run['id']}/continue",
           json={"action": "continue"},
           headers=auth_headers
       )
       assert response.status_code == 403
       assert response.json()["error_code"] == "REVIEW_GATE_LOCKED"
   ```

4. **幂等测试**：
   ```python
   def test_continue_idempotency(client, auth_headers, confirmed_workflow_run):
       """Test continue request is idempotent."""
       # First request
       r1 = client.post(...)
       assert r1.status_code == 200
       # Second request (same run)
       r2 = client.post(...)
       assert r2.status_code == 200
       assert r2.json()["status"] == "already_executed"
   ```

5. **失败恢复测试**：
   ```python
   def test_confirmed_but_continue_failed(client, auth_headers, confirmed_run):
       """Test confirmed status is not rolled back on continue failure."""
       # Mock continue failure
       response = client.post(...)
       assert response.status_code == 500
       # Verify story status remains confirmed
       story = client.get(f"/api/story-workspace/stories/{story_id}")
       assert story.json()["review_status"] == "confirmed"
   ```

---

## 9. 完成标志

- [ ] 服务端聚合查询：给定 `workflow_run_id`，返回全部关联 story/character/scene 的审阅状态
- [ ] Gate 判定逻辑：任一项 `pending` 或 `rejected` → gate 锁定；全部 `confirmed` → gate 解锁
- [ ] 确认 API (`POST /api/story-workspace/stories/:id/confirm`) 必须接收 `workflow_run_id` + `review_version`
- [ ] 服务端校验：运行 ID 匹配且审阅版本未过期才允许确认
- [ ] 确认后继续/结束 API 必须幂等：首次合法确认后只发出一次信号
- [ ] 重复点击、刷新或网络重试不得重复推进
- [ ] 客户端直接请求继续/结束时，服务端以聚合审阅状态拒绝未全部确认的请求
- [ ] 驳回只记录意见并保持锁定；重新生成创建新 run attempt
- [ ] 若内容已确认但后续继续失败，确认事实不回滚；页面进入失败态，幂等重试继续
- [ ] `pending_review` 为 canonical 运行状态；不新增第二个 API 枚举
- [ ] 确认幂等通过数据库唯一约束或分布式锁实现

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| `workflow_run` 数据模型尚未完成（SUO-226） | 高 | 接口设计需与 SUO-226 数据模型对齐；可先定义接口草案 |
| 聚合查询性能（大量 story/character/scene） | 中 | 使用数据库索引（`idx_stories_workflow_run`）；必要时缓存聚合结果 |
| 幂等实现复杂度 | 中 | 使用数据库唯一约束实现，避免引入分布式锁复杂度 |
| 版本校验增加 API 复杂度 | 低 | `review_version` 使用简单版本号（如 `updated_at` 时间戳或整数版本） |
| 客户端绕过风险 | 高 | 所有继续/结束请求必须经过服务端聚合校验；不信任客户端任何状态标记 |

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- 审阅 gate 聚合查询 API
- Gate 判定逻辑（锁定/解锁）
- 确认 API 版本校验
- 继续/结束 API 幂等控制
- 防绕过验证（服务端聚合校验）
- 失败恢复（确认不回滚）

**❌ 范围外**（本 task 不实现）：
- Workflow Run 数据模型（由 `task_226_backend_workflow-binding-run-schema` 定义）
- Workflow Run 创建/管理 API（由 `task_226_backend_workflow-run-api` 定义）
- Agent 集成适配（由 `task_226_backend_agent-deck-desk-adapter` 定义）
- Deck 插件目录 API（由 `task_226_backend_deck-plugin-directory-api` 定义）
- Desk 配置预检 API（由 `task_226_backend_desk-preflight-api` 定义）
- 前端 ReviewGate 组件（由 `task_230_frontend_dream-page-review-gate` 定义）
- 前端路由和导航（由 `task_230_frontend_dream-nav-item` 定义）

---

## 执行边界

### 允许修改范围
- 允许创建 `backend/src/routes/story-workspace/review-gate.ts`（或等效路径）
- 允许创建 `backend/src/services/story-workspace/review-gate.service.ts`
- 允许修改确认端点（追加 `workflow_run_id` + `review_version` 校验）
- 允许修改 workflow-run 服务（追加继续/结束幂等控制）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件（除本任务指定的 4 份同步更新外）
- **禁止修改** 前端代码
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`
- **禁止修改** 数据库 schema 定义（Schema 在 `task_201` 中完成，本任务仅复用）
- **禁止修改** 现有 `claude-agent` 服务（SSE 流、thread 生命周期）

### 明确排除项
- **复杂画布**：API 仅提供结构化数据的聚合查询，不提供画布/可视化数据端点
- **视频**：API 不包含视频/镜头相关资源端点
- **移动端**：后端 API 不假设移动端消费者
- **实时协作**：无 WebSocket/Socket.io 实时推送端点
- **计费/积分**：API 调用不触发积分消耗记录
- **DELETE 端点**：本期不提供物理删除
- **文件上传**：角色头像为外部 URL，本 API 不提供文件上传端点

---

## 增量差异说明

### 与既有 `task_202_backend_story-workspace-rest-api.md` 的关系

| 维度 | `task_202` REST API 基线 | 本 `task_230` 增量 |
|---|---|---|
| 确认端点 | `POST /stories/:id/confirm`（无版本校验） | 追加 `workflow_run_id` + `review_version` 参数校验 |
| 聚合查询 | 无 | 新增 `GET /workflow-runs/:id/review-gate` |
| 继续/结束 | 无 | 新增 `POST /workflow-runs/:id/continue`（幂等） |
| 防绕过 | 无 | 所有继续/结束请求必须服务端聚合校验 |

**无冲突声明**：本增量不修改 `task_202` 的 CRUD 端点、分页逻辑、搜索筛选。仅在 confirm 端点追加参数校验，并新增 gate 聚合和继续端点。

### 与既有 `task_203_backend_story-workspace-review-workflow.md` 的关系

| 维度 | `task_203` 审阅状态流转基线 | 本 `task_230` 增量 |
|---|---|---|
| 状态流转 | `pending → confirmed/rejected` | 追加运行级 gate 聚合判断 |
| 批量操作 | 基线批量 confirm/reject | 批量操作需校验同一 `workflow_run_id` |
| 确认后动作 | 无 | 追加继续/结束幂等控制 |

**无冲突声明**：本增量在 `task_203` 的状态流转基础上追加 gate 聚合层，不修改状态枚举、不修改批量操作基线逻辑。
