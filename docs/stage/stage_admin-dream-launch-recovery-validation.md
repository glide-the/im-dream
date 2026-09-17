<!-- [Input] Registered75 component DTOs, actual source oracles and isolated public continuation receipts. -->
<!-- [Output] Selected component transaction fault and actual final-COMMIT response-loss validation. -->
<!-- [Pos] Coordinator-owned isolated recovery gate; ordinary services and Runtime stay separate. -->
<!-- [Sync] 2026-09-15: record11 selected rollback faults/3 actual-COMMIT losses,308 checks and19 preservation. -->

# Dream 启动持久化事务与未知提交结果验证

## 背景与问题

Source、claim、finish 已注册在 Admin 的75项业务契约中。原业务各自提交，Dream 在 claim 提交后才执行 Runtime；不能因迁为HTTP把独立事务合并或对失败写入盲重试。首轮公开组件合同因全局主体覆盖拦截层的预期错误退出1，主协调保存了唯一已提交Source和17张表的完整状态。修正及续跑见[组件验证计划](stage_admin-dream-launch-component-validation.md)。本轮先编写独立故障harness，只在剩余公开合同通过后执行。

## 目标与边界

主协调拥有本计划、具名隔离目标身份核验、新fixture、技术凭据、选择性DDL故障、实际COMMIT后一次响应丢失和回执复核。Admin任务保留生产75实现冻结，Dream任务继续不依赖这些故障的消费迁移。Luna只执行后续非破坏确定性或文档检查，不执行本轮DDL、故障注入或凭据准备。

目标仅 `ink_auth_data_codex_test_792494523a17_launch75`，owner/51534/loopback/datadir均逐次核验；正常5433、用户服务/账户、Google/Gateway/模型、Thread workspace、CLI/TMP/sandbox不操作。业务数据只通过公开生产DTO写入，新key/request/Run各自独立，不修改旧已通过用例、原时间、lease或回执。

## 概念与规则

- Source五个选择性点：新Thread INSERT、新message INSERT、该Thread排序UPDATE、原receipt INSERT、同事务audit INSERT。
- Claim三个点：原message envelope UPDATE、原receipt、audit；Finish三个点：metadata UPDATE、原receipt、audit。每一点以本轮新确定性标识或新request匹配，不能让触发器影响其它请求。
- 每次故障前准备新的公开业务fixture，再读取固定17表完整PG文本状态。失败应返回503 AUTH_SERVICE_UNAVAILABLE，17表全部byte exact，不产生部分来源、metadata、lease、receipt或audit。
- Source/Claim/Finish各验证一次实际最终COMMIT响应丢失。Pool代理必须先执行真实原query与参数，只有真实COMMIT完成且精确原receipt可见后才抛一次transport错误，不能伪造commit/result。
- 未知结果先原GET；恢复完整原DTO、时间、parts/metadata/context/claim/scopes。确认committed后同input重放，所有保护表与已提交状态一致，receipt/audit各1；没有重复业务效果。
- Source与claim/finish完整结果对照实际Python应用/helper/dispatcher源，不复制其SQL、状态机或数值算法。Claim的原Runtime调用只捕获参数证明COMMIT顺序，技术验证不执行Runtime。
- 仅清理本轮明确 `codex_launch75_` 命名触发器与函数、当前harness自有pools。先身份核验再DDL；cleanup函数处于模块作用域，异常退出也保留首个业务失败，不用清理失败覆盖它。

## Optimized Prompt:

You are the primary coordinator of the Admin-owned Dream launch recovery gate. Existing evidence is a registered75 catalog, three closed Source/Claim/Finish contracts, unchanged original72 descriptors and capabilities, an explicitly owned disposable launch75 PostgreSQL target, and a truthful first public harness failure with a one-case/17-table prior checkpoint. Read the finalized public continuation receipt before executing faults. While it is pending, prepare only this recovery harness and project plan. Require strict DTOs and actual Python source-oracle expectations for new fixture creation; reuse the fixed original Run expected-source adapter and final-COMMIT pool proxy pattern, without copying any production state machine or algorithm.

Own only temporary recovery scripts, new named isolated fixtures and coordinator documentation; do not edit frozen production routes, schemas, capabilities, producer modules or Dream runtime. Prove exact database, owner role, loopback port and data_directory before privileged operations. Restrict AUTH/DATA clients to the same disposable target and keep all credentials in0600 private configuration; export no private signing key. Create fresh public Source/Preflight/Run/claim prerequisites with per-call new technical OAuth, while preserving all old accepted source facts, timestamps, leases, receipts and audit history.

Inject eleven new-case selected faults: five Source Thread/message/order/receipt/audit points, three claim envelope/receipt/audit points and three finish metadata/receipt/audit points. Bind each trigger predicate to a locally generated exact source ID or request, using only a fixed relation/event list. Expect the unchanged public503 safe persistence error and byte-exact rollback of all seventeen protected relations. Remove only this harness's trigger/function after every case, and verify no owned fault objects remain. For each component, additionally inject exactly one response loss only after the real final COMMIT succeeds and the exact original receipt is visible. Validate full actual-source/static result, GET committed recovery, same-input replay and one correlated receipt/audit with no duplicate protected effects. Never replay old accepted writes merely to obtain a passing total.

Keep normal services, Google, user/model acceptance, Runtime, SSE, file operations, resource admission and TMP/sandbox unchanged. Capture exact command, cwd, underlying exit status, completed cases and cleanup results. Preserve the first failure and classify harness versus business defects from actual behavior before correction. Secret-scan pinned artifacts before archiving, update file/folder/stage/exec docs and valid references, and keep the overall migration and real acceptance goals active.

USER REQUIREMENT:
遵从DTO/ORM完成数据库访问接口迁移，保留原事务、并发、幂等与权限；用实际隔离故障及未知提交结果恢复验证，而不冒充正常真实业务或Runtime验收。

## 状态、验收与风险

| 阶段 | 条件与输入 | 成功标准 | 失败处理 |
|---|---|---|---|
| 执行前 | 公开组件剩余合同真实退出0 | 原失败/已接受Source保留，全部case/GET有证据 | 未通过时只准备harness，不注入DDL |
| 新fixture | 公开Source/PF/Run/claim、实际源预期 | 完整DTO/原摘要/owner/context/time一致 | 准备失败即停该case并保留回执 |
| 11点原子性 | 固定表、选择性新ID/request | 503；完整17表无变化 | 修实现或harness，不改断言掩盖 |
| 3项COMMIT丢失 | 真实query/COMMIT、精确可见receipt | GET/replay完整恢复，各1receipt/audit | absent不推断回滚，不自动重试 |
| 清理与文档 | 当前自有命名对象/pools | 仅自有对象移除；safe证据有命令/退出码 | 单列清理失败，保留业务原退出码 |

拟运行 `python3 /private/tmp/ink-auth-migration-validation/run-launch75-atomic-recovery.py`，cwd `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`；确切结果必须执行后登记。源码对照使用现有实际integration oracle、临时Run expected-source helper、成熟Drizzle Repository/UOW与原GET。风险包括lease在GET前自然过期、Pool中未命中精确request的中间COMMIT、异常清理词法作用域及回执损坏；以fresh新case和完整状态/原result证据处理，不改变产品TTL或旧数据。

当前仅制定计划；11点和3项恢复尚未执行。全启动/failure recorder、剩余Dream SQL、浏览器/Google/设备完整业务、正常用户/模型/Admin可见回执及运行无PG仍独立pending。

## 实际结果与原记录保护

上述“仅制定计划”是执行前状态。公开continuation真实退出0、37/21/974后，主协调实际 `python3 /private/tmp/ink-auth-migration-validation/run-launch75-atomic-recovery.py` cwd Admin729f，内部 `node --import tsx /private/tmp/ink-auth-migration-validation/launch75-atomic-recovery.mts`，退出0、308断言。11项逐个新fixture/newkey/request，实际503 AUTH_SERVICE_UNAVAILABLE且完整17表rollback；Source/Claim/Finish各在真实最终COMMIT与精确receipt可见后仅抛一次响应丢失，首次503、GET200 committed、同input replay200，完整原source/parts/metadata/context/claim/scopes/time与实际Python源和DTO一致，receipt/audit各1、已提交17表状态恢复后不变。

异常与成功路径清理均模块作用域，11组各删除本轮自有trigger/function，cleanup proof为PASS、current owned fault objects none；只关闭本harness的owner/DATA/AUTH pools，不清理业务回执或用户服务。随后实际 `python3 /private/tmp/ink-auth-migration-validation/run-verify-launch75-preservation.py` cwd同上退出0、19断言，完全只读：原 `source-new-null` Source/Thread/完整receipt/input hash/scopes/commit time未变，8无关fullrelation byte exact；旧Run/Preflight/request/history/consumption/receipt/audit每条原PG文本仍存在。只允许本阶段指定的新claim message metadata变化，未修改旧fixture或lease。

原命令与proof保留在 `/private/tmp/ink-auth-migration-validation/launch75-atomic-recovery-command-receipt.json`、`launch75-atomic-recovery-proof.json`、`launch75-atomic-recovery-cleanup-proof.json`、`launch75-post-validation-preservation-command-receipt.json`、`launch75-post-validation-preservation-proof.json`。私有诊断/owner/env/签发Token/fixture/checkpoint不进入项目证据；源语法2MTS与3PythonAST gate仅语法范围，不称类型或业务通过。75冻结窗口已释放，整体goal仍active；正常数据库、Google/账户/模型/Runtime、全部Dream生产入口无PG尚未验收。

- [launch75-atomic-recovery-command-receipt.json](../exec/admin-auth-data-verification/launch75-atomic-recovery-command-receipt.json)

- [launch75-atomic-recovery-proof.json](../exec/admin-auth-data-verification/launch75-atomic-recovery-proof.json)

- [launch75-atomic-recovery-cleanup-proof.json](../exec/admin-auth-data-verification/launch75-atomic-recovery-cleanup-proof.json)

- [launch75-post-validation-preservation-command-receipt.json](../exec/admin-auth-data-verification/launch75-post-validation-preservation-command-receipt.json)

- [launch75-post-validation-preservation-proof.json](../exec/admin-auth-data-verification/launch75-post-validation-preservation-proof.json)

- [launch75-primary-harness-static-gate.md](../exec/admin-auth-data-verification/launch75-primary-harness-static-gate.md)
