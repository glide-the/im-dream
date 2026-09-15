<!-- [Sync] 2026-09-15: consume registered Run cancel with original reason/full result and bounded receipts; other lifecycle gaps remain. -->
<!-- [Sync] 2026-09-15: consume registered76 OAuth-write default Workspace; original text ID/receipt and independent read scope stay explicit. -->
<!-- [Input] Published Admin Run read/create/retry/cancel/fail DTOs and original WorkflowRun/application semantics. -->
<!-- [Output] Current consumer ownership, normal flow, states, failures and technical acceptance limits. -->
<!-- [Pos] Current Run data migration rules; original lifecycle and launch designs remain indexed separately. -->
<!-- [Sync] 2026-09-15: delegate three Run domain operations while retaining the default Workspace dependency. -->
<!-- [Sync] 2026-09-16: wire launch failure recording through Admin Run fail and failure-envelope DTO operations. -->

# Run Admin 消费现行设计

## 背景与问题

原公开 Run 读取、创建和重试通过 Dream application service 查询或写 PostgreSQL。Admin 已发布三个领域操作并承担身份归属、冻结来源、Preflight token 消费、Run/transition/receipt/audit 原子提交。Dream 继续负责公共投影及后续 Runtime/文件业务。

## 目标与边界

GET `/api/story-workspace/workflow-runs/{workflow_run_id}` 保持原200，POST `/workflow-runs` 与 POST `/workflow-runs/{workflow_run_id}/retry` 保持原201，全部返回原完整28字段模型。这三个公开入口及其默认 Workspace 选择均使用已注册 Admin 操作，不调用 Dream SQL/service；其它生命周期入口独立追踪。

公开入口已消费 read/create/retry/cancel；生产 Dream launch 也通过同一 `AdminRunData` 消费 create/read/fail，并通过 Registry133 在当前 actor 范围恢复冻结 Run。guidance、confirmation、SystemConfig、内部 agent-output 与其它领域仍按迁移清单追踪。目录注册与隔离技术测试不等于正常业务验收。

## 概念与规则

### 正常流程与状态

1. 共享认证校验当前 Admin OAuth 与 principal，GET要求dream:read，POST要求dream:write；Thread/Run server grant不能代替公开OAuth。
2. 默认 Workspace 通过 OAuth-write workspace-default.ensure，空输入、原文本ID和原两态receipt；服务器已有 workspace_id 保持复用，尚未绑定时即使 GET 也要求 dream:write，只有read则403且不执行领域操作。初始化失败停止，未知不自动重发。具体[默认规则](workflow-preflight-read-current.md#默认-workspace-初始化)与 `_workflow_actor` 顺序保持。消费者匹配 identity/unified 两项 exact schema及三个 operation 的版本/hash，缺少任何项即fail closed。
3. Read仅传服务器Workspace与路径RunID。坏ID或前后空白按原Run-not-found返回registry404，不将DTO trim用作路径修复。
4. Create只传Workspace、PF ID/token、业务key与三项required nullable source。Source必须全null或完整thread/message/aware time tuple；公开时间先用原datetime.fromisoformat解析，按Python微秒精度截断后传输，不计算token/hash/fingerprint/RunID。
5. Retry只传原Run lookup、PF/token与新业务key。Admin读取原source并校验原failed/rejected/cancelled等前置条件；Dream不新增preread、状态转换或Runtime dispatch。
6. Admin回复经闭集DTO、canonical actor/Workspace及完整原模型校验。Read匹配ID，write匹配key与retry_of，Create还匹配完整source tuple及aware time。相同key可复用另一个同语义PF，因此不要求回复PF ID等于本次输入。

DTO复用原 [WorkflowRun](../../backend/models/workflow_run.py) 校验failed字段、receipt/session联合绑定、started状态、原legacy thread-only读取、source/session ID限制及created/started/completed状态与顺序。全部nullable字段必须显式提供，时间aware且输出最多六位微秒。公共datetime JSON继续由原模型生成，UTC为Z，不使用Dream clock改写历史状态。

binding_revision/status_version为正安全整数；key最多255 Unicode codepoints，属于原协议和JSON技术边界。Pydantic trim后还按原Python strip拒绝空key；保留两者对额外控制字符的不同处理，不增加产品配额或sentinel。

### 原请求回执与失败反馈

写超时、损坏回复或绑定错配使用安全error code、原UUID与outcome_unknown=true；不重发、不推断rollback，也不自动启动模型。服务器显式用相同operation/input/UUID读取原通用两态receipt。absent无result且不触发重发；committed含完整bounded Run，重新校验actor/Workspace/key/retry或Create source。Admin在读取回执时验证当前owner与冻结来源，Dream不拿当前Run状态覆盖原请求结果。

原八项业务错误映射提取到 [error_registry](../../backend/services/errors/error_registry.py)，原application静态方法继续调用同函数并保持fallback。公开消费者只在原code/status匹配且非unknown时返回旧registry payload；INVALID_RUN_REQUEST的400/422沿旧fallback返回422。其他Admin错误保留安全UUID/unknown，不猜新alias，不回显upstream文本。框架validation保护只安装在两个Run POST，固定422详情且不回显token/source；语义tuple/时间/key错误使用原安全422。token从input DTO repr排除。

### 影响范围与验收

[消费者](../../backend/services/admin_data/run_data.py)、[公开路由](../../backend/routers/story_workspace.py)、request-auth注册及原error mapping提取是本阶段范围。其他Story Workspace函数、原模型、PF三态/通用两态receipt、Runtime/资源LKG、共享文件和TMPDIR协议保持。

[生产入口技术测试](../../backend/tests/test_admin_run_routes.py) 使用实际FastAPI/OAuth/client/DTO与MockHTTP。旧领域SQL/service被fence，该独立领域套件的default loader只在tests依赖注入；新增[默认初始化生产入口套件](../../backend/tests/test_admin_default_workspace.py)不覆盖loader，验证完整default→domain的授权/失败/顺序；覆盖十种状态、28字段/required nullable/微秒/时区、完整source/255 astral key、错配/原404与业务错误、scope/schema/hash、同UUID两态receipt及无重试。原SQLite技术fixture仍跳过行锁并发测试，不代表PG并发已验收。

Admin安全回执中的Run72 remaining public230、atomic业务68/原wrapper cleanup exit1与独立SELECT cleanup3 exit0均保留各自范围。Root未重跑隔离PG或正常业务；普通账户、真实PostgreSQL、Admin可见Run/账本及模型验收由主协调执行。

### 公开 Run cancel

POST `/workflow-runs/{workflow_run_id}/cancel` 复用当前OAuth dream:write与已注册默认Workspace依赖，默认初始化先于领域取消。公开request模型保持reason的原default、Pydantic trim、min1/max500；这些是原协议约束，不新增产品额度或确认。消费者把原 `user_cancelled:{request.reason}` 作为required nullable reason_code wire（wire不trim、不加长度限制）；只传服务器Workspace/路径Run与reason，不传actor、target status、clock或Runtime facts。Admin按原生命周期规则转换为cancelled，同状态返回原结果，非法transition409；独立Run/history/receipt/audit事务与current owner/source校验由Admin执行。

消费者要求exact identity/unified、版本1与实际hash d46995d76d34585e93303ff91b1c83c3bc5b028f27edfa840e1057256518647e。回复匹配actor/Workspace/路径Run/cancelled状态并通过原完整28字段模型，保持200与微秒JSON；bad path不trim修复，沿原404映射，原八业务error code/status复用。cancel POST使用原Run scoped safe validation，固定422无raw reason回显；reason从DTO repr排除。已发出timeout504/坏回复503保留安全UUID/unknown，不重发或推断rollback。显式同operation/input/UUID generic原两态receipt；committed再检查完整绑定/cancelled，absent不重发。

[公开生产入口技术套件](../../backend/tests/test_admin_run_cancel.py)复用完整default fixture，无替代loader/Run handler，验证default→cancel、原reason/model/default/range、重复producer结果、原404/八errors、OAuth/schema/hash、wrong reply/unknown/receipt两态。重复请求用例只证明消费者不自行转换状态，数据库幂等由producer独立回执负责。旧application/WorkflowRunService/模型和其它Story函数保留；此Run状态接口不改Agent turn/resume/cancel/SSE、资源admission/lease、Runner/FS/TMPDIR，正常模型与其它生命周期持久化仍待验收。
### Run fail 生产接线

Admin 已注册 workflow-run.fail v1/write/dream:write，实际 hash 为79e2fbb8f96aa241b664657f03e77020d9cbd2cc8f8b67eeae89a02ea34ac31f，复用 identity/unified 两项 exact schema。[消费者](../../backend/services/admin_data/run_data.py)输入为服务器 Workspace/Run、required failed_step/error_code 与 required nullable reason_code；三项失败文本保留原字符串，非空校验不 trim、不增加配额或 sentinel。状态转换、数据库 clock、transition/receipt/audit 原子提交及 current owner/frozen source 校验继续由 Admin 执行。

回复使用原完整28字段模型，必须匹配 canonical actor/Workspace/Run 与 failed 状态。原 same-failed replay 不改历史 failed_step/error_code，消费者不要求它们等于本次请求，也不生成新 completed_at 或 status_version。timeout/回复错配保留原 UUID/unknown；显式同 operation/input/UUID 原两态 receipt，committed 重做完整绑定校验，absent 不重发。

生产 `DreamLaunchFailureRecorder` 使用请求绑定的 current OAuth owner，先调用 `workflow-run.fail`，仅在返回完整 failed Run 后调用 `dream-launch-failure.envelope`。两次写各自使用新的 request ID；超时只读取各自原 receipt，不盲重试。actor、Workspace、Run 和 source ID 均由服务端上下文或 Admin 已存事实校验，不创建通用后台账户，也不把两个原事务伪装为一次提交。[launch 组合测试](../../backend/tests/test_story_workspace_dream_launch_api.py)覆盖调用顺序、同 actor/client 接线和无 SQL；[类型测试](../../backend/tests/test_admin_launch_failure.py)继续覆盖单个 DTO/HTTP 契约。真实长时 token 过期与正常模型验收仍需在本机服务链路执行。
