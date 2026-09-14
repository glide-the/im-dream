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
