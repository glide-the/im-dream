<!-- [Input] Actual default Workspace Python source, existing Admin typed schema and shared OAuth/UOW. -->
<!-- [Output] Primary-owned default Workspace provider design, implementation and validation gates. -->
<!-- [Pos] Registered76 isolated default Workspace gate; Dream consumer and full production closure remain separate. -->
<!-- [Sync] 2026-09-15: retain candidate21/registration20 and public347/recovery90/preservation159; consumer pending. -->

# 默认 Workspace 数据接口迁移

## 背景与问题

Dream `services/story_workspace/agent_integration.py:get_or_create_default_workspace` 查询 owned Workspace，以 `created_at ASC, id ASC` 选择最早一项；没有时随机 UUID 创建原默认名称和空 settings，并独立提交。`_story_workflow_current_user`、`_deck_current_user`、`_deck_plugin_current_user` 等仍调用此函数直连数据库，因此已替换的 Preflight 数据操作不能据此宣称整条路由无 PostgreSQL。

Admin 当前 schema 已有 `storyWorkspaceWorkspaces`，unified capability、受限 Data 角色和通用 result/audit UOW 已存在。该默认查询不新增表、字段或 migration；既有 text Workspace ID 不能因新建使用 UUID 而统一强制 UUID。原查询不按 deprecated Workspace status 过滤，迁移不能自行改变选择规则。

## 目标与边界

主协调独立拥有新 `workspaceDefaultDto.ts`、`workspaceDefaultRepository.ts`、`workspaceDefaultService.ts`、相关新测试/source adapter 与专用 policy。Admin 任务拥有共享 Route/Receipt/Registry/capability 广告，待候选通过后接入；Dream 任务待真实注册后消费。所有 Agent 保护彼此已有修改，不回退、不格式化无关代码。

规范候选 `workspace-default.ensure`：OAuth `dream:write`、闭合空 input `{}`、output `{workspace_id: string}`。Actor 从 live OAuth canonical mapping 推导，不接受 user/workspace/table/SQL/settings/name 字段，也不接受 entity persistence grant。identity/unified exact schema requirements 与 API descriptor 分开检查；不依赖最新 migration head。

## 概念与规则

- 原先 owned 最早项直接返回原 text ID；新建原默认名称集中在非 secret policy，settings 使用原空对象，不增加 deployment 环境分支或用户可编辑配置。
- 同 canonical actor 的默认初始化通过 scoped transaction advisory lock 串行化，避免同时无 Workspace 时创建多个默认项。创建、bounded result、receipt 和 audit 同一 Admin UOW；失败整笔 rollback。
- 同原 request 的 replay 保留原有界 ID，恢复前检查该 Workspace 当前仍由 canonical actor 拥有；不要求它在随后新增 Workspace 后仍为最早，也不自动改成另一实体。GET 只原操作/request，失去当前 owner 不恢复结果。
- 新 request 正常重新执行原最早查询。未知 COMMIT 先原 receipt GET，同输入仅在协议允许时重复，不盲重试写入；absent 不代表已回滚。
- 原 helper replay 无 commit 与 fresh commit 的差异由实际 source adapter记录；生产原子提交由现 `withDataTransaction` 承担。原 Agent/story bundle 持久化仍独立待迁，不借此迁入 Runtime。

## Optimized Prompt:

You are the primary implementation owner of an independent, initially unregistered Admin default Workspace component. Read the actual Dream get_or_create_default_workspace and dependent actor resolvers, Admin storyWorkspaceWorkspaces schema, locked Drizzle0.45.2 transaction types, principal/decimal DTO, ReceiptRepository and exact identity/unified requirements. Reuse these modules; do not edit launch75 production windows, shared registry/routes/receipt handlers, schema/migrations or registered codecs. Record that Admin Agent.md, docs/rules/README.md and CLAUDE.md are absent in this checkout; use actual AGENTS and relevant Cursor rules. The stale database Cursor note naming app/lib/db/schema.ts conflicts with current AGENTS/user sole packages/db/Drizzle ownership, so preserve canonical schema and perform no DDL.

Implement new closed empty input and workspace_id output without forcing legacy text IDs to UUID. Require active OAuth dream:write and reject all Thread/Run/Editor grant scopes. Keep canonical bigint as decimal string into parameterized typed Drizzle expressions. In a caller-owned Admin UOW serialize actor initialization with a scoped advisory lock, select owned oldest created_at ASC,id ASC without new status filter, otherwise randomUUID insert using centralized original default name and empty settings. Reuse generic request digest/result/audit receipt; validate current ownership and null entity scope before original bounded replay. Never accept caller settings, owner or arbitrary SQL, never commit or create pools in the repository. Provide a current-owner bounded result validator for producer original GET.

Write a test-only source adapter that invokes the actual Python function with fixed positional results, explicitly injected UUID, captured parameters/commit/rollback and bigint-safe transport. Do not copy its algorithm, interpret SQL, connect PostgreSQL or modify business source. Cover fresh/existing/non-UUID/bigint/source exception, strict forbidden fields, OAuth scope/entity/disabled principal and corrupted/deleted/foreign bounded results. Delegate one bounded deterministic/source/type/lint gate to existing Luna; preserve actual first failures and only rerun affected checks. Update affected new headers/folder docs and producer handoff plan; do not advertise capability, change Dream consumers, deploy, migrate normal data, call accounts/Google/models or declare full migration complete. Later registered public concurrency/rollback/receipt checks require primary-owned verified disposable target.

USER REQUIREMENT:
数据库改造成接口遵从 DTO/ORM 设计，并彻底移除 Dream 生产数据库路径，保持原业务行为和可核验权限、事务、幂等结果。

## 验收、证据与风险

候选先经 actual source 等价、成功/失败 unit、type/lint；生产注册后再验公开同 actor 并发单默认项、owner/readonly/entity/非法字段拒绝、同请求 bounded replay、receipt/audit 和故障全 rollback。制定计划时候选尚未实现/注册；下方记录后续候选结果。Dream 调用处和其他 Agent 集成 SQL 仍开放，正常本机真实验收未执行。

设计依据采用 [Drizzle 事务](https://orm.drizzle.team/docs/transactions)、[typed select](https://orm.drizzle.team/docs/select) 与 [PostgreSQL transaction advisory locks](https://www.postgresql.org/docs/18/explicit-locking.html)，并以本机锁定版本源码和实际生成查询为准；只在 Admin 现 UOW 内执行，锁随事务结束释放。主要风险是 legacy text IDs、bigint Number 转换、多个初次请求与删除/owner变更时旧 receipt 的权限恢复。

## 候选实现与首轮真实命令回执

主协调在 Admin729f 新建 DTO、typed Repository、Service、unit/source tests、actual Python source adapter、非secret `workspace-default-policy.ts` 和独立 provider plan；四个受影响目录文档只追加，原所有其他 dirty 文件保留。没有修改共享75 Registry/Route/Receipt/schema/migration 或正常服务，也没有广告 Workspace API。

专用 Luna cwd `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`，实际执行：

```text
INK_DREAM_SOURCE=/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/dream/workspaceDefault.test.ts app/lib/dream/workspaceDefaultSource.test.ts --configLoader runner --cache false --reporter default
exit 0; Test Files 2 passed; Tests 21 passed (unit20/source1)
node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false
exit 0; no diagnostics
node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/dream/workspaceDefaultDto.ts app/lib/dream/workspaceDefaultRepository.ts app/lib/dream/workspaceDefaultService.ts app/lib/dream/workspaceDefault.test.ts app/lib/dream/workspaceDefaultSource.test.ts config/workspace-default-policy.ts
exit 0; no diagnostics
python3 -c 'import ast,pathlib; p=pathlib.Path("tests/integration/workspaceDefaultSourceOracle.py"); ast.parse(p.read_text(),filename=str(p)); print("AST PASS")'
exit 0; AST PASS
git diff --check
exit 0; no output
```

原始回执在 `/private/tmp/ink-workflow-read-validation/workspace-default-first-gate.md`；主协调已读 raw 输出。source1 调用实际原 helper，固定 positional DB results/UUID 捕获 fresh、legacy replay、insert exception 的完整参数与 commit/rollback，canonical actor 大于JS安全整数仍以字符串运输；不执行 SQL、真实 DB、网络、Runtime 或 Provider。没有清理既有 source caches。候选技术 gate 已通过；生产 ingress/原GET/实际注册、隔离public并发和原子事务以及Dream消费仍 pending，不能称完整迁移通过。


## 注册76与独立公开窗口的实际结果

新薄Ingress11/OriginalGET9共20、wholetype/lint/diff0；实际注册76全部旧75 full descriptors、原PF/delegation字节保持。OAuth-only dream:write/空input/legacy text ID，与确切identity/unified requirements保持，没有DDL。新隔离target来自已ownedlaunch75，125表before/after fingerprint完全一致、51534/owner/datadir核验、ACL apply0、没有正常库操作。

严格公开第一次命令exit0，14cases/22GET/347assertions/17protected：三同original+两不同original一起first POST仅一个新Workspace，每distinct一receipt/audit、replay无重复；actual helper完整params/UOW和全新行、legacy最早、同时间ID排序、archived选择、权限/空input/digest/scope/currentowner恢复均验。主任务3选择性INSERTfault与真实finalCOMMIT响应单次丢失合计90断言exit0，全17表rollback或GET200/replay200/fullresult/1Workspace1receipt1audit恢复。SELECT preservation159 exit0，来源125表旧完整行、首次fixture17表与5positive originals全部保留；清理本轮3组trigger/function、activeobjects none。

原fixture准备脚本exit1是局部operation变量scope，发生于公开合同之前；新seed与grant不重建，continuation16setup/17fullcheckpoint exit0，原失败回执不覆盖。三技术结果独立于Dream consumer、Runtime与正常Google/account/model业务，76固定验收窗口已释放，整体goal仍active。见[公开验证计划](stage_admin-default-workspace-public-validation.md)。

- [workspace76-registration-first-gate.md](../exec/admin-auth-data-verification/workspace76-registration-first-gate.md)

- [workspace76-public-command-receipt.json](../exec/admin-auth-data-verification/workspace76-public-command-receipt.json)
