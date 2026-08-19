<!-- [Input] Story Workspace routes, pages, contracts, and services. -->
<!-- [Output] Current project, story, episode, review, and navigation design. -->
<!-- [Pos] Canonical Story Workspace business design. -->

# Story Workspace

## 业务目标

Story Workspace 是登录后的主外壳，把 Writing、Chat、Dream、Deck、创作资产、订阅和设置放在同一
导航体系中。业务数据按当前用户和工作区隔离。

## 信息架构

| 页面 | 路径 | 当前职责 |
|---|---|---|
| Dream | `/story-workspace/dream` | 新建和重入 Dream Run |
| Writing/Timeline/Analysis | `/story-workspace/writing` 等 | 写作、时间线与分析 |
| Chat | `/story-workspace/chat` | 通用 Thread 对话 |
| Stories/Characters/Scenes | 对应复数路径 | 当前创作数据列表、筛选和状态 |
| Decks | `/story-workspace/decks` | 已可运行用户 Deck 与系统 Deck |
| Execution | `/story-workspace/runs/{run_id}/execution` | 当前 Run 产物工作台 |
| Episode Review | `/story-workspace/episodes/{episode_id}/review` | Episode 阅读、确认和驳回 |
| Settings/Subscription | `/story-workspace/settings/**`、`/subscription` | Work、模型、关于和套餐额度 |

## 当前需求与结果

- Workspace、Story、Character 和 Scene 提供 actor-scoped 列表、详情与更新。
- Story、Character、Scene 支持确认、驳回；Story 还支持归档，批量操作使用同一权限与 revision 校验。
- Episode 页面从已同步 Artifact 投影读取剧本、镜头和辅助产物，不直接把工作区文件当数据库事实。
- Story Index 缺失或漂移时显示可恢复状态；reconcile 是显式写操作，GET 不产生修复副作用。
- 桌面使用侧栏与内容区；窄屏基于同一数据和路由重排，不创建第二套业务流程。
- Settings / Work 内聚 Deck、资源链接和插件，不在主导航复制三个管理入口。
- 页面加载、空、权限不足、冲突和依赖不可用均显示可恢复状态，不以假数据填充。

## 代码所有权

- 路由：`frontend/src/router/storyWorkspacePath.ts`、`frontend/src/router/story-workspace.tsx`
- 页面：`frontend/src/pages/story-workspace/`
- 组件：`frontend/src/components/story-workspace/`
- API：`backend/routers/story_workspace.py`
- 合同与持久化：`backend/story_workspace/`、`backend/services/story_workspace/`
