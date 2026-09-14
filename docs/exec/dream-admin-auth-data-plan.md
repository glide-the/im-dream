<!-- [Input] User delegation, Agent.md, AGENTS.md, baseline 7d38715c, and Admin-owned contracts when published. -->
<!-- [Output] Executable Dream migration plan, dependency gates, and exact evidence inventory. -->
<!-- [Pos] Dream implementation plan; Admin owns authentication, database transactions, and schema contracts. -->
<!-- [Sync] 2026-09-14: establish the implementation goal and first scan/design stage. -->

# Dream 接入 Admin 认证与数据服务执行计划

## 背景与问题

Dream baseline `7d38715c1a8f74cb5fb3dcb114320156eaf6b3e6` 的 Python Authlib、自签 JWT 与生产 PostgreSQL 访问需要迁移。基线 Release 已发布，不重复发布。当前工作区为 `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`，实现分支 `codex/dream-admin-auth-data-client`。目标状态以 Codex goal 为准，未完成实现、文档和必需验证不得完成 goal。

## 目标与边界

四项目迁移前基线均已发布，只记录关联，不重复发布/升级pins：Dream `7d38715c`、Admin `017f3ac`、Runtime `d9c16304330b393c86e650926b191c0cfeaf0bf2` (`v0.1.9-pre-admin-auth-data.20260914`)、SDK `d6b87f14549c01f921c664fe525ba986b4ac8d88` (`v0.2.145-pre-admin-auth-data.20260914`)。Runtime/SDK仅源码tag/Release，不代表版本或registry接口更改。

Admin 任务 `01a0a03d-f058-7130-bfa9-71d2bb0bc1c9` 在 `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory` 唯一定义认证和领域数据 API。Dream 只消费实际契约及已发布 capability，不能提供 SQL gateway、通用表列 CRUD、运行时 DDL、PG fallback 或另一个 token authority。原账户 PK、实体关联、原事务并发条件必须保留。相邻 Admin 只读；协调任务拥有其协调文档。

Next 页面、FastAPI 业务编排、Runner/ThreadFactory/service/EventBus/SSE、turn/resume/cancel、admission 算法及既有 lease、共享 FS、server-owned Runtime snapshot 和精确 `.claude-tmp` 协议保持原行为。真实业务验收仅使用用户指定现有账户、实体、模型与调用次数，条件未给出时不执行或冒称完成。

## 概念与规则

身份认证、Dream 访问、Admin 管理、实体权限、服务身份与用户委托分别校验。Admin unavailable、timeout、权限拒绝、capability 缺失必须有明确失败回执；非幂等写不盲重试，未知提交通过 Admin 规定的请求 ID 恢复。资源后台同步错误保持 LKG，不能传播 turn；turn 主路径不新增资源策略远程查询。

## 阶段 1：完整扫描与设计

### Optimized Prompt

作为 Dream 实现负责人，依据用户授权和 baseline 证据完成全部生产 DB 与认证入口清单，并向 Admin 唯一接口负责人反馈。先读取根维护合同、中英 README、规则索引、Cursor 规则和涉及目录合同；重点读取认证、Device、项目架构、跨项目交互与验证脚本，每次只保留必要设计文档。用 Python AST 与 `rg` 联合扫描 Python/Next 生产代码、启动健康、后台 worker、model catalog、observability、state/preferences、Notion pool、文件 metadata、Run/Thread/message、Deck/Plugin/MCP 和所有 SQL/UOW 调用。每文件记录函数、表/数据、事务/锁/CAS/冲突、身份权限、目标 Admin 接口状态、替换策略与行号证据；单独标识 importer、fixture、技术 harness 与真实运行入口。不得将缺少接口标为完成，不创建临时 SQL gateway。

向协调和 Admin 任务报告绝对路径、实际分支、认证/拓扑基线和清单。接收实际契约后逐项评审覆盖正常流程、状态、失败恢复、配置、PK 映射、API、发布/回滚，并将后续实现阶段的 Optimized Prompt 写入本文件后立即执行一次，不递归优化。复用现有领域抽象；保留历史设计原文并索引。架构与认证现行稿保持背景与问题、目标与边界、概念与规则，并以 Admin 唯一规范链接确定接口。六张 Mermaid 对应 Google、Dream API→Admin DB、Device、refresh、业务 persist/SSE、共享 FS/meta。

验收：生成可重复扫描清单，检查全部直接 DB import/SQL/pool/UOW 与动态入口，确认 Next 是否存在 DB 访问；扫描不读取凭证或业务正文。风险：接口事务粒度不足会拆散一致性；身份映射错误会破坏数据归属；因此等待 Admin 契约再实现客户端，未就绪时继续独立设计和分析。

### 依赖与执行状态

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| goal | active | 当前任务 `01a0a03e-02f7-7221-9118-8bf3f6a91cb3` |
| 分支 | 已建立并切换 | `git switch codex/dream-admin-auth-data-client` exit 0 |
| 初始用户修改保护 | worktree clean | 初始 `git status --short` 无输出；原仓库 repomix 不在本 worktree |
| Admin 规范契约 | 等待实际路径/版本 | 已向 Admin 与协调任务发送契约协调消息 |
| 生产 DB 清单 | 执行中 | [扫描清单](dream-admin-data-inventory.md) |
| 真实业务验收 | 条件部分就绪，未执行 | 用户授权已有账户现有数据；协调持有凭据，正常model catalog选模型、限次并Admin可见；新API/长turn委托待实现 |

## 后续阶段及完成门槛

1. 消费 Admin 契约：统一客户端、JWT/JWKS resource server、Google/BFF/Device/refresh 产品流程，显式停用旧 authority。
2. 逐领域迁移全部生产 SQL/ORM/pool/UOW 与权限/事务至 Admin；Dream 复用 typed repository/domain abstractions。所有实际入口无 PG 凭证/驱动依赖。
3. 资源 API provider 与 observer/snapshot persistence：保留 default/desired/effective/revision、LKG、safe integer/exact bytes、monotonic revision 与 Runtime 所有权。
4. 更新现行设计、历史索引、README 镜像、文件头和目录合同；测试前形成流程/模块/权限/正常与失败恢复影响表。
5. 必需确定性验证由 `luna_test_runner` 执行并等待原始 cwd/command/exit/output；实现、迁移、真实模型验收由主任务负责。技术验证使用显式隔离资源，不停止用户服务；Chrome 仅一次轻量启动检查。
6. 复查生产无 DB 直连和旧 token authority，运行公开入口验证，提交自身修改并报告实际 branch/commit、命令、退出码与真实回执缺口。任何必需项未完成时 goal 保持 active。

## 阶段 2：统一客户端与身份验证基础

### Optimized Prompt

消费已经读取的 Admin 规范 `0.1`（实际文件 `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/docs/architecture/admin-dream-auth-data-contract.md`，设计状态、未发布runtime capability），在 Dream 内实现无PG依赖的统一 transport和OAuth JWT验证基础。复用现有httpx/Pydantic/PyJWT/cryptography依赖、no-retry/redacted error模式，但现有Product客户端绑定HS256和Product专属响应过滤，不能承担全领域协议。新增单一 `services/admin_data`模块，server-owned配置限定HTTPS或明确loopback HTTP、固定Admin origin/issuer/resource、独立service secret、有限timeout/response大小和JWKS cache；禁止ambient proxy、token指定URL、开放redirect、日志凭证或用户ID覆盖。

JWT用成熟PyJWT验证ES256、`at+jwt`、exact issuer/audience、exp/iat/jti/client_id/scope、最多300s寿命、非空BA subject；canonical users.id必须由Admin principal映射，不能转换sub猜ID。JWKS缓存按配置，未知kid受控刷新，缓存/网络错误fail closed，不逐请求获取。transport只调用严格注册领域operation，输入/输出闭集DTO、request_id回显，非幂等写网络/timeout/无效成功响应视为unknown commit，保留原request_id/input摘要并显式receipt恢复，不盲重试，不认为absent证明rollback。Admin未定义或未发布DTO的方法保留依赖gate，不接生产或虚构返回。

同步文件头、目录合同、中英README与设计；先列影响/权限/成功失败恢复表。确定性validation交Luna runner：MockTransport协议、凭证脱敏、JWT各种字段/kid缓存、scope/映射边界、timeout/unavailable/denied/request mismatch/unknown commit/receipt恢复，等待cwd/command/exit/output；不碰真实账户/DB/模型。新模块通过后逐领域接实际Admin操作；阶段完成不等于整个goal完成。

### 测试前影响表

| 流程 | 模块 | 权限/数据 | 验证 | 成功 | 失败恢复 |
| --- | --- | --- | --- | --- | --- |
| OAuth API验证 | admin_data JWT verifier | 只解Admin BA subject/scope，不猜users.id | 签名/typ/算法/issuer/audience/time/JTI/client/scope + JWKS轮换 | 返回不可变token claims | 401/403或依赖503，不fallback旧JWT |
| 内部领域调用 | admin_data transport | service +用户委托/明确定义后台scope | strict DTO/注册operation/request_id | 确切DTO | 安全错误；写未知提交保留request_id |
| 写请求恢复 | admin_data receipts | 原operation/主体/服务/input匹配 | committed/absent/异值/未知响应 | 原提交结果 | absent仍保持未知，不创建新ID |
| 浏览器会话 | Next BFF（待DTO） | host-only handle与Admin encrypted store | PKCE/state/origin/CSRF/refresh锁 | tokens只在server | 等Admin确切DTO与capability，不局部接入 |

### 设计评审与补充约束

| 发现/要求 | 责任与调整 | gate |
| --- | --- | --- |
| 用户要求DTO/ORM设计 | Admin Request/ResponseDTO→domain service→typed repository→Drizzle ORM；Dream严格Pydantic只消费DTO，保留公开Dream响应 | 禁止database函数RPC/PostgresRow/表列投影；逐入口映射DTO/API/Repository |
| 密码/注册能力保留 | Dream保留已有产品流程，Admin迁密码哈希/既有PK并恢复OAuth上下文 | 认证owner迁移不删除密码登录/注册，不保留Dream自签JWT |
| 独立服务身份与后台scope | Admin client registry；Dream显式service client ID/credential两头，用户Bearer分开 | 每client backgroundScopes闭集，不使用全权shared secret |
| BA subject不同于users.id | principal canonical_user_id十进制string；Dream只用Admin映射，不猜sub | subject/user/active/实体检查与billing一致 |
| 300s token与长turn | Admin thread/run/service/client/scopes绑定opaque delegation，renew只基于已有委托并检查账号/owned entities | 未定义DTO前不让turn依赖短用户token持久化，不能丢SSE事件或改lease/cancel |
| browser handle无Dream DB | Admin encrypted browser store，exchange transaction同client/input绑定并支持原transaction恢复 | resolve并发refresh/unknown结果只能同handle恢复 |
| 原UOW explicit commit | Admin aggregate单事务保持锁/CAS/回滚，Dream无remote逐statement transaction | 159事务候选图逐项闭合 |

## 阶段 3：浏览器BFF登录事务边界

### Optimized Prompt

依据已冻结的Admin browser-session DTO和主拓扑，在Dream Next现有App Router中准备可复用BFF登录事务/CSRF边界，先实现纯server-owned配置、受限return_to、AES-GCM短期HttpOnly事务cookie、PKCE/state/nonce与handle CSRF校验。读取Next现有Claude Agent streaming proxy并复用其cache-free/abort流语义，后续接入时不重写SSE parser/EventBus。新模块只在API私有server目录，不增加第二Web根或依赖；native Node crypto负责AES-GCM/HMAC/random/S256，token不存Browser或URL。

配置必须显式Dream public origin与独立cookie secret；HTTPS或exactloopbackHTTP，无部署名称/test fallback/固定secret，cookie名/path/samesite按统一实现定义并文档化。return_to防scheme/双slash/反斜线/控制/编码绕过；callback对state/iss/redirect/PKCE及事务expiry做确定性判断。Admin exchange成功才关闭cookie；未知结果允许保留同transaction恢复，不能新建请求或再盲兑外部code。写操作检查exactOrigin+绑定handle的CSRF；缺handle/错误CSRF failclosed。

生产start/callback/proxy、AuthContext密码/注册/Google产品和Voice接入须等Admin实际password/OAuth注册/长turn委托能力，当前只完成server边界基础，不局部开启旧token绕过。同步文件头/目录/设计与README阶段事实。测试用nativeNode注入明确配置/clock，以实际函数验证expiry/tamper/PKCE/state/return/Origin/CSRF；交Luna有界运行，无真实Google/账户/服务/网络/browser下载。阶段结束不完成全goal，后续继续逐领域DTO/ORM迁移。

## 阶段 4：生产资源策略与诊断领域接口

### Optimized Prompt

将 `agent_factory` 的资源策略读取和后台诊断发布依赖切到单一 Admin HTTP client。Admin 的确切领域输入输出、操作 capability 的 input/output 版本及 contract SHA256 必须来自其实际 DTO/注册实现；发现 envelope 或回执缺口先协调修正，不制造临时远程 SQL 或不同版本的 API。Dream strict Pydantic 区分 configured/not_configured/invalid；读取失败、缺 capability 或响应漂移为 unavailable。provider 继续验证原 admission/effort parser，refresher 的 revision/LKG/取消和后台异常规则原样保留；不能在 turn 内查 Admin 或 PG。

observer 保留 capacity-one 最新队列、单 worker、timeout 后等待旧调用结束和安全计数器。Admin 拥有 DB clock、statement timeout、TTL 与事务回执；Dream 只发送闭集 diagnostics DTO 和 server-owned instance identity。未知写结果保留原 request_id，恢复只查原回执，不盲重发，也不让未解决旧写被后续 snapshot 覆盖。只在 Admin 实际 capability 就绪后注册该写入口。

同步生产文件头、目录合同、当前 Claude Agent 架构、认证交互设计及执行数量。Luna 验证实际 provider/client/refresher/sink 的已配置、未配置、非法、权限与 capability/网络失败、higher/same/rollback revision、精确数值、timeout/队列排序和原回执恢复；不使用 PG、真实模型或用户服务。最后报告已替换生产方法与仍未替换清单，不把两个后台入口当全域完成。

### 测试前影响表

| 流程 | 执行模块 | 权限与输入输出 | 正常流程 | 失败反馈与恢复 |
| --- | --- | --- | --- | --- |
| desired 读取 | AdminResourceData / ResourcePolicyProvider | service resource-policy:read；严格状态/desired DTO | composition root 与后台读取；原 parser 生成 effective 候选 | 网络/响应/capability unavailable 保留 LKG；invalid 明确保留 LKG |
| revision 更新 | 原 ResourcePolicyRefresher | immutable config/effort/revision | 只有更高合法 revision 进入公开 replace | same 异值/回滚 invalid；same 同值只诊断；不影响既有 lease |
| diagnostics 发布 | 原队列/worker + AdminResourceData | service resource-observer:write；content-free snapshot/instance/time | Admin 一次事务写 snapshot/DB clock/TTL/receipt | 队列丢弃计数；timeout 隔离；unknown 只恢复原 request_id |
| Agent turn | 原 Runner/ThreadFactory/service | 已有 immutable policy snapshot | 原 admission/SSE/工具/resume/cancel | 后台同步异常不传播 turn；不引入 Admin 主路径查询 |

### 阶段 4 实现状态

生产已替换领域方法 **2**：`resource_policy.ClaudeAgentResourcePolicyProvider.load`、`resource_postgres_sink.ClaudeAgentResourcePostgresSink._write_sync`；composition root `agent_factory` 移除database import。Admin实际DTO/hash已读取，资源调用缺广告或漂移 fail closed；后台LKG、队列、timeout规则保留。全域baseline清单仍100生产候选/159事务候选，尚未完成其余领域；startup_database仍PG，旧认证/Device/Gateway/tool数据库注入尚未迁移。资源确定性验证Luna已完成：111 passed in 1.54s，exit0；真实DB/模型验收未执行。

## 阶段 5：Admin/Auth server credential 的 Runtime 环境边界

### Optimized Prompt

复用现有SDK env merge和Gateway credential tombstones机制，禁止新增Admin/Auth/BFF服务器秘密通过SDK完整parent-env overlay、用户env或MCP配置进入CLI/Bash/hooks/外部stdio。实际SDK会先继承parent再叠options.env；单纯pop不能删除已有parent秘密，因此在最终merge中为实际保留键生成空值tombstone，服务器os.environ原值保持用于Admin client。精确键来自本轮实际配置：Admin Dream service secret/client registry、BetterAuth secret/token-encryption、Google client secret、BFF cookie secret和现行Dream JWT signing key。技术身份origin/client_id不是秘密，不需限制正常配置。

所有MCP显式env投影同步阻止这些键被extra_env或外部config恢复；不打印value、不写真实token/凭据测试产物。保持现有Notion thread-projected凭据及模型/Gateway行为；旧Gateway全局签发秘密与Editor DATABASE_URL仍是待Admin长期委托/Editor DTO闭合的生产入口，本阶段不能声称完整无凭据Runtime。长期委托只有thread/Run/subject/service/client/scope绑定的opaque token，投影到必要执行模块；不得把全局Admin secret换名后送CLI。

文件头/目录/设计/执行状态同步后，Luna仅验证实际merge/user-overlay/MCP投影中服务器秘密被清空、二次merge不能复活、parent未修改、必要非秘密字段和原Notion/Runtime调优行为不变。无需真实模型/Google/DB，不修改CLAUDE_CODE_TMPDIR协议、SDK/Runtime pins或用户.env。

### 测试前影响表

| 输入路径 | 执行模块 | 处理与结果 | 验证/失败边界 |
| --- | --- | --- | --- |
| parent/.env/options.env | sdk_env 最终 merge | 保留服务器环境；子进程overlay为精确秘密键写空值 | parent仍可用于Admin client，CLI不获得value；重复merge保持 |
| user SDK env | sdk_env user overlay | 原allowlist+再次保护服务器秘密键 | 用户不能覆盖；正常API_TIMEOUT等原优先级保持 |
| stdio MCP explicit env | agent_runner 配置投影 | 禁止恢复同一组服务器秘密值 | 内部/外部config一致；thread绑定的Notion或未来opaque tool token按原所有权透传 |
| 已有PG/Gateway helper | 原生产模块 | 本阶段不伪造新delegation DTO | 清单保留，后续必须替换；不是full credential/no-PG验收 |

### 阶段 5 执行结果

实际final SDK/user merge写精确Admin/Auth服务器秘密空值tombstone，internal/external stdio配置去除同一组键，parent原值和其他字段保持。Luna fresh 187 passed/1 skipped in0.98s exit0；首轮5旧字典断言更新后全部通过。原SDK/Runner/tmp/MCP/输出验证保留；未改变tmp协议或pins。后续继续chat/auth/Runtime委托及全域迁移，不能完成goal。
