/**
 * Custom ChatTransport for the /api/claude-agent SSE endpoint.
 *
 * The backend emits a custom SSE protocol:
 *   data: {"type": "text-delta",     "text": "..."}
 *   data: {"type": "text-done",      "text": "..."}
 *   data: {"type": "tool-event",     "tool_name": "...", "tool_call_id": "...", "state": "...", ...}
 *   data: {"type": "tool-approval-request", "toolCallId": "...", "toolName": "...", "input": {...}}
 *   data: {"type": "message-metadata", "sessionId": "...", "turnIndex": 0}
 *   data: {"type": "message-final",  "text": "...", "usage": {...}}
 *   data: {"type": "finish",         "reason": "success"|"error"}
 *   data: {"type": "error",          "message": "..."}
 *
 * This transport converts those events into the UIMessageChunk objects that
 * @ai-sdk/react's useChat hook expects.
 *
 * Unicode escape sequences (e.g. \u770b\u8d77\u6765) are decoded automatically
 * by JSON.parse() so Chinese characters display correctly.
 */

import { HttpChatTransport, type HttpChatTransportInitOptions, type UIMessage, type UIMessageChunk } from 'ai';

// ---------------------------------------------------------------------------
// Backend event shapes
// ---------------------------------------------------------------------------

interface BackendTextDelta {
  type: 'text-delta';
  text: string;
}

interface BackendTextDone {
  type: 'text-done';
  text: string;
}

interface BackendToolEvent {
  type: 'tool-event';
  tool_name: string;
  tool_call_id: string;
  state: 'input-available' | 'input-streaming' | 'output-available' | 'output-error' | 'error';
  input?: unknown;
  output?: unknown;
  is_error?: boolean;
  title?: string;
  provider_executed?: boolean;
}

interface BackendToolApprovalRequest {
  type: 'tool-approval-request';
  toolCallId: string;
  toolName: string;
  input?: unknown;
}

interface BackendMessageMetadata {
  type: 'message-metadata';
  sessionId: string;
  turnIndex: number;
}

interface BackendMessageFinal {
  type: 'message-final';
  text: string;
  usage?: unknown;
  sessionId?: string;
}

interface BackendFinish {
  type: 'finish';
  reason: 'success' | 'error';
}

interface BackendError {
  type: 'error';
  message: string;
}

type BackendEvent =
  | BackendTextDelta
  | BackendTextDone
  | BackendToolEvent
  | BackendToolApprovalRequest
  | BackendMessageMetadata
  | BackendMessageFinal
  | BackendFinish
  | BackendError;

// ---------------------------------------------------------------------------
// Stream conversion
// ---------------------------------------------------------------------------

const TEXT_PART_ID = 'text-0';

/**
 * Parse raw SSE text into an array of BackendEvent objects.
 * Each SSE frame is separated by a blank line; lines beginning with
 * "data: " carry the JSON payload.
 */
function parseSSEChunk(raw: string): BackendEvent[] {
  const events: BackendEvent[] = [];
  // Split by double newline to get individual SSE frames
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

/**
 * Convert a single backend event into zero or more UIMessageChunk objects.
 *
 * @param event - The parsed backend SSE event.
 * @param state - Mutable state bag shared across all events in one stream.
 */
function convertEvent(
  event: BackendEvent,
  state: { started: boolean; textStarted: boolean },
): UIMessageChunk[] {
  const chunks: UIMessageChunk[] = [];

  // Helper: emit start + start-step once before any content
  const ensureStarted = () => {
    if (!state.started) {
      chunks.push({ type: 'start' });
      chunks.push({ type: 'start-step' });
      state.started = true;
    }
  };

  switch (event.type) {
    case 'text-delta': {
      ensureStarted();
      if (!state.textStarted) {
        chunks.push({ type: 'text-start', id: TEXT_PART_ID });
        state.textStarted = true;
      }
      chunks.push({ type: 'text-delta', id: TEXT_PART_ID, delta: event.text });
      break;
    }

    case 'text-done': {
      if (state.textStarted) {
        chunks.push({ type: 'text-end', id: TEXT_PART_ID });
        state.textStarted = false;
      }
      break;
    }

    case 'tool-event': {
      ensureStarted();
      const { tool_call_id: toolCallId, tool_name: toolName, state: toolState } = event;
      switch (toolState) {
        case 'input-available':
          chunks.push({
            type: 'tool-input-start',
            toolCallId,
            toolName,
            dynamic: true,
            ...(event.title ? { title: event.title } : {}),
            ...(event.provider_executed !== undefined ? { providerExecuted: event.provider_executed } : {}),
          });
          chunks.push({
            type: 'tool-input-available',
            toolCallId,
            toolName,
            input: event.input,
            dynamic: true,
          });
          break;

        case 'input-streaming':
          chunks.push({
            type: 'tool-input-delta',
            toolCallId,
            inputTextDelta:
              typeof event.input === 'string' ? event.input : JSON.stringify(event.input),
          });
          break;

        case 'output-available':
          chunks.push({
            type: 'tool-output-available',
            toolCallId,
            output: event.output,
            dynamic: true,
          });
          break;

        case 'output-error':
        case 'error':
          chunks.push({
            type: 'tool-output-error',
            toolCallId,
            errorText:
              typeof event.output === 'string' ? event.output : JSON.stringify(event.output ?? ''),
            dynamic: true,
          });
          break;
      }
      break;
    }

    case 'tool-approval-request': {
      ensureStarted();
      const { toolCallId, toolName } = event;
      chunks.push({
        type: 'tool-input-start',
        toolCallId,
        toolName,
        dynamic: true,
      });
      chunks.push({
        type: 'tool-input-available',
        toolCallId,
        toolName,
        input: event.input,
        dynamic: true,
      });
      break;
    }

    case 'message-metadata':
      chunks.push({
        type: 'message-metadata',
        messageMetadata: { sessionId: event.sessionId, turnIndex: event.turnIndex },
      });
      break;

    case 'message-final':
      // Close any open text part then close the step
      if (state.textStarted) {
        chunks.push({ type: 'text-end', id: TEXT_PART_ID });
        state.textStarted = false;
      }
      chunks.push({ type: 'finish-step' });
      break;

    case 'finish':
      chunks.push({
        type: 'finish',
        finishReason: event.reason === 'success' ? 'stop' : 'error',
      });
      break;

    case 'error':
      // Surfaces as a stream error; useChat will capture it via its error state.
      throw new Error(event.message);
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
    const conversionState = { started: false, textStarted: false };

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
          // Flush any remaining decoder bytes (no-op for UTF-8 SSE text)
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
