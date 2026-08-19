# Claude Agent 沙箱网络 SandboxPermissionRequest 权限工具设计

> 当前架构使用 SDK `can_use_tool` 作为运行时沙箱网络询问的单一通道。
> `workspace.py` 把系统配置写入每个 Thread 的 `.claude/settings.json`；
> 清单外域名由 Claude Code 沙箱产生 `SandboxNetworkAccess` 控制请求，复用现有
> 用户确认链返回 allow 或 deny。PreToolUse 只负责工具执行前权限，不重复实现网络代理门禁。
> 关联文档：
> - `claude-agent-permission-policy.md`（权限等级与决策顺序）
> - `claude-agent-tool-confirmation-flow.md`（工具确认链路，§6.3）
> - `claude-agent-sandbox-network-permission-sequence.md`（交互时序图）
> - `claude-agent-sandbox-network-interaction-plan.md`（沙箱网络配置设计）

---

## 1. 背景与目标

Claude Code 原生的 `SandboxPermissionRequest` 弹窗（restored-src `REPL.tsx:2216` → `SandboxPermissionRequest.tsx`）依赖 sandbox-runtime 的 `sandboxAskCallback`，在 headless/SDK 模式下该回调 fail-closed（`cli/structuredIO.ts:731-753`），因此 Ink & Memory 需要自己的按请求粒度网络审批交互。

**架构定位（2026-07-26 明确）**：网络策略是**系统级控制**——
`sandbox_network_mode` / `sandbox_network_allowed_domains` 由
`backend/libs/claude_agent_kit/server/workspace.py` 写入每线程
`.claude/settings.json` 的 `sandbox.network`，由 Claude Code 自身沙箱
（bwrap `--unshare-net` + 过滤代理）强制执行。当 sandboxed Bash 在代理层
命中未授权域名时，CLI 发起**系统级 control request**——不经 PreToolUse
hook，只通过 SDK 的 `can_use_tool` 回调通道送达。本设计将该通道接入
Ink & Memory 既有 `on_tool_confirmation_request` 确认链路，成为**唯一的
网络确认通道**。

| 业务配置 | 行为 |
|---|---|
| 网络禁用（`sandbox_network_mode = "disabled"`） | 双层硬拒：PreToolUse 层 `_apply_disabled_network_permission` 拒绝 `WebFetch`/`WebSearch`/常见网络 Bash 命令（2026-06-21 既有行为，未变）；运行时 `sandbox.network` 配 `deniedDomains=["*"]` |
| 白名单（`sandbox_network_mode = "allowlist"`） | CLI 沙箱代理按 `sandbox.network.allowedDomains` 放行清单内域名；清单外域名触发 `can_use_tool` 询问 → Ink & Memory 网络变体确认卡 |
| 开放网络（`sandbox_network_mode = "open"`） | 不写 `sandbox.network` = 不限制出网；**无逐次询问**（语义已回退，见 `claude-agent-sandbox-network-interaction-plan.md`） |

## 2. 现行机制：can_use_tool 确认通道

- 入参：`tool_name == "SandboxNetworkAccess"`，`input == {"host": <hostname>}`；
- SDK 支持：`claude_agent_sdk 0.2.128` 的 `ClaudeAgentOptions.can_use_tool: CanUseTool | None`（2026-07-26 迁移；此前 `claude_code_sdk 0.0.25` 的序列化方言过旧被新版 CLI 拒绝，见状态头），结果类型 `PermissionResultAllow(updated_input, updated_permissions)` / `PermissionResultDeny(message, interrupt)`；
- CLI 配对（2026-07-26）：`cli_path` 经 `sdk_env.apply_cli_path_to_options()` 锁定系统/npm CLI（2.1.220，与内置线对齐；内置优先会遮蔽 Docker 的 apply-seccomp 补丁 CLI）；apply-seccomp passthrough 经 `sandbox.seccomp.applyPath` settings 覆盖实现（2.1.220 单一二进制，无 vendor 文件可补丁）；
- 官方契约保证：`can_use_tool` 不会对权限流中已被解析的工具再次触发——本系统的 PreToolUse hook 对所有工具返回显式 allow/deny，因此接线后**不会重复弹窗**（含 AskUserQuestion，其由 hook 路径带 answers 解决）。

实现（`agent_runner.py`）：与 `_pre_tool_use_hook` 同闭包定义
`_can_use_tool(tool_name, input_data, context)` 并传入
`ClaudeAgentOptions(can_use_tool=...)`：

| 触发 | 行为 |
|---|---|
| `SandboxNetworkAccess` | 提取 `host`；走与 PreToolUse 步骤 ⑦ **相同**的 `on_tool_confirmation_request` 确认链路，payload 携带 `confirmationKind: "sandbox_network"` + `networkRequest: {host, policyMode, matchedAllowedDomain: null}`；批准 → `PermissionResultAllow(updated_input=input_data)`；拒绝/失败/超时 → `PermissionResultDeny(message=…)`，message 指明目标 host 并提示"可在设置中将该域名加入沙箱网络 allowedDomains" |
| 其他 tool_name | 走同一通用确认链路（不带 discriminator），映射方式镜像步骤 ⑦（含 AskUserQuestion 的 answers 合并进 updated_input）；按官方契约此分支极少触发 |
| 回调内任意异常 / 无确认回调 | 记录 warning 并 fail-closed → `PermissionResultDeny` |

## 3. 确认弹窗协议

复用现有链路，零新通道：

```
CLI 沙箱代理拦截 → SDK can_use_tool
  → runner._can_use_tool → callbacks.on_tool_confirmation_request(payload)
  → service._make_tool_confirm_cb（service.py，~1580-1650 行）
  → SSE tool-approval-request {toolCallId, toolName, input, confirmationKind, networkRequest}
  → 前端 ToolConfirmationDock（网络变体卡片）
  → POST /api/claude-agent/tool-confirm {thread_id, tool_call_id, approved, reason?}
  → ToolConfirmationStore.resolve → runner PermissionResultAllow/Deny
```

**payload 契约**：

```json
{
  "toolCallId": "...",
  "toolName": "SandboxNetworkAccess",
  "input": { "host": "cdn.example.com" },
  "confirmationKind": "sandbox_network",
  "networkRequest": {
    "host": "cdn.example.com",
    "policyMode": "allowlist",
    "matchedAllowedDomain": null
  }
}
```

前端 `toolConfirmation.ts` 的 `'sandbox-network'` `PendingConfirmationKind`
（由 `confirmationKind` 鉴别）驱动 `ToolConfirmationDock.tsx` 渲染网络变体
卡片：host、策略模式、二元 放行/拒绝。`claude-agent-transport.ts` 与
`claude-agent-sse-utils.ts` 透传 `confirmationKind` / `networkRequest`；
字段缺失时回退通用确认卡（向后兼容）。

> "放行并记住"（写入 `sandbox_network_allowed_domains` → `PUT /api/system-config`）列为后续迭代；本期 Dock 维持二元 批准/拒绝（`tool-confirmation-flow.md` §8.3 的两态约束）。

## 4. 行为矩阵

| 触发 | disabled | allowlist | open |
|---|---|---|---|
| `WebFetch` / `WebSearch` | PreToolUse 硬拒（既有） | **无 Ink & Memory 门禁**：遵循既有通用权限策略（auto 模式下低敏自动放行）；域名行为由 CLI 自身权限/沙箱层处理 | 同 allowlist——无逐次询问 |
| 网络类 Bash（sandboxed） | PreToolUse 硬拒（既有）+ 运行时 `deniedDomains=["*"]` | 清单内域名沙箱代理放行；**清单外域名 → can_use_tool 网络确认卡** | 不写 `sandbox.network` = 不限制出网，无询问 |
| 网络类 Bash（非沙箱，如 workspace 关闭） | PreToolUse 硬拒（既有） | 走既有通用确认策略（高敏 Bash 弹窗，无网络鉴别字段） | 同左 |
| 非网络工具 | 现有分类不变 | 现有分类不变 | 现有分类不变 |

关键权衡：PreToolUse 门禁拆除后，`open` 模式不再有任何逐次确认
（`sandbox.network` 省略 = 不限制出网）；`allowlist` 模式下 `WebFetch`
访问清单外域名不再被我们的确认卡前置拦截（它遵循 CLI 自身权限流），
只有沙箱内 Bash 的运行时代理拦截会经 `can_use_tool` 弹卡。

## 5. 配置边界

| 层 | 状态 |
|---|---|
| `backend/routers/system_config.py` | 不变——`sandbox_network_mode` / `sandbox_network_allowed_domains` 键为 CLI 沙箱配置的真相源 |
| `backend/libs/claude_agent_kit/server/workspace.py` | 不变——把上述配置写入每线程 `.claude/settings.json` 的 `sandbox.network` |
| `backend/claude_agent/service.py` | 读取配置用于 workspace 初始化；透传 `confirmationKind` / `networkRequest` 到 SSE；不向 `AgentRunOptions` 传 allowed_domains |
| `backend/libs/claude_agent_kit/types.py`（`AgentRunOptions`） | 仅保留 `sandbox_network_mode`（can_use_tool payload 上报 `policyMode` 用） |

## 6. 业务约束

1. sandboxed Bash 命中清单外域名 → `can_use_tool` 收到 `SandboxNetworkAccess{host}` → 弹出网络变体确认卡；批准后 `PermissionResultAllow(updated_input)` 放行，拒绝后 `PermissionResultDeny` 回传且 message 含 host 与 allowedDomains 提示；
2. 确认链路异常 / 无确认回调 → fail-closed `PermissionResultDeny` 并记 warning；
3. 其他 tool_name 走同一通用确认链路（不带 discriminator），不重复弹窗；
4. `disabled` 模式由 PreToolUse 硬拒网络工具；
5. 事件契约：`tool-approval-request` 携带 `confirmationKind: "sandbox_network"` 时前端渲染网络卡片，缺失时回退通用确认卡（向后兼容）；
6. `open` 模式无逐次网络确认（语义回退）；`allowlist` 模式 `WebFetch` 清单外域名不再被 Ink & Memory 前置拦截。
