# Registry 121：Confirmation Runtime Admin 持久化所有者

## Prompt Architect

### Optimized Prompt

你是一名跨项目 Next.js、Python、PostgreSQL/Drizzle、DTO/ORM 与长任务授权架构工程师。请在 Admin `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory` 与 Dream `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory` 中完成 Registry 121：让 Registry 120 已由 Admin 持久化并领取的 Story Workspace confirmation 后台 Runtime turn 获得一个由当前 durable claim 派生、可续期且受精确实体约束的 `server-persistence` grant，并将现有 `AdminTurnPersistence` 注入同 Thread Runtime。

Admin 必须使用严格 Zod DTO、Service 和 typed Drizzle Repository。新增 `story-workspace-confirmation.claim-turn` 后台操作，在一个 Admin transaction 内完成 message claim 与 authority 签发/恢复；客户端不能提交 actor、Thread、Run、scope 或 purpose。authority 的主体、Thread 与 Run 只能从 Admin 校验后的 confirmation message、Workflow、Subject 和 service 配置派生。每次 delegation resolve/renew 都必须验证 source message 仍为相同 `dispatching` claim、lease 尚未到期、主体仍 active、Thread/Run 仍归属该主体。旧 claim、过期 lease、已 ACK、错误 service、错误 Thread/Run 或 inactive subject 必须在 ORM 操作前失败。token 只返回 Dream 服务端，不能写入 message metadata、receipt、audit、日志、Runtime 参数、文件或浏览器。

Admin Drizzle 是唯一 schema 来源。以 additive migration 扩展 `identity.runtime_delegations` 的 authority source/message/claim 绑定，保留现有 OAuth 创建与 `idg_` 协议，发布新的精确 schema capability；不得修改 0000–0061 历史。注册 Registry 121 的真实 JSON schema hash，并保留 Registry 120 五个操作兼容。Dream 使用严格 Pydantic DTO 消费新操作，以返回的 grant 通过既有 `workflow-context.resolve` 和 `deck-chat-context.resolve` 构造 immutable snapshots，再创建并启动现有 `AdminTurnPersistence`，注入 `ClaudeAgentRunRequest`，在 turn 结束或失败时 drain/close。Admin 不可用、capability 缺失、claim 丢失或快照不一致时，本次 dispatch 失败并由现有 lease/backoff 恢复，禁止回退到 Dream PostgreSQL。

保持 Runner、ThreadFactory、Agent Runtime、EventBus、SSE、turn/resume/cancel、资源策略、admission、lease、共享文件系统、`.claude-tmp` 与 Story confirmation 产品状态语义不变。`user_message_pre_persisted` 仍只跳过已由 Admin claim 校验的 confirmation user message；assistant、Session、Thread、SystemConfig、Deck、plugin、MCP scope、Runtime activation 和 Story output 全部通过同一个 Admin owner。新增确定性 Admin/Dream 合同测试和具名可删除 PostgreSQL 迁移/并发/ACL 验证；验证旧 claim 无法继续写、同 claim 恢复同 grant、并发只产生一个有效 claim-turn、ACK 后 authority 失效，以及 confirmation Runtime 路径不触发 Dream DB fallback。更新受影响文件头、目录文档、架构/阶段文档和 Markdown 索引，并仅提交本阶段拥有的改动。

### Optional Enhancers

- 在具备本机正常 Admin、Dream、Gateway 与真实 PostgreSQL 条件后，补充一次保留业务回执的真实 confirmation Runtime 验收。
- 在全部 Dream 生产数据库入口迁移完成后，删除仅为尚未迁移内部 dispatcher 保留的通用数据库 fallback。

## 背景与问题

Registry 120 已将 confirmation submit/fact/claim/lease/ack、Run transition、user message 和 receipt 迁入 Admin。当前 coordinator 领取 claim 后直接构造 `ClaudeAgentRunRequest`，只设置 `user_message_pre_persisted=True`，没有 `admin_workflow_resolution`、`admin_deck_chat_context` 或 `admin_turn_persistence`。因此该内部 Runtime turn 仍可能通过 `ClaudeAgentService` 的旧内部 dispatcher 分支读取或写入 Dream PostgreSQL。

现有 `AdminTurnPersistence` 已实现消息、Thread、Session、SystemConfig、Deck plugin refs、managed MCP workspace、Runtime activation 和 Story output 的统一 DTO client，公开 Chat 也已经验证其 grant 生命周期。本阶段复用它，不建立第二套消息或 Runtime 服务。

## 目标与边界

- Admin 负责 claim-turn authority 的 DTO、授权、Drizzle 持久化、租约校验和数据访问。
- Dream 负责 confirmation claim 调度、共享文件校验、同 Thread Runtime、EventBus 与 SSE。
- Admin authority 从持久化 claim 派生；Dream 不提交或覆盖 actor、Thread、Run、purpose、scope。
- 只关闭 confirmation dispatcher 这一条内部 Runtime 路径。其他生产数据库入口继续按关闭清单逐项迁移。
- 不改变用户可见 confirmation 状态、Run 状态、重试节奏和 ACK 条件。

## 概念与规则

1. `claim-turn` 是 Registry 121 新操作；Registry 120 的 `claim` 保留以支持旧 Dream 版本。
2. `authority_source=story-confirmation-claim` 的 `idg_` grant 必须同时绑定 service、auth subject、canonical actor、Thread、Run、message 和 claim。
3. 同一 message/claim/service 的重复请求恢复同一未失效 token；不同 claim 不能恢复旧 token。
4. delegation 每次进入 Admin UOW 时以数据库时钟验证 claim lease，并持有 message share lock；claim/ACK 的 message update 必须等待已进入的 UOW 完成。
5. lease 过期、claim 被替换或 ACK 后，新的 Admin 操作立即拒绝；token 本地 TTL 不能绕过此检查。
6. migration 只增加 nullable source 列、约束、索引和 `identity.runtime-confirmation-claim.v1` capability；旧 OAuth delegation 行继续满足现有 v1 行为。

## 责任与依赖

| 项目 | 责任 | 依赖 |
| --- | --- | --- |
| Admin | Drizzle expand、capability、claim-turn DTO/Service/Repository、delegation source 校验、接口测试 | Registry 120 message claim；现有 runtime delegation；identity/dream unified schema |
| Dream | Pydantic 合同、grant/snapshot composition、Runtime request 注入与关闭、路径级回归 | Admin Registry 121；Registry 105/106/107/108/109 与 Chat/Session 操作 |
| 协调 | 哈希同步、迁移 replay、并发/ACL/旧版本兼容、阶段状态 | 两仓实现和真实命令回执 |

## 正常流程与状态转换

1. coordinator 调用 `claim-turn(message_id?, claim_id)`。
2. Admin 锁定 confirmation message，完成 `pending/expired dispatching → dispatching(claim_id, lease)`；随后从该行派生并创建或恢复 claim-bound `server-persistence` grant。
3. Dream 用 grant 读取 Workflow 和 Deck chat-context 快照，构造并启动 `AdminTurnPersistence`。
4. Dream 以 `resume=True` 和 `user_message_pre_persisted=True` 运行原 ThreadFactory/Runtime。
5. Runtime 的全部数据库动作经 Admin DTO/ORM 完成；共享文件仍由 Dream 读取或写入。
6. turn 完成后 Dream 关闭 owner，再 ACK；失败则关闭 owner、保留/延期 claim 并按现有 backoff 重试。

失败处理：Admin capability 缺失、grant 响应不一致、Workflow/Deck 快照不匹配、claim lease 丢失或 Admin 超时均返回失败，不创建无 owner 的 Runtime request，也不调用 Dream DB fallback。未知 claim-turn 响应只允许以相同 DTO/request id 恢复。

## 修改范围

Admin：`packages/db/src/schema/auth.ts`、新的 `drizzle/0062_*` 与 capability contract、delegation Repository/Service、Subject Repository、confirmation DTO/Service/Repository/Handler/Registry/tests、相关 `.folder.md` 和架构文档。

Dream：`story_workspace_confirmation_data.py`、`dream_confirmation_service.py`、必要的 Admin owner composition helper、tests、文件头、阶段/架构文档。混有用户/其他任务改动的目录索引只提交本阶段新增行。

## 验收标准与命令

- Admin typecheck、focused ESLint、Registry/confirmation/delegation unit tests 通过。
- 具名隔离 PostgreSQL 从 0000 replay 到 0062，重复 migrate、fresh/upgrade、约束、capability、并发 claim-turn、claim 过期/替换/ACK fencing 和受限角色验证通过并清理。
- Dream Pydantic contract、coordinator、AdminTurnPersistence 与 ClaudeAgent path tests 通过。
- 测试将 `_db.get_db`、`get_chat_thread`、Session update、plugin DB pack、Deck context mapper、MCP SQL 和 assistant save 设为 fail-if-called；confirmation Runtime 仍成功完成。
- `rg` 清单确认 confirmation dispatcher 不存在 PostgreSQL credential、SQL、ORM 或 fallback；完整 Story Workspace 回归通过。
- Markdown 相对链接、`git diff --check` 通过，两个工作分支分别提交并推送。

## 风险与回滚条件

- 若 migration replay、旧 delegation 兼容或 claim fencing 任一失败，不发布 Registry 121 capability，Dream 保持未消费新操作。
- 若 claim-turn 已发布而 Dream 尚未升级，Registry 120 旧 `claim` 仍可工作；新 Dream 在 capability 缺失时 fail closed，不改用旧数据库。
- 若真实本机服务缺少新 migration/capability，只报告技术验证结果，不将真实业务验收标记为通过。

## 设计评审结论

- 符合认证与数据归 Admin：`claim-turn` 由配置服务身份进入，active subject、actor、Thread、Run、message、claim、scope 与 purpose 均由 Admin 校验或派生，Dream DTO 不接受这些覆盖字段。
- 符合 DTO/ORM 分层：Admin 使用 strict Zod input/output、`StoryWorkspaceConfirmationService`、`DelegationService`、typed Drizzle Repository 和单一 caller-owned UOW；Dream 使用 strict Pydantic DTO 与现有统一 Admin client。
- 事务没有拆分：message claim 与 grant 创建/恢复在同一个事务；Workflow、Deck 和后续持久化是 grant 约束下的独立具名读取/写入，claim 的 share/update 锁保证 ACK 或 claim 替换等待已进入的数据 UOW。
- 保留 Dream 业务执行：ThreadFactory、Runner、Agent Runtime、EventBus、SSE、turn/resume/cancel、admission/resource LKG、共享文件系统和 `.claude-tmp` 协议未迁入 Admin，也未新增队列、控制通道或 Runtime 服务。
- 旧 OAuth delegation 的 source 三列均为 NULL，继续走现有行为；只有 `story-confirmation-claim` 行执行动态 claim fencing。Registry120 五项 descriptor 与 prefix SHA 保持不变。

## 实现结果

Admin 新增 Registry121 `story-workspace-confirmation.claim-turn`。输入仍是 `{message_id, claim_id}`，输出要求 `dispatch/authority` 同时存在或同时为空。`0062_foamy_otto_octavius.sql` 只扩展 `identity.runtime_delegations` 三个 nullable source 字段、message FK、部分唯一索引与行形状 CHECK，并发布 capability `identity.runtime-confirmation-claim.v1`。每次 delegation resolve/renew 以数据库时钟验证相同 message/claim 仍为 `dispatching` 且 lease 未过期。

Dream 的 `AdminStoryWorkspaceConfirmationWorkerData` 校验 Registry121 operation 与 capability 后，把 grant 交给已有 Workflow、Deck 和 `AdminTurnPersistence` 消费端。coordinator 仅在三项 owner 都成功构造后创建 Runtime request；dispatcher 在 drain 前启动 owner，在所有 terminal/error/cancel 路径关闭并 drain owner，Runtime 成功后才执行原 ACK。

契约结果：

| 项目 | 值 |
| --- | --- |
| Registry120 prefix SHA | `4b0bbfa8caecd42acf0ecc89be4153b6d6fb1e124aac4ff27e937ecb14904795` |
| `claim-turn` operation SHA | `c971b5f2ee3517eb9c078d70544bfaa46d74a293afc44b1b8386496d9d081e62` |
| Registry121 full SHA | `969d316b62c1c77aa5f232030d882fd48b36f01b0728cd4f86b877caa99909af` |
| schema capability SHA | `d9de67655e6d8d5ae9654d6502a2cf5d9ab1bb6d829975b243eb25e239b08919` |

## 技术验证回执

| 工作目录 | 命令 | 结果 |
| --- | --- | --- |
| Admin worktree | `pnpm exec tsc --noEmit` | exit 0 |
| Admin worktree | `pnpm exec vitest run app/lib/auth/delegationService.test.ts app/lib/dream/storyWorkspaceConfirmation.test.ts app/lib/dream/storyWorkspaceConfirmationHandler.test.ts app/lib/dream/storyWorkspaceConfirmationRegistration.test.ts` | 4 files、32 tests passed |
| Admin worktree | `pnpm exec vitest run app/lib/auth/schemaContract.test.ts app/lib/db/migration-journal.test.ts` | 2 files、10 tests passed |
| Admin worktree | `pnpm exec vitest run`（15 个 Registry99–121 append/registration files） | 15 files、89 tests passed |
| Admin worktree | `pnpm test:run` | 248 files、1945 tests passed、36 skipped，exit 0 |
| Admin worktree | `pnpm build` | `@ink-memory/db` build、Next.js 16.1.6 production build、TypeScript与19个静态页面全部通过，exit 0 |
| Admin worktree | `pnpm db:generate` | 118 tables；`No schema changes, nothing to migrate`，未生成 0063 |
| Admin worktree | `node scripts/run-story-workspace-confirmation-contract.mjs` | 0000→0062 共63项 replay；第二次 migrate no-op；capability、claim替换、并发同grant、ACK fencing、restricted ACL 4 tests passed；具名库 `ink_story_workspace_confirmation_test_4f055b6af9` 已清理 |
| Dream backend | `python -m pytest -q tests/test_story_workspace*.py tests/test_admin_story_workspace_confirmation_data.py`（临时只读 vendor link，finally精确unlink） | 26 files；720 passed、4 skipped、180 subtests passed |
| Dream backend | `python -m pytest -q tests/test_claude_agent_service.py` | 41 passed、9 subtests passed |
| Dream backend | `python -m pytest -q tests/test_server_claude_agent.py tests/test_claude_agent_confirmation_policy.py` | 115 passed、4 subtests passed |
| Dream worktree | `python -m py_compile`（四个受影响生产模块） | exit 0 |

静态关闭证据：confirmation coordinator 生产模块没有导入 `database`、连接池、SQL 或 ORM；consumer 只导入统一 Admin DTO client。Runtime request 明确携带 `admin_workflow_resolution`、`admin_deck_chat_context`、`admin_turn_persistence` 和 `user_message_pre_persisted=True`；测试把 Dream `get_db/save_chat_message` 设为 fail-if-called，user row 跳过重写且 assistant 经 Admin owner 成功调用。

## 失败分类与修正

1. 第一次新增 capability 查询误用无 schema 的 `schema_capabilities`，在 fixture 写入前失败；按 Drizzle 声明改为 `drizzle.schema_capabilities` 后完整重跑通过，临时库均清理。
2. Story 全套首次因 worktree 缺少既有 `vendor/drama-forge` fixture 出现6个 FileNotFoundError；临时只读链接源仓库 fixture 后全套通过并由 `finally` 精确删除链接。
3. Claude Agent 整文件首次发现旧测试仍 patch Registry120 已移除 guard；改为当前 claim-bound owner/DB-fence 断言后整文件通过。
4. Admin 全套首次只有14个历史 Registry test 将总长度硬编码为120；改为各自 frozen segment 的 append-safe 最小长度，Registry121 独立保留精确总长/全hash断言，目标89项与全套1945项均重跑通过。

## 尚未执行的真实验收

本阶段没有对本机正常 Admin PostgreSQL 应用 0062，也没有启动正常 Admin/Dream/Gateway 或调用真实模型；因此以上是 provider-free 与具名隔离 PostgreSQL 技术验证。真实 confirmation Runtime 业务验收必须在正常服务已经发布 Registry121 与 capability 后，使用用户指定现有账户和业务实体从公开入口执行，并在日常 Admin 中核对 Run、Thread、message、Gateway 与结算记录。本阶段不把该项标记为完成。
