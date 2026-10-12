<!-- [Sync] 2026-10-11: round29 两条正常本机图片链路、展示稳定及历史恢复实际通过；unknown usage、原路由与技术故障验证边界单列。 -->
<!-- [Sync] 2026-10-10: 同步独立Image选择和明确调用分工；原稿逐字保留，两条源码路径接通，真实验收尚未完成。 -->
<!-- [Input] 已评审图片设计、当前Admin Images/目录/授权合同与IM源码。 -->
<!-- [Output] 可复核的执行接口、认证、消息关联、文件与历史保存规则。 -->
<!-- [Pos] 工程接入合同，业务目的和页面由现行PRD/正式设计所有。 -->
<!-- [Sync] 2026-10-10: 更新为实际接入源码，未声明上线或真实模型验收。 -->
# 聊天图片工具实施说明

当前计量修订以[模型分工专项设计](image-model-call-division.md)的round30为准：Gateway严格读取本次Responses顶层报告Token，沿平台模型价格与原账本结算；完整上游图片费用另记未知。历史round29固定Unknown是实现缺口，不证明Provider未返回usage，旧三条未保留原计数，不能推算或用新调用补账。独立Images分项合同保持。新版本已在正常本机采用，用户取消后的真实重验进行中。

当前状态（2026-10-11 round29）：2026-10-11 round29：两条图片链路已在指定现有账户、本机正常 Dream/Admin/Gateway/PostgreSQL 上完成实际生成、编辑、查看、下载、后续引用及历史重开；草图实际绘制并完成理解和内置编辑，显式 image_gen 在支持内置图片的 AI 下仍仅执行所选 Image 模型。闪烁修复后同图持续39秒稳定，后续真实SSE更新保持原Blob。最终AI恢复 gpt-6.1-sol，Image保留 codex-gpt-image-2；原多来源路由保持不可调用，用户自行选择已核实的非路由AI后才能执行内置图片。内置交付成功，但完整图片用量未报告，保留 RESPONSES_IMAGE_USAGE_UNKNOWN，不能称实际费用已知。故障注入与37项既有跳过的边界见执行记录；独立复核与文档、图示检查已通过；真实故障、跳过和未知用量的边界保持单列。 初次实施和恢复时的未验收文字属于历史阶段，完整原文与索引保留，最新证据见专项执行记录。

目的与边界见[PRD](../../prd/chat/image-generation.md)及[正式设计](image-generation-interaction-design.md)。本稿只说明实际程序行为。[改写前全文](image-generation-implementation-notes-20261010-implementation-history.md)保留；[独立设计评审](../../exec/image-tool-design-review-20261010.md)、[本轮验证](../../exec/image-tool-validation-20261010.md)与[执行记录](../../exec/image-tool-implementation-20261010.md)分别说明实施门禁和验收范围。

本稿的模型用途与调用入口以[专项模型分工设计](image-model-call-division.md)为准；[此次分工修订前原文](image-generation-implementation-notes-20261010-model-division-history.md)完整保留。普通图片需求不再默认交给独立工具；主对话内置能力不支持或当前不可调用时明确反馈，不能切换到Images。只有明确要求使用image_gen执行操作时，才使用用户保存的Image模型。上传与草图本身不发起操作。

## 选定链路

主对话保留 `ChatPanel → POST /api/claude-agent → ClaudeAgentService → ClaudeAgentRunner → Claude Code → Admin /v1/messages → 实际Provider`。Codex/xAI Provider走既有Responses适配；其他Provider不强制切换。Gateway保留用户图片和Read图片Tool结果，保持原call_id与function工具声明。普通图片需求在专项分支增加内置`image_generation`（generic强制所选操作，Codex使用已实测auto形状），显式工具请求保持独立Images。

图片调用为 `mcp__image_gen__imagegen → image_gen_stdio → SessionProjectionBroker → ImageGenerationProvider → Admin /v1/images/generations 或 /edits → 实际图片Provider`。stdio消费五项原broker环境；Admin service key、当前grant、Provider凭证与工作区根都留在Host。Runtime工具与HTTP层不默认重试图片请求。

## 实际接口

| 入口 | 输入 | 输出与处理 |
|---|---|---|
| MCP `imagegen` / CLI `mcp__image_gen__imagegen` | 非空`prompt`，可选`reference_images`当前Thread workspace URI数组；禁止额外字段 | 成功为JSON text，失败为MCP `isError`及安全说明。 |
| 原broker `image.generate` | 严格工具输入，加broker capability与request_id | DTO验证、capability恒定时间匹配、使用本轮绑定Host执行器；不新建HTTP服务。 |
| Admin `GET /v1/models` | 当前gateway-cli bearer与server service key | 完整旧catalog或完整新catalog；残缺、未知字段、无效endpoint拒绝。 |
| Admin `POST /v1/images/generations` | JSON `model,prompt`，无参考图 | 单次请求，流式读取完整HTTP正文以控制容量；这不是图片预览流。 |
| Admin `POST /v1/images/edits` | multipart `model,prompt,image[]`，实际参考图片字节 | Admin负责Provider差异；不发送服务器路径、workspace URI或URL代替字节。 |
| 原workspace content/download与messages | 浏览器Cookie经原BFF转OAuth，Thread selector与规范路径 | 每次重新认证、授权当前Thread、Workspace Mode、公开路径；原文件/历史展示。 |

本轮工具没有n、mask、quality、size等新产品配置入口。使用Admin和Provider已有默认参数，不强制设置Codex不接受的output_format。图像生成模型独立于主对话模型，仍由Admin管理提供商、模型与计费。

```json
{"prompt":"把背景改成蓝色","reference_images":["workspace://files/generated/previous.png"]}
```

```json
{"kind":"image-generation-result","version":1,"requestId":"broker-request-id","images":[{"uri":"workspace://files/generated/server-generated-name.png","alt":"Generated image","mediaType":"image/png"}]}
```

结果不包含base64、凭证、服务器路径或Provider原始报文。requestId是broker调用身份，不替代SDK toolCallId。

Host在绑定时记录Thread根目录设备号和inode；参考图严格读取与发布均匹配该目录身份。根目录被替换为其他目录或符号链接后，不读取替换目录的图片，不发起Images请求。参考图读取复用原文件描述符遍历，仅向严格读取传入可选`expected_root_identity`，其他文件调用保持原行为。

## 认证、目录与配置

`AdminRequestAuth.gateway_runtime`只在当前认证actor的scopes包含`images:create`时，把该scope加入原gateway-cli请求。没有图片scope的普通文本turn仍用三项原scope；精确合同就绪且原工作区存在时可注册selector，独立Images执行必须再检查图片scope。Host每次Images请求调用`AdminGatewayRuntime.access_token`读取当前续期grant，并检查`allows("images:create")`。Admin再次校验主体、绑定实体、scope、模型权限与计费条件；不假借messages:create权限。

通用delegation四个hash来自当前Admin `delegationContracts`真实DTO，证据见独立评审回执；Story、scheduled与task-result的冻结合同和自动grant范围不变。旧Admin版本没有新hash时仍按原精确合同门禁拒绝，不能用runtime降级绕过。生产启用必须部署配套合同。

新catalog包含`endpoint_availability`与图片reserve，旧catalog不声明图像能力。目录兼容旧形状及新增`responses_image`；后者单独表达内置生成/编辑、配置和资格，按已发布能力、明确Responses配置、精确capability与实际角色权限开放；缺条件时关闭。文本选择只使用`messages.callable`；纯图片模型不进入原文字模型列表或文字默认。图片选择只使用`images.callable`及对应generation/edit能力。

`ClaudeAgentService`从当前已授权SystemConfig snapshot取得`image_model`并透传至`ImageGenerationProvider.model_alias`。Host只使用这个只读别名；未选择、失效、不支持本次生成/编辑或不可调用时失败并提供设置恢复入口。不读取`INK_IMAGE_MODEL_ALIAS`，不复用文字default，不按唯一候选或目录default选择。新选择只影响后续turn。

服务器默认执行保护由 `INK_IMAGE_TIMEOUT_SECONDS=600`、`INK_IMAGE_MAX_BYTES=33554432`、`INK_IMAGE_MAX_RESPONSE_BYTES=67108864`、`INK_IMAGE_MAX_PIXELS=50000000`提供，可由服务器配置调整。它们限制本次HTTP读取、输入/输出字节和解码工作量，是执行容量，不是用户订阅配额。参考图逐张读取并累计字节，第一次超过本次输入容量即停止，不继续读取后续文件或请求Images。Provider计费、模型规格与权限仍由Admin决定。用户、Deck、Plugin和MCP参数不能改这些配置。

## 当前Thread图片与文件

上传附件先通过原workspace sync校验当前Thread并保存。Router以服务器返回的`workspacePath=files/...`构造`workspace://`加转义路径的引用，`AttachmentPayload.id`携带它；ContextBuilder在视觉图片块旁添加参考URI。之后Agent通过原工具输入传入该URI。历史生成图在原消息中保留同一类引用。工具不能指定另一个Thread或服务器根。

Host只从其构造时绑定的工作区读取参考图，拒绝绝对路径、隐藏组件、路径逃逸和符号链接；使用原严格普通文件读取及新可选字节上限。Pillow实际解码检查PNG/JPEG/WebP，不仅检查扩展名。需要的图片集合全部验证后再发编辑请求。

Host返回图片先检查响应总字节、严格base64和实际格式/像素/解码。发布时核对Thread目录inode，使用`O_NOFOLLOW`目录描述符依次打开`files`与`generated`，发布到`files/generated/`，以`O_EXCL`建立完整临时文件、fsync、link原子发布且不覆盖旧文件，再删除临时文件。集合中任何保存失败只清理本调用新文件，绝不清理用户已有文件。文件名由服务器UUID生成，不拼接prompt或Provider路径。

Workspace Mode关闭不注册此工具，也不因此启用cwd、侧栏或sandbox。原`.claude-tmp`协议不变。工作区文件保留规则和部署的持久存储能力不变，不新增图片表或runtime DDL。

## 调用关联与最终回复

Host把实际成功结果按独立request_id登记，并记录规范化后的原prompt/reference_images。`ClaudeAgentService._make_tool_event_cb`只有在真实toolCallId已登记、工具名为内部保留名、名称不冲突且非isError时，才调用`consume_result`。Host结果及原输入必须逐项匹配登记记录，且只能消费一次。

未知调用仍保留通用Tool fallback，但不能因此登记图片归属；外部同kind结果不触发图片补齐。服务器保留`image_gen`名称，外部同名MCP按原冲突检查拒绝。

Service在原文本结束回调前补齐最终文字遗漏的图片，同一个text part保存。若模型以Tool结束，则在原完成/partial边界产生一个图片文本part。对未结束的partial文本，补齐后结束该原文本块。已展示的相同URI不再追加；普通链接、代码或裸URI不算图片展示。补齐使用固定alt与服务器规范URI，不插入Provider修订prompt。

没有本轮已匹配图片结果时，图片补齐函数直接返回原调用方全文，不改变普通多段文字的`message-final`或parts。对应回归通过生产Service验证原两段回调与最终全文。

正常和部分消息仍用`AdminAgentTurnPersistence.persist_assistant`。不增加SSE类型、图片状态机或数据库字段。最终文本、parts与历史final投影包含相同图片引用；重开时通过原历史与文件公开路径读取，不触发模型或Images请求。

## 失败、停止与运行范围

生成失败、错误结果、解码失败、文件失败和参考图不可用均返回Tool isError，不返回成功URI。HTTP连接异常时反馈请求结果未知；不自动重试、查询虚构任务或承诺费用撤销。用户重新发送是新Tool调用，新Idempotency-Key由服务器turn与broker request_id哈希生成。

`ImageGenerationProvider.close`与发布共享锁，关闭后不再发布新文件，`consume_result`也不接受迟到的Tool完成回执；等待期间的晚回包被丢弃。原Service取消先关闭Host再保存partial，已匹配完成图片保留。发布完成但CLI尚未报告成功的文件仍在工作区，不伪造Tool完成或最终图片。图像请求不改变原disconnect继续执行、ThreadFactory、lease、resume、确认或取消语义。

浏览器图片访问失败沿用原读取/重试反馈；消息保存失败沿用原保存错误。两者都不自动再发Images请求。

## 源码与验证定位

| 能力 | 文件及符号 |
|---|---|
| 输入与JSON结果 | [image_generation_protocol.py](../../../backend/libs/claude_agent_kit/server/image_generation_protocol.py:18)，`ImageToolInput`、`ImageGenerationResult` |
| 工具发现/调用 | [image_gen_stdio.py](../../../backend/libs/claude_agent_kit/server/image_gen_stdio.py:13)，`create_image_gen_server` |
| 注册 | [agent_runner.py](../../../backend/libs/claude_agent_kit/server/agent_runner.py:3809)，internal `image_gen` composition |
| Host执行/保存/关联 | [images.py](../../../backend/services/admin_gateway/images.py:37)，`ImageGenerationProvider`、`generate`、`_publish`、`consume_result` |
| 目录及模型分流 | [models.py](../../../backend/services/admin_gateway/models.py:130)，`_parse_model`、`fetch_catalog` |
| 生命周期和最终消息 | [service.py](../../../backend/claude_agent/service.py:3021)，`_complete_image_results`、原text done与normal/partial保存 |
| 完整技术旅程 | [test_image_generation_tool.py](../../../backend/tests/test_image_generation_tool.py:104)，PNG输入与同文件编辑连接；第133行的生成/保存/重开编辑，真实broker/stdio、Service及错误恢复 |

本轮使用注入Provider与隔离文件进行技术验证；本机Chrome检查原图片查看/下载/重载/响应式。图片相关的真实模型、正常Gateway计费和正常数据库持久化尚未验收，不能由上述结果替代。最终计数、退出码与本轮修订见验证回执。运行时还需Admin注册的OAuth与Gateway服务Key允许图片范围；旧token没有该scope时沿用普通文字功能，重新取得已授权token后才提供图片工具。

## 2026-10-10 正常服务恢复补充

Admin文本目录沿用既有 allowance-only 调用资格，Images仍使用独立图片资格。前端接受订阅included而Messages不可调用的有效目录项，图片专用模型不进入聊天选择；已知HTTP409模型选择失败有明确设置恢复反馈，不自动换模型或重发。

完整公开入口隔离E2E发现并修正了生成文件漏写`files/`及上传附件URI重复`files/`的问题；旧组件旅程未覆盖公开GET，不能证明图片可访问。普通文本已在当前正常登录会话、原模型和正常数据库上回复OK并重开；图片真实生成、编辑与计费仍未验收。新回执及服务恢复过程见[恢复记录](../../exec/image-service-recovery-20261010.md)。

## 本轮内置接入修订

两种模型、真实Provider调用身份、原事务互斥、CLI raw图片结果、历史重开和失败恢复以[专项正式设计](image-model-call-division.md)为准。原下文的Images时序保留为该子流程，不能替代专项完整时序。历史图片通过“添加到当前消息”走原上传路径成为当前素材，添加不发起推理。Host注册条件现为原工作区、Gateway Runtime与精确图片合同就绪；Images实际调用另要求images:create，native使用原messages:create资格。
