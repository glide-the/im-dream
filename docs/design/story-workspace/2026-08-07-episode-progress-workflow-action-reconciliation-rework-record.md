# 第一集产物进度与 Dream Agent 工作流动作对账返工记录

> 日期：2026-08-07  
> 真实 Run：`run_b81d3731b56b4703868b66af76e7b656`  
> 范围：Episode artifact / workflow facts / OptionV2 action projection / 真实浏览器只读验收  
> 结论：已修复“审阅报告已生成但仍推荐 `review_script`”；未派发真实动作，未执行归档。

## 0. 本轮规划前置器

### Optimized Prompt

基于真实 Run 的 Episode binding、artifact manifest、review provenance、workflow completion 和 action projection，复现并修复“第一集产物进度已显示审阅报告已生成，但 Dream Agent 仍把 `review_script` 作为当前操作”的服务端对账缺陷。不得让前端解析进度 DOM 或本地推导动作；显式 source revision 仍优先，只有报告内容事实与当前可信 completion 同时成立时才允许兼容旧报告。采用 TDD，最终以真实 API 和浏览器证明推荐动作与 canonical 产物进度一致。

### Optional Enhancers

- 区分“报告文件存在”“报告显式绑定当前 script revision”“旧报告由当前 completion 补足 revision 证明”。
- 对缺少早期 output completion 的历史 Run 只建立有界兼容基线；显式 stale completion 继续阻断。
- 真实认证浏览器不落盘新 trace，避免持久化短时认证请求头。

### 执行计划与验收标准

1. 只读核对真实 manifest、review frontmatter、workflow facts 和 action projection。
2. 写真实形态 Red 测试；修复 resolver 与 multi-Episode snapshot；扩大回归。
3. 以独立 8766 当前代码服务和 5174 前端进行真实浏览器复验。
4. 验收要求：`review_script` 消失，推荐动作变为当前缺失产物对应的 `generate_prompts`；显式 stale review/storyboard 仍不能跳步；无真实动作 POST。

## 1. 问题判定

### 问题

→ `EpisodeOverviewContent` 显示“审阅报告 已生成”，但 `StoryWorkspaceDreamAgentDialog` 仍把 key 为 `review_script` 的按钮标为推荐且可执行。

### 现状证据

→ 真实 manifest：outline、script、storyboard、review 均为 `available`；Prompts、Renders 为 `not_generated`。manifest revision 为 `sha256:8b6b7c7d03f7e6e8930d5e93094fa872d1cdab2d8057c5ff21c31b8d0f85bdb8`。  
→ 真实 review projection：`scope=script`、`overallVerdict=APPROVED`、`reviewedArtifacts=[script.md]`，但旧 frontmatter 只有 `reviewed_files[].hash=v1`，没有受支持的 `revision` / `source_revisions`。  
→ workflow facts revision 为 `3`，已包含 `review_script` completion。服务端按当前 `script.md` 重新计算的 action input revision 与 completion 均为 `sha256:a537586f7f9c27601e42e801e3f08c2e13e564353a9c6a0bf6c315c86e03dd81`。  
→ 修复前 projection 为 `review_script + needs_confirmation`；原因代码只比较报告中的 reviewed source revision（`backend/services/story_workspace/episode_action_service.py` 修复前 `759-781`），完全没有使用已由 MCP writer 校验并 CAS 记录的当前 completion。  
→ `StoryWorkspaceDreamAgentDialog` 本身只消费服务端 action options，没有解析产物进度 DOM；因此不能在前端补条件分支。

### 根因

→ 当前 resolver 把“报告内逐文件 sha256”当作 script review current 的唯一证明。真实历史报告早于该字段合同，只携带 `script.md + v1`；与此同时，服务端已经保存了针对当前 script revision 的可信 `review_script` completion，但 resolver 未将二者对账。  
→ 同一历史 Run 的 storyboard 文件已存在，但没有早期 `refresh_assets` / `regenerate_storyboard` completion；旧 resolver 会继续回退到更早步骤，无法按实际产物 horizon 推进到缺失的 Prompt 包。

### 可选方案

1. 前端看到“审阅报告已生成”就隐藏 `review_script`：拒绝。文件存在不等于审阅当前 revision，且会制造第二个 workflow owner。
2. 任何报告文件存在即视为 current：拒绝。stale、invalid、非 APPROVED 报告会错误跳步。
3. 修改真实 review 文件补写 sha256：拒绝。会改写用户创作产物，且不能修复其他历史 Run。
4. 服务端合并 artifact provenance 与当前 completion，并为历史 output artifact 建立有界基线：采用。

### 最终决策

→ 显式 source revision 存在时继续拥有最高优先级；若它与当前 script 不同，即使 completion 当前也必须停在 `review_script`。  
→ 只有在报告 scope 为 script/full-chain、verdict 为 APPROVED、明确包含 `script.md`，且 `review_script` completion input revision 与当前 script 计算结果一致时，才允许补足缺失的旧 source revision（`backend/services/story_workspace/episode_action_service.py:668-698`）。  
→ storyboard/prompts 已存在、对应 output completion 缺失且当前 `review_script` completion 成立时，可作为历史 baseline；一旦对应 output completion 存在但 stale，必须回到更新动作（`backend/services/story_workspace/episode_action_service.py:700-727`）。  
→ storyboard 缺失时仍先要求 assets completion；存在但无法证明 baseline/current 时，也不会直接跳到 Prompt（`backend/services/story_workspace/episode_action_service.py:840-900`）。  
→ multi-Episode snapshot 复用同一服务端判定，不在 projector 或 Dialog 再造规则（`backend/services/story_workspace/multi_episode_action_service.py:321-381`）。

### 影响范围

- 后端：legacy/V1 workflow projection、OptionV2 snapshot 的 current storyboard 判定。
- 前端生产代码：无改动；继续消费服务端 `actionProjection`。
- 真实浏览器用例：更新为新 projection，并取消真实认证 trace 落盘。

### 风险与控制

- 风险：旧 artifact 可能存在但没有 completion。控制：只有当前可信 `review_script` completion 才能启用历史 output baseline。
- 风险：completion 当前但报告显式 revision stale。控制：显式 revision 优先，测试固定仍返回 `review_script`。
- 风险：storyboard completion 已存在但 stale。控制：不使用 legacy baseline，测试固定返回 `regenerate_storyboard`。
- 风险：浏览器误派发真实动作。控制：监听全部 `/episode-actions/` POST 并断言空数组。

## 2. TDD 与回归结果

| 阶段 | 命令/证据 | 结果 |
| --- | --- | --- |
| Red | `pytest ... -k 'legacy_artifact_progress or legacy_progress_keeps'` | `2 failed, 101 deselected`；均错误停在 `review_script` |
| Green 聚焦 | 同上 | `2 passed, 101 deselected` |
| 后端相关 | Episode actions + multi-Episode actions + artifact API | `175 passed` |
| 后端扩大 | `test_story_workspace_episode*.py test_story_workspace_multi_episode*.py` | `494 passed, 77 subtests passed in 6.21s` |
| TypeScript | `cd frontend && npx tsc -b` | exit 0 |
| ESLint | `npx eslint e2e/story-workspace-real-episode-artifacts.spec.ts` | exit 0 |
| Node seam | 先因 4177 未启动得到 2 个 `ERR_CONNECTION_REFUSED`；启动本轮自有 Vite 后重跑 | `2 passed (7.8s)` |
| 真实浏览器 | 独立 8766 当前代码 + 5174，真实 actor/run | `1 passed (7.4s)` |

关键测试位于 `backend/tests/test_story_workspace_episode_actions.py:501-625`：

- 当前 review completion + 旧报告无 sha256 + storyboard available → `generate_prompts`；
- 显式 stale review revision → 保持 `review_script`；
- 显式 stale storyboard completion → `regenerate_storyboard`。

## 3. 真实 API 与浏览器证据

修复后的真实响应：

- HTTP 200；aggregate ETag：`sha256:bc9d85a02be96f9871e1bea00e63c301e8b9fb9d5b7a25e92c7ec81fba56fc67`；
- Episode UID：`432d16772fea4c5489d3a65d8ff3a152`；
- recommended：`generate_prompts`，label“生成 EP01 Prompt 包”，`executable=true`；
- `review_script` 不再出现在 action options；
- 第二个直显操作为“审阅 EP01 完整产物” preview；
- 其余 4 项折叠到“更多工作流操作（4）”；
- EP02 plan 仍为 blocked，原因“完成 EP01 完整产物校验后可用”。

证据文件：

- `output/playwright/story-workspace-real-episode-artifacts/workflow-action-projection.json`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-desktop-1440x1000.png`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-narrow-390x844.png`
- `output/playwright/story-workspace-real-episode-artifacts/episode-artifact-manifest.json`

真实浏览器同时断言：review 进度可见、22 个 storyboard shots 可读、0 个 Story Workspace API 4xx/5xx、0 个 page/console error、0 个 Episode action POST。没有点击“生成 EP01 Prompt 包”，没有外部模型或付费调用。

本轮取消了真实认证用例的新 trace 写入（`frontend/e2e/story-workspace-real-episode-artifacts.spec.ts:47-320`）。证据目录中 2026-08-06 的旧 `trace.zip` 在本轮开始前已存在，本轮未覆盖、未删除，也不把它作为本轮证据。

## 4. 工作区与服务

- 调查开始时：branch `story-workspace`，`git status --short` 无输出；最近提交 `e16a81d`。
- 最终复核时并发出现 `README.md`、`README.zh.md`、`deploy/local/deploy.sh`、`frontend/vite.config.ts` 四个其他工作线改动；本轮未编辑、未格式化、未暂存这些文件。
- 用户原有 5173（PID 87690）和 8765（PID 82275）只读复用，未停止或重启。
- 本轮自有 8766、5174、4177 仅用于当前代码/API/浏览器验收，交付前关闭。
- 没有修改真实 Episode 文件、workflow facts 或数据库业务行；独立后端启动只执行既有幂等表初始化。
- 未覆盖其他工作线文件；未执行归档操作。
