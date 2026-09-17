<!-- [Input] Admin immutable 0000..0053 history, candidate 0054, explicit disposable database protocol and actual migration runner. -->
<!-- [Output] Primary-owned schema replay/adoption/concurrency/ACL validation plan and execution gates. -->
<!-- [Pos] Coordinator migration validation; sole schema files remain in Admin drizzle. -->
<!-- [Sync] 2026-09-15: add the frozen 0061 Reflections aggregate migration, event cutover and Registry99 acceptance gate. -->

# Admin 认证与 Dream 数据分离迁移验证计划

## 背景与问题

Admin 的候选 0054 增加 identity 认证表和 dream 操作收据，当前仍未冻结、未应用。新建一张 dream 表不能证明既有业务表已经分离。
历史迁移包含 Provider expand/data/contract gate，必须复用正常 migration orchestrator，不能跳过历史检查直接执行候选 SQL。
协调读取了 Admin 根规则、drizzle/AGENTS、migration runner、runtime target resolver 和既有隔离 schema/provider harness；没有执行正常数据库变更。

## 目标与边界

主任务负责创建本轮独立 PostgreSQL、核验目标身份、migration/backfill/破坏性执行及结果审查。Luna 只执行冻结实现的确定性和 provider-free 技术验证。
隔离集群与数据目录位于本轮明确命名的临时目录；数据库名称包含 auth-data/codex/test 标识，监听地址限定回环，使用独立可用端口和随机凭据。
所有 schema/DDL 必须来自 Admin drizzle。正常 PostgreSQL、现有 Admin 3000 进程、用户文件和历史 migration 0000..0053 不变。

## 概念与规则

- 候选冻结：记录 schema、journal、snapshot、SQL、capability descriptor SHA 和 Git commit；运行期间改变候选则废弃对应结果，重跑受影响流程。
- 目标核验：每个写入阶段先检查 current_database、current_user、server address/port、data_directory 和本轮集群归属，禁止使用来源不明的 DSN。
- 历史复用：采用 Admin `packages/db/src/migrate.ts` 和根 `scripts/migrate-provider-managed-accounts.mjs`。Provider encryption/identity pepper 使用本轮独立随机值，不能读取正常账户 secret 或正文。
- capability：核验 schema capability 的 version/hash/实际表结构，API capability 另行通过接口验证；不以 Drizzle 全局 head 代替领域兼容检查。
- 数据分离：逐表核验 schema、owner、FK、索引、sequence/function 权限和连接角色允许/拒绝矩阵，不能只检查名称。
- 清理：仅停止本轮数据目录匹配的 PostgreSQL；保留脱敏命令回执和候选 fingerprint，删除本轮独立数据库/临时凭据，不触碰正常业务 Run/Thread。

## Optimized Prompt: 隔离迁移准备与执行

You are the primary migration acceptance owner. Prepare a named, disposable PostgreSQL cluster using installed local tooling and existing Admin migration infrastructure. Evidence: baseline Admin 017f3acc has immutable 0000..0053; candidate 0054 is not frozen or applied; local PostgreSQL tools are installed; normal Admin runs on 3000 and must remain untouched. Read the canonical DTO/ORM contract, Admin migration/folder rules, target resolver, journal/adoption/schema capability implementations and existing isolated schema/provider harnesses. Ownership: coordinator owns this plan, isolated lifecycle and actual migration/destructive validation receipts; Admin task alone owns SQL/schema/journal/snapshot/capability/data runner changes; Dream consumes released capabilities and never creates schema. Do not apply a changing candidate. First protect existing Git edits, prove installed tooling and independent port/path/database ownership, and prepare baseline replay. On explicit candidate freeze, record exact hashes and execute public migration runner/orchestrator against the independently proven target. Validate empty replay, old-prefix adoption with preserved identifiers, missing/partial schema drift fail-closed, repeat application and concurrent migrators, capability hash/catalog consistency and least-privilege ACL including canonical registration/platform projection. Add only this plan, affected documentation inventories and actual execution receipts to the coordinator branch. Keep credentials and DSNs out of reports. Do not migrate normal PostgreSQL or stop existing services. On failure identify harness vs SQL/contract defect, send concrete evidence to the migration owner, repair forward candidate according to its published status, then rerun the failed and affected checks. Acceptance requires command/cwd/exit/catalog results, rollback/atomicity proof and owned-resource cleanup; isolated results never count as real-user/Google/model acceptance.

USER REQUIREMENT:
Validate Admin-only Drizzle migrations and database responsibility separation in an identity-proven named isolated database, preserving legacy data and the original business transaction semantics.

## 验证顺序与成功标准

| 步骤 | 依赖 | 成功标准 | 失败处理 |
| --- | --- | --- | --- |
| 隔离工具/目录/端口准备 | 本机 tooling | 本轮 root/数据库/端口/进程可追溯，回环连接 | harness 不可启动则记录前置失败，不判业务失败 |
| 历史空库 replay | 0000..0053 字节与基线一致 | 正常 orchestrator 通过各历史 gate，journal/hash 正确 | 保留 rollback 回执，不绕过 gate |
| 新候选空库 replay | Admin 冻结 commit/descriptor | SQL/source/snapshot/capability 一致，auth/dream 表可由 ORM 访问 | 将实际错误交唯一 migration owner |
| 旧前缀升级/adoption | 明确命名独立数据库与合法旧结构 | 旧 PK/主体/FK 和数据关系保持，新能力可用 | 不隐式重建用户或补建漂移对象 |
| partial drift/capability 缺失 | 隔离故障注入 | runner/应用 fail closed，无部分提交 | catalog 与 ledger rollback 证据 |
| 重复与并发 migrator | 正常 migration runner | 不重复 DDL/ledger，锁保护单次提交 | 失败不声称完成或移动历史 hash |
| 权限与业务投影 | 最终 schema/role 配置 | auth 最小权限、Admin domain 范围、Dream 无数据库凭据路径；注册平台投影原子 | 不用全库 owner 连接掩盖权限缺口 |
| 清理与回执 | 本轮归属证明 | 只清理本轮资源，正常 Admin/PG 保持 | 无法证明归属的进程不停止 |

## 当前状态与回滚

隔离集群准备、基线0000..0053重放和修复后的0054验证已执行通过；完整业务schema分离/ACL和旧用户adoption仍待Admin实现。
具名隔离库 `ink_auth_data_codex_test_792494523a17`，回环端口51534，数据目录 `/private/tmp/ink-auth-data-migration-20260914-792494523a17/postgres`，每项身份已核验。
54项历史SQL逐字节匹配基线017f3acc，正常migration orchestrator通过Provider gate。0054首轮实际42830外键顺序失败并完整rollback；owner修复未发布候选后，18表/189字段catalog一致，旧prefix升级/重复/并发/fresh全历史/partial-drift rollback全部通过。
正常数据库没有变更；新认证字段存在不等于旧账户映射、最小权限和全部业务schema归属已经完成。
实际回执索引见 [协调执行记录](../exec/exec_admin-auth-data-coordination.md)。
运行失败保留脱敏日志；未发布候选按 owner 规则修正，已发布历史只能新增前向 migration。
隔离通过后才评审正常部署的具体变更和不可逆条件，不在准备阶段申请空泛确认。


## Optimized Prompt: 冻结 0055 委托前向迁移验证

You are the primary owner of migration execution. Evidence: Admin 0054 has passed upgrade/repeat/concurrent/fresh/drift rollback on the named owned PostgreSQL; user-authorized worktree sync preserved frozen 0054/0055 bytes. Admin froze 0055 SQL 559e9f406cf9ee64f7b8c5803cfb2a012dcfca7c21f5bcd4bf54e057a1d33351, snapshot b600f3d62785cbb7999288485a1cb7cb7cb90eed89fbee15b6767c34ab39dcf7, descriptor 865ff782ce5f165a61ffd9ab9a1ac6a69683e7bd9ba9467a9c763944db5c797a and identity.runtime-delegation.v1 contract 1a682e29c2fcfa6d870a64c131773f0fa2ce49866fc56b30f334e07040e79a83. Freeze a separate immutable 0000–0055 validation history; verify 0000–0054 match prior successful history exactly. Before every write prove database name prefix, configured loopback port/current user and owned data_directory. Use only the Admin normal explicit migration runner and orchestrator, never Dream DDL. Replay old-prefix upgrade, repeat, two concurrent migrators, fresh full history and partial-drift rollback; compare all runtime delegation table columns/types/nullability, named keys/index/check definitions with the frozen snapshot and contract, preserving legacy nullable expansion rows. Keep primary fixture/migration responsibilities distinct from Luna provider-free route validation. Record exact commands/cwd/exit/raw sanitized output and separate any CHECK SQL NULL semantic gaps from catalog replay success. Do not change frozen migrations or normal local PostgreSQL, and do not claim least-privilege ACL/adoption or real Google/model acceptance merely from schema success.

USER REQUIREMENT:
Validate Admin's actual forward Drizzle delegation migration and capability in an identity-verified disposable PostgreSQL while preserving long-turn authorization and explicit legacy compatibility.

当前风险：0055 creation CHECK 中input_sha256缺少显式IS NOT NULL，PostgreSQL允许整个表达式为NULL；已交Admin唯一schema owner以新前向migration修正，不改冻结0055。运行/capability/catalog结果与这个语义缺口分别记录。


0055实际命令：`python3 /private/tmp/ink-auth-migration-validation/replay-candidate-0055.py`，cwd Admin729f，exit0；16columns与snapshot/descriptor一致，ledger56且0055单次，upgrade/repeat/concurrent/freshfull/partialdriftrollback通过。creation SQLNULL缺口保留，0056前向修复未执行；ACL/adoption与正常真实数据库验收仍未完成。详见[0055回执](../exec/admin-auth-data-verification/candidate-0055-receipt.json)与[catalog/已知缺口](../exec/admin-auth-data-verification/candidate-0055-catalog-proof.json)。

## Optimized Prompt: 冻结 0061 Reflections 聚合迁移验证

You are the primary owner of the frozen Admin 0061 Reflections aggregate migration acceptance. Evidence: Admin 0000–0060 has already passed the normal migration orchestrator on named disposable PostgreSQL targets; 0060 SQL and capability receipts are preserved; the current 0061 candidate adds task sections, task-bound encrypted child authority, task report linkage, task service/subject/snapshot/revision fields, and a deterministic event-sequence cutover. The application contract is strict Zod DTO → Service → typed Drizzle Repository → one Admin transaction, while Dream remains the Agent/EventBus/SSE/shared-files executor and will consume the frozen Registry99 contract. Do not execute any DDL until the Admin task publishes one commit and exact 0061 SQL, snapshot, descriptor and capability hashes.

Read the final Admin commit, migration/folder rules, 0061 SQL and snapshot, `dream-reflection-task-persistence-v1` descriptor, Registry99 artifact, Reflections Repository/Service/RTA code, the existing 0060 receipts and the actual old Dream event writer. Freeze a separate immutable 0000–0061 history; prove that 0000–0060 journal entries and bytes match the prior successful history. Before every write prove the database name begins with `ink_auth_data_codex_test_reflections_`, the server listens only on loopback, and the data directory belongs to this run. Use the normal Admin migration runner and provider orchestrator for full-history work. Never connect to the normal Dream/Admin database, copy normal credentials, or modify a published earlier migration.

Validate old-prefix upgrade, repeat application, two concurrent migrators, fresh full-history replay, and partial-object drift rollback with an unchanged ledger. Exercise an overlapping old writer and prove 0061 waits for its table lock before deterministically resequencing every task by `created_at NULLS LAST, id`; then prove sequence is non-null, positive, unique per task, bounded by PostgreSQL int4 in DTO and ORM, and exposed as the worker high-water mark. Validate task/section/report foreign keys, lifecycle and revision checks, one live task-section authority, exact service/subject/thread binding, expiry/revocation constraints, capability version/hash/catalog consistency, and rollback at every injected failure. Run the provider-free Registry99, ingress, source-oracle, typecheck and lint gates against the same frozen commit. Record sanitized commands, working directories, exit codes, key catalog values and owned-resource cleanup in project receipts. A harness failure remains distinct from a schema or business defect; repair only the unpublished candidate, rerun affected checks, and do not count this isolated result as real Google, real model, or normal-database acceptance.

USER REQUIREMENT:
Validate the Admin-only 0061 Drizzle migration and Reflections DTO/ORM transaction contract in identity-proven disposable PostgreSQL, preserving legacy events and Dream Runtime/SSE/shared-files behavior while removing Dream production database access.


## Optimized Prompt: 冻结0056注册与最小权限真实验证

You are the primary owner of isolated migration, fixture preparation and privilege execution. Evidence: 0054/0055 exact frozen-history replay passed; 0055 SQL NULL creation CHECK gap is real and the schema owner produced forward0056. Freeze0056 SQL 3b60191c7534898a00ba6edb84a81f2540d5ad0f8f01befce4f035027bcb25fc, snapshot 7c2c7b1eddd9391b14c1e4d2f596bd21e3ba465461ccd241e7e70e4a8efede91, descriptor934247332228e134b01565b9e904178b24e0515150172c759609fbb2bc5b6e5d and identity.registration-integrity.v1 contract9a051b12a0f964d244f9f24d8c286a35ca39b67ddd6fbb242c626c6df159497e. Read exact0056 SQL, descriptor/snapshot, existing canonical provisioning triggers and auth-access-policy.mjs. Preserve0000–0055 bytes in a separate frozen history and replay through Admin explicit migration runner on owned disposable targets, with identity proof before every DDL/DML/grant. Validate corrected NULL constraint, legacy nullable compatibility, controlled SECURITY DEFINER function exact arguments/return/search_path/PUBLIC EXECUTE denial, new canonical insertion+Free/model/allowance/event+subject mapping transaction and rollback when any precondition is absent. For least privilege, prepare four independently named limited non-owner/no-membership roles and 0600 private target config in an isolated clone; run policy default dry-run, explicit --apply and repeat, verifying real CONNECT/table/column/function privilege attempts, auth direct canonical/billing writes denied, data provider/token private columns denied and all Dream DB access denied. Test actual Admin business API under restricted auth/data credentials rather than superuser only. Registration must preserve real product rules and IDs, reject duplicate/conflicting legacy evidence without implicit same-email merge. No normal service/database/config changes; record actual commands/cwd/exit/sanitized receipts and separate schema/catalog, ACL, adoption and provider-free auth proof. Luna owns deterministic isolated Route contracts; primary owns new credentials and all migration/fixture/destructive/privilege operations. Do not mark full migration complete until every production DB entry and mandatory real acceptance is closed.

USER REQUIREMENT:
Complete Admin-only database access with actual role grants and controlled canonical registration, preserve old identity/business records and close the SQL NULL constraint gap using a forward migration.

状态：0056候选已冻结；隔离replay/真实role ACL/controlled注册/adoption验证待执行。PUBLIC function grant、nested trigger search_path与backfill evidence需实际验证，不将static tests冒充权限证明。

## Optimized Prompt: 0057/0058 purpose 与 Editor 前向验证

You are the primary owner of forward Drizzle migration validation. Evidence: frozen54–56 replay/catalog and actual restricted ACL/registration pass; Admin generated immutable57 structural expansion and58 NULL-safe purpose CHECK+capability. Pin both SQL/snapshot hashes and descriptor; reuse the explicit named disposable PG ownership proof, normal migration orchestrator and private configs. Preserve all0..56 bytes. Validate upgraded/repeated/concurrent/fresh history, duplicate-column drift at57 rollback and missing-constraint drift at58 rollback with exact ledger/capability,18 delegation/7Editor columns and named indexes/FKs/checks. Prepare primary-only disposable source/Thread/Editor/Gateway-key fixtures; prove3 valid mutually exclusive purpose writes, unknown/null-purpose-withEditor/nullEditor/mixedscopes/nullarray/gateway-without-key refusals SQL23514, and exact Session ON DELETE CASCADE without deleting server/Gateway grants. Do not infer user authorization from FK, do not modify normal PG, do not call providers or print credentials. Record actual command/cwd/exit/output and sanitized catalog proofs, notify Admin/Dream and update docs; no overall completion claim.

USER REQUIREMENT:
验证Admin唯一前向迁移与明确定义的server-persistence/gateway-cli/editor-stdio授权边界，保留Editor与业务主体归属、历史兼容和缺能力failclosed。


## Optimized Prompt: 0059 lossless version storage 前向验证

You are the primary migration/fixture owner. Evidence: actual restricted Deck contract found JSONB negative-zero normalization breaks original Python canonical hash, Admin soleDrizzleowner generated immutable0059 canonicaltext nullable+projectionCHECK+exactphysicalcap. Pin SQL/snapshot/descriptor and all59priorhistory/journal bytes. Prove only named owned DB/user/loopbackport/datadir and run normalorchestrator, no normalPG. Validate upgrade/repeat/two concurrent/freshfull60history/duplicatecolumnpartial rollback exactledger/cap/catalog11columns/FKs/indexes/check. Prepare primary-owned oldversionfixture BEFOREexpand and assert originalPK/hash/jsonb/createdby/time unchanged andnewtextNULL, no guessed historicalbackfill. Newversion writes rawnegativezero canonicaltext+sameJSONBprojection, compare exacttextbytes andprove mismatchedprojectionSQL23514 rollback. Saveallactualcommand/cwd/exit/sanitizedoutput/catalogproof andnotifyAdmin/Dream; onlythenactivateexactnewcapgate andLunapublic19originalhashassertion withoutweakeningit.

USER REQUIREMENT:
保留历史数据/主键/hash与JSONB查询，并用Admin唯一前向migration保存新版本精确canonical字节，隔离验证一致性后启用业务接口。


## 0059 实际结果与原断言修复

主任务冻结0059 SQL SHA `21c7d7c73beb0ec3a9cd163060748a1b41e9305dc1085cb5387668103a9f67e0`，capability `dream.deck-content-canonical-storage.v1` version1/hash `97a95f92efecf3435890fcb3f9c1ce46e33fbed8a3de4dca3a632484de4f1c76`。实际六条迁移子命令覆盖升级、重复、两个并发migrator、全新60项history与预期partial rollback；catalog11列、ledger60且候选单次、原PK/hash/jsonb/time/owner与NULL兼容保持。新canonical text保留负零，JSONB仍可查询，没有猜测历史backfill。

原projection UPDATE检查被0036 append-only trigger先拒绝SQL55000，harness退出1。剩余脚本原样核验冻结字节/catalog，再分别断言原UPDATE55000和新mismatched INSERT23514；退出0，未重复迁移/禁用trigger/降低预期。见[原命令](../exec/admin-auth-data-verification/candidate-0059-receipt.json)、[catalog](../exec/admin-auth-data-verification/candidate-0059-catalog-proof.json)、[校正范围](../exec/admin-auth-data-verification/candidate-0059-harness-correction.json)。正常数据库保持不变。
