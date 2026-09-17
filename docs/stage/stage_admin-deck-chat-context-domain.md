<!-- [Input] Public Claude Agent Deck selection, legacy DeckChatContextService SQL and existing Admin Deck/refs schemas. -->
<!-- [Output] Implemented current-actor storage read plus immutable Dream policy/prompt snapshot plan. -->
<!-- [Pos] Remaining production database-access migration stage; separate from workspace plugin packing and internal dispatchers. -->
<!-- [Sync] 2026-09-15: keep ORM/permission filtering in Admin and enabled/ready business rules in Dream. -->

# Claude Agent Deck Chat Context 数据接口迁移

## 背景与问题

`backend/routers/claude_agent.py` 的公开 `POST /api/claude-agent` 已通过 Admin 读取 Thread、SystemConfig、Workflow context 并持久化消息，但选择 Deck/Voice 时仍创建 Dream PostgreSQL 连接并调用 `DeckChatContextService.resolve`。该 service 分三次读取 owned Deck、启用 Voice、启用 Claude Plugin refs/installation，再在 Dream 构造 `<deck_context>` system prompt。Story Workspace Dream turn 又在 `ClaudeAgentService` 内重复一次同类数据库读取。Agent Runtime、SSE、workspace plugin packing 和文件系统不是本接口应迁入 Admin 的业务执行。

## 目标与边界

- Admin 增加一个只读聚合操作 `deck-chat-context.resolve`，输入只含 `deck_id` 与 nullable `voice_id`，从 OAuth principal 派生 owner，在同一 read UOW 返回 owned Deck、selected/all Voice 与 plugin refs 的存储字段、enabled 状态和 installation 状态。
- 严格采用 Zod DTO → Service → typed Drizzle Repository → 调用方 UOW。不得接受 actor/thread owner、任意表列、SQL、prompt 模式、文件路径或 Runtime 参数。
- Dream 保留 prompt JSON/XML 编码、`MAX_DECK_CONTEXT_CHARS` 截断、普通 proposal instruction 与 Dream workspace instruction，并把已认证 snapshot 作为 immutable server-owned 值传入本次 Agent Run。
- 公开 route 不再创建 Dream 数据库连接。Story Workspace public turn 使用同一 snapshot 重新选择 Dream-mode instruction，不重复查询数据库。
- workspace plugin packing 仍由 Dream 执行，本阶段不把 artifact、CLI、workspace 或 launch manifest 迁入 Admin。其现有 DB 读取与没有 OAuth snapshot 的内部 dispatcher 明确保留为后续关闭项，本阶段不能宣称全 Agent path 已关闭。
- 无 migration；复用统一 schema capability、Deck/Voice/ref/installation Drizzle schema 和现有 OAuth client。

## 概念与规则

Admin 先验证 owned Deck；不存在或非 owner 返回 `DECK_ACCESS_DENIED` 404。Admin 不把 Deck、Voice、ref 的 enabled 或 installation ready 当作数据权限，按 `order_index, created_at, id` / `plugin_installation_id` 返回状态事实；指定 Voice 不存在或不属于 Deck 时返回空列表。Dream 只接受 `deck.enabled is true`，过滤 disabled Voice/ref；指定 Voice 缺失或禁用返回 `AGENT_ACCESS_DENIED` 404，禁用 Deck 返回 `DECK_DISABLED` 409，任一启用引用不是 ready 返回 `DECK_PLUGIN_UNAVAILABLE` 409。上述判断都发生在写入、admission 和 SSE 之前。

Dream snapshot 绑定 canonical actor、请求 Deck 与 nullable Voice。公开 route 完成当前 immutable Deck/Voice 冲突判断和 Admin CAS bind/select 后，将 snapshot 连同 Workflow resolution、turn persistence 和 editor runtime 交给 `ClaudeAgentRunRequest`。Service 使用 snapshot 前重新核对 actor、Deck、Voice；普通 turn 与 Dream turn只改变现有 instruction 后缀，Deck/Voice/ref JSON bytes、Unicode与截断算法保持。snapshot 不能进入浏览器、CLI env、日志或 SSE payload。

## Optimized Prompt

You are the Admin/Dream public Deck chat-context migration owner. Read both repositories' rules; Dream `backend/routers/claude_agent.py`, `backend/services/deck/chat_context.py`, `backend/claude_agent/service.py`, `ClaudeAgentRunRequest`, the exact Deck bind/select and Workflow snapshot order, `load_deck_plugin_refs`, focused route/service tests; Admin Deck/Voice/ref/installation DTOs and Drizzle schemas, actor/scopes, operation registry and restricted-role harnesses. Implement the minimum aggregate interface that removes the public Claude Agent route's Deck context PostgreSQL connection without moving prompt composition, Runtime, SSE or filesystem work to Admin.

Add exactly one OAuth read operation `deck-chat-context.resolve` with strict input `{deck_id, voice_id}` where `voice_id` is nullable. Its strict output contains only the actor-owned Deck, selected/all Voice and plugin-ref storage fields in deterministic order, including enabled and installation status. Derive owner from the verified principal, require `dream:read`, reject Thread/entity grants, and execute all reads in one typed Drizzle Repository under the existing read UOW. Admin returns `DECK_ACCESS_DENIED` only for missing/foreign Deck and otherwise projects status facts; it does not apply Deck/Voice/ref enabled or plugin-ready business rules. Do not accept actor IDs, thread owner, SQL/table/column selectors, prompt mode, file paths or plugin bytes. No migration.

In Dream, create an exact-hash Pydantic consumer and immutable server-owned resolution that binds canonical actor, Deck and nullable Voice. Apply `DECK_DISABLED`, `AGENT_ACCESS_DENIED`, disabled Voice/ref filtering and enabled-plugin ready checks in the Dream assembler, then produce byte-compatible normal and Dream-mode prompts, provenance, compact JSON, Unicode and `MAX_DECK_CONTEXT_CHARS` behavior without database access. The public route must call Admin before any Agent admission/SSE, retain existing requested-vs-persisted Deck/Voice conflict and CAS bind/select behavior, then pass the snapshot into `ClaudeAgentRunRequest`. For a public Story Workspace turn, `ClaudeAgentService` must reuse that same snapshot for Dream-mode prompt construction instead of calling `DeckChatContextService` again.

Keep Runner, ThreadFactory, EventBus, admission, lease, turn/resume/cancel, SSE frames, model config, shared filesystem and workspace packing behavior unchanged. Do not edit `_pack_thread_workspace_plugins` or claim its separate PostgreSQL read is closed in this stage. Keep internal non-public dispatchers without an Admin snapshot listed as pending; never silently fall back to Dream PostgreSQL from the migrated public route. Admin/capability/DTO/permission/plugin-status failures must occur before user-message persistence, Agent admission and stream start.

Add Admin DTO/service/repository/handler/registry tests plus a restricted SELECT-only PostgreSQL contract for ownership, status projection, ordering, selected/all Voice, nullable fields, closed selectors and no writes. Add a source oracle against the current Dream service. Add Dream consumer, enabled/ready policy, prompt-byte parity and public-route tests that make route-level `database.get_db` and legacy context resolve raise while normal/Dream prompts, Deck/Voice CAS conflicts and failures remain correct; assert no snapshot or plugin detail leaks to SSE/logs. Run focused Vitest/pytest, restricted-role integration, cache-free typecheck/compile/lint, source-only AST scan and diff/Markdown gates. Commit Admin first and freeze exact pins, then Dream separately. Do not push, modify normal PostgreSQL, change plugin packing, touch user Plugin edits or run a real model.

USER REQUIREMENT:
将 Dream 全部生产数据库访问迁到 Admin，接口遵从 DTO / ORM，同时保留 Agent Runtime、SSE、业务编排和共享文件系统。

## 项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 任务 | 单一 aggregate read DTO、Service、typed Repository、Handler/Registry 与受限角色合同 | Registry104 先独立提交；复用 unified Deck/Voice/ref schema |
| Dream 任务 | exact consumer、immutable snapshot、纯 prompt assembler、公开 route 与 public Dream turn 替换 | Admin commit/tree/op hash 冻结；Deck default consumer先独立提交 |
| Root | 源行为/字节对照、公开路径时序、AST 和 Runtime/SSE 回归 | 两侧提交与现有 route/service harness |

## 正常流程与失败处理

1. Route 从 Admin current actor 和 Thread 取得 persisted Deck/Voice，执行既有 immutable 冲突判断。
2. Admin aggregate 校验 actor owned Deck，读取 ordered Voice/ref 状态并返回严格 snapshot。
3. Route 执行既有 Deck bind / Voice CAS；冲突保持409且不进入 Agent。
4. Workflow context 与 snapshot 一并传入 Run；Service核对 actor/Deck/Voice，按普通或 Dream 模式构造原 prompt。
5. permission、disabled、agent missing、plugin nonready、capability、transport 或 malformed output 均在持久化/admission/SSE前明确失败，无 Dream DB fallback。

## 验收与风险

- 公开 `/api/claude-agent` Deck context 分支零 `database.get_db` 与 legacy context resolver；运行时 fence 抛错仍可完成 provider-free request preparation。
- Admin wire 与 Repository 无 actor/SQL/path/runtime selector；所有 Deck/Voice/ref读取在一个 UOW，other actor 严格隔离。
- normal/Dream prompt 在 ASCII、中文、emoji、null、all/selected Voice、refs 与截断边界上与旧 builder byte-compatible。
- public Dream turn不重复查询 Deck context；snapshot不进入 browser、CLI env、日志或 SSE。
- 风险是 workspace pack 和内部 dispatcher仍有独立 DB 入口；在本阶段证据中明确列出，后续用现有 `deck-plugin-refs.runtime-read`/Thread grant 与 adapter安装接口关闭，不能把本提交当成 Agent 全路径完成。
