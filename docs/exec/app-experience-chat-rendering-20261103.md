<!-- [Input] APP-06用户反馈、当前ios-store工作区、消息源码及隔离技术回执。 -->
<!-- [Output] 影响范围、方案评审、修复任务、原失败与修订后验证证据。 -->
<!-- [Pos] APP-06独立执行记录；共享总清单与Notion任务登记由总控维护。 -->
<!-- [Sync] 2026-11-03: 追加用户静止对话持续跳动反馈，新增固定历史消息与连续几何回归；原因与修复资格按实际测量登记。 -->
# APP-06 对话文本渲染修复记录

日期：2026-11-03，Asia/Shanghai。分支：`ios-store`。工作区保留用户及其他任务的全部现有未提交改动。

## 需求范围与交付物

原文与原问题保留于[Notion来源](https://app.notion.com/p/40b30b7547c380f7ac22f85fdd2dbdd0#40d30b7547c3804a8bbadaedf8408366)，本轮通过连接器读取。反馈为长输入折叠、Markdown代码长空白、最新消息难以到达及v3.1布局应用。

交付物为[消息阅读PRD](../prd/chat/message-reading.md)、[正式交互稿与评审](../design/multi-platform/chat-message-reading.md)、Native消息展示修复、原组件技术规格及Simulator完整旅程回执。用户手机当前0.1.0/build28仅由用户测试，本轮物理设备操作数量为零。APP-04持续暂停；APP-05图标和Swift由原任务负责。

## 实施前影响评估

| 对象 | 当前来源与所有者 | 本轮影响与预期 |
| --- | --- | --- |
| 用户正文 | `ChatMessageList.native.tsx`的MessageText，原UIMessage | 增加实测预览及展开/收起，原文本与标识保持 |
| 代码、表格和普通Markdown | `ChatMarkdown.native.tsx`，原react-markdown/remark-gfm | 按复现证据修订局部容器测量，原Markdown语义保持 |
| 阅读位置 | `ChatMessageList.native.tsx`，原chatScrollPosition | 布局变化继续使用原底部跟随和跳转，用户手势保留历史位置 |
| 页面/输入/键盘 | `ChatPage.native.tsx`、`AIInputDock.native.tsx`、原Swift宿主 | 复用原区域、主题和动作，仅作相邻验证 |
| 消息提交、Stream、Stop与历史 | `useNativeChatThread`、原HTTP/SSE DTO | 生产代码保持，fixture调用原Hook和解析入口 |
| Project、Episode、canonical Artifact、Run私有`.dream`及after-turn Hook | 原Dream工作区及服务端 | 退出本轮范围，技术环境不创建或修改任何此类实体 |
| PostgreSQL/API投影、账户、Admin、Gateway、模型 | 原生产所有者 | 保持；技术环境使用具名内存HTTP/Stream边界，真实业务写入与模型调用数量为零 |
| 复制、导出、工具及附件 | 原copy、export、renderOtherPart入口 | 完整文本继续传递，混合内容按原区域展示 |

复现候选分别取自用户原文、当前源码和既有技术规格；缺少用户问题原始消息样本，使用明确命名的长普通文本、长Markdown、短代码、空代码和长代码行样本。浏览器为390×844并缩至320×480，原生目标为本轮独立iPhone16/iOS18.6 Simulator。分别记录内容尺寸、可见区域、滚动位置和操作预期。

## 发现、判断与方案收敛

| 类型 | 证据或决策 | 状态 |
| --- | --- | --- |
| 源码事实 | MessageText直接渲染完整用户Markdown，缺少折叠控件 | 已核对 |
| 源码候选 | RN横向ScrollView默认flexGrow/flexShrink参与尺寸分配；列表几何变化可更新底部意图 | 待原生复现判定 |
| 基线技术验证 | 两项定向浏览器规格为1通过/1失败；缺少Expand message导致长用户消息用例失败 | 已执行，退出1 |
| 基线相邻结果 | Chrome代码内在高度、长行与视口变化后的最新位置用例通过 | 浏览器资格，原生待验证 |
| 原生基线复现 | 同一单行用户代码的容器高981.3pt、代码文字高952.0pt；回复代码83.7pt，最新正文y=1164.7而列表下界551.7 | 实际页面断言失败，退出65；截图与几何保留 |
| 产品边界 | v3.1第6/8/11页保留原消息纵滚、输入、Stop和安全区 | 已核对PDF及可编辑源 |
| 方案比较 | 固定字符截断会改变Markdown和复制；整页WebView扩大范围；选用原Markdown完整测量与展示裁剪 | 最小方案评审通过 |
| 滚动方案 | 沿原列表维护用户阅读意图，在布局后执行原scrollToEnd，复用原跳转入口 | 实现和验证待登记 |

当前代码事实、拟议修复与实际验证分别记录。网络、Admin和模型未被用作渲染根因。

## 验证计划与执行边界

| 旅程 | 输入与动作 | 预期 |
| --- | --- | --- |
| 长用户输入 | 原Chat入口→长普通文本/Markdown→原Send→展开/收起→复制 | 预览随可见区域，复制与已提交文本完整一致 |
| 回复与停止 | 原Hook接收原SSE→增量更新→原Stop或完成→保存 | 正文与原任务状态一致，Stop可达、零重复提交 |
| 阅读位置 | 最新→上滑历史→增量/高度变化→原滚动到底部 | 历史位置保留，原跳转可到末尾 |
| 原生布局 | 代码长行/空块/嵌套列表→横滑及纵滑→软件键盘→收键盘→深浅色 | 紧凑代码高度、独立纵滚、输入和安全区可达 |
| 保存与返回 | 完成→原Back→原历史→重开同Thread→返回 | 保存文本和消息标识保持，展示状态按Thread隔离 |
| 相邻回归 | 短消息、表格、引用、混合附件/工具、历史过程及Thread切换 | 原渲染、复制、历史和权限入口保持 |

有界类型、浏览器、文档及构建验证通过luna-test-stage专用runner执行。原生App外壳复用已验证Simulator制品，只编译具名fixture和本轮消息源码；不安装依赖、不重建Next和App，不触及物理iPhone、原booted Plus或用户服务。构建成功、安装启动和实际UI断言分别登记。

基线日志：`frontend/output/playwright/app06-20261103/baseline/`。原失败截图位于该目录`test-results/e2e-native-messages-long-u-552a6-thout-changing-message-text/test-failed-1.png`。

## 当前回执

| 命令 | 退出码 | 关键输出 |
| --- | --- | --- |
| `corepack pnpm native:typecheck`，frontend目录 | 0 | 原生完整类型检查通过 |
| 已安装Chrome `--headless=new --dump-dom about:blank` | 0 | 浏览器轻量启动成功；临时profile已清理 |
| `corepack pnpm exec playwright test --config=e2e/web-rnw-regression.config.ts e2e/native-messages.spec.ts --grep 'long user text has\|code blocks use' --workers=1 --reporter=line --output=output/playwright/app06-20261103/baseline/test-results` | 1 | 2项：1通过、1失败；原失败保留 |

## 剩余资格

本轮源码、设计、26项浏览器规格及独立Simulator两项旅程已完成。物理iPhone、Android、真实模型、正常账户业务数据库、普通App重新打包安装及正式发布退出本轮执行范围；fixture保存属于内存技术证据。原失败与后续通过的分轮记录均保留。

## Native基线与最小源码修订

独立目标：`Kastention-APP06-20261103`，iPhone16/iOS18.6，`B94A11B3-DFEE-47D0-BEE7-3F6C29C58E40`。独立bundle为`com.inkmemory.app06qualification`；原booted Plus及物理iPhone均未操作。原编译App外壳来自`frontend/ios/build/app-experience-acceptance-20261103/previous-app.app`，通过APFS副本保留，原制品保持。

构建入口为原Metro CLI，`--max-workers 1`，本轮`NODE_OPTIONS=--max-old-space-size=1024`，再用已安装Hermes编译。该堆值用于本次轻量fixture预算，退出通用默认配置。主机16GiB，构建前约6.2GiB磁盘可用；新Simulator启动后约1.9GiB，后续仅允许本轮增量bundle和原runner增量编译。macOS无Linux cgroup；全Next、App重构建及依赖安装数量为零。

| 阶段与命令 | 退出码 | 结果 |
| --- | --- | --- |
| `NODE_OPTIONS=--max-old-space-size=1024 corepack pnpm exec react-native bundle --platform ios --dev false --entry-file e2e/native/chat-rendering-fixture.tsx --bundle-output ios/build/app06-chat-20261103/baseline.jsbundle --assets-dest ios/build/app06-chat-20261103/APP06.app --max-workers 1` | 0 | baseline JS 3,078,137 bytes，原源码快照保留 |
| 已安装`hermesc`编译baseline，副本签名及`codesign --verify --deep --strict` | 0 | baseline HBC 4,659,430 bytes，安装文件摘要匹配 |
| `xcodebuild build-for-testing -jobs 1`，独立UI runner | 0 | 测试runner构建完成 |
| 首次`test-without-building` | 65 | 测试环境缺少目标变量，未启动目标页面；harness失败保留 |
| 变量写入xctestrun后的`test-without-building`，仅`testCodeHeightAndLatestPosition` | 65 | 实际1项/1失败，最新回复不可触达；代码空白及几何已复现 |

基线原始命令与日志归`frontend/ios/build/app06-chat-20261103/baseline/`和`baseline-ui/`。`baseline-ui/APP06-baseline-r2.xcresult`保存实际页面失败；`attachments-r2-all/0543DF7E-EBB6-45E5-B278-9443A22B9CB9.png`显示大块代码背景占满消息区。

修订范围为三处：

1. `ChatMarkdown.native.tsx`为代码和表格横滚显式设置`flexGrow:0/flexShrink:0`，内容顶部对齐，阻止正文参与纵向剩余高度分配。
2. `ChatMessageList.native.tsx`测量列表可见高度与完整用户正文，在原气泡内裁剪预览；展开进入历史阅读意图，保留全文复制和Thread/消息/part键。
3. 原列表合并下一布局帧的`scrollToEnd`，手势开始和Thread切换清理旧帧；拖动期间尺寸变化继续由用户手势所有。双语展开/收起文案加入原i18n域。

Chrome修订批次保留：r1为6通过/1失败，缺少显式`aria-expanded`后已补齐；r2为7通过/1失败，RNW图片DOM load事件与原生Image事件形状不同，测试平台边界已映射宽高；r3为7通过/1失败，主Agent源码修改触发Vite热重载并将样本重置成初始24条消息。r3退出本轮有效完成证据，后续固定源码快照重跑。三次原始日志与截图保留，规格断言未放宽。

## 修订后阶段回执

| 批次 | 命令或入口 | 退出码与数量 | 覆盖及限制 |
| --- | --- | --- | --- |
| `message-r4` | 原配置执行`e2e/native-messages.spec.ts` | 0，8/8 | 长预览、完整复制、Thread隔离、GFM、代码高度与长行、异步图片高度、历史位置及原跳转 |
| `adjacent-r1/tool-image.log` | 同配置执行`e2e/native-tool-results.spec.ts e2e/chat-image-share.spec.ts` | 0，12/12 | 原工具/附件/持久App、文档回执、图片预览与导出，保留原权限及完整内容 |
| `adjacent-r1/session.log` | 原会话规格grep限定6项 | 0，6/6 | 原提交DTO、结束保存、附件、长Markdown、Stop及手动权限；APP-04后台/前台用例执行0 |
| 两端类型 | `corepack pnpm native:typecheck`；`corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 均0 | r4/adjacent源码时点全量类型检查 |
| 首次文档收尾 | `node output/playwright/app06-20261103/docs/validate-docs.mjs`；`git diff --check` | 均0 | 3文档、9相对链接、9清单、3张Mermaid实际解析及渲染，错误0 |
| `fixed-r1-ui-r2` | 原两方法XCUITest | 65，1通过/1失败 | 代码实际80pt，原981.3pt；最新可达。长旅程停在fixture对WKWebView使用RN Keyboard.dismiss |
| `fixed-r2-ui-r1` | 原两方法XCUITest | 65，1通过/1失败 | 代码80/83.7/44.3/83.7pt与横向触摸通过；软件键盘、原blur、发送、收起和展开通过。默认快速swipe跨过Collapse，保存重开尚未执行 |
| `final-r1` | 原消息8项、Native类型、文档与diff | 消息0，8/8；类型2；文档/diff均0 | 新增320×200短屏短消息断言通过；Native类型发现并行任务新增`RuntimePerformanceCharts.native.tsx:32`向InkLabel传string[]，原APP-05所有者负责修复 |

短屏规则补充：仅在完整正文高于预览与原44pt展开控件的合计高度时收起，避免为单行短正文新增占用。PRD和交互稿已同步；后续固定候选采用该判定。

`fixed-r1`首次runner增量编译因当前XCTest缺少`lastMatch`退出65，尚未执行UI；测试改用原查询的`element(boundBy:)`，未修改产品。后续`fixed-r1-ui-r2`的收键盘动作改由原`AIInputDock.active`传给`MarkdownInputEditor`触发原文档blur，并等待实际键盘消失。

`fixed-r2`原录像`fixed-r2-ui-r1-attachments/D7ED176E-8D25-41DB-A1A4-5E908CF35A0D.mp4`的20秒帧显示Paragraph16–19，43秒帧显示最新Reply complete，支持默认快速手势跨过收起入口的判断。长样本保持35段；定位改为按目标frame方向执行有界小步慢拖，并记录每步几何，末尾可触达断言保持。未观察到文本选择占用的证据。

## 最终验收结果

最终产品源码仅修改`ChatMarkdown.native.tsx`、`ChatMessageList.native.tsx`及原i18n消息文案。页面、输入组件、业务Hook、HTTP/SSE、权限、存储、后台恢复、Swift及图标的生产代码均未由本任务修改。

| 最终批次 | 实际结果 | 证据 |
| --- | --- | --- |
| `final-r1`消息回归 | 8/8，退出0，41.5秒；包含最终短视口短消息保护 | `frontend/output/playwright/app06-20261103/final-r1/` |
| `adjacent-r1`相邻回归 | 12项工具/图片分享及6项原会话，合计18/18，均退出0 | 同根`adjacent-r1/` |
| `final-type`完整Native类型 | 退出0，原APP-05所有者修复其并行图表文件后的最终回执 | 同根`final-type/native-typecheck.log`；原失败保留 |
| 完整Web类型 | 退出0 | 同根`adjacent-r1/web-typecheck.log` |
| `fixed-r4-ui-r1`实际XCUITest | 2/2，退出0，72.0秒 | `frontend/ios/build/app06-chat-20261103/fixed-r4-ui-r1.xcresult`及同名test日志 |

原生同场景代码高度为80.0/83.7/44.3/83.7pt；首段从981.3pt降至80.0pt。最新回复可触达，代码横向触摸改变长行横向位置并保持外层纵向位置。

长旅程保持35段、完整提交文本和原消息标识。展开后首段位置为y=229.3pt、收起入口为y=3345.0pt，全文范围约3115.7pt；小步拖动每步推进约253pt，收起入口实际触达并执行。收起后历史重开保持稳定；浏览器同时验证再次展开。全文自然尺寸未被预览maxHeight截断，未观察到布局循环。

同一旅程实际通过：软件键盘输入与原blur→原Send→收起/展开→回复增量→历史阅读位置保持→原最新跳转→空输入聚焦时软件键盘下原Stop可达→原Stop一次→内存保存两条完整消息→深浅色→原Back→原历史重开同Thread→初始收起→返回。fixture记录原业务POST=1、Stop POST=1，无重复提交。运行中有草稿时的Send/清空后Stop仍由原`useComposerDraft`负责；测试后段改为聚焦空输入，生产交互保持。

`fixed-r3`已证明完整展开与有界慢拖，后段因测试输入草稿后仍期望Stop而失败，退出65。原任务按`useComposerDraft.showStopAction`修正测试预期，保留失败回执。最终fixture只补调用计数，当前修复未加入新的业务状态或接口。

上述结果属于provider-free技术资格与独立Hermes/WKWebView Simulator旅程。保存证据来自测试所有的内存transport；正常账户、PostgreSQL、Gateway及真实模型调用数量为零。物理iPhone、Android、普通App重新打包安装和正式发布仍有独立资格；用户手机build28保持原安装状态。

### 制品匹配、截图与资源收尾

最终bundle、App副本及实际安装应用的`main.jsbundle` SHA-256均为`d9ae764ea8d29204bf7fe91a7aaff0f941f3f88b2d651c5deb4e6cc1b75a7aed`。三个生产源、fixture及Swift规格的构建前/后摘要一致，完整命令与摘要归`fixed-r4-source-sha-prebundle.log`、`fixed-r4-final-sha.log`及`fixed-r4-ui-r1-receipt-summary.log`。本轮仅编译fixture Metro/Hermes与UI runner，普通App、Next、原依赖锁和发布制品保持。

主Agent已查看原生基线大块代码空白及最终四类截图，确认代码区域紧凑、预览与展开入口可见、软件键盘上方Stop可达、深色安全区和输入边界正确。最终8张截图位于`fixed-r4-ui-r1-attachments/`：

- [代码同场景修复后](../../frontend/ios/build/app06-chat-20261103/fixed-r4-ui-r1-attachments/97FCB763-B5F5-44FE-BD98-F5C9E80B6458.png)
- [长消息收起态](../../frontend/ios/build/app06-chat-20261103/fixed-r4-ui-r1-attachments/D75689A8-A7FA-475F-8B46-4EBEEF1B7E49.png)
- [流式期间软件键盘与Stop](../../frontend/ios/build/app06-chat-20261103/fixed-r4-ui-r1-attachments/15E1C493-73EC-499B-B7AD-0F2A3E1447F8.png)
- [深色完成态](../../frontend/ios/build/app06-chat-20261103/fixed-r4-ui-r1-attachments/596EA09A-7A57-456D-81BF-9B179C332529.png)
- [同Thread历史重开](../../frontend/ios/build/app06-chat-20261103/fixed-r4-ui-r1-attachments/F90A679F-CBB4-496D-B973-42B307FC5C38.png)

测试结束后终止本轮APP06并关闭独立Simulator。清理前核对设备名称/UDID及第三方bundle，内容仅包含`com.inkmemory.app06qualification`与本轮XCTest runner；导出截图和SHA后删除本轮设备，`simctl delete`退出0。文档服务PID41800、loopback55247经进程命令和监听核对后发送SIGTERM，停止命令退出0、执行会话按终止信号返回143，后续监听检查为空。原Plus、物理设备、真实账户及其他服务操作数量为零。`cleanup-precheck.json`与`cleanup-receipt.json`保存边界；清理后磁盘可用约3.9GiB，所有本轮失败/通过回执和候选App保留。

### Notion同步

已将APP-06实际通过范围追加到[已修复问题](https://app.notion.com/p/40b30b7547c380ad8b12eaf5a864a9a5)，使用`insert_content`与`position:end`保留既有Admin及其他App记录。初次请求缺少`content`参数返回400，远端未写入；更正参数后返回目标page_id，成功且无warnings。原问题页、原截图及源页任务登记由总控所有，本任务未修改源页任务行。

最终文档收尾：`node output/playwright/app06-20261103/docs/validate-docs.mjs`退出0，3份文档、14个相对链接、9项清单及3张Mermaid均通过；`git diff --check`退出0。日志归`frontend/output/playwright/app06-20261103/docs-final/`。本轮浏览器验证按仓库`ink-dream-playwright-qa`执行，机械阶段由`luna-test-stage`专用runner留存回执。

## 持续跳动补充反馈与复现范围

用户提供同一iPhone16 Plus/iOS18.6对话的两张截图：输入卡保持原位置，长用户气泡及14秒历史过程在两个纵向位置间变化，最终回复在其中一张进入可见区域。截图中的测试指令属于显示内容，本轮UI回归无工具执行或模型请求。

当前源码同时使用`maintainVisibleContentPosition`与JavaScript布局帧内的`scrollToEnd`；长消息预览读取正文自然高度。持续偏移的具体触发源待同场景测量。原通过记录保留，本次增加静止期间连续采样以覆盖持续移动。

| 业务对象或界面 | 当前来源与所有者 | 本轮影响 |
| --- | --- | --- |
| 消息纵向位置、长正文预览 | `ChatMessageList.native.tsx` | 检查无输入变化时的稳定性，按复现决定最小修复 |
| 完整正文、消息与Thread标识、复制 | 原消息DTO及既有组件 | 保持 |
| 提交、流式、Stop、历史读取 | `useNativeChatThread.native.ts`及原公开接口 | 保持，定向相邻回归 |
| Project、Episode、Artifact、Run私有产物与Hook | 现行Agent与持久化链路 | 退出本轮UI技术验证，无写入 |
| Admin、权限、Notion连接、APP-04生命周期 | 原服务和对应任务 | 退出修改范围 |

沿原`chat-rendering-fixture.tsx`增加固定三条历史消息：前一回复、中文长用户正文、含14秒过程的短最终回复。原`ChatRenderingUITests`新增`testIdleHistoryRemainsStill`，通过24次定时几何采样检查同一最终回复的纵向跨度不超过2pt，并核对最终可达与展开入口。该2pt为UI测量误差容限，业务无新增限制。fixture仅持有内存消息；身份认证、数据库与模型调用均为0。

新增证据归`frontend/ios/build/app06-flicker-20261103/`，两张原反馈图以私有副本保留。原Plus与物理手机供用户使用；机械复现采用独立Simulator及已有App/runner增量制品，不重新安装依赖或构建完整Next/App。原Plus最近8分钟系统日志定向读取退出0，未取得所筛选警告；该结果仅覆盖系统日志中已记录的消息。基线、最小修复及修订后资格分别待回执。

### 静止样本结果与用户中断

短历史样本的`baseline-idle-history-r3`实际执行`testIdleHistoryRemainsStill`1项、0失败，退出0；24次最终回复位置均为519.333pt，跨度0pt。该结果限定固定短历史，原用户截图中的持续跳动仍待复现。首次runner PCH路径、缺少目标环境变量及缺少fixture origin分别保留为harness失败，产品断言尚未执行。

随后将前文扩展为18段，以覆盖实际可滚动历史；增量Metro、Hermes及runner构建均退出0。首次UI阶段因私有xctestrun缺少runner App以70退出；修正私有配置后的第二次运行进入Stable与消息元素读取。用户随后中断并要求优先打包，长历史阶段未完成几何输出或断言，未取得有效测试退出码。该阶段保持未完成，生产滚动逻辑修改为0。

本轮新建的`Kastention-APP06-Flicker-20261103`、UDID `520621DD-EB1A-4D1E-A7BF-090A01EF2A8D`已关闭并核对身份后删除，`simctl delete`退出0。两份本轮可重建fixture App副本在保存Bundle ID、可执行文件及Hermes摘要后清理；日志、xcresult、截图、fixture源码和bundle输入保留，清理回执为`rebuildable-app-cleanup.json`。删除范围仅涉及本轮测试资源，原Plus与真机数据保持。

主任务对原Plus仅读取系统日志和截图、普通激活App；当前Notion详情和授权状态保留。CUA检查因并行XCTest改变Simulator前台窗口而拒绝旧控件索引，未完成原对话警告读取，未派发消息、修改权限或确认授权。本轮没有确认闪烁根因或完成源码修复；用户最新请求转入Release30 iPhone打包。
