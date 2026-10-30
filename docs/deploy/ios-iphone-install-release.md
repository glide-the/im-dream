<!-- [Input] 当前 frontend React Native 工程、端侧运行库、Xcode 与已登记 iPhone。 -->
<!-- [Output] iPhone 开发安装、临时包检查、TestFlight 与 App Store 发布操作。 -->
<!-- [Pos] iOS 实机操作手册；架构与历史资格归 mobile-app-release.md 和跨端设计。 -->
<!-- [Sync] 2026-10-30: 核对现行工程、开发签名与设备，补充临时包实测和正式发行前提。 -->
<!-- [Sync] 2026-10-30: 用户确认设备已信任；真机日志定位根目录 Debug dylib 漏签，补充显式签名和逐文件校验。 -->

# iPhone 打包、安装与发布操作手册

## 适用范围

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
- 原 Next standalone 位于 `frontend/ios/Next/build-source/.next`。需要刷新 Web 资源时，顺序执行下列命令；准备目录由构建共享，避免与其他任务并行覆盖。

```bash
python3 frontend/ios/scripts/prepare-next.py
pnpm --dir frontend/ios/Next/build-source build
```

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
