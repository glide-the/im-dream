<!-- [Input] backend/routers/reflections.py、backend/reflections_agent.py、Claude Agent ThreadFactory/Service、Admin section persistence 与前端 voiceApi.ts。 -->
<!-- [Output] Reflections 任务启动、Agent 执行、转录解析、结果持久化、事件发布及恢复时序。 -->
<!-- [Pos] Reflections Agent 执行现行技术设计；产品入口与来源选择归内容选择 PRD/交互稿。 -->
<!-- [Sync] 2026-10-23: 展开 Task API→Engine→Runner→ThreadFactory/Service 及 Engine→EventBus→SSE，保留完整修订前稿。 -->

# Reflections Agent 执行与业务交互设计

## 背景与问题

[模块时序索引 6.1](../sequence-diagrams.md#61-回响分析analyze-echoes) 原图将执行阶段合并为 `TaskAPI→Agent` 和 `Agent→Stream`。当前源码包含后台任务、独立栏目 Thread、授权续期、Agent 内部流消费、转录解析、来源校验、结果保存和任务事件发布，需要分别说明各步骤的执行条件与输出。

本轮读取了指定任务[“扩展回归分析资源选择”](codex://threads/01a13319-aaf3-77b2-be92-932bec20c04a)的历史记录，并核对当前源码。历史记录用于定位 Notion 冻结输入与 Deck/Agent 选择；本文的执行合同依据本轮读取的代码。本文修订范围为后台执行说明、历史保存和文档验证；后台执行模块及运行权限沿用当前源码。当天再次分析弹窗的组件调整和交互规则由[分析内容交互稿](reflections-analysis-content-design.md)持有。

采用既有交互稿承载执行细节，在模块索引展开关键调用并链接本文。[修订前完整原文](reflections-agent-interaction-design-pre-execution-detail-20261023-history.md)保留原方案、持久化草案及图示文本。当前实现以 Admin PostgreSQL operation/DTO、Dream 执行模块和下列时序为准。

## 目标与边界

- 展示任务创建、订阅、启动、栏目执行、报告生成及结果读取的实际顺序。
- 展示单个栏目从授权建立到模型执行、转录解析和资源清理的完整调用链。
- 定义任务事件与 Agent 内部事件的生产模块、持久化位置和消费方。
- 覆盖确定失败、结果未知、事件保存失败、断线恢复和终态报告恢复。

产品目标、来源选择与页面骨架见[分析内容 PRD](../../prd/memory/reflections-analysis-content-prd.md)和[内容选择交互稿](reflections-analysis-content-design.md)。L2 蒸馏与 L3 回应流程见[记忆交互稿](reflections-agent-memory-interaction-design.md)。本文使用当前接口名称，新增接口数量为零。

## 概念与规则

### 执行模块

| 模块 | 输入、职责与输出 |
| --- | --- |
| `AnalysisView` / `voiceApi.runReflectionsTask` | 提交分析来源、栏目与语言；持有 task_id 和 lastEventId；读取任务与结果并打开报告 |
| `routers.reflections` | OAuth 身份与任务归属检查；创建冻结输入；公开 start/get/results/events/report 接口；准备任务 EventBus 并启动后台执行 |
| `start_reflections_task` / `ReflectionsTaskEngine` | 按 task_id 管理本机执行锁和后台 asyncio task；加载冻结输入，串行执行各栏目，保存结果与任务终态 |
| `ClaudeAgentReflectionsRunner.run_section` | 建立栏目授权和持久化 owner；准备提示文件；构造 `ClaudeAgentRunRequest`；等待 Agent 轮次完成；读取转录并解析最后一段 assistant 文本 |
| `AdminReflectionSectionPersistence` | 绑定 task/section/thread，维护栏目 authority、消息写入与私有 Session broker；提供 Gateway delegation；关闭时回收 broker、keeper 和 authority |
| `ClaudeAgentThreadFactory` / `ClaudeAgentService` | 执行统一 admission、上下文组装、Runner 生命周期、工具回调和消息持久化；提供轮次 completion 与 Factory owner_completion |
| `ClaudeAgentRunner` / Gateway | 按服务器选定模型执行推理和工具调用；Gateway 按当前 delegation 处理模型请求 |
| `ReflectionEventBus` / `TaskPersistenceObserver` | 分配任务事件 sequence，先调用 Admin 保存事件，再更新本机序号并发送给订阅者 |
| Reflections SSE endpoint | 校验任务读取权限；回放 Admin 历史事件；按 sequence 输出后续已保存事件 |
| Admin Reflections operations | 保存 task、section、Thread 消息、结构化 result、event 和 task 关联报告；检查业务权限、revision 与持久化回执 |

### 执行归属与输入

- 分析请求的 `analysis_content` 保存来源选择；Admin 创建事务冻结选定日记、Notion 正文和解析后的 Agent system prompt。Deck 提供 Agent 分组，执行选择使用成对的 `deck_id`、`agent_id`。
- `ReflectionsTaskEngine._assemble_context()` 加载冻结分析内容并准备任务工作区。没有可分析的日记正文且没有冻结 Notion 页面时，返回 `REFLECTION_NO_ANALYZABLE_INPUT`。
- 每个栏目通过 `reflection-section.begin` 取得其 thread_id、revision 与 authority。Runner 使用 `resume=False` 构造该栏目 Agent 轮次。
- 模型由 `resolve_platform_model()` 读取栏目 owner 的服务器配置和 Gateway catalog 后选择。选定 Agent 的 prompt 在 Reflections 系统提示前拼接；模型运行参数由选定模型提供。
- 前端提交的 `language` 经后端规范化后写入输入快照；栏目工作区的 `MEMORY_ANSWER_PROMPT.md` 追加该语言的输出要求，title、description、evidence 使用该语言，JSON 字段名保持既有合同。
- 日记检索通过本栏目的 snapshot Session provider 返回冻结范围；Notion 正文从 `analysis_content` 注入本次提示。私有 broker 的配置及权限见[独立设计](../claude-agent/session-projection-broker-design.md)。

### 两组事件

| 事件 | 生产与消费 | 保存与展示 |
| --- | --- | --- |
| Agent 内部事件 | ThreadFactory/Service/Runner 产生，`drain_chat_agent_turn()` 消费当前 Agent 流并等待 completion 和 owner_completion | Service 通过栏目 persistence 保存用户和 assistant 消息；栏目转录供 Runner 解析；分析 Chat 保留相关消息 |
| `reflection.*` 任务事件 | Engine 在 context、task、section 状态节点调用 `ReflectionEventBus.publish()` | `TaskPersistenceObserver` 先写 Admin event；SSE 回放并输出任务事件，页面据此更新状态 |

`ClaudeAgentReflectionsRunner` 的调用参数中没有向 Reflections EventBus 转发模型 token 的 `on_event`。任务 SSE 输出任务与栏目状态、结果计数和错误摘要；Agent 生成期间可持续执行模型或工具调用，页面在下一任务事件到达时更新栏目进度。

## 正常业务时序

### 1. 任务启动与栏目执行

```mermaid
sequenceDiagram
    actor U as 用户
    participant FE as AnalysisView / voiceApi
    participant API as routers.reflections
    participant A as Admin Reflections
    participant E as ReflectionsTaskEngine
    participant R as ClaudeAgentReflectionsRunner
    participant B as ReflectionEventBus
    participant S as Reflections SSE
    U->>FE: 选择分析来源与 Agent，提交分析
    FE->>API: POST tasks，auto_start=false、request_key
    API->>A: 创建任务并冻结分析输入
    A-->>API: task_id、来源与栏目
    API->>B: prepare_reflection_event_bus
    API-->>FE: 202 与 task_id
    FE->>S: GET tasks/task_id/events
    S->>A: 读取当前用户的历史事件
    S-->>FE: reflection.stream.connected 与历史回放
    FE->>API: POST tasks/task_id/start
    API->>A: reflection-task.start
    API->>E: start_reflections_task，加载输入并创建后台任务
    API-->>FE: 202 与当前任务状态
    E->>E: _assemble_context / _start_run
    E->>B: publish reflection.context.ready / reflection.task.started
    B-->>S: 保存成功后的任务事件
    S-->>FE: 分析进度
    loop 按任务 sections 串行执行，echoes 为示例
        E->>A: reflection-section.begin
        A-->>E: thread_id、revision、栏目 authority
        E->>B: publish reflection.section.started
        E->>R: run_section(section, load, begin)
        Note over R: 单栏目 Agent 执行见下一张图
        R-->>E: 从已保存转录解析的 JSON 结果
        E->>E: _validate_results，过滤日记引用并检查 Notion 引用
        E->>A: reflection-section.finish，outcome=completed
        A-->>E: 已保存 result_count
        E->>B: publish reflection.section.completed
        B-->>S: 已保存的栏目完成事件
        S-->>FE: 栏目进度与结果计数
    end
    E->>A: reflection-task.advance，action=finalize
    E->>A: reflection-report.ensure
    A-->>E: 原 task 关联报告结果
    E->>B: publish 任务终态事件
    B-->>S: 已保存的终态事件
    S-->>FE: COMPLETED / PARTIAL_FAILED / FAILED
    FE->>API: GET task 状态与 results
    API->>A: reflection-task.get
    A-->>API: 当前任务、结果和失败栏目
    API-->>FE: 结构化结果和失败栏目
    opt 需要读取或恢复报告
        FE->>API: POST tasks/task_id/report
        API->>A: 检查终态并 ensure 原任务报告
        API-->>FE: 原任务关联报告
    end
    FE-->>U: 展示分析结果与原任务报告
```

前端在收到连接事件后调用一次 start；SSE 建立过程包含既有宽限与轮询恢复。单栏目请求使用 `sections=["echoes"]`，当前统一入口可提交多个栏目。具体页面步骤和反馈由内容选择交互稿所有。

### 2. 单分区 Agent 执行

```mermaid
sequenceDiagram
    participant E as ReflectionsTaskEngine
    participant R as ClaudeAgentReflectionsRunner
    participant O as AdminReflectionSectionPersistence
    participant F as ClaudeAgentThreadFactory
    participant C as ClaudeAgentService
    participant K as ClaudeAgentRunner
    participant G as Admin / Gateway
    E->>R: run_section，冻结输入与 begin 结果
    R->>O: 创建 owner 并 start
    O->>O: 启动 authority keeper 与 snapshot Session broker
    R->>O: resolve_actor_id / gateway_runtime / system_config
    O->>G: 栏目 authority 校验与 Gateway delegation
    G-->>R: 经 owner 返回模型目录与服务器配置
    R->>R: resolve_platform_model 与 _prepare_section_workspace
    R->>R: 构造 ClaudeAgentRunRequest，冻结 Agent prompt + Reflections workflow
    R->>F: 经 drain_chat_agent_turn 调用 run_streaming(request)
    F->>C: assemble_context，绑定 owner 和当前栏目 Thread
    F->>C: execute_session
    C->>O: persist_user
    O->>G: 保存栏目用户消息
    C->>K: run_streaming(run_options, callbacks)
    loop 模型推理与按需工具调用
        K->>G: 已选模型的推理请求
        G-->>K: 模型输出或工具调用
        opt 需要补充日记正文
            K->>O: 经 user MCP 和私有 broker 查询冻结 Session
            O-->>K: 本栏目 snapshot 中的日记正文
        end
        K-->>C: 文本、工具及轮次回调
        C-->>F: 内部 Agent 流帧
        F-->>R: 由 drain 持续消费
    end
    C->>O: persist_assistant / update_session，保存消息与会话绑定
    O->>G: 持久化 assistant 与会话绑定
    C-->>F: message-final / finish
    F-->>R: completion 与 owner_completion 已完成
    R->>R: 检查 NormalizedTurnResult.completed
    R->>O: finally 关闭 Gateway runtime 和 owner
    O->>G: 回收 authority 与相关资源
    R->>G: reflection-section.transcript
    G-->>R: 已持久化的栏目 Thread 消息
    R->>R: 提取最后一段 assistant 文本，解析数组或对象
    R-->>E: 结构化结果，或输出解析错误
```

Runner 等待轮次 completion 和 Factory owner_completion 后处理结果。`REFLECTION_AGENT_TURN_FAILED` 表示轮次未满足完成条件；`REFLECTION_ANALYSIS_OUTPUT_INVALID` 表示转录的最终文本解析失败。owner 的清理逻辑由 `finally` 执行，转录读取通过后台 Reflections worker 身份完成。

`_validate_results()` 将日记引用限制到 launch snapshot，逐项检查 `related_notion_page_ids` 的冻结页面范围；缺少有效来源的条目被跳过。有效结果转换为 `ReflectionInsightInputDTO`，Notion 标题与 URL 写入 evidence。`reflection-section.finish` 返回后，Engine 才发布栏目完成事件。有效空数组可完成为零条结果；报告生成遵循 `reflection-report.ensure` 的原业务规则。

### 3. 任务事件保存与页面消费

```mermaid
sequenceDiagram
    participant E as ReflectionsTaskEngine
    participant B as ReflectionEventBus
    participant P as TaskPersistenceObserver
    participant A as Admin reflection-event.append
    participant S as stream_reflections_task_events_endpoint
    participant FE as AnalysisView / voiceApi
    E->>B: publish reflection.section.completed 等事件
    B->>B: 在锁内分配下一个 sequence 和 event_id
    B->>P: required observer.on_event
    P->>A: 保存 task_id、sequence、类型与 payload
    A-->>P: 已提交事件
    P-->>B: 保存完成
    B->>B: 更新 sequence、记录事件、发送订阅队列
    B-->>S: 已提交事件
    S-->>FE: event、id 和 JSON data
    FE->>FE: 更新栏目状态并保留 lastEventId
    opt 断线后恢复订阅
        FE->>S: 同 task_id 与 Last-Event-ID
        S->>B: 先注册本机订阅
        S->>A: 经 OAuth 读取权限查询历史事件
        A-->>S: cursor 后的持久化事件
        S-->>FE: 历史回放与高于回放最大 sequence 的后续事件
    end
```

任务事件保存成功后，本机 sequence 和订阅队列才推进。每次订阅先取得已有 bus 的 token，再读取 Admin 历史，SSE 以回放最大 sequence 过滤后续队列。浏览器取消订阅时释放 token，后台任务保留执行归属。

## 异常与恢复时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant FE as AnalysisView / voiceApi
    participant API as routers.reflections
    participant E as ReflectionsTaskEngine
    participant R as ClaudeAgentReflectionsRunner
    participant A as Admin Reflections
    participant B as ReflectionEventBus
    participant S as Reflections SSE
    E->>R: 执行当前栏目
    alt Agent 轮次失败或输出无法解析
        R-->>E: REFLECTION_AGENT_TURN_FAILED / REFLECTION_ANALYSIS_OUTPUT_INVALID
        E->>A: reflection-section.finish，outcome=failed
        A-->>E: 保存栏目错误
        E->>B: publish reflection.section.failed
        E->>E: 按任务顺序处理剩余栏目
    else 来源引用校验失败
        R-->>E: 候选结果
        E->>E: 拒绝越界 Notion 引用
        E->>A: 保存栏目失败与错误摘要
        E->>B: 发布持久化后的失败事件
    else Admin 写入结果未知
        A-->>E: AdminDataError，outcome_unknown=true
        E->>E: 退出本轮执行并保留 Admin 当前状态
        FE->>API: GET task/results，核对原任务
        API->>A: 校验归属并读取状态与结果
        A-->>API: 已保存状态与结果
        API-->>FE: 当前任务读取结果
    end
    opt required event observer 保存失败
        E->>B: publish 任务或栏目事件
        B->>A: reflection-event.append
        A-->>B: 保存错误
        B-->>E: 发布异常，当前 sequence 与队列保持原值
        Note over E,FE: 恢复页面时查询 task/results/events 的已保存状态
    end
    U->>FE: 刷新或重新打开分析
    FE->>API: GET task，读取原 task_id
    API->>A: 校验归属并查询原任务
    A-->>API: 当前状态、栏目进度及结果
    API-->>FE: 原任务读取结果
    alt 已完成或部分完成
        FE-->>U: 展示已保存结果
        opt 报告保存需要恢复
            FE->>API: POST tasks/task_id/report
            API->>A: 校验终态并执行 report ensure
            A-->>API: 原任务关联报告
            API-->>FE: 报告恢复结果
        end
    else CREATED 且用户明确启动
        FE->>API: POST tasks/task_id/start，启动原任务
        API->>A: 授权启动并加载原任务
        API->>E: 进入既有后台执行流程
        API-->>FE: 当前任务状态
    else 当前任务仍在执行
        FE->>S: 重新订阅并携带 Last-Event-ID
        S->>A: 查询已保存历史
        B-->>S: 后续已提交事件
        S-->>FE: 历史回放与后续任务事件
    end
```

确定的栏目失败会保存错误并继续其余栏目，最终状态由 Admin finalize 结果确定。`outcome_unknown=true` 传播到 Engine 后，本轮执行结束；恢复依据 Admin 当前状态和原业务回执。终态再次进入 Engine 只执行报告恢复分支。浏览器重开使用同一 task_id；进程重启后的生产者恢复取决于既有任务启动入口和 Admin 栏目状态，页面订阅负责读取事件。

## 状态转换

```mermaid
stateDiagram-v2
    [*] --> CREATED: 创建任务并冻结输入
    CREATED --> ASSEMBLING: 公开 start 获得启动状态
    ASSEMBLING --> QUEUED: context-ready 提交成功
    QUEUED --> RUNNING: run-started 提交成功
    RUNNING --> RUNNING: begin 栏目并等待 Agent 完整轮次
    RUNNING --> RUNNING: 解析转录、检查来源、保存栏目 outcome
    RUNNING --> COMPLETED: finalize 返回全部栏目成功
    RUNNING --> PARTIAL_FAILED: finalize 返回部分栏目失败
    RUNNING --> FAILED: finalize 返回全部栏目失败
    ASSEMBLING --> FAILED: 确定的上下文失败并保存 fatal-fail
    QUEUED --> FAILED: 确定的启动失败并保存 fatal-fail
    RUNNING --> FAILED: 确定的任务失败并保存 fatal-fail
    COMPLETED --> COMPLETED: 原任务 report ensure 或重开读取
    PARTIAL_FAILED --> PARTIAL_FAILED: 原任务 report ensure 或重开读取
    FAILED --> FAILED: 读取错误与已有任务记录
```

以上状态名称来自持久化 task DTO。Agent 内部流帧由 Agent 生命周期管理；任务状态由 Admin `advance`/`finish` 结果更新。结果未知时保持已保存状态，后续读取核实结果。

## 接口、权限与恢复规则

| 边界 | 当前合同 |
| --- | --- |
| create/start/get/results/events/report | OAuth 当前用户与任务归属校验；扩展来源按精确 analysis-content capability 准入 |
| worker-load / advance / begin / finish / append / transcript / report.ensure | Admin Reflections 后台 operation；任务与栏目范围由服务端 DTO/authority 检查 |
| Agent 消息和模型请求 | 栏目 authority 绑定 Thread；Gateway runtime 使用限定用途 delegation；RTA 留在 Host |
| EventBus 事件 | required observer 保存成功后分发；可选 observer 的失败按已有异常隔离处理 |
| report.ensure | Engine 在 finalize 后调用；前端通过原 task_id 的 report 入口恢复关联报告 |

源码使用 `POST /api/reflections/tasks/{task_id}/report` 恢复任务报告。6.1 的执行链统一采用该入口与后台 `reflection-report.ensure`。结果字段为统一的 title、description、related_session_ids、evidence、confidence 等 DTO 字段，业务栏目由 section 标识。

## 验收矩阵与本轮检查范围

| 检查项 | 功能验收标准 / 源码依据 |
| --- | --- |
| 执行调度 | start 校验归属并创建后台任务；同 task 本机锁避免重复并发；`ReflectionsTaskEngine.run` 管理执行阶段 |
| Agent 执行 | Runner 建立栏目 owner、选定模型并调用统一 ThreadFactory/Service；等待两项 completion，转录解析与完成判断分别执行 |
| 消息及来源 | 用户/assistant 消息通过栏目 owner 保存；只处理冻结来源，越界 Notion 引用导致栏目失败 |
| 任务事件 | `TaskPersistenceObserver` 先保存；保存失败时 sequence 与队列保持原值；SSE 回放与本机队列按 sequence 去重 |
| 失败及恢复 | 栏目确定失败继续处理其他栏目；未知写入通过原任务查询核实；重开读取结果和事件，终态恢复关联报告 |
| 图文一致 | 6.1 索引和本文使用相同的 Engine/Runner/Factory/Service/EventBus 职责与当前接口名 |

现有测试参考：[Engine、事件与权限](../../../backend/tests/test_reflections_agent.py)、[来源冻结及栏目执行](../../../backend/tests/test_reflection_analysis_content.py)、[快照与 Admin 操作](../../../backend/tests/test_admin_reflection_task_data.py)。本轮执行文档引用、历史字节、用词、Mermaid 解析/渲染及相邻图示保存检查；功能测试和真实模型验收属于后续执行范围。

## 源码索引

- [任务与 SSE 路由](../../../backend/routers/reflections.py#L503)：start、results、report、events。
- [Engine 与 Runner](../../../backend/reflections_agent.py#L456)：栏目执行、请求构造、转录解析、结果校验和事件发布。
- [统一流消费](../../../backend/services/story_workspace/dream_lifecycle_observer.py#L108)：drain 与轮次完成判断。
- [ThreadFactory](../../../backend/claude_agent/thread_factory.py#L352)与 [Service](../../../backend/claude_agent/service.py#L2520)：Agent 生命周期、消息持久化和内部流。
- [栏目 persistence](../../../backend/services/admin_data/reflection_section_persistence.py#L194)：authority、消息、Gateway 与资源清理。
- [前端任务客户端](../../../frontend/app/_dream/api/voiceApi.ts#L828)与 [AnalysisView](../../../frontend/app/_dream/components/AnalysisView.tsx#L842)：订阅、启动、恢复及报告打开。
