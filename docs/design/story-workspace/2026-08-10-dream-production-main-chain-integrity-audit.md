# Dream 剧本生产主链完整性审计

日期：2026-08-10
阶段：任务一，只读审计结论（实现前基线）
范围：Dream、Admin 公共 Gateway 合同、PostgreSQL、前端 session/恢复状态与现有测试。未调用真实收费 Provider，未向共享数据库写入。

## 1. 结论

当前代码已经具备较完整的订阅 BFF、Gateway 模型目录、Workflow Run 原子创建、Dream Files、Dream Agent 消息、Episode artifacts、ETag/revision、权限隔离和 PostgreSQL 类型兼容测试，但**尚不能证明 Dream 剧本生产主链发布完整**。

发布阻断缺口有两个：

1. 标准 Chat 会解析并传递服务端选定的平台模型；Dream launch、Dream Agent 消息、确认续写和 guidance 内部回合创建 `ClaudeAgentRunRequest` 时未传 `model`。Agent Runner 因而可能通过 Gateway 执行，却没有证据证明使用了用户已保存且当前可调用的 platform model identifier。
2. Dream launch 接受任务后立即把源消息标为 `dispatched`，后台消费协程忽略 SSE 错误；同时 Story Workspace 未连接 Runtime Load Receipt / Agent Session，所以 Workflow Run 通常停在 `queued`。Provider、Gateway 或上下文装配失败可能只存在于短生命周期内存事件中，刷新后无法从 Workflow Run 得到真实失败事实。

因此，“Mock 成功”“单接口 200”或当前 295 个后端 focused tests 通过，只证明局部合同，不等于用户从资格到产物读取的业务 E2E 完整。

## 2. 经审计的主链与真值所有者

| # | 业务步骤 | 当前事实来源 / 真值所有者 | 审计判断 |
|---|---|---|---|
| 1 | 登录并解析 canonical user | Dream auth dependency + PostgreSQL user | 已有 actor 校验；BFF 会验证 subject 存在、启用且响应 subject 一致 |
| 2 | Subscription / Plan Version / Entitlement / Allowance | Admin Subscription + PostgreSQL | Admin 为唯一真值；Dream 只做代理和展示，不在浏览器推导 |
| 3 | 获取模型目录 | `GET /api/gateway/models` → Admin `/v1/models` | 已接入；DTO 严格、错误码保留；设置页刷新失败会清空 last-good，需改进 |
| 4 | 保存模型 | `PUT /api/system-config` + live catalog validation | 只保存 alias 和 `provider=gateway`；无 Provider Secret 入浏览器，基本正确 |
| 5 | 创建/重入 Run | `WorkflowRunService` + PostgreSQL；reentry 聚合 Dream facts | 创建、幂等、权限与重入覆盖较强；run 生命周期没有接入 Dream 执行 |
| 6 | Dream Agent 使用所选模型 | Claude Agent service / Gateway | **缺陷**：四条 Dream 内部路径未绑定服务端解析后的 alias |
| 7 | alias / entitlement / provider routing | Admin Gateway | Admin 真值；Dream 必须每回合 fail-closed，不得信任客户端 alias |
| 8 | reserve / capture / release | Admin Token Ledger | Admin 已有单元与真实 PG E2E；Dream 仓库不能直接证明真实 Provider canary |
| 9 | 受控产物写入 | thread workspace Dream Files + PostgreSQL binding/index | 文件 schema、stage、review、prompt、render guide 有大量合同测试 |
| 10 | Run / Files / Messages / Binding / Artifacts / Projection 一致 | PostgreSQL + canonical files，各服务拥有各自 projection | 产物侧较强；Workflow Run 状态与异步 Agent 结果脱节，未满足完整一致性 |
| 11 | 刷新/重入/桌面/移动恢复 | 服务端 reentry + hooks 的 last-good / request isolation | Files、messages、artifacts 覆盖较强；Workflow 失败恢复不足；模型目录 last-good 不足 |
| 12 | 安全失败呈现 | 服务端安全错误合同 + UI error state | 订阅/目录局部正确；launch 异步错误可能被吞掉并表现为继续生成 |

## 3. 已有覆盖

### 3.1 后端

- Gateway catalog：严格字段、alias、callable/availability、default alias、401/402/403/409/429/502/503 映射。
- 模型保存：只接受合法 alias，保存前查 live catalog；下架返回 409，无资格返回 403。
- 标准 Chat：服务端 preference 优先、客户端不得覆盖、无保存项时使用 live default。
- Gateway inference adapter：服务端凭据、流式协议和安全错误映射。
- Workflow Run：preflight、幂等、权限、并发冲突、重试、状态机、PostgreSQL 原生 datetime/boolean。
- Dream launch/files/messages/confirmation/tool confirmation/Episode artifacts：范围边界、DTO、revision/ETag、重复提交与错误合同。
- PostgreSQL runtime：正式运行时只使用 PostgreSQL pool，并要求 Alembic head；不存在运行时 SQLite/JSON/内存 fallback。

实现前 focused baseline：`295 passed, 4 skipped, 141 subtests passed`。第一次从错误目录启动导致 `0 executed / 1 collection error`，已确认是测试工作目录问题，不是产品失败。

### 3.2 前端

- Gateway catalog Zod strict contract 和安全状态文案。
- Subscription context/plans/preview/execute 的 last-good、幂等引用和 409 刷新。
- Dream Files、Agent messages、tool confirmation、confirmation、Episode artifacts 的 run 切换隔离、late-response 丢弃、empty/error/last-good 合同。
- Episode artifact 真实只读浏览器规格包含 1440×1000、390×844、关键产物计数、action projection 和无写请求断言。
- Model Settings 的 Mock E2E 已证明目录驱动、禁用无资格模型、只保存 alias。

## 4. 缺失覆盖与可见故障

| 缺失 / 故障 | 触发条件 | 用户影响 | 分类 | 级别 |
|---|---|---|---|---|
| Dream 内部回合未解析所选模型 | launch/message/confirmation/guidance | 用户选择可能不生效；调用事实无法与资格和计费对账 | 代码缺陷 + 测试缺口 | 必须修复 |
| launch 异步错误被消费但不持久化 | Gateway/Provider/上下文装配/流式中断 | 页面可显示继续生成，刷新后仍无失败原因 | 代码缺陷 + 交互缺陷 | 必须修复 |
| Workflow Run 长期 `queued` | Dream 未建立 receipt/session/状态迁移 | Run detail 与 files/messages 不一致，不能作为恢复真值 | 架构集成缺口 | 发布门禁 |
| 模型目录刷新清空 last-good | 已经加载成功后刷新 401/5xx | 设置页失去仍可解释的上次目录，用户无法区分首次失败与刷新失败 | 交互/代码缺陷 | 应当修复 |
| system-config GET 失败无独立状态 | 设置页配置请求失败 | 可能以默认值渲染，让用户误判保存状态 | 交互缺陷 | 应当修复 |
| 无 Dream 主链 token 对账 E2E | 未做隔离 Admin+Dream 联测 | 无法证明同一 Dream turn 的 reserve/capture/release 与 run/message 对应 | 测试缺口 | 发布门禁 |
| 旧 `dream-surface.spec.ts` 依赖 SQLite | 运行旧浏览器 lane | 与 PostgreSQL-only 运行时相悖，可能制造假绿或污染旧文件 | 测试债务 | 禁止用于验收 |
| 真实收费 Provider canary 未授权 | 外部真实推理 | Provider 真实 usage/流中断只能由安全 canary 证明 | 外部场景 | 可延期但必须声明 |

## 5. 根因

1. 模型选择逻辑放在 HTTP Chat router 私有函数中，而内部 Dream dispatcher 绕过 router；共享 Agent service 未承担“每回合解析与验证 alias”的不变量。
2. Dream launch 将“后台任务已创建”当成“dispatch 已完成”，没有把 stream terminal/error 结果回写到持久层。
3. Workflow Run 的严格状态机来自 Runtime Plugin 架构；Dream 当前 Agent 执行没有创建匹配的 Receipt/Session，因此不能合法进入 `running`。旧设计选择忽略 run status，形成第二套生命周期投影。
4. 设置页把 catalog error 当成替换数据，而不是 refresh metadata；所以失败时删除 last-good。

## 6. 推荐的最小安全方案

### 第一阶段（本轮可实施）

1. 将平台模型解析抽为 server-only 领域服务；输入 canonical user 和可选 client alias，输出 live callable alias，保留 403/409/5xx 安全合同。
2. 在 Claude Agent context assembly 中对**每个新回合**执行解析，并把结果写入 `AgentRunOptions.model`；标准 Chat router 继续拒绝 client mismatch，内部 Dream 路径无需信任浏览器字段。
3. 为 Dream launch 增加调用前资格检查，禁止在已知无模型/无资格/Gateway 不可用时创建虚假成功；异步 terminal error 必须落为安全可读事实，至少将合法的 `queued` run 转为 `failed`。
4. 模型目录刷新失败时保留 last-good models，显示“当前展示上次成功目录”的 alert 和重试；首次失败仍 fail-closed。
5. 先写失败测试，再实施，覆盖内部路径、错误映射、last-good 和无 secret/路径泄露。

### 第二阶段（独立发布门禁）

让 Dream runtime 通过现有 Runtime Reconcile → Load Receipt → Agent Session 链进入 `running`，并在 canonical stages、review、confirmation、continuation、completion 上由服务端做合法状态迁移。此阶段不能用直接 UPDATE 或放宽 `_ALLOWED_TRANSITIONS` 代替。

### 第三阶段（隔离环境验收）

以单独 PostgreSQL clone 和本轮自有端口联起 Dream + Admin Gateway safe canary，按同一 correlation/idempotency key 对账 model alias、Workflow Run、Agent message、reserve/capture/release、artifacts。未授权时 Provider 使用 deterministic stub，真实 Provider 标为未执行。

## 7. 不应采用的方案

- 不在前端复制模型目录、entitlement 或 allowance；会制造第二套真值并导致资格漂移。
- 不将 `queued` 直接更新为 `running/completed`；会绕过 Receipt、Session 和合法迁移证据。
- 不吞掉 Gateway/Provider 异常并生成 assistant “成功”消息；会产生虚假成功和错误计费预期。
- 不硬编码当前用户、plan、alias、run 或 artifact 数量来让 E2E 通过。
- 不恢复 SQLite、JSON 或内存 fallback；会掩盖 psycopg 类型、事务和并发问题。
- 不放宽测试断言、使用 forced click 或截图替代业务断言。

## 8. 测试矩阵与真值断言

| 场景组 | 关键场景 | 必须断言的事实 |
|---|---|---|
| 身份/资格 | 无订阅、无模型权限、allowance exhausted | canonical subject 一致；401/402/403 原样安全呈现；无 Agent/Provider 调用 |
| Catalog | success、empty、last-good refresh、409 stale、429、502、503 | catalog 只来自 Gateway；只保存 alias；失败不伪造目录 |
| Run | create/replay/conflict/reentry/refresh/cross-actor | 幂等 key、actor/workspace/source 不漂移；错误不泄露其他 run |
| Agent | SSE、取消、重试、工具确认、stream abort | model 为 server-resolved alias；terminal/error durable；重复请求不重复执行 |
| Artifacts | characters/scenes/script/storyboard/review/prompt/render guide | canonical file schema、revision、binding、projection 与 episode 作用域一致 |
| Token | reserve/capture/release/replay/missing usage | ledger 序列、usage 与响应一致；失败 release；无 cash fallback |
| PostgreSQL | datetime、JSONB、boolean、nullable、conflict | 使用 psycopg 原生值；事务提交/回滚明确 |
| UI/可访问性 | 1440×1000、390×844、键盘、focus、ARIA | loading/empty/error/last-good 可区分；无强制点击；焦点恢复 |
| 诊断/安全 | console/pageerror/requestfailed/HTTP | 无非预期错误；无 Token、Secret、DSN、绝对路径或 Provider 凭据 |

## 9. 发布判断

当前判断：**不满足完整主链发布证明**。第一阶段修复与验证完成后，可将“模型选择与显式失败”从阻断降为已验证；但在 Dream 合法接入 Runtime Receipt/Agent Session 状态迁移、并完成隔离 PostgreSQL 的跨服务 Token 对账前，不应宣称 Workflow/计费/产物全链一致。真实收费 Provider 未执行时必须继续作为诚实遗留。

## 10. 回滚与清理

- 回滚单位：共享模型解析服务、Agent context 接入、launch 失败持久化、Model Settings last-good UI，均保持可独立回退。
- 不修改 Workflow 状态机合法边、不修改 Admin 计费账本、不迁移或重归属现有数据。
- 测试只使用精确命名数据库/用户/端口/输出目录；共享数据库仅 SELECT 或事务 rollback。
- 验收后关闭本轮自有服务，删除本轮精确命名资源，并保留未授权外部场景清单。
