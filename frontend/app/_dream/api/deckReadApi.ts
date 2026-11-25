// [Sync] 2026-11-25: scope catalog reads to the active session across Web Bearer and native Cookie transports.
// [Sync] 2026-11-03: use Kastention / 卡片结构 for Deck display copy; retain existing identifiers, requests and operations.
// [Sync] 2026-10-28: bulk catalog reads share in-flight requests per transport and session; settled reads are released.
// [Input] Authenticated Deck catalog/list/detail endpoints and an optional platform HTTP transport.
// [Output] Existing Deck DTOs and original error behavior.
// [Pos] Deck read owner re-exported by voiceApi; native imports avoid unrelated chat runtime modules.
import type {Deck} from './voiceApi';
import {browserRequestHeaders,getBrowserCsrfToken} from '../lib/browserSession';
import {API_BASE} from '../lib/apiBase';
const catalogReads = new WeakMap<typeof fetch, Map<string, Promise<Deck[]>>>();

export function listDecksWithVoices(transport: typeof fetch = fetch): Promise<Deck[]> {
  let sessionScope: string;
  try { sessionScope = requireSessionScope(); } catch (error) { return Promise.reject(error); }
  let reads = catalogReads.get(transport);
  if (!reads) { reads = new Map(); catalogReads.set(transport, reads); }
  const pending = reads.get(sessionScope);
  if (pending) return pending;
  const request = (async () => {
    const response = await transport(`${API_BASE}/api/decks/catalog`, { headers: authHeaders(sessionScope), cache: 'no-store' });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(typeof error.detail === 'string' ? error.detail : 'Load Agents failed');
    }
    const data = await response.json();
    if (getBrowserCsrfToken() !== sessionScope) throw new Error('Not authenticated');
    return data.decks as Deck[];
  })().finally(() => { if (reads.get(sessionScope) === request) reads.delete(sessionScope); });
  reads.set(sessionScope, request);
  return request;
}

export async function listDecks(transport:typeof fetch=fetch):Promise<Deck[]> {
  const response=await transport(`${API_BASE}/api/decks`,{headers:authHeaders()});
  if(!response.ok){const error=await response.json();throw new Error(error.detail || 'List Kastention failed');}
  const data=await response.json();return data.decks;
}
export async function getDeck(deckId:string,transport:typeof fetch=fetch):Promise<Deck> {
  const response=await transport(`${API_BASE}/api/decks/${deckId}`,{headers:authHeaders()});
  if(!response.ok){const error=await response.json();throw new Error(error.detail || 'Get Kastention failed');}
  return response.json();
}
function requireSessionScope(): string {
  const sessionScope = getBrowserCsrfToken();
  if (!sessionScope) throw new Error('Not authenticated');
  return sessionScope;
}

function authHeaders(sessionScope = requireSessionScope()): Record<string, string> {
  return browserRequestHeaders({ 'Content-Type': 'application/json' }, sessionScope);
}
