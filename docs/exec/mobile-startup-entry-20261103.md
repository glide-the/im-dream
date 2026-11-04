<!-- [Input] 用户反馈首次开屏角色四周方框，以及每次打开显示1秒动画的要求。 -->
<!-- [Output] 透明占位修订、每次进入的展示规则、实现范围和定向验证回执。 -->
<!-- [Pos] 移动启动展示专项；产品规则归mobile-startup PRD，业务图归正式交互稿。 -->
<!-- [Sync] 2026-11-03: 保留原业务实例，以独立展示计时和透明宿主占位处理本轮反馈。 -->

# 开屏透明边缘与每次进入1秒展示

## 目标与执行范围

用户确认方框位于开屏角色四周，并要求每次打开App显示1秒动画。当前工作区为`ios-store`，含大量用户与其他任务改动；品牌名称继续读取现有Kastention常量。原登录、业务恢复、任务和数据保持原入口，APP-04暂停状态保持。本轮改动范围为启动展示及其透明占位。

### Optimized Prompt

检查首次开屏角色四周方框的实际资源及原生加载占位，复用已完成的透明SVG路径。统一首帧、RN加载和动画容器的透明边缘，保持角色轮廓和蓝白配色。每次冷启动及实际后台返回前台至少展示1秒，计入可见前台时间，诊断和登录窗口遮挡期间暂停；单纯inactive回到active沿当前周期。原业务页面在开屏覆盖下保持挂载，保留草稿、请求、任务、认证和恢复行为。完整呼吸周期为1秒，减少动态效果沿系统偏好。同步PRD、正式时序/状态图、目录合同，执行受控时钟、原登录回归和原生透明/布局合同检查，保留实际设备与完整包体采用边界。

本轮提示词优化一次。实施复用原StartupScreen、StartupArtwork、原AppState观察及准备Promise。

## 发现、判断与交付收敛

| 发现与问题 | 判断依据 | 选定处理 |
| --- | --- | --- |
| 开屏角色四周方框 | 当前Simulator安装包的StartupArtwork包含两份Vector记录，Image元数据Opaque=false；源路径无背景矩形 | 复用当前SVG，明确动画容器和Svg背景透明、borderWidth=0；原生imageView声明opaque=NO |
| 原生加载占位尺寸 | 当前RCTRootView.layoutSubviews只设置loadingView.center；Storyboard保留393×852画布尺寸 | StartupReactRootView在原layout后设置loadingView.frame=bounds，加载占位背景clear且isOpaque=false |
| 快速启动与再次进入 | 原画面由loading控制，成功会话可直接进入已有业务页 | 独立展示计时作为覆盖层，原服务启动与会话读取继续执行 |
| 一秒展示的页面归属 | 替换已登录页面会卸载草稿及页面状态 | 底层账户子树保持挂载，覆盖期间关闭触控和无障碍入口，结束后恢复 |
| 每次进入与系统窗口 | 后台返回与短暂inactive具有独立的用户操作来源 | 冷启动和实际background后重置1秒；inactive暂停剩余时长，active继续 |
| 动画节奏 | 原呼吸周期为2400ms | 共享UI规则定义1000ms展示及500ms单方向，形成完整1秒呼吸 |

边框处理依据为当前资源透明性和原生占位尺寸合同；用户所见首帧与新包的设备对照验收单列。设计评审通过，具体规则见[启动PRD](../prd/mobile-app/mobile-startup.md)，正常、恢复和状态图见[交互稿](../design/multi-platform/mobile-startup-interaction.md#每次打开的1秒开屏与透明占位2026-11-03)。

## 实施范围与验证影响

| 文件 | 职责与影响 |
| --- | --- |
| `src/components/startupPresentation.ts` | 当前产品指定的1秒展示、完整呼吸周期；独立于服务超时和任务期限 |
| `src/platform/useStartupPresentation.native.ts` | 使用单调时钟累计前台可见时间；effect重新读取当前AppState，接收原回调并清理自有timer |
| `src/platform/SessionGate.native.tsx` | 原启动/会话继续；保留账户实例并覆盖StartupScreen；诊断/登录遮挡暂停展示计时 |
| `src/components/StartupArtwork.native.tsx` | 显式透明、无容器边框及500ms单方向呼吸；原七条角色路径保持 |
| `ios/InkMemory/InkMemoryApp.swift` | 原加载占位适应宿主，原诊断Window和业务桥保持 |
| `ios/InkMemory/LaunchScreen.storyboard` | 原生角色imageView保持透明 |

隔离技术验证的业务范围：动画展示、透明边缘和视觉时长为变更项；原会话、Native初始化次数、账户页面、草稿和诊断为保持项；Project、Episode、canonical Artifact、Run-private `.dream`、after-turn Hook、PostgreSQL/API投影及真实模型为本轮范围外。

## 验证回执

回执目录：`/tmp/ink-startup-entry-20261103/validation/`。`luna_test_runner`执行定向检查，主Agent已读取实际日志、JSON和截图。使用本机已安装Chrome、已锁定依赖、隔离Vite和受控时钟；完整发布构建、设备安装、真实业务及原服务维护继续单列。

| 实际命令或阶段 | 退出码 | 关键输出 |
| --- | --- | --- |
| `corepack pnpm run native:typecheck` | 0 | Native TypeScript通过，含新hook与共享展示规则 |
| `corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | Web及fixture类型检查通过 |
| `corepack pnpm exec playwright test --config=.../playwright.startup-entry-20261103.config.mjs --grep=... --reporter=line --workers=1` | 0 | 最终5项定向用例通过，涵盖四项新增与原诊断返回 |
| 相同隔离配置的完整`native-session-gate.spec.ts` | 0 | 最终19/19通过，32.0秒；初次状态unknown、连续两次返回、诊断暂停补足及原登录场景通过 |
| 原组件的深浅色/390×844与390×320视觉用例 | 0 | 4/4通过；七条SVG路径、无图片或背景矩形、字体加载、操作命中及无溢出 |
| 已有截图内角色区域的像素取样 | 0 | 四个视口/主题各取角色范围内四角及相邻外侧四点，均与当前主背景相同 |
| `xcrun ibtool --warnings --errors --notices --target-device iphone --target-device ipad --minimum-deployment-target 16.4 --compile ... frontend/ios/InkMemory/LaunchScreen.storyboard` | 两平台各0 | iphoneos与iphonesimulator启动页资源编译通过 |
| `xcrun swiftc -frontend -parse frontend/ios/InkMemory/InkMemoryApp.swift` | 0 | 当前Swift语法通过；保留原诊断Overlay及桥接 |
| `corepack pnpm exec react-native bundle --platform ios --dev false --entry-file index.native.js --max-workers 2 --bundle-output ... --sourcemap-output ... --assets-dest ...` | 0 | 原普通入口打包通过；source map含新hook、规则及原组件，startup.png资源0 |
| 精确10份Markdown的引用、锚点和清单检查 | 0 | 60链接、98锚点，清单与引用通过 |
| 本机Chrome动态提取当前交互稿并渲染Mermaid | 0 | 18/18图生成SVG，console/page errors均0 |
| 本轮指定路径`git diff --check` | 0 | 格式检查通过 |

最终回执包括`full-entry-suite-final19.log`、`native-typecheck-final-race.log`、`web-typecheck-final-race.log`、`metro-inspection.json`、`visual-artwork-corners.json`、`docs-exact10-check.json`及`mermaid-interaction.json`。首轮时钟使用install后仍随真实时间前进，导航/断言耗时使999ms相对推进越过原期限；改为导航前冻结时钟后通过。原诊断用例首次17/18通过，余项在新一秒覆盖尚在途时读取观察者数量；补充等待开屏结束，再核对原观察者1，最终19项通过。早期失败回执保留。

初次AppState从unknown变为active的情况通过新增fixture核对：hook在effect中重新读取当前状态，覆盖原监听注册之前已发生的状态变化。该差异仅位于明确命名的测试平台边界，生产入口保持相同状态规则。

容量与原服务回执归`preflight.log`及`preflight-corrected-summary.json`。Mac物理内存16GiB；当时free页约142.5MiB，purgeable及inactive页分别记录，磁盘可用8.8GiB。串行检查使用原Metro两worker，无堆覆盖参数；本轮快照用于技术检查记录，完整发布构建容量另行核对。5173监听者为CoreSimulator的InkMemory PID71082；该进程和其他既有服务保持。日志中的8.8GiB归磁盘，未作为可用内存记录。

临时配置、spec及自有Chrome/Vite/Metro/Mermaid进程已清理。真实账户、数据库、业务正文、设备安装和服务操作为0。本轮完成源码、隔离页面、原生语法及资源合同验证；完整Xcode构建、手机首次开屏与安装采用继续单列。
