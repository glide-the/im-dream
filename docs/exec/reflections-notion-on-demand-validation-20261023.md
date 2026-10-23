<!-- [Input] Reflections 按需读取实现、创建 503 修复与用户完整测试要求。 -->
<!-- [Output] 定向技术回归、隔离数据库集成、真实账户和模型链路及正常 Admin 回执。 -->
<!-- [Pos] 本次 Reflections 变更的测试执行记录，原始失败与日志保留在 output/reflections-full-20261023。 -->
<!-- [Sync] 2026-10-23: 追加正常账户、既有 Agent/模型、报告重开、L2/L3 文件和正常 Admin 结算验收；保留首次浏览器入口阻塞。 -->
# Reflections 按需读取测试记录

## 范围与交付状态

工作分支：Dream、Admin 均为 `codex/reflections-l2-l3-20261015`。本轮工作项覆盖创建 503 修复后的任务创建、启动、按需读取、实际来源证据、权限、报告保存与恢复、历史阅读、当天再次分析弹窗，以及 L2/L3 和 Calendar 相邻回归。主 Agent 维护实现与测试、准备和清理隔离 PostgreSQL；`luna_test_runner` 执行确定性检查和隔离回归。

当前实现沿用原任务、栏目 Agent Thread、RTA、Read hook、事件、报告和历史入口。共享数据库结构保持现行 Admin Drizzle 合同。真实验收新增正常任务、Thread、报告、记忆文件、Gateway 请求与 Token 流水；历史正文、订阅配置和旧账本记录保持。正常服务继续使用 3000、8765、5173。Project、Episode、创作 canonical Artifact、Run-private `.dream` 发布和创作 after-turn Hook 属于本轮范围外。

首次入口尝试：`cua.getBrowser({url:"http://127.0.0.1:5173"})` 返回 `Local browser use is disabled in Work settings`，Codex 自身设置控制被拒绝。后续使用项目已安装 Chrome 完成正常公开登录、可见选择与任务启动，使用用户 Chrome 的原有登录会话完成报告阅读、刷新和历史重开，并通过保存密码的正常自动填充登录 Admin。Work 设置保持原值。真实业务入口使用配置的 `http://localhost:5173`；`127.0.0.1` 的登录来源校验返回 `DREAM_ORIGIN_DENIED`。两类浏览器入口分别记录能力结果。隔离技术结果与正常业务结果分别列明。

## 问题处理与测试修订

1. 创建 503 的修复位于 `AdminRequestAuth`：共享 `AdminDataClient` 注册五个 `SCOPE_OPERATIONS`。正常 Admin catalog 的五个精确 descriptor 与内容 schema 匹配，修复后的生产客户端可通过 `supports` 校验。
2. 回归断言按现行合同修订：操作按名称查找；创建只提交来源范围；Notion 实际引用包含正文 SHA 与读取时间；界面文案描述按需读取；弹窗内通过名称定位日记复选框。
3. 新增 v2 测试覆盖真实客户端 dispatch、原 Runner 的最终转录解析及本栏目引用约束、Host 读取、首次证据保存、后续栏目复用、撤权、越界、空正文、未知写入读回和失败重试。Admin 集成通过现行公开 operation/receipt 路由和真实事务执行。
4. 时间线返回测试在卡片获得键盘焦点后记录进入阅读器时的位置。现行页面通过 `focus({preventScroll:true})` 恢复焦点。浮层测试使用现有按钮关闭内容选择和窄屏导航后点击生成，保留真实点击和视口断言。
5. 新测试的隔离 fixture 补齐合法 UUID、独立 Notion credential home 和普通 Chat 的空 task runtime。原始失败日志继续保留。

## 命令与回执

以下命令均使用仓库已安装依赖，Luna 执行的完整日志保存于 `output/reflections-full-20261023/`。

| 检查 | 实际命令与目录 | 退出码 | 结果 |
| --- | --- | --- | --- |
| Dream 后端完整集合 | 在 `backend` 执行下方 13 文件 pytest 命令 | 0 | 415 passed、1 skipped、206 subtests passed |
| L2/L3 相邻合同 | `.venv/bin/python -m pytest -q tests/test_memory_chain.py`，cwd=`backend` | 0 | 58 passed |
| Admin 合同 | `corepack pnpm exec vitest run --exclude "**/*.integration.test.ts"` 后接下方 12 文件集合，cwd=`ink-admin-memory` | 0 | 102 tests passed |
| Admin 数据库集成 | `REFLECTION_CONTENT_PRIVATE_FIXTURE=/private/tmp/ink-reflection-content-db-eERgoX/integration-private.json corepack pnpm exec vitest run app/lib/dream/reflectionAnalysisContent.integration.test.ts` | 0 | 3 tests passed；原始日志 `admin/reflection-analysis-content-integration-v4.log` |
| Reflections 页面 | `E2E_WEB_BASE=http://127.0.0.1:5173 corepack pnpm exec playwright test e2e/reflections-analysis-content.spec.ts --reporter=line --workers=1 --output=../output/reflections-full-20261023/frontend/reflections-23-final-artifacts`，cwd=`frontend` | 0 | 23 passed；含桌面 1440px 与窄屏 375px 截图 |
| Memory / Calendar 页面 | `E2E_WEB_BASE=http://127.0.0.1:5173 corepack pnpm exec playwright test e2e/memory-behavior.spec.ts e2e/calendar-auth-context.spec.ts e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts --reporter=line --workers=1` | 0 | 69 passed |
| Reflections source/browser 合同 | `corepack pnpm exec playwright test app/_dream/components/__tests__/ReflectionHistory.test.ts app/_dream/components/chat/__tests__/ReflectionAnalysisPreview.test.ts app/_dream/components/chat/__tests__/ReflectionAnalysisPreview.browser.test.ts --reporter=line --workers=1` | 0 | 6 passed |
| Voice API 相邻合同 | `corepack pnpm exec playwright test app/_dream/api/__tests__/voiceApi.picture-readonly.test.ts app/_dream/api/__tests__/voiceApi.writing-sse.test.ts --reporter=line --workers=1` | 0 | 7 passed |
| TypeScript | Dream/frontend、Admin 分别执行 `corepack pnpm exec tsc --noEmit` | 0 | 无诊断 |
| 定向 ESLint | 详见两端回执的文件集合 | 0 | 应用变更和新增测试无诊断 |
| 文档引用与保存 | `python3 output/reflections-full-20261023/validate-docs.py`，cwd=`ink-dream-memory` | 0 | 5 份现行文档、52 个本地引用、9 个图块；历史原文与 4 个无关部署文件保持原 SHA |
| Mermaid | `node output/reflections-full-20261023/render-mermaid.mjs`，cwd=`ink-dream-memory` | 0 | 9/9 解析和 SVG 渲染成功，无页面错误 |
| 差异格式 | Dream、Admin 分别执行 `git diff --check` | 0 | 无空白错误 |

Dream 后端最终命令，cwd=`backend`：

```bash
.venv/bin/python -m pytest -q \
  tests/test_reflection_analysis_content.py \
  tests/test_reflection_history.py \
  tests/test_reflections_agent.py \
  tests/test_reflections_config_router.py \
  tests/test_admin_request_auth.py \
  tests/test_admin_reflection_task_data.py \
  tests/test_admin_reflections_config.py \
  tests/test_notion_runtime_integration.py \
  tests/test_claude_agent_notion_cli_runtime.py \
  tests/test_reflection_notion_scope.py \
  tests/test_claude_agent_service.py \
  tests/test_claude_agent_runner.py \
  tests/test_claude_agent_context_builder.py
```

Admin 的 12 文件集合：`reflectionAnalysisContent.test.ts`、`reflectionAnalysisContentHandler.test.ts`、`reflectionHistoryService.test.ts`、`reflectionNotionScopeHandler.test.ts`、`reflectionTaskAuthorityIngress.test.ts`、`reflectionTaskAuthorityService.test.ts`、`reflectionTaskDto.test.ts`、`reflectionTaskEventSequencing.test.ts`、`reflectionTaskHandler.test.ts`、`reflectionTaskOperationCandidate.test.ts`、`reflectionTaskRegistration.test.ts`、`reflectionTaskService.test.ts`，路径前缀为 `app/lib/dream/`。

后端保留的一个 skip 为现有 `test_tool_confirmation_callback_is_called`，依赖真实 Claude Code SDK PreToolUse confirmation。当前 provider-free 集合记录该前置条件。

## 场景覆盖

| 需求项 | 验证交付物 | 当前结果 |
| --- | --- | --- |
| 创建和启动 | v2 client/route tests、Admin 集成、页面 task/SSE 用例 | 来源范围提交、无创建前正文读取、原 start 与事件链路通过 |
| 按需读取 | Host/hook 与实际 section Runner 参数化测试 | 按页读取、保存 SHA、成功读取后可引用；本栏目未读取引用拒绝 |
| 权限 | Admin handler 与 PostgreSQL 集成 | 外部账户/服务、浏览器调用后台操作、错误 Thread/revision、范围外页面、撤销连接均拒绝 |
| 重试与恢复 | Host unknown write、原 receipt、report.ensure、页面恢复 | 未知写入仅查原记录；创建幂等、报告幂等、重载通过 |
| 空正文与零结果 | v2 Host 与 Admin 空页集成 | 保存空页读取记录；结果引用排除空正文；零结果任务完成，`report.ensure` 返回空回执，报告表无新增记录 |
| 兼容与相邻回归 | v1 PG 集成、旧栏目/历史/Chat/Memory/Calendar 用例 | 原公开合同与相邻入口回归通过 |
| 当天再次分析 | 桌面与窄屏页面用例 | 选择继承、取消无写、重开保留、空输入禁用、Notion-only 提交与固定操作区通过 |
| 真实账户与模型 | 正常浏览器入口、正常 Admin 页面及只读核对 | task `48905dfb-118c-4a6f-a2c8-3aaa0d5446bf` 完成三栏各 6 条；报告 56 可刷新后重开；37 个正常 Gateway 请求全部 succeeded/settled |

## 本机真实账户与模型验收

验收账户为用户指定的 `dmeck@suoxya.com`。Dream 通过公开登录页面完成身份认证；Admin 使用用户 Chrome 保存的账号密码自动填充并正常提交，页面显示 `Dmeck / SUPER_ADMIN`。全程保留原认证、来源归属和计费校验；密码、Cookie、OAuth 参数、来源正文和 Agent prompt 未写入验收产物。

| 验收对象 | 实际结果 |
| --- | --- |
| 正常服务与数据库 | Dream 5173/8765、Admin/Gateway 3000；数据库 `ink-memory`、端口 54329、system identifier `7676483171327326081` |
| 既有业务实体 | Deck `长毛猪`（`ad6ef80e-bee4-47b8-a829-ecc8a7e30f9c`）；Agent `边界与红线`（`5188417e-e3fc-4b19-9e52-66c87aa599b3`） |
| 模型 | 账户已保存且公开 catalog 可调用的 `deepseek-v4-flash-vision-exp`；37 个请求的实际模型一致 |
| 输入选择 | 当天再次分析弹窗选择 439 篇日记、Notion 和上述 Agent；Notion 索引范围 344 页 |
| 创建 | 2026-10-23 12:39:03 开始提交，5216 ms 返回 202 与任务 ID；初始正文页数为 0；request key `b7db247c-c6f2-4aef-b8ee-9152c63f9c21` |
| 原启动链路 | events 200；创建返回后立即请求 start，12:39:15.640 开始执行，start 返回 202 |
| 三栏终态 | echoes、traits、patterns 各 6 条、全部 COMPLETED；12:42:43.527 任务完成，无栏目错误 |
| 按需来源 | 三个 Agent 输入均仅含 `snapshot_version`、`index_path`；实际读取 23 页，共 168685 字节；所有正文 SHA 及最终引用的 page ID/SHA/read_at 与保存记录匹配 |
| 报告保存 | 报告 `56` 于 12:42:43.691 保存，18 条结果、23 个实际来源链接，无失败栏目 |
| 报告阅读和恢复 | 浏览器打开单条详情及来源列表；历史可按 12:39:03 的真实创建时间定位；刷新返回回顾入口后重开同一报告，三个栏目仍各 6 条 |
| 幂等与费用 | 重开前后报告 SHA `a900af16a246c1fee7ac44ef768faeb8b8d1c6b9c934d8c4863fef76de419973`、37 个 Gateway 请求完全一致；charged/capture 均为 2833363 Token |
| 正常 Admin 可见性 | 请求日志显示本次 `req_6e5c3f2037684ca088100aeeffdfff86` 为 succeeded/settled、HTTP 200；Token 流水显示对应 reserve/capture/release，其中 capture 为 109716 Token；其余请求通过同一正常数据库精确关联核对 |
| 原记忆后续处理 | 自动生成 artifact `df4219e2-ff55-4f6f-ba29-2b7ce69e3948` revision 1，L2 含 18 条观察，L3 含 1 条主题，均为 ready、规则版本 `memory-rules-v2`；两个 Markdown 文件的 SHA 与正常数据库一致 |

上述 23 页表示 Agent 实际读取并保留的 Notion 来源。344 页表示可检索范围。439 篇日记表示用户选择的分析范围。首次真实验收时，报告来源栏只显示 Agent 和 Notion 页面数，日记范围展示缺失，Notion 文案缺少“已读取”限定；当时登记为展示缺口。用户随后要求直接补齐，实施及验证见下方追加工作项。

模型对三份较大的索引文件的首次 `Read` 各返回一次工具错误，后续分页读取、检索和页面读取成功，三栏正常完成。该记录保留在正常 Thread 中。本轮未通过真实账户执行撤权、故障注入、未知写入或空结果操作；这些恢复分支的覆盖采用前文隔离技术回执。窄屏 375px 交互采用前文页面回归回执；本次正常账户页面观察使用桌面 Chrome。L2/L3 自动产物已核对，本次未额外发起三个 Memory Tools 或行为策略的模型调用。

验收产物位于本机忽略目录 `output/reflections-real-20261023/`：`create-start-receipt.json`、`completed-business-state.json`、`reopened-business-state.json`、`ui-and-recovery-receipt.json`，以及来源选择、再次分析和执行中截图。数据库核对脚本为 Admin 的本机忽略文件 `output/reflections-real-20261023/verify-task.ts`，执行 `BEGIN READ ONLY`、限定本账户与任务的 SELECT，并回滚只读事务。它用于核对正常页面操作产生的记录。实际执行命令：

```bash
# cwd=/Users/dmeck/project/ink-admin-memory；两次执行均为退出码 0
corepack pnpm exec tsx --env-file=.env.local \
  output/reflections-real-20261023/verify-task.ts \
  48905dfb-118c-4a6f-a2c8-3aaa0d5446bf completed
corepack pnpm exec tsx --env-file=.env.local \
  output/reflections-real-20261023/verify-task.ts \
  48905dfb-118c-4a6f-a2c8-3aaa0d5446bf reopened
```

浏览器 runner 在打开单条详情时出现一次 REPL 超时并重置；后续通过用户 Chrome 完成该详情、历史和刷新重开步骤。中间失败保留为 harness 记录。真实业务未重建任务、重跑模型或重放创建写入。

## 资源与后续验收

隔离 PostgreSQL 名称为 `ink_codex_reflection_content_05a86d27bb`，监听端口 58036。主 Agent 在调用唯一 Admin migrator 前核对数据库名、端口、data directory 与 loopback 身份；private manifest 使用 `0600`。本轮完成后，通过自有 fixture 的完成文件通知其关闭数据库，退出码 0，根目录已删除。正常 PostgreSQL、Admin、Gateway、Dream 服务保持运行。

保留原始失败、重跑回执及本次正常任务、报告、记忆和结算记录；未执行合并或远程发布。正常公开入口的正向模型链路已完成，故障分支和窄屏交互的证据范围见前文。

## 追加工作项：报告来源栏

优化执行范围：根据用户直接补齐的要求，复用已保存报告的日记选择和统计、原 Notion 来源链接，在原报告来源栏补齐日记范围及 Notion 已读取数量。交付代码、桌面/窄屏交互与刷新重开验证；任务执行、后端协议、模型和数据库写入保持原合同。本工作项只读取已有正常报告，新增模型调用为 0。

现状核对确认 `analysisContent.diary_session_ids` 与 `stats.entries` 已经通过历史报告返回。方案采用 `ReflectionBlogPage` 的现有区域，明确日记选择范围与 Notion 已读取数量，复用现有列表展开；没有新增页面、接口或持久化字段。具体选择数组优先提供数量，空数组显示 0，null 和旧报告来源摘要缺失时采用已保存报告统计。区域增加 flex wrap 与元素宽度约束。

已保存代码：`frontend/app/_dream/components/AnalysisView.tsx`。正常用户 Chrome 打开原报告 56 后，实际显示“日记范围 · 439 篇”“分析 Agent：边界与红线”“Notion · 已读取 23 个页面”。原报告、任务和模型调用记录保留。正常服务观察属于既有账户的只读展示验收。

技术验证追加到 `frontend/e2e/reflections-analysis-content.spec.ts`：具体选择数量优先于统计、中英文桌面/375px、仅 Notion 的 0 篇日记、旧报告统计、原链接展开、刷新后重开、零创建和启动请求。产物保存于 `output/reflections-source-strip-20261023/`。Luna 实际执行以下命令，均退出码 0：

| 命令，cwd=`frontend` | 结果 |
| --- | --- |
| `E2E_WEB_BASE=http://127.0.0.1:5173 corepack pnpm exec playwright test e2e/reflections-analysis-content.spec.ts --reporter=line --workers=1 --output=../output/reflections-source-strip-20261023/browser` | 27 passed（1.1m），含新增 4 个来源栏场景；原 Reflections 链路回归通过 |
| `corepack pnpm exec tsc --noEmit` | 无诊断 |
| `corepack pnpm exec eslint app/_dream/components/AnalysisView.tsx e2e/reflections-analysis-content.spec.ts` | 无诊断 |

主 Agent 检查新增桌面和窄屏截图，来源字段及原链接可见，无文档级横向溢出。原报告的正常浏览器观察与本表拦截 fixture 的技术回归分别记录；本工作项未新增真实模型调用。

关联：[内容交互稿](../design/memory/reflections-analysis-content-design.md)、[产品需求](../prd/memory/reflections-analysis-content-prd.md)、[Agent 执行设计](../design/memory/reflections-agent-interaction-design.md)。
