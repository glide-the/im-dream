// [Input] Unified share client and public snapshot schema with an isolated HTTP boundary.
// [Output] Stable publication keys, strict output, current status and safe public-URL contracts.
// [Pos] Provider-free technical tests; no database/account/model or normal service is used.
import {test, expect} from '@playwright/test';
import {publishChatShare, getExternalShare, revokeExternalShare, externalShareUrl} from '../externalShareApi';
import {publicShareSnapshot} from '../publicShareSchema';
const id = '22222222-2222-4222-8222-222222222222', key = '11111111-1111-4111-8111-111111111111';
const path = '/share/' + 's'.repeat(43);
const share = {id, kind: 'chat', source_id: 'private-thread', title: 'Conversation', path, status: 'active', source_available: true, created_at: '2026-11-12T00:00:00Z', revoked_at: null};
test('publication uses only the source path and stable request key', async () => {
  const calls: {path: string; body: unknown}[] = [];
  const transport = (async (input, init) => {calls.push({path: String(input), body: JSON.parse(String(init?.body))}); return Response.json({share, path, url: 'https://public.example' + path});}) as typeof fetch;
  const result = await publishChatShare('private thread', key, transport);
  expect(calls).toEqual([{path: '/api/claude-agent/threads/private%20thread/share', body: {request_key: key}}]);
  expect(externalShareUrl(result, 'http://localhost:5173')).toBe('https://public.example' + path);
});
test('status and revocation retain the same server-owned record identity', async () => {
  const calls: string[] = [];
  const transport = (async (input) => {calls.push(String(input)); return Response.json({share: {...share, status: 'revoked', revoked_at: '2026-11-12T00:01:00Z'}});}) as typeof fetch;
  expect((await getExternalShare(id, transport)).status).toBe('revoked');
  expect((await revokeExternalShare(id, key, transport)).status).toBe('revoked');
  expect(calls).toEqual(['/api/shares/' + id, '/api/shares/' + id + '/revoke']);
});
test('public URLs reject credentials, other routes and native loopback fallbacks', () => {
  expect(() => externalShareUrl({path, url: 'https://user:secret@public.example' + path}, 'https://public.example')).toThrow();
  expect(() => externalShareUrl({path: '/api/private', url: null}, 'https://public.example')).toThrow();
  expect(() => externalShareUrl({path, url: null}, 'http://localhost:5173', true)).toThrow('NOTE_SHARE_PUBLIC_URL_REQUIRED');
});
test('public schemas exclude owner metadata and system/tool payloads', () => {
  expect(publicShareSnapshot.safeParse({kind: 'chat', title: 'Conversation', created_at: null, messages: [{role: 'assistant', content: '**hello**'}]}).success).toBe(true);
  expect(publicShareSnapshot.safeParse({kind: 'chat', title: 'Conversation', created_at: null, messages: [{role: 'system', content: 'private'}]}).success).toBe(false);
  expect(publicShareSnapshot.safeParse({kind: 'note', title: 'Note', created_at: null, paragraphs: ['body'], owner_id: 'foreign'}).success).toBe(false);
});
