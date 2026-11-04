<!-- [Input] USB连接的原iPhone、构建24至27配置、现有账号与启动设计及公网Admin运行证据。 -->
<!-- [Output] Google与注册入口诊断、最小修订、技术验证和设备采用回执。 -->
<!-- [Pos] 本轮移动账号入口修复执行记录，真实身份验证与技术资格分项登记。 -->
<!-- [Sync] 2026-11-02: 独立代理出口采用后，用户确认真机复验通过；自动化工具限制按历史回执保留。 -->
<!-- [Sync] 2026-11-02: 记录精确账号回调不一致与日志接线修复，保留并行图标改动及原业务。 -->

# iPhone账号入口与错误日志修复

## 当前交付状态（2026-11-02）

| 交付物 | 当前结果 | 验证边界 |
| --- | --- | --- |
| iPhone构建27 | 原bundle覆盖安装、普通启动通过 | 原数据保留；开发签名安装包 |
| Google入口 | 真机原按钮、取消及关闭通过；修复出口后用户确认真机复验通过 | 最终结果来自用户手工确认；本轮自动化未取得逐阶段会话及界面回执 |
| Google服务端兑换网络 | 独立Docker出口已采用，撤除Mac临时转发后Admin实际网络读取通过 | 公开端点读取有命令回执；登录业务结果由用户真机复验确认 |
| 注册入口 | 真机Create Account字段与按钮通过，原POST及失败恢复技术回归通过 | 新账户创建尚未执行 |
| 开发者页 | 构建26真机显示HTTP503原消息及WebKit frame，三类账号来源和复制回归通过；构建27保留相同接线 | 进程内错误记录，系统浏览器网页内部内容退出采集 |
| 公网Admin | Linux CI及制品校验通过，候选服务直连/公网200，catalog dry-run更新0 | 原配置其他字段、权限及数据目录身份保持 |

下方保留各阶段执行与恢复记录；当前状态按本表及文末最终采用回执核对。真实模型调用、新账户创建和App Store发布均为0。

## 需求与问题判断

目标为USB诊断Google、注册和开发者控制页日志。先检查实际安装包及生产接口，限定现有账号路径、包内配置与错误通知；正常网页登录、Client ID、PKCE、Cookie/CSRF、权限与数据保持。用户设备VPN已开启，实际连接为wired；网络状态独立于配置校验结果。

| 证据 | 发现 | 处理 |
| --- | --- | --- |
| 原iPhone构建24的Info及包内env | 原生App回调与BFF HTTP回调不同，原`authorization`精确校验拒绝 | 仅包内BFF既有env键投影到对应App回调，核对Info宏 |
| 公网同Client授权探针 | 原HTTP回调接受，App回调返回invalid redirect | 原Admin兼容补丁按同一Client增量登记；scope/grant/secret保持 |
| 真机原WK注册页面观测 | Create Account、Email、注册及Google按钮存在且启用 | 复用原表单，退出新增注册业务职责；账户创建成功待独立验收 |
| 原诊断采集代码 | 启动、会话、配置及目录有记录；账号、文档和Google异常缺少接线 | 复用InkAccountError及原进程快照，补固定三类来源 |

注册与Google交互归[现行iOS设计](../design/multi-platform/mobile-ios-interaction.md#公网包账号回调与诊断接线2026-11-02)，错误来源与生命周期归[启动交互](../design/multi-platform/mobile-startup-interaction.md#账号错误接入2026-11-02)。同一路径复用现有界面、表单及会话验证，新增页面、数据库表、发布平台和认证系统为0。

## 实施范围

- `InkAccountLogin.swift`保留原校验与系统授权，记录configuration、authorization-configuration、system-authorization、callback失败。
- `MobileHostViewController`仅采纳原允许来源的主框架公开错误；`InkRuntime`通过已有RN事件机制转交。
- `SessionGate`将原账号错误写入`BackendRuntimeManager`；`RuntimeDiagnostics`显示和复制同一记录。取消继续原规则，页面刷新读取原内存，原请求重放为0。
- `AuthEntry`保留原Google/密码表单和注册字段；仅增加公开失败码、options HTTP状态与原异常上报。
- `bundle-node.py`仅调整打包副本的既有回调键；原Web env及源码env保持。
- Admin复用既有精确回调兼容补丁，隔离工作树PR41合并到main；运行发布仅覆盖4份已验证实现/CLI，候选配置仅为原localhost服务增加一个回调。源工作区中其他未提交改动保持。

凭据、Cookie、Bearer、PKCE、授权code/state、表单正文退出采集；页面保留所采集错误原文。并行任务的图标、启动画面与相关文档保持，当前包沿现有源码一并构建，相关设计由其原执行记录负责。

## 验证记录

工件根为`frontend/ios/build/ios-auth-20261102/`，属本轮私有且git忽略目录；日志保留实际失败与后续复验。

| 命令或操作 | 退出码 | 关键结果 |
| --- | --- | --- |
| `pnpm exec vitest run app/lib/auth/config.test.ts app/lib/auth/browserSessionService.test.ts app/lib/auth/oauthClientCatalog.test.ts`，Admin隔离源码 | 0 | 25项通过；同Client、精确回调、交换恢复及权限保持 |
| Admin隔离`pnpm exec tsc --noEmit --incremental false --pretty false` | 2 | 原安装依赖缺少embedded-postgres；完整CI及ECS构建单独核验 |
| Admin PR41 CI | 0 | Deterministic checks和Drizzle migration journal通过；合并提交5cc8323142052ca450850e5c8a419c5166f989f2 |
| Node原生TS runner直接执行mobileHost.test.ts | 1 | extensionless import解析失败，harness未完成 |
| 隔离TS loader执行同一mobileHost.test.ts | 0 | 3项通过 |
| `pnpm run native:typecheck`及`pnpm exec tsc --noEmit --pretty false` | 各0 | Native及Web类型通过 |
| `pnpm exec playwright test --config=ios/build/ios-auth-20261102/validation/final-playwright.config.mjs`，frontend目录 | 0 | 21项通过；原注册POST、失败/重试、取消、登录窗口关闭及三类错误展示/复制 |
| `python3 -m py_compile frontend/ios/scripts/bundle-node.py`及生产AST配置资格 | 各0 | 5项配置合同通过；目标回调、其他env键保持、0600、重复键和Info不符拒绝 |
| `pnpm build`，本轮隔离Next build-source | 0 | 原Next生产构建通过 |
| `bundle-next.py --verify-sources` | 0 | 当前553项运行输入匹配 |
| `xcodebuild ... CURRENT_PROJECT_VERSION=25 CODE_SIGNING_ALLOWED=NO ... build` | 0 | Release iPhone目标构建通过 |
| `python3 .../package25.py` | 0 | 83份framework签名、329份Python源码比对、codesign深层严格校验及IPA校验通过 |
| `devicectl device install app ...`及普通`process launch` | 各0 | 原bundle覆盖安装构建25并启动；未卸载或清空App数据 |

首次Playwright新错误用例遇旧Vite优化产物，独立观察者探针定位为缓存中的旧fixture；明确force重新优化后全21项通过。注册密码选择器按辅助文本修正到原字段name，表单未调整。首次Xcode资源脚本的Info宏核对失败，按实际target解析宏后通过。初次包脚本基准路径拼接错误，仅清理本轮release25副本并更正；原构建24及用户数据保持。

USB调试中的首次LLDB批量attach未等待停止、Swift复杂表达式JIT异常及Python调度探针未执行，均记录为harness失败。后续ObjC++已读取真实WK页面并完成原注册切换；该证据证明原页面渲染与按钮状态，退出真实注册成功及Google身份验证资格。

## 公网发布与设备复验

Admin PR：[41](https://github.com/glide-the/dream-im-platform/pull/41)。候选运行目录`/srv/ink-admin-releases/20261102T-native-account-callback`复用原依赖和数据目录。原catalog CLI dry-run为一个Client追加一个URI，正式apply verified=true。原scope、grant、secret及其他配置逐字段核对保持；`RUN_DB_MIGRATIONS=false`，数据库目录与原权限保持。

初次候选复制排除了workspace子目录的node_modules，原生产构建以TS2307退出。停止本轮构建及观察进程后，仅补`packages/db/node_modules`到原依赖位置的链接，依赖安装与源码变更均为0，再由原`pnpm local:stable`构建。构建、服务就绪及双回调复验继续更新本节。

设备构建25：`com.inkmemory.mobile`，IPA `frontend/ios/build/InkMemory-Account-Release-device-20261102-b25.ipa`，SHA256 `7b4526c4c8e60d566d69b11a0c89ec09dd21acfa0b019b1651c1f616b48c94e4`。开发profile有效至2026-11-08 01:03:45 Asia/Shanghai，商店发行资格沿独立发布文档。

## 评审与验收边界

设计评审：待满足明确前提后通过。原业务与权限保留；回调映射和错误接线对应已定位缺口；无新增页面、认证体系或数据库。技术回归、目标构建与原设备安装通过。公网双回调、真机Google系统授权、用户Google身份验证、真实注册成功及Web账户回归分别按实际回执登记。真实模型调用、商店提交与正式App Store发布为0。


### 真机诊断与WebKit错误格式修订

构建25的实际开发者页已显示原会话503及登录页面错误，USB XCUITest `testDiagnosticsShowsObservedFailure`最终退出0，真机截图与AX树保留在`ui-validation/diagnostics-device-final.xcresult`。首次运行期间前台界面发生切换；第二次实际页面已打开，harness将header误查为StaticText而失败；按实际AX类型Other修正后通过。页面及产品代码未因这两项harness失败改写。

真机同时表明WebKit的Error.stack仅含frame，旧`stack ?? message`写法丢失message。`AuthEntry`改为name、message与stack共同上报。明确stack-only Error fixture的22项聚焦回归与Web类型检查退出0；对照探针证明旧表达式缺失`AUTH_OPTIONS_UNAVAILABLE (HTTP 503)`，当前表达式保留该消息和原frame。构建26采用该修订及当前并行启动资源，556项Next运行输入已核对，Release目标构建、83份Framework签名、329份Python源码比对及IPA CRC/严格签名检查通过。制品`frontend/ios/build/InkMemory-Account-Release-device-20261102-b26.ipa`，SHA256 `02bf81a283d15ff641d6d5ed7105fdbf0483c86caf78dd1a8d9cfd1c294a00db`。

### 公网构建恢复记录

候选完整构建期间记录MemoryCurrent约1.23GB，随后SSH banner连续超时且公网502。该时间关联构成资源诊断依据，OOM根因仍需系统记录核实。云助手仅停止本轮候选构建的任务`t-bj071vg5edlaio0`停在等待执行；对应命令含hostname与WorkingDirectory精确检查。控制台已核对实例`i-2ze9gvp834u057cbobbq`、名称、北京地域及公网IP，发起一次普通恢复重启。原数据库、磁盘、密钥与swap配置保持，后续以原服务恢复和公开认证复验为前提。

阿里云[停止中状态处理](https://help.aliyun.com/zh/ecs/support/troubleshooting-and-resolution-to-instance-issues-in-the-stopping-state)和[普通重启](https://help.aliyun.com/zh/ecs/user-guide/restart-instances/)说明该阶段及恢复方式，查阅日期2026-11-02。当前重启、服务就绪、双回调及Google实际授权继续分项记录。公网发布状态为待完成。

文档验证：Markdown清单905项，本轮影响10份，185链接与42锚点/源码行号通过；25张Mermaid解析和渲染通过，新增/修改文本禁用词0处；两项git diff检查退出0。后续本记录追加文本沿同一验证器复核。


构建26已由`devicectl device info apps --bundle-id com.inkmemory.mobile`读回版本0.1.0(26)。`testLoginPageOriginalFailureIsDiagnosed`沿真实登录窗口、HTTP失败、关闭与开发者页完成，退出0；截图直接包含HTTP503消息及WebKit frame，原文已核对。工件归`ui-validation/login-error26-device-r2.xcresult`，静态截图为`ui-validation/login-error26-attachments/98B4AC39-A143-47E9-B6DA-D86BCA0F4967.png`。首次冷启动UI资格未加载accessibility，独立普通启动与后续完整测试分别登记；正常iPhone应用进程内Next已就绪。

公网恢复：一次普通ECS恢复重启已完成；原制品通过既有`pnpm run start:embedded` supervisor在原服务中恢复，direct/public各200。该临时配置沿原服务用户、数据库目录、权限及既有构建产物，拆分原`local:stable`中的build和start两个阶段。后续候选构建由具名临时systemd unit执行原`pnpm build`，通过后才切换原服务的源码目录与已构建产物；失败自动回到原制品。运行时业务入口、账户和数据服务保持，源码依赖安装与schema变更0。

原服务的NODE_OPTIONS堆上限为2048MiB，物理MemTotal约1607MiB。首轮发布前未核对该构建条件，造成公网中断；本轮明确记录该操作缺口。一次512MiB堆/900MiB初始进程预算构建失败，按实际MemAvailable356MiB放宽至1000MiB后，最终日志确认V8512MiB堆耗尽，build worker SIGABRT，退出1；监测到的原memcg事件oom=0。该限额失败已自动恢复原服务，未再次造成主机连接丢失。现以640MiB堆、1040MiB构建进程上限及600秒启动期限复验，原业务数据目录与权限保持；结果继续以对应回执为准。

云助手恢复任务最终状态为发送失败，任务已结束。当前build仅限本轮`ink-admin-ios-account-build-20261102-r2.service`及对应观察进程。


## 源码证据索引

| 事实与修订 | 当前入口 |
| --- | --- |
| 原精确账号回调校验 | [NativeAccountCallback.authorization](../../frontend/ios/InkMemory/InkAccountLogin.swift#L57) |
| Google阶段错误投影 | [NativeAccountLogin.report](../../frontend/ios/InkMemory/InkAccountLogin.swift#L210) |
| 原允许来源的账号错误消息 | [MobileHostViewController](../../frontend/ios/InkMemory/MobileHostViewController.swift#L174) |
| RN固定事件 | [InkRuntime.supportedEvents](../../frontend/ios/InkMemory/InkReactNative.swift#L51) |
| 原登录观察实例转交错误 | [InkRuntime账号接线](../../frontend/ios/InkMemory/InkReactNative.swift#L401) |
| 固定来源及进程内快照 | [BackendRuntimeManager](../../frontend/src/runtime/BackendRuntimeManager.ts#L10) |
| 订阅与释放 | [SessionGate](../../frontend/src/platform/SessionGate.native.tsx#L60) |
| WebKit保留name/message/stack | [AuthEntry](../../frontend/app/_dream/components/Auth/AuthEntry.tsx#L63) |
| 公开认证失败来源 | [AuthEntry](../../frontend/app/_dream/components/Auth/AuthEntry.tsx#L71) |
| 包内回调与Info宏一致性 | [bundle-node.py](../../frontend/ios/scripts/bundle-node.py#L105) |


### Linux CI制品替代服务器编译

640MiB/1040MiB预算构建期间SSH再次超时，已停止该具名构建并由原观察任务恢复原制品；公网再次200。后续采用Linux CI完整构建，ECS仅校验和启动已构建制品。原服务继续使用原supervisor、私有配置、数据目录及权限。

隔离源码分支`codex/ios-account-linux-build-20261102`以实际ee0497b43115为基线，保留12份当前已部署的源码差异，再采用已评审的4份账号兼容实现。此分支保留当前业务实现，Root Admin未提交工作区与其他Agent改动保持。已逐字节比对917份运行输入；源锁文件与ECS一致，实际Node版本为22.23.4，CI按该版本构建。CI沿既有配置、unit、lint、类型、build与隔离migration门禁，并额外保存Linux x64制品及输入/输出SHA-256回执。源码分支提交`0418fbd`。该分支承载运行快照的构建与追踪，正式账号修复源PR41已合并；当前主分支业务变更继续其原发布职责。

制品内容限定`.next`、`packages/db/dist`与来源回执；env、凭据、业务数据、node_modules及Next cache排除。ECS接收前核对完整运行输入与锁摘要，解包后逐项核对输出；激活失败沿原制品恢复。CI上传制品、ECS启动、公开认证与真机Google资格分别登记。

### Google入口选择修订与CI复跑

用户指出系统窗口显示ink-admin网站。代码核实：宿主拦截原Google POST后打开通用authorize，Admin原loginPage显示/auth/sign-in，后台管理员路径为/admin/login。原Web的/auth/dream/google直接调用social provider。现将原用户Google选择沿单值identity_provider参数进入已签名查询，Admin原页面验签后继续原social流程，Google失败回调停止自动跳转并保留原重试。原Client、PKCE、账户和权限保持。对应PR42；该UI入口修订和真实Google完整成功分别验收。

物理testOriginalRegistrationAndGoogleEntry的进入/取消版本退出0，证明原注册表单和系统会话。后续google-provider26-device运行在查找第二次Google按钮阶段失败，退出65；未观察到Google页面。该harness对原WK而非系统浏览器WebView执行滚动，伴随页面仍加载，结果退出provider业务缺陷和Google成功资格。

Linux CI41403579754在unit阶段23项失败，build与artifact步骤未执行。21项为已部署Registry293与旧生成清单不符，2项为原Run绑定/catalog测试落后；从已提交c0ddbde恢复库存与catalog测试、只读复用原工作区两份对应测试后，保持运行源码。合并Google入口修订的构建快照为427c2df，CI41405015995继续完整门禁。

当前Swift生产enum隔离资格退出0：原Client/S256/state等字段保持、Google选择单值和幂等、重复/其他provider拒绝。实际Next556项运行输入核对通过；构建27继续iPhone目标编译，设备采用独立记录。

Google选择连续性：隔离Vitest五文件30项、受影响TS lint、实际AuthSignIn的Chrome四项流程均退出0。PR42完整CI通过，合并提交06c435b04420f3743fe21a51117c78cbd40a74f9。默认Web密码/注册/Google、一次自动选择、签名查询保持、失败片段停止及原重试均有技术回执。

构建27的Release目标编译、83份Framework签名、329份Python源码比对、Next556输入核对及IPA CRC/深层严格签名通过；SHA256为e34d8030fc5e249aff5b2b40a0702dbe500c786c196bbc1a69dfdea4aa3d2579，147733575字节。原iPhone的installed27.json读回0.1.0(27)，普通启动退出0，覆盖安装保留App数据。公网候选另行采用后再做Google页面资格，完整Google身份验证和账户创建继续分别登记。

Linux run41405015995的完整unit/lint/type/build、打包和隔离migration通过，制品上传因隐藏输出目录被action过滤而失败。目录由.release-output改为release-output，内容与校验保持；新快照9622393的run41406132016执行同一完整门禁。公网候选917份输入再次核对0差异，当前活跃服务维持原制品。

Google错误恢复补充：实际provider的appendQueryParams会添加error/error_description。当前AuthSignIn在google-error页恢复原已签名查询后提供显式重试，Chrome实际组件5项复验及lint退出0，覆盖access_denied、temporarily_unavailable、签名字段保持及原默认Web。独立PR43；最终构建快照75a795d采用同一补充，run41406911965继续完整门禁，前一9622393快照退出最终部署候选。

部署准备：原/候选真实配置名为.env.local，各105项键、0600、uid999，无重复键。候选最终917份输入与构建分支再次0差异。操作脚本在服务切换前核对精确主机、架构、原恢复目录、Node版本、锁文件、输入/输出摘要及原数据inode/owner；只接受相对路径及普通tar文件，失败恢复原服务和本轮候选输出。AST/纯fixture与py_compile均退出0，整体脚本尚未执行。

PR43完整CI通过，合并提交f6bfd5c5f74c2a9b550680e44911332cd983944a。当前最终运行源码与公网候选0差异；整体操作脚本继续保持未执行，待最终Linux制品及门禁完成。此前两个有界构建unit均为failed，原制品服务active；无活跃构建或延后切换计划。

## 最终制品与服务采用

最终源码75a795de42db3e9eff3de6dc19005dc0bb1b416f，Linux CI [41406911965](https://github.com/glide-the/dream-im-platform/actions/runs/41406911965)的配置、unit、lint、类型、build、打包、上传与隔离migration均通过。GitHub连接器读回两项job成功并取得artifact 13123898772；本机gh下载曾因TLS握手超时退出1，改用连接器文件引用下载成功。ZIP仅含tgz、sha256、receipt三项。

制品SHA256为41e16e058361738cba440d2a3000fefbd1a0443f7a4a81687bb792c1ff2ba225。Node22.23.4/Linux x64、917份输入、981份输出及原锁文件逐项校验；包内原生.node/.so/.dylib为0，既有Linux依赖复用。执行activate-linux-artifact.py退出0，ECS编译/依赖安装/schema操作均为0；服务采用候选目录，buildId=dLfpF-c4NJoCL-X1NifWE，直连/公网均200，原数据inode与owner保持。源码/产物/运行回执归本轮私有工件，回退原制品继续保留。

候选配置仍为105键，仅同一Client追加精确App回调；其他原字段逐项保持。catalog的--browser-redirects复核为dry-run、updates=[]，verified=false按计划模式记录；本次额外apply为0，前阶段正式登记verified=true继续保留。

物理iPhone的google-provider27-device.xcresult退出0，80.456秒。沿原Login→Register→Continue with Google，直接进入accounts.google.com的真实Google账号选择页面；未执行第二次登录方式选择。取消系统窗口及原左上关闭通过。原注册表单截图CFCF1AE5-843A-4A20-BB16-6870F024C60F.png，Google页面截图13B741CB-D267-402C-8A9E-09E53BFF1322.png，均归ui-validation/google-provider27-attachments。截图已目视核对，含个人账户的截图保留于git忽略工件目录，正文退出账户值。

最终验收状态：技术修复、构建、开发签名、真机安装、原注册入口、Google页面进入/取消及错误日志验证完成。完整Google身份授权、最终登录会话、新账户创建与真实模型业务为独立验收项，本轮未宣称完成。正常账户、权限和业务继续原路径。

公开资源检查：首次10个JS读取中7个200、3个为URLError/TimeoutError，退出1；仅对这3项执行有界GET复验后全部200，退出0。真机Google账号选择页已实际渲染，当前证据支持该次静态读取的暂态网络失败；应用重试与业务实现保持。获取复验JSON的首次SCP发生在写入完成前，退出1；后续单文件续取，按实际回执登记。

最终文档检查：check-docs.mjs退出0，Markdown清单921项、本轮11份文档、221个链接、94个锚点及源码行号，错误和新增术语命中均0。check-mermaid.mjs退出0，31张图解析/渲染通过；git diff --check退出0。文档验证退出功能验收职责，真实Google完整授权及注册成功仍按上表边界登记。

服务收尾复核：service为active、User=ink-admin、候选WorkingDirectory、MainPID=23739。ECS本机直连完整文档200、10508字节、退出0；一次公网curl接收200后正文8秒超时，退出28，单列网络观察，未据此调整业务代码或服务器。SCP续取复验JSON已完成。真机Google页面完整渲染与注册入口资格保持。

Mac公网匿名读取完整登录文档：public-document-final.json记录200、11989字节、4.577秒、complete=true，命令退出0。该结果与真机Google页面渲染、ECS直连结果分别留存；ECS自身公网读取超时继续保留原证据。最终source/env、原Admin脏工作区及并行品牌/文档改动均按各自归属保留，未执行本轮Dream提交或回退。

## Google回调兑换与独立出口（2026-11-02后续）

用户实际完成Google网页登录后，15:54:05的/auth/sign-in公开error为invalid_code，原签名、Google选择及App回调字段仍存在；原生App尚未收到成功回调。服务端实测Tinyproxy17891上游17890无监听，Google CONNECT502。该证据将本次失败定位到Admin到Google的授权码兑换网络，弹窗关闭逻辑退出此次修改范围。

临时仅恢复17890反向出口后，Google接口连通；原Mac relay处于disabled且本机3000有现用Node服务，该状态保持。本轮临时SSH未绑定本机3000，未启用已禁用的完整relay。用户随后明确要求Docker tun-proxy并提供私有Clash配置，实际Docker操作授权范围限定独立代理。

Docker Compose及配置边界位于Admin隔离工作树的deploy/clash。实际配置为21节点VLESS/Trojan、7890混合代理、原自动节点选择；TUN维持原关闭配置，服务名tun-proxy。运行容器采用隔离bridge、回环17892、只读配置和根文件系统、清空capabilities，控制器保持容器内loopback。Node业务、网页登录、PKCE、账户、scope和权限保持。

原生Admin未重启，PID23739；原Tinyproxy4条上游指向新容器。Docker引导连接及本轮Mac反向SSH已撤销，17890监听不存在。按Admin运行用户、实际Node/proxy环境读取Google token端点为GET404、JWK200，339ms/317ms，退出0；容器healthy，主机可用内存约747MiB，swap仍0。该资格对应服务端网络；公开端点探针提交凭据及兑换Google授权码的次数均为0。

本轮用户暂不需要luna-test-stage回归，已中断该阶段，单元/浏览器隔离回归未继续。实际部署执行Compose配置预检、真实Clash配置检查、容器启动与实际网络读取，退出码均0。初次Python YAML读取缺少模块，改用已安装Ruby Psych读取结构元数据，未安装依赖。初次临时SSH控制socket路径过长退出255，采用本轮受限短路径后成功，最终连接已精确关闭。

USB只读页面检查的testInspectGoogleReturn未执行到测试方法，XCTest runner被iOS以签名/entitlements/未信任开发者错误拒绝。profile设备、Team、有效期、公开证书与已安装App匹配，本地深层严格签名验证退出0；普通Dream App启动退出0。iPhone镜像要求Mac登录密码，本轮未输入、未绕过该锁定。该阶段自动化未取得完整Google授权、App回调、session、自动关闭及主页回执。

最终用户回执：2026-11-02，独立出口修复后，用户回复“好了我已经验证了”。本次Google登录修复登记为用户真机复验通过；内部各请求状态码、会话写入和页面关闭的自动化逐阶段证据保持缺失。该确认范围为本次登录问题，注册新账户、真实Claude任务和商店发布分别沿原记录验收。

本轮运维回执归frontend/ios/build/ios-auth-20261102的admin-google-transport.json、upstream-adoption.json和after.json；真实节点凭据及完整配置保留私有路径，退出版本库和日志。
