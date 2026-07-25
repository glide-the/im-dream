# SandboxPermissionRequest 模块交互图

> 关联设计：`claude-agent-sandbox-network-permission-tool.md`
> 状态：已实现（2026-07-23）——实现与本图一致；步骤 ④（full-access）与
> ⑥（低敏 allow）在存在待审批网络请求时均被跳过（D→G 直连语义）。
> 日期：2026-07-23

## 1. 模块总览

```mermaid
flowchart LR
    subgraph CFG["业务配置层"]
        SC["system_config<br/>sandbox_network_mode<br/>sandbox_network_allowed_domains"]
    end

    subgraph BE["Server 权限判定层（backend）"]
        SVC["claude_agent/service.py<br/>读取配置 · 注入 AgentRunOptions"]
        HOOK["agent_runner._pre_tool_use_hook<br/>②.5 _apply_sandbox_network_permission"]
        CB["_make_tool_confirm_cb<br/>ToolConfirmationStore"]
    end

    subgraph BUS["事件推送层"]
        SSE["SSE tool-approval-request<br/>{confirmationKind: sandbox_network}"]
    end

    subgraph FE["前端弹窗层"]
        TP["claude-agent-transport.ts"]
        DOCK["ToolConfirmationDock<br/>网络变体卡片"]
    end

    subgraph RT["沙箱运行时"]
        CC["Claude Code / sandbox-runtime<br/>bwrap --unshare-net + 过滤代理"]
    end

    SC --> SVC --> HOOK
    HOOK -->|"未命中/策略关闭 → 确认"| CB --> SSE --> TP --> DOCK
    DOCK -->|"POST /tool-confirm"| CB
    CB -->|"allow / deny"| HOOK
    HOOK -->|"命中 allowedDomains → 显式 allow"| CC
    HOOK -->|"deny → 阻断"| CC
```

## 2. 判定流程（PreToolUse 决策链）

```mermaid
flowchart TD
    A["工具调用进入<br/>_pre_tool_use_hook"] --> B{"① editor 重定向?"}
    B -->|是| Z1["返回 redirect"]
    B -->|否| C{"② mode == disabled<br/>且为网络请求?"}
    C -->|是| Z2["硬拒绝 deny"]
    C -->|否| D{"②.5 沙箱网络权限判定<br/>_apply_sandbox_network_permission"}

    D -->|"mode == allowlist<br/>host 命中 allowedDomains"| Z3["显式 allow<br/>（low_sensitivity 子类）"]
    D -->|"mode == allowlist<br/>host 未命中 / Bash 网络命令"| G
    D -->|"mode == open<br/>任意网络请求"| G
    D -->|"非网络请求"| E{"④ full-access?"}

    E -->|是| Z4["allow"]
    E -->|否| F{"⑥ 低敏感度?<br/>（open 模式下网络工具已跳过）"}
    F -->|是| Z5["allow"]
    F -->|否| G["⑦ on_tool_confirmation_request<br/>弹窗确认"]
    G -->|批准| Z6["allow"]
    G -->|拒绝 / 超时 / 回调失败| Z7["deny"]
```

## 3. 确认时序（policy ON · 未命中域名）

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as 前端 ToolConfirmationDock
    participant API as POST /api/claude-agent/tool-confirm
    participant SVC as service._make_tool_confirm_cb
    participant HOOK as _pre_tool_use_hook
    participant SDK as Claude Agent SDK

    SDK->>HOOK: PreToolUse(WebFetch, url=github raw)
    HOOK->>HOOK: ②.5 allowlist 判定：host 未命中 allowedDomains
    HOOK->>SVC: on_tool_confirmation_request(payload<br/>+ confirmationKind=sandbox_network)
    SVC->>SVC: store.begin_pending(toolCallId)
    SVC-->>FE: SSE tool-approval-request
    FE->>U: 渲染网络确认卡（host / 策略模式）
    U->>FE: 批准 / 拒绝
    FE->>API: {thread_id, tool_call_id, approved}
    API->>SVC: confirm_tool → store.resolve
    SVC->>HOOK: future 返回 allow / deny
    HOOK->>SDK: hookSpecificOutput.permissionDecision
```

## 4. 三种模式行为对照

| 触发 | disabled | allowlist（命中） | allowlist（未命中） | open |
|---|---|---|---|---|
| WebFetch/WebSearch | 硬拒绝（现状） | 自动放行（新增低敏感度子类） | 弹窗 | 弹窗（每次） |
| 网络类 Bash 命令 | 硬拒绝（现状） | 弹窗（不解析 host，保守） | 弹窗 | 弹窗（每次） |
| 非网络工具 | 现有分类不变 | 现有分类不变 | 现有分类不变 | 现有分类不变 |
