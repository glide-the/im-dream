<!-- [Sync] 2026-10-07: Calendar current status reflects accepted-cache/ownership implementation and frontend71/11/overview1; normal cap/drain/claims still gated, pre-status histories and four current/historical diagram identities saved pending fresh docs rendering. -->
<!-- [Sync] 2026-10-07: R2实际71/71、最终Scheduled11/11及旧overview1/1通过；归档首失败、测试修复和正常发布缺口，隔离清理单独留回执。 -->
<!-- [Sync] 2026-10-07: root R2 leaf review passes strict saved marker/cooldown/owner guards; scope re-read reuses resolveSingleNotionConnector then checks captured connectorId, new8/freshbuild still pending. -->
<!-- [Sync] 2026-10-07: 最终新focused9/完整63、freshbuild、tsc/focusedESLint均实际exit0；保留首4/5与次8/1，文档/清理待最终回执，真实新UI复核受Chromeharness限制。 -->
<!-- [Sync] 2026-10-07: 第二focused9实际8pass/1fail exit1，最后Refresh请求仍在途却读旧idle计数；只修test完成边界，verif4与生产保持，待复测。 -->
<!-- [Sync] 2026-10-07: 新9例首轮4pass/5fail exit1；actor时间flags与长runFor重放导致deadline的测试前置问题已修，源码不改，待实际复测。 -->
<!-- [Sync] 2026-10-07: R1–R4独立评审通过后前端源码与63例预计旅程冻结，待Lunafreshbuild/实际验证；正常Chrome诊断harness失败不作产品结论。 -->
<!-- [Sync] 2026-10-07: 独立评审修正一次total、updatedAt强上下文失效及observed/loaded/verification分别去重；最新background成功事实同步，仍待复核。 -->
<!-- [Input] 当前连接器同步策略、公开 DTO、Calendar 快照读取与2026-10-07正常服务观察。 -->
<!-- [Output] 可见面板版本发现、极简正文、设置恢复与实际技术回执；单独记录正常发布缺口。 -->
<!-- [Pos] Calendar 同步发现增量设计证据；正文合同归现行 PRD/正式稿。 -->
<!-- [Sync] 2026-10-07: 仅设计与源码诊断，尚未实施或验收；浮空修复另行执行。 -->
# Notion同日快照发现与简约正文影响评估

本仓前端增量已通过独立评审并实现；Luna最终完整四spec **71/71**、修改诊断后的完整Scheduled **11/11**、旧Settings overview **1/1**，以及freshbuild/tsc/focusedESLint均实际exit0（§14.5）。新增8、异常刷新7均另有完整通过回执。状态同步前PRD/原3图与作用域文档已通过；本次当前4图需重新实际检查（§15）。具名隔离资源已按实际清理回执收口。正常账户首次立即同步502失败保留，随后后台重试成功且正常日历已显示今日文档（§8）。当前Admin/Dream归属与接受缓存源码、83/3/52及6/2隔离技术合同已通过；正常cap发布、旧writer drain及claims切换仍未证明，整体目标受该发布门禁约束。

> §1–7保留首次设计与源码调查时点的原文，包含当时“待review/未实施”状态；不作为当前结论。§8保存后续真实恢复观察，§9保存首轮评审修正，现行实施交接见§10，后续失败与修复见§11–12，最终实际技术回执见§13。

## 1. Optimized Prompt / 交付

核对正常服务同步状态、现有lock/timeout/分页和Admin合同，提出最小安全版本发现与简约正文，不擅自重置同步中、不增加schema或远程扫描。交付现行PRD/正式正文、完整pre-sync历史、四阶段增量和本影响评估，独立review后才生产实施。

## 2. Git与所有权

基线develop HEAD `dc5c7723f28bc75efe55f7573182fe857782dbdf`；工作区包含大量用户/其他Agent tracked和untracked改动（backend、App、连接器、设计、测试等），原样保留。此次只拥有Calendar现行PRD/正式稿、新pre-sync历史、calendar-sync-refresh-workflow-20261007、本exec及相邻.folder索引。浮空CSS/E2E/既有exec与20261006历史不覆盖；Notion生产/测试尚未获本阶段实现门禁。

## 3. 已有实际证据及局限

父Agent在正常本机公开UI和GET /api/connectors观察：一个Notion connector含7个notion_database来源；effective自动启用、15分钟、revision1；status syncing，last_attempt 2026-10-06T07:33:11Z，last_success/last_synced 2026-10-06T07:17:09Z，next_sync 2026-10-06T07:32:09Z，last_error null。今日2026-10-07，成功版本仍昨天。无需保存connector全ID、私密标题、正文或凭证。

父Agent检查当前正常backend进程启动晚于旧attempt，但这不能排除其他主机writer；Admin审计只见每次patch/saveSnapshot事务FOR UPDATE，没有owner/CAS/fencing。父Agent从正常公开入口立即同步一次，HTTP502，当时UI索引未推进；此首次失败保留。随后真实background retry成功，正常Calendar今日文档已确认，最新事实见§8；不能用fixture代替该正常账户证据。

源码：sync_policy.py的sync_policy_is_due对syncing永久False；factory.sync有进程内_SYNC_LOCKS，取消尝试写SYNC_CANCELLED，hardkill无法保证完成。operation timeout由INK_NOTION_OPERATION_TIMEOUT_SECONDS管每次CLI（默认30秒/合法<=300），数据库分页串行+cursor保护，无整次同步最长预算；scheduler60秒扫描（可由INK_NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS配置）只判due，不是lease或重试时限。跨进程自动恢复不能用age/no-local-lock/PID时间替代所有权证明。

CalendarNotionPanel当前60秒timer仅setNow做跨日；后台sync没有browser event；同日requested key保持，所以成功版本变化不会自动重读。resourceConnectorApi当前丢掉current_snapshot_version，但Admin NotionConnectorDTO/store/public GET已返回该字段，可新增严格前端投影，不用新endpoint/schema。正常正文当前常驻total/synctime/coverage，空组及重复Open链接，均可在现有组件中缩减。

## 4. 影响与最小方案

| 边界 | 现有owner / 增量 |
| --- | --- |
| 连接/授权/归属/配置 | Admin DTO＋facade＋credential Provider；只读检查仍走公开Cookie API，不改变权限 |
| 选择/数据库page/快照 | 原selected scope及SnapshotStore；新资源由成功sync加入index，不能用版本检查代替同步 |
| 日期/校验 | 原today.py与documents；历史零remote，今天只索引当天更新元数据，明确server API合同不改 |
| 版本发现 | 既有60秒timer active+document visible GET connectors；版本/context未变零documents，变化才安全重读；hidden不新请求 |
| 并发/滚动 | actor/connector/scope/auth/updatedAt/date/zone/version/generation guards；显式refresh与自动探测分开，完整同context下Notion数据/scroll保持；unknown更新clear＋reread，原RESULT/安排输入owner保持 |
| 呈现 | 标题一次真实短total＋非空组/title/time＋Refresh，移除常驻技术说明/分组重复count/Open；error/partial0/必要sync恢复保留 |
| 自动同步中断恢复 | 当前无安全跨进程接管能力，不在Dream按age清syncing；Admin owner/lease/fencing capability是确有必要的依赖事实 |

任务安排/结果/编辑/历史、日记打开/删除、Chat导航、Agent Runtime/正文读取、Gateway、schema、Webhook/队列/同步调度器均不修改。无新增持久化或资源权限。连接器恢复入口仅导航原Settings，Calendar不调用select/sync/body/config writes。

## 5. Admin依赖与实施门禁

可独立闭合：前端public DTO版本保留、可见版本发现/并发保护、极简正文及必要恢复入口。需独立review可实施后才能编码。

不可本仓安全闭合：persisted syncing进程丢失后的自动接管。所需合同为Admin原子claim、唯一owner+单调fence、服务器租约/续租和publish/finish owner/fence校验；过期writer迟到提交必须拒绝，非expired owner不得抢占。具体migration/capability由Admin Drizzle唯一管理。没有这些真实能力前保持阻塞，不能声称整体异步同步策略已修复。是否创建确有必要的Admin依赖任务由主Agent按原用户授权管理；本阶段不擅自创建跨项目任务。

## 6. 旅程、证据与隔离清理

| 旅程 | 必需验证 |
| --- | --- |
| 后台成功→同日更新 | 公开DTO从V1到V2、原日期列表出现新行；无browser event也发现；未变零documents/remote；真实missing问题须正常账户同步成功证据 |
| 可见/隐藏 | active、page visibility、切走再回、关闭/登出；hidden零新查询，probe取消；不weakening原tooltip/focus/业务3spec |
| 并发 | A→B→A/不同actor/日期/时区/版本乱序、check-read间V2→V3、401/归属撤销清空、临时失败旧列表、429冷却 |
| UI正文 | 标题一次短total，正常无重复count/coverage/fullsynctime/空组/重复Open；双命中/单一安全标题链接与aria；partial0/同步未完成/error/disabled/URL失败可恢复 |
| 原完整回归 | 原Calendar/tasks/diary/Notion3spec完整业务旅程与真实DTO；浮空自然高度/菜单及actual shadow/alpha安全断言继续 |
| 后端依赖 | owner/lease/fence缺失先记录阻塞；合同发布后才测双worker/中断/迟到提交/正常长期同步不误接管 |

Luna负责确定性接口/单元、构建和隔离Chrome技术验证；使用新明确命名output/端口/源码副本，清理仅自建资源，不停用户5173/8765。正常本机业务操作与隔离技术回执分别记录，本阶段未运行机械测试/构建或真实同步。

## 7. 完整历史与交付

- PRD pre-sync历史：19921bytes，SHA256 ecd9ccc553da8c0166459f7e9ab7c33b6039ca4014c3869dec7bcf5994b721e7。
- 正式稿 pre-sync历史：22953bytes，SHA256 099d1b59545b3fd6a123aadf77ec5794f5983e5a66d4a0637c10c72609066f47，保留前3幅Mermaid全文。
- [现行PRD](../prd/calendar/calendar-right-panel-tabs-prd.md)正文含骨架和新增规则/矩阵；[正式稿](../design/claude-agent/calendar-right-panel-tabs-ui-design.md)正文含新的正常/异常/状态图及具体交互规格。
- [四阶段增量](../design/claude-agent/calendar-sync-refresh-workflow-20261007/README.md)仅过程证据，复用原PDF target_image，不下载图片/加框架。

当前：设计待review，生产未实现、验证/清理未执行；浮空实测失败修复在独立阶段处理。不得标记整体完成。

## 8. 最新正常服务恢复观察（真实已发生，保留首次失败）

主Agent随后通过正常公开GET connectors/documents和Calendar UI确认：原策略仍enabled、15分钟、revision1；background retry成功，status applied，last_success/last_attempt均2026-10-06T21:48:20Z（本地2026-10-07 05:48），next_sync2026-10-06T22:03:20Z（06:03），last_error null。当前snapshotVersion为`snap-20261006T214820Z-dc9ee898`，candidateCount从319推进至320。documents HTTP200，dateKey/todayKey2026-10-07、Asia/Shanghai，counts created1/edited1/total2，partialReasons为空；今日日记原创建时间2026-10-06T20:53Z（本地今04:53），创建/编辑双命中且只计一次，真实正常UI标题可见。初读verification pending，随后正常UI元数据校验时间更新。

实际安全回执：`output/calendar-floating-workspace-20261007/notion-normal-runtime-receipt.json`。首次用户公开Settings立即同步POST502仍保留；成功发生于随后既有background retry，不改policy、selection或正文，无model验收。正常服务和业务记录保留，未清理。不能把一次后台成功等同新增跨进程crash recovery能力已实现：当前只证明本账户今天页面已进入快照和正常日历；owner/CAS/fencing缺口仍有真实依赖任务`01a11331-2830-7220-bf91-4a144acfd62f`由主Agent按原授权创建。

本节追加时点：设计正文当时正在独立review，最新事实不覆盖初始调查；当时浮空CSS修复已交Luna、Notion新前端尚未实施。后续评审green与实施现状见§10。

## 9. 独立评审必改项已同步（当时复核待执行）

1. 当前PRD/正式稿同步首次manual502、随后background本地05:48成功和正常今日UI可见，历史失败不覆盖；一次成功不作永久crash能力闭合。
2. 标题旁保留一次真实短total“2篇”；partial明确“已知0篇”；组计数/空组/重复Open/技术coverage/fullsynctime移除，必要恢复仍保留。
3. updatedAt强guard：任何变化（含sync patch）均unknown context、clear＋reread；没有独立auth/scope revision不得仅同snapshotVersion猜许可。只有完整同ctx才保证保留允许数据/scroll，删除“sync状态变化必保列表”的保证。
4. observed检查context/version、成功loaded、in-flight、verification完成键分别管理。读取失败/409不推进loaded，needsRead防止同observed永久dedupe，下一正常60秒周期或显式Refresh才重读，非错误effect紧循环。Retry-After抑制所有新检查/读取/校验；临时校验失败按原显式Refresh恢复，pending/partial不能标完成。

本节修正交接时点：PRD规则/骨架/验收、正式稿三幅Mermaid和四阶段增量已一致同步；pre-sync/pre-floating/20261006全部历史字节不动。当时仅文档修正、等待独立复核，未改Notion生产API/Panel/i18n/E2E；后续可实施结论与源码冻结见§10。


## 10. 独立门禁通过后的前端实施交接（实际新验证待执行）

实施 Optimized Prompt：按[独立评审R1–R4可实施结论](./notion-calendar-sync-refresh-design-review-20261007.md)，保留公开DTO版本、active/auth/page-visible串行检查、完整上下文与取消/代号提交保护、observed/loaded/读取/校验分离和规定恢复；正文只显示一次实际短总数、非空组、标题/上游时间、单一外链和必要恢复。冻结源码交Lunafreshbuild和完整回归，不改backend/Admin/schema/同步动作。

本阶段文件所有权：`CalendarNotionPanel.tsx`、`resourceConnectorApi.ts`、`i18n.ts`及邻近headers/folder；原三spec中的Notion/actor测试、既有测试fixture文档，现行PRD/正式稿/本exec及英中README局部事实。生产任务/日记/Modal/Chat状态owner和已冻结浮空CSS保持，其他Agent广泛dirty不覆盖。后台owner/CAS依赖由主任务接续，不能用本前端检查取代真实能力发布。

源码：API严格投影已存在的`current_snapshot_version`，显式null与缺字段不同，非法字符串/类型按原结构错误fail closed；不新建endpoint。Panel独立probe AbortController/generation，每轮完成后才排下一60秒检查，隐藏/页面隐藏不启动新phase；未变检查不取消有效读取/校验。完整上下文含actor/connector/选中type-ID/auth/updatedAt/date/zone；任一updatedAt变化清旧数据及成功owner，不能用同步状态猜许可。已观察和成功加载身份分开，只有通过提交检查的documents响应推进loaded；probe V2/实际V3后，后续观察V3不重读/远程。读失败/409保留needsRead，正常下周期/显式Refresh恢复；临时verification失败只显式Refresh重试，409下周期重读；Retry-After保护所有新phase。401/授权/权限失效清原完成键，恢复到相同ID也不能沿旧授权完成标志。

正文沿现有React/Token渲染：标题旁一次total或partial已知数量；空组不渲染、组数量不重复，常驻coverage/full同步时间及重复Open链接移除；原标题即安全新标签链接，保留完整可访问名称、上游时间和双命中标记。缺快照/字段、partial0、syncing影响缺失/error/disabled原因与管理入口至多一条，不发select/sync/body/config写入。Settings入口仍只导航，语言英中同义。

测试源码冻结：原三spec54完整旅程/浮空安全/真实alpha/焦点/tooltip断言保留；新增8个Notion版本/恢复参数旅程和1个mounted actor A→B→A/logout迟到旅程，**预计63例，实际枚举/执行结果以Luna为准，当前不是63通过**。覆盖无event V1→V2、串行长probe、未变零docs/remote、active/pagevisibility、实际V3竞争、初次与V1→V2读502/409、临时远程失败显式恢复与409正常周期、sync-only updatedAt ABA、授权恢复、Retry-After、一次count/单link/非空组/partial0。原日期ABA/跨午夜/关闭/登出/无写和完整任务/日记旅程继续。harness actor差异只在允许E2E目录通过AuthContext依赖注入，metadata走现有生产组件及真实公开DTO，没有复制业务状态机。

Luna使用独立新源码副本、隔离本轮自建端口和installed Chrome，freshbuild后先新增focused9再完整三spec及tsc/focusedESLint，最后当前文档/历史/Mermaid/diff和自建资源清理。精确命令、退出码、首次失败与修复留作后续追加；本worker未运行机械测试/build或启停服务。

正常新UI复核限制：主Agent在用户Chrome既有tab读取AX/screenshot/CDP出现`Emulation.setFocusEmulationEnabled`超时；同Chrome新建localhost5173 tab一次仍执行超时并reset kernel。分类为浏览器诊断harness故障，不据此判Panel缺陷、不无界重试；原正常账户今日文档已先前可视证明且§8回执保留。新精简UI/版本发现先以隔离冻结源码真实DTO自动化/截图验证，当前正常服务新UI尚未重新复核。未再触发真实同步写入，仅首次manual502及后续background成功；正常服务、账户记录保留。


## 11. 新增旅程首次失败与测试前置修复（复测待执行）

修复 Optimized Prompt：保留新增9首轮实际4pass/5fail、全部trace和原完整业务断言；根据真实DTO validator及trace时序修正actor命中标识与Clock前置，只在允许E2E目录改harness，不改生产源码或降低59秒/60秒/Retry-After、无写及迟到拒绝要求；冻结后交Luna先新增9再完整63。

首轮`output/notion-calendar-sync-refresh-20261007/focused-new9.log`实际 **4 passed / 5 failed (7.6m)，exit1**，对应`focused-new9-results`保存全部失败trace/error-context。已通过V2 probe/实际V3/再观察V3零重复、sync-only updatedAt A→B→A旧响应拒绝、probe授权丢失/同ID恢复、简约一次count/单title-link/非空组/partial0。通过四项不能替代其余失败或原完整三spec。

| 首次失败 | 分类与证据 | 最小修复/复测范围 |
| --- | --- | --- |
| mounted actor A→B→A，B文档未出现（line141，5s） | harness DTO：`lastEditedTime=2026-09-28T08:00:00Z`位于半开日区间，但`editedOnDate=false`，明确违反现有`notionTodayApi.schema.superRefine`；error-context为读取失败反馈。不是放宽validator的理由 | fixture改双命中true；仍归created、total1，继续验证A→B→A和logout迟到不能提交，无生产改动 |
| background V1→V2 line848、读502/409恢复、Retry-After恢复（共4例，均60000ms deadline） | harness Clock：第一个trace Run clock60001实际18.299s、第二22.131s、180001再33.116s；大量无关App动画/SSE定时器重放先耗尽deadline。Close context start111744.313先于heldroute fulfil start112425.107，后者报Target closed，响应没有提交；heldsync_policy已满足frozen/current normalizeSyncPolicy必要rule/status/schema/allowed字段，diagnostics并非必需，不能臆断DTO缺字段或产品失效 | 现有Modal初始焦点ready后、进入Notion前install并pauseAt；每次明确59秒/60秒/120秒边界fastForward，长heldprobe仍保证串行且无新请求。周期/冷却/零重复/可见性断言保留。同步status整行包含原管理button，按role=status文本及唯一管理入口验证，不按包含button的父p全文等于单独文案 |

安装的Playwright `Clock` API文档明确pauseAt后仅显式推进，fastForward只触发到期timer最多一次；用例逐60秒检查周期推进，避免重放全App动画，并非增加任意sleep、forceclick或改生产调度。已有正常流程、日期/午夜/actor/context代号、Retry-After及UI实际断言保留；两份测试headers和E2E folder已同步。

此次只改测试，已成功freshbuild的生产源码不变，无需为test-only前置修正重build。Luna需重跑同一新增focused9和原三spec完整63，再做当前静态/文档/历史/清理；最新命令和退出码按实际后续回执追加。当前不宣称新增9或63通过，不把首次harness失败删掉，也不以重跑通过掩盖原问题分类。


## 12. 第二轮focused实际回执及显式刷新完成边界

Luna第二轮`focused-repair9.log`实际 **8 passed / 1 failed (22.4s)，exit1**，原`focused-repair9-results`保留trace/error-context。actor DTO、串行/可见版本发现、读409与429、V3竞争、上下文ABA/授权恢复及简约正文均已通过；剩余读502/远程临时失败旅程最后计数实际3、期望4（line917）。不将第二轮8项替代完整63或删掉首次5失败。

只读trace逐请求核对（同一created/edited DTO、完整上下文相同）：

| 阶段 | 已实际documents / remote | 是否符合合同 |
| --- | --- | --- |
| 初读快照失败502 | documents #1失败；无remote | loaded不推进，等正常60秒周期 |
| 同版本首次恢复 | documents #2成功pending；remote #1成功complete，version=snap-fixture | 需要首次校验 |
| probe发现V2，读取失败502 | documents #3失败；无remote | 同上下文允许旧数据，needsRead保留 |
| 下一正常周期恢复V2 | documents #4成功pending；remote #2成功complete，version=V2 | 新版本需要校验 |
| 第一次显式Refresh | documents #5成功pending；remote #3失败502，version=V2 | refreshnonce允许重新校验，失败保留同ctx列表与错误 |
| 随后未变V2正常probe | 只有GETconnectors，无documents或remote | 不自动重试临时远程失败；保持错误及允许旧列表 |
| 第二次显式Refresh | trace最后GETconnectors仍在途(time=-1)，后续响应因立即断言失败而被teardown取消 | 本应待documents #6和remote #4完成，不可用旧列表判断已完成 |

对应trace时点：最后Refresh click结束11104.710；旧标题toBeVisible结束11107.704、旧aria-busy=false断言结束11111.598，计数3在11112.916立即失败。error-context随后已显示Refresh disabled，证明生产进入loading；不是“成功同版本无需第四次显式校验”。三次remote及未变probe零重读要求已经分别成立，新显式nonce仍要求第四次remote，原期望4不降低。

修复 Optimized Prompt：只修允许测试目录中的异步完成边界，等待第四次校验请求、alert消失、最终busy=false，再判当前标题/流程成功；生产/API/i18n不变，保留所有阶段计数、临时失败LKG和零自动remote断言。`expect.poll(fixture.verifications).toBe(4)`先确认新阶段已开始，再alert0与最终非忙碌确认响应成功，不用sleep/forceclick或把expected改3。

两份test/header和folder已同步，测试总数仍预计63；生产源码未改，无需新build。源码冻结交主任务复核后，Luna须实际重跑新增9及完整三spec63，再完成静态/文档/历史和自建资源清理。此处只是最小修复交接，复测尚未执行，不声称9/63完成。


## 13. 最终前端隔离技术回执（真实UI和后端独立门禁仍分别报告）

Luna使用本轮明确源码副本和自建55175服务，实际`focused-final9` **9 passed (18.5s)，exit0**；随后原三spec完整`full-final63` **63 passed (1.4m)，exit0**。本轮freshbuild、最终tsc和focusedESLint均退出0。首次focused9=4pass/5fail和第二=8pass/1fail的全部日志、trace、DTO/Clock/刷新完成边界修复原文仍保留；最终回归没有改expected=4、隐藏零查询、同版本零remote、上下文/actor迟到拒绝或原tasks/diary/视觉/焦点断言。生产在freshbuild后仅test-only修正，没有为测试加入业务分支。

| 实际检查 | 退出码 / 关键输出 | 回执根 `output/notion-calendar-sync-refresh-20261007/` |
| --- | --- | --- |
| 新增focused9 | 0；9 passed (18.5s) | `focused-final9.command.log` / `.exit.log` / `.log` / `focused-final9-report` |
| 原三spec完整新63 | 0；63 passed (1.4m) | `full-final63.command.log` / `.exit.log` / `.log` / `full-final63-report` / `full-final63-results` |
| 新生产源码freshbuild | 0；Next compiled successfully in107s、静态页3/3 | `build.command.log` / `.exit.log` / `.keyoutput.log` |
| 最终tsc | 0；无类型错误 | `final-tsc.command.log` / `.exit.log` / `.log` |
| 最终focusedESLint | 0；无lint错误 | `final-eslint.command.log` / `.exit.log` / `.log` |

实际命令如下，均由Luna执行，cwd为明确本轮`frontend-build`副本，不是用户正常服务或真实数据库：

focused9：

```sh
cd /Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/frontend-build
E2E_WEB_BASE=http://127.0.0.1:55175 PLAYWRIGHT_HTML_OUTPUT_DIR=/Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/focused-final9-report corepack pnpm exec playwright test e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts --grep='background V1|probe V2|same observed version|sync-only updatedAt|probe authorization loss|connector probe Retry-After|compact Notion|actor A B A' --workers=1 --trace=on --reporter=line,html --output=/Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/focused-final9-results
```

完整63：

```sh
cd /Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/frontend-build
E2E_WEB_BASE=http://127.0.0.1:55175 PLAYWRIGHT_HTML_OUTPUT_DIR=/Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/full-final63-report corepack pnpm exec playwright test e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts --workers=1 --reporter=line,html --output=/Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/full-final63-results
```

freshbuild：

```sh
cd /Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/frontend-build
corepack pnpm run build
```

tsc：

```sh
cd /Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/frontend-build
corepack pnpm exec tsc --noEmit --incremental false
```

focusedESLint：

```sh
cd /Users/dmeck/project/ink-dream-memory/output/notion-calendar-sync-refresh-20261007/frontend-build
corepack pnpm exec eslint app/_dream/components/CalendarPopup.tsx app/_dream/components/CalendarNotionPanel.tsx app/_dream/api/resourceConnectorApi.ts app/_dream/api/notionTodayApi.ts app/_dream/i18n.ts e2e/calendar-right-panel-tabs.spec.ts e2e/scheduled-task-calendar.spec.ts e2e/calendar-auth-context.spec.ts e2e/fixtures/calendarHarness.ts
```


通过范围：Calendar默认日期/栏目、键盘手动激活/tooltip/关闭重开、同日草稿/结果/scroll；完整任务安排/编辑失败冲突/run/history/results/Thread/pause/delete恢复；日记打开/返回/当前/删除；Notion快照与历史创建、今日校验、连接/权限/partial/Retry-After/网络、版本发现、页面可见/隐藏、actor/context/date ABA与迟到拒绝、单次数量/非空组/安全外链和无写；三栏四宽明暗/系统主题、自然短长高度/末行menu/真实shadow安全区与alpha对比。均是公开生产入口与真实DTO的隔离技术旅程，**不是完整真实账户业务或真实模型验收**。

原正常账户今日文档恢复观察仍以§8安全回执为准，首次manual502与后续background成功分别保留；用户Chrome新精简UI当前因focus/CDP诊断harness超时尚未复核（§10）。此次技术63不能代替该正常新UI验证，更不能证明Admin所有权/capability发布或Dream后端永久中断恢复已完成。后台合同/集成由独立worker和主任务推进，本前端不覆盖其正式稿、代码或回执。

最终当前Markdown清单/引用/Mermaid/历史hash/diff check、技术截图检视和本轮自建55175/sourcecopy清理仍待实际回执；用户正常5173/8765及业务记录保留。整体目标不得因前端技术回归已通过而提前标完成。


## 14. Settings 首次同步失败反馈增量（已评审，实施与新增验证待执行）

本轮 Optimized Prompt：在现有 Settings 资源选择/同步入口上区分服务器已确认范围保存与索引同步失败；仅严格 `ResourceConnectorApiError.context.selection_saved === true` 才声明范围已保存，并经公开 GET 回读同一连接器。保留选择草稿和最近成功索引；合法 Retry-After 只暂停现有保存/同步按钮，到期仅解禁，零自动 GET/POST。所有新异步读取、错误及冷却使用 actor、connector、请求 generation 与 AbortController 双重提交检查，A→B→A 旧响应不得提交；不改 API、i18n、Calendar 已通过63的业务实现或后端合同。

影响与所有权：当前 develop HEAD `dc5c7723f28bc75efe55f7573182fe857782dbdf`，保留广泛已有 dirty。本 worker 只修改 `ConnectorNotionDetailPage.tsx` 必要资源处理/头、dashboard.folder、允许 E2E 具名新增完整旅程与最小旧 Settings harness 认证前置、相关 folder、本 exec/README 局部。后端 worker 独占 Notion-session 主稿、服务器 envelope/所有权集成；R2 用户文案/状态建议交其合并，不覆盖。Calendar 三spec63与浮空CSS保持冻结，本轮source新变化必须由Luna freshbuild及原63+新增旅程实跑，旧63不能证明此新叶子已通过。

服务器事实：仅 replace 已确认完成后的首次 sync 失败附加布尔 `selection_saved:true`；busy 为HTTP409/code `NOTION_SYNC_BUSY`，合法 Retry-After 由服务器提供；未知 replace、手动同步没有保存标记。现有 API helper 已保留 detail context/code/Retry-After，无需改 API。

| 入口/结果 | 用户反馈与状态 | 验证边界 |
| --- | --- | --- |
| 保存后 true 标记，busy或其他safe错误 | “资源范围已保存，索引更新未完成”；busy另显示“连接器已有同步任务，请稍后重试”。只GET回读同一连接器，保留输入，不自动再同步 | 保存一次→失败→GET已保存范围→返回/重开→原来源/最近成功索引保留 |
| missing/false/字符串true或未知提交 | “保存状态未确认；你的本页选择仍保留，请返回查看当前范围后重试” | 不猜状态、不声明服务器未改变，不用HTTP status推断标记 |
| true标记但GET回读失败 | 已保存反馈保留，明确当前范围暂时无法重新读取，保留草稿/最近读取范围 | 首次POST结果和GET失败分别保留；禁止再次POST |
| 手动同步busy | “连接器已有同步任务，请稍后重试”；不声明保存范围 | 合法Retry-After期间现有按钮disabled，到期只恢复可操作；下一次仅用户点击发POST |
| actor/connector/卸载变化 | 取消GET/旧timer并推进generation，迟到结果不覆盖新状态 | mounted A→B→A、连接器切换和卸载 late response；权限每次仍由服务器裁决 |

新增完整技术旅程从正常公开 Settings 页面进入资源详情，通过真实DTO验证范围选择→保存后失败→确认GET范围→返回/重开→手动busy冷却→显式成功；另覆盖严格标记、读取失败、合法/缺失/非法Retry-After及owner迟到。技术资源只使用新命名源码副本/输出/自建端口，由Luna执行和清理；用户5173/8765与正常记录保留。到期计时仅UI状态，不是lease权限判断，无新增轮询/同步调度器/确认/API/schema/正文读取。

### 14.1 Calendar 前阶段机械文档回执（本R2新代码不在该通过范围）

Luna已实际执行 `python3 output/notion-calendar-sync-refresh-20261007/docs-final-current-check.py`，exit0：聚焦105条解码后Markdown引用0缺失，README中英文各15 headings/12 fences、PRD桌面/窄屏/浮空骨架、历史SHA和git diff --check通过。现行正式稿已有当前3个Mermaid，Chrome+Mermaid11.17.2全部parse/render通过（`mermaid-final.exit.log=0`），不是本轮另新增3图；当前图SHA与pre-sync/pre-floating历史3图不同，历史完整字节各自保留，详见 `mermaid-identity.log`。

通用全工作区旧checker exit1完整保留：8inventory缺口为其他Agent Activity/priority-activity工作或归属未知tsbuildinfo；9linkfailure中8为旧checker未decode的PDF引用（真实PDF存在），另1为其他Agent priority-activity缺失执行记录。无删除、覆盖或放宽旧checker；具体清单见 `output/notion-calendar-sync-refresh-20261007/docs-scope-receipt.md`。这不替代本R2修改后需要重做的聚焦文档检查。

主Agent已人工检视 `visual/calendar-notion-light-1440-natural-short.png` 与390暗色stress/normal技术截图：右侧独立浮空外壳、内部简约留白及自然短高符合本轮UI规则。新正常账户compact UI仍受§10 Chrome focus/CDP harness故障限制，不能把技术截图称真实业务验收；技术图库位置为 `output/notion-calendar-sync-refresh-20261007/visual/`。当前没有读取到本轮明确cleanup回执，不宣称自建55175/sourcecopy已清理，等runner实际记录。

### 14.2 R2 实现交接（待实际新增旅程与freshbuild）

仅Settings资源处理新增真实actor读取、actor/connector/action generation/AbortController提交保护、严格保存标记回读及UI冷却；正常/失败后不自动重发任何选择或同步请求。原API对object detail/Retry-After的解析已够用，API/i18n/Calendar63源码未更改。原独立Settings host仅包正常AuthProvider并提供公开sessionDTO，保留已有七段/子页完整旅程。新具名 `frontend/e2e/notion-settings-save-recovery.spec.ts` 预计8例：完整正常Settings恢复链、true502+回读失败、missing/false/stringtrue三例、非法/missingRetryAfter、unmount/connectorABA、mounted actorABA。最后一项用允许测试目录/Vite依赖注入保持叶子挂载；业务组件/API/DTO没有复制状态机。

Luna需新命名源码副本与自有端口freshbuild，然后新增8+原三spec63预计71（实际count/命令/exit以runner为准）；旧Settings spec另保持原旅程并补认证前置，若执行独立Vite则回执独立统计。当前R2代码、预期测试数均为交接，不宣称通过。先保存首次失败、按真实日志分类修复，再重跑受影响完整流程；只清理本轮自建隔离资源，不停止用户5173/8765。

主Agent独立只读复核R2 marker、Retry-After、actor/connector/generation/unmount guard方向通过；最终回读已复用现有 `resolveSingleNotionConnector`，随后严格核对捕获的connectorId，避免直接在多项DTO里find旧ID。找不到/解析后的当前Notion不同ID时保留已保存结论，显示“暂时无法重新读取当前范围；本页选择仍保留”，不采用其它连接器或自动重写。已有true502+GET失败旅程保留该反馈及后续正常返回/重开/显式同步恢复；新8源码冻结待Luna实际执行。

### 14.3 R2 首次构建/类型检查失败与最小修复（复测待执行）

Luna实际新源码freshbuild **exit1**、tsc **exit2**：`ConnectorNotionDetailPage.tsx:485:26 TS2322`，`window.setTimeout` 的数字返回值不能赋给被共享Node声明解析为 `NodeJS.Timeout` 的 `ReturnType<typeof window.setTimeout>`。这是新叶子实现的类型缺陷，不归为浏览器或业务API失败，首次日志由runner原样保留。

修复仅将叶子冷却timer局部变量声明为 `number | undefined`，明确浏览器timer句柄；定时回调、服务器Retry-After deadline、owner/generation/abort检查、到期零请求和clearTimeout清理保持原语义。影响仅该文件类型声明/头，本worker未执行build/tsc/浏览器命令。源码重新冻结，交Luna重跑freshbuild/tsc、新8、原日历63与旧Settings完整旅程；实际通过/失败/命令待后续回执，不能用先前Calendar63的通过代替本修复验证。

### 14.4 R2 新8通过后完整71首轮失败与Calendar前置修复

Luna实际 `output/notion-settings-save-recovery-20261007/settings8-repair` **8/8 passed (13.2s)，exit0**，freshbuild/tsc/focusedESLint退出0；完整四spec71首轮 **2 failed / 59 passed (1.6m) / 10 serial skipped，exit1**。失败为Calendar `ADMIN_DATA_UNAVAILABLE` 临时刷新期望2条实际0，及Scheduled Thread导航请求取消诊断；后者由runner独立分析，本worker不改其生产代码。当前完整必要回归仍未通过。

首轮完整命令未开trace；对应full71-results只有error-context，不能编造首次逐请求/React事件。主Agent `diff -u` 确认Calendar生产源与前一final63副本无差异（exit0），不采用此前不同hash即推断生产变化的结论。Calendar失败AX同时出现“0篇”、stale保留文案和正常今日空文案；源码temporary分支只保留old.data才显示stale，说明当时保留的是已提交空DTO，不能仅凭这个snapshot断言生产丢弃原2条。

只读找到fixture非原子响应机制：handle先检查 `mode==='fail'`，建立2条DTO后 `await page.evaluate(todayKey)`，恢复后再次读取可变mode并把任何非success结果清items/counts。原case只等初读标题可见即切mode=fail，仍在途中今日verification可能已越过fail检查，随后制造HTTP200/空DTO；Refresh自动等待busy解禁后会保留该空DTO。这个机制由代码可直接确认，但首次无networktrace，不能把旧失败唯一归因为该时序。

主Agent复核通过的最小harness修订：仅允许测试目录每个metadata响应在首次异步date观察前捕获mode并用于此响应后续分支；原七个failurecases在注入fault前等待真实网络verification HTTP200响应body `verificationState=complete`、remote计数1、最终busyfalse/2条/alert0。恢复阶段同样等待第二次complete响应、计数2与最终UI，再结束完整流程。原keeps2/权限清0/错误分类断言不降低，生产/API/i18n无改动。测试总数仍71，文件头/folder同步；交Luna traceOn聚焦复测七项及完整71，保存首失败和复测证据。本worker未执行任何测试/build命令。

### 14.5 R2 完整旅程最终实际回执

以上§14–14.4保留交接和首次失败的原时点。本节记录后续实际结果，均由专属Luna使用本机Chrome与具名隔离源码副本执行，不是正常账户或真实模型验收。

| 实际验证 | 结果/退出码 | 原始回执目录中的文件 |
| --- | --- | --- |
| 新Settings恢复完整旅程 | 8 passed，0 | `settings8-repair.command.log/.log/.exit.log` |
| Calendar异常刷新完整流程 | 7 passed，0 | `notion-refresh-final.log/.exit.log`，保留trace |
| Calendar、Scheduled、auth/context、Settings四spec | 71 passed (2.4m)，0 | `full71-handoff.log/.exit.log`及HTML/trace |
| 最后诊断调整后完整Scheduled spec | 11 passed (26.4s)，0 | `scheduled-final.log/.exit.log`、`scheduled-final.network.jsonl`及HTML/trace |
| 旧Settings overview及子页完整旅程 | 1 passed，0 | `old-settings-vite-repair5.log/.exit.log`及HTML/trace |
| freshbuild / TypeScript / focusedESLint | 均0 | `build-final`、`tsc-final`、`eslint-final`、`tsc-scheduled-final`、`eslint-scheduled-final`的command/log/exit回执 |

这些文件位于仓库 `output/notion-settings-save-recovery-20261007/`。完整命令、工作目录、修复分类、源码身份与清理结果另汇总于该目录 `frontend-final-receipt.md`。旧Settings须使用具名 `run-old-settings-vite-overview.sh` 与隔离Vite/React去重/cache配置；Next入口不能替代该独立host。此前旧host前置失败保留，最终真实组件与正常AuthProvider/session DTO旅程通过。

Scheduled首轮异常来自Thread导航时被正常取消的列表GET。只在具名handoff阶段、页面与Referer均为 `/story-workspace/chat`、精确GET `/api/claude-agent/threads?limit=21`且错误为 `net::ERR_ABORTED` 时记录为导航诊断；其他错误仍进入unexpected。最终测试不要求取消必须发生，逐条检查实际捕获的取消，同时保留目标URL、Calendar隐藏、目标Thread请求与 `getUnexpected() === []` 的业务断言。完整71曾在更严格但非业务必需的取消数量断言下通过；最后只调整该诊断断言，完整受影响11项重新通过，没有无理由重复另60项。

Calendar当前源码与R2副本的SHA256均为 `62d0a37b07a867bf40d99787398fa0fa33ef830cb709eff4573513e8f798bdae`，与前一final63验证副本相同。旧floating副本的不同hash不能证明本轮Calendar变化。§14.4的首轮59通过/2失败/10 serial未执行完整保留；修复后完整71没有失败或跳过。首次无trace的时序仍不可唯一归因，后续trace及明确完成边界才是复测证据。

本轮覆盖默认日期/栏目、键盘焦点/tooltip、日期与关闭重开、同日状态/滚动、任务安排和未发送草稿、编辑成功/失败/冲突、运行与历史分页、精确结果及Thread导航、暂停恢复/删除撤销、日记打开返回/当前/删除、Notion正常/异常/时区/并发/版本更新与零正文或配置写入，以及设置范围保存/首sync失败/busy/回读/冷却/ABA恢复。四宽明暗与自然浮空高度、末行菜单保持原旅程。正常账户今日文档恢复仍以§8为准；新compact UI正常Chrome验收受§10的诊断harness限制，未用技术截图代替。

## 15. Calendar 当前正文与后端状态同步（纯文档，新四图已实际检查通过）

本轮 Optimized Prompt：以当前后端代码/Notion正式稿和实际两端技术回执同步Calendar PRD/正常异常时序；保存旧全文/图块，不把旧进程锁诊断写成当前能力，也不把技术green写成正常cap/claims已开放。不修改生产或测试，不重跑业务。

影响/所有权只限当前Calendar PRD、正式交互稿与各folder、本exec；Notion-session主稿、后台/core、用户和其他Agent dirty均保留。修改前完整历史：

| 历史文件 | 完整字节数 / SHA256 |
| --- | --- |
| `docs/prd/calendar/calendar-right-panel-tabs-prd-pre-backend-status-20261007-history.md` | 27588 / `24093cae23b3b6b61cc78f736419404dfb624e9ecf0eb74c04755e7f3c8a3b87` |
| `docs/design/claude-agent/calendar-right-panel-tabs-ui-design-pre-backend-status-20261007-history.md` | 33734 / `5035b216ba5237fd60ca13bace4f4efc77a96ab33b52eb6630b68f1ce3d3d24b` |

按字节保存记录为 `output/notion-settings-save-recovery-20261007/calendar-backend-status-history-identity.json`。已有pre-snapshot/borderless/floating/sync/implementation历史均不改。

当前正文改为 facade `_accepted_snapshot`→Admin当前full identity→`load_accepted`/缺缓存走既有Admin snapshot.current只读恢复→`cache_accepted`，提交前重查updatedAt/范围/凭证/identity。同步用精确 `notion.sync-run.request/claim/renew/finish`：Admin裁决due/lease，renew及单次finish接受后缓存，未知/预算耗尽不重发或补终止写。普通read仍缺独立auth/scope revision，updatedAt强guard不放宽；Calendar零sync-run/select/sync/body写入。正式合同链接Notion交互稿§6及后端exec§13，Dream83核心/3取消/52相关与Admin consumer6/公开worker2技术通过分开统计。

原 `sync_policy_is_due` persisted syncing跳过、`_SYNC_LOCKS`与旧patch/saveSnapshot只行锁明确为首次**旧正常服务**诊断；首次manual502及后续旧background成功/正常今日可见事实不删。当前源码技术缺口已关闭，**当前正常cap目录仍缺四operation/schema，正常发布、旧writer/旧Admin ingress drain与claims切换未证明**，不清旧owner、不fallback旧写，不停止用户服务。不能宣称正常自动恢复已启用或整体目标完成。

### 15.1 图块身份与新验证要求

当前正式稿从旧3块变为4块：当前正常图更新为接受缓存/claim-renew-finish；新增当前异常恢复图；旧异常图明确历史且原bytes保留；state图原bytes保留。当前3幅业务图与历史1幅的图块SHA按正文出现顺序如下：

1. 当前正常：`b20572b49bc532d4765d47681b0339541245213cc4000e830f4ed6d9e48188de`。
2. 新增当前异常：`2e468b251a7088c2363f24a7b4c84a0cb5a3461c91341daf88928d7c071c711b`。
3. 旧异常历史：`4a954f758e59aa82fff8720c5511e67c9a3005623b1bf23341e1356ee54c52d5`。
4. 当前state：`23734f12fbbf65fab1d31dfc0f5b5d03eede52eccd7fe638d3c06235d8656dfa`。

旧3块SHA原样为 `4e0b71548e25a45fd6956cd11786eae9d7809918b483592cc6e0a70b4a557679`、`4a954f758e59aa82fff8720c5511e67c9a3005623b1bf23341e1356ee54c52d5`、`23734f12fbbf65fab1d31dfc0f5b5d03eede52eccd7fe638d3c06235d8656dfa`，均在新全文历史保存；其中旧异常=当前第3块、旧state=当前第4块，字节一致。机器可读身份为 `calendar-backend-status-diagram-identity.json`。**旧3图parse/render回执仅证明当时正文，本次不得整体复用**；主Agent审查后Luna更新具名checker当前预期4并实际parse/render全部4图，核对全文历史SHA/引用/骨架/Markdown与diff，本worker未执行机械文档或业务测试。

### 15.2 最终技术脚本与资源清理补充

前端完整71、受影响Scheduled11、Notion刷新7精确 `.command.log` 已补齐；旧Settings具名脚本第4次实跑 `old-settings-vite-script-run4` **1 passed (3.1s)，exit0**，脚本bash语法检查exit0。前3次JSX转换/fs403/optimize504均为harness前置失败，原log/exit保留，不用最后通过删除早期问题。最终脚本/回执索引为 `output/notion-settings-save-recovery-20261007/run-old-settings-vite-overview.sh`、`old-settings-vite-script-run4.command.log/.log/.exit.log`、`frontend-final-receipt.md`。

Luna实际清理日志 `cleanup-before.log/cleanup-after.log` 确认只停止自建Next55175/Vite55176的9726/9735/13140/13177，并删除本R2 frontend-build/cache/node_modules symlink；`old-copy-cleanup-before.log/old-copy-cleanup-after.log` 确认此前sync-refresh与floating两具名frontend-build副本也已清理。所有output根、日志/HTML/trace/network/visual/hash及可重复脚本保留，未知frontend/tsconfig.tsbuildinfo保留。用户5173仍由原PID11689监听；8765在清理前已经无监听，本轮未启停，不能声称“8765仍运行”。以上是已实际资源边界，不覆盖此前待清理时点原文。

### 15.3 新正文最终实际文档门禁

专属Luna在一次本机Chrome/既有Mermaid会话对当前Calendar四图全部实际parse/render，exit0，均产生SVG；旧三图回执只保留原时点。新全文历史/图块身份、当前骨架、作用域Markdown清单与引用检查均exit0：当前前端引用122条、缺失0，Notion4图/Calendar4图的当前数量和README双语结构一致，`git diff --check` exit0。命令/输出/退出码以 `output/notion-sync-ownership-dream-20261007/validation/calendar-backend-status-*.command/.log/.exit.log` 为准，最终汇总为同目录 `calendar-backend-status-final-receipt-20261007.md`。

正常capability发布、全部旧writer/ingress drain、claims启用、服务切换与发布后正常用户验收仍没有回执。正常账户当次恢复、隔离技术通过和当前源码发布状态分别报告；本轮未关闭整体目标、未创建提交或PR。
