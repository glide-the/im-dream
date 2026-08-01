# Story Workspace Episodes 元信息渲染与审阅闭环 Issue 清单

> **增量 Issue**: SUO-243
> **父 Issue**: SUO-198
> **设计增量来源**: SUO-241（`design_003_story-workspace-episodes-metadata-review.md`）
> **稳定基线**: SUO-230（`ISSUES_story-workspace.md`）
> **生成 Agent**: IssueDispatcher
> **最后更新**: 2026-08-01
> **更新类型**: 增量差异，不重写稳定基线；仅追加 SUO-243-* 系列 Issue

---

## 0. 文档元信息

- Issue 清单文件：`docs/issue/ISSUES_story-workspace-episodes-metadata.md`
- 来源设计稿：
  - 主设计稿：`docs/design/story-workspace/design_003_story-workspace-episodes-metadata-review.md`
  - 稳定基线设计稿：`docs/design/story-workspace/story-workspace-prd.md`、`docs/design/story-workspace/story-workspace-layout-design.md`
  - 背景设计稿：`docs/CLAUDE.md`（Agent 服务集成说明）
  - 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`
- 生成 Agent：`IssueDispatcher`
- 所属流水线阶段：`issue`
- 上游阶段：`design`（SUO-241）
- 下游阶段：`task`
- 下游 Agent：`TaskDesignAgent`
- 共享设计稿来源：`docs/design/story-workspace/`
- 是否作为当前实现合同：是
- 备注：
  - 本文档由 SUO-241 设计稿拆解生成，作为 task 阶段任务规划输入。
  - 本文档**仅包含 SUO-243 增量 Issue**，不重复基线（SUO-201）或先前增量（SUO-226 / SUO-230）内容。
  - 若与设计稿冲突，以 `docs/design/story-workspace/` 中稳定设计稿为准。
  - 若与当前 API / 代码实现冲突，必须记录为阻塞或澄清项，不得静默覆盖。

---

## 1. 关联设计稿信息

- 主设计稿：`docs/design/story-workspace/design_003_story-workspace-episodes-metadata-review.md`
- 稳定基线设计稿：`docs/design/story-workspace/story-workspace-prd.md`、`docs/design/story-workspace/story-workspace-layout-design.md`
- 关联设计稿：`docs/design/deck/deck-integration-delta.md`
- 背景设计稿：`docs/CLAUDE.md`（claude-agent 服务集成）
- 参考设计稿：`docs/design/story-workspace/调研Dreem_app平台.pdf`

- 本清单覆盖范围：
  - `output/episodes` 元信息到工作空间统一投影的映射与渲染
  - 两种输入路径（参考产物导入 + 简单描述触发 Agent 产出）进入同一 `StoryWorkspaceEpisodeProjection`
  - Dream 页面内 episodes 列表、结构化详情 Tabs、右侧审阅区的增量组件
  - 简单描述入口（`StoryWorkspacePromptComposer`）与运行进度展示
  - 页面状态增量：empty、validating、metadata-incomplete、artifact-version-conflict、stale-review、regenerating
  - 审阅 Gate 增强：artifact 完整性校验、跨文件冲突阻断、Agent 审查发现展示
  - 版本/运行/审计最小合同：attempt、artifact ID/version/hash、aggregate hash、retry/supersede
  - 运行记录与历史审计：不可变 attempt、旧版本只读保留

- 明确排除范围：
  - 节点画布、自由拖拽、空间定位或复杂可视化编排
  - 视频预览、上传、生成、播放器、模型计费或平台视频能力
  - 代码、数据库、API、Agent、导入器或 execute 流程的具体实现
  - Deck 插件内部工作流定义
  - 移动端或平板端设计
  - 用户手动创建/编辑剧本内容（仅审阅确认）
  - 后续执行的具体步骤定义（由 Deck workflow 决定）

- 关键约束：
  - 所有新增业务路径、路由、包名、组件、状态和事件均保留 `story-workspace` 前缀
  - 源文件事实必须保留，不得静默改写；缺失字段由接入封装补齐并标记
  - 页面 UI 状态是后端 canonical 状态的可见投影，不另造第二套事实
  - `pending_review` 仍是 canonical 可审阅状态；不新增第二个 API 枚举
  - Agent `overall_verdict=PASS` 不能代替用户确认
  - 源文件 `status=draft` 不能映射为用户审阅状态
  - 确认后继续/结束必须幂等；客户端按钮启用不是授权事实
  - 再次生成创建不可变新 attempt/version，旧产物永久保留
  - 视觉符合 UI Design v2：暖纸色、轻纸面分区、无卡片、无纯白全屏

- 补充说明：
  - 本批 Issue 拆解基于 SUO-230 稳定基线，仅追加 SUO-241 设计增量引入的新工作项。
  - SUO-230 已覆盖的 Dream 导航、ReviewGate 四步流程、版本锁定、防绕过等保持不变。
  - 本增量聚焦：episodes 元信息投影、页面骨架细化、状态扩展、审计合同。
  - 设计稿 §11 相对 SUO-230 的增量变更说明是本次拆解的准绳。

---

## 2. Issue 总览表

### 2.1 SUO-243 增量 Issue（由 SUO-241 设计增量引入）

| Issue ID | 标题 | 类型 | 优先级 | 标签 | 前置依赖 | 分发去向 |
|---|---|---|---|---|---|---|
| `SUO-243-SH-001` | Episodes 统一投影与字段映射合同定义 | shared | P0 | `contract`,`projection`,`episodes-metadata`,`delta` | `SUO-201-SH-002`, `SUO-230-SH-001` | `@TaskDesignAgent` |
| `SUO-243-BE-001` | Episode 元信息接入与适配层 | backend | P0 | `adapter`,`episodes`,`artifact`,`delta` | `SUO-226-BE-001`, `SUO-243-SH-001` | `@TaskDesignAgent` |
| `SUO-243-BE-002` | Artifact 版本校验与冲突检测 | backend | P0 | `validation`,`artifact-version`,`conflict`,`delta` | `SUO-243-BE-001` | `@TaskDesignAgent` |
| `SUO-243-BE-003` | 审阅事件与执行 Gate 审计记录 | backend | P0 | `audit`,`review-event`,`gate-record`,`delta` | `SUO-230-BE-001`, `SUO-243-BE-002` | `@TaskDesignAgent` |
| `SUO-243-FE-001` | Dream 页面 Episodes 列表与详情骨架 | frontend | P0 | `episodes`,`list`,`detail`,`dream-page`,`delta` | `SUO-230-FE-002`, `SUO-243-SH-001` | `@TaskDesignAgent` |
| `SUO-243-FE-002` | 简单描述入口与运行进度组件 | frontend | P0 | `prompt-composer`,`runtime-progress`,`delta` | `SUO-230-FE-002` | `@TaskDesignAgent` |
| `SUO-243-FE-003` | Episode 结构化详情 Tabs | frontend | P1 | `tabs`,`episode-detail`,`structured-display`,`delta` | `SUO-243-FE-001` | `@TaskDesignAgent` |
| `SUO-243-FE-004` | 页面状态组件（增量状态） | frontend | P1 | `state`,`error-ui`,`episode-status`,`delta` | `SUO-226-FE-003`, `SUO-243-FE-001` | `@TaskDesignAgent` |
| `SUO-243-FE-005` | 审阅面板 Episodes 增强（完整性/冲突/发现） | frontend | P1 | `review-panel`,`artifact-integrity`,`findings`,`delta` | `SUO-226-FE-002`, `SUO-243-FE-001` | `@TaskDesignAgent` |
| `SUO-243-SH-002` | Episodes 端到端闭环 E2E（导入→渲染→审阅→执行） | shared | P0 | `e2e`,`episodes`,`closed-loop`,`delta` | `SUO-243-BE-003`, `SUO-243-FE-005` | `@TaskDesignAgent` |

---

## 3. Issue 明细

### 3.1 SUO-243 增量 Issue 明细

#### SUO-243-SH-001

- 标题：Episodes 统一投影与字段映射合同定义
- 类型：shared
- 优先级：P0
- 标签：`contract`,`projection`,`episodes-metadata`,`delta`
- 描述：
  定义 `StoryWorkspaceEpisodeProjection` 统一投影的数据结构与字段映射合同。该合同覆盖 `output/episodes` 中 script、storyboard、prompts、review-report、render-guide 五类 artifact 到统一投影的完整字段映射，以及两种输入路径（参考产物导入 + 即时 Agent 生成）进入同一投影的适配规则。是前后端实现 episodes 渲染与审阅的共同依据。

- 验收条件：
  - [ ] 定义 `StoryWorkspaceEpisodeProjection` 核心字段：
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
  - [ ] 定义字段映射规则：源字段 → 统一投影字段 → 页面区域/组件 → 对状态或审阅的影响
  - [ ] 定义两种输入路径的适配规则：
    - 参考产物路径：`output/episodes/EP??` → 解析 → 校验 → 版本/运行封装
    - 即时生成路径：`StoryWorkspacePromptComposer` → Agent → 相同合同产出 → 页面渲染
  - [ ] 定义缺失字段默认假设与标记规则（`story-workspace-episodes-schema-unknown`）
  - [ ] 定义 artifact kind 枚举：`story-workspace-episode-script`, `story-workspace-episode-storyboard`, `story-workspace-episode-prompts`, `story-workspace-episode-review-report`, `story-workspace-episode-render-guide`
  - [ ] 定义 `requiredArtifactKinds` 默认清单（script/storyboard/prompts/review-report）及工作流覆盖规则
  - [ ] 定义必审单元与 Gate 聚合规则：哪些 artifact kind 为必审、完整性如何判定
  - [ ] 文档化命名前缀约束：所有新增路由/组件/状态/事件使用 `story-workspace` 前缀

- 前置依赖：`SUO-201-SH-002`（命名规范与类型定义共享包）、`SUO-230-SH-001`（确认幂等联调完成，审阅基础稳定）

- 关联路径：
  - `docs/contracts/story-workspace-episode-projection.md`（新建）
  - `shared/types/story-workspace/episodes/`（新建或扩展）

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（backend domain 主导合同定义）

- 协作 Agent：`TaskDesignAgent`（frontend domain 消费确认）

- 设计决策引用：
  - `DEC-020`：已有 episodes 参考产物和简单描述触发的新产物必须进入同一 `StoryWorkspaceEpisodeProjection`
  - `DEC-024`：对样本版本、时长、审查范围冲突采取"并列展示并阻断"，不得静默归一
  - 设计稿 §3.1 / §4.2 字段映射表 / §5.1 路径与命名合同

- 备注：
  - **[CLARIFICATION_NEEDED]** `requiredArtifactKinds` 暂按默认清单收敛；最终以锁定的 Deck workflow snapshot 为准
  - **[CLARIFICATION_NEEDED]** 样本未提供稳定 manifest、schema version、run/audit ID，接入封装方案需 TaskDesignAgent 在 task 阶段细化
  - 本 Issue 是**所有 SUO-243 下游实现的阻塞前置**；合同冻结前下游使用 mock/最小适配层
  - 不得自行编造源文件格式合同；必须在 Issue 评论区记录待确认项

---

#### SUO-243-BE-001

- 标题：Episode 元信息接入与适配层
- 类型：backend
- 优先级：P0
- 标签：`adapter`,`episodes`,`artifact`,`delta`
- 描述：
  实现 episodes 元信息的接入适配层。负责从两种输入路径（`output/episodes` 参考产物导入、Agent 即时生成产出）解析 artifact bundle，按 `StoryWorkspaceEpisodeProjection` 合同生成统一投影。包括：文件清单解析、字段提取、内容 hash 计算、schema version 识别、缺失字段标记、运行封装创建。

- 验收条件：
  - [ ] 实现 `output/episodes/EP??` 目录解析：识别 script.md、storyboard.yaml、prompts/*.yml、review-report.md、render-guide.md
  - [ ] 实现字段提取与映射：按 SUO-243-SH-001 合同将源字段映射到统一投影字段
  - [ ] 计算 content hash 与 artifact ID：每个文件接入时生成稳定标识
  - [ ] schema version 识别：已声明的按声明处理；未声明的标记 `story-workspace-episodes-schema-unknown`
  - [ ] 缺失字段处理：按设计稿 §4.4 默认假设补齐，并标记"系统补充" vs "源文件事实"
  - [ ] 运行封装创建：导入样本使用 `sourceKind=story-workspace-episode-reference`，即时生成使用 `sourceKind=story-workspace-episode-generated`
  - [ ] 接入结果写入 `story-workspace` 数据表，关联 `workflow_run_id`
  - [ ] 解析失败时保留可读内容，标记解析错误，不丢弃源数据
  - [ ] 半结构化 Markdown 解析失败时回退为原始 Markdown 展示

- 前置依赖：`SUO-226-BE-001`（Workflow Binding 与 Run 数据模型）、`SUO-243-SH-001`（投影合同定义）

- 关联路径：
  - `backend/src/services/story-workspace/episode-adapter.ts`
  - `backend/src/services/story-workspace/episode-parser.ts`
  - `backend/src/services/story-workspace/artifact-indexer.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（backend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-020`：两种输入路径进入同一投影
  - `DEC-023`：再次生成创建不可变新 attempt/version，旧产物永久保留
  - `DEC-024`：冲突并列展示并阻断
  - 设计稿 §3.1 / §4.1 样本产物清单 / §4.4 缺失字段默认假设

- 备注：
  - 接入层不得写回伪造的源 frontmatter；系统补充事实与源事实必须区分标记
  - 样本 EP01/EP90 的已知数据问题（版本冲突、时长差异、审查不完整）必须在接入时保留并标记

---

#### SUO-243-BE-002

- 标题：Artifact 版本校验与冲突检测
- 类型：backend
- 优先级：P0
- 标签：`validation`,`artifact-version`,`conflict`,`delta`
- 描述：
  实现 artifact 版本校验与跨文件冲突检测服务。校验规则包括：跨文件身份一致性（episode/project 归属）、版本一致性（script.version vs storyboard.generated_from）、数量一致性（storyboard.total_shots vs 实际 shots 数量）、时长差异阈值、content hash 比对。冲突时阻断确认与后续执行，并列展示冲突来源。

- 验收条件：
  - [ ] 身份一致性校验：script.episode / storyboard.episode / prompts.meta.episode 必须一致；不一致时标记 `story-workspace-artifact-identity-conflict`
  - [ ] 版本一致性校验：storyboard.generated_from 必须与活动 script.version 匹配；不匹配时标记 `story-workspace-artifact-version-conflict`
  - [ ] 数量一致性校验：storyboard.total_shots 与实际 shots[] 数量必须匹配；不匹配时标记 `story-workspace-shot-count-mismatch`
  - [ ] 时长差异校验：script / storyboard / prompt / target 四个时长来源并列比对；超阈值时标记警告或阻断（按 workflow 规则）
  - [ ] content hash 校验：检测同名文件内容变化；变化时生成新 artifact version
  - [ ] 审查完整性校验：review report 必须覆盖必审文件范围；不覆盖时标记 `story-workspace-review-incomplete`
  - [ ] Agent 裁决校验：`overall_verdict=BLOCK` 时阻断 Gate；`CONDITIONAL` 时要求显式知悉
  - [ ] 一致性状态校验：`consistency_status` 非 `verified` 时 Gate 默认阻断
  - [ ] 校验结果结构：通过 / 警告（可继续但需知悉）/ 阻断（禁止确认）
  - [ ] 校验失败时：保留可读内容，禁止确认和后续执行，展示具体冲突项

- 前置依赖：`SUO-243-BE-001`（Episode 元信息接入与适配层）

- 关联路径：
  - `backend/src/services/story-workspace/artifact-validator.ts`
  - `backend/src/services/story-workspace/conflict-detector.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（backend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-021`：源文件状态、Agent 审查、用户审阅和后续执行是四个独立状态维度
  - `DEC-022`：Gate 绑定最新活动 run 的明确 required artifact versions 与 aggregate hash
  - `DEC-024`：冲突并列展示并阻断，不得静默归一
  - 设计稿 §4.3 样本中已确认的数据问题 / §6.2 审阅动作与 Gate 规则

- 备注：
  - 样本 EP01 的 `script.version: 5` vs `storyboard.generated_from: script@v1` 是必须检测并阻断的典型案例
  - 样本 EP90 的 review report 缺少 reviewer 列表、reviewed_files、维度发现，必须标记"审查信息不完整"
  - 时长差异不选择任一值覆盖其他来源；四个值和来源必须并列展示

---

#### SUO-243-BE-003

- 标题：审阅事件与执行 Gate 审计记录
- 类型：backend
- 优先级：P0
- 标签：`audit`,`review-event`,`gate-record`,`delta`
- 描述：
  实现审阅事件与执行 Gate 的审计记录服务。定义并持久化四类审计对象：`StoryWorkspaceRunRecord`、`StoryWorkspaceArtifactVersion`、`StoryWorkspaceReviewEvent`、`StoryWorkspaceExecutionGateRecord`。保证每次审阅动作（确认、驳回、再次生成、进入后续执行）都有完整的审计追踪，支持历史倒序展示与版本比较。

- 验收条件：
  - [ ] `StoryWorkspaceRunRecord` 必留字段：
    - `storyWorkspaceRunId`, attempt, source kind, input summary
    - Deck workflow/release/runtime snapshot refs
    - status, retry/supersede refs
    - started/finished/failed stage timestamps
  - [ ] `StoryWorkspaceArtifactVersion` 必留字段：
    - artifact ID/kind/version, source path, source-declared version
    - content hash, schema version, generated from
    - ingested/generated at/by, validation status
  - [ ] `StoryWorkspaceReviewEvent` 必留字段：
    - review event ID, review unit, run, artifact/version
    - action (confirm/reject/regenerate/continue), reason
    - finding acknowledgements, actor, timestamp, request ID
  - [ ] `StoryWorkspaceExecutionGateRecord` 必留字段：
    - required artifact versions, aggregate hash
    - gate result/reason, trigger actor/time
    - idempotency key, downstream execution ID
  - [ ] 确认幂等：同一确认聚合 hash 只触发一次后续执行；重复请求返回已确认状态
  - [ ] 驳回后重新生成：创建新 run attempt，`retryOfRunId`/`supersedesVersion` 指向旧事实
  - [ ] 历史按时间倒序展示；默认只展开当前 attempt，旧 attempt 可比较但不可修改
  - [ ] 审计日志只显示必要的非敏感来源；Deck secret/config 值不可进入审计记录
  - [ ] 若内容已确认但后续继续失败，确认事实不回滚；允许幂等重试继续

- 前置依赖：`SUO-230-BE-001`（审阅 gate 服务端聚合与防绕过验证）、`SUO-243-BE-002`（Artifact 版本校验与冲突检测）

- 关联路径：
  - `backend/src/services/story-workspace/review-audit.service.ts`
  - `backend/src/services/story-workspace/gate-record.service.ts`
  - `backend/src/db/schema/story-workspace/audit.ts`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（backend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-021`：四个独立状态维度
  - `DEC-022`：Gate 绑定 aggregate hash
  - `DEC-023`：再次生成创建不可变新 attempt/version
  - 设计稿 §6.3 运行、版本与审计最小合同

- 备注：
  - 这是审计关键 Issue；所有审阅事件必须不可变、不可删除
  - 确认幂等通过数据库唯一约束或分布式锁实现
  - "保存"不等于确认；只有"确认通过"或"保存并确认"能生成确认审计记录

---

#### SUO-243-FE-001

- 标题：Dream 页面 Episodes 列表与详情骨架
- 类型：frontend
- 优先级：P0
- 标签：`episodes`,`list`,`detail`,`dream-page`,`delta`
- 描述：
  在 Dream 页面中实现 episodes 列表与详情骨架。列表展示分集摘要信息（EP/标题、产物完整性、镜头/时长、Agent 质量、来源版本、用户审阅状态、更新时间）。详情采用结构化展示（概览/剧本/分镜/Prompt/Agent 审查/执行参考/版本与运行 Tabs）。右栏审阅区随选中项切换。沿用 240px / 自适应 / 360px 三栏骨架。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeListTable` 组件实现
  - [ ] 列表列：
    - `EP / 标题`：episode、title、series
    - `产物完整性`：script/storyboard/prompts/review/guide 五类紧凑标签
    - `镜头 / 时长`：实际镜头数，script/storyboard/prompt/target 差异提示
    - `Agent 质量`：PASS / CONDITIONAL / BLOCK / incomplete
    - `来源版本`：活动 run、attempt、script source version、artifact version
    - `用户审阅`：待审阅、已确认、已驳回、过期、冲突
    - `更新`：最新 artifact 时间或接入时间
  - [ ] 搜索、状态筛选、问题筛选和版本筛选放在轻量 Toolbar
  - [ ] 无"手动新建剧本"按钮
  - [ ] `StoryWorkspaceEpisodeDetail` 组件实现，包含结构化内容展示
  - [ ] 点击列表行后，右栏 Review Panel 切换到该 episode 的审阅详情
  - [ ] 默认只展示摘要行；复杂内容通过详情 Tab 展开
  - [ ] 列表与详情展示相同 run/artifact version，不出现来源漂移

- 前置依赖：`SUO-230-FE-002`（Dream 页面与 ReviewGate 组件）、`SUO-243-SH-001`（投影合同定义）

- 关联路径：
  - `frontend/src/components/story-workspace/episodes/StoryWorkspaceEpisodeListTable.tsx`
  - `frontend/src/components/story-workspace/episodes/StoryWorkspaceEpisodeDetail.tsx`
  - `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（frontend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-020`：两种输入路径进入同一投影
  - `DEC-025`：借用 Dreem 列表 → 详情模式，但用表格替代黑色画布
  - 设计稿 §5.2 Dream 页面骨架 / §5.3 分集列表 / §5.4 分集详情

- 备注：
  - 列表保持高密度但可扫描；内部列表不堆叠卡片，hover 才允许轻阴影
  - 所有 Loading、状态颜色同时有文本、图标和 `aria-live`/可见 focus 表达

---

#### SUO-243-FE-002

- 标题：简单描述入口与运行进度组件
- 类型：frontend
- 优先级：P0
- 标签：`prompt-composer`,`runtime-progress`,`delta`
- 描述：
  实现 Dream 页面顶部的简单描述入口（`StoryWorkspacePromptComposer`）与运行进度展示组件。用户输入题材、剧情或修改意图后提交，系统创建 `storyWorkspaceRunId` 并进入运行状态。运行中展示步骤进度、已到达的 artifact kind 与非敏感日志。组件位于 Dream 页面中栏顶部、Gate 上方。

- 验收条件：
  - [ ] `StoryWorkspacePromptComposer` 组件实现：
    - 文本输入框：支持多行输入，placeholder "输入你想创作/修改的内容…"
    - "交给 Agent" 提交按钮
    - 显示已选择的 Deck/运行快照上下文
    - 显示最近输入历史（可快速复用）
  - [ ] 提交后创建 `storyWorkspaceRunId`，输入摘要进入运行记录
  - [ ] 运行中状态：`StoryWorkspaceRuntimeProgress` 组件展示：
    - 当前运行步骤（queued → running → output_validating → pending_review）
    - 已到达的 artifact kind（script / storyboard / prompts / review / guide）
    - 非敏感日志摘要（不含 Deck secret 或提示词正文）
    - `workflow_run_id` 可点击复制
  - [ ] 运行失败时展示失败阶段、错误码与重试入口
  - [ ] 运行成功且校验通过后，列表自动刷新显示新 episode
  - [ ] 未选择 Deck 插件时，输入框禁用并提示先选择工作流
  - [ ] 提交动作幂等：同一输入在短时间内不重复创建 run

- 前置依赖：`SUO-230-FE-002`（Dream 页面与 ReviewGate 组件）

- 关联路径：
  - `frontend/src/components/story-workspace/prompt/StoryWorkspacePromptComposer.tsx`
  - `frontend/src/components/story-workspace/prompt/StoryWorkspaceRuntimeProgress.tsx`
  - `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（frontend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-020`：两种输入路径进入同一投影
  - `DEC-025`：借用 Dreem 一句话入口模式
  - 设计稿 §3.2 完整五步闭环 / §5.2 Dream 页面骨架 / §6.1 页面状态表

- 备注：
  - 简单描述入口是 Dream 页面的主焦点；无 episode 时空态引导用户输入
  - 运行进度组件不是日志查看器；只展示非敏感摘要和步骤状态

---

#### SUO-243-FE-003

- 标题：Episode 结构化详情 Tabs
- 类型：frontend
- 优先级：P1
- 标签：`tabs`,`episode-detail`,`structured-display`,`delta`
- 描述：
  实现 Episode 详情区域的结构化 Tabs 组件。包含七个 Tab：概览、剧本、分镜、Prompt、Agent 审查、执行参考、版本与运行。每个 Tab 以结构化表格/键值对展示对应 artifact 的内容，不做画布化。点击镜头行后右栏 Review Panel 切换到该镜头的结构化详情。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeOverview` Tab：集元信息、角色/场景引用、弧光、完整性、时长对照
  - [ ] `StoryWorkspaceEpisodeScriptDetail` Tab：场景分组、动作/对白、CAM/情绪/伏笔/钩子标签
  - [ ] `StoryWorkspaceEpisodeShotTable` Tab：shot 表（ID、场景、角色、摄影、画面、时长、转场）
  - [ ] `StoryWorkspaceEpisodePromptTable` Tab：逐镜正/负提示词、参数、可生成性
  - [ ] `StoryWorkspaceAgentReviewFindings` Tab：总裁决、审查范围、维度、BLOCK/WARN、签字
  - [ ] `StoryWorkspaceRenderGuideReference` Tab：render guide 风险、费用估算、工具、队列文本状态
  - [ ] `StoryWorkspaceRunHistory` Tab：artifact 关系、run/attempt、输入摘要、审阅与执行事件
  - [ ] 每个 Tab 内的结构化内容使用表格/键值对，不套多层面板
  - [ ] 未识别 token（如 CAM/@EMOTION/@SETUP/@HOOK/TRANS）原样展示，不丢数据
  - [ ] 解析不到时回退为原始 Markdown 展示
  - [ ] 点击镜头行后，右栏 Review Panel 切换到该镜头的结构化详情

- 前置依赖：`SUO-243-FE-001`（Dream 页面 Episodes 列表与详情骨架）

- 关联路径：
  - `frontend/src/components/story-workspace/episodes/tabs/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（frontend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-024`：冲突并列展示并阻断
  - `DEC-025`：用轻纸面表格替代黑色画布
  - 设计稿 §5.4 分集详情 / §7.2 Ink & Memory UI Design v2 约束

- 备注：
  - 确认动作仍作用于明确显示的审阅单元和 artifact version，不能因 UI 选中变化误确认其他内容
  - 执行参考 Tab 仅展示文本/结构化参考元信息；不提供视频预览/生成按钮

---

#### SUO-243-FE-004

- 标题：页面状态组件（增量状态）
- 类型：frontend
- 优先级：P1
- 标签：`state`,`error-ui`,`episode-status`,`delta`
- 描述：
  实现 SUO-241 设计增量引入的新页面状态 UI 组件。包括：空态（无 episode）、提交中（创建 run）、生成中（Agent 运行）、校验中（文件到达但未完成解析）、元信息不完整（必审文件/字段缺失）、版本冲突（跨文件身份/版本/数量不一致）、过期审阅（审阅期间出现新 artifact version）。这些组件复用现有空态/错误态视觉规范，但针对 episodes 场景定制文案和恢复动作。

- 验收条件：
  - [ ] `StoryWorkspaceEpisodeEmptyState`：无 episode 投影、无活动 run；引导用户输入简单描述
  - [ ] `StoryWorkspaceInputSubmittingState`：正在创建 run；提交按钮 Loading
  - [ ] `StoryWorkspaceAgentRunningState`：run queued/running；展示步骤和已到达 artifact kind
  - [ ] `StoryWorkspaceOutputValidatingState`：文件到达但尚未完成解析；已完成区块可读，缺失区块骨架；标明"不可审阅"
  - [ ] `StoryWorkspaceMetadataIncompleteState`：必审文件/字段缺失；完整性条标出缺失项；确认禁用
  - [ ] `StoryWorkspaceArtifactVersionConflictState`：跨文件身份/版本/数量不一致；并列显示冲突来源；禁止确认
  - [ ] `StoryWorkspaceStaleReviewState`：审阅期间出现新 artifact version；旧内容只读并提示"审阅版本已过期"
  - [ ] 所有状态组件遵循 Ink & Memory 视觉规范（暖纸色、轻纸面分区）
  - [ ] 恢复动作按钮明确：重试（沿用原版本）、再次生成（创建新 attempt）、切换最新版本
  - [ ] 状态颜色同时有文本、图标和 `aria-live`/可见 focus 表达

- 前置依赖：`SUO-226-FE-003`（配置/执行/失败状态 UI 组件）、`SUO-243-FE-001`（Episodes 列表与详情骨架）

- 关联路径：
  - `frontend/src/components/story-workspace/state/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（frontend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-021`：四个独立状态维度
  - `DEC-024`：冲突并列展示并阻断
  - 设计稿 §6.1 页面状态表 / §7.2 UI Design v2 约束

- 备注：
  - 页面 UI 状态是后端 canonical 状态的可见投影，不另造第二套事实
  - `pending_review` 仍是 canonical 可审阅状态；不新增第二个 API 枚举

---

#### SUO-243-FE-005

- 标题：审阅面板 Episodes 增强（完整性/冲突/发现）
- 类型：frontend
- 优先级：P1
- 标签：`review-panel`,`artifact-integrity`,`findings`,`delta`
- 描述：
  在现有审阅面板（Review Panel）基础上增加 episodes 特有的审阅能力：artifact 完整性展示、跨文件冲突提示、Agent 审查发现（BLOCK/WARN/CONDITIONAL）展示、已知悉状态追踪。右栏固定包含当前 episode、run、attempt、artifact version 与"是否最新活动版本"标记。

- 验收条件：
  - [ ] 必审 artifact 完整性展示：script / storyboard / prompts / review / guide 五类存在状态
  - [ ] 缺失项标出具体缺失的 artifact kind 和字段
  - [ ] 跨文件冲突提示：身份冲突、版本冲突、数量冲突、时长差异；并列展示冲突来源值
  - [ ] Agent 审查发现展示：
    - 总裁决（PASS / CONDITIONAL / BLOCK / incomplete）
    - 审查范围（是否覆盖必审文件）
    - 维度评分与发现（BLOCK 阻断，WARN/CONDITIONAL 要求显式知悉）
    - 签字信息
  - [ ] 已知悉状态：用户对 CONDITIONAL/WARN 的知悉必须显式记录
  - [ ] 用户意见输入：驳回时必填，确认时可选
  - [ ] 动作按钮：`确认通过` / `保存并确认`、`驳回/退回修改`、`再次生成`、`进入后续执行`
  - [ ] 最近一次同类操作的 actor、时间、request ID 展示
  - [ ] "是否最新活动版本"标记：非最新版本时提示"审阅版本已过期"
  - [ ] 关闭面板、刷新、路由切换不改变审阅状态

- 前置依赖：`SUO-226-FE-002`（审阅面板来源溯源与版本信息展示）、`SUO-243-FE-001`（Episodes 列表与详情骨架）

- 关联路径：
  - `frontend/src/components/story-workspace/review/StoryWorkspaceEpisodeReviewPanel.tsx`
  - `frontend/src/components/story-workspace/review/StoryWorkspaceArtifactIntegrity.tsx`
  - `frontend/src/components/story-workspace/review/StoryWorkspaceConflictAlert.tsx`
  - `frontend/src/components/story-workspace/review/StoryWorkspaceAgentFindings.tsx`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（frontend domain）

- 协作 Agent：无

- 设计决策引用：
  - `DEC-021`：Agent 审查与用户审阅分离
  - `DEC-022`：Gate 绑定 aggregate hash
  - `DEC-024`：冲突并列展示并阻断
  - 设计稿 §5.5 右侧审阅区 / §6.2 审阅动作与 Gate 规则

- 备注：
  - Agent `overall_verdict=PASS` 不能代替用户确认；两类状态严格分离
  - 确认动作带运行 ID 与审阅版本校验，防过期确认
  - "保存"不等于确认；只有"确认通过"或"保存并确认"能确认

---

#### SUO-243-SH-002

- 标题：Episodes 端到端闭环 E2E（导入→渲染→审阅→执行）
- 类型：shared
- 优先级：P0
- 标签：`e2e`,`episodes`,`closed-loop`,`delta`
- 描述：
  端到端验证 episodes 完整闭环：参考产物导入或简单描述触发 → Agent 产出 → 适配层解析 → 统一投影 → 页面渲染 → 用户审阅（确认/驳回/再次生成）→ Gate 校验 → 后续执行。覆盖正常流程、解析失败、版本冲突、Agent 失败、驳回后再次生成、过期确认、后续执行失败等异常路径。

- 验收条件：
  - [ ] 正常流程：简单描述 → Agent 产出 → 页面渲染 → 用户确认 → Gate 解锁 → 后续执行
  - [ ] 参考产物导入：`output/episodes/EP01` 导入后正确渲染到同一投影
  - [ ] 两种输入路径的 episode 在同一列表中展示，UI 语义一致
  - [ ] 解析失败路径：保留可读内容，标记解析错误，禁止确认
  - [ ] 版本冲突路径：EP01 式 `script.version: 5` vs `storyboard.generated_from: script@v1` 被检测并阻断
  - [ ] Agent 失败路径：保留 run 与已生成文件清单；"重试当前运行"形成新 attempt
  - [ ] 驳回后再次生成：创建新 run/attempt，旧版本审计保留，新版本重新走完整 Gate
  - [ ] 过期确认拒绝：Agent 重新生成后，对旧版本的确认请求被服务端拒绝
  - [ ] 后续执行失败：确认事实不回滚；允许幂等重试继续
  - [ ] 全部必审项确认后才解锁后续执行；任一项 pending/rejected 时阻断
  - [ ] 客户端绕过验证：直接调用继续 API，服务端以聚合状态拒绝

- 前置依赖：`SUO-243-BE-003`（审阅事件与执行 Gate 审计记录）、`SUO-243-FE-005`（审阅面板 Episodes 增强）

- 关联路径：
  - `frontend/src/components/story-workspace/episodes/`
  - `frontend/src/components/story-workspace/review/`
  - `backend/src/services/story-workspace/`
  - `backend/src/routes/story-workspace/`

- 分发去向：`@TaskDesignAgent`

- 主责 Agent：`TaskDesignAgent`（frontend domain 主导 E2E 场景）

- 协作 Agent：`TaskDesignAgent`（backend domain 配合接口与校验）

- 设计决策引用：
  - `DEC-020`～`DEC-025`
  - 设计稿 §3.2 完整五步闭环 / §8 验收标准

- 备注：
  - 前端职责：正确传递运行 ID 与审阅版本、展示 gate 状态、禁用/启用操作按钮、渲染 episodes 列表与详情
  - 后端职责：适配层解析、版本校验、冲突检测、审计记录、Gate 聚合校验、幂等控制
  - 建议编写自动化 E2E 测试覆盖上述场景
  - 样本 EP01/EP90 可作为 E2E 测试的参考数据

---

## 4. 共享任务与依赖说明

### 4.1 SUO-243 增量依赖关系

- `SUO-243-SH-001`（Episodes 统一投影与字段映射合同定义）是**所有 SUO-243 下游实现的阻塞前置**。在该合同未冻结前，下游实现应使用 mock/最小适配层。
- `SUO-243-SH-001` 依赖 `SUO-201-SH-002`（基础类型定义）和 `SUO-230-SH-001`（审阅基础稳定）。
- `SUO-243-BE-001`（Episode 元信息接入）依赖 `SUO-226-BE-001`（Workflow Binding/Run 数据模型）和 `SUO-243-SH-001`（投影合同）。
- `SUO-243-BE-002`（Artifact 版本校验）依赖 `SUO-243-BE-001`（接入层）。
- `SUO-243-BE-003`（审阅事件与审计记录）依赖 `SUO-230-BE-001`（审阅 gate 服务端聚合）和 `SUO-243-BE-002`（版本校验）。
- `SUO-243-FE-001`（Episodes 列表与详情）依赖 `SUO-230-FE-002`（Dream 页面基线）和 `SUO-243-SH-001`（投影合同）。
- `SUO-243-FE-002`（简单描述入口）依赖 `SUO-230-FE-002`（Dream 页面基线）。
- `SUO-243-FE-003`（结构化详情 Tabs）依赖 `SUO-243-FE-001`（列表与详情骨架）。
- `SUO-243-FE-004`（增量状态组件）依赖 `SUO-226-FE-003`（状态组件基线）和 `SUO-243-FE-001`。
- `SUO-243-FE-005`（审阅面板增强）依赖 `SUO-226-FE-002`（审阅面板基线）和 `SUO-243-FE-001`。
- `SUO-243-SH-002`（端到端 E2E）依赖 `SUO-243-BE-003` 和 `SUO-243-FE-005`。

### 4.2 与基线的关系

- SUO-243 增量**不推翻** SUO-201 基线、SUO-226 增量或 SUO-230 增量。
- SUO-243 在 SUO-230 已建立的 Dream 页面、ReviewGate、版本锁定、防绕过基础上，追加 episodes 特有的元信息投影、列表/详情渲染、状态扩展和审计合同。
- 若后续发现某个 Issue 的实现范围超出当前设计稿，必须回到 Issue 评论区记录澄清，不得直接下沉到 task 阶段。

---

## 5. 分发去向说明

### 5.1 TaskDesignAgent（统一分发）

- 所有 SUO-243 增量 Issue 统一分发给 `@TaskDesignAgent`。
- `TaskDesignAgent` 根据 `type`、标签、关联路径与验收条件分别规划 UI、交互、状态、接口、数据、Schema、脚本、服务端逻辑和跨端联调。
- domain 必须写入 Issue/task 字段；不得再通过拆分 Agent 身份表达前后端边界。

### 5.2 Shared Issue 处理规则

- `SUO-243-SH-001`（投影合同定义）：主责 `TaskDesignAgent`（backend domain 主导），协作 `TaskDesignAgent`（frontend domain 消费确认）。
- `SUO-243-SH-002`（端到端 E2E）：主责 `TaskDesignAgent`（frontend domain 主导 E2E 场景），协作 `TaskDesignAgent`（backend domain 配合）。
- 所有 shared Issue 均有唯一主责 Agent，不允许无主责状态。

---

## 6. 推荐推进顺序

### 6.1 SUO-243 增量推进顺序

```text
Phase 1: 合同定义（阻塞后续所有增量）
└── SUO-243-SH-001  Episodes 统一投影与字段映射合同定义
    ├── 依赖：SUO-201-SH-002（基础类型）, SUO-230-SH-001（审阅基础）
    └── 注意：合同冻结前下游使用 mock/适配层

Phase 2: 后端接入与校验（可并行，依赖 Phase 1）
├── SUO-243-BE-001  Episode 元信息接入与适配层
│   └── 依赖：SUO-226-BE-001（Run 模型）, SUO-243-SH-001
└── SUO-243-BE-002  Artifact 版本校验与冲突检测
    └── 依赖：SUO-243-BE-001

Phase 3: 后端审计记录（依赖 Phase 2）
└── SUO-243-BE-003  审阅事件与执行 Gate 审计记录
    └── 依赖：SUO-230-BE-001（Gate 聚合）, SUO-243-BE-002

Phase 4: 前端骨架与入口（可并行，依赖 SUO-230 基线）
├── SUO-243-FE-001  Dream 页面 Episodes 列表与详情骨架
│   └── 依赖：SUO-230-FE-002（Dream 页面基线）, SUO-243-SH-001
└── SUO-243-FE-002  简单描述入口与运行进度组件
    └── 依赖：SUO-230-FE-002

Phase 5: 前端详情与状态（依赖 Phase 4）
├── SUO-243-FE-003  Episode 结构化详情 Tabs
│   └── 依赖：SUO-243-FE-001
├── SUO-243-FE-004  页面状态组件（增量状态）
│   └── 依赖：SUO-226-FE-003（状态基线）, SUO-243-FE-001
└── SUO-243-FE-005  审阅面板 Episodes 增强
    └── 依赖：SUO-226-FE-002（审阅面板基线）, SUO-243-FE-001

Phase 6: 端到端联调（依赖 Phase 3 + Phase 5）
└── SUO-243-SH-002  Episodes 端到端闭环 E2E
    ├── 依赖：SUO-243-BE-003, SUO-243-FE-005
    └── 注意：需验证正常流程、解析失败、版本冲突、Agent 失败、驳回再生、过期确认、后续执行失败
```

### 6.2 与基线/先前增量的整体关系

```text
基线 Phase 1-5（SUO-201）+ 增量 Phase A-F（SUO-226）+ 增量 Phase G-I（SUO-230）
    │
    └── SUO-243 Phase 1-6（Episodes 元信息渲染与审阅闭环）
        ├── 依赖 SUO-230 的 Dream 页面、ReviewGate、审阅基础
        ├── 依赖 SUO-226 的 Workflow Binding/Run 模型
        └── 依赖 SUO-201 的三栏布局、表格、审阅面板基线
```

---

## 7. 阻塞与澄清记录

### 7.1 [CLARIFICATION_NEEDED] `requiredArtifactKinds` 最终来源

- **歧义点**：Gate 的必审 artifact 清单暂按 script/storyboard/prompts/review-report 默认；但最终应以锁定的 Deck workflow snapshot 的 `requiredArtifactKinds` 为准
- **可能解释 A**：以 Deck workflow snapshot 为准
- **可能解释 B**：以 story-workspace 默认清单为准
- **默认采用解释**：以 Deck workflow snapshot 为准；无 snapshot 时使用默认清单并标记 assumption
- **需要确认方**：`@CEOOrchestrator` 路由产品/Deck owner
- **是否阻塞 task 阶段**：**否**（可采用默认假设继续）
- **风险**：默认清单可能与未来工作流不同，导致 Gate 行为不一致
- **Clarification owner / action**：`@CEOOrchestrator` 确认 `requiredArtifactKinds` 的权威来源

### 7.2 [CLARIFICATION_NEEDED] 样本缺失字段的接入封装方案

- **歧义点**：样本 EP01/EP90 缺少稳定 run_id、artifact ID/hash、schema version、用户审阅事件和后续执行 ID
- **可能解释 A**：由接入层完全生成系统字段，源文件保持不变
- **可能解释 B**：在源文件中追加 frontmatter
- **默认采用解释**：由接入封装生成系统字段，标记"接入审计"，不写回伪造的源 frontmatter
- **需要确认方**：`@CEOOrchestrator` 路由数据 owner
- **是否阻塞 task 阶段**：**否**
- **风险**：源文件与系统字段的对应关系可能丢失
- **Clarification owner / action**：`@CEOOrchestrator` 确认接入封装方案

### 7.3 [CLARIFICATION_NEEDED] 后续执行的具体步骤定义

- **歧义点**：Gate 后的"进入后续执行"具体执行什么步骤不在本设计范围内
- **可能解释 A**：由 Deck workflow 决定后续步骤
- **可能解释 B**：由 story-workspace 定义固定后续步骤
- **默认采用解释**：由 Deck workflow 决定；story-workspace 只输出已确认 run/version 与幂等触发语义
- **需要确认方**：`@CEOOrchestrator` 路由产品 owner
- **是否阻塞 task 阶段**：**否**
- **风险**：Gate 后动作不明确，可能导致用户困惑
- **Clarification owner / action**：`@CEOOrchestrator` 确认后续执行的产品定义

### 7.4 [CLARIFICATION_NEEDED] 手工结构化编辑范围

- **歧义点**：设计稿提到"若未来允许手工结构化编辑"，但当前是否允许以及允许范围未明确
- **可能解释 A**：当前不允许任何手工编辑；仅审阅确认
- **可能解释 B**：当前允许有限编辑（如标题、描述）
- **默认采用解释**：当前不允许手工编辑；任何保存都必须生成新 artifact version；不允许在已确认版本上原地修改
- **需要确认方**：`@CEOOrchestrator` 路由产品 owner
- **是否阻塞 task 阶段**：**否**
- **风险**：若产品要求提前开放编辑，需回退到 design 阶段
- **Clarification owner / action**：`@CEOOrchestrator` 确认当前编辑范围

---

## 8. design → issue → task → stage 影响矩阵

| 设计增量 | Issue 影响 | Task 影响 | Stage 影响 | Exec 影响 |
|---|---|---|---|---|
| DEC-020 统一投影 | 新增 SUO-243-SH-001 | 新增投影合同 task | 新增投影字段校验 wave | 统一投影数据结构 |
| DEC-021 四独立状态维度 | 各 Issue 追加状态约束 | 各 task 追加状态分离约束 | 状态审计验证 | 状态模型实现 |
| DEC-022 Gate 绑定 aggregate hash | 新增 SUO-243-BE-003 | 新增审计记录 task | Gate 审计验证 wave | 审计表实现 |
| DEC-023 不可变 attempt/version | 新增 SUO-243-BE-001/002 | 新增接入/校验 task | 版本历史验证 | 接入层实现 |
| DEC-024 冲突并列阻断 | 新增 SUO-243-BE-002 | 新增冲突检测 task | 冲突场景 E2E | 校验逻辑实现 |
| DEC-025 借 Dreem 模式换轻纸面 | 新增 SUO-243-FE-001/002/003 | 新增列表/详情/Tabs task | 视觉验收 wave | 组件实现 |
| Episodes 元信息 Delta | 新增 10 条增量 Issue | 新增 10+ task | 新增 2-3 waves | 新增实现范围 |

### 8.1 Stage 建议

- 保留现有 `stage_story-workspace.md` 作为基线 Stage
- 保留 `stage_story-workspace-dream-gate.md` 作为 Dream 导航与 Gate 增量 Stage
- **新建 `stage_story-workspace-episodes-metadata.md`** 作为 Episodes 元信息渲染与审阅闭环增量 Stage
- Episodes 增量 Stage 置于 SUO-243-SH-001 合同冻结后、SUO-243-BE-003 和 SUO-243-FE-005 完成后
- **旧 Stage 不能作为 SUO-243 增量的 execute 准入；SUO-243 增量 Stage 必须独立验证：参考产物导入 / 简单描述 → 统一投影 → 列表渲染 → 详情 Tabs → 审阅确认 → Gate 放行/阻断 → 后续执行**

---

## 9. 相对 SUO-230 的增量变更说明

| SUO-230 稳定项 | SUO-241（SUO-243 传播）新增/变化 | 未改变内容 |
|-----------------|----------------------------------|------------|
| 顶部 Dream 与 canonical 路由 | Dream 中栏新增 episodes 列表/详情、简单描述入口、运行历史 | Dream 入口、选中态、兼容重定向 |
| 四步可见 Review Gate | 把"Agent 产出/页面渲染"细化为 artifact bundle、校验和投影；增加版本冲突与不完整态 | 未确认不得继续、服务端防绕过 |
| 三栏与右侧 Review Panel | 右栏新增 artifact 完整性、Agent findings、版本和审计；动作补齐退回/再次生成 | 240px / 自适应 / 360px 骨架 |
| 运行级 `workflow_run_id` | 增加 attempt、artifact ID/version/hash、aggregate hash、retry/supersede 关系 | Deck release/runtime snapshot/lock 来源 |
| 待审阅/驳回/确认/继续/失败 | 增加 empty、validating、metadata incomplete、version conflict、stale review、regenerating | canonical `pending_review` 语义 |
| 表格替代复杂画布 | 明确 Episode/Shot/Prompt/Findings 表与结构化 Tabs | 不实现复杂画布 |
| 排除平台视频 | render-guide 只展示文本/结构化参考元信息 | 无视频预览、上传、生成或模型计费 |
| **两种输入路径** | **新增：参考产物导入与即时 Agent 生成进入同一 `StoryWorkspaceEpisodeProjection`** | — |
| **字段映射合同** | **新增：40+ 字段从 script/storyboard/prompts/review-report/render-guide 到统一投影的映射** | — |
| **审计最小合同** | **新增：RunRecord / ArtifactVersion / ReviewEvent / ExecutionGateRecord 四类审计对象** | — |

---

## 10. Issue-First 协作说明

- Issue 是最小调度单元。
- 同一 Issue 任一时刻只允许一个主责 Agent。
- shared Issue 必须有主责 Agent 与协作 Agent。
- 必须通过 Issue 评论区补充上下文、阻塞、回退和评审意见。
- 必须通过 `@mention` 唤醒目标 Agent。
- 不假设 Agent 之间存在隐式共享内存。
- 不允许绕过 Issue 直接下发 task。
- 所有 Agent 间协作以 Issue 线程、Issue 文档和关联产物为准。
- **增量 Issue 必须明确标注对基线的影响：新增 / 变更 / 无影响。**
- **基线 Issue（SUO-201-xxx / SUO-226-xxx / SUO-230-xxx）不得反向改写其 exec 结论。**
