/**
 * [Input]  Pawkeyland-aligned Claude Agent SSE event shapes.
 * [Output] parseClaudeAgentSseBuffer, applyBackendEventToMessages, consumeClaudeAgentSseStream.
 * [Pos]    shared SSE helpers in frontend/src/lib
 * [Sync]   2026-06-09: extracted from claude-agent-transport for thread SSE reconnect.
 * [Sync]   2026-06-09: add consumeClaudeAgentSseStream with incremental frame buffering.
 * [Sync]   2026-06-12: emit AI SDK 6 dynamic-tool and reasoning parts during reconnect replay.
 * [Sync]   2026-06-13: replay tool-input-start/delta as input-streaming parts for
 *                      Write terminal previews until final input arrives.
 * [Sync]   2026-07-23: SandboxPermissionRequest — replayed tool-approval-request
 *                      frames also forward confirmationKind / networkRequest into
 *                      toolMetadata (claude-agent-sandbox-network-permission-tool.md §5).
 */

import { getToolName, isToolUIPart, type DynamicToolUIPart, type ToolUIPart, type UIMessage } from 'ai';

export type BackendEvent = {
  type: string;
  [key: string]: unknown;
};

export function drainClaudeAgentSseFrames(buffer: string): {
  buffer: string;
  frames: string[];
} {
  const frames: string[] = [];
  let remaining = buffer;
  const blankLine = /(?:\r\n|\n|\r)(?:\r\n|\n|\r)/;
  let boundary = blankLine.exec(remaining);
  while (boundary?.index !== undefined) {
    frames.push(remaining.slice(0, boundary.index));
    remaining = remaining.slice(boundary.index + boundary[0].length);
    boundary = blankLine.exec(remaining);
  }
  return {
    buffer: remaining,
    frames: frames.filter((frame) => frame.trim()),
  };
}

export function parseClaudeAgentSseBuffer(raw: string): BackendEvent[] {
  const events: BackendEvent[] = [];
  const frames = raw.split(/(?:\r\n|\n|\r){2,}/);
  for (const frame of frames) {
    const dataLines: string[] = [];
    for (const line of frame.split(/\r\n|\n|\r/)) {
      if (!line || line.startsWith(':')) continue;
      const separator = line.indexOf(':');
      const field = separator < 0 ? line : line.slice(0, separator);
      if (field !== 'data') continue;
      let value = separator < 0 ? '' : line.slice(separator + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      dataLines.push(value);
    }
    if (!dataLines.length) continue;
    try {
      const parsed = JSON.parse(dataLines.join('\n')) as BackendEvent;
      if (parsed && typeof parsed.type === 'string') {
        events.push(parsed);
      }
    } catch {
      // Ignore malformed or non-JSON application frames. The caller retains
      // incomplete frames until a blank-line boundary has arrived.
    }
  }
  return events;
}

function ensureAssistantMessage(messages: UIMessage[]): { messages: UIMessage[]; index: number } {
  const next = [...messages];
  const last = next[next.length - 1];
  if (last?.role === 'assistant') {
    return { messages: next, index: next.length - 1 };
  }
  const assistant: UIMessage = {
    id: `reconnect-asst-${Date.now()}`,
    role: 'assistant',
    parts: [],
  };
  next.push(assistant);
  return { messages: next, index: next.length - 1 };
}

function appendTextDelta(parts: UIMessage['parts'], delta: string): UIMessage['parts'] {
  const next = [...parts];
  const last = next[next.length - 1];
  if (last && last.type === 'text') {
    next[next.length - 1] = { ...last, text: `${last.text}${delta}` };
    return next;
  }
  next.push({ type: 'text', text: delta });
  return next;
}

function appendReasoningDelta(parts: UIMessage['parts'], delta: string): UIMessage['parts'] {
  const next = [...parts];
  let idx = -1;
  for (let i = next.length - 1; i >= 0; i -= 1) {
    if (next[i]?.type === 'reasoning') {
      idx = i;
      break;
    }
  }
  if (idx >= 0) {
    const part = next[idx] as Extract<UIMessage['parts'][number], { type: 'reasoning' }>;
    next[idx] = { ...part, text: `${part.text}${delta}` };
    return next;
  }
  next.push({ type: 'reasoning', text: delta, state: 'streaming' });
  return next;
}

function stringifyToolError(output: unknown): string {
  if (typeof output === 'string') return output;
  try {
    return JSON.stringify(output ?? '');
  } catch {
    return String(output);
  }
}

function appendPartialToolInput(input: unknown, delta: string): Record<string, unknown> {
  const current =
    input && typeof input === 'object' && !Array.isArray(input)
      ? (input as Record<string, unknown>)
      : {};
  return {
    ...current,
    _partialInputJson: `${typeof current._partialInputJson === 'string' ? current._partialInputJson : ''}${delta}`,
  };
}

function getToolInput(part: ToolUIPart | DynamicToolUIPart): unknown {
  return 'input' in part ? part.input : undefined;
}

function isEmptyRecord(value: unknown): boolean {
  return Boolean(value)
    && typeof value === 'object'
    && !Array.isArray(value)
    && Object.keys(value as Record<string, unknown>).length === 0;
}

/** Approval frames may omit input (or carry the adapter's empty placeholder).
 * Preserve the already-normalized tool input instead of erasing it on replay. */
function replayToolInput(
  eventType: string,
  eventInput: unknown,
  previous: ToolUIPart | DynamicToolUIPart | undefined,
): unknown {
  const previousInput = previous ? getToolInput(previous) : undefined;
  if (eventType === 'tool-approval-request'
    && previousInput !== undefined
    && (eventInput === undefined || eventInput === null || isEmptyRecord(eventInput))) {
    return previousInput;
  }
  return eventInput ?? previousInput ?? {};
}

export function applyBackendEventToMessages(
  messages: UIMessage[],
  event: BackendEvent,
): UIMessage[] {
  const { messages: base, index } = ensureAssistantMessage(messages);
  const target = base[index];
  const parts = [...(target.parts ?? [])];

  switch (event.type) {
    case 'text-delta': {
      const delta = String(event.delta ?? '');
      base[index] = { ...target, parts: appendTextDelta(parts, delta) };
      return base;
    }
    case 'reasoning-delta': {
      const delta = String(event.delta ?? '');
      base[index] = { ...target, parts: appendReasoningDelta(parts, delta) };
      return base;
    }
    case 'tool-input-start': {
      const toolCallId = String(event.toolCallId ?? '');
      const toolName = String(event.toolName ?? 'tool');
      const existing = parts.findIndex(
        (p) => isToolUIPart(p) && p.toolCallId === toolCallId,
      );
      const invocation: DynamicToolUIPart = {
        type: 'dynamic-tool',
        toolCallId,
        toolName,
        state: 'input-streaming',
        input: undefined,
      };
      if (existing >= 0) {
        parts[existing] = invocation;
      } else {
        parts.push(invocation);
      }
      base[index] = { ...target, parts };
      return base;
    }
    case 'tool-input-available':
    case 'tool-approval-request': {
      const toolCallId = String(event.toolCallId ?? '');
      const toolName = String(event.toolName ?? 'tool');
      const existing = parts.findIndex(
        (p) => isToolUIPart(p) && p.toolCallId === toolCallId,
      );
      const previous = existing >= 0 && isToolUIPart(parts[existing])
        ? parts[existing] as ToolUIPart | DynamicToolUIPart
        : undefined;
      const invocation: DynamicToolUIPart = {
        type: 'dynamic-tool',
        toolCallId,
        toolName,
        state: 'input-available',
        input: replayToolInput(event.type, event.input, previous),
        ...(event.type === 'tool-approval-request'
          ? {
              toolMetadata: {
                approvalRequested: true,
                // SandboxPermissionRequest pass-through (see claude-agent-transport.ts).
                ...(typeof event.confirmationKind === 'string' && event.confirmationKind
                  ? { confirmationKind: event.confirmationKind }
                  : {}),
                ...(event.networkRequest && typeof event.networkRequest === 'object'
                  ? { networkRequest: event.networkRequest }
                  : {}),
              } as DynamicToolUIPart['toolMetadata'],
            }
          : {}),
      };
      if (existing >= 0) {
        parts[existing] = invocation;
      } else {
        parts.push(invocation);
      }
      base[index] = { ...target, parts };
      return base;
    }
    case 'tool-input-delta': {
      const toolCallId = String(event.toolCallId ?? '');
      if (!toolCallId) return messages;
      const idx = parts.findIndex(
        (p) => isToolUIPart(p) && p.toolCallId === toolCallId,
      );
      if (idx >= 0) {
        const prev = parts[idx] as ToolUIPart | DynamicToolUIPart;
        const toolName = getToolName(prev);
        parts[idx] = {
          type: 'dynamic-tool',
          toolCallId,
          toolName,
          state: 'input-streaming',
          input: appendPartialToolInput(getToolInput(prev), String(event.delta ?? '')),
          title: prev.title,
          toolMetadata: prev.toolMetadata,
          providerExecuted: prev.providerExecuted,
        };
        base[index] = { ...target, parts };
      }
      return base;
    }
    case 'tool-output-available': {
      const toolCallId = String(event.toolCallId ?? '');
      const idx = parts.findIndex(
        (p) => isToolUIPart(p) && p.toolCallId === toolCallId,
      );
      if (idx >= 0) {
        const prev = parts[idx] as ToolUIPart | DynamicToolUIPart;
        const input = getToolInput(prev);
        const toolName = getToolName(prev);
        const baseTool = {
          type: 'dynamic-tool',
          toolCallId,
          toolName,
          input,
          title: prev.title,
          toolMetadata: prev.toolMetadata,
          providerExecuted: prev.providerExecuted,
        } satisfies Partial<DynamicToolUIPart> & Pick<DynamicToolUIPart, 'type' | 'toolCallId' | 'toolName'>;
        parts[idx] = event.isError
          ? {
              ...baseTool,
              state: 'output-error',
              errorText: stringifyToolError(event.output),
            }
          : {
              ...baseTool,
              state: 'output-available',
              output: event.output,
            };
        base[index] = { ...target, parts };
      }
      return base;
    }
    default:
      return messages;
  }
}

export async function consumeClaudeAgentSseStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: BackendEvent) => boolean | void,
): Promise<void> {
  const decoder = new TextDecoder();
  let sseBuffer = '';

  const dispatchBuffer = (raw: string) => {
    for (const event of parseClaudeAgentSseBuffer(raw)) {
      const shouldStop = onEvent(event);
      if (shouldStop === false) {
        return false;
      }
    }
    return true;
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    sseBuffer += decoder.decode(value, { stream: true });
    const { buffer, frames } = drainClaudeAgentSseFrames(sseBuffer);
    sseBuffer = buffer;

    for (const frame of frames) {
      if (dispatchBuffer(`${frame}\n\n`) === false) {
        return;
      }
    }
  }

  const tail = decoder.decode();
  if (tail) {
    sseBuffer += tail;
  }
  if (sseBuffer.trim()) {
    dispatchBuffer(`${sseBuffer}\n\n`);
  }
}
