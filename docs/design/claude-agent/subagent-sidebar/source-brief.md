# 子智能体任务展示原始需求

为聊天会话新增“子智能体任务”侧边栏入口和右侧详情面板。

现有组件位置：
- 入口位于 frontend/src/components/chat/PlanPanel.tsx 的 PlanButton，图标来自 frontend/src/components/chat/Icons.tsx。
- 页面承载位于 frontend/src/components/chat/ChatView.tsx 的 ChatViewContent。
- 右侧详情面板应复用 frontend/src/components/dashboard/FileSidebar.tsx 的布局与开合方式。

截图说明：
- 主图 `assets/subagent-detail.jpg`：任务详情页面。顶部显示“子智能体”，主体按“已开启”和“完成 · 数量”分组；任务行包含代理图标、任务名、摘要和耗时。
- 辅图 `assets/subagent-summary.png`：侧边栏入口元信息。显示多个最近代理图标、完成任务总数和“完成”状态。
- 聊天任务按钮参考 `assets/subagent-chat-button-reference.png`：Agent 工具记录应收敛为头像、任务名和状态胶囊；点击后进入对应任务详情，不展示内部启动 envelope。

功能目标：
1. 正确解析并显示最近对话里 subagent 的执行记录，包括运行中和已完成任务。
2. 在 PlanButton 所在的聊天侧边栏增加入口元信息；点击后在对话窗口右侧打开任务详情面板。
3. 空状态、数量、运行状态、完成状态、任务摘要与耗时应由真实会话数据驱动。
4. 遵循现有设计系统、国际化、可访问性和响应式行为，不引入独立 Tailwind 页面。
