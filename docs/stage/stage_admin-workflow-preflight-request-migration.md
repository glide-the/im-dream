<!-- [Input] Frozen Admin0060 generation proof and owned PG60 history/target identity records. -->
<!-- [Output] Executable expand/repeat/concurrent/fresh/drift/catalog/ACL validation for immutable Preflight request bindings. -->
<!-- [Pos] Primary migration owner; Admin owns schema and application implementation. -->
<!-- [Sync] 2026-09-15: plan once before any0060 database execution; normal database is outside this phase. -->

# Preflight 原请求绑定 migration 验证

## 背景与问题

完整 Preflight 原业务有分阶段提交。首次请求部分提交后，必须将 service/actor/request/input 与既有 PF 持久绑定，避免重试更换输入或生成第二个 PF。Admin唯一Drizzle新增0060，九列 immutable request table 和 exact capability；含 pft 最终结果由应用 AEAD receipt 保存，不将 token 原文写到该表。

## 目标与边界

Admin任务拥有唯一schema/SQL/snapshot/descriptor/ACL与执行代码。协调主任务独占具名隔离migration/fixture/破坏性校验，Luna只处理确定性和非破坏性公开合同。只使用已证明的本轮PG51534/datadir下新建可删除 `_pf61_*` 数据库；normal5433/Dream/Admin/Gateway现有账户不访问。既有0..59 migration和所有已通过业务fixture不重复或清理。

## 概念与规则

- 冻结0060 SQL SHA `037508ab9cf0caac9bf1ada33d50a78aae45767a37d388721a241080f0f43b51`、snapshot `c003a9b59d54874241bec277389fd242a8ee90e55d4205ec8905e24f9fae7bf6`、descriptor `aef13bcd4e4f7ba4302b5aac5a184a0887098315886cac687cb11d09bf90087c`；capability dream.workflow-preflight-request.v1/v1/hash `7123babb03535e0a0c7a818e902c331cefbe73c660b46395136dcc9a5b19f3da`。
- 首先逐byte核验60priorSQL/history/journal，并复制冻结61 history到本轮新目录。所有查询与DDL先核验database/user/loopbackport/data_directory，凭据只读0600私有配置不公开。
- 实际正常migrator执行升级、重复、两个并发实例、fresh provider-aware全61历史、故意duplicate table的partial rollback。验证ledger61/候选仅一次/cap只成功提交后可见，失败保留旧ledger60且无新增function/trigger/cap。
- 验证九列类型/default/nullability、PK、index、FK正确引用 public.workflow_preflights且DELETE RESTRICT、CHECK与statement BEFORE UPDATE/DELETE/TRUNCATE55000、pg_catalog函数search_path、PUBLIC EXECUTE撤销。PostgreSQL generated identifier超过63字节时按实际截断名验证语义，不宣称未截断名称存在。
- 只准备最小隔离PF与request row，验证有效INSERT与duplicate23505/hash或canon23514/孤立FK23503；UPDATE/DELETE/TRUNCATE55000不改已写request，父PF delete RESTRICT23001保持binding（missing-PF INSERT仍23503）。没有替代生产状态机或禁用trigger。
- 新clone应用Admin显式ACL dry/apply/repeat，data实际SELECT/INSERT成功且无UPDATE/DELETE/TRUNCATE/function EXEC；AUTH/control无该表写，Dream仍无CONNECT。配置/secret与安全proof分别保管。
- 失败分类为候选业务/约束问题或harness问题；原退出码和输出保留，修正真实缺陷/明确harness后仅续跑未完成步骤。新cap未验证不交付Dream；wholePreflight/create/retry不因migration通过而宣称实现完成。

## Optimized Prompt:

You are the primary migration and destructive-fixture owner. Admin has frozen sole-Drizzle0060 with a nine-column immutable original-request-to-Preflight binding table, composite service/actor/request primary key, SHA and positive canonical-ID checks, PF foreign key RESTRICT, statement-level UPDATE/DELETE/TRUNCATE55000 guard with pg_catalog search_path and revoked PUBLIC execution, and exact final capability. Verify its three pinned hashes and all previous60 SQL/journal bytes before copying a frozen61 history. Use only newly named disposable databases on the previously proved owned local PG port/data directory; prove database/user/loopback/port/datadir on every target and never access normal databases or print private config. Reuse normal migration orchestrators to prove upgrade/repeat/two concurrent/fresh provider-aware full history and duplicate-table partial rollback, exact ledger61 and one candidate/capability. Compare real catalog column types/defaults/nullability/PK/index/FK/checks and generated63-byte identifier behavior, function body/search_path/ACL and enabled statement trigger events. Prepare only isolated minimal PF/request facts; prove valid and duplicate/invalid hash/canonical/FK inserts, immutable update/delete/truncate refusals, original PF delete RESTRICT and unchanged rows. Apply the actual Admin ACL runner in named clones, then prove limited data SELECT/INSERT only, no elevated ownership/function access, no auth/control request writes and Dream CONNECT denial. Preserve all raw sanitized command/cwd/exit output and failure/rollback records. Do not change frozen history, disable triggers, lower assertions, replay already-passed domain fixtures, run providers/models, deploy or touch normal user services. Hand the validated exact capability and receipts to Admin/Dream, update own headers/folder index/mirror and keep the full task active until application and mandatory business acceptance are complete.

USER REQUIREMENT:
原事务/分阶段提交经接口迁移须绑定原请求并处理未知提交恢复，数据库变更唯一Admin Drizzle管理且只在已证明具名隔离库验证。

## 验收与风险

命令：本轮 primary `python3 /private/tmp/ink-auth-migration-validation/replay-candidate-0060.py` 包装实际 `node packages/db/dist/migrate.js` 与fresh `node scripts/migrate-provider-managed-accounts.mjs`，随后实际 `node drizzle/data/auth-access-policy.mjs`。执行后填真实退出码、catalog/ACL与失败恢复证据。风险：应用依赖部分提交需独立状态与加密receipt；本阶段只证明expand结构，不证明完整Preflight执行或正常部署。新ACL在ledger60会fail closed，故先新clone迁移61再应用，不回退旧ACL来降低边界。

当前状态：实际六迁移子命令、九列catalog/约束/不可变与最新ACL15实际查询通过；完整Preflight应用/公开合同和正常部署仍待后续。


## 实际命令与校正结果

主任务 `python3 /private/tmp/ink-auth-migration-validation/replay-candidate-0060.py` cwdAdmin729f初始退出1发生在SQL前（聚合算法），按原已冻结filename+NUL+bytes算法校正后六迁移子命令完成：upgrade/repeat/两并发/fresh61均0、故意duplicate-table迁移非0且ledger60无cap/guard。九列catalog、PK/index/FK RESTRICT、CHECK、statement58/O trigger、pg_catalog与PUBLIC EXEC=false吻合。wrapper末尾PF DELETE返回23001，错预期23503导致1；剩余 `verify-candidate-0060-remaining.py` 退出0，只重验catalog/精确RESTRICT与未变PF/request，未重复迁移或改候选。先前七个SQL拒绝已核验非0和SQLSTATE，但其各自精确psql退出数字未单独留存，因此proof为null，不推造数字。见[六实际子命令](../exec/admin-auth-data-verification/candidate-0060-receipt.json)、[catalog](../exec/admin-auth-data-verification/candidate-0060-catalog-proof.json)、[原失败/续验](../exec/admin-auth-data-verification/candidate-0060-harness-correction.json)、[SQLSTATE官方定义](https://www.postgresql.org/docs/18/errcodes-appendix.html)。

最新ACL dry/apply/repeat三子命令0且hash相同。role harness首次mode bitwise括号错误在DB前失败，随后用不存在user_id列的UPDATE得到42703；原记录保留，真实catalog列的UPDATE和剩余四查询续验0，不再INSERT/DDL/ACL重放。共15实际role queries：DATA仅SELECT/INSERT原请求，mutation/TRUNCATE/guard、Auth/control、Admin模型权限I/U/D和privateJWK拒绝42501；DreamCONNECT拒绝42501且catalog全false。见[原ACL/权限失败](../exec/admin-auth-data-verification/candidate-0060-acl-receipt.json)、[实际15查询](../exec/admin-auth-data-verification/candidate-0060-actual-role-proof.json)、[剩余命令0](../exec/admin-auth-data-verification/candidate-0060-final-role-receipt.json)。
