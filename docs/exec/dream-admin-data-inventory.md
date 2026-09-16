<!-- [Sync] 2026-09-16: retire zero-caller Dream Deck/Voice/default/version SQL after strict Admin DTO adoption; baseline rows remain historical. -->
<!-- [Sync] 2026-09-15: close Story Workspace Guidance persistence through Registry115 and record the current source scan. -->
<!-- [Sync] 2026-09-16: close managed-MCP persistence through Registry134-147 and retain the baseline row as history. -->
<!-- [Sync] 2026-09-15: close eleven Story Workspace catalog routes through Registry114 and record the corrected current scanner. -->
<!-- [Sync] 2026-09-15: close three current-user picture-history reads through Registry103 and record the fresh scanner. -->
<!-- [Sync] 2026-09-15: close public local-data import and first-login writes through Registry101 and record the fresh current scanner. -->
<!-- [Sync] 2026-09-15: close production SystemConfig calls through registered80 and record the fresh current scanner. -->
<!-- [Sync] 2026-09-15: close public Reflections config calls through registered83 while retaining the ownerless task reader. -->
<!-- [Sync] 2026-09-15: close Agent prompt recent Session reads while retaining tools/background consumers. -->
<!-- [Sync] 2026-09-15: three public default resolvers share registered Admin ensure; Deck Plugin role reuses current profile. -->
<!-- [Sync] 2026-09-15: map actual77 fail/envelope consumer preparation without subtracting retained SQL. -->
<!-- [Sync] 2026-09-15: consume registered Run cancel with original reason/full result and bounded receipts; other lifecycle gaps remain. -->
<!-- [Sync] 2026-09-15: record actual SystemConfig callsites and credential ownership without replacing an unpublished domain. -->
<!-- [Sync] 2026-09-15: retain original launch commit ordering while candidate operations remain unregistered. -->
<!-- [Sync] 2026-09-15: close content/download Thread ownership and retain missing SystemConfig/default capabilities. -->
<!-- [Sync] 2026-09-15: close public Preflight GET independently of Workspace/SystemConfig/Run dependencies. -->
<!-- [Sync] 2026-09-15: consume PF execute/original receipts without claiming the default-dependent POST is DB-free. -->
<!-- [Sync] 2026-09-15: consume full Run read/create/retry; other lifecycle and default dependencies stay open. -->
<!-- [Sync] 2026-09-15: prepare launch metadata/source seam without counting retained production SQL as migrated. -->
<!-- [Sync] 2026-09-15: retain Runtime/shared-file technical regression and Gateway ownership gaps. -->
<!-- [Sync] 2026-09-15: record complete Admin Deck list modes and remaining SQL source candidates. -->
<!-- [Sync] 2026-09-15: record Admin-owned Deck detail and unchanged legacy Memory projection. -->
<!-- [Sync] 2026-09-15: index five Admin Deck writes, shared schema gate and closed deletion feedback. -->
<!-- [Sync] 2026-09-15: map public Voice four replacements and retained database dependencies. -->
<!-- [Sync] 2026-09-15: map all nine social replacements and retired old database paths. -->
<!-- [Sync] 2026-09-15: record catalog synchronization without closing outstanding domain migrations. -->
<!-- [Sync] 2026-09-15: map three public refs consumers and remaining Runtime/install dependencies. -->
<!-- [Sync] 2026-09-15: map Browser async snapshot ownership and remaining business verification. -->
<!-- [Input] Dream baseline Python AST and follow-up production rg scan. -->
<!-- [Output] Per-file DB/transaction/permission evidence and pending Admin API mapping. -->
<!-- [Pos] Dream migration inventory; Admin owns the eventual canonical API contract. -->
<!-- [Sync] 2026-09-15: record two public preference consumers without closing system/first-login/background database domains. -->
<!-- [Sync] 2026-09-15: record public Deck content-version replacement while retaining other Deck/Voice/Runtime dependencies. -->
<!-- [Sync] 2026-09-15: add public Agent Thread reads and SDK-native Session writes to actual consumer mappings. -->
<!-- [Sync] 2026-09-15: distinguish baseline scans from actual resource/Chat/Workflow/user-turn/Session consumer mappings. -->
<!-- [Sync] 2026-09-14: initial exhaustive candidate scan; candidates are not all reachable production SQL. -->

# Dream 生产数据入口清单

## 2026-09-16 managed-MCP 关闭证据

| Dream 文件与入口 | 原访问数据 | 事务/并发要求 | 目标 Admin 模块与接口 | Dream 替换方式 | 验收证据 |
|---|---|---|---|---|---|
| `backend/claude_mcp/repository.py`、`backend/claude_mcp/credentials.py` 与 `backend/script/import_claude_mcp_config.py` | Server、App settings、encrypted credential、discovery snapshot、import receipt、schema capability；legacy existing-thread enumeration | actor/workspace 过滤、CAS、credential/snapshot invalidation、import lock、单事务、未知提交；兼容同步只能显式注入 thread provider | Admin `ManagedMcpRepository` + Registry134-147 `managed-mcp.*` strict Zod DTO/typed Drizzle | `AdminManagedMcpRepository` strict Pydantic DTO；公开OAuth、Agent `server-persistence`、import OAuth principal；兼容模块移除隐式 Dream DB fallback | managed-MCP/MCP Apps `184 passed, 3 skipped`；auth/server `195 passed, 4 subtests`；AST 554 modules/80 production entries/19 driver modules/38 legacy helpers/0 parse errors，managed-MCP 相关入口无数据库访问；两仓artifact SHA `9cd4be42914d338d4180c5c85e969b7a452f93570318cc23366b24e7a5cbe5a6` |

下方大表保留 baseline AST 结果用于追溯；其中 managed-MCP repository 的
`production / 28` 行描述迁移前状态，不能解释为当前生产实现。

当前 source-only 机器回执见
[`dream-db-closure-after-managed-mcp-registry147-source-only.json`](admin-auth-data-verification/dream-db-closure-after-managed-mcp-registry147-source-only.json)。
它是源码候选清单，不替代后续完整生产入口运行验证。

共享AdminClient已同步catalog readiness、refresh与operation广告检查；领域HTTP保持并发且未知提交原receipt语义不变。该改动只关闭metadata竞态，不减少其它生产DB迁移清单。

## 背景与问题

扫描 baseline `7d38715c` 的 Python AST：DB imports、SQL 字符串片段、connection/execute/commit/rollback/UOW 调用。动态拼接、工厂和路由依赖仍需 `rg`/调用链复查；`execute` 同名非 DB 调用也可能被列为候选。不得将候选清单当作已完成迁移。机器清单包含完整函数签名与各调用行号：[JSON 清单](dream-admin-data-inventory.json)。

## 目标与边界

Admin 接口列仅在规范实际就绪后填写。带锁/CAS/ON CONFLICT/Savepoint 的操作必须在 Admin 单个领域事务执行，不能拆成无一致性 HTTP 请求。FS 和 Runtime 业务留 Dream，DB metadata/权限与持久化搬 Admin。显式 importer/maintenance 与生产入口单列。

## 概念与规则

actor 参数提示仅是扫描证据，不能证明权限充分；Admin 必须依据签名主体与服务身份校验实体归属，不能使用任意 user_id 头。非幂等写遵循 Admin 请求 ID 与未知提交恢复契约。

## 当前源码入口映射

此表记录实际消费者范围，发布capability仍由Admin逐请求执行检查。技术合同通过不等于正常本机真实业务验收；完整startup/pool/159事务及其它生产入口继续开放。

Registry115将公开Guidance的Run/Workspace/Thread权限、幂等判断和`chat_message`写入替换为`AdminStoryWorkspaceGuidanceData`。Dream只保留Admin成功后的same-Thread Runtime投递及202映射；业务replay不重复投递，未知写只读取原receipt，投递失败不撤销已经提交的命令。`guidance_service.py`不再导入database或包含SQL；`story_workflow_application.py`移除旧Guidance database方法。当前[source-only scan](admin-auth-data-verification/dream-db-closure-after-registry115-source-only.json)读取545个Python模块：78个production entry、49个SQL模块、452个SQL literal、27个driver/database import模块、50个legacy helper call、392个connection/transaction call、29个Admin consumer模块、133个operation name，parse errors为空。相对Registry114减少1个production entry、1个SQL模块、2个SQL literal、1个driver/import模块和2个legacy helper；新增两个模块来自consumer与测试，connection/transaction计数不变。该结果证明本切片源码关闭，不代表剩余数据库全域关闭。

Registry114将`story_workspace.py`中的Workspace get/patch、Story/Character/Scene三组list/detail/patch共11个公开入口替换为`AdminStoryWorkspaceCatalogData`。旧`_story_db/_owned_row/_patch_owned_row/_paginate_query`及动态SQL/sort/filter policy从生产路由删除；公开DTO、页面排序/过滤/分页、详情关系和错误状态由provider-free路由测试保持。Admin使用closed Zod DTO、Service和typed Drizzle Repository处理权限与事务，两个write使用原receipt恢复，一个read无receipt。当前[corrected source-only scan](admin-auth-data-verification/dream-db-closure-after-registry114-source-only.json)读取543个Python模块：79个production entry、50个SQL模块、454个SQL literal、28个driver/database import模块、52个legacy helper call、392个connection/transaction call、29个Admin consumer模块、132个operation name，parse errors为空。相对Registry111扫描减少1个SQL模块、9个SQL literal、1个driver/import模块、1个legacy helper和11个connection/transaction call；该差异只证明本切片源码关闭，剩余候选必须继续按调用链迁移。

阶段31只读源码扫描增加无SQL的run_data模块：298scanned/48SQL模块/513字面execute候选、16driver模块、35legacy import模块与121直接helper Call候选，exit0/parse_errors=[]。旧application方法仍供其他调用者使用，默认Workspace及动态Repository/stdio仍未迁移，不能以三个公开领域调用替换推断这些SQL已退出全域。阶段29的297扫描是当时历史，以下原baseline与现有候选表保留各自范围。

阶段32新增无SQL的launch metadata模块，扫描299模块，其余48/513/16/35/121保持，parse_errors=[]/exit0；source seam仅类型准备，旧endpoint未接线，原launch32条SQL候选未消失。现有Admin typed资源provider保持，policy/admission/sdk_env补跑67pass exit0作为LKG/revision/safeint/精确内存/后台隔离/lease技术证据；startup/health/SystemConfig/selected model/GatewayCLIkey另行待迁移，不混记为provider缺口。

| 生产入口 | 实际Admin领域合同/消费者 | 已替换范围 | 保留的迁移依赖 |
| --- | --- | --- | --- |
| `agent_factory`资源composition | [resource_data](../../backend/services/admin_data/resource_data.py)：resource-policy.read、resource-observer.publish | 独立provider/observer sink无PG；read/publish/close同活动锁，shutdown后台owner和Factory后关闭HTTP | 全域startup/其它DB与正常业务验收仍开放 |
| 公开Deck完整列表 | [deck_list_data](../../backend/services/admin_data/deck_list_data.py)：deck.list | published false/true两mode无DB；原counts/author字段/owner int/ISO，Admin过滤排序装饰，单read | 创建/default/provision/install/后台与正常业务仍待；列表原路径无default/文件依赖 |
| 三公开default resolver/DeckPlugin role | [shared deps](../../backend/routers/deps.py)、既有current_profile | Story/Deck binding/DeckPlugin共享empty Admin ensure、原textID/服务器WS/Scope/unknown；role复用OAuthread/canonicalID/rawrole，三resolver无DB | 其余binding/control-plane provider、background/internal输出DB和正常验收仍待；目录77不替代全链 |
| 公开Preflight读取/领域执行 | [preflight_data](../../backend/services/admin_data/preflight_data.py)：workflow-preflight.read/execute、独立original receipt reader | GET无default/旧service/SQL；POST领域操作交Admin，raw JSON/原202与17字段、actor-Deck-revision/three schemas、显式同ID三态receipt/no resend；generic receipt不改 | POST default已使用registered76 Admin ensure；隐藏source仍待；目录80不替代全域Run/launch或正常验收；revision descriptor元数据差异待Admin修正 |
| 公开Run读取/创建/重试/取消 | [run_data](../../backend/services/admin_data/run_data.py)：workflow-run.read/create/retry/cancel | 领域操作无旧service/SQL；原200/201/28required fields/lifecycle/微秒/key/source、actor/Workspace/ID或key-retry-source、two exact schemas/hash、显式generic原两态receipt/no resend；原error mapping共享 | 四个入口default已使用registered76 Admin ensure；guidance/confirmation/launch/Run其它持久化及正常验收仍待；原SQLite行锁并发skip保持，不宣称PG验收 |
| 公开Story Workspace Guidance | [guidance consumer](../../backend/services/admin_data/story_workspace_guidance_data.py)/[Runtime dispatcher](../../backend/services/story_workspace/guidance_service.py)：story-workspace-guidance.submit | Registry115 current OAuth；Admin owned Run/Workspace/Thread、confirmed/failed、immutable message与receipt；Dream only-new same-Thread dispatch、原202与best-effort failure；无Dream SQL | 正常Admin/Dream/Runtime真实业务验收仍待；其它Workflow/artifact数据库入口继续迁移 |
| 公开Workspace文件 | [workspace_data](../../backend/services/admin_data/workspace_data.py)：chat-thread.get；[system_config_data](../../backend/services/admin_data/system_config_data.py)：user-system-config.get | content/download先Thread ownership再配置/Mode/path/FS；list/upload/delete/move参数后先配置再FS；无配置fallback，保留404/409/安全503 | 其它文件管理metadata与正常共享文件/CLI验收另行 |
| 隐藏launch来源与dispatch | [launch_metadata_data](../../backend/services/admin_data/launch_metadata_data.py)：三registered75 types/原source seam；原[infrastructure](../../backend/services/story_workspace/dream_launch_infrastructure.py)待接线 | strict source/claim真假/10Context/raw JSON/finish、原command约束/callsite source IDs与fingerprint、current actor、同UUID两态receipt/no resend已技术准备；原application/builder/endpoint/router未变 | 生产endpoint只传actor/Workspace字符串，未选择新adapter；原source/claim/finish/prepare/Voice/failure SQL仍pending；launch75公开PG剩余37待primary，不声明完整PG/normal launch；default Workspace仍未注册 |
| 公开Deck详情 | [deck_detail_data](../../backend/services/admin_data/deck_detail_data.py)：deck.detail | 单Admin owned aggregate；closed fields/owner int/ISO/原纯Memory解析/URL与nestedDeck匹配，无DB | Admin voiceRow emptytext→null投影差异需修正；其它create/default/install/内部helper继续开放 |
| 公开Deck mutation | [deck_mutation_data](../../backend/services/admin_data/deck_mutation_data.py)：update/delete/toggle-publication/collect/sync-parent | 五公开写无DB；原结果/错误/闭集删除reason、four schemas、单Admin事务与unknown原UUID | create/default/provision、全局install/文件证据与原内部/fixture helper SQL仍开放 |
| 公开Voice mutation | [voice_data](../../backend/services/admin_data/voice_data.py)：create/update/delete/collect | 四路由无DB；four exact schemas，requirednullable/optional/rawMemory，原errors/unknownreceipt | 同模块Deck其余read/create/default/provision/plugin FS evidence与internal/fixture四helper SQL仍开放 |
| 公开好友与邀请码 | [social_data](../../backend/services/admin_data/social_data.py)：九actual operation | 全部九路由无DB，原int/null/ISO/errors/images/unknownUUID；旧database九helper-before-I/O拒绝 | 其它daily-picture/import/System/后台SQL与正常业务验收仍开放 |
| 公开Deck Claude Plugin refs | [deck_refs_data](../../backend/services/admin_data/deck_refs_data.py)：list/prepare/replace | 两公开GET/PUT无DB；无path的metadata→原artifact/CLI检查→source-bound Admin TX；原enabled/ISO与unknownUUID | 全局install/catalog/operation、serveradapter、runtimepacking、voice-memory/analysis仍有DB依赖 |
| Browser session/AuthContext | [browserSession](../../frontend/app/_dream/lib/browserSession.ts)：current immutable public snapshot/CSRF | cancelled/superseded reads无状态修改；logout成功清除，failed保留；React只提交current snapshot | 正常Browser journey/真实业务与server配置仍待验收 |
| 共享身份与profile | [request_auth](../../backend/services/admin_data/request_auth.py)/[profile_data](../../backend/services/admin_data/profile_data.py)：JWT/JWKS→principal→user-profile.current | 公开Admin主体/canonical PK/strict profile；旧Dream authority退役 | Gateway subject与内部tool后台独立purpose仍需迁移 |
| 公开Chat CRUD/history/ownership | [chat_data](../../backend/services/admin_data/chat_data.py)：14 typed methods | HTTP Thread/message入口已切换，公开响应/cursor/commit后close保留 | assistant等后台消费者与Deck/settings/MCP仍有PG |
| 公开Chat Workflow上下文 | [workflow_data](../../backend/services/admin_data/workflow_data.py)：workflow-context.resolve | Admin完整provenance→immutable actor/thread snapshot，普通null不走旧PG mapper | 内部confirmation/launch及完整Run/preflight/lifecycle事务仍需迁移 |
| 公开user-turn原子预留 | [user_message_data](../../backend/services/admin_data/user_message_data.py)/[turn_persistence](../../backend/services/admin_data/turn_persistence.py)：chat-user-message.persist | server-persistence exact Thread/Run；guard/message/title单Admin事务，known复用/unknown原receipt；Factory renew/cleanup | 原内部dispatcher guard保留，CLI/Editor各purpose与其余后台persist仍未切换 |
| 公开写作Session CRUD/summary | [sessions router](../../backend/routers/sessions.py)/[session_data](../../backend/services/admin_data/session_data.py)：session.save/get/batch/list/text-list/delete | 路由无Dream DB；原metadata/state/microsecond/timezone/metrics/confirmed edit events；`session.list`另接受精确Thread-bound server-persistence prompt/tool read | Reflections后台仍有原DB入口；其他五项Session operation不接受该purpose |
| 公开Agent Thread/SDK/Session projection | [Service](../../backend/claude_agent/service.py)/[turn_persistence](../../backend/services/admin_data/turn_persistence.py)/[Session broker](../../backend/services/admin_data/session_projection_broker.py)：chat-thread.get/update-session/thread-system-config.get/session.list | resume、Session回写、fresh SystemConfig、prompt三日投影与Chat工具任意日期/正文候选使用exact server grant；broker close先drain；ContextBuilder及sessions_tool无DB | 缺owner内部dispatcher在配置边界fail closed；Reflections background及其余内部PG独立迁移 |
| 公开Deck内容版本 | [deck_versions router](../../backend/routers/deck_versions.py)/[deck_version_data](../../backend/services/admin_data/deck_version_data.py)：deck-content.state/preview/commit/history/detail | router无Dream PG；four exact schema、Admin snapshot/hash/CAS/TX，rawsnapshot/creator int/微秒、safe409/unknown原UUID；旧Dream content-version service已退役 | refs/FS/CLI evidence/Runtime consumer与其他剩余SQL边界继续单列迁移 |
| 公开用户偏好 | [preferences router](../../backend/routers/preferences.py)/[preferences_data](../../backend/services/admin_data/preferences_data.py)：user-preferences.get/save | router无Dream DB；OAuth/2schema，requirednullable/rawobject/Python numeric/原NULL merge/{}/微秒、unknown原UUIDno retry | 后台context仍待；default-voices仍本地config，Runtime purpose不管理preferences |
| 公开本地数据导入与first-login完成 | [auth router](../../backend/routers/auth.py)/[local_data_import](../../backend/services/admin_data/local_data_import.py)：local-data.import/first-login.complete | 三公开入口无Dream DB；Registry101 current OAuth、strict legacy request、四类独立解析、raw JSON、安全整数毫秒、Admin accepted counts；两write未知只查同operation原UUID receipt且不重发 | 正常Admin/PostgreSQL/真实账户导入另行验收；旧database helper定义只保留为未达生产路由的兼容候选 |
| 当前用户图片历史 | [pictures router](../../backend/routers/pictures.py)/[picture_history_data](../../backend/services/admin_data/picture_history_data.py)：picture-history.list/full | 三公开入口无Dream DB；Registry103 current OAuth、nullable ISO范围、safe limit、原普通/范围prompt差异、nullable精确时间和full原404；无actor/friend/物理selector | 正常Admin/PostgreSQL/真实账户图片读取另行验收；好友timeline/full保持独立授权领域 |
| 用户/Thread SystemConfig | [system_config_data](../../backend/services/admin_data/system_config_data.py)：user-system-config.get/patch、thread-system-config.get | Settings OAuth读写+fresh read；公开Chat单OAuth snapshot；活动turn exact grant；raw Python JSON、ten-field closed patch、no DB/default fallback；Gateway selector显式reader | ownerless内部dispatcher在配置前拒绝；正常Admin/PG/Gateway/共享FS业务验收仍待 |
| 公开Reflections分区配置与memory-init | [reflections_config_data](../../backend/services/admin_data/reflections_config_data.py)：reflections-section-config.get/save/delete；[router](../../backend/routers/reflections.py) | current OAuth三operation；save/delete unknown仅原UUID committed typed receipt恢复、单次POST；Dream保留静态default/display/五文件过滤/partial merge；memory-init顺序为Admin Thread owner→Admin custom config→路径与FS | 后台Reflections worker无OAuth或领域grant，旧config read与task/event/result数据库路径保留；正常Admin/PG/共享FS业务验收仍待 |

## 阶段40历史基线源码扫描与当时的直接 helper

本节保留 2026-09-14/15 扫描原貌，用于核对迁移差值；其中标记“现已退役”的路径不再是当前源码。当前状态以文末日期化关闭章节和最新 source-only 回执为准。

2026-09-15 fresh scanner覆盖301个production Python模块，排除tests、`backend/script`及四个明确offline schema/import/legacy模块；结果为46个literal SQL-bearing模块、506个literal SQL execute候选、16个driver/import模块、30个legacy database import模块、108个直接legacy helper Call候选，`parse_errors=[]`、exit0。相对阶段39，SystemConfig旧SQL和生产调用被删除；计数变化同时包含并行工作树改动，不能全部归因于本阶段。完整机器结果与command receipt保存在`/private/tmp/dream-admin-stage40-system-config-validation/scanner/`。这些仍是源码候选，不是生产可达性闭环。

仍有27个模块包含直接legacy helper Call候选：Story launch/agent integration、Deck/Plugin内部服务、Claude service内部dispatcher、MCP/Notion credentials、reflection/report/picture/auth路由与维护工具等。当前优先级最高的原事务组合是`story_workspace.receive_agent_story_output → agent_integration.get_or_create_default_workspace/store_agent_story_output`；它同时处理默认Workspace与Agent产物，必须由Admin单一领域aggregate替换，不能拆成独立ensure后在Dream继续SQL。

| 当前直接helper模块 | Call候选 |
| --- | ---: |
| `services/story_workspace/dream_launch_infrastructure.py`、`routers/story_workspace.py` | 2 |
| `services/deck/admin_gateway.py`、`services/deck_plugin/release_service.py`、`routers/claude_plugins.py`、`services/deck/story_workflow_application.py` | 25 |
| `services/story_workspace/dream_artifact_turn_hook.py`、`dream_auto_repair_service.py`、`guidance_service.py`、`libs/.../story_workspace_tool.py` | 9 |
| `claude_agent/service.py`、`routers/claude_agent.py` | 11 |
| `services/claude_plugin/deck_refs_service.py`、`routers/deck_plugin_binding.py`、`services/deck/defaults.py` | 5 |
| `server.py`、`routers/auth.py` | 7 |
| `claude_mcp/credentials.py`、`notion/credentials.py`、`libs/.../sessions_tool.py` | 3 |
| `reflections_agent.py`、`routers/reflections.py` | 32 |
| `routers/pictures.py`、`routers/reports.py`、`routers/voices.py` | 6 |
| `tools/session_inspector.py`、`tools/session_inserter.py` | 8 |

## 阶段41当前Reflections配置边界与源码扫描

registered83新增`reflections-section-config.get/save/delete`三项OAuth operation。公开config GET/PUT/DELETE已无Dream database call；save/delete响应未知时仅用同一OAuth查询原request ID的原operation receipt，committed typed output才确认，absent/查询失败/坏回执保持unknown且不重发。`memory-init`按Admin Chat Thread owner→Admin custom config→路径/共享FS执行。Dream继续拥有静态default、display、五文件过滤、partial merge与公开回复。后台`reflections_agent.py`没有可续期OAuth或已发布领域grant，保留唯一生产`get_reflections_section_config`调用及task/event/result数据库状态；database旧save/delete兼容符号在I/O前拒绝。

2026-09-15 fresh scanner覆盖302个production Python模块，结果为46个literal SQL-bearing模块、504个literal SQL execute候选、16个driver/import模块、30个legacy database import模块、102个直接legacy helper Call候选，`parse_errors=[]`、exit0。仍有27个直接helper模块；阶段40上表为当时snapshot，当前Reflections相关计数为`reflections_agent.py` 15、`routers/reflections.py` 11。机器结果与command receipt保存在`/private/tmp/dream-admin-stage41-reflections-config-validation/scanner/`。这些是源码候选和provider-free闭环证据，不代表正常Admin/PostgreSQL/账户/共享FS业务验收。

## 阶段42 Agent最近Session上下文边界

Admin已冻结允许`server-persistence`调用既有`session.list` v1的最小行为门禁，operation hash保持`1936970e27a8b854dd08cd785b0da6534656aa5af0e652750693f86e88860435`。Dream owner在activity锁内验证immutable actor/Thread，使用current renewed token，并在POST前匹配Better Auth、runtime delegation、runtime purpose三项identity schema；输入固定UTC当天及前两天且`include_text=false`，输出保持strict DTO顺序并拒绝正文。读取参与close drain，不触碰unknown write pending。

Service仅在首次prompt或Settings prompt变化时读取；keepalive cache hit不调用Admin。ContextBuilder删除`_fetch_recent_sessions`、`_fetch_sessions`及全部database import/调用，只渲染传入projection并按`INK_AGENT_CONTEXT_SESSIONS`截断。空projection与纯渲染错误保留empty文本；Admin/capability/grant/DTO失败在Workspace、Runner/CLI之前终止且无PG fallback。`sessions_tool.py`与`reflections_agent.py`后台Session读取仍为独立缺口，不能借Chat grant。Runtime/SSE/admission/lease/resource LKG/resume/cancel/shared FS/TMPDIR均未修改。

阶段42 fresh scanner覆盖302个production Python模块：46个literal SQL-bearing模块、504个literal SQL execute候选、16个driver/import模块、29个legacy database import模块、102个直接helper Call候选，`parse_errors=[]`、exit0；仍有27个直接helper模块。ContextBuilder的legacy database import模块归零，两个旧helper函数及调用均删除；全局helper计数受共享工作树并行改动影响，不能只按前一snapshot差值归因本阶段。机器结果与回执保存在`/private/tmp/dream-admin-stage42-agent-session-context/scanner/`，不代表正常Admin/PostgreSQL/账户/模型业务验收。

## 阶段43 Chat Session工具私有broker边界

`sessions_tool.py`删除`INK_AGENT_USER_ID`授权和`database`导入/调用，只通过neutral strict client向turn-local broker发送request ID、ISO日期与`include_text`。Chat provider固定当前`AdminTurnPersistence`的canonical actor/Thread，在共同activity lock内取得current renewed grant、匹配`session.list`及三identity schema并调用Admin。broker使用`127.0.0.1`临时端口、256-bit capability和现有Admin transport timeout/max-bytes；Phase4先停止accept并drain在途读取，再关闭keeper/HTTP。

user MCP配置只投影五个broker字段、`INK_AGENT_SESSION_RETRIEVAL_MODE`与`INK_AGENT_SESSION_FUZZY_MIN_SCORE`，并为Claude Gateway credential和Admin/BFF server-only keys写空tombstone。isolated Python bootstrap在package导入前清除继承环境，`user_mcp_stdio`入口再次只保留broker/policy，因此DB URL、actor/Thread/task ID和custom user env不可见。Story Workspace、Editor、Memory、Notion、Runtime及SSE/lease/resume/cancel/shared FS/TMPDIR路径未改。Reflections `worker-load` Session snapshot未冻结，仍是单独缺口，不能借Chat grant。

2026-09-15 current rich AST scanner覆盖514个Python模块：80个production entry、52个SQL模块、496个SQL literal、37个driver/database import模块、94个legacy helper call、457个transaction/connection call、24个Admin data import模块、88个operation name、104个nonproduction entry、166个schema-reference SQL literal，`parse_errors=[]`。相对协调方冻结的Stage42 baseline，新增三个无DB模块且`production_entries`、driver/database import module和legacy helper call各减少1；`sessions_tool.py`自身三类命中均为0。机器artifact位于`/private/tmp/dream-admin-stage43-session-tool-broker/scanner/dream-current-db-closure-scan.json`。这些是dirty-safe源码候选，不代表全部生产可达性或正常业务验收。

## Registry101本地数据导入边界

`routers/auth.py`的`/api/import-local-data`、`/api/import-calendar-recovery`与`/api/mark-first-login-completed`已删除legacy `database`导入和三个helper调用。前两项把旧localStorage内容规范化为闭合Session、Picture、Preferences、Report DTO，并通过同一个`local-data.import`领域事务提交；first-login使用独立幂等`first-login.complete`。主导入的类别解析相互独立，calendar recovery非法时保持固定400，Report缺失旧时间字段时使用同一请求时钟。两项write的响应未知时只读取同operation、同OAuth、同request ID的原回执，不重发，也不回退Dream PostgreSQL。

2026-09-15只读scanner覆盖310个production Python模块，排除tests、`backend/script`及四个明确offline schema/import/legacy模块；结果为46个literal SQL-bearing模块、504个literal SQL execute候选、16个driver/import模块、24个legacy database import模块、70个直接legacy helper Call候选，`parse_errors=[]`、exit0。`routers/auth.py`不再出现在legacy import/helper列表；`database.py`中的`import_user_data`与`set_first_login_completed`定义仍作为兼容源码候选保留。计数包含共享工作树并行改动，不能把全量差值归因于Registry101，也不代表正常Admin/PostgreSQL/账户导入验收。

## Registry103当前用户图片历史边界

`routers/pictures.py`的普通列表、范围列表与按日full入口已删除legacy `database`导入和三个helper调用。普通/范围入口共享`picture-history.list`，Dream把空白日期规范化为null并以canonical `YYYY-MM-DD`和非负safe limit构造闭合DTO；普通列表保留null prompt到空字符串映射，范围列表保留nullable prompt。full入口使用`picture-history.full`并把null或空图映射为原`404 Picture not found for this date`。两项均为current OAuth read，Admin从principal确定owner；capability、scope、transport与DTO失败不回退Dream PostgreSQL或好友操作。

2026-09-15只读scanner覆盖311个production Python模块，结果为46个literal SQL-bearing模块、504个literal SQL execute候选、16个driver/import模块、23个legacy database import模块、67个直接legacy helper Call候选，`parse_errors=[]`、exit0。`routers/pictures.py`不再出现在legacy import/helper列表；三个database helper定义仍作为兼容源码候选保留。相对Registry101 snapshot只把本文件的一项legacy import与三项helper调用归因本阶段；其它共享工作树计数不据此解释，也不代表正常Admin/PostgreSQL/账户图片业务验收。

## baseline逐文件扫描

下表SQL数、函数行号与初始接口状态保留baseline扫描事实；当前替换状态以本稿上表及[逐阶段执行回执](dream-admin-auth-data-plan.md)为准。

| 文件 | 范围/SQL数 | 数据表 | 事务与并发证据 | 身份参数证据 | 阶段1初始迁移依赖 |
| --- | --- | --- | --- | --- | --- |
| [backend/agent_factory.py](../../backend/agent_factory.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/admission.py](../../backend/claude_agent/admission.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/context_builder.py](../../backend/claude_agent/context_builder.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/resource_policy.py](../../backend/claude_agent/resource_policy.py) | production / 1 | system_settings | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/resource_postgres_sink.py](../../backend/claude_agent/resource_postgres_sink.py) | production / 3 | SET, claude_agent_resource_snapshots | L213 ClaudeAgentResourcePostgresSink._write_sync: ON CONFLICT | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/service.py](../../backend/claude_agent/service.py) | production / 4 | chat_thread, decks, workflow_runs | 详见 JSON 调用线索 | 625,668,733 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/thread_pool.py](../../backend/claude_agent/thread_pool.py) | production / 1 | the | 详见 JSON 调用线索 | 315 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_agent/tool_confirmation_store.py](../../backend/claude_agent/tool_confirmation_store.py) | production / 3 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_mcp/credentials.py](../../backend/claude_mcp/credentials.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_mcp/driver.py](../../backend/claude_mcp/driver.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_mcp/identity.py](../../backend/claude_mcp/identity.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_mcp/repository.py](../../backend/claude_mcp/repository.py) | production / 28 | OF, SET, dream_mcp_credentials, dream_mcp_discovery_snapshots, dream_mcp_import_receipts, dream_mcp_servers, drizzle.schema_capabilities, story_workspace_workspaces | L130 <module>: revision; L845 PostgresMcpRepository.save_discovery_snapshot_sync: ON CONFLICT,revision; L364 PostgresMcpRepository.get_app_settings_sync: revision; L409 PostgresMcpRepository.update_app_settings_sync: RETURNING,revision; L598 PostgresMcpRepository.update_server_sync: RETURNING,revision; L652 PostgresMcpRepository.delete_server_sync: RETURNING,revision; L671 PostgresMcpRepository.get_credential_sync: revision; L703 PostgresMcpRepository.upsert_credential_sync: ON CONFLICT,RETURNING,revision; L796 PostgresMcpRepository.get_discovery_snapshot_sync: revision; L835 PostgresMcpRepository.save_discovery_snapshot_sync: revision; L944 PostgresMcpRepository.import_server_sync: revision; L439 PostgresMcpRepository.update_app_settings_sync: revision; L487 PostgresMcpRepository.create_server_sync: RETURNING,revision; L534 PostgresMcpRepository.update_server_sync: FOR UPDATE; L639 PostgresMcpRepository.delete_server_sync: FOR UPDATE; L755 PostgresMcpRepository.delete_credential_sync: FOR UPDATE | 130,765,961,364,409,598,652,671,703,796,835,877,944,439,487,534,639,755,912,932,474 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/claude_mcp/service.py](../../backend/claude_mcp/service.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/database.py](../../backend/database.py) | production / 176 | SET, a, ai_models, analysis_reports, chat_message, chat_thread, claude_plugin_installations, daily_pictures, deck_claude_plugin_refs, deck_plugin_bindings, deck_runtime_snapshots, decks, device_authorizations, friend_invites, friendships, oauth_accounts, platform_users, reflection_result, reflection_task, reflection_task_event, reflections_section_configs, refresh_tokens, subscription_events, subscription_plan_entitlements, subscription_plan_versions, subscription_plans, subscription_usage_allowances, subscriptions, task, the, user_preferences, user_sessions, users, voices | L780 _upsert_default_deck_plugin_ref: ON CONFLICT; L474 seed_system_decks: ON CONFLICT; L1673 create_user: RETURNING; L1805 upsert_oauth_account: ON CONFLICT; L1924 create_device_authorization: RETURNING; L2127 save_session: ON CONFLICT; L2515 save_preferences: ON CONFLICT; L2827 use_invite_code: RETURNING; L3829 save_reflections_section_config: ON CONFLICT; L4100 append_reflection_task_event: ON CONFLICT; L437 backfill_builtin_deck_plugin_refs: ON CONFLICT; L502 seed_system_decks: ON CONFLICT; L2689 import_user_data: ON CONFLICT; L2708 import_user_data: ON CONFLICT; L335 replace_deck_claude_plugin_refs: FOR UPDATE; L638 publish_deck: FOR UPDATE; L874 reconcile_default_screenplay_deck_plugin_ref: FOR UPDATE; L1070 delete_deck: FOR UPDATE; L1292 sync_deck_with_parent: FOR UPDATE; L1426 create_voice: FOR UPDATE; L1484 update_voice: FOR UPDATE; L1575 delete_voice: FOR UPDATE; L1578 delete_voice: FOR UPDATE; L1607 fork_voice: FOR UPDATE; L3485 save_chat_message: ON CONFLICT,RETURNING; L901 reconcile_default_screenplay_deck_plugin_ref: FOR UPDATE; L1010 update_deck: FOR UPDATE; L1494 update_voice: FOR UPDATE | 821,656,673,837,972,1205,1445,1630,1805,1843,1898,2127,2171,2313,2515,2642,2763,2827,2994,3087,3115,3145,3257,3829,3851,3910,4014,1232,1338,2598,2603,2620,2627,2689,2701,2708,4019,605,638,719,817,1070,1292,1426,1484,1575,1578,1607,1682,1776,1860,2144,2205,2278,2351,2407,2444,2464,2483,2494,2542,2573,2591,2616,2654,2727,2783,2809,2860,2885,2920,2955,2963,3018,3030,3053,3101,3126,3804,3989,4048,4067,571,881,1010,1374,1494,2243,3207,3976,4133,4147,4158,967 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/libs/claude_agent_kit/server/agent_runner.py](../../backend/libs/claude_agent_kit/server/agent_runner.py) | production / 3 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/libs/claude_agent_kit/server/editor_tool.py](../../backend/libs/claude_agent_kit/server/editor_tool.py) | production / 2 | user_sessions | 详见 JSON 调用线索 | 321,287 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/libs/claude_agent_kit/server/notion_read_hook.py](../../backend/libs/claude_agent_kit/server/notion_read_hook.py) | production / 1 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/libs/claude_agent_kit/server/sdk_env.py](../../backend/libs/claude_agent_kit/server/sdk_env.py) | production / 1 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/libs/claude_agent_kit/server/sessions_tool.py](../../backend/libs/claude_agent_kit/server/sessions_tool.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/libs/claude_agent_kit/server/story_workspace_tool.py](../../backend/libs/claude_agent_kit/server/story_workspace_tool.py) | production / 3 | chat_thread, story_workspace_workspaces, the, workflow_runs | 详见 JSON 调用线索 | 56,155,186 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/memory_workspace_defaults.py](../../backend/memory_workspace_defaults.py) | production / 4 | Memory, Rules, Use, a, decision, memory, merely, procedural, the | L149 <module>: FOR UPDATE | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/notion/credentials.py](../../backend/notion/credentials.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/notion/operations.py](../../backend/notion/operations.py) | production / 3 | its | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/notion/store.py](../../backend/notion/store.py) | production / 22 | SET, connector_chat_threads, connector_resource_pages, connector_resources, connector_snapshots, resource_connectors | L214 NotionConnectorRepository.get_connector: FOR UPDATE; L559 NotionConnectorRepository.attach_thread: ON CONFLICT; L159 NotionConnectorRepository.insert_connector: RETURNING; L260 NotionConnectorRepository.update_connector: RETURNING,revision; L409 NotionConnectorRepository.upsert_snapshot: ON CONFLICT,RETURNING,revision; L294 NotionConnectorRepository.delete_connector: RETURNING; L384 NotionConnectorRepository.delete_resource: RETURNING | 159,174,233,260,505,523,539,575,294 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/persistence/catalog.py](../../backend/persistence/catalog.py) | production / 5 | LATERAL, pg_catalog.pg_am, pg_catalog.pg_attrdef, pg_catalog.pg_attribute, pg_catalog.pg_class, pg_catalog.pg_collation, pg_catalog.pg_constraint, pg_catalog.pg_index, pg_catalog.pg_namespace, pg_catalog.pg_proc, pg_catalog.pg_trigger, unnest | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/persistence/health.py](../../backend/persistence/health.py) | production / 1 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/persistence/postgres.py](../../backend/persistence/postgres.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/persistence/unit_of_work.py](../../backend/persistence/unit_of_work.py) | production / 1 | publishing | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/reflections_agent.py](../../backend/reflections_agent.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/reflections_config.py](../../backend/reflections_config.py) | production / 3 | Rules, existing | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/auth.py](../../backend/routers/auth.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/claude_agent.py](../../backend/routers/claude_agent.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/claude_plugins.py](../../backend/routers/claude_plugins.py) | production / 6 | claude_plugin_operations, deck_claude_plugin_refs | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/deck_plugin_binding.py](../../backend/routers/deck_plugin_binding.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/deck_plugins.py](../../backend/routers/deck_plugins.py) | production / 1 | users | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/deck_versions.py](../../backend/routers/deck_versions.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/device_oauth.py](../../backend/routers/device_oauth.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/friends.py](../../backend/routers/friends.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/notion.py](../../backend/routers/notion.py) | production / 3 | its | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/oauth.py](../../backend/routers/oauth.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/pictures.py](../../backend/routers/pictures.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/preferences.py](../../backend/routers/preferences.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/reflections.py](../../backend/routers/reflections.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/reports.py](../../backend/routers/reports.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/sessions.py](../../backend/routers/sessions.py) | production / 1 | a | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/story_workspace.py](../../backend/routers/story_workspace.py) | production / 25 | story_workspace_characters, story_workspace_scene_characters, story_workspace_scenes, story_workspace_stories, story_workspace_story_characters, story_workspace_workspaces | 详见 JSON 调用线索 | 893,886,899 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/system_config.py](../../backend/routers/system_config.py) | production / 1 | into | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/voices.py](../../backend/routers/voices.py) | production / 2 | a | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/routers/workspace.py](../../backend/routers/workspace.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/schema/capabilities.py](../../backend/schema/capabilities.py) | production / 6 | drizzle.schema_capabilities | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/schema/catalog.py](../../backend/schema/catalog.py) | production / 4 | sqlite_master | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/schema/importer.py](../../backend/schema/importer.py) | explicit import/maintenance script; verify callers before retirement / 37 | information_schema.columns, pg_catalog.pg_attribute, pg_catalog.pg_class, pg_catalog.pg_constraint, pg_catalog.pg_database, pg_catalog.pg_index, pg_catalog.pg_namespace, pg_catalog.pg_trigger, sqlite_master, sqlite_sequence, unnest | 详见 JSON 调用线索 | 1274 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/schema/legacy_main_sqlite.py](../../backend/schema/legacy_main_sqlite.py) | explicit import/maintenance script; verify callers before retirement / 92 | IF, OF, ON, agent_sessions, chat_message, chat_thread, decks, runtime_load_receipts, sqlite_master, user_preferences, user_sessions, users, voices, workflow_runs | L797 create_tables: revision; L838 create_tables: revision; L879 create_tables: revision; L918 create_tables: revision; L1049 create_workflow_run_tables: revision; L1168 create_workflow_run_tables: revision; L1245 create_runtime_plugin_tables: revision; L1278 create_runtime_plugin_tables: revision; L1298 create_runtime_plugin_tables: revision; L1375 create_runtime_plugin_tables: revision; L1415 create_agent_session_tables: revision; L1461 create_agent_session_tables: revision; L76 _migrate_story_workspace_review_persistence: SAVEPOINT; L119 _migrate_story_workspace_review_persistence: SAVEPOINT; L121 _migrate_story_workspace_review_persistence: SAVEPOINT; L122 _migrate_story_workspace_review_persistence: SAVEPOINT | 205,226,241,267,280,301,316,340,354,397,439,456,472,579,918,964,982,1003,1049,1105,1120,1168,1415 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/schema/legacy_notion_sqlite.py](../../backend/schema/legacy_notion_sqlite.py) | explicit import/maintenance script; verify callers before retirement / 5 | IF | L16 create_legacy_notion_tables: revision; L80 create_legacy_notion_tables: revision | 16 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/script/bootstrap_postgres_roles.py](../../backend/script/bootstrap_postgres_roles.py) | explicit import/maintenance script; verify callers before retirement / 29 | billing_accounts, drizzle.__drizzle_migrations, information_schema.tables, pg_class, pg_depend, pg_namespace, pg_proc, pg_roles, pg_tables, pg_trigger, pg_type, platform_users, public., users | L405 verify: SAVEPOINT; L426 verify: SAVEPOINT; L427 verify: SAVEPOINT | 385,100,414,278 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/script/import_claude_mcp_config.py](../../backend/script/import_claude_mcp_config.py) | explicit import/maintenance script; verify callers before retirement / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/script/import_diaries.py](../../backend/script/import_diaries.py) | explicit import/maintenance script; verify callers before retirement / 6 | an, user_preferences, user_sessions, users | 详见 JSON 调用线索 | 1249,1117,601 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/script/reconcile_story_artifact_index.py](../../backend/script/reconcile_story_artifact_index.py) | explicit import/maintenance script; verify callers before retirement / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/script/verify_gateway_e2e.py](../../backend/script/verify_gateway_e2e.py) | explicit import/maintenance script; verify callers before retirement / 8 | chat_message, chat_thread, gateway_requests, jsonb_array_elements, messages, platform_users, subscription_token_ledger_entries, subscription_usage_allowances, users | 详见 JSON 调用线索 | 549,592,727,783 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/server.py](../../backend/server.py) | production / 4 | claude_plugin_installations, deck, voice | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/admin_gateway/selection.py](../../backend/services/admin_gateway/selection.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/admin_product/identity.py`（迁移前文件，现已删除） | production / 1 | users | 单行 active identity 读取 | 61 | 已关闭：主体来自 Admin OAuth principal，Admin Product ORM 再次复核 active canonical/platform identity |
| [backend/services/admin_product/runtime.py](../../backend/services/admin_product/runtime.py) | production / 0 | Admin HTTP composition | 无本地事务 | 不适用 | 已关闭：只创建 Product client，不创建 PostgreSQL pool或fallback |
| [backend/services/claude_agent/remote_interaction_guard.py](../../backend/services/claude_agent/remote_interaction_guard.py) | production / 2 | agent_sessions, workflow_runs | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/claude_agent/session_manager.py](../../backend/services/claude_agent/session_manager.py) | production / 17 | agent_sessions, deck_runtime_plugin_locks, runtime_load_receipt_entries, runtime_load_receipts, workflow_runs | L709 SessionManager._acquire_attempt: revision | 762,785,798,301,709,353,660 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/claude_plugin/deck_refs_service.py`（历史基线，现已退役） | production / 3 | claude_plugin_installations, deck_claude_plugin_refs, decks | 详见 JSON 调用线索 | 40 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/claude_plugin/install_service.py](../../backend/services/claude_plugin/install_service.py) | production / 16 | claude_plugin_installations, claude_plugin_operations, deck_claude_plugin_refs | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/claude_plugin/marketplace_service.py](../../backend/services/claude_plugin/marketplace_service.py) | production / 4 | LATERAL, claude_plugin_installations, claude_plugin_marketplace_entries, claude_plugin_marketplace_entry_policies, claude_plugin_marketplace_revisions, claude_plugin_marketplaces, drizzle.schema_capabilities | L108 MarketplaceCatalogService.list_entries: revision; L201 MarketplaceCatalogService.resolve_install_source: revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/claude_plugin/workspace_packer.py](../../backend/services/claude_plugin/workspace_packer.py) | production / 2 | claude_plugin_installations, deck_claude_plugin_refs | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck/admin_gateway.py](../../backend/services/deck/admin_gateway.py) | production / 12 | deck_plugin_installations, deck_plugin_releases, deck_runtime_plugin_locks, runtime_plugin_materializations | L566 DeckPluginAdminService.reject_upgrade: revision; L274 DeckPluginAdminService._materialize: revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck/agent_type.py](../../backend/services/deck/agent_type.py) | production / 2 | deck_plugin_bindings, deck_plugin_releases | L55 agent_type_records_for_decks: revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck/builtin_plugin.py](../../backend/services/deck/builtin_plugin.py) | production / 6 | deck_plugin_releases, deck_runtime_plugin_locks | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck/chat_context.py](../../backend/services/deck/chat_context.py) | production / 2 | decks, voices | 详见 JSON 调用线索 | 67 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/deck/content_versioning.py`（历史基线，现已退役） | production / 12 | deck_claude_plugin_refs, deck_plugin_bindings, deck_plugin_releases, deck_versions, decks, drizzle.schema_capabilities, voices | L168 DeckContentVersionService._owned_deck: FOR UPDATE; L101 advance_deck_draft_revision: RETURNING,revision; L418 DeckContentVersionService.commit: revision; L227 DeckContentVersionService._snapshot: revision; L460 DeckContentVersionService.list_versions: revision; L480 DeckContentVersionService.get_version: revision; L170 DeckContentVersionService._owned_deck: revision; L397 DeckContentVersionService.commit: RETURNING,revision | 460,480,170,397 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck/defaults.py](../../backend/services/deck/defaults.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/deck/runtime_context.py`（历史基线，现已退役） | production / 5 | deck_plugin_installations, deck_plugin_releases, deck_runtime_plugin_locks, runtime_plugin_materializations | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck/story_workflow_application.py](../../backend/services/deck/story_workflow_application.py) | production / 4 | chat_thread, story_workspace_workspaces, workflow_runs | 详见 JSON 调用线索 | 280,365,372,1428 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/deck_plugin/binding_service.py`（历史基线，现已退役） | production / 11 | deck_plugin_bindings, decks, story_workspace_workspaces | L251 BindingService.save: revision; L166 BindingService.list_history: revision; L237 BindingService.save: revision; L313 BindingService.clear: revision; L340 BindingService._lock_owned_deck: FOR UPDATE; L361 BindingService.latest_revision: revision | 91,340,99,107 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/deck_plugin/compatibility_service.py`（历史基线，现已退役） | production / 6 | columns, deck_plugin_installations, deck_plugin_releases, deck_runtime_plugin_locks | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck_plugin/installation_service.py](../../backend/services/deck_plugin/installation_service.py) | production / 8 | columns, deck_plugin_installations, deck_plugin_releases, deck_runtime_plugin_locks | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck_plugin/manifest_validator.py](../../backend/services/deck_plugin/manifest_validator.py) | production / 1 | deck_plugin_releases | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/deck_plugin/release_service.py`（历史基线，现已退役） | production / 11 | deck_plugin_releases, deck_runtime_plugin_locks | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck_plugin/revocation_service.py](../../backend/services/deck_plugin/revocation_service.py) | production / 30 | IF, revocation_audit_events, revocation_cancel_commands, revocation_impact_manifests, revocation_incidents, revocation_notification_outbox, revocation_quarantined_targets, revocation_runtime_receipts, security_revocations | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/deck_plugin/rollback_manager.py](../../backend/services/deck_plugin/rollback_manager.py) | production / 6 | deck_plugin_installations, deck_plugin_releases, deck_runtime_plugin_locks, information_schema.columns | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/deck_plugin/selection_validation_service.py`（历史基线，现已退役） | production / 4 | deck_plugin_installations, deck_plugin_releases | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/errors/error_registry.py](../../backend/services/errors/error_registry.py) | production / 5 | Claude, the | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/events/event_emitter.py`（迁移前基线，现已删除） | production / 3 | events | 详见 JSON 调用线索 | 无生产调用者 | 退役未接线实现；未创建无业务调用方的Admin接口 |
| [backend/services/runtime_plugin/materialization_manager.py](../../backend/services/runtime_plugin/materialization_manager.py) | production / 5 | runtime_plugin_materializations | L342 MaterializationManager._begin_attempt: revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/runtime_plugin/reconcile_service.py](../../backend/services/runtime_plugin/reconcile_service.py) | production / 11 | deck_runtime_plugin_locks, runtime_load_receipt_entries, runtime_load_receipts, runtime_plugin_materializations, runtime_plugin_reconcile_attempts, workflow_runs | L277 SqliteCliAuditSink.record: revision; L793 ReconcileService._record_headless_attempt: revision; L820 ReconcileService._record_headless_failure: revision; L849 ReconcileService._persist_receipt: revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/agent_integration.py](../../backend/services/story_workspace/agent_integration.py) | production / 25 | story_workspace_characters, story_workspace_scene_characters, story_workspace_scenes, story_workspace_stories, story_workspace_story_characters, story_workspace_workspaces | L106 store_agent_story_output: SAVEPOINT; L137 store_agent_story_output: SAVEPOINT; L350 store_agent_story_output: SAVEPOINT; L353 store_agent_story_output: SAVEPOINT; L354 store_agent_story_output: SAVEPOINT; L356 store_agent_story_output: SAVEPOINT | 79,69,119 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/artifact_story_index_reconcile.py](../../backend/services/story_workspace/artifact_story_index_reconcile.py) | production / 1 | chat_message, chat_thread, story_workspace_workspaces, users, workflow_runs | 详见 JSON 调用线索 | 294 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/artifact_story_index_repository.py](../../backend/services/story_workspace/artifact_story_index_repository.py) | production / 20 | LATERAL, cannot, information_schema.columns, one, pg_catalog.pg_attribute, pg_catalog.pg_class, pg_catalog.pg_index, pg_catalog.pg_namespace, returned, story_workspace_stories | L488 ArtifactStoryIndexRepository.upsert: FOR UPDATE; L380 ArtifactStoryIndexRepository.upsert: FOR UPDATE; L500 ArtifactStoryIndexRepository.upsert: RETURNING,revision; L443 ArtifactStoryIndexRepository.upsert: RETURNING,revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_artifact_turn_hook.py](../../backend/services/story_workspace/dream_artifact_turn_hook.py) | production / 5 | chat_message, list, the, workflow_runs | 详见 JSON 调用线索 | 1192 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_auto_repair_service.py](../../backend/services/story_workspace/dream_auto_repair_service.py) | production / 3 | chat_message | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_confirmation_service.py](../../backend/services/story_workspace/dream_confirmation_service.py) | production / 16 | chat_message, chat_thread, failed, story_workspace_workspaces, workflow_runs | L1518 StoryWorkspaceDreamConfirmationService.submit_confirmation: ON CONFLICT | 561,903,1548,617,730,1595 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_launch_endpoint_service.py](../../backend/services/story_workspace/dream_launch_endpoint_service.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_launch_infrastructure.py](../../backend/services/story_workspace/dream_launch_infrastructure.py) | production / 28 | chat_message, chat_thread, claude_plugin_installations, deck_plugin_bindings, deck_plugin_installations, deck_runtime_plugin_locks, decks, runtime_plugin_materializations, story_workspace_workspaces, voices, workflow_preflights, workflow_runs | L627 DreamRuntimeProvisioningService._ensure_materialization: revision; L799 DreamRuntimeProvisioningService._latest_binding_revision: revision | 295,349,502,1165,1450,1462,260,290,1241,1388 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_reentry_service.py](../../backend/services/story_workspace/dream_reentry_service.py) | production / 4 | LATERAL, chat_message, chat_thread, deck_plugin_bindings, deck_plugin_releases, deck_runtime_plugin_locks, deck_runtime_snapshots, decks, jsonb_array_elements, jsonb_array_elements_text, story_workspace_stories, story_workspace_workspaces, workflow_preflights, workflow_runs | L179 StoryWorkspaceDreamReentryService._query_authorized_rows: revision | 179 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/dream_runtime_activation_service.py](../../backend/services/story_workspace/dream_runtime_activation_service.py) | production / 3 | agent_sessions, deck_runtime_plugin_locks, runtime_plugin_materializations | L286 StoryWorkspaceDreamRuntimeActivationService._load_evidence: revision | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/story_workspace/dream_thread_binding.py`（迁移前基线，现已删除） | production / 1 | chat_message, deck_plugin_bindings, story_workspace_workspaces, workflow_runs | L351 DreamRunBindingResolver.resolve: revision | 351 | 已由Admin `workflow-context.resolve` strict DTO/typed Drizzle aggregate替换 |
| [backend/services/story_workspace/dream_workflow_lifecycle_service.py](../../backend/services/story_workspace/dream_workflow_lifecycle_service.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/episode_binding_service.py](../../backend/services/story_workspace/episode_binding_service.py) | production / 1 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/story_workspace/guidance_service.py](../../backend/services/story_workspace/guidance_service.py) | production / 2 | chat_message, chat_thread | 详见 JSON 调用线索 | 290 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/story_workspace/preflight_builder.py`（历史基线，现已退役） | production / 13 | deck_plugin_bindings, deck_plugin_installations, deck_plugin_releases, deck_runtime_plugin_locks, deck_runtime_snapshots, decks, runtime_plugin_materializations, story_workspace_workspaces, voices | L290 StoryWorkspacePreflightServiceBuilder.ensure_snapshot: revision; L101 StoryWorkspacePreflightServiceBuilder.resolve_binding: revision; L262 StoryWorkspacePreflightServiceBuilder.ensure_snapshot: revision | 83,236 | 等待 Admin 规范；按原 aggregate 事务替换 |
| `backend/services/workflow/preflight_service.py`（历史基线，现已退役） | production / 12 | workflow_preflights | L540 PreflightService._insert_checking: revision | 540,427 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/services/workflow/run_service.py](../../backend/services/workflow/run_service.py) | production / 16 | agent_sessions, current, deck_plugin_bindings, deck_plugin_releases, deck_runtime_plugin_locks, runtime_load_receipts, workflow_preflights, workflow_run_token_consumptions, workflow_run_transitions, workflow_runs | L511 WorkflowRunService._create_run: revision; L602 WorkflowRunService._load_preflight_context: revision; L797 WorkflowRunService._validate_agent_session_binding: revision | 700,864,511,295,890,460 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/tools/session_inserter.py](../../backend/tools/session_inserter.py) | production / 0 | 依赖/工厂入口 | 详见 JSON 调用线索 | 需调用链核查 | 等待 Admin 规范；按原 aggregate 事务替换 |
| [backend/tools/session_inspector.py](../../backend/tools/session_inspector.py) | production / 1 | user_sessions | 详见 JSON 调用线索 | 61 | 等待 Admin 规范；按原 aggregate 事务替换 |

## 生产函数与方法证据

- `backend/agent_factory.py`: <module>
- `backend/claude_agent/admission.py`: ClaudeAgentAdmissionController.__init__
- `backend/claude_agent/context_builder.py`: imports only
- `backend/claude_agent/resource_policy.py`: ClaudeAgentResourcePolicyProvider.load
- `backend/claude_agent/resource_postgres_sink.py`: ClaudeAgentResourcePostgresSink._write_sync
- `backend/claude_agent/service.py`: ClaudeAgentService._persist_user_message._save_user, _activate_story_workspace_dream_runtime, _emit_plan_updated, _pack_thread_workspace_plugins, _resolve_managed_mcp_workspace_scope_sync, _resolve_story_workspace_dream_deck_prompt, _store_story_workspace_output_sync
- `backend/claude_agent/thread_pool.py`: AgentRunState.with_editor_state
- `backend/claude_agent/tool_confirmation_store.py`: <module>, ToolConfirmationStore._validate_answer, _ask_user_policy
- `backend/claude_mcp/credentials.py`: ClaudeMcpCredentialSynchronizer.__init__
- `backend/claude_mcp/driver.py`: ClaudeMcpCliDriver.__init__
- `backend/claude_mcp/identity.py`: PlatformClaudeMcpIdentityProvider.__init__
- `backend/claude_mcp/repository.py`: <module>, PostgresMcpRepository.app_settings_capability_available_sync, PostgresMcpRepository.capability_available_sync, PostgresMcpRepository.create_server_sync, PostgresMcpRepository.delete_credential_sync, PostgresMcpRepository.delete_server_sync, PostgresMcpRepository.find_import_receipt_sync, PostgresMcpRepository.get_app_settings_sync, PostgresMcpRepository.get_credential_sync, PostgresMcpRepository.get_discovery_snapshot_sync, PostgresMcpRepository.get_server_sync, PostgresMcpRepository.import_server_sync, PostgresMcpRepository.list_servers_sync, PostgresMcpRepository.save_discovery_snapshot_sync, PostgresMcpRepository.update_app_settings_sync, PostgresMcpRepository.update_server_sync, PostgresMcpRepository.upsert_credential_sync
- `backend/claude_mcp/service.py`: build_default_claude_mcp_service
- `backend/database.py`: _PooledConnectionLease.__exit__, _PooledConnectionLease.close, _insert_default_screenplay_deck, _open_runtime_pool, _retired_system_deck_visibility, _touch_chat_thread, _upsert_default_deck_plugin_ref, _verified_default_deck_plugin_installation, accept_friend_request, append_reflection_task_event, auto_fork_system_decks, backfill_builtin_deck_plugin_refs, bind_chat_thread_deck, create_chat_thread, create_deck, create_default_screenplay_deck, create_device_authorization, create_reflection_task, create_refresh_token, create_user, create_voice, delete_chat_thread, delete_deck, delete_reflections_section_config, delete_session, delete_voice, extract_text_from_sessions_on_date, fork_deck, fork_voice, generate_invite_code, get_all_sessions_with_text, get_analysis_reports, get_chat_message_process_detail, get_chat_thread, get_daily_picture_full, get_daily_pictures, get_daily_pictures_range, get_deck_with_voices, get_device_authorization_by_device_code_hash, get_device_authorization_by_user_code_hash, get_friend_picture_full, get_friend_requests, get_friend_timeline, get_friends, get_latest_chat_message_id, get_latest_reflection_task, get_preferences, get_published_decks, get_reflection_task, get_reflections_section_config, get_refresh_token, get_session, get_sessions_batch, get_system_config, get_user_by_email, get_user_by_id, get_user_by_oauth_account, get_user_decks, get_users_with_activity_on_date, get_voice_memory_config_by_thread, import_user_data, increment_deck_install_count, init_db, list_chat_message_page, list_chat_messages, list_chat_threads, list_chat_threads_for_search, list_deck_claude_plugin_refs, list_latest_reflection_results, list_reflection_results, list_reflection_task_events, list_sessions, list_sessions_in_range, load_voices_from_user_decks, publish_deck, reconcile_default_screenplay_deck_plugin_ref, record_device_authorization_poll, reject_friend_request, remove_friend, replace_deck_claude_plugin_refs, replace_reflection_section_results, revoke_refresh_token, revoke_user_refresh_tokens, save_analysis_report, save_chat_message, save_preferences, save_reflections_section_config, save_session, save_system_config, seed_system_decks, select_chat_thread_voice, set_first_login_completed, sync_deck_with_parent, unpublish_deck, update_chat_thread_claude_session, update_chat_thread_title, update_deck, update_device_authorization_status, update_reflection_task_status, update_voice, upsert_oauth_account, use_invite_code
- `backend/libs/claude_agent_kit/server/agent_runner.py`: <module>
- `backend/libs/claude_agent_kit/server/editor_tool.py`: _load_editor_state_from_db, _save_editor_state_to_db
- `backend/libs/claude_agent_kit/server/notion_read_hook.py`: apply_notion_page_read_redirect
- `backend/libs/claude_agent_kit/server/sdk_env.py`: apply_gateway_credential_tombstones
- `backend/libs/claude_agent_kit/server/sessions_tool.py`: imports only
- `backend/libs/claude_agent_kit/server/story_workspace_tool.py`: <module>, _with_authoritative_context
- `backend/memory_workspace_defaults.py`: <module>
- `backend/notion/credentials.py`: NotionCredentialStore.__init__
- `backend/notion/operations.py`: NotionOperationClient._run_endpoint, _is_people_system_database
- `backend/notion/store.py`: NotionConnectorRepository._execute, NotionConnectorRepository.attach_thread, NotionConnectorRepository.delete_connector, NotionConnectorRepository.delete_resource, NotionConnectorRepository.delete_selected_resources, NotionConnectorRepository.find_database_resource, NotionConnectorRepository.get_active_connector, NotionConnectorRepository.get_connector, NotionConnectorRepository.get_connector_for_thread, NotionConnectorRepository.get_current_snapshot, NotionConnectorRepository.get_snapshot, NotionConnectorRepository.insert_connector, NotionConnectorRepository.insert_resource, NotionConnectorRepository.list_connectors, NotionConnectorRepository.list_resources, NotionConnectorRepository.list_snapshots, NotionConnectorRepository.list_sync_candidates, NotionConnectorRepository.mark_resource_synced, NotionConnectorRepository.replace_resource_pages, NotionConnectorRepository.update_connector, NotionConnectorRepository.upsert_snapshot, NotionConnectorStore.attach_thread_to_connector, NotionConnectorStore.create_connector, NotionConnectorStore.delete_connector, NotionConnectorStore.delete_connector_resource, NotionConnectorStore.replace_connector_resources, NotionConnectorStore.save_auth_state, NotionConnectorStore.save_snapshot, NotionConnectorStore.update_connector, _DefaultNotionStoreRuntime.open
- `backend/persistence/catalog.py`: <module>, _fetchall
- `backend/persistence/health.py`: <module>, _fetchone, check_postgres_health
- `backend/persistence/postgres.py`: PostgresPool.connection, PostgresPool.from_env
- `backend/persistence/unit_of_work.py`: PostgresUnitOfWork, PostgresUnitOfWork.__enter__, PostgresUnitOfWork.__exit__, PostgresUnitOfWork._configure_transaction, PostgresUnitOfWork._release_after_failed_enter, PostgresUnitOfWork.commit, PostgresUnitOfWork.execute, PostgresUnitOfWork.rollback
- `backend/reflections_agent.py`: imports only
- `backend/reflections_config.py`: <module>
- `backend/routers/auth.py`: imports only
- `backend/routers/claude_agent.py`: claude_agent_stream
- `backend/routers/claude_plugins.py`: _run_install, _run_install.finish_error, get_installation, get_operation, install_plugin, list_deck_plugins, list_installations, list_marketplace, list_operations, put_deck_plugins, uninstall_plugin
- `backend/routers/deck_plugin_binding.py`: _binding_db, _deck_current_user, put_agent_type
- `backend/routers/deck_plugins.py`: _deck_plugin_current_user, rollback_plugin
- `backend/routers/deck_versions.py`: _service, commit_version
- `backend/routers/device_oauth.py`: imports only
- `backend/routers/friends.py`: imports only
- `backend/routers/notion.py`: _http_error, select_resources
- `backend/routers/oauth.py`: imports only
- `backend/routers/pictures.py`: imports only
- `backend/routers/preferences.py`: imports only
- `backend/routers/reflections.py`: imports only
- `backend/routers/reports.py`: imports only
- `backend/routers/sessions.py`: save_session
- `backend/routers/story_workspace.py`: _archive_story, _batch_review, _owned_review_row, _owned_row, _paginate_query, _patch_owned_row, _story_db, _story_workflow_current_user, _transition_pending_review, get_scene, get_workspace, list_characters, list_scenes
- `backend/routers/system_config.py`: <module>
- `backend/routers/voices.py`: update_deck, update_voice
- `backend/routers/workspace.py`: imports only
- `backend/schema/capabilities.py`: _relation_exists, claude_agent_resource_observer_capability_available, claude_code_runtime_config_capability_available, inspect_schema_authority, managed_mcp_resources_capability_available, mcp_app_connection_settings_capability_available
- `backend/schema/catalog.py`: _extract_database, _index_columns, _table_indexes
- `backend/schema/importer.py`: _assert_sqlite_integrity, _baseline_conflicts, _calibrate_sequences, _digest_database_query, _fetch_scalar, _insert_from_stage, _open_read_only_sqlite, _scan_table, _sqlite_foreign_keys, _stage_table, _staged_drift_summary, _validate_cross_database_foreign_keys, _validate_source_constraints, _validate_source_schema, _validate_target_catalog, _validate_target_conflicts, _validate_target_constraints_and_indexes, _validate_target_foreign_keys, _verify_staged_subset, migrate_to_postgres, readonly_snapshot_bundle, run_legacy_migration, verify_existing_postgres
- `backend/schema/legacy_main_sqlite.py`: _backfill_default_memory_workspace_config, _migrate_story_workspace_review_persistence, create_agent_session_tables, create_claude_plugin_tables, create_event_tables, create_runtime_plugin_tables, create_tables, create_workflow_run_tables, drop_story_workspace_tables
- `backend/schema/legacy_notion_sqlite.py`: create_legacy_notion_tables
- `backend/script/bootstrap_postgres_roles.py`: _alter_table_owner, _configure_default_privileges, _configure_functions, _configure_schemas, _configure_sequences, _configure_tables, _configure_types, _create_roles, _function_rows, _grant_table, _has_table_privilege, _public_tables, _sequence_rows, main, verify
- `backend/script/import_claude_mcp_config.py`: _run
- `backend/script/import_diaries.py`: _build_agent_token, fetch_existing_sessions, list_users, parse_args, preserve_import_timestamps, resolve_timezone
- `backend/script/reconcile_story_artifact_index.py`: _close_database, _open_database
- `backend/script/verify_gateway_e2e.py`: _gateway_receipt, _metrics, _thread_receipt, main
- `backend/server.py`: <module>, startup_claude_plugin_seed._seed
- `backend/services/admin_gateway/selection.py`: imports only
- `backend/services/admin_product/identity.py`（迁移前基线）: `PostgresCanonicalUserRepository._find_active_sync`；2026-09-16 已删除
- `backend/services/admin_product/runtime.py`（迁移前基线）: `LazyProductBffService._delegate`；2026-09-16 已移除 pool composition
- `backend/services/claude_agent/remote_interaction_guard.py`: RemoteInteractionGuard.guard_reload
- `backend/services/claude_agent/session_manager.py`: SessionManager._acquire_attempt, SessionManager._load_scoped_queued_run, SessionManager._mark_compensation_pending, SessionManager._mark_failed, SessionManager._record_remote_start, SessionManager._rollback_read_transaction, SessionManager._validate_receipt, SessionManager.read_session, SessionManager.terminate_session
- `backend/services/claude_plugin/deck_refs_service.py`: DeckPluginRefService.assert_deck_owner, DeckPluginRefService.list_refs, DeckPluginRefService.replace_refs
- `backend/services/claude_plugin/install_service.py`: PluginInstallService._begin_operation, PluginInstallService.get_installation, PluginInstallService.get_operation, PluginInstallService.list_installations, PluginInstallService.uninstall, _attach_installation_lineage, _ensure_marketplace, _find_installation_by_artifact, _insert_installation, _insert_operation, _revive_installation, _update_operation
- `backend/services/claude_plugin/marketplace_service.py`: MarketplaceCatalogService.list_entries, MarketplaceCatalogService.resolve_install_source, remote_marketplace_capability_available
- `backend/services/claude_plugin/workspace_packer.py`: _load_server_adapter_refs, load_deck_plugin_refs
- `backend/services/deck/admin_gateway.py`: DeckPluginAdminService._db, DeckPluginAdminService._installation_row, DeckPluginAdminService._lifecycle, DeckPluginAdminService._materialize, DeckPluginAdminService._release, DeckPluginAdminService._runtime_rows, DeckPluginAdminService._view, DeckPluginAdminService.get_version, DeckPluginAdminService.install, DeckPluginAdminService.list_installations, DeckPluginAdminService.reject_upgrade
- `backend/services/deck/agent_type.py`: agent_type_records_for_decks
- `backend/services/deck/builtin_plugin.py`: _repair_legacy_builtin_release, seed_builtin_deck_plugin
- `backend/services/deck/chat_context.py`: DeckChatContextService.resolve
- `backend/services/deck/content_versioning.py`: DeckContentVersionService._latest_snapshot, DeckContentVersionService._owned_deck, DeckContentVersionService._snapshot, DeckContentVersionService.commit, DeckContentVersionService.get_version, DeckContentVersionService.list_versions, advance_deck_draft_revision, content_version_capability_available
- `backend/services/deck/defaults.py`: resolve_default_deck_plugin_ref
- `backend/services/deck/runtime_context.py`: _installation_row, resolve_runtime_context
- `backend/services/deck/story_workflow_application.py`: DreamArtifactApplicationService._get_dream_files_from_db, DreamArtifactApplicationService._get_dream_files_sync, DreamArtifactApplicationService._get_episode_artifacts_sync, DreamArtifactApplicationService._get_episode_index_sync, DreamArtifactApplicationService._get_story_index_sync, DreamArtifactApplicationService._reconcile_story_index_sync, DreamConfirmationApplicationService._submit_dream_confirmation_sync, StoryWorkflowRunApplicationService.cancel_run, StoryWorkflowRunApplicationService.create_preflight, StoryWorkflowRunApplicationService.create_run, StoryWorkflowRunApplicationService.get_preflight, StoryWorkflowRunApplicationService.get_run, StoryWorkflowRunApplicationService.retry_run, StoryWorkflowRunApplicationService.submit_guidance, _StoryWorkspaceApplicationSupport._run_actor_context, _dream_confirmation_actor_context
- `backend/services/deck_plugin/binding_service.py`: BindingService._current_row, BindingService._lock_owned_deck, BindingService.clear, BindingService.latest_revision, BindingService.list_history, BindingService.resolve_workspace_access, BindingService.save
- `backend/services/deck_plugin/compatibility_service.py`: CompatibilityService._installation_row, CompatibilityService._resolved_runtime_lock, CompatibilityService._update_installation, CompatibilityService.check_compatibility
- `backend/services/deck_plugin/installation_service.py`: InstallationService._required_row, InstallationService._update_row, InstallationService._validated_release, InstallationService.install, InstallationService.uninstall
- `backend/services/deck_plugin/manifest_validator.py`: _assert_unique
- `backend/services/deck_plugin/release_service.py`: DeckPluginReleaseService._get_by_id, DeckPluginReleaseService._transition_published_release, DeckPluginReleaseService.create_draft, DeckPluginReleaseService.get_release, DeckPluginReleaseService.get_runtime_plugin_lock, DeckPluginReleaseService.publish_with_lock, DeckPluginReleaseService.validate_release, _with_default_db
- `backend/services/deck_plugin/revocation_service.py`: SQLiteRevocationRepository._create_tables, SQLiteRevocationRepository._insert_audit, SQLiteRevocationRepository._insert_notification, SQLiteRevocationRepository.append_incident, SQLiteRevocationRepository.append_runtime_receipt, SQLiteRevocationRepository.audit_events, SQLiteRevocationRepository.commands, SQLiteRevocationRepository.commit_revocation, SQLiteRevocationRepository.find_idempotency, SQLiteRevocationRepository.get_record, SQLiteRevocationRepository.incidents, SQLiteRevocationRepository.manifests, SQLiteRevocationRepository.next_sequence, SQLiteRevocationRepository.notifications, SQLiteRevocationRepository.quarantined_targets, SQLiteRevocationRepository.records, SQLiteRevocationRepository.runtime_receipts, SQLiteRevocationRepository.save_notification
- `backend/services/deck_plugin/rollback_manager.py`: RollbackManager._table_projection, RollbackManager.rollback_installation
- `backend/services/deck_plugin/selection_validation_service.py`: SelectionValidationService._installation_scope, SelectionValidationService.list_options, SelectionValidationService.validate
- `backend/services/errors/error_registry.py`: <module>
- `backend/services/events/event_emitter.py`（迁移前基线，现已删除）: EventEmitter._load, EventEmitter.build_envelope, EventEmitter.emit
- `backend/services/runtime_plugin/materialization_manager.py`: MaterializationManager._begin_attempt, MaterializationManager._perform_materialization, MaterializationManager._select
- `backend/services/runtime_plugin/reconcile_service.py`: ReconcileService._persist_receipt, ReconcileService._record_headless_attempt, ReconcileService._record_headless_failure, ReconcileService.create_load_receipt, ReconcileService.read_receipt, ReconcileService.read_workflow_readiness, SqliteCliAuditSink.record
- `backend/services/story_workspace/agent_integration.py`: get_or_create_default_workspace, store_agent_story_output
- `backend/services/story_workspace/artifact_story_index_reconcile.py`: ArtifactStoryIndexReconcileRepository.list_run_candidates, ArtifactStoryIndexReconcileService.dry_run
- `backend/services/story_workspace/artifact_story_index_repository.py`: ArtifactStoryIndexRepository._rollback_quietly, ArtifactStoryIndexRepository.find, ArtifactStoryIndexRepository.list_records, ArtifactStoryIndexRepository.require_schema, ArtifactStoryIndexRepository.schema_columns, ArtifactStoryIndexRepository.upsert, StoryWorkspacePublicStoryRepository._available_columns, StoryWorkspacePublicStoryRepository.get_story, StoryWorkspacePublicStoryRepository.get_story_row, StoryWorkspacePublicStoryRepository.list_stories, StoryWorkspacePublicStoryRepository.list_stories_for_character
- `backend/services/story_workspace/dream_artifact_turn_hook.py`: DreamArtifactTurnHook._load_authoritative_run, DreamArtifactTurnHook._load_launch_authority, DreamArtifactTurnHook._materialize_story_index, DreamArtifactTurnHook._record_output_ready, DreamArtifactTurnHook._synchronize_episode_registry, DreamArtifactTurnHook.resolve_auto_repair_project_cleanup_scope
- `backend/services/story_workspace/dream_auto_repair_service.py`: settle_dream_auto_repair_message
- `backend/services/story_workspace/dream_confirmation_service.py`: StoryWorkspaceDreamConfirmationCoordinator._defer_owned_claim, StoryWorkspaceDreamConfirmationService._select_confirmation_for_scope, StoryWorkspaceDreamConfirmationService._select_message, StoryWorkspaceDreamConfirmationService._thread_owned_by, StoryWorkspaceDreamConfirmationService.submit_confirmation, _story_workspace_dream_confirmation_has_run_scope, _story_workspace_set_dream_confirmation_claim_lease, story_workspace_claim_dream_confirmation, story_workspace_guard_persisted_dream_confirmation_turn, story_workspace_mark_dream_confirmation_dispatched, story_workspace_read_dream_confirmation_fact, story_workspace_read_pending_dream_confirmations
- `backend/services/story_workspace/dream_launch_endpoint_service.py`: imports only
- `backend/services/story_workspace/dream_launch_infrastructure.py`: DreamLaunchEnvelopeDispatcher.__call__, DreamLaunchEnvelopeDispatcher._finish_claim, DreamLaunchEnvelopeDispatcher._message_row, DreamLaunchFailureRecorder.record, DreamLaunchSourceRepository._require_scope, DreamLaunchSourceRepository.ensure_source, DreamLaunchWorkflowOperationsAdapter._existing_replay_run, DreamLaunchWorkflowOperationsAdapter.create_preflight, DreamLaunchWorkflowOperationsAdapter.create_run, DreamLaunchWorkflowOperationsAdapter.prepare, DreamRuntimeProvisioningService._active_binding_row, DreamRuntimeProvisioningService._ensure_active_binding, DreamRuntimeProvisioningService._ensure_claude_installation, DreamRuntimeProvisioningService._ensure_deck_installation, DreamRuntimeProvisioningService._ensure_materialization, DreamRuntimeProvisioningService._latest_binding_revision, DreamRuntimeProvisioningService._require_scope, DreamRuntimeProvisioningService._runtime_lock, DreamRuntimeProvisioningService.ensure_frozen_runtime_evidence, DreamRuntimeProvisioningService.require_agent_scope
- `backend/services/story_workspace/dream_reentry_service.py`: StoryWorkspaceDreamReentryService._confirmation_facts, StoryWorkspaceDreamReentryService._project_titles, StoryWorkspaceDreamReentryService._query_authorized_rows
- `backend/services/story_workspace/dream_runtime_activation_service.py`: StoryWorkspaceDreamRuntimeActivationService._load_evidence, StoryWorkspaceDreamRuntimeActivationService._rollback_read, StoryWorkspaceDreamRuntimeActivationService._validate_active_runtime
- `backend/services/story_workspace/dream_thread_binding.py`: DreamRunBindingResolver.resolve
- `backend/services/story_workspace/dream_workflow_lifecycle_service.py`: StoryWorkspaceDreamWorkflowLifecycleService._read_run
- `backend/services/story_workspace/episode_binding_service.py`: StoryWorkspaceEpisodeBindingService.activate_episode
- `backend/services/story_workspace/guidance_service.py`: StoryWorkspaceGuidanceService._select_guidance_message, StoryWorkspaceGuidanceService._thread_owned_by
- `backend/services/story_workspace/preflight_builder.py`: StoryWorkspacePreflightServiceBuilder._installation_scope, StoryWorkspacePreflightServiceBuilder.check_capabilities, StoryWorkspacePreflightServiceBuilder.check_identity, StoryWorkspacePreflightServiceBuilder.ensure_snapshot, StoryWorkspacePreflightServiceBuilder.read_materialization, StoryWorkspacePreflightServiceBuilder.resolve_binding
- `backend/services/workflow/preflight_service.py`: PreflightService._active_preflight, PreflightService._insert_checking, PreflightService._load_model, PreflightService._persist_binding, PreflightService._persist_failed, PreflightService._persist_passed, PreflightService._persist_snapshot, PreflightService.consume_preflight_token, PreflightService.read_preflight
- `backend/services/workflow/run_service.py`: WorkflowRunService._consume_token_for_run, WorkflowRunService._create_run, WorkflowRunService._insert_transition, WorkflowRunService._load_preflight_context, WorkflowRunService._rollback_read_transaction, WorkflowRunService._runtime_lock_digest, WorkflowRunService._select_scoped_run, WorkflowRunService._validate_agent_session_binding, WorkflowRunService.list_transitions, WorkflowRunService.transition_run
- `backend/tools/session_inserter.py`: imports only
- `backend/tools/session_inspector.py`: fetch_sessions

## 特殊入口与排除边界

- `backend/script/**`、`backend/schema/{legacy_main_sqlite,legacy_notion_sqlite,importer}.py`：显式导入/维护候选，不应由 server/runtime 自动调用；后续逐项核查。
- `backend/tests/**`、`frontend/e2e/**` 与明确验证脚本：可保留隔离 fixture/harness 数据库代码，但不得成为生产 import。
- `frontend/app/**`、`frontend/packages/**`：初始 rg 未发现 PG/SQL driver；Node MCP Apps token/actor 委托与 BFF 仍需认证流程核查。
- `backend/server.py` startup/health、`agent_factory.py` 后台 composition、Notion store pool、resource observer sink/publisher与model registry：不因不是业务 router 而漏迁移。Product BFF identity/pool 已于2026-09-16关闭。

## 待验收

每文件填实际 Admin operation/capability/commit 与 Dream 替换证据，最后执行生产无 DB driver/credentials/SQL/static-import 与公开入口失败验证。

## 2026-09-15当前生产模块源码复核

命令：`/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-current-sql-scan.py`，exit0/parse_errors=[]。扫描backend Python，排除tests、backend/script以及四个明确offline schema catalog/importer/legacy模块。当前47个模块包含512个以SQL关键字开头的execute/executemany源码调用候选；16个模块仍导入数据库driver/persistence。

这些是源码候选，不等于已证明运行可达的生产SQL全集，也不能与baseline835字符串片段直接相减。变量SQL、repository自定义exec/pool/独立stdio DATABASE_URL等需继续入口追踪。无字面SQL的Notion/MCP/Product Repository/Runtime仍因persistence imports继续开放，不能报告closed。

| 当前模块 | 字面SQL调用候选 | 变量execute候选 |
| --- | --- | --- |
| [backend/database.py](../../backend/database.py) | 144 | 5 |
| [backend/services/story_workspace/dream_launch_infrastructure.py](../../backend/services/story_workspace/dream_launch_infrastructure.py) | 32 | 0 |
| [backend/services/story_workspace/agent_integration.py](../../backend/services/story_workspace/agent_integration.py) | 23 | 0 |
| [backend/services/deck_plugin/revocation_service.py](../../backend/services/deck_plugin/revocation_service.py) | 22 | 1 |
| [backend/routers/story_workspace.py](../../backend/routers/story_workspace.py) | 20 | 6 |
| [backend/services/story_workspace/dream_confirmation_service.py](../../backend/services/story_workspace/dream_confirmation_service.py) | 19 | 0 |
| [backend/services/claude_agent/session_manager.py](../../backend/services/claude_agent/session_manager.py) | 18 | 0 |
| [backend/services/workflow/run_service.py](../../backend/services/workflow/run_service.py) | 17 | 0 |
| [backend/services/story_workspace/artifact_story_index_repository.py](../../backend/services/story_workspace/artifact_story_index_repository.py) | 16 | 1 |
| [backend/services/claude_plugin/install_service.py](../../backend/services/claude_plugin/install_service.py) | 15 | 0 |
| `backend/services/deck_plugin/binding_service.py`（历史基线，现已退役） | 13 | 0 |
| `backend/services/story_workspace/preflight_builder.py`（历史基线，现已退役） | 13 | 0 |
| `backend/services/workflow/preflight_service.py`（历史基线，现已退役） | 13 | 0 |
| [backend/services/deck/admin_gateway.py](../../backend/services/deck/admin_gateway.py) | 12 | 0 |
| [backend/services/runtime_plugin/reconcile_service.py](../../backend/services/runtime_plugin/reconcile_service.py) | 12 | 0 |
| `backend/services/deck/content_versioning.py`（历史基线，现已退役） | 11 | 1 |
| `backend/services/deck_plugin/release_service.py`（历史基线，现已退役） | 11 | 0 |
| [backend/services/deck_plugin/installation_service.py](../../backend/services/deck_plugin/installation_service.py) | 7 | 0 |
| [backend/routers/claude_plugins.py](../../backend/routers/claude_plugins.py) | 6 | 0 |
| [backend/schema/capabilities.py](../../backend/schema/capabilities.py) | 6 | 0 |
| [backend/services/deck/builtin_plugin.py](../../backend/services/deck/builtin_plugin.py) | 6 | 0 |
| [backend/services/deck_plugin/rollback_manager.py](../../backend/services/deck_plugin/rollback_manager.py) | 6 | 0 |
| `backend/services/deck/runtime_context.py`（历史基线，现已退役） | 5 | 0 |
| `backend/services/deck_plugin/compatibility_service.py`（历史基线，现已退役） | 5 | 0 |
| [backend/services/runtime_plugin/materialization_manager.py](../../backend/services/runtime_plugin/materialization_manager.py) | 5 | 0 |
| [backend/services/claude_plugin/marketplace_service.py](../../backend/services/claude_plugin/marketplace_service.py) | 4 | 0 |
| [backend/services/deck/story_workflow_application.py](../../backend/services/deck/story_workflow_application.py) | 4 | 0 |
| `backend/services/deck_plugin/selection_validation_service.py`（历史基线，现已退役） | 4 | 0 |
| `backend/services/events/event_emitter.py`（迁移前基线，现已删除） | 4 | 0 |
| [backend/services/story_workspace/dream_artifact_turn_hook.py](../../backend/services/story_workspace/dream_artifact_turn_hook.py) | 4 | 0 |
| [backend/services/story_workspace/dream_auto_repair_service.py](../../backend/services/story_workspace/dream_auto_repair_service.py) | 4 | 0 |
| [backend/claude_agent/service.py](../../backend/claude_agent/service.py) | 3 | 0 |
| `backend/services/claude_plugin/deck_refs_service.py`（历史基线，现已退役） | 3 | 0 |
| [backend/services/story_workspace/dream_runtime_activation_service.py](../../backend/services/story_workspace/dream_runtime_activation_service.py) | 3 | 0 |
| [backend/libs/claude_agent_kit/server/editor_tool.py](../../backend/libs/claude_agent_kit/server/editor_tool.py) | 2 | 0 |
| [backend/libs/claude_agent_kit/server/story_workspace_tool.py](../../backend/libs/claude_agent_kit/server/story_workspace_tool.py) | 2 | 0 |
| [backend/server.py](../../backend/server.py) | 2 | 0 |
| [backend/services/claude_agent/remote_interaction_guard.py](../../backend/services/claude_agent/remote_interaction_guard.py) | 2 | 0 |
| [backend/services/claude_plugin/workspace_packer.py](../../backend/services/claude_plugin/workspace_packer.py) | 2 | 0 |
| [backend/services/deck/agent_type.py](../../backend/services/deck/agent_type.py) | 2 | 0 |
| [backend/services/deck/chat_context.py](../../backend/services/deck/chat_context.py) | 2 | 0 |
| [backend/services/story_workspace/artifact_story_index_reconcile.py](../../backend/services/story_workspace/artifact_story_index_reconcile.py) | 2 | 0 |
| [backend/services/story_workspace/guidance_service.py](../../backend/services/story_workspace/guidance_service.py) | 2 | 0 |
| `backend/services/admin_product/identity.py`（迁移前基线，现已删除） | 1 | 0 |
| [backend/services/story_workspace/dream_reentry_service.py](../../backend/services/story_workspace/dream_reentry_service.py) | 1 | 2 |
| `backend/services/story_workspace/dream_thread_binding.py`（迁移前基线，现已删除） | 1 | 0 |
| [backend/tools/session_inspector.py](../../backend/tools/session_inspector.py) | 1 | 0 |
| [backend/claude_mcp/repository.py](../../backend/claude_mcp/repository.py) | 0 | 5 |
| [backend/claude_mcp/service.py](../../backend/claude_mcp/service.py) | 0 | 0 |
| [backend/notion/store.py](../../backend/notion/store.py) | 0 | 1 |
| [backend/persistence/postgres.py](../../backend/persistence/postgres.py) | 0 | 0 |
| [backend/services/admin_product/runtime.py](../../backend/services/admin_product/runtime.py) | 0 | 0 |

重点未关闭：database通用助手/Session与assistant，Story Workspace/PF/Run/source/dispatch/确认/产物Repository，Plugin install/catalog/refs-runtime/packer，Deck binding/content/runtime/Gateway，Editor/stdio、Notion pools与startup。Product pool 已关闭；MCP managed persistence 已由后续 Registry147 阶段关闭。revocation_service仍有sqlite3源码import，必须继续按运行入口及Schema协议清理，不能新建SQLite fallback。普通用户/模型/共享FS/Runtime验证由实际入口及发布capability决定，不使用环境标签跳过。

### Runtime/共享文件回归与授权依赖

2026-09-15指定workspace/pipeline/sdk_env三文件技术合同105pass/8.35s exit0。只验证原本地路径/TMPDIR/artifact/SDK合同，未证明真实CLI、模型、共享文件HTTP OAuth或normal PostgreSQL链路。该105项旧回执时Workspace harness尚未配置Admin owner；阶段29适配实际OAuth/typed Thread lookup，阶段40又把SystemConfig读取改为Admin user/Thread operation。Gateway CLI旧全局key/本地subject JWT仍是迁移入口；阶段33完整342项技术套件不把旧auth mock当完整验收。

### 通用database helper与DI调用候选

阶段35后同一只读scanner扫描299模块并补扫嵌套import、直接导入helper与模块alias：34个模块仍导入legacy database，118处直接helper Call候选，exit0/parse_errors=[]。Workspace ownership helper已移除一次源码Call（由两GET调用），剩余两处SystemConfig；当前47字面SQL模块/512候选与16driver模块；删除DeckPlugin resolver的roleSQL/default get_db和binding默认get_db，后台原事务保留。以下同时列出零Call但仍把helper作为DI/default callback传递的模块；这些不能据零Call视为关闭。静态候选还可能含已退役/不可达路径，后续依公开入口与发布capability复核，不当作运行时调用次数。

| database引用模块 | 直接helper调用候选 |
| --- | --- |
| [backend/services/story_workspace/dream_launch_infrastructure.py](../../backend/services/story_workspace/dream_launch_infrastructure.py) | 1 |
| [backend/routers/story_workspace.py](../../backend/routers/story_workspace.py) | 1 |
| [backend/services/deck/admin_gateway.py](../../backend/services/deck/admin_gateway.py) | 1 |
| `backend/services/deck_plugin/release_service.py`（历史基线，现已退役） | 1 |
| [backend/routers/claude_plugins.py](../../backend/routers/claude_plugins.py) | 9 |
| [backend/services/deck/story_workflow_application.py](../../backend/services/deck/story_workflow_application.py) | 14 |
| [backend/services/story_workspace/dream_artifact_turn_hook.py](../../backend/services/story_workspace/dream_artifact_turn_hook.py) | 5 |
| [backend/services/story_workspace/dream_auto_repair_service.py](../../backend/services/story_workspace/dream_auto_repair_service.py) | 2 |
| [backend/claude_agent/service.py](../../backend/claude_agent/service.py) | 12 |
| `backend/services/claude_plugin/deck_refs_service.py`（历史基线，现已退役） | 1 |
| [backend/libs/claude_agent_kit/server/editor_tool.py](../../backend/libs/claude_agent_kit/server/editor_tool.py) | 2 |
| [backend/libs/claude_agent_kit/server/story_workspace_tool.py](../../backend/libs/claude_agent_kit/server/story_workspace_tool.py) | 1 |
| [backend/server.py](../../backend/server.py) | 4 |
| [backend/services/story_workspace/guidance_service.py](../../backend/services/story_workspace/guidance_service.py) | 1 |
| `backend/services/story_workspace/dream_thread_binding.py`（迁移前基线，现已删除） | 0 |
| [backend/tools/session_inspector.py](../../backend/tools/session_inspector.py) | 5 |
| [backend/claude_agent/context_builder.py](../../backend/claude_agent/context_builder.py) | 0 |
| [backend/claude_mcp/credentials.py](../../backend/claude_mcp/credentials.py) | 1 |
| [backend/libs/claude_agent_kit/server/sessions_tool.py](../../backend/libs/claude_agent_kit/server/sessions_tool.py) | 1 |
| [backend/notion/credentials.py](../../backend/notion/credentials.py) | 1 |
| [backend/reflections_agent.py](../../backend/reflections_agent.py) | 15 |
| [backend/routers/auth.py](../../backend/routers/auth.py) | 3 |
| [backend/routers/claude_agent.py](../../backend/routers/claude_agent.py) | 2 |
| [backend/routers/deck_plugin_binding.py](../../backend/routers/deck_plugin_binding.py) | 2 |
| [backend/routers/pictures.py](../../backend/routers/pictures.py) | 3 |
| [backend/routers/reflections.py](../../backend/routers/reflections.py) | 17 |
| [backend/routers/reports.py](../../backend/routers/reports.py) | 2 |
| [backend/routers/system_config.py](../../backend/routers/system_config.py) | 3 |
| [backend/routers/voices.py](../../backend/routers/voices.py) | 1 |
| [backend/routers/workspace.py](../../backend/routers/workspace.py) | 2 |
| [backend/services/admin_gateway/selection.py](../../backend/services/admin_gateway/selection.py) | 0 |
| [backend/services/deck/defaults.py](../../backend/services/deck/defaults.py) | 3 |
| [backend/services/story_workspace/dream_launch_endpoint_service.py](../../backend/services/story_workspace/dream_launch_endpoint_service.py) | 0 |
| [backend/tools/session_inserter.py](../../backend/tools/session_inserter.py) | 3 |

## SystemConfig 生产读取与身份复查 · 阶段32历史定位

> 本节保留阶段32发现发布前缺口的原文；其“未发布、仍直接读取”结论已由上方阶段40当前映射取代。

当前源码 AST 复查得到六个直接 getter、一个直接 saver、三个 getter 注入引用及两个 reader 引用；后两个分别为实际调用和兼容函数转发。它们仍使用 `user_preferences.system_config_json`；已接入的 Preferences 五项字段不能覆盖此列。旧 save 用 `current.update(patch)` 合并已保存对象，保留未知 keys，更新时间并提交；SQL、owner 校验、并发/CAS、JSON 合并和持久化需要独立 Admin domain，尚未发布。Dream 继续负责公开键过滤、Gateway callable/modelAlias 校验及 env/sandbox/user keys 清理。

| 生产位置 | 当前输入与行为 | 消费新 Admin domain 所需凭据与绑定 | 当前缺口 |
| --- | --- | --- | --- |
| [设置 GET](../../backend/routers/system_config.py#L229)、[PUT](../../backend/routers/system_config.py#L236) | get_current_user 返回当前账户；GET 一次读取，PUT 先清理 patch，再 save 和读取公开投影 | 复用 `_admin_actor: AdminRequestActor` 和 `AdminRequestAuth.client`，GET dream:read、PUT dream:write；canonical ID 只用于结果匹配 | 仍直接 get/save；模型目录旧客户端也仍需接线 |
| [公开 Chat 模型选择](../../backend/routers/claude_agent.py#L660) | user_id/body.model 传纯 selection；helper 显式注入旧 getter | 在公开 ingress 的 immutable OAuth actor 上读取配置并提供 server-owned reader/snapshot；不把 ID 转成 credential | helper 只接 ID；[selection 两默认 reader](../../backend/services/admin_gateway/selection.py#L29)仍指向旧 getter |
| [公开 Chat 附件](../../backend/routers/claude_agent.py#L1035) | Workspace Mode 和网络配置，位于附件下载/FS 同步前 | 当前 ingress 已有 OAuth actor，可复用；保留 Mode/path/FS 执行顺序 | 仍直接读取；失败当前 500，迁移必须定义 Admin unavailable 的安全错误 |
| [Workspace 初始化](../../backend/routers/workspace.py#L152)、[Mode 校验](../../backend/routers/workspace.py#L211) | current_user ID；前者异常使用现有 defaults，后者异常 503、关闭时 409 | 两公开 GET 使用当前 OAuth dream:read；现有 Thread ownership 已由 Admin 验证，配置不使用 Editor token | 两次旧 getter 仍在；前者 fallback 不能冒称新 domain 的 fail-closed 行为 |
| [Agent assemble_context](../../backend/claude_agent/service.py#L1655) | request.user_id；读取 prompt/env/IM/Workspace/sandbox 后再构造 Runner；当前异常日志并继续 | 公开普通 Chat/Run 已携带 `AdminTurnPersistence`，其 `current_grant(actor_id, thread_id)` 返回后台续期的 server-persistence idg，绑定同一 Thread 和 authoritative Run（普通 Chat 为 null）；新 domain 必须明确接受该 purpose、dream:read 和请求绑定，并在 Admin 验证 active owner | 当前仍 `int(request.user_id)` +旧 getter；持久化 owner 尚无配置读取方法，不能因它已接 Thread/Session 就宣称配置已迁移 |
| [内部 Dream 模型选择](../../backend/claude_agent/service.py#L1706) | dream_context 非 null 后再次调用 `_platform_model_resolver(request.user_id, request.model)` | 同一 server-owned Thread/Run grant 或明确 OAuth ingress snapshot；内部 dispatcher 尚未向 request 接入该 owner，缺凭据应在新边界拒绝 | service 默认 resolver 仍调用旧 catalog/getter；不能使用全局 Gateway key 或 ID 补签 JWT 代替授权 |
| [Editor stdio](../../backend/libs/claude_agent_kit/server/editor_mcp_stdio.py)、[Editor tool](../../backend/libs/claude_agent_kit/server/editor_tool.py#L270)、[ContextBuilder](../../backend/claude_agent/context_builder.py#L407) | 没有直接 SystemConfig getter；ContextBuilder 只接 service 传入的 configured_system_prompt。Editor state 和 recent sessions 则仍有独立 DB 读取 | Agent 服务中的配置读取仍走服务器 persistence 身份；Editor 子进程只能接已发布的 editor-stdio idg、editor:read/write 和绑定 Session，不能读取全账户 SystemConfig，也不能收到 server-persistence/OAuth/service/DB secret | [_editor_mcp_stdio_config](../../backend/libs/claude_agent_kit/server/agent_runner.py#L2202)当前仍投影 actor ID 与 DATABASE_URL，独立 Editor 迁移未关闭 |

身份协议以实际 [delegation DTO](../../backend/services/admin_data/delegation.py#L25)为准：server-persistence 与 gateway-cli 的 editor_session_id 必须 null；只有 editor-stdio 可以具有非 null Editor Session。当前 Admin Editor handler 显式要求 editor-stdio 与 editor scope，其内部 OAuth 分支也要求对应 editor scope；不存在可复用的“Editor server-persistence” grant。配置 getter 的服务端身份与 Editor state 的子进程身份分别定义，不能为清理文档改 purpose/scopes。创建 grant 必须以真实 OAuth actor 授权，并由 Admin 检查 Thread/Run/Editor ownership 和 authoritative Workflow context；service credential 单独存在不能替代用户授权。

阶段32后的只读 artifact 已见 76 个合同，新增 workspace-default.ensure；未见 SystemConfig 合同。此观察仅为本地 producer 源码/注册 artifact 证据，不代表正常服务部署或真实账户验收。

### 阶段33默认 Workspace 接入范围

[workspace_data](../../backend/services/admin_data/workspace_data.py)复用 existing typed consumer，新增empty ensure DTO/原text ID DTO/实际hash/two schema与显式原两态receipt；[Workflow ingress](../../backend/routers/story_workspace.py)不再在 `_story_workflow_current_user` 打开DB，保留服务器workspace_id分支。PF POST与Run read/create/retry的完整入口均调用actualAdmin default再领域操作，初始化OAuthwrite-only/unknown stop/no resend。独立 internal agent-output 的旧 default helper和get_db仍在，其他生命周期函数未改。SystemConfig六getter/一saver/三个injection/two reader证据保持；资源provider/Runtime/文件/TMPDIR不改，注册76数量不等于全SQL或正常模型验收。

阶段33重跑当前扫描为299模块/48 SQL-bearing/513literal/16driver-persistence imports/35legacy imports/**120**direct legacy helper calls，parse_errors=[]/exit0；相对阶段32仅默认helper中的一次get_db移除，残留SQL模块/字面候选数量保持。以上为完整声明scope内源码候选，不是全生产可达SQL关闭证据。

### 阶段34公开Run cancel

run_data复用Run28 model/two exact schemas增加cancel actualhash/requirednullable raw reason/绑定cancelled结果和原两态receipt；request owner通过原tuple注册第四项Run操作。[公开cancel](../../backend/routers/story_workspace.py)复用actual default loader→Admin取消，原reason/default/范围/编码、200/28fields/八errors/404/scoped安全422/unknown UUID保持，旧application SQL不再由该公开函数调用；其余Story函数、原application/WorkflowRunService/Agent/Runtime/资源/FS/TMPDIR字节保持。剩余两个current-user default resolver在Deck插件/binding待下一阶段复用统一client，DeckPlugin roleSQL亦单独追踪；internal agent-output/后台输出默认helper保持，未将default初始化操作冒用为这些事务的授权。SystemConfig仍未发布，Coordinator独立provider候选不属于本任务。

### 阶段35三个公开默认 resolver

[shared deps](../../backend/routers/deps.py)直接复用阶段33typed Story helper算法，三个wrapper统一调用，default resolver没有get_db/SQL。Deck Plugin role读取复用当前Profile OAuthread/canonicalID/rawrole，原permission/scope/DTO不改，失败不使用user fallback。当前scanner299/47SQL-bearing/512literal/16driver/34legacy imports/118helper、parse_errors=[]；完整声明scope的SQL/legacy tables按此次差异更新，不把源码候选视为全生产可达闭环。其余background/internal default helper、binding/control-plane领域DB/Runtime/Gateway/SystemConfig继续开放。artifact实际77的新dream-launch-failure.envelope只观察到注册，尚未消费；本阶段两个旧API specs不变、client63。
## 阶段36：Run fail / failure envelope 类型消费准备

现有 run_data 注册 workflow-run.fail，actual SHA79e2fbb8f96aa241b664657f03e77020d9cbd2cc8f8b67eeae89a02ea34ac31f；复用原28字段/current actor/Workspace/Run/failed 检查，不以本次失败参数覆盖原 same-failed replay。launch_metadata_data 注册 actual77 dream-launch-failure.envelope，SHA5967ae40f60858553f27f43dd83f021f93928e7c25c582d2e711d68df4d4e042；input仅Workspace/Run/rawerror，五字段reply匹配服务器nullable source/error/Run，updatedfalse保留，显式原两态receipt/no resend。两项同为v1/write/dream:write/bgnull与identity/unified两exactschema；requestclient65、resource2独立。

本阶段没有选择原生产 launch builder/dispatcher/failure recorder；后者仍缺 Admin turn owner，SQL scanner不得减去其SQL。正常流程必须先确认 Run fail COMMIT，再独立写 failure envelope；unknown不能假定rollback或提交。OAuth/sameThread+Run server persistence写和OAuth-only original GET的权限由发布Admin边界负责，不增加Runtime recovery或caller actor/source/context/metadata/codec权限。当前全SQL/driver/legacy inventory范围保持，normalPG/model/Runtime/CLIEditor/SystemConfig其余迁移与77primary隔离故障验收继续独立追踪。
阶段36fresh七文件provider-free回归386passed/4.26s/exit0，无failed/skipped；两次旧矩阵fixture/导入错误分别375pass2fail与373pass4fail均在计划保留。Actual77 contract check exit0/PASS，failinput/envelopeinput+output完整schema与published要求一致，failoutput原read28相同，client65/Run5/launch4、499其它trackedbackend Python bytes保持；原launch/resource/Runner/FS/TMPDIR没有接线或改动。Scanner299/47SQL-bearing/512literal/16driver/34legacy imports/118helper、parse_errors=[]保持阶段35范围。Normal账户/PG/model/Runtime及后台owner/生产SQL仍未验收，不能按operation注册计数宣布迁移完成。详见[执行计划](dream-admin-auth-data-plan.md#阶段36实现与技术回执)。
## 阶段37：Workspace76 mandatory Luna 独立回执

Root实际读取[command receipt](/private/tmp/dream-admin-stage37-workspace76-validation/luna/command-receipt.json)与stdout/stderr：exactfocused3file argv/cwd、exit0、wall2541ms，66passed/18deselected/2.12s，stderr空；非正常账户/PG/model业务。source-only fresh [receipt](/private/tmp/dream-admin-stage37-workspace76-validation/source/command-receipt.json) exit0/PASS，[闭环文件/原source ordering/10sourceSHA/完整SQL-driver-legacy候选列表](/private/tmp/dream-admin-stage37-workspace76-validation/source/workspace76-source-closure.json)已生成，source与8447a80a相同，没有功能代码变更。

接受范围仅three default resolver/strict empty DTO/rawID/currentOAuthcanonical/profile与original two-state receipt/no retry、Thread content/download ownership先于Mode/path/FS的fences；末端Deck领域provider为test DI、Story output/其它领域/正常TMPBash不包含。原Admin/SQL created_at ASC/id ASC ordering与NULL处理不在Dream重实现。story_workspace.py::receive_agent_story_output → agent_integration.py::get_or_create_default_workspace和store_agent_story_output整体SQL事务保留，无published完整StoryoutputAPI，不能拆成独立ensure造成一致性丢失。scanner snapshot299/47SQL/512literal/16driver/34legacy/118helpers不变，globalgoal未完成。首个Luna date writer与source Runner路径前置失败保留在[计划](dream-admin-auth-data-plan.md#阶段37独立回执与实际闭环边界)，未伪称API失败或抹去失败。

## 阶段38：公开 Chat assistant writer

[AdminTurnPersistence](../../backend/services/admin_data/turn_persistence.py)在既有server-persistence owner中增加`chat-message.persist`，继续绑定canonical actor、authoritative Thread/Run、dream read/write与空Editor Session。input沿用已发布八字段和原history validator；成功assistant保留完整parts、metadata与final projection，cancel/error partial保留parts及`null/false/null` projection。Service为assistant生成独立服务器message ID，不复用user message或SSE turn ID。四项schema校验复用[Workspace consumer](../../backend/services/admin_data/workspace_data.py)原算法，每次command与unknown receipt恢复前fresh读取；缺失、重复或任一hash漂移在POST前503。

user/Session/assistant共用一个pending。timeout或坏reply保留原operation、immutable input与UUID，阻止不同写；同输入只查原receipt，absent保持unknown，committed且message ID匹配才清除。公开完整写失败保持原`ClaudeAgentAssistantPersistenceError`与Hook抑制，partial保持原日志/吞错，无parts继续no-op；SDK final safeguard顺序、Factory/Runner/EventBus/SSE/admission/lease、资源LKG、共享FS与TMPDIR不改。缺authoritative owner的内部dispatcher仍使用原SQL helper，本阶段没有给actor ID或service credential增加权限。

mandatory Luna第一次focused运行exit1，结果28passed/6failed/69deselected；六项失败都是fixture误认为fresh schema GET不会增加请求数，实际新增请求全是`/capabilities` GET且无POST。只修断言后fresh复跑exit0，34passed/69deselected/1.05s，stderr空；Root已读取[首次回执](/private/tmp/dream-admin-stage38-assistant-validation/luna/command-receipt.json)、[复跑回执](/private/tmp/dream-admin-stage38-assistant-validation/luna-rerun/command-receipt.json)及两轮stdout/stderr。

source checker首次因捕获进程未继承`PYTHONPATH`在导入前exit1，保留[回执](/private/tmp/dream-admin-stage38-assistant-validation/source/command-receipt.json)；显式环境重跑[exit0/PASS](/private/tmp/dream-admin-stage38-assistant-validation/source-rerun/command-receipt.json)：actual operations 77、`chat-message.persist`原SHA/八字段、四schema、完整/部分构造和SDK顺序AST、原user/Session方法及500个其它backend Python文件保持，内部SQL gap明确存在，normal acceptance=false。fresh scanner [exit0](/private/tmp/dream-admin-stage38-assistant-validation/scanner/command-receipt.json)：299模块、47 SQL-bearing、512字面SQL候选、16 driver、34 legacy import、117直接helper调用、parse_errors=[]；仅公开Service减少一个legacy helper调用候选，不表示其余数据库领域完成。

## 2026-09-16 Product BFF 数据边界关闭

| Dream 入口 | 迁移前访问 | Admin 目标与 DTO/ORM | Dream 替换 | 验收证据 |
|---|---|---|---|---|
| `backend/services/admin_product/identity.py` | 直接读取 `users(id, email, is_active)` | 共享 Admin OAuth `/principal` 提供 canonical ID；Admin Product Repository 在业务 ORM 查询前复核 active canonical/platform identity | 文件删除；不接受 caller user ID | Product subject binding 与 mismatched response 测试通过 |
| [backend/services/admin_product/runtime.py](../../backend/services/admin_product/runtime.py) | 为一次身份读取创建 Dream `PostgresPool` | 既有 Admin Product strict DTO + signed Product JWT + Product service/Repository事务 | 仅延迟创建 `AdminProductClient` | composition source fence 无 pool/persistence/DATABASE_URL/SQL |
| [backend/routers/product.py](../../backend/routers/product.py) | 旧同步调用 Dream auth，并尝试本地 session renewal | 复用共享异步 `AdminRequestAuth`；GET/POST 分别要求 `dream:read`/`dream:write` | canonical subject 只来自 Admin principal；保留Pydantic DTO、origin、幂等和安全错误 | focused route/client 21 passed |

本阶段没有新增 Admin schema、migration 或重复 Product API。Admin 已有 Product
Repository 保留业务事务和数据权限；Dream 不会在 Admin OAuth 或 Product API
不可用时退回 PostgreSQL。dirty-safe AST 回执
[dream-db-closure-after-product-bff-source-only.json](admin-auth-data-verification/dream-db-closure-after-product-bff-source-only.json)
实际扫描553个Python模块，当前生产候选78、SQL模块44、SQL literal 404、driver或
database import模块17、legacy helper调用38、transaction/connection调用308、
Admin operation名168、parse error 0；`admin_product` entries为空。本结果只关闭
Product BFF，余下生产候选继续按本清单迁移。

## 2026-09-16 Deck 删除错误边界关闭

| Dream 入口 | 迁移前访问 | Admin 目标与 DTO/ORM | Dream 替换 | 验收证据 |
|---|---|---|---|---|
| [backend/routers/voices.py](../../backend/routers/voices.py) | 公共删除已调用 Admin；仅为构造四类409文案而传递导入整个 Dream `database` 模块 | `deck.delete` strict input/result/error DTO；Admin typed Drizzle Repository执行owner、引用关系和事务检查 | route-owned闭合集合把已校验的reason映射为原文案；不执行SQL、不接受user ID、不回退数据库 | 四reason行为测试、production source fence与全仓source-only复扫 |

本阶段不改变 `deck.delete` capability、schema hash、receipt、状态码或 Admin
事务。缺少 details 仍使用原通用引用文案；未知 reason 或带额外字段的错误体在
strict DTO解析时继续 fail closed。共享文件系统、Runtime、SSE、资源策略与其他
Deck 内部数据库入口不在本次小闭环范围内。

实际 source-only 回执
[dream-db-closure-after-deck-route-source-only.json](admin-auth-data-verification/dream-db-closure-after-deck-route-source-only.json)
扫描553个Python模块，当前生产候选78、SQL模块44、SQL literal 404、driver或
database import模块16、legacy helper调用37、transaction/connection调用308、
Admin operation名168、parse error 0。`voices.py` 条目只剩Admin DTO imports，
其SQL、driver/database import、legacy helper与transaction字段均为空。

## 2026-09-16 Workflow Context 旧解析器退役

| Dream 文件与入口 | 迁移前访问 | 事务/并发要求 | 目标 Admin 模块与接口 | Dream 替换方式 | 验收证据 |
|---|---|---|---|---|---|
| `backend/services/story_workspace/dream_thread_binding.py` | 直接聚合`chat_thread`、`chat_message`、`workflow_runs`、Workspace与binding并在Dream重算retry/provenance | 完整retry图、同一owner与binding revision必须来自同一数据快照；冲突在Runtime前失败 | `workflow-context.resolve` strict Thread-only DTO → Admin service → typed Drizzle `WorkflowContextRepository` | 旧模块和旧算法测试删除；公开Chat已有`AdminRequestAuth.workflow_context`，Service只消费immutable `AdminWorkflowResolution` | Admin consumer、Chat ingress和Agent Service回归；production source fence；source-only复扫 |
| [backend/services/deck/story_workflow_application.py](../../backend/services/deck/story_workflow_application.py) | 两个未使用resolver import使旧模块仍属于production import图 | 无业务I/O；只需去除死引用 | 同上 | 删除两个import分支中的旧symbol | AST确认symbol零引用并通过模块编译 |

Admin producer保留完整 owner、retry leaf、launch message、Workspace、Deck/plugin、
revision、runtime snapshot和状态校验；Dream不复制该算法，也不从请求接受Run、actor
或retry selector。普通Chat或终态链仍返回 `context: null`。Agent Service保留显式
测试mapper seam，但生产请求缺少Admin snapshot时继续配置失败，不会打开数据库。

实际 source-only 回执
[dream-db-closure-after-workflow-context-retirement-source-only.json](admin-auth-data-verification/dream-db-closure-after-workflow-context-retirement-source-only.json)
扫描551个Python模块，当前生产候选77、SQL模块43、SQL literal 403、driver或
database import模块15、legacy helper调用37、transaction/connection调用308、
Admin operation名168、parse error 0。相对上一回执减少两个Python模块（旧生产
resolver与其旧测试）、一个生产SQL模块、一个SQL literal和一个database import
模块；旧模块名不再出现在任何生产import中。

## 2026-09-16 未使用 Event 持久化路径退役

全仓生产调用搜索确认 `EventEmitter` 没有业务调用者，仅由它自己的测试和一个
opt-in旧PostgreSQL integration case导入。因此本阶段删除
`backend/services/events/event_emitter.py` 及两处专属测试，不为不存在的业务
流程创建通用event CRUD或无权限语义的Admin操作。`EventEnvelope` strict frozen
DTO和纯内存`EventConsumer`继续保留；测试改为直接构造DTO，覆盖十类必需payload、
递归敏感字段拒绝、ID去重、aggregate顺序和gap timeout。

`events` schema与历史设计记录未在本阶段删除。未来若出现真实持久化调用方，必须
根据该入口的actor、Workspace、幂等、aggregate version并发与事务边界设计具名
Admin DTO → Service → typed Drizzle Repository 操作，Dream不得恢复SQL路径。

实际 source-only 回执
[dream-db-closure-after-unused-event-retirement-source-only.json](admin-auth-data-verification/dream-db-closure-after-unused-event-retirement-source-only.json)
扫描550个Python模块，当前生产候选76、SQL模块42、SQL literal 400、driver或
database import模块14、legacy helper调用37、transaction/connection调用308、
Admin operation名168、parse error 0；相对上一回执减少一个无调用者的生产模块、
一个SQL模块、三个SQL literal和一个driver import模块。

## 2026-09-16 Deck CRUD 与内容版本旧 SQL 退役

公开 Deck list/detail/default/create/update/delete/fork/publish/sync、四项 Voice 写入和
五项 content-version 路由已经通过 strict Pydantic DTO 调用 Admin 具名业务操作；Admin
Service 与 typed Drizzle Repository 负责 actor 权限、聚合锁、draft revision、snapshot
hash、CAS、事务和原 request receipt。Dream 继续负责公开响应投影、共享 artifact/CLI
校验、Runtime、SSE 与共享文件系统，不保留数据库 fallback。

因此本阶段删除 `database.py` 中 22 个零生产调用者的 Deck/Voice/default helper、两个
Deck refs helper、显式 fixture seeding helper、`services/deck/content_versioning.py`，并把
`services/deck/agent_type.py` 收敛为纯 manifest → Chat/Dream 映射。仍被 startup 使用的
`backfill_builtin_deck_plugin_refs` 保留并继续列入后续迁移，不将本阶段误报为 Dream
全量无 PostgreSQL。

动态 f-string SQL 感知的 source-only 回执
[dream-db-closure-after-deck-crud-version-retirement-source-only.json](admin-auth-data-verification/dream-db-closure-after-deck-crud-version-retirement-source-only.json)
在同一 AST 口径下从 HEAD 的 297 个生产模块/29 个 SQL 模块/480 个 SQL call 变为
296/27/402，减少 1 个生产模块、2 个 SQL 模块、78 个 SQL call 和 137 个 connection
call；parse error 为 0。Agent 类型 SQL 为 0，退役 owned symbol 为 0，`database.py`
仍有 73 个 SQL call，说明全局关闭目标继续进行。
