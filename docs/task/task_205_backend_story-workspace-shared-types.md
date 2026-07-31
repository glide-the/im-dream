# task_205_backend_story-workspace-shared-types

## 1. 任务标题

Story Workspace 命名规范与类型定义共享包（后端主责）

## 2. 关联 Issue

- **Issue ID**: `SUO-201-SH-002`
- **Issue 标题**: 命名规范与类型定义共享包
- **类型**: `shared`
- **优先级**: P0
- **标签**: `naming`, `types`, `shared`
- **来源设计稿**:
  - `docs/design/story-workspace/story-workspace-prd.md` §3.1 `DEC-004`（`story-workspace` 前缀命名）
  - `docs/design/story-workspace/story-workspace-prd.md` §4.2（命名映射）
  - `docs/design/story-workspace/story-workspace-prd.md` §14.1（命名前缀汇总）
  - `docs/design/story-workspace/story-workspace-layout-design.md` §5.1–5.5（数据表结构）
  - `docs/design/story-workspace/story-workspace-layout-design.md` §8（Zustand Store 结构）
- **Issue 清单**: `docs/issue/ISSUES_story-workspace.md` §3 Issue 明细、§5 分发去向说明
- **主责 Agent**: `BackendTaskAgent`
- **协作 Agent**: `FrontendTaskAgent`

## 3. 任务目标

建立 `story-workspace` 的命名规范和共享类型定义包，确保前后端在业务标识、数据模型、状态枚举、API 合同上保持一致。BackendTaskAgent 作为类型合同的**唯一主责方**，输出后端可消费的 Python 模型作为规范源；FrontendTaskAgent 仅负责消费并对齐到 TypeScript。

**核心约束**：
- 所有业务标识必须使用 `story-workspace` 前缀（DEC-004）。
- 后端 Python 模型是**唯一规范源**；前端 TypeScript 类型必须与其字段、类型、可选性保持一致。
- 若项目暂无 monorepo shared package，则后端类型放在 `backend/types/story-workspace/`，前端镜像放在 `frontend/src/types/story-workspace/`，并在本任务文档中声明同步机制。
- 禁止在 task 文档中直接实现代码；仅定义类型合同与命名检查清单。
- 本任务**不**负责 Agent 产出 prompt 模板或 UI 组件类型；仅负责业务数据类型与命名规范。

## 4. 实现步骤

### Step 1: 确定共享类型物理位置

根据项目当前结构（`backend/` 为 Python/FastAPI，`frontend/` 为 TypeScript/React，根目录无 `shared/` package），推荐方案：

| 位置 | 用途 | 说明 |
|------|------|------|
| `backend/types/story-workspace/` | **规范源（Canonical）** | Python dataclass / Pydantic 模型，BackendTaskAgent 主责 |
| `frontend/src/types/story-workspace/` | **消费端镜像** | TypeScript interfaces/types，FrontendTaskAgent 主责 |
| `docs/task/task_205_backend_story-workspace-shared-types.md` | **合同文档** | 本任务文档，记录字段对照表与同步规则 |

> 若项目后续引入 monorepo shared package，则迁移到 `shared/types/story-workspace/`，并废弃上述两个镜像目录。

### Step 2: 创建后端类型定义文件（规范源）

新建 `backend/types/story-workspace/__init__.py`，使用 Python dataclass 定义：

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

class ReviewStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

class ContentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class StoryType(str, Enum):
    SHORT = "short"
    LONG = "long"
    SCRIPT = "script"
    OUTLINE = "outline"

class RoleType(str, Enum):
    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    EXTRA = "extra"

class BatchAction(str, Enum):
    CONFIRM = "confirm"
    REJECT = "reject"
    ARCHIVE = "archive"

class ResourceType(str, Enum):
    STORY = "story"
    CHARACTER = "character"
    SCENE = "scene"

@dataclass
class StoryWorkspaceStory:
    id: str
    identifier: str
    title: str
    description: Optional[str] = None
    status: ContentStatus = ContentStatus.DRAFT
    review_status: ReviewStatus = ReviewStatus.PENDING
    type: StoryType = StoryType.SHORT
    content: Optional[str] = None
    author_id: int = 0
    workspace_id: str = ""
    character_count: int = 0
    scene_count: int = 0
    agent_generated: bool = True
    agent_session_id: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

# StoryWorkspaceCharacter / StoryWorkspaceScene / StoryWorkspaceWorkspace
# StoryWorkspaceStoryDetail / StoryWorkspaceCharacterDetail / StoryWorkspaceSceneDetail
# StoryWorkspaceStoryCharacter / StoryWorkspaceSceneCharacter
# PaginatedResponse / PaginationInfo / StoryFilter / CharacterFilter / SceneFilter
# BatchReviewRequest / BatchReviewResponse / ReviewActionRequest / WorkspaceStats
# AgentOutputRequest / AgentStoryOutput / AgentCharacterOutput / AgentSceneOutput
# ... 详见原始 task_205 文档 §Step 2
```

### Step 3: 创建命名规范检查清单

新建 `backend/types/story-workspace/naming-checklist.md`：

```markdown
# Story Workspace 命名规范检查清单

| 类型 | 前缀 | 示例 |
|------|------|------|
| 路由路径 | `/story-workspace/` | `/story-workspace/stories` |
| 页面组件 | `StoryWorkspace*Page` | `StoryWorkspaceStoriesPage` |
| 布局组件 | `StoryWorkspace*Layout` | `StoryWorkspaceThreeColumnLayout` |
| 业务组件 | `StoryWorkspace*` | `StoryWorkspaceStoryTable` |
| API 路由 | `/api/story-workspace/` | `/api/story-workspace/stories` |
| 数据库表 | `story_workspace_*` | `story_workspace_stories` |
| Python 类型 | `StoryWorkspace*` | `StoryWorkspaceStory` |
| TypeScript 类型 | `StoryWorkspace*` | `StoryWorkspaceStory` |
| Hooks | `useStoryWorkspace*` | `useStoryWorkspaceStore` |
| CSS 类名 | `.story-workspace-*` | `.story-workspace-table-row` |
| 目录 | `story-workspace/` | `pages/story-workspace/` |

## 禁止事项

- ❌ 不使用 `storyWorkspace`（驼峰，应为 PascalCase 类型名）
- ❌ 不使用 `StoryWorkspace` 以外的前缀
- ❌ 不在数据库表名中使用连字符（使用下划线）
- ❌ 不混用单复数（stories 表名，Story 类型名）
```

### Step 4: 定义前端 TypeScript 镜像类型

在 `frontend/src/types/story-workspace/index.ts` 中定义：

```typescript
export enum ReviewStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  REJECTED = 'rejected',
}

export enum ContentStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  ARCHIVED = 'archived',
}

export enum StoryType {
  SHORT = 'short',
  LONG = 'long',
  SCRIPT = 'script',
  OUTLINE = 'outline',
}

export interface StoryWorkspaceStory {
  id: string;
  identifier: string;
  title: string;
  description?: string;
  status: ContentStatus;
  review_status: ReviewStatus;
  type: StoryType;
  content?: string;
  author_id: number;
  workspace_id: string;
  character_count: number;
  scene_count: number;
  agent_generated: boolean;
  agent_session_id?: string;
  review_notes?: string;
  created_at: string;  // ISO 8601
  updated_at: string;
  confirmed_at?: string;
  published_at?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

// ... StoryWorkspaceCharacter, StoryWorkspaceScene, StoryWorkspaceWorkspace,
//     StoryFilter, CharacterFilter, SceneFilter, BatchReviewRequest, etc.
```

### Step 5: 建立前后端字段对照表

| 后端字段 | 后端类型 | 前端字段 | 前端类型 | 说明 |
|----------|----------|----------|----------|------|
| `id` | `str` | `id` | `string` | UUID |
| `identifier` | `str` | `identifier` | `string` | 业务标识 |
| `title` | `str` | `title` | `string` | 故事标题 |
| `review_status` | `ReviewStatus` | `review_status` | `ReviewStatus` | 枚举一致 |
| `status` | `ContentStatus` | `status` | `ContentStatus` | 枚举一致 |
| `type` | `StoryType` | `type` | `StoryType` | 枚举一致 |
| `agent_generated` | `bool` | `agent_generated` | `boolean` | SQLite 用 0/1，API 层转 bool |
| `tags` | `List[str]` | `tags` | `string[]` | 角色性格标签 |
| `created_at` | `Optional[datetime]` | `created_at` | `string` | ISO 8601 字符串 |

### Step 6: 制定同步与变更流程

1. **类型变更**：任何字段增删改由 BackendTaskAgent 先更新 `backend/types/story-workspace/`，再通知 FrontendTaskAgent 同步更新 `frontend/src/types/story-workspace/`。
2. **枚举变更**：`ReviewStatus`、`ContentStatus`、`StoryType` 是前后端共享契约，变更需双方同步。
3. **检查工具**：建议在 CI 中增加命名前缀扫描（可选，本任务不实现，仅记录为建议）。
4. **版本标记**：在类型文件顶部添加 `TYPE_CONTRACT_VERSION` 常量，便于追踪合同版本。

## 5. 涉及文件路径

| 路径 | 说明 |
|------|------|
| `backend/types/story-workspace/__init__.py` | **新文件**：后端 Python 类型规范源 |
| `backend/types/story-workspace/naming-checklist.md` | **新文件**：命名规范检查清单 |
| `frontend/src/types/story-workspace/index.ts` | **前端责任**：TypeScript 类型镜像（FrontendTaskAgent 消费） |
| `backend/routers/story-workspace.py` | 引用上述类型 |
| `backend/services/story-workspace/agent_integration.py` | 引用上述类型 |
| `docs/task/task_205_backend_story-workspace-shared-types.md` | 本任务文档，作为合同记录 |

## 6. 输入 / 输出说明

### 输入

- 设计稿数据表结构：`docs/design/story-workspace/story-workspace-layout-design.md` §5.1–5.5
- 设计稿命名映射：`docs/design/story-workspace/story-workspace-prd.md` §4.2、§14.1
- Issue 清单：`docs/issue/ISSUES_story-workspace.md` §3
- 现有后端技术栈：Python 3.12 + FastAPI + SQLite（项目当前使用 dataclass / Pydantic 混合风格）
- 现有前端技术栈：TypeScript + React

### 输出

- `backend/types/story-workspace/__init__.py`：后端 Python 类型规范模型
- `backend/types/story-workspace/naming-checklist.md`：命名规范检查清单
- `frontend/src/types/story-workspace/index.ts`：前端 TypeScript 镜像类型（FrontendTaskAgent 消费）
- 前后端字段对照表（记录于本任务文档 §Step 5）
- 类型同步流程（记录于本任务文档 §Step 6）

## 7. 依赖项

| 依赖 | Issue ID | 类型 | 说明 |
|------|----------|------|------|
| 无 | — | — | 本任务无前置依赖，可与其他任务并行 |
| `SUO-201-BE-001` | 数据库 Schema | 软依赖 | Schema 字段确定后类型模型更稳定；可基于设计稿先行定义 |
| `SUO-201-BE-002` | REST API | 软依赖 | API 请求/响应类型需与路由参数对齐 |
| `SUO-201-BE-004` | Agent 集成 | 软依赖 | Agent 产出 payload 类型需与共享类型对齐 |
| 现有技术栈 | — | 现有 | Python dataclass / Pydantic、TypeScript |

## 8. 测试策略

### 8.1 后端类型导入测试

```python
def test_types_importable():
    from types.story_workspace import (
        ReviewStatus, ContentStatus, StoryType,
        StoryWorkspaceStory, StoryWorkspaceCharacter, StoryWorkspaceScene,
        PaginatedResponse, StoryFilter, BatchReviewRequest,
        AgentOutputRequest, AgentStoryOutput,
    )
    assert ReviewStatus.PENDING == "pending"
    assert ContentStatus.DRAFT == "draft"
```

### 8.2 后端类型实例化测试

```python
def test_story_type_creation():
    from types.story_workspace import StoryWorkspaceStory, ReviewStatus, ContentStatus, StoryType

    story = StoryWorkspaceStory(
        id="test-id",
        identifier="story-001",
        title="测试故事",
        review_status=ReviewStatus.PENDING,
        status=ContentStatus.DRAFT,
        type=StoryType.SHORT,
        author_id=1,
        workspace_id="ws-1",
    )
    assert story.title == "测试故事"
    assert story.agent_generated is True
```

### 8.3 枚举值一致性测试

```python
def test_enum_values():
    from types.story_workspace import ReviewStatus, ContentStatus, StoryType

    assert ReviewStatus.PENDING.value == "pending"
    assert ReviewStatus.CONFIRMED.value == "confirmed"
    assert ReviewStatus.REJECTED.value == "rejected"

    assert ContentStatus.DRAFT.value == "draft"
    assert ContentStatus.PUBLISHED.value == "published"
    assert ContentStatus.ARCHIVED.value == "archived"

    assert StoryType.SHORT.value == "short"
    assert StoryType.LONG.value == "long"
    assert StoryType.SCRIPT.value == "script"
    assert StoryType.OUTLINE.value == "outline"
```

### 8.4 前后端字段对照校验（人工 / 半自动）

- 检查前端 `StoryWorkspaceStory` 字段名与后端模型一致。
- 检查所有必填字段在前端接口中标记为非可选。
- 检查日期字段前端使用 `string`（ISO 8601），后端使用 `datetime`。

## 9. 完成标志

- [ ] 后端类型定义文件 `backend/types/story-workspace/__init__.py` 创建完成。
- [ ] 命名规范检查清单 `backend/types/story-workspace/naming-checklist.md` 创建完成。
- [ ] 前端 TypeScript 镜像类型文件 `frontend/src/types/story-workspace/index.ts` 创建完成（由 FrontendTaskAgent 消费）。
- [ ] 审阅状态枚举 `ReviewStatus = 'pending' | 'confirmed' | 'rejected'` 定义完成。
- [ ] 内容状态枚举 `ContentStatus = 'draft' | 'published' | 'archived'` 定义完成。
- [ ] 故事类型枚举 `StoryType = 'short' | 'long' | 'script' | 'outline'` 定义完成。
- [ ] API 列表响应类型 `PaginatedResponse<T>` 定义完成。
- [ ] 筛选参数类型 `StoryFilter`、`CharacterFilter`、`SceneFilter` 定义完成。
- [ ] 批量操作类型 `BatchReviewRequest`、`BatchReviewResponse` 定义完成。
- [ ] Agent 产出类型 `AgentOutputRequest`、`AgentStoryOutput`、`AgentCharacterOutput`、`AgentSceneOutput` 定义完成。
- [ ] 前后端字段对照表完整（至少包含 §Step 5 列出的字段）。
- [ ] 命名规范检查清单完整（覆盖路由、组件、API、数据库表、类型、Hooks、CSS 类）。
- [ ] 类型同步流程文档化。
- [ ] 后端类型导入/实例化/枚举测试通过。

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **前后端类型不同步** | 高 | BackendTaskAgent 作为唯一规范主责；建立字段对照表；变更时先改后端再同步前端 |
| **项目无 monorepo shared package** | 中 | 采用后端规范源 + 前端镜像方案；文档化同步机制；未来可迁移到 `shared/types/story-workspace/` |
| **Python dataclass 与 Pydantic 风格差异** | 中 | 后端模型使用 dataclass（与现有部分代码风格一致），FastAPI 路由中可包装为 Pydantic 或直接用 dict 校验 |
| **日期类型前后端不一致** | 低 | 后端使用 `datetime`，API 序列化为 ISO 8601 字符串；前端使用 `string` 接收 |
| **Agent 产出 payload 与共享类型偏差** | 中 | `SUO-201-BE-004` 的 Agent 集成服务引用本任务模型；偏差时在集成层做适配并记录 |
| **命名前缀遗漏** | 中 | 提供命名规范检查清单；建议在 stage 执行前做人工扫描 |

## 11. 下游执行提示

- **StagePlanner 注意**: 本任务是所有前后端工作的前置基础之一，可与 `SUO-201-BE-001`（Schema）并行启动。建议在其后尽快完成，以便 `SUO-201-BE-002`、`SUO-201-BE-004` 和前端任务引用稳定类型。
- **与 FrontendTaskAgent 协作**: FrontendTaskAgent 仅消费本任务产出的类型合同。BackendTaskAgent 需在类型变更时主动通知 FrontendTaskAgent，可通过 Issue 评论或子任务委派。
- **与 BE-004 的关系**: `SUO-201-BE-004` 的 Agent 产出 payload 必须与本任务的 `AgentStoryOutput` 等模型字段对齐；若 Agent 输出字段少于模型，集成服务应提供默认值。
- **合同稳定性**: `ReviewStatus` / `ContentStatus` / `StoryType` 一旦确定，后续 stage 变更成本较高，建议在实现前冻结。
- **迁移路径**: 若未来引入 monorepo shared package，本任务文档应作为迁移依据，将 `backend/types/story-workspace/` 和 `frontend/src/types/story-workspace/` 合并到 `shared/types/story-workspace/`。

## 12. 执行边界

### 允许修改范围
- `backend/types/story-workspace/__init__.py` — **新文件**：Python 类型定义（dataclass / enum）。
- `backend/types/story-workspace/naming-checklist.md` — **新文件**：命名规范检查清单。
- 若项目存在 `shared/types/` monorepo 共享包，优先放置其中；否则按方案 B（前后端各自维护）执行。
- 本任务文档中可包含前端 TypeScript 类型定义的**参考模板**（供 FrontendTaskAgent 参考），但不实际写入前端目录。

### 禁止修改范围
- ❌ `docs/design/`、`docs/issue/`、`docs/stage/`、`docs/exec/` — 任何设计阶段产物。
- ❌ `docs/task/TASK-REQUIREMENT-FORMAT.md` — 提示词模板。
- ❌ `frontend/src/types/story-workspace/` — 前端 TypeScript 类型由 FrontendTaskAgent 负责，本 Agent 仅提供参考模板。
- ❌ 实现代码 — 本任务仅为类型定义与命名规范，不实现业务逻辑。
- ❌ 现有项目类型文件 — 不修改 backend/frontend 中已有的无关类型定义。

### 明确排除项（本期不在范围）
- **复杂画布编辑器** — 类型定义不包含画布/时间线相关数据结构。
- **视频生成模块** — 类型定义不包含视频/镜头相关类型。
- **移动端适配** — 类型定义与设备无关；但本期明确排除移动端/平板端适配需求。
- **用户手动创建内容** — 类型中 `agent_generated` 默认 `true`，不设计用户手动创建内容的专用类型。
- **实时协作** — 无协作会话、光标、锁等类型。
- **四视角转面图** — 角色类型 `avatar_url` 为单字符串，不扩展为多角度对象。
- **历史版本管理** — 无版本快照、diff、回滚相关类型。
- **@提及系统** — 无 Mention、Notification 相关类型。
- **计费/积分系统** — 无积分、配额、计费相关类型。
- **运行时类型校验库** — 本任务定义静态类型（dataclass / TypeScript interface），不引入 `pydantic`、`zod` 等运行时校验库（除非项目已有）。
