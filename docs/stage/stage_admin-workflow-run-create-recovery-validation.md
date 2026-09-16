<!-- [Input] Actual registered Run72 DTO/ORM, prior public case receipts and owned disposable PostgreSQL. -->
<!-- [Output] Primary-only rollback and lost-commit recovery plan with explicit full state evidence. -->
<!-- [Pos] Cross-project Run acceptance; persistence is Admin-owned and Runtime remains Dream-owned. -->
<!-- [Sync] 2026-09-15: plan selected atomic-write faults without resetting prior accepted cases. -->

# Run 创建与重试的事务故障及回执恢复

## 背景与问题

Admin 已注册创建/重试两项，原 70 项契约保持不变。首次公开合同在 readonly 认证错误码预期处停止；六个前置成功用例的完整源对照及事务断言已越过，主协调另外只读核验其单回执/审计、原完整字段和新 Run 两次 transition。剩余拒绝/回执仍补验中。故障验证必须使用新的 Preflight 与业务键，不重置这些结果。

## 目标与边界

主协调负责本轮 owned `run72` 技术数据库身份、凭据、触发器、故障 SQL、提交后响应丢失与清理。Admin 任务拥有生产 DTO/Service/Repository/Route；Luna 仅执行准备好的公开非破坏性合同。故障脚本不得连接正常数据库，改变既有索引/trigger、复制状态机或增加 test-only 生产分支。Dream 来源准备、dispatch、Runner、Runtime、SSE、资源算法与文件协议继续保持原顺序。

## 概念与规则

- 每个失败用例先通过公开 Preflight 接口生成新的合法记录，再记录完整业务表状态；故障只匹配本轮新业务键、request_id 或 PF 标识。
- 在 Run INSERT、Token mapping INSERT、PF consume CAS、第一次 transition、queued UPDATE、第二次 transition、receipt INSERT 和 audit INSERT 分别选择单个事务故障。预期公开 503，Run、两次历史、消费、PF、receipt/audit 和相关 Thread/Session 状态全部等于调用前。
- 新 terminal parent 的 retry 还应覆盖已通过只读先决阶段后、原子创建阶段失败；父 Run 与来源不变，不保留部分 child。
- 响应丢失只在真实 PostgreSQL 最终 COMMIT 成功且精确新回执可见之后注入一次；不伪造 COMMIT、返回值或数据库状态。依据实际 Route，记录是否返回 503 或已恢复结果；公开 receipt GET 必须返回原 Run/Thread scope 的完整结果，再次同输入调用不得新增效果。
- 错误输入或 owner/scope 不匹配不能恢复原记录。缺少 receipt 不代表回滚；客户端先查询原 request，未知结果不盲重试。
- cleanup 仅删除本轮明确名称的 fault function/trigger，关闭本轮 pool；已提交业务与故障回执保留，普通用户服务不停止。

## Optimized Prompt:

You are the primary owner of isolated registered Workflow Run creation/retry rollback and unknown-commit acceptance. Read actual WorkflowRunCreation DTO/Service/Repository/Handler, ReceiptRepository, withDataTransaction and public operation/receipt Routes; confirm the canonical72 catalog and original70 complete descriptor parity. Reuse only the proved disposable run72 database in the owned loopback51534 PostgreSQL instance; before every privileged setup verify database, owner role, port and data_directory and actual restricted AUTH/DATA credentials. Prepare new successful public Preflights, business keys and request IDs. Preserve all earlier accepted Run/PF/Thread/receipt/history facts. Capture complete exact JSON text state without rounding bigint or microseconds. Inject a single explicitly named trigger fault at each of Run INSERT, token map INSERT, PF consume UPDATE, initial transition INSERT, queued Run UPDATE, second transition INSERT, final receipt INSERT and audit INSERT; predicate every trigger on the selected new operation. Assert actual public failure and whole transaction rollback, including unchanged parent in a retry case. Remove only owned trigger/function in finally; retain actual first errors and safe command receipts. For transport loss, proxy the real restricted pg client without changing any query or parameter; throw once only after successful real final COMMIT and SELECT visibility of the exact committed receipt. Call the public original receipt GET and same-input original operation to prove every bounded result, Run/Thread scope, original created time and single history/consume/audit; classify absent or denied separately. Use actual Python semantic/model oracle for successful result expectations and production DTOs, never duplicate SQL/state algorithms or relax assertions. Do not migrate/restart/deploy normal services, call Google/real account/models/CLI, change canonical schemas or production paths, or allow broader credentials. Update project plan, scope/commands/exit codes and reviewed worktree mirror; overall goal remains active until all migration and real acceptance gates pass.

USER REQUIREMENT:
按 DTO/ORM 迁移要求验证 Run 创建/重试的原子持久化、未知提交结果恢复及原权限，保留 Runtime 与共享文件语义，不能把隔离技术故障检查冒充真实业务验收。

## 验收与风险

准确记录每个触发故障、公开状态/错误码、事务前后结果、响应丢失注入次数、完整回执恢复与清理退出码。最主要风险是触发器 predicate 错匹配、全局唯一错误值碰撞、PF/JWT 自然过期与此前 fixture 已改变；使用每项独立新 ID 和实际 clock，保留过去失败，仅补未执行路径。当前本阶段尚未执行，首次公开28合同仍非全通过；正常本机 Google、真实账户/实体/模型和 Dream 全域 no-PG 验收均 pending。


## 实际执行与清理补验

`python3 /private/tmp/ink-auth-migration-validation/run-run72-atomic-recovery.py` cwdAdmin729f原退出1：业务输出PASS68后，主fixture最后cleanup helper定义在try块内、finally无法调用，未能写清理回执。九项故障的每项remove已在各用例内实际执行，业务断言未失败；原退出1保留。只改主fixture helper作用域，不改生产代码/约束/预期，不重跑这些68项。

主协调随后 `/Users/dmeck/project/ink-dream-memory/backend/.venv/bin/python /private/tmp/ink-auth-migration-validation/verify-run72-fault-cleanup.py` cwd原Dream退出0、3断言：owned Run72精确身份、fault triggers0、functions0；九组选择对象全部删除，不停止用户服务，业务与失败历史保留。应报告业务68通过和独立cleanup3通过，不声称原命令退出0。

九点是Run INSERT、Token map、PF CAS、第一次transition、queued UPDATE、第二次transition、receipt、audit，以及新failed parent retry的child receipt。每点实际公开503/AUTH_SERVICE_UNAVAILABLE、16保护表整笔rollback完全byte-exact；parent保持原样。真实COMMIT后仅注入一次响应丢失，公开503、原GET200 committed、同input replay200，原完整static与实际Python源一致、原ID/time/scopes不变；最终Run1/history2/consume1/receipt1/audit1。正常数据库、Google/模型/CLI/用户服务均未调用。

本轮bounded故障与恢复检查达成后，72项短验证冻结已释放，Admin可继续新来源/dispatch持久化领域；旧72完整契约兼容仍须逐项校验。全域迁移、Dream Runtime实际执行与正常本机真实业务仍未完成，goal active。

- [run72-atomic-recovery-command-receipt.json](../exec/admin-auth-data-verification/run72-atomic-recovery-command-receipt.json)

- [run72-atomic-recovery-proof.json](../exec/admin-auth-data-verification/run72-atomic-recovery-proof.json)

- [run72-atomic-recovery-cleanup-diagnosis.json](../exec/admin-auth-data-verification/run72-atomic-recovery-cleanup-diagnosis.json)

- [run72-atomic-recovery-cleanup-command-receipt.json](../exec/admin-auth-data-verification/run72-atomic-recovery-cleanup-command-receipt.json)

- [run72-atomic-recovery-cleanup-proof.json](../exec/admin-auth-data-verification/run72-atomic-recovery-cleanup-proof.json)
