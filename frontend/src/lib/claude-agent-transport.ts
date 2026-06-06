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
 *   data: {"type": "tool-input-available",  "toolCallId": "...", "toolName": "...", "input": {...}}
 *   data: {"type": "tool-output-available", "toolCallId": "...", "output": ..., "isError": false}
 *   data: {"type": "tool-approval-request", "toolCallId": "...", "toolName": "...", "input": {...}}
 *   data: {"type": "message-final",         "text": "...", "usage": {...}, "sessionId": "..."}
 *   data: {"type": "finish",                "finishReason": "stop"|"error"}
 *   data: {"type": "error",                 "errorText": "..."}
 *
 * This transport converts those events into the UIMessageChunk objects that
 * @ai-sdk/react's useChat hook expects.
 *
 * Unicode escape sequences (e.g. \u770b\u8d77\u6765) are decoded automatically
 * by JSON.parse() so Chinese characters display correctly.
 */

import { HttpChatTransport, type HttpChatTransportInitOptions, type UIMessage, type UIMessageChunk } from 'ai';

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
  | BackendToolInputAvailable
  | BackendToolOutputAvailable
  | BackendToolApprovalRequest
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
  const events: BackendEvent[] = [];
  const frames = raw.split(/\n\n+/);
  for (const frame of frames) {
    for (const line of frame.split('\n')) {
      if (line.startsWith('data: ')) {
        const json = line.slice('data: '.length).trim();
        if (!json) continue;
        try {
          const parsed = JSON.parse(json) as BackendEvent;
          if (parsed && typeof parsed.type === 'string') {
            events.push(parsed);
          }
        } catch {
          // Ignore malformed JSON lines
        }
      }
    }
  }
  return events;
}

interface ConversionState {
  started: boolean;
  toolInputs: Record<string, unknown>;
}

/**
 * Convert a single backend SSE event into zero or more UIMessageChunk objects.
 *
 * Protocol contract (Pawkeyland-aligned):
 *   - text-start / text-delta(delta) / text-end   replace old text-delta(text) / text-done
 *   - tool-input-start + tool-input-available + tool-output-available  replace old tool-event
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

    case 'tool-input-available': {
      ensureStarted();
      state.toolInputs[event.toolCallId] = event.input;
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
      chunks.push({
        type: 'tool-input-available',
        toolCallId: event.toolCallId,
        toolName: event.toolName,
        input: event.input !== undefined ? event.input : state.toolInputs[event.toolCallId] ?? {},
        dynamic: true,
        toolMetadata: { approvalRequested: true },
      });
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
      throw new Error(event.errorText);
    }
  }

  return chunks;
}

// ---------------------------------------------------------------------------
// Transport class
// ---------------------------------------------------------------------------

export class ClaudeAgentChatTransport<UI_MESSAGE extends UIMessage = UIMessage>
  extends HttpChatTransport<UI_MESSAGE>
{
  constructor(options: HttpChatTransportInitOptions<UI_MESSAGE> = {}) {
    super(options);
  }

  protected processResponseStream(
    stream: ReadableStream<Uint8Array>,
  ): ReadableStream<UIMessageChunk> {
    const decoder = new TextDecoder();
    const conversionState: ConversionState = { started: false, toolInputs: {} };

    return stream.pipeThrough(
      new TransformStream<Uint8Array, UIMessageChunk>({
        transform(chunk, controller) {
          const text = decoder.decode(chunk, { stream: true });
          const events = parseSSEChunk(text);
          for (const event of events) {
            try {
              const uiChunks = convertEvent(event, conversionState);
              for (const uiChunk of uiChunks) {
                controller.enqueue(uiChunk);
              }
            } catch (err) {
              controller.error(err);
              return;
            }
          }
        },
        flush(controller) {
          const remaining = decoder.decode();
          if (remaining) {
            const events = parseSSEChunk(remaining);
            for (const event of events) {
              try {
                const uiChunks = convertEvent(event, conversionState);
                for (const uiChunk of uiChunks) {
                  controller.enqueue(uiChunk);
                }
              } catch (err) {
                controller.error(err);
                return;
              }
            }
          }
        },
      }),
    );
  }
}
