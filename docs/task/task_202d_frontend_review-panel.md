# task_202d_frontend_review-panel.md

> **Task ID**: `task_202d`  
> **关联 Issue**: `SUO-201-FE-004` — `审阅面板（Review Panel）与审阅操作`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-007`, `DEC-008`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace 审阅面板（Review Panel）与审阅操作实现

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-FE-004` | 审阅面板（Review Panel）与审阅操作 | frontend | P0 |

---

## 3. 任务目标

实现审阅面板组件，展示 Agent 生成的完整内容，支持用户审阅确认操作。面板内包含：Agent 生成内容展示（只读/可编辑切换）、审阅状态指示、关联角色/场景列表、修改意见输入区、确认/驳回/编辑操作按钮。编辑模式下字段可修改，保存后可确认或仅保存。

---

## 4. 实现步骤

1. **创建审阅组件目录**
   - `frontend/src/components/story-workspace/review/`

2. **实现 `StoryWorkspaceReviewActions` 审阅操作按钮**
   - 确认通过按钮：Spark Green 背景
   - 驳回按钮：#E74C3C 背景
   - 编辑按钮：Action Brown 背景
   - 编辑模式按钮：保存并确认 / 保存 / 取消

3. **实现 `StoryWorkspaceReviewNotesInput` 驳回修改意见输入**
   - 多行文本输入
   - 驳回时必填验证
   - 提示文字：「请填写修改意见，帮助 Agent 重新生成」

4. **实现 `StoryWorkspaceAgentContentDisplay` Agent 生成内容展示**
   - 故事：标题、描述、内容（纯文本/Markdown）
   - 角色：名称、身份、性格、背景、口头禅、标签
   - 场景：名称、描述
   - 只读模式与编辑模式切换

5. **组装 `StoryWorkspaceReviewPanel` 完整审阅面板**
   - 标题栏：内容标题 + 关闭按钮 + Agent 来源标记
   - 审阅状态指示：● 待审阅 / 已确认 / 已驳回
   - Agent 生成内容展示区域
   - 关联角色列表（可点击跳转角色模块）
   - 关联场景列表（可点击跳转场景模块）
   - 修改意见输入区（驳回时显示）
   - 审阅操作按钮组

6. **实现审阅操作逻辑**
   - 确认通过：调用 `POST /api/story-workspace/{type}/:id/confirm`
   - 驳回：调用 `POST /api/story-workspace/{type}/:id/reject`，附带 review_notes
   - 编辑后保存：调用 `PATCH /api/story-workspace/{type}/:id`
   - 编辑后保存并确认：先 PATCH 再 confirm
   - 操作完成后 Toast 通知 + 表格刷新

7. **状态流转反馈**
   - 确认后：Toast「已确认」，状态变 confirmed，行标记消失
   - 驳回后：Toast「已驳回」，状态变 rejected，行变红色标记
   - 编辑保存后：Toast「已保存」

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/components/story-workspace/review/`（目录）
- `frontend/src/components/story-workspace/review/StoryWorkspaceReviewActions.tsx`
- `frontend/src/components/story-workspace/review/StoryWorkspaceReviewNotesInput.tsx`
- `frontend/src/components/story-workspace/review/StoryWorkspaceAgentContentDisplay.tsx`
- `frontend/src/components/story-workspace/review/index.ts`
- `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx`（组装组件）

**复用文件**（只读）：
- 全局 Toast 组件
- 全局 Modal/Dialog 组件
- 基础 Button、Input 组件

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §3.4 Review Panel
- 布局设计稿 §3.4 Review Panel 线框
- 设计稿 §4.5.3 审阅面板交互
- 设计稿 §4.5.4 审阅确认流程

**输出**：
- `StoryWorkspaceReviewPanel` 完整审阅面板组件
- `StoryWorkspaceReviewActions` 操作按钮组件
- `StoryWorkspaceReviewNotesInput` 修改意见输入组件
- `StoryWorkspaceAgentContentDisplay` 内容展示组件

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_202c` (FE-003 数据表格) | ⏳ 需先完成 | 表格行选中触发面板展示 |
| `SUO-201-BE-003` (审阅状态流转 API) | ⏳ 需先完成 | confirm/reject API |
| `SUO-201-SH-002` (共享类型包) | ⏳ 可选 | 类型定义 |
| 全局 Toast/Modal 组件 | ✅ 已存在 | 通知和弹窗 |

**本任务被依赖**：
- `task_202g` (SH-001 E2E 联调) — 依赖审阅面板完成

---

## 8. 测试策略

1. **审阅流程 E2E 测试**：
   - 点击待审阅行 → 面板展开 → 显示 Agent 内容
   - 点击确认 → API 调用 → Toast「已确认」→ 表格刷新
   - 点击驳回 → 输入修改意见 → API 调用 → Toast「已驳回」→ 行变红
   - 点击编辑 → 修改字段 → 保存并确认 → 状态 confirmed

2. **编辑模式测试**：
   - 进入编辑模式后字段可修改
   - 保存并确认：PATCH + confirm 顺序调用
   - 仅保存：PATCH 调用，状态不变
   - 取消：恢复原始内容

3. **关联跳转测试**：
   - 点击关联角色 → 跳转到角色模块
   - 点击关联场景 → 跳转到场景模块

4. **错误处理测试**：
   - API 失败时显示错误提示
   - 网络错误时 Toast 提示

---

## 9. 完成标志

- [ ] `StoryWorkspaceReviewPanel` 组件，宽度 360px
- [ ] 标题栏：内容标题 + 关闭按钮 + Agent 来源标记
- [ ] 审阅状态指示：● 待审阅 / 已确认 / 已驳回
- [ ] Agent 生成内容展示：故事描述、角色属性、场景信息
- [ ] 编辑模式：字段可修改，显示「保存并确认」/「保存」/「取消」按钮
- [ ] 关联角色列表：可点击跳转角色模块
- [ ] 关联场景列表：可点击跳转场景模块
- [ ] 修改意见输入区：驳回时必填
- [ ] 确认通过按钮：Spark Green 背景，点击后状态变为 confirmed，Toast「已确认」
- [ ] 驳回按钮：#E74C3C 背景，点击后弹出修改意见输入框，状态变为 rejected
- [ ] 编辑按钮：Action Brown 背景，进入编辑模式
- [ ] 操作完成后表格刷新

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 审阅 API 尚未实现 | 中 | 使用 Mock API 或 MSW 开发，后续切换 |
| 编辑模式状态管理复杂 | 中 | 使用本地 state 管理编辑态，提交后同步到全局 store |
| 关联跳转与路由同步 | 低 | 通过全局状态或 URL 参数传递选中项 ID |
| 内容编辑器类型不确定 | 低 | 默认纯文本/Markdown，预留富文本扩展点 |

---

## 附录：审阅面板状态机

```
[view mode] --点击编辑--> [edit mode]
[edit mode] --点击保存并确认--> [confirmed] + API call
[edit mode] --点击保存--> [view mode] + API call
[edit mode] --点击取消--> [view mode]
[view mode] --点击确认--> [confirmed] + API call
[view mode] --点击驳回--> [reject dialog] --提交--> [rejected] + API call
```

---

## 范围边界

**✅ 范围内**：
- 审阅面板 UI 和交互
- 确认/驳回/编辑操作
- 关联角色/场景列表展示和跳转
- 修改意见输入
- 状态流转反馈

**❌ 范围外**：
- 后端审阅状态流转 API（BackendTaskAgent 负责）
- Agent 重新生成流程（后续迭代）
- 富文本编辑器（默认纯文本/Markdown）
- 四视角头像（本期仅单张头像）
