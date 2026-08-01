# TASK-REQUIREMENT-FORMAT

Status: Filled Prompt Template for SUO-245
Updated: 2026-08-01
Scope: Story Workspace Episodes metadata/review delta task-document generation

> [Input]
> - `docs/design/story-workspace/design_003_story-workspace-episodes-metadata-review.md`
> - `docs/issue/ISSUES_story-workspace-suo241-delta.md`
> - `docs/issue/ISSUES_story-workspace.md`（稳定基线，仅用于映射核对）
>
> [Output]
> - 生成 10 份 `docs/task/task_241_<domain>_<slug>.md`
> - 本文件是已填充的 Prompt Template，不是最终任务文档
>
> [Position] `task-requirement-template` in `$PROJECT_ROOT/docs/task/`

## 1. Assignment Snapshot

| Field | Value |
|---|---|
| Paperclip Issue | `SUO-245` |
| Title | `[task][story-workspace][episodes-metadata] 生成可执行任务文档` |
| Domain | `backend`、`frontend`、`shared` 增量任务包 |
| Priority | `medium` |
| Status | `in_progress` |
| Work mode | `standard` |
| Parent | `SUO-243`（issue 阶段增量传播，已完成） |
| Ancestor | `SUO-198`（Story Workspace 主需求） |
| Source design | `design_003_story-workspace-episodes-metadata-review`（DEC-020～DEC-025） |
| Source issue list | `ISSUES_story-workspace-suo241-delta.md`（10 条，全部分配给 TaskDesignAgent） |

## 2. Filled Issue Bundle

| Issue ID | 标题 | Domain | 优先级 | 标签 | 前置依赖 | 设计引用 | 关联路径 |
|---|---|---|---|---|---|---|---|
| `SUO-241-BE-001` | Episodes 元信息适配层与统一投影数据模型 | backend | P0 | `episode`, `projection`, `adapter`, `schema`, `delta` | `SUO-201-BE-001`, `SUO-226-BE-001` | DEC-020, DEC-024；§3.1, §4.2～§4.4 | `backend/src/services/story-workspace/episode-adapter.ts`; `backend/src/db/schema/story-workspace/episode-projection.ts`; `backend/src/services/story-workspace/episode-parser/` |
| `SUO-241-BE-002` | 运行记录与审计最小合同 API | backend | P0 | `api`, `run-record`, `audit`, `versioning`, `delta` | `SUO-241-BE-001`, `SUO-226-BE-004` | DEC-021, DEC-023；§3.2, §6.3 | `backend/src/routes/story-workspace/runs.ts`; `backend/src/services/story-workspace/run-record.service.ts`; `backend/src/db/schema/story-workspace/run-record.ts` |
| `SUO-241-BE-003` | 审阅 Gate 服务端聚合与冲突阻断校验 | backend | P0 | `api`, `review-gate`, `conflict`, `security`, `delta` | `SUO-241-BE-002`, `SUO-230-BE-001` | DEC-022, DEC-024, DEC-018；§3.3, §4.3, §6.2 | `backend/src/routes/story-workspace/review-gate.ts`; `backend/src/services/story-workspace/review-gate.service.ts`; `backend/src/services/story-workspace/conflict-validator.ts` |
| `SUO-241-FE-001` | Dream 页面 Episodes 工作空间骨架 | frontend | P0 | `layout`, `episode-workspace`, `dream-page`, `delta` | `SUO-230-FE-002` | DEC-020, DEC-025, DEC-017；§5.1, §5.2, §7.1 | `frontend/src/pages/story-workspace/StoryWorkspaceEpisodeWorkspacePage.tsx`; `frontend/src/components/story-workspace/episode/StoryWorkspacePromptComposer.tsx`; `frontend/src/router/story-workspace.tsx` |
| `SUO-241-FE-002` | EpisodeListTable 分集列表组件 | frontend | P0 | `table`, `episode-list`, `data-display`, `delta` | `SUO-241-FE-001` | DEC-024, DEC-025；§5.3, §7.2 | `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeListTable.tsx`; `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeListToolbar.tsx` |
| `SUO-241-FE-003` | EpisodeDetail 分集详情 Tabs | frontend | P0 | `tabs`, `episode-detail`, `structured-display`, `delta` | `SUO-241-FE-002` | DEC-025；§5.4, §7.2 | `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeDetail.tsx`; `frontend/src/components/story-workspace/episode/tabs/` |
| `SUO-241-FE-004` | EpisodeReviewPanel 分集审阅区 | frontend | P0 | `review`, `panel`, `episode-review`, `delta` | `SUO-241-FE-003`, `SUO-201-FE-004` | DEC-021, DEC-022, DEC-024；§5.5, §6.2 | `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeReviewPanel.tsx`; `frontend/src/components/story-workspace/review/` |
| `SUO-241-FE-005` | Episodes 页面状态组件集 | frontend | P1 | `state`, `ui`, `episode-states`, `delta` | `SUO-201-FE-006`, `SUO-241-FE-001` | DEC-023, DEC-024；§6.1 | `frontend/src/components/story-workspace/episode/state/` |
| `SUO-241-SH-001` | 统一投影端到端联调（参考产物 + 简单描述 → 渲染 → 审阅） | shared | P0 | `e2e`, `integration`, `episode-projection`, `delta` | `SUO-241-BE-001`, `SUO-241-FE-004` | DEC-020, DEC-025；§3.1, §8.1 | `frontend/src/components/story-workspace/episode/`; `backend/src/services/story-workspace/episode-adapter/` |
| `SUO-241-SH-002` | 审阅 Gate 冲突阻断与版本过期联调 | shared | P0 | `e2e`, `review-gate`, `conflict`, `security`, `delta` | `SUO-241-BE-003`, `SUO-241-FE-004` | DEC-022, DEC-024, DEC-018；§6.2, §8.1 | `frontend/src/components/story-workspace/episode/`; `backend/src/routes/story-workspace/review-gate.ts` |

## 3. Issue Acceptance Inputs

### `SUO-241-BE-001`

- 定义覆盖分集、剧本、分镜、Prompt、Agent 审查、render guide 的 `StoryWorkspaceEpisodeProjection`。
- 解析 `script.md`、`storyboard.yaml`、`prompts/*.yml`、`review-report.md`、`render-guide.md`。
- 校验必审 artifact、跨文件 episode/version/generated_from、时长差异和未知 schema；解析失败保留原文。
- 接入时生成 artifact ID/content hash，保留 source version；参考产物与简单描述产出进入同一投影。

### `SUO-241-BE-002`

- 定义 `StoryWorkspaceRunRecord`、`StoryWorkspaceArtifactVersion`、`StoryWorkspaceReviewEvent`、`StoryWorkspaceExecutionGateRecord`。
- 提供 run 单条/列表查询；历史倒序，当前 attempt 默认展开，旧 attempt 只读可比较。
- 重新生成创建不可变新 run/attempt/version 并写入 retry/supersede 关系；审计不泄露 Deck secret/config。

### `SUO-241-BE-003`

- 以 `workflow_run_id` 聚合必审 artifact 状态，处理缺失、版本/身份冲突、时长差异、Agent BLOCK/CONDITIONAL、审查不完整和过期版本。
- 确认请求必须绑定 `workflow_run_id`、`review_version`、`aggregate_hash`；后续执行再次校验。
- 服务端拒绝客户端绕过；确认与继续幂等，继续失败不得回滚确认事实。

### `SUO-241-FE-001`

- 在 Dream canonical 页面内落地 PromptComposer、运行进度、ReviewGate、列表/详情与 360px 右栏。
- 保持 240px / 自适应 / 360px 桌面三栏；关闭右栏不改变 Gate。
- 提供 episodes 列表、详情、review 深链；未选择 Deck 或配置不完整时禁止提交。

### `SUO-241-FE-002`

- 列展示 EP/标题、产物完整性、镜头/多源时长、Agent 质量、来源版本、用户审阅、更新时间。
- 提供搜索和状态/问题/版本筛选；冲突红色、时长差异黄色且都并列展示来源。
- 不提供手工新建剧本；状态不能只靠颜色表达。

### `SUO-241-FE-003`

- 提供概览、剧本、分镜、Prompt、Agent 审查、执行参考、版本与运行 7 个结构化 Tabs。
- Shot 选择驱动右栏详情，但确认始终绑定明确审阅单元和 artifact version。
- 解析失败回退原始 Markdown；未知 token 原样展示。

### `SUO-241-FE-004`

- 右栏展示 episode/run/attempt/version、活动版本标志、完整性、Agent findings、冲突和已知悉状态。
- 支持确认/保存并确认、驳回、再次生成、进入后续执行；驳回意见必填。
- 冲突或 stale review 禁止确认；动作携带运行 ID、review version、aggregate hash。

### `SUO-241-FE-005`

- 实现 empty、input-submitting、output-validating、metadata-incomplete、artifact-version-conflict、stale-review、regenerating 状态组件。
- 明确重试、再次生成、切换最新版本的语义；UI 只是 canonical run/review 状态投影。

### `SUO-241-SH-001`

- 以 EP01/EP90 验证参考产物接入，以简单描述验证即时生成，两者进入同一投影、页面与审阅语义。
- 覆盖列表、详情、审阅面板、运行历史、版本冲突阻断和多源时长并列展示。

### `SUO-241-SH-002`

- 覆盖版本冲突、时长差异、Agent BLOCK、审查不完整、stale review、确认三元组校验、幂等继续和 API 防绕过。

## 4. Required Outputs

1. `task_241_backend_episode-adapter-projection.md` → `SUO-241-BE-001`
2. `task_241_backend_run-record-audit.md` → `SUO-241-BE-002`
3. `task_241_backend_review-gate-conflict.md` → `SUO-241-BE-003`
4. `task_241_frontend_episode-workspace.md` → `SUO-241-FE-001`
5. `task_241_frontend_episode-list-table.md` → `SUO-241-FE-002`
6. `task_241_frontend_episode-detail-tabs.md` → `SUO-241-FE-003`
7. `task_241_frontend_episode-review-panel.md` → `SUO-241-FE-004`
8. `task_241_frontend_episode-states.md` → `SUO-241-FE-005`
9. `task_241_shared_episode-projection-e2e.md` → `SUO-241-SH-001`
10. `task_241_shared_review-gate-conflict-e2e.md` → `SUO-241-SH-002`

每份输出必须包含且仅以任务规划为目的：

1. 任务标题
2. 关联 Issue
3. 任务目标
4. 实现步骤
5. 涉及文件路径
6. 输入 / 输出说明
7. 依赖项
8. 测试策略
9. 完成标志
10. 风险提示

## 5. Global Generation Constraints

- 只新增或增量更新 `docs/task/` 下的任务文档，不修改 design、issue、stage 或实现代码。
- 所有任务均是 SUO-241 相对稳定基线的增量，不能反向重写 SUO-201、SUO-226、SUO-230 的稳定结论。
- 所有业务路径、路由、包名、组件、状态和数据标识使用 `story-workspace` 前缀。
- 仅桌面端（≥1280px），沿用 240px / 自适应 / 360px 三栏，不包含移动端或平板端。
- 不实现复杂画布、视频预览/上传/生成/播放器、模型计费、Deck 插件内部工作流、第三方插件运行时或用户手工从零创建故事。
- 参考 episodes 与简单描述触发的新产出必须进入唯一 `StoryWorkspaceEpisodeProjection`。
- 源文件状态、Agent 审查、用户审阅、后续执行保持四个独立状态维度。
- Gate 绑定最新活动 run 的明确 required artifact versions 与 aggregate hash；客户端 UI 不能替代服务端授权。
- 再次生成必须创建不可变的新 attempt/version，旧产物、驳回意见、审阅事件与运行记录永久保留。
- 版本、身份、时长和审查范围冲突必须并列展示；阻断条件不得静默归一。
- 结构化解析失败时保留并展示原始内容；不得伪造源 frontmatter 或丢弃未知 token。
- UI 使用 Ink & Memory UI Design v2：暖纸色、少面板、多留白、小面积强调、高密度可扫描、状态不只靠颜色。

## 6. Shared Responsibility Contract

两份 shared 任务都必须显式写出以下边界：

| 边界 | `SUO-241-SH-001` | `SUO-241-SH-002` |
|---|---|---|
| 前端 | 同一页面渲染两种来源；列表/详情/审阅/运行历史一致消费投影 | 传递 run/review/hash；展示冲突/过期；正确锁定动作 |
| 后端 | 解析参考产物与 Agent 产出；统一投影、完整性、冲突和版本封装 | 聚合 Gate、版本/冲突校验、幂等控制、API 防绕过 |
| 联调 | 固定 EP01/EP90 与简单描述场景，核对 I/O、状态和审计 | 注入冲突/过期/BLOCK/不完整/重复继续场景并核对端到端结果 |
| 验收 | 两种来源无字段、状态、版本或审阅语义分叉 | UI 锁定与服务端拒绝同时成立，确认事实和幂等结果可审计 |

## 7. Non-blocking Clarifications to Preserve

以下 3 项不得在任务文档中被删除或擅自定案；使用默认假设继续，均不阻塞 task 阶段：

1. `[CLARIFICATION_NEEDED] requiredArtifactKinds`：默认 `script/storyboard/prompts/review-report`；最终以锁定的 Deck workflow snapshot 为准。
2. `[CLARIFICATION_NEEDED] 时长差异阈值`：默认按百分比差异，具体警告/阻断阈值由 workflow 规则决定。
3. `[CLARIFICATION_NEEDED] 手工结构化编辑范围`：默认仅允许基线批准的结构化字段；任何保存生成新 artifact version，禁止原地修改已确认版本。

## 8. Model Generation Instruction

基于以上已填充 Issue 字段、验收输入、设计决策、约束、依赖和澄清项，生成第 4 节列出的 10 份 Markdown 任务文档。任务必须可由下游实现 Agent 直接执行和验证，但不得包含实现代码或 Stage 排期。生成后执行：

- 10 条 Issue 与 10 份任务一一映射，无遗漏、无重复；
- 文件名符合 `task_<序号>_<domain>_<slug>.md`；
- 每份文档具备 10 个必需章节；
- 依赖、路径、I/O 与增量设计范围一致；
- shared 文档具备前端、后端、联调、验收四类边界；
- 3 个非阻塞澄清项在相关任务中可追踪。
