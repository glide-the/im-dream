<!-- [Input] Actual Admin SystemConfig25 candidate and Dream server-owned request/grant/resolution callers. -->
<!-- [Output] Before-code Prompt Architect for a minimal Thread-bound raw-config read candidate. -->
<!-- [Pos] Root-owned unregistered domain; registered77, Runtime and shared wire stay producer-owned. -->
<!-- [Sync] 2026-09-15: plan current owned Thread read with existing UserConfig repository/mandatory codec. -->

# Thread SystemConfig 读取领域

## 背景与问题

原 Dream Settings、workspace、router model resolver 与 ClaudeAgentService 使用 get_system_config 直接读取数据库。用户级 get/patch 已有 unregistered candidate25 门禁；该接口拒绝所有实体委托，不能把它直接当成 Agent 内部的 Thread/Run 配置读取能力。真实调用链已有 AdminRequestActor、immutable AdminWorkflowResolution、server-persistence grant 与 AdminTurnPersistence；service 仍在读取失败后默认 {}，与本次 Admin 不可用明确失败目标冲突。

## 目标与边界

Root拥有新 threadSystemConfigDto/Service/test 与自己 userSystemConfigService 的复用读取函数、此阶段文档和 Admin handoff。复用 ChatThreadRepository.requireOwned（现有当前owner查询；不升级上游grant持有的SHARE锁）与 UserSystemConfigRepository.get、已验纯Python codec；不复制SQL、不新增Repo或配置、不改registered77 Route/Registry/Receipt/fixed map/capability/迁移。Admin producer后续提供薄Handler及真实公开授权；Dream任务把取得的配置变成immutable server-owned snapshot供model/context/Runtime消费，保留effort LKG及最终模型输出配置来源、admission/lease/Runner/SSE/reconnect语义，不在Agent turn查询远程资源策略。

## 概念与规则

候选 thread-system-config.get：read/dream:read，strict {thread_id}→{config_json:string}，不接收用户、Run、editor、codec或path selector。OAuth从subject link得到canonical actor并校验当前Thread；server-persistence的thread必须匹配，现有shared boundary先核验其grant与当前ownedRun（若绑定Run），不把body里的外部ID作为主体。Editor会话或run非空而thread为空的组合在service拒绝。Thread当前owner查询先于UserConfig Repository/codec，Thread缺失/他人404 CHAT_THREAD_NOT_FOUND；不足scope403；非法input400；存储/codec/网络失败明确业务失败，只有无行/NULL/空串由原codec合法返回{}。raw integer/float/-0/Unicode/unknown keys保持原Python表示。

配置读取事务结束后再执行业务；复用已有typed owner查询，不更新Thread字段或新增UPDATE行锁，不持有到Runtime/SSE。UserConfig当前行读取不创建、不更新、不接收外部列名，不添加receipt/audit。业务读取与原配置patch的同row并发由现有PostgreSQL语义提供；不宣称此候选已注册、部署或完成所有caller替换。

## Optimized Prompt:

You are the primary owner of the unregistered Thread SystemConfig read candidate. Existing evidence confirms the user SystemConfig DTO/ORM/pure-codec candidate has25 deterministic passes and that Dream routes/model resolver/service still directly read the column. Read actual AdminRequestActor, immutable workflow resolution, server-persistence grant creation/current identity checks, Agent run request/context assembly and the existing Admin ChatThreadRepository, UserSystemConfigRepository, DTO, service and source oracle. Reuse the proven mandatory Python codec and factor only the Root-owned raw-read helper from the unregistered user service. Add a strict thread-system-config.get read DTO and service that requires current active server-derived identity/dream:read, denies Editor or inconsistent/unmatched entity scopes, calls existing owned Thread permission query before current UserConfig read, and returns the same strict raw config JSON. Never accept user_id/SQL/column/path/Run selector, create defaults on exceptions, query resource policy from Agent turn, or alter Runtime/admission/SSE/lease/FS protocol. Keep registered77 and all shared wire/catalog/codec/migrations unchanged. Update owned handoff/folder headers. Delegate a bounded deterministic domain gate plus affected prior user source/type/lint checks to Luna; record exact command/cwd/exit and real counters, then hand off the unregistered descriptor for later producer registration/public/consumer verification. A passing candidate does not close real accounts, Runtime, no-PG or whole migration.

USER REQUIREMENT:
数据库改造成接口要遵从DTO/ORM，并保留Dream Runtime与Agent业务执行；Thread/Run按当前实体归属消费用户配置，Admin不可用不能回退Dream直连。

## 流程、影响与验收

| 流程 | 判断与模块 | 验收/失败恢复 |
|---|---|---|
| OAuth owned Thread读 | strict DTO→principal→existingThreadRepo→UserConfigRepo→mandatorycodec | 所有原raw字段及canonical bigint decimal主体不转Number；Thread失败不读取配置 |
| server-persistence读 | matchingThread及shared currentRun校验 | 错Thread/Editor/不一致Run scope403、无配置访问 |
| 无配置行 | 原pure codec正常absence | 返回{}是数据状态，读取或codec故障不默认{} |
| 消费者接入（后续） | server-owned immutable snapshot→model/context/Runtime | 默认/资源LKG与selected model配置各保留；断网公开503且不执行Runtime |

候选门禁拟执行 Admin729f `npx vitest run app/lib/dream/threadSystemConfig.test.ts app/lib/dream/userSystemConfig.test.ts app/lib/dream/userSystemConfigSource.test.ts`、whole `npx tsc --noEmit`、owned ESLint、diff及引用验证。实际命令/计数按真实回执更新。公开typed HTTP/当前数据库权限/全行不变/Run委托作用域与Dream全部caller关闭另列pending；不增加数据库结构或新控制服务。

## 当前状态

before-code规划已执行：3个新候选文件与Root自有raw-read复用函数已落盘，先前文件完整备份于 /private/tmp/ink-thread-system-config-own-write-272mgki9；未注册/广告或改shared77。Root已实际读取Luna最终post-review gate：Thread18、cache-free whole tsc/ownedlint/diff均exit0；修正前source1批14与未改User24各有实际通过回执，首次env/type失败保留。候选仍未注册，公开/消费者pending。Failure77独立公开续接窗口继续，Root新文件不改其冻结契约。已有canonical资料：[Admin接口契约](/Users/dmeck/.codex/worktrees/729f/ink-admin-memory/docs/architecture/admin-dream-auth-data-contract.md)、[现有用户配置候选](stage_admin-user-system-config-domain.md)。


## 同轮评审修正与真实候选门禁

首轮实际 Thread18/User24通过，source1因主任务命令未提供mandatory源env在line32退出1；首轮wholetsc2含tsbuildinfo EPERM与test的unknown mock.instances类型。Root以typed Repository this捕获真实canonical actor保留断言；Luna focused correction Thread18+actual whole source1批14合计19通过、cache-free tsc0/ownedlint0/diff0，原失败回执保留。此前User24未改且已通过，不重复无关测试。

评审随后确认server-persistence shared boundary已对ownedThread持有SHARE锁。纯配置读若再复用 requireOwned(thread,true) 升级UPDATE，两份不同grant的并发读取可能互相等待。按[PostgreSQL行锁与死锁文档](https://www.postgresql.org/docs/18/explicit-locking.html)，本候选改为复用 requireOwned(thread)现有currentowner SELECT，保留同UOW先Thread权限再profile读取，上游grant的currentThread/Run锁不变；OAuth当前owner在读取语句检查，其user级配置仍只来自同一canonical subject。不改共享Repository或既有生产写入锁，不新增默认/控制服务。修正前原规划与代码测试完整原文备份于 /private/tmp/ink-thread-config-read-lock-review-95r8v9vb，后续安全归档索引；本文件现行描述已同步，公开并发/当前Run验证仍pending。

上述ordinary-owner-read修正后的Thread18及whole type/lint/diff已实际重新执行并exit0；Root已读raw，不把修正前19冒充本次18门禁。Root新的候选只给producer未来注册，不提前广告SHA或启用Dream旧DB fallback。


## 最终候选回执与handoff

| 命令（cwd Admin729f） | exit | 实际范围 |
|---|---|---|
| npx vitest run app/lib/dream/threadSystemConfig.test.ts | 0 | 最终ordinary owner read的18/18，实际typed canonical bigint actor、OAuth与Thread/Run-bound scope、拒绝selector、owner优先、raw JSON与故障传播 |
| npx tsc --noEmit --incremental false | 0 | whole项目，无compiler diagnostics；避免未授权cache写入 |
| npx eslint app/lib/dream/threadSystemConfigService.ts app/lib/dream/threadSystemConfig.test.ts | 0 | 最终受影响2文件，无lint diagnostics |
| git diff --check | 0 | 无空白错误，不暂存/提交其他任务修改 |

[最终raw回执](/private/tmp/ink-workflow-read-validation/thread-system-config-read-lock-review-gate.md)、[source/env/type focused修正19](/private/tmp/ink-workflow-read-validation/thread-system-config-correction-gate.md)、[原始首轮失败](/private/tmp/ink-workflow-read-validation/thread-system-config-first-gate.md)均保留。Producer后续提供薄Handler共享校验/固定codec DI/API capability，与用户get/patch兼容一起发布；Dream按实际callsite把配置取为immutable snapshot，当前数据库直连清单未关闭。正常账户/Google/model/Admin可见业务以及整个迁移goal继续active。


## 候选读锁复核后的实际门禁

最初实现对 Thread owner SELECT 使用update锁；设计复核依据 PostgreSQL行锁兼容关系，发现并发两个共享delegation grant先持有SHARE再升级UPDATE可能相互等待。候选改为现有 `requireOwned(threadId)` 当前owner普通SELECT，Run/Thread绑定仍由上游同一事务的Delegation/authoritative workflow context校验，配置读取不修改Thread。最终精确 Thread测试18/18、cache-free typecheck0、owned2 ESLint0、diff-check0。此前Thread18+whole source oracle1批14同轮结果与独立User24保留为分开的实际回执；首轮因命令漏传mandatory source env和测试mock类型错误的失败均保留。候选尚未注册，必须等待producer将固定mandatory codec/薄handler/Original GET接入后重跑公开与事务门禁。

- [thread-system-config-read-lock-review-gate.md](../exec/admin-auth-data-verification/thread-system-config-read-lock-review-gate.md)

- [thread-system-config-before-lock-review-plan.md](../exec/admin-auth-data-verification/thread-system-config-before-lock-review-plan.md)
