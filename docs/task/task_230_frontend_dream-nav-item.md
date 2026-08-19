# task_230_frontend_dream-nav-item.md

> **Task ID**: `task_230_frontend_dream-nav-item`  
> **关联 Issue**: `SUO-230-FE-001` — `TopNavBar Dream 导航项与 canonical 路由`  
> **上游 Issue**: `SUO-230` (Issue 清单 §2.3)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-017`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `TaskDesignAgent`  
> **增量来源**: `SUO-232` 传播 → `SUO-234` task 阶段

---

## 1. 任务标题

Story Workspace Dream 导航项（`StoryWorkspaceDreamNavItem`）与 canonical 路由配置

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-230-FE-001` | TopNavBar Dream 导航项与 canonical 路由 | frontend | P0 |

---

## 3. 任务目标

在现有全局 AppHeader / `TopNavBar` 中增加 Dream 导航项。该导航项是 `story-workspace` 业务域的全局入口，以 `/story-workspace/dream` 为 canonical 路由。兼容既有 `/story-workspace` 与 `/story-workspace/dashboard` 重定向。任一 `/story-workspace/*` 子页保持 Dream 选中，其他平台页面显示未选中。

**核心约束**：
- Dream 是 `story-workspace` 顶级业务域入口，Sidebar 的概览/故事/角色/场景是域内二级导航
- 不得维护两份平行页面状态（Dashboard 与 Dream）
- 重定向不得创建额外 store、重复请求或独立 `workflow_run_id`
- 不改变三栏宽度（240px / 自适应 / 360px），不新增第二层顶部栏

---

## 4. 实现步骤

### Step 1: 实现 `StoryWorkspaceDreamNavItem` 组件

- 内部标识：`story-workspace-dream`
- 用户可见文案：`Dream`
- 组件位置：`frontend/src/components/story-workspace/navigation/StoryWorkspaceDreamNavItem.tsx`
- 接收 props：`isActive: boolean`, `onClick: () => void`

**选中态表现**：
- `aria-current="page"`
- Charcoal Brown 600 字重
- Memory Yellow 3px 短下划线（非整块深色背景）

**未选中/交互态**：
- Warm Brown 常态文字
- 下划线透明
- hover 复用现有 `--color-bg-hover` 与 Charcoal Brown
- 键盘 focus 使用可见 Action Brown 轮廓

### Step 2: 集成到 `TopNavBar`

- 在现有 AppHeader / `TopNavBar` 的 Logo 后横向导航组中插入 Dream 项
- 位置：与其他顶级导航项（Writing、Timeline、Analysis、Decks、Chat）并列
- 不改变全局 Header 高度

**选中判定逻辑**：
```typescript
const isDreamActive = pathname.startsWith('/story-workspace');
```
- 当前路径为 `/story-workspace/dream` 或任一 `/story-workspace/*` 子页时选中
- 进入 Writing、Timeline、Analysis、Decks、Chat、Settings 等其他平台页面时未选中

### Step 3: 路由配置更新

修改 `frontend/src/router/story-workspace.tsx`（或等效路由配置）：

```typescript
const storyWorkspaceRoutes = [
  {
    path: '/story-workspace',
    component: StoryWorkspaceLayout,
    children: [
      { path: '', redirect: '/story-workspace/dream' },           // ← 新增：根路径重定向
      { path: 'dream', component: StoryWorkspaceDreamPage },      // ← canonical 入口
      { path: 'dashboard', redirect: '/story-workspace/dream' },  // ← 新增：兼容重定向
      { path: 'stories', component: StoryWorkspaceStoriesPage },
      { path: 'characters', component: StoryWorkspaceCharactersPage },
      { path: 'scenes', component: StoryWorkspaceScenesPage },
    ],
  },
];
```

**重定向规则**：
- `/story-workspace` → `/story-workspace/dream`（301 等效行为）
- `/story-workspace/dashboard` → `/story-workspace/dream`（301 等效行为）
- 重定向不得创建额外 store 状态、不重复发起数据请求、不生成新的 `workflow_run_id`

### Step 4: 可访问性

- 键盘导航：Tab 聚焦时显示 Action Brown 可见轮廓
- 屏幕阅读器：`aria-current="page"` 标记当前选中项
- 点击区域：导航项整体可点击，不限于文字区域

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/components/story-workspace/navigation/StoryWorkspaceDreamNavItem.tsx`
- `frontend/src/components/story-workspace/navigation/index.ts`

**修改文件**（增量适配）：
- `frontend/src/components/TopNavBar.tsx` — 插入 Dream 导航项
- `frontend/src/router/story-workspace.tsx` — 追加 canonical 路由与重定向

**复用文件**（只读）：
- `frontend/src/styles/tokens.css` — 色彩 token

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §3.6.1 全局顶部 Dream 导航合同
- 布局设计稿 §2.4.1 AppHeader 顶部 Dream 入口
- 设计稿 §4.1 信息架构（路由结构）
- 设计稿 §4.2 命名映射
- 既有 `task_202b_frontend_sidebar-navigation.md` 的路由配置基线

**输出**：
- `StoryWorkspaceDreamNavItem` 组件：导航项 UI + 选中/未选中状态
- 更新后的路由配置：canonical `/story-workspace/dream` + 兼容重定向
- `TopNavBar` 集成：Dream 项插入现有导航组

---

## 7. 依赖项

| 依赖 | Issue ID | 状态 | 说明 |
|---|---|---|---|
| `task_202b` (FE-002 Sidebar 导航与路由) | `SUO-201-FE-002` | ✅ 基线稳定 | 提供路由配置基线；本任务在其上增量追加 canonical 路由与重定向 |
| `frontend/src/components/TopNavBar.tsx` | — | ✅ 已存在 | 现有全局顶部导航组件 |
| `frontend/src/styles/tokens.css` | — | ✅ 已存在 | 色彩 token |
| `StoryWorkspaceDreamPage` | `SUO-230-FE-002` | ⏳ 并行 | Dream 页面由 `task_230_frontend_dream-page-review-gate.md` 定义；本任务仅配置路由指向 |

**本任务被依赖**：
- `task_230_frontend_dream-page-review-gate.md` — Dream 页面需要路由配置
- `task_230_shared_idempotency-e2e.md` — E2E 测试需要导航项可交互

---

## 8. 测试策略

1. **导航功能测试**：
   - 点击 Dream 导航至 `/story-workspace/dream`
   - 在 `/story-workspace/stories` 等子页时 Dream 保持选中
   - 在 `/writing` 等非 story-workspace 页面时 Dream 未选中

2. **重定向测试**：
   - 访问 `/story-workspace` 自动重定向到 `/story-workspace/dream`
   - 访问 `/story-workspace/dashboard` 自动重定向到 `/story-workspace/dream`
   - 重定向不创建额外 store 状态

3. **视觉测试**：
   - 选中态：Charcoal Brown 600 + Memory Yellow 3px 短下划线
   - 未选中态：Warm Brown + 透明下划线
   - Hover 效果复用 `--color-bg-hover`
   - Focus 轮廓：Action Brown

4. **可访问性测试**：
   - `aria-current="page"` 在选中时存在
   - 键盘 Tab 可聚焦
   - 屏幕阅读器正确朗读

---

## 9. 完成标志

- [ ] `StoryWorkspaceDreamNavItem` 组件实现，内部标识 `story-workspace-dream`
- [ ] 用户可见文案为 `Dream`
- [ ] Canonical 目标：`/story-workspace/dream`
- [ ] 兼容路由：`/story-workspace` 与 `/story-workspace/dashboard` 重定向至 `/story-workspace/dream`
- [ ] 选中判定：当前路径为 `/story-workspace/dream` 或任一 `/story-workspace/*` 子页时选中
- [ ] 选中表现：`aria-current="page"`，Charcoal Brown 600 字重，Memory Yellow 3px 短下划线
- [ ] 未选中表现：非 story-workspace 页面为 Warm Brown、透明下划线；hover 复用 `--color-bg-hover`
- [ ] 布局位置：沿用现有 AppHeader / TopNavBar 的 Logo 后横向导航组，不新增第二层顶部栏
- [ ] 不改变三栏宽度（240px / 自适应 / 360px）
- [ ] 键盘 focus 使用可见 Action Brown 轮廓
- [ ] 重定向不创建额外 store、不重复请求、不生成独立 `workflow_run_id`

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 现有路由机制为状态切换而非 react-router | 中 | 等效实现为在 App.tsx 中增加 view 分支；Dream 项点击设置 `view = 'story-workspace'` 并子状态为 `'dream'` |
| TopNavBar 组件结构不确定 | 低 | 只读分析现有 TopNavBar 结构后插入；使用 `story-workspace-dream` 前缀避免命名冲突 |
| Dashboard 与 Dream 双状态风险 | 高 | 明确 Dashboard 仅重定向，不维护独立 store；`StoryWorkspaceDashboardPage` 保留复用但不再拥有独立路由状态 |
| 既有 `/story-workspace` 路由被占用 | 中 | 将既有根路由从指向 Dashboard 改为重定向到 Dream；Dashboard 页面组件保留，由 Dream 页面复用 |

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- `StoryWorkspaceDreamNavItem` 导航项组件
- TopNavBar 集成（插入 Dream 项）
- Canonical 路由 `/story-workspace/dream` 配置
- 兼容重定向（`/story-workspace` → `/story-workspace/dream`，`/story-workspace/dashboard` → `/story-workspace/dream`）
- 选中/未选中状态逻辑
- 可访问性属性（`aria-current`、`focus` 轮廓）

**❌ 范围外**（本 task 不实现）：
- `StoryWorkspaceDreamPage` 页面内容（由 `task_230_frontend_dream-page-review-gate.md` 定义）
- `StoryWorkspaceReviewGate` 组件（由 `task_230_frontend_dream-page-review-gate.md` 定义）
- Dashboard 页面内容填充（由 `task_202e` 基线定义）
- 后端路由/重定向逻辑
- 移动端导航适配
- 全局 Header 高度或样式修改（仅插入导航项）

---

## 执行边界

### 允许修改范围
- 允许创建 `frontend/src/components/story-workspace/navigation/StoryWorkspaceDreamNavItem.tsx`
- 允许创建 `frontend/src/components/story-workspace/navigation/index.ts`
- 允许修改 `frontend/src/components/TopNavBar.tsx`（插入 Dream 导航项）
- 允许修改 `frontend/src/router/story-workspace.tsx`（追加 canonical 路由与重定向）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件（除本任务指定的 4 份同步更新外）
- **禁止修改** 后端代码（`backend/`）
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`
- **禁止修改** 现有全局 Settings 页面
- **禁止修改** Sidebar 导航结构（Sidebar 保持独立）

### 明确排除项
- **复杂画布**：本 task 的导航项仅包含文本和样式状态，不涉及 Canvas 渲染
- **视频**：不涉及视频相关导航或预览
- **移动端**：本 task 明确排除移动端导航适配；TopNavBar 的移动端行为（如汉堡菜单）不在本任务范围
- **用户手动创建内容**：导航项仅指向 Agent 产出内容的展示页面，不提供手动创建入口
- **路由守卫**：本 task 仅配置基础路由和重定向，不涉及复杂路由守卫、权限控制
- **实时数据**：导航项状态基于当前路径，不涉及实时数据推送

---

## 增量差异说明

### 与既有 `task_202b_frontend_sidebar-navigation.md` 的关系

| 维度 | `task_202b` 基线 | 本 `task_230` 增量 |
|---|---|---|
| 导航层级 | Sidebar 二级导航（工作台首页/故事/角色/场景） | TopNavBar 一级入口（Dream） |
| 路由 | `/story-workspace` → `/story-workspace/dashboard` | `/story-workspace` → `/story-workspace/dream`；追加 `/story-workspace/dashboard` → `/story-workspace/dream` |
| 选中范围 | Sidebar 项按精确路由匹配 | Dream 项按 `/story-workspace/*` 前缀匹配 |
| 组件 | `StoryWorkspaceSidebar` | `StoryWorkspaceDreamNavItem` |
| 页面 | `StoryWorkspaceDashboardPage` 拥有独立路由状态 | `StoryWorkspaceDashboardPage` 保留复用，由 Dream 页面组合 |

**无冲突声明**：本增量不修改 `task_202b` 的 Sidebar 导航结构、不删除 Dashboard 页面组件、不破坏既有子路由。仅追加全局入口和重定向规则。
