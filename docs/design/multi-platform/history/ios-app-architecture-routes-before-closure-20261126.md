<!-- [Input] 2026-11-15 iOS 架构路线评估全文。 -->
<!-- [Output] 终止 Agent 迁移时保留的决策记录、估算与依据。 -->
<!-- [Pos] 历史快照，围栏内相对路径按原文所在的 multi-platform 目录解释。 -->

# iOS 架构路线评估原稿

2026-11-26 终止迁移后，实施范围以[现行架构决策](../ios-app-architecture-decision.md)为准。以下保留当时的判断和估算。

````markdown
<!-- [Input] AGENTS.md、两个本地仓库当前源码、APP-03历史测量与APP-04现行设计。 -->
<!-- [Output] 路线二与路线三的架构取舍、功能差距、人日估算和分阶段交付边界。 -->
<!-- [Pos] iOS App架构决策；产品交互归mobile-recovery-interaction.md，开发合同归mobile-background-execution-technical.md。 -->
<!-- [Sync] 2026-11-15: 按用户最新指示排除路线一；优先确定挂起与重开恢复，再比较TS迁移，全部新增行为为建议、未实现。 -->

# Kastention iOS App架构取舍

2026-11-15用户已选择路线二，并将实施范围进一步明确为`claude_agent.py`、`claude_mcp.py`、`claude_plugins.py`三个入口及直接依赖，目标目录为`frontend/packages`。现行包结构、简化规则和50–80人日范围见[TS模块化迁移方案](../claude-agent/typescript-agent-modular-migration.md)。本文保留路线比较与原范围估算，iOS挂起/恢复合同继续适用。

## 背景与问题

用户希望减少App启动等待和本地服务管理负担，同时保留手机端Agent编排、工具执行、权限、原会话和恢复能力。模型推理继续使用当前配置的模型服务。当前范围为分析与设计，业务代码、依赖、业务进程、真实模型、提交和部署均保持原状。

2026-11-15用户明确排除路线一。本文只评估路线二“Python业务服务保留，Agent迁移到TS”和路线三“App依赖的本地业务全面迁移到TS”。远端Admin、Gateway、PostgreSQL和Web入口作为现有依赖；其接口随动工作计入相应估算。

## 目标与边界

交付顺序为：iOS执行实例与系统生命周期合同 → 资源与迁移边界 → 音频接口。第一阶段独立完成挂起和恢复设计，TS迁移、播放器与锁屏媒体控制按后续阶段接入。所有拟议变更均处于设计状态。

发现依据为当前源码、历史测量和现行交互稿；核心问题收敛为执行所有权、保存事实和重开核对；方案比较以功能保留及端侧宿主可实现性为标准；交付选用下文路线二及最小路径。用户原需求提及的两份Notion页面，连接器本次均返回标题和空白正文，需求细节采用本轮用户提供的完整要求，未补写页面内容。

## 推荐结论

**当前推荐路线二作为分阶段迁移路线。先在现有App宿主接入后台许可与恢复，再将完整Agent执行责任迁入现有嵌入式Node，Python继续承载其余本地业务。**

该选择把跨语言迁移限制在Agent边界，保留现有日记、卡片结构、Notion、文件、写作和账户接线。TS demo提供可复用的Runner、消息转换和工具交互起点；生产能力以IM合同补齐。迁移完成后，手机端Agent只由Node持有，Python仅提供业务操作，避免同一Thread拥有两个执行者。

路线二保留Python、Node、Next和Python HTTP监听，当前启动仍需等待Python就绪。其直接收益为收敛Agent与CLI之间的语言边界及分离业务服务依赖；启动或内存改善保持待测。若唯一目标为缩短启动，已有证据支持先处理已定位的等待与装配依赖，TS迁移优先级应低于第一阶段恢复接入。

路线三适合用户已决定长期统一端侧业务语言、愿意承担完整功能对齐成本，并把移除App内Python业务宿主与Next列为明确交付目标的阶段。当前完整迁移成本较高，iOS系统执行限制依然存在。

## 概念与规则

### 必须分别持有的对象

| 对象 | 含义与责任 |
| --- | --- |
| TypeScript | 源码语言，需编译为JavaScript；运行能力由实际宿主提供 |
| React Native Hermes | 当前原生界面的JavaScript运行环境；缺少Node的文件、网络、worker和进程接口 |
| 嵌入式Node | 当前App进程内的独立运行环境，持有Next与CLI的Worker；两条路线均复用 |
| Next.js Server | 当前登录、BFF和局部网页依赖的Node应用服务；TS Agent可在独立Worker运行 |
| Claude CLI / Runtime | 原有打包的执行入口与JSONL控制协议，拥有工具循环；语言迁移需适配其启动、控制、退出与文件环境 |
| 业务Thread | Admin保存的对话与归属，进程重开后继续使用原ID |
| SDK会话 | `claude_session_id`和对应transcript，保存模型交互上下文 |
| 一轮执行 | 本次message、dispatch turn、执行者和claim；同一Thread可有多轮执行 |
| 页面订阅 | 当前页面的HTTP/SSE reader；关闭订阅仅结束观察 |
| 后台许可 | iOS给予App的执行时间；系统可拒绝或收回 |
| 系统挂起 | App停止被调度，内存可能暂留；网络对端和远端写入可继续变化 |
| 进程终止 | Python、Node、Worker、Future和内存句柄全部消失；重开创建新实例并核对保存记录 |

恢复消息、核对任务状态、重新开始执行分别处理。SDK `resume`提供历史上下文接续；系统许可、业务claim、工具副作用和结果落库需要应用自己的合同。

### 当前工作区与资料边界

| 来源 | 本次事实 | 使用方式 |
| --- | --- | --- |
| IM本地 | `develop`，HEAD `000f3e8c`；存在大量既有未提交代码及文档 | 以当前工作区为主；本轮仅追加相关文档，保存旧正文与图示 |
| TS demo本地 | `feat/claude-agent-kit`，HEAD `53dc2c4`；存在一份未跟踪动画设计文档 | 以本地源码和已安装SDK 0.2.20为依据，保留无关文档 |
| GitHub参考仓库 | 当前默认分支同为`feat/claude-agent-kit`，分支集合返回HEAD `b22053b153412ed3d5487bccf3cad095ae5acfc0` | 与本地HEAD不同；未读取远端实现并替代本地判断，未执行fetch/checkout |
| demo README | 仍以AI4Sales销售PWA描述产品，数据库为客户、待办与会话 | 用作历史用途说明，功能清单以源码为准 |
| 两份Notion链接 | 返回“IM音频生态系统设计”“修复 iOS 前后台与进程重开恢复”及空白正文 | 需求正文以用户本轮要求为准，连接器返回范围单列 |

### 源码事实与影响

| 编号 | 当前源码 | 核查结果与架构影响 |
| --- | --- | --- |
| E1 | [EmbeddedDreamBackend.swift](../../../frontend/ios/InkMemory/EmbeddedDreamBackend.swift)、[DreamPython.m](../../../frontend/ios/InkMemory/DreamPython.m)、[DreamNode.m](../../../frontend/ios/InkMemory/DreamNode.m) | 原生单例先初始化CPython，再启动同进程Node，最后绑定业务。Python与Node均已嵌入App，无需为TS新增第二套Node |
| E2 | [ios.py](../../../backend/mobile_runtime/ios.py)、[ios_http.py](../../../backend/mobile_runtime/ios_http.py)、[host.cjs](../../../frontend/ios/runtime/host.cjs) | Python装配FastAPI、Factory、业务模块和Uvicorn，再启动原Next；Next需要Python origin。App当前ready依赖整条链 |
| E3 | [transport.native.ts](../../../frontend/src/platform/transport.native.ts)、[InkReactNative.swift](../../../frontend/ios/InkMemory/InkReactNative.swift)、[SessionGate.native.tsx](../../../frontend/src/platform/SessionGate.native.tsx) | Native请求使用原生URLSession/Cookie接BFF；登录验证在ensureStarted后进行。只迁移Agent无法解除当前登录与启动依赖 |
| E4 | [ios_claude_transport.py](../../../backend/mobile_runtime/ios_claude_transport.py)、[worker.mjs](../../../frontend/ios/runtime/worker.mjs)、[ios-process-boundary.mjs](../../../frontend/ios/runtime/ios-process-boundary.mjs) | Python SDK经私有鉴权socket驱动原Node Worker，直接加载Runtime入口；工具命令经包内guest执行兼容层。iOS路径具有专用适配，桌面SDK默认spawn无法直接替换 |
| E5 | [thread_factory.py](../../../backend/claude_agent/thread_factory.py)、[runtime_owner.py](../../../backend/claude_agent/runtime_owner.py)、[event_bus.py](../../../backend/claude_agent/event_bus.py) | Factory以bg_task持有生产者，reader释放走unsubscribe，运行锁持续到生产者结束；该语义应迁移保留 |
| E6 | [useNativeChatThread.native.ts](../../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts)、[nativeChatRecovery.native.ts](../../../frontend/app/_dream/components/chat/nativeChatRecovery.native.ts) | 后台关闭reader，前台重新读history/status；保留主/侧选择、草稿和有效附件引用。待提交到生产者绑定前存在窗口，需增加原生接受回执关联 |
| E7 | [service.py](../../../backend/claude_agent/service.py)、[continuation_data.py](../../../backend/services/admin_data/continuation_data.py)、[resume_transcript.py](../../../backend/libs/claude_agent_kit/server/resume_transcript.py) | 已有snapshot、history digest、claim、arm_query、complete/fail/unknown及本地transcript lease。优先复用这些恢复合同，避免新增独立恢复数据库 |
| E8 | [turn_persistence.py](../../../backend/services/admin_data/turn_persistence.py)、[tool_confirmation_store.py](../../../backend/claude_agent/tool_confirmation_store.py)、[Agent status](../../../backend/routers/claude_agent.py) | 写入结果不明时按原request ID查receipt；工具Future归当前turn内存。`not_found/running=false`仅表示缺少运行实例，业务成功须核对保存终态 |
| E9 | [NativeThreadPresence.swift](../../../frontend/ios/InkMemory/NativeThreadPresence.swift)、[ios.py](../../../backend/mobile_runtime/ios.py) | 已有账户范围的宿主观察与二值显示，独立于页面；该聚合缺少精确turn/生产者身份，后台到期仍需扩展关联 |
| E10 | [Info.plist](../../../frontend/ios/InkMemory/Info.plist)、[原生入口](../../../frontend/ios/InkMemory/InkMemoryApp.swift) | 已有显示组件；当前未见本专项beginBackgroundTask或BGContinuedProcessingTask实现。显示组件与执行时间分别交付 |

demo证据路径以下均相对于`/Users/dmeck/project/claude-agent-next-kit`：

| 当前已有能力 | 源码依据 | 可复用与补齐范围 |
| --- | --- | --- |
| 流式文本、思考、工具事件、usage、错误和停止控制 | `app/lib/claude-agent-kit/server/server/agent-runner.ts` | 保留解析与回调基础，按IM事件DTO和结束语义适配 |
| 会话ID保存、SDK resume、JSONL历史读取 | `app/api/claude-agent/route.ts`、`server/utils/session-files.ts` | 保留会话读取逻辑；业务Thread与SDK会话分别映射，迁移IM claim/transcript合同 |
| toolChoice、canUseTool、AskUserQuestion答案回填、确认入口 | `agent-runner.ts`、`app/lib/tool-confirmation-store.ts`、`tool-confirm/route.ts` | 确认当前按toolCallId存Map/Promise；需补账户、Thread、turn、输入指纹及重复决策校验 |
| 消息parts、附件下载/工作区同步、文件预览与存储 | `app/lib/message-parts.ts`、`chat-attachment-processing.ts`、`workspace.ts`、`file-storage/` | 纯转换函数可筛选复用；工作目录、存储授权和路径约束采用IM边界 |
| PostgreSQL会话与配置持久化 | `app/lib/db.ts`、`db/schema.ts` | demo为销售业务数据模型，含runtime建表/数据重写逻辑；IM迁移采用现有Admin DTO与capability，排除该数据库接线 |
| Node SDK自定义启动接口 | 已安装`node_modules/@anthropic-ai/claude-agent-sdk/sdk.d.ts:764`、`:1547` | SDK 0.2.20已有`spawnClaudeCodeProcess`与SpawnedProcess，具备接入原Worker的扩展点；demo当前未使用 |

demo缺口集中于生产执行边界：`route.ts:512`的request abort会调用Agent abort；每次POST创建Runner，执行跟随响应；最终消息在onFinish中保存，保存错误只记录日志。该路径需要改成宿主持有、事件独立订阅和保存回执驱动终态。现有按message ID过滤重复历史只覆盖存储合并，无法约束重复query或工具执行。当前所读Agent/确认入口缺少IM等价的账户归属与授权链。

## 两路线对照

| 比较项 | 路线二：保留Python业务，Agent迁TS（推荐） | 路线三：本地业务全面迁TS |
| --- | --- | --- |
| 端侧运行组成 | 原生Swift + RN/Hermes + CPython业务 + 嵌入式Node中的Agent/CLI/Next + 原guest工具 | 原生Swift + RN/Hermes + 嵌入式Node中的Agent/CLI和本地业务 + 所需guest工具 |
| Python解释器 | 保留主CPython；Python工具依赖继续按原制品执行 | 移除主业务CPython。Python编写的第三方插件仍需guest解释器；完全移除Python需替换相关插件 |
| 本地Python HTTP | 保留；继续承担Next与Python业务接入 | 全部App业务切换完成后移除 |
| Node / Next | Node必需；当前登录、BFF和局部网页需要Next，先保留 | Node必需。TS语言本身无需Next；本估算包含App认证与局部网页接线迁移，完成后移除App内Next |
| 其他本地HTTP与socket | 保留原Next HTTP和Python HTTP，原CLI私有鉴权TCP控制连接继续使用 | 目标为原生业务桥与包内页面资源桥；完成认证回调和局部网页替换后可移除业务HTTP。原CLI私有TCP控制连接继续使用；只迁移语言无法消除HTTP依赖 |
| Agent执行与事件 | 原Node host持有TS Agent，SDK自定义spawn驱动原CLI Worker；页面订阅IM事件；Python业务调用经原有本地认证接口 | 同一Node host内调用TS业务函数，页面经原生桥订阅；远端Admin/Gateway保持原协议 |
| iOS挂起/恢复 | 原宿主申请许可、绑定原turn、到期收尾；读取Admin claim、消息与transcript核对 | 同一合同；语言统一保持同样的系统限制与副作用不明区间 |
| 功能对齐缺口 | Agent资源准入、上下文、授权、插件/MCP、队列、子任务、回顾/工作流编排、停止、保存/结算和恢复 | 路线二全部缺口，加App本地业务适配、认证、文件与局部页面服务替换 |
| 资源收益依据 | 减少Python→CLI控制跨语言边界；原Node已存在。解释器与业务装配继续占用，新增TS控制Worker可能抵消部分收益 | 删除CPython主宿主与App内Next后可减少模块、装配及服务常驻组成；CLI/Node/Hermes/guest和远端等待仍保留 |
| 资源不确定项 | TS Worker和对象常驻占用、原CLI兼容性、Python业务是否可延迟启动；无迁移前后实测 | 移除组件后的实际内存、能源及启动收益；TS重实现依赖大小、业务访问网络成本 |
| 改动范围 | Agent层和宿主接线；Python业务接口与远端合同尽量复用 | App本地全部业务和原生接线；远端只做必要合同扩展，Web继续原Python路径 |
| 实施成本 | 68–114人日，分阶段交付 | 120–198人日，包含功能对齐和移除App内Next的接线 |
| 维护成本 | 两种业务语言，需维护Agent→Python DTO及一次执行者归属；避免双写与双Factory | 端侧主业务统一TS；Web仍为Python时需维护两种实现的合同，第三方插件与CLI适配仍存在 |

### 人日估算

口径：1名熟悉两个仓库的资深工程师；覆盖实施、功能对齐、集成和必要验证，包含正常评审返工。范围为粗估，表示实际工作量；多任务等待、发布审核和第三方问题耗时单列。音频生态、Android实现、远端平台重写均排除。

| 工作包 | 路线二 | 路线三 | 估算依据及主要不确定项 |
| --- | ---: | ---: | --- |
| 宿主与原生桥接 | 8–14 | 10–16 | 复用DreamNode、host/worker和guest边界；适配SDK SpawnedProcess、线程退出、后台许可和旧代次释放；CLI版本协议兼容性影响上限 |
| 请求与事件通道 | 7–12 | 8–14 | 执行脱离Next请求；保留现有事件DTO、接受回执、读取/停止/确认；路线三增加原生业务桥及局部文档接线 |
| Agent能力补齐 | 22–36 | 22–36 | 资源策略/准入4–6，上下文与Deck/模型/MCP权限6–10，队列/子任务/定时与工作流6–10，事件/工具/文件协作6–10；迁移现有规则，demo基础复用 |
| 保存与恢复 | 12–20 | 12–20 | claim/arm与receipt4–6，transcript及Thread会话映射3–5，失效确认/不明工具结果与UI核对3–5，后台到期和进程代次收尾2–4 |
| 本地业务接入或迁移 | 7–12 | 48–80 | 路线二保留业务，完成已认证内部调用和Agent执行者移交；路线三分解见下表 |
| 集成与必要验证 | 12–20 | 20–32 | 锁屏/拒绝/到期/重开、公开业务合同、原Web兼容、账户权限和工具结果；覆盖设备与系统差异，不以完整迁移充当决策前置 |
| **总计** | **68–114** | **120–198** | 各工作包顺序分工求和，避免把共同阶段重复计入 |

第一阶段“现有宿主中的iOS后台与恢复”约14–24人日，包含在两条路线总量内，来自宿主、保存恢复和集成工作包。可先按现有Python Factory实现，随后整体移交到TS；传输DTO、用户规则与持久化身份保持一致。第一阶段保留CLI原路径，TS Agent完整迁移为后续交付，用户可先获得恢复能力。

### 路线三的本地业务范围

以[当前业务路由清单](../../../backend/routers/__init__.py)与Native入口为依赖图。路由数仅用于发现边界，工作量按实际业务合同计算。

| 业务组 | 当前范围与可复用部分 | 迁移内容 | 人日（已计入48–80） |
| --- | --- | --- | ---: |
| 账户、配置与Admin接入 | auth/oauth/device_oauth、preferences、system_config、gateway_models、product及原BFF | TS严格DTO、capability、用户与服务认证、Cookie/CSRF、系统登录回调；复用远端接口，App内Next退出需完成对应原生登录/调用适配 | 10–17 |
| 日记、卡片结构与资料 | sessions、pictures、voices、friends、reports、deck_plugins/binding/versions及关联UI | Admin数据访问、编辑事件和领域校验；大部分页面TS已有，Python业务规则需要翻译，Admin权威数据保持原处 | 9–15 |
| Notion、回顾、记忆与写作 | notion、reflections、memory、story_workspace | 连接器与投影、分析上下文、工作流协同、结果回写；Agent编排计入上方Agent工作包，纯业务适配计入本行 | 13–22 |
| 插件、文件及分享 | claude_plugins、claude_mcp、storage、workspace、note_shares、external_shares | 插件摘要与目录校验、MCP接线、文件归属/上传预览、发布快照的App消费；远端匿名Web展示继续原入口。Python插件若要求彻底退出需逐项替换 | 10–16 |
| 本地基础设施 | 配置、生命周期、日志错误、异步资源释放与打包 | 替换Python依赖调用，装配Node业务函数；对App依赖闭包逐项清点并删除退出路径，保留Web实现 | 6–10 |

纯DTO、规则和协议可以按行为翻译，现有TS UI、消息parts和原生文件桥可直接复用适用部分。Python的FastAPI/Depends、Pydantic、asyncio、HTTPX、SDK hook、stdio MCP和插件环境管理需要TS实现或平台适配。TS demo销售数据库、客户/待办页面和runtime DDL不进入IM。

### 资源依据

[APP-03记录](../../exec/app-experience-python-performance-20261102.md#三份启动观察)保存三次Simulator观察：总启动6.784–7.428秒，CPython初始化14.614–23.071毫秒，首次入口导入829.677–881.504毫秒，Factory准备3270.638–3924.306毫秒；其内原生Admin传输等待为2980.441–3629.962毫秒。三份制品存在UI差异，测量记录归历史候选，本轮未重跑原始采样。

这些数据支持“历史Simulator的主要已测启动等待位于Factory原生Admin传输边界”。其等待还包括原生调度、网络、回调与重新获取GIL，接口级贡献未确认。该证据无法推导当前iPhone耗时、Python计算性能损失或TS迁移收益。当前CPU/热状态诊断与模块线程采样可复用；本轮未取得各运行环境独立内存、能源或迁移前后对照。

路线二继续装配Python业务与登录依赖，迁移Agent控制代码无法自动消除上述Admin等待。路线三减少运行组成有源码依据；可节省多少启动、内存和电量须后续按同制品同设备测量。

## 推荐架构与最小改动路径

### 当前可决定的事项

1. 原生App宿主持有执行许可和精确任务关联，页面只订阅。语言切换保持该责任不变。
2. 第一阶段采用有限后台时间；iOS 26持续任务只对已具备实际进度和受控收尾的工作开放。普通开放式Agent无法给出准确总体进度时沿有限能力运行。
3. 复用Admin continuation claim、消息metadata、receipt和SDK transcript；重开只读核对，缺失终态不显示成功，不自动重发query/工具。
4. TS Agent接入现有嵌入式Node，通过SDK自定义spawn适配原CLI Worker。Hermes仅承担界面，App无需新增Node实例。
5. 路线二保留Python业务HTTP和原Next登录路径。现有业务、权限、资源策略与临时目录规则完整迁移。

### 关键技术事实与条件

| 条件 | 当前证据 | 对决策的影响 |
| --- | --- | --- |
| SDK 0.2.20能否通过自定义SpawnedProcess完整控制包内Runtime | 本地类型已提供扩展点，原Worker协议已存在；两者集成尚未运行 | 支持路线二可实施判断。若Runtime协议不兼容，先保留原执行宿主并适配既有SDK边界，增加4–8人日，路线三同受影响；无需完整重写demo才决定 |
| 路线三移除Next与业务HTTP的登录及页面接线 | [InkAccountLogin](../../../frontend/ios/InkMemory/InkAccountLogin.swift)已有原生回调接收，当前仍转交本地`/auth/callback`与原BFF处理；局部Web页面仍由原Next承载 | 需要把既有认证事务、Cookie交接和局部资源读取迁入TS/原生边界，保留原身份验证及回调校验。该工作计入路线三账户与通道包；保留当前接线时仍需Next/HTTP，不能宣称服务已移除 |
| 开放式Agent是否符合持续后台任务进度合同 | 原事件有增量/工具/结束，缺少已知总量 | 当前决定使用有限后台能力；未来具备确定工作单元后独立接持续任务 |
| 共享Admin现有capability是否可满足新的状态核对字段 | Dream消费方已实现continuation.v1，线上发布状态本轮未检查 | 复用现有capability；新增跨进程结果核对字段须先由Admin Drizzle发布，缺失时fail closed，相关随动计入保存恢复包 |
| App当前全部本地Python依赖是否包含Python插件 | 原ios_mcp、plugin-python和guest制品具备Python工具路径 | 路线三移除主CPython后，完整插件生态仍可能携带guest Python；完全移除解释器需按实际启用插件范围计入业务迁移，超出既有插件范围重新估算 |

### 实施顺序

| 顺序 | 最小交付 | 退出条件 |
| --- | --- | --- |
| 1 | 在现有EmbeddedDreamBackend/InkRuntime及Factory观察边界增加精确接受、许可和到期关联 | 后台取消reader仍保留已接受生产者；系统到期只收尾绑定turn，旧回调无法停止新turn |
| 2 | 沿原claim、消息和receipt核对恢复，补页面的不明/停止中/等待回答反馈 | 同进程返回与新进程重开分别核对；缺失生产者和保存终态均不报成功；重复工具风险阻断 |
| 3 | 复用demo Runner与转换函数，在host.cjs增加TS执行所有权和SDK spawn适配 | 原CLI、文件、权限、资源策略及事件协议保持；不启动demo Next销售应用 |
| 4 | 迁移完整Agent上下文、工具确认、队列、任务协同、保存和结算接线 | 同一Thread仅一个执行者，Python业务调用带原授权与DTO，缺capability拒绝；按业务逐项对齐 |
| 5 | 原移动Agent入口整体切换到TS，移除其Python生产者责任 | 正常入口与恢复入口均落到同一TS宿主；Web保持原公开合同 |
| 6 | 按已有测量处理资源装配和启动等待，音频边界独立接入 | 性能结论来自后续实际测量；播放仅按实际媒体及用户选择执行 |

步骤1–2构成第一阶段，可以先于步骤3–5交付。步骤3–5为路线二的Agent迁移交付，现有Python业务服务保留。切换以明确运行capability和一次执行者归属控制，部署环境名称不参与业务行为选择。

## 最小验证建议

本轮只做文档检查，以下为后续实现时的有限验证建议：

- 用已安装SDK类型和原Worker协议做一次无模型控制握手，覆盖stdin/stdout、退出、取消和原临时目录；验证自定义spawn集成事实。
- 通过公开生产入口、隔离provider验证一次接受后断开reader、一次绑定前切后台、一次旧turn到期和一次进程重开读取；沿原DTO与claim核对零重复query。
- 真实设备验证一次锁屏许可到期和一次进程重开；用户及模型验收需另有当次授权，本轮未执行。
- 资源阶段先复用已有阶段计时，补同设备的Python/Node/CLI活动与进程内存观测。数据用于选择精简项，架构推荐已按当前事实给出。

## 目标匹配与过度设计评审

| 结论 | 评审项 | 最终处理及理由 |
| --- | --- | --- |
| 保留 | iOS生命周期先于迁移 | 第一阶段单独可交付，先建立任务接受、许可、保存和恢复责任 |
| 保留 | 路线二与路线三实际运行组成与人日 | 两者均需嵌入式Node/CLI适配；成本覆盖业务与功能对齐，语言统一收益定性陈述 |
| 保留 | 原Thread、SDK会话、claim、receipt与原生宿主 | 当前已有身份及持久化能力，避免丢失IM功能 |
| 简化 | 原技术稿多层BackgroundWorkAdapter与平台实现类 | 本轮iOS范围只在EmbeddedDreamBackend内增加许可方法与运行关联；旧类图保留历史正文，实际类拆分等待实现需要 |
| 简化 | 独立恢复服务、执行数据库与新任务状态表 | 复用Admin continuation、消息metadata、transcript及现有草稿；跨进程新字段确有需要时由Admin capability提供 |
| 保留 | 页面断连、用户停止、到期分别处理 | 断连只结束观察；用户停止走原停止；到期按绑定turn有界收尾，原因无法核实时显示事实 |
| 保留 | 工具副作用与保存状态不明 | 停止自动推进，核对原回执；任意外部工具缺少幂等或查询接口时保留不明，不自动重放 |
| 延后 | 持续后台任务适配 | 第一阶段使用有限时间；实际进度能力齐备的工作再接iOS 26持续任务 |
| 延后 | 资源精简、全面业务TS与音频生态 | 分别属于后续资源取舍和媒体能力，第一阶段验收独立完成 |
| 删除 | 为保活新增音频、心跳、重复申请许可和常驻调度 | 用户任务缺少该运行依据，且无法保证系统持续调度 |
| 删除 | 完整重写demo或先执行全量测试再决定路线 | 现有源码足以作出推荐；验证聚焦SDK启动适配和生命周期边界 |

本轮产物为设计，新增行为与性能收益均未作为已实现或已验收结果报告。产品场景与图示见[第一阶段交互补充](mobile-recovery-interaction.md#2026-11-15-ios第一阶段任务交互)，运行拓扑与生命周期见[开发合同补充](mobile-background-execution-technical.md#2026-11-15-ios第一阶段宿主与恢复合同)。

## 外部依据与本轮检查

- [GitHub参考仓库](https://github.com/glide-the/claude-agent-next-kit)及[当前分支集合](https://api.github.com/repos/glide-the/claude-agent-next-kit/branches)：本次只读核对远端HEAD差异，本地实现为主。
- [音频需求](https://app.notion.com/p/IM-db930b7547c383b0917501d0ea510ed0?pvs=21)、[iOS恢复需求](https://app.notion.com/p/iOS-40c30b7547c380689349f87592b3eeac?pvs=21)：连接器返回空白正文，细节采用本轮用户要求。
- [Apple有限后台执行](https://developer.apple.com/documentation/uikit/extending-your-app-s-background-execution-time)：任务开始前申请，完成后及时释放；到期处理需有界。
- [Apple持续后台任务](https://developer.apple.com/documentation/backgroundtasks/performing-long-running-tasks-on-ios-and-ipados)：用户前台发起、实际进度、系统取消与无通知关闭约束，2026-11-15读取官方Markdown。
- [Hermes](https://reactnative.dev/docs/hermes)：当前RN JavaScript引擎；本地Podfile.lock已核对实际工程使用。

2026-11-15由限定的luna_test_runner执行文档验证，主Agent复核脚本和命令回执：

| 命令或检查 | 退出码 | 关键输出 |
| --- | ---: | --- |
| `python3 /tmp/ink-ios-architecture-doccheck-20261115/inventory-links-check.py` | 0 | 7份文件、头部及清单有效，272个本地引用/锚点检查失败0；新增文字禁用词0 |
| 原Node内直接`mermaid.parse` | 1 | 20块中9块通过，11块遇到`purify.addHook is not a function`，原Node环境缺少DOM；作为harness失败保留 |
| `node /tmp/ink-ios-architecture-doccheck-20261115/mermaid-browser-check.mjs` | 0 | 本机已有Chrome与Playwright解析20/20，新增图示渲染6/6，失败0；隔离浏览器已关闭 |

完整回执保存在`/tmp/ink-ios-architecture-doccheck-20261115/receipt.md`。Chrome检查只加载包内Mermaid与空白文档，未访问业务页面、运行本地服务器或安装依赖。本轮只修改7份设计、产品与目录文档，旧正文和图示保留。检查范围限定文档结构与图示，不代表功能、真机或真实模型验收。
````
