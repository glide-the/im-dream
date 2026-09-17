<!-- [Sync] 2026-09-15: three public default resolvers share registered Admin ensure; Deck Plugin role reuses current profile. -->
<!-- [Sync] 2026-09-15: consume registered76 OAuth-write default Workspace; original text ID/receipt and independent read scope stay explicit. -->
<!-- [Input] Published Admin Preflight read/execute/receipt DTOs and original Dream model semantics. -->
<!-- [Output] Current ownership, state, failure and acceptance rules for reads and staged execution. -->
<!-- [Pos] Current consumer design; original stage/Run rules remain separately applicable. -->
<!-- [Sync] 2026-09-15: migrate only the owner-scoped GET without default Workspace or SQL. -->
<!-- [Sync] 2026-09-15: consume the execute domain and original three-state receipt; default lookup remains pending. -->
<!-- [Sync] 2026-09-15: link the subsequent full Run domain consumer while retaining workflow dependencies. -->
<!-- [Sync] 2026-09-16: remove the duplicate Dream SQL Preflight service and builder after all production callers adopted Admin DTOs. -->

# Preflight 读取与领域执行现行设计

> 当前公开 Preflight 与 Dream Launch 均通过严格 DTO 调用 Admin `workflow-preflight.execute/read`。Dream 中重复的 `PreflightService` 与 `StoryWorkspacePreflightServiceBuilder` PostgreSQL 实现已经删除；历史 task 与 exec 文档继续保留原实施记录。

## 背景与问题

原 GET 通过 Dream application service 查询 PostgreSQL，路由还先初始化 default Workspace；实际 read_preflight 只使用 Preflight ID 和 actor ID。Admin 已发布 owner-scoped workflow-preflight.read，并承担记录读取、当前 Deck 所有权校验及 token 签发。公开读取可独立迁移。

## 目标与边界

GET `/api/story-workspace/workflow-preflights/{preflight_id}` 使用统一 Admin OAuth 身份，返回原完整 17 字段，不读 PostgreSQL、不初始化 Workspace、不修改 Preflight或TTL。POST 的领域执行使用已发布 workflow-preflight.execute，默认 Workspace 使用 OAuth-write `workspace-default.ensure`，不调用旧 default SQL。Dream Launch 通过 `AdminDreamLaunchWorkflowOperations` 组合 source、Preflight、Run、dispatch 与 failure DTO；Run领域消费见[现行Run设计](workflow-run-admin-consumer-current.md)。真实 Google、真实 PostgreSQL 与模型业务验收仍由主协调执行。

## 概念与规则

### 正常流程与状态

1. 共享身份依赖验证当前 OAuth、principal 与 dream:read；普通 Thread/Run 委托不能用于该公开读取。
2. 路由校验原路径 ID，不接受前后空白；消费者刷新并匹配 identity/unified 两项 schema capability 与实际 read operation 版本/hash。
3. Admin 按 canonical actor 和 ID 读取，并校验当前 Deck owner。读取失败不会创建 default Workspace。
4. Dream 校验闭集 DTO、响应 ID 和 created_by；状态规则复用原 [WorkflowPreflight](../../backend/models/workflow_preflight.py)。公共时间继续使用该模型的 datetime JSON 序列化，保留精确微秒，UTC 输出 Z。

checking、passed、failed、expired 读取都不转换状态。只有 failed 含非 null error_code/failed_check；passed 必须含 snapshot ID/summary，允许 token 为 null。Admin 仅在 passed、未 consumed、未 expired 时按原存储绑定签发 token；Dream 不用当前时钟覆盖结果，不重新计算有效期。非 passed 不暴露 token。expires_at 必须严格晚于 created_at，比较保留六位微秒与时区。

字段中的 nullable 项必须显式提供；空字符串保留原模型允许的含义，不新增产品限制。binding_revision 的非负安全整数是 JSON/TypeScript 技术边界。实际 Zod 执行 `.nonnegative().safe()`，目录 descriptor 的 minimum 仍为负安全下界，属于待修正的导出元数据差异；消费者按实际 runtime 非负规则拒绝负值，不改 capability hash。

### POST 领域执行与原请求回执

POST `/api/story-workspace/workflow-preflights` 保持原 202 与完整模型响应。共享 OAuth/dream:write 与现有默认 Workspace 选择后，输入仅包含 workspace_id、deck_id、binding_revision 和 input_json。JSON 使用原 canonical 编码参数（Unicode/finite/compact/sort keys），保留 Python float、negative zero 与大整数文本；Dream 不计算新 hash、检查事实或 token。Admin 负责原 stages 与数据库提交，执行需 identity/unified/0060 request 三项 exact schema 与实际 operation hash。响应 created_by/Deck/revision 必须匹配。

request_state 为 in_progress 时必须保持 checking、无 token；committed 也可能复用旧 checking。Dream 不重开检查或续 TTL。公共响应继续仅返回原 17 字段，request-state只供领域协议使用。输入 validation/JSON 无法编码时固定 422，不回显 input；这项框架保护只应用于 PF POST。

独立原 PF receipt reader 复用 Admin HTTP transport，要求原 operation/request ID、当前 actor 与三项 schema。公开调用生成 UUID；协议 request ID 仍遵循原 Identifier，并非仅允许 UUID。absent 没有 result；in_progress/committed 的 result.request_state 必须匹配状态，包含原完整 Preflight。in_progress 不自动 resume；absent 不表示 rollback，也不触发重发；committed 保留原时间和 token，即使目前已过期也不重签。所有其他领域仍使用原通用两态 receipt。服务器消费方法不增加公开恢复路由或自动恢复流程。

### 失败反馈

GET 坏路径 ID、缺失记录或其他 actor 继续返回原 WORKFLOW_PERMISSION_DENIED/404。capability/DTO/identity 错配 fail closed；GET/receipt 超时使用安全 code、原 UUID 与 outcome_unknown=false。execute 已发出的超时/损坏回复或绑定错配保留原 UUID/outcome_unknown=true，不自动重发或猜测提交结果；显式读取原 receipt。token 与原始 input_json 从 DTO repr 中排除。没有额外确认或环境名称分支。

### 影响范围与验收

受影响模块为 [公开路由](../../backend/routers/story_workspace.py)、[读取消费者](../../backend/services/admin_data/preflight_data.py) 与 request-auth operation 注册；其他 Story Workspace 路由、原状态模型、Runtime、资源 LKG、共享文件及 TMPDIR 协议不变。

[生产入口技术测试](../../backend/tests/test_admin_preflight_routes.py) 使用实际 FastAPI/OAuth owner/client/DTO 与 MockTransport，禁止 Dream get_db/default Workspace/旧 service。覆盖完整字段、所有状态与 null token、微秒/时区、required nullable、响应 actor/ID、schema/hash、原404、拒绝 Runtime grant及同 UUID 超时无重试。它不证明真实 Admin 签名或普通账户/模型业务链路。

本地已发布安全回执提供 Admin remaining-read 8cases/74assertions 与原 permission tail 11assertions exit0；它们是隔离技术证据，原完整命令失败历史仍保留。正常服务、真实 PostgreSQL 和 Admin 可见业务验收由主协调执行。

[领域执行技术测试](../../backend/tests/test_admin_preflight_execution.py) 使用生产 POST/认证/client/DTO，旧领域 service/SQL 被 fence，默认 Workspace loader 在测试中显式注入以隔离领域合同。覆盖 raw JSON、原202/17字段、request-state、三态同UUID receipt、capability/scope/绑定错配/私密validation与无自动重发。默认 Workspace 的生产接线由独立完整入口套件验证；这些 fixture 不证明真实 token 或模型验收。

### 默认 Workspace 初始化

`_story_workflow_current_user` 复用已有服务器 workspace_id；否则使用同一 immutable OAuth actor、dream:write 和空 `{}` 调用注册76的 workspace-default.ensure。返回原文本ID，不强制UUID、长度或 trim。Admin按账户串行化初始化并选择 created_at ASC、id ASC 的 oldest-owned Workspace；没有记录才使用配置中的默认名称、settings:{} 和 Admin生成的UUID，在同一事务记录领域结果、receipt与audit。Dream不复制查询、锁或默认值。

default需identity/unified两项exact schema与实际hash 5fb0f70b1790979687090e6c04dd837f24ff0a4c0598d95d5085117e65aa2b95，OAuth-write-only；server-persistence/Editor bearer不替代公开授权。初始化失败停止后续PF/Run/launch。HTTP超时保持共享client的504、安全UUID和unknown；坏回复503/unknown，其他拒绝保持安全code/status。显式originalGET只查询原UUID/operation、空input digest、all-null scopes和当前owner，返回absent或committed原textID；absent不触发初始化。默认初始化是写操作，服务器尚无Workspace的Run GET等入口只有dream:read则403；已有服务器workspace_id继续原read路径，PF GET始终不初始化。

[完整生产入口技术测试](../../backend/tests/test_admin_default_workspace.py)保留实际default loader，以MockHTTP替代Admin transport并fence旧DB/service；验证default先于PF/Run、原202/200/201/full模型、原textID、401/403/capability/unknown stop与同UUID两态receipt/no resend。Dream Launch 独立套件验证 Admin Preflight/Run 组合与失败恢复。原独立PF/Run领域套件继续用显式default DI隔离各自合同；它们只证明相关生产入口，不代表 Dream 全项目数据库迁移或真实业务验收完成。

### 三个公开 current-user resolver

StoryWorkflow、Deck binding 和 Deck Plugin 均调用routers.deps的同一个默认helper。helper算法从阶段33的Story原typed实现直接抽取，服务器workspace_id分支、OAuthwrite/empty input/两schema/原text ID/unknown原UUID/停止业务操作与原两态receipt保持。DeckPlugin resolver额外角色查询复用已注册user-profile.current（identity.better-auth.v1版本1/实际hash、OAuth dream:read），AdminRequestAuth检查current profile ID与actor canonical ID相同。已有服务器role非空保持；新读取返回raw role，权限函数依原role/scopes判断，不猜alias。Profile不可用、超时、坏DTO/ID错配明确失败，不fallback user。POST只有write且需profile则403；GET需默认初始化仍要求write，已有服务器workspace_id可走原read路径。

[新公开入口技术套件](../../backend/tests/test_admin_deck_default_workspace.py)保留生产resolver/sharedOAuth/client/DTO，DB fenced，只有尚未迁移的binding/control-plane业务provider使用显式tests DI；验证default→profile→domain、rawtext/serverworkspace/serverrole/权限拒绝、profile scopes/ID/capability/unknown停止。既有binding fixture用default DI隔离领域DTO/CAS，独立新套件验证真实认证/默认依赖。剩余后台/internal输出默认helper仍属于原业务事务，不能拿public ensure作为其授权或事务迁移证据。
