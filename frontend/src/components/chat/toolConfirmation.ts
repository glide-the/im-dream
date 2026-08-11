// [Input] ToolUIPart/DynamicToolUIPart from the chat message stream; auth token; API_BASE.
// [Output] confirmToolCall() POST helper, resolveToolName()/isAskUserQuestionPart() classifiers,
//          and resolvePendingToolConfirmation() — the single source of truth for whether a tool
//          part is waiting on a user decision (drives ToolConfirmationDock and the ChatMessageList
//          「待确认」 collapsed-row badge).
// [Pos] tool-confirmation shared utility node in frontend/src/components/chat
// [Sync] 2026-07-20: created for the floating ToolConfirmationDock — confirmation UI moved out of
//        the message list into a dock floating above AIInputDock (design: claude-agent-tool-confirmation-flow.md §8).
// [Sync] 2026-07-23: SandboxPermissionRequest — add the 'sandbox-network' PendingConfirmationKind
//        driven by toolMetadata.confirmationKind==='sandbox_network' plus the
//        resolveSandboxNetworkRequest() helper (design: claude-agent-sandbox-network-permission-tool.md §5A).
// [Sync] 2026-07-26: drop the optional `source` field — the PreToolUse gate was removed;
//        can_use_tool (runtime sandbox proxy) is the single network-confirmation channel.
import { getToolName, type DynamicToolUIPart, type ToolUIPart, type UIMessage } from 'ai';
import { getAuthToken } from '../../contexts/AuthContext';
import { API_BASE } from '../../lib/apiBase';
import { isEditorWriteTool } from './editorWriteTools';

export type AnyToolUIPart = ToolUIPart | DynamicToolUIPart;

const THREAD_LIFECYCLES = new Set(['idle', 'running', 'destroyed', 'not_found']);
const MAX_TOOL_CONFIRMATION_SNAPSHOT_IDS = 256;
const MAX_TOOL_CALL_ID_LENGTH = 255;

export interface ChatThreadStatusResult {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
  pending_tool_call_ids: string[];
  tool_confirmation_observation: 'known' | 'unknown';
}

/** Load persisted history before sampling ephemeral runtime ownership.
 * This order prevents an earlier known-empty status from settling a pending
 * tool part that finishes persistence while history is still loading. */
export async function loadChatHistoryThenRuntimeStatus<T>(
  loadHistory: () => Promise<T>,
  loadStatus: () => Promise<ChatThreadStatusResult | null>,
): Promise<{ history: T; status: ChatThreadStatusResult | null }> {
  let history = await loadHistory();
  const status = await loadStatus();
  // A turn can finish after the first history read but before the status read.
  // Once idle is observed, persistence is stable; read once more so opening
  // Chat from Dream cannot miss the just-completed assistant turn and then
  // skip SSE reconnect because the runtime is already idle.
  if (status?.lifecycle === 'idle') {
    history = await loadHistory();
  }
  return { history, status };
}

/** Parse the runtime confirmation snapshot without converting malformed data
 * into an authoritative empty observation. */
export function parseChatThreadStatus(payload: unknown): ChatThreadStatusResult | null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const raw = payload as Record<string, unknown>;
  if (typeof raw.running !== 'boolean'
    || typeof raw.lifecycle !== 'string'
    || !THREAD_LIFECYCLES.has(raw.lifecycle)
    || !Number.isInteger(raw.turn_count)
    || (raw.turn_count as number) < 0
    || !Array.isArray(raw.pending_tool_call_ids)
    || raw.pending_tool_call_ids.length > MAX_TOOL_CONFIRMATION_SNAPSHOT_IDS
    || (raw.tool_confirmation_observation !== 'known'
      && raw.tool_confirmation_observation !== 'unknown')) {
    return null;
  }
  const pendingIds = raw.pending_tool_call_ids;
  if (pendingIds.some((item) => (
    typeof item !== 'string' || item.length === 0 || item.length > MAX_TOOL_CALL_ID_LENGTH
  )) || new Set(pendingIds).size !== pendingIds.length) {
    return null;
  }
  const lifecycle = raw.lifecycle as ChatThreadStatusResult['lifecycle'];
  if (raw.running !== (lifecycle === 'running')) return null;
  if (lifecycle !== 'running'
    && (raw.tool_confirmation_observation !== 'known' || pendingIds.length > 0)) {
    return null;
  }
  if (raw.tool_confirmation_observation === 'unknown' && pendingIds.length > 0) return null;
  return {
    running: raw.running,
    lifecycle,
    turn_count: raw.turn_count as number,
    pending_tool_call_ids: [...pendingIds] as string[],
    tool_confirmation_observation: raw.tool_confirmation_observation,
  };
}

/** Build exact tombstones for historical tool calls that the runtime no
 * longer owns. Unknown observations deliberately settle nothing. */
export function deriveSettledToolCallIdsFromHistory(
  messages: readonly UIMessage[],
  status: ChatThreadStatusResult | null,
): ReadonlySet<string> {
  if (status?.tool_confirmation_observation !== 'known') return new Set<string>();
  const runtimePending = new Set(status.pending_tool_call_ids);
  const settled = new Set<string>();
  for (const message of messages) {
    for (const part of message.parts ?? []) {
      const toolCallId = (part as { toolCallId?: unknown }).toolCallId;
      if (typeof toolCallId === 'string'
        && toolCallId.length > 0
        && toolCallId.length <= MAX_TOOL_CALL_ID_LENGTH
        && !runtimePending.has(toolCallId)) {
        settled.add(toolCallId);
      }
    }
  }
  return settled;
}

/** Return the exact runtime-owned confirmation identities from a trusted
 * status observation. */
export function runtimePendingToolCallIdsFromStatus(
  status: ChatThreadStatusResult | null,
): ReadonlySet<string> {
  return status?.tool_confirmation_observation === 'known'
    ? new Set(status.pending_tool_call_ids)
    : new Set<string>();
}

const TOOL_COMPLETED_STATES = new Set(['output-available', 'output-error']);
const ASK_USER_TOOL_NAMES = new Set(['askuserquestion', 'ask_user_question', 'ask_user', 'askuser']);

export type ToolConfirmationRequestResult =
  | { readonly state: 'resolved'; readonly approved: boolean }
  | { readonly state: 'not-pending' }
  | { readonly state: 'error'; readonly message: string };

function readToolConfirmationError(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return 'Tool confirmation failed.';
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  return 'Tool confirmation failed.';
}

/** Decode only the typed stale-state conflict; ownership and other errors stay errors. */
export function interpretToolConfirmationResponse(
  status: number,
  payload: unknown,
  expectedToolCallId?: string,
): ToolConfirmationRequestResult {
  if (status >= 200 && status < 300 && payload && typeof payload === 'object') {
    const value = payload as { ok?: unknown; success?: unknown; approved?: unknown };
    if (value.ok === true || value.success === true) {
      return { state: 'resolved', approved: value.approved === true };
    }
  }
  if (status === 409 && payload && typeof payload === 'object') {
    const detail = (payload as { detail?: unknown }).detail;
    if (detail && typeof detail === 'object'
      && (detail as { code?: unknown }).code === 'TOOL_CONFIRMATION_NOT_PENDING'
      && (expectedToolCallId === undefined
        || (detail as { tool_call_id?: unknown }).tool_call_id === expectedToolCallId)) {
      return { state: 'not-pending' };
    }
  }
  return { state: 'error', message: readToolConfirmationError(payload) };
}

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
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // A malformed response is a transport error, never evidence of settlement.
  }
  return interpretToolConfirmationResponse(response.status, payload, toolCallId);
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

/**
 * SandboxPermissionRequest metadata attached by the backend when the CLI's
 * sandbox-runtime proxy blocks a network egress to a non-allowlisted host
 * (delivered via the SDK can_use_tool channel as "SandboxNetworkAccess").
 * Mirrors the runner's confirmation payload `networkRequest` block.
 */
export interface SandboxNetworkRequestInfo {
  host: string | null;
  policyMode: string;
  matchedAllowedDomain: string | null;
}

export const SANDBOX_NETWORK_CONFIRMATION_KIND = 'sandbox_network';

/** Return the sandbox network request metadata when the backend marked this
 * part as a SandboxPermissionRequest confirmation; null otherwise. */
export function resolveSandboxNetworkRequest(part: AnyToolUIPart): SandboxNetworkRequestInfo | null {
  const raw = part as unknown as { toolMetadata?: Record<string, unknown> };
  const metadata = raw.toolMetadata;
  if (metadata?.confirmationKind !== SANDBOX_NETWORK_CONFIRMATION_KIND) return null;
  const networkRequest = metadata.networkRequest;
  if (!networkRequest || typeof networkRequest !== 'object') return null;
  const info = networkRequest as Record<string, unknown>;
  return {
    host: typeof info.host === 'string' ? info.host : null,
    policyMode: typeof info.policyMode === 'string' ? info.policyMode : '',
    matchedAllowedDomain: typeof info.matchedAllowedDomain === 'string' ? info.matchedAllowedDomain : null,
  };
}

export type PendingConfirmationKind = 'confirm' | 'askuser' | 'sandbox-network';

export interface PendingToolConfirmation {
  kind: PendingConfirmationKind;
  partKey: string;
  toolCallId: string;
  toolName: string;
  title?: string;
  input: unknown;
  /** Present only when kind === 'sandbox-network'. */
  networkRequest?: SandboxNetworkRequestInfo | null;
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
 * - network requests the backend flagged with confirmationKind 'sandbox_network'
 *   pend as 'sandbox-network' (host/policy-mode network-variant card);
 * - everything else pends as 'confirm' when the runtime snapshot owns the ID,
 *   the backend explicitly requested approval (toolMetadata.approvalRequested),
 *   or the session runs in manual mode.
 */
export function resolvePendingToolConfirmation(
  part: AnyToolUIPart,
  toolChoice: string | undefined,
  settledToolCallIds: ReadonlySet<string> = new Set<string>(),
  runtimePendingToolCallIds: ReadonlySet<string> = new Set<string>(),
): PendingConfirmationKind | null {
  if (settledToolCallIds.has(part.toolCallId)) return null;
  if (TOOL_COMPLETED_STATES.has(part.state ?? '')) return null;
  const input = 'input' in part ? part.input : undefined;
  if (input === undefined || input === null) return null;
  const toolName = resolveToolName(part);
  if (toolName && isEditorWriteTool(toolName)) return null;
  if (isAskUserQuestionPart(part)) return 'askuser';
  if (isApprovalRequestedPart(part) && resolveSandboxNetworkRequest(part)) return 'sandbox-network';
  if (runtimePendingToolCallIds.has(part.toolCallId)) return 'confirm';
  if (isApprovalRequestedPart(part) || toolChoice === 'manual') return 'confirm';
  return null;
}
