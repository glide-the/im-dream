<!-- [Input] topic.txt, target_image.png, priority_filter.png and current public source contracts. -->
<!-- [Output] Stage 1 optimized execution prompt, screenshot analysis, current PRD pointer and capability findings. -->
<!-- [Pos] html-design-workflow Stage 1 process evidence; docs/prd/chat/priority-activity.md owns product rules and page skeletons. -->
<!-- [Sync] 2026-10-07: Stage 1 document-only draft completed; later design review and feature validation pending. -->

# Stage 1：活动视图产品需求草案

## Optimized Prompt:

你是 Ink & Memory 活动视图的产品需求设计师。基于 workflow/inputs/topic.txt 和两张参考图，先只读核对当前 ChatView、chatHistoryApi、scheduledTaskApi、useStoryWorkspaceDreamRuns、Dream reentry DTO、Dream 公开路由和本机 Admin scheduled-task.day 的真实行为，再生成可评审的中文产品需求草案。明确直接铃铛入口、右侧互斥面板、优先级与按日期历史、今日定时任务范围、Chat updated_at 与 Dream lastActivityAt 的五分钟窗口、运行状态证据、来源内去重、分类显示、原导航、独立加载错误及恢复、响应式与可访问性。现行 PRD 归属 docs/prd/chat/priority-activity.md，正文直接包含背景与问题、目标与边界、概念与规则、页面模块表、桌面和窄屏骨架、验收与需求追踪矩阵。既有接口没有全局任务、跨 Chat 运行或普通正文预览时如实写明范围；只提最小公开投影建议并标为建议、未实现，不画成已交付功能。不改变发送、任务控制、Runtime 或数据库 Schema，不从截图照搬置顶、归档、标记已读，不新增依赖。所有权限于委派的 PRD、Stage 1 文件和目录清单；保留已有用户、其他 Agent 改动与历史。供后续三个设计阶段及独立评审继续，禁止编写功能代码或宣称真实业务验收。

## 本阶段执行与来源

1. 阅读仓库合同、Stage 1 参考提示和截图，区分用户指令与截图中的界面文字。
2. 核对公开来源的时间、状态、日期范围、分页、导航和已存在的错误语义。
3. 写入现行 PRD 与目录清单；当前草案等待后续设计阶段扩充与独立评审。

## 截图布局解读

| 区域 | 观察 | 本次映射 |
| --- | --- | --- |
| 顶部铃铛 | 深色背景上的轮廓铃铛，选中时为圆角深色按钮；红框是标注 | Chat 新建旁的活动入口，使用现有主题与图标。 |
| 优先级 | 日期组之前显示标题、省略号菜单和活动行 | 只读汇集今日任务与最近五分钟 Chat/Dream。 |
| 日期历史 | 今天、昨天等段落，行有标题和说明 | 复用现有历史日期分组和分页，不补普通正文接口。 |
| 显示菜单 | 独立圆角纸面，选项右侧勾选 | 仅优先级部分、定时任务、Chat、Dream。 |
| 额外管理行 | 置顶、归档、全部标已读 | 不在本次范围，不增加相应接口或按钮。 |

## 当前 PRD

[现行产品需求及正文骨架](../../../../prd/chat/priority-activity.md)。后续 Stage 2 可直接扩充其正文骨架，Stage 3 正式设计稿拟创建于上级目录 `priority-activity-sidebar.md`；创建前不作为已交付链接。

## 核对结果与限制

- `getScheduledDay(localDate, displayTimeZone)` 返回日期匹配的 definitions 和 triggers；scheduled 用 scheduled_at，manual 用 created_at。当天 definitions 不按状态过滤；昨日仍运行触发与未来 once 不在响应中，因此范围命名为今日定时任务。
- Admin `chatThreadRepository.ts` 的列表按 updated_at 降序；updated_at 同时由消息、标题、Deck/Voice/SDK session 更改推进。ChatHistoryThread 没有跨 Thread running 和普通正文预览。
- Dream lastActivityAt 为服务器的 Run 创建、Thread 更新、阶段活动最大时间。generating/running 是阶段投影，不能替代实时 Runtime 运行观察。原重入视图顺序继续服务端所有；活动视图只派生展示排序。
- Admin 列表已核实按 updated_at 降序。Chat 用同一 listChatThreads limit/offset 顺序读取，直到首个早于窗口的有效记录或空响应，不设固定最多页数；日期历史分页独立保留。Dream recent 项仍由服务器限量。使用现有实体 ID 做来源内去重，没有 DTO 关联证据时不跨来源合并。
- ChatView 的 fetchThreads 当前把错误转为空数组；本次活动读取边界必须保留失败状态。失败不能报告为无活动。
- 旧 Chat Sidebar PRD 的更多入口与右侧宽度合同需由后续阶段保存完整旧稿历史后同步。当前 PlanButton 职责不变。

## 近期集合计划修正的 Optimized Prompt:

已确认 Admin chatThreadRepository.list 按 updated_at DESC 返回。只修正最近 Chat 读取方案：复用同一 listChatThreads limit/offset 顺序扫描五分钟集合，遇到首个早于窗口的有效记录或空响应即停止，不增加固定最多页数、不扫描全历史、不改变日期历史分页。不在用户界面暴露分页实现说明。保留其他已确认范围、授权与设计约束，同步 PRD 的规则、接口限制和验收矩阵。

## 交付状态

本阶段仅完成文档草案，不包含功能代码、完整业务时序或独立评审结论。Markdown inventory、引用路径和 diff 检查由本阶段执行并在完成回执报告；真实业务测试不在本阶段。
