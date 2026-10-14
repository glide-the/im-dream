<!-- [Input] 用户批准的 L2/L3 设计、当前源码和本轮验证回执。 -->
<!-- [Output] 实现范围、测试层级、真实账户检查点和可复查证据。 -->
<!-- [Pos] Reflections 记忆实现执行记录；不代替产品规则。 -->
<!-- [Sync] 2026-10-15: 建立实现、技术验证与真实模型验收记录。 -->
# Reflections L2/L3 实现与验收

优化提示词执行依据：在新分支中依次实现报告到 L2 文件、只读 Agent Tools、L3 固定主题与当前任务策略、现有 Settings 中的行为设置。复用生产入口；先隔离验证，再使用用户指定的已有账户及现有执行对象和模型验收。不合并、不发布，不修改无关数据或凭证。

## 业务对象与影响

| 对象 | 本轮影响 | 最终消费者 |
| --- | --- | --- |
| Project、Episode、canonical Story Artifact、Run `.dream` 发布、after-turn Hook | 不在范围；不能用它们替代记忆成功证据 | 原有 Story Workspace |
| Reflections Task、已保存报告及 `{deckId, agentId}` | 相邻回归；保留现有选择、执行、部分成功、报告历史流程 | 现有 Analysis/报告页面 |
| L2 `memory_distillation.md` | 新报告持久化后自动生成，保留来源和分析推断 | 两个只读 Agent Tools |
| L3 `memory_theme.md` | 绑定精确 L2 版本，由固定规则生成观察线索 | 当前任务策略执行器 |
| Behavior desired/revision | 由用户在现有 Settings 保存；本轮 immutable effective snapshot | 下一次 Agent 回应 |
| PostgreSQL/API 投影 | Admin Drizzle 新 capability 与 DTO；缺失时拒绝记忆域 | Dream Worker、私有 MCP Host、Settings |
| Chat、Gateway、Token 结算、正常 Admin 日志 | 真实模型验收沿正常服务路径写入，保留可复核记录 | 原有 Chat/管理后台 |

## 工作区

Dream 与 Admin 分支：`codex/reflections-l2-l3-20261015`。Admin 开始时无未提交改动。Dream 已有本轮设计文档，保留历史稿。Admin 在 `/private/tmp/ink-l2-l3-admin-20261015` 准备独立源文件，应用前检查实际仓库基线与只属于本轮的文件。

## 实现选择

L2 采用固定、保留来源的转换，不额外调用模型。报告结构已有 title、description、evidence、confidence、related_session_ids；按相同观察合并来源，不重新推断个人事实。L3 使用版本化的复合表达规则，单独关键词不触发；没有匹配时返回空记录。当前策略也不新增模型调用；只允许已发布行动，先检查当前表达、拒绝边界、开关和来源版本。此规则方案不冒充语义模型，对隐含表达的覆盖有限。

能力发布时起的新报告自动发现；历史报告本轮不批量改写或另起分析。技术测试与真实业务验收分开记录。

## 验证与检查点

- Admin staging：`pnpm exec tsc --noEmit`，exit 0；日志 `/private/tmp/ink-l2-l3-admin-tsc-20261015.log`。仅静态检查。
- 真实账户：用户指定邮箱 `dmeck@suoxya.com`；凭证仅用于正常登录，不写入证据。登录尚未尝试。
- 正常服务观察：Admin 当前监听 3000，正常 PostgreSQL 当前监听 54329；Dream 标准 8765/5173 尚未观察到监听。需启动既定正常入口，不能用替代 Gateway 或随机端口 Admin 冒充真实验收。
- 模型调用预算：最多一次 Reflections 三模式分析与三次正常 Chat 回应；实际模型、Deck/Agent 以正常账户现有配置读取并记录后调用。故障注入不在真实账本执行。

具体技术验证回执与正常服务检查点见下文；静态检查不声明功能或真实业务验收完成。

## 最终实现与验证结果

L2从实际COMPLETED栏目及冻结报告生成；已保留报告级Notion/Agent选择摘要，未虚构逐条原文引用。L3失败不阻塞L2；独立转换重试读取已发布L2，文件发布未知时恢复规范字节。设置、Thread内否认/重新允许、原回执、权限和源版本均有技术用例。固定规则尚未经过真实模型质量验收，不把它宣称为语义分类器。

| 验证命令 | 实际结果与层级 |
| --- | --- |
| `PYTHONPATH=backend backend/.venv/bin/python -m pytest -q backend/tests/test_memory_chain.py backend/tests/test_claude_agent_runner.py::TestClaudeAgentRunnerMcpDefaults::test_user_mcp_exposes_session_retrieval_and_thread_tools` | exit 0，30 passed；生产公开Settings入口/私有broker/转换/文件/反馈专项技术验证 |
| 较早八文件Python回归（Reflections/history/content/broker/Thread/context/Runner） | 325 passed、1 skipped、184 subtests；唯一旧目录断言失败已按新增三Tool修订，并在上述专项重跑通过。不是30+325条互不重复用例 |
| frontend `pnpm exec tsc --noEmit` | exit 0 |
| frontend `pnpm exec eslint`（四个实现文件、memory spec与calendarHarness） | exit 0，无错误或warning |
| Admin staging `pnpm exec tsc --noEmit` | exit 0；最终新DTO/SQL更新类型已检查 |
| `E2E_WEB_BASE=http://127.0.0.1:55173 pnpm exec playwright test e2e/memory-behavior.spec.ts --workers=1 --reporter=line` | exit 0，4 passed；桌面/窄屏、保存重开、未知回执、冲突、读失败恢复；无非预期console/page/API错误 |
| `e2e/reflections-analysis-content.spec.ts` | 邻接20条首次通过；today用例错误地修改报告保存时间，按实际task创建日固定clock后重跑通过，共21条通过。生产分析页面无修改 |
| Admin staging `node --import tsx verify-memory-isolated.ts` | exit 0；完整前向migration历史、来源→生产转换→真实私有文件→Admin ready、重复发现、跨owner拒绝、CAS/原回执通过。不是正常账户/model验收 |
| `node output/docs/reflections-l2-l3-design-20261015/validate-implementation-docs.mjs` | exit 0；30个Markdown、113个本地引用、3个Mermaid block，failures=[]；历史与跨仓库策略字节检查 |
| `node output/docs/reflections-l2-l3-design-20261015/chrome-mermaid-parse.mjs` | exit 0；实际Chrome解析sequence/sequence/stateDiagram，3/3通过。纯文档harness有1条generic 404，无page error，不算功能验收 |
| `git diff --check` | exit 0 |

全部回执保存在 `output/docs/reflections-l2-l3-design-20261015/`，关键日志为 python-final3.log、admin-staging-tsc-final3.log、playwright-memory-final2.log、isolated-migration.log、implementation-doc-checks.json、chrome-mermaid-result.json。桌面与窄屏截图分别为 memory-behavior-desktop-final2.png、memory-behavior-narrow-final2.png。狭窄视口截图捕获当前滚动位置，不假称完整页面高度截图。

## 正常服务与真实模型验收前置

本机正常Admin：公开issuer/origin为 `https://ink-admin.suoxya.com`，实际服务器传输为 `http://127.0.0.1:3000`。只读capability回执 normal-capabilities.json 显示：memory_schema_present=false、memory_operations=[]、exact_memory_ready=false。这是当前正常服务事实，不能用隔离库代替。

用户授权了真实模型测试并提供既有产品账户；本轮尚未尝试登录、尚未选择或调用模型，实际业务模型调用0次。正常Admin未发布能力前无法验收新链路；不会把已有分析单独运行或隔离假provider说成该链路通过。按根AGENTS的migration隔离与capability发布合同，本轮未向正常PostgreSQL运行migration、回填或改写历史，也未改变既有Admin/PostgreSQL服务。

待发布最小顺序：审核/发布Admin前向migration与精确capability、激活同一正常Admin操作注册，然后Dream消费此版本。随后使用指定账户及其既有Deck/Agent/模型，经正常可见入口执行一次三模式回顾、读取L2、开启行为设置后正常Chat验证，再核对正常Admin中的request/Thread/结算和失败恢复。预算仍最多一次三模式回顾与三次Chat；不创建影子账户/Deck/账本，不清理真实验收Run。此项尚未完成。

## 收敛评审与清理

保留两张共享表、小型后台worker、三个业务Tools和一个Settings栏目。无模式独立页面/Tool、确认弹窗、自由策略prompt、独立判定模型Thread或额外计数触发。历史批量回填、原文逐字核验和report_id精确UI深链是明确边界；首次使用在下一次回顾产生可用文档后生效。

已删除本轮命名的隔离数据库 ink_memory_l2_l3_qa_20261015，Luna仅停止其55173自有Next、文档56798自有server/Chrome context，8765没有本轮业务服务。原memory_tool.py保持HEAD字节，tsconfig.tsbuildinfo仅为验证生成物，在提交前恢复原字节。没有合并、推送、远程发布或正常模型账本写入。

精确schema requirement：`dream.memory.v1` v1，SHA256 `d08fae4c65a4ee448d64e80ebfcb371c2fbfb0a9fe1091825971c35756aacbc6`。对应Admin文件清单及逐文件摘要见 admin-applied.json。
