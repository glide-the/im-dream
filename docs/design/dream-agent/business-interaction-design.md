# Dream Agent 全业务交互设计

> 本文描述当前业务目标。Dream 是共享 Chat thread 上的创作工作台，不是第二套 Agent
> runtime，也不是按固定步骤推进的剧本生产状态机。

## 1. 业务边界

Dream 包含以下能力：

1. 用户发起一个有权限、可审计的 Dream Run，并复用一个 Chat thread；
2. 首次初始化默认引导 `/drama-init`；
3. 此后用户可以任意、重复执行当前 Deck 实际安装的 Skill；
4. 主 Agent turn 前后由宿主 Hook 检查 canonical 工作台并自动同步 `.dream`；
5. Dream 和 Execution 页面只读展示已经构建的 Project/Episode 产物；
6. 对话、工具确认、Stop、历史恢复和 Claude session 全部沿用 Chat。

不包含：阶段推荐按钮、next action、completion fact、Skill DAG、Episode action POST、
“只允许当前步骤”的服务端校验，以及由 Observer 推进的文件同步。

## 2. 发起 Dream 与首次初始化

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream 发起页
    participant API as Story Workspace API
    participant DB as Run 与 Thread
    participant S as ClaudeAgentService
    participant A as 主 Agent
    participant H as DreamArtifactTurnHook

    U->>D: 选择 Deck/Agent，输入创作目标
    D->>API: POST dream-runs/start
    API->>DB: 校验用户、订阅、Deck、幂等并创建 Run/thread/message
    API->>S: 通过标准 thread 启动首个 turn
    S->>A: Dream 上下文 + 默认 /drama-init 初始化目标
    API-->>D: workflowRunId + threadId
    D-->>U: 显示同一 thread 的实时输出
    A-->>S: 首轮根 turn 成功
    S->>H: 同步实际工作台文件
    opt 人物、场景、分镜三个初始化页面产物齐全
        H->>DB: 记录一次性 pending_review readiness
        D-->>U: 显示“确认并继续”
        U->>D: 确认初始化结果
        D->>DB: 记录 confirmed 并在同一 thread 继续
    end
```

浏览器不能提交工作区绝对路径、thread 所有权或 Claude session ID。首次初始化是默认产品
行为，不代表后续 Skill 必须按表格顺序执行。`pending_review → confirmed` 只服务首次
初始化确认；它不推导 Episode 下一步，也不在后续 Skill 之间流转。

## 3. Chat 输入 `/` 与 Skill 推荐

```mermaid
sequenceDiagram
    actor U as 用户
    participant I as Chat 输入框
    participant R as Deck 插件引用
    participant P as 插件安装事实
    participant L as Thread 冻结加载回执

    U->>I: 输入 /
    I->>R: 读取当前 Deck 的 enabled 引用
    I->>P: 读取 ready 安装及 component inventory
    opt 已有 thread
        I->>L: 核对当前 thread 冻结插件 digest/version
    end
    I-->>U: 展示实际安装且匹配的 Skill
    U->>I: 选择 /drama-script
    I-->>U: 仅插入普通文本，不自动发送
    U->>I: 补充 EPxx 与创作要求后发送
```

Slash 菜单不读取 Episode 阶段，不排序“下一步”，不隐藏可随机执行的 Skill。查询失败时
退化为普通文本输入，不阻塞 Chat。

## 4. 十三个业务 Skill

| 指令 | 业务用途 | 典型产物 |
|---|---|---|
| `/drama-init` | 项目初始化 | `project.yaml`、核心角色弧光、弧光台账、题材包 |
| `/drama-plan` | 分集规划 | 分集大纲、`character_beats`、节奏曲线、伏笔地图 |
| `/drama-script` | 剧本创作 | `script.md` |
| `/drama-asset` | 视觉资产设定 | 角色卡、场景卡、道具卡 |
| `/drama-storyboard` | 分镜设计 | `storyboard.yaml` |
| `/drama-prompt` | Prompt 生成 | Prompt package |
| `/drama-render` | 渲染指引 | 渲染参数与拼接方案 |
| `/drama-voice` | 配音 | 配音脚本与声线路由 |
| `/drama-edit` | 后期整合 | 剪辑、字幕、音效、转场清单 |
| `/drama-promote` | 宣发 | 封面、投放文案、数据策略 |
| `/drama-query` | 状态查询 | Project/Episode 事实摘要 |
| `/drama-doctor` | 项目体检 | 一致性检查与修复建议 |
| `/drama-payoff` | 爽点规划与审查 | 爽点蓝图、证据审查、债务审计 |

除首次 `/drama-init` 外，表格顺序不表达依赖、阶段或推荐关系。

## 5. 任意 Skill 的主 Agent turn

```mermaid
sequenceDiagram
    actor U as 用户
    participant C as 共享 Chat transport
    participant S as ClaudeAgentService
    participant H as DreamArtifactTurnHook
    participant A as 主 Agent
    participant W as canonical 工作台

    U->>C: /drama-storyboard EP03，保留既有人物设定
    C->>S: 标准 thread 消息
    S->>H: before_main_turn(服务端派生的 run/thread/workspace)
    H->>W: 记录 allowlist 文件摘要基线
    S->>A: run_streaming，恢复同一 Claude session
    A->>W: 读取/写入本次所需工作台产物
    A-->>S: 根 turn 成功
    S->>H: after_main_turn(ticket)
```

主 Agent 可以不调用 Story Workspace MCP。MCP 只辅助 Agent 主动预览或写受控 stage，
不能承担自动同步正确性。

## 6. Hook 自动同步与 Project/Episode 关联

```mermaid
sequenceDiagram
    participant S as ClaudeAgentService
    participant H as DreamArtifactTurnHook
    participant DB as Run/Thread 权限事实
    participant W as canonical 工作台
    participant P as .dream 私有 Run
    participant B as Episode Binding
    participant O as DreamObserver

    S->>H: after_main_turn
    H->>DB: 重验 actor/thread/run/冻结 Deck binding
    H->>W: 安全扫描当前 allowlist 快照
    H->>P: 幂等更新人物/场景/分镜 stage
    H->>P: 写 Project/Episode 文件副本
    H->>P: 最后原子替换 artifact/manifest.json
    opt 已构建唯一 Project 且存在 EP01 产物
        H->>B: 幂等构建 EP01 产物关联
    end
    H-->>S: 同步结果
    S-->>O: 标准事件/非控制型业务提示
```

Hook 比较 turn 前后摘要用于审计“本轮改了什么”，但发布的是 turn 成功后的完整当前
快照，因此用户随机调用 Skill 或重复修改同一文件都能收敛。相同字节是 no-op。

## 7. 页面读取与自动刷新

```mermaid
sequenceDiagram
    actor U as 用户
    participant E as Execution 页面
    participant API as Episode artifacts GET
    participant P as .dream/Binding

    U->>E: 打开或刷新当前 Run
    E->>API: GET workflow-runs/{run}/episode-artifacts + If-None-Match
    API->>API: 校验用户、Run、thread 和 Workspace
    API->>P: 只读当前关联与 manifest
    alt 尚未构建 Episode 产物关联
        API-->>E: unbound
        E-->>U: 尚未构建 EPxx 产物关联；继续自动读取
    else 已构建关联
        API-->>E: bound + Artifact surface + ETag
        E-->>U: 显示大纲、剧本、分镜、Prompt、渲染和审阅内容
    end
```

GET 不启动 Agent、不恢复任务、不写绑定，也没有“手动构建关联”按钮。页面只通过轮询和
精确 Run 输出失效信号读取最新事实。

## 8. Dream 与 Chat 切换

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream 页面
    participant C as Chat 页面
    participant T as 同一 thread history/status/SSE

    U->>D: 查看产物与对话
    D->>T: 读取 thread 消息、状态和流
    U->>C: 打开同一 Agent 会话
    C->>T: 使用相同 threadId
    T-->>C: 相同历史、session、工具确认和当前 turn
    U->>D: 返回 Dream
    D->>T: 继续相同 threadId
```

切换页面不重发首轮消息，不创建新 thread，不修改 `claude_session_id` 或
`resume_existing_session` 语义。用户消息和内部 JSON 正文均按 Chat 既有可见性显示，
Dream 不做正文脱敏或额外过滤。

## 9. 工具确认、Stop、失败与取消

```mermaid
sequenceDiagram
    actor U as 用户
    participant UI as 共享 ChatPanel
    participant S as ClaudeAgentService
    participant A as 主 Agent
    participant H as DreamArtifactTurnHook
    participant P as .dream last-good

    alt 工具确认或 AskUserQuestion
        A-->>UI: 标准 Chat confirmation
        U->>UI: 批准、拒绝或回答
        UI->>S: 标准 thread confirmation
    else 用户 Stop
        U->>UI: Stop 当前可取消主 turn
        UI->>S: 标准取消
        S-->>A: 取消传播
        Note over H,P: 不执行成功后同步
    else Agent failed/cancelled
        A-->>S: 标准失败或取消终态
        Note over H,P: 保留 last-good manifest
    else Hook 校验或原子发布失败
        H--xS: 同步失败
        S-->>UI: 使用同一 Chat turn 的唯一失败终态
        Note over P: 不伪装为同步成功，不产生第二终态
    end
```

## 10. Observer 边界

```mermaid
sequenceDiagram
    participant B as Shared EventBus
    participant O as DreamObserver
    participant Q as 派生业务投影/审计
    participant S as ClaudeAgentService

    B-->>O: NormalizedAgentEvent
    O->>O: 校验 thread/turn/event，去重与顺序检查
    O->>Q: 更新非控制型投影
    alt Observer 异常
        O--xQ: 记录日志并隔离
        Note over S: 不影响 SSE、Stop、终态或 Hook 发布
    end
```

Observer 不扫描文件、不重试发布、不创建 binding、不派发 Skill、不改变 thread 或 Workflow
生命周期。业务正确性所需的同步留在成功边界 Hook。

## 11. 权限与数据完整性

- 每次写操作重验用户身份、thread 所有权、Run、Workspace、Deck binding 和 revision；
- workspace、Run-private 和 Project/Episode 路径只由服务端派生；
- 文件读取拒绝 traversal、符号链接、非法编码、超限数量和大小；
- 内容文件先写，`manifest.json` 最后原子提交；
- 统一 Chat 协议不降低 Workflow 和 Artifact 业务权限；
- `.dream` 是当前 Run preview，不替代 Admin sealed Artifact 合同。
