<!-- [Input] Shared Chat Thread/SSE runtime, Dream authority, confirmations, Stop, reconnect, and Deck Agent selection. -->
<!-- [Output] Canonical Dream Agent interaction contract without a parallel runtime or client-selected authority. -->
<!-- [Pos] Dream Agent interaction source of truth. -->
<!-- [Sync] 2026-08-31: consume structured Thread binding errors and permit legal same-Deck current-Agent switching. -->

# Dream Agent 共享交互设计

> 状态：当前设计。本文只定义 Dream 与 Chat 共用的 Agent 交互；Skill、工作台文件和
> `.dream` 发布业务由[全业务交互](./business-interaction-design.md)与
> [Skill 和工作台同步](../story-workspace/skill-commands-and-workbench-sync.md)定义。

## 1. 交互合同

Dream 和 Chat 是同一个 actor-owned thread 的两个页面。两者共用：

- thread 消息、状态、历史和 Claude session；
- Chat SSE transport、parser、reducer 和 composer；
- 工具确认、AskUserQuestion、Stop、失败、取消和断线恢复；
- `ClaudeAgentService.assemble_context` 与既有 runner 入口。

Dream 浏览器只能携带标准 `threadId` 调用 Chat API。Workflow Run 与 Dream 上下文由服务端
根据已认证用户和 thread 反向解析，不能新增 Claude 报文字段，也不能由浏览器指定内部
run。Dream 页面可以额外读取 actor-scoped 的业务投影，但它不能覆盖 thread lifecycle。

`ChatPanel` 是唯一实时消息与输入状态 owner。Dream 不建立第二套 EventSource、消息过滤、
parser、reducer 或 Stop 状态。用户消息和内部 JSON 控制报文遵循 Chat 的原始可见性合同，
Dream 不额外做正文脱敏或页面级过滤。

Dream launch message 中的 Agent 是不可变来源证明；Thread 当前 Agent 是下一轮执行者，允许
在同一 Deck 内按既有 CAS 规则切换。resolver 必须校验 launch Agent 与其 top-level/nested
字段和请求指纹自洽，但不得要求它永远等于当前 Thread Agent。真正无法证明 authority 时，
沿用标准 Chat SSE 的结构化 `errorCode`，前端按
[Thread 绑定冲突与恢复](../story-workspace/thread-binding-conflict-recovery.md) 显示安全状态。

## 2. 普通发送与增量输出

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream 页面
    participant C as 共享 ChatPanel
    participant API as Chat thread API
    participant S as ClaudeAgentService
    participant R as Claude runner
    U->>C: 在 Dream 输入并发送
    C->>API: threadId + 标准 Chat 消息
    API->>S: assemble_context(thread)
    S->>R: 调用既有 run_streaming 入口
    R-->>API: 标准化文本/工具事件
    API-->>C: Chat SSE 增量帧
    C-->>D: 共享 reducer 实时渲染
    API-->>C: 唯一终态并恢复持久化历史
```

## 3. Dream 与 Chat 页面切换

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream 页面
    participant T as Thread 服务
    participant C as Chat 页面
    U->>D: 打开同一 Agent 会话
    D->>T: 读取 threadId 的历史、状态和 stream
    U->>C: 切换到 Chat
    C->>T: 使用同一 threadId 恢复
    T-->>C: 同一历史、运行状态和待确认工具
    U->>D: 返回 Dream
    D->>T: 再次使用同一 threadId
    Note over D,C: 不创建 thread，不重发首轮消息，不复制历史
```

## 4. 工具确认、拒绝和 AskUserQuestion

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as ChatPanel
    participant API as Chat confirmation API
    participant S as ClaudeAgentService
    S-->>P: canonical tool-input-available
    alt 普通批准
        U->>P: 批准
        P->>API: threadId + turnId + toolCallId + choice
    else 拒绝或 reject-only
        U->>P: 拒绝
        P->>API: 同一标准确认 DTO
    else AskUserQuestion
        U->>P: 选择或填写答案
        P->>API: 稳定 question/toolCall 标识 + answer
    end
    API->>S: 恢复同一 turn
    S-->>P: 继续输出或标准失败终态
```

Dream 不包装确认内容，不生成私有确认消息，也不通过 workflow 状态判断是否等待确认。

## 5. 子代理

```mermaid
sequenceDiagram
    participant S as ClaudeAgentService
    participant B as EventBus
    participant P as ChatPanel
    S->>B: subagent-started
    B-->>P: 标准 Chat SSE
    S->>B: subagent-running / tool events
    B-->>P: 更新子代理展示
    S->>B: subagent-completed / failed / cancelled
    B-->>P: 更新展示
    Note over P: 历史 subagent transcript 不代表主 turn 正在运行，也不阻塞输入
```

## 6. Stop 与取消传播

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as ChatPanel
    participant API as Stop API
    participant S as ClaudeAgentService
    participant R as Claude runner
    U->>P: 仅在存在可取消主 turn 时点击 Stop
    P->>API: stop(threadId)
    API->>S: 取消同一 turn
    S->>R: 传播取消
    R-->>S: 清理 SDK/异步资源
    S-->>P: cancelled 唯一终态
    P->>API: 恢复权威历史和状态
```

页面卸载或切换只断开当前 reader，不等同于 Stop。

## 7. 输出前失败与部分输出后失败

```mermaid
sequenceDiagram
    participant R as Claude runner
    participant API as Chat SSE
    participant P as ChatPanel
    alt 输出前失败
        R-->>API: error + failed terminal
        API-->>P: 失败且无空白 assistant 气泡
    else 部分输出后失败
        R-->>API: text-delta
        API-->>P: 保留可见部分输出
        R-->>API: error + failed terminal
        API-->>P: 标记失败并恢复持久化历史
    end
    Note over API: 每个 turn 最多一个 completed/failed/cancelled 终态
```

## 8. 断线重连与页面刷新

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as ChatPanel
    participant API as Thread API
    participant R as 运行中的 turn
    R-->>P: SSE 增量
    P-xR: 浏览器断线或刷新
    P->>API: GET history + status(threadId)
    alt turn 仍运行
        API-->>P: running + reconnect stream
        R-->>P: 后续增量与终态
    else turn 已结束
        API-->>P: completed/failed/cancelled + 完整历史
    end
    Note over P: reducer 以稳定消息/part 标识去重，不重新启动 SDK turn
```

## 9. Slash Skill 建议

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as 共享 Chat composer
    participant API as Plugin/Deck API
    U->>P: 输入 /
    P->>API: 读取 thread receipt、Deck refs 和安装清单
    API-->>P: 已启用、ready、版本与摘要匹配的 Skill
    P-->>U: 显示键盘可操作的 Slash 列表
    U->>P: 选择 /drama-script
    P-->>U: 仅填入“/drama-script ”
    Note over P: 不自动发送，不根据 Episode 产物推导推荐顺序
```

## 10. Observer

```mermaid
sequenceDiagram
    participant S as ClaudeAgentService
    participant B as Shared EventBus
    participant O as DreamObserver
    participant W as Workflow projection
    participant P as Chat SSE
    S->>B: NormalizedAgentEvent
    par 主交互
        B-->>P: Chat SSE
    and 后置业务投影
        B-->>O: 内部事件
        O->>O: 校验 thread/turn/event 顺序并幂等去重
        O->>W: 更新非控制型业务投影
    end
    Note over O: 异常被隔离，不能中断 SSE，也不能反向控制 Agent
```

事件重放或重复到达时，Observer 使用稳定 event/turn/thread 标识幂等；观察到终态后忽略
同一 turn 的迟到业务事件。Observer 不存储第二份 Agent 消息历史，也不决定 Skill、Stop、
确认或 Chat 终态。

## 11. Hook 与 Agent 终态边界

```mermaid
sequenceDiagram
    participant S as ClaudeAgentService
    participant H as DreamArtifactTurnHook
    participant R as Claude runner
    participant W as canonical 工作台
    participant D as .dream 私有投影
    S->>H: before_main_turn：校验授权并记录文件基线
    S->>R: 运行主 Agent
    R->>W: 随机 Skill 或自然语言产生文件
    alt 根 turn 成功
        R-->>S: completed candidate
        S->>H: after_main_turn：扫描、校验、幂等发布
        H->>D: 原子更新 stages/manifest
        H-->>S: 同步完成
        S-->>S: 发布唯一 completed
    else failed/cancelled
        R-->>S: failed/cancelled
        Note over H,D: 不发布本轮半成品
    end
```

Hook 以文件事实工作，不判断 `/drama-*` 的执行顺序，不写 completion fact，也不依赖 Agent
主动调用 MCP 才能保证同步。Hook 失败沿原 turn 失败路径处理，不新增第二终态。

## 12. 权限与数据边界

- Chat 路由校验 thread 所有权；Dream 业务 GET/写命令另行校验 actor、thread、run、workflow。
- 统一协议不取消 workflow 权限、路径 allowlist、schema、摘要、原子发布或数据完整性校验。
- Dream 上下文由服务端反向映射；客户端不能借 `threadId` 读取其他用户的 Run。
- `.dream` 是 Story Workspace 控制面；主 Agent 写 canonical 工作台，Hook 负责私有投影。
- MCP 写工具是辅助能力，不能成为成功、同步或生命周期的唯一依据。

## 13. 验收

- Dream 与 Chat 使用同一 thread history、status、SSE、confirmation、Stop 和 Claude session。
- 普通文本、Unicode、换行、JSON 控制正文和工具消息不被 Dream 额外过滤。
- 输出前失败、部分输出后失败、取消、断线和刷新均只产生一个权威终态。
- 只有真实可取消的主 turn 显示 Stop；历史子代理记录不阻塞输入。
- 输入 `/` 只展示当前 thread/Deck 实际安装且校验通过的 Skill，选择后不自动发送。
- 页面没有 Episode 阶段推荐按钮、next action、completion fact 或顺序状态机。
- Hook 在成功边界自动发布实际工作台文件；Observer 和 MCP 均不控制主 Agent。
