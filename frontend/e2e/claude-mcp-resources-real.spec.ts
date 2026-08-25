// [Input] Named existing actor/Deck, normal Dream/PostgreSQL, candidate Claude Runtime, an explicit remote MCP URL or server-owned stdio profile, and live Agent runtime.
// [Output] Real-business managed-DB configure → auth routing → automatic inventory → visible Chat SSE/MCP results → refresh/resume → cleanup evidence.
// [Pos] Opt-in macOS/Linux Claude MCP acceptance; no API interception, shadow account, cloned database, or fake CLI.
// [Sync] 2026-08-19: add the complete real-account MCP OAuth and per-turn Agent credential reuse journey.
// [Sync] 2026-08-20: assert Linux file projection versus macOS secure-storage reuse without reading Keychain.
// [Sync] 2026-08-20: verify remote server definitions reach Agent through the public SDK option and tolerate a direct localhost OAuth callback.
// [Sync] 2026-08-21: accept absolute HTTP(S) server input while preserving user-scope cleanup.
// [Sync] 2026-08-24: move both Agent turns onto visible Chat, approve only the named MCP tool in UI,
//                    and require persisted output-available results across refresh/resume before logout/removal.
// [Sync] 2026-08-24: accept both explicit post-logout unauthenticated labels before strict credential deletion checks.
// [Sync] 2026-08-25: accept explicit anonymous/OAuth modes, prove anonymous add never auto-starts login,
//                    preserve user-initiated login semantics, bind the Chat to an existing Deck, and assert both SSE responses.
// [Sync] 2026-08-25: replace CLI credential-store assertions with managed PostgreSQL ownership/encryption and ephemeral Chat projection evidence.
// [Sync] 2026-08-25: express real MCP turns as visible business requests while keeping the exact read-only tool in assertions only.
// [Sync] 2026-08-25: allow only an explicit read-only MCP tool set and always close the journey-owned runtime session.
// [Sync] 2026-08-25: wait for persisted tool/result parts after the Runtime turns idle before asserting resume output.
// [Sync] 2026-08-25: let detail discovery classify OAuth; the user-facing create form carries no auth mode.
// [Sync] 2026-08-25: preserve the safe backend error body when OAuth operation creation is rejected.
// [Sync] 2026-08-25: cover streamable HTTP, legacy SSE, and server-owned stdio through one visible managed-DB inventory/Chat journey.
// [Sync] 2026-08-25: permit only the exact read-only WaitForMcpServers pending-server handshake before the named MCP tool appears.
// [Sync] 2026-08-25: remove the obsolete redirect-file/manual-submit fallback; real OAuth must complete through the same-origin automatic callback popup.
// [Sync] 2026-08-25: wait for automatic detail inventory; no refresh inventory control is part of the business journey.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_MCP_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_MCP_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_MCP_ACTOR_EMAIL ?? '';
const DECK_ID = process.env.INK_REAL_CLAUDE_MCP_DECK_ID ?? '';
const SERVER_NAME = process.env.INK_REAL_CLAUDE_MCP_SERVER_NAME ?? '';
const SERVER_URL = process.env.INK_REAL_CLAUDE_MCP_SERVER_URL ?? '';
const SERVER_TRANSPORT = process.env.INK_REAL_CLAUDE_MCP_TRANSPORT ?? 'streamable_http';
const STDIO_PROFILE_KEY = process.env.INK_REAL_CLAUDE_MCP_STDIO_PROFILE_KEY ?? '';
const AUTH_MODE = process.env.INK_REAL_CLAUDE_MCP_AUTH_MODE ?? 'oauth';
const SAFE_INSPECTION_TOOL = process.env.INK_REAL_CLAUDE_MCP_SAFE_TOOL
  ?? (AUTH_MODE === 'anonymous' ? 'server_info' : 'get_server_info');
const SAFE_INSPECTION_TOOLS = new Set(
  (process.env.INK_REAL_CLAUDE_MCP_SAFE_TOOLS ?? SAFE_INSPECTION_TOOL)
    .split(',')
    .map((tool) => tool.trim())
    .filter(Boolean),
);
const BUSINESS_REQUEST = process.env.INK_REAL_CLAUDE_MCP_BUSINESS_REQUEST
  ?? '读取这个连接公开提供的只读信息，并说明是否成功。';
const BUSINESS_FOLLOW_UP = process.env.INK_REAL_CLAUDE_MCP_BUSINESS_FOLLOW_UP
  ?? '再次读取同一对象的只读信息，确认刷新后连接仍然可用。';
const EXPECTED_TOOL_COUNT = Number(process.env.INK_REAL_CLAUDE_MCP_TOOL_COUNT ?? (AUTH_MODE === 'anonymous' ? '40' : '41'));
const EXPECTED_RESOURCE_COUNT = Number(process.env.INK_REAL_CLAUDE_MCP_RESOURCE_COUNT ?? '0');
const EXPECTED_PROMPT_COUNT = Number(process.env.INK_REAL_CLAUDE_MCP_PROMPT_COUNT ?? '0');
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

const IMPACT_SCOPE = {
  actor: 'one named existing platform user',
  mcpConfiguration: 'one explicitly named user-scope remote server or server-owned stdio profile, removed at journey end',
  oauthCredential: AUTH_MODE === 'oauth'
    ? 'real provider token in the actor user store, logged out and revoked at journey end'
    : 'no OAuth credential is created or projected',
  agent: 'one normal persisted Chat thread with two read-only model turns across refresh/resume',
  historicalThreads: 'no login fan-out; only the new turn target is projected',
  subscriptionAndOtherUsers: 'unchanged',
} as const;

type ThreadStatus = {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
  pending_tool_call_ids?: string[];
};

type PersistedPart = {
  type?: string;
  toolName?: string;
  state?: string;
  text?: string;
};

type ThreadMessages = {
  thread: { id: string; title?: string | null };
  messages: Array<{ role: string; parts: PersistedPart[] }>;
};

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.describe.configure({ mode: 'serial' });
test.skip(!ENABLED, 'Set INK_REAL_CLAUDE_MCP_QA=1 with the named actor/server inputs.');

function requireInputs(): void {
  if (!ACTOR_EMAIL || !DECK_ID || !SERVER_NAME) {
    throw new Error(
      'INK_REAL_CLAUDE_MCP_ACTOR_EMAIL, INK_REAL_CLAUDE_MCP_DECK_ID, and INK_REAL_CLAUDE_MCP_SERVER_NAME are required.',
    );
  }
  if (!['streamable_http', 'sse', 'stdio'].includes(SERVER_TRANSPORT)) {
    throw new Error('INK_REAL_CLAUDE_MCP_TRANSPORT must be streamable_http, sse, or stdio.');
  }
  if (!['anonymous', 'oauth'].includes(AUTH_MODE)) {
    throw new Error('INK_REAL_CLAUDE_MCP_AUTH_MODE must be anonymous or oauth.');
  }
  if (!Number.isInteger(EXPECTED_TOOL_COUNT) || EXPECTED_TOOL_COUNT < 1) {
    throw new Error('INK_REAL_CLAUDE_MCP_TOOL_COUNT must be a positive integer.');
  }
  if (![EXPECTED_RESOURCE_COUNT, EXPECTED_PROMPT_COUNT].every((count) => (
    Number.isInteger(count) && count >= 0
  ))) {
    throw new Error('INK_REAL_CLAUDE_MCP_RESOURCE_COUNT and INK_REAL_CLAUDE_MCP_PROMPT_COUNT must be non-negative integers.');
  }
  if (!SAFE_INSPECTION_TOOLS.has(SAFE_INSPECTION_TOOL)
    || [...SAFE_INSPECTION_TOOLS].some((tool) => !/^[A-Za-z0-9_.:-]+$/.test(tool))) {
    throw new Error('INK_REAL_CLAUDE_MCP_SAFE_TOOLS must be a valid comma-separated set containing INK_REAL_CLAUDE_MCP_SAFE_TOOL.');
  }
  if (!BUSINESS_REQUEST.trim() || !BUSINESS_FOLLOW_UP.trim()
    || BUSINESS_REQUEST.length > 500 || BUSINESS_FOLLOW_UP.length > 500) {
    throw new Error('Real MCP business requests must be non-empty and at most 500 characters.');
  }
  if (SERVER_TRANSPORT === 'stdio') {
    if (!STDIO_PROFILE_KEY || SERVER_URL || AUTH_MODE !== 'anonymous') {
      throw new Error('stdio acceptance requires a profile key, no URL, and anonymous auth mode.');
    }
  } else if (!SERVER_URL.startsWith('https://')) {
    throw new Error('The real MCP acceptance URL must use HTTPS.');
  }
}

function createActorToken(email: string): string {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import os',
    "from persistence.config import load_database_url_from_env_file",
    "load_database_url_from_env_file(override=True) if os.environ.get('INK_LOAD_DATABASE_URL_FROM_ENV_FILE') == '1' else None",
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

async function getJson<T>(
  request: APIRequestContext,
  path: string,
  token: string,
): Promise<T> {
  const response = await request.get(`${WEB_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(200);
  return response.json() as Promise<T>;
}

async function approveExpectedMcpConfirmation(
  page: Page,
  threadId: string,
): Promise<boolean> {
  const dialogs = page.locator('[role="alertdialog"]:visible');
  const count = await dialogs.count();
  if (count === 0) return false;
  if (count !== 1) {
    throw new Error('Multiple tool confirmations are visible in the MCP OAuth journey.');
  }
  const dialog = dialogs.first();
  const accessibleName = await dialog.getAttribute('aria-label');
  const expectedToolNames = [...SAFE_INSPECTION_TOOLS]
    .map((tool) => `mcp__${SERVER_NAME}__${tool}`);
  const isExpectedMcpTool = Boolean(
    accessibleName && expectedToolNames.some((toolName) => accessibleName.includes(toolName)),
  );
  const isExactPendingServerWait = Boolean(
    accessibleName?.includes('WaitForMcpServers')
    && (await dialog.textContent())?.includes(JSON.stringify({ servers: [SERVER_NAME] })),
  );
  if (!isExpectedMcpTool && !isExactPendingServerWait) {
    throw new Error('An unexpected tool confirmation blocked the MCP transport journey.');
  }
  const approve = dialog.getByRole('button', { name: /^(同意|Approve)/ });
  await expect(approve).toBeVisible();
  const confirmationResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/tool-confirm'
  ), { timeout: 20_000 });
  await approve.click();
  const confirmationResponse = await confirmationResponsePromise;
  const confirmationPayload = await confirmationResponse.json().catch(() => null) as {
    detail?: { code?: string } | string;
  } | null;
  const confirmationCode = typeof confirmationPayload?.detail === 'object'
    ? confirmationPayload.detail.code
    : confirmationPayload?.detail;
  expect(
    confirmationResponse.status(),
    `Tool confirmation failed with code ${confirmationCode ?? 'unknown'}.`,
  ).toBe(200);
  expect(confirmationResponse.request().postDataJSON()).toMatchObject({
    thread_id: threadId,
    approved: true,
  });
  await expect(dialog).toBeHidden({ timeout: 15_000 });
  return true;
}

async function waitForTurn(
  page: Page,
  token: string,
  threadId: string,
  expectedTurnCount: number,
): Promise<void> {
  await expect.poll(async () => {
    if (await approveExpectedMcpConfirmation(page, threadId)) return false;
    const status = await getJson<ThreadStatus>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
      token,
    );
    return status.running === false && status.turn_count >= expectedTurnCount;
  }, {
    timeout: 360_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(true);
}

function mcpToolParts(payload: ThreadMessages): PersistedPart[] {
  return payload.messages.flatMap((message) => message.parts).filter((part) => (
    part.toolName?.startsWith(`mcp__${SERVER_NAME}__`)
  ));
}

function assistantText(payload: ThreadMessages): string {
  return payload.messages
    .filter((message) => message.role === 'assistant')
    .flatMap((message) => message.parts)
    .filter((part) => part.type === 'text' && typeof part.text === 'string')
    .map((part) => part.text?.trim() ?? '')
    .filter(Boolean)
    .join('\n');
}

async function completeAutomaticAuthorization(popup: Page): Promise<void> {
  const deadline = Date.now() + 180_000;
  const clickedLabels = new Set<string>();
  while (Date.now() < deadline) {
    if (popup.isClosed()) return;

    const submitted = popup.getByRole('heading', { name: 'MCP 授权已自动提交' });
    if (await submitted.isVisible().catch(() => false)) {
      await popup.waitForEvent('close', { timeout: 5_000 }).catch(async () => {
        await popup.close();
      });
      return;
    }

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
  throw new Error('The OAuth provider did not complete the automatic callback before timeout.');
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

async function cleanupThreadRuntime(
  request: APIRequestContext,
  headers: Record<string, string>,
  threadId: string | null,
): Promise<void> {
  if (!threadId) return;
  const statusResponse = await request.get(
    `${WEB_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
    { headers },
  ).catch(() => null);
  if (statusResponse?.ok()) {
    const status = await statusResponse.json() as ThreadStatus;
    for (const toolCallId of status.pending_tool_call_ids ?? []) {
      await request.post(`${WEB_BASE}/api/claude-agent/tool-confirm`, {
        headers,
        data: {
          thread_id: threadId,
          tool_call_id: toolCallId,
          approved: false,
          reason: '真实业务测试清理：拒绝未完成的工具确认。',
        },
      }).catch(() => undefined);
    }
  }
  await request.delete(`${WEB_BASE}/api/claude-agent/session`, {
    headers,
    params: { session_id: threadId },
  }).catch(() => undefined);
}

function managedProjectionFacts(threadId: string): {
  databaseHasServer: boolean;
  databaseHasCredential: boolean;
  databaseConfigContainsPlaintextCredential: boolean;
  threadProjectionFiles: number;
  targetHasObsoleteMcpServer: boolean;
  targetHasMcpOauthFiles: boolean;
} {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import os',
    "from persistence.config import load_database_url_from_env_file",
    "load_database_url_from_env_file(override=True) if os.environ.get('INK_LOAD_DATABASE_URL_FROM_ENV_FILE') == '1' else None",
    'import database,json,sys',
    'from pathlib import Path',
    'from libs.claude_agent_kit.server.workspace import get_workspace_root',
    'db=database.get_db()',
    "actor=db.execute('select id from users where email=%s and status=%s',(sys.argv[1],'active')).fetchone()",
    "assert actor is not None, 'actor not found'",
    "server=db.execute('select id,remote_url,stdio_profile_key from dream_mcp_servers where user_id=%s and server_key=%s',(actor['id'],sys.argv[3])).fetchone()",
    "credential=db.execute('select id,ciphertext,iv,tag from dream_mcp_credentials where server_id=%s',(server['id'],)).fetchone() if server else None",
    'db.close()',
    "target=Path(get_workspace_root())/sys.argv[2]/'.claude-home'",
    "target_config=json.loads((target/'.claude.json').read_text()) if (target/'.claude.json').exists() else {}",
    "projection_dir=Path(get_workspace_root())/sys.argv[2]/'.claude-tmp'/'mcp-config'",
    "projection_files=sum(1 for item in projection_dir.iterdir() if item.is_file()) if projection_dir.exists() else 0",
    "oauth_dir=target/'mcp-oauth'",
    "config_text=' '.join(str(value or '') for value in (server['remote_url'],server['stdio_profile_key'])) if server else ''",
    "cipher_text=' '.join(str(credential[key] or '') for key in ('ciphertext','iv','tag')) if credential else ''",
    "print(json.dumps({'databaseHasServer':bool(server),'databaseHasCredential':bool(credential),'databaseConfigContainsPlaintextCredential':('Authorization' in config_text or 'Bearer ' in config_text or 'Bearer ' in cipher_text),'threadProjectionFiles':projection_files,'targetHasObsoleteMcpServer':bool(target_config.get('mcpServers',{}).get(sys.argv[3])),'targetHasMcpOauthFiles':oauth_dir.exists() and any(item.is_file() for item in oauth_dir.iterdir())}))",
  ].join(';');
  return JSON.parse(execFileSync(BACKEND_PYTHON, ['-c', source, ACTOR_EMAIL, threadId, SERVER_NAME], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  })) as {
    databaseHasServer: boolean;
    databaseHasCredential: boolean;
    databaseConfigContainsPlaintextCredential: boolean;
    threadProjectionFiles: number;
    targetHasObsoleteMcpServer: boolean;
    targetHasMcpOauthFiles: boolean;
  };
}

test('real actor completes MCP auth routing, inventory, Agent resume, and cleanup', async ({ page }) => {
  test.setTimeout(600_000);
  requireInputs();
  expect(IMPACT_SCOPE).toEqual({
    actor: 'one named existing platform user',
    mcpConfiguration: 'one explicitly named user-scope remote server or server-owned stdio profile, removed at journey end',
    oauthCredential: AUTH_MODE === 'oauth'
      ? 'real provider token in the actor user store, logged out and revoked at journey end'
      : 'no OAuth credential is created or projected',
    agent: 'one normal persisted Chat thread with two read-only model turns across refresh/resume',
    historicalThreads: 'no login fan-out; only the new turn target is projected',
    subscriptionAndOtherUsers: 'unchanged',
  });
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const diagnostics = diagnosticsFor(page);
  let operationId: string | null = null;
  let threadId: string | null = null;
  let removed = false;
  let authOperationRequests = 0;
  page.on('request', (request) => {
    if (
      request.method() === 'POST'
      && decodeURIComponent(new URL(request.url()).pathname)
        === `/api/claude-mcp/servers/${SERVER_NAME}/auth-operations`
    ) {
      authOperationRequests += 1;
    }
  });

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
    const decks = await getJson<{ decks: Array<{ id: string; enabled?: boolean; agent_type?: string }> }>(
      page.request,
      '/api/decks',
      token,
    );
    expect(decks.decks.some((deck) => deck.id === DECK_ID && deck.enabled !== false),
      'the selected existing Deck must be enabled').toBe(true);

    await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
    await expect(page.getByRole('heading', { name: 'Claude MCP 资源' })).toBeVisible();
    await expect(page.getByText('安全门禁已关闭此能力')).toHaveCount(0);
    await page.getByLabel('MCP 服务名称').fill(SERVER_NAME);
    await page.getByLabel('MCP 传输方式').selectOption(SERVER_TRANSPORT);
    if (SERVER_TRANSPORT === 'stdio') {
      await page.getByLabel('MCP stdio profile key').fill(STDIO_PROFILE_KEY);
    } else {
      await page.getByLabel('MCP 服务 URL').fill(SERVER_URL);
    }
    await page.getByRole('button', { name: '添加 MCP 服务' }).click();

    const card = page.getByRole('article', { name: `MCP 服务 ${SERVER_NAME}` });
    if (AUTH_MODE === 'oauth') {
      await expect(card).toContainText('已配置', { timeout: 30_000 });
      await card.getByRole('button', { name: '管理与工具' }).click();
      await expect(page.getByRole('button', { name: '开始认证' })).toBeVisible({ timeout: 60_000 });
      await page.getByRole('button', { name: '资源连接器' }).click();
    }
    if (AUTH_MODE === 'anonymous') {
      await expect(card).toContainText('已配置', { timeout: 30_000 });
      expect(authOperationRequests, 'anonymous add must not auto-start login').toBe(0);
      await expect(card.getByRole('button', { name: '退出认证' })).toHaveCount(0);
      await expect(card.getByRole('button', { name: /认证/ })).toHaveCount(0);
    } else {
      await expect(card).toContainText('需要认证');
      const operationResponse = page.waitForResponse((response) => (
        response.request().method() === 'POST'
        && decodeURIComponent(new URL(response.url()).pathname)
          === `/api/claude-mcp/servers/${SERVER_NAME}/auth-operations`
      ));
      await card.getByRole('button', { name: '开始认证' }).click();
      const operationHttpResponse = await operationResponse;
      expect(
        operationHttpResponse.status(),
        await operationHttpResponse.text(),
      ).toBe(202);
      const operationPayload = await operationHttpResponse.json() as {
        operation: { id: string };
      };
      operationId = operationPayload.operation.id;
      await expect(card).toContainText('等待授权');

      const authorizationLink = card.getByRole('link', { name: '打开授权页面' });
      await expect(card.getByLabel(`${SERVER_NAME} redirect URL`)).toHaveCount(0);
      await expect(card.getByRole('button', { name: '提交并连接' })).toHaveCount(0);
      const popupPromise = page.waitForEvent('popup');
      await authorizationLink.click();
      const popup = await popupPromise;
      await completeAutomaticAuthorization(popup);
      await expect(card).toContainText('已认证', { timeout: 60_000 });
    }

    await card.getByRole('button', { name: '管理与工具' }).click();
    await expect(page.getByRole('button', { name: /刷新 inventory|重试 inventory|重试探测/ })).toHaveCount(0);
    await expect(page.getByRole('tab', { name: `Tools ${EXPECTED_TOOL_COUNT}` })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByRole('article', { name: `MCP 工具 ${SAFE_INSPECTION_TOOL}` })).toBeVisible();
    await expect(page.getByRole('tab', { name: `Resources ${EXPECTED_RESOURCE_COUNT}` })).toBeVisible();
    await expect(page.getByRole('tab', { name: `Prompts ${EXPECTED_PROMPT_COUNT}` })).toBeVisible();
    await page.getByRole('button', { name: '资源连接器' }).click();

    await page.getByRole('button', { name: '返回应用' }).click();
    const seededThreadTitle = `MCP auth routing QA ${Date.now()}`;
    const seededThreadResponse = await page.request.post(`${WEB_BASE}/api/claude-agent/threads`, {
      headers,
      data: { deckId: DECK_ID, title: seededThreadTitle },
    });
    expect(seededThreadResponse.status(), await seededThreadResponse.text()).toBe(200);
    const seededThread = await seededThreadResponse.json() as {
      thread_id: string;
      deck_id: string | null;
    };
    expect(seededThread.deck_id).toBe(DECK_ID);
    threadId = seededThread.thread_id;
    await page.goto(`${WEB_BASE}/story-workspace/chat`);
    const seededHistoryEntry = page.getByTitle(seededThreadTitle).first();
    await expect(seededHistoryEntry).toBeVisible({ timeout: 30_000 });
    await seededHistoryEntry.click();

    const prompt = `请使用刚才添加的 ${SERVER_NAME} 只读连接完成这项检查：${BUSINESS_REQUEST} 不要创建、修改或删除任何远端内容。`;
    const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
    await expect(input).toBeVisible();
    await input.fill(prompt);
    const agentRequestPromise = page.waitForRequest((request) => (
      request.method() === 'POST'
      && new URL(request.url()).pathname === '/api/claude-agent'
    ));
    const agentResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname === '/api/claude-agent'
    ));
    await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
    const agentRequest = await agentRequestPromise;
    expect(agentRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
    const agentResponse = await agentResponsePromise;
    expect(agentResponse.status()).toBe(200);
    expect(agentResponse.headers()['content-type']).toContain('text/event-stream');

    await waitForTurn(page, token, threadId, 1);
    const firstHistory = await getJson<ThreadMessages>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
      token,
    );
    const firstMcpParts = mcpToolParts(firstHistory);
    expect(firstMcpParts.length).toBeGreaterThanOrEqual(1);
    expect(firstMcpParts.every((part) => SAFE_INSPECTION_TOOLS.has(
      part.toolName?.slice(`mcp__${SERVER_NAME}__`.length) ?? '',
    ))).toBe(true);
    expect(firstMcpParts.some((part) => (
      part.toolName === `mcp__${SERVER_NAME}__${SAFE_INSPECTION_TOOL}`
    ))).toBe(true);
    expect(firstMcpParts.every((part) => part.state === 'output-available')).toBe(true);
    expect(assistantText(firstHistory).length).toBeGreaterThan(0);
    await expect(page.getByText(prompt, { exact: true })).toBeVisible();

    const threadTitle = firstHistory.thread.title?.trim();
    expect(threadTitle).toBeTruthy();
    await page.reload();
    const historyEntry = page.getByTitle(threadTitle!).first();
    await expect(historyEntry).toBeVisible({ timeout: 30_000 });
    await historyEntry.click();
    await expect(page.getByText(prompt, { exact: true })).toBeVisible({ timeout: 30_000 });

    let unexpectedThreadCreations = 0;
    page.on('request', (request) => {
      if (request.method() === 'POST'
        && new URL(request.url()).pathname === '/api/claude-agent/threads') {
        unexpectedThreadCreations += 1;
      }
    });
    const followUp = `继续刚才的 ${SERVER_NAME} 连接检查：${BUSINESS_FOLLOW_UP} 仍然不要创建、修改或删除任何远端内容。`;
    const followUpInput = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
    await followUpInput.fill(followUp);
    const followUpRequestPromise = page.waitForRequest((request) => (
      request.method() === 'POST'
      && new URL(request.url()).pathname === '/api/claude-agent'
    ));
    const followUpResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname === '/api/claude-agent'
    ));
    await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
    const followUpRequest = await followUpRequestPromise;
    expect(followUpRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
    const followUpResponse = await followUpResponsePromise;
    expect(followUpResponse.status()).toBe(200);
    expect(followUpResponse.headers()['content-type']).toContain('text/event-stream');

    await waitForTurn(page, token, threadId, 2);
    let finalHistory = await getJson<ThreadMessages>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
      token,
    );
    await expect.poll(async () => {
      finalHistory = await getJson<ThreadMessages>(
        page.request,
        `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
        token,
      );
      return mcpToolParts(finalHistory).length > firstMcpParts.length
        && assistantText(finalHistory).length > assistantText(firstHistory).length;
    }, {
      timeout: 30_000,
      intervals: [250, 500, 1_000, 2_000],
    }).toBe(true);
    const finalMcpParts = mcpToolParts(finalHistory);
    expect(finalMcpParts.length).toBeGreaterThan(firstMcpParts.length);
    expect(finalMcpParts.every((part) => SAFE_INSPECTION_TOOLS.has(
      part.toolName?.slice(`mcp__${SERVER_NAME}__`.length) ?? '',
    ))).toBe(true);
    expect(finalMcpParts.some((part) => (
      part.toolName === `mcp__${SERVER_NAME}__${SAFE_INSPECTION_TOOL}`
    ))).toBe(true);
    expect(finalMcpParts.every((part) => part.state === 'output-available')).toBe(true);
    expect(assistantText(finalHistory).length).toBeGreaterThan(assistantText(firstHistory).length);
    await expect(page.getByText(followUp, { exact: true })).toBeVisible();
    expect(unexpectedThreadCreations).toBe(0);

    const workspaceResponse = await page.request.get(`${WEB_BASE}/api/workspace/files`, {
      headers,
      params: { sessionId: threadId, recursive: '1' },
    });
    expect(workspaceResponse.status(), await workspaceResponse.text()).toBe(200);
    const workspace = await workspaceResponse.json() as { tree?: unknown[]; workspaceCreated?: boolean };
    expect(Array.isArray(workspace.tree)).toBe(true);
    expect(workspace.workspaceCreated).toBe(false);

    const projection = managedProjectionFacts(threadId);
    expect(projection).toMatchObject({
      databaseHasServer: true,
      databaseHasCredential: AUTH_MODE === 'oauth',
      databaseConfigContainsPlaintextCredential: false,
      threadProjectionFiles: 0,
      targetHasObsoleteMcpServer: false,
      targetHasMcpOauthFiles: false,
    });

    await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
    const connectedCard = page.getByRole('article', { name: `MCP 服务 ${SERVER_NAME}` });
    if (AUTH_MODE === 'anonymous') {
      await expect(connectedCard).toContainText('已配置', { timeout: 30_000 });
      await expect(connectedCard.getByRole('button', { name: '退出认证' })).toHaveCount(0);
    } else {
      await expect(connectedCard).toContainText('已认证', { timeout: 30_000 });
      await connectedCard.getByRole('button', { name: '退出认证' }).click();
      await expect(connectedCard).toContainText(/已退出|需要认证/);
    }
    await connectedCard.getByRole('button', { name: '移除' }).click();
    await expect(connectedCard).toHaveCount(0);
    removed = true;
    operationId = null;

    const revoked = managedProjectionFacts(threadId);
    expect(revoked).toMatchObject({
      databaseHasServer: false,
      databaseHasCredential: false,
      databaseConfigContainsPlaintextCredential: false,
      threadProjectionFiles: 0,
      targetHasObsoleteMcpServer: false,
      targetHasMcpOauthFiles: false,
    });
    expect(diagnostics).toEqual([]);
  } finally {
    await cleanupThreadRuntime(page.request, headers, threadId);
    if (!removed) {
      await cleanup(page.request, headers, operationId, SERVER_NAME);
    }
  }
});
