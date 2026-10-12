// [Input] Actual HTTP transport and synthetic public pre-SSE responses.
// [Output] Safe typed model-selection failures and unchanged unrelated HTTP/SSE behavior.
// [Pos] Isolated transport regression; no browser, normal service or model.
// [Sync] 2026-10-10: preserve the concrete 409 identity reported by the normal Chat route.
import { expect, test } from '@playwright/test';
import { ClaudeAgentChatTransport, ClaudeAgentTransportError, readClaudeAgentErrorCode } from '../claude-agent-transport';

const request = {
  trigger: 'submit-message' as const, chatId: 'owned-fixture', messageId: undefined, abortSignal: undefined,
  messages: [{ id: 'user-1', role: 'user' as const, parts: [{ type: 'text' as const, text: 'Hello' }] }],
};

for (const code of ['GATEWAY_MODEL_SELECTION_STALE', 'GATEWAY_MODEL_SELECTION_CONFLICT']) {
  test(`HTTP ${code} reaches the existing typed UI error boundary without upstream text`, async () => {
    let calls = 0;
    const transport = new ClaudeAgentChatTransport({ fetch: async () => {
      calls++;
      return Response.json({ detail: { error_code: code, message: 'private upstream text' } }, { status: 409 });
    } });
    const error = await transport.sendMessages(request).catch((value: unknown) => value);
    expect(error).toBeInstanceOf(ClaudeAgentTransportError);
    expect(readClaudeAgentErrorCode(error)).toBe(code);
    expect((error as Error).message).not.toContain('private upstream');
    expect(calls).toBe(1);
  });
}

test('an unrelated conflict retains the existing HTTP failure behavior', async () => {
  const transport = new ClaudeAgentChatTransport({ fetch: async () =>
    Response.json({ detail: { error_code: 'CHAT_INPUT_USE_QUEUE' } }, { status: 409 }) });
  const error = await transport.sendMessages(request).catch((value: unknown) => value);
  expect(error).toBeInstanceOf(Error);
  expect(readClaudeAgentErrorCode(error)).toBeNull();
});

test('successful text SSE still passes through the same decoder', async () => {
  const frames = [
    { type: 'text-start', id: 'text-1' }, { type: 'text-delta', id: 'text-1', delta: 'OK' },
    { type: 'text-end', id: 'text-1' }, { type: 'finish', finishReason: 'stop' },
  ].map(event => `data: ${JSON.stringify(event)}\n\n`).join('');
  const transport = new ClaudeAgentChatTransport({ fetch: async () =>
    new Response(frames, { headers: { 'content-type': 'text/event-stream' } }) });
  const reader = (await transport.sendMessages(request)).getReader();
  const chunks = [];
  for (;;) { const next = await reader.read(); if (next.done) break; chunks.push(next.value); }
  expect(chunks).toContainEqual({ type: 'text-delta', id: 'text-1', delta: 'OK' });
  expect(chunks).toContainEqual({ type: 'finish', finishReason: 'stop' });
});
