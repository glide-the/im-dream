<!-- [Sync] 2026-10-07: 冻结源码副本完整三spec实际54/54、tsc/ESLint/build exit0；sticky仅修测量语义，最终文档/清理待新阶段合并回执。 -->
<!-- [Input] 用户2026-10-07布局修正、现行Calendar PRD/正式稿与真实DOM/CSS/harness。 -->
<!-- [Output] 唯一右侧浮空外壳/自然高度的影响评估、增量设计门禁及待执行旅程矩阵。 -->
<!-- [Pos] 本轮独立执行证据，不覆盖2026-10-06回执或历史。 -->
<!-- [Sync] 2026-10-07: 设计增量已交付，生产/测试未改；独立评审、实施与实际验证仍待完成。 -->
<!-- [Sync] 2026-10-07: 独立评审通过后CSS/测试源码冻结；保留原48旅程并新增6个高度/menu场景，待Luna实际验证。 -->
# Calendar右侧浮空纸片与自然高度：影响和门禁

## 1. 当前结论与依据

用户明确：左右不一定等高；右侧外层仍为圆角浮空纸片，只有内部简约留白。本轮改正此前把整个右侧做成无圆角/阴影平面的解释。依据[现行PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)、[正式稿](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)与已渲染[PDF第5页](../design/claude-agent/calendar-borderless-ui-workflow-20261006/inputs/target_image.png)。2026-10-06四阶段、独立评审/执行记录/历史均保留，其48/48回执不作为新CSS通过依据。

Optimized Prompt：复用已有四阶段进行外壳/高度小范围增量，保存全文历史，直接更新PRD骨架和正式CSS/状态/验收；保留原业务图、owner和API。只交可评审文档，独立评审通过才实施，由Luna实际验证新布局和原完整旅程。

本轮[独立设计评审](./calendar-floating-workspace-design-review-20261007.md)已通过，外壳/高度/in-flow菜单CSS及测试源码已落实并冻结；**该浮空冻结副本完整54例、tsc/ESLint/build已实际通过（§8）；最终文档/隔离清理待回执，新Notion前端另阶段验证**。下方原设计交接保留其历史时点，源码完成不代表验收完成。

## 2. 实施前影响评估

| 项目 | 事实与边界 |
| --- | --- |
| Git基线 | `develop`；HEAD=`dc5c7723f28bc75efe55f7573182fe857782dbdf`，广泛dirty涉及任务/Notion/文档和其他Agent工作；现有变化完整保留，不reset/revert/格式化无关文件。 |
| 当前文件所有权 | 本worker仅持有现行calendar PRD/正式稿、pre-floating完整历史、20261007四阶段增量、本exec及相关folder；主任务审阅/独立评审。现阶段不改生产CSS/TSX/E2E。通过后另阶段限定CalendarPopup.css、必要文件头/folder、原3spec/fixture视觉验证及README英中事实同步，Luna持有实际命令和隔离资源。 |
| 页面/组件/复用 | CalendarPopup外壳包含左calendar、右workspace→tabs→workspace-scroll→3个section；复用现有DOM、字体/图标、paper/text/hover/active/focus/shadow Tokens和64/40rem断点。无需新组件、框架、字体、CDN或通用平台。 |
| 当前代码差距 | workspace与section height100%使短内容填满；workspace radius/shadow0；tabs/section opaque paper但各平面无角。窄屏Calendar末尾padding0，旧workspace-scroll尾部垫片不能保护新增外壳shadow。拟单外壳自然height+确定max-height/flex shrink、同一顶底角和外画布安全留白。 |
| owner | activeTab/focusedTab/tooltip、selectedDate、panelRefs/mobileScrollRef、安排输入/任务LIST-RESULT/已读结果不变；moreOpen/ref/keyboard/onLayerChange及编辑/历史独立Modal owner不迁移。Modal原monthPrev initialFocus及harness实际ready继续保留。 |
| 接口/权限/数据边界 | 公共documents/scheduled/session APIs、Admin归属、Notion凭证、当前选中数据库page快照、今天更新项校验、actor/date/timezone/request guard和缓存均不改；无字段/schema缺口，不新增Admin依赖任务。 |
| 呈现 / 已知风险 | 只调整workspace外壳和高度。absolute more菜单在短高最后行可能被section裁切，不能靠固定大min-height或上开猜空间；提出原menu参与task下方布局，须评审并实际点击验证。CSS百分比上限/flex链、hidden长panel、异步状态高度、RESULT、切栏scroll与焦点、圆角接缝/末尾shadow为必验风险。 |
| 影响业务旅程 | 原安排/未发送Chat草稿、编辑成功/失败/冲突、历史/结果、运行/暂停恢复/删除撤销、Thread导航、日记打开返回/当前/删除、Notion连接/快照/校验/刷新/并发均完整回归；只呈现变化，不新建状态机。 |
| 测试数据/隔离 | 复用frontend/e2e生产DTO fixture、原3spec和installed Chrome；增加短/空/长数据仅测试DI，不在业务放fallback。新输出建议`output/calendar-floating-workspace-20261007`、新端口候选55175，由Luna先确认空闲并记录自建PID/副本身份。无真实模型/账号写入或数据库需求。 |
| 清理边界 | 仅本轮自建55175（实际由runner确认）与具名sourcecopy/node_modules symlink；保留回执/截图。不能停止用户正常5173/8765或删除20261006证据。现设计阶段未启动进程/创建测试资源。 |
| 非范围/阻塞 | Project/Episode/Run/Hook/Runtime、Chat业务、连接器配置/同步/缓存/API/权限、shared schema全部不改。无跨项目依赖。当前门禁是本次独立评审未完成，flex/menu和实际旅程尚未验证。 |

## 3. 最小设计与历史保留

右workspace唯一持有opaque paper、24/20/18px原paper圆角及对应soft/medium shadow，border0/gap0/overflow visible。tabs顶角/section底角绘制同一外壳接缝，内部无独立border/shadow或普通条目卡片。桌面保留原left/Modal/Calendar高度，workspace auto/max-height100% top对齐，确定grid row与两层min-height0/flex:0 1 auto传递上限；短自然结束，长active section滚动，不测量JS。窄屏原整体scroll/sticky tabs、section auto/visible，末尾外画布留白中幅2.25rem/小幅1.75rem，workspace-scroll不再当外部阴影垫片。

原more菜单打开时采用CSS display:contents把同一menu作为task下方右对齐grid item，关闭不预留高度；功能菜单原border/shadow可留。需独立评审确认这项呈现，不能先实施。源码已有菜单ArrowUp/Down/Home/End与首项聚焦；其他关闭/outside语义只按现有源码，不新增产品规则。DOM/ref/contains、more命中区、tab顺序、Escape/原Modal恢复和最后项点击须实测。

- [PRD修正前完整原文](../prd/calendar/calendar-right-panel-tabs-prd-pre-floating-20261007-history.md)：SHA256=`c7f7406c51d79812ca0a1def800f2f658e4a316138c464eb9b7e5716aba95a27`，17214 bytes。
- [正式稿修正前完整原文](../design/claude-agent/calendar-right-panel-tabs-ui-design-pre-floating-20261007-history.md)：SHA256=`0d59c569a8d6cec7bafcd0498eca4696dc2ad4e313dc803dc33f52476fe1b18b`，17732 bytes。
- 正式稿只替换视觉正文和本次状态说明，3个Mermaid正常/异常/状态业务块原文保留；当前PRD直接包含新骨架。
- [四阶段增量索引](../design/claude-agent/calendar-floating-workspace-workflow-20261007/README.md)依序交付PRD→结构→层级→视觉，复用既有图像路径，不重做已完成业务设计；技能证据不代替正式正文。

## 4. 必要验收矩阵（当前均待执行）

| 旅程/状态 | 实际证据 |
| --- | --- |
| Calendar完整入口 | 默认栏目/日期、键盘手动激活/tooltip优先、日期变化、关闭重开、同日草稿/scroll/LIST-RESULT保留；hidden长panel不撑高且不可聚焦/播报 |
| 自然高度/动态变化 | 三栏目短/空/加载/错误/partial真实wrapper高度，低于left且不强制等高；短→长→短、切栏/换日、刷新结果/空和LIST↔RESULT，原左月历尺寸不变 |
| 长内容/原scroll owner | 桌面上限真实grid内容区且active section实际scroll，tabs外置；1024/430/390整体Calendar滚到底、sticky tabs纸底及下外壳可见；RESULT/Modal原子滚动保持 |
| 任务完整旅程+menu | 原安排/未发Chat草稿、edit成功失败冲突、run/历史分页/精确结果/Thread、pause/resume/delete/undo；短一行和长列表最后行menu截图、more命中区/Tab/ref/实际键盘、最后项真实点击及editor/history焦点返回 |
| 日记完整旅程 | 日期/list/open/return、当前标记、原delete；长标题删除标签真实单行 |
| Notion正常/异常/边界 | 原快照/今天校验/历史创建、数据库page范围、外链/刷新/连接/权限/partial/Retry-After、网络、A→B→A/hidden/close/logout迟到/午夜；无select/sync/body写入 |
| 视觉/主题/安全区 | 三栏目×1440/1024/430/390×light/dark，加系统；normal/hover/selected/focus、实际alpha/opaque对比、唯一wrapper radius/shadow、tabs顶/section底接缝、内部无卡片；focus/tooltip/menu不裁切 |
| 浮空纸片真实几何 | harness必须从workspace外边界测安全区，不能继续query section或void expected；desktop side36/bottom56、中幅20/36、小幅16/28px（16px root；按实际rem复核）；窄屏滚到底保留shadow和圆角完整截图 |
| 静态/文档/资源 | Luna实际tsc/lint/必要build、Markdown inventory/links、Mermaid、历史byte hash/diff check；精确命令/退出码/首次失败与修复复测；只清理本轮自建端口/副本 |

原完整三spec继续：`calendar-right-panel-tabs.spec.ts`、`scheduled-task-calendar.spec.ts`、`calendar-auth-context.spec.ts`。新增高度/menu实际证据不能代替全旅程；20261006的48pass不能当本轮回执。技术验证与真实业务/模型验收分开，本轮不请求真实模型。

## 5. 当前交接

设计读取、真实组件/Token/harness搜索、图像复核及文档保存已执行；未执行测试/build、未启动服务，也未修改生产/测试源码。独立评审通过后另行实施与Luna验证，实际命令、失败修复、回归、文档/历史检查和清理按追加回执记录。在代码、必要旅程和收口回执完成前不标记目标完成。


## 6. 实施交接（2026-10-07，实际验证待执行）

Optimized Prompt：按独立评审落实唯一浮空workspace、自然短高/确定上限flex链、顶底角接缝、原窄屏整体scroll与外部shadow安全区；只打开时将原more菜单参与行布局。加强真实wrapper几何与公开DTO完整旅程，保留业务/focus/对比断言，冻结代码交Luna实际验证。

`CalendarPopup.css`修改原定义：desktop definite grid row、workspace auto/max100%及24/20/18px原paper/shadow，scroll wrapper与section min0/shrink，内tabs顶角/section底角；窄屏保留原整体scroll/sticky，外画布bottom36/28px，移除内部尾垫。原more-open wrap display:contents，menu static/grid-column2/-1参与task下方高度。左月历样式和全部状态/接口/文案不变；TSX仅文件头。components folder及README英中同段呈现句已同步。

`calendarHarness.ts`改为实际Calendar边界及calendar/workspace外壳安全区，expected side/bottom真正参与比较；保留旧scroll owner返回合同。actual视觉指标增加外壳角/shadow和内容height/cap，opaque/alpha真实合成方法不变。长task/diary仅公开DTO fixture数据，原业务操作仍调用生产公开URL；没有新业务状态机或test-only生产代码。

原三spec的48旅程和全部业务/焦点/tooltip/对比阈值保留，相关视觉从平面修改为唯一浮空外壳/顶底角。新增四个宽度的自然高度旅程（两主题短/空/长/短往返、切栏/换日、隐藏长panel、原草稿），新增1440/390两个short/long-last-row菜单旅程（两主题、原Tab和首项/End/Escape、真实最后项delete/restore、editor/history焦点返回、命中区/DOM refs和高度收回）。原长内容场景扩展为三栏长内容×四宽度×两主题，保存外壳/滚动/安全区computed及截图。预计原三spec合计54用例，实际以runner枚举/执行为准。

源码冻结后建议Luna先执行新height/menu和原visual/long-content重点，再完整原三spec及必要tsc/lint/隔离build、文档/历史/Mermaid/diff和新端口/副本清理。该建议不是执行回执。本worker未执行任何机械测试/构建或启停服务。本次用户新提出的Notion文本密度和真实今日内容缺失由主任务另行诊断/评审；本布局源码或fixture空状态不作为真实同步故障已修复的证据，整体门禁继续保留。

## 7. 首轮实际失败与最小修复（复测尚待）

Optimized Prompt：根据真实focused日志/trace截图，区分窄屏网格压缩与sticky接缝测量错误；修复根因且不降低安全/对比/焦点/业务断言，交Luna实际复测。

Luna首轮重点8例实际3pass/5fail，见`output/calendar-floating-workspace-20261007/floating-focused-retry.log`与同名trace/results。1024自然高度旅程点击9月29日，被右section-heading拦截并120秒超时；430/390真实外壳bottomGap分别0.484/0.281px，小于27px下限；390菜单0.031px附近同样失败；长三栏滚动paperJoin1453px大于1px。日志和首次截图保留，未据此宣称整体完成。

读取trace截图确认1024月历纸片只包到第19日，后两行真实溢出并被下方workspace盖住；390截图右底角与阴影在画布底部被截。分类为CSS缺陷：窄屏恢复implicit auto grid rows，而确定viewport高度及子项min-height0允许轨道缩小，内容从实际paper盒子溢出，底部padding并不能保护超出grid item的实际内容。最小修复在原<=64rem Calendar声明`grid-auto-rows:max-content;align-content:start`，内容轨道按自然高度、只Calendar原owner滚动。桌面原确定row/max cap、左月历样式、menu/ref/API/状态不变。

长列表trace截图则显示原sticky tabs已移到Calendar视口顶端，panel自然起点随整体scroll移出视口；两者的getBoundingClientRect距离不是自然布局接缝。分类为harness测量缺陷：helper暂将原Calendar scrollTop设0测实际自然seam并finally恢复，不sleep或forceclick；继续记录visualPaperJoin，并新增sticky实际位置与预期top、两纸片gap及月份最后行距paper底padding断言。纸底/圆角/实际外壳side/bottom阈值、真实末行点击和alpha/焦点阈值全部保持。

此次修复影响窄屏三栏短/空/长、动态换日/切栏、末行menu与所有滚动底部场景。需先复测原focused8例，随后原三spec完整54例与必要静态/隔离build；新CSS使前一build不能当修复通过证据。机械命令由Luna执行；本worker仅读取已有回执/截图与改源码。现行正式视觉规则仍要求自然高度、月份保留和shadow安全区，此修复落实已评审规则，不追加业务或菜单合同。


## 8. sticky测量收口与冻结副本实际回归

focused修复复测实际7pass/1fail；1024月份点击遮挡、窄屏底部安全空间、自然接缝和末行menu前述失败已通过。余下长三栏sticky差值68px来自helper把滚动内容区起点当Calendar边界：原Calendar padding-top=4.25rem（16px root时68px），CSS tabs top=0。helper按实际scrollport内容起点 `layout.top + paddingTop + tabs.top`，并以workspace自然起点及底部限制clamp计算预期；仍比较实际sticky top差值<=1px，未放宽合同或修改生产sticky样式。首次失败与`floating-focused-repair*`回执保留。

Luna随后采用明确冻结的生产/测试源码副本，完整三spec实跑 **54 passed (1.9m)，exit0**，见`output/calendar-floating-workspace-20261007/full-regression-frozen.log`及`.exit.log`。前一共享测试路径受源码转入Notion新阶段影响，中断exit130，属于harness冻结前置问题，不作为通过/失败业务结论；独立冻结copy最终54/54为本布局回执。新增Notion版本发现/文案生产代码不在这份54源码中，不能借此证明新Notion前端通过。

| 已实际执行检查 | 退出码/关键输出 | 回执 |
| --- | --- | --- |
| 冻结副本三spec完整Playwright（精确命令待runner补充） | 0；54 passed (1.9m) | `full-regression-frozen.log` / `.exit.log` |
| `corepack pnpm exec tsc --noEmit --incremental false`，cwd为本轮`frontend-build` | 0 | `frozen-tsc.command.log` / `.exit.log` / `.log` |
| `corepack pnpm exec eslint app/_dream/components/CalendarPopup.tsx app/_dream/components/CalendarNotionPanel.tsx app/_dream/api/notionTodayApi.ts e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts e2e/fixtures/calendarHarness.ts`，同cwd | 0 | `frozen-eslint.command.log` / `.exit.log` / `.log` |
| `corepack pnpm run build`，同cwd，窄屏CSS修复后的build | 0；Next compiled successfully 15.0s、静态页3/3 | `repair-build.command.log` / `.exit.log` / `.keyoutput.log` |

以上均为公开生产入口+真实DTO的隔离技术验证，无真实账户/模型或数据库写入。布局54旅程与该源码静态/build已通过；当前PRD/正式稿之后还含新Notion增量，最终Markdown清单/引用/Mermaid/历史hash/diff check和自建端口/副本清理等待新阶段统一实际执行。用户正常5173/8765不清理，20261006和本轮首次失败证据保留。整体异步同步/Notion门禁尚未闭合，不标记项目目标完成。
