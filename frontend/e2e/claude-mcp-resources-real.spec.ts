// [Input] Named existing actor, normal Dream/PostgreSQL, official Claude CLI, a real OAuth MCP URL, and live Agent runtime.
// [Output] Real-business Resources configure → OAuth → Connected → Agent user-credential reuse → Logout → Remove evidence.
// [Pos] Opt-in macOS/Linux Claude MCP acceptance; no API interception, shadow account, cloned database, or fake CLI.
// [Sync] 2026-08-19: add the complete real-account MCP OAuth and per-turn Agent credential reuse journey.
// [Sync] 2026-08-20: assert Linux file projection versus macOS secure-storage reuse without reading Keychain.
// [Sync] 2026-08-20: verify remote server definitions reach Agent through the public SDK option and tolerate a direct localhost OAuth callback.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { join, resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_MCP_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_MCP_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_MCP_ACTOR_EMAIL ?? '';
const SERVER_NAME = process.env.INK_REAL_CLAUDE_MCP_SERVER_NAME ?? '';
const SERVER_URL = process.env.INK_REAL_CLAUDE_MCP_SERVER_URL ?? '';
const BROWSER_HANDOFF_DIR = process.env.INK_REAL_CLAUDE_MCP_BROWSER_HANDOFF_DIR ?? '';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

const IMPACT_SCOPE = {
  actor: 'one named existing platform user',
  mcpConfiguration: 'one explicitly named user-scope HTTPS server, removed at journey end',
  oauthCredential: 'real provider token in the actor user store, logged out and revoked at journey end',
  agent: 'one normal persisted Chat thread and one read-only model turn',
  historicalThreads: 'no login fan-out; only the new turn target is projected',
  subscriptionAndOtherUsers: 'unchanged',
} as const;

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.describe.configure({ mode: 'serial' });
test.skip(!ENABLED, 'Set INK_REAL_CLAUDE_MCP_QA=1 with the named actor/server inputs.');

function requireInputs(): void {
  if (!ACTOR_EMAIL || !SERVER_NAME || !SERVER_URL) {
    throw new Error(
      'INK_REAL_CLAUDE_MCP_ACTOR_EMAIL, INK_REAL_CLAUDE_MCP_SERVER_NAME, and INK_REAL_CLAUDE_MCP_SERVER_URL are required.',
    );
  }
  if (!SERVER_URL.startsWith('https://')) {
    throw new Error('The real MCP acceptance URL must use HTTPS.');
  }
}

function createActorToken(email: string): string {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import auth,database,sys',
    'db=database.get_db()',
    "user=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'],user['email']))",
  ].join(';');
  return execFileSync(BACKEND_PYTHON, ['-c', source, email], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    const text = message.text();
    if (message.type() === 'error'
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(text)) {
      diagnostics.push(`console: ${text}`);
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${new URL(url).origin}`);
    }
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${new URL(response.url()).pathname}`);
    }
  });
  return diagnostics;
}

async function authorizationRedirect(popup: Page): Promise<string> {
  const deadline = Date.now() + 180_000;
  const clickedLabels = new Set<string>();
  while (Date.now() < deadline) {
    const current = popup.url();
    if (/^https?:\/\/(?:127\.0\.0\.1|localhost)(?::\d+)?\//.test(current)
      && /[?&]code=/.test(current)) {
      return current;
    }

    const inputValues = await popup.locator('input').evaluateAll((inputs) => inputs
      .map((input) => (input as HTMLInputElement).value)
      .filter((value) => /^https?:\/\//.test(value) && /[?&]code=/.test(value)));
    if (inputValues[0]) return inputValues[0];

    const loginControlVisible = await popup.locator(
      'input[type="email"], input[type="password"], input[autocomplete="username"], input[autocomplete="current-password"]',
    ).first().isVisible().catch(() => false);
    if (loginControlVisible) {
      throw new Error('The OAuth provider requires an authenticated browser session.');
    }

    for (const label of ['Authorize', 'Allow', 'Approve', 'Continue', '授权', '允许', '同意', '继续']) {
      const control = popup.getByRole('button', { name: new RegExp(`^${label}$`, 'i') }).first();
      if (!clickedLabels.has(label) && await control.isVisible().catch(() => false)) {
        clickedLabels.add(label);
        await control.click();
        break;
      }
    }
    await popup.waitForTimeout(500);
  }
  throw new Error('The OAuth provider did not return a redirect URL before timeout.');
}

function handoffFile(name: 'authorization-url' | 'redirect-url'): string {
  return join(resolve(BROWSER_HANDOFF_DIR), name);
}

function clearBrowserHandoff(): void {
  if (!BROWSER_HANDOFF_DIR) return;
  rmSync(handoffFile('authorization-url'), { force: true });
  rmSync(handoffFile('redirect-url'), { force: true });
}

async function authorizationRedirectFromChrome(
  page: Page,
  authorizationUrl: string,
): Promise<string> {
  if (!BROWSER_HANDOFF_DIR) {
    throw new Error('Chrome handoff directory is not configured.');
  }
  const parsedAuthorization = new URL(authorizationUrl);
  if (parsedAuthorization.protocol !== 'https:') {
    throw new Error('OAuth authorization URL must use HTTPS.');
  }
  mkdirSync(resolve(BROWSER_HANDOFF_DIR), { recursive: true, mode: 0o700 });
  clearBrowserHandoff();
  writeFileSync(handoffFile('authorization-url'), authorizationUrl, {
    encoding: 'utf-8',
    mode: 0o600,
  });

  const deadline = Date.now() + 300_000;
  while (Date.now() < deadline) {
    if (existsSync(handoffFile('redirect-url'))) {
      const redirectUrl = readFileSync(handoffFile('redirect-url'), 'utf-8').trim();
      const parsedRedirect = new URL(redirectUrl);
      if (
        !['127.0.0.1', 'localhost'].includes(parsedRedirect.hostname)
        || !parsedRedirect.searchParams.has('code')
      ) {
        throw new Error('Chrome handoff did not return a valid local OAuth redirect URL.');
      }
      clearBrowserHandoff();
      return redirectUrl;
    }
    await page.waitForTimeout(500);
  }
  throw new Error('Chrome did not return the OAuth redirect URL before timeout.');
}

async function cleanup(
  request: APIRequestContext,
  headers: Record<string, string>,
  operationId: string | null,
  serverName: string,
): Promise<void> {
  if (operationId) {
    await request.post(
      `${WEB_BASE}/api/claude-mcp/auth-operations/${encodeURIComponent(operationId)}/cancel`,
      { headers },
    ).catch(() => undefined);
  }
  await request.post(
    `${WEB_BASE}/api/claude-mcp/servers/${encodeURIComponent(serverName)}/logout`,
    { headers },
  ).catch(() => undefined);
  await request.delete(
    `${WEB_BASE}/api/claude-mcp/servers/${encodeURIComponent(serverName)}`,
    { headers },
  ).catch(() => undefined);
}

function credentialProjectionFacts(threadId: string): {
  credentialDelivery: 'file_projection' | 'secure_storage_reference';
  sourceHasMcpOAuth: boolean;
  sourceHasMcpServer: boolean;
  targetHasObsoleteMcpServer: boolean;
  targetHasMcpOAuth: boolean;
  targetHasMainClaudeOauth: boolean;
  secureStorageHomeMatchesSource: boolean;
} {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database,json,sys',
    'from pathlib import Path',
    'from claude_mcp.credentials import ClaudeMcpCredentialSynchronizer,resolve_user_paths',
    'from claude_mcp.settings import ClaudeMcpSettings',
    'from libs.claude_agent_kit.server.workspace import get_workspace_root',
    'settings=ClaudeMcpSettings.from_env()',
    'sync=ClaudeMcpCredentialSynchronizer(settings)',
    'db=database.get_db()',
    "actor=db.execute('select id from users where email=%s and status=%s',(sys.argv[1],'active')).fetchone()",
    'db.close()',
    "assert actor is not None, 'actor not found'",
    'source=resolve_user_paths(str(actor[\'id\']),settings).config_dir',
    "target=Path(get_workspace_root())/sys.argv[2]/'.claude-home'",
    "source_config=json.loads((source/'.claude.json').read_text()) if (source/'.claude.json').exists() else {}",
    "target_config=json.loads((target/'.claude.json').read_text()) if (target/'.claude.json').exists() else {}",
    'source_value=sync._read_source_credentials(source) or {} if sync.requires_file_credential_verification else {}',
    'target_value=sync._read_target_credentials(target) or {}',
    "delivery='file_projection' if sync.requires_file_credential_verification else 'secure_storage_reference'",
    "secure_home=sync.secure_storage_home(str(actor['id']))",
    "print(json.dumps({'credentialDelivery':delivery,'sourceHasMcpOAuth':bool(source_value.get('mcpOAuth')),'sourceHasMcpServer':bool(source_config.get('mcpServers',{}).get(sys.argv[3])),'targetHasObsoleteMcpServer':bool(target_config.get('mcpServers',{}).get(sys.argv[3])),'targetHasMcpOAuth':bool(target_value.get('mcpOAuth')),'targetHasMainClaudeOauth':'claudeAiOauth' in target_value,'secureStorageHomeMatchesSource':secure_home==source if secure_home else False}))",
  ].join(';');
  return JSON.parse(execFileSync(BACKEND_PYTHON, ['-c', source, ACTOR_EMAIL, threadId, SERVER_NAME], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  })) as {
    credentialDelivery: 'file_projection' | 'secure_storage_reference';
    sourceHasMcpOAuth: boolean;
    sourceHasMcpServer: boolean;
    targetHasObsoleteMcpServer: boolean;
    targetHasMcpOAuth: boolean;
    targetHasMainClaudeOauth: boolean;
    secureStorageHomeMatchesSource: boolean;
  };
}

test('real actor completes MCP OAuth, Agent credential reuse, logout, and removal', async ({ page }) => {
  test.setTimeout(600_000);
  requireInputs();
  expect(IMPACT_SCOPE).toEqual({
    actor: 'one named existing platform user',
    mcpConfiguration: 'one explicitly named user-scope HTTPS server, removed at journey end',
    oauthCredential: 'real provider token in the actor user store, logged out and revoked at journey end',
    agent: 'one normal persisted Chat thread and one read-only model turn',
    historicalThreads: 'no login fan-out; only the new turn target is projected',
    subscriptionAndOtherUsers: 'unchanged',
  });
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const diagnostics = diagnosticsFor(page);
  let operationId: string | null = null;
  let removed = false;

  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    const before = await page.request.get(`${WEB_BASE}/api/claude-mcp/servers`, { headers });
    expect(before.status()).toBe(200);
    const beforeServers = await before.json() as { servers: Array<{ name: string }> };
    expect(beforeServers.servers.some((server) => server.name === SERVER_NAME)).toBe(false);

    await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
    await expect(page.getByRole('heading', { name: 'Claude MCP 资源' })).toBeVisible();
    await expect(page.getByText('安全门禁已关闭此能力')).toHaveCount(0);
    await page.getByLabel('MCP 服务名称').fill(SERVER_NAME);
    await page.getByLabel('MCP HTTPS URL').fill(SERVER_URL);
    await page.getByRole('button', { name: '添加 MCP 服务' }).click();

    const card = page.getByRole('article', { name: `MCP 服务 ${SERVER_NAME}` });
    await expect(card).toContainText('需要认证');
    const operationResponse = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && decodeURIComponent(new URL(response.url()).pathname)
        === `/api/claude-mcp/servers/${SERVER_NAME}/auth-operations`
    ));
    await card.getByRole('button', { name: '开始认证' }).click();
    const operationPayload = await (await operationResponse).json() as {
      operation: { id: string };
    };
    operationId = operationPayload.operation.id;
    await expect(card).toContainText('等待授权');

    const authorizationLink = card.getByRole('link', { name: '打开授权页面' });
    let redirectUrl: string;
    if (BROWSER_HANDOFF_DIR) {
      const authorizationUrl = await authorizationLink.getAttribute('href');
      if (!authorizationUrl) throw new Error('Authorization URL is not available.');
      redirectUrl = await authorizationRedirectFromChrome(page, authorizationUrl);
    } else {
      const popupPromise = page.waitForEvent('popup');
      await authorizationLink.click();
      const popup = await popupPromise;
      redirectUrl = await authorizationRedirect(popup);
      await popup.close().catch(() => undefined);
    }
    const redirectInput = card.getByLabel(`${SERVER_NAME} redirect URL`);
    const connectedStatus = card.getByText('已连接', { exact: true });
    await expect.poll(async () => {
      if (await connectedStatus.isVisible().catch(() => false)) return 'connected';
      if (await redirectInput.isVisible().catch(() => false)) return 'redirect';
      return 'pending';
    }, { timeout: 60_000 }).not.toBe('pending');

    // Recent Claude Code builds host a localhost callback even with
    // `--no-browser`. If the browser reaches that listener, the original CLI
    // can finish before the UI submits the same redirect. Preserve the manual
    // stdin path for headless/SSH while treating direct callback completion as
    // the same idempotent operation result.
    if (await redirectInput.isVisible().catch(() => false)) {
      try {
        await redirectInput.fill(redirectUrl, { timeout: 5_000 });
        await card.getByRole('button', { name: '提交并连接' }).click({ timeout: 5_000 });
      } catch (error) {
        if (!await connectedStatus.isVisible().catch(() => false)) throw error;
      }
    }
    redirectUrl = '';
    await expect(card).toContainText('已连接', { timeout: 60_000 });

    const threadResponse = await page.request.post(`${WEB_BASE}/api/claude-agent/threads`, {
      headers,
      data: { title: `Claude MCP real QA ${new Date().toISOString()}` },
    });
    expect(threadResponse.status()).toBe(200);
    const threadId = (await threadResponse.json() as { thread_id: string }).thread_id;
    const agentResponse = await page.request.post(`${WEB_BASE}/api/claude-agent`, {
      headers: { ...headers, 'Content-Type': 'application/json' },
      data: {
        thread_id: threadId,
        message: {
          id: `claude-mcp-real-qa-${Date.now()}`,
          role: 'user',
          parts: [{
            type: 'text',
            text: `必须使用名为 ${SERVER_NAME} 的 MCP server 调用一个只读工具，简要确认连接可用。不要创建、更新或删除任何远端资源。`,
          }],
        },
        resume: false,
        toolChoice: 'auto',
        max_turns: 5,
      },
      timeout: 360_000,
    });
    expect(agentResponse.status()).toBe(200);
    expect(agentResponse.headers()['content-type'] ?? '').toContain('text/event-stream');
    const agentFrames = await agentResponse.text();
    expect(agentFrames.includes(`mcp__${SERVER_NAME}`)).toBe(true);
    expect(/"type"\s*:\s*"error"/.test(agentFrames)).toBe(false);

    const projection = credentialProjectionFacts(threadId);
    expect(projection.sourceHasMcpServer).toBe(true);
    expect(projection.targetHasObsoleteMcpServer).toBe(false);
    expect(projection.targetHasMainClaudeOauth).toBe(false);
    if (process.platform === 'darwin') {
      expect(projection).toMatchObject({
        credentialDelivery: 'secure_storage_reference',
        sourceHasMcpOAuth: false,
        targetHasMcpOAuth: false,
        secureStorageHomeMatchesSource: true,
      });
    } else {
      expect(projection).toMatchObject({
        credentialDelivery: 'file_projection',
        sourceHasMcpOAuth: true,
        targetHasMcpOAuth: true,
        secureStorageHomeMatchesSource: false,
      });
    }

    await card.getByRole('button', { name: 'Logout' }).click();
    await expect(card).toContainText('已退出');
    await card.getByRole('button', { name: '移除' }).click();
    await expect(card).toHaveCount(0);
    removed = true;
    operationId = null;

    const revoked = credentialProjectionFacts(threadId);
    expect(revoked.sourceHasMcpOAuth).toBe(false);
    expect(revoked.sourceHasMcpServer).toBe(false);
    expect(revoked.targetHasObsoleteMcpServer).toBe(false);
    expect(revoked.targetHasMcpOAuth).toBe(false);
    expect(revoked.targetHasMainClaudeOauth).toBe(false);
    expect(diagnostics).toEqual([]);
  } finally {
    clearBrowserHandoff();
    if (!removed) {
      await cleanup(page.request, headers, operationId, SERVER_NAME);
    }
  }
});
