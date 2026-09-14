<!-- [Input] User delegation, Agent.md, AGENTS.md, baseline 7d38715c, and Admin-owned contracts when published. -->
<!-- [Output] Executable Dream migration plan, dependency gates, and exact evidence inventory. -->
<!-- [Pos] Dream implementation plan; Admin owns authentication, database transactions, and schema contracts. -->
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
