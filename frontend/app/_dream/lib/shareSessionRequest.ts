// [Input] Browser session, transport and a key for an equivalent in-progress request.
// [Output] Shared promise scoped to the originating session and transport.
// [Pos] Deduplicates concurrent requests while preserving fresh reads after settlement.
import { BrowserSessionError, getBrowserCsrfToken } from './browserSession';

export function createSessionRequestShare<T>() {
  const pendingByTransport = new WeakMap<typeof fetch, Map<string, Promise<T>>>();

  return function shareSessionRequest(transport: typeof fetch, key: string, request: () => Promise<T>): Promise<T> {
    const session = getBrowserCsrfToken();
    const assertSession = () => {
      if (session !== getBrowserCsrfToken()) throw new BrowserSessionError(401, 'Please log in again.');
    };
    const requestKey = JSON.stringify([session, key]);
    let pending = pendingByTransport.get(transport);
    if (!pending) {
      pending = new Map();
      pendingByTransport.set(transport, pending);
    }
    const existing = pending.get(requestKey);
    if (existing) return existing;
    const requests = pending;
    const result = Promise.resolve().then(() => {
      assertSession();
      return request();
    }).then(value => {
      assertSession();
      return value;
    }).finally(() => requests.delete(requestKey));
    requests.set(requestKey, result);
    return result;
  };
}
