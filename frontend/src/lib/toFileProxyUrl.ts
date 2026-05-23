export function toFileProxyUrl(storageKey: string): string {
  const encoded = typeof globalThis.btoa === 'function' ? globalThis.btoa(storageKey) : storageKey;
  return '/api/storage/file/' + encoded;
}
