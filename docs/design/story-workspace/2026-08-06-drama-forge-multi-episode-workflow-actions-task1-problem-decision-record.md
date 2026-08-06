# Dream 后续多 Episode 工作流动作补全：任务一问题判定实施记录

> 日期：2026-08-06
>
> 阶段：任务一（只调查与产品裁决）
>
> 结论：通过；本阶段只新增本记录，没有修改生产代码
>
> 上游 owner：`design_009_drama-forge-first-episode-storyline-storyboard-workbench.md`
> 后续输入：任务二必须以本记录的唯一推荐方案为准

## 0. 本轮规划前置器

### 0.1 Optimized Prompt

在不修改生产代码的前提下，以 drama-forge README、命令 Skill、Agent、模板、schema、生成脚本与真实 Episode 产物，以及 Ink-Dream 当前 binding、artifact surface、workflow facts、Continue API、Dream Agent adapter、确认窗口、REST 恢复和现有测试为证据，调查“Outline / 详细分镜生成选项”的准确语义。逐项完成 P1—P6 裁决，建立 EP01、EP02、EP03 动作矩阵，明确可信 EP 编号、动作 truth ownership、当前/推荐/预览/重新生成的区别、revision/idempotency/reentry 身份与唯一推荐方案。所有结论附文件行号或测试输出；不得从前端数组位置、按钮文案、Agent 消息、用户输入路径或 slash command 猜测 Episode 身份。本轮只能新增中文调查记录，不得修改生产代码。

### 0.2 Optional Enhancers

- 将 vendor 的规范合同、历史脚本漂移和 Ink-Dream 当前投影分开记录。
- 将“事实证据”“产品裁决”和“任务二/三待实现合同”分开，避免把设计目标冒充现状。
- 对 action option 同时记录 target Episode、canonical inputs、可派发性、推荐性和禁用原因。
- 用 EP01 → EP02 → EP03 的同一规则证明没有 EP01 字面量或数组下标依赖。

### 0.3 执行计划

1. 记录分支、提交、脏文件、5173/8765 与测试服务基线。
2. 还原 vendor 单集与跨集工作流、产物路径、review scope 和 revision 关系。
3. 追踪当前 EP01 authority/binding、surface、workflow facts、action options、Continue、instruction、幂等与恢复链路。
4. 盘点后端 pytest、前端 Node seam、Playwright/E2E 与交互测试。
5. 完成 P1—P6、动作矩阵、truth ownership 和唯一推荐方案。
6. 只新增本记录并复核工作区。

### 0.4 验收标准

- P1—P6 均具有“问题 → 现状证据 → 根因 → 可选方案 → 最终决策 → 影响范围 → 风险 → 验收方式”。
- 明确“更多工作流操作（5）”的来源和 N 的计算方式。
- 明确 Outline、Dream storyboard 摘要、script、详细 storyboard 和下一 Episode 的边界。
- 给出 EP01、EP02、EP03 的可信身份和动作矩阵。
- 明确是否需要后端合同变更和最终用户可见名称。
- 生产代码零修改；既有服务不关闭；不执行归档。

## 1. 调查基线与证据优先级

### 1.1 工作区安全记录

- 调查开始时分支为 `story-workspace`，HEAD 为 `6506432 feat(story-workspace): link artifact progress to reader`；之前四个提交为 `9391e9e`、`ce2d375`、`1226231`、`1a54396`。命令：`git branch --show-current && git log -5 --oneline --decorate`。
- 调查开始时 `git status --short` 无输出，工作区干净，没有可归属为其他工作线的未提交文件。
- 5173 已由 PID 87690 的既有 Vite 进程监听；8765 已由 PID 82275 的既有 backend `server.py` 进程监听。二者均为调查前已有服务，本轮不重启、不关闭。
- 其他监听服务包括 18789 与 4723；本轮没有操作这些服务。
- 聚焦后端基线：`backend/.venv/bin/pytest -q backend/tests/test_story_workspace_episode_actions.py backend/tests/test_story_workspace_episode_binding.py backend/tests/test_story_workspace_episode_artifacts_api.py`，结果为 `190 passed, 70 subtests passed in 1.92s`。
- 前端 Node seam 共 14 项：13 项通过；`StoryWorkspaceDreamAgentWorkflowActions.test.ts` 在启动 harness 时因 Vite 8 把 `port: 0` 回落到已占用的 5173 而失败，失败发生在 `server.listen()`，尚未进入产品断言。测试产生的 `.last-run.json` 与错误上下文已恢复/删除，工作区重新干净。该环境冲突不是“测试通过”，任务三必须用不占用用户服务的端口修复或隔离后重跑。

### 1.2 证据优先级

冲突时使用以下优先级：

1. 当前 canonical 文件、当前运行代码和严格合同；
2. vendor README 的正式工作流与 canonical 路径；
3. 与 canonical 路径一致的 Skill/Agent/template 语义；
4. 已漂移的旧 Skill 路径和批处理脚本只作为风险证据。

依据：vendor 明确 `stories/` 与 `assets/` 是源文件，缓存和派生产物可重建（`vendor/drama-forge/drama-forge/README.md:459-465`）。当前 storyboard Skill 仍写旧 `scripts/season-*` 与 `storyboards/season-*`（`vendor/drama-forge/drama-forge/.claude/skills/drama-storyboard/SKILL.md:8-16`），而 README 的 canonical Episode 树是 `stories/{project}/episodes/EP??/storyboard.yaml`（`vendor/drama-forge/drama-forge/README.md:83-91`），所以不能把旧路径当作新 API 输入。

## 2. vendor 多 Episode 工作流事实

### 2.1 正式顺序与重复边界

README 的“典型工作流（从零到第一集）”给出：

`init → plan → script → script-reviewer → asset → storyboard → prompt → full-chain review → validate/commit → render+voice → edit → promote`（`vendor/drama-forge/drama-forge/README.md:353-378`）。

README 随后明确：“每集都重复步骤 3-9；角色卡和场景卡首次创建后跨集复用”（`vendor/drama-forge/drama-forge/README.md:381`）。因此：

- `/drama-plan` 是全剧/批次分集规划，产出 master outline 和每集 `episode-outline.md`（`vendor/drama-forge/drama-forge/README.md:99-115`）。
- 每个 Episode 的生产闭环从本集 script 开始，经过 review、asset 引用/补齐、storyboard、prompt、full-chain review 和 validation/commit。
- “开始下一集”不等于跳过当前集的 prompt 或 validation；下一集的 outline 可能已由早期 `/drama-plan` 批次生成，此时下一合法动作应是本集 script，而不是重复创造 outline。

### 2.2 单集命令、输入与产物

| 环节 | 可信输入 | canonical 产物 | 证据 |
| --- | --- | --- | --- |
| Episode outline | project、master outline、世界观、角色与 ledger | `episodes/EP{NN}/episode-outline.md`，批准后才能进入剧本 | `drama-plan/SKILL.md:102-165,194-212` |
| script | 已批准/锁定的本集 outline、角色/场景资产、ledger | `script.md` 与剧本级 `review-report.md` | `drama-script/SKILL.md:55-124` |
| script review | 当前 script revision、outline 与连续性事实 | 同路径 `review-report.md`，scope 为 script | `drama-script/SKILL.md:120-141`；`script-reviewer.md:82-88` |
| assets | project/outline/episodes 中的需求 | 跨集复用的角色、场景、道具卡 | `drama-asset/SKILL.md:37-50,395-432` |
| detailed storyboard | 已批准剧本、定稿角色/场景资产 | 八层详细分镜；canonical 项目使用 `storyboard.yaml` | `README.md:147-159,251-255`；`storyboard-table.md:1-25` |
| prompts | storyboard、角色/场景锚点和 script 情绪上下文 | `prompts/` 下逐 shot Prompt 包 | `README.md:160-171`；`drama-prompt/SKILL.md:42-81` |
| full-chain review | outline、script、storyboard、prompts 当前 revision | 同路径 `review-report.md`，scope 为 full-chain | `README.md:366-372`；当前 adapter 的 scope 判定见 `episode_auxiliary_artifact_adapter.py:1539-1569` |

### 2.3 review-report 的准确语义

`review-report.md` 不是永久代表某一种审查，也不是“整个隐藏工作流完成”的状态。它是每 Episode 的单一审查报告路径：

- `drama-script` 把 script 和 review report 同时列为输出（`vendor/drama-forge/drama-forge/.claude/skills/drama-script/SKILL.md:15-25`）。
- `script-reviewer` 规定每集报告固定写入 `episodes/EP{NN}/review-report.md`（`vendor/drama-forge/drama-forge/.claude/agents/script-reviewer.md:82-88`）。
- 模板可以列 script、storyboard、prompts 等 reviewed files（`vendor/drama-forge/drama-forge/.claude/docs/templates/review-report.md:12-29`）。
- 当前 adapter 优先读显式 `scope: script|full-chain`；无 scope 时只有 reviewed artifacts 恰好证明 script 或完整链路才推导，否则为 `unknown`（`backend/services/story_workspace/episode_auxiliary_artifact_adapter.py:1539-1569`）。

结论：报告 scope 与它引用的 source revisions 共同决定它是否仍适用于当前上游；文件存在本身不等于审查完成。

### 2.4 真实 Episode 产物与 revision 关系

- EP01 outline 状态为 approved，但示例正文声明它由 script 投影，说明样例存在历史漂移，不能据此反转规范依赖（`vendor/drama-forge/drama-forge/stories/didi-zhengzhou/episodes/EP01/episode-outline.md:1-20`）。
- EP01 script 为 `status: draft`、`version: 5`（`.../EP01/script.md:1-23`）。
- EP01 detailed storyboard 为 `episode: EP01`，并声明 `generated_from: script@v1`（`.../EP01/storyboard.yaml:1-10`）。
- EP17/EP28 storyboard 分别声明 `script@v4`、`script@v5`，证明 `generated_from` 是每 Episode 的上游版本关系，不是全局 EP01 常量（`.../EP17/storyboard.yaml:1-8`；`.../EP28/storyboard.yaml:1-8`）。
- Prompt 包逐 shot 使用同一 Episode 的 shot ID（`.../EP01/prompts/ep001-prompts.yml:1-17`），README 又要求同一 Episode 内统一 prompt tool（`vendor/drama-forge/drama-forge/README.md:467-469`）。
- EP01 report 只 reviewed `script.md`，结果为 `CONDITIONAL_APPROVAL`，不能冒充 full-chain APPROVED（`.../EP01/review-report.md:1-12,30-46`）。

### 2.5 vendor 实现漂移风险

- `generate_storyboards.py` 使用参数化 `EP{ep_num}` 读取 script 和写 storyboard，并把 script version 写进 `generated_from`（`vendor/drama-forge/drama-forge/scripts/generate_storyboards.py:18-65,125-136`）；这证明 EP 号是显式输入，但该脚本主循环写死 EP31—40（同文件 `:167-179`），不能直接成为通用后端合同。
- `generate_prompts.py` 从 `episodes/EP{ep_num}/storyboard.yaml` 生成 `prompts/ep{NNN}-prompts.yml`（`vendor/drama-forge/drama-forge/scripts/generate_prompts.py:268-287,313-344`），但项目 slug 又写死为 didi-zhengzhou（同文件 `:15-17`）。
- `drama-storyboard` 与 `drama-prompt` Skill 的旧目录和 README canonical 路径不一致（`drama-storyboard/SKILL.md:8-16`；`drama-prompt/SKILL.md:11-19`）。

裁决：产品动作忠实采用 vendor 命令语义和 canonical Episode 产物，不调用这些历史批处理脚本拼路径，也不把它们的硬编码范围投影到浏览器。

## 3. 当前 Story Workspace 合同事实

### 3.1 EP01 身份被全链路写死

当前不是“已有通用多 Episode 合同但 UI 漏按钮”，而是 EP01 专项合同：

- `StoryWorkspaceEpisodeBindingFile.episode_code` 是 `Literal["EP01"]`，validator 也固定 EP01 root（`backend/story_workspace/contracts.py:1174-1193`）。
- binding service 固定检查 `stories/{slug}/episodes/EP01`，创建 binding 时写 `episode_code="EP01"` 与 EP01 root（`backend/services/story_workspace/episode_binding_service.py:314-320,703-732`）。
- launch authority parser 只接受 `episode_code == "EP01"`（`backend/services/story_workspace/episode_artifact_service.py:118-165`）。
- writer tool 首次 authority 与 binding 都写 EP01（`backend/libs/claude_agent_kit/server/story_workspace_tool.py:463-508`）。
- surface 只返回 `opaqueEpisodeId`，没有 Episode display label/code（`backend/story_workspace/contracts.py:2006-2034`；`frontend/src/hooks/story-workspace/contracts.ts:826-840`）。
- Execution route 只传 run ID；页面虽有 `episodeId?` prop，但该 prop只用于 review deep-link，不参与 artifact query/action target（`frontend/src/router/story-workspace.tsx:184-191`；`StoryWorkspaceExecutionPage.tsx:478-505,734-737`）。

### 3.2 workflow facts、manifest 和 action options

- manifest entry 拥有 relative key、availability、content revision、producer 与 consumers（`backend/story_workspace/contracts.py:1214-1233`）。
- workflow fact file 以 run + opaque episode UID 为身份，保存每个 action 的 input revision、manifest revision、message id 与技术 revision（同文件 `:895-931`）。
- action input revision 按 action 哈希 canonical artifact revisions；storyboard 输入是当前 script + review，以及 refresh_assets completion（`backend/services/story_workspace/episode_action_service.py:503-558`）。
- resolver 根据 artifact availability、review scope/source revisions 和 completion facts 推导唯一 next action（同文件 `:635-856`）。
- action options 是从唯一 next action 开始的 vendor 步骤后缀；只有第一项 `isCurrent`，也只有第一项可能 `canDispatch`（同文件 `:607-632`；对应 Pydantic 约束 `backend/story_workspace/contracts.py:962-1032`）。

### 3.3 “更多工作流操作（5）”为何是 5

来源链如下：

1. 后端 `_action_options` 从当前 next action 起返回剩余步骤后缀（`episode_action_service.py:607-632`）。
2. Execution 不生成业务动作，只把后端 options 映射为 dialog view model（`frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx:900-933`）。
3. Dialog 无条件取前两项为 direct，其余为 overflow（`frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx:40-47`）。
4. 展开按钮直接显示 `workflowActionGroups.overflow.length`（同文件 `:303-327`）。

所以“更多工作流操作（5）”严格表示“服务端当前返回 7 项，默认显示 2 项，折叠 5 项”，不是固定文案，也不是系统总共有 5 个动作。当前后端测试证明初始状态可返回 9 项，outline 到达后返回 8 项（`backend/tests/test_story_workspace_episode_actions.py:427-487`）；交互 seam 证明 4 项会切成 2 direct + 2 overflow（`frontend/src/components/story-workspace/dream/__tests__/StoryWorkspaceDreamAgentWorkflowActions.test.ts:120-143,172-177`）。

### 3.4 Continue、allowlist、幂等和恢复

- Continue body 当前接受 opaque `episodeId`、action enum、idempotency key 与受限用户 guidance；guidance 明确拒绝 slash command、路径、凭证和内部协议（`backend/story_workspace/contracts.py:1045-1146`）。
- 服务端重新比较 ETag、surface episode UID、workflow facts episode UID 和 resolver 当前唯一 action，任何不一致拒绝（`backend/services/story_workspace/episode_action_service.py:1269-1358`）。
- actor/workspace/run/thread/Deck/binding/runtime snapshot 的关系在文件探测前验证（`backend/services/deck/story_workflow_gateway.py:1447-1481`）。
- idempotency provenance 当前包含 action、episode UID、input/facts/manifest/workflow revisions（`episode_action_service.py:1040-1178`）。
- 前端 idempotency key 仅在同一挂载会话的 run + fact + action 身份内复用，不使用 localStorage（`StoryWorkspaceExecutionPage.tsx:113-139,500-552`）。
- REST hook 使用 run-scoped ETag、AbortController、generation 和晚响应门禁；ETag 与 last-good 仅保存在挂载实例（`frontend/src/hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts.ts:310-370,672-675`）。
- writer event 只使 REST query 失效；事件内容不成为 workflow truth（同文件 `:270-279`）。

### 3.5 当前前端仍复制 EP01 文案/命令

- 浏览器 contract 中复制了一份 EP01 display command 常量，并严格要求服务端值与它相等（`frontend/src/hooks/story-workspace/contracts.ts:497-507,1473-1479`）。
- 后端 label/display command 也写死“第一集”和 `(EP01)`（`backend/services/story_workspace/episode_action_service.py:91-115`）。
- public workflow instruction、recover/continue 文本和 heading 均写“第一集”（`backend/services/story_workspace/episode_workflow_instruction.py:57-115,226-239`；`episode_action_service.py:1180-1227`；`StoryWorkspaceDreamAgentDialog.tsx:303-320`）。
- Episode artifact reader 也显示 `EP01 · Canonical artifacts`（`frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeArtifactReader.tsx:268`）。

这组证据直接否定“只在 dialog 里再加两个按钮”的方案。

## 4. P1：EP 编号来源

### 问题

当前/下一 Episode 的 EP 编号由谁提供；前端消费什么；后端如何从可信绑定得到 EP01、EP02、EP03。

### → 现状证据

- 当前 launch metadata + run-scoped `episode.json` 同时锁定 run/story/opaque UID/EP01（`backend/services/story_workspace/episode_artifact_service.py:118-165`；`backend/story_workspace/contracts.py:1174-1193`）。
- surface 不公开 display EP code（`backend/story_workspace/contracts.py:2006-2034`）。
- 前端命令/label 写死 EP01（`frontend/src/hooks/story-workspace/contracts.ts:497-507`；`backend/services/story_workspace/episode_action_service.py:91-115`）。
- gateway 在关系授权后才读取绑定和文件（`backend/services/deck/story_workflow_gateway.py:1503-1564`）。

### → 根因

design_009 的 v1 明确只支持“一个 run 绑定第一集”；EP code 的安全策略被实现成 `Literal[EP01]`。该策略在第一集专项中正确，但没有可扩展的 Episode registry、active Episode 或 server display identity。

### → 可选方案

1. 前端从 URL、数组位置或已返回列表的 index 计算 EP02：身份可伪造，拒绝。
2. Continue 接受任意 `EPxx` 或 episode path：扩大路径/命令攻击面，拒绝。
3. 由服务端在已授权 run/story 下维护 revisioned Episode binding registry；浏览器只消费 opaque Episode ID、server display label 和 opaque action ID。

### → 最终决策

采用方案 3。

- Episode binding registry 是 EP 身份 owner。每项保存 server-generated `episode_uid`、受校验正整数 `episode_number`、由服务端格式化的 `episode_code/display_label` 与 canonical root；root 永不返回浏览器。
- 旧 `dream-episode/v1` EP01 binding 迁移/兼容读为 registry 的第一个成员；不得建立第二份 EP01 truth。
- 当前 Episode 是 registry 中服务端持久化/推导的 active work Episode，不由前端 URL 或 selection 决定。
- 下一 Episode number 只可由“同一 run/story 的已绑定 contiguous number + 项目 total episodes 上限”得到；创建时由服务端 CAS，不能由用户提交。
- 浏览器 action request 改为只发送 server-issued opaque `actionId`、idempotency key 与安全 guidance。服务端用当前 run/Deck/story binding、Episode registry revision、workflow facts 和 manifest 重新生成 allowlist，并按 exact actionId 命中目标。
- 前端可显示 `targetEpisode.displayLabel`，但不得解析该 label 构造命令、路径或业务身份。

### → 影响范围

Episode binding/authority contract、artifact surface、workflow projection、Continue request、MCP writer/completion、gateway、frontend parser/view model、confirmation 和测试；需要后端合同变更，但不需要修改 `backend/database.py`。

### → 风险

legacy EP01 migration、并发创建 EP02 的单 winner、项目 total episodes 缺失、旧 source metadata 仍是 EP01 authority。

### → 验收方式

EP01/02/03 的 opaque IDs 与 display labels 均不同；同一 next Episode 并发创建只有一个 binding；篡改 run/Deck/story/episode/actionId 在文件探测或 Agent 派发前拒绝；前端源码无 EP 编号格式化和 slash command 拼接。

## 5. P2：Outline 与分镜语义

### 问题

“Outline 分镜生成选项”究竟是当前 Episode 更新、下一 Episode 创建、vendor action 漏投影，还是组合。

### → 现状证据

- Episode outline 是 `/drama-plan` 的逐集产物（`README.md:99-115`；`drama-plan/SKILL.md:102-165`）。
- Dream 初稿 `storyboards.json` 只是 `.dream` 三阶段之一，每项只有 display name、summary、source file 和 relations（`backend/story_workspace/contracts.py:662-711`）；它不是八层 `storyboard.yaml`。
- detailed storyboard 的 template 明确八层结构、EP code 和 `generated_from: script@revision`（`storyboard-table.md:14-38,77-89`）。
- vendor storyboard 依赖 approved script 与定稿资产，不负责 Prompt（`drama-storyboard/SKILL.md:1-20,37-71`）。
- Prompt 直接消费 storyboard（`README.md:160-171`；`drama-prompt/SKILL.md:42-81`）。

### → 根因

中文需求把 Outline 与“分镜”并列，而当前产品中又同时存在 Dream storyboard 摘要、Episode outline 和 detailed storyboard 三种表面；若仅按按钮名理解，会虚构一个 vendor 不存在的“Outline 分镜”状态。

### → 可选方案

1. 新增名为“Outline 分镜”的复合状态/文件：vendor 不存在，拒绝。
2. 把下一 Episode storyboard 与 outline 一键生成：绕过 script review 与 asset 依赖，拒绝。
3. 把需求拆为两个 vendor 已存在的受控能力，并保留当前 Episode Prompt 的优先级。

### → 最终决策

采用方案 3；最终业务定义是以下组合：

1. **当前 Episode 详细分镜更新**：当当前 Episode 有 approved/current script review 且资产 completion 对当前 script/review 仍有效时，允许“基于最新剧本更新 EPxx 详细分镜”。它执行 `/drama-storyboard (EPxx)` 的 server-owned template，输入是当前 script/review/assets revisions；不是 Dream 摘要，也不是从 outline 直接生成。
2. **下一 Episode 分集规划/继续**：当前 Episode 完成 full-chain review 和 validation/commit 后，服务端检查下一 Episode binding/artifacts。若 outline 缺失，动作名为“开始 EP(next) 分集规划”；若 outline 已 approved/current，则直接推荐“创作 EP(next) 剧本”，不得重复伪装为新 outline。
3. **当前 Episode Prompt 包优先**：当前 detailed storyboard 已 current 而 Prompt 缺失/陈旧时，推荐动作必须是“生成 EPxx Prompt 包”；分镜更新作为可执行但会使下游 revisions 失效的重新生成动作，不能把下一 Episode 提前为推荐。

最终用户可见名称不使用“Outline 分镜生成”这一含糊总称。使用：

- `基于最新剧本更新 EPxx 详细分镜`
- `生成 EPxx Prompt 包`
- `开始 EP(next) 分集规划`（仅 outline 确实缺失时）

### → 影响范围

action labels/descriptions、target Episode DTO、disabled reason、canonical inputs、confirmation consequence copy 和 instruction template。

### → 风险

更新已验证 Episode 的 storyboard 会使 prompts/full-chain review/validation 变陈旧；必须在确认窗口明确展示影响，不得以旧完成事实继续。

### → 验收方式

UI 无单独“生成分镜”或“Outline 分镜”含糊按钮；每个动作显示目标 EP；下一 EP storyboard 在 script/review/assets 未完成时只能是带真实原因的 preview，不能点击。

## 6. P3：工作流顺序和依赖

### 问题

每个 EP 的合法顺序、review-report scope、Prompt/下一 Episode 优先级、重新生成和确认边界。

### → 现状证据

- vendor 完整顺序和每集步骤 3—9 重复见 `README.md:353-381`。
- 当前 resolver 已按 artifact/review/completion revision 推进，而不只看文件存在（`episode_action_service.py:719-835`）。
- storyboard input revision 包含 script、review 和 refresh_assets completion；Prompt input revision 是 storyboard（同文件 `:513-558`）。
- 当前 Continue 每次只授权一个 action，完成后停止并等待服务端重算（`backend/services/story_workspace/episode_workflow_instruction.py:289-299`）。

### → 根因

当前 resolver 是单一路径“唯一 next action + 未来步骤预览”；它不能同时表达推荐 Prompt、可选分镜重生成和下一 Episode preview，也不能承载跨 Episode target。

### → 可选方案

1. 所有可见动作都可执行：会把未来 preview 当按钮，拒绝。
2. 仍只允许唯一 current action：无法提供合法 re-generation 与 next Episode choice，拒绝。
3. 保留唯一 `recommendedActionId`，同时让后端 action options 表达其他合法可执行 action 与 blocked preview。

### → 最终决策

采用方案 3。

每个 Episode 的真实顺序是：

`Episode outline → script → script-scoped review → assets current → detailed storyboard → prompts → full-chain review → validation/commit`。

规则：

- `review-report.md` 以 scope + reviewed source revisions 判断 script 或 full-chain，不创建第二个报告状态。
- 当前 script revision 未获 APPROVED script/full-chain review 时，storyboard 不能派发。
- assets completion 必须针对当前 script/review input；跨集复用资产不等于跳过本集依赖核对。
- storyboard 更新后，旧 Prompt/full-chain review/validation completion 由 input revision 自动变 stale。
- Prompt 缺失/陈旧时优先于下一 Episode。
- 下一 Episode 只有当前 Episode validation/commit current 后才可执行；在此之前可以 preview，但必须 disabled 并说明“完成 EPxx 完整产物校验后可用”。
- 所有会覆盖或使下游变 stale 的重新生成动作必须打开 Episode confirmation。
- 后续 Episode 继续使用同一 Dream Agent、同一 workflow run 和隐藏 thread；Episode binding/facts 分集隔离，Agent 消息不拥有 action 状态。

### → 影响范围

resolver、workflow facts schema、action option eligibility、instruction target、confirmation 和 reentry。

### → 风险

vendor `/drama-plan` 可批量提前生成多个 outlines；因此“下一 Episode”必须先读文件事实，不能假定 outline 缺失。旧 full-chain report 覆盖 script report 后也必须靠 scope/revisions 判断。

### → 验收方式

构造每个依赖缺失/陈旧的 fixtures；证明 Prompt 推荐顺序、storyboard re-generation 下游失效、next Episode validation gate、scope/revision gate 和同一 run/thread。

## 7. P4：“更多工作流操作”动作模型

### 问题

action options 为何是 5；当前、推荐、未来和重新生成如何区分；谁生成、N 如何计算。

### → 现状证据

- 后端生成 action options 后缀（`episode_action_service.py:607-632`）。
- 前端只映射后端值，但本地补了统一的未来 disabled reason（`StoryWorkspaceExecutionPage.tsx:919-932`）。
- Dialog 默认前二、其余折叠，N 等于 overflow length（`StoryWorkspaceDreamAgentDialog.tsx:40-47,303-327`）。
- 当前 contract 强制只有第一项 current/canDispatch（`backend/story_workspace/contracts.py:962-1032`）。

### → 根因

现有 option 只表达线性导航；`isCurrent` 同时承担“推荐”“合法”“排第一”三种语义，无法表达多 Episode 和 re-generation alternative。disabled reason 又由前端统一写成“完成当前步骤后可用”，会掩盖真实依赖。

### → 可选方案

1. 前端根据 artifacts 自行追加/排序动作：形成第二 workflow owner，拒绝。
2. 后端只返回可执行项，未来完全不显示：无法解释链路，但可行性不足。
3. 后端返回完整、受控、带状态的 options；前端仅展示、折叠和提交 opaque actionId。

### → 最终决策

采用方案 3。任务二/三的新 option 最少包含：

```text
actionId             server-issued opaque stable ID
kind                 allowlisted product capability
targetEpisode        opaqueEpisodeId? + displayLabel + relation(current|next)
label                明确 EP 的用户动作名
description          目的、影响和依赖摘要
displayCommand       server-authored vendor product entry
availability         executable | preview | blocked
isRecommended        唯一推荐项
canDispatch          服务端当前可派发事实
disabledReason       server-authored；可派发时为 null
canonicalInputs[]    action-specific relative label + availability + revision
consequences[]       会变 stale 的下游公共名称
```

- workflow facts/resolver 拥有 `recommendedActionId`、ordered options 和可执行性。
- `isRecommended` 与 `canDispatch` 分离；可存在一个推荐项和一个合法 re-generation alternative。
- preview/blocked 必须 disabled；不能因排在 direct 前二就可点击。
- 后端按相关性排序；前端始终 `direct = first 2`、`overflow = rest`。
- `N = max(actionOptions.length - 2, 0)`；N 只数折叠项，展开/折叠不改变 N。
- 前端只可附加瞬时 UI 原因（Agent busy、本次提交中）；canonical disabledReason 必须由服务端提供，不能统一猜测。

### → 影响范围

Pydantic/TS contracts、parser、resolver、Execution adapter、Dialog view model、a11y tests。

### → 风险

option 数量过多；同 kind 跨 Episode 重复；旧 action enum 被当 React key。opaque actionId 和最多 current+next 两个 Episode 的范围可控制复杂度。

### → 验收方式

7 options 显示 2 direct + “更多（5）”；同 kind 的 EP01/EP02 option 使用不同 actionId；blocked preview 不可点击且 reason 可见；Escape 收起 overflow 并把焦点还给 disclosure。

## 8. P5：多 Episode 扩展

### 问题

EP01、EP02、EP03 如何保持动作、binding、revision、idempotency 和恢复身份不混淆。

### → 现状证据

- vendor 真实目录跨多个 EP 使用相同 artifact 名，并由目录 EP code 和文件 frontmatter 区分（例如 EP10/17/28 的 outline/script/storyboard/report）。
- 当前 workflow facts 只以 run + episode UID 绑定（`backend/story_workspace/contracts.py:911-931`），但物理文件名固定 `episode-workflow.json`（`episode_action_service.py:180-280`），同一 run 无法同时保存多 Episode facts。
- idempotency provenance 已包含 episode UID 和 revisions（`episode_action_service.py:1101-1113`），但前端 identity 仍只有 run + aggregate fact + action enum（`StoryWorkspaceExecutionPage.tsx:119-139,549-552`）。

### → 根因

v1 的“一个 run 一个 Episode”使单文件 facts、单 active surface 和 action enum 足够；多 Episode 后同 kind 会重复，action enum 不能再充当 option identity。

### → 可选方案

1. 每个 Episode 新建 run/thread：丢失同一 Dream 连续上下文，拒绝。
2. 在 action ID 中放 episode path/code：可猜测路径，拒绝。
3. 同一 run/thread，binding registry + per-episode facts + opaque action ID + server target descriptor。

### → 最终决策

采用方案 3。

#### EP01—EP03 动作矩阵

| active Episode | 事实快照 | recommended | 可执行 alternative | next preview | 关键约束 |
| --- | --- | --- | --- | --- | --- |
| EP01 | script APPROVED；assets current；storyboard current；Prompt 缺失 | 生成 EP01 Prompt 包 | 基于最新剧本更新 EP01 详细分镜 | 开始 EP02 分集规划（disabled） | Prompt 优先；更新分镜会使后续 stale |
| EP01 | full-chain APPROVED；validation current | 若 EP02 outline 缺失：开始 EP02 分集规划；若已存在：创作 EP02 剧本 | 基于最新剧本更新 EP01 详细分镜 | EP02 后续步骤依赖式 preview | 服务端 CAS 建立/复用 EP02 binding |
| EP02 | outline current；script 缺失 | 创作 EP02 剧本 | 无不满足依赖的伪动作 | EP03 分集规划（disabled） | label/command 必须是 EP02，不复用 EP01 字面量 |
| EP02 | storyboard current；Prompt 缺失 | 生成 EP02 Prompt 包 | 基于最新剧本更新 EP02 详细分镜 | EP03 分集规划（disabled） | EP02 revisions 与 EP01 facts 隔离 |
| EP02 | validation current | 若 EP03 outline 缺失：开始 EP03 分集规划；若已存在：创作 EP03 剧本 | 基于最新剧本更新 EP02 详细分镜 | EP03 后续步骤 | 服务端 CAS 建立/复用 EP03 binding |
| EP03 | script/review/assets current；storyboard 缺失或 stale | 生成/更新 EP03 详细分镜 | 依事实决定 | EP04 仅在项目范围内 preview | 不从数组 index 推导 `03` |

#### 身份规则

- `actionId` 不包含 path、story slug 或可执行命令；同 kind + 不同 target/revision 得到不同 opaque ID。
- `displayLabel` 与 `displayCommand` 由 target binding 的 server episode code 格式化。
- workflow facts 物理/逻辑分区包含 episode UID；不能让 EP02 completion 覆盖 EP01。
- idempotency identity 至少包含 actor、Deck、run、story authority、target episode UID（或 server next candidate identity）、actionId、input revision、facts revision 和 aggregate ETag。
- accepted/pending action 必须投影回 workflow facts 的技术 dispatch 状态，刷新后由 REST 恢复；浏览器本地 pending 只能加速当前挂载体验。
- revision 到达或 facts revision 前进后，旧 pending/late response 不能覆盖新 option snapshot。

### → 影响范围

binding/facts 文件布局、workflow projection ETag、pending claim、idempotency、REST parser/reducer 和 real E2E fixtures。

### → 风险

同一 run 中并发推进两个 Episode、EP02 outline 已由早期 plan 生成但未绑定、项目总集数边界、legacy 单 facts 文件迁移。

### → 验收方式

EP01/02/03 表驱动测试；并发/重复 key/不同 key；刷新和重入；错 run/Deck/story/episode/actionId；late REST response generation gate。

## 9. P6：Truth ownership

### 问题

workflow、Episode identity、artifact、正文、Agent messages 和前端局部状态分别由谁拥有。

### → 现状证据

- 当前 workflow projection 声明是 derived navigation，不拥有 creative content（`episode_action_service.py:635-640`）。
- workflow file docstring 明确只保存 revisioned evidence（`backend/story_workspace/contracts.py:911-924`）。
- manifest entry 记录 availability/revision/producer/consumer（同文件 `:1214-1233`）。
- Dream Agent activity contract 只允许过滤后的公共摘要（同文件 `:329-340`）。
- REST events 只失效查询，不承载 facts（`useStoryWorkspaceEpisodeArtifacts.ts:270-279`）。

### → 根因

多 Episode 使 label、pending 和 action alternatives 增多；若让前端 template、Agent message 或文件存在性各自推导 workflow，会产生多个 owner。

### → 可选方案

1. 前端结合文件和消息推导：拒绝。
2. Agent 消息标记完成并驱动按钮：拒绝。
3. 按身份、availability、content 与 workflow technical facts 分层单一 owner。

### → 最终决策

采用方案 3。

```text
Authorized run/Deck/story provenance
  └─ Episode binding registry
       owns: opaque Episode identity, episode number/code, active/next relation

Canonical Episode files
  └─ own: outline/script/storyboard/prompts/review actual content

Episode artifact manifest
  └─ owns: per-artifact availability, content revision, producer/consumers

Episode workflow facts + resolver
  └─ own: recommended/executable/blocked action options,
          action input revision, technical completion and durable dispatch state

Dream Agent messages
  └─ own: user-visible process/result summaries only

Frontend local state
  └─ owns: dialog open, overflow expanded, selected item,
          confirmation guidance draft, focus restoration and mounted request generation
```

按钮 label/template 只消费 server action option；artifact 文件不写 workflow state；Agent message 不把“已发送/处理完成”变成 action completion；localStorage 不参与。

### → 影响范围

contract docstrings、adapter boundaries、pending recovery、frontend reducer 和 tests。

### → 风险

当前 pending claim 存在 `chat_message.metadata` 中；任务三若继续使用它作为持久协调记录，必须由 workflow service 安全投影为技术 dispatch fact，不能让可见消息内容成为 owner。

### → 验收方式

删除/缺失 writer event 后 REST 仍恢复；伪造 Agent 文本“已完成 EP02”不改变 options；刷新清空前端状态后 target Episode、pending 和 disabled reason 仍由服务端出现。

## 10. 唯一推荐方案

### 10.1 推荐方案摘要

实施“同一 Dream Agent/run/thread 下的 server-owned multi-Episode action projection”：

1. 将单 EP01 binding 安全演进为 revisioned Episode registry，兼容旧 v1；后端拥有 EP code，前端只见 opaque ID + display label。
2. 将 workflow facts 按 Episode 隔离，并在 run-level resolver 中生成当前 Episode、合法 re-generation 与下一 Episode preview/action。
3. action option 使用 opaque `actionId`，明确 target Episode、description、availability、recommended、disabledReason、action-specific canonical inputs 和 consequences。
4. Continue body 不再让前端提交 action enum + episode ID 组合；只提交 actionId、idempotency key 和安全 guidance，后端按最新 authority/binding/facts/manifest exact allowlist revalidate。
5. 当前 storyboard current 而 Prompt 缺失时优先“生成 EPxx Prompt 包”；“基于最新剧本更新 EPxx 详细分镜”是需确认的合法 alternative；当前 Episode validation current 后才允许开始下一 Episode。
6. 下一 Episode outline 若已由 `/drama-plan` 生成，直接推荐该 Episode 的 script，不制造重复 outline。
7. UI 仍默认最多显示两个 server-ordered relevant options，其余折叠；N 等于实际 overflow 数量。
8. REST facts/revisions 是刷新和重入 owner；不挂载 ChatView，不暴露路径、命令参数、内部 completion 协议或凭证。

### 10.2 是否需要后端合同变更

**需要，而且是必要条件。** 至少涉及：

- `StoryWorkspaceEpisodeBindingFile` 从 EP01 literal 演进为多 Episode registry/entry；
- source authority 与 gateway 的 target Episode 验证；
- artifact surface 增加 active/target Episode display facts；
- workflow facts per-Episode 隔离和 run-level action projection；
- action option DTO 增加 actionId/target/description/state/disabledReason/canonicalInputs/consequences；
- Continue request 改为 opaque actionId；
- instruction/template 按可信 target binding 生成 EPxx；
- completion tool 校验 target Episode/action claim；
- aggregate ETag/idempotency/pending recovery 纳入 Episode facts。

不需要新 DDL，也不应修改 `backend/database.py`；可沿用 run-authorized workspace file protocol、现有 chat coordinator 与关系授权边界。

### 10.3 最终用户可见名称

不存在一个名为“Outline 分镜生成”的 vendor 状态或按钮。最终使用三个明确名称：

- **基于最新剧本更新 EPxx 详细分镜**
- **生成 EPxx Prompt 包**
- **开始 EP(next) 分集规划**

其中第三项只在下一 Episode outline 确实缺失且当前 Episode 已 validation current 时可执行；否则显示真实 disabled reason 或替换为下一 Episode 的实际 next action。

## 11. 任务一完成对照

| 验收项 | 结论 | 证据 |
| --- | --- | --- |
| vendor 多 Episode 顺序 | PASS | `README.md:353-381` |
| EP code 当前来源 | PASS：当前全链路 EP01 literal；需 registry | `contracts.py:1174-1193`；`episode_binding_service.py:703-732` |
| Outline/摘要/详细分镜边界 | PASS | `contracts.py:662-711`；`storyboard-table.md:1-25` |
| review-report scope | PASS | `episode_auxiliary_artifact_adapter.py:1539-1569` |
| action options（5）来源 | PASS | `episode_action_service.py:607-632`；`DreamAgentDialog.tsx:40-47,303-327` |
| EP01/02/03 动作矩阵 | PASS | 本记录第 8 节 |
| truth ownership | PASS | 本记录第 9 节 |
| 后端合同是否变更 | 是；不改 database.py | 本记录第 10.2 节 |
| 聚焦后端基线 | PASS | `190 passed, 70 subtests passed in 1.92s` |
| 前端交互基线 | PARTIAL | 13 passed；1 项因既有 5173 冲突在 harness 启动前失败 |
| 生产代码零修改 | PASS | 本阶段仅新增本记录 |

任务二必须把本记录中的 option DTO、优先级、disabled preview、confirmation consequences、刷新恢复和 EP01→EP02→EP03 规则转化为可实现交互；不得退回“前端追加两个写死 EP01/EP02 按钮”的方案。
