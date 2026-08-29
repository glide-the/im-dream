// [Input] Running Vite frontend plus production-shaped intercepted Notion connector and MCP summary DTOs.
// [Output] Verify server-owned partial state, unavailable-placeholder removal, localized detail copy, and dialog-free disconnect.
// [Pos] Provider-free Notion Settings browser journey; it never calls Notion, a real backend, or business data.
// [Sync] 2026-08-29: initial focused wide-viewport interaction and browser-diagnostic contract.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chrome', viewport: { width: 1180, height: 820 } });

test('Notion Settings shows partial availability and disconnects without a confirmation dialog', async ({ page }) => {
  const applicationDiagnostics: string[] = [];
  const harnessDiagnostics: string[] = [];
  let deleteRequests = 0;
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (text.includes('WebSocket connection to') || text.includes('[vite] failed to connect')) {
      harnessDiagnostics.push(text);
    } else {
      applicationDiagnostics.push(text);
    }
  });
  page.on('pageerror', (error) => applicationDiagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')) {
      applicationDiagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  const connector = {
    id: 'connector-1',
    name: 'Notion Resource Connector',
    platform: 'notion',
    auth_status: 'authenticated',
    created_at: '2026-08-29T00:00:00Z',
    updated_at: '2026-08-29T00:05:00Z',
    last_synced_at: '2026-08-29T00:04:00Z',
    config: {
      auth_error: 'The new authorization attempt expired.',
      auth_session: { auth_session_status: 'expired' },
    },
    sources: [{
      id: 'source-1',
      external_id: 'database-1',
      resource_type: 'notion_database',
      title: 'Team Knowledge',
      sync_status: 'synced',
      updated_at: '2026-08-29T00:04:00Z',
      last_synced_at: '2026-08-29T00:04:00Z',
    }],
    sync_policy: {
      schema_version: 1,
      default: { enabled: true, interval_minutes: 15, revision: 1 },
      desired: { enabled: true, interval_minutes: 15, revision: 1 },
      effective: { enabled: true, interval_minutes: 15, revision: 1 },
      status: 'applied',
      last_attempt_at: '2026-08-29T00:05:00Z',
      last_success_at: '2026-08-29T00:04:00Z',
      next_sync_at: '2026-08-29T00:19:00Z',
      last_error_code: null,
      allowed_interval_minutes: [15, 60, 360, 1440],
    },
  };

  await page.route(`${WEB_BASE}/notion-connector-settings-harness`, async (route) => {
    await route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/notionConnectorSettingsHarness.tsx"></script></body></html>',
    });
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (request.method() === 'GET' && path === '/api/connectors') {
      await route.fulfill({ json: { connectors: [connector] } });
      return;
    }
    if (request.method() === 'GET' && path.endsWith('/databases')) {
      await route.fulfill({ json: { databases: [] } });
      return;
    }
    if (request.method() === 'GET' && path.endsWith('/pages')) {
      await route.fulfill({ json: { pages: [] } });
      return;
    }
    if (request.method() === 'DELETE' && path === '/api/connectors/connector-1') {
      deleteRequests += 1;
      await route.fulfill({ json: { deleted: true } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/claude-mcp/capability') {
      await route.fulfill({
        json: {
          enabled: true,
          reason_code: null,
          management_mode: 'managed_db',
          schema_capability: 'dream.managed-mcp-resources.v1',
          schema_version: 1,
          transports: ['streamable_http', 'sse', 'stdio'],
        },
      });
      return;
    }
    if (request.method() === 'GET' && path === '/api/claude-mcp/servers') {
      await route.fulfill({ json: { servers: [] } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: `unexpected ${request.method()} ${path}` } });
  });

  let dialogCount = 0;
  page.on('dialog', async (dialog) => {
    dialogCount += 1;
    await dialog.dismiss();
  });

  await page.goto(`${WEB_BASE}/notion-connector-settings-harness`);
  await expect.poll(async () => JSON.stringify({
    body: await page.locator('body').innerText(),
    diagnostics: applicationDiagnostics,
  })).toContain('资源链接');
  await expect(page.getByRole('heading', { name: '资源链接', exact: true })).toBeVisible();
  await expect(page.getByText('部分可用', { exact: true })).toBeVisible();
  await expect(page.getByText('飞书', { exact: true })).toHaveCount(0);
  await expect(page.getByText('CLI 执行器', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: /Notion/ }).click();

  await expect(page.getByRole('heading', { name: 'Notion Resource Connector' })).toBeVisible();
  await expect(page.getByText(/当前已生效的授权仍可使用；需要更新权限时请重新授权。/)).toBeVisible();
  await expect(page.getByText('当前 Notion 授权没有返回可选择的数据库或页面。')).toBeVisible();
  await expect(page.getByText('data_source or page')).toHaveCount(0);

  await page.getByRole('button', { name: '关闭连接' }).click();
  await expect.poll(() => deleteRequests).toBe(1);
  expect(dialogCount).toBe(0);
  await expect(page.getByText('连接后可选择当前账号下允许 Chat 使用的数据库和页面。')).toBeVisible();
  expect(applicationDiagnostics).toEqual([]);
  expect(harnessDiagnostics.every((item) => item.includes('WebSocket') || item.includes('[vite]'))).toBe(true);
});
