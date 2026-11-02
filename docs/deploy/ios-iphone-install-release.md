<!-- [Sync] 2026-11-02: 原iPhone从23覆盖安装24并普通启动，2161项原数据metadata保持；保留首次失联回执。 -->
<!-- [Sync] 2026-11-01: 启动控制页构建24完成签名与制品核对，原iPhone安装时连接中断，设备采用待重连。 -->
<!-- [Sync] 2026-11-01: 当前工作区公网构建23重新生成Next/RN与Python资源，原iPhone从22覆盖安装并启动；源env和手机数据保持。 -->
<!-- [Sync] 2026-11-01: 写作资源纠偏要求prepare/build/verify与实际服务根摘要一致；模拟器及物理制品资格分别登记。 -->
<!-- [Sync] 2026-11-01: 构建22修复Notion授权链接闪退，模拟器默认浏览器与七项Web通过；同机覆盖安装及启动通过，真实授权独立验收。 -->
<!-- [Sync] 2026-11-01: Notion构建21同机升级，精确解释执行文件可读检测及版本/帮助通过；原资源401保留授权前提。 -->
<!-- [Sync] 2026-11-01: 系统验证后20普通启动与后台真实业务通过，原首次Security和503保留；页面与弹窗待独立验收。 -->
<!-- [Sync] 2026-11-01: 追加构建20失败池修复、增量构建与签名安装回执，原业务验收分列。 -->
<!-- [Sync] 2026-10-31: 构建19恢复一次头前网络丢失并收敛阶段日志；设备安装与业务结果分项登记。 -->
<!-- [Sync] 2026-10-31: 索引端侧目标编译与原登录认证方案、排障指南和分平台资格；本轮仅文档维护。 -->
<!-- [Sync] 2026-10-31: 当前17共享Admin系统连接池；设备安装/进程与Simulator冷启动通过，真机3项GET503及锁屏分别记录，工作区待修复。 -->
<!-- [Sync] 2026-10-31: 构建16缓冲/原期限修订，设备安装与普通启动、Simulator冷启动读取通过；物理前台及完整任务继续分项验收。 -->
<!-- [Sync] 2026-10-31: 当前iPhone构建15共享系统Admin HTTP，原会话200；锁屏与Simulator、完整任务分别验收。 -->
<!-- [Sync] 2026-10-31: 当前源码全量生产构建13、签名/无线升级及普通启动通过，原数据与描述文件实际有效期分别记录。 -->
<!-- [Sync] 2026-10-31: 公网12补原Product API地址，实际无线安装、数据保留与用量200分列，模型及会话网络范围保留。 -->
<!-- [Sync] 2026-10-31: 构建11保留原Web回调，实际无线升级和Simulator登录关闭通过，设备Locked与业务网络失败分列。 -->
<!-- [Sync] 2026-10-31: 登记公网Admin构建10、实际invalid_redirect及同Client回调兼容发布，安装与账号验收分列。 -->
<!-- [Sync] 2026-10-31: 重新核对构建8九项ntn资源及11项路径/解析器检查，分列表内真机执行、Notion业务及实际Admin来源条件。 -->
<!-- [Sync] 2026-10-31: 当前构建8采用独立Stop恢复，Simulator真实停止/冷恢复通过；真机无线升级与ntn暂存通过，账号网络及CLI资格分列。 -->
<!-- [Sync] 2026-10-31: 当前构建7沿原签名装配、Simulator原Python执行ntn通过；构建6真机启动失败及构建7设备连接缺口分别保留。 -->
<!-- [Sync] 2026-10-31: 补Simulator构建6的RN焦点修复、离线字节码/adhoc签名/覆盖安装与正常业务；原Release设备IPA保持构建5。 -->
<!-- [Sync] 2026-10-31: 补Release保留Metro输入、当前源码离线复现及IPA Hermes逐字节追溯，保留初次验证脚本失败与临时缓存清理。 -->
<!-- [Sync] 2026-10-31: 补当前产品安装包、Simulator制品和Release IPA的ntn九资源核对及产品App原Python直接执行，真实Notion业务分列。 -->
<!-- [Sync] 2026-10-31: 增加产品标识Simulator 0.1.0/5首次安装、原登录和自身Bash/Stop/冷恢复，旧验证标识及设备条件分列。 -->
<!-- [Sync] 2026-10-31: 更新真机3到5无线覆盖、运行目录保留及Locked拒绝启动；增加真实Bash及冷重开证据入口。 -->
<!-- [Sync] 2026-10-31: 新增当前账号/宿主Release构建5及Wi-Fi设备状态，分列Simulator长文/Stop/重开和Notion授权前提。 -->
<!-- [Sync] 2026-10-31: 当前源码Release全量构建与开发签名0.1.0/4通过；设备原构建3、原env和真实业务资格保持。 -->
<!-- [Input] 当前 frontend React Native 工程、端侧运行库、Xcode 与已登记 iPhone。 -->
<!-- [Output] iPhone 开发安装、临时包检查、TestFlight 与 App Store 发布操作。 -->
<!-- [Pos] iOS 实机操作手册；架构与历史资格归 mobile-app-release.md 和跨端设计。 -->
<!-- [Sync] 2026-10-30: 核对现行工程、开发签名与设备，补充临时包实测和正式发行前提。 -->
<!-- [Sync] 2026-10-30: 用户确认设备已信任；真机日志定位根目录 Debug dylib 漏签，补充显式签名和逐文件校验。 -->

# iPhone 打包、安装与发布操作手册

最新设备采用见[构建24覆盖安装与普通启动](#2026-11-02-构建24覆盖安装与普通启动)；下方旧小节保留对应阶段的制品与回执。

认证职责和状态见[目标编译与认证合同](../design/multi-platform/mobile-runtime-architecture.md#端侧登录认证与目标编译合同2026-10-31)，后续问题按[端侧认证排障指南](mobile-auth-troubleshooting.md)逐层取证。本手册保留每次制品和实际验证原文；本轮文档整理未复测设备/API。

## 适用范围

最新设备版本采用[构建24覆盖安装与普通启动](#2026-11-02-构建24覆盖安装与普通启动)，各日期记录保留原阶段范围。

当前工程入口为 [`frontend/ios/InkMemory.xcworkspace`](../../frontend/ios/InkMemory.xcworkspace)，Scheme 为 `InkMemory`。React Native 主界面从 [`index.native.js`](../../frontend/index.native.js)装配；Swift 加载包内 `main.jsbundle`，原 Python 后端与 Node/Next 运行库一起进入安装包。正常网页登录和保留的 DOM 文档继续使用现有适配。

架构与历史资格见[移动发布设计](mobile-app-release.md)，页面取舍见[统一工程设计](../design/multi-platform/react-native-web-project-structure.md)。旧 `mobile/ios/` 路径按历史记录解释，当前操作使用 `frontend/ios/`。

| 交付方式 | 必需条件 | 制品与安装方式 |
| --- | --- | --- |
| 自己的 iPhone 开发测试 | Xcode Apple Account、开发证书及私钥、含设备 UDID 的开发 profile、Developer Mode | 开发签名 `.app`，由 Xcode 或 `devicectl` 安装 |
| 登记设备分发 | Apple Developer Program、登记设备、匹配的证书和 profile | 导出对应设备的 `.ipa`，通过 Apple 工具安装 |
| TestFlight | Apple Developer Program、App Store Connect 应用与上传角色、合格 SDK | Release Archive 上传后由 TestFlight 分发 |
| App Store | TestFlight 所需条件、商店材料、隐私及审核资格 | 正式应用标识的合格构建，经审核发行 |

## 一、设备与签名准备

1. Mac 安装完整 Xcode，在 `Settings > Accounts` 登录 Apple Account。
2. 打开 workspace，在 `InkMemory > Signing & Capabilities` 选择 Team。应用标识、证书、profile 与 Team 必须匹配。常规开发可使用 Automatically manage signing。
3. 首次用数据线连接 iPhone，完成手机的“信任此电脑”，在 Xcode 设备窗口完成配对。后续可使用已配对的 Wi‑Fi 连接。
4. iPhone 打开“设置 > 隐私与安全性 > 开发者模式”，按系统提示重启，再确认启用。设备密码由设备持有人输入。
5. 安装和启动时保持设备可用；锁屏、未配对、profile 到期分别按对应提示处理。

仓库根目录检查：

```bash
xcodebuild -version
xcrun devicectl list devices
security find-identity -v -p codesigning
```

私钥保留在 Keychain，禁止导出到仓库、日志或安装包。遇到 `codesign` 的 Keychain 访问提示，输入的是该钥匙串密码；核对访问者为本次 Apple 签名工具后，由本人授权，保留整个钥匙串的访问保护。

Personal Team 的开发 profile 通常在签发后七天到期，到期需重新配置签名、构建并安装。TestFlight 和商店发布需要 Developer Program 资格。[Apple 账户说明](https://developer.apple.com/help/account/basics/about-your-developer-account)、[Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)，查阅日期：2026-10-30。

## 二、准备安装包

### 资源与配置

- 依赖以 `frontend/pnpm-lock.yaml` 和 `frontend/ios/Podfile.lock` 为准。已有依赖和运行库可直接复用，避免一次设备启动重复安装和初始化。
- Python、Node、Guest、字体资源需已按工程原脚本准备完成，缺少资源时按明确错误补齐。
- 原 Next standalone 位于 `frontend/ios/Next/build-source/.next`。Web运行源码变化后，顺序执行下列命令；准备目录由构建共享，避免与其他任务并行覆盖。

```bash
python3 frontend/ios/scripts/prepare-next.py
pnpm --dir frontend/ios/Next/build-source build
python3 frontend/ios/scripts/bundle-next.py --verify-sources
```

- `prepare-next.py`记录checkout与prepared输入摘要；`bundle-next.py`在修改应用资源前拒绝缺失或过期来源，并在包内保留`source-receipt.json`。并行构建可将`INK_IOS_NEXT_ROOT`设为`frontend/ios/`内本轮具名目录，准备、编译和Xcode资源阶段使用同一值。`bundle-next.py`的输出为`TARGET_BUILD_DIR/UNLOCALIZED_RESOURCES_FOLDER_PATH/next`；调用方使用应用资源根，服务从该`next/mobile-manifest.json`的`serverEntry`启动。验证前核对该实际根的来源摘要与本轮准备回执。写作纠偏的分项资格见[专项记录](../exec/writing-mobile-layout-review-20261101.md#安装资源纠偏与模拟器验证)。
- Xcode 资源阶段执行 [`bundle-python.py`](../../frontend/ios/scripts/bundle-python.py) 和 [`bundle-node.py`](../../frontend/ios/scripts/bundle-node.py)，装配原后端、Next、字体和普通 env。原生 JS bundling 使用 `index.native.js`；包内资源支持脱离 Metro 启动。
- `build-rn-ios.sh` 是完整准备入口，包含依赖安装和 `pod install`。缓存齐备时使用下方 Xcode 命令。
- 当前脚本复制 `backend/.env` 与 `frontend/.env.local`。本机临时包按当前配置使用；对外分发前必须逐键审查，服务端凭证与高权限共享秘密留在服务端，签名材料保留在 Keychain/受控 CI。本机临时包限定本次开发设备使用。

### 服务地址

手机的 `localhost` 指向手机。Dream BFF 与 Python 使用手机 loopback；Mac Admin 的 `localhost:3000` 无法由物理 iPhone 直接访问。

物理设备使用可达的 HTTPS Admin，沿用 `INK_ADMIN_DREAM_BASE_URL`、`INK_ADMIN_DREAM_TRANSPORT_BASE_URL` 和 `INK_GATEWAY_BASE_URL`。本机 Admin 联调需提供符合现有认证规则的 HTTPS 入口。当前 BFF 的 `exactServerOrigin` 只接受 HTTPS 或 HTTP loopback；`http://Mac-IP:3000` 会触发配置拒绝。保持原来源、issuer、resource、Cookie、CSRF、PKCE 和回调校验。

环境文件正文、密码、Cookie、授权码与 service secret 退出日志。临时包的地址调整只作用于该包副本，源配置保持；修改资源后重新签名。

### 开发构建与安装

打开 workspace，选择 Scheme `InkMemory` 和已连接的 iPhone，执行 `Product > Run`。Xcode 使用当前 Team 签名并安装，无需先生成 IPA。

命令行等价操作，变量由本轮设备和工作目录确定：

```bash
export IOS_DEVICE_UDID="填写设备 UDID"
export IOS_DERIVED_DATA="填写本轮允许使用的缓存绝对路径"

xcodebuild \
  -workspace frontend/ios/InkMemory.xcworkspace \
  -scheme InkMemory -configuration Debug -sdk iphoneos \
  -destination "id=$IOS_DEVICE_UDID" \
  -derivedDataPath "$IOS_DERIVED_DATA" -jobs 2 \
  ENTRY_FILE=index.native.js COMPILER_INDEX_STORE_ENABLE=NO build

export IOS_APP_PATH="$IOS_DERIVED_DATA/Build/Products/Debug-iphoneos/InkMemory.app"
codesign --verify --deep --strict "$IOS_APP_PATH"
xcrun devicectl device install app --device "$IOS_DEVICE_UDID" "$IOS_APP_PATH"
xcrun devicectl device process launch --device "$IOS_DEVICE_UDID" com.inkmemory.mobile
```

上述构建使用工程签名配置。签名关闭的中间 `.app` 需先签入全部嵌套 framework 及应用根目录的动态库、复制匹配 profile，再使用对应 entitlements 签名主应用，才能安装到真机。Xcode 16 Debug 包可能包含 `InkMemory.debug.dylib` 与 `__preview.dylib`；两者均需单独签名并执行 `codesign --verify --strict`，最后重新签名主应用。`codesign --verify --deep` 无法单独证明所有根目录动态库已签名。常规操作由 Xcode 完成签名。

更换 Bundle ID 时，同时核对 profile、MCP URL scheme 和包内 `INK_CLAUDE_MCP_OAUTH_REDIRECT_URI`。同 Bundle ID 安装按升级处理并保留应用容器，开发测试期间保留现有数据。

## 三、临时包检查

| 检查项 | 预期结果 | 执行前提 |
| --- | --- | --- |
| 安装与普通启动 | 安装成功，进程启动，无即时退出 | 匹配签名、已登记设备、Developer Mode |
| 本地运行库 | 包内 Python、Node/Next 就绪，原会话入口可读取 | 完整资源；实际设备日志或页面回执 |
| 正常网页登录入口 | 原登录页面可打开，选项加载成功 | 手机可达 Admin HTTPS；简单检查无需提交密码 |
| 更多及资源页面 | 当前账号可进入五项更多、设置与资源页，返回可用 | 当前正常登录；页面回执单独记录 |
| 真实任务 | 原业务完成，历史及正常 Admin 记录可复核 | 明确账号、模型及任务验收范围 |

只将实际执行的行登记为通过。真实任务、MCP 第三方授权、升级、前后台恢复与完整资源验收继续按原矩阵执行。

## 四、TestFlight 与 App Store

1. 使用 Apple Developer Program Team，在 App Store Connect 建立同 Bundle ID 的 iOS 应用，确认上传权限、版本与递增构建号。
2. 使用符合当期上传要求的 Xcode/SDK，核对最低部署目标与运行库支持范围。本机 Xcode 16.4 用于本次开发安装；Apple 自 2026-04-28 起要求上传的 iOS 应用使用 iOS 26 SDK 或更新版本。[官方 SDK 要求](https://developer.apple.com/news/?id=ueeok6yw)，查阅日期：2026-10-30。
3. 完成真实账号、完整端侧业务、资源授权、升级和设备回归；核对运行库、插件与字体的许可证和分发条件。
4. 核对隐私清单、权限用途、隐私政策、账户删除、适用的第三方登录与数字内容支付要求。Python/Claude、插件和命令运行能力按审核条款确认；动态代码和下载扩展核对 [App Review Guidelines 2.5.2](https://developer.apple.com/app-store/review/guidelines/#software-requirements)，查阅日期：2026-10-30。开发签名回执覆盖开发测试范围。
5. Xcode 选择真机通用目标，执行 `Product > Archive`。Organizer 核对归档后，选择 `Distribute App > App Store Connect`，验证并上传。处理完成后在 TestFlight 添加测试人员，外部测试按 Apple 审核流程执行。
6. 测试通过后填写商店材料、地区与审核说明，提交 App Review；审核通过后按选定方式发行。账号注册、付费、法律协议、上传、审核和正式发布本轮均未执行。

```bash
export IOS_ARCHIVE_PATH="填写本次归档绝对路径/InkMemory.xcarchive"
xcodebuild \
  -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory \
  -configuration Release -destination 'generic/platform=iOS' \
  -archivePath "$IOS_ARCHIVE_PATH" archive
```

留存 `.xcarchive`、dSYM、导出 IPA、日志、源码版本和未提交改动摘要、依赖锁摘要、Next/Hermes 摘要、SDK、应用 version/build、Team 与 profile 到期时间。按对应渠道导出 IPA，开发 profile 的设备和有效期限制持续生效。失败重试使用已核对归档；修复代码后生成递增构建。暂停发行、客户端修复版与服务端回退分别处理，保留已安装客户端兼容。

Apple 操作参考，查阅日期 2026-10-30：[登记设备分发](https://developer.apple.com/documentation/xcode/distributing-your-app-to-registered-devices)、[测试与正式分发](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)、[归档与 Organizer](https://help.apple.com/xcode/mac/current/en.lproj/dev1bc569500.html)。

## 五、2026-10-30 临时包执行记录

执行范围为开发临时包、设备安装和普通启动尝试；本机服务、业务源码、源 env、账号与数据库保持。设备为通过 Wi‑Fi 配对的 iPhone 16，iOS 18.0.1；Developer Mode 为 enabled，设备已包含在现有 profile 中。

| 项目 | 本轮结果 |
| --- | --- |
| 应用 | `Ink iPhone Test`；`com.inkmemory.mobile`；版本 `0.1.0`；构建号 `2` |
| 构建 | Xcode 16.4，iphoneos arm64，Debug，复用 `frontend/ios/build/RNW`，耗时 108 秒，退出 0 |
| 资源 | Next Build ID `PuwYVswBXxLYmnb4tnQjz`；Hermes SHA-256 `e4e426fa35bf509162b4ba7b43d33774a7976d34102461b87315bed3eb53241a` |
| 签名 | 复用已有 Apple Development 身份与开发 profile；83 个 framework 和主应用签名完成；深层严格校验退出 0；私钥未导出 |
| 网络配置 | 仅临时包副本的现有 Admin/Gateway transport 键采用原配置的 `https://ink-admin.suoxya.com`；源 env 的本机 3000 设置保留 |
| 安装 | `devicectl device install app` 退出 0，返回已安装的 bundle ID 与设备容器路径 |
| 首次启动 | `devicectl device process launch --console` 退出 1；CoreDevice 10002，底层 FBSOpenApplicationErrorDomain 3；系统拒绝原因为签名、entitlements 或 profile 信任校验 |
| 设备 UI | iPhone 镜像要求本人输入 Mac 登录密码；本轮未输入或修改任何密码 |
| 运行与业务 | 尚未取得普通启动、端侧运行库就绪、登录页或资源页面回执；真实任务、模型调用和商店提交均未执行 |

设备端下一步：打开“设置 → 通用 → VPN 与设备管理”，检查本次开发者 App 的信任状态。系统显示确认或“允许并重新启动”时，由持有人完成；已信任时继续核对设备端拒绝原因。保留全部系统签名和权限校验。完成后点击主屏幕的 `Ink iPhone Test`，或重试上方普通启动命令，按检查表补充实际回执。

本次 profile 到期时间为 **2026-11-01 00:48:40（Asia/Shanghai）**，对应 UTC 2026-10-31 16:48:40；到期后重新配置开发签名并安装。

临时 IPA：`frontend/ios/build/InkMemory-iPhone-Test-20261030.ipa`，143,345,880 字节，文件权限 0600；SHA-256：`35e3066908b7e5aaa53570f030a97e9f01d1d924a34b35d6322c0942342d8ca2`。开发 profile 限定已登记设备，本地普通 env 随包携带，限定本次自用测试。

具体命令与回执目录：`/tmp/ink-iphone-temporary-20261030/`。构建使用第二节命令，并附加 `CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO` 生成中间包；随后复制到本轮 `Payload/InkMemory.app`，调整临时显示名、构建号和上述传输地址，使用已有 profile 与 Keychain 身份完成嵌套及主应用签名。

| 操作 | 实际命令入口 | 退出码与关键结果 |
| --- | --- | --- |
| 设备发现 | `xcrun devicectl list devices`、`device info details`、`device info lockState` | 0；connected、localNetwork、paired、Developer Mode enabled |
| 真机包生成 | `xcodebuild -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory -configuration Debug -sdk iphoneos -destination id=<本轮设备UDID> -derivedDataPath frontend/ios/build/RNW -jobs 2 … build` | 0；`BUILD SUCCEEDED`，无依赖安装和测试执行 |
| 签名与校验 | `codesign --force --sign <本机已有身份> …`；`codesign --verify --deep --strict …/InkMemory.app` | 0；签名与 profile 匹配 |
| IPA 装配 | `ditto -c -k --keepParent Payload <本轮IPA路径>` | 0；产物摘要见上文 |
| 安装 | `xcrun devicectl device install app --device <本轮设备> …/Payload/InkMemory.app` | 0；设备返回安装成功 |
| 启动尝试 | `xcrun devicectl device process launch --device <本轮设备> --console com.inkmemory.mobile` | 1；系统启动安全校验拒绝，等待设备端核对 |

`build-receipt.json`、`candidate-receipt.json`、`sign-receipt.json`、`ipa-receipt.json`、`install.json`、`launch.json` 保留首包原始回执。7 个构建输入摘要前后一致。下节登记用户确认和补签修复后的当前结果。


### 用户确认与根目录动态库补签

用户确认设备已经信任开发者 App。再次启动时，`devicectl` 返回 0，进程立即结束；设备控制台出现 `dyld: Library not loaded: @rpath/InkMemory.debug.dylib`，具体原因为该动态库缺少 cdhash、处于未签名状态。该回执说明命令退出 0 需要结合应用退出信息和设备日志判定；首包的深层签名检查未覆盖该遗漏。

修复仅作用于临时包副本：对 `InkMemory.debug.dylib`、`__preview.dylib` 分别签名并严格校验，将构建号改为 `3`，重新签名主应用后覆盖安装。业务源代码、源 env、Admin、数据库及运行库行为保持。

| 修复检查 | 实际结果 |
| --- | --- |
| 两个根目录 dylib 签名及逐文件校验 | 均退出 0 |
| 主应用重新签名与深层严格校验 | 均退出 0 |
| `devicectl device install app` | 退出 0；设备接受构建号 3 |
| `devicectl device process launch --console` | 返回启动成功，保持控制台观察；普通 App PID 为 6656 |
| 设备进程复核 | 约 3 分钟后 `device info processes` 退出 0，同一 PID 仍存在 |
| 运行库目录元数据 | `device info files` 退出 0；生成 `InkMemory/runtime/node-6656.json` 与 Guest、插件运行库目录；端点内容和凭证未读取 |
| 动态库错误 | 修复后的控制台无 `Library not loaded` |
| 可视检查 | iPhone 镜像仍要求 Mac 登录密码；未输入密码，登录页、更多与资源页面保持未验收 |
| 真实业务 | 登录提交、模型调用、资源授权与数据写入均未执行 |

当前 IPA 保持原路径 `frontend/ios/build/InkMemory-iPhone-Test-20261030.ipa`，内容已替换为修复后的构建号 **3**；143,687,149 字节，0600。当前 SHA-256 为 `99bfc1951f98402aaf76b8bd6466093f733939a066bdd6add920b3e3313fe567`；上节构建号 2 的大小及摘要归首包历史。

修复回执：`sign-r2-receipt.json`、`install-r2.json`、`device-console-r2.log`、`process-list-r2-running.json`、`process-list-r2-final.json`、`runtime-directories-r2.json` 和 `ipa-r2-receipt.json`，均位于本轮回执目录。文档本地引用及清单检查、范围内 `git diff --check` 退出 0；本手册新增 Mermaid 图数量为 0。

当前状态：**打包文档与修复 IPA 已完成；真机安装及普通进程启动检查通过；可视页面、完整端侧业务与正式发布未验收**。


## 六、2026-10-31 Release开发包

本阶段[Release开发IPA构建5](../../frontend/ios/build/InkMemory-Release-device-20261031-b5.ipa)：`com.inkmemory.mobile`、0.1.0/5，142,022,903字节、0600；SHA256 `e7948d126a825ae952a1caeb8778ef36c74f938f28246e479b82f4c951407efa`。当前App target复用前阶段锁定Release依赖，重编当前Swift、账号回调与宿主资源，xcodebuild退出0、43.27秒。83个framework及主应用的既有开发签名严格校验通过。Next BUILD_ID `VGOr-pi9sPcnIYSQAoWSj`；固定ntn0.15.1/MIT及原Python/Node/Next随包。

当前iPhone16/iOS18.0.1为localNetwork、paired、tunnel connected、Developer Mode enabled，现已从构建3通过Wi-Fi覆盖升级到构建5，安装退出0、27.63秒。升级前后运行目录1,948条路径集合相同、普通文件元数据无变化；10个符号链接元数据的可用性有差异。启动命令返回1，系统以Locked拒绝启动，未尝试解锁。原env的localhost3000需要转换为可达同一正常Admin的有效HTTPS传输配置；既有公网地址当前未匹配本机新BUILD_ID静态文件，登录前提未确认。保持原Client、来源校验和业务权限；本机Simulator继续直接访问正常3000。profile到期仍为2026-11-01 00:48:40 Asia/Shanghai，正式SDK/渠道前提沿第四节。[构建5与真实业务证据](../exec/mobile-app-design-review-20261024.md#2026-10-31-长文停止重开与release构建5)集中维护。

### 前阶段构建4记录

[当前Release开发IPA](../../frontend/ios/build/InkMemory-Release-device-20261031-b4.ipa)：`com.inkmemory.mobile`，0.1.0/4，141,989,805字节，0600；SHA256 `4473faceb2c6a9c0bb3142dcc635ce82db9e3e3947cfaf797d8cae14ec0496c2`。现有workspace与锁定依赖完成新建DerivedData的Release设备构建，2 jobs、278.5秒、退出0。无需修订现行Pods链接配置；未安装依赖。

普通生产`index.native.js`、Next BUILD_ID `5qMhJuDJak0IFMh36ESGg`、当前Dream Python/Node及固定ntn0.15.1/MIT随包。83个framework和主应用复用现有开发身份及profile签名，逐项严格校验通过。该包采用Release主程序，无根目录Debug dylib；前节Debug补签历史保留原范围。

当前iPhone16/iOS18.0.1为wired、paired、connected，Developer Mode enabled。原安装构建3保留，本轮未安装4；当前包普通env使用本机Admin3000。物理设备访问Mac服务需可达的原HTTPS入口，具体规则沿第二节，来源校验及源env保持。当前普通Simulator继续原loopback与正常账户业务，Release真实启动/登录/任务及升级验收独立执行。

开发profile于2026-11-01 00:48:40 Asia/Shanghai到期，安装前重核有效期。该包限定现有开发设备；当前SDK18.5与[Apple SDK26上传要求](https://developer.apple.com/news/?id=ueeok6yw)分列，查阅2026-10-31。当前开发签名IPA、真实设备验收、正式Archive、TestFlight和商店状态分别登记。完整命令见[本轮执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-release设备包构建资格)。
<!-- [Sync] 2026-10-31: 分列普通Simulator账号回调采用、ntn摘要和本地Notion授权缺口，原Release IPA保持。 -->


## 七、2026-10-31普通Simulator账号回调采用

普通`com.inkmemory.loginntn`已采用当前BFF、Native账号会话及原env目标映射；Next BUILD_ID `VGOr-pi9sPcnIYSQAoWSj`。原Client的两个App URI已沿正常Admin目录发布并读回；原Web地址、PKCE及权限保持。`bundle-node.py`映射包内既有redirect键，`host.cjs`向Next保留该配置。原密码表单实际完成App回调并关闭弹窗，系统授权进入原Admin与取消返回通过；既有Thread真实Chat完成且正常Gateway settled，冷启动保留同一消息和账户。

该普通包为Simulator调试宿主与优化Hermes，前节真机Release IPA保留原阶段摘要。ntn/MIT继续匹配固定锁，当前包4项端侧XCTest重跑通过；普通资源范围读取返回原授权缺失反馈，本应用授权文件数为0，原连接配置及7项范围保持。真实Notion授权、读取、同步、Agent与真机独立验收。[命令、退出码、失败及安装资源证据](../exec/mobile-app-design-review-20261024.md#2026-10-31-普通包账号回调采用与notion授权核对)集中维护，当前全目标保持进行中。

最新普通Simulator的两次长文请求分别完成与Stop取消，正常Gateway均settled；进程重开后11用户/10助手、最后cancelled与running=false保持，原对话恢复Send。当前ntn原授权准备成功，用户确认前poll触发原超时；本应用真实授权、资源读取与同步仍待验收。上述结果与开发Release构建5的资源/签名检查分别计入对应范围。

当前普通Simulator完成一次真实Bash业务和最终回复，原消息process返回1个Bash、output-available及实际输出标记；两条正常Gateway均completed/settled。普通App冷启动后12用户/11助手、同一工具过程/最终回复保持。具体命令和发布前提见[无线升级与业务记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-无线升级构建5与真实bash业务)。

## 八、2026-10-31产品Simulator首次安装与业务

该阶段Simulator使用[产品应用包](../../frontend/ios/build/InkMemory-Simulator-20261031-b5.app)，标识`com.inkmemory.mobile`、版本0.1.0、构建5，iPhone16 Plus/iOS18.6 arm64。原workspace编译通过，原index.native.js生产Metro/Hermes通过；Next的717项源文件与锁保持一致，原Client及已登记`com.inkmemory.mobile.auth:/auth/callback`采用。包内私有配置通过原打包阶段生成，源env修改0；当前包限本机开发验证，外部分发条件继续按前节执行。

主Agent以`codesign --force --sign -`执行Simulator本地签名，严格校验通过。普通产品副本排除具名XCTest插件及7个测试框架，原编译缓存和前阶段验证制品保留；83项运行框架保留，85个Mach-O文件动态库依赖检查通过。此签名方式对应Simulator，本手册的iPhone开发签名与登记设备分发仍使用各自证书/profile。

首次安装命令`xcrun simctl install 120A4231-E08B-422F-A45E-08BDB72937D7 frontend/ios/build/InkMemory-Simulator-20261031-b5.app`退出0、6.89秒；13项实际安装资源与制品一致。启动使用同设备的`simctl launch --console ... com.inkmemory.mobile`，当前App自身拥有5173，正常Mac Admin/Gateway3000与PG54329保持。前阶段验证App已停止，其数据inode和23/98字节文件保留；跨应用Cookie、凭据和运行目录复制0。

产品实测：原网页登录弹窗左上关闭/重开、密码成功关闭及主页；原账号正常首页创建自身Thread，首轮Bash completed、第二轮流式正文经原Stop cancelled，3条正常Gateway记录均settled。产品冷启动保留账户、自身2用户/2助手、Bash过程和已停止正文；原生Decks和五项More导航实际到达。具体源摘要、命令与范围归[产品执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-产品标识simulator首次安装与真实业务)。物理Release、完整Google/Notion/MCP业务及正式发行继续分列。

## 九、2026-10-31产品包ntn专项验证

当前实际安装的产品Simulator App、[Simulator制品](../../frontend/ios/build/InkMemory-Simulator-20261031-b5.app)及[Release IPA](../../frontend/ios/build/InkMemory-Release-device-20261031-b5.ipa)均核对为`com.inkmemory.mobile`、0.1.0/5。固定ntn0.15.1、MIT、manifest、三个Node执行适配和三个Python Notion模块共9资源逐字节一致；六个执行适配文件匹配当前源码。IPA摘要保持`e7948d126a825ae952a1caeb8778ef36c74f938f28246e479b82f4c951407efa`。

ntn为10,930,616字节的ELF AArch64，沿既有App内Linux ARM64命令解释器执行。锁定SHA256为`faee5c2227abea0ea401bd27689a9d150d32402d4240f349619710fd621824fc`；MIT为1,074字节，摘要匹配锁文件。App私有guest目录内的实际执行文件匹配该摘要，常规文件、无符号链接、权限0755。

当前产品App25378内原`notion.auth._run_ntn_command`直接执行`--version`与`--help`，两项退出0，版本0.15.1及Usage匹配；标准输出11与1,584字节、标准错误均0。驱动退出0、7.043秒，App未重启，临时home和观察文件已清理。本轮网络、凭据读取、模型调用、重建及安装均0。命令、原始日志及范围归[专项执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-产品包ntn专项验证)。

当前结论：Simulator产品包内CLI解析和执行通过，Release IPA资源核对通过。真机ntn执行、有效Notion授权、资源读取、同步及Agent使用继续分别验收；既有HTTP/HTTPS四项技术回执保持原测试宿主范围，真实Notion业务状态保持待验收。

## 十、2026-10-31Release前端来源追溯

当前构建5的原Xcode产品目录保留Metro JS中间文件。以当前源码、原`index.native.js`、iOS、`dev=false`、`minify=false`和原本地config命令重新打包，取得8,591,594字节JS，SHA256 `2c3547721b202e327e0339f3cf055b29504145be8ea01bd70b920397e46e5d63`，与原中间文件逐字节相同。原Hermes参数编译该中间文件，输出5,727,468字节，SHA256 `14ec457bd5063291d7f7293f7b1e0c9f329b9eb91e7b21f73feb23a0943709e7`，与当前IPA成员一致。

该证据覆盖当前源码→Release Metro输入→Hermes→IPA成员。IPA本体保持第六节路径、字节及摘要；原生重编译、签名、安装和App重启均0。首次验证脚本缺少cwd与本地config参数，触发隐式npx临时下载并失败；修正为显式frontend目录及已有本地工具后离线通过，本轮具名npx目录已按创建时间、版本和无活跃引用核定后清理，共享npm内容缓存保留。原始失败、命令与剩余资格归[来源与运行实例记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-release前端来源与运行实例核对)。

同一当前源码按产品Simulator的`minify=true`参数离线打包，取得3,745,775字节JS、SHA256 `37148b65ddd0edd16133223d6f225ce302c640d2edeb904a052fd340a0e0461c`，与已验收产品Simulator的保留输入逐字节一致。该对照补齐两类制品的当前源码来源；各平台执行资格继续分别记录。

App实例及原HTTP执行位置归[现行运行库架构](../design/multi-platform/mobile-runtime-architecture.md#2026-10-31-ios现行实例与启动合同)。来源校验属于制品技术验证；真机完整业务、第三方授权、发行账号及SDK要求继续按原矩阵执行。


## 十二、2026-10-31 Simulator构建6与输入焦点修复

该阶段[Simulator构建6](../../frontend/ios/build/InkMemory-Simulator-20261031-b6.app)为`com.inkmemory.mobile`、0.1.0/6，已覆盖安装到原iPhone16Plus/iOS18.6 Simulator。它由留存构建5通过APFS clone装配，仅更新当前源码Metro/Hermes、Info构建号和adhoc主签名；原生重编译与Next资源重建均0。原生库、Python/Node/Next/Claude、固定ntn及回调地址保持原构建资源。设备Release IPA仍为前述构建5，输入焦点修复尚待装配进入设备制品。

当前HBC为5,673,355字节，SHA256 `aa9c8477f4dd895cd6541fddfd0b92f23c83fe6c919764c868bd1e682911aefb`。离线Metro、原Hermes、adhoc签名、deep/strict校验、simctl覆盖安装及安装后摘要/签名检查均退出0。覆盖安装后data路径UUID变化，data inode183813951保持，正常Cookie与自身Thread恢复。原构建5 App和Release IPA保留。

实际软件键盘输入→切换Decks/More收起键盘→返回保留长草稿→用户点击再次显示键盘通过。原正常账户新增一次公开短Chat，助手completed、Gateway completed/settled，最终8用户/6助手、原取消与完成结果保持。所有正常记录保留，未提交的具名布局草稿已清空；当前键盘关闭、空输入、Full access保持。完整命令、故障截图、技术与业务范围归[执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-软件键盘与持久输入焦点修复)。

当前物理iPhone通过localNetwork连接回执退出0；设备包采用、有效HTTPS Admin连接、真机业务、Notion授权和正式渠道条件继续分别验收。Simulator焦点与业务回执保持其平台范围。

## 十三、2026-10-31构建7与ntn启动修复

当前[设备开发IPA构建7](../../frontend/ios/build/InkMemory-Release-device-20261031-b7.ipa)为`com.inkmemory.mobile`、0.1.0/7，142,521,540字节、0600，SHA256 `47808cc8c6ff1d0af61fa0e55386b1a596a0a17af7b8413b4b71ec64df394203`。当前[Simulator构建7](../../frontend/ios/build/InkMemory-Simulator-20261031-b7.app)已经覆盖安装；原构建5和6制品保留。当前状态采用本节，下方各日期章节保留对应阶段原文。

构建6设备IPA已通过原开发签名和83项framework校验，并经Wi-Fi覆盖安装退出0、29.503秒；安装前后运行目录1,948项元数据相同。普通launch返回PID7778，随后完整进程清单确认退出。控制台重开退出1、1.582秒，实际记录`IOS_NOTION_CLI_PATH_INVALID`和Node退出1。该次失败归Node启动校验；前阶段Locked记录保留原范围。

[host.cjs](../../frontend/ios/runtime/host.cjs#L32)先规范化Native endpoint父目录，再拼接固定guest目录。Notion子目录及目标文件的符号链接拒绝、摘要和执行权限检查保持。原宿主启动片段的路径fixture先复现退出1，修复后5项通过；既有resolver6项及Node语法均退出0。构建7仅更新宿主、构建号和主签名，沿构建6的HBC；无原生、Metro或Next重编译。

设备App与IPA逐项匹配7,648对象，Simulator与前版匹配7,512对象；变化限Info、host和根签名，83项framework、原profile、entitlements及两项env字节保持。IPA全归档16,575项已分类校验，未知条目0。构建7深度严格签名验证和ZIP CRC均通过，摘要已追加原`SHA256SUMS`。

构建7 Simulator通过原`notion.auth._run_ntn_command`运行包内`--version`和`--help`，两项退出0，输出11及1,584字节、stderr0；固定ntn0.15.1为10,930,616字节，实际暂存文件摘要匹配、普通文件、0755。临时空home和观察文件已清理。普通入口恢复原账户及自身Thread的8用户/6助手、最后completed26字符与原正常Gateway结算。本轮模型调用和Notion API请求0，完整Notion授权/读取/同步继续待验收。

构建7设备候选尚未安装：准备安装前CoreDevice报告设备不可达，后续清单为paired、tunnel unavailable、Developer Mode enabled。设备保留构建6；构建7真机修复效果和完整业务待连接恢复后执行。原profile到期时间为2026-11-01 00:48:40 Asia/Shanghai；当前SDK18.5，App Store上传仍须满足[Apple SDK要求](https://developer.apple.com/news/?id=ueeok6yw)及原渠道前提，查阅日期2026-10-31。代码/制品检查、Simulator执行、真机执行及正式发行分别登记。精确命令与失败记录归[本阶段回执](../exec/mobile-app-design-review-20261024.md#2026-10-31-真机ntn启动路径修复与构建7)。

## 十四、2026-10-31构建8与停止恢复

当前[设备开发IPA8](../../frontend/ios/build/InkMemory-Release-device-20261031-b8.ipa)为`com.inkmemory.mobile`、0.1.0/8，142,521,558字节、0600，SHA256 `c63e17649cd5894aa7cc2d045e3880d6b73f64114245c6025043017dbd07baec`；当前[Simulator构建8](../../frontend/ios/build/InkMemory-Simulator-20261031-b8.app)已经覆盖安装。HBC为5,673,334字节，SHA256 `d85fb52f1552686475c3d3268a92a657c031f76e0a3071704825e74f3114c6c0`。原5/6/7制品保留；各日期章节采用各自阶段范围。

构建8仅更新Native Stop读取所有权、当前Metro/Hermes、构建号及主签名。原运行库、Next、ntn/MIT、2项env、profile及83个framework保持；全对象/归档、源码source map、可执行模式与符号链接审计通过。原生及Next重编译0，既有开发身份/entitlements继续使用，原profile到期与正式SDK/账号前提保持。

产品Simulator通过正常Claude/Bash查询包内ntn0.15.1，原process为output-available；首个泛称Notion CLI请求误用notion的结果保留。构建7真实Stop后服务端cancelled/idle、页面仍Stop，原Hook新增延迟取消reader回归先RED；构建8改为回执获准后结束旧读取代次并独立查询原状态。新增用例及完整31项会话回归、双TS类型、Metro/Hermes/签名均退出0。

构建8真实正文输出期间原Stop，页面恢复空输入/禁用Send，原messages/status为cancelled、7,985字符、running=false，正常Gateway cancelled/settled。普通冷重开期间无调试器，原历史入口恢复12用户/10助手、ntn工具结果及两条停止正文；8条保护消息按ID/状态/长度保持。阶段共4次UI提交、6条唯一正常Gateway记录均settled；原账户/模型/权限保持，Notion API和凭证正文读取0，观察文件清理。

设备无线连接恢复后，构建8由6覆盖升级，退出0、29.043秒；首次启动前1,949项运行目录元数据相同。普通console启动PID7839，Next在314ms就绪，ntn实际暂存为10,930,616字节普通文件、0755，设备复制出的代码字节匹配固定SHA256 `faee5c2227abea0ea401bd27689a9d150d32402d4240f349619710fd621824fc`。原路径拒绝未复现。端点文件仅检查0600及存在性，正文读取0。

该真机记录覆盖安装、Node/Next启动和ntn暂存字节。当前包访问手机localhost3000的Admin service-token请求为ECONNREFUSED；完整Python/CLI执行、正常账号及Chat业务继续待验收。物理CLI资格驱动未取得可用调试上下文，目标曾显示platform=host/state=connected，随后为no such process，初版驱动的PYTHON_NOT_READY标签退出解释器状态判断；该诊断阶段原console出现signal9，后续CoreDevice清单显示同包PID7848。未下发新的App重开命令，物理CLI执行计数0；继续使用实际进程/设备回执判断，禁止通过该驱动结果判定Python兼容失败。

[本阶段执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-构建7真实ntn业务与停止恢复修复)提供命令、失败现场、制品及剩余前提。真机需要符合原来源/TLS规则的同一本机Admin入口；完整Notion授权、Google完整授权与正式发布继续分列。

### 构建8的ntn验证范围复核

2026-10-31重新读取上述Simulator制品及设备IPA：两个包内各9项Notion资源逐字节匹配，manifest与`node-dependencies.json`的`notionCli`锁一致；`ntn`为ELF64 AArch64、10,930,616字节、0755常规文件，MIT许可证及摘要匹配。三个Node执行文件与三个Python Notion适配文件匹配当前源码，制品保持构建8。

| 验证对象 | 已取得证据 | 当前范围 |
| --- | --- | --- |
| App与IPA资源 | 两包9项一致；ntn、manifest、MIT匹配固定锁 | 打包资源验证通过 |
| 路径与解析器 | 原staging脚本5项、resolver脚本6项退出0 | 文件路径和DNS配置技术验证通过，脚本执行CLI及网络请求0 |
| Simulator产品App | 前述原Python版本/帮助退出0；正常Claude/Bash得到ntn0.15.1与原process结果 | 包内命令执行通过，复用原阶段业务回执 |
| 物理iPhone | 构建8安装、Node/Next启动及实际ntn暂存摘要/0755 | 真机CLI执行待验收；本轮调试目标保持connected，未达到stopped，执行派发0 |
| Notion账户与业务 | 当前App有效授权、资源读取及同步缺少完整回执 | 真实Notion业务待验收，沿原设置入口和授权流程补齐 |

现有`https://work.suoxya.com`登录页BUILD_ID及路由专用JS字节与当前Mac Admin一致。匿名`/api/auth/get-session`在该别名返回403/`AUTH_BROWSER_ORIGIN_DENIED`，原登记`http://localhost:3000`返回200/null。真机完整登录仍依赖可达且符合原来源规则的同一本机Admin入口；本轮Admin、issuer、Client、来源校验及源env变更0。调试后旧App进程消失，恢复普通启动PID7872，Next在314ms就绪；该进程访问手机localhost3000仍返回`ECONNREFUSED`。精确命令及未完成覆盖归[本轮复核](../exec/mobile-app-design-review-20261024.md#2026-10-31-构建8ntn打包复核与真机执行缺口)。


## 十五、2026-10-31公网Admin构建10与账号回调

阶段记录：本节保留构建10的故障和未采用候选；当前修正版采用第十六节。

用户指定公网Admin为`https://ink-admin.suoxya.com`。该阶段物理iPhone16已安装`com.inkmemory.mobile`、0.1.0/10；设备查询确认安装路径归属该构建。原构建8与其本机服务配置保留，`work.suoxya.com`候选已撤回，源env及本机Admin配置保持。

| 制品或配置 | 当前值与范围 |
| --- | --- |
| 设备IPA | `frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b10.ipa`，142,521,456字节 |
| IPA SHA-256 | `2fc56c2704914f53c14a94f1dcf69ef73df5291f3282b83b1dc3329fc0e60095` |
| 包内Admin transport / Gateway | 原env键均指向`https://ink-admin.suoxya.com`；原Admin base、issuer与resource保持 |
| App账号回调 | `com.inkmemory.mobile.auth:/auth/callback`；既有Client ID及S256保持 |
| Hermes | `d85fb52f1552686475c3d3268a92a657c031f76e0a3071704825e74f3114c6c0`，沿构建8 |
| Team / profile | `45KY254AF7`，设备包含在原开发profile中；到期时间2026-11-01 00:48:40（Asia/Shanghai） |
| 运行位置 | RN、Python、Node、Next、Claude与ntn归App；公网Admin提供原认证、持久化与Gateway |

公网Nginx记录13:28:10、13:29:16两次手机授权请求使用现有`ink-dream-browser-local`及该App回调，随后`/api/auth/error`明确返回`invalid_redirect` / `invalid redirect uri`。用户观察到后台登录页。该故障发生于OAuth回调校验；Dream产品账号继续使用原网页登录，管理账户与管理登录保持独立。公网旧`BrowserSessionService.exchange`还只接受原主Web回调，完整修复需同步原service精确回调集合与同Client目录。

修复沿Admin已有`config.ts`、`BrowserSessionService`、`oauthClientCatalog`及`auth:provision-dream-oauth --browser-redirects`发布入口。当前service主Web回调保留，新增精确App URI；对应公开Client使用既有`native`登记类型，`requirePKCE=true`、原scope、grant、密钥与资源绑定保持。未登记URI继续拒绝；数据库schema、账户、角色和权限修改0。25项定向认证技术合同通过；真实账号、Google与设备业务按后续回执分别验收。

该阶段候选完成Webpack编译，在TypeScript阶段随实例重启中断。后续r2/r3在禁用swap条件下发生OOM，完整构建资格缺失；候选、Client目录apply及服务切换均未采用。原服务14:08恢复200，数据目录保持。密码登录修复收敛为包内恢复已登记Web回调，采用第十六节。精确命令、失败及最终结果归[本次执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-公网admin构建10登录回调修复)。


## 十六、2026-10-31公网Admin构建11与原网页登录恢复

阶段记录：当前设备制品采用第十七节构建12；本节密码登录回执保留原构建范围。

当前[设备开发IPA11](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b11.ipa)为`com.inkmemory.mobile`、0.1.0/11，142,521,598字节，SHA256 `5acdb5f3391fdb9d5705a3279a5c8a25ae925bb8b344a02f7c8a842360d54c7f`。Wi-Fi覆盖安装退出0、27.358秒；设备查询确认构建11，首次启动前运行目录元数据与升级前一致。普通launch退出1，iOS返回Locked；物理设备页面、登录及完整CLI业务待解锁后验收。

构建10将原密码登录回调自动改成公网未登记的App URI，触发`invalid_redirect`。构建11仅恢复原已登记`http://localhost:5173/auth/callback`，Admin transport及Gateway继续`https://ink-admin.suoxya.com`。公开Client、S256、scope、Cookie、CSRF、权限、账户及端侧执行归属保持。包内6,311项核对：变化限回调env、Info构建号、可执行签名及CodeResources；缺失、额外、意外字节和模式差异均0，profile与Hermes保持。Google系统授权需要的私有回调兼容按原设计独立发布和验收，公网采用状态仍待完成。

生产打包脚本`bundle-node.py`删除按bundle identifier自动替换账号回调的步骤，沿普通源env复制账号配置。实际生产资源脚本退出0，前端env逐字节一致、0600，原MCP回调映射和sandbox关闭配置保持，源env修改0。首次验证缺少前置Python阶段创建的`app/`目录而退出1，补齐harness前提后通过；原失败保留。

普通产品Simulator覆盖构建11，数据inode183813951保持。原可见密码表单完成公网授权、exchange200、resolve200；App内原`/auth/session`200、账户匹配和CSRF存在。网络5xx/超时期间原会话检查失败，点击原Try again后登录弹窗关闭，进入RN Chat并显示公网历史。后续既有Thread读取出现503及会话重试反馈，真实模型完成资格需独立回执。原生、Next和前端页面重编译0；Python/Node/Next/Claude继续在App进程运行，Mac业务服务0。

原开发profile到期时间2026-11-01 00:48:40（Asia/Shanghai）保持；本轮证书续期、账号变更和商店提交0。签名、安装、Simulator密码登录、完整真实业务与正式发行分别登记。[交互规则](../design/multi-platform/mobile-ios-interaction.md#公网密码网页登录与配置回调保留)与[精确执行回执](../exec/mobile-app-design-review-20261024.md#2026-10-31-公网构建11恢复原网页登录)为当前依据。


## 十七、2026-10-31公网Admin构建12与Product API配置

阶段记录：当前物理设备采用第十九节构建15，本节保留构建12的验收范围。

当前[公网设备IPA12](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b12.ipa)为`com.inkmemory.mobile`、0.1.0/12，142,521,586字节，SHA256 `9f0cab764a6ebf6b78edbaa938ee55c933c83a08320edf19e05b9cdc9db6a4e8`。设备Wi-Fi升级退出0、26.088秒，apps读回构建12，首次启动前运行目录元数据与升级前一致。普通产品Simulator覆盖12，data inode183813951保持；原11/10/8制品保留。

实际包审计发现构建11的`INK_ADMIN_PRODUCT_API_BASE_URL`仍为`http://127.0.0.1:3000`，原Product客户端会访问设备自身。构建12在包内backend普通env副本中修正该现有键为`https://ink-admin.suoxya.com`。原Product Origin、账号Web回调、Client/S256、scope、权限、Gateway及其他配置保持，源env和业务程序修改0。6,311项归档比较仅backend env、Info构建号及根签名变化；缺失/额外/意外/模式差异0，CRC与deep/strict签名校验通过；原生、Next、Hermes重编译0。

构建12通过同App原用量GET返回200，检查时间范围内新增Gateway记录为空。原系统配置200、原模型与Full access/Workspace保持。该阶段session503/`BFF_ADMIN_UNAVAILABLE`及模型目录503/`GATEWAY_UNAVAILABLE`实际保留，原工作区重试继续执行；完整真实Chat完成资格尚未取得。构建11原密码表单、账户匹配、CSRF及自动关闭的资格保持对应平台/制品范围，当前原回调沿用。物理设备实际页面及完整业务、Google/Notion授权和正式发行分别验收。

既有profile到期2026-11-01 00:48:40（Asia/Shanghai）保持。发布配置须逐个核对[既有HTTP配置清单](mobile-app-release.md#公网端侧包的既有http配置清单)，网络和任务恢复沿原规则。[执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-公网构建12-product-api配置)提供具体命令及失败/恢复状态。


构建12设备运行补充：原`devicectl device process launch`本次退出0、Locked=false，无调试器及强制终止。该回执覆盖普通启动；屏幕、账号及实际CLI业务保持独立。普通Simulator原工作区重试后进入RN Chat主页，旧会话和本次输入所在历史保留，原读取恢复规则继续采用。


构建12追加业务结果：原模型目录重读200且可调用，原会话加载恢复；第二次原UI查询结束后出现会话状态待核对。后续status200/idle，messages超时、inputs/usage503，版本工具结果及完整结算未取得。实际输入/历史保留，完整公网Claude业务保持未完成；已安装和普通启动的资格保持。


## 十八、2026-10-31当前源码构建13与iPhone安装

当前[公网设备IPA13](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b13.ipa)为`com.inkmemory.mobile`、0.1.0/13，142,606,645字节，SHA256 `ecf2e478318d2c6011282ccc48ed505cbf7654d44062de9dd537a5ba5093a0c7`。本阶段从当前工作树重新执行独立Next生产构建及Xcode Release构建，Swift宿主、Metro/Hermes、Python业务源码和Next资源进入新制品；底层锁定Python/Node/Guest运行资源继续复用。既有未提交源码参与本轮构建，本轮新增程序改动0。

`prepare-next.py`、独立`pnpm build`及全新DerivedData中的`xcodebuild ... CURRENT_PROJECT_VERSION=13 build`均退出0；原生构建406.079秒，入口`index.native.js`，安装依赖0。Next BUILD_ID为`7d9jH8rpXR1wr5dGZXg_x`，HBC SHA256为`c079fd4ec4f1fa8f6dbd6daeb01ecd26f25a6fea6dd15817a01a72eb52f0bf52`。包内328份Python源码和3份Node执行适配匹配当前源码，ntn固定0.15.1摘要匹配锁。签名deep/strict及归档CRC通过，归档16,575项。构建前3,161份文件的摘要核对到文档更新前全部保持。

公网制品沿普通env副本配置：Admin Data transport、Product API和Gateway指向`https://ink-admin.suoxya.com`；原`http://localhost:5173/auth/callback`保留。公开Client、原权限、来源校验及其他配置保持。源env、Admin和数据库修改0。

物理iPhone16经Wi-Fi由12覆盖安装13，安装退出0、21.743秒，apps读回0.1.0/13；首次启动前运行目录元数据逐项相同。普通console启动成功，进程8106与已安装路径匹配，内置Next在308ms就绪；无调试器及强制重开。该回执覆盖源码构建、签名、设备安装和启动，完整登录、Claude/Google/Notion业务及商店发行继续独立验收，本轮未发起模型业务验收。

Xcode已使用`-allowProvisioningUpdates -allowProvisioningDeviceRegistration`，实际沿用原Team45KY254AF7及描述文件8a404027-cd3f-4e0a-8b8c-e0aad62dee83，有效期仍至2026-11-01 00:48:40（Asia/Shanghai）。本轮描述文件有效期未延长。精确命令、退出码与设备回执归[本阶段执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-当前源码重建13与手机升级)。


## 十九、2026-10-31工作区读取与系统HTTP适配

阶段记录：当前设备与Simulator采用第二十节构建16，本节保留15的原始成功与失败。

当前物理设备为[开发IPA15](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b15.ipa)，`com.inkmemory.mobile`、0.1.0/15，142,623,150字节，SHA256 `6e2431f3c2197764c5e371ee40452dce6008803eae884b0023b42defd03752bd`。构建13全新DerivedData作为增量基础，Swift/Objective-C/C++重新编译，Node/Python资源重新装配；Next BUILD_ID与Hermes摘要沿第十八节。329份Python源码与4份Node平台文件逐项匹配，依赖安装0；deep/strict签名和CRC退出0。

原构建13普通启动后，工作区会话读取发生`UND_ERR_CONNECT_TIMEOUT`。构建14诊断继续记录会话503、历史504；原密码表单协议经公网Admin完成原PKCE交换、resolve/profile200及登录弹窗自动关闭，真机RN主界面到达“新建对话”。该项为公开网页登录协议及原Native Cookie交接验证；可见表单键入验收继续独立记录。账号、Client/S256、权限、BFF Cookie/CSRF与Admin程序保持原所有者。

构建15采用[系统HTTP适配](../design/multi-platform/mobile-runtime-architecture.md#2026-10-31-admin-json-http平台兼容)：复用现有NativeHTTPResponse，通过私有C ABI向Next和同步HTTPX提供Admin JSON后通道。原本机ASGI/SSE、Runtime/Gateway流及Web业务保持原路径。新增业务页面、业务HTTP路由、数据库变更、配置键和第三方依赖均0。

| 验证项 | 实际结果 | 范围 |
| --- | --- | --- |
| 原HTTPX/DTO合同 | 7通过，退出0 | 有界响应、原错误与写入未知结果；Provider-free |
| Node fetch适配 | 6通过，退出0 | 正文/头/取消及其他来源、Gateway/SSE、非manual透传 |
| Native源合同 | 原类/函数切片编译与7项执行退出0 | macOS Foundation隔离URLProtocol；字节、上限、Cookie、重定向、取消及UTF-8，iOS目标单独验证 |
| iPhone目标构建 | `xcodebuild ... CURRENT_PROJECT_VERSION=15 build`退出0 | 实际Swift/C++/CPython绑定进入设备App |
| 无线覆盖安装 | `devicectl device install app`退出0，22.604秒 | 14→15，安装前后原运行目录元数据相同 |
| 普通启动 | 无调试器启动，内置Next Ready282ms | 原产品App，未配置Mac业务中继 |
| 原账号会话 | App内`GET /auth/session`200，账号匹配、CSRF存在 | 实际iPhone构建15；本次读取50.682秒 |
| 物理后续读取 | 当前`passcodeRequired=true`，配置/历史回执尚未取得 | 待解锁后普通前台复核；期间缺项保持待验收 |
| Simulator | 普通产品12→15覆盖安装退出0，原数据inode保持；原重试后配置与20项历史恢复 | 无调试器真实账号读取；冷启动追加记录见下方 |

现有profile仍至2026-11-01 00:48:40（Asia/Shanghai），Team与UUID沿第十八节；本轮有效期未延长。Google公开回调登记、真实Claude/Notion业务和TestFlight/App Store继续分别验收。物理锁屏、Simulator、真实账号读取与模型任务拥有独立资格，当前结果覆盖安装、原会话读取与已执行的技术检查。

具体命令及安全回执归[本轮执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-ios-admin系统http兼容与工作区读取)。公开网络的超时和首屏耗时继续记录，服务就绪、登录恢复及完整工作区可用分别判定。


### 同源Simulator工作区恢复

普通iPhone16 Plus / iOS18.6 Simulator完成12→15覆盖升级，`xcodebuild ... -sdk iphonesimulator ... CURRENT_PROJECT_VERSION=15 CODE_SIGNING_ALLOWED=NO build`、adhoc签名deep/strict、`simctl install`均退出0。安装后原数据目录inode183813951保持。设备与Simulator的Metro输入逐字节一致；Simulator采用同一设备Hermes制品与Next BUILD_ID，原独立编译HBC摘要及打包前置断言失败保留在私有证据。编译HBC的摘要差异未作为业务源码差异；本次复用同一份共享RN字节码。

无调试器的原页面“重试读取”和历史“重新加载”完成配置恢复：附件、快捷操作可用，原权限显示“完全访问”，20项既有历史可见。此项覆盖当前真实账号的公开读取与原页面失败恢复；模拟数据、影子账号、Mac业务服务和模型调用均0。

随后普通进程终止/重开，原账号自动进入RN主页，内置Next Ready433ms，配置自动恢复。“新建对话”、附件与“完全访问”可见，冷启动历史出现原加载失败反馈。端侧Python、Next与控制监听均归同一App进程。

同步LLDB观察阶段三项本机请求均为URLSession -1001；该阶段拥有调试器干预，原始回执保留，HTTP200声明0。detach后本机匿名会话请求44ms返回401，用于监听就绪检查；真实账号读取资格由原普通UI恢复回执提供。初次脚本模块名包含连字符，LLDB导入拒绝；改为合法模块名后执行及detach成功。普通重开阶段无调试器附加，手机当前密码锁定状态与模拟器资格分别记录。


## 二十、2026-10-31 HTTP读取恢复与构建16

阶段记录：当前设备和Simulator采用第二十一节构建17；本节保留16的原始资格。

当前[开发IPA16](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b16.ipa)为`com.inkmemory.mobile`、0.1.0/16，142,625,298字节，SHA256 `51313a662921d40409472b4513cee41a295492a7382b4839ce4d80e8ec21f8e2`。原密码网页登录、Client/S256、Cookie/CSRF、权限、Web页面与业务接口保持。源env、Admin、数据库Schema及第三方依赖修改0。

构建15普通冷启动自动恢复账号与配置，历史读取最终显示原失败反馈。后续修订限定原HTTP传输：UTF-8/字节消费者排空缓冲时立即恢复此前挂起的任务；Admin绑定按原请求期限设置独立墙钟定时器，完成/取消后撤销并释放本次定时器引用。具体网络失败与缓冲状态的因果关系继续按实际回执判断。当前Swift函数原样提取后，在macOS Foundation隔离URLProtocol中编译、执行9项合同退出0，覆盖无回调超时与延迟拉取后实际URLSessionTask恢复；iOS运行资格另按下表判定。

| 验证项 | 实际结果 | 范围 |
| --- | --- | --- |
| iPhone/Simulator Release16 | 两次最终源码`xcodebuild`均退出0 | 同一Swift源摘要；RN源变化0，复用已核对的同源Hermes |
| 签名与制品 | 设备deep/strict、ZIP CRC及Simulator adhoc/strict均退出0 | 329份Python、4份Node摘要匹配，原Next BUILD_ID保持 |
| 物理覆盖安装 | 15→16退出0，21.345秒 | apps读回16，原runtime元数据保持 |
| 物理普通启动 | `devicectl device process launch`退出0，PID8291，lockState为passcodeRequired=false | 无强制终止；前台工作区验收继续单列 |
| 普通Simulator冷启动 | 无调试器，原账号、配置与20项真实历史自动恢复，原重试点击0 | 附件及快捷操作可用，权限“完全访问”；观察在启动后60.711秒内完成，Next Ready474ms |
| 物理原接口读取 | 94号取得原session503 / BFF_ADMIN_UNAVAILABLE、配置200且形状有效、历史504 / ADMIN_TIMEOUT | 会话与历史读取失败；完整前台工作区继续待复核 |

设备与Simulator共享HBC摘要`c079fd4ec4f1fa8f6dbd6daeb01ecd26f25a6fea6dd15817a01a72eb52f0bf52`；本轮没有重新编译React页面。物理手机后续进入其他前台应用，检查工具已退出；本轮未继续切换用户手机页面。原账号会话在15阶段的200保留原制品资格，16的完整前台读取保持待验收。普通Simulator使用原产品标识、原数据与正常公网Admin，隔离账号、模型调用与Mac业务服务均0。

开发profile保持8a404027-cd3f-4e0a-8b8c-e0aad62dee83，有效期至2026-11-01 00:48:40（Asia/Shanghai），本轮未延长。完整Claude/Google/Notion业务及商店发行继续独立验收。原15失败、同步调试观察超时及16首次观察脚本API缺口均在执行记录保留，技术合同、普通UI读取和物理发布资格分别登记。


构建16物理读取追加：原GET会话503（51.852秒）、配置200（62.606秒）、历史504（39.500秒）。95号确认原App PID8291继续存在，未把后台状态单独归因为网络失败。共享连接复用修订与后续实际版本回执按执行记录继续登记。


## 二十一、2026-10-31 Admin连接复用与构建17

阶段记录：当前物理设备已安装第二十三节构建20，启动待系统验证；本节保留17原始503及安装回执。

当前[设备开发IPA17](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b17.ipa)为`com.inkmemory.mobile`、0.1.0/17，142,625,581字节，SHA256 `0b0f83226a76f429ee7b9bc19e6064fc2ab2cafbcbf69f2d3bf15e57f0eb0bc7`。设备已Wi-Fi覆盖安装16→17，退出0、21.169秒，apps读回17，原runtime目录元数据保持。普通launch退出0、PID8315；此项覆盖App进程启动。

Admin后通道复用单个App级临时URLSession，每个Task在resume前绑定当前NativeHTTPResponse，完成/取消只处理当前Task。Cookie与系统凭据存储关闭，原请求期限、字节上限、TLS及重定向校验保持。前端原本机HTTP继续各自Session；原网页登录、Client、权限、Web页面、ASGI/SSE、Gateway与CLI业务保持。新增业务页面、业务路由、依赖和源env修改0。

| 验证项 | 结果 | 资格 |
| --- | --- | --- |
| `96-native-transport-check.py` | swiftc及10项实际执行退出0 | macOS Foundation源合同，覆盖共享Session取消隔离和连续请求；外网与模型0 |
| 设备/Simulator Release17 | 最终xcodebuild均退出0，59.473秒/54.562秒 | 同一Swift源SHA256 7d9b02bfad05189a45959d090a0c276e95fff6097979786d075ba2e90a688c62，RN源变化0 |
| 归档、签名、资源 | 设备deep/strict、CRC及Simulator adhoc/strict退出0 | 329份Python及4份Node匹配，同一Hermes及Next BUILD_ID |
| 普通Simulator冷启动 | 账号、配置、20项真实历史自动恢复；原重试点击0 | 无调试器；附件可用、完全访问，Next Ready461ms，观察在42.612秒内完成 |
| 物理原GET会话 | 503 / BFF_ADMIN_UNAVAILABLE，30.304秒 | 账号与CSRF成功资格未取得 |
| 物理原GET配置 | 503 / BFF_ADMIN_UNAVAILABLE，30.044秒 | 本次配置未加载；16的200保留原构建范围 |
| 物理原GET历史 | 503 / BFF_ADMIN_UNAVAILABLE，8.932秒 | 本次历史未加载 |
| 物理系统HTTPS对照 | 公开JWKS GET200，7.118秒 | 当前手机系统URLSession可达；后通道及业务成功保持独立 |
| 最新物理状态 | `device info lockState`退出0，passcodeRequired=true | 当前锁屏，完整普通前台工作区待解锁后复核 |

真机17工作区实现验收未通过。共享连接属于已实现的平台传输修订，剩余业务失败继续定位；初始打开与短暂界面观察仍显示加载，后续5项只读观察在调度后detach完成，期间锁屏与后台状态影响单独记录。系统HTTPS200、服务器收到部分200、Simulator成功均保持各自范围。

只读服务器检查按ink-memory-aliyun-ops规范执行，确认原Admin服务active、用户ink-admin；相关CFNetwork请求存在200。服务器代码/配置、服务启停、数据库直连/Schema和Docker操作0。日志只保留固定接口分类、状态、字节数与CFNetwork版本，账号、Cookie、授权码、密钥和业务正文输出0。具体后通道公开GET对照的符号查找/表达式执行未取得成功回执，列为harness缺口。

后续优先取得手机解锁并保持Dream前台时的普通冷启动console、原会话/配置/历史与原重试回执，核对Next实际传输选择及每个超时阶段；异常条件继续fail closed。当前开发profile仍于2026-11-01 00:48:40（Asia/Shanghai）到期，续期未取得。完整Claude、Google/Notion业务及TestFlight/App Store保持独立，本阶段模型调用0。


## 二十二、2026-10-31 iPhone头前网络失败与构建19

当前[设备开发IPA19](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261031-b19.ipa)为com.inkmemory.mobile、0.1.0/19，142,637,026字节，SHA256 `b1842ec714990ab00a5aef90bcb13d5e13d64b4c5a06cfa0e809f35442fca8bb`。18→19覆盖安装退出0，51.832秒；apps读回19，原runtime元数据保持。无调试器console冷启动Next Ready282ms。原profile 8a404027-cd3f-4e0a-8b8c-e0aad62dee83仍至2026-11-01 00:48:40（Asia/Shanghai）。

17本轮受控读取为503/503/200；18定向日志确认active前台会话解析在响应头前返回NSURLErrorDomain/-1005，0字节、系统连接复用，Native至Next约2毫秒。另一请求耗尽原30秒期限。具体物理链路原因保持未知。19在现有Native适配内，仅为固定认证读取增加一次头前-1005恢复，沿原期限、取消与大小限制；服务token、授权交换、撤销和业务写入保持原规则。

技术验证：Node6项、实际Swift源合同18项及iPhone Release19均退出0；原依赖、Next BUILD_ID `7d9jH8rpXR1wr5dGZXg_x`和HBC `c079fd4ec4f1fa8f6dbd6daeb01ecd26f25a6fea6dd15817a01a72eb52f0bf52`复用。原329份Python与4份Node资源匹配，签名deep/strict与ZIP CRC通过。普通成功阶段日志已收敛，失败或恢复才输出当前请求暂存阶段。原网页登录、Client/S256、Cookie/CSRF、角色与App内Python/Claude路径保持；新增依赖、业务接口、配置键、Schema与服务端改动0。

19原账户、配置、历史及真实任务状态按[本轮执行记录](../exec/mobile-app-design-review-20261024.md#2026-10-31-iphone-503定向采证与修复)继续登记。18首次无线安装失败、17/18实际503与Native fixture前置失败均保留原回执。18、19技术与安装资格独立于完整真机业务和正式发行。

构建19原公开读取追加：GET /auth/session 200（4.924秒），原账号匹配、CSRF存在；GET /api/system-config 200（5.370秒），原workspace/full access均true；GET历史200（3.054秒、限1项）。当前模型deepseek-v4-flash-vision-exp，模型目录200（6.348秒）。单次真实任务预算1；原网页登录弹窗、真实历史可见和模型最终/持久化继续分别取证。


## 二十三、2026-11-01 失败连接池与构建20

19后续冷启动/auth/options 200、7.591秒，随后同一PID该GET 503、30.070秒。对应service-token已命中Native，active、reused=1、响应头缺失、正文0；密码提交0、任务提交0。20退役连接丢失或原期限超时的当前Admin Session，后续请求获取新Session，旧在途Task按原期限结束。普通取消、固定只读一次恢复、授权交换和写入单次派发保持。

| 项目 | 实际回执 | 资格 |
| --- | --- | --- |
| Node / Native源合同 | 8项 / 24项，退出0，Swift编译0/运行0 | Provider-free技术验证 |
| xcodebuild | build20-command.json精确argv，退出0、40.051秒 | 同工程增量Release20，依赖安装0 |
| 制品 | 142639943字节，SHA256 bae15d1fc2b2f2d6cb6013f152b4d260728e4a1e5100723318165fc1b675c2fe | deep/strict签名和ZIP CRC通过，329份Python/4份Node匹配，Next/HBC沿19 |
| 描述文件 | c1464290-29a4-48e7-85d8-09710eca2c40，有效至2026-11-08 01:03:45上海时间 | 原Team与证书，证书在profile中，application identifier/entitlements匹配 |
| 覆盖安装 | devicectl install退出0、20.554秒，已安装0.1.0/20 | 2042项路径无增删，普通文件元数据一致；10项既有符号链接的目标metadata变为空，完整列表比较脚本退出1 |
| 普通启动 | 退出1，FBSOpenApplicationErrorDomain/Security | 本地签名/证书/profile核对通过；手机开发者信任或系统验证为当前前提 |
| 账户/真实任务 | 新制品未启动 | 20独立验收待完成；19历史200资格保留 |

原安装比较脚本失败保留，追加99-install20-reviewed-receipt.json说明实际差异。新profile续签后的系统拒绝与HTTP503分别登记；手机系统信任/验证由持有人完成。用户桌面、镜像和键鼠保持停止。后续启动与业务回执继续追加[执行记录](../exec/mobile-app-design-review-20261024.md)。


### 系统验证后追加：同一构建20真实业务

设备持有人完成iOS系统验证，普通启动获准；受控冷启动Next Ready277ms、App PID9053。仍为上述IPA20、同一Bundle和原数据。原Security拒绝保留历史回执。20首次后台preflight 200/6.793秒，后续journey前置GET503/9.332秒；该次密码/模型提交0。受控冷启动后该GET200/2.424秒，后续两次暖读取200/2.908秒和2.320秒。

| 业务步骤 | 实际结果 | 范围 |
| --- | --- | --- |
| 原密码登录协议 | 单次POST303，原PKCE authorize/callback导航完成，最终200 | 同一App内公开HTTP；原网页可见弹窗资格单列 |
| 原GET /auth/session | 200、5.384秒 | 指定现有账户匹配，合法CSRF存在 |
| 原GET /api/system-config | 200、4.054秒 | workspace/full access均true |
| 原GET模型目录/历史 | 200、6.663秒 / 200、8.962秒 | 当前模型可调用、5项真实历史；历史页面显示待验收 |
| 原POST /api/claude-agent | 单次发送，HTTP200、9023字节流 | 原App内Python→SDK/CLI，最终短回复匹配 |
| 原messages/status | 200 / 200 | 新用户消息及completed助手持久化，running=false、idle |
| 正常Admin账单 | req_4a3866fec4a640db86250788d4cf87e4，HTTP200、succeeded、settled | 窗口内仅1次；模型deepseek-v4-flash-vision-exp；输入3627、缓存读取19712、输出89、扣减23428 Token |

完整旅程158.738秒，任务提交预算1、实际1，额外模型调用0。原登录页面、弹窗关闭、可见历史和真机实际网络恢复触发继续独立验收。后台HTTP及SQL只读审计的具体命令、退出码、失败和回执归[执行记录](../exec/mobile-app-design-review-20261024.md#2026-11-01-构建20原登录协议与一次真实claude任务)。


## 2026-11-01 Notion安装检测修复构建21

[构建21开发IPA](../../frontend/ios/build/InkMemory-Notion-Release-device-20261101-b21.ipa)沿原依赖、开发身份及配置签名，SHA256 `4a507ab5d66793ca1639a713e5440c38416f3391332f34bddd8de45d972ca2fb`，142,640,647字节、0600；profile至2026-11-08 01:03:45（Asia/Shanghai）。同一iPhone16覆盖安装、启动及最终apps读回21均退出0。

真机原固定ntn文件为0755，原生X_OK返回false。修复后仅精确绑定的解释执行文件检查R_OK；原主机检查、包内摘要、私有端点及权限门禁保持。手机原Python工厂检测installed，版本/帮助均退出0；原公开会话/配置/能力目录/连接记录均200，资源列表401，当前手机有效Notion授权与资源读取继续待验收。正式渠道发布未执行。[设计与评审](../design/multi-platform/react-native-web-project-structure.md#iphone-notion安装提示与恢复2026-11-01)及[命令与分项证据](../exec/ios-notion-20261101.md)分别维护。


## 2026-11-01 Notion授权链接修复构建22

[构建22开发IPA](../../frontend/ios/build/InkMemory-NotionLinks-Release-device-20261101-b22.ipa)复用21原生、后端与生效配置，正常`index.native.js`重新生成Hermes。SHA256 `1bba8268b0baa142521ffb73b30fcdb0c8a66d4cc082755963d4c7f3eee6e241`，142,559,295字节、0600；签名及83个framework严格校验通过，profile期限沿前节。

原Notion默认回调提取`Linking.openURL`导致接收者丢失；现行平台函数保留接收者、Promise失败合同及系统默认浏览器选择。模拟器原组件点击闪退复现、修复后Safari打开/返回及失败反馈、十九项原生页面与七项Web回归通过。原iPhone覆盖安装和启动均退出0，读回0.1.0/22。真实Notion授权网页确认、资源读取及正式渠道发布分别验收。[本轮设计与命令](../exec/ios-notion-links-20261101.md)保留全部范围及失败历史。


## 2026-11-01 当前工作区公网构建23

用户授权将最新工作区代码打包至原iPhone，Admin采用`https://ink-admin.suoxya.com`。本轮读取当前合同及工作树，保留未提交的写作关联对话修复，沿当前源码重新准备独立Next standalone、RN/Hermes字节码、Python及Node运行资源。业务源码、源env、依赖与正常服务保持；递增构建号采用23，同一bundle ID覆盖安装原22，卸载与数据清理操作为0。

执行依据归私有工件`frontend/ios/build/iphone-latest-20261101/optimized-prompt.md`，本轮规划整理一次。源码基线为`f40a9cfae8e85489a5354ccce7987f0a6a50f57d`及当时未提交改动；549份前端runtime输入在构建后、签名后与当前源码匹配。独立Next根为`frontend/ios/build/iphone-latest-20261101/Next`，打包来源门禁退出0，Mac Web的`.next`保持。

### 制品与公网配置

- 应用：`Ink & Memory`、`com.inkmemory.mobile`、`0.1.0 (23)`。
- [开发IPA](../../frontend/ios/build/InkMemory-PublicAdmin-Release-device-20261101-b23.ipa)：142791393字节，权限0600，SHA256 `e82d23a635f1b453fd95c9bd26840929ff4266d9de87e17c182fa2dad05d103f`。
- Next BUILD_ID：`0venWLY53yy9qjALxSnQI`；来源回执SHA256 `56774dd982c308f5a59fcf705c17f2a4cf289d853031330e2d5159ae45aee445`。
- Hermes字节码`main.jsbundle`：5744210字节，SHA256 `39e5bd8733e5c4d353a3d37b7ec87e54f0e945d2d80e16c18cc5c3946a643394`。引擎Framework二进制摘要与JS字节码摘要分别记录。
- 83个Framework和主应用沿原开发身份签名；profile匹配原设备及Team，有效至2026-11-08 01:03:45（Asia/Shanghai）。

安装包的原env配置项采用公网Admin：前后端`INK_ADMIN_DREAM_BASE_URL`及`INK_ADMIN_DREAM_TRANSPORT_BASE_URL`为公网根，`INK_ADMIN_AUTH_ISSUER`为公网`/api/auth`；后端`INK_ADMIN_PRODUCT_API_BASE_URL`及`INK_GATEWAY_BASE_URL`使用同一公网根。修改仅作用于待签名副本的这些既有URL键，其他配置字节保持。Dream本机origin、原正常网页登录回调、Client及PKCE仍沿原所有者，源env写入0，凭证正文输出0。

### 实际命令与回执

确定性阶段由luna_test_runner执行，主Agent执行公网配置、签名、安装与启动。原始回执归`frontend/ios/build/iphone-latest-20261101/validation/`及同根的设备JSON；旧22制品保留。

| 命令或阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --pretty false --incremental false`，frontend | 0 | Web类型通过，7.153秒 |
| `pnpm run native:typecheck`，frontend | 0 | Native类型通过，3.430秒 |
| `INK_IOS_NEXT_ROOT=<本轮Next绝对路径> python3 frontend/ios/scripts/prepare-next.py` | 0 | 无env的当前源码准备完成，725文件、549 runtime输入；复用已安装依赖 |
| `pnpm --dir <本轮Next根>/build-source build` | 0 | Next生产构建通过，27.616秒；私有tsconfig仅指定原安装typeRoots |
| `INK_IOS_NEXT_ROOT=<本轮Next根> python3 frontend/ios/scripts/bundle-next.py --verify-sources`，构建前后 | 0 | 当前checkout与prepared输入一致，无旧资源采纳 |
| `env -u SKIP_BUNDLING INK_IOS_NEXT_ROOT=<本轮Next根> xcodebuild -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory -configuration Release -sdk iphoneos -destination generic/platform=iOS -derivedDataPath frontend/ios/build/rebuild-iphone-20261031/DerivedData -jobs 3 CURRENT_PROJECT_VERSION=23 CODE_SIGNING_ALLOWED=NO build` | 0 | BUILD SUCCEEDED，59.735秒；正常RN入口重新生成字节码 |
| `python3 frontend/ios/build/iphone-latest-20261101/package23.py` | 0 | 公网URL投影、83个Framework签名、主应用签名与IPA归档完成 |
| `codesign --verify --deep --strict <release23/Payload/InkMemory.app>`、`unzip -t <本轮IPA>` | 0 | 签名与归档完整性通过；329份Python和4份Node平台源匹配当前仓库 |
| `xcrun devicectl device install app --device F615EA70-0AFD-5E1A-9373-AECBD061688D <本轮签名App>` | 0 | 原iPhone22覆盖升级23；未卸载、未清理数据 |
| `xcrun devicectl device process launch --device F615EA70-0AFD-5E1A-9373-AECBD061688D com.inkmemory.mobile` | 0 | 普通启动成功，PID 10173 |
| `xcrun devicectl device info apps`及`device info processes`，同一设备 | 0 | 设备读回0.1.0/23及同一新安装路径，App进程存在 |

制品来源、构建、签名、安装和普通进程启动已完成。本轮额外发起的模型任务、账户维护及第三方授权操作为0。笔记A/B对话、完整登录、资源及Claude真实任务的本轮真机页面验收未执行；先前技术或真实业务回执保留各自版本范围。TestFlight与App Store发布未执行。

## 2026-11-01 启动控制页构建24（待设备重连）

用户授权将已验证的启动控制页及原始错误日志安装至原iPhone。构建24采用当前工作区普通`index.native.js`入口、当前Next standalone、Python及Node资源。原模拟器准备/就绪与两入口资格、原始EADDRINUSE展示/复制资格见[专项记录](../exec/mobile-startup-design-review-20261101.md#原始错误日志补充2026-11-01)。

| 交付项 | 结果 |
| --- | --- |
| 应用与制品 | `com.inkmemory.mobile`、0.1.0/24；[开发IPA](../../frontend/ios/build/InkMemory-Startup-Release-device-20261101-b24.ipa)，142812974字节、0600，SHA256 `ecb6ef6066d9eb7e7c26bdc14c3c1374896c2a0f49dd7f30a05ba9237793be56` |
| 构建 | 独立`prepare-next.py`、`pnpm build`、前后两次`bundle-next.py --verify-sources`及`xcodebuild ... CURRENT_PROJECT_VERSION=24 CODE_SIGNING_ALLOWED=NO build`均退出0；原DerivedData增量构建约49秒 |
| 当前来源 | Next runtime输入550份、Python329份及Node4份逐字匹配；HBC `9acabc8e61f4e5651ea34d95d6a0b5b7404ff182ec343a94a14a86d2e4e78d27`，Next BUILD_ID `KOV9qB9o5Tu9uPUYbr6Ms` |
| 开发签名 | 原Team/profile，83个Framework及主应用签名通过；deep/strict、IPA CRC均退出0；原有效期至2026-11-08 01:03:45上海时间 |
| 既有配置 | 副本沿原23制品规则采用公网Admin；正常账号回调、源env及锁文件保持；依赖安装和模型调用为0 |
| 安装前设备 | 同一iPhone16可连接，已解锁，原App读回0.1.0/23；原数据目录2161项metadata已保存 |
| 首次安装 | `devicectl device install app`退出1、12.206秒，CoreDevice连接失效，NWError60超时；设备随后unavailable |
| 当前设备采用 | 无成功安装回执；设备读回与普通启动等待同一iPhone重新连接，最新已确认版本为23 |

本轮工件归`frontend/ios/build/startup-iphone-20261101-b24/`。首次私有打包脚本将签名基线误指release24，复制profile前退出；已修正为原release23并完成后续签名，失败日志保留。安装失败与包体签名/源码资格分别记录。设备发现重试返回CoreDevice1000，Xcode发现同一设备available=false，说明需恢复设备连接。卸载、数据清理、账号维护及正常服务变更为0；本轮物理页面、业务与正式渠道发行均未验收。

## 2026-11-02 构建24覆盖安装与普通启动

用户要求继续安装。设备已恢复可连接，安装前读回同一`com.inkmemory.mobile`为0.1.0/23。本轮复用前节已签名构建24，IPA SHA256仍为`ecb6ef6066d9eb7e7c26bdc14c3c1374896c2a0f49dd7f30a05ba9237793be56`；原生、Next、Python与RN资源重新构建次数为0。

| 命令或核对 | 退出码 | 实际结果 |
| --- | --- | --- |
| `codesign --verify --deep --strict <release24/Payload/InkMemory.app>` | 0 | 既有签名通过，包内版本24与HBC摘要匹配原制品回执 |
| `xcrun devicectl device install app --device F615EA70-0AFD-5E1A-9373-AECBD061688D <release24/Payload/InkMemory.app>` | 0 | 20.827秒，同一iPhone16从23覆盖升级24 |
| `devicectl device info apps` | 0 | 读回0.1.0/24，新安装路径与安装回执匹配 |
| `devicectl device info files`，安装前/后且启动前 | 各0 | Library/Application Support均2161项，路径增删0，普通文件及符号链接metadata变化0 |
| `devicectl device process launch` | 0 | 普通启动PID10604 |
| `devicectl device info processes` | 0 | PID10604及新安装路径仍存在 |

本次采用包含启动控制页与原始错误日志。源env、原配置、登录回调、开发签名、正常服务及业务数据维护操作保持原范围；卸载、数据清理、依赖安装和模型调用为0。数据核对仅读取metadata，正文与凭证读取为0。物理页面、登录、真实业务及任务恢复验收分别执行。

回执归`frontend/ios/build/startup-iphone-20261101-b24/resume-20261102/`，包括`preflight-commands.json`、`install24-command.json`、`install24.json`、`apps-after.json`、`data-comparison.json`、`launch24.json`、`processes-after.json`及`device24-receipt.json`。前节首次失联与未完成安装的原回执保持历史状态；本节记录设备24实际采用。
