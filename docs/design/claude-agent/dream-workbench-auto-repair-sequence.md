<!-- [Input] Dream auto-repair interaction contract and current ThreadFactory/EventBus/history recovery behavior. -->
<!-- [Output] Business sequence diagrams for success, bounded failure, cancellation, and refresh/reconnect de-duplication. -->
<!-- [Pos] Sequence-diagram companion to dream-workbench-auto-repair.md; it does not define a separate protocol. -->
<!-- [Sync] 2026-09-01: initial business sequence set. -->
<!-- [Sync] 2026-09-01: add pre-write collection validation, move/merge cleanup, and visible structured exhausted failure. -->

# Dream 工作区自动修正业务时序图

本文只展开 [`dream-workbench-auto-repair.md`](./dream-workbench-auto-repair.md) 已定义的合同。参与者名称对应现有生产模块，不代表新增服务。

## 1. 原始 Turn、自动修正与成功完成

```mermaid
sequenceDiagram
    autonumber
    actor User as 用户
    participant UI as ChatPanel
    participant API as Chat/Dream 既有入口
    participant Factory as ClaudeAgentThreadFactory
    participant Bus as EventBus
    participant Service as ClaudeAgentService
    participant DB as PostgreSQL chat_message
    participant Claude as ClaudeAgentRunner
    participant Hook as DreamArtifactTurnHook
    participant WS as Thread workspace

    User->>UI: 发起原始 Dream Turn
    UI->>API: POST Chat 或 Dream 内部 dispatcher
    API->>Factory: run_streaming(original request)
    Factory->>Factory: Thread lock + admission + RUNNING
    Factory->>Service: assemble_context(original request)
    Service->>DB: save original user message
    DB-->>Service: commit
    Service->>Claude: run_streaming(normal options/resume)
    loop Claude 正常输出与工具调用
        Claude-->>Service: normalized callback
        Service->>Bus: publish event
        Bus-->>UI: SSE event
    end
    Claude->>WS: 修改 workspace
    Claude-->>Service: success result
    Service->>Hook: after_main_turn(trusted ticket)
    Hook->>Hook: 在任何投影写入前校验 canonical roots、stage collection 与 launch authority
    Hook-->>Service: PROJECT_STORY_SLUG_MISMATCH / agent_repairable

    Service->>Service: allowlist 模板 + stable id/attempt=1
    Service->>DB: INSERT user chat_message (dispatching)
    DB-->>Service: commit exact row
    Service->>DB: CAS dispatching -> dispatched（唯一执行权）
    DB-->>Service: claim won
    Service->>Bus: publish chat-message(exact dispatched id/parts/metadata)
    Bus-->>UI: SSE chat-message
    UI->>UI: 结束当前 AI SDK reader（不报错）
    UI->>API: GET history then status
    API->>DB: SELECT messages
    DB-->>API: 自动 user 消息
    API-->>UI: user 气泡 + running=true
    UI->>API: GET existing /threads/{id}/stream
    API->>Bus: subscribe(replay then live)

    Factory->>Factory: 记录逻辑 Turn 边界并分配新 Turn id；保持 lock/task/admission/EventBus
    Factory->>Service: assemble_context(auto user request, resume=true)
    Service->>DB: exact CAS replay auto user message
    Service->>Claude: run_streaming(normal repair Turn)
    Claude->>WS: 移动/合并到 canonical 目录并修正 project_id/project_slug
    Claude->>WS: 核对后移除旧项目根，不保留重复 EP/entity_id
    Claude-->>Service: success result
    Service->>Hook: after_main_turn(new trusted ticket)
    Hook-->>Service: validation passed
    Service->>DB: save repair assistant message + Claude session
    DB-->>Service: commit
    Service->>Bus: message-final + finish(stop)
    Bus-->>UI: repair assistant events + terminal
    Factory->>Factory: release admission/lock, RUNNING -> IDLE
    UI->>API: final authoritative history recovery
    API->>DB: SELECT messages
    DB-->>UI: original user + auto user + repair assistant
```

## 2. 错误分类与禁止自动修复

```mermaid
sequenceDiagram
    autonumber
    participant Service as ClaudeAgentService
    participant Hook as DreamArtifactTurnHook
    participant Authority as Server-owned authority
    participant WS as Workspace facts
    participant Bus as EventBus/SSE

    Service->>Hook: after_main_turn(ticket)
    Hook->>Authority: 校验 actor/thread/run/Deck/plugin/source/frozen facts
    alt 可信身份异常
        Authority-->>Hook: mismatch/missing/tampered
        Hook-->>Service: DREAM_LAUNCH_AUTHORITY_INVALID / non_repairable
        Service->>Bus: safe error + finish(error)
        Note over Service,Bus: 不生成 user 消息，不提示 Agent 修改 authority
    else 可信身份合法
        Hook->>WS: 读取唯一 canonical project slug
        alt workspace slug 与 trusted slug 不同
            WS-->>Hook: safe validated actual slug
            Hook-->>Service: PROJECT_STORY_SLUG_MISMATCH / agent_repairable
            Note over Service: allowlist code 可启动一次修正
        else 多 canonical 项目根 / stage schema 或 entity_id 重复
            WS-->>Hook: bounded workspace collection facts
            Hook-->>Service: allowlisted agent_repairable issue
            Note over Service: 固定模板要求移动/合并/清理；不公开原始路径或 Pydantic 文本
        else DB/CAS/权限/路径安全/未知异常
            Hook-->>Service: DREAM_ARTIFACT_SYNC_FAILED / non_repairable
            Service->>Bus: safe error + finish(error)
        end
    end
```

## 3. 第二次失败、Runner 失败与 Stop

```mermaid
sequenceDiagram
    autonumber
    actor User as 用户
    participant UI as ChatPanel
    participant Factory as ClaudeAgentThreadFactory
    participant Service as ClaudeAgentService
    participant Claude as ClaudeAgentRunner
    participant Hook as DreamArtifactTurnHook
    participant DB as chat_message
    participant Bus as EventBus

    Note over Factory,Service: auto request metadata 已声明 repairAttempt=1
    Factory->>Service: execute normal repair Turn
    alt 用户 Stop / task cancel
        User->>UI: Stop
        UI->>Factory: existing stop endpoint
        Factory-xService: cancel 唯一 bg_task
        Service->>DB: partial assistant（如有）+ auto status=failed
        Service->>Bus: finish(stop, cancelled=true)
    else Runner/assembly 失败
        Claude-->>Service: failure
        Service->>DB: auto status=failed
        Service->>Bus: safe error + finish(error)
    else Claude 成功但 Hook 再失败
        Service->>Hook: after_main_turn(ticket)
        Hook-->>Service: structured issue（例如 canonical roots 仍重复）
        Service->>DB: CAS auto status=failed
        Service->>Bus: DREAM_WORKBENCH_AUTO_REPAIR_FAILED + allowlisted 最终 validation code + finish(error)
    end
    Note over Service,Factory: 不构造第二条 auto user 消息，不存在第三个 Turn
    Bus-->>UI: terminal error card 显示安全最终原因
    UI->>DB: 通过 history API 恢复
    DB-->>UI: 同一 auto user 气泡，来源标记“工作台自动修正未通过”
```

## 4. 刷新、断线重连与去重

```mermaid
sequenceDiagram
    autonumber
    actor User as 用户
    participant UI1 as 原 ChatPanel
    participant Bus as EventBus replay buffer
    participant Producer as Factory bg_task
    participant DB as chat_message
    participant UI2 as 刷新后的 ChatPanel

    Producer->>DB: commit dream_repair_X + CAS dispatched
    Producer->>Bus: chat-message(id=dream_repair_X, status=dispatched)
    Bus-->>UI1: chat-message
    UI1-xBus: 主动结束 POST subscriber
    Note over Producer,Bus: producer 继续；subscriber 断开不 cancel bg_task

    User->>UI2: 页面刷新/重新进入 Thread
    UI2->>DB: history API
    DB-->>UI2: dream_repair_X（唯一持久行）
    UI2->>Producer: status API
    Producer-->>UI2: running=true
    UI2->>Bus: subscribe
    Bus-->>UI2: replay 原始 Turn events
    UI2->>UI2: 暂存 reconnect assistant
    Bus-->>UI2: replay chat-message(dream_repair_X)
    UI2->>UI2: message-id upsert + 清除边界前未持久化 assistant
    Bus-->>UI2: replay/live repair Turn events
    UI2->>UI2: 在 auto user 后创建 repair assistant

    alt 重复 chat-message / 再次重连
        Bus-->>UI2: chat-message(id=dream_repair_X)
        UI2->>UI2: replace same id；气泡数量不变
    end

    Producer->>DB: persist final assistant/status
    Producer->>Bus: finish
    UI2->>DB: final history recovery
    DB-->>UI2: exact ids/parts/metadata
```
