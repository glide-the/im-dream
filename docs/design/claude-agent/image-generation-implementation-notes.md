<!-- [Input] 现行Chat图片PRD/正式设计；2026-10-07源码调研与两种官方API对比；原实施合同。 -->
<!-- [Output] 图像Tool最小接入、接口/身份/关联/文件/持久化合同及实施验收追踪。 -->
<!-- [Pos] 正式设计配套实施说明；不把技术细节写成产品需求，全部新增图像能力仍为建议、未实现。 -->
<!-- [Sync] 2026-10-09: 从业务正文分离程序规则，保留原技术边界与验收编号，未修改程序或接口。 -->

<!-- [Sync] 2026-10-09: 补充双钻石重做记录及首期接口选择条件，原技术事实与运行路径不变。 -->

# 聊天图片生成与编辑：实施说明

[正式交互设计](image-generation-interaction-design.md)负责用户目的、功能和业务图，[PRD](../../prd/chat/image-generation.md)负责产品范围和页面骨架。本说明只供接入和验证使用，不作为页面文案或新增产品限制。[旧稿原文](image-generation-interaction-design-20261009-history.md)保留全部历史内容与原图；[本轮执行记录](../../exec/image-design-purpose-rewrite-20261009.md)记录重写与验证。

## 1. 证据与选择边界

源码及官方接口事实沿用2026-10-07读取记录，未因本轮改写重新获得当前Codex界面或真实Provider证据。文件、符号、行号和官方资料见[源码研究](image-generation-source-research.md)及[完整时序与API对比](codex-image-generation-call-comparison.md)。

Claude Code恢复源码中的主请求为`anthropic.beta.messages.create`，工具由`toolToAPISchema`转换为Anthropic schema；更换Key不增加Responses工具声明或结果处理。MCP具备通用扩展入口。Image API仍需要图像模型，Responses路径另需要支持图像工具的主模型。当前Codex Tool声明和恢复item不足以确定其私有上游接口。

2026-10-07所读Admin `app/v1`无Images或Responses公开路由，现有`responseTools`只构造function，结果转换只消费message/function_call/reasoning。这些读取日结论不代表所有部署；实施前核对已发布capability。

建议采用服务器绑定的一个内部图像MCP Tool，保留Claude主Agent。Image API和Responses是Provider边界的可选路径，首期实现一种。Admin负责公开图像授权、模型/catalog、完整结果、请求与计费合同；不能在Dream用Proxy主密钥绕过Gateway，不假借现有`messages:create`代表图像授权。

### 首期接口选择条件（建议，未实现）

| 实施条件 | 建议选择与理由 |
|---|---|
| 两种公开能力均满足生成、编辑、授权、计费和质量要求 | 优先Image API。Claude已承担需求理解及工具选择，直接图片请求可省去第二主模型的工具决策；不据此推断费用或质量更优。 |
| 已选且获授权的Provider只公开Responses图像工具 | 在同一内部Tool的Provider边界采用Responses，补齐主模型/工具请求及图片output解析，保留同一用户流程。 |
| 两种路径均未满足所需合同 | 暂不实施生成接入，不用其他凭证或临时运行路径绕过。 |

此表整理[完整对比稿§17](codex-image-generation-call-comparison.md)的条件性建议，不表示已选Provider、实际能力已通过验收，或Codex当前采用任一路径。首期只实现一种，不建立自动路由、双接口fallback或上游会话映射表。选择以实际已发布合同及后续完整验收为准。

## 2. 现有模块与最小补充

| 边界 | 现有模块/公开入口 | 建议补充，未实现 |
|---|---|---|
| 发起、确认、停止与恢复 | `claude_agent.py` 的`POST /api/claude-agent`、`POST /api/claude-agent/tool-confirm`、Thread `stop/messages/status/stream`；`ChatView` / `hydrateClaudeThreadSession` | 不新增公开Chat入口或图像任务状态机。 |
| 上下文与Tool注册 | `ClaudeAgentService.assemble_context`、`AgentRunOptions`、Runner internal MCP composition | 专用服务器图像配置与`image`保留名；命名建议`image.generate` / `mcp__image__generate`，未发布。 |
| 权限 | `_pre_tool_use_hook`、`_can_use_tool`、`ToolConfirmationDock` | 复用原判断与回执，不自动加入低敏allow；批准前、拒绝或授权等待中停止都不请求Provider。 |
| 执行 | 原MCP executor | 建议`ImageGenerationProvider`职责：调用所选已授权路径，解析最终图片。可直接放入现有Tool适配模块，不要求独立服务或通用框架。 |
| 结果 | Runner `_normalize_tool_result_output`、真实`toolCallId`、Service既有Tool事件 | 小型JSON text描述；必要动作名称、状态映射。仅实际存在final缺图时实施本轮引用补齐，不另造通用补齐框架。 |
| 文件和展示 | 当前Thread files；`ChatMarkdown`、`WorkspaceImage`、原content/download | 只补安全的新图片发布；复用现有读取、查看、缩放、下载。 |
| 保存 | `AdminAgentTurnPersistence`、原normal/partial parts保存与history hydration | 保存规范图片引用；不新增图像表或改原turn生命周期。 |

服务器绑定配置不从外部`opts.claude_mcp_servers`注入。建议把`image`加入`_INTERNAL_MCP_SERVER_NAMES`并复用冲突拒绝；用户、Deck、Plugin、外部MCP不得替换同名内部服务。Provider host、模型、参数能力和容量来自服务器配置/授权catalog，不使用用户env或模型自选身份。文件或图像能力不具备时不注册/执行此方案，沿用原能力反馈，不自动启用Workspace。

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

Agent final优先输出图片Markdown。存在Tool成功但final漏图的实际缺口时，Service仅对本轮已登记内部图像Tool成功结果补齐规范图片引用。建议职责名`ImageResultReferences`不要求新增组件层级。其他Tool同kind输出、未登记调用、历史消息或外部同名Tool均不得触发补齐。已有同一URI图片不重复；普通链接、代码示例和bare URI不算已展示图片。alt转义方括号、反斜杠和换行，文件名服务器生成，不能拼接Provider地址或revised prompt形成路径/Markdown。

## 4. 调用关联、身份与权限

Runner回调的真实`toolCallId`、本轮pending登记、内部服务绑定和当前assistant/Thread关联决定结果归属；结果体自报ID或kind不能授予权限。通用Service auto-register fallback不用于登记新图像结果。保留原Runner的ID匹配和turn语义，不新增控制通道。

Provider请求只消费自身HTTP响应。Responses流第一次有效response ID固定到请求上下文；事件按所属response、item与output index关联，重复事件不得重复发布文件。上游response/item ID与Runtime toolCallId不同，不要求相等，不接受跨请求结果。

浏览器继续同源Cookie/内存CSRF，经`proxyApiRequest`取得服务器OAuth后请求workspace内容；浏览器不接收OAuth或图像Key。后端每次读取重新认证、校验Thread所有权、Workspace Mode及公开路径，拒绝符号链接。Admin独立完成图像授权与计费，不新增一套Dream身份体系。

## 5. 两种上游实际接口

以下是2026-10-07核查的上游合同，非已发布IM接口；请求样例、官方引用与两种时序见[对比稿§15–17](codex-image-generation-call-comparison.md)。Admin路径/scope/DTO仍待发布。

| 内容 | Image API | Responses API |
|---|---|---|
| 生成 | `POST /v1/images/generations`，SDK `images.generate`；JSON图像`model/prompt` | `POST /v1/responses`，SDK `responses.create`；主`model/input`与`tools:[{type:"image_generation",...}]` |
| 编辑 | `POST /v1/images/edits`，SDK `images.edit`；JSON `images`引用，或multipart `image[]`文件 | 同responses入口，`input_image`参考图、按能力指定图像工具`action`；必要时`tool_choice`确保调用 |
| 完整结果 | GPT Image `data[].b64_json`；Image API完成流事件的`b64_json` | 图片output item的`image_generation_call.result`；完成标记本身没有最终字节 |
| 流 | `image_generation`或`image_edit` partial/completed | response图像call状态/partial；继续读`output_item.done`或完整response output |
| 后续编辑 | 再提供已授权参考图片 | 首期也重新提供图片，不依赖上游continuation，不新增会话映射表 |
| 取消 | 中止自有HTTP，未确认独立cancel job路由 | 官方cancel仅用于background响应；首期不引入background |

两种接口都支持流式图片，edit也接受File ID，不能当成Responses独占优势。读取部分图不增加前端实时预览；只发布完整结果。当前Service忽略`tool_progress`，沿用原调用/授权状态，不将上游事件写入Claude流或新增SSE。两种适配只改变Provider输入输出；不替换Claude主模型请求协议。

## 6. 文件生成与会话持久化

服务器使用本次执行绑定的规范化Thread root，检查root、`files/`和目标父目录不经符号链接。采用目录描述符或等价原子方案创建自有临时文件，检查解码结果、MIME与图片签名，发布不覆盖已有文件的新图片，清理自有临时文件。现有普通文件写入不能作为上述保护已实现的证据。图片不写`.claude-tmp`，不改变临时目录或sandbox合同。

文件字节保存到Thread files，规范URI与图片说明进入原消息parts，由Admin保存；历史通过`hydrateClaudeThreadSession`和原文件读取恢复。文件与消息不构成跨存储原子事务。文件已发布但消息保存失败时保留文件和原错误，不自动再生成、不宣称保存成功。正常或停止后的partial保存继续使用原路径；停止不删除已经完成的图片。

该方案需要持久`local_persistent`或等价明确文件拓扑，多副本应能读取同一Thread文件；不能用环境名称或临时图床降级。未发现新表需求。任何实际Schema需求仍由Admin Drizzle前向migration/capability发布，Dream不得建表、增加SQLite或运行时降级。

## 7. 失败、取消与兼容性

Provider/无图/无效base64或MIME/文件发布错误走原Tool错误。图片访问错误走WorkspaceImage原反馈；可重试读取只请求原文件。停止结束自有请求/等待，不让迟到结果重新启动已停止turn；已发布且已登记结果进入原partial保存，迟到边界按V7验证。断线先恢复原运行状态与历史，不自动重发未知结果请求。上游取消、费用撤销和幂等保证必须由实际Provider验收，不能从abort推断。

已有文本、Tool、Markdown、附件、图片URI和历史不扫描重写；不新增Runner、ThreadFactory、EventBus、SSE种类、队列、restart/kill控制、Apps画布或运行环境分支。Service引用衔接不改变原normal/partial保存顺序。

## 8. 需求到实施与验证追踪

全部新功能未实现；本轮只做设计评审及文档检查。编号承接旧稿，便于比对历史回执；旧结果不作为新图像功能验收。

| 需求/编号 | 设计与实施边界 | 实施后的验证 |
|---|---|---|
| 设计完整 V1 | PRD骨架、正式稿正常/异常/状态图、来源与建议标记 | 清单、引用、图示渲染、实际稿评审。 |
| 生成 V2 | 原公开发起、内部Tool、Provider、最终结果 | 受控Provider走公开生产入口和原DTO/SSE。 |
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
| Image API V11 | 所选路径请求编码/完整输出 | 生成与编辑、JSON/文件、data/流结果，连到V2–V9。 |
| Responses V12 | 所选路径tools/input_image/output | response/item关联、完成标记后缺图/有图，连到V2–V9。 |

实施先确认Admin公开能力、参考图映射、持久文件拓扑与当前Codex界面；只实现所选V11或V12路径，再执行V2–V9完整技术链。指定正常真实账户、模型和实体后才做V10，保留正常业务记录。Provider-free验证交Luna，真实模型和生产写入由主执行者按仓库协议处理。

本轮双钻石重做的业务取舍、现行稿评审及文档回执见[2026-10-09重做记录](../../exec/image-design-double-diamond-20261009.md)；本文源码/API事实仍为原读取日证据。
