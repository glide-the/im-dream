// [Input] ToolUIPart/DynamicToolUIPart from the chat message stream; auth token; API_BASE.
// [Output] confirmToolCall() POST helper, resolveToolName()/isAskUserQuestionPart() classifiers,
//          and resolvePendingToolConfirmation() — the single source of truth for whether a tool
//          part is waiting on a user decision (drives ToolConfirmationDock and the ChatMessageList
//          「待确认」 collapsed-row badge).
// [Pos] tool-confirmation shared utility node in frontend/src/components/chat
// [Sync] 2026-07-20: created for the floating ToolConfirmationDock — confirmation UI moved out of
//        the message list into a dock floating above AIInputDock (design: claude-agent-tool-confirmation-flow.md §8).
import { getToolName, type DynamicToolUIPart, type ToolUIPart } from 'ai';
import { getAuthToken } from '../../contexts/AuthContext';
import { API_BASE } from '../../lib/apiBase';
import { isEditorWriteTool } from './editorWriteTools';

export type AnyToolUIPart = ToolUIPart | DynamicToolUIPart;

const TOOL_COMPLETED_STATES = new Set(['output-available', 'output-error']);
const ASK_USER_TOOL_NAMES = new Set(['askuserquestion', 'ask_user_question', 'ask_user', 'askuser']);

export async function confirmToolCall(
  threadId: string,
  toolCallId: string,
  approved: boolean,
  reason?: string,
  answers?: Record<string, unknown>,
) {
  const response = await fetch(`${API_BASE}/api/claude-agent/tool-confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAuthToken()}` },
    body: JSON.stringify({ thread_id: threadId, tool_call_id: toolCallId, approved, reason, answers }),
  });
  return (await response.json()) as { ok?: boolean; success?: boolean; message?: string };
}

/**
 * Robustly resolve the tool name from a part.
 *
 * History-loaded DynamicToolUIPart objects can lose their `toolName` field after
 * DB serialization. When that happens, the AI SDK's `getToolName()` falls back to
 * stripping the 'tool-' prefix from `type`, yielding 'invocation' instead of the
 * real tool name. This helper retries with a direct field read.
 */
export function resolveToolName(part: AnyToolUIPart): string {
  try {
    const name = getToolName(part);
    if (name && name !== 'invocation') return name;
  } catch {
    // getToolName may throw if the part has an unexpected structure
  }
  const raw = part as unknown as Record<string, unknown>;
  if (typeof raw.toolName === 'string' && raw.toolName) return raw.toolName;
  return '';
}

export function isAskUserQuestionPart(part: AnyToolUIPart): boolean {
  const normalizedType = (part.type ?? '').toLowerCase();
  if (normalizedType === 'tool-askuserquestion') return true;
  const name = resolveToolName(part).toLowerCase();
  return ASK_USER_TOOL_NAMES.has(name) || name.endsWith('__ask_user') || name.endsWith('__askuserquestion');
}

export function isApprovalRequestedPart(part: AnyToolUIPart): boolean {
  const raw = part as unknown as { toolMetadata?: Record<string, unknown> };
  return raw.toolMetadata?.approvalRequested === true;
}

export type PendingConfirmationKind = 'confirm' | 'askuser';

export interface PendingToolConfirmation {
  kind: PendingConfirmationKind;
  partKey: string;
  toolCallId: string;
  toolName: string;
  title?: string;
  input: unknown;
}

/**
 * Decide whether a tool part is currently waiting on a user decision.
 *
 * - completed parts (output-available / output-error) never pend;
 * - parts whose input has not arrived yet never pend (avoid rendering half-parsed
 *   streaming JSON as a form — the dock appears on the next frame);
 * - editor write tools keep their specialized inline EditorWriteApprovalUI and are
 *   excluded from the floating dock;
 * - AskUserQuestion tools always pend as 'askuser' (answers must be collected even
 *   in auto / full-access modes);
 * - everything else pends as 'confirm' when the backend explicitly requested
 *   approval (toolMetadata.approvalRequested) or the session runs in manual mode.
 */
export function resolvePendingToolConfirmation(
  part: AnyToolUIPart,
  toolChoice: string | undefined,
): PendingConfirmationKind | null {
  if (TOOL_COMPLETED_STATES.has(part.state ?? '')) return null;
  const input = 'input' in part ? part.input : undefined;
  if (input === undefined || input === null) return null;
  const toolName = resolveToolName(part);
  if (toolName && isEditorWriteTool(toolName)) return null;
  if (isAskUserQuestionPart(part)) return 'askuser';
  if (isApprovalRequestedPart(part) || toolChoice === 'manual') return 'confirm';
  return null;
}
