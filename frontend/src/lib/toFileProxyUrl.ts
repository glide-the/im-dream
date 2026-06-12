// [Input] Runtime API base config and backend storage file endpoint contract.
// [Output] Browser-accessible file proxy URL for stored file keys.
// [Pos] file-proxy-url utility node
// [Sync] 2026-06-12: prefix file proxy URLs with centralized API base for cross-origin deployments.
import { apiUrl } from './apiBase';

export function toFileProxyUrl(storageKey: string): string {
  const encoded = typeof globalThis.btoa === 'function' ? globalThis.btoa(storageKey) : storageKey;
  return apiUrl('/api/storage/file/' + encoded);
}
