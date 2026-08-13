# Dream Agent 当前设计

> 状态：**已实现并通过本机真实业务验收（2026-08-13）**。

当前 Dream Agent 只解决一个完整业务：主 Agent 在当前 thread 工作区构建创作产物；
根 turn 成功后，宿主把实际文件同步到当前 Run 的 `.dream` 私有目录；Dream 页面读取
人物、场景和分镜并正常显示。

## 1. 当前架构

```mermaid
flowchart LR
    U["用户"] --> D["Dream 页面"]
    D --> T["共享 Chat thread / SSE"]
    T --> S["ClaudeAgentService"]
    S --> A["Claude Agent runner\n入口不变"]
    A --> W["canonical 工作台文件"]
    S --> H["DreamArtifactTurnHook\n仅成功后执行"]
    W --> H
    H --> P[".dream 私有 Run\nstages + artifact manifest"]
    P --> D
    T --> C["Chat 页面\n同一 thread"]
```

Dream 与 Chat 共用 thread、消息、Claude session、SSE、工具确认、Stop、历史和重连。
Dream 没有第二套 Agent runtime、SSE、parser 或 reducer。

## 2. 当前业务范围

- Dream 发起时创建可信 Workflow Run，并绑定同一 actor-owned Chat thread。
- 服务端给首轮 Agent 明确的项目 ID；Agent 只构建工作台产物，不写 `.dream`。
- 根 turn 成功后，Hook 校验人物、场景、分镜和 Project/Episode allowlist 产物。
- Hook 原子同步当前 Run 的页面 stage 和 `artifact/manifest.json`。
- Dream 页面通过既有 actor-scoped `dream-files` GET 展示，不新增页面协议。
- 刷新、Dream→Chat→Dream 都继续使用同一 thread，不重新发起首轮消息。
- Agent failed/cancelled/Stop 时不发布本轮半成品；同步异常不制造第二个 Chat 终态。

不属于当前范围：固定 `/drama-*` 命令顺序、next action、checkpoint、文件 watcher、
Observer 主动同步、MCP 作为同步前置条件，以及 Admin sealed Artifact 发布。

## 3. 当前文档

| 文档 | 用途 |
|---|---|
| [全业务交互](./business-interaction-design.md) | 当前可用业务及逐项时序 |
| [工作台自动同步](./deck-output-sync-design.md) | 文件发现、投影、幂等和失败边界 |
| [Project / Episode 合同](./project-episode-artifact-contract.md) | 当前 Run preview 与 Admin 权威 Artifact 的区别 |
| [工具与自动同步边界](./dreamflow-tool-boundaries.md) | Agent、Hook、Observer、MCP 的职责 |
| [设计审查](./design-review.md) | 当前架构接受结论与证据 |
| [Prompt 轮次记录](./prompt-rounds.md) | 可追溯执行记录，不是业务规范 |

目录中其他历史迁移文档只用于 Git/架构追溯；与上述当前文档冲突时，以上述当前文档
和可执行代码为准。

## 4. 真实验收

真实账号使用 `deepseek-v4-pro` 完成 Run
`run_604125a31ad9478990622b675a996863`：

- canonical 工作台：2 个人物、1 个场景、`project.yaml`、`EP01/storyboard.yaml`；
- `.dream`：3 个 stage、2 个 Artifact 文件副本和最终 manifest；
- canonical 文件与私有副本 SHA-256 一致；
- Dream 页面刷新、可见 Chat 按钮、同 thread 历史和返回 Dream 均通过；
- `--headed --workers=1`：`1 passed (1.2m)`；
- 后端聚焦回归：131 passed、2 skipped、59 subtests；
- 共享 Chat/layout：24 passed；TypeScript、ESLint、生产构建和 diff gate 通过。

该证据证明本机真实业务闭环，不代表 staging、生产发布或负载验收。
