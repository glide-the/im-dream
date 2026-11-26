// [Input] One local Writing document's explicit clipboard or PNG export request.
// [Output] Validated share intents and request-bound completion/cancellation receipts.
// [Pos] Native presentation boundary; no network origin, local path or opaque file handle is accepted.
export type WritingShareRequest = {requestId: string} & ({kind: 'copy'; text: string} | {kind: 'images'; images: {base64: string; name: string}[]});
export interface WritingShareResult {requestId: string; status: 'completed' | 'cancelled' | 'failed'}
export function isWritingShareRequest(value: unknown): value is WritingShareRequest {
  if (!value || typeof value !== 'object') return false;
  const item = value as Record<string, unknown>;
  if (typeof item.requestId !== 'string' || !item.requestId) return false;
  if (item.kind === 'copy') {
    if (typeof item.text !== 'string') return false;
    try {const url = new URL(item.text); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && /^\/share\/[A-Za-z0-9_-]{43}$/.test(url.pathname) && !url.search && !url.hash;} catch {return false;}
  }
  return item.kind === 'images' && Array.isArray(item.images) && item.images.length > 0 && item.images.every(image => image && typeof image === 'object' && typeof image.base64 === 'string' && /^[A-Za-z0-9+/]+={0,2}$/.test(image.base64) && typeof image.name === 'string' && /^[^/\\]+\.png$/i.test(image.name) && Array.from(image.name as string).every(character => character.charCodeAt(0) >= 32 && character.charCodeAt(0) !== 127));
}
export function isWritingShareResult(value: unknown): value is WritingShareResult {
  if (!value || typeof value !== 'object') return false;
  const item = value as Record<string, unknown>;
  return typeof item.requestId === 'string' && Boolean(item.requestId) && ['completed', 'cancelled', 'failed'].includes(String(item.status));
}
