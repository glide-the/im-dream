> [Sync] 2026-07-20: 初版 — 依据 `claude-plan-mode-analysis.md`（Claude Code 还原源码分析）与现有 claude-agent 交互契约设计；仅设计契约，业务代码实现见 §7/§8。
> [Sync] 2026-07-20: §7 全部实现项已落地（后端 + 前端 + 测试 + 契约/策略文档登记）。实现偏差记录：① 防抖为 leading-edge throttle（立即发射、窗口内抑制重复），终版由 ExitPlanMode 最终读取保证；② `contentBytes` 在 `truncated:true` 时仍报磁盘真实字节数；③ REST 负载以文件系统为准但不回写内存态（下一事件自愈）；④ 前端交互后经修订为控制栏计划按钮（见下条 Sync）；⑤ ChatPanel 追加 transport `threadId` 透传与重连流 `plan-*` 帧转发。验证：后端 153 passed（`backend/.venv` pytest），前端 `npm run build` exit 0。
> [Sync] 2026-07-20: 交互修订 — 前端由「常驻面板」改为「浮动控制栏计划按钮」：`PlanButton`（`PlanPanel.tsx` 默认导出，title="计划"）渲染于「新建对话」按钮与「更多」按钮之间；默认不渲染，仅当 `planMode ∈ {planning, exited}` 或 `exists === true` 时出现；点击切换锚定弹层（计划 Markdown、徽标、updatedAt、截断加载完整），点击外部/Esc 收起，切换 thread 自动收起；未读更新以按钮圆点指示。弹层未复用 CollapsibleSection（按钮即开关语义），样式对齐栏内「更多」下拉。验证：`npm run build` exit 0。

# claude-plan 设计：Plan Mode 计划内容捕获与展示契约

> 本文件路径为兼容既有文档引用而保留。计划、待办和执行流水不再作为业务设计维护。

当前业务需求与已实现结果请从 [业务设计目录](../.folder.md) 按模块查阅。
