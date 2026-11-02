// [Input] Original Chat tool DTOs, terminal text and partial Write inputs.
// [Output] Unchanged tool state/output, terminal and editor-result projections shared by Web and Native.
// [Pos] Presentation-only extraction from ChatMessageList; no tool execution, approval or persistence ownership.
import type {DynamicToolUIPart,ToolUIPart} from 'ai';
import {parseEditorWriteResult,type EditorWriteResult as EditorWriteOutput} from './editorWriteTools';
import {parsePartialInputJson} from './toolInputSummary';
export type ToolStatus='executing'|'completed'|'error';
const TOOL_COMPLETED_STATES=new Set(['output-available','output-error']);
export function getToolStatus(part: ToolUIPart | DynamicToolUIPart, isLoading: boolean): ToolStatus {
  if (part.state === 'output-error') return 'error';
  if (TOOL_COMPLETED_STATES.has(part.state ?? '')) return 'completed';
  return isLoading ? 'executing' : 'completed';
}

export function getToolOutputText(part: ToolUIPart | DynamicToolUIPart): string | null {
  if ('output' in part && part.output != null) return typeof part.output === 'string' ? part.output : JSON.stringify(part.output, null, 2);
  if ('error' in part && part.error != null) return typeof part.error === 'string' ? part.error : JSON.stringify(part.error, null, 2);
  if ('errorText' in part && typeof part.errorText === 'string') return part.errorText;
  return null;
}

export function getEditorWriteOutput(part: ToolUIPart | DynamicToolUIPart, isError: boolean): EditorWriteOutput {
  if ('output' in part) {
    const parsed = parseEditorWriteResult(part.output);
    if (parsed) return parsed;
  }
  if (isError) {
    const errorText = getToolOutputText(part) ?? '';
    const parsed = parseEditorWriteResult(errorText);
    if (parsed) return parsed;
    return { ok: false, error: errorText || 'editor_write_failed' };
  }
  return {};
}

export function parseTerminalOutput(raw: string): { command: string | null; output: string; exitCode: string | null } {
  const lines = raw.split('\n');
  let command: string | null = null;
  let exitCode: string | null = null;
  const outputLines: string[] = [];

  lines.forEach((line) => {
    const commandMatch = line.match(/^\$\s+(.+)/);
    const exitMatch = line.match(/^Exit code:\s*(\d+)/i);
    if (commandMatch && !command) command = commandMatch[1];
    else if (exitMatch) exitCode = exitMatch[1];
    else outputLines.push(line);
  });

  return { command, output: outputLines.join('\n').trim(), exitCode };
}


const BUILTIN_WRITE_TOOL_NAMES = new Set(['write']);

export function isBuiltInWriteTool(toolName: string): boolean {
  return BUILTIN_WRITE_TOOL_NAMES.has(toolName.toLowerCase());
}

export function readToolInput(part: ToolUIPart | DynamicToolUIPart): unknown {
  return 'input' in part ? part.input : undefined;
}

export function resolveWriteInput(input: unknown): { filePath: string; content: string; partialJson: string } {
  const partial = parsePartialInputJson(input);
  const value =
    input && typeof input === 'object' && !Array.isArray(input)
      ? { ...partial, ...(input as Record<string, unknown>) }
      : partial;
  return {
    filePath: typeof value.file_path === 'string' ? value.file_path : '',
    content: typeof value.content === 'string' ? value.content : '',
    partialJson: typeof value._partialInputJson === 'string' ? value._partialInputJson : '',
  };
}


export function imageFailureMessage(value: unknown): string {
  if (typeof value === 'string') {
    try {
      const parsed: unknown = JSON.parse(value);
      return parsed && typeof parsed === 'object' && 'message' in parsed && typeof parsed.message === 'string' ? parsed.message : '';
    } catch { return value; }
  }
  return value && typeof value === 'object' && 'message' in value && typeof value.message === 'string' ? value.message : '';
}


export const WRITE_PREVIEW_COLLAPSE_CHAR_LIMIT=1800;
export const WRITE_PREVIEW_COLLAPSE_LINE_LIMIT=24;
