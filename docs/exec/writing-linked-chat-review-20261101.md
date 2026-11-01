<!-- [Input] 用户确认的写作记录入口、Web与Native直接调用链、设备构建22、既有请求回执和只读工作边界。 -->
<!-- [Output] 差异诊断、网络证据范围、交互设计评审、条件化实施清单及验证回执。 -->
<!-- [Pos] 写作记录关联对话专项执行记录；产品规则归mobile-app，业务时序归现行writing-mobile-layout。 -->
<!-- [Sync] 2026-11-01: 本轮仅文档，源码、测试、依赖、配置与安装包保持；设计、技术验证与设备业务验收分列。 -->

# 写作记录关联对话：只读诊断与设计评审

## 范围与处理结论

本轮直接采用用户给定的Optimized Prompt规划一次。用户随后明确“笔记”指“更多 → 写作”或时间线中的写作记录。读取根合同、直接目录合同、现行移动PRD、写作设计和相关源码；保留现有未提交改动。本轮交付[产品规则与骨架](../prd/dream-workspace/mobile-app.md#写作记录与关联对话)及[现行跨平台交互设计补充](../design/multi-platform/writing-mobile-layout.md#写作记录与关联对话)。

- **故障根因待验证**：未取得用户本次A/B操作的实际请求和响应，当前证据不足以将失败归因于网络、认证、记录关联或Modal。
- **已有打开路径**：写作记录内的`ChatWidgetUI → handleOpenWritingChatThread → WritingDocument → WritingView → MoreNavigator → Business → openThread`已经接通。Web与Native均使用卡片的threadId；选中记录本身不自动切换Chat。
- **优先入口缺口**：`ChatWidgetUI`中Chat按钮初始`opacity=0`、`pointerEvents=none`，仅onMouseEnter显示；现有Web用例先hover再点击。原组件390宽度触屏模拟中，两次点击按钮位置均未打开对话，实际触发标题折叠/展开；桌面hover后点击成功。22的本地Next产物含相同显示条件。真机首次触摸与实际请求继续采证，局部建议仅复用原按钮及现有mobileWriting值。
- **确认的独立差异**：Web写作Chat发送当前`editor_state`并等待原保存屏障；Native侧会话只收到threadId，当前发送上下文未提供这两项。该差异影响写作上下文，打开已有历史的阶段独立验证。
- **当前手机**：2026-11-01读回`com.inkmemory.mobile`、0.1.0/22、设备available/paired。原构建回执中的两个RN入口摘要匹配当前源码；包内Next全链条的逐文件来源尚未确认。
- **最小处理**：已有对话加载失败优先原重新读取；触屏入口问题优先实施项I2a，仅涉及原ChatWidgetUI显示条件和App传入现有mobileWriting。先完成当前设备的同一卡片复验与资源核对，再进入后续实施。当前无零代码恢复成功回执。
- **评审结论**：待满足明确前提后通过。文档方案和23项既有技术合同已经分别检查；实现、设备A/B与真实模型验收保持未完成。

## 判断依据与方案删减

发现范围限定为用户入口、原移动设计、直接调用链及已有失败回执。定义的问题为“指定写作记录的已有卡片能否打开其原Thread，以及切换后的身份、反馈和恢复是否一致”。

| 方案 | 判断与采用条件 |
| --- | --- |
| 现有重试与重新进入 | 优先采用。源码已有日历重选、Chat重试、前台恢复和文档Retry；恢复结果需原操作回执 |
| 更新安装资源 | 原设备版本与来源核对后按资源缺口决定；22已含匹配当前RN入口的回执，禁止直接将现象归为旧包 |
| 局部调用或参数修正 | 仅在对应故障位置有证据时实施；发送上下文缺口单列后续依赖 |
| 移动卡片直接显示已有Chat入口 | 优先局部建议。显示条件位于原ChatWidgetUI，App已有mobileWriting；保留原卡片关联、折叠与桌面hover，组件新增数为零 |
| 每份记录自动新建唯一Thread、自动打开Chat | 删除。现行Voice复用、卡片多关联与手动建议各有规则 |
| 新增对话页面、HTTP接口、草稿库或同步系统 | 删除。当前问题可沿原组件、文档协议、保存屏障和请求构造处理 |

交付仅追加现行PRD和写作设计，保留历史原文、其他章节及原验收状态。

## 入口与所有者

| 职责 | 当前所有者与入口 |
| --- | --- |
| 选择写作记录 | `CalendarPopup.handleOpenEntry`读取完整Session；`App.handleLoadEntry`加载；`useSessionLifecycle.loadPersistedEditorSession`更新编辑状态 |
| 时间线阅读 | `CollectionsView`及`CollectionsView.native`打开原图片/评论或回顾报告，普通日期卡无写作Chat导航 |
| 已有关联解析 | `ChatWidgetUI`读取`data.threadId`；`ensureVoiceThread`负责Voice关联复用和懒创建 |
| 建议关联 | `WritingSuggestionController.ensureThread`读取或创建`writingThreadId`，与Chat卡片引用分别所有 |
| Web导航 | `App.handleOpenWritingChatThread`设置requestedThreadId/nonce；原`ChatView`读取与展示 |
| Native导航 | 固定URL的`WritingDocument`消息经`WritingView.receive`校验，`MoreNavigator.onOpenThread`透传，`Business.sideChat/Modal`展示 |
| HTTP与恢复 | Web原fetch；Native原clientFetch/openResponse；共享hydrate读取messages/status；Native hook持有epoch和reader |

## 差异诊断表

下表“当前行为”来自源码；设备实际行为单独记录。“待验证”保留业务与来源的不确定性。

| 问题 | Web当前行为 | 端侧当前行为 | 证据路径与行号 | 原因或待验证假设 | 最小处理方式 | 影响范围 |
| --- | --- | --- | --- | --- | --- | --- |
| 记录A/B选择 | 原日历getSession后替换EditorState；关闭日历 | 局部WritingDocument复用同一App与生命周期 | [CalendarPopup:886](../../frontend/app/_dream/components/CalendarPopup.tsx#L886)、[App:874](../../frontend/app/_dream/App.tsx#L874)、[生命周期:179](../../frontend/app/_dream/hooks/useSessionLifecycle.ts#L179) | 真机getSession目标与响应未取得；包内DOM源码版本未完整映射 | 记录A/B实际GET和目标id，用原重选恢复 | 写作编辑与已保存状态 |
| Chat入口显示与触摸 | 鼠标进入卡片后按钮显示；现有Web测试先hover | 局部DOM沿相同鼠标条件，初态透明并关闭指针，未提供touch/focus显示接线 | [初态:76](../../frontend/app/_dream/components/ChatWidgetUI.tsx#L76)、[事件:128](../../frontend/app/_dream/components/ChatWidgetUI.tsx#L128)、[按钮:237](../../frontend/app/_dream/components/ChatWidgetUI.tsx#L237)、[Web用例:357](../../frontend/e2e/story-workspace-default-entry.spec.ts#L357) | 触屏入口可发现性缺口已证；真机合成鼠标事件与首次点击结果待验证 | 将已有mobileWriting透传原卡片，移动常显原Chat按钮；桌面保持hover，建议、未实现 | 仅写作卡片入口，Web窄屏与Native |
| 时间线入口 | 普通日期卡显示摘要；图片/报告有点击动作 | 同一规则，日期卡无对话回调 | [Web:105](../../frontend/app/_dream/components/CollectionsView.tsx#L105)、[Web:135](../../frontend/app/_dream/components/CollectionsView.tsx#L135)、[Native:53](../../frontend/app/_dream/components/CollectionsView.native.tsx#L53)、[More:44](../../frontend/app/_dream/components/story-workspace/layout/MoreNavigator.native.tsx#L44) | 时间线记录与写作日历入口可能混用，具体失败入口待确认 | 使用写作页原日历；时间线新增动作单列需求 | 入口解释，无新增功能 |
| 已有卡片进入Chat | data.threadId存在时显示Chat入口；设置准确Thread及nonce | open-thread消息携带同一id；校验来源后打开侧Business | [卡片:221](../../frontend/app/_dream/components/ChatWidgetUI.tsx#L221)、[App:1207](../../frontend/app/_dream/App.tsx#L1207)、[文档:26](../../frontend/app/_dream/components/Editor/WritingDocument.tsx#L26)、[宿主:28](../../frontend/app/_dream/components/WritingView.native.tsx#L28)、[RN:193](../../frontend/src/App.tsx#L193)、[RN:210](../../frontend/src/App.tsx#L210) | 已有实现；尚无本次点击、消息与history/status回执 | 先复验当前22；仅修正被证实的消息或呈现条件 | 原侧会话与Writing |
| 笔记与Thread关系 | 卡片threadId与Voice.thread_id可复用；建议有独立writingThreadId | DOM复用同一关联规则 | [卡片消费:2153](../../frontend/app/_dream/App.tsx#L2153)、[Voice:685](../../frontend/app/_dream/api/voiceApi.ts#L685)、[建议:184](../../frontend/app/_dream/hooks/useWritingSuggestions.ts#L184) | 多记录共享Voice Thread属于现有规则；不能只凭Thread相同判断错绑 | 对照点击卡片保存的id；禁止自动另建Thread | 既有卡片、Voice与建议 |
| 对话读取与网络 | 共享history/status；失败显示原重试 | openThread设置id并recover；失败unknown，原自动/手动重试 | [读取:346](../../frontend/app/_dream/components/chat/threadSessionHydration.ts#L346)、[Native:95](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L95)、[Native:115](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L115)、[Native:268](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L268)、[RN:139](../../frontend/src/App.tsx#L139) | 既有17回执为503；22本次未取证 | 优先重试同一id，只读history/status；保持原服务地址 | 当前Thread及其观察者 |
| 发送当前写作上下文 | ChatView收到state与保存屏障，发送前等待；builder投影editor_state | Business传入Deck/Voice/设置；侧会话入参只有threadId，无editorState与保存屏障 | [Web接线:1804](../../frontend/app/_dream/App.tsx#L1804)、[发送屏障:522](../../frontend/app/_dream/components/chat/ChatPanel.tsx#L522)、[builder:18](../../frontend/app/_dream/lib/claude-chat-request.ts#L18)、[RN:104](../../frontend/src/App.tsx#L104)、[Native发送:145](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L145) | 源码差异已证；其对本次故障的作用待发送回执 | 条件化补齐原上下文与保存屏障，准确文件见实施项I3 | 写作侧会话发送，普通Chat保持 |
| 原稿与返回 | 面板关闭会卸载Chat；Thread切换以key重建；草稿为组件状态 | 主Business隐藏保留，侧Business关闭卸载 | [Web面板:64](../../frontend/app/_dream/components/story-workspace/layout/WritingWorkspaceSplitPane.tsx#L64)、[Web key:1344](../../frontend/app/_dream/components/chat/ChatView.tsx#L1344)、[草稿:28](../../frontend/app/_dream/components/chat/useComposerDraft.ts#L28)、[RN:142](../../frontend/src/App.tsx#L142)、[RN:211](../../frontend/src/App.tsx#L211) | 跨关闭恢复侧稿无现行合同；主Chat返回需设备复验 | 保持当前生命周期，区分主Chat稿、侧会话稿与已保存正文 | 草稿与返回 |
| 任务及迟到读取 | 共享hydration与既有Chat观察者 | active核对mounted/epoch/threadId；关闭释放reader；Stop独立 | [身份:52](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L52)、[恢复:99](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L99)、[卸载:255](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L255) | 读取隔离已有；A/B实际任务未验收 | 重用原恢复和Stop，禁止把关闭面板当任务取消 | 原运行任务与队列 |
| 创建或日历读取迟到 | handleAgentSelect与handleOpenEntry的await后无同次Session选择核对 | 共享DOM路径继承该控制流 | [创建:1338](../../frontend/app/_dream/App.tsx#L1338)、[记录读取:889](../../frontend/app/_dream/components/CalendarPopup.tsx#L889) | 共享风险，尚无乱序复现；手动建议的身份保护已独立实现 | 先确定性复现，再在原回调加Session/请求校验 | 两端共享回调，无新关联规则 |
| 会话失效 | 原认证与Cookie/CSRF；局部文档AuthProvider | 原401回调触发refreshSession/SessionGate；读取与stream均有处理 | [Native:43](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L43)、[stream:68](../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts#L68)、[文档认证:18](../../frontend/app/_dream/components/Editor/WritingDocument.tsx#L18)、[账户边界:215](../../frontend/src/App.tsx#L215) | 本次401或会话恢复请求未取得 | 复用正常登录恢复，禁止新增认证协议 | 原账户和资源权限 |

## 设备版本与网络证据

### 当前采用范围

1. `git branch --show-current`为`ios-native`；HEAD为`b47e59d96d6fcdb088e3c28c19615e6d5535b9d4`。当前工作区含大量已有未提交修改，HEAD不能代表全部打包输入。
2. `xcrun devicectl list devices`退出0，当前iPhone16 available/paired。`device info apps`过滤产品bundle退出0，读回0.1.0/22。
3. [构建22原执行记录](ios-notion-links-20261101.md#普通产品构建22与手机采用)记录同一手机覆盖安装和启动。测试代理只读核对本地22包体，`main.jsbundle`与`runner/product/main.jsbundle.hbc`均为5,682,434字节，SHA256均为`342da27993d4d5545342fac3f46b62b379bfc6eb13d2e4d1f9bec6dd081e9911`。
4. 原`runner/product/integrity.log`中`WritingView.native.tsx`和`frontend/src/App.tsx`摘要与当前源码相同。`MoreNavigator`、文档和生命周期没有对应逐文件输入回执；包内Next只保留编译产物。`sourceLockSha256`是构建锁摘要，单独使用它无法证明当前DOM文件已安装。
5. 上述核对未从设备读取完整安装包字节。当前采用判断由设备版本、既有安装回执及本地相应制品组成；已安装全链条的逐字节映射待补充。安装资源、本轮故障恢复及真实业务分别验收。

6. 补充检查本地22包内`next/frontend/ios/Next/build-source/.next/static/chunks/3331.b28daa4ea1935c45.js`，SHA256为`f3ce79bcb02c962da9c413f10d609865f9b57012352218ad820458b8694adeb5`。原模块具有`useState(false)`、onMouseEnter/Leave及`opacity:+!!g,pointerEvents:g?"auto":"none"`，证明该具体显示条件已进入22本地制品。其他DOM模块的源码精确映射缺口仍保留。后续13:22（Asia/Shanghai）设备再次读回22。

### 请求回执与限制

只抽取现有结果中的label、status、transportError、elapsedMs及字节计数；未输出凭证、笔记或聊天正文。以下为历史请求回执，未重跑原诊断脚本。

| 证据 | 请求与返回 | 能支持的判断 |
| --- | --- | --- |
| `frontend/ios/build/rebuild-iphone-20261031/112-device17-reads-receipt.json`与原`physical_workspace17_reads.py:11`目标映射 | GET `/auth/session`503/30304ms；GET `/api/system-config`503/30044ms；GET `/api/claude-agent/threads?limit=1`503/8932ms；三项transportError均0 | 当时本地入口有HTTP失败回执；503发生在HTTP服务处理链，外部连接、Admin与服务内部原因继续按原诊断区分 |
| 同目录`94-device16-reads-receipt.json` | session503/51852ms；configuration200/62606ms；history504/39500ms；transportError均0 | 既有慢读和超时响应证据，仅覆盖16阶段 |
| 同目录`106-device17-reads-receipt.json` | public-system200/7118ms/192字节/transportError0 | 当时一个公网GET成功；本次笔记或Thread读取状态仍需对应回执 |
| `frontend/ios/build/notion-auth-crash-20261101/launch22.log`及抽取结果 | 未抽到HTTP访问日志 | 仅支持本地文件缺少本次请求记录；无法据此判断请求未发出或网络正常 |
| 本次A/B记录GET、卡片Thread GET、stream和401 | 尚未取得 | 本次失败阶段、恢复有效性和根因保持待验证 |

当前根因判断优先需要一次已有请求记录：时间、平台/构建、入口动作、记录A/B的脱敏别名、卡片目标与实际Thread是否相等、方法、脱敏路径、状态码、耗时、取消及重试结果。仅在原Network或原生日志已有字段内采集；日志缺字段时登记缺口。禁止新增埋点、读取请求正文或凭证。打开既有Thread的链路中，模型请求应为零。

### 触屏技术复现

测试代理在任务临时目录打包原`ChatWidgetUI`，输入为无正文的合成卡片及只计数的onOpenChat回调。真实账户、HTTP、模型、数据库和业务服务调用均为零。初次使用Playwright Chromium，随后纠正为本机`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`，版本156.0.8078.74，两套回执分开保留且行为一致；未下载或安装浏览器。仓库测试文件保持。

| 条件 | 实际结果 |
| --- | --- |
| 390×844、hasTouch/isMobile、初次显示 | opacity为0，pointer-events为none；elementFromPoint命中DIV |
| 按按钮几何中心首次触摸 | onOpenChat计数0；底层标题触发collapse:true |
| 同一位置第二次触摸 | onOpenChat仍为0；底层标题变为collapse:false |
| 桌面鼠标进入卡片 | opacity变为1，pointer-events变为auto |
| 桌面普通点击 | onOpenChat计数1，目标为原fixture Thread |

该结果支持“触摸入口在发请求前受显示与命中条件阻挡”的技术判断；本次用户设备的实际失败阶段仍需WKWebView与原请求回执。[样本截图](/tmp/ink-note-chat-design-20261101/validation/chat-widget-touch-390.png)与[本机Chrome结构化回执](/tmp/ink-note-chat-design-20261101/validation/chat-widget-touch-chrome-receipt.json)供复核。样本不构成真实账户、真机或模型验收。

### 零代码处置路径

1. 在当前原账户与构建22确认前台可用；需要登录时走原登录，保留现有服务配置。
2. 从“更多 → 写作 → 日历 → 日记列表”选择已有记录A；取得原GET结果后查看其卡片是否已有Chat入口。普通时间线日期卡按原阅读规则使用。
3. 点击A中已有卡片的Chat入口；读取失败时使用当前侧会话的“重试读取”。恢复连接或返回前台后核对同一Thread的history/status，保持原记录与未发送主Chat稿。
4. 关闭侧会话；通过原日历选择B，执行相同动作；随后回A并打开原卡片。允许A/B按原Voice规则复用Thread。
5. 只有局部文档加载失败时使用原文档Retry。没有已有Thread的卡片所需创建请求属于业务写入，应按明确账户、记录与操作授权另行执行；本轮未发起。

执行状态：尚未在当前设备完成以上A/B操作，零代码解决与网络恢复成功均未验收。本轮没有指定两条既有记录标识及真实模型发送目标，未读取其正文，未创建Thread或提交模型请求。

## 设计评审

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| Web关联规则 | 卡片、Voice和建议各有已有引用 | 文档按实际引用说明 | 删除自动唯一Thread和切记录自动打开规则 | 原A/B卡片目标核对 |
| 触屏入口 | 原Chat按钮依赖鼠标hover；合成样本触摸两次均未导航，桌面hover后成功；22本地产物同条件 | 优先处理原按钮的触屏可达性；建议mobileWriting控制原按钮常显 | 仅两个原文件接线，不新增组件、状态或页面 | WKWebView真机结果与原请求回执；完整设备字节映射单列 |
| 入口归属 | 记录选择位于写作日历；时间线为原阅读 | 按实际模块绘制路径 | 页面骨架、正常图和诊断表一致 | 用户具体失败动作与包内DOM来源 |
| 选择、展示和参数 | 原记录选择与Thread导航独立；发送editor_state存在差异 | 将打开与发送拆为两项证据 | 已有导航优先复验；上下文修正标建议、未实现 | 实际GET/POST的脱敏元数据 |
| 网络恢复 | 已有重试、前台恢复与文档重载 | 复用原操作；分列历史503与当前缺口 | 删除新网络层、自动重发和换地址建议 | 当前22原请求与恢复回执 |
| 草稿 | 主Chat稿保留；侧稿和Web面板稿为组件状态 | 明确关闭/切Thread释放边界 | 删除跨关闭草稿恢复与持久草稿库 | 原主Chat稿和正文保存边界复验 |
| 任务与迟到 | reader关闭和任务Stop有独立所有权 | 原epoch及history/status复用 | 无新增状态机或自动停止 | 已有运行任务与迟到结果验收 |
| 身份与权限 | 401、SessionGate、Cookie/CSRF已接入 | 沿原恢复与归属校验 | 无新账户或认证重构 | 当前账户会话失效的可控前提 |
| 修改证据 | hover显示条件与发送上下文差异明确；导航断链未证；共享乱序为风险 | 实施清单按证据条件排序 | 优先原按钮可达性，关闭未经证实的大范围修复 | I1取证后选择I2/I2a/I3/I4 |
| 图与验收 | PRD有两端骨架；正式稿有正常、异常和状态图 | 状态用已有组件与函数命名 | 图示明确现有路径与待验证项 | 文档命令与设备验收分别记录 |

**评审结果：待满足明确前提后通过。** 前提为取得本次A/B失败阶段回执、补齐对应安装资源来源、据此收敛实际实施项。若仅原重试恢复，转为零代码处置并登记回执；若进入I3，上下文的同次保存与取消协议需完成局部技术评审。文档审核与既有合同通过不提升实现和设备业务资格。

## 后续实施清单

| 顺序与工作项 | 准确文件与函数 | 缺陷证据及预期行为 | 可复用模块与最小范围 | 依赖、回退与验收 |
| --- | --- | --- | --- | --- |
| I1 原操作取证 | 原`CalendarPopup.handleOpenEntry`、`ChatWidgetUI`、`WritingView.receive`及`Business`可见入口；原Network/原生日志 | 当前缺少A/B与失败回执。预期准确记录getSession目标、open-thread及history/status结果 | 仅原入口、已有日志和重新读取，源码修改零 | 已有真实账户、两条记录及既有卡片；不发送模型。原返回动作结束观察；覆盖V1—V4/V7 |
| I2 安装采用核对与条件化更新 | `frontend/ios/scripts/prepare-next.py`、`bundle-next.py`原准备/校验入口；原Metro bundle与现有设备安装流程 | 22的RN两入口来源已核对，DOM逐文件来源缺回执。预期设备包含选定候选的两类资源 | 原构建/签名/安装流程，不修改脚本、锁、配置或业务接口 | 先证实缺少现有接线，再获实施/安装授权；保留22制品与原容器。按原覆盖升级/回退流程，不删除账户与数据；重验V1—V8 |
| I2a 移动卡片按钮可达性，建议、未实现 | `frontend/app/_dream/components/ChatWidgetUI.tsx`的Props与原Chat按钮显示条件；`frontend/app/_dream/App.tsx`的ChatWidgetUI实例 | 源码237/238为hover限定，22本地产物同条件；触屏技术样本两次未导航，桌面hover后成功。预期有threadId的展开移动卡片无需悬停，原按钮可见且单次触摸打开；折叠/缺关联与桌面行为保持 | 从App透传现有mobileWriting，复用原onOpenChat/按钮/条件；无需新增Hook、全局状态、路由或组件。仅修改原Chat按钮的触屏显示条件，删除行为保持 | 技术复现已取得，先对应设备现象；后续单独授权实施。回退两处接线即可；V2补充初态可见、首触成功、无hover、无force点击，桌面hover回归及缺关联/折叠验证 |
| I3 写作发送上下文对齐，建议、未实现 | `frontend/app/_dream/App.tsx`的`WritingDocumentHost`及原保存屏障接线；`components/Editor/WritingDocument.protocol.ts`原state/event schema、`WritingDocument.tsx`的Canvas；`WritingView.native.tsx`的sync/receive；`story-workspace/layout/MoreNavigator.native.tsx`原Props透传；`frontend/src/App.tsx`的Business；`components/chat/useNativeChatThread.native.ts`的submitMessage | Web App:1804及ChatPanel:522提供state/屏障，Native Business与submitMessage缺少。预期当前写作侧会话每次提交使用同次绑定的Session快照，并在原保存成功后发送 | 复用`ensureSessionPersistedForAgent`、原文档消息校验、`sendCoordinatedChatUserMessage`的提交顺序、原`buildClaudeChatRequest`。上下文通过原文档协议按需取得，普通Chat不读取写作上下文 | 先确认需验收写作上下文发送；定义同次请求标识、documentId/Session匹配、取消/超时及保存失败回执。单纯打开快照不足以保证发送前保存。回退仅撤销本项接线，保留原发送及数据；V5/V6/V8/V9全部通过 |
| I4 乱序局部保护，条件化建议、未实现 | `frontend/app/_dream/App.tsx`的handleAgentSelect；`frontend/app/_dream/components/CalendarPopup.tsx`的handleOpenEntry | await后缺少同次Session选择校验，当前只有控制流风险。预期A创建或读取迟到不导航到B或覆盖B | 先复现；复用`WritingSuggestionController.isCurrent/ensureThread`的身份方式，在现有回调加触发Session/目标Cell/选择序号核对，无新全局状态 | 需可控乱序provider-free用例，后续才获测试修改授权；回退本项守卫。不得删除服务端已创建Thread或自动再次创建；V6/V9与Web相邻回归 |
| I5 实际故障处局部修正，条件化建议、未实现 | 消息阻断时仅`WritingDocument.Canvas`/`WritingView.receive`；呈现阻断时仅`frontend/src/App.tsx`的Business.sideChat/Modal | 需“点击→意图→GET→呈现”首个失败点的实际回执。预期同一卡片打开其原Thread | 原schema、URL/documentId/active校验、Modal及useNativeChatThread，不新增页面、接口或Thread规则 | I1/I2完成；修正后仅撤销本项差异即可回退。V1—V4/V7/V8和相邻Web回归 |

I2a为当前入口的最小局部建议；I3为独立已证发送源码差异，两项分别评审。I4/I5只在取得对应故障证据后进入实施。本轮源码、测试、依赖、配置及安装包修改数均为零，提交、产品构建、安装、迁移和部署未执行。

## 验收矩阵

| 编号 | 操作与预期，依据当前Web规则 | 执行前提与状态 |
| --- | --- | --- |
| V1 A/B/A选择 | 原日历依次选择两条已有记录；成功后EditorState.id、正文所属与卡片引用同步；失败保留原编辑。切记录不自动创建或切换Chat | 当前已授权账户、记录标识、对应安装资源、原请求元数据；设备未执行 |
| V2 对应Chat | A/B分别点击已有卡片；当前hover行为先取证。I2a完成后移动初态可见且无需hover、无需force、首触打开；实际history/status请求id等于卡片threadId；无自动创建；按原Voice关系允许相同Thread；桌面hover、折叠和缺关联条件保持 | 既有卡片与原GET回执；触屏技术样本和设备资格分别记录 |
| V3 返回与稿件 | 主Chat先留未发送稿，进入Writing并开关侧会话后主稿保持；A返回恢复已保存正文/卡片。单独记录侧会话关闭及Web面板关闭释放组件内稿，禁止承诺跨关闭恢复 | 不提交模型；临时稿按明确授权处理。当前未执行 |
| V4 网络失败及恢复 | 分别记录连接失败、HTTP失败、stream中断；原重试读取或返回前台后恢复原Thread；GET成功与页面展示分别核对，无重复POST | 故障注入仅隔离harness；真实网络变化需设备前提。当前原A/B请求缺失 |
| V5 写作发送上下文 | 后续I3中，POST沿原builder包含绑定目标记录的editor_state；先完成原保存；保存失败保留输入且无POST；普通Chat保持原规则 | I3局部协议与实施完成；确定性provider-free验证先行。真实模型需指定账户、模型及调用上限，本轮未执行 |
| V6 迟到与取消 | 关闭或切Thread后旧GET/SSE不能写新实例；A创建或记录读取迟到不得覆盖B。手动建议继续原Session/Cell/request/Thread校验 | 前半原合同23项覆盖部分；共享回调新增乱序覆盖待后续授权，设备未执行 |
| V7 现有任务 | 使用已有运行中任务开关页面；原history/status恢复状态；只有原Stop受理才停止。禁止新建模型任务用于本轮取证 | 既有任务标识和授权；本轮未执行 |
| V8 会话失效与权限 | 可控401进入原会话恢复；不同账户或无权限记录继续原拒绝，不展示旧正文；恢复后重选原记录及卡片 | 隔离harness或用户当前会话自然失效，禁止破坏真实凭证；本轮未执行 |
| V9 Web相邻回归 | 原日历、Voice复用、卡片发送/折叠/Chat入口、手动建议/重试、已保存状态恢复及正常Chat保持；桌面分栏与Web窄屏原覆盖模式保持 | 已有6文件23项确定性合同通过；完整浏览器和真实账户流程未执行 |

技术fixture与真实业务分别登记。23项合同未覆盖当前设备触摸、真实账户、实际网络、包内DOM版本或模型输出。无需重复下载浏览器、初始化环境或运行无关全量构建。

## 命令与验证回执

确定性检查由`luna_test_runner`执行，主Agent已读取[原始命令回执](/tmp/ink-note-chat-design-20261101/validation/receipts.md)。任务临时配置与输出位于`/tmp/ink-note-chat-design-20261101/validation/`；配置仅限定现有测试，不修改仓库测试。

| 执行命令 | 退出码 | 关键输出与覆盖边界 |
| --- | --- | --- |
| `git status --short`、`git branch --show-current`、`git rev-parse HEAD` | 0 | 已有修改/未跟踪文件保留，ios-native及上述HEAD |
| `xcrun devicectl list devices` | 0 | iPhone16 available/paired |
| `xcrun devicectl device info apps --device F615EA70-0AFD-5E1A-9373-AECBD061688D --filter 'bundleIdentifier == "com.inkmemory.mobile"'` | 0 | 0.1.0/22；未安装或重启应用 |
| `pnpm exec playwright test --config=/tmp/ink-note-chat-design-20261101/validation/playwright.config.mjs`，cwd=`frontend` | 0 | 23 passed，11.8s；testDir限定app/_dream，6个原文件，无webServer、浏览器、数据库、账户或模型请求 |
| 初次`pnpm exec playwright test <六个原文件> --workers=1 --reporter=line` | 0 | 67 passed，42.4s；误匹配ios/build中的副本，排除最小覆盖计数；完整argv归原始回执 |
| 中间`pnpm exec playwright test <六个原文件> --test-dir app/_dream --workers=1 --reporter=line` | 1 | unknown option --test-dir；harness命令错误，随后临时配置修正，无产品失败结论 |
| Python只读hashlib/JSON包体与来源核对，完整脚本归原始回执 | 0 | HBC摘要/大小相同、两项RN入口hash匹配；DOM源码逐文件映射缺口保留 |
| Python既有JSON字段抽取及console HTTP正则抽取，本文“请求回执与限制” | 0 | 16/17历史状态如表；22启动文件HTTP记录0，未读取正文或凭证 |
| `pnpm exec esbuild /tmp/ink-note-chat-design-20261101/validation/chat-widget-fixture.tsx --bundle --format=iife --platform=browser --alias:react=/Users/dmeck/project/ink-dream-memory/frontend/node_modules/react --alias:react-dom=/Users/dmeck/project/ink-dream-memory/frontend/node_modules/react-dom --outfile=/tmp/ink-note-chat-design-20261101/validation/chat-widget-fixture.js` | 0 | 仅临时harness打包原组件。首次缺少react路径别名的尝试退出1，修正后成功，未安装依赖 |
| `node /tmp/ink-note-chat-design-20261101/validation/run-chat-widget-touch.mjs`，初次Chromium及后续本机Chrome分别执行 | 0 / 0 | 390触摸两次导航0；桌面hover后导航1，两套结果一致；版本和渠道归各自JSON |
| `python3 /tmp/ink-note-chat-design-20261101/validation/validate_docs.py` | 0 | 7份Markdown的本轮新增内容、引用路径、来源行号、标题锚点、目录清单、围栏、术语和空白检查；原始计数归文档回执 |
| `node --experimental-loader=/tmp/ink-writing-mobile-design-20261101/validation/dom-purify-stub-loader.mjs /tmp/ink-writing-mobile-design-20261101/validation/check_mermaid.mjs /tmp/ink-note-chat-design-20261101/validation/linked-chat-diagram-1.md`，另外两条将文件名依次换为`linked-chat-diagram-2.md`与`linked-chat-diagram-3.md`，完整命令归原始回执 | 0 / 0 / 0 | 新增正常、异常恢复、状态图3/3解析成功；DOMPurify桩仅供语法解析，不作为渲染或业务验收 |
| `git diff --check -- <本轮7份Markdown路径>` | 0 | 已跟踪文件空白通过；未跟踪文件的新增内容由上述脚本覆盖 |

本轮执行23项既有合同和原组件隔离触屏采证，未运行类型检查、生产构建或真实模型。文档检查回执归[docs-validation-receipts.md](/tmp/ink-note-chat-design-20261101/validation/docs-validation-receipts.md)。

工作区非Markdown基线覆盖2026个文件；最终验证检测到`frontend/app/_dream/App.tsx`、`frontend/e2e/ios/WritingLayoutUITests.swift`、`frontend/e2e/writing-mobile-layout.spec.ts`与`frontend/ios/scripts/bundle-next.py`发生其他工作区变动，基线后非Markdown新增/删除路径均为零。本轮主Agent只编辑本文及6份相关Markdown，测试代理只写任务临时目录；上述文件的现有变动均保留，未回退或修改。关联卡片源码行号已按当前App核对，原入口和本节诊断条件保持。
