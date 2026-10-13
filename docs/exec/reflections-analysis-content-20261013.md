<!-- [Input] AGENTS.md、当前 Reflections、Notion 索引及 Deck Agent 合同。 -->
<!-- [Output] 本轮执行依据、发现、设计评审、影响评估和验证回执。 -->
<!-- [Pos] 回归分析内容选择实施工作记录。 -->
<!-- [Sync] 2026-10-13: 保存只读基线并开始 Double Diamond 核对。 -->

# 回归分析内容选择实施记录

## 执行依据

Optimized Prompt:

在当前共享工作区完成回归分析的分析内容展开入口、Notion 整体开关和 Deck 分组 Agent 选择，统一总分析入口。先读取历史、当前合同和实现，追踪候选、请求、执行上下文、事件、结果与历史报告，再定义最小范围、比较方案、编写正式设计并评审。复用 Notion 已挂载索引与读取接口、Deck 选择组件、Admin 持久化和任务恢复。配置不得启动同步或模型；默认继续仅分析日记。每个任务冻结选择和正文，服务端校验归属、可用性、权限与快照版本。来源不能混用日记会话标识。保留原有栏目配置、错误、报告和日历访问。不修改其他任务的文件，不新增 Dream 数据库行为或控制通道。若现有冻结合同不足，先在 Admin 准备最小前向合同，缺失能力必须关闭新增路径。设计、实现及修复由主代理完成；有界、隔离、无模型调用的验证交给 Luna 测试代理，保留首测和复测回执。全部必要验证完成前保持目标 active，不部署或重启用户服务。

Optional Enhancers: 保存桌面、窄屏截图和选择到报告的证据对应。

## 计划

1. 保存现有改动的文件摘要，读取现行路径和测试。
2. 定义 Notion 范围与 Deck Agent 的分析执行语义，交付产品需求和正式业务图；在实现前保存评审。
3. 扩展通过评审的必要边界并同步目录合同和文件头。
4. 保存影响评估，执行完整相关旅程及合同验证，修复后复测。
5. 核对基线、文档引用、图语法和变更差异，汇报实际完成状态。

## 发现

- 历史聊天 `01a1074e-7297-7641-a8ec-cad809d85990` 主要交付日历 Notion 栏目设计；其中旧路径和外部接口说明只作历史背景。
- `AnalysisView.runAnalyzeAll` 只传入 language、sessionIds、onEvent。`ReflectionTaskCreateSnapshotDTO` 和 `ReflectionLaunchSnapshotDTO` 只有日记会话、语言、栏目配置和统计。当前 Notion 没有加入回归分析。
- `NotionSnapshotStore` 明确拒绝快照正文；`CanonicalWorkspaceSnapshot.pages` 是兼容空字段。本地保存的是已挂载资源的索引，正文由 `NotionOperationClient.get_page_markdown` 读取。不能将索引说明成全文快照。
- `DeckChatSelector` 按 Deck 分组、选择 Agent，公开值为 `{deckId, agentId}`。分析选择应固定一个 Agent 的分析指令；不将组标题误认为可执行选项。
- Admin 当前 Registry99 严格冻结任务输入和 worker-load 合同。直接增加字段、复用会话标识或只保存在前端都会破坏恢复和报告追溯；实现须先解决任务输入持久化边界。
- 本轮基线摘要在 `output/playwright/reflections-content-20261013/baseline.json`；同步、设置、认证等既有改动不属于本轮所有权。

## 实现前评审

结论：**修改后可实施**。完成以下收敛后，允许实施选定最小方案；新增能力尚未发布时不能将新增路径称为现有服务已可用。

1. 将“本地全文快照”改为“本地挂载索引 + 提交时读取正文”，标明索引版本和正文读取时间。复用现有读取接口，只有点击分析才读取范围内页面。
2. 保留 Deck 分组、Agent 选择合同，采用所选 Agent 的分析指令。回归分析不切换 Chat 插件、模型或 Dream 写作协议；面板明确名称，避免声称选择整个 Deck Runtime。
3. 排除浏览器本地保存正文和 Dream JSON 数据库。原 Admin DTO 严格冻结，必须通过一列任务私有输入和追加操作在事务内保存，保留全部旧操作描述和旧日记路径。该扩展是恢复所需数据，不是全局配置系统。
4. 只增加 Notion 整体开关，不增加逐资源管理器、扫描、同步或确认。日历今天列表不决定分析范围。
5. 删除可见栏目 Analyze，不删除公开分区接口；原有配置、报告、事件和恢复继续复用。
6. 补齐即时提交锁、原任务查询失败不得另建任务、服务器已保存报告不得重复写入、保存失败可恢复。这些是完整旅程必要边界。

页面骨架与正式正常、异常、状态图已直接交付到各自正文。权限未扩大、没有任意产品配额、没有新同步机制。Admin 前向 migration/capability 由主代理处理，Dream 仅在发布的能力存在时使用新增操作。

## 影响评估（测试前）

| 模块与事实 | 变化与调用者 | 必要验证 |
| --- | --- | --- |
| AnalysisView / voiceApi | 页面选择到真实 DTO、统一入口、提交锁、报告恢复 | 桌面和窄屏配置到请求/事件/结果/历史/再次分析 |
| DeckChatSelector | 可选文案和焦点恢复；公开 `{deckId, agentId}` 不变 | Chat 分组选择回归和键盘 |
| reflections router / engine | 选择验证、Notion 冻结输入、Agent prompt、恢复 | 默认/开启/关闭、拒绝无效输入、执行/部分失败/报告保存重试 |
| Admin task | 私有输入列、追加能力和操作、原报告来源摘要 | 隔离 PostgreSQL migration、归属/事务/幂等、旧描述不变 |
| Notion facade / 索引 | 调用既有快照和正文读取，不更改同步所有权 | 授权/挂载/版本变化、去重、读取失败和日历访问回归 |
| Project / Episode / canonical Artifact | 不在范围，均不改变 | 不创建 Dream 写作或资产输入 |
| Run-private .dream / after-turn Hook | 不在范围 | 不改变产物发布或后台 Hook |
| Runner / ThreadFactory / EventBus / SSE / turn / cancel | 保持现有生产路径与协议，只供给任务输入 | 原任务恢复和持久事件回归 |

本轮技术验证不使用付费模型、正常账户或正常数据库。Luna 只运行有界验证；数据库准备与 migration 由主代理负责，须先验证隔离名称。用户已有端口 5173/8765 的服务只读保留。

## 前置回执

Luna：preflight exit 0，Playwright 1.62.1、本机 Chrome 155.0.8059.40，一次 launch/close exit 0。5173 与 8765 已有服务，不属于本轮清理范围。日志：`output/playwright/reflections-content-20261013/preflight.log`。

## 当前状态

实现、必要修复、本轮技术验证及最终目录/引用/静态复核已完成。正常服务发布与真实模型验收未执行；它们不在本轮授权范围。


## 实现后复核

结论：**通过本轮技术交付复核**。需求、正式设计与实现对应；9 条页面旅程覆盖了来源选择、实际请求、事件、结果、报告/历史、再次分析及失败恢复。

- 默认任务继续原 Registry99 日记路径，全部旧操作描述保持原位置及 hash；新选择依赖精确 `dream.reflection-analysis-content.v1`，未发布时 fail closed。
- 候选只读当前挂载索引；正文仅在提交时读取。规范化页面标识去重，索引中归档页面排除；任一读取失败明确尚未创建，允许调整来源。创建结果未知才保留原 request_key/选项以恢复原回执，不再读取新版正文。
- Admin 原创建与私有输入写入共享事务，实际解析归属及启用的 Agent 指令；公开摘要无正文/prompt，后台加载只允许原 service/task。`schemaRequirements.ts` 独立持有物理 capability，避免通过 service 循环导入造成 undefined requirement。
- `diary_session_ids=null` 沿用全部日记；`[]` 明确不选日记。Notion 只使用独立引用，标题/安全 URL 进入 evidence，来源版本/读取时间/摘要保存在元数据。仅提供当前 Agent 指令，不改变模型、权限、插件、Runtime env 或工作区/TMPDIR 协议。
- 总按钮即时锁定，栏目 Analyze 删除而配置保留。选择变化仅影响下一次；断流或任务查询失败保留原任务。报告保存重试只 ensure 原终态任务，历史按 task_id 区分，保留部分失败栏目和 Notion 来源链接。
- 无正文由 engine 记录 FAILED 且不调用 Runner；页面使用同一安全错误文案提示选择有正文的来源，不保存空报告。默认、desired 页面选项、effective 固定任务输入各自独立；task revision 与 Notion 索引版本不同。

## 最终技术验证回执

以下是无模型调用的技术自动化。页面测试使用真实 UI、公开 API/SSE parser 与 staged boundary DTO；Admin 集成使用隔离 PostgreSQL、真实 production POST/receipt/UOW/repository，只注入 OAuth/service 身份边界。它们不是正常账户或真实模型业务验收。

日志根目录：`output/playwright/reflections-content-20261013/`。

| 验证 | 实际命令 / 工作目录 | Exit / 关键结果 | 回执 |
| --- | --- | --- | --- |
| 后端影响范围 | Dream: `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_reflection_analysis_content.py backend/tests/test_reflections_agent.py backend/tests/test_admin_reflection_task_data.py backend/tests/test_reflections_config_router.py backend/tests/test_notion_today.py -q` | 0；61 passed，8 subtests | final-contracts-receipt.log（实际工具回执摘要；本次 stdout 未单独保存） |
| 最后 capability 防御复测 | Dream: `PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_reflection_analysis_content.py -q` | 0；17 passed，2 subtests；重复/错 hash/revision 均拒绝 | final-content-focused.log |
| Admin 新旧合同 | Admin: `corepack pnpm exec vitest run app/lib/dream/reflectionAnalysisContent.test.ts app/lib/dream/reflectionAnalysisContentHandler.test.ts app/lib/dream/reflectionTaskDto.test.ts app/lib/dream/reflectionTaskService.test.ts app/lib/dream/reflectionTaskRegistration.test.ts app/lib/dream/reflectionTaskOperationCandidate.test.ts` | 0；6 files，59 tests；旧16项 descriptor 保持 | final-contracts-receipt.log（实际工具回执摘要） |
| Admin 持久化旅程 | Admin: `REFLECTION_CONTENT_PRIVATE_FIXTURE=<primary-owned-0600-manifest> corepack pnpm exec vitest run app/lib/dream/reflectionAnalysisContent.integration.test.ts` | 0；1 passed；同 key 同值恢复/异值409、越权404、Notion-only/实际 Agent、部分终态、同 task 唯一报告、公开重载 | final-admin-integration-r3.log |
| 前向 migration | Admin: `corepack pnpm exec tsx scripts/verify-reflection-analysis-content.ts` | 0；最终0081空库重放、旧prefix升级、重复、并发、漂移回滚全部通过；text nullable 与cap相符 | final-migration.log、final-migration-receipt.json |
| 页面完整旅程 | frontend: `E2E_WEB_BASE=http://127.0.0.1:59187 corepack pnpm exec playwright test e2e/reflections-analysis-content.spec.ts --reporter=line --workers=1` | 0；9 passed；桌面/窄屏、默认/Notion/Agent、SSE、保存重试/重载、部分失败、未知创建/双击/恢复、来源失效/当日选择、无正文FAILED | browser-final-9-rerun.log |
| Calendar 相邻回归 | frontend: `E2E_WEB_BASE=http://127.0.0.1:59187 corepack pnpm exec playwright test e2e/calendar-right-panel-tabs.spec.ts --reporter=line --workers=1` | 0；49 passed | final-validation-receipt.log |
| Chat 相邻回归 | frontend: `E2E_WEB_BASE=http://127.0.0.1:59187 corepack pnpm exec playwright test e2e/chat-first-deck-defaults.spec.ts --reporter=line --workers=1` | 0；1 passed，保留默认 Deck/Agent 选择流程 | final-validation-receipt.log |
| 类型/静态检查 | frontend 与 Admin: `corepack pnpm exec tsc --noEmit --incremental false`；frontend focused ESLint 与 spec ESLint | 0；无错误 | final-contracts-receipt.log、final-9-validation-receipt.log |
| 构建 | 隔离 frontend copy: `corepack pnpm exec next build --webpack` | 0；类型、编译、静态生成完成 | final-copy-build.log |
| 文档与差异 | scoped Markdown 引用、26个新增 .folder 路径、浏览器 Mermaid parse、两仓库 `git diff --check` | 0；无缺失；normal/error/state 均 parsed=true | docs-scoped-check.log、mermaid-browser-validation.log、final-9-validation-receipt.log、final-review-static.log |

### 失败与修复记录

首测和复测分别保存，不把失败覆盖成通过：

1. Python 未设 `PYTHONPATH=backend` 属于 import harness 前置失败；使用项目正确入口后回归通过。新 test 的 frozen DTO 构造与 string report_id fixture 按真实 DTO 修正。
2. Admin 新测试曾错误读取 candidate 字段；修正后还暴露实际 service/registry 循环加载缺陷。将 capability 放到现有 schemaRequirements 模块后，59 项合同通过。
3. 隔离 fixture 初次连接器/资源标识未用既有 UUID DTO；修正准备脚本。持久 fixture 复测通用 request ID 重用会正确返回 OPERATION_REQUEST_CONFLICT，改为每次技术验证独立 namespace，并在同一旅程显式复用 key 验证幂等，不修改业务规则或删除旧 fixture。
4. 创建前 Notion 读取失败误被前端按所有5xx保留为未知提交；服务器现明确 outcome_unknown=false。已提交或真正未知结果仍恢复原回执。
5. 相邻 Calendar 首测将明确的 Notion probe abort 算作意外错误；只在该 fixture lane、GET /api/connectors、ERR_ABORTED、Story Workspace referer 下分类。其他错误仍检查。Chat 旧断言使用过时中文标题；改为当前组件的 Claude Code Plugins 正式名称。两项完整复测通过，未改相邻产品功能。
6. 首个隔离 PG target identity 检查将 inet 文本的 /32 当作主机差异，改用 host(inet_server_addr())；随后原全历史0052数据门禁拒绝直接重放，harness改为调用既有0047/data、0049/data、0051/data真实迁移CLI，再由唯一 migrator继续。门禁和历史SQL未改。Mermaid Node 的 DOMPurify 前置不完整；使用浏览器解析三图通过。隔离 copy 的 node_modules 指向外部已安装依赖，默认 Turbopack 会拒绝越界 symlink；支持的 Webpack 构建通过。这个故障属于 copy harness，不作为页面缺陷或正常 Turbopack 构建结论。
7. 仅创建422的空正文页面 fixture 不覆盖真实 engine FAILED；新增第9条 CREATED→SSE FAILED、无报告旅程，修正文案复用后通过。

## 清理、工作区和交付边界

本轮创建的具名临时 PostgreSQL 集群（包括前置失败重试）均已停止并删除，私有 fixture/凭证也随目录移除；最终 migration 矩阵独立重跑并清理。59187 只由验证 runtime 使用，测试代理已停止精确自有 session 并确认端口清理。用户原5173/8765服务未操作。本轮 isolated frontend copy 已删除，原 node_modules 保留；清理事实见 cleanup-receipt.json。

基线46条路径中，4份共享目录合同只有追加本轮说明；其他源文件保留基线。执行期间3份既有 Notion 文档发生变化，本轮未写入或回退，保留当前状态供其工作复核：`docs/design/notion-session/connector-interaction.md`、`docs/prd/notion-session/resource-connector.md`、`docs/exec/notion-scheduled-sync-status-repair-20261013.md`。完整摘要为 baseline-final-review.json。变更前分区/报告设计已单独保存原文并从现行路径链接。

本轮不发布 migration、重启正常服务、部署或调用真实模型。新路径在正常服务中启用前，需要 Admin 发布0081及其精确 capability，并运行相应新代码；默认日记路径没有依赖全局最新 head。正式设计和 PRD 是已交付要求，测试回执只证明上述技术范围。
