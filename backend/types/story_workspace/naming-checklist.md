# Story Workspace 命名规范检查清单

本清单适用于 Story Workspace 的设计、实现与审查。后端 Python 合同以同目录 `__init__.py` 为唯一规范源，合同版本由 `TYPE_CONTRACT_VERSION` 标识；前端只能消费并镜像字段、类型、可选性和枚举值。

## 命名映射

| 类型 | 规范 | 示例 | 检查 |
|---|---|---|---|
| 页面路由 | `/story-workspace/` | `/story-workspace/stories` | 路由段使用小写连字符，不使用 `storyWorkspace` |
| 页面组件 | `StoryWorkspace*Page` | `StoryWorkspaceStoriesPage` | PascalCase，以 `Page` 结尾 |
| 布局组件 | `StoryWorkspace*Layout` | `StoryWorkspaceThreeColumnLayout` | PascalCase，以 `Layout` 结尾 |
| 业务组件 | `StoryWorkspace*` | `StoryWorkspaceStoryTable` | 必须保留完整业务前缀 |
| API 路由 | `/api/story-workspace/` | `/api/story-workspace/stories` | 资源集合使用复数 |
| 数据库表 | `story_workspace_*` | `story_workspace_stories` | snake_case，禁止连字符 |
| Python 类型 | `StoryWorkspace*` | `StoryWorkspaceStory` | PascalCase；公共类型由后端规范源导出 |
| TypeScript 类型 | `StoryWorkspace*` | `StoryWorkspaceStory` | 与 Python 合同字段和枚举值一致 |
| Hooks | `useStoryWorkspace*` | `useStoryWorkspaceStore` | camelCase，并以 `use` 开头 |
| CSS 类 | `.story-workspace-*` | `.story-workspace-table-row` | kebab-case，禁止 camelCase |
| 目录 | `story-workspace/` | `pages/story-workspace/` | 业务目录使用小写连字符 |

## 单复数规则

- API 集合、数据库资源表使用复数：`stories`、`characters`、`scenes`。
- 单个模型和资源类型使用单数：`StoryWorkspaceStory`、`story`。
- 关联表按两侧资源复数命名：`story_workspace_story_characters`、`story_workspace_scene_characters`。
- 工作区单例 API 使用 `/workspace`；数据库表使用 `story_workspace_workspaces`。

## 合同同步检查

- [ ] `ReviewStatus` 仅包含 `pending`、`confirmed`、`rejected`。
- [ ] `ContentStatus` 仅包含 `draft`、`published`、`archived`。
- [ ] `StoryType` 仅包含 `short`、`long`、`script`、`outline`。
- [ ] `BatchAction` 仅包含 `confirm`、`reject`、`archive`。
- [ ] `ResourceType` 仅包含 `story`、`character`、`scene`。
- [ ] 前端镜像保持字段名、类型、可选性和默认语义一致；日期通过 API 序列化为 ISO 8601 字符串。
- [ ] 合同变更先更新后端规范源和 `TYPE_CONTRACT_VERSION`，再通知 FrontendTaskAgent 同步镜像。
- [ ] 数据库布尔值若以 SQLite `0/1` 存储，API 边界转换为 `bool`。

## 禁止事项与范围排除

- [ ] 不使用无业务前缀的公共组件或公共业务类型。
- [ ] 不在数据库表名中使用连字符，不在路由或 CSS 类中使用下划线业务前缀。
- [ ] 不新增画布、时间线、镜头、视频或四视角角色类型。
- [ ] 不新增移动端/平板端专用类型。
- [ ] 不新增用户手工创建内容的请求类型；`agent_generated` 默认值保持 `true`。
- [ ] 不新增实时协作会话、光标、锁、Mention、通知、版本历史或计费类型。
