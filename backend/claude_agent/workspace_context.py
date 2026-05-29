# [Input] None — self-contained prompt template module.
#         Runtime dependency: libs.claude_agent_kit.server.editor_index.EDITOR_RESOURCES
#         defines the virtual resource names embedded in this template.
# [Output] Provide build_workspace_context_block to ClaudeAgentContextBuilder.build_user_message.
# [Pos] workspace-context-prompt node in backend/claude_agent
# [Sync] 2026-05-28: initial implementation — standalone workspace context prompt
#                    for edit-point context assembly integration.
# [Sync] 2026-05-29: add Document editing workflow section so Agent receives in-message
#                    scheduling guidance alongside the capability inventory.
# [Sync] 2026-05-29: remove set_comment_feedback from write tools list (not in final
#                    4-tool design); update reply_to_comment signature to include reason.
# [Sync] 2026-05-29: add session_id parameter to build_workspace_context_block and include
#                    it in the template so the agent can pass it in write tool calls.
# [Sync] 2026-05-29: rename session_id → editor_session_id throughout to eliminate
#                    ambiguity with workspace_id (cwd basename / Claude thread ID);
#                    editor_session_id is the user_sessions.id from /api/sessions.

"""Workspace context prompt for the Ink & Memory Claude Agent.

Produces the ``<workspace_context>`` block that is injected into every user
turn between ``<runtime_context>`` and the user's message text.  The block
tells the agent about:

- the working directory path;
- the current session ID (required for write tool calls);
- the workspace directory layout (files/, skills/, logs/, .claude/, .editor/);
- the ``.editor/`` virtual index mechanism and readable virtual paths;
- the read / write path separation rules and the MCP write tools.

The template is intentionally static with respect to ``editor_state`` — it
describes the *mechanism*, not the current document content.  The agent reads
actual document content on demand via ``read_file``.

Usage::

    from claude_agent.workspace_context import build_workspace_context_block

    block = build_workspace_context_block(
        cwd="/workspaces/thread-xyz",
        editor_session_id="sess-abc123",   # user_sessions.id from /api/sessions
    )
    # Returns a "<workspace_context>…</workspace_context>" text string.
    # Returns an empty string when cwd is falsy.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

WORKSPACE_CONTEXT_TEMPLATE = """\
<workspace_context>
Working directory: {cwd}
Editor Session ID: {editor_session_id}

  ↑ This is the document session ID from /api/sessions (user_sessions.id).
    It is distinct from the workspace directory name and the Claude thread ID.
    You MUST pass it as the first argument to every MCP write tool call.

Workspace layout:
  files/    — user-uploaded and agent-produced files
  skills/   — installable skill packages
  logs/     — agent execution logs
  .claude/  — Claude project config (read-only)
  .editor/  — EditorState virtual index (virtual read-only)

Editor virtual index (.editor/):
  This directory holds placeholder files. Reading them triggers a real-time
  redirect to the current EditorState snapshot — the on-disk content is
  always empty {{}}.

  .editor/cells.json       — ordered array of all document cells (TextCell / WidgetCell)
  .editor/commentors.json  — list of applied voice commentor annotations
  .editor/tasks.json       — list of ongoing analysis tasks
  .editor/session.json     — session metadata (id, selectedState, createdAt)
  .editor/full_state.json  — complete EditorState snapshot (debug / full analysis)

Reading document content:
  read_file(".editor/<resource>.json")                      — intercepted; returns live snapshot

Writing document content (all require human confirmation):
  write_segment(editor_session_id, cellId, text, reason)          — replace a cell's full text
  delete_segment(editor_session_id, cellId, reason)               — remove a cell (irreversible)
  insert_widget(editor_session_id, widgetType, data, afterCellId) — insert a widget cell
  reply_to_comment(editor_session_id, commentId, content, reason) — add to a comment thread

  NOTE: Always pass the Editor Session ID shown above (NOT the working directory
  name) as the first argument to every write tool call.

  CONSTRAINT: Do NOT write files directly inside .editor/. Direct writes are
  silently ignored — placeholder content is never treated as real state.
  All document mutations must go through the MCP write tools listed above.

Document editing workflow (follow this order every editing session):
  Step 1 — Orient: read_file(".editor/cells.json") to load the full cell array.
           Optionally read ".editor/session.json" for mood / metadata context.
  Step 2 — Analyse: digest content, then share observations or draft proposals
           with the user before making any changes.
  Step 3 — Mutate via MCP write tools only (each requires human confirmation):
           write_segment / delete_segment / insert_widget / reply_to_comment
  Step 4 — Verify: after confirmation, re-read updated cells to confirm the change.
</workspace_context>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_workspace_context_block(cwd: str, editor_session_id: str = "") -> str:
    """Return the formatted ``<workspace_context>`` text block for *cwd*.

    Args:
        cwd:               Absolute path to the agent's working directory for this session.
                           Typically the value resolved by ``get_or_create_workspace``.
        editor_session_id: The document session ID from ``/api/sessions`` (``user_sessions.id``).
                           This is distinct from the workspace directory name (which may be
                           the Claude thread ID or a different workspace identifier).
                           Must be provided explicitly — it is NOT derived from *cwd*.

    Returns:
        A ``<workspace_context>…</workspace_context>`` string ready to be
        wrapped in a Claude content block, or ``""`` when *cwd* is empty.
    """
    if not cwd:
        return ""
    import os  # noqa: PLC0415
    return WORKSPACE_CONTEXT_TEMPLATE.format(
        cwd=cwd,
        editor_session_id=editor_session_id or "(unknown — service layer must provide editor_session_id)",
    )
