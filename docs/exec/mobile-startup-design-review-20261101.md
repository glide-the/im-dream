<!-- [Sync] 2026-11-02: iPhone24覆盖安装、版本/进程读回及数据metadata核对完成，首次失联回执保留。 -->
<!-- [Sync] 2026-11-01: 按用户要求追加原始错误日志，验证与安装结果单独记录。 -->
<!-- [Sync] 2026-11-01: 完成模拟器两入口、启动结果、复制与前后台验证，原Web已恢复；配置/目录错误独立保留。 -->
<!-- [Sync] 2026-11-01: 用户授权实现后追加四个源码文件和定向验证，前阶段文档记录保持。 -->
<!-- [Sync] 2026-11-01: 本次交付改为独立PRD及独立交互设计，实施与验收范围保持。 -->
<!-- [Sync] 2026-11-01: 移动应用PRD迁至docs/prd/mobile-app/mobile-app.md，更新现行引用，保留历史回执。 -->
<!-- [Input] 用户纠正、现有后台启动调用链与原业务约束。 -->
<!-- [Output] 最小异步启动方案、评审与必要验证。 -->
<!-- [Pos] 移动异步启动设计记录；仅文档修订。 -->
<!-- [Sync] 2026-11-01: 按用户纠正删除热点优化、基线前置与扩展监测实施项。 -->
# 移动异步启动最小方案评审

当前阶段：源码实现、隔离技术回归及iPhone16 Plus / iOS18.6模拟器专项已完成，采用与剩余问题见文末。下方设计阶段和历史回执保留各自范围；物理设备与完整真实业务验收未执行。

## 背景与问题

用户将范围收敛为Python异步启动、最小改动和最小探索。依据前轮已核对的直接调用链，`EmbeddedDreamBackend`已有后台队列，RN已有effect启动和共享Promise。现有异步路径直接复用；本轮沿原授权只修订文档。

前稿原文及图示保留于[历史记录](../design/multi-platform/history/mobile-startup-expanded-draft-20261101.md)。性能热点分析、基线前置、Python内部并发/延后初始化、新Native快照和分段埋点均退出实施项。

## 目标与边界

交付[独立交互与技术设计](../design/multi-platform/mobile-startup-interaction.md)及[独立PRD](../prd/mobile-app/mobile-startup.md)。程序实现、依赖安装、打包、设备安装保持后续范围。已有用户和其他Agent改动保持。

## 概念与规则

原Native后台初始化与内部顺序保持。前端直接渲染原准备视图，原effect发起启动；就绪后执行原认证和业务读取。开发者页只观察JS启动结果，保存开始/结束、更新时间和安全错误，总耗时直接计算；不读取原始日志或新增网络探测。登录、权限、输入、任务、停止和恢复继续原规则。

### 设计评审

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 异步启动 | Native后台队列与JS共享Promise已存在 | 直接复用 | Python内部改造数为零 | 后续最小接线验证 |
| 前端等待 | 业务依赖原就绪和认证 | 准备视图直接呈现，开发者页独立可达 | 保留原业务条件 | 页面入口实现 |
| 最小状态 | 原Promise已有完成与拒绝结果 | 原JS管理器保存结果和总耗时 | 新Native方法、分段记录、配置键均为零 | JS状态读取与观察 |
| 开发者页 | 原关于入口可复用 | 同一只读页，准备视图增加入口 | 刷新和复制现有状态 | 页面实现 |
| 探索与验证 | 直接调用链已足够判断 | 删除性能专项和基线前置 | 无新增环境探索或监测平台 | 聚焦验收 |

**评审结论：通过。** 完成最小方案与文档修订，程序和设备验收未执行。

## 接线完成与剩余验收

1. 已完成：原`BackendRuntimeManager`共享Promise保存并公开最少状态及观察；Native和Python启动保持。
2. 已完成：原准备视图与关于接入同一只读开发者页，保留原登录和业务门禁。
3. 技术验证按文末命令回执登记；下表的目标平台与真实业务资格继续待执行，性能采样和监控建设退出实施前提。

## 验收计划

| 场景 | 预期结果 | 验证方式与前提 | 证据 |
| --- | --- | --- | --- |
| 后端尚未完成 | 原框架可见、开发者页可进入，业务仍等待 | 后续公开入口技术检查控制原启动Promise完成时机 | 可操作页面与原业务门禁；待执行 |
| 就绪或失败 | 就绪后原会话流程继续；失败显示安全错误 | 原正常启动及有界失败依赖 | 原启动结果、页面反馈；待执行 |
| 重复启动、前后台及重开 | 复用原实例和原恢复；观察正确释放 | 原入口及生命周期合同检查 | 启动计数、输入与监听；待执行 |
| 登录及网络失败 | 原登录、权限及各项读取重试保持 | 原接口技术回归，设备按后续授权执行 | 原响应与恢复反馈；待执行 |
| 刷新和复制 | 只读取已有状态，摘要脱敏 | 固定安全状态及原复制适配 | 新启动/网络调用0，原位置反馈；待执行 |

## 精简阶段文档验证回执

前轮检查属于[历史前稿](../design/multi-platform/history/mobile-startup-expanded-draft-20261101.md)对应内容。本次由`luna_test_runner`完成定向检查，主Agent已读取原始JSON回执。验证脚本及回执目录为`/tmp/ink-mobile-startup-design-20261101-01a196d5/validation/`。

| 命令（上述目录） | 退出码 | 关键输出 |
| --- | --- | --- |
| `python3 correction-doccheck.py` | 0 | 10份文档、216个链接、59个源码引用、89个锚点，缺失0；历史原文代码块正确排除 |
| `python3 correction-semantic-check.py` | 0 | 当前范围与精简方案一致；十路径`git diff --check`退出0 |
| `node correction-mermaid-chrome-check.mjs` | 0 | 20/20图解析通过；只复用本机Chrome和已安装依赖，本轮上下文和临时profile已清理 |

程序、性能及设备验收均未执行；本轮没有新增源码探索、程序改动、依赖安装、打包或设备操作。

## 独立文档整理与验证

按用户要求，将本次功能正文迁至独立PRD和独立交互设计；总移动文档保留原章节入口。原四张交互图随正文迁移，产品骨架分为启动页和开发者页。已有移动PRD业务目录迁移及其他工作区改动保持，程序未修改。本文仍负责后续实施和验收计划。

指定`luna_test_runner`已执行`python3 /tmp/ink-mobile-startup-design-20261101-01a196d5/standalone-20261101/validation/migration-check.py`，最终退出0；10份文档、275个链接、59个源码引用、140个标题锚点检查通过，十路径`git diff --check`退出0。首次验证脚本执行因脚本自身语句错误退出1，修正验证脚本后重跑，仓库文档未因该错误改写。

独立设计的4张图与迁移前交互正文逐字一致，架构16张图保持；复用前轮已通过的Mermaid语法结果，本次未重复启动浏览器。原始回执归同目录`migration-check.json`，主Agent已读取。以上为文档验证，程序和设备验收均未执行。

## 源码实施与技术验证（2026-11-01）

| 文件 | 本轮实现 | 验证关注点 |
| --- | --- | --- |
| `frontend/src/runtime/BackendRuntimeManager.ts` | 原共享Promise增加内存状态、开始/结束及单调总耗时、闭集错误；观察原会话读取结果 | 并发调用共享一次启动，诊断不读取Native或发HTTP；原返回值保持 |
| `frontend/src/components/RuntimeDiagnostics.native.tsx` | 同一只读页、原位置反馈、固定安全摘要与现有copyText、AppState暂停和解除观察 | 刷新只重读，凭证/正文/地址保持私有，复制失败恢复 |
| `frontend/src/platform/SessionGate.native.tsx` | 原准备与会话检查反馈、覆盖诊断页、原会话结果观察；本地失败提示重开 | 认证/身份释放保持；诊断打开期间启动完成仍保留页面，返回当前原业务 |
| `frontend/app/_dream/components/AboutView.native.tsx` | 关于入口打开同一组件，返回原关于 | 不重建底层Business，原输入与任务保持 |

Native、Python、内部初始化顺序、资源策略、HTTP协议、依赖与数据库改动为零。原App组合和其他未提交写作/聊天修复保持。新增技术场景复用`native-session-gate.spec.ts`的公开组件及显式测试侧Native facade，使用隔离Vite与合成原会话DTO；Project/Episode/Artifact/Run-private/Hook/正常数据库与真实模型均退出本轮技术检查范围。

指定`luna_test_runner`完成Native/Web类型检查，以及原会话、设置分类和导航的隔离浏览器检查。主Agent已读取原始日志与JSON回执。当前实现尚未打包安装；技术回执不能代表真实iOS/Android页面、系统挂起或真实业务验收。

命令工作目录为`frontend/`，本轮临时配置为`/tmp/ink-mobile-startup-implementation-20261101/validation/native-playwright.config.mjs`，配置仅使用现有本机Chrome与spec自有动态端口Vite。

| 命令或阶段 | 退出码 | 关键结果 |
| --- | --- | --- |
| `pnpm run native:typecheck` | 0 | 当前原生TypeScript通过，覆盖新增页面和SessionGate接线 |
| `pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | Web类型通过，新增测试facade调整后复验通过 |
| `pnpm exec playwright test --config=/tmp/ink-mobile-startup-implementation-20261101/validation/native-playwright.config.mjs e2e/native-session-gate.spec.ts e2e/native-settings-categories.spec.ts e2e/native-settings-navigation.spec.ts --reporter=line --workers=1` | 1 | 首轮25通过、7失败；设置分类15项通过，初次失败与修订见下文 |
| 同配置，定向`e2e/native-session-gate.spec.ts e2e/native-settings-navigation.spec.ts` | 1 | 第二轮15通过、2失败；启动/登录/诊断11项全部通过，设置导航剩余两项旧harness断言待修订 |
| `pnpm exec playwright test --config=/tmp/ink-mobile-startup-implementation-20261101/validation/native-playwright.config.mjs e2e/native-settings-navigation.spec.ts --reporter=line --workers=1` | 0 | 最后6/6通过，9.1秒；原选择状态断言保留 |
| `python3 /tmp/ink-mobile-startup-implementation-20261101/validation/doccheck-implementation.py` | 0 | 24路径、16份Markdown、231个链接、63个源码引用、180个锚点，缺失0；同scope的`git diff --check`退出0 |
| `node /tmp/ink-mobile-startup-implementation-20261101/validation/mermaid-chrome-check-implementation.mjs` | 0 | 本机Chrome真实DOM中20/20图生成SVG成功；历史四重围栏正文排除 |

首轮新增诊断用例发现底层原业务视图缺少浏览器语义隐藏，`SessionGate`增加`aria-hidden`并保留组件挂载及原Native属性，复跑11/11通过。设置导航的6项前置失败来自fixture使用过期导出名，修订为共享文件的现行别名；随后两项断言分别受嵌套Deck标签和Native selected到RNW的映射缺项影响。断言限定到原Work tablist，并在测试facade补充selected的ARIA投影，生产设置逻辑保持；6/6通过。最终三个spec共32个独立场景按上述分轮结果通过，未将早期失败记为成功。

最终场景覆盖准备期间可进入、重复启动共享、启动完成时诊断页保持、失败/摘要脱敏、只读刷新、复制失败恢复、AppState暂停/释放、关于返回与原草稿，以及原登录、身份释放和设置流程。两视口为390×844及1280×800，检查无横向溢出、操作区可见。最终用例无pageerror或应用console error；`transformWithEsbuild`弃用提示保留harness归属。

完整日志保存在`/tmp/ink-mobile-startup-implementation-20261101/validation/`：`playwright.log`、`playwright-targeted-rerun.log`、`playwright-settings-navigation-rerun.log`、`doccheck-implementation.json`及`mermaid-chrome-check-implementation.json`。隔离组件截图为同临时根的`startup-diagnostics-pending.png`和`startup-diagnostics-ready.png`。runner已关闭本轮Chrome、Vite及Playwright，无残留自有进程，用户Chrome及正常服务保持。

本轮无依赖安装、Next/原生打包、设备安装、真实账号/模型调用、数据库或部署操作。真实平台页面、前后台系统挂起、实际剪贴板和正常业务验收保留后续范围。

## 模拟器验证（2026-11-01）

用户授权在模拟器测试后，采用现有iPhone16 Plus / iOS18.6模拟器，保留原`com.inkmemory.mobile`数据。复用已安装0.1.0/17的Native、Python、Next与资源，仅在自有副本中更新普通`index.native.js`入口的Hermes字节码；此结果限定当前前端接线，Native整包的当前源码构建资格另列。

| 操作或证据 | 结果 | 范围 |
| --- | --- | --- |
| runner执行原Metro bundle、现有hermesc编译 | 均退出0 | source map中4个本次源码逐字匹配；HBC5701619字节，SHA256 `dddad9eebe98c76b788e12770adc8ceef4621b29acbb911d8a5857afe32e3413` |
| 自有副本ad hoc签名、deep/strict核对、`simctl install` | 均退出0 | 原安装覆盖；数据目录inode183813951保持，未卸载或清理 |
| 普通启动与准备页入口 | 通过 | 实际Hermes页面显示准备状态，启动尚未结束时可点击进入开发者页 |
| 刷新、返回及启动失败反馈 | 通过 | 原位置显示状态已刷新；启动失败仍可进入页面，返回显示原恢复说明 |
| 原生复制及`simctl pbpaste` | 通过 | 页面显示复制成功，系统剪贴板201字符；固定诊断头及白名单字段匹配，无凭证/正文/地址 |
| Home后台与普通返回 | 通过 | 观测暂停、操作禁用；回到前台恢复取样，原启动时间和结果保持 |
| 本地启动成功与设置关于入口 | 通过 | 用户授权暂停原Web后，实际App独占`::1:5173`，本地ready耗时11115ms；原会话重试一次后进入主页，再经更多/设置/关于打开同一页 |
| 就绪后的刷新、复制、返回和前后台 | 通过 | 原开始时间/耗时及App PID32253保持；系统剪贴板读回ready/available安全摘要，返回原关于页 |
| 原配置与Agent目录读取 | 保留失败 | 页面仍显示配置和目录读取失败；本轮未定位该问题，完整业务可用性继续待验收 |

经用户显式授权，核对原Web的PID、frontend工作目录及`pnpm run dev --hostname localhost --port 5173`命令后，临时停止其Next CLI。释放端口后，Simulator App成为5173的实际监听者并成功就绪；原失败console记录为`listen EADDRINUSE ... ::1:5173`。测试结束停止本轮App，按原目录和命令恢复Web，当前Node PID27895监听同一地址，`curl http://localhost:5173/`返回200。原账户数据、其他服务及物理设备保持；模型和消息提交为零，未执行直接数据库维护。

本轮工件归`/tmp/ink-startup-simulator-20261101/`：`before.json`、`install-receipt.json`、`installed.json`、`clipboard-receipt.json`、`ui-receipt.json`和私有`cold-console.log`。原始包与运行数据保留，编译生成物仅位于本轮临时目录。

### 本轮收尾与验收边界

本次模拟器采用的是原0.1.0/17 Native/运行资源与本轮普通入口Hermes，四个改动文件的source map内容匹配当前工作区。模拟器UI通过电脑使用工具逐步操作并读取实际辅助功能树，未将浏览器fixture结果替代模拟器回执。原账户恢复和页面读取沿普通生产入口；未新建账户、Thread或模型任务。

本轮实际通过准备中可进入、端口失败反馈、成功就绪、两处入口、只读刷新、原生剪贴板及前后台观察。原会话首次读取失败、用户入口重试后有效；配置与Agent目录错误保持独立记录。11.115秒为本次初始化观测值，性能提升及真机耗时未验收。

恢复回执归`web-pause-restore.json`，首页探测退出0、HTTP200；原账户目录inode保持。已安装本次前端并保留Simulator，测试App已退出以释放5173，原Web正常运行。Simulator与本机Web需独占该配置端口；再次同时启动会产生相同冲突。网络行为核对参考[Apple Simulator资源说明](https://developer.apple.com/library/archive/documentation/IDEs/Conceptual/iOS_Simulator_Guide/TestingontheiOSSimulator/TestingontheiOSSimulator.html)及[微软iOS Simulator主机网络说明](https://learn.microsoft.com/en-us/dotnet/maui/data-cloud/local-web-services?view=net-maui-8.0#ios-simulator)，本机冲突结论依据实际console和lsof。

### 最终文档检查

指定runner执行`python3 /tmp/ink-startup-simulator-20261101/validation/final-doccheck.py`，修正临时验证脚本自身语法后最终退出0；7份文档、36个链接、5个源码引用、55个锚点及采用/恢复回执一致。相同7路径`git diff --check`退出0。原始失败和最终结果保留于本轮validation目录；未重跑已通过的图示、组件测试或业务服务。

## 原始错误日志补充（2026-11-01）

用户明确要求控制页展示启动错误原文。现有页面仅保存通用code，既有NSError.userInfo携带底层描述；Next Worker的具体监听错误原先仅输出console。范围收敛为沿现有返回链传递原文，在同一控制页展示并复制。

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 原始启动原因 | Native桥携带userInfo，页面只显示通用code；Next具体错误仅在console | 原样保存Error字段和userInfo；沿现有Worker/status返回Next原文 | 同一错误块首行展示NSLocalizedDescription，完整详情及堆栈保持 | 技术及模拟器回执见后文 |
| 记录数量与来源 | 通用日志平台超出本次范围 | startup/session/config/catalog各保留本次进程最近一次错误 | 固定来源、内存保存、同来源覆盖、恢复后保留 | 进程重开重新记录 |
| 读取与重试 | 刷新应只读取已有状态 | 复用getSnapshot/subscribe及copyText | 原请求/取消/权限与运行实例保持 | 原业务失败继续原入口重试 |
| 页面交互 | 需要查看错误内容与复制 | 同页纵向滚动，原文可选择，固定刷新及复制诊断摘要 | 独立PRD骨架、正式设计与源码一致 | 物理设备待后续采用 |

设计评审：通过。源码已接入，技术检查与模拟器采用记录在本节后续回执；真实业务与物理设备验收单列。此前阶段的脱敏摘要回执保留为当时实现记录，现行规则以独立PRD和本节为准。

### 原始错误技术验证

指定`luna_test_runner`执行本轮隔离验证，工件归`/tmp/ink-startup-error-log-20261101/validation/`。原始命令日志保留；使用已安装依赖与Chrome，模型、数据库和正常服务调用为零。

| 命令 | 退出码与关键输出 | 证据范围 |
| --- | --- | --- |
| `pnpm exec tsc --noEmit --pretty false`（frontend） | 0 | Web类型合同 |
| `node --check frontend/ios/runtime/host.cjs`及`worker.mjs` | 各0 | Node语法 |
| `node frontend/ios/scripts/check-host-auth-env.mjs` | 0，22 cases / 0 failures | 环境、回调、重复启动、错误原文与原console输出 |
| `.venv/bin/python -m pytest -q tests/test_mobile_web_startup_errors.py`（backend） | 0，2 passed | 原控制帧长错误原文与code回退；内存fixture |
| `pnpm exec playwright test --config=/tmp/ink-startup-error-log-20261101/validation/native-playwright.config.mjs e2e/native-session-gate.spec.ts e2e/native-chat-setup.spec.ts --reporter=line --workers=1`（frontend） | 0，20 passed | 原始错误展示/复制、Error非枚举字段、最近错误覆盖、恢复保留、原认证/读取/取消及只读观察 |

首次`pnpm run native:typecheck`退出2，指出日志标题向`InkLabel`传入多个children；已改为单一模板字符串。随后错误块移至启动状态下方，定向复核与工件结果见后续回执。

后续`pnpm run native:typecheck`退出0。错误块顺序更新后的`native-session-gate.spec.ts`定向复核退出0，12 passed；原认证、只读刷新、后台观察及原文复制保持通过。原Metro bundle与Hermes编译均退出0，source map中RuntimeDiagnostics、SessionGate、AboutView与BackendRuntimeManager逐字匹配；HBC5705408字节，SHA256 `c089ce7559920f464321d9447c245fb009711af1c9b4861b987d4a1ae6215557`。

`python3 /tmp/ink-startup-error-log-20261101/validation/error-log-doccheck.py`退出0，12份Markdown、39链接、5源码引用、100锚点；指定12路径`git diff --check`退出0。`node /tmp/ink-startup-error-log-20261101/validation/error-log-mermaid-chrome.mjs`退出0，4/4 SVG，Chrome console/pageErrors为空。文档验证限定清单、引用和图示，程序与目标设备回执分别记录。

### 原始错误模拟器验证

复用iPhone16 Plus / iOS18.6及原0.1.0/17 Native，仅覆盖当前普通入口Hermes与现有host.cjs、worker.mjs、ios_claude_transport.py三份资源。原安装资源与本轮修改前基线逐字相同；原生代码、依赖、端口和认证配置保持。签名、deep/strict核对与`simctl install`均退出0；已安装HBC摘要与本轮编译工件匹配，数据目录inode183813951保持。

| 操作或证据 | 结果 | 边界 |
| --- | --- | --- |
| 普通启动与准备期打开控制页 | 通过 | 原准备视图可操作，最初显示正在启动及当前没有错误记录 |
| 实际启动失败原文 | 通过 | CUA实际AX树及截图显示`Error: listen EADDRINUSE: address already in use ::1:5173`，errno -48、syscall listen、端口和原堆栈完整保留 |
| 原错误显示位置 | 通过 | 启动状态下方直接显示错误日志，NSLocalizedDescription在首行，原code/userInfo/nativeStackIOS保留 |
| 手动刷新 | 通过 | 显示状态已刷新，原错误及23:25:06更新时间保留；本次失败耗时35854ms |
| 系统复制 | 通过 | 显示诊断摘要已复制，`simctl pbpaste`退出0；3433字节摘要包含EADDRINUSE、errno、userInfo和nativeStackIOS |
| 本机服务与数据 | 保持 | 本轮借现有冲突验证原文，未暂停原Web；PID27895及HTTP200保持，原账户目录inode保持 |

本轮App已退出，已安装改动保留；自有console启动会话随App退出结束。工件归`/tmp/ink-startup-error-log-20261101/`的`before.json`、`resource-receipt.json`、`install-receipt.json`、`ui-receipt.json`、`clipboard.txt`及`cleanup-receipt.json`。UI证据来自CUA原生页面观察及系统剪贴板读回；`cold-console.log`为空，未作为错误回执。

本次错误日志功能的技术验证和模拟器专项通过；日志语义按当前错误返回对象执行。实际5173冲突来自模拟器与本机Web共用主机监听地址，端口及登录回调保持现有配置。完整业务、物理设备采用和其他原配置/目录请求问题继续沿各自验收范围执行。

## iPhone构建24与安装状态

用户授权模拟器验证后打包至原iPhone。当前源码的独立Next及普通RN入口Release24构建完成；550份Next输入、329份Python、4份Node、签名及IPA完整性检查通过。制品与实际命令见[设备安装记录](../deploy/ios-iphone-install-release.md#2026-11-01-启动控制页构建24待设备重连)。

首次设备检查可连接、已解锁、当前版本23；安装命令退出1，CoreDevice连接失效、NWError60。后续设备发现及lockState重试返回设备不可用，Xcode同一设备available=false。安装完成、设备24读回、数据metadata比较与普通启动均待设备重连；原模拟器验证与包体技术资格保持。源env、锁文件、原数据和正常服务无维护操作，账号/模型调用为0。

本轮6份文档检查命令`python3 /tmp/ink-startup-iphone-20261101-b24/validation/install-doccheck.py`退出1，新增链接及语义问题0；13项原有历史IPA缺失/旧行号锚点引用单列保留。6路径`git diff --check`退出0；构建与安装回执的23/24边界、版本、摘要和失败状态一致，结果归本轮validation的`install-doccheck-final.json`。最终设备发现仍返回unavailable，安装未完成。

## 2026-11-02 iPhone构建24覆盖安装与普通启动

用户要求继续安装，同一iPhone16恢复连接。复用原构建24和开发签名，deep/strict核对退出0；`devicectl device install app`退出0、20.827秒，版本读回0.1.0/24。安装前后Library/Application Support均2161项，路径增删、普通文件及符号链接metadata变化均0；未读取正文或凭证。

普通`devicectl device process launch`退出0，PID10604；后续进程查询退出0，同一PID和新安装路径保持。设备实际采用完成，源env/原配置和签名保持；重建、依赖安装、卸载、清理、账号维护与模型调用为0。物理页面、登录和完整业务验收单列。[完整命令和回执](../deploy/ios-iphone-install-release.md#2026-11-02-构建24覆盖安装与普通启动)归本次resume目录，11月1日首次安装失败保持历史原文。
