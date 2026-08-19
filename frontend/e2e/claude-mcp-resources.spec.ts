// [Input] Running frontend entry point plus production-shaped intercepted Claude MCP and boot API fixtures.
// [Output] Verify Resources → Configure → MCP Login → redirect → Connected → Logout → Remove with auth headers and zero secret persistence.
// [Pos] Provider-free Claude MCP browser journey; it never calls a real OAuth provider, CLI, backend, or business database.
// [Sync] 2026-08-19: cover the complete visible v1 connector journey and responsive layout.
// [Sync] 2026-08-19: cover restricted HTTPS configuration and user-owned removal before real-provider QA.

import { expect, test, type Request as PlaywrightRequest } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

test('Resources completes the provider-free Claude MCP login and logout journey', async ({ page }) => {
  const token = 'claude-mcp-resources-technical-token';
  const serverName = 'e2e-user-server';
  const serverUrl = 'https://mcp.example.test/api';
  const redirectUrl = 'https://callback.example.test/done?code=private-code&state=private-state';
  const mcpRequests: PlaywrightRequest[] = [];
  const unexpectedApiRequests: string[] = [];
  const diagnostics: string[] = [];
  let serverState: 'needs_auth' | 'connected' | 'logged_out' = 'needs_auth';
  let operationState: 'waiting_for_user' | 'exchanging_code' | 'connected' = 'waiting_for_user';
  let operationActive = false;
  let submittedRedirect: string | null = null;
  let configured = false;

  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('react-grab.com')) {
      diagnostics.push(message.text());
    }
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (!url.includes('react-grab.com') && !url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')) {
      diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  page.on('request', (request) => {
    if (request.url().includes('/api/claude-mcp/')) mcpRequests.push(request);
  });

  await page.context().route('https://oauth.example.test/**', async (route) => {
    await route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><title>Fake OAuth Provider</title><h1>Authorization complete</h1>',
    });
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = decodeURIComponent(url.pathname);
    const method = request.method();
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }

    if (method === 'GET' && path === '/api/me') {
      await route.fulfill({ json: { user_id: 'claude-mcp-user', email: 'claude-mcp@example.test', display_name: 'Claude MCP User', role: 'user' } });
      return;
    }
    if (method === 'GET' && path === '/api/connectors') {
      await route.fulfill({ json: { connectors: [] } });
      return;
    }
    if (method === 'GET' && path === '/api/claude-mcp/capability') {
      await route.fulfill({
        json: {
          enabled: true,
          reason_code: null,
          cli_version: '2.1.235',
          minimum_cli_version: '2.1.186',
          headless_minimum_cli_version: '2.1.191',
          credential_identity: 'technical-agent-identity',
        },
      });
      return;
    }
    if (method === 'GET' && path === '/api/claude-mcp/servers') {
      await route.fulfill({
        json: {
          servers: configured ? [{
            name: serverName,
            state: serverState,
            transport: 'http',
            detail: null,
            active_operation_id: operationActive ? 'operation-1' : null,
          }] : [],
        },
      });
      return;
    }
    if (method === 'POST' && path === '/api/claude-mcp/servers') {
      const payload = request.postDataJSON() as { name: string; url: string };
      expect(payload).toEqual({ name: serverName, url: serverUrl });
      configured = true;
      await route.fulfill({
        status: 201,
        json: {
          server: {
            name: serverName,
            state: 'needs_auth',
            transport: 'http',
            detail: null,
            active_operation_id: null,
          },
        },
      });
      return;
    }
    if (method === 'POST' && path === `/api/claude-mcp/servers/${serverName}/auth-operations`) {
      operationState = 'waiting_for_user';
      operationActive = true;
      await route.fulfill({ status: 202, json: { operation: operationPayload(operationState) } });
      return;
    }
    if (method === 'GET' && path === '/api/claude-mcp/auth-operations/operation-1') {
      if (operationState === 'exchanging_code') {
        operationState = 'connected';
        operationActive = false;
        serverState = 'connected';
      }
      await route.fulfill({ json: { operation: operationPayload(operationState) } });
      return;
    }
    if (method === 'POST' && path === '/api/claude-mcp/auth-operations/operation-1/redirect') {
      submittedRedirect = (request.postDataJSON() as { redirect_url: string }).redirect_url;
      operationState = 'exchanging_code';
      operationActive = true;
      await route.fulfill({ json: { operation: operationPayload(operationState) } });
      return;
    }
    if (method === 'POST' && path === `/api/claude-mcp/servers/${serverName}/logout`) {
      serverState = 'logged_out';
      await route.fulfill({
        json: {
          server: {
            name: serverName,
            state: 'logged_out',
            transport: null,
            detail: null,
            active_operation_id: null,
          },
        },
      });
      return;
    }
    if (method === 'DELETE' && path === `/api/claude-mcp/servers/${serverName}`) {
      configured = false;
      await route.fulfill({
        json: {
          server: {
            name: serverName,
            state: 'not_configured',
            transport: null,
            detail: null,
            active_operation_id: null,
          },
        },
      });
      return;
    }
    if (method === 'GET' && path === '/api/default-voices') {
      await route.fulfill({ json: {} });
      return;
    }
    if (method === 'GET' && path === '/api/sessions') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (method === 'GET' && path === '/api/sessions/range') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (method === 'GET' && path === '/api/sessions/events') {
      await route.fulfill({ body: ': connected\n\n', contentType: 'text/event-stream' });
      return;
    }
    if (method === 'GET' && path === '/api/pictures/range') {
      await route.fulfill({ json: { pictures: [] } });
      return;
    }
    if (method === 'GET' && path === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: true, timezone: 'Asia/Shanghai' } });
      return;
    }
    if (method === 'GET' && path === '/api/decks') {
      await route.fulfill({ json: { decks: [] } });
      return;
    }
    if (method === 'GET' && path === '/api/version') {
      await route.fulfill({ json: { version: 'technical-e2e' } });
      return;
    }
    unexpectedApiRequests.push(`${method} ${path}`);
    await route.fulfill({ status: 501, json: { error: { code: 'UNEXPECTED_E2E_API' } } });
  });

  function operationPayload(state: typeof operationState) {
    return {
      id: 'operation-1',
      server_name: serverName,
      state,
      authorization_url: state === 'waiting_for_user'
        ? 'https://oauth.example.test/authorize?client_id=fake&state=opaque-session'
        : null,
      error: null,
      redirect_submitted: state !== 'waiting_for_user',
      created_at: '2026-08-19T00:00:00Z',
      updated_at: '2026-08-19T00:00:01Z',
    };
  }

  await page.addInitScript((authToken) => {
    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);
  await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);

  await expect(page.getByRole('heading', { name: '资源链接', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Claude MCP 资源' })).toBeVisible();
  await page.getByLabel('MCP 服务名称').fill(serverName);
  await page.getByLabel('MCP HTTPS URL').fill(serverUrl);
  await page.getByRole('button', { name: '添加 MCP 服务' }).click();
  const serverCard = page.getByRole('article', { name: `MCP 服务 ${serverName}` });
  await expect(serverCard).toBeVisible();
  await expect(serverCard).toContainText('需要认证');

  await serverCard.getByRole('button', { name: '开始认证' }).click();
  await expect(serverCard).toContainText('等待授权');
  const authorizationLink = serverCard.getByRole('link', { name: '打开授权页面' });
  await expect(authorizationLink).toHaveAttribute('href', /oauth\.example\.test\/authorize/);
  const popupPromise = page.waitForEvent('popup');
  await authorizationLink.click();
  const popup = await popupPromise;
  await expect(popup.getByRole('heading', { name: 'Authorization complete' })).toBeVisible();
  await popup.close();

  const redirectInput = serverCard.getByLabel(`${serverName} redirect URL`);
  await redirectInput.fill(redirectUrl);
  await serverCard.getByRole('button', { name: '提交并连接' }).click();
  expect(submittedRedirect).toBe(redirectUrl);
  await expect(serverCard).toContainText('已连接', { timeout: 5000 });
  expect(await page.evaluate((secret) => Object.values(localStorage).every((value) => !value.includes(secret)), 'private-code')).toBe(true);

  await serverCard.getByRole('button', { name: 'Logout' }).click();
  await expect(serverCard).toContainText('已退出');
  await expect(serverCard.getByRole('button', { name: '重新连接' })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 760 });
  await expect(serverCard).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ fullPage: true, path: 'output/playwright/claude-mcp-resources-narrow.png' });

  await serverCard.getByRole('button', { name: '移除' }).click();
  await expect(serverCard).toHaveCount(0);
  await expect(page.getByText('尚未配置 MCP 服务。')).toBeVisible();

  const mcpHeaders = await Promise.all(mcpRequests.map((request) => request.allHeaders()));
  expect(mcpHeaders.length).toBeGreaterThanOrEqual(6);
  expect(mcpHeaders.every((headers) => headers.authorization === `Bearer ${token}`)).toBe(true);
  expect(mcpRequests.filter((request) => request.method() !== 'GET')).toHaveLength(5);
  expect(unexpectedApiRequests).toEqual([]);
  expect(diagnostics).toEqual([]);

});
