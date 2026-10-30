// [Input] Existing same-origin BFF URLs, DTOs and CSRF headers.
// [Output] Web HTTP responses and incremental text chunks.
// [Pos] Browser platform transport; Metro selects transport.native.ts.
export type OpenResponse = {status: number; chunks: AsyncIterable<string>; cancel: () => void};
export async function openResponse(path: string, init: RequestInit = {}): Promise<OpenResponse> {
  const abort = new AbortController();
  const response = await fetch(path, {...init, credentials: 'include', signal: init.signal ?? abort.signal});
  async function* chunks() {
    const reader = response.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    try {
      while (true) { const next = await reader.read(); if (next.done) break; yield decoder.decode(next.value, {stream: true}); }
      const tail = decoder.decode(); if (tail) yield tail;
    } finally { reader.releaseLock(); }
  }
  return {status: response.status, chunks: chunks(), cancel: () => abort.abort()};
}
export const clientFetch: typeof fetch = fetch;
