# Claude Agent 沙箱网络 SandboxPermissionRequest 权限工具设计

> 状态：已实现（2026-07-23）
> 实现备注：
> - 步骤 ②.5 同时守卫 ④（full-access allow）与 ⑥（低敏 allow）——与本文件
>   §3 只点名 ⑥ 相比多守卫了 ④，与配套时序图
>   `claude-agent-sandbox-network-permission-sequence.md` §2（D→G 直连、
>   不经 E）一致；`open` 模式"每次询问"因此不被完全访问模式吞掉。
> - `networkRequest.matchedAllowedDomain` 本期恒为 `null`（命中即显式
>   allow，不进入弹窗），字段为后续"放行并记住"迭代预留。
> - `WebSearch` 的 input 通常不含 `url`（只有 `query`），无法提取 host，
>   在 allowlist 模式下按"未命中"处理 → 弹窗（保守，与 §4 提取规则一致）。
> 关联文档：
> - `claude-agent-permission-policy.md`（权限等级与决策顺序）
> - `claude-agent-tool-confirmation-flow.md`（工具确认链路）
> - `claude-agent-sandbox-network-interaction-plan.md`（沙箱网络配置设计）
> - `../sandbox-wildcard-network-issue/interaction-design.md`（Claude Code 原生 SandboxPermissionRequest 现状分析，§5）
> 日期：2026-07-23

---

## 1. 背景与目标

Claude Code 原生的 `SandboxPermissionRequest` 弹窗（restored-src `REPL.tsx:2216` → `SandboxPermissionRequest.tsx`）依赖 sandbox-runtime 的 `sandboxAskCallback`，在 headless/SDK 模式下该回调 fail-closed（`cli/structuredIO.ts:731-753`），因此 Ink & Memory 目前**没有任何按请求粒度的网络审批交互**——网络治理只有三档静态模式（`sandbox_network_mode`: `disabled` / `allowlist` / `open`，见 `backend/routers/system_config.py:56`）。

本设计在 Ink & Memory 的 PreToolUse 权限层补上一个 **SandboxPermissionRequest 模式**，复用既有 `on_tool_confirmation_request` 确认链路（`backend/libs/claude_agent_kit/types.py:128`），实现：

| 业务配置 | 行为 |
|---|---|
| 网络策略关闭（`sandbox_network_mode = "open"`，不写 `sandbox.network`） | 每次网络请求触发确认弹窗 |
| 网络策略开启（`sandbox_network_mode = "allowlist"`） | 命中 `allowedDomains` 的请求 → `low_sensitivity_permission` 自动放行；未命中 → 确认弹窗 |
| 网络禁用（`sandbox_network_mode = "disabled"`） | 维持现状：硬拒绝（`_apply_disabled_network_permission`，`agent_runner.py:433-459`） |

> **语义变更说明**：`"open"` 模式原定义为"不限制出网"（`claude-agent-sandbox-network-interaction-plan.md:81`）。本设计将其重定义为"每次询问"——沙箱不配置网络策略时，由 Ink & Memory 确认层接管逐次审批。这是产品层面的有意变更，须在变更日志与用户文档中显式声明。

## 2. 权限等级模型映射

系统现有两级分类（无枚举，按 helper 函数分类，`claude-agent-permission-policy.md:57-100`）：

- `low_sensitivity_permission` → 自动放行（`_apply_low_sensitivity_query_permission`，`agent_runner.py:1243`）；
- 其余 → `on_tool_confirmation_request` 弹窗确认（`agent_runner.py:1659-1737`）。

本设计新增第三条分类规则，挂入同一决策链：

| 请求类别 | 分类 | 效果 |
|---|---|---|
| 命中 `allowedDomains` 的网络请求（policy ON） | **低敏感度子类**：`sandbox_network_allowed` | 显式 allow，不弹窗 |
| 未命中 `allowedDomains` 的网络请求（policy ON） | 高敏感度 | `on_tool_confirmation_request` 弹窗 |
| 任意网络请求（policy OFF / open） | 高敏感度 | `on_tool_confirmation_request` 弹窗（**每次**，不记忆） |
| 非网络请求 | 维持现有分类不变 | — |

## 3. 决策链插入点

`_pre_tool_use_hook`（`agent_runner.py:1574`）现有顺序：① editor 重定向 → ② disabled 硬拒 → ③ 工作区边界 → ④ full-access → ⑤ workspace files → ⑥ 低敏感度 → ⑦ 前端确认 → ⑧ 失败兜底 deny。

**插入新步骤 ②.5（`_apply_sandbox_network_permission`），位于 ② 之后、④ 之前**：

```
mode == "allowlist":
    提取目标 host（见 §4）
    host 命中 allowedDomains  → return allow（低敏感度子类，短路后续步骤）
    host 未命中 / 无法提取    → return None（落入 ⑦ 确认弹窗）
mode == "open":
    是网络工具/网络 Bash 命令 → return None，且步骤 ⑥ 必须跳过网络类工具
                                （否则 WebFetch/WebSearch 会被现有
                                  _LOW_SENSITIVITY_QUERY_TOOL_NAMES 自动放行，
                                  agent_runner.py:247-248）
mode == "disabled":
    不进入本步骤（② 已硬拒）
```

> 关键正确性约束：`WebFetch`/`WebSearch` 当前在低敏感度白名单内（`agent_runner.py:247-248`）。open 模式下若不改步骤 ⑥，新规则会被静默绕过。实现方式：步骤 ⑥ 执行低敏感度放行前，先判断 `sandbox_network_mode == "open"` 且为网络类工具 → 跳过。

## 4. 域名匹配语义

与 sandbox-runtime 对齐（`sandbox-runtime/src/sandbox/domain-pattern.ts:25-37`，语义记录于 `../sandbox-wildcard-network-issue/interaction-design.md:96`）：

| 模式 | 语义 |
|---|---|
| `example.com` | 精确匹配（大小写不敏感），**不含**子域 |
| `*.example.com` | 严格子域（`a.example.com` ✓，`example.com` ✗），不匹配 IP 字面量 |
| `*` | **非法值**，视为永不命中并记 warning（与上游 schema 禁止意图一致） |

host 提取规则：

| 工具 | 提取方式 | 可靠性 |
|---|---|---|
| `WebFetch` / `WebSearch` | `input.url` 的 host（`urllib.parse`） | 精确 |
| 网络类 Bash 命令（`_is_network_bash_command`，`agent_runner.py:402-430`） | **不解析目标 host**（shell 命令中的 URL 提取是启发式的，不可靠） | 一律按"未命中"处理 → 弹窗 |

即：`allowedDomains` 低敏感度放行**只对 WebFetch/WebSearch 生效**；Bash 网络命令在 allowlist 模式下始终弹窗。这是保守设计，文档化即可。

## 5. 确认弹窗协议扩展

复用现有链路，零新通道：

```
runner ⑦ → callbacks.on_tool_confirmation_request(payload)
  → service._make_tool_confirm_cb（service.py:1580-1643）
  → SSE tool-approval-request {toolCallId, toolName, input}
  → 前端 ToolConfirmationDock
  → POST /api/claude-agent/tool-confirm {thread_id, tool_call_id, approved, reason?}
  → ToolConfirmationStore.resolve → runner allow/deny
```

**payload 新增鉴别字段**（`agent_runner.py:1660-1664` 的 `confirmation_payload` 与 `service.py:1624` 透传）：

```json
{
  "toolCallId": "...",
  "toolName": "WebFetch",
  "input": { "url": "https://raw.githubusercontent.com/..." },
  "confirmationKind": "sandbox_network",
  "networkRequest": {
    "host": "raw.githubusercontent.com",
    "policyMode": "allowlist",
    "matchedAllowedDomain": null
  }
}
```

前端 `toolConfirmation.ts:66-102` 新增 `'sandbox-network'` 的 `PendingConfirmationKind`（由 `confirmationKind` 鉴别），`ToolConfirmationDock.tsx` 渲染网络变体卡片：host、命中策略模式、放行/拒绝。`claude-agent-transport.ts:365-376` 透传 `confirmationKind`。

> "放行并记住"（写入 `sandbox_network_allowed_domains` → `PUT /api/system-config`）列为后续迭代；本期 Dock 维持二元 批准/拒绝（`tool-confirmation-flow.md:549-551` 的两态约束）。

## 6. 配置 plumbing

| 层 | 改动 |
|---|---|
| `backend/libs/claude_agent_kit/types.py`（`AgentRunOptions`，~181 行） | 新增 `sandbox_network_allowed_domains: Sequence[str] \| None` |
| `backend/claude_agent/service.py`（~1079 行） | 值已在作用域（`service.py:874-875`），传入 `AgentRunOptions` |
| `agent_runner.py` `run_streaming`（~1491 行） | 读取新选项，随 `sandbox_network_mode` 一起闭包进 hook |
| `backend/routers/system_config.py` | 无需改动（键已存在） |

## 7. 验收标准

1. `allowlist` 模式下 `WebFetch` 请求命中 `allowedDomains`（含 `*.suffix` 严格子域语义）→ 无弹窗直接执行；
2. `allowlist` 模式下未命中域名 → 弹出网络变体确认卡，批准后执行，拒绝后 deny 回传；
3. `open` 模式下 `WebFetch`/`WebSearch`/网络 Bash 命令**每次**弹窗（同域名连续请求也弹），不再被低敏感度规则自动放行；
4. `disabled` 模式行为与现状完全一致（回归测试）；
5. Bash 网络命令在 `allowlist` 模式下始终弹窗（无论域名是否在清单中）；
6. 配置 `"*"` 在 `allowedDomains` 中 → warning 日志 + 永不命中；
7. 事件契约：`tool-approval-request` 携带 `confirmationKind: "sandbox_network"` 时前端渲染网络卡片，缺失时回退通用确认卡（向后兼容）。
