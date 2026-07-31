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
| `task_202b` (FE-002 Sidebar 导航) | ⏳ 需先完成 | 提供页面骨架和路由 |
| `SUO-201-BE-002` (REST API) | ⏳ 并行 | 数据 API 接口 |
| `SUO-201-SH-002` (共享类型包) | ⏳ 可选 | TypeScript 类型定义 |
| `frontend/src/styles/tokens.css` | ✅ 已存在 | 色彩系统 |

**本任务被依赖**：
- `task_202d` (FE-004 审阅面板) — 依赖表格行选中
- `task_202e` (FE-005 Dashboard) — 依赖表格数据展示
- `task_202f` (FE-006 状态组件) — 依赖表格骨架

---

## 8. 测试策略

1. **视觉测试**：
   - 审阅状态标记正确（黄条/红条/竖线）
   - 标签样式符合规范
   - 行高 56px，Hover 效果正常

2. **交互测试**：
   - 点击行选中，右侧出现 Action Brown 竖线
   - 点击行后右侧 Review Panel 展开
   - Checkbox 多选仅限待审阅项
   - 多选后 Toolbar 替换为批量操作栏

3. **功能测试**：
   - 搜索框输入后表格过滤
   - 筛选下拉选择后表格过滤
   - 点击表头排序（升序/降序/取消）
   - 分页切换正确

4. **API 集成测试**：
   - Hooks 正确调用 `/api/story-workspace/stories` 等接口
   - 正确处理分页响应格式

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

**✅ 范围内**：
- 三个模块的数据表格
- 搜索、筛选、排序、分页
- 审阅状态视觉标记
- 批量选择操作栏
- 数据查询 Hooks

**❌ 范围外**：
- 审阅面板内部实现（FE-004 负责）
- 审阅操作 API 调用（FE-004 负责）
- Dashboard 页面（FE-005 负责）
- 空态/加载/错误组件（FE-006 负责）
- 新建/创建功能（DEC-008 排除）
