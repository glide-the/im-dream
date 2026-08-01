# Story Workspace Episodes 元信息渲染与审阅工作空间增量设计

> **Design ID**: `design_003_story-workspace-episodes-metadata-review`  
> **关联 Issue**: [SUO-241](/SUO/issues/SUO-241)  
> **父需求**: [SUO-198](/SUO/issues/SUO-198)  
> **稳定基线**: [SUO-230](/SUO/issues/SUO-230)、[story-workspace-prd.md](./story-workspace-prd.md)、[story-workspace-layout-design.md](./story-workspace-layout-design.md)  
> **样本来源**: `output/episodes/EP01`、`output/episodes/EP90`  
> **调研来源**: [调研Dreem_app平台.pdf](./调研Dreem_app平台.pdf)、`docs/prd/Ink & Memory UI Design v2.pdf`  
> **状态**: design 完成，可供下游只读消费  
> **更新日期**: 2026-08-01

## 0. 增量适用规则

本文是 `story-workspace` 稳定设计的**受控增量附录**，不是平行 PRD。

- [SUO-230](/SUO/issues/SUO-230) 已确认的顶部 Dream 导航、canonical `/story-workspace/dream`、桌面三栏、`StoryWorkspaceReviewGate`、未确认不得继续、表格替代复杂画布、排除平台视频及 UI Design v2 均保持不变。
- 本文只补充 `output/episodes` 元信息如何进入同一工作空间投影，以及“简单描述 → Agent 产出 → 页面渲染 → 用户审阅 → 后续执行”的页面与状态细节。
- 若本文与稳定基线发生冲突，仅本文显式标记为“SUO-241 变化”的 episodes 元信息、运行版本及审阅规则生效；其余内容仍以稳定基线为准。
- 下游 `IssueDispatcher`、`TaskDesignAgent`、`StagePlanner` 只读消费本文；本文不直接拆 Issue、写 Task 或排 Stage。

---

## 1. 背景与目标

### 1.1 背景

现有设计已经回答“从哪里进入 Dream”和“未审阅不能继续”，但没有回答以下问题：

1. Agent 产出的剧本、分镜、提示词、审查报告和渲染指引怎样落入工作空间。
2. 用户只输入一句简单描述时，页面怎样从运行中逐步渲染到可审阅状态。
3. `output/episodes` 中不同文件、版本、状态和质量结论怎样映射到列表、详情、异常提示和审阅 Gate。
4. 驳回、退回修改、再次生成后怎样保留旧版本、运行记录和用户审计。

### 1.2 目标

建立唯一的 `StoryWorkspaceEpisodeProjection`（工作空间分集投影），同时消费：

- **参考内容路径**：已有 Agent 文件产物被索引后落入工作空间；
- **即时生成路径**：用户简单描述触发 Agent，Agent 按相同 episodes 合同产出后由页面渲染。

两条路径必须进入同一页面骨架、同一字段映射、同一版本模型和同一审阅 Gate，避免“导入内容”和“新生成内容”形成两套 UI 语义。

---

## 2. 范围界定

### 2.1 范围内

- `output/episodes` 样本清单、字段含义、完整性与跨文件一致性规则。
- episodes 元信息到列表、详情、状态、版本、运行记录和审阅动作的映射。
- Dream 页面内的简单描述入口、运行进度、分集列表、结构化详情和右侧审阅区。
- 空态、加载态、部分产出态、失败态、过期版本态和元信息冲突态。
- 确认、编辑后确认、驳回/退回修改、再次生成、进入后续执行的 Gate。
- 审计最小合同，以及样本缺失字段的默认假设。
- Dreem PDF 截图的采用/舍弃说明及 Ink & Memory UI Design v2 的视觉约束。

### 2.2 范围外

- 不设计节点画布、自由拖拽、空间定位或复杂可视化编排。
- 不包含视频预览、上传、生成、播放器、模型计费或平台视频能力。
- 不实现代码、数据库、API、Agent、导入器或 execute 流程。
- 不定义 Deck 插件内部工作流；仍复用基线中的 Deck owner、preflight 与运行快照语义。
- 不新增移动端或平板端设计。

---

## 3. 方案摘要

### 3.1 两种输入，一套投影

```text
已有 Agent 产物                              用户简单描述
output/episodes/EP??                         StoryWorkspacePromptComposer
        │                                              │
        └──────────────┐                 ┌─────────────┘
                       ▼                 ▼
              story-workspace episodes 元信息适配层
              清单 → 解析 → 校验 → 版本/运行封装
                               │
                               ▼
                 StoryWorkspaceEpisodeProjection
              分集 / 场景 / 镜头 / Prompt / 审查 / 指引
                               │
              ┌────────────────┼─────────────────┐
              ▼                ▼                 ▼
      EpisodeListTable   EpisodeDetail       ReviewPanel
              └────────────────┼─────────────────┘
                               ▼
                 StoryWorkspaceReviewGate
              确认 / 驳回 / 再次生成 / 后续执行
```

`output/episodes` 是字段样本和参考内容来源，不等于已经具备可直接放行的运行审计。缺失的运行、版本和审阅字段由 `story-workspace` 接入封装补齐；源文件事实必须保留，不得静默改写。

### 3.2 完整五步闭环

| 步骤 | 用户/系统行为 | 页面结果 | Gate 结果 |
|------|---------------|----------|-----------|
| 1. 简单描述 | 用户输入题材、剧情或修改意图；选择既有 Deck 运行上下文 | 建立 `storyWorkspaceRunId`，输入摘要进入运行记录 | 锁定，不可继续 |
| 2. Agent 产出 | Agent 生成 episodes artifact bundle；已有参考产物也从此入口被索引 | 显示运行步骤、已到达的 artifact kind 与非敏感日志 | 锁定，不可审阅不完整版本 |
| 3. 页面渲染 | 适配层校验并生成统一投影；列表和详情增量显示 | 完整版本进入 `story-workspace-pending-review`；部分版本标记“产出校验中/不完整” | 完整且一致后才开放审阅 |
| 4. 用户审阅 | 用户检查剧本、镜头、Prompt、Agent 审查结论；确认、编辑后确认或驳回 | 写入当前 artifact version 的审阅事件和意见 | 全部必审项确认才解锁 |
| 5. 后续执行 | 用户点击“进入后续执行”，系统做最终 Gate 校验并幂等触发 | 显示继续中、完成或失败；保留原确认事实 | 仅最新活动版本可放行一次 |

### 3.3 异常与回退总则

- 解析失败、必需文件缺失、跨文件版本冲突：保留可读内容，但禁止确认和后续执行。
- Agent 失败：保留本次 run 与已生成文件清单；“重试当前运行”形成新 attempt，不覆盖失败记录。
- 用户驳回：当前版本变为只读的 `rejected` 事实；“再次生成”创建新 run/attempt，并带入原始描述与驳回意见。
- 确认提交冲突：若服务端发现页面版本过期，返回最新版本并要求重新审阅，不继承旧确认。
- 后续执行失败：确认记录仍有效；允许对同一已确认版本幂等重试后续执行，不要求用户重复确认，除非产物版本已改变。

---

## 4. `output/episodes` 元信息与 UI 映射

### 4.1 样本产物清单

| Artifact kind | 样本路径 | 可用内容 | 默认审阅用途 |
|---------------|----------|----------|--------------|
| `story-workspace-episode-script` | `EP??/script.md` | 集级元信息、角色/场景引用、人物弧光、场景正文、CAM/情绪/伏笔/钩子 | 分集概览、剧本详情、叙事一致性审阅 |
| `story-workspace-episode-storyboard` | `EP??/storyboard.yaml` | 镜头数/时长/来源版本、镜头、角色、运镜、画面、对白、转场 | 镜头表与结构化详情 |
| `story-workspace-episode-prompts` | `EP??/prompts/*.yml` | 工具/合同快照/生成者、一致性、逐镜 Prompt 参数与可生成性 | Prompt 与生成策略只读审阅 |
| `story-workspace-episode-review-report` | `EP??/review-report.md` | 审查人角色、范围、总裁决、维度得分、阻断/警告、签字 | Agent 审查摘要与问题清单 |
| `story-workspace-episode-render-guide` | `EP??/renders/render-guide.md` | 镜头、风险、费用估算、工具与队列状态 | 仅展示执行参考元信息；不提供视频能力 |

是否为 Gate 必审项不由文件名写死，而由已锁定的 Deck workflow snapshot 提供 `requiredArtifactKinds`。样本预览默认把前四类作为必审内容，`render-guide` 为可选参考；若工作流明确将其列为必审项，则纳入聚合 Gate。

### 4.2 字段映射表

| 源字段/结构 | 字段含义 | 统一投影字段 | 页面区域/组件 | 对状态或审阅的影响 |
|-------------|----------|--------------|---------------|--------------------|
| 目录 `EP01` / `EP90` | 分集目录标识 | `storyWorkspaceEpisodeKey` | 列表首列、面包屑 | 与文件内 episode 不一致时进入冲突态 |
| `script.series` | 剧集名称 | `storyWorkspaceSeriesTitle` | 页面标题、筛选器 | 展示字段；缺失时显示“未命名剧集” |
| `script.episode` | 分集序号 | `storyWorkspaceEpisodeNumber` | 列表排序、详情标题 | 必填；目录/文件不一致时阻断确认 |
| `script.title` | 分集标题 | `storyWorkspaceEpisodeTitle` | 列表与详情 Header | 缺失不阻断解析，但标记必修复 |
| `script.genre` | 题材 ID | `storyWorkspaceGenreId` | 概览标签 | 只读；不得擅自翻译成新枚举 |
| `script.duration_estimate` | 剧本目标/估算时长 | `storyWorkspaceScriptDurationEstimateSec` | 概览指标、时长差异提示 | 与分镜/Prompt 时长并列，不互相覆盖 |
| `script.character_refs[]` | 集级角色引用 | `storyWorkspaceCharacterRefs` | 概览“角色”、引用跳转 | 引用无法解析时警告；按 workflow 规则决定是否阻断 |
| `script.scene_refs[]` | 集级场景引用 | `storyWorkspaceSceneRefs` | 概览“场景”、镜头筛选 | 引用无法解析时警告；不得伪造场景 |
| `script.character_beats[]` | 角色弧光的起点、触发、选择、终点与可见证据 | `storyWorkspaceCharacterBeats` | “叙事/弧光”结构化表 | 可由用户逐项审阅；原文字段完整保留 |
| `script.status` | 源剧本自身状态 | `storyWorkspaceSourceScriptStatus` | 来源标签 | 不等同于用户审阅状态 |
| `script.version` | 源剧本版本 | `storyWorkspaceSourceScriptVersion` | 版本条、运行详情 | 作为跨文件来源校验基准 |
| 剧本正文“集元信息” | 前情、核心冲突、集尾钩子等半结构化内容 | `storyWorkspaceEpisodeSynopsisSections` | 概览与剧本页 | 解析不到时回退为原始 Markdown |
| 剧本场头/动作/对白 | 场景顺序与剧本内容 | `storyWorkspaceScriptScenes` | 场景分组列表、详情 | 内容审阅主体；不做画布化 |
| `CAM` / `@EMOTION` / `@SETUP` / `@HOOK` / `TRANS` | 镜头、情绪、伏笔、钩子与转场标注 | `storyWorkspaceScriptAnnotations` | 行内标签、过滤器、详情抽屉 | 未识别 token 原样展示，不丢数据 |
| `storyboard.episode/project` | 分镜归属 | `storyWorkspaceStoryboardIdentity` | 来源与运行详情 | 与目录/剧本不一致时阻断确认 |
| `storyboard.total_shots` | 分镜镜头数 | `storyWorkspaceStoryboardShotCount` | 列表指标、完整性校验 | 与实际 shots 数量不符时阻断确认 |
| `storyboard.total_duration_sec` | 分镜累计时长 | `storyWorkspaceStoryboardDurationSec` | 时长对照 | 与 Prompt/剧本差异超阈值时显示警告或阻断 |
| `storyboard.target_duration_sec` | 目标时长 | `storyWorkspaceTargetDurationSec` | 进度/偏差 | 与剧本估算并列，冲突时显示来源 |
| `storyboard.status` | 分镜源状态 | `storyWorkspaceSourceStoryboardStatus` | Artifact 完整性条 | 不直接映射为 Gate 状态 |
| `storyboard.generated_from` | 分镜引用的剧本版本 | `storyWorkspaceStoryboardGeneratedFrom` | 版本关系图、冲突提示 | 与活动 script.version 不符时禁止确认 |
| `storyboard.last_updated` | 分镜更新时间 | `storyWorkspaceStoryboardUpdatedAt` | 来源/时间 | 只读审计证据 |
| `shots[].shot_id` | 镜头 ID | `storyWorkspaceShotId` | 镜头表主键、详情标题 | 重复或缺失时阻断确认 |
| `shots[].scene_ref/characters` | 镜头场景、角色及动作 | `storyWorkspaceShotReferences` | 镜头表、引用详情 | 无法解析时警告/阻断按工作流规则 |
| `shots[].shot_type/camera` | 景别、角度、高度、运动、镜头 | `storyWorkspaceShotCamera` | 镜头表“摄影”列、详情 | 结构化只读，不提供画布控件 |
| `shots[].visual/dialogue/timing` | 画面、对白、时长、转场 | `storyWorkspaceShotContent` | 镜头详情与时长列 | 内容审阅主体 |
| `prompts.meta.episode/project` | Prompt 归属 | `storyWorkspacePromptIdentity` | 来源与运行详情 | 与分集身份不符时阻断确认 |
| `prompt_tool/tool_version` | 生成工具及版本 | `storyWorkspacePromptTool` | Prompt 概览 | 只展示元信息，不在本期提供模型选择 |
| `contract_snapshot` | Prompt 生成时的合同快照 | `storyWorkspacePromptContractSnapshot` | 版本条、审计详情 | 缺失时标记不可完整溯源 |
| `generated_at/generated_by` | 生成时间与 Agent 角色 | `storyWorkspacePromptGeneratedAudit` | 运行记录 | 源审计证据，不替代用户审阅审计 |
| `consistency_status` | Agent 一致性检查状态 | `storyWorkspacePromptConsistencyStatus` | 质量标签 | 非 verified 时 Gate 默认阻断 |
| `prompts.meta.total_shots/total_duration/target_duration` | Prompt 聚合指标 | `storyWorkspacePromptMetrics` | 时长对照、完整性条 | 与 storyboard 不一致时显示冲突 |
| `prompts.shots[].positive/negative` | 逐镜正/负提示词 | `storyWorkspaceShotPrompt` | Prompt Tab、镜头详情 | 可审阅，不默认在列表全文展开 |
| `prompts.shots[].params` | 模型、模式、时长、运镜、画幅等 | `storyWorkspaceShotPromptParams` | 键值详情表 | 只读展示；不提供视频生成控件 |
| `prompts.shots[].generability` | 角色锁定、运动可行性、时长预算、备注 | `storyWorkspaceShotGenerability` | 质量列、问题筛选 | 任一阻断值按 workflow 规则阻断 Gate |
| `review-report.review_date/reviewers/reviewed_files` | Agent 审查日期、角色与范围 | `storyWorkspaceAgentReviewAudit` | 审查摘要、来源 | 审查范围不覆盖必审文件时提示不完整 |
| `overall_verdict/review_mode` | Agent 总裁决与模式 | `storyWorkspaceAgentReviewVerdict` | 列表质量列、详情 Header | Agent 裁决不等同于用户确认；BLOCK 时禁止确认 |
| 维度评分/BLOCK/WARN/建议 | 质量发现 | `storyWorkspaceAgentReviewFindings` | 问题表与筛选 | BLOCK 阻断，WARN/CONDITIONAL 要求显式知悉 |
| `render-guide` 概览 | 风险、费用、工具与镜头数 | `storyWorkspaceRenderGuideSummary` | “执行参考”Tab | 仅参考；不得显示视频预览/生成按钮 |
| 渲染队列 `shot_id/duration/risk/priority/tool/status` | 逐镜执行建议 | `storyWorkspaceRenderQueueReference` | 结构化表 | 仅当列入 requiredArtifactKinds 才影响 Gate |

### 4.3 样本中已确认的数据问题

这些问题必须在 UI 中显式展示，不能由适配层悄悄“修正”为一致：

| 样本 | 观察 | 页面处理 |
|------|------|----------|
| EP01 / EP90 | `script.version: 5`，但 `storyboard.generated_from: script@v1` | 标记 `story-workspace-artifact-version-conflict`，禁用确认与后续执行；允许查看两个来源值 |
| EP01 | review report 为 `CONDITIONAL_APPROVAL`，且有时长 WARN | 列表显示“条件通过 · 1 警告”；确认前要求用户显式展开/知悉，不伪装成 PASS |
| EP90 | review report 只有最小总裁决和签字，缺少 reviewer 列表、reviewed_files、维度发现 | 标记“审查信息不完整”；若工作流要求完整审查则阻断 |
| EP90 | script 尾部 35s、storyboard 105.5s、prompt meta 94s、目标 110s | 时长对照同时展示四个值和来源；按 workflow 阈值判断警告/阻断 |
| EP01 | script 尾部计算时长 63s、审查报告提及 CAM 71s、storyboard/prompt 118s、目标 110s | 同上；不选择任一值覆盖其他来源 |
| 两集 | 缺少稳定 `run_id`、artifact ID/hash、schema version、用户审阅事件和后续执行 ID | 由接入封装生成；标记“接入审计”，不写回伪造的源 frontmatter |
| 两集 | `reviewed_files` 指向原始 `stories/...`，不等同于当前 `output/episodes/...` | 展示原路径，并通过 content hash/受控引用判断是否为同一内容；仅路径相似不足以确认 |

### 4.4 缺失字段与默认假设

| 缺失字段 | 默认设计假设 | 风险 |
|----------|--------------|------|
| `storyWorkspaceRunId` / attempt | 每次生成或导入接入创建不可变运行封装；导入样本使用 `sourceKind=story-workspace-episode-reference` | 无稳定 ID 会导致历史和幂等不可追踪 |
| artifact ID / version / content hash | 每个文件接入时计算稳定 artifact ID 与内容 hash；源 version 作为来源字段而非唯一版本 | 仅依赖文件名会把覆盖误认为新版本 |
| schema version | 未声明的样本标记 `story-workspace-episodes-schema-unknown`，采用兼容解析并保留原文 | 字段演化可能导致错误映射 |
| 必审 artifact 清单 | 以锁定 workflow snapshot 的 `requiredArtifactKinds` 为准；无清单时默认 script/storyboard/prompts/review-report | 默认清单可能与未来工作流不同 |
| 用户审阅审计 | 由 story-workspace 独立记录 actor、action、reason、artifact version、run、timestamp、request ID | 不得把 Agent review report 当作用户确认 |
| 后续执行语义 | 继续/结束仍由 Deck workflow 决定；story-workspace 只提交通过 Gate 的 run/version | 本文不定义具体执行步骤 |

---

## 5. 页面信息架构与关键骨架

### 5.1 路径与命名合同

所有业务路径、包名、组件、状态和事件均保留 `story-workspace` 前缀：

| 类型 | 规范命名 |
|------|----------|
| Dream canonical 入口 | `/story-workspace/dream` |
| 分集工作空间 | `/story-workspace/episodes` |
| 分集详情 | `/story-workspace/episodes/:storyWorkspaceEpisodeId` |
| 分集审阅深链 | `/story-workspace/episodes/:storyWorkspaceEpisodeId/review` |
| 运行记录 | `/story-workspace/runs/:storyWorkspaceRunId` |
| 领域包 | `story-workspace-episodes-metadata` |
| 统一投影 | `StoryWorkspaceEpisodeProjection` |
| 页面 | `StoryWorkspaceEpisodeWorkspacePage` |
| 列表 | `StoryWorkspaceEpisodeListTable` |
| 详情 | `StoryWorkspaceEpisodeDetail` |
| 审阅区 | `StoryWorkspaceEpisodeReviewPanel` |
| 运行记录 | `StoryWorkspaceRunHistory` |
| UI 状态 | `story-workspace-*`，例如 `story-workspace-output-validating` |
| 领域事件 | `story-workspace.episode.output-indexed`、`story-workspace.episode.review-confirmed` |

`/story-workspace/stories` 仍可保留基线中的故事聚合语义；本增量的 episode 路径表达具体 episodes artifact bundle，不将二者静默合并成同一 ID。

### 5.2 Dream 页面骨架

```text
┌─ AppHeader：Dream（保持 SUO-230 选中态）─────────────────────────────────────┐
├──────────────┬────────────────────────────────────────────┬─────────────────┤
│ StoryWorkspace│ Dream / 分集工作空间                       │ Episode Review  │
│ Sidebar       │                                            │ Panel           │
│               │ 简单描述                                   │                 │
│ 概览          │ [输入你想创作/修改的内容…………] [交给 Agent] │ 当前：EP01 v5   │
│ 分集工作空间  │ [Deck/运行快照] [最近输入]                  │ 来源与完整性     │
│ 角色          │                                            │ Agent 审查发现   │
│ 场景          │ StoryWorkspaceReviewGate                   │ 用户审阅意见     │
│ 运行记录      │ 产出中 → 校验 → 待审阅 → 已确认 → 后续执行 │                 │
│               │                                            │ [驳回/退回修改]  │
│               │ 分集列表 / 分集详情                        │ [再次生成]       │
│               │ EP | 标题 | 产物 | 镜头/时长 | 质量 | 状态 │ [保存并确认]     │
│               │ ────────────────────────────────────────── │ [进入后续执行]   │
└──────────────┴────────────────────────────────────────────┴─────────────────┘
```

骨架沿用 240px / 自适应 / 360px 三栏。简单描述区、Gate、列表/详情位于中栏；右栏始终审阅当前选中 episode/artifact version。关闭右栏不改变 Gate。

### 5.3 分集列表

列表列定义：

1. `EP / 标题`：episode、title、series。
2. `产物完整性`：script / storyboard / prompts / review / guide 五类紧凑标签。
3. `镜头 / 时长`：实际镜头数，以及 script / storyboard / prompt / target 的差异提示。
4. `Agent 质量`：PASS / CONDITIONAL / BLOCK / incomplete。
5. `来源版本`：活动 run、attempt、script source version、artifact version。
6. `用户审阅`：待审阅、已确认、已驳回、过期、冲突。
7. `更新`：最新 artifact 时间或接入时间。

默认只展示摘要行；搜索、状态筛选、问题筛选和版本筛选放在轻量 Toolbar。无“手动新建剧本”按钮。

### 5.4 分集详情

详情采用结构化 Tab，不采用画布：

| Tab | 内容 | 主要组件 |
|-----|------|----------|
| 概览 | 集元信息、角色/场景引用、弧光、完整性、时长对照 | `StoryWorkspaceEpisodeOverview` |
| 剧本 | 场景分组、动作/对白、CAM/情绪/伏笔/钩子标签 | `StoryWorkspaceEpisodeScriptDetail` |
| 分镜 | shot 表：ID、场景、角色、摄影、画面、时长、转场 | `StoryWorkspaceEpisodeShotTable` |
| Prompt | 逐镜正/负提示词、参数、可生成性 | `StoryWorkspaceEpisodePromptTable` |
| Agent 审查 | 总裁决、审查范围、维度、BLOCK/WARN、签字 | `StoryWorkspaceAgentReviewFindings` |
| 执行参考 | render guide 风险、费用估算、工具、队列文本状态 | `StoryWorkspaceRenderGuideReference` |
| 版本与运行 | artifact 关系、run/attempt、输入摘要、审阅与执行事件 | `StoryWorkspaceRunHistory` |

点击镜头行后，右侧 Review Panel 切换到该镜头的结构化详情，但确认动作仍作用于明确显示的审阅单元和 artifact version，不能因 UI 选中变化误确认其他内容。

### 5.5 右侧审阅区

右栏固定包含：

- 当前 episode、run、attempt、artifact version 与“是否最新活动版本”。
- 必审 artifact 完整性及源文件路径/来源版本。
- Agent 审查结论、BLOCK/WARN、跨文件冲突和已知悉状态。
- 用户意见输入；驳回时必填，确认时可选。
- `确认通过` / `保存并确认`、`驳回/退回修改`、`再次生成`、`进入后续执行`。
- 最近一次同类操作的 actor、时间、request ID；全部历史进入版本与运行 Tab。

---

## 6. 交互状态与审阅 Gate

### 6.1 页面状态表

| UI 状态 | 进入条件 | 页面表现 | 可用动作 |
|---------|----------|----------|----------|
| `story-workspace-empty` | 无 episode 投影、无活动 run | 简单描述为主焦点；列表空态说明 Agent 将生成哪些产物 | 提交简单描述 |
| `story-workspace-input-submitting` | 正在创建 run | 提交按钮 Loading，输入和 Deck 上下文暂时只读 | 取消尚未接受的请求（若支持） |
| `story-workspace-agent-running` | run queued/running | Gate 高亮“Agent 产出”；展示步骤和已到达 artifact kind | 查看运行记录 |
| `story-workspace-output-validating` | 文件到达但尚未完成解析/一致性校验 | 已完成区块可读；缺失区块骨架；醒目标明“不可审阅” | 查看来源、等待或失败后重试 |
| `story-workspace-metadata-incomplete` | 必审文件/字段缺失 | 完整性条标出缺失项；确认禁用 | 退回 Agent、再次生成 |
| `story-workspace-artifact-version-conflict` | 跨文件身份、版本、数量或 hash 不一致 | 并列显示冲突来源；不得自动选一 | 退回 Agent、再次生成 |
| `story-workspace-pending-review` | 最新活动版本完整、一致且可审阅 | Gate 高亮“用户审阅”；右栏操作可用 | 确认、编辑后确认、驳回、再次生成 |
| `story-workspace-review-submitting` | 正在提交确认/驳回 | 按钮 Loading，防重复；保留当前内容 | 等待结果 |
| `story-workspace-rejected` | 最新活动版本被驳回 | 红色语义状态、意见与退回对象可见；旧版本只读 | 再次生成 |
| `story-workspace-regenerating` | 驳回/失败后已创建新 attempt | 新旧 attempt 并列；新版本生成中，旧版本审计保留 | 查看历史 |
| `story-workspace-confirmed` | 最新活动版本的全部必审单元已确认 | Gate 解锁第四步；确认信息只读 | 进入后续执行 |
| `story-workspace-continuing` | 后续执行已幂等触发 | 显示执行 run/步骤；审阅事实不可编辑 | 查看运行 |
| `story-workspace-completed` | 后续执行完成或 workflow 在确认处结束 | 完成摘要、来源、审计 | 查看历史 |
| `story-workspace-failed` | 输入、Agent、解析、审阅或后续执行任一步失败 | 非敏感错误码、失败阶段、是否保留确认事实 | 按失败阶段重试/再次生成 |
| `story-workspace-stale-review` | 审阅期间出现新 artifact version | 旧内容只读并提示“审阅版本已过期” | 切换最新版本重新审阅 |

页面 UI 状态是基线 canonical run/review 状态的可见投影，不另造第二套后端事实。`pending_review` 仍是可审阅的 canonical 状态。

### 6.2 审阅动作与 Gate 规则

| 动作 | 前置条件 | 状态变化 | 审计要求 | 后续执行影响 |
|------|----------|----------|----------|--------------|
| 确认通过 | 最新活动 artifact version；必审项完整且无 BLOCK/版本冲突；用户已知悉 CONDITIONAL/WARN | 当前审阅单元 `pending → confirmed` | actor、run、artifact/version、finding acknowledgement、request ID、时间 | 全部必审单元确认后才解锁 |
| 编辑后确认 | 用户仅在基线允许的结构化编辑范围修改；保存产生新 artifact version | 新版本先 `pending`，同一原子请求校验成功后 `confirmed` | 记录 diff 摘要、原/新版本、actor | 只对新版本生效；旧确认不继承 |
| 驳回/退回修改 | `pending_review` 或确认请求尚未成功；必须填写原因并选择退回范围 | 当前版本 `pending → rejected` | 原因、退回 artifact/shot、actor、run/version、时间 | Gate 保持锁定 |
| 再次生成 | `pending_review`、`rejected`、`failed` 或冲突态；若未驳回则需确认放弃当前待审版本 | 创建新 run attempt/version，`retryOfRunId`/`supersedesVersion` 指向旧事实 | 原始描述、补充意见、触发人、旧/新 ID | 新版本重新走完整 Gate；旧版本不可覆盖 |
| 进入后续执行 | 最新活动版本全部必审项 confirmed；Deck snapshot/runtime lock 仍有效；未发生新版本 | `confirmed → continuing → completed/failed` | 幂等键、确认聚合 hash、后续执行 ID、actor、时间 | 同一确认聚合只触发一次；失败可幂等重试 |

不可绕过规则：

1. Agent `overall_verdict=PASS` 不能代替用户确认。
2. 源文件 `status=draft` 不能被 UI 误映射为用户“已驳回”或“待审阅”；二者是不同维度。
3. 任一 required artifact 缺失、身份/版本冲突、Agent BLOCK 或活动版本过期时，服务端与页面都禁止确认。
4. 批量确认必须逐项绑定相同 run 的明确 artifact versions；不能用“当前列表所有项”作为不稳定目标。
5. 驳回、再次生成、刷新、关闭面板或切换路由均不能删除历史审阅事件。
6. 后续执行必须再次校验确认聚合 hash；客户端按钮启用不是授权事实。

### 6.3 运行、版本与审计最小合同

| 对象 | 必留字段 |
|------|----------|
| `StoryWorkspaceRunRecord` | `storyWorkspaceRunId`、attempt、source kind、input summary、Deck workflow/release/runtime snapshot refs、status、retry/supersede refs、started/finished/failed stage |
| `StoryWorkspaceArtifactVersion` | artifact ID/kind/version、source path、source-declared version、content hash、schema version、generated from、ingested/generated at/by、validation status |
| `StoryWorkspaceReviewEvent` | review event ID、review unit、run、artifact/version、action、reason、finding acknowledgements、actor、timestamp、request ID |
| `StoryWorkspaceExecutionGateRecord` | required artifact versions、aggregate hash、gate result/reason、trigger actor/time、idempotency key、downstream execution ID |

历史按时间倒序展示；默认只展开当前 attempt，旧 attempt 可比较但不可修改。审计日志只显示必要的非敏感来源，Deck secret/config 值仍不可进入页面。

---

## 7. 调研截图取舍与 UI Design v2 适配

### 7.1 Dreem 截图取舍

| 截图证据 | 采用 | 舍弃/改造 | 落点 |
|----------|------|-----------|------|
| PDF 第 2 页：一句话输入后生成创作方案，左右分区与常驻 Agent | 采用“简单描述位于工作台顶部”“Agent 运行状态常驻” | 不复制密集表单和独立深色工作区 | Prompt Composer + 中栏 Gate + 右栏 Review Panel |
| PDF 第 3 页：最终方案预览、Script Review、底部创建动作 | 采用“先完整预览再由用户拍板” | 单个“Create”改为确认/驳回/再次生成/后续执行四类受控动作，禁止绕过 Gate | 分集详情 + 审阅动作 |
| PDF 第 4 页：Assets/Outline 双层信息、breadcrumb、角色/地点/脚本入口 | 采用资产引用、层级定位、脚本深链 | 不把人物/地点素材做可编辑图库；本期只读引用 | 概览 Tab、角色/场景 ref、面包屑 |
| PDF 第 6 页：左侧故事线列表、叙事点分组、点击镜头看详情 | 采用“列表定位 → 结构化详情”的主从交互 | 黑色节点画布改为数据表；不实现节点拖拽 | EpisodeListTable + ShotTable + Detail |
| PDF 第 7 页：协作窗口确认、历史版本入口 | 采用右侧审阅面板与显式历史记录 | 视频预览、上传、生成、播放器与历史镜头画面全部排除 | Review Panel + Run History（文本/元信息） |
| PDF 第 8 页：镜头决策控件与外部模型选择 | 只保留已有 params/generability 的只读结构化展示 | 不提供交互控件摆放、外部模型选择或积分计费 | Prompt Tab / 执行参考 Tab |

### 7.2 Ink & Memory UI Design v2 约束

- 页面背景使用 `--color-bg-app` Warm Canvas，内容面使用 `--color-bg-paper`；不使用纯白全屏和 Dreem 黑色画布。
- 主文字使用 `--color-text-primary` / `--color-text-body`，说明和时间使用 `--color-text-secondary` / `--color-text-muted`。
- 主操作使用 `--color-action-primary`；Memory Yellow 只用于待审阅短下划线、竖条或小标签，不铺满大区块。
- confirmed 使用既有正向语义 token；错误/驳回使用现有错误语义 token，禁止新增孤立十六进制色。
- 以留白、字号、行分隔线组织信息；页面级最多一条 Border Paper 虚线边界。内部列表不堆叠卡片，hover 才允许轻阴影。
- 分集列表、Shot 表和问题表保持高密度但可扫描；右栏用分节标题和键值对，不套多层面板。
- 所有 Loading、状态颜色同时有文本、图标和 `aria-live`/可见 focus 表达，不能只靠颜色。

---

## 8. 验收标准

### 8.1 闭环与异常

- [ ] 从简单描述到后续执行的五步在同一页面和运行记录中可追踪。
- [ ] 参考 episodes 导入与即时 Agent 生成进入同一个 `StoryWorkspaceEpisodeProjection`。
- [ ] 解析失败、缺失、跨文件冲突、Agent 失败、驳回、再次生成、过期确认和后续执行失败均有恢复路径。

### 8.2 元信息与页面

- [ ] script、storyboard、prompts、review-report、render-guide 的可用字段均有 UI 映射。
- [ ] 列表、详情、右侧审阅区展示相同 run/artifact version，不出现来源漂移。
- [ ] EP01/EP90 中已观察到的版本、时长、审查范围差异不会被静默覆盖。
- [ ] 缺失 run/audit/schema 字段有接入封装假设，并明确标记来源事实与系统补充事实。

### 8.3 页面骨架与状态

- [ ] 提供 Dream 页面骨架、分集列表、详情 Tabs、版本/运行记录和 Review Panel。
- [ ] 空态、提交态、生成态、校验态、不完整态、冲突态、待审阅、驳回、再次生成、已确认、继续、完成、失败、过期态都有明确行为。
- [ ] 复杂内容使用表格/结构化详情，无复杂画布；无视频相关控件。

### 8.4 Gate 与审计

- [ ] 只有最新、完整、一致、无阻断的活动版本可确认。
- [ ] 驳回原因必填；再次生成创建新 attempt/version 且保留旧事实。
- [ ] 全部必审项确认后才可幂等进入后续执行；服务端再次校验 aggregate hash。
- [ ] 用户审阅与 Agent 审查分离，均保留 actor/source、版本、时间和请求标识。

### 8.5 视觉与命名

- [ ] 截图采用/舍弃有依据，且交互落点可追踪到 PDF 页码。
- [ ] 视觉符合 UI Design v2 的暖纸、少面板、多留白、小面积强调和无卡片规则。
- [ ] 所有新增路由、包名、组件、状态和领域事件使用 `story-workspace` 前缀。

---

## 9. 风险与依赖

| 风险/依赖 | 影响 | 处理 |
|-----------|------|------|
| episodes 没有统一 manifest/schema version | 不同文件可能被错误拼成同一版本 | 接入时生成 manifest envelope；未知 schema 保留原文并标警告 |
| 样本源版本已经不一致 | 用户可能确认过期分镜/Prompt | Gate 以明确 artifact versions 聚合，冲突时阻断 |
| 半结构化 Markdown 解析不稳定 | 集元信息、CAM token、报告表格可能丢失 | 结构化解析失败时展示原始 Markdown；不丢弃源内容 |
| Deck workflow 未声明 requiredArtifactKinds | Gate 不知道完整性范围 | 使用本文默认清单并标出 assumption；快照一旦锁定不得运行中改变 |
| Agent 审查与用户审阅语义混淆 | Agent PASS 可能绕过用户 Gate | 两类状态、事件和 UI 标签严格分离 |
| 运行中覆盖同名文件 | 历史与当前版本不可区分 | content hash + artifact version + immutable attempt；禁止原地覆盖审计事实 |
| 后续执行接口未在本设计定义 | Gate 后动作取决于 Deck workflow | 只输出已确认 run/version 与幂等键；由既有 Deck 合同决定继续或结束 |
| 调研截图偏向视频/深色画布 | 容易偏离当前产品边界与视觉规范 | 仅借用信息层级、确认和历史模式；视频与画布明确排除 |

---

## 10. 关键决策记录

| 决策 ID | 日期 | 决策 | 原因 | 影响 |
|---------|------|------|------|------|
| DEC-020 | 2026-08-01 | 已有 episodes 参考产物和简单描述触发的新产物必须进入同一 `StoryWorkspaceEpisodeProjection` | 防止两套页面、字段和审阅语义 | 接入、列表、详情、Gate |
| DEC-021 | 2026-08-01 | 源文件状态、Agent 审查、用户审阅和后续执行是四个独立状态维度 | `draft`、`PASS`、用户确认和执行完成不能互相替代 | 状态模型与审计 |
| DEC-022 | 2026-08-01 | Gate 绑定最新活动 run 的明确 required artifact versions 与 aggregate hash | 防过期确认、部分确认和客户端绕过 | 确认与后续执行 |
| DEC-023 | 2026-08-01 | 再次生成创建不可变新 attempt/version，旧产物、驳回意见和运行记录永久保留 | 支撑比较、审计和恢复 | 版本/运行历史 |
| DEC-024 | 2026-08-01 | 对样本版本、时长、审查范围冲突采取“并列展示并阻断”，不得静默归一 | 保证来源真实性 | 校验、错误态、Review Panel |
| DEC-025 | 2026-08-01 | 借用 Dreem 的一句话入口、主从详情、确认和历史模式，但用轻纸面表格替代黑色画布并排除视频 | 同时满足调研依据、范围和 UI v2 | 页面与视觉 |

---

## 11. 相对 SUO-230 的增量变更说明

| SUO-230 稳定项 | SUO-241 新增/变化 | 未改变内容 |
|-----------------|------------------|------------|
| 顶部 Dream 与 canonical 路由 | Dream 中栏新增简单描述、episodes 列表/详情和运行历史 | Dream 入口、选中态、兼容重定向 |
| 四步可见 Review Gate | 把“Agent 产出/页面渲染”的输入细化为 artifact bundle、校验和投影；补足版本冲突与不完整态 | 未确认不得继续、服务端防绕过 |
| 三栏与右侧 Review Panel | 右栏新增 artifact 完整性、Agent findings、版本和审计；动作补齐退回/再次生成 | 240px / 自适应 / 360px 骨架 |
| 运行级 `workflow_run_id` | 增加 attempt、artifact ID/version/hash、aggregate hash、retry/supersede 关系 | Deck release/runtime snapshot/lock 来源 |
| 待审阅/驳回/确认/继续/失败 | 增加 empty、validating、metadata incomplete、version conflict、stale review、regenerating | canonical `pending_review` 语义 |
| 表格替代复杂画布 | 明确 Episode/Shot/Prompt/Findings 表与结构化 Tabs | 不实现复杂画布 |
| 排除平台视频 | render-guide 只展示文本/结构化参考元信息 | 无视频预览、上传、生成或模型计费 |

本文不全量改写 SUO-230，也不改变已传播的稳定结论。下游只需围绕本表的新增项做增量消费。

---

## 12. 阻塞或澄清说明

当前无阻止 design 完成的外部 blocker。以下内容以默认假设收敛，后续若合同明确则在同一 Design ID 下增量修订：

- `requiredArtifactKinds` 暂按 script/storyboard/prompts/review-report 默认；最终以锁定的 Deck workflow snapshot 为准。
- 样本未提供 manifest、schema version、run/audit ID，按“接入封装生成但不伪造源 frontmatter”的方案处理。
- 后续执行的具体步骤不在本设计范围内；Gate 只输出已确认 run/version、aggregate hash 与幂等触发语义。
- 若未来允许手工结构化编辑，任何保存都必须生成新 artifact version；不允许在已确认版本上原地修改。

