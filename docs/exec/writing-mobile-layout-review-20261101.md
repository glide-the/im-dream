<!-- [Input] 用户三项移动布局需求、直接源码证据、现行移动PRD与跨平台设计。 -->
<!-- [Output] 问题定位、最小处理范围、设计评审、验收计划与本轮命令回执。 -->
<!-- [Pos] 2026-11-01文档交付记录；代码实现及真机业务验收分别追踪。 -->

# 写作移动布局定位与设计评审

以下设计评审及原命令记录属于实现前阶段，源码行号按该阶段记录；当前代码合同归[现行设计](../design/multi-platform/writing-mobile-layout.md)，实施与验证见[最小代码实现阶段](#最小代码实现阶段)。

## 背景与问题

本轮范围为“更多 → 写作”的稿纸排版、启动心情滚动及所属页面的心情导航入口。开始时工作树已有6项Notion相关修改；执行期间其他工作继续修改Notion、更多导航及共享文档。本轮保留全部改动，共享文档只增加专项段落和索引。一次提示词优化在制定执行计划前完成，执行依据保存在本机`/tmp/ink-writing-mobile-design-20261101/execution-basis.md`。直接调查覆盖App、App.css、StateChooser、StateCube、会话及输入hook、Writing文档、原生页头与MoreNavigator，未追踪无关网络请求。

## 目标与边界

交付物为[原移动PRD补充](../prd/dream-workspace/mobile-app.md#写作排版与心情入口)、[正式跨平台交互设计](../design/multi-platform/writing-mobile-layout.md)及本记录。生产代码、持久化数据、数据库schema、依赖、设备安装和服务配置修改为零。未执行真实账号操作、模型调用或真机触摸测试。用户现象作为反馈记录，源码结论与待验证假设分别标明。

## 概念与规则

### 定位与处理结论

| 问题 | 当前代码事实 | 触发条件 | 原因或待验证假设 | 最小处理方案 | 影响文件 | 回归范围 |
| --- | --- | --- | --- | --- | --- | --- |
| 写作段落线条与字体 | [App.css:273](../../frontend/app/_dream/App.css#L273)为稿纸背景；[App.tsx:2038](../../frontend/app/_dream/App.tsx#L2038)和[2065](../../frontend/app/_dream/App.tsx#L2065)均为18px/1.8；默认32.4px与横线周期相等；[1994](../../frontend/app/_dream/App.tsx#L1994)固定Chooser槽32px+10.8px，[2029](../../frontend/app/_dream/App.tsx#L2029)首段加0.4px | 手机短宽度、长文换行、字体加载、字号变化，或非整行高建议/Chat卡混排 | 源码确认固定几何与缺少字体/宽度重算；默认周期错配证据缺失。字体实际加载、浏览器表单默认padding及单元尾部空隙仍待运行时测量 | 移动1.6行高与局部共享尺寸；统一textarea/高亮盒模型；每段稿纸线按实际行框起线；复用高度更新并补字体/宽度触发。桌面保持 | `App.tsx`、`App.css`、`hooks/useTextCells.ts`；局部文档作用域涉及`Editor/WritingDocument.css` | 字体切换、输入法、长段、多个单元、建议卡、评论定位、自动保存、滚动恢复及桌面分栏 |
| 启动心情无法触摸滚动 | [StateChooser.tsx:41](../../frontend/app/_dream/components/StateChooser.tsx#L41)按选择和loading展开；[248](../../frontend/app/_dream/components/StateChooser.tsx#L248)全屏居中且无滚动；[StateCube.tsx:258](../../frontend/app/_dream/components/StateCube.tsx#L258)为鼠标事件；[WritingView:28](../../frontend/app/_dream/components/WritingView.native.tsx#L28)关闭外层滚动 | 恢复后空选择，或点击已选控件；短屏、横屏、文字放大时内容超过区域 | 源码确认内容无滚动及固定尺寸；WebKit/Android触摸传递与键盘影响待设备复现。日期及偏好恢复规则见[useSessionLifecycle.ts:412](../../frontend/app/_dream/hooks/useSessionLifecycle.ts#L412)，自动触发频次继续由原恢复结果决定 | 原Chooser内约束高度并让整段内容纵滚；自适应立方体尺寸；纵滑不提交、点击沿原动画提交；取消沿原页面返回，补保存失败的原区域反馈 | `StateChooser.tsx`、`StateCube.tsx`、`App.tsx`、`App.css`；宿主无需开启外层滚动 | 长问候/长选项、触摸至末端、拖动后无误选、同日/跨日/历史恢复、确认语义与页面返回 |
| StateChooser移入所属导航栏 | [App.tsx:1998](../../frontend/app/_dream/App.tsx#L1998)在正文首部；[WritingView:24](../../frontend/app/_dream/components/WritingView.native.tsx#L24)页头仅返回与标题；[protocol:7](../../frontend/app/_dream/components/Editor/WritingDocument.protocol.ts#L7)无心情展示或展开消息 | 原生写作页及Web窄屏；原生横屏仍由原生宿主承载 | 源码确认入口位置与目标有差距；无需新增全局导航入口 | 原生页头右侧展示当前值并打开同一Chooser，复用既有消息身份校验；Web新增局部写作页头；正文只保留日期与标签；原3项工具保持可达 | `WritingView.native.tsx`、`Editor/WritingDocument.tsx`、`Editor/WritingDocument.protocol.ts`、`App.tsx`、`StateChooser.tsx`、`App.css`；`MoreNavigator.native.tsx`仅在返回关闭接线需要时调整 | 展开/选择/返回/重进、页面隐藏、乱序或旧文档消息、加载/失败、相邻更多页面、账户退出 |

表内均为源码定位与建议范围；三个用户现象尚未通过本轮浏览器或设备复现。网络波动与布局问题的直接关联尚无证据。原生WebView保留现有滚动配置，内层DOM纵滚需独立验证。

### 方案比较与收敛

| 问题 | 比较方案 | 选择与删减依据 |
| --- | --- | --- |
| 稿纸排版 | 只改全局32.4px；现有TextCell内局部渐变与共享行框；新画布/逐行测量组件 | 采用局部渐变及现有盒模型，覆盖非整行卡片。只改全局周期无法消除相位累积；新画布、字形测量和新增组件退出范围 |
| 留白 | 保持1.8且只修几何；移动沿现有1.6文字节奏并修几何；新增字号/行距设置 | 采用移动1.6，默认28.8px，字号保持18px；相对行高随有效字号变化。交互与视觉验收核对可读性；新增设置退出范围 |
| 心情滚动 | 原组件内受限纵滚；套用共享Modal；重写Native选择器 | 采用原组件内纵滚。共享Modal现有遮罩/Escape/关闭按钮会增加退出动作；重写Native选择器扩大选项与状态同步范围 |
| 页头 | 在局部文档再画一套Native导航；宿主现有页头加展示/打开意图；抽离新全局心情服务 | 采用宿主页头与原文档通信。保留选择保存所有者，禁止重复存储、全局服务及第二套导航 |

发现依据为当前目标、原移动PRD及源码；核心范围为排版几何、纵滚区域和本页入口。方案比较后确定以上局部改动，正式设计与验收依此交付。历史设计和已有图示保留。

### 最终设计评审

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 三项问题可追踪 | 每项需要事实、建议与验收对应 | 定位表关联源码及V01—V12 | 三项均有处理范围、预期和验证前提 | 实施后执行矩阵 |
| 字体与线条 | 默认算式吻合，单独宣称周期错误缺乏证据 | 明确源码风险，移动使用共享相对行框 | 默认28.8px、局部起线和盒模型规则已定义 | 实际字体/缩放测量与视觉验收 |
| 自动触发 | “第一天”表达无法覆盖会话优先及偏好日期判断 | 以原恢复结果和loading驱动 | 无新增每日计数、启动标记或频次设置 | 原账户跨日/历史恢复验证 |
| 完整触摸访问 | 原全屏居中无滚动，立方体300px固定 | 受限高度、整段滚动、共享立方体尺寸 | 所有原可选项和提示可滚动触达 | iOS/Android实际触摸与大字 |
| 确认、关闭与取消 | 原Chooser无独立确认/关闭按钮，选项即提交 | 删除新增确认页、底部按钮和跳过动作 | 保留原提交；取消通过所属页返回更多 | 淡出期间返回与回调取消验证 |
| 页面归属 | 原生已有页头，心情逻辑仍在DOM | 页头展示/打开意图，原App保存 | 单一可见入口、原处理函数和持久化 | 小范围消息与返回接线 |
| 小屏操作拥挤 | 原3项悬浮工具可能覆盖新页头 | 保留3项工具同组并预留操作区 | 心情属于导航，工具入口保持可达 | 最窄屏及文字放大布局 |
| 数据与错误 | 心情偏好失败当前只有console | 原反馈区显示失败，重试仅偏好写入 | 无重复会话创建；本地值与保存回执分别描述 | 单次保存失败/重试与晚到响应 |
| 状态与依赖 | 可复用loading/expanded/fading/active | 删除新业务状态、配置、依赖和平台层 | 新增仅局部尺寸、展示消息和瞬时反馈 | 实现时复核监听与回调释放 |
| 桌面和相邻业务 | 移动样式可能波及桌面评论几何 | 分别限定窄屏及局部文档，保留桌面计算 | 桌面行距、Chooser和Writing/Chat保持 | 桌面、Calendar、Agent与更多回归 |
| 图文与交付资格 | 图示需要区分现有函数与建议接线 | 消息、样式、提示均标建议未实现 | PRD骨架、正常/异常/状态图与矩阵对应 | 文档门禁回执与实施后验收 |

**评审结论：通过。** 本结论适用于定位与设计文档交付；三项处理方案已收敛，业务与权限边界保持，过度设计已删减。代码实现、浏览器交互和真机验收均待执行，验收前提见下表。

## 验收计划

下表均为待执行计划。尺寸为验证取样，沿现有布局断点和设备可用视口，不新增产品阈值。技术自动化使用公开生产组件与DTO及明确fixture；真实业务只在用户指定账户和本机正常服务中执行。

| 编号/范围 | 预期结果 | 验证方式 | 执行前提 |
| --- | --- | --- | --- |
| V01 默认与不同字号 | 18px默认移动行框28.8px；文字放大后横线周期与有效行框一致，高亮与输入重合；桌面保持32.4px | provider-free浏览器读取computed style和行框几何；人工检查18/22/系统放大样本 | 排版实现完成，当前生产组件，已安装Chrome；iOS/Android系统字体放大需设备 |
| V02 长段与自动换行 | 中英混排、标点、长词、空行、末尾换行无裁切；增删内容后高度及光标可见 | 原textarea输入、粘贴和输入法；记录scrollHeight/clientHeight及截图 | 原会话DTO fixture；真实输入法需设备 |
| V03 字体加载与失败 | 后备可编辑；字体到达后重排而正文/选区/阅读位置保持；失败继续后备字体 | fixture控制原字体资源延迟/失败，前后几何与文本比对 | 不改业务源码、不关闭安全策略；正常资源可用 |
| V04 混排与评论 | 建议卡/Chat卡之间下一正文首线重新对齐；文本与建议顺序、评论锚点保持 | 既有写作建议和文档fixture；核对多个TextCell、桌面评论/分栏 | 原数据结构与手动请求入口；模型使用fixture |
| V05 窄屏与横竖屏 | 320/390宽度、短高及横屏无横向溢出；页头、工具、末行与反馈可达；安全区只占一次 | 浏览器视口与截图；iOS/Android旋转及系统区域核对 | 移动布局实现，真实设备安装对应候选；宿主视口记录 |
| V06 键盘 | 原生与Web窄屏光标、末段可滚至键盘上方；打开心情后键盘收起，返回不自动唤起 | 设备输入与心情展开/返回，录制可见区域 | 正常页面与系统键盘；DOM聚焦测试仅作补充 |
| V07 心情长内容与触摸 | 长问候/长名称/大字/横屏可滑至末端，全部原可选项可点；纵滑不误选，背景不滚动 | provider-free组件几何/指针检查；真机手指从各区域拖动 | 原前3项/锁定配置保持，iOS WKWebView及Android WebView分别执行 |
| V08 心情选择与取消 | 点击沿原反馈及淡出只提交一次；返回更多无保存，重进按原有值/空值展示；淡出中返回取消未提交回调 | fixture统计公开偏好与会话请求；页面/系统返回及计时控制 | 导航和回调清理实现；原生Back需设备 |
| V09 触发与恢复 | 同日有值、跨日、current-session、历史选择及偏好日期组合保持原规则；无新增频次 | 受控时钟和公开会话/偏好DTO fixture；真实账户读取单列 | 复用原useSessionLifecycle，不复制状态机；写入fixture或指定真实账户 |
| V10 失败与重试 | 偏好失败保留当前值并可见重试；重试不新建会话或覆盖后来的选择；文档Retry、401沿原恢复 | fixture失败/晚到响应；公开组件操作及请求计数 | 对应反馈与协议实现，独立故障注入环境 |
| V11 导航与文档消息 | 心情入口仅在写作页头出现一次；旧URL/documentId/revision/nonce无作用；loading不可点，重载/active切换不误打开 | 原协议测试及Writing原文档fixture；RN组件与实际WebView分项验证 | 建议消息实现，复用身份校验，原生/网页两类证据 |
| V12 保存与相邻业务 | 原编辑、保存、重新进入、Calendar、新建、Agent入口、建议重试、Chat返回、更多五项及权限行为保持；桌面无布局变化 | 既有`writing-document.spec.ts`、`writing-manual-suggestions.spec.ts`及原导航回归；真实业务公开入口单列 | 技术fixture为Luna阶段；真实账户/本机正常Dream、Admin及PostgreSQL需另行满足授权和条件 |

每项回执记录平台、候选版本、视口/有效字体、动作、预期、实际及证据。浏览器runner无法启动记录为harness前置失败；文档检查、模拟触摸及组件fixture均不提升真机资格。

## 本轮验证记录

初轮确定性检查由`luna_test_runner`执行。Markdown清单与头注、本轮本地引用及锚点、源码行号、新增术语检查通过；原始结果在`/tmp/ink-writing-mobile-design-20261101/validation/`。仅扫描本轮链接，旧链接总数单列，旧文档完整引用检查退出本轮范围。

| 实际命令或检查 | 退出码 | 关键输出与边界 |
| --- | --- | --- |
| `python3 /tmp/ink-writing-mobile-design-20261101/validation/check_docs.py` | 0 | 8目标、8项清单/头注标记、引用/锚点/源码行号通过；新增禁用术语0；源码探针通过 |
| `node --experimental-loader=/tmp/ink-writing-mobile-design-20261101/validation/dom-purify-stub-loader.mjs /tmp/ink-writing-mobile-design-20261101/validation/check_mermaid.mjs docs/design/multi-platform/writing-mobile-layout.md` | 0 | 新正式稿正常时序、异常恢复、状态转换共3图，3/3解析通过；采用当前已安装Mermaid与临时Node环境DOMPurify接口桩，仅检查语法 |
| `git diff --check -- docs/prd/dream-workspace/mobile-app.md docs/prd/dream-workspace/.folder.md docs/design/multi-platform/.folder.md docs/design/multi-platform/README.md docs/design/multi-platform/react-native-web-project-structure.md docs/exec/.folder.md` | 0 | 无空白诊断；两份新稿通过单独空白检查 |
| `git diff --no-index --check /dev/null docs/design/multi-platform/writing-mobile-layout.md` | 1 | 存在新增文件差异，空白诊断为空；Python尾随空白检查为0项 |
| `git diff --no-index --check /dev/null docs/exec/writing-mobile-layout-review-20261101.md` | 1 | 同上；退出1按差异存在记录，未改写为命令退出0 |

主Agent逐项核对PRD骨架、设计三图、状态表、定位表与V01—V12：原选择函数和保存职责一致，建议消息及布局全部标注未实现，退出操作、延迟回调清理、失败提示和验收前提相互对应。该项属于文档评审，实际页面行为待实施后验证。

最终整体验证命令为`bash /tmp/ink-writing-mobile-design-20261101/validation/run_validation.sh`，退出码0，输出`check_docs=0 mermaid=0 tracked_diff=0 design_no_index=1 review_no_index=1 whitespace=0`。其中两次退出1为新稿相对空文件的差异存在，诊断为空；新稿另由`python3 /tmp/ink-writing-mobile-design-20261101/validation/check_new_whitespace.py`检查，退出码0。完整原始回执为同目录的`receipt.md`与`receipt.json`。本段回执补充后仅复核文档引用、术语与差异，图示正文保持。

未执行生产构建、类型检查、应用浏览器复现、触摸/键盘、原生设备、真实账号、网络、模型、数据库或业务端到端验证。临时目录保留供复核，未创建服务、端口或仓库生成物。


## 最小代码实现阶段

用户已授权按评审稿完成最小实现并分别交付验证状态。执行依据保存于`/tmp/ink-writing-mobile-implementation-20261101/execution-basis.md`；本阶段开始时工作树已有Notion、更多导航和回顾相关改动，全部保留。

| 需求项 | 交付物与行为 | 当前进度 |
| --- | --- | --- |
| 移动排版 | App/App.css限定移动行框与每单元稿纸线；useTextCells更新字体及宽度变化后的高度和阅读位置 | 源码已实现 |
| 心情滚动 | 原Chooser Portal到编辑区域内，问候/立方体/说明共同纵滚；StateCube保留原选项并清理200ms回调，Chooser清理800ms回调 | 源码已实现 |
| 所属页头 | Web本页页头和原生WritingView页头显示当前心情；原文档展示快照与一次打开意图，原App继续持久化 | 源码已实现 |
| 失败恢复 | 原反馈区域提供偏好失败重试，匹配会话/选择/提交序号，原EditorState保存路径保持 | 源码已实现 |
| 桌面边界 | 原字体、行高、Chooser槽、背景线、工具和Writing/Chat布局保持原分支 | 生产副本浏览器回归通过 |

技术阶段已取得Web类型、原生类型和独立临时源码副本生产构建退出0；初次原生页头浏览器fixture遇到jsxDEV模块导出错误，已补齐与既有fixture一致的预打包配置。修订后原生页头1项通过；Web生产副本及相邻写作目标22项通过，浏览器交互占11项、源码/控制器验证占11项。命令同时匹配的旧ios/Next/build-source镜像11项单独登记，退出目标覆盖计数。

| 验证类别 | 实际命令 | 退出码与证据 |
| --- | --- | --- |
| Web类型 | `corepack pnpm exec tsc --noEmit --pretty false`，工作目录frontend | 0，无诊断 |
| 原生类型 | `corepack pnpm native:typecheck`，工作目录frontend | 0，原生TypeScript工程通过 |
| 生产构建 | `NEXT_TELEMETRY_DISABLED=1 corepack pnpm exec next build --webpack`，工作目录为本阶段validation内frontend-production-copy-20261101-1245 | 0，编译成功、TypeScript通过、9/9静态页；复用原配置与已装依赖，排除.env及原.next |
| 原生页头组件 | `corepack pnpm exec playwright test e2e/writing-native-header.spec.ts --config=/tmp/ink-writing-mobile-implementation-20261101/validation/playwright.config.cjs --reporter=line --workers=1` | 0，1项通过；消息乱序/旧文档、active和重载已验证，console及pageerror为空 |
| Web与相邻写作 | `E2E_WEB_BASE=http://127.0.0.1:41873 INK_WRITING_EVIDENCE_DIR=/tmp/ink-writing-mobile-implementation-20261101/validation/evidence-web corepack pnpm exec playwright test e2e/writing-mobile-layout.spec.ts e2e/writing-document.spec.ts e2e/writing-manual-suggestions.spec.ts app/_dream/components/__tests__/WritingSuggestionContract.test.ts app/_dream/hooks/__tests__/WritingSuggestionController.test.ts --config=/tmp/ink-writing-mobile-implementation-20261101/validation/playwright.config.cjs --reporter=line --workers=1` | 0，目标22项通过，另有旧镜像11项；移动行框/宽度变化、字体到达、长文、更多取消、单次选择、保存重试、原文档及桌面布局均有断言 |

原始命令回执归`/tmp/ink-writing-mobile-implementation-20261101/validation/`中的`receipt`、`quick-stage`、`native-header-and-build`及`web-and-native-final`文件。首次空白页按fixture模块加载失败保留，原生页头修订后通过；该次失败不用于判定产品按钮与系统触摸。

截图为同目录`evidence-web/writing-mobile.png`与`writing-desktop.png`，覆盖最窄320px移动文字放大和1280px桌面布局。所有请求使用公开DTO fixture，正常服务和原.next保持；测试自有41873端口已释放。新增Chrome触摸输入滚动断言已定向通过：使用CDP touchStart/move/end实际输入推动内层scrollTop，滑动没有产生心情写入；随后沿原选项完成选择。该用例继续属于浏览器验证，物理设备手势另验。

`app/_dream/components/__tests__/WritingChooserProtocol.test.ts`独立执行退出0，2项通过。连同前述控制器/源码11项，本阶段目标技术用例共13项；网页11项及原生页头组件1项，共12项独立浏览器用例通过。定向触摸复验沿同一已有用例执行，次数单列，覆盖计数保持。

文档检查初次退出1：评审记录缺少新协议规格的显式登记；本段补齐`WritingChooserProtocol.test.ts`。补齐后执行`node --experimental-loader=/tmp/ink-writing-mobile-design-20261101/validation/dom-purify-stub-loader.mjs /tmp/ink-writing-mobile-implementation-20261101/validation/check_writing_docs.mjs`退出0：9份专项文件、当前/历史6图、引用、术语和空白通过。代码/spec头注14项、直接目录合同11份检查退出0；24目标精确diff检查退出0，新稿/spec共6文件空白检查退出0。实施前稿的原代码行号按历史阶段解释，已单列，不声明为当前行号。

独立协议完整命令为`corepack pnpm exec playwright test app/_dream/components/__tests__/WritingChooserProtocol.test.ts --config=/tmp/ink-writing-mobile-implementation-20261101/validation/playwright.config.cjs --reporter=line --workers=1`，退出0。触摸定向完整命令为`E2E_WEB_BASE=http://127.0.0.1:41873 INK_WRITING_EVIDENCE_DIR=/tmp/ink-writing-mobile-implementation-20261101/validation/evidence-web corepack pnpm exec playwright test e2e/writing-mobile-layout.spec.ts -g 'short chooser' --config=/tmp/ink-writing-mobile-implementation-20261101/validation/playwright.config.cjs --reporter=line --workers=1`，退出0。

9个核心生产文件与构建副本比较：7项字节一致，App.tsx两处Desktop注释及WritingView.native.tsx的openExternalLink import顺序有差异，运行表达式相同。hash比较命令按差异存在退出1，未改写为字节一致；生产构建与浏览器回执适用于对应副本，当前两项差异无需重建。

完整末轮证据归`/tmp/ink-writing-mobile-implementation-20261101/validation/final-targeted-receipt.md`及同名JSON，包含命令、退出码、逐文件SHA-256、首次失败与修订后的通过记录。当前最小实现评审通过；设备、真实账户和真实模型资格分别保留未执行状态。

真实账户、模型、数据库业务写入、设备构建安装及真机验收未执行。iOS/Android系统手势、键盘、安全区和系统文字放大继续按V01—V12前提独立验收。


## 安装资源纠偏与模拟器验证

用户截图包含原生写作页头读取中、正文旧心情与工具重叠及大间距线条。当前构建22的原生HBC含chooser-view，包内Next的2038份JS/CSS无新版Writing特征；旧准备目录的App/WritingDocument缺少对应移动参数及展示消息。该证据确认原生与包内网页资源采用不同阶段。前阶段25项用例属于源码和独立制品技术资格，手机实际组合退出该资格。

最新用户指令采用模拟器验证，物理手机/USB/镜像操作停止。一次纠偏执行依据与用户修订归`frontend/ios/build/writing-layout-20261101/execution-basis.md`。本轮独立Next根为该目录的`Next`，正常Web、原共享Next准备目录及全部既有改动保持。

| 工作项 | 实施与当前结果 |
| --- | --- |
| 来源门禁 | prepare-next记录sourceInputs，bundle-next在复制前检查checkout/prepared；包内保留来源回执。原默认输出兼容，具名输出保护并行构建 |
| 独立编译 | 新Next生产构建退出0，TypeScript通过、静态页9/9；不安装依赖，不复制.env |
| 旧源核对 | 旧ROOT的verify-sources退出1，明确IOS_NEXT_SOURCE_RECEIPT_MISSING；按预期阻止打包 |
| 新源核对 | 新ROOT的verify-sources退出0，549项runtime inputs通过 |
| 故障探针 | 修改本轮自有prepared源码或回执后，verify退出1并报告IOS_NEXT_SOURCES_STALE；逐字节恢复后退出0 |
| 实际资源 | 原bundle-next装配2332文件到本轮asset-app，独立serverEntry、source-receipt、static/public均来自该编译 |
| 模拟器耦合 | 原WritingView、真实Hermes/WKWebView加载实际包内Next；内存DTO承接所有写入，最终r6的1项UI流程通过 |

第一阶段精确命令及退出码归`frontend/ios/build/writing-layout-20261101/validation/receipt.md`与同名JSON；缺少来源及变更来源的退出1为预期失败，未汇报为实际命令退出0。Simulator使用独立应用及具名数据，仅清理本轮自有进程、端口和设备状态。真实账户、数据库、模型与手机安装使用数保持0。


模拟器r4按当时断言通过。主Agent逐张复核真实截图，确认选择后仍出现键盘、空输入绘制两行。源码对应`App`的通用空白单元自动聚焦effect及textarea默认rows=2；追加移动分支显式rows=1、保留桌面空白聚焦并关闭移动通用自动聚焦。UI用例新增选择后键盘关闭断言，浏览器补空输入高度等于一行的检查；r4截图、来源回执与失败范围保留。

r5新源码的编译、类型检查及6项来源门禁回归通过。该次UI退出65、Web定向3项退出1（2通过/1失败），原始日志归`validation/r5-receipt.md`。主Agent核对实际服务根，确认runner将`UNLOCALIZED_RESOURCES_FOLDER_PATH`设为`next`，新资源被放到`asset-app/next/next`；服务继续从`asset-app/next`加载r4。当前App与新准备回执摘要为`b20bffe15c648d422dd811c5de440e9dd36ea7c4888db46e71ec6fa384f92ecb`，旧服务回执为`6994dab19d71a09cc3e48f5b369fb0ec867132558de74ed29efa0e31463f3925`。r5页面失败按旧r4制品解释，最新源码行为需更正资源根后独立判定；原始失败不覆盖。

### 最终模拟器与浏览器回执

r6更正资源输出根，启动前核对实际Next来源。独立Simulator为`InkMemory-Writing-20261101`，iPhone 16/iOS 18.6，UDID `9FA7728D-341E-4B42-BBD1-D06278576144`；独立应用为`com.inkmemory.writingqualification`。原WritingView与真实Hermes/WKWebView加载本轮Next原页面；该次Next服务运行在Mac loopback，公开DTO由内存fixture接收，App内置Node宿主及真实账户业务退出该资格。

下表命令由`luna_test_runner`执行，仓库相对路径均从本仓库根解释；Web命令工作目录为`frontend`。完整原始日志和摘要归`frontend/ios/build/writing-layout-20261101/validation/`。

| 验证类别 | 实际命令 | 退出码与关键结果 |
| --- | --- | --- |
| 生产构建 | `NEXT_TELEMETRY_DISABLED=1 corepack pnpm build`，目录为本轮`Next/build-source` | 0，Next 16.1.6编译及TypeScript通过、9/9静态页 |
| 资源装配 | `TARGET_BUILD_DIR=/Users/dmeck/project/ink-dream-memory/frontend/ios/build/writing-layout-20261101 UNLOCALIZED_RESOURCES_FOLDER_PATH=asset-app INK_IOS_NEXT_ROOT=/Users/dmeck/project/ink-dream-memory/frontend/ios/build/writing-layout-20261101/Next python3 frontend/ios/scripts/bundle-next.py` | 0，2332文件；实际根为`asset-app/next`，来源与当前输入一致 |
| iOS真实WebView交互 | `INK_WRITING_UI_TARGET=com.inkmemory.writingqualification xcodebuild test-without-building -xctestrun /Users/dmeck/project/ink-dream-memory/frontend/ios/build/writing-layout-20261101/simulator/ui-runner-r2/DerivedData/Build/Products/InkNativeUITests_iphonesimulator18.5-arm64.xctestrun -destination 'platform=iOS Simulator,id=9FA7728D-341E-4B42-BBD1-D06278576144' -resultBundlePath /Users/dmeck/project/ink-dream-memory/frontend/ios/build/writing-layout-20261101/simulator/ui-runner-r2/WritingLayout-r6.xcresult -parallel-testing-enabled NO -only-testing:InkNativeUITests/WritingLayoutUITests/testPackagedWritingHeaderAndTouchChooser` | 0，1项通过、0失败；页头消息、正文去重、工具与日期分区、输入与收键盘、返回保稿、长启动内容真实swipe、单次选择及选择后键盘关闭均通过 |
| Web浏览器交互 | `E2E_WEB_BASE=http://127.0.0.1:62539 INK_WRITING_EVIDENCE_DIR=/Users/dmeck/project/ink-dream-memory/frontend/ios/build/writing-layout-20261101/validation/r6-web-all-evidence corepack pnpm exec playwright test --config /Users/dmeck/project/ink-dream-memory/frontend/ios/build/writing-layout-20261101/validation/r5-playwright.config.ts` | 0，7项通过；空单行、18/22px字体、320px与长文、原更多返回、CDP触摸滚动、取消两段延迟、保存失败重试、原生横屏文档nonce、桌面原值与字体加载均有断言 |
| Web/原生类型 | `corepack pnpm exec tsc --noEmit --pretty false`；`corepack pnpm native:typecheck` | 均0；当前源码无诊断 |
| 来源门禁回归 | `python3 frontend/e2e/ios/test_next_source_receipt.py` | 0，6项通过；缺失来源、源码变化、双快照差异及非法路径拒绝，当前快照只读通过 |

主Agent复核`validation/attachments-r6/manifest.json`对应三张真实截图：`writing-packaged-ready`空单元仅一条稿纸线、页头Unhappy且正文无重复；`writing-startup-touch-scrolled`显示滚动后原3项选择；`writing-selected-header`页头OK、空输入仍为一行、软键盘关闭。fixture记录`preferenceWrites=[{"selected_state":"ok"}]`、`unexpectedWrites=[]`，真实账户、数据库写入和模型调用均0。

### 纠偏评审

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 段落行框 | 空textarea默认rows=2，移动高度形成额外一行 | 移动显式rows=1，保留原高度更新及桌面分支 | 浏览器空高度与有效行框一致，模拟器截图一行 | 系统字体缩放及真实输入法 |
| 心情与键盘 | 通用空白聚焦在心情变化后唤起软键盘 | 移动关闭该通用自动聚焦，原明确编辑动作保持 | 模拟器打开心情及选择后键盘关闭，长内容可真实滑至选项 | Android系统手势与物理设备 |
| 所属页头 | 新原生页头曾加载旧网页，读取状态持续 | 刷新对应Next及来源门禁，核对实际服务根 | 模拟器页头收到原文档展示消息，正文入口移除 | 手机当前安装包采用更新资源后独立验收 |
| 桌面与业务 | 移动修订需要保留相邻布局及保存职责 | 所有规则限定移动，继续原状态/提交入口 | 桌面、取消、重试、保存与保稿定向通过 | 真实账户业务按公开入口单列 |
| 新增内容 | 构建输出参数与测试夹具有具体纠偏需求 | 限制具名输出，fixture留在e2e目录 | 新业务状态、后端接口、依赖及Schema均0 | 完整设备发布构建另行登记 |

Next服务62539与fixture服务62601已关闭，隔离Simulator为Shutdown；原有服务和其他设备保持。r5的旧资源失败记录及r6的来源摘要、截图、日志保留，完整回执为`validation/r6-receipt.md`和同名JSON。

**评审结论：通过。** 本结论覆盖最小源码修订、来源门禁及上述技术、浏览器和iOS模拟器交互。物理iPhone和Android真机验收未执行，手机当前安装包未在本轮更新；真实账号、数据库及模型资格保持未执行。原有未提交改动保留。
