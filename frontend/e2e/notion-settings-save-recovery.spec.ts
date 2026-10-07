// [Input] Public Settings entry, real connector/session DTOs and server-confirmed selection/sync errors.
// [Output] Full resource-save/re-read/manual-sync journeys, strict marker/Retry-After boundaries and late-owner rejection.
// [Pos] Isolated technical E2E in frontend/e2e; all selection/sync writes stay in named memory fixtures.
// [Sync] 2026-10-07: cover confirmed saved scope, retained drafts/index, UI-only cooldown and actor/connector ABA cleanup without changing Calendar's 63 cases.
import { expect, test, type Page, type Route } from '@playwright/test';
// @ts-expect-error Playwright's Node modules are outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node modules are outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';
import { CSRF, installFixtures, WEB_BASE } from './fixtures/calendarHarness';

test.use({ channel: 'chrome', locale: 'zh-CN', viewport: { width: 1180, height: 820 } });
test.setTimeout(60_000);
const failures = new WeakMap<Page, () => string[]>();
test.afterEach(async ({ page }, info) => {
  if (info.status !== info.expectedStatus) await info.attach('settings-recovery-surface', { body: await page.screenshot(), contentType: 'image/png' });
  expect(failures.get(page)?.() ?? []).toEqual([]);
});

type Failure = { status: number; code: string; marker?: unknown; retry?: string };
const rule = { enabled: true, interval_minutes: 15, revision: 1 };
function connector(id = 'settings-notion-a', chosen = ['db-old']) {
  return { id, name: 'Notion Resource Connector', platform: 'notion', auth_status: 'authenticated',
    created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-28T10:00:00Z', last_synced_at: '2026-09-28T09:00:00Z',
    current_snapshot_version: 'settings-snapshot-1',
    sources: chosen.map((external_id) => ({ id: `source-${external_id}`, external_id, resource_type: 'notion_database',
      title: external_id === 'db-old' ? '原有成功索引' : '新增范围', sync_status: 'synced', page_count: 2,
      updated_at: '2026-09-28T09:00:00Z', last_synced_at: '2026-09-28T09:00:00Z' })),
    sync_policy: { schema_version: 1, default: rule, desired: rule, effective: rule, status: 'applied',
      last_success_at: '2026-09-28T09:00:00Z', last_attempt_at: '2026-09-28T09:00:00Z',
      next_sync_at: '2026-09-28T09:15:00Z', last_error_code: null, allowed_interval_minutes: [15, 60, 360, 1440] } };
}
const catalog = { schema_version: 5, package_revision: 'settings-recovery-1',
  cli_installation: { status: 'installed', required_version: '0.15.1', install_command: 'npm install -g ntn@0.15.1' },
  mcp_inventory: { status: 'not_integrated', revision: null, read_status: 'not_integrated', write_status: 'not_integrated' },
  skills: [], operations: [] };

async function fixture(page: Page, standalone = false) {
  const base = standalone ? null : await installFixtures(page);
  const errors: string[] = [];
  if (standalone) {
    page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
    page.on('requestfailed', (request) => {
      if (new URL(request.url()).pathname === '/api/connectors' && request.failure()?.errorText === 'net::ERR_ABORTED') return;
      errors.push(`request: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    });
    page.on('console', (message) => {
      const expected = /\/api\/connectors(?:\/[^/]+\/(?:resources\/select|sync))?$/.test(new URL(message.location().url || '/', 'http://fixture/').pathname)
        && /(?:409|502|503)/.test(message.text());
      if (message.type() === 'error' && !expected) errors.push(message.text());
    });
  }
  let current = connector();
  let saveFailure: Failure | null = { status: 409, code: 'NOTION_SYNC_BUSY', marker: true, retry: '120' };
  let syncFailure: Failure | null = { status: 409, code: 'NOTION_SYNC_BUSY', retry: '120' };
  let rereadFailure = false;
  let holdRead = false;
  const held: Route[] = [];
  const calls: string[] = [];
  const saveBodies: Array<Record<string, unknown>> = [];
  let saves = 0, syncs = 0, reads = 0;
  let actor = '20260929';
  await page.route('**/auth/session', (route) => route.fulfill({ json: { user: {
    id: actor, email: 'settings-recovery@example.test', display_name: 'Settings QA', avatar_url: null,
    role: 'user', created_at: '2026-09-01T00:00:00Z' }, csrf_token: CSRF } }));
  const fail = async (route: Route, failure: Failure) => {
    const detail: Record<string, unknown> = { error_code: failure.code };
    if (failure.marker !== undefined) detail.selection_saved = failure.marker;
    await route.fulfill({ status: failure.status, headers: failure.retry === undefined ? {} : { 'Retry-After': failure.retry }, json: { detail } });
  };
  await page.route('**/api/connectors**', async (route) => {
    const request = route.request(), path = new URL(request.url()).pathname;
    calls.push(`${request.method()} ${path}`);
    if (request.method() === 'GET' && path === '/api/connectors') {
      reads += 1;
      if (holdRead) { holdRead = false; held.push(route); return; }
      if (rereadFailure) { rereadFailure = false; await fail(route, { status: 503, code: 'ADMIN_DATA_UNAVAILABLE' }); return; }
      await route.fulfill({ json: { connectors: [current] } }); return;
    }
    if (path === '/api/connectors/notion/capabilities') { await route.fulfill({ json: { catalog } }); return; }
    if (path.endsWith('/databases')) { await route.fulfill({ json: { databases: [
      { database_id: 'db-old', title: '原有成功索引', subtitle: 'Notion 数据库', selected: current.sources.some((source) => source.external_id === 'db-old') },
      { database_id: 'db-new', title: '新增范围', subtitle: 'Notion 数据库', selected: current.sources.some((source) => source.external_id === 'db-new') },
    ] } }); return; }
    if (path.endsWith('/pages')) { await route.fulfill({ json: { pages: [] } }); return; }
    if (path.endsWith('/resources/select') && request.method() === 'POST') {
      expect(request.headers()['x-ink-csrf']).toBe(CSRF);
      saves += 1; const body = request.postDataJSON() as Record<string, unknown>; saveBodies.push(body);
      if (saveFailure?.marker === true || !saveFailure) {
        const ids = (body.selected_databases as Array<string | { database_id: string }>).map((entry) => typeof entry === 'string' ? entry : entry.database_id);
        current = connector(current.id, ids);
      }
      if (saveFailure) await fail(route, saveFailure); else await route.fulfill({ json: { connector: current } });
      return;
    }
    if (path.endsWith('/sync') && request.method() === 'POST') {
      expect(request.headers()['x-ink-csrf']).toBe(CSRF); syncs += 1;
      if (syncFailure) await fail(route, syncFailure);
      else { current = { ...current, last_synced_at: '2026-09-28T12:05:00Z', current_snapshot_version: 'settings-snapshot-2' }; await route.fulfill({ json: { connector: current } }); }
      return;
    }
    errors.push(`unexpected connector request ${request.method()} ${path}`);
    await route.fulfill({ status: 501, json: { detail: 'UNEXPECTED_SETTINGS_E2E_REQUEST' } });
  });
  failures.set(page, () => [...errors, ...(base?.getUnexpected() ?? []).filter((entry) => {
    // These exact server-response console diagnostics belong to injected failures above.
    const injectedResponse = /^console: Failed to load resource: the server responded with a status of (?:409|502|503)\b/.test(entry);
    const canceledOwnedRead = held.length > 0 && entry === `request: net::ERR_ABORTED ${WEB_BASE}/api/connectors`;
    return !injectedResponse && !canceledOwnedRead;
  })]);
  return { calls, saveBodies, reads: () => reads, saves: () => saves, syncs: () => syncs,
    saved: () => current, saveFailure: (value: Failure | null) => { saveFailure = value; },
    syncFailure: (value: Failure | null) => { syncFailure = value; },
    failRead: () => { rereadFailure = true; }, holdRead: () => { holdRead = true; }, held,
    identity: (id: string, chosen = ['db-old']) => { current = connector(id, chosen); },
    actor: (value: string) => { actor = value; },
  };
}

async function openSettings(page: Page) {
  await page.goto(`${WEB_BASE}/story-workspace/settings/resources`);
  await page.getByRole('button').filter({ has: page.getByRole('heading', { name: 'Notion', exact: true }) }).click();
  await expect(page.getByRole('heading', { name: 'Notion CLI', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '重新连接 Notion', exact: true })).toBeEnabled();
}
async function resources(page: Page) {
  await page.getByRole('button', { name: /管理资源范围/ }).click();
  await expect(page.getByRole('heading', { name: '资源范围', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '保存并首次同步', exact: true })).toBeEnabled();
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toBeVisible();
}
async function selectAdditional(page: Page) {
  await page.getByRole('button', { name: /新增范围 Notion 数据库/ }).click();
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'true');
}
async function pauseClock(page: Page) {
  await page.clock.install({ time: new Date('2026-09-28T12:00:00Z') });
  await page.clock.pauseAt(new Date('2026-09-28T12:00:01Z'));
}

test('Settings saved selection then busy sync completes the whole public recovery journey', async ({ page }) => {
  const f = await fixture(page); await openSettings(page); await resources(page); await selectAdditional(page); await pauseClock(page);
  const baseline = f.reads();
  await page.getByRole('button', { name: '保存并首次同步', exact: true }).click();
  await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('资源范围已保存，索引更新未完成。');
  await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('连接器已有同步任务，请稍后重试。');
  await expect(page.getByText('服务器当前范围 2 个', { exact: true })).toBeVisible();
  await expect.poll(f.reads).toBe(baseline + 1); expect(f.saves()).toBe(1); expect(f.syncs()).toBe(0);
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'true');
  const lastSuccess = f.saved().last_synced_at;
  await page.getByRole('button', { name: 'Notion', exact: true }).click();
  await page.getByRole('button', { name: /管理已挂载来源/ }).click();
  await expect(page.getByText('原有成功索引', { exact: true })).toBeVisible();
  const sync = page.getByRole('button', { name: '立即同步', exact: true });
  await expect(sync).toBeDisabled();
  const calls = [...f.calls];
  await page.clock.fastForward(119_000); await expect(sync).toBeDisabled(); expect(f.calls).toEqual(calls);
  await page.clock.fastForward(1_000); await expect(sync).toBeEnabled(); expect(f.calls).toEqual(calls);
  expect(f.saved().last_synced_at).toBe(lastSuccess);
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await resources(page);
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await page.getByRole('button', { name: /管理已挂载来源/ }).click();
  await sync.click(); await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('连接器已有同步任务，请稍后重试。');
  await expect(page.locator('.notion-detail').getByRole('alert')).not.toContainText('资源范围已保存'); await expect(sync).toBeDisabled();
  const busyCalls = [...f.calls]; await page.clock.fastForward(120_000); await expect(sync).toBeEnabled(); expect(f.calls).toEqual(busyCalls);
  f.syncFailure(null); await sync.click(); await expect.poll(f.syncs).toBe(2);
  await expect(page.locator('.notion-detail').getByRole('alert')).toHaveCount(0); await expect(sync).toBeEnabled();
  expect(f.saved().current_snapshot_version).toBe('settings-snapshot-2'); expect(f.saves()).toBe(1);
  expect(f.saveBodies[0].selected_pages).toEqual([]);
});

test('Settings confirmed scope survives first-sync 502 and failed scope re-read', async ({ page }) => {
  const f = await fixture(page); await openSettings(page); await resources(page); await selectAdditional(page);
  f.saveFailure({ status: 502, code: 'NOTION_UPSTREAM_UNAVAILABLE', marker: true }); f.failRead();
  await page.getByRole('button', { name: '保存并首次同步', exact: true }).click();
  await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('资源范围已保存，索引更新未完成。');
  await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('暂时无法重新读取当前范围；本页选择仍保留。');
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'true');
  expect(f.saves()).toBe(1); expect(f.syncs()).toBe(0);
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await page.getByRole('button', { name: '资源链接', exact: true }).click();
  await page.getByRole('button').filter({ has: page.getByRole('heading', { name: 'Notion', exact: true }) }).click(); await resources(page);
  await expect(page.getByText('服务器当前范围 2 个', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await page.getByRole('button', { name: /管理已挂载来源/ }).click();
  await expect(page.getByText('原有成功索引', { exact: true })).toBeVisible();
  f.syncFailure(null); await page.getByRole('button', { name: '立即同步', exact: true }).click();
  await expect.poll(f.syncs).toBe(1); await expect(page.locator('.notion-detail').getByRole('alert')).toHaveCount(0);
});

for (const marker of [undefined, false, 'true']) {
  test(`Settings only boolean true confirms saved scope: ${String(marker)}`, async ({ page }) => {
    const f = await fixture(page); await openSettings(page); await resources(page); await selectAdditional(page);
    f.saveFailure({ status: 409, code: 'NOTION_SYNC_BUSY', marker }); const baseline = f.reads();
    await page.getByRole('button', { name: '保存并首次同步', exact: true }).click();
    await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('保存状态未确认');
    await expect(page.locator('.notion-detail').getByRole('alert')).not.toContainText('范围已保存'); await expect(page.locator('.notion-detail').getByRole('alert')).not.toContainText('服务器范围没有改变');
    await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('button', { name: '保存并首次同步', exact: true })).toBeEnabled();
    expect(f.reads()).toBe(baseline); expect(f.saves()).toBe(1); expect(f.syncs()).toBe(0);
  });
}

test('Settings missing or invalid Retry-After never invents a cooldown or auto retry', async ({ page }) => {
  const f = await fixture(page); await openSettings(page);
  await page.getByRole('button', { name: /管理已挂载来源/ }).click(); const sync = page.getByRole('button', { name: '立即同步', exact: true });
  await pauseClock(page);
  for (const retry of [undefined, 'invalid', '-1', '1.5', '9007199254740992']) {
    f.syncFailure({ status: 409, code: 'NOTION_SYNC_BUSY', retry }); await sync.click();
    await expect(page.locator('.notion-detail').getByRole('alert')).toContainText('连接器已有同步任务，请稍后重试。'); await expect(sync).toBeEnabled();
    const before = [...f.calls]; await page.clock.fastForward(120_000); expect(f.calls).toEqual(before);
  }
  expect(f.syncs()).toBe(5); expect(f.saves()).toBe(0);
});

test('Settings unmount and connector A B A rejects late saved-scope re-read and old cooldown', async ({ page }) => {
  const f = await fixture(page); await openSettings(page); await resources(page); await selectAdditional(page); await pauseClock(page); f.holdRead();
  await page.getByRole('button', { name: '保存并首次同步', exact: true }).click(); await expect.poll(() => f.held.length).toBe(1);
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await page.getByRole('button', { name: '资源链接', exact: true }).click();
  f.identity('settings-notion-b'); await page.getByRole('button').filter({ has: page.getByRole('heading', { name: 'Notion', exact: true }) }).click(); await resources(page);
  await expect(page.getByText('服务器当前范围 1 个', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await page.getByRole('button', { name: '资源链接', exact: true }).click();
  f.identity('settings-notion-a'); await page.getByRole('button').filter({ has: page.getByRole('heading', { name: 'Notion', exact: true }) }).click(); await resources(page);
  const canceled = await f.held[0].fulfill({ json: { connectors: [connector('settings-notion-a', ['db-old', 'db-new'])] } }).then(() => false, () => true);
  await test.info().attach('canceled-old-scope-read', { body: JSON.stringify({ canceled }), contentType: 'application/json' });
  await expect(page.getByText('服务器当前范围 1 个', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'false');
  await expect(page.locator('.notion-detail').getByRole('alert')).toHaveCount(0); await expect(page.getByRole('button', { name: '保存并首次同步', exact: true })).toBeEnabled();
  const before = [...f.calls]; await page.clock.fastForward(120_000); expect(f.calls).toEqual(before);
  expect(f.saves()).toBe(1); expect(f.syncs()).toBe(0);
});

// The normal App unmounts Settings on account changes. This allowed test-only auth
// projection keeps the real leaf mounted to exercise its explicit actor ABA guard.
let server: Awaited<ReturnType<typeof createServer>>;
let standaloneBase: string;
const authModule = `
import { useSyncExternalStore } from 'react';
import { loadBrowserSession } from '/app/_dream/lib/browserSession.ts';
await loadBrowserSession();
const listeners = new Set();
let current = { user: { id: '20260929' }, isAuthenticated: true, isLoading: false };
window.addEventListener('settings-fixture-actor', async (event) => {
 await loadBrowserSession(); current = { ...current, user: { id: event.detail } };
 listeners.forEach(listener => listener());
});
export function useAuth() { return useSyncExternalStore(listener => { listeners.add(listener); return () => listeners.delete(listener); }, () => current); }
`;
const settingsModule = `
import React from 'react'; import { createRoot } from 'react-dom/client';
import '/app/_dream/i18n.ts'; import '/app/_dream/styles/tokens.css';
import ConnectorNotionDetailPage from '/app/_dream/components/dashboard/ConnectorNotionDetailPage.tsx';
createRoot(document.querySelector('#root')).render(React.createElement(ConnectorNotionDetailPage, { onBack: () => {} }));
`;
test.beforeAll(async () => {
  const port = await new Promise<number>((resolve, reject) => {
    const probe = createNetServer(); probe.once('error', reject); probe.listen(0, '127.0.0.1', () => {
      const address = probe.address(); if (!address || typeof address === 'string') { probe.close(); reject(new Error('Missing Settings fixture port')); return; }
      probe.close((error?: Error) => error ? reject(error) : resolve(address.port));
    });
  });
  server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port, strictPort: true }, plugins: [{ name: 'settings-resource-owner-projection', enforce: 'pre',
      configureServer(vite) { vite.middlewares.use(async (request, response, next) => {
        if (request.url !== '/settings-resource-owner') return next();
        response.setHeader('Content-Type', 'text/html'); response.end(await vite.transformIndexHtml('/settings-resource-owner',
          '<html><head><link rel="icon" href="data:,"></head><body><main id="root"></main><script type="module" src="/settings-resource-owner.js"></script></body></html>'));
      }); },
      resolveId(id) { if (id.includes('contexts/AuthContext')) return '\0settings-resource-owner-auth'; return id === '/settings-resource-owner.js' ? '\0settings-resource-owner.js' : null; },
      load(id) { return id === '\0settings-resource-owner.js' ? settingsModule : id === '\0settings-resource-owner-auth' ? authModule : null; },
    }] });
  await server.listen(); standaloneBase = `http://127.0.0.1:${port}/settings-resource-owner`;
});
test.afterAll(async () => { await server?.close(); });

test('Settings mounted actor A B A rejects prior scope response and cooldown owner', async ({ page }) => {
  const f = await fixture(page, true); await page.goto(standaloneBase); await resources(page); await selectAdditional(page); await pauseClock(page); f.holdRead();
  await page.getByRole('button', { name: '保存并首次同步', exact: true }).click(); await expect.poll(() => f.held.length).toBe(1);
  f.actor('20260930'); f.identity('settings-notion-b', ['db-new']); await page.evaluate(() => window.dispatchEvent(new CustomEvent('settings-fixture-actor', { detail: '20260930' })));
  await expect(page.getByText('服务器当前范围 1 个', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '保存并首次同步', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Notion', exact: true }).click();
  await page.getByRole('button', { name: /管理已挂载来源/ }).click();
  await expect(page.getByText('新增范围', { exact: true })).toBeVisible();
  f.actor('20260929'); f.identity('settings-notion-a'); await page.evaluate(() => window.dispatchEvent(new CustomEvent('settings-fixture-actor', { detail: '20260929' })));
  await expect(page.getByText('原有成功索引', { exact: true })).toBeVisible();
  await f.held[0].fulfill({ json: { connectors: [connector('settings-notion-a', ['db-old', 'db-new'])] } }).catch(() => undefined);
  await expect(page.getByText('原有成功索引', { exact: true })).toBeVisible();
  await expect(page.getByText('新增范围', { exact: true })).toHaveCount(0); await expect(page.locator('.notion-detail').getByRole('alert')).toHaveCount(0);
  await page.getByRole('button', { name: 'Notion', exact: true }).click(); await resources(page);
  await expect(page.getByRole('button', { name: /新增范围 Notion 数据库/ })).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByRole('button', { name: '保存并首次同步', exact: true })).toBeEnabled();
  const before = [...f.calls]; await page.clock.fastForward(120_000); expect(f.calls).toEqual(before); expect(f.saves()).toBe(1); expect(f.syncs()).toBe(0);
});
