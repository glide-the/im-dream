<!-- [Input] 用户专项授权、五个本机项目源码、现行图片设计和本轮工作区基线。 -->
<!-- [Output] Expert Prompt Architect执行提示、双钻石计划、调查、独立评审修订及本轮验证回执。 -->
<!-- [Pos] 主对话与独立图片模型分工专项执行记录，不替代现行PRD或正式设计。 -->
<!-- [Sync] 2026-10-11: round23-25 unchanged normal image-turn capability satisfies blocked audit; preserve corrected Dream OAuth evidence and completed Runtime publication. -->
<!-- [Sync] 2026-10-11: 保留逐轮历史；当前两条源码路径接通，fresh技术验证与真实验收限制分别记录。 -->
# 图片模型选择与调用分工：执行记录

2026-10-11 round26 恢复执行：用户明确授权 Admin 受控发布正常本机库缺失的 image-turn capability，并核对、同步实际 OAuth 客户端的 images:create scope。以下历史 blocked 状态保留为当时回执；本轮按新授权恢复发布与完整真实业务验收，目标工具的历史 blocked 状态不代表用户要求停止。

当前状态：两种模型选择、四项能力、服务器互斥、真实ID、内置图片结果与原文件/历史边界已在源码接通。用户在此前blocked审计后提供现有账户并明确授权Runtime验证后的生产发布，当时目标恢复active。Runtime0.1.11已完成同源四平台资格、五包生产发布、公开字节校验、本机精确安装及正常后端采用。完整正常图片真实验收仍未完成：正常数据库精确image-turn capability在恢复后的round23–25连续缺失，本轮阻塞审计通过，完整目标为blocked，不能标complete。实际Dream邮箱入口在round24返回OAuth客户端images:create拒绝，未建立本机会话；Admin管理身份的邮箱拒绝不能判断Dream密码有效或无效。下列round1–24均为当时快照；round23关于账户凭据及公开认证origin的泛化判断已由round24纠正，不能当作当前设计或最终通过声明。现行规则以[正式设计](../design/claude-agent/image-model-call-division.md)为准，最新命令与未验证项见本文末尾round25回执。

## Expert Prompt Architect

**角色**：Ink & Memory架构与产品工程负责人；主执行者负责实现、真实业务验收和正常服务操作，独立评审与Luna负责各自限定范围。

**上下文**：复用当前聊天“实现主对话与 image_gen 模型分工”（`01a125f2-f97e-7d33-8859-8b7676ee5688`），既有图片任务“调研并设计 Tool 图像生成交互”（`01a116cd-51e2-79b0-af95-db07ad5cfae9`）和Admin“Image 模型中心：调研、设计、实现与验证”（`01a120ae-3bb0-7432-88a2-4755ecb4275a`）是来源，不重复创建任务。当前聊天自动目标覆盖调查、设计、独立评审、实现、修订与验证；不因技术测试通过而缩小目标后宣称完整完成。

**任务**：分别核实Messages至上游Responses与独立Images的请求、资格和结果协议。为设置页增加独立Image选择，并公开准确的主对话生成/编辑标记。用户普通图片需求只允许已支持的主对话内置能力，明确要求image_gen时只用保存的Image模型；名称讨论与上传/草图不触发图片调用。建立失败反馈、文件/调用身份/历史关联。先写业务PRD和正式稿，基于实际稿独立评审并修订后再实施最小范围。

**约束**：读取各项目合同；保护已有未提交改动。Schema只由Admin Drizzle管理，现有偏好可复用，不执行migration或runtime DDL。没有自动模型选择、接口回退、双路生成、额外确认、环境分支或控制通道。不能把视觉输入、OpenAI身份或模型勾选当成内置工具兼容。建议与未验证行为逐项标明。不询问用户；缺少指定真实账户/实体/模型时记录限制并继续技术工作。

**交付**：专项[PRD](../prd/chat/image-model-call-division.md)、[正式设计](../design/claude-agent/image-model-call-division.md)、源码路径/符号/行号、独立评审问题及修订、本轮完整命令/退出码/关键输出、跳过及具体限制、目标实际状态。

**验收**：覆盖目录到设置保存/刷新到两项分别生效；Images生成/编辑、图像访问、会话保存重开、草图发送；模型与结果失败、连接/取消/重试及原文本工具媒体。确定性检查与隔离可见浏览器旅程委派luna_test_runner，读取原始日志；真实验收走指定真实身份的正常Dream/Admin/Gateway/PostgreSQL并保留Admin可查询回执。完整主对话Responses图片链路未实现或未验收时，目标不得标为完成。

以上即本轮Optimized Prompt；Optional Enhancers不增加未经要求的功能。

## 双钻石计划与当前状态

1. 发现：读取合同和基线，独立调查CLI/Codex与Admin，核实已有UI/Host/持久化；真实CLI配合隔离假Gateway验证server图片扩展的可行性。
2. 定义：明确AI与Image用途、素材与意图边界、default/desired/effective、公开能力与调用资格，以及完整链路缺口。
3. 发展：写专项正文骨架和正常/异常/状态图；独立评审实际稿；先修订设计再改代码。
4. 交付：实施可证实范围，保留内置图片执行的明确能力门禁；重跑完整隔离旅程与受影响回归，修复失败；记录正常服务真实验收缺失输入。仍缺源码或必需验证时目标保持active。

工作区基线已复制至`/tmp/im-image-model-split-20261010/baseline-im`和`baseline-admin`，包含原diff、未提交文件副本和SHA-256。没有重置、提交、推送或重启用户服务。Admin缺少Agent.md/CLAUDE.md/docs/rules/README.md，读取AGENTS.md及相关Cursor/目录合同；三个参考项目根合同缺失，以现有README与具体源码为依据。

## 初期调查快照（内置接入前，保留当时事实）

| 链路/边界 | 当前实现与最小处理 |
|---|---|
| 主对话实际协议 | Claude Code恢复版`queryModel`调用`anthropic.beta.messages.create`，[claude.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1822)；实际模块顺序为IM→CLI→Gateway `/v1/messages`→仅适用的Responses adapter→上游`/v1/responses`。generic OpenAI仍用Chat，不按Key或名称猜。 |
| 工具声明/输出 | Admin `responseTools`只声明function，[responses-adapter.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/responses-adapter.ts:126)；`responsesResponseToOpenAIChat`/`ResponsesToOpenAIChatStreamState.push`没有内置图片结果转换。新增声明仍不能闭合结果、身份、文件与计费。 |
| CLI/SDK结果 | CLI保留未知server内容，`query`只执行tool_use；SDK Assistant parser会丢弃未知图片result，raw StreamEvent可透传。候选是明确server图片扩展协议和Dream raw适配器；属于建议，未实现，须验证真实CLI重放，不伪装普通本地工具或advisor结果。 |
| 独立Images | `ImageGenerationProvider.generate`→`image_gen_stdio`/broker→Admin Images生成JSON或编辑multipart，原工具输入、toolCallId、broker requestId与发布文件匹配；本轮另保存实际Gateway req_请求身份。[images.py](../../backend/services/admin_gateway/images.py:108)。源码已实现。 |
| 四种能力 | `capabilities.image_generation/image_edit`及`endpoint_availability.images`只表示独立Images。主对话内置能力未实现，不得映射这些字段为AI标记。采用单独`endpoint_availability.responses_image`，当前generation/edit/configured/callable均关闭。 |
| 发布/资格 | Admin已发布模型、images生成/编辑、配置、订阅权限/余额和endpoint callable分别表达；修订前Dream只公开聊天模型且丢弃Images字段；本轮BFF已公开两类事实，前端分开AI与Image列表。 |
| 默认与保存 | AI维持Admin可调用default；Image没有独立公开default，初始未选择，不复用AI default或服务器env自动回退。保存失效alias仍展示并要求用户重新选择。 |
| 保存协议 | 复用`user_preferences.system_config_json`；原十字段patch合同冻结，追加严格`user-system-config.patch-image-model`操作，保留旧descriptor/hash和JSON数字类别，不增表。 |
| 图片与历史 | Service `_complete_image_results`使用真实工具身份/Host登记结果补齐workspace图片引用；`AdminAgentTurnPersistence.persist_assistant`保存原parts；ChatMarkdown/WorkspaceImage负责查看下载，重开读取原引用。内置图片尚无这组关联。 |
| Codex参考 | 当前CLI测试要求namespace imagegen存在而hosted image_generation不存在；存在Responses ImageGenerationCall类型不等于默认启用。`responses_lite.rs:673`、`models.rs:1217`。不能将参考源码写成IM或本机客户端验收。 |

官方依据：[视觉输入](https://developers.openai.com/api/docs/guides/images-vision?api-mode=responses)、[图片生成](https://developers.openai.com/api/docs/guides/image-generation#responses-api)。Responses使用主对话模型、内置工具与image_generation_call结果；Images直接选择图片模型。这里仅引用协议区别，模型名称不作为能力判断。

### CLI、SDK与参考实现的具体源码证据

以下为本轮研究者已读取的源码事实；恢复源码不是当前安装二进制的执行回执，运行时观察另见CLI隔离探针。

| 路径/具体符号 | 事实与边界 |
|---|---|
| [claude.ts / queryModel paramsFromContext:1699](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1699)、[queryModel:1822](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1822)、[executeNonStreamingRequest:864](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/api/claude.ts:864) | 构造model/messages/system/tools/tool_choice/max_tokens/thinking；流式与非流式均走anthropic.beta.messages.create，不直接发Responses。 |
| [messages.mjs / Messages.create:51](/Users/dmeck/project/claude-code-sourcemap/restored-src/node_modules/@anthropic-ai/sdk/resources/beta/messages/messages.mjs:51)、[api.ts / toolToAPISchema:119](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/utils/api.ts:119) | 实际Messages endpoint为/v1/messages?beta=true；工具为name/description/input_schema。 |
| [query.ts / msgToolUseBlocks:829](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/query.ts:829) | 仅tool_use加入本地streamingToolExecutor，不把server_tool_use作为本地工具执行。 |
| [claude.ts / queryModel内容块default:2039](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/api/claude.ts:2039)、[messages.ts / normalizeContentFromAPI:2747](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/utils/messages.ts:2747)、[QueryEngine.ts / includePartialMessages:818](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/QueryEngine.ts:818) | 未识别块被保留；partial messages转发message.event。这里只能推断可设计明确扩展，不能宣布图片全链路已支持。 |
| [message_parser.py / parse_message:168](/Users/dmeck/project/ink-dream-memory/backend/.venv/lib/python3.12/site-packages/claude_agent_sdk/_internal/message_parser.py:168)、[server内容分支:194](/Users/dmeck/project/ink-dream-memory/backend/.venv/lib/python3.12/site-packages/claude_agent_sdk/_internal/message_parser.py:194)、[StreamEvent:343](/Users/dmeck/project/ink-dream-memory/backend/.venv/lib/python3.12/site-packages/claude_agent_sdk/_internal/message_parser.py:343) | assistant只收集列出的类型，接收server_tool_use，但server result只有advisor_tool_result；未知图片结果丢弃。raw StreamEvent.event原样保留。不得将图片伪装成advisor结果。 |
| [models.rs / ResponseItem::ImageGenerationCall:1217](/Users/dmeck/project/codex/codex-rs/protocol/src/models.rs:1217)、[responses.rs / process_responses_event:353](/Users/dmeck/project/codex/codex-rs/codex-api/src/sse/responses.rs:353)、[responses_lite.rs / non_lite_uses_standalone_image_generation_by_default:673](/Users/dmeck/project/codex/codex-rs/core/tests/suite/responses_lite.rs:673) | 有图片结果类型和done解析；默认测试断言standalone imagegen存在、hosted image_generation不存在。这是参考源码/测试合同，本轮未运行Codex该测试，不代表IM或客户端已兼容。 |

## 初期影响与测试矩阵（接入前快照）

| 场景 | 验证方式与预期边界 |
|---|---|
| Admin能力/目录到两类列表 | Admin models及适配测试、Dream catalog/BFF严格校验、可见设置浏览器；内置资格关闭且不误标Images。 |
| 两项保存/刷新/失效恢复 | 新操作合同/codec/认证/授权/receipt，设置独立PATCH与刷新回读；不接受身份/路径/凭证。 |
| 主对话普通生成/编辑 | 当前不支持的反馈与零Images回退；成功Responses内置生成/编辑仍缺声明、结果、文件/计费完整实现。 |
| 独立生成/编辑到文件/消息重开 | 公开HTTP入口与生产Service，限定fake SDK/provider/storage；隔离技术验证。 |
| 草图/上传→发送→理解或编辑 | 本机Chrome可见画布/添加/发送，PNG同文件视觉块及编辑multipart/原图保留；fake推理不证明真实理解。 |
| 失败/取消/连接与兼容 | 原Host/Service/文件/transport回归，以及保存/目录错误可见恢复。 |
| 真实完整业务 | 缺少本轮用户指定现有真实账户、已有Thread/Deck和两个模型，不询问、不用影子数据；不执行正常数据库写入。 |

独立评审、实际修改及本轮回执将在执行后追加。旧图片/草图回执仅作为设计依据，不算本轮验证。

## 独立评审修订（实施前）

评审者admin_image_research基于实际专项稿，提出并先修订：R1新Image写合同必须尾部追加，不能改变冻结Registry前缀；Service重解析须选新DTO。R2先Dream兼容旧/新endpoint形状，再Admin公开字段，避免旧客户端目录失败。R3真实CLI探针的raw事件和历史保留不等于正常turn成功，两轮执行错误明确记录。全部修订已写回正式稿；最终评审结论待回执。

独立评审最终结论：选择、目录资格与明确反馈子范围可实施，完整专项仍不可完成。R4补齐各类Image资格原因/恢复映射，R5明确Service配置到只读Provider alias与下一turn生效，R6明确workspace/images:create是工具可用的既有条件。正式稿已先完成六项修订。

## 交付钻石补充：当前提示与验证调整

**Expert Prompt Architect补充**：仍以原专项角色、用途、单一路径、真实/隔离边界和完整目标为准。新增事实：独立评审识别Gateway请求身份由Admin createPlatformId("req")生成，不能以UUID假报文验证；当前Admin配置到目录的可见链路尚未在本轮重跑。任务是先按真实ID合同修订协议和fixture，再重复受影响确定性和完整可见旅程，同时复用既有Admin Image模型中心E2E。约束是只用新建、命名、已验证身份且可删除的隔离PostgreSQL和自有端口；不要改正常服务、全局ID、Drizzle Schema或既有业务算法。验收必须保留原错误轮次与新命令退出码，不能用上轮假阳性宣称真实兼容。

**调整计划**：主执行者修订ID合同并启动原命名隔离PG harness；Luna执行重跑与Admin可见E2E；主执行者读取回执、修复失败、同步文档并完成文档检查。真实账户与Responses成功路径仍不由隔离回执补足。

## 选择子范围实现与独立复审（round5快照）

| 实际修改 | 关键源码与职责 |
|---|---|
| 独立两项选择 | [ModelConfigSection](/Users/dmeck/project/ink-dream-memory/frontend/app/_dream/components/dashboard/ModelConfigSection.tsx:296)分别PUT对应字段，精确回读确认；未知提交提示核对，禁用选择，只重新读配置。复用原单选布局，无确认弹窗。 |
| 目录分离与兼容 | [gatewayModelsApi](/Users/dmeck/project/ink-dream-memory/frontend/app/_dream/api/gatewayModelsApi.ts:96)、[GatewayModel](/Users/dmeck/project/ink-dream-memory/backend/services/admin_gateway/models.py:73)和Admin [models](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/models.ts:288)区分Images与Responses事实、能力/准备/资格；旧文字模型兼容，旧Image-only未声明chat也不进入AI/default/save/实际resolver。 |
| 偏好存储与回执 | [system_config](/Users/dmeck/project/ink-dream-memory/backend/routers/system_config.py:275)校验对应资格，[严格新操作](/Users/dmeck/project/ink-dream-memory/backend/services/admin_data/system_config_data.py:196)和Admin [DTO](/Users/dmeck/project/ink-admin-memory/app/lib/dream/userSystemConfigDto.ts:32)尾部追加；原十字段patch不变，未知结果按原operation/request查receipt，不重发。原JSON大整数/负零/未知键保留。 |
| 工具选择绑定 | [Service](/Users/dmeck/project/ink-dream-memory/backend/claude_agent/service.py:2284)绑定本turn读取的image_model，[Provider](/Users/dmeck/project/ink-dream-memory/backend/services/admin_gateway/images.py:100)仅检查该alias和当前操作，移除环境、AI默认、单个候选回退。工作区、权限与原执行语义保留。 |
| 图片身份与历史 | [Images执行](/Users/dmeck/project/ink-dream-memory/backend/services/admin_gateway/images.py:145)读取实际x-request-id，按Admin createPlatformId("req")合同校验；[协议](/Users/dmeck/project/ink-dream-memory/backend/libs/claude_agent_kit/server/image_generation_protocol.py:17)另存gatewayRequestId。沿原工具output与消息parts保存，新图引用仍由原Host登记/文件归属校验生成，旧结果可缺该字段。 |
| 未支持内置结果 | Admin [Responses转换](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/responses-adapter.ts:196)对native JSON与SSE明确失败，不能静默丢图。当前内置声明/完整转换未实现，目录仍关闭。 |
| 用途规则 | 原context_builder与image_gen_stdio说明普通需求、明确工具需求、名称讨论和素材的区别；仅属模型执行规则源码，不当作真实语义或强制互斥的证明。 |
| 可见隔离旅程 | 新Settings和public Chat浏览器spec复用生产组件、transport、公开路由/DTO/Service/broker；SDK/Provider/Admin存储为注入边界。图片从Provider响应经过Host生成文件，无前端拼图或假最终SSE。 |

独立复审新增修订：R7旧Admin Image表单缺chat:false会混入AI，已统一各准入边界并保留旧文字兼容。R8响应字段存在null不能冒充缺省，已严格拒绝。R9工具输出原先只保存broker身份，现另保存实际Gateway身份并验证历史。R10网络保存回执丢失可能已提交，已改未确认状态及只读恢复。R11主执行者初版误把Gateway请求ID当UUID，独立评审以repository.createPlatformId与实际response Header发现P1；已按req_32hex合同修复，同时改隔离fake报文并补UUID/短ID拒绝。最后只读复审确认这些子范围没有新P1/P2；必需新测试仍以修复后回执为准。

未改Runner、ThreadFactory、资源策略算法、EventBus、SSE公开协议、恢复/取消状态机、部署环境分支或正常数据库。本轮没有新增Drizzle migration、Dream DDL、SQLite fallback、控制通道或发布操作；原工作区其他未提交改动完整保留。

## 实际CLI隔离协议探针

本轮安装CLI而非恢复源码的模拟执行。最终命令：

```sh
PYTHONPATH=backend:. perl -e 'alarm 60; exec @ARGV' backend/.venv/bin/python /tmp/im-image-model-split-20261010/cli-probe/run_probe.py
```

退出码0。隔离Gateway收到两次POST `/v1/messages?beta=true`，新会话1条message、resume 3条；实际tool声明仍为Claude普通工具。server_tool_use image_generation与图片result及普通最终文本能保留在CLI transcript，两轮ResultMessage为success/is_error=false/end_turn/errors=[]；session为412181dd-4d82-44b6-9695-a9d2ebbaf043，没有Images或本地图片工具调用。

[原始小回执](/tmp/im-image-model-split-20261010/cli-probe/rerun/probe-receipt-rerun.json)、[退出码](/tmp/im-image-model-split-20261010/cli-probe/rerun/probe-rerun.exit)与[原始transcript](/tmp/im-image-model-split-20261010/cli-probe/rerun/config-home/projects/-private-tmp-im-image-model-split-20261010-cli-probe-rerun-thread-fixture/412181dd-4d82-44b6-9695-a9d2ebbaf043.jsonl)保留。这里只证明CLI接受这组完整报文及session恢复，假Gateway并不证明真实Responses转换、图片发布或计费。首次缺普通终态文本时，两轮error_during_execution原回执保留；此前timeout命令缺失127、tee目标目录未创建的前置失败也不隐藏，不计通过。

## 本轮迭代回执与错误保留

所有确定性与隔离浏览器命令由luna_test_runner执行，主执行者已读取原始exit/out。

| 轮次 | 本轮实际结果 | 处理 |
|---|---|---|
| round1 | Dream pytest exit1，168通过1失败；Admin77 tests exit0；Admin tsc exit2；frontend tsc/8契约exit0 | 修fixture capability长度及GatewayError type；前缀验证脚本初次错误修后exit0，261原operation完全一致，新尾部hash两项目匹配。 |
| round2 | Dream169、Admin77、两tsc、8契约exit0；Chrome一次启动检查exit0，154.0.8037.98；浏览器exit1，8通过1失败 | Vite fixture页面前缀吞掉.js请求，属于harness前置错误，修成页面精确匹配；不能据此判生产页面或API缺陷。 |
| round3 | 聚焦公开可见旅程exit0，1 passed (8.7s)；frontend tsc exit0 | 生成、查看下载、重开、绘制发送编辑、文件重试贯通；只属隔离技术验证。 |
| round4 | Dream180、Admin94、两tsc、9契约、10浏览器均exit0 | 独立复审随后发现Gateway ID形状假阳性；此轮绿色不能证明真实ID兼容。修后必须重跑，原日志保留。 |

各轮日志分别保留于`/tmp/im-image-model-split-20261010/validation-round1`至`validation-round4`。第4轮10项浏览器包括5设置、4草图和1贯通公开旅程；截图、下载文件和trace均保留。所有这些结果都不能替代正常账户/模型验收。

## 选择子范围修复后回执（round5，非当前最终验收）

以下均为本轮重新执行，主执行者已读取原始命令回执与关键输出；没有用round4或既有任务的绿色结果替代。完整命令及工作目录见[命令清单](/tmp/im-image-model-split-20261010/validation-round5/commands.md)，对应`.exit`保留退出码。所有技术验证使用限定fixture或具名隔离数据库；Admin浏览器流程会写入隔离业务数据，不是只读检查，也不是正常服务真实验收。

| 本轮检查 | 退出码与关键输出 | 原始回执 |
|---|---|---|
| Dream图片、目录、偏好、公开旅程与上下文9文件pytest | 0；182 passed (25.33s) | [pytest](/tmp/im-image-model-split-20261010/validation-round5/dream-pytest.out) |
| Admin目录、严格操作/codec/receipt、Responses和Images 11文件Vitest | 0；11 files / 94 tests passed | [Vitest](/tmp/im-image-model-split-20261010/validation-round5/admin-vitest.out) |
| Admin与Dream frontend TypeScript | 两条`pnpm exec tsc --noEmit --incremental false`均0 | [Admin](/tmp/im-image-model-split-20261010/validation-round5/admin-tsc.out)、[frontend](/tmp/im-image-model-split-20261010/validation-round5/dream-frontend-tsc.out) |
| frontend模型目录纯合同Playwright | 0；9 passed | [目录合同](/tmp/im-image-model-split-20261010/validation-round5/frontend-playwright-contract.out) |
| frontend HTTP错误纯合同Playwright | 0；4 passed；清单误写Vitest后按真实Playwright命令补跑 | [补跑](/tmp/im-image-model-split-20261010/validation-round5/frontend-http-errors-contract-rerun.out) |
| Service、Runner、ThreadFactory、EventBus兼容pytest | 0；291 passed, 1 skipped, 179 subtests passed | [含跳过原因](/tmp/im-image-model-split-20261010/validation-round5/dream-compatibility-skip-detail.out) |
| Dream可见Chrome：设置、公开Chat贯通旅程、草图 | 0；10 passed (17.3s)：5设置+1贯通+4草图 | [浏览器](/tmp/im-image-model-split-20261010/validation-round5/browser-e2e.out) |
| Admin现有Image模型中心可见Chrome全流程 | 0；1 passed (1.2m)：Provider、模型、价格、生成/编辑、结算、安全记录 | [Admin浏览器](/tmp/im-image-model-split-20261010/validation-round5/admin-visible-e2e.out) |
| Markdown路径/目录/历史/operation合同检查 | 0；14份Markdown、补齐源码证据后286本地引用（含46源码行号）、无失效路径；13外链仅列出未请求；5历史全文hash一致；261旧operation完整descriptor/capability前缀完全保留，新操作为第262项，hash一致 | [文档检查](/tmp/im-image-model-split-20261010/validation-round5/doc-validation/source-evidence-final.out) |
| Mermaid语法 | 0；追加最终记录后，本机11.17.2解析10图，失败0 | [语法回执](/tmp/im-image-model-split-20261010/validation-round5/doc-validation/mermaid-parse-rerun.out) |

可见旅程的原始截图、下载文件与trace保存在[Dream生成物目录](/tmp/im-image-model-split-20261010/validation-round5/browser-artifacts)及[Admin生成物目录](/tmp/im-image-model-split-20261010/validation-round5/admin-browser-artifacts)。Chrome只在round2做过一次启动前置检查，后续没有重复预检查、安装或下载Chromium。10图语法与Markdown检查属于文档验证，不作为业务功能验收。

兼容测试唯一跳过项是`backend/tests/test_claude_agent_runner.py:1224`的Tool确认PreToolUse：需要真实SDK子进程hook，mock query_stream只能在工具执行后返回，不能触发该hook。这个skip不是图片生成通过，也未由CLI隔离协议探针替代。

### 完整流程覆盖与未验证行为

| 用户要求的流程 | 本轮具体覆盖 | 未验证部分与限制 |
|---|---|---|
| Admin配置→models→IM标记 | Admin可见配置生成/编辑能力及目录契约；Dream真实设置组件接公开BFF形状，四能力不混用 | 两端在各自隔离harness验证，未在正常四服务和真实账户中贯通；Responses内置字段仍关闭。 |
| 分别保存AI/Image→刷新→分别生效 | Chrome分别选择与保存、刷新恢复、失效选择、窄屏、读取失败、已提交但响应丢失后只读核对；公开Chat绑定已保存Image alias | 真实模型对AI选择的输出差异未验收；本轮没有正常业务库偏好写入。 |
| 普通文字生成→Responses内置→访问/保存/重开 | 只验证未实现结果不能静默转换或回退Images；真实CLI接受完整server扩展及resume的隔离协议 | 内置声明、Gateway事件/结果转换、Dream raw图片发布、图片计费及历史关联尚未实现；成功旅程未运行。 |
| 上传→主对话编辑→原图保留→后续引用 | 原图视觉块和Messages/Responses输入转换合同；独立Images编辑的原图保留、同文件引用和持久化 | 主对话内置编辑成功未实现；fakeSDK不证明真实图片理解或后续语义引用。 |
| 明确image_gen→所选Image→Images生成/编辑→不双路 | 公开路由/生产Service/broker/Host贯通，Provider检查所选alias，实际req_身份从HTTP到SSE/历史不变；fakeSDK分别调用生成和编辑，当前内置关闭 | 真实模型对“执行image_gen”和名称讨论的区分未验收；未来同时开放两路时的服务端互斥尚未实现，不能把prompt当保证。 |
| 添加→绘制→入消息→发送→理解或编辑 | 可见绘制画布、添加PNG不触发调用、实际发送，PNG上传SHA与编辑输入相同，返回新图并保留原图 | 当前贯通旅程为Images编辑技术验证，未验证真实模型理解；工作区关闭时视觉输入的既有缺口未扩展修复。 |
| 不可用/失效/生成/解析/文件/断线/取消/重试 | 严格目录/保存/Provider失败与零回退；HTTP错误；可见保存断线核对、文件503后只读Retry；Host取消及迟到结果拒绝技术合同 | 没有正常真实模型的连接中断、取消/重试与全部失败可见旅程；内置成功链路缺失，故其恢复不能宣称验收。 |
| 文字、普通Tool、媒体、历史兼容 | 原Service/Runner/Factory/EventBus 291测试与179 subtests；图片消息保存、重开、工具结果身份保持；原图片输入适配测试 | 一项真实SDK PreToolUse hook跳过；这些隔离回归不是正常服务真实模型验收。 |

### 自有资源身份与清理

主执行者使用原`node --import tsx scripts/prepare-gateway-deadlock-postgres.mjs`准备新的隔离cluster，先检查`current_database()`、`data_directory`和127.0.0.1监听身份，才将Admin既有79份Drizzle migration应用于本轮隔离数据库；没有新增migration或修改正常数据库。实际数据库为`ink_gateway_deadlock_test_a4859d5b4c1f`与其`_ui`数据库，PG端口60980、harness App端口61030，根目录为`/var/folders/bn/m6tkvhx160d9nx6v6rkkkrj80000gn/T/ink-gateway-deadlock-test-tIvbcA`。该脚本是本轮命名的验证脚本，不是Dream runtime DDL。

[身份回执](/tmp/im-image-model-split-20261010/validation-round5/owned-postgres-identity.json)不含凭证。主执行者向本轮自有setup session发送换行执行其清理入口，exit0、`owned PostgreSQL cluster and private fixture removed`；确认自有端口结束后，仅删除本轮`.next-e2e-deadlock-a4859d5b4c1f`。Luna清理其自有Python/Vite/浏览器fixture；[清理回执](/tmp/im-image-model-split-20261010/validation-round5/owned-cleanup.json)确认自有PG/私密fixture/Next目录均不存在，未停止用户正常服务。日志、trace、截图及下载图片保留用于复核。

## 子范围阶段快照：交付状态与必需后续工作（内置接入前）

此段保留当时状态；后续已实施内置链路，当前状态以文末 2026-10-11 交付核对为准。

专项PRD、正式设计、现有图片稿修订、历史全文、独立复审修订、独立选择/公开能力/严格写合同/工具alias绑定/真实Gateway ID关联的源码和上述隔离验证已落地。没有提交、推送、部署或启动/重启正常服务。

当前聊天`01a125f2-f97e-7d33-8859-8b7676ee5688`的完整目标仍为**active**，未标记complete或blocked。两个既有来源聊天保持原状态，没有创建重复聊天、代发消息或把它们旧回执计入本轮完成。完整专项尚未完成：主对话Responses内置生成/编辑仍需按正式稿补齐实际协议和持久化/计费，并在两路都开放时实施服务端互斥；这不是本轮已经具备但仅未上线的功能。

真实业务验收另缺本轮用户指定的现有真实账户、已有Thread/Deck及明确AI/Image模型。遵照不询问要求记录缺失，没有任选账户、影子实体或替代Gateway冒充验收，没有正常数据库Run/Token结算可供Admin复核。本轮真实CLI配假Gateway观察也不能补足这些输入。上述实现缺口和真实验收缺口必须都关闭后，才能将完整目标改为complete。

## 自动目标续轮：继续主对话链路

上轮分类为progress：代码与修订后的隔离回执、文档检查、源码证据和资源清理改变了权威状态。完整目标没有缩小；当前续轮继续实现主对话Responses前提，不把“内置关闭”当最终交付。

### Expert Prompt Architect（续轮计划前）

**角色与上下文**：保持专项负责人和原完整目标；以当前两项目工作树为准。独立研究确认普通OpenAI只发Chat；现有Provider.config、Gateway协议转换、transport和Admin单次模型验证可复用。另确认原Images用量/价格capability不能直接等同混合Responses计费；精确delegation的Thread/Run身份在Gateway principal投影时丢失，现有两个幂等key不能作为跨链路排他依据。

**任务**：先补普通OpenAI明确选择Responses方言的最小配置、实际请求、JSON/SSE转换与验证路径；保持旧默认Chat和既有托管产品方言。随后继续处理真实server图片声明/结果、调用方式约束、文件历史与混合计费，不以这项前提完成替代完整图片能力。

**约束与验收**：无Key/host/model-name推断、隐式协议切换或重发；Provider.config服务端保存，并复用原credential-sensitive expectedAuthRevision与验证边界；不增加Provider种类、表、CLI替代入口、部署环境分支或正常服务写入。Responses文本/视觉兼容、显式配置非法值fail closed、验证与实际端点/报文一致、JSON/SSE终态和原托管/文字流程须由Luna重新验证。图片能力保持未开放，直到声明/实际用量/排他/发布完整。真实模型仍需指定输入；不得猜费用或用fake报文声明真实模型兼容。

**计划**：先更新现行正式稿并独立评审明确方言前提；实施共用方言解析和相关调用点；Luna限定回归；主执行者读原回执并同步文档。新协议前提完成后继续审查图片结果和混合结算，不将目标标为complete。

### 续轮独立评审及已修订源码

实际稿两项P2已先修：每个显式路由候选采用自己的冻结API；停用创建、登记验证Model后激活/敏感保存，失败保留原状态。只读复审确认可实施。实际代码再次独立评审发现P1：非敏感预读之后，另一管理员验证切换API，旧草稿可能在行锁后覆盖新config却不推进revision。已在原行锁内重查有效API；没有敏感验证回执却需切换则原409，不UPDATE、不在事务里调用上游。公开PATCH确定性回归覆盖，复审确认P1关闭。

源码范围：共用`resolveProviderApi`/`resolveProviderInferenceEndpoint`，generic显式Responses请求转换、transport、JSON/SSE和实际候选配置；Admin单次模型验证、原敏感CAS；共享Provider表单具名字段与隐藏覆盖移除。原default Chat、managed dialect、Images路径与native图片拒绝保留。未新增Schema、Provider enum、消息通道、确认或部署环境分支。

Luna round6首轮Vitest exit1（153 passed/3 failed）、tsc exit2：本轮新增验证fixture没有真实ReadableStream且cancel不返回Promise，代理断言误把HTTP request ID当response.id。主执行者修正fixture和独立身份断言后，新回执Vitest exit0（10文件/157 passed）、tsc exit0；原失败日志保留。具体原命令/日志见[round6目录](/tmp/im-image-model-split-20261010/validation-round6)。这些只验证Responses协议前提，不能替代完整图片或真实业务验收；下一步仍推进native事件/意图/文件与结算。

### Expert Prompt Architect（内置链路下一阶段计划前）

**上下文与事实**：普通OpenAI Responses前提已实施并通过新合同检查，可见E2E正在本轮隔离库运行。官方Response ImageGenerationCall和完成事件没有逐调用图片usage，顶层usage也没有公开完整图片拆分；不能复用独立Images解析器编造费用。独立研究建议复用原CLI工具循环的结构化选择步骤，缺决定时两条图片能力均关闭，普通文字无需新增分类调用。

**目标与边界**：继续完整专项。先将结构化语义选择、服务认证的turn/message绑定与跨链路门禁写入实际稿并独立评审；不按名称正则、不另启Runner或自动切换模型。随后实施Gateway原Responses内置声明/结果、Dream raw发布及历史关联；图片成功但完整计费未知时保留业务成功和usageKnown:false，既有预留核对不能冒充真实费用。需要新发布的具名合同；不得改旧Images capability或在Dream补Schema。

**验证计划**：每项实现由Luna新合同与隔离可见E2E检查，主执行者读真实命令；覆盖未选路时双路拒绝、已选路时另一链路拒绝、名称讨论与素材无副作用、server调用ID与Gateway ID、文件与重开、unknown成功和报表。真实语义/模型验收仍缺本轮指定真实账户、实体和明确模型，不用fake成功替代。

### 内置增量独立评审修订与测试harness恢复

独立实际稿评审指出2项P1：stdio仅有broker UUID，须先登记真实Gateway选择与SDK tool_use_id、唯一pending匹配，原receipt不可变；claim、Gateway建档、预留必须在同一PoolClient事务原子完成，原unknown worker仅Token-only。2项P2为图中漏CLI/Gateway实际传输与错误强制全部主模型Responses，以及历史保存错误等待worker。已将追加不可变阶段receipt、固定account→turn→receipt锁序、双端真实调用身份、同路也只允许单执行、AI服务预算+文本预留安全加乘、Token-only零现金资格及立即保存/异步结算写入实际稿，再交独立复审。新增合同/capability与该执行面仍为建议未实现，不修改旧Images物理合同。

round6可见E2E先有变量重名导致parse失败（未进入浏览器），修正后进入并完成原Images旅程，但新增OpenAI主对话API字段accessible name带必填星号，精确测试locator失败且wrapper等待未退出；Luna只停止本轮自有runner/App，保留trace。修正后再跑遭同隔离库上次中断保留的callable订阅409，未到新增旅程。上述均保留原失败回执，不能判断新增产品流程已通过。主执行者确认旧自有PG/端口已停，仅清理命名旧cluster与dist；新明确隔离数据库`ink_gateway_deadlock_test_a91151bf9bab`及`_ui`应用原79migration，核对database/data_directory/127.0.0.1与0600 manifest后交Luna重跑。旧setup stdin已关闭，SIGTERM自有setup后目录未自动删除，改由主执行者确认自有端口停止并核对manifest身份后只删除其目录。无正常数据库或服务变更。

### 内置前提实际代码与本轮回执

实际稿2P1与2P2全部经独立复审关闭，进一步采用CLI已有MCP `_meta["claudecode/toolUseId"]`与PreToolUse/source精确匹配，保留broker UUID的独立意义；缺meta不推测。只读研究另外确认server图片历史目前会被原Gateway过滤，必须以真实图片专用历史转换恢复，不能伪造function output或重新获得claim；providerExecuted实时/保存两处仍待透传。

已新增Admin`responses-image-protocol.ts`结果规范化前提并导出复用原`validateBase64Image`完整解码器；结果去重/数量/完成态/action/格式/规范base64，保留实际Response/item/HTTP/Gateway身份，安全summary不含prompt、revised_prompt、图片或原始usage，完整结算保持unknown且reportedImageModel为null。独立只读代码评审未发现P1/P2。Luna新命令`pnpm exec vitest run app/lib/gateway/responses-image-protocol.test.ts app/lib/gateway/image-protocols.test.ts app/lib/gateway/responses-adapter.test.ts app/lib/gateway/image-conversation-adapter.test.ts` exit0、4文件35 passed；`pnpm exec tsc --noEmit --incremental false` exit0，已读[原命令与输出](/tmp/im-image-model-split-20261010/validation-round6/native-result-prerequisite.out)和[类型回执](/tmp/im-image-model-split-20261010/validation-round6/native-result-tsc.exit)。helper没有接入public入口，不能称为native业务通过。

同时补Gateway原认证对delegation已核实身份的server-only immutable投影，保留service/auth subject/canonical user/Thread/Run/purpose，排除bearer、token hash及浏览器自报turn。没有扩大scope或改变fixed-key/OAuth行为；后续实际绑定及门控尚未实现。

新隔离库rerun3原日志实际包含Running 1 test/worker及具体测试编号；Luna初判未启动Playwright与原日志矛盾，经主执行者读取后要求只读复核并更正回执。trace证实已进入新增Responses Provider页，在第二个必填字段“模型目录模式 *”处因exact locator未匹配而失败，随后wrapper挂起。主执行者已同时检查并修正新增目录/状态字段locator。该失败不能归类为浏览器启动前置失败或完整产品验收失败；原始日志、修正观察与trace均保留，继续重新执行。

### round6最终回执与round7继续实施

主执行者已读取round6 rerun4原始command/out/exit：Admin可见E2E exit0、1 passed (1.2m)，原Images全流程及新增明确Responses主协议均通过隔离fake Provider；runtime身份11tests与tsc均0。文档检查14文件、300本地引用、47源码行号、历史完整；当前稿12个Mermaid由11.17.2全部解析通过。未将技术验证称真实模型验收。

round7补充成功图片交付与完整计费unknown的writer前提、合并真实关联，以及worker结案后Product/报表unknown状态；首轮新Vitest exit0、6文件29passed，tsc0，已读[原回执](/tmp/im-image-model-split-20261010/validation-round7/billing-unknown-vitest.out)。独立只读评审随后指出3P2：Token/趋势仍纳入完整未知、Known writer可能继承旧false终态、unknown失败漏safe summary；已修源码，并继续修可见Token卡片/模型列/全未知趋势，不将原29passed当修订后回执。

追加严格图片turn/source/selection/claim DTO与同PoolClient不可变receipt helper，新operation仍未注册，Provider执行仍未接通。Gateway DATABASE_URL原platform池与ADMIN_CONTROL_DATABASE_URL认证池不同，不把control角色当Gateway。新物理合同只验证既有结构并发布cap；实际Gateway角色的schema USAGE/receipt SELECT、INSERT/audit INSERT逐项另核，无权关闭。正常库角色权限没有自动扩大，也没有新增第5认证角色。

Drizzle custom生成第一次误写root空0079占位。该条已入journal，按冻结合同保留原SQL/snapshot/tag/when；纠正为scratch生成并完成0080候选后一次导入，不改旧历史或正常库。scratch首轮CLI缺参数、第二轮绝对out被工具错误拼接，第二轮虽返回exit0但日志含ENOENT，未认定成功；改相对out后实际生成0080，再在入root前完成结构校验和capability SQL。该新合同尚待隔离migration/限权角色和API验证，不作为已上线。

### Expert Prompt Architect（素材协议修订前）

角色与事实：原上下文把附件图片与独立URI文本按固定顺序发送；CLI imageResizer重建图片块并可能改格式/尺寸。原文件sha只能由Host文件读取验证，不能充当CLI wire sha。
目标与约束：当前消息上传、草图及从历史添加为当前素材的图片，先由server bind固化URI/原文件摘要/顺序；Gateway在首次关闭执行路由的实际Messages中核对该顺序及服务文本，再追加仅含URI/wire摘要/格式/大小的normalized receipt。后续native只发送获选素材的相同wire bytes。缺少当前素材或normalize事实时明确要求添加素材，不从任意正文/Read路径猜授权。
计划：修订正式稿，独立审查素材绑定和专用恢复；实现原receipt上的normalized事实及native输入核对；验证resize后摘要不同仍能正确关联、同URI不同wire拒绝、选择范围外图片排除、历史添加当前素材流程。原新合同复用结构，不改冻结0080或原合同hash。

本轮已修复独立评审P1（image receipt DTO词法作用域）与P2（执行后select exact replay），尚待公开Handler新命令回执。49passed/tsc0为修订前基础检查，不替代上述修复或后续接入。

### Expert Prompt Architect（接入与兼容评审修订）

角色、目标与原合同不变。新增事实：真实 CLI 附件 new/resume 的素材 marker 位于固定 user-context 文本之后，原文件与 resized wire 摘要不同；原 stdio 工具现在必须核对 Hook 与 MCP meta 的真实 tool_use_id。独立评审又发现原生图片历史转换丢失和 GIF 普通看图回归。目标是先修正式稿中的具体行为与恢复路径，再修历史只读投影及当前素材格式资格，更新仅存在于测试目录的注入 fixture，使新绑定/选择/执行流程成为技术验证的真实前置，而不增加业务 fallback。

调整计划：主执行者补齐 Gateway 历史、素材与 Images 参数精确校验及 IM 发布/引用；Luna重新执行确定性合同与可见流程；独立评审针对修后实际源码复审；随后同步各目录合同、Registry镜像与完整当前文档。真实验收仍缺用户指定现有身份、实体与两模型，不能用隔离回执替代。当前目标保持 active。

round7 native-connected-rerun2 的原始 8文件74测试与tsc均exit0。前一轮 `it.each` 数组展开不符合测试作者意图，已修为具名 blocks，再重新执行本轮负例；未用前轮通过代替修后验证。IM初次接入回归exit1（19passed/27failed），主要为旧fixture未绑定/选择/Hook、旧参数缺必填reference_images、新工具目录断言未更新，保留原日志并继续修订；不能据此宣布媒体或公开业务已通过。

### 2026-10-11 复审后验证计划（EPA → 计划）

**角色与目标**：架构与产品工程主执行者；完成最新复审修订及本轮必要验证，明确技术验证和正常真实业务验收的区别。**输入**：实际设计、当前代码、round9 原始回执及独立复审。**约束**：不询问、不改变正常服务、隔离数据库必须具名且核对身份、Luna 只执行检查、保留历史与失败回执。**输出**：当前命令/退出码/关键输出、修订点、清理回执及明确未验收项。**验收**：失败反馈/取消历史/原生确认边界修订有可见组件证据；原 Admin 全流程结算及能力配置在新隔离库重新执行；当前文档清单/引用/历史/图示校验通过。

执行顺序：先修订实际设计及代码，再由主执行者编写反馈组件检查并初始化全新具名 Admin fixture；Luna 执行当前确定性检查与完整可见流程；主执行者读取回执、修订实际失败、验证文档并清理自有资源。真实业务仍缺用户指定现有账户、业务实体、AI/Image 模型；安装的正常 Runtime 大图缩放还缺原生 sharp 包。上述事实不会用隔离流程替代。

## 2026-10-11 交付核对：当前实现与证据范围

以下是当前事实；上方各阶段未实现状态与失败回执保留用于追溯，不代表当前实现。

### 六项调查结论

| 问题 | 当前回答及可复核源码 |
|---|---|
| 1. 两条链路实现到哪里 | **源码已实现**：主对话 IM→实际 CLI Messages→Gateway `handleAnthropicMessages`→`proxyResponsesImage`→上游 Responses 内置图片工具，结果回到 raw bridge、原文件及消息保存。显式工具 IM→CLI→`image_gen.imagegen`→`ImageGenerationProvider.generate`→Gateway 原 Images 生成/编辑。CLI 从未改为直接发送 Responses。[Gateway 入口](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/anthropic-handler.ts:24)、[内置代理](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/responses-image-proxy.ts:51)、[Images 执行](../../backend/services/admin_gateway/images.py:218)。 |
| 2. 最小 CLI/Gateway 能力 | **源码已实现**：复用 CLI 现有 tool_use 循环执行结构化语义选择，真实 PreToolUse/MCP meta 身份与 Gateway 实际完整 tool call 关联；Gateway 才声明内置工具、强制单路单次执行、转换真实 server blocks；SDK raw StreamEvent 补齐其 parser 未识别的图片 result。当前保存、读取、严格历史投影、count_tokens 视觉转换、图片发布及完整用量未知状态都已接入。[stdio 两工具](../../backend/libs/claude_agent_kit/server/image_gen_stdio.py:24)、[Service 原生事件](../../backend/claude_agent/service.py:3414)、[历史投影](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/protocol-adapters.ts:104)。没有修改恢复源码或安装的 CLI bundle。 |
| 3. 四项能力可否区分 | **源码已实现**：Responses `responses_image_generation` / `responses_image_edit` 和独立 Images `image_generation` / `image_edit` 分开；目录输出 `responsesImage` 与 `images`，各自含 generation、edit、configured、entitled、callable，不能互相推导。[models endpoint](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/models.ts:303)、[设置选择](../../frontend/app/_dream/components/dashboard/ModelConfigSection.tsx:144)。 |
| 4. 勾选、发布、endpoint 是否同事实 | **源码已实现**：Admin 表单明确四个勾选名称，原保存校验、Provider 显式 Responses 方言与原模型发布/资格被目录投影。内置 configured 还要求精确 capability、实际 Gateway pool 角色权限和预算；声明能力不代表已配置或有调用资格。[表单](/Users/dmeck/project/ink-admin-memory/app/components/admin/AdminResourceViews.tsx:101)、[保存规则](/Users/dmeck/project/ink-admin-memory/app/lib/admin/mutations.ts:251)、[精确权限](/Users/dmeck/project/ink-admin-memory/app/lib/db/image-turn-capability.ts:15)。 |
| 5. 默认/保存/失效 | **源码已实现**：AI 保留原默认和原用户选择，Image 默认未选择；严格独立 patch 保存 Image alias，实际 turn 冻结两项选择。失效 alias 仍显示并要求用户重新选择；保存结果未知时只回读，不重复写；不按模型名、环境或单个候选回退。Host 在保存 native 决定前校验所选 AI 能力，Gateway 实际执行再校验。[AI/Image 保存](../../frontend/app/_dream/components/dashboard/ModelConfigSection.tsx:343)、[Host bind/select](../../backend/services/admin_gateway/images.py:108)。 |
| 6. 身份、引用、历史 | **源码已实现**：原同用户 thread/run/message 与当前素材摘要通过具名 bind/select/result 操作关联。真实 selection tool ID、execution tool ID、req_/resp_/ig_、outputIndex 与文件 MIME/bytes/SHA 保留；broker UUID 独立，不能替代 Provider/CLI 身份。跨链路 claim 和原 Gateway 建档/预留同事务。文件发布沿原授权目录/消息 parts；两端点产生新文件，保留原图；历史图先添加到当前消息再参与编辑。[互斥 claim](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/image-turn-receipts.ts:105)、[raw 图片发布](../../backend/services/admin_gateway/images.py:169)、[原具名操作适配](../../backend/services/admin_data/image_turn_data.py:130)。 |

**本轮已观察**：正常安装 CLI 和仅补本机 native sharp 包的隔离原 bundle 均实际发送 `/v1/messages?beta=true`；实际 CLI 解析 server blocks 后正常结束，同一 CLI/MCP probe 的 PreToolUse 与 MCP meta ID 精确一致。正常安装 Runtime 0.1.10 的 2400px 视觉输入在发送 Gateway 前失败；隔离 bundle 才观察到原图与缩放后 wire 图的不同摘要。可见浏览器使用实际生产组件/公开入口，但 Dream SDK/Admin/Provider/storage seam 是隔离实现。真实 PostgreSQL 技术检查观察到一赢家/一拒绝、相同 idempotency 重读及强制 rollback，不发送真实 Provider。

**合理推断**：这些实际协议观察支持当前桥接方式，但不能保证尚未选择的真实模型一定采用正确语义选择、图片格式或完整计费结果。**建议，未实施/未验收**：正常服务发布新 capability/明确角色授权及下一版本 Runtime 发布采用后，使用用户指定现有账户、实体、AI/Image 模型进行正常数据库完整真实模型流程；本轮未自行发布、授权正常角色或选取账户。

### 独立评审及本轮修订

原设计 P1 调用身份缺失、claim 与预留不原子，以及 P2 时序图、持久化等待 worker 等问题已先改实际设计再实施。后续源码复审修正 native 完整历史、真实 CLI 日期前缀、原图/wire SHA 分离、GIF 视觉兼容、权限检测 fail closed、预授权前严格历史检查、count_tokens 使用同一视觉投影、unknown 持久化成功才发布及取消后的发布边界。没有改原 admission 比较、资源策略、Runner 线程生命周期、SSE/resume/cancel 状态机。

最新前端独立复审修正：实时及历史失败展示 message；原生 Provider 执行不产生虚假的本地确认；中断历史显示未完成。第二次复审指出确认墓碑不代表执行结束、实时错误可能是 JSON 字符串；已据真实 DTO 再修并复核关闭两处 P2。新增可见组件检查覆盖这些边界，普通/MCP 确认策略保留。Admin round9 全流程发现本轮已知用量摘要覆盖 worker 的 `actual_usage_recovered`；修复后保留该值，没有更改金额算法或只修改测试期望。

精确协议：Admin 原 registry 262 项前缀不变，追加 image-turn 三项到 265；Dream 原部分镜像 147 项前缀不变，追加到 150。Admin 前向 0080 发布 `dream.image-turn.v1`，复用原 receipt/audit/requestSummary/message 存储，不新增业务表或 Dream DDL；旧 0079 与新 0080 SQL/snapshot 按已生成稿冻结。能力发布和生产角色权限激活分开，当前正常服务未部署此增量。

### EPA → 验证矩阵补齐（2026-10-11）

**目标与输入**：当前两端完整可见旅程已通过，最终矩阵复核发现图片停止/失败后发送新请求及普通工具的可见证据不足，不能只用单元结果补成浏览器覆盖。**边界**：仅扩展已有具名 public journey fixture 的 SDK/Provider seam、调用原 threadStop helper 和公开生产入口；不增加业务状态机、API、最终图片注入或真实模型声明。**计划**：在同一实际组件/公开路由浏览器旅程增加停止进行中的显式图片、重开无图、解析失败后新请求重试及普通工具/文字恢复；由 Luna 重跑完整4spec及受影响公开入口测试，再读取实际回执。正常账户/模型验收限制仍单独保留。

### 最终本轮命令回执与覆盖（2026-10-11）

下表均为本专项修改后的实际命令，主执行者已读取 command/out/exit；不同检查的 seam 不能合并为一次真实模型流程。源文件后续只变更测试断言或文档时，未重复不受影响的兼容检查。完整命令保存在对应 command 文件，原失败轮次也保留。

| 检查及执行位置 | 命令与退出码 | 关键输出及范围 |
|---|---|---|
| Admin 确定性合同 | `pnpm exec vitest run`，19个明确文件，exit 0；[完整命令](/tmp/im-image-model-split-20261010/validation-round11/admin-vitest.command)、[输出](/tmp/im-image-model-split-20261010/validation-round11/admin-vitest.out) | 19 files / 138 passed；实际协议转换、当前素材、严格结果、原预留与 claim、unknown/known 摘要、原 worker/报表合同。 |
| Admin 类型 | `pnpm exec tsc --noEmit --incremental false`，exit 0；[回执](/tmp/im-image-model-split-20261010/validation-round11/admin-tsc.exit) | 无类型错误。 |
| Admin 完整可见流程 | `node scripts/verify-image-model-center-e2e.mjs <本轮具名 fixture.json>`，exit 0；[完整命令](/tmp/im-image-model-split-20261010/validation-round11/admin-visible.command)、[输出](/tmp/im-image-model-split-20261010/validation-round11/admin-visible.out) | 1 passed (1.6m)；可见 Provider 明确 Responses 保存/刷新/验证、四项能力保存/发布、公开 models 字段及原 Images/结算/失败/取消流程。使用具名真实 PostgreSQL 与 fake Provider。fixture 已按协议清理。 |
| Dream 图片与公开入口合同 | `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest`，10个明确文件，exit 0；[完整命令](/tmp/im-image-model-split-20261010/validation-round13/dream-image-pytest.command)、[输出](/tmp/im-image-model-split-20261010/validation-round13/dream-image-pytest.out) | 192 passed；模型目录/偏好/冻结选择/Host/真实 DTO/公开图片 journey 合同。 |
| Dream 原流程兼容 | `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_runner.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_event_bus.py -q -rs`，exit 0；[输出](/tmp/im-image-model-split-20261010/validation-round9/dream-compatibility.out) | 291 passed / 1 skipped / 179 subtests passed。skip 为原 PreToolUse 不能由 post-execution AssistantMessage mock 触发；实际 CLI/MCP probe 单独观察该协议，不把此 skip 改称通过。 |
| 前端类型与纯合同 | `pnpm exec tsc --noEmit --incremental false` exit 0；`pnpm exec playwright test --config=…/frontend-contract.config.mjs --reporter=line` exit 0；[类型回执](/tmp/im-image-model-split-20261010/validation-round17/frontend-tsc.exit)、[合同完整命令](/tmp/im-image-model-split-20261010/validation-round10/frontend-contract.command)、[输出](/tmp/im-image-model-split-20261010/validation-round10/frontend-contract.out) | 13 passed；模型四项事实、AI/Image候选、typed HTTP错误及原成功文字 SSE。类型检查包含最终生产布局修订。 |
| Dream 完整可见矩阵 | `pnpm exec playwright test --config=/tmp/im-image-model-split-20261010/validation-round18/dream-visible.config.mjs --reporter=line`，exit 0；[输出](/tmp/im-image-model-split-20261010/validation-round18/dream-visible.out) | 4 spec / 12 passed (27.1s)。实际生产组件、公开路由、Service/Host、文件与消息流程；SDK/Admin/Provider/storage 为隔离 seam，未注入前端最终图片或复制 SSE；包含375×812素材按钮完整范围及实际添加。 |
| 实际 CLI/MCP 协议 | `PYTHONPATH=backend:. backend/.venv/bin/python /tmp/im-image-model-split-20261010/validation-round7/cli-mcp-image-probe.py`，exit 0；[输出](/tmp/im-image-model-split-20261010/validation-round7/native-connected-rerun5/cli-mcp-image.out) | 实际 CLI 发3次 Messages，真实 selection/image 工具 ID 在 Hook/meta/Host 一致；仅1次 fake Images 请求、所选 `selected-image`、文件1个、CLI success。原 bundle 隔离补 native 包，不代表正常 Runtime 或真实模型通过。 |
| PostgreSQL 原事务合同 | `node --conditions=react-server --import tsx /tmp/im-image-model-split-20261010/validation-round7/verify-owned-image-turn-pg.mjs`，exit 0；[输出](/tmp/im-image-model-split-20261010/validation-round7/native-connected-rerun6/owned-image-turn-pg.out) | 具名隔离 PG：原请求预留/互斥一赢家、原幂等重读、claim/audit强制rollback、独立角色权限与自有预留清理均 true；没有调用真实 Provider。 |
| 当前文档及 Mermaid | `node --conditions=react-server --import tsx …/runtime-descriptors.mjs`、`python3 …/doc-check.py`、`python3 …/extract-mermaid.py`、`node …/mermaid-harness.mjs`均exit 0；完整command/out/exit保存于[最终文档检查目录](/tmp/im-image-model-split-20261010/validation-round18/doc-validation) | 19文件、398本地引用、79源码行号；历史全文/清单/265与150 registry前缀/精确capability/冻结migration均通过。Mermaid 11.17.2解析6图，failures=0；这是文档验证。 |

| 完整流程项 | 本轮证据与验收边界 |
|---|---|
| 1. Admin→models→标记 | Admin 可见真实 PG 流程核对四勾选及公开字段；Dream 设置可见流程核对 AI 的 Responses 标记与 Image 的 Images 标记。两端浏览器不是同一正常服务调用链。 |
| 2. 两项保存/刷新/分别生效 | 可见独立保存/回读/刷新、失效选择保留、读失败禁用及未知保存只回读；公开旅程分别观察 AI alias 和 Image alias。 |
| 3. 普通生成→内置→查看/保存/重开 | 公开 journey 可见新图及重开；Gateway JSON/SSE/终态与 raw Host 合同、实际 CLI server block 接受分别验证。尚未在正常服务真实 AI 模型执行。 |
| 4. 上传/编辑→原图/引用 | 草图沿原上传入口送出、历史图添加当前消息、native 编辑后原图保留、三图重开；原文件与 CLI wire 摘要独立核验。真实模型编辑效果未验收。 |
| 5. 显式工具生成/编辑→无重复 | 可见生成/下载/草图编辑，selected Image alias 与调用计数准确；语义讨论不触发；实际 CLI Hook/meta/Host 和隔离 PG 原事务竞争分别验证。真实模型的语义路由准确性未验收。 |
| 6. 添加/绘制/发送 | 可见鼠标/触屏绘制、撤销/重做、清空、PNG上传及真实 Send；添加素材前后两路调用数不变。fake SDK 回答不作为真实图片理解质量证据。 |
| 7. 不可用/失效/失败/中断/取消/重试 | 可见不支持反馈、保存失效/未知、结果解析失败后新请求、图片只重读、进行中 Stop→重开未完成且无图片。连接中断后的真实 Provider 行为、已发上游取消计费仅有技术合同，尚未正常服务验收。 |
| 8. 文字/Tool/媒体/历史兼容 | 可见讨论文字及普通 Read Tool结果在重开后直接展示；Service/Runner/ThreadFactory/EventBus、GIF视觉、native严格历史/count_tokens转换合同。真实长期会话与其他媒体未做正常服务端到端验收。 |

最新可见历史截图：[生成/编辑/重开](/tmp/im-image-model-split-20261010/validation-round18/dream-visible-artifacts/image-chat-public-journey--aa895-dit-and-recover-a-file-read/image-chat-reopened.png)、[停止与失败恢复后普通工具历史](/tmp/im-image-model-split-20261010/validation-round18/dream-visible-artifacts/image-chat-public-journey--35578-etain-ordinary-tool-history/image-chat-recovered-tool-history.png)。截图是隔离技术验证证据。

### 后续失败回执、修订与清理

round8 的可见重跑遇到上次隔离订阅留下的409，改为重新核对并初始化全新具名数据库。round9 的 Admin 全流程发现 worker 的 `actual_usage_recovered` 被 known writer 覆盖，是源码问题；修复 resolution 后，独立复审再发现 spread 旧 summary 会重新写回 unknownReason/resolvedAt。已在数据库合并和新输入两处移除旧终态字段，保留真实 ID与 recovered resolution；round11 的138项及完整可见流程重新通过。没有改变锁顺序、Token或金额算法。

round10 首轮新增反馈检查使用了不符合实际 DTO 的 action/空 refs，随后按真实 input.operation 和非空 refs 修正；源码复审同时修正“确认结束不等于执行结束”和实时 JSON errorText 只展示 message。取消恢复 journey 的 round12/13 失败分别为未点击实际折叠行、误要求空输入 Send 可用，以及等待不存在的外层“展开过程”；保留失败记录，改为点击实际图片工具行并核对原 Stop 结束/重开未完成。round14 的12项通过后增加普通 Tool 真实 output 在历史中可见的断言，round15 再次12项通过。没有以旧通过代替修订后检查，也没有把 locator/fixture 失败称页面或 API 缺陷。

本轮所有明确命名的 PG/App fixture、私有 CLI workspace、隔离 Runtime bundle 已清理；Luna 自有浏览器/runner/测试服务也已结束。主执行者逐项核对数据库名、data_directory、127.0.0.1及自有端口后清理，未停止正常服务。[早期资源清理](/tmp/im-image-model-split-20261010/validation-round7/owned-cleanup-first.json)、[round9/10清理](/tmp/im-image-model-split-20261010/validation-round10/owned-cleanup.json)、[最终 PG/App清理](/tmp/im-image-model-split-20261010/validation-round11/owned-cleanup.json)、[自有 CLI清理](/tmp/im-image-model-split-20261010/validation-round15/owned-cli-cleanup.json)。安全回执、manifest校验摘要、原始日志与截图保留；CLI/PG probe 再执行需按同协议重新准备 fixture。

### 当前交付限制与任务状态

此节是round18–19时的历史交付快照，原文保留。账户未指定、Runtime未发布/未采用等限制已由round23解除；当前认证及Schema限制以文件开头与末尾round24为准。

**源码、现行稿、独立评审修订及隔离技术流程已交付；完整专项的正常服务真实业务验收未完成。** 未指定本轮现有真实账户、已有 Thread/Deck/业务实体和明确 AI/Image 模型，不能任选账户或建立影子实体。正常 Runtime 0.1.10 的大图输入缺 native sharp，probe 在 Gateway POST 前失败；正常服务尚未发布精确 `dream.image-turn.v1` capability 和实际 Gateway pool 角色权限。没有修改正常安装、发布 migration、扩大正常角色权限、提交/推送或部署。正常数据库没有本轮 Run/Thread/Gateway/Token结算验收记录，不能提供日常 Admin 可查的真实成功证明。

因此尚未验证：真实模型对普通请求/明确工具请求/名称讨论的语义选择，真实 Responses 生成/编辑及完整混合用量，真实 Images 生成/编辑，正常服务文件/历史、断线/已发取消/重试、草图理解与原文字/工具/媒体完整兼容。已完成所有不依赖上述输入的工作，没有提问或将技术结果包装为上线/真实验收。

既有 Dream 聊天“调研并设计 Tool 图像生成交互”（`01a116cd-51e2-79b0-af95-db07ad5cfae9`）与 Admin 聊天“Image 模型中心：调研、设计、实现与验证”（`01a120ae-3bb0-7432-88a2-4755ecb4275a`）沿用为来源；最终只读快照分别为 idle / 旧turn completed，以及 notLoaded / 旧turn completed，没有创建重复聊天或向它们代发消息。当前专项聊天 `01a125f2-f97e-7d33-8859-8b7676ee5688` 的目标仍为 **active / 未完成**，不以隔离通过标记 complete，也不把本轮持续取得进展的工作标记 blocked。

### EPA → 截图布局复核修订（2026-10-11）

**事实与目标**：主执行者读取 round15 实际历史截图，发现本轮添加素材的文字入口错误复用1.7rem图标按钮宽度，英文逐字换行。原普通工具输出在重开后可见已确认。**边界**：只修原 WorkspaceImage 文字入口的具名局部样式，复用按钮/上传回调；文件名省略，预览/下载原图标保持；不变更数据、协议或调用。**计划**：先将桌面/窄屏文字入口规则补入实际设计并独立复审；修组件class及原局部CSS/目录合同；在原公开旅程窄屏核对文字没有超出按钮并实际添加素材；Luna重跑完整12项浏览器及前端类型，最后重新检查当前文档。round16文档19文件/398本地引用/79行号及6个Mermaid全通过是此布局修订前回执。

独立实际稿评审未发现P1/P2，同意限定实施，并建议核对Range同一行及添加后调用数不变。主执行者已实施局部class/CSS，在原公开旅程375px核对文字位于按钮内且同一行，然后实际添加素材并沿原断言确认两路调用数未增加。

round17 修后前端类型与完整12项可见矩阵均exit0，主执行者已读取实际原回执。源码复审无新P1/P2，另指出测试只核对视口左右边界；已在测量前沿浏览器正常滚动入口进视口，再补上下边界及E2E目录说明。该加强断言不改变生产代码，最终矩阵继续执行，round17通过不替代其新回执。

round18加强断言后的原完整12项矩阵exit0、12 passed (27.1s)，主执行者已读取command/out/exit并复核截图。真实素材添加、原图/新图重开及普通工具输出均可见；自有browser/Vite/backend fixture/runner已清理。未改变正常业务验收限制或目标状态。

## 自动目标续轮：Runtime 图片依赖前置修复

上一目标轮为progress：实际布局、测试与文档权威状态改变。当前重新读取对应两聊天最近8轮用户输入，没有找到本轮指定的真实账户、已有实体或AI/Image模型。正常业务输入限制仍在；没有重跑已通过的矩阵或任选身份。

### Expert Prompt Architect（Runtime最小修复计划前）

**角色与目标**：保持完整专项的架构/产品工程主执行者；移除不依赖真实账户的图片运行前置缺口。**新事实**：本机存在 `/Users/dmeck/project/ink-claude-code-dream` 的实际单一Runtime源码。已读取其AGENTS/README/设计/build/test与受影响folder合同；原src字节不能更改。`npm-release.mjs`生成平台包只声明Bun，`verify-npm-tarball.mjs`与`smoke-npm-release.mjs`也强制只有Bun；构建已包含sharp 0.34.5 JS，其`@img/sharp-<target>` 0.34.5和`@img/sharp-libvips-<target>` 1.2.4没有进入平台依赖声明。实际正常Runtime大图在Gateway前失败与此一致。[sharp官方安装说明](https://sharp.pixelplumbing.com/install/)也要求安装平台原生依赖。

**边界**：只修现有npm平台依赖生成、prepack/归档/install smoke及配置事实；不改CLI原始模块、parser、SDK/Runner、模型、数据库、已发布0.1.10或正常安装，不增加备用CLI或全局模块路径。新发布须用新版本及原四平台资格；本轮不生成或发布新的0.1.10制品，也不以本机fixture证明四平台或真实模型通过。

**计划与验收**：先在Runtime现行正式稿补充具体修复并独立评审，再以同一政策派生精确平台依赖，三处消费同一事实，prepack/install smoke验证实际native加载。主执行者编写明确私有fixture，使用同字节原CLI、生产依赖映射和公开SDK观察2400px新会话/resume视觉输入；Luna运行受影响确定性/source/compat检查，主执行者负责实际CLI观察。保存新命令、失败和清理回执，再同步IM实际稿/记录。正常服务真实业务验收缺失输入继续单独保留。

### Runtime修订、实际观察与新增验证

在Runtime现行正式稿基础上完成独立评审：先修订实际Bun执行和公开exports两处P2；源码复审再修订optionalDependencies覆盖与真正libvips动态库逃逸两处P2。复审关闭全部四项。生产stager、prepack、独立tarball verifier和install smoke消费同一目标依赖映射；prepack内嵌预期映射和探针，不依赖未归档helper。helper加载native前检查core/metadata/export目录与所有库文件realpath，fresh install允许树内正常hoisting。原CLI模块、src/provenance/原始摘要、旧0.1.10与正常安装未改。

首次native探针误用了不存在的vipsVersion函数，按sharp 0.34.5的utility实际源码改为libvipsVersion并核对semver及来源；失败回执保留。Luna第一次命令wrapper产生127，随后重跑才是真实命令；主执行者又从原始日志发现Node26超出合同，故保留该轮结果并按Node24.13.0重新执行，不将超出工具链范围的通过当最终证据。

主执行者使用明确private npm fixture安装生产映射中的Bun1.4.0、native sharp0.34.5和libvips package1.2.4；selector/core/平台metadata与正常已发布原文件摘要逐项相同。最终Bun加载验证返回libvips8.17.3（[准备回执](/tmp/im-image-model-split-20261010/validation-round19/private-runtime-preparation.json)），没有修改正常安装或生成资格标记。实际公开SDK0.2.145新会话及相同session恢复均success，fixture Gateway恰有2次Messages POST、均观察server image blocks；原2400px素材40503cf…经过原CLI转换为2000px wire图7a21d…，resume保留历史图片并接受新的当前图片（[实际CLI输出](/tmp/im-image-model-split-20261010/validation-round19/cli-large-image.out)）。这是隔离实际CLI技术验证，返回图片由fixture提供，不是Responses真实模型生成。

Runtime新版本的四平台native加载、完整资格、新版pack/公开发布/正常安装和Dream pin采用未执行；不能为旧版0.1.10重制包。正常服务新capability/权限和指定真实账户、现有实体、AI/Image模型仍为真实业务验收前置限制。不存在正常数据库本轮Run/Thread/Token成功验收记录，目标没有标记完成。

### Round19最终命令与解释

Runtime命令由Luna在该仓库执行，完整命令均明确前置Node24.13.0的PATH并使用其npm11.6.2；兼容脚本及native探针实际使用项目/fixture的Bun1.4.0，ambient Bun1.2.20没有参与（[工具链回执](/tmp/im-image-model-split-20261010/validation-round19/runtime-toolchain.json)）。下表为修订后主回执，不采用Node26、首轮127或探针函数错误的结果。

| 命令 | exit | 关键输出及覆盖 |
|---|---|---|
| `npm test` | 0 | 62 tests，58 pass、0 fail、4 skip；四目标exact map、optional覆盖、actual Bun native/hoisting和真实库文件escape回归。[输出](/tmp/im-image-model-split-20261010/validation-round19/runtime-test.out) |
| `npm run lint` | 0 | modules1902、files2159；单一src与作者文件合同。[输出](/tmp/im-image-model-split-20261010/validation-round19/runtime-lint.out) |
| `npm run source:verify` | 0 | 1902 files、30,382,832 bytes、原inventory40269454…一致。[输出](/tmp/im-image-model-split-20261010/validation-round19/runtime-source.out) |
| `npm run npm:templates` | 0 | 10 generated templates verified；不执行发布stage/pack。[输出](/tmp/im-image-model-split-20261010/validation-round19/runtime-templates.out) |
| `npm run test:mcp-auth-compat` | 0 | 52 pass、231 expect、0 fail。[输出](/tmp/im-image-model-split-20261010/validation-round19/runtime-mcp-compat.out) |
| `npm run test:dream-compat` | 0 | 4 pass、71 expect、0 fail。[输出](/tmp/im-image-model-split-20261010/validation-round19/runtime-dream-compat.out) |
| `node prepare-private-runtime.mjs`（实际命令为Node24绝对路径） | 0 | 私有production映射安装、实际Bun加载、原CLI/metadata摘要相同；最终探针包括库文件检查。[命令](/tmp/im-image-model-split-20261010/validation-round19/private-runtime-preparation.final.command) |
| `PYTHONPATH=backend:. backend/.venv/bin/python cli-large-image-probe.py`（见完整绝对命令） | 0 | actual CLI/SDK新建和同session resume success、2 Messages、2400→2000px；fake Gateway。[命令](/tmp/im-image-model-split-20261010/validation-round19/cli-large-image.command)、[安全结构回执](/tmp/im-image-model-split-20261010/validation-round19/cli-large-image-receipt.json) |
| `python3 doc-check.py` | 0 | 33 Markdown文件、引用及line refs、历史原文/清单、265/150 registry、精确capability与冻结0079/0080一致。[输出](/tmp/im-image-model-split-20261010/validation-round19/doc-validation/doc-check.out) |
| `python3 extract-mermaid.py` + Node24 `mermaid-harness.mjs` | 0 / 0 | Mermaid11.17.2，10 diagrams、0 failures；现有Chrome，自有Vite/端口已结束。[输出](/tmp/im-image-model-split-20261010/validation-round19/doc-validation/mermaid-harness.out) |

Runtime四项skip为：两项原官方comparator/Dream Python对照及失败资格收据fixture未提供；pipe与PTY两项原headless MCP OAuth fixture未设置专用Python/root。它们不是图片回归通过，也不与本次已通过的52项源合同混算。新代码没有触及这些协议，不使用旧资格回执填补skip。

所有命令/out/exit原始回执已由主执行者读取。新增本轮自有private-install及CLI home/thread目录已按明确路径删除，安全JSON、摘要、命令与失败日志保留；删除前再次验证正常selector/core/平台metadata摘要未变（[清理回执](/tmp/im-image-model-split-20261010/validation-round19/owned-runtime-cleanup.json)）。没有改正常服务、真实数据库或既有dist删除。

最终交付状态：当前源码和文档、独立评审修订、完整隔离可见旅程及新增实际CLI图片技术观察已交付。既有两个来源聊天未另建或代发；当前专项目标仍active，正常Runtime新版采用、capability发布和指定真实账户/实体/模型的完整真实验收未完成。该续轮发现并修复新的前置代码缺口，属于实质进展，不作为同一阻碍连续三轮的blocked状态。

## 正常验收前置复核（2026-10-11，goal续轮）

上一轮为实质进展：Runtime打包源码及四项独立评审修订、锁定工具链检查和2400px实际CLI新建/resume均新增权威状态。本轮沿对应两个既有聊天分页读取至最早用户消息（hasMore=false），没有发现指定的真实账户、已有实体或明确AI/Image模型；不从assistant提议或fixture身份推导授权。正常安装selector/core/平台metadata重新核对仍与round19摘要相同，平台依赖仍仅Bun。

**Expert Prompt Architect — Optimized Prompt**：你是当前专项主执行者。完整目标仍含两条图片链路及正常真实业务验收。以当前正常配置与明确只读事务复核Gateway精确image-turn capability；必须调用现有getPool与imageTurnCapabilityAvailable，不复制业务状态机或更改Schema/权限。验证连接实际为本机正常数据库，只输出capability存在/匹配/就绪与SQLState等安全事实，不输出凭证或业务正文。缺指定身份或发布前置时保留完整未验证范围，不执行模型请求、不创建替代实体。此前技术矩阵未改且已通过，不重复无关检查。

**执行计划**：沿现有Admin配置装载正常数据库DSN→核对loopback及实际database→BEGIN READ ONLY→读取精确capability并调用现有生产就绪边界→ROLLBACK并关闭仅自有pool→保存安全回执。该检查是前置只读证据，不能当作真实业务或完整模型验收。

**本轮权威结果**：两个来源聊天均分页到hasMore=false：Dream读取18个turn/24条userMessage，Admin读取24个turn/19条userMessage，未发现本轮指定真实身份、实体或AI/Image模型。正常Runtime三个摘要仍与round19一致，已安装平台dependencies仍仅bun1.4.0。

正常配置对应Gateway pool的只读检查命令为`node --conditions=react-server --import tsx /tmp/im-image-model-split-20261010/validation-round20/normal-prerequisites.mjs`（实际Node24绝对命令见[command](/tmp/im-image-model-split-20261010/validation-round20/normal-prerequisites.command)）；exit0。实际database=ink-memory、role=ink_memory、transaction_read_only=on；capabilityPresent=false、capabilityMatches=false、生产imageTurnCapabilityAvailable=false（[安全回执](/tmp/im-image-model-split-20261010/validation-round20/normal-prerequisites.json)）。没有读取用户正文、调用模型、业务写入、migration、grant或服务修改；自有pool已关闭。首轮验证脚本引号错误在连接前退出，修正后才完成上述只读检查，initial失败回执保留，不归因于Gateway。

本轮未改变功能状态或取得新的真实模型验收，归类为no progress（前置复核），不是等待中的live job。本轮是上一实质进展之后同一真实验收阻碍的第1轮；身份/实体/模型指定及正常capability、Runtime新版采用仍缺失，完整目标保持active，未达到连续3轮blocked门槛。没有通过重复技术矩阵或仅修改记录将专项标记完成。

## 最终阻塞审计（round21–22，2026-10-11）

round21为连续同一阻碍第2轮：两个来源聊天更新时间未变，正常数据库的生产就绪检查仍为false，正常Runtime selector/core/平台metadata摘要仍与round19相同；没有功能修改或真实验收。[round21回执](/tmp/im-image-model-split-20261010/validation-round21/input-and-runtime-audit.json)保留当时active状态。

round22为连续同一阻碍第3轮。主执行者重新执行[正常数据库只读命令](/tmp/im-image-model-split-20261010/validation-round22/normal-prerequisites.command)，exit0；实际ink-memory / ink_memory / read_only=on，精确capabilityPresent、capabilityMatches及生产gatewayReady均false（[输出](/tmp/im-image-model-split-20261010/validation-round22/normal-prerequisites.json)）。capability行缺失，不能据此推断角色权限已经满足或缺少哪项grant。正常安装三个摘要均未变，实际dependencies仍仅bun1.4.0（[Runtime复核](/tmp/im-image-model-split-20261010/validation-round22/normal-runtime-audit.json)）。两个来源聊天更新时间仍为1791638007、1791592310，没有新的指定真实身份、已有实体或AI/Image模型输入。

三个独立评审/验证代理均completed，没有confirmed live job等待。源码、文档、独立修订和本专项修订后技术回执已交付；剩余正常Runtime新版本资格/发布/采用、精确capability发布及指定真实业务验收无法由重复隔离测试完成。Schema合同只允许本轮migration技术验证使用具名隔离数据库；本轮不向正常库执行DDL或grant，不任选真实账户或建立影子实体，也不重制已发布0.1.10。没有正常服务修改、模型调用或业务写入。

依据[三轮阻塞审计](/tmp/im-image-model-split-20261010/validation-round22/blocked-audit.json)，当前专项目标转为**blocked / 完整真实业务验收未完成**；不是暂停或完成。前述各轮active记录保留为历史状态。未验证范围仍是本记录“当前交付限制与任务状态”及正式稿验收矩阵中的正常服务完整链路，不能用本机私有CLI、fake Provider或隔离PG回执替代。

## 用户补充账户与生产发布授权（2026-10-11）

用户提供现有账户登录输入，并明确要求“Runtime验证后走生产发布”；后续不提问。密码不进入源码、执行稿或验收日志。该输入解除账户未指定的限制，已有业务实体及模型选择先从该账户公开页面核对；不创建替代身份、订阅或账本。目标恢复active，原blocked记录保留为历史。本轮正常Dream/Admin/Gateway/PostgreSQL服务分别从现有监听和README入口确认；不以新起隔离服务冒充。

**Expert Prompt Architect — Optimized Prompt**：继续原完整图片专项目标，主执行者负责真实账户操作、Runtime版本与生产发布/采用。已修复的native依赖代码使用现有单一源码及四平台qualification/publish链路。当前Runtime main及本机HEAD均为4be8fc81364d1050ef3eeee22f1ce3ae30d4c86f，远端没有相关未合并PR；公开五包均latest0.1.10，候选0.1.11均不存在。源码工作区包含本任务18项修订及用户原有114项旧生成物删除，必须隔离提交范围。新版本不得改src/provenance或覆盖旧包，不降低四平台、SDK/MCP、native安装、版权或精确制品门禁。所有正常业务步骤走公开生产入口，保护凭证和正文；正常Schema发布仍受Admin Drizzle及工作区协议约束。

**计划**：在明确命名的Runtime release worktree复制本任务拥有的修订，按现有政策原子推进0.1.11并同步受影响版本合同；独立复审实际release改动，Luna执行新候选的确定性与本机隔离检查。主执行者完成scoped PR、等待真实CI、合并、跟踪同一源SHA的四平台资格及五包生产发布，逐包验证公开完整性。成功后安装精确新版本，同步Dream pin/resolver/依赖及文档，并按发布合同完成正常采用证据。并行使用用户指定账户可见登录，读取当前设置、已有实体及公开模型资格，继续可执行的真实流程；缺capability等阻碍明确记录，不用隔离结果代替。每个阶段只据真实命令/任务句柄推进，不将dispatch或旧绿色视为完成。

### round23：新版本候选、实际评审与当前 CI

候选工作树为`/tmp/im-runtime-image-0.1.11-20261011`，只提交本任务拥有的native修复及0.1.11版本/文档合同，42文件；原Runtime工作树的114项历史生成物删除保留。提交`3a6c75a70514c6bb31340a87bc8e28adaa549c27`已经[PR #28](https://github.com/glide-the/ink-claude-code-dream/pull/28)进入main，merge SHA为`a60eb7f3b5e4af39479b07eac7aef93b538c7723`。独立复审关闭了将0.1.9历史资格写成当前候选资格的P2；版本合同一致，原src/provenance和旧回执未改，未发现新增代码P1/P2。

Luna按根执行者编写的明确命令在Node24.13.0/npm11.6.2下重跑新候选：lint、source、templates、legal、diff均exit0；Runtime单测62项55pass/7skip/0fail，MCP兼容52pass，Dream兼容4pass。补充显式现有Dream/Python的focused检查16项13pass/3skip/0fail，exit0。三skip是两项官方comparator和正常Dream仍精确固定0.1.10的manifest验收，未称通过。最初focused外层日志重叠已保留为`initial-overlapped`证据，同命令重新执行后由根执行者读取完整独立raw输出。最终文档检查15文件/35本地链接无缺失，exit0。命令、raw输出、退出码在[round23目录](/tmp/im-image-model-split-20261010/validation-round23)。

`git push -u origin codex/runtime-image-native-0-1-11`、`gh pr create … --body-file runtime-pr-body.md`及绑定候选SHA的`gh pr merge … --squash --match-head-commit 3a6c75a70514c6bb31340a87bc8e28adaa549c27`均exit0。[本轮PR源码CI](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38081614548)成功，watch命令exit0；同merge SHA的[四平台资格](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38081685997)已真实启动，当前尚未完成。排队或开始执行不等于资格、公开发布或正常采用成功。

指定账户已通过本机Chrome的实际Admin邮箱表单提交。页面停留`http://localhost:3000/admin/login`并显示`The email or password is invalid`，未建立认证账户，未读取现有实体或模型，模型调用0次。Dream登录表单实际指向远端Admin认证origin，因此没有将远端登录冒充本机正常业务。自动选择Google入口的初次操作没有提交Google凭据，已返回本机并使用明确邮箱form selector。所有本轮加密auth profile已删除、命名自有浏览器已关闭，凭据不写入回执；[安全结果](/tmp/im-image-model-split-20261010/validation-round23/normal-account-login.json)。账户“未指定”的旧限制已解除，当前限制是本机指定账户登录被拒绝。

### round23：生产发布、公开字节与正常Runtime采用完成

同merge SHA `a60eb7f3b5e4af39479b07eac7aef93b538c7723` 的main源码CI `38081686094`、四平台资格 `38081685997`、自动生产发布 `38082683882` 全部success。四host均59pass/3skip/0fail；独立实际SDK/MCP differential和stage/fresh-install native smoke通过。3skip为两个comparator fixture前置和旧Dream精确pin不匹配的production manifest测试；没有将skip算成正常采用。五包按平台先于selector顺序通过既有CI发布，无本地npm publish。原始CI输出和最终qualification summary已读取，首次任务尚未结束的log查询exit1不作为失败或通过证据。

主执行者下载该qualification精确归档，重新下载公开五包核对SHA-512 integrity、SHA-256、平台、依赖及字节一致，`verify-public-runtime.py` exit0。selector SHA-256 `88ae16a19b7f92aa1fea92b7522daf182faeca89c9b1818de53ca91d796e4f2a`，四平台完整摘要在[当前发布接入回执](../deploy/runtime-0.1.11-image-native-and-dream-adoption.md)。正常Node24.13.0/npm11.6.2精确global install 0.1.11 exit0；默认PATH resolver和相邻manifest通过，无CLI override；实际Bun1.4.0加载sharp0.34.5、libvips package1.2.4 / library8.17.3。没有重制0.1.10或改变SDK/原始src。

Dream源码精确pin、Docker、AutoDL默认合同和启动期望同步0.1.11，backend/frontend metadata仍0.1.4/0.0.4；只更改事实变化的合同，没有远端部署或Docker构建。Luna执行根作者的发布后检查，主执行者读取实际command/out/exit：

| 本轮命令 | exit | 实际输出 |
|---|---|---|
| `.venv/bin/python -m pytest tests/test_sdk_env.py tests/test_dockerfile_claude_contract.py tests/test_verify_claude_registry_release.py tests/test_claude_plugin_cli.py -q -p no:cacheprovider` | 0 | 66passed / 13subtests passed |
| `.venv/bin/python -m pytest tests/test_server_claude_agent.py -k startup -q -p no:cacheprovider` | 0 | 4passed / 92deselected，25项现有on_event warnings |
| `python published-cli-image-probe.py`（完整argv见round23 command） | 0 | 实际公开0.1.11 CLI/SDK2400px新会话及同session resume success；2Messages POST，分别含2000px wire图片和两类server image blocks；自有fixture已删除 |
| `python3 adopt-normal-dream-runtime.py` | 0 | 正常进程env仅内存保留，manifest预检、指定后端SIGTERM及原server.py/cwd重启、新启动身份通过，其他三个正常listener PID未变 |

该CLI probe使用loopback fake Gateway，不是正常模型调用。后端原PID79939无活动Runtime子进程，新PID35255打印SDK0.2.145 / Runtime0.1.11 / cli_mode=dream_runtime / CLI compatibility2.1.241，health200；该正常服务保留运行。最初psutil检查因模块缺失在读取前exit1；未加运行依赖，改用macOS原生只读接口。先前process args查询误显示debugpy临时adapter token，已停止输出完整args，后续只记录安全PID/cwd/身份；不将token写入仓库或回执。旧debugpy目标已退出。

正常生产前置只读命令重新运行exit0，实际ink-memory / ink_memory / read_only=on；精确image-turn capability存在false/匹配false/gatewayReady=false，写入0。指定账户已提供，当前缺口是本机邮箱登录被拒绝，不能恢复成“账户未指定”。没有账户重置、Schema/权限修改、真实模型调用或正常业务验收记录。完整两路生成/编辑、语义选择、草图、正常图片/文件/历史/Token结算及断线取消重试仍待真实验收。

### Expert Prompt Architect — 发布完成后的收尾提示

**Optimized Prompt**：你是原图片专项主执行者。生产Runtime0.1.11已完成同源资格、发布、公开归档检查和正常Dream采用。只把新权威证据同步到现行稿，保留历史回执；Runtime跟进提交仅文档，不触发同版本资格重建或再次发布。独立评审实际当前稿及边界，Luna执行具名确定性文档/引用/图语法检查；所有CI与命令读取真实回执。Runtime原工作区114项用户历史生成物删除必须逐项保护，本任务18项修订已进入#28，只有证实其已被提交覆盖后才做限定路径备份及fast-forward。不得正常DDL/grant、重设账户、重复模型请求或把未完成业务验收写成complete。

**执行计划**：修订Runtime当前发布状态文档→独立复审并确定性验证→文档only PR/源码CI/精确合并→保护原工作区用户改动并同步已提交版本；同步Dream现行PRD/正式稿/依赖设计/目录合同→新文档引用和Mermaid检查→根读取真实回执并核对正常后端身份/其他服务保持→交付准确完成与阻碍状态。该计划不增加配置或运行路径，正常图片真实验收限制继续单独记录。

文档收尾独立评审发现并修订四项P2：中文手册/兼容报告将npm平台core JS及精确Bun运行依赖误写为standalone不依赖Bun；旧发布关闭关系图未标历史；历史Comfy/OAuth计数被“本轮”标题混用；Runtime根目录正文仍以当前语气写0.1.9及后端已停止。现已按实际包/启动身份改正，历史图和计数保留并标范围，新当前流程图明确真实图片验收受阻。没有因此修改运行代码或重新资格/发布0.1.11。

Runtime原正常源码工作区已安全fast-forward到已发布SHA a60eb7f3：四个native实现文件含helper逐字节与发布commit一致；另三实施合同只差0.1.11版本/同步头，检查通过后仅本任务18路径做scoped stash及独立文件摘要备份。用户114项dist历史文件删除的路径集合和删除状态前后逐项相同，未stage、恢复或提交；src/provenance无diff。scoped stash `802e85a185705d361cff03043055af45d5e216d9`及具名备份保留，未pop旧版本覆盖新源码。

文档检查首轮：48文件/486本地链接/79行号、31外部引用跳过，历史/清单/265和150注册合同/精确capability/冻结migration/PRD骨架通过；Runtime8文档37本地链接无缺；Mermaid11.17.2对13图parse成功。但Dream `git diff --check` exit2发现本轮docs/deploy/.folder.md末尾多余空行，Admin/Runtime diff尚未执行。原始回执完整保留于round23/initial-final-doc-whitespace；修正仅该空行后重跑同一driver，不能将首轮部分通过报完整通过。

文档收尾独立复审确认上述四P2全部关闭，无剩余P1/P2。本轮修正后的Luna完整doc driver exit0，主执行者读取全部真实command/out/exit：48文件、486本地链接、79行号，31外部引用明确跳过；Runtime8文档37链接无缺；Mermaid11.17.2对13图均成功；Dream/Admin/Runtime各自diff --check exit0。自有Mermaid Chrome/Vite/端口已结束。文档检查不计入功能或真实业务验收。

文档only提交 `40323d6a3aba5e442de42c6420c88106c8646be7` 已创建并附加[Runtime #29](https://github.com/glide-the/ink-claude-code-dream/pull/29)，8文档89insert/16delete；不改运行代码、版本、workflow、已发布字节或历史回执。当前源码CI `38084138670` 已启动，待真实回执后合并；公开0.1.11资格仍绑定a60eb7f3，不能改绑该文档commit。

### 本轮最终交付状态

[Runtime #29](https://github.com/glide-the/ink-claude-code-dream/pull/29)已绑定head40323d6精确合并，merge/main为 `a4a2e306ca7f5af8a153f53c4964ec658541a1c6`；PR源码CI38084138670与main源码CI38084198870均success，主执行者读取原始输出。该文档only提交没有重建或重复发布0.1.11；其生产资格/公开归档保持绑定a60eb7f3。正常原Runtime源码工作区再次safe fast-forward至a4a2e306，8份当前文档与已复审提交逐字节相同，114项用户删除的路径及状态完全保留，scoped备份保留。

最终正常listener核对通过：Dream新后端35255保留运行；Admin64237、Dream前端84357、PostgreSQL64180未变。安全身份与native/manifest结果已保存，私密正常启动日志权限0600，不转写env或凭据。没有远端部署、镜像构建、正常库Schema/grant、账户重置或真实模型调用。

既有Dream聊天“调研并设计 Tool 图像生成交互”与Admin聊天“Image 模型中心：调研、设计、实现与验证”沿用作来源，旧turn completed，当前不另建或代发。当前专项目标active / 未完成，Runtime发布子范围已完成，全部不依赖认证及capability的代码/文档/评审修订与受影响技术检查已经交付。剩余正常模型语义选择、两路生成/编辑、草图理解、图片文件/历史/结算及连接取消重试没有真实业务回执，不用本轮Provider-free或历史结果替代。

最终记录及正常Runtime源码同步后的Luna close-doc检查exit0：48文件、486本地引用、79行号，33外部引用跳过；旧原文/清单/精确capability/版本/265与150注册合同全通过，三个正常源码工作区diff检查exit0。主执行者已读全部实际command/out/exit。13张图在前一独立门禁均parse成功，图未再变化，不重复浏览器。

正常进程采用后最终重新执行final-normal-prerequisites.mjs：exit0，ink-memory / ink_memory / transaction_read_only=on，capabilityPresent=false、capabilityMatches=false、gatewayReady=false；写入0，自有pool已关闭。指定账户本机登录拒绝证据保留；不重设账户或绕过Schema。当前goal最新工具回执仍active，当前resume轮取得生产发布及正常采用的实质进展，未满足新一轮连续三轮blocked条件，且完整真实图片验收没有完成，因此未标complete或paused。

## round24：纠正登录证据范围并验证 Dream 实际入口

**Expert Prompt Architect — Optimized Prompt**：继续原专项完整真实验收。复核生产认证模块发现，round23提交的`/admin/login`只检查独立`admin_users`，不能据此判断指定Dream用户凭据无效。Dream邮箱表单使用`/auth/dream/password`的Better Auth用户域；公开认证authority和内部transport的分离是现有合同，不能仅凭公开origin认定替代环境。保持正常配置，通过当前Dream页面实际邮箱登录一次，保护密码、cookies和OAuth code，不重设账户、不替换入口或修改Schema。根据实际回调、账户与正常数据入口确认认证结果；只有正常业务链路证据才能支持真实验收。

**调整计划**：复用已安装Chrome与具名自有会话→检查当前页面邮箱form和公开action→凭据仅由加密auth vault及隐藏stdin提交→读取安全反馈与回调结果；认证成功后读取该账户已有设置、实体和公开模型目录，继续不依赖缺失capability的流程。重新只读检查正常image-turn capability，阻碍时fail closed；保存新回执并纠正现行稿中的认证结论，保留round23原始Admin拒绝历史，再独立复审与文档检查。不重复已通过且未变化的Runtime或隔离图片技术矩阵。

**证据范围修正**：`normal-account-login.json`的scope明确为本机Admin邮箱登录；`adminAuthService.signInAdminOnTransaction`仅查AdminSessionRepository，而`dreamBrowserEntry.handleDreamPasswordEntry`调用Better Auth的`signInEmail`。此前“指定账户本机登录被拒绝”的泛化结论不成立；准确结论是Admin管理身份登录被拒绝，Dream指定用户登录尚未验证。旧原始回执不改写。

**本轮实际可见操作**：复用已安装Chrome（headed），不重复startup check或安装浏览器；正常`http://localhost:5173`快照显示Email/Password/Login，DOM只读核实邮箱form action为配置的`https://ink-admin.suoxya.com/auth/dream/password`、method POST及mode login。具名加密auth profile从隐藏TTY stdin取得密码；使用`form:has(input[name="password"])`下的邮箱/密码/submit selector，未选择Google或Register。`agent-browser … auth login` exit0仅说明automation动作成功，不能当作登录成功；回到本机`/auth/callback`时，安全字段为`error=invalid_scope`、`error_description=The following scopes are invalid: images:create`，JSON detail=`BFF_OAUTH_CALLBACK_INVALID`。没有输出完整URL、state、cookies或凭据。认证本机会话未建立，已有实体/模型尚未读取，真实模型调用0；profile已删除，owned Chrome会话已关闭。[安全登录回执](/tmp/im-image-model-split-20261010/validation-round24/dream-account-login.json)及[页面截图](/tmp/im-image-model-split-20261010/validation-round24/dream-oauth-callback-failed.png)保留。

**独立调查与最小判断**：公开authority和localhost3000的`/api/auth/.well-known/openid-configuration`无凭据GET均HTTP200、同issuer、scopeCount23且images:create声明为true（[metadata回执](/tmp/im-image-model-split-20261010/validation-round24/authority-scope-metadata.json)）。已安装官方OAuth Provider的[authorizeEndpoint](/Users/dmeck/project/ink-admin-memory/node_modules/@better-auth/oauth-provider/dist/authorize-zWEGx4ky.mjs:5556)先按`client.scopes ?? opts.scopes`校验并生成同一错误描述，早于resource、PKCE及用户Session。因此本轮证明该OAuth client请求被公开authority拒绝；实际client scope目录不一致是最强解释，但未读取公开authority对应row，不能断言具体登记步骤遗漏，也不能认定Dream密码有效/无效或Provider全局不支持。

[capabilitiesHandler](/Users/dmeck/project/ink-admin-memory/app/lib/auth/capabilitiesHandler.ts:27)广告编译时authScopes；BFF [start](/Users/dmeck/project/ink-dream-memory/frontend/app/api/_auth/handlers.ts:47)从内部transport取得后原样请求公开issuer。[独立评审](/tmp/im-image-model-split-20261010/validation-round24/auth-independent-review.md)确认不按image Schema/role readiness删images:create，不改变BFF或正常目录绕过失败。OAuth scope、gateway.images.v1及dream.image-turn.v1/原角色权限分别表达授权、Images Schema及turn执行合同。现有[provisionDreamOAuthCatalog](/Users/dmeck/project/ink-admin-memory/app/lib/auth/oauthClientCatalog.ts:332)能先dry-run比较配置目标/实际目录，显式apply后回读；这是建议、未执行的Admin目录发布恢复，不是本轮Runtime五包发布，也不采用runtime自修或新控制通道。

**正常Schema边界复核**：`node --conditions=react-server --import tsx validation-round24/normal-prerequisites.mjs`（实际cwd/绝对argv见[命令](/tmp/im-image-model-split-20261010/validation-round24/normal-prerequisites.command)）exit0；实际ink-memory / ink_memory / read_only=on，精确capabilityPresent=false、capabilityMatches=false、生产gatewayReady=false，写入0，自有pool关闭（[输出](/tmp/im-image-model-split-20261010/validation-round24/normal-prerequisites.json)）。这是独立于OAuth失败的图片执行阻碍，不推断grant状态，不执行normal DDL/grant或目录登记。未更改功能代码，因此本轮只复审修订稿并做受影响文档/图检查，旧完整技术矩阵不重跑也不称为本轮真实验收。

**当前稿复审及验证**：独立只读评审核对正常Runtime仓库和Dream的实际修订稿，无剩余P1/P2；Runtime发布/采用仍完成，待验收只指图片正常业务。Luna执行`python3 validation-round24/run-doc-checks.py`，外层及六项内层均exit0。主执行者读取真实command/out/exit：48文件、497本地引用、83行号、33外部引用明确跳过，旧原文/清单/265与150注册/精确capability/冻结migration/PRD骨架均通过；受影响Runtime正式稿5图由Mermaid11.17.2解析5/5、0fail，图片正式稿3图未变化、未重复浏览器。Dream/Admin/Runtime diff检查均exit0；自有Vite端口55620及Chrome已关闭。这些是文档检查，不计功能或真实模型验收。正常Schema只读命令由主执行者执行，独立于Luna文档driver。

**Expert Prompt Architect — 认证证据收尾 Optimized Prompt**：保持已发布Runtime版本、资格SHA和公开字节。正常Runtime仓库当前4份文档已经复审，纠正Admin拒绝与Dream OAuth失败混用；应同步到同一源码主分支，避免远端当前发布记录继续保留错误判据。复用此前具名release工作树，禁止碰用户114项历史删除或src/provenance；不重建或重新发布五包，不操作正常认证目录、Schema或账户。

**收尾计划**：在tracked clean的既有release工作树从当前main创建限定文档分支→复制这4份逐字节已复审稿→scoped提交/PR并等待真实源码CI→精确合并→比较正常Runtime4文件与提交字节，只暂存本任务4路径做安全fast-forward，逐项验证用户114删除保持→读回CI和文档最终验证。该范围只修订发布证据，不解除OAuth/Schema阻碍或宣称完整业务完成。

**收尾实际回执**：4份已复审Runtime文档逐字节复制后提交`052f4cb77bfde99534762956cefe5c28725a2800`，7insert/5delete，源码/版本/workflow/公开字节不变。[Runtime #30](https://github.com/glide-the/ink-claude-code-dream/pull/30)已创建并附加本聊天；PR源码CI38085085377 success、watch exit0，根读取raw输出：62项55pass/7skip/0fail，MCP52、Dream4通过。其7skip仍为源码CI的既有fixture前置，不能替代四平台资格或真实模型验收。绑定head052f4cb精确squash合并后main为`6bc0df376ab91b6c83994cf994d592a91b3801d2`；main源码CI38085343516 watch exit0。文档only路径没有再次资格或发布0.1.11，生产资格及五包仍绑定a60eb7f3。

正常Runtime源码工作树只对本任务4路径保存逐字节备份及scoped stash `243396073eb5d93cc17972dac22be5088873f056`，safe fast-forward到6bc0df3；最终只剩114项用户历史生成物删除，前后路径与状态逐项相同，src/provenance无diff，4稿与已复审merge字节相同（[同步回执](/tmp/im-image-model-split-20261010/validation-round24/runtime-auth-doc-source-sync.json)）。没有pop旧stash覆盖新稿。Luna最终close库存/diff回执再次exit0、497links/83行号/33外部跳过；根已读真实输出，runner明确未额外执行正常DB/服务/认证命令，前述prerequisite JSON属于根的独立检查。

正常服务4个listener PID与本轮入口一致，后端35255仍运行公开0.1.11，正常release-manifest SHA256与采用回执相同（[服务回执](/tmp/im-image-model-split-20261010/validation-round24/normal-service-audit.json)）。最初harness把capabilities.json摘要与release-manifest预期比较，现已按实际文件修正并保留initial回执；不是Runtime或正常安装变化。没有正常服务重启、Schema/权限/目录/账户修改、真实图片请求或新增替代业务实体。

**当前任务状态**：两个既有来源聊天仍沿用，未创建重复任务或代发。完整goal active / 未完成；Runtime发布子范围完成。OAuth客户端scope拒绝与正常精确image-turn capability缺失是当前两个独立真实验收阻碍，本轮真实入口失败原因已定位及独立复核，作为这组阻碍的第1轮审计记录；尚未满足连续3轮blocked门槛。普通/显式两路生成编辑、草图理解、原文字/普通工具/媒体/历史的正常账户流程及正常Run/Thread/Gateway/Token结算仍未通过真实业务验收，不以已交付技术矩阵替代。

round24最终追加记录与正常Runtime文档source同步后的Luna收尾检查：final-doc-check和三个final-diff均exit0；48文件、499本地引用、83行号、34外部引用跳过，其余历史/清单/注册/capability/冻结migration/PRD合同通过。主执行者已读取真实command/out/exit。main源码CI38085343516的raw确认success、同6bc0df3、55pass/7skip/0fail、MCP52/Dream4；所有本轮CI和文档job已完成，没有confirmed live job。完整goal仍active，当前正常真实验收阻碍第1轮，未标complete或paused。

## round25：连续正常Schema阻碍审计

**Expert Prompt Architect — Optimized Prompt**：原完整目标不缩小。上一轮是实质进展：真实Dream入口失败定位、独立复审及更正稿/Runtime文档PR合并完成。本轮只重新核对剩余正常执行前置，不重复已通过的Runtime、Provider-free或隔离浏览器矩阵，不重复提交密码，不以状态记录制造进展。新OAuth原因不重置持续存在的同一Schema阻碍；阻塞计数按恢复后的三个真实goal turn和各自精确只读回执核对。未建立本机用户会话的最新观察仍为round24，不把未重试写成新的认证结果。

**审计计划与实际**：复用已审阅normal-prerequisites脚本，仅将本轮输出改到具名round25目录；Gateway getPool/生产imageTurnCapabilityAvailable、BEGIN READ ONLY、实际identity及精确capability、ROLLBACK、自有pool关闭。实际[命令](/tmp/im-image-model-split-20261010/validation-round25/normal-prerequisites.command)exit0，ink-memory / ink_memory / read_only=on，capabilityPresent=false、capabilityMatches=false、gatewayReady=false、写入0（[输出](/tmp/im-image-model-split-20261010/validation-round25/normal-prerequisites.json)）。没有DDL/grant、OAuth目录登记、账户修改或模型请求。正常Runtime包/manifest仍与采用回执相同，source HEAD6bc0df3，四listener PID与round24逐项相同（[状态回执](/tmp/im-image-model-split-20261010/validation-round25/runtime-and-service-audit.json)）。

**计数更正及结论**：round24将“OAuth+Schema”作为新阻碍组记第1轮，但精确Schema缺失实际上在恢复后的round23、24、25三轮连续存在，不能因新增认证诊断而重置这个相同条件。主执行者读取三个JSON并验证实际database/role/read_only、同capability version/hash、false就绪和写入0；[blocked审计](/tmp/im-image-model-split-20261010/validation-round25/blocked-audit.json)证明门槛满足。三个独立代理均completed，所有本轮CI/测试已terminal，没有confirmed live job。当前轮是no progress前置复核，不是verified wait；已经完成全部不依赖这些前置的授权工作，剩余真实业务验收无法继续，完整目标转blocked / 未完成，既有来源聊天保留、不创建重复任务。

恢复需要既有Admin发布合同中的精确image-turn capability，以及对配置OAuth客户端目录的核对和同步；本轮没有执行这些正常发布写操作，不改变BFF请求scope或绕过执行检查。正式稿中的两路真实生成/编辑、语义分工、草图、普通文字/工具/媒体及正常文件/历史/结算/断线取消重试仍未通过正常账户验收。Runtime0.1.11生产发布和采用保持已完成；文档检查及所有隔离结果不能将完整目标改为complete。

round25文档收尾由Luna执行，主执行者读取实际command/out/exit：库存检查exit0，48文件、503本地引用、83行号、34外部引用跳过，历史/清单/注册/capability/冻结migration/PRD合同全部通过；Dream/Admin/Runtime diff均exit0。未运行浏览器或功能矩阵，没有新的真实模型或图片验收；验证代理已结束。阻塞审计证明恢复后的三轮相同Schema条件，目标状态提交blocked，不是暂停或完成。

## Round26：用户授权正常库受控发布与真实验收恢复

**Expert Prompt Architect — Optimized Prompt**：角色为当前专项主执行者；上下文为 Runtime0.1.11 已资格验证、生产发布及正常采用，正常库尚缺精确 image-turn capability，实际 OAuth 客户端此前拒绝 images:create。任务是先核对正常库身份、Drizzle 严格前缀和受控目录实际差异，按用户本轮授权发布必需前向迁移并同步实际客户端图片 scope，再通过现有账户和正常公开入口重新完成可见业务 E2E。约束是不绕过 capability，不补 runtime DDL，不替换账户/数据库/Gateway，不修改无关目录字段、服务、线程或运行语义，保护凭证及所有未提交工作；主执行者负责正常迁移和真实模型，Luna只负责确定性/隔离验证。交付为原文保留的发布前后回执、独立复审、实际用户旅程、模型调用身份与存储证据、当前限制和准确最终目标状态。验收以真实公开业务操作及正常数据库记录为准，技术隔离结果不能替代。

**计划（双钻石交付阶段）**：1. 只读核对正常库、迁移前缀、原Gateway角色资格、OAuth客户端和资源目录，独立评审实际计划。2. 通过Admin现有Drizzle runner锁定目标迁移，目录同步先核对字段差异并回读；必要前置随实际结果修订最小范围。3. 现有账户登录，通过设置、主对话、图片工具、上传/草图、访问/保存/重开完整旅程，逐项记录真实调用与正常Admin可查询记录；确定性与隔离故障矩阵交Luna新执行。4. 对实际缺陷先修订设计再实现和复验，同步文档，只有要求全部完成才标完成。

**业务概念与影响简报（任何正常发布/浏览器/模型操作之前）**：

| 概念/事实 | 源头与写入责任 | 最终消费者 | 本轮预期 |
| --- | --- | --- | --- |
| Project / Episode | 既有故事规范文件和成功主轮Hook | 故事/章节页面 | 不在本图片专项范围，不改既有故事正文 |
| Chat Thread / Claude会话 | 现有ClaudeAgentService、Admin消息与线程DTO | 主对话、历史恢复 | 用户可见的新轮次；保留已有会话身份 |
| 图片素材与结果文件 | 现有媒体上传/草图、图片结果处理、线程文件模块 | 图片卡片、查看、下载、后续引用 | 实际结果持久化，编辑保留原素材 |
| Run-private .dream 发布 | 原成功主轮Hook，仅实际工作区参与时适用 | 原文件API及下游消费者 | 不引入图片专项的另一份故事发布协议；没有该发布的聊天不伪称有 |
| after-turn Hook / 调用ID | CLI真实Hook与Provider工具ID、Admin图片轮receipt | 请求关联和历史 | 两条互斥链路各保留真实ID；不改恢复/取消协议 |
| PostgreSQL / API投影 | Admin Drizzle发布、原Gateway角色、原消息DTO | 正常Admin请求/结算、Dream文件与历史API | 仅用户授权capability和scope发布及普通业务写入 |
| 设置选择 | 原模型目录、原偏好保存 | AI与Image列表、下一轮调用 | 两项独立保存/刷新恢复；不自动切换模型 |

本轮 Chrome 启动轻量检查复用已通过的前置回执，不重新安装浏览器。下文命令均为本轮新执行；过去技术通过仍属过去证据。

### Round26受控发布实际回执

两位独立评审发现原目录apply会写`dpopBoundAccessTokens=false`，初始audit未覆盖此字段；主执行者补查5个实际目标client全部原值false后，才复用原发布入口。没有新增配置、目录代码或grant。

- 初始operator wrapper缺显式migration DSN的预检exit1，没有连接/写入；随后由主执行者把已核对的正常DATABASE_URL明确绑定为本次runner的MIGRATION_DATABASE_URL。不存在产品runtime fallback。
- `pnpm --filter @ink-memory/db migrate --through 0080_image_turn_capability --status` exit0：严格前缀79项到0078，pending仅0079空占位和0080。
- 同runner受控apply exit0：两项提交；`--check` exit0，81/81 current、pending空。精确capability与原ink_memory角色USAGE/SELECT/INSERT/audit INSERT全部通过，原`imageTurnCapabilityAvailable`=true。
- `pnpm auth:provision-dream-oauth --apply` exit0、verified=true。此前资源allowedScopes和3个public客户端scopes各仅缺images:create；2个service客户端、links、secret/hash、redirect、PKCE、DPoP等无业务差异。发布后重新只读audit exit0，所有plan项unchanged、差异空。
- 原正常前端5173已不再监听，启动Next时首次`pnpm run dev -- --hostname ...`因多余`--`被当目录而exit1（harness命令错误，未启动服务）；修正为`pnpm run dev --hostname 127.0.0.1 --port 5173`，正常入口ready。保留原backend/Admin/PG listener，不停止用户已有服务。

受控发布回执位于[/tmp round26](/tmp/im-image-model-split-20261010/validation-round26/)，数据库身份ink-memory，Gateway角色ink_memory、auth角色ink_auth；DSN/凭证不写文档和安全回执。独立复审问题已在apply前解决。真实业务E2E正在本机正常页面执行；发布成功尚不等于图片验收通过。

### Round26用户纠正：本机认证中心必须使用本机地址

**Expert Prompt Architect — Optimized Prompt（调整计划前）**：用户明确纠正“local登陆应该是local”“认证中心跳转错了”。角色仍为主执行者。新证据是Admin `.env.local` BETTER_AUTH_URL及Dream前后端authority/issuer仍指公开HTTPS，而transport是正常本机3000；项目frontend `.env.example` 已提供localhost3000 issuer。任务改为修正这套正常本机配置，使邮箱表单与OAuth授权均走本机Admin，同时三端保持同一issuer、JWKS和resource合同。只复用已存在配置键，不按部署名称分支、不改浏览器表单action做测试旁路、不替换服务/用户/数据库，不放宽issuer/PKCE校验、不撤销历史身份或改资源/订阅。前述重定向短正文仅为建议、未实施，本轮不据猜测修改该代码。完成配置回读后再走真实可见登录和图片矩阵，必要正常重载由主执行者负责。

**修订计划**：独立评审实际配置差异；Admin issuer设为本机既有origin，Dream前后端authority/issuer同步同值，保留原internal transport、resource、secret、client/callback、scope、数据与运行路径。备份只放0600本机文件。确认Admin dev env重载和后端明确进程采用，不停止PG/NATAPP，不更改edge路由。实际表单action及OAuth redirect都应本机，登录后的issuer校验仍严格。

公开链路诊断为历史失败：第一POST创建了正常identity Session，但edge499，页面520；第二页面522。它们尚未建立Dream BFF会话，也不代表图片链路执行。用户纠正后停止继续沿公开认证链路验收，保留失败和配置差异，不将此前“公开origin不自动等于替代环境”的事实解释为本机应跳公开中心。

### Round26用户进一步澄清：由实际客户端请求地址选择认证跳转

**Expert Prompt Architect — Optimized Prompt（再次调整计划前）**：同一正常Admin/Dream通过NATAPP边缘公开访问。用户明确要求依据实际客户端请求地址判断跳转，禁止以改静态配置解决本机登录。之前同步本机issuer方案及独立评审保留为已放弃建议；尚未修改任何.env或重载后端。任务是在现有请求校验、BFF、Admin认证入口中复用服务配置的地址/客户端边界，按实际请求地址选择本机或公开浏览器跳转；保留稳定issuer/resource/keys/scopes/严格code-state-PKCE验证，不绕过角色/capability，不增加部署环境分支/额外控制通道或任意Host重定向。先核实官方已安装Provider的session、consent、issuer与redirect构造，再写实际最小设计独立评审，实现新验证及真实登录/图片流程。

**修订计划**：并行只读核实BFF实际请求origin解析和官方Provider跳转语义；把本机请求与现有内网Admin origin、公开请求与现有公开Admin origin准确绑定，明确来源/允许列表/未知Host拒绝。更新正式设计后独立评审再实施。Luna验证确定性请求地址/issuer合同；主执行者通过正常可见页面验证实际本机登录、不走公开网络，并继续完整图片验收。

### round26 请求地址独立评审修订与实施范围

独立评审实际稿发现两项P2：旧origin校验先接受内网URL，导航可能误判；仅换Admin hostname不能解决Dream callback与host-only事务cookie跨域。正式稿已先修订：导航专用单值forwarded→精确canonical Host/URL检查，不影响原API/CSRF；请求必须匹配已有client/service/callback的origin，未覆盖别名在凭证提交前失败。已登记local/public合同各按实际请求选中心，不扩大客户端目录、不改静态issuer/.env。当前正常local service只覆盖localhost:5173，public完整验收需其已有public service/callback路径；地址导航技术检查不能宣称两种真实登录都完成。Admin仅浏览器交互factory改变baseURL/cookie，token及稳定issuer/audience不变。代码实施所有权由主执行者负责；Luna负责修改后的隔离合同与类型检查。评审原文保留于round26/request-origin-design-review.md。

实施独立评审补出P2：Provider的end-session/confirm也读取Session cookie并构造同中心确认页面；已先补正式稿交互责任，再纳入同一browser端点集合及投影回归。Luna首轮Node合同22pass、Admin32pass；Dream类型检查发现新测试数组推断含undefined，已用显式Record数组修复，保留首轮exit2，不改产品行为。Next HMR保留旧process-shared Admin client实例未包含新增只读transportOrigin时options503，已在原cache有效性检查中按该实际属性重建一次，不重载正常服务。

### round26 正常用户旅程：实际可执行范围与对话表

正常本机邮箱→localhost:3000 consent→原callback已进入指定账户Chat。设置可见Admin目录：所有AI的Responses generation/edit=false；唯一Images候选codex-gpt-image-2 generation/edit/configured=true但entitled/callable=false，radio disabled。不凭模型名勾能力、不改订阅或新建资格。先回读正常目录配置原因，继续不依赖图片调用资格的真实步骤。AI从原gpt-6.1-sol可见选择gpt-5.6-luna，保存反馈及刷新恢复通过；Image仍未选择，不改变AI选择。最终恢复原AI偏好。

| 可见对话 | 预期工具与文件 | 持久化/API/最终页面 | 不变范围 |
|---|---|---|---|
| 讨论image_gen是什么，不生成图片 | 正常文字；不得调用图片 | 同真实Thread保存文字/原调用身份，刷新仍可见 | 无图文件、无图调用、既有实体正文 |
| 请画简洁小猫 | AI缺Responses能力，明确反馈及设置恢复 | 原工具拒绝事实保留，图片请求0 | 不自动换Image/模型 |
| 明确请使用image_gen画小猫 | Image未选择且无资格，明确反馈 | 原失败消息保留，Images执行0 | 不重复内置、不自动选择 |
| 添加→绘制圆与三角→发送询问图形 | 当前图片素材视觉理解，非生成 | 原附件/真实消息/历史，原素材保留 | 不触发图片生成或编辑 |
| 可见停止进行中回复→另发简短请求 | 原取消与下一轮正常文字 | 取消/后续消息保留、重开核对 | 不改SSE/Runner/恢复语义 |

正文输入均为用户可从页面理解的自然语言，不传内网ID/路径/Hook实现提示。技术故障注入矩阵仍属Luna隔离验证；缺真实模型能力或资格的生成/编辑/结果文件/下载/后续引用不得伪称真实通过。

### round26 发布后进程采用：进一步核实

**Expert Prompt Architect — Optimized Prompt（调整前）**：正常模型目录证实当前公开AI全部未发布Responses图片能力，当前Free版本Images entitlement=0；两条图片执行资格不能虚构。另普通图片实际回复只有“当前无法执行”，历史未出现selector调用。调查现有AdminDataClient：capabilities_snapshot一旦成功加载保持进程快照，request_auth仅首次或失效时刷新；后端35255从04:25启动，早于本轮capability发布，image provider按该snapshot的ready启动。任务是按既有正常服务发布采用方式重新获取已发布合同，不更改缓存/Runner/控制协议，不在主轮直接查PG。仅在真实线程idle且后端没有Agent子进程后，由主执行者正常SIGTERM并从相同backend/.env入口重新启动0.1.11；不操作Admin/PG/NATAPP，随后原Thread重新发送核对selector和失败恢复。

**实施计划**：记录现有正常实体状态及任务scope只读request/receipt；正常优雅停止原明确PID，等8765退出后同入口启动，核对Runtime身份和实际业务消息；三端authority/env不改。若已发布snapshot仍不ready，继续核实公开capabilities而不绕过。无资格生成/编辑仍明确未验收。

### round26 正常Admin生产构建采用：计划更正

**Expert Prompt Architect — Optimized Prompt（调整前）**：先前把Admin视作dev/HMR不准确。实际64178 supervisor argv为`packages/db/src/supervise.ts pnpm start`，64237运行next start；发布前的生产构建没有本轮image-turn操作。公开capabilities已读到精确Schema但operations空，新的源码/data-role逐项合同均available=true。后端重启仍只获得旧Admin API目录，不能据此认为图片语义执行通过。用户已授权Runtime验证后生产发布和受控capability/OAuth发布；当前必要下一步是准备并资格验证当前Admin生产构建，再由既有start:embedded正常采用，不改.env/DB配置/端点/权限/Schema，不构建一套替代Gateway供真实测试。保护源工作区及原构建，完整记录当前source快照与构建字节，资格失败不切换。

**计划**：在具名0700目录复制当前源构建快照、复用原依赖与正常私有env；只构建，不启动候选业务服务或DB。Luna执行全体非integration技术测试及task文件lint，主执行者生产build；独立复审采用计划。通过后核对无活跃Agent和当前PG数据目录身份，使用原supervisor优雅退出（该owner会同时停止自有PG），保存原.next，采用合格构建并启动原start:embedded；同一正常PG数据目录/账户/订阅/日志原封保留，没有migration/startupDDL写Schema。旧应用仅供本轮失败恢复，正常采用后不以旧构建继续验收；后台resume/资源策略代码不修改。公开capabilities出现image-turn三个操作后，后端正常采用同一新快照，再继续原Thread真实流程。

前两轮“重启后仍无selector”的观察保留，调查型readonly receipt首次ORDER BY猜测created_at导致42703、exit2，已按原schema committed_at修正，exit0，不是业务写入失败。正常模型还缺Responses公开能力、Free Images entitlement=0；生产采用不会凭空授予这些事实。

### round26 生产资格完整单测发现与最小修订

**Expert Prompt Architect — Optimized Prompt**：不缩小完整任务；新本轮全体非integration结果为2444pass/37skip/2fail，不能用focused通过替代发布资格。一个失败是Provider新增openaiApi必填字段在现有Anthropic编辑中提交空字符串；另一个是旧schedule读operation测试把“追加时的位置”误当永久全registry尾部，实际prefix没有变化。复用已有omitEmptyOnUpdate元数据，不新增表单框架/域协议；旧合同测试固定原prefix位置，仍验证权限/DTO与生成注册表一致，不能删断言。先评审具体最小修订再实施，重新focused、整套非integration，并因metadata产品源码变化重新快照build。

**修订计划**：Provider openaiApi编辑空值沿已有字段规则省略，已选Responses须原样提交；修正旧schedule两条read断言引用原259/260索引而非当前数组尾部，保留Registry262原prefix。同步两个文件header及folder、设计兼容性说明。发布前门禁仍包括existingPG/HBA/db存在、源码/env/build fingerprint及无在途Gateway请求。此前build exit0，初版hash严格脚本exit2仅Next自动把私有snapshot next-env.d.ts的旧E2E types import改为自身.next/types；normal源未改，已限定记录生成文件差异，没有据此改原文件。

### round26 同一实例 NATAPP：最小完整补充设计待评审

**Expert Prompt Architect — Optimized Prompt**：最新用户要求指同一正常实例的本机与NATAPP公开访问，单canonical BFF并未完成。不能因Host借用另一个service身份或扩张principal/delegation client集合。现有session表能保存同service不同origin，Provider browser client已经支持多redirect。最小安全补充是保留当前confidential service和browser client，只把同一Dream应用已有的精确callback登记为该browser client可用地址；实际请求只在这份已发布目录内选择callback。请求地址决定跳转，不以配置挑中心；server配置继续管理安全地址授权、transport和issuer，不是跳转开关。既有目录受控发布需先独立审查差异，禁止更改secret、scopes、PKCE、后台权限或订阅。

**待评审计划**：Admin原OAuth目录把当前Dream应用已登记callbacks列入现有各Browser client的redirect集合，保留实际client ID；requireDreamService只在既有已登记Dream origin和当前自身browser client实际active/同resource/精确redirect发布均满足时选择origin+callback，保留verified service ID、secret和后台scope，不借用其他service/browser身份。BFF逐请求解析完整单值forwarded或Host/URL，构造同路径exact callback、cookie/AAD/CSRF，先通过原authenticated capabilities确认目录再向用户给form action；用原Origin头让原Admin session入口关联这个地址，不新建控制通道或cap/DTO/schema。options/start/callback/session/logout/API/Apps用同一个boundary和原服务transport；Python principal/delegation/Gateway仍接受原client，代码/权限不改。旧local cookie/handle兼容，cross-origin handle拒绝；未知、未发布、disabled、歧义fail closed。正式稿写下实际业务正常/失败图后独立评审，再实施、测试与受控目录publish，重建一次最终Admin源码产物，之后正常本机采用、同账户可见登录及图片E2E。

同client设计独立评审P2先修稿：标准Origin不包含path，双方只替换各自原callback origin、保留pathname，完整URI必须同时命中既有Dream exact登记和当前自身client实际发布；歧义或不同path在options前拒绝。共享AdminBffClient owner不保存可变Origin，使用不可变逐请求实例且共享原token owner；新增双origin并发合同。现publisher无revision字段，采用版本只引用其真实发布回执/fingerprint。

Admin发布侧P2先修设计：原完整catalog --apply会重写其它客户端字段/资源并删link，不可用于仅callback发布承诺。本轮沿现有catalog新增受控定向browser-redirects CLI模式，同事务row lock后检查非redirect合同、拒绝删除原地址，只更新既有BrowserClient redirectUris/updatedAt并逐行回读其它字段；原完整desired同样用同Dream登记callback集合，防下次收窄。没有新HTTP/control channel/DB能力/secret或后台授权。


### round26 同client源码独立评审修订

**Expert Prompt Architect — Optimized Prompt**：实际源评审补出两个P2：无cookie native Bearer若进入逐地址BFF factory会放宽原origin且没有目录检查；现有Bearer-only BFF不能承接DPoP配置，但published查询/定向计划未读这两项实际字段。先正式稿写明原native canonical、当前cookie优先不降级、原DPoP不支持只读拒绝，再最小修改factory与目录快照，不新增native服务依赖，不写DPoP，不改JWT/Runner。Luna本轮46Node/127Admin auth通过，Admin tsc exit2为两个publisher函数union泛型推断，需修显式同事务分支；不存在lint目标的harness exit2已保留且修正命令exit0。

**修订计划**：修原factory选择及生产factory回归；目录snapshot读DPoP供narrow前置、published exact callback查询拒绝不兼容状态；同事务CLI直接分支避免错误union推断。独立源复审、Lunafresh focused/类型/lint，再全Admin非integration发布资格；由主执行者dryrun/apply精确callback、构建最终源快照并正常采用，继续可见同账户localhost/NATAPP与图片流程。


round26最新发布资格：两个same-client实现复审final均关闭P2且没有新P1/P2。fresh Node 47/47、Admin auth128/128及两端tsc/lint全部exit0；全Admin非integration正在运行。最终r3生产build exit0，1716source manifest bd2ac9c010e5a0b4365dc808e03939e63e9c00bec9877b3eca59dd7323b82de8，source正常未变，mirror只Next生成next-env.d.ts变化；buildId Zpc72RHey7bmjBijxxMYt，910产物文件hash 203a32e27e6edf7ed2bbcabf771fd21794a36478351bd751ac0a59e26a926e03。两条callback定向dryrun/apply均exit0 verified=true；实际auth角色ink_auth/正常ink-memory回读，除redirectUris/updatedAt外所有字段hash、resource/link hash均未变，Device/service整行hash未变。

正常采用门禁：PG54329正常持久目录PG_VERSION18/HBA已有/数据库已存在；Gateway角色read-only gate exit0。17条reserved/streaming历史记录latest Oct3，早于当前Next Oct10启动，current-process请求0且active PG查询0，没有正常Next外部Provider socket；不能为发布清这些历史账本。已有真实Thread闲置、后端无Agent孩子。正常服务采用尚待完整测试。

真实浏览器绘制圆与三角后首次screenshot等待fonts/render超时，完整harness错误保留，不判断图片功能失败。恢复只限本轮driver：短暂开启自身Node inspector，停止当前页面资源加载、设置明确默认15s超时，随即关闭inspector，未创建新Chrome或改服务；实际Add to message→Sketch.png上传完成，正常storage图片已在发送框。本轮截图失败不计验收通过。生产采用及新增失败恢复/素材/取消/普通工具所需模型预算由原8增加为最大12；仍显式gpt-5.6-luna、逐轮读真实终态，不调用无限探针。


本轮全Admin test:run完成：326files pass/18skip，2452tests pass/37skip、0failed，exit0，189.25s；原有source-contract类skip未变。r3构建、source/配置before切换复核exit0，原.next保存.next-im-image-round26-previous，正常build采用Zpc72RHey7bmjBijxxMYt。正常Admin新supervisor43335/PG43336/Next43393；同正常PG/HBA/hash/db端口身份一致，三个image-turn操作实际DTO及精确哈希匹配，ready=true、actualbrowser client ink-dream-browser-local、images:create=true。采用不是图片实际输出验收。

一次采用顺序失误：backend SIGTERM初次15秒门禁exit1仍未退出时继续了Admin切换；其原8765→Next59911残留SSE连接使uvicorn等待graceful，后台暂时记录ADMIN_UNAVAILABLE。没有活动Agent/model或当前Gateway请求。随后只优雅停本轮自己启动的正常frontend34968，连接关闭后backend51479正常退出，无SIGKILL/原SSE或取消源码变化；保留该失败，不称首停成功。新正常backend48186/session56631仍相同server.py/.env与Runtime0.1.11；frontend48227/session80754仍相同原dev入口/.env/5173。Admin/session81313从原start:embedded正常拥有PG。正常账户页面恢复200，既有Thread重开保留本轮四条和原两条历史；首次未发送草图因离开页面移除，仅其上传文件保留，后续重新绘制再实际发送。


### round26 正常恢复素材边界：诊断计划

**Expert Prompt Architect — Optimized Prompt**：正常新Gateway第一次发送纯文字失败409 IMAGE_MATERIALS_MISMATCH（没有Provider request/扣费）；真实bind、JSONL marker一致且0素材，旧历史未改。fresh实际published CLI0.1.11→隔离fake Gateway恢复两次完整SDK成功，生产helper检查fixture成功；不能据此前推断normal原因或随意放宽安全parser。原安全error只给通用反馈，需最小非正文诊断。

**计划**：先设计/独立评审原helper仅固定reason+计数日志，无正文/marker/身份/额外控制端点；root实现、Lunafocused/type/lint，全非integration及新的source build后正常采用，公开发送一条取得实际失败分支再修。保留现有业务失败、fixture命令127/CJS1初错与修后exit0，不用technicalsuccess掩盖realfailed。实际地址public打开主Document仍为空body，继续检查真实响应状态与中心入口，不先宣称公网登录已通过。

round26诊断设计独立评审已读取：`image-material-diagnostic-design-review.md`无新增P1/P2。主执行者只在原七处失败出口增加固定枚举及数值计数，保留原409错误；新增回归覆盖日志不包含正文/身份/图片与sink失败仍原错误。源码进入技术验证，尚未正常采用。


### round26 诊断采用与真实重现

**Expert Prompt Architect — Optimized Prompt**：fixed-stage诊断设计/实现独立复审无P1/P2；首focused隐私断言碰撞通用fixture ID“message”，root改独特fixture ID后fresh23/23、tsc/lint/build均0，全Admin2454pass/37skip、326filespass/18skip、0fail。r4旧夹具build不采用；r5 source1716、manifest3f130ff0e5f80f169577fb1031f65717c534a397ef20ae9b516631083addf9fb，buildQMWNPHQdD3VaCQPccRGuJ、910files artifact1fb513935ba82f41a3b3b1f1d6aa4e6ddbc98c88d05d09640c4c6063f226c18c。qualifier初次错误假定normal next-env是.next/dev，实际原文件为其他既有.next-e2e路径，拒绝exit1；原source字节不改，只限定一次Next生成import行到.next/types、其余精确相等后exit0。

**计划**：复核source/.env/正常PG身份/HBA和当前实际active请求为0；只优雅停本轮已识别的原frontend→backend→Admin supervisor，每步实际退出门禁后才继续。不重复此前SSE drain顺序失误。备份当前.next，采用r5，按同一原入口/.env重启正常Admin/PG、backend/frontend。复用同Chrome/同账户/既有Thread，一次纯文字公开发送取得固定stage/count；可能前次失败导致CLI合并user，证据必须标注当前重试而非首失败根因。再按实际branch设计最小修订，评审后实现，不绕过素材或图片资格。

正常/auth/options本机200→localhost:3000，公网200→原公开Admin；同实例静态配置未改。实际公网可见页react-dom脚本HTTP2错误/502，登录表单仍空，为公网页面加载前置失败，已记录normal-public-frontend-precondition.json，不能宣称公网登录通过。


### round26 恢复合并修订计划

**Expert Prompt Architect — Optimized Prompt**：r5诊断正常采用，frontend35335/backend35063/Admin Next35049/PG34986，同源原env/正常库不变，ordereddrain全部true。公开同账户既有Thread重发“只回复OK”实际7:23:37Z；Gateway stage marker-position-and-binding，messages11、arrays11、strings0、marker1/material0/marked1/blocks9/index-1，两次CLI请求诊断均同形。未产生Provider reserve/正常费用，此时仍不能说首失败根因；CLI源码明确合并未完成旧user可解释当前重发。

**计划**：正式稿先写完整唯一current block作为边界、prefix不授权任何素材、保留pair/tail/decoder及所有身份/资格/claim规则，独立评审后root改定位及回归，Luna新actualCLI失败/resume fixture与helper、聚焦/type/lint/fullunit/副本build。正常服务源码采用后真实同账户恢复、文字/普通Tool、上传/草图实际发送与不支持恢复；Positive图像仍按现有资格门禁，不能改Free订阅/模型真实能力或称通过。当前恢复尚未修复，不删历史。

恢复定位源码已按评审稿实施并独立复审无P1/P2。raw隔离r3观察current marker在message2/block4、块内字符offset0，确实出现完整块位移；Luna初述offset0不能理解为block0，root已读原始safe receipt纠正。r3helper读取时current源码已是新定位，不当旧helper对照；其fixture turnkey非hex、canonical非numeric，后续只修fixture并由真实DTO.parse验证、同wire对照r5旧helper与current，不复制parser；r3保留为技术协议观察，不替正常首失败根因或完整model验收。


### round26 最终恢复源码采用与真实矩阵计划

**Expert Prompt Architect — Optimized Prompt**：r6已独立实现复审无P1/P2，当前定位只取唯一完整current textblock及之后strict pairs，不授权恢复prefix。fresh4files31tests/tsc/lint/fullAdmin2456pass/37skip326filespass18skip均0，r6build p6VExBST7NFDcAnsStT5k、1718source manifest d52c0e7cd045a513095b683d72837d4da4994832dc6fbd6998c0525d51106d4d、910artifacts hash7c08d8bdccfa43cd4c5f89602d0c34cd1a7a8436bf8857c393e3612eeeeefaaa，正常原env不改、只副本next-env生成一行。r5正常重发失败4次CLI HTTP retry均dispatch前，正常readback只4个旧Provider requests与2bind，没有新增费用。readback误用Node导致JSONimport缺type exit1是harness，改tsx真实入口exit0，只读无写。

**计划**：重复同已审的source/env/PG/HBA/idle gate与有序graceful正常采用。复用Chrome/同账户/既有Thread，普通文字恢复→普通图片不支持反馈→显式image_gen未选模型反馈→重绘草图/添加（无模型）/实际发送视觉理解→讨论工具名称加原普通Tool→停止与明确重试、重开及历史。真实模型验收预算由最大12增加为明确最大18个实际Provider requests（非产品限制），原因是首次Gateway发布及两次素材失败未成功验收，selector/工具回合另计真实模型请求；固定gpt-5.6-luna、逐轮终态读back，不无限probe。Positive native/Images生成编辑仍缺已发布可调用模型/该账户entitlement，不能改资格或借其他旧账户结果，记录具体未覆盖。独立Luna再跑最后可见12/后端192/协议对照与文档验证；最终恢复原AI选择gpt-6.1-sol、Image仍原None，保留正常本轮业务记录。


### round26 草图驱动恢复计划

**Expert Prompt Architect — Optimized Prompt**：当前正常r6真实文字及普通图片、明确image_gen恢复反馈已观察。重绘草图时已存在的可见Chrome驱动在鼠标操作处停滞，未出现协议失败或新增模型调用；不得把harness停滞当产品缺陷或重启用户服务。

**计划**：只检查本轮已识别Node driver37283及其自有Chrome，通过临时inspector读取当前页面/驱动状态并解除页面加载等待；明确超时且关闭inspector，不新下载/启动检查Chrome、不注入业务结果、账户或网络mock。若不能恢复则记录具体前置失败；继续其它可执行正常流程与文档，不掩盖失败。

驱动恢复实际失败：stdin发送过长后发生终端行缓冲丢失，尚未进入草图操作；临时inspector打开原Add/Draw时先遇到canvas选择器歧义（生产页面另有react-grab overlay canvas），改为精确Sketch canvas定位。随后root关闭inspector误用动态import，Node返回ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING并退出1，自有Chrome亦退出。这是harness错误；normal services/DB/Thread未改，无新增Provider请求。原驱动未保存未发送草图；保留失败并使用短命令、pipe stdin的新驱动和已安装Chrome，不重复下载或启动资格检查。同账户重新正常登录后继续可执行矩阵。


### round26 最终技术回执（r6当前源码）

主执行者已读取原始command/out/exit，不以子Agent摘要代替：

| 范围 | 本轮命令 | exit / 关键输出 |
|---|---|---|
| Admin当前素材、Read、history、Responses | `pnpm exec vitest run app/lib/gateway/image-turn-materials.test.ts app/lib/gateway/image-read-flow.test.ts app/lib/gateway/image-conversation-adapter.test.ts app/lib/gateway/responses-image-proxy.test.ts` | 0；4文件31项，素材17项 |
| Admin类型及局部lint | `pnpm exec tsc --noEmit --incremental false`；`pnpm exec eslint app/lib/gateway/image-turn-materials.ts app/lib/gateway/image-turn-materials.test.ts` | 各0 |
| Admin完整非integration单测 | `pnpm test:run` | 0；326文件通过18跳过，2456项通过37跳过，0失败，191.52s；跳过项为原source-contract检查等，不把跳过计通过 |
| 当前Admin源码快照构建 | `pnpm build` | 0；只在r6独立副本生成.next，再由主执行者资格及正常采用 |
| Dream图片后端10文件 | `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests/test_admin_gateway_models.py backend/tests/test_gateway_models_router.py backend/tests/test_admin_system_config.py backend/tests/test_system_config_router.py backend/tests/test_image_generation_tool.py backend/tests/test_image_chat_public_journey.py backend/tests/test_admin_gateway_model_selection.py backend/tests/test_claude_agent_gateway_model.py backend/tests/test_claude_agent_context_builder.py backend/tests/test_image_turn_contract.py -q` | 0；192 passed，28.50s |
| Frontend公开目录/错误合同 | `pnpm exec playwright test --config=/tmp/im-image-model-split-20261010/validation-round26/final-image-merged-luna/frontend-contract.config.mjs --reporter=line` | 0；13 passed，718ms |
| 可见安装版Chrome完整隔离图片流程 | `pnpm exec playwright test --config=/tmp/im-image-model-split-20261010/validation-round26/final-image-merged-luna/dream-visible.config.mjs --reporter=line` | 0；4spec12 passed，35.9s，0skip；真实鼠标/设置/发送/查看/下载/重开/失败恢复/窄屏操作，Provider、SDK和存储为明确隔离seams；不是正常账户图片验收 |
| actual published CLI失败后恢复与真实DTO | `PYTHONPATH=backend:. backend/.venv/bin/python /tmp/im-image-model-split-20261010/validation-round26/failure-resume-material-probe-r4/failure-resume-material-probe.py` | 0；同session基线200、旧绑定fixture409、新current空素材200；current marker实际message2/block4、块内offset0 |
| 同wire旧/新生产helper对照 | `pnpm exec tsx /tmp/im-image-model-split-20261010/validation-round26/failure-resume-material-probe-r4/helper-compare.ts` | 0；binding经真实DTO.parse，两版消费相同wire SHA；r5旧helper预期409，当前helper成功且images/normalize均0 |

完整回执：[Admin当前检查目录](/tmp/im-image-model-split-20261010/validation-round26/material-merged-luna)、[Dream最终图片检查目录](/tmp/im-image-model-split-20261010/validation-round26/final-image-merged-luna)、[actual CLI probe](/tmp/im-image-model-split-20261010/validation-round26/failure-resume-material-probe-r4)。Luna仅拥有确定性/隔离验证与自有进程清理，正常发布、账户、模型调用均由主执行者操作。旧round18/23/先前r3/r5回执作为历史保留，不能代替此表。


### round26 最终评审与取消矩阵修订计划

**Expert Prompt Architect — Optimized Prompt**：最终独立稿复核两组P2为未标历史的缺cap/scope文字与已发布状态冲突，以及Admin旧“无主对话勾选/全走Images”与四能力/两链规则冲突。按实际事实缩明历史、能力和Schema所有权，不改代码。真实计数请求已完成3000输出，但harness按逐行DOM匹配失败（实际段落以空格展示），未发生关闭标签、取消，不能称通过。当前实际Provider总17。

**计划**：先修上述稿并请求独立复核；原17号真实请求保留为文字成功及harness断言失败，不删历史。测试预算限定提升到20个实际Provider请求，仅为重新执行一次真实断线恢复/取消及明确新发送，不无限探针；仍固定gpt-5.6-luna、正常原账户与Thread，按实际Gateway streaming/可见Stop判断，不依赖数字换行。close自有标签→同context重开Thread→可见Stop取消→一次新发送OK，逐项保留真实终态与用量。随后原AI选择恢复、文件hash/目录/业务账本只读核对、最终文档Luna验证及准确交付未完成的正向图片限制。

取消harness第二次未达到目标：18号正常Provider已在07:47:32Z完成“6000会超出单条消息长度”的回复，driver关闭标签时间07:47:41Z，故只验证闲置历史重开，未观察活动取消；可见Stop等待10s失败保留。随后在同20请求预算内把send→close→reopen→Stop连为一个可见操作序列，避免等待只读账本导致错过短回复；不把模型自行拒绝当产品限制或取消成功。
