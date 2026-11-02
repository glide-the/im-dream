// [Input] Original section config prompt-file names, order and labels.
// [Output] The same config fields for Web and native controls.
// [Pos] Presentation metadata only; prompt content, defaults and validation remain server-owned.
// [Sync] 2026-10-29: extract existing labels without changing workflow or tool instructions.
export const PROMPT_FILE_ORDER = [
  'WORKFLOW.md',
  'MEMORY_QUERY_PROMPT.md',
  'MEMORY_Distiller_PROMPT.md',
  'MEMORY_ANSWER_PROMPT.md',
  'DEFAULT_UPDATE_MEMORY_PROMPT.md',
] as const;

export const PROMPT_FILE_LABELS: Record<string, string> = {
  'WORKFLOW.md': 'Analysis Workflow',
  'MEMORY_QUERY_PROMPT.md': 'Signal Query',
  'MEMORY_Distiller_PROMPT.md': 'Distillation Rules',
  'MEMORY_ANSWER_PROMPT.md': 'Output Format',
  'DEFAULT_UPDATE_MEMORY_PROMPT.md': 'Update Rules',
};

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────
