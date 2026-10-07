<!-- [Input] 正常连接停留syncing的回执、现行Notion合同及Admin/Dream源码中的锁、DTO、receipt和snapshot发布路径。 -->
<!-- [Output] 保留最小Admin依赖合同建议，并索引后续实际实施、验证与正常发布缺口。 -->
<!-- [Pos] 初稿历史与依赖索引；最终精确合同和实际回执由后续正式文档所有。 -->
<!-- [Sync] 2026-10-07: 已创建Admin依赖并完成隔离实现/联调，正常发布未完成；保留以下首次草案全文及当时状态。 -->
<!-- [Sync] 2026-10-07: 只读分析后提出4个operation与必要发布边界；未写生产/数据库、未创建跨项目任务。 -->
# Notion自动同步执行归属：最小Admin依赖草案

**当前索引：** 以下正文保留首次草案的建议及当时“未实现/未创建任务”状态，不作为当前能力证明。实际依赖任务为 `01a11331-2830-7220-bf91-4a144acfd62f`，本仓精确artifact、Dream接入及实际技术结果见[实施记录](./notion-sync-ownership-dream-integration-20261007.md)与[独立评审](./notion-sync-ownership-dream-integration-review-20261007.md)。Admin已完成受控前向migration/合同实现、公开入口9项、发布边界13项及实际Dream consumer6项/worker2项隔离验证；正常Admin仍未发布四操作及schema，旧writer drain、claims启用和正常服务切换没有回执。仅隔离通过，不宣称已上线或整体目标完成。

## 1. 问题、目标与边界

正常公开读取发现某已授权、选择7个数据库、自动15分钟的连接从2026-10-06T07:33:11Z持续显示`syncing`；最近成功07:17:09Z、下次计划07:32:09Z。这是诊断输入，不把等待时长当作“已停止”的证明，不在产品中设任意过期阈值。

Dream `notion/sync_policy.py::sync_policy_is_due`把持久化`syncing`永久排除；`factory.py::sync`仅有进程内`_SYNC_LOCKS`，不具备跨进程执行归属。Admin `notionConnectorRepository.patch/saveSnapshot`虽分别锁connector行，但锁不跨远程扫描，现有DTO没有run条件提交。取消后的失败状态回写也可能失败。目标是让未完成执行可依据**Admin数据库时钟、明确租约和当前执行ID**恢复，旧执行不能覆盖新snapshot/状态；有效执行不被抢占。

本草案只扩现有Notion持久化合同，不新增队列、Webhook、通用调度框架、活动历史库、正文同步或Notion写入。Dream不读共享数据库、不做DDL。Admin项目：`/Users/dmeck/project/ink-admin-memory`；源码最终合同、capability版本/hash和是否需要物理migration由其实施任务交付，以下名称均为**建议、未实现**。

## 2. 复用与最小新增

复用Admin `app/lib/dream/notionConnector{Dto,Service,Repository,Handler}.ts`、`operationRegistry.ts`、`ReceiptRepository`、`withDataTransaction`及既有`connectors:sync`后台权限；Dream沿用`AdminNotionConnectorData`、facade、builder和公开同步入口。

Admin已有`chatScheduledTaskService.ts::claimOne/renewOne`使用数据库时钟、执行ID及租约条件，可复用这种校验方式和配置组织。其`scheduled-trigger.*`绑定TaskSession、模型执行及`schedule:execute`，不能直接拿来承载Notion同步，不复制Chat状态机/表。

最少新增**4个operation**；手动与定时claim共用一个私有事务函数，但分别使用现有user/background ingress，避免扩大浏览器权限。

| 建议operation | 权限/输入 | 输出及事务效果 |
| --- | --- | --- |
| `notion.sync-run.request` | user `dream:write` +已验证Dream service；现有`authority`、`connector_id`、服务端生成`worker_id` | 手动首次/立即同步；事务内校验actor归属、有效授权及非空选择，可忽略自动开关/未到计划。返回`claimed`或`busy`及完整当前connector；不取消有效run。 |
| `notion.sync-run.claim` | background `connectors:sync`；`connector_id`、服务端`worker_id` | 定时claim；事务内再检查有效授权/选择、当前effective策略及due，返回`claimed`、`busy`或`not_due`。候选列表仅用于发现，不能作为提交时判断。 |
| `notion.sync-run.renew` | background `connectors:sync`；`connector_id/run_id/fence_epoch/worker_id` | 当前service/worker/run、上下文及有效租约匹配才延长租约；返回新的`lease_expires_at`和服务器clock/policy。旧run/过期run不续租、不改状态。 |
| `notion.sync-run.finish` | background `connectors:sync`；同一归属键，`outcome`严格联合DTO | `succeeded`含现有snapshot、synced_resources；`failed/cancelled`仅含安全error_code。成功时同一事务校验归属/上下文、调用原saveSnapshot内核、更新current identity/成功时间/资源状态并结束run；失败/取消保留LKG，只结束匹配run并记录安全失败状态。 |

不允许在finish前单独调用旧snapshot.save，再另一步写succeeded。manual request由现有公开`POST /api/connectors/{id}/sync`及保存范围的首次同步内部使用；浏览器不提供worker/run/fence/租约参数。manual取得的run同样绑定签发的Dream service，后续renew/finish可走同一后台合同；Admin不得接受其他service接管此run。actor始终由Admin认证主体/已存connector求得，不接受caller-selected user_id。

## 3. 归属记录、配置与claim规则

优先复用connector已有`config_json`中的Admin保留对象（建议`snapshot_sync_execution`），并通过connector行锁读写；不默认新增表。对象仅保存当前执行/最近安全结果，不演化为历史活动库。最少字段：

- `run_id`：Admin新生成UUID，每次claim唯一；`fence_epoch`：Admin递增正安全整数，不回滚/复用，溢出fail closed；
- `service_client_id`、`worker_id`：已验证service与本次服务器进程身份；
- `owner_user_id`、`selection_revision`、`authorization_revision`：claim时的actor/选择/有效授权上下文；
- `policy_revision`：claim时策略版本，供诊断；finish写当前策略，不把旧policy整块覆盖回去；
- `started_at`、`heartbeat_at`、`lease_expires_at`、当前run结束标识和安全error_code。

selection/authorization revision必须由Admin在原`resources.replace/delete`、有效授权提升/撤销、影响读取范围的更新中单调推进。当前`current_source_revision`是snapshot的上游内容revision，**不能冒充选择revision**；简单比较集合hash也不能识别A→B→A。相同内容的幂等receipt重放不重复推进revision。Dream另外保存有效凭证文件身份，在远程读取前后检查，变化时拒绝提交；Admin不接收凭证或文件路径。

租约长度及建议heartbeat间隔来自Admin服务器所有配置，复用现有`config/chat-scheduled-task-policy`的配置组织，严格校验合法正值、heartbeat小于lease并留出续租延迟预算。配置值是进程恢复的技术合同，不是产品同步频率或“多久就算失败”；不得来自浏览器、部署环境名称或Dream自行猜测。用Admin数据库clock判断过期，不用Dream wall clock授权接管。

claim在同一connector行锁事务内：

1. 校验service/actor、授权、非空来源和当前上下文；scheduled再判断effective启用/due，manual按正常用户意图执行。
2. 当前run未结束且租约有效：返回busy，只读结果，不覆盖、不取消、不开始第二次远程扫描。公开manual入口映射为可识别的`NOTION_SYNC_BUSY`及服务器计算的重试时间，不返回`synced:true`或伪造同步失败；私有run归属字段不展示给浏览器。
3. 当前run已结束/不存在，或租约已由数据库clock证明失效：分配新run与更高fence、租约和上下文；推进last_attempt与syncing，保留成功snapshot。
4. 旧run随后renew/finish必须409拒绝，不能更新新run的lease、snapshot、last-success或错误状态。lease失效只撤销提交资格，不向另一进程发送kill/restart。

`status=syncing`是当前run的展示状态，不再是永久mutex。scheduled遇error且到计划可重新claim；自动关闭不阻止manual请求，但不能被旧run完成时重新打开。策略保存的revision改变不必丢弃同一授权/选择的正常索引结果；finish必须基于**当时最新策略**计算applied/disabled/next-sync，不覆盖desired/effective/revision。actor、授权、来源改变则renew/finish fail closed；当前上下文已结束该run时，旧run连失败状态也不能写回。

## 4. 条件提交、receipt与本地缓存

每个write使用现有request UUID/receipt；未知结果先查原request receipt，不重新生成claim或重复finish。receipt重放可以返回已提交结果，但不延长租约、重新发布snapshot或改新run。一次成功finish仅接受匹配connector/workspace的轻量metadata，`pages={}`；数据库page关系仍经过原DTO/schema检查。

成功finish的事务必须同时检查：run/fence/worker/service匹配、数据库clock租约有效、actor仍有效且归属不变、授权有效且revision未变、selection revision未变。全部成立才写snapshot与current identity及同步结果；失败任一条件回滚整个事务。安全错误建议：`NOTION_SYNC_RUN_INVALID`、`NOTION_SYNC_LEASE_EXPIRED`、`NOTION_SYNC_CONTEXT_CHANGED`、`NOTION_SYNC_CAPABILITY_UNAVAILABLE`，精确注册由Admin交付。

**必须同步修正Dream发布顺序。** 当前`factory.sync`先覆盖本地`current.json`再Admin save，Admin拒绝不能撤销这次本地覆盖；仅增加Admin fencing不够。建议：先原子finish取得已接受的identity，再缓存该版本；读取本地索引必须与Admin返回的`current_snapshot_version`匹配，不匹配时使用已有Admin `notion.snapshot.current/get`取得已接受版本。缓存采用版本隔离写入，不能让旧run迟到覆盖新current后被直接读取。Calendar及其他LKG消费者保持当前选择求交，不为修复扩大正文权限。

Dream收到明确renew失效应停止本轮远程调用/丢弃结果，且不得再以旧run写failed；网络/receipt不确定期间也不得提交。只取消本轮自建CLI请求，不停止用户服务或其他run。成功/失败/取消保持原业务入口和公开反馈，不新增浏览器长轮询协议或正文缓存。

## 5. 发布与legacy边界

建议独立capability `dream.notion-sync-ownership.v1`，由Admin发布严格schema/operation版本/hash与前向Drizzle capability登记。若JSON和现有行锁足以满足合同，仅登记合同和必要JSON迁移；若确需表/字段，则只在Admin Drizzle expand migration实施。Dream必须锁定实际发布的精确capability/hash，不能依赖最新head或自行补建。

推荐expand → Dream支持新合同/receipt和缓存identity检查 → 验证旧同步writer已结束 → connector逐步启用ownership enforcement → 验证后contract。新合同启用后，旧`notion.snapshot.save`、`notion.sync-snapshot.save`和generic config/identity patch不得绕过归属写同步结果；Admin保留对象禁止外部config_patch覆盖，旧receipt只可重放已提交结果。旧读接口和connector JSON DTO继续兼容。

缺capability时，新自动恢复不得回退到无fence同步；允许读取已授权LKG并反馈所需能力。迁移时只有`syncing`、没有run/lease的legacy状态不能按age当作expired，也不能据某进程没有本地锁推断全局空闲。须由发布过程证明旧writer已结束；无法证明时保持LKG并返回`NOTION_SYNC_LEGACY_OWNER_UNRESOLVED`，不抢占活跃执行。当前已确认本机旧进程结束的单次公开manual恢复，与跨进程永久合同交付分开记录。

## 6. Admin与Dream必要回执

| 旅程 | 必须证明 |
| --- | --- |
| 并发claim | 两个service worker同时请求仅一个claimed；另一个busy且未远程扫描；active lease不被manual抢占。 |
| 崩溃与接管 | 受控DB clock使lease失效，新run fence推进；旧run续租、成功/失败/取消提交全部拒绝；新run只提交一次。 |
| 上下文与策略 | actor/授权/来源变更含A→B→A使旧runfail closed；policy保存不被旧finish回滚，自动关闭仍允许manual。 |
| LKG与原子性 | Admin、Notion、续租失败/取消保留已接受snapshot；snapshot+current identity+状态同事务，失败无部分推进；未知结果由原receipt确认。 |
| 缓存乱序 | A旧run在B成功后迟到发布本地索引，所有消费者仍读取Admin已接受版本；不存在只靠Admin fencing却泄漏旧current.json的路径。 |
| 原完整连接器流程 | 选择数据库→page分页索引→背景更新发现新page→Calendar刷新命中；禁用/立即同步/失败恢复、原权限与metadata-only范围保持。 |
| 兼容发布 | capability缺失fail closed、legacy writer未结束不接管、启用后旧写入口无法绕过；精确capability/contract hash、必要migration和cleanup实际回执。 |

持久化并发/故障注入使用明确命名隔离PostgreSQL，schema和迁移由Admin管理；正常用户恢复仅走本机公开入口，记录按真实业务协议保留。不能以mock claim或单条API成功替代上述完整旅程。

本草案由分析者提出，尚未独立评审，不自行宣称批准。主任务据此创建并跟踪明确Admin依赖；Calendar的反馈/文案增量可独立评审，不能以UI修正宣称永久自动恢复完成。
