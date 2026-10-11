<!-- [Input] 选定Gateway Responses主对话与独立Images执行；Claude/Admin/Codex源码、PRD和正式设计。 -->
<!-- [Output] 图像Tool最小接入、接口/身份/关联/文件/持久化合同及实施验收追踪。 -->
<!-- [Pos] 正式设计配套实施说明；不把技术细节写成产品需求，全部新增图像能力仍为建议、未实现。 -->
<!-- [Sync] 2026-10-09: 从业务正文分离程序规则，保留原技术边界与验收编号，未修改程序或接口。 -->

<!-- [Sync] 2026-10-09: 补充双钻石重做记录及首期接口选择条件，原技术事实与运行路径不变。 -->
<!-- [Sync] 2026-10-09: 选定双链路，补齐Messages/Responses图片兼容缺口、建议工具命名、原接口和必需V12验证；前稿完整保留。 -->

# 聊天图片生成与编辑：实施说明

[正式交互设计](image-generation-interaction-design.md)负责用户目的、功能和业务图，[PRD](../../prd/chat/image-generation.md)负责产品范围和页面骨架。本说明只供接入和验证使用，不作为页面文案或新增产品限制。[旧稿原文](image-generation-interaction-design-20261009-history.md)保留全部历史内容与原图；[此前目的重写](../../exec/image-design-purpose-rewrite-20261009.md)与[本轮执行记录](../../exec/image-gateway-redesign-20261009.md)分别保留各轮评审和验证。

## 1. 选定方案与兼容边界

**可以让Claude Code经Gateway使用Responses；当前图片报文尚未完整兼容。** Claude Code是Agent Runtime，不是主模型名称。CLI继续发送Anthropic Messages，Admin将选定Provider的请求及响应转换为Responses；不要求CLI原生解析Responses。

本次采用两条链路：

- 主对话：`ChatView → ClaudeAgentService → ClaudeAgentRunner → Claude Code CLI → Admin /v1/messages → adaptProviderRequest → Provider Responses`。
- 图片执行：CLI实际调用内部`image_gen.imagegen`（建议、未实现）→ Dream内部MCP执行器 → Admin Images入口（建议、未实现）→ Provider Images → 新图保存与原消息回复。

返回主对话时保留原`tool_use.id/tool_result.tool_use_id`与Responses `function_call.call_id/function_call_output.call_id`关联。普通文本、函数及流转换已有源码；不是本轮真实模型通过证据。图片输入与图像执行需补齐，不用新Runner或第二套SSE主循环。

### 图片兼容缺口

| 层次 | 当前真实行为 | 本方案必要补充，未实现 |
|---|---|---|
| Messages → Chat | `normalBlocks`收集text/image，但`anthropicContentToOpenAI`只保留text；图片会丢失。 | 保留用户image的媒体类型与数据，形成实际图像内容项。不能静默删图后继续推理。 |
| Chat → Responses | `messageText`仅接受text/input_text/output_text；实际收到image_url等内容时抛`UPSTREAM_DIALECT_UNSUPPORTED`。 | 在原转换模块把图片转换为`input_image`，保留文字和图片的顺序；不支持的类型返回安全协议错误。 |
| Tool结果 → 主模型 | 当前Anthropic数组tool_result会JSON.stringify；下层function output也转换为JSON文字。 | 原Read等工具返回图片时，保留与call ID绑定的图片内容，不把base64当普通文字。支持的Responses function_call_output可使用input_text/input_image内容数组。 |
| 自定义工具声明 | CLI工具schema → Chat function → Responses function已存在。 | 注册一个内部image_gen MCP服务及imagegen工具，延续原函数转换。 |
| Responses内置图像 | `responseTools`只构造function；结果及流转换只消费文本、函数、reasoning，没有图片call输出接线。 | 本次不在主请求注入内置image_generation，不需要为它增加结果通道。 |

仅第一层丢图不是第二层主动拒绝的等价说法；完整Messages路径可能先丢掉图片、剩文字仍被处理。两处必须分别修正和验证。普通JSON图片URI作为工具结果可保持文字输出；只有实际图片内容才按多模态字段转换。

内置`/v1/responses + image_generation`不是不可适配。Gateway可以构造该平台工具请求、提取`image_generation_call.result`并接通图片保存和CLI/IM允许的输出。但当前没有完整实现；这比本方案多了平台工具声明、图片事件消费与媒体回传工作。本次只实施独立Images方向，原内置方案留在[对比稿](codex-image-generation-call-comparison.md)及[前稿](image-generation-implementation-notes-20261009-gateway-history.md)，不自动切换。

Responses支持图片输入及平台图像工具；自定义function output也可携带图片内容。[官方图像工具](https://developers.openai.com/api/docs/guides/tools-image-generation)、[官方函数结果](https://developers.openai.com/api/docs/guides/function-calling#formatting-results)。本轮2026-10-09读取官方页面，不把示例模型固化为IM配置。

### 读取证据

| 编号 | 文件、符号、行号 | 结论与范围 |
|---|---|---|
| G1 | [claude.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1822)，`anthropic.beta.messages.create`；[sdk.py](../../../backend/services/admin_gateway/sdk.py:44)，`apply_gateway_sdk_env_to_options` | CLI仍用Messages，Dream绑定Admin base与entity delegation，不靠用户Key或env切换协议。 |
| G2 | [protocol-adapters.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/protocol-adapters.ts:258)，`adaptProviderRequest`；响应296；[stream-adapters.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/stream-adapters.ts:218)，`createProtocolStreamAdapter` | Messages经Chat转换为Responses，返回经Chat转换为Anthropic流；已存在转换入口。 |
| G3 | [protocol-adapters.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/protocol-adapters.ts:39)，`anthropicContentToOpenAI`，`normalBlocks`71，tool_result90 | 用户图片丢失；数组tool_result转换成JSON文字。 |
| G4 | [responses-adapter.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/responses-adapter.ts:40)，`messageText`；`responseInput`60、`responseTools`113 | 非文本图片被拒绝；function output成为JSON文字；只声明function。 |
| G5 | [responses-adapter.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/responses-adapter.ts:193)，`responsesResponseToOpenAIChat`；流255 | 输出/流接线不消费image_generation_call；不能宣称内置图像已兼容。 |
| G6 | [protocol-adapters.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/protocol-adapters.ts:267)，providerAdapterKind分支；[provider-transport.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/provider-transport.ts:128)，`sendProviderRequest` | 当前codex/xai进入Responses，generic OpenAI不等于Responses；managed认证不能伪装为普通Key。 |
| G7 | [agent_runner.py](../../../backend/libs/claude_agent_kit/server/agent_runner.py:3805)，internal MCP composition；保留名402、冲突3856 | 可复用MCP，新增image_gen注册/绑定尚未实现；不能被外部同名覆盖。 |
| G8 | [route.ts](/Users/dmeck/project/ink-admin-memory/app/v1/messages/route.ts:1)；`rg --files app/v1`本次只列models/chat/messages/count_tokens | Admin图像入口、模型授权及计费合同尚待发布；不把设计或本地目录判为已部署服务能力。 |

Codex独立Images执行的K1–K19证据见[完整CLI链路](codex-cli-image-generation-chain.md)。IM原入口、Workspace、持久化与权限的D1–D10见[原研究](image-generation-source-research.md)。源码基线是本机具名验证产物，不含凭证。

选定主模型必须来自已认证catalog中实际可调用、支持目标Responses路线及图片输入的Provider。普通OpenAI Provider如需新增标准Responses能力，由Admin在其配置与适配边界补充；不把adapterKind伪装成codex、不改变其他Provider路线、不使用模型ID猜测协议。图像模型与主对话模型独立由服务器配置/授权选择，可共用Provider，不默认是同一模型。

## 2. 现有模块与最小补充

| 边界 | 现有模块/公开入口 | 建议补充，未实现 |
|---|---|---|
| 发起、确认、停止与恢复 | `claude_agent.py` 的`POST /api/claude-agent`、`POST /api/claude-agent/tool-confirm`、Thread `stop/messages/status/stream`；`ChatView` / `hydrateClaudeThreadSession` | 不新增公开Chat入口或图像任务状态机。 |
| 上下文与Tool注册 | `ClaudeAgentService.assemble_context`、`AgentRunOptions`、Runner internal MCP composition | 专用服务器图像配置与`image_gen`保留名；显示/职责名`image_gen.imagegen`，CLI MCP名建议`mcp__image_gen__imagegen`，未发布。 |
| 权限 | `_pre_tool_use_hook`、`_can_use_tool`、`ToolConfirmationDock` | 复用原判断与回执，不自动加入低敏allow；批准前、拒绝或授权等待中停止都不请求Provider。 |
| 执行 | 原MCP executor | 在原MCP适配处调用Admin独立Images生成/编辑并解析完整结果；不要求新的Provider框架或独立服务。 |
| 结果 | Runner `_normalize_tool_result_output`、真实`toolCallId`、Service既有Tool事件 | 小型JSON text描述；必要动作名称、状态映射。仅实际存在final缺图时实施本轮引用补齐，不另造通用补齐框架。 |
| 文件和展示 | 当前Thread files；`ChatMarkdown`、`WorkspaceImage`、原content/download | 只补安全的新图片发布；复用现有读取、查看、缩放、下载。 |
| 保存 | `AdminAgentTurnPersistence`、原normal/partial parts保存与history hydration | 保存规范图片引用；不新增图像表或改原turn生命周期。 |

服务器绑定配置不从外部`opts.claude_mcp_servers`注入。建议把`image_gen`加入`_INTERNAL_MCP_SERVER_NAMES`并复用冲突拒绝；用户、Deck、Plugin、外部MCP不得替换同名内部服务。Provider host、模型、参数能力和容量来自服务器配置/授权catalog，不使用用户env或模型自选身份。文件或图像能力不具备时不注册/执行此方案，沿用原能力反馈，不自动启用Workspace。

## 3. 建议调用与结果合同（未实现）

```json
{"prompt":"把这张图的背景改成蓝色","reference_images":["workspace://files/scene.png"]}
```

Tool校验非空prompt、同Thread规范参考URI与Provider支持参数。生成无需参考图；编辑读取已存在、获授权且可解码的参考文件。沿用附件上传到Workspace的已有映射；映射未确认前不能把Claude图片块当成Tool文件。模型不得传用户ID、Thread root、绝对路径或Provider凭证。不新增任意数量/尺寸配额。

MCP成功结果采用一个JSON text块，以适配既有text归一化：

```json
{"kind":"image-generation-result","version":1,"images":[{"uri":"workspace://files/generated/result.png","alt":"蓝色背景的场景","mediaType":"image/png"}],"providerRequestId":"provider-response-id"}
```

仅Provider完成、图片解码检查及文件发布成功后返回成功。`images`覆盖实际返回集合；`providerRequestId`可选，仅作诊断，不授予权限或替代参考图。消息不保存凭证、base64、磁盘路径。失败沿用Tool `isError`与安全错误；能力/输入/上游/结果/文件保存分类的具体码由Admin合同确定，不新增SSE error类型。

Agent final优先输出图片Markdown。存在Tool成功但final漏图的实际缺口时，Service仅对本轮已登记内部图像Tool成功结果补齐规范图片引用。引用衔接直接放在原消息完成/部分保存边界，不要求新增组件层级。其他Tool同kind输出、未登记调用、历史消息或外部同名Tool均不得触发补齐。已有同一URI图片不重复；普通链接、代码示例和bare URI不算已展示图片。alt转义方括号、反斜杠和换行，文件名服务器生成，不能拼接Provider地址或revised prompt形成路径/Markdown。

## 4. 调用关联、身份与权限

Runner回调的真实`toolCallId`、本轮pending登记、内部服务绑定和当前assistant/Thread关联决定结果归属；结果体自报ID或kind不能授予权限。通用Service auto-register fallback不用于登记新图像结果。保留原Runner的ID匹配和turn语义，不新增控制通道。

图片执行仅消费自身Images HTTP响应；真实toolCallId、Provider请求诊断ID及文件URI分别保留，不能要求相等或接受跨调用结果。主对话沿用Gateway既有function call与流关联；图片内容转换不改变这些ID。MCP函数声明按CLI全名转换，不照搬Codex的namespace报文格式。

浏览器继续同源Cookie/内存CSRF，经`proxyApiRequest`取得服务器OAuth后请求workspace内容；浏览器不接收OAuth或图像Key。后端每次读取重新认证、校验Thread所有权、Workspace Mode及公开路径，拒绝符号链接。Admin独立完成图像授权与计费，不新增一套Dream身份体系。主对话继续使用原gateway-cli delegation；图片请求使用当前用户/Thread绑定的服务器Admin认证上下文与已发布图像权限合同，凭证不作为MCP参数或进入CLI env。Admin在调用Provider前验证主体、实体绑定、图像scope、模型授权和计费条件；缺合同就拒绝，不假借messages:create或直接使用Provider主密钥。具体scope/DTO由Admin发布。

## 5. 选定链路的实际接口

下表区分当前接口、上游协议及拟议Admin入口。`/v1/images/*`是本方案要求的Admin公开能力，当前尚未实现；Provider真实base和认证来自服务器配置，不能固定为公开OpenAI或Codex后台地址。

| 边界 | 输入与输出 | 实现状态 |
|---|---|---|
| 前端 → Dream | 原`POST /api/claude-agent`，文字/附件、原DTO与SSE | 已有入口；图像结果衔接待补。 |
| CLI → Admin | 原`POST /v1/messages`，Anthropic文字/图片、tool schema、tool_use/tool_result | 原主入口已存在，图片兼容待补。 |
| Admin → 主Provider | 已选Responses路线的`POST {base}/responses`，input_text/input_image、自定义function；返回文本、function_call、流事件 | 文本/函数已有转换；图片块及图片tool output待补。不注入内置image_generation。 |
| CLI → 内部MCP | 建议`mcp__image_gen__imagegen`，prompt/reference_images | 建议，未实现；不是CLI新增原生平台工具。 |
| MCP → Admin生成 | 建议`POST /v1/images/generations`，授权图像model、prompt及支持参数；完整data图片/安全错误 | 建议，未实现。 |
| MCP → Admin编辑 | 建议`POST /v1/images/edits`，授权图像model、prompt、实际参考图片内容/引用 | 建议，未实现。输入JSON images或multipart由已发布合同决定，不发送本机路径。 |
| Admin → 图像Provider | `POST {base}/images/generations`或`/images/edits`；GPT Image完整`data[].b64_json`及实际用量 | 上游协议可用不等于Admin已支持或当前账户已授权。 |
| 文件 → 前端 | 原workspace content/download，规范URI与鉴权图片读取 | 复用；新图发布待补。 |

Images请求不引入第二个Responses决策模型。不从主对话`previous_response_id`或图片数量推断图像调用身份；继续编辑重新提供已授权参考图，历史由IM维护。Tool成功只返回已经保存的JSON文件描述；Agent需要再看图时使用原Read/附件能力及补齐后的主对话多模态转换。

只发布完整图片。当前Service忽略tool_progress，本次不增加百分比、partial预览或新的SSE类型。HTTP重试及费用处理必须按实际Admin/Provider合同验证，不从abort或现有文本计费推断图像幂等和退款。

## 6. 文件生成与会话持久化

服务器使用本次执行绑定的规范化Thread root，检查root、`files/`和目标父目录不经符号链接。采用目录描述符或等价原子方案创建自有临时文件，检查解码结果、MIME与图片签名，发布不覆盖已有文件的新图片，清理自有临时文件。现有普通文件写入不能作为上述保护已实现的证据。图片不写`.claude-tmp`，不改变临时目录或sandbox合同。

文件字节保存到Thread files，规范URI与图片说明进入原消息parts，由Admin保存；历史通过`hydrateClaudeThreadSession`和原文件读取恢复。文件与消息不构成跨存储原子事务。文件已发布但消息保存失败时保留文件和原错误，不自动再生成、不宣称保存成功。正常或停止后的partial保存继续使用原路径；停止不删除已经完成的图片。

该方案需要持久`local_persistent`或等价明确文件拓扑，多副本应能读取同一Thread文件；不能用环境名称或临时图床降级。未发现新表需求。任何实际Schema需求仍由Admin Drizzle前向migration/capability发布，Dream不得建表、增加SQLite或运行时降级。

## 7. 失败、取消与兼容性

Provider/无图/无效base64或MIME/文件发布错误走原Tool错误。图片访问错误走WorkspaceImage原反馈；可重试读取只请求原文件。停止结束自有请求/等待，不让迟到结果重新启动已停止turn；已发布且已登记结果进入原partial保存，迟到边界按V7验证。断线先恢复原运行状态与历史，不自动重发未知结果请求。上游取消、费用撤销和幂等保证必须由实际Provider验收，不能从abort推断。

已有文本、Tool、Markdown、附件、图片URI和历史不扫描重写；不新增Runner、ThreadFactory、EventBus、SSE种类、队列、restart/kill控制、Apps画布或运行环境分支。Service引用衔接不改变原normal/partial保存顺序。

## 8. 需求到实施与验证追踪

全部新功能未实现；本轮做设计评审、文档检查和现有Gateway适配器的确定性核查。编号承接旧稿，便于比对历史回执；旧结果不作为新图像功能验收。

| 需求/编号 | 设计与实施边界 | 实施后的验证 |
|---|---|---|
| 设计完整 V1 | PRD骨架、正式稿正常/异常/状态图、来源与建议标记 | 清单、引用、图示渲染、实际稿评审。 |
| 生成 V2 | 原公开发起、主对话、内部Tool、独立Images、最终结果 | 受控Provider走公开生产入口和原DTO/SSE，覆盖两条链路。 |
| 查看下载 V3 | 新图片→原workspace router/WorkspaceImage | 鉴权读取、图片展示、查看缩放下载。 |
| 历史和编辑 V4 | 原持久化、final缺图衔接、同Thread参考图 | 保存→重开→继续编辑，Tool-only final也能显示。 |
| 错误 V5 | Tool/解析/文件发布 | 生成失败、无图、无效字节/类型、写入失败。 |
| 文件与能力 V6 | 原读取+新安全写入 | 外部Thread、遍历、符号链接、Mode关闭、缺Provider先拒绝。 |
| 授权 V6a | 原Hook和确认Dock | auto/manual/full-access等原策略；批准前、拒绝/停止后Provider调用为零。 |
| 调用身份 V6b | 保留名/真实ID/本请求output关联 | 同名注册、其他Tool同kind、跨调用结果拒绝。 |
| 停止断线 V7 | 原cancel/resume+Provider abort/迟到边界 | 停止、迟到、断线恢复、重试次数与文件回执。 |
| 保存问题 V8 | 原normal/partial/Admin持久化 | 文件已成、消息保存失败，保留原反馈且不再生成。 |
| 兼容 V9 | 原文本/工具/媒体 | 受影响旧合同fresh回归。 |
| 真实业务 V10 | 正常服务/数据库/账户/模型/业务实体 | 本机公开入口真实生成编辑、重开、Admin请求/费用可查。 |
| Images V11 | 选定图片执行链请求编码/完整输出 | 生成与编辑、真实输入格式、完整data结果、图像授权和计费，连到V2–V9。 |
| 主对话Responses V12 | Messages转换、图片输入、tool_use/function_call与流回传 | 文字、用户图片、Read图片结果、函数参数、call ID、tool_result回填与最终回复；丢图和不支持类型独立验证。 |

实施先确认Admin公开能力、主对话Provider路线、参考图映射与持久文件拓扑；V11独立Images与V12主对话兼容都是本方案必需验证，再执行V2–V9完整技术链。指定正常真实账户、模型和实体后才做V10，保留正常业务记录。Provider-free验证交Luna，真实模型和生产写入由主执行者按仓库协议处理。

本轮前稿完整保存在[Gateway重写前实施说明](image-generation-implementation-notes-20261009-gateway-history.md)，本轮评审与验证见[执行记录](../../exec/image-gateway-redesign-20261009.md)。V12改为主对话兼容追踪，不把旧内置图像候选的测试要求当作本方案已实现。
