<!-- [Input] 用户对 Admin 请求体验的反馈、TS demo 启动入口、现有 iOS 执行与媒体工具合同。 -->
<!-- [Output] Agent 迁移终止决定、iOS 恢复与音频的职责及设计入口。 -->
<!-- [Pos] iOS 架构决策。产品流程与开发接口分别由下列专项文档维护。 -->
<!-- [Sync] 2026-11-26: 撤销 TS 迁移工作项及估算，以现有执行链推进恢复与音频设计。 -->

# Kastention iOS 架构决策

## 背景与问题

**终止将 Agent 从 Python 迁移到 TypeScript 的路线。** 用户反馈 Admin 优化后的接口响应已经可以接受。本地 `claude-agent-next-kit` 通过 `next dev`／`next start` 启动 Web 服务。迁入 demo 仍需解决手机锁屏、系统挂起、执行中断和重开核对，且会重复实现现有业务。

撤销原定在 `frontend/packages` 建设的 `claude-agent`、`claude-mcp`、`claude-plugins` 三个包及其迁移排期。任务与会话继续由现有 Python Agent 处理，连接与工具发现沿用现有 MCP，插件安装与工作区准备沿用现有插件服务。手机上继续使用已有 CLI Worker。

## 目标与边界

| 顺序 | 需要解决的问题 | 当前基础与设计缺口 |
| --- | --- | --- |
| 1. iOS 前后台与进程重开 | 用户锁屏或离开后，回到同一对话能分清任务仍在运行、等待回答、已完成或结果待核实 | 页面已能解除订阅并在返回时读取原对话，Factory 持有已接受的执行。设计需要将有限后台许可绑定到具体执行，按保存回执核对结果。见[恢复交互](mobile-recovery-interaction.md#2026-11-15-ios第一阶段任务交互)及[宿主与恢复合同](mobile-background-execution-technical.md#2026-11-15-ios第一阶段宿主与恢复合同)。 |
| 2. Agent 音频 | 正常显示 v4.2 脸型时钟；有媒体要播时先展示内容，请用户决定 | 后端已有可选音频 MCP 和问答。前端需接入媒体预览、原生播放器和锁屏媒体控制。见[组件设计](../../prd/mobile-app/ios-system-player.md)、[前端交互](mobile-clock-audio-frontend.md)及[播放器开发合同](ios-system-player-technical.md)。 |

## 概念与规则

- **同进程返回。** 页面订阅与任务分别由 `useNativeChatThread` 和 `ClaudeAgentThreadFactory` 持有。回到前台先读原 Thread；任务仍在运行时重新订阅，用户主动停止沿原停止入口处理。[页面生命周期](../../../frontend/app/_dream/components/chat/useNativeChatThread.native.ts) · [执行与订阅](../../../backend/claude_agent/thread_factory.py)
- **挂起与重开。** 系统挂起时端侧计算暂停。设计要求在有限后台时间到期时，只对绑定的那轮任务收尾。新进程按原 Thread、执行标识和保存回执核对。结果不明时显示“结果待核实”，重试仅读取，避免重复发消息、执行工具或播放音频。[宿主与恢复合同](mobile-background-execution-technical.md#保存与重开核对) · [Apple 后台执行时间](https://developer.apple.com/documentation/uikit/extending-your-app-s-background-execution-time)
- **确认与播放。** 设备具备播放能力且用户在当前对话启用工具后，发送时才传入 `mobile_clock_audio`。Agent 提供媒体信息，低敏工具通过 `AskUserQuestion` 收集本次选择。只有用户选择“播放”、本次调用成功返回 `playback_requested`，前端才创建或更新播放器。拒绝、取消及重读历史均保留当前播放状态。原生播放器按实际播放状态更新系统媒体控件；后台音频能力只用于媒体播放。[音频工具](../../../backend/libs/claude_agent_kit/server/mobile_clock_audio.py) · [Apple 媒体播放配置](https://developer.apple.com/documentation/avfoundation/configuring-your-app-for-media-playback)

原[架构路线评估](history/ios-app-architecture-routes-before-closure-20261126.md)、[三包迁移说明](../claude-agent/typescript-agent-modular-migration.md)及[旧执行拓扑](history/ios-execution-topology-20261115.md)供历史追溯。
