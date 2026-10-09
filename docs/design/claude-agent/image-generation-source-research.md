<!-- [Input] Notion 图像能力需求；Claude Code restored-src；Codex Round52 交付与后续语义恢复；Dream 当前源码。 -->
<!-- [Output] Tool 图像生成假设的分层结论、架构比较、可复核行号与实施缺口。 -->
<!-- [Pos] 聊天图像生成调研证据；产品规则属于 docs/prd/chat/image-generation.md。 -->
<!-- [Sync] 2026-10-09: 保留2026-10-07源码事实与原评审；技术字段和程序规则现由实施说明维护，正式稿重写为业务描述。 -->

<!-- [Sync] 2026-10-09: 补充双钻石重做记录指引，原技术事实及接口边界不变。 -->

# 通过 Tool 生成图片：源码调研

## 背景与问题

[Notion「近期需求」图像能力支持](https://app.notion.com/p/3d630b7547c380939b7ef1e16a886b6f#3e930b7547c3805b80eddd1eb04ece6c)于本次 2026-10-07 调研读取成功。页面正文包含图像生成、参考图编辑、Admin 代理及 Codex 客户端恢复源码要求，未返回截断标记或未知块提示。正文没有可读取的图像能力讨论批注。本文只提取该章节，不把任务管理、硬件或 ComfyTV 讨论扩展成本需求。fetch 内容中的 as-of 时间不等于本次调用时间，因此不记录未核实的时分。

页面提出通过 Admin 代理 Codex Provider 的 `/v1/responses` 与 `image_generation`。这是一项需求与上游协议描述，不证明本机 Admin 已实现该入口。页面中的套餐、模型、一次图片数量和尺寸等陈述不能直接成为 Dream 产品规则。

## 目标与边界

回答 Tool 发起是否成立、Claude Code 能支持什么、Dream 应复用什么以及最小缺口。仅调研和设计，不修改应用或 Admin，不调用付费模型，不读取账户秘密、不重启服务。

源码读取基线：Dream `develop`，HEAD `fcbbb6e935c2e5bad265da4ebca474dc7b3eccc8`，同时存在其他任务的未提交改动；以下行号是本次工作区读取位置，不宣称对应纯 HEAD。Claude Code 是指定恢复目录；Codex 是指定交付目录，包含原 `src/` 与后续 `work/semantic-recovery-restart/src/`。后续恢复片段注释中的 bundle 偏移只说明恢复来源，未核实它们全部接入了交付应用。

## 概念与证据规则

- **源码已实现**：本次读取到明确的函数或分支；恢复源码只代表所读恢复版本。
- **当前工具声明**：本会话能看到的 `image_gen.imagegen` 输入声明，不等于界面观察或 Dream 能力。
- **当前界面已观察**：本次没有图像交互可归入此类。父会话读取 `com.openai.codex` 被 Computer Use 拒绝；不得绕过。
- **合理推断**：多个边界组合能支持方案，但尚未形成已验证的完整调用链。
- **建议，未实现**：本方案需要增加的行为或接口。

## 明确结论

1. **Tool 发起图像生成是可成立的接入方案，但不能笼统说三套系统已经都这样实现。** 当前会话有 `image_gen.imagegen` 工具声明；外部 Responses 协议定义 `image_generation`。Codex 恢复源码能识别 `imageGeneration` 并处理图片结果，但没有找到与当前工具声明完全对应的执行端实现。Dream 当前没有本方案的图像 Tool。
2. **Claude Code 已有通用 Tool 扩展、调用关联、图片输入和 MCP 图片结果转换；没有找到所读恢复源码中的内置图像生成 Provider。** 搜索范围为 `restored-src/src`，关键词 `imagegen`、`image_generation`、`imageGeneration`；这不是对所有私有或未来版本的断言。
3. 差异涉及**生成执行能力、结果协议与展示**。Claude 的图片内容块主要供模型读取，不自动变成 Dream 可恢复的用户图片。Codex 的 `imageGeneration`、本地文件协议和媒体查看器不能直接照搬到 Web Dream。
4. **最小方向**：Dream 增加服务器绑定的图像 MCP Tool 和 Provider 适配，将成功图片写入当前 Thread 的 `files/`，返回小型 JSON 描述及 `workspace://` 引用；沿用现有 Tool 状态、Markdown、WorkspaceImage、鉴权文件读取与会话持久化。仅当 Agent 未输出规范图片引用时，由 Service 在现有消息完成/部分保存边界补齐引用，具体程序规则现见[实施说明](image-generation-implementation-notes.md)。
5. **当前 Admin 缺少公开 Responses 图像入口，方案尚不可宣称端到端可用。** 必须先由 Admin 提供经授权、计费和结果透传的能力；不允许 Dream 直接使用 Proxy 主密钥绕开 Gateway。

## 源码证据索引

| 编号 | 文件、符号与本次行号 | 已确认行为及边界 |
|---|---|---|
| C1 | [tools.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/tools.ts)，`getAllBaseTools` 193，`getTools` 271 | 内置 Tool 集合与权限过滤；未发现内置 image generation Tool。 |
| C2 | [mcp/client.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/mcp/client.ts)，`fetchToolsForClient` 1743–1755，Tool `call` 1833–1904 | `tools/list` 发现；提取 `toolUseId`，经 `_meta['claudecode/toolUseId']` 关联；传 AbortSignal 与 progress，返回 MCP content/metadata。 |
| C3 | 同 C2，内容转换分支 2482–2555 | MCP `image` 的 base64 经缩放转换为 Claude 图片块；图片 resource blob 有相同转换。不是用户文件发布接口。 |
| C4 | [toolExecution.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/services/tools/toolExecution.ts)，Tool 映射 1292–1295，错误 `tool_use_id` 分支 669–672；[FileReadTool.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/tools/FileReadTool/FileReadTool.ts)，image 输出 schema 249–294 | Tool 结果匹配调用 ID；已有读取图片能力，不是生成图片能力。 |
| C5 | [sessionStorage.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/utils/sessionStorage.ts)，`recordTranscript` 1408–1435，`loadTranscriptFromFile` 2294；[QueryEngine.ts](/Users/dmeck/project/claude-code-sourcemap/restored-src/src/QueryEngine.ts)，`recordTranscript` 调用 451、609 | 消息转录与恢复存在；不证明外部生成文件会自动保存、备份或恢复。 |
| X1 | [remote-conversation-event-reducer.ts](/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery/src/renderer/recovered/agent-04/remote-conversation-event-reducer.ts)，`RemoteImageGenerationItem` 67–70、`parseRemoteConversationItem` 209–210、`mergeStoredAndLiveRemoteEvents` 410–425 | 图片 item 有自己的 ID；解析与远程 live/stored 合并保留未重复的完成图片。不能推断数据库内已经保存全部图片字节。 |
| X2 | [cycle-0113-aggregate-slices.ts](/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery/work/semantic-recovery-restart/src/renderer/recovered/agent-05/cycle-0113-aggregate-slices.ts)，`originalNormalizeImageGenerationItem` 32–39、`originalResolveImageGenerationSource` 20–28 | 优先 `savedPath`，否则使用 `result`；能表达地址或 base64。属于后续语义恢复片段。 |
| X3 | [filesystem-media-src.ts](/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery/src/renderer/recovered/agent-05/filesystem-media-src.ts)，`filesystemMediaSrc` 18；[cycle-0206-renderer-protocols.ts](/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery/work/semantic-recovery-restart/src/renderer/recovered/agent-06/cycle-0206-renderer-protocols.ts)，`isGeneratedImageServiceUrl` 54–55、`generatedImageAltMessage` 65–70 | 本地 `app://fs/@fs` 与 `file-service://`/`sediment://` 识别；图片 final response 的替代文本。不是 Dream 应增加的协议。 |
| X4 | [cycle-0128-image-preview.tsx](/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery/work/semantic-recovery-restart/src/renderer/recovered/agent-05/cycle-0128-image-preview.tsx)，`OriginalImagePreviewDialogProps` 46–69、查看器 202 起、下载 436–441 | 查看、缩放、下载、错误回调、可选前后图片切换。Props 存在不证明生成结果一定启用编辑按钮或画廊。 |
| X5 | [cycle-0146-app-server-dynamic-tools.ts](/Users/dmeck/project/Codex-Original-Functionality-Round52-Delivery/work/semantic-recovery-restart/src/renderer/recovered/agent-04/cycle-0146-app-server-dynamic-tools.ts)，`AppServerDynamicTool` 24、item type 286 | 动态 Tool 与 `imageGeneration` 类型可表达；未据此确认内置图像 Tool 的执行归属。 |
| D1 | [agent_runner.py](../../../backend/libs/claude_agent_kit/server/agent_runner.py)，MCP composition 3805–3863、`_normalize_tool_result_output` 3063–3086、结果处理 4677–4743 | 已有服务器 MCP 注入和 ID 关联；JSON text 能保留为对象。混合 text/image content 经 text 归一化不能保证图片自动透出前端，因此使用小型 JSON 文件引用。 |
| D2 | [service.py](../../../backend/claude_agent/service.py)，`_make_tool_event_cb` 3294 起，结果 SSE 3429–3492，`_sse_events_to_ui_parts` 3740（Tool 分支 3784–3803），`_persist_assistant_turn` 3076、`_persist_partial_assistant` 2989 | Tool input/output 通过 `toolCallId` 关联；输出进入 collected parts，持久化正常/部分消息。通用 fallback auto-register 不是新图像描述的授权检查。 |
| D3 | [claude-agent-transport.ts](../../../frontend/app/_dream/lib/claude-agent-transport.ts)，事件声明 130–160；[ChatMessageList.tsx](../../../frontend/app/_dream/components/chat/ChatMessageList.tsx)，Tool 处理 592–643、通用折叠 765–785、outside MCP Apps 797–841 | 现有 Tool 过程展示；不能说任意 JSON 图片结果已自动显示在 final。图片无需新增 Apps iframe。 |
| D4 | [build_user_message_content.py](../../../backend/libs/claude_agent_kit/messages/build_user_message_content.py)，`AttachmentPayload` 30–40、图片输入 81–98；[context_builder.py](../../../backend/claude_agent/context_builder.py)，图片引用示例 207 | 用户图片附件进入 Claude base64 图片块；已有 `workspace://files/...` 提示词。附件输入不等于图像编辑 Provider 已存在。 |
| D5 | [WorkspaceFileReference.tsx](../../../frontend/app/_dream/components/chat/WorkspaceFileReference.tsx)，`WorkspaceImage` 234、读取/释放 255–280、下载/预览 301–330；[ChatMarkdown.tsx](../../../frontend/app/_dream/components/chat/ChatMarkdown.tsx) | 已有缩略图、鉴权 blob、加载重试、共享全屏查看器、缩放与下载；Thread 改变会清理读取和 blob。 |
| D6 | [workspace.py](../../../backend/routers/workspace.py)，`_require_owned_workspace_thread` 200–220、`read_workspace_file_content_endpoint` 356–402、下载 709–755；[文件核心](../../../backend/libs/claude_agent_kit/server/workspace.py)，读取 1766、无符号链接读取 1817、写入 1974 | 先 OAuth/Thread 所有权，再 Workspace Mode、路径及已存在目录；content 只读普通文件并拒绝符号链接。写入函数本身不提供同等原子发布保证，新 Tool 写入须补齐检查。 |
| D7 | [threadSessionHydration.ts](../../../frontend/app/_dream/components/chat/threadSessionHydration.ts)，`hydrateClaudeThreadSession` 335–355；[assistantTurnHistory.ts](../../../frontend/app/_dream/components/chat/assistantTurnHistory.ts)，`processPart` 22 起 | 历史先读消息再状态；过程可延迟加载。不能只把结果藏在 Tool output 而宣称重开即可看到图片。规范 final Markdown 是最小恢复通路。 |
| D8 | [agent_runner.py](../../../backend/libs/claude_agent_kit/server/agent_runner.py)，`_INTERNAL_MCP_SERVER_NAMES` 402–404、`_pre_tool_use_hook` 3254–3270、权限判断 3390–3418、确认/拒绝 3425–3525、`_can_use_tool` 3553 起、同名冲突拒绝 3856–3863 | 调用先登记，权限可能后确认；新 image 不在现有保留名/auto 低敏集合。建议内部注册并扩充原保留名，不能外部同名注入；授权流程按已有策略，不自动放行。 |
| D9 | [ChatMessageList.tsx](../../../frontend/app/_dream/components/chat/ChatMessageList.tsx) 605、765–785；[toolInputSummary.ts](../../../frontend/app/_dream/components/chat/toolInputSummary.ts)，`resolveToolInputSummary` 40–61；[ToolConfirmationDock.tsx](../../../frontend/app/_dream/components/chat/ToolConfirmationDock.tsx) 50、74、137；[service.py](../../../backend/claude_agent/service.py)，`_make_tool_confirm_cb` 3577–3660 | 默认工具标题来自 toolName，摘要不读取 prompt；原授权 Dock 可批准/拒绝，Service 发原 tool-approval-request。图像友好名称与准确状态映射是必要未实现小改动。 |
| D10 | [workspaceFileAccess.ts](../../../frontend/app/_dream/components/chat/workspaceFileAccess.ts)，`fetchWorkspaceFile` 49–65；[browserSession.ts](../../../frontend/app/_dream/lib/browserSession.ts)，`browserRequestHeaders` 28–34；[api-proxy.ts](../../../frontend/app/api/_auth/api-proxy.ts)，`apiAuthorization` 11–23、`createApiProxy` 32–43 | 浏览器从内存会话取CSRF，同源Cookie请求文件，不用OAuth localStorage/Bearer；Next BFF解析Cookie会话并转发服务器OAuth。Python文件端点再次验证。 |
| A1 | [Admin v1 models 路由](/Users/dmeck/project/ink-admin-memory/app/v1/models/route.ts)、[chat 路由](/Users/dmeck/project/ink-admin-memory/app/v1/chat/completions/route.ts)、[messages 路由](/Users/dmeck/project/ink-admin-memory/app/v1/messages/route.ts)、[count_tokens 路由](/Users/dmeck/project/ink-admin-memory/app/v1/messages/count_tokens/route.ts)；`rg --files app/v1` 本次枚举 | 当前 v1 目录没有 `responses/route.ts`。此结论限源码目录，不把它推断成所有部署/代理都没有 Responses。 |
| A2 | [responses-adapter.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/responses-adapter.ts)，`responsesResponseToOpenAIChat` 193–221、`ResponsesToOpenAIChatStreamState` 298–317 | 当前 Chat 转换提取 text/function_call/reasoning；不能当成公开图片字节透传入口。仅补充只读核查，不修改 Admin。 |

## 架构对比

| 比较项 | Claude Code 恢复源码 | Codex 恢复客户端 / 当前声明 | Ink & Memory 当前源码与建议 |
|---|---|---|---|
| Tool 定义、注册、发现 | 内置 tools + MCP `tools/list`（C1/C2） | 动态 Tool schema（X5）；当前声明另有 `image_gen.imagegen` | 复用 internal MCP composition；新增 image 保留名与内部绑定，不能作为外部 `opts.claude_mcp_servers` 同名项注入（D1/D8）。 |
| 执行归属 | Tool executor → MCP server；没有所读内置图像 Provider（C2/C4） | 客户端承接 imageGeneration；当前图像执行端源码未定位 | 建议 Dream Tool 适配，Admin/Gateway 负责 Provider 授权、路由、计费；能力待提供（A1/A2）。 |
| 生成/编辑输入 | JSON Tool args；文件读取、用户图片块可用 | 当前声明 prompt、路径或最近图片引用、透明背景；恢复客户端不证明相同执行协议 | 建议 prompt + 当前 Thread 内规范参考图 URI；用户附件沿用已有上传/文件流程，不新增“最近 N 张”隐式绑定。 |
| 输出协议 | MCP content / image / resource 转 Claude 块（C3） | imageGeneration `result`、`savedPath`（X1/X2） | 建议 JSON text `{kind, images:[{uri, alt, mediaType}], ...}`，版本与字段见实施说明；图片字节不进入 SSE。 |
| ID 与消息 | `toolUseId` / `tool_use_id`（C2/C4） | item ID、turn/thread 通知（X1） | 已有 `toolCallId` + Thread + assistant message（D2）；上游 response/item ID 仅诊断映射。 |
| 进度/完成 | AbortSignal、MCP progress（C2） | started/completed item；合并 live/stored（X1） | Tool input仅证明登记；原授权区可能等待/拒绝；需要友好动作与“图片调用处理中”映射，不证明Provider已开始（D8/D9）。 |
| 展示与访问 | 模型图片块不等于 Web 展示（C3） | 多种 src 与查看器（X2–X4）；当前界面未观察 | Markdown→WorkspaceImage→Cookie/内存CSRF→Next BFF→服务器OAuth content；浏览器不存OAuth（D5/D6/D10）。 |
| 历史 | 转录与恢复（C5），文件仍需外部保存 | 合并事件不证明重启恢复字节（X1） | canonical URI 存现有消息 parts，字节留 Thread files；history final Markdown 可读（D7）；依赖同一持久文件拓扑。 |
| 失败/取消/重试 | 标记错误，传 abort；连接层有重试，不能等同生成幂等（C2/C4） | 通用 error/willRetry 和 terminal 状态；图像任务取消能力未确认 | 原权限等待/拒绝/停止；Tool 停止自有请求，不能保证 Provider 取消/退款；未注册能力反馈不伪造Tool失败（D8）。 |
| 后续引用 | 可 Read 当前文件或提供图片块（C4） | 当前声明支持路径/最近图片；恢复源码未定位完整编辑链 | Agent 引用同 Thread 文件，经 Tool 再校验读取；多图指代不明确时只澄清对象。 |

## 上游协议查证与限制

本次读取 [OpenAI 官方图像文档](https://developers.openai.com/api/docs/guides/image-generation)与 [codex-proxy API_CN.md](https://github.com/icebear0828/codex-proxy/blob/dev/API_CN.md)。官方示例支持 Responses `image_generation_call.result` 与参考图 `input_image`；Proxy 文档描述自己的 Responses 转发。这些协议支持适配方向，不证明 Admin 当前部署兼容，不把示例模型或参数数量硬编码为 Dream 配额。未发出真实请求验证本机套餐、实际尺寸、取消或计费。

实施前：Admin 需给出允许图像 Tool 的公开能力、鉴权和计费合同；Dream 需验证发布能力与正常账户路径；当前客户端界面观察仍待补充。Workspace Mode 关闭或文件拓扑不满足时不注册/不执行此文件方案，不自动开启设置或新增另一文件服务。

## 方案关系

现行[聊天图像PRD](../../prd/chat/image-generation.md)定义产品边界和骨架；[正式交互设计](image-generation-interaction-design.md)定义功能、状态和恢复；[实施说明](image-generation-implementation-notes.md)维护程序规则。[原执行记录](../../exec/image-generation-design-20261007.md)保存2026-10-07验证，本轮重写与检查见[2026-10-09记录](../../exec/image-design-purpose-rewrite-20261009.md)。

## 两种API与客户端链路补充（2026-10-07）

[Codex完整时序与Image API/Responses接口对比](codex-image-generation-call-comparison.md)进一步区分交付应用、恢复查看器和当前Tool声明，并列官方HTTP/SDK/流事件及CLI协议源码。Claude Code主链使用Anthropic Messages，不会仅因换Key而声明Responses内置图像Tool；Admin现有Responses adapter只构造function工具并投影text/function_call/reasoning，缺少图像入口与结果能力。两种上游均可置于同一个内部MCP Tool的Provider边界，不直接改变Claude主Runner。

补充核查还确认：交付本地ConversationPage显示message.text，交付远程ConversationItem显示图片JSON details，恢复查看器接线仍未确认；Dream `_make_tool_event_cb`明确忽略tool_progress，不能据此承诺图片实时百分比。Image API也支持流式图片，官方edit reference已支持File ID；Responses完成标记不携带最终base64。这些修订细节与源码/官方引用在补充对比稿逐项列出，不宣称当前Codex实际采用哪种上游。

本轮双钻石重做的业务取舍、现行稿评审及文档回执见[2026-10-09重做记录](../../exec/image-design-double-diamond-20261009.md)；本文源码/API事实仍为原读取日证据。
