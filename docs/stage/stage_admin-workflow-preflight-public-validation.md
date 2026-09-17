<!-- [Input] Frozen 0060, actual restricted ACL proof and Admin-owned full Preflight public harness dependency. -->
<!-- [Output] Proven named disposable target, public production-route contract and retained failure receipts. -->
<!-- [Pos] Coordinator owns database identity/fixture/fault preparation; Admin owns DTO/service/Repository and Luna executes bounded contracts. -->
<!-- [Sync] 2026-09-15: one Prompt Architect pass before isolated full Preflight validation. -->

# 完整 Preflight 数据接口公开验证

## 背景与问题

0060 的不可变原请求绑定、九列 catalog、迁移重放与受限角色已通过隔离验证。完整 Preflight 领域的输入校验、原 fingerprint、三阶段原请求恢复、授权、八项检查和执行条件还需要实际公开路由验证。迁移成功不能代替应用合同通过。

## 目标与边界

Admin 任务拥有完整 Preflight DTO/Service/Repository、公开 harness 和薄 ingress/共享注册。主协调任务仅负责本轮明确命名 `_preflight61` 隔离数据库身份、0060 和最新 ACL、按 Admin 实际文件提供的最小 fixture/失败注入。Luna 只调用公开生产 operation/receipt 入口和 SELECT 核对；真实账户、凭据、模型、普通数据库不进入本阶段。Dream 的生产入口关闭仍是消费端独立责任。

## 概念与规则

- 数据源仅是本任务已拥有的 `_workflow60` 技术 fixture，包含完整合法 Run 和已有锁/manifest 验证事实；它不是正常数据库 clone，也不冒充真实业务链路。创建新 target 前后核对 source 表行数/摘要不变，不重跑或重置既有 104/163/78/230 结果。
- 先核验 PostgreSQL 数据库名、用户、loopback 端口、data_directory，再创建新 target。现有同名 target 不覆盖或清理。只在新 target 执行冻结 Admin Drizzle 0060；旧 60 SQL 和 journal 前缀保持不变。
- schema capability `dream.workflow-preflight-request.v1` v1/hash `7123babb03535e0a0c7a818e902c331cefbe73c660b46395136dcc9a5b19f3da` 与 API capability、部署版本分别判断。0060 SQL SHA `037508ab9cf0caac9bf1ada33d50a78aae45767a37d388721a241080f0f43b51` 不改动。
- AUTH 和 DATA 各用明确受限角色，DSN 都必须是新 target；Dream 角色没有 CONNECT。目标配置文件 0600，凭据不进入文档、公开日志、任务消息或浏览器。
- 完整 fixture 和 fault SQL 必须根据 Admin 已读取代码产生的实际 DTO/source projection/harness 文件定义后执行，不能猜字段或复制另一套状态机。主任务执行必要种子与失败注入；Luna 不做 DDL、直接数据修改、TTL 修改或 secret 操作。
- 当前 OAuth 主体、scope、workspace、原 request/fingerprint、不可变请求绑定、receipt 并发恢复和未知提交结果均由 Admin 真实生产层验证。相同输入重放原结果，变更输入拒绝；未查到 receipt 不代表回滚，不盲目重试写入。
- 正常成功、权限拒绝、八项检查失败、pending/完成/恢复、过期、并发和不可用结果以实际插件/领域状态为准；不修改第三方状态机或为测试增加生产 fallback。
- Runner、SSE、turn/resume/cancel、资源策略与共享文件系统协议保持既有执行归属。本轮元数据验证不声称已执行实际 Agent、Google 或模型。

## Optimized Prompt:

You are the primary cross-project coordinator. Admin owns full workflow Preflight DTO, Service, typed Repository, protocol implementation and its real public contract harness; Dream owns consumers. Verify the frozen Admin Drizzle 0060 hashes and prior sixty migration bytes/journal prefix. Before any database operation, prove the owned disposable PostgreSQL database name, user, loopback host/port and data directory. Create a new explicitly named _preflight61 target only from the already owned _workflow60 provider-free technical fixture. Never clone the normal business database, reset an existing target or rerun passed domains. Capture source table count/digest before and after target preparation. Apply only the frozen forward 0060 through the Admin migration mechanism and latest explicit restricted ACL, recording actual command/cwd/exit and capability/catalog outcomes. Require both AUTH and DATA connections to target the new name with their existing distinct least-privilege roles and prevent Dream CONNECT. Store private DSNs and secrets in 0600 task-owned temporary files and emit only sanitized evidence. Wait for the Admin task's actual fixture DTO, source projection, eight-check minimal fault recipes and public harness before business seeding; do not duplicate their algorithm exploration or invent fields. Primary owns fixture/DDL/fault/TTL/secret preparation, while the Luna test runner executes a bounded public production-route contract and SELECT-only verification. Cover normal success, current OAuth subject/scope/workspace/entity checks, original request/fingerprint identity, immutable binding, pending/completed/recovery, expired credentials, check failures, concurrent duplicate replay, input conflict and unknown commit restoration without blind retries. Preserve strict DTO → domain Service → Repository → ORM, original transaction boundaries and Runtime/SSE/resource-policy/shared filesystem semantics. Retain failed harness receipts and fix their actual cause without relaxing assertions. Update this plan, folder index and exact coordinator-owned worktree mirror, and distinguish technical validation from unexecuted normal-user Google/model acceptance. Do not mark either downstream task or the overall goal complete.

USER REQUIREMENT:
按 DTO/ORM 设计将数据库访问迁入 Admin，使用具名隔离数据库验证完整 Preflight 公开业务协议、权限、事务、并发与失败恢复。

## 评审、验收与风险

分工满足 Admin 持久化与 Dream 执行边界。阶段顺序是 target/migration/ACL → 实际 fixture 文件评审 → 主任务最小种子/fault → Luna 定向 type/lint/unit/公开合同 → 消费者接入。验证命令使用 Admin 实际 migration/ACL 工具以及其实际 public harness，执行后补充 cwd/退出码/输出；任何未执行步骤保留 pending。风险包括 fixture 已被先前公开写入改变、短时 token 在 type gate 等待期间过期、source clone 混淆真实验收以及尚未注册 API。只准备新 target，不改变 source；只刷新所需凭据，不 reset 数据；未注册能力不能提前宣称 Dream 可消费。

当前状态：首次完整24合同退出1且原首failed历史保留；补验完整命令仍退出1，在read-passed-active原事实自然过期时停止，已越过前置执行/源码/并发/replay及checking/failed读取断言。后续8剩余读取74断言、原权限末段11断言、四类故障96断言、原结果恢复与初始UOW回滚44断言、三阶段真实COMMIT后中断及父恢复54断言全部通过。不能把分层补验报告为原24一次全通过。Dream全部生产入口关闭及真实Google/正常账户实体/模型仍未达成，goal active。


## 目标准备的实际结果

主任务 `python3 /private/tmp/ink-auth-migration-validation/prepare-preflight61-target.py` 工作目录Admin729f，退出0。两个实际子命令 `node packages/db/dist/migrate.js` 与 `node drizzle/data/auth-access-policy.mjs --apply` 均0；目标identity与exactcap/ledger61通过，源技术表count/digest前后相同。私有0600配置的AUTH/DATA均指新target，不包含业务seed。见[目标证明](../exec/admin-auth-data-verification/full-preflight61-target-proof.json)、[实际子命令](../exec/admin-auth-data-verification/full-preflight61-target-command-receipt.json)。

## 首次公开失败、评审与定向修复

实际原服务模型/Release与Lock hash、builder binding/snapshot、输入/fingerprint/full read投影构造24 cases、9独立Deck、9安装与10materialization事实；主任务种子与短时OAuth/原checking映射准备均0。没有把原零安装/零materialization的clone当完整正向fixture。Luna公开入口命令退出1，第一`fresh-passed`实际failed(binding_release/DECK_PLUGIN_UNAVAILABLE)，stage1/audit1；后续23 cases没有执行。原预期passed保持，不能改成failed掩盖缺陷。

受限DATA角色实际Repository.binding SELECT/行锁通过，两个真实生产parser均接受；catalog确认旧audit唯一索引为request_id/action/resource_type/resource_id，原阶段只改metadata.stage、键相同。主任务只在本轮隔离库尝试旧键duplicate INSERT，实际23505/准确索引名并rollback，原audit bytes不变。修复范围限Admin Repository的固定服务端stage参与resource digest，原action和request相关性、同stage唯一性、旧index/历史receipt保持，不新增migration/capability/状态机。

另一个原源码回执证实lock/snapshot/input_hash outer whitespace原PFT签名使用raw存储字符串，输出DTO会归一；Admin签名调整为raw六字段及UTC expiry，35最小tests/type/lint/diff通过，70契约hash与0060不变。首次24使用clean IDs，两个缺陷分别验证。

定向恢复使用新0600remediation fixture：保留原24文件及期待不变，先public GET恢复整个旧failed回执并比对原service，然后新建第一成功原请求、保留23未执行cases的输入/期待/ID。未知提交不盲重试，已确认旧请求terminal failed后才创建新请求；不reset原PF/map/audit/receipt。固定stage-key最小gate与新公开合同执行后再记录实际结果。

## 回执归档检查

自动审批曾拒绝直接归档，因为尚未证明密码或Token没有进入回执。主任务随后只读加载40份0600私有配置，按实际secret、tokens及数据库密码进行原值、JSON转义、URL编码和base64比对，同时检查9类凭据模式；16份公开候选均无命中。生产harness的cases[].token只允许五个枚举名称，实际tokens.*值全部参与检查。归档器再次逐文件核验SHA，候选变化时停止，不复制私有文件。

- [preflight-public-artifact-disclosure-proof.json](../exec/admin-auth-data-verification/preflight-public-artifact-disclosure-proof.json)
- [preflight61-public24-initial-failure.md](../exec/admin-auth-data-verification/preflight61-public24-initial-failure.md)
- [preflight70-stage-audit-key-gate.md](../exec/admin-auth-data-verification/preflight70-stage-audit-key-gate.md)
- [full-preflight61-remediation-proof.json](../exec/admin-auth-data-verification/full-preflight61-remediation-proof.json)

## 分层补验的实际结果

四类独立fault公开接口输出均与原源码相同，stage2/2/4/3、snapshot增量0/0/1/1、Run/Session无新增。恢复验证只在真实最终COMMIT完成后注入一次响应丢失，原passed/full source及PF/map/receipt/audit精确不变；当前过期read Token NULL，原bounded结果保持，新request按原规则生成新PF；损坏cipher/workspace返回503，canonical返回403；初始expiry/checking/map/audit同时rollback。三自有child在checking/binding/snapshot真实COMMIT后准确SIGKILL(-9)，父GET/replay只报告in_progress且保留原stage/snapshot，不resume。

读取补验先保留两次原Pydantic ID/expiry准备异常（零新增回滚）和markerless consumed范围错误，再仅新建即时active/expired两marker事实，旧consumed/expiry/权限六cases全部保留，8cases/74断言通过；complete末段other absent/read-only403/thread403/actor selector400及全state不变11断言另通过。原完整合同两次退出1真实回执不删除、不改期待。

- [preflight61-remaining-read-marked-pass.md](../exec/admin-auth-data-verification/preflight61-remaining-read-marked-pass.md)
- [preflight61-receipt-permission-tail-pass.md](../exec/admin-auth-data-verification/preflight61-receipt-permission-tail-pass.md)
- [preflight61-selected-faults-catalog-corrected-command-receipt.json](../exec/admin-auth-data-verification/preflight61-selected-faults-catalog-corrected-command-receipt.json)
- [preflight61-recovery-proof.json](../exec/admin-auth-data-verification/preflight61-recovery-proof.json)
- [preflight61-interruption-command-receipt.json](../exec/admin-auth-data-verification/preflight61-interruption-command-receipt.json)
- [preflight-public-final-disclosure-proof.json](../exec/admin-auth-data-verification/preflight-public-final-disclosure-proof.json)
