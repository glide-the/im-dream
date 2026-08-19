> [Sync] 2026-07-20: 初版 — 依据 `claude-task-tools-source-analysis.md`（Claude Code 还原源码分析）与 `claude-plan.md` 既有范式；仅设计契约，业务代码实现见 §7/§8。
> [Sync] 2026-07-20: §7 全部实现项已落地（后端 + 前端 + 测试 + 契约/策略文档登记）。验证：后端 todo 26 tests + plan 23 tests + runner 71 tests 全绿，前端 `npm run build` exit 0。
> [Sync] 2026-07-20: §5.6 按钮形态修订 — PlanButton 去除常驻文字，仅显示 `IconList` 列表图标（Icons.tsx 新增），「计划与待办」文字改为悬浮 tooltip（hover 且弹层未打开时显示，`aria-label` 保留语义）；`IconPlanTasks` 保留于弹层徽标处。
> [Sync] 2026-07-20: §5.6 弹层样式修订（参照进度卡片样式图）— 弹层改为「计划」「待办」双卡片堆叠；待办区改为圆点状态图标（completed 实心+白勾+删除线 / in_progress 描边+中心点 / pending 空心圆）替代 #id 与文字徽章，默认展示前 3 条、超出经「展开 N 个 / 收起」折叠控制。

# claude-todo 设计：任务清单捕获与展示契约

> 本文件路径为兼容既有文档引用而保留。计划、待办和执行流水不再作为业务设计维护。

当前业务需求与已实现结果请从 [业务设计目录](../.folder.md) 按模块查阅。
