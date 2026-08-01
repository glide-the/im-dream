# Story Workspace Issue 清单（SUO-241 增量 — Episodes 元信息渲染与审阅闭环）

> **增量 Issue**: SUO-241  
> **父 Issue**: [SUO-198](/SUO/issues/SUO-198)  
> **设计增量来源**: [SUO-241](/SUO/issues/SUO-241)（DEC-020～DEC-025）  
> **稳定基线**: [SUO-230](/SUO/issues/SUO-230)、`story-workspace-prd.md`、`story-workspace-layout-design.md`  
> **生成 Agent**: IssueDispatcher  
> **最后更新**: 2026-08-01  
> **更新类型**: 增量差异，不重写稳定基线

---

## 0. 文档元信息

- Issue 清单文件：`docs/issue/ISSUES_story-workspace-suo241-delta.md`
- 来源设计稿：
  - 主设计稿：`docs/design/story-workspace/design_003_story-workspace-episodes-metadata-review.md`（DEC-020～DEC-025）
  - 稳定基线设计稿：`docs/design/story-workspace/story-workspace-prd.md`、`docs/design/story-workspace/story-workspace-layout-design.md`
  - Deck 集成 Delta：`docs/design/story-workspace/story-workspace-deck-integration-delta.md`（DEC-009～DEC-019）
  - 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`
- 生成 Agent：`IssueDispatcher`
- 所属流水线阶段：`issue`
- 上游阶段：`design`（SUO-241）
- 下游阶段：`task`
- 下游 Agent：`TaskDesignAgent`
- 共享设计稿来源：`docs/design/story-workspace/`
- 是否作为当前实现合同：是
- 备注：
  - 本文档由 SUO-241 设计增量拆解生成，作为 task 阶段任务规划输入。
  - 本文档为**增量附录**：不重复 SUO-201 / SUO-226 / SUO-230 已稳定基线内容，仅追加 SUO-241 引入的新 Issue。
  - 若与稳定基线冲突，以本文档显式标记的"SUO-241 变化"为准；其余以稳定基线为准。
  - 若与当前 API / 代码实现冲突，必须记录为阻塞或澄清项，不得静默覆盖。

---

## 1. 关联设计稿信息

- 主设计稿：`docs/design/story-workspace/design_003_story-workspace-episodes-metadata-review.md`
- 稳定基线设计稿：`docs/design/story-workspace/story-workspace-prd.md`、`docs/design/story-workspace/story-workspace-layout-design.md`
- Deck 集成 Delta：`docs/design/story-workspace/story-workspace-deck-integration-delta.md`
- 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`

- 本清单覆盖范围：
  - `output/episodes` 元信息到工作空间投影的适配与映射
  - 简单描述入口（PromptComposer）与 Agent 产出的运行追踪
  - `StoryWorkspaceEpisodeProjection` 统一投影数据模型
  - EpisodeListTable 分集列表（产物完整性、镜头/时长、质量、审阅状态）
  - EpisodeDetail 分集详情 Tabs（概览/剧本/分镜/Prompt/审查/执行参考/版本与运行）
  - EpisodeReviewPanel 分集审阅区（artifact 完整性、Agent findings、用户意见、审阅动作）
  - 运行记录与审计最小合同（RunRecord、ArtifactVersion、ReviewEvent、ExecutionGateRecord）
  - 审阅 Gate 与冲突阻断（版本冲突、时长差异、审查不完整、跨文件不一致）
  - 页面状态：empty、submitting、running、validating、metadata-incomplete、artifact-version-conflict、pending-review、rejected、regenerating、confirmed、continuing、completed、failed、stale-review
  - 不可变 attempt/version 与重新生成语义

- 明确排除范围：
  - 复杂画布编辑器（节点拖拽、空间定位、可视化编排）
  - 视频预览、上传、生成、播放器、模型计费
  - 代码、数据库、API、Agent、导入器或 execute 流程的实现
  - Deck 插件内部工作流定义
  - 移动端或平板端适配
  - 用户手动从零创建故事/角色/场景
  - 完整第三方插件运行时

- 关键约束：
  - 所有业务路径、路由、包名、组件/模块/数据标识均采用 `story-workspace` 前缀
  - 本期仅桌面端（≥1280px），不包含任何移动端或平板端适配
  - 三栏骨架保持不变（240px / 自适应 / 360px）
  - 表格替代复杂画布；无视频相关控件
  - 两种输入（已有 episodes 参考产物 / 简单描述触发）必须进入同一 `StoryWorkspaceEpisodeProjection`
  - 源文件状态、Agent 审查、用户审阅、后续执行是四个独立状态维度，不得互相替代
  - Gate 绑定最新活动 run 的明确 required artifact versions 与 aggregate hash
  - 再次生成创建不可变新 attempt/version，旧产物、驳回意见和运行记录永久保留
  - 样本版本、时长、审查范围冲突采取"并列展示并阻断"，不得静默归一
  - 视觉符合 Ink & Memory UI Design v2（暖纸色、少面板、多留白、小面积强调）

- 补充说明：
  - 本批 Issue 拆解基于 SUO-241 设计增量，聚焦 episodes 元信息如何进入工作空间投影及审阅闭环
  - SUO-241 明确"本文不全量改写 SUO-230，也不改变已传播的稳定结论"
  - 下游只需围绕新增项做增量消费
  - 设计文档中的 CLARIFICATION_NEEDED 已单列，采用默认假设时标注风险

---

## 2. Issue 总览表

### 2.1 SUO-241 增量新增 Issue

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `SUO-241-BE-001` | Episodes 元信息适配层与统一投影数据模型 | backend | P0 | `episode`,`projection`,`adapter`,`schema`,`delta` | `SUO-201-BE-001`, `SUO-226-BE-001` | `@TaskDesignAgent` |
| `SUO-241-BE-002` | 运行记录与审计最小合同 API | backend | P0 | `api`,`run-record`,`audit`,`versioning`,`delta` | `SUO-241-BE-001`, `SUO-226-BE-004` | `@TaskDesignAgent` |
| `SUO-241-BE-003` | 审阅 Gate 服务端聚合与冲突阻断校验 | backend | P0 | `api`,`review-gate`,`conflict`,`security`,`delta` | `SUO-241-BE-002`, `SUO-230-BE-001` | `@TaskDesignAgent` |
| `SUO-241-FE-001` | Dream 页面 Episodes 工作空间骨架 | frontend | P0 | `layout`,`episode-workspace`,`dream-page`,`delta` | `SUO-230-FE-002` | `@TaskDesignAgent` |
| `SUO-241-FE-002` | EpisodeListTable 分集列表组件 | frontend | P0 | `table`,`episode-list`,`data-display`,`delta` | `SUO-241-FE-001` | `@TaskDesignAgent` |
| `SUO-241-FE-003` | EpisodeDetail 分集详情 Tabs | frontend | P0 | `tabs`,`episode-detail`,`structured-display`,`delta` | `SUO-241-FE-002` | `@TaskDesignAgent` |
| `SUO-241-FE-004` | EpisodeReviewPanel 分集审阅区 | frontend | P0 | `review`,`panel`,`episode-review`,`delta` | `SUO-241-FE-003`, `SUO-201-FE-004` | `@TaskDesignAgent` |
| `SUO-241-FE-005` | Episodes 页面状态组件集 | frontend | P1 | `state`,`ui`,`episode-states`,`delta` | `SUO-201-FE-006`, `SUO-241-FE-001` | `@TaskDesignAgent` |
| `SUO-241-SH-001` | 统一投影端到端联调（参考产物 + 简单描述 → 渲染 → 审阅） | shared | P0 | `e2e`,`integration`,`episode-projection`,`delta` | `SUO-241-BE-001`, `SUO-241-FE-004` | `@TaskDesignAgent` |
| `SUO-241-SH-002` | 审阅 Gate 冲突阻断与版本过期联调 | shared | P0 | `e2e`,`review-gate`,`conflict`,`security`,`delta` | `SUO-241-BE-003`, `SUO-241-FE-004` | `@TaskDesignAgent` |

---

## 3. Issue 明细

### SUO-241-BE-001

- 标题：Episodes 元信息适配层与统一投影数据模型
- 类型：backend
- 优先级：P0
- 标签：`episode`,`projection`,`adapter`,`schema`,`delta`
- 描述：
  实现 episodes 元信息适配层，将 `output/episodes` 参考产物和用户简单描述触发的 Agent 产出统一映射到 `StoryWorkspaceEpisodeProjection`。适配层负责：文件清单解析、字段映射、完整性校验、版本冲突检测、跨文件一致性校验。统一投影数据模型支撑列表、详情、审阅和运行记录的一致消费。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeProjection` 数据模型定义，字段覆盖：
    - `storyWorkspaceEpisodeKey`, `storyWorkspaceSeriesTitle`, `storyWorkspaceEpisodeNumber`, `storyWorkspaceEpisodeTitle`
    - `storyWorkspaceGenreId`, `storyWorkspaceScriptDurationEstimateSec`
    - `storyWorkspaceCharacterRefs`, `storyWorkspaceSceneRefs`, `storyWorkspaceCharacterBeats`
    - `storyWorkspaceSourceScriptStatus`, `storyWorkspaceSourceScriptVersion`
    - `storyWorkspaceEpisodeSynopsisSections`, `storyWorkspaceScriptScenes`, `storyWorkspaceScriptAnnotations`
    - `storyWorkspaceStoryboardIdentity`, `storyWorkspaceStoryboardShotCount`, `storyWorkspaceStoryboardDurationSec`
    - `storyWorkspaceTargetDurationSec`, `storyWorkspaceSourceStoryboardStatus`, `storyWorkspaceStoryboardGeneratedFrom`
    - `storyWorkspaceShotId`, `storyWorkspaceShotReferences`, `storyWorkspaceShotCamera`, `storyWorkspaceShotContent`
    - `storyWorkspacePromptIdentity`, `storyWorkspacePromptTool`, `storyWorkspacePromptContractSnapshot`
    - `storyWorkspacePromptGeneratedAudit`, `storyWorkspacePromptConsistencyStatus`, `storyWorkspacePromptMetrics`
    - `storyWorkspaceShotPrompt`, `storyWorkspaceShotPromptParams`, `storyWorkspaceShotGenerability`
    - `storyWorkspaceAgentReviewAudit`, `storyWorkspaceAgentReviewVerdict`, `storyWorkspaceAgentReviewFindings`
    - `storyWorkspaceRenderGuideSummary`, `storyWorkspaceRenderQueueReference`
  - [ ] 适配层解析 `script.md`、`storyboard.yaml`、`prompts/*.yml`、`review-report.md`、`render-guide.md`
  - [ ] 完整性校验：检测必审 artifact 缺失（默认 script/storyboard/prompts/review-report）
  - [ ] 版本冲突检测：跨文件 episode、version、generated_from 不一致时标记 `story-workspace-artifact-version-conflict`
  - [ ] 时长差异检测：script/storyboard/prompt/target 时长并列展示，超阈值时标记警告或阻断
  - [ ] 未知 schema 标记 `story-workspace-episodes-schema-unknown`，采用兼容解析并保留原文
  - [ ] 接入时生成 artifact ID 与 content hash；源 version 作为来源字段
  - [ ] 两种输入（参考产物 / 简单描述触发）进入同一投影，不形成两套语义

- 前置依赖：`SUO-201-BE-001`（基线 schema）、`SUO-226-BE-001`（workflow binding/run 模型）

- 关联路径：
  - `backend/src/services/story-workspace/episode-adapter.ts`
  - `backend/src/db/schema/story-workspace/episode-projection.ts`
  - `backend/src/services/story-workspace/episode-parser/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-020`：已有 episodes 和简单描述产物进入同一投影
  - `DEC-024`：冲突并列展示并阻断，不得静默归一
  - 设计稿 §3.1 / §4.2 / §4.3 / §4.4

- 备注：
  - 解析失败时展示原始 Markdown，不丢弃源内容
  - 不得把 Agent review report 当作用户确认
  - `[CLARIFICATION_NEEDED]` `requiredArtifactKinds` 暂按默认清单；最终以锁定的 Deck workflow snapshot 为准

---

### SUO-241-BE-002

- 标题：运行记录与审计最小合同 API
- 类型：backend
- 优先级：P0
- 标签：`api`,`run-record`,`audit`,`versioning`,`delta`
- 描述：
  实现运行记录与审计最小合同的 API。包括：StoryWorkspaceRunRecord（运行记录）、StoryWorkspaceArtifactVersion（artifact 版本）、StoryWorkspaceReviewEvent（审阅事件）、StoryWorkspaceExecutionGateRecord（执行 Gate 记录）。支撑版本历史、审阅审计和不可变 attempt 语义。

- 验收条件：
  - [ ] `StoryWorkspaceRunRecord` 模型与 API：
    - 字段：`storyWorkspaceRunId`、attempt、source kind（`story-workspace-episode-reference` / `story-workspace-prompt-generated`）、input summary、Deck workflow/release/runtime snapshot refs、status、retry/supersede refs、started/finished/failed stage
    - API：`GET /api/story-workspace/runs/:runId`、`GET /api/story-workspace/runs`（按状态、时间筛选）
  - [ ] `StoryWorkspaceArtifactVersion` 模型：
    - 字段：artifact ID/kind/version、source path、source-declared version、content hash、schema version、generated from、ingested/generated at/by、validation status
  - [ ] `StoryWorkspaceReviewEvent` 模型：
    - 字段：review event ID、review unit、run、artifact/version、action（confirm/edit-confirm/reject/regenerate/continue）、reason、finding acknowledgements、actor、timestamp、request ID
  - [ ] `StoryWorkspaceExecutionGateRecord` 模型：
    - 字段：required artifact versions、aggregate hash、gate result/reason、trigger actor/time、idempotency key、downstream execution ID
  - [ ] 历史按时间倒序展示；默认只展开当前 attempt，旧 attempt 可比较但不可修改
  - [ ] 审计日志只显示必要的非敏感来源，Deck secret/config 值不进入页面
  - [ ] 重新生成创建新 run/attempt，`retryOfRunId`/`supersedesVersion` 指向旧事实

- 前置依赖：`SUO-241-BE-001`、`SUO-226-BE-004`（Workflow Run 创建 API）

- 关联路径：
  - `backend/src/routes/story-workspace/runs.ts`
  - `backend/src/services/story-workspace/run-record.service.ts`
  - `backend/src/db/schema/story-workspace/run-record.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-021`：四个独立状态维度
  - `DEC-023`：不可变新 attempt/version，旧产物永久保留
  - 设计稿 §6.3 / §3.2

- 备注：
  - 源文件 `status=draft` 不能映射为用户"已驳回"或"待审阅"
  - 驳回、再次生成、刷新、关闭面板或切换路由均不能删除历史审阅事件

---

### SUO-241-BE-003

- 标题：审阅 Gate 服务端聚合与冲突阻断校验
- 类型：backend
- 优先级：P0
- 标签：`api`,`review-gate`,`conflict`,`security`,`delta`
- 描述：
  实现服务端审阅 Gate 的冲突阻断校验。以 `workflow_run_id` 为维度聚合全部必审 artifact 的审阅状态；检测版本冲突、时长差异、审查不完整、跨文件不一致等阻断条件；任一项阻断时拒绝确认和后续执行请求。

- 验收条件：
  - [ ] 服务端聚合查询：给定 `workflow_run_id`，返回全部关联 artifact 的审阅状态与完整性
  - [ ] Gate 判定逻辑：
    - 必审 artifact 缺失 → 阻断
    - 跨文件 episode/version/generated_from 不一致 → 阻断
    - 时长差异超阈值 → 警告或阻断（按 workflow 规则）
    - Agent review `BLOCK` → 阻断
    - Agent review `CONDITIONAL` 且用户未显式知悉 → 阻断
    - 审查信息不完整（如 EP90 缺少 reviewer 列表）→ 按 workflow 规则判断
    - 活动版本过期（审阅期间出现新 artifact version）→ 阻断，要求重新审阅
  - [ ] 确认 API 必须接收 `workflow_run_id` + `review_version` + `aggregate_hash`
  - [ ] 服务端校验：运行 ID 匹配、审阅版本未过期、aggregate hash 一致才允许确认
  - [ ] 客户端直接请求确认/继续/结束时，服务端以聚合状态拒绝未通过校验的请求
  - [ ] 确认后继续/结束必须幂等：首次合法确认后只发出一次信号
  - [ ] 若内容已确认但后续继续失败，确认事实不回滚；允许幂等重试继续

- 前置依赖：`SUO-241-BE-002`、`SUO-230-BE-001`（审阅 gate 服务端聚合基线）

- 关联路径：
  - `backend/src/routes/story-workspace/review-gate.ts`
  - `backend/src/services/story-workspace/review-gate.service.ts`
  - `backend/src/services/story-workspace/conflict-validator.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-022`：Gate 绑定 required artifact versions 与 aggregate hash
  - `DEC-024`：冲突并列展示并阻断
  - `DEC-018`（基线）：运行级审阅 gate
  - 设计稿 §6.2 / §3.3 / §4.3

- 备注：
  - 这是安全关键 Issue；客户端 UI 锁定不能替代服务端校验
  - 批量确认必须逐项绑定相同 run 的明确 artifact versions
  - 后续执行必须再次校验确认聚合 hash；客户端按钮启用不是授权事实

---

### SUO-241-FE-001

- 标题：Dream 页面 Episodes 工作空间骨架
- 类型：frontend
- 优先级：P0
- 标签：`layout`,`episode-workspace`,`dream-page`,`delta`
- 描述：
  在 Dream 页面中实现 Episodes 工作空间骨架。包含：简单描述入口（PromptComposer）、运行进度展示、分集列表/详情区域、右侧 EpisodeReviewPanel。沿用 240px / 自适应 / 360px 三栏骨架，不新增第二层顶部栏。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeWorkspacePage` 页面实现（或作为 `StoryWorkspaceDreamPage` 的子区域）
  - [ ] 简单描述区：`StoryWorkspacePromptComposer` 组件，输入题材/剧情/修改意图，选择 Deck 运行上下文
  - [ ] 运行进度：展示当前 `storyWorkspaceRunId`、步骤和已到达 artifact kind
  - [ ] 中栏布局：简单描述区 → ReviewGate → 分集列表/详情
  - [ ] 右栏：始终审阅当前选中 episode/artifact version
  - [ ] 关闭右栏不改变 Gate 状态
  - [ ] 路径：`/story-workspace/episodes`（列表）、`/story-workspace/episodes/:storyWorkspaceEpisodeId`（详情）、`/story-workspace/episodes/:storyWorkspaceEpisodeId/review`（审阅深链）
  - [ ] 所有新增路由、组件、状态使用 `story-workspace` 前缀

- 前置依赖：`SUO-230-FE-002`（Dream 页面与 ReviewGate 基线）

- 关联路径：
  - `frontend/src/pages/story-workspace/StoryWorkspaceEpisodeWorkspacePage.tsx`
  - `frontend/src/components/story-workspace/episode/StoryWorkspacePromptComposer.tsx`
  - `frontend/src/router/story-workspace.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-020`：两种输入进入同一投影
  - `DEC-025`：借用 Dreem 一句话入口模式
  - `DEC-017`（基线）：Dream 页面为 canonical 入口
  - 设计稿 §5.1 / §5.2 / §7.1

- 备注：
  - PromptComposer 不是"新建故事"按钮，而是创作意图输入区
  - 未选择 Deck 插件或 Desk 配置不完整时禁止提交

---

### SUO-241-FE-002

- 标题：EpisodeListTable 分集列表组件
- 类型：frontend
- 优先级：P0
- 标签：`table`,`episode-list`,`data-display`,`delta`
- 描述：
  实现分集列表组件 `StoryWorkspaceEpisodeListTable`。列表展示 episodes 的核心元信息：EP/标题、产物完整性、镜头/时长、Agent 质量、来源版本、用户审阅状态、更新时间。支持搜索、状态筛选、问题筛选和版本筛选。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeListTable` 组件实现
  - [ ] 列定义：
    1. `EP / 标题`：episode、title、series
    2. `产物完整性`：script/storyboard/prompts/review/guide 五类紧凑标签
    3. `镜头 / 时长`：实际镜头数，script/storyboard/prompt/target 差异提示
    4. `Agent 质量`：PASS / CONDITIONAL / BLOCK / incomplete
    5. `来源版本`：活动 run、attempt、script source version、artifact version
    6. `用户审阅`：待审阅、已确认、已驳回、过期、冲突
    7. `更新`：最新 artifact 时间或接入时间
  - [ ] 轻量 Toolbar：搜索、状态筛选、问题筛选、版本筛选
  - [ ] 默认只展示摘要行；点击展开详情或导航到详情页
  - [ ] 无"手动新建剧本"按钮
  - [ ] 版本冲突行：红色标记，显示冲突来源
  - [ ] 时长差异行：黄色标记，并列展示多个来源值
  - [ ] 符合 Ink & Memory UI Design v2（暖纸色、高密度但可扫描）

- 前置依赖：`SUO-241-FE-001`

- 关联路径：
  - `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeListTable.tsx`
  - `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeListToolbar.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-024`：冲突并列展示并阻断
  - `DEC-025`：表格替代画布
  - 设计稿 §5.3 / §7.2

- 备注：
  - 列表行 hover 允许轻阴影，平时不堆叠卡片
  - 状态颜色同时有文本、图标和 aria-live 表达

---

### SUO-241-FE-003

- 标题：EpisodeDetail 分集详情 Tabs
- 类型：frontend
- 优先级：P0
- 标签：`tabs`,`episode-detail`,`structured-display`,`delta`
- 描述：
  实现分集详情组件 `StoryWorkspaceEpisodeDetail`，采用结构化 Tab 展示 episode 的全部 artifact 内容。不采用画布，所有内容以表格、键值对、结构化文本呈现。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeDetail` 组件实现，包含以下 Tabs：
    - `概览`：集元信息、角色/场景引用、弧光、完整性、时长对照 — `StoryWorkspaceEpisodeOverview`
    - `剧本`：场景分组、动作/对白、CAM/情绪/伏笔/钩子标签 — `StoryWorkspaceEpisodeScriptDetail`
    - `分镜`：shot 表（ID、场景、角色、摄影、画面、时长、转场）— `StoryWorkspaceEpisodeShotTable`
    - `Prompt`：逐镜正/负提示词、参数、可生成性 — `StoryWorkspaceEpisodePromptTable`
    - `Agent 审查`：总裁决、审查范围、维度、BLOCK/WARN、签字 — `StoryWorkspaceAgentReviewFindings`
    - `执行参考`：render guide 风险、费用估算、工具、队列文本状态 — `StoryWorkspaceRenderGuideReference`
    - `版本与运行`：artifact 关系、run/attempt、输入摘要、审阅与执行事件 — `StoryWorkspaceRunHistory`
  - [ ] 点击镜头行后，右侧 Review Panel 切换到该镜头的结构化详情
  - [ ] 确认动作仍作用于明确显示的审阅单元和 artifact version
  - [ ] 结构化解析失败时回退为原始 Markdown 展示
  - [ ] 未识别 token（如 CAM、@EMOTION）原样展示，不丢数据

- 前置依赖：`SUO-241-FE-002`

- 关联路径：
  - `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeDetail.tsx`
  - `frontend/src/components/story-workspace/episode/tabs/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-025`：表格替代画布
  - 设计稿 §5.4 / §7.2

- 备注：
  - 每个 Tab 内部保持高密度但可扫描
  - 右栏用分节标题和键值对，不套多层面板

---

### SUO-241-FE-004

- 标题：EpisodeReviewPanel 分集审阅区
- 类型：frontend
- 优先级：P0
- 标签：`review`,`panel`,`episode-review`,`delta`
- 描述：
  实现分集审阅区组件 `StoryWorkspaceEpisodeReviewPanel`。右栏固定展示当前 episode 的审阅信息，包括 artifact 完整性、Agent 审查结论、用户意见输入和审阅动作。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeReviewPanel` 组件实现
  - [ ] 展示当前 episode、run、attempt、artifact version 与"是否最新活动版本"
  - [ ] 必审 artifact 完整性及源文件路径/来源版本
  - [ ] Agent 审查结论、BLOCK/WARN、跨文件冲突和已知悉状态
  - [ ] 用户意见输入；驳回时必填，确认时可选
  - [ ] 审阅动作：`确认通过` / `保存并确认`、`驳回/退回修改`、`再次生成`、`进入后续执行`
  - [ ] 最近一次同类操作的 actor、时间、request ID
  - [ ] 全部历史进入版本与运行 Tab
  - [ ] 版本冲突时：并列显示冲突来源，禁用确认
  - [ ] 活动版本过期时：提示"审阅版本已过期"，要求切换最新版本

- 前置依赖：`SUO-241-FE-003`、`SUO-201-FE-004`（审阅面板基线）

- 关联路径：
  - `frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeReviewPanel.tsx`
  - `frontend/src/components/story-workspace/review/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-021`：四个独立状态维度
  - `DEC-022`：Gate 绑定 artifact versions 与 aggregate hash
  - `DEC-024`：冲突并列展示并阻断
  - 设计稿 §5.5 / §6.2

- 备注：
  - "保存"不等于确认；只有"确认通过"或"保存并确认"能确认
  - 确认动作必须带运行 ID 与审阅版本校验

---

### SUO-241-FE-005

- 标题：Episodes 页面状态组件集
- 类型：frontend
- 优先级：P1
- 标签：`state`,`ui`,`episode-states`,`delta`
- 描述：
  实现 Episodes 工作空间特有的页面状态 UI 组件。这些状态是 SUO-241 增量引入的新 UI 状态，需要针对 episodes 场景定制文案和恢复动作。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeEmptyState`：无 episode 投影、无活动 run；简单描述为主焦点
  - [ ] `StoryWorkspaceEpisodeInputSubmittingState`：正在创建 run；提交按钮 Loading
  - [ ] `StoryWorkspaceEpisodeOutputValidatingState`：文件到达但尚未完成解析/一致性校验；标明"不可审阅"
  - [ ] `StoryWorkspaceEpisodeMetadataIncompleteState`：必审文件/字段缺失；完整性条标出缺失项
  - [ ] `StoryWorkspaceEpisodeArtifactVersionConflictState`：跨文件身份、版本、数量或 hash 不一致；并列显示冲突来源
  - [ ] `StoryWorkspaceEpisodeStaleReviewState`：审阅期间出现新 artifact version；旧内容只读并提示过期
  - [ ] `StoryWorkspaceEpisodeRegeneratingState`：驳回/失败后已创建新 attempt；新旧 attempt 并列
  - [ ] 所有状态组件遵循 Ink & Memory 视觉规范
  - [ ] 恢复动作按钮明确：重试（沿用原版本）、再次生成（创建新 run）、切换最新版本

- 前置依赖：`SUO-201-FE-006`（状态组件基线）、`SUO-241-FE-001`

- 关联路径：
  - `frontend/src/components/story-workspace/episode/state/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-023`：不可变新 attempt/version
  - `DEC-024`：冲突并列展示
  - 设计稿 §6.1

- 备注：
  - 页面 UI 状态是基线 canonical run/review 状态的可见投影，不另造第二套后端事实
  - `pending_review` 仍是可审阅的 canonical 状态

---

### SUO-241-SH-001

- 标题：统一投影端到端联调（参考产物 + 简单描述 → 渲染 → 审阅）
- 类型：shared
- 优先级：P0
- 标签：`e2e`,`integration`,`episode-projection`,`delta`
- 描述：
  端到端验证统一投影的完整流程：已有 `output/episodes` 参考产物被索引后落入工作空间；用户简单描述触发 Agent 产出后由同一投影渲染；两种输入进入同一页面骨架、字段映射、版本模型和审阅 Gate。

- 验收条件：
  - [ ] 参考产物导入：EP01/EP90 样本被正确解析并展示在列表中
  - [ ] 简单描述触发：用户输入后创建 run，Agent 产出后进入同一列表
  - [ ] 两种来源的 episode 展示相同字段、相同审阅语义
  - [ ] 列表展示产物完整性、镜头/时长、质量、审阅状态
  - [ ] 详情 Tabs 正确展示概览、剧本、分镜、Prompt、审查、执行参考、版本
  - [ ] 审阅面板展示 artifact 完整性、Agent findings、用户意见
  - [ ] 运行记录展示 run/attempt、输入摘要、审阅与执行事件
  - [ ] 版本冲突（如 EP01 script@v5 vs storyboard@v1）被正确标记并阻断确认
  - [ ] 时长差异被并列展示

- 前置依赖：`SUO-241-BE-001`、`SUO-241-FE-004`

- 关联路径：
  - `frontend/src/components/story-workspace/episode/`
  - `backend/src/services/story-workspace/episode-adapter/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-020`：两种输入进入同一投影
  - `DEC-025`：表格替代画布
  - 设计稿 §3.1 / §8.1

- 备注：
  - 前端职责：页面渲染、列表/详情/审阅 UI、状态展示
  - 后端职责：适配层解析、投影模型、完整性校验、版本冲突检测

---

### SUO-241-SH-002

- 标题：审阅 Gate 冲突阻断与版本过期联调
- 类型：shared
- 优先级：P0
- 标签：`e2e`,`review-gate`,`conflict`,`security`,`delta`
- 描述：
  端到端验证审阅 Gate 的冲突阻断与版本过期能力。覆盖场景：版本冲突阻断、时长差异警告/阻断、Agent BLOCK 阻断、审查不完整阻断、活动版本过期、确认版本校验、幂等继续。

- 验收条件：
  - [ ] 版本冲突阻断：EP01 script@v5 vs storyboard@v1 时确认被禁用
  - [ ] 时长差异：script/storyboard/prompt/target 差异超阈值时显示警告或阻断
  - [ ] Agent BLOCK 阻断：review report 总裁决为 BLOCK 时禁止确认
  - [ ] 审查不完整：缺少 reviewer 列表时按 workflow 规则判断
  - [ ] 活动版本过期：审阅期间 Agent 重新生成后，旧版本确认被服务端拒绝
  - [ ] 确认版本校验：确认请求必须带正确的 run ID + review version + aggregate hash
  - [ ] 幂等继续：全部确认后仅放行一次后续执行
  - [ ] 客户端绕过：直接调用继续 API（跳过 UI）被服务端以聚合状态拒绝

- 前置依赖：`SUO-241-BE-003`、`SUO-241-FE-004`

- 关联路径：
  - `frontend/src/components/story-workspace/episode/`
  - `backend/src/routes/story-workspace/review-gate.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`

- 协作 Agent：无

- 设计决策引用：
  - `DEC-022`：Gate 绑定 artifact versions 与 aggregate hash
  - `DEC-024`：冲突并列展示并阻断
  - `DEC-018`（基线）：运行级审阅 gate
  - 设计稿 §6.2 / §8.1

- 备注：
  - 前端职责：正确传递运行 ID 与审阅版本、展示冲突状态、禁用/启用操作按钮
  - 后端职责：聚合校验、版本校验、冲突检测、幂等控制、防绕过拒绝

---

## 4. 共享任务与依赖说明

### 4.1 SUO-241 增量依赖

- `SUO-241-BE-001`（元信息适配层）依赖 `SUO-201-BE-001`（基线 schema）和 `SUO-226-BE-001`（workflow binding/run 模型）。
- `SUO-241-BE-002`（运行记录 API）依赖 `SUO-241-BE-001` 和 `SUO-226-BE-004`（Run 创建 API）。
- `SUO-241-BE-003`（审阅 Gate 冲突阻断）依赖 `SUO-241-BE-002` 和 `SUO-230-BE-001`（审阅 gate 基线）。
- `SUO-241-FE-001`（Episodes 工作空间骨架）依赖 `SUO-230-FE-002`（Dream 页面基线）。
- `SUO-241-FE-002`（分集列表）依赖 `SUO-241-FE-001`。
- `SUO-241-FE-003`（分集详情 Tabs）依赖 `SUO-241-FE-002`。
- `SUO-241-FE-004`（分集审阅区）依赖 `SUO-241-FE-003` 和 `SUO-201-FE-004`（审阅面板基线）。
- `SUO-241-FE-005`（状态组件集）依赖 `SUO-201-FE-006`（状态组件基线）和 `SUO-241-FE-001`。
- `SUO-241-SH-001`（统一投影 E2E）依赖 `SUO-241-BE-001` 和 `SUO-241-FE-004`。
- `SUO-241-SH-002`（冲突阻断 E2E）依赖 `SUO-241-BE-003` 和 `SUO-241-FE-004`。

### 4.2 与稳定基线的关系

- SUO-241 增量**不修改** SUO-201 / SUO-226 / SUO-230 已稳定基线的 Issue 范围、验收条件或分发去向。
- SUO-241 增量在既有基线之上**追加** episodes 元信息渲染、统一投影、冲突阻断和不可变版本语义。
- 若后续发现某个 Issue 的实现范围超出当前设计稿，必须回到 Issue 评论区记录澄清，不得直接下沉到 task 阶段。
- 若某个 Issue 需要新增设计决策，必须标记 `[CLARIFICATION_NEEDED]`，由 `CEOOrchestrator` 判断是否回退到 `DesignArchitect`。

---

## 5. 分发去向说明

### 5.1 TaskDesignAgent

- **Backend Issue**：
  - `SUO-241-BE-001`：Episodes 元信息适配层与统一投影数据模型
  - `SUO-241-BE-002`：运行记录与审计最小合同 API
  - `SUO-241-BE-003`：审阅 Gate 服务端聚合与冲突阻断校验
- **Frontend Issue**：
  - `SUO-241-FE-001`：Dream 页面 Episodes 工作空间骨架
  - `SUO-241-FE-002`：EpisodeListTable 分集列表组件
  - `SUO-241-FE-003`：EpisodeDetail 分集详情 Tabs
  - `SUO-241-FE-004`：EpisodeReviewPanel 分集审阅区
  - `SUO-241-FE-005`：Episodes 页面状态组件集
- **Shared Issue**：
  - `SUO-241-SH-001`：统一投影端到端联调
  - `SUO-241-SH-002`：审阅 Gate 冲突阻断与版本过期联调
- 负责接口、数据处理、Schema、Migration、服务端逻辑、校验链路、UI、交互、状态管理、前端接口消费、页面结构、E2E 验证。

### 5.2 Shared Issue 处理规则

- `SUO-241-SH-001`（统一投影 E2E）：主责 `TaskDesignAgent`。
- `SUO-241-SH-002`（冲突阻断 E2E）：主责 `TaskDesignAgent`。
- 所有 shared Issue 均有唯一主责 Agent，不允许无主责状态。

---

## 6. 推荐推进顺序

### 6.1 SUO-241 增量推进顺序

```text
Phase J: 后端数据模型（可并行，依赖基线）
├── SUO-241-BE-001  Episodes 元信息适配层与统一投影数据模型
│   └── 依赖：SUO-201-BE-001, SUO-226-BE-001
└── SUO-241-BE-002  运行记录与审计最小合同 API
    └── 依赖：SUO-241-BE-001, SUO-226-BE-004

Phase K: 后端 Gate 冲突阻断（依赖 Phase J）
└── SUO-241-BE-003  审阅 Gate 服务端聚合与冲突阻断校验
    └── 依赖：SUO-241-BE-002, SUO-230-BE-001

Phase L: 前端骨架与列表（依赖基线前端 + Phase J）
├── SUO-241-FE-001  Dream 页面 Episodes 工作空间骨架
│   └── 依赖：SUO-230-FE-002
├── SUO-241-FE-002  EpisodeListTable 分集列表组件
│   └── 依赖：SUO-241-FE-001
└── SUO-241-FE-005  Episodes 页面状态组件集
    └── 依赖：SUO-201-FE-006, SUO-241-FE-001

Phase M: 前端详情与审阅（依赖 Phase L）
├── SUO-241-FE-003  EpisodeDetail 分集详情 Tabs
│   └── 依赖：SUO-241-FE-002
└── SUO-241-FE-004  EpisodeReviewPanel 分集审阅区
    └── 依赖：SUO-241-FE-003, SUO-201-FE-004

Phase N: 端到端联调（依赖 Phase K + Phase M）
├── SUO-241-SH-001  统一投影端到端联调
│   └── 依赖：SUO-241-BE-001, SUO-241-FE-004
└── SUO-241-SH-002  审阅 Gate 冲突阻断与版本过期联调
    └── 依赖：SUO-241-BE-003, SUO-241-FE-004
```

### 6.2 与整体流水线的关系

```text
基线 Phase 1-5（SUO-201） + 增量 Phase A-E（SUO-226） + 增量 Phase G-I（SUO-230）
  ↓
SUO-241 增量 Phase J-N（Episodes 元信息渲染与审阅闭环）
  ↓
Task 阶段 → Stage 阶段 → Exec 阶段
```

### 6.3 关键路径

```text
SUO-201-BE-001 → SUO-226-BE-001 → SUO-241-BE-001 → SUO-241-BE-002 → SUO-241-BE-003 → SUO-241-SH-002
SUO-230-FE-002 → SUO-241-FE-001 → SUO-241-FE-002 → SUO-241-FE-003 → SUO-241-FE-004 → SUO-241-SH-002
```

---

## 7. 对既有 Issue 清单的增量影响

### 7.1 需追加设计决策引用的既有 Issue

| 既有 Issue | 追加引用 | 原因 |
|---|---|---|
| `SUO-201-BE-001` | `DEC-020` | 统一投影需要 episodes 相关表 |
| `SUO-201-BE-004` | `DEC-020` | Agent 产出需关联 episode projection |
| `SUO-226-BE-001` | `DEC-020`, `DEC-023` | Workflow run 需关联 episode artifact version |
| `SUO-226-BE-004` | `DEC-021`, `DEC-023` | Run 状态需区分用户审阅与后续执行 |
| `SUO-230-BE-001` | `DEC-022`, `DEC-024` | 审阅 gate 需增加冲突阻断校验 |
| `SUO-230-FE-002` | `DEC-020`, `DEC-025` | Dream 页面需增加 episodes 工作空间 |
| `SUO-230-SH-001` | `DEC-022`, `DEC-024` | 幂等联调需覆盖冲突阻断场景 |

### 7.2 需新建的 Task 文档（SUO-241）

| 建议 Task ID | 内容 | 负责 Agent |
|---|---|---|
| `task_241_backend_episode-adapter-projection.md` | Episodes 元信息适配层与统一投影 | `@TaskDesignAgent` |
| `task_241_backend_run-record-audit.md` | 运行记录与审计最小合同 API | `@TaskDesignAgent` |
| `task_241_backend_review-gate-conflict.md` | 审阅 Gate 冲突阻断校验 | `@TaskDesignAgent` |
| `task_241_frontend_episode-workspace.md` | Dream 页面 Episodes 工作空间骨架 | `@TaskDesignAgent` |
| `task_241_frontend_episode-list-table.md` | EpisodeListTable 分集列表 | `@TaskDesignAgent` |
| `task_241_frontend_episode-detail-tabs.md` | EpisodeDetail 分集详情 Tabs | `@TaskDesignAgent` |
| `task_241_frontend_episode-review-panel.md` | EpisodeReviewPanel 分集审阅区 | `@TaskDesignAgent` |
| `task_241_frontend_episode-states.md` | Episodes 页面状态组件集 | `@TaskDesignAgent` |
| `task_241_shared_episode-projection-e2e.md` | 统一投影端到端联调 | `@TaskDesignAgent` |
| `task_241_shared_review-gate-conflict-e2e.md` | 审阅 Gate 冲突阻断联调 | `@TaskDesignAgent` |

---

## 8. 阻塞与澄清记录

### 8.1 [CLARIFICATION_NEEDED] `requiredArtifactKinds` 默认清单

- **歧义点**：Gate 必审 artifact 清单是否由 Deck workflow snapshot 提供，或采用固定默认
- **可能解释 A**：由锁定的 Deck workflow snapshot 动态提供
- **可能解释 B**：采用固定默认清单（script/storyboard/prompts/review-report）
- **默认采用解释**：采用固定默认清单，但标记为 assumption；最终以锁定的 Deck workflow snapshot 为准
- **需要确认方**：`@CEOOrchestrator` 路由 Deck owner
- **是否阻塞 task 阶段**：否（可采用默认假设继续）
- **风险**：默认清单可能与未来工作流不同

### 8.2 [CLARIFICATION_NEEDED] 时长差异阈值

- **歧义点**：script/storyboard/prompt/target 时长差异的警告/阻断阈值未定义
- **可能解释 A**：按百分比差异（如 >20% 警告，>50% 阻断）
- **可能解释 B**：按绝对秒数差异
- **默认采用解释**：按百分比差异，具体阈值由 workflow 规则决定
- **需要确认方**：产品 owner
- **是否阻塞 task 阶段**：否（可在 task 阶段细化）
- **风险**：阈值过严导致频繁阻断，过松导致质量问题

### 8.3 [CLARIFICATION_NEEDED] 手工结构化编辑范围

- **歧义点**：用户是否可在审阅时进行结构化编辑，以及编辑范围
- **可能解释 A**：仅允许在基线允许的结构化编辑范围修改
- **可能解释 B**：不允许任何编辑，只能确认或驳回
- **默认采用解释**：仅允许在基线允许的结构化编辑范围修改；任何保存必须生成新 artifact version
- **需要确认方**：产品 owner
- **是否阻塞 task 阶段**：否
- **风险**：编辑范围不明确可能导致版本管理混乱

---

## 9. Issue-First 协作说明

- Issue 是最小调度单元。
- 同一 Issue 任一时刻只允许一个主责 Agent。
- shared Issue 必须有主责 Agent 与协作 Agent。
- 必须通过 Issue 评论区补充上下文、阻塞、回退和评审意见。
- 必须通过 `@mention` 唤醒目标 Agent。
- 不假设 Agent 之间存在隐式共享内存。
- 不允许绕过 Issue 直接下发 task。
- 所有 Agent 间协作以 Issue 线程、Issue 文档和关联产物为准。
- 增量 Issue 必须明确标注对基线的影响：新增 / 变更 / 无影响。
- 基线 Issue（SUO-201-xxx / SUO-226-xxx / SUO-230-xxx）不得反向改写其 exec 结论。
