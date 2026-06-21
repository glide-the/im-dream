> [Input] User incident summary, Claude Code sandbox network settings docs,
> `docs/prd/Settings.md`, `backend/routers/system_config.py`,
> `backend/libs/claude_agent_kit/server/workspace.py`,
> `backend/claude_agent/service.py`, and
> `frontend/src/components/dashboard/ModelConfigSection.tsx`.
> [Output] Interaction design for Settings-controlled Claude Agent sandbox
> network policy.
> [Pos] sandbox-network-interaction-plan in `docs/design/claude-agent`
> [Sync] 2026-06-21: initial design for sandbox network settings.

# Claude-Agent Sandbox Network Interaction Plan

## 1. Optimized planning prompt used for this round

```text
You are an Expert Prompt Architect.
Convert the requirement into an implementation-ready product and engineering
plan.
Goal: add a minimal Settings control for Claude Agent sandbox network behavior
after diagnosing failures across WebFetch domain checks, Bash/curl sandbox
network egress, and missing local tools.
Tasks:
1. Classify the failure layers and decide the correct product/runtime boundary.
2. Draft the interaction design for the Settings model configuration page.
3. Check whether the design meets the goal without adding an oversized policy
   system.
4. Implement the smallest code path through system_config, Settings UI, and
   thread-local .claude/settings.json sandbox.network.
Constraints: reuse existing ModelConfigSection and system_config APIs; do not
hard-code business domains as defaults; do not claim the UI can override host,
Docker, or managed sandbox policy; enabled modes keep WebFetch permission rules
separate from Bash sandbox network policy, while disabled mode denies
WebFetch/WebSearch in the runner; keep gh CLI installation as an environment issue.
Output: diagnosis, interaction design, non-goals, implementation points, and
validation evidence.
```

## 2. Problem handling judgment

The incident is not a single `raw.githubusercontent.com` domain block. It has
three independent failure layers:

| Way | Failure layer | Product handling |
|---|---|---|
| WebFetch | Tool domain permission | Keep under Claude-agent / Claude Code permission rules such as `WebFetch(domain:...)`. |
| curl / git / npm | Bash sandbox network egress | Add Settings-backed sandbox network policy and write it to `.claude/settings.json` `sandbox.network`. |
| gh CLI | Runtime environment | Install or omit the tool in the backend image/runtime; a network setting cannot fix a missing binary. |

Therefore the correct fix is a Settings control that expresses the user's
network policy intent and persists it per user. The runtime implementation
belongs in workspace initialization, because that is where the thread-local
Claude Code project settings are generated.

The UI must not promise that "open network" always succeeds. Claude Code
sandbox settings can pre-allow or deny domains, but actual connectivity can
still be constrained by managed settings, Docker networking, host firewalls, or
the absence of tools such as `gh`.

## 3. Interaction design

Location: Settings -> AI 模型配置, directly after Workspace Mode and before
IM Approval Mode. This keeps all agent execution-environment controls in one
area: workspace filesystem first, sandbox network second, approval policy third.

Controls use the reference layout supplied by the user:

1. "代理网络访问" is a close/enable pill switch.
2. When disabled, the persisted mode is `disabled` and no nested controls are
   shown. The control shows the helper text "设置完成后将禁用网络访问。"
3. When enabled, a left-border group shows domain policy, additional domains,
   HTTP method status, and a high-risk warning.

| Label | Stored mode | Runtime settings | User meaning |
|---|---|---|---|
| 禁用网络 | `disabled` | `sandbox.network.allowedDomains=[]` + `deniedDomains=["*"]`; PreToolUse denies network tools | Bash sandbox subprocesses and common network tools should not reach external domains. |
| 白名单 | `allowlist` | `sandbox.network.allowedDomains=[...]` | Pre-allow listed domains; other domains still follow Claude Code or managed policy. |
| 开放网络 | `open` | `sandbox.network.allowedDomains=["*"]` | Request outbound access for sandbox subprocesses, subject to runtime policy. |

Allowlist editing:

- Show only when proxy network access is enabled and "自定义域" is selected.
- Clicking `+ 添加域` opens a single-line domain input with Save/Cancel.
- Strip schemes and paths, so pasted URLs like
  `https://raw.githubusercontent.com/org/repo/file` become
  `raw.githubusercontent.com`.
- Support wildcard domain patterns such as `*.npmjs.org`.
- Reject bare `*` from allowlist input; selecting "开放网络" is the explicit way
  to request all-domain access.
- Added domains and removed domains save via `PUT /api/system-config`.
- Show saved domains as removable pills.

HTTP method control:

- Render a disabled "所有方法" select to match the reference layout.
- Do not persist HTTP method policy in this phase; Claude Code sandbox network
  settings are domain-based, and adding an unused method field would be
  misleading over-design.

Copy constraints:

- Explain that this setting affects Bash/curl/git/npm-style subprocesses.
- State that disabled mode rejects WebFetch/WebSearch in the runner, while
  enabled modes leave WebFetch domain behavior to tool/domain permission rules.
- State that runtime policy can still block outbound access even when the UI
  stores "开放网络".

## 4. Fit-to-goal / over-design check

This design fits the target because it gives the user a direct control for the
layer that failed in the incident: sandbox network egress for subprocesses.
It also keeps the other two layers visible so users do not expect a network
toggle to install `gh` or bypass WebFetch domain rules.

This is intentionally not over-designed:

- no role-based permission matrix;
- no admin UI for managed settings;
- no custom proxy configuration UI;
- no audit log;
- no per-tool network policy;
- no hard-coded GitHub domain defaults;
- no custom sandbox-runtime wrapper around the full Claude Code process.

The smallest sufficient implementation is:

1. persist `sandbox_network_mode` and `sandbox_network_allowed_domains` in the
   existing per-user `system_config_json`;
2. expose the control in the existing `ModelConfigSection`;
3. pass the config through `ClaudeAgentService` and attachment workspace init;
4. write `sandbox.network` into the existing thread-local
   `.claude/settings.json` sandbox block.

## 5. Runtime contract

Default mode is `allowlist` with an empty domain list. That preserves the
existing behavior of not pre-allowing any new domains.

The generated sandbox snippets are:

```json
{
  "sandbox": {
    "network": {
      "deniedDomains": ["*"]
    }
  }
}
```

```json
{
  "sandbox": {
    "network": {
      "allowedDomains": ["raw.githubusercontent.com", "github.com"]
    }
  }
}
```

```json
{
  "sandbox": {
    "network": {
      "allowedDomains": ["*"]
    }
  }
}
```

Claude Code documents `sandbox.network.allowedDomains` /
`sandbox.network.deniedDomains` as Bash sandbox domain controls. This design
adds runner PreToolUse enforcement for disabled mode because project-level
sandbox domain settings can otherwise enter prompt/fallback paths. WebFetch
allow/deny remains a permission-rule concern in enabled modes. See:

- https://code.claude.com/docs/en/sandboxing
- https://code.claude.com/docs/en/settings

## 6. Acceptance criteria

- Settings shows Sandbox Network under AI model configuration.
- Mode is loaded from and saved to `/api/system-config`.
- Allowlist domains are cleaned and de-duplicated before persistence.
- Thread workspace initialization writes `sandbox.network` according to the
  saved user config.
- Attachment workspace initialization uses the same network config.
- Tests cover disabled, allowlist, open, and service-to-workspace handoff.
