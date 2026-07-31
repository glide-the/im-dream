# task_202e_frontend_dashboard.md

> **Task ID**: `task_202e`  
> **关联 Issue**: `SUO-201-FE-005` — `工作台首页 Dashboard`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-007`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace 工作台首页 Dashboard 实现

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-FE-005` | 工作台首页 Dashboard | frontend | P1 |

---

## 3. 任务目标

实现工作台首页 Dashboard 页面。展示 Agent 产出概览（待审阅剧本数、已确认剧本数、最近 Agent 生成活动）、待审阅快捷入口（Agent 最新生成的剧本/角色/场景，点击直达审阅）、已确认剧本列表（最近确认）。空态时引导用户前往 Chat 触发 Agent 生成。

---

## 4. 实现步骤

1. **实现 `StoryWorkspaceDashboardPage` 页面组件**
   - 顶部：页面标题 + 审阅状态统计（待审阅数 / 已确认数 / 总数）
   - 中部：待审阅项快捷入口卡片（Agent 最新产出）
   - 下部：已确认剧本列表（最近确认，最多 5 条）

2. **实现统计区域**
   - 待审阅数：Memory Yellow 强调色
   - 已确认数：Spark Green 强调色
   - 总数：Warm Brown
   - 数字实时更新（基于 API 数据）

3. **实现待审阅快捷入口卡片**
   - 展示 Agent 最新生成的剧本/角色/场景
   - 卡片包含：标题、类型、生成时间、审阅状态
   - 点击直达对应审阅面板
   - 无待审阅项时显示空态

4. **实现已确认剧本列表**
   - 最近确认的剧本（最多 5 条）
   - 简洁展示：标题 + 确认时间
   - 点击可查看详情

5. **空态处理**
   - 「还没有剧本内容，在 Chat 中让 Agent 为你生成剧本」
   - 空态图标：Charcoal Brown 线条 + Memory Yellow 点缀风格，64px
   - 引导用户前往 Chat 触发 Agent

6. **数据聚合**
   - 通过 `GET /api/story-workspace/stories` 等接口聚合统计
   - 可按 `review_status=pending` 筛选获取待审阅数
   - 可按 `review_status=confirmed` 筛选获取已确认数

---

## 5. 涉及文件路径

**新增/修改文件**：
- `frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx`（填充内容）

**复用文件**（只读）：
- `frontend/src/components/story-workspace/state/StoryWorkspaceEmptyState.tsx` — 空态组件（FE-006 提供）
- `frontend/src/components/story-workspace/table/StoryWorkspaceReviewStatusBadge.tsx` — 状态标签

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §4.3.1 工作台首页
- 布局设计稿 §3.5.1 工作台首页空态
- 设计稿 §5.1 空态设计

**输出**：
- 完整的 Dashboard 页面组件
- 统计展示、快捷入口、已确认列表

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_202c` (FE-003 数据表格) | ⏳ 需先完成 | 数据查询 Hooks 复用 |
| `task_202f` (FE-006 状态组件) | ⏳ 需先完成 | 空态组件复用 |
| `SUO-201-BE-002` (REST API) | ⏳ 并行 | 统计数据 API |

**本任务被依赖**：
- 无直接下游（Dashboard 是独立页面）

---

## 8. 测试策略

1. **数据展示测试**：
   - 有待审阅项时正确显示数量和快捷入口
   - 已确认列表正确显示最近 5 条
   - 统计数字与 API 返回一致

2. **空态测试**：
   - 无数据时显示空态引导
   - 空态文案正确
   - 图标风格符合规范

3. **交互测试**：
   - 点击快捷入口直达审阅面板
   - 点击已确认项查看详情

4. **视觉测试**：
   - 统计数字颜色正确（待审阅黄/已确认绿）
   - 布局符合设计稿

---

## 9. 完成标志

- [ ] `StoryWorkspaceDashboardPage` 页面组件
- [ ] 顶部：页面标题 + 审阅状态统计（待审阅数 / 已确认数 / 总数）
- [ ] 中部：待审阅项快捷入口卡片（Agent 最新产出）
- [ ] 下部：已确认剧本列表（最近确认，最多 5 条）
- [ ] 空态：「还没有剧本内容，在 Chat 中让 Agent 为你生成剧本」
- [ ] 统计数字实时更新
- [ ] 快捷入口点击直达对应审阅面板

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| Dashboard 数据需多次 API 调用 | 低 | 可合并为一次聚合请求，或并行发起 |
| 空态引导到 Chat 的跳转路径 | 低 | 使用现有 Chat 视图切换机制 |
| 快捷入口卡片信息密度 | 低 | 仅展示核心字段，点击后查看完整内容 |

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- Dashboard 页面实现
- 统计展示
- 待审阅快捷入口
- 已确认列表
- 空态引导

**❌ 范围外**（本 task 不实现）：
- 后端统计聚合 API（BackendTaskAgent 负责）
- Chat 触发 Agent 的实现（已有系统）
- 实时数据推送（本期建议轮询）

---

## 执行边界（增量修正）

### 允许修改范围
- 允许修改 `frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx`（填充 Dashboard 内容）
- 允许创建 Dashboard 专用的展示组件（如统计卡片、快捷入口卡片等）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件
- **禁止修改** 后端代码（`backend/src/` 等）
- **禁止修改** 现有 Chat 系统代码（仅允许跳转/引导）
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`

### 明确排除项
- **复杂画布**：Dashboard 使用标准组件和卡片布局，不涉及 Canvas 渲染、数据可视化图表（如 D3.js, ECharts）、仪表盘图形绘制等
- **视频**：Dashboard 中不包含视频内容展示、视频预览卡片、最近视频活动等功能
- **移动端**：Dashboard 明确排除移动端适配，统计卡片和快捷入口在移动端下不做重新布局（如单列堆叠），保持桌面端设计
- **用户手动创建内容**：Dashboard 的「待审阅快捷入口」仅展示 Agent 最新生成的内容，统计数字仅反映 Agent 产出数据。空态引导文案明确指向「在 Chat 中让 Agent 为你生成剧本」，不提供手动创建入口
- **实时数据推送**：Dashboard 数据刷新采用轮询机制（如 30 秒间隔），不涉及 WebSocket、Server-Sent Events、GraphQL Subscription 等实时推送技术
- **数据可视化图表**：不涉及折线图、柱状图、饼图等统计图表，仅使用数字卡片和列表展示
- **通知中心**：不涉及全局通知中心、消息提醒、推送通知等功能
