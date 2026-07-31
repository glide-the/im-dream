# Story Workspace Issue 清单

## 0. 文档元信息

- Issue 清单文件：`docs/issue/ISSUES_story-workspace.md`
- 来源设计稿：
  - 主设计稿：`docs/design/story-workspace/story-workspace-prd.md`
  - 补充设计稿：`docs/design/story-workspace/story-workspace-layout-design.md`
  - 背景设计稿：`docs/CLAUDE.md`（Agent 服务集成说明）
  - 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`
- 生成 Agent：`IssueDispatcher`
- 所属流水线阶段：`issue`
- 上游阶段：`design`（SUO-199）
- 下游阶段：`task`
- 下游 Agent：
  - `FrontendTaskAgent`
  - `BackendTaskAgent`
- 共享设计稿来源：`docs/design/story-workspace/`
- 是否作为当前实现合同：是
- 备注：
  - 本文档由设计稿拆解生成，作为 task 阶段任务规划输入。
  - 若与设计稿冲突，以 `docs/design/story-workspace/` 中稳定设计稿为准。
  - 若与当前 API / 代码实现冲突，必须记录为阻塞或澄清项，不得静默覆盖。

---

## 1. 关联设计稿信息

- 主设计稿：`docs/design/story-workspace/story-workspace-prd.md`
- 重点补充设计稿：`docs/design/story-workspace/story-workspace-layout-design.md`
- 关联设计稿：`docs/CLAUDE.md`（claude-agent 服务集成）
- 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`

- 本清单覆盖范围：
  - Workspace 布局骨架：三栏桌面端布局、导航、侧边栏、主内容区
  - Agent 产出渲染：剧本/角色/场景由 Agent 自动生成，页面负责渲染展示
  - 审阅确认流程：用户查看 Agent 产出 → 确认通过 / 提出修改 / 重新生成
  - 故事/剧本列表：数据表格呈现 Agent 产出的剧本，展示生成状态
  - 角色资产管理：展示 Agent 生成的角色列表，支持审阅编辑
  - 场景资产管理：展示 Agent 生成的场景列表，支持审阅编辑
  - 空态/加载/错误/选中态：各模块的完整状态设计，含 Agent 生成中状态
  - 桌面端布局：固定三栏桌面端布局，无响应式适配需求

- 明确排除范围：
  - 用户手动创建故事/角色/场景（本期内容由 Agent 产出，用户仅审阅确认）
  - 复杂画布编辑器（故事板/时间线可视化编辑）
  - 视频生成模块（镜头生成、视频预览）
  - 计费/积分系统（积分消耗策略）
  - 移动端适配（完整移动端交互，本期明确排除，仅桌面端）
  - 实时协作（多创作者同时编辑）
  - 四视角转面图（本期仅支持单张头像）
  - 人物三视图维护
  - 历史版本管理
  - @提及系统

- 关键约束：
  - 所有业务路径、路由、包名、组件/模块/数据标识均采用 `story-workspace` 前缀
  - 本期仅桌面端（≥1280px），不包含任何移动端或平板端适配
  - Sidebar 始终 240px 展开，不提供折叠为图标栏的模式
  - Detail Panel（Review Panel）始终 360px 展开，不作为抽屉滑出
  - 所有交互基于鼠标（hover、点击），不考虑触控
  - 表格始终完整展示所有列，不提供卡片式简化视图
  - 核心工作流：Agent 产出 → 页面渲染 → 用户审阅确认 → 后续执行
  - 用户不手动创建内容，仅对 Agent 产出进行审阅、编辑、确认

- 补充说明：
  - 本批 Issue 拆解基于已确认业务模型：Agent 产出剧本工作空间 → 页面渲染 → 用户审阅确认 → 后续执行
  - 复杂画布改为数据表呈现，排除平台视频、移动端/平板端、用户手动创建内容
  - 设计文档中的 CLARIFICATION_NEEDED 已单列，采用默认假设时标注风险

---

## 2. Issue 总览表

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `SUO-201-BE-001` | 数据库 Schema 与数据表初始化 | backend | P0 | `database`,`schema`,`migration` | 无 | `@BackendTaskAgent` |
| `SUO-201-BE-002` | Story Workspace REST API 实现 | backend | P0 | `api`,`rest`,`crud` | `SUO-201-BE-001` | `@BackendTaskAgent` |
| `SUO-201-BE-003` | 审阅状态流转与批量操作 API | backend | P0 | `api`,`review`,`workflow` | `SUO-201-BE-002` | `@BackendTaskAgent` |
| `SUO-201-BE-004` | Agent 产出数据接收与存储集成 | backend | P0 | `agent`,`integration`,`sse` | `SUO-201-BE-001` | `@BackendTaskAgent` |
| `SUO-201-FE-001` | 三栏布局骨架与全局样式 | frontend | P0 | `layout`,`ui`,`desktop-only` | 无 | `@FrontendTaskAgent` |
| `SUO-201-FE-002` | Sidebar 导航与路由配置 | frontend | P0 | `navigation`,`router`,`sidebar` | `SUO-201-FE-001` | `@FrontendTaskAgent` |
| `SUO-201-FE-003` | 数据表格组件（故事/角色/场景） | frontend | P0 | `table`,`component`,`data-display` | `SUO-201-FE-002` | `@FrontendTaskAgent` |
| `SUO-201-FE-004` | 审阅面板（Review Panel）与审阅操作 | frontend | P0 | `review`,`panel`,`workflow` | `SUO-201-FE-003` | `@FrontendTaskAgent` |
| `SUO-201-FE-005` | 工作台首页 Dashboard | frontend | P1 | `dashboard`,`overview` | `SUO-201-FE-003` | `@FrontendTaskAgent` |
| `SUO-201-FE-006` | 空态/加载/错误/选中态组件 | frontend | P1 | `state`,`ui`,`ux` | `SUO-201-FE-003` | `@FrontendTaskAgent` |
| `SUO-201-SH-001` | 前端-后端联调：审阅工作流 E2E | shared | P0 | `e2e`,`integration`,`review-workflow` | `SUO-201-BE-003`, `SUO-201-FE-004` | `@FrontendTaskAgent` + `@BackendTaskAgent` |
| `SUO-201-SH-002` | 命名规范与类型定义共享包 | shared | P0 | `naming`,`types`,`shared` | 无 | `@FrontendTaskAgent` + `@BackendTaskAgent` |
| `SUO-201-DO-001` | Story Workspace 使用文档 | docs | P2 | `documentation`,`user-guide` | `SUO-201-SH-001` | `@FrontendTaskAgent` |

---

## 3. Issue 明细

### SUO-201-BE-001

- 标题：数据库 Schema 与数据表初始化
- 类型：backend
- 优先级：P0
- 标签：`database`,`schema`,`migration`
- 描述：
  根据设计稿数据表结构，创建 story-workspace 相关的数据库表及索引。包括：故事表、角色表、场景表、故事-角色关联表、场景-角色关联表、工作区表。所有表名使用 `story_workspace_*` 前缀。此 Issue 是所有后端工作的基础。

- 验收条件：
  - [ ] `story_workspace_stories` 表创建，含所有字段（id, identifier, title, description, status, review_status, type, content, author_id, workspace_id, character_count, scene_count, agent_generated, agent_session_id, review_notes, created_at, updated_at, confirmed_at, published_at）
  - [ ] `story_workspace_characters` 表创建，含所有字段
  - [ ] `story_workspace_scenes` 表创建，含所有字段
  - [ ] `story_workspace_story_characters` 关联表创建
  - [ ] `story_workspace_scene_characters` 关联表创建
  - [ ] `story_workspace_workspaces` 表创建
  - [ ] 所有设计稿中指定的索引已创建
  - [ ] Migration 文件可回滚
  - [ ] 数据库约束（外键、非空、默认值）与设计稿一致

- 前置依赖：无

- 关联路径：
  - `backend/src/db/migrations/`
  - `backend/src/db/schema/story-workspace/`

- 分发去向：`@BackendTaskAgent`

- 主责 Agent：`BackendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-004`：`story-workspace` 前缀命名
  - 设计稿 §5.1-5.5 数据表结构

- 备注：
  - 需确认数据库方言（PostgreSQL 假设，含 gin_trgm_ops 和 gin 索引）
  - `review_status` 字段 enum 值：`pending` / `confirmed` / `rejected`

---

### SUO-201-BE-002

- 标题：Story Workspace REST API 实现
- 类型：backend
- 优先级：P0
- 标签：`api`,`rest`,`crud`
- 描述：
  实现 story-workspace 的 REST API 路由，包括工作区、故事、角色、场景的 CRUD 操作。支持列表查询（搜索、筛选、排序、分页）和详情查询。所有路由使用 `/api/story-workspace/*` 前缀。

- 验收条件：
  - [ ] `GET /api/story-workspace/workspace` — 获取当前用户工作区
  - [ ] `PATCH /api/story-workspace/workspace/:id` — 更新工作区设置
  - [ ] `GET /api/story-workspace/stories` — 列表（支持 q/review_status/status/type/sort/order/page/per_page）
  - [ ] `GET /api/story-workspace/stories/:id` — 详情
  - [ ] `PATCH /api/story-workspace/stories/:id` — 更新（用户编辑 Agent 生成内容）
  - [ ] `GET /api/story-workspace/characters` — 列表
  - [ ] `GET /api/story-workspace/characters/:id` — 详情
  - [ ] `PATCH /api/story-workspace/characters/:id` — 更新
  - [ ] `GET /api/story-workspace/scenes` — 列表
  - [ ] `GET /api/story-workspace/scenes/:id` — 详情
  - [ ] `PATCH /api/story-workspace/scenes/:id` — 更新
  - [ ] 列表接口返回标准分页格式 `{ data, pagination: { page, per_page, total, total_pages } }`
  - [ ] API 认证复用现有全局 Auth 中间件

- 前置依赖：`SUO-201-BE-001`

- 关联路径：
  - `backend/src/routes/story-workspace/`
  - `backend/src/services/story-workspace/`
  - `backend/src/validators/story-workspace/`

- 分发去向：`@BackendTaskAgent`

- 主责 Agent：`BackendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-004`：`story-workspace` 前缀命名
  - 设计稿 §6.1-6.2 API 路由设计

- 备注：
  - PATCH 更新接口用于用户编辑 Agent 生成内容，需校验 `agent_generated=true` 的字段允许编辑
  - 搜索使用 gin_trgm_ops 索引，需确认数据库已启用 pg_trgm 扩展

---

### SUO-201-BE-003

- 标题：审阅状态流转与批量操作 API
- 类型：backend
- 优先级：P0
- 标签：`api`,`review`,`workflow`
- 描述：
  实现审阅状态流转的核心 API：确认（confirm）、驳回（reject）、归档（archive）。包括单条审阅操作和批量审阅操作。状态流转需符合设计稿定义：pending → confirmed / rejected，confirmed 可进入后续执行流程，rejected 触发 Agent 重新生成。

- 验收条件：
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
  - [ ] 所有操作记录审计日志（可选，视现有系统能力）

- 前置依赖：`SUO-201-BE-002`

- 关联路径：
  - `backend/src/routes/story-workspace/`
  - `backend/src/services/story-workspace/review.service.ts`

- 分发去向：`@BackendTaskAgent`

- 主责 Agent：`BackendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-007`：核心工作流 Agent 产出 → 审阅确认
  - `DEC-008`：用户不手动创建，仅审阅
  - 设计稿 §4.5.1-4.5.4 交互设计

- 备注：
  - 驳回后的 Agent 重新生成流程设计稿标记为 `[CLARIFICATION_NEEDED]`，采用默认假设：通过同一 Chat 线程重新生成
  - 已确认内容的后续执行流程设计稿标记为 `[CLARIFICATION_NEEDED]`，采用默认假设：暂存，后续迭代定义

---

### SUO-201-BE-004

- 标题：Agent 产出数据接收与存储集成
- 类型：backend
- 优先级：P0
- 标签：`agent`,`integration`,`sse`
- 描述：
  实现 claude-agent 服务与 story-workspace 的数据集成。Agent 生成剧本/角色/场景后，通过内部 API 将数据存入 story-workspace 数据表，标记 `review_status='pending'` 和 `agent_generated=true`。需要复用现有 `claude-agent` 服务的 SSE 端点和 thread 机制。

- 验收条件：
  - [ ] Agent 生成剧本内容后，可调用 story-workspace API 存入数据
  - [ ] 数据存入时自动设置 `agent_generated=true`，`review_status='pending'`
  - [ ] 关联 `agent_session_id` 到 Chat thread ID
  - [ ] 角色和场景数据与故事数据一并存入，自动建立关联
  - [ ] 存入后 Dashboard 可正确显示「待审阅」计数
  - [ ] 与现有 `claude-agent` 服务集成不破坏现有 Chat / Deck 功能
  - [ ] 错误处理：Agent 生成失败时记录日志，不阻塞用户现有操作

- 前置依赖：`SUO-201-BE-001`

- 关联路径：
  - `backend/src/services/story-workspace/agent-integration.ts`
  - `backend/src/routes/story-workspace/`（内部接收端点）
  - `docs/CLAUDE.md`

- 分发去向：`@BackendTaskAgent`

- 主责 Agent：`BackendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-007`：核心工作流
  - 设计稿 §10.2 与 claude-agent 服务的集成
  - `docs/CLAUDE.md` §Thread Lifecycle

- 备注：
  - `[CLARIFICATION_NEEDED]` Agent 产出的触发方式：设计稿默认假设为用户在 Chat 中通过指令触发（如「生成一个关于...的剧本」）
  - `[CLARIFICATION_NEEDED]` 驳回后的重新生成流程：默认假设为通过同一 Chat 线程进行
  - `[RISK]` Agent 生成内容格式不固定，需定义最小数据契约（至少包含 title + 内容）
  - `[RISK]` Agent 生成与页面渲染的时序问题，需设计 Agent 生成中状态

---

### SUO-201-FE-001

- 标题：三栏布局骨架与全局样式
- 类型：frontend
- 优先级：P0
- 标签：`layout`,`ui`,`desktop-only`
- 描述：
  实现 Story Workspace 的桌面端三栏布局骨架：左侧 Sidebar 240px + 中间 Main Content（自适应）+ 右侧 Review Panel 360px。布局组件使用 `StoryWorkspace*` 前缀命名。严格遵循 Ink & Memory UI v2 视觉体系（暖纸张、轻纸面分区、无卡片设计）。本期仅桌面端，不包含任何移动端/平板端适配代码。

- 验收条件：
  - [ ] `StoryWorkspaceLayout` 根布局组件实现三栏结构
  - [ ] Sidebar 固定 240px，始终展开，不可折叠为图标栏
  - [ ] Main Content 填充剩余宽度
  - [ ] Review Panel 固定 360px，默认展开，可手动折叠
  - [ ] 页面背景 Warm Canvas #F6EFE5，内容区 Paper Cream #FFFAF2
  - [ ] 边框使用 Border Paper #D8C7B3 虚线
  - [ ] 确认无 `@media` 移动端查询代码
  - [ ] 确认无 `<768px` 或 `768px-1279px` 的响应式处理
  - [ ] 布局在 ≥1280px 下正确渲染

- 前置依赖：无

- 关联路径：
  - `frontend/src/components/story-workspace/layout/StoryWorkspaceLayout.tsx`
  - `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx`
  - `frontend/src/styles/tokens.css`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-001`：轻纸面分区布局
  - `DEC-003`：三栏桌面布局
  - `DEC-006`：仅桌面端
  - 设计稿 §4.4 布局交互

- 备注：
  - Review Panel 折叠行为：点击关闭按钮后表格恢复全宽，点击行再次展开
  - 布局组件需复用现有 AppHeader（全局）

---

### SUO-201-FE-002

- 标题：Sidebar 导航与路由配置
- 类型：frontend
- 优先级：P0
- 标签：`navigation`,`router`,`sidebar`
- 描述：
  实现 Story Workspace 的 Sidebar 导航组件和路由配置。Sidebar 包含工作台首页、故事管理、角色管理、场景管理导航项，以及底部设置入口。路由使用 `/story-workspace/*` 前缀。当前项使用 Memory Yellow 下划线指示。

- 验收条件：
  - [ ] `StoryWorkspaceSidebar` 组件实现，240px 宽度
  - [ ] 导航项：工作台首页、故事管理、角色管理、场景管理
  - [ ] 底部设置入口（跳转全局 Settings）
  - [ ] 当前项指示：Memory Yellow 下划线（2px，偏移 4px）
  - [ ] Hover 效果：背景色轻微变化
  - [ ] 路由配置：`/story-workspace` → redirect `/story-workspace/dashboard`
  - [ ] 子路由：`/dashboard`, `/stories`, `/characters`, `/scenes`
  - [ ] 路由文件：`frontend/src/router/story-workspace.tsx`

- 前置依赖：`SUO-201-FE-001`

- 关联路径：
  - `frontend/src/components/story-workspace/layout/StoryWorkspaceSidebar.tsx`
  - `frontend/src/router/story-workspace.tsx`
  - `frontend/src/pages/story-workspace/`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-003`：三栏桌面布局
  - `DEC-004`：`story-workspace` 前缀命名
  - 设计稿 §3.1 Sidebar 导航栏
  - 设计稿 §9 路由配置

- 备注：
  - Logo 区显示「Ink & Memory 创作者工作台」
  - 用户信息区显示头像和用户名（复用现有用户体系）

---

### SUO-201-FE-003

- 标题：数据表格组件（故事/角色/场景）
- 类型：frontend
- 优先级：P0
- 标签：`table`,`component`,`data-display`
- 描述：
  实现故事、角色、场景三个模块的数据表格组件。表格展示 Agent 生成的内容，支持搜索、筛选、排序、分页。表格行需实现审阅状态视觉标记（待审阅黄条、已驳回红条）、选中态（右侧 Action Brown 竖线）、Hover 效果。Toolbar 仅保留搜索、筛选、排序功能（本期无新建按钮）。

- 验收条件：
  - [ ] `StoryWorkspaceStoryTable`：展示标题、审阅状态、类型、角色数、场景数、生成时间、操作
  - [ ] `StoryWorkspaceCharacterTable`：展示头像、名称、身份、性格标签、关联故事、审阅状态、操作
  - [ ] `StoryWorkspaceSceneTable`：展示名称、描述、关联故事、关联角色、审阅状态、操作
  - [ ] 审阅状态标签样式符合规范（待审阅/已确认/已驳回/已归档）
  - [ ] 待审阅项：左侧 4px Memory Yellow 竖条
  - [ ] 已驳回项：左侧 4px 红色竖条 + 背景透明度 60%
  - [ ] 选中行：右侧 2px Action Brown 竖线
  - [ ] 搜索框：圆角 999px，宽度 240px
  - [ ] 筛选下拉：审阅状态、类型多选
  - [ ] 排序：点击表头排序，支持升序/降序/取消
  - [ ] 分页：默认 20 条/页
  - [ ] 批量选择：Checkbox 多选（仅限待审阅项）

- 前置依赖：`SUO-201-FE-002`

- 关联路径：
  - `frontend/src/components/story-workspace/table/`
  - `frontend/src/components/story-workspace/layout/StoryWorkspaceToolbar.tsx`
  - `frontend/src/components/story-workspace/layout/StoryWorkspaceBatchReviewToolbar.tsx`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-002`：复杂画布以数据表呈现
  - `DEC-008`：用户不手动创建
  - 设计稿 §3.2-3.3 Toolbar 与 Data Table
  - 设计稿 §4.5.2 表格交互

- 备注：
  - `[CLARIFICATION_NEEDED]` 故事/剧本内容编辑器：设计稿默认假设为纯文本/Markdown，富文本编辑器后续迭代
  - 批量操作栏在选中待审阅项时替换常规 Toolbar，背景 Action Brown 深色带

---

### SUO-201-FE-004

- 标题：审阅面板（Review Panel）与审阅操作
- 类型：frontend
- 优先级：P0
- 标签：`review`,`panel`,`workflow`
- 描述：
  实现审阅面板组件，展示 Agent 生成的完整内容，支持用户审阅确认操作。面板内包含：Agent 生成内容展示（只读/可编辑切换）、审阅状态指示、关联角色/场景列表、修改意见输入区、确认/驳回/编辑操作按钮。编辑模式下字段可修改，保存后可确认或仅保存。

- 验收条件：
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

- 前置依赖：`SUO-201-FE-003`

- 关联路径：
  - `frontend/src/components/story-workspace/review/`
  - `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-007`：核心工作流 Agent 产出 → 审阅确认
  - `DEC-008`：用户不手动创建，仅审阅
  - 设计稿 §3.4 Review Panel
  - 设计稿 §4.5.3 审阅面板交互

- 备注：
  - `[CLARIFICATION_NEEDED]` 角色头像上传规格：默认假设本期仅支持单张头像，四视角转面图后续迭代
  - `[CLARIFICATION_NEEDED]` 与 Deck 编辑器的关系：默认假设后续迭代明确
  - 编辑模式需区分「保存并确认」（状态变 confirmed）和「保存」（状态不变）

---

### SUO-201-FE-005

- 标题：工作台首页 Dashboard
- 类型：frontend
- 优先级：P1
- 标签：`dashboard`,`overview`
- 描述：
  实现工作台首页 Dashboard 页面。展示 Agent 产出概览（待审阅剧本数、已确认剧本数、最近 Agent 生成活动）、待审阅快捷入口（Agent 最新生成的剧本/角色/场景，点击直达审阅）、已确认剧本列表（最近确认）。空态时引导用户前往 Chat 触发 Agent 生成。

- 验收条件：
  - [ ] `StoryWorkspaceDashboardPage` 页面组件
  - [ ] 顶部：页面标题 + 审阅状态统计（待审阅数 / 已确认数 / 总数）
  - [ ] 中部：待审阅项快捷入口卡片（Agent 最新产出）
  - [ ] 下部：已确认剧本列表（最近确认，最多 5 条）
  - [ ] 空态：「还没有剧本内容，在 Chat 中让 Agent 为你生成剧本」
  - [ ] 统计数字实时更新
  - [ ] 快捷入口点击直达对应审阅面板

- 前置依赖：`SUO-201-FE-003`

- 关联路径：
  - `frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-007`：核心工作流
  - 设计稿 §4.3.1 工作台首页
  - 设计稿 §3.5.1 工作台首页空态

- 备注：
  - Dashboard 数据通过 `GET /api/story-workspace/stories` 等接口聚合
  - 空态图标使用 Charcoal Brown 线条 + Memory Yellow 点缀风格

---

### SUO-201-FE-006

- 标题：空态/加载/错误/选中态组件
- 类型：frontend
- 优先级：P1
- 标签：`state`,`ui`,`ux`
- 描述：
  实现各模块的完整状态组件：空态（无 Agent 产出、无待审阅项、搜索结果为空）、加载态（表格骨架屏、面板骨架屏）、错误态（加载失败、保存失败）、选中态（表格行选中、批量操作栏）。所有状态组件遵循 Ink & Memory 视觉规范。

- 验收条件：
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

- 前置依赖：`SUO-201-FE-003`

- 关联路径：
  - `frontend/src/components/story-workspace/state/`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-001`：轻纸面分区
  - 设计稿 §5 状态设计
  - 设计稿 §3.5-3.6 空态与错误态

- 备注：
  - 空态图标风格：Charcoal Brown 线条 + Memory Yellow 点缀，64px
  - 骨架屏背景：color-mix(Paper Cream 90%, Muted Tan)

---

### SUO-201-SH-001

- 标题：前端-后端联调：审阅工作流 E2E
- 类型：shared
- 优先级：P0
- 标签：`e2e`,`integration`,`review-workflow`
- 描述：
  端到端验证 Agent 产出 → 页面渲染 → 用户审阅确认的完整工作流。包括：Agent 生成数据后前端正确展示、审阅状态标记正确、确认/驳回/编辑后确认操作完整、批量审阅可用、状态流转正确。需要前后端 Agent 协作完成联调。

- 验收条件：
  - [ ] Agent 生成剧本数据后，Dashboard 显示「1 项待审阅」
  - [ ] 故事列表中新生成项左侧显示 Memory Yellow 竖条
  - [ ] 点击待审阅行，右侧 Review Panel 正确展示 Agent 生成内容
  - [ ] 点击「确认通过」→ 状态变为 confirmed → Toast「已确认」→ 表格刷新
  - [ ] 点击「驳回」→ 填写修改意见 → 状态变为 rejected → Toast「已驳回」→ 行变红色标记
  - [ ] 编辑模式：修改字段 → 「保存并确认」→ 状态 confirmed
  - [ ] 批量审阅：多选待审阅项 → 批量确认/驳回 → 确认弹窗 → 操作完成
  - [ ] 筛选：按审阅状态筛选后表格正确刷新
  - [ ] 排序：按生成时间/标题排序正确
  - [ ] 分页：切换页码正确加载数据
  - [ ] 空态：无数据时正确显示空态引导
  - [ ] 错误态：API 失败时正确显示错误提示

- 前置依赖：`SUO-201-BE-003`, `SUO-201-FE-004`

- 关联路径：
  - `frontend/src/components/story-workspace/`
  - `backend/src/routes/story-workspace/`
  - `backend/src/services/story-workspace/`

- 分发去向：`@FrontendTaskAgent` + `@BackendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：`BackendTaskAgent`

- 设计决策引用：
  - `DEC-007`：核心工作流
  - 设计稿 §4.1-4.3 关键交互流程

- 备注：
  - 前端职责：审阅面板 UI、审阅操作交互、状态展示、表格刷新
  - 后端职责：审阅状态流转 API、数据持久化、批量操作
  - 联调验证点：状态变更后前端实时刷新（轮询或 WebSocket，本期建议轮询）
  - `[RISK]` Agent 生成与页面渲染的时序问题，需验证 Agent 生成中状态的 Loading 指示

---

### SUO-201-SH-002

- 标题：命名规范与类型定义共享包
- 类型：shared
- 优先级：P0
- 标签：`naming`,`types`,`shared`
- 描述：
  建立 story-workspace 的命名规范和共享类型定义包。包括 TypeScript 类型/接口、API 请求/响应类型、状态枚举定义。确保前后端命名一致，所有标识使用 `story-workspace` 前缀。

- 验收条件：
  - [ ] 共享类型包定义：StoryWorkspaceStory, StoryWorkspaceCharacter, StoryWorkspaceScene, StoryWorkspaceWorkspace
  - [ ] 审阅状态枚举：ReviewStatus = 'pending' | 'confirmed' | 'rejected'
  - [ ] 内容状态枚举：ContentStatus = 'draft' | 'published' | 'archived'
  - [ ] 故事类型枚举：StoryType = 'short' | 'long' | 'script' | 'outline'
  - [ ] API 列表响应类型：PaginatedResponse<T>
  - [ ] 筛选参数类型：StoryFilter, CharacterFilter, SceneFilter
  - [ ] 前后端引用同一类型定义源
  - [ ] 命名前缀检查清单：路由、组件、API、数据库表、类型、Hooks、CSS 类

- 前置依赖：无

- 关联路径：
  - `shared/types/story-workspace/`
  - `frontend/src/types/story-workspace/`
  - `backend/src/types/story-workspace/`

- 分发去向：`@FrontendTaskAgent` + `@BackendTaskAgent`

- 主责 Agent：`BackendTaskAgent`

- 协作 Agent：`FrontendTaskAgent`

- 设计决策引用：
  - `DEC-004`：`story-workspace` 前缀命名
  - 设计稿 §4.2 命名映射
  - 设计稿 §14.1 命名前缀汇总

- 备注：
  - 优先定义类型，前后端并行开发时作为合同
  - 类型定义应放在 monorepo 的 shared package 中（如果存在），否则前后端各自维护并保持一致

---

### SUO-201-DO-001

- 标题：Story Workspace 使用文档
- 类型：docs
- 优先级：P2
- 标签：`documentation`,`user-guide`
- 描述：
  编写 Story Workspace 的使用文档，包括功能概述、审阅工作流说明、常见问题。面向内部团队和后续维护者。

- 验收条件：
  - [ ] 文档包含功能概述（各模块说明）
  - [ ] 审阅工作流说明（Agent 产出 → 审阅确认流程）
  - [ ] 命名规范速查表
  - [ ] API 端点速查表
  - [ ] 常见问题（FAQ）

- 前置依赖：`SUO-201-SH-001`

- 关联路径：
  - `docs/issue/ISSUES_story-workspace.md`
  - `docs/design/story-workspace/`

- 分发去向：`@FrontendTaskAgent`

- 主责 Agent：`FrontendTaskAgent`

- 协作 Agent：无

- 设计决策引用：
  - 设计稿 §1-3 背景与方案摘要

- 备注：
  - 文档放在 `docs/` 下合适位置，不写入 `docs/design/`（禁止修改设计稿）

---

## 4. 共享任务与依赖说明

- `SUO-201-SH-002`（命名规范与类型定义共享包）是所有前后端工作的前置基础；在该 Issue 未完成前，前后端应基于设计稿中的类型定义先行开发，后续对齐。
- `SUO-201-BE-001`（数据库 Schema）是后端工作的前置基础；`SUO-201-BE-002` 依赖其完成。
- `SUO-201-BE-003`（审阅状态流转 API）依赖 `SUO-201-BE-002`（REST API）。
- `SUO-201-FE-001`（三栏布局）是前端工作的前置基础；`SUO-201-FE-002` 依赖其完成。
- `SUO-201-FE-003`（数据表格）依赖 `SUO-201-FE-002`（Sidebar 导航）。
- `SUO-201-FE-004`（审阅面板）依赖 `SUO-201-FE-003`（数据表格）。
- `SUO-201-SH-001`（E2E 联调）是 shared 类型 Issue，需要 `FrontendTaskAgent` 与 `BackendTaskAgent` 协作完成，必须在 `SUO-201-BE-003` 和 `SUO-201-FE-004` 完成后推进。
- `SUO-201-BE-004`（Agent 集成）可与前端并行开发，但 E2E 验证需等待前后端均完成。
- 若后续发现某个 Issue 的实现范围超出当前设计稿，必须回到 Issue 评论区记录澄清，不得直接下沉到 task 阶段。
- 若某个 Issue 需要新增设计决策，必须标记 `[CLARIFICATION_NEEDED]`，由 `CEOOrchestrator` 判断是否回退到 `DesignArchitect`。

---

## 5. 分发去向说明

- `BackendTaskAgent`：
  - 领取 `SUO-201-BE-001`（数据库 Schema）、`SUO-201-BE-002`（REST API）、`SUO-201-BE-003`（审阅状态流转）、`SUO-201-BE-004`（Agent 集成）。
  - 负责接口、数据处理、Schema、Migration、服务端逻辑、校验链路。
  - 作为主责 Agent 负责 `SUO-201-SH-002`（命名规范与类型定义）。

- `FrontendTaskAgent`：
  - 领取 `SUO-201-FE-001`（三栏布局）、`SUO-201-FE-002`（Sidebar 导航）、`SUO-201-FE-003`（数据表格）、`SUO-201-FE-004`（审阅面板）、`SUO-201-FE-005`（Dashboard）、`SUO-201-FE-006`（状态组件）。
  - 负责 UI、交互、状态管理、前端接口消费、页面结构。
  - 作为主责 Agent 负责 `SUO-201-SH-001`（E2E 联调）和 `SUO-201-DO-001`（使用文档）。

- `Shared Issue` 处理规则：
  - `SUO-201-SH-001`（E2E 联调）：主责 `FrontendTaskAgent`，协作 `BackendTaskAgent`。
  - `SUO-201-SH-002`（命名规范）：主责 `BackendTaskAgent`，协作 `FrontendTaskAgent`。
  - 两个 shared Issue 均有唯一主责 Agent，不允许无主责状态。

---

## 6. 推荐推进顺序

```text
Phase 1: 基础准备（可并行）
├── SUO-201-SH-002  命名规范与类型定义共享包
├── SUO-201-BE-001  数据库 Schema 与数据表初始化
└── SUO-201-FE-001  三栏布局骨架与全局样式

Phase 2: 前后端核心开发（可并行，依赖 Phase 1）
├── Backend:
│   ├── SUO-201-BE-002  REST API 实现
│   └── SUO-201-BE-004  Agent 产出数据接收与存储集成
└── Frontend:
    ├── SUO-201-FE-002  Sidebar 导航与路由配置
    ├── SUO-201-FE-003  数据表格组件
    └── SUO-201-FE-004  审阅面板与审阅操作

Phase 3: 后端审阅工作流（依赖 Phase 2 Backend）
└── SUO-201-BE-003  审阅状态流转与批量操作 API

Phase 4: 前端完善（依赖 Phase 2 Frontend）
├── SUO-201-FE-005  工作台首页 Dashboard
└── SUO-201-FE-006  空态/加载/错误/选中态组件

Phase 5: 联调与验证（依赖 Phase 2-4）
└── SUO-201-SH-001  前端-后端联调：审阅工作流 E2E

Phase 6: 文档（依赖 Phase 5）
└── SUO-201-DO-001  Story Workspace 使用文档
```

---

## 7. 阻塞与澄清记录

### [CLARIFICATION_NEEDED] 角色头像上传规格

- 歧义点：角色头像是否需要四视角转面图？本期仅支持单张头像？
- 可能解释 A：本期仅支持单张头像上传
- 可能解释 B：需要支持多视角头像上传
- 默认采用解释 A：本期仅支持单张头像，四视角转面图为后续迭代
- 需要确认方：`CEOOrchestrator` / 产品方
- 是否阻塞 task 阶段：否（可采用默认假设继续）
- 风险：若后续需求变更为多视角，需重新设计头像上传组件

### [CLARIFICATION_NEEDED] 故事/剧本内容编辑器

- 歧义点：详情面板中故事内容的编辑方式（纯文本/Markdown/富文本）？
- 可能解释 A：纯文本/Markdown 编辑
- 可能解释 B：富文本编辑器
- 默认采用解释 A：本期为纯文本/Markdown，富文本编辑器后续迭代
- 需要确认方：`CEOOrchestrator` / 产品方
- 是否阻塞 task 阶段：否
- 风险：若用户期望富文本编辑，本期体验可能不足

### [CLARIFICATION_NEEDED] 与 Deck 编辑器的关系

- 歧义点：故事内容是否与 Deck 系统打通？
- 可能解释 A：本期独立，后续迭代考虑与 Deck 集成
- 可能解释 B：需要本期打通 Deck 编辑器
- 默认采用解释 A：与 Deck 编辑器的关系在后续迭代中明确
- 需要确认方：`CEOOrchestrator` / 产品方
- 是否阻塞 task 阶段：否
- 风险：已确认内容暂存，后续执行流程未定义

### [CLARIFICATION_NEEDED] Agent 产出的触发方式

- 歧义点：用户如何在 Chat 中触发 Agent 生成剧本？是否需要专门的指令或按钮？
- 可能解释 A：用户通过自然语言指令触发（如「生成一个关于...的剧本」）
- 可能解释 B：需要专门的 UI 按钮或指令模板
- 默认采用解释 A：Agent 产出通过现有 Chat 对话中的指令触发
- 需要确认方：`CEOOrchestrator` / `DesignArchitect`
- 是否阻塞 task 阶段：否
- 风险：触发方式不明确可能导致用户发现成本过高

### [CLARIFICATION_NEEDED] 驳回后的重新生成流程

- 歧义点：用户驳回后，Agent 重新生成的时序和通知机制？
- 可能解释 A：通过同一 Chat 线程重新生成
- 可能解释 B：需要异步队列 + 通知机制
- 默认采用解释 A：驳回后 Agent 重新生成通过同一 Chat 线程进行
- 需要确认方：`CEOOrchestrator` / `DesignArchitect`
- 是否阻塞 task 阶段：否
- 风险：重新生成时序不确定，用户体验可能不一致

### [CLARIFICATION_NEEDED] 已确认内容的后续执行

- 歧义点：用户确认后，内容进入什么下游流程？（Deck 生成？发布？）
- 可能解释 A：已确认内容暂存，后续执行流程在后续迭代中定义
- 可能解释 B：需要本期定义并接入下游流程
- 默认采用解释 A：已确认内容暂存，后续执行流程在后续迭代中定义
- 需要确认方：`CEOOrchestrator` / 产品方
- 是否阻塞 task 阶段：否
- 风险：用户确认后无明确反馈，可能产生「确认后什么都没发生」的困惑

---

## 8. Issue-First 协作说明

- Issue 是最小调度单元。
- 同一 Issue 任一时刻只允许一个主责 Agent。
- shared Issue 必须有主责 Agent 与协作 Agent。
- 必须通过 Issue 评论区补充上下文、阻塞、回退和评审意见。
- 必须通过 `@mention` 唤醒目标 Agent。
- 不假设 Agent 之间存在隐式共享内存。
- 不允许绕过 Issue 直接下发 task。
- 所有 Agent 间协作以 Issue 线程、Issue 文档和关联产物为准。
