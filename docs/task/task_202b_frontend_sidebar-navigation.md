# task_202b_frontend_sidebar-navigation.md

> **Task ID**: `task_202b`  
> **关联 Issue**: `SUO-201-FE-002` — `Sidebar 导航与路由配置`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-003`, `DEC-004`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace Sidebar 导航与路由配置实现

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-FE-002` | Sidebar 导航与路由配置 | frontend | P0 |

---

## 3. 任务目标

实现 Story Workspace 的 Sidebar 导航组件和路由配置。Sidebar 包含工作台首页、故事管理、角色管理、场景管理导航项，以及底部设置入口。路由使用 `/story-workspace/*` 前缀。当前项使用 Memory Yellow 下划线指示。

---

## 4. 实现步骤

1. **实现 `StoryWorkspaceSidebar` 组件**
   - 宽度 240px，背景 Paper Cream
   - Logo 区：「Ink & Memory 创作者工作台」
   - 导航项：工作台首页、故事管理、角色管理、场景管理
   - 底部设置入口（跳转全局 Settings）
   - 用户信息区：头像和用户名（复用现有用户体系）
   - 当前项指示：Memory Yellow 下划线（2px，偏移 4px）
   - Hover 效果：背景色轻微变化（Paper Cream 深色 5%）

2. **创建路由配置**
   - 新建 `frontend/src/router/story-workspace.tsx`（或等效路由配置）
   - 路由前缀：`/story-workspace`
   - 子路由：`/dashboard`, `/stories`, `/characters`, `/scenes`
   - 默认重定向：`/story-workspace` → `/story-workspace/dashboard`

3. **创建页面组件骨架**
   - `frontend/src/pages/story-workspace/` 目录
   - `StoryWorkspaceDashboardPage.tsx`（工作台首页骨架）
   - `StoryWorkspaceStoriesPage.tsx`（故事列表骨架）
   - `StoryWorkspaceCharactersPage.tsx`（角色列表骨架）
   - `StoryWorkspaceScenesPage.tsx`（场景列表骨架）

4. **导航状态管理**
   - 当前导航项与路由同步
   - 使用 Memory Yellow 下划线标记当前项
   - 图标 20px，Charcoal Brown；文字 14px，500 字重

5. **与现有系统集成**
   - 复用现有用户认证体系（`useAuth`）
   - 设置入口跳转现有全局 Settings 页面
   - 不重复实现用户头像/用户名获取逻辑

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/components/story-workspace/layout/StoryWorkspaceSidebar.tsx`
- `frontend/src/router/story-workspace.tsx`（或等效路由配置位置）
- `frontend/src/pages/story-workspace/`（目录）
- `frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx`
- `frontend/src/pages/story-workspace/StoryWorkspaceStoriesPage.tsx`
- `frontend/src/pages/story-workspace/StoryWorkspaceCharactersPage.tsx`
- `frontend/src/pages/story-workspace/StoryWorkspaceScenesPage.tsx`
- `frontend/src/pages/story-workspace/index.ts`

**复用文件**（只读）：
- `frontend/src/contexts/AuthContext.tsx` — 用户认证
- `frontend/src/components/AppLayout.tsx` — 参考布局模式

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §3.1 Sidebar 导航栏
- 布局设计稿 §3.1 Sidebar 导航栏线框
- 设计稿 §4.1 信息架构（路由结构）
- 设计稿 §4.2 命名映射

**输出**：
- `StoryWorkspaceSidebar` 组件：完整导航栏
- `story-workspace.tsx` 路由配置
- 4 个页面组件骨架（后续任务填充内容）

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_202a` (FE-001 布局骨架) | ⏳ 需先完成 | StoryWorkspaceLayout 提供布局容器 |
| `frontend/src/contexts/AuthContext.tsx` | ✅ 已存在 | 用户认证信息 |
| `frontend/src/styles/tokens.css` | ✅ 已存在 | 色彩/字体 token |

**本任务被依赖**：
- `task_202c` (FE-003 数据表格) — 依赖 Sidebar 导航和页面骨架

---

## 8. 测试策略

1. **导航功能测试**：
   - 点击每个导航项正确切换路由
   - 当前项正确显示 Memory Yellow 下划线
   - 设置入口正确跳转全局 Settings

2. **视觉测试**：
   - Sidebar 宽度 240px
   - Logo 区文字正确显示
   - 用户信息区头像和用户名显示正常

3. **路由测试**：
   - `/story-workspace` 重定向到 `/story-workspace/dashboard`
   - 各子路由正确渲染对应页面骨架

---

## 9. 完成标志

- [ ] `StoryWorkspaceSidebar` 组件实现，240px 宽度
- [ ] 导航项：工作台首页、故事管理、角色管理、场景管理
- [ ] 底部设置入口（跳转全局 Settings）
- [ ] 当前项指示：Memory Yellow 下划线（2px，偏移 4px）
- [ ] Hover 效果：背景色轻微变化
- [ ] 路由配置：`/story-workspace` → redirect `/story-workspace/dashboard`
- [ ] 子路由：`/dashboard`, `/stories`, `/characters`, `/scenes`
- [ ] 路由文件：`frontend/src/router/story-workspace.tsx`（或等效位置）
- [ ] Logo 区显示「Ink & Memory 创作者工作台」
- [ ] 用户信息区显示头像和用户名（复用现有用户体系）

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 现有项目路由机制不确定 | 中 | 当前 App.tsx 使用状态切换（view state），需确认 Story Workspace 接入方式 |
| 与现有 Sidebar/VerticalNav 命名冲突 | 低 | 使用 `StoryWorkspaceSidebar` 前缀避免冲突 |
| 用户认证信息获取 | 低 | 复用 `useAuth` hook，不重新实现 |

---

## 附录：路由配置参考

```typescript
// frontend/src/router/story-workspace.tsx
const storyWorkspaceRoutes = [
  {
    path: '/story-workspace',
    component: StoryWorkspaceLayout,
    children: [
      { path: '', redirect: '/story-workspace/dashboard' },
      { path: 'dashboard', component: StoryWorkspaceDashboardPage },
      { path: 'stories', component: StoryWorkspaceStoriesPage },
      { path: 'characters', component: StoryWorkspaceCharactersPage },
      { path: 'scenes', component: StoryWorkspaceScenesPage },
    ],
  },
];
```

**注意**：如项目使用状态路由而非 react-router，等效实现为在 App.tsx 中增加 `view === 'story-workspace'` 分支，内部再用子状态管理 `dashboard | stories | characters | scenes`。

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- Sidebar 导航组件
- 路由配置
- 页面组件骨架
- 与现有用户体系的集成

**❌ 范围外**（本 task 不实现）：
- 数据表格实现（FE-003 负责）
- Dashboard 页面内容（FE-005 负责）
- 全局 Settings 页面修改
- 移动端导航适配

---

## 执行边界（增量修正）

### 允许修改范围
- 允许创建 `frontend/src/components/story-workspace/layout/StoryWorkspaceSidebar.tsx`
- 允许创建 `frontend/src/router/story-workspace.tsx`（或等效路由配置位置）
- 允许创建 `frontend/src/pages/story-workspace/` 目录及页面骨架文件
- 允许修改 `frontend/src/App.tsx`（接入 Story Workspace 路由/视图切换）

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件
- **禁止修改** 后端代码（`backend/src/` 等）
- **禁止修改** 现有用户认证体系核心逻辑（仅允许复用 `useAuth` hook）
- **禁止修改** 现有全局 Settings 页面
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`

### 明确排除项
- **复杂画布**：本 task 的 Sidebar 导航仅包含文本链接和图标，不涉及 Canvas 渲染、SVG 复杂图形、图标动画绘制等画布相关技术
- **视频**：本 task 不涉及视频播放器、视频缩略图、视频流处理等相关功能
- **移动端**：本 task 明确排除移动端导航适配（如汉堡菜单、底部 Tab 栏、手势滑动等），Sidebar 始终固定 240px 宽度，不可折叠为图标栏
- **用户手动创建内容**：本 task 导航项仅引导至 Agent 产出内容的展示页面，不包含用户手动创建故事/角色/场景的入口或表单
- **路由守卫**：本 task 仅配置基础路由，不涉及复杂路由守卫、权限控制、懒加载策略
- **面包屑导航**：本 task 不包含面包屑导航实现
