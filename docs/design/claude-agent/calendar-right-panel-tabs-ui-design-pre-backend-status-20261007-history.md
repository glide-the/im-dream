<!-- [Sync] 2026-10-07: 前端新增9及完整63技术旅程、freshbuild/tsc/focusedESLint实际通过；正常新UIharness限制与后端独立门禁保留，当前文档/清理待回执。 -->
<!-- [Sync] 2026-10-07: 同步发现/简约文案独立评审通过且前端源码冻结待新63实际验证；浮空冻结副本54通过，完整历史不变。 -->
<!-- [Sync] 2026-10-07: 独立评审修正一次total、updatedAt强上下文失效及observed/loaded/verification分别去重；最新background成功事实同步，仍待复核。 -->
<!-- [Input] 当前连接器同步策略、公开 DTO、Calendar 快照读取与2026-10-07正常服务观察。 -->
<!-- [Output] 可见面板版本发现、极简正文及跨进程同步恢复能力缺口的待评审合同。 -->
<!-- [Pos] Calendar 同步发现增量设计证据；正文合同归现行 PRD/正式稿。 -->
<!-- [Sync] 2026-10-07: 仅设计与源码诊断，尚未实施或验收；浮空修复另行执行。 -->
<!-- [Input] Calendar PRD、现有索引/同步/权限及UI v2.pdf，用户2026-10-07右侧浮空外壳/自然高度修正。 -->
<!-- [Output] 原快照/页签业务图及右侧唯一浮空外壳、内部留白、CSS自然高度/菜单与验收规格。 -->
<!-- [Pos] 正式交互设计正文；技能证据不替代业务图。 -->
<!-- [Sync] 2026-10-06: 取代 Search 每次扫描及非今天禁读；保存此前完整正文。 -->
<!-- [Sync] 2026-10-06: 明确已选数据库行的同步、索引持久化及旧索引恢复链路。 -->
<!-- [Sync] 2026-10-06: 连续浅纸、留白/文字层级及原响应式滚动已按独立评审落地，实际回执归本轮 exec；原三幅业务图保留。 -->
<!-- [Sync] 2026-10-06: 日记删除标签不收缩/不折行，保留原字号和命中区；实际渲染行矩形纳入视觉回归。 -->
<!-- [Sync] 2026-10-07: 保存修正前完整原文；单一圆角浮空workspace、自然高度与短高菜单方案待独立评审，原3幅业务图不变。 -->
<!-- [Sync] 2026-10-07: 独立评审通过且现有CSS落实外壳/高度/menu；实际验证待Luna，业务3图保留。 -->
# 日历右侧页签与 Notion 日期文档交互设计

## 1. 背景与问题

[现行 PRD](../../prd/calendar/calendar-right-panel-tabs-prd.md)按用户要求改为连接器快照优先，解决每次全量 Search 的长时间等待，并支持所选历史日期创建文档。此前交互细节完整保存在[历史稿](./calendar-right-panel-tabs-ui-design-pre-snapshot-20261006-history.md)，其 Search/非今天禁读规则已被取代。

用户先要求符合 [UI Design v2.pdf](../../prd/Ink%20%26%20Memory%20UI%20Design%20v2.pdf) 第5页 §5.4 的少面板、多留白。2026-10-07进一步明确：右侧外层仍为圆角浮空纸片，只有内部简约留白，左右不必等高。本稿据此修正2026-10-06平面外壳规则；[修正前完整原文](./calendar-right-panel-tabs-ui-design-pre-floating-20261007-history.md)按字节保存，[更早视觉前文](./calendar-right-panel-tabs-ui-design-pre-borderless-20261006-history.md)及当时评审/回执保留。浮空阶段不改变原3幅业务图。本次同步发现增量更新业务图，前文完整保存在[pre-sync历史](./calendar-right-panel-tabs-ui-design-pre-sync-20261007-history.md)。

## 2. 目标与边界

互斥页签、任务/日记/Chat 导航保持既有实现。Calendar 只消费当前选择与索引交集，不增加配置入口。历史只读创建日；今天读取创建和最近编辑，先显示快照，仅校验快照当天更新项。既有同步更新索引，新页面发现仍属于连接器同步，不承诺全集或历史编辑事件。

视觉仅修正现有 `CalendarPopup.css` 的右侧 workspace外壳/高度及最后行菜单的布局空间，保留已实现内部留白。复用React DOM、Tokens、字体/图标/断点和状态owner；不改左月历CSS尺寸、原编辑/历史Modal、API/权限/缓存/文案，不新增组件、框架或测量JS。2026-10-06[评审](../../exec/calendar-borderless-ui-design-review-20261006.md)和[回执](../../exec/calendar-borderless-ui-20261006.md)仅证明当时范围；本次[影响与门禁](../../exec/calendar-floating-workspace-20261007.md)记录新规格，[本轮独立评审已通过](../../exec/calendar-floating-workspace-design-review-20261007.md)，现有CSS源码已实施，**浮空冻结副本54/54、tsc/ESLint/build已实际通过；新Notion前端完整63和freshbuild/tsc/focusedESLint已实际通过；最终当前文档/清理仍待回执**。

## 3. 概念与规则

快照版本和 `fetched_at` 表达最近成功同步，`observedAt` 为当前投影时间，不能混用。同步时间留在DTO供诊断，不在正常清单常驻；校验/恢复状态按必要性呈现。`createdOnDate/editedOnDate` 使用上游原始时间与所选日区间判断，缺字段为 null，缺标题用未命名。旧字段 `last_edited` 保留 Runtime 兼容，日历不从含糊别名或本地 updatedAt 筛选。

公开生产入口（2026-10-06 实现，技术验证见回执）：`GET /api/connectors/{connector_id}/notion/documents?date_key=...`。首次返回快照；同入口 `validate_remote=true&snapshot_version=...` 校验，仅由服务器索引选出今天更新项。旧 `/notion/today` 作为同一处理函数兼容路由，不保留 Search 业务分支。返回 coverage=connector_snapshot，snapshotVersion/snapshotFetchedAt、todayKey、verificationState（not_required/pending/complete/partial）、items/counts/partialReasons/retryAfter。无快照为 partial + snapshot_unavailable，缺字段为 metadata_missing，不是正常空列表。

第一次读无需远程 API 日期配置；第二阶段使用 `INK_NOTION_TODAY_API_VERSION`（现有名称保持）明确合同，经实际 CLI 请求头核对 2026-03-11。`NotionOperationClient.get_page_metadata` 仅新增元数据读取，仅调用 v1/pages/{id}，禁止 Markdown/blocks。校验 ID 与请求 ID 匹配，异步期间再核对归属/授权/凭证/索引版本和日期时区。上游归档/删除/拒绝访问的页面剔除；401 清空；临时错误保留同上下文结果并标记未完成，Retry-After 期间刷新禁用。URL 使用服务器精确 HTTPS host 白名单，默认包含官方 page.url 的 app.notion.com（见[Notion Page 文档](https://developers.notion.com/reference/page)），不开放任意子域、userinfo 或异常端口。只读结果不发布快照、修改 Admin、同步或扩大正文权限。metadata-only GET（包括既有同步新增的独立页面读取）统一要求服务器显式 API 日期，缺失时 fail closed，同步失败保留 LKG。整次校验复用现有 INK_NOTION_OPERATION_TIMEOUT_SECONDS 预算；429 停止后续调用。初次列表可同时 partial 与 pending，仍展示实际已知行。409 的 NOTION_CONTEXT_CHANGED（归属/选择/凭证）必须清空旧列表；NOTION_SNAPSHOT_CHANGED（版本）停止校验并提示刷新；NOTION_DATE_CONTEXT_CHANGED（午夜/时区）重新投影所选日期，不能提交旧校验。

## 4. 页面与交互

继续使用现有 paper/surface/text tokens、App 字体、IconFile/NotionMark。选中页签显示圆角浅底、图标及名称，未选中透明图标且保留可访问名称和 hover/focus tooltip。tablist 与 panel 关联、visible focus 2px outline 与现有 inset -3px、手动键盘激活；不重写任务状态机。页面骨架由 PRD 正文直接提供。

### 4.1 外壳、内部与 CSS 映射

| selector | 具体规格 | 边界与状态 |
| --- | --- | --- |
| `.calendar-popup` / `__calendar` | 桌面沿用原确定height/padding，两列；仅将desktop grid row明确为`minmax(0,1fr)`以提供可解析上限，左月历原height/尺寸/圆角/shadow保持 | <=64rem还原原自动grid rows与整体滚动，不强制两个区域等高 |
| `__workspace` | 唯一右侧opaque `--color-bg-paper`，border0/gap0/overflow visible/box-sizing border-box；height auto、align-self start、max-height100%；radius24px、shadow`0 8px 18px var(--color-shadow-soft), 0 18px 36px var(--color-shadow-medium)`（复用原左纸面值） | 不设固定大min-height；不使用outer overflow hidden/clip、contain paint、mask或transform剪掉focus/tooltip/menu；未选tab有确定纸底 |
| `__workspace-scroll` / 直接`__section` | scroll wrapper为column flex、`flex:0 1 auto; min-height:0`；active section也`flex:0 1 auto; min-height:0; height:auto; overflow:auto`，只它承担普通长列表桌面滚动 | 旧height100%两处移除，短/空自然结束；max-height由确定grid area传给workspace，再通过flex shrink分配减去tabs，不写固定tabs高度；hidden display none原规则保留 |
| `__tabs` / `__section` | 同色opaque paper，内部border/shadow0；tabs仅顶部两角、section仅底部两角继承workspace半径，接缝直角/gap0 | 圆角只完成同一外壳绘制，不是两个独立卡片；sticky时tabs保有opaque背景；不新增容器 |
| 内部标题、普通行、RESULT | 2026-10-06已实现留白/字号/字重、透明行、无装饰线/静态阴影保持；tabs/heading/body横向1.5rem，<=40rem1rem | 原安排输入、按钮、状态、当前标记与日记delete `flex:0 0 auto; nowrap`不变；RESULT精确消息原内层scroll保留 |
| `__more-wrap:has(__more-menu)` / `__more-menu`（本轮已通过独立裁决） | menu打开时wrap `display:contents`，同一个menu改position static、grid-column2/-1、justify-self end、width max-content/max-width100%、margin-top .25rem；原功能菜单border/shadow/按钮字号/命中区保留 | menu参与原task下方实际高度，关闭不留空间；不把菜单Portal迁出或复制内容，不加菜单状态/高度常量；DOM结构与refs/contains、原键盘和操作保持 |
| <=64rem（包括1024px） | workspace radius20px，shadow`0 6px 14px soft, 0 10px 20px medium`；height auto/max-height none；scroll wrapper flex none/display block/padding-bottom0；section height auto/overflow visible | 原Calendar整体overflow auto、tabs sticky top0；`.calendar-popup`画布padding-bottom2.25rem（36px），side沿用1.25rem（20px），保障外壳阴影末端 |
| <=40rem（430/390px） | workspace radius18px，shadow`0 4px 10px soft, 0 8px 16px medium`；同样自然高度/整体滚动 | 原画布side1rem（16px），padding-bottom1.75rem（28px）；不缩小左月历或原外层Modal，不以workspace-scroll尾部垫片隔开底角 |

右侧24/20/18px半径及shadow值来自既有左paper断点，不添加主题色常量。可用仅组件内`--calendar-popup-paper-radius`统一workspace/tabs/section角值，仍由现有CSS断点所有，不扩展通用Token系统。

### 4.2 自然高度与滚动传递

桌面Modal和Calendar当前确定高度、原2.25rem侧边/3.5rem底部留白保持。右workspace height auto、max-height100%解析到确定grid row，内部scroll wrapper与section允许min-height0/flex-shrink1：短内容按max-content实际高度结束，超过可用高度才收缩active section，tabs仍在其滚动范围外。正文直接给出关键CSS片段；本轮已按通过评审的规格修改原定义，冻结副本实际高度/menu与完整54旅程已通过；新Notion增量后的完整回归另行执行：

```css
.calendar-popup { grid-template-rows: minmax(0, 1fr); }
.calendar-popup__workspace {
  --calendar-popup-paper-radius: 24px;
  box-sizing: border-box; height: auto; max-height: 100%;
  align-self: start; min-height: 0; gap: 0; overflow: visible;
  border: 0; border-radius: var(--calendar-popup-paper-radius);
  background: var(--color-bg-paper);
  box-shadow: 0 8px 18px var(--color-shadow-soft), 0 18px 36px var(--color-shadow-medium);
}
.calendar-popup__workspace-scroll { display: flex; flex-direction: column; flex: 0 1 auto; min-height: 0; }
.calendar-popup__workspace-scroll > .calendar-popup__section { flex: 0 1 auto; min-height: 0; height: auto; overflow: auto; }
.calendar-popup__tabs { border-radius: var(--calendar-popup-paper-radius) var(--calendar-popup-paper-radius) 0 0; }
.calendar-popup__section { border-radius: 0 0 var(--calendar-popup-paper-radius) var(--calendar-popup-paper-radius); }
.calendar-popup__more-wrap:has(.calendar-popup__more-menu) { display: contents; }
.calendar-popup__more-menu { position: static; grid-column: 2 / -1; justify-self: end; width: max-content; max-width: 100%; margin-top: .25rem; }
@media (max-width: 64rem) {
  .calendar-popup { grid-template-rows: none; padding-bottom: 2.25rem; }
  .calendar-popup__workspace {
    --calendar-popup-paper-radius: 20px; height: auto; max-height: none;
    box-shadow: 0 6px 14px var(--color-shadow-soft), 0 10px 20px var(--color-shadow-medium);
  }
  .calendar-popup__workspace-scroll { display: block; flex: none; padding-bottom: 0; }
  .calendar-popup__workspace-scroll > .calendar-popup__section { height: auto; overflow: visible; }
}
@media (max-width: 40rem) {
  .calendar-popup { padding-bottom: 1.75rem; }
  .calendar-popup__workspace {
    --calendar-popup-paper-radius: 18px;
    box-shadow: 0 4px 10px var(--color-shadow-soft), 0 8px 16px var(--color-shadow-medium);
  }
}
```

CSS以修改原定义和两个现有media块实施，片段不是额外叠覆整套样式；不改左月历selector。需实际验证auto/max-height及双层flex的收缩链：空/短明显低于原calendar，长内容workspace不超grid可用范围、section `scrollHeight>clientHeight`；切长→短必须重新自然收回，不能只读取computed height:auto作为成功。菜单打开会使task参与实际高度，短paper随内容增高直到上限；达到上限时原section滚动允许最后项进入视口并操作。

<=64rem沿用整个Calendar滚动，workspace取消max-height，section overflow visible，不增加外壳或列表scroll owner；tabs sticky于原Calendar且受workspace边界约束。末尾必须能滚到右外壳bottom及完整shadow留白。桌面图形测量使用`.calendar-popup`边界与workspace外壳，窄屏滚到底时测calendar/workspace两个外壳相对Calendar边界，不能拿section内边界冒充浮空纸片。既有`readFloatingPaperSafety`需要换成真实workspace测量，`expectFloatingPaperSafety(expected)`必须比较实际side/bottom而非`void expected`：桌面36/56px、1024为20/36px、430/390为16/28px（16px root；其他root按实际computed rem值）。shadow仍允许blur衰减，以实际padding边界和截图检验不被画布裁切。

同日scroll refs、安排输入和LIST/RESULT保持；hidden/inert面板不参与高度、不产生新请求/轮询。异步snapshot/loading/校验、日期变化及错误/恢复只由已有状态触发布局，旧响应guard不变，不增加resize observer/测量JS或高度动画。RESULT精确消息原内层scroll和编辑/历史Modal原owner是既有内容子区，不因外壳改造新增其他滚动层。

### 4.3 主题、焦点、菜单和恢复

沿用opaque paper、alpha hover/active、primary/secondary、focus及soft/medium shadow Tokens，浅/深/系统主题均使用actual合成背景测对比；透明tab不能落在遮罩上。selected文字4.5、图标/focus3、原tooltip/action文字4.5阈值不降低。选中浅底、未选hover和visible outline、原鼠标/键盘tooltip保持，不添加缩放/漂浮/高度动画。

more菜单仍由当前task的`moreOpen/moreMenuRef/moreButtonRef/onLayerChange`所有；源码已有ArrowUp/Down/Home/End与首个可用项聚焦。in-flow只改变盒子布局，需验证DOM/ref包含关系、more原命中区、Tab顺序、原菜单键盘和Calendar Escape处理、tab切换关闭及编辑/历史返回焦点；现有outside点击语义以源码/原旅程为准，不新增不存在的关闭规则。短/长最后一行逐项实际点击（可使用公开DTO fixture恢复）和状态截图必须证明功能可达，不仅比较menu rectangle。用户可以按既有操作返回LIST或关闭menu，纸片自然收回；错误、partial、刷新、登录/登出或换日仍保持原恢复路径。原3幅业务时序/状态图说明API和owner，本轮CSS排版不改变图逻辑。

### 4.4 本次视觉与完整回归验收

| 场景 | 实际证据与必要断言 |
| --- | --- |
| 三栏目×1440/1024/430/390×浅/深，含系统 | workspace为唯一圆角shadow纸片；tabs顶角/section底角接缝无缺口，内部无独立border/shadow；actual alpha对比、focus/tooltip与操作不裁切，左月历尺寸保持 |
| 短/空/加载/失败/partial | 实际wrapper短高随可见内容，内部恢复入口可点击；无固定大min-height；隐藏长面板不撑高 |
| 短→长→短、切tabs/换日、刷新加载→命中/空、LIST↔RESULT | right实际高度更新/收回、长达到可用上限；桌面只原active section列表滚动，窄屏只原Calendar整体滚动；草稿/scroll/结果/焦点owner保留 |
| 一行任务和长列表最后行menu | 打开时in-flow只增当前task实际高度；原more命中区与tab顺序、refs、实际支持键盘、Escape/切栏关闭、菜单最后项实际点击与editor/history焦点返回；功能menu可保留border/shadow |
| 外壳shadow安全区 | `readFloatingPaperSafety`基于workspace外边界，真实computed padding和expected side/bottom实际比较；窄屏滚到底的底角/阴影完整截图，不将section内距计作外部安全留白 |
| 原三份完整E2E | 保留Calendar、所有task/diary、Notion正常/异常/并发/API无写完整旅程及首帧focus-ready前置；新增高度/menu场景不替代这些旅程 |
| 代码/文档/资源 | Luna实际执行必要TypeScript/ESLint/build、Markdown inventory/links、Mermaid、diff check；只清理新命名端口/副本，保留用户服务；技术不冒充真实账户验收 |

本轮独立评审已明确批准外壳、高度flex链、sticky阴影与in-flow菜单方案，现有CSS已落实。2026-10-06回执只属于旧平面规则；本次不能提前宣称新代码或自动化完成。业务骨架直接在PRD正文，正常/异常/状态图继续在本稿下面。

### 4.5 日期文档正文层级（源码已实施，隔离技术旅程63通过）

`CalendarNotionPanel`复用`__section-heading/__section-body/__notion-group/__notion-row/__notion-meta`与现有Tokens。正常层级为“Notion 文档 / 一次短total（2篇） / 刷新”→非空“当日创建”“当日编辑”→文档标题和上游时间，组名不再重复计数；双命中仍在创建组显示创建/编辑两时间标识。标题旁只保留一次服务端counts.total的短数量，删除组计数、重复total、完整snapshotFetchedAt、coverage技术句、正常空组与第二个Open链接，DTO/服务端counts不删除。标题是唯一新标签外链，使用原openAria完整名称及安全URL规则；URL无效时仍显示标题与可理解反馈。

首次无列表显示“正在读取文档…”/“Loading documents…”；已有列表的刷新或后台校验仅Refresh按钮忙状态与aria-busy，不增加常驻解释段，不夺焦点或重复live播报。数量正常为“{{count}}篇”/“{{count}} documents”，partial为“已知{{count}}篇”/“{{count}} known documents”；只有标题旁一次数量。partial提示简短“部分文档未能读取，请稍后刷新。”/“Some documents are unavailable. Refresh to try again.”；已知0仍是partial，不能使用正常空文案。无候选/当日无命中原业务判断保持，正常空仅一条消息，不渲染空组。

同步恢复最多一条原因与原Settings入口：syncing“连接器同步尚未完成”/“Connector sync has not completed”；error“连接器同步失败”/“Connector sync failed”；disabled“自动同步已关闭”/“Automatic sync is off”。缺快照/字段沿用前往同步提示。仅这些状态对当前结果有影响时展示（syncing在空/partial时解释缺失；error/disabled说明更新需用户操作），与其他同原因提示去重。入口“管理连接器”/“Manage connector”只导航既有详情；不自动POST sync、不改策略。syncing没有活跃owner证明，不显示确定的实时进度或“稍后一定更新”。用户正常新建的Notion页面仍依赖成功同步进入索引，不能靠前端轮询制造页面。

### 4.6 可见版本检查与请求所有权（源码已实施，隔离技术旅程63通过）

1. `resourceConnectorApi.normalizeConnector`保留现有Admin/public DTO的`current_snapshot_version`为nullable严格字符串；不新建后端API/schema，不使用快照正文、选择缓存或timestamp代版本。`listConnectors(signal)`仍校验连接唯一性及授权状态。
2. `CalendarNotionPanel`现有60秒日期检查timer复用于轻量版本检查；仅active、authenticated且`document.visibilityState=visible`，挂起时不发请求，可见恢复即检查。每轮完成后安排下一轮，date/midnight/Retry-After仍由原定时语义所有，不做setInterval叠请求。规则集中于既有具名技术周期，不新增同步频率产品限制。
3. context为actor、connector ID、日期、IANA时区、授权状态、规范化选择type/ID与connector updatedAt；version单独比较。缺独立auth/scope revision时，不能用同snapshotVersion猜权限没变。**任何updatedAt变化都unknown context，含sync patch，取消旧请求并清空数据再重读**。只有完整ctx相同、loaded成功版本匹配且无待读取失败/409时，才零documents/远程并保留列表/scroll；新版本且完整ctx相同才可保留LKG后台读取。不保证sync status变化必保旧列表，状态/updatedAt必须一起检查。版本字符串不按时间排序。
4. probe采用独立AbortController/generation或共用严格请求owner：取消+提交检查同时绑定上述context及generation。hide/页面隐藏取消probe并停止新阶段；已开始snapshot/verification维持原可结束规则，仅可提交仍一致上下文。close/logout/actor/date/zone/connector变化取消并丢弃旧响应，不允许A→B→A旧代号覆盖。REST读取走公开Cookie/CSRF helper，不绕过身份与Admin归属。
5. `observed`仅记录最新accepted connector检查context/version；`loaded`只在documents成功通过所有提交检查后记录实际context/响应版本。另有读取in-flight键与`needsRead`，失败/409不推进loaded；observed未变但needsRead仍在时，下一正常60秒周期或显式刷新可重读，不永久抑制同版本恢复。成功才清needsRead，cancel/旧响应不当成功。可保留LKG与是否需要重读是两个维度，LKG仅完整同context允许展示。显式refreshnonce与自动读代号分别管理。
6. verification的in-flight键、完成键与loaded/observed独立：完成键仅成功complete/not_required才推进，pending/partial/失败不伪装完成。临时校验失败清in-flight并停在反馈状态，按原显式Refresh恢复，不由effect立刻再次校验；新版本/上下文或显式refreshnonce仍可进入新校验。409 NOTION_SNAPSHOT_CHANGED停止旧校验、标needsRead，下一**正常60秒周期**或显式刷新再读，不因错误state变化立即probe/read/verify。只服务器索引的今天更新ID可远程校验，历史零remote，不执行Search/body/select/sync/config。临时读取/检查失败保留完整同context允许LKG；Retry-After冷却同时抑制probe/read/verify，下一周期须满足冷却结束，或用户到期Refresh。401/归属/权限错误按原分类清空，RESOURCE_CONNECTORS_CHANGED_EVENT原失效路径保留。
7. 已有同日scroll/结果和安排输入owner保留；Notion数据/scroll仅完整同context时保留，不unmount重新建面板、不对该安全后台刷新自动scrollToTop；unknown context则按原安全清空规则，不保证保留。新增行变化只按原DOM自然布局。隐藏面板不参与新查询；document隐藏恢复可见的检查不等同用户显式Refresh。

### 4.7 后端中断恢复门禁（尚阻塞，不实施shortcut）

`sync_policy_is_due`当前对persisted syncing永久False；`_SYNC_LOCKS[(actor,connector)]`只为进程内锁。`INK_NOTION_OPERATION_TIMEOUT_SECONDS`限制每次CLI（默认30秒，合法<=300秒），分页数量没有整次同步最长时长；`INK_NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS`只是扫描周期，不是租约。取消处理可写SYNC_CANCELLED，但hard kill/进程丢失无法保证finally落盘。Admin现有patch/saveSnapshot各事务FOR UPDATE不能覆盖整次远程构建，没有owner/expected-attempt/CAS/fencing。因此age、过期next_sync、本机无锁或PID启动晚于attempt均不能证明其他进程已停止。

安全自动恢复需Admin明确提供原子claim、唯一owner+递增fence、服务器租约/续租规则及publish/finish校验；过期owner的迟到快照与状态提交必须拒绝。租约预算/心跳来自服务器合同，不能临时以每operation timeout乘任意常数估算。需要schema才由Admin Drizzle前向migration/capability管理，Dream只消费已发布capability。**此依赖当前缺失，当前稿不批准自动清syncing或抢占**。现有公开“管理已挂载来源 → 立即同步”仍为用户可操作恢复路径，本次首次立即同步HTTP502未推进快照；随后既有后台重试于本地今05:48成功，candidate319→320、counts created1/edited1/total2，正常Calendar今日文档已可见，详见本轮exec§8。这证明本账户当次恢复，不证明跨进程中断自动接管能力闭合。

## 5. 正常业务时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as CalendarNotionPanel
    participant C as connector router
    participant R as documents router
    participant A as Actor facade
    participant S as NotionSnapshotStore
    participant W as NotionSnapshotSyncWorker
    participant N as NotionOperationClient
    U->>P: 选择日期并进入 Notion
    P->>C: GET connectors
    C-->>P: 授权/选择/版本/syncPolicy
    P->>R: GET documents(date_key)
    R->>A: 身份/归属/用户时区
    A->>S: load_current(actor, connector)
    S-->>A: 版本/轻量索引
    A-->>P: 与选择求交后的日期清单
    P-->>U: 标题旁一次total/非空组/标题链接/上游时间
    alt 今天有更新项且面板可见
        P->>R: GET documents(validate_remote, snapshot_version)
        R->>A: 同上下文/版本待校验ID
        A->>N: 仅今天更新ID的metadata GET
        N-->>A: 创建/编辑/标题/URL
        A-->>P: 提交检查后同版本结果
    end
    W->>A: 既有策略到期sync
    A->>N: 已选数据库分页/独立页元数据
    N-->>A: 范围内索引
    A->>S: publish_current
    Note over P,C: 可见检查已实施；实际63技术旅程见exec
    loop 仅active且页面可见的检查周期
        P->>C: GET connectors
        C-->>P: 当前context/版本/syncPolicy
        alt 完整context与成功loaded版本相同且无needsRead
            P->>P: 保留列表/scroll，不读documents
        else 新版本或unknown context或待读取失败
            P->>P: unknown context先清空旧数据
            P->>R: GET documents(date_key)
            R-->>P: 当前上下文新投影
            P->>P: 成功提交才推进loaded并清needsRead
            P-->>U: 更新清单，必要时原规则校验
        end
    end
    U->>P: 打开文档标题
    P-->>U: 安全HTTPS外链新标签
```


## 6. 异常与恢复时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as CalendarNotionPanel
    participant C as connector router
    participant A as Actor facade
    participant N as NotionOperationClient
    participant W as NotionSnapshotSyncWorker
    P->>A: 读取当前快照
    alt 无快照或缺时间字段
        A-->>P: partial/实际已知数量
        P-->>U: 一条恢复原因与管理连接器
        U->>C: 既有Settings公开立即同步
        C->>A: sync
        alt 同步成功
            A-->>C: 新版本/成功状态
            P->>C: 可见检查发现新版本
            P->>A: 重新读取日期快照
        else 同步失败
            A-->>C: 安全错误，不推进成功版本
            P-->>U: 保留允许结果及失败恢复入口
        end
    else 有今天更新项
        P->>A: 绑定版本校验
        A->>N: metadata GET
        alt 授权失效
            N-->>A: 401
            A-->>P: NOTION_AUTH_EXPIRED
            P-->>U: 清空旧清单/管理连接器
        else 页面拒绝或删除
            N-->>A: 403/404
            A-->>P: 剔除行/partial实际已知数量
        else 网络或限流
            N-->>A: safe code/Retry-After
            A-->>P: 同上下文partial
            P-->>U: 保留结果，冷却后可刷新
        else context/版本/日期冲突
            A-->>P: 409
            P->>P: 丢弃旧响应，按原context规则清空
            P->>P: needsRead置true，loaded不推进
            P->>C: 下一正常60秒周期或显式刷新
        end
    end
    W->>W: persisted syncing跳过到期判断
    Note over W,A: 缺跨进程owner/lease/fencing，自动接管尚阻塞
    Note over P,C: 检查失败保留同context允许结果；认证失败清空
```


## 7. 交互状态图

```mermaid
stateDiagram-v2
    [*] --> ReadingSnapshot: 可见且登录
    ReadingSnapshot --> SnapshotShown: 有快照
    ReadingSnapshot --> NeedsSync: 无快照
    ReadingSnapshot --> Partial: 字段缺失
    ReadingSnapshot --> NeedsConnection: 未连接或授权未完成
    SnapshotShown --> Validating: 今天更新项且可见
    SnapshotShown --> Ready: 历史或无更新项
    Validating --> Ready: 校验成功
    Validating --> Partial: 临时失败或页面拒绝
    Validating --> NeedsConnection: 授权失效并清空
    Ready --> CheckingVersion: 可见周期或返回
    Partial --> CheckingVersion: 可见周期且冷却结束
    NeedsSync --> CheckingVersion: 管理后返回
    CheckingVersion --> NeedsSync: 完整context与loaded相同无快照且无needsRead
    CheckingVersion --> Ready: 完整context与loaded相同且原完整结果无needsRead
    CheckingVersion --> Partial: 完整context与loaded相同无needsRead且原partial或临时检查失败
    CheckingVersion --> ReadingSnapshot: 新版本或unknown context或needsRead
    ReadingSnapshot --> Partial: 临时失败且允许LKG不推进loaded
    ReadingSnapshot --> NeedsRetry: 失败无允许LKG不推进loaded
    NeedsRetry --> CheckingVersion: 下一正常60秒周期且冷却结束或显式刷新
    CheckingVersion --> NeedsConnection: 授权失效并清空
    Ready --> ReadingSnapshot: 显式刷新或换日或午夜
    Partial --> ReadingSnapshot: 显式刷新且冷却结束
    NeedsConnection --> ReadingSnapshot: 连接后返回
    Ready --> Hidden: 切走或页面隐藏并停止检查
    Partial --> Hidden: 切走或页面隐藏并停止检查
    Hidden --> CheckingVersion: 恢复可见并保留同context局部scroll
    ReadingSnapshot --> [*]: 关闭或登出并取消
    Validating --> [*]: 关闭或登出并取消
    CheckingVersion --> [*]: 关闭或登出并取消
```


## 8. 影响、接口与验收

执行模块：router 校验 OAuth/归属及偏好；facade 读取私有索引并做前后提交检查；today.py 负责日期/投影/只校验当天更新项；operations 提供 metadata-only GET；sync 保留上游字段并刷新选中独立页面元数据；前端保留快照再校验。Admin JSON DTO 可承载新增字段，无共享 schema 依赖。

数据库选择沿用 `resource_type=notion_database`：`select_resources` 保存选择后调用 `sync`，`build_canonical_snapshot` 对选中 data source 执行 `query_database` 全页查询，数据库 page 行同时进入 `index` 与对应 `database_pages`。`filter_snapshot_for_connector` 用仍选中的数据库关系允许这些页面进入日历候选，不需要把每行另存为独立选择。重启不重建持久化索引；缺原始时间的旧索引按异常图返回 partial，用户从“管理已挂载来源 → 立即同步”恢复，再返回日历刷新。测试必须经过实际 builder 和持久化，不能仅用预置快照证明数据库选择链路。

测试矩阵按 PRD §6；额外覆盖旧快照字段缺失、规范化 ID 去重、remote ID 不匹配、同步版本变化、取消选择、已有列表在慢校验期间可用，以及历史请求含 validate_remote 仍零远程调用。任务和日记全旅程继续调用公开生产入口及真实 DTO。隔离技术结果与真实账户业务验收分开报告。

[影响评估、独立评审与测试回执](../../exec/notion-calendar-snapshot-repair-20261006.md)记录门禁与实际命令；阶段文档不能宣称实现或验证完成。

本次外壳/高度的[影响、设计门禁及待执行矩阵](../../exec/calendar-floating-workspace-20261007.md)和[四阶段增量过程](./calendar-floating-workspace-workflow-20261007/README.md)仅作修正证据；本稿正文规格和原业务图为正式交付。

本次[同步发现/文案影响与交接](../../exec/notion-calendar-sync-refresh-20261007.md)和[四阶段增量证据](./calendar-sync-refresh-workflow-20261007/README.md)已通过[独立评审](../../exec/notion-calendar-sync-refresh-design-review-20261007.md)，前端源码已实施，最终新增9/完整63隔离技术旅程及freshbuild/tsc/focusedESLint已实际通过，回执见exec§13。首次正常同步502保留，随后后台成功与正常今日UI命中见exec§8；Admin跨进程所有权及后续Dream capability集成另有门禁，前端不实现接管shortcut。正常Chrome新UI诊断harness超时限制见exec§10。
