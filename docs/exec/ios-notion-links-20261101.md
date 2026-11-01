<!-- [Input] 用户报告构建21打开Notion授权闪退，并要求在模拟器修复、回归七项及统一端侧默认浏览器。 -->
<!-- [Output] 崩溃依据、局部修复、模拟器与七项网页验证及制品状态。 -->
<!-- [Pos] 本轮Notion授权链接修复执行记录；前轮安装检测证据保留在ios-notion-20261101.md。 -->

# Notion授权链接与端侧默认浏览器

## 范围与执行依据

本轮按一次优化执行依据推进：读取当前工作区与直接调用链；只读取得手机崩溃元数据；在隔离模拟器使用原组件与原React Native Linking复现；修复方法接收者和错误反馈；端侧网页链接统一交给本机默认浏览器；沿原Next页面与mock DTO完成此前七项Notion Web主用例。原账户、Notion授权协议、凭证存储、资源范围、权限、数据库及模型调用保持原所有者。用户和其他Agent的未提交修改保留。

技术验证边界：Project、Episode、正文、Run、Hook和数据库均不涉及。模拟器使用独立应用标识和明确的内存授权会话，原组件、DTO parser、Hermes和系统URL处理链参与验证；真实授权和真实资源读取独立验收。

## 发现与最小修复

手机`InkMemory-2026-11-01-122653.ips`记录`com.inkmemory.mobile`、0.1.0/21、PID9701、2026-11-01 12:26:52（Asia/Shanghai），异常`EXC_CRASH/SIGABRT`，末次异常栈进入`RCTExceptionsManager reportFatal`。该记录确认React Native致命JavaScript异常；模拟器使用原冻结生产模块复现同一点击后退出，并捕获`TypeError: undefined is not a function`与`RCTFatalException`；修复后的同一路径验证通过。

原`ConnectorNotionDetailPage.native.tsx`使用默认参数`openLink=Linking.openURL`，点击时执行独立函数`openLink(url)`。已安装React Native 0.81.5的`Linking.openURL`调用`this._validateURL`，提取方法会丢失接收者；原`.catch`仅接收Promise拒绝，同步异常在调用返回前抛出。`AboutView.native.tsx`和`ReflectionBlogPage.native.tsx`存在相同默认参数。

选用一个小型平台函数`externalLinks.native.ts::openExternalLink`：在async函数中执行`Linking.openURL`，保留接收者，原相对链接按可选origin解析，异常以Promise拒绝交给原反馈。Notion、关于、回顾、Chat/Plan/文件/工作区及Writing调用该函数；Notion和关于的页面回调同时捕获同步异常。新增浏览器容器、原生桥接接口、依赖、安装管理页及数据库变更数均为0。

## 评审

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 闪退触发 | 手机记录JS致命异常，默认方法引用丢失接收者 | 用原组件与Hermes复现，局部修复调用 | 原组件Hermes前后验证通过 | 真机原授权网页确认 |
| 全部端侧网页链接 | 三处默认回调及App/Writing分别打开链接 | 复用统一async平台函数与系统Linking | 模拟器默认Safari前台与返回通过 | 真机原授权网页确认 |
| 失败恢复 | 同步抛出可越过原Promise.catch | Notion和关于采用try/await/catch | 同步异常显示原反馈且App存活 | 无 |
| 授权与权限 | 原验证码、轮询、凭证与回调已有明确所有者 | 保留原业务接口和状态 | 新认证协议与权限变更数0 | 真实Notion授权独立验收 |
| 七项Web回归 | 既有七项依赖Next页面；正常5173占用默认构建锁 | 本轮独立Next输出与CLI宿主，复用原页面和mock DTO | 原服务保持运行，七项通过 | 无 |

[正式交互设计](../design/multi-platform/mobile-ios-interaction.md#端侧网页链接与notion授权恢复2026-11-01)包含正常、异常与状态图。[移动产品需求](../prd/dream-workspace/mobile-app.md#设置资源详情与恢复骨架)保留原桌面及窄屏骨架。

## 当前证据

证据目录：`frontend/ios/build/notion-auth-crash-20261101/`。手机崩溃原文权限0600，仅输出异常类型、版本及技术栈；凭证、验证码、Cookie、Token及用户文档正文输出数均为0。

- 模拟器baseline已冻结：Hermes SHA256 `74f51c137389ea4aa5fa415f3043b3cc84925030932a32035bb5e4929626ab47`。初次Metro入口位于ios目录，被既有blockList拒绝，退出1；本轮配置临时放行后bundle和Hermes编译均退出0。现行harness改放`frontend/e2e/native/notion-links-entry.tsx`，后续使用原Metro配置。
- 七项Next首轮使用programmatic dev server，服务就绪后缺少CLI bundlerService，七项导航均连接拒绝，退出7。当前改用独立CLI宿主，失败历史保留。
- 生产修复已落地；模拟器前后验证、七项主用例及制品状态按实际回执继续补充。

## 七项Web回归结果

`E2E_WEB_BASE=http://[::1]:5173 pnpm exec playwright test -c ios/build/notion-auth-crash-20261101/runner/web/notion-web.config.mjs --reporter=list`退出0，`7 passed (14.8s)`。复用的原Next进程cwd已核对为当前frontend，只读页面与静态资源；所有业务GET/POST由现有page.route闭合fixture处理，真实账户、数据库及模型调用均为0。

保留前置失败：programmatic Next缺bundlerService、隔离CLI符号链接路由发现失败、IPv4地址族连接拒绝。正常服务监听`[::1]:5173`，采用对应IPv6 origin后业务断言完成；测试将AuthProvider/useNotionConnector主动取消的读取归入网络失败。测试harness按现有memorySettingsLifecycle模式增加明确Notion Settings opt-in，仅分类同源、资源页精确referer、无查询、GET `/auth/session`或`/api/connectors`的`ERR_ABORTED`；其他路径、方法和错误保持失败断言，生产业务状态与校验修改数为0。

文档路径与文件头首轮退出0；新状态图通过，两份时序图因Mermaid保留词`Link`报错，参与者别名已改为`Opener`，后续语法复验独立记录。

## 模拟器与相邻原生验证

独立iPhone16/iOS18.6模拟器`InkMemory-NotionLinks-20261101`使用专用fixture应用`com.inkmemory.notionlinks`，原组件、原DTO parser、原Hermes及Linking参与验证。基底沿已安装的原RN原生库；真实账户、后端、数据库、模型及Notion授权会话使用数均为0。

| 实际命令或回执 | 退出码 | 关键结果 |
| --- | --- | --- |
| 原`loadBrowserSession`验证合成会话 | 0 | 原严格schema通过，actor为明确数字fixture，CSRF43字符 |
| `xcodebuild build-for-testing`原UI runner | 0 | 仅本轮测试工程，原生产Xcode工程保持 |
| `xcodebuild test-without-building` baseline | 0 | 点击原Notion验证页按钮后进程退出；Simulator捕获`Unhandled JS Exception: TypeError: undefined is not a function`及`RCTFatalException` |
| `react-native bundle --platform ios --dev false --entry-file e2e/native/notion-links-entry.tsx`与Hermes | 0 / 0 | 原组件修复后的技术entry |
| 同一UI runner的after测试 | 0 | Notion网页进入默认Safari，返回App存活；同步throw显示原重试信息；关于GitHub链接进入Safari并可返回 |
| `pnpm -C frontend native:typecheck` | 0 | 原生类型检查通过 |
| `native-notion-resources.spec.ts` | 0 | 4 passed |
| `native-settings-categories.spec.ts` | 0 | 15 passed |

原冻结bundle保持；baseline仅修正唯一测试会话DTO字面量，原生产Notion与Linking模块字节保持。首两次baseline UI因测试会话缺严格字段、ID格式错误分别退出65，归harness前置失败；两次失败与原始冻结制品均保留。修正DTO后才取得实际产品闪退及修复后通过的回执。

修复后技术Hermes SHA256 `85aa2c10114ac0c3c983cdf9aff2a28891ab068cf1e1347a6ac7b56b38b76d5a`；其fixture入口拥有独立资格，普通产品包继续使用`index.native.js`。独立模拟器已关闭；自有runner、派生目录及临时配置已清理，普通模拟器和正常服务保持。

三份新业务图最终解析退出0；取消分类9项实际listener边界检查退出0，POST、其他路径/查询/referer/跨域/错误及未启用场景均保持未分类。

完整回执：`runner/simulator/VALIDATION-RECEIPT.md`与`runner/web/receipt.md`。

## 普通产品构建22与手机采用

普通产品沿`index.native.js`及原Metro配置编译，RN bundle退出0（20秒），Hermes退出0（3秒），采用RN0.81.5/HBC96。打包沿手机既有构建21的原生库、Python/Node/Next、固定ntn、profile及生效配置字节，替换正常产品Hermes及构建号；原生重编、依赖安装、源env写入、账户维护及模型调用均为0。技术fixture未进入正常产品入口。

[开发IPA构建22](../../frontend/ios/build/InkMemory-NotionLinks-Release-device-20261101-b22.ipa)为142,559,295字节、0600，SHA256 `1bba8268b0baa142521ffb73b30fcdb0c8a66d4cc082755963d4c7f3eee6e241`。正常Hermes SHA256为`342da27993d4d5545342fac3f46b62b379bfc6eb13d2e4d1f9bec6dd081e9911`；83个既有framework严格校验及主应用重新签名/deep-strict验证退出0，归档CRC通过。开发profile有效至2026-11-08 01:03:45（Asia/Shanghai）。

| 实际命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `python3 frontend/ios/build/notion-auth-crash-20261101/package22.py` | 0 | 原生/后端/账号配置保持，正常产品HBC装配，签名与归档通过 |
| `xcrun devicectl device install app --device F615EA70-0AFD-5E1A-9373-AECBD061688D frontend/ios/build/notion-auth-crash-20261101/release22/Payload/InkMemory.app` | 0 | 原iPhone16覆盖21为22 |
| `xcrun devicectl device process launch --device F615EA70-0AFD-5E1A-9373-AECBD061688D com.inkmemory.mobile` | 0 | 普通启动PID9817 |
| `device info apps`与`device info processes` | 0 / 0 | 读回0.1.0/22、安装路径与同一运行进程 |

安装路径为`/private/var/containers/Bundle/Application/2E699F32-1724-4938-9ACF-02899F568E68/InkMemory.app/`。本轮手机采用只执行安装、启动和元数据读取，手机真实Notion授权确认及资源读取未重新发起；原账号、授权记录及范围保留供用户从原入口继续。

## 当前交付状态

- **设计完成**：端侧默认浏览器、正常/异常/状态图、失败反馈及评审表完成。
- **技术验证**：模拟器旧版闪退复现与修复后实际Safari打开/返回/同步失败恢复通过；原生19项、Web七项、类型、文档及Hermes通过。
- **真机业务验收**：当前iPhone构建22覆盖安装及启动通过；真实Notion授权确认与后续资源读取继续独立验收。
- **发布状态**：构建22开发包已签名并安装；App Store和TestFlight发布未执行。

## 最终制品与复现脚本核对

Luna只读审计确认最终IPA为`iphoneos`、0.1.0/22、最低iOS16.4；包内`main.jsbundle`与正常产品Hermes逐字节一致。ntn/manifest/MIT及四份Python适配在22、21与当前对应源码间保持预期字节一致。应用配置、profile及凭证正文未被该审计读取或输出。

现有UI runner准备脚本新增可选同目录Swift测试源参数；默认DeckScroll行为保持。`ruby -c frontend/e2e/ios/prepare-ui-runner.rb`退出0；默认与`NotionLinksUITests.swift`项目生成均退出0，fileRef和Sources正确；目录外与缺失源分别退出1。复现入口为`ruby frontend/e2e/ios/prepare-ui-runner.rb <新的绝对临时目录> NotionLinksUITests.swift`。两次实际UIKit测试的完整xcodebuild argv与xctestrun合成环境变量已补入`runner/simulator/VALIDATION-RECEIPT.md`，临时runner清理状态同时保留。

最终`device info processes`退出0，构建22进程9817继续运行。当前制品及新增文档引用均存在；共享部署手册扩大历史扫描发现9个旧IPA引用目标缺失，该历史制品缺口单独保留，当前22链接与摘要核对通过。本轮清理范围仅本轮命名的模拟器fixture、UI runner、派生目录和临时Metro配置，普通制品、旧IPA及未知归属文件处理数均为0。

最终审计回执：`runner/final-audit-receipt.md`。
