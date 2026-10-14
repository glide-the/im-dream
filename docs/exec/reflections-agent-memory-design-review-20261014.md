<!-- [Input] 用户授权、三份指定 Notion 资料及其相关子页、现行设计和本轮源码读取。 -->
<!-- [Output] 问题处理判断、证据索引、方案比较、设计评审、最小实施范围和文档检查回执。 -->
<!-- [Pos] 文档设计交付记录，不表示功能实现、真实数据/模型验收、合并或发布。 -->
<!-- [Sync] 2026-10-14: 完成资料核对、独立设计评审修订和文档/图示检查；未实施或验收功能。 -->
# Reflections 到 Agent Memory：判断与设计评审

> [Sync] 2026-10-15：本文保留上一轮完整判断和回执；报告内提取/个人事实库方案已被用户纠正，现行规则以[L2/L3修订记录](reflections-l2-l3-design-review-20261015.md)和其正式稿为准。本文资料证据仍可定位，旧评审通过不代表新方案已实现。

## 1. 问题处理判断与推荐方案

Reflections 三模式和报告流程已经存在，不重建分析系统。真正缺少的是**报告到持久个人记忆的业务转换、后续召回与修正闭环**，以及普通 Agent 可访问的业务 Tools。当前仓库没有已完成的正式跨会话事实记忆库，不能把新入口描述成单纯调用现有 Memory CRUD。

推荐：已保存单份报告 → 原报告页内提取与必要编辑 → 一次保存 → 同一回顾分析页查看、修正 → Agent 按任务召回。报告与候选仍可保留分析推断，进入记忆不代表成为确定事实。私人记忆属于认证用户，Deck/分析 Agent 只记录执行来源。

交付依次为：[产品规则与页面骨架](../prd/memory/reflections-agent-memory-prd.md)、[正式交互设计、Tools与业务图](../design/memory/reflections-agent-memory-interaction-design.md)、本文的符合性与反过度设计评审。所有新增能力均为建议、未实现。

## 2. 执行依据与边界

本轮用户已经提供完整 Optimized Prompt。Expert Prompt Architect 步骤将其作为一次可执行依据进行收敛，不递归优化：结合指定正文、现行 PRD 与源码证据，完成问题判断、最小交互方案、工具权限和设计评审；只保存文档，保留历史，不实施代码、schema、模型调用、真实数据写入、合并或发布。计划为并行发现 → 核心关系定义 → 少量方案比较 → PRD/正式图示 → 独立评审修订 → 文档检查。

开始时 `git status --short` 无输出，根 `AGENTS.md`、相关 `.folder.md` 和规则已读取。历史记忆仅定位 Reflections 内容/历史设计；当前结论来自本轮源码读取，不依赖旧验收结论。三个只读子任务分别负责 Reflections、持久记忆与 Tools 核对，没有执行模型或功能测试。

## 3. 指定资料与上下文证据

| 标号与资料 | 本轮实际读到的相关正文 | 采用与限制 |
| --- | --- | --- |
| N1 [临时记事本-10-14 / 指定锚点](https://app.notion.com/p/3f930b7547c380adb4def30db8c1f2e2#72130b7547c3824495fe01acc06d0ba6) | “iM的记忆系统与会话关联”、任务一/二：分析已实现，Deck 思维骨架缺个人信息上下文，缺 Agent 公开 Tool，需把分析模式输出处理为记忆 | 作为用户问题依据，不能当作实现证明。单独读取锚点返回类型 block、标题相同、空正文，相关文字在父页；父页有 truncated=true 和一个与本任务无关的 external_object_instance，未宣称整页完全读取 |
| N2 [0602沟通内容](https://app.notion.com/p/29a30b7547c3808b8d49f801bdce65d4) | “L1/L2工程图”“L3工程图”“后续沟通”：事实提取→检索蒸馏→情绪主题；检索/回应映射等待具体文档，也记录“先记住，再解释；先结构化，再上理论” | 是成熟思考和工程推进记录的索引，并非 IM 发布合同；正文含无关内容，未复制到本次文档 |
| N2a [三层记忆体系策略主题如何与角色行为连接讨论](https://app.notion.com/p/2ae30b7547c380aab75bf70d7860b077) | 第二节：社会层、特质层、深层情感主题；第三及第六节：抽取标签必须真正影响模型回应、哪些标签值得实现仍待收敛 | 内容分层与下面的处理阶段分别采用，不混为三个存储层 |
| N2b [三层记忆系统架构与情绪标注](https://app.notion.com/p/2b630b7547c3801e9991c517d94a1e2e) | L1 facts、L2 七类检索与 memory_distillation.md、L3 四主题/细分标签与 memory_theme.md | 明确各阶段实际输入输出；不把原文固定重复次数或文件结构继承为本项目规范 |
| N3 [设备的个人记忆系统前期沟通方案](https://app.notion.com/p/29c30b7547c380d3aec4cafc97f97df5) | “记忆风格指导提示词”“小云雀 USER”“Memory_dis”“Memory_theme”“动态上下文提示词模版”及后续日期记录 | 采用用户事实/角色设定分开、来源角色、摘要与按任务上下文使用；不采用旧设备/IP、图库、MQ和完整标签流水线 |
| N3a [情感主题建模可行性讨论](https://app.notion.com/p/2ab30b7547c38077a14bf7dd2ea059b7) | 事件摘要→二次主题提取；目标为被理解；指出接口梳理和召回映射未完成 | 作为“主张尚待验证”的证据，不宣称模型效果已成立 |
| N3b [主题回应策略MVP](https://app.notion.com/p/2b530b7547c3807a869ded024184f7b6) | 四主题的角色话术与场景示例 | 映射的思考可参考；强制打断等范例不变成 IM 通用行为 |

以上均经连接的 Notion fetch 读取。正文中的历史时间和工具返回的 as-of 时间只是来源元数据，不证明工程当前已落地；主文读取足够支持本次选择。未读取附件、图像内容、unknown bookmark 或它们引用的外部系统，因此不主张已验证全部心理标签/提示词。没有无法访问的指定主文；指定锚点的单独空 block 与父页中的上下文分别记录。

## 4. 当前实现证据

### 4.1 分析模式、输入输出和完整流程

| 核对项 | 当前代码事实与文件位置 |
| --- | --- |
| 模式与名称 | [reflections_config.py](../../backend/reflections_config.py) 319–377：echoes/traits/patterns；[i18n.ts](../../frontend/app/_dream/i18n.ts) 1328–1331：重复回响/性格折射/行为轨迹。旧文档译名不作为新的第四模式 |
| 三模式含义 | reflections_config.py 64–115、151–212、237–290：跨会话主题、有限材料中的特质推断、行为条件与例外；不能把推断当诊断，也不能因模式数拆三个 Tool |
| 共享输出 | [ReflectionResult](../../frontend/app/_dream/api/voiceApi.ts) 448–458 与 [ReflectionInsightInputDTO](../../backend/services/admin_data/reflection_task_models.py) 460–465：title/description/related_session_ids/evidence/confidence。默认 prompt 的3–6条不是业务限额，执行允许[] |
| 用户入口 | [现行分析内容PRD](../prd/memory/reflections-analysis-content-prd.md) 18–40；[AnalysisView.tsx](../../frontend/app/_dream/components/AnalysisView.tsx) 937–985：总分析、分析内容、原范围选择；不是历史独立 Analyze 方案 |
| 冻结来源/Agent | [reflections.py](../../backend/routers/reflections.py) 424–471；[reflection_analysis_content_data.py](../../backend/services/admin_data/reflection_analysis_content_data.py) 30–99：提交时读取 Notion 正文，冻结 `{deckId,agentId}` 的 Agent prompt。Deck 是分组，Agent 是执行视角 |
| 执行与原文读取 | [reflections_agent.py](../../backend/reflections_agent.py) 299–309、323–401、444–575、648–747：任务 workspace、section Thread、生产 RunRequest/Factory、冻结范围 broker、最终 assistant 文本解析；不是再次遍历全部实时来源 |
| 终态与保存 | reflections_agent.py 703–712、800–831：COMPLETED/PARTIAL_FAILED/FAILED 与 report ensure；[reflections.py](../../backend/routers/reflections.py) 569–584：公开报告保证保存，不重跑模型。恢复跳过已完成和已失败栏目，不称“自动重试所有失败” |
| 未知创建与重开 | [voiceApi.ts](../../frontend/app/_dream/api/voiceApi.ts) 658–702、756–863；AnalysisView.tsx 103–148、645–688：原 request_key、原任务、lastEventId。CREATED 不在进入页面时自动启动 |
| 历史阅读 | [reflectionHistory.ts](../../frontend/app/_dream/components/reflectionHistory.ts) 7–39；[现行历史PRD](../prd/memory/reflections-history-prd.md) 13–32：字符串bigint ID、真实创建时间、原最近三份与时间轴，共用 ReflectionBlogPage |
| 报告阅读复用 | AnalysisView.tsx 2056–2104、2165–2179、2233–2353：三栏目、列表、详情、滚动及报告级来源摘要 |
| 不可冒充的来源入口 | AnalysisView.tsx 2351–2362 的 Related Notes 仍为占位；reflections_agent.py 871–894：Notion item page IDs 只校验并追加至 evidence，未结构化保存。报告级page集合不等于逐条来源 |
| 精确报告缺口 | [reports.py](../../backend/routers/reports.py) 55–105：只有recent/history/save；无按report_id detail。现有 Chat 标签仅打开最新匹配栏目，不能作为指定来源返回 |

### 4.2 Memory 能力与归属

| 核对项 | 当前代码事实与文件位置 |
| --- | --- |
| 程序性工作区 | [memory_workspace.py](../../backend/libs/claude_agent_kit/server/memory_workspace.py) 13–39、156–214：提示词/状态，不是长期摘要桶；[context_builder.py](../../backend/claude_agent/context_builder.py) 546–564：发现目录后注入文件清单，普通 Chat 不创建正式记忆 |
| 默认更新规则 | reflections_config.py 134–140、221–226、308–312：NO_CHANGE，不负责向用户事实库写入 |
| Agent配置区别 | [voice_data.py](../../backend/services/admin_data/voice_data.py) 34–58、81–115 接受 memory_workspace_config；[chat_context.py](../../backend/services/deck/chat_context.py) 67–75、132–180 只投影 Agent system_prompt；配置不是用户记忆 |
| 私人信息不能随Deck发布 | [Admin deckVoiceRepository.ts](../../../ink-admin-memory/app/lib/dream/deckVoiceRepository.ts) 75–115：配置随复制/内容快照转移。记忆应 user-owned，不能写入该字段 |
| Mem0存根 | [memory_tool.py](../../backend/libs/claude_agent_kit/server/memory_tool.py) 43–102：gateway/search 被注释；[agent_runner.py](../../backend/libs/claude_agent_kit/server/agent_runner.py) 2113–2159：默认关闭，需要精确allowlist；有 Tool 名称不等于正式检索能力 |
| 当前schema合同 | [Admin current-catalog.json](../../../ink-admin-memory/drizzle/contracts/current-catalog.json) 15–64 未列正式个人记忆表；[dream.ts](../../../ink-admin-memory/packages/db/src/schema/dream.ts) 535–570 仅配置字段。这里只读源码合同，没有验证正常数据库部署 |
| voice-memory.resolve | [deckRuntimeDataRepository.ts](../../../ink-admin-memory/app/lib/dream/deckRuntimeDataRepository.ts) 87–98：读取提示词配置，Dream生产没有消费者，不是正式记录检索 |
| UI可复用限制 | [FileSidebar.tsx](../../frontend/app/_dream/components/dashboard/FileSidebar.tsx) 120–215 只有文件操作；[DeckEditorModal.tsx](../../frontend/app/_dream/components/DeckEditorModal.tsx) 20–47 没有Memory栏目。没有现成的记忆记录编辑器可直接宣称复用 |

### 4.3 Tools、注册与权限

| 核对项 | 当前代码事实与文件位置 |
| --- | --- |
| 内置协议 | [mcp_server.py](../../backend/libs/claude_agent_kit/server/mcp_server.py) 31–61：stdio MCP，get_sessions_range + THREAD_TOOL_SPECS，call_id 来自传输；[thread_tool.py](../../backend/libs/claude_agent_kit/server/thread_tool.py) 22–169：实际六个 Thread Tools，头部旧“五个”不准确 |
| 已有日记读取 | [sessions_tool.py](../../backend/libs/claude_agent_kit/server/sessions_tool.py) 66–143、316–399：日期/query/labels检索；vector不可用，auto可降fuzzy；不能冒充报告/记忆检索 |
| 六个Thread Tools | create_scheduled_task/create_thread/list_threads/read_thread/send_message_to_thread/wait_threads；读消息和等待 Thread 不等于读报告或等待 reflection task |
| 私有broker | [session_projection_broker.py](../../backend/services/admin_data/session_projection_broker.py) 149–281；[turn_persistence.py](../../backend/services/admin_data/turn_persistence.py) 224–625：strict DTO、绑定主体/Thread、exact capability，不存在通用数据隧道 |
| 子进程边界 | agent_runner.py 2201起：仅私有broker字段和检索policy进入user stdio；不传Admin凭据、actor或浏览器自定义env |
| 写收据及未知结果 | [claude_agent.py](../../backend/routers/claude_agent.py) 2240、2305–2314、2416–2428：源消息与call_id绑定幂等，超时不证明未提交 |
| 现有Tool许可 | agent_runner.py 3331–3383：既有guard和确认协议；新增工具还需domain权限校验，不能借full access绕过 |
| 分析worker特殊范围 | reflections_agent.py 533–539 使用空managed MCP snapshot；[reflection_task_runtime.py](../../backend/services/admin_data/reflection_task_runtime.py) 44起限定snapshot Session。新增记忆写Tool不直接塞进分析child Thread |

## 5. 少量方案比较与选择

| 方案 | 复用与使用成本 | 新增复杂度和决定 |
| --- | --- | --- |
| A. 报告页内提取+同页记忆查看 | 用户已在判断分析结论，报告ID和上下文明确；最少入口转换 | 仍需真实持久记忆/来源/回执，但无需新分析或向导。选为主路径 |
| B. 分析完成自动写全部结论 | 少一次操作，但未知用途、推断/变化/冲突被自动扩大为事实 | 改动分析终态、权限与失败恢复，难以解释误记。排除；完成后提供A同一入口 |
| C. 普通Agent按任务提取与召回 | 复用MCP/broker、报告和生产Agent执行；已有报告可供主动处理 | 必须新业务Tools与DTO，不能用任意文件写代替持久库。与A共用服务，选为Agent路径 |
| D. 按模式/Agent/理论层建立独立记忆页面和库 | 接口和页面数量增加，用户需先理解分类与归属 | 没有当前任务依据且容易随Deck复制私人信息。排除 |

选择A+C，不改变现有分析任务状态。四个建议 Tools 为 `get_reflection_reports`、`prepare_reflection_memory`、`save_agent_memory`、`search_agent_memory`。之所以保留报告read，是为了Agent能在未知report_id时主动找现有分析；save承担提取提交和记忆修正，避免再添第五个单独更新Tool。

## 6. 目标符合性与反过度设计评审

| 检查 | 修订后设计结论 |
| --- | --- |
| 1. 实际入口 | 已指定保存报告的操作区、正文内候选和一次保存；来源报告不靠“最新”跳转猜测 |
| 2. 用户和Agent | 同一业务服务覆盖页面闭环与四Tool任务，不复制保存状态机 |
| 3. 资料准确性 | 内容分层与处理阶段分开；不套短期/长期/程序性“三层”，不沿固定次数/旧IP策略 |
| 4. 复用 | 保留原分析、报告、历史、Agent执行和broker；没有正式记忆库则明确必要前置，不能虚称CRUD已有 |
| 5. Tools必要性 | 模式是来源参数；报告/提取/写入/召回副作用不同，四个职责独立，不把不同实体塞一个万能Tool |
| 6. 可删除复杂度 | 删除独立站点、步骤向导、逐模式Tool、Agent归属选择、全量自动注入、批量保存和统一确认；仅新增有业务必要的持久操作/版本 |
| 7. 完整恢复与修正 | 原key核对未知、原operation重试、版本冲突不覆盖、草稿同步、重开、停用抑制和精确来源返回均有定义 |
| 8. 状态准确 | 既有实现引用源码；所有新增接口/图中模块标建议未实现；验收矩阵只列后续标准 |

本轮收敛中已直接消除的错误方向：不把 `memory/` 和 Mem0 存根当正式事实库；不把 Deck/Agent 配置当私人记忆目标；不把两个“三层”定义合并；不将 Notion报告级摘要当逐条引用；不把旧 Chat 的最新栏目跳转当来源报告精确返回；不让模型伪造人工选择字段。

独立评审指出的缺口已直接修订：保持左封面/右栏目列表、下方详情与底部播放器的原报告布局；补同页停用管理与reactivate；区分纯重复和可add_source的重复；prepare.read支持原key，save.read_receipt独立恢复修正回执；首次key绑定复用原服务器request_id；空收据不消除未知；草稿和提交均CAS；正常图明确先running后后台执行/read；推断/冲突的选择必须由认证页面绑定，不接受模型确认字段。四个Tools数量保持不变。

独立复核：Reflections评审确认原布局、停用恢复、来源补充和原key读取四处合同已闭合；Tools评审确认跨调用收据、未知结果、草稿版本、异步执行、用户选择绑定和模型重启边界均已落实。其复核指出的报告ID示例超出bigint边界和停用读取措辞已直接修正。设计可作为后续实施依据，必要前置仍是Admin已发布能力；不表示功能或业务验收完成。

## 7. 最小实施范围与证据缺口

只实施单报告候选、user-owned记忆/版本/来源、四Tool与公开业务服务、原报告区域和同页列表详情、精确报告读取、原key恢复。前置为 Admin Drizzle migration/capability、严格DTO与事务；正常数据库部署、模型效果和真实账户旅程另行验证。

尚需实施合同收敛：来源原文的授权/版本读取；用户对推断/冲突选择与服务端请求绑定；后台claim恢复与模型调用控制；实际检索与去重质量。未读取附件与心理标签细节不影响第一版报告到记忆闭环，但不足以实现完整情绪策略系统。

## 8. 实际文档检查

以下由 `luna_test_runner` 在本仓库执行，主任务读取实际日志后收录。只检查文档，不表示功能或真实业务通过。

| 实际命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `node output/docs/reflections-agent-memory-20261014/chrome-mermaid-parse.mjs` | 0 | 本机Chrome与Mermaid 11.17.2实际解析3/3图：sequence、sequence、stateDiagram；无page error |
| `node output/docs/reflections-agent-memory-20261014/validate-docs.mjs` | 0 | 12个变更Markdown、58个本地引用、三新文件头与目录登记、两稿桌面/窄屏骨架及三图全部通过；只有docs变更 |
| `git diff --check` | 0 | 无空白或补丁格式错误 |

正式稿最终解析的SHA-256为 `96ef8ff6d48361f98941cf1c7b0e22dfd7718865197672ae892ba5e82d199681`。记录这次哈希只为匹配图示解析版本，不是功能交付标记。原有四份相关历史文稿存在且未删除/覆盖；现有文稿采用增补说明，保留旧正文。

首次Node解析stateDiagram出现 `DOMPurify.addHook is not a function`，是文档解析harness问题；首次file模块Chrome尝试也未执行。失败日志保留，随后使用具名Chrome临时profile和随机loopback端口完成实际解析，不能把失败尝试计为通过。最终回执为 `chrome-mermaid-parse-final.log`、`validate-docs-final.log` 和 `validation-summary.json`，均在 `output/docs/reflections-agent-memory-20261014/`。

本轮Chrome profile、loopback服务及临时根目录已清理，脚本/回执保留；未启动或修改用户正常Dream/Admin/Gateway，未连接或写入业务数据库。收录本节后仅重做Markdown/差异检查，正式图稿不再变更。
