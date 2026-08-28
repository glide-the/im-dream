<!--
[Input] Specified real user/Thread, PostgreSQL Chat/Gateway evidence, Claude transcript, Runner/Service/SSE contracts, and provider-free regression tests.
[Output] Record the terminal max-output root cause, minimal repair, business boundary, and local verification ledger.
[Pos] Dream implementation task record; no schema, deployment, provider configuration, or Agent state-machine ownership.
[Sync] 2026-08-28: classify final max_tokens as an explicit recoverable failure after the full SDK stream ends.
-->

# Claude Agent 输出上限自动停止修复

## 任务记录

| 字段 | 内容 |
|---|---|
| 原始需求 | 检查并修复 `dmeck@suoxya.com` 在 Thread `57daf71f-7272-5931-af3f-3b1990764d5c` 遇到的 Claude Agent 自动停止。 |
| 负责人 | Dream Codex task |
| 仓库 | `/Users/dmeck/project/ink-dream-memory` |
| 文件所有权 | Runner terminal classification、focused tests、直接相关 folder/task 文档。 |
| 当前状态 | 实现与本地 focused/regression 验证完成；未部署、未重启现有服务、未推送。 |
| Schema / migration | 不需要；不修改 PostgreSQL schema，不执行 DDL。 |
| 阻断项 | 现有本机 Dream 服务启动早于源码修复，按工作区安全合同不停止或替换用户服务；在线修复复验需要其后续按正常流程重启。 |

## 本地真实证据

- 指定账号、Thread、既有 Claude session、workflow Run 与 agent session 均存在；Run 无失败码，agent session 仍为 active，下一轮消息可继续，排除 Thread/Session 被销毁。
- 问题 assistant 行只保存一个 reasoning part，没有 text/tool/final；usage 为 `inputTokens=65911`、`outputTokens=4096`。
- 对应 Gateway request 为 HTTP 200、outcome succeeded；响应事件 `4101` 是 `message_delta`，`stop_reason=max_tokens`、`output_tokens=4096`，事件 `4102` 正常 `message_stop`。
- Chat assistant metadata 没有 `is_partial`，证明 Service 走了成功分支，而不是用户 Stop、SSE 断开或 `CancelledError` 分支。
- 真实页面经公开 Thread API 可见“比如剧情推进”之后只有 reasoning 展示，没有字段级/全局错误；下一条用户消息仍能沿原 Thread 继续。

## 根因

Admin Gateway 正确把输出长度终态提供给 Claude Runtime；Dream Runner 的 `_process_message()` 也把它投影成 `ToolEventPayload(type="message_delta", stop_reason="max_tokens")`。但是 Service 按设计忽略 `message_*` 工具事件，而 Runner 在 SDK iterator 正常结束后无条件保留 `success=True`。结果是：

1. reasoning 消耗满 4096 output tokens；
2. 未生成用户可见 final text；
3. Runner 仍报告成功；
4. Service 写入普通 assistant 行并发送 `finishReason=stop`；
5. 页面表现为没有错误的“自动停止”。

## 修复规则

- Runner 记录完整 SDK 流中最后一个非空 terminal stop reason。
- 只有 SDK iterator 已完整结束且最终 reason 仍为 `max_tokens` 时，才返回受控的可恢复失败。
- 若 Runtime 在同一 SDK 流内自行恢复并随后给出 `end_turn`，最终 reason 被更新，turn 继续按成功处理。
- 错误复用现有 `on_error → partial assistant persistence → finishReason:error`；Session ID 和已收集 usage 保留。
- 不自动重试或注入隐藏用户消息，避免已有工具调用、文件写入或外部副作用被重放。
- 不改 admission、lease、Runner 工具顺序、ThreadFactory、resume、cancel、SSE 帧顺序或 Agent 状态机。
- 不把 4096、8192 或其他任意值包装为产品规则；模型的真实 output 上限仍属于 Gateway model/provider 配置。

## 回滚

回滚 `agent_runner.py` 的 terminal reason 记录与流尾检查，并删除对应两条 Runner 用例即可。无数据库、配置或业务数据回滚。

## 验证账本

- `cd backend && .venv/bin/python -m pytest -q tests/test_claude_agent_runner.py`：exit `0`，`123 passed, 1 skipped, 100 subtests passed`。
- `cd backend && .venv/bin/python -m pytest -q` 运行 Service error/success/cancel、shared-session resume 与 ThreadFactory stop 五条 focused node：exit `0`，`5 passed`。
- `cd ../ink-admin-memory && npm test -- --run app/lib/gateway/stream-adapters.test.ts`：exit `0`，`2 passed`；证明 `length ↔ max_tokens` 的现有协议转换保持正确，Admin 无需代码修改。
- `cd backend && .venv/bin/python -m py_compile ... && .venv/bin/markdown-it ... && git diff --check`：exit `0`。
- 本机已有 Chrome + 正常 `5173/8765` 服务读取指定真实 Thread：公开 `messages/status/plan/todos/subagents/plugin-load-receipt` 均返回 200；页面复现“reasoning 后无错误即停止”的修复前基线。没有发送新模型消息或修改业务数据。

真实历史记录保留，不清理指定 Thread、Run 或 Gateway request。现有 Dream PID 在本次源码修复前已启动；遵守“不停止或替换用户已有服务”，所以浏览器在线修复后终态需待该服务按正常流程重启后复验。
