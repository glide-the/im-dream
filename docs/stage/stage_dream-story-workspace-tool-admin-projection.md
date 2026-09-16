<!-- [Input] Story Workspace stdio MCP child PostgreSQL reads, existing Admin Run/scope DTO operations, and the turn-owned private projection broker. -->
<!-- [Output] Executable plan for a brokered authoritative Run projection while Dream retains controlled filesystem writes. -->
<!-- [Pos] Dream production-database closure stage for the Story Workspace Agent tool. -->
<!-- [Sync] 2026-09-16: apply the Prompt Architect template once before implementation. -->

# Story Workspace MCP 权威 Run 投影阶段

## 背景与问题

`backend/libs/claude_agent_kit/server/story_workspace_tool.py` 是 Dream Agent Runtime 启动的 stdio MCP 子进程。当前每次 `write_dream_run` 或 `write_dream_stage` 调用都会建立 Dream PostgreSQL 连接，执行 Workspace owner、WorkflowRun 与 Chat Thread 查询，再把权威 Run 交给 Dream 的受控文件写入器。这条路径违反“SQL、事务与数据权限过滤归 Admin，Dream 生产服务不保留数据库访问路径”的目标。

Admin 已经提供 `workflow-managed-mcp-scope.resolve` 与 `workflow-run.read` 两个严格业务接口。它们使用 Zod DTO、Service 和 typed Drizzle Repository 完成主体、Thread、Run、Workspace 与数据权限检查；Dream 已有对应 Pydantic DTO 客户端。当前 turn owner 也已经持有绑定 actor、Thread、Run 的可续期 `server-persistence` grant 和一个只向子进程投影随机 capability 的私有 loopback broker。缺口是 Story Workspace 子进程尚未通过这个 owner 获取 Run 投影。

## 目标与边界

- 复用既有 Admin `workflow-managed-mcp-scope.resolve` 与 `workflow-run.read`，不新增 migration、SQL、通用 CRUD、表列选择器或另一套 Run Repository。
- 扩展当前 turn-local 私有投影边界，使 Story Workspace 子进程只能请求本 turn 已绑定的 WorkflowRun；请求不得携带 actor、Thread、Workspace、任意 Run selector、Admin bearer、数据库 URL 或 SQL。
- Host provider 先用相同 grant 解析 actor/Thread/Run 对应 Workspace，再用 `RunLookupInputDTO` 读取完整 `RunDTO`；Dream 对 Admin 回包再次核对 actor、Workspace、Run 与 source Thread。
- 子进程把 strict wire DTO 转成 Dream `WorkflowRun`，继续调用现有 `StoryWorkspaceDreamFileWriter`。路径规范化、符号链接拒绝、CAS revision、原子替换、共享文件系统和 `.dream` 协议保持不变。
- Admin 不可用、capability 错误、DTO 漂移、Run/Thread/Workspace 不匹配或 broker 关闭时统一 fail closed，不回退 PostgreSQL，不进行文件写入。
- 不改变 Agent Runtime、Runner、ThreadFactory、admission、lease、EventBus、SSE、turn/resume/cancel、资源策略或 `CLAUDE_CODE_TMPDIR` 行为。

## 概念与规则

1. **身份认证**：Admin access token 只存在于 Dream 主进程的 turn owner；stdio child 不接收 token。
2. **实体权限**：turn owner 的 immutable resolution 固定 actor、Thread 与 WorkflowRun；Admin scope/read 接口负责 ORM 查询和数据权限。
3. **用户委托**：两个 read 操作都使用同一个当前可续期 `server-persistence` grant，且与已有写屏障和 close/drain 生命周期共存。
4. **文件职责**：Admin 返回数据库事实；Dream 根据这些事实写共享文件系统。数据库接口不接收路径，Admin 不执行文件写入。
5. **协议闭集**：子进程请求只有随机 capability、request ID 与固定操作名；响应只有完整 strict Run projection 或稳定错误。
6. **调用新鲜度**：每次工具调用都重新读取 Admin，不缓存 Run，不把启动时快照冒充当前数据库事实。

## 本轮 Optimized Prompt

本阶段只应用一次下列 Prompt Architect 模板生成的执行指令，后续直接实现，不递归优化。

You are the Dream Story Workspace MCP database-closure owner. Remove every production PostgreSQL, SQL, pool and WorkflowRunService read from `backend/libs/claude_agent_kit/server/story_workspace_tool.py` while preserving its two public MCP tools, strict input schemas, per-call authoritative provenance, CAS semantics, filesystem containment and product-visible failure shape.

Read the Story Workspace tool and stdio factory, `StoryWorkspaceDreamFileWriter`, `AdminTurnPersistence`, the current Session projection broker/protocol, Dream `AdminWorkflowManagedMcpScopeData` and `AdminRunData`, the Admin operation contract evidence, relevant folder contracts and focused tests before editing. Reuse the current turn-owned private loopback endpoint instead of adding an unrelated service. The host must derive actor, Thread and WorkflowRun from the immutable turn owner, resolve Workspace through `workflow-managed-mcp-scope.resolve`, then read the full Run through `workflow-run.read`. Both operations must use the same renewed `server-persistence` grant and strict Pydantic DTOs backed by Admin Zod → Service → typed Drizzle Repository implementations.

The child request must not accept actor ID, Thread ID, Workspace ID, Run ID, SQL, table/column names, Admin bearer, OAuth cookie, service secret or database URL. Project only the exact broker host, ephemeral port, random 256-bit capability, timeout/max-bytes and the existing host-owned Story Workspace identity tuple needed for tool-argument equality. Validate the strict response and reconstruct the canonical Dream `WorkflowRun`; reject any actor, Workspace, Run or source-Thread mismatch before opening the thread workspace. Do not fall back to Dream PostgreSQL or a startup snapshot when Admin, capability, transport or DTO validation fails.

Keep Dream as the owner of `StoryWorkspaceDreamFileWriter`, normalized thread workspace lookup, no-follow/symlink rules, `.dream` filenames, CAS revision and atomic filesystem replacement. Keep Admin as the owner of database access, permission filters and ORM reads. Preserve Runtime, ThreadFactory, service, EventBus, SSE, turn/resume/cancel, admission, leases, resource-policy LKG, sandbox and `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp` behavior.

Update affected file headers, folder docs, this stage record and the production database closure inventory. Add deterministic tests for exact child env, successful scope+Run projection, wrong/missing capability, forbidden selectors, malformed/oversized response, timeout/closed owner, actor/Thread/Run/Workspace mismatch, renewed grant, in-flight close drain, no-file-write on failure, preserved CAS and a source gate proving the Story Workspace child has no database/driver/SQL/WorkflowRunService path. Run focused pytest, compile/static checks, Markdown link validation and `git diff --check`; record command, working directory, exit code and key output. Stage only owned files because the worktree contains unrelated user and agent changes.

USER REQUIREMENT:
将 Dream 全部生产数据库访问迁到 Admin，并严格遵从 DTO / ORM；保留 Dream 产品交互、Agent Runtime、SSE 和共享文件系统语义。

## 项目、责任人与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 数据服务 | 继续提供 scope resolve 与 Run read 的 Zod DTO、Service、typed Drizzle Repository 和权限过滤 | Registry107 与既有 workflow-run.read 已发布 |
| Dream turn owner | 用同一可续期 grant 组合两个 DTO 调用并提供私有 Run 投影 | `AdminTurnPersistence`、Admin capability catalog |
| Dream MCP child | 消费 strict 投影，保留原文件写入、CAS 与错误外形 | broker 已启动且 exact env 已注入 |
| Root | 评审数据库关闭证据、文档、测试、提交与推送 | 本阶段实现和验证完成 |

## 正常流程与状态转换

1. Chat/confirmation composition root 创建绑定 actor、Thread、Run 的 `AdminTurnPersistence`，启动 grant keeper 与私有 broker。
2. Service 只把 exact broker tuple 与既有 Story Workspace identity tuple放入 Runner 的 server-owned `mcp_env`。
3. stdio child 收到工具调用，先验证工具参数的 Run 等于 host 绑定 Run，再发出无实体 selector 的固定 Run projection 请求。
4. Host provider 在 close/drain lock 内取得当前 grant，调用 scope resolve 得到 Workspace，再调用 Run read 得到完整 strict DTO。
5. Host 与 child 分别验证 Run、Workspace、actor、source Thread；验证通过后 Dream 打开规范化的既有 Thread workspace 并执行 CAS 文件写入。
6. owner closing 时 broker 先停止接收并 drain 已进入 provider 的请求，再关闭 keeper 与 HTTP client。

## 失败处理

- broker 配置缺失、capability 错误、请求/响应超限、超时或关闭：返回稳定 service failure，文件不变。
- Admin 401/403/404/409/503、capability drift 或 DTO 损坏：原错误被安全映射，禁止 PG fallback。
- scope 与 Run 的 Workspace 不一致、Run actor/source Thread/ID 不匹配：按权限/响应损坏处理，文件不变。
- CAS 冲突、路径越界、符号链接或 I/O 错误：沿用 `DREAM_WRITE_REJECTED` 外形与服务端日志，不泄漏路径、token 或 broker tuple。

## 修改范围

- `backend/libs/claude_agent_kit/server/story_workspace_tool.py`：删除 DB/SQL/WorkflowRunService，改用 strict broker client。
- 私有投影 protocol/broker：在现有 loopback 生命周期内增加 fixed current-Run projection，保留 Session 与 Reflections兼容。
- `backend/services/admin_data/turn_persistence.py`：组合 scope DTO 与 Run DTO provider，复用 grant、锁与 close/drain。
- `backend/claude_agent/service.py`、`backend/libs/claude_agent_kit/server/agent_runner.py`：仅注入 Story child 所需的 exact broker字段。
- 对应 tests、`.folder.md`、数据库关闭清单和本阶段回执。

## 验收标准、验证命令与风险

- Story tool 生产源码没有 `database`、`psycopg`、pool、原生 SQL、`WorkflowRunService` 或 PostgreSQL fallback。
- Admin 数据读取严格通过现有 `WorkflowManagedMcpScopeInputDTO` 和 `RunLookupInputDTO`；Admin 仍由 Zod/Service/Drizzle Repository 执行权限和查询。
- 成功、拒绝、超时、关闭、Run/Thread/Workspace错配、CAS、symlink/path 与 no-write-on-failure 测试通过。
- 运行焦点 pytest、`py_compile`、source AST/文本 gate、Markdown 本地链接检查、`git diff --check`，所有退出码为0。
- 风险是扩展共享 broker 时影响普通 Session 与 Reflections 投影。必须保留原 Session wire/client 测试，并证明不支持 Run 的 provider 仍可正常提供 Session、也不能被 Story child越权调用。

## 实现与验证结果

本阶段复用既有`SessionProjectionBroker`的单端口、单capability和close/drain生命周期，保持原Session request wire不变；增加固定`workflow-run.current`请求。普通或Reflections provider未绑定Run时返回`STORY_WORKSPACE_PROJECTION_DENIED`。`AdminTurnPersistence`的Run provider不接收child实体参数：它从immutable resolution取得actor/Thread/Run，使用当前可续期grant依次调用Registry107 managed-scope与既有`workflow-run.read`，再核对Workspace、actor、source Thread及六项冻结Deck来源。stdio child验证host-owned actor/Thread/Run后才打开workspace并调用原writer。

Dream没有新增SQL、migration或Admin接口；Admin仍用已发布Zod DTO、Service和typed Drizzle Repository。`story_workspace_tool.py`已删除`database`、原生SQL和`WorkflowRunService`，Admin/transport失败时只返回既有`DREAM_WRITE_REJECTED`且不生成runtime文件。两个MCP工具、Run/stage revision、CAS冲突、路径与symlink规则、Runtime/SSE/turn生命周期和共享文件协议未变。

实际验证均在`/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`执行：

- 相关业务套件：在`backend`运行`.venv/bin/python -m pytest -q`并传入broker、Story tool、turn owner、Runner、Service、Dream files、Session tool和PostgreSQL边界九个测试文件；最终候选**exit 0，356 passed、1 skipped、196 subtests passed，20.03s**。
- 编译：`PYTHONPATH=backend backend/.venv/bin/python -m py_compile`检查六个生产文件和四个测试文件；**exit 0**。
- AST源码门禁：排除tests、`.venv`、script、tools和schema后解析全部production Python；**exit 0，parse_errors=0，Story blocked names=0，Story SQL literals=0，实际数据库import模块=11**。第一次仅用`UPDATE `关键词的临时分类器把工具描述中的英文“update”误判为SQL并exit 1；修正为`SELECT…FROM / INSERT INTO / UPDATE…SET / DELETE FROM`结构后得到上述结果，没有修改产品预期来掩盖失败。
- Markdown与diff：最终提交范围的9个受影响Markdown检查27个本地链接，**missing=0**；随后`git diff --check` **exit 0**。

当前剩余11个实际生产数据库import文件已在本阶段的源码门禁输出中逐项列明。因此本阶段的Story Workspace stdio入口技术验证完成，但Dream全域数据库关闭和真实账户/模型业务验收仍未完成。

> [Sync] 2026-09-16: 后续全域复查发现 `story_workspace_tool.py` 仍保留一个未使用的 `StoryWorkspaceDreamReentryService` import。它没有参与工具调用，但会在 stdio child 启动时加载旧数据库模块。当前修正删除该 import 并加入文件头；工具继续只通过 turn broker 取得 Admin Run DTO，原有 CAS、路径、文件与失败语义不变。
