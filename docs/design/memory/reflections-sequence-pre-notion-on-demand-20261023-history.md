<!-- [Input] 修改前模块时序正文。 -->
<!-- [Output] 全量正文前置读取时期的完整第六节图示。 -->
<!-- [Pos] 历史时序；现行流程见 ../sequence-diagrams.md。 -->
<!-- [Sync] 2026-10-23: 按原文保存第六节，保留执行步骤补全后的图示。 -->

## 6. 深度分析模块

分析任务处理本次选中的日记与冻结 Notion 正文，按 echoes、traits、patterns 保存结构化结果。来源选择、页面入口与骨架见[分析内容交互稿](memory/reflections-analysis-content-design.md)；后台执行、Agent 内部流及任务 SSE 的完整说明见[Reflections Agent 执行设计](memory/reflections-agent-interaction-design.md)。

### 6.1 回响分析（Analyze Echoes）

下图以 `sections=["echoes"]` 展示单栏目执行。当前页面统一入口可提交多个栏目；Deck 提供 Agent 分组，执行选择使用成对的 `deck_id`、`agent_id`。Task API 通过 `start_reflections_task()` 创建后台 Engine，Runner 经 ThreadFactory 执行该栏目 Agent，Engine 按已保存结果发布任务事件。

```mermaid
sequenceDiagram
    actor User as 用户
    participant FE as AnalysisView / voiceApi
    participant TaskAPI as routers.reflections
    participant Admin as Admin Reflections
    participant Engine as ReflectionsTaskEngine
    participant Agent as ClaudeAgentReflectionsRunner
    participant Factory as ClaudeAgentThreadFactory / Service
    participant Bus as ReflectionEventBus
    participant Stream as Reflections SSE
    User->>FE: 提交分析来源、栏目和 Agent 选择
    FE->>TaskAPI: POST /api/reflections/tasks，auto_start=false
    TaskAPI->>Admin: 创建任务并冻结来源与 Agent prompt
    Admin-->>TaskAPI: task_id、冻结输入与栏目
    TaskAPI->>Bus: prepare_reflection_event_bus
    TaskAPI-->>FE: 202 与 task_id
    FE->>Stream: GET /api/reflections/tasks/task_id/events
    Stream->>Admin: 校验权限并读取持久化事件
    Stream-->>FE: reflection.stream.connected 与历史回放
    FE->>TaskAPI: POST /api/reflections/tasks/task_id/start
    TaskAPI->>Admin: reflection-task.start
    TaskAPI->>Engine: start_reflections_task，加载快照并创建后台任务
    TaskAPI-->>FE: 202 与当前状态
    Engine->>Engine: _assemble_context / _start_run
    Engine->>Admin: reflection-section.begin，section=echoes
    Admin-->>Engine: 栏目 thread_id、revision 与 authority
    Engine->>Bus: publish reflection.section.started
    Bus->>Admin: 经 required observer 保存任务事件
    Bus-->>Stream: 已提交的栏目开始事件
    Stream-->>FE: 栏目运行中
    Engine->>Agent: run_section(echoes, load, begin)
    Agent->>Agent: 建立栏目 owner、选择模型、准备工作区与请求
    Agent->>Factory: 经 drain_chat_agent_turn 调用 run_streaming
    Factory->>Factory: assemble_context / execute_session，执行模型与工具
    Factory->>Admin: 通过栏目 persistence 保存用户及 assistant 消息
    Factory-->>Agent: 内部流消费完成；completion 与 owner_completion 已完成
    Agent->>Agent: 关闭栏目资源
    Agent->>Admin: reflection-section.transcript
    Admin-->>Agent: 栏目 Thread 转录
    Agent->>Agent: 解析最终 assistant 文本为 JSON
    Agent-->>Engine: 候选分析结果
    Engine->>Engine: 校验来源并转换 ReflectionInsightInputDTO
    Engine->>Admin: reflection-section.finish，保存 echoes 结果
    Admin-->>Engine: result_count 与栏目状态
    Engine->>Bus: publish reflection.section.completed
    Bus->>Admin: reflection-event.append 成功后推进 sequence
    Bus-->>Stream: 已提交的栏目完成事件
    Stream-->>FE: 栏目完成与结果计数
    Engine->>Admin: finalize 任务并执行 reflection-report.ensure
    Engine->>Bus: publish 对应任务终态事件
    Bus->>Admin: 持久化终态事件
    Bus-->>Stream: 已提交的终态事件
    Stream-->>FE: 任务终态
    FE->>TaskAPI: GET /api/reflections/tasks/task_id 与 results
    TaskAPI->>Admin: 读取当前任务、结果和失败栏目
    Admin-->>TaskAPI: 当前任务与已保存结果
    TaskAPI-->>FE: 结果与失败栏目
    opt 报告读取或保存恢复
        FE->>TaskAPI: POST /api/reflections/tasks/task_id/report
        TaskAPI->>Admin: 校验终态并 ensure 原任务报告
        TaskAPI-->>FE: 原 task 关联报告
    end
    FE-->>User: 展示回响结果与任务报告
```

#### 执行与事件合同

| 阶段 | 执行模块与输出 |
| --- | --- |
| 启动分析 | Task API 校验启动权限并创建后台 Engine；响应包含 task_id 和当前状态 |
| 执行 Agent | `ClaudeAgentReflectionsRunner.run_section()` 经统一 ThreadFactory/Service 执行；`drain_chat_agent_turn()` 消费内部流并等待轮次和 Factory owner 完成 |
| 取得结果 | Runner 从 Admin 栏目转录提取最后一段 assistant 文本，解析 JSON；Engine 校验冻结来源后保存结构化结果 |
| 发布进度 | Engine 调用 `ReflectionEventBus.publish()`；`TaskPersistenceObserver` 保存事件成功后，SSE 输出 `reflection.*` 状态、计数与错误摘要 |
| 打开报告 | Engine finalize 后执行 `reflection-report.ensure`；前端按原 task_id 查询或恢复关联报告 |

Agent 内部流供 Runner 等待执行完成，栏目消息通过 persistence 保存。Reflections SSE 的事件生产方为 Engine/EventBus；栏目生成期间，页面在任务事件到达时更新状态。单栏目执行、事件持久化、异常恢复和状态转换的正文图见[执行设计](memory/reflections-agent-interaction-design.md)。

[修订前 6.1 原图](history/pre-admin-user-preferences-20260915/sequence-diagrams.md#61-回响分析analyze-echoes)完整保留。

### 6.2 特质分析 / 模式分析

`traits`、`patterns` 使用同一 Task API、Engine、Runner、ThreadFactory 和任务事件链。Engine 按任务 sections 顺序串行执行，分别保存各栏目的结果与错误。持久化结果采用统一 DTO 字段 `title`、`description`、`related_session_ids`、`evidence`、`confidence`，栏目归属由 `section` 标识。

---

