<!-- [Input] Dream 当前 Notion facade/store/scheduler/cache，以及 Admin 正在冻结的四 operation、execution JSON 和 capability 合同。 -->
<!-- [Output] Dream 集成影响、方案历史、冻结实现、失败修复及实际技术与发布门禁回执。 -->
<!-- [Pos] Dream 后端集成执行记录；不替代正式产品/设计正文或正常发布事实。 -->
<!-- [Sync] 2026-10-07: 保留初稿及R1/R2/R3/R4修复记录；追加实际Admin consumer 6/6和公开worker 2/2，Dream复测与正常发布分别收口。 -->
# Notion 同步归属 Dream 集成影响与实施记录

**当前状态：实现已冻结，Dream 后端功能复测、作用域文档和设计图检查通过；正常发布仍阻塞。** 精确合同和源码准入见§9–10，首次失败及分类修正见§11，Admin实际消费者联调见§12，本仓实际复测见§13。以下首轮声明保留当时的 proposal 状态，不代表当前尚未编码。

初稿声明（历史）：

**状态：仅 proposal，未实现。** Admin 依赖任务 `01a11331-2830-7220-bf91-4a144acfd62f` 仍在实现/验证；本文按实际源码草案描述字段，不将其视为 published artifact，不写入尚未确认的 operation/schema hash。正常账户已恢复；本阶段不重复真实 sync/select/body，不启停服务或修改正常数据库。

## 1. Optimized Prompt 与实施前门禁

只读核对 Admin strict DTO、四个 operation、receipt、lease 和缓存发布规则，复用 Dream 现有生产入口及权限 owner；提出先 Admin 条件提交、后按接受版本缓存、全部消费者读取一致性与单条同步路径。交付可独立评审的影响/方案及完整旅程。主 Agent 确认冻结发布合同并批准方案前不改生产代码。

进入实现必须获得：Admin 精确 operation inventory/schema artifact、对应发布 revision 与验证回执；四个 operation digest 和 `dream.notion-sync-ownership.v1` digest 均来自该 artifact，不从 Drizzle 最新 head 推断。实现可消费已确认 artifact；新 claim 实际启用另需 Admin 配置、受控 actor 锁 capability 和旧 writer/旧 ingress drain 证明。仅登记 capability 不等于已启用或正常库已迁移。

## 2. Git、所有权与已有生产事实

Dream 基线 develop HEAD `dc5c7723f28bc75efe55f7573182fe857782dbdf`。工作区已有用户及其他 Agent 的 backend、App、连接器、Calendar、测试和文档改动；`factory.py/sync.py/operations.py` 已承载快照日期修复，不能覆盖这些增量。此次仅拥有本文；拟实施所有权为：

| 文件/目录 | 拟负责变化 |
| --- | --- |
| `backend/services/admin_data/notion_connector_data.py` | strict execution DTO、四 descriptor、独立精确 schema gate、原 receipt 恢复及结果绑定 |
| `backend/services/admin_data/request_auth.py` | 仅注册四个 Notion operation，不改其他领域认证/委托 |
| `backend/notion/store.py` | manual/user request 与 service-only claim/renew/finish adapter；保持 actor 投影 |
| `backend/notion/factory.py` | manual/保存非空范围首次同步/scheduled 共用 claim→build→renew→finish；停止旧 transition/save；全部快照消费者对齐接受 identity |
| `backend/notion/snapshot_store.py` | 私有版本隔离缓存、接受 identity 校验、原 thread 投影/清理安全约束 |
| `backend/notion/sync_policy.py`、`sync_scheduler.py` | 不再以 persisted syncing 永久跳过；真正 due/busy/lease 判断由 Admin 所有；产品策略值不变 |
| `backend/notion/errors.py`、`backend/routers/notion.py` | 仅本域typed busy错误和现有public HTTP映射，不改其他路由或共享AdminDataError |
| `backend/tests/**` 及受影响 headers/.folder.md | 使用真实 DTO/公开入口的具名 DI harness；不增加生产 test-only 分支 |
| `docs/prd/notion-session/resource-connector.md`、`docs/design/notion-session/connector-interaction.md` | 保存变更前全文，补正文骨架/业务时序/异常/状态与验收；Calendar 文档由前端作者持有 |

新增 operation registration 不将新 schema 要求合并进全部旧 connector reads：旧只读/LKG 路径仍可用，任何新同步必须单独通过 execution 精确 capability gate，缺能力不落回旧写入。架构/操作边界变化还须同步两份 README，由主 Agent 协调其共享所有权。

当前生产差距：`sync()` 在进程内 `_SYNC_LOCKS` 中写 started policy，构建后先 `publish_current` 再 `save_snapshot`，最后从旧 started_policy 写 succeeded/failed；hard kill 可遗留 syncing，取消补写也可能失败。worker 对 syncing 永久判 not due。Calendar、facade.get_current_snapshot 与 thread project 直接读取 actor `current.json`，未和 Admin 接受 identity 对齐。Admin 新草案会封闭旧同步写入口，故这些调用不能保留为新 claim 的 fallback。

## 3. 实际 Admin 草案合同（待冻结，不 pin hash）

来源为 Admin `notionSyncRunDto.ts/notionSyncRunState.ts/notionSyncRunRepository.ts/notionConnectorHandler.ts`、`config/notion-sync-policy.ts` 及 `drizzle/contracts/dream-notion-sync-ownership-v1.json`。

| operation | 输入与认证 | 结果及 Dream 使用 |
| --- | --- | --- |
| `notion.sync-run.request` | authority（原 thread/run nullable合同）、connector_id UUID、worker_id UUID；dream:write actor 与 connectors:sync service 同时验证 | 手动/保存非空范围首同步；claimed 才构建，busy 不抢占、不伪成功 |
| `notion.sync-run.claim` | connector_id、worker_id；service-only connectors:sync | 自动扫描复用现有候选接口；Admin 锁内判断 latest effective/due，可能 claimed/busy/not_due |
| `notion.sync-run.renew` | connector_id、worker_id、run_id UUID、正安全整数 fence_epoch；service-only | 校验当前归属/上下文/DB clock；renewed 才继续，失败停止自建远程扫描 |
| `notion.sync-run.finish` | 同一归属键；outcome为 succeeded（workspace_id、snapshot、synced_resources）/failed（严格安全code）/cancelled（NOTION_SYNC_CANCELLED）；service-only | 一个终止 outcome；Admin 原子提交 snapshot/关系/current identity/当前 policy/run/receipt/audit；只有成功接受后缓存 |

输出是严格 `status/connector/run/server_now/retry_at/execution_policy/snapshot`。run 包含 service_client_id、worker_id、owner_user_id、selection_revision、authorization_revision、policy_revision、lease timestamps 与 terminal status。execution_policy 是正安全整数 lease_seconds、heartbeat_seconds、renewal_budget_seconds，且 heartbeat+budget<lease，来源为 Admin 服务器配置，不自设产品阈值。

所有响应须匹配请求 connector、worker/run/fence、当前 actor 与状态组合；terminal succeeded 还须绑定 snapshot metadata/workspace/version 与返回 connector identity。request 的用户 bearer 仅用于 request 和其原 user receipt；**renew/finish 必须 access_token=None、背景 connector-scoped receipt**，即使执行由用户发起。Admin handler 明确拒绝 background operation 的 delegated user bearer；复用同一个服务 client，不新增 OAuth/凭证机制。

复用 `AdminDataClient.supports/capabilities/execute/receipt/background_receipt` 和 `AdminNotionConnectorData` 的未知写屏障。旧21 descriptor/hash保持原样，新四 descriptor/schema gate独立。写超时/5xx仅查询原 request_id 的 receipt；absent/查询失败保留 outcome_unknown，不使用新UUID重发 claim/finish。已提交 claim receipt 只证明曾取得归属，开始远程扫描前需 renew 证明当前仍有效；已提交 finish receipt 可恢复接受结果，不再次终止。

## 4. 单一执行路径与续租

1. worker_id 是服务器生成、进程稳定 UUID；按实际 PID 变化重新生成可避免 prefork 继承相同UUID，但 PID不用于判定他人 lease 失效。不得接收浏览器 worker/run/fence/lease 输入。
2. 手动与范围保存调用 request，scheduled 调用 claim；其后共用同一执行函数。去掉旧进程 mutex 对整次扫描的阻塞语义，不能让第二次 manual 在锁后偷偷启动另一轮；Admin 活跃 lease 返回 busy。进程内只可保留不代替 Admin 归属的短暂实现保护。
3. 使用 claimed connector.sources 构建原轻量索引，仍由现有 builder 完成数据库分页/独立页 metadata，`pages={}`。构建前后核对有效凭证文件身份；来源/授权 revisions 与 owner/fence 由 Admin renew/finish检查，A→B→A不能恢复旧run。不得在同步中为“保持授权”反复 auth-state.save，该 operation 会推进 authorization_revision。
4. 并行启动一个受控 heartbeat 与一个构建 task；同步 Admin HTTP 通过现有线程执行方式移出 event loop，否则续租无法运行。按 Admin heartbeat_seconds 串行 renew，最多一个在途续租；monotonic 只控制本进程 renewal_budget_seconds，不用客户端时钟裁决其他 worker 的 lease。每次拒绝/未知结果/预算耗尽停止后续扫描并取消、等待本轮 builder；现有 operation cancellation仅终止其自建 ntn 子进程。
5. 当前 Admin transport 是同步 HTTP、固定配置 timeout；外层预算不能杀死已进入的线程。超出 renewal budget 后不启动第二次 renew或新finish，不再调用 Notion，跟踪并等待原有限 HTTP/receipt 请求退出。不能借 asyncio.wait_for 声称底层写已取消，迟到 Admin 写仍由 owner/fence保护。若冻结合同要求更强 per-request timeout，实现前由主 Agent 批准 shared-client 的最小扩展，不改全局 timeout/共享 client 状态。
6. builder完成后停止并等待当前heartbeat，提交 succeeded finish；构建失败/用户取消仅在归属仍已知有效且没有终止写在途时提交一次 failed/cancelled。renew拒绝、ctx变化、unknown finish或失效 lease后不得再补 failed 覆盖新run。cancelled outcome的有界终止请求可使用现有receipt机制；请求本身未知则停止并让Admin lease过期，不循环重试。
7. succeeded只返回Admin原子接受的identity。缓存失败发生在Admin成功之后，不能改写为run failed；后续读取从Admin接受快照恢复缓存。失败/取消/旧writer拒绝均保留允许范围内的LKG。manual busy按§4.1给出明确可恢复409，scheduled busy/not_due属于未执行，不计成功；不改变现有公共 sync endpoint或创建第二套协议。

scheduled 不再根据本地 syncing/age/next_sync决定接管。保留既有扫描周期和候选来源，只对认证且有来源的候选调用Admin claim，最新策略、DB clock和active lease在锁内裁决；默认/desired/effective/revision仍由原产品策略及Admin所有，Dream不写旧started/succeeded/failed JSON。保存空范围使用Admin resources.replace的原子清identity结果并清自有缓存，不再generic patch current_*。

### 4.1 Manual busy的最小typed错误与公开恢复

现有 `AdminDataError` 没有本域retry DTO，router对它只输出detail=code；`NotionSnapshotNotReadyError`固定提示先连接/选择，也不能表示有效owner忙。拟在 `notion/errors.py`增加具名 `NotionSyncBusyError`，只保存固定安全code `NOTION_SYNC_BUSY`和nullable `retry_after`，不携带run/fence/worker、内部配置或上游正文。

当request返回busy时，facade从该输出已校验的 `server_now/retry_at`计算 `ceil(max(0, retry_at - server_now))` 秒；两端均为服务器时间值，不读取客户端wall clock、不据此判定lease失效或允许抢占。missing/null/非法或不可安全序列化的retry只返回明确busy、无Retry-After，不伪造延迟或成功。用户等待后重试仍必须重新经Admin原子request，不用客户端倒计时判权限。

`routers/notion.py::_http_error`新增本域类型分支：409、现有detail对象中的 `error_code=NOTION_SYNC_BUSY`，仅有合法非负整数时发Retry-After头。共享AdminDataError与其他domain映射不变。Settings当前 `fetchJson`已经读取detail.error_code及Retry-After，叶子同步反馈需由主Agent协调前端文件owner作最小code文案映射（“连接器已有同步任务，请稍后重试”），保留当前资源/索引、不新增确认/自动排队/计时器；避免只显示通用“请求失败409”或“先连接选择”。范围保存后首同步若busy/失败，不得把已提交的范围说成未保存；按实际已完成步骤给反馈，不能回滚或猜测配置。本worker不覆盖前端作者的改动。

## 5. 接受版本缓存与全部消费者

Admin current identity 为唯一接受来源；本地文件是可恢复缓存，不另设当前事实。finish先提交，再写对应版本的私有文件。版本是不透明EntityId，不直接拼接任意字符串路径；用固定安全编码/摘要作文件键，文件内仍核对完整原身份，不按版本字符串或fetched_at排序。旧current.json只作为兼容缓存候选，必须与Admin full identity一致；新writer不抢写共享current指针。

统一复用 facade 的接受快照解析：actor/connector归属及有效授权→当前identity→精确本地version缓存→缺失/损坏/不匹配时走现有用户 `snapshot.current/get`→核对完整identity、pages为空→缓存。实际 `NotionConnectorRepository.persistSnapshot`将metadata的snapshot_version/source_revision/sync_cursor分别写入connector.current_*，并将 `metadata.fetched_at`写入 `connector.last_synced_at`；解析应按该实际合同匹配resource_connector_id=connector.id、workspace_id=connector.id、三个current字段以及fetched_at与last_synced_at的同一UTC时间值，另校验metadata.state为snapshot_ready，不从connector猜state。Admin unavailable/权限拒绝时不把未核验本地文件当最新，也不读旧writer孤立文件。完整current identity为null时返回原无快照partial，不用历史文件猜当前版本。

**当前只读revision不可用**：实际Admin `projectConnector(internal=false)`明确删除config.snapshot_sync_execution；普通user/background get/list/active/syncCandidates和run输出中的connector均经该公开投影。selection_revision/authorization_revision只在内部state和四个写operation的run输出可见，后者不是当前只读权限证明。Calendar/today/thread不得调用request/claim来取得revision，也不得假设内部JSON会传到浏览器或普通read。本次按当前实际合同保留所有读者的updatedAt保守上下文；只有将来冻结artifact明确提供实际可用、服务器所有且精确cap证明的只读revision投影，并经独立审核，才可另行采用。本文不默认要求新增Admin operation。

| 消费者 | 最小变化与提交边界 |
| --- | --- |
| `today_pages` 初读/校验/校验后复查 | 都通过Admin接受identity解析，不仅比较磁盘current；保留actor/connector/auth/选择/updatedAt/凭证/日期时区前后检查与快照409。当前普通read缺独立revision，heartbeat更新updatedAt也按未知上下文保守409，再走已评审的下一正常周期/显式刷新恢复；不得凭同版本、run历史输出或sync状态忽略冲突。 |
| facade `get_current_snapshot` | 返回接受版本；缺缓存可读取现有Admin快照，进程重启/另一worker成功后可恢复，不 remote Notion。返回前同样复核当前read上下文与完整identity；发生updatedAt冲突不交旧响应。 |
| `materialize_workspace`/`snapshot_store.project_thread` | facade先解析接受版本再交纯文件投影；只交当前选择求交结果，原私有权限/路径/无body不变。结束前复核归属、授权/选择/updatedAt/凭证及current identity；冲突清理本轮thread投影并失败，不把旧版本交给下一turn。 |

未来只读scope/auth revision若具备真实合同再由主Agent独立批准，并在Notion正式稿写明具体来源/判断/恢复；当前所有read/today/thread和Calendar前端updatedAt未知上下文保护不放宽。Chat turn仍不执行Notion扫描/同步，缓存缺失恢复只读Admin，不扩大Agent正文权限、不热替换已有turn。凭证projection、Read Hook、Runner/TMPDIR和任务状态机不修改。

## 6. 发布边界与尚未闭合项

Admin目前已写0074 actor锁函数/精确capability草案及默认关闭claims gate；这不是正常库已迁移或生产claims已开放的证明。release须expand已验证capability→Dream兼容read/strict新写代码（claims仍关闭）→证明全部旧Dream writer和旧Admin ingress退出→全入口旧写enforcement→启用新claim。gate关闭/配置缺失/能力不匹配fail closed，不fallback旧save/transition，不触发runtimeDDL或SQLite。

ownerless legacy syncing仍返回 `NOTION_SYNC_LEGACY_OWNER_UNRESOLVED`；本仓不按时间/PID清状态，需明确drain证明和Admin允许的显式恢复回执。当前正常账户已有成功快照无需本proposal修改。待主Agent提供published artifact、Admin测试完成、root方案评审和运营发布事实；本文不自行启动/发布依赖，不向其他用户任务发消息。

## 7. 必须由 Luna 执行的完整技术旅程

| 旅程 | 断言与入口 |
| --- | --- |
| 精确DTO/能力/权限 | 新四严格字段/安全整数/时间/status绑定、确切hash及缺cap failclosed；旧21reads兼容；request双bearer，renew/finish无user bearer；生产request_auth注册与原receipt |
| 三种入口 | 公开manual sync、非空resources/select→首次sync、既有scheduled sweep共用同一builder和finish；manual busy为明确409、retry仅服务器时间差、缺retry不猜、无新claim/构建；空范围不sync并原子清identity；数据库选中包含page索引 |
| lease与并发 | 两worker唯一claim、manual busy、健康长同步串行heartbeat、不误接管；Admin clock可控过期后高fence接管；旧成功/失败/取消全拒绝；范围/授权/actor/凭证A→B→A |
| 未知/cancel/LKG | claim和renew原receipt、返回旧claim必须renew、finish提交响应丢失恢复；absent未知不重发；cancel中断自建CLI、单终止结果；renew拒绝/预算耗尽无再scan/failed；policy最新revision不被旧run覆盖 |
| 先commit后缓存/全部读者 | Admin拒绝finish不写缓存；Admin成功但缓存失败从Admin恢复；不同process/restart缺缓存；旧迟到写V1而Admin currentV2；Calendar/facade/thread都只交接受identity；普通read实际去除executionJSON且不调用claim取得revision；heartbeat updatedAt变化保守409/恢复；fetched_at与last_synced_at错配、完整身份错配/缓存损坏/路径或symlink拒绝；empty/partial不伪正常 |
| 原业务回归 | backend既有Notion DTO/store/router/snapshot/scheduler/today/runtime投影与正文权限旅程；前端已greenCalendar三份完整旅程仅在新增后端影响时重复；不复制Admin状态机作为证明 |
| 文档与清理 | 历史完整字节保存；PRD骨架、正式3图、matrix一致；Markdown inventory/引用/Mermaid/diff check；只清本轮具名隔离fixture/端口/进程，保留正常服务和数据 |

Dream provider-free tests可用真实HTTP serializer和DI受控clock验证消费者，但不能替代Admin实际PostgreSQL并发/原子合同回执。跨项目必要能力未发布、旧writer drain未知或必需旅程失败时不宣称永久恢复完成。任何正常业务验收须主 Agent按仓库协议用指定真实账户/正常服务另记，本阶段没有真实写入或模型调用。

## 8. 主 Agent独立审核修订（未开放生产门禁）

- R1：删除内部execution JSON可供普通只读提交检查的假设。已按实际public投影明确当前read/today/thread保留updatedAt；未来revision仅在已冻结、实际可读、精确cap证明的合同下另审。实际persistSnapshot的fetched_at→last_synced_at绑定已补入完整identity。
- R2：补NotionSyncBusyError与仅本域router映射所有权、服务器时间差Retry-After、缺retry安全busy、现有Settings最小code反馈及保存范围后首同步的真实步骤反馈；不扩共享AdminDataError。

仍仅本文改动，所有production/前端/测试/历史/folder未由本worker修改。等待精确Adminfreeze和主Agent复核，不以本文修订宣称代码门禁已开放。

## 9. 冻结合同与编码影响（2026-10-07）

主 Agent 独立评审现已批准编码，消费固定 `output/notion-sync-ownership-dream-20261007/admin-artifact/` 的 revision30 产物，不追随 Admin 全局 head。来源、文件摘要及四完整 descriptor 由该目录 `artifact-provenance.json` / `admin-four-operation-contracts.json` 保存。精确 schema `dream.notion-sync-ownership.v1` v1 的摘要为 `a54b947c69ea0f129d22fd440c3a9f5694026ac0977adef2d5b09a97d7a9e993`；request/claim/renew/finish 摘要分别为 `d020bdae89d51eef867e1337d6006081f6ba6b7a7560c4a4442b5e1461398fa3`、`a2e95601c0dcb2c0c010931bbe7ab2afb4e4f6000847fe0fb92ddb819ce432cc`、`f15c16e243d7640fb02401cf21d1fc8584628ef307da3f8814c9a6d445bb1719`、`885e17ff0feeb4372e735d988608e9380dd72249892f69753b00165045742877`。旧21 descriptor保持原值。

本轮文件所有权按§2，保留当前develop基线和既有dirty日期/操作增量；Calendar frontend/Calendar现行文档由原worker负责。代码阶段复用现有router、Store、Admin exact gate/receipt、canonical builder、actor私有文件安全检查及CLI取消，没有新增schema/调度服务。测试fixture仅在backend/tests依赖注入新四真实DTO响应；Admin实际DB原子/并发证明仍以依赖任务实际9/13旅程回执为准，Dream fixture不得冒充并发证明。

当前正常Admin公开能力目录读取成功且business writes=0，但新四operation及该schema全部缺失、exact=false；回执为 `output/notion-sync-ownership-dream-20261007/normal-capabilities-read-final.log` / `.exit.log`。因此源码接入和隔离技术验证不等于正常自动恢复已生效；新写缺cap fail closed，旧只读/LKG合同兼容。claims开启与全部旧writer drain尚未证明，本轮不正常DDL、不启停服务、不按age清owner、不触发真实sync/select/body。

R2最小本域错误已获独立批准：仅resources.replace响应已确认后，首次同步busy/失败在原安全HTTP detail追加严格布尔 `selection_saved:true`；replace未知、manual sync不标。busy为409 `detail.error_code=NOTION_SYNC_BUSY`，合法服务器时间差才有Retry-After。Settings叶子由前端作者实现，正式Notion稿同步正常/异常/状态及旅程；该错误不扩共享AdminDataError、不返回伪synced或rawexception。

首次实际消费者失败由Admin依赖验证报告：select首次sync抛NotionCredentialError。原因是本轮_credential_identity把st_ctime_ns当授权身份，但真实CredentialStore读取会chmod600，未改变凭证也推进ctime；这是生产实现缺陷。修复为复用有限大小、O_NOFOLLOW的私有文件读取，比较文件内容摘要及dev/inode/size/mtime，摘要不输出、不持久化。sync/get_current/today/materialize统一使用该身份；真实CredentialStore文件的完整成功/重复读取旅程未mock身份，待Luna复测。

另补取消与续租预算交叉：每次续租记录本进程deadline/实际completed_at；取消扫描后等待原HTTP/receipt结束，完成已超预算或结果异常则丢失执行许可，不提交failed/cancelled。shield只保留有限请求所有权，不能豁免预算；Dream DI交叉测试和Admin真实入口验证均待实际回执。

## 10. 源码冻结候选与待执行验证

本轮实现候选使用§9精确四pin，strict nested metadata DTO、immutable run context绑定、process UUID、request/claim→初renew→原builder＋串行heartbeat→单finish、实际预算清理及接受后缓存已完成编码。get_current/today/thread均通过严格接受版本解析，缺缓存复用旧Admin只读，生产消费者无load_current或publish_current旁路。原低层current文件/旧21描述符仅保留兼容边界，本轮sync不调用旧snapshot.save、sync-snapshot.save、started/terminal patch。

新技术旅程文件backend/tests/test_notion_sync_ownership.py覆盖公开select/manual、scheduled实际facade、busy及selection_saved准确错误、缺cap旧读兼容、finish拒绝LKG、cache失败只读恢复、嵌套未知body/config拒绝、opaque version路径、选择Thread投影、初renew拒绝、取消等待与超预算交叉、串行heartbeat、原user/background receipt及strict DTO。同步修正原router/snapshot/today/scheduler fixture，使它们输入当前真实DTO与Admin接受identity；不放宽生产校验适配旧fixture。

scheduler统计语义：candidates为候选数量；attempted为已提交Admin claim的候选次数；succeeded仅synced=true；failed仅实际错误。busy/not_due的claim会计入attempted，但没有构建或成功/失败执行，succeeded/failed均不增加，不能把claim请求数称为已执行同步次数。

核心生产/17case冻结后，按主Agent指示另建backend/tests/test_notion_sync_cancellation_edges.py（3case，不修改并行runner读取中的core文件），覆盖扫描中第二renew超预算取消、已发claim取消等待原返回不构建/终止、已提交finish在途取消等原结果且下一读恢复。只通过测试DI有限delay/Event与真实DTO/私密凭证执行；无真实业务写入或Admin状态机副本。该额外文件与原新旧旅程均已交专属Luna，回执尚待返回，本记录不宣称通过。

PRD及正式交互稿已保存前文完整字节历史，正文补桌面/窄屏骨架、正常/异常/状态3 Mermaid及矩阵、实际发布未闭合事实；受影响file headers/folder已同步。README由主Agent协调共享文本。此时本worker没有运行测试、构建、静态或文档检查，不记录虚构exit0。建议Luna使用已有backend/.venv与pytest，首先新ownership+原AdminDTO/router/snapshot/store/scheduler/today完整集合，再相关Notion Runtime/服务投影回归；前端新增Settings叶子与原Calendar63由同一Luna在后端freeze独立复核后执行。命令、退出码、首次失败/修复/复测与生成物清理待实际回执追加，不能把该冻结候选称为验证通过。

## 11. 首次Luna回执、分类纠正与fixture修复

首次实际回执为 `output/notion-sync-ownership-dream-20261007/validation/backend-validation-receipt-20261007.md`，原日志与原分类保留。backend cwd首批八文件命令exit1：83 passed、16 subtests、2 failed；相关Notion Runtime/服务回归exit0：52 passed、122 deselected、5 subtests；compileall exit0。ruff探测exit127（现有环境无可用工具），不能称lint通过，不安装无项目必要工具。新取消三例原命令collection exit2，额外PYTHONPATH=tests诊断exit0、3 passed，但原命令仍需修复复测。

| 首次失败 | 实际合同及重新分类 | 最小修复 |
| --- | --- | --- |
| ExecutionJourney要求renew/finish HTTP Authorization为None | 实际AdminDataClient._request在access_token=None时仍发送服务Bearer；有user token时Authorization为actor、另有服务header。service-only是没有user bearer，绝非没有HTTP认证。本次收到synthetic服务token正符合生产合同；原回执归为生产/合同失败不准确，应为新增测试断言缺陷 | 严格断言配置的fixture service token，同时明确不等于actor token，保持所有user/service分离校验 |
| TestNotionStore期望fixture.service.access.token | 原tests/conftest自动替换默认OAuthClientCredentialsTokenSource，而新Notion边界显式注入synthetic服务provider，真实Client优先使用显式DI；两测试前置值不一致，应为fixture provider/断言不一致，不是生产泄露user bearer | fixture统一由state.service_token供provider，两个旅程均严格检查该已配置值并拒绝actor token；不改共享conftest或生产client |
| 新三例独立命令不能import sibling | 测试未按现有tests包路径引用，collection尚未进入业务代码，属于harness导入缺陷 | 改为tests.test_notion_sync_ownership，与正常项目命令一致，不靠额外PYTHONPATH作为最终通过方式 |

该阶段只改变backend/tests的provider、断言、导入、headers/folder及本文，生产源码继续冻结。本人没有运行修复后的机械验证。复测仍由Luna执行原八文件完整首批加新三例原命令，记录新exit/结果；已通过52项回归因无生产变更无需重复。Admin实际P1和发布能力/drain边界仍以主任务最新实际回执为准，本文不扩大原技术证据范围。

## 12. Admin 实际消费者联调回执

主 Agent 读取依赖任务 `01a11331-2830-7220-bf91-4a144acfd62f` 的实际验证正文。修复后完整 consumer lane **6/6，exit0**：真实 Dream facade/DTO/cache 经真实 Admin 生产 Route Handler 与具名隔离 PostgreSQL 验证首次分页同步、Calendar/Thread、busy/LKG、上游失败、丢失 finish 响应后的原 receipt 恢复、重启缺缓存与旧版本晚写、真正凭证变化，以及续租取消超预算无 finish。前后11文件源码指纹稳定。首个 ctime 误判失败和独立续租限定通过仍保留，没有覆盖原失败。

公开路由/worker lane 首次 **exit1**，原因是隔离账户缺少时区，worker未执行；通过现有 preferences.save 的真实 DTO/route 配置后，独立 lane **2/2，exit0**。覆盖选择失败后回读与显式重试、禁用策略后手动同步、busy，以及真实后台 worker 将1页索引刷新为2页再经公开 Calendar读取；前后12文件指纹稳定。明确注入的 Notion metadata provider、受控时钟和 synthetic credentials 仅位于允许测试 harness，没有正常 Notion或模型调用。两个 lane 各自绑定源码指纹，不能冒充同一时间的单次8例或正常业务验收。

来源原始日志位于 Admin 仓库 `output/notion-sync-ownership-20261007/` 的 `dream-consumer-postfix.log`、`dream-public-worker-rerun.log`；完整分类与命令见该仓库 `docs/verification/notion-sync-ownership-20261007.md`。此前 Admin 公开入口9/9、发布边界13/13和2238单元通过保持原验收范围。依赖任务已确认清理全部自有进程、隔离cluster/runtime/fixture，保留安全日志；正常数据库、用户服务和记录未修改。

这些实际联调关闭首次 consumer P1 和取消超预算行为的技术缺口，不替代 Dream 本仓修复后的完整pytest/文档回执。正常capability目录仍缺新四操作及schema，旧writer drain和claims启用仍未证明；整体目标保持未完成。

## 13. 本仓后端实际复测与范围

专属 Luna 已执行原八文件核心批次 **83 passed、16 subtests passed，exit0**，独立取消边界三例的正常项目命令 **3 passed，exit0**，扩展 `compileall` **exit0**。此前相关 Notion Runtime/服务投影回归 **52 passed、122 deselected、5 subtests passed，exit0** 因生产代码未再改变而保留，不无理由重复。源码和 fixture 指纹、完整命令/输出/退出码均保存在 `output/notion-sync-ownership-dream-20261007/validation/backend-validation-receipt-20261007.md` 及同目录 `.command/.log/.exit.log` 文件。

首次汇总数字另有回执笔误：实际原批次是 **81 passed、2 failed、16 subtests passed**，共83用例；§11及原回执先前的83 passed加2 failed属于当时误报。Luna已通过实际首次输出和正常collection核对并追加更正，没有删除两条失败或少跑用例。两处服务认证断言和独立测试导入前置修复后，同一完整批次及三边界均通过，生产认证未降低。

固定消费 artifact 与 Admin当前正式文件只读比对 **10/10，exit0**：capability合同、四operation descriptor及五个原文件SHA一致，未追随全局head。Notion正式稿当前总计4图（原1图加本次3图），已在一次本机Chrome和现有Mermaid运行时实际parse/render全部通过；Calendar的当前3图复用既有实际渲染回执，内容身份另行检查。历史SHA、PRD骨架、双语README及作用域引用检查由同一Luna最终收口。

`ruff`探测 **exit127**，现有环境无可用工具，未安装额外环境或冒称lint通过；语法检查与全部上述功能回归已实际通过。文档checker首次只查看前20行，漏掉 `request_auth.py` 既有第28–30行的Input/Output/Pos，这是检查脚本边界缺陷，不能称生产文件头缺失；源码无需为此重复增加说明或变更认证。原exit1保留，按完整前导注释区修正checker后再记录最终回执。

本阶段没有启动或停止正常服务、写正常数据库、读取真实凭证、调用真实Notion或模型。pytest已退出，临时资源由测试上下文清理。前端71及旧设置overview由另一Luna独立验证，不能用本后端通过替代；整体目标仍由正常发布和必需前端/文档门禁共同约束。

最终文档回执补充：checker首轮实际只读取前14行，§13此前记为20行不准确；原误报exit1保留。按完整前导注释修正检查脚本后，同作用域16文档/21源码清单 **errors=0、exit0**，`request_auth.py`未为检查器改变。当前Notion4图已实际parse/render；Calendar3个图块SHA均与前阶段真实渲染回执一致，identity命令exit0。所有权前历史PRD/design全文SHA分别为 `974fd07e99a09ecb908b9b74989392e687387231be44b3a5e22482c642a47a1a` / `ec9bcb46a9833a21dbda971432a471a2ccd72f33f014004fb54f7361f151a38d`，没有覆盖历史。前端最终完整71及受影响11、旧overview1也已独立通过，详见[前端最终回执](./notion-calendar-sync-refresh-20261007.md#145-r2-完整旅程最终实际回执)；两端技术通过仍不替代正常发布。

后续文档校正已通过：[Calendar执行记录§15](./notion-calendar-sync-refresh-20261007.md#15-calendar-当前正文与后端状态同步纯文档新四图已实际检查通过)将旧锁/跳过诊断与当前归属源码分开，保存另两份完整历史；当前Calendar正式稿改为四图（当前正常/异常/state及一幅历史异常），四图已由Luna重新实际parse/render通过，作用域122引用0缺失、历史身份及diff检查exit0。上述较早三图回执不再作为当前四图通过证明；Notion四图内容未改，原实际回执继续适用。
