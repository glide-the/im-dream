<!-- [Input] 保留网页业务复审前的执行记录原文。 -->
<!-- [Output] 历史计划、偏移设计和实际验证回执，供范围追溯。 -->
<!-- [Pos] 已退出当前实施依据的移动执行记录快照。 -->
<!-- [Sync] 2026-10-25: 原文及SHA-256保留，现行执行记录在原路径维护。 -->

# 保留网页业务复审前历史

原文件：`docs/exec/mobile-app-design-review-20261024.md`。内部相对引用按该原路径解释。当前实现以[现行复审](../mobile-app-design-review-20261024.md)为准。

SHA-256: `29227e0da861d0c0dfa22a7a63c54e7a33f9cc7d9d3fe870a0f55f017d305733`

<!-- original:start docs/exec/mobile-app-design-review-20261024.md -->
<!-- [Sync] 2026-10-25: 当前结论见文末保留网页业务复审；此前方案及回执为阶段历史。 -->
<!-- [Sync] 2026-10-25: record native Python implementation, simulator execution and physical-device prerequisites. -->
<!-- [Input] 双原生宿主、端侧Python、当前代码切片、独立公网边界、源码与官方资料。 -->
<!-- [Output] 设计判定、iOS最小宿主、范围收敛、后续依赖及分层验证回执。 -->
<!-- [Pos] 移动架构、双平台设计和第一实现切片的现行项目执行记录。 -->
<!-- [Sync] 2026-10-24: 按用户反馈删除未接线抽象，收敛iOS宿主并保留前轮验证历史。 -->
<!-- [Sync] 2026-10-24: 对齐能力门禁、限域传输、平台配置、代码评审与最终验证回执。 -->

# 端侧移动应用设计评审与后续工作

**现行结论以文末“2026-10-25 保留网页业务的设计复审与实现修正”为准。此前优化提示词、候选方案、任务项和回执按阶段历史保留，退出本轮实施依据。**

## 交付与范围

| 交付物 | 现行文档 | 状态 |
| --- | --- | --- |
| 问题判断、兼容证据、参考映射、架构和发布 | [技术稿](../deploy/mobile-app-release.md) | 供审查；完整原CLI本地发行不通过 |
| 用户任务、设备内执行、页面骨架 | [移动PRD](../prd/dream-workspace/mobile-app.md) | 目标设计，能力待实现 |
| 运行时与代码归属 | [共用架构](../design/story-workspace/mobile-runtime-architecture.md) | WebView、Native、Python、bridge和公网边界已定义 |
| 共享用户旅程与状态 | [共享交互](../design/story-workspace/mobile-app-interaction.md) | 正常/异常、任务与恢复语义已定义 |
| iOS平台交互 | [iOS设计](../design/story-workspace/mobile-ios-interaction.md) | 独立拓扑、骨架、时序、状态图和当前实施证据已完成 |
| Android平台交互 | [Android设计](../design/story-workspace/mobile-android-interaction.md) | 独立拓扑、骨架、时序和状态图已完成 |
| 第一实现切片 | `frontend/mobile/**`、`frontend/app/_dream/platform/**`、`backend/mobile_runtime/**`、`mobile/**` | 共享资源/协议/资格门禁/宿主代码已落盘；完整业务受门禁 |
| 原始远程宿主四稿与旧检查回执 | [历史快照](history/mobile-app-remote-host-before-device-python-20261024.md) | 原文保留，已退出当前路线 |

用户最终要求：保留Swift/WKWebView与Kotlin/Android WebView；Dream Python在设备运行；核对Claude CLI兼容；原生宿主定义WebView、内置进程和共享系统能力；参考Codex恢复语义；Admin独立公网部署；完成设计评审和方案代码。跨端框架讨论保留为选型记录，用户最终选择原生宿主。

本轮已增加设计文档、第一实现切片和iOS宿主强化，并执行本机具备条件的构建、单元、模拟器启动和连接设备预检。未调用真实模型，未修改数据库、业务数据或运行服务，未创建或修改凭证证书，未提交商店或发布。外部Admin没有改造、部署、migration或版本发布任务。

## 优化执行依据与收敛

本次实质范围更新前完成一次提示词优化；常规资料补齐与评审修订沿用同一执行依据。

**Optimized Prompt：**

在Ink & Memory现有Next.js/React/Python和只读Codex参考源码基础上，完成双原生宿主的可审查设计与第一实现切片。iOS使用Swift/WKWebView，Android使用Kotlin/Android WebView；一个签名安装包承载随包React资源、原生宿主和端侧Dream Python。明确WebView、原生平台能力、嵌入Python、Claude Runtime、公网用户服务和应用私有文件的所有权；使用版本化method/event白名单形成uni-app风格语言桥接，无Lua、动态反射或自由URL。分别编写iOS与Android正式设计稿，包含页面骨架、正常/异常时序、React-Native-Python调用、运行时与任务状态。参考Codex的先订阅后hydrate、事件缓冲、generation隔离、提交失败恢复草稿、Stop与终态分离、resume后重取流所有权语义，不复制其源码、协议、资源或二进制。实现共享React移动构建入口、bridge合同与校验、Python资格边界、Swift/Kotlin轻量宿主和明确能力门禁；Python、公开认证、本地ASGI未合格时禁止挂载完整业务，Claude Runtime未合格时阻止Agent创建与推进，所有路径禁止远程代跑。Admin保持独立公网部署，不修改其代码、schema、部署或服务身份。执行前端/协议/Python单元、可用平台构建和文档/Mermaid检查；Android工具链缺失时记录前置失败。禁止真实模型、凭证、签名、商店提交和正式发布。最终逐层区分设计、代码、静态/编译、Python、CLI、真实业务、签名和发布状态。

**Optional Enhancers：** 后续任务可在B01–B03逐项闭合后增加真机性能预算、TestFlight/Play测试轨道自动化和渠道材料模板；每项以真实账号、签名资格和明确发布授权为前提。

### iOS实施计划优化

连接iPhone后的实施计划再次执行一次提示词优化，后续常规编码与验证沿用该结果。

**Optimized Prompt：**

在Ink & Memory当前未提交工作基础上完成可审查的iOS实现：保护用户和其他Agent改动，只修改iOS宿主、共享移动bridge/启动入口及对应文档；使用Swift/WKWebView加载随包React资源，强化main-frame origin校验、每文档generation所有权、陈旧异步回调清理、导航/renderer有界恢复、生命周期和网络快照、键盘安全区、脱敏日志及本地资源根目录约束；为原生启动响应设置共享超时并提供可重试反馈。先审计仓库与本机是否存在可签名的iOS CPython、完整依赖和Claude Runtime制品；缺少目标artifact时保持`python`、`localTransport`、`publicClientAuth`、`claudeRuntime`和`files`失败关闭。使用已连接iPhone执行只读设备/签名预检；只尝试现有自动签名条件，禁止创建、导入、删除证书或profile。执行React/Swift单元、模拟器安装启动、generic iPhoneOS无签名编译和签名探针，准确区分代码实现、模拟器技术验证、真机安装、端侧Python、真实业务、签名和发布状态。

**Optional Enhancers：** Developer Mode、Team、证书、bundle ID和合格CPython artifact到位后，继续执行真机安装启动、WebView origin/localStorage、前后台、renderer恢复及stdlib-only Python smoke；完整Dream与Claude Runtime仍受B01–B03门槛约束。

| 阶段 | 决策依据 | 本轮交付 |
| --- | --- | --- |
| 发现 | UI可共享，当前Python启动依赖服务机密、CLI、stdio进程及本机记录 | 源码/官方兼容矩阵，区分解释器和完整业务 |
| 定义 | 用户需要设备执行，远程宿主前提已失效；Admin公网独立不改变现有服务间协议 | 三项核心阻断与外部范围边界 |
| 比较 | 原CLI全本地、进程内替代runtime、远程执行三条路线 | 原CLI双平台不通过；替代runtime为待审查候选，远程方案退出 |
| 交付 | 原生宿主和端侧Python目标保留，发行前置条件清晰 | PRD、共享架构、双平台设计、发布稿、第一代码切片与分层回执 |

## 核心阻断与设计判定

| ID | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| B01 本地Agent执行 | iOS不支持当前CLI子进程模型；官方CLI无手机目标；Android无项目移动制品资格 | 将CPython与CLI分开，审计stdio/Bash/插件/Notion/恢复完整依赖 | 撤销完整CLI可随包运行结论；不改远程执行，替代runtime独立候选 | 可审查的本地实现及能力等价范围；iOS原方案明确阻断 |
| B02 公开客户端权限 | 当前Python/Next BFF要求服务secret，用户token仍附服务token | 禁止service secret/token/client_credentials上端，只核对既有公开用户能力 | 移除Admin新接口/注册URI/capability/部署任务；现内部客户端无法直接发行 | 现公网用户级权限能否覆盖消息/Run/资源/结算/回执；缺少即继续阻断 |
| B03 Python与ABI | 后端含Pydantic-core/crypto/Pillow/cffi等，当前锁无手机加载证据 | 两平台解释器/扩展/ABI/签名资格分开 | 嵌入方式有官方路径，整个backend运行未证明 | 精确版本交集与手机真机import/启动资格 |

**最终设计评审：待满足明确前提后通过。** 设计已经给出两个平台的安装、页面、端侧进程、桥接、Python、构建与发布路径，并用能力门禁约束未完成环节。明确前提为B01移动Claude Runtime、B02公开用户权限和B03平台Python/原生扩展资格闭合。

**当前发行评审：不通过。** 判定对象为“保持现有完整Dream及Claude CLI，双平台端侧运行并正常商店发行”。B01–B03仍未闭合，第一代码切片只建立宿主、协议和失败关闭路径，不能进入签名或商店发布。

原生宿主与端侧Python目标保持为已选方向。进程内Agent候选涉及权限、工具、插件、MCP、恢复及成本，当前只保留资格接口与能力门禁；公开用户接口缺口不自动扩展为Admin任务。

## 设计评审与修订

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 运行位置 | 旧稿加载远程页面并由服务器执行 | 保存旧稿，现行稿改为随包资源+本机Python | 实际手机包内执行成为验收条件 | 移动装配与真实运行证据 |
| 当前源码复用 | React/DTO/路由有复用面，Next动态BFF和全startup无法复制 | 同一frontend根增加esbuild移动入口、显式bridge和临时限域fetch shim | 移动资源从`_dream`唯一源码生成，Next继续拥有Web；移动产物替换5个远程brush URL | 完整API/HTML资源/FormData/WebSocket/认证逐项迁入显式适配并回归 |
| CLI能力 | “能运行Python”无法推出SDK/CLI可运行 | 官方平台与项目fork版本分开，逐项进程/工具审计 | B01明确不通过，Android实验不代表iOS | 合格移动实现与独立平台验证 |
| 公网服务范围 | 前稿安排Admin注册、协议及后端业务 | 改为现有公开能力消费核验 | 无Admin开发/部署/数据库任务，无虚构删除/举报接口 | B02和渠道资格缺口供审查 |
| 生命周期 | asyncio task在设备被挂起/终止时无法持续执行 | 重写状态与异常时序，区分已保存内容和内存执行 | 无后台常驻/自动续跑/准时调度承诺 | 真机锁屏/后台/kill验证 |
| 恢复与跨设备 | 原CLI恢复要求本机workspace/JSONL | history阅读、文件可读、执行恢复分开 | 缺记录失败关闭，不新建/改绑/自动同步 | runtime本地记录合同及设备文件可用性 |
| 文件归属 | 旧稿全为服务器文件 | 本地workspace与云storage区分，选择先准备本地 | 不隐含云上传/同步；导出用户文件不自动删除 | 附件DTO和云端用户权限覆盖 |
| Stop/队列 | 回执可仍running，队列仅纯文本 | 保留原受理/终态与queue独立反馈 | running=false+history真实结果才结束展示；附件不自动排队 | 适配后端到端一致性 |
| 认证与秘密 | 移动公开客户端无法保守服务器机密 | Native安全存储只接合法用户授权，公开接口不足阻断 | 无Keychain包装service secret方案 | B02 |
| 引入复杂度 | 本地目标触发新的runtime/embedding/transport工作 | 只列有具体需求的入口和平台层 | 无离线DB、同步、通用插件/发布平台；替代runtime不默认实施 | 用户审查候选能力范围 |
| 平台发布 | Python嵌入合法路径与CLI技术阻断不同 | 账号/签名/扩展/动态代码/隐私/支付逐项定义 | 无“Python一律不能上架”结论，无法跳过B01–B03 | 后续账号/地区/实际制品/审核 |
| 图示和验证 | 共享稿无法表达两平台进程和系统行为 | 新增共用架构、iOS稿和Android稿；图中逐项标记当前/建议 | 双平台各有拓扑、骨架、正常/异常、调用和状态图 | Mermaid、链接与最终代码行号检查 |
| 桥接抽象 | Lua会增加第三种运行语言和动态执行面 | 使用JSON清单、TS/Swift/Kotlin/Python类型镜像和固定白名单 | 满足共享系统组件调用，无Lua与动态插件机制 | 流事件、业务path allowlist和生成/一致性验证 |
| iOS宿主 | 当前任务需要加载本地前端并接入本机Python | 收缩到WKWebView和直接bridge；删除未接线平台Registry、文件仓库及设备预检框架 | 本地页面可构建，完整端侧Dream未完成 | Python及依赖制品、认证/CLI兼容和真机签名 |
| Android宿主 | 需要WebView与端侧Python容器 | 落盘UI进程+非导出`:dream_runtime`私有服务、Binder和文件批次回滚 | 进程职责清楚，后台终止进入恢复流程；外链allowlist为空 | Gradle bootstrap、Android SDK36、CPython ABI与实际构建 |

## iOS宿主实施回执

### 范围收敛

**Optimized Prompt：** 根据用户“过度设计”的反馈收缩当前iOS实现。保留Swift/WKWebView加载同源随包React、必要的来源/请求校验、页面generation隔离和启动失败反馈。删除本轮尚无调用方的原生文件副本管理、通用平台registry、重复原生错误页面和设备预检脚本；启动超时直接由移动入口负责，移除共享可配置超时框架。共享React业务保持单一来源，Python与Claude CLI沿用已核验阻断，缺少实际制品时准确反馈。只修改本任务代码和对应文档，保留已有验证历史，执行必要编译、单元与文档检查。当前交付定义为可编译的iOS宿主，完整端侧Dream继续标记未完成。

**Optional Enhancers：** 实际Python装配或首个系统能力接线产生需求后，再增加对应方法与验证。

当前iOS交付为本地页面宿主。端侧Python、公开用户认证、本地ASGI和Claude Runtime仍未接入。

| 收敛项 | 处理结果 | 剩余依赖 |
| --- | --- | --- |
| 通用能力Registry | 宿主直接处理app信息、启动和生命周期状态；删除额外protocol/registry层 | 实际Python调用设备能力后按需接线 |
| 文件副本仓库 | 删除未开放的iOS文件、选择/保存/分享实现与配置 | 首个文件业务及账户/Thread归属 |
| 失败恢复界面 | 取消独立原生页面；加载失败使用系统重试提示，renderer只自动重载一次 | 真机故障验证 |
| 启动框架 | 删除共享timeout policy和自动重新hydrate订阅；移动入口保留一个定时器和手动重试 | 本地服务实际启动 |
| 用户反馈 | 删除内部模块和reason code清单，保留一句说明与重试 | 产品工作区需Python接入后开放 |
| 设备预检 | 删除专用脚本；使用Xcode/devicectl直接检查 | Developer Mode、Team、签名身份及bundle ID |
| 正确性检查 | 保留origin/method/path/generation校验和AbortSignal清理 | 实际运行时接入后补对应业务测试 |

收敛前完整设计及实施表已保存在[历史原文](history/mobile-ios-before-scope-reduction-20261024.md)。参考宿主实现见[`MobileHostViewController.swift`](../../mobile/ios/InkMemory/MobileHostViewController.swift)，当前启动入口见[`entry.tsx`](../../frontend/mobile/entry.tsx)。

连接设备审计识别到一台已配对的物理iPhone，设备处于开机解锁后的有线连接状态。Developer Mode关闭，DDI服务不可用；Xcode工程未配置Development Team，Keychain有效codesigning identity为0，bundle identifier仍为占位值。generic iPhoneOS无签名编译通过；常规签名构建在provisioning阶段以“requires a development team”退出。当前没有可安装签名制品，真机安装和启动没有执行。

仓库、本机SDK和现有模拟器App均未发现`Python.xcframework`、iOS标准库或libpython。完整依赖中的`aiohttp`、`cffi`、`cryptography`、`pydantic-core`和`websockets`没有锁定iOS wheel；现有Claude SDK仍通过`anyio.open_process`启动CLI，项目CLI发行白名单只有darwin/linux四项目标。iOS能力快照继续准确返回unavailable。

### 独立审计证据

前端审计确认`_dream/**`可作为独立浏览器资源图构建。当前移动入口临时替换`globalThis.fetch`并只路由相对字符串`/api/**`与`/auth/**`，完整业务中的FormData、HTML资源/导航、WebSocket和现有POST form仍未覆盖；显式transport、文件handle和系统授权适配继续列M05/M07。认证审计确认现有Next BFF Cookie/CSRF与移动public client属于不同合同。流式适配保留ReadableStream、AbortSignal、EOF、错误body与响应校验。

iOS/Runtime审计确认当前SDK通过subprocess启动CLI，iOS端须使用3.13+合格Framework和已签名原生扩展回执，普通桌面import探针不能提升移动资格。Android/参考审计确认私有runtime service、Binder、固定appassets origin适合宿主边界；Codex的hydrate缓冲、generation、草稿恢复、Stop和resume语义可复用。参考仓库未发现覆盖整仓复制分发的许可，设计只引用语义和路径。

独立范围、源码、身份和平台审计已完成，修订记录如下；设计结论为待满足明确前提后通过，发行结论继续为不通过。历史快照回执只适用于前稿。

| 独立评审发现 | 当前修订 |
| --- | --- |
| 新发行配置术语与现有resource-policy混淆 | 删除另一套default/desired/effective/revision定义，明确原policy合同与B02/M05未闭合 |
| agent_factory导入期读取策略 | 在源码矩阵补导入期依赖，禁止仅改startup就宣称可嵌入 |
| runtime职责包含持久化 | 图示改为runtime调用模型，Python业务模块保留原持久化职责 |
| 状态图缺正常完成/失败及回读仍运行分支 | 补Running→Hydrating、Hydrating→Running/Ready，保留原工具确认业务规则 |
| 既有插件/脚本/调度被称默认新增 | 改为现有能力移动支持待审查，不静默缩减 |
| 附件组件职责与授权取消图 | 明确useFileUpload和AIInputDock分别职责，正常授权图只表示成功 |
| 商店矩阵缺显式正式分发结果 | A26补审核通过、选定地区/轨道分发和实际安装样本 |
| `claudeRuntime`从应用门禁移除后无业务feature gate | 明确应用required三项；M07覆盖Chat/Dream/Writing Agent创建、发送、建议、评论与工具确认入口，历史和Terminal结果保持可读 |
| 现有Auth POST与移动CSP冲突 | 移动认证维持unavailable；后续系统授权、callback、安全存储和会话投影独立接线 |
| Python探针与Native快照未组合 | 明确资格事实来自目标artifact回执；Native组合根加载与合并列M05/M06 |

独立聚焦复核确认上述修订闭合：设计文档通过内容与范围评审，完整原CLI双平台发行资格继续不通过。该评审为只读文档/源码审查，无运行验证。

## 后续工作项

第一代码切片已完成到宿主、协议和资格门禁。后续按门槛顺序推进；阻断成立时停止完整业务、签名和发布工作。

| 工作项 | 建议负责人职责 | 依赖与边界 | 交付物/验收条件 |
| --- | --- | --- | --- |
| M00 宿主与门禁切片（已完成） | 前端/移动/Python负责人 | 不依赖服务secret、模型或完整Python | 共享React资源构建、v1 bridge、Python资格边界、iOS/Android宿主容器和明确unavailable状态；iOS只保留本地WebView、直接bridge、必要校验与启动失败重试，验证结果见本稿末尾 |
| M01 决策审查 | 产品/技术负责人 | 当前四稿、B01–B03 | 确定原CLI保留要求与替代runtime是否进入后续设计，确认功能范围/地区/账号；不默认改公网服务 |
| M02 权限资格核对 | 移动/安全负责人 | 只用既有公开文档与用户授权能力，不读服务secret | 逐业务列用户客户端可用入口、scope/刷新/归属/回执；覆盖不足写明B02，不绕过检查 |
| M03 Python依赖资格 | iOS/Android负责人 | 独立允许的技术任务，精确依赖清单 | 两端解释器/扩展来源、ABI、签名、import与启动最小回执；无服务/模型调用 |
| M04 Agent兼容决策 | Runtime负责人 | B01官方限制和项目精确fork清单 | iOS原CLI子进程路径不成立的明确结论；Android可行性分开；候选runtime工具/权限/MCP/取消/恢复差异及成本供审查 |
| M05 共享资源与传输 | 前端/移动/Python负责人 | 资源、bridge和限域fetch shim首段已完成；业务接线依赖M01/M02/M04 | 完成显式transport、ASGI组合、target receipt加载/能力合并、业务path allowlist、FormData/文件/WebSocket/认证适配及payload schema校验；保留原业务入口/parser |
| M06 平台与文件 | 两平台/后端负责人 | iOS保留最小容器，系统动作待首个业务接线；Android保留前轮适配；Python/账户接线依赖M02–M05 | 完成解释器、账户目录、picker到workspace、生命周期和真实本地执行位置 |
| M07 核心业务资格 | 业务/Runtime/测试负责人 | M06、合格本地runtime和公开权限 | 接入`claudeRuntime`业务feature gate，覆盖Chat/Dream/Writing Agent/建议/评论/工具确认；完成原队列/Stop/工作区/恢复全流程与缺能力反馈，无远程替代 |
| M08 构建签名CI | 发布/平台负责人 | M03–M07与账号签名 | Python/扩展/资源同SHA打包、IPA/归档/APK/AAB、符号/摘要/秘密扫描、ABI与16KB记录 |
| M09 渠道资格 | 产品/发布负责人 | 地区/权益及已有账户反馈能力 | 隐私/AI许可/登录/删除/举报/付费模式及动态代码说明，缺口写为发行阻断 |
| M10 真机技术与真实业务 | 测试/业务负责人 | M07–M09、后续明确授权 | 实际手机安装包内执行，用户指定账户/实体与正常公网服务，记录可复核结果；Mac服务不冒充手机运行 |
| M11 测试分发/正式发布 | 发布负责人 | B01–B03关闭、M10、渠道审核通过 | TestFlight/Play真实安装升级、审核、放量、暂停与修复回执 |

当前授权覆盖设计、第一代码切片、iOS宿主实施及现有条件下的设备预检/构建/模拟器验证。购买账号、创建或修改证书/profile、真实模型、测试分发和正式发布仍待后续任务。

## 后续验收矩阵

以下矩阵是后续完整验收计划。M00已经执行的资源构建、bridge/Python单元、静态检查和可用平台编译只记录为技术验证，未满足任何需要嵌入Python、真实账户、真机、签名、渠道或商店的验收项。iOS、Android分别留证据；原CLI兼容缺失直接记录阻断。Provider-free技术验证与真实业务/模型验收分开；真实验收必须在实际手机包内执行，并使用经后续授权的真实账户与既有公网业务，保留正常记录。

| ID/平台 | 场景 | 预期结果 | 验证方法 | 执行前提 |
| --- | --- | --- | --- | --- |
| A01 iOS、Android分别 | Python嵌入与本机执行位置 | 实际包内解释器/模块执行，资源与ABI匹配，无Mac/远程后端代跑 | 设备进程、模块路径、无正文本机回执及网络调用边界 | M03、专用测试构建，后续授权 |
| A02 iOS、Android分别 | 原生扩展加载 | 固定Pydantic-core/crypto/Pillow/cffi及所有活跃依赖可import | 真机目标ABI最小import、签名与依赖清单 | 正确解释器ABI及平台制品 |
| A03 iOS | 原CLI/SDK子进程 | 现路径按官方限制记录不兼容，不用模拟器/Node替代证明 | 源码/官方证据；有明确新本地实现才做相应资格 | M04架构决策；当前B01阻断 |
| A04 Android | 原CLI及工具链 | 官方目标、ABI、执行入口、stdio/工具/sandbox逐项有证据 | APK实际运行验证；Termux不计 | 经审查的可行本地制品与M04，当前无资格 |
| A05 iOS、Android分别 | 服务机密排除 | 安装包/资源/日志/配置无server secret、服务token/私钥 | 制品静态扫描、依赖配置核对、授权调用记录 | M02/M08；不读取或输出秘密正文 |
| A06 iOS、Android分别 | 公开用户业务权限 | 用户级scope覆盖消息/Run/文件/结算/回执，越权拒绝 | 已有公开入口逐项contract验证 | M02；缺覆盖保持B02，不能创建替代云代理 |
| A07 iOS、Android分别 | 首装/冷启动 | 页面与Python就绪后进入；失败明确重试，无不可用核心伪装 | 实际包安装、启动失败技术场景 | M06/M08、合格能力 |
| A08 iOS、Android分别 | 版本升级 | 同签名身份升级，保留账户目录/偏好/记录，兼容不损坏 | 上一受支持包→新包，文件清单与历史回读 | 两版本/同签名、非敏感自有数据 |
| A09 iOS、Android分别 | 登录/取消/拒绝/过期 | 系统认证匹配活动事务，用户凭证仅安全存储，原页草稿保留 | 真实系统流程及错误回调技术验证 | 已有公开授权能力、M02 |
| A10 iOS、Android分别 | 失效/退出/换账户 | 失效暂停联网；撤销失败保留；成功锁定文件，跨账户拒绝 | 测试用户公开入口、目录/凭证验证 | M06、可删除测试会话 |
| A11 iOS、Android分别 | 核心Chat/Dream | 本地编排，原DTO/权限/思维模式/问题/初稿规则一致 | 先provider-free公开入口，再获授权真实模型全流程 | M07及B01/B02/B03通过 |
| A12 iOS、Android分别 | 流式/文本队列/停止 | 单一流；附件不排队；Stop仅受理，history真实终态决定显示 | 丢响应/断流技术合同，后正常真机业务 | 合格runtime与现有持久化合同 |
| A13 iOS、Android分别 | 断网与发送未知 | 本地已有内容保留；联网操作失败明确，无自动重发 | 飞行模式/网络切换、任务与记录对照 | M07、自有测试记录 |
| A14 iOS、Android分别 | 后台/锁屏/前台 | 实际暂停/中断据实反馈，恢复先核对，无持续执行承诺 | 设备OS生命周期、模型连接与本机状态回执 | M06/M07；不新增常驻服务 |
| A15 iOS、Android分别 | kill/重开/缺JSONL | 内存丢失不冒充运行；缺原记录失败关闭，云历史可读范围分开 | 真机终止、自有记录移除故障注入单列技术验证 | 可删除测试账户目录，禁止操作用户现有workspace |
| A16 iOS、Android分别 | 换设备/重装 | 不自动改绑/建新会话，不承诺本机文件自动恢复 | 两设备或重新安装测试账户，查绑定与文件来源 | 明确可删除测试数据，后续授权 |
| A17 iOS、Android分别 | 附件导入/本地准备/发送 | 用户选择仅准备本地，云传输按实际请求许可，DTO路径合法 | picker取消/类型大小/云传输网络记录 | M06、非敏感附件及公开文件能力 |
| A18 iOS、Android分别 | 本机/云文件预览保存分享 | 来源区分、Thread归属正确、系统动作取消/失败反馈，临时副本清理 | 三个既有文件入口、两类路径及本地Blob边界 | M06、测试文件与目标应用 |
| A19 iOS、Android分别 | MCP/插件/Bash/Notion | 仅有资格的本地能力可用；缺失明确，不关闭sandbox伪通过 | 每工具实际协议/权限/副作用和恢复验收 | M04选择的可行runtime、最小允许能力 |
| A20 iOS、Android分别 | 资源/启动worker | 原算法/lease保持，本平台指标可追溯，无全局共享任务误领取 | 平台资源provider与组合入口合同检查 | M05/M06，清晰owner/capability |
| A21 iOS、Android分别 | 窄屏/键盘/返回/辅助功能 | 主操作可见、IME不误发、滚动独立、VoiceOver/TalkBack可达 | 真机软件/硬件键盘、旋转/分屏、文字缩放 | M06 |
| A22 Web | 共享代码回归 | 原Next/BFF登录、流/队列/Stop、文件、偏好和商业页正常 | 复用既有Chrome harness与公开入口 | 共享代码实现后，隔离fixture；当前不运行 |
| A23 iOS | 签名/归档/安装/TestFlight | Framework/Python/资源签名正确，版本/符号/hash可追溯 | Xcode/ASC/TestFlight真实回执 | M08、账号/profile、门槛关闭 |
| A24 Android | APK/AAB/ABI/16KB/安装 | appId/version/签名正确，所有so可加载，Play拆分包正常 | Gradle/apksigner/bundletool、16KB设备与Play测试轨道 | M08及合格ABI/密钥 |
| A25 iOS、Android分别 | 隐私/AI许可/删除/举报/权益 | 数据声明符合本地和公网行为，已有渠道闭环可用 | 应用操作/服务回执/材料审查 | M09；缺口不作为已实现 |
| A26 iOS、Android分别 | 上传未知/审核/正式发布/暂停/修复 | 查构建状态再重传；审核通过后按选定地区/轨道正式分发并留实际安装样本；暂停不降级旧包，修复号递增 | 受控测试分发、审核/正式发布及安装回执 | M11及后续发布授权 |

## 前轮与收敛前验证

以下回执来自范围收敛前代码。后续已删除的测试、脚本和界面按历史记录保留，收敛后结果另行追加。

| 实际命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `python - <<'PY'`（内联Markdown链接与行锚检查器） | 0 | 19份本轮修改的现行稿/索引，162个本地链接，64个行锚，错误0；历史快照保留原文并排除 |
| `cd frontend && node <<'NODE'`（Playwright+本机Chrome+本地Mermaid 11.17.2） | 0 | 共享架构、共享交互、iOS和Android共20张图，离线parse错误0 |
| `python - <<'PY'`（内联四行文件头与禁用术语检查器） | 0 | 7份移动现行稿、1560行，缺失文件头0，禁用术语错误0 |
| `git diff --check` | 0 | 无输出 |
| `cd frontend && corepack pnpm mobile:test` | 0 | 13项bridge、启动超时、transport、流、取消与校验单元通过 |
| `cd frontend && corepack pnpm mobile:typecheck` | 0 | 移动入口和协议TypeScript检查通过 |
| `cd frontend && node ../mobile/scripts/check-bridge-contract.mjs` | 0 | 共享response policy有效；TS/Python/Swift/Kotlin镜像与清单一致：13 methods、4 events、7 errors；payload schema仍列M05 |
| `cd frontend && corepack pnpm mobile:build`及`check-web-assets.mjs` | 0 | 由`_dream`生成13个清单文件并逐项校验SHA-256；生成资源无`files.svgbox.net`引用 |
| `cd frontend && corepack pnpm build` | 0 | Next 16.1.6生产构建完成；原Web动态路由继续保留 |
| `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/test_mobile_runtime.py -q` | 0 | 8项目标制品资格、能力门禁和失败关闭单元通过；未装配解释器、ASGI或CLI |
| `xcodebuild ... build`（generic iPhoneOS、禁用签名） | 0 | arm64 iPhoneOS技术构建`BUILD SUCCEEDED`，13个Web清单文件通过校验；未生成可安装签名制品，Xcode 16.4工具链未达到当前上传最低要求 |
| `xcodebuild ... test`（iOS 18.6 Simulator、禁用签名） | 0 | 9项Swift generation、资源路径、生命周期和能力门禁单元通过，`TEST SUCCEEDED` |
| `simctl install` + `simctl launch` + screenshot（iPhone 16 Pro Simulator） | 0 | 本地资源、WKWebView bridge和能力响应成功；页面进入真实unavailable能力状态；模拟器已终止并关机 |
| `mobile/ios/scripts/check-device-readiness.sh`（收敛前，已删除） | 2 | 一台物理iPhone已配对；Developer Mode关闭、DDI不可用、Team缺失、签名身份0、bundle ID占位；输出已脱敏 |
| `xcodebuild ... build`（generic iPhoneOS、常规签名） | 65 | provisioning阶段明确要求Development Team；未创建/导入证书或profile，未执行安装 |
| `cd mobile/android && sh scripts/check-toolchain.sh` | 1 | JDK 17.0.15可用；缺Gradle 9.6 bootstrap与Android SDK platform 36，未执行Gradle unit、assemble、APK或AAB |
| `python - <<'PY'`（移动边界静态检查） | 0 | 固定来源、私有Android service、iOS外链配置和Python边界共5项，错误0 |

文档与代码验证不能证明解释器/CLI/ABI、真实手机业务或真实模型。连接设备只完成只读资格预检；真机签名、安装、启动、测试分发、商店审核和正式发布均未执行。前稿历史回执不作为现行端侧运行证据。

## 本次收敛评审与验证

**收敛评审：最小iOS宿主通过。完整端侧Dream未完成。** 每个保留模块直接对应本地页面加载、桥接回复、来源/资源校验或失败重试。无调用方的Registry、iOS文件仓库、额外原生页面和设备预检框架已删除。Python/依赖制品、公开用户认证及Claude执行模型仍为独立实施依赖。

| 实际命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `cd frontend && corepack pnpm mobile:typecheck` | 0 | 移动入口和协议TypeScript检查通过 |
| `cd frontend && corepack pnpm mobile:test` | 0 | 12项bridge/transport单元通过；已删除通用timeout测试，保留AbortSignal清理 |
| `node mobile/scripts/check-bridge-contract.mjs` | 0 | 13 methods、4 events、7 errors保持一致，无共享timeout policy |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.6' -derivedDataPath /tmp/ink-memory-ios-scope-derived CODE_SIGNING_ALLOWED=NO test` | 0 | 7项Swift单元通过；13个Web资源清单校验通过；日志`/tmp/ink-memory-ios-scope-test.log` |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath /tmp/ink-memory-ios-device-impl-derived CODE_SIGNING_ALLOWED=NO build` | 0 | arm64 iPhoneOS无签名构建通过；日志`/tmp/ink-memory-ios-scope-device-build.log` |
| `xcrun simctl boot/bootstatus/install/launch/io screenshot/shutdown`（iPhone 16 Pro Simulator） | 0 | 本地WebView与bridge成功进入本机服务未接入提示；截图`/tmp/ink-memory-ios-scope-startup.png`；本轮启动的模拟器已关闭 |
| `plutil -lint mobile/ios/InkMemory/Info.plist mobile/ios/InkMemory.xcodeproj/project.pbxproj` | 0 | 两份工程配置有效；删除文件的Xcode引用为0 |
| `python3 - <<'PY'`（本轮Markdown/文件头/行锚/历史SHA检查） | 0 | 18份现行文档与目录合同，158个本地链接、65个行锚、2段历史原文SHA，错误0 |
| `cd frontend && node --input-type=module`（纯Node Mermaid） | 1 | 4图解析，6图缺DOMPurify浏览器上下文；记录为解析环境限制 |
| `cd frontend && node --input-type=module`（本机Chrome离线Mermaid） | 0 | 2份本次修改正式稿共10图全部解析通过；浏览器已关闭 |
| `git diff --check` | 0 | 空白检查通过 |

以上结果仅覆盖宿主、共享入口和文档。未执行手机安装、端侧Python、真实模型、账户业务、签名分发或商店发布。

## 2026-10-25 端侧Python实施

本节保留前序公共后端步骤及当时的设备状态；当前业务路由、签名、安装与真机执行结果见后续“完整后端装配与Xcode配置”。

**Optimized Prompt：** 在现有最小iOS宿主中嵌入真实CPython和Dream Python代码，先取得可复现的iPhoneOS/Simulator制品并启动真实后端入口、调用现有接口，再连接现有React。复用当前FastAPI/DTO/业务模块，逐项处理实际导入依赖；解释器探针与健康响应只计为技术步骤，完整Dream业务单独留验收证据。保持Admin公网独立与现有认证边界，不复制服务凭证、不调用真实模型、不修改数据库。仅新增这条运行链必需的启动代码与构建适配；设备或签名缺口继续推进独立工作并准确记录。禁止使用远程后端、模拟响应或固定available状态代替手机执行。本轮React接线以真实iPhone后端执行回执为前提。

**Optional Enhancers：** 取得真机执行回执后，按原接口接入React并覆盖一次实际业务读取及停止/重开。


### 交付与当前判定

**当前判定：iOS Python公共后端技术步骤通过；用户要求的物理iPhone运行待解除安装前提。完整Dream业务与React传输未完成。** 原生启动链为`EmbeddedDreamBackend` → `DreamPython` C API → `mobile_runtime.ios` → FastAPI → `routers.public`。本轮无通用框架、插件平台、远程执行或Admin改动。原生宿主在Python启动成功后载入已有React入口；React业务传输与工作区门禁继续关闭。

| 交付物 | 当前行为与证据 |
| --- | --- |
| [iOS解释器启动](../../mobile/ios/InkMemory/DreamPython.m#L14)与[串行执行器](../../mobile/ios/InkMemory/EmbeddedDreamBackend.swift#L7) | 嵌入真实CPython，配置bundle搜索路径与UTF-8，释放空闲GIL；无外部Python进程、TCP监听或服务端回退 |
| [实际后端入口](../../backend/mobile_runtime/ios.py#L42) | 启动真实FastAPI lifespan，通过同一个ASGI实例执行公共GET请求，返回实际响应；`businessReady=false` |
| [共享公共路由](../../backend/routers/public.py#L11) | 从原`server.py`抽取root、health、robots、sitemap、llms共5条路径；正常服务器继续挂载同一router，返回内容兼容 |
| [依赖清单](../../mobile/ios/python-dependencies.json)、[准备脚本](../../mobile/ios/scripts/prepare-python.py)与[资源脚本](../../mobile/ios/scripts/bundle-python.py) | CPython 3.13.17 b17、后端锁定FastAPI 0.123.4/Pydantic 2.12.5/pydantic-core 2.41.5；下载校验SHA-256；本地官方Rust与目标标准库匹配；arm64 iPhone与Simulator扩展分别编译，全部缓存位于忽略目录Python/ |
| [原生执行测试](../../mobile/ios/InkMemoryTests/EmbeddedDreamBackendTests.swift) | 实际目标解释器返回`platform=ios`及Simulator状态；健康/内容200、未知路由404、POST拒绝、重复启动成功 |

### 实际验证回执

命令均在仓库根目录执行，标注`cd backend`的命令在该目录执行。日志保留于本轮命名的`/tmp/ink-ios-python-*20261025*`路径。

| 实际命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `python3 mobile/ios/scripts/prepare-python.py` | 0 | 两个目标的pydantic-core 2.41.5 release编译完成；依赖校验完成。日志`/tmp/ink-ios-python-prepare-20261025.log` |
| `cd backend && .venv/bin/python -m pytest tests/test_public_router.py tests/test_mobile_runtime.py tests/test_seo_content.py -q` | 0 | 14项通过；公开响应兼容、实际ASGI与原有移动门禁/SEO回归。无业务服务或模型调用 |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination 'platform=iOS Simulator,id=DAA412BE-8C54-4180-972F-A51D23A39139' -derivedDataPath /tmp/ink-ios-python-20261025 ONLY_ACTIVE_ARCH=YES ARCHS=arm64 test` | 0 | 8项原生测试通过。日志`/tmp/ink-ios-python-tests-final-20261025.log`，实际回执`EMBEDDED_DREAM_PROOF platform=ios python=3.13.17 health=200 llms=200 missing=404 businessReady=false` |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath /tmp/ink-ios-python-device-20261025 CODE_SIGNING_ALLOWED=NO build` | 0 | 最终arm64 iPhoneOS构建通过，含真实Python及原生扩展。日志`/tmp/ink-ios-python-device-build-final-20261025.log`；未签名、未安装到手机 |
| `python3 - <<'PY'`（应用资源与Mach-O检查） | 0 | 70个framework；CPython与pydantic-core均为IOS目标；`.env*`、未转换`.so`与`.pyc`均为0；Python与core许可证存在 |
| `codesign --verify --deep --strict /tmp/ink-ios-python-20261025/Build/Products/Debug-iphonesimulator/InkMemory.app` | 0 | 模拟器应用及嵌套framework签名校验通过；签名为模拟器ad-hoc，无证书创建或导入 |
| `xcrun simctl launch --terminate-running-process DAA412BE-8C54-4180-972F-A51D23A39139 com.inkmemory.mobile`及`simctl spawn ... log show --style compact --last 2m --predicate 'processID == 35097 AND category == "MobileHost"'` | 0 | 普通应用入口再次记录`Dream Python started version=3.13.17 platform=ios`；日志`/tmp/ink-ios-python-normal-launch-20261025.log`，无XCTest启动参数 |
| `xcrun devicectl list devices --json-output /tmp/ink-ios-20261025-devices-final.json`与`security find-identity -v -p codesigning` | 0 | iPhone 16/iOS 18.0.1已配对；Developer Mode disabled、DDI false；valid identities为0。工程未配置Team；标识符未写入文档 |
| `cd frontend && node --input-type=module`（本机Chrome离线Mermaid parse） | 0 | 两份本轮修改正式稿共11图解析通过；浏览器已关闭 |
| `python3 - <<'PY'`（Markdown清单、文件头、引用与行锚检查） | 0 | 27份现行文档，179个本地链接、69个行锚，错误0；历史快照保留原文 |
| `plutil -lint mobile/ios/InkMemory/Info.plist mobile/ios/InkMemory.xcodeproj/project.pbxproj`、`git diff --check`、`node mobile/scripts/check-bridge-contract.mjs` | 0 | 工程配置和空白检查通过；协议保持13 methods、4 events、7 errors |
| `xcrun simctl terminate/shutdown/delete DAA412BE-8C54-4180-972F-A51D23A39139`（三个独立命令） | 0 | 只清理本轮创建的InkDreamPython-20261025模拟器；构建制品、日志和执行回执保留 |

前置失败与修复：首次pytest从仓库根运行因tests导入路径退出4，切换backend目录后通过；首次Rust构建因Homebrew编译器与官方目标库元数据不匹配退出1，改为项目内匹配的官方编译器后通过；一次下载超时退出1，增加有界下载重试后通过；Xcode接入过程的C函数参数与待生成扩展导致构建退出65，修复调用并完成制品准备后两目标通过。

文档检查的前两次执行退出1：首版检查器贪婪匹配相邻链接且只读取前5000字符，修正检查器后定位`docs/deploy/.folder.md`缺三项文件头；补齐文件头后通过。

### 剩余依赖与下一步

1. **物理设备执行**：在iPhone开启Developer Mode，并在Xcode提供可用开发Team/账号与签名配置。当前缺少这些事实，未执行真机签名或安装；连接与配对证据单独保留。
2. **完整Dream业务**：本轮运行公共后端切片。原`server.py`完整组合仍依赖Admin service identity、服务级客户端和Claude CLI；不得把机密放入应用。后续按既有公开用户接口与实际模块覆盖继续装配。现有CLI子进程执行边界保持关闭。
3. **React接线顺序**：先取得物理iPhone后端启动与请求回执，再接入当前React；`runtime.request`、流式读取、停止和认证仍待实现，未开放工作区。
4. **分发前制品事项**：CPython发布包的`VERSIONS`和实际解释器为3.13.17，framework Info.plist报告3.13.16，记录为上游元数据差异；分发前核对并统一framework元数据。pydantic-core Rust传递依赖的完整许可证清单待补齐。当前Xcode 16.4用于本机技术验证；商店工具链、测试分发和正式发布保持后续任务。

官方资料于2026-10-25查阅：[CPython 3.13 iOS嵌入与扩展包装](https://docs.python.org/3.13/using/ios.html)、[BeeWare Python Apple support b17发布资产](https://github.com/beeware/Python-Apple-support/releases/expanded_assets/3.13-b17)、[pydantic-core 2.41.5源码配置](https://github.com/pydantic/pydantic-core/blob/v2.41.5/Cargo.toml)、[PyO3交叉编译](https://pyo3.rs/v0.26.0/building-and-distribution.html#cross-compiling)、[Apple Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)。本轮无真实账户业务、模型调用、数据库操作、商店提交或正式发布。


## 2026-10-25 完整后端装配与Xcode配置

**Optimized Prompt：** 在已验证的内嵌CPython/FastAPI基础上继续装配完整Dream后端，沿当前生产业务路由、认证、持久化、Agent/Claude执行和后台资源所有权核对实际导入、启动及请求依赖；优先修复可以在iOS进程内复用的模块，保留原公开入口、DTO、权限和失败恢复。实际执行现有业务代码并取得目标平台回执，公共健康接口回执单独记录。用户已授权操作Mac上的Xcode账号、Team与设备调试配置；使用已存在的用户账号完成开发设置，遇到Apple登录、双重认证或手机锁屏/重启确认时保留界面并明确必要用户操作。继续使用Swift/WKWebView与端侧Dream Python；Admin维持公网独立，不修改Admin、不复制服务凭证，不用远程Dream代理、虚构成功、替代CLI或关闭权限检查解锁完整业务。沿实际依赖处理可执行工作；iOS平台不支持的进程模型与现有授权协议缺口须通过代码和官方依据说明。保留其他未提交改动，仅做必要实现与对应文档、测试，不扩展框架。未获新增真实模型/业务写入或发布授权，本轮保持技术验证。最终交付代码、实际命令与退出码、完整业务未完成项及真机配置状态。

**Optional Enhancers：** 在开发签名与设备准备完成后，先安装并执行现有原生后端测试，再按同一路径验证可装配的业务路由；完整模型业务验收单独保留授权与账户前提。


### 本轮结果与实现评审

**当前判定：iPhone业务路由技术验证通过；完整Dream后端继续待满足明确前提后通过。** Developer Mode已启用、DDI可用，Xcode已登录用户Apple Account，应用与测试Target均配置同一个Personal Team和自动签名。签名、安装、开发者信任后的启动及原生测试均取得实际设备回执。正式发布与完整账户/Agent验收继续独立记录。

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 业务执行覆盖 | 前轮仅挂载公共router | 复用11个原有业务模块，连同公共router共66项注册；保留原DTO与依赖 | 真机配置读取200，受保护读写401，原生8项通过 | 账户授权后的真实读写与Agent执行 |
| 导入依赖 | Kit根包和server根包导入协议时连带初始化Runner；refs DTO连带导入插件执行器 | 保留导出名称/对象并按访问加载；refs/defaults在实际验证时加载执行器 | 原消息/协议与业务router独立加载；原验证顺序保持；127项回归通过 | 完整服务器与真实模型验收 |
| 本地请求 | 前轮GET/HEAD限制仅用于公共入口 | 复用共享transportPolicy，校验method、相对路径、query、headers、bodyBase64与已有字节限制 | POST真实进入原鉴权边界；拒绝服务凭证、用户覆盖header及非法输入 | pull stream、取消、二进制响应及React调用接线 |
| 签名配置 | 初始账号/Team/身份缺失；钥匙串逐次询问 | 用户直接完成Apple登录；应用与测试Target选择Personal Team；确认单一签名后串行构建 | 有效开发身份、匹配profile与真机安装；未导出私钥 | 正式发行账号、分发证书与商店条件 |
| 真机启动 | 首次启动因开发者证书信任被拒绝 | 检查deep signature、Team、App ID、debug entitlement和设备profile归属；设备完成信任后重试已安装制品 | devicectl启动0；test-without-building退出0，8项通过 | 完整业务资格 |
| 完整数据链 | 当前AdminDataClient每次请求取得service token，用户请求还添加服务身份header | 保留原认证；公开配置可读，保护接口缺用户授权维持401；应用不携带服务机密 | 未伪造用户或绕过服务身份；Admin仅只读源码核对 | 可发行到设备的用户数据协议、公开client注册及相应覆盖 |
| Claude执行 | 当前客户端构造ClaudeSDKClient并通过CLI子进程执行；手机Python标准subprocess无支持 | 保留原Runner和失败关闭状态，未替换为远程Dream或模拟输出 | 业务路由的运行资格与Agent资格分开 | iOS进程内兼容执行/传输实现及完整工具、恢复、停止验收 |

代码证据：[iOS路由组合与请求入口](../../backend/mobile_runtime/ios.py#L18)、[Kit按访问导出](../../backend/libs/claude_agent_kit/__init__.py#L60)、[server按访问导出](../../backend/libs/claude_agent_kit/server/__init__.py#L14)、[refs校验](../../backend/services/admin_data/deck_refs_data.py#L165)、[原ClaudeSDKClient构造](../../backend/libs/claude_agent_kit/server/simple_cas_client.py#L106)。

数据协议证据：[AdminDataClient](../../backend/services/admin_data/client.py#L78)每次请求调用服务token provider；[AdminDataConfig](../../backend/services/admin_data/config.py#L68)保留必需服务机密。[Admin只读源码requireDreamService](../../../ink-admin-memory/app/lib/auth/serviceIdentity.ts#L14)校验服务client、subject与scope，用户令牌单独提交无法提供服务身份。本轮未修改Admin。官方兼容性依据于2026-10-25查阅：[Python subprocess移动平台限制](https://docs.python.org/3.13/library/subprocess.html)、[Claude Code系统要求](https://code.claude.com/docs/en/setup#system-requirements)。当前进程模型需要移植工作；内嵌解释器和开发签名分别提供Python执行与设备安装条件。

### 本轮实际命令与回执

命令中的`$IOS_UDID`与`$CORE_DEVICE_ID`来自devicectl JSON的已配对iPhone，不在文档记录设备标识。执行使用subprocess参数数组传递实际值，日志位于本轮命名的/tmp路径。

| 实际命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `python3 mobile/ios/scripts/prepare-python.py` | 0 | 补齐uv.lock中httpx/httpcore/h11/certifi/PyJWT精确wheel与hash；已准备双目标Python及扩展 |
| `cd backend && .venv/bin/python -m pytest tests/test_public_router.py tests/test_deck_defaults.py tests/test_admin_deck_default_routes.py tests/test_admin_deck_refs_routes.py tests/test_sessions_router.py tests/test_admin_preferences_routes.py tests/test_mobile_runtime.py -q` | 0 | 127项通过，日志`/tmp/ink-ios-business-pytest-final-20261025.log` |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination 'platform=iOS Simulator,id=0B064A4E-9F00-4EA9-B27B-14787B3EEF58' -derivedDataPath /tmp/ink-ios-business-20261025 ONLY_ACTIVE_ARCH=YES ARCHS=arm64 test` | 0 | 8项原生测试通过，含11个业务模块、原始角色内容、GET/POST鉴权与服务header拒绝；日志`/tmp/ink-ios-business-sim-test-final-20261025.log` |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination "platform=iOS,id=$IOS_UDID" -derivedDataPath /tmp/ink-ios-business-device-20261025 -resultBundlePath /tmp/ink-ios-business-device-tests-final-20261025.xcresult -jobs 1 -allowProvisioningUpdates -allowProvisioningDeviceRegistration test` | 65 | 构建/签名/安装完成；启动因设备开发者证书信任被拒绝。日志`/tmp/ink-ios-business-device-test-final-20261025.log` |
| `codesign --verify --deep --strict /tmp/ink-ios-business-device-20261025/Build/Products/Debug-iphoneos/InkMemory.app`与Python profile/entitlement核对 | 0 | deep signature有效；Team与application identifier匹配；当前手机在ProvisionedDevices中；get-task-allow=true |
| `xcrun devicectl device info apps --device "$CORE_DEVICE_ID" --bundle-id com.inkmemory.mobile --json-output /tmp/ink-ios-business-installed-apps-20261025.json` | 0 | 真机已有1个匹配应用 |
| `xcrun devicectl device process launch --device "$CORE_DEVICE_ID" --timeout 20 --json-output /tmp/ink-ios-business-launch-20261025.json com.inkmemory.mobile` | 0 | 设备完成开发者信任后，已安装应用启动成功 |
| `xcodebuild -project mobile/ios/InkMemory.xcodeproj -scheme InkMemory -configuration Debug -destination "platform=iOS,id=$IOS_UDID" -derivedDataPath /tmp/ink-ios-business-device-20261025 -resultBundlePath /tmp/ink-ios-business-device-execution-20261025.xcresult -jobs 1 test-without-building` | 0 | 物理iPhone 16/iOS 18.0.1：8项全部通过；`simulator=false`由原生条件编译分支断言，Python实际报告`platform=ios`及3.13.17。日志`/tmp/ink-ios-business-device-execution-20261025.log` |
| `cd frontend && corepack pnpm mobile:test`与`node mobile/scripts/check-bridge-contract.mjs` | 0 | 12项桥接/传输回归通过；13 methods、4 events、7 errors保持一致 |

真机原始测试回执：`EMBEDDED_DREAM_PROOF platform=ios python=3.13.17 businessModules=11 defaults=200 protectedReadWrite=401 missing=404 businessReady=false`。配置读取执行的是现有业务代码；401记录鉴权保护，未完成用户数据读写。未调用真实模型，未修改业务数据库或历史内容，未提交商店或发布。

前置失败与修复：defaults延迟导入首次移除旧class导出造成4项失败/20项错误，保留原导出后通过；模拟器首次缺少Story contracts与JSON合同资源而退出65，补齐真实导入依赖后通过；首次并行开发签名遇到errSecInternalComponent退出65，单一开发签名校验成功后改用-jobs 1；第一次单framework校验指向尚未复制的Python.framework而退出1，改为自有临时制品副本后签名退出0。未通过修改钥匙串全局安全设置或导出私钥处理授权。

### 设备配置操作记录

- Xcode：Settings → Accounts → Add Apple Account。用户在Apple界面输入账号并完成认证；Personal Team出现后，在应用与测试Target的Signing & Capabilities选择该Team，保留Automatically manage signing。身份与profile由Xcode自动管理，本轮使用本机开发签名。
- iPhone：设置 → 隐私与安全性 → 开发者模式，按提示重启、解锁并确认。当前devicectl报告enabled及DDI可用。
- 钥匙串：codesign使用开发私钥时触发系统授权；“允许”针对单次访问，“始终允许”保存该应用对该条目的授权。密码仅输入系统界面，本轮未读取或保存密码。官方说明：[Apple钥匙串访问提示](https://support.apple.com/guide/keychain-access/if-youre-asked-for-access-to-your-keychain-kyca1243/mac)。
- 设备开发者信任：设置 → 通用 → VPN与设备管理 → 开发者App，按系统提示信任本次签名账号的开发者条目；之后真实应用启动与测试通过。
- Xcode用户界面状态与Python下载/编译缓存加入Git忽略范围；开发App保留在手机，真机测试回执与构建制品留存。Personal Team开发安装与正式发行资质分别核对：[Apple项目说明](https://developer.apple.com/help/account/membership/programs-overview/)。


文档与工程复核：`python3 - <<'PY'`（Markdown清单、路径、行锚及文件头）退出0：31份现行文档、189个本地链接、77个行锚，错误0；`cd frontend && node --input-type=module`（本机Chrome离线Mermaid parse）退出0：两份正式稿共11图通过，浏览器已关闭；`plutil -lint mobile/ios/InkMemory/Info.plist mobile/ios/InkMemory.xcodeproj/project.pbxproj`与`git diff --check`退出0。Xcode保存工程时移除自定义注释，配置完成后已恢复工程文件头。只关闭并删除本轮InkDreamBusiness-20261025模拟器，保留手机应用和真机回执。以上文档检查与127项provider-free后端回归分别记账；物理iPhone的8项测试覆盖实际解释器/业务配置/鉴权边界，真实账户读写及模型验收继续未完成。

<!-- original:end docs/exec/mobile-app-design-review-20261024.md -->
