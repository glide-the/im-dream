// [Sync] 2026-10-10: show image prompt and generate/edit labels in existing live/history tool rows.
// [Input] Raw tool input objects from ToolUIPart/DynamicToolUIPart (live stream or history replay), including `_partialInputJson` streaming accumulators.
// [Output] parsePartialInputJson(), resolveToolInputSummary(), summarizeToolInvocation(), isShellTool() — one-line "what is this tool doing" summaries for tool cards/rows.
// [Pos] tool-input-summary utility node in frontend/app/_dream/components/chat
// [Sync] 2026-07-19: created so Terminal cards, collapsed tool rows, and ToolMessagePart headers show the task description (and bash command) instead of only the tool result.

const SHELL_TOOL_NAMES = new Set(['bash', 'terminal', 'shell']);

export function isShellTool(toolName: string): boolean {
  return SHELL_TOOL_NAMES.has(toolName.trim().toLowerCase());
}

export function parsePartialInputJson(input: unknown): Record<string, unknown> {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return {};
  const raw = (input as Record<string, unknown>)._partialInputJson;
  if (typeof raw !== 'string' || !raw.trim()) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

export interface ToolInputSummary {
  /** Human-readable task description emitted by the model (e.g. Bash `description`). */
  description: string;
  /** Shell command for bash/terminal tools. */
  command: string;
  /** Primary target for file/search/web tools (file_path, pattern, query, url…). */
  target: string;
}

export function resolveToolInputSummary(input: unknown): ToolInputSummary {
  const partial = parsePartialInputJson(input);
  const value =
    input && typeof input === 'object' && !Array.isArray(input)
      ? { ...partial, ...(input as Record<string, unknown>) }
      : partial;
  const pick = (...keys: string[]): string => {
    for (const key of keys) {
      const raw = value[key];
      if (typeof raw === 'string' && raw.trim()) return raw.trim();
    }
    return '';
  };
  return {
    description: pick('description', 'prompt'),
    command: pick('command'),
    target: pick('file_path', 'path', 'pattern', 'query', 'url'),
  };
}

/**
 * One-line summary of what a tool invocation is doing:
 * - shell tools prefer the model's task description, then the command itself;
 * - every other tool prefers the task description, then its primary target.
 */
export function summarizeToolInvocation(toolName: string, input: unknown): string {
  const { description, command, target } = resolveToolInputSummary(input);
  if (description) return description;
  if (isShellTool(toolName)) return command;
  return target || command;
}

/** Image actions reuse the ordinary tool row; only the business label changes. */
export function imageToolAction(toolName: string, input: unknown): 'generate' | 'edit' | 'prepare' | null {
  if (toolName === 'mcp__image_gen__select_image_operation') return 'prepare';
  if (toolName !== 'mcp__image_gen__imagegen' && toolName !== 'image_generation') return null;
  const value = input && typeof input === 'object' && !Array.isArray(input) ? input as Record<string, unknown> : {};
  if (toolName === 'image_generation') return value.operation === 'edit' ? 'edit' : value.operation === 'generate' ? 'generate' : null;
  return Array.isArray(value.reference_images) && value.reference_images.length > 0 ? 'edit' : 'generate';
}
