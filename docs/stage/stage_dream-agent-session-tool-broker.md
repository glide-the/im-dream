<!-- [Input] User MCP Session tool direct database call, published Admin session.list and Chat turn-owned projection. -->
<!-- [Output] Implemented Chat-only private loopback Session broker with no PostgreSQL, identity or Admin credential in the child. -->
<!-- [Pos] Chat Agent Session retrieval closure stage; Reflections task snapshot remains a separate frozen-contract dependency. -->
<!-- [Sync] 2026-09-15: define the shared Session projection broker before implementation. -->
<!-- [Sync] 2026-09-15: implement the Chat provider and defer Reflections until its worker-load snapshot contract freezes. -->

# Agent Session 检索工具数据接口阶段

## 背景与问题

`backend/libs/claude_agent_kit/server/sessions_tool.py` 运行在 `user` stdio MCP 子进程中。阶段开始时它从 `INK_AGENT_USER_ID` 取得数字主体并直接调用`database.list_sessions_in_range`，且`_user_mcp_stdio_config`会投影整个`mcp_env`。公开Chat的首轮近期Session已经通过Thread-bound `server-persistence` grant调用Admin `session.list`，但任意日期、按正文模糊检索的工具路径仍要求Dream子进程持有PostgreSQL运行条件。Reflections子Agent也会调用同一工具，但其`worker-load` Session snapshot尚未冻结；本阶段不能借用浏览器token、Chat Thread grant或临时构造另一种授权。

## 目标与边界

- 复用 Admin 已发布的 `session.list` v1 Zod DTO、Service、typed Drizzle Repository 和 Dream Pydantic DTO；不新增 SQL、通用 CRUD、表列选择器或 migration。
- `sessions_tool.py` 只负责原输入校验、模糊排序、标签过滤、vector-unavailable 状态和产品 JSON；Session 原始行由当前 Runtime owner 经私有 loopback broker 提供。
- 普通Chat broker复用本turn的`AdminTurnPersistence`与续期后的`server-persistence` grant。
- Reflections broker只有在Admin `worker-load`发布并冻结bounded immutable Session snapshot后另行实现；本阶段不猜测shape、不接Chat provider，也不把Reflections标为完成。
- MCP 子进程仅得到随机的 turn/task-local broker capability、loopback host/port、timeout/max-bytes 和既有检索策略配置；不得得到 Admin bearer、OAuth cookie、service secret、PostgreSQL 凭据、任意 actor ID 或完整用户环境。
- Dream 保留 MCP 工具名、检索算法、Agent Runtime、SSE、EventBus、workspace 和 shared filesystem 语义。Admin 仍是数据库 owner；本阶段不把 Agent 或模糊排序迁入 Admin。

## 概念与规则

一个`SessionProjectionBroker`对应一个正在运行的Chat turn。宿主在启动MCP子进程前固定provider与canonical actor/Thread owner，并生成256-bit URL-safe capability。请求DTO只包含`start_date`、`end_date`、`include_text`和request ID；不接受user ID、Thread ID、task ID、SQL、排序字段或路径。宿主用常量时间比较capability，在loopback上限制单行请求/响应大小、连接超时与并发drain。

Chat provider将闭合DTO交给当前`AdminTurnPersistence`，在其activity lock内校验immutable actor/Thread、取得续期grant、匹配`session.list`和三项identity schema，再调用Admin。provider返回strict`SessionListResultDTO`，且`include_text=false`时拒绝任何正文泄漏。未来Reflections provider必须只读Admin `worker-load`冻结snapshot，不从Dream DB、工作区或模型输入补全；其当前状态为pending。

空查询结果是成功并返回空数组。broker 缺失、capability 错误、请求/响应超限、Admin 401/403/503、超时、能力漂移或 DTO 损坏返回稳定的 service error；`sessions_tool.py` 不回退 PostgreSQL。原 `vector` 明确不可用与 `auto` 回退 fuzzy 的状态保持；这些状态在发起 broker I/O 前确定。

## 初始 Optimized Prompt（历史输入，仅执行一次）

本轮已经应用下列prompt一次。随后协调任务把实现边界明确收窄为Chat-only，因为Reflections `worker-load` snapshot contract尚未冻结；下文涉及Reflections实现的句子保留为历史输入，不是本阶段完成声明。

You are the Dream Agent Session retrieval migration owner. Close the remaining production PostgreSQL access in `libs/claude_agent_kit/server/sessions_tool.py` without moving Dream Agent execution or fuzzy ranking into Admin. Read the exact MCP factory/stdio launch path, `AgentRunOptions.mcp_env`, `AdminTurnPersistence` lifecycle, private Editor broker implementation, Reflections `worker-load` launch snapshot contract, existing Session Pydantic DTOs and Admin `session.list` Zod → Service → typed Drizzle Repository implementation before editing.

Implement one reusable, private loopback `SessionProjectionBroker` in the Dream server. Its strict request contains only request ID, ISO date bounds and `include_text`; its strict response is the existing Session list projection or a bounded safe error. Bind each broker instance at construction to one provider. For ordinary Chat, the provider must call the current turn-owned `AdminTurnPersistence` under its existing actor/Thread validation, grant renewal and close/drain lifecycle. For Reflections, the provider must read only the bounded immutable Session snapshot returned by Admin `reflection-task.worker-load` for that task and section. Never accept a user ID, Thread ID, task ID, table/column selector, bearer or database URL from the child.

Project to the `user` MCP child only the exact broker host, ephemeral port, random 256-bit capability, timeout/max-bytes and the two existing retrieval-policy values. Remove `INK_AGENT_USER_ID` as Session authorization and stop forwarding the general turn/user environment to this child. The child validates the broker tuple, calls it synchronously, parses the existing strict DTO and then runs the current date-only, label, fuzzy, limit, Unicode and vector-interface logic unchanged. It must never import `database`, `psycopg`, persistence pools or Admin HTTP clients and must not fall back when the broker or Admin is unavailable.

Start the broker after the owning persistence/snapshot provider is ready and before the Claude Runtime starts. Stop accepting requests during owner close, drain one dispatched synchronous call before closing HTTP/provider resources, and close only the task's server/thread/socket. Preserve ThreadFactory admission order, lease, cancellation, EventBus/SSE terminal behavior, turn/resume flow, editor broker, shared filesystem, `CLAUDE_CODE_TMPDIR`, `0700`, symlink and sandbox boundaries. A failed tool query returns the existing product-visible tool error shape with a service-specific code; it does not disclose host, port, capability, token, URL, raw body or exception.

Update file headers, folder docs, the Session retrieval design and database closure inventory. Add deterministic tests for exact env projection, wrong/missing capability, malformed/oversized requests and responses, timeout/closed owner, actor/Thread mismatch, renewed grant, include-text/no-text leakage, Reflections snapshot filtering, fuzzy/labels/date-only/vector compatibility, one in-flight close drain and a production-path probe that makes all legacy database helpers raise. Refresh the AST inventory and require zero database/driver imports and zero legacy helper calls in `sessions_tool.py`. Run focused pytest, compile/static checks and `git diff --check`; route the bounded deterministic stage to Luna when capacity is available. Keep normal Google, model and daily-database business acceptance separate.

USER REQUIREMENT:
将 Dream 全部生产数据库访问迁到 Admin，并严格遵从 DTO / ORM，同时保留 Agent Runtime、SSE、共享文件系统和业务交互。

## 项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 任务 | 保持现有`session.list` DTO/Service/Repository与精确`server-persistence`门禁 | 已冻结的Session list provider |
| Dream 任务 | 实现Chat broker/provider、严格子进程环境和无DB的Sessions tool | Chat turn persistence commit |
| 后续Reflections任务 | `worker-load`冻结bounded snapshot后实现task/section provider | Reflections aggregate provider checkpoint |
| Root | 评审owner/lifecycle、源调用清单、fresh AST、Luna回执与真实验收缺口 | Chat实现完成后执行；Reflections另行验收 |

## 状态转换与失败处理

1. owner 建立：Chat turn persistence先完成actor/Thread绑定；未来Reflections必须由独立section snapshot owner完成task绑定。
2. broker 启动：绑定 provider，监听 `127.0.0.1` 临时端口，生成私有 capability；失败则 Runtime 不启动。
3. MCP 查询：child 发送闭合 DTO；host 验证 capability 和大小，provider 返回 strict Session projection。
4. 产品处理：child 沿用 fuzzy/labels/limit/vector 规则并返回现有工具 JSON。
5. owner closing：broker 停止接收新请求，已发送的同步调用 drain；随后关闭 grant keeper/HTTP/snapshot owner。
6. 任意失败：返回稳定错误或在启动前终止；不使用用户 ID 作为凭据、不读 Dream PostgreSQL、不重新生成另一授权。

## 验收标准与风险

- `sessions_tool.py` 以及 user MCP factory 无 `database`、PostgreSQL driver、pool/UOW 或 Admin credential import，运行探针旧 helper 调用数为零。
- user MCP child env 是精确 allowlist；扫描和子进程回显测试证明无 service secret、bearer、OAuth、数据库 URL、actor ID、Thread/task ID及用户自定义 env。
- Chat Session内容只来自当前turn owner；跨actor、跨Thread、关闭后调用和capability猜测均拒绝。跨task/section归入未来Reflections合同验收。
- 原日期、正文 fuzzy、labels、limit、Unicode、vector 与返回 JSON 兼容测试通过；Admin unavailable 有明确错误且无 PG fallback。
- 主要风险是正文投影体积和 loopback capability 生命周期。必须沿 Admin/Runtime 的 max-bytes 配置限制响应、使用随机单 owner capability，并在 owner close 时销毁；不得硬编码另一套业务上限。

## 实现状态与技术回执

Chat路径已实现。`session_projection_protocol.py`提供不依赖Admin/DB的strict DTO和同步child client；`session_projection_broker.py`绑定单一provider，以`127.0.0.1`临时端口、`token_urlsafe(32)` capability及Admin HTTP timeout/max-response-bytes运行。`AdminTurnPersistence`在keeper ready后启动broker，provider沿同一activity lock调用current renewed `session.list`；close先停止accept并drain在途provider，再关闭keeper和HTTP。

Service在Runtime组装前取得broker tuple。Runner只把五个broker字段和两项既有retrieval policy投给user stdio，并为Claude Gateway与Admin/BFF server credential写空tombstone。Runner通过isolated Python bootstrap在package导入前清空继承环境；`user_mcp_stdio`入口再次只保留broker/policy。`sessions_tool.py`已无`INK_AGENT_USER_ID`、database/driver/pool/Admin client依赖；保留原date-only、正文fuzzy、labels、limit、Unicode、vector unavailable与auto fallback产品JSON，broker失败返回稳定`session_projection_unavailable`且无PG fallback。

Primary provider-free焦点套件使用既有依赖执行，loopback需要解除本机sandbox bind限制；[回执](/private/tmp/dream-admin-stage43-session-tool-broker/primary/command-receipt.json)为**exit 0，370 passed、1 skipped、13.63s**。Mandatory Luna先记录sandbox harness bind失败（21 failed、349 passed、1 skipped），随后对最终代码以相同argv和允许的loopback重新执行；[最终回执](/private/tmp/dream-admin-stage43-session-tool-broker/luna/command-receipt.json)为**exit 0，370 passed、1 skipped、13.55s**，并确认`git diff --check` exit 0、八个production Python文件compile exit 0，仓库字节未修改。首次失败只来自`127.0.0.1` bind权限，不能判断产品失败。

[Source gate](/private/tmp/dream-admin-stage43-session-tool-broker/source/command-receipt.json) **exit 0/PASS**：`sessions_tool.py` blocked import为0、legacy helper mention为0，neutral protocol的Admin/DB import为0，isolated bootstrap在package import前清理，Runner exact allowlist/tombstone存在。[Fresh scanner](/private/tmp/dream-admin-stage43-session-tool-broker/scanner/command-receipt.json) **exit 0/PASS**：514 modules、80 production entries、52 SQL modules、496 SQL literals、37 driver/database import modules、94 legacy helper calls、457 transaction/connection calls、24 Admin data modules、88 operation names、104 nonproduction entries、166 schema literals、`parse_errors=[]`。相对Stage42冻结baseline，本阶段新增三个无DB模块，production entry、driver/database import module和legacy helper call各减少1；不能据此宣称全域生产可达SQL已关闭。[Markdown/link/header gate](/private/tmp/dream-admin-stage43-session-tool-broker/docs/command-receipt.json) **exit 0/PASS**：13个受影响Markdown、397个本地链接、13个Python header及中英README的27级heading结构通过。

本阶段未访问正常Admin、PostgreSQL、账户、模型、浏览器或外部网络，也未执行真实业务验收。Reflections `worker-load` Session snapshot provider、其他后台Session消费者和其余Dream SQL领域保持开放。
