// [Input] Production file proxy URL helpers and current-origin BFF path contract.
// [Output] Stored-key fidelity and removal of historical credential query parameters.
// [Pos] Provider-free pure URL contracts; no filesystem/HTTP/business mutation.
// [Sync] 2026-09-14: embedded files authenticate through Cookie, never URL tokens.
import assert from 'node:assert/strict';
import test from 'node:test';
import { toFileProxyUrl, withStorageAuthToken } from './toFileProxyUrl.ts';

test('stored keys produce same-origin URLs without credentials', () => {
  const key = 'owned/files/image.png';
  assert.equal(toFileProxyUrl(key), '/api/storage/file/' + btoa(key));
});
test('old proxy origin and token queries are removed while business parameters survive', () => {
  assert.equal(withStorageAuthToken('https://old.example/api/storage/file/key?token=private&download=1&access_token=private'), '/api/storage/file/key?download=1');
  assert.equal(withStorageAuthToken('/api/storage/file/key?download=1'), '/api/storage/file/key?download=1');
  assert.equal(withStorageAuthToken('https://example.com/image.png?download=1'), 'https://example.com/image.png?download=1');
});
