<!-- [Input] Frozen PF70/0060, proven disposable preflight61 and actual original eight-check/source recipe. -->
<!-- [Output] Primary-owned failure-injection commands and retained public-route receipts. -->
<!-- [Pos] Coordinator owns isolated SQL faults; Admin owns DTO/Service/Repository; Dream retains Runtime/FS. -->
<!-- [Sync] 2026-09-15: one Prompt Architect pass before remaining isolated failure checks. -->

# Preflight 失败与恢复验证

## 背景与问题

首次公开验证发现审计键碰撞，修复后相关20项测试与type/lint通过。后续执行已越过该故障；读取断言因原有效期结束停止，六种实际读取与原Python源码一致。既有数据和预期保留，不能重置或改预期掩盖结果。八项检查中的兼容、snapshot和Token失败，以及阶段中断和未知提交恢复仍需要独立证据。

## 目标与边界

Admin任务负责协议实现；本任务负责已命名、已证明身份的隔离数据库上的DDL/fault、即时凭据和必要fixture；Luna负责不含故障修改的确定性/公开合同。所有业务调用均使用Admin生产operation/receipt入口、真实DTO和受限AUTH/DATA连接，owner连接只用于隔离故障准备和SELECT核验。

## 概念与规则

- 每次操作前验证数据库名、actor、loopback端口和data_directory，普通数据库不进入脚本。
- 复用已经准备的独立compatibility-fault、snapshot-fault、token-fault事实，输入、binding与snapshot预期来自已捕获的原Python builder，不从实际输出反推预期。
- 兼容失败使用独立进程和一个明确compatible=false；snapshot/最终passed/snapshot绑定失败仅用本轮命名trigger，依据该独立Deck和状态触发，允许后续failed持久化。
- 前置checking/binding、独立snapshot和snapshot绑定提交按原状态语义保留；失败不创建Run或Session，不调用Runtime、Agent、共享文件系统或模型。
- 旧失败receipt/map/audit保持。新请求只有在旧提交结果已明确后创建，未知提交先查原receipt，不盲重试；阶段中断不能恢复执行。
- 只删除本轮自己创建的trigger/function，保留本轮业务失败和恢复回执。私有配置0600，公開回执先进行已知秘密与模式检查再归档。

## Optimized Prompt:

You are the primary cross-project coordinator implementing bounded isolated failure acceptance. Admin owns the frozen PF70 DTO, Service, typed Repository and original-request protocol; Dream owns consumers and Runtime. Existing evidence proves the named disposable PostgreSQL target and frozen0060/ACL, the stage audit key fix, actual source projections and independent compatibility/snapshot/token fault facts. Read the actual original eight-check recipe, production execution boundaries, immutable snapshot schema and source oracle. Before any SQL verify exact disposable database, actor, loopback port and data directory; require both actual AUTH and DATA credentials to identify that target with restricted roles. Reuse independent prepared fault Decks and canonical input/binding/snapshot expectations. In separate primary processes test explicit compatibility=false, selected snapshot INSERT failure, selected final passed UPDATE failure and snapshot-binding UPDATE failure after the snapshot commit. Use public production operation/receipt routes and real strict DTOs, independently prepared static fields and actual unmodified Python source for every complete projection. Assert expected first check/error, stage/receipt/audit counts, original canonical/input/fingerprint, committed snapshot survival and unchanged Run/Session counts. Keep original failed fixtures, histories and expectations untouched. Store fresh short OAuth/private configuration only in owned0600 files or process memory, export no private key or token. Remove only newly created named trigger/functions in finally; retain failures and raw sanitized command/cwd/exit receipts. Do not change production clock, schema capability, contract hash, migration bytes, state machine, Runtime, SSE, resource policy or filesystem boundaries. Then assess independent interruption, unknown final commit, expiry/original receipt and corruption cases without broad reruns; missing cases stay pending. Primary owns DDL, faults and credentials; Luna executes only deterministic non-destructive validation. Update folder/index, exact coordinator-owned worktree docs and disclose technical versus unexecuted normal-user Google/model acceptance.

USER REQUIREMENT:
按DTO/ORM分层迁移数据库访问，补齐完整业务失败、事务和恢复验证，保留原业务和共享文件系统语义。

## 验收、命令与风险

主任务执行明确命名的`run-preflight61-selected-faults.py`，每个子进程记录cwd、command、exit、assertion和安全输出；compatibility、snapshot、token、snapshot-binding分别要求预期check4/stages2、check6/stages2、check8/stages4、check6/stages3。完整字段还必须与原源码投影相同，Run/Session无新增。后续阶段中断、未知提交、过期/损坏和初始UOW回滚未执行时保持pending。DDL只存在于隔离验证脚本；触发器清理失败或身份不匹配即停止。非幂等故障调用不自动重试，已执行case不盲重跑。

## 实际结果

主任务四独立子命令全部退出0：22/24/25/25断言，共96。完整投影与原source equal；stage2/2/4/3、snapshot增量0/0/1/1，Run/Session无新增，三个本轮trigger/function清理0，兼容case没有trigger。原capability schema误用public导致42P01在业务和DDL前停止，校正为实际drizzle定义后仅续跑未执行步骤，原失败保留。

见[实际四子命令](../exec/admin-auth-data-verification/preflight61-selected-faults-catalog-corrected-command-receipt.json)。正常Google/模型和Dream全入口关闭仍pending。
