# task_202f_frontend_state-components.md

> **Task ID**: `task_202f`  
> **关联 Issue**: `SUO-201-FE-006` — `空态/加载/错误/选中态组件`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-001`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace 空态/加载/错误/选中态组件实现

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-FE-006` | 空态/加载/错误/选中态组件 | frontend | P1 |

---

## 3. 任务目标

实现各模块的完整状态组件：空态（无 Agent 产出、无待审阅项、搜索结果为空）、加载态（表格骨架屏、面板骨架屏）、错误态（加载失败、保存失败）、选中态（表格行选中、批量操作栏）。所有状态组件遵循 Ink & Memory 视觉规范。

---

## 4. 实现步骤

1. **创建状态组件目录**
   - `frontend/src/components/story-workspace/state/`

2. **实现 `StoryWorkspaceEmptyState` 空态组件**
   - 居中显示
   - 轻纸面图标（Charcoal Brown 线条 + Memory Yellow 点缀），64px
   - 标题：Warm Brown，20px
   - 描述：Muted Tan，14px
   - 操作提示（如适用）

3. **实现 `StoryWorkspaceLoadingState` 加载态（骨架屏）**
   - 表格骨架屏：5 行占位
   - 背景：color-mix(Paper Cream 90%, Muted Tan)
   - shimmer 动画（横向渐变扫过）
   - 圆角：4px
   - 面板骨架屏：标题区 + 内容区占位

4. **实现 `StoryWorkspaceErrorState` 错误态**
   - 错误图标（Charcoal Brown 线条 + 红色点缀）
   - 错误信息标题
   - 错误描述
   - 重试按钮（Action Brown 背景）

5. **各模块空态文案配置**
   - 工作台首页：「还没有剧本内容，请先让 Agent 生成」
   - 故事列表：「暂无待审阅的剧本」
   - 角色列表：「还没有角色，等待 Agent 生成」
   - 场景列表：「还没有场景，等待 Agent 生成」
   - 搜索结果：「未找到匹配的结果」+ 清除搜索条件

6. **错误提示条**
   - 加载失败时显示在表格上方
   - 背景：#E74C3C 10%，边框虚线
   - 文字：#E74C3C
   - 包含重试按钮

7. **Toast 通知复用**
   - 复用现有全局 Toast 组件
   - 不重新实现 Toast

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/components/story-workspace/state/`（目录）
- `frontend/src/components/story-workspace/state/StoryWorkspaceEmptyState.tsx`
- `frontend/src/components/story-workspace/state/StoryWorkspaceLoadingState.tsx`
- `frontend/src/components/story-workspace/state/StoryWorkspaceErrorState.tsx`
- `frontend/src/components/story-workspace/state/index.ts`

**复用文件**（只读）：
- 全局 Toast 组件（现有）

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §5 状态设计
- 布局设计稿 §3.5-3.6 空态与错误态线框
- 设计稿 §5.1-5.4 各状态详细规范

**输出**：
- `StoryWorkspaceEmptyState` — 可配置文案的空态组件
- `StoryWorkspaceLoadingState` — 骨架屏组件
- `StoryWorkspaceErrorState` — 错误展示组件

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_202c` (FE-003 数据表格) | ⏳ 需先完成 | 骨架屏用于表格加载态 |
| `frontend/src/styles/tokens.css` | ✅ 已存在 | 色彩 token |
| 全局 Toast 组件 | ✅ 已存在 | 通知提示 |

**本任务被依赖**：
- `task_202e` (FE-005 Dashboard) — 使用空态组件
- `task_202g` (SH-001 E2E) — 验证各状态表现

---

## 8. 测试策略

1. **空态测试**：
   - 各模块空态文案正确
   - 图标风格符合规范（Charcoal Brown + Memory Yellow）
   - 居中显示

2. **骨架屏测试**：
   - 5 行占位正确显示
   - shimmer 动画流畅
   - 圆角 4px

3. **错误态测试**：
   - 错误图标显示正常
   - 重试按钮可点击
   - 错误提示条样式正确

4. **集成测试**：
   - API 加载中时显示骨架屏
   - API 失败时显示错误态
   - 无数据时显示空态

---

## 9. 完成标志

- [ ] `StoryWorkspaceEmptyState`：居中显示，轻纸面图标，标题 + 描述 + 操作提示
- [ ] `StoryWorkspaceLoadingState`：骨架屏 5 行，shimmer 动画，圆角 4px
- [ ] `StoryWorkspaceErrorState`：错误图标 + 错误信息 + 重试按钮
- [ ] 工作台首页空态：「还没有剧本内容，请先让 Agent 生成」
- [ ] 故事列表空态：「暂无待审阅的剧本」
- [ ] 角色列表空态：「还没有角色，等待 Agent 生成」
- [ ] 场景列表空态：「还没有场景，等待 Agent 生成」
- [ ] 搜索结果空态：「未找到匹配的结果」+ 清除搜索条件
- [ ] Toast 通知复用现有全局 Toast 组件
- [ ] 错误提示条：加载失败时显示在表格上方

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| shimmer 动画性能 | 低 | 使用 CSS animation，避免 JS 计算 |
| 空态图标设计资源 | 低 | 使用 CSS/Icon 组合，不依赖外部图片 |
| 多模块空态文案维护 | 低 | 通过 props 配置，集中管理文案 |

---

## 附录：空态组件接口

```typescript
interface StoryWorkspaceEmptyStateProps {
  icon?: React.ReactNode;           // 自定义图标（默认使用线条风格）
  title: string;                    // 空态标题
  description?: string;             // 空态描述
  action?: {                        // 操作提示（可选）
    label: string;
    onClick: () => void;
  };
}

interface StoryWorkspaceLoadingStateProps {
  rows?: number;                    // 骨架屏行数（默认 5）
  columns?: number;                 // 列数
  variant?: 'table' | 'panel';      // 变体
}

interface StoryWorkspaceErrorStateProps {
  title: string;                    // 错误标题
  description?: string;             // 错误描述
  onRetry?: () => void;             // 重试回调
}
```

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- 空态、加载态、错误态组件
- 各模块空态文案
- 骨架屏实现
- 错误提示条

**❌ 范围外**（本 task 不实现）：
- Toast 组件实现（复用现有）
- Modal/Dialog 实现（复用现有）
- 全局错误边界（如有则复用）

---

## 执行边界（增量修正）

### 允许修改范围
- 允许创建 `frontend/src/components/story-workspace/state/` 目录及组件文件
- 允许配置各模块空态文案（通过组件 props 或配置文件）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件
- **禁止修改** 后端代码（`backend/src/` 等）
- **禁止修改** 现有全局 Toast 组件核心逻辑（仅允许复用）
- **禁止修改** 现有全局 Modal/Dialog 组件核心逻辑（仅允许复用）
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`

### 明确排除项
- **复杂画布**：状态组件使用 CSS/Icon 组合实现图标，不涉及 Canvas 渲染、SVG 复杂动画绘制、Lottie 动画等
- **视频**：不涉及视频加载状态、视频骨架屏、视频错误提示等
- **移动端**：状态组件在桌面端和移动端表现一致，不做移动端特定的空态设计（如移动端引导手势动画）
- **用户手动创建内容**：空态文案明确反映 Agent 生成内容的缺失状态，如「还没有剧本内容，请先让 Agent 生成」「还没有角色，等待 Agent 生成」。不提供手动创建的引导按钮或表单入口
- **骨架屏复杂度**：骨架屏仅使用简单的 CSS shimmer 动画，不涉及复杂的内容占位符布局（如图片占位符的特定形状、多段落文本占位符等）
- **错误边界**：不涉及 React Error Boundary 的实现（如有现有全局错误边界则复用）
- **重试策略**：错误态提供「重试」按钮触发重新加载，不涉及指数退避、自动重试、断网检测等复杂重试策略
