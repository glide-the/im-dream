// [Sync] 2026-11-12: declare UTF-8 and resolve isolated native owners before Vite externalization.
// [Sync] 2026-11-12: scope Vite optimization artifacts to this isolated share validation.
// [Sync] 2026-11-12: use the unified public database reader for both content kinds.
// [Input] Production public Next page and native note action adapter, with isolated HTTP/platform owners.
// [Output] Anonymous server reads, escaped text, unavailable-snapshot handling and native cancellation/cleanup evidence.
// [Pos] Provider-free technical contracts; Project/Episode/Artifact/Run/Hook/Thread and normal services are out of scope.
import {test, expect} from '@playwright/test';
import {createServer} from 'vite';
import {renderToStaticMarkup} from 'react-dom/server';
import {fileURLToPath} from 'node:url';
import type {PublicShareSnapshot} from '../app/_dream/api/publicShareSchema';
interface StagedFile {id: string; base64: string; name: string}
interface NativeFixture {copied: string[]; imports: StagedFile[]; exports: string[][]; released: string[]; completed: boolean; failAt: number}
const nativeScope = globalThis as typeof globalThis & {__noteNative?: NativeFixture};
test.use({channel: 'chrome'});

let server: Awaited<ReturnType<typeof createServer>>, base: string, previousOrigin: string | undefined;
const reads: {path: string; authorization?: string; cookie?: string}[] = [];
const token = 's'.repeat(43);
const note: PublicShareSnapshot = {kind: 'note', title: '河边的记录', created_at: '2026-11-12T00:00:00Z', paragraphs: ['第一段\n第二行', '<script>window.bad=true</script>']};
let snapshot: PublicShareSnapshot = note;
test.beforeEach(() => {snapshot = note;});
test.beforeAll(async () => {
  previousOrigin = process.env.INK_BACKEND_INTERNAL_URL;
  server = await createServer({root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, cacheDir: fileURLToPath(new URL('../test-results/external-sharing/cache/note-share-boundaries', import.meta.url)), logLevel: 'silent', server: {host: '127.0.0.1', port: 0},
    ssr: {noExternal: ['react-native']},
    plugins: [{name: 'note-share-boundaries', enforce: 'pre', resolveId(source, importer) {
      if (source === 'react-native') return '\0note-share-native-runtime';
      if (source === './fileUpload.native' && importer?.endsWith('/noteShare.native.ts')) return '\0note-share-native-files';
      return null;
    }, load(id) {
      if (id === '\0note-share-native-runtime') return `export const NativeModules={InkRuntime:{copyText:async text=>{globalThis.__noteNative.copied.push(text)},exportFiles:async ids=>{globalThis.__noteNative.exports.push(ids);return {completed:globalThis.__noteNative.completed}}}};`;
      if (id === '\0note-share-native-files') return `export async function importNativeSketch(base64,name){const f=globalThis.__noteNative;if(f.failAt===f.imports.length)throw Error('synthetic import failure');const id='file-'+f.imports.length;f.imports.push({id,base64,name});return {id}};export function releaseNativeFiles(ids){globalThis.__noteNative.released.push(...ids)}`;
      return null;
    }, configureServer(vite) {vite.middlewares.use(async (req, res, next) => {
      if (req.url?.startsWith('/api/public/shares/')) {
        reads.push({path: req.url, authorization: req.headers.authorization, cookie: req.headers.cookie});
        res.setHeader('Content-Type', 'application/json');
        if (!req.url.endsWith('/' + token)) {res.statusCode = 404; res.end('{}'); return;}
        res.end(JSON.stringify(snapshot)); return;
      }
      if (!req.url?.startsWith('/reader/')) return next();
      try {
        const page = await vite.ssrLoadModule('/app/share/[token]/page.tsx');
        const element = await page.default({params: Promise.resolve({token: req.url.slice('/reader/'.length)})});
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        res.end('<!doctype html><html><head><link rel="icon" href="data:,"></head><body>' + renderToStaticMarkup(element) + '</body></html>');
      } catch (error) {
        if (String((error as {digest?: string}).digest).includes('404')) {res.statusCode = 404; res.end('Note not found');}
        else {res.statusCode = 500; res.end(String(error));}
      }
    });}}]});
  await server.listen(); base = server.resolvedUrls!.local[0]; process.env.INK_BACKEND_INTERNAL_URL = base;
});
test.afterAll(async () => {if (previousOrigin === undefined) delete process.env.INK_BACKEND_INTERNAL_URL; else process.env.INK_BACKEND_INTERNAL_URL = previousOrigin; delete nativeScope.__noteNative; await server?.close();});

test('public page reads without browser credentials and renders markup as literal prose', async ({page}) => {
  reads.length = 0;
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await page.context().addCookies([{name: 'private_session', value: 'synthetic-cookie', url: base}]);
  await page.setExtraHTTPHeaders({authorization: 'Bearer synthetic-browser-token'});
  const response = await page.goto(base + 'reader/' + token);
  expect(response?.status()).toBe(200);
  await expect(page.getByRole('heading', {name: note.title})).toBeVisible();
  await expect(page.getByText('<script>window.bad=true</script>', {exact: true})).toBeVisible();
  await expect(page.getByRole('textbox')).toHaveCount(0);
  expect(await page.evaluate(() => (window as Window & {bad?: unknown}).bad)).toBeUndefined();
  expect(reads).toEqual([{path: '/api/public/shares/' + token, authorization: undefined, cookie: undefined}]);
  expect(errors).toEqual([]);
  const module = await server.ssrLoadModule('/app/share/[token]/page.tsx');
  expect(module.dynamic).toBe('force-dynamic'); expect(module.metadata.robots).toEqual({index: false, follow: false}); expect(module.metadata.referrer).toBe('no-referrer');
});

test('public AI text renders without an account or private workspace references', async ({page}) => {
  reads.length = 0;
  snapshot = {kind: 'chat', title: '共享AI对话', created_at: null, messages: [
    {role: 'user', content: 'Question [private file](workspace://files/a.md) ![private image](workspace://files/a.png)'},
    {role: 'assistant', content: '**Shared answer** and $x^2$'},
  ]};
  const response = await page.goto(base + 'reader/' + token);
  expect(response?.status()).toBe(200);
  await expect(page.getByRole('heading', {name: snapshot.title})).toBeVisible();
  await expect(page.locator('strong')).toHaveText('Shared answer');
  await expect(page.getByRole('link', {name: 'private file'})).toHaveCount(0);
  await expect(page.locator('img')).toHaveCount(0);
  await expect(page.getByRole('textbox')).toHaveCount(0);
  expect(reads).toEqual([{path: '/api/public/shares/' + token, authorization: undefined, cookie: undefined}]);
});

test('missing public snapshot produces the page not-found result', async ({request}) => {
  const response = await request.get(base + 'reader/missing-token'); expect(response.status()).toBe(404);
});

test('native copy and cancelled export use system owners and release every imported handle', async () => {
  const f: NativeFixture = {copied: [] as string[], imports: [] as StagedFile[], exports: [] as string[][], released: [] as string[], completed: false, failAt: -1};
  nativeScope.__noteNative = f;
  const {performNoteShare} = await server.ssrLoadModule('/src/platform/noteShare.native.ts');
  expect(await performNoteShare({requestId: 'copy', kind: 'copy', text: 'https://notes.example/share/' + token}, () => true)).toEqual({requestId: 'copy', status: 'completed'});
  expect(f.copied).toHaveLength(1);
  expect(await performNoteShare({requestId: 'image', kind: 'images', images: [{base64: 'iVBORw==', name: 'note.png'}]}, () => true)).toEqual({requestId: 'image', status: 'cancelled'});
  expect(f.exports).toEqual([['file-0']]); expect(f.released).toEqual(['file-0']);
});

test('native late ownership loss and import failure release staged handles before returning', async () => {
  const f: NativeFixture = {copied: [], imports: [] as StagedFile[], exports: [] as string[][], released: [] as string[], completed: true, failAt: -1};
  nativeScope.__noteNative = f;
  const {performNoteShare} = await server.ssrLoadModule('/src/platform/noteShare.native.ts');
  const images = [{base64: 'iVBORw==', name: 'first.png'}, {base64: 'iVBORw==', name: 'second.png'}];
  expect(await performNoteShare({requestId: 'stale', kind: 'images', images}, () => f.imports.length === 0)).toEqual({requestId: 'stale', status: 'cancelled'});
  expect(f.exports).toEqual([]); expect(f.released).toEqual(['file-0']);
  f.imports = []; f.released = []; f.failAt = 1;
  expect(await performNoteShare({requestId: 'failed', kind: 'images', images}, () => true)).toEqual({requestId: 'failed', status: 'failed'});
  expect(f.exports).toEqual([]); expect(f.released).toEqual(['file-0']);
});


test('the explicit public API bypasses account auth and retains credential-free upstream reads', async () => {
  reads.length = 0;
  const api = await server.ssrLoadModule('/app/api/public/shares/[token]/route.ts');
  const response = await api.GET(new Request('https://public.example/api/public/shares/' + token, {headers: {authorization: 'Bearer visitor', cookie: 'private=visitor'}}), {params: Promise.resolve({token})});
  expect(response.status).toBe(200); expect(await response.json()).toEqual(note);
  expect(response.headers.get('cache-control')).toBe('no-store');
  expect(reads).toEqual([{path: '/api/public/shares/' + token, authorization: undefined, cookie: undefined}]);
  const legacy = await server.ssrLoadModule('/app/api/public/note-shares/[token]/route.ts');
  expect(legacy.GET().status).toBe(404);
});
