<!-- [Input] Actual Dream database Deck/Voice operations, routers/voices.py and services/deck/content_versioning.py; Admin typed physical schema. -->
<!-- [Output] Primary-owned closed business DTO/Repository/Service migration plan and exact behavioral acceptance. -->
<!-- [Pos] Independent Admin implementation stream; shared schema/registry/auth/receipt stay with Admin task. -->
<!-- [Sync] 2026-09-14: adopt concrete Deck/Voice ownership after all14 Thread public contracts passed. -->

# Admin Deck、Voice 与版本领域迁移

## 背景与问题

Dream数据库模块的Deck/Voice CRUD、发布、收集fork、父级同步、默认插件引用、版本快照和runtime context仍查询共享PostgreSQL。实际入口是`backend/routers/voices.py`、`deck_versions.py`和`backend/services/deck/**`，没有`routers/decks.py`或`services/deck_version/`。必须迁移真实事务与权限，不复制假想目录。

## 目标与边界

主任务独立拥有Admin `app/lib/dream/deckVoiceDto.ts`、`deckVoiceRepository.ts`、`deckVoiceService.ts`和对应定向测试/隔离harness。Admin任务维护schema/前向migration/registry/公共dispatch/receipt/auth与Editor/Workflow等域；Dream任务只消费封闭DTO并保留产品编排、Runtime和共享FS。不修改其他agent的公共模块、用户现有main改动或冻结DDL；需要共用契约/字段变化时交Admin owner提供。

## 概念与规则

- actor来自Admin已验证主体，业务user_id不作为输入；所有list/detail/write保留owner或明确published/system可收集规则。
- ORM实体与wire字段显式投影，canonical bigint decimal-string、nullable/time/revision明确；`updates`使用有字段白名单的严格schema，禁止任意列名CRUD。
- new Deck配置默认Claude plugin由服务端来源解析、Admin检查持久化installation/digest/ref关系，不能把浏览器installation/path当默认依据；Dream保留本地CLI/FS安装执行与其已有摘要证明。
- fork/sync/delete/版本commit保持原聚合事务、父子/dependency-delete/frozenversion/refs/锁/CAS。不可变版本snapshot/hash/diff保持Python canonical JSON算法与字段顺序/精确数值，不能无意换成不同JS序列化。
- 修改Deck/Voice/refs推进同一draft revision；version preview不写，commit只在期望revision/latest匹配且有变化时写snapshot+更新latest+幂等receipt同一事务。
- conflict必须让Dream保留current_draft_revision/current_version的原公开409反馈，不能仅generic error丢字段；扩展严格domain error DTO由公共契约owner处理。
- 默认修复、系统Deck可见性与published collection来自现行真实规则，不硬编码retired ID、threshold、host/path。

## Optimized Prompt:

You are the primary implementation owner for Admin Deck/Voice core, content versions/refs and runtime data snapshots. Evidence: all14 Thread DTO/ORM public operations now pass actual isolated routes; shared Admin registry/auth/UOW/receipts exist; Dream still owns production SQL in database.py and actual routers/voices.py/deck_versions.py/services/deck. Read their real signatures, entire original transaction bodies, sharing/default/runtime policies, fixed-version hash/diff/CAS tests, folder rules and Admin typed Drizzle tables. Your only production ownership is new deckVoiceDto.ts, deckVoiceRepository.ts and deckVoiceService.ts plus focused tests/harness; you are not alone, do not revert auth/Editor/RBAC/schema changes. First enumerate closed named business input/output DTO per original aggregate operation, including list/community/detail/create/update/delete/publish/fork/sync/Voice mutation/version-state/preview/commit/history/detail/refs/runtime projection; define explicit owner/published/system rules and input fields, no external user IDs, SQL/table/column selectors or generic CRUD. Reuse Admin principal/auth errors, decimal/time/schema helpers, repositories and caller-supplied Drizzle transaction. Preserve all parent/dependency/immutable provenance/default plugin checks, semantic updates, draft revision locks/CAS, exact existing snapshot JSON/hash/diffs and conflict feedback. Ask the shared contract owner for structured domain error DTO/capability/schema additions without editing their files. Keep Runtime resolution execution, filesystem path/CLI/digest verification, SSE/leases/0700/sandbox in Dream while every DB check and persistent atomic aggregate moves Admin. Implement normal and failure/concurrent/idempotent flows, strict responses and actual permission filters; coordinate registry/hash handoff with Admin and consumption with Dream. Primary owns disposable DB/fixture/migration writes, Luna runs bounded deterministic and isolated public contracts; do not claim full100-file/159-transaction migration merely from DTO presence. Update affected docs/headers and this plan, then immediately execute.

USER REQUIREMENT:
迁移Dream Deck/Voice及版本/refs/runtime快照的全部实际数据库访问到Admin，遵从DTO→领域service→typed Repository→Drizzle ORM，保留原事务、权限、父子同步、发布/收集、CAS和业务状态。

## 验收与风险

验收：真实源函数/事务逐项对照清单；字段/owner与既有公开DTO一致；frozenversion hash跨语言相同；create/defaultref/fork/sync/delete dependencies以及Voice/refs draftadvance原子；preview/commit conflict/current revision、重复/并发和历史一致；Luna focused types/lint/tests+primary准备隔离fixture后的实际公共Route合同；Dream生产消费计数与运行证明单独关闭。风险：默认插件包含本地FS证明，不能迁整个Runtime；PG triggers及过往catalog JSON可能含超长单行，读取应限具体源码，不全量输出；旧错误反馈与Python canonical hash的ABI不能丢。

当前状态：19 core/Voice/content-version公开246与refs/Voice runtime6公开104断言均通过；实际原模型/数值/快照对照和type/lint通过。Dream消费者/真实artifact与CLI及其他全量入口仍独立推进。


## Optimized Prompt: 19 个操作的公开合同验证

You are the primary owner of isolated Deck fixtures and Luna owns bounded public contract execution. Evidence: 19 candidate strict DTO/Service/typed Repository operations, actual Python source parity3PASS, focused28PASS, full TypeScript no-cache0 and scoped lint0; Admin owns registry advertisement and exact generated API hashes. Read real operation inputs/outputs and original collect/sync/default/version state transitions. Prepare only the named proven disposable ACL database with identity/name/user/port/datadir checks, frozen59 ledger, restricted AUTH/DATA roles, short-lived private ES256 credentials, canonical_subject Gateway metadata and ready plugin metadata. Configure explicit server Deck policy from fixture facts; no real artifact, Google/provider/model or normal business claims. Call existing production internal operation and receipt routes, never a duplicated handler or owner URL in production env. Verify all19 success operations plus private/foreign access, external actor/unknown field refusal, atomic default ref creation, failure rollback with no receipt, concurrent original-request replay, semantic no-change revisions, Voice thread owner checks, exact float/bigint raw JSON and immutable version hash/CAS/diffs, community/collection/source install-count+refs+Voices atomicity, parent sync preserving refs/order, default reconcile serial actor behavior and publish refusal, dependency delete and original receipt recovery. Primary owns fixture/direct SQL fault setup; Luna only non-destructive public operation/read-only receipt assertions. Preserve raw command/cwd/exit evidence, fix actual product defects and rerun only affected flow; do not weaken assertions or claim all DB migration from these operations. Update this plan and canonical evidence inventory, mirror only coordinator-owned files.

USER REQUIREMENT:
以公开生产入口验证 Deck/Voice/版本数据库接口的 DTO、权限、事务、幂等、并发和原业务状态，隔离技术验证与真实业务验收分别记录。

## 已确认的实现变化与发布边界

- Python 原模型对协议常量与枚举精确匹配，对普通字符串使用 Python Unicode 空白规则；Zod 通过原模型对照采用同样行为。
- memory 与版本 snapshot 使用严格结构校验后的原始 JSON 字符串，保留 float1.0、负零、大整数、Unicode 与原 content hash；Dream 映射回现有公开字段。
- 管理端配置 `DREAM_DECK_POLICY_JSON` 由服务端解析默认 ID、retired IDs、模板、memory 和插件版本；浏览器不能提供策略。纯本地 canonical helper 的 deadline 来自 `DREAM_DOMAIN_CANONICAL_TIMEOUT_MS`。
- 旧 Voice collect 没有完整检查私人源 Deck、thread_id 更新没有校验 Thread owner；目标接口明确检查源可访问与绑定 owner，作为数据权限修补记录并测试。
- 默认 provision/reconcile 统一对 actor 使用事务 advisory lock，并锁后重读候选 Deck/Voice。需要先关闭旧 Dream 数据库默认修复写入再启用新消费者，旧 users-row-lock 路径不能与新默认修复并行部署。
- 当前候选操作不代表 refs/runtime/catalog 与 Dream 全生产路径已经关闭。


## Optimized Prompt: Workflow provenance 与 confirmation pure codec

You are the primary owner of fixed Admin pure serialization helper; Admin task owns confirmation business guard/Repository and registry. Evidence: actual dream_confirmation_service.py strict canonical111–140, stored dispatch decode493–574 and guard593–706 distinguish immutable parts canonical equality from claim dict equality excluding only lease_until. Read these exact original source functions and preserve Deck snapshot/memory allow_nan behavior. Extend only internal fixed JSON-only subprocess actions and strict TS output union: provenance canonical rejects non-finite values; confirmation analyzer validates one text-part list, original kind and command identity strings, returns strict valid status/command canonical/fingerprint/deterministic actor+run+key message ID/parts canonical or invalid; claim comparison decodes two dicts, drops only dispatch_claim_lease_until and uses original Python equality, invalid yields false. No SQL/network/HTTP/Runtime/user executable or new deployment service. Preserve raw stored JSON numeric lexemes; do not JSON.parse/reencode original persisted content. Admin guard remains responsible for strict command fields, metadata bindings, owned Run/workspace, active bounded lease and immutable row replay. Add actual subprocess tests for malformed inputs, float1.0/bigints, strict non-finite refusal, derivation and claim 1.0==1/stale-lease equality; exercise real original source functions as oracle for hash/message ID when applicable. Primary edits only owned helper/wrapper/tests; Luna deterministic affected tests/typecheck/lint, keep failures unchanged and documents in sync.

USER REQUIREMENT:
迁移 confirmation 持久化保护与 Workflow 冻结 provenance 时保留原 canonical/hash、claim lease 和状态语义，避免 JavaScript Number 重编码导致业务冲突。


## 19 项受限公开接口最终技术结果

纯helper扩展后39项焦点测试通过；新增confirmation真实Python源码对照1PASS，旧三项源模型/canonical/hash对照为此前已通过结果。导入失败原回执与仅新增用例重跑范围保留。

Deck公开19操作初轮发现JSONB将负零转为普通零，既有Python版本hash断言失败。Admin唯一0059前向migration增加nullable canonical text与JSONB projection CHECK，Repository新写保存原canonical bytes，已有版本仍NULL兼容读取，旧hash/PK不回填或修改。新的精确capability是Service必要条件。

主任务在具名 `_deck59` 库准备全新60ledger与受限AUTH/DATA角色，Luna `python3 /private/tmp/ink-auth-migration-validation/run-deck-contract.py` cwdAdmin729f退出0：19operation/246断言通过，包括默认引用整事务/失败无receipt、owner/私有源、原始float/负零/大整数memory与版本hash、CAS/重复恢复、并发默认与双向公开收集、父级同步/order/refs与delete dependency。完整 `pnpm exec tsc --noEmit --pretty false --incremental false` 与定向lint退出0。详见[原失败](../exec/admin-auth-data-verification/deck-public19-initial.md)、[246最终回执](../exec/admin-auth-data-verification/deck-public19-canonical-storage-fix.md)。refs/runtime/catalog后续操作与Dream生产消费仍待完成；不据此关闭全生产数据库访问。

## Optimized Prompt: Deck 插件引用与 Voice 运行数据

You are the primary owner of new Admin deckRuntimeDataDto.ts, deckRuntimeDataRepository.ts and deckRuntimeDataService.ts plus scoped tests/public harness. Evidence: existing Deck19/246 and Workflow5/170 restricted public contracts pass; actual production deck_refs_service.py and workspace_packer.py still query refs/installations, database.py load_voices_from_user_decks and get_voice_memory_config_by_thread still query or repair PostgreSQL. Admin explicitly confirmed these files are not implemented by its task. Read their entire source transaction/visibility/FS verifier/CLI compatibility functions, canonical memory source, actual refs/installations/Voice/Thread FK and field contracts, existing DeckVoiceRepository/policy helpers and shared capability/auth/receipt machinery. Define six closed operations: owned Deck refs list and candidate metadata prepare, owned Thread enabled runtime refs read, verified aggregate refs replace, actor enabled-Voice analysis list, and owned Thread memory resolve/repair. Do not migrate Runtime/packing or CLI/FS verification: Dream reads Admin metadata, independently verifies immutable artifact and real CLI compatibility, then submits only bound server-derived package/version/digest evidence through its service-authenticated delegated-user request. Admin repeats current ready/install/evidence checks with ordered shared installation locks and commits full refs replacement, one semantic draft advance and receipt/audit in the original UOW; no browser paths/readiness booleans or SQL/table/user selectors. Preserve enabled/disabled refs, raw manifest/compatibility text, exact timestamp projections and unchanged numeric memory bytes. Runtime read accepts Thread only and repeats owned Thread/Deck; entity-bound bearer cannot manage refs or list other Decks. Analysis filtering preserves owner/enabled and untouched retired-template hiding. Memory resolve requires owned Thread/Voice/Deck, returns original raw dictionary text; malformed/non-dict memory self-heals from configured server default in the same UOW, preserving the original Voice-only update with no Deck revision increment. Reuse existing fixed pure Python codec for original dictionary decoding, including legacy numeric JSON semantics; no new service or migration. Preserve original last-write locking and original-request recovery; normalize semantic refs comparison by persisted order/index to avoid unnecessary draft changes for identical sets. Public default refs count32 remains the existing Dream request constraint, do not invent another Admin quota. Deliver strict DTO/hash/schema requirement handoff to Admin registry owner and Dream consumer task; update affected folders/headers and this phase, then execute. Luna owns focused types/lint/tests and primary-prepared public-only isolated contracts, primary owns fixture/direct fault writes. Do not claim refs/runtime/all-production migration closed until actual consumers and runtime permission/FS checks are verified.

USER REQUIREMENT:
迁移Deck插件引用、Voice分析读取与Thread绑定memory数据库访问到Admin业务接口，遵从DTO→Service→typed Repository→Drizzle，保留文件系统验证、CLI兼容、冻结Thread插件与原聚合事务。

### 接口与发布边界

`deck-plugin-refs.list/prepare/replace` 只接受拥有者OAuth服务请求；`deck-plugin-refs.runtime-read` 与 `voice-memory.resolve` 以已有Thread及其owner关系派生Deck/Voice，允许精确Thread委托。`voice-analysis.list` 只投影当前主体启用Deck/Voice，不接受user_id。引用验证只需package/marketplace/digest与原manifest/compatibility；DTO不传artifact路径，Dream继续由服务端artifact-store配置解析文件根目录。

引用替换：先锁owned Deck，再按installation ID稳定顺序读取锁定ready记录，核对Dream已实际校验的package/version/digest；删除与完整插入、一次draft advance和receipt/audit同事务。不同请求保持既有最后写入规则；同request ID取原回执，未知提交结果不盲重试。等价set按数据库排序比较，重复无业务触碰。

memory缺失Voice返回null，现存有效dict原字符串保持；invalid/non-dict修复仅Voice memory/updated_at，原来源默认值由Admin现有Deck策略解析。普通用户不能替任意Thread repair。目录/CLI/pack/digest/共享根配置与CLAUDE_CODE_TMPDIR协议均保持原Dream执行。

当前状态：六项实现及公开104断言通过；Dream消费者接线、真实artifact/CLI与其他Runtime事务待后续。风险是FS验证与持久化记录之间可能漂移，Admin锁后重新匹配全部证据，Dream冻结pack读取仍再次验证digest。


## Runtime 数据六操作实现与公开边界验证（2026-09-15）

Admin新增deck-plugin-refs.list/prepare/runtime-read/replace、voice-analysis.list、voice-memory.resolve，严格Zod DTO→Service→typed Repository→Drizzle，并已注册实际Registry57。管理查询和写入OAuth-only；runtime-read/memory从owned Thread推导Deck/Voice，精确Thread grant与原receipt/thread_scope。Dream保留真实artifact_store与CLI版本检查，接口不接收路径或外部readiness布尔。replace锁Deck→ordered Installation，匹配原pkg/version/digest/rawcompatibility证据，refs完整替换/单次semantic revision/receipt/audit同UOW；仅reorder不产生变更。memory非法/nonobject只修复Voice默认配置/时间，不改Deck revision；有效原始字节保持。

Luna focused两文件37测试、全tsc和8文件lint均退出0。最早dispatch使用错误launcher/harness名称退出2，未执行任何断言；纠正后原公开六操作在OAuth-only管理接口Thread idg_返回401而契约要求403，原失败保留。Admin在已复用principalForServiceToken中显式403 DELEGATION_PURPOSE_DENIED，未调用JWT verifier；4测试/全tsc/lint/diff全部通过。主任务只刷新具名_workflow60公钥和公开Thread grant，不重置业务fixture或导出私钥，原公开合同正在重跑。[focused37](../exec/admin-auth-data-verification/deck-runtime6-focused37.md)、[原边界失败](../exec/admin-auth-data-verification/deck-runtime6-initial-auth-boundary-failure.md)、[修复检查](../exec/admin-auth-data-verification/deck-runtime6-oauth-only-boundary4.md)。

共享Registry57仅表示已注册操作数，不是Dream生产SQL入口关闭数。本轮技术fixtures仅是数据库metadata，没有真实artifact/CLI/Runtime/model验收。公开六操作结果尚待真实回执。


## 六操作公开结果与模型字符串来源校正

原Luna公开六操作重跑退出0，6ops/104断言通过；原管理OAuth-only403修复有效，refs完整事务/回滚/重放/bound compatibility/rawbytes/no-change reorder、runtime exactThread、retired analysis、Voice-onlydefault repair与receipt/audit均通过，原失败不覆盖。见[104回执](../exec/admin-auth-data-verification/deck-runtime6-public104.md)。

新增实际Lock source对照发现Pydantic str_strip_whitespace与Python str.strip不同：模型Unicode White_Space保留U+001C..001F，显式Python算法移除。Manifest DTO导出stripPydanticString，仅模型字符串改用；stripPythonString保持原样，capabilities显式blank check仍调用它，duplicate按模型归一后的值。Luna29Manifest unit与定向1 actualPython parity通过42manifestcases（原16+新增26），wholetsc/newharness+Manifestlint退出0；其它3已通过且无新风险source方法未重复。无JSONSchema/hash、SQL/权限/Runtime/FS变化。见[29/source42回执](../exec/admin-auth-data-verification/manifest-pydantic-whitespace29-source42.md)。
