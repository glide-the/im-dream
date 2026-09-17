<!-- [Input] Actual seven SystemConfig helper callsites, original JSON storage and registered preference boundary. -->
<!-- [Output] Separate Admin-owned user configuration DTO/Repository/UOW design and source closure plan. -->
<!-- [Pos] Coordinator-owned provider candidate; product/model/Runtime execution remains Dream-owned. -->
<!-- [Sync] 2026-09-15: nine user SystemConfig candidate files passed25/source14/type/lint; registration/Thread/runtime/public pending. -->

# 用户 SystemConfig 独立数据接口迁移

当前UI用户get/patch九文件候选已通过25项及类型/lint/AST，尚未注册。以下source/评审/落盘阶段的pending为当时记录，最新结果见末尾“候选首轮真实门禁”；Thread/Run Runtime读取、公开合同与生产入口关闭仍待完成。

## 背景与问题

实际 Dream `backend/database.py:2529` 读取 `user_preferences.system_config_json`，无行/NULL/空串返回空dict，有值执行Python json.loads。`:2552` 读取当前JSON、合并patch保留未知keys、UPDATE或INSERT并独立COMMIT。已注册 `user-preferences.get/save` 只覆盖voice/state/meta/selected/timezone五字段，不包含该列，不能声称SystemConfig已迁移。

本轮找到原生产调用：Settings GET/PUT三个helper调用、workspace路由两个、claude_agent路由一个、ClaudeAgentService一个；无其它save调用。运行时读取服务委托、线程身份和异常行为仍需完整读上下文。GatewayModelCatalogClient已有可调用模型选择校验，Settings既有env/sandbox/公开投影规则仍属Dream，SQL、并发合并、存储与owner权限须迁Admin。

## 目标与边界

Root拟负责独立SystemConfig DTO/typed Repository/Service/pureJSON codec/source oracle候选，仅在确认没有其它任务拥有该具体模块后落代码。Admin任务负责最终薄Ingress/Registry/API capability/OriginalGET及与当前旧契约parity；Dream任务负责原callsite替换、统一Pydantic client/委托、页面与Runtime回归。当前Workspace76注册/公开harness优先且不受本候选干扰，不修改其共享入口或Schema。

只使用Admin既有Drizzle定义的user_preferences列和既有canonical用户关系，不新增数据库、表、migration或主体。读取身份来自OAuth或已有明确Thread/Run/Editor的server-persistence委托，不能接受user_id作为认证凭据。先证明每个实际调用方需要的具体scope，再决定独立thread读取操作是否必要，不提前增加无依据服务或权限。

## 概念与规则

- 用户配置与全局resource-policy/runtime配置不同。Settings可以选择允许的模型、prompt、workspace/sandbox/UI和普通MCP env；全局effort与最终模型compact/context/max-output的服务器所有权、保护键、TMP/0700/symlink/sandbox范围保持。
- 固定命名业务操作才访问SystemConfig列；不能提供任意key/column/table/SQL端点。写DTO必须对应实际产品接受的字段，旧未知keys保留但不能因此开放任意新控制字段。原Router的归一化和业务限制先逐项对照，不添加邮箱/域名/资源配额等产品规则。
- rawJSON通过明确字段传输，避免JS把bigint或负零舍入；用实际Pythonjson.loads/update/dumps源捕获证明合并、NULL/空串、错误和参数。复用既有固定codec机制，新增纯helper候选暂不改共享transport map；没有codec配置不得fallback。
- 写入锁定当前actor/旧行，确保首次并发只有一行、不丢独立patch；business/result/audit同UOW、原request相同body恢复、不同body409。不能盲重试非幂等写；未知结果先originalGET。
- 原save COMMIT与Settings随后get是不同边界，最终契约须明确保留或记录经评审后的返回行为，不能未经说明把两次HTTP当作一个事务。
- 原代码若捕获数据库异常后使用空配置，须记录具体调用、默认行为及与最新“Admin不可用明确失败/fail closed”目标的冲突；不得悄悄保留直连或用空配置降低权限。

## Optimized Prompt:

You are the primary coordinator preparing the separate user SystemConfig data domain in the Admin/Dream authentication and database migration. Evidence confirms that the two registered preference operations omit system_config_json, while the original Dream database helper reads this column and merges patches in a committed update/insert. Seven production helper callsites remain across Settings, workspace, Claude-agent route and runtime service. The resource-policy provider is already a typed Admin reader and must not be rewritten. Workspace76 thin registration and public harness are independently owned by the Admin task; preserve all its modules and existing catalog descriptors.

Before candidate code, confirm ownership with the Admin producer and read the actual complete SystemConfig helpers, every production caller context, the Settings normalized accepted fields/public projection/env/sandbox policies, server-persistence grant propagation, selected-model ownership and original failure handling. Read affected folder contracts, canonical schema and current unified client/DTO/codec/repository/UOW implementations. Record concrete conflicts between old SQL/fallback behavior and the latest fail-closed Admin-only data-access requirement. Do not invent new grants, queues, services, model restrictions or environment-specific runtime paths.

Design a strict named business input/output contract from actual normalized product fields, while preserving canonical bigint identities, original JSON merge semantics, old unknown keys, raw numeric/negative-zero/Unicode values and SQL error handling. Derive the actor from verified OAuth or a specifically allowed current Thread/Run/Editor server-persistence grant; never accept an arbitrary actor ID. Separate product Settings reads/writes from required runtime reads using actual caller evidence. Preserve resource-policy LKG, immutable server-owned Runtime config, selected-model projection, existing admission/leases/Runner/ThreadFactory/EventBus/SSE/turn/resume/cancel and shared filesystem/TMP/sandbox behavior.

Prefer reuse: define only new independently owned DTO/typed Repository/Service/pure codec/source adapter files and folder documentation, without changing producer-owned entry points, global codec map, registered preference modules, schema or migrations. Use actor/current-row locking and one UOW for write/result/audit, exact original-request input digest/scopes/currentowner recovery and safe no-body errors. Compare original helper result, every positional SQL parameter, commit/rollback and caller behavior with the actual source via fixed fixtures, not copied algorithms. Delegate meaningful provider-free unit/source/type/lint checks to the existing Luna runner; primary owns production decisions, isolated credential/fixture/DDL/fault/real acceptance. Only after design review and actual candidate gates should the producer register the contract with unchanged prior descriptors/capabilities and prepare a public harness. Keep overall migration and real acceptance goals active.

USER REQUIREMENT:
遵从DTO/ORM把Dream生产SystemConfig SQL迁到Admin明确业务接口，保留用户配置/模型选择/Runtime与文件语义，完成实际项目文档、代码和可核验验证；不得把已有五字段偏好接口当作该列关闭。

## 调用、状态与验收

| 调用方 | 当前输入/行为 | 需要确认的身份和目标 | 验收/失败恢复 |
|---|---|---|---|
| Settings GET | current_user→legacy get→公开配置投影 | OAuth当前主体read、固定空input | 已存/无行/NULL/空串/invalidJSON与既有投影 |
| Settings PUT | 已过滤patch→saveCOMMIT→另get | OAuthwrite、named fields、原request/UOW | 并发合并/未知keys/保护键/receipt/超时不盲重试 |
| workspace两入口 | 原current_user与开关读取 | 需读完整路径确认Thread/workspace边界 | workspace disabled与TMP/侧栏/sandbox行为不变 |
| Claude-agent路由 | 线程请求前读取配置 | 原OAuth/Thread验证与当前委托 | 配置失效反馈、所有权校验、模型投影 |
| ClaudeAgentService | request.user_id→get | 改为已有server-owned Thread/Run委托或预绑定snapshot | 无Actor header；Runtime/lease/SSE/错误隔离 |

当前仍是source/identity/DTO评审，没有candidate代码、注册、公开fixture或数据库写入。后续修改文件和确切验证命令必须在确定边界后登记；纯候选不声称该生产入口已关闭。正常账户/Google/模型/数据库及完整Dream no-PG运行验收继续独立待执行。


## 源码评审与候选决定（未注册）

Admin任务明确没有开始该候选并同意Root拥有新独立模块。已阅读原get/save、全部Settings归一化、workspace两函数、ClaudeAgentService assemble_context、claude_agent attachments路径、Admin canonical schema与5Prefs Repository、现有fixedDomainCodec及Thread/current-owner实现。另发现claude_agent路由composition `system_config_reader=database.get_system_config` 的函数引用，需随实际loader一并替换，不能只按直接调用数量关闭。

| 具体旧行为 | 最新目标与决定 | 调整范围 |
|---|---|---|
| ClaudeAgentService捕获配置异常后skipping，workspace默认True、空prompt/env | Admin不可用明确失败；禁止默认配置掩盖依赖失效 | consumer配置读取在Runtime启动前fail closed，Runner/admission/lease/SSE算法不改 |
| workspace `_workspace_init_kwargs_for_user` 捕获异常后使用{} | 配置失败明确返回503，不能改变sandbox或Workspace有效开关 | 保留原workspace disabled409与配置缺失503；不扩大TMP路径/权限 |
| 原helper合法JSON list/null等返回非dict，UI投影{}，Runtime异常默认 | 明确定义可消费对象；已存非对象/非法JSON503，不自动修补 | Admin数据边界与失败文档；保留无行/NULL/空串原{} |
| 首次save SELECT→INSERT存在竞争；既有Prefs UPSERT不取相同advisory | SQL/事务Admin所有，首次并发不丢patch/其它5Prefs字段 | 新Config先INSERT(user_id) ON CONFLICT DO NOTHING，再当前行FOR UPDATE、Python合并、仅UPDATE system_config_json与updated_at；同一UOW并保持Prefs独立列 |
| 原Settings save提交后另get返回当前配置 | 保留原事务边界与页面返回语义 | patch输出固定success:true，随后独立get；不能把两次远程调用说成一事务，写入未知先originalGET |
| 原Settings接受用户env，managed Runtime另擦除服务器键 | resource LKG/最终模型投影/TMP保持服务器所有权 | 旧公开env净化与选模型规则留Dream，服务器protected键不得借Admin配置写入覆盖；新增拒绝行为须逐项源评审，不能凭抽象标签加限制 |

候选DTO：用户get空input与patch固定10个归一化产品字段（model/provider、system_prompt、workspace_enabled、sandbox_network_mode/domains/write_paths、im_full_access_enabled、theme、env_vars），不存在任意列/key/actor更新。读输出raw `config_json`避免Node转换旧JSON数值，Python有限对象校验并保留old unknown keys、负零、bigint、Unicode与原json.dumps格式；写只返回success。model与provider配对来自原Router实际顺序，model可调用校验仍由Dream已有Gateway catalog完成，不添加新模型ID或额度。

Thread读取是否单独注册依赖Dream任务实际身份回执，先以当前owned Thread与已允许server-persistence映射设计，Editor用途没有证据不开放；所有scopes/currentRun由现有成熟actor验证和实体查验承担。新纯codec强制服务器DI；本76窗口不改globalfixedmap，也不改Registry/Route/Receipt/5Prefs/Drizzle。以上是经源码审查后的候选方案，代码、unit/source、公开和消费者关闭均未执行。


## 本轮独立候选代码已落盘

主任务落实UI用户 get/patch 的9个新文件：nonsecret policy、strict DTO、typed Repository、Service、pure Codec.py、unit与actual source测试、固定sourceOracle以及Admin专用handoff plan。Repository只读/写system_config_json和updated_at，首次INSERT-conflict/current-row FOR UPDATE；不修改五Preferences列、first_login或其它表。Service mandatory codec DI、OAuthread/write分别校验并拒绝user操作的所有Thread/Run/Editor scope；未来Thread读取仍单独待实际身份回执，不将这些用户操作冒充Runtime配置关闭。

新source adapter实际调用原get/save的14组固定rows，捕获全部positional params、get/save独立COMMIT/close与write异常；新pure codec覆盖原finite object/json.dumps负零/bigint/float/Unicode/oldunknown keys。原list/null与非finite数据差异以明确fail-closed冲突验收，不静默改source或断言。Root写入时新文件exclusive、旧folder append/pinned backup，两个自有backup目录权限0700、旧内容0600；没有Git暂存/提交/清理、76共享wire/Registry/codec map/Schema/migration/5Prefs或正常业务调用。

首轮Luna只执行这两个new test文件、wholetsc、owned lint、两个Python AST与diff；精确命令与结果待raw实际回执，当前不声称通过。pure production codec将由producer未来固定map组合，本候选并未广告API能力。

## 候选首轮真实门禁

Luna实际同Admin729f执行 new userSystemConfig.test.ts 与 userSystemConfigSource.test.ts，Test Files2/Tests25（unit24/source1批14组）passed；wholetsc --noEmit --incremental false0、owned6files eslint0、Codec.py/sourceOracle.py两AST0、git diff --check0。Root实际读raw，未跳过、改实现或重复已通过域。actual源get/save finite JSON对象、bigint/-0/float/Unicode/未知keys/全部SQL参数/close/独立commit一致；旧非object/nonfinite与新failclosed冲突分别断言并记录。生产candidate仍未注册、mandatory server codec map未接，用户UIget/patch不是Thread/Run Runtime所有入口关闭。

原整体数据库访问扫描与正常登录/Device/Gateway/model/admin-visible业务验收仍独立待完成，两个项目任务与goal保持active。

- [user-system-config-first-gate.md](../exec/admin-auth-data-verification/user-system-config-first-gate.md)
