<!-- [Input] 用户活动入口和筛选参考图、优化提示词与当前生产接口。 -->
<!-- [Output] 四阶段设计过程的输入、输出、状态与现行产品文档导航。 -->
<!-- [Pos] 活动视图 html-design-workflow 过程索引；不替代现行 PRD 或正式交互设计稿。 -->
<!-- [Sync] 2026-10-07: version design conclusions and prompts; keep reference screenshots containing conversation excerpts local only. -->
<!-- [Sync] 2026-10-07: All four design stages saved; implementable independent review and source implementation and passed focused and final full-workspace type results recorded with historical failures. -->

# 活动视图设计过程 · 2026-10-07

现行产品规则与页面骨架由[Chat 活动视图 PRD](../../../prd/chat/priority-activity.md)所有。[正式设计稿](../priority-activity-sidebar.md)位于上级目录，直接交付业务时序、异常恢复和状态图。技能阶段文件保留过程证据。

| 阶段 | 产物 | 状态 |
| --- | --- | --- |
| 输入 | [优化提示词](inputs/topic.txt)；本地参考图 `inputs/target_image.png`、`inputs/priority_filter.png` | 截图含对话片段，按根维护合同保留本地且不纳入 Git；布局与筛选结论已写入 PRD 和设计稿。 |
| Stage 1 | [产品需求草案](workspace/1_prd_draft.md) | 已生成，仅文档；接口限制与正文骨架归现行 PRD。 |
| Stage 2 | [结构草图](workspace/2_structure_sketch.md) | 已生成；完整骨架直接写入 PRD 正文。 |
| Stage 3 | [层级与逻辑](workspace/3_hierarchy_logic.md) | 已生成；正式稿直接包含正常、异常恢复和两幅状态图。 |
| Stage 4 | [视觉与实现映射](workspace/4_ui_design.md) | 已生成视觉规格并实现最小源代码；12项focused及最终全仓类型技术检查通过，历史失败见回执。 |
| 独立评审 | [评审回执](../../../exec/priority-activity-design-review-20261007.md) | 已明确可实施，D1 已闭合。 |
| 实施 | [实施回执](../../../exec/priority-activity-implementation-20261007.md) | 源代码与技术回执已写入；未执行真实业务验收。 |

执行技能为仓库 `.agents/skills/html_design_skill/SKILL.md`；不采用技能示例中的无关业务背景或新增字体、图标、CSS 框架。每次制定或变更阶段计划前，在阶段文件记录一次当次 Optimized Prompt，不逐轮朗读。
