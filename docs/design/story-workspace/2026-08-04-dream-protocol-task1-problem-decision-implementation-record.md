# 2026-08-04 `.dream` 映射与 Dream 执行布局专项：任务一问题判定实施记录

> **任务**：任务一／问题判定（只做裁决，不改代码）  
> **日期**：2026-08-04  
> **输入基线**：`术语表.md`、`story-workspace-prd.md`、`story-workspace-layout-design.md`、`design_003`、`design_004`、`design_005`、两份 PDF、`vendor/drama-forge/` 及打包说明  
> **输出约束**：本记录是任务二的输入；任务三在任务一、二审阅通过前不启动。

## 1. 调研证据摘要

### 1.1 Dreem 创作者协作页面

逐页核对 `调研Dreem_app平台.pdf` 后，和本专项直接相关的页面如下：

| PDF 页码 | 截图事实 | 对本专项的约束 |
|---|---|---|
| 第 3 页 | 创作者协作页由两层交互组成；数据层包含资产与任务进度，用户通过侧栏指导 Agent 推进创作 | 后续执行页必须同时提供可定位的数据层与 Agent 协作入口，不能只呈现通用运行表格 |
| 第 4 页 | `Assets / Outline` 为同一主工作面的一级切换；资产按 Characters、Locations、Script、World assets 分组 | 主工作面采用「资产 / 故事线」切换与分组行，不复制固定卡片墙 |
| 第 5 页 | 新资产须经创作者确认；故事扩展由后续 Agent 执行，可上传剧本作为指导 | 保留“Agent 产出—用户确认—继续执行”边界；上传本期不做 |
| 第 6 页 | 左侧故事线列表定位右侧叙事点；点击镜头文稿后打开协作窗口，窗口展示人物、主要信息、运镜等 | 执行页主层采用「故事线 / 资产索引 → 叙事点或执行步骤详情」；协作区是上下文相关的第二层，不是始终占据全局右栏 |
| 第 7 页 | 协作窗口内确认后等待生成；左侧为预览，右上有历史记录，左上可上传自定义镜头 | 本期以结构化产物摘要、执行状态与运行记录替代视频预览、上传和播放器；确认与指导动作仍贴近当前叙事点 |
| 第 8 页 | 特殊镜头可附加决策控件和选项 | 仅保留为只读结构化字段；本期不实现可视化控件编辑 |

### 1.2 Ink & Memory UI Design v2.1

`Ink & Memory UI Design v2.pdf` 的执行约束：第 4 页规定 Warm Canvas `#F6EFE5`、Paper Cream `#FFFAF2`、Action Brown `#5F4A36`、Border Paper `#D8C7B3` 等 token 与用途；第 5 页规定减少面板、增加留白、强调色只集中在少数焦点、浅纸面或透明混合分区、页面级最多一条虚线纸边界、静止条目无阴影和外框卡片。故 Dreem 截图只作为信息架构与操作动线来源，不能复制其深色主题、卡片堆叠或视频控件。

### 1.3 drama-forge 上游实际行为

- 原始上游包没有 `.ink/` 或 `.dream/`；`.ink/workspace-init.json` 是本仓打包脚本额外注入（`vendor/pack_drama_forge.py:19-21`、`:81-96`、`:195-201`）。已打包 profile 也只有 `runtime_dirs`、`workspace_files`、`python`（`vendor/dist/drama-studio/plugins/drama-forge/.ink/workspace-init.json:1-19`）。
- 上游把 `stories/`、`assets/`、`exports/`、`.dramaforge/` 定义为用户项目的运行时工作目录（`vendor/drama-forge-upstream-changes.md:41-49`）；插件根只读、产物写会话工作区（`vendor/pack_drama_forge.py:98-110`）。
- 初始化工作流把人物与场景写入 `assets/characters/`、`assets/scenes/`，把故事设定写入 `stories/{project}/`；元信息位于资产卡 YAML frontmatter（`vendor/drama-forge/drama-forge/.claude/skills/drama-init/SKILL.md:206-250`）。
- 分镜工作流读资产卡，写 storyboard 与校验报告；审批状态与审阅时间位于分镜文件本身（`vendor/drama-forge/drama-forge/.claude/skills/drama-storyboard/SKILL.md:8-17`、`:216-249`）。
- 上游运行记录属于 `.dramaforge/runs/{run-id}/`；`RunStore` 将 `run.json`、任务记录和 `events.jsonl` 写入该目录（`vendor/drama-forge/drama-forge/scripts/dramaforge_core/production/run_store.py:96-131`、`:338-382`）。该内部 `run_id` 与 Ink-Dream 的 `workflow_run_id` 没有现存映射。
- 对 `vendor/drama-forge/`、`vendor/drama-forge-upstream-changes.md` 与 `vendor/pack_drama_forge.py` 定向检索 `.dream`、`workflow_run_id`、`projection_entry` 均为零命中；因此“插件在生成阶段写 `.dream/`”是新诉求，不是上游兼容要求。

## 2. P1：`.dream` 映射逻辑缺少独立设计 owner

**问题**：成立。协议合同散落，且 `design_004` 同时承担跳转链、执行页与 `.dream` 详细协议，容易出现双 owner。

**现状证据**：

- 术语表是全仓术语唯一 canonical，但明确只做术语对齐、不改变设计决策（`docs/architecture/术语表.md:3-5`）；当前 `.dream` 一行却同时概括 schema、冻结、原子写和冲突策略（`:28-35`）。
- `design_004` 自称受控增量附录（`docs/design/story-workspace/design_004_story-workspace-dream-surface-execution-page.md:11-19`），但其 §3 实际拥有 schema、触发、生成、冻结和透出完整合同（`:76-246`）。
- `design_005` 是“代码现状版”，明确不得把设计语义误认为已接线（`docs/design/story-workspace/design_005_dream-module-dataflow-and-sequence.md:1-5`）。

**处置决策**：新增 `design_006_dream-protocol-dir-mapping.md`，作为 `.dream` 协议目录交互合同的唯一设计 owner。

**引用关系**：

1. `docs/architecture/术语表.md` 只保留业务术语、技术命名、状态与 `design_006` 链接。
2. `design_006` 唯一拥有触发链路、目录/schema、写入边界、冻结、异常、前端判定和 manifest/receipt 关系。
3. `design_004` 保留 DEC-027～032 原文及历史修订，§3 收敛为摘要与前向引用；执行页布局仍由 `design_004` 与 PRD 共同约束。
4. `design_005` 继续记录已接线代码与 G1～G7，不成为协议规范 owner。

**理由**：术语、规范、代码现状三类文档各自只有一个 owner，既可追溯历史决策，又避免复制 schema 和冻结语义。

## 3. P2：生成期元信息诉求与冻结语义冲突

**问题**：新诉求要求在人物、场景、分镜阶段向 `.dream/` 追加元信息，并把 `workflow_run_id`、运行来源五字段与 `projection_entry` 写入 `workspace.json`；这与 DEC-029 的 pack 期静态事实、运行期不回写和 Agent 只读直接冲突。

**现状证据**：

- 当前 `workspace.json` 只有 `schema_version`、`deck_id`、`plugins[]`、`entry_route`，明确不含 run、binding、snapshot、lock 与时间戳（`design_004:111-138`；代码现状复核见 `design_005:61-66`）。
- `.dream/` 只在首个 agent turn 的 pack 时刻生成，不在 run 创建或 Agent 运行中写入（`design_004:146-181`）；冻结工作区只校验、不重建（`:202-228`）。
- DEC-029 原文规定运行期不回写、run 级事实只认 REST API（`design_004:431`），2026-08-03 注记再次确认该结论（`:441`）。
- 当前唯一写方是 packer；`.dream/` 无 REST 读方（`design_005:236-246`）。
- G1 queued 后无生产推进方、G2 confirm 不驱动 run、G3 preflight/run 无 UI 接线（`design_005:256-268`）。
- 上游真实写区和内部 run owner 见 §1.3；上游没有 `.dream` 写行为。

**处置决策**：选择 **a）维持冻结**。

1. `workspace.json` 继续使用 `dream-surface/v1`，字段保持 `{deck_id, plugins[], entry_route}`，不加入 `workflow_run_id`、`deck_plugin_binding_id`、`binding_revision`、`deck_plugin_version`、`deck_runtime_snapshot_id`、`runtime_plugin_lock_id` 或 `projection_entry`。
2. 人物、场景、分镜的生成期元信息继续由插件写入其既有 canonical 工作区文件；host 通过现有 Agent 输出解析、story-workspace 数据库、`story-workspace-output` SSE 与 REST API 提供审阅和执行投影。
3. 运行来源与状态只从 actor-scoped run REST API 读取。`projection_entry` 在 G5 的 projection 端点及 schema 尚未成立前不得写入静态文件；将来若需要，只能作为 REST 响应中的受控链接或静态路由模板另立合同，不能携带某次 run 的事实。
4. Agent 对 `.dream/**` 继续只读；本专项不新增运行期子区，不修订 DEC-029 的冻结边界。

**理由**：

- 上游兼容性不要求 `.dream` 运行期写入；强加写入会把资产文件、`.dramaforge/runs`、host REST/DB、`.dream` 变成四个事实 owner。
- pack 时尚无 run；在 `workspace.json` 回填 run 会破坏同 digest 字节一致、冻结只校验与原子物理映射不变量。
- G1～G3 是生产推进、confirm 驱动和 UI 接线缺口；增加一个文件投影既不推进状态机也不建立 UI 链路，只会掩盖断链。
- `projection_entry` 依赖 G5；端点不存在时写入口会成为不可兑现的合同。

**否决项**：

- b）分层扩展暂不采纳：即使放在 `.dream/runs/`，仍需新增 host run 与插件内部 run 的绑定、单 writer、并发、失败回滚、清理和可重建规则；当前没有消费方或 G1～G3 闭环支撑。
- c）修订 DEC-029 不采纳：没有证据证明 REST API 不应继续作为运行事实唯一真相源。

## 4. P3：后续执行阶段布局

**问题**：PRD 把固定 240 / 自适应 / 360 三栏写成唯一桌面布局（`docs/design/story-workspace/story-workspace-prd.md:479-531`），而 `design_004` 的执行页是通用数据层 + 常驻 360px 指导栏（`design_004:300-321`）；两者都没有完整表达 PDF 第 6～7 页的「故事线定位 → 叙事点 → 上下文协作窗口」动线。

**处置决策**：**审阅三栏保留；执行阶段调整为独立的“两层协作工作台”，替换“全站唯一三栏”的表述。**

- 审阅阶段：保留左导航 + 中表格/内容 + 右审阅详情的桌面三栏，因为右栏 owner 是当前 artifact version 的审阅。
- 后续执行阶段：继续使用独立路由 `/story-workspace/runs/:storyWorkspaceRunId/execution`，不嵌入审阅三栏；第一层为左侧 `Assets / Outline` 索引与中部叙事点/执行步骤主工作面，第二层为选中项触发的上下文协作区，承载确认状态、Agent 指导、运行历史和失败重试。
- 不复制视频：PDF 的镜头预览、上传、播放器替换为结构化产物摘要、人物/场景引用、步骤状态和运行记录；不引入可编辑画布。
- 视觉必须引用 UI Design v2.1 第 4～5 页：Warm Canvas / Paper Cream、Action Brown 少量焦点、留白和行分隔、页面级单一虚线纸边界、静止条目无卡片阴影。

**理由**：该形态保留 DEC-030 的“独立执行页、审阅右栏与指导职责不混用”原则，同时修订其内部信息架构，使定位和协作动作对齐 PDF，而不是把固定三栏比例误当调研结论。

## 5. P4：PRD 整体更新范围

任务二至少更新下列章节：

1. 元信息、背景与目标（`story-workspace-prd.md:3-28`）：把前置准备与四阶段主生命周期分开。
2. 范围内/外（`:32-60`）：区分审阅三栏与执行两层工作台；补 `.dream` 冻结边界。
3. 核心 DEC 与 Dreem 调研解读（`:64-207`）：保留 DEC-003/007 原文，追加 2026-08-04 注记；纠正“创作者协作页=固定三栏”的过度归纳。
4. 模块职责与来源字段（`:209-263`）：明确运行事实只认 REST，`.dream` 不承载 run provenance。
5. Dream 可见布局和 Gate（`:265-325`）：按四阶段校准页面状态。
6. 信息架构与路由（`:329-362`）：补独立执行页。
7. Dream 入口及内容页面（`:379-478`）：把“待审阅卡片”改为轻纸面条目。
8. 布局交互（`:479-531`）：将“唯一三栏”改为阶段化布局。
9. 核心交互（`:533-623`）：主叙事收敛为「Agent 产出 → 页面渲染 → 用户审阅确认 → 后续执行」，preflight 是前置链路。
10. 状态、视觉和验收（`:627-784`）：增加执行协作状态，移除全站固定三栏验收。
11. 风险、DEC、修订记录、未决项与验证（`:788-881`）：保留原决策文本，追加 2026-08-04 修订注记和 G1～G7 遗留说明。

## 6. P5：本期不做

- 不允许 Agent 或插件写、改、删 `.dream/**`；不新增 `.dream/runs/`。
- 不把 `workflow_run_id`、运行来源五字段、时间戳或 `projection_entry` 写入 `workspace.json`。
- 不实现故事板/时间线/场景布局/决策控件等复杂画布编辑。
- 不实现平台视频生成、镜头预览、上传、播放器、外部模型选择或计费。
- 不实现用户手动创建故事、人物、场景；不实现人物三视图/四视角与可编辑图库。
- 不实现移动端、平板端、触控和响应式布局。
- 不实现积分计费、多人实时协作或历史版本编辑。
- 不修改 Deck 编辑器内部工作流、提示词、secret-ref、插件配置与发布能力。
- 不新增数据库 Schema/DDL，不修改 `backend/database.py`。
- 任务一、二不实现执行引擎步骤语义，不接 G1～G7；其中 G1～G3、G5、G6 必须在任务三方案中逐项决定“接线或遗留”，不得以文档投影暗示已完成。

## 7. 任务一完成判定

- P1～P5 均已形成单一结论，P2 已显式裁决为方案 a。
- PDF 布局与视觉证据、上游插件真实写区、DEC-029 与 G1～G3 均已进入理由链。
- 本任务只新增本实施记录；未修改代码、schema、DDL 或插件制品。
- 下一步：以本记录为输入执行任务二，新增 `design_006`，先更新术语表，再更新 PRD 与受影响 DEC 注记。
