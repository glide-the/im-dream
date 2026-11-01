// [Input] Original attachment metadata and stored keys/proxy URLs.
// [Output] Original size labels and Cookie-based file URLs, plus a same-origin native storage path.
// [Pos] File message presentation only; file ownership and byte access remain server/platform owned.
import {toFileProxyUrl,withStorageAuthToken} from '../../lib/toFileProxyUrl';
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function resolveFileUrl(url?: string) {
  if (!url) return undefined;
  if (url.startsWith('/') || url.startsWith('http')) {
    // Persisted proxy URLs carry no credentials; attach the current auth token
    // so <img src> / download links pass backend storage auth.
    return withStorageAuthToken(url);
  }
  if (url.startsWith('blob:') || url.startsWith('data:')) {
    return url;
  }
  return toFileProxyUrl(url);
}

export function messageStoragePath(raw:string,origin:string):string|null {
  const resolved=resolveFileUrl(raw);if(!resolved)return null;
  const local=resolved.startsWith(origin+'/')?resolved.slice(origin.length):resolved;
  const path=local.split(/[?#]/)[0];
  return path.startsWith('/api/storage/file/')&&path.length>'/api/storage/file/'.length?path:null;
}
