/**
 * [Input]  Pawkeyland-aligned Claude Agent SSE event shapes.
 * [Output] parseClaudeAgentSseBuffer, applyBackendEventToMessages, consumeClaudeAgentSseStream.
 * [Pos]    shared SSE helpers in frontend/src/lib
 * [Sync]   2026-06-09: extracted from claude-agent-transport for thread SSE reconnect.
 * [Sync]   2026-06-09: add consumeClaudeAgentSseStream with incremental frame buffering.
 */

import { isToolUIPart, type UIMessage } from 'ai';

export type BackendEvent = {
  type: string;
  [key: string]: unknown;
};

export function drainClaudeAgentSseFrames(buffer: string): {
  buffer: string;
  frames: string[];
} {
  const parts = buffer.split('\n\n');
  return {
    buffer: parts.pop() ?? '',
    frames: parts.filter((frame) => frame.trim() && !frame.startsWith(':')),
  };
}

export function parseClaudeAgentSseBuffer(raw: string): BackendEvent[] {
  const events: BackendEvent[] = [];
  const frames = raw.split(/\n\n+/);
  for (const frame of frames) {
    for (const line of frame.split('\n')) {
      if (!line.startsWith('data: ')) continue;
      const json = line.slice('data: '.length).trim();
      if (!json) continue;
      try {
        const parsed = JSON.parse(json) as BackendEvent;
        if (parsed && typeof parsed.type === 'string') {
          events.push(parsed);
        }
      } catch {
        // ignore malformed frames
      }
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

function appendReasoningDelta(parts: UIMessage['parts'], id: string, delta: string): UIMessage['parts'] {
  const next = [...parts];
  const idx = next.findIndex((p) => p.type === 'reasoning' && (p as { id?: string }).id === id);
  if (idx >= 0) {
    const part = next[idx] as { type: 'reasoning'; id: string; text: string };
    next[idx] = { ...part, text: `${part.text}${delta}` };
    return next;
  }
  next.push({ type: 'reasoning', id, text: delta });
  return next;
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
      const id = String(event.id ?? 'reasoning');
      const delta = String(event.delta ?? '');
      base[index] = { ...target, parts: appendReasoningDelta(parts, id, delta) };
      return base;
    }
    case 'tool-input-available':
    case 'tool-approval-request': {
      const toolCallId = String(event.toolCallId ?? '');
      const toolName = String(event.toolName ?? 'tool');
      const existing = parts.findIndex(
        (p) => isToolUIPart(p) && p.toolCallId === toolCallId,
      );
      const invocation = {
        type: 'tool-invocation' as const,
        toolCallId,
        toolName,
        state: 'call' as const,
        input: event.input ?? {},
        dynamic: true as const,
        ...(event.type === 'tool-approval-request'
          ? { toolMetadata: { approvalRequested: true } }
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
    case 'tool-output-available': {
      const toolCallId = String(event.toolCallId ?? '');
      const idx = parts.findIndex(
        (p) => isToolUIPart(p) && p.toolCallId === toolCallId,
      );
      if (idx >= 0) {
        const prev = parts[idx] as Extract<UIMessage['parts'][number], { type: 'tool-invocation' }>;
        parts[idx] = {
          ...prev,
          state: event.isError ? 'output-error' : 'output-available',
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
  if (sseBuffer.trim() && !sseBuffer.startsWith(':')) {
    dispatchBuffer(`${sseBuffer}\n\n`);
  }
}
