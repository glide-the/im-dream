# drama-forge 多 Episode 工作流操作：任务三实施与验收记录

> 日期：2026-08-06
>
> 上游裁决：`2026-08-06-drama-forge-multi-episode-workflow-actions-task1-problem-decision-record.md`
>
> 通过设计：`design_011_drama-forge-multi-episode-workflow-actions.md`
>
> 独立评审：`2026-08-06-drama-forge-multi-episode-workflow-actions-task2-design-review-record.md`
>
> 实施方式：U1—U10，逐单元 Red → Green → 回归 → 独立提交
> 结论：专项代码、确定性浏览器与真实只读浏览器验收通过；未派发真实 Episode 动作

## 0. 本轮规划前置器

### 0.1 Optimized Prompt

严格以任务一的产品裁决和任务二通过独立评审的 `design_011` 为唯一实施输入，采用 TDD 将服务端拥有的多 Episode workflow action projection 落地。后端必须从 actor、Deck、run、story、Episode registry/binding、artifact manifest、workflow facts 与 revisions 生成可信 OptionV2、opaque actionId、目标 Episode、canonical inputs、disabled reason 和指令模板；前端只能消费该投影、显示最多两个直接动作、计算真实 overflow 数量、打开受控确认窗口并提交 actionId。实现 EP01/EP02/EP03 稳定身份、当前 Episode storyboard/Prompt、下一 Episode 入口、幂等与刷新重入恢复，覆盖桌面、390px、键盘、Escape 与焦点。不得修改 `backend/database.py`、拼接任意 slash command、挂载 ChatView、使用 localStorage 拥有 workflow truth，或以 mock/消息冒充真实 artifact 成功。每个 U 单元必须留下 Red/Green 证据并独立提交；最终以 pytest、Playwright Node seam、真实浏览器、TypeScript、ESLint、截图、trace、run/Episode/revisions 和零真实派发证明结果。

### 0.2 Optional Enhancers

- 保留 legacy surface 的只读兼容，但所有新派发走 OptionV2。
- actionId 同时绑定 run、可信 target、action、intent 与 input revision，避免数组位置身份。
- 将 next Episode candidate 也设计为 opaque server identity；浏览器永远不发送路径或 EP 数字。
- 真实浏览器只做事实、展开、确认前合同与响应式验收；付费/覆盖动作不派发。
- 对截图增加人工可读性复核，不以“无水平溢出”替代文本不重叠。

### 0.3 执行计划

1. U1 建 OptionV2 与纯投影；U2 建 registry/binding；U3 连接当前 Episode facts。
2. U4 连接下一 Episode candidate/bound entry；U5 用可信选择器构造 Agent instruction。
3. U6 实现前二/overflow；U7 实现 opaque confirm/POST；U8 实现 revisions/幂等/重入。
4. U9 完成键盘、Escape 与焦点恢复；U10 完成 E2E、真实浏览器、静态检查和文档。
5. 每单元只提交自身文件，最后复核禁改文件、其他工作线、服务归属和归档状态。

### 0.4 验收标准

- 用户要求的 23 类测试均有专项测试、代码证据或真实浏览器证据。
- 每个动作显示可信目标 EP；当前与下一 Episode 不混淆。
- 默认最多两个动作，N 等于真实隐藏项；preview/blocked 不可点击。
- V2 POST 不含 action、episodeId、displayCommand、路径或 slash command。
- refresh/reentry 只从服务端 registry/manifest/facts 重建。
- pytest、18 项前端专项、真实 actor/run、`tsc -b`、全部改动前端 ESLint 通过。
- 不修改 `backend/database.py`；不关闭用户已有服务；不执行归档。

## 1. 最终业务定义与架构裁决

“Outline 分镜生成选项”不是一个 vendor 状态。最终拆成三个已有业务动作：

1. `基于最新剧本更新 EPxx 详细分镜`：当前 Episode 已有 detailed `storyboard.yaml` 且 script/review/assets revisions 允许重入时的明确更新动作；
2. `生成 EPxx Prompt 包`：当前 Episode detailed storyboard 后的正式下一步；
3. `开始 EP(next) 分集规划`：当前 Episode 已校验、项目仍有可信下一集时的跨集入口；若 `/drama-plan` 已生成下一集 outline，则投影为 `创作 EP(next) 剧本`。

前端没有新增 “Outline 分镜” 状态，也不从按钮、数组下标或 URL 推导 EP。服务端 registry/binding 拥有身份，manifest 拥有 availability/revision，workflow facts 拥有合法动作，文件拥有正文，Agent 消息只展示过程，前端只拥有展开/选择/草稿/焦点。

## 2. 实施结果总览

| 单元 | 主要结果 | Red / Green 证据 | 独立提交 |
| --- | --- | --- | --- |
| U1 | OptionV2、状态不变量、最多 9 项、opaque actionId 纯投影 | `evidence/2026-08-06-multi-episode-u1-{red,green}.txt` | `32b000c` |
| U2 | v2 Episode registry、EP01/02/03 稳定 UID、v1 兼容投影与 CAS | `...-u2-{red,green}.txt` | `7295e00` |
| U3 | manifest + workflow facts → 当前 Episode 推荐/重入动作 | `...-u3-{red,green}.txt` | `75f3e2b` |
| U4 | validated current → next candidate/bound Episode 两步 horizon | `...-u4-{red,green}.txt` | `427c78e` |
| U5 | actionId 选择器与可信 EP 指令模板；拒绝错误 run/target | `...-u5-{red,green}.txt` | `f23b6dc` |
| U6 | Dream Agent 前二、overflow(N)、preview/blocked/pending 视觉 | `...-u6-{red,green}.txt` | `977d03a` |
| U7 | 目标 EP + action-specific canonical inputs 确认；opaque POST | `...-u7-{red,green}.txt` | `408ee47` |
| U8 | REST projection/ETag、每集 facts、晚响应与刷新重入恢复 | `...-u8-{red,green}.txt` | `11cd62f` |
| U9 | actionId+wasOverflow 焦点重建、Escape 栈、390px 键盘 | `...-u9-{red,green}.txt` | `fdd786b` |
| U10 | V2 E2E、正确确认来源、重复提交、真实只读浏览器、窄屏修复、文档 | `...-u10-{red,green}.txt` | 本记录所在独立提交 |

## 3. 合同与边界实现

### 3.1 后端

- `backend/story_workspace/contracts.py` 新增严格 discriminated canonical inputs、OptionV2、target current/next、registry v2 和 Continue V2；Pydantic 拒绝错误身份组合、非法状态与多余字段。
- `backend/services/story_workspace/multi_episode_action_service.py` 是 server truth projector：actionId 哈希可信 run/target/action/intent/input revision；label 使用 server-formatted `EP{NN}`；current suffix、storyboard regeneration 与 next two-step horizon 最多 9 项。
- `episode_binding_service.py` 保留 legacy EP01 read compatibility，并以 CAS 建立/激活 EP02、EP03；浏览器不接触 episode code 到路径的映射。
- `episode_artifact_service.py` 和 gateway 从 registry/facts/manifest 构造聚合 ETag 与 `actionProjection`；EP02+ facts 使用带 opaque UID 的独立文件，EP01 保留兼容文件名。
- `episode_workflow_instruction.py` 只接收已验证 selector；后端模板从可信 Episode binding 选择 vendor instruction，不接收浏览器命令。
- gateway 在文件探测/派发前复核 actor、Deck、run、story、Episode、runtime lock，并继续保留 allowlist/ETag/409 边界。

### 3.2 前端

- 严格解析 OptionV2 并审计公开字符串字段；legacy surface 只读兼容，新 V2 请求只发 `actionId + idempotencyKey + userGuidance`。
- Execution 直接投影服务端 options，不创建业务动作；推荐项成为页面主入口，同一 actionId 进入确认，代码见 `StoryWorkspaceExecutionPage.tsx:880-919,947-1015,1307-1331`。
- confirmation 显示目标 Episode、action-specific canonical inputs/revisions 与 consequences；Agent 来源取消时重建 Agent，页面来源取消时恢复页面按钮，代码见 `StoryWorkspaceExecutionPage.tsx:1415-1435`。
- Dialog 始终 `slice(0, 2)`；overflow 数量来自其余真实项；disabled preview/blocked 仍可读但不可派发；U9 以 ref map 按 actionId 恢复焦点。
- 390px overflow 使用 max-content grid rows 并在 176px 区域内滚动，避免三行文案挤入相邻按钮，见 `StoryWorkspaceDreamPage.css:459-470`。

## 4. 多 Episode 动作矩阵

| 服务端事实 | 推荐动作 | 可执行备选 | 折叠预览/阻塞 |
| --- | --- | --- | --- |
| EP01 script 尚待审阅 | 审阅 EP01 剧本 | 无 | assets、storyboard、Prompt、full review、validate、render |
| EP01 storyboard current，Prompt 缺失 | 生成 EP01 Prompt 包 | 基于最新剧本更新 EP01 详细分镜 | full review、validate、render、EP02 plan blocked、EP02 script preview |
| EP01 validation current，EP02 未绑定 | 开始 EP02 分集规划 | 更新 EP01 详细分镜、准备 EP01 渲染与配音指引 | 创作 EP02 剧本 preview |
| EP02 outline 已存在 | 创作 EP02 剧本 | 当前 EP01/02 合法替代项 | 审阅 EP02 剧本 preview |
| EP02 validation current | 开始/创作 EP03 | 同规则 | 仅 current + next，不保留 previous |
| 最后一集 validation current | 准备该集渲染与配音指引 | 更新该集详细分镜 | render 完成后 options 空 |

EP01/EP02/EP03 测试使用不同 opaque UID、label 与 actionId；actionId 不依赖数组位置。真实 run 的项目计划当前只提供 EP01，因此真实证据诚实显示 7 个 EP01 动作，不伪造 EP02；EP02/03 由后端确定性测试和浏览器 fixture 覆盖。

## 5. TDD 与评审

### 5.1 Red

U1—U9 的失败输出均已随相应提交保存在 `docs/design/story-workspace/evidence/`。U10 新增两项有效 Red：

- OptionV2 页面主入口没有选择推荐 actionId，且确认来源状态残留导致取消焦点错误；
- 真实 390px overflow 的按钮内容高度大于 grid row，截图人工复核后增加 `scrollHeight <= clientHeight` 断言并稳定复现。

详见 `evidence/2026-08-06-multi-episode-u10-red.txt`。

### 5.2 Green 与单元复核

每个单元提交前均执行聚焦测试、相关回归与 diff check。最终复核特别确认：

- 无 `backend/database.py` 改动；
- 前端没有构造 `/drama-*` 请求；公开 `displayCommand` 仅展示服务端返回值；
- V2 endpoint 重复相同 actionId/key 返回同 messageId 和 `replayed=true`，测试见 `backend/tests/test_story_workspace_episode_actions.py:1299-1318,1333+`；
- preview/blocked 在组件和 contract 两层拒绝派发；
- late response、refresh/reentry 不覆盖更高 revision；
- confirmation 与 Dream Agent 不同时 mount，页面没有 `<ChatView`。

## 6. 最终测试结果

| 门 | 结果 |
| --- | --- |
| 后端专项 pytest | `221 passed, 77 subtests passed in 3.62s` |
| 前端 OptionV2/recovery/Dialog/Execution/mock E2E | `18 passed in 11.4s` |
| 真实 actor/run Playwright | `1 passed in 6.9s` |
| TypeScript | `npx tsc -b`，exit 0 |
| ESLint | 自 `6506432` 起全部改动 `.ts/.tsx`，exit 0 |
| U10 幂等聚焦后端 | `1 passed in 0.51s` |

完整命令和输出见 `evidence/2026-08-06-multi-episode-u10-green.txt`。

## 7. 真实浏览器证据

### 7.1 身份和 revisions

- actor：`dmeck123@suoxya.com`；UI 当前显示名称/邮箱与登录 actor 的资料存在历史差异，不影响 token actor 授权，测试以 token 对应用户记录为准。
- run：`run_b81d3731b56b4703868b66af76e7b656`。
- Episode UID：`432d16772fea4c5489d3a65d8ff3a152`，label `EP01`。
- manifest：`sha256:8b6b7c7d03f7e6e8930d5e93094fa872d1cdab2d8057c5ff21c31b8d0f85bdb8`。
- aggregate ETag：`sha256:89e6eebdf7a12f8f2cf631d0cfb4d3b5127a6a3e983831f62a0544450e41c7c5`。
- workflow facts revision：`3`；当前推荐 `审阅 EP01 剧本`。
- artifact revisions：outline `6677ad…812e`、script `eaa513…7669`、storyboard `f7a5a5…f1b6`、review `95757a…0f5c`；Prompt/Renders 尚未生成。
- action projection：7 项，默认 2 项，`更多工作流操作（5）`；`生成 EP01 详细分镜` 与 `生成 EP01 Prompt 包` 均为真实 disabled preview，原因是先完成当前 EP01 步骤。

### 7.2 文件

- `output/playwright/story-workspace-real-episode-artifacts/workflow-action-projection.json`
- `output/playwright/story-workspace-real-episode-artifacts/episode-artifact-manifest.json`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-desktop-1440x1000.png`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-narrow-390x844.png`
- `output/playwright/story-workspace-real-episode-artifacts/trace.zip`

浏览器监听所有 `/episode-actions/` POST 并断言为空数组。没有点击真实派发按钮，没有付费模型调用，没有覆盖 artifact，也没有用 mock 冒充真实 run 成功。

## 8. 变更文件分类

### 8.1 后端生产

- `backend/story_workspace/contracts.py`
- `backend/services/story_workspace/multi_episode_action_service.py`
- `backend/services/story_workspace/episode_binding_service.py`
- `backend/services/story_workspace/episode_artifact_service.py`
- `backend/services/story_workspace/episode_action_service.py`
- `backend/services/story_workspace/episode_workflow_instruction.py`
- `backend/services/deck/story_workflow_gateway.py`
- `backend/routers/story_workspace.py`

### 8.2 前端生产

- `frontend/src/hooks/story-workspace/contracts.ts`
- `frontend/src/hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts.ts`
- `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx`
- `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.css`
- `frontend/src/components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx`

### 8.3 测试与文档

- 7 个新增后端多 Episode/OptionV2 测试文件及既有 Episode gateway test；
- OptionV2、REST recovery、Dialog、Execution、mock E2E、real E2E 前端测试；
- 任务一记录、任务二设计/评审、`design_011`、本记录与 U1—U10 证据。

## 9. 按设计实现与诚实遗留

| 设计项 | 结果 | 备注 |
| --- | --- | --- |
| server truth ownership | 已实现 | registry + manifest + facts → projection |
| EP01/02/03 稳定身份 | 已实现并测试 | 真实 run 当前只有 EP01 |
| current storyboard update / Prompt | 已实现 | 真实状态当前为 disabled preview |
| next Episode plan/script | 已实现并测试 | 未在真实项目伪造下一集 |
| 两直接项 + overflow(N) | 已实现 | 真实 2+5 |
| confirmation/canonical inputs | 已实现 | 真实浏览器停在派发前 |
| idempotency/revision/reentry | 已实现并测试 | 同 key replay + late response gate |
| desktop/narrow/keyboard | 已实现 | 窄屏人工复核促成 U10 CSS 修复 |
| durable accepted/dispatchState 恢复 | 合同可表达；仍依赖现有消息/REST 落地时序 | 没有真实长任务派发证据，不宣称外部模型完成 |
| legacy EP01 surface | 保留只读兼容 | 新 V2 路径不依赖前端 EP01 命令常量 |

## 10. 工作区与服务安全

- 开始时工作区干净，U1—U9 均独立提交；任务一/二文档一直保持单独未提交，不覆盖其他工作线。
- 本专项没有发现或修改其他工作线脏文件。
- 用户原有 5173/PID 87690 与 8765/PID 82275 全程保留。
- U10 自有服务 4177 deterministic Vite、5174 real-browser Vite、8766 current-code backend 均已关闭；端口复核无监听。
- 用户原有 5173/PID 87690 与 8765/PID 82275 在清理后仍继续监听。
- `backend/database.py` 未修改。
- 未执行 push、PR、归档、删除 artifact 或任何不可恢复操作。
- 明确声明：本轮未执行归档操作。
