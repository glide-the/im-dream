# Dream Agent 生命周期边界

Dream 不定义业务阶段状态机。Agent turn 的运行、工具确认、Stop、失败、取消、断线和恢复
全部使用 Chat 的 thread 生命周期；Skill 与 Artifact 不参与这些状态的计算。

## 1. 单一 Agent 生命周期

```mermaid
sequenceDiagram
    actor U as 用户
    participant UI as Chat 或 Dream 的共享 ChatPanel
    participant T as ThreadFactory
    participant S as ClaudeAgentService
    participant A as Claude runner

    U->>UI: 发送普通消息或 /skill 文本
    UI->>T: run_streaming(threadId)
    T->>S: assemble_context + execute_session
    S->>A: 原 SDK run_streaming
    A-->>UI: 增量文本、工具、确认或 AskUserQuestion
    alt 用户 Stop
        U->>UI: Stop 当前可取消主 turn
        UI->>T: cancel thread main turn
        T-->>UI: 单一 cancelled 结果
    else Agent 成功
        A-->>UI: 单一 completed 结果
    else Agent 或 Hook 失败
        A-->>UI: 单一 failed 结果
    end
```

页面不保存第二份 `submitting/streaming/waiting_confirmation` 业务状态，也不根据历史子 Agent
transcript、Artifact、Observer 或 Workflow 行显示 Stop。

## 2. 刷新、断线与页面切换

```mermaid
sequenceDiagram
    actor U as 用户
    participant P as Chat/Dream 页面
    participant H as Thread history/status
    participant E as Thread SSE

    U->>P: 刷新、断线恢复或切换页面
    P->>H: 用同一 threadId 读取历史和状态
    alt 主 turn 仍运行
        P->>E: 重连同一 stream
        E-->>P: 继续增量、确认或终态
    else 已结束
        H-->>P: 持久化历史与终态
    end
```

GET 不启动新 turn。切换页面不创建 thread、不重发首轮消息，也不改变 Claude session ID。

## 3. Hook 生命周期

```mermaid
sequenceDiagram
    participant S as ClaudeAgentService
    participant H as DreamArtifactTurnHook
    participant P as .dream last-good

    S->>H: before_main_turn
    H-->>S: 服务端派生 ticket + 文件摘要基线
    alt 根 turn 成功
        S->>H: after_main_turn
        H->>P: 校验并原子提交当前快照
    else failed/cancelled/waiting confirmation
        Note over S,P: 不执行 after_main_turn
    end
```

Hook 只在 Dream 根 turn 上执行一次；SDK 内部子 Agent 不单独提交快照。Hook 不生成第二
终态，但 Hook 失败会使同一 Chat turn 走既有唯一失败路径，不能继续宣称完成。

## 4. Observer 生命周期

Observer 由 `SessionObserverRegistry` 创建和关闭，订阅标准事件，使用 thread/turn/event
身份去重并忽略终态后的迟到业务提示。它没有持久状态账本，不扫描工作台、不发布文件、
不构建 Episode 关联，也不改变 Agent 或 Workflow 状态。异常由 registry 隔离，资源在
turn/session close 时释放。

## 5. 明确没有的生命周期

- 没有 Continuing 阶段；
- 没有 Skill 阶段、推荐动作、next action 或 completion fact；
- 没有 Episode action 的确认、派发、恢复或刷新状态机；
- 没有用 Artifact availability 推进 Agent turn；
- 没有用 Observer 投影反向控制 Chat 输入、Stop 或终态。
