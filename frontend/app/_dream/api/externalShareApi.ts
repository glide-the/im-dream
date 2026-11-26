// [Input] Original Cookie/native transport and strict public-share DTOs.
// [Output] Idempotent publication, owned listing/status/revocation and validated public URLs.
// [Pos] Shared Web/Native share client; no source owner, file key or database credential is caller-selected.
import {z} from 'zod';
import {browserRequestHeaders} from '../lib/browserSession';
const kind = z.enum(['chat', 'note']);
const metadata = z.strictObject({id: z.uuid(), kind, source_id: z.string(), title: z.string(), path: z.string().regex(/^\/share\/[A-Za-z0-9_-]{43}$/),
  status: z.enum(['active', 'revoked']), source_available: z.boolean(), created_at: z.string(), revoked_at: z.string().nullable()});
const cursor = z.strictObject({created_at: z.string(), id: z.uuid()});
const list = z.strictObject({public_origin: z.string().nullable(), shares: z.array(metadata), counts: z.strictObject({chat: z.number().int().nonnegative(), note: z.number().int().nonnegative()}), next_cursor: cursor.nullable()});
const publication = z.strictObject({share: metadata, path: z.string(), url: z.string().nullable()});
export type ExternalShare = z.infer<typeof metadata>;
export type ShareKind = z.infer<typeof kind>;
export type ShareCursor = z.infer<typeof cursor>;
export type SharePage = z.infer<typeof list>;
export type SharePublication = z.infer<typeof publication>;
export class ShareApiError extends Error {constructor(readonly status: number) {super(status === 409 ? 'NOTE_SHARE_CHANGED' : 'SHARE_REQUEST_FAILED');}}
export function newShareRequestKey() {return globalThis.crypto?.randomUUID?.() ?? 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, character => {const value = Math.floor(Math.random() * 16); return (character === 'x' ? value : (value & 3) | 8).toString(16);});}
async function request(path: string, init: RequestInit, transport: typeof fetch, signal?: AbortSignal) {
  const response = await transport(path, {...init, signal, cache: 'no-store', headers: browserRequestHeaders({'Content-Type': 'application/json'})});
  if (!response.ok) throw new ShareApiError(response.status);
  return response.json();
}
export async function publishShare(path: string, body: object, transport: typeof fetch = fetch, signal?: AbortSignal): Promise<SharePublication> {
  const value = publication.parse(await request(path, {method: 'POST', body: JSON.stringify(body)}, transport, signal));
  if (value.path !== value.share.path) throw new Error('SHARE_RESPONSE_INVALID');
  return value;
}
export function publishChatShare(threadId: string, requestKey: string, transport: typeof fetch = fetch, signal?: AbortSignal) {
  return publishShare(`/api/claude-agent/threads/${encodeURIComponent(threadId)}/share`, {request_key: requestKey}, transport, signal);
}
export async function getExternalShare(id: string, transport: typeof fetch = fetch, signal?: AbortSignal) {
  const result = z.strictObject({share: metadata}).parse(await request(`/api/shares/${encodeURIComponent(id)}`, {method: 'GET'}, transport, signal)).share;
  if (result.id !== id) throw Error('SHARE_RESPONSE_INVALID');
  return result;
}
export async function listExternalShares(kind: ShareKind, status: ExternalShare['status'], before: ShareCursor | null = null, transport: typeof fetch = fetch, signal?: AbortSignal, limit = 20): Promise<SharePage> {
  const query = new URLSearchParams({kind, status, limit: String(limit)});
  if (before) {query.set('before_created_at', before.created_at); query.set('before_id', before.id);}
  const result = list.parse(await request('/api/shares?' + query, {method: 'GET'}, transport, signal));
  if (result.shares.some(share => share.kind !== kind || share.status !== status)) throw Error('SHARE_RESPONSE_INVALID');
  return result;
}
export async function revokeExternalShare(id: string, requestKey: string, transport: typeof fetch = fetch, signal?: AbortSignal) {
  const result = z.strictObject({share: metadata}).parse(await request(`/api/shares/${encodeURIComponent(id)}/revoke`, {method: 'POST', body: JSON.stringify({request_key: requestKey})}, transport, signal)).share;
  if (result.id !== id || result.status !== 'revoked') throw Error('SHARE_RESPONSE_INVALID');
  return result;
}
export function externalShareUrl(value: Pick<SharePublication, 'path' | 'url'>, fallbackOrigin: string, requirePublicOrigin = false): string {
  if (!/^\/share\/[A-Za-z0-9_-]{43}$/.test(value.path)) throw new Error('SHARE_RESPONSE_INVALID');
  const url = new URL(value.url ?? value.path, fallbackOrigin);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== value.path || url.hash || url.search) throw new Error('SHARE_RESPONSE_INVALID');
  if (requirePublicOrigin && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) throw new Error('NOTE_SHARE_PUBLIC_URL_REQUIRED');
  return url.href;
}
