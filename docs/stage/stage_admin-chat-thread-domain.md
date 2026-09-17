<!-- [Input] Dream database.py chat-thread/message functions, baseline CAS/pagination tests and Admin DTO/UOW modules. -->
<!-- [Output] Primary-owned Thread/message DTO and ORM implementation plan for the Admin provider task. -->
<!-- [Pos] Bounded independent execution workstream; Admin task owns common handlers/delegation/schema/registry. -->
<!-- [Sync] 2026-09-14: assign Thread/message persistence to the coordinator while provider/client tasks proceed. -->

# Admin Thread 与消息领域实现计划

## 背景与问题

Dream database.py 的 Thread/消息操作仍执行 PostgreSQL。已有不可变消息身份、精确重放、完成态摘要投影以及含历史 NULL 时间的 keyset 顺序必须保持。
Admin 当前 typed Drizzle schema 使用 number 模式 bigint；领域模块不能将 canonical decimal-string 主体转换为不精确的 JavaScript number。

## 目标与边界

主任务拥有 Admin `app/lib/dream/chatThreadDto.ts`、`chatThreadRepository.ts`、`chatThreadService.ts` 及定向测试。Admin任务继续通用 operation handler/receipt、主体/长turn委托、schema/registry和目录总索引；Dream任务消费具体DTO并保留产品/Runtime执行。
不改schema历史、不执行正常数据库写入。每个写操作接受Admin已验证主体并在同一事务调用Repository，与通用幂等收据一起提交；不能接受外部任意user_id。

## 概念与规则

- 严格输入/输出DTO，ORM entity通过字段白名单投影；canonical ID以decimal string参数化bigint比较/插入。
- 创建/bind/select检查当前用户Deck/Voice关系；voice CAS与固定Deck来源保持。读取/更新/删除/message操作全部检查Thread所有权。
- message id只接受首次插入或同thread/role/parts/metadata语义相同重放；不得reparent/overwrite，重放不touch更新时间。
- message insert与thread touch同Admin事务；assistant completed投影严格对应canonical parts/metadata。错误保留明确409/400/404。
- page保留created_at DESC NULLS LAST、id DESC、limit+1、原时间微秒精度和NULL tail；不将cursor时间经JS Date损失精度。
- corrupt stored JSON保留fail-closed诊断，不把无metadata SQL NULL误判为损坏；客户端公开投影仍由Dream原模块执行。

## Optimized Prompt: Thread/message DTO ORM 实现

You are the primary owner of Admin chat-thread/message DTO, Repository and Service modules. Evidence: Dream database.py functions create/get/bind/select/list/search/delete/title/session/save/list/page/process/latest; existing immutable-envelope and pagination tests; Admin typed Drizzle schema plus capability-gated UOW and strict auth DTO. Read these exact source/tests, selected ownership checks and Admin folder/AGENTS rules. Implement only chatThreadDto.ts, chatThreadRepository.ts, chatThreadService.ts and focused tests in the shared Admin worktree; do not revert other agents' edits. Reuse typed Drizzle entities/UOW, decimal and timestamp DTO, AuthBoundaryError, canonical contract hashing and existing schema capabilities. Define closed named business requests/results, preserve nullable legacy fields, exact integer identity, microsecond timestamp keyset semantics and JSON semantic message replay. All methods take Admin-authenticated principal/delegation context; entity owner/Deck/Voice checks and CAS stay in the database transaction. Services support an existing transaction so generic handler can atomically add the operation receipt; never introduce independent HTTP subtransactions. Keep Dream Runtime/EventBus/SSE/leases/FS unchanged. Validate normal creates/pages/session persistence, unauthorized entities, same-ID replay and conflicting/concurrent insert, strict final projection, bigint and timestamp precision, NULL cursor tail and malformed stored JSON. Delegate deterministic focused tests/typecheck to Luna and keep migration/isolated fixture mutation with the primary. Deliver exact operation DTO/hash files to the Admin registry owner and Dream client task, update this plan with evidence, and do not call full migration complete until production consuming paths and runtime proof exist.

USER REQUIREMENT:
Move Dream Thread/message database persistence into Admin business APIs using DTO/ORM layering while preserving original transaction, permission, concurrency and history behavior.

## 验收与状态

14命名操作的DTO/Repository/Service已实现，Admin任务接入handler/registry/通用收据与委托。Luna focused11测试/tsc通过，先前lint通过；实体权限/CAS/消息重放/ORM运行及Dream生产消费仍待完整集成验证。
定向验证回执、operation DTO/hash和Dream替换关闭证据另行记录，当前不得声称生产迁移完成。


本轮真实生产Route/ORM隔离技术回执：首次socket/tsx harness失败不判业务；到达Route后503为0032旧capability digest，与真实既有0033已发布摘要不符，修正owned service strictgate引用。其后故意invalid DTO的request_id断言失败为harness缺X-Request-Id（真实Dreamclient始终必发），按真实协议修复并保持断言。Luna原合同exit0、route_calls_assertions59，验证owner/scope/CAS/semantic replay/concurrent receipt/audit/final/process/exactmicrosecond/NULL。完整14operation覆盖缺口追加后待fresh验证；这不是Dream实际生产全部SQL关闭或真实Google/model验收。详见[原公共合同通过回执](../exec/admin-auth-data-verification/thread-public-contract-protocol-fix.md)。

## 全14与受限角色结果

所有14个封闭operation、93条公共Route断言已由Luna在自有隔离库执行退出0；随后用真实受限AUTH/DATA角色重复对应权限边界阶段，也退出0。owner连接只用于harness只读目标身份/audit proof。最终定向lint退出0。Thread领域Admin接口合同验证通过；Dream全域迁移与生产入口运行证明不因此视为完成。回执：[all14](../exec/admin-auth-data-verification/thread-public-contract-all14.md)、[受限角色](../exec/admin-auth-data-verification/thread-public-contract-restricted-roles.md)。


## Optimized Prompt: 原始 user message 聚合与 confirmation guard

You are the primary owner of ChatThreadRepository and existing ChatThreadService; Admin owns new atomic user-message DTO/Service/Handler and confirmationGuard/Repository. Evidence: existing14operations93restricted-route assertions pass, actual original confirmation source classifies stored row/reserved namespace and preserves fresh lease rather than overwriting queued stale state; fixed pure helper preserves strict raw numeric canonical/fingerprint/source-derivedmessageID and Python claim equality. Read existing persistMessage and original public initial-user-message/title transaction. Add persistUserMessageRaw(input:{thread_id,message_id,parts_json,metadata_json},title:string) only in owned Repository: strict string JSON shape checks, canonicalBusinessJson on raw parts/metadata, owned Thread update lock, per-user persisted guard using stored row, exact immutable id/role/thread/canonical parts+metadata replay, insert+Thread touch+missing-title update in caller UOW; full generic receipt still Admin Service. Call Admin-owned guard for every generic role=user after owned Thread update lock, including requests without incoming confirmation markers, true returns original id without write/title/touch/lease override. Do not copy guard or new DTO/registry; wait for owner-export before import. Retain existing assistant/final/projection/keyset behavior, no duplicate SQL HTTP services or remote policy/Runtime changes. Canonical part equality preserves original numeric categories; metadata null versus object remains distinct. Title comes from Dream existing pure extraction; Admin owns configuredUnicode truncate only when title is missing. Admin-owned guard validates closed command/metadata/activeRun/workspace/current and queued leases; primary only calls it. Add affected raw message integration tests through new public production operation once registered and rerun changed14flow/confirmation cases; primary owns direct owned fixture/fault setup, Luna only deterministic/public/read-only verification. Update headers/folder docs/canonical contracts and retain old93PASS as historical pre-guard evidence, not new guard acceptance.

USER REQUIREMENT:
迁移 user-message insert 与自动Thread title 的原事务到Admin，并保持确认消息持久化claim lease保护，遵从DTO/Service/Repository/Drizzle，保留Runner/Event/SSE turn行为。


## Stored confirmation guard 后的原合同回归

Luna在实际受限AUTH/DATA角色下重跑受影响的原14operation，93条公开Route断言通过；完整无缓存types和定向lint退出0。[post-guard回执](../exec/admin-auth-data-verification/thread-post-confirmation-guard-regression.md)与旧历史结果分开保留。新raw user-turn聚合和确认claim业务用例另由主任务准备全FK隔离fixture，再通过原公开operation验证，不把原93条当成新增确认接口验收。
