> [Input] `backend/libs/claude_agent_kit/server/agent_runner.py`, Claude Code restored source `tools/SkillTool/constants.ts`, `backend/claude_agent/context_builder.py`, frontend tool confirmation flow.
> [Output] Claude-agent tool permission policy for `tool_choice` modes, sensitivity classes, and PreToolUse hook decisions.
> [Pos] permission-policy-doc in `docs/design/claude-agent`
> [Sync] 2026-06-09: initial standalone policy extracted from runner implementation and product rule: query-like tools are low-sensitivity; execution/write/interactive tools are high-sensitivity unless explicitly listed.
> [Sync] 2026-06-09: implementation note added for hook payload normalization (`tool_name`/`toolName`, `tool_input`/`toolInput`) and auto-mode retention of `Skill` in effective `allowed_tools`.
> [Sync] 2026-06-09: Settings-controlled `im_full_access_enabled` added; when enabled, exposed non-answer-form tools receive explicit PreToolUse allow after `.editor/` virtual-index redirects.
> [Sync] 2026-06-13: clarify separation from Claude Code Bash sandbox; per-thread
> workspace filesystem confinement is configured through `.claude/settings.json`,
> not by parsing shell paths in `PreToolUse`.
> [Sync] 2026-06-13: full-access mode now excludes AskUserQuestion-style tools;
> they still use frontend confirmation so answers can be collected.

# Claude-Agent Permission Policy

This document is the source of truth for Claude-agent tool permission decisions.
It describes the product policy, not Claude Code's internal classifier.

## 1. Goals

- Avoid native Claude Code permission prompts when the backend has already made a safe product-level decision.
- Keep `tool_choice=auto` useful for low-risk query and navigation workflows.
- Route high-sensitivity actions through the frontend confirmation side-channel so the user sees and approves the exact tool input.
- Default unknown tools to high-sensitivity.

## 2. Modes

| Mode | Policy |
|---|---|
| `auto` | Low-sensitivity tools return explicit `permissionDecision:"allow"` from `PreToolUse`. High-sensitivity tools emit `tool-approval-request` and wait for frontend confirmation. |
| `manual` | All non-special tools go through frontend confirmation. `.editor/` virtual-index `Read` redirects still run because they only replace placeholder reads with a safe tempfile snapshot. |
| `none` | No tools are exposed; auto allow rules do not apply. |

When `system_config.im_full_access_enabled=true`, exposed tools bypass the sensitivity matrix and receive explicit `permissionDecision:"allow"` in `PreToolUse`, except answer-form tools (`AskUserQuestion`, `mcp__user__ask_user`). Those tools still go through frontend confirmation because the form is the only place where user answers are collected and merged into `updatedInput`. This setting is controlled from Settings → AI model configuration → 「应如何批准 IM」. `tool_choice="none"` still exposes no tools.

Settings `system_config.workspace_enabled=true` additionally enables the
per-thread Claude Code Bash sandbox described in
[`claude-agent-workspace-sandbox.md`](./claude-agent-workspace-sandbox.md).
That sandbox is a runtime filesystem boundary for Bash and child
processes. It is deliberately not implemented as a shell path parser in
`_pre_tool_use_hook`.

## 3. Low-Sensitivity Tools

Low-sensitivity tools are query-like or context-selection operations with no direct content mutation.
Current auto-allow inventory:

| Tool class | Tool names / rule |
|---|---|
| Built-in read/search | `Read`, `Glob`, `Grep`, `LS`, `NotebookRead`, `TodoRead`, `WebFetch`, `WebSearch`, `BashOutput` |
| MCP resource query | `ListMcpResources`, `ReadMcpResource` |
| Workspace files area | `Read` / `Write` / `Edit` / `MultiEdit` only when the resolved target is inside `{cwd}/files/**` |
| Session query | `mcp__user__get_sessions_range` |
| Memory query | `mcp__memory__recall_shared_stories` |
| Necklace query | `mcp__necklace__*` names returned by `allowed_necklace_tool_names()` |
| Editor context switch | `mcp__editor__switch_editor` |
| Skill invocation | `Skill` |
| Read-only Bash subset | `Bash` only when the command has no shell metacharacters and the first token is in the read-only/navigation allowlist (`ls`, `cd`, `pwd`, `echo`, `cat`, `head`, `tail`, `wc`, `find`, `which`, `type`, `date`, `whoami`, `id`, `groups`, `env`, `printenv`, `uname`, `hostname`) |

`switch_editor` is low-sensitivity because the MCP handler is a no-op and the PostToolUse hook only changes which existing editor session `.editor/` reads resolve to. It does not modify document content.

`Skill` is low-sensitivity because Claude Code exposes skills through the built-in `Skill` tool, whose job is to expand or run a named skill prompt. The exact tool name was confirmed in restored Claude Code source: `src/tools/SkillTool/constants.ts` exports `SKILL_TOOL_NAME = 'Skill'`. Do not use a broad `skill*` prefix. Allowing `Skill` does not allow later tool calls made by that skill; those calls are evaluated again by this policy.

Implementation detail: hook payloads are normalized before policy lookup. The runner accepts both Claude hook JSON keys (`tool_name`, `tool_input`) and adjacent SDK/frontend camelCase keys (`toolName`, `toolInput`) so a payload such as `{"toolName": "Skill"}` cannot fall through as an unknown tool. In `auto` mode, `Skill` is also retained in effective `allowed_tools` even if a caller passes a custom allowlist, because Claude Code's SkillTool has its own permission path that otherwise defaults to ask for some skill metadata.

## 4. High-Sensitivity Tools

High-sensitivity tools require frontend confirmation in `auto` and `manual` modes:

| Tool class | Examples |
|---|---|
| Execution / complex shell | `Bash` with pipes, redirects, substitutions, separators, unknown commands, or write side effects |
| Writes outside workspace files | `Write`, `Edit`, `MultiEdit` when the resolved path is outside `{cwd}/files/**` |
| Editor writes | `mcp__editor__write_segment`, `mcp__editor__delete_segment`, `mcp__editor__insert_widget`, `mcp__editor__reply_to_comment` |
| User interaction | `AskUserQuestion`, `mcp__user__ask_user` |
| Unknown tools | Any tool not explicitly classified as low-sensitivity |

## 5. Hook Output Contract

Every backend allow decision must use the Claude Code CLI 2.1+ `PreToolUse` format:

```python
HookJSONOutput(
    hookSpecificOutput={
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }
)
```

Do not use empty `HookJSONOutput()` to mean allow. Empty output only declines to make a hook-level decision; Claude Code then falls back to its own permission layer, which can still show a native permission prompt.

Deny decisions use:

```python
HookJSONOutput(
    hookSpecificOutput={
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }
)
```

## 6. Decision Order

`agent_runner.py::_pre_tool_use_hook` applies decisions in this order:

1. `.editor/` virtual-index `Read` redirect, all modes.
2. If `im_full_access_enabled` is true, tools are exposed, and the tool is not an answer-form tool: explicit allow.
3. In `auto` only: workspace `files/` built-in file permission.
4. In `auto` only: explicit low-sensitivity tool allow.
5. Frontend confirmation callback.
6. Deny by default when confirmation is required but unavailable.

Bash sandboxing is not a step in this order. Claude Code loads the sandbox
settings from the current thread workspace and enforces them when a Bash command
actually runs.

## 7. Frontend Confirmation

When a high-sensitivity tool reaches the confirmation branch, the backend emits `tool-approval-request`.
The frontend maps that event to the existing tool part with `toolMetadata.approvalRequested=true` and renders Approve/Cancel UI.

Approval returns explicit `permissionDecision:"allow"`.
Rejection returns explicit `permissionDecision:"deny"` with the user-visible reason.

AskUserQuestion-style tools additionally merge frontend `answers` into `updatedInput`.
This remains true in full-access mode.

## 8. Matrix

| Tool / condition | `auto` | `manual` | `none` |
|---|---|---|---|
| `.editor/` virtual-index `Read` | Redirect + allow | Redirect + allow | Not exposed |
| `Read`, `Glob`, `Grep`, `LS`, `WebSearch` | Allow | Confirm | Not exposed |
| `Write` inside `{cwd}/files/**` | Allow | Confirm | Not exposed |
| `Write` outside `{cwd}/files/**` | Confirm | Confirm | Not exposed |
| `Skill` | Allow | Confirm | Not exposed |
| `mcp__editor__switch_editor` | Allow | Confirm | Not exposed |
| Editor write MCP tools | Confirm | Confirm | Not exposed |
| `AskUserQuestion` / `mcp__user__ask_user` | Confirm with form | Confirm with form | Not exposed |
| `AskUserQuestion` / `mcp__user__ask_user` with full access | Confirm with form | Confirm with form | Not exposed |
| Read-only Bash subset | Allow | Confirm | Not exposed |
| Complex or mutating Bash | Confirm | Confirm | Not exposed |
| Unknown tool | Confirm | Confirm | Not exposed |
