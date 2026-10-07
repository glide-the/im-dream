<!-- [Input] 现行活动 PRD、正式交互设计、Stage 2/3 及当前公开读取和导航源码。 -->
<!-- [Output] 独立设计评审结论、逐项证据、实施边界及文档验证回执。 -->
<!-- [Pos] 活动视图功能代码之前的独立设计门禁；不代表实现或真实业务验收。 -->
<!-- [Sync] 2026-10-07: independent design review is implementable after the normal-sequence network-owner correction; implementation and real-business acceptance remain pending. -->

# 活动视图独立设计评审 · 2026-10-07

## Optimized Prompt:

你是 Ink & Memory 的独立产品与交互设计评审者。在本轮评审计划之前记录此优化提示词。只读审阅现行 docs/prd/chat/priority-activity.md、docs/design/claude-agent/priority-activity-sidebar.md、Stage 2/3 和当前 ChatView、历史、定时任务、Dream 公开读取的真实源码边界。逐项判断：新建旁铃铛打开同一个右侧历史面板；优先级符合今日定时任务与最近五分钟 Chat/Dream 的目标；任务 running 与 Dream 业务阶段标签有真实字段证据；Chat 使用更新时间降序的公开分页直到窗口之外或空响应，正确处理未来/无效时间、重复 ID 和独立历史 offset；保留既有用户主动删除，活动打开、刷新、筛选、导航不自动写入；搜索与原导航复用，孤立触发不伪造定义快照；来源失败、旧状态、乱序响应及跨日恢复不会虚报当前状态；宽窄屏焦点、浮层、唯一列表滚动和正文图示与矩阵一致。只评审最小必要方案，不新增需求、控制通道、数据库、通知系统、管理操作或静态原型。当前源码尚未实现的差距应列为实施要求，不冒充设计阻塞或已完成能力。记录明确“可实施”或具体阻塞、逐项结论和关键风险。只新增本评审回执及 docs/exec/.folder.md 对应条目，保留用户和其他 Agent 改动，不改功能代码或无关文档。Mermaid 解析由 Stage 3 作者收尾，本轮不重复浏览器测试，不声称功能或真实业务验收。

## 结论

**可实施。** 现行产品范围、接口证据、正常／异常恢复和页面／来源状态合同一致；唯一正常时序职责问题已在当前正式稿实际修正并由本评审复核，其他项没有设计阻塞。批准的是本稿所列最小活动面板方案，Stage 4 可以在该合同内完成视觉规格后实施。当前生产组件仍需按方案修改，此结论不代表代码、浏览器功能或真实业务验收已完成。

## 评审范围与依据

已核对以下现行文档与公开源码，未修改功能代码、其他现行设计稿或用户服务：

- [现行 PRD 与桌面／窄屏骨架](../prd/chat/priority-activity.md)。
- [正式交互设计与四幅正文业务图](../design/claude-agent/priority-activity-sidebar.md)。
- [Stage 2 页面草图](../design/claude-agent/priority-activity-workflow-20261007/workspace/2_structure_sketch.md)和[Stage 3 层级映射](../design/claude-agent/priority-activity-workflow-20261007/workspace/3_hierarchy_logic.md)。
- [ChatView 当前历史、删除、侧栏与导航](../../frontend/app/_dream/components/chat/ChatView.tsx)、[历史公开读取](../../frontend/app/_dream/api/chatHistoryApi.ts)、[定时任务公开读取](../../frontend/app/_dream/api/scheduledTaskApi.ts)、[可空快照详情](../../frontend/app/_dream/components/chat/ScheduledTaskDetailSidebar.tsx)。
- [Dream 重入读取](../../frontend/app/_dream/hooks/story-workspace/useStoryWorkspaceDreamRuns.ts)、[重入 DTO](../../frontend/app/_dream/hooks/story-workspace/contracts.ts)、[Dream 服务端阶段投影](../../backend/services/story_workspace/dream_reentry_service.py)和[现有移动端判定](../../frontend/app/_dream/utils/mobileDetect.ts)。
- Admin 只读源码：`/Users/dmeck/project/ink-admin-memory/app/lib/dream/chatThreadRepository.ts` 的 `list` 使用 `thread.updated_at DESC` 与 limit/offset；`chatScheduledTaskService.ts` 的 `scheduled-task.day` 按日期范围返回 definitions/triggers。

评审覆盖产品与交互规则、模块职责和实现可行性。四幅 Mermaid 的语法解析由 Stage 3 作者执行并单独报告；本轮未重复解析或启动浏览器测试。

## 逐项结论

| 检查项 | 结论 | 依据与实施约束 |
| --- | --- | --- |
| 直接铃铛与同一历史面板 | 通过 | 有无 Thread 都能打开；更多中的历史入口指向相同 threadSidebarOpen，不增加第二个历史栏。当前源码尚无铃铛，这属于批准方案的实施差距。 |
| 三来源优先级目标 | 通过 | 今日任务＋最近五分钟 Chat updated_at／Dream lastActivityAt，统一展示层排序；不会更改 Dream 原集合、顺序或服务端 sortKey。 |
| 日期与运行状态证据 | 通过 | 今日范围明确在产品文字；Admin day 不提供昨日持续运行或未来一次性定义。只有 trigger.running 标记任务运行中；Dream 生成中／进行中是业务阶段，Chat 不猜全局 running。 |
| 五分钟窗口与完整近期扫描 | 通过 | 使用已实现的 descending listChatThreads，原始响应条数推进 offset，遇到早于窗口的有效记录或空响应才停止，无固定最多页数。未来和无效时间不纳入且不是提前停止证据。五分钟恰好纳入、超过移出，跨日连续计算。 |
| 去重、排序和历史分页 | 通过 | 按来源和实体 ID 去重；task_id 合并触发；只从历史展示数组排除已显示的优先级 Chat，底层历史 offset 和 hasMore 独立。相同标题或 Deck 不作为跨来源关联。 |
| 原主动删除保留 | 通过 | 原 handleDeleteThread 及公开删除权限链保留；按钮阻止行导航，成功后从历史与近期集合移除相同 ID，失败不移除。打开／刷新／筛选／导航不自动写入，用户主动按原删除按钮不属于新增管理行为。 |
| 搜索与正常导航 | 通过 | 复用原搜索内联弹窗、handleSelectThread、openDreamRun 和 canonical href；修饰键 Dream 链接保持浏览器行为；主 Chat 草稿、附件、发送及停止语义不变。 |
| 孤立触发与任务详情 | 通过 | 现有 ScheduledTaskDetailSidebar 已允许 snapshot 缺省或 null。定义存在才转换快照；孤立触发只传 taskId，不伪造 rule、revision 或定义状态。ChatView 内部 state 的 snapshot 必填需最小放宽。 |
| 独立来源失败与旧状态 | 通过 | 首次、扫描途中、更新失败分别提供来源重试；已有行受当前窗口过滤，旧运行／阶段状态退出当前运行优先层并显示上次状态；任务跨日不复用昨日为今日，错误不能形成整体成功空。 |
| 请求并发与刷新停止 | 通过 | 当前 API 具备可行的序号保护；不支持 Signal 的 Chat／任务请求丢弃旧响应，不能假称网络已取消。支持 Signal 的 Dream 读取可取消；停止的是活动新增刷新，不能改变原 Dream hook 或消息恢复生命周期。 |
| 桌面／窄屏／焦点与滚动 | 通过 | 复用20rem右侧布局与原 useMobile；固定标题、唯一内容滚动区、浮层不裁剪。窄屏隔离背景与管理焦点，菜单和搜索先关闭，关闭抽屉归还铃铛；原焦点工具可满足方案，不需额外导航状态机。 |
| 正文图示与矩阵 | 通过，原问题已闭合 | PRD 正文直接包含桌面／390px／菜单／错误骨架，正式稿正文有正常、异常恢复及页面／来源状态四图，R1–R8 对应一致。原正常图的纯转换职责问题已修正，当前图由 ChatViewContent 负责网络调用，见下表。 |
| 历史与目录合同 | 通过 | 当前 Sidebar 和 Dashboard 已引用新合同；原 Sidebar 完整稿单独保存。同名产品文档 HistorySearchDialog 被明确说明为当前 ChatView 内联弹窗，不要求为文档名拆新组件。 |
| 最小范围与过度设计 | 通过 | 一个面板外壳、一个展示模型及现有入口协调即可实现。不新增后台聚合、共享 Schema、运行控制、通知／已读存储、管理动作、字体图标依赖或静态原型。 |

## 唯一图文修正与门禁

| 编号 | 问题 | 最小修正 | 状态 |
| --- | --- | --- | --- |
| D1 | 正式稿将 activitySidebarModel 定义为纯转换，正常时序图却由 M 直接调用 listChatThreads 执行近期网络扫描。 | 近期 loop 的网络调用 owner 改为 ChatViewContent 的读取协调；M 只接收批次做时间筛选、ID 去重和展示派生，不新增模块。 | 已闭合：当前磁盘正常图为 V→C 网络循环，V→M 传批次／统一 now／已收集 ID；M 返回筛选、去重及停止条件。Stage 3 说明已同步。 |

D1 在本评审收口前已实际修正并复核，图文职责一致。此修正只对齐已经批准的职责，不扩展需求，也不需要改生产入口或数据库。最终结论为可实施。

## 实施时必须保留的风险与验收

1. 公开 offset 分页没有原子快照保证；扫描期间 Thread 更新可能改变批次位置，现行设计已说明通过下一次正常刷新重新扫描，不为此改游标合同。验证应证明多页窗口纳入和重复 ID 保护。
2. ChatView.fetchThreads 当前吞掉读取错误。实施必须只在本次相关列表边界保留来源及分页失败，不能把接口异常变成“没有活动”或“全部已显示”。
3. 双侧栏互斥、近期／历史删除同步、旧状态退出运行优先层、跨日任务与晚到响应、窄屏背景焦点及搜索叠层需要实际技术验证；文档规则不是通过证据。
4. 今日任务、Chat 非消息更新时间、Dream 阶段／recent 集合限制是已确认边界，最终交付仍须说明，不能将界面称为全局实时任务监控。

Stage 4 可以在上述产品合同内细化视觉。任何改变日期范围、状态证据、窗口、读取主路径或原能力的方案需要重新核对受影响项；单纯按现有规格补尺寸、主题和文字不重复创造业务门禁。

## 验证回执

本轮只做源码和文档核对，没有功能、模型或真实业务测试回执。

| 命令或证据来源 | 退出码 | 关键结果与范围 |
| --- | --- | --- |
| `python3` 内联文档检查（本评审执行，校验相对链接、代码围栏、尾部空白、R1–R8、四图数量和 D1 调用所有权） | 0 | `PASS markdown_files=6 local_links=23 trace_rows=8 formal_diagram_blocks=4 D1=closed`；本回执已经登记到 exec 清单。 |
| `git diff --check -- docs/exec/.folder.md docs/exec/priority-activity-design-review-20261007.md` | 0 | 无输出。未跟踪的新回执另外由上方文档检查确认尾部空白和围栏。 |
| Stage 3 作者的四图 parse/render 回执，本评审只读取其已记录结果 | 0（作者回执） | Stage 3 记录 `mermaid_blocks=4 failures=0`，随后仅正常图复核为 `network_owner=ChatViewContent model_network_calls=0`；本评审未重复启动浏览器或解析测试。 |

当前本机用户服务、数据库、进程和端口未由本评审修改。功能实施和相关技术验证均由后续任务执行，不能将本次“可实施”写成“功能已验收”。
