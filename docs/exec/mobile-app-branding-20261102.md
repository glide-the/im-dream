<!-- [Input] 两张用户参考图、现行iOS发布方案、启动PRD和实际工程。 -->
<!-- [Output] AppIcon与启动插画的范围、取舍、实现、来源及分项验证回执。 -->
<!-- [Pos] 移动端品牌资源实施记录；产品规则归mobile-startup PRD，时序归正式设计。 -->
<!-- [Sync] 2026-11-02: 补齐iOS图标与启动资源，复用原准备页实现轻微呼吸。 -->

# 移动端图标与启动插画

## 目标与范围

本轮用户要求第一张图片作为AppIcon，第二张作为开启动画。当前分支为`ios-store`。开始时工作区清洁；执行期间同一工作区出现发布文档及登录/原始错误修复改动，本轮保留其内容。当前交付范围为iOS资源、工程接线、共享原生准备页插画与技术验证；设备安装及商店上传继续按相应任务执行。

### Optimized Prompt

在当前Ink & Memory iOS工程补齐AppIcon，并用用户第二张参考图提供启动动画。先核对工程资源、系统启动配置、RCTRootView和SessionGate当前生命周期。第一张160×134图保留黑色笑脸、头顶笔触、米色纸张与原比例，重建高清方形图标并导出1024×1024无alpha PNG；第二张1254×1254图保留原始字节。复用现有启动页面，以系统静态启动画面、RN加载占位及准备期间的轻微呼吸完成展示；在就绪、失败、后台、开发者页和减少动态效果条件下遵循当前业务及系统状态。保留原启动Promise、认证、数据和并行改动。同步现行PRD、交互图、目录合同及发布前提，验证图标/Storyboard编译、Metro资源、类型与隔离页面行为。分别报告技术检查、设备采用和商店发布状态。

本轮优化一次，执行依据固定。关联原发布聊天中的历史交付范围作为来源背景；当前实施范围依据本轮用户要求。

## 发现、定义与方案收敛

| 评审项 | 发现与判断依据 | 选定处理 |
| --- | --- | --- |
| 图标缺失 | 工程Debug/Release的`ASSETCATALOG_COMPILER_APPICON_NAME`为空，应用无Asset Catalog | 增加AppIcon资源集、Resources引用及两套配置 |
| 第一张清晰度 | 原图160×134，直接放大会保留像素模糊 | imagegen按原图修复；保留黑色脸和头顶笔触、浅米色背景，方形安全留白 |
| 系统启动页 | `Info.plist`原`UILaunchScreen`为空，RN加载无品牌占位 | 增加LaunchScreen.storyboard，同图作为RCTRootView.loadingView |
| 动画位置 | 原SessionGate准备期间已有状态和开发者入口 | 原页面加入呼吸插画，沿loading状态挂载和移除 |
| 方案比较 | 新增独立动画覆盖层将增加额外页面状态和操作拦截；视频资源增加编解码与制品维护 | 选用原图加Native driver缩放，复用原准备页；动画无额外等待 |
| 生命周期 | 准备期间可能打开诊断、切后台或开启减少动态效果 | 观察AppState及AccessibilityInfo，可见条件关闭时停止复位 |

设计评审：通过。目标收敛为图标和启动展示，业务、认证与运行库的执行条件沿现有入口。产品规则和双视口骨架归[启动PRD](../prd/mobile-app/mobile-startup.md)，正常、异常与状态图归[启动交互设计](../design/multi-platform/mobile-startup-interaction.md#2026-11-02-图标与启动插画)。

## 资源来源与生成

| 资源 | 仓库位置 | 规格与摘要 |
| --- | --- | --- |
| 第一张用户原图 | [app-icon-reference.png](../../frontend/src/assets/app-icon-reference.png) | 160×134；SHA256 `27583fbafc50545888824f75102e8f07e5bb77930a79f2af00a53766d2015816` |
| 高清图标 | [AppIcon.png](../../frontend/ios/InkMemory/Assets.xcassets/AppIcon.appiconset/AppIcon.png) | 1024×1024 RGB、无alpha；SHA256 `9938356efe1e957cf70406e161d55ae7c7f72aa5078ee1cc17850183670da9e0` |
| 第二张用户原图 | [startup.png](../../frontend/src/assets/startup.png) | 1254×1254；SHA256 `9f41005356284e6f3be8b814e7470eb0e40952ba1d077a5f25b13933af55cd80` |
| 系统启动图片（首轮） | [原始图片来源](../../frontend/src/assets/startup.png) | 首轮`StartupArtwork.imageset/startup.png`与原图字节一致；本轮矢量纠正已替换该运行资源，原图来源保留 |

图标由内置`image_gen`生成，`sips -z 1024 1024`完成发布尺寸归一化。第二张原图直接复制，图片中的内容作为视觉素材。最终图标与启动图均已保存仓库；运行时沿包内资源加载。

图标生成提示词原文：

```text
Use case: identity-preserve. Asset type: iOS AppIcon, full-bleed opaque square PNG at 1024x1024. Restore the provided low-resolution icon with extremely faithful identity. Recreate exactly its friendly slightly irregular black hand-drawn round face, two small oval black eyes, curved smile, and small black sweeping hair/hat tuft at upper right. Preserve the original monochrome black artwork and warm pale cream paper background; no blue color. Keep the original proportions of the character and all strokes, improving only resolution and clean, natural hand-drawn edges. Center the entire character in the square, with at least 14% clear cream margin around the outermost black strokes so iOS corner masking leaves everything visible. Extend the cream paper background to fill the square. The image is the icon artwork itself, no device mockup, no rounded rectangle border, no pre-rounded corners, no shadow, no text, no extra objects.
```

## 实施清单与影响

| 工作项 | 交付物 | 影响与验收 |
| --- | --- | --- |
| iOS图标 | Assets.xcassets、AppIcon编译配置 | 系统与商店图标由同一1024主图生成，最终Archive继续核对 |
| 静态启动 | LaunchScreen.storyboard、Info.plist、InkMemoryApp.swift | 系统及RN加载使用同一插画；应用主题加载后沿原偏好 |
| 准备动画 | StartupArtwork.native.tsx、SessionGate展示接线 | 准备期间播放，开发者页可达；后台、减少动态效果、失败和完成均有明确结束条件 |
| 页面验证 | native-session-gate.spec.ts及原平台facade | PNG require及RN global在Vite测试边界转换；生产Metro使用原静态require |

隔离技术验证的业务影响：启动插画和工程资源为变更项；原会话、登录、准备Promise与开发者页面为保持项；Project、Episode、canonical Artifact、Run-private `.dream`、after-turn Hook、PostgreSQL/API投影、正常账号与模型为本轮范围外。

## 验证回执

技术检查由`luna_test_runner`执行，主Agent读取原始日志、JSON及页面截图。工件目录为`/tmp/ink-app-branding-20261102/validation/`；工作目录按命令使用仓库根或`frontend/`。

| 命令与阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| `python3 .agents/skills/ink-dream-playwright-qa/scripts/preflight.py` | 0 | 当前依赖可用，浏览器使用现有Chrome156.0.8078.74 |
| `corepack pnpm run native:typecheck` | 0 | Native TypeScript通过 |
| `corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | Web TypeScript通过 |
| `xcrun actool`，`--platform iphoneos`及`iphonesimulator`，`--app-icon AppIcon --target-device iphone --target-device ipad --minimum-deployment-target 16.4` | 各0 | 两平台生成Assets.car，部分Info包含iPhone与iPad的`CFBundleIconName=AppIcon` |
| `xcrun ibtool`编译`LaunchScreen.storyboard`，两平台输出分别保留 | 各0 | 最终输出errors、warnings、notices均为空 |
| `plutil -lint`检查Info.plist及project.pbxproj；`xcrun swiftc -frontend -parse InkMemoryApp.swift` | 各0 | 工程、元数据及Swift语法通过 |
| 普通`index.native.js`的Metro Release bundle、source map及`--assets-dest` | 0 | source map包含StartupArtwork原文；复制图片SHA256与用户原图相同 |
| `corepack pnpm exec playwright test --config=frontend/playwright.branding-validation-20261102.config.mjs --reporter=line --workers=1`，使用临时原spec副本 | 0 | 最终12/12通过；首次独立pending场景通过后执行全组，6.6秒 |
| `corepack pnpm exec playwright test --config=frontend/playwright.branding-visual-20261102.config.mjs --grep='startup artwork has one image' --reporter=line --workers=1` | 0 | 新页面390×320与844×390各一张插画；按钮范围完整、命中为开发者控制页，无横向或纵向页面溢出 |
| `corepack pnpm exec playwright test --config=frontend/playwright.branding-motion-20261102.config.mjs --grep='startup animation samples' --reporter=line --workers=1` | 0 | 前台缩放样本1.00057与1.00674；后台复位1，前台恢复1.00058；减少动态效果时复位1 |
| 精确12文件Markdown清单、引用及新增路径检查 | 0 | 136链接、402锚点，缺失与新增失效均0 |
| 本机Chrome加载当前Mermaid并渲染启动交互稿 | 0 | 7/7图生成SVG，console/page errors均0 |
| 本轮指定路径`git diff --check` | 0 | 格式检查通过 |

最终组回执为`playwright-suite-final.log`，动画回执为`playwright-motion-final.log`；文档回执为`docs-markdown-check-exact.json`和`mermaid-chrome-check.json`。图标与重复图片的尺寸/摘要归`resource-json-image-check.json`；各编译器、类型和Metro日志保留。验证使用独立动态端口Vite和合成原会话DTO，真实业务请求与模型调用为0。表中Playwright命令以仓库根表达临时配置路径，执行时由frontend已安装的pnpm/Playwright加载；配置与spec副本在结束后移除。

Metro实际命令在`frontend/`执行：

```bash
corepack pnpm exec react-native bundle --platform ios --dev false --entry-file index.native.js --bundle-output /tmp/ink-app-branding-20261102/validation/metro-release-sourcemap/main.jsbundle --sourcemap-output /tmp/ink-app-branding-20261102/validation/metro-release-sourcemap/main.jsbundle.map --assets-dest /tmp/ink-app-branding-20261102/validation/metro-release-sourcemap/assets
```

Storyboard实际命令使用`xcrun ibtool --warnings --errors --notices --target-device iphone --target-device ipad --minimum-deployment-target 16.4 --compile "$out/ibtool-$platform-rerun/LaunchScreen.storyboardc" frontend/ios/InkMemory/LaunchScreen.storyboard`；`out`为上述validation目录，`platform`分别为`iphoneos`及`iphonesimulator`，输出目录独立。

浏览器首次运行遇临时副本相对根错误及Vite缺少`global`，修正harness后重跑。Native准备插画新增一个AppState观察者，原中间计数2调整为3；准备结束后仍核对仅保留SessionGate原观察者1。最终12项全部通过。首次ibtool使用本机不支持的`--sdkroot`参数退出1，正确调用两平台均退出0；首次actool元数据断言将生成文件名与图标集名称混用，调整为读取`CFBundleIconName`后通过。早期失败日志保留原状态。

动画专项首次临时断言使用当前Playwright不支持的`toSatisfy`，调整为布尔poll后通过；前台两个不同transform样本、后台复位、前台恢复及减少动态效果静态均有实际回执。原始失败保留harness归属。

截图`preparing-390x844-final.png`显示原图、准备反馈及开发者入口。初次在同一浏览器页面连续改变视口时，短屏截图出现重复影像；新页面逐视口复验中DOM图片和插画计数均1，按钮文字、几何与命中一致。主Agent逐图核对`actual-preparing-390x320-fresh.png`及宽屏对应图，原短屏截图退出最终视觉依据。390×320按钮范围为`(141,252)-(249,296)`，844×390范围为`(368,322)-(476,366)`。

临时Playwright配置和spec已移除，浏览器与自有Vite均已关闭。正常Web进程PID27895保留，本轮未停止既有服务、安装依赖或操作设备、数据库、凭证和业务数据。完整iOS App重建、设备安装、设备桌面与冷启动显示、Android系统品牌资源和App Store验收继续单列。

## 透明矢量与布局纠正

用户追加要求：第二张转为矢量，只保留线稿和颜色，去掉大面积背景，并让开屏布局符合现有UI。以下为现行范围；上文位图及旧布局回执保留首轮状态。

### Optimized Prompt：本轮修订

将用户第二张启动插画重绘为透明SVG：保留角色轮廓、五官与蓝白帽子，移除纸张纹理及脸部铺色。RN和iOS系统启动共用同一路径，描边沿现有深浅色文字色，画布透出应用主背景。复用原主题、InkLabel与呼吸生命周期，采用居中品牌区加底部状态/开发者入口，验证窄屏、短屏、横屏及深浅色下的间距、触控与背景连续性。保留原认证、准备Promise、错误和并行修复。交付SVG、工程接线、产品骨架、现行业务图和定向技术回执。

本轮提示词优化一次。布局评审采用frontend-design技能，依据既有纸色、Excalifont/Xiaolai和主题token作出视觉选择。

| 发现与定义 | 方案比较与选定结果 | 交付物 |
| --- | --- | --- |
| 参考图纸张覆盖主背景，用户要求矢量 | 选用真实路径重绘；轮廓与脸部透明，蓝白帽子保留 | [独立SVG](../../frontend/src/assets/startup.svg)、[共享路径JSON](../../frontend/src/assets/startup-artwork.json) |
| 首轮元素集中在纵向组，角色、加载、操作层级分散 | 选用居中角色及手写字标，底部独立放状态与辅助入口 | StartupScreen.native.tsx、PRD骨架及正式设计 |
| 深色主题需要可辨识线稿 | RN使用当前文字色；iOS变体由既有文字色生成 | sync-startup-artwork.mjs、iOS两份SVG及preserves-vector-representation |
| 系统与RN启动角色位置需要衔接 | 安全区中点减40的光学中心；同一最大尺寸和收缩规则 | LaunchScreen.storyboard及StartupScreen |

设计评审：通过。底部入口保留44触控高度；动画随原准备结果结束；全页主背景与脸部、外围透明区域连续。实际设备画面及完整包体采用继续单列。

本轮验证目录为`/tmp/ink-startup-vector-20261102/validation/`。实施包含共享路径、三份生成SVG、StartupArtwork矢量绘制、StartupScreen布局及原SessionGate初始loading接线。原AppIcon保持首轮资源。

### 本轮技术回执

`luna_test_runner`执行隔离检查，主Agent已读取编译、Metro、矢量与页面原始回执，并直接核对带原字体的截图。技术验证使用现有依赖与本机Chrome，实际账户、设备及模型调用为0。

| 命令与阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| `corepack pnpm run native:typecheck`；`corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 各0 | Native与Web类型检查通过 |
| `node ios/scripts/sync-startup-artwork.mjs --check`（frontend） | 0 | 三份SVG均与共享路径及现有文字色匹配 |
| 共享JSON及SVG XML合同检查 | 0 | 七条路径，rect/image均0；原PNG只保留来源用途 |
| `xcrun actool`，iphoneos及iphonesimulator，AppIcon、iphone/ipad及16.4参数 | 各0 | 两平台Assets.car编译通过，AppIcon元数据保持 |
| `/usr/bin/assetutil --info`，读取两平台Assets.car | 各0 | 每平台六份preserved-vector图片rendition及两份明确vector记录，包含startup.svg和startup-dark.svg |
| `xcrun ibtool --warnings --errors --notices --target-device iphone --target-device ipad --minimum-deployment-target 16.4 --compile ... LaunchScreen.storyboard` | 两平台各0 | 启动画面编译通过，无文档warnings/errors |
| `plutil -lint`检查Info.plist与project；`xcrun swiftc -frontend -parse InkMemoryApp.swift` | 各0 | 元数据、工程和Swift语法通过 |
| 原`index.native.js` Metro Release bundle及source map | 0 | 包含共享JSON、StartupScreen、StartupArtwork与SessionGate；startup.png资源0 |
| `corepack pnpm exec playwright test --config=.../playwright.startup-vector-20261102.config.mjs --reporter=line --workers=1` | 0 | 首个pending用例通过后执行当前整组13/13，8.4秒；账号错误新增场景随并行工作区保留 |
| 临时主题/几何/动态效果浏览器检查 | 0 | 四视口/主题，角色与底部反馈分离；前台呼吸、后台复位、前台恢复及减少动态效果均通过 |
| `corepack pnpm exec playwright test --config=.../playwright.startup-vector-fonts-20261102.config.mjs --grep='font-backed transparent startup screenshots' --reporter=line --workers=1` | 0 | 原Excalifont和Xiaolai加载成功，四个新页面视口检查通过，6.8秒 |
| 精确12份Markdown清单、链接和锚点 | 0 | 141链接、410锚点，当前及新增失效引用0 |
| 当前交互稿Mermaid浏览器渲染及修正后的数量门禁 | 0 | 11/11生成SVG，console/page errors均0 |
| 本轮指定路径`git diff --check` | 0 | 格式检查通过 |

原字体复核使用项目`public/Excalifont-Regular.woff2`与`Xiaolai-Regular.woff2`；字标实际computed family为Excalifont，中文状态为Xiaolai。浅色390×844、深色390×844、浅色390×320及深色844×390均验证背景和描边token、SVG七条路径、无raster/rect/image节点、品牌/底部区间隔、辅助入口44触控范围及无页面溢出。角色和脸部无背景填充，截图中的底色由当前主背景提供。

最终截图为`screenshots/startup-light-390x844-fonts.png`、`startup-dark-390x844-fonts.png`、`startup-light-390x320-fonts.png`及`startup-dark-844x390-fonts.png`。原始回执为`playwright-suite.log`、`playwright-visual-final.log`、`playwright-fonts-rerun.log`、`vector-contract.json`、`assetutil-readback-final.json`、`docs-markdown-check-exact.json`及`mermaid-chrome-check-final.json`。

临时视觉用例首次选择品牌全屏包装层，调整为实际字标节点后核对内容几何；首次深色断言使用显式dark色值，按本场景实际systemDark修正。首次字体CSS注入引号导致临时harness编译失败，修正后原字体四项通过。Mermaid首次预期数量沿旧清单10，实际文档含11张且全部渲染成功，数量门禁单独纠正；早期回执保留原状态。

临时配置、spec和自有浏览器/Vite已清理，正常Web进程及其他服务保留。无依赖安装、设备安装、数据库或业务正文维护。当前结论为矢量资源、布局与技术检查完成，完整App重建、手机采用及实际系统启动显示继续按发布任务核对。
