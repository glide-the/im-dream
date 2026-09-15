<!-- [Sync] 2026-09-16: consume Registry130-132 launch Runtime operations and delete Dream provisioning SQL. -->
<!-- [Sync] 2026-09-16: consume Registry127-129 Agent-type operations with local artifact verification and no Dream database fallback. -->
<!-- [Sync] 2026-09-16: consume Registry121 claim-turn and inject claim-bound AdminTurnPersistence into confirmation Runtime. -->
<!-- [Sync] 2026-09-16: consume Registry120 Story confirmation DTOs and remove its production PostgreSQL state machine. -->
<!-- [Sync] 2026-09-15: consume Registry115 Story Guidance persistence and keep same-Thread Runtime dispatch in Dream. -->
<!-- [Sync] 2026-09-15: consume Registry114 Story catalog operations through strict DTOs and remove eleven production SQL routes. -->
<!-- [Sync] 2026-09-15: consume Registry111 Story review operations through strict DTOs and remove eight production SQL paths. -->
<!-- [Sync] 2026-09-15: close internal Agent Story output through the existing Registry109 DTO/ORM contract. -->
<!-- [Sync] 2026-09-15: bind Registry109 standalone Story output DTO/ORM UOW and original receipt recovery. -->
<!-- [Sync] 2026-09-15: bind Registry103 current-user picture list/full reads and original public projections. -->
<!-- [Sync] 2026-09-15: bind Registry101 local-data aggregate/first-login writes and legacy parsing behavior. -->
<!-- [Sync] 2026-09-15: specify user and Thread SystemConfig operations, ordering and fail-closed consumers. -->
<!-- [Sync] 2026-09-15: specify Reflections custom-config operations and Thread-to-config-to-filesystem ordering. -->
<!-- [Sync] 2026-09-15: public Editor tools use exact Admin purpose grants, operations and original-ID receipts; stdio DB credentials are removed. -->
<!-- [Sync] 2026-09-15: public assistant complete/partial writes use the bound turn owner; internal dispatcher SQL remains open. -->
<!-- [Sync] 2026-09-15: record complete Admin Deck list modes and remaining SQL source candidates. -->
<!-- [Sync] 2026-09-15: record unregistered Run create/retry and original hidden-source dispatch ordering. -->
<!-- [Sync] 2026-09-15: record Admin-owned Deck detail and unchanged legacy Memory projection. -->
<!-- [Sync] 2026-09-15: index five Admin Deck writes, shared schema gate and closed deletion feedback. -->
<!-- [Sync] 2026-09-15: define Voice current OAuth/Memory/optional fields and mutation receipts. -->
<!-- [Sync] 2026-09-15: define social identity, policy, original errors and unknown receipts. -->
<!-- [Sync] 2026-09-15: specify shared catalog synchronization, failed refresh and per-request concurrent dispatch. -->
<!-- [Sync] 2026-09-15: specify prepare/local verification/source recheck and unknown refs writes. -->
<!-- [Sync] 2026-09-15: specify abort/read identity and success-only logout snapshot ownership. -->
<!-- [Input] Admin canonical design v0.1, Dream entry/transaction scans and actual consumer DTO code. -->
<!-- [Output] Dream implementation review, six cross-project flows, state/failure and release gates. -->
<!-- [Pos] Dream consumer architecture; Admin owns API/DTO/domain/repository/ORM contracts. -->
<!-- [Sync] 2026-09-15: define resource HTTP owner drain and final shutdown ordering. -->
<!-- [Sync] 2026-09-15: define preference raw object projection, NULL merge and unknown-save recovery. -->
<!-- [Sync] 2026-09-15: define OAuth-only Deck version consumers, four exact capabilities and unknown commit handling. -->
<!-- [Sync] 2026-09-15: specify bound Thread/SDK Session operations, mutable confirmation reuse and scoped unknown recovery. -->
<!-- [Sync] 2026-09-15: specify bound recent Session prompt reads and Runtime-before failure behavior. -->
<!-- [Sync] 2026-09-15: specify public Session projection/events and reusable closed Editor state DTOs. -->
<!-- [Sync] 2026-09-15: specify atomic raw user persistence, short-lock renewal and terminal/cancel cleanup. -->
<!-- [Sync] 2026-09-15: record standalone authority refusal and named script account validation; preserve outstanding domain gates. -->
<!-- [Sync] 2026-09-14: record actual BFF/Browser, request identity, Chat/resource consumers and pending Runtime/full-domain gates. -->

# Dream / Admin 认证与数据交互

## Dream Launch Runtime（Registry130–132）

公开 `POST /api/story-workspace/dream-runs/start` 继续接受 Deck、nullable Voice、目标和幂等 key。`_story_workflow_current_user` 先完成 Admin bearer 校验及 default Workspace 解析；路由只从 `_admin_actor` 取得当前 access token，并构造 request-scoped `AdminDreamLaunchRuntime`。Token 不进入 DTO、日志、repr、Agent 环境或共享文件。缺失 Admin owner/actor 直接返回配置失败。

启动适配器先调用 `runtime-scope`，因此 disabled/越权 Deck、错误 Workspace 或 Voice 仍在模型目录、source、Preflight 和 Run 写入前失败。随后保留原 idempotency lookup：没有既有 Run 时调用 current plan；既有 queued Run 重放时提交该 Run 和 source Thread 作为 replay identity。Admin 用 typed Drizzle Repository 派生 active binding 或 Run-frozen stale binding/lock；Dream 不提交 Plugin/version、revision 选择、lock、数据库或路径。plan 返回不含路径的 candidate，Dream 复用现有 `verify_agent_type_runtime` 从 server-owned artifact store 推导路径并校验 digest、manifest 与 Claude CLI，然后调用 prepare。prepare 未知提交只读取原 operation/request receipt，不自动重发。

```mermaid
sequenceDiagram
  participant B as Dream Browser
  participant R as Dream Router
  participant L as Dream Launch Application
  participant A as Admin Registry130-132
  participant F as Shared artifact + Claude CLI
  participant P as Admin PostgreSQL
  B->>R: start Deck/Voice/goal/idempotency key + bearer
  R->>R: Admin auth + default Workspace
  R->>L: command + actor + request Runtime port
  L->>A: runtime-scope
  A->>P: enabled Deck/Workspace/Voice ORM check
  L->>L: existing idempotent Run lookup
  alt new Run
    L->>A: runtime-plan(current)
    A->>P: active binding + configured lock/installation
  else queued replay
    L->>A: runtime-plan(replay, Run, source Thread)
    A->>P: owned Run + Preflight + frozen binding/lock
  end
  A-->>L: binding + path-free candidate
  L->>F: verify digest + manifest + CLI
  L->>A: runtime-prepare + exact evidence
  A->>P: recheck + materialization + optional Workspace installation + receipt
  A-->>L: same binding + runtime_ready
  L->>L: unchanged source/Preflight/Run/dispatch flow
  L-->>B: accepted context or closed business error
```

三个 operation SHA 为 `67dbe0a6eb7ddfd9bd1fa668e38f143add53201b725b19506af976319bba2b92`、`efd986cef6f891202c4d3ceb889d7491e8227dc097eeb009202a2be92549e9a6` 与 `d9c2faeb03b86cf562286f283e5bfcd3098e1da81c1b628c2e9aaa5a7b897882`。Registry129 prefix SHA 保持 `686f0668c72ca6114d894392d2dd2a2fde228b87fa31a1b858fd1dd553663881`，完整 Registry132 SHA 为 `6e0149b3d3354d081564af21349f364cc092087d5aadce0d5164654a6c005bb2`。本阶段没有 schema/migration 变更。Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、共享 Workspace、`.claude-tmp` 与资源策略 LKG 没有改变；launch 其余持久化仍在迁移清单中，不能据此宣称 Dream 全域数据库关闭。

## Deck Plugin Binding 与 Agent Type（Registry122–129）

Dream 的 `plugin-options`、binding current、history、validate 和 save 五个公开入口保留原路径与 JSON 响应，但数据调用统一进入 `AdminDeckPluginBindingData`。严格 Pydantic 输入只包含 Deck、当前/default Workspace、Plugin/version、`next_run`、limit 和 expected revision；current OAuth actor 只从 `_admin_actor` 取得，不能由请求 DTO 或 header 提交用户 ID。返回 DTO 重新校验 Deck、Plugin/version、revision、时间与 selection summary，Admin 服务不可用或契约不匹配直接失败，不回退 Dream PostgreSQL。

`PUT /api/voice-decks/{deck_id}/agent-type` 也使用同一 consumer。Chat 调用 clear；Dream 先调用 runtime-plan，取得 Admin 根据服务端策略、release、lock 和 ready installation 选择的唯一候选。候选只有 package/version/digest/compatibility 等校验字段，没有 artifact path。Dream 从配置的共享 artifact store 派生实际路径，校验 digest、`.claude-plugin/plugin.json` 和本机 Claude CLI，再把精确 evidence 交给 runtime-prepare。Admin 在 receipt transaction 中重新选择并核对事实，幂等写或刷新 materialization，确保 Workspace installation；最后 Dream 使用既有 save CAS 改变 Agent type。

Admin 的对应 Zod DTO → Service → typed Drizzle Repository 在一个 transaction 中重复 owner 检查并读取 release、installation、runtime lock 与 materialization。save 在 receipt UOW 内锁 Deck，比较 expected revision，运行 compatibility，执行 active→stale、insert 下一 revision 和 Deck draft revision 推进。同选择是无副作用返回；冲突映射原409/current revision，selection 不允许映射原422 validation。网络结果未知时 Dream 只读取同 operation/request 的 original receipt，absent 或错配继续报告未知，不重发 POST。

```mermaid
sequenceDiagram
  participant UI as Dream UI
  participant API as Dream FastAPI
  participant ADM as Admin Registry122-129
  participant FS as Shared artifact + Claude CLI
  participant DB as Admin PostgreSQL
  UI->>API: binding read/validate/save
  API->>ADM: strict DTO + current OAuth + request_id
  ADM->>DB: Drizzle owner + compatibility
  alt save
    ADM->>DB: lock + CAS + stale/insert + draft + receipt
  end
  DB-->>ADM: committed projection
  ADM-->>API: strict DTO / closed error
  API-->>UI: unchanged public response
  UI->>API: select Dream Agent type + expected revision
  API->>ADM: runtime-plan
  ADM-->>API: closed candidate without path
  API->>FS: verify digest + manifest + CLI
  API->>ADM: runtime-prepare + immutable evidence
  ADM->>DB: recheck + materialization + Workspace installation + receipt
  API->>ADM: binding.save CAS
```

新增 clear/runtime-plan/runtime-prepare operation hash 为 `9a89ec380e280fc64b67b9725a68edf3244df0f76e41df8db5fd89b3e3fd44fc`、`87a3f0497e3927aa8c8048e6bc79de1b042631f096f85184568201dce378e5f7`、`9cc1a08d15e0279ed977bb5b7ee25a5ab270cf32a4f67ded719c23e33d000716`；Registry126 prefix SHA 保持 `67a18f69f0674270c5f316959a7d962ef7a8c201249f4c45ac3a780ed710eada`，Registry129 完整 SHA 为 `686f0668c72ca6114d894392d2dd2a2fde228b87fa31a1b858fd1dd553663881`。本阶段不改 schema 或 migration。Runtime、SSE、EventBus、共享 workspace、`.claude-tmp`、资源策略 LKG 均未改变；launch Runtime 后续契约见上节 Registry130-132。

Story Workspace confirmation现绑定Admin Registry120。Dream浏览器入口使用current OAuth先读取既有`run.read` DTO，校验actor、Run、source Thread与当前状态，然后在共享文件系统中完成两次相同projection/base-revision检查；只有检查稳定才把原camelCase confirmation command作为严格Pydantic DTO提交给Admin。Admin从OAuth主体重新派生owned Run/Workspace/Thread，生成canonical message/metadata，在一个typed Drizzle UOW完成普通user消息、Thread touch、Run transition和receipt。Dream不发送actor、message ID、状态、SQL、表列、数据库、路径或事务选择器，也不保留confirmation PostgreSQL fallback。

Admin只让新持久提交携带即时dispatch；业务幂等重放返回`dispatch:null`，由后台reconciler恢复，避免两个并发响应启动同一Runtime turn。Dream coordinator通过唯一Admin client和`story-confirmation:dispatch`服务scope执行claim/lease/ack：同claim重试恢复、过期租约可接管、不同claim不能续租或确认。Dream继续调度同一Thread Runtime，保留heartbeat、EventBus、SSE、turn/resume/cancel、Agent文件CAS和共享文件系统权限；`user_message_pre_persisted`只有Admin claim的严格message/actor/thread事实完全匹配时才跳过重复user消息保存。Admin失败、capability/hash/DTO错误、越权、状态冲突或未知写入均产生明确失败，不查询Dream数据库。

`submit/fact/claim/lease/ack`的operation SHA依次为`2571aa2cc9c19656c4ac90d33221da65e8a631657adebf9f535ab0fe3c76bb12`、`f455a6075161751d25a229dd64479e2a6d6ca781ea7aacfa5575ec4561f52beb`、`c049317c4383584a7574b11daea1b8c626875d589e0dbbd45dfb739c4ca8cde1`、`a5720992e5a0cbc39773481dd3f98a32e6b535c34ea24df230de6ad5646817e6`和`12aeed9beb6584354aa584ebadf7ce352d68084632c0d2c90a2c768c3a8626c6`，完整Registry120 SHA为`4b0bbfa8caecd42acf0ecc89be4153b6d6fb1e124aac4ff27e937ecb14904795`。本阶段不改数据库schema或Admin migration；其它Dream数据库候选仍按全域清单迁移，不能据此宣称全部关闭。

Story Workspace Guidance现绑定Admin Registry115。Dream从current OAuth构造严格`workflow_run_id/kind/text/step_id/idempotency_key` DTO，不发送actor、Workspace、Thread、message ID或数据库选择器。Admin锁定owned Run/Workspace/source Thread，要求Run为confirmed/failed，派生immutable message与fingerprint，在一个Drizzle UOW提交message、Thread touch、结果、audit及receipt；相同业务命令重放不改变Thread排序，changed input返回409。Dream只对new commit或original-receipt恢复返回的严格dispatch envelope调用既有同Thread Runtime；投递失败保留已提交命令并返回`dispatched:false`，业务replay不重复投递。operation SHA为`a061ed38d2ca10073bbb7fd078e679f072f0cbd4ff1ce900792fbf8725223727`，完整Registry115 SHA为`58ab3cd933165dca7d6ae2d6eb50f46ff8f148e8e7eaf3dd5e46ceab1ad2ba9b`。[Registry115源码扫描](../exec/admin-auth-data-verification/dream-db-closure-after-registry115-source-only.json)为545模块、49个SQL模块、452个SQL literal、27个driver/import模块、50个legacy helper、392个connection/transaction call和133个operation name，parse errors为空；其它数据库候选仍需迁移。

Story Workspace的Workspace get/patch、Story list/detail/patch、Character list/detail/patch与Scene list/detail/patch现绑定Admin Registry114。Dream只发送`workspace/action`、闭集`view`或闭集`resource_type/resource_id/patch` DTO；Pydantic RootModel校验响应的view、resource、ID、分页与时区时间，present-fields序列化保留omitted与显式null/false/zero/empty差异。Admin在typed Drizzle Repository中执行owner过滤、稳定排序、分页、详情关系、受控更新和Scene同owner Story检查。read不生成receipt；write未知只查询原request receipt且不重发。11个FastAPI响应及错误反馈保持，路由不再导入Dream database。三个契约SHA为`3fbd32dd7343ae5008d7f71f2475db1b022a95060f2544b9dfbea606af894965`、`317ed15c2f827c44099e0641693d3dcf09bc01186e26586a9b2281226faa142b`、`0ef2cc94d01d488c46a9872efb389b43890e9267460705ebee33ac5ab47180cd`，完整Registry114 SHA为`dc80b77410aac58528dde77578154d9848d9dfc3bf55de4a35c8c315a81af704`。修正后的[源码扫描](../exec/admin-auth-data-verification/dream-db-closure-after-registry114-source-only.json)仍有其它数据库候选，不能据此声明全域关闭。

Story Workspace七个单项审核入口与一个批量入口现绑定Admin Registry111。Dream从当前OAuth取得actor，只发送闭集`resource_type/resource_id(s)/action/notes` DTO；Pydantic验证Admin返回的资源类型、精确ID、时区时间以及批量updated/skipped按请求顺序组成的完整互斥分区。Admin在一个typed Drizzle UOW内执行owner、generated、pending、artifact revision、Story确认级联、逐项audit与operation receipt。Dream继续提供原公开路由、状态码和产品反馈；Admin不可用、权限拒绝、capability/DTO错误或未知提交均返回安全业务失败，未知只查原request receipt且不重发，也不调用Dream SQL。契约SHA为`9f741208c6096b38f414fc5fb7c53d045d771233055dd68005571e7b47392392`与`621206fde4e9322a042940e45234fadfa4bbe01ba5febea67faf7d2ad0050667`，完整Registry111 SHA为`01f1a9ffbd9daf44e9bc640768a13ae636d9e718cb42365ff2de1ba5c244efc3`；其它Story Workspace数据库入口仍按清单迁移。

公开Agent成功turn的standalone Story proposal绑定Admin Registry109：Dream保留`parse_agent_story_output`与既有post-turn失败隔离，只把strict Thread/Story/Character/Scene DTO交给当前`AdminTurnPersistence`。`POST /api/story-workspace/internal/agent-output`保留原Header、请求体和四字段成功响应，并以当前OAuth actor调用同一consumer；确定性输入/Thread错误保持422，服务、capability或未知提交返回可恢复的安全错误。Admin派生actor/Workspace/Deck，在一个typed Drizzle UOW中协调Story identity、Character name、Scene order、关系与计数并提交pending-review结果、receipt和audit。unknown响应仅以原request ID读取receipt，不重发POST；stored Thread必须与结果Thread相等，Run/Editor scope必须为空。两条生产入口均不调用Dream PostgreSQL，旧SQL实现仅留在测试oracle用于事务语义比对；普通Chat的assistant结果与原SSE终态保持。其它Story Workspace SQL仍按清单迁移。契约SHA `2b7d9180c78829df86289d717037ddbfd20ecee517d8213e0e71b9388cee65ed`，完整Registry109 SHA `48909feea302787bcbd0ed7a263212eeee163a0e3e7887acfda56cc2b421d513`。

共享Client以同一catalog锁覆盖readiness、完整refresh与operation广告检查，调用方不会读取加载期间的空广告。fresh成功后按exact合同判断；失败仍清空ready/广告，下一RequestAuth重新加载。领域HTTP在短检查锁外执行，DTO/token/request_id只属于该请求；多个refresh按获取锁顺序完成，不互相覆盖。receipt维持原二态、原UUID且不自动重发。

本地数据迁移绑定Admin Registry101提交`c051a58e9193b0f39f2b211ac9ff5182fea87d73`、tree`49cd33a9cdf0f73c1faebecc01baccfca0af7a5b`。`local-data.import`与`first-login.complete`的operation hash分别为`f2f13ac392be415b42bb9532d42e20bf04fef2400551cd2f528991f4f6de271d`和`f06bbfd87fd905139b40df61eccdda6726678adda304dcd141a0bf52cf874cb0`，均要求current OAuth `dream:write`及identity/unified exact v1 schema。Dream只负责旧localStorage的按字段解析、raw JSON编码、安全整数毫秒到RFC3339转换和公开响应映射；Admin从principal取得owner，以一个UOW执行Session owner检查和四类写入并提交receipt/audit。主导入某类无效不会阻止其它已规范化类别，calendar recovery非法仍固定400，首次登录 absent/0/1均以独立幂等操作完成。两项写响应未知时只查询同operation、同OAuth、同request ID的committed typed receipt；absent、查询失败或坏回执继续unknown，不重复POST，也不调用Dream `import_user_data`或`set_first_login_completed`。

当前用户图片历史绑定Admin Registry103提交`547e89896776627b43ecaab0a5ac848891f21a94`、tree`1eec30f84691d53a1cf35e04a4ccaf98c93c04f2`。`picture-history.list`与`picture-history.full`的operation hash分别为`d03993f15860caadba56b6788a4c1b1d0fa086e949f1831b6e805a2eabee028d`和`e35e76d3425641660da361f2671f0004042a3600b2f3d4072386233c0d90efa3`，要求current OAuth `dream:read`与相同identity/unified exact v1 schema。Dream把普通列表的null prompt映射为空字符串，范围列表保留nullable prompt，空白范围日期变null，合法范围保持双端包含；Admin按principal限制owner、日期倒序、thumbnail/full fallback与同日最新原图。无图null映射原404；日期非法保持固定400。scope、capability、transport或DTO失败不伪装为空列表，不查询Dream PostgreSQL，也不使用好友授权操作。完整状态与验收见[当前用户图片历史设计](../design/picture-history-current.md)。

公开好友九操作只用current OAuth与identity/unified exact gate，Admin从subject确定actor，URL仅选择friend/request。Admin唯一执行邀请码policy/pair与code锁/状态转换/原receipt；Dream保留公开int PK/nullable微秒/label/thumbnail/full字段、closed业务400、timeline null403/full falsey404。写unknown原UUID只查receipt，无retry；旧database九helper在I/O前拒绝，其它图片/import/后台SQL未据此关闭。完整功能规则与验收见[好友现行稿](../design/social-friendship-current.md)。

公开Voice四mutation只持current OAuth，exact四schema/actualhash；create optional→requirednullable，update原None省略/emptyfalsezero保留，Python rawMemory数值与原sort规则不经JS重编码。Admin执行defaults/order/ownedDeck-Voice锁/内容与thread/draft语义/TX回执；changed:false原404/closed create-fork原400，unknown原UUID无retry。Editor present-fields serializer提取共享base，Editor nullable检查不变。完整规则见[Voice现行稿](../design/voice-crud-current.md)。

公开Deck update/delete/publish/collect/sync使用五项当前OAuth Admin写操作与four exact schema。Admin执行锁、字段比较/draft、发布切换/parent detach、收藏复制/计数、同步及原receipt单事务；Dream保留None省略/空falsezero与原结果/status，不再预读发布或拆分收藏。错误详情按code仅保留Version两revision或Delete四reason；unknown原UUID无retry。详见[Deck写操作现行稿](../design/deck-mutations-current.md)。

## 背景与问题

Dream baseline `7d38715c` 的 Python/Next 架构保留，但 Python 登录 authority与全部生产DB访问移Admin。阶段40已把用户与Thread SystemConfig生产读取/写入改为三个Admin operation；其后fresh closure scanner数字记录在[清单](../exec/dream-admin-data-inventory.md)。源码候选不等于生产可达SQL证明，仍需结合[事务图](../exec/dream-admin-transaction-boundaries.json)与入口调用链复查。

本稿包含目标、评审与当前实现范围。Dream统一[客户端](../../backend/services/admin_data/client.py)、[严格DTO](../../backend/services/admin_data/models.py)与[JWT验证器](../../backend/services/admin_data/jwt_verifier.py)已接入Resource后台、共享请求身份/profile、Chat CRUD/history/ownership/初始message预留以及SystemConfig；Next BFF与Browser同源session已实现并通过类型/构建技术检查。Runtime server-persistence consumer/keeper已接公开user-turn、assistant完整/部分消息、Thread SystemConfig与Factory生命周期，Editor exact Session purpose已接公开Agent turn，CLI、缺owner的内部dispatcher与其余后台持久化仍待接；旧Dream issuer已退役，其余数据库领域与正常本机真实业务验收尚未完成；候选source/isolated proof不能代替正常部署能力。

## 目标与边界

[Admin唯一规范](/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/docs/architecture/admin-dream-auth-data-contract.md)定义API/DTO/operation/capability。Dream仅消费确切DTO并用Pydantic严格校验；Admin Request/Response DTO → domain service → typed repository → Drizzle ORM，ORM实体与公开DTO显式投影分离。不能把database函数RPC、PostgresRow、表列模型或远程逐statement transaction包装为HTTP。每个原事务组合变为明确业务操作，保留原公开Dream DTO/状态。

Next页面、FastAPI编排、Agent Runtime、Runner/ThreadFactory/service/EventBus/SSE、turn/resume/cancel、资源admission算法/比较/顺序与既有lease不改。共享FS仍Dream执行规范路径操作，Admin持有metadata与数据权限。Dream无生产PG凭据/连接库/SQL/pool/UOW/DDL路径；独立importer/技术fixture不得自动成为runtime依赖。

## 概念与规则

### 逐项设计评审

| 事项 | 现有证据/冲突 | 实现责任与调整 | 完成证据 |
| --- | --- | --- | --- |
| 认证authority | Authlib/HS256/默认secret/滑动renewal在Dream | Admin Better Auth/OAuth/JWKS；Dream Resource Server+BFF | 旧authority静态复查、Google/JWT/refresh生产入口 |
| 密码/注册产品能力 | AuthContext已有login/register，认证迁移不授权删功能 | Admin保留密码哈希/账户映射/注册并恢复OAuth上下文，Dream保留产品入口 | 既有密码登录、注册正常/失败与无旧JWT签发 |
| 数据访问 | database/独立Notion/MCP/Product pools与159事务候选 | Admin领域DTO/ORM单事务；Dream统一typed client/adapters | 每入口映射DTO/API/repository/commit/验证 |
| 服务与用户身份 | 旧任意actor env/服务HS256投影 | Admin client registry限定后台scopes；服务ID与credential两头、用户Bearer分开 | 权限拒绝/无actor override/后台tool委托 |
| BA与业务PK | BA sub为opaque ID，users.id仍业务PK | Admin显式subject_links；principal canonical_user_id十进制string | 映射/禁用/FK/billing验证，无邮箱自动合并 |
| 长turn | 用户access最多300s，后台持久化不能因过期丢事件 | Admin绑定subject/thread/run/scopes/service/client的opaque delegation与renew | 续期/禁用/权限/未知提交、不改cancel/lease |
| browser handle | Dream无DB，不能内存伪装durable session | Admin encrypted handle store，同client transaction/input绑定、refresh行锁 | PKCE/CSRF/并发refresh/原handle恢复 |
| REST/SSE/Voice | Browser bases可直达8765，Next无upgrade handler | REST/SSE经Dream同源BFF；现有speech-recognition WS固定关闭1008 | 同源Cookie/origin与流代理验证；不启用ASR |
| 写恢复 | HTTP超时不证明Admin事务rollback | request_id绑定输入摘要，业务+receipt单commit | 同键同值/异值/并发/unknown response/absent不重建ID |
| Story Guidance | 旧Dream Service直接查Run/Workspace/Thread并写Message | Registry115 strict DTO→Admin Service→typed Drizzle Repository；Dream只执行成功后的same-Thread Runtime dispatch | immutable message、replay不重排、changed conflict、并发、投递失败隔离、无Dream DB |
| 资源与Runtime | PG policy/provider/observer，server-ownedRuntime调参 | API独立provider/sink，LKG和模型metadata所有权保留 | monotonic revision/精确memory/global effort/最终model |
| FS/metadata | tool和service直接SQL +共享FS | Admin授权DTO/CAS/checkpoint；Dream realpath/no-symlink/实体绑定 | 写文件未知metadata恢复与thread tmp精确路径 |

### Google登录（BFF已实现，正常本机Google待验收）

```mermaid
sequenceDiagram
    participant B as Browser
    participant F as Dream Next BFF
    participant A as Admin Better Auth OAuth
    participant G as Google
    B->>F: 登录(受限return_to)
    F->>F: state/nonce/S256 PKCE短期HttpOnly事务cookie
    F-->>B: Admin authorization redirect
    B->>A: code authorization(resource/client/state)
    A->>G: 内置Google social sign-in
    G-->>A: Admin callback(code/state)
    A->>A: account/provider subject映射与独立管理权限
    A-->>B: code/state/iss到注册Dream callback
    B->>F: callback
    F->>F: state/issuer/redirect/PKCE校验并消费事务cookie
    F->>A: browser-sessions/exchange(service ID/credential)
    A-->>F: opaque handle/expires_at
    F-->>B: Dream host-only HttpOnly cookie与页面返回
```

### Dream API → Admin领域数据

```mermaid
sequenceDiagram
    participant B as Browser or CLI
    participant F as Dream BFF/Resource Server
    participant C as Dream AdminDataClient
    participant A as Admin DTO domain service
    participant R as Admin typed repository/Drizzle ORM
    B->>F: 同源handle或目标OAuth Bearer
    F->>F: JWT签名/ES256/at+jwt/issuer/audience/time/scope
    F->>C: 确切domain RequestDTO
    C->>A: service ID/credential +用户/受限委托 +request_id
    A->>A: principal映射/active/scope/实体权限
    A->>R: owned aggregate操作/锁/CAS
    R-->>A: domain数据(非ORM公开实体)
    A-->>C: 显式ResponseDTO/request_id
    C-->>F: Pydantic校验结果
    F-->>B: 保留公开Dream产品DTO
```

### Device OAuth（不能用Session兑换）

```mermaid
sequenceDiagram
    participant C as CLI public client
    participant A as Admin OAuth
    participant B as Browser
    C->>A: device/code(client/scopes/resource，无secret)
    A-->>C: device_code/user_code/verification_uri/interval/expiry
    B->>A: verification user_code
    A->>A: 登录并恢复device上下文，显示client/scopes/resource
    B->>A: approve或deny
    C->>A: oauth2/token(device grant)
    A->>A: 单事务poll/slow_down/expiry/decision/consume
    A-->>C: OAuth tokens或官方pending/denied/expired错误
```

### Refresh（只在Admin保管token）

```mermaid
sequenceDiagram
    participant F as Dream BFF
    participant A as Admin browser-session domain
    participant O as Admin OAuth Provider
    F->>A: resolve(service ID/credential/handle/request_id)
    A->>A: lock handle/expiry/client/principal
    alt token需刷新
        A->>O: OAuth refresh grant
        O->>O: 原子轮转/重放撤销
        O-->>A: successor token pair
        A->>A: 加密原子替换
    end
    A-->>F: access_token/principal/expires_at(仅server)
    Note over F,A: 超时只能同handle恢复，不盲重试外部refresh
```

### Agent持久化与原SSE

```mermaid
sequenceDiagram
    participant R as Dream Runtime/Runner
    participant D as Dream service
    participant A as Admin domain service
    participant DB as Admin repository/PG
    participant B as Browser EventBus/SSE
    R-->>D: 原Runtime事件
    D->>A: 确切persist DTO/绑定Run委托/request_id
    A->>DB: owned entity/lock/CAS/业务+audit+receipt
    DB-->>A: commit
    A-->>D: DTO/request_id
    D-->>B: 原顺序SSE事件
    Note over D,A: unknown提交查询原receipt，absent不证明rollback
    Note over R,D: admission/lease/turn/resume/cancel保持原语义
```

### 共享FS与metadata

```mermaid
sequenceDiagram
    participant D as Dream file/tool service
    participant A as Admin metadata domain
    participant FS as Shared FS
    D->>A: entity/thread/Run/revision授权DTO请求
    A->>A: subject映射/active/owned关系/路径metadata
    A-->>D: bounded相对路径/权限/revision DTO
    D->>D: realpath/root/thread/no-symlink检查
    D->>FS: 精确文件操作
    D->>A: metadata checkpoint/digest/request_id
    A->>A: 原子CAS metadata+receipt
    Note over D,FS: .claude-tmp在真实thread root，0700，无symlink，sandbox精确路径
```

### 配置与状态

用户SystemConfig由registered80的`user-system-config.get`、`user-system-config.patch`和`thread-system-config.get`提供。公开Settings GET使用current OAuth读取；PUT先在Dream执行公开字段清洗、模型与provider配对和Gateway目录校验，再向Admin提交closed ten-field patch。Admin只返回写入确认，Dream随后使用新的request ID执行独立GET，并从该结果生成原`{success,data}`响应。unknown写保留原request ID进入receipt恢复，不假定提交或自动重发。`config_json`由Python JSON decoder读取，保留任意精度整数、`1.0`、`-0.0`、Unicode与未知已保存字段；非法JSON、非object、NaN、Infinity或非有限嵌套数值按上游响应无效处理。

公开Chat在Thread/message校验后使用current OAuth读取一份用户snapshot，并同时提供给模型选择和附件处理。活动turn使用Factory持有的`AdminTurnPersistence`，以同一actor/Thread、authoritative Run和`server-persistence` grant调用Thread SystemConfig；此读取与user/Session/assistant写共享关闭排空锁。配置必须在Workflow mapper、prompt、Workspace、文件同步和Runtime options之前成功；Admin unavailable、合同漂移或坏JSON均终止该路径，不保留Dream DB/default fallback。Gateway selector只接受显式authorized snapshot；缺少turn owner与reader的内部dispatcher在映射上下文前返回配置错误，等待其生产owner接线。

全部公开Workspace文件入口在执行文件系统调用前读取current OAuth SystemConfig。list/upload/delete/move先做请求参数检查，再读配置；content/download先验证Thread所有权，再读配置，然后执行Mode、路径、realpath/no-symlink与文件操作。这样缺失Thread仍为404，而配置不可用安全返回503，且不会先访问共享FS。

Reflections用户自定义分区配置由registered83的`reflections-section-config.get/save/delete`提供，三项操作只接受current request OAuth。公开GET在Dream把Admin返回的partial prompt对象合并到静态default，并生成display与`usedCustomConfig`；PUT由Dream过滤五个允许文件名和空白内容后保存raw JSON；DELETE保持原`reset:true`回复。save/delete响应未知时只以同一OAuth查询原request ID和原operation receipt；committed且原output DTO有效才确认，absent、查询失败或坏回执继续返回outcome unknown，不重新POST。`memory-init`先调用Admin Chat确认Thread归属，再读自定义配置，最后执行既有路径检查和共享FS写入；任一身份、capability或配置错误都发生在FS之前。后台Reflections task没有已发布的可续期grant，仍保留旧配置reader和task/result数据库路径，不能据三项OAuth操作声明完整Reflections迁移完成。

资源`default`由Dream配置提供，`desired`仅Admin持久化，`effective/revision`由Dream独立provider/composition的LKG拥有。合法更高revision替换；同rev同值仅diagnostics，同rev异值/回滚invalid；unavailable保留LKG。四值为JSON/TS正安全整数，组合memory bytes精确，不能把技术边界包装成产品配额或用0关闭保护。turn主路径不加policy HTTP查询。

`global effort`来自policy LKG；compact/context/model max output来自最终选中的Admin模型，未配置不注入，用户/parent/workspace/env不可覆盖。`ai_models.max_output_tokens`只投影vendor-scoped CLI capability。`CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp`、真实thread/0700/no-symlink/关闭Workspace Mode行为与sandbox精确路径全部保留。

## 验收、发布与回滚

关联协调的[测试前完整影响表](/Users/dmeck/project/ink-dream-memory/docs/stage/stage_admin-auth-data-business-validation.md)，本任务为每入口补实际DTO/接口/repository/测试mapping，不复制冲突方案。Luna仅确定性技术验证；真实业务使用正常本机Dream/Admin/Gateway/PG与已授权现有账户数据，按正常model catalog限次，留下正常Admin可见Run/结算。凭据由协调保管，不复制至消息/文档/日志。

运行新Admin migration/backfill/破坏性测试仍只允许具名隔离DB并核验身份；数据授权不解除此边界。发布顺序expand → Dream兼容 → backfill/validate → contract， capability只代表实际已实现操作和Drizzle收据，不代替ACL/Schema物理迁移回执。回滚保留前向DDL/receipt，不复活已撤销旧token。全域覆盖、同源WS/REST/SSE、认证设备refresh、长turn委托与数据恢复未闭合时保持goal active。

## 首批生产资源接入事实

`agent_factory`、`resource_policy.load` 和 `resource_postgres_sink._write_sync` 已改为Admin HTTP依赖，两个领域方法移除直接SQL。Admin提供真实双向contract SHA256：read `1559c28cd5fbfbbf1b01a35fe6853ba5ccec2f26f45a428ac26ce22d005b3c78`，publish `409dfce5218c0471d9612016305698bba7388eb8d37c34be40b50b10488c1114`，版本均1；运行时须匹配capabilities广告，候选hash不是发布证明。正常读取返回严格状态DTO；非法desired保留LKG，网络/权限/capability/响应漂移不会应用配置。后台observer unknown写仅原request_id receipt恢复，未找到回执不重发、不越过旧写。Agent admission/revision/lease/SSE和共享FS合同不变。其他领域和认证切换仍未闭合。

### 资源 HTTP owner 当前生命周期

背景与问题：refresher/sink取消后，已经dispatch的同步HTTP可能仍在完成；关闭transport不能与该请求并发。目标与边界：只关闭resource composition拥有的独立client，不改变LKG、revision、resource算法、queue或Agent lease，shared request-auth owner仍有自己的生命周期。

概念与规则：AdminResourceData的read_policy/publish_observer/close共用原writer活动锁，整个capabilities/operation/receipt I/O在锁内。close等待已进入的操作，设closed后关闭client，重复close幂等；关闭后读写在创建client或HTTP前返回safe配置错误，provider按原unavailable规则保留fallback/LKG，不传播turn。未知observer write的原UUID记录保留，关闭不查receipt、不重发。

server先按原顺序stop publisher/refresher/sink/sampler，再Factory.aclose，随后asyncio.to_thread(resource_data.close)，最后Redis、数据库和shared request-auth关闭。各owner异常继续原安全日志与后续释放；即使sink已有detached同步调用，活动锁也等待其完成。测试用actual adapter/MockTransport/Event/明确命名ownedthreads覆盖active read/write drain、closed/no reopen/idempotence和provider fallback；shutdown测试仅编译原production注册函数并注入owner，避免full server的其它Runtime/DB初始化，不复制关闭实现。全域startup与正常业务验收仍开放。

## Runtime 环境阶段事实

新增Admin/Auth服务器秘密由SDK最终merge空值tombstone和内部/外部stdio MCP显式env过滤保护，server os.environ原值保持，二次merge不能复活。确切键/执行模块/正常失败流程见 [SDK环境设计](../design/claude-agent/claude-sdk-env-design.md#8-adminauth-服务器秘密与子进程边界)。现有Gateway helper仍需Admin长期委托/领域DTO替换；Editor stdio的`DATABASE_URL`与actor投影已删除，但这项收口不是完整无PG/无全局凭据验收。

### Browser session 异步状态

唯一browserSession owner保存immutable public snapshot，CSRF仅由该snapshot导出。read开始使用对象identity，每个fetch/body await与失败检查当前identity/AbortSignal；旧成功、401、parse错误或transport错误返回null且不修改当前owner。clear/logout开始失效旧read，logout失败仍保留snapshot，strict成功clear也失效期间read。AuthContext异步commit额外检查snapshot identity，旧null不能覆盖新session。deferred HTTP/body技术测试不启真实Browser/server/模型，保持同源Cookie/CSRF和Apps显式headers合同。

## Thread/message 消费端阶段事实

14个Admin实际输入输出/hash已写入严格Chat DTO与typed consumer，actor token与原request_id显式提供。微秒ISO字符串校验后原样保持，canonical用户ID不按BA sub猜测。原Python最终正文校验已抽为 `backend/chat_message_projection.py`，database旧私有alias和新Message DTO调用同一函数；生成器未复制其规则。消息回复ID还必须匹配原显式message_id，否则写结果保持unknown并用原receipt恢复。

Chat router的create/get/list/search/delete、bind Deck/select Voice与message list/page/process-detail/latest、初始user-message预留、公开turn assistant回写和用户SystemConfig snapshot已接typed consumer；现有搜索器、公开parts投影和微秒/NULL游标保持。共享请求身份与me profile已接入Admin。内部dispatcher persist/title/session、Deck context及其缺失SystemConfig owner等剩余直接DB入口未闭合；现有DTO数量不代表全域迁移完成。

## 当前用户资料与请求 actor 的接入状态

Admin `user-profile.current` 的闭集输入为空，输出仅当前调用主体的profile；Dream [typed consumer](../../backend/services/admin_data/profile_data.py)保留既有公开字段和微秒ISO字符串。canonical ID来自principal，与profile ID逐项比对，OAuth subject不转换为用户ID。profile不可通过runtime grant读取，不暴露token或密码字段。

[请求认证owner](../../backend/services/admin_data/request_auth.py)验证JWT scope，再向Admin读取active principal，要求subject/client/scopes一致，生成不可变server-owned actor。生产async依赖在线程池执行HTTP I/O，并在请求state显式保存actor；共享`get_current_user`与storage/workspace复用同一依赖，没有cookie/query token或旧JWT renewal fallback。composition root在已有业务owners关闭后释放自有client/verifier。token非法401、scope不足403、Admin配置/网络/DTO失败503；profile ID不一致按无效上游响应处理，禁止回查Dream PG。旧签发入口和long-turn/tool接入仍待完成，不代表认证产品全链路迁移完成。

## BFF API 请求规则

Next运行时auth与API Route Handler接入同一私有BFF owner，旧generic API/auth/OAuth rewrites已移除。Browser handle cookie存在时只解析该handle，非法、重复或空cookie直接401，不采用附带Bearer；所有Browser写须exact Origin与handle-bound CSRF。无handle cookie的Device/native请求只接受显式OAuth Bearer，Python验证Admin签名/scope/principal；Origin存在时仍须exact match。请求Cookie、服务/actor覆盖头、代理身份头及响应cookie/renewal credential不转发；URL token/access_token拒绝400。共享HTTP transport复用原Claude代理body/abort/SSE flush，不新增parser/EventBus。Browser state与显式MCP Apps已接同一session/CSRF owner；候选源码与技术构建并非正常部署或真实业务证明。

## Browser 与构建阶段事实

AuthContext现从同源BFF session读取strict公开user与内存CSRF；登录注册单一入口进入Admin同页email/signup/Google UI，device entry转Admin device UI。37个Browser API/hook/Chat/XHR模块与明确Node Apps adapter采用该owner，文件URL回到当前origin且去除旧token。静态旧getter/storage读取/Bearer写/options.token均0，full frontend typecheck与production Next build已通过。仍需受影响业务journey与真实模型验收；旧Dream authority已退役，其余数据域/后台grant仍未闭合。Chat initial user reserve采用下方原子user-turn命令与server-persistence委托，沿用原identity与409/unknown回执，不使用短OAuth token承担后台persist。

### Runtime purpose consumer 的当前边界

Admin以`auth.delegations`单独返回create/renew/revoke/原request_id receipt的method、path、版本与实际双向DTO hash；只在三项identity以及0033 `dream.schema.unified.v1` 全部published且匹配时广告。Dream server create同时检查这四项schema与四descriptor，调用独立create入口，不通过generic operation模拟。ID沿用非空text业务字段，不增加任意长度产品限制。

共有HTTP函数接收显式URL/header/DTO和timeout/响应大小，不持有身份配置。Internal consumer注入service身份与必要用户Bearer；public Runtime consumer只持exact idg，prepared request不继承httpx client的Cookie、auth或默认key headers。响应校验原request_id、闭集DTO和purpose/thread/run/EditorSession/scopes；renew不能改变maximum或降低expiry。

Server keeper在expiry前运行后台renew。响应丢失保留原ID，后续先查原receipt；absent继续保持pending，不新建动作。恢复原committed结果后仍以有效expiry判断是否可用，maximum不延长；到期或purpose不匹配时授权边界拒绝。后台异常只写安全diagnostics，不传播到Agent turn。server-persistence keeper与Editor stdio purpose已接公开Agent生命周期；confirmation dispatcher 通过 Registry121 接入同一 owner，CLI最小投影和其他后台路径仍逐项迁移。

### Confirmation Runtime 的 claim-bound Admin owner

执行模块 `AdminStoryWorkspaceConfirmationWorkerData.claim_turn` 只发送 nullable `message_id` 和服务器生成的 `claim_id`。Admin 在一个 transaction 内锁定 Registry120 confirmation message，执行原 pending/expired-claim 状态转换，并从该行派生 actor、Thread、Workflow Run 与 active subject。`DelegationService` 创建或恢复 scope 固定为 `dream:read/write`、purpose 固定为 `server-persistence` 的 grant；Dream 不能提交这些身份或权限字段。Registry121 operation SHA 为 `c971b5f2ee3517eb9c078d70544bfaa46d74a293afc44b1b8386496d9d081e62`，完整 registry SHA 为 `969d316b62c1c77aa5f232030d882fd48b36f01b0728cd4f86b877caa99909af`，并要求 `identity.runtime-confirmation-claim.v1` capability SHA `d9de67655e6d8d5ae9654d6502a2cf5d9ab1bb6d829975b243eb25e239b08919`。

Dream 校验 dispatch 与 authority 同时存在、Thread/Run/scope/purpose 精确匹配，然后用现有 `workflow-context.resolve`、`deck-chat-context.resolve` 生成 immutable snapshots并构造 `AdminTurnPersistence`。dispatcher 在 drain 前启动 owner，把三项对象注入 `ClaudeAgentRunRequest`；turn 成功或失败均先关闭并 drain owner，只有 Runtime 成功才 ACK。Admin 每次 resolve/renew 都对 source message 取得 share lock并以数据库时钟验证相同 dispatching claim 和未过期 lease；ACK、替换或过期后下一项数据操作返回授权失败。capability、DTO、snapshot、HTTP 或授权失败均不创建无 owner 的 Runtime request，也不回退 Dream PostgreSQL。Runner、ThreadFactory、EventBus、SSE、resume/cancel、resource LKG、共享文件系统和 `.claude-tmp` 不变。

旧Dream password/Google/Device/token与Python local-cookie logout九条HTTP路径已改为明确410标准Admin authority迁移响应，不解析/转发敏感请求、不执行签发或相关DB动作。Standalone旧auth helpers已拒绝本地签发/密码/refresh权限，两个脚本改为显式Admin OAuth并核对正常生产profile账户；Authlib/bcrypt从manifest/lock/export原子移除，其余版本不变。Gateway subject helper、Agent purpose接线与其他数据库领域仍待迁移；MCP SDK外部OAuth协议保持。此项不等于正常本机登录/模型验收。

### 公开 Chat 的 Workflow 上下文

执行模块`AdminWorkflowData`只发送`workflow-context.resolve`的`{thread_id}`；Admin在同一事务校验唯一线性retry leaf、冻结binding、workspace owner和启动message来源/fingerprint/父状态，经过完整校验的terminal leaf或普通Chat返回`context:null`。Dream strict校验实际十字段、required nullable agent_id、原255边界、Run格式和正JSON-safe revision，operation hash为`f395682ec6cf8f308df652a1aa2792cca86d102eb1fff62a4c6a59792bfc1e66`，同时匹配identity/unified物理capabilities。

公开route在已有Deck/Voice绑定后、message预留与SSE前读取。409/权限/网络/capability/DTO失败直接返回安全错误，不写初始message、不启动runtime。成功时校验thread及当前Deck/Voice，并向内部RunRequest注入不可变`AdminWorkflowResolution`；公开DTO/SDK不含该字段。Service核对actor/thread，含ordinary null均直接复用，不调用旧PG mapper。snapshot不授予新增scope、长期runtime或CLI权限；confirmation 已通过 Registry121 独立派生并注入同类 immutable snapshot，launch 等其余内部路径继续迁移自己的 typed authority。验收聚焦真实HTTP consumer、null/十字段、错配、失败-before-SSE和既有Service行为，技术fixture不代表正常本机业务回执。

### 原子 user-turn 与 server-persistence 生命周期

`chat-user-message.persist`的input仅`thread_id/message_id/parts_json/metadata_json/title_candidate`；metadata required nullable，JSON保持Python float、负零、大整数表示，禁NaN/非JSON对象。Dream复用原`extract_text_from_parts`得到包含attachments协议的未截断candidate；Admin在单一事务执行ownedThread update lock、stored confirmation guard，保护当前dispatch lease/control metadata，非confirmation时写rawmessage并按原配置仅填missing title。output仅`message_id/confirmation_preserved`，actualhash `2c5b20900ef867a237613e49a89b4073f4c0c89cd1d2161962f7132084696c37`。

公开ingress在已验证Workflow上下文后以当前OAuth创建最小server-persistence idg：仅dream read/write、exactthread、authoritativeRun或普通null、无EditorSession。`AdminTurnPersistence`只在server保存该grant/typedclient；初始原子预留成功后Service复用同输入的已知result，不再拆三次DB调用或重发。unknown保留原UUID，后续只查原receipt；absent或读取失败继续阻止新写/推理，不能认为取消/超时表示rollback。reply message ID错配按unknown处理。confirmation 已使用上节 claim-bound 服务身份；launch 等其他内部路径仍保留原guard并单独迁移。

Factory在原admission acquire之后启动该owner的独立renewal和Chat Session broker，EventBus/Runner/lease/resume/cancel顺序保留。SSE disconnect只取消subscription，后台turn及grant继续；terminal/cancel注册自有Phase4 cleanup，broker先停止accept并drain已dispatch读取，随后等待同步writer、renewal线程并关闭独立Runtime client，application client仍由composition关闭。Keeper network action与current/diagnostics短锁分离；expiry/max/purpose/actor/thread边界拒绝，不扩大授权。server grant不进入CLI/Editor/user MCP或Browser；Editor使用另一个exact Session purpose且其idg仍只留主进程。Agent prompt和Chat Session工具都由owner读取Admin `session.list` strict projection。Gateway独立目的、内部dispatcher assistant、Reflections后台Session上下文和其他数据库领域仍需迁移。验收使用实际public route/Service/Factory与明确clock/MockTransport，覆盖unknown原ID、disconnect/cancel/drain、numeric/title和current不等待HTTP；未据此宣称正常本机模型验收。

### 公开 Agent Thread 恢复与 SDK Session 回写

执行模块`ClaudeAgentService._thread_record/_save_sdk_session`在公开request含server owner时复用`AdminTurnPersistence`，调用实际`chat-thread.get/update-session`；只有缺owner的现存内部dispatcher保留原PG入口。读取仅发送thread_id并核对reply Thread与canonical actor；更新只发送thread_id/claude_session_id/agent_contract_version，grant不进入Runtime options。恢复仍执行原当前project transcript与contract版本检查；只有SDK-native init触发early write，final/repair使用同一helper，不改变取消/SSE/lease顺序。

owner在单一activity锁中串行user/session/assistant命令及Thread读取，Phase4等待已dispatch的读写。未知写记录原operation/immutable input/request ID；不同操作或输入拒绝，已知user缓存也不能绕过pending。同操作同输入只能查原receipt，absent/读取失败继续unknown，committed恢复结果且不POST重试。Session是可变字段，只有最近一次确认的同输入更新可复用；A→B→A重新执行命令，user message identity冲突保持409。

初始user预留unknown仍在SSE/推理前拒绝。SDK init回写unknown保留原callback日志处理，已经运行的turn与cancel继续既有路径，随后owner管理的不同写被拒绝；公开assistant已进入该屏障，内部dispatcher assistant、Run与FS metadata数据库写仍不经过此owner，因此当前不是全域未知写屏障。验收通过actual Service/native SystemMessage/next-turn transcript/cancel和MockTransport/Thread DB fence，不代表正常本机数据库或模型验收。

### 公开 assistant 完整与部分消息持久化

背景与问题：公开Chat已经在RunRequest携带绑定当前actor、Thread与authoritative Run的`AdminTurnPersistence`，但成功assistant与cancel/error partial仍由Service直接调用旧`database.save_chat_message`。用户能够收到SSE终态而消息回写仍绕过Admin数据边界，且该写没有加入user/Session已建立的unknown提交屏障。

目标与边界：`ClaudeAgentService`继续按原SSE事件生成reasoning/tool/text parts、`turnStatus`、`finalPartIndex`、duration、usage、model、toolCount与Dream source metadata；公开request把同一值交给owner，owner调用既有`chat-message.persist`。完整消息带原`history_final_text/history_process_available/history_projection_version`，partial保持`null/false/null`。消息ID由Dream服务器生成，不能复用user message ID或SSE turn ID。内部dispatcher尚无authoritative owner，继续使用原SQL入口；本阶段不新增凭据、接口、数据库表、Runner状态或文件行为。

正常流程与状态：owner先取得当前renewed grant，重新读取catalog并逐项匹配identity、unified、history keyset与final projection四项schema，再提交required八字段DTO。Admin只接受`assistant`角色并返回同一message ID；确认后owner清除pending。成功assistant仍先提交再运行Dream Hook，SDK final safeguard仍在assistant确认后执行。cancel/error仅在收集到parts时写一条`is_partial=true`消息；无可持久化事件时保持原no-op。

失败反馈：actor或Thread与grant不匹配时在I/O前拒绝；schema缺失、重复或hash漂移返回503且不发消息POST。HTTP超时或回复ID/null/额外字段错误保留原operation、完整input与request ID，阻止后续不同user、Session或assistant写；只有相同输入查询原receipt，absent继续unknown，committed核对message ID后恢复，不重发。partial沿用原日志与吞错行为，完整assistant沿用`ClaudeAgentAssistantPersistenceError`并阻止后续Hook；这些规则不把取消解释为数据库回滚。

影响与验收：公开Service路径不得打开PG，parts/metadata/history构造、错误/取消、SDK顺序、admission/lease/Factory/Runner/EventBus/SSE、共享FS与`.claude-tmp`协议保持。provider-free验收覆盖完整/partial三种终态、四schema故障、reply错配、unknown跨操作阻断与原receipt恢复；normal本机账户、PG、模型、Runtime和Admin可见业务记录仍需独立验收。

### 公开 Session 与 Editor 状态边界

Admin `session.save/get/batch/list/text-list/delete`六operation负责owned Session持久化、state/writingThread绑定、name/labels null保留、UTC范围与排序。Dream复用闭集EditorEngine state DTO，覆盖text/widget/suggestion Cells、commentors/tasks/weight；optional在wire省略，只有selectedState可显式null，required nullable字段保留。有限JSON数值与微秒ISO按实际合同校验；错误state/ID/额外字段在I/O前返回安全400，Admin状态损坏返回503，missing get保持404。

公开Session走同一已认证request actor/OAuth与shared threadpool/error adapter，无外部user ID。metadata list移除内部text:null，Dream保留时区date_key、mixed-word metrics与aggregate响应；空batch不发domain request。update/delete收到confirmed result才publish原user-scoped Edit Session event；unknown保留原request ID，不retry、不发event，业务状态按原receipt确认。公开OAuth行为不变；同一`session.list`为Agent recent prompt和Chat Session工具接受已经由配置service完整解析、绑定Thread、Editor Session为空、包含`dream:read`且未过期的`server-persistence` grant。其他五项Session operation仍拒绝该purpose。Reflections后台读取没有冻结的task snapshot provider，继续保持独立授权缺口。公开HTTP/DTO/DB-fenced技术验收不代表正常账户业务验收。

#### Agent最近Session prompt上下文

`AdminTurnPersistence.recent_sessions`在既有activity锁内验证immutable Workflow actor/Thread，读取current renewed grant，并在POST前匹配`session.list` SHA `1936970e27a8b854dd08cd785b0da6534656aa5af0e652750693f86e88860435`与Better Auth/runtime delegation/runtime purpose三项identity schema。输入固定为UTC当天及前两天、`include_text=false`；输出只接受strict `SessionPreviewDTO`且禁止返回正文。读取参与Phase4 close drain，不进入或清除user/SDK Session/assistant unknown写屏障。

Service只在首次system prompt或Settings `SYSTEM_PROMPT`变化触发重建时调用一次，保持Admin的`updated_at DESC`顺序；ContextBuilder按`INK_AGENT_CONTEXT_SESSIONS`截断并只渲染投影。空投影或渲染错误保留原empty文本。Admin不可用、grant/capability漂移或坏DTO在Workspace/Runner/CLI前终止，并由既有安全错误边界返回；不回退Dream PostgreSQL。keepalive且Settings prompt未变不发Session请求。Agent Runtime、SSE、resource LKG、admission/lease、resume/cancel、shared FS与TMPDIR规则不变。

#### Chat Session Tool私有broker

`AdminTurnPersistence`构造时绑定不可变actor/Thread provider，并使用现有Admin HTTP timeout和max-response-bytes创建`SessionProjectionBroker`。Factory在keeper ready后、Runtime前启动`127.0.0.1`临时端口和256-bit URL-safe capability。request strict DTO只含capability、request ID、ISO日期和`include_text`；额外actor、Thread、task、SQL或credential字段在provider I/O前拒绝。provider在owner activity lock内读取current renewed grant、匹配`session.list`和三identity schema，并返回现有`SessionListResultDTO`；`include_text=false`在host和child双重拒绝正文。

Service将五个broker字段加入server-owned `mcp_env`。Runner给user stdio只保留这五项与两个既有retrieval policy，为三项Claude credential和全部Admin/BFF server-only secret写空tombstone；isolated Python bootstrap在package import前清空继承环境，stdio入口再次只保留该allowlist，因此DB URL、actor/Thread/task ID与用户custom env同样不可见。`sessions_tool.py`仅调用neutral strict client，然后执行原date/fuzzy/labels/limit/Unicode/vector/auto逻辑；broker/Admin/DTO/timeout/size失败返回稳定`session_projection_unavailable`，不import或调用Dream DB，也不披露endpoint、capability、token、正文或异常。Reflections task snapshot provider尚未冻结，本阶段不借用Chat grant。

#### 公开 Agent Editor runtime

背景与问题：Editor MCP子进程原先获得`DATABASE_URL`与actor ID并直接读写Session，形成独立认证和数据路径。现行公开Agent turn由主进程OAuth actor创建`editor-stdio` grant，固定当前Thread、exact Editor Session、`run_id=null`及`editor:read/editor:write`，并在创建前匹配`editor-state.load` SHA `1555a622d0030dc2242ee86825fd949f4ea8b0fbe77e28528b19c72804c40335`与`editor-state.replace` SHA `bb37ffff488c49a6e8b69f58a16eb1a4eb454f1d6f014a1b91832c001811a4f6`。

正常流程：Factory仍在admission之后启动active Editor owner。stdio仅得到loopback host/port、每turn随机capability、timeout和最大字节数；不含OAuth、service secret、idg、actor、Admin origin或DB值。每个mutation由子进程请求broker，主进程以exact grant调用public load，应用原mutation后调用replace；成功state进入runtime cache，Service tool-result回调刷新`AgentRunState`并发布既有Session event。`switch_editor`为目标Session创建独立grant并先完成load，成功才由PostToolUse采用缓存。新grant使用请求进入时由主进程保存的OAuth；长turn中该token过期会使未授权Session切换失败并保留原state，现有Admin合同没有旧Editor grant派生或请求OAuth刷新操作，Dream不以service身份、actor参数或PG连接补权限。

状态与失败：replace可能已发送但回复未知时，runtime保留完整input和原request ID，只查询public Editor receipt；absent或查询失败保持unknown且不重发，不同input被阻止，committed核对operation/request/Session后恢复。grant创建、输入或broker检查在POST前失败不进入unknown。Admin missing/permission/stored-state/DTO失败保留原flyweight，不查询Dream PG或写fallback。terminal/cancel在Phase4关闭broker、所有keeper和public clients；SSE disconnect不提前关闭。

影响与验收：Editor确认UI、mutation算法、`.editor/`读、Session event、admission/lease/Runner/EventBus/SSE/resume/cancel、resource LKG、Runtime配置、workspace/TMPDIR均保持。provider-free技术测试覆盖exact hash/grant、prepared bearer headers、switch/cache、unknown receipt/no resend、malformed input和lifecycle；未进行正常本机账户/PG/模型时不报告正常业务验收。现行细节见[Editor MCP](../design/claude-agent/edit-point/mcp-tools.md)与[EditorState生命周期](../design/claude-agent/edit-point/editor-state-lifecycle.md)。

### 公开 Deck 内容版本边界

`AdminDeckVersionData`消费state/preview/commit/history/detail五operation；当前request OAuth独立于Runtime purposes，Admin拒绝Thread grant作为Deck管理授权。Dream在domain调用前匹配identity/unified/content-versions/canonical-storage四项exact v1与operation hash，缺失/重复/错误version或hash时503；Admin继续逐事务验证物理ledger、principal/owner、CAS与输入。共享actor/threadpool adapter复用原权限规则，domain只定制安全JSON错误。

Admin负责snapshot/hash/diff、Deck锁、immutable append及latest/published revision同事务更新。Dream闭集校验v1 snapshot raw字符串，最终标准Python decode成原flat detail的snapshot dict；float/负零/bigint、required nullable、created_by公开int与微秒时间保持，不重算或改写canonical JSON。reply外层/nested Deck或selected version不匹配读503，commit按unknown处理。

commit的positive safe CAS与原description/limit合同保持。409 conflict只携带已校验current_draft_revision/current_version及固定安全message；已确认事务失败保留草稿/旧vN，网络/响应结果不明保留原UUID/outcome_unknown、不自动POST重试，absent不能证明rollback。catalog fresh fetch失败清除ready，下次共享身份重新加载，避免其他领域沿用空广告。公开五operation技术验收无Dream PG；其他Deck/Voice14、refs/voice6的actualFS/CLI证据、Runtime和内部content-version消费者继续开放，正常业务验收独立。

### 公开用户偏好边界

`AdminPreferencesData`消费user-preferences.get/save两个actualoperation，current OAuth、identity/unified exact schema与closed input由同一transport/actor adapter校验；Admin用户级Service拒绝全部idg管理授权。POST只允许五optional公共字段，转voice_configs_json/meta_prompt/state_config_json/selected_state/timezone五requirednullable wire；rawJSON用Python生成，不经JS重编码。null执行原COALESCE保留，{}与空字符串仍保存；不接受外部actor/firstlogin/systemconfig写。偏好route handler将typed请求校验失败转固定422，不回显正文/input，避免非finite输入在框架错误响应编码时失败。

GET null row仍{}；rawconfig还原原voice_configs/state_config对象，firstlogin整数/null只读，ISO offset/微秒保持。raw对象NaN/Infinity无法输出公共标准JSON时safe503/noheal。confirmed true返回原success；timeout/invalidwrite结果保留原UUID/outcome_unknown/no retry，不能由absent声明rollback。default-voices仍Dream config，System/Runtime策略/firstlogin/import/后台context仍独立；具体default/desired/effective/revision与状态见[现行稿](../design/user-preferences-current.md)，旧时序原文另存。actual公开DTO/DBfenced MockTransport是技术验收，与正常真实账户/模型验收分开。

### 公开Deck Claude Plugin refs

list/prepare/replace经当前OAuth与exactidentity/unified，拒绝全部entitygrant管理。prepared闭集installation无path，selectedIDs exact/unique/ready后由Dream原staticmethod验证制品摘要与CLI SemVer；body不接受package/digest/compat/actor。Admin按source evidence锁与重检当前ready/package/version/digest/rawcompat，在单TX refs/semanticdraft/receipt/audit，no-op/reorder不推进。Dream只校验replyDeck/IDs与原enabled0/1/ISO投影，unknown保留原UUID/no retry。共同scoped validation复用原偏好wrapper，固定422不回显正文；global install/catalog/runtime/Voice仍在清单开放。完整规则见[现行refs稿](../design/deck/deck-claude-plugin-refs-current.md)。

公开GET /api/decks/{deck_id}消费deck.detail/current OAuth，four exact schemas/hash，outer与每个Voice deck_id必须匹配。原null404/owner int/时间/Memory值保持；无read retry或DB fallback。实际Admin producer目前将empty Memory归null，与原Dream保留emptytext不同，仍需修正且不计该值真实验收完成。详见[Deck详情现行规则](../design/deck/deck-detail-version-history.md)。

### 尚未发布的Run创建/重试与隐藏来源

Admin prospective workflow-run.create/retry当前不在70 registry，发布冻结期间不能调用。create来源三字段要求全null或完整aware tuple；retry沿用原Run来源，不能替换。两输出保持完整WorkflowRun；源码/ingress PASS属于Admin报告，不能替代注册或公开业务验收。

隐藏来源必须沿用原执行顺序：Dream Application由verified actor/workspace/key canonical JSON确定UUIDv5 Thread/message；Admin未来领域事务在PF/Run前ensure_source，初始metadata不含workflowRunId。Run确认后原dispatch阶段的claim保存workflowRunId与dispatching，再调用turn dispatcher。持久化移Admin不改变该顺序、claim/lease/重入/失败或Runtime编排；实际source/dispatch capability未发布，消费端接线继续pending。

GET /api/decks的published false/true两mode均消费deck.list/current OAuth/dream:read与four exact schema/hash。Admin处理过滤/计数/排序/policy；user保留total_voice_count并省略author_display_name，community保留author_display_name并省略total_voice_count。无默认初始化/文件检查/DB fallback/read retry。详见[现行规则](../design/deck/deck-detail-version-history.md)。
