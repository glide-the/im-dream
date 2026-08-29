// [Input] MCP editor write tool names and direct/stdio result envelopes.
// [Output] Shared detector and display-only Editor result envelope parser.
// [Pos] editor-write-tools utility node in frontend/src/components/chat
// [Sync] 2026-07-08: split non-component exports out of EditorWriteApprovalUI to keep Fast Refresh lint clean.
// [Sync] 2026-08-29: unwrap stdio content[].text business results so live and
//        history failure cards preserve the backend's authoritative error state.

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
