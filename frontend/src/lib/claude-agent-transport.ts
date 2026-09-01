/**
 * [Input]  /api/claude-agent SSE stream (Pawkeyland-aligned protocol).
 * [Output] UIMessageChunk stream consumed by @ai-sdk/react useChat.
 * [Pos]    transport adapter in frontend/src/lib
 * [Sync]   2026-05-24: initial implementation with old protocol (text-delta.text,
 *                      tool-event.state, finish.reason, error.message).
 * [Sync]   2026-05-24: full rewrite to match Pawkeyland-aligned SSE protocol:
 *                      text-start/text-delta(delta)/text-end, separate tool-input-start /
 *                      tool-input-available / tool-output-available events, finish.finishReason,
 *                      error.errorText. Mirrors backend service.py AgentStreamingCallbacks.
 * [Sync]   2026-05-24: add reasoning-start/reasoning-delta/reasoning-end event handling
 *                      for thinking mode (emitted by on_tool_event thinking_delta/thinking
 *                      branches in service.py).
 * [Sync]   2026-06-06: map tool-approval-request to toolMetadata.approvalRequested
 *                      so auto-mode backend confirmations render frontend approval UI.
 * [Sync]   2026-06-13: map tool-input-delta SSE frames to AI SDK 6
 *                      tool-input-delta chunks for built-in Write previews.
 * [Sync]   2026-07-20: forward plan-mode-changed / plan-updated lifecycle frames to the
 *                      useThreadPlan store without mapping them to UIMessageChunks
 *                      (claude-plan.md §5.4: 不收集，不产生消息气泡).
 * [Sync]   2026-07-20: forward todo-updated lifecycle frames to the useThreadTodos
 *                      store without mapping them to UIMessageChunks
 *                      (claude-todo.md §5.4: 不收集，不产生消息气泡).
 * [Sync]   2026-07-23: SandboxPermissionRequest — pass confirmationKind /
 *                      networkRequest from tool-approval-request through to
 *                      toolMetadata so ToolConfirmationDock can render the
 *                      network-variant confirmation card
 *                      (claude-agent-sandbox-network-permission-tool.md §5).
 * [Sync]   2026-08-31: preserve structured Agent errorCode/retryability for safe UI mapping.
 * [Sync]   2026-09-01: end the single-assistant POST response at a persisted
 *                      auto-repair user boundary; reconnect continues the same EventBus.
 * [Sync]   2026-09-01: expose server-authored error text only through the
 *                      typed transport error so known UI codes can render a
 *                      safe structured terminal reason.
 *
 * Custom ChatTransport for the /api/claude-agent SSE endpoint.
 *
 * The backend emits a Pawkeyland-aligned SSE protocol:
 *   data: {"type": "message-metadata",      "sessionId": "...", "turnIndex": 0}
 *   data: {"type": "text-start",            "id": "..."}
 *   data: {"type": "text-delta",            "id": "...", "delta": "..."}
 *   data: {"type": "text-end",              "id": "..."}
 *   data: {"type": "reasoning-start",       "id": "..."}
 *   data: {"type": "reasoning-delta",       "id": "...", "delta": "..."}
 *   data: {"type": "reasoning-end",         "id": "..."}
 *   data: {"type": "tool-input-start",      "toolCallId": "...", "toolName": "..."}
 *   data: {"type": "tool-input-delta",      "toolCallId": "...", "toolName": "...", "delta": "..."}
 *   data: {"type": "tool-input-available",  "toolCallId": "...", "toolName": "...", "input": {...}}
 *   data: {"type": "tool-output-available", "toolCallId": "...", "output": ..., "isError": false}
 *   data: {"type": "tool-approval-request", "toolCallId": "...", "toolName": "...", "input": {...}}
 *   data: {"type": "chat-message",         "message": {"id": "...", "role": "user", "parts": [...], "metadata": {...}}}
 *   data: {"type": "message-final",         "text": "...", "usage": {...}, "sessionId": "..."}
 *   data: {"type": "finish",                "finishReason": "stop"|"error"}
 *   data: {"type": "error",                 "errorText": "...", "errorCode": "...", "retryable": false}
 *
 * This transport converts those events into the UIMessageChunk objects that
 * @ai-sdk/react's useChat hook expects.
 *
 * Unicode escape sequences (e.g. \u770b\u8d77\u6765) are decoded automatically
 * by JSON.parse() so Chinese characters display correctly.
 */

import { HttpChatTransport, type HttpChatTransportInitOptions, type UIMessage, type UIMessageChunk } from 'ai';
import { applyPlanEvent } from '../hooks/useThreadPlan';
import { applyTodoEvent, type ThreadTodoItem } from '../hooks/useThreadTodos';
import {
  publishStoryWorkspaceOutput,
  type StoryWorkspaceOutputReceipt,
} from './story-workspace-events';
import {
  drainClaudeAgentSseFrames,
  parseClaudeAgentSseBuffer,
} from './claude-agent-sse-utils';

// ---------------------------------------------------------------------------
// Backend event shapes (Pawkeyland-aligned)
// ---------------------------------------------------------------------------

interface BackendMessageMetadata {
  type: 'message-metadata';
  sessionId: string;
  turnIndex?: number;
  [key: string]: unknown;
}

interface BackendTextStart {
  type: 'text-start';
  id: string;
}

interface BackendTextDelta {
  type: 'text-delta';
  id: string;
  delta: string;
}

interface BackendTextEnd {
  type: 'text-end';
  id: string;
}

interface BackendReasoningStart {
  type: 'reasoning-start';
  id: string;
}

interface BackendReasoningDelta {
  type: 'reasoning-delta';
  id: string;
  delta: string;
}

interface BackendReasoningEnd {
  type: 'reasoning-end';
  id: string;
}

interface BackendToolInputStart {
  type: 'tool-input-start';
  toolCallId: string;
  toolName: string;
  title?: string;
  providerExecuted?: boolean;
}

interface BackendToolInputAvailable {
  type: 'tool-input-available';
  toolCallId: string;
  toolName: string;
  input: unknown;
  title?: string;
  providerExecuted?: boolean;
}

interface BackendToolInputDelta {
  type: 'tool-input-delta';
  toolCallId: string;
  toolName?: string;
  delta: string;
}

interface BackendToolOutputAvailable {
  type: 'tool-output-available';
  toolCallId: string;
  output: unknown;
  isError: boolean;
}

interface BackendToolApprovalRequest {
  type: 'tool-approval-request';
  toolCallId: string;
  toolName: string;
  input?: unknown;
  // SandboxPermissionRequest discriminator (claude-agent-sandbox-network-
  // permission-tool.md §5A). Absent for generic confirmations.
  confirmationKind?: string;
  networkRequest?: {
    host: string | null;
    policyMode: string;
    matchedAllowedDomain: string | null;
  };
}

interface BackendPlanModeChanged {
  type: 'plan-mode-changed';
  planMode: 'planning' | 'exited';
  toolCallId?: string;
}

interface BackendPlanUpdated {
  type: 'plan-updated';
  slug: string;
  fileName: string;
  content: string;
  contentBytes: number;
  truncated?: boolean;
  updatedAt?: string;
}

interface BackendTodoUpdated {
  type: 'todo-updated';
  source: 'todo_write' | 'task_v2' | null;
  todos: ThreadTodoItem[];
  truncated?: boolean;
  updatedAt?: string | null;
}

interface BackendStoryWorkspaceOutput extends StoryWorkspaceOutputReceipt {
  type: 'story-workspace-output';
}

interface BackendChatMessage {
  type: 'chat-message';
  message: {
    id: string;
    role: 'user';
    parts: UIMessage['parts'];
    metadata: Record<string, unknown>;
  };
}

interface BackendMessageFinal {
  type: 'message-final';
  text: string;
  usage?: unknown;
  sessionId?: string;
}

interface BackendFinish {
  type: 'finish';
  finishReason: 'stop' | 'error';
}

interface BackendError {
  type: 'error';
  errorText: string;
  errorCode?: string;
  retryable?: boolean;
  retryAfterSeconds?: number;
}

export class ClaudeAgentTransportError extends Error {
  readonly errorCode: string | null;
  readonly retryable: boolean | null;
  readonly retryAfterSeconds: number | null;

  constructor(event: BackendError) {
    super(event.errorText || 'Claude-agent error');
    this.name = 'ClaudeAgentTransportError';
    this.errorCode = typeof event.errorCode === 'string' && event.errorCode
      ? event.errorCode
      : null;
    this.retryable = typeof event.retryable === 'boolean' ? event.retryable : null;
    this.retryAfterSeconds = Number.isInteger(event.retryAfterSeconds)
      ? event.retryAfterSeconds ?? null
      : null;
  }
}

export function readClaudeAgentErrorCode(error: unknown): string | null {
  return error instanceof ClaudeAgentTransportError ? error.errorCode : null;
}

export function readClaudeAgentErrorText(error: unknown): string | null {
  return error instanceof ClaudeAgentTransportError && error.message.trim()
    ? error.message
    : null;
}

type BackendEvent =
  | BackendMessageMetadata
  | BackendTextStart
  | BackendTextDelta
  | BackendTextEnd
  | BackendReasoningStart
  | BackendReasoningDelta
  | BackendReasoningEnd
  | BackendToolInputStart
  | BackendToolInputDelta
  | BackendToolInputAvailable
  | BackendToolOutputAvailable
  | BackendToolApprovalRequest
  | BackendPlanModeChanged
  | BackendPlanUpdated
  | BackendTodoUpdated
  | BackendStoryWorkspaceOutput
  | BackendChatMessage
  | BackendMessageFinal
  | BackendFinish
  | BackendError;

// ---------------------------------------------------------------------------
// Stream conversion
// ---------------------------------------------------------------------------

/**
 * Parse raw SSE text into an array of BackendEvent objects.
 * Each SSE frame is separated by a blank line; lines beginning with
 * "data: " carry the JSON payload.
 */
function parseSSEChunk(raw: string): BackendEvent[] {
  return parseClaudeAgentSseBuffer(raw) as BackendEvent[];
}

interface ConversionState {
  started: boolean;
  toolInputs: Record<string, unknown>;
  toolNames: Record<string, string>;
  settledToolCallIds: Set<string>;
  /** Chat/thread id used to route plan-* lifecycle frames to the plan store. */
  threadId?: string;
}

/**
 * Convert a single backend SSE event into zero or more UIMessageChunk objects.
 *
 * Protocol contract (Pawkeyland-aligned):
 *   - text-start / text-delta(delta) / text-end   replace old text-delta(text) / text-done
 *   - tool-input-start + tool-input-delta + tool-input-available + tool-output-available  replace old tool-event
 *   - finish.finishReason   replaces old finish.reason
 *   - error.errorText       replaces old error.message
 */
function convertEvent(
  event: BackendEvent,
  state: ConversionState,
): UIMessageChunk[] {
  const chunks: UIMessageChunk[] = [];

  const ensureStarted = () => {
    if (!state.started) {
      chunks.push({ type: 'start' });
      chunks.push({ type: 'start-step' });
      state.started = true;
    }
  };

  switch (event.type) {
    // -----------------------------------------------------------------------
    // Text streaming
    // -----------------------------------------------------------------------
    case 'text-start': {
      ensureStarted();
      chunks.push({ type: 'text-start', id: event.id });
      break;
    }

    case 'text-delta': {
      ensureStarted();
      chunks.push({ type: 'text-delta', id: event.id, delta: event.delta });
      break;
    }

    case 'text-end': {
      chunks.push({ type: 'text-end', id: event.id });
      break;
    }

    // -----------------------------------------------------------------------
    // Reasoning / thinking events (thinking mode)
    // -----------------------------------------------------------------------
    case 'reasoning-start': {
      ensureStarted();
      chunks.push({ type: 'reasoning-start', id: event.id });
      break;
    }

    case 'reasoning-delta': {
      ensureStarted();
      chunks.push({ type: 'reasoning-delta', id: event.id, delta: event.delta });
      break;
    }

    case 'reasoning-end': {
      chunks.push({ type: 'reasoning-end', id: event.id });
      break;
    }

    // -----------------------------------------------------------------------
    // Tool events (separate Pawkeyland-style events)
    // -----------------------------------------------------------------------
    case 'tool-input-start': {
      ensureStarted();
      state.toolNames[event.toolCallId] = event.toolName;
      chunks.push({
        type: 'tool-input-start',
        toolCallId: event.toolCallId,
        toolName: event.toolName,
        dynamic: true,
        ...(event.title ? { title: event.title } : {}),
        ...(event.providerExecuted !== undefined ? { providerExecuted: event.providerExecuted } : {}),
      });
      break;
    }

    case 'tool-input-delta': {
      ensureStarted();
      chunks.push({
        type: 'tool-input-delta',
        toolCallId: event.toolCallId,
        inputTextDelta: event.delta,
      });
      break;
    }

    case 'tool-input-available': {
      ensureStarted();
      state.toolInputs[event.toolCallId] = event.input;
      state.toolNames[event.toolCallId] = event.toolName;
      chunks.push({
        type: 'tool-input-available',
        toolCallId: event.toolCallId,
        toolName: event.toolName,
        input: event.input,
        dynamic: true,
      });
      break;
    }

    case 'tool-output-available': {
      ensureStarted();
      if (event.isError) {
        chunks.push({
          type: 'tool-output-error',
          toolCallId: event.toolCallId,
          errorText:
            typeof event.output === 'string'
              ? event.output
              : JSON.stringify(event.output ?? ''),
          dynamic: true,
        });
      } else {
        chunks.push({
          type: 'tool-output-available',
          toolCallId: event.toolCallId,
          output: event.output,
          dynamic: true,
        });
      }
      break;
    }

    // tool-approval-request: tool-input-start/available were already emitted
    // by the backend before this event. Re-emit the input with metadata so
    // the UI can distinguish "waiting for approval" from a normal running tool
    // even when the session is in auto mode.
    case 'tool-approval-request': {
      ensureStarted();
      state.settledToolCallIds.delete(event.toolCallId);
      state.toolNames[event.toolCallId] = event.toolName;
      chunks.push({
        type: 'tool-input-available',
        toolCallId: event.toolCallId,
        toolName: event.toolName,
        input: event.input !== undefined ? event.input : state.toolInputs[event.toolCallId] ?? {},
        dynamic: true,
        toolMetadata: {
          approvalRequested: true,
          // SandboxPermissionRequest pass-through — the dock renders a
          // network-variant card when these are present, and falls back to
          // the generic card when they are absent (backward compatible).
          ...(event.confirmationKind ? { confirmationKind: event.confirmationKind } : {}),
          ...(event.networkRequest ? { networkRequest: event.networkRequest } : {}),
        },
      });
      break;
    }

    // -----------------------------------------------------------------------
    // Plan lifecycle frames (claude-plan.md §5.4)
    // 不收集：plan-* 帧是面板状态而非对话消息，不映射为 UIMessageChunk，
    // 只转发到按 threadId 键控的 plan store（useThreadPlan）。
    // -----------------------------------------------------------------------
    case 'plan-mode-changed':
    case 'plan-updated': {
      if (state.threadId) {
        applyPlanEvent(state.threadId, event);
      }
      break;
    }

    // -----------------------------------------------------------------------
    // Todo lifecycle frames (claude-todo.md §5.4)
    // 不收集：todo-updated 帧是面板状态而非对话消息，不映射为 UIMessageChunk，
    // 只转发到按 threadId 键控的 todos store（useThreadTodos）。
    // -----------------------------------------------------------------------
    case 'todo-updated': {
      if (state.threadId) {
        applyTodoEvent(state.threadId, event);
      }
      break;
    }

    // Structured output is already persisted and scoped by the backend. This
    // frame updates Dream application state and does not create a chat part.
    case 'story-workspace-output': {
      publishStoryWorkspaceOutput(event);
      break;
    }

    // -----------------------------------------------------------------------
    // Session metadata & lifecycle
    // -----------------------------------------------------------------------
    case 'message-metadata': {
      chunks.push({
        type: 'message-metadata',
        messageMetadata: {
          sessionId: event.sessionId,
          turnIndex: event.turnIndex,
        },
      });
      break;
    }

    case 'message-final': {
      chunks.push({ type: 'finish-step' });
      break;
    }

    case 'finish': {
      chunks.push({
        type: 'finish',
        finishReason: event.finishReason === 'stop' ? 'stop' : 'error',
      });
      break;
    }

    case 'error': {
      throw new ClaudeAgentTransportError(event);
    }
  }

  return chunks;
}

// ---------------------------------------------------------------------------
// Transport class
// ---------------------------------------------------------------------------

export interface ClaudeAgentChatTransportInitOptions<UI_MESSAGE extends UIMessage = UIMessage>
  extends HttpChatTransportInitOptions<UI_MESSAGE>
{
  /** Chat/thread id; plan-* SSE frames are forwarded to the plan store under this key. */
  threadId?: string;
}

export class ClaudeAgentChatTransport<UI_MESSAGE extends UIMessage = UIMessage>
  extends HttpChatTransport<UI_MESSAGE>
{
  private readonly threadId?: string;

  constructor(options: ClaudeAgentChatTransportInitOptions<UI_MESSAGE> = {}) {
    const { threadId, ...transportOptions } = options;
    super(transportOptions);
    this.threadId = threadId;
  }

  protected processResponseStream(
    stream: ReadableStream<Uint8Array>,
  ): ReadableStream<UIMessageChunk> {
    const decoder = new TextDecoder();
    const conversionState: ConversionState = {
      started: false,
      toolInputs: {},
      toolNames: {},
      settledToolCallIds: new Set<string>(),
      threadId: this.threadId,
    };
    let sseBuffer = '';

    const dispatch = (
      raw: string,
      controller: TransformStreamDefaultController<UIMessageChunk>,
    ): boolean => {
      const events = parseSSEChunk(raw);
      for (const event of events) {
        if (event.type === 'chat-message') {
          // AI SDK owns one assistant response per POST. Close this reader so
          // ChatPanel hydrates the committed user fact and reconnects to the
          // still-running canonical factory task for the repair response.
          controller.enqueue({ type: 'finish-step' });
          controller.enqueue({ type: 'finish', finishReason: 'stop' });
          controller.terminate();
          return false;
        }
        const uiChunks = convertEvent(event, conversionState);
        for (const uiChunk of uiChunks) {
          controller.enqueue(uiChunk);
        }
      }
      return true;
    };

    return stream.pipeThrough(
      new TransformStream<Uint8Array, UIMessageChunk>({
        transform(chunk, controller) {
          sseBuffer += decoder.decode(chunk, { stream: true });
          const drained = drainClaudeAgentSseFrames(sseBuffer);
          sseBuffer = drained.buffer;
          for (const frame of drained.frames) {
            try {
              if (!dispatch(`${frame}\n\n`, controller)) return;
            } catch (err) {
              controller.error(err);
              return;
            }
          }
        },
        flush(controller) {
          sseBuffer += decoder.decode();
          if (!sseBuffer.trim()) return;
          try {
            dispatch(`${sseBuffer}\n\n`, controller);
          } catch (err) {
            controller.error(err);
          }
        },
      }),
    );
  }
}
