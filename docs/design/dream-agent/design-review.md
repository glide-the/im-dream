# Dream Agent 设计审查

> 结论：**接受**。当前最小业务已实现并通过真实模型、真实数据和真实页面验收。

## 1. 审查结论

| 问题 | 结论 |
|---|---|
| 是否形成第二套 Agent runtime/SSE/reducer | 否；Dream 直接复用 Chat thread、SSE 和 `ChatPanel`。 |
| 是否修改 Claude Agent 入口 | 否；`ClaudeAgentRunner.run_streaming` 与 `agent_runner.py` 未改。 |
| 是否修改 session identity | 否；原始 `claude_session_id` 和 resume 语义保持不变。 |
| 同步是否依赖 Agent 主动 MCP | 否；宿主在成功根 turn 后自动同步。 |
| 是否建立命令 DAG/next action/checkpoint | 否；同步只看实际文件。 |
| Observer 是否成为状态 owner | 否；Observer 不参与文件发布或 Agent 控制。 |
| 页面是否增加新协议 | 否；继续使用 actor-scoped `dream-files`。 |
| 权限是否削弱 | 否；before/after 都绑定可信 actor/thread/Run/binding。 |
| 是否发布失败/取消半成品 | 否；只有 root turn success 调用 after hook。 |
| 是否把 preview 冒充 Admin Artifact | 否；合同明确区分 Run preview 与 sealed Artifact。 |
| 页面是否适应窗口 | 是；共享主容器限制根级横向溢出，真实 1200×720 验证通过。 |

## 2. 被拒绝的过度设计

- 固定或随机 `/drama-*` 命令注册表；
- next action、recommended action 或 checkpoint 决定同步；
- Agent 必须调用 MCP 才能让页面显示；
- 文件 watcher、每个 PostToolUse 或子 Agent 完成时提前发布；
- Observer 读取工作台、重试发布或推进 Workflow；
- Dream 专用 EventSource、transport、parser、reducer 或第二终态；
- 多环境部署分支和 runtime tier 判断。

## 3. 安全与一致性

- 工作区、thread、Run 和 Project/Episode 私有路径全部由服务端派生。
- 文件读取拒绝 traversal、符号链接、非法编码、超限数量和超限大小。
- 私有写入使用目录锁、`O_NOFOLLOW`、临时文件、fsync 和原子替换。
- `manifest.json` 最后写，是已发布 preview 的提交标记。
- Hook 异常与 Chat 流隔离；日志不进入 SSE 正文。
- Workflow 写命令继续检查用户身份、thread 所有权、权限和 revision。

## 4. 验收证据

- 真实账号、真实本机数据、真实 `deepseek-v4-pro`。
- 最终 Run：`run_604125a31ad9478990622b675a996863`。
- 产物：2 人物、1 场景、1 分镜、`project.yaml`、`EP01/storyboard.yaml`。
- `.dream`：3 个 stage、2 个私有文件副本、最终 manifest；源/副本 SHA-256 一致。
- Dream 刷新、Dream→Chat→Dream、同 thread history、窗口适配均通过。
- 有头 Chromium：`--headed --workers=1`，`1 passed (1.2m)`。
- 后端聚焦：131 passed、2 skipped、59 subtests。
- 共享 Chat/layout：24 passed；生产构建、ESLint、py_compile、diff check 通过。
- Admin Gateway 中本轮模型请求为 settled/succeeded/HTTP 200，可在“请求日志”查看。

## 5. 未宣称的内容

本审查只接受本机当前业务闭环，不授予 staging、canary、生产发布、负载或 Admin sealed
Artifact 验收结论。
