# task_230_frontend_dream-page-review-gate.md

> **Task ID**: `task_230`  
> **关联 Issue**: `SUO-230-FE-002` — `Dream 页面与 ReviewGate 组件`  
> **上游 Issue**: `SUO-230` (Issue 清单 §2.3 / §3.3)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-017`, `DEC-018`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `TaskDesignAgent`  
> **增量来源**: `SUO-232` 传播 → `SUO-234` task 阶段

---

## 1. 任务标题

Story Workspace Dream 页面（`StoryWorkspaceDreamPage`）与审阅 Gate（`StoryWorkspaceReviewGate`）组件实现

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-230-FE-002` | Dream 页面与 ReviewGate 组件 | frontend | P0 |

---

## 3. 任务目标

实现 `StoryWorkspaceDreamPage` 页面与 `StoryWorkspaceReviewGate` 组件。Dream 页面是 `story-workspace` 的 canonical 入口页，同时展示工作流上下文条、四步审阅 gate（Agent 产出 → 页面渲染 → 用户审阅 → 继续/结束）、产出数据表及右侧 Review Panel。ReviewGate 在活动 `workflow_run_id` 存在时固定显示于 Main Content 标题/工作流上下文条下方、数据表上方。

**核心约束**：
- Dashboard 页面保留复用，不再拥有独立路由状态
- ReviewGate 与 Review Panel 必须显示同一运行来源
- "保存"不等于确认；只有"确认通过"或"保存并确认"能确认当前版本
- 确认动作必须带运行 ID 与审阅版本校验，防过期确认
- 关闭面板、刷新、路由切换不改变 gate 状态
- Gate 聚合当前 `workflow_run_id` 的全部必审故事、角色、场景；任一项为 `pending` 或 `rejected` 时，继续/结束按钮禁用

---

## 4. 实现步骤

### Step 1: 实现 `StoryWorkspaceDreamPage` 页面

- 位置：`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`
- 组合既有 Dashboard 概览能力（统计卡片、待审阅快捷入口、已确认列表）
- 在 Dashboard 内容基础上追加：
  - `StoryWorkspaceWorkflowContextBar`（来自 `task_226_frontend_workflow-context-bar` 或等效实现）
  - `StoryWorkspaceReviewGate`（本任务 Step 2）
  - 产出数据表（复用 `StoryWorkspaceStoryTable` 等既有表格组件）

**页面布局**：
```
┌─ AppHeader：Dream（选中）────────────────────────────────────────────────────┐
├──────────────┬────────────────────────────────────────────┬─────────────────┤
│ StoryWorkspace│ Dream / 创作工作流                         │ StoryWorkspace  │
│ Sidebar       │ [Deck v3] [Desk 已就绪] [run id]           │ Review Panel    │
│               │                                            │                 │
│ 概览          │ StoryWorkspaceReviewGate                   │ 来源/版本       │
│ 故事          │ [✓ Agent 产出]─[✓ 页面渲染]─[审阅中]─[锁]  │ 完整产出        │
│ 角色          │                                            │ 编辑            │
│ 场景          │ StoryWorkspace*Table                       │ 确认 / 驳回     │
│               │ 待审阅黄条 / 已驳回红条 / 已确认正常行       │                 │
└──────────────┴────────────────────────────────────────────┴─────────────────┘
```

### Step 2: 实现 `StoryWorkspaceReviewGate` 组件

- 位置：`frontend/src/components/story-workspace/review/StoryWorkspaceReviewGate.tsx`
- 四步进度指示：
  1. **Claude Agent 产出** — Agent 按 Deck 工作流生成内容
  2. **页面渲染** — 数据完整持久化后在表格展示
  3. **用户审阅** — 用户查看、确认、驳回或编辑后确认
  4. **继续/结束** — 全部必审项确认后，按所选 Deck 插件继续或结束

**Gate 状态映射**（`StoryWorkspaceReviewGateState` → UI 表现）：

| UI 状态 | 来源运行状态 | 可见表现 | 后续执行 gate |
|---------|-------------|----------|---------------|
| `story-workspace-agent-running` | `queued` / `running` | 第一步高亮，数据区骨架态 | 锁定 |
| `story-workspace-rendering` | `output_validating` | 第二步高亮；部分结果不可审阅 | 锁定 |
| `story-workspace-pending-review` | canonical `pending_review` | 第三步高亮；待审阅黄条，Review Panel 可操作 | 锁定 |
| `story-workspace-rejected` | 任一必审项 `rejected` | 第三步红色状态，显示修改意见与"沿原快照重新生成" | 锁定 |
| `story-workspace-confirming` | 确认请求提交中 | 操作按钮 Loading 且防重复提交 | 锁定 |
| `story-workspace-confirmed` | 全部必审项 `confirmed` | 第三步完成，第四步解锁 | 仅此状态可请求继续或结束 |
| `story-workspace-continuing` / `story-workspace-completed` | 已确认后继续/终点 | 第四步显示执行中或已结束；来源信息只读 | 已放行 |
| `story-workspace-failed` | 任一步失败 | 显示非敏感错误、失败步骤与可恢复动作 | 锁定；按幂等规则重试 |

**Gate 规则实现**：
1. `pending_review` 是与 SUO-215 运行状态机一致的 canonical API 状态；既有文案"待审阅/awaiting review"只是展示语义，不新增第二个 API 枚举
2. 运行级 gate 以该 `workflow_run_id` 的全部必审故事、角色、场景为聚合集合；任一项仍为 `pending` 或 `rejected` 时，不得进入 `confirmed`、`continuing` 或 `completed`
3. "保存"只更新内容并保持待审阅；只有"确认通过"或"保存并确认"可确认当前版本。确认必须校验运行 ID 与审阅版本，避免对过期 Agent 产出放行
4. 确认动作必须幂等：首次合法确认后只发出一次继续/结束信号；重复点击、刷新或网络重试不得重复推进 Claude Agent
5. 驳回只记录意见并锁住 gate；重新生成创建可审计的新 run attempt，默认沿用 DEC-010 的插件/配置快照，不能在原运行上静默覆盖
6. 若内容已确认但后续继续失败，确认事实不回滚；页面进入失败态，并以同一已确认运行幂等重试继续动作

### Step 3: Gate 与 Review Panel 联动

- `StoryWorkspaceReviewGate` 与 `StoryWorkspaceReviewPanel` 必须显示同一 `workflow_run_id` 来源
- 选中待审阅行后，右侧 Review Panel 展示同一运行来源及操作
- 关闭面板或离开再返回不会改变 gate
- 确认操作需传递：
  - `workflow_run_id`: 当前运行 ID
  - `review_version`: 审阅版本标识（用于防过期）

### Step 4: 状态管理扩展

在 Zustand store 中追加：

```typescript
interface StoryWorkspaceState {
  // ... 既有状态 ...

  // Dream 运行级审阅 gate
  activeWorkflowRunId: string | null;
  storyWorkspaceReviewGateState: StoryWorkspaceReviewGateState | null;
  requiredReviewCount: number;
  confirmedReviewCount: number;

  // 审阅操作状态
  reviewActionInProgress: boolean;  // 确认/驳回操作中
  reviewNotes: string;  // 驳回修改意见
}
```

### Step 5: 确认操作防过期

- 确认 API 请求必须携带 `workflow_run_id` + `review_version`
- 服务端拒绝过期版本时，前端展示"内容已更新，请刷新后重新审阅"提示
- 重新生成后（新 run attempt），旧 `review_version` 自动失效

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`
- `frontend/src/components/story-workspace/review/StoryWorkspaceReviewGate.tsx`

**修改文件**（增量适配）：
- `frontend/src/hooks/story-workspace/useStoryWorkspaceStore.ts` — 追加 gate 状态
- `frontend/src/components/story-workspace/review/StoryWorkspaceReviewPanel.tsx` — 追加版本校验、gate 联动
- `frontend/src/components/story-workspace/review/StoryWorkspaceReviewActions.tsx` — 追加确认版本参数

**复用文件**（只读）：
- `frontend/src/components/story-workspace/review/StoryWorkspaceReviewPanel.tsx` — 基线审阅面板（`task_202d`）
- `frontend/src/components/story-workspace/table/StoryWorkspaceStoryTable.tsx` — 基线表格（`task_202c`）
- `frontend/src/components/story-workspace/workflow/StoryWorkspaceWorkflowContextBar.tsx` — 工作流上下文条（`task_226`）
- `frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx` — Dashboard 基线（`task_202e`）

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §3.6.2 Dream 页面可见布局与审阅 gate
- 设计稿 §3.6.3 对下游 issue/task/stage 的影响
- 布局设计稿 §2.4.2 Dream 页面可见布局
- 布局设计稿 §2.4.3 Gate 状态与不可绕过规则
- 既有 `task_202e_frontend_dashboard.md` 的 Dashboard 基线
- 既有 `task_202d_frontend_review-panel.md` 的 Review Panel 基线

**输出**：
- `StoryWorkspaceDreamPage` 页面：canonical 入口，组合工作流上下文 + gate + 数据表 + Review Panel
- `StoryWorkspaceReviewGate` 组件：四步进度指示 + 状态映射 + gate 规则
- 更新后的状态管理：gate 状态、审阅版本校验
- 更新后的审阅操作：确认带运行 ID + 审阅版本

---

## 7. 依赖项

| 依赖 | Issue ID | 状态 | 说明 |
|---|---|---|---|
| `task_202a` (FE-001 三栏布局) | `SUO-201-FE-001` | ✅ 基线稳定 | 提供布局容器 |
| `task_202b` (FE-002 Sidebar 导航) | `SUO-201-FE-002` | ✅ 基线稳定 | 提供二级导航 |
| `task_202c` (FE-003 数据表格) | `SUO-201-FE-003` | ✅ 基线稳定 | 提供数据表组件 |
| `task_202d` (FE-004 审阅面板) | `SUO-201-FE-004` | ✅ 基线稳定 | 提供 Review Panel 基线；本任务追加 gate 联动 |
| `task_202e` (FE-005 Dashboard) | `SUO-201-FE-005` | ✅ 基线稳定 | 提供 Dashboard 概览能力；本任务组合为 Dream 页面 |
| `task_202f` (FE-006 状态组件) | `SUO-201-FE-006` | ✅ 基线稳定 | 提供空态/加载态组件 |
| `task_230_frontend_dream-nav-item` | `SUO-230-FE-001` | ⏳ 并行 | 提供 canonical 路由配置 |
| `task_226_frontend_workflow-context-bar` | `SUO-226-FE-001` | ⏳ 需先完成 | 提供 Deck 工作流上下文条；若尚未完成，使用占位组件 |
| `SUO-230-BE-001` (审阅 gate 服务端聚合) | `SUO-230-BE-001` | ⏳ 需先完成 | 提供服务端聚合 API；前端可先用 mock 数据并行开发 |

**本任务被依赖**：
- `task_230_shared_idempotency-e2e.md` — E2E 测试需要 Dream 页面和 ReviewGate

---

## 8. 测试策略

1. **Gate 状态流转测试**：
   - `queued` → `running` → `output_validating` → `pending_review` → `confirmed` → `continuing`/`completed`
   - 每一步 UI 状态正确映射
   - 失败状态正确显示错误和恢复动作

2. **Gate 锁定/解锁测试**：
   - 任一项 `pending` 时继续按钮禁用
   - 任一项 `rejected` 时继续按钮禁用且显示红色阻断状态
   - 全部 `confirmed` 时继续/结束按钮启用
   - 确认后仅允许幂等触发一次

3. **防过期测试**：
   - 确认请求携带 `workflow_run_id` + `review_version`
   - 过期版本被拒绝，前端提示刷新
   - 重新生成后旧版本自动失效

4. **联动测试**：
   - Gate 与 Review Panel 显示同一运行来源
   - 关闭面板不改变 gate
   - 刷新页面后 gate 状态从服务端重新读取

5. **视觉测试**：
   - 四步进度指示器样式正确
   - 各状态颜色正确（高亮/锁定/解锁）
   - 待审阅黄条、已驳回红条正确显示

---

## 9. 完成标志

- [ ] `StoryWorkspaceDreamPage` 页面实现，组合既有 Dashboard 概览能力
- [ ] `StoryWorkspaceReviewGate` 组件实现，包含四步进度指示
- [ ] Gate 状态映射完整：
  - `queued`/`running` → "Agent 产出"高亮，表格骨架态
  - `output_validating` → "页面渲染"高亮，部分结果不可审阅
  - `pending_review` → "用户审阅"高亮，待审阅黄条与 Review Panel 操作可用
  - 任一必审项 `rejected` → 红色阻断状态、修改意见及重新生成入口
  - 全部必审项 `confirmed` → 第四步解锁，可继续或结束
- [ ] Gate 聚合当前 `workflow_run_id` 的全部必审故事、角色、场景
- [ ] 任一项为 `pending` 或 `rejected` 时，继续/结束按钮禁用
- [ ] 确认动作带运行 ID 与审阅版本校验，防过期确认
- [ ] 驳回后显示修改意见输入框与"沿原快照重新生成"入口
- [ ] 关闭面板、刷新、路由切换不改变 gate 状态
- [ ] 页面同时可见：工作流上下文条、ReviewGate、数据表、Review Panel
- [ ] 确认幂等：重复点击不重复推进
- [ ] Dashboard 页面保留复用，不再拥有独立路由状态

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| `task_226_frontend_workflow-context-bar` 尚未完成 | 中 | Dream 页面可先使用占位组件，待上下文条完成后替换 |
| `SUO-230-BE-001` 服务端聚合 API 尚未完成 | 中 | 前端可用 mock 数据并行开发，接口确定后切换 |
| ReviewGate 与 Review Panel 状态同步复杂 | 中 | 使用同一 Zustand store 管理，避免多源状态 |
| 确认版本校验增加交互复杂度 | 低 | 版本过期时明确提示用户刷新，不静默失败 |
| 四步进度指示与现有状态组件风格不一致 | 低 | 遵循 Ink & Memory UI v2 视觉规范（暖纸色、轻纸面分区） |

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- `StoryWorkspaceDreamPage` 页面（组合工作流上下文 + gate + 数据表 + Review Panel）
- `StoryWorkspaceReviewGate` 组件（四步进度指示 + 状态映射）
- Gate 与 Review Panel 的联动逻辑
- 确认操作的运行 ID + 审阅版本校验
- 状态管理扩展（gate 状态、审阅操作状态）
- Dashboard 概览能力的复用和组合

**❌ 范围外**（本 task 不实现）：
- `StoryWorkspaceWorkflowContextBar` 组件（由 `task_226_frontend_workflow-context-bar.md` 定义）
- 数据表格组件（由 `task_202c` 基线定义）
- 审阅面板基线 UI（由 `task_202d` 基线定义）
- 服务端聚合 API（由 `task_230_backend_review-gate-aggregation.md` 定义）
- 后端确认幂等逻辑（由 `task_230_backend_review-gate-aggregation.md` 定义）
- Agent 重新生成流程（由 `task_226_backend_agent-deck-desk-adapter.md` 定义）
- Deck/Desk 预检逻辑（由 `task_226` 系列定义）

---

## 执行边界

### 允许修改范围
- 允许创建 `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`
- 允许创建 `frontend/src/components/story-workspace/review/StoryWorkspaceReviewGate.tsx`
- 允许修改 `frontend/src/hooks/story-workspace/useStoryWorkspaceStore.ts`（追加 gate 状态）
- 允许修改 `frontend/src/components/story-workspace/review/StoryWorkspaceReviewPanel.tsx`（追加 gate 联动、版本校验）
- 允许修改 `frontend/src/components/story-workspace/review/StoryWorkspaceReviewActions.tsx`（追加确认版本参数）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件（除本任务指定的 4 份同步更新外）
- **禁止修改** 后端代码（`backend/src/` 等）
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`
- **禁止修改** 数据表格核心组件（`task_202c` 基线）
- **禁止修改** Sidebar 导航结构（`task_202b` 基线）

### 明确排除项
- **复杂画布**：本 task 的 Dream 页面使用数据表呈现产出，不涉及 Canvas 渲染、可视化编辑
- **视频**：不涉及视频内容展示、视频预览
- **移动端**：Dream 页面明确排除移动端适配
- **用户手动创建内容**：Dream 页面仅展示 Agent 产出和审阅状态，不提供手动创建入口
- **实时协作**：不涉及多用户同时审阅的实时同步
- **富文本编辑器**：审阅面板编辑模式使用纯文本/Markdown
- **版本历史**：不涉及内容版本历史、diff 对比

---

## 增量差异说明

### 与既有 `task_202e_frontend_dashboard.md` 的关系

| 维度 | `task_202e` Dashboard 基线 | 本 `task_230` Dream 页面增量 |
|---|---|---|
| 路由状态 | `/story-workspace/dashboard` 拥有独立路由 | `/story-workspace/dashboard` 重定向到 `/story-workspace/dream`；Dashboard 组件由 Dream 页面复用 |
| 页面组件 | `StoryWorkspaceDashboardPage` 独立页面 | `StoryWorkspaceDreamPage` 组合 Dashboard + 工作流上下文条 + ReviewGate |
| 审阅 gate | 无 | 新增 `StoryWorkspaceReviewGate` 四步进度指示 |
| 工作流上下文 | 无 | 复用 `StoryWorkspaceWorkflowContextBar` |
| 确认操作 | 基线 confirm（无版本校验） | 追加 `workflow_run_id` + `review_version` 校验 |

**无冲突声明**：本增量不删除 Dashboard 页面组件，仅将其降级为可复用组件并由 Dream 页面组合。Dashboard 的统计展示、快捷入口、已确认列表能力全部保留。

### 与既有 `task_202d_frontend_review-panel.md` 的关系

| 维度 | `task_202d` Review Panel 基线 | 本 `task_230` 增量 |
|---|---|---|
| 确认操作 | `POST /api/story-workspace/{type}/:id/confirm` | 追加 `workflow_run_id` + `review_version` 参数 |
| Gate 联动 | 无 | Review Panel 操作需与 ReviewGate 状态同步 |
| 来源展示 | 基线（无版本溯源） | 追加运行 ID 和审阅版本展示（与 `task_226-FE-002` 协同） |

**无冲突声明**：本增量只追加参数和联动逻辑，不修改 Review Panel 基线的 UI 结构、编辑模式、驳回流程。
