// [Sync] 2026-10-28: bulk catalog reads share in-flight requests per transport and session; settled reads are released.
// [Input] Authenticated Deck catalog endpoint and an optional platform HTTP transport.
// [Output] Existing Deck DTOs and original error behavior.
// [Pos] Shared catalog read owner for Chat, Voice initialization and Deck/Reflections choices.
import type {Deck} from './voiceApi';
import {browserRequestHeaders,getBrowserCsrfToken} from '../lib/browserSession';
import {API_BASE} from '../lib/apiBase';
const catalogReads = new WeakMap<typeof fetch, Map<string, Promise<Deck[]>>>();

export function listDecksWithVoices(transport: typeof fetch = fetch): Promise<Deck[]> {
  let headers: Record<string, string>;
  try { headers = authHeaders(); } catch (error) { return Promise.reject(error); }
  const csrf = headers['x-ink-csrf'];
  let reads = catalogReads.get(transport);
  if (!reads) { reads = new Map(); catalogReads.set(transport, reads); }
  const pending = reads.get(csrf);
  if (pending) return pending;
  const request = (async () => {
    const response = await transport(`${API_BASE}/api/decks/catalog`, { headers, cache: 'no-store' });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Load Agents failed');
    }
    const data = await response.json();
    if (getBrowserCsrfToken() !== csrf) throw new Error('Not authenticated');
    return data.decks as Deck[];
  })().finally(() => { if (reads.get(csrf) === request) reads.delete(csrf); });
  reads.set(csrf, request);
  return request;
}

function authHeaders(): Record<string, string> {
  const csrf=getBrowserCsrfToken();if(!csrf)throw new Error('Not authenticated');
  return {'Content-Type':'application/json',...browserRequestHeaders({},csrf)};
}
