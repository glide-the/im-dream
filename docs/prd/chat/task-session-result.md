<!-- [Input] Admin committed task-result records and Dream's owner-authorized task-results route. -->
<!-- [Output] Source Chat completion notification rules and acceptance. -->
<!-- [Pos] Historical Chat task-result card behavior; superseded by docs/prd/claude-agent/task-session-completion.md. -->
<!-- [Sync] 2026-09-28: mark the result-card model superseded after adopting wait_threads parent-turn continuation. -->
<!-- [Sync] 2026-09-27: define durable task-result cards, delivery status and technical-message suppression. -->
<!-- [Sync] 2026-09-28: record normal-account real-model delivery, source-history refresh and navigation acceptance. -->

# 任务完成结果通知（历史稿，不再生效）

> 本稿保留 2026-09-28 以前的后台结果卡片方案。现行产品使用 [`wait_threads`](../claude-agent/task-session-completion.md)：结果作为父 Agent 当前 Tool 调用的回执返回，对话区不再渲染独立 `Task result` 卡片，也不再轮询 `/task-results`。

## 背景与问题

独立任务 Thread 完成后，来源会话需要展示可返回查看的结果。结果由 Admin 在目标最终消息事务中创建；Dream 提供来源 Thread 的受权读取接口。来源会话中的服务端技术输入用于续接执行，不能当作用户发言显示。

## 目标与边界

来源 Chat 的消息区显示简短结果卡片、服务端回传状态和前往目标 Thread 的操作。刷新页面后从 `GET /api/claude-agent/threads/{thread_id}/task-results` 恢复；打开中的页面定期刷新，并在页面重新可见或本会话执行结束时读取。现行[任务与进度面板](./task-activity.md)负责已创建任务、子智能体、计划和待办导航，结果卡片不复制到其中。目标 Thread 的来源标记保持原位。

本界面不创建结果、不修改派发状态、不从消息正文推断完成，也不展示内部通知标识、revision 或错误码。

## 概念与规则

| 状态 | 用户可见说明 | 页面行为 |
| --- | --- | --- |
| `pending` | 等待通知 | 展示已保存的目标结果和入口。 |
| `dispatching` | 通知中 | 继续刷新状态。 |
| `delivered` | 已通知 | 保留结果卡片和入口。 |
| `failed` | 通知失败 | 保留结果卡片和入口，允许查看目标 Thread。 |
| `state_unknown` | 通知状态待核对 | 保留服务端最后状态，不推断成功。 |

每条结果按 `notification_id` 稳定渲染。只读取当前 owner 授权的来源 Thread 结果；已成功读取过结果的会话遇到临时失败时保留上次有效列表并提供重试。旧部署缺少接口或首次读取失败时不打断普通 Chat，页面继续在可见期间重试；身份或 Thread 权限失效时清除旧结果。格式错误按读取失败处理。`role=user` 且 `metadata.kind=task-session-result` 的消息在历史与当前 Chat 可见消息入口过滤，不显示为用户气泡；其他用户消息仍正常显示。任务详情服务端返回 `completed` 时，会话信息中的任务状态显示“已完成”。

## 验收

结果卡片显示标题、有限高度的结果预览、状态和目标 Thread 按钮；点击进入对应目标会话。首次加载、状态变化、刷新恢复、失败重试与窄屏均可使用。技术消息不出现为用户气泡。组件测试使用受控接口响应覆盖状态和布局；2026-09-28 另用正常账户、正常数据库和真实模型完成生产入口 E2E，验证 `delivered` 结果触发来源历史刷新和原 Claude 会话续跑，并验证来源/目标双向导航。

视觉回执：[桌面](./assets/task-session-result-desktop.png)、[390px 窄屏](./assets/task-session-result-mobile.png)。
