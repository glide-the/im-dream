<!-- [Input] Actual Admin strict context/raw-user DTOs, guard and public delegation/receipt routes; frozen60 history. -->
<!-- [Output] Primary-owned Workflow fixture lifecycle and Luna public contract acceptance evidence. -->
<!-- [Pos] Coordinator phase; SQL schema remains exclusively Admin Drizzle and Runtime remains Dream. -->
<!-- [Sync] 2026-09-15: prepare named isolated FK-valid provenance/control fixtures before public verification. -->

# Workflow 上下文与 user-turn 原子接口验证

## 背景与问题

Thread 14 项及 Deck 19 项公开合同已经通过。新增 `workflow-context.resolve` 与 `chat-user-message.persist` 涉及冻结启动消息、重试图、Run/Workspace/binding 关系与原始 JSON，单元 mock 无法证明真实 ORM、权限和事务行为。当前生产 Workflow 完整 command 与 Dream 消费仍在其他任务实施，不据此声明全部访问关闭。

## 目标与边界

主任务创建 `_workflow60` 具名隔离库、完整 FK fixture、短期私有签名凭据和受限 AUTH/DATA 配置；直接准备/故障注入只限已验证本轮数据库。Luna 只执行现有公开 Route 与只读 catalog/receipt/audit 查询。Admin 任务拥有 DTO、guard、registry、harness 与 Workflow 全命令；Dream 任务保留 Runtime、SSE、文件系统并消费接口。

## 概念与规则

- context 必须从 owned Thread、完整 retry graph、冻结 launch metadata、当前 Agent 和 binding 读取，外部 run_id/actor 不构成授权。
- parent status、唯一 root/leaf、完整 frozen tuple、源码 fingerprint/input hash 校验在 terminal 返回 null 前执行。
- active Run 新 grant 必须与当前 context 精确匹配；已有 grant 可在 owned Run terminal 后完成末次持久化，新 grant 不能复用 terminal Run authority。
- user-turn 保存原始 parts/metadata、首次 message identity、缺失标题与 Thread touch 在同一 Admin UOW；重放不改 immutable message 和 Thread 时间，metadata NULL 与 object 不混同。
- stored control 与 reserved namespace 决定确认记录保护，旧 queued lease 不能覆盖当前有效 lease；claim 改动、过期、错 owner/Run/hash/parts 与新伪造 control 全部拒绝。
- 所有失败与恢复均走原 Route，保留实际 status/request_id；harness 凭据只存私有0600文件，不进入项目回执。

## Optimized Prompt:

You are the primary owner of isolated Workflow provenance/raw-user fixtures; Luna owns the bounded non-destructive public contract stage. Evidence: frozen0000–0059 exact Drizzle history/ledger60 and restricted ACL proofs pass; Thread14/93 post-guard and Deck19/246 pass; Admin strict workflow-context.resolve and chat-user-message.persist plus existing runtime-delegation and receipt routes are implemented and unit/type/lint validated. Read actual workflowContextService/Repository/DTO, source DreamThreadContextMapper and confirmation service, complete typed release/lock/binding/snapshot/preflight/Run FK/CHECK/trigger contracts and current public harness. Clone only the independently verified empty owned fresh60 replay database into named _workflow60, verifying current_database/current_user/loopbackport/data_directory before every write. Apply the existing explicit four-role ACL runner; production pools use limited AUTH/DATA credentials and no owner URL. Seed technical actors, owned/foreign Threads, complete source launch/linear retries and FK-valid release/lock/binding/snapshot/preflight/Run data, including valid active/terminal contexts and corrupted but constraint-valid graphs/provenance. Derive launch/confirmation hashes and IDs using actual pure/source functions, never duplicate the business resolver or state machine. Create a terminal-bound grant through the actual public create route while active, then primary-only transition the owned fixture Run terminal; retain its bounded encrypted grant. Prepare raw ordinary/missing-title/split-write records and current confirmation claims with older queued lease/equal Python metadata, stale/newer/changed/missing-kind/forged/foreign cases. Keep direct setup/faults separate from public assertions and sanitize all raw receipts. Luna runs existing production operation/delegation/receipt routes plus read-only owner proof and asserts exact context/null/conflict, owner/scope and strict fields, whole title/message transaction, raw float/bigint/NULL bytes, replay/no-touch, terminal final persistence, control snapshot/lease preservation and one receipt/audit. On failure identify fixture/harness versus actual product defect, repair by ownership and rerun only failed/affected cases without relaxing assertions. Preserve normal services/database/real-account/model/FS/Runtime semantics; no migration replay or real-acceptance claim. Update this plan, affected inventories and exact coordinator-owned worktree mirror with command/cwd/exit/output and coverage limits.

USER REQUIREMENT:
使用真实 DTO/Service/Repository/Drizzle 和公开生产入口验证 Workflow 身份来源、user-turn 原事务、确认 claim 保护、并发重放与权限，明确区分隔离技术验证和正常本机真实业务验收。

## 验收与风险

验收：完整 target identity 与有限 roles；有效 active/linear-retry/fallback slug/current Agent、完整 terminal 检查、invalid binding/source/branch/parent conflict；new/existing grant authority；raw numeric/NULL/immutable replay/title恢复；confirmation stored-based分类和 lease/claim/parts拒绝、generic user 同样保护；receipt/audit原子单次。完整 Workflow 状态事务和其他域全量访问仍独立验收。

风险：不能用失效的先前300秒Token；不能关闭FK/trigger创建fixture；不能把 canonical text 经JS Number重编码；helper/secret/日志仅按现有配置；随机数据只在明确命名的harness文件和隔离数据库。

当前状态：18上下文/14确认用例的公开170断言已通过；完整Run五操作另见独立163阶段，其他Workflow事务继续推进。


## 实际结果与测试准备修复

完整18context与14confirmation fixture已完成。初轮公开grant已成功，但无Runtime receipt/session的fixture直接running→completed被原joint binding guard拒绝SQL55000，原回执保留。remaining脚本只读复用原成功core，不重新建库/插入或迁移，以实际公开新grant后执行原允许cancelled/status_version+1转换；保留FK/trigger。新增source oracle直接调用原Python Command模型/hidden_parts/fingerprint/messageID，未复制状态机。

Luna `python3 /private/tmp/ink-auth-migration-validation/run-workflow-contract.py` cwdAdmin729f退出0：5个公开接口族、18contextcases、14confirmationcases、170断言通过。有效当前Agent/linear leaf/fallback与terminal、坏metadata/binding/graph/µs/owner/status拒绝；grant新context限制与旧terminal末次persist；raw float1.0/bigint/NULL、title原子补齐、不可变重复/冲突；stored classification、旧lease保护/数值claim Python equality与过期/更晚lease/错Run/hash/parts等拒绝、generic user同样guard；原receipt/audit各单次通过。见[170回执](../exec/admin-auth-data-verification/workflow-public5-context-confirmation.md)、[初轮准备失败](../exec/admin-auth-data-verification/workflow-fixture-initial-failure.json)、[最终准备事实](../exec/admin-auth-data-verification/workflow-fixture-preparation-proof.json)。

这是provider-free受限角色技术验证。完整Run写事务、全部Dream生产SQL入口关闭与真实Google/正常账户模型验收仍未完成。
