// [Input] Stored file keys/proxy URLs and same-origin storage endpoint contract.
// [Output] Cookie-authenticated file URLs with no OAuth credential query parameters.
// [Pos] Existing file URL helper/import boundary; server retains owner/path validation.
// [Sync] 2026-09-14: remove historical URL tokens and resolve storage proxies at the current Next origin.
import { apiUrl } from './apiBase.ts';

export function toFileProxyUrl(storageKey: string): string {
  const encoded = typeof globalThis.btoa === 'function' ? globalThis.btoa(storageKey) : storageKey;
  return apiUrl('/api/storage/file/' + encoded);
}

// Retain the established helper name for callers while removing retired tokens.
export function withStorageAuthToken(raw: string): string {
  try {
    const url = new URL(raw, 'https://file-proxy.invalid');
    if (!url.pathname.startsWith('/api/storage/file/')) return raw;
    url.searchParams.delete('token'); url.searchParams.delete('access_token');
    return apiUrl(url.pathname + url.search + url.hash);
  } catch { return raw; }
}
