// [Input] MCP editor write tool names and direct/stdio result envelopes.
// [Output] Shared detector, result parser, and session-bound Writing jump intent helpers.
// [Pos] editor-write-tools utility node in frontend/src/components/chat
// [Sync] 2026-07-08: split non-component exports out of EditorWriteApprovalUI to keep Fast Refresh lint clean.
// [Sync] 2026-08-29: unwrap stdio content[].text business results so live and
//        history failure cards preserve the backend's authoritative error state.
// [Sync] 2026-09-01: preserve editor_session_id in completed-write jump intents
//        so Writing can activate the exact persisted note before focusing a cell.

export const EDITOR_WRITE_TOOL_NAMES = new Set([
  'mcp__editor__write_segment',
  'mcp__editor__delete_segment',
  'mcp__editor__insert_widget',
  'mcp__editor__reply_to_comment',
]);

export function isEditorWriteTool(toolName: string): boolean {
  return EDITOR_WRITE_TOOL_NAMES.has(toolName.toLowerCase());
}

export interface EditorWriteResult {
  ok?: boolean;
  cellId?: string;
  commentId?: string;
  reason?: string;
  error?: string;
  recovered?: boolean;
}

export interface EditorJumpToCellDetail {
  cellId: string;
  editorSessionId?: string;
}

function nonEmptyString(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const normalized = value.trim();
  return normalized || undefined;
}

export function resolveEditorWriteJumpTarget(
  toolName: string,
  input: Record<string, unknown>,
  output: EditorWriteResult,
): EditorJumpToCellDetail | null {
  const normalizedToolName = toolName.toLowerCase();
  const cellId = nonEmptyString(output.cellId)
    ?? nonEmptyString(input.cellId)
    ?? (normalizedToolName === 'mcp__editor__reply_to_comment'
      ? nonEmptyString(input.commentId)
      : undefined);
  if (!cellId) return null;

  const editorSessionId = nonEmptyString(input.editor_session_id);
  return editorSessionId ? { cellId, editorSessionId } : { cellId };
}

export function parseEditorJumpToCellDetail(value: unknown): EditorJumpToCellDetail | null {
  if (!value || typeof value !== 'object') return null;
  const detail = value as Record<string, unknown>;
  const cellId = nonEmptyString(detail.cellId);
  if (!cellId) return null;
  const editorSessionId = nonEmptyString(detail.editorSessionId);
  return editorSessionId ? { cellId, editorSessionId } : { cellId };
}

function isEditorWriteResult(value: unknown): value is EditorWriteResult {
  return Boolean(
    value
      && typeof value === 'object'
      && typeof (value as { ok?: unknown }).ok === 'boolean',
  );
}

export function parseEditorWriteResult(value: unknown): EditorWriteResult | null {
  if (isEditorWriteResult(value)) return value;
  if (typeof value === 'string') {
    try {
      const decoded = JSON.parse(value) as unknown;
      return isEditorWriteResult(decoded) ? decoded : null;
    } catch {
      return null;
    }
  }
  if (!value || typeof value !== 'object') return null;
  const content = (value as { content?: unknown }).content;
  if (!Array.isArray(content)) return null;
  for (const item of content) {
    if (!item || typeof item !== 'object') continue;
    const parsed = parseEditorWriteResult((item as { text?: unknown }).text);
    if (parsed) return parsed;
  }
  return null;
}
