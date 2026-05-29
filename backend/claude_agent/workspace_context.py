# [Input] None — self-contained prompt template module.
#         Runtime dependency: libs.claude_agent_kit.server.editor_index.EDITOR_RESOURCES
#         defines the virtual resource names embedded in this template.
# [Output] Provide build_workspace_context_block to ClaudeAgentContextBuilder.build_user_message.
# [Pos] workspace-context-prompt node in backend/claude_agent
# [Sync] 2026-05-28: initial implementation — standalone workspace context prompt
#                    for edit-point context assembly integration.
# [Sync] 2026-05-29: add Document editing workflow section so Agent receives in-message
#                    scheduling guidance alongside the capability inventory.

"""Workspace context prompt for the Ink & Memory Claude Agent.

Produces the ``<workspace_context>`` block that is injected into every user
turn between ``<runtime_context>`` and the user's message text.  The block
tells the agent about:

- the working directory path;
- the workspace directory layout (files/, skills/, logs/, .claude/, .editor/);
- the ``.editor/`` virtual index mechanism and readable virtual paths;
- the read / write path separation rules and the MCP write tools.

The template is intentionally static with respect to ``editor_state`` — it
describes the *mechanism*, not the current document content.  The agent reads
actual document content on demand via ``read_file`` or MCP read tools.

Usage::

    from claude_agent.workspace_context import build_workspace_context_block

    block = build_workspace_context_block(cwd="/workspaces/sess-abc")
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
  read_file(".editor/<resource>.json")             — intercepted; returns live snapshot

Writing document content (all require human confirmation):
  write_segment(cellId, text, reason)              — replace a cell's full text
  delete_segment(cellId, reason)                   — remove a cell (irreversible)
  insert_widget(widgetType, data, afterCellId)     — insert a widget cell
  set_comment_feedback(commentId, feedback)        — update a voice comment rating
  reply_to_comment(commentId, role, content)       — add to a comment thread

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


def build_workspace_context_block(cwd: str) -> str:
    """Return the formatted ``<workspace_context>`` text block for *cwd*.

    Returns an empty string when *cwd* is falsy so callers can safely guard
    with ``if block:`` before appending it to the content-blocks list.

    Args:
        cwd: Absolute path to the agent's working directory for this session.
             Typically the value resolved by ``get_or_create_workspace``.

    Returns:
        A ``<workspace_context>…</workspace_context>`` string ready to be
        wrapped in a Claude content block, or ``""`` when *cwd* is empty.
    """
    if not cwd:
        return ""
    return WORKSPACE_CONTEXT_TEMPLATE.format(cwd=cwd)
