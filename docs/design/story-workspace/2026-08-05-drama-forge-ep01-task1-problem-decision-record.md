# drama-forge 第一集完整工作流接入：任务一问题判定实施记录

> 日期：2026-08-05  
> 阶段：任务一（调查、问题判定与产品裁决）  
> 结论：通过；本记录只新增调查与裁决文档，没有修改生产代码  
> 后续 canonical owner：待任务二建立的 `design_009`

## 0. 本轮规划前置器

### 0.1 Optimized Prompt

在不修改生产代码的前提下，以 vendor README、对应 skill/command/hook、模板/schema、真实 EP01 示例，以及 Ink-Dream 当前前后端实现和真实 run 文件为证据，还原 drama-forge 从零到第一集的真实顺序、依赖、产物和重复规则；识别规范与实现漂移；逐项完成 P1—P7 产品裁决。每项裁决必须采用“问题 → 现状证据 → 根因 → 可选方案 → 最终决策 → 影响范围 → 风险 → 验收方式”，明确唯一推荐方案、truth ownership、稳定身份、渐进恢复、安全 API 边界与本期非目标。所有结论附文件与行号或只读检查输出；不得把文件名、数组位置、Agent 消息或浏览器状态当作未被证明的业务事实。

### 0.2 Optional Enhancers

- 建立“命令 → 输入 → 产物 → owner → consumer → revision”的证据矩阵。
- 对 `Episode → 叙事点 → 场景 → 镜头 → Prompt → Render` 计算可机器验证的关联完整率；无法证明的关联显示“尚未关联”。
- 单列 README、skill、hook、生成脚本和样例之间的合同漂移，防止把历史实现误当 canonical contract。

### 0.3 执行计划

1. 记录工作树、分支、近期提交和运行服务，划定其他工作线文件。
2. 读取项目术语、现有设计、UI Design v2、最新实施记录。
3. 读取 vendor README 涉及的全部技能、CLI、hook、模板、schema 和 EP01 示例。
4. 读取 Execution、Dream files、surface、run deep-link、权限与恢复实现及测试。
5. 用只读脚本核验 EP01 的 shot/prompt/render 关联和当前真实 Dream run 产物。
6. 完成 P1—P7 裁决与唯一推荐方案；记录仍需任务二验证的风险。

### 0.4 验收标准

- 覆盖 vendor 从零到第一集的完整命令顺序、输入、输出、依赖、重复规则和当前接入差距。
- P1—P7 均具备完整问题判定结构和行号证据。
- 明确每类 artifact 的唯一 owner、消费者、更新方式和不可越权边界。
- 明确稳定 ID、非位置关联、渐进到达、刷新与重新进入恢复合同。
- 本阶段仅新增本记录，不修改生产代码。

## 1. 调查边界与证据优先级

### 1.1 证据优先级

当资料互相冲突时，本轮采用以下优先级：

1. canonical 文件的实际内容和当前可执行代码；
2. vendor README 明示的“典型工作流”；
3. 当前 manifest、模板和 schema；
4. skill 中仍与 canonical 路径一致的语义约束；
5. 历史设计和已漂移的 hook/生成脚本只作为风险证据，不反向改写事实。

理由：vendor 自身声明 files 是 truth、索引/报告可重建，手工修改优先，且缓存不得覆盖真实文件（`vendor/drama-forge/drama-forge/README.md:459-469`）。Ink-Dream 则规定 `.dream` 是宿主投影协议，不替代 drama-forge 的 canonical episode 文件（`docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md:27-46`）。

### 1.2 工作区安全记录

- 当前分支：`story-workspace`；调查开始时相对远端 ahead 25。
- 调查开始时 HEAD：`dbd09b6 docs(story-workspace): record Dream Agent hierarchy rework`；近期提交还包括 `1e6e157`、`c67b3c3`、`ee7b4c3`、`3d2dcf8`。
- 其他工作线已有未提交改动，涉及 `backend/database.py`、Dream launch、Story Workspace contracts、Chat、Deck、Settings、Subscription 及若干测试和截图。本轮未覆盖、回滚、格式化或提交这些文件。
- 调查时已存在的服务监听端口包括 8765、5173、5174、4723、18789；本轮未停止这些用户服务。
- 本轮为阅读 PDF 建立了受控临时渲染目录 `tmp/pdfs/ui-design-v2/`；它不是产品制品，将在最终清理阶段删除。

### 1.3 UI Design v2 约束

设计 PDF 第 4 页定义暖纸张色板，第 5 页明确“少面板、多留白、轻纸面”，页面级仅一条虚线，静态状态不使用卡片与阴影，仅 hover 提供轻反馈（`docs/prd/Ink & Memory UI Design v2.pdf:4-5`，页面渲染目视证据：`tmp/pdfs/ui-design-v2/page-04.png`、`tmp/pdfs/ui-design-v2/page-05.png`）。现有布局设计也要求米白底、纸面感、克制阴影和清晰三层层级（`docs/design/story-workspace/story-workspace-layout-design.md:45-54`）。

## 2. drama-forge 真实工作流还原

### 2.1 README 明示的完整顺序

README 的“典型工作流（从零到第一集）”给出唯一明确顺序：init → plan → script → script-reviewer → asset → storyboard → prompt → full-chain review → atomic commit validation → render+voice → edit → promote；第 3—9 步对每一集重复，资产可跨集复用（`vendor/drama-forge/drama-forge/README.md:353-381`）。完整流水线还在概览中表述为从 concept 到 publish（`vendor/drama-forge/drama-forge/README.md:10-12`）。

| 顺序 | 命令/动作 | 主要输入与前置依赖 | 权威输出 | 重复/增量规则 | 当前 Ink-Dream 接入 | 缺失能力 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `/drama-forge:drama-init` | 项目概念、类型、语言；新 story slug | `project.yaml`、`genre.yaml`、ledger、角色索引/锁和目录骨架 | 已存在项目时 CLI 拒绝覆盖（`scripts/dramaforge.py:749-751`） | Dream launch 会要求执行 init（`backend/services/story_workspace/dream_launch_gateway.py:679-691`） | 没有持久化 story/episode 绑定；README 树与 CLI 实际创建物不一致 |
| 2 | `/drama-forge:drama-plan` | project/genre、角色与世界观 | 项目/季/集规划；EP outline | 审阅通过后锁定，可批量形成 episode outlines（`skills/drama-plan/SKILL.md:157-176,194-210,418-437`） | 未接入 | 故事线和显式叙事点尚无 surface |
| 3 | `/drama-forge:drama-script EP01` | 已批准 EP01 outline、角色/场景资产 | `episodes/EP01/script.md` | 同一 episode 按文件 revision 更新 | 未接入；当前 launch 直接跳到 storyboard | 对白、动作、场景内容与 revision 均未消费 |
| 4 | `/drama-forge:drama-script-reviewer` | script、outline、连续性资料 | `review-report.md` 的剧本审阅内容 | 可随 script revision 重审；报告必须标明审阅范围 | 未接入 | 报告范围和只读呈现缺失 |
| 5 | `/drama-forge:drama-asset` | 已确认剧本、角色/场景需求 | 角色、场景、道具资产 | 资产可复用；手工 canonical 修改优先 | 当前 `.dream` characters/scenes 是宿主投影 | episode 与资产来源关联不完整 |
| 6 | `/drama-forge:drama-storyboard EP01` | script、资产、镜头规范 | `episodes/EP01/storyboard.yaml` | 同一 `shot_id` 跨 revision 保持身份 | 已部分接入并投影到 `.dream/stages/storyboards` | 只消费部分 shot 字段；缺少 outline/script 上游关系 |
| 7 | `/drama-forge:drama-prompt EP01` | storyboard shot、资产锚点 | `episodes/EP01/prompts/` | 以显式 `shot_id` 关联，不得按位置配对 | 未接入 | 列表、关联诊断、分页/限额缺失 |
| 8 | `/drama-forge:drama-full-chain-review` | outline/script/storyboard/prompts/资产 | `review-report.md` 中完整链路审阅 | 每次上游变更后可重审；条件通过不是虚构的失败状态 | 未接入 | 范围、结论、定位链接缺失 |
| 9 | `dramaforge episode-commit --episode 1`，并执行原子校验语义 | script、可选 storyboard/prompts、review | 内部索引、ledger、备份/提交结果 | CLI 会刷新索引与备份（`scripts/dramaforge.py:1139-1148`） | 未接入 | 当前 hook 路径和格式已漂移，不能照搬 |
| 10 | `/drama-forge:drama-render EP01` + `/drama-forge:drama-voice EP01` | storyboard、prompts、角色/场景锚点 | render guide/注册后的 render 产物、voice 产物 | 每个 shot 可增量产生 | 未接入 | 示例只有 render guide/队列，没有真实媒体；语音不在本期页面边界 |
| 11 | `/drama-forge:drama-edit EP01` | render、voice 等制作产物 | edit/export 产物 | 集级制作 | 未接入 | 本期明确不做视频剪辑 |
| 12 | `/drama-forge:drama-promote EP01` | 已完成 episode | 宣发产物 | 发布后按需生成 | 未接入 | 本期明确不做宣发 |

README 对 plan、script/reviewer、asset、storyboard、prompt、render/voice/edit/promote 的输出说明分别见 `README.md:99-185`；命令清单和核心输出见 `README.md:246-262`。

### 2.2 规范与实现漂移

1. README 的 init 树列出 outline、script、storyboard、prompts 和 review（`README.md:51-97`），但 CLI `cmd_init` 实际只创建项目骨架、project/genre、ledger、角色索引/锁，随后提示 plan（`scripts/dramaforge.py:723-822`）。因此这些 EP01 文件不能被当作 init 的既成输出。
2. README 与 manifest 的 canonical storyboard 是 `episodes/EPxx/storyboard.yaml`（`dramaforge.manifest.yaml:11-19`），旧 storyboard skill 却仍写 `storyboards/.../storyboard-final.md`（`skills/drama-storyboard/SKILL.md:198-247`）。
3. prompt skill 仍描述旧 `storyboard/<project>/<episode>` 和单个 `prompt_package.yaml`（`skills/drama-prompt/SKILL.md:1-19,219-290`），真实 EP01 则使用 `episodes/EP01/prompts/ep001-prompts.yml`。
4. Git hook 只在 Bash 命中 `git commit` 后运行（`.claude/hooks/validate_commit.sh:48-71`），且校验 `storyboard.md` 等旧路径（`.claude/hooks/validate_commit.sh:123-182`）；CLI `episode-commit` 使用 canonical `storyboard.yaml`、prompts 目录和 review，并允许 storyboard/prompts 缺失后跳过（`scripts/dramaforge.py:1003-1085`）。本期不得把旧 hook 当作 API 合同。
5. render skill 的实际语义是生成制作指导而非真实视频（`skills/drama-render/SKILL.md:347-434`）；示例 `renders/render-guide.md` 也只有逐 shot 的 pending 队列（`stories/didi-zhengzhou/episodes/EP01/renders/render-guide.md:1-24`）。

### 2.3 真实 EP01 产物核验

示例目录包含且仅包含以下第一层产物：`episode-outline.md`、`script.md`、`storyboard.yaml`、`prompts/ep001-prompts.yml`、`renders/render-guide.md`、`review-report.md`。内容证据如下：

- outline 只有 frontmatter 和简短说明，声明从 script 投影，未采用完整模板的 Story Goals/Scene Sequence（`stories/didi-zhengzhou/episodes/EP01/episode-outline.md:1-31`）。
- script 具有 `status: draft`、version 5、核心冲突、hook、S01/S02 等显式场景和对白/动作（`stories/didi-zhengzhou/episodes/EP01/script.md:1-43,97-105,219-234`）。
- storyboard 有 45 个显式且唯一的 `shot_id`，`generated_from` 仍写 `script@v1`，但没有通用 narrative beat 或 script scene 外键（`stories/didi-zhengzhou/episodes/EP01/storyboard.yaml:1-20`）。
- prompt 文件逐项携带 `shot_id`（`stories/didi-zhengzhou/episodes/EP01/prompts/ep001-prompts.yml:1-22`）。
- render guide 队列逐项携带 shot identity，但都是 pending，不等价于真实媒体（`stories/didi-zhengzhou/episodes/EP01/renders/render-guide.md:1-24`）。
- review 只审剧本且结果为 `CONDITIONAL_APPROVAL`（`stories/didi-zhengzhou/episodes/EP01/review-report.md:1-18`），不能伪装成 full-chain review 已完成。

只读 YAML/Markdown 核验输出：

```text
storyboard_total=45 unique=45
prompt_total=45 unique=45 exact_shot_set=True missing=0 orphan=0
render_queue_total=45 unique=45 exact_shot_set=True missing=0 orphan=0
regular_scene_encoded=31
supplemental=14
scene_ref_counts={'scene_train_station_night':24,'scene_car_interior_night':21}
storyboard_shots_with_characters=20 prompt_shots_with_characters=0
storyboard_dialogue_nonempty=0
```

结论：prompt/render-guide 与 shot 的显式关联完整率为 100%；能从 regular shot ID 明确解析 SNN 的只有 31/45，14 个 `SUP-E01-*` 不得按数组位置或邻近 shot 静默归入 script scene。prompt 中角色为空而 storyboard 有 20 个带角色 shot，证明样例和生成器也可能漂移，UI 必须显示来源与关联诊断。

## 3. Ink-Dream 当前接入程度

1. Dream launch 当前明确要求同一 Dream Agent 执行 run → characters → scenes → storyboards 后等待确认（`backend/services/story_workspace/dream_launch_gateway.py:679-691`）；Agent context 也重复这一三阶段顺序（`backend/claude_agent/context_builder.py:435-459`）。它跳过了 vendor 的 plan → script → reviewer → asset → storyboard 顺序。
2. host 协议只映射 characters、scenes、storyboards 三个 stage，storyboard canonical 源是 episode 的 YAML（`plugins/ink-dream-story/skills/dream-story-workflow/references/dream-file-sync.md:40-73`）。
3. `.dream` run/stage contract 固定为三个 required stages（`backend/story_workspace/contracts.py:531-613`）；前端 parser 和 polling hook也固定同一集合（`frontend/src/hooks/story-workspace/useStoryWorkspaceDreamFiles.ts:19-20,138-190`）。
4. 后端已经具备 actor/run/thread/workspace 校验、受控相对 source path、`O_NOFOLLOW` 和缺失 stage 可恢复语义（`backend/services/deck/story_workflow_gateway.py:235-323,1214-1287`；`backend/services/story_workspace/dream_file_service.py:1076-1160,1382-1526`）。这些能力应复用，不应开放任意文件读取。
5. Execution 当前 view model 只认识三个 stage，并把内容投影成扁平 Assets/Outline（`frontend/src/pages/story-workspace/executionViewModel.ts:11-18,60-99`）。页面 Outline 是扁平条目；聚焦视图还写死一个展示编号“01”，不是详细分镜（`frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx:230-292,293-374`）。
6. 当前页面未挂载 `ChatView`；Dream Agent 仅以预览和对话框存在（`StoryWorkspaceExecutionPage.tsx:178-228,376-383`）。该边界必须保持。
7. `.dream` REST polling 是文件事实通道；SSE 只做失效提示，轮询间隔不低于 5 秒（`useStoryWorkspaceDreamFiles.ts:224-240,346-361`）。
8. 现有真实 run `run_2cb...` 的 `.dream` 只有 characters/scenes/storyboards；其 EP01 只有 `storyboard.yaml`，`generated_from` 是 `outline-skeleton@chapter-1`，没有 outline/script/prompts/renders/review。这是当前接入差距的磁盘事实，不可用预期行为补齐。

## 4. P1 第一集完整工作流边界

### 问题

init 后还应执行什么；哪些属于初始创作与 Episode execution；是否沿用同一 Dream Agent/run/thread；run 如何绑定 story/episode；用户如何推进且不增加 vendor 不存在的业务状态。

### → 现状证据

- vendor 顺序和重复边界见 `README.md:353-381`。
- vendor 采用 Ask → Options → Decide → Draft → Approve 的共同门禁，不支持无确认地一路自动执行（`README.md:189-201`）。
- 当前 Ink-Dream 只执行三 stage 后一次确认（`dream_launch_gateway.py:679-691`；`dream-file-sync.md:75-90`）。
- run contract 有 workflow_run_id、thread_id、workspace_root 和 revisions，但没有 story/episode identity（`backend/story_workspace/contracts.py:531-555`）。
- 当前 canonical 设计禁止自行引入驳回、失败、重试和归档业务流程（`design_006_dream-protocol-dir-mapping.md:14-23,483-493`）。

### → 根因

现有集成把“可确认的 Dream 初稿投影”误当成 drama-forge 的完整第一集流程；run 与 episode 只通过 storyboard `source_file` 偶然相连，outline 先到达时没有可恢复绑定。

### → 可选方案

1. init 后全自动串行至 render：违背 vendor 的确认门禁，长任务也无法可靠恢复。
2. 每个命令创建新 run/thread：割裂同一创作上下文和恢复链路。
3. **同一 Dream Agent、同一 run、同一技术 thread，按 vendor 阶段顺序由用户触发“继续下一步”；用持久化 episode binding 和文件存在/revision 推导进度，不新增状态机。**

### → 最终决策

采用方案 3。

- Initial Dream 边界：建立 concept/story，执行 init，并形成可确认的前期创作草稿。对于新 run，后续 writer 必须按 vendor 顺序执行；现有“先 storyboard”运行作为 legacy partial run 展示，不伪造成完整链路。
- Episode execution 本期边界：plan → script/reviewer → asset → storyboard → prompt → full-chain review → episode-commit 校验语义 → render guide/已注册 render 展示。
- voice、edit、promote 是 vendor 后续真实步骤，但属于音视频制作/宣发，本期只在流程图标明边界，不在工作台提供操作。
- 页面只提供由后端计算的单一上下文操作“继续下一步”，发送受控意图给同一 Dream Agent；不向用户展示 slash command、原始工具参数或隐藏 thread。
- run 下新增受控 `.dream/runtime/runs/<run>/episode.json` 物理映射，schema 建议为 `dream-episode/v1`，只拥有绑定身份：run、受校验 story slug、`EP\d+` episode code、canonical episode root 的相对引用和 binding revision。它不是 episode 内容 owner。
- v1 一个 run 绑定一个 episode；响应使用不透明 episode ID。未来可演进为列表，不改变 artifact owner。

### → 影响范围

Dream launch/context、受控 writer tool、Story Workspace backend contract/service/router、Execution adapter/view model/page、恢复测试和迁移展示。

### → 风险

当前 legacy run 顺序与 vendor 冲突；full-chain review 与 script-reviewer 共用报告路径可能覆盖范围；外部模型/渲染依赖可能阻止真实 E2E 到达末端。

### → 验收方式

从 README 生成的 workflow fixture 与 runtime next-step resolver 顺序一致；同一 run/thread 的 binding 在刷新/重新进入后不变；legacy run 明确显示已有文件与缺失文件，不伪造已完成步骤；页面不出现新业务失败/驳回/重试/归档状态。

## 5. P2 产物与 truth ownership

### 问题

`.dream`、episode 文件、Dream Agent 消息和前端草稿谁拥有哪类事实，哪些允许修改，如何避免双 owner。

### → 现状证据

- `.dream` 是宿主投影，canonical storyboard 仍在 drama-forge episode 路径（`design_006_dream-protocol-dir-mapping.md:27-46,58-84`）。
- outline 模板定义 story goals、核心冲突、SC-NN 场序、叙事功能、场景目标、关键对白节拍和角色弧线（`templates/episode-outline.md:85-120,128-245,350-429`）。
- script 模板定义场景正文和下游链接（`templates/script-template.md:145-179,357-378`）。
- storyboard 格式以稳定 `shot_id` 为镜头身份；prompt 格式用同一 shot_id 关联。真实样例也验证精确集合相等。
- 现有设计规定 Agent 消息是沟通事实，文件与 run snapshot 才是业务恢复事实（`design_008_dream-reentry-and-agent-workbench.md:519-559`）。

### → 根因

当前 surface 把 `.dream` stage 摘要、Agent 文本和局部 UI 混在一个页面，却没有 episode artifact manifest 与字段级 owner 表。

### → 可选方案

1. 把 Agent 消息解析成 episode 内容：易漂移且不可可靠恢复。
2. 前端复制一套可编辑 JSON：形成第二 owner。
3. **canonical episode 文件拥有内容；`.dream` 只拥有投影/binding/revision；Agent 消息拥有沟通；本地 draft 只拥有未提交输入。**

### → 最终决策

采用方案 3，字段级 owner 如下：

| 对象 | 唯一 owner | 页面消费者 | 修改方式 |
| --- | --- | --- | --- |
| `.dream` stage | 宿主 stage snapshot/revision | Dream 与 Execution 的渐进状态 | 仅受控 writer + CAS |
| `episode.json` | run↔story↔episode 绑定投影 | episode artifact service | 仅受控 writer；前端不得传路径 |
| `episode-outline.md` | 故事线、story goals、核心冲突、显式 SC 叙事点 | 故事线/叙事点导航 | 本期只读；修改请求交给 Dream Agent 回写 canonical 文件 |
| `script.md` | SNN 场景、动作、对白、场景级剧本 | 场景与镜头上下文 | 同上 |
| `storyboard.yaml` | shot 结构、顺序和 8 层镜头字段 | 镜头列表/检查器 | 同上 |
| `prompts/` | 每个显式 shot_id 的 prompt 文本与参数 | shot 的 Prompt 辅助页 | 同上；不得以 storyboard prompt 副本覆盖 |
| `renders/` | render guide/队列及有可验证 shot 引用的已注册媒体 | Render 辅助页 | 外部 renderer/受控登记；无显式关联即“尚未关联” |
| `review-report.md` | 审阅范围、结论、问题和建议 | Review 只读辅助页 | 只读展示；新审阅通过 Dream Agent 重新生成 |
| Dream Agent messages | 用户与 Agent 的沟通历史 | 预览/对话框 | 消息 API；不得覆盖 artifact |
| 前端 local draft | 未提交的输入与临时选择 | 当前浏览器会话 | 提交后成为消息；不拥有 run/episode/artifact 恢复事实 |

### → 影响范围

adapter 必须输出 provenance；组件不得跨文件合并写回；编辑入口必须改为“请 Dream Agent 修改”，而非本地 artifact editor。

### → 风险

同一 `review-report.md` 可能承载不同阶段报告；需要用报告内 scope/revision 显示范围，不能仅由文件存在推导 full-chain review 完成。

### → 验收方式

contract 测试逐字段验证 source artifact；Agent 消息更新不改变 artifact response；review 为只读；任何无法证明的关联显示“尚未关联”。

## 6. P3 故事线与叙事点信息架构

### 问题

如何建立 `Episode → Story Arc / Narrative Beat → Scene → Shot → Prompt → Render`，并在 vendor 缺少稳定 ID 时避免数组下标身份。

### → 现状证据

- outline 模板的每个 `SC-NN` 明确 1:1 映射到 script `SNN`，并携带叙事功能/摘要/目标/关键对白节拍（`templates/episode-outline.md:128-228`）。
- script 样例具有 S01/S02 显式 heading（`stories/didi-zhengzhou/episodes/EP01/script.md:36-43,97-105`）。
- storyboard 的 `scene_ref` 值是资产场景（本例仅车站/车内），不是 script scene；补充 shot ID 不含 SNN。
- 当前前端 key 用 stage+entityId，扁平索引仍显示数组序号（`executionViewModel.ts:60-99`；`StoryWorkspaceExecutionPage.tsx:331-348`）。

### → 根因

vendor 有 episode、SC-NN、SNN 和 shot_id，但没有独立 Story Arc ID，也没有对所有 storyboard shot 强制 script scene/narrative beat 外键。

### → 可选方案

1. 用数组下标：revision 插入后身份漂移。
2. 依据文本/邻近位置猜测：不可验证。
3. **adapter 为已有显式 key 生成稳定不透明 view ID；只在 vendor 明示 1:1 规则时关联；扩展新 writer 输出可选外键，legacy 缺失保持“尚未关联”。**

### → 最终决策

采用方案 3。

- Episode ID：后端以 run binding 生成不透明 ID，不暴露路径。
- Story Arc：v1 每集一个 episode arc；`arcId = hash(episodeIdentity, "arc")`。它是 view-model 容器，内容仍归 outline。
- Narrative Beat：仅将 outline 中显式 `SC-NN` 段作为 beat；`beatId = hash(episodeIdentity, SC-NN)`。character beats 只作为角色弧线辅助信息，不冒充主叙事点。
- Scene：script 的显式 SNN；`sceneId = hash(episodeIdentity, SNN)`。只利用模板证明的 SC-NN ↔ SNN 规范化编号关联。
- Shot：canonical `shot_id`；`shotViewId = hash(episodeIdentity, shot_id)`。
- Prompt：显式 `shot_id` + prompt kind；Render：显式 shot/prompt 引用 + 受控相对 artifact identity。revision 不进入稳定 identity。
- 对新 writer/schema 增加可选 `narrative_beat_ref`、`script_scene_ref`；adapter 兼容 legacy。没有外键的 `SUP-*` 不按位置配对。
- 响应包含 association coverage、missing、orphan 和 diagnostics；UI 用“尚未关联”显式呈现。

### → 影响范围

outline/script parser、storyboard/prompt/render adapter、schema/writer、view model、selection reducer、键盘导航和质量门测试。

### → 风险

自由格式 Markdown 可能缺少 SC/SNN；writer 扩展需保持 vendor 兼容；hash 输入必须使用服务端受控 identity 而非敏感绝对路径。

### → 验收方式

同一实体跨 revision 保持 view ID；插入/重排不改变现有选择；31 个可证明 regular shot 正确关联，14 个 supplemental 明示未关联；缺失/孤儿统计可机器验证。

## 7. P4 Execution 页面交互

### 问题

如何在不把 Dream 变成 Chat、也不堆叠卡片的前提下展示故事线、叙事点、场景、镜头及辅助 artifact。

### → 现状证据

- 现有 canonical 页面是独立 Execution route 和两层工作面，不应挂固定全局第三栏（`design_004_story-workspace-dream-surface-execution-page.md:255-347`）。
- 现有设计已要求 Outline 支持叙事层级，但当前只是 placeholder（`design_007_dream-business-module-interaction.md:297-324`）。
- Agent 预览/对话框与内容面分离（`design_008_dream-reentry-and-agent-workbench.md:153-192,213-275`）。
- UI Design v2 约束见本记录 1.3。

### → 根因

现有 execution view model 只有 stage item，没有 episode hierarchy、artifact provenance 和 selection stability。

### → 可选方案

1. 单一纵向时间线：难以同时阅读 storyline 与详细 shot。
2. 后台式多 Tab 数据表：割裂叙事关系，辅助产物抢占主层级。
3. 固定三栏：窄屏困难且违背现有两层工作面。
4. **章节式 master-detail：左侧故事线/叙事点导航，右侧场景与镜头创作面；shot 检查器在右侧上下文内展开；Prompt/Render/Review 为辅助页签。**

### → 最终决策

采用方案 4。

- 默认进入 Episode Overview：标题、故事目标/冲突/hook、artifact 进度细线和缺失提示；不自动选 shot。
- 左侧按 outline 顺序列叙事点，显示 SC-NN、叙事功能、摘要和关联覆盖；选择后 URL 不改变，稳定 selection 留在页面状态。
- 右侧显示 beat 目标、关键对白节拍、关联 script scene，再按 scene 展开 shot 序列。
- 选择 shot 后，在同一内容工作面进入 detail inspector：storyboard 的镜头字段、script 上下文/对白、Prompt、Render、来源 revision；Escape 返回父层并恢复焦点。
- Prompt、Render、Review 不进入左侧主叙事树。Review 可从问题定位到已关联 beat/scene/shot；无定位则保持报告段落。
- 未生成显示“尚未生成”和下一步含义，不显示虚构内容；未关联显示“尚未关联”。
- 新 revision 在后台合并；稳定 ID 存在时保留 selection、滚动锚点和键盘焦点；实体被删除时回到最近父级并用 `aria-live="polite"` 通知。
- Dream Agent 预览只呈现状态和最近沟通；对话框负责继续/修改请求，不拥有 storyline。严禁直接挂载 `ChatView`。

### → 影响范围

Execution CSS/布局、hierarchical view model、selection reducer、inspector、artifact tabs、Agent dialog adapter、响应式和 a11y 测试。

### → 风险

右侧信息密度高；窄屏需单列 drill-down；旧 outline 缺少 SC 段时主导航可能为空。

### → 验收方式

桌面与窄屏线框评审；键盘可完成 beat/scene/shot 导航；Escape/焦点恢复通过；页面源码与运行时均无 ChatView；辅助内容不改变故事线主层级。

## 8. P5 渐进生成和恢复

### 问题

各 artifact 分阶段到达、revision 更新、离开/刷新/重新登录时如何恢复，且不以 localStorage 为 owner。

### → 现状证据

- 当前 stage API 允许缺失 stage，确认前继续 polling（`dream_file_service.py:1382-1526`；`useStoryWorkspaceDreamFiles.ts:224-240,346-361`）。
- 当前聚焦选择只在 key 仍存在时保留（`StoryWorkspaceExecutionPage.tsx:118-126`），但 key 仅覆盖 stage/entity。
- reentry 设计要求重新从 run、workspace、binding、snapshot 和文件事实恢复（`design_008_dream-reentry-and-agent-workbench.md:384-418,420-485`）。

### → 根因

episode artifacts 没有绑定、manifest、aggregate revision 或条件请求；浏览器无法区分“未生成”“未关联”“解析失败”。

### → 可选方案

1. localStorage 记住 episode/文件内容：越权且会过期。
2. Agent 消息推断生成阶段：不可恢复。
3. **后端 binding + artifact manifest + REST polling/ETag 是事实；SSE 只使缓存失效；前端保留最后成功快照和稳定选择。**

### → 最终决策

采用方案 3，并按以下表现恢复：

| 文件事实 | 页面表现 |
| --- | --- |
| outline 未生成 | Episode 骨架 + “故事线尚未生成”；允许受控“继续下一步” |
| outline 已生成 | 独立展示故事线；没有 SC 段则叙事点为空，不从 script 反推故事 |
| script 生成中/已到达 | 保留 outline；逐个加入可证明关联的 scenes |
| storyboard revision 更新 | 按 shot_id 增量替换字段；不重置仍存在的 beat/scene/shot |
| prompts 逐步产生 | 每个 shot 显示 prompt 可用/尚未生成；孤儿 prompt 单列诊断 |
| renders 逐步产生 | guide、queue、实际登记媒体分开；不得把 pending 当完成 |
| review 到达 | 进入辅助视图，并显示审阅 scope/source revision |
| 离开/刷新/重新登录 | canonical run deep-link → actor 校验 → episode binding → manifest/view model；本地只恢复非权威 UI 偏好 |

REST 至少 5 秒 polling；响应带 aggregate `manifestRevision` 与每个 artifact 的 revision/mtime/size/source command，支持 ETag/304。解析错误为技术异常并保留最后成功快照，不扩展成业务失败状态。

### → 影响范围

episode query hook、cache key/ETag、poll lifecycle、selection reducer、error boundary、reentry loader。

### → 风险

mtime 单独不足以识别替换；大文件重复读取成本高；当前 SSE writer event 不完整。

### → 验收方式

用多 revision fixture 依次到达 outline/script/storyboard/prompts/renders/review；刷新与重新进入返回相同 binding/revisions；ETag 未变时 304；SSE 缺失时 REST 仍恢复；选择与焦点不跳动。

## 9. P6 API 与聚合合同

### 问题

现有 run/files/surface 是否足够；如何安全聚合 episode 目录、校验绑定、处理缺失和增量读取。

### → 现状证据

- 当前 `/dream-files` 只返回固定三 stage，无法表达目录 artifact、关联诊断或 episode identity（`backend/story_workspace/contracts.py:563-735`）。
- Dream source reader 已做可信根目录、相对路径、符号链接和 `O_NOFOLLOW` 防护（`dream_file_service.py:1076-1160`）。
- gateway 先按 actor/workspace/run/thread 授权再探测文件（`story_workflow_gateway.py:1214-1287`）；测试覆盖其他 actor、缺失、symlink 和逃逸（`backend/tests/test_story_workspace_dream_api.py:640-783`）。
- 更严格 reentry 查询还联合校验 workspace/preflight/binding/release/runtime lock/snapshot/deck/thread/source provenance（`backend/services/story_workspace/dream_reentry_service.py:111-183`）。

### → 根因

stage aggregate 的领域是宿主投影，不适合塞入任意 episode 目录；现有没有目录 allowlist、文件上限、媒体受控 URL、episode 绑定或关联覆盖合同。

### → 可选方案

1. 扩展 `/dream-files` 返回所有文件：混淆领域且放大路径攻击面。
2. 前端调用通用 files API 自行拼路径：不可接受。
3. **在既有 Story Workspace contract owner 下增加 actor-scoped Episode Artifact Surface，由受控 binding 解析 allowlisted canonical 文件并返回有界 manifest + normalized view model。**

### → 最终决策

采用方案 3。

建议合同：

- `GET /api/story-workspace/workflow-runs/{run_id}/episode-artifacts`：默认返回该 run 唯一 binding 的 manifest、outline/scene/shot 索引、association metrics、review summary 和下一步 capability；支持 `If-None-Match`。
- prompts/renders 目录采用有界分页清单，`limit <= 100`、opaque cursor；当前页可包含受大小上限约束的文本 prompt 摘要。不得返回绝对路径。
- 实际 render 媒体只通过受控资源 endpoint/短期 URL，校验 MIME、size、range、episode binding 和 actor；不把任意相对路径交给前端。
- allowlist：精确文件名 `episode-outline.md`、`script.md`、`storyboard.yaml`、`review-report.md`；目录 `prompts/` 和 `renders/` 只允许批准扩展名。目录和文件逐层 `lstat/open`，拒绝 symlink、`..`、NUL、跨根目录和超限文件。
- 授权顺序：actor → workspace owner → frozen run provenance/creator → Deck binding/owner → thread owner → `episode.json` 与 run 一致 → canonical episode root containment，然后才读取。
- Markdown 解析为受控 section AST/text；YAML 使用 safe loader、schema/数量/深度/字符串长度上限；前端默认纯文本或安全 renderer。
- 缺失 artifact 返回 `availability: "not_generated"`，HTTP 200；解析失败返回 artifact 级 technical diagnostic 并保留其他可用 artifact，不虚构内容。
- revision 使用内容摘要构成的 opaque token，并附 mtime/size；aggregate token 形成 ETag。writer event 不完整期间持续 REST polling。

### → 影响范围

Story Workspace backend contracts/service/router/tests；受控 writer；frontend contracts/hook/adapter；媒体响应与 CSP。

### → 风险

aggregate payload 可增长；Markdown parser 对自由格式兼容有限；render 媒体 endpoint 需要明确缓存和 Range 语义。

### → 验收方式

actor/Deck/run/story/episode 交叉越权矩阵全部拒绝；路径穿越/symlink/超限/错误扩展被拒绝；缺失返回 not_generated；ETag/分页稳定；API 不泄漏绝对路径、凭证、原始工具参数。

## 10. P7 本期边界

### 问题

哪些能力明确不进入本期，避免以技术异常或 vendor 后续命令扩张业务状态机。

### → 现状证据

- 当前设计明确 Dream 不是 Chat 页面、隐藏 thread 仅是技术事实（`docs/architecture/术语表.md:47-52`；`design_008_dream-reentry-and-agent-workbench.md:631-737`）。
- canonical 设计排除视频制作和无证据的新失败/驳回/重试/归档流程（`design_004_story-workspace-dream-surface-execution-page.md:65-73,419-448`）。

### → 根因

vendor 全流水线包含 voice/edit/promote，历史设计还残留 reject/retry；若不明确边界，会把本期 artifact workbench 变成通用 Agent/视频后台。

### → 可选方案

1. 顺手实现全部 vendor 命令和历史状态：范围失控。
2. **只实现第一集文本/分镜/prompt/render-guide/已登记 render/review 的可读、可恢复工作面和受控下一步。**

### → 最终决策

采用方案 2。本期不做：

- 将 Dream 或 Execution 改成通用 Chat 页面，或直接挂载 `ChatView`；
- 展示模型隐藏推理、原始工具参数、命令、凭证、敏感路径和调试事件；
- 画布式无限编辑器；
- 视频剪辑、视频制作、voice/edit/promote 操作；
- 与当前 Dream run 无关的通用 Agent 中心；
- 仅依赖 localStorage 恢复 run、episode 或 artifact；
- 没有 vendor/产品证据的业务失败、驳回、人工重试或归档流程；
- 前端直接编辑 canonical Markdown/YAML；
- 用 mock 冒充外部模型或 renderer 的真实成功。

### → 影响范围

任务二非目标、页面文案、capability resolver、E2E 报告和诚实遗留表。

### → 风险

用户可能期待真实视频预览；应明确区分 render guide、pending queue 与已注册媒体。

### → 验收方式

源码扫描、运行时 DOM 和浏览器网络检查均不出现上述能力；技术异常只显示可恢复提示，不产生新业务状态。

## 11. 唯一推荐方案

唯一推荐方案是：**保留 `.dream` 三 stage 作为 Dream 初稿投影，以同一 Dream Agent/run/thread 继续 vendor 的 episode 顺序；新增 run-scoped episode binding 和 actor-scoped Episode Artifact Surface；以 canonical episode 文件为唯一内容 owner；用显式 SC/SNN/shot_id 和不透明 view ID 建立可证明关联；Execution 使用故事线 master-detail + 上下文 shot inspector，Prompt/Render/Review 为辅助层；进度完全由后端 binding、artifact 存在性和 revision 推导。**

该方案同时满足：不改变 Dream 的独立产品身份、不开放任意文件、不引入业务状态机、不依赖浏览器恢复、不让消息或 UI 成为 artifact owner，并允许 legacy partial run 诚实展示。

## 12. 任务二仍需设计验证的风险

1. **workflow 顺序迁移**：新 run 必须按 vendor 顺序；legacy run 已先有 storyboard，交互上如何解释而不制造状态，需要线框验证。
2. **outline 自由格式**：真实样例不含 SC 段，模板却包含；空叙事点导航的可理解性需验证。
3. **review 单文件多范围**：script review 与 full-chain review 共用路径，设计需显示 scope/source revision，并避免以存在性推断。
4. **supplemental shot**：14/45 无可证明 script scene；“尚未关联”在主工作流中的密度和定位需验证。
5. **detail 信息密度**：八层 shot + script + prompt + render 在窄屏必须可访问但不能变成后台表格。
6. **受控下一步**：应让用户理解阶段目的，又不能暴露原始 slash command 或技术 thread。
7. **payload 增长**：aggregate 与目录分页边界需要在 API/组件图中明确。
8. **真实外部依赖**：renderer/模型/凭证若阻断，只能报告真实到达阶段；确定性 UI fixture 必须显式标注。

## 13. 任务一验收结论

- 已按 README 还原 12 步完整流水线，并将本期边界裁决至 render guide/已登记 render 展示。
- 已识别 init、storyboard、prompt、hook、render 语义的 vendor 内部漂移。
- 已对真实 EP01 做 shot/prompt/render 关联核验，并记录不可证明的 supplemental shot。
- 已调查现有 Dream files、polling、权限、Execution、reentry 和真实 partial run 的接入差距。
- P1—P7 均已给出唯一最终决策、影响、风险和验收。
- 本轮只新增本实施记录，没有修改生产代码；任务二必须以本记录为输入建立 `design_009`，不得重新引入已排除方案。
