<!-- [Input] Published Admin Preflight read/execute/receipt DTOs and original Dream model semantics. -->
<!-- [Output] Current ownership, state, failure and acceptance rules for reads and staged execution. -->
<!-- [Pos] Current consumer design; original stage/Run rules remain separately applicable. -->
<!-- [Sync] 2026-09-15: migrate only the owner-scoped GET without default Workspace or SQL. -->
<!-- [Sync] 2026-09-15: consume the execute domain and original three-state receipt; default lookup remains pending. -->

# Preflight 读取与领域执行现行设计

## 背景与问题

原 GET 通过 Dream application service 查询 PostgreSQL，路由还先初始化 default Workspace；实际 read_preflight 只使用 Preflight ID 和 actor ID。Admin 已发布 owner-scoped workflow-preflight.read，并承担记录读取、当前 Deck 所有权校验及 token 签发。公开读取可独立迁移。

## 目标与边界

GET `/api/story-workspace/workflow-preflights/{preflight_id}` 使用统一 Admin OAuth 身份，返回原完整 17 字段，不读 PostgreSQL、不初始化 Workspace、不修改 Preflight或TTL。POST 的领域执行使用已发布 workflow-preflight.execute；现有 default Workspace lookup 尚未迁移，因此 POST 整体仍有 SQL 依赖。Run 创建/重试消费、默认 Workspace、SystemConfig 和 launch source/dispatch 消费是后续入口。阶段30检查时目录已注册75项，新增三项launch仍未接Dream消费者；目录注册与隔离技术验收不等于正常业务完成。

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

[领域执行技术测试](../../backend/tests/test_admin_preflight_execution.py) 使用生产 POST/认证/client/DTO，旧领域 service/SQL 被 fence，默认 Workspace loader 在测试中显式注入。覆盖 raw JSON、原202/17字段、request-state、三态同UUID receipt、capability/scope/绑定错配/私密validation与无自动重发。这个 fixture不证明生产 default lookup 已迁移，也不证明真实 token 或模型验收。
