# Story Workspace Prompts「来源无效」兼容性返工记录

日期：2026-08-07

范围：真实 run `run_b81d3731b56b4703868b66af76e7b656` 的 EP01 Prompt 产物投影、前端合同与工作流动作恢复

结论：代码已修复；不修改真实创作产物，不派发 Episode 动作。

## 1. 本轮 Optimized Prompt

你是 Ink-Dream 项目的高级全栈工程师。针对真实 Dream run
`run_b81d3731b56b4703868b66af76e7b656` 中“Prompts 来源无效”的错误状态，先读取真实
Episode binding、artifact manifest、vendor drama-prompt 合同和实际
`prompts/prompt_package.yaml`，区分文件确实无效、后端适配器不兼容和前端安全合同误判。
采用 TDD 修复生产实现，使真实多平台 Prompt 包在安全校验、镜头关联、revision 与 workflow
facts 中得到一致投影；不得用前端隐藏错误，不得更改真实创作文件或业务数据库，不得派发可能付费或覆盖
artifact 的动作。完成后运行后端 pytest、前端 Node seam、TypeScript、ESLint 和真实浏览器验收，保存
manifest、workflow facts、截图及测试输出，并独立提交本轮文件。

## 2. Optional Enhancers

- 保留旧版七字段 `ep???-prompts.yml` 兼容性，同时支持当前安装插件的三平台合同。
- 三平台结构只要出现任一平台，就要求 Kling、Runway、Jimeng 全部存在；不完整数据继续 fail closed。
- 公共文本安全规则必须区分普通视觉语义 `node` 与可执行 Node.js 命令。
- 浏览器只读验收，不提交真实 Episode action。

## 3. 执行计划与验收标准

1. 记录 git 与服务基线，复现当前 8765 API 的 `invalid`。
2. 对照 vendor README、已安装 `drama-prompt` Skill、真实文件和适配器定位根因。
3. 先写多平台兼容、缺平台拒绝和公共文本边界的失败测试，再实现最小修复。
4. 运行后端完整 Episode 回归、前端 seam、TypeScript、ESLint 和确定性浏览器回归。
5. 用当前代码的隔离服务读取真实 run，核对 Prompt 数量、Shot 覆盖、workflow action 和桌面/窄屏 UI。
6. 独立提交并只关闭本轮服务。

验收标准：

- `prompts/` 必须由真实 `invalid` 变为 `available`，并保留可信 source revision。
- 22 个 storyboard Shot 必须各关联 Kling、Runway、Jimeng 三条 Prompt，共 66 条，孤儿关联为 0。
- Dream Agent 不再推荐“生成 EP01 Prompt 包”，而应根据当前 facts 推荐“审阅 EP01 完整产物”。
- 普通英文 `node` 可展示；`node --eval script.js` 与 `node scripts/build.js` 仍被拒绝。
- 后端、前端、TypeScript、ESLint 和真实浏览器测试全部通过；真实工作空间零写入、零动作派发。

## 4. 问题判定

### 问题 A：真实 Prompt 包存在，但 manifest 报「来源无效」

问题

→ 真实工作空间已有 `prompts/prompt_package.yaml`，旧服务仍将 `prompts/` 投影为 `invalid`，导致进度显示“来源无效”，并错误保留“生成 EP01 Prompt 包”动作。

现状证据

→ 真实文件 frontmatter 声明 episode 1，文件确实存在：
`backend/data/agent-workspace/30396299-54b3-5227-bcc1-7c9a60dd05d8/stories/proj-da1c690c/episodes/EP01/prompts/prompt_package.yaml:1-7`。

→ 实际 Shot 同时包含 `kling`、`runway`、`jimeng` 字符串：同文件 `:24-26`。

→ 当前安装的 vendor Skill 明确输出 `prompt_package.yaml`，并要求 Kling / Runway / 即梦三平台：
`backend/data/agent-workspace/30396299-54b3-5227-bcc1-7c9a60dd05d8/.ink/plugins/drama-forge@drama-studio@sha256-ee54155bdfed06929c0065563c04c722990614db06082914d2608da5f2a42fd2/.claude/skills/drama-prompt/SKILL.md:3-17`、`:116-194`、`:220-227`。

→ vendor README 仍记录旧式 `ep???-prompts.yml` 七字段产物：
`vendor/drama-forge/drama-forge/README.md:255`；设计说明同时确认同一镜头存在三平台版本：
`vendor/drama-forge/drama-forge/dramaforge-claude-code-template-design.md:429-438`。

根因

→ 后端 Prompt adapter 只接受旧式单条 `positive` / `negative` / `params` 结构；真实安装插件生成的是
Shot 下三平台结构，因此在读取第一条时以 `required_text_missing` 失败。文件并非不存在，也不是 Episode
binding 错误，而是 vendor 合同存在新旧两种合法投影形式，应用侧只实现了旧形式。

可选方案

→ 方案一：前端看到 Prompt 文件后强制显示“已生成”。该方案绕过后端安全解析和 truth ownership，否决。

→ 方案二：把真实文件改写成旧 schema。该方案会篡改用户创作产物，且下一次 vendor 生成仍会复发，否决。

→ 方案三：后端安全兼容旧式七字段和安装插件的三平台合同，前端只消费服务端投影。采用。

最终决策

→ `_prompt_variants` 按可信 Shot 记录生成平台 variant；若发现平台键，必须同时存在
`kling`、`runway`、`jimeng`，支持当前紧凑字符串和 Skill 文档中的结构化 `prompt_text` /
`negative_prompt` / 参数字段；否则继续使用旧式七字段解析。实现见
`backend/services/story_workspace/episode_auxiliary_artifact_adapter.py:367-474`、`:1109-1251`。

→ 每条投影身份由 canonical Shot ID 与平台 kind 组成，不使用数组位置；Shot 关联、source artifact 和 source
revision 仍由服务端拥有，见同文件 `:430-467`。

影响范围

→ 后端只改变 `prompts/` 的安全读取投影；未改变数据库、Episode binding、action allowlist、Continue API、
idempotency 或真实文件。由于 workflow facts 依赖 artifact availability，动作会自然从
`generate_prompts` 前进到 `review_full_chain`。

风险

→ 宽松接受任意平台缺失会把不完整包误报为可用，因此三平台模式必须完整。

→ “可读取”不等于 vendor 完整质量审查通过；完整性与内容质量仍由 `review_full_chain` / `validate_episode` 负责。

验收方式

→ 单元 Red/Green、API 集成测试、真实 API manifest、Shot 定位后的三平台 UI 与工作流动作共同验收。

### 问题 B：合法 Runway 文案中的 `node` 被误判为命令

问题

→ 后端兼容三平台后，真实响应仍在浏览器合同解析时报
`auxiliary.prompts.items[61].positive violates public_text policy`。

现状证据

→ 真实 Runway 自然语言描述包含视觉流程图中的普通单词 `node`；旧正则把任何单词边界 `node` 都当作原始命令。

→ 后端与前端分别在
`backend/services/story_workspace/episode_auxiliary_artifact_adapter.py:111-124` 和
`frontend/src/hooks/story-workspace/contracts.ts:1108-1115` 共同执行 public-text 安全策略。

根因

→ 安全规则缺少命令上下文判断，造成自然语言假阳性。

最终决策

→ 仅当 `node` 后跟 CLI flag、路径起始、含斜杠脚本路径，或 `.js/.cjs/.mjs/.ts/.tsx/.json`
文件名时判为命令。自然语言可读，但命令载荷仍 fail closed。

→ 后端覆盖见
`backend/tests/test_story_workspace_episode_auxiliary_artifact_adapter.py:211-280`、`:908-925`；前端覆盖见
`frontend/src/hooks/story-workspace/__tests__/useStoryWorkspaceEpisodeArtifacts.test.ts:1154-1166`。

风险与验收

→ 通过 `node scripts/build.js` 和 `node --eval script.js` 的负例保证收窄规则没有放开实际 CLI；通过
“one node flickers” 正例保证视觉文案不再误伤。

## 5. TDD 证据

### Red

- 后端正确测试入口：
  `.venv/bin/python -m pytest -q tests/test_story_workspace_episode_auxiliary_artifact_adapter.py -k 'drama_prompt_three_platform'`
  首轮结果：`2 failed, 81 deselected`；旧 adapter 返回 `required_text_missing`，且不能表达缺平台原因。
- 加入真实自然语言 `node` 后再次运行：`1 failed, 1 passed`；失败原因
  `raw_command_forbidden`，证明第二根因可重复。
- 前端聚焦 seam 首轮将自然语言 `node` 拒绝，证明浏览器端也存在同一假阳性。
- 直接运行 `pytest` 曾因项目导入路径发生 collection error；改用仓库规定的
  `python -m pytest` 后才计入功能 Red/Green，该 collection error 不作为产品失败证据。

### Green

- 三平台 adapter 聚焦测试：`2 passed, 81 deselected`。
- adapter 安全回归（自然语言与真实命令）：`11 passed, 73 deselected`。
- adapter 与 Episode API 相关集：`150 passed in 1.12s`。
- 后端 Episode / multi-Episode 完整回归：`498 passed, 77 subtests passed in 8.38s`。
- 前端 artifact parser Node seam：`36 passed (5.3s)`。
- 确定性浏览器 seam `story-workspace-episode-execution.spec.ts`：`2 passed (8.2s)`。
- TypeScript：`npx tsc -b`，exit 0。
- ESLint：覆盖本轮全部前端改动文件，exit 0。
- 最新真实浏览器验收：`1 passed (9.1s)`。

## 6. 真实 run 验收

### 身份与 revision

- run：`run_b81d3731b56b4703868b66af76e7b656`
- actor：`dmeck123@suoxya.com`
- story：`proj-da1c690c`
- opaque Episode ID：`432d16772fea4c5489d3a65d8ff3a152`
- Episode label：`EP01`
- manifest revision：`sha256:3e96262f64b145f73605e395d60ff44e6fab68019ead5f90fece62a83267106a`
- aggregate ETag：`sha256:3125d4ffa16433855b5c8a4b61af9bb5ee3ea1d11812aca0c9917043bd9ed163`
- Prompt content revision：`sha256:12ecffcd489fdc5933f7288c11e5a4904cd455075e72cfcd431d4ca20372d1aa`

结构化证据：

- `output/playwright/story-workspace-real-episode-artifacts/episode-artifact-manifest.json`
- `output/playwright/story-workspace-real-episode-artifacts/workflow-action-projection.json`

当前代码读取结果：`prompts/ availability=available`，66 条 Prompt，22/22 个 Shot 已关联，ratio 1，
Prompt page 66 条全部返回。浏览器 spec 对这些字段作显式断言，见
`frontend/e2e/story-workspace-real-episode-artifacts.spec.ts:87-140`、`:143-166`。

### UI 与 workflow facts

- Episode Overview 显示“Prompts 已生成”：
  `output/playwright/story-workspace-real-episode-artifacts/episode-overview-progress-desktop-1440x1000.png`。
- Shot `S04-E01-020a` 可见 Kling、Runway、Jimeng 三个平台卡片：
  `output/playwright/story-workspace-real-episode-artifacts/episode-artifacts-desktop-1440x1000.png`；断言见
  `frontend/e2e/story-workspace-real-episode-artifacts.spec.ts:289-297`。
- 推荐动作已是“审阅 EP01 完整产物”，`executable=true`；第二个直接操作是“校验并提交 EP01”，其余
  3 项折叠到“更多工作流操作（3）”。桌面证据：
  `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-desktop-1440x1000.png`。
- 窄屏 390×844 无严重横向溢出，动作数量仍为 3：
  `output/playwright/story-workspace-real-episode-artifacts/workflow-actions-narrow-390x844.png`。
- 浏览器监听结果：Story Workspace API 4xx/5xx 为 0，console/page error 为 0，Episode action POST 为 0。

## 7. 诚实遗留与运行说明

- 真实 Prompt frontmatter 的 `total_shots: 21` 位于
  `.../EP01/prompts/prompt_package.yaml:5`，但实际 `shots` 数组和 storyboard 均为 22。此次不修改真实创作
  artifact；22 条实际 Shot 全部成功关联。该元数据不一致应由接下来的“审阅 EP01 完整产物”或
  “校验并提交 EP01”报告处理，不能把“来源可安全读取”夸大为“内容质量已通过”。
- 用户原有 5173/8765 服务在本轮开始时分别由 PID 48097/53706 监听，本轮不重启、不关闭；8765 仍加载旧
  Python 进程，因此用户当前页面需在 owner 控制下重启后端后才会看到修复。当前代码通过隔离的
  5174→8766 组合完成真实验收。
- 本轮未修改 `backend/database.py`，未修改数据库业务行，未编辑真实 Prompt 文件，未派发真实动作，未产生
  模型付费调用。
- 本轮没有覆盖、回滚、格式化或提交其他工作线文件；开始时工作树干净。
- 本轮完成后只关闭本轮启动的 4177、5174、8766，并保留用户的 5173、8765。
- 未执行任何归档操作。
