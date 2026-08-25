// [Input] Running frontend entry point plus production-shaped intercepted Claude MCP and boot API fixtures.
// [Output] Verify managed-DB Resources → Configure → automatic inventory → OAuth → revision-aware Update → Logout → Remove with zero secret persistence.
// [Pos] Provider-free Claude MCP browser journey; it never calls a real OAuth provider, CLI, backend, or business database.
// [Sync] 2026-08-19: cover the complete visible v1 connector journey and responsive layout.
// [Sync] 2026-08-19: cover restricted HTTP(S) configuration and user-owned removal before real-provider QA.
// [Sync] 2026-08-20: cover the Notion-aligned detail workbench and prompt-free tool inventory.
// [Sync] 2026-08-21: cover remote HTTP plus project-scope read-only removal controls.
// [Sync] 2026-08-24: accept the production shell's authenticated session autosave
//                    without weakening the strict unexpected-request audit.
// [Sync] 2026-08-25: model Runtime-authored anonymous/required/authenticated states and the renamed Chinese logout action.
// [Sync] 2026-08-25: use managed-DB DTOs and explicit POST discovery; no CLI-shaped list/get/inventory fixture remains.
// [Sync] 2026-08-25: cover detail-page PATCH and CAS revision propagation before delete.
// [Sync] 2026-08-25: prove auth_kind is absent from forms and CRUD payloads; backend fixtures own classification.
// [Sync] 2026-08-25: require discovery evidence before OAuth appears and carry its CAS revision into later edits.
// [Sync] 2026-08-25: prove the MCP OAuth callback stays on the SPA, submits automatically, and never renders or stores its code/state.
// [Sync] 2026-08-25: require cache-first automatic detail inventory and no refresh/retry inventory controls.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

test('MCP OAuth callback submits automatically and keeps secrets out of page content and storage', async ({ page }) => {
  const backendCallbackRequests: string[] = [];
  let submittedRedirect: string | null = null;
  await page.context().route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (route.request().method() === 'POST'
      && path === '/api/claude-mcp/auth-operations/operation-auto/redirect') {
      submittedRedirect = (route.request().postDataJSON() as { redirect_url: string }).redirect_url;
      await route.fulfill({
        json: {
          operation: {
            id: 'operation-auto',
            server_name: 'automatic-oauth',
            state: 'exchanging_code',
            authorization_url: null,
            error: null,
            redirect_submitted: true,
            created_at: '2026-08-25T00:00:00Z',
            updated_at: '2026-08-25T00:00:01Z',
          },
        },
      });
      return;
    }
    await route.fulfill({ status: 401, json: { detail: 'Not authenticated' } });
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname === '/oauth/callback' && request.resourceType() !== 'document') {
      backendCallbackRequests.push(request.url());
    }
  });

  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'callback-technical-token');
    localStorage.setItem('ink-memory:claude-mcp:pending-oauth-operation', 'operation-auto');
  });

  await page.goto(`${WEB_BASE}/oauth/callback?code=private-code&state=private-state`);

  await expect(page.getByRole('heading', { name: 'MCP 授权已自动提交' })).toBeVisible();
  await expect(page.locator('body')).not.toContainText('private-code');
  await expect(page.locator('body')).not.toContainText('private-state');
  expect(submittedRedirect).toContain('code=private-code');
  expect(await page.evaluate(() => Object.values(localStorage).every((value) => !value.includes('private-code')))).toBe(true);
  expect(await page.evaluate(() => localStorage.getItem('ink-memory:claude-mcp:pending-oauth-operation'))).toBeNull();
  expect(backendCallbackRequests).toEqual([]);
});

test('Resources completes the provider-free Claude MCP login and logout journey', async ({ page }) => {
  const token = 'claude-mcp-resources-technical-token';
  const serverName = 'e2e-user-server';
  const serverUrl = 'http://mcp.example.test/api';
  const mcpRequests: Array<{ method: string; path: string; headers: Record<string, string> }> = [];
  const unexpectedApiRequests: string[] = [];
  const diagnostics: string[] = [];
  let serverState: 'configured' | 'needs_auth' | 'connected' | 'logged_out' = 'configured';
  let operationState: 'waiting_for_user' | 'exchanging_code' | 'connected' = 'waiting_for_user';
  let operationActive = false;
  let submittedRedirect: string | null = null;
  let configured = false;
  let serverRevision = 1;
  let serverDisplayName = serverName;

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
  page.context().on('request', (request) => {
    if (request.url().includes('/api/claude-mcp/')) {
      mcpRequests.push({
        method: request.method(),
        path: decodeURIComponent(new URL(request.url()).pathname),
        headers: request.headers(),
      });
    }
  });

  await page.context().route('https://oauth.example.test/**', async (route) => {
    const automaticCallback = `${WEB_BASE}/oauth/callback?code=private-code&state=private-state`;
    await route.fulfill({
      contentType: 'text/html',
      body: `<!doctype html><title>Fake OAuth Provider</title><h1>Authorization complete</h1><script>location.replace(${JSON.stringify(automaticCallback)})</script>`,
    });
  });
  await page.context().route('**/api/**', async (route) => {
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
          cli_version: null,
          minimum_cli_version: null,
          headless_minimum_cli_version: null,
          credential_identity: null,
          management_mode: 'managed_db',
          schema_capability: 'dream.managed-mcp-resources.v1',
          schema_version: 1,
          transports: ['streamable_http', 'sse', 'stdio'],
        },
      });
      return;
    }
    if (method === 'GET' && path === '/api/claude-mcp/servers') {
      await route.fulfill({
        json: {
          servers: [...(configured ? [{
            name: serverName,
            state: serverState,
            auth_state: serverState === 'connected' ? 'authenticated' : serverState === 'configured' ? 'unknown' : 'required',
            transport: 'streamable_http',
            detail: null,
            active_operation_id: operationActive ? 'operation-1' : null,
            config_scope: 'user',
            removable: true,
            id: 'server-1',
            display_name: serverDisplayName,
            auth_kind: serverState === 'configured' ? 'none' : 'oauth',
            enabled: true,
            revision: serverRevision,
            credential_revision: serverState === 'connected' ? 1 : 0,
            credential_ref: serverState === 'connected' ? 'credential-1' : null,
            credential_configured: serverState === 'connected',
            workspace_id: null,
            url: serverUrl,
            stdio_profile_key: null,
          }] : [])],
        },
      });
      return;
    }
    if (method === 'GET' && path === `/api/claude-mcp/servers/${serverName}`) {
      await route.fulfill({
        json: {
          server: {
            name: serverName,
            state: serverState,
            auth_state: serverState === 'connected' ? 'authenticated' : serverState === 'configured' ? 'unknown' : 'required',
            transport: 'streamable_http',
            detail: null,
            active_operation_id: operationActive ? 'operation-1' : null,
            config_scope: 'user',
            removable: true,
            id: 'server-1',
            display_name: serverDisplayName,
            auth_kind: serverState === 'configured' ? 'none' : 'oauth',
            enabled: true,
            revision: serverRevision,
            credential_revision: serverState === 'connected' ? 1 : 0,
            credential_ref: serverState === 'connected' ? 'credential-1' : null,
            credential_configured: serverState === 'connected',
            workspace_id: null,
            url: serverUrl,
            stdio_profile_key: null,
          },
        },
      });
      return;
    }
    if (method === 'POST' && path === `/api/claude-mcp/servers/${serverName}/discoveries`) {
      expect(request.postDataJSON()).toEqual({ force: false });
      if (serverState === 'configured') {
        serverState = 'needs_auth';
        serverRevision = 2;
        await route.fulfill({
          json: {
            discovery: {
              server_id: 'server-1',
              status: 'failed',
              config_revision: serverRevision,
              credential_revision: 0,
              server_info: null,
              tools: [],
              resources: [],
              prompts: [],
              error: { code: 'CLAUDE_MCP_CREDENTIAL_REQUIRED', retryable: false, trace_id: 'trace-auth-required' },
              discovered_at: '2026-08-25T00:00:00Z',
              cached: false,
              truncated: false,
            },
          },
        });
        return;
      }
      const tools = [
        { name: 'submit_workflow', description: 'Submit a workflow', annotations: { read_only: null, destructive: true, open_world: null } },
        { name: 'get_job_status', description: 'Read job status', annotations: { read_only: true, destructive: null, open_world: null } },
        { name: 'wait_for_job', description: 'Wait for a job', annotations: { read_only: true, destructive: null, open_world: null } },
        { name: 'get_output', description: 'Read an output', annotations: { read_only: true, destructive: null, open_world: null } },
        { name: 'use_previous_output', description: null, annotations: { read_only: null, destructive: null, open_world: null } },
        ...Array.from({ length: 36 }, (_, index) => ({
          name: `comfy_tool_${String(index + 6).padStart(2, '0')}`,
          description: `Technical tool ${index + 6}`,
          annotations: { read_only: null, destructive: null, open_world: null },
        })),
      ];
      await route.fulfill({
        json: {
          discovery: {
            server_id: 'server-1',
            status: 'complete',
            config_revision: serverRevision,
            credential_revision: 1,
            server_info: { name: 'Technical MCP', version: '1.0.0' },
            tools,
            resources: [{ uri: 'https://mcp.example.test/resources/readme', name: 'README', description: 'Read-only resource', mime_type: 'text/markdown' }],
            prompts: [{ name: 'inspect_workflow', description: 'Inspect without mutation', argument_count: 1 }],
            error: null,
            discovered_at: '2026-08-25T00:00:00Z',
            cached: false,
            truncated: false,
          },
        },
      });
      return;
    }
    if (method === 'POST' && path === '/api/claude-mcp/servers') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      expect(payload).toEqual({
        name: serverName,
        display_name: serverName,
        transport: 'streamable_http',
        scope: 'user',
        url: serverUrl,
        stdio_profile_key: null,
      });
      configured = true;
      await route.fulfill({
        status: 201,
        json: {
          server: {
            name: serverName,
            state: 'configured',
            auth_state: 'unknown',
            transport: 'streamable_http',
            detail: null,
            active_operation_id: null,
            config_scope: 'user',
            removable: true,
            id: 'server-1', display_name: serverName, auth_kind: 'none', enabled: true,
            revision: 1, credential_revision: 0, credential_ref: null,
            credential_configured: false, workspace_id: null, url: serverUrl,
            stdio_profile_key: null,
          },
        },
      });
      return;
    }
    if (method === 'PATCH' && path === '/api/claude-mcp/servers/server-1') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      expect(payload).toEqual({
        expected_revision: 2,
        display_name: 'Edited MCP Server',
        transport: 'streamable_http',
        workspace_id: null,
        url: serverUrl,
        stdio_profile_key: null,
        enabled: true,
      });
      serverRevision = 3;
      serverDisplayName = 'Edited MCP Server';
      await route.fulfill({
        json: {
          server: {
            name: serverName,
            state: serverState,
            auth_state: 'authenticated',
            transport: 'streamable_http',
            detail: null,
            active_operation_id: null,
            config_scope: 'user',
            removable: true,
            id: 'server-1',
            display_name: serverDisplayName,
            auth_kind: 'oauth',
            enabled: true,
            revision: serverRevision,
            credential_revision: 1,
            credential_ref: 'credential-1',
            credential_configured: true,
            workspace_id: null,
            url: serverUrl,
            stdio_profile_key: null,
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
    if (method === 'DELETE' && path === `/api/claude-mcp/servers/${serverName}/credential`) {
      serverState = 'logged_out';
      await route.fulfill({
        json: {
          server: {
            name: serverName,
            state: 'logged_out',
            auth_state: 'required',
            transport: null,
            detail: null,
            active_operation_id: null,
            config_scope: 'user',
            removable: true,
          },
        },
      });
      return;
    }
    if (method === 'DELETE' && path === '/api/claude-mcp/servers/server-1') {
      expect(url.searchParams.get('expected_revision')).toBe('3');
      configured = false;
      await route.fulfill({
        json: {
          server: {
            name: serverName,
            state: 'not_configured',
            auth_state: 'unknown',
            transport: null,
            detail: null,
            active_operation_id: null,
            config_scope: 'user',
            removable: false,
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
    if (method === 'POST' && path === '/api/sessions') {
      const payload = request.postDataJSON() as {
        session_id?: unknown;
        editor_state?: unknown;
      };
      expect(payload.session_id).toEqual(expect.any(String));
      expect(payload.editor_state).toEqual(expect.any(Object));
      await route.fulfill({ json: { ok: true } });
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
  await expect(page.getByLabel('MCP 认证方式')).toHaveCount(0);
  await expect(page.getByText('认证要求由 Dream 连接 Server 后自动判断')).toBeVisible();
  await page.getByLabel('MCP 服务名称').fill(serverName);
  await page.getByLabel('MCP 服务 URL').fill(serverUrl);
  await page.getByRole('button', { name: '添加 MCP 服务' }).click();
  const serverCard = page.getByRole('article', { name: `MCP 服务 ${serverName}` });
  await expect(serverCard).toBeVisible();
  await expect(serverCard).toContainText('已配置');
  await expect(serverCard.getByRole('button', { name: '开始认证' })).toHaveCount(0);
  await serverCard.getByRole('button', { name: '管理与工具' }).click();
  await expect(page).toHaveURL(new RegExp(`mcp-server=${serverName}`));
  await expect(page.getByRole('button', { name: /刷新 inventory|重试 inventory|重试探测/ })).toHaveCount(0);
  await expect(page.getByText('需要认证', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('user · revision 2', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '开始认证' }).click();
  await expect(page.getByText('等待授权', { exact: true }).first()).toBeVisible();
  const authorizationLink = page.getByRole('link', { name: '打开授权页面' });
  await expect(authorizationLink).toHaveAttribute('href', /oauth\.example\.test\/authorize/);
  const popupPromise = page.waitForEvent('popup');
  await authorizationLink.click();
  const popup = await popupPromise;
  await popup.waitForEvent('close');
  expect(submittedRedirect).toContain('code=private-code');
  await expect(page.getByText('已认证连接', { exact: true }).first()).toBeVisible({ timeout: 5000 });
  expect(await page.evaluate((secret) => Object.values(localStorage).every((value) => !value.includes(secret)), 'private-code')).toBe(true);

  await expect(page.getByRole('heading', { name: `${serverName} MCP Server` })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Tools 41' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText(serverUrl, { exact: true })).toBeVisible();
  await page.getByRole('searchbox', { name: '搜索 MCP 工具' }).fill('submit_workflow');
  const destructiveTool = page.getByRole('article', { name: 'MCP 工具 submit_workflow' });
  await expect(destructiveTool).toContainText('破坏性');
  await page.getByRole('searchbox', { name: '搜索 MCP 工具' }).fill('');
  await page.getByRole('combobox', { name: '筛选 MCP 工具风险' }).selectOption('read_only');
  await expect(page.getByRole('article', { name: 'MCP 工具 get_job_status' })).toContainText('只读');
  await expect(page.getByRole('article', { name: 'MCP 工具 submit_workflow' })).toHaveCount(0);
  await page.getByRole('tab', { name: 'Resources 1' }).click();
  await expect(page.getByText('README', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Prompts 1' }).click();
  await expect(page.getByText('inspect_workflow', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Tools 41' }).click();
  await page.getByRole('combobox', { name: '筛选 MCP 工具风险' }).selectOption('all');
  await page.getByRole('button', { name: '编辑配置' }).click();
  const editForm = page.getByRole('form', { name: '编辑 MCP Server 配置' });
  await editForm.getByLabel('显示名称').fill('Edited MCP Server');
  await editForm.getByRole('button', { name: '保存配置' }).click();
  await expect(page.getByText('user · revision 3', { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 760 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ fullPage: true, path: 'output/playwright/claude-mcp-detail-narrow.png' });
  await page.reload();
  await expect(page.getByRole('heading', { name: `${serverName} MCP Server` })).toBeVisible();
  await page.getByRole('button', { name: '资源连接器' }).click();
  await expect(serverCard).toBeVisible();

  await serverCard.getByRole('button', { name: '退出认证' }).click();
  await expect(serverCard).toContainText('已退出');
  await expect(serverCard.getByRole('button', { name: '刷新数据库状态' })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 760 });
  await expect(serverCard).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ fullPage: true, path: 'output/playwright/claude-mcp-resources-narrow.png' });

  await serverCard.getByRole('button', { name: '移除' }).click();
  await expect(serverCard).toHaveCount(0);

  const mcpHeaders = mcpRequests.map((request) => request.headers);
  expect(mcpHeaders.length).toBeGreaterThanOrEqual(6);
  expect(mcpHeaders.every((headers) => headers.authorization === `Bearer ${token}`)).toBe(true);
  const discoveryRequests = mcpRequests.filter((request) => (
    request.method === 'POST'
    && request.path === `/api/claude-mcp/servers/${serverName}/discoveries`
  ));
  expect(discoveryRequests).toHaveLength(4);
  expect(mcpRequests.filter((request) => (
    request.method !== 'GET' && !discoveryRequests.includes(request)
  ))).toHaveLength(6);
  expect(unexpectedApiRequests).toEqual([]);
  expect(diagnostics).toEqual([]);

});
