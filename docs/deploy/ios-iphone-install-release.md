<!-- [Input] ink-dream iOS工程、开发签名和目标设备。 -->
<!-- [Output] 本地准备、构建、安装、启动及安装失败处理步骤。 -->
<!-- [Pos] iPhone开发安装手册；商店发行归App Store上架手册。 -->
<!-- [Sync] 2026-11-04: 移动配置改为完整运行配置，说明.env复制、Admin连接选择及编辑器入口。 -->
<!-- [Sync] 2026-11-03: 增加公网Admin配置片段及合并步骤，核对Product API地址和既有前端配置。 -->
<!-- [Sync] 2026-11-02: 正文聚焦安装任务，逐版本设备回执移存执行历史。 -->

# ink-dream iPhone 开发安装手册

## 适用范围

本手册用于将 ink-dream 安装到开发设备并检查启动。TestFlight和App Store分发按[上架手册](ios-app-store-release.md)执行。

工程入口为[`frontend/ios/InkMemory.xcworkspace`](../../frontend/ios/InkMemory.xcworkspace)，Scheme为`InkMemory`，Bundle ID为`com.inkmemory.mobile`。已有同Bundle ID应用时采用覆盖安装，并保留设备内数据。

## 一、设备与签名准备

1. 在Xcode的`Settings → Accounts`登录开发Apple账户。
2. 打开workspace，在`InkMemory → Signing & Capabilities`选择有权使用的Team，常规开发使用自动签名。
3. 连接iPhone并完成“信任此电脑”和配对；后续可使用已配对的Wi-Fi连接。
4. 在设备“设置 → 隐私与安全性 → 开发者模式”按提示启用Developer Mode。
5. 安装及启动时保持设备可用。锁屏、配对失败和profile到期分别按系统提示处理。

在仓库根目录读取工具与设备信息：

```bash
xcodebuild -version
xcrun devicectl list devices
security find-identity -v -p codesigning
```

签名证书、私钥、profile与Team及Bundle ID需要匹配。私钥保存在Keychain，密码由本人输入。免费Personal Team的开发profile通常在签发七天后到期，到期后重新配置签名并安装。[Apple账户说明](https://developer.apple.com/help/account/basics/about-your-developer-account)、[Developer Mode](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)，查阅：2026-11-02。

## 二、准备安装包

### 资源与配置

1. 选定源码版本，核对`frontend/pnpm-lock.yaml`、`frontend/ios/Podfile.lock`及锁定的iOS运行资源，复用已有安装结果。
2. 按[构建内存与恢复手册](build-memory-and-recovery.md)确认本次构建容量和可恢复制品。
3. Python、Node、Guest及字体资源缺失时，按`frontend/ios/scripts/`内对应准备脚本的错误提示补齐。
4. Web源码变更后按下方顺序准备Next；同一准备目录贯穿构建、验证及Xcode资源阶段。并行任务使用各自具名目录。

```bash
export INK_IOS_NEXT_ROOT="<仓库绝对目录>/frontend/ios/build/<本次安装>/Next"
python3 frontend/ios/scripts/prepare-next.py
pnpm --dir "$INK_IOS_NEXT_ROOT/build-source" build
python3 frontend/ios/scripts/bundle-next.py --verify-sources
```

`INK_IOS_NEXT_ROOT`需位于`frontend/ios/`内。Xcode资源阶段装配后端、运行库、Next及字体；RN打包入口为`index.native.js`。核对最终App的`next/source-receipt.json`、`mobile-manifest.json`和`serverEntry`对应本次准备结果，来源过期时重新准备。

`build-rn-ios.sh`包含依赖安装、Pods和资源准备；缓存齐备时使用后文直接构建命令。当前装配会读取`backend/.env`与`frontend/.env.local`；开发配置只用于授权测试范围。对外分发先完成[包内配置审查](ios-app-store-release.md#发布前检查)。

### 服务地址

手机的`localhost`指向手机自身。包内服务使用loopback，外部Admin使用手机可达的HTTPS地址。核对`INK_ADMIN_DREAM_BASE_URL`、`INK_ADMIN_DREAM_TRANSPORT_BASE_URL`、`INK_GATEWAY_BASE_URL`及既有认证注册。

使用公网Admin时，按以下顺序准备配置：

1. 从现用`backend/.env`复制完整配置到`backend/.env.mobile`，保留全部公共运行配置和已登记凭据；已有移动配置时保留目标Admin连接值。新建配置可参考[移动完整配置模板](../../backend/.env.mobile.example)，空白凭据在本机填写。该本机文件已加入Git忽略规则，文件权限使用`0600`。
2. 在`.env.mobile`中设置目标Admin连接。认证、Product API及Gateway地址采用`https://ink-admin.suoxya.com`；Service Secret和Gateway Key使用目标Admin已登记值。其余配置与`.env`保持一致，公共配置调整时同步两份文件。编辑器的`Backend: Python (server.py, Admin)`通过`envFile`直接加载`.env.mobile`；普通Backend入口加载`.env`。两个入口共用原后端端口，按先后运行。
3. 为iOS打包时，将`.env.mobile`中的目标Admin连接按键合并到`backend/.env`，将Admin认证与数据访问配置同步到`frontend/.env.local`，保留前端原Cookie Secret和本机Next来源。`INK_ADMIN_PRODUCT_API_BASE_URL`需要单独核对。`INK_DREAM_API_RESOURCE`沿用Admin登记的`https://ink-frontend.suoxya.com/api`；Client ID、resource和回调需与目标Admin登记一致。Product写请求的`INK_ADMIN_PRODUCT_ORIGIN`需在目标Admin的`PRODUCT_API_ORIGIN_ALLOWLIST`内，本模板沿用原`http://127.0.0.1:5173`，登记情况由Admin管理方核对。
4. 使用原Xcode流程重新打包。当前脚本读取`backend/.env`和`frontend/.env.local`；`.env.mobile`用于准备配置。打包时账户回调按实际Bundle ID写为`<Bundle ID>.auth:/auth/callback`，MCP回调写为`<Bundle ID>.mcp:/oauth/callback`；账户回调需在原Admin Client中精确登记。

服务地址、账户回调和MCP回调分别管理。地址调整后重新生成并签名安装包；日志保留错误与配置键，密码、Cookie和service secret保存在受控配置中。具体认证问题按[认证排障指南](mobile-auth-troubleshooting.md)处理。

### 开发构建与安装

Xcode选择`InkMemory`和已连接的iPhone，执行`Product → Run`完成构建、签名及安装。命令行方式在仓库根目录执行：

```bash
export IOS_DEVICE_UDID="<目标设备UDID>"
export IOS_DERIVED_DATA="<本次允许使用的缓存绝对路径>"
export IOS_BUILD_JOBS="<按可用容量确定的并发数>"
xcodebuild \
  -workspace frontend/ios/InkMemory.xcworkspace \
  -scheme InkMemory -configuration Debug -sdk iphoneos \
  -destination "id=$IOS_DEVICE_UDID" \
  -derivedDataPath "$IOS_DERIVED_DATA" -jobs "$IOS_BUILD_JOBS" \
  ENTRY_FILE=index.native.js COMPILER_INDEX_STORE_ENABLE=NO build

export IOS_APP_PATH="$IOS_DERIVED_DATA/Build/Products/Debug-iphoneos/InkMemory.app"
codesign --verify --deep --strict "$IOS_APP_PATH"
xcrun devicectl device install app --device "$IOS_DEVICE_UDID" "$IOS_APP_PATH"
xcrun devicectl device process launch --device "$IOS_DEVICE_UDID" com.inkmemory.mobile
```

构建采用工程签名配置。关闭签名生成的中间App需要完整处理嵌套framework、根目录动态库、profile和主应用签名后才能安装；常规安装交由Xcode处理。更换Bundle ID前核对回调、profile及数据迁移，保留已有设备数据。

## 三、安装后检查

| 检查项 | 预期结果 | 失败处理 |
| --- | --- | --- |
| 安装与普通启动 | 设备读回目标版本，应用启动并保持可用 | 核对签名、profile、Developer Mode、锁屏和配对状态 |
| 服务准备 | 准备完成，页面能够进入 | 按应用错误和资源来源记录处理，避免采用过期资源 |
| 登录与读取 | 正常登录，配置和历史可读取 | 按认证排障指南核对HTTPS、回调和会话 |
| 使用与恢复 | 在本次测试范围内完成操作及重开，原数据保留 | 保存失败结果和版本；按对应步骤恢复 |

只登记实际执行的项目。真实任务按[本机真实业务测试协议](../../AGENTS.md#本机真实业务测试协议)执行，保留正常服务可查询的回执。

## 四、常见失败处理

| 现象 | 处理顺序 |
| --- | --- |
| 设备不可用或安装超时 | 读取设备连接状态，恢复配对与解锁后重新安装已核对的包 |
| 开发profile过期 | 在Xcode更新当前Team的开发签名，重新构建并覆盖安装 |
| 启动被系统拒绝 | 按设备提示核对Developer Mode和开发者信任；保存系统错误 |
| 签名校验失败 | 核对全部framework及根目录动态库，完整重新签名或从Xcode重构建 |
| 包内资源与源码不一致 | 在同一具名目录重新准备、构建及验证，再安装 |
| 网络或认证失败 | 核对物理设备实际可达地址及原认证注册，按认证排障指南处理 |

## 五、进入商店分发

安装检查通过后，按[App Store发布手册](ios-app-store-release.md)办理正式会员、分发签名、Archive、TestFlight和审核。开发安装结果按开发测试范围记录；商店候选单独完成测试和发行步骤。

## 历史引用

原有核查、评审与回执见[修订前原文](../exec/history/ios-release-documents-before-reader-revision-20261102.md#ios-iphone-install-releasemd)。

<a id="iphone-打包安装与发布操作手册"></a>
<a id="三临时包检查"></a>
<a id="四testflight-与-app-store"></a>
<a id="五2026-10-30-临时包执行记录"></a>
<a id="用户确认与根目录动态库补签"></a>
<a id="六2026-10-31-release开发包"></a>
<a id="前阶段构建4记录"></a>
<a id="七2026-10-31普通simulator账号回调采用"></a>
<a id="八2026-10-31产品simulator首次安装与业务"></a>
<a id="九2026-10-31产品包ntn专项验证"></a>
<a id="十2026-10-31release前端来源追溯"></a>
<a id="十二2026-10-31-simulator构建6与输入焦点修复"></a>
<a id="十三2026-10-31构建7与ntn启动修复"></a>
<a id="十四2026-10-31构建8与停止恢复"></a>
<a id="构建8的ntn验证范围复核"></a>
<a id="十五2026-10-31公网admin构建10与账号回调"></a>
<a id="十六2026-10-31公网admin构建11与原网页登录恢复"></a>
<a id="十七2026-10-31公网admin构建12与product-api配置"></a>
<a id="十八2026-10-31当前源码构建13与iphone安装"></a>
<a id="十九2026-10-31工作区读取与系统http适配"></a>
<a id="同源simulator工作区恢复"></a>
<a id="二十2026-10-31-http读取恢复与构建16"></a>
<a id="二十一2026-10-31-admin连接复用与构建17"></a>
<a id="二十二2026-10-31-iphone头前网络失败与构建19"></a>
<a id="二十三2026-11-01-失败连接池与构建20"></a>
<a id="系统验证后追加同一构建20真实业务"></a>
<a id="2026-11-01-notion安装检测修复构建21"></a>
<a id="2026-11-01-notion授权链接修复构建22"></a>
<a id="2026-11-01-当前工作区公网构建23"></a>
<a id="制品与公网配置"></a>
<a id="实际命令与回执"></a>
<a id="2026-11-01-启动控制页构建24待设备重连"></a>
<a id="2026-11-02-构建24覆盖安装与普通启动"></a>
