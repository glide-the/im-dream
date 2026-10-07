<!-- [Input] Dream integration proposal, actual Admin four-operation DTO and public connector projection, existing Dream router/error boundaries. -->
<!-- [Output] Independent implementation gate and required corrections with release limitations. -->
<!-- [Pos] Backend integration review evidence; current product contract remains in Notion PRD and formal design. -->
<!-- [Sync] 2026-10-07: 保留R1–R4首次问题与修复准入；追加Dream83/3/52、Admin consumer6/worker2实际通过，正常发布保持关闭。 -->
# Notion 同步归属 Dream 集成独立评审

评审者：主 Agent；方案作者：`calendar_borderless_review`。依据为[集成方案](./notion-sync-ownership-dream-integration-20261007.md)及本次读取的实际源码。此次只评审后端集成，不复用前端通过结论作为后端门禁，不写正常数据库或启停服务。

## 首轮结论：修改后可实施，精确合同门禁仍未闭合

四个 operation、服务端租约、唯一执行归属、原 receipt、先 Admin 提交后缓存及全部消费者校验接受版本的方向可实施。下列两项必须先修正；Admin 的 DTO/schema/operation artifact 仍在独立验证，不能 pin 猜测值或将登记 capability 视为正常服务已启用。

| 必改项 | 实际依据 | 要求 |
| --- | --- | --- |
| R1：普通只读接口无法取得 execution revisions | Admin `notionConnectorRepository.projectConnector(internal=false)` 明确删除 `snapshot_sync_execution`；四个新写操作的 run 不能代替 Calendar 只读合同 | 本版本 read/today/thread 保留 `updatedAt` 的保守上下文保护。仅当冻结合同确实提供只读、服务器所有的安全 revision 投影时，才可另行评审采用。不得调用 claim 获取 revision，不因 heartbeat 或同步状态豁免并发校验。 |
| R2：busy 的恢复反馈尚无实现边界 | Dream `AdminDataError` 没有 Notion retry DTO；router 对该类型只返回 code；`NotionSnapshotNotReadyError` 的连接/选择提示不适用于活跃同步 | 采用最小 Notion 领域 typed error 和 router 映射，保留现有公开入口；返回明确 busy 409，若提供 Retry-After，按输出的 `retry_at - server_now` 计算，不使用 Dream wall clock 裁决 lease。不扩共享 Admin 错误 DTO 或混入其他领域。 |

缓存身份按实际 Admin repository 的 `last_synced_at = metadata.fetched_at` 关系匹配，版本不透明，文件名使用安全编码。来源、授权、actor、凭证或当前接受 identity 变化必须拒绝提交/投影；损坏文件、路径与 symlink 不得作为旧缓存回退。文档中的假设必须与可见 DTO 和实际测试一致。

## 后续门禁与回执

方案修订及独立复核通过后，只能使用 Admin 已冻结、可复核的精确 artifact 实施代码；缺 capability、claim gate 关闭或 legacy owner 未解决时 fail closed，不回退旧写路径。正常库迁移、旧 writer drain 和启用事实需另有实际发布回执。源代码或隔离测试完成不能替代这些事实。

Luna 的确定性验证须覆盖公开手动同步、保存范围首次同步、后台扫描、健康续租/失效/旧执行迟到、未知提交 receipt、取消、先提交后缓存及 Calendar/facade/thread 全部消费者；保留失败与复测命令/退出码。当前没有此后端实现或验证结论。

## 修订复核：方案可实施，合同与发布状态单独闭合

方案 §4.1/§5/§8 已落实 R1/R2。普通只读 revision 不可用的事实保持明确；所有读者继续校验 updatedAt。busy 使用 Notion 领域错误和服务器时间差，范围保存与首次同步分别按实际结果反馈。原首次评审和修订记录保留。

主 Agent 通过此修订方案的独立设计门禁。生产编码只能在 Admin 精确 artifact 冻结并附实际验证回执后开始；运行时任何新写入必须通过已发布 capability 和服务器 claim gate。当前依赖仍在验证，没有正常库迁移、旧 writer drain、claim 启用或永久中断恢复验收回执，故本复核不代表这些条件完成。

## 编码门禁通过

Admin 任务 revision 30 实际报告公开入口 9/9、发布边界 13/13、2238 项单元测试、typecheck/lint/隔离 build 退出 0，现有 Dream builder 的严格 DTO 兼容检查实际通过。主 Agent 从当前正式合同生成四操作及 DTO/策略的不可变消费副本，保存于 `output/notion-sync-ownership-dream-20261007/admin-artifact/`；provenance 记录文件 SHA256、四操作 digest 与验证观察。后续验证再次比对 Admin 最终交付，差异必须修订并重测，不能依赖全局最新 head。

据此批准按修订方案实施 Dream 源码、测试及文档。schema capability digest 为 `a54b947c69ea0f129d22fd440c3a9f5694026ac0977adef2d5b09a97d7a9e993`。正常库未迁移，claim gate 未启用，旧 writer drain 未证明；新同步运行时必须 fail closed，本文不授权停止用户服务、正常库 DDL、发布启用或 legacy 状态重置。只读旧合同继续兼容。代码完成仍须独立复核及 Luna 完整技术回执。

## 实现首轮复核：R3/R4 待修复和验证

R3：续租等待中取消不能绕过该次服务器策略预算。已派发的同步 HTTP 请求仍须等待原 receipt 的有限返回；清理之后再次检查实际完成时间，超预算、异常或归属失效均不得发出 failed/cancelled finish。Admin 依赖任务在真实生产 Route Handler 的具名隔离 PostgreSQL 中追加取消与超时交叉验证；Dream owner 修复该路径，尚无通过结论。

R4：新增 `_credential_identity` 把 `st_ctime_ns` 纳入比较，但 `NotionCredentialStore.effective_home` 使用的 `_read_private_file` 每次执行 `chmod(0600)`。同一凭证的读取也可能改变 ctime，不能因此判定授权变化。Admin 真实 Dream consumer 首次保存并同步已抛出 `NotionCredentialError`；只读源码确认上述条件，原失败保存在 Admin `output/notion-sync-ownership-20261007/dream-consumer-probe.log`。这是实现缺陷，不能通过模拟恒定身份或修改测试期望掩盖。修复应以实际稳定凭证内容及必要文件身份为依据，继续拒绝真正的凭证替换；摘要与正文均不得进入公开反馈或日志。同步、Calendar、facade 与 Thread 使用同一个身份检查，验证使用真实私密凭证文件。

上述失败不撤销已冻结四项合同的消费许可，但永久恢复的实现及验收仍未通过。修复后须交给 Luna 执行完整消费者旅程，并引用实际退出码和结果；源码与隔离验证不代替正常 capability、旧 writer drain 及服务发布。

## 修复源码复核与验证准入

主 Agent 已只读核对冻结源码：R3 每次 renew 记录 monotonic deadline 和实际 completed_at，正常返回及取消清理后的原请求均检查预算；越界或异常设置失去执行许可，不发终止写。R4 复用有限大小、O_NOFOLLOW 的凭证读取，比较内容与 dev/inode/size/mtime，排除读取自身的 chmod ctime；Calendar、facade、Thread 与同步共同使用该检查。

同时核对固定四操作及严格嵌套 DTO、服务端权限、原 receipt 恢复、先接受后缓存、所有消费者的完整接受 identity、updatedAt 强上下文，以及只在 replace 确认后添加严格 selection_saved 标记。当前方向通过源码复核，允许 Luna 执行新旧后端旅程。额外三条取消交叉路径由独立的 `backend/tests/test_notion_sync_cancellation_edges.py` 覆盖；不以此源码复核宣称这些测试已运行或通过。

## 最终技术验证复核与发布缺口

R3/R4修复后的实际Admin consumer6/6、公开路由及worker2/2均exit0；本仓Luna核心83项加16 subtests、取消边界3项、此前相关Runtime/服务52项加5 subtests均exit0。核心首轮实际81通过/2失败的服务Bearer断言缺陷，以及三例首轮导入前置失败，均保留并按实际合同纠正；生产认证没有降低。扩展compileall、固定artifact10/10、作用域文档检查、历史身份及diff检查通过，Notion正式稿4图实际parse/render通过，Calendar3图与原实际回执SHA一致。完整命令/退出码见[实施记录§12–13](./notion-sync-ownership-dream-integration-20261007.md#13-本仓后端实际复测与范围)及其指定原日志；Ruff工具不可用的exit127保持明确，不称lint通过。

据此，已评审源码及隔离技术旅程通过。本机正常Admin目录仍缺四operation与精确schema；claims开关、旧writer/ingress drain及正常Dream/Admin服务切换没有实际发布回执。旧正常账户今日文档曾经恢复不代表新归属机制已上线。整体目标及正常发布继续未完成，本结论不授权正常数据库DDL、遗留状态强制重置或停止用户服务。

后续Calendar正式稿已同步实际归属与接受缓存流程并保存完整变更前历史。当前总四图已实际parse/render通过，作用域122引用和历史身份/diff检查通过，详见[当前文档回执](./notion-calendar-sync-refresh-20261007.md#153-新正文最终实际文档门禁)；上文旧三图身份回执只属于原正文阶段，不作为当前四图验收。后端源码及精确artifact未变，无需因此重复功能回归；正常发布仍未完成。
