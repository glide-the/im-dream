// [Sync] 2026-10-07: actor metadata retains true dual day-hit flags for matching upstream timestamps; DTO consistency validation remains unchanged.
// [Sync] 2026-10-07: public metadata DTOs prove actor A→B→A and logout reject late snapshot submissions; test-only auth projection preserves the real Calendar owner.
// [Sync] 2026-10-06: update login/connection copy for selected-date Notion snapshot support.
// [Input] Production CalendarPopup and explicit reactive authentication projection injected by Vite only in this test.
// [Output] Mounted-component auth transitions, default/retained tabs and rejection of late responses.
// [Pos] Provider-free technical contract; the normal App sign-in gate is covered separately by the Next journey.
// [Sync] 2026-10-05: cover auth transitions that the App gate does not expose as a mounted Calendar.
import { expect, test, type Page, type Route } from '@playwright/test';
// @ts-expect-error Playwright Node fixture imports are outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright Node fixture imports are outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chrome', viewport: { width: 1440, height: 900 } });
const diagnostics = new WeakMap<Page, string[]>();
test.afterEach(async ({ page }, info) => {
  const errors = diagnostics.get(page) ?? [];
  await info.attach('calendar-auth-browser-diagnostics', { body: JSON.stringify(errors), contentType: 'application/json' });
  if (info.status !== info.expectedStatus) await info.attach('calendar-auth-surface', { body: await page.screenshot(), contentType: 'image/png' });
  expect(errors).toEqual([]);
});
const authModule = `
  import { useSyncExternalStore } from 'react';
  import { loadBrowserSession, clearBrowserSession } from '/app/_dream/lib/browserSession.ts';
  const listeners = new Set();
  const user = { id: '20260929', display_name: 'Calendar QA' };
  const projection = (authenticated, actor = user) => ({ user: authenticated ? actor : null, isAuthenticated: authenticated,
    isLoading: false, authError: null, logout: async () => {} });
  const authenticated = new URLSearchParams(location.search).get('authenticated') === 'true';
  if (authenticated) await loadBrowserSession(); else clearBrowserSession();
  let current = projection(authenticated);
  window.addEventListener('calendar-fixture-auth', async (event) => {
    const authenticated = typeof event.detail === 'boolean' ? event.detail : event.detail.authenticated;
    const actor = typeof event.detail === 'boolean' ? user : { ...user, id: event.detail.id };
    if (authenticated) await loadBrowserSession(); else clearBrowserSession();
    current = projection(authenticated, actor); listeners.forEach((listener) => listener());
  });
  export function useAuth() { return useSyncExternalStore((listener) => { listeners.add(listener); return () => listeners.delete(listener); }, () => current); }
`;
const calendarModule = `
  import React from 'react';
  import { createRoot } from 'react-dom/client';
  import '/app/_dream/i18n.ts';
  import '/app/_dream/styles/tokens.css';
  import CalendarPopup from '/app/_dream/components/CalendarPopup.tsx';
  createRoot(document.querySelector('#root')).render(React.createElement(CalendarPopup, {
    timezone: 'UTC', initialDateKey: '2026-09-28', onLoadEntry: () => {}, onClose: () => {},
  }));
`;
let server: Awaited<ReturnType<typeof createServer>>;
let base: string;
test.beforeAll(async () => {
  const port = await new Promise<number>((resolve, reject) => {
    const probe = createNetServer(); probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (!address || typeof address === 'string') { probe.close(); reject(new Error('No fixture port')); return; }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
  server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true }, plugins: [{ name: 'calendar-auth-projection', enforce: 'pre',
      configureServer(vite) { vite.middlewares.use(async (request, response, next) => {
        if (!request.url?.startsWith('/calendar-auth?')) return next();
        response.setHeader('Content-Type', 'text/html');
        response.end(await vite.transformIndexHtml('/calendar-auth', '<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/calendar-auth.js"></script></body></html>'));
      }); },
      resolveId(id) { if (id.includes('contexts/AuthContext')) return '\0calendar-auth-projection'; return id === '/calendar-auth.js' ? '\0calendar-auth.js' : null; },
      load(id) { return id === '\0calendar-auth.js' ? calendarModule : id === '\0calendar-auth-projection' ? authModule : null; },
    }] });
  await server.listen(); base = `http://127.0.0.1:${port}/calendar-auth`;
});
test.afterAll(async () => { await server?.close(); });
async function auth(page: import('@playwright/test').Page, authenticated: boolean | { authenticated: boolean; id: string }) {
  await page.evaluate((detail) => window.dispatchEvent(new CustomEvent('calendar-fixture-auth', { detail })), authenticated);
}
test.beforeEach(async ({ page }) => {
  const errors: string[] = []; diagnostics.set(page, errors);
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText ?? '';
    if (/^\/api\/connectors\/[^/]+\/notion\/documents$/.test(new URL(request.url()).pathname) && failure.includes('ERR_ABORTED')) return;
    errors.push(`request: ${failure} ${request.url()}`);
  });
  await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));
  await page.addInitScript(() => localStorage.setItem('ink-language', 'zh'));
  await page.route('**/auth/session', (route) => route.fulfill({ json: {
    user: { id: '20260929', email: 'calendar-auth@example.test', display_name: 'Calendar QA', avatar_url: null,
      role: 'user', created_at: '2026-09-01T00:00:00Z' }, csrf_token: 'c'.repeat(43),
  } }));
  await page.route(/^https?:\/\/[^/]+\/api\//, (route) => route.fulfill({ json: route.request().url().includes('/sessions') ? { sessions: [] }
    : route.request().url().includes('/connectors') ? { connectors: [] } : { tasks: [], triggers: [] } }));
});
test('unauthenticated mount defaults to diary and login retains the selected panel', async ({ page }) => {
  await page.goto(`${base}?authenticated=false`);
  const diary = page.getByRole('tab', { name: '日记', exact: true });
  await expect(diary).toHaveAttribute('aria-selected', 'true'); await expect(page.getByRole('tab')).toHaveCount(2);
  await page.getByRole('tab', { name: 'Notion', exact: true }).click();
  await expect(page.getByText('登录后可连接 Notion 并查看文档。')).toBeVisible();
  await auth(page, true); await expect(page.getByRole('tab')).toHaveCount(3);
  await expect(page.getByRole('tab', { name: 'Notion', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText('连接 Notion 后可查看文档。')).toBeVisible();
});
test('logout removes an unactivated focused task tab and restores a visible keyboard entry', async ({ page }) => {
  const sessions = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/sessions');
  await page.goto(`${base}?authenticated=true`);
  await sessions;
  const diary = page.getByRole('tab', { name: '日记', exact: true }); await diary.click(); await diary.press('ArrowLeft');
  await expect(page.getByRole('tab', { name: '定时任务', exact: true })).toBeFocused();
  await auth(page, false); await expect(page.getByRole('tab')).toHaveCount(2); await expect(diary).toBeFocused();
  await expect(diary).toHaveAttribute('tabindex', '0'); await expect(diary).toHaveAttribute('aria-selected', 'true');
});


test('actor A B A and logout reject late metadata without losing the selected Calendar tab', async ({ page }) => {
  const held: Route[] = []; const calls: string[] = [];
  let title = '旧账户A迟到文档'; let holding = true;
  const metadata = (value: string) => ({ connectorId: 'notion-auth', dateKey: '2026-09-28', todayKey: '2026-09-28',
    timeZone: 'UTC', intervalStart: '2026-09-28T00:00:00Z', intervalEnd: '2026-09-29T00:00:00Z',
    observedAt: '2026-09-28T12:00:00Z', coverage: 'connector_snapshot', snapshotVersion: 'snapshot-auth',
    snapshotFetchedAt: '2026-09-28T10:00:00Z', verificationState: 'not_required', paginationState: 'complete',
    partialReasons: [], candidateCount: 1, retryAfter: null, counts: { created: 1, edited: 0, total: 1 },
    items: [{ pageId: 'actor-page', title: value, emoji: null, url: 'https://www.notion.so/actor-page',
      createdTime: '2026-09-28T08:00:00Z', lastEditedTime: '2026-09-28T08:00:00Z', group: 'created', createdOnDate: true, editedOnDate: true }] });
  await page.route('**/api/connectors', async (route) => {
    calls.push(`${route.request().method()} connectors`);
    await route.fulfill({ json: { connectors: [{ id: 'notion-auth', name: 'Notion', platform: 'notion', auth_status: 'authenticated',
      created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z', current_snapshot_version: 'snapshot-auth', config: {}, sources: [] }] } });
  });
  await page.route('**/api/connectors/notion-auth/notion/documents?*', async (route) => {
    calls.push(`${route.request().method()} documents`);
    if (holding) { held.push(route); return; }
    await route.fulfill({ json: metadata(title) });
  });
  await page.goto(`${base}?authenticated=true`);
  await expect(page.getByRole('button', { name: '← 上个月', exact: true })).toBeFocused();
  const notion = page.getByRole('tab', { name: 'Notion', exact: true }); await notion.click();
  const panel = page.getByRole('tabpanel'); await expect.poll(() => held.length).toBe(1);
  holding = false; title = '账户B当前文档'; await auth(page, { authenticated: true, id: 'calendar-actor-b' });
  await expect(panel.getByText(title, { exact: true })).toBeVisible(); await expect(notion).toHaveAttribute('aria-selected', 'true');
  title = '账户A新请求文档'; await auth(page, { authenticated: true, id: '20260929' });
  await expect(panel.getByText(title, { exact: true })).toBeVisible();
  await held[0].fulfill({ json: metadata('旧账户A迟到文档') }).catch(() => undefined);
  await expect(panel.getByText('旧账户A迟到文档')).toHaveCount(0); await expect(panel.getByText(title, { exact: true })).toBeVisible();
  holding = true; await panel.getByRole('button', { name: '刷新', exact: true }).click(); await expect.poll(() => held.length).toBe(2);
  await auth(page, false); await expect(panel.getByText('登录后可连接 Notion 并查看文档。')).toBeVisible();
  await held[1].fulfill({ json: metadata('登出后迟到文档') }).catch(() => undefined);
  await expect(panel.getByRole('listitem')).toHaveCount(0); await expect(notion).toHaveAttribute('aria-selected', 'true');
  expect(calls.every((call) => call.startsWith('GET '))).toBe(true);
});
