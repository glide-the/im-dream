<!-- [Input] Current Dream auto-repair message persistence, Admin Registry168, Chat Drizzle repositories and turn owner. -->
<!-- [Output] Registry169 implementation plan and Dream consumer acceptance contract. -->
<!-- [Pos] Cross-project execution plan for one atomic message-status domain; Runtime, SSE and files remain Dream-owned. -->
<!-- [Sync] 2026-09-16: freeze the DTO-Service-ORM migration before implementation. -->

# Dream 自动修正消息状态迁移阶段

## 背景与问题

Dream `dream_auto_repair_service.py` 仍用 `database.save_chat_message` 保存自动修正用户消息，并用显式 PostgreSQL 事务锁定 `chat_message`、校验不可变身份和 CAS 更新 `dispatch_status`。调用发生在现有 Claude Agent turn 内；Runtime、SSE、工作区校验和一次自动修正策略均不应迁入 Admin。

## 目标与边界

复用当前 turn 的 `server-persistence` grant 和 Registry `chat-user-message.persist` 保存消息，新增单一 Registry169 `dream-auto-repair.settle` 业务操作。Admin 使用严格 Zod DTO、Service 和 typed Drizzle Repository 在一个事务中完成 actor/Thread/Run 绑定、消息行锁、状态验证、幂等重放、状态更新、receipt 与 audit。Dream 只保留消息构造、运行编排、SSE 和错误反馈，不保留 SQL、连接、事务或数据库回退。

## 概念与规则

- 输入只包含 Thread、message、不可变自动修正 identity 和目标 `dispatched|failed`；不接受 actor、role、表、列、SQL 或事务选择器。
- Admin 从 OAuth 或精确 `server-persistence` grant 推导 canonical actor；delegation Thread 必须匹配，存在 Run scope 时必须匹配 `workflowRunId`。
- Repository 只读取 actor-owned Thread 中的 user message，并以 `FOR UPDATE` 串行化状态迁移。
- `dispatching → dispatched|failed` 与 `dispatched → failed` 合法；相同终态返回 `changed=false`；其他状态或 identity 冲突返回 409。
- 未知提交只按原 request ID 查询 receipt；Dream 不重发非幂等写。
- 现有 `dream.schema.unified.v1` 足够，不新增 migration。

## Optimized Prompt:

You are the Admin/Dream data-boundary implementer. Migrate the Dream auto-repair message persistence without changing Claude Agent Runtime, EventBus, SSE, workspace validation, retry count or visible error behavior. Reuse the current turn-owned `chat-user-message.persist` operation for the initial immutable user message. Add exactly one Registry169 operation, `dream-auto-repair.settle`, after the byte-stable Registry168 prefix. Define a strict actor-free DTO containing only thread ID, message ID, the immutable auto-repair identity fields and target terminal status. In Admin, derive the canonical actor from OAuth or an exact `server-persistence` delegation, enforce Thread and optional Run binding, lock the owned user message through a typed Drizzle Repository, decode and validate stored metadata, compare every immutable identity field, permit only `dispatching` to `dispatched|failed` and `dispatched` to `failed`, return `changed=false` for exact replay, and commit the metadata update, audit and original receipt in one transaction. Do not add schema, generic CRUD, SQL selectors, Dream database fallback or a second state machine. In Dream, implement strict Pydantic DTO/hash pinning and original receipt recovery, inject the current `AdminTurnPersistence` into auto-repair persist/settle calls, map Admin failures to the existing safe `DreamAutoRepairError` behavior, and retain all existing filesystem and Runtime semantics. Add focused provider-free Admin and Dream tests for success, replay, invalid identity, transition conflict, grant Thread/Run mismatch, unknown result recovery and source closure. Update affected file headers, folder contracts and current architecture references. Run deterministic typecheck/lint/unit tests and record commands and outputs.

USER REQUIREMENT:
继续把 Dream 所有生产数据库访问迁到 Admin，数据库接口严格遵从 DTO → Service → ORM Repository，并保留 Dream 业务执行、Agent Runtime、SSE 与共享文件系统。

## 接口与状态

`dream-auto-repair.settle` 输入由 `thread_id`、`message_id`、`expected_identity` 和 `status` 组成；输出为 `message_id`、最终 `status` 与 `changed`。初始消息继续使用已有 `chat-user-message.persist`，因此不会把一个原事务拆成不一致的多步数据库写：消息提交完成后才产生 SSE，终态结算是后续独立 CAS 事务，与现行行为一致。

## 保持不变

消息 ID、parts、metadata 内容、一次修正上限、项目清理范围、Runner、ThreadFactory、turn/resume/cancel、EventBus、SSE、工作区路径与 `CLAUDE_CODE_TMPDIR` 全部保持。

## 验收

- Admin Registry168 前缀 hash 不变，Registry169 DTO/Repository/Service/handler/receipt 测试通过。
- Dream 自动修正模块和 Service 不导入 `database`/psycopg，不执行 SQL，且无数据库回退。
- 原成功、同终态重放、`dispatched→failed`、非法 identity/状态、authority mismatch 和未知提交恢复均有确定性测试。
- 相关 Python/TypeScript 编译、类型、lint、focused tests 和 Markdown 链接检查退出 0。

## 风险与发布顺序

先发布 Admin Registry169，再发布 Dream consumer。Admin capability/hash 缺失时 Dream 返回既有自动修正安全失败，不启动或继续额外 Runtime；不得回退数据库。回滚 Dream consumer 不移动 Admin registry 或 migration；本阶段没有 schema 回滚。

## 实施与验证结果

Admin Registry169 已在 `7358216a6055d7946fe0f906c7a653bada4acf81` 实现并推送：严格 Zod DTO、Service、typed Drizzle Repository、thin handler、operation registry、receipt 与生成契约清单均已更新；Registry168 prefix SHA 保持 `5b165b20d82ba48a47ada70db497df54552ec256f673f53a977e9c177a6a1961`，完整 Registry169 SHA 为 `adb90cec21e76f709d9d10638642051f33b1eb04df618f6984aaffb5c4a0962e`。Admin focused 15 tests、`tsc --noEmit`、受影响 ESLint、169项JSON和Markdown相对引用检查均退出0。

Dream 已实现 Registry169 严格 Pydantic consumer，并把 `AdminTurnPersistence` 作为首次消息与终态写入的唯一生产 owner。终态操作加入与 user/assistant/session/Runtime/Story output 共用的 unknown-write barrier；未知结果阻止不同写入，直到同一 operation/input/request receipt 确认。终态确认同时推进owner内的消息reservation，使第二个正常resume Turn以相同`dispatched`metadata replay，不把合法状态推进误报为内容冲突；Admin返回的闭集identity/state冲突仍映射为原Dream安全错误码。`dream_auto_repair_service.py` 已无 `database`、连接、SQL与fallback，原消息ID、metadata、单次修复、Runtime、SSE和文件系统语义保持。focused 157 tests + 9 subtests 退出0；最终Dream提交与更广生产入口关闭仍由后续阶段继续。
