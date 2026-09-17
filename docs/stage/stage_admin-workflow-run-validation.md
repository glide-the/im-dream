<!-- [Input] Actual Admin Run DTO/ORM commands, immutable Runtime bindings and proven isolated ledger60. -->
<!-- [Output] Primary fixtures, public Run lifecycle/create/retry acceptance and retained exact command receipts. -->
<!-- [Pos] Cross-project coordination; Admin persists whole state transactions and Dream executes Runtime. -->
<!-- [Sync] 2026-09-15: record Run72 original failure, remaining230 and selected atomic68/cleanup3 evidence. -->

# Workflow Run 状态事务验证

## 背景与问题

`workflow-run.read/history/start/fail/cancel` 已在 Admin 实现并完成 focused、typecheck 和 lint。先前上下文测试使用的 Run 不具备完整 started Runtime 回执和 Session 绑定，仅证明上下文边界，不能作为完整生命周期验收。六项 Deck runtime 数据接口的公开合同正在独立修复认证错误码，原失败保留。

## 目标与边界

主任务负责本轮已核验 `_workflow60` 隔离数据库中的完整 fixture、短期凭据和故障准备；Luna 只执行现有公开生产 Route、只读状态和回执查询。Admin 任务拥有 Run DTO、Service、Repository、Handler、registry 和公开 harness；Dream 任务消费接口并保留实际 Runtime、文件系统和 SSE。不得修改正常数据库、重放已通过迁移、关闭 trigger 或复用不完整上下文 Run。

## 概念与规则

- Admin 原事务内锁定 owned Run/Workspace，校验 readiness、lock digest、creating Session 和明确 placement，再原子激活 Session、CAS Run、追加一项历史并提交 receipt/audit。
- start 只接受 OAuth；fail/cancel 可接受原 Thread/Run 精确绑定的 server-persistence grant。不同 Run 的同主体 grant 不得恢复原回执。
- 使用真实 `run_`、`pf_`、`as_`、`wrt_` 格式、完整 FK、原 status/version/joint binding/时间规则；原始 JSON 数值经现有纯 Python helper 计算 digest，不经 JS Number 重编码。
- queued start、同目标重放、终态拒绝、缺失/不匹配 readiness/Session、错误 owner/scope、并发同 request_id、不同输入冲突及未知提交结果恢复均走同一公开接口。
- command clock 来自实际 PostgreSQL；harness 只对比精确微秒结果与持久化值，不注入业务时钟。
- 凭据只存私有 0600 文件；公开证明仅包含目标身份、命令、退出码和脱敏输出。这是 provider-free 技术验证，不能代替正常本机真实模型或 Runtime 验收。

## Optimized Prompt:

You are the primary owner of isolated full Workflow Run fixtures. Evidence: exact Admin Drizzle ledger60, restricted AUTH/DATA roles, prior Thread14/93, Deck19/246 and Workflow context/raw-user170 assertions pass; Admin five Run operations and their public harness are implemented and focused/type/lint verified. Before setup, read actual workflowRunDto/Service/Repository, workflowRunCommandDto/Service/Repository, adminWorkflowRun.contract.ts, original Python WorkflowRun/Transition validators, runtime_load_receipts/agent_sessions schema and original immutable/joint-binding/status triggers. Use the existing independently named _workflow60 database and verify database/user/loopback port/data directory and limited production pools before every owner write. Reuse only known actors and complete immutable release/lock/binding references; create new fully valid pf_/run_/as_/wrt_ identities, original complete provenance, owned/foreign workspaces, legal initial and queued history, persisted readiness/lock hash and creating Session placement. Preserve previous context-only and control fault cases untouched. Derive canonical digest using actual pure helper, and expectations from original strict lifecycle model with precise microseconds. Prepare successful read/history/start/fail/cancel and rejected wrong owner/workspace/Run-grant/readiness/Session/terminal cases. Obtain fresh ES256 at+jwt and exact purpose-bound Run grants through actual public routes; never export private signing keys or print tokens. Luna executes tests/integration/adminWorkflowRun.contract.ts through a named private launcher; only public commands may write and owner verification is SELECT-only. Assert original whole Session+Run+history+receipt/audit transaction, CAS/status/version, exact binding and clock, same-request concurrent/replay single result, conflicting request rollback, unchanged denied state and original Run-scoped recovery. Classify failures as fixture/harness versus product, retain original receipts and fix by file ownership without relaxing assertions. Update this phase, affected coordinator inventories and explicitly owned worktree mirror. No actual Runtime/CLI/model/Google/normal DB action or migration replay.

USER REQUIREMENT:
按严格 DTO → Service → Repository → Drizzle ORM 验证完整 Workflow Run 的权限、状态事务、Runtime 绑定、并发和提交恢复；保护现有数据并区分技术验证与真实业务验收。

## 验收命令与风险

Luna 执行已存在 `tests/integration/adminWorkflowRun.contract.ts`；主任务 launcher 明确工作目录、私有 fixture 和受限配置。记录实际命令、退出码、断言数与覆盖范围。主要风险是短期凭据过期、不完整 Runtime binding、错误来源时间精度、已有 fixture 状态改变后盲目重跑、同一 request_id 混入新输入。仅刷新必要凭据，不重新建库或重置已成功业务结果。

当前状态：完整4Run/21cases准备成功，原公开五操作163断言通过；完整创建/重试/启动与真实Runtime验收待后续。


## 公开合同结果与 UTC 修复

主任务在原_workflow60 ledger60准备4个全新完整Run与21公开cases，原strict模型/完整source FK/readiness entries/creatingSession lease/settings/placement/lock digest/历史均验证，2实际公开Run grants成功，旧context-onlycases未动。首次Luna读取比较失败，主任务只读发现PG::text使用+08，而fixture为UTC同瞬时µs。原业务Service._row_to_run/_row_to_transition调用_parse_datetime.astimezone(UTC)，直接Model接受offset不足以替代实际Service规范化。主任务调用实际原Service只读12断言证明UTC；Admin仅在Workflow投影与command clock补齐UTC六位微秒，未改共享Chat/Deck时间/DTO/hash/权限/状态/fixture预期。最小40测试及wholetsc/lint/diff修复后通过（并发schema导出错误初回执保留）。

主任务仅刷新短期JWT和两个实际publicRun grants，不重置业务；原Luna `python3 /private/tmp/ink-auth-migration-validation/run-workflow-run-contract.py` cwdAdmin729f退出0：5ops/21cases/163断言通过。完整读取/历史、exactµs、OAuth-only start、wrongRun/owner/Workspace/readiness/Session拒绝、同UOW Session激活/Run CAS/一历史/receipt/audit、并发同request单次、同目标重放不touch、终态拒绝、fail/cancel及exact originalRun+Thread恢复通过。[163回执](../exec/admin-auth-data-verification/workflow-run5-public163.md)、[初失败](../exec/admin-auth-data-verification/workflow-run5-initial-utc-failure.md)、[原Service12证据](../exec/admin-auth-data-verification/workflow-run5-source-projection12.json)。

这是受限角色provider-free持久化合同验证。Preflight执行、Run创建/重试/完整启动与真实Runtime/model/正常本机业务验收仍未完成。


## Run 创建与重试：72 项注册后的公开验证规划

### 背景与问题

已核验 Admin 规范目录为 72 项，新增 `workflow-run.create` 与 `workflow-run.retry`；原 70 项完整描述符、原 Preflight receipt 和专用 delegation 契约保持不变。注册 focused 47 项、原请求/存储字符源对照 2 项及原结果恢复 1 项通过，完整 typecheck、定向 lint、diff 检查退出 0；初次 Vitest 参数和 source 路径错误保留。这些结果尚不证明公开创建/重试的持久化事务。

### 目标与边界

Admin 任务负责 DTO、Service、Repository、Handler 与公开集成 harness；主协调负责经身份核验的具名隔离数据库、fixture、凭据与故障恢复；Luna 执行已准备的非破坏性公开合同。Dream 任务消费实际发布契约，业务来源准备、dispatch、Runtime 与流式输出继续按原顺序迁移；本阶段不迁移其业务执行所有权。

### 概念与规则

创建输入保持 workspace、Preflight/token、原 business key 与全部 null 或完整 Voice 来源三元组；retry 加原 Run 标识，来源由原 Run 派生。严格 DTO 校验、owner/工作区/来源权限、当前 release/lock 与 original semantic fingerprint 由 Admin 执行。首次创建将 Run preflight 状态、第一次 transition、Preflight CAS 消费、queued 状态和第二次 transition、精确 Run/Thread scope receipt/audit 放入一个事务；retry 的只读先决阶段不写入，随后重新锁定并校验原来源。禁止将事务拆成多个无恢复保证的调用或对未知写入盲目重试。

### Optimized Prompt:

You are the primary owner of public Workflow Run create/retry acceptance after actual registration. Evidence: the canonical Admin operation catalog contains 72 operations; old 70 complete descriptors and special receipt/delegation artifacts are unchanged; source/atomic/ingress and focused registration gates pass. Admin owns strict Zod Route → Service → typed Repository → Drizzle plus the public integration harness; Dream owns its consumers and preserves source preparation before Preflight/Run and dispatch persistence before Runtime acceptance. Read actual workflowRunCreationDto/Service/Repository/Handler/Semantics, receipt binding and production Route, original Python request validators and _create_run/retry implementation, immutable Preflight/Run/transition triggers, and existing isolated ownership/ACL proofs. First verify database name, current user, loopback port, PostgreSQL data directory, exact capabilities and limited AUTH/DATA production connections; prepare only new canonical fixtures in the owned disposable target. Keep previous Preflight and Run test history unchanged. Derive complete expected outputs and semantic fingerprints from original Python behavior, preserve microsecond UTC, raw canonical JSON, exact subject IDs and Python codepoint/blank rules. Cover fresh create, business-key semantic replay with a new valid Preflight, consumed Preflight replay, conflicting key/source, complete Voice source, malformed source, expired/failed/consumed token, current release/lock drift, foreign owner/Workspace/source, readonly/missing/delegated credentials, same-request concurrent writes, retry allowed terminal states and rejected nonterminal/same-key/source mismatch. Assert Run + two transitions + Preflight consumption + bounded receipt/audit are atomic and unique, replay is unchanged, denied writes roll back and receipt recovery retains original Run and Thread scopes. Primary owns triggers/faults and unknown-commit recovery; Luna executes only the prepared public-route contract plus SELECT verification with exact commands, exit codes, assertion counts and cleanup boundaries. Preserve actual failures, classify harness vs product, repair by owner and rerun only affected paths without changing expected semantics. Update this plan, coordinator results and reviewed worktree mirror. No normal database migration, Google, real account/model, Runtime/CLI, user-service restart or baseline mutation.

USER REQUIREMENT:
继续跨项目重构，按 DTO/ORM 设计验证 Admin Run 创建/重试的完整生产接口与原事务、并发、权限和恢复；再让 Dream 消费，不能把注册或 isolated 检查当真实业务验收。

### 验收命令与风险

Admin 任务提供实际集成 harness 后，主协调创建仅含新 fixture 的私有 launcher；Luna 返回工作目录、完整命令、退出码和关键输出。主协调另行执行需要故障注入的 rollback/unknown commit 检查。新写操作不重放已经改变状态的旧 fixture；凭据临执行准备，不通过修改原时间或期望修正自然过期。尚待公开接口回执、Dream 相关入口关闭和正常本机真实业务验收；协调目标保持 active。


### Run72 分层公开合同实际回执

首次 `run-run72-public-contract.py` 退出1，在第六成功流程之后的 readonly 错误码预期停止；不虚构未输出断言总数。主协调只读复核六项原完整static、Run/Thread scope、单receipt/audit和新Run双transition通过。remaining harness默认full原断言不变，显式范围仅跳过六原acceptedPOST并SELECT校验完整bounded结果；实际 `run-run72-remaining-contract.py` cwdAdmin729f退出0：22拒绝、10回执、230断言。三个未执行时效operand各新request/PF保持11项frozen字段、输入哈希完全相同，旧signed期限不改。仅readonly预期按实际共享Auth校正ACCESS_SCOPE_REQUIRED；source/secrets/env类型失败与修复实际gate保留。后置主SELECT证明八核心业务表逐字节JSONtext未变，正常数据库不变。

这不是原28一次全通过，也不是普通本机真实Google/用户/模型/Runtime验收。原子写fault、unknown COMMIT与Dream完整业务执行仍按[新恢复阶段](stage_admin-workflow-run-create-recovery-validation.md)继续。

Run72原子故障与unknown commit业务68通过；原命令因primary cleanup helper scope退出1，独立SELECT cleanup3退出0，九组对象均无残留。原结果/两次历史/消费/receipt/audit均恰一次，正常数据未动。窗口释放，详见上述恢复阶段。

- [run72-contract-parity.json](../exec/admin-auth-data-verification/run72-contract-parity.json)

- [run72-public-luna-receipt.md](../exec/admin-auth-data-verification/run72-public-luna-receipt.md)

- [run72-remaining-public-luna-receipt.md](../exec/admin-auth-data-verification/run72-remaining-public-luna-receipt.md)

- [run72-prior-accepted-proof.json](../exec/admin-auth-data-verification/run72-prior-accepted-proof.json)

- [run72-post-remaining-preservation-proof.json](../exec/admin-auth-data-verification/run72-post-remaining-preservation-proof.json)

- [run72-public-disclosure-proof.json](../exec/admin-auth-data-verification/run72-public-disclosure-proof.json)
