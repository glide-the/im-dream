<!-- [Input] Published Admin Preflight read DTO and the original Dream GET/model semantics. -->
<!-- [Output] Current ownership, state, failure and acceptance rules for public Preflight reads. -->
<!-- [Pos] Current read design; original execute/Run designs remain separately applicable. -->
<!-- [Sync] 2026-09-15: migrate only the owner-scoped GET without default Workspace or SQL. -->

# Preflight 读取现行设计

## 背景与问题

原 GET 通过 Dream application service 查询 PostgreSQL，路由还先初始化 default Workspace；实际 read_preflight 只使用 Preflight ID 和 actor ID。Admin 已发布 owner-scoped workflow-preflight.read，并承担记录读取、当前 Deck 所有权校验及 token 签发。公开读取可独立迁移。

## 目标与边界

GET `/api/story-workspace/workflow-preflights/{preflight_id}` 使用统一 Admin OAuth 身份，返回原完整 17 字段。Dream 不读 PostgreSQL，不初始化 Workspace，不修改 Preflight，不创建 Run，不续 token TTL。POST execute、Run 创建/重试、默认 Workspace 与 SystemConfig 是后续入口；隐藏 launch-source.ensure 尚未注册。当前目录的 72 项注册不等于新增 Run 公开集成或正常业务验收已完成。

## 概念与规则

### 正常流程与状态

1. 共享身份依赖验证当前 OAuth、principal 与 dream:read；普通 Thread/Run 委托不能用于该公开读取。
2. 路由校验原路径 ID，不接受前后空白；消费者刷新并匹配 identity/unified 两项 schema capability 与实际 read operation 版本/hash。
3. Admin 按 canonical actor 和 ID 读取，并校验当前 Deck owner。读取失败不会创建 default Workspace。
4. Dream 校验闭集 DTO、响应 ID 和 created_by；状态规则复用原 [WorkflowPreflight](../../backend/models/workflow_preflight.py)。公共时间继续使用该模型的 datetime JSON 序列化，保留精确微秒，UTC 输出 Z。

checking、passed、failed、expired 读取都不转换状态。只有 failed 含非 null error_code/failed_check；passed 必须含 snapshot ID/summary，允许 token 为 null。Admin 仅在 passed、未 consumed、未 expired 时按原存储绑定签发 token；Dream 不用当前时钟覆盖结果，不重新计算有效期。非 passed 不暴露 token。expires_at 必须严格晚于 created_at，比较保留六位微秒与时区。

字段中的 nullable 项必须显式提供；空字符串保留原模型允许的含义，不新增产品限制。binding_revision 的非负安全整数是 JSON/TypeScript 技术边界。实际 Zod 执行 `.nonnegative().safe()`，目录 descriptor 的 minimum 仍为负安全下界，属于待修正的导出元数据差异；消费者按实际 runtime 非负规则拒绝负值，不改 capability hash。

### 失败反馈

坏路径 ID、缺失记录或其他 actor 继续返回原 WORKFLOW_PERMISSION_DENIED/404 与固定错误文案。capability/DTO/identity 错配 fail closed；transport 超时使用安全 code、原 request UUID 和 outcome_unknown=false，不自动重试，不回传上游消息或正文。token 从 DTO repr 中排除。没有额外确认弹窗或环境名称分支。

### 影响范围与验收

受影响模块为 [公开路由](../../backend/routers/story_workspace.py)、[读取消费者](../../backend/services/admin_data/preflight_data.py) 与 request-auth operation 注册；其他 Story Workspace 路由、原状态模型、Runtime、资源 LKG、共享文件及 TMPDIR 协议不变。

[生产入口技术测试](../../backend/tests/test_admin_preflight_routes.py) 使用实际 FastAPI/OAuth owner/client/DTO 与 MockTransport，禁止 Dream get_db/default Workspace/旧 service。覆盖完整字段、所有状态与 null token、微秒/时区、required nullable、响应 actor/ID、schema/hash、原404、拒绝 Runtime grant及同 UUID 超时无重试。它不证明真实 Admin 签名或普通账户/模型业务链路。

本地已发布安全回执提供 Admin remaining-read 8cases/74assertions 与原 permission tail 11assertions exit0；它们是隔离技术证据，原完整命令失败历史仍保留。正常服务、真实 PostgreSQL 和 Admin 可见业务验收由主协调执行。
