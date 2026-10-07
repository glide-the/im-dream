<!-- [Input] 现行 Calendar/索引合同、UI Design v2.pdf 第5页及用户2026-10-07外层浮空纸片与内部留白修正。 -->
<!-- [Output] 互斥页签、日期快照及右侧圆角浮空外壳/内部留白/自然高度的产品合同与正文骨架。 -->
<!-- [Pos] calendar 业务现行 PRD；正式业务图归交互设计所有。 -->
<!-- [Sync] 2026-10-06: 用连接器当前索引取代每次 Search；保留此前正文历史。 -->
<!-- [Sync] 2026-10-06: 明确数据库内 page 候选和旧索引显式同步恢复。 -->
<!-- [Sync] 2026-10-06: 右侧改为轻纸底、无装饰边框和卡片阴影，以留白和文字层级分区；改动前全文另存历史。 -->
<!-- [Sync] 2026-10-06: 连续 opaque paper、1024 原堆叠与窄屏外层滚动已按独立评审落地；实际验证及收口回执归本轮 exec。 -->
<!-- [Sync] 2026-10-06: 长日记标题不能挤压删除标签；保留单行操作、原字号及命中区。 -->
<!-- [Sync] 2026-10-07: 保留右侧唯一圆角浮空外壳，内部无卡片；左右不强制等高，完整前文另存历史，新设计待独立评审。 -->
<!-- [Sync] 2026-10-07: 本轮独立评审通过且CSS源码落地；实际高度/menu/全旅程及收口等待Luna回执。 -->
# 日历右侧页签与 Notion 日期文档 PRD

## 1. 背景与问题

右侧采用定时任务、日记、Notion 互斥栏目。此前 Notion 每次打开或刷新都遍历 Search，未使用连接器已存在的索引快照，等待长且限制只能今天。用户明确要求：只有当天更新的文档远程校验，其它从连接器快照获取。此要求取代原 Search 范围及非今天禁读规则。[此前完整正文](./calendar-right-panel-tabs-prd-pre-snapshot-20261006-history.md)保留原文；[首次评审](../../exec/calendar-right-panel-tabs-design-review-20261004.md)为历史证据。

用户先要求右侧符合 [Ink & Memory UI Design v2.pdf](../Ink%20%26%20Memory%20UI%20Design%20v2.pdf) 第5页 §5.4 的简约留白。2026-10-06 将整块右侧做成无圆角/阴影的平面，2026-10-07 用户明确修正：**左右不一定等高，右侧外层仍是圆角浮空纸片，只有容器内部简约留白。** 因此 `calendar-popup__workspace` 保留一层完整纸片，页签/栏目/普通条目不再各套卡片；无装饰边框要求针对内部内容。此次不追加 PDF 通用页面虚线。修正前[完整 PRD](./calendar-right-panel-tabs-prd-pre-floating-20261007-history.md)保存原文；[2026-10-06 无边框调整前全文](./calendar-right-panel-tabs-prd-pre-borderless-20261006-history.md)和既有执行记录不覆盖。

## 2. 目标与边界

保留左月历、原初始日期、三个互斥页签及既有任务、日记、Chat 导航。Notion 从当前 actor、当前连接器已同步索引与当前选择的交集读取。历史日期展示该日创建的文档；今天展示今天创建或最近编辑的文档。快照立即返回并显示，然后仅对快照中上游最近编辑时间在今天区间的页面读取远程元数据校验。日历不运行 Search、同步、选择、正文读取、导入或配置写入。

这不承诺工作区全部、授权全集或 Search 全集。新文档及快照尚未记录的变化由既有连接器手动/自动同步发现。历史日期不展示历史编辑事件：Notion 最新编辑时间不能证明历史某日曾编辑。没有快照或旧索引缺创建时间时明确提示前往连接器同步，不用同步时间、本地 updatedAt 或现在补值。无 schema 变更；复用现有 JSON 索引字段和 Provider。

本轮只修正现有右侧外壳和高度：workspace 唯一持有纸底、圆角与浮空阴影，内部标题/行/RESULT 延续留白，右侧随当前可见内容自然增高，桌面超过可用高度时由原 active section 滚动。左月历沿用原尺寸，不以伸展右侧或缩小左侧实现等高。复用 DOM、状态 owner、图标、Tokens 和断点；原任务编辑/历史 Modal、Notion 权限/日期/快照/校验、文案/API/配置不变。短高最后行菜单的呈现需同步解决：本轮独立评审批准仅在原 menu 打开时使其参与同任务行下方布局，不新增菜单状态、Portal 或测量 JS；CSS已落实，实际验证待回执。

## 3. 概念与规则

- 身份认证、Admin 归属校验、Notion 授权、资源选择、索引同步、日历命中分别判断。授权失效、登出、归属/凭证变化清除旧结果。
- 当前索引由 `NotionSnapshotStore.load_current` 读取；`filter_snapshot_for_connector` 与最新选择求交。只读日历不发布或修改索引，背景同步仍为写入 owner。
- 同步保留上游 `created_time`、`last_edited_time`。选中独立页面通过元数据 GET 更新索引；数据库行来自既有分页 query。索引保持 `pages={}`，不下载正文。
- 服务端使用 actor Admin 偏好的 IANA 时区。所选日零点及次日零点分别转 UTC，采用半开区间，不假定一天恒为 24 小时。非法日期、时区失败，不静默替代。
- 今天按创建优先分组；双命中显示两标识、只计一次。历史只按创建筛选。按对应上游时间降序，再按规范化资源身份稳定排序。缺标题显示“未命名文档”；非法/缺失字段使结果为部分结果，不能伪造正常空清单。
- 初次 GET 返回快照列表、快照版本/同步时间、实际唯一计数和是否需要校验。列表显示后再 GET 校验；服务端从同版本索引决定待校验 ID，客户端不能提供额外资源 ID。只在所选日等于服务端今天时校验 `last_edited_time` 位于今天的记录。历史请求即使带校验参数也不得远程读取。
- 校验沿用明确的服务器 Notion API 日期合同，不依赖浏览器或路径推断；配置缺失使依赖远程元数据的同步和校验 fail closed，快照读取仍可用。API 日期已由 ntn 0.15.1 实际请求头核对为 2026-03-11，部署须采用该配置。
- 校验使用 metadata-only GET，拒绝返回资源 ID 不匹配，删除/归档/403/404 的页面从本次结果移除。401 清除整个旧列表；临时失败/限流保留同上下文快照并标记校验未完成，尊重 Retry-After，不自动重试。
- 请求取消与提交检查同时绑定 actor、connector updated_at、凭证文件身份、日期/时区、索引版本及请求代号。整次校验复用现有 operation timeout 预算，429 停止后续调用。归属/选择/凭证冲突清空旧列表，索引版本冲突停止校验并提示刷新，午夜/时区冲突重新投影所选日期；初次 partial 可同时 pending 并展示已知行。校验期间快照变化返回冲突，不能覆盖新列表；换日、换身份、关闭后的旧响应丢弃。
- 显式刷新重新读取快照，必要时再校验当天更新项。没有日期/上下文变化的切走返回不重新请求。隐藏时不启动第二阶段校验或轮询；已有请求可结束并保存当前上下文结果。
- 跨午夜保留所选日、重新按历史创建规则读取快照，不显示旧今日编辑组。时区变化清空旧上下文并重新读取。
- 外链使用服务器配置的 HTTPS host 白名单，禁止用户信息、异常端口/协议；直接新标签打开，沿用 noreferrer/noopener，无正文编辑器或打开前权限预检。

## 4. 页面骨架

### 4.1 桌面骨架

```text
透明 Calendar 画布                                           [关闭]
╭ 左月历纸片（尺寸/操作不变） ╮    ╭ 右侧唯一浮空 workspace ───────╮
│ 月份导航、日期格、原标记   │    │ [◷ 定时任务]   ▤   N         │
│                          │    │ 栏目标题 / 数量        原操作 │
│                          │    │ 唯一 active section：         │
│                          │    │ 任务 LIST / RESULT、安排输入   │
│                          │    │ 或日记 / Notion 同步/日期组    │
│                          │    │ 透明内容行、留白，无标题横线   │
│                          │    ╰──────────────────────────────╯
│                          │       ↑短/空内容自然结束、保留阴影
╰──────────────────────────╯       不拉满到左月历底边
长内容：右纸片到可用高度上限，tabs留在上方，只有active section滚动。
RESULT精确消息原内层滚动保留；不新增外壳scroll owner。
菜单打开：原task下方右对齐功能menu参与高度；原焦点/操作owner不变。
编辑/历史独立Modal覆盖Calendar，关闭恢复原入口焦点。
```

### 4.2 窄屏骨架（1024 / 430 / 390px）

```text
原Calendar视口与整体滚动                                  [关闭]
╭ 左月历纸片 ─────────────────────────────────────────────╮
│ 保留原窄屏尺寸、月份/日期操作                            │
╰────────────────────────────────────────────────────────╯
                   原两区之间留白
╭ 右侧同一workspace浮空纸片 ───────────────────────────────╮
│ [◷]  ▤  [N Notion]   ← 原sticky tabs，有opaque纸底和顶角 │
│ 栏目标题 / 数量 / 恢复                              刷新│
│ 创建组（今天另有编辑组）                               │
│ 透明文档行、上游时间、外链；无嵌套卡片                 │
╰────────────────────────────────────────────────────────╯
       ↓外壳底角与阴影；原Calendar滚动区末尾有安全留白
短内容自然结束；长内容整体滚动至底部，section不增加独立滚动。
tooltip不因外壳圆角被裁切；功能菜单/原Modal仍可键盘与点击操作。
```

### 4.3 层级与弹窗关系、页签及既有业务

P01 现有日历 Modal 持有月历和右侧栏目；P02 左月历、P03 右侧 workspace 内页签、P04 唯一可见栏目属于同一弹窗；workspace 是唯一右侧浮空外壳，不按栏目增加纸片。任务编辑/历史 Modal 覆盖 P01，保持原 owner、焦点陷阱和关闭后的焦点恢复；Notion 设置入口关闭 Calendar 后进入既有连接器设置页面。

登录首次默认定时任务，未登录默认日记；弹窗中登录保留当前栏目。关闭重开恢复 App 原初始日期及默认栏目。同日切换保留滚动、安排输入、任务 LIST/RESULT 和已读取结果；换日保持栏目、任务回 LIST，原安排草稿保留。隐藏面板不可聚焦、不可读出、不留可见 Portal。编辑/历史 Modal 保留原焦点陷阱与 owner；取消沿用现状，不增加确认。

选中项圆角背景、图标和名称，未选中项图标和完整 accessible name；tooltip 支持鼠标/键盘。tablist/tab/tabpanel 关联、aria-selected、方向键/Home/End 移动焦点，Enter/Space 手动激活。使用项目既有主题、字体、Tokens、图标及窄屏断点。

任务安排和未发送 Chat 草稿、列表、编辑成功/失败/冲突、运行、历史分页、精确结果、Thread、暂停/恢复、删除/撤销由[任务 PRD](../claude-agent/scheduled-task-diary-page-prd.md)保持。日记打开、返回、当前标记、既有删除保持。

### 4.4 右侧浮空外壳、内部留白与高度条件

| 部位/呈现条件 | 呈现规则 | 保留行为与验收 |
| --- | --- | --- |
| workspace 外壳 | 一层 opaque `--color-bg-paper`、原paper圆角与soft/medium双层阴影；border=0、gap=0、overflow visible | tabs和唯一active section属于同一外壳；不新增外壳状态或滚动 |
| tabs / section | 无独立border/shadow；tabs顶角与section底角顺接外壳，其余接缝为直角且无间隔；sticky tabs使用同色opaque纸底 | 未选透明tab有确定纸底；不通过外壳overflow hidden裁切focus/tooltip/menu |
| 短/空/加载/错误内容 | 右侧高度为实际tabs+当前栏目内容，不设置固定大min-height，不拉满左月历 | loading→结果/空/失败、刷新和切栏后高度重新自然排版；恢复动作仍可达 |
| 桌面长内容 | 右侧上限为原Calendar可用内容高度，左月历不动；tabs外置，active section可缩小并滚动 | hidden/inert面板display none，不参与高度，不新增查询或轮询；原滚动refs保留 |
| 任务RESULT | 精确消息原内层scroll及header/footer动作保留，不加装饰分隔线或固定外壳高度 | LIST↔RESULT、同日往返和关闭重开仍由原owner处理 |
| 已打开任务menu | 同一task下方右对齐、参与实际高度，关闭不预留空间；原功能菜单border/shadow保留 | 已通过独立裁决的in-flow呈现；more命中区、DOM/ref、tab顺序、原键盘/关闭/操作及最后项实际点击保持 |
| 标题 / 状态 / 普通条目 | 无标题线、条目框或静态阴影；用原标题字重/字号及间距区分，日记当前项轻active及原文字标记 | 任务/日记/Notion全部内容、数量和原恢复入口不变，删除标签不换行、不缩小字号/命中区 |
| 页签normal/hover/selected/focus | 未选透明图标，hover轻底；selected active浅底圆角图标文字；visible outline和鼠标/键盘tooltip保持 | tablist/tab/tabpanel、手动激活、日记键盘焦点优先tooltip保留；对比按actual纸底合成 |
| 功能输入 / 按钮 / 浮层 | 原主次/危险/禁用/提交边界保留；不把输入/menu/Modal outline统一清零 | 原任务编辑/历史Modal、focus陷阱/恢复和Portal owner不变 |

1440px 沿用两列及左月历的既有确定高度；右 workspace top对齐、height auto、仅max-height受可用高度约束。CSS通过可收缩的workspace-scroll/active section传递上限，不使用内容测量JS或固定菜单预留高度。<=64rem（1024px已堆叠）保留Calendar整体滚动、workspace/section自然高度和tabs sticky；右外壳在所有断点仍存在。<=40rem（430/390px）保留原宽度及左月历，只沿用1rem内部水平padding。桌面保持2.25rem侧边、3.5rem底部原画布留白；<=64rem原画布底部增加2.25rem，<=40rem增加1.75rem，供右外壳底角/阴影在滚动末尾完整显示。取消workspace-scroll旧尾部垫片，留白属于外壳外的Calendar画布。section末尾内距仍保护按钮/焦点。

主题复用 `--color-bg-paper`、hover/active/text/focus及soft/medium shadow Tokens；不新增固定主题色、字体或图标。正式稿 §4.1–4.4 直接给出CSS、圆角接缝和验收。本轮是2026-10-07增量设计，[独立评审已通过](../../exec/calendar-floating-workspace-design-review-20261007.md)，CSS源码已按规则落实，**实际自动化/文档收口待Luna回执**；2026-10-06已执行结果不能证明新外壳/高度方案通过。

## 5. 完整流程与失败恢复

打开日历 → 原默认栏目/日期 → Notion → 登录/连接/归属 → 读取当前选中范围快照 → 所选时区日期筛选、去重计数 → 立即显示同步时间和清单 → 今天且有更新项时读取元数据校验 → 更新同上下文列表 → 直接打开 Notion → 显式刷新或切走返回。

未连接/授权未完成/失效进入 Settings；未选择或无快照/字段缺失提示前往同步。临时校验失败保留允许展示的同上下文快照；校验拒绝访问的资源移除，授权失效清空。冲突提示刷新；没有查询次数或分页实时进度伪装。部分结果的已知 0 不能显示为正常“无文档”。

选择数据库类型时，日期文档的候选是该已选数据库内已同步的 page 行；不要求逐页手动选择。同步把这些页面写入轻量 `index`，`database_pages` 记录页面与已选数据库的关系，日历按当前选择过滤后再按上游时间筛选。旧索引缺少时间字段时，重启服务不会重建索引；在连接器“管理已挂载来源 → 立即同步”后返回日历刷新。同步只更新元数据，不批量读取正文。

## 6. 需求追踪与验收

| 需求 | 设计/实现边界 | 必须验证 |
| --- | --- | --- |
| 互斥页签及业务保留 | CalendarPopup / 原任务日记 owner | 打开/切栏/换日/重开；完整任务/日记旅程、焦点/键盘/tooltip/明暗/窄屏 |
| 唯一右侧圆角浮空外壳 / 内部留白 | workspace拥有paper/radius/shadow，tabs/section无独立卡片；左月历/原Modal不改 | 三栏目×390/430/1024/1440×明暗及系统主题；真实wrapper外壳圆角、阴影、接缝、内行透明和实际alpha对比；左右不强制等高 |
| 自然高度 / 长内容上限 / 切栏换日 | 原CSS flex/grid与active section owner；hidden面板无高度 | 短/空/加载/错误、短→长→短、LIST/RESULT、同日与换日动态高度；长section到上限后只原owner滚动、草稿/结果/焦点恢复 |
| 短高与最后行菜单可达 | 原moreOpen/DOM/ref/keyboard，CSS in-flow方案已通过独立评审，实际验证待回执 | 命中区和tab顺序、实际支持的键盘导航/关闭、点击菜单最后项、编辑/历史返回、滚动到最后行的菜单状态截图；不以几何/截图代真实点击 |
| 阴影安全区与滚动底部 | 原Calendar画布包围calendar/workspace；harness测真实外壳 | 桌面side36/bottom56px，1024 side20/bottom36px，430/390 side16/bottom28px（16px root）；真实computed内距与外壳边界，expected必须实际比较而非void |
| 快照优先与历史创建 | facade / snapshot_store / today.py / API / CalendarNotionPanel | 无远程历史读取；今天快照先显示；缺创建字段明确 partial |
| 今天更新项校验 | operations metadata-only / facade | 只查询快照当天更新 ID；不 Search/select/sync/body/write；旧快照与新响应一致性 |
| 上游时间与当前选择 | sync / filter_snapshot_for_connector | 半开边界、DST 23/25h、双命中、去重稳定排序、取消选择不泄漏 |
| 数据库内页面与旧索引恢复 | 公开 resources/select、sync → 实际 builder → SnapshotStore → documents | 分页数据库行保留原始时间；选择数据库即可进入日历候选；旧索引 partial 经显式同步恢复 |
| 失败与并发 | actor/credential/revision guards | 401/403/404/429/网络、刷新旧结果、A→B→A、关闭/登出/午夜/隐藏 |
| 文档与技术回执 | 正式设计、exec 记录 | Markdown 清单/引用、Mermaid、diff check；命令/退出码，隔离清理 |

[正式交互设计](../../design/claude-agent/calendar-right-panel-tabs-ui-design.md)直接交付正常、异常和状态图。[本轮影响、评审和验证回执](../../exec/notion-calendar-snapshot-repair-20261006.md)区分设计可实施与实际测试完成，不以文档检查替代功能或真实业务验收。

[2026-10-07影响评估与门禁](../../exec/calendar-floating-workspace-20261007.md)和[四阶段增量证据](../../design/claude-agent/calendar-floating-workspace-workflow-20261007/README.md)对应本次修正；PRD正文仍直接交付骨架，正式交互稿直接交付业务图。此前[2026-10-06执行记录](../../exec/calendar-borderless-ui-20261006.md)、[独立评审](../../exec/calendar-borderless-ui-design-review-20261006.md)与所有历史保留，只证明其当时范围；本次[独立评审](../../exec/calendar-floating-workspace-design-review-20261007.md)已通过且CSS源码完成；实际测试/文档检查/隔离清理仍待回执。
