<!-- [Input] Frozen PF70/0060, original committed response protocol and isolated fault96 evidence. -->
<!-- [Output] Primary-owned public unknown-commit, expiry and damaged-receipt recovery evidence. -->
<!-- [Pos] Coordinator injects only isolated harness faults; Admin owns all SQL/ORM/UOW and authority. -->
<!-- [Sync] 2026-09-15: one Prompt Architect pass before original-request recovery validation. -->

# Preflight 原请求恢复验证

## 背景与问题

四类检查故障96项断言通过，失败提交与snapshot保留已验证。完整验收还需要证明最终COMMIT已经成功但调用方收到错误时不会把passed改写为failed；当前PF过期不会修改原请求的bounded回执；密文或绑定损坏必须返回明确失败而不能继续执行。

## 目标与边界

主任务只在已拥有的具名preflight61隔离库，通过现有公开operation/receipt route、真实DTO、受限角色及原Python源码执行。Pool代理和故障只存在于明确命名验证脚本，生产模块、契约70、migration0060、Runtime/FS保持原归属。Admin处理全部真实SQL、事务和权限，owner连接仅用于隔离故障准备和只读核验。

## 概念与规则

- 每次先证明目标name/actor/loopbackport/data_directory与受限AUTH/DATA，拒绝普通数据库。
- Lost commit只在生产Drizzle真实COMMIT完成且原receipt已经存在后抛一次transport错误；抛错前记录原passed完整source投影、PF/map/receipt/audit。公开返回必须恢复精确原结果，抛错后不得改变状态、TTL、token/hash或审计次数。
- 过期只作用于本轮新建、已捕获passed回执的隔离PF；普通read不返回Token，同一原request/receipt仍返回完整原bounded结果。新原request按照既有expiry规则处理，不任意重试未知提交。
- 损坏场景通过本轮新建的map/receipt事实验证ciphertext及canonical/workspace绑定，保留旧receipt/history，不删除、覆盖或解除既有guard。返回503而不是absent、resume或直连fallback。
- 保留Run/Session计数，Runner/SSE/Runtime/sharedFS不会在本阶段执行；安全回执在已知secret/pattern检查后进入项目文档。

## Optimized Prompt:

You are the primary coordinator proving original-request recovery on the owned disposable Preflight61 target. Existing source and fault receipts prove strict DTO/Service/Repository/Drizzle and four-stage persistence; recovery remains pending. Read the actual execution catch/finish, receipt repository, AEAD binding codec and public original receipt service. Before SQL verify exact database, actor, loopback port/data directory and restricted AUTH/DATA credentials. Use only public production operation/read/receipt routes and real DTOs. Inject one lost response after the real final Drizzle COMMIT, only after independently SELECTing a committed original receipt, capturing the full actual original Python source projection and immutable PF/map/receipt/audit facts. The production caller must recover the exact passed result before any failure mutation; assert only one final receipt/audit, unchanged expiry/hash/state and no Run/Session. Then expire only that owned fresh current PF and prove ordinary read token NULL while original request/receipt retain the captured complete result, without refreshing its TTL. Prepare separate new owned malformed-cipher and wrong-binding map/receipt facts rather than editing historical guarded receipts; require503, unchanged persisted state and no execution/resume/fallback. Keep Pool interception, SQL fault setup and private fresh credentials only in named primary validation files, never production environment branches. Preserve frozen PF70 wire and0060, prior fixtures/expected/failures, AgentRuntime/FS/resource policies. Emit actual sanitized command/cwd/exit/assertion receipts and safe provenance docs; mark interruption/initial-UOW rollback and real Google/model acceptance pending until actually executed. Run database mutation/fault/credentials in primary; Luna executes only non-destructive deterministic validation. Update this plan, folder index and exact coordinator-owned Dream worktree mirror before session end.

USER REQUIREMENT:
保留原事务、并发、过期、未知提交恢复语义，以公开接口完成数据库服务迁移验收，禁止非幂等盲重试。

## 阶段中断执行规划

已有证据：四类故障96断言通过；lost final commit、过期原结果、损坏绑定和初始UOW回滚44断言通过；剩余八读取74断言通过。仍需checking、binding、snapshot各自真实COMMIT后中断，证明原请求不会继续执行。主任务拥有明确命名的子进程和隔离目标；Admin生产代码与契约保持冻结。

### Optimized Prompt:

You are the primary coordinator completing bounded stage-interruption acceptance. Reuse the proven disposable Preflight61 target, original source and independent compatibility-fault Deck with all production compatibility flags true. Read the actual production staged execution and original receipt semantics. In three separately spawned owned child processes, use real restricted Pool/Drizzle and public production operation routes. Preserve every query and parameter; only after the real selected checking, binding or snapshot COMMIT succeeds, independently SELECT the original map, checking PF and exact retained stage audit count, capture a private context and safe aggregate proof, then terminate only that spawned child with SIGKILL. The parent must verify the exact expected child signal and captured stage proof, never kill another process. In a fresh owned parent process use current OAuth and public original receipt/operation replay routes; compare complete in-progress DTO with unmodified original Python projection and assert original PF/map/snapshot/audit and Run/Session remain unchanged, no final receipt, token, resume or TTL. Snapshot-stage interruption must preserve the newly committed immutable snapshot while PF snapshot reference remains NULL. Keep private contexts0600 and export only safe command/cwd/exit/assertion receipts; child signal is expected fault evidence, not a successful child command. No production changes, migration, normal database, Runtime or filesystem operation. Close only parent-owned pools; preserve all interrupted facts and prior failure receipts. Update coordinator documents and mirrors, and keep real Google/model and Dream production closure pending.

USER REQUIREMENT:
验证各事务阶段中断与原请求恢复，保留并发、lease、Runtime和共享文件系统语义。

## 验收与风险

执行`run-preflight61-recovery-validation.py`，按实际子命令记录输出与退出码。lost commit只触发一次且恢复full passed/source，原状态与回执完全相同；过期read token为NULL而原结果精确不变；新damaged/binding事实503且无执行写入；Run/Session没有新增。Pool代理必须保留真实client方法/参数/COMMIT语义，未注入或未观察到真实提交时测试失败，不能声称验证成功。阶段kill/transport中断、初始expiry+checking+map回滚和正常业务验收仍pending。

## 实际结果

`run-preflight61-recovery-validation.py`及其实际Node子命令退出0，44断言；包括一次真实final COMMIT响应丢失、当前expiry与原结果保持、新原request规则、三damaged场景和初始UOW回滚。`run-preflight61-interruption-validation.py`总体退出0：三个自有execute child准确exit -9(SIGKILL预期故障)，三个父recover子命令exit0，各18断言，共54；GET/replay完整原source equal，仅in_progress不resume，stage1/2/3，snapshot增量0/0/1，Run/Session无新增。子命令-9不报告为child退出0，只作为主任务已核实的故障证据。所有history保留，普通服务未修改。

见[恢复44](../exec/admin-auth-data-verification/preflight61-recovery-proof.json)、[阶段中断原子命令](../exec/admin-auth-data-verification/preflight61-interruption-command-receipt.json)。
