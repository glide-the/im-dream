<!-- [Sync] 2026-10-29: 登记资源内容与安全响应头源码候选；当前普通App制品保持，完整设置采用继续实施。 -->
<!-- [Sync] 2026-10-29: 回顾源码Next构建与原运行候选分列，普通App更多/回顾采用继续实施。 -->
<!-- [Sync] 2026-10-29: Work插件源码的Next构建与当前普通候选分列，原生页面采用/真实安装继续验收。 -->
<!-- [Sync] 2026-10-29: 区分设置分类源码的Web/Native技术回执与仍在运行的旧More候选，目标采用和发布继续单列。 -->
<!-- [Sync] 2026-10-29: iOS显示偏好阶段Web构建与组件资格分列，普通安装候选及完整导航采用保持独立。 -->
<!-- [Sync] 2026-10-29: 区分当前模型候选与窄屏更多源修订，普通原生目标页导航继续未采用。 -->
<!-- [Sync] 2026-10-29: 原生Deck维护候选已装配/签名/安装，Web25与Native17技术及实际只读XCTest分项登记，主包与正式发布保持。 -->
<!-- [Sync] 2026-10-29: 再次复核源env、运行候选包内env、原登录action及App到本机3000的实际连接；历史主包配置单独标注。 -->
<!-- [Sync] 2026-10-29: 当前Mac与Simulator连接本机Admin/Gateway 3000；公网部署回执保留历史范围，认证身份沿用本机Admin声明值。 -->
<!-- [Sync] 2026-10-27: RN框架目标保持，按原生与网页区域减少迁移范围。 -->
<!-- [Sync] 2026-10-27: 现行跨平台设计引用更新为docs/design/multi-platform/。 -->
<!-- [Sync] 2026-10-26: Simulator原Dream产物、索引及ACK已有真实回执；iPhone新包无线安装成功，启动被锁屏拒绝，发行资格保持。 -->
<!-- [Sync] 2026-10-26: 端侧统一复用普通env关闭Claude命令沙箱；配置规则与业务验证记录分节，取消新增隔离适配。 -->
<!-- [Sync] 2026-10-26: 原确认恢复候选通过77项无模型测试及Simulator构建，包内原源摘要匹配；实际续接继续验收。 -->
<!-- [Sync] 2026-10-26: 原Admin同Run上下文读取兼容已采用，原确认派发与完整业务继续单独验收。 -->
<!-- [Sync] 2026-10-26: 前后台专项保留首次命令143与原重试后完成回执，调用数超限及原因继续诊断。 -->
<!-- [Sync] 2026-10-26: Simulator原Chat长Bash、三类授权续期、普通重开、运行中停止与同Session恢复取得回执。 -->
<!-- [Sync] 2026-10-26: Simulator原Dream创建、审核保存及EP01阅读取得回执，续接受现有Admin授权合同阻断。 -->
<!-- [Sync] 2026-10-26: 端侧资源补齐已声明内置插件的不可变制品，原CLI校验及完整Dream消费者链继续验收。 -->
<!-- [Sync] 2026-10-26: 记录Simulator真实Bash及双目标SDK/Runner技术回执，真机网页登录业务继续待验收。 -->
<!-- [Sync] 2026-10-26: 确认双平台沿用AutoDL关闭命令沙箱的部署配置，取消新增沙箱适配前置项。 -->
<!-- [Sync] 2026-10-25: iOS原SDK Bash/停止/恢复及原Runner技术通过，真机独立构建成功；真实工具业务继续验收。 -->
<!-- [Sync] 2026-10-25: 同步原Session真实追问、普通重开与页面结束反馈间歇失败，发行资格保持。 -->
<!-- [Sync] 2026-10-25: 本机构建保留原前端与后端env文件及配置消费者。 -->
<!-- [Sync] 2026-10-25: 记录普通env本机装配；外部分发前保留凭证范围评审和完整业务门槛。 -->
<!-- [Sync] 2026-10-25: 增加Node24原Runtime独立Simulator回执与制品来源，发行资格保持未通过。 -->
<!-- [Input] 现有Next/React/Python代码、原网页登录合同、双原生宿主与只读参考项目。 -->
<!-- [Output] 保持业务的打包判断、平台发行、账号/制品条件和验证阻断。 -->
<!-- [Sync] 2026-10-25: 随包原Next standalone、原public/static与Uvicorn/h11接线，保留原授权失败。 -->
<!-- [Pos] iOS/Android技术打包发布设计；当前业务行为由原模块所有。 -->
<!-- [Sync] 2026-10-25: 记录公网Admin拓扑、Simulator业务验收与更新后的开发签名IPA。 -->
<!-- [Sync] 2026-10-25: 记录iOS Simulator安装包宿主的正常登录与真实业务回执。 -->
<!-- [Sync] 2026-10-25: 记录iOS开发签名app/IPA与业务测试包，保持真机业务验收和正式发行门槛。 -->
<!-- [Sync] 2026-10-25: 删除移动专属认证、替代Agent、文件和任务业务变更方案。 -->

<!-- [Sync] 2026-10-27: RN原生界面与HTTP目标独立标注；旧包回执保留原范围，工作台创建退出移动适配。 -->

# Ink & Memory 移动打包与发布

<!-- [Sync] 2026-10-30: iPhone 实机操作采用现行 frontend/ios 工程，临时包回执归操作手册。 -->
当前 iPhone 的打包、签名、安装与 TestFlight/App Store 操作见[实机操作手册](ios-iphone-install-release.md)。本稿保留跨端发布设计及各阶段历史回执。

## 2026-10-27现行发布工程

统一源码与依赖归`frontend/`；RN主界面、RNW及平台文件的现行合同见[统一工程设计](../design/multi-platform/react-native-web-project-structure.md)。主构建入口为`pnpm --dir frontend native:bundle:ios`及`frontend/ios/scripts/build-rn-ios.sh`，iOS归`frontend/ios/InkMemory.xcworkspace`，Android归`frontend/android/`的RN Gradle构建。根mobile工程与旧HTML资源构建退出发布链。

签名、证书、隐私、账户、渠道及原后端运行库约束继续有效。以下旧WebView制品、命令与回执归历史范围，新RN界面按登录、真实任务、停止、恢复、附件、升级与Web回归分别验收；当前完整发行资格保持未通过。

### 当前本机Admin连接

当前安装候选补充记录（2026-10-29模型阶段）：`com.inkmemory.uiparity`由App25143在Simulator运行，Hermes摘要`2c9d8c80f83638c42d1a103a039948e48325c1af11e861541b212258c5cec7f9`，Next BUILD_ID `f8FBAb9DVLSobcCS7EGKx`，普通env继续本机3000；用户主包保持。随后窄屏更多修订的Web源码先构建为`YA79pOgTZixmn3p_Som9V`，浏览器历史关闭的最终构建为`wN5_RQQz7c9NjJIIjk-QG`；技术检查按各自制品记录，尚未采用到该安装候选。原生五项菜单组件通过呈现/回调检查，Writing/Timeline/Analysis、主题及完整设置目标接线继续实施，当前候选的More正文退出最终交付验收依据。详见[窄屏纠偏执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-29窄屏更多导航纠偏)。

2026-10-29按用户要求，当前Mac与iOS Simulator使用现有普通env：`INK_ADMIN_DREAM_TRANSPORT_BASE_URL=http://localhost:3000`、Backend `INK_GATEWAY_BASE_URL=http://localhost:3000`。`INK_ADMIN_DREAM_BASE_URL`和`INK_ADMIN_AUTH_ISSUER`沿用本机Admin声明的认证身份，实际Token、JWKS及业务数据请求使用现有transport。App Client ID、PKCE、Cookie、CSRF、权限和正常网页登录保持。

本机Admin登录页返回200。恢复后的普通RN候选在App进程内监听5173，原`GET /auth/options`返回`http://localhost:3000/auth/dream/password`及`http://localhost:3000/auth/dream/google`；App会话resolve返回200，进程TCP连接终点为本机`[::1]:3000`。Google后续第三方授权及回跳退出本次只读连接检查。物理iPhone的localhost指向手机自身；后续真机联调需使用可达同一本机Admin的有效服务地址并核对原授权来源配置。当前回执覆盖Simulator，完整发行资格继续按原矩阵验收。

普通候选、源env和后续资源装配使用同一配置归属；本次复核未修改Admin代码、账户、数据库或业务接口。命令与范围见[本机连接复核](../exec/mobile-app-design-review-20261024.md#2026-10-29历史生命周期资格与本机admin连接复核)。

本次再次检查：正在运行的`com.inkmemory.uiparity`普通RN候选，包内`app/.env`与Next旁的`.env.local`均采用本机3000；原`/auth/options`两个action返回本机地址，App PID73061到`[::1]:3000`存在已建立连接。历史主包`com.inkmemory.mobile`仍携带旧公网配置，当前检查覆盖正在运行的候选，主包覆盖安装继续随完整交付执行。初次Python默认代理请求返回502/403；显式禁用loopback请求代理后，两项原GET返回200。该代理诊断与App实际连接分别记录，详见[重复连接检查回执](../exec/mobile-app-design-review-20261024.md#2026-10-29再次核对本机3000与原生详情滚动)。

2026-10-29后续RN候选补齐原Deck首页/预览、Chat选择与草稿预填，普通栏目切换保留输入；首次非空稿触发的Tiptap已销毁实例异常已修复。Web类型、无凭证生产构建和25项技术回归通过，Simulator实际目录/预填及草稿操作取得回执。该阶段复用原Native运行库，按原脚本装配新Next资源及普通env；签名与安装面向独立候选，主App、真机、升级、商店及完整页面继续按原矩阵验收。详见[原生Deck与输入修复记录](../exec/mobile-app-design-review-20261024.md#2026-10-29原生deck首页预览与首次预填修复)。

2026-10-29原生Deck维护候选继续复用原Native运行库，新增原Work、字段/Agent、插件引用及内容版本呈现；本机3000普通env保持。Web/共享25项、Native维护/启动17项技术通过，实际Simulator维护导航与预览滚动两个XCTest用例分别通过，软件键盘只读检查已有回执。真实保存/提交、主包覆盖、真机、升级和商店发布继续按原矩阵验收，详见[维护阶段回执](../exec/mobile-app-design-review-20261024.md#2026-10-29原生deck维护与内容版本交付阶段)。

### iOS显示偏好适配阶段

2026-10-29，Web优先门禁取得同一生产构建kFFJidERge-ryI5LACTiO及35项回归。原生主题、原常规字段与更多组件取得17项fixture及类型/原UI检查；真实目标构建与安装采用分别记录。iOS复用已安装React-RCTSettings 0.81.5，新增依赖和原生桥接模块为0。普通安装候选保持上一模型阶段；General组件、完整设置分类及Writing/Timeline/Analysis接线继续实施，当前产物退出完整原生更多交付依据。源码、失败修订、制品与剩余前提见[本阶段执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-29原生主题与常规设置适配)。

本阶段目标编译补充：独立derivedData因磁盘耗尽退出65，复用本任务UIParity后xcodebuild与Metro均退出0；签名关闭，未安装或启动新App。source map已选择iOS偏好适配，General与五项More组件尚未进入普通主入口。该编译输出退出完整原生菜单与业务验收依据。

磁盘故障后的现用服务于同一数据目录恢复，PostgreSQL59828、Admin59853、App25143分别持有54329、3000、5173。数据库目录身份和控制文件头标识匹配，WAL回放完成，Admin原Build ID保持；登录页和App登录选项均200。未改Admin源码/env、账号、权限或schema，原阶段PID仅作历史回执。构建前空间预算、失败、缓存清理与恢复步骤归本阶段执行记录。当前约4.8GiB空闲仅记录本次状态，后续构建按实际峰值预算核对。

## 原发布判断与既有运行库记录

前端取舍：RN为统一App框架，Swift/Kotlin代码作为平台适配复用；业务视图按[RN内的区域取舍](../design/multi-platform/frontend-reuse-tradeoffs.md)渐进迁移。RN入口与端侧运行库共存为安装包验证项，原生区域和保留网页分别取得业务回执。

2026-10-27目标采用RN原生界面，通过App内HTTP访问原BFF和端侧Python，App级模块管理运行时生命周期。见[运行时架构](../design/multi-platform/mobile-runtime-architecture.md#react-native目标架构2026-10-27)与[RN交互稿](../design/multi-platform/mobile-react-native-interaction.md)。工作台创建和审核确认退出移动展示与适配。RN构建与业务回执均待实施；下文WebView包和业务回执保留原范围。原账号、签名、制品、渠道及关闭Claude命令沙箱要求继续有效。

## 路线判断

选定Swift/WKWebView、Kotlin/Android WebView与端侧Dream Python，复用现有React、Next BFF和业务代码，公网Admin/Gateway提供现有账户、数据与模型入口。2026-10-26关闭Mac relay的Simulator已完成原Dream创建、审核确认、四份Episode产物、故事索引及确认ACK；原完成回复、Session、持久化和4次确认阶段请求结算均已核对，后置同步恢复零新增模型。原Chat长Bash、运行中停止及同Session恢复保留独立真实回执。iPhone新开发包已签名构建和Wi-Fi覆盖安装，启动被设备锁屏拒绝，真机账户业务继续待验收。Android、第三方工具覆盖、Google平台回调及渠道资格沿原计划验收；完整移动发行资格维持未通过。

[PRD](../prd/dream-workspace/mobile-app.md)、[架构](../design/multi-platform/mobile-runtime-architecture.md)、[共享交互](../design/multi-platform/mobile-app-interaction.md)、[iOS](../design/multi-platform/mobile-ios-interaction.md)、[Android](../design/multi-platform/mobile-android-interaction.md)和[复审记录](../exec/mobile-app-design-review-20261024.md#2026-10-25-保留网页业务的设计复审与实现修正)承载现行范围。原历史快照保留原文，退出实现依据。

## 发现与问题定义

| 当前事实 | 证据 | 影响 |
| --- | --- | --- |
| Next 16.1.6 / React 19.1、动态Route Handlers与原BFF | [package](../../frontend/package.json)、[auth handlers](../../frontend/app/api/_auth/handlers.ts#L30)、[API Route](../../frontend/app/api/[[...path]]/route.ts) | 完整Next静态导出不可行；静态React资源无法执行原BFF |
| 原Dream登录使用网页form | [AuthEntry](../../frontend/app/_dream/components/Auth/AuthEntry.tsx#L43) | 容器必须支持原表单、导航、Cookie、callback；不改用设备码或原生登录 |
| 内部数据客户端同时要求用户和服务身份 | [client](../../backend/services/admin_data/client.py#L78)、[config](../../backend/services/admin_data/config.py#L68) | 开发包沿用普通env和原身份/用户授权校验，短期grant按原范围签发；外部分发凭证范围继续评审 |
| Python依赖原生扩展与后台组合 | [pyproject](../../backend/pyproject.toml)、[server](../../backend/server.py) | 逐项验证目标扩展；全局worker所有权保持原部署 |
| 原SDK与Runtime传输 | [simple_cas_client](../../backend/libs/claude_agent_kit/server/simple_cas_client.py#L115)、[iOS Transport](../../backend/mobile_runtime/ios_claude_transport.py#L143) | 服务器默认CLI子进程；iOS以同协议传输运行原Runtime Worker，Simulator真实Bash已执行，外部stdio工具逐项验收 |
| 原业务路由与执行模块 | [mobile_runtime.ios](../../backend/mobile_runtime/ios.py#L61)、[原路由清单](../../backend/routers/__init__.py#L6)、[原生测试](../../frontend/ios/InkMemoryTests/EmbeddedDreamBackendTests.swift) | 物理iPhone保留早期11模块执行回执；独立Simulator装配24模块并完成原Dream核心链路，真机完整业务继续验收 |
| 原视觉资源被移动构建额外替换 | [构建脚本](../../frontend/legacy/build-mobile-assets.mjs) | 本轮移除笔刷替换，原UI和来源URL继续复用 |

## Python 与 Claude CLI 官方兼容矩阵

| 项目 | 已核对依据 | 结论 |
| --- | --- | --- |
| CPython iOS嵌入 | [Python 3.13 iOS](https://docs.python.org/3.13/using/ios.html)，2026-10-25查阅 | Framework、扩展包装和签名有实际路径；完整Dream依赖另行验证 |
| iOS subprocess | [Python subprocess](https://docs.python.org/3.13/library/subprocess.html)，2026-10-25查阅 | 原CLI/stdio调用模型无法直接使用 |
| Claude Code平台 | [官方setup](https://code.claude.com/docs/en/setup#system-requirements)，2026-10-25查阅 | 官方支持平台无iOS/Android；fork须独立验证 |
| 项目当前发行目标 | [发布校验](../../scripts/verify_claude_registry_release.py#L50) | 仅darwin/linux的arm64/x64；iOS/Android制品缺失 |
| 本机已安装CLI | `file`与`xcrun vtool -show-build`实际读取 | Mach-O arm64、platform MACOS；root包0.1.12与平台包0.1.5存在版本不匹配；不作为手机运行时 |
| Node.js Mobile | [上游release](https://github.com/nodejs-mobile/nodejs-mobile/releases)、[维护者24.21.0-0制品](https://github.com/fogtape/nodejs-mobile/releases/tag/v24.21.0-0)、[API差异](https://code.janeasystems.com/nodejs-mobile/nodejs-apis-differences)，2026-10-25查阅 | 当前实现固定Node24.21.0-0库并校验SHA-256；同应用运行原Runtime JavaScript，排除桌面可执行文件；新增App内命令兼容候选，原SDK Bash/停止/恢复技术通过，完整工具及真机资格独立验证 |

Android Python嵌入需独立验证ABI、依赖、16 KB page size与原工具调用；iOS结果不替代Android回执。兼容缺口不授权替换Agent、权限、工具或恢复语义。

## 候选路线与收敛

| 路线 | 复用、服务端与维护影响 | 决策 |
| --- | --- | --- |
| 原生WebView宿主＋端侧Python | 复用React与Python；需原Next BFF接入、扩展和Claude兼容；两平台只维护薄宿主 | 用户选定路线；继续按原业务集成，阻断须实际解决 |
| WebView加载已部署完整Dream | 原网页/BFF复用高；业务和Python继续在部署主机执行 | 不满足端侧Python目标，退出本轮实现 |
| React Native等重写原页面 | React语法可复用，DOM/CSS/编辑器与原网页登录需改造；CLI问题仍存在 | 不新增第二套业务实现 |

Electron面向桌面运行时，无法由macOS制品生成iOS/Android包。Capacitor/Tauri可组织宿主，无法自动补齐原BFF、Python和CLI；当前已选轻量原生宿主，不增加框架依赖。PWA的Web分发无法证明端侧Python执行。

## 架构、网络和认证

共享页面、原BFF、端侧Python和平台宿主职责见[架构](../design/multi-platform/mobile-runtime-architecture.md#执行位置与代码归属)。移动构建只处理资源位置和hash；不复制BFF服务器秘密，不将原生账户令牌仓库或新Admin设备API作为发行路径。

包内页面与public资源沿原构建复用；原第三方图片来源继续按原实现联网读取。本轮不生成视觉替代资源，不声明全部页面内容可离线使用。

历史拓扑（2026-10-25）：Admin独立部署在`https://ink-admin.suoxya.com`，当时Dream BFF通过HTTPS backchannel访问公网Admin，原登录表单使用对应HTTPS action。2026-10-29当前Mac和Simulator采用上节本机3000传输；旧公网制品保持原记录。localhost Dream client、callback、Cookie/CSRF和OAuth目录继续执行原校验。

原网页邮箱/密码/注册/Google表单、会话失效、退出和取消保持原合同。bridge无`auth.*`或`auth.callback`。原文件上传、停止、队列、Run/Thread状态、持久化、资源策略和计费保持原实现。平台生命周期只通知页面，不新增后台落库、调度、自动续跑或业务终态。

## 平台打包发布路径

### 端侧Claude命令沙箱配置

部署决定（2026-10-26复核）：iOS和Android统一沿用AutoDL已有的关闭方式。端侧Dream进程使用现有普通backend env键，复用原配置解析和settings生成；新增Claude命令沙箱兼容层退出实施范围。

```dotenv
INK_AGENT_SANDBOX_ENABLED=false
```

该配置适用于iOS和Android端侧Dream后端。新增Claude沙箱后端、文件/网络/proc逐命令隔离及其等价性验证退出实施清单和发布前置项。原Python、Node、Claude和Bash的端侧执行兼容继续按运行要求验收；正常网页登录、业务权限和审批沿用现有实现。宿主在Dream初始化前提供普通env，页面不增加沙箱开关、管理入口或确认步骤。

当前AutoDL生成器在[`prepare-env.sh`](../../deploy/autodl-ssh/prepare-env.sh#L108)写入该值，[AutoDL部署说明](autodl.md#L59)记录使用条件。端侧复用同一[`resolve_sandbox_enabled`](../../backend/libs/claude_agent_kit/server/workspace.py#L202)，由既有settings生成逻辑输出以下四项；缺少或非法值沿用原默认启用行为，不修改全局默认值。

| 原Claude settings字段 | 端侧部署输出 |
| --- | --- |
| `sandbox.enabled` | `false` |
| `sandbox.failIfUnavailable` | `false` |
| `sandbox.autoAllowBashIfSandboxed` | `false` |
| `sandbox.allowUnsandboxedCommands` | `true` |

字段生成依据为[`workspace.py`](../../backend/libs/claude_agent_kit/server/workspace.py#L626)，已有[配置测试](../../backend/tests/test_claude_agent_workspace.py#L286)覆盖显式关闭和环境变量关闭；本轮仅核对源码，未重跑业务测试。宿主在SDK启动前向端侧Dream进程装配普通env，沿用原配置所有权，不新增部署环境名称分支、浏览器开关或第二套设置。

| 配置对象 | 定义 |
| --- | --- |
| default | 现有解析器在缺失、空值或非法值时返回`true`，保留全局默认 |
| desired | iOS和Android端侧部署明确提供`INK_AGENT_SANDBOX_ENABLED=false` |
| effective | 由端侧Dream进程读取值及原CLI settings确认；候选包与两平台分别留存回执 |
| revision | 现有env无动态revision；以源码SHA、客户端version/build及配置摘要追踪，不新增Admin配置模型 |

装配顺序为构建输入 → 包内普通env → Dream进程解析 → 原CLI settings。重新构建和启动后核对生效值，不新增应用内切换入口。

执行范围：

- 关闭Claude Bash额外的文件/网络命令沙箱，停止新增sandbox-runtime的iOS/Android后端、逐命令文件/网络/proc/进程隔离及其发布门禁。现有资格原型和失败回执保留为历史证据，不接入当前生产target。
- 保留端侧Python、Node、原Claude Runtime及Bash执行兼容。启动、argv/env/cwd、stdio、退出、停止、资源清理和恢复继续实现；关闭沙箱配置无法补齐这些运行能力。
- 保留iOS系统应用沙箱、Android应用UID及存储权限。批准的命令在Dream应用拥有的系统资源范围内执行；AutoDL的root进程身份不迁入移动端。iOS边界依据[Apple运行时安全](https://support.apple.com/en-nz/guide/security/sec15bfe098e/web)，2026-10-25查阅。
- 正常网页登录、账户、Workspace Mode、现有工具权限/审批、API鉴权、持久化、流式响应、Stop和计费保持。沿用原`can_use_tool`及Hook链路，不设置`bypassPermissions`或跳过工具审批。
- `sandbox_network_mode="disabled"`表达禁止网络访问；本次配置使用`INK_AGENT_SANDBOX_ENABLED=false`。保留已有网络业务设置，停止声明Claude沙箱代理的域名过滤与每命令文件/进程隔离。已批准Bash可接触App有权访问的文件和网络，任务间额外隔离不列入当前保证。
- MCP Apps的iframe/来源隔离与Claude命令沙箱分别配置，既有MCP Apps规则保持。`CLAUDE_CODE_TMPDIR`继续使用既定thread内精确`.claude-tmp`及0700，禁止扩大为整个`/tmp`。

实施顺序：普通env装配并核对四项CLI settings → 端侧原命令执行接线 → 模拟器原网页登录与真实工具任务、流式/Stop/持久化/重开 → 物理iPhone → 原渠道打包发布。Android独立取得对应执行与构建回执。

验收要求：两平台安装包实际读取同一env键；四项settings一致；Workspace Mode及高敏感工具审批保持；真实Bash完成自有工作区文件任务；Stop与恢复通过；无Mac业务进程或relay；原账户、文件、消息及结算可核对。配置中存在`false`只证明输入，完整业务以原入口回执验收。

当前状态：**设计已更新；iOS候选包已装配关闭值，Simulator完成一次原账户真实Bash任务；Simulator与物理iPhone原SDK/Runner技术验证通过；Android待接线**。iOS[Debug/Release配置](../../frontend/ios/InkMemory.xcodeproj/project.pbxproj#L342)和[资源脚本](../../frontend/ios/scripts/bundle-node.py#L59)将该值写入包内`app/.env`；源backend/frontend env保持。双目标原SDK通过Bash、共享文件、权限拒绝、MCP、连续容器恢复、流中断、运行中Bash停止及描述符清理；原Dream Runner通过。2026-10-26 Simulator实际Bash写入并读回自有临时记录，原页面终态、正常Admin消息与两次Gateway请求结算均取得回执。物理iPhone独立构建和安装执行技术用例通过；原网页进入Chat的只读验证超时，真实账户工具任务与发行继续待验收。完整工具和Dream Project/Episode流程分别保留验收项。实际命令与范围见[续作记录](../exec/mobile-app-design-review-20261024.md#2026-10-26-原会话恢复复验与完整业务核对)。原方案保存在[历史快照](../exec/history/mobile-sandbox-before-disabled-20261025.md)，逐命令沙箱隔离扩展保持停止。

### 既有业务接入验证记录

以下回执保留各阶段实际结果，后续修复与未完成项由对应执行记录维护。端侧命令沙箱关闭规则按上一节执行。

2026-10-26恢复候选补充：原`dream-files`读取在当前账户的Run及工作区校验后，读取同Thread已接受的原确认消息并交给既有精确claim协调器；终态Run及已ACK消息只读取。77项无模型测试与Simulator构建通过，包内三份生产Python源摘要匹配，relay地址为空。实际原账户续接、完整业务及物理iPhone继续验收，见[原确认的精确恢复记录](../exec/mobile-app-design-review-20261024.md#原确认消息的当前账户精确恢复)。关闭命令沙箱配置保持。

2026-10-26 05:40采用状态补充：公网Admin原生版本已包含原确认Run grant的workflow-context及deck-chat-context读取兼容；同Run校验、原grant来源/有效期及Thread/Deck/Voice归属保持。103项无模型边界测试和类型/定向lint通过，服务新构建就绪且直接/公网登录页200。原iOS Run仍confirmed、确认消息dispatching，重新进入可读取原EP01；旧确认派发恢复与完整业务继续待验收，详见[原确认续接记录](../exec/mobile-app-design-review-20261024.md#原确认续接的精确run上下文兼容)。端侧关闭命令沙箱配置保持。

2026-10-26当前业务回执：关闭relay的Simulator沿原网页登录创建Dream，端侧生成8份工作台文件，原页面显示2人物、1场景和EP01的3镜头，正常Admin保存回复并完成3次真实请求结算。更新重开保留工作区；原“确认并继续”已保存，Run为confirmed，原EP01 Artifact reader可读取相同storyboard摘要。续接在原worker准备阶段收到Admin的DELEGATION_ENTITY_DENIED，未新增模型请求；当前完整业务与真机发行验收保留未通过。部署配置继续关闭Claude命令沙箱；该授权依赖与沙箱配置分别处理，详见[当前执行回执](../exec/mobile-app-design-review-20261024.md#原确认提交及当前授权依赖)。

后续验证补充：2026-10-26物理iPhone原React启动与正常账户messages/status/inputs读取重试均退出0；原status为not_found，原inputs为local_owner=false，表明该物理进程当前未拥有该会话执行。Simulator插件资源候选包含8份已核对摘要的不可变artifact，原CLI校验6份通过、2份音乐插件frontmatter失败；剧本卡组需要的ink-dream-story和drama-forge通过。该候选的真实Dream随后在原ensure_plugin_venv调用subprocess时失败，Gateway请求0。后续固定Linux Python接线候选已通过Simulator原venv/pip、9项依赖导入及原dramaforge.py --help，模型调用0；完整业务、物理设备及正式发行继续按独立回执验收，新增命令沙箱继续停止。

2026-10-26长会话补充：关闭relay的Simulator沿原网页登录和原Thread执行一次只读Bash及170秒等待，原任务约201秒后达到流式终态；gateway-cli、server-persistence与editor-stdio各续期1次，正常Admin保存新助手消息并完成2次模型请求结算。原Session绑定、历史字节前缀、测试文件及精确临时目录规则保持。该目标测试退出0；此前间歇失败与Dream确认后的授权依赖分别保留，完整业务和真机资格继续待验收。命令、标识及回执见[原长任务记录](../exec/mobile-app-design-review-20261024.md#原长任务续期与持久化真实回执)。

同轮普通App另取得[Bash运行中停止及再次执行回执](../exec/mobile-app-design-review-20261024.md#原bash运行中停止与同session恢复)：原Stop使170秒等待命令在启动约20秒后写入中断结果，正常Admin保留cancelled部分消息；同Session后续无工具追问到达completed，页面结束生成，两次请求正常结算。原长任务普通重开后的回复可读。该结果覆盖本轮具体任务，完整Dream续接及物理设备继续按各自条件验收。

随后[前后台专项](../exec/mobile-app-design-review-20261024.md#前后台恢复诊断与有界验收)保留混合结果：首次sleep 45在60000毫秒超时配置下约95秒返回143，原Claude重试成功并保存completed回复。实际3次请求超过本阶段2次上限，人工Stop未在最终生成前受理；后台精确时长及首次143来源缺少对应诊断，专项验收保持未通过，后续先执行无模型诊断。宿主遵循[iOS生命周期](https://developer.apple.com/documentation/uikit/managing-your-app-s-life-cycle)及[有限后台执行规则](https://developer.apple.com/documentation/uikit/extending-your-app-s-background-execution-time)，2026-10-26查阅；当前不增加后台常驻、业务重放或超时扩展。

### iOS

- 插件资源由`bundle-python.py`从原配置的不可变artifact store装配，包含`PLATFORM_BUILTIN_SOURCES`内置包、已声明本地marketplace目录内源码插件的已准备制品及摘要manifest；源目录名称、canonical digest与复制结果逐项校验。远程来源及其他运行数据排除。手机启动复用原store导入，Admin冻结锁、Deck refs及原CLI兼容性决定加载版本。当前源码与已批准摘要存在差异时保留原不可变制品，插件许可及分发条件随发行材料核对。该准备步骤不新增Admin安装或发布操作；缺少必须内置制品时构建明确失败，卡组其它未准备依赖由原校验拒绝。
- 当前工程归属`frontend/ios/InkMemory.xcworkspace`及`InkMemory.xcodeproj`；Xcode编译RN宿主、CPython Framework、目标扩展、Node库及原Next standalone/React资源。当前deployment target为16.4，发布前核对全部依赖交集。
- 应用标识、version/build、Team和entitlements由工程/受控构建配置提供。当前本机Personal Team用于已连接iPhone开发安装，正式发行资格另行提供。
- 本机调试：开发签名 → 安装 → 正常应用启动 → Dream原网页登录和完整任务验证。证书/私钥继续由Xcode与Keychain管理，禁止写入仓库或产物资源。
- 历史开发制品（2026-10-25）：`mobile/ios/build/InkMemory-development-20261025.ipa`与`mobile/ios/build/SHA256SUMS`。制品使用当时开发profile，包内Dream Web上游为`192.168.0.103:5173`，Admin表单和BFF backchannel使用公网HTTPS；IPA不含测试bundle，ZIP、深层签名、登记设备和SHA-256已校验。该制品只用于当时已登记设备联调。
- 正式路径：合格工具链和发行账号 → Archive → 签名/entitlement/profile校验 → `.xcarchive`、dSYM、IPA留存 → App Store Connect/TestFlight → 测试通过 → 审核及选定地区发行。
- 待提供Apple Developer Program、发行Team/角色、App Store Connect记录、应用图标、必要分发证书/profile和商店材料。现有开发安装不表示具备这些条件。

### Android

- 工程归属`mobile/android/`；Gradle/Kotlin编译WebView宿主、目标Python/扩展与共享资源。当前工程minSdk29、compile/target36；构建前重核工具链兼容矩阵和发布时渠道要求。
- applicationId/versionName/versionCode由受控配置提供；versionCode递增。测试APK签名安装；Play使用签名AAB、upload key及Play App Signing，保留mapping/native symbols。
- 所需前提：合格Android SDK/Gradle/JDK、设备ABI/16 KB验证、受控签名密钥与恢复责任、Play账号和应用记录。当前缺少Android完整构建/真机回执。
- 发布地区和渠道尚未指定，工作假设为受控测试及后续Google Play。中国大陆或其他商店由明确渠道要求单独确定，不自动增加多渠道平台。

### 最小构建与制品流程

源码SHA和干净范围 → 锁定依赖/下载hash与许可 → iOS独立目录构建原Next standalone与React资源、Android沿用现有资源准备 → 平台编译 → 有界回归 → 受控签名 → 签名/标识/权限/ABI校验 → 安装验证 → 留存制品与回执 → 测试分发 → 审核/发布。

留存version/build、源码SHA、资源hash、CPython/扩展/CLI身份、工具链、签名公开指纹、构建日志、测试结果、符号和渠道构建ID。签名秘密位于Keychain/CI secret或受控keystore，不进入源码、bundle、日志或文件清单。CPython framework元数据差异及Rust传递许可清单属于发行前置项，详见原实施回执。

仅按实际构建需要组织脚本和CI，不新增应用内打包页面或发布中台。

## 更新与恢复

客户端、Web/BFF、Python与Admin按现有DTO/schema capability兼容；不按环境名选择另一套业务。升级保留平台允许保留的数据和原业务记录，不新增同步/迁移协议。

上传失败先查渠道构建状态，确认缺失后重传同一制品；签名/版本冲突按渠道要求修复新build。暂停发行只停止新增分发；已安装应用通过递增修复版本更新。服务端回退需兼容已安装客户端和原已发布schema，不通过回退恢复已撤销会话或修改历史结算。

## 商店和地区前提

| 适用事项 | 触发与当前依据 | 处理要求 |
| --- | --- | --- |
| 隐私声明和数据安全 | 原账户、正文、附件和模型请求 | 声明原数据处理及平台权限，核对第三方依赖 |
| Google等第三方登录 | 现有AuthEntry提供Google | 按发布渠道重核等效登录适用条件；缺口先评审，当前不新增登录业务 |
| 账户删除 | 原产品提供账户能力 | 核对现有可用闭环与渠道要求，缺口不得写成已实现 |
| 数字内容支付 | 仅在安装包实际提供购买时触发 | 核对既有权益入口和地区/渠道规则，不新增支付系统 |
| AI披露、内容政策和最小功能 | 原Chat/Dream模型内容和核心任务 | 核对原业务与平台材料；核心任务未运行时不提交可用性声明 |
| 本地网络/文件权限 | 实际连接Mac或使用原附件入口 | 仅按所需系统操作配置权限与用途；保留原业务行为 |

商店与工具链资料保留原2026-10-24查阅范围，实际发布前按当日官方资料重核：[Apple Review](https://developer.apple.com/app-store/review/guidelines/)、[Apple分发](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)、[Play目标API](https://developer.android.com/google/play/requirements/target-sdk)、[Android 16 KB](https://developer.android.com/guide/practices/page-sizes)。本次复审只修正业务边界，不构成渠道合规或发布验收。

### 参考能力映射

以下 `R` 表示上述参考根目录；文件和行号可直接定位。只借鉴流程、责任划分及制品追溯，复制具体源码或二进制需要独立授权核查。

| 参考模块或流程 | 当前作用 | 可借鉴内容 | 移动端适配要求 | 证据 |
| --- | --- | --- | --- | --- |
| package 与 runtime build | 重建工程包0.2.0，vendor目标Electron42.1.0；esbuild 编译 Main、CJS Preload、React Renderer，生成 ASAR | 入口清单、输入图、锁定版本、构建后来源摘要 | 平台宿主各自构建，排除 Electron/Preload/ASAR | `R/package.json:2–6,25–36,140–158`；`R/scripts/build-application-runtime.mjs:40–75,141–174` |
| macOS build/sign/verify | Darwin arm64 检查、外部输入 hash、`.app` 组装、ad-hoc 签名、Mach-O/ZIP 校验 | 构建前条件、签名后校验、产物摘要 | 替换为 Xcode 归档和 Gradle 制品；iOS 分发身份需重新登记 | `R/build-sign-verify-original-ui-macos-arm64.sh:36–67,77–109` |
| deliverables | Skeleton/Frameworks/ASAR 组合应用，输出源码包和 SHA256SUMS | 分开源码、应用、验证说明；留存摘要 | `.xcarchive`/符号/IPA 与 APK/AAB 独立管理 | `R/scripts/package-original-ui-deliverables.mjs:8–30,38–47` |
| CodexAppServerSidecar | 桌面启动 `codex app-server`，监听本机随机 WebSocket | 展示与执行模块所有权 | 当前Dream执行位置为服务器；本轮端侧Python/CLI资格按兼容矩阵核定 | `R/src/entries/main-runtime.ts:311–315`；`R/src/main/runtime/codex-app-server-sidecar.ts:95–108` |
| LocalNodePtyBackend | 本机 node-pty 启动 shell | 宿主接口隔离 | 不进入移动安装包 | `R/src/main/terminal/node-pty-backend.ts:59–77` |
| CodexMobilePage | 桌面手机连接引导、MFA 和客户端状态；文案要求手机在 ChatGPT 访问保持唤醒的 Mac | 取消、错误、重试及权限反馈方式 | Ink 使用既有公网账户与本机执行边界，配对协议无复用授权 | `R/src/renderer/mobile/codex-mobile-page.tsx:25–51` |
| mobile protocol/service | Electron IPC 调用 ChatGPT REST；本机 JSON 保存设置；开关仅读 clients 并写设置 | DTO、分页、鉴权失败与重试组织 | 不复制 OpenAI endpoint、token、业务常量 | `R/src/shared/mobile/codex-mobile-protocol.ts:38–65`；`R/src/main/mobile/codex-mobile-service.ts:55–67,166–219,231–249` |
| Sparkle updater / Windows policy | macOS 原生更新与 Windows Store 身份规则 | 版本、渠道身份、更新失败状态 | 由目标移动商店更新；不引入 Sparkle 或自下载原生更新 | `R/src/main/updater/desktop-updater-service.ts:134–220`；`R/src/main/automations/windows-store-updater-policy.ts:4–9,62–92` |
| vendor manifest | 原 DMG、ASAR、node-pty hash 与签名前后来源 | 每项二进制的来源、许可、平台和摘要 | 官方移动依赖独立清单 | `R/vendor/node-pty-electron42-darwin-arm64/VENDOR-MANIFEST.json:1–29` |

`MobileQrArtwork` 是 `<i>` 与按钮构成的示意图，未编码配对 URL（`R/src/renderer/mobile/codex-mobile-page.tsx:9–13`）；当前 Mobile 为 Partial，仍需第二设备实际批准（`R/docs/parity/Codex-Original-Feature-Inventory.md:51`）。文件扫描未发现 Xcode project、Podfile、Gradle、AndroidManifest、Capacitor、Expo 或 Flutter 工程标记，根包无移动打包命令。移动连接状态与独立移动工程分别记录。

#### 来源和分发条件

根包 `private: true`、README 声明证据重建且为非官方源码（`R/package.json:4–5`、`R/README.md:3`），扫描未发现覆盖根源码的 LICENSE/NOTICE。`R/resources/renderer/original-ui/README.md:3–7` 记录 CSS/字体从原 ASAR 提取，hash 仅证明来源。node-pty 的 MIT 许可要求保留声明（vendor 内 `node_modules/node-pty/LICENSE:1–19,23–43`），覆盖范围限定该组件。原始应用 Skeleton、Frameworks、Codex CLI、字体、商标及整套源码的复制分发授权仍待核验。

`R/scripts/materialize-node-pty-electron42-vendor.mjs:74–109` 的 vendor 目标固定 Electron42/Darwin/arm64；`R/scripts/build-application-runtime.mjs:113–133` 写入 OpenAI Sparkle feed、公钥和原版本。移动方案全部排除这些制品与发布身份；不从参考仓库复制文件。目标仓库自身字体、图标和前端依赖的分发许可仍需在首个构建前形成清单。

### 历史文档差异及影响

| 差异 | 当前依据 | 处理 |
| --- | --- | --- |
| 参考 README 停留 Round52 的 3/16/20 统计 | `R/package.json:134–139` 已有 Round84/85；功能清单 `:9–10` 为35 Implemented/4 Partial | 引用当前脚本，旧统计保留历史 |
| work 子树称无完整 APP、包版本0.1.0 | `R/work/semantic-recovery-restart/README.md:11–12` 对应 checkpoint；根工程已含应用组装 | 两个源码位置分别定位 |
| README-ZH 称 DMG 仅分析输入 | `R/README-ZH.md:64–65` 与 macOS 脚本 `:13,31,44,66,79` 强制 DMG 并抽取 node-pty 存在差异 | 不复用旧输入清单 |
| 参考连接、云任务和 SSH 的交付标题 | `R/docs/delivery/round-84-README.md:22,42` 未点击 Allow；round85 `:26` 云账户与完整链路受限 | 仅记录已观察局部能力 |
| Dream 历史 Vite/Cloud 发布说明 | [deploy/README](../../deploy/README.md#L25):25–30、[发布索引](README.md)已有漂移说明；[release-system-design](release-system-design.md)保留历史 | 当前方案采用 Next/pnpm，同源 BFF |
| docker-entrypoint 跨源注释和 desktop-only 文件头 | [docker-entrypoint](../../frontend/docker-entrypoint.sh#L10):10–20 与 apiBase 同源实现存在差异；[Layout](../../frontend/app/_dream/components/story-workspace/layout/StoryWorkspaceLayout.tsx#L2):2 与 responsive CSS 存在差异 | 本轮只登记，后续拥有对应代码的任务同步注释 |



### iOS原Web资源构建补充

`prepare-next.py`在忽略目录准备原Next源码和共享bridge合同，使用当前已安装依赖。原`frontend/.next`、用户Web服务及`.env`保持原状。原Next构建启用standalone后，`bundle-next.py`复制trace依赖、public和static，重定位包内依赖链接，排除桌面原生模块并记录摘要。原Next BFF在应用Node Worker中运行，原HTTP proxy通过Uvicorn/h11连接同一Dream ASGI实例。发布前须核对原Next/React及依赖许可、目标设备运行、Web来源/callback、合法原授权与完整业务。

早期无env包缺少原service secret与BFF Cookie配置，原认证入口返回503；该阶段回执保留。当前本机包按下节装配普通env，已通过原网页登录、独立真实模型回复、页面终态及正常Admin持久化与结算。此前开发IPA继续保留原Mac relay接线；本次独立Simulator测试不更新该IPA，不产生新发布记录。

iOS Xcode已移除重复静态资源phase，独立入口统一为包内原Next；资源打包只清理当前目标的旧`web/`生成物。原共享React源码与Android构建保持。


## 普通env本机调试产物

2026-10-25用户要求直接复用普通env。当前iOS本机资源阶段复制现有`backend/.env`到应用`app/.env`供Python读取，并复制现有`frontend/.env.local`到原Next server目录供Node读取；React业务源码、登录、权限与Admin代码保持。当前包包含原Dream服务身份与BFF配置，本机调试验收与外部分发资格分别核定。商店候选制品的凭证范围评审、账号业务、完整工具、真机、归档及渠道门槛继续保留；本轮未提交商店或执行正式发布。新回执见[普通env与原登录](../exec/mobile-app-design-review-20261024.md#普通env接线与原登录验收)。

历史核对：2026-10-25早期普通Simulator App的原`backend/.env`和`frontend/.env.local`各一份，与源文件逐字节一致，检查退出0。随后候选构建按本稿关闭配置，仅在包内backend env装配现有沙箱键；配置对照应分别核对该键及其余原值，前端env继续按原文件核对。独立App-hosted Bash原语资格通过；接入原SDK的Bash、停止和恢复技术用例通过。完整工具、物理设备、授权范围和渠道核验继续保留，正式开发IPA保持原历史制品。


### 2026-10-29设置分类源码与当前安装包

当前运行候选仍为com.inkmemory.uiparity、App25143及原f8FBAb9DVLSobcCS7EGKx Web制品；本阶段没有替换普通候选或主App。普通Native更多仍为旧Settings入口，五项菜单和完整目标页的采用继续实施。

新源码增加记忆回应、原只读订阅和关于内容；Web生产构建wO9zo_de9MpdulUAMS99U及完整47项技术回归通过，Native内容fixture15项、更多/外观13项通过。上述结果均按[执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-29原生设置分类交付阶段)分项登记，普通账户业务、iOS目标采用、真机、升级、签名与发布继续独立验收。

本阶段保留普通App-owned Next/Python/Node/Claude运行方式、本机Admin3000和正常网页登录。未启动Docker、替代Mac Dream执行端、随机端口Admin或第二套数据库，账号、权限、账本和历史正文保持本阶段范围之外。


设置分类阶段的普通App unsigned Simulator构建已通过，产物仍位于原UIParity目录。独立临时资格包验证真实Hermes/UUID/UserDefaults和合成保存回执后已卸载，原登录URL scheme未注册，证书/私钥/Team操作为0；普通候选继续PID25143及原f8制品。主App和运行候选8个文件摘要保持，正常App/本机Admin的直连公开读取均200。原生触控滚动、VoiceOver、完整更多目标、真机与正式发布保持各自验收状态。


### 2026-10-29Work插件源码与当前运行候选

本阶段源码新增原生Claude Code Plugins内容，复用原状态及HTTP；原生普通App入口保持，未替换安装包。独立Next生产构建为`_Sk2A9_lvjbyCh6zy3_mc`，普通运行候选仍沿上节原f8制品；本阶段原生Xcode构建、安装、证书和商店操作均为0。Web生产/平台fixture验证及剩余前提见[Work插件阶段记录](../exec/mobile-app-design-review-20261024.md#2026-10-29原生work插件内容阶段)。原生更多的完整目标、普通主入口采用、真机升级和正常账户业务继续分别验收。


### 2026-10-29回顾源码门禁

回顾共享API/状态及Native内容形成源码候选。当前独立Next生产构建为`UeTGl0fm8h3F4UjDEJ5h9`，原Web回顾与History29项、Native平台fixture10项通过；原生普通App入口保持，当前安装候选与上节原f8制品一致。本阶段Xcode构建、安装、证书和商店操作为0，实际目标与正常业务继续验收。详情见[原生回顾执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-29原生回顾目标页阶段)。


回顾补充回执：2026-10-29原生11项定向通过，来源区域修订后类型检查和报告/配置两项通过。当前结果为组件技术验证，普通App安装与真实账户生成继续验收。各次命令、范围与重叠项归执行记录。


## 2026-10-29更多导航候选更新

普通Simulator候选更新为`com.inkmemory.uiparity` / `Ink More QA`，Next BUILD_ID `uPuNuHgwJ5Y98cA_d1AQ2`，Hermes SHA256 `9103b83836c6246ac2fd68f9b30918970dab4822cc95a36123118aab0b6dfe0f`。本阶段复用原生二进制、Python/Node运行库与既有配置，更新JS和Next资源，经Simulator ad hoc签名与严格校验后安装。用户主包保持；本阶段Xcode/真机签名/商店提交为0。

当前Web生产构建与36项技术检查、Native时间线/More组合7项及最终重跑通过；实际Simulator已打开五项菜单、写作、时间线/已有报告返回、回顾与原设置根页。正常账户新模型任务、完整Settings/Work资源、Calendar资源配置跳转、复杂工具/MCP交互、真机与商店发布继续等待持续目标验收。该候选退出正式完整iOS交付声明。回执和各次命令见[本阶段执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-29更多app接线与目标页阶段)。


### 2026-10-29资源页面候选状态

当前共享资源状态和原Web呈现已通过credential-free生产构建，BUILD_ID为`n3VcZiPBtUhAapkj7eRso`；MCP/Notion/更多/写作文档21项技术回归通过。Native Notion、MCP列表及详情为源码候选；普通App的完整Settings/Resources接线和系统授权所有者继续实施。

HTTP候选通过原URLSession只投影Content-Type和Retry-After，JS恢复原错误等待合同。Cookie及凭证响应头留在原生。Swift语法检查通过，URLProtocol目标测试、新Xcode构建及普通候选安装待执行；候选来源与真实业务验证分项记录。当前安装的`com.inkmemory.uiparity`沿前阶段制品，用户主包保持。资源候选结果退出已采用、真实资源授权已完成与渠道已发布的声明。
