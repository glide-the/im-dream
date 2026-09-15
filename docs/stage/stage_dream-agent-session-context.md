<!-- [Input] Dream ContextBuilder direct Session reads, existing Admin session.list DTO/ORM and server-persistence grant lifecycle. -->
<!-- [Output] Execution plan for moving first-turn recent-session context reads to Admin without exposing credentials to Runtime. -->
<!-- [Pos] Chat Agent context persistence closure; MCP session search and Reflections background tasks remain separate consumers. -->
<!-- [Sync] 2026-09-15: reuse session.list through the existing turn owner; Admin/read-contract failures stop before Workspace, Runtime and SSE. -->

# Agent Recent Session Context 数据接口阶段

## 背景与问题

阶段开始前，`ClaudeAgentContextBuilder` 在首个 turn 构建 system prompt 时直接调用 `database.list_sessions_in_range`，兼容方法还调用 `database.list_sessions`。Admin 已经通过 `session.list` 提供严格日期、文本开关、owner 过滤与 typed Drizzle Repository；Dream 的公开 Session 路由已经消费该接口。当时 `server-persistence` grant 已绑定真实用户、Thread 与可选 Run，但 Admin Session handler 只接受 OAuth 或 `editor-stdio`，所以 Agent 首 turn 尚无法复用现有接口。本阶段完成后，只有符合下述精确条件的`server-persistence` grant可额外调用`session.list`。

## 目标与边界

- 复用现有 `session.list` 契约与 ORM，不新增通用查询、表/列选择器或 migration。
- 仅允许 `server-persistence` grant 在其 canonical owner 范围读取 Session list；OAuth 公开 Session 行为保持。
- `AdminTurnPersistence` 持有和续期 grant，并在 Dream 服务器内调用 Admin。token、service secret 和数据库凭据不进入 Claude CLI、MCP 子进程、workspace、浏览器参数或日志。
- ContextBuilder 只接收已经验证的 Session DTO 投影并渲染原 system prompt；不自行 import `database`。
- 本阶段不处理 `sessions_tool.py` 的任意日期检索，也不处理 Reflections 后台 task 的 Session 读取；它们需要各自明确的服务器调用边界，不能借 Chat turn grant。

## 概念与规则

原行为取 UTC 当天及前两天、按 Admin 原 `updated_at DESC` 顺序，最多渲染 `INK_AGENT_CONTEXT_SESSIONS` 条，字段为 id/name/labels/created_at/updated_at/first_line。Admin 成功返回空列表时继续显示原 empty 文本。Admin 401/403/503、能力缺失、超时或坏 DTO 必须作为明确业务失败传播，并在 Workspace、Runner、CLI 与 SSE 启动前终止；不得把读取失败转换成空列表，也不得回退 PostgreSQL。ContextBuilder 只对已经取得的投影执行纯渲染，渲染异常仍使用 empty block。Settings system prompt 变化触发重建时重新取一次 Session 列表；同 keepalive 缓存且设置未变时不新增调用。

## Optimized Prompt

You are the Admin/Dream recent-session context migration owner. Reuse the published `session.list` v1 Zod DTO, typed Drizzle `EditorSessionRepository.list`, exact capability hash and Dream Pydantic `SessionListInputDTO/ResultDTO`. Extend the Admin Session ingress only for an already validated `server-persistence` delegation from the same configured service: resolve its canonical principal, require purpose `server-persistence`, null editor-session binding, active expiry, `dream:read`, and retain the existing Thread/Run-bound grant lifecycle. Authorize only `session.list`; do not broaden save/get/batch/delete, editor-stdio, arbitrary owner selection or receipt behavior.

Add an `AdminTurnPersistence.recent_sessions` read that validates actor/thread against the immutable workflow resolution, obtains the current renewed grant under the existing activity lock, sends the original three-day `session.list` DTO with `include_text=false`, and returns strict Python DTO projections. Change `ClaudeAgentService` to acquire this projection before first system-prompt build and pass it into `ClaudeAgentContextBuilder`. Remove production database imports and compatibility reads from ContextBuilder. Tests may inject a deterministic session projection through the existing service composition boundary; production without a valid turn owner, valid Admin response, required capability or valid DTO must fail before Workspace, Runtime and SSE, never query PostgreSQL. Only an Admin success with an empty list, or a ContextBuilder-only projection rendering error, uses the existing empty-context text.

Preserve the exact prompt rendering, row order, day window, configurable count, cache/rebuild rules, Runtime/SSE/lease behavior and all workspace/TMP/sandbox rules. Do not pass delegation tokens or service credentials into CLI/MCP/workspace. Update affected headers, folder docs, architecture inventory and call graph. Validate Admin purpose/scope/service/expiry/entity negatives, Dream DTO/order/render/error/cache behavior, a runtime no-PG probe and fresh AST counts. Record the separate remaining `sessions_tool` and Reflections background gaps.

USER REQUIREMENT:
将 Dream 生产数据库访问迁入 Admin，遵从 DTO/ORM，并保持 Agent Runtime、SSE、资源与共享文件系统语义。

## 项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 任务 | 为既有 `session.list` 增加精确 `server-persistence` 读取授权和负向测试 | 已发布 Session DTO/ORM、DelegationService |
| Dream 任务 | `AdminTurnPersistence` 读取、Service 注入、ContextBuilder 移除 DB | Admin 行为 gate、现有 turn owner |
| Root | 源调用对照、契约评审、fresh AST 和运行探针 | 两侧实现与确定性测试 |

## 修改范围与保持行为

Admin 影响 `editorSessionHandler/Service` 及测试和对应目录/架构文档，不改变 schema、operation input/output 或 hash。Dream 影响 `services/admin_data/turn_persistence.py`、`claude_agent/service.py`、`claude_agent/context_builder.py` 和 focused tests/docs。Runner、ThreadFactory、EventBus、SSE、turn/resume/cancel、admission/lease、资源策略 LKG、模型配置、workspace、`CLAUDE_CODE_TMPDIR` 与文件权限保持原状。

## 正常流程、失败与状态

1. 浏览器 OAuth 建立真实 Workflow resolution；Dream 创建绑定 Thread/Run 的 `server-persistence` grant。
2. 首 turn 或 Settings prompt 变化时，turn owner 用当前续期后的 grant 调用 `session.list`。
3. Admin 校验 service、token、purpose、scope、expiry 和 canonical owner，执行 fixed ORM 查询并返回 DTO。
4. Dream 截断配置数量并按原模板渲染；keepalive 复用已缓存 system prompt。
5. Admin 401/403/503、能力缺失、超时或坏 DTO 作为明确业务失败传播，在 Workspace、Runner、CLI 与 SSE 前终止；不启动第二条查询、不回退 PG。只有成功空列表或已取得投影的纯渲染错误进入 recent-session empty block。
6. owner 关闭后 grant 不再使用；已有 close/drain 顺序保持。

## 验收标准与命令

- Admin focused Vitest：OAuth保持；server-persistence list成功；错误 purpose、service、scope、过期、editor binding 和其他 session 操作拒绝。
- Dream pytest：三日 DTO、顺序/数量/Unicode渲染、成功 empty 与纯渲染 error、Admin/DTO 失败-before-Workspace/Runtime/SSE、system prompt cache/rebuild、无 turn owner、close 后调用与无 DB fallback。
- 无缓存 Admin `tsc`、focused ESLint；Dream compile/import与目录规则检查；两仓 `git diff --check`。
- fresh AST 证明 `context_builder.py` 的 driver/database imports、legacy helper 和 transaction calls 为0；运行探针把旧 helper设为抛错，真实生产组合仍从 Admin mock/isolated public Route取得内容。
- 风险是给 Thread-bound grant 开放 owner级 Session list。实现必须将放行限制在 `session.list` 和 `server-persistence`，并用相同 canonical subject 派生 owner；未证明前不扩大到 MCP/后台任务。
