# task_202a_frontend_three-column-layout.md

> **Task ID**: `task_202a`  
> **关联 Issue**: `SUO-201-FE-001` — `三栏布局骨架与全局样式`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-001`, `DEC-003`, `DEC-006`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace 三栏布局骨架与全局样式实现

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-FE-001` | 三栏布局骨架与全局样式 | frontend | P0 |

---

## 3. 任务目标

实现 Story Workspace 的桌面端三栏布局骨架：左侧 Sidebar 240px + 中间 Main Content（自适应）+ 右侧 Review Panel 360px。严格遵循 Ink & Memory UI v2 视觉体系，本期仅桌面端，不包含任何移动端/平板端适配代码。

---

## 4. 实现步骤

1. **创建布局目录结构**
   - 创建 `frontend/src/components/story-workspace/layout/` 目录
   - 创建 `frontend/src/components/story-workspace/` 根目录

2. **实现 `StoryWorkspaceLayout` 根布局组件**
   - 三栏结构：Sidebar (240px) + Main Content (flex: 1) + Review Panel (360px)
   - 页面背景 Warm Canvas #F6EFE5 (`--color-bg-app`)
   - 内容区背景 Paper Cream #FFFAF2 (`--color-bg-paper`)
   - 边框使用 Border Paper #D8C7B3 虚线 (`--color-border-paper`)
   - 复用现有全局 `AppHeader`（`TopNavBar`）

3. **实现 `StoryWorkspaceReviewPanel` 审阅面板容器**
   - 固定宽度 360px
   - 默认展开，可手动折叠（点击关闭按钮后折叠）
   - 折叠后 Main Content 恢复全宽
   - 左边框：虚线 Border Paper

4. **验证桌面端约束**
   - 确认无 `@media` 移动端查询代码
   - 确认无 `< 768px` 或 `768px-1279px` 的响应式处理
   - 布局在 ≥1280px 下正确渲染

5. **样式 token 复用**
   - 全部使用 `frontend/src/styles/tokens.css` 中已定义的 CSS Variable
   - 不新增色彩定义，如需补充需在 tokens.css 中添加

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/components/story-workspace/`（目录）
- `frontend/src/components/story-workspace/layout/`（目录）
- `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.tsx`
- `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx`
- `frontend/src/components/story-workspace/layout/index.ts`

**复用文件**（只读）：
- `frontend/src/components/AppLayout.tsx` — 参考现有布局模式
- `frontend/src/components/TopNavBar.tsx` — 全局 AppHeader
- `frontend/src/styles/tokens.css` — 色彩/字体 token

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §4.4 布局交互、§6 视觉设计规范
- 布局设计稿 §2.1 全局布局骨架、§2.2 布局约束声明
- 现有 tokens.css 色彩定义

**输出**：
- `StoryWorkspaceLayout` 组件：提供三栏布局骨架
- `StoryWorkspaceReviewPanel` 组件：可折叠的右侧审阅面板容器
- 布局 index.ts 导出

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `frontend/src/styles/tokens.css` | ✅ 已存在 | 色彩系统 |
| `frontend/src/components/TopNavBar.tsx` | ✅ 已存在 | 全局导航栏 |
| `SUO-201-SH-002` (共享类型包) | ⏳ 可选 | 类型定义可后续对齐 |

**本任务被依赖**：
- `task_202b` (FE-002 Sidebar 导航) — 依赖本任务的布局骨架

---

## 8. 测试策略

1. **视觉验证**：
   - 截图验证三栏比例正确（240px : 自适应 : 360px）
   - 验证背景色、边框色与 tokens.css 一致

2. **约束验证**：
   - `grep -r "@media" frontend/src/components/story-workspace/layout/` 应无结果
   - `grep -r "768px\|1279px" frontend/src/components/story-workspace/layout/` 应无结果

3. **交互验证**：
   - Review Panel 关闭后 Main Content 恢复全宽
   - 点击表格行后 Review Panel 展开

---

## 9. 完成标志

- [ ] `StoryWorkspaceLayout` 组件实现三栏结构
- [ ] Sidebar 固定 240px，始终展开，不可折叠为图标栏
- [ ] Main Content 填充剩余宽度
- [ ] Review Panel 固定 360px，默认展开，可手动折叠
- [ ] 页面背景 Warm Canvas #F6EFE5，内容区 Paper Cream #FFFAF2
- [ ] 边框使用 Border Paper #D8C7B3 虚线
- [ ] 确认无 `@media` 移动端查询代码
- [ ] 确认无 `< 768px` 或 `768px-1279px` 的响应式处理
- [ ] 布局在 ≥1280px 下正确渲染

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 现有项目无 react-router | 中 | 当前使用 App.tsx 状态路由，Story Workspace 作为新 view 接入；如需独立路由后续评估 |
| Review Panel 折叠状态管理 | 低 | 使用本地 state 或 Zustand store 管理，不依赖后端 |
| 与现有 AppLayout 的层级关系 | 低 | StoryWorkspaceLayout 作为独立布局，不修改 AppLayout |

---

## 附录：布局组件接口定义

```typescript
// StoryWorkspaceLayout Props
interface StoryWorkspaceLayoutProps {
  children: React.ReactNode;           // Main Content 区域内容
  sidebar: React.ReactNode;            // Sidebar 区域内容
  reviewPanel?: React.ReactNode;       // Review Panel 区域内容（可选）
  reviewPanelOpen?: boolean;           // Review Panel 展开状态
}

// StoryWorkspaceReviewPanel Props
interface StoryWorkspaceReviewPanelProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
}
```

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- 三栏布局骨架实现
- 桌面端（≥1280px）布局
- Review Panel 折叠行为
- 全局样式 token 复用

**❌ 范围外**（本 task 不实现）：
- Sidebar 导航内容（FE-002 负责）
- 数据表格内容（FE-003 负责）
- 审阅面板内部内容（FE-004 负责）
- 移动端/平板端适配
- 响应式断点处理

---

## 执行边界（增量修正）

### 允许修改范围
- 允许创建 `frontend/src/components/story-workspace/layout/` 目录及子文件
- 允许创建 `frontend/src/components/story-workspace/` 根目录
- 允许修改 `frontend/src/styles/tokens.css`（如需补充新 token）
- 允许修改 `frontend/src/App.tsx`（如需接入 Story Workspace 路由/视图）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件
- **禁止修改** 后端代码（`backend/src/` 等）
- **禁止修改** 现有全局组件（`AppLayout.tsx`, `TopNavBar.tsx`）的核心逻辑（仅允许参考/复用）
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`

### 明确排除项
- **复杂画布**：本 task 仅实现 CSS Flexbox/Grid 布局骨架，不涉及 Canvas 2D/3D 渲染、SVG 复杂图形操作、WebGL 等画布相关技术
- **视频**：本 task 不涉及视频播放器嵌入、视频流处理、WebRTC 等相关功能
- **移动端**：本 task 明确排除所有移动端（<768px）和平板端（768px-1279px）适配代码，不包含任何 `@media` 查询、响应式断点处理、触摸手势支持
- **用户手动创建内容**：本 task 布局容器仅用于展示 Agent 生成的内容，不包含任何用户手动创建/编辑内容的输入区域或表单
- **路由实现**：如项目无 react-router，本 task 仅提供布局组件，不强制要求实现路由切换逻辑（由 FE-002 负责）
- **动画效果**：Review Panel 折叠仅使用 CSS transition，不涉及复杂动画库（Framer Motion 等）
