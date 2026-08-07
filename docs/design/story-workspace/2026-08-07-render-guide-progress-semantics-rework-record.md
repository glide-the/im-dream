# Story Workspace「Renders 尚未生成」语义返工记录

日期：2026-08-07

范围：真实 run `run_b81d3731b56b4703868b66af76e7b656` 的 EP01 产物进度命名与状态文案

结论：修复 UI 语义，不伪造渲染产物，不修改后端 artifact truth。

## 1. 本轮 Optimized Prompt

你是 Ink-Dream 项目的高级全栈工程师。针对真实 Dream run
`run_b81d3731b56b4703868b66af76e7b656` 中 Episode Overview 显示
“Renders 尚未生成”的问题，先核对真实 Episode workspace、artifact manifest、vendor
`/drama-render` 合同、workflow facts 与现有 UI 映射，判断是产物缺失、路径或 schema 不兼容，还是 UI
把“渲染指引”和“最终渲染媒体”混为一谈。不得通过前端把不存在的 artifact 标成已生成。采用 TDD 修复
用户可见语义，保留服务端 availability truth，并用确定性浏览器和真实 run 完成只读验收。

## 2. Optional Enhancers

- 明确区分 `renders/render-guide.md`、render queue 与真实视频/图片文件。
- 未生成渲染指引时显示“尚未准备”；合法指引存在时显示“已准备”。
- 不把 `full-chain-review-report.md` 或 Dream Agent 消息当作 render artifact。
- 浏览器验收监听 Story Workspace API、console、page error 和 Episode action POST。

## 3. 执行计划与验收标准

1. 记录工作树、分支、服务 PID 与真实 EP01 文件清单。
2. 对照 vendor README、已安装 drama-render Skill 与服务端 manifest owner 裁决语义。
3. 先修改组件和浏览器断言得到 Red，再实现 artifact-specific 文案得到 Green。
4. 运行组件 seam、确定性 Playwright、真实 run Playwright、TypeScript、ESLint 和后端相关回归。
5. 保存真实 manifest、workflow action、截图和 revision；独立提交并只关闭本轮 4177 服务。

验收标准：

- UI 不再出现含糊的 `Renders`。
- `renders/ availability=not_generated` 显示“渲染指引 / 尚未准备”。
- `renders/ availability=available` 显示“渲染指引 / 已准备”。
- 不存在 `renders/render-guide.md` 时不得显示已准备，更不得暗示视频已渲染。
- 当前 workflow action 顺序仍由服务端 facts 决定。
- 桌面与窄屏无回归，真实 run 零写入、零动作派发。

## 4. 问题判定

问题

→ Episode Overview 把逻辑 artifact `renders/` 显示为英文复数 `Renders`，用户会自然理解为最终视频或图片。
但当前产品合同实际只投影“渲染指引与队列”，因此“Renders 尚未生成”同时混淆了对象和完成语义。

现状证据

→ vendor README 将 `/drama-render` 定义为“渲染指引（含工具参数、分段策略、拼接方案）”，见
`vendor/drama-forge/drama-forge/README.md:173-177`、`:248-257`。

→ vendor 顺序是完整链路审查通过、`validate_commit.sh` 后才进入 `/drama-render + /drama-voice`，见
`vendor/drama-forge/drama-forge/README.md:366-374`。

→ 服务端将逻辑键 `renders/` 的 producer 定义为 `prepare_render_guide`，见
`backend/services/story_workspace/episode_artifact_service.py:247-253`；实际读取的规范文件是
`renders/render-guide.md`，见同文件 `:981-985`。

→ 没有规范文件或 revision 时，服务端必须投影 `not_generated`，见同文件 `:1278-1286`。

→ 真实 EP01 文件清单中没有 `renders/` 目录、`render-guide.md`、`render_queue.yaml` 或任何视频文件；只有
outline、script、storyboard、Prompt 与审阅报告。真实 API 同样返回：
`renders/ availability=not_generated`、`contentRevision=null`、`mtime=null`、`size=null`。

根因

→ UI 局部常量把后端的 Render Guide artifact 写成了 `Renders`，而 Execution 页其他位置已经使用
`Render Guide`。通用 availability 文案又把所有 artifact 都表述为“已生成/尚未生成”，没有体现
“准备渲染指引”这一受控动作边界。

可选方案

→ 方案一：因为已有 Prompt 或完整链路报告而把 Renders 改成“已生成”。这会伪造不存在的 render guide，否决。

→ 方案二：把 `full-chain-review-report.md` 当作 render artifact。文件职责错误，否决。

→ 方案三：保留服务端 `renders/` availability，UI 改为“渲染指引”，并使用“已准备/尚未准备”。采用。

最终决策

→ 产物名固定为“渲染指引”；`available` 显示“已准备”，`not_generated` 显示“尚未准备”；`invalid` 和
`unavailable` 继续沿用“来源无效/当前不可用”。实现见
`frontend/src/components/story-workspace/episode/StoryWorkspaceEpisodeNarrativeWorkbench.tsx:64-105`、
`:300-313`。

→ UI 只读取每个 manifest entry 的 `relativeKey` 和 `availability`，不从 Agent 消息、数组位置或本地状态推导。

影响范围

→ 仅修改 Episode Overview 的展示语义和相关测试；没有修改后端合同、数据库、workflow facts、action
allowlist、revision 或真实 artifact。

风险

→ 用户仍会看到“尚未准备”，因为这正是当前真实状态。真正的渲染指引必须在前置审查和校验通过后，由受控
`prepare_render_guide` 动作生成；本轮不派发该动作。

验收方式

→ 同时覆盖 `available` 的确定性 fixture 和真实 `not_generated` run，避免只验证一个状态。

## 5. TDD 与验证结果

### Red

- 首轮将测试期望从 `Renders` 改为“渲染指引”，组件聚焦测试结果：`1 failed, 10 passed`；实际 HTML
仍是 `<strong>Renders</strong>`。
- 第二轮加入 artifact-specific 状态期望，结果：`1 failed, 10 passed`；实际仍是“渲染指引 / 已生成”，
证明通用 availability 文案不能表达 Render Guide 的准备语义。

### Green

- `StoryWorkspaceEpisodeNarrativeWorkbench` 组件测试：`11 passed (1.5s)`。
- 确定性浏览器 `story-workspace-episode-execution.spec.ts`：`2 passed (9.0s)`。
- 真实 run 浏览器 `story-workspace-real-episode-artifacts.spec.ts`：`1 passed (7.8s)`。
- 后端 artifact/action 相关回归：`174 passed in 2.12s`。
- `npx tsc -b`：exit 0。
- ESLint 覆盖全部 4 个前端改动文件：exit 0。
- `git diff --check`：通过。

测试断言见：

- `frontend/src/components/story-workspace/episode/__tests__/StoryWorkspaceEpisodeNarrativeWorkbench.test.tsx:471-510`
- `frontend/e2e/story-workspace-episode-execution.spec.ts:769-790`
- `frontend/e2e/story-workspace-real-episode-artifacts.spec.ts:240-258`

## 6. 真实 run 证据

- run：`run_b81d3731b56b4703868b66af76e7b656`
- opaque Episode ID：`432d16772fea4c5489d3a65d8ff3a152`
- manifest revision：`sha256:3e96262f64b145f73605e395d60ff44e6fab68019ead5f90fece62a83267106a`
- aggregate ETag：`sha256:7c6933e6aa02f58e5d3060a769bbcaa09980f1cbecf67154aaf4445937657d84`
- `renders/`：`not_generated`，revision/mtime/size 均为空
- 当前推荐动作：“审阅 EP01 完整产物”
- “准备 EP01 渲染与配音指引”：`preview`，不可派发，原因“完成当前 EP01 步骤后可用”

结构化证据：

- `output/playwright/story-workspace-real-episode-artifacts/episode-artifact-manifest.json`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-action-projection.json`
- `output/playwright/story-workspace-real-episode-artifacts/episode-overview-progress-desktop-1440x1000.png`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-narrow-390x844.png`

浏览器最终证据明确显示“渲染指引 / 尚未准备”，且不再出现 `Renders`。Story Workspace API 4xx/5xx、
console error、page error 与 Episode action POST 均为 0。

## 7. 诚实遗留与运行安全

- 工作空间存在 `full-chain-review-report.md`，但它不是 `renders/render-guide.md`，不能据此把渲染指引标为
已准备。当前服务端仍要求完成当前完整链路审阅与校验后再开放渲染指引动作。
- 本轮未创建、编辑或删除真实创作文件，未修改数据库业务行，未派发真实动作，未产生模型调用。
- 开始时工作树干净；改动仅属于本轮 4 个前端文件与本记录。
- 用户原有 5173/8765 服务保持运行；本轮结束时只关闭本轮启动的 4177。
- 未执行任何归档操作。
