<!-- [Sync] 2026-10-06: close accepted Search scope, implemented read DTO, ownership, configuration and the completed technical journey matrix. -->
<!-- [Sync] 2026-10-06: link the missing-config 503 recovery and observed ntn 0.15.1 API-date contract. -->
<!-- [Input] 本轮用户目标、图标页签截图、当前 Calendar/Chat/Notion 源码、现行设计合同及 Notion 官方 API。 -->
<!-- [Output] 日历右侧页签与 Notion 今日文档的产品规则、正文页面骨架图、接口缺口及验收追踪；业务时序与状态图由正式设计稿所有。 -->
<!-- [Pos] docs/prd/calendar 的现行日历业务产品设计；已有任务、日记与连接器合同继续负责原业务。 -->
<!-- [Sync] 2026-10-04: 新增仅文档方案；独立评审统一事实、外链/日期条件与状态边界，严格完整枚举阻塞及建议接口未实现状态保持。 -->

# 日历右侧页签与 Notion 今日文档 PRD

> 2026-10-05 实施范围决定：用户已明确接受“Search 可发现的今日页面”，保留遗漏提示和刷新入口。严格授权全集不属于本次验收范围。本次实施沿用已评审候选方案；今日请求以服务端 `INK_NOTION_TODAY_API_VERSION` 显式设置 `ntn api --notion-version`，缺失或非法设置 fail closed，不从最新官方文档或 endpoint 推断日期。URL 来源由服务器 `INK_NOTION_ALLOWED_URL_HOSTS` 配置。实现及自动化结果见[实施记录](../../exec/calendar-right-panel-tabs-implementation-20261005.md)；实施前正文另存[阶段历史稿](./calendar-right-panel-tabs-prd-preimplementation-20261005-history.md)，当前正文定义已接受范围，验证状态以该记录为准。

<!-- [Sync] 2026-10-05: 按业务模块归入 docs/prd/calendar；PRD 直接包含桌面/窄屏骨架，业务时序与状态图直接位于正式设计稿；保留前轮原文。 -->

> 2026-10-05 文档修正：本稿归入日历业务目录，正文直接包含页面骨架；业务交互与状态图直接位于正式设计稿。[2026-10-04 历史原稿](../claude-agent/calendar-right-panel-tabs-prd-20261004-history.md)保留原文。该阶段只调整图示所在位置与文档维护规则；后续 Search 范围决定见本稿当前说明。

## 1. 背景与问题

用户希望把日历弹窗右侧同时显示的“定时任务”和“日记”调整为“定时任务 / 日记 / Notion”三个互斥栏目。右侧一次显示一个栏目；左侧月历继续选择日期。附件仅说明图标页签的视觉规则：选中项有圆角背景并显示图标和名称，未选中项以图标为主，名称通过提示与可访问名称提供。Home、聊天、日历和深色背景均是示例，不决定实际栏目、主题或业务。

**处理建议：保留左侧月历和透明弹窗画布，将右侧卡栈改为一个页签导航与当前栏目的纸面；复用现有任务、日记、Settings 和连接器读取边界。新增 Notion 栏目只查询文档元数据并打开 Notion，不执行资源选择、全文同步、导入或写回。**

**本次目标：三个互斥页签及 Search 可发现的今日页面。** 用户已接受该资源范围；分页扫描完成只说明当前请求结束，不能证明授权范围已被完整枚举。当前今日 DTO 从原始 page 保留创建/编辑时间，今日接口明确 API 配置、错误分类和部分结果。本次以隔离技术自动化验证实施，不宣称真实账户验收。

### 1.1 实施前源码证据（2026-10-04）

以下表格保留设计时的基线差距；当前实现入口是 `CalendarPopup`、`CalendarNotionPanel`、`notionTodayApi` 与 `routers/notion.py:today_pages`，实际验证见实施记录。

| 已验证事实 | 当前证据 | 对本需求的影响 |
| --- | --- | --- |
| 任务与日记同时显示在右卡栈，当前没有三个栏目页签 | `frontend/app/_dream/components/CalendarPopup.tsx` 的 `calendar-popup__workspace-scroll`，约 683–766 行 | 修改呈现归属，不重做任务或日记业务 |
| LIST 与 RESULT 通过 `selectedResultTaskId` 在同一任务纸面互斥 | 同文件约 725–738 行 | 页签切走后再返回，应保留同一日期的已选结果；无需增加结果路由 |
| 编辑与历史使用共享 Modal，状态由内部 `ScheduledTaskCard` 持有；RESULT 当前卸载列表卡 | 同文件 `ScheduledTaskCard`，约 172、376、406 行 | 当前并非父组件集中保存编辑/历史。页签实现须保留状态 owner，不把切栏写成无条件卸载 |
| `isAuthenticated` 布尔值、所选日期或时区变化清空任务和结果选择 | 同文件约 451–470 行的 effect 依赖 | 保留日期/登录变化行为；不能据此证明两个已登录 actor 切换也会清空，新 Notion 请求须另按 actor 绑定 |
| 日记打开与删除已有生产入口；删除已有确认 | 同文件 `handleOpenEntry`、`handleDeleteEntry`，约 600–620 行 | 保留日记打开、当前日记标识和既有删除行为；本轮不扩展删除规则、不新增确认 |
| 弹窗挂载日期优先为当前编辑日记创建日，再回退今天 | `frontend/app/_dream/App.tsx`，约 2397–2410 行 | 不强行改为今天；非今天时 Notion 显示日期提示，不能展示今日列表冒充所选日内容 |
| Chat 有内联 `role="tablist"` 和两枚按钮；两项都显示文字 | `frontend/app/_dream/components/chat/ChatView.tsx`，约 1417–1468 行 | 可参照选中背景、状态和图标；并不存在可直接导入的 `WorkspaceTabBar` 组件，完整键盘模式也须补齐 |
| 现有主题提供明暗主题 token，Calendar 继承项目字体 | `frontend/app/_dream/styles/tokens.css`、`CalendarPopup.css` | 引用现有 token 与字体，不复制截图色值或引入字体依赖 |
| Notion 的页面/数据库发现来自上游并消费分页；`selected` 只是附加标记 | `backend/notion/factory.py:list_pages/list_databases`、`backend/notion/operations.py:_discover_all` | 清单读取可复用发现与 actor 凭证边界，不要求先手动选择资源 |
| `/resources` 返回 Admin 保存的手动选择，来源索引也属于选择范围 | `backend/routers/notion.py:list_resources`、`backend/notion/store.py` | 不能把本地选择或同步来源当作 Notion 全部资源 |
| 页面发现投影保留 `page_id/title/url/last_edited/parent`，没有 `created_time` 或图标 | `backend/notion/operations.py:normalize_page_item`，约 203–215 行 | 创建分组缺必要数据；新今日 DTO 要从原始上游字段投影，不能从本地时间补值 |
| 前端 `NotionResourceOption` 只有 `lastEdited`，来源 `updatedAt` 可能取本地更新时间 | `frontend/app/_dream/api/resourceConnectorApi.ts` | 不复用 `sources.updatedAt` 判断今日创建或编辑 |

### 1.2 现行合同与本稿关系

- [定时任务完整交互 PRD](../claude-agent/scheduled-task-diary-page-prd.md)与[原交互设计](../../design/claude-agent/scheduled-task-diary-page-ui-design.md)继续定义安排、任务结果、编辑、历史、Chat 标记及执行会话。其旧“三张纸面同时可见”条款由本稿的右侧互斥页签方案补充；当前源码已采用互斥页签，既有业务入口保持。
- [Notion 资源连接器 PRD](../notion-session/resource-connector.md)与[连接器交互架构](../../design/notion-session/connector-interaction.md)继续定义 Settings 配置、选择、同步、授权和 Agent 正文读取。本文新增的是 Calendar 文档元数据发现边界，**不扩大 Agent 的已选页面正文读取权限**。
- [本轮交互设计](../../design/claude-agent/calendar-right-panel-tabs-ui-design.md)负责视觉与详细交互规格；页面骨架直接位于本稿 §4，业务时序与状态图直接位于该设计稿 §9；[本轮独立评审](../../exec/calendar-right-panel-tabs-design-review-20261004.md)记录结论与阻塞项；[文档验证回执](../../exec/calendar-right-panel-tabs-doc-validation-20261004.md)记录实际检查命令与结果。
- [四阶段设计证据](../../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/1_prd_draft.md)保留技能输入及阶段产物。历史文档保留原文并由原稿导航索引；本轮不重写历史版本、不删原功能代码。

## 2. 目标与边界

### 2.1 目标

1. 日历右侧同时只有一个栏目显示；顺序为“定时任务、日记、Notion”。
2. 页签使用附件的图标交互，并保持项目暖纸张主题及用户现有明暗主题。
3. 保留左月历、安排任务草稿、任务列表/结果、编辑、历史、暂停/恢复、删除/撤销、立即运行、精确执行 Thread 打开与日记打开/删除。
4. Notion 有可用连接和上游读取权限时，按用户现有时区展示今天创建及最新编辑时间在今天的页面元数据；各状态、计数和可见范围准确。
5. 查询与刷新只读、可重复执行；打开列表不触发资源保存、同步策略写入、正文读取、导入或其他持久业务变更。
6. 保留真实的失败与完整性限制，不能把未连接、权限不足、上游失败和搜索空结果合并成“暂无数据”。

### 2.2 本轮交付与非目标

本轮交付页签、今日只读接口、局部状态及回归自动化，同时维护 PRD/正式设计/历史稿。隔离自动化不代表真实 Notion 账户、真实模型或正常业务数据库验收。

不增加通用多平台框架、全文编辑器、全文缓存、历史活动库、Webhook、新同步调度器、队列、Notion 写入、资源导入、额外确认弹窗或与本需求无关的环境检查。本方案不需要 PostgreSQL schema 变化。未来若发现确有数据合同变更，须先由 Admin Drizzle 发布前向 migration 与 capability，Dream 不能补建表或依赖未发布能力。

### 2.3 最小合理假设

| 假设 | 设计采用方式 | 对目标的影响 |
| --- | --- | --- |
| “文档”指 Notion page，包括 Search 实际返回的数据库行页面 | data source 容器不作为一篇文档计数；附件、评论、正文 block 不在清单 | 不自动设计全部 Notion 对象浏览器 |
| 不要求限定当前用户本人 | 不按 `created_by` 或 `last_edited_by` 过滤，不额外读取人员信息 | 展示授权可访问范围里的页面 |
| 现行 Settings 只管理一个当前 Notion 连接 | 复用其当前连接选择规则，不新增账号切换器 | 若历史重复记录有歧义，保留“前往设置”解决；不自行扩张多账号功能 |
| 用户已接受 Search 可发现的今日页面 | 当前接口始终返回 `coverage=search_discoverable` | 保留遗漏提示与刷新；不扩大为授权范围全集 |

## 3. 概念与规则

### 3.1 资源与状态分别定义

| 概念 | 输入与程序含义 | 本栏目如何使用 |
| --- | --- | --- |
| Notion 工作区资源 | 工作区内所有对象 | 不承诺工作区完整枚举 |
| 连接器授权可访问范围 | 当前 actor 的有效凭证、Read content capability、Notion 分享与页面权限共同允许的资源 | 是服务器请求上游的权限边界，不等于搜索返回集合 |
| Search 可发现页面 | 当前有效凭证调用 `POST /v1/search` 实际返回的页面，受索引及分页影响 | 用户已接受的今日查询候选集合 |
| 项目已选择资源 | Admin 保存的数据库与独立页面完整选择集合 | 继续用于 Agent 索引/正文权限，不限制本次 Calendar 元数据发现 |
| 本地同步范围 | 最近成功索引与当前选择的交集 | 不用来代替上游发现或 Notion 时间字段 |
| 连接成功 | 当前连接记录存在且服务器确认有效授权 | 不代表已选择、已同步、今天有页面或具有全部资源权限 |
| 查询成功 | 本次只读扫描得到可用响应 | 与选择、同步成功相互独立 |
| 扫描完成 | 当前搜索分页已处理结束，且没有该请求的截断或未处理错误 | 只说明本次搜索扫描完成，不代表授权范围完整枚举 |

Calendar 页面的授权范围与 Agent 正文读取范围必须在接口与文档中分别命名。元数据可见不自动使页面进入 Thread，不允许 Runtime 从该清单绕过已选范围读取正文。

### 3.2 页签与生命周期

| 条件或动作 | 当前规则 |
| --- | --- |
| 顺序及图标 | 定时任务使用已有 `IconClock`，日记使用已有 `IconFile`，Notion 使用现有 `NotionMark` 字形。`NotionMark` 当前是 Settings 内部函数，实施时可最小提取共享，不能复制另一套品牌绘制 |
| 首次打开 | 已登录提供三个栏目并默认定时任务；未登录沿用现状隐藏定时任务页签，仅提供日记/Notion并默认日记。默认选择只适用于首次打开，Notion 始终保留并提示登录后连接，键盘只遍历可见项 |
| 弹窗已开时登录/登出 | 登录只补任务入口并保留当前日记或 Notion，不强行切栏目；登出时清除旧身份数据和请求，当前任务项消失则回日记。身份变化不建立新的默认页签，也不新增登录弹窗 |
| 未连接 | 保留 Notion 页签和“前往设置连接 Notion”入口，沿用 Settings 唯一配置入口，不在 Calendar 复制 OAuth 或资源选择表单 |
| 同一日期切栏 | 保留各栏目滚动位置、安排任务输入、任务 LIST/RESULT 选择和已有结果；关闭锚定更多菜单并保留可恢复的任务数据。非当前面板不可见、不可聚焦，不能因展示隐藏触发新上游查询 |
| 编辑或历史 Modal 打开 | 沿用顶层 Modal 焦点陷阱，背景月历与页签不可操作。编辑中的 desired、字段错误、revision 冲突与保存失败均由既有 owner 保留；用户关闭/取消后沿用当前丢弃未提交草稿的行为，不新增确认 |
| 日期变化 | 保留当前页签；任务按新日期重新读取并回到 LIST，列表滚动回顶部。日记读取所选日；安排输入是尚未发送意图，仍保留。Notion 清除前一日期显示并执行下述非今天规则 |
| 弹窗关闭后重开 | 重新挂载，采用 App 原有初始日期与默认页签，重新读取当前服务器状态；不建立跨次打开的页签、滚动或草稿持久缓存 |
| 打开任务聊天或日记 | 继续调用原 App callback；关闭日历并进入原生产入口，不另造导航 |
| 查看结果后要编辑或历史 | 当前源码的 RESULT 没有这些按钮，用户返回 LIST 使用既有操作即可。本轮不为保留能力额外加结果页操作，原稿与实际源码的差异需明确记录 |

保留面板状态可以在 `CalendarPopup` 的现有状态 owner 上处理，也可对已经展示过的局部面板保持挂载。必须避免隐藏面板中的旧副作用继续发起新的加载/轮询，并防止隐藏状态 owner 的 Portal 留在页面；不新建全局栏目 store 或通用框架。

### 3.3 今天与非今天

1. `App` 已传入 `userTimezone`，来自现有 `useSessionLifecycle` 和用户偏好同步；服务端由已认证 actor 读取 Admin `user-preferences.get` 的同一 IANA 时区。未能读取、缺失或非法时区不能静默使用服务器时区或固定偏移，栏目显示“无法读取日期设置，请重试”，保留其他栏目。
2. Dream 在请求开始取得一次服务端 clock，转换到该 IANA 时区得到当天日期 D。将 D 的当地零点和 D 下一日的当地零点分别转成 UTC 时刻 S、E，判断区间为 **S ≤ 时间 < E**。次日起点按当地日期构造，不能把 S 加固定 24 小时；夏令时日可能不是 24 小时。
3. 本次只有今天的 Notion 清单。用户选择非今天时保留 Notion 页签，显示“Notion 栏目只展示今天的文档。”及“回到今天”按钮，不请求上游，不显示旧今日列表，不把未来或历史日期映射到今天。
4. “回到今天”更新左侧日期并保留 Notion 页签，然后读取今日清单。不暗中修改弹窗首次打开日期。
5. 请求 `date_key` 只用于核对当前用户选择与服务器今天是否一致，不能接受任意历史区间。若跨过用户当地午夜或时区偏好已变化，服务端返回当前 `dateKey/timeZone` 的安全差异提示；前端更新服务器今天/时区上下文后重做日期门禁，保留用户原所选日期；若原选日现在不是今天，显示日期提示并等待用户点击“回到今天”，不静默改左月历或继续请求。仅所选日仍等于今天时重新请求，旧响应不得显示在新日期下。

### 3.4 时间、分组、计数与排序

- 今天创建判定使用上游 page 的 `created_time`；今天编辑判定使用上游 `last_edited_time`。不使用 connector 时间、资源行更新时间、`lastSyncedAt`、本地同步时间或读取时间。
- 同时命中创建与编辑时，只归入“今天创建”，该行显示“创建”和“编辑”两个标识；“今天编辑”分组排除创建组。一个页面只计一次。创建组时间显示创建时间，双命中可在同一行补充最近编辑时间；编辑组显示最近编辑时间。
- 创建组按 `created_time` 降序，编辑组按 `last_edited_time` 降序；时间相同按资源身份稳定排序。总计是两个互斥组的已知唯一页面数之和。
- 资源身份使用连接器 ID 与 Notion page ID；标题和 URL 不是身份。分页重复结果合并；选择较新 `last_edited_time` 对应的完整元数据，不把重复页计成多篇。不可比较或冲突记录必须作为扫描期间变化/元数据缺失提示记录，不能随意覆盖。
- 标题从 Notion title 属性取得；缺失或空标题显示“未命名文档”，不向用户展示 page ID 作为标题。图标优先使用安全 emoji；未提供或其他图标类型使用项目资源图标，不新增远程图片下载。
- 原始时间缺失、无时区或无法解析时不能补成现在。无法判定分组的记录不计入已知今日结果，并使响应标为部分结果，提示“部分文档信息暂时无法读取，可刷新重试”。
- `last_edited_time` 只代表页面当前最新编辑时间；不表示当天全部编辑记录、编辑次数或人员活动。扫描期间可能出现新编辑，结果不是同一原子时刻的历史快照。
- 两组标题只报告实际已知数量；扫描未完成/截断时使用“已发现 N 篇”，未知时显示状态，不写 0。两组为 0 只有在搜索扫描正常结束且无无法判定记录时才能显示，但仍使用“暂未发现”而非断言今天工作区完全没有资源。

## 4. 页面模块结构与信息架构

| 编号 | 模块 | 自上而下、自左至右的位置 | 内容与功能 |
| --- | --- | --- | --- |
| P01 | 现有日历 Modal | 透明画布、原有遮罩与关闭按钮 | 保留 dialog、滚动锁、关闭及焦点恢复 |
| P02 | 月历纸面 | 桌面左列；窄屏上方 | 保留年月导航、日期格、日记标记与键盘操作 |
| P03 | 右侧页签栏 | 桌面右列顶部；窄屏月历下方 | 按定时任务、日记、Notion 顺序选择唯一栏目 |
| P04 | 当前栏目纸面 | 页签栏下方 | 当前栏目的标题、状态、计数与内容；不再叠放任务和日记两张可见纸面 |
| P05 | 定时任务面板 | P04 内 | 复用 LIST/RESULT、安排输入和既有任务动作；所有权与 DTO 不变 |
| P06 | 日记面板 | P04 内 | 复用所选日日记、当前标记、打开及既有删除 |
| P07 | Notion 面板头 | P04 顶部 | “今天的 Notion 文档”、已知计数与“刷新”；不显示 token、内部 ID、API 版本或索引实现细节 |
| P08 | Notion 分组清单 | P07 下方 | 创建组、编辑组；每行图标、标题、标识、当地时间和打开入口 |
| P09 | Notion 局部状态区 | 清单之前或无清单时正文 | 连接、权限、加载、部分结果、旧结果与恢复操作；不影响月历和其他页签 |
| P10 | 既有编辑/历史 Modal | 覆盖 P01；Portal 继续由既有 Modal 管理 | 沿用已实现表单、历史分页、焦点和 revision 行为 |

桌面保持月历与右栏并列，各自滚动。右栏只保留当前栏目内容的滚动；页签与栏目头保持可达，长任务结果仍由既有正文滚动处理。窄屏按“月历 → 页签 → 当前面板”排列，控制区不横向溢出；没有可见第二个栏目或重复日期总栏。正文骨架见下文 §4.1–4.3；详细 token 映射和视觉状态见交互设计。

### 4.1 桌面页面骨架

以下骨架采用已登录场景；未登录隐藏定时任务页签，仅日记/Notion。图中的 N 与 HH:mm 是响应占位，不是测试数据或预置数量。选中项显示图标与名称，未选中项有 tooltip 和可访问名称；同一时刻只显示一个栏目。

```text
透明 Calendar 画布                                   [关闭]
┌ 月历纸面 P02 ─────────┐   P03 [◷ 定时任务] [▤] [N]
│ [上一月]  年月 [下一月]│   ┌ 当前纸面 P04 ─────────────────┐
│ 周一 … 周日           │   │ 定时任务               原计数 │
│ 日期格与原日记标记    │   ├──────────────────────────────┤
│                       │   │ P05 安排输入                 │
│ 原日期选择与滚动      │   │ LIST：原任务与操作           │
│                       │   │ 或 RESULT：返回、结果、会话  │
└───────────────────────┘   └──────────────────────────────┘

Notion 选中时：P03 [◷] [▤] [N Notion]
┌ 当前纸面 P04 ────────────────────────────────────────────┐
│ 今天的 Notion 文档               已发现 N 篇      [刷新] │
│ 上次读取：当地时间                                        │
├─────────────────────────────────────────────────────────┤
│ P09：部分文档可能尚未显示，可刷新或在 Notion 查看。        │
│ 今天创建（已发现 N 篇）                                   │
│ [图标] 标题 [创建] [编辑]                  [在 Notion 打开]│
│        创建 HH:mm · 最近编辑 HH:mm                       │
│ 今天编辑（已发现 N 篇）                                   │
│ [图标] 标题 [编辑]                         [在 Notion 打开]│
│        最近编辑 HH:mm                                    │
└─────────────────────────────────────────────────────────┘
```

### 4.2 窄屏页面骨架

```text
┌ 视口内 Calendar ───────────────[关闭] ┐
│ P02 月历纸面                          │
│ 年月导航、日期与原标记                │
├───────────────────────────────────────┤
│ P03 [◷] [▤] [N Notion]               │
├ 当前纸面 P04 ─────────────────────────┤
│ 今天的 Notion 文档              [刷新]│
│ 已发现 N 篇 · 上次读取：当地时间       │
│ P09 范围/失败反馈与恢复操作            │
│ 今天创建（已发现 N 篇）               │
│ [图标] 标题最多两行 [创建] [编辑]     │
│        创建 HH:mm · 最近编辑 HH:mm    │
│        [在 Notion 中打开]             │
│ 今天编辑（已发现 N 篇）…              │
└───────────────────────────────────────┘
```

窄屏按月历、页签、当前面板单列排列，控制区可换行；月历和当前面板保留原业务职责。只有已接受的响应才能显示数量；加载时计数未知，部分结果的数字是已知下界。

### 4.3 模块层级与弹窗关系

```text
P01 现有日历 Modal：遮罩、关闭、滚动锁与焦点恢复
├── P02 月历纸面：年月导航、所选日期、日记标记
├── 右侧工作区：桌面与 P02 并列，窄屏排在 P02 下方
│   ├── P03 日历栏目 tablist：已登录为定时任务 / 日记 / Notion
│   └── P04 当前栏目纸面：唯一可见 tabpanel 与栏目滚动
│       ├── P05 定时任务：仅已登录，安排输入 → LIST 或 RESULT
│       │   └── LIST 既有操作 → P10；RESULT 返回 LIST 后继续操作
│       ├── P06 日记：所选日条目、当前标识、打开与既有删除
│       └── Notion 内容组合
│           ├── P07 面板头：今日标题、已知计数、上次读取、刷新
│           ├── P09 局部状态：日期、连接、加载、部分与恢复
│           └── P08 两组清单：创建优先归组，编辑组排除创建组
└── P10 既有编辑或历史 Modal：复用原状态 owner 与权限
```

P10 编辑或历史 Modal 打开期间，背景月历与页签不可操作；关闭后恢复原触发控件或当前可用栏目焦点。所有示意与 §3 的状态、日期和身份规则相同，图示本身不表示功能已实现。

## 5. 用户流程、状态与恢复

### 5.1 正常读取和打开

1. 用户打开日历，系统保持原初始日期和默认栏目。
2. 用户切换到 Notion。前端先判断日期：非今天只显示日期提示；今天读取现有 `GET /api/connectors`，复用当前连接规则。
3. 未连接时保留前往 Settings 的入口；有连接时不能只凭 `status=synced` 判断授权，而要消费服务器有效授权状态及本次查询结果。
4. 前端调用 `GET /api/connectors/{connector_id}/notion/today?date_key={当前日期}`。Dream 验证会话、Admin connector 归属及用户时区，凭证 Provider 获取当前 actor 有效凭证；使用原 Notion operations driver 查询上游。
5. Dream 消费搜索分页、校验元数据、按当天区间筛选、去重与分组，然后返回最小字段及搜索完整性说明。
6. 前端仅接受当前请求上下文的响应；显示创建组和编辑组，标题显示实际已知计数。
7. 用户点击文档或“在 Notion 中打开”。复用 Settings 外链打开方式，使用服务端校验过的 Notion HTTPS URL 在新标签打开，并声明外链语义、`noopener noreferrer`；URL 缺失或无效时该入口禁用并显示“暂时无法打开，可刷新重试”。不读取页面正文、不新增内置编辑器。

### 5.2 刷新、返回与并发

- 第一次进入今天的 Notion 栏目才发起清单请求；同一打开周期切走再回来使用已显示结果。只读刷新显式重新扫描，不借“刷新”调用 `/sync`。
- 刷新时保留同一 actor、连接、日期和时区的旧结果及滚动位置，显示“正在刷新”；成功以新完整响应原子替换，不把两个扫描混合成一个清单。
- 当前搜索部分结果可以展示并标记不完整；刷新失败时保留旧结果与“上次读取”时间，不继续显示“最新”。失败的新部分扫描不能与旧完整扫描合并；用户可重新刷新。
- 请求上下文包含当前 actor 会话、connector ID、所选日期、用户时区与本地递增请求序号。切日期、切连接、断开、登出、关闭弹窗或开始更新请求时取消旧请求；即使取消失败，响应提交前也要比对上下文。旧响应不得覆盖当前结果，旧账号/连接结果不得继续显示。
- 去 Settings 时保存本次来源标记；回到当前弹窗且收到现有 `RESOURCE_CONNECTORS_CHANGED_EVENT` 的授权/连接变化后，先重读 connector；只有今天且 Notion 面板可见时自动刷新一次。若导航会卸载弹窗，则再次打开后按正常初次流程读取，不为本需求改变设置导航框架。
- 自动刷新只消费业务变化事件，不增加轮询器、搜索扫描 session 或持久活动表。查询不修改同步策略中的 default、desired、effective、revision，也不推进最近同步成功时间。

### 5.3 状态文案与操作

| 状态与判定 | 显示文案及计数 | 操作与恢复 |
| --- | --- | --- |
| 未登录 | “登录后可连接 Notion 并查看今天的文档。”，无计数 | 沿用原登录入口；其他可用栏目继续可见 |
| 未连接 | “连接 Notion 后可查看今天的文档。”，无计数 | “前往设置连接 Notion”；不在 Calendar 复制授权 |
| 授权进行中 | “Notion 连接尚未完成。”，无计数 | “前往设置继续连接”；返回后重读服务器状态 |
| 当前有效授权失效 | “Notion 授权已失效，请重新连接。”，清除当前连接旧清单 | “前往设置重新连接”；成功后重新查询 |
| 连接正常但搜索未发现任何可访问页面 | “当前连接尚未发现可访问文档。可以在 Notion 检查分享权限后刷新。” | 刷新、前往设置；不宣称整个授权范围绝对无资源，也不要求先选择资源 |
| 初次加载 | “正在读取今天的文档…”，骨架与 `aria-busy`，计数未知 | 可切栏、关闭；重复点击刷新不产生并发同请求 |
| 扫描结束，发现候选但今日命中为零 | “今天暂未发现新建或编辑的文档。”；两组已知数量为 0 | 刷新；显示必要的搜索遗漏说明 |
| 加载成功 | 两组行列表、当地时间、“已发现 N 篇”及上次读取时间 | 在 Notion 打开、刷新 |
| 分页尚未结束 | “正在读取今天的文档…”，计数未知，不显示实时发现数量 | 一次聚合 GET 尚未返回时继续加载；没有进度流或扫描会话，返回 partial 后才报告实际已知数量 |
| 分页失败、上游截断或记录无法判定 | “部分文档尚未读取，当前已发现 N 篇。”；只报已知数 | “重新刷新”；从新扫描开始，不伪造完整数量、不无限自动重试 |
| 刷新失败且已有旧结果 | “刷新失败，仍显示上次读取的文档。”，标明上次读取时间 | 重试；若授权或归属撤销，旧结果立即清除，不能沿用此状态 |
| 查询权限拒绝 | “当前连接没有权限读取这些文档。”，无完整计数 | 在 Notion 检查分享与读取权限，前往设置，完成后刷新 |
| 页级不可见/不存在/删除的明确反馈，或打开 URL 不可用 | 已有接口明确反馈时显示“此文档当前不可用，可能已移除或访问权限已变化。”；URL 缺失/无效显示“暂时无法打开，可刷新重试” | 外链直接打开，不新增 page/正文预检；外站权限或删除反馈由 Notion 目的地展示，Search 遗漏不能诊断删除，404 不能断言删除；只移除明确被拒绝行，其他可见记录保留 |
| 网络失败且无结果 | “暂时无法读取 Notion 文档，请重试。”，计数未知 | 重试；月历、日记和任务继续可用 |
| Notion 限流 | “Notion 请求较多，请稍后重试。”；部分已知结果标记不完整 | 尊重上游 `Retry-After` 后开放重试，不把 API 吞吐数写成产品配额 |
| Notion 上游不可用或超时 | “Notion 暂时无法响应，请稍后重试。” | 重试；有同上下文旧结果时沿用刷新失败反馈 |
| Admin/capability/时区设置不可用 | “暂时无法读取连接或日期设置，请重试。” | 重试；请求上游前失败，不切换本地存储或默认时区 |
| 所选日不是今天 | “Notion 栏目只展示今天的文档。”，不显示任何今日计数 | “回到今天”，更新左月历后读取 |

所有错误只呈现安全业务文案；原始 CLI 输出、堆栈、凭证、服务器路径与内部 request ID 不进入页面。搜索遗漏说明是用户判断“是否还需要去 Notion 查看”的必要信息，采用一句“部分文档可能尚未显示，可刷新或在 Notion 查看”，不展示技术排查说明。

业务时序、异常恢复与页面状态图直接包含于[正式交互设计稿 §9](../../design/claude-agent/calendar-right-panel-tabs-ui-design.md)，本 PRD 负责产品规则、页面骨架与验收，双方按同一状态和模块定义维护。

## 6. API 可行性与接口缺口

### 6.1 官方能力与用途

核对日期：2026-10-04。以下链接都是 Notion 官方资料；最新官方合同不能直接视为本仓库 `ntn` 已验证合同。

| 接口或来源 | 能力与字段 | 适用性与限制 |
| --- | --- | --- |
| [Search](https://developers.notion.com/reference/post-search)，`POST /v1/search` | 按标题 query；object 可为 page/data_source；以 `last_edited_time` 排序；支持 cursor 与 page_size。page 返回 ID、title 属性、URL、created_time、last_edited_time、icon 等 | 不提供时间区间 filter；本方案使用 page 对象、不传 query，服务器逐页过滤今天。不能编造 Search 的 `created_time` 日期参数 |
| [Search 限制](https://developers.notion.com/reference/search-optimizations-and-limitations) | 搜索可返回连接器共享范围内对象，但不保证完整枚举，索引更新有延迟，扫描期间索引也可能改变 | 不能通过全部翻页宣称全部文档；不依靠排序提前停止扫描来保证创建组完整 |
| [Data Source Query](https://developers.notion.com/reference/query-a-data-source)与[时间筛选](https://developers.notion.com/reference/filter-data-source-entries)，`POST /v1/data_sources/{id}/query` | 针对一个已知 source 的页面；`timestamp` 为 `created_time` 或 `last_edited_time`，对应同名对象内使用日期条件；以 compound AND 表示起点和终点，例如 `{"and":[{"timestamp":"created_time","created_time":{"on_or_after":"S"}},{"timestamp":"created_time","created_time":{"before":"E"}}]}`，没有额外 `date` 包装；两类时间再用 OR 合成，有 cursor。S/E 为说明占位，实施必须使用固定版本支持的合法日期值与条件结构 | 适合已知数据库行的查询，不涵盖独立页面或未知 source，也不能证明工作区全集。本轮不默认加 source 枚举与分片扫描 |
| [Page 对象](https://developers.notion.com/reference/page) | 页面本身创建与最新编辑时间是上游时间，URL 和标题由相应字段投影；容器与页面不能混计 | DTO 必须保留原始来源，不把“最近编辑”包装成活动日志 |
| [Capabilities](https://developers.notion.com/reference/capabilities) | Read content capability 与页面分享共同决定读取权限；连接成功不足以证明每页可读 | 缺读取能力或分享权限要单独反馈，不靠前端 selected 状态授权 |
| [Pagination](https://developers.notion.com/reference/intro#pagination)及[限流](https://developers.notion.com/reference/request-limits) | 按返回 cursor 继续；限流时按 `Retry-After` 处理 | 页大小遵守固定版本的官方允许范围与已有配置；超时、重试次数来自服务端技术配置，不成为产品数量限制 |
| [Status codes](https://developers.notion.com/reference/status-codes) | 401、403、404、429 与上游失败语义不同 | 404 可能是对象不可见或不存在，不能直接显示“已删除” |
| Dream `GET /api/connectors/{id}/pages`、`/databases` | 现有上游发现，后端已经顺序消费 cursor，拒绝不前进 cursor；分页后才返回列表 | 缺 created_time/icon、完整性与细粒度错误。按原接口直接在前端筛选不能满足本目标 |
| Dream `GET /api/connectors/{id}/resources` 与 sources | 已选择的 Admin 本地记录、同步状态与元数据 | 适合 Settings 和 Agent 范围摘要，不能作为今日上游文档全集 |

### 6.2 版本与完整性前置条件

- 仓库与本机固定 `ntn 0.15.1`；只读 `ntn --version` 与 `ntn api --help` 均 exit 0，help 明确支持 `--notion-version`，这些检查未访问用户 Notion 资源。
- 今日接口必须设置服务器 `INK_NOTION_TODAY_API_VERSION` 为合法 API 日期，经 `--notion-version` 传给 CLI；无默认值，缺失/非法配置以 `NOTION_API_VERSION_UNCONFIGURED` 失败。原调用不因此改 API 日期。技术测试显式注入日期，不代表正常服务已经配置或真实上游兼容性已验收。
- 2026-10-06 修复：隔离 loopback HTTP 捕获本机固定 `ntn 0.15.1` 默认和显式调用均发送 `Notion-Version: 2026-03-11`；配置模板显式采用该日期，本机原 env 已补此键。程序仍无兜底日期，已有部署须补配置并重启所拥有的 Dream 后端。连接列表 200 不代表今日配置已就绪；缺配置的今日接口 503 及同入口恢复 200 由[独立修复回执](../../exec/notion-today-503-repair-20261006.md)记录，不表示真实 Notion 账户已验收。
- 服务器管理员按所用 Notion API 合同配置日期，浏览器和 actor workspace 均不能选择版本。原始 page 时间、布尔 `has_more`、cursor、所返回 `request_status` 经今日合同校验；不从最新文档日期或 endpoint 猜测版本。
- 对固定版本支持的 `request_status.type/incomplete_reason` 做校验。`has_more=false` 仍可能伴随上游截断；Data Source Query 最新合同也有 query 结果截断情形。不能只消费 cursor 便声明完整扫描，不把上游限制写成产品配额。
- `scan_complete` 仅在所用版本的全部分页结束、cursor 正常、无上游截断、无无法处理元数据、无未处理错误时成立。无论该值为何，响应都明确 `coverage=search_discoverable`，不能返回 `all_workspace_complete=true`。

### 6.3 当前公开读取接口

当前接口 **`GET /api/connectors/{connector_id}/notion/today?date_key={当前日期}`**，并复用现有 connector router → facade → actor credential Provider → operations 路径。新接口与既有资源选择 DTO 分开，避免把今日元数据写入手动选择模型。

| 合同项 | 当前合同 |
| --- | --- |
| 输入 | connector 路由 ID 与当前 `date_key`；身份来自同源会话。没有 token、user_id、workspace 路径、Notion home、任意时间范围或用户指定主机 |
| 前置读取 | 既有 Admin connector 归属操作、`user-preferences.get`、当前有效凭证；Admin/capability 不可用在请求上游前失败 |
| 时间上下文 | `connectorId/dateKey/timeZone/intervalStart/intervalEnd/observedAt`；前端核对自己的当前日期和时区再提交显示 |
| 文档最小字段 | `pageId/title/url/createdTime/lastEditedTime/emoji/group/createdToday/editedToday`；icon 可仅投影 emoji 或项目资源图标类型，不返回 opaque raw、人员档案或正文 |
| 计数 | 创建、编辑与唯一总数，只针对响应 items；未知数量为空，不默认为 0；候选页面数可用于区分未发现可访问文档与今日无命中 |
| 完整性 | `coverage=search_discoverable`，`paginationState=scan_complete/partial`，已知记录数、安全 `partialReasons`；首次同步请求的分页处理中不对客户端伪造完成 |
| 错误 | 区分应用未登录、连接不可用、有效授权失效、读取权限拒绝、日期设置失败、限流、超时、上游异常；错误码由今日边界与既有 Admin 错误合同提供，见实施记录的错误表 |
| 只读效果 | 不更新 connector/resources/snapshots/sync-policy；不调用全文、Markdown、blocks、sync、selection 或导入接口，不写数据库 |

**分页策略：** Dream 一次请求顺序消费 Search cursor，逐页元数据处理；复用现有不前进 cursor 保护，并增加按 page ID 去重及所用 API 完整性检查。分页超时或上游失败时，已取得可处理候选时可返回 `partial`，包括候选有效但尚无今日命中；此时今日“已发现 0 篇”只是已知下界，必须并列不完整提示。未取得任何可处理候选且请求失败则返回明确失败，不返回正常空结果。刷新从新扫描开始，不新增持久扫描任务、游标会话表或公开任意 cursor 通道。限流由 driver 暴露安全错误与 `Retry-After`；今日显式版本路径将 CLI 错误映射为安全码与 `Retry-After`；原发现/同步错误合同保留。

**错误来源：** 后端先区分 Dream 会话认证、Admin 数据权限/能力与 Notion 上游错误，再投影安全业务错误。Dream 401 表示应用会话失效，应回到原登录流程；Notion 401 表示 provider 有效授权失效，应前往 Settings 重新连接。不得只按数字 401 触发全站登出或只显示 Notion 重新授权。Notion 授权失效、应用登出和归属拒绝会清除显示清单，查询本身不写 Admin connector 状态；网络或限流失败才允许保留同上下文旧结果。

## 7. 身份、权限与数据所有权

1. 前端复用 `resourceConnectorApi` 的同源 Cookie 会话与既有 API base。GET 不携带浏览器自造 actor 或 provider secret。
2. Dream 通过现有 `get_current_user`、`AdminRequestAuth` 和 `AdminRequestActor` 建立 actor；Admin strict DTO 执行 connector 归属和用户偏好读取。外部 connector ID 的错误保持现有归属隐藏语义，不返回另一个 actor 的状态或标题。
3. Dream 只从 `credential_store.effective_home(actor)` 获取服务器拥有的有效凭证，不能使用进程用户共享 home、用户输入 home、workspace 文件或 parent env 凭证。
4. Notion API 决定当前凭证和页面权限；页级被拒绝或不可见不得补成可访问结果。连接器被撤销、登出或归属变化后立即清除前端清单，不保留跨身份旧结果。
5. Admin 拥有连接、选择、同步策略和持久化数据；Dream 拥有本次元数据查询、过滤与短期页面展示。该清单不持久化正文、资源选择或历史活动，不要求新增 Admin 数据表。
6. URL 从上游 page 字段读取；今日 DTO 在 `today.safe_url` 检查 HTTPS、服务器 `INK_NOTION_ALLOWED_URL_HOSTS` 精确主机、端口与 userinfo 后投影；缺失/非法 URL 返回 null。Calendar 以新标签与 `noopener noreferrer` 打开，不新增预检、不用 page ID 拼地址；原 Settings URL 行为保留。

## 8. 可访问性与响应式

- 页签容器使用 `role=tablist` 和“日历栏目”名称；每个真实 button 使用 `role=tab`、`aria-selected`、稳定 `id/aria-controls`。三个 panel 使用 `role=tabpanel` 与 `aria-labelledby`；隐藏面板不能被辅助技术读出或进入 Tab 顺序。
- 采用手动激活：左右方向键只移动页签焦点，Home/End 到首末项；Enter/Space 激活当前焦点页签。鼠标点击同时激活并保持焦点在该页签，避免方向键浏览触发上游加载。仅一个 tab 进入正常 Tab 顺序。
- 图标 `aria-hidden`；所有栏目始终有完整可访问名称，未选中时名称可以视觉隐藏。tooltip 在鼠标悬停和键盘焦点都显示，Escape 可关闭，不以 HTML title 作为唯一名称，不要求点击才能读到名称。
- 选中项显示完整名称和圆角背景；悬停提高表面层级；焦点始终有 `--color-border-focus` 的可见轮廓，焦点和选中是独立状态。
- 切栏不强制把焦点移到列表；Tab 后进入当前面板首个可用控件。进入任务结果、退出 Modal 和返回任务列表继续复用现有焦点恢复；目标已删除时回到当前面板标题或页签。
- loading 使用 `aria-busy`，计数/刷新使用 `aria-live=polite`，权限与失败使用局部 alert；不得因后台旧响应打断读屏或重复宣告完整列表。
- 窄屏保留月历在上方与单面板；三项导航通过文字仅在选中项可见来适配。标题可换行或省略但可访问名称完整，控制区 `min-width:0`，不产生水平页面滚动。对比度、触控区和 reduced motion 沿用项目现有合同，不复制附件的灰黑颜色。

## 9. 最小影响范围与复用优先

| 范围 | 直接复用 | 需要调整或补充 | 不应改变 |
| --- | --- | --- | --- |
| Calendar | 月历、共享 Modal、任务卡/结果、日记动作、已有滚动与 i18n | 本地栏目状态、图标页签语义、右栏布局、每栏目滚动恢复、旧响应检查 | 左月历日期与既有任务/日记业务 DTO |
| Chat | 内联页签的 token、视觉状态与现有图标 | 若需要共享只抽出最小图标/样式，不能声称已有完整 tab primitive | Chat 的栏目名称、Thread、SSE、TaskSession 或消息协议 |
| Notion 前端 | API helper、connector 选择规则、变更事件、Settings 导航、外链打开 | 新今日 DTO helper 与局部状态文案，最小提取现有 Notion 字形 | OAuth、选择、同步策略表单不移入 Calendar |
| Notion 后端 | actor facade、Admin归属、凭证 Provider、ntn driver、Search cursor 保护 | 上游原始时间投影、今日只读接口、去重/部分结果/错误分类、HTTPS/服务器允许主机校验、显式 API 版本合同 | 已选范围、Agent Read、正文与同步工作流 |
| Admin | 现有 connector 读取、用户偏好读取能力 | 若现有 capability 不可用则记录阻塞；不默认新增 | Drizzle schema、资源策略、账本和配置业务 |

## 10. 验收与“需求 → 设计 → 实现 → 测试”矩阵

本表关联当前实现和实际测试入口；完整执行结果在[实施记录](../../exec/calendar-right-panel-tabs-implementation-20261005.md)。测试为隔离技术验证，覆盖公开生产入口/真实 DTO，不代表真实账户或上游全集验收。

| 编号与需求 | 设计规则 | 当前实现 | 验证入口 |
| --- | --- | --- | --- |
| R01 三个互斥页签 | §3.2、§4 | CalendarPopup 本地 active/focus、hidden/inert panels | tabs spec 日历旅程；auth-context spec 默认/可见项 |
| R02 图标与主题 | §4、§8 | 复用 SVG/token/NotionMark，手动激活与 tooltip | tabs spec 键盘、明暗、390px |
| R03 原任务与日记 | §3.2、§5.1 | 原 callback、ScheduledTaskCard/Result、Modal 与 sessions | scheduled-task-calendar 全旅程；tabs spec 日记旅程 |
| R04 状态生命周期 | §3.2、§5.2 | 同日 mounted owner/cache、各栏滚动、日期 generation | tabs spec 输入/结果/滚动/换日/重开/编辑焦点 |
| R05 用户今天 | §3.3 | AdminPreferencesData + today.day_context 半开区间 | test_notion_today DST 23/25 小时与日期；tabs 午夜 |
| R06 非今天门禁 | §3.3、§5.3 | CalendarNotionPanel 日期 guard 与回到今天 | tabs spec 非今天无请求/旧列表 |
| R07 上游时间与去重 | §3.4、§6.3 | today.read_today 原始时间、ID 合并、创建优先双标 | backend 分页/缺字段/排序；tabs unique grouping |
| R08 权限与范围 | §3.1、§7 | 既有 Admin owner/effective_home；扫描前后上下文 | backend public route 归属/凭证变化；无 Agent Read 扩权 |
| R09 Search 范围 | §1、§6 | search_discoverable、scan_complete/partial | backend cursor/截断/partial0；tabs 状态与遗漏提示 |
| R10 失败与恢复 | §5.3 | 安全错误来源、Retry-After、同上下文旧结果 | tabs 所列状态、route.abort 初次/刷新、来源错误；backend 错误码 |
| R11 并发与只读 | §5.2、§6.3 | AbortController、请求 generation、上下文匹配 | tabs A→B→A/关闭/登出；backend 无 writes/select/sync/body |
| R12 资源打开 | §3.4、§5.1、§7 | safe_url 配置主机校验；直接 Notion 外链 | backend URL 拒绝；tabs popup、缺 URL 提示 |
| R13 版本与最小边界 | §6.2、§9 | 显式版本 CLI 参数、缺配置 fail closed | backend spawn 参数/配置；本机 CLI help 回执 |
| R14 文档门禁 | §1.2、§11 | PRD 骨架、正式业务三图、阶段历史与目录 | Markdown 清单/引用/Mermaid/diff 回执单列 |

## 11. 实施状态与交付入口

用户已经接受 Search 可发现范围；设计评审 B01 的严格全集要求不属于本次验收。I01 的今日 API 日期已作为必需服务器配置，I02 已补时间/错误/部分结果 DTO，I03 已补今日 URL 校验。正常服务是否已设置该日期、真实 Notion 兼容性与真实账户数据不在本轮技术结果之中。

本轮实现与自动化技术验证完成：最后源码39项浏览器旅程全部通过、0失败、0跳过；后端37项通过，静态检查、构建、明暗/窄屏色彩及文档检查通过。具体命令、源码SHA、首次失败修复与最终回执以[实施记录](../../exec/calendar-right-panel-tabs-implementation-20261005.md)为准。PRD 直接包含桌面/窄屏骨架；[正式交互设计](../../design/claude-agent/calendar-right-panel-tabs-ui-design.md)直接包含正常/异常/状态三图。原评审与文档回执保留，不反向覆盖历史结论。
