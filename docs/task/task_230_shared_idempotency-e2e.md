# Task: Story Workspace 确认幂等与审阅版本校验 E2E 联调（Shared）

> **Task ID**: `task_230_shared_idempotency-e2e`  
> **关联 Issue**: `SUO-230-SH-001` — `确认幂等与审阅版本校验联调`  
> **上游 Issue**: `SUO-230` (Issue 清单 §2.3 / §3.3)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-017`, `DEC-018`, `DEC-010`, `DEC-014`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `TaskDesignAgent`  
> **增量来源**: `SUO-232` 传播 → `SUO-234` task 阶段

---

## 1. 任务标题

SUO-230-SH-001: Story Workspace 审阅 Gate 确认幂等、版本校验与防绕过 E2E 联调（Shared）

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-230-SH-001` | 确认幂等与审阅版本校验联调 | shared | P0 |
| `SUO-230-FE-002` | Dream 页面与 ReviewGate 组件 | frontend | P0 |
| `SUO-230-BE-001` | 审阅 gate 服务端聚合与防绕过验证 | backend | P0 |
| `SUO-201-SH-001` | 前端-后端联调：审阅工作流 E2E | shared | P0 |
| `SUO-226-SH-002` | 端到端工作流集成 E2E（Deck→Desk→Agent→审阅） | shared | P0 |

---

## 3. 任务目标

端到端验证 Story Workspace Dream 页面的审阅 Gate 在确认幂等、审阅版本校验、客户端绕过防护三个安全关键维度上的行为一致性。确保前端 `StoryWorkspaceReviewGate` / `StoryWorkspaceReviewPanel` 与后端审阅 gate 聚合服务、继续/结束幂等控制协同工作，不因 UI 状态、网络重试或恶意请求导致重复推进工作流。

**核心约束**：
- 前端是「体验层」，后端是「权威层」；所有放行/阻断判定以服务端聚合状态为准。
- 确认幂等必须在网络超时、快速重试、页面刷新等场景下保持一致。
- 审阅版本校验必须阻止对过期 Agent 产出的确认。
- 客户端绕过尝试（直接调用 continue API）必须被服务端拒绝。
- E2E 测试必须可自动化、可重复运行，不依赖人工干预。

---

## 4. 实现步骤

### 步骤 1：定义 E2E 测试范围与入口

1.1 确定测试入口：
- 以 `/story-workspace/dream` 为起点，覆盖 Dream 导航 → Dream 页面 → ReviewGate → Review Panel → 确认/驳回 → 继续/结束 完整链路。
- 同时覆盖客户端绕过路径：直接调用 `POST /api/story-workspace/workflow-runs/:id/continue`。

1.2 确定测试数据准备：
- 使用测试固件（fixture）创建包含多个 story/character/scene 的 `workflow_run`。
- 各产出项初始审阅状态为 `pending`。
- 为每个产出项分配初始 `review_version`（如 `v1`）。

### 步骤 2：实现幂等确认流程 E2E 测试

2.1 正常确认路径：
- 打开 Dream 页面，ReviewGate 显示「用户审阅」高亮，继续/结束按钮禁用。
- 在 Review Panel 中逐个确认 story/character/scene。
- 每次确认请求携带 `workflow_run_id` + `review_version`。
- 全部确认后，ReviewGate 解锁，继续/结束按钮启用。

2.2 重复确认幂等：
- 对同一已确认产出项再次发送确认请求。
- 期望：服务端返回已确认状态（`200 OK` + 当前状态），不创建新的确认事件、不推进工作流。
- 前端展示保持稳定，不闪烁或重复 Toast。

2.3 网络重试幂等：
- 模拟第一次确认请求网络超时（前端发起但未收到响应）。
- 前端自动重试相同请求（相同 `idempotency_key`）。
- 期望：服务端识别为重复请求，返回已处理状态，不重复确认。

### 步骤 3：实现审阅版本校验 E2E 测试

3.1 过期版本拒绝：
- 在 Review Panel 中打开待审阅 story，记录当前 `review_version`。
- 触发 Agent 重新生成（模拟驳回后重新生成），产生新 run attempt，story 的 `review_version` 更新为 `v2`。
- 使用旧版本 `v1` 发送确认请求（模拟前端缓存未刷新或恶意请求）。
- 期望：服务端返回 `409 CONFLICT`，错误码 `REVIEW_VERSION_EXPIRED`。
- 前端提示：「内容已更新，请刷新后重新审阅」。

3.2 版本刷新后正常确认：
- 前端刷新 Review Panel，获取最新 `review_version`。
- 使用新版本 `v2` 发送确认请求。
- 期望：确认成功，状态变为 `confirmed`。

### 步骤 4：实现防绕过 E2E 测试

4.1 客户端直接调用 continue API：
- 创建一个仍有 `pending` 产出项的 workflow run。
- 不经过 UI 确认，直接发送 `POST /api/story-workspace/workflow-runs/:id/continue`。
- 期望：服务端返回 `403 FORBIDDEN`，错误码 `REVIEW_GATE_LOCKED`。

4.2 部分确认后绕过：
- 确认部分（而非全部）产出项。
- 直接调用 continue API。
- 期望：服务端仍以聚合状态拒绝。

4.3 驳回后绕过：
- 驳回任一必审产出项。
- 直接调用 continue API。
- 期望：服务端返回 `403 FORBIDDEN`。

### 步骤 5：实现 Gate 解锁与单次放行 E2E 测试

5.1 全部确认后放行：
- 全部 story/character/scene 确认后，ReviewGate 显示第四步解锁。
- 点击「继续」或「结束」。
- 期望：请求成功，`workflow_run` 状态流转为 `continuing`/`completed`。

5.2 继续请求幂等：
- 在第一次继续请求成功后，再次发送相同 continue 请求。
- 期望：服务端返回 `200 OK` + `already_executed`，不重复执行工作流。

5.3 已确认但继续失败：
- 全部确认后，模拟继续动作失败（如 Agent 服务不可用）。
- 期望：产出项的 `confirmed` 状态不回滚，`workflow_run` 进入 `failed` 状态。
- 用户可点击「重试继续」，使用同一 `workflow_run_id` 幂等重试。

### 步骤 6：实现驳回后重新生成 E2E 测试

6.1 驳回路径：
- 驳回 story，填写修改意见。
- ReviewGate 进入红色阻断状态，继续/结束按钮禁用。

6.2 重新生成：
- 点击「沿原快照重新生成」。
- 期望：创建新 run attempt，默认沿用原 `deck_plugin_id` + `deck_plugin_version` + `desk_config_snapshot_id`。
- 新 run 的产出项具有新的 `workflow_run_id` 和 `review_version`。
- 旧 run 的驳回记录保留，不被覆盖。

### 步骤 7：E2E 测试基础设施

7.1 前端测试工具：
- 使用 Playwright / Cypress（项目现有 E2E 框架）。
- 提供测试辅助函数：
  - `createWorkflowRunFixture()` — 创建测试 run
  - `confirmItem(itemId, version)` — 确认产出项
  - `rejectItem(itemId, notes)` — 驳回产出项
  - `callContinueApi(runId, action)` — 直接调用 continue API 用于绕过测试

7.2 后端测试支持：
- 提供测试专用接口或 seed 脚本，用于创建可控的 workflow run 和产出项。
- 确保测试数据隔离，不影响其他测试。

7.3 断言重点：
- Gate 状态与按钮启用/禁用状态一致。
- API 响应码与错误码符合预期。
- 数据库状态（review_status、continuation 记录）幂等稳定。

---

## 5. 涉及文件路径

### 新增 E2E 测试文件

```
e2e/tests/story-workspace/
  review-gate-idempotency.spec.ts      -- 幂等确认与版本校验 E2E
  review-gate-bypass.spec.ts           -- 防绕过 E2E
  review-gate-lifecycle.spec.ts        -- Gate 解锁、继续、驳回重生成 E2E
  fixtures/
    workflow-run.fixture.ts            -- 测试数据固件
    review-items.fixture.ts            -- 产出项固件
  helpers/
    review-api.helper.ts               -- API 直接调用辅助
    gate-state.helper.ts               -- Gate UI 状态断言辅助
```

### 前端被测文件（只读引用）

```
frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx
frontend/src/components/story-workspace/review/StoryWorkspaceReviewGate.tsx
frontend/src/components/story-workspace/review/StoryWorkspaceReviewPanel.tsx
frontend/src/components/story-workspace/review/StoryWorkspaceReviewActions.tsx
frontend/src/hooks/story-workspace/useStoryWorkspaceStore.ts
```

### 后端被测文件（只读引用）

```
backend/src/routes/story-workspace/review-gate.ts
backend/src/services/story-workspace/review-gate.service.ts
backend/src/services/story-workspace/workflow-run.service.ts
backend/src/routes/story-workspace/review.ts
```

---

## 6. 输入 / 输出说明

### 输入

| 来源 | 内容 | 格式 |
|---|---|---|
| 前端 UI | ReviewGate 状态、按钮启用/禁用 | React 组件状态 |
| 前端 API | `PUT /api/story-workspace/stories/:id/confirm`（带 `workflow_run_id` + `review_version`） | JSON |
| 后端 API | `GET /api/story-workspace/workflow-runs/:id/review-gate` | JSON |
| 后端 API | `POST /api/story-workspace/workflow-runs/:id/continue` | JSON |
| 测试固件 | 预创建 workflow run + story/character/scene | 数据库 seed |

### 输出

| 去向 | 内容 | 格式 |
|---|---|---|
| E2E 测试报告 | 幂等、版本校验、防绕过测试结果 | Playwright/Cypress 报告 |
| 缺陷记录 | 前后端行为不一致项 | Issue 评论 / 缺陷单 |
| 联调结论 | 验收通过/阻塞项 | SUO-230-SH-001 评论 |

### 关键 API 合同

**确认请求（前端 → 后端）**
```jsonc
{
  "workflow_run_id": "run-uuid",
  "review_version": "v1"
}
```

**继续请求（直接绕过测试用）**
```jsonc
POST /api/story-workspace/workflow-runs/:id/continue
{
  "action": "continue" | "complete"
}
```

**过期版本响应**
```jsonc
{
  "status": 409,
  "error_code": "REVIEW_VERSION_EXPIRED",
  "message": "内容已更新，请刷新后重新审阅"
}
```

**Gate 锁定响应**
```jsonc
{
  "status": 403,
  "error_code": "REVIEW_GATE_LOCKED",
  "message": "存在未审阅或已驳回的产出项"
}
```

---

## 7. 依赖项

| 依赖 | Issue ID | 状态 | 说明 |
|---|---|---|---|
| `task_230_frontend_dream-nav-item` | `SUO-230-FE-001` | ✅ 已产出 | 提供 Dream 导航与 canonical 路由入口 |
| `task_230_frontend_dream-page-review-gate` | `SUO-230-FE-002` | ✅ 已产出 | 提供 ReviewGate / ReviewPanel UI 与状态 |
| `task_230_backend_review-gate-aggregation` | `SUO-230-BE-001` | ✅ 已产出 | 提供审阅聚合、版本校验、继续幂等 API |
| `task_202d_frontend_review-panel` | `SUO-201-FE-004` | ✅ 基线稳定 | 审阅面板基线 |
| `task_202_backend_story-workspace-rest-api` | `SUO-201-BE-002` | ✅ 基线稳定 | REST API 基线 |
| `task_203_backend_story-workspace-review-workflow` | `SUO-201-BE-003` | ✅ 基线稳定 | 审阅状态流转基线 |
| `task_226_backend_workflow-binding-run-schema` | `SUO-226-BE-001` | ⏳ 需先完成 | workflow_run 数据模型 |
| `task_226_backend_workflow-run-api` | `SUO-226-BE-004` | ⏳ 需先完成 | run 创建与管理 API |
| `task_226_frontend_workflow-context-bar` | `SUO-226-FE-001` | ⏳ 需先完成 | 工作流上下文条（可用占位组件先行联调） |

**本任务被依赖**：
- 无直接下游；是 SUO-230 增量家族的 shared 收口验证。

---

## 8. 测试策略

### 8.1 幂等确认测试

```typescript
// 伪代码示例
test('重复确认同一产出项保持幂等', async ({ page, api }) => {
  const run = await createWorkflowRunFixture({ pendingStories: 1 });
  await page.goto(`/story-workspace/dream?run=${run.id}`);

  const story = run.items[0];
  const r1 = await api.confirm(story.id, story.review_version);
  expect(r1.status).toBe(200);

  const r2 = await api.confirm(story.id, story.review_version);
  expect(r2.status).toBe(200);
  expect(r2.data.review_status).toBe('confirmed');
  // 数据库只应有一条确认记录
  expect(await db.countConfirmEvents(story.id)).toBe(1);
});
```

### 8.2 审阅版本校验测试

```typescript
test('过期 review_version 被拒绝', async ({ page, api }) => {
  const run = await createWorkflowRunFixture({ pendingStories: 1 });
  const story = run.items[0];

  // 模拟重新生成，版本变为 v2
  await api.triggerRegeneration(run.id, story.id);

  // 使用旧版本 v1 确认
  const response = await api.confirm(story.id, 'v1');
  expect(response.status).toBe(409);
  expect(response.data.error_code).toBe('REVIEW_VERSION_EXPIRED');
});
```

### 8.3 防绕过测试

```typescript
test('部分确认时直接调用 continue API 被拒绝', async ({ api }) => {
  const run = await createWorkflowRunFixture({
    pendingStories: 2,
    confirmedStories: 1,
  });

  const response = await api.continue(run.id, 'continue');
  expect(response.status).toBe(403);
  expect(response.data.error_code).toBe('REVIEW_GATE_LOCKED');
});
```

### 8.4 Gate 解锁与单次放行测试

```typescript
test('全部确认后继续请求幂等', async ({ page, api }) => {
  const run = await createWorkflowRunFixture({ confirmedStories: 3 });

  const r1 = await api.continue(run.id, 'continue');
  expect(r1.status).toBe(200);

  const r2 = await api.continue(run.id, 'continue');
  expect(r2.status).toBe(200);
  expect(r2.data.status).toBe('already_executed');
});
```

### 8.5 失败恢复测试

```typescript
test('已确认但继续失败时不回滚确认状态', async ({ page, api }) => {
  const run = await createWorkflowRunFixture({ confirmedStories: 3 });
  await api.mockAgentFailure(run.id);

  const response = await api.continue(run.id, 'continue');
  expect(response.status).toBe(500);

  // 确认状态保持不变
  for (const item of run.items) {
    expect(await db.getReviewStatus(item.id)).toBe('confirmed');
  }
});
```

---

## 9. 完成标志

- [ ] E2E 测试覆盖正常确认 → Gate 解锁 → 继续/结束完整链路
- [ ] 重复确认幂等：数据库只产生一次确认记录，UI 不重复提示
- [ ] 网络超时重试幂等：前端自动重试不导致重复确认
- [ ] 过期 `review_version` 被拒绝，前端展示明确刷新提示
- [ ] 客户端直接调用 continue API 在 Gate 未解锁时被拒绝
- [ ] 部分确认、驳回后 continue API 均被拒绝
- [ ] 全部确认后继续/结束请求幂等：重复请求返回 `already_executed`
- [ ] 已确认但继续失败时，确认状态不回滚，可幂等重试继续
- [ ] 驳回后重新生成创建新 run attempt，沿用原快照版本
- [ ] 切换工作流插件后创建新 run，历史产出确认状态不受影响
- [ ] 所有 E2E 测试可在 CI 中稳定运行
- [ ] 前后端行为不一致项已记录并指派修复 owner

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| `workflow_run` 数据模型尚未完成（SUO-226） | 高 | 使用 mock run service 或测试 seed 先行编写测试；模型完成后切换真实 API |
| 前端 ReviewGate 与 Review Panel 状态同步复杂 | 中 | E2E 测试同时断言 UI 状态和 API 响应，捕获状态漂移 |
| 幂等测试依赖精确时间控制 | 中 | 使用测试时钟或数据库断言，避免 flaky |
| Agent 重新生成难以在 E2E 中稳定触发 | 中 | 通过 API 直接修改 `review_version` 模拟重新生成，不依赖真实 Agent |
| 绕过测试需要直接调用 API | 低 | 在 E2E helper 中封装，避免测试代码冗余 |
| 多产出项场景数据准备复杂 | 低 | 使用 fixture factory 批量创建 story/character/scene |

---

## 11. 范围边界

### ✅ 范围内

- Dream 页面 → ReviewGate → ReviewPanel → 后端审阅 API 的端到端验证
- 确认幂等（重复确认、网络重试）
- 审阅版本过期校验
- 客户端绕过 continue API 的防护验证
- Gate 解锁与继续/结束幂等
- 驳回后重新生成与版本锁定验证

### ❌ 范围外

- `StoryWorkspaceDreamPage` 页面实现（由 `task_230_frontend_dream-page-review-gate.md` 负责）
- `StoryWorkspaceReviewGate` 组件实现（同上）
- 审阅 gate 服务端聚合 API 实现（由 `task_230_backend_review-gate-aggregation.md` 负责）
- workflow_run 数据模型实现（由 `task_226_backend_workflow-binding-run-schema.md` 负责）
- Deck/Desk 端到端集成（由 `task_226-SH-002` 负责）
- 单元测试（本任务专注 E2E）

---

## 12. 执行边界

### 允许修改范围

- `e2e/tests/story-workspace/` 目录（新建 E2E 测试文件）
- `e2e/fixtures/` 或等效测试固件目录
- `e2e/helpers/` 测试辅助函数
- CI E2E 配置中添加本任务测试路径

### 禁止修改范围

- **禁止修改** `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`
- **禁止修改** `docs/task/` 下其他 task 文件
- **禁止修改** 前端/后端实现代码（本阶段为 E2E task 规划，非 execute）
- **禁止修改** 共享类型包基线

---

## 13. 与相关 Task 的协作边界

| 内容 | `task_230_frontend_dream-page-review-gate` | `task_230_backend_review-gate-aggregation` | 本 task |
|---|---|---|---|
| ReviewGate UI | 负责实现 | 不直接涉及 | 负责验证 |
| 审阅聚合 API | 消费合同 | 负责实现 | 负责验证 |
| 确认幂等 | 前端按钮防重 + 错误提示 | 服务端幂等控制 | 端到端断言 |
| 版本校验 | 前端传递版本 + 过期提示 | 服务端校验版本 | 端到端断言 |
| 防绕过 | UI 锁定按钮 | 服务端聚合拒绝 | 端到端断言 |
| continue 幂等 | UI 单次触发 | 服务端幂等控制 | 端到端断言 |

---

## 14. 增量差异说明

### 与 `SUO-201-SH-001`（基线审阅 E2E）的关系

| 维度 | `SUO-201-SH-001` 基线 | 本 `SUO-230-SH-001` 增量 |
|---|---|---|
| 验证范围 | 单个产出项 confirm/reject | 运行级 gate 聚合、幂等、版本校验、防绕过 |
| 入口 | 故事列表 → Review Panel | Dream 页面 → ReviewGate → Review Panel |
| 状态机 | `pending → confirmed/rejected` | 增加 `confirmed → continuing/completed/failed` |
| 安全维度 | 基础权限 | 客户端绕过防护、过期版本拒绝 |

**无冲突声明**：本增量在基线审阅 E2E 之上追加运行级 gate 验证，不推翻基线单个产出项的审阅流程。
