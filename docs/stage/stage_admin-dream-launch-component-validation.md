<!-- [Input] Actual Dream launch callsites, Admin closed component DTOs and prior Run72 evidence. -->
<!-- [Output] Cross-project source/claim/finish public contract and isolated recovery acceptance plan. -->
<!-- [Pos] Coordinator-owned launch persistence validation; complete Runtime launch remains a separate gate. -->
<!-- [Sync] 2026-09-15: retain first failure and37-case/21-GET/974 continuation, with308 recovery evidence. -->

# Dream 启动来源与派发元数据的接口验证

## 背景与问题

制定本计划时 Admin 已注册 72 项操作。Run 创建/重试的剩余公开合同通过 230 个断言，选择性事务故障与真实最终 COMMIT 后响应丢失通过 68 个业务断言；原故障命令退出 1，独立清理检查退出 0、3 个断言通过。详见 [Run 计划](stage_admin-workflow-run-validation.md) 和 [事务恢复计划](stage_admin-workflow-run-create-recovery-validation.md)。这些结果不覆盖 Dream 启动来源或派发。

当时 Admin 正实现未注册的 `dream-launch-source.ensure`、`dream-launch-dispatch.claim` 和 `dream-launch-dispatch.finish`。实际 Dream `DreamLaunchApplicationService.launch` 的指纹参数在 Agent 为 NULL 时不包含 `agent_id` 键；此前未注册候选对 helper 的调用包含该 NULL 键，不能代替完整应用调用处等价证据。该缺陷修正与后续75注册结果见末节；原 72 项契约、已验收 Run 数据和历史回执继续保留。

## 目标与边界

Admin 任务负责生产 DTO、typed Repository、Service、Route、capability 和规范契约。Dream 任务负责消费接口及保留来源准备、Preflight、Run、claim、Runtime 调用、finish 的原编排顺序。主协调负责本计划、隔离目标身份、凭据、fixture、故障注入及回执审核；已有 Luna runner 只执行明确的确定性或已准备公开非破坏合同。

本阶段验收三个持久化组件，不宣称完整启动、Agent/model/binding 准备、失败记录或 Dream 全域数据库迁移关闭。生产认证、事务、权限和 SQL 均由 Admin 执行；Runtime、SSE、资源准入及共享文件执行仍属 Dream。不得更改线程工作区、符号链接限制、0700 或 `CLAUDE_CODE_TMPDIR` 协议。

## 概念与规则

- Source 输入仅 owned Workspace、Deck、可空 Agent、goal 和原 ASCII 业务幂等键。Actor、确定性 Thread/message 标识、指纹、metadata、clock 由 Admin 推导。实际应用调用处与实际 `ensure_source` 的参数、完整结果、提交顺序均须对照，覆盖 Agent 有值及 NULL。
- Source 同一原请求恢复完整初始结果和原时间；同业务键同内容返回同一来源，不覆盖已被 claim/finish 更新的 metadata 或 Thread 排序。不同内容、失去权限及非法控制字段失败且不产生部分写入。
- Claim 输入仅 owned Workspace/Run 和 Dream 已生成的 instruction text。Context、source、claim 标识及 envelope 来自当前存储。事务提交后 Dream 才执行后续 Voice 读取和 Runtime；finish 是另一笔事务，不合并为跨 HTTP 的假原子操作。
- 原 dispatched 或 fresh dispatching 返回明确 no-claim；过期 lease 可生成新 claim。精确 TTL、微秒和 legacy 时间解析由实际原 dispatcher 对照，不延长旧 fixture 的时间以掩盖过期。
- Finish 只接受原 Run、服务签发 claim 和 accepted 布尔，固定映射原 pending/dispatched。旧 claim 不匹配时保持当前 lease，不覆盖后续 claim。
- Original receipt GET 仅原操作/request 与 OAuth write 身份。Source 重验当前 owned scope、原输入摘要及 source；claim 恢复重验当前 active lease、完整 parts/context/runtime metadata；finish 仅返回原有界结果。GET 不提供新的 Runtime 权限。
- 服务身份与用户 OAuth 委托分别检查；readonly、其他主体、缺失 Token、purpose-bound entity grant、任意 Actor/metadata/context patch 均不能扩大权限。所有业务写入与 result/audit 按原组件 UOW 保持一致。

## Optimized Prompt:

You are the primary coordinator of the next Admin-owned Dream launch persistence acceptance stage. Read the actual unregistered SourceEnsure and DispatchClaim/Finish DTOs, typed repositories, services, handlers, OriginalReceiptService, transaction and receipt routes, plus the final producer registration and source-callsite receipts. Trust the producer's scoped exploration and inspect only fixture/acceptance dependencies. First require actual registered operation artifacts, exact schema/API capability requirements and complete original72 descriptor/requirement/capability parity; preserve original Preflight receipt and delegation artifacts. Require the actual DreamLaunchApplicationService.launch capture for both nullable and non-null Agent, not a manually reconstructed helper input. Record any original failure and only rerun affected gates after correction.

Before privileged setup, prove a new explicitly named disposable target on the already owned loopback PostgreSQL instance by database name, owner role, server port and data_directory. Reuse Admin Drizzle-only existing capability and restricted AUTH/DATA credentials; never migrate or seed normal services. Prepare each new source and Run through public registered production operations using full real DTOs and exact semantic/source oracle expectations. Keep all previously accepted fixtures, original IDs/times, capabilities and protected state unchanged. Store credentials only in named 0600 private files. Supply Luna one bounded public POST/GET contract with exact wrapper command, cwd, output paths, explicit prepared cases and cleanup ownership; wait for raw exit-code receipts.

Validate Source first create, same request replay, same business key replay and conflict, Agent-null/full-callsite fingerprint, owner/Workspace/Deck/Agent mismatch, forbidden control fields, codepoint/whitespace boundaries, concurrent source creation and original receipt permissions. Validate claim against actual dispatcher source: first claim, dispatched/fresh no-claim, expired lease replacement, concurrent claims, full parts/context/raw metadata preservation and original GET active-lease checks. Validate finish accepted/rejected, mismatching old claim, duplicate input and original receipt. Compare complete bigint/raw numeric/negative-zero/Unicode/microsecond fields without JavaScript rounding or copied business algorithms. Do not execute Runtime, models, Google or user workspaces in this technical stage.

Primary alone injects selected new-key source or claim/finish transaction faults and a single transport failure only after real final COMMIT and exact receipt visibility. Assert whole component rollback including source/Thread/message/Run/lease/result/audit; recover by original receipt and same-input replay without a second effect. Use separate fresh operands for unexecuted naturally expired cases, documenting frozen-fact equality and skipped accepted cases; never reset accepted state, alter old expiry, remove guards or relax assertions. Capture actual commands/cwd/exit codes and safe raw evidence, inspect cleanup of only owned fault objects/pools, secret-scan before archiving and merge only coordinator-owned documentation into the protected worktree. Keep full migration and real acceptance goals active.

USER REQUIREMENT:
遵从 DTO/ORM 将 Dream 数据库访问迁为 Admin 业务接口，保持原权限、事务、幂等、Runtime 与共享文件语义，并提供可核验的真实命令结果；隔离验证不能冒充完整启动或正常本机真实业务验收。

## 状态与验收顺序

| 步骤 | 输入与依赖 | 通过标准 | 失败与恢复 |
|---|---|---|---|
| 注册前评审 | 实际调用处源对照、生产候选、完整旧72快照 | NULL Agent 与非NULL等价；注册与当前规范一致 | 保留原失败，仅修候选和受影响测试 |
| 具名目标准备 | 已验证隔离实例、当前 migration/capability、受限角色 | 名称/role/port/datadir正确；来源只读指纹不变 | 身份不符停止该准备，不连接正常库 |
| Source 公开合同 | 新 owned Workspace/Deck/source command | 完整结果与源一致；并发仅一来源；原回执权限正确 | 原子回滚；未知结果先GET，不盲重试 |
| Claim/finish 公开合同 | 新公开 Run/source、实际数据库 clock | 完整metadata/source/lease/parts/context和原事务顺序一致 | 旧lease no-op；过期恢复不新增权限 |
| 故障与提交恢复 | 每项新 key/request/fixture | 全组件rollback或原COMMIT单效果可恢复 | 保留失败、原退出码；仅清理本轮对象 |
| 消费与文档 | 真实注册DTO、原Dream编排、原始回执 | consumer用真实接口；代码/执行证据与索引同步 | 全启动、其余SQL、真实验收仍单独跟踪 |

## 影响范围、命令与风险

拟修改主协调本计划、[执行报告](../exec/exec_admin-auth-data-coordination.md)、stage/evidence 索引及其受保护 worktree 镜像；生产代码由相应任务拥有。确切公开命令须由最终生产 harness 交付后登记，不预先伪造回执或操作数量。Luna 执行 source/contract/lint/typecheck 和文档 gate；主协调执行身份/fixture/故障/秘密检查。

风险包括指纹 NULL 键与实际调用处差异、Python/Pydantic Unicode 边界、unknown numeric metadata、lease 自然过期、不同 UOW 的响应丢失及旧 request 恢复失去当前权限。依据原 source 和 actual public behavior 分类；保留第一失败，不能通过修改产品状态机或断言隐藏问题。公开数据库验收尚未执行；正常 Google、现有账户/实体/模型、全启动和 Dream 全生产入口无直连仍 pending。

## 注册与隔离目标实际结果

后续实际应用 NULL Agent 对照第一轮退出1、fingerprint差异已保留；只修未注册候选遗漏NULL key语义，受影响实际source2与原GET24、全type/lint/AST/diff退出0。source/claim/finish已实际注册75，旧72完整descriptor/requirements/capability和独立PF receipt/delegation原字节均保持；注册后Route3/Receipt7共10测试、全type/lint/diff退出0。主协调只读了这些真实 raw gate，没有重跑已通过范围，也未将注册作为公开DB通过。

新项SHA分别为source `cb498be127a6aca92c9e6e0cde099c9c80cf78ca2486186e9d043457c2263503`、claim `958549a9bfe4b02d8b31e1e538c81ffad020bb4525a328f542f865b377e8ec43`、finish `5aa3b738bef5319ee705f5851d83588e1d18dcaf37bdc5789267494fec480f2e`；均OAuth dream:write、exact identity/unified既有capabilities，不新增migration。

主协调实际 `python3 /private/tmp/ink-auth-migration-validation/prepare-launch75-target.py` cwdAdmin729f退出0，准备具名 `ink_auth_data_codex_test_792494523a17_launch75`。来源仅此前本轮可删除的 `_run72`；每步确认owner/127.0.0.1/51534/datadir `/private/tmp/ink-auth-data-migration-20260914-792494523a17/postgres`，拒绝既存目标和活跃来源会话。来源125表before/after完全一致，fingerprint SHA `df7dfed77316102b9bf860f1ba518758adef98236305852eed90318883b177c5`；未重放migration，受限ACL真实apply退出0，identity/unified及PF request exact cap匹配，ledger61仅记录该具名目标历史。

私有owner/ACL/base/env均exclusive0600，不输出凭据。目标proof在 `/private/tmp/ink-auth-migration-validation/launch75-target-proof.json`，ACL命令在同目录 `launch75-target-acl-command-receipt.json`。当时新业务fixture/公开POST/GET/并发/故障尚未执行；后续实际结果如下。正常5433数据库、Google、账户/模型/CLI和用户服务均未操作。完整prepare/failure/Runtime启动及全域no-PG/真实验收仍开放。

## 首轮公开失败与继续验证边界

主协调实际 `python3 /private/tmp/ink-auth-migration-validation/run-prepare-launch75-fixture.py` cwd Admin729f退出0、46个准备断言，生成38个case、18个原GET检查点和15个成功场景。四个新claim Run均通过真实公开Source、Preflight和Run接口准备，完整Run/source结果与实际Python源对照。原Goal-only input digest、可空Agent prompt、bigint/raw numeric/negative-zero/Unicode metadata和新过期/非法lease各有独立预期；旧Run72记录及过期时间不修改。该46项是准备检查，不能报告为公开38项已经通过。

Luna实际 `python3 /private/tmp/ink-auth-migration-validation/run-launch75-public-contract.py` cwd Admin729f退出1，内层为 `node --import tsx tests/integration/adminDreamLaunch.contract.ts`，停在原GET状态断言，未输出通过总数。主协调随后实际 `python3 /private/tmp/ink-auth-migration-validation/run-diagnose-launch75.py` 退出0，只新增本轮隔离技术JWK、SELECT业务状态及公开GET，没有重复POST或修改原fixture。

诊断证明只有 `source-new-null` 的原receipt已提交。该Source的user GET返回200 committed、other返回200 absent、readonly返回403 ACCESS_SCOPE_REQUIRED、entity grant返回403 DELEGATION_PURPOSE_DENIED；查询含 `actor_id` 时共享身份边界先返回400 USER_OVERRIDE_FORBIDDEN，首轮harness错误预期了后续闭集路由的404 OPERATION_UNAVAILABLE。实际共享边界明确拒绝主体覆盖，不修改生产接口、身份校验或权限规则。修正保留相同actor query并断言实际400，另以无主体覆盖含义的额外参数验证404闭集行为。

主协调实际 `python3 /private/tmp/ink-auth-migration-validation/run-checkpoint-launch75.py` cwd Admin729f退出0：17张固定保护表的完整PG文本状态、首个Source/Thread、原result/input digest/commit time均保存于0600私有检查点；只有一个已接受请求与一个对应audit，余37个case尚无receipt。状态SHA为 `b5d5f6c977963f406656261b8e0f21e98862a7870f3571cd71cf5eec39d8d4b1`。继续harness只能只读恢复这一个已接受case的完整原结果并重验source oracle/静态DTO/17表不变，其余37项与全部原GET保持原断言。原fixture、首轮退出1和检查点不覆盖；凭据自然过期时仅签发新的技术OAuth，不能延长旧lease或重置已接受业务状态。

安全命令回执与诊断分别为 `/private/tmp/ink-auth-migration-validation/launch75-public-command-receipt.json`、`launch75-original-diagnosis-command-receipt.json`、`launch75-original-diagnosis.json`、`launch75-prior-checkpoint-command-receipt.json`、`launch75-prior-accepted-proof.json`。剩余公开case、选择性事务故障和实际COMMIT恢复仍待执行，首个已提交Source不能被计作完整启动或Runtime验收。

续跑harness新增严格 `validation_scope=remaining_after_source_new_null` 与固定0600检查点，full模式不接受检查点绕过POST，全部原38项case保留。第一guard命令因现有Vitest仅收录app/**/*.test.ts退出1、whole tsc因status推导可选退出2；只移动新守卫测试并校正helper类型。第二gate新6守卫通过、tsc因input推导可选仍退出2；只校正该类型后静态supplement type/lint/diff全部退出0，没有重复运行已通过的6项。运行时safeParse/owner/NULL-Agent/first-case/scopes/17表及完整源对照约束均保留，两个类型失败和未收录测试的原回执不覆盖。

主协调实际 `python3 /private/tmp/ink-auth-migration-validation/run-prepare-launch75-continuation.py` cwd Admin729f退出0：17表prior完全不变，原38项case事实exact，原fixture SHA为 `ef01594cd9aef0806fd48afdb60b10ab2868856f004f8dce225266ce0251d13c`，新增3个普通闭集查询后共21个GET检查点。只新增隔离技术JWK并签发300s OAuth；旧fixture、已接受结果、lease与时间保持。Luna已接收唯一有界公开续跑命令；结果必须读取实际回执后登记。之后的11点和3项COMMIT恢复见[独立事务计划](stage_admin-dream-launch-recovery-validation.md)，执行前必须公开续跑真实退出0。

## 续跑与恢复实际验收

Luna实际 `python3 /private/tmp/ink-auth-migration-validation/run-launch75-public-continuation.py` cwd Admin729f退出0；内部公开 `node --import tsx tests/integration/adminDreamLaunch.contract.ts`。stdout明确37 cases、skipped accepted1、prepared38、21 receipts、974 assertions、17 protected tables，完整实际应用/ensure、claim COMMIT-before-captured-turn和独立finish均true，full_prepare_failure_runtime明确not executed。主协调逐字读安全wrapper JSON与Luna回执后接受声明范围；未把原full退出1改写成一次38项通过。

主协调后续独立fault/真实COMMIT恢复命令退出0、308断言；11个选择性点均503且17表全部rollback byte exact，Source/Claim/Finish各真实最终COMMIT后单次响应丢失经GET200与同input replay200恢复完整结果，receipt/audit各1无重复。自有11×2触发器/函数清理PASS，原记录SELECT补验19断言退出0，原已接受Source/Thread/fullreceipt及8个无关fullrelation/其它旧rows保持。完整命令、输入边界及清理见[恢复计划](stage_admin-dream-launch-recovery-validation.md)。75生产冻结窗口已释放，后续默认Workspace/failure注册及Dream消费者继续；本阶段不代表全部生产数据库入口关闭或正常真实业务/模型验收。

- [launch75-public-command-receipt.json](../exec/admin-auth-data-verification/launch75-public-command-receipt.json)

- [launch75-original-diagnosis.json](../exec/admin-auth-data-verification/launch75-original-diagnosis.json)

- [launch75-prior-accepted-proof.json](../exec/admin-auth-data-verification/launch75-prior-accepted-proof.json)

- [launch75-public-continuation-luna-receipt.md](../exec/admin-auth-data-verification/launch75-public-continuation-luna-receipt.md)

- [launch75-public-continuation-command-receipt.json](../exec/admin-auth-data-verification/launch75-public-continuation-command-receipt.json)

- [launch75-continuation-typing-supplement-gate.md](../exec/admin-auth-data-verification/launch75-continuation-typing-supplement-gate.md)

- [launch75-public-disclosure-proof.json](../exec/admin-auth-data-verification/launch75-public-disclosure-proof.json)
