// [Input] Original Chat messages, tool permission display state and localized export labels.
// [Output] Unchanged ordered export blocks and pending-confirmation card DTOs for Web and Native.
// [Pos] Pure share projection; DOM rendering and file transport remain platform-owned.
import {getToolName,isToolUIPart,type DynamicToolUIPart,type ToolUIPart,type UIMessage} from 'ai';
import type {TFunction} from 'i18next';
import {resolvePendingToolConfirmation,resolveToolName,type PendingToolConfirmation} from './toolConfirmation';
import {isEditorWriteTool} from './editorWriteTools';
import {isShellTool,resolveToolInputSummary,summarizeToolInvocation} from './toolInputSummary';
import type {AskUserQuestionInput,QuestionField} from './askUserQuestionModel';

export interface ExportToolBlock {
  kind: 'tool';
  toolName: string;
  title?: string;
  summary?: string;
  status: 'executing' | 'completed' | 'error';
  /** Per-row amber badge label (待确认 / 待回答) when this part awaits a user decision. */
  pendingLabel?: string;
  /** Terminal-card header label (e.g. localized "Terminal" / "Write"). */
  terminalLabel?: string;
  command?: string;
  output?: string;
  outputTruncated?: boolean;
  exitCode?: string | null;
  /** Right-aligned colored status text on the terminal header (Written / Write failed…). */
  statusLabel?: string;
  /** Completed editor-write parts render as a quiet success row instead of a terminal card. */
  isEditorWrite?: boolean;
}

export type ExportBlock =
  | { kind: 'text'; text: string }
  | { kind: 'reasoning'; text: string }
  | ExportToolBlock;

export interface ExportChatMessage {
  role: 'user' | 'assistant';
  blocks: ExportBlock[];
  files: string[];
}

export interface ExportConfirmationQuestionOption {
  label: string;
  description?: string;
}

export interface ExportConfirmationQuestion {
  question: string;
  required?: boolean;
  description?: string;
  options: ExportConfirmationQuestionOption[];
}

export interface ExportPendingConfirmation {
  kind: 'confirm' | 'askuser' | 'sandbox-network' | 'reject-only';
  title: string;
  badge: string;
  /** Mono detail block for the generic confirm variant (command or truncated JSON). */
  detail?: string;
  /** Pre-localized info rows for the sandbox-network variant ("Host: …" / "Network policy: …"). */
  infoRows?: string[];
  questions?: ExportConfirmationQuestion[];
  primaryActionLabel: string;
  secondaryActionLabel: string;
}

export interface ExportImageLabels {
  you: string;
  assistant: string;
  footer: string;
  thinking: string;
  truncated: string;
  workspaceImageUnavailable: string;
}

export interface ExportThreadImageOptions {
  threadId: string;
  title: string;
  messages: ExportChatMessage[];
  labels: ExportImageLabels;
  pendingConfirmation?: ExportPendingConfirmation | null;
}

const TOOL_COMPLETED_STATES = new Set(['output-available', 'output-error']);
const BUILTIN_WRITE_TOOL_NAMES = new Set(['write']);
const REASONING_CHAR_LIMIT = 8000;
const TOOL_OUTPUT_CHAR_LIMIT = 4000;

/** Local mirror of ChatMessageList.getToolOutputText (kept private there). */
function readToolOutputText(part: ToolUIPart | DynamicToolUIPart): string | null {
  if ('output' in part && part.output != null) {
    return typeof part.output === 'string' ? part.output : JSON.stringify(part.output, null, 2);
  }
  if ('error' in part && part.error != null) {
    return typeof part.error === 'string' ? part.error : JSON.stringify(part.error, null, 2);
  }
  return null;
}

/** Local mirror of ChatMessageList.parseTerminalOutput (kept private there). */
function parseTerminalOutput(raw: string): { command: string | null; output: string; exitCode: string | null } {
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

function truncateText(text: string, limit: number): { text: string; truncated: boolean } {
  if (text.length <= limit) {
    return { text, truncated: false };
  }
  return { text: text.slice(0, limit), truncated: true };
}

function toExportToolBlock(
  part: ToolUIPart | DynamicToolUIPart,
  toolChoice: string,
  t: TFunction,
): ExportToolBlock {
  const toolName = resolveToolName(part) || getToolName(part);
  const title = 'title' in part ? (part as { title?: string }).title : undefined;
  const input = 'input' in part ? part.input : undefined;
  const summary = summarizeToolInvocation(toolName, input) || undefined;
  const status: ExportToolBlock['status'] = part.state === 'output-error'
    ? 'error'
    : TOOL_COMPLETED_STATES.has(part.state ?? '')
      ? 'completed'
      : 'executing';

  const pendingKind = resolvePendingToolConfirmation(part, toolChoice);
  const pendingLabel = pendingKind === 'askuser'
    ? t('chat.toolConfirmation.pendingAnswer')
    : pendingKind
      ? t('chat.toolConfirmation.pendingConfirm')
      : undefined;

  const base: ExportToolBlock = { kind: 'tool', toolName, title, summary, status, pendingLabel };

  // Completed editor-write tools render as a quiet success row (their specialized
  // completed card shows file diffs in-app; the image keeps a one-line record).
  if (isEditorWriteTool(toolName) && status !== 'executing') {
    return { ...base, isEditorWrite: true };
  }

  const isWrite = BUILTIN_WRITE_TOOL_NAMES.has(toolName.toLowerCase());
  const outputText = readToolOutputText(part);

  if (isWrite) {
    const value = input && typeof input === 'object' && !Array.isArray(input)
      ? (input as Record<string, unknown>)
      : {};
    const filePath = typeof value.file_path === 'string' ? value.file_path : '';
    const content = typeof value.content === 'string' ? value.content : '';
    const bodyText = content || outputText || '';
    const { text, truncated } = truncateText(bodyText, TOOL_OUTPUT_CHAR_LIMIT);
    return {
      ...base,
      terminalLabel: t('chat.share.write'),
      command: `write ${filePath || 'pending-path'}`,
      output: text || undefined,
      outputTruncated: truncated,
      statusLabel: status === 'error'
        ? t('chat.share.writeFailed')
        : part.state === 'output-available'
          ? t('chat.share.written')
          : t('chat.share.writing'),
    };
  }

  if (status !== 'executing' && outputText) {
    const parsed = parseTerminalOutput(outputText);
    const command = resolveToolInputSummary(input).command || parsed.command || undefined;
    const body = parsed.output || outputText;
    const { text, truncated } = truncateText(body, TOOL_OUTPUT_CHAR_LIMIT);
    return {
      ...base,
      terminalLabel: t('chat.share.terminal'),
      command,
      output: text || undefined,
      outputTruncated: truncated,
      exitCode: parsed.exitCode,
    };
  }

  return base;
}

/** Convert a UIMessage into ordered export blocks; null when nothing exportable remains. */
export function toExportChatMessage(message: UIMessage, toolChoice: string, t: TFunction): ExportChatMessage | null {
  if (message.role !== 'user' && message.role !== 'assistant') {
    return null;
  }
  const blocks: ExportBlock[] = [];
  const files: string[] = [];

  for (const part of message.parts ?? []) {
    if (part.type === 'text') {
      const text = ((part as { text?: string }).text ?? '').trim();
      if (text) {
        blocks.push({ kind: 'text', text });
      }
      continue;
    }
    if (part.type === 'reasoning') {
      const reasoningText = (part as { text?: string }).text ?? '';
      if (reasoningText.trim()) {
        const { text } = truncateText(reasoningText.trim(), REASONING_CHAR_LIMIT);
        blocks.push({ kind: 'reasoning', text });
      }
      continue;
    }
    if (part.type === 'file') {
      const filename = (part as { filename?: string }).filename ?? '';
      if (filename) {
        files.push(filename);
      }
      continue;
    }
    if (message.role === 'assistant' && isToolUIPart(part)) {
      blocks.push(toExportToolBlock(part as ToolUIPart | DynamicToolUIPart, toolChoice, t));
    }
  }

  if (blocks.length === 0 && files.length === 0) {
    return null;
  }
  return { role: message.role, blocks, files };
}

function toExportConfirmationQuestions(input: unknown, t: TFunction): ExportConfirmationQuestion[] {
  const value = (input ?? {}) as AskUserQuestionInput;
  if (Array.isArray(value.questions) && value.questions.length > 0) {
    return value.questions.map((question: QuestionField) => ({
      question: question.question ?? question.label ?? question.header ?? t('chat.askUser.fallbackQuestion'),
      required: question.required === true,
      description: question.description,
      options: (question.options ?? []).map((option) => (
        typeof option === 'string'
          ? { label: option }
          : { label: option.label, description: 'description' in option ? option.description : undefined }
      )),
    }));
  }
  const fallbackQuestion = value.question ?? value.message ?? value.text ?? value.prompt;
  const fallbackOptions = value.options ?? value.choices ?? [];
  if (!fallbackQuestion && fallbackOptions.length === 0) {
    return [];
  }
  return [{
    question: fallbackQuestion ?? t('chat.askUser.fallbackQuestion'),
    options: fallbackOptions.map((option) => ({ label: option })),
  }];
}

/**
 * Build the static bottom card mirroring ToolConfirmationDock for the exported image.
 * Returns null when no confirmation is pending.
 */
export function buildExportPendingConfirmation(
  confirmation: PendingToolConfirmation | null,
  t: TFunction,
): ExportPendingConfirmation | null {
  if (!confirmation) {
    return null;
  }
  const { kind, toolName, input } = confirmation;
  const summaryText = summarizeToolInvocation(toolName, input);
  const unknownTool = t('chat.toolConfirmation.unknownTool');

  if (kind === 'askuser') {
    return {
      kind,
      title: t('chat.toolConfirmation.askUserTitle'),
      badge: t('chat.toolConfirmation.pendingAnswer'),
      questions: toExportConfirmationQuestions(input, t),
      primaryActionLabel: t('chat.toolConfirmation.submit'),
      secondaryActionLabel: t('chat.toolConfirmation.cancel'),
    };
  }

  if (kind === 'sandbox-network') {
    const networkRequest = confirmation.networkRequest ?? null;
    const policyModeText = networkRequest?.policyMode === 'allowlist'
      ? t('chat.toolConfirmation.networkPolicyAllowlist')
      : networkRequest?.policyMode === 'open'
        ? t('chat.toolConfirmation.networkPolicyOpen')
        : networkRequest?.policyMode || unknownTool;
    return {
      kind,
      title: t('chat.toolConfirmation.networkConfirmTitle', { tool: toolName || unknownTool }),
      badge: t('chat.toolConfirmation.pendingApproval'),
      infoRows: [
        t('chat.toolConfirmation.networkHostLabel') + (networkRequest?.host ?? t('chat.toolConfirmation.networkHostUnknown')),
        t('chat.toolConfirmation.networkPolicyLabel') + policyModeText,
      ],
      primaryActionLabel: t('chat.toolConfirmation.approve'),
      secondaryActionLabel: t('chat.toolConfirmation.reject'),
    };
  }

  if (kind === 'reject-only') {
    return {
      kind,
      title: t('chat.toolConfirmation.rejectOnlyTitle'),
      badge: t('chat.toolConfirmation.pendingApproval'),
      detail: t('chat.toolConfirmation.rejectOnlyDescription'),
      primaryActionLabel: t('chat.toolConfirmation.rejectAndContinue'),
      secondaryActionLabel: '',
    };
  }

  const commandText = isShellTool(toolName) ? resolveToolInputSummary(input).command : '';
  let detail = commandText;
  if (!detail && input != null) {
    try {
      const json = JSON.stringify(input);
      detail = json.length > 240 ? `${json.slice(0, 240)}…` : json;
    } catch {
      detail = String(input);
    }
  }
  return {
    kind,
    title: t('chat.toolConfirmation.confirmTitle', { tool: toolName || unknownTool })
      + (summaryText ? t('chat.toolConfirmation.withSummary', { summary: summaryText }) : ''),
    badge: t('chat.toolConfirmation.pendingApproval'),
    detail: detail || undefined,
    primaryActionLabel: t('chat.toolConfirmation.approve'),
    secondaryActionLabel: t('chat.toolConfirmation.reject'),
  };
}

