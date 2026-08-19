# task_202c_frontend_data-table-components.md

> **Task ID**: `task_202c`  
> **关联 Issue**: `SUO-201-FE-003` — `数据表格组件（故事/角色/场景）`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **设计决策**: `DEC-002`, `DEC-008`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace 数据表格组件实现（故事/角色/场景）

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-FE-003` | 数据表格组件（故事/角色/场景） | frontend | P0 |

---

## 3. 任务目标

实现故事、角色、场景三个模块的数据表格组件。表格展示 Agent 生成的内容，支持搜索、筛选、排序、分页。表格行需实现审阅状态视觉标记（待审阅黄条、已驳回红条）、选中态（右侧 Action Brown 竖线）、Hover 效果。Toolbar 仅保留搜索、筛选、排序功能（本期无新建按钮）。

---

## 4. 实现步骤

1. **创建表格组件目录结构**
   - `frontend/src/components/story-workspace/table/`

2. **实现通用表格行组件 `StoryWorkspaceTableRow`**
   - 行高 56px
   - Hover 效果：背景色变化
   - 选中态：右侧 2px Action Brown 竖线
   - 待审阅：左侧 4px Memory Yellow 竖条
   - 已驳回：左侧 4px 红色竖条 + 背景透明度 60%
   - Checkbox 多选（仅限待审阅项）

3. **实现 `StoryWorkspaceStoryTable`**
   - 字段：标题、审阅状态、类型、角色数、场景数、生成时间、操作
   - 标题列可排序
   - 审阅状态标签样式符合规范

4. **实现 `StoryWorkspaceCharacterTable`**
   - 字段：头像、名称、身份、性格标签、关联故事、审阅状态、操作
   - 性格标签以胶囊标签展示
   - 头像占位处理

5. **实现 `StoryWorkspaceSceneTable`**
   - 字段：名称、描述、关联故事、关联角色、审阅状态、操作

6. **实现 Toolbar 组件 `StoryWorkspaceToolbar`**
   - 搜索框：圆角 999px，宽度 240px
   - 筛选下拉：审阅状态、类型多选
   - 排序下拉
   - **无新建按钮**（DEC-008：用户不手动创建）

7. **实现批量审阅操作栏 `StoryWorkspaceBatchReviewToolbar`**
   - 多选时替换常规 Toolbar
   - 背景 Action Brown 深色带
   - 显示已选择数量
   - 批量确认/驳回按钮 + 取消按钮

8. **实现审阅状态标签 `StoryWorkspaceReviewStatusBadge`**
   - 待审阅：Memory Yellow 15% 背景
   - 已确认：Spark Green 15% 背景
   - 已驳回：#E74C3C 10% 背景 + 虚线边框
   - 已归档：Muted Tan 20% 背景

9. **实现分页组件 `StoryWorkspacePagination`**
   - 默认 20 条/页
   - 标准分页控件

10. **数据获取 Hooks**
    - `useStories()` — 故事数据查询
    - `useCharacters()` — 角色数据查询
    - `useScenes()` — 场景数据查询
    - 支持搜索、筛选、排序、分页参数

11. **接入现有列表页并补齐导出**
    - 将 `StoryWorkspaceStoryTable`、`StoryWorkspaceCharacterTable`、`StoryWorkspaceSceneTable` 分别接入现有 Stories / Characters / Scenes 页面骨架，替换当前“后续数据表格任务中接入”的占位内容。
    - 三个页面只组合本 task 的 Toolbar、Table、Pagination 与查询 Hook；不得在本 task 内实现 Review Panel、Dashboard 或路由逻辑。
    - 更新 `layout/index.ts` 与 `components/story-workspace/index.ts` 的最小导出，使页面通过稳定 barrel 引用本 task 组件。

---

## 5. 涉及文件路径

**新增文件**：
- `frontend/src/components/story-workspace/table/`（目录）
- `frontend/src/components/story-workspace/table/StoryWorkspaceStoryTable.tsx`
- `frontend/src/components/story-workspace/table/StoryWorkspaceCharacterTable.tsx`
- `frontend/src/components/story-workspace/table/StoryWorkspaceSceneTable.tsx`
- `frontend/src/components/story-workspace/table/StoryWorkspaceTableRow.tsx`
- `frontend/src/components/story-workspace/table/StoryWorkspacePagination.tsx`
- `frontend/src/components/story-workspace/table/StoryWorkspaceReviewStatusBadge.tsx`
- `frontend/src/components/story-workspace/table/index.ts`
- `frontend/src/components/story-workspace/layout/StoryWorkspaceToolbar.tsx`
- `frontend/src/components/story-workspace/layout/StoryWorkspaceBatchReviewToolbar.tsx`
- `frontend/src/hooks/story-workspace/`（目录）
- `frontend/src/hooks/story-workspace/useStories.ts`
- `frontend/src/hooks/story-workspace/useCharacters.ts`
- `frontend/src/hooks/story-workspace/useScenes.ts`
- `frontend/src/hooks/story-workspace/index.ts`

**修改文件（页面接入与导出闭环）**：
- `frontend/src/components/story-workspace/layout/index.ts`
- `frontend/src/components/story-workspace/index.ts`
- `frontend/src/pages/story-workspace/StoryWorkspaceStoriesPage.tsx`
- `frontend/src/pages/story-workspace/StoryWorkspaceCharactersPage.tsx`
- `frontend/src/pages/story-workspace/StoryWorkspaceScenesPage.tsx`

**复用文件**（只读）：
- `frontend/src/styles/tokens.css` — 色彩 token

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §3.2-3.3 Toolbar 与 Data Table
- 布局设计稿 §3.3 Data Table 线框
- 设计稿 §4.5.2 表格交互
- 设计稿 §5.4 选中态

**输出**：
- 3 个专用表格组件（Story/Character/Scene）
- 1 个通用表格行组件
- 1 个审阅状态标签组件
- 1 个分页组件
- Toolbar 和批量操作栏组件
- 3 个数据查询 Hooks

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_202b` (FE-002 Sidebar 导航) | ✅ 已完成（SUO-265） | 已提供三个列表页骨架和 canonical 路由 |
| `SUO-201-BE-002` (REST API) | ✅ 已完成（SUO-264） | 已提供列表查询、搜索、筛选、排序与分页接口 |
| `SUO-201-SH-002` (共享类型包) | ⏳ 可选 | TypeScript 类型定义 |
| `frontend/src/styles/tokens.css` | ✅ 已存在 | 色彩系统 |

**本任务被依赖**：
- `task_202d` (FE-004 审阅面板) — 依赖表格行选中
- `task_202e` (FE-005 Dashboard) — 依赖表格数据展示
- `task_202f` (FE-006 状态组件) — 依赖表格骨架

---

## 8. 测试策略

### 8.1 可执行命令

1. **构建**（从仓库根目录执行）：
   ```bash
   cd frontend && npm run build
   ```
   通过标准：TypeScript 构建与 Vite 打包均成功。
2. **本 task scoped lint**（从仓库根目录执行）：
   ```bash
   cd frontend && npx eslint src/components/story-workspace/table src/components/story-workspace/layout/StoryWorkspaceToolbar.tsx src/components/story-workspace/layout/StoryWorkspaceBatchReviewToolbar.tsx src/components/story-workspace/layout/index.ts src/components/story-workspace/index.ts src/hooks/story-workspace src/pages/story-workspace/StoryWorkspaceStoriesPage.tsx src/pages/story-workspace/StoryWorkspaceCharactersPage.tsx src/pages/story-workspace/StoryWorkspaceScenesPage.tsx
   ```
   通过标准：本 task 闭集内无 ESLint error；若全仓历史 warning/error 不在闭集内，必须单独记录，不得越界修复。
3. **单元测试**：`N/A`。当前 `frontend/package.json` 没有测试 runner 或 `test` script；本 task 禁止通过修改 `package.json`、lockfile 或新增依赖来引入测试框架。
4. **浏览器验证**：以 1280px 桌面视口逐一访问 `/story-workspace/stories`、`/story-workspace/characters`、`/story-workspace/scenes`，保留三页截图、交互记录及相关列表请求的 Network 证据。

### 8.2 验收与验证映射

| 验收 ID | 验收条件 | 对应验证 |
|---|---|---|
| `AC-202C-01` | 三个页面不再显示占位文案，分别实际渲染 Story / Character / Scene 表格；页面可通过现有 Sidebar 和 canonical 路由到达 | 构建 + 三路由 1280px 截图 |
| `AC-202C-02` | Hooks 使用 `/api/story-workspace/stories|characters|scenes`，正确处理 `{ data, pagination }`；搜索、筛选、排序、分页产生与 REST 基线一致的 `q`、`review_status`、`sort`、`order`、`page`、`per_page` 参数 | 浏览器交互 + Network 请求/响应证据 |
| `AC-202C-03` | pending 黄条、rejected 红条、选中态右侧 Action Brown 竖线、56px 行高与 Hover 可见 | 三类状态 fixture/真实数据截图 |
| `AC-202C-04` | Checkbox 仅允许 pending 项；选择后批量栏替换常规 Toolbar，取消后恢复；本 task 只验证批量栏状态，不调用审阅 API | 浏览器交互记录 |
| `AC-202C-05` | scoped lint 与 build 通过，实际 diff 只命中允许闭集；未修改 Review Panel、Dashboard、router/App、依赖文件或排除能力 | 命令输出 + `git diff --name-only` / `git diff --check` |

> 本 task 不把“点击行后 Review Panel 展开”作为验收条件；它属于 `task_202d`。若当前环境没有可用 API 数据，可使用浏览器网络层临时响应完成视觉/交互验证，但不得把 mock 文件写入仓库。

---

## 9. 完成标志

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
- [ ] 批量操作栏在选中时替换常规 Toolbar
- [ ] 三个现有列表页分别接入对应表格，不再渲染占位文案
- [ ] `layout/index.ts` 与 `components/story-workspace/index.ts` 完成最小导出
- [ ] `AC-202C-01`～`AC-202C-05` 均有对应验证证据，build 与 scoped lint 通过

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| API 接口尚未实现 | 中 | 使用 Mock 数据或 MSW 拦截开发，等后端就绪后切换 |
| 共享类型包未完成 | 低 | 先基于设计稿定义本地类型，后续迁移到共享包 |
| 性格标签展示长度 | 低 | 标签过多时截断或换行，保持行高不变 |
| 头像占位处理 | 低 | 无头像时显示默认占位图标（Charcoal Brown） |

---

## 附录：表格组件接口定义

```typescript
// 通用表格 Props
interface StoryWorkspaceTableProps<T> {
  data: T[];
  loading: boolean;
  selectedIds: string[];
  onSelect: (id: string) => void;
  onSelectAll: () => void;
  onRowClick: (item: T) => void;
  pagination: PaginationState;
  onPageChange: (page: number) => void;
}

// 审阅状态枚举
enum ReviewStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  REJECTED = 'rejected',
  ARCHIVED = 'archived',
}

// 故事类型枚举
enum StoryType {
  SHORT = 'short',
  LONG = 'long',
  SCRIPT = 'script',
  OUTLINE = 'outline',
}
```

---

## 范围边界

**✅ 范围内**（本 task 允许实现）：
- 三个模块的数据表格
- 搜索、筛选、排序、分页
- 审阅状态视觉标记
- 批量选择操作栏
- 数据查询 Hooks

**❌ 范围外**（本 task 不实现）：
- 审阅面板内部实现（FE-004 负责）
- 审阅操作 API 调用（FE-004 负责）
- Dashboard 页面（FE-005 负责）
- 空态/加载/错误组件（FE-006 负责）
- 新建/创建功能（DEC-008 排除）

---

## 执行边界（增量修正）

### 允许修改范围
- `frontend/src/components/story-workspace/table/**` — 仅创建/修改本 task 的表格、表格样式、状态标签与分页组件。
- `frontend/src/components/story-workspace/layout/StoryWorkspaceToolbar.tsx` — 仅实现搜索/筛选/排序 Toolbar。
- `frontend/src/components/story-workspace/layout/StoryWorkspaceBatchReviewToolbar.tsx` — 仅实现 pending 多选后的批量栏视觉与回调合同。
- `frontend/src/components/story-workspace/layout/index.ts` — 仅追加上述两个 Toolbar 的导出。
- `frontend/src/components/story-workspace/index.ts` — 仅追加 table / layout 的必要导出，不重组既有导出。
- `frontend/src/hooks/story-workspace/**` — 仅创建/修改三类列表查询 Hooks 及其本地类型/导出。
- `frontend/src/pages/story-workspace/StoryWorkspaceStoriesPage.tsx` — 仅替换占位内容并组合 Story Toolbar/Table/Pagination/Hook。
- `frontend/src/pages/story-workspace/StoryWorkspaceCharactersPage.tsx` — 仅替换占位内容并组合 Character Toolbar/Table/Pagination/Hook。
- `frontend/src/pages/story-workspace/StoryWorkspaceScenesPage.tsx` — 仅替换占位内容并组合 Scene Toolbar/Table/Pagination/Hook。

### 禁止修改范围
- **禁止修改** `docs/design/` 目录下任何文件
- **禁止修改** `docs/issue/` 目录下任何文件
- **禁止修改** `docs/stage/` 目录下任何文件
- **禁止修改** `docs/exec/` 目录下任何文件
- **禁止修改** `docs/task/` 下其他 task 文件
- **禁止修改** 后端代码（`backend/src/` 等）
- **禁止修改** 现有全局表格组件（如有）的核心逻辑
- **禁止修改** `docs/task/TASK-REQUIREMENT-FORMAT.md`
- **禁止修改** `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewPanel.tsx`、`frontend/src/pages/story-workspace/StoryWorkspaceDashboardPage.tsx`、`frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`
- **禁止修改** `frontend/src/router/story-workspace.tsx`、`frontend/src/App.tsx`、`frontend/package.json`、任何 lockfile；现有路由已由 `task_202b` 提供
- **禁止新增** 仓库内 mock、快照或测试 runner 配置；当前无前端测试框架，验证采用 build、scoped lint 与浏览器证据

### 明确排除项
- **复杂画布**：本 task 的表格仅使用标准 HTML table 或 CSS Grid/Flexbox 布局，不涉及 Canvas 渲染、虚拟滚动 Canvas 实现、大数据量 Canvas 优化等
- **视频**：本 task 表格单元格中不包含视频播放器、视频预览、视频缩略图展示
- **移动端**：本 task 表格明确排除移动端适配，不包含横向滚动优化、卡片式布局转换、触摸手势支持等移动端表格特性
- **用户手动创建内容**：本 task 的 Toolbar **明确排除**「新建」按钮（DEC-008 决策：用户不手动创建内容）。表格仅展示 Agent 生成的内容，不提供用户手动添加/创建故事/角色/场景的入口
- **复杂表格功能**：不涉及树形表格、嵌套表格、行内编辑、拖拽排序、列宽拖拽调整、冻结列等高级表格功能
- **实时更新**：表格数据刷新采用轮询机制，不涉及 WebSocket 实时推送、Server-Sent Events 等实时数据更新技术
- **导出功能**：不涉及 Excel/CSV/PDF 导出功能

---

## SUO-270 Execute Readiness Delta

### 准入项

- `SUO-264` REST API 与 `SUO-265` Sidebar/路由/页面骨架均已有完成回执和最小验证；本 task 的两项硬接入前提已满足。
- 仓库现有 `build`、ESLint 与 1280px 浏览器路径足以形成最小充分验证，不依赖新增测试框架。

### 本次修正项

- 把三个列表页、两个 barrel export 纳入最小写入闭集，并增加页面接入步骤。
- 删除跨 task 的 Review Panel 展开验收，建立 `AC-202C-01`～`AC-202C-05` 与可执行验证的一一映射。
- 显式冻结 App/router、Dashboard/Dream、依赖与测试框架配置，保留数据表替代复杂画布及既有排除项。

### 仍阻塞项

- **task 文档自身：无。**
- **StagePlanner 后续**：`docs/stage/stage_story-workspace.md` §7.1 仍只列 table/Toolbar/hooks，未列三个页面与两个 export；须由独立 StagePlanner 子单同步后，才能以 Task + Stage 联合作为 execute 最终准入证据。本 Issue 不修改 Stage。
