<!-- [Input] 2026-10-04 用户目标、原图、现行增量 PRD/交互/四阶段产物、受影响目录合同、当前函数行为与 Notion 官方 API。 -->
<!-- [Output] 独立设计评审的八项裁决、源码与官方事实、必要修正、严格全集阻塞及 R01–R14 最小验收责任。 -->
<!-- [Pos] docs/exec 日历右侧页签独立设计评审；不表示功能实现、文档检查通过或真实业务验收。 -->
<!-- [Sync] 2026-10-04: 独立复核 D01–D05 最小文档修正闭合；分开裁决页签呈现、搜索候选与严格全部今日文档目标，保存最终评审。 -->
<!-- [Sync] 2026-10-05: 追加独立补正评审，确认日历业务 PRD 正文骨架及正式设计稿正文三类业务图；保留 §1–8 原文与功能阻塞。 -->

# 日历右侧页签与 Notion 今日文档独立设计评审

## 1. 裁决与评审边界

**整体严格目标：存在阻塞。** 官方 Search 明确不保证完整枚举连接器可访问文档，逐页读取、排序与刷新都不能证明“全部今天创建或编辑的文档”已经覆盖。当前已选资源及本地索引也不是授权资源全集。未得到用户接受时，不能把严格目标改为搜索可发现范围。[官方搜索限制](https://developers.notion.com/reference/search-optimizations-and-limitations)

**页签呈现：可实施。** 推荐保留左月历、原透明 dialog 画布，把右侧改为“定时任务 / 日记 / Notion”图标页签与唯一当前纸面。已登录三项；未登录保留原任务认证边界，仅日记与 Notion。附件视觉、键盘、状态 owner、Portal、原业务保留及非今天行为已有实施级规则，不需要新任务状态机或全局导航框架。

**Search 可发现今日页面候选：修改后可实施。** 其边界、只读效果与恢复方向合理；须先明确用户是否接受该范围，并完成服务器 API 日期、原始时间投影、今日 DTO、错误来源、分页完成与 URL 校验合同。建议今日 GET 尚未实现；现有代码具备可复用边界，不等于新增功能已经完成。本轮文档调整与后续实现责任见 §6。

评审者是本轮独立产品、交互与技术设计角色，未参与主 PRD、交互稿或四阶段产物的作者工作。评审者只拥有本报告，不修改功能代码、其他设计稿、数据库或用户服务。作者收到取证反馈后可修正文档；本报告以最后读取的现行稿及流程图裁决，不把较早快照的已修问题继续报告为遗漏。

### 1.1 优化后的评审执行提示词

> 作为未参与作者工作的独立评审者，读取仓库门禁、受影响目录合同、用户原图、现行 PRD/交互/四阶段文档及当前 Calendar、Chat、App、Notion API/driver/facade/auth 函数行为。逐项回答：互斥页签、附件视觉与项目规范、既有业务保留、连接后的今日清单、范围/时间/计数/完整性、失败与恢复、权限/所有权/接口缺口、过度设计。分别标注源码事实、官方事实、设计建议及未决事项；旧行号只用于定位。独立核对 Notion 官方 Search、搜索限制、Data Source Query/timestamp filter、capabilities、page、versioning、request limits 与 status codes；只执行本机 CLI version/help，不访问真实账户资源。重点核对原始时间、IANA 半开区间、去重、partial/零计数、聚合 GET 无实时进度、外链无预检、状态 owner/Portal/焦点、身份及请求乱序。用可实施/修改后可实施/存在阻塞明确分层裁决，保留严格全集阻塞，不以设计完整或文档检查宣布功能完成。保存 R01–R14 追踪和后续最小验收责任，不引入全文、同步、Webhook、队列、历史库、schema 或无必要确认。

## 2. 材料与取证范围

| 材料 | 评审用途 |
| --- | --- |
| 根 `AGENTS.md`、`Agent.md` §9、`docs/rules/README.md`、`docs/exec/.folder.md` | 文档先行、独立评审、复用、维护及实际证据门禁 |
| [增量 PRD](../prd/claude-agent/calendar-right-panel-tabs-prd.md)、[正式交互稿](../design/claude-agent/calendar-right-panel-tabs-ui-design.md) | 产品规则、接口建议、状态、视觉与 R01–R14 |
| [Stage 1](../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/1_prd_draft.md)、[Stage 2](../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/2_structure_sketch.md)、[最新 Stage 3](../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/3_hierarchy_logic.md)、[Stage 4](../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/4_ui_design.md)及其目录合同 | 技能产物、P01–P10 模块、业务时序与页面状态一致性 |
| [原图](../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/inputs/target_image.png) | 已用 `view_image` 查看：选中 Home 有圆角背景、图标和名称，另外两项仅图标；没有业务范围或技术参数 |
| [现行任务 PRD](../prd/claude-agent/scheduled-task-diary-page-prd.md)、[任务骨架](../prd/claude-agent/scheduled-task-diary-page-structure-sketch.md)、[任务 UI](../design/claude-agent/scheduled-task-diary-page-ui-design.md)及各现行补充 | 原任务/日记/Chat 能力保留；旧同时可见布局由增量稿补充，不删除原业务 |
| [连接器 PRD](../prd/notion-session/resource-connector.md)、[交互架构](../design/notion-session/connector-interaction.md)及其现行补充和目录合同 | Settings、选择、同步、有效凭证与 Agent 已选正文范围继续独立 |
| `frontend/app/_dream/{.folder.md,components/.folder.md,components/chat/.folder.md,api/.folder.md}`；`backend/{routers,notion}/.folder.md` | 当前生产源码归属、目录职责与复用边界 |
| [CalendarPopup](../../frontend/app/_dream/components/CalendarPopup.tsx)、[Calendar 样式](../../frontend/app/_dream/components/CalendarPopup.css)、[ChatView](../../frontend/app/_dream/components/chat/ChatView.tsx)、[App](../../frontend/app/_dream/App.tsx)、[API helper](../../frontend/app/_dream/api/resourceConnectorApi.ts) | 呈现、日期、任务状态 owner、结果、认证、主题与 transport 当前行为 |
| [router](../../backend/routers/notion.py)、[operations](../../backend/notion/operations.py)、[factory](../../backend/notion/factory.py)、[auth](../../backend/notion/auth.py)；Settings `ConnectorNotionDetailPage` 外链和字形 | 上游发现、Admin 归属、有效凭证、分页、DTO、错误与 CLI/API 版本 |

源码证据是本轮只读观察，不证明正常服务部署、当前用户授权、线上 capability 或真实资源覆盖。历史原文是否逐字保存、Markdown 清单、引用路径、Mermaid 语法与 diff 的机械验证由[文档验证回执](./calendar-right-panel-tabs-doc-validation-20261004.md)负责；本报告不虚构其通过结果。

### 2.1 当前函数行为与差距

| 源码事实 | 直接影响 |
| --- | --- |
| `CalendarPopup` 的 `calendar-popup__workspace-scroll` 同时渲染已认证任务 section 与日记 section，没有本轮三个页签 | 新增的是右栏呈现；保留月历和已有动作即可 |
| `selectedResultTaskId` 由 Calendar 持有；LIST 卡与 RESULT 互斥，进入 RESULT 卸载列表卡 | 切栏目须保存同日结果选择和已读结果；无需结果路由或 RESULT 编辑/历史按钮 |
| `ScheduledTaskCard` 持有编辑 desired/defaultDraft、字段错误、revision 冲突、历史及菜单；编辑/历史使用共享 Modal | 保持既有 owner 或明确迁移其状态；不能用无条件卸载丢草稿，也不能仅 CSS 隐藏而留下 Portal |
| 任务 reset effect 依赖 `isAuthenticated`、`selectedDate`、`timezone` | 认证布尔变化、换日、换时区会清空；同为已登录的 actor 切换不能由该 effect 证明。新请求与旧数据清除必须真正绑定 actor |
| `handleOpenEntry`、`handleDeleteEntry` 和 App callbacks 已有；日记删除已有确认；安排把未发送草稿交给 Chat；结果按精确 `final_message_id` 读取 | 保留原业务，不为设计稿重做创建、消息解析、结果或导航，不新增确认 |
| App 初始日期先取当前日记创建日，再取用户时区今天；Calendar CSS 已有 token、字体、断点、焦点与 reduced motion | 不强行重设今天；采用当前视觉体系 |
| Chat 页签是内联实现，两项都有可见文字；Settings `NotionMark` 是局部函数 | 可以复用 token/图标及最小提取字形；没有已完成的公共 tab primitive 可以直接导入 |
| `factory.list_pages/list_databases` 用 actor 有效 home 调上游；Admin 已选 ID 仅加 `selected` 标记。`list_selected_resources` 返回 Admin 选择记录 | 空选择仍可发现元数据；resources/sources 不能成为工作区或授权资源全集 |
| `normalize_page_item` 未返回 `created_time`、icon；`_extract_last_edited` 还容许别名 fallback；前端只含 `lastEdited`，source `updatedAt` 可取本地时间 | 今日 DTO 必须独立保留原始 page 两时间，缺字段不能补现在、改用同步时间或旧宽松 fallback |
| `_discover_all` 顺序消费 cursor 并拒绝不前进；`SearchResult` 丢弃 `request_status`，当前没有今日 DTO、去重或 partial 返回 | 复用 cursor 保护，补元数据聚合及版本支持的完成状态；不能称当前分页已具完整性保证 |
| `_run_endpoint` 未显式传 `--notion-version`；`build_notion_env` 不传 `NOTION_API_VERSION`；CLI policy 固定 `0.15.1` | 未证明项目 API 日期固定；data_sources 路径不能反推日期版本 |
| `_http_error` 区分现有 auth/permission，但泛化 operation 为 502；driver 不投影 429/Retry-After | 新今日协议要区分错误来源并安全保留限流等待，避免 Notion 401 误触发应用登出 |
| 原 operations/API helper 原样投影 URL；Settings 有 `target=_blank`、`noopener noreferrer`，局部 Markdown 链接仅做协议前缀判断 | 可复用打开方式；本次元数据 URL 的 HTTPS/允许 Notion 来源校验仍是需补充的合同，不应称已存在完整 host 校验 |

## 3. Notion 官方事实与可行性

核对日期为 2026-10-04。使用官方参考页；Query 页面普通网页读取失败后，成功只读读取同域 [官方 Markdown](https://developers.notion.com/reference/query-a-data-source.md)。没有对真实 connector、token、page 或数据库发请求。

| 官方来源 | 独立核对结论 | 本方案裁决 |
| --- | --- | --- |
| [Search](https://developers.notion.com/reference/post-search) | page object filter、标题 query、最新编辑排序、cursor/page_size；没有日期区间 filter | 不传标题 query，以 page 候选逐页在服务器筛今天。不得虚构 Search timestamp filter |
| [搜索限制](https://developers.notion.com/reference/search-optimizations-and-limitations) | 全量枚举、立即完整结果不能保证，索引延迟和扫描期间变化存在 | `scan_complete` 仅是本次搜索扫描完成。排序+cursor 不是全部授权文档证明 |
| [Query a data source](https://developers.notion.com/reference/query-a-data-source) | 查询一个已知 source 的内容；权限取决于父数据库分享与读取能力；当前参考有结果截断状态 | 不能覆盖独立 page/未知 source，不默认加入 source 枚举或分片系统，不用 `has_more=false` 单独宣布完整 |
| [Filter data source entries](https://developers.notion.com/reference/filter-data-source-entries) | `timestamp=created_time/last_edited_time`，对应同名对象内放日期条件，无额外 `date` 包装，不要求 property；compound and/or 可组合 | 时间范围示意应采用明确 compound AND，并以固定 API/CLI 合同校验；不是本候选 Search 参数 |
| [Capabilities](https://developers.notion.com/reference/capabilities) | 内容能力与上游授权控制能调用的 API 和可见内容 | 连接成功不证明每页可读；元数据可见不扩大 Dream Agent 正文权限 |
| [Page](https://developers.notion.com/reference/page) | page 有原始 `created_time`、`last_edited_time`、title 属性、URL 与 icon | 本地更新时间不是上游创建/编辑时间；最新编辑字段不是完整活动历史 |
| [Versioning](https://developers.notion.com/reference/versioning) | `Notion-Version` header 必需，当前参考最新为 `2026-03-11` | 这是官方现状，不是本仓库已采用的日期。明确 server-owned 日期和固定 CLI 回执后才能锁定 DTO/完成状态 |
| [Request limits](https://developers.notion.com/reference/request-limits) | 429 与 529 等等待使用返回 `Retry-After`，有界重试和失败反馈 | driver 暴露安全等待；不照抄吞吐数字为产品限额，不新增队列架构 |
| [Status codes](https://developers.notion.com/reference/status-codes) | 401、403、404、429、5xx 语义不同；404 可能未共享或不存在 | 必须区分 Dream/Admin/Notion 错误来源；不能由 404 或搜索缺行断言删除 |

本机只读证据：`ntn --version` 退出码 **0**，输出 `ntn 0.15.1`；`ntn api --help` 退出码 **0**，列出 `--notion-version` 与 `NOTION_API_VERSION`，未给默认 API 日期。帮助还说明 `--data` 推断 POST，与当前 `_run_endpoint` 通过 body 调 Search 一致。该证据不含账户资源读取，不证明 API 请求版本或真实权限。

## 4. 用户八项问题的逐项裁决

| 问题 | 裁决 | 事实、建议与未决 |
| --- | --- | --- |
| 1. 三个栏目是否互斥？ | **可实施** | 设计 P03 控制唯一 P04；已登录三项，未登录隐藏任务。最新 Stage 3 已有登录守卫、登出任务回 Diary 和请求/旧数据清除。隐藏 panel 必须退出读屏与 Tab 顺序；不能多张纸面同时显示 |
| 2. 是否采用附件且符合项目规范？ | **可实施** | 原图仅给选中圆角+图标+名称、未选中图标形式。正式稿采用当前明暗 token、本地字体和 Clock/File/Notion 字形；未选中 hover/focus tooltip、完整 accessible name、独立焦点及手动激活明确。无需外部字体、Tailwind 或 Font Awesome |
| 3. 是否保留原任务和日记？ | **可实施** | 原安排、LIST/RESULT、精确 final、编辑、历史、任务动作、Thread、日记 callback 保留。编辑/历史 Modal 开启时背景不可切换；同日切栏保护状态 owner，换日回 LIST，重开遵循原 initialDateKey。原正确代码只需呈现调整和缺口回归 |
| 4. 连接后今日清单能满足吗？ | **存在阻塞** | 严格“全部”不能由 Search 或已选索引保证；已有 DTO 还缺创建时间。只读 `GET /api/connectors/{connector_id}/notion/today?date_key=当前日期` 是建议未实现。搜索候选方案待用户接受，不能作为默认验收替代 |
| 5. 范围、时间、计数与完整性清楚吗？ | **修改后可实施** | 分开工作区、授权、Search、选择与同步；用户 IANA 时区下当地相邻两次零点转换 UTC，S 包含/E 排除；原始两时间、创建优先双标一次计数、ID 去重、分组时间降序稳定排序合理。partial 已知 0、正常空与午夜重做门禁已有一致规则，仍须完成服务器版本及 DTO 合同 |
| 6. 状态失败与恢复完整吗？ | **修改后可实施** | 未登录/连接/进行中/有效授权过期、搜索无候选/今日无命中、网络/限流/上游/前置失败、partial、刷新旧结果有不同反馈。聚合 GET 未返回时计数未知，没有分页实时数量。权限失败清除，临时失败仅保留同上下文旧结果。现有 driver 的安全错误分类仍需补 |
| 7. 权限、所有权和接口缺口正确吗？ | **修改后可实施** | Admin 归属和偏好、Dream 有效凭证 Provider 与本次只读聚合、Notion 上游权限职责正确。输入不接受自造 actor/token/home/区间/主机。新 GET 不 sync/select/body/写 DB；元数据不进入 Thread 正文范围。actor/connector/date/tz/generation 防乱序、有效 URL 直接打开均合理；新字段、版本、URL 校验和错误来源是实际缺口 |
| 8. 是否过度设计？ | **可实施** | 当前建议局限 Calendar 本地状态、原 Modal/图标/typed helper、现有 facade/driver 与最小 DTO。明确排除通用多平台、正文/历史缓存、Webhook、队列、扫描表、新 schema、额外同步、写入导入和确认。仅补有业务必要的范围提示与恢复入口 |

## 5. 状态与协议交叉核对

1. **页签与焦点。** 选中与 focused 分开；Arrow/Home/End 仅移动焦点，Enter/Space 激活。Portal 位于隐藏容器之外，不能假定 hidden/inert 自动隐藏 Portal；P10 开启时沿用 Modal stack，切栏关闭锚定更多菜单。登出时若焦点位于消失的任务页签或任务层，恢复到可见日记页签/面板。
2. **只读分页与计数。** 这是一个聚合 GET，服务器未返回前只展示 loading。`partial` 表达读取未完成或元数据无法判定，已知今日数可以为 0；必须与不完整提示并列。全部没有可用候选且请求失败是 Failed；正常 scan_complete 的无候选和候选存在但今日零命中分别是 SearchEmpty/TodayEmpty。任何一种成功都不证明授权全集。
3. **刷新。** 新扫描只替换本次结果，不与上次扫描拼接。成功、partial、保留旧结果必须明确读取时间；授权/归属/身份/凭证上下文变化清旧记录。连接变更先重新核对服务器状态，仅今天且 Notion 可见时刷新一次。
4. **午夜与日期。** 服务器日期/时区差异先重做门禁；原所选日若已非今天，进入 TodayOnly，等待用户“回到今天”。不能为了自动续查静默修改左月历选日。非今天无上游请求、无旧今日清单或计数。
5. **并发。** Abort 加提交前上下文检查；generation 消除 A→B→A 的首轮 A 迟到覆盖。登出、撤销、换连接、换日期/时区、关闭及新扫描使旧代号失效。隐藏面板完成有效在途请求可保存局部结果，不夺焦点、不播报、不触发新查询。
6. **外链。** 复用新标签打开方式，URL 是服务端校验的上游字段；缺失/非法禁用该行打开。没有 page/blocks/正文权限预检；Notion 目的地处理外站登录/不可见/删除。Dream 只有已有接口的明确页级错误才局部反馈，搜索遗漏与外链导航不能诊断删除。

## 6. 必要修正、未决与实施最小责任

| 编号 | 类型 | 最小处理与门禁 |
| --- | --- | --- |
| B01 | 严格目标阻塞 | Search 不保证全集；先取得能证明完整来源的方案，或由用户明确接受可发现范围。不能通过改文案、排序或 source 分片声称解决 |
| D01 | 文档事实修正 | 把已有新标签打开方式和未来 HTTPS/允许 Notion 来源校验分开；不把校验称为当前现成 helper。实施先搜共享规则，缺失才补最小配置驱动校验 |
| D02 | 文档事实修正 | 当前任务 reset 的身份依赖是认证布尔；不能声称它证明同为已登录 actor 切换清理。新页签/请求规则保留实际 actor 绑定 |
| D03 | 文档执行消歧 | Data Source 半开区间用 compound AND 的两个 timestamp 条件示意，无 `date` 包装；它仍不是 Search 参数，也未有固定 CLI 真实调用回执 |
| D04 | 文档状态消歧 | 将 partial 的已知今日 0、所有候选无效失败与正常空结果区分；Stage 3 边与正式状态表使用相同条件 |
| D05 | 文档日期消歧 | 午夜/时区差异先重做 TodayOnly；只由“回到今天”修改用户选择。登录后新项出现时不强行重置仍可用的栏目，登出当前任务回日记 |
| I01 | 后续版本合同 | 服务器固定 API 日期；核对 `ntn 0.15.1` 请求、原始字段、错误、cursor 和支持的 request_status。无当前日期回执前不得宣称已验证；不为本稿默认升级 CLI |
| I02 | 后续只读 DTO/接口 | 补原始两时间、最小 icon/title/url、上下文、去重分组与安全 partial/错误；GET 只读，不沿用 resources/sources 或正文路径代替 |
| I03 | 后续 Calendar 呈现 | 本地 active/focus 状态与单 panel，保留原 state owner，按可见性控制局部加载与 Portal，沿用主题及 i18n，不重写任务业务 |

上述 D 项是发现后反馈给作者的最小修正，不是扩展产品功能。D01–D05 已在最新现行 PRD、交互稿与 Stage 3 独立复核闭合，具体位置见 §8；无需继续增加文档状态或流程。I 项是实现缺口，不能因报告完成而标成已有代码。

## 7. R01–R14 关联矩阵与未来最小验收责任

与[PRD §10](../prd/claude-agent/calendar-right-panel-tabs-prd.md)及[交互稿 §10](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)同编号；测试列是未来责任，本轮未执行功能验收。

| 编号 | 独立裁决/对应八问 | 最小实施 owner | 最小验收 |
| --- | --- | --- | --- |
| R01 | 可实施；1 | Calendar | 已登录三项、未登录两项；唯一 panel、左月历原行为；键盘只遍历可见项、登出任务回日记 |
| R02 | 可实施；2 | Calendar/现有图标 | 选中图标+文字、未选中 tooltip/accessible name；焦点、明暗主题、窄屏不溢出 |
| R03 | 可实施；3 | 原 Calendar/App owner | 安排为未发送草稿；精确 final_message_id；原编辑/历史/运行/Thread/日记入口仍可完成 |
| R04 | 可实施；3、6 | Calendar/卡内 Modal | 同日切回滚动和结果保留；P10 字段/错误不丢、背景不可切；Portal/焦点、换日/重开规则 |
| R05 | 修改后可实施；5 | Dream actor 偏好/clock | S 包含/E 排除，夏令时短长日、非法或不可读时区 fail closed，不加固定 24h |
| R06 | 可实施；5 | Calendar 日期门禁 | 过去/未来不请求；跨午夜重做门禁不静默改选择；回到今天同步左月历 |
| R07 | 修改后可实施；5 | operations/今日 DTO | 上游原始两时间、双命中一次计数、分页重复稳定、缺时间/冲突 partial，不补现在 |
| R08 | 修改后可实施；7 | Admin DTO/Provider/Dream | 跨 actor connector 无泄露；空选择可发现元数据；列表不能扩张 Agent 已选正文权限 |
| R09 | 存在阻塞；4、5 | 产品 owner/上游覆盖决策 | Search scan_complete 不能称全集；用户未接受候选前维持 B01；截断/索引缺漏诚实呈现 |
| R10 | 修改后可实施；6 | driver/router/helper/Calendar | 区分错误来源及各状态；429/529 安全等待；partial 0、正常两类空与旧结果不同 |
| R11 | 可实施；6、7 | Calendar 请求 owner/今日 GET | A→B→A 乱序、登出/撤销/关闭拒绝旧响应；重复读取/刷新没有 select/sync/body/数据库写入 |
| R12 | 修改后可实施；7 | Dream URL 投影/Calendar | HTTPS/允许来源校验、缺/恶意 URL 禁用、正常直接新标签；无权限预检、正文或删除诊断 |
| R13 | 修改后可实施；8 | 服务器配置/driver | 明确 API 日期与固定 CLI 合同；保持无 schema、Webhook、queue、历史库或第二路径 |
| R14 | 文档检查待回执；全部 | 作者/独立评审/文档验证角色 | 清单、引用、历史原文、Mermaid、diff 有真实命令与退出码；不替代功能/真实业务验收 |

未来技术合同测试应通过生产公开入口、真实 DTO 和依赖注入覆盖确定边界，不复制 parser/状态机；测试所需数据库写入只能使用明确命名隔离库。未来若用户要求真实业务验收，使用正常本机 Dream/Admin/Gateway、指定现有真实账户和实体，回执须可在日常 Admin 查询。当前没有用户资源读取、模型调用或业务写入，不能把本报告或文档验证叫作真实业务测试。

## 8. 交付与最后核对记录

本报告完成独立事实核对、八项裁决与未来验收责任。功能代码未改；新今日接口、真实权限、API 实际日期与严格全集没有实现或真实业务验证。当前正常服务、Admin capability、真实资源分页和账户状态均未访问，属于未能验证的边界。

最后核对记录：已重新读取最新 PRD、交互稿、Stage 1 和带身份守卫的 Stage 3；未登录任务隐藏、任务入口登录守卫、登出当前任务回 Diary 与旧 Notion 清除已有明确规则。D01 的 URL 校验缺口已写入 PRD 所有权、UI §5.2 和正常时序；D02 现状仅按认证布尔说明；D03 已采用 AND 两条件且 S/E 仅说明占位；D04 正式表述与状态图 Partial/Failed 条件已一致。D05 午夜门禁保留所选日并等待“回到今天”；PRD §3.2/UI §3.3 已分开“首次打开”与“弹窗已开时登录/登出”，默认仅用于首次打开，弹窗内登录保留日记/Notion，与 Stage 1/3 一致。D01–D05 均由实际再次读取确认闭合，没有遗留的作者文档修正项；B01 与 I01–I03 仍按本报告保留。

实际文档机械检查及退出码见[文档验证回执](./calendar-right-panel-tabs-doc-validation-20261004.md)。在该回执产出前，本报告只记录“待后续验证”，不写通过。严格 B01 在文档检查通过后仍存在；用户接受搜索范围也只是关闭范围决定，不能替代 I01–I03 与功能验收。

## 9. 2026-10-05 文档归属与正文图示补正评审

**本次文档补正：可接受，未发现遗漏。** 现行 PRD 已按日历业务归属存放，页面骨架直接位于 PRD 正文；正式交互设计稿正文直接包含正常业务时序、异常与恢复时序、页面状态转换三幅 Mermaid 图。新根规则与文档职责一致。补正只调整文档所有权、图示交付位置及引用，不扩大业务范围，也不改变 §1 的整体裁决：页签呈现可实施，Search 候选修改后可实施，严格全部今日文档仍存在 B01 阻塞。

本次仍由未参与作者工作的独立评审者执行，仅追加本节与文件头 Sync，保留本报告 §1–8 原文。前八节引用旧 PRD 路径是 2026-10-04 评审记录；旧路径现为迁移指引，当前产品规则与骨架请阅读[日历业务 PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)。[前轮 PRD 历史原稿](../prd/claude-agent/calendar-right-panel-tabs-prd-20261004-history.md)单独保留，不作为现行交付位置规则。

### 9.1 直接核对材料与裁决

| 检查项 | 直接阅读的材料与内容 | 裁决 |
| --- | --- | --- |
| 业务目录归属 | [docs/prd/calendar 目录合同](../prd/calendar/.folder.md)定义日历弹窗、日期选择及右侧栏目职责；[现行 PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)头部 Pos 与该职责一致。旧 Claude Agent 路径明确仅为迁移导航，并指向现行稿和历史原稿 | 符合 `docs/prd/<业务模块>/`，没有第二份现行产品规则 |
| PRD 正文桌面骨架 | PRD §4.1 直接展示 P02 左月历、P03 图标栏目、P04 唯一当前面板、任务安排/LIST/RESULT 及 Notion 分组/刷新/打开入口；占位数量明确不是查询证据 | 正文直接交付，没有只以阶段链接替代 |
| PRD 正文窄屏骨架 | PRD §4.2 直接展示月历→栏目→当前面板单列、关闭/刷新/外链/局部恢复；§4 前文及 §4.3 明确当前栏目滚动、结果正文滚动与弹窗层级 | 主要区域、入口、切栏及滚动职责可审阅 |
| 弹窗关系 | PRD §4.3 直接包含 P01–P10 层级；P10 复用编辑/历史 owner，开启期间月历和页签不可操作，关闭恢复当前可用焦点 | 原业务与 Modal 关系没有因迁移丢失 |
| 正式稿正常图 | [正式设计稿 §9.1](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)直接包含 `sequenceDiagram`；用户→Calendar/Settings→Dream→Admin/Notion，现有 connector 读取、actor/归属/时区、元数据分页、去重分组、安全 URL、上下文提交和直接外链均在图内 | 接口沿用现名；新今日 GET 显著标注建议且未实现 |
| 正式稿异常与恢复图 | 正式稿 §9.2 直接包含 `sequenceDiagram`；非今天、应用登录、Settings 授权返回、Admin 前置失败、Notion 授权/权限/限流/上游失败、partial 与从头重试有明确分支 | 失败反馈与恢复路径直接位于正文，没有新增同步或正文读取 |
| 正式稿状态图 | 正式稿 §9.3 直接包含 `stateDiagram-v2`；默认栏目、登录守卫、登出清理、日期门禁、缓存、Loading、Success、两类空、Partial、旧结果与撤销均表达 | 与既有状态规则一致，partial 已知今日 0 不成为正常空结果 |
| 与过程图一致 | 阅读正式稿 §9.1–9.3 与[Stage 3 §5–7](../design/claude-agent/calendar-right-panel-tabs-workflow-20261004/3_hierarchy_logic.md)，参与者、接口、判断条件、错误分支和状态转换相同；Stage 3 保留过程证据，正式稿声明自己拥有业务图 | 未发现业务规则漂移；代码块逐字一致性及 Mermaid 解析由文档验证角色检查 |
| 根维护规则一致 | 根 [AGENTS.md](../../AGENTS.md)“产品文档归属与图示交付要求”、[Agent.md §9](../../Agent.md)、[规则索引](../rules/README.md)均明确 PRD 正文骨架、正式设计稿正文业务/状态图及阶段产物只作过程证据 | 所有权分工一致，没有以链接代替各自正文图示 |
| 范围与门禁保持 | PRD 及正式稿继续保留 Search 可发现候选、严格完整枚举阻塞、API 日期/DTO/URL/错误缺口和建议 GET 未实现标记；查看/刷新只读、不 select/sync/body/写 DB、不扩大 Agent 已选正文权限 | 本次不关闭 B01 或 I01–I03，不增加框架、schema、队列、Webhook、历史库或功能验收声明 |

### 9.2 证据与验证职责

本次只读审阅使用 `sed -n '118,215p' docs/prd/calendar/calendar-right-panel-tabs-prd.md`、`sed -n '270,378p' docs/design/claude-agent/calendar-right-panel-tabs-ui-design.md`、`sed -n '378,491p' docs/design/claude-agent/calendar-right-panel-tabs-ui-design.md`、Stage 3 对应段落及根规则读取，相关命令退出码均为 **0**；关键输出是 PRD §4.1–4.3 的正文骨架/层级与正式稿 §9.1–9.3 的两个时序图、一个状态图。它们是直接阅读证据，不是自动文档检查通过回执。

本次未重新研究 Notion API、未执行 CLI/模型/资源查询、未改功能代码、未运行链接/Markdown 清单/历史原文比对/Mermaid 解析等机械检查。作者保留历史原稿并提供旧路径指引已可直接阅读；历史是否逐字保存及最终所有引用、清单和 Mermaid 语法由后续 Luna 复核，并追加到[文档验证回执](./calendar-right-panel-tabs-doc-validation-20261004.md)。该回执无论是否通过，都不能作为新增功能、真实账户资源覆盖或真实业务验收证明。
