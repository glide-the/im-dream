<!-- [Input] Dream auto-repair interaction contract and current ThreadFactory/EventBus/history recovery behavior. -->
<!-- [Output] Business sequence diagrams for success, bounded failure, cancellation, and refresh/reconnect de-duplication. -->
<!-- [Pos] Sequence-diagram companion to dream-workbench-auto-repair.md; it does not define a separate protocol. -->
<!-- [Sync] 2026-09-01: initial business sequence set. -->
<!-- [Sync] 2026-09-01: add pre-write collection validation, move/merge cleanup, and visible structured exhausted failure. -->
<!-- [Sync] 2026-09-01: show repair-safe ambiguous context assembly before the normal Runner turn. -->
<!-- [Sync] 2026-09-01: show fresh launch-authority cleanup scope resolution and exact PreToolUse stale-root deletion. -->
<!-- [Sync] 2026-09-01: show marker-only deletion denial returning the exact safe full-root retry command. -->
<!-- [Sync] 2026-09-01: show persisted projectCleanup, matching .dream facts, and actionable trusted-root denial. -->
<!-- [Sync] 2026-09-01: show assistant persistence before both Hook attempts and preserve the committed reply across SSE/history handoff. -->

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
    participant Context as DreamWorkbenchContext
    participant DB as PostgreSQL chat_message
    participant Claude as ClaudeAgentRunner
    participant Guard as PreToolUse safety guard
    participant Hook as DreamArtifactTurnHook
    participant WS as Thread workspace

    User->>UI: 发起原始 Dream Turn
    UI->>API: POST Chat 或 Dream 内部 dispatcher
    API->>Factory: run_streaming(original request)
    Factory->>Factory: Thread lock + admission + RUNNING
    Factory->>Service: assemble_context(original request)
    Service->>Context: refresh_for_turn(workspace)
    alt workspace 有多个结构安全的 canonical project
        Context-->>Service: unbound context(project_resolution=ambiguous)
        Note over Context,Service: 不选择任一 slug；禁止创建第三套 Project；不修改可信身份
    else 唯一或尚无 project
        Context-->>Service: resolved/missing context
    end
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
    Service->>DB: save original assistant(exact reasoning/tool/text parts + session)
    DB-->>Service: commit
    Service->>Hook: after_main_turn(trusted ticket)
    Hook->>Hook: 在任何投影写入前校验 canonical roots、stage collection 与 launch authority
    Hook-->>Service: PROJECT_STORY_SLUG_MISMATCH / agent_repairable

    Service->>Hook: resolve trusted/stale project cleanup fact
    Hook-->>Service: projectCleanup(trusted, stale[])
    Service->>Service: allowlist 模板 + exact relative paths + stable id/attempt=1
    Service->>DB: INSERT user chat_message (dispatching)
    DB-->>Service: commit exact row
    Service->>DB: CAS dispatching -> dispatched（唯一执行权）
    DB-->>Service: claim won
    Service->>Bus: publish chat-message(exact dispatched id/parts/metadata)
    Bus-->>UI: SSE chat-message
    UI->>UI: 结束当前 AI SDK reader（不报错）
    UI->>API: GET history then status
    API->>DB: SELECT messages
    DB-->>API: 原始 assistant + 自动 user 消息
    API-->>UI: 保留 assistant + user 气泡 + running=true
    UI->>API: GET existing /threads/{id}/stream
    API->>Bus: subscribe(replay then live)

    Factory->>Factory: 记录逻辑 Turn 边界并分配新 Turn id；保持 lock/task/admission/EventBus
    Factory->>Service: assemble_context(auto user request, resume=true)
    Service->>Context: refresh_for_turn(workspace)
    Context-->>Service: ambiguous 时先返回不猜根的普通上下文
    Service->>Hook: resolve_auto_repair_project_cleanup_scope(ticket, validationCode)
    Hook->>DB: reload authoritative Run + immutable launch message
    DB-->>Hook: trusted Run/Thread/Deck/plugin/projectStorySlug
    Hook-->>Service: fresh trusted slug + exact stale slug set
    Service->>Service: compare persisted projectCleanup == fresh scope
    Service->>Context: refresh_for_turn(auto_repair=fresh scope)
    Context->>WS: rewrite server-owned .dream/WORKBENCH.md facts
    Context-->>Service: trusted/stale/merge direction/trusted delete=false
    Service->>Service: build repr-hidden typed execution scope
    Service->>DB: exact CAS replay auto user message
    Service->>Claude: run_streaming(normal repair Turn)
    Claude->>WS: 移动/合并到 canonical 目录并修正 project_id/project_slug
    Claude->>Guard: Bash rm -rf exact stale project root
    Guard->>Guard: 校验 typed scope、Run/Thread、单目标、路径、no-symlink、merge coverage
    Guard-->>Claude: permissionDecision=allow（无需确认框）
    Claude->>WS: 移除旧项目根，不保留重复 EP/entity_id
    Claude-->>Service: success result
    Service->>DB: save repair assistant(exact reasoning/tool/text parts + session)
    DB-->>Service: commit
    Service->>Hook: after_main_turn(new trusted ticket)
    Hook-->>Service: validation passed
    Service->>Bus: message-final + finish(stop)
    Bus-->>UI: repair assistant events + terminal
    Factory->>Factory: release admission/lock, RUNNING -> IDLE
    UI->>API: final authoritative history recovery
    API->>DB: SELECT messages
    DB-->>UI: original user + original assistant + auto user + repair assistant
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

## 2.1 自动清理安全分支

```mermaid
sequenceDiagram
    autonumber
    participant Claude as ClaudeAgentRunner
    participant Guard as PreToolUse
    participant Scope as DreamAutoRepairExecutionScope
    participant WS as Thread workspace

    Claude->>Guard: rm request
    Guard->>Scope: validate typed server-only marker
    alt 普通 session / Run、Thread 或 validation 不匹配
        Scope-->>Guard: invalid or absent
        Guard-->>Claude: deny（通用 .dream write guard）
    else scope 合法且只请求 rm stories/<stale>/project.yaml
        Guard-->>Claude: deny marker-only bypass + 返回 exact full-root command
        Claude->>Guard: rm -rf -- stories/<stale>
        Guard->>WS: 重新执行完整 scope/path/tree 校验
    else scope 合法且请求删除 trusted root
        Guard-->>Claude: deny；明确 trusted root 必须保留 + 返回 stale root exact command
        Claude->>WS: Read/Glob + Edit/Write，按 stale -> trusted 合并
        Claude->>Guard: rm -rf -- stories/<stale>
    else scope 合法且请求递归清理
        Guard->>WS: resolve exact stories/<stale-slug>
        alt 多目标、越界、非 scope slug 或 shell script
            WS-->>Guard: target mismatch
            Guard-->>Claude: deny
        else exact stale root
            Guard->>WS: lstat workspace/stories/roots/tree + compare relative entries
            alt 未完整迁移 / symlink / 特殊文件 / tree 超限
                WS-->>Guard: unsafe or incomplete
                Guard-->>Claude: deny；先补齐迁移
            else every stale entry represented under trusted root
                WS-->>Guard: cleanup preconditions satisfied
                Guard-->>Claude: allow original exact rm
                Claude->>WS: remove scoped stale root
            end
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
        Service->>DB: persist completed repair assistant SSE parts
        DB-->>Service: commit
        Service->>Hook: after_main_turn(ticket)
        Hook-->>Service: structured issue（例如 canonical roots 仍重复）
        Service->>DB: CAS auto status=failed
        Service->>Bus: DREAM_WORKBENCH_AUTO_REPAIR_FAILED + allowlisted 最终 validation code + finish(error)
    end
    Note over Service,Factory: 不构造第二条 auto user 消息，不存在第三个 Turn
    Bus-->>UI: terminal error card 显示安全最终原因
    UI->>DB: 通过 history API 恢复
    DB-->>UI: 同一 auto user + 已完成 repair assistant，来源标记“工作台自动修正未通过”
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

    Producer->>DB: original assistant 已提交；commit dream_repair_X + CAS dispatched
    Producer->>Bus: chat-message(id=dream_repair_X, status=dispatched)
    Bus-->>UI1: chat-message
    UI1-xBus: 主动结束 POST subscriber
    Note over Producer,Bus: producer 继续；subscriber 断开不 cancel bg_task

    User->>UI2: 页面刷新/重新进入 Thread
    UI2->>DB: history API
    DB-->>UI2: original assistant + dream_repair_X（唯一持久行）
    UI2->>Producer: status API
    Producer-->>UI2: running=true
    UI2->>Bus: subscribe
    Bus-->>UI2: replay 原始 Turn events
    UI2->>UI2: replay 原始 SSE；history assistant 保持为 durable 事实
    Bus-->>UI2: replay chat-message(dream_repair_X)
    UI2->>UI2: message-id upsert；保留边界前 durable assistant，清除边界后的原 Turn 临时 replay
    Bus-->>UI2: replay/live repair Turn events
    UI2->>UI2: 在 auto user 后创建 repair assistant

    alt 重复 chat-message / 再次重连
        Bus-->>UI2: chat-message(id=dream_repair_X)
        UI2->>UI2: replace same id；气泡数量不变
    end

    Producer->>DB: Hook 前已 persist final repair assistant/status
    Producer->>Bus: finish
    UI2->>DB: final history recovery
    DB-->>UI2: exact ids/parts/metadata
```
