<!-- [Sync] 2026-10-09: 原始测试回执仅保留本机；正文保留命令、退出码和结论，不建立指向忽略目录的仓库链接。 -->
<!-- [Input] 用户对上一轮图像 Tool 调研的补充要求、AGENTS.md/Agent.md 与指定三套本地源码。 -->
<!-- [Output] Codex App 图像调用全流程对比文档的优化提示词、执行步骤和本轮文档验证回执。 -->
<!-- [Pos] 上一轮图像调研的补充执行记录；不创建重复执行聊天，不改变应用业务行为。 -->
<!-- [Sync] 2026-10-07: CLI/两种API研究、实际正式稿补充及Luna一致性/14图渲染检查完成；保留原始回执，功能未实现。 -->

# Codex App 图像调用与业务对比补充记录

本记录中的 `frontend/test-results/` 文件是本机验证产物，已由 Git 忽略；命令与结果摘要保留在本文，原始文件不随仓库提交。


## Optimized Prompt

你是一名熟悉桌面客户端、Agent Tool 协议和图像生成的架构研究员。基于上一轮已交付的图像调研和正式设计，整理一份可独立阅读的 Codex App 图像调用时序与业务对比文档，重点对比 Claude Code 与 Ink & Memory。追踪用户发起、Thread/turn 发送、客户端/主进程/app-server 边界、Tool 输入和结果、图片事件关联、渲染与文件访问、会话重开、后续编辑，以及失败、取消、断线与重试。

先读取相关工作合同并保护已有未提交改动。每个已确认边界列出文件、符号与行号；区分交付实现、后续语义恢复片段、当前工具声明、推断和未定位边界。完整覆盖流程不等于完整源码已经找到：找不到的执行核心、文件生成、数据库写入或恢复调用必须直接标出，不编造连接，不把历史恢复源码当成当前界面。沿用上一轮实际界面访问受限的证据，不绕过限制，不为了文档调用收费模型。

在现有 Claude Agent 设计目录新增专门的研究对比文档，包含正常全景、真实客户端事件、查看/下载、历史恢复、异常与取消 Mermaid 时序图、状态图、标识及业务矩阵、Dream 最小复用判断和未验证范围。该文档是来源对比，PRD 和正式设计继续拥有产品规则与拟议实现，不复制新功能合同。同步目录清单及相关文档交叉引用，保留原稿与原有图示。只修改本轮文档和具名验证产物。机械文档与 Mermaid 检查交给 luna_test_runner，等待新回执，修正问题后复验。最终给出可点击文档、覆盖范围与限制，不声称新图像功能实现。

## 执行步骤

1. 补充读取 Codex 恢复客户端的发送、RPC、通知、图片处理及文件边界，核对上一轮对三套系统的结论。
2. 编写独立对比文档与流程图；未知边界明确标注，逐项检查符号、ID、事件和业务语义。
3. 同步清单与交叉引用；委托 Luna 做本轮引用/清单/图示渲染/空白检查；记录回执后交付。

## 影响范围与验证分类

只增加来源分析文档与引用，不改变用户入口、Agent/Tool、消息协议、文件权限、持久化和取消行为。无需新增 PRD 或运行生产入口/真实模型；不得把文档检查称为功能验收。上一轮记录见 [图像生成设计执行记录](image-generation-design-20261007.md)。

## 用户补充与调整后的 Optimized Prompt

在继续完成 Codex App 完整调用与业务对比的基础上，按用户指定的 OpenAI 官方 image-generation 的 Image API 与 Responses API 两种路径，梳理各自实际交互接口。读取指定官方页面及相关 API reference，列出 HTTP method/path、SDK方法、请求编码、生成/编辑输入、结果字段、流式事件、后续引用和取消恢复边界；images-vision 仅解释图片输入，不另当作生成方案。区分官方API、Codex当前Tool和恢复客户端item、Claude MCP、Dream公开接口以及未实现Admin能力。用具体样例与时序说明两种方案如何接在现有Agent Tool之后，不能因Responses有内置Tool而断言当前Codex私有实现必然走它。保留原目标和不实现功能、不生产写入、不绕过权限等边界。将接口对比纳入同一研究交付并重验全部新增图示和引用。

调整步骤：补充官方API核查 → 新增两种实际接口矩阵/示例/时序及本地路由映射 → 同步文档链接 → Luna执行最终范围检查。本轮使用 OpenAI Docs 官方资料工作流；机械验证按 luna-test-stage 委托执行。

## 当前状态

源码补充、API比较与实际文稿修订已完成；Luna独立一致性评审未发现具体矛盾，文档及14图渲染均取得本轮exit 0回执。下面完整记录实际覆盖和实施限制。收口记录写入后仅重验引用/空白，不因未变图示重复启动浏览器。

## Claude CLI 与两种接入方案：本轮 Optimized Prompt

你是一名 Agent 协议与产品交互架构研究员。在 Ink & Memory 已有图像调研、PRD 和正式设计基础上，调查两种 OpenAI 图像接口及 Claude Code CLI 的实际接入条件。将“Claude Code 只需传入 Key 就能调用 Responses 平台内置图像工具”“Image API 与模型无关”“Codex App 使用其中某一路径”全部作为待验证假设，而非前提。基于指定 Claude restored-src、Codex 恢复代码、Dream 和 Admin 当前源码及官方 API 文档回答：CLI 实际发送何种协议，能否声明 Responses 内置 image_generation，是否能消费对应图片结果；Key 的身份认证作用与协议/工具能力区别；Image API 如何由通用 MCP Tool 调用，以及对话模型选择与图像模型选择的区别；Codex 工具声明、会话 item 与上游接口间是否有已定位的调用证据。

分别列出 Image API 与 Responses API 的 HTTP/SDK 接口、生成和编辑输入、最终与流式输出、标识关联、多轮引用及取消恢复边界。明确 IM 集成每种方案的最小改动：现有 Claude Agent MCP composition、权限 Hook、Provider 适配、Admin/Gateway 公开授权和计费入口、结果转换、Thread 文件、现有 SSE/图片组件、消息保存及重开。复用同一外层生产链路，选择一个已获授权且可用的 Provider 路径，不默认同时实现两套适配，不替换 Claude Runner 或增加第二对话状态机、控制通道和数据库表。

任务一：先调查源码和官方接口，输出可证实的判断及未知边界。任务二：更新现行正式交互设计，补齐两种方案的接口映射、流程、异常、状态、兼容性、验收和实施前置条件，保持 PRD 的业务范围与正文骨架一致。任务三：基于实际文稿独立评审目标覆盖与过度设计；修订问题后委托 luna_test_runner 执行 fresh 文档清单、源码引用与 Mermaid 渲染检查，等待命令/退出码/产物回执。尚未实现的方案只通过设计与文档检查；不得报告功能、当前 Codex UI 或真实账户/模型验收通过。

计划：核对 CLI 请求协议与 Gateway 结果投影 → 整理两种上游接口并更新对比文档和正式稿 → 评审实际文稿、修正 → Luna 文档/图示检查并记录本次回执。可选增强项：实施时另补已指定真实账户、实体和模型的业务验收；本轮不调用模型或写生产数据。

## 已完成的源码判断与文稿修订

- Claude `getAnthropicClient` / `anthropic.beta.messages.create` 和 `toolToAPISchema` 证实主链为Messages；Key不代替协议与图像结果处理。
- Admin `adaptProviderRequest`可把普通Anthropic请求转换成Responses，但`responseTools`仅构造function；最终和流转换目前不提供图像Tool合同。`app/v1`只枚举models、chat/completions、messages、count_tokens，没有responses或images公开路由。
- Codex交付页面实际为message.text/图片JSON details；恢复viewer和媒体协议不能当成当前界面或私有上游路径。对相关src搜索未定位Image API/Responses图像HTTP执行；结论保持未知。
- 官方Image API也有流式图像、edit JSON也接受File ID；Responses图片完成标记没有最终字节。已修正文稿的接口比较和流程。
- 新增独立调用对比，覆盖7条Codex分边界时序、2条IM可选适配时序与1张本地状态图；正式稿保留原3图并增加Provider时序、V11/V12选定路径验收。PRD仍使用原业务骨架，只增加方案来源关联。

## 影响评估与验证选择

| 范围 | 本轮实际变更与评审要点 | 验证分类 |
|---|---|---|
| 用户发起 | 只修订文档；仍为原输入、附件、发送/停止，无方案切换或额外确认。 | PRD骨架/流程一致性检查。 |
| Agent/Tool | 提出同一MCP Tool与两种可选Provider；不实施CLI、Runner或权限Hook变更。 | CLI/Gateway源码核查；不能执行新Tool验收。 |
| 消息/事件 | 说明两种上游结果转换；不新增SSE，不承诺Provider百分比或partial UI。 | 文稿/图示/接口字段一致性。 |
| 前端图片 | 区分交付Codex文字投影、恢复viewer与Dream既有组件。 | 来源和设计核查；不重复旧组件功能测试。 |
| 文件/权限 | 拟议写入边界保持Thread所有权、Schema、路径和图片解码；原读取边界复用。 | 检查建议/现状标记，无运行文件写入。 |
| 保存/重开 | 共用现有消息parts与Thread files，不新增上游会话表；文件拓扑仍是实施条件。 | 完整流程及V4/V8覆盖检查，未测试新生成持久化。 |
| 失败/取消/重试 | 结果标记和字节分开；重新加载只读已有图，未知请求不自动重发，stop无远端退款保证。 | 现行异常/状态图与两种API补充一致性。 |
| 兼容性/Schema | 文档加法修订，不改程序、环境路径或数据库；保留旧图与上一轮回执。 | 文件清单、引用/行号、JSON、14块Mermaid实际渲染与空白检查。 |

验证实现为本轮具名 `frontend/test-results/codex-image-call-comparison-20261007/` 脚本，禁止模型、业务HTTP、数据库、安装或旧服务变更。Luna仅运行文档检查与文稿一致性评审；完整功能链和真实业务验收均因未实现而不执行。

## 本轮独立评审与新验证回执

执行者为 `luna_test_runner`，任务 `/root/image_comparison_validation`。评审基于已经保存的实际对比稿和正式稿，不评审派发计划。其独立一致性回执（本机文件 `frontend/test-results/codex-image-call-comparison-20261007/consistency-review.md`）未发现新矛盾；主执行者接受其有界文稿结论，保留当前UI/私有生成执行/真实模型的未知边界。此前主执行者已经纠正路径归属、几个恢复源码函数行号以及两种上游的stream完成结果差异。

| 命令（cwd） | 退出码 | 关键输出与实际范围 |
|---|---|---|
| `python3 frontend/test-results/codex-image-call-comparison-20261007/check-docs.py`（仓库根） | 0 | 8/8文件头、5条清单、104本地引用、37行号范围、6个JSON示例；errors=[]；覆盖原PRD/研究/正式稿、新对比/exec及三个.folder。外链22条不由该脚本联网检查。 |
| `node test-results/codex-image-call-comparison-20261007/render-mermaid.mjs`（frontend） | 0 | Chrome一次轻量启动通过；comparison10/10、formal4/4；14个图全部parse与SVG render成功。不是业务页面E2E。 |
| `git diff --check -- docs/design/claude-agent/codex-image-generation-call-comparison.md docs/design/claude-agent/image-generation-interaction-design.md docs/design/claude-agent/image-generation-source-research.md docs/design/claude-agent/.folder.md docs/prd/chat/image-generation.md docs/prd/chat/.folder.md docs/exec/codex-image-call-comparison-20261007.md docs/exec/.folder.md`（仓库根） | 0 | 无输出；未跟踪文件的行尾空白和换行由上面的Python检查覆盖。 |

原始产物：文档stdout（本机文件 `frontend/test-results/codex-image-call-comparison-20261007/check-docs.out`）、图示stdout（本机文件 `frontend/test-results/codex-image-call-comparison-20261007/render-mermaid.out`）、Mermaid逐图JSON（本机文件 `frontend/test-results/codex-image-call-comparison-20261007/mermaid-receipt.json`）、空白stdout（本机文件 `frontend/test-results/codex-image-call-comparison-20261007/git-diff-check.out`）、定向源码核对（本机文件 `frontend/test-results/codex-image-call-comparison-20261007/review-symbols.out`）。14个SVG保留在该目录的`svg/`，只关闭本轮自有Chrome和临时Vite；回执含`owned_browser_and_harness_server=closed`，未停止用户服务、未创建数据库或业务记录。

官方联网核查由主执行者通过OpenAI Docs流程完成，包含用户指定vision/两种generation guide及对应generate/edit、SDK、流事件和background reference。各个网页依据就近写在对比稿。单独cancel reference因抓取体积限制未取得内容，限制由已取得的官方Background guide及Responses SDK方法页交叉核查；没有据此调用上游接口。

## 结论、实施条件与任务状态

结论是同一Claude MCP外层与一种已授权Provider适配：Image API可减少第二主模型的工具决策；所需Provider仅支持Responses时采用Responses。两者都仍需Admin发布图像权限/模型/catalog、完整结果和计费合同；现有普通Messages授权/文字转换不够。必须确认上传文件映射、Thread持久文件拓扑和安全发布，并完成V2–V9及所选V11或V12技术链，再以指定真实账户/实体/模型执行V10。

未验证：当前Codex真实图片界面、其私有执行端使用哪个上游、实际模型质量/参数/取消/计费、两种新Tool调用、文件发布、会话写库和重新编辑的功能链。原有测试结果未冒充本次生成验收；本轮没有实现任何新图像功能。文档评审确认没有新增无业务依据的页面、确认、SSE、控制通道、background状态或数据库表；公开接口名、scope和DTO仍由Admin制定。

已登记执行聊天`01a116cf-87fa-7170-bf66-4a195510a6ca`保留，未递归创建聊天。2026-10-07本轮`wait_threads(timeoutMs:0)`实际返回`idle`、最近turn`completed`，原最终回执报告其目标`complete`。本轮补充在父聊天交付，`get_goal`返回`goal:null`；没有将派发状态当作完成，也没有声称创建/更新了本轮新目标。

最终收口：上述记录与正式稿状态写入后，Luna按同一Python命令和8路径空白命令fresh复验，均exit 0；8文件头、5清单、110本地引用、37行号、6JSON，errors=[]。最终stdout为具名产物目录中的`check-docs-final.out`与`git-diff-check-final.out`。图示未变，沿用本轮14/14渲染回执而不重复浏览器启动；源码/接口调查、实际文稿修订、独立一致性评审和文档验证交付完成，功能与真实业务仍未验收。
