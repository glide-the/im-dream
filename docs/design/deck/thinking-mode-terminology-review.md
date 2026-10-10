<!-- [Input] 用户原始需求、Notion 概念定义、现行 Deck 代码与仓库合同。 -->
<!-- [Output] 可复制的优化提示词、处理判断、修改范围和验证证据。 -->
<!-- [Pos] 2026-10-09 思维模式命名任务的处理记录。 -->
<!-- [Sync] 2026-10-10: 后续复核统一读取根 AGENTS.md，不再引用已删除的根 Agent.md。 -->
<!-- [Sync] 2026-10-09: 记录命名处理、文档与代码修改、测试 fixture 恢复和完整 Chrome 旅程通过回执。 -->
# 思维模式命名任务处理记录

## Optimized Prompt

```text
你是 Ink & Memory 项目的产品与前端工程专家。请完成两项任务：先判断 DeckManager 的中文名称和概念如何调整，再同步修改代码与现行设计稿。

上下文：用户定位的入口是 frontend/app/_dream/components/DeckManager.tsx。概念依据为：
https://app.notion.com/p/ink-and-memory-38f30b7547c3804cb8a0d1250a3b8ae2?source=copy_link#e4f30b7547c3837ab5d4815f3f1b0e37
Ink & Memory 定位于个人思维模式的整理，Deck 是承载形式；面对需求，解决路径、对应方案和 Skills、MCP、Plugin 的组合构成不同的思维模式。中文产品名称必须是“思维模式”。

执行要求：
1. 先读取链接内容、根 AGENTS.md、相关目录合同与当前代码。检查工作区未提交改动，保护用户和其他 Agent 的工作。
2. 区分产品名称、技术标识符和用户业务内容。判断已有实现是否满足目标；本次优先修正文案和设计语义，不创造额外业务能力。
3. 复用 i18n.ts 及现有组件，统一中文导航、工作台页签、列表、预览、维护字段、版本面板、Chat/Dream 信息入口与客户端失败反馈。英文界面沿用 Deck；按当前语言渲染，不拼接双语标签。
4. 保留 DeckManager、Deck 类型、deck_id、公开 API、路由、翻译键、样式类名和已有用户名称及说明。仅允许新建默认名称随中文文案调整。
5. 不改变 CRUD、权限、schema、Runtime、资源策略、启停判断、草稿修订、版本提交或 Thread 语义；不把 Skills/MCP 自动组合、多智能体协作等设想写成已实现功能。
6. 先完成文档，再修改代码。现行 PRD 放在 docs/prd/deck/，包含背景与问题、目标与边界、概念与规则、桌面和窄屏页面骨架、状态、失败恢复和验收矩阵。正式设计稿直接包含 Mermaid 正常业务时序、异常恢复时序和页面状态图。保留历史原文与图示，更新受影响文件头、目录清单和现行引用。
7. 验证范围与命名修改相称。复用本机 Chrome、仓库现有 Provider-free 浏览器旅程和已安装依赖，检查中文、英文切换及窄屏布局。不得调用真实模型、修改真实数据库或停止用户已有服务。报告 Markdown 清单、链接、Mermaid、静态检查和浏览器验证的实际命令、退出码及结果。

交付：清晰说明处理判断、代码与设计文档修改及验证结论；给出可点击文件链接。严格区分文档检查、技术验证和真实业务验收。不要提交、发布或部署未授权的变更。
```

## Optional Enhancers

- 如后续扩大为功能迭代，可另行指定 Skills/MCP/Plugin 组合的具体业务规则与验收对象；本次不采用该扩展。
- 如后续要求真实业务验收，可指定本机现有账户与已有实体；本次不采用该扩展。

## 任务一：处理判断

Notion 页面已读取，项目定位明确指出 Deck 承载个人思维模式。现有 `DeckManager`、维护弹窗、版本组件和 Chat 翻译已覆盖本次所需业务；问题主要是中文产品名称与描述不一致。

因此采取“产品中文名称统一，现有 Deck 实现保留”的处理方式。修正 `i18n.ts` 中文资源，以及维护、版本、插件、Dream 信息组件和 hook 中直接写入的相关文案，不增加配置模型、接口、数据库迁移、页面或确认步骤。

本次属于现有产品名称与说明纠正，没有新增流程或状态行为。文档先行，按现有实现核对设计；不将该措辞修改描述为新业务功能或已完成未来多智能体设计。

## 任务二：执行顺序

1. 建立[业务 PRD](../../prd/deck/thinking-modes.md)和[正式设计](./thinking-mode-terminology.md)，记录产品概念、实际栏目和保持原样的业务边界。
2. 同步当前设计索引、入口、视觉和版本文档中的现行中文名称指引，保留原有历史图示。
3. 修改既有翻译和组件，更新对应文件头及目录清单；保留业务内容与协议。
4. 复用既有维护旅程，加入中文思维模式用语和窄屏布局断言，执行静态与文档验证。

## 合并交付规划（Optimized Prompt）

```text
将本次思维模式命名变更创建为 GitHub PR，合并到仓库默认主分支，并将原工作区切回该分支。先检查远程默认分支、当前提交与工作区差异；使用独立 codex/ 分支只提交本次代码、设计、目录合同和必要双语 README 引用。保护其他任务的未提交文件与本地提交，不将 README 扩写或图片生成设计混入本 PR。复核提交树的路径、README 镜像及已验证源文件，记录实际检查；创建 PR 后等待适用 GitHub CI，按仓库允许方式合并。同步本地主分支时保留其他工作，并确认最终分支、PR 状态和剩余改动。
```

仓库默认主分支为 `develop`。本次使用独立工作区准备 29 个文件的提交，README 仅包含思维模式概念、中文名称和 PRD 引用；其他任务的九模块 README 改写、配图及图片生成设计保留在原工作区。八个生产文件和浏览器旅程与已通过验证的源码一致。

## 验证证据

### 首轮回执与恢复

本轮验证使用现有本机 Next 和本机 Chrome，业务接口均由 Playwright fixture 模拟。首次运行在会话中断时仅保留“测试已开始”的日志，没有退出结果，不作为通过证据。

接续验证由 `luna_test_runner` 执行，使用[浏览器验证技能](../../../.agents/skills/ink-dream-playwright-qa/SKILL.md)和用户技能目录中的 `luna-test-stage` 技能；后者本次读取位置为 `/Users/dmeck/.codex/skills/luna-test-stage/SKILL.md`。

| 检查 | 实际命令或方法 | 退出码 / 结果 |
| --- | --- | --- |
| 定向 ESLint | 在 `frontend/` 执行 `corepack pnpm exec eslint app/_dream/i18n.ts app/_dream/components/DeckEditorModal.tsx app/_dream/components/DeckClaudePluginSelector.tsx app/_dream/components/deck/DeckVersionPanel.tsx app/_dream/components/deck/DeckVersionSubmitDialog.tsx app/_dream/hooks/useDeckPluginBinding.ts app/_dream/hooks/useDeckPluginOptions.ts app/_dream/components/story-workspace/dream/StoryWorkspaceDreamDeckMetadata.tsx e2e/chat-first-deck-defaults.spec.ts` | `0`，无错误 |
| TypeScript | 在 `frontend/` 执行 `corepack pnpm exec tsc --noEmit --incremental false` | `0` |
| 原旅程首次完整回执 | Playwright 运行 `e2e/chat-first-deck-defaults.spec.ts`，临时配置指定本机 Chrome | `1`；登录表单跳转真实外部 Admin，遇到 Cloudflare 522，后续断言未执行 |
| 正式设计图语法 | 本机 Chrome 加载已安装 Mermaid `11.16.0`，对正式设计的三段 Mermaid 逐段执行 `mermaid.parse` | 三段均成功，`3/3` |
| 首轮文档检查 | 文件清单、相对引用与锚点、README 双语结构、翻译键与插值检查 | `1`；检查器额外要求未规定的 H1，并将英文复数键与中文无复数键按字面比较，属于检查器缺口 |
| 差异空白检查 | `git diff --check` | `0` |

原浏览器旅程仍模拟旧 `/api/login` token，与当前公开 Cookie/CSRF session 和 Admin 表单流程不符。测试现已复用仓库已有语言偏好旅程的认证 fixture 方法：`/auth/options`、`/auth/session` 和表单 action 均在技术 fixture 中拦截，保持真实生产表单及后续业务组件，不连接真实 Admin、不新增生产入口。

文档检查不要求新设计标题包含实现别名；“思维模式命名与交互设计”与 PRD、链接保持一致。翻译检查需要按语言复数规则比较同一键族，并核对 `{{count}}` 插值；已有英文 `agentCount_one/other` 与中文 `agentCount` 不需要修改。

首轮日志、失败截图和 trace 保存在 `frontend/test-results/ink-thinking-mode-qa-resume-20261009/`。原临时配置、Mermaid HTTP 服务及临时目录已清理，用户的本机 Next 服务保留。

### 恢复与最终浏览器结果

后续回执暴露的是测试与当前页面、语言或公开读取合同的差异，按具体原因修正：中文主导航检查移到返回应用后的主页面；Work 页签、分页及错误提示限定到其实际区域；当前英文提交提示按英文断言；插件和 MCP 的只读目录补齐现行 DTO fixture。没有调整生产状态机、HTTP 接口、业务数据或资源策略。

源码核对确认 `useEditSessionEvents` 与 `usePluginInstallations` 在退出时取消 GET，`ChatView` 在重读和退出时取消旧列表请求。因此测试只将列明的 GET `net::ERR_ABORTED` 单独记录为 `expected-lifecycle-aborts` JSON 附件，其中线程列表 query 必须精确为 `?limit=21`。未知请求、其他失败原因、HTTP 错误、console error 与 pageerror 继续参与严格诊断，不做全局取消忽略。

| 检查 | 实际命令或方法 | 退出码 / 结果 |
| --- | --- | --- |
| 最终测试 ESLint | 在 `frontend/` 执行 `corepack pnpm exec eslint e2e/chat-first-deck-defaults.spec.ts` | `0` |
| 修正后的文档检查 | 在 `frontend/` 执行 `node test-results/ink-thinking-mode-qa-final-20261009/docs-static-check.mjs` | `0`，`SUMMARY failures=0`；清单、相对链接与锚点、README 双语结构、翻译键族与插值通过，原有 11 段业务图保留 |
| 完整 Chrome 旅程 | `E2E_WEB_BASE=http://127.0.0.1:5173 /Users/dmeck/project/ink-dream-memory/frontend/node_modules/.bin/playwright test /Users/dmeck/project/ink-dream-memory/frontend/e2e/chat-first-deck-defaults.spec.ts --config /Users/dmeck/project/ink-dream-memory/frontend/playwright.ink-thinking-mode.qa-lifecycle.config.mjs`，cwd 为本轮命名的临时目录 | `0`，`1 passed (15.2s)` |
| 通过旅程证据 | 同一命令添加 `--reporter=json`，临时配置指定 `trace: "on"` | `0`；保留 JSON、通过 trace、21 张主动截图及 14 条明确的 lifecycle GET 取消记录 |
| 最终差异检查 | `git diff --check` | `0` |

完整旅程覆盖登录、首页资格投影、系统预览、Chat 草稿、Dream fixture 入口和恢复、工作台、中英切换、中文维护和 390px 无横向溢出、创建、Agent/Prompt/插件修改、内容版本预览与提交、重新打开、相关对话冲突处理、启停失败恢复和 Agent 删除。最终断言要求未知请求和未预期诊断均为空，并消费四次主动注入的 HTTP 失败。

最终证据位于 `frontend/test-results/ink-thinking-mode-qa-lifecycle-20261009/`，原始命令与退出码见该目录的 `commands-exit-receipt.md`。额外一次配置路径错误的调用未启动测试，以独立 harness 错误日志保留，不计为旅程失败或通过。执行配置与临时 cwd 已清理，本机 Next PID `62544` 保留。

### 最终静态复核

在最后一次测试 fixture 和本文结果更新后，重新执行当前代码的 `corepack pnpm exec tsc --noEmit --incremental false`、上表完整八个生产文件和测试的 ESLint、`node test-results/ink-thinking-mode-qa-final-20261009/docs-static-check.mjs`、目录路径清单脚本和 `git diff --check`，退出码均为 `0`。文档脚本输出 `SUMMARY failures=0`；目录脚本核对五个新增路径与十一份受影响目录清单。

完整命令、日志与退出码位于 `frontend/test-results/ink-thinking-mode-qa-final-static-20261009/commands-exit-receipt.md`；清单检查命令为 `node /Users/dmeck/project/ink-dream-memory/frontend/test-results/ink-thinking-mode-qa-final-static-20261009/folder-inventory-check.mjs`。该阶段没有启动服务或浏览器，误创建的临时嵌套目录已清理。

本轮结果是文档检查与 Provider-free 技术验证；没有真实账户、真实 PostgreSQL、真实模型、Token 结算或发布验收结论。
