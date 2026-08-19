<!-- [Input] Chat UI, Claude Agent router/runtime, workspace sandbox, and thread persistence. -->
<!-- [Output] Current Chat and Agent interaction contract. -->
<!-- [Pos] Canonical chat-agent module design. -->

# Chat 与 Agent

## 业务目标

Chat 是通用 Agent 对话入口。普通 Chat 与 Dream 使用同一 Thread、消息、SSE、工具确认和恢复协议；
Dream 只增加 Run 上下文和独立工作台，不复制 Agent runtime。

## 当前需求与结果

- 新建 Thread 时由服务端固定 Deck、内容版本和 Agent 上下文；历史 Thread 不自动切换 Deck 版本。
- 同一 Thread 可在当前 Deck 包含的 Agent 间显式切换，不能越过 Deck 权限和配置边界。
- 消息流支持文本、Markdown、Mermaid、文件、工具调用、AskUserQuestion 和编辑器写入确认。
- 运行中通过 SSE 接收增量事件；刷新后从 Thread 消息、状态和 stream 端点恢复。
- 用户可以停止运行、删除 Thread、查看历史、Plan、TODO 和 SubAgent 进度。
- Tool Confirm 在服务端保存待确认状态；取消或拒绝不会执行工具写入。
- Workspace Mode 启用时，Agent 只能访问服务端分配的工作区和允许的临时根；网络和命令权限由服务端策略控制。
- Deck 预览示例进入 Chat 时只选择 Deck/Agent 并预填输入，不自动发送。

## 主要接口

`/api/claude-agent`、`/api/claude-agent/threads`、`/messages`、`/stream`、`/status`、
`/plan`、`/todos`、`/subagents`、`/stop` 和 `/tool-confirm` 共同构成公开生产协议。

## 代码所有权

- Chat UI：`frontend/src/components/chat/`
- Deck/Agent 选择：`frontend/src/components/deck/DeckChatSelector.tsx`
- 后端入口：`backend/routers/claude_agent.py`
- Runtime：`backend/claude_agent/`、`backend/services/claude_agent/`
- Thread 持久化：`backend/database.py`、`backend/claude_agent/service.py`
