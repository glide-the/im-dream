<!-- [Sync] 2026-11-02: Google网页后invalid_code先检查Admin独立出口，新增Docker代理与真机工具信任边界。 -->
<!-- [Sync] 2026-11-01: 20实际密码303及PKCE回调、会话/配置/历史200、真实任务完成并结算；保留先前503及UI缺口。 -->
<!-- [Sync] 2026-11-01: 追加19复用连接残余超时与20失败池处理，桌面停止约束和真机独立资格保持。 -->
<!-- [Sync] 2026-10-31: 构建18定向日志已实现，补阶段判定与受控复现；真机采用及业务结果单列。 -->
<!-- [Input] 当前端侧编译入口、原网页登录/认证实现及build17分平台回执。 -->
<!-- [Output] 目标制品配置检查、登录认证排障、恢复步骤和后续验收指南。 -->
<!-- [Pos] 长期维护操作指南；认证职责归跨平台架构，逐次构建与业务回执归设备手册和执行稿。 -->
<!-- [Sync] 2026-10-31: 整理普通env、精确回调、Cookie交接、503/504、平台差异和无凭据采证要求。 -->

# 端侧目标编译、登录认证与排障指南

## 背景与问题

本指南处理“包已安装、App进程启动、登录或工作区读取失败”的定位与恢复。初稿源码核对日期为2026-10-31，初稿设备/API结果引用build17上一轮回执；本文末节追加本轮build17/18复测及修复状态。长期操作步骤与历史结果分别维护。

- 认证方案、所有者、正常/异常时序和状态：[运行库架构的认证合同](../design/multi-platform/mobile-runtime-architecture.md#端侧登录认证与目标编译合同2026-10-31)。
- 当前设备制品、签名和实际HTTP结果：[设备手册第二十一节](ios-iphone-install-release.md#二十一2026-10-31-admin连接复用与构建17)。
- 每次命令、失败和采证资格：[执行记录](../exec/mobile-app-design-review-20261024.md)。

## 目标与边界

保持RN/RNW主界面、正常网页密码登录、App Client ID、S256、Cookie/CSRF、角色与业务权限。iOS App持有Python、Node、Next及原Runtime；公网Admin持有原认证和数据服务。Android沿RN入口完成相同业务合同，当前缺口按下文登记。初稿章节中的命令为后续操作模板；本轮已执行命令和回执归末节与执行记录。

故障处理继续使用原接口和普通env键。服务重启、Admin变更、凭证轮换、数据库维护、依赖安装、模型任务及渠道发布按独立工作项执行；本指南的读取检查不自动触发这些操作。

## 概念与规则

### 事实、方案与待验证事项

| 标记 | 用途 |
| --- | --- |
| 代码事实 | 已从当前文件入口核对的行为；路径/行号可追踪 |
| 历史回执 | 指定日期、平台、制品与操作的结果；复测产生新记录 |
| 方案 | 后续工作项及其验收条件；实施状态单列 |
| 待验证 | 当前缺少足够证据的条件或假设；保留未知状态 |

### 当前平台状态

| 平台/制品 | 历史结果 | 当前资格 |
| --- | --- | --- |
| iPhone16、iOS18.0.1、0.1.0/20 | 系统验证后启动、原登录协议/会话/配置/历史200，一次真实任务完成并结算 | 后台业务通过；原网页弹窗关闭、可见历史和真机恢复触发待独立验收 |
| iPhone16、iOS18.0.1、0.1.0/19 | 18→19覆盖安装、原数据保留、普通冷启动通过；原会话/配置/历史分别200，合法账户与CSRF匹配 | 账户读取通过；原网页登录弹窗、可见历史和一次真实任务按末节继续验收 |
| iPhone16 Plus、iOS18.6 Simulator、0.1.0/17 | 无调试器冷启动自动恢复账号、配置及20项历史，重试点击0 | 对应Simulator的真实账号读取通过；20为该次观测数量 |
| Android当前源码 | ReactActivity入口、共享index.native.js与InkRuntime存在；ensureStarted拒绝CAPABILITY_UNAVAILABLE | 端侧运行时、登录弹窗和HTTP/Cookie桥接待实现/验收 |
| Web | 沿Next和原BFF | 本轮无Web源码改动；后续功能改动执行相邻回归 |

代码：[iOS SessionGate](../../frontend/src/platform/SessionGate.native.tsx#L24)、[Android入口](../../frontend/android/app/src/main/java/com/inkmemory/mobile/MainActivity.kt#L5)、[Android模块](../../frontend/android/app/src/main/java/com/inkmemory/mobile/InkRuntimePackage.kt#L8)。

## 一、先按症状选择检查入口

按“目标制品 → 运行时 → 原会话 → 回调/Cookie → 业务接口”取证。为每一步记录平台、build、时间、前后台状态及结果。

| 现象或错误 | 检查入口 | 对应操作与判定 |
| --- | --- | --- |
| DoubleConversion链接失败、原生模块缺失 | Xcode目标、Pods锁、实际链接日志 | 确认当前失败仍存在，再处理该目标的依赖/链接；安装新依赖属于后续实施 |
| 安装失败、Developer Mode关闭、Team/profile问题 | 当前签名、配对、设备状态 | 按设备手册处理原Team与描述文件；设备使用者完成系统授权与解锁 |
| launch成功、出现工作区暂时无法打开 | SessionGate的ensureStarted与/auth/session | 两类异常共用此反馈；分别取得运行时就绪与会话结果 |
| 登录按钮打开Admin后台登录页、invalid_redirect | /auth/options、原表单action、/auth/start、精确redirect_uri | 核对产品入口与已登记回调；保留当前有效密码回调，停止盲目替换 |
| IOS_ADMIN_HTTP_CONFIGURATION_INVALID | Admin适配初始化与Native绑定方法 | 核对原env格式、adminHTTP/cancelAdminHTTP、Native二进制与Worker资源版本 |
| IOS_NEXT_ORIGIN_INVALID / IOS_BACKEND_ORIGIN_INVALID | host.cjs本机Origin校验 | App本机地址沿原loopback绑定，Admin公网目标沿原后通道字段 |
| IOS_NOTION_CLI_PATH_INVALID | 运行时初始化与原ntn资源 | 先取得真实启动错误，核对规范化容器路径、manifest与权限；版本/帮助执行与授权业务分项验收 |
| codesign钥匙串访问提示 | macOS签名程序与当前钥匙串权限 | 由钥匙串持有人在系统对话框处理原签名授权，密码退出脚本与日志；签名状态与Dream登录分列 |
| BFF_CONFIGURATION_INVALID | 原env消费者和包内有效配置 | 检查必需键存在、URL/issuer/resource关系及原schema；凭据只记匹配布尔值 |
| BFF_SERVICE_AUTH_FAILED | 原服务client_credentials请求的HTTP状态 | 按原服务Client登记、有效性、scope和配置所有者核对；保留角色与权限 |
| BFF_ADMIN_UNAVAILABLE / 503 | Next AdminBffClient服务令牌、resolve/profile或代理前置鉴权 | 定位具体调用阶段、实际传输选择、超时/取消与响应完成情况 |
| ADMIN_TIMEOUT / 504 | Python request_admin_dto及HTTPX适配 | 记录原请求期限和只读恢复次数；检查网络、响应读取与原Admin日志 |
| /auth/session为401 | 原Cookie、handle撤销/过期及响应DTO | 匿名请求401可为预期；通过原网页登录恢复，禁止手工拼装Cookie |
| BFF_ORIGIN_DENIED / BFF_CSRF_INVALID / 403 | BffLoginBoundary、browserRequestHeaders | 核对同源/代理头和当前会话CSRF；写接口继续原校验 |
| BFF_LOGIN_TRANSACTION_INVALID / BFF_OAUTH_CALLBACK_INVALID | 事务Cookie、state/nonce/iss、回调接收地址 | 保留原错误与事务归属；原事务可恢复时使用原回调恢复，过期后重新开始原登录 |
| Google取消、回不到App、disallowed_useragent | NativeAccountLogin、系统授权、App回调登记 | 分别检查系统授权启动、取消、协议回跳和本机BFF接收；Google外部授权使用系统用户代理 |
| 登录成功后弹窗持续存在 | NativeLoginSessionProbe与finishLogin | 检查200、同一来源、user/CSRF结构、Cookie交接和dismiss完成次序 |
| 锁屏、切换后台或进程重开后失败 | AppState、原请求/取消时序、运行时和会话重读 | 将锁屏前请求与新前台请求分开；复测保留原数据及原失败 |
| LLDB导入/静态初始化/符号失败 | harness命令、语言和当前App符号 | 记harness失败；业务结论取普通App、真实HTTP及原页面 |

错误证据：[Next传输错误](../../frontend/app/api/_auth/admin-client.ts#L137)、[Python超时映射](../../backend/services/admin_data/http_transport.py#L49)、[原会话读取](../../frontend/app/_dream/lib/browserSession.ts#L39)。

## 二、目标编译与配置核对

### 2.1 冻结本轮目标和来源

开始前读AGENTS.md、相关.folder.md、当前设计和git status。记录源码commit与未提交输入摘要，保护已有工作。目标记录至少包含：平台/架构、设备或Simulator、Bundle ID/applicationId、版本/构建号、Admin目标、应用本机来源、OAuth登记回调、已有账户及验证范围。

项目Xcode配置中的构建号可被命令行CURRENT_PROJECT_VERSION覆盖。源码标记、IPA/App中Info.plist和已安装版本分别读回。当前工程入口为frontend/ios/InkMemory.xcworkspace与frontend/android/app；RN入口为frontend/index.native.js。

### 2.1.1 平台目标与受控构建入口

| 平台目标 | 当前源码配置 | 后续检查 |
| --- | --- | --- |
| iOS设备/Simulator | Xcode工程最低iOS16.4；build17采用当时iPhoneOS18.5 SDK | 区分iphoneos与iphonesimulator，核对实际架构/SDK；最低运行版本和商店上传工具链分别判定 |
| Android | app/build.gradle.kts配置compileSdk/targetSdk36、minSdk29、Java17和NDK27.1.12297006 | 这些值为源码事实，完整依赖、ABI及端侧运行时资格另验 |

源码：[iOS目标](../../frontend/ios/InkMemory.xcodeproj/project.pbxproj#L491)、[Android目标](../../frontend/android/app/build.gradle.kts#L15)。当前Android源码清单包含gradle-wrapper.properties，本轮文件存在性检查确认gradlew与gradle-wrapper.jar缺失。仓库内自包含wrapper入口尚未具备；后续先确认锁定Gradle执行方式、依赖和归档条件。本轮Gradle下载/执行0，工具链缺口与认证接口失败分别登记。

以下为后续已授权构建模板，前提为依赖锁已核对、原Python/Node/Guest运行资源及Next生产资源已准备、目标配置已冻结。本轮不执行：

```sh
: "${IOS_TARGET_UDID:?从Xcode当前目标清单选择设备标识}"
: "${IOS_DERIVED_DATA:?指定本轮受控构建目录}"
: "${IOS_BUILD_NUMBER:?指定本轮构建号}"
xcodebuild -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory -configuration Release -sdk iphoneos -destination "id=$IOS_TARGET_UDID" -derivedDataPath "$IOS_DERIVED_DATA" "CURRENT_PROJECT_VERSION=$IOS_BUILD_NUMBER" build
```

Simulator使用显式目标ID与-sdk iphonesimulator，按现有开发流程配置签名。该模板不执行公网目标覆盖、IPA归档、安装或认证验收；这些阶段分别形成制品/签名/运行回执。

### 2.2 识别源码、制品和运行进程三处配置

| 位置 | 当前代码事实 | 核对内容 |
| --- | --- | --- |
| 原frontend/.env.local、backend/.env | 继续普通env来源；本轮不读取正文 | 键的消费者、原值归属及选定目标 |
| Next独立构建准备 | prepare-next.py排除env，创建受控构建目录 | 准备成功只证明源码就绪，完整运行配置在后续装配 |
| App资源装配 | bundle-node.py复制两份原env并设置0600；保留原账号回调 | 分别记录源文件与实际包的配置匹配结果 |
| 包内Next Worker | host.cjs显式投影applicationEnvironment及本机Origin/backend绑定 | 核对运行时有效公开地址和绑定；完整进程环境保持私有 |
| Python启动 | mobile_runtime.ios读取包内.env，override=False | 检查现存进程值优先级对有效配置的影响；禁止输出全量env |
| build17公网制品 | 独立私有staging脚本修改包内4个既有目标键后重新签名 | 公网目标装配尚缺少稳定的仓库内标准入口，列后续脚本工作项 |

源码：[准备目录](../../frontend/ios/scripts/prepare-next.py#L15)、[普通env装配](../../frontend/ios/scripts/bundle-node.py#L54)、[Worker环境](../../frontend/ios/runtime/host.cjs#L119)、[Python dotenv](../../backend/mobile_runtime/ios.py#L27)。

现有build-rn-ios.sh包含pnpm install、pod install和uv准备步骤。排障先读脚本；依赖已准备时使用已确认的独立构建命令，避免把重装依赖当作读取检查。[脚本证据](../../frontend/ios/scripts/build-rn-ios.sh#L15)。本指南不执行该脚本。

### 2.3 沿原键核对地址与身份

操作记录中，default取原schema/host-config默认来源，desired记录本轮选定目标，effective记录当前进程的有效公开值与传输归属，revision关联源码/制品/manifest标识。以上用语服务于构建核对，新增配置服务、业务配置字段及运行分支0。

| 既有字段/来源 | 含义与检查要求 |
| --- | --- |
| INK_ADMIN_DREAM_BASE_URL、INK_ADMIN_AUTH_ISSUER、INK_DREAM_API_RESOURCE | Admin canonical身份、issuer/resource；保持原相互校验 |
| INK_ADMIN_DREAM_TRANSPORT_BASE_URL | Next和Python Admin后通道目标；公网包逐一核对 |
| INK_ADMIN_PRODUCT_API_BASE_URL | Product客户端目标；遗留手机loopback3000曾导致用量失败 |
| INK_GATEWAY_BASE_URL | 原Gateway目标；认证读取成功后仍需独立验证 |
| INK_DREAM_PUBLIC_ORIGIN | App本机Next来源，按实际绑定生成；Cookie、Origin与回调接收共用原规则 |
| INK_BACKEND_INTERNAL_URL / BACKEND_URL | Next到同App Python的本机服务地址，由原运行库绑定 |
| INK_DREAM_BFF_REDIRECT_URI | 提交Admin校验的原回调；值需精确登记 |
| InkAccountOAuthCallbackURI、CFBundleURLTypes | iOS系统账号授权的目标App协议；与BFF声明、Admin登记和接收映射一起核对 |
| INK_CLAUDE_MCP_OAUTH_REDIRECT_URI | 独立MCP/Notion授权回跳，保留其协议和操作归属 |
| capabilities.auth.clients.browser | 原登录请求client_id的实际来源；保持已发布Client |
| INK_ADMIN_DREAM_SERVICE_CLIENT_ID / INK_ADMIN_DREAM_SERVICE_SECRET | BFF/Python原服务身份；与用户登录Client分别核对职责 |
| INK_DREAM_BFF_COOKIE_SECRET | 原事务Cookie和CSRF密钥；仅记存在/匹配结果，轮换属于独立操作 |
| INK_ADMIN_DREAM_TIMEOUT_SECONDS / INK_ADMIN_DREAM_MAX_RESPONSE_BYTES | 沿原调用方期限与大小约束，诊断不提升产品配额 |

手机localhost指向手机；Simulator的宿主网络可访问Mac服务。5173属于该App Next，Python使用原动态本机绑定；3000属于用户选定的Admin服务。localhost、127.0.0.1、LAN主机名和公网域名分别核对监听、Cookie来源与OAuth登记，禁止全局替换。

本机Admin仅在用户选定该目标时通过实际LAN可达地址使用；公网目标使用已批准HTTPS。输入普通env并保持一条业务路径，目标差异在制品配置与回执中说明，不新增按部署环境名称解锁鉴权的分支。

### 2.4 形成制品证据

记录锁文件与运行资源manifest摘要、Native可执行版本/UUID、Hermes摘要、Next BUILD_ID、Python和Node平台资源匹配、非敏感目标配置、签名Team/profile有效期及安装前后数据保留结果。含凭据配置只输出存在、权限、目标公开值及匹配布尔值，避免凭据正文和凭据摘要进入日志。

Swift/C++/Objective-C变更需要对应原生目标重新构建。RN源码有变化时重新生成该平台JS/Hermes资源。复用HBC或使用SKIP_BUNDLING=1须证明RN输入相同及Native模块合同兼容；Next源码变化须重建Next资源。每个目标独立核验，构建成功与实际安装匹配分别登记。

## 三、正常登录与回调排查

### 3.1 密码网页登录

1. 通过原App登录入口打开独立登录文档，左上关闭按钮为ink-login-close。
2. 原GET /auth/options返回产品password_action和google_action，产品路径为/auth/dream/password与/auth/dream/google。该接口本身会查询Admin capabilities，503需先定位后通道。
3. 用户沿原密码表单登录；原/auth/start创建事务并取得已发布Client与scope，原/auth/callback负责交换、handle Cookie和事务清理。
4. NativeLoginSessionProbe只同步当前App本机来源的Cookie，调用原/auth/session；200且user/CSRF合法后触发finishLogin。
5. UIKit dismiss完成后presentLogin才resolve；SessionGate再次读取原会话，再显示RN主页面。配置和历史随后按原HTTP接口读取。

手机号/邮箱、密码、验证码、授权码和Cookie正文不进入回执。协议级表单调用、可见表单键入、弹窗关闭、真实业务读取分别验收。

### 3.2 Google与三类回调

| 回调 | 所有者 | 检查 |
| --- | --- | --- |
| Dream账号回调 | 原BFF与Admin Client登记 | 提交的redirect_uri、BFF callbackUri、原事务三方一致 |
| iOS App协议接收与本机HTTP接收 | NativeAccountCallback及BffLoginBoundary.callbackRequestUri | App URI先严格匹配，再映射本机/auth/callback；保留原state/iss校验 |
| Google Provider回调 | Admin及其Google登记 | 由Admin任务核对实际登记，保留原Provider所有权 |
| MCP/Notion回调 | 原MCP授权操作与端侧适配 | 使用原.mcp协议；账号.auth与MCP回跳分别校验 |

build17密码回调沿已登记http://localhost:5173/auth/callback。Google系统授权需要App协议、原Client精确登记、Admin交换服务接受值、同一普通env与App接收映射一致；当前公网完整资格待验证。后续统一回调采用前，先具备必要登记/服务兼容，再用同一业务代码同时回归密码与Google；现有密码入口保持可用。

Google授权使用已实现的NativeAccountLogin/ASWebAuthenticationSession适配，取消返回原登录文档；保持原事务、Client、S256和权限。第三方OAuth的系统用户代理要求见[Google错误说明](https://developers.google.com/identity/protocols/oauth2/native-app#disallowed_useragent)。当前首方密码登录承载沿项目实现；原生OAuth的外部用户代理标准及发布适用性单独评审，完整标准符合性审查待完成。

### 3.3 App Client、PKCE和凭据范围

App Client ID可作为公开标识。PKCE verifier/state/nonce由每次登录事务生成，按S256派生challenge，保持原事务Cookie作用域；静态env承担既有Client/回调等配置。服务Client与BFF Cookie密钥继续由现有App内服务代码消费，RN组件只持有原公开会话与内存CSRF。

当前打包程序复制原env，现行开发制品包含服务身份/BFF配置。App包内静态共享secret的保密性无法由签名、压缩或Keychain自动保证；RFC8252第8.5节定义了该分发限制。外部分发须核定现有服务身份的端侧使用资格、scope、发放/撤销及静态凭据范围，当前审查待完成。后续工作保持原Admin认证与普通env合同，具体改动另行实施；新增认证服务、共享密钥放行或权限绕过均不列为本次排障方案。[RFC8252](https://www.rfc-editor.org/rfc/rfc8252#section-8.5)、[RFC7636](https://www.rfc-editor.org/rfc/rfc7636#section-4.2)。

## 四、503/504与工作区失败的检查顺序

1. **确认版本和现场。** 当前安装build、可执行路径、普通启动、前后台/锁屏、调试器附加时间分别记录。工作区文字反馈涵盖运行时启动与会话两类异常。
2. **确认本机服务。** ready、Next监听、原/auth/session分别取证；端侧ASGI/Node实例与RN页面生命周期保持独立。
3. **确认实际请求归属。** RN本机HTTP、Next Admin后通道、Python Admin后通道、Gateway/SSE分别标注。Next受控Admin来源/路径且redirect=manual才命中系统适配；其余fetch保留原实现。
4. **确认绑定和配置。** 检查Next worker在服务入口前安装ios-admin-http，原AdminBffClient捕获的transport是否命中；Python同步HTTPX绑定只在原iOS组合根启用。源文件存在或打包manifest匹配只证明装配。
5. **确认请求阶段。** 将参数/序列化、队列、系统请求开始、响应头、正文完成、Native回调、原DTO处理分开。构建18已在五类固定认证路径补定向阶段日志，覆盖serialized、native-enter、main-start、network-start、headers、network-complete、native-result、native-return、native-callback和next-result；网络指标和原数字错误码单列。安装采用与真机业务回执分别登记，保持单请求期限、取消与大小约束。
6. **对照原Admin证据。** 按固定接口分类、已有request_id及时间窗口关联。原模块ID缺少映射时保留未知。系统公开GET200、Nginx部分200与具体业务请求成功分别判定。
7. **验证原读取恢复。** 先/auth/session，再/api/system-config及/api/claude-agent/threads?limit=1，随后回到原UI列表。读取使用原Cookie/会话所有者；Mac匿名curl得到401只证明匿名监听响应。

源码：[Next绑定时机](../../frontend/ios/runtime/worker.mjs#L107)、[选择条件](../../frontend/ios/runtime/ios-admin-http.mjs#L14)、[Python绑定](../../backend/mobile_runtime/ios.py#L97)、[HTTPX过滤](../../backend/mobile_runtime/ios_admin_http.py#L19)、[系统池与期限](../../frontend/ios/InkMemory/InkReactNative.swift#L633)。

### 最小阶段观测方案（建议、未实现完整采集）

现有日志不足时，在原函数内补固定阶段与有界元数据，继续原日志设施；原错误码、超时、重试、鉴权和请求处理保持。新增诊断HTTP接口、页面、数据库表和统一监控服务0。

| 原模块 | 建议观测点 | 验证与处理依据 |
| --- | --- | --- |
| [ios-admin-http](../../frontend/ios/runtime/ios-admin-http.mjs#L14) | 选择条件、序列化开始/结束、正文大小、Native回调及Abort | 先证明该原Admin请求命中绑定；按实际失败点调整平台适配 |
| [DreamNodeProcess](../../frontend/ios/InkMemory/DreamNodeProcess.cc#L319) | libuv入队/开始/完成、取消和环境清理 | 区分队列等待与系统网络等待，保留单请求取消及原回调 |
| [NativeHTTPResponse](../../frontend/ios/InkMemory/InkReactNative.swift#L539) | Task开始/头/字节完成、期限/取消、缓冲大小及挂起状态 | 系统返回200与字节/回调完成分别核对，其他Task和连接池存续单独检查 |
| [Python适配](../../backend/mobile_runtime/ios_admin_http.py#L19) | 来源/路径命中、原timeout扩展、返回和错误映射 | 区分Native传输、HTTPX响应及原DTO校验；写入未知结果保持 |
| [AdminBffClient](../../frontend/app/api/_auth/admin-client.ts#L137) | 服务令牌、resolve、profile原阶段与已有request_id | 关联具体上游结果，DTO/CSRF/权限所有权继续原模块 |

每项只记录阶段、耗时、状态/原错误、字节数与匹配布尔值。只有同一平台/制品/调用的证据明确后，选择单点修改及对应回归；证据缺口继续登记待定位，回调、Client、密钥和权限保持原值。

UND_ERR_CONNECT_TIMEOUT只说明该次Undici连接失败。先检查URL分类、来源、redirect条件及当前制品，Gateway/SSE继续原传输。30秒附近的503仅形成计时线索；DNS、TLS、队列、正文读取、回调和JS处理均需各自证据。buffer恢复、墙钟期限和共享连接均已进入当前代码；真机17失败仍保留。

读请求恢复沿原模块执行。普通写请求、创建任务、授权码交换和退出登录采用各自已实现的幂等/未知结果规则；禁止用统一重试循环重复派发。原callback在交换结果未知时保留事务供原恢复，原logout在撤销失败时保留handle。代码依据：[callback/logout](../../frontend/app/api/_auth/handlers.ts#L75)、[Python读写恢复](../../backend/services/admin_data/http_transport.py#L19)。

## 五、前后台、取消与再次进入

| 场景 | 当前行为与检查要求 |
| --- | --- |
| 左上关闭/系统取消授权 | 结束当前登录操作、取消probe/授权；dismiss完成后返回LOGIN_CANCELLED，保留业务数据 |
| 请求中进入后台/锁屏 | 系统调度可能暂停；请求结果和App状态分别记录。URLSession共享池不提供后台常驻执行资格 |
| 返回前台 | SessionGate.active触发refresh，已有inFlight合并；记录是否合并到旧请求及旧请求失败后的原重试结果 |
| 冷进程重开 | 原共享运行时重新装配，原Cookie/handle交由/auth/session复核；后端任务结果沿既有持久化与查询恢复 |
| 会话401 | 原前端清会话并走原登录；后续API继续原认证 |
| 会话503且已有页面 | 原session引用可保留现有页面，后续API继续服务端认证；界面保留不授予新权限 |
| 退出失败 | 原revoke未确认成功时保持原失败与handle；原服务撤销、Cookie过期、跨存储清理和账户切换分别验收 |

前台事件与inFlight完成次序可能影响恢复；该竞态为待验证假设，当前未证明其构成本次503根因。恢复过程中Task、Thread和Agent继续原执行归属，登录关闭与HTTP取消仅结束各自操作，业务任务取消沿原Stop入口。

## 六、安全采证与命令入口

默认使用普通App原UI、启动console和对应接口回执。仅记录：源码/制品标识、时间、App状态、固定路径分类、HTTP状态、已有错误码、耗时、字节数、绑定命中布尔值、账号匹配/CSRF存在布尔值、公开回调匹配结果。响应为错误体时账号匹配记unknown；旧回执false保留原文，并注明未形成账号验证。

日志排除密码、Cookie/Set-Cookie值、Bearer、服务secret、PKCE verifier、state/nonce、授权码、完整回调query、JWT正文、数据库连接串和用户业务正文。错误出现后先保存有界证据，禁止清全库、重建账户、重置业务数据、修改角色、关闭TLS/CSRF/签名校验或默认启动Docker。

以下为后续只读检查模板；变量由当次目标/制品配置提供，AUTH_QA_DIR为已创建且权限受控的私有目录。源env和凭据不放入命令行。

```sh
: "${AUTH_QA_DIR:?设置本轮私有证据目录}"
: "${IOS_COREDEVICE_ID:?从当前设备清单选择目标}"
: "${IOS_APP_ID:?从制品Info.plist核对标识}"
xcrun devicectl device info apps --device "$IOS_COREDEVICE_ID" --bundle-id "$IOS_APP_ID" --json-output "$AUTH_QA_DIR/apps.json"
xcrun devicectl device info lockState --device "$IOS_COREDEVICE_ID" --json-output "$AUTH_QA_DIR/lock.json"
```

已确认空闲的App由设备使用者关闭后，按授权执行一次普通前台console启动：

```sh
xcrun devicectl device process launch --device "$IOS_COREDEVICE_ID" --console --json-output "$AUTH_QA_DIR/launch.json" "$IOS_APP_ID"
```

当前devicectl help说明：App已运行时，该命令的console选项不建立新的标准流重定向；可捕获信号会转发给App。读取观察器状态与终止App分别操作，保持原进行中任务。结束观察后核对目标App及任务存续，清理只涉及本轮明确拥有的工具进程和私有输出。

Simulator只读入口为xcrun simctl list devices available；Android入口为adb devices与当前applicationId。采用HTTPS App Links且目标系统支持时，可读取adb shell pm get-app-links "$ANDROID_APP_ID"；私有scheme按实际intent-filter与回调验证。当前Android Manifest仅有launcher过滤器，账号回跳待实施。[Android官方说明](https://developer.android.com/training/app-links/verify-applinks)。

LLDB为有明确需求时的专项技术手段。编译/符号/静态初始化失败列为harness失败；调度成功需要后续回调文件与HTTP结果证明。调试暂停期间的耗时单列，普通无调试器前台结果独立复测。默认排障不注入登录凭据、不手工同步Cookie、不调用未实现的诊断接口。

## 七、本次错误的复盘与当前结论

| 阶段 | 已有证据 | 处理/剩余问题 |
| --- | --- | --- |
| 早期Release | 曾见DoubleConversion链接失败 | 后续13/15/16/17构建通过；按当前日志确认再处理链接 |
| 构建10 | 公网回调invalid_redirect、误入后台登录 | 11保留原已登记密码回调；Google兼容单列 |
| 构建11/12 | Product API遗留127.0.0.1:3000、用量失败 | 12包内修正原Product目标，证明登录与业务目标需逐项核对 |
| 构建13/14 | UND_ERR_CONNECT_TIMEOUT；历史504；14原密码表单协议及弹窗关闭取得回执 | 协议调用与可见键入验收分别记录 |
| 构建15 | 系统HTTP绑定已采用；物理会话200/50.682秒，后续锁屏 | 全部工作区读取未通过 |
| 构建16 | 缓冲恢复/原期限；物理session503、配置200、history504；Simulator冷启动读取通过 | 成功与失败按接口保留，传输修订未形成真机完整通过 |
| 构建17 | 连接池/Task.delegate；Simulator账号/配置/20历史恢复；物理3项GET503 | 真机未通过，下一步普通前台console与实际绑定/超时定位 |
| 对照及harness | 系统JWKS GET200；服务器部分200；动态符号/表达式失败 | 对照仅覆盖相应请求，harness结果归技术观察，业务资格采用原UI与HTTP回执 |

build17真机原会话耗时30.304秒、配置30.044秒、历史8.932秒；错误均为BFF_ADMIN_UNAVAILABLE。相近期限形成诊断线索，具体失败阶段仍待定位。

原始路径归上一轮私有证据目录frontend/ios/build/rebuild-iphone-20261031/：98/99为17制品/安装，103/104为Simulator，105/112为真机GET，106为公开GET，110为服务器脱敏日志，111为锁屏。文件存在性已核对；初稿阶段HTTP与设备状态未重测，本轮新回执归末节。

## 八、后续工作项和验收

| 优先级/责任 | 工作项 | 依赖与完成条件 |
| --- | --- | --- |
| P0 iOS/测试 | 普通解锁前台冷启动、原重试与原3项GET | 目标/账户/制品冻结、签名有效；保留完整失败与响应结果 |
| P0 iOS/Next | 核对Worker绑定、fetch选择、队列/头/正文/回调阶段 | 实际有效配置和有界诊断；单次请求关联，保留TLS/权限/期限 |
| P0 发布维护 | 续核Team/profile/安装版本与构建输入 | 17阶段profile到期2026-11-01 00:48:40 Asia/Shanghai；下次操作读回实际值 |
| P1 构建维护 | 将既有目标键装配与脱敏制品回执纳入原脚本/CI | 当前公网staging步骤属私有执行材料；签名前装配并校验，不新增发布平台 |
| P1 iOS/Admin登记所有者 | Google精确回调、同Client及原交换服务兼容 | 登记/服务采用先具备，原普通env和两种登录同时回归；本轮无Admin变更 |
| P1 Android | 原InkRuntime运行时就绪、登录文档及HTTP/Cookie桥接 | 保留ReactActivity与原BFF；补齐实际端侧执行，禁止远端Mac执行替代 |
| P1 认证/发布 | 审查包内服务身份/BFF配置的外部分发资格 | scope、发放/撤销、静态凭据范围及原数据权限；具体实施独立安排 |

下表为初稿阶段的后续验收计划；当前执行状态归末节：

| 验收项 | 预期结果 | 验证方式/前提 |
| --- | --- | --- |
| iOS首次安装/覆盖升级 | 目标版本正确、原数据保留、普通启动 | 已授权的签名安装；升级前后目录元数据与版本读回 |
| Android运行时资格 | 完成端侧就绪后进入原认证流程 | 当前CAPABILITY_UNAVAILABLE只支持保护行为检查；实施完成后验证APK/AAB实际运行 |
| 密码登录/窗口关闭 | 原表单成功、合法session、dismiss后RN主页 | 普通App、指定现有账户，记录可见键入与Cookie交接结果 |
| 登录取消/重复点击 | 只持有一个操作，左上关闭/系统取消返回 | 原UI与无调试器观察，迟到回调不改变后续登录 |
| Google授权/取消/回跳 | 原Client/S256、精确登记、本机原callback完成 | 登记与系统用户代理具备，原密码登录同时回归 |
| 会话失效/403 | 401进入原登录；Origin/CSRF/权限拒绝保持 | 正常账户公开入口；权限故障注入仅隔离技术合同，不改真实权限 |
| 配置与历史 | 原DTO正确、现有权限与列表可见 | 原会话成功后逐项GET和原页面，按实际账号返回验收 |
| 网络/前后台/锁屏 | 原失败可恢复，Cookie/数据保持 | 分开记录旧inFlight与新前台请求；锁屏下停止普通前台结论 |
| 进程重开/退出/切换账号 | 原会话重新验证、成功撤销后旧handle拒绝、账户视图隔离 | 无运行中任务的授权复测；跨Cookie存储清理单独检查 |
| 相邻Web与窄屏 | 原登录/回调/权限及导航行为保持 | 后续有功能改动时使用原Web回归，不以Native结果代替 |
| 真实Claude业务 | 原发送/流式/停止/恢复及正常持久化可核对 | 认证读取稳定后按明确模型与调用预算另行验收；本轮模型0 |
| 分发/发布 | 签名、凭据范围与渠道条件分别通过 | 商店当前要求按提交时官方资料再核定，开发包结果独立 |

关闭问题的证据需包含同一平台/版本的普通前台结果、相应HTTP与错误码、实际目标和数据保留、相邻回归及未覆盖项。文档完成、技术验证、真实账号读取、真实模型验收、开发安装与正式发布分别登记。

## 后续问题记录模板

每个新问题在既有执行记录追加一项，保留先前回执；凭据与用户正文退出模板。

```text
事件与时间：
平台/系统/设备或Simulator：
源码commit及本轮未提交输入标识：
App标识/版本/build/制品SHA/Native与JS资源匹配结果：
签名与profile实际有效期：
所选Admin及App本机公开Origin/回调匹配布尔值：
App前后台/锁屏/调试附加起止时间：
原UI入口与操作；已有账户匹配结果true/false/unknown：
原接口/模块阶段/已有request_id/HTTP状态/错误码/耗时/字节数：
实际执行命令/退出码/脱敏证据路径：
已证实原因；待验证假设；本次单点处理：
恢复后的同平台/同制品结果及相邻回归：
技术验证/真实账号读取/真实模型/开发安装/正式发布各自状态：
未执行项、下一工作项、责任与前提：
```

## 官方资料与查阅范围

查阅日期2026-10-31：[RFC7636](https://www.rfc-editor.org/rfc/rfc7636)核对S256；[RFC8252](https://www.rfc-editor.org/rfc/rfc8252)核对原生OAuth外部用户代理和静态共享secret分发限制；[Google OAuth错误](https://developers.google.com/identity/protocols/oauth2/native-app#disallowed_useragent)核对嵌入式授权限制；[Android App Links](https://developer.android.com/training/app-links/verify-applinks)核对HTTPS域名验证。

Apple的[ASWebAuthenticationSession](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession)、[Task.delegate](https://developer.apple.com/documentation/foundation/urlsessiontask/delegate)及[Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)网页需JavaScript，抓取未取得正文。API可用性另核对本机iPhoneOS18.5 SDK官方头文件：Foundation/NSURLSession.h第314–322行、AuthenticationServices/ASWebAuthenticationSession.h第17/69–71行；项目当前最低iOS16.4，17.4回调API由代码availability分支覆盖。Developer Mode具体操作按当次Xcode/设备界面与官方说明核对，本轮系统设置验证0。

## 2026-10-31 本轮503采证入口

当前构建17受控读取：会话503（30.600秒）、配置503（8.394秒）、随后历史200（6.718秒）。原失败与后续成功按单请求保留。构建18只补现有认证适配的脱敏阶段日志；精确制品、安装及业务状态以[本轮执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-iphone-503定向采证与修复)为准。

1. 核对已安装构建、App路径与包内原Admin目标；启动普通console，记录解锁、前台和调试器附加范围。
2. 使用原公开接口与已有Cookie依次读取会话、配置和限1项历史；每次请求取得状态、原错误码、耗时、结果形状和账号/CSRF匹配布尔值。
3. 按日志traceId关联selected-native、serialized与native-enter；核对传输命中及派发等待。requestId存在时附带原x-request-id，日志内UUID保持在适配内部。
4. native-enter至main-start用于核对主队列调度；network-start至headers、network-complete用于核对网络与正文。network-metrics记录系统实际报告的DNS、连接、TLS和响应时段，指标缺失保留未知。
5. native-result、native-return、native-callback、next-result用于核对返回链路。deadline表示适配原期限结束，network-error保留数字错误码；两者分别解释，禁止将取消后的系统-999改写为原始网络根因。
6. 原页面继续显示原加载、失败与重试，原401沿正常网页登录恢复；弹窗在原合法会话/CSRF检查及UIKit关闭完成后结束。写入、授权交换和任务创建继续原未知结果与幂等规则。

采证目录为frontend/ios/build/iphone-503-20261031，属于本轮私有生成物。设备连接超时属于安装/调试前置失败，原API503属于业务请求结果；两项分别记录。日志只记录固定操作名、关联值、阶段、时间、状态、字节数、原错误码及必要生命周期，凭据、Cookie、完整查询参数和业务正文输出0。

构建18已捕获前台session-resolve响应头前NSURLErrorDomain/-1005（8.958秒、0字节、reused=1），Native到Next约2毫秒；另一请求耗尽原30秒期限，清理返回-999。该证据指向系统网络连接阶段，具体物理链路原因保留未知。

构建19源码增加一次原期限内的固定认证读取恢复：仅上述-1005且未收到头/体、未取消；GET JWKS/capabilities及POST resolve/profile按原可重复读取合同处理，服务token、授权交换、撤销和其他写入保持原规则。响应头后失败与超时沿原错误返回。日志收敛为失败/恢复时输出当前请求暂存阶段；普通成功不输出完整阶段。技术验证、安装采用及真实业务结果以执行记录为准。

19本轮原GET回执：会话200/4.924秒，配置200/5.370秒，历史200/3.054秒；原账号匹配与CSRF存在，workspace_enabled与im_full_access_enabled均true。当前选定模型为deepseek-v4-flash-vision-exp，模型目录200。单次真实任务预算1；登录弹窗、历史可见结果与任务正常持久化按独立回执判定。

后台采证补充：当前Mac仅识别该手机的usbmuxd无线设备，原App端口连接未建立；USB数据连接为后续后台采证前提。调试器表达式及电脑点击工具的前置失败与App HTTP结果分别登记。用户使用电脑期间保持桌面、镜像和键鼠停止操作，端侧原运行归属与普通数据保持。


## 2026-11-01 USB后台复测与失败池恢复

USB数据连接已枚举到同一设备。usbmuxd直连原App端口返回连接拒绝；后续从现有App内CPython独立线程调用原公开HTTP，不新增监听端口或业务入口。LLDB表达式返回unknown error时须先读取脱敏设备回执，确认实际派发次数；密码、授权交换或任务创建的未知结果禁止直接重发。用户使用电脑期间，镜像、桌面、窗口置前与键鼠保持停止。

19冷启动/auth/options 200、7.591秒，后续同一PID的该GET 503、30.070秒；后者位于service-token响应头前，active、reused=1、正文0。20在-1005或原期限超时后退役当前Admin Session，后续Task获取新Session，旧在途Task继续其原期限；普通取消只影响当前Task。超时本次返回原失败，服务token和写入单次发送。固定读取仅沿原头前-1005规则恢复一次。

复测按“同一制品 → /auth/options → 正常密码网页登录 → /auth/session → 配置 → 历史 → 一次最短真实任务”进行。原会话/CSRF和正常messages/status持久化结果只记录形状、匹配布尔值、状态和用量。后台协议结果、原页面可见状态与登录弹窗关闭分别登记；接口成功不能替代弹窗关闭回执。实际命令、签名有效期、安装和业务结果归执行记录。


### 构建20系统验证后实际回执

设备持有人完成系统验证后，devicectl准许启动；后续受控冷启动Next Ready277ms、App PID9053。20早期/auth/options 503、9.332秒发生于密码提交前，模型提交0；对应失败保留。受控冷启动该GET 200、2.424秒，随后暖读取200、2.908/2.320秒。

单次密码POST返回303，原/auth/start、authorize、/auth/callback与/login导航完成，合法会话/CSRF恢复；配置、模型目录和历史均200。原公开POST /api/claude-agent单次发送，App内Python→原SDK/CLI完成，最终回复匹配约定短回复，助手completed、Thread idle、原messages持久化通过。正常Admin同一账户时间窗口内仅1项Gateway请求，HTTP200、succeeded、settled；实际模型deepseek-v4-flash-vision-exp，输入3627、缓存读取19712、输出89、扣减23428 Token。追加模型调用0。

后台协议读取与页面显示分别验收；本次操作未控制真机页面。原页面的登录弹窗关闭及历史/新回复显示待手机可见回执。网络丢失恢复、取消隔离与失败池排空已通过定向技术合同；实际真机恢复触发及长期网络稳定性仍缺证据。具体回执归[执行记录](../exec/mobile-app-design-review-20261024.md#2026-11-01-构建20原登录协议与一次真实claude任务)。

## Google登录后停在认证服务登录页

Google网页身份验证后，Admin通过`https://oauth2.googleapis.com/token`兑换授权码。该段连接由Admin的出口提供；手机VPN覆盖手机网络。`invalid_code`覆盖provider授权码兑换失败，排障按服务端实际连接证据判断。

本轮发现原Tinyproxy17891的上游17890缺失，CONNECT502。当前原生Admin继续原HTTP代理配置，Tinyproxy指向Docker Clash混合代理17892；容器BitzNet节点独立出站。服务名tun-proxy，当前配置TUN关闭，宿主默认路由保持。Admin部署资源归其`deploy/clash/`目录，真实配置退出Git。

排查顺序：

1. 核对公开OAuth错误码、时间与请求路径，输出排除完整查询、授权code/state、Cookie与凭据。
2. 核对Admin服务用户、实际Node环境、现有HTTP代理监听及对应上游，使用无凭据公开Google端点验证连接。token端点GET404与JWK200只证明网络。
3. 核对容器healthy、回环发布、原配置、节点选择和私有日志；原Admin及PostgreSQL保持。
4. 重新发起原Google登录，观察原App回调、BFF exchange/session、弹窗关闭及主页。先前失败或过期的code退出重放。
5. iOS拒绝测试runner时，将签名、profile、设备信任及UI工具状态单列。工具错误退出业务缺陷判定；后续真机闭环以可见主页与原会话共同确认。

2026-11-02独立出口采用后，用户确认真机复验通过。该结果登记为用户手工验收，自动化runner限制及逐阶段证据缺口分别保留。本轮实际结果与限制见[账号执行记录](../exec/ios-account-entry-fix-20261102.md#google回调兑换与独立出口2026-11-02后续)。
