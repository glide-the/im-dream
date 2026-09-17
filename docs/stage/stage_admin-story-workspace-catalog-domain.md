<!-- [Input] Registry111 closure scan, current Story Workspace public routes and Admin DTO/Drizzle operation framework. -->
<!-- [Output] Executed cross-project plan and acceptance evidence for Story Workspace browse/edit persistence in Admin. -->
<!-- [Pos] Current Prompt Architect plan; implementation and command receipts must update its acceptance section. -->
<!-- [Sync] 2026-09-15: implement and validate Registry114 catalog operations and Dream consumer replacement. -->

# Story Workspace Catalog 数据接口迁移阶段

## 背景与问题

Registry111已经关闭七个单项审核入口和一个批量审核入口。修正后的dirty-safe AST扫描读取541个仓库Python模块，得到79个production candidate、51个SQL模块、463个SQL literal、29个数据库/driver import模块、53处旧helper调用、403处连接或事务调用、29个Admin data consumer和129个operation name，parse errors为空。该结果是源码候选清单，不代表运行可达或全域关闭。

`backend/routers/story_workspace.py`仍由Dream直接执行Workspace get-or-create/patch、Story list/detail/patch、Character list/detail/patch、Scene list/detail/patch。这些入口共享owner过滤、分页排序、JSON投影、关联读取和patch事务，适合作为下一个封闭业务聚合；Review、Agent output、Runtime、SSE与共享文件系统不进入本阶段。

## Optimized Prompt:

You are the Admin/Dream cross-project architect implementing the next production database-closure slice after Registry111. Read the current Dream Story Workspace router, public DTO models, Story projection repository, route tests, Admin operation registry/receipt/auth/data-transaction framework, Drizzle schema, folder contracts and current architecture documents. Reuse existing strict DTO, Service, typed Drizzle Repository, capability and original-receipt mechanisms.

Design closed Story Workspace catalog operations around actual product actions: get-or-create the current user's default Workspace, browse exact Story/Character/Scene list and detail views, and edit the allowed fields of a Workspace, Story, Character or Scene. Use discriminated request/response DTOs with fixed view/resource enums and explicit fields. Never accept actor, owner, table, column, SQL, database address, path, arbitrary filter expression or transaction selector. Keep all permission filters and persistence in Admin Drizzle. Preserve the existing public Dream route payloads, sort/filter/page semantics, not-found/invalid-query/empty-patch feedback, JSON tags/settings behavior, Scene-to-owned-Story validation and Story/Character/Scene detail relations.

For writes, commit the mutation, explicit safe output projection, operation receipt and audit in one Admin transaction. Define same-request replay, changed-input conflict, concurrent state change behavior, timeout and unknown-commit recovery; Dream must query only the original receipt and must never retry the POST or fall back to PostgreSQL. For reads, use one capability-gated Admin read transaction and return explicit DTOs only. Keep Browser authentication as current Admin OAuth; do not accept arbitrary user IDs.

Admin owns the Zod DTO, Service, typed Drizzle Repository, Route registration, operation catalog and isolated PostgreSQL contract. Dream owns Pydantic DTOs, unified Admin client calls, current FastAPI routes and product response mapping. Preserve Agent Runtime, Runner, ThreadFactory, EventBus, SSE, turn/resume/cancel, resource-policy LKG/admission/lease, shared filesystem and `CLAUDE_CODE_TMPDIR={AGENT_CWD}/{thread_id}/.claude-tmp` behavior. Do not add migration unless the actual Drizzle schema lacks a required structure; all migrations remain Admin-only.

Validate owner isolation, pagination and deterministic ordering, list filters, detail relations, empty/malformed selectors, partial patch semantics including false/zero/empty values, owned Scene Story reassignment, idempotent replay, concurrent write behavior, rollback on output/receipt/audit failure, restricted database role permissions and Dream no-database fallbacks. Update operation artifacts, folder docs, architecture ownership maps, current closure scan and concrete command receipts. Commit Admin before Dream, and keep unrelated worktree changes unstaged.

USER REQUIREMENT:

继续把Dream生产数据库访问迁入Admin，数据库接口严格遵从DTO/ORM设计，保留现有产品交互、Runtime、SSE和共享文件系统语义。

## 所属项目、责任与依赖

| 项目 | 责任 | 依赖 |
| --- | --- | --- |
| Admin | Zod契约、Service、typed Drizzle Repository、权限、事务、回执、审计、Route与隔离PG验证 | Registry111、identity/unified capability、现有Story projection与receipt UOW |
| Dream | Pydantic契约、统一Admin consumer、11个公开路由替换、原响应与错误映射、DB fence | Admin发布的operation hash和capability |
| 协调 | 契约hash、关闭清单、文档、测试回执与两仓提交顺序 | Admin先完成并验证，Dream后消费 |

## 修改范围

- Admin：`app/lib/dream/**`、内部operation Route、生成契约JSON、关联测试与架构/验证文档。
- Dream：`backend/services/admin_data/**`、`backend/routers/story_workspace.py`、关联测试和架构/阶段文档。
- Drizzle：只读核对现有表、索引和约束；缺口出现时才在Admin前向migration中扩展。
- 保持不变：审核Registry111、Agent output Registry109、Runtime/SSE/EventBus、资源策略、共享文件系统及临时目录协议。

## 正常流程与失败处理

1. Dream从当前OAuth请求派生调用身份，构建封闭DTO并检查Admin capability。
2. Admin验证DTO和scope，在一个UOW中通过Drizzle执行owner过滤、读取或写入。
3. 列表按现有过滤、排序和分页返回；详情返回现有关联投影；写入提交结果、receipt与audit。
4. Dream严格校验结果与原selector/ID一致，再映射为原FastAPI响应。
5. 404、非法sort/filter、空patch、关联Story非owner、并发冲突保持明确状态；服务或capability缺失失败关闭。
6. 写结果未知时只查询原operation/request receipt；absent或损坏继续返回unknown，不重发、不直连数据库。

## 验收与风险

- Admin：focused Vitest、全量`pnpm test:run`、`pnpm lint`、`pnpm build`、runner-owned restricted-role PostgreSQL合同。
- Dream：compileall、focused consumer/route/request-auth tests、公开路由DB fence和修正后的AST closure扫描。
- 文档：变更Markdown本地引用全部存在，目录索引与契约hash一致，`git diff --check`通过。
- 风险：动态Story投影列、legacy text timestamp/JSON、分页排序、artifact Story约束及写后响应若处理不一致会改变产品行为；必须用当前源码oracle和真实Drizzle schema逐项冻结。
- 本阶段技术验证不能替代正常Dream/Admin/Gateway/PostgreSQL上的真实账户业务验收。

## 实施与验收结果

Admin已注册三个Registry114操作。`storyWorkspaceCatalogDto/Repository/Service/Handler`使用closed Zod union、typed Drizzle实体和单一UOW；read不生成receipt，workspace/patch把业务结果、实体审计、通用operation审计与receipt原子提交。公开`artifact_available`从canonical `artifact_status`派生，兼容物理列不进入Drizzle模型；没有生成或应用新migration。完整Registry114 SHA为`dc80b77410aac58528dde77578154d9848d9dfc3bf55de4a35c8c315a81af704`。

Dream新增`story_workspace_catalog_data.py`严格Pydantic consumer并替换11个公开路由。查询和patch只经过统一Admin client；unknown write只读取原receipt。路由源码没有`database`导入、SQL literal、连接或事务helper，原FastAPI payload与错误行为由provider-free fake覆盖。Runtime、SSE、EventBus、资源LKG、共享文件系统和`.claude-tmp`代码均未修改。

| 验证 | 结果 |
| --- | --- |
| Admin focused DTO/handler/registry/receipt/review/schema Vitest | 8 files / 28 tests passed；exit 0 |
| Admin TypeScript | `pnpm exec tsc --noEmit`；exit 0 |
| Admin whole unit suite / lint / build | 240 files / 1913 passed / 36 configured skips；`pnpm lint`与Next production build均exit 0 |
| Admin isolated PostgreSQL | 62 migrations applied；restricted executor；6/6 catalog cases passed；cluster cleaned |
| Dream focused consumer/route/review/auth pytest | 49 passed；exit 0 |
| Dream affected broad Story suite | 724 passed / 35 failed / 3 skipped；exit 1；失败为旧auth覆盖、SQLite Chat列和本地vendor artifact harness，详见下文 |
| Dream corrected AST scan | 543 modules；50 SQL modules；454 SQL literals；28 driver/import modules；52 legacy helper calls；392 connection/transaction calls；parse errors 0 |

首次PostgreSQL harness因测试fixture只设置`artifact_status/script_size_bytes`而违反现有artifact identity完整性约束，未进入业务断言。fixture改为完整`dream_episode` identity/revision/sync bundle后重跑通过；生产约束与实现没有放宽。Admin整仓首轮1912 pass/1 fail发现canonical Drizzle明确禁止`artifact_available`布尔影子列；实现改为从`artifact_status`派生公开值并撤回schema扩张，随后focused28、whole1913、lint、type、build与PG合同全部通过。

Dream扩展Story suite首轮724 pass/35 fail。其中本次删除`story_workspace.database`使一项旧test patch失效，已改为直接验证route不初始化Workspace，随后连同catalog/review/auth聚焦49项通过。其余失败集中在旧测试仍绕过当前Admin auth导致401、legacy SQLite `chat_message` fixture缺少`history_final_text`，以及本机未提供的vendor episode artifact；这些不是Registry114断言通过，且没有通过恢复Dream SQL或降低认证修正。正常本机账户/Google/模型/完整业务验收及其它Dream数据库领域仍未完成，协调goal保持active。
