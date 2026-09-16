<!-- [Sync] 2026-09-17: record the real model-reservation and Workflow-binding completion gates. -->
<!-- [Sync] 2026-09-17: add the pre-business-change OAuth role and user-domain design audit stage. -->
<!-- [Sync] 2026-09-16: audit final authentication ownership and remove obsolete Dream SessionMiddleware/deployment cookie authority. -->
<!-- [Sync] 2026-09-15: inspect Workspace76 component receipts and prepare registered public Run cancel consumption. -->
<!-- [Sync] 2026-09-15: prepare actual77 fail/envelope types and preserve production launch owner gaps. -->
<!-- [Sync] 2026-09-15: record actual SystemConfig callsites and credential ownership without replacing an unpublished domain. -->
<!-- [Sync] 2026-09-15: distinguish unregistered launch metadata candidates from the frozen72 catalog. -->
<!-- [Sync] 2026-09-15: record shared-file Thread ownership and unchanged schema-gate extraction. -->
<!-- [Sync] 2026-09-15: record public Preflight read adoption and current 72-operation release boundaries. -->
<!-- [Sync] 2026-09-15: retain Runtime/shared-file technical regression and Gateway ownership gaps. -->
<!-- [Sync] 2026-09-15: record complete Admin Deck list modes and remaining SQL source candidates. -->
<!-- [Sync] 2026-09-15: record unregistered Run create/retry and original hidden-source dispatch ordering. -->
<!-- [Sync] 2026-09-15: record Admin-owned Deck detail and unchanged legacy Memory projection. -->
<!-- [Sync] 2026-09-15: index five Admin Deck writes, shared schema gate and closed deletion feedback. -->
<!-- [Sync] 2026-09-15: record Stage24 public Voice implementation and present-fields reuse. -->
<!-- [Sync] 2026-09-15: record Stage23 consumer implementation and independent technical gate. -->
<!-- [Sync] 2026-09-15: record Stage22 RED reproduction and synchronized metadata implementation. -->
<!-- [Input] User delegation, Agent.md, AGENTS.md, baseline 7d38715c, and Admin-owned contracts when published. -->
<!-- [Output] Executable Dream migration plan, dependency gates, and exact evidence inventory. -->
<!-- [Pos] Dream implementation plan; Admin owns authentication, database transactions, and schema contracts. -->
<!-- [Sync] 2026-09-15: record preference consumers and their independent public technical evidence. -->
<!-- [Sync] 2026-09-15: record five public Deck content-version consumers and exact contract gates. -->
<!-- [Sync] 2026-09-15: implement bound Agent Thread/SDK Session consumers and scoped original-receipt recovery. -->
<!-- [Sync] 2026-09-15: implement public Session consumers while retaining separate background authorization gates. -->
<!-- [Sync] 2026-09-15: record atomic user-turn and factory-owned server persistence implementation and technical validation. -->
<!-- [Sync] 2026-09-14: record ten implementation stages and current Auth/Chat/Resource/BFF/Runtime technical evidence. -->

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

### 阶段1初始依赖与执行状态 · 2026-09-14

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

## 阶段 6：Thread/message 严格领域消费端

### Optimized Prompt

读取 Admin 实际 `chatThreadDto.ts`、domain Service/typed Repository 与16操作artifact中的14个chat双向hash，准备显式OAuth/Runtime委托参数的 typed Chat consumer，不做数据库函数RPC、远程row或UOW仿真。DTO闭集覆盖Thread create/get/list/search/delete/bind/voice/title/session和message persist/list/page/detail/latest；canonical用户ID保持十进制string，原微秒ISO字符串验证后原样保留，不经Date或浮点时间戳削精度。所有用户权限/owned entities/CAS/immutable message identity/receipt事务归Admin，Dream保留公开响应和Agent/SSE状态机。

先搜索复用现有Chat final projection validator与DTO；纯validation若仍位于database.py则抽到独立纯模块并由原接口re-export/调用，不复制一套语义、不改变已有程序接口。消息显式identity由原Dream调用边界生成一次，重试/unknown只能原request_id与receipt，不盲重发或生成新entity。用户actor来自Admin principal/目标token，长turn actor来自owned thread/Run/scopes delegation，不能用user_id header/body或全局token。缺实际grant/profile/API capability时typed消费者先保持显式依赖，不让生产turn依赖300s旧access token。

完整OAuth request binding与runtime/tool delegation就绪后，一次性改生产router/service及间接调用入口，并移除对应SQL函数生产依赖；迁移期间不实现environment标签分支或双数据库行为。Luna确定性检查exact DTO/hash/role/JSON/nullable微秒时间/Owner absence/metadata错误/CAS409/原receipt及final projection matrix，原baseline validator缺口测试继续调用同一生产函数。文件头/目录/当前设计/执行方法数量同步；阶段完成不等于全域goal完成。

### 测试前影响表

| 流程 | 模块/权限 | 正常规则 | 失败/恢复 |
| --- | --- | --- | --- |
| Thread CRUD/provenance | Admin domain+typed Chat consumer；dream read/write OAuth | 既有owned user/thread/Deck/Voice、bind-once/CAS | 不存在/权限拒绝不猜actor；runtime grant不可create/list/delete/provenance |
| immutable message | Admin persist+receipt，显式message identity | 相同JSON语义精确replay、原Thread顺序保持 | 异值409不覆盖；unknown原request_id receipt |
| history/page/detail | strict DTO保留原微秒ISO与nullable | keyset before排序/NULL时间/有无process按既有响应 | metadata损坏显式decode_error；无DB row或正文日志 |
| 生产actor接入 | request/turn composition；Admin principal/delegation | 原PK映射与owned Run/thread、短用户token与长turn授权分离 | DTO/grant/profile/capability缺口fail closed，不能局部用旧签发路径冒充完成 |

### 阶段 6 准备状态

14个exact DTO与真实artifact hash、显式actor/request_id typed Chat consumer已落盘；原final-history validator抽纯模块，database私有alias保持同一函数。评审核对Admin process-detail的fullMessageFields不含projection_version，原行为已保留process；协调仅补显式canonical/final decoder模式与缺口测试，wire/hash未改变，不算现行生产缺陷。资源desired response的effort字段按Admin output JSONschema改为required nullable，legacy输入由Admin输出fixture显式补null，不改变原parser语义。此阶段生产chat入口未切换，实际replacement计数保持2；确定性验证交Luna后继续auth/Runtime actor composition。

Luna fresh：四个有界测试文件 `test_admin_chat_data.py`、`test_chat_message_identity_cas.py`、`test_admin_resource_data.py`、`test_claude_agent_resource_policy.py`，`80 passed in 0.83s` exit0；`git diff --check` exit0。首轮5个同因失败已修复Pydantic bound validator wrapper，14个实际Admin hash只读比对全部一致；未访问PG/模型/网络/用户服务。

## 阶段 7：Admin 当前用户资料与请求认证

### Optimized Prompt

以实际 Admin 第17个 `user-profile.current` 闭集 DTO、双向摘要和现有 principal/JWT verifier 为依据，准备唯一请求认证 owner。复用现有 transport，不新增签发、数据库函数代理、部署名称分支或缓存用户 active 状态。服务器先验证 Admin ES256 token 和按 HTTP 读写需要的 dream scope，再取 Admin principal 并比对 subject、client_id 和完整 scopes；只有 Admin 映射的 canonical_user_id 可投影为既有 Python user_id。当前用户资料通过严格 profile DTO 读取并比对同一 ID，保留 Dream `/api/me` 原字段与时间字符串，不猜 email 或 role，不在 Browser 返回 access token。

请求 actor 为不可变、凭证 repr 隐藏的 server-owned 对象，显式保存在请求 state 和既有 current-user 投影中供领域迁移使用；不能在 sync FastAPI dependency 的工作线程设置 ContextVar 后假设传播到 Agent 后台。实际 HTTP I/O 从 async dependency 通过已有 threadpool 执行，不阻塞 event loop。composition root 拥有单一 client/verifier，capability 初始化有锁并 fail closed，应用关闭时释放自有 HTTP 连接；测试只注入 owner，不复制 auth 入口。

分批准备不能称为产品开启：共享依赖、文件例外依赖与旧 OAuth/Device/password 签发入口的最终切换必须同 BFF session/产品入口和长 turn/tool delegation 一并闭合。Admin profile 仅 OAuth，runtime grant 不读取完整资料。长期委托保持 owned Thread/Run 与实际 scope 绑定；短期用户 token 不成为后台 Agent 持久化凭据。保留 original public response/文件权限/SSE/lease/tmp 行为，同步 headers、目录、设计与影响表。Luna 只做 provider-free DTO/principal/profile mismatch、scope、无 cookie/query fallback、安全错误和原公开投影测试；没有真实 DB/model/browser 验收时保持明确 pending。

### 测试前影响表

| 流程 | owner 与输入输出 | 正常流程 | 失败反馈与恢复 |
| --- | --- | --- | --- |
| 当前用户资料 | typed profile consumer；OAuth dream:read | 空 input，只读调用主体，严格 decimal/null/time/provider DTO | missing capability/漂移/拒绝 fail closed，不以 JWT 猜 profile |
| 请求身份 | Admin request-auth composition；Bearer + HTTP method | verifier scope → principal claim equality → canonical ID → immutable actor | token 401、scope 403、依赖 503；无 cookie/query/旧 HS256 fallback |
| `/api/me` 原公开投影 | profile 与 principal 同 ID | id/email/display_name/avatar_url/role/created_at 保持 | ID 异常作为无效上游响应，不读取 Dream PG |
| Agent 后台 | 后续 owned runtime delegation | request actor 仅用于创建委托；后台使用长 turn token | grant/Run/tool 合同缺口保持 pending，不泄漏全局密钥或改事件语义 |

阶段7有界技术回执：`test_admin_request_auth.py` 的21个实际 DTO/owner/FastAPI dependency 用例，`21 passed in 0.24s` exit0；`git diff --check` exit0。第17项profile capability与实际Admin artifact逐字段一致，hash `01011316efa10475dd1d1aa8856c82cb17ddbeb404125ebcd80af5f250f2a9d0`。没有PG/网络/模型/用户服务调用，prepared dependency尚未切换所有生产入口。

后续实际接入回执：共享 `get_current_user`、storage/workspace dependency、`/api/me`和`/auth/me`已切换Admin；Chat router消费11/14操作（CRUD/search/owned get/bind/select/message list/page/detail/latest），persist/title/session后台委托未接。Luna公开HTTP+request-auth两文件 `38 passed in 0.92s` exit0，`git diff --check` exit0。真实router/DTO/transport与显式fake auth/runtime provider，Dream PG被封住；并非全域或真实模型验收。router剩余DB：model selection callback和stream的system config、Deck context get_db、initial save_chat_message。

## 阶段 8：实际浏览器 BFF 与生产请求切换

### Optimized Prompt

复用现有 Next private login boundary、native crypto、zod/http fetch 和 Claude streaming proxy，实现实际 `/auth/start`、注册的callback、`/auth/session`、`/auth/logout` 及通用同源API BFF。Admin是密码/注册/Google唯一认证owner，Dream入口启动同一code/PKCE流程并保留relative return。server transport限定已配置Admin origin/issuer/resource、独立service身份、无redirect/retry、有界响应与安全错误；strict principal/handle/profile/capability来自实际第17项artifact。callback保留同transaction进行未知兑换恢复，成功后才清理transaction cookie，不把OAuth token放Browser或URL。

API proxy每次解析opaque host-only handle，所有写入验证exact Origin和handle-bound CSRF，移除Browser Authorization/cookie/用户身份和服务凭据头，再注入Admin已解析token。保留现有request abort、SSE body流、headers和cache/no-buffer语义，不能复制parser/EventBus或改turn/resume/cancel。文件GET使用同源cookie，删除旧storage token query行为，保留路径/owner检查。当前 `/ws/speech-recognition` 按发布设计固定关闭1008，不启用ASR、不制造WS handshake新业务。

公开API支持Browser handle与Device/native OAuth Bearer两种协议凭据：handle cookie一旦存在（含空值/重复/非法值），只走handle解析，写入必须Origin/CSRF，不能fallback到附带Bearer；没有handle cookie时仅接受显式Bearer，并移除全部Cookie/服务/actor覆盖头，由Python唯一Resource Server验证Admin ES256/principal。两种请求都校验目标public origin，Origin头存在时必须exact match。无ambient cookie的Bearer写不需要Browser CSRF。URL中token/access_token一律拒绝，Browser只用同源cookie。这是凭据协议选择，不按部署环境分业务路径。

Browser auth state只读公开user+CSRF，用同源REST/SSE/XHR与中央header helper逐调用点迁移，移除localStorage OAuth/fragment adoption/sliding renewal。既有token标识符不可换成无权限marker来冒充登录，不保留自签JWT/旧cookie/queryfallback。生产dependency只验证Admin bearer/principal，`/api/me`只读取typed profile。长turn三类凭据分别为server持久化、CLI Gateway、exactEditorSession stdio；不能把wide或全局service/DB key投到CLI。只有实际grant/tool/Workflow resolve合同接好后才统一开启生产流程，候选源码不部署。

Luna按有界公开handler注入transport验证start/PKCE/callback/tamper/origin/CSRF/capability/DTO、同transaction恢复、session无token、stream abort、HTTP header隔离；当前用户和文件请求保持公开DTO。随后实际frontend typecheck/build、production closure静态扫描和授权本机业务验收，逐入口记关闭证据；缺全域Admin API/模型/正常服务回执时继续active，不停在typedDTO准备。同步受影响folder/file headers/现行设计和中英README，不覆盖同步过来的原仓库dirty文档。

### 测试前影响表

| 流程 | 执行owner与权限 | 正常流程 | 失败与恢复 |
| --- | --- | --- | --- |
| Login/Google/register | Dream start/callback + Admin Better Auth UI | state/PKCE/exactissuer → Admin handle → 同源relative return | tamper/expiry/state拒绝；unknown保留原transaction，不盲再兑code |
| Browser session/profile | Dream BFF + Admin resolve/profile | 只返user与CSRF，tokens只在server | missing handle401、依赖503、profile/principal ID异常fail closed |
| REST/SSE/XHR写 | 同源BFF与Admin bearer | exact Origin/CSRF → body保持 → server bearer代理 | browser身份头被移除；网络安全502，无盲重写请求 |
| 图片与文件GET | 同源handle + 现有storage/workspace owner/path | Browser无query token，文件结果与权限保持 | 无handle401；路径/owner错误保持 |
| 后台turn与工具 | 分开的owned server/Gateway/Editor grant | expiry前受控renew，CLI无server/DB key | 不用300s access token替代long turn；Workflow完整activation检查迁Admin |

### BFF 与错误边界实现回执

实际BFF start/callback/session/logout与generic REST/SSE代理已实现，旧rewrite停用。原SSE transport抽为共享模块，body/abort不缓冲。Luna runtime `22 pass, 0 fail` exit0（首轮loopback EPERM是harness前置失败，允许测试自有server后重跑通过）；初次tsc exit2仅4项fake env类型要求NODE_ENV，配置输入改为只读键值集合，fresh tsc待回执。`pnpm install --frozen-lockfile --ignore-scripts --store-dir /private/tmp/dream-admin-data-pnpm-store` exit0，复用当前lock exact版本，package/lock无改动；offline首轮缺tarball不是产品失败。

Admin新增唯一error details为DECK_VERSION_CONFLICT的strict `{current_draft_revision: nonnegative safeint, current_version: nonnegative safeint|null}`。Pythontransport只保留该DTO，其它code/extra/null/bool/越界fail closed，不保留上游message。后续Deck version adapter恢复原公开409这两项字段；当前仅shared error consumer接入，不计Deck生产迁移关闭。

Fresh `pnpm exec tsc --noEmit --incremental false` exit0，无输出；`git diff --check` exit0。当前只代表已接入BFF源码与现有frontend类型门槛，不代表Browser全调用点、build或真实业务验收完成。

## 阶段 9：Browser session 状态与全部请求头切换

### Optimized Prompt

依据Admin实际UI（唯一authorize进入Admin sign-in，同页password/signup/Google并保留signed OAuth context，无自定义register/Google参数），Dream用一个登录/注册入口启动既有PKCE BFF。复用现有登录卡片的样式与产品主导航，不让Dream重复收集密码。AuthContext从同源`/auth/session`读取闭集公开profile+CSRF，用户ID保持decimal string；只有服务返回有效session才设置认证状态，不把CSRF当OAuth token或把任意marker放Bearer。logout等待Admin成功撤销后清状态，失败保留会话并展示安全反馈，不增加确认弹窗。

新增单一纯Browser session/header owner保存内存CSRF并生成同源请求头，逐个修改API、hooks、Chat/SSE/XHR、Workspace/文件与MCP Apps调用点，禁止OAuth localStorage/fragment adoption、sliding renewal和URL token。原可注入测试token选项改为显式csrfToken或headers配置并同步技术fixtures，不新增生产test fallback。API base固定同源；当前speech WS仍关闭1008且不启用。文件URL保留key/path/查询业务参数，去除历史token并归当前origin，不改变文件权限/读写。Node Apps显式adapter先用同一BFF apiAuthorization，再向现有Runtime传server-resolved Bearer，保留既有session cleanup/policy/transport行为。

同步受影响文件headers/folder/current auth设计。Luna做实际纯session/header/URL与public BFF确定性验证、完整frontend typecheck/build和必要受影响journey；保留已通过22BFF/38public Chat回执，无新变化不重复SDK全套。所有旧OAuth storage/nativeBearer调用点必须静态复核，真实Admin/Google/model尚未验收保持active。

### 测试前影响表

| 流程 | owner/输入输出 | 正常 | 失败/恢复 |
| --- | --- | --- | --- |
| Browser登录/注册 | Dream入口→Admin password/signup/Google UI→BFF | 原relative return，session只返profile/CSRF | 未配置或Admin unavailable安全反馈，不签发本地token |
| Browser session | 同源session DTO/React state | exactdecimal user/微秒字符串，CSRF只存内存 | 401清状态，其余失败不伪造登录，允许重试 |
| REST/SSE/XHR | 单一Browser header owner | Cookie由Browser携带，写CSRF，body/abort保留 | 无OAuth header/query；Backend依旧权限判断 |
| logout | BFF+Admin revoke | committed才清cookie/state | failed revoke保留session并提示，不本地假成功 |
| Files/Apps | 同源URL/Node受控Beareradapter | 原FS path/session/policy/cleanup | token移除，invalid handle无Bearer fallback，不改变Node上游权限 |

阶段9首轮Node28通过，1项原生Node extensionless apiBase import失败已补`.ts`；loopback EPERM仍是测试server harness前置失败，允许自有server后SSE回归通过。tsc首轮2项同因：resourceConnectorApi改headers后遗漏中央helper import，已补。fresh focused URL/typecheck待回执。静态生产Browser扫描：getAuthToken调用0、AUTH_TOKEN localStorage读取0（仅删除legacy键）、Authorization Bearer写0、options.token残留0。此盘点不代表后台Runtime/全域SQL关闭。

阶段9fresh gate：`node --test app/_dream/lib/toFileProxyUrl.test.ts` 2 passed/0 failed exit0；`pnpm exec tsc --noEmit --incremental false` exit0；`NODE_ENV=production pnpm exec next build` exit0，Turbopack compiled successfully、TypeScript completed、静态页面生成完成，包含auth/session/me与Claude/generic API routes。28项已通过runtime加2项focused file URL共30通过；不是同一命令一次30项回执。`git diff --check` exit0，构建产物保留worktree，不访问业务数据。

Chat主stream初始user-message reserve新增actual typed persist（OAuth request，beforeSSE），router使用12/14操作；原public message ID与409反馈保留，unknown不重试。后台title/session/assistant与Dream confirmation guard仍需分别接独立server委托/typed Workflow领域，尚未计关闭。补真实public route/provider-free initial reserve和conflict-before-runtime回归，fresh待回执。

## 阶段 10：Runtime purpose 委托与独立 HTTP consumer

### Optimized Prompt

读取Admin实际delegation create/renew/revoke/原请求receipt DTO与三项identity capability，复用现有有界HTTP解析、错误安全投影和原request_id规则。将transport共有部分抽为不持有认证配置的函数，internal consumer显式注入独立service身份；public Runtime consumer仅注入exact idg Bearer，不接受Cookie、Admin/Auth/DB/Gateway全局key。保持原超时、大小界限、无redirect/retry、write unknown语义及现有resource/Chat/profile接口。创建由server owner用用户OAuth与service身份调用独立Admin入口，先验证实际schema capability，输出purpose、thread/run/EditorSession/scopes必须逐项等于申请值；expiry与maximum保持合法次序。三类scope不可互换，Editor必须精确session，server凭据不得进入CLI。

用原动作ID查询public receipt并验证operation/request/entity/result，absent保持未知状态、不新建动作或续期。建立server keeper在到期前续期，同token/entity/purpose/scopes/maximum必须保持，失败保存pending原ID并先读取receipt，最大寿命到期fail closed；不改admission/lease/Runner/SSE/cancel，不在turn主路径查询PG。Keeper只改变授权可用性，真实CLI/Editor投影与后台写接入分别记录关闭证据；Workflow完整activation/confirmation guard未接入时保留原生产保护。候选schema尚未发布与route proof未通过，不把consumer源码称为可部署完整Runtime。

先做Python真实consumer的注入HTTP技术验证（无PG/model），再复用Luna运行受影响resource/Chat/auth测试与docs路径检查。同步文件headers、admin_data/backend folder与现行设计；继续全域SQL/旧issuer迁移，不在adapter准备后标记目标完成。

| 流程 | 执行模块与输入输出 | 正常 | 失败与恢复 |
| --- | --- | --- | --- |
| Create | server→Admin独立create；OAuth+service→三类exact grant | published capability与scope/entity匹配后持有opaque token | missing/invalid capability或响应拒绝；unknown保留原ID |
| Renew/revoke | public HTTP consumer仅idg与request_id | 返回同entity/purpose/scopes/maximum，续期前到期 | timeout先原ID receipt；absent不盲重试 |
| Keeper | server后台clock与immutable grant | 到期前renew，成功替换expiry | pending原ID恢复；maximum不延长，失败不传播Agent turn |
| CLI/Editor | 后续各自最小purpose投影 | 无server/DB key，Editor exact Session | scope不可扩展；缺授权拒绝，不回退旧key |

阶段10fresh technical gate：Python purpose/shared boundary/Chat adapter/public Chat/requestAuth/resource六文件集合 `193 passed in 1.29s` exit0；`node --test app/api/_auth/handlers.test.ts` 8 pass/0 fail exit0；`pnpm exec tsc --noEmit --incremental false` exit0；显式无webServer/browser的config `pnpm exec playwright test --config=/private/tmp/dream-admin-config-validation.mjs` 7 passed/512ms exit0。Docs checker40files/180local links/历史原文SHA与README结构一致/6sequence块/failures0，diff check0。实际create候选已按Admin非空text ID更新为61186...，不接受旧hashfallback；required auth.delegations四descriptor与三schema逐项匹配。仍未将keeper接入生产Agent lifecycle，也未用技术HTTP fixture冒充正常Admin业务回执。

## 阶段 11：退役 Dream 旧签发与刷新入口

### Optimized Prompt

协调合同明确没有旧Dream POST本地token返回兼容或native密码转发要求。先列出现有外部协议依赖：routers/oauth.py的Authlib仅执行Google账号登入并签发Dream HMAC，routers/device_oauth.py的Authlib仅执行Dream Device/refresh；它们必须退役。Managed MCP仍由标准mcp.client.auth OAuthClientProvider/TokenStorage执行外部MCP server授权/refresh，不能删除、替换或放宽；Notion connector当前credential/login流程保持。两个明确命名的维护/验收脚本仍调用旧auth.create_access_token，它们不算生产路由关闭，后续改为显式Admin OAuth凭据，禁止给正常用户继续返回已被Resource Server拒绝的HMAC。

保留/api/register、/api/login、/oauth/google/login/callback、/oauth/device/code/verify GET/POST、/oauth/token、/auth/logout原路径，统一明确410迁移DTO。根据server-owned已验证Admin origin/issuer/resource生成标准authorize/token/device/code/revoke/JWKS/verification端点与resource信息，不依据用户请求Host/query/credential控制目标，不转发密码、code、refresh或cookie，不读业务数据库、不读取Google/Admin secrets。未配置合法Admin公开authority时返回安全503且不猜host。BFF /auth/logout继续执行已实现的handle revoke；Python旧Cookie/user-wide refresh logout返回410，不能假装已撤销Admin会话。保留typed/api/me、/auth/me和独立import-local-data/mark-first-login业务。

提取单一退役响应owner，薄路由不解析敏感body、不启动Authlib/OAuth/DB，也不新增HTTP转发或第二issuer。保留旧导入的request/response DTO标识符供接口历史引用，移除旧runtime authority实现后同步受影响headers/folder/README/现行Auth架构与调用链inventory。Luna通过公开FastAPI路径以synthetic敏感body和封住DB/HTTP的fixture验证全部410、无cookies/token/header/secret、configured endpoints精确、invalid/missing authority503、typedme仍运行；不用隔离fixture冒充本机真实OAuth/model验收。

| 流程 | 执行owner/输入输出 | 正常 | 失败与恢复 |
| --- | --- | --- | --- |
| Old password/Google/Device/token | Dream退役owner，忽略原body/query/credential | 410标准Admin authority信息，不签token | 缺合法authority503，禁止猜测或转发敏感数据 |
| Browser login/logout | 既有Next BFF/独立Admin owner | PKCE与handle revoke保持 | revoke失败保留cookie/session |
| 外部MCP OAuth | 标准MCP SDK与现有credential repo | 外部协议与加密token合同保持 | 本阶段不改变refresh/权限/取消 |
| Current profile/import | typedme与原独立数据业务 | canonical/profile字段保持 | 未迁移导入DB不计全域关闭 |

阶段11 Python fresh gate：public retired auth/registration/request profile三文件 `46 passed in 0.64s` exit0；仍使用fake repository/cipher/discovery的MCP SDK外部OAuth `5 passed in 0.19s` exit0，原协议保留。docs19files/179links/166inventory/历史原文SHA与README结构/6sequence块0fail，diff0。接着补Next实际旧同路径薄adapter，静态login/register在generic proxy前直接返回410；不让旧请求先被401遮住迁移反馈。Next/currentauthority parser只读三项公开配置，不要求或读取private service凭据。fresh Node/type/build待回执。

阶段11 Next fresh gate：`node --test app/api/_auth/retired-auth.test.ts app/api/_auth/handlers.test.ts app/api/_auth/login-boundary.test.ts` 27 pass/0 fail exit0；`pnpm exec tsc --noEmit --incremental false` exit0；`NODE_ENV=production pnpm exec next build` exit0，包含static/api/login/register/oauth/auth新路径，编译/类型/静态页面/优化完成。docs30files/179links/212concrete folder entries/history SHA/README parity/6sequence blocks0fail，diff0。保留本轮worktree构建产物，不访问正常数据库/模型/外部服务。

## 阶段 12：关闭旧 standalone authority 与脚本自签

### Optimized Prompt

九条Python与八条Next旧HTTP方法已退役，继续关闭可调用的backend/auth.py旧密码/HS256/refresh/sliding authority。保留已有helper标识符供历史import与fixture，签发/密码校验接口明确抛安全retired exception，旧token验证/renewal仅拒绝；保留无authority的duration/sha256/header纯函数。不读取JWT/refresh secret、无默认key、不import bcrypt或jwt签发库，不引入另一个issuer或凭body猜principal。真正认证仍唯一Admin JWT verifier+freshprincipal+BFF。

将import_diaries Agent标注改为必须显式--api-token/已配置secret中的Admin OAuth，去掉DB邮箱查询后自签与相关auth import；CLI/env参数内容不得打印。真实Gateway verifier必须显式现有email与AdminOAuth secret，无固定codex影子账户默认；在任何数据库/网络/模型调用前拒绝缺失凭据，保留已有显式model contract优先检查。其余校验/正文parser/计费流程不借本阶段重写，标注旧Gatewaysubject helper路径另待purpose迁移。未运行脚本，不能报正常模型验收。

源码没有其它Authlib/bcrypt使用时，从pyproject移除这两项仅属于旧authority的依赖；先offline更新uv.lock/export requirements，保持所有剩余resolved版本与SDK/Runtime/project pins不变。manifest/lock/export原子同步；不修改用户venv、不重装SDK/浏览器、不用部署环境名切行为。同步backend/script/test headers/folder、README与现行Auth设计，保留3份历史原文。

Luna运行真实retired helper/公开Auth/router/JWT boundary合同、现有verification纯合同（no script main realaction）、缺secret-before-I/O回归、lock/export一致与docsinventory检查。所有真实DB/model/用户数据保持未触碰；全域数据库与Agent grant接线继续active。

阶段12 fresh技术回执：六文件集合 `101 passed in 0.78s` exit0；tomllib/requirements比较exit0，仅authlib/bcrypt移除，无新增包，其余版本/制品URL/hash/size保持；`uv lock --check --offline` exit0（隔离cache，仅resolver无install）。docs19files/179links/148folderentries/历史原文SHA/README结构/6sequence块0fail，diff0。两个script真实main未执行，PG/model/正常账户未触碰；后续Workflow/grant/全域DB继续active。

## 阶段 13：Admin Workflow 上下文与公开 Chat 接线

### Optimized Prompt · 2026-09-15

消费实际workflowContextDto/Handler/Service与operation artifact，不复制Admin retry图/来源hash/数据库规则。唯一input thread_id，保留原StoryWorkspaceDreamRunContext十字段的非空/255/Run格式/正安全整数边界，strict required nullable agent_id，不用客户端传入的Run/Deck/actor作为上下文。Admin返回null明确普通Chat或经过完整校验的terminal leaf；409/权限/缺capability fail closed。Runtime create readiness增加已发布0033 dream.schema.unified.v1 exact digest，不能只匹配三项identity capabilities。

公开Chat在已有Deck/Voice绑定后、初始message预留和SSE前读取Admin上下文，通过不可变服务器snapshot注入内部RunRequest；公开DTO不暴露该字段，service精确检查actor/thread后使用snapshot，不再对该公开入口调用旧PG mapper。内部持久化confirmation/launch dispatch仍保留原guard/mapper直到对应typed command和服务身份合同接好，不给缺scope/过期OAuth新增fallback。原admission比较、lease、EventBus、Runner、resume/cancel和SSE unchanged，后台long-turn grant生命周期另接，不能将snapshot准备称为完整Runtime迁移。

同步涉及headers/folder/设计与README，Luna验证actual typed HTTP、真实公开Chat路由、null/十字段/actor-thread错配/required nullable/技术数值、capability drift和读失败-before-message/SSE。Provider-free无PG/model/用户服务。长turn三purpose、Editor/Gateway/其余域继续执行，目标保持active。

阶段13 fresh技术回执：新Workflow consumer、公开Chat、requestAuth、delegation、data boundary、Chat/resource与原Service八文件 `251 passed in 1.38s` exit0；实际Workflow hash与canonical artifact匹配，四Runtime special hashes和create/discovery四项schema逐项匹配，非旧三schema checker。docs20files/179links/187folderentries/历史原文SHA/README结构/6sequence块0fail；tracked diff check0，新Python no-index仅预期内容差异exit1且无whitespace错误。无PG/model/账户/网络/SDK进程，内部dispatch/full-domain未迁移。

## 阶段 14：原子 user-turn 与服务器持久化委托

### Optimized Prompt · 2026-09-15

Admin已提供actual chat-user-message.persist（hash2c5b20900ef867a237613e49a89b4073f4c0c89cd1d2161962f7132084696c37）：严格thread/message IDs、parts_json rawarray、metadata_json required nullable rawobject、title_candidate string；返回message_id与confirmation_preserved。Dream复用原extract_text_from_parts生成未截断candidate，Python json.dumps保留负零/float/bigint词法，禁NaN/非JSON；Admin唯一事务执行ownedThread锁、原storedconfirmationguard、rawmessage+仅缺title填充，不在Dream重写guard或模拟UOW。

公开入口在已验证Workflow snapshot后创建最小server-persistence idg（dream read/write、exactthread/authoritativeRun、无EditorSession/Gatewayscope），credential只留server。使用独立server holder将已知原子预留交给Service，Service重复已确认同一输入不重发；未知提交保留原requestID，后续只能查原receipt，absent禁止新写/推理。先保持所有尚未接好typed的内部dispatch原guard，不能旧lease回写覆盖当前controlmetadata。接上有界grant后台renew、expiry/max failclosed与factory生命周期自有cleanup；不因SSE disconnect停止后台turn，不改变admission比较、lease、resume/cancel/EventBus/Runner。

Keeper current只能读短锁snapshot，HTTP renewal不持有hotpath锁；offturn错误仍只记safe diagnostics。Gateway/Editor各purpose后续独立接线，不把本阶段server idg投给CLI或替代wide/globalkey。验证 actual DTO/公开route/Service与clock/fakeProvider，没有PG/model/真实用户服务；保留SSE原实现。同步headers/folder/现行设计和证据，整体数据库/认证目标仍active。

阶段14技术回执：十文件初轮 `325 passed, 1 failed in 1.58s` exit1，唯一新测试错误预期timeout503；实际transport既有`ADMIN_TIMEOUT/504`，原Chat参数测试也按504。仅更正新预期并增加exacterror code，不改transport、unknown/单POST/noRuntime/脱敏断言。fresh三受影响文件 `49 passed in 0.87s` exit0，无skip；其余277测试初轮通过且源码未再改。实际atomicuser/Workflow canonical DTO/hash及Runtime四special hash、create/discovery四schema与renew/revoke/receipt三schema全部比较exit0。docs20files/181links/191inventory/history3SHA/README结构/6sequence计数0fail，未render；tracked diff check0。无PG/model/账户/网络/用户服务，完整后台/CLI/Editor/数据库仍active。

## 阶段 15：公开 Session 与复用 Editor 状态 DTO

### Optimized Prompt · 2026-09-15

读取Admin实际editorSessionDto/Service/Repository/Handler与已通过受限public103合同的八operation artifact。复用既有StrictDTO、EntityId、精确ISO时间校验和统一无retry transport，新增闭集EditorEngine cell/commentor/task/weight/state DTO供Session与后续Editor stdio共用；optional字段在wire省略，required nullable保持null，finite JSON值/当前state ID/writingThread归属依Admin合同failclosed。不新增任意业务限额、表列CRUD、remoteUOW或Dream SQL。

将公开/api/sessions save/get/batch/list/range/text-list/delete全部改typed Admin consumer，显式request actor token，保留原name/labels null保留语义、UTC范围、排序、微秒ISO、date_key时区和mixed-word metrics。list除去内部text:null，batch空列表不发数据请求，get missing原404，delete幂等success，update/delete SSE只在confirmed command之后publish；unknown保留原request ID/error且不发event/不retry。复用Chat现有authenticated threadpool/error调用规则为共同router helper，不复制另一套权限/parser/SSE。正常Browser/公开DTO不展示技术实现。

只迁移实际可授权入口；当前Session Handler不接受Thread server-persistence grant，后台ContextBuilder/Session工具保留清单依赖，不能假造Editor或宽purpose来读所有Session。后续stdio仅exact existing Session editor-stdio idg，去除DATABASE_URL另阶段处理。同步nearest folder/file headers、中英README、现行设计与技术回执，测试走实际FastAPI入口/DTO、MockTransport/公开生产dependency、DB fenced，无PG/model/真实账户/服务，不改部署环境行为或pins。

阶段15实现状态：six exact Session hashes已与实际48-op artifact逐项比较匹配；公开Session router无database import/call，统一helper直接复用原Chat actor/threadpool/safe error规则。原calendar/event回归已接actual公开FastAPI/auth/DTO，native datetime单独保留helper regression。新增闭集Editor状态、optional/null/finite/identity、metrics及confirmed/unknown edit events测试，Luna gate进行中；后台Session工具/Editor/全域仍未关闭。

阶段15 fresh技术回执：指定八文件 `190 passed in 1.20s` exit0，无skip/失败。六Session capability/artifact/canonical SHA逐项一致；Editor全部closed字段/optional集合一致，仅selectedState可显式null。Session router AST无DB import/连接/execute/commit/rollback；共享helper的Chat错误语义由同批公开route测试覆盖。docs19files/192links/179inventory/history3SHA/README heading parity/6sequence计数0fail，未render；tracked diff0，新五Python no-index内层exit1仅内容差异，无whitespace错误。无PG/model/network/真实服务/SDKruntime，后台Session/Editor/其他领域继续待迁移。

## 阶段 16：服务器 Thread 读取与 SDK Session 回写

### Optimized Prompt · 2026-09-15

消费已实际验证Chat14中的chat-thread.get/update-session，以既有server-persistence exact Thread/Run grant替换公开turn Service里的Thread resume/binding读取和SDK-native session ID/contract回写；不使用短用户OAuth、不扩大purpose、不传全局secret。复用AdminChatData、strict Thread DTO与immutable Workflow snapshot，保持SDK session identity、resume兼容检查、on_message/cancellation时持久化和Factory/SSE/lease顺序。内部dispatcher尚无对应server identity时保留原入口依赖，不能靠用户ID仿造后台actor。

扩展当前server持久化owner的同一write barrier：任何unknown操作保留原operation/input/request ID，只有同操作同输入可查原receipt，absent或回执失败禁止后续不同写/推理；known user reservation仍复用，不重复POST。新Session回写严格以originalUUID执行，任何网络/响应未知不生成新ID盲重试。当前通用assistant DTO会经过Admin JSON number解析，raw词法与组合事务尚待actual raw assistant合同，因此该入口不得借本阶段假造codec或变更message parts。

同步文件头/目录/现行设计/中英README/当前入口映射，专用runner验证actual DTO/Service/native on_message/cancel/unknown跨操作barrier/原receipt和Factory回归，严格MockTransport/explicitclock/fakeprovider/DBfence，无PG/真实模型/服务/Runtime子进程。Full-domain、Gateway/Editor、正常本机业务验收保持开放。

阶段16实现状态：公开Service Thread resume/repair fallback读取与SDK init/final/repair Session更新接入exact owner，internal absent-owner原路径保持。共享pending记录actual operation/input/UUID；known user缓存不能绕过pending，Session仅最近确认可复用，A→B→A重新写。Thread读取也由Phase4 drain。范围明确：初始user unknown在推理前拒绝；SDK init unknown保持原callback日志/运行turn与cancel，owner随后不同写拒绝，旧assistant/Run DB尚不在该屏障内。actualService/native init/next-turn transcript/cancel、scope mismatch、跨操作receipt与mutable Session技术gate进行中。

阶段16技术回执：首轮指定七pytest文件 `253 passed, 1 failed in 1.58s` exit1，无skip；唯一失败为新cancel测试对NormalizedAgentEvent使用字符串in断言。仅改该断言为actual event.payload exact finish/stop/cancelled+metadata turnId，并补lost Session参数后，fresh两文件 `62 passed in 1.16s` exit0无skip。其余首轮通过文件无源变更，不重复执行。actual Chat get/update-session capability/artifact/canonical SHA一致；server grant boundThread/Run/scopes与public优先typed owner/internal fallback检查exit0。docs19/194links/173inventory/history3SHA/README parity/6sequence0fail（未render），diff check0。无PG/network/model/账户/服务/SDKruntime，未清理并发文件。

## 阶段 17：公开 Deck 内容版本五项消费端

### Optimized Prompt · 2026-09-15

读取Admin实际deckVoiceDto/Service/Repository/Handler与registered57 artifact，消费已public19/246验证的deck-content.state/preview/commit/history/detail五项。复用StrictDTO、Chat安全整数/ISO/canonical identity、统一request actor/threadpool/redacted error transport；Deck版本公开入口不再创建Dream PG service。CAS、snapshot/hash/preview/commit/immutable history事务只由Admin执行；同时要求actual unified/content-versions/canonical-storage三项物理capability，不使用Drizzle最新head。

新增与actual closed v1 snapshot对应的只读DTO，snapshot_json保留原字符串，只校验shape，Dream最终用标准Python JSON decode回原snapshot dict，保持负零/float/bigint，不复制canonicalization/diff/hash算法。公开created_by保留原int、ISO微秒保持、detail保持原flat summary/snapshot响应。缺required nullable/extra/nonfinite/ID错配fail closed，写reply错配unknown。公开409保留closed current_draft_revision/current_version并使用安全固定错误message；提交unknown保留原UUID，不盲retry。原limit/description合同边界保持，不新增产品配额或确认。

仅迁移这五public操作。Deck/Voice其他14操作、default plugin provisioning、refs/voice6以及Runtime消费者、Dream actualartifact_store/CLIcompat证据、internal content-version Service调用继续清单开放，不能用metadatafixture当FS/model验收。更新file headers/nearest folder/README镜像/现行设计/映射；dedicated runner经actualFastAPI/Auth/DTO/MockTransport验证三capability/hash/CAS/409/unknown/numeric snapshot/permissions/ID/微秒且DB fenced，无PG/网络/模型/用户服务/SDKruntime与pins变更。

阶段17实现状态：五actualhash已逐项匹配57artifact；物理requirements除三Deck领域schema外还包含identity，共four exact v1，复用Workflow已有identity/unified pins。public版本router无Dream database/PG Service，引入closed raw v1 snapshot shape，仅decode原响应，不复制hash/CAS。positive safe CAS严格输入、closed409 details/unknown原UUID、creatorint/微秒/selectedDeck-version绑定；共享actor invocation增加可选safe domain error handler，Chat/Session默认语义保持。client catalog fresh失败清空ready，下一共享auth重新载入，补cross-domain profile恢复用例。Luna技术gate进行中，otherDeck14/refs/voice6/FS/Runtime及内部版本Service仍开放。

阶段17技术回执：首轮指定六pytest文件 `176 passed, 3 failed, 1 warning in 2.07s` exit1、无skip；三个失败同源为nested canonical ID validator绑定收到ValidationInfo。改显式classmethod调用原Principal validator，保留校验；新test cookie改client级设置后，fresh两文件 `66 passed in 0.99s` exit0，无skip/failure/warning。其余首轮通过文件无源变更未重跑。five capability/artifact/canonical SHA与four physicalrequirements实际匹配，TS closed fields/required nullable一致，public router AST无DB/_service，consumer无hash/CAS实现，exit0。既有明确命名SQLite fixture仅技术验证。docs24/203links/199inventory/history3SHA/README parity/6sequence0fail，Deck11sequences/交互6仅计数未render；tracked check0、新三文件no-index inner exit1且无输出，仅内容差异无whitespace error。无PG/network/model/用户服务/SDKruntime或pyc/并发清理。

## 阶段 18：公开用户偏好两项消费端

### Optimized Prompt · 2026-09-15

读取Admin实际userPreferencesDto/Service/Repository/Handler与registered60 artifact，消费user-preferences.get/save两项actualhash；Admin公开受限合同尚在独立验证时只以广告+exact identity/unified schema failclosed，不将unit/metadatafixture声称正常业务验收。复用StrictDTO/requirednullable/rawobjecttext/ISO、shared actor/threadpool/safe errors与clientcatalog恢复，无user ID/runtimepurpose。只使用当前OAuth，不允许server-persistence/CLI/Editor grant管理preferences。

公开GET保持未保存{}与voice_configs/state_config原dict、meta_prompt/selected_state/timezone/first_login_completed/微秒时间；POST把五optional公共字段转requirednullable wire，None沿用原COALESCE保留，空对象保存{}，JSON保持Pythonfloat/negativezero/bigint不经JS重编码。拒绝外部actor/firstlogin/systemconfig字段和错误形状，不增加产品配额/默认值/确认；stored config无法投影有效公共JSON时safe failclosed，不修数据库。不改变default-voices本地config端点、SYSTEM config/模型/Workspace/effort/Deck策略所有权。

公开偏好路由移除Dream DB，仅typed two operation。其它System Config/first-login/导入/后台读取仍明确待迁移，不靠该合同扩大context授权。补actualFastAPI/Auth/DTO/MockTransport/DBfence的partial/null/emptyobject/numeric/time/permissions/invalid fields/unknown原UUIDno retry测试，同步nearest file/folder/README镜像/现行设计与旧时序索引；专用runner技术验收无PG/网络/模型/用户服务/SDKruntime，不改pins。

阶段18实现状态：actual60 artifact两hash/identity-unified pins接入；public preferences router无database，shared invoke保持原scope/error/threadpool。closed publicfive optional→wirefive requirednullable，NULL/{}及emptytext/rawfloat/negativezero/bigint/offset微秒/readonlyfirstlogin保留；无法publicJSON投影的stored config503且无heal，写invalidtrue/timeout unknown原UUIDno retry。defaultvoices/System/Runtime/firstlogin/import/后台读取分开。Coordinator传入Admin真实受限public2/78 exit0技术回执（非normal业务），Dream独立Luna gate进行中。

旧sequence source完整保存于docs/design/history/pre-admin-user-preferences-20260915/sequence-diagrams.md，原字节SHA256: 699f7ea4fe740b2f391c7a13b792b985df8b676fd211ba4dd9dfc64f8a1e7fc1；现行用户偏好单独功能稿与索引，原十模块功能/流程不删除，旧issuer/SQL不作为当前规范。

阶段18验证发现并修复：初批五文件186pass；新增raw NaN请求后fresh偏好文件30pass/1fail（FastAPI默认validation detail回显NaN导致JSONResponse编码失败）。偏好局部APIRoute复用原typed校验/OpenAPI，将RequestValidationError转固定422且不回显input，补Inf/overflow/顶层数组/malformed正文用例；不增加全局业务分支。fresh偏好文件 `36 passed in 0.76s` exit0，无skip/failure。初批其它通过文件未修改，不重复运行。`python3 /private/tmp/dream-admin-doc-check.py` exit0：30files/216links/222inventory/history3SHA/README parity/6sequence计数0fail（未render）；`git diff --check` exit0。原sequence archive bytes_equal，SHA与上述原文一致。actual两operation hash/closed schema/identity-unified comparator已exit0。无PG/network/model/账户/用户服务/SDKruntime。

## 阶段 19：资源 Admin HTTP owner 的序列化关闭

### Optimized Prompt · 2026-09-15

关闭清单中仍开放的资源Admin客户端生命周期缺口。复用AdminResourceData原writer串行锁，让policy read/publish/close共享同一活动边界；close等待已dispatch HTTP，标记closed后不重开/不接新request，重复close幂等。client只由resource composition root所有，server在原publisher/refresher/sink/sampler停机与factory drain后关闭该HTTP owner，不关闭别人的服务/连接。

不改资源default/desired/effective/revision/LKG、admission判断顺序/比较/算法/lease、observer最新队列或未知写原receipt规则；关闭后的读取仍由原provider安全fallback，不传播Agent turn。全部操作只在off-turn reader/writer/shutdown；不增加turn PostgreSQL、restart/shell或环境标签路径。

同步file headers/nearest folder/README镜像/现行设计/清单与计划；Luna以actual AdminResourceData/MockTransport/Event/ownedthreads验证close drain active policyread/observerwrite、无并发复用/reopen/新请求、repeat close与LKG，原policy/sink/pipeline回归。不启动真实server/DB/模型/Runtime/服务，不改tmp协议、版本pins或其他后台数据入口。

阶段19实现状态：resource adapter原writer锁覆盖全部read/publish/close，closed前等待active HTTP且closed后不创建/dispatch；server Factory后to_thread关闭resource owner，再原Redis/db/sharedauth。保持原pipeline/LKG/unknown receipt与lease。新增actual lazy-owned HTTP Event/threads和unusedclosed/actual shutdown function DI失败隔离；Luna技术gate进行中。

阶段19 fresh技术回执：指定五文件 `60 passed in 1.61s` exit0，无failure/skip。doc checker exit0：28files/215links/199inventory/history3SHA/README parity/6sequence计数0fail（未render），diff check0。actual server AST wiring检查0：Factory.aclose < resource_data.close < Redis.aclose；admission/lease/pipeline文件无变更。无PG/network/model/账户/服务/SDKruntime；本轮自有线程已结束，无pyc/端口/生成物清理。

## 阶段 20：Browser session 过期异步结果边界

### Optimized Prompt · 2026-09-15

修复已取消或旧/auth/session请求在clear/logout/新session读取之后仍修改内存CSRF的问题。复用唯一browserSession owner及现有strict public DTO，使用对象identity记录当前read代次，不能引入OAuth/storage/token/时间阈值。每个await/catch后检查AbortSignal与read identity；aborted/superseded结果返回null且无状态修改/错误覆盖，旧401不能清除新session。clear与logout开始使已有read失效，logout失败仍保留已验证public session，只有strict成功receipt清除。

唯一owner保存immutable public session snapshot并由其导出CSRF，AuthContext在异步then提交前检查returned snapshot仍为当前owner；过期null同样不能覆盖已加载session。保持当前同源Cookie/CSRF headers、Admin单一登录注册入口、公开profile与失败反馈，不改变server handle/refresh、MCP标准OAuth/Apps、SSE或任意业务DTO。不增加确认或产品限制。

测试显式deferred fetch/JSON覆盖abort before-I/O/after-response/after-json、旧成功/旧401/旧失败、新请求顺序、clear/logout期间旧结果、failedrevoke保留、immutable/no OAuth headers。专用runner执行actual Node helpers与受影响typecheck，无Browser/网络/DB/model/服务。同步header/nearestfolder/README镜像/现行Auth设计/清单，其他全域DB/真实业务gate仍开放。

阶段20实现状态：唯一Browser owner的immutable snapshot导出CSRF，read identity/abort在每个await/catch后检查；clear/logout start失效旧read，strict成功后清除，失败保留。AuthContext then current snapshot identity额外保护UI commit。deferred fetch/body覆盖旧成功/401/503/失败、abort/clear/failed与successful revoke期间请求，等CSRF不同snapshot也不可adopt；Luna Node/typecheck/doc gate进行中。

阶段20技术回执：首轮native Node三文件命令exit1：20pass/1fail/0skip，browserSession与fileURL全通过；root误将原Playwright apiBase spec交给nativeNode，extensionless ESM前置失败，不是业务缺陷。无需source改动，复用无Browser/server配置，仅该apiBase文件 `2 passed (234ms)` exit0/0skip。full `pnpm exec tsc --noEmit --incremental false` exit0，无输出。doc checker29files/216links/120inventory/history3SHA/README parity/6sequence0fail（未render），diffcheck0。未启动Browser/network/PG/model/用户服务/SDKruntime，不重复已通过20Node/typecheck。

## 阶段 21：公开 Deck Claude Plugin 引用三项消费端

### Optimized Prompt · 2026-09-15

读取actual Admin deckRuntimeDataDto/Service/Repository/Handler与60-op artifact，消费deck-plugin-refs.list/prepare/replace三项，要求identity/unified exact v1，OAuth用户级管理禁止所有entity grant。仅替换claude_plugins router里的GET/PUT /api/decks/{deck_id}/claude-plugins；global catalog/install/operation/background与runtime packing暂按实际依赖开放，不复制SQL/事务到HTTP或冒充内部授权。

复用StrictDTO/ISO/统一actor/threadpool/error transport。闭集installation metadata无artifact path，prepare输入strip唯一installation IDs；Dream返回后验证selected IDs exact match且ready，复用PluginInstallService原artifact_store.get_artifact和CLI SemVer方法，将不依赖db的两个方法改staticmethod（原算法/调用不改），不构造假的db或另写digest/compatibility算法。public refs的enabled/order默认保留，order用实际PG integer技术范围；legacy无产品依据max32不成为新的产品配额，以实际Admin无此限制合同为准。

只从prepare的server metadata生成package/version/digest/rawcompat source evidence，body不接受这些字段/actor/path。实际FS与CLI验证失败在replace前返回原安全error/status；Admin在同TX锁ownedDeck/installations并重检metadata/ready，refs语义变化推进draft，reorder/no-op保留原记录/时间。Dream保留public {deck_id,refs}及enabled的原0/1投影和ISO微秒，确认reply需matchDeck/IDs；replace unknown保留原UUID/outcome_unknown，不retry，prepare/read错误不制造write。不得用fixture称实际共享FS/CLI或真实模型验收。

新增现行refs功能稿（背景问题/目标边界/概念规则/default-desired-effective-revision/状态失败影响验收），逻辑Deck Plugin历史设计与oldsource不删除/覆盖。同步headers/nearestfolders/README镜像/API/交互/入口清单。Luna验证actualFastAPI/Auth/DTO/MockTransport与明确命名temp artifact fixture、注入CLI版本的技术验证；DB fenced，public scopes/threehash/twoSchema/closed IDs/defaults/no-op/unknown/no blindretry，以及原artifact/CLI纯合同回归。无PG/model/真实账户/服务/SDKruntime/Browser、tmp协议或版本pin变更。runtime-read/voice-memory/analysis与全部其它数据库仍需后续实际消费接线。

阶段21输入边界补充（source变更前）：typed refs与偏好同样必须安全拒绝raw非finite/错误形状，不回显RequestValidationError.input。将阶段18现有局部APIRoute校验wrapper移至同一routers.deps作为可复用route class，偏好仅保留原固定detail子类，Plugin router显式采用固定plugin detail；无全局handler/另一业务入口。既有偏好36合同必须同批回归，保留typed OpenAPI、status与原detail。

阶段21实现状态：threeactual hashes与identity/unified接入；两个refs公开functions无DB/oldservice调用，stripuniqueIDs/closedinputs→prepareexactreadyIDs→原staticartifact/CLI→source evidence→Adminreplace，响应保持原enabled0/1与ISO。保留其它Plugin SQL入口依赖，移除无actualAdmin合同依据legacy32。Prefs与Plugin复用同一scoped validation route，原Prefsdetail不变。actualpublic tests+owned artifact/injectedCLI技术验证与原owner测试已适配；Luna gate进行中。

阶段21 fresh技术回执：指定六文件 `194 passed in 1.63s` exit0，无failure/skip。三operation canonical/hash与两exact schema requirements、TS closed DTO/artifact、两个public函数无DB/oldservice comparator最终exit0；首次checker误拒允许的static/signature差异，修正checker后通过，无产品测试失败。原CLI/artifact算法只有staticmethod/self/header diff。doc checker33files/238links/229inventory/history3SHA/README parity/6sequence0fail（未render），tracked diff0；new2py no-index innerexit1/no output仅内容差异无whitespace。未访问PG/network/model/account/服务/SDKCLIruntime，无pyc；只清自有stage21-noindex临时输出。

## 阶段 22：共享 capability catalog 并发刷新

### Optimized Prompt · 2026-09-15

修复统一Client共享catalog refresh在加载期间清空advertised导致其它已验证caller误判missingcapability的竞态。先以actualClient/MockTransport/Event/明确命名ownedthreads复现：initial广告成功，另一个refresh已dispatch但blocked时，execute不能直接因为中间空dict误503；refresh完成合法则继续原UUID，failed/missing/drift则无operation I/O failclosed。只用技术DTO注册fixture，不拷贝业务/SQL/身份状态机。

复用Client统一transport，增加catalog RLock；capabilities readiness读/刷新HTTP与execute广告检查共享同一lock。execute只在合同/type/scope/DTO生成的短检查阶段持锁，实际领域HTTP在锁外，既有RPC仍可并发；receipt保持原二态与originalID无重试，不改变刷新失败清空ready/advertisement与下一RequestAuth恢复。body/header仍per-request显式actor，无全局token状态；不引入TTL/缓存quota/租户/环境分支或全局HTTP串行。

只改共享metadata同步和meaningful并发测试/相关headers/folder/README镜像/现行设计/清单。Luna先给当前源码复现failed命令回执，root修复后fresh client/共享Auth/各消费端相关合同；验证RPC可以同时dispatch、多个刷新不能交错修改广告、失败不使用旧广告、unknown原UUID不自动重发。全部MockTransport/ownedEventThreads，无PG/model/账户/network/服务/SDKruntime；当前资源/admission/lease/SSE/FS和所有未迁移领域保持边界，不把本阶段称全域完成。

阶段22 RED技术回执：真实Client受控并发6用例命令exit1，`5 failed, 1 passed, 67 deselected in 0.21s`；四种refresh等待断言和双refresh交错断言复现，无PG/network。root增加catalog RLock覆盖readiness/完整refresh/短execute检查，领域HTTP锁外、receipt不改，fresh共享Client/Auth/领域合同待验。

阶段22 fresh技术回执：指定十文件共享Client/Auth/领域集合 `324 passed in 2.47s` exit0，无failure/skip；六并发用例全部通过，私有广告/readiness仅Client内部访问，execute HTTP在锁外。doc checker exit0：30files/236links/202inventory/history3SHA/README parity/6sequence计数0fail（未render），diffcheck0。无PG/network/model/account/services/SDKruntime，无pyc或自有线程遗留。

## 阶段 23：公开好友与邀请码九项消费端

### Optimized Prompt · 2026-09-15

读取actual Admin socialFriendshipDto/Service/Repository/Handler、69-op Registry与九operation artifact，复用统一StrictDTO/decimalPK/ISO/null/transport/actor/threadpool/原receipt。仅消费已通过provider-free公开9/230合同的friend-invite.generate/use、friend-request.list/accept/reject、friendship.list/remove/timeline/picture-full，全部OAuth-only和identity/unified exact gate，body不能传actor/user_id；不迁移或重建Adminpair/code锁、状态机/SQL/policy到Dream。

替换routers/friends.py全部九个Dream DB入口，保留原公开整数ID、required nullable微秒时间、label/thumbnail/full图字段；closed success:false/error原400 detail，timeline null403/full falsey404，其余安全错误及unknown原UUID沿共享调用规则，不重发写。邀请码生成长度/有效期只由Admin显式policy默认6/604800执行；Dream不加限制或确认。pending只能recipient accept/reject，Admin保证同一码只消费一次、accept/reject唯一transition、rejected同方向重申保留rowID刷新时间，used_at非空不能再次消费；这些并发证明来自Admin真实公开技术回执，不在Dream复制模拟数据库。

保留原database九helper的名字/签名以明确拒绝旧路径，移除它们的生产SQL并在任何连接前抛安全AdminDataError；不把任意user_id转为服务权限，不制造兼容DB fallback。其它daily-picture/导入SQL仍在清单，不借本阶段删除程序/测试/历史原文。新功能稿按背景问题/目标边界/概念规则写正常、状态、失败、影响、验收；非配置好友关系明确无revision，不假造CAS字段。现行sequence只改好友模块并引用已字节保存的原十模块history。

同步受影响file headers/nearestfolders/中英README/API/架构/清单，避开协调own20docs。Luna用actualFastAPI/RequestAuth/Pydantic/MockTransport/DBfence验证全部九路由、原closed错误/null/empty/UTF8/数字时间/scopes/strict actor拒绝/hash drift/unknown原receipt及无blindretry，技术DTO与实际canonical/hash逐项比较。无PG/network/model/真实账户/Browser/服务/Runtime/共享FS，不改版本pins、TMPDIR、Agent/SSE资源语义；正常真实业务仍待既有parent验收。

阶段23实现状态：nineactual hashes/identity-unified已注册，公开九functions无database import/call；closed rawcode/decimalPK/nullable ISO与原projection/error/null图片保持，Admin控制policy/locks/TX。旧database九helper保留签名并在I/O前拒绝；current social design/sequence/history索引同步。Luna provider-free gate待运行；未触碰PG/account/network/model/service/Browser/FS/Runtime，全部目标仍active。

阶段23首轮技术回执：六文件命令exit2，collection五文件受同一PydanticUserError阻塞，未执行用例；discriminator字段不允许mode=before field validator。root改为各分支model-before校验，仍严格拒绝非boolean，不取消union/闭集。另将新receipt fixture改为原status/result DTO，生产receipt未改。static9hash/requirements/AST comparator0，doc32files/243links/228inventory/history3/README/6sequence0，diff0；fresh同批待验。

阶段23 fresh技术回执：Luna因usage limit停止，未返回修复后回执；primary直接运行原六文件命令 `257 passed in 2.30s` exit0，无failure/skip。runtime9 closed fields/type/null/enum、canonical/hash/requirements/ISO函数与旧9helper签名/其它database函数AST comparator最终0；custom checker初次按未sort canonical/empty required/ISO regex表达差异误拒，修正checker表示处理，未改产品或测试断言。另发现actualtimeline descriptor minimum=-MAX而actualZod链非负，Python保持0；记录Adminmetadata修正缺口而非假称bounds完全一致。actualAdmin安装Zod原链pure验证exit0：runtime_negative_accepted=false/runtime_zero_accepted=true/descriptor_minimum=-9007199254740991，无DB/Provider。doc checker33files/247links/228inventory/history3SHA/README parity/6sequence计数0fail（未render），diff0。无PG/network/model/account/Browser/services/SDKRuntime，未用reset credit/改依赖；Luna首轮collection失败仍保留。

## 阶段 24：公开 Voice CRUD 四项消费端

### Optimized Prompt · 2026-09-15

消费actual已发布Deck19中的voice.create/update/delete/collect，复用统一StrictDTO、EntityId、SafeInteger、原JSON object helper与Deck version四schema exact gate，不能迁移成逐SQL远程调用。仅替换voices.py四公开Voice路由与其typed request模型，Deck十操作、default plugin evidence/安装catalog/其他后台仍按当前依赖开放。Admin控制ownedDeck/Voice行锁、创建默认Memory与order、内容/偏好/thread语义、draft revision及原UUID回执，不在Dream再写事务或state算法。

公共create optional/null→wire requirednullable；原空Memory create使用Admin显式policy默认。update原None省略保留已保存值，emptytext/emptydict/false/0仍传，memory_workspace_config对象以Python原json.dumps（update sort_keys沿用原行为）产生rawstring，保留float/negativezero/bigint；公开finite/对象校验拒绝NaN/Inf且无原body echo，body禁止actor/id/evidence。只原thread_id设置由Admin新实体权限边界校验，不持scope更宽的Runtime purpose。四返回保留voice_id或success:true，changed:false原404；closed已知domain错误映射原create/fork安全400 detail，其他依原统一code/status/unknown ID，不使用上游message。

Actor只有current request OAuth；missing/hash/schema/domain失败在公开入口与Admin独立failclosed。unknown只保留同operation原UUIDreceipt，无自动写retry。数据库四helper尚有内部/default/fixture消费者时保留明确清单依赖，不能借公开迁移破坏后台或清理程序/测试。同步受影响folder/file headers、README镜像、API/现行Voice功能稿与清单，保持现行/历史各自索引。

Luna actualFastAPI/Auth/DTO/MockTransport/DBfence验证四public入口、requirednull/optional省略/empty/false/zero/Unicode/rawJSON数值、Memory默认不由Dream制造、actor字段/finite拒绝、fouractualhash/physicalcap、unknown原receipt、单POST/no-blindretry，以及原Deck routes回归不动FS/default行为。Provider-free，无PG/network/model/正常账户/Browser/用户服务/SDKRuntime/安装，不改变Agent/资源/SSE/lease/TMPDIR或pins。正常真实业务与全部生产DB仍开放。

阶段24复用细化（shared source改动前）：统一transport会调用完整model_dump，optional wire字段必须只序列化model_fields_set，不能把默认None注入wire。将既有EditorDTO的present-fields wrap serializer提取为ChatStrictDTO同目录共享PresentFieldsDTO基类；Editor保留自身null检查，VoiceUpdates只复用序列化并按actualnullable允许显式null。原Editor/session合同需同批回归，不更改全局parser/model_dump或Other DTO。

阶段24实现状态：fouractualhash/fourSchema已注册，四publicVoice functions无DB；create requirednullable/原Memory default交Admin，update原None省略/emptyfalsezero与raw数值/sort保持。shared PresentFieldsDTO只提取原Editor serializer，Editor null校验不变；四路由采用局部安全validation class，Deck其它函数不改。技术gate待运行；无PG/model/network/account/services/Browser/SDKRuntime，未改pins/tmp/Agent/SSE资源。

阶段24 fresh技术回执：Luna usage限制仍不可用，primary执行指定八文件 `280 passed in 2.12s` exit0，无failure/skip。四actualhash/canonical/requirements/closedDTO shape comparator0；present-fields method与Editor optional-null method AST原样，其他Deck函数/整个database.py source unchanged，四公开Voice AST无DB。doc checker34files/254links/231inventory/history3SHA/README parity/6sequence计数0fail（未render），diff0。无PG/network/model/真实账户/Browser/services/SDKRuntime或pins/tmp/Agent/SSE资源改动；其他域与正常业务gate仍active。

## 阶段 25：公开 Deck 五项 mutation

### Optimized Prompt · 2026-09-15

消费actual已发布Deck19中的deck.update/delete/collect/toggle-publication/sync-parent，仅替换voices.py这五条公开路由。Deck list/detail/create/default/provision需要原defaults/FS证据仍保留依赖，不能拿候选DTO冒充已授权安装metadata。复用统一StrictDTO/PresentFields/EntityId/SafeInteger与four exact Deck schemas，OAuth-only，body拒acting user_id与原None省略、empty/false/0保持；Admin独立处理locks/CAS/draft/refs/Voices复制/发布与parent detach/collection计数/TX原receipt，不在Dream仿造组合事务。

公开update/delete changed:false原404；publish返回原success/published，collect原deck_id，sync原success/synced_voices。仅known code映射旧safe sharing/default/self/private/parent业务错误与status，不能输出上游message。actual delete的DECK_DELETE_BLOCKED带closed reason：child_decks/related_threads/runtime_history/referenced_records。统一ErrorDTO现仅允许Version409details，需要按code增加这四枚举DTO并严格校验owner，AdminDataError类型随之扩展；保留Version两revision/null规则，拒错code/shape/extra/未知reason，failure仍unknown原UUID，不能把详情宽泛dict放行。删除反馈复用原DeckDeletionConflict纯message投影；其它数据错误按原safe code/UUID/outcome_unknown。

所有write持current OAuth与原UUID；unknown只查同operation/原IDreceipt，无retry。原database相关helper尚有内部/fixture消费者保留清单，未据此删除程序/接口/测试/历史原文。同步affected headers/folders/README/API/现行mutation设计/原设计索引/清单，避免协调own文档。

Luna unavailable usage已确认，本阶段primary执行bounded provider-free actualFastAPI/Auth/Pydantic/MockTransport/DBfence：五route/olderror、none/emptyfalsezero、原collection组合单operation、publish无需pre-read、sync事务owner仅Admin、delete四reason/strictowner/unknown原receipt、Version409旧边界及既有Deck policy/default/技术SQL fixture回归。旧route专用两case改实际HTTP owner合同，保留其它policy/SQLfixture测试。源码hash/requirements/DTO与untouchedDeck/Voice functions逐项比较。无PG/network/model/Browser/用户账户/服务/SDKRuntime/FS/迁移/secret/pin/tmp/Agent/SSE资源变化，整体goal继续active。

阶段25复用细化（source改动前）：将Version/Voice原相同fourSchema fresh检查提取为deck_version_data.require_deck_capabilities，三adapter调用同一检查；原Version outer/nested identity和Voice返回语义保持，同批回归。共享transport不新增SQL/全局actor或重试。

阶段25实现状态：five actualhash/four schemas已注册，五公开Deck writes无DB；update None省略/emptyfalsezero与原结果保留，publish无需Dream预读、collection复制计数单operation。共用原Version/Voice schema检查，Version identity/Voice语义不改；ErrorDTO按code保留两revision或四reason，安全反馈丢上游message。首轮primary九文件 `295 passed in 2.00s` exit0，无failure/skip；新增malformed结果/可选details用例与actual合同/文档gate待最终检查。无PG/network/model/真实账户/Browser/services/SDKRuntime或pins/tmp/Agent/SSE资源改动。

阶段25最终技术回执：初始九文件295pass/2.00s后新增十项malformed结果/optional details，primary指定Deck文件 `63 passed in 0.95s` exit0，无failure/skip；未重复无变化的其它已通过文件。actual五canonical hashes/capabilities/four requirements/closedDTO comparator0，四reason与原schema gate/Version identity AST保持，其他Deck/Voice functions/database整体与原policy/deletion早期tests unchanged，五公开write无DB。doc checker35files/269links/234inventory/history3SHA/README parity/6sequence计数0fail（未render）；git diff --check exit0。正常业务、全部其余DB迁移仍active；本阶段不运行真实账户/PG/model/network/Browser/services。

## 阶段 26：公开 Deck 详情读取

### Optimized Prompt · 2026-09-15

消费已发布deck.detail，只替换GET /api/decks/{deck_id}。复用exact four Deck schemas/统一client/current OAuth/dream:read/EntityId/SafeInteger/时间与canonical ID校验，不把当前缺安装catalog的list/create/default/provision同步迁移。闭集Deck/Voice aggregate DTO只读取actual requirednullable字段，Admin计算agent type/binding revision/sharing/version状态、ownedDeck过滤与Voice排序，Dream不复制policy或SQL。验证outer Deck ID及每个Voice deck_id均匹配URL，拒错配；原null仍404 Deck not found。

公共响应逐字段沿用原DBdict；owner decimalstring还原int、ISO微秒原样，Voice memory_workspace_config_json转原memory_workspace_config。原_parse_voice_row只对非空text json.loads，emptytext保留，invalid JSON为None，合法JSON不限object（array/scalar/null皆可）；复用原纯helper而非更严格的preferences config_object，避免误删legacy读能力。保留Pythonfloat/-0/bigint，公共JSON无法表达NaN/Inf时安全503，不heal/重写。wire deck_version_capability LiteralTrue须额外按exact bool拒1。

独立provider-free actual FastAPI/Auth/DTO/MockTransport/DBfence验证正向完整字段、nullable/legacyMemory/numeric/time、outer/nested实体错配、malformed/extra/missing/boolean/安全整数/权限/cap漂移/null404、单read/no retry且拒委托。原Deck mutate/Voice/version/publicSession共享合同已有pass，仅按新增生产source影响执行适当相关测试；不碰正常PG/账户/model/network/Browser/services/SDKRuntime/pins/tmp/Agent/SSE资源。同步相关设计稿3基础/状态失败影响验收、README/目录/API/清单；真实普通业务gate与全域DB目标继续active。

阶段26复用细化（source改动前）：原_parse_voice_row只在database内定义，无现有独立Memory投影模块。将同一纯函数原样提取到backend/voice_projection.py，database以同名import alias保留旧内部接口/调用，不引入数据库依赖到Admin DTO。新消费者只复用纯helper，原函数AST与其它database函数必须逐项验证。

阶段26实现状态：one actualhash/four schemas/OAuth read已注册，public detail无DB、null404，outer/nestedDeck错配拒绝；闭集requirednullable/time/owner字段保持，pure helper提取原AST且database同名alias/其他functions unchanged。primary八文件 `246 passed in 1.84s` exit0无failure/skip。实际合同checker初次因整数exclusiveMinimum:0与minimum:1表示差异失败，按相同整数集合归一后exit0，未改产品DTO。

阶段26实际Admin projection gap：voiceRow源执行 `if(raw!==null)JSON.parse(raw)` catch归null；Node JSON.parse(emptytext)回执null，而原Dream pure helper回执emptytext。本阶段consumer对响应empty仍保留原行为，但真实producer修正前不计该legacy值验收完成；Admin源只读未改。另未改变原invalid JSON→None/公共nonfinite安全503。完整普通业务/其他DB目标继续active。

阶段26最终文档/源码技术回执：actual contract/closed DTO/exact four requirements/canonical hash/ISO与原pure helper AST/alias/其他database与router函数检查exit0；producer empty Memory语义gap明确保留。文档检查35files/280links/237inventory/history3SHA/README parity/6sequence计数0fail（未render），git diff --check exit0；之后更新write现行稿详情索引再检查引用。未跑正常业务/PG/model/network/Browser/服务，不宣称全部生产迁移完成。

阶段26最后引用检查：35files/281links/237inventory，failures=[] exit0；历史与README/6sequence检查保持。

## 阶段25–26命令与停止状态回执

工作分支提交：1794bd81（五公开Deck写）；40f04ed4（owned详情读与原Voice纯投影提取）。primary使用已有Python依赖，本轮不运行PG、模型、Browser或用户服务。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_deck_mutation_routes.py backend/tests/test_admin_deck_version_routes.py backend/tests/test_admin_voice_routes.py backend/tests/test_admin_session_routes.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_data_boundary.py backend/tests/test_deck_defaults.py backend/tests/test_deck_sharing_policy.py backend/tests/test_deck_deletion.py
# exit 0; 295 passed in 2.00s（新增十项结果/optional details之前）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_deck_mutation_routes.py
# exit 0; 63 passed in 0.95s（新增十项之后）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_deck_detail_routes.py backend/tests/test_admin_deck_mutation_routes.py backend/tests/test_admin_voice_routes.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_deck_version_routes.py backend/tests/test_deck_defaults.py backend/tests/test_deck_deletion.py backend/tests/test_deck_sharing_policy.py
# exit 0; 246 passed in 1.84s
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage25-contract-check.py
# exit 0; actual hashes/DTOs/requirements/gate/untouched-source PASS
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage26-contract-check.py
# exit 0; actual hash/aggregate/requirements/ISO/alias/source PASS; producer empty Memory gap retained
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 35 files, 281 links, 237 inventory; failures=[]; history3/README parity/6sequence count（未render）
git diff --cached --check
# exit 0（每项提交前）
```

最后只读检查：registry仍70；Workflow公开Run/PF读取使用_story_workflow_current_user，其默认workspace由Dream数据库取得，尚无发布的workspace默认领域合同；PF70完整fault/interruption/unknown验证仍pending，不能消费未关闭gate。其他全域清单、Admin empty Memory projection与timeline descriptor差异、正常本机真实业务/模型验收继续保留。协调任务同步仍受此前auto-review拒绝及未回复授权限制，不重试或绕过。get_goal返回usageLimited（用户用量控制状态），本目标未标记complete/blocked；本轮代码与目录文档均已提交，未消耗reset credit。

## Admin未注册Run创建/重试通知与Dream依赖复核

Admin报告独立prospective实现25项源/原子性与9项OAuth ingress通过；本任务未重跑Admin测试，也未将该报告计为注册/发布/正常业务证明。只读workflowRunCreationDto与实际70 registry复核exit0：workflow-run.create/retry均未注册，shared PF70/Route/DTO/Registry冻结继续保留。

create闭集输入为workspace_id/workflow_preflight_id/preflight_token/idempotency_key，加全null或完整source_voice_thread_id/source_message_id/source_message_time；retry为相同四项加workflow_run_id，不接受替换source。两输出复用既有完整{run:WorkflowRun}。key长度按原Python码点规则；Admin报告四项旧输出UTF16候选与原源码八例差异需修正，原完整schema/hash保持且等待解除冻结；Dream不按候选猜hash或发布capability。

ensure_source属于Admin未来持久化领域实现，Dream只在实际发布后接消费者。当前Dream原Application由actor/workspace/key的canonical JSON推导UUIDv5 Thread/message，在PF与Run前原子确保隐藏来源。原ensure_source metadata不含workflowRunId；Run确认后Application进入原dispatcher，dispatch claim先保存workflowRunId/dreamContext与dispatchStatus=dispatching，再调用turn dispatcher。不能将通知中的“dispatch后才绑定”扩写为Runtime接受后才写绑定或改变原claim/lease/失败重入语义。原来源tuple、fingerprint、UUID与source先提交/Run后dispatch顺序均继续作为验收依据。Runtime/Agent编排仍Dream所有；尚无已发布ensure_source/dispatch领域capability，生产PG迁移保持pending。

本轮仅文档记录，未修改production代码、Admin源、registry/hash/schema、服务/数据库/模型，也未发送跨任务消息。

## 阶段27：完整公开Deck列表

### Optimized Prompt · 2026-09-15

源码复核get_user_decks/get_published_decks都是只读aggregate，list不执行default reconcile/文件检查。因此消费已发布deck.list覆盖GET /api/decks全部published false/true业务模式，创建/default/provision/install仍保留独立依赖。公共published query沿用FastAPI原bool语义，内部community closed bool、current OAuth/dream:read与four exact Deck schemas/hash。Admin唯一负责owner/community/exclude-currentactor/retired visibility、enabled与total计数、author与binding/version/sharing装饰和排序，Dream不重算policy或SQL。

复用Deck detail的OwnedRow/DeckRow/安全整数/ISO/canonical ID投影；将原公共policy字段与exacttrue validator原样提取为DeckPolicyDTO，detail只增加voices和其原projection，AST证明原行为。ListItem继承policy加voice_count、requirednullable total_voice_count/author_display_name；原user响应保留total_count、不包含新增author_display_name，community保留author_display_name、不包含新增total_count；server总是发送闭集nullable字段，Dream只做原响应投影。owner还原int、空/null/bool/zero/time保持，无默认初始化/文件操作/重试。

provider-free实际HTTP/Auth/DTO/MockTransport/DBfence验证两mode/emptylist/计数与fields/大owner/时间/exactcap/权限/closed malformed/timeout与单read；旧同步list-route case改实际HTTP，原共享policy SQL fixtures保留。相关detail/mutation/Voice/version/current auth同批必要回归，不跑PG/账户/model/network/Browser/services/SDKRuntime/pins/tmp/Agent/SSE资源。同步受影响headers/folders/README/API/现行设计3基础、模式/状态/失败/范围/验收和迁移清单。整体全域目标与未发布PF/Run/source依赖保持pending。

阶段27fresh技术回执：primary指定九文件 `270 passed in 2.27s` exit0无failure/skip。actual deck.list canonical hash/capability/four requirements/closed DTO comparator0；原policy fields/validator/detail projection AST与其他classes/router functions/database整体/原共享policy其他tests unchanged，公开list无DB。创建/default/provision/install/后台仍pending；仅迁移只读list不新增FS/init/确认/重试。

阶段27当前源码清单：只读AST scanner排除tests/手工script/明确offline schema模块，exit0/parse_errors=[]；48个模块有513个字面SQL execute候选、16个模块有数据库driver/persistence imports。动态SQL与Repository/pool/stdio仍另行追踪，不能与baseline835片段相减或声明全域关闭。完整路径/计数记录当前迁移清单；本轮未调用正常PG/模型/服务/文件/Runtime。

阶段27命令：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_deck_list_routes.py backend/tests/test_admin_deck_detail_routes.py backend/tests/test_admin_deck_mutation_routes.py backend/tests/test_admin_voice_routes.py backend/tests/test_admin_deck_version_routes.py backend/tests/test_admin_request_auth.py backend/tests/test_deck_defaults.py backend/tests/test_deck_deletion.py backend/tests/test_deck_sharing_policy.py
# exit 0; 270 passed in 2.27s
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage27-contract-check.py
# exit 0; actual hash/DTO/four requirements/shared-policy/source PASS
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-current-sql-scan.py
# exit 0; 48 SQL-bearing modules/513 literal candidates/16 driver-persistence import modules; parse_errors=[]
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 35 files/341 links/239 inventory; failures=[]; original history/README parity/6sequence count（未render）
git diff --check
# exit 0
```

本轮actual关闭入口：GET /api/decks published false/true；原database两list helper仅剩旧test调用，没有生产Python调用者，但函数SQL本体作为现有fixture/清理依赖保留，未将整个database模块报告关闭。全域目标继续未完成；协调报告PF八失败/unknown/UOW/expiry/reads/三阶段中断已补，末段receipt权限/文档核验尚未发布完成通知，consumer仍以发布capability与实际完整gate为准。资源/Runtime/共享FS本轮无业务变更或真实回归，不用provider-free读接口PASS冒充其验收。

## 2026-09-15协调继续指令：Runtime与共享文件技术回归

本轮actual关闭并提交GET /api/decks published false/true：4a0f6162。此前五write1794bd81与owned详情40f04ed4保持；公共Admin消费者统一strict DTO/client，无新direct fallback。主协调报告Preflight八检查失败、unknown/初始UOW rollback、expiry/reads/三阶段真实提交中断已补，末段原receipt权限与文档核验尚在冻结，发布通知前consumer保持pending。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_claude_agent_workspace.py backend/tests/test_claude_plugin_pipeline.py backend/tests/test_sdk_env.py
# exit 0; 105 passed in 8.35s
```

实际执行已有production workspace/TMPDIR/sandbox、artifact/packer和SDK配置代码的provider-free技术合同：由临时工作区/受控SDK依赖与明确test内SQLite memory fixture验证，不接正常PG、Browser/用户服务、模型或真实Gateway/CLI provider；owned temp由test context释放。共享文件HTTP授权、真实Bash sandbox回执、真实CLI/模型与普通服务仍不计验收，本轮未改tmp协议/版本pins/Runtime算法或资源。

Gateway只读源事实：Admin gateway/auth已接gateway-cli idg purpose；Dream SDK helper仍从AdminGatewayConfig读取global service key并签subject JWT，selected model仍读database.get_system_config。目的委托的消费端需服务器持有的immutable grant/config、既有keeper/cleanup与内部launch同路径接线，不能仅替换env文本或保留本地issuer fallback。SystemConfig与后台CLI/Editor/来源/dispatch持久化capability仍未完成，继续全域清单。

Workspace文件HTTP生产身份已复用get_current_user/Admin共享依赖；旧测试fixture仍patch retired auth.verify_access_token且没有配置Admin owner，本轮未用它冒充Admin OAuth授权验收。生产Thread/SystemConfig metadata仍直接调用database，继续迁移，并适配实际DTO harness。所有源码/统计是技术状态，完整生产SQL/Repository与普通账户/模型/Admin可见业务目标未完成。

当前SQL复核补充：同一scanner遍历nested/direct legacy database imports，35模块/122直接helper Call候选exit0；DI/default callable的零Call引用仍开放，完整路径另列清单。48字面SQL模块/513调用与16driver/persistence import模块保持；统计不能替代运行可达性证明。Workspace生产身份源码实际已共用get_current_user，未制造认证代码变更；仅Thread/SystemConfig数据与旧测试harness继续待迁移。

## 阶段28：公开 Preflight 读取

### Optimized Prompt · 2026-09-15

先消费实际注册的 workflow-preflight.read，将 GET /api/story-workspace/workflow-preflights/{preflight_id} 接入当前 Admin OAuth/dream:read。源码 read_preflight 只按 created_by 和 ID 查询，不使用 workspace；这条 GET 移除无关 default Workspace 初始化与旧 application service 依赖。POST execute 与 Run 创建/重试、default Workspace、SystemConfig 仍分别迁移，不改变其他入口。

复用 WORKFLOW_SCHEMA_REQUIREMENTS 的 identity/unified 两项 exact capability 与实际 read hash ddb0cf666b0dc24fcc4df3ef84be42232b5f907d3361c165eb4c6244bc912d73。新增闭集 input/output，保留完整 17 字段、required nullable、原字符串 strip、非负安全 revision、带时区且最多六位小数的 ISO 时间原文；复用原 WorkflowPreflight model 状态/失败字段/snapshot/token/精确微秒 expiry 检查，不复制状态机、不按 Dream 时钟重新判 token。响应 ID 与已认证 canonical actor 必须匹配。token 不进入 repr/错误日志。

公共坏 ID（包括额外空白）与 Admin owner 拒绝保留原 WORKFLOW_PERMISSION_DENIED/404，其他 transport/DTO/capability 失败使用统一安全 code/request UUID/outcome_unknown 反馈，不回传上游正文、不重试读。测试走实际 FastAPI 生产依赖、Admin client/DTO 与 MockTransport，并 fence Dream get_db/default Workspace/旧 service；覆盖所有状态/nullable/token、微秒排序、owner/ID、两 schema/hash/scope、原404、超时同 UUID 无重试。更新现行设计、folder/header/README 镜像与逐入口清单，报告真实命令与技术范围。

当前发布事实另行更新：实际目录 72 项，新增 Run create/retry 已注册，旧 70 项契约保持的通知须按规范核对；主协调的新公开集成验收仍 pending。读取已见本地 primary remaining-read 8cases/74assertions exit0、原 receipt permission tail 11assertions exit0，均为隔离技术证据，保留完整命令的历史失败，不能称一次全部成功。隐藏 launch-source.ensure 仍未注册。Runtime/资源 LKG/共享文件、版本 pins 与普通服务均保持原边界。

阶段28源码细化：原 GET 的 _workflow_json 调用 WorkflowPreflight.model_dump(mode="json")，因此 wire 保留时间文本并按实际 DTO 拒绝时间前后空白，公共响应继续由原纯模型输出 datetime JSON（UTC为Z），不将新 wire 原文直接替换旧时间序列化。状态与公共投影都复用该模型，无需改它的源码。

阶段28 fresh 技术回执：primary 实际执行以下命令；不接普通 PostgreSQL/账户/服务/网络/模型/Browser，不修改 Admin 源或 Runtime pins。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_preflight_routes.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_workflow_data.py backend/tests/test_workflow_preflight.py backend/tests/test_story_workspace_api.py backend/tests/test_admin_chat_routes.py
# exit 0; 141 passed in 2.44s; no failures/skips
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage28-contract-check.py
# exit 0; actual72 canonical descriptors/new Run hashes/full keys; read DTO/hash/two schemas, original model/Workflow/database/Runner/Workspace/auth methods/other routes unchanged
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 35files/377links/242inventory, history3 exact bytes, README parity, 6Mermaid count, failures=[]; no rendering
git diff --check
# exit 0; no output
```

初次 pytest 命令误写不存在的 test_admin_workflow_context.py，exit4/no tests；按实际文件清单纠正为 test_admin_workflow_data.py 后才有上述通过结果。初次 AST checker 指向不存在的 server/runner.py，exit1；纠正为实际 agent_runner.py 后通过，没有改生产代码以迎合检查。72项 canonical hash 均自洽，create/retry匹配实际新hash/full Run keys；本轮没有早期70完整descriptor快照，故不声明历史70字节比较通过。revision metadata差异仅在比较器副本显式标注实际非负边界，未改目录/源/hash。

已关闭本条公开 GET 的 SQL/service/default Workspace 依赖；旧 read/service 实现及其他入口仍存在，不将模块候选数量减少或 technical 模型测试当作全域/正常验收。Luna此前usage limit失败，本批由primary执行同provider-free边界；目标仍未完成，未同步跨任务消息。

## 阶段29：共享文件读取的 Thread 数据入口

### Optimized Prompt · 2026-09-15

复核实际72目录与默认composition：公开owner注册54操作，其他18中resource两项已由独立composition接入，不能将非公开列表当剩余总数。SystemConfig/default Story Workspace均无已发布操作；原 default helper按actor读取oldest(created_at,id)或创建默认记录，不能用Deck default/PF execute/用户偏好替代。保留其pending并继续独立已有chat-thread.get。

共享文件 content/download 生产身份已共用Admin get_current_user，原 _require_owned_workspace_thread 仍读Dream PG。复用AdminChatData/ThreadIdInputDTO/原闭集ThreadResultDTO、实际GET hash与identity/unified两exact requirements，验证reply Thread ID及canonical actor；null保持原404，capability/HTTP/DTO/owner错配保持固定WORKSPACE_AUTH_UNAVAILABLE/503，不泄露异常。Admin客户端由request.app的显式owner提供，OAuth只在线程池操作内传递；无用户ID输入、额外grant/PG fallback。

两GET按原顺序session ID→Thread owner→Workspace Mode→public path→existing filesystem执行；仅增加Request DI与await owner查询，不改变文件路径、symlink、no-create、cache/MIME/ZIP/header、其他list/upload/delete/move入口或TMPDIR/Runtime协议。SystemConfig两读取仍pending。本批将Workflow原two-schema四行gate原样提取为共享require_workflow_capabilities，Workflow context/Preflight/Workspace复用，展开AST证明前两原行为未变。

原Workspace测试fixture仍patch退役localJWT，先适配为实际OAuth owner/MockTransport/严格Thread projection并fence get_db/get_chat_thread，保留SystemConfig受控fixture与原临时FS实例。两owner-null案例改用受控Admin输出，其他业务断言原AST保持；增加两GET的scope/hash/schema/owner-ID/timeout拒绝且Mode/FS未调用的故障断言。跑相关Admin、原Workspace/SDK/packer技术合同，保持正常服务/PG/模型未触及。同步现行共享文件设计/folder/header/README与逐入口清单，精确报告闭合范围。

阶段29规范细化（比较器实际失败后、修正源码前）：chat-thread.get 实际要求四项，除 identity/unified 还含 dream.chat-history-keyset-pagination.v1（a0dfe5f8d4b4330a9e17db07a8716d5d2bc25e291f3624f09005e79c01fc8ab0）和 dream.chat-history-final-projection.v1（50c27f86113c170064b0913bf052f9bd12884d3345c920d7b11468a768e0a432）。Workspace必须消费四项，不能只按Workflow两项推断。两项gate仅供原Workflow/Preflight复用；Workspace复用其两项值并检查完整四项，fixture按实际目录同步。此前296测试通过只属修正前技术结果，不计实际requirements闭合；修正后重新验证。

阶段29实际结果：content/download复用当前OAuth/strict Thread DTO/实际four schemas与hash，null原404，所有metadata故障固定原503；Mode/path/FS顺序、GET其它body与文件规则及其他管理函数AST保持。原测试除setUp/tearDown与两Admin-null selector外，其余旧函数/断言AST保持；新增wrong actor/ID/DTO、four capability（含keyset/final）、timeout与非法OAuth均在Mode/FS前拒绝。两旧gate展开AST保持Workflow/Preflight行为，原ChatDTO/数据库/Runtime/Workspace源未变。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_workspace_router.py backend/tests/test_admin_preflight_routes.py backend/tests/test_admin_workflow_data.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_chat_data.py backend/tests/test_admin_chat_routes.py backend/tests/test_claude_agent_workspace.py backend/tests/test_claude_plugin_pipeline.py backend/tests/test_sdk_env.py
# primary fresh after actual four-schema correction: exit 0; 296 passed in 11.78s; no failure/skip
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage29-contract-check.py
# exit 0; actual Chat get/four requirements/hash; expanded old gates/other route bodies and assertions unchanged; metadata ownership DB-free, SystemConfig2 pending
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 39files/392links/290inventory/history3 exact bytes/README parity/6Mermaid count/failures=[]; no rendering
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-current-sql-scan.py
# exit 0; 297modules,48SQL-bearing/513literal candidates,16driver/persistence imports,35legacy modules/121helper Call candidates,parse_errors=[]; not full runtime reachability proof
git diff --check
# exit 0; no output
```

规范checker最初因错误两项requirements假设exit1，按实际四项改消费者与fixture后重跑；后续checker因比较测试时引用上轮循环残留node而exit1，修正只读checker索引old[name]后通过，没有改生产代码或旧业务断言。文档checker初轮误将inline Markdown示例当链接、将明确“未迁移文件（跳过）”历史foreign清单当本目录成员；按Markdown code/该历史章节边界校验真实链接与现行inventory后通过，原示例/历史名称均保留。

仅清理测试自有temporary workspace/HTTP context，未访问正常PG/账户/网络/模型/Browser/CLI provider，未重启服务/更改资源算法、LKG、Runtime版本或CLAUDE_CODE_TMPDIR协议。本阶段不声明SystemConfig/default Workspace/所有文件管理无PG，也不当作真实共享文件/Bash/模型验收；目标未完成，跨任务同步仍未发送。

### 72项冻结期间的 launch 候选复核 · 2026-09-15

新通知与实际规范复核分开记录。当前目录仍72，Run create/retry已注册；按实际名称 dream-launch-source.ensure、dream-launch-dispatch.claim、dream-launch-dispatch.finish 查询，目录均无广告，operationRegistry亦未接入。不能将候选DTO/Handler/Repository视为已发布capability，不新增Dream消费者或猜hash。主协调正在Run故障/unknown COMMIT验收；通知报告独立剩余public22 denial+10GET/230assertions exit0/skipped6，原full28 exit1与六项fullbounded/core8原文保持，本轮只读该协作状态与Admin矩阵，不称Root重跑或一次完整通过。

实际原Dream源码边界：ensure_source位于PF/Run之前，UUIDv5来源与fingerprint不变。dispatcher先在claim事务保存workflowRunId/dreamContext/dispatching/claim ID并COMMIT；随后独立读取Voice prompt、调用turn dispatcher。异常或accepted False以独立finish事务回pending，接受则回dispatched；finish要求当前dispatching与同claim ID，stale lease返回False，不能覆盖后来claim。_before_claim回调也保持在claim之前，不能借迁移改变Runtime准备/选择顺序。

Admin候选实际DTO只让Dream发送owned Run lookup+instruction_text，或Run lookup+claim_id+accepted boolean；服务端从ownedRun/完整binding/sourceThread/message推导context、parts_json与runtime metadata_json，finish状态由accepted固定映射。claim receipt恢复后重新读取当前source，要求dispatching/同claim ID/fresh lease且parts/metadata/context匹配，否则拒绝旧claim；Runtime/Voice读取不进入这两个提交事务。现Root实现的原顺序已符合这个目标，本轮不制造业务代码变更。

Admin矩阵报告未注册source23+ingress5、dispatch32（Service22/source4/Handler6）、type/lint/source gate exit0；Root未重跑这些命令，也未以它们代替公开PG或完整launch验收。Agent/model/binding prepare、failure recorder、公开PG与正常Runtime/完整launch仍pending。SystemConfig/default Workspace仍没有已发布operation；48SQL模块与动态Repository/stdio迁移继续开放。

本次只读复核及文档命令：主venv Python /private/tmp/dream-admin-doc-check.py exit0，36files/394links/156inventory/history3 exact bytes/README parity/6Mermaid count/failures=[]（未render）；git diff --check exit0无输出。只更新这份执行记录及逐入口清单，不修改production/候选源码、服务、数据库、凭据、Runtime或模型，不重复已经通过的源码测试。

## 阶段30：公开 Preflight execute 领域操作

### Optimized Prompt · 2026-09-15

已实际读取Run72安全回执：remaining public22 denial+10GET/230 exit0/skipped6；selected atomic9与真实finalCOMMIT丢响应业务68通过但原wrappercleanup exit1保留，独立SELECT cleanup3 exit0/owned触发器函数0。本阶段先消费发布PF execute，不将Run全命令/正常业务宣布完成，也不消费未注册launch source/dispatch。

保持POST /api/story-workspace/workflow-preflights的202与原17字段模型projection，将原StoryWorkflowRunApplicationService.create_preflight替换为Admin唯一execute领域调用。_story_workflow_current_user现有default Workspace lookup仍保留并明确pending：实际输入须带workspace_id，尚无已发布default Workspace操作，不能用假workspace或其它DTO替代。保留actor选择顺序；test-only default loader以backend/tests依赖注入实现，不在business添加环境标签或fallback。

复用PreflightDTO/原模型、strict安全整数/JSON与当前OAuth actor，输入workspace_id/deck_id/binding_revision/input_json仅由现有请求和server actor生成。JSON字符串按原PreflightService._canonical_json同一stdlib参数编码，保留Python大整数/float/negativezero与Unicode，不重算hash或check顺序。执行匹配identity/unified/0060 request三项exact schemas与execute SHA413db72b5d4bfc1fdf572d801aec4339a7b00549ea19ebc4025c67f5ae2cf494，response actor/Deck/revision匹配；in_progress须checking无token，committed可checking，不在Dream重开checks、TTL或token。

提供独立typed原PF receipt reader，按已发布SHAad144287942f6f3ad2db82dda7c7b0f20cdf3578e68df4bd8e8b86e8dbbec2f2校对三态DTO与operation/request ID/result state/actor，absent无result。沿用同Admin HTTP transport但不改generic两态receipt parser；任何未知write仅保留原UUID/unknown并显式read receipt，无自动重发/假定rollback。读API不新增Browser/Runtime控制通道。

复用已存在的SafeRequestValidationRoute+scoped router方式仅保护PF POST框架/DTO/JSON validation不回显私密input，其余Story Workspace路由不改。actual FastAPI/auth/client/DTO/MockTransport，fence oldservice/domainSQL，default Workspace fixture明确标记。覆盖完整四状态/request两状态、同原UUIDreceipt三态、无autoResume/retry、boundexpired/nulltoken、schema/hash/scope/actor-Deck-revision与private malformed，相关Workflow/Chat/Workspace技术回归与actual规范/原model/其他router AST、文档mirror/links/inventory验证。只报PF领域执行依赖关闭，不称该POST整体无PG；其他Run/默认/SystemConfig/全域SQL与正常验收继续pending。

阶段30实际结果：PF POST领域执行改为Admin单operation，原202/17字段/纯模型datetime JSON保持；只在该POST安装现有安全validation router。default Workspace loader仍依赖生产SQL，fixture仅在tests显式注入。执行reply actor/Deck/revision绑定，input_json按原四项canonical编码参数保留raw Python数字/Unicode，DTO repr不含input/token。独立原receipt使用同transport和原Identifier（公开调用生成UUID，协议不是UUID-only）、三态/result-state/canonical actor约束；超时write保留原UUID/unknown、不自动重发或恢复，generic两态receipt方法AST未变。没有新增公开receipt路由或完整Browser恢复journey。

阶段30规范检查时Admin已注册75项，实际registry接入source.ensure/dispatch.claim/finish；三个新增SHA分别cb498be127a6aca92c9e6e0cde099c9c80cf78ca2486186e9d043457c2263503、958549a9bfe4b02d8b31e1e538c81ffad020bb4525a328f542f865b377e8ec43、5aa3b738bef5319ee705f5851d83588e1d18dcaf37bdc5789267494fec480f2e。Dream未接这三项；此前72未注册复核是当时历史，不覆盖它。default Workspace/SystemConfig仍无目录操作，不猜hash或复用preferences代替。全部75 descriptor canonical SHA自洽，PF execute实际capability/三schema/closed input-output及独立receipt norm SHA/三schema/closed三态shape通过；known revision导出minimum差异显式标注，原runtime非负安全整数不改，时间校验继续复用原模型。

primary fresh技术命令：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_preflight_execution.py backend/tests/test_admin_preflight_routes.py backend/tests/test_admin_data_boundary.py backend/tests/test_admin_workflow_data.py backend/tests/test_admin_request_auth.py backend/tests/test_workflow_preflight.py backend/tests/test_story_workspace_api.py backend/tests/test_workspace_router.py
# exit 0; 259 passed in 5.46s; no failures/skips
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage30-contract-check.py
# exit 0; 75 actual descriptors,55 client operations,execute/receipt hashes,3 exact schemas,17 original fields; generic receipt/other Story routes/auth methods AST unchanged
env PYTHONDONTWRITEBYTECODE=1 /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 39files/395links/291inventory,3 history SHA unchanged,README parity,6Mermaid count only/failures=[]; no render
git diff --check
# exit 0; no output
```

本轮正常Dream/Admin/Gateway/PG/账户/模型/Browser/Runtime/CLI未调用，不修改Admin源码、SDK/Runtime pins、原模型、数据库或TMPDIR协议。Run公开消费与launch全域/selected model/default/SystemConfig/Gateway-purpose/CLIEditor及正常业务验收继续开放，不能据本阶段259技术测试宣布全域完成。

## 阶段31：Run 读取、创建与重试领域消费者

### Optimized Prompt · 2026-09-15

先读实际75目录、workflowRunDto/CreationDto/Service/Semantics与原WorkflowRun/RunService/application/public入口，复用完整28字段纯模型与原错误映射，不用旧summary投影。消费已发布workflow-run.read/create/retry（read实际hash读取后写入，create531d41a45a7a745b120a83c57a88bdb0cf40ffcdc52d245d56bc0d372342eb08/retry01c72910ed713ce10c86e03c426f98549c81d1991cbaf05415b6bbcdbb8e9bd7），均identity/unified两项exact schema，公开OAuth scope分read/write，不接受server grant。

保留三个公开入口的原200/201、28字段、nullable provenance、Pydantic string strip与datetime JSON；strict wire DTO要求全部nullable字段显式存在，整数是正安全整数、原key最多255 codepoints、输出时间最多6位且aware/lifecycle复用原模型。Create输入仅server Workspace+PF/token/key+三项requirednullable source，allnull或完整tuple；source time沿原datetime.fromisoformat解析/精度截断再传输，Dream不计算token/hash/fingerprint/新RunID、不拆Admin原子事务。Retry只发送原owned Run lookup/PF/token/new key，source由Admin原Run推导，无preread/runtime dispatch。回复匹配canonical actor/Workspace/业务key/读取ID或retry_of；同key复用可能来自另一个同语义PF，不错误要求reply PF ID等于新输入。

default Workspace操作仍未注册，这三个入口暂保留_story_workflow_current_user生产SQL，tests显式注入default loader并fence领域旧service/PG；不报整个route无PG。坏Run路径（包括前后空白）保持原Run-not-found registry404，不把DTO trim变成授权读取。公开写仅scoped复用SafeRequestValidationRoute隐藏token/source私密validation，不改变cancel/guidance/confirmation/launch/其它route。复用原八项业务error mapping到共享纯error_registry helper，原application静态方法调用同helper保持原fallback；只在实际code/status匹配且非unknown时投影旧payload，其他Admin错误保留safe UUID/unknown，不猜新alias。

Unknown write不重发，不推断rollback；显式generic原两态receipt同UUID/同operation/input读取，完整bounded result再做actor/Workspace/key/retry匹配。原PF三态reader与所有其它通用transport保持。actual production FastAPI/OAuth/client/DTO+MockHTTP、所有Run statuses/nullable/微秒、source/255 astral keys/time/capability/identity/error与receipt/无retry测试，相关原Run技术合同回归；actual规范/hash/closed shape/原model/API其它functions/资源RunnerFilesAST与docs/README/history验证。正常PG/实体/模型验收仍由主协调，默认/SystemConfig/selected model/Gateway-purpose/CLIEditor/全域Repository等继续开放。

阶段31实际结果：read SHAcaf17aab8bb1bdf49fa7a38e8f4ff4e257246adcb3f8c4dea6ea8b5991328f32以及create/retry两项SHA、两项exact schemas与全部closed DTO shape按实际目录通过；28字段全部required（包括nullable）、原纯模型lifecycle/time JSON保持。Create reply source tuple及aware time也匹配原input；同key原PF ID不强制改为新PF。Source parser沿原datetime.fromisoformat，再isoformat传输，不计算新hash/token。显式两态receipt先验证operation/input类型，完整result actor/Workspace/key/retry/source校验，无auto resend/resume或新增公开receipt路由。

原application八项mapping AST值逐项相等，fallback原AGENT_EXECUTION_FAILED/422；原error registry/payload/classes与其他application类/方法保持。三个公开路由仍依赖原default Workspace SQL，actualOAuth/HTTP技术fixture仅在tests显式注入loader。其他router functions/classes、PF两读取消费/generic receipt/资源RunnerFiles/原database与models字节或AST保持。补齐现行Run设计、affected folders与README mirrors，不改历史原文。

primary fresh命令：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_run_routes.py backend/tests/test_workflow_run.py backend/tests/test_admin_preflight_execution.py backend/tests/test_admin_preflight_routes.py backend/tests/test_admin_data_boundary.py backend/tests/test_admin_request_auth.py backend/tests/test_story_workspace_api.py
# exit 0; 317 passed,1 skipped in 5.11s
# skip is existing SQLite concurrency test: legacy SQLite cannot model PostgreSQL row-lock concurrency; superseded by owned-PG contract
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage31-contract-check.py
# exit 0; actual75/client58,3 Run hashes/2schemas/28closed required fields/8original mappings; other routers/application/error registry/PF receipts/Runtime/Files unchanged
env PYTHONDONTWRITEBYTECODE=1 /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 42files/405links/305inventory,3 original history SHA,README parity,6Mermaid count/failures=[]; no render
env PYTHONDONTWRITEBYTECODE=1 /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-current-sql-scan.py
# exit 0; 298scanned,48SQL modules/513literal candidates,16drivers,35legacy imports/121helper Calls,parse_errors=[]; not whole runtime reachable proof
git diff --check
# exit 0; no output
```

317/1是source reply/type guard补充后的fresh结果；之前315/1不替代它。原SQLitefixture只是技术回归，PG row-lock/Run正常链路不由这项skip或MockHTTP证明。本轮普通服务/PG/账户/模型/Browser/Runtime未调用；不修改Admin源码、SDK/Runtime pins或TMPDIR。默认Workspace/SystemConfig/selected model/purpose Gateway/CLIEditor、Run其它持久化与所有剩余SQL域继续开放。

## 阶段32：已注册 launch metadata 类型消费者与原 source seam

### Optimized Prompt · 2026-09-15

实际75中source.ensure/dispatch.claim/finish已注册，公开隔离验收仍在进行，不能称其已完整通过。先按真实DTO/registry/Service/原application/infrastructure准备独立可复用消费者与原source Protocol adapter；不把尚未传递OAuth actor的旧endpoint假装接线完成。原endpoint只接actor/Workspace字符串，prepare、Voice读取、failure recorder及runtimeprovision仍SQL，当前任务记录这个身份与capability缺口，不消费未注册default Workspace。

DTO复用现有StoryWorkspaceDreamLaunchCommand/Context字段metadata与validator，避免复制业务字符上限；source输入无Boundary whitespace，不normalize，nullable Agent required；context全10字段required nullable Agent、immutable/positive safeint、原Pydantic trim。UUID按实际Zod元数据pattern，claim为dlc_32hex，claim真假union与RootModel保持wire top-level不包root；raw parts_json/metadata_json不回显repr，标准JSON解析有限object/array，不复制运行时parser或重序列化。两个schemas与三项实际hash精确匹配，所有新域OAuthwrite，无user override/delegation控制通道。

source adapter只接服务端immutable AdminRequestActor/client，保持原ensure_source Protocol签名；校验actor与原callsite给定source IDs/fingerprint，在实际Admin回复上匹配，不发送这些caller provenance。调用经worker thread，unknown不重发或继续PF；原application conditional Agent fingerprint/UUIDv5/先prepare后source→PF/Run流程源码不改。Claim消费者对原Source/Context全字段、Run/thread/message、当前actor/Workspace与原instruction parts/runtime metadata做匹配；不调用Voice/Runtime、不在Dream生成claim/status/lease或检查TTL。Finish只发issued claim+accepted bool并匹配Run/source，Runtime/Bash/Files/LKG仍原路径。

原generic两态receipt显式同UUID操作读取，boundedsource/claim/finish重做对应检查；absent不推断rollback，claimtrue stale交Admin409，不自动重claim/resume/dispatch，保留原UUID未知结果。注册到请求owner但生产endpoint尚未选择adapter，源清单必须说typed/seam技术准备，原launch SQL未迁移，不能说公开整条无PG/normal launch完成。

通过实际client/DTO/HTTP和原application usecase seam测试，校验schema/hash/闭集字段、source正常/重放/私密错配、no-agent fingerprint原callsite、claim真假/10context/raw JSON/status/issued ID、finish accepted/stale result、sameUUID receipt/timeout/no resend与OAuth owner。相关PF/Run技术回归、actual descriptor/原application/endpoint/builder/router/Runtime/model字节保持检查及docs mirror/history/链接清单。不开正常服务/PG/Gateway/模型/Browser，不改Admin、pins或TMPDIR。

阶段32实际结果：三actual SHA/两项exact schemas/input-output closed shapes（claimed tagged union无root包装）、原command metadata与validator函数复用、10 Context required字段通过。Source expectation只包含原callsite已有的三个来源事实，不构造假timestamp；adapter接服务端immutable actor并在worker thread调用HTTP。Unknown/错配停在原application source seam，无PF/Run/dispatch。Claim fullContext/current actor-Workspace/raw instruction/metadata与sourceIDs匹配，finish仅issued claim+accepted，generic两态receipt显式同UUID读取，stale409不reclaim。生产endpoint/builder尚未选择这些adapter，source/claim/finish SQL仍保留；不将类型准备称作全生产入口迁移。

源码导入检查曾因Pydantic discriminator字段before validator限制和bound classmethod validator复用方式返回exit1；先改为RootModel前置flag检查与原validator.__func__复用后，导入/raw instruction检查exit0，再开始完整技术测试；没有弱化validator/断言或修改普通服务。初次六文件281passed exit0之后补source unknown停PF前/full context值/非有限指数用例，fresh为287passed。

主协调新要求的资源全系统gate：已有resource_policy.py/Admin typed provider/read background scope符合目标，源码保持，不制造改动。补跑现有policy/admission/sdk_env三文件，覆盖LKG/revision回滚与动态替换、safeint/组合内存精确边界、后台callback异常隔离、admission资源顺序/既有lease/后续acquire与SDK env约束；off-turn provider/Runtime主路径源码与原composition保持的证据按源码检查记录，不把67测试当作完整普通账户/远程模型/SSE验收。

primary fresh命令：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_launch_metadata.py backend/tests/test_story_workspace_dream_launch.py backend/tests/test_admin_run_routes.py backend/tests/test_admin_preflight_execution.py backend/tests/test_admin_data_boundary.py backend/tests/test_admin_request_auth.py
# exit 0; 287 passed in 3.35s; no failures/skips
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage32-contract-check.py
# exit 0; actual75/client61,3actual launch hashes/2schema/closed DTOs,original constraint+validator reuse/10required Context; original application/endpoint/builder/router/Runtime/Files/provider unchanged
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_claude_agent_resource_policy.py backend/tests/test_claude_agent_admission.py backend/tests/test_sdk_env.py
# exit 0; 67 passed in 0.73s; existing provider unchanged
env PYTHONDONTWRITEBYTECODE=1 /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-doc-check.py
# exit 0; 41files/410links/275inventory,3 history original SHA,README parity,6Mermaid count/failures=[]; no render
env PYTHONDONTWRITEBYTECODE=1 /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-current-sql-scan.py
# exit 0; 299scanned/48SQL modules/513literal candidates/16drivers/35legacy imports/121helper Calls,parse_errors=[]; static candidates,not full reachable runtime proof
git diff --check
# exit 0; no output
```

文档checker仍显式检查当前Run/launch设计与历史，backend folder动态范围随阶段改动变化，41/410/275不表示完整repository Markdown普查。Source importer/后台helper/Repository/pool/stdio与全域startup/health/SystemConfig/selected model/GatewayCLIkey等仍开放。launch75主协调报告首轮actor_id query层级harness预期错，实际400 USER_OVERRIDE_FORBIDDEN正确且首Source已提交/其余37待执行，Root未重跑或判业务缺陷。default Workspace候选21仍未注册。本轮不调用普通PG/账户/模型/Browser/Runtime、不改Admin/pins/TMPDIR，完整launch/普通数据与Admin可见账本验收仍由主协调完成。

### launch75 窗口释放后的只读证据核对

收到主协调释放75通知后，Root读取 `/private/tmp/ink-auth-migration-validation/launch75-*-command-receipt.json`，仅输出command/cwd/exit code与聚合计数，不读取凭据或输出正文，不执行DB/Runtime。实际命令均在Admin729f；`node --import tsx tests/integration/adminDreamLaunch.contract.ts` 原首轮exit1保留，continuation exit0记录cases37/skipped_accepted_cases1/prepared38/receipts21/assertions974/protected_tables17。`node --import tsx /private/tmp/ink-auth-migration-validation/launch75-atomic-recovery.mts` exit0，assertions308/selected_faults11/commit_losses3/private_keys_exported=false。`node --import tsx /private/tmp/ink-auth-migration-validation/verify-launch75-preservation.mts` exit0，assertions19/unrelated_full_relations8，scope为SELECT-only/designated new claim metadata changes/no original reset。

主协调另报告cleanup11×2删除、原source/full8tables/旧rows保留正确，本轮仅核对上述三个aggregate命令结果，不称Root重跑故障、清理或完整38一次通过。注册75组件技术gate已释放；原旧endpoint OAuth actor传递与Source/dispatch选择、prepare/Voice/failure、default/SystemConfig/selected model/Gateway/CLI及正常业务仍pending。76 Workspace薄Ingress/原GET尚未实际注册，不提前消费。原阶段32生产代码及287/67测试结果不变，只同步当前设计/状态。

### SystemConfig 当前调用点与身份回报

[生产清单](dream-admin-data-inventory.md#systemconfig-生产读取与身份复查--阶段32后)已按实际 AST 和身份 DTO记录：六个直接 get、一个 save、三个 getter 注入引用及两个 reader 引用。公开设置/Chat/Workspace复用已有immutable OAuth actor；service配置读取可在新 domain 明确支持后复用 Thread/Run server-persistence，内部 dispatcher 仍缺 owner；Editor stdio 不直接读取配置，也无“Editor server-persistence” purpose。原 helper 合并未知 keys，Preferences 五字段不得冒称覆盖。此次只读分析不改 getter、异常行为、Runner 或权限接口。

## 阶段33：已注册76默认 Workspace 消费者

### Optimized Prompt

核对 Admin 实际 76 项注册 artifact、operationRegistry、公开生产 named ingress、原 GET receipt、identity/unified exact schemas 后，复用 AdminDataClient/DomainOperation/StrictDTO 和共享 immutable OAuth actor，新增空输入的 workspace-default.ensure typed consumer。原文本 Workspace ID 原样返回，不强制 UUID、长度或 trim；Admin 独占 oldest-owned 的 created_at ASC/id ASC、账户锁、默认名称/settings、UUID、事务和 current-owner receipt。将 `_story_workflow_current_user` 的默认读取改为该 named operation，保留现有服务器 workspace_id 复用分支；独立 internal agent-output 的默认 SQL 仍保留并列明。注册写操作要求 dream:write，GET Run 等隐式 default 初始化若只有 dream:read 必须明确403，不猜新 readonly 合同、不扩权。PF GET 独立 read 继续无 default 初始化。未知提交只保留原UUID、显式读取原两态receipt，absent 不重发；自动初始化失败不得继续 PF/Run/launch。

在 backend/tests 中调用实际 FastAPI/shared OAuth/client/DTO，禁止覆盖默认 loader；MockHTTP仅替代 Admin transport，旧 DB/旧 service fenced。覆盖真实 helper→default→PF/Run 的公开生产路径、原 status/full response、空输入/原文本ID、401/403/503、schema/hash 缺失、未知结果 stop-before-domain、同UUID receipt/no resend。保留独立 PF/Run合同测试的 DI fixture用于自身领域验证。更新受影响文件header/folder、现行设计稿/README/清单/本计划。AST核对其它Story routes/Runtime/SSE/resources/shared FS/原数据库实现字节保持；运行有意义的 bounded suite、Markdown库存路径/history/README及diff检查。全部属于 provider-free 技术验证，不运行正常服务、真实PG或模型，不改 pins。

### 阶段33实现与独立技术回执

Admin新同步与Root实际源码核对均确认76注册：workspace-default.ensure empty input、legacytext输出、OAuth-write-only、identity/unified两schema、actor-init先于receipt与originalGET empty digest/all-null scopes/current owner。Root核对operationRegistry、named ingress和receipt真实注册；producer报告20/20 ingress/originalGET、旧75 FULL/delegation/PFreceipt字节不变，首次隔离public/concurrency/fault尚待主协调，不据这些信息声称真实业务通过。

实现复用 workspace_data module、shared DomainOperation/StrictDTO/require_workflow_capabilities/client 和immutable actor。公开Workflow默认helper中get_db移除，服务器已有workspace_id复用；default需dream:write，read-only且需初始化时403停止，PF GET独立read。ensure raw text ID无UUID/trim/额外长度限制；explicit generic两态receipt保留原UUID、不初始化或重发。internal agent-output原defaultSQL、其它Story functions、Agent/Runner/Runtime/资源LKG/共享文件/TMPDIR和SystemConfig原实现保持。受影响folder/header、README/现行Auth/PF/Run/launch设计和当前源码清单同步。

原独立PF/Run套件保留default DI作为自身合同隔离；新增实际公开default-dependent套件无dependency override、fence DB/旧domain service，覆盖OAuth/client/empty default→PF202/Run200-201完整模型、legacy text/原serverworkspace分支、readscope/401-403、schema/hash失配、初始化unknown/rejection停领域调用前、同UUID原receipt两态/闭集/identity/no resend。首次七文件suite **exit1，336pass/1fail/7.19s**，失败为新测试误期待Timeout503，实际shared HTTP parser按既有合同返回504；保留此回执，修正测试状态预期，不改生产error handler。加原workspace分支与bad receipt五case后fresh七文件suite **342pass/7.11s，exit0，无失败/skips**：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_default_workspace.py backend/tests/test_admin_preflight_execution.py backend/tests/test_admin_preflight_routes.py backend/tests/test_admin_run_routes.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_data_boundary.py backend/tests/test_workspace_router.py
```

- `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage33-contract-check.py` **exit0/PASS**：actual76/client62/default1/two exact schemas、实际SHA与input/output schema闭集逐项相同（原text min1，无修复）、registry/named ingress/originalGET注册；原serverworkspace branch、其它Story functions/Thread consumer methods、原Actor/Auth methods保持，剩余497 tracked backend Python字节或两测试header-only AST不变。SystemConfig domain仍未注册；normal_business_acceptance=false。
- `python3 /private/tmp/dream-admin-current-sql-scan.py` **exit0**：299模块/48 SQL-bearing/513literal/16driver-persistence imports/35legacy imports/120directhelper/parse_errors=[]。源码候选scope声明不变；相对阶段32仅defaulthelper一次get_db消除，残留仍开放。
- `python3 /private/tmp/dream-admin-doc-check.py` **exit0**：41files/431local links/297folder entries/failures=[]、三历史原文SHA不变/README heading parity=true，6 Mermaid仅数量检查，未声称渲染。
- `git diff --check` **exit0，无输出**。正常本机Google/账户/PostgreSQL/模型/CLI及Admin可见Run/账本验收未执行；Runtime/SDK pins和既有服务未触碰。

SystemConfig身份回报详见[精确生产清单](dream-admin-data-inventory.md#systemconfig-生产读取与身份复查--阶段32后)：公开OAuth actor与Thread/Run server-persistence可按未来发布domain明确支持分别复用；Editor只具有editor-stdio/editor:read-write，未直接读取SystemConfig。internal dispatcher没有server owner、新domain未发布时不得以user ID/service key/新自签JWT补充授权。

- `python3 /private/tmp/dream-admin-system-config-calls.py` **exit0/PASS**：6direct getter/1saver/3getter injection/2reader references，Editor与ContextBuilder direct getter=false/database_calls_executed=false；输出仅file/function/line/reference，未导入业务module或执行数据库调用。未来替换必须明确处理旧service skipping和Workspace初始化defaults，Admin unavailable不得用空对象悄悄继续；此分析未改旧行为。

### Workspace76 新回执只读核对

Root只读 `/private/tmp/ink-auth-migration-validation/workspace76-public-command-receipt.json`：`node --import tsx tests/integration/adminWorkspaceDefault.contract.ts` exit0/PASS，provider-free default Workspace 14cases/22originalGET/347assertions/17protected tables，initial same/distinct-original concurrency=true、actual entire original source=true。当前同目录atomic recovery command：`node --import tsx /private/tmp/ink-auth-migration-validation/workspace76-atomic-recovery.mts` exit0/PASS/90assertions，workspace_insert/receipt_insert/audit_insert三故障各503、whole17 full byte exact rollback/cleanup PASS；actual final COMMIT lostresponse一次，initial503/originalGET200/replay200、oneWorkspace/oneReceipt/oneAudit，actual original source=true。preservation command：`python3 /private/tmp/ink-auth-migration-validation/run-verify-workspace76-preservation.py` exit0/PASS/159assertions，125original tables全row保留/17first-preparation tables保留、5positive originals currentowner/digest/scopes、active owned fault functions0。

以上为实际安全command receipt汇总，不重跑数据库/不修改producer冻结窗口；非正常账户/model/Runtime验收。Admin同步的prepare oracle23complete vectors只按source-only证据记录，捕获catalog/current-scope/frozen/binding，不代表实际SQL/Gateway/FS/provisioning；named prepare API未发布。failure候选尚未注册。SystemConfig producer候选由协调主任务独立推进，本任务只负责Dream精确身份回报及实际发布后的消费者，不新增另一Admin provider。

## 阶段34：已注册公开 Workflow Run cancel

### Optimized Prompt

复用 run_data 的原28字段RunDTO、typed client、exact identity/unified gates与共享current OAuth actor，将公开 `/workflow-runs/{id}/cancel` 从旧application SQL改为实际 workflow-run.cancel。先对照旧cancel_run/transition_run和Admin command ingress/output schema/原generic receipt，保留原request reason的Pydantic trim/default/min1/max500及 `user_cancelled:{request.reason}` 编码，输入只含服务器Workspace/路径Run和requirednullable reason_code（wire无新trim或业务边界）。Admin承担状态转换、terminal replay、Run/history/receipt/audit事务及当前owner/冻结source校验；Dream不新增状态算法、clock、资源admission/lease或Runtime执行。Reply必须匹配canonical actor/Workspace/路径Run、cancelled状态，复用完整原模型。Bad path仍原Run-not-found404，ILLEGAL_RUN_TRANSITION/其它原八业务映射保持；共享safe request validation scoped到cancelPOST，raw reason/token不回显。

公开cancel只接受OAuth dream:write，复用已注册76 default helper，原serverworkspace分支/default→cancel顺序保持。Unknown保留原UUID、显式原generic两态receipt，absent不重发；committed重新检查完整bounded result，不用当前状态覆盖原结果。将cancel注册到request owner，其余Run三op capability/DTO/key/source/PF replay规则保持。其他Story函数、旧application/WorkflowRunService/模型、Agent turn/resume/cancel/SSE、Runner/资源/共享FS/TMPDIR、SDK/Runtime pins字节不改。

Tests调用公开生产FastAPI入口、实际default loader/sharedOAuth/client/DTO，MockHTTP只替代transport；fence旧DB/domain service，覆盖原200/28fields/时间、default/rawreason/默认reason、重复cancel、非法transition/404/401/403/schema/hash、reply错配/unknown stop/no retry、同UUID两态receipt。补充独立Run和完整default suite回归；不改技术fixture为生产fallback、不跑正常DB/models或扩大provider窗口。同步受影响header/folder/当前Auth/Run/PF/README/库存/计划，AST对照唯一改变函数与原字段约束/错误映射，其余业务source保持；运行有意义bounded suite、actual contract schema/SHA、Markdown inventory/history/README和diff验证后只提交本阶段明确拥有路径。

### 阶段34实现与技术回执

复用run_data增加cancel DTO/actualSHA/第四Run operation、原28字段返回和显式原两态receipt；reason_code required nullable/raw str/repr排除，无新业务边界。公开cancel采用原Run scoped安全validation与actual `_story_workflow_current_user` default依赖，保留原reason模型及 `user_cancelled:{request.reason}` 编码，reply匹配canonical actor/Workspace/路径Run/cancelled状态，原200/28fields/时间/八业务errors/404保持；未执行Agent取消或Runtime。共享完整default fixture仅在tests增加cancel结果/原receipt operation选项与旧factory fence，新生产入口测试无default/domain-handler override。

六文件fresh suite **253pass/1skip/4.87s，exit0**：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_run_cancel.py backend/tests/test_admin_default_workspace.py backend/tests/test_admin_run_routes.py backend/tests/test_admin_preflight_execution.py backend/tests/test_admin_request_auth.py backend/tests/test_workflow_run.py
```

唯一skip为原 `WorkflowRunConcurrencyTests.test_concurrent_same_scope_token_and_key_create_exactly_one_run`：legacy SQLite不能模拟PostgreSQL行锁并发，superseded by owned-PG contract；不据此报告PG真实并发验收。新cancel测试覆盖actualdefault→cancel/原reason默认trim/max500/rawwire/28fields/重复producer结果/八errors/404/OAuth/schema/hash/timeout504/错配unknown/同UUID两态receipt/committed重校验。

- `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage34-contract-check.py` **exit0/PASS**：actual76/client63/Run4、cancel input schema闭集逐项相同/输出与原read28schema全对象相同/two schemas/所有actual canonical SHA匹配；原reason JoinedStr与request constraints AST相同，旧Run aliases/三op assign/原28class与CRUD methods在显式cancel branch之外保持；其它Story functions/原Actor/Auth AST保持，497其它tracked backend Python字节不改。Normal acceptance=false。
- `python3 /private/tmp/dream-admin-current-sql-scan.py` **exit0**：299modules/48SQL-bearing/513literal/16driver/35legacy imports/120directhelper/parse_errors=[]；声明scope内残留候选仍开放，不当作全可达SQL清零。
- `python3 /private/tmp/dream-admin-doc-check.py` **exit0**：41files/434links/298folder entries/failures=[]，三历史原文SHA/README heading parity保持，6Mermaid只查数量未渲染。
- `git diff --check` **exit0/no output**。受影响header/folder/README/现行Auth/Run/库存同步；没有正常DB/服务/models/CLI、资源/TMPDIR或Runtime/SDK pin操作。

主任务已明确继续其余两个current-user默认resolver；本任务定位为 deck_plugin_binding._deck_current_user 与 deck_plugins._deck_plugin_current_user，下一阶段统一复用既有typed default consumer。后者额外SELECTrole尚需明确现有profile合同作用域/输出校验，不使用ID当凭据；后台和internal agent-output的原默认helper属于不同生产事务入口，不将公开ensure冒用为事务替换。SystemConfig producer候选由协调主任务负责，本任务精确身份表已写库存，实际published domain之后再消费。

## 阶段35：三个公开 current-user 默认 Workspace resolver

### Optimized Prompt

按主协调明确要求把 StoryWorkflow、Deck binding、Deck Plugin 的公开默认Workspace resolver统一至已验证 workspace-default.ensure。复用既有workspace_data/client/DTO/immutable OAuth actor和共享 invoke_admin_operation，在routers/deps抽取现有Story helper的一次逻辑实现；保持服务器workspace_id复用、OAuthwrite-only、两exact schemas/实际hash、原textID/default-before-domain、unknown原UUID/显式原GET/no resend。三个wrapper调用同一helper，不在public resolver打开DB；其它domain DB dependencies/后台和internal输出事务仍单独追踪，不用公开ensure替代其事务。

DeckPlugin resolver额外role SELECT复用现有 AdminRequestAuth.current_profile（profile合同已注册、原ID/rawrole与scopes），在已有服务器role为空时明确OAuth dream:read、currentProfile回复canonical ID匹配后取role；原serverrole非空继续保留，不猜role alias，不改变_permissions/_require_permission/_workspace_request或Admin管理边界。Profile unavailable不使用user role fallback，安全status/code/requestID；token仅write且需role projection按已发布readscope403，不扩权或把userID当credential。

对照实际现有DeckPlugin/binding public routes和test fixture，provider-free测试调用公开生产路由/sharedOAuth/default/profile client/DTO；Fake domain仅通过tests DI替代尚未迁移的业务provider，旧DB fenced，不覆盖current-user resolver，不复制route/parser/state machine。验证三个default wrapper公共default→业务顺序、已有服务器Workspace分支、raw text ID、profile角色/ID匹配/权限拒绝、scope/capability/unknown stop/no auto-retry；复用已通过PF/Run/default suites回归。AST比较除三个wrapper/sharedhelper外的原route funcs/classes、原权限check/DTO和其它Agent/Runtime/resources/FS/TMPDIR不改；actual operation63仍无新provider/schema/authauthority。同步headers/folders/currentAuth/PF/default/Deck设计库存/README和计划，检查Markdown paths/history/README与diff后仅提交明确拥有路径，不跑normal PG/models/服务、SDK/Runtime pins。

### 阶段35实现与技术回执

三个wrapper统一调用routers.deps.resolve_admin_default_workspace，body直接抽取阶段33typed Story算法，现有server workspace/dream:write/empty input/two schemas/raw text ID/unknown原UUID/停止domain流程保持。DeckPlugin role复用既有AdminRequestAuth.current_profile，明确dream:read/原profile spec/identity1/ID检查，server role非空复用，缺role读取失败不使用user fallback。原权限/scopes/request/业务routes/classes不改。DeckPlugin resolver全部SQL/database import移除；binding与Story只移除default依赖，剩余领域/后台/internal输出SQL继续追踪。

新actual公开Deck/binding套件不override三resolver/sharedOAuth/client/DTO，only remaining business provider在tests DI；旧DB fenced。共享default transport fixture扩展profile及explicit write-only token测试，生产模块无测试分支。旧binding domain fixtures明确override current resolver来隔离DTO/CAS，与新的actual默认/认证入口套件分别标注，匿名入口依旧真实auth拒绝。

首次七文件命令包括旧 `test_deck_plugin_admin_integration.py`，**exit1/243pass/1skip/1fail/5.72s**。新默认/角色入口用例全部通过；唯一fail是原 `test_install_list_and_readiness_use_real_materialized_plugin` 自动调用真实 `claude plugin validate` 返回exit2，在未改的PluginInstallService CLI安装harness中失败。此次确实发生这一次CLI validate调用，不报告为provider-free/真实model验收；不读取/复制normal凭据、不变更TMPDIR协议、不用失败判断新页面/API有缺陷，不重跑该真实CLIharness。原fixture tearDown清理其自有tmp/DB，Root不清理正常服务或其它Agent资源。

按本阶段目标重跑六文件provider-free命令 **242pass/1skip/5.19s，exit0**：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_deck_default_workspace.py backend/tests/test_admin_default_workspace.py backend/tests/test_admin_run_cancel.py backend/tests/test_admin_run_routes.py backend/tests/test_admin_preflight_execution.py backend/tests/test_deck_plugin_binding.py
```

唯一skip为原 `test_concurrent_compare_and_swap_allows_only_one_revision`：legacy SQLite不能模拟PostgreSQL行锁并发，superseded by owned-PG contract。新套件覆盖actualdefault→role→business provider、raw text ID/既有serverworkspace/serverrole、原user权限拒绝、profile scopes/DTO/ID/capability/error、不fallbackuser、初始化unknown停profile/domain前。此技术suite不声称PG并发/normal account/model/Runtime验收。

- `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage35-contract-check.py` **exit0/PASS**：实际artifact此时**77**/client63，新增dream-launch-failure.envelope仅观察注册尚未消费；default/profile两个已消费capability/版本/hash和two default/identity-only profile要求匹配实际registry。原Storytyped算法body直接复用、三wrapper各一shared调用/无SQL，existing profile rawrole/readscope/ID方法复用；其它routes/permissions/classes/deps保持，496其余tracked backend Python字节不变，background/internal原defaulthelper保留。
- `python3 /private/tmp/dream-admin-current-sql-scan.py` **exit0**：299modules/**47SQL-bearing/512literal/16driver/34legacy imports/118directhelper**、parse_errors=[]，相对阶段34减少DeckPlugin role SQL与两默认get_db；完整声明scope内当前SQL/legacy tables同步，未当作全可达SQL清零。
- `python3 /private/tmp/dream-admin-doc-check.py` **exit0**：42files/438local links/300folder entries/failures=[]、三history SHA原文不改/README heading parity=true，6Mermaid只查数量。
- `git diff --check` **exit0/no output**。受影响folder/header/README/currentAuth/PF共享默认/Deck canonical设计/库存已同步；没有正常DB/服务/model业务操作，Runtime/SDK pins/资源/TMPDIR源不变。

SystemConfig当前callsite/Thread或Run grant/Editor用途表仍在[精准清单](dream-admin-data-inventory.md#systemconfig-生产读取与身份复查--阶段32后)；Profile role使用公开OAuth，不把server-persistence/editor-stdio当作用途授权。协调主任务独立SystemConfig producer候选尚无已发布消费者合同。跨任务详细同步的既有自动审批拒绝未解除，结果写入本任务文件供复核，不重试发送或复制normal凭据。
## 阶段36：已注册 Run fail 与 failure envelope 消费者准备

### Optimized Prompt

对照 actual77 导出的 workflow-run.fail 与 dream-launch-failure.envelope，复用 run_data 原28字段模型和 launch_metadata_data 的 client/two exact gates/显式 original receipt，增加闭集输入、原始失败文本、完整回复关联校验。fail 使用原服务器 Workspace/Run、required failed_step/error_code 和 requirednullable reason_code；三项失败文本不增加 trim、长度或编码规则。Admin 同 failed replay 返回原 Run，所以 Dream 只验证 actor/Workspace/Run/failed 状态及原模型，不强制历史失败参数等于本次参数。failure envelope 只发送 Workspace/Run/error_code，回复匹配原 Run/error 与服务器持有的 nullable source IDs，保持 raw IDs、bool 和 null；不得发送 source/context/metadata/codec 路径或改写 metadata。

原流程先提交 Run FAILED，再以独立事务记录消息 failed/error/removeclaim。两个 typed operation 不合并事务、不推断是否提交、不自动重试；unknown 保留原 UUID，原 GET receipt absent 不触发重发，committed 重新关联检查。注册到现有 request owner 元组仅代表具备消费类型，原 launch builder/endpoint/dispatcher/failure recorder 尚无完整 Admin owner，不以 actor_id、共享 service key 或伪造 grant 接入后台，不宣称生产 SQL 已迁移。Runtime purpose/current Thread+Run 与 OAuth original GET 限制由已发布 Admin 边界校验；不新增 Dream 控制通道、状态算法或 runtime grant。

限定代码所有权为两个现有领域模块与 request_auth 元组共享 header；新增 provider-free transport 测试复用旧 Run fixture 数据与实际 client/DTO，覆盖原失败 replay、原始文本、full source/reply mismatch、capability/hash、HTTP errors、unknown stop 和两态原 receipt，fence SQL。保持旧 launch/Agent/SSE/资源/lease/Runner/FS/TMPDIR/SDK pins 原字节；不调用正常 DB/model/CLI、不改 producer 冻结窗口。同步当前设计三基础/状态/失败/验收、headers/folders/README/库存与实际 technical receipts，运行 bounded pytest、actual contract/SHA、源码保护、Markdown inventory/diff 检查后只提交明确拥有路径。
### 阶段36实现与技术回执

两个现有domain module新增fail/envelope DTO/actualSHA、完整回复关联和原generic两态receipt；共享request owner原AST不改，只复用扩大后的operation tuple。Run fail只验证原actor/Workspace/Run/failed模型，same-failed历史详情可不同于本次raw失败参数。Envelope的raw nullable source IDs存于服务器immutable expectation，不发送caller source/context/metadata/codec；updatedfalse保留，true不能确认null source。Production launch builder/endpoint/dispatcher/failure recorder没有接线或字节修改；没有减少SQL库存、调用CLI/model/正常数据库或调整producer冻结资源。

首个专用文件76passed/.81s/exit0；首次七文件回归375passed/2failed/4.24s/exit1，旧launch receipt参数矩阵遍历新第四operation却仍传source.ensure DTO，修复其failure DTO/source branch。第二次373passed/4failed/4.19s/exit1发现该测试缺新导入，修复测试import；没有放宽production校验。增加missing source与malformed original receipt覆盖后，fresh命令：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_launch_failure.py backend/tests/test_admin_launch_metadata.py backend/tests/test_admin_run_routes.py backend/tests/test_admin_run_cancel.py backend/tests/test_admin_deck_default_workspace.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_data_boundary.py
```

结果386passed/4.26s/exit0，无failed/skipped。只用实际consumer/client/DTO与MockHTTP，旧SQL fenced；没有重跑阶段35旧CLI integration（其原validate exit2前置失败仍保留），不冒充正常模型业务回执。

`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage36-contract-check.py` exit0/PASS：actual77每个自SHA、fail input/envelope input+output完整schema相等（仅去title/$schema/$defs、解ref并排序required/union）、fail full output与原read28 schema完全相同、两exact要求；client65/Run5/launch4、existingdomain方法移除唯一新增branch后AST相等、requestownerAST相等、499其它trackedbackend Python原bytes保持（含production launch/资源/Runner/FS/TMPDIR）。

`python3 /private/tmp/dream-admin-doc-check.py` exit0：41files/445local links/277folder entries/failures=[]，三历史SHA保持、README标题一致、6Mermaid只计数未render。`python3 /private/tmp/dream-admin-current-sql-scan.py` exit0：299modules/47SQL-bearing/512literal/16drivers/34legacy imports/118helper、parse_errors=[]，与阶段35同声明范围，不把source candidates视为完整生产可达证明。最终docs/diff检查另以提交前实际结果记录。

剩余：后台immutable owner链路与原source/claim/finish/failure生产SQL、完整prepare/Voice/Run start/其它domains、SystemConfig发布后actualcallsite迁移、GatewayCLIkey/CLIEditor、正常PG/Admin可见Run/账户/model验收及77primary故障/COMMIT-loss验证。Goal仍未完成；不升级SDK/Runtime pins、不部署/重启正常服务、不写外部任务消息。
提交前最终文档检查 `python3 /private/tmp/dream-admin-doc-check.py` exit0：41files/446local links/277folder entries/failures=[]，historySHA/README标题保持；`git diff --check` exit0。只暂存本阶段15明确拥有路径，不包含其它任务docs/.folder、docs/exec/.folder、docs/stage/.folder、验证目录或pnpm缓存。
## 阶段37：Workspace76 已实现消费者独立复核

### Optimized Prompt

继续原全量迁移goal，本轮只复核已释放Workspace76，不重写已正确的AdminWorkspaceData/resolve_admin_default_workspace或三个wrapper。独立机械验证交给mandatory Luna既有runner，精确cwd与provider-free focused pytest selection，只创建明确命名stage37/luna raw receipts/log，不调用正常PG/CLI/model/browser、不改producer77冻结或未注册SystemConfig/Reflection接口。原runner此前usage-limit errored，本轮按主任务要求发出一次同目标followup并等待真实回执，不reset credit/换模型/伪称已执行。

主Agent并行只读源码：校验实际76strict empty/input+raw ID/schema/hash、currentcanonical/OAuth身份路径、original request GET/no auto retry；复核Admin已有created_at ASC/id ASC/null处理代码和Dream消费者仅relay原ID、不复制排序；记录实际公开路由及测试DI边界。以当前HEAD8447a80a为保护基准，3wrapper/文件权限调用顺序/TMP+FS源码不变；复用当前scanner snapshot列所有47 SQL候选模块/16driver/34legacy，不重复已有广域测试或据rg声称完整关闭。Story internal agent-output在原整体事务内的default SELECT/INSERT和store_agent_story_output写入继续pending，没有对应Admin完整业务API，不拆成跨事务ensure。仅在真实Luna命令/cwd/exit/raw output可读后接受独立验证；保存明确source artifact/闭环文件/剩余调用列表/cleanup/正常验收缺口，并继续原goal下一发布缺口，不将turn结束当goal完成。
### 阶段37独立回执与实际闭环边界

既有mandatory Luna runner本轮followup真实执行完成。Root已实际读取[command receipt](/private/tmp/dream-admin-stage37-workspace76-validation/luna/command-receipt.json)、[stdout](/private/tmp/dream-admin-stage37-workspace76-validation/luna/pytest.stdout.log)、[stderr](/private/tmp/dream-admin-stage37-workspace76-validation/luna/pytest.stderr.log)，确认exact argv/cwd/exit0、wall2541ms、原stdout `66 passed, 18 deselected in 2.12s`，stderr空。未声称不可观察的Fast mode元数据。命令为：

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_default_workspace.py backend/tests/test_admin_deck_default_workspace.py backend/tests/test_workspace_router.py -k 'default or original_workspace_text or original_uuid_two_state_receipt or receipt_identity or readonly_preflight or initialization_rejection or missing_exact_capability or admin_thread_reply_identity_and_dto_fail_before_mode_or_files or admin_thread_timeout_does_not_retry_or_access_mode_files or admin_schema_and_thread_hash_are_required_before_file_access or foreign_thread_is_hidden_before_workspace_probe'
```

runner报告首个receipt wrapper使用macOS不支持的 `date +%s%3N`，writer失败；换Python clock后同argv重跑并返回有效原命令回执。该wrapper失败不作为API缺陷。未生成pyc，只有专属output保留；使用synthetic MockTransport/显式fixture/临时workspace，没有正常PG/模型/CLI/network/账户/服务操作，未清理其它资源。18deselected是此focused selection之外，旧Story事务和其它真实business provider没有验收。

Root source-only脚本首轮exit1：误填不存在的backend/claude_agent/runner.py、gitshow子命令128；通过rg file inventory找到实际libs/claude_agent_kit/server/{agent_runner,workspace,sdk_env}.py后只修验证脚本。fresh `python3 /private/tmp/dream-admin-stage37-workspace-source-check.py` exit0/PASS/164ms，[原receipt](/private/tmp/dream-admin-stage37-workspace76-validation/source/command-receipt.json)/[stdout](/private/tmp/dream-admin-stage37-workspace76-validation/source/source.stdout.log)/[stderr](/private/tmp/dream-admin-stage37-workspace76-validation/source/source.stderr.log)均实际读取；[完整source closure与47SQL/16driver/34legacy候选列表](/private/tmp/dream-admin-stage37-workspace76-validation/source/workspace76-source-closure.json)。源码检查不执行DB/模型，stderr空。

实际default闭环文件为routers/deps.py的单shared resolver、story_workspace.py::_story_workflow_current_user、deck_plugin_binding.py::_deck_current_user、deck_plugins.py::_deck_plugin_current_user与services/admin_data/workspace_data.py：三wrapper各恰好一次shared调用，无oldDb/default execute；empty DTO/currentcanonical/OAuthwrite/rawID、wrong reply与503/noDBfallback由actual public consumer tests覆盖。Deckbinding/plugin的末端领域provider由test DI替代，故只接受resolver/role边界，不宣称该业务domain SQL已关闭。Profile复用既有current_profile canonicalID/readscope；不新增role fallback。

文件权限闭环为workspace.py::{read_workspace_file_content_endpoint,download_workspace_file}和AdminWorkspaceData.exists_owned：Thread ownership先于Mode/path/FS，错ID/错actor/malformed/timeouts/missing schema/hash/foreignThread不进入Mode或文件probe。Source artifact含10文件与8447a80a字节比对，实际Runner/workspace/sdk_env及旧Story事务保持；这不替代正常Bash工具的TMPDIR真实回执。Admin默认选择保留原 `created_at ASC, id ASC LIMIT 1`，Drizzle `.orderBy(asc(created_at),asc(id))`未加NULL/coalesce分支；Dream只relayID，没有复制排序或NULL算法。76已释放public14cases/22originalGET/347assertions原command receipt只读，不重跑数据库。

仍生产调用SQL：POST /api/story-workspace/internal/agent-output在story_workspace.py::receive_agent_story_output仍调用agent_integration.py::get_or_create_default_workspace（SELECT/INSERT）并执行原store_agent_story_output整体事务；没有完整Admin Story output业务API，不能拆成无一致性的ensure调用。旧background/internal default、launch/Agent integration与其它47SQL候选模块、16drivers、34legacy imports保留；当前scanner snapshot仍299/47/512/16/34/118、parseerrors=[]，完整scope与路径见artifact/库存，不按一次rg或已注册count宣布全迁移。

下一发布缺口只读定位：server.health当前已无DB，是原liveness投影，不制造代码改动；startup_database仍init_db且剩余生产SQL依赖pool，不能先关闭造成运行时失败。Deck.create/default三API已注册，但default plugin evidence仍由旧SQL安装清单+真实FS/CLI verifier取得，尚不能冒用browser evidence。Preferences.default-voices实际只读config.VOICE_ARCHETYPES，已无DB；voice-analysis.list对应的旧load_voices_from_user_decks没有其它生产Python callsite，不制造替代实现。继续定位到ClaudeAgentService._persist_assistant_turn仍直接SQL，而公开Chat已带AdminTurnPersistence；下一阶段先核对现有registered chat-message.persist的DTO/原History projection/目的grant和生命周期再确定实际writer消费，不消费未注册SystemConfig/Reflection或预接77后台生产路径。
## 阶段38：公开 Chat assistant 持久化接入现有 turn owner

### Optimized Prompt

继续原全量迁移，复用已注册 chat-message.persist/MessagePersistInputDTO/原FinalHistory validator与现有 AdminTurnPersistence，将公开Chat的成功assistant与cancel/error partial回写接到现有server-persistence owner。它必须仍绑定canonical actor/authoritative Thread+Run、exact read/write scopes/editor null，写入只包含原parts/metadata/history三字段；message ID由服务器生成，不修改SSE/turn IDs、不修改Runtime parser/reducer或PG schema。原SSE events→UI parts、completed finalIndex/text/process/version、duration/usage/model/toolCount/Dream source均保持；partial noevent/noUIparts no-op、is_partial/turnStatus与日志/吞错语义保持，成功assistant失败沿原ClaudeAgentAssistantPersistenceError，SDK final safeguard仍在成功assistant之后且原失败日志不把已写message改成missing。

复用唯一unknown pending屏障扩展第三种operation：保留原operation/input/UUID，坏回复/timeout不重发；同输入显式原两态receipt恢复、absent或不同user/session/assistant写继续阻止，current grant每次renewed snapshot透传、不查询资源PG。以已发布four identity/unified/keyset/final exact requirements校验新assistant command和receipt；复用workspace既有四schema gate，必要时只提取同算法helper供原ownership与新writer调用，不复制政策或新增API。Reply messageID必须匹配输入，只有确认后clear pending；不缓存或改写历史assistant row，不制造clock、lease、newresourcealgorithm。

原internal confirmation/launch尚未携带turn owner，保留其既有SQL边界并明确pending，不以actorID/sharedservicekey/自签JWT/环境名给它新权限；新公开owner路径fence旧DB，其他service/Factory/Runner/ThreadFactory/EventBus/SSE/admission/leases/sharedFS/TMPDIR/RuntimeSDK pins原字节保持。允许代码所有权仅turn_persistence.py、workspace_data.py四gate提取、service.py两个原writer及一个shared dispatch helper、已有turn技术fixture/new focusedtests；同步affected headers/folders/当前Auth交互/README/库存/计划，normal/状态/失败/验收明确定义且不删历史稿。

机械验证由mandatory Luna既有runner执行一次fresh focused provider-free suite，原message History/SDK callback/cancel/disconnect/drain与newassistant pending/mismatch/four schemas/rawmetadata须覆盖；只用真实现有生产methods/DTO/Factory与MockTransport/明确clock，不复制入口/parser/state、不调用正常PG/CLI/model或修改77冻结候选。Primary先完成source实现与测试，runner不改代码；等待actual command/cwd/exit/rawstdout/stderr后review，失败只由Primary修正再focused rerun，不重复无新变化广域gate。静态compare唯一新增branch/helper与原full/partial构造和原four gate、其余backend bytes；完整scanner当前scope保持未迁移模块，不据改一处helper宣布全目标完成。

### 实现与技术回执

现有`chat-message.persist`实际SHA、八字段DTO与final-history validator未改。`AdminTurnPersistence.persist_assistant`在原activity/write locks内取得current grant，复用四项schema gate，并把PERSIST_MESSAGE加入user/Session共用pending；new/receipt两路径都不重发，reply message ID匹配后才clear。`ClaudeAgentService`两个原assistant writer只改为调用shared `_save_assistant_message`；公开request使用owner和服务器UUID，缺owner的内部dispatcher保留原database helper。原complete/partial parts、metadata、history三字段、错误/日志与SDK final顺序未改。

mandatory Luna exact focused argv在Dream cwd第一次exit1：28passed/6failed/69deselected/1.10s，stderr空。六失败均为测试断言仍要求schema fault前后请求数不变；实际第二次请求是预期fresh `/capabilities` GET，0 POST，production gate正确。只修断言后同一focused argv fresh复跑exit0：34passed/69deselected/1.05s，stderr空。Root逐项读取[首次command receipt](/private/tmp/dream-admin-stage38-assistant-validation/luna/command-receipt.json)、[复跑command receipt](/private/tmp/dream-admin-stage38-assistant-validation/luna-rerun/command-receipt.json)和两轮raw stdout/stderr；均未调用正常PG/CLI/model/browser/account/service。

source capture首轮因wrapper未传`PYTHONPATH`在`services`导入前exit1，保留[原回执](/private/tmp/dream-admin-stage38-assistant-validation/source/command-receipt.json)，不归类源码失败。显式`PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend`复跑[exit0/PASS](/private/tmp/dream-admin-stage38-assistant-validation/source-rerun/command-receipt.json)：actual77、published operation、四schema、八字段/SHA、complete/partial构造及SDK顺序AST、原user/Session pending方法、500其它backend Python bytes全部符合；资源/admission/lease/Runner/Factory/SSE/FS/TMPDIR未改，`internal_SQL_owner_gap_retained=true`、`normal_business_acceptance=false`。fresh scanner [exit0](/private/tmp/dream-admin-stage38-assistant-validation/scanner/command-receipt.json)为299/47SQL/512literal/16driver/34legacy/117helper、parse_errors=[]，只比阶段37减少公开Service的一次helper调用。内部dispatcher assistant、Story output整体事务、SystemConfig、Gateway/Editor和其余领域继续开放；未消费未注册SystemConfig/Reflection或连接77 failure后台路径。

## 阶段39：Editor stdio 移除 PostgreSQL 能力并消费 Admin 委托操作

### Optimized Prompt

继续原全量迁移，关闭current closure scanner指出的Editor子进程`DATABASE_URL`投影。复用Admin实际公开`editor-state.load` SHA `1555a622d0030dc2242ee86825fd949f4ea8b0fbe77e28528b19c72804c40335`、`editor-state.replace` SHA `bb37ffff488c49a6e8b69f58a16eb1a4eb454f1d6f014a1b91832c001811a4f6`、现有EditorStateDTO、runtime-delegation create/renew/receipt与Admin origin transport边界；不得把service secret、OAuth bearer、DATABASE_URL、actor ID或PG driver恢复到Editor子进程。Admin继续唯一执行OAuth身份、Thread/Editor Session ownership、purpose/scope、WritingThread与state schema校验；Dream不复制这些数据库规则。

保留现有外部stdio MCP与五个工具、确认策略、live-session PreToolUse、`.editor/`虚拟读取、同一轮`switch_editor`、flyweight和`session_updated`事件语义。由于`editor-stdio` grant精确绑定一个Session且换Session必须由OAuth服务新建grant，主进程建立turn-owned本地Editor broker：只接收随机进程能力与closed JSON命令，使用server-owned OAuth向Admin创建目标Session grant并调用公开load/replace；子进程不接收Admin bearer。Broker绑定`127.0.0.1`随机端口，使用单行有界closed JSON和每turn随机capability；不改变`CLAUDE_CODE_TMPDIR`位置、symlink检查、Workspace Mode或sandbox allow路径。stdio env只投影loopback host/port、一次性能力、timeout和最大字节数，用户/env/Deck/plugin不可覆盖；错误与日志不包含token、正文或上游异常。

Editor mutation算法仍在原`editor_tool.py`中保持：目标缺失只fresh reload一次，完整state原样mutate，replace最后写入生效；write/delete/insert/reply原业务成功/error字段与UUID/timestamp行为不变。DB loader/saver改成broker load/replace，missing与unavailable分开；replace网络结果未知时runtime保存原request UUID/input，仅查询公开receipt，不重发，absent阻止其它write且不声称rollback。Broker在每次load/confirmed replace缓存完整state，stdio工具结果不回显文档；service写结果和Runner switch hook只读取该turn owner缓存更新AgentRunState，删除原`database.get_session`与`load_editor_state_from_db`调用。Switch先通过broker向Admin load目标，Admin拒绝foreign/deleted/corrupt后不切换；成功后同一子进程可继续写新Session。

生产公开route仅在`editor_state`非null时由现有AdminRequestAuth创建Editor owner，绑定当前actor/thread与初始state.id；请求/SSE前错误沿现有safe AdminDataError。Factory在原admission acquire后启动owner，在原Phase4 finally独立drain，和turn persistence并列但不改变admission顺序、lease、EventBus、disconnect/cancel/resume或Runner进程生命周期；内部dispatcher缺Admin owner时Editor fail closed，不回退PG。关闭必须停止listener、grant keeper和clients，不停止用户服务或清理其他文件。

源码允许新增`services/admin_data/editor_runtime.py`，修改request_auth/router/request dataclass/service/Factory/types/runner/editor_tool/stdio headers及focused tests；同步affected folder docs、Editor现行设计、Admin auth交互、README/库存/计划，不改历史稿。Primary先实现与focused provider-free tests；mandatory Luna复用既有runner执行一次fresh exact command并保存command/cwd/exit/raw stdout/stderr，失败仅Primary修复再复跑。覆盖actual capability/hash、exact grant binding、loopback/private能力/有界消息、服务/OAuth/DB不投子进程、load/replace/receipt unknown/no-resend、两次目标读取、switch新grant、cache/event、cancel/error/cleanup，以及原Runner/TMPDIR/resource/admission/lease/SDK env边界。不开正常服务/PG/Gateway/model/browser/CLI，不宣称未迁移SystemConfig/Story整事务/其余SQL或正常业务验收完成。

### 阶段39实现与独立技术回执

新增turn-owned `AdminEditorRuntime`、strict Editor operation/broker DTO和bearer-only public client。公开Agent入口用当前OAuth创建exact `editor-stdio` grant；Factory在原admission后启动`127.0.0.1`随机端口listener及每Session keeper，在Phase4等待broker action后关闭listener/keepers/clients。stdio只接收host/port、每turn随机capability、timeout和最大消息字节数；不接收OAuth、service secret、idg、actor、Admin origin或`DATABASE_URL`。`editor_tool.py`删除Dream数据库load/update，四个mutation在Admin current load后变换完整state并replace，`reply_to_comment`按现行DTO写`chatHistory`的assistant消息；`switch_editor`先成功load才允许PostToolUse采用runtime cache。每次load先清除目标旧cache，因此失败的后续switch不会采用历史成功值。

replace可能已经发送时，main runtime与child client都保留原input/request ID。相同input只查询public `editor-state.replace` receipt，absent或查询失败保持unknown且不重发；下一次read也先恢复该pending，结果未确定时不读取新state。grant/校验等POST前失败不建立unknown屏障。启动首个keeper失败会关闭该keeper、listener和clients；运行中为新Session启动keeper失败会关闭keeper并移除未完成绑定。请求准备在长turn owner创建前完成；初始Editor grant失败关闭persistence owner，user message预留失败关闭两个owner。

Primary最终exact suite使用Dream cwd和`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend`执行下列argv，**exit0，355passed/1skipped/4.94s，stderr空**；原始[command receipt](/private/tmp/dream-admin-stage39-editor-validation/primary/command-receipt.json)、stdout和stderr均已保存：

```sh
/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python -m pytest -q backend/tests/test_admin_editor_runtime.py backend/tests/test_editor_index_and_tool.py backend/tests/test_admin_chat_routes.py backend/tests/test_admin_turn_persistence.py backend/tests/test_claude_agent_runner.py backend/tests/test_claude_agent_service.py backend/tests/test_admin_delegation.py
```

Mandatory Luna初次同argv在默认sandbox **exit1，348passed/6failed/1skipped**，六个失败全部发生在`_ThreadingBroker.server_bind()`的`PermissionError: [Errno 1] Operation not permitted`，属于loopback harness前置失败；[原回执](/private/tmp/dream-admin-stage39-editor-validation/luna/command-receipt.json)保留。按已授权的仅disposable `127.0.0.1` bind权限执行后通过；最终源码变更后的fresh同argv [exit0回执](/private/tmp/dream-admin-stage39-editor-validation/luna-final/command-receipt.json)为**355passed/1skipped/4.86s，stderr空**，stdout SHA256 `91c47329e1c31f1643f24ff799f8ae1bb1080789bc9fb1f92409e6bba012da80`。Luna未修改仓库或访问PG、正常服务、模型、CLI、浏览器和外部网络。

- `env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend /Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/dream-admin-stage39-editor-source-check.py` **exit0/PASS**：21项backend exact manifest、15个Python AST、两项actual operation/hash/path/scope、original-ID receipt、stdio credential boundary、admission-before-start与Phase4-close-before-lease-release符合；admission/EventBus/resource data+policy四个高风险模块相对HEAD无改动，`normal_business_acceptance=false`。
- `python3 /private/tmp/dream-admin-stage39-doc-check.py` **exit0/PASS**：15份affected docs、55个本地链接、15个Python header、3份history正文保留迁移前HEAD文字，四处原Markdown尾随空格按diff规则移除且带独立历史标识，`git diff --check=0`，无失败。
- `python3 /private/tmp/dream-admin-current-sql-scan.py` **exit0**：300模块/46 SQL-bearing/510 literal/16 driver/33 legacy imports/115 helper candidates、parse_errors=[]。这些是当前源码候选，不是完整可达SQL证明；SystemConfig、internal dispatcher、Story组合事务及其它列出的生产数据库路径仍开放。

现有Admin合同只允许用请求OAuth创建绑定一个Editor Session的grant。已创建grant由keeper续期到Admin固定maximum；若长turn中请求OAuth已过期，切换到此前没有grant的新Session会被Admin拒绝并保留原flyweight。Admin当前没有从旧Editor grant派生新Session grant或刷新请求OAuth的操作，本阶段不以service identity、actor参数或PG连接补权限。正常本机账户/PostgreSQL/Admin可见记录/真实模型验收未执行；Runtime/SDK pins、正常服务、Gateway、资源LKG、admission/lease、EventBus/SSE、shared FS与TMPDIR未改。

## 阶段40：SystemConfig 生产读写消费 Admin 已发布合同

### Optimized Prompt

继续原全量迁移，消费Admin实际发布的`user-system-config.get`、`user-system-config.patch`与`thread-system-config.get`，从公开Settings、公开Chat预检、Agent执行上下文、Workspace公开文件入口和Gateway模型选择中移除Dream PostgreSQL SystemConfig读写。三个operation必须逐项固定实际SHA与`identity.better-auth.v1`、`dream.schema.unified.v1`要求；user get/patch只使用当前请求OAuth，thread get只使用现有`AdminTurnPersistence`持有的exact `server-persistence` grant，不把actor、Run、path、配置selector、service secret或数据库连接放入业务DTO。

新增单一typed SystemConfig adapter。`config_json`按Python JSON语义解析并保留大整数、`1.0`、`-0.0`、Unicode与未知字段；顶层非object、无效JSON、NaN/Infinity及递归非有限数必须503 fail closed，不能修复、默认或回退数据库。patch DTO仅包含Admin发布的十个可选字段并由Pydantic拒绝额外字段；公开PUT继续复用现有Dream请求清洗、Gateway catalog可调用校验、unknown-key忽略、provider/model联动和public secret过滤。非空patch成功后独立fresh get形成原`{success,data}`回复；patch已提交而后续get失败时返回安全错误，不声明回滚。patch网络结果未知只允许用原request UUID查询原两态receipt；absent不重发。

公开Chat在确认canonical Thread后以OAuth读一次user config，供模型选择和附件Workspace参数共用；Agent实际执行在admission后从turn owner fresh读取thread config，保持request preflight与执行snapshot边界独立。turn read沿现有activity lock和grant renewal生命周期，close等待在途读取；Admin unavailable、capability漂移或配置损坏必须终止该turn，不沿旧空配置继续。Gateway selector移除默认数据库reader，所有生产caller显式传入已获授权的config reader；尚无OAuth/grant的Story guidance/internal dispatcher fail closed并记为待迁移，禁止以user ID、共享service key、自签JWT或环境分支补权限。

Workspace公开入口使用当前OAuth user get。原Thread ownership优先于Mode/path/文件访问的入口继续保持该顺序；不需要Thread的数据入口在任何文件操作前完成Mode判断。Workspace Mode关闭仍只创建thread runtime根与`.claude-tmp`的原协议不变，SystemConfig迁移不得改变规范化真实路径、symlink、0700、sandbox write allow、shared FS、Editor broker或TMPDIR行为。Agent模型、system prompt、env、IM、sandbox与workspace投影仍用既有解析与服务器Runtime键scrub；不得改变final model catalog对compact/context/max output的所有权、资源LKG、admission/lease、Runner、ThreadFactory、EventBus、SSE、resume/cancel语义。

允许新增`services/admin_data/system_config_data.py`并修改request auth、turn persistence、Settings/Chat/Workspace routers、Agent service与Gateway selector及其focused tests；先同步文件headers和affected folder/current design/README/库存，保留历史稿。Primary用MockTransport和公开生产入口覆盖exact capability/hash/schema、OAuth与idg分离、closed DTO、原JSON语义、corrupt fail-closed、patch后fresh read、unknown original receipt/no resend、turn close drain、Chat一次preflight复用、Workspace顺序和无database fallback。mandatory Luna在Primary通过后执行相同fresh bounded provider-free suite，保存command/cwd/exit/raw stdout/stderr；不访问正常PostgreSQL、账户、Admin服务、Gateway模型、CLI、浏览器，不把技术测试报告为正常业务验收。最后运行actual contract/source gate、完整当前SQL扫描、Markdown inventory与`git diff --check`，只提交本阶段明确拥有路径并报告未注册后台/Story组合事务/其余SQL及正常业务验收缺口。

### 阶段40实现与独立技术回执

新增单一[SystemConfig typed consumer](../../backend/services/admin_data/system_config_data.py)，固定actual80三项operation：`user-system-config.get` SHA `6e9b75cccbc6e843a9c25a0cbec041fef4c6dff3919af8449eff03c23e779dd5`、`user-system-config.patch` SHA `4f596ea05fe6adc5d881f5484b41ce40ae3a08358a7332f1b3b964112bd38b72`、`thread-system-config.get` SHA `50ca46f131005c0e9831797fc9f2590984da8c8878fec92db61656ec9eefec8b`，并要求identity SHA `1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3`与unified SHA `8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71`。Dream decoder保留任意精度integer、float类别、negative zero、Unicode和未知stored key；非object、invalid JSON与递归非有限数拒绝。patch采用present-fields closed十字段DTO，显式null、额外字段、未配对model/provider、秘密键及服务器Runtime/TMPDIR/身份键拒绝；write unknown只查原request ID receipt，不重发。

公开Settings GET/PUT使用current OAuth，PUT确认后以独立request执行fresh GET。公开Chat在Thread与message校验后读取一次OAuth配置，复用于模型选择和附件；活动turn在Workflow mapper、prompt、Workspace与Runner前由`AdminTurnPersistence`以exact Thread/Run grant fresh读取。配置read与现有user/Session/assistant writer共用activity lock，close会等待在途操作。Gateway selector无隐式数据库reader，缺explicit authorized snapshot在catalog前503；缺owner的internal dispatcher同样在mapper前拒绝。全部Workspace route在文件系统前读OAuth配置，content/download仍保持Thread ownership → config/Mode → path/FS顺序。`database.get_system_config/save_system_config`兼容符号保留，但在I/O前明确拒绝；生产SystemConfig直接数据库调用为0。

Primary在Dream cwd用`PYTHONDONTWRITEBYTECODE=1`与`PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend`运行十文件exact suite，**exit0，275passed/4.35s，stderr空**；[command receipt](/private/tmp/dream-admin-stage40-system-config-validation/primary/command-receipt.json)、raw stdout/stderr已保存。Mandatory Luna不改仓库，以相同argv/cwd/env fresh运行，Root读取[command receipt](/private/tmp/dream-admin-stage40-system-config-validation/luna/command-receipt.json)及raw输出：**exit0，275passed/4.30s，stderr空**，stdout SHA256 `a427e19676693df45bb27d5f0139a3fbc8372606b16069d058916d6f31bcccc6`。两轮均未访问正常PostgreSQL、Admin服务、账户、外部网络、Gateway模型、CLI或浏览器。

- [source receipt](/private/tmp/dream-admin-stage40-system-config-validation/source/command-receipt.json) **exit0/PASS**：actual80 artifact SHA `661823a292301a67b70ccff8068492a035cc6a3b90fe7abe4eb623f4bc161879`、三operation/hash/two schema requirements、24文件backend manifest、17个Python AST、配置读取顺序、Gateway explicit reader、数据库兼容函数无SQL、Workspace Thread ownership顺序全部符合。admission、EventBus、ThreadFactory、Runner、SDK env、resource data/policy与agent factory相对阶段39 commit `dfb93e8f`未改，`normal_business_acceptance=false`。
- [scanner receipt](/private/tmp/dream-admin-stage40-system-config-validation/scanner/command-receipt.json) **exit0**：301模块、46 SQL-bearing、506 literal SQL候选、16 driver/import、30 legacy database import与108 direct helper Call候选，`parse_errors=[]`。相对阶段39的变化包含并行工作树改动，不全部归因本阶段；这些计数也不是完整生产可达性证明。27个直接helper模块及下一Story agent-output aggregate见[当前清单](dream-admin-data-inventory.md#阶段40当前源码扫描与剩余直接helper)。
- [docs receipt](/private/tmp/dream-admin-stage40-system-config-validation/docs/command-receipt.json) **exit0/PASS**：16份affected/current文档、375个本地链接、17个Python header、README中英文27/27 heading结构及`git diff --check`均通过。

一次较宽诊断加入旧`test_server_claude_agent.py`、Story launch等suite时得到187passed/1skipped/30failed；失败集中于仍直接调用已迁移route而未解析FastAPI `Depends`的旧fixture，以及Story旧401/422期望，不是本阶段exact发布门禁，也未据此判断生产API失败。本阶段没有修改这些未迁移Story路径。Admin producer的公开PostgreSQL、并发、fault/final-COMMIT/preservation和正常账户/model验收仍pending；Dream全域迁移保持active。下一原事务aggregate是`receive_agent_story_output → get_or_create_default_workspace/store_agent_story_output`，必须由Admin单operation保存默认Workspace与Agent产物，不能拆成ensure后继续Dream SQL。

## 阶段41：Reflections 分区配置消费 Admin registered83

### Optimized Prompt

继续原全量迁移。Story agent-output完整aggregate尚无发布operation，不能拆开或预接；先消费Admin在actual83新增的`reflections-section-config.get/save/delete`，关闭公开Reflections配置GET/PUT/DELETE和`memory-init`中的自定义配置SQL。固定三项actual hash与identity/unified exact schema；仅接受current request OAuth，业务DTO只有closed section和save的`prompt_files_json`，不加入actor、Thread、path、default/effective选择器、service secret或数据库字段。

新增单一typed consumer：section闭集保持`echoes/traits/patterns`；get的nullable raw JSON按Python解析，顶层必须object，保留integer、float、negative zero、Unicode和legacy未知key，坏Admin JSON按invalid response拒绝。Dream继续拥有五个prompt文件名、非空string/strip过滤、静态default、display labels、partial effective merge、`usedCustomConfig`和共享FS写入。PUT在原路由过滤后用`json.dumps(..., ensure_ascii=False)`形成Admin raw input，保存确认后还原原`saved/section/updatedFiles`；DELETE无论Admin deleted真假均保留原`reset:true`。未知写只以同一OAuth查询原request ID/operation的receipt；仅committed strict output确认，absent/查询失败/坏回执保持outcome unknown，不自动重发。

`memory-init`先保持body/section校验，再用现有Admin Chat Thread read确认owner，随后OAuth读取自定义配置，最后执行原路径与文件写入；Thread不存在404、配置失败安全上游错误，任何鉴权/配置失败前不得触碰FS。公开config GET只读一次自定义配置并在Dream合并static；不把default或完整有效配置持久化到Admin。`reflections_agent`后台task仍缺可续期的OAuth/领域grant，继续保留其旧get helper并明确pending；本阶段只把无其它生产调用者的save/delete兼容helper改为I/O前拒绝，不误报完整Reflections task持久化迁移。

保留Reflections task/event/result状态机、Agent/SSE、resource LKG、admission/lease、Runtime ownership、Workspace/TMPDIR/shared FS协议。允许新增`services/admin_data/reflections_config_data.py`，修改request auth、Reflections router、无调用的database save/delete、focused tests和affected headers/folder/current memory design/README/API/架构/库存/计划。Primary用actual typed MockTransport覆盖三hash/schema/OAuth、raw类别/null/invalid、closed DTO、write reply、unknown无重发，以及公开GET merge、PUT过滤、DELETE结果和memory-init Thread→config→FS顺序。Mandatory Luna在Primary通过后执行同一fresh provider-free suite并保存raw receipts；不访问正常PG/Admin/account/model/CLI/browser。最后运行actual83 source gate、fresh SQL scanner、Markdown/link/header检查与`git diff --check`，仅提交明确manifest；报告后台Reflections task、Story agent-output aggregate、其余SQL与正常业务验收仍开放。

### 阶段41实现与独立技术回执

新增[Reflections typed consumer](../../backend/services/admin_data/reflections_config_data.py)，固定actual83三项operation：get SHA `2e1057f1cdd9248c2dbd603057310399e7ea5a51c90c601405ebb86868ccb640`、save SHA `dc2ba4ee442618b4fd39d75b8ddf9ca834b25913d85e4bee0cba76d20b4b047f`、delete SHA `8b03792f711e79c1d12343a93980da91d7675d280f9713ab454e6369b2b45967`，并要求相同identity/unified exact schema。公开config GET/PUT/DELETE使用current OAuth；Dream保留静态default、display、五文件过滤、partial merge、`usedCustomConfig`和原回复。`memory-init`先以Admin Chat确认Thread owner，再读取Admin custom配置，最后执行原路径/共享FS写入。旧database save/delete兼容符号在I/O前拒绝；后台`reflections_agent.py`没有长期Admin owner，唯一config reader及task/event/result数据库路径明确保留。

Primary exact五文件provider-free suite在Dream cwd以`PYTHONDONTWRITEBYTECODE=1`和`PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend`执行，**exit0，125passed/1.82s，stderr空**；[command receipt](/private/tmp/dream-admin-stage41-reflections-config-validation/primary/command-receipt.json)及raw stdout/stderr已保存。Mandatory Luna以相同argv/cwd/env执行，Root读取[command receipt](/private/tmp/dream-admin-stage41-reflections-config-validation/luna/command-receipt.json)和raw输出：**exit0，125passed/1.84s，0failed/0skipped，stderr空**，stdout SHA256 `9a9ac0202edce5455d016057824c15e98c8a6935e0eec71ac2ee9d6a4bd7e6a0`。两轮不访问正常PostgreSQL、Admin服务、账户、凭据、外部网络、模型、CLI或浏览器。

- [source receipt](/private/tmp/dream-admin-stage41-reflections-config-validation/source/command-receipt.json)最终fresh **exit0/PASS**：actual83 artifact SHA `2ce9712bf6d5d16867ae4cc2d68c167b834cacee45d25b647d1ea18f7367d566`、三operation/hash/two schemas、12文件backend manifest、7个Python AST、公开直接config DB call为0、后台唯一reader保留、database writer无SQL、Thread→config→FS及八个task/SSE函数相对阶段40不变。首轮source checker因用全文件字符串`background`排除background path而误匹配合法字段`background_scope=None`，exit1；这是checker断言错误，改为核对精确null scope后fresh通过，不能把首轮称为源码通过。
- [scanner receipt](/private/tmp/dream-admin-stage41-reflections-config-validation/scanner/command-receipt.json) **exit0**：302模块、46 SQL-bearing、504 literal SQL候选、16 driver/import、30 legacy database import与102 direct helper Call候选，`parse_errors=[]`；27个直接helper模块仍存在。这些数字不证明生产可达SQL全闭合。
- [docs receipt](/private/tmp/dream-admin-stage41-reflections-config-validation/docs/command-receipt.json) **exit0/PASS**：13份affected/current Markdown、2个本阶段新增本地链接、7个Python header、folder inventory、README中英文27/27 heading层级与`git diff --check`全部通过。

较宽Reflections background回归最初在fixture setup得到7fail，因为显式SQLite fixture调用已退役Dream password hasher；改用inert fixture值后又有5fail，因为旧fixture表缺当前Chat final projection三列。仅更新测试fixture后最终52passed/1.47s，生产认证、PostgreSQL与运行时schema没有增加fallback或DDL。Coordinator随后回报Registry83 **PUBLIC READY**，Admin侧公开48、保持258与原子2568均通过，save/delete原request receipt恢复可用；本阶段未重跑这些Admin命令，也未执行正常账户、正常服务、PostgreSQL、共享FS或模型业务验收。Story agent-output aggregate仍无发布operation，后台Reflections、reports及其余SQL领域继续开放；Agent/SSE/admission/lease/resource LKG/Runtime/ThreadFactory/shared FS/TMPDIR和pins未改。

提交后Coordinator复核发现实现只保留了write timeout的`outcome_unknown`，尚未执行文档约定的原receipt读取；同时`backend/.folder.md`重复列出`reflections_agent.py`。后续修正让save/delete在原POST结果未知时用同一OAuth、request ID和operation查询一次receipt：只有`CommittedReceiptDTO`且原output DTO严格有效才返回，absent、receipt timeout或坏DTO继续携带原ID与`outcome_unknown=true`，不发送第二个POST；目录表项合并且背景数据库缺口保留。首次本地focused命令误用worktree中不存在的相对`backend/.venv/bin/python`，harness **exit127**，随后使用仓库实际venv得到24passed/0.19s。

修正后的Primary原五文件exact suite [command receipt](/private/tmp/dream-admin-stage41-reflections-receipt-correction/primary/command-receipt.json) **exit0，133passed/1.81s，stderr空**，stdout SHA256 `b7cf9dfcb711f99a23ac98e57b78c40c2376e6b7270b4ea848ec744b6fe45f95`。Mandatory Luna以相同argv/cwd/env fresh执行，Root读取[command receipt](/private/tmp/dream-admin-stage41-reflections-receipt-correction/luna/command-receipt.json)和raw stdout/stderr：**exit0，133passed/1.78s，0failed/0skipped，stderr空**，stdout SHA256 `f94331348d67105489197d1bfb17de1ed94ed4b793df926892234113bb86445e`；Luna未编辑仓库或访问正常PG、服务、账户、凭据、外部网络、模型、CLI、浏览器。

[修正source gate](/private/tmp/dream-admin-stage41-reflections-receipt-correction/source/command-receipt.json) **exit0/PASS**：三项actual83 hash不变，`_write`每次至多一次execute与一次原receipt，save/delete均无直接execute或POST retry，committed strict result检查存在，Reflections目录行唯一；Python compile与`git diff --check`均exit0。[Markdown gate](/private/tmp/dream-admin-stage41-reflections-receipt-correction/docs/command-receipt.json)覆盖9份受影响current文档、378个链接、2个source header、README headings 27/27与3份回执，**exit0/PASS**。正常业务验收和阶段41已列其余数据库缺口保持不变。

## 阶段42：Agent最近Session上下文消费Admin turn grant

### Optimized Prompt

继续原全量迁移，在Admin行为gate确认后复用已发布`session.list` v1，而不新增通用查询或数据库结构。固定actual contract SHA `1936970e27a8b854dd08cd785b0da6534656aa5af0e652750693f86e88860435`及identity Better Auth/runtime delegation/runtime purpose exact requirements。Admin ingress只允许同一配置service已经验证的`server-persistence` grant在`session.list`使用：purpose必须为`server-persistence`，scope包含`dream:read`，Editor Session binding为空，expiry有效，canonical principal来自grant；不得扩大到session save/get/batch/delete/text-list、editor-stdio、任意owner或receipt。

Dream在现有`AdminTurnPersistence`增加一个只读recent Sessions方法。它必须先以immutable Workflow resolution验证actor/Thread，随后在现有activity lock内取得当前续期grant，按UTC当天及前两天生成closed `SessionListInputDTO(start_date,end_date,include_text=false)`，调用现有`AdminSessionData.list`并返回strict `SessionPreviewDTO`投影。该读取参与owner close/drain，但不进入或清除user/SDK Session/assistant write unknown屏障；idg、service secret、OAuth、Admin origin和数据库凭据不得进入CLI、MCP child、Workspace、浏览器参数或日志。

`ClaudeAgentService`只在首次system prompt或Settings `SYSTEM_PROMPT`变化触发rebuild时读取一次该投影；同keepalive且设置不变继续复用`state.system_prompt`，不新增Session调用。Admin错误、合同漂移、超时或坏DTO必须在Workspace、Runner与CLI启动前传播到既有安全错误边界，不回退Dream PostgreSQL。空投影和ContextBuilder对已取得投影的纯渲染错误继续显示原`_No recent entries found._`。测试composition可显式注入已验证投影；正常生产缺少turn owner仍在现有SystemConfig边界fail closed。

`ClaudeAgentContextBuilder`改为只渲染Service传入的Session投影，不import `database`、不自行计算日期或执行executor，删除`_fetch_recent_sessions`与兼容`_fetch_sessions`两个生产数据库读取。保持Admin返回的`updated_at DESC`顺序、`INK_AGENT_CONTEXT_SESSIONS`截断、id/name/labels/created_at/updated_at/first_line、Unicode、标题/excerpt fallback与模板文本不变。`sessions_tool.py`任意日期查询和`reflections_agent.py`后台Session读取明确保留为独立授权缺口，不能借Chat turn grant。

允许修改`turn_persistence.py`、`service.py`、`context_builder.py`及focused tests和受影响headers/folder/current architecture/README/API/库存/计划。先用MockTransport覆盖exact DTO/hash、UTC三日、include_text false、同actor/Thread/current renewed bearer、strict output/顺序/数量、Admin失败前置终止、empty projection、cache与Settings rebuild、close drain、ownerless无PG fallback；Primary通过后由mandatory Luna同argv fresh复跑并保存command/cwd/exit/raw stdout/stderr。最后执行actual contract/source AST gate、运行探针将旧两个helper设为抛错并从Admin mock取得内容、当前SQL scanner、Markdown inventory/link/header和`git diff --check`。测试不访问正常PostgreSQL、Admin服务、账户、模型、CLI、浏览器或外部网络；Admin gate未确认前不报告该消费者可用，正常业务验收和其余SQL缺口继续单列。

### 阶段42实现与独立技术回执

Admin prerequisite已回报STATIC READY/FROZEN：仅`session.list`允许同配置service完整解析后的Thread-bound `server-persistence`/`dream:read`/null Editor Session；OAuth行为和其他五项Session operation保持，Registry83 operation/map/delegation/PF artifacts SHA未变。其独立Luna为29/29、cache-free tsc0、focused lint0、Markdown与diff0；本Dream阶段未重跑Admin命令或访问其正常PostgreSQL。

Dream在[turn owner](../../backend/services/admin_data/turn_persistence.py)增加`recent_sessions`，使用current renewed token、UTC当天和前两天、`include_text=false`及Better Auth/runtime delegation/runtime purpose三项exact schema；返回strict DTO tuple并参与close drain，不改变unknown write pending。[Service](../../backend/claude_agent/service.py)只在首次prompt或Settings prompt变化时读取并投影；Admin或DTO失败在Workspace/Runner/CLI/SSE前传播，不能转换成空列表。[ContextBuilder](../../backend/claude_agent/context_builder.py)只渲染投影并按配置截断，删除两个legacy fetch函数和database imports。Admin成功空投影或已经取得投影后的纯渲染失败保留原empty文本；keepalive cache、SSE、resume/cancel、admission/lease、resource LKG、shared FS与TMPDIR保持。

Primary六文件provider-free suite在文档一致性修正后以`PYTHONDONTWRITEBYTECODE=1`和`PYTHONPATH=/private/tmp/dream-admin-data-test-deps:backend` fresh执行，**exit0，272passed/1.78s，stderr空**；[command receipt](/private/tmp/dream-admin-stage42-agent-session-context/primary/command-receipt.json)及raw stdout/stderr已保存，stdout SHA256 `a3465b9ac8e256ee74f6ff276707fcc1a5e18ad097db31b2ca3549fda31a1d40`。Mandatory Luna先前以相同argv/cwd/env fresh执行，Root读取[command receipt](/private/tmp/dream-admin-stage42-agent-session-context/luna/command-receipt.json)：**exit0，272passed/1.79s，0failed/0skipped，stderr空**，stdout SHA256 `bdebdf71544d7b4ea463436a04e090c13c3030b48922abda41d5eed6a0c03b7b`；Luna确认未编辑仓库或访问正常PG/Admin/account/model/CLI/browser/network。

[source/runtime probe receipt](/private/tmp/dream-admin-stage42-agent-session-context/source/command-receipt.json) **exit0/PASS**：`session.list`原SHA、三identity schema、四source hashes、ContextBuilder database import/helper为0；把旧Session helpers替换为记录调用后仍从supplied Admin projection渲染且调用数0。[scanner receipt](/private/tmp/dream-admin-stage42-agent-session-context/scanner/command-receipt.json) **exit0**：302模块、46 SQL-bearing、504 literal SQL候选、16 driver/import、29 legacy database import、102 direct helper Call候选、27直接helper模块、`parse_errors=[]`。ContextBuilder旧import和两helper关闭；`sessions_tool.py`、Reflections后台及其它SQL领域仍开放，正常业务验收未执行。

Markdown gate首次exit1，发现受影响的Thread Session设计稿仍有三个已改名文档的旧链接；更新链接并统一阶段稿、架构、认证、API、上下文和检索设计的失败语义后，fresh [docs receipt](/private/tmp/dream-admin-stage42-agent-session-context/docs/command-receipt.json) **exit0/PASS**：18份affected/current/stage Markdown、434个本地链接、README中英文27/27 headings、7个source headers、4份前置回执和`git diff --check`均通过。门禁同时断言Admin读取失败不得转换成空列表，只有成功空列表或已取得投影的纯渲染错误使用empty block。首次失败是文档库存缺口，不是Session API或Runtime测试失败；fresh成功回执覆盖同一路径的失败回执，因此本段保留该失败事实。

## 阶段43：Chat Session工具消费turn-local Admin projection broker

### 实现边界

复用已冻结的Admin `session.list`与Stage42 `AdminTurnPersistence`，关闭`libs/claude_agent_kit/server/sessions_tool.py`最后一条Chat生产数据库路径。新增neutral strict protocol和server-only loopback broker；request只含capability、request ID、ISO日期、`include_text`，任何actor/Thread/task/SQL/credential字段都由closed DTO在provider前拒绝。Chat provider固定owner的canonical actor/Thread，在共同activity lock内取得current renewed grant、匹配三identity schema并调用现有`AdminSessionData.list`。`include_text=false`在host与child双重禁止正文。

Factory先让persistence keeper ready，再启动`127.0.0.1`临时端口和256-bit capability；Service在Runtime workspace前取得child tuple。生产timeout/max-bytes直接来自已有Admin HTTP配置，缺失时fail closed，不新增业务常量。Phase4先关闭broker accept并drain在途同步读取，再关闭owner writer、keeper与HTTP。SSE disconnect、admission/lease、EventBus、Runner、resume/cancel、Editor、Story Workspace、Memory、Notion、shared FS、TMPDIR与sandbox保持。

Runner的user stdio配置只选择五个broker字段和两个既有retrieval policy，为Claude Gateway credential及Admin/BFF server secret写空tombstone；isolated Python bootstrap在package导入前清空继承环境，`user_mcp_stdio`入口再次只恢复broker/policy。实际子进程capture覆盖parent bearer/API/OAuth/Admin/DB/actor/Thread/custom值并确认全部不可见。`sessions_tool.py`删除`INK_AGENT_USER_ID`、database/PG/pool/Admin client依赖和fallback，保留date/fuzzy/labels/limit/Unicode/vector/auto产品行为；稳定错误不含endpoint、capability、token、URL、正文、body或异常。

本阶段按协调决定只实现Chat provider。Reflections `worker-load`的bounded Session snapshot尚未冻结，因此不猜shape、不借Chat grant、不标完成；其task/section owner和过滤测试在producer contract发布后另行实施。

### 技术回执

Primary最终焦点套件[回执](/private/tmp/dream-admin-stage43-session-tool-broker/primary/command-receipt.json) **exit0，370passed/1skipped/13.63s**。Mandatory Luna初次在sandbox内因loopback bind权限得到21fail、349pass、1skip，判定为harness失败；允许明确命名的`127.0.0.1`临时端口后对最终代码以相同argv fresh执行，[回执](/private/tmp/dream-admin-stage43-session-tool-broker/luna/command-receipt.json) **exit0，370passed/1skipped/13.55s**。Luna额外执行`git diff --check` exit0和八production Python文件compile exit0，且未编辑仓库。

[Source gate](/private/tmp/dream-admin-stage43-session-tool-broker/source/command-receipt.json) **exit0/PASS**：Session tool blocked import与legacy helper mention均为0，neutral protocol无Admin/DB import，stdio clear在运行前，Runner使用exact allowlist+tombstones。[Current AST scanner](/private/tmp/dream-admin-stage43-session-tool-broker/scanner/command-receipt.json) **exit0/PASS**：514 Python modules、80 production entries、52 SQL modules、496 SQL literals、37 driver/database import modules、94 legacy helper calls、457 transaction/connection calls、24 Admin data modules、88 operation names、104 nonproduction entries、166 schema literals、`parse_errors=[]`。相对Stage42冻结baseline，新增三个无DB模块，production entry、driver/database import module、legacy helper call各减少1；全域生产可达SQL和正常业务验收仍保持active/pending。

## 阶段44：最终认证所有权与部署投影审计

### Optimized Prompt

作为跨项目认证与发布边界审计负责人，以当前 Admin `6ce3898742b59b76b2e74fecc585eda7e2556b6b`、Dream `b8b210e6da3f8148b5131770b9517e3a1f3b433b`、两条 CLEAN Draft PR、当前 CI 和正常库 54/63 状态为证据，逐项复核“Admin 是唯一认证中心、Dream 只消费认证能力”的生产代码与部署配置。读取 Dream `server.py`、认证退役路由、Next BFF、local/Docker/Remote SSH/AutoDL/Google Cloud 配置脚本、受影响目录合同和现行认证/交互文档；搜索 Dream 中 JWT/Session/Authlib/Google/Device secret、cookie middleware、旧登录广告和所有部署投影。区分允许的 Admin OAuth access-token 校验、Gateway/Product 服务令牌、标准外部 MCP OAuth client，与不再允许的 Dream 用户 Session/JWT/Google/Device authority。

本轮修正仅删除已经没有调用者的 FastAPI `SessionMiddleware`、`SESSION_SECRET_KEY`/`JWT_SECRET` fallback、旧 Dream `GOOGLE_CLIENT_SECRET`/`JWT_SECRET`/`OAUTH_TOKEN_ENCRYPTION_KEY` Secret Manager投影和 `COOKIE_SECURE`/`COOKIE_SAMESITE` 部署投影；未使用的 Workflow helper也不得回退通用JWT secret。Next BFF 的独立 `INK_DREAM_BFF_COOKIE_SECRET`、HttpOnly handle、PKCE/state/CSRF、Admin Better Auth Session、Admin OAuth access/refresh token、CORS、Runtime/SSE/共享文件系统全部保持。旧 `/api/register`、`/api/login`、Google/Device/token FastAPI 路由继续返回既有 410 迁移响应，不恢复本地签发，也不删除历史文档。控制台不再把退役入口宣传为可用登录接口。

更新受影响源码头、`backend/.folder.md`、部署目录合同和当前部署文档；现行 Admin 契约中“全部待验证”的旧标题改为真实状态，历史增量回执保留。验证包括：生产源码无 `SessionMiddleware` 与三个旧cookie/session键；各部署投影无这些键且继续要求 BFF cookie secret；认证退役路径仍为 410/no-store/不写Cookie；Admin JWT/JWKS、BFF与完整数据库关闭门禁不回归；shell语法、Remote/AutoDL投影测试、Markdown本地引用、`git diff --check`通过。正常数据库、服务、真实Google/Device/模型不在本轮启动或修改；其验收仍等待独立正常库切换授权。

### 阶段44实现与验证回执

FastAPI已删除无调用者的Starlette `SessionMiddleware`、本地Session/JWT fallback和旧Cookie策略，并在导入业务模块前移除Admin-owned旧认证键及Next-only BFF cookie key；Story Workspace workflow helper只接受独立`INK_WORKFLOW_TOKEN_SECRET`。`itsdangerous`从生产manifest、uv lock和hash requirements移除。local/Docker/Remote/AutoDL投影会拒绝、过滤或tombstone旧Dream Google/JWT/Session/OAuth secret；Remote文件同步在上传前拒绝SQLite/WAL/SHM。Google Cloud旧SQLite/GCS同步入口除help外全部fail closed，不再执行数据库、GCS或Cloud Run动作。

Cloud Run投影进一步按运行职责拆分：backend与frontend使用独立service account，Secret Manager按单个secret授权；注册Dream service secret按实际调用方绑定，BFF cookie secret只绑定Next。旧`.cloud-env`认证引用被过滤，无合法backend引用时发布显式`--clear-secrets`；Next缺Admin origin/issuer/resource/service client、service secret或BFF cookie secret时在镜像构建前拒绝。`setup-env`只从`frontend/.env.local`读取BFF secret作为masked交互默认，不把它复制到backend或明文配置；旧project-wide Secret Accessor在逐secret授权完成后移除。Cloud资源未在本阶段创建或修改，以上通过synthetic dry-run验证。

- Dream全量backend：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests`，**exit0，3527 passed / 24 skipped / 615 subtests passed，169.63s**；skip与warning均为既有provider条件、SDK提示和FastAPI lifespan deprecation，无失败。
- 最终认证/数据库关闭焦点：三文件pytest **exit0，42 passed / 4.36s**；FastAPI synthetic legacy-env import、`uv lock --check`、requirements export内容一致性、生产auth/SQLite source scan全部exit0。
- 部署投影：全部changed shell `bash -n`、AutoDL topology、Remote env projection、Google Cloud synthetic dry-run、retired sync help/refusal均exit0；实际Google Cloud、正常服务和正常数据库未访问。
- 前端未改业务源码，但对最终工作树执行`corepack pnpm lint && corepack pnpm build`，**exit0**；lint保留17个既有Hook warning、0 error，Next 16.1.6 production build与TypeScript通过。
- 文档与工作树：Dream 17份changed Markdown、123个本地目标0缺失；Admin 2份changed Markdown、13个本地目标0缺失；两仓`git diff --check`均exit0。正常数据库仍为54/63，migration、role ACL、配置启用、服务重启及真实Google/Device/模型/业务旅程均未执行。

## 阶段45：Dream 用户域与 OAuth client 角色复核

### Optimized Prompt

作为 Dream 认证消费端负责人，在继续业务修改前先核对现行设计与实现，不把 OAuth 术语和产品用户混用。读取 Dream 认证主设计、ER/流程图、项目架构、Next BFF、Python Admin client/request auth/service-token source，以及 Admin 业务域评审、Admin login/guard、service identity 和 operation contract。Admin Better Auth/OAuth Provider 是 Authorization Server；Dream browser/device 是 public client；Dream server 是 confidential client；Dream user 是 Authorization Code/Device token 的 delegated subject/resource owner；Admin operator 是独立 `admin_users/admin_sessions/RBAC` 管理主体。`client_credentials` 只证明 Dream server client，不得为每个 Dream user 建 client 或据此访问用户实体。

用户数据调用必须保持双身份：`Authorization` 携带 user bearer，Dream 服务端用私有服务头附加 service bearer；Admin 分别验证 client 与用户 subject/scope/entity。无用户后台操作只使用具名 background scope。保持 strict Pydantic DTO → Admin Zod DTO → Domain Service → typed Repository → Drizzle/UOW；拒绝 caller user ID、SQL、表列、通用 CRUD 和 Admin 不可用时的 PostgreSQL fallback。保持 Runtime、SSE、EventBus、turn/resume/cancel、资源策略 LKG、共享文件系统和 `.claude-tmp` 不变。

先写设计审查结论和角色表，再运行聚焦的 Admin/Dream auth、service identity、BFF 与请求认证测试；只有测试或源码证明实际调用偏离设计时才修改业务代码。验收要求相同邮箱不合并、不复制密码/Session/角色，Dream 登录不创建 Admin Session，Admin 登录不读取 Dream user，public client 无 secret，service token `sub == client_id`，用户 token `sub` 映射 canonical Dream user，所有文档/ER/时序图一致，Markdown引用和`git diff --check`通过。已经符合目标的业务实现不为增加改动量而重写。

### 阶段45技术回执

Admin 聚焦7文件35项、Dream Python请求/双身份3文件109项、Dream Next BFF 3文件23项全部通过。两仓各4份受影响Markdown的本地引用检查分别覆盖9/12个链接，缺失均为0；两仓`git diff --check`均exit0。首次Dream命令使用worktree根`.venv`和不存在的Vitest分别exit127/254，确认测试实际使用`backend/.venv`、`PYTHONPATH=backend`与原生`node --test`后fresh通过；两次首失败均是harness命令路径，不是认证业务失败。源码与测试证明现行实现符合角色设计，因此本阶段不改业务代码。

## 阶段46：迁移数据域的正常用户只读业务验收

### Optimized Prompt

作为跨项目真实业务验收负责人，复用本机当前正常 Dream Browser Session、Admin/Dream/Gateway服务和真实 PostgreSQL，只通过公开生产入口验证已迁移的数据域。先从实际 Dream routers、frontend API client、strict Pydantic DTO、Admin operation registry与Zod输出确定可安全读取的用户资料、偏好、Session、图片/报告/社交、产品/模型目录、Plugin、MCP与Notion状态接口；不猜路径，不调用旧认证入口。每个请求只记录HTTP状态、顶层字段、数量和验收所需稳定ID，不读取或保存正文、prompt、文件内容、token、secret、DSN、加密配置或私有文件名。

所有请求使用现有Dream同源BFF和Browser handle，由BFF携带user bearer与server-only service bearer；不直接调用Admin内部接口，不修改Admin operator、Dream user映射、Deck绑定、订阅、Plugin/MCP/Notion配置或历史数据。正常结果必须符合公开DTO；401/403/404/409/503分别按身份、权限、实体、冲突与依赖失败判断。Admin不可用时必须明确失败，禁止回退Dream PostgreSQL。发现DTO、权限或投影偏差时，先定位Dream Pydantic→Admin Zod→Service→typed Repository链路并做最小业务修复，再重跑受影响流程；已符合目标的接口只补回执。

保持Runtime、SSE、EventBus、turn/resume/cancel、资源策略LKG、共享文件系统与`.claude-tmp`不变。本阶段不发起模型turn、Run、写操作或外部Provider发现，也不清理用户历史。验收为实际公开请求成功、响应闭集与客户端DTO一致、Admin数据接口可用、Browser不能注入私有服务头、Dream生产源码无PostgreSQL回退；记录具体命令/状态/数量并同步业务验证稿。模型额度、合法Workflow绑定和独立Admin凭据仍作为单独真实验收门，不由本阶段替代。

## 阶段47：真实模型与Workflow完成性审计

### Optimized Prompt

作为跨项目真实业务完成性审计负责人，复用当前正常 Dream Browser Session、Admin/Dream/Gateway服务和真实 PostgreSQL，只通过公开生产入口核对剩余模型turn与Workflow验收条件。先读取真实Gateway/Product模型目录、Dream模型选择与Runtime配置所有权、token预留/结算实现、Deck创建与Plugin绑定公开路由、strict DTO及当前验收回执；只记录模型别名、安全数值上限、可调用状态、拒绝原因、Deck/Plugin稳定标识和HTTP状态，不读取或保存prompt、正文、token、secret、DSN、Provider凭据或私有配置。

模型验收不得修改订阅、allowance、账本、历史结算、服务端模型配置或客户端可见的Runtime所有权。先证明每个公开可选模型的合法预留要求；只有存在预留不高于当前真实可用额度的模型时，才用用户已有账户通过正常Dream入口发起一次受限turn，并核对Thread、SSE、Gateway request、Admin持久化和结算结果。若所有合法模型都超过当前额度，记录目录、预留规则、当前余额和失败回执，保持现有失败账本，不重复提交或伪造成功。

Workflow验收不得修改用户已有Deck。先核对公开产品流程是否允许创建一个明确命名的本轮验收Deck，以及是否存在可合法绑定的Plugin/Workflow；只有公开create/bind/preflight流程、权限与依赖均可满足时才创建新Deck并按普通用户路径验收。不存在合法绑定时，记录当前唯一Deck绑定状态、可用目录和具体阻塞；不得直写数据库、内部Admin接口或配置字段。若无模型也能合法执行preflight、读取或取消等产品流程，只在其真实状态机允许时验证，不能把局部步骤报告为成功Run。

所有调用继续使用Dream同源BFF与服务端双身份，不接受浏览器注入的service bearer或用户ID；数据库仍经Pydantic DTO → Admin Zod DTO → Domain Service → typed Repository → Drizzle/UOW。保持Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、资源策略LKG、共享文件系统、sandbox与`.claude-tmp`不变。同步阶段回执、架构/验收状态和PR说明；验证Markdown引用、源码边界与`git diff --check`。只有完整真实流程达到既有断言才能关闭对应门，否则以可复核证据继续列为未完成。

### 阶段47真实完成性回执

正常Dream Browser Session从公开同源入口读取Gateway模型目录、Product用量、SystemConfig、Deck列表、Plugin options与binding，均未直连Admin内部接口或数据库。`GET /api/gateway/models`返回200和9个`callable=true/included`模型：7个公开上限为128,000，2个为384,000；当前服务端选择为`provider=gateway/model=gpt-5.6-luna`。Admin Gateway `prepareGatewayRequest`按估算输入加有效最大输出执行Token预留；Dream固定Runtime在未知Gateway alias下使用32,000默认输出上限，认证目录只设置其模型capability上界，Browser、用户env与请求体不能降低服务端所有的Runtime配置。当前公开Allowance为granted 100,000、reserved 75,006、consumed 16、remaining 24,978，所以任意当前模型即使输入为0也至少需要32,000，大于24,978。本轮没有再次提交turn，也没有修改订阅、allowance、账本、结算记录或模型配置。完整Agent turn、continue、运行中cancel和live SSE保持未完成；小额Gateway canary仍不能替代这些流程。

公开`GET /api/decks`继续返回唯一既有Deck `86512acd-abc9-44d1-af72-ea5a60af225d`。其`plugin-binding`为200、revision 0、binding null；`plugin-options`唯一发布项`ink.dream.story-workflow@1.0.0`为installation `missing`、compatibility `failed`、runtime readiness `unknown`、`selectable=false`，reason为`DECK_PLUGIN_UNAVAILABLE`，恢复动作为`select_an_available_installed_release`。由于不存在合法可选Workflow，本轮没有修改既有Deck，也没有创建不能执行的验收Deck或调用Preflight/Run写入口。成功Workflow Run仍等待正常产品流程安装并暴露可选release后验收；负向未知Run/Preflight回执继续有效，不能据此声称成功状态机已通过。

## 阶段48：模型产品视角与 Workflow 安装权限复核

### Optimized Prompt

作为Admin Product/Gateway领域架构师和Dream消费端负责人，解释并验证同一canonical用户的Gateway目录与Product model catalog为何可能不同，不能先假设主体映射或授权存在缺陷。读取最新模型可见性业务决策、Gateway availability/Subscription resolver、Product context/model repository、Dream两个strict BFF DTO和正常库只读事实。确认`enabled`目录、Allowance调用资格、可选Plan Entitlement限额与订阅页权益投影的职责；若代码偏离最新已批准合同则最小修复业务与测试，若代码符合而现行文档仍描述旧强制白名单，则只校正文档，不回退已批准产品行为。

同时检查`ink.dream.story-workflow@1.0.0`的公开release详情、Workspace installation列表、runtime readiness和install权限。普通Dream用户只有在已有`plugin:admin`权限且公开install DTO所需source、scope和idempotency均来自产品入口时才能安装；Admin operator域不得冒充Dream用户或继承其Workspace。缺权限时只记录403和所需管理动作，不绕过RBAC、不直写`deck_plugin_installations`、不把独立Admin Session与Dream Session合并。

验收包括：同一canonical subject/Allowance在Gateway与Product响应中保持一致；Gateway enabled模型无Entitlement仍按最新`allowance-only`合同调用并保留nullable entitlement审计，Product model catalog明确是当前Plan权益视图；相同email不参与映射。Workflow release存在但installation missing时，普通用户install/readiness入口按RBAC拒绝，现有Deck保持revision 0/binding null。同步所有现行设计中的资格顺序与流程图，保留历史worklog原文；运行Markdown引用、`git diff --check`和相关focused测试，不修改订阅、账本、Plugin安装、Deck或数据库。

### 阶段48复核结果

只读正常库按公开Allowance事实定位到同一active Subscription：100,000 granted、75,006 reserved、16 consumed。其当前Plan Version只有一个旧`deepseek-v4-flash` Entitlement；最新Round 67已明确取消“Plan Entitlement是模型白名单”，Gateway允许任意`enabled`且Provider/Pricing/Subscription/Allowance/显式Permission满足的模型，并把缺Entitlement请求记录为`entitlementSource=allowance-only`。因此Gateway的9项included与Product context的空权益/空Product model catalog是两个产品视角，不是OAuth主体漂移。Product catalog继续表达当前Plan权益；设置与Runtime使用Gateway目录。本轮不修改业务代码。

Workflow release详情公开读取200并包含受控source；Workspace installation列表和runtime-readiness对当前Dream用户均返回403 `WORKFLOW_PERMISSION_DENIED`，说明用户没有`plugin:read/plugin:admin`管理权限。普通用户无法通过正常入口安装该release，独立Admin operator也不能冒充Dream Workspace主体；本轮未提交install、enable、binding、Preflight或Run写请求。当前成功Workflow验收需由产品管理流程先为该Workspace或instance建立ready installation，再由Dream用户从公开options选择。
