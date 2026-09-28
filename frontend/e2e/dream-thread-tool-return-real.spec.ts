// [Input] Named normal-account actor, running Dream/Admin/Gateway/PostgreSQL services and the production Chat UI.
// [Output] Visible create_thread → wait_threads journey with an independent target Thread and one parent-turn final.
// [Pos] Opt-in real-model acceptance for Dream Thread Tools; created Threads and business receipts are retained for review.
// [Sync] 2026-09-28: replace background task-result delivery with same-turn wait_threads completion.
// [Sync] 2026-09-28: require Auto Thread orchestration to proceed without a duplicate confirmation dialog.
// [Sync] 2026-09-28: emulate the normal browser grant, including Gateway scopes, and prove 0068 through dmeck@suoxya.com.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_THREAD_TOOL_RETURN_QA === '1';
const WEB_BASE = process.env.INK_REAL_THREAD_TOOL_WEB_BASE ?? 'http://localhost:5173';
const ACTOR_EMAIL = process.env.INK_REAL_THREAD_TOOL_ACTOR_EMAIL ?? 'dmeck@suoxya.com';
const ADMIN_REPO = process.env.INK_ADMIN_REPO_ROOT ?? resolve(process.cwd(), '../../ink-admin-memory');

type ThreadStatus = {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
};

type PersistedPart = {
  type?: string;
  text?: string;
  toolName?: string;
  state?: string;
  output?: unknown;
};

type ThreadMessages = {
  thread: { id: string; title?: string | null };
  messages: Array<{ id: string; role: string; parts: PersistedPart[]; metadata?: Record<string, unknown> }>;
};

type TaskLinks = {
  source: null | { source_thread_id: string; thread_id: string; task_id: string };
  created: Array<{
    task_id: string;
    source_thread_id: string;
    thread_id: string;
    title: string;
    launch_status: 'pending' | 'starting' | 'failed';
    launch_error_code: string | null;
  }>;
};

// Business impact brief for this normal-account journey:
// - Source Thread: one visible user turn and one normal assistant final are added.
// - Target Thread: one independent Thread, first user message, assistant final, and
//   a distinct persisted Claude session are added through the public product path.
// - Parent/target relation: persisted and visible in the existing navigation UI.
// - Project, Episode, canonical story files, private Run artifacts, and billing
//   configuration: out of scope and must remain unchanged.

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1440, height: 900 },
});
test.skip(!ENABLED, 'Set INK_REAL_THREAD_TOOL_RETURN_QA=1 to run the normal-account real-model journey.');

function createActorSession(email: string): { handle: string; expiresAt: number } {
  const browserScopes = [
    'openid', 'profile', 'email', 'offline_access',
    'dream:read', 'dream:write', 'editor:read', 'editor:write',
    'product:read', 'product:write',
    'messages:create', 'messages:count_tokens', 'models:list',
  ].join(' ');
  const source = `
    import { createHash, randomBytes, randomUUID } from 'node:crypto';
    import pg from 'pg';
    import { symmetricDecrypt } from 'better-auth/crypto';
    import { importJWK, SignJWT } from 'jose';
    import { encryptAuthBundle } from './app/lib/auth/tokenEncryption.ts';
    const [email, origin] = process.argv.slice(1);
    const clients = JSON.parse(process.env.DREAM_DATA_SERVICE_CLIENTS ?? '[]');
    const client = clients.find((candidate) => candidate.origin === origin);
    if (!client) throw new Error('normal Dream OAuth client not found');
    const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
    try {
      const actor = await pool.query(
        'SELECT s.auth_user_id FROM public.users u JOIN identity.subject_links s ON s.canonical_user_id=u.id JOIN identity."user" i ON i.id=s.auth_user_id JOIN public.platform_users p ON p.source=\\'ink-dream\\' AND p.external_user_id=u.id::text WHERE lower(i.email)=lower($1) AND u.status=\\'active\\' AND p.status=\\'active\\' LIMIT 1',
        [email],
      );
      if (actor.rowCount !== 1) throw new Error('active linked actor not found');
      const keys = await pool.query('SELECT id, alg, "privateKey" FROM identity.jwks ORDER BY "createdAt" DESC LIMIT 1');
      if (keys.rowCount !== 1) throw new Error('Admin signing key not found');
      const row = keys.rows[0];
      const privateJwk = await symmetricDecrypt({
        key: process.env.BETTER_AUTH_SECRET,
        data: JSON.parse(row.privateKey),
      });
      const key = await importJWK(JSON.parse(privateJwk), row.alg ?? 'ES256');
      const now = Math.floor(Date.now() / 1000);
      const token = await new SignJWT({ client_id: client.oauthClientId, scope: ${JSON.stringify(browserScopes)} })
        .setProtectedHeader({ alg: 'ES256', kid: row.id, typ: 'at+jwt' })
        .setIssuer(process.env.BETTER_AUTH_URL)
        .setAudience(process.env.DREAM_API_RESOURCE)
        .setSubject(actor.rows[0].auth_user_id)
        .setJti(randomUUID())
        .setIssuedAt(now)
        .setExpirationTime(now + 300)
        .sign(key);
      const handle = 'dbr_' + randomBytes(32).toString('base64url');
      const expiresAt = new Date(Date.now() + 1_800_000);
      const transactionId = randomUUID();
      const ciphertext = encryptAuthBundle({
        handle,
        service_client_id: client.id,
        origin: client.origin,
        oauth_client_id: client.oauthClientId,
        subject: actor.rows[0].auth_user_id,
        tokens: { access_token: token, token_type: 'Bearer', expires_in: 300, scope: ${JSON.stringify(browserScopes)} },
        access_expires_at: new Date((now + 300) * 1000).toISOString(),
      });
      await pool.query(
        'INSERT INTO identity.browser_sessions (handle_hash,service_client_id,origin,auth_user_id,transaction_id,input_sha256,token_ciphertext,status,expires_at,created_at,updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,\\'active\\',$8,now(),now())',
        [
          createHash('sha256').update(handle).digest('hex'), client.id, client.origin,
          actor.rows[0].auth_user_id, transactionId,
          createHash('sha256').update('real-thread-tool-e2e:' + transactionId).digest('hex'),
          ciphertext, expiresAt,
        ],
      );
      process.stdout.write(JSON.stringify({ handle, expiresAt: Math.floor(expiresAt.getTime() / 1000) }));
    } finally {
      await pool.end();
    }
  `;
  return JSON.parse(execFileSync(process.execPath, ['--env-file=.env.local', '--import', 'tsx', '--input-type=module', '-e', source, email, WEB_BASE], {
    cwd: ADMIN_REPO,
    encoding: 'utf-8',
  }).trim()) as { handle: string; expiresAt: number };
}

function haveDistinctPersistedClaudeSessions(sourceThreadId: string, targetThreadId: string): boolean {
  const source = `
    import pg from 'pg';
    const [sourceThreadId, targetThreadId] = process.argv.slice(1);
    const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
    try {
      const result = await pool.query(
        'SELECT count(*)::int AS count, count(DISTINCT claude_session_id)::int AS distinct_count FROM public.chat_thread WHERE id = ANY($1::text[]) AND claude_session_id IS NOT NULL AND length(claude_session_id) > 0',
        [[sourceThreadId, targetThreadId]],
      );
      process.stdout.write(JSON.stringify({
        distinct: result.rowCount === 1
          && result.rows[0].count === 2
          && result.rows[0].distinct_count === 2,
      }));
    } finally {
      await pool.end();
    }
  `;
  const result = JSON.parse(execFileSync(process.execPath, [
    '--env-file=.env.local', '--input-type=module', '-e', source,
    sourceThreadId, targetThreadId,
  ], {
    cwd: ADMIN_REPO,
    encoding: 'utf-8',
  }).trim()) as { distinct: boolean };
  return result.distinct;
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
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${new URL(response.url()).pathname}`);
    }
  });
  return diagnostics;
}

async function getJson<T>(request: APIRequestContext, path: string, csrfToken: string): Promise<T> {
  const response = await request.get(`${WEB_BASE}${path}`, {
    headers: { 'x-ink-csrf': csrfToken },
  });
  expect(response.status(), await response.text()).toBe(200);
  return response.json() as Promise<T>;
}

async function rejectUnexpectedConfirmation(page: Page): Promise<void> {
  const dialogs = page.locator('[role="alertdialog"]:visible');
  const count = await dialogs.count();
  expect(count, 'Auto Thread orchestration must not wait for a confirmation dialog.').toBe(0);
}

async function waitForSourceTask(page: Page, csrfToken: string, sourceThreadId: string): Promise<TaskLinks> {
  let snapshot: TaskLinks = { source: null, created: [] };
  await expect.poll(async () => {
    await rejectUnexpectedConfirmation(page);
    snapshot = await getJson<TaskLinks>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(sourceThreadId)}/task-links`,
      csrfToken,
    );
    return snapshot.created.length;
  }, {
    timeout: 360_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(1);
  return snapshot;
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

test('create_thread starts an independent Claude session and wait_threads resumes the same parent turn', async ({ page }) => {
  test.setTimeout(900_000);
  await page.route('**/react-grab/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/javascript', body: '' });
  });
  const session = createActorSession(ACTOR_EMAIL);
  const diagnostics = diagnosticsFor(page);
  const apiRequests: string[] = [];
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/')) {
      apiRequests.push(`${request.method()} ${url.pathname}`);
    }
  });
  const marker = `THREAD-RETURN-E2E-${Date.now()}`;
  const prompt = `请创建一个新的独立会话，让新会话只回复“${marker}”。等待新会话完成后，在当前这一轮告诉我它的结果。`;

  await page.context().addCookies([{
    name: 'ink-dream-browser', value: session.handle, domain: 'localhost', path: '/',
    httpOnly: true, sameSite: 'Lax', expires: session.expiresAt,
  }]);
  await page.addInitScript(() => {
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });
  const sessionResponse = await page.request.get(`${WEB_BASE}/auth/session`);
  expect(sessionResponse.status(), await sessionResponse.text()).toBe(200);
  const csrfToken = (await sessionResponse.json() as { csrf_token: string }).csrf_token;
  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  const newChat = page.getByTitle(/^(New chat|新建对话)$/);
  if (await newChat.isVisible().catch(() => false)) await newChat.click();

  const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await expect(input).toBeVisible({ timeout: 30_000 });
  await input.fill(prompt);
  const createResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/threads'
  ));
  const agentRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  const agentResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status(), await createResponse.text()).toBe(200);
  const sourceThreadId = (await createResponse.json() as { thread_id: string }).thread_id;
  const agentRequest = await agentRequestPromise;
  expect(agentRequest.postDataJSON()).toMatchObject({ id: sourceThreadId, resume: true });
  const agentResponse = await agentResponsePromise;
  expect(agentResponse.status(), await agentResponse.text()).toBe(200);

  const links = await waitForSourceTask(page, csrfToken, sourceThreadId);
  const task = links.created[0];
  expect(task.source_thread_id).toBe(sourceThreadId);
  expect(task.launch_status).not.toBe('failed');
  expect(task.launch_error_code).toBeNull();
  expect(task.thread_id).not.toBe(sourceThreadId);

  await expect.poll(async () => {
    const status = await getJson<ThreadStatus>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(task.thread_id)}/status`,
      csrfToken,
    );
    return status.running === false && status.turn_count >= 1;
  }, {
    timeout: 360_000,
    intervals: [1_000, 2_000, 5_000],
  }).toBe(true);

  const targetHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(task.thread_id)}/messages`,
    csrfToken,
  );
  expect(targetHistory.thread.id).toBe(task.thread_id);
  expect(targetHistory.thread).not.toHaveProperty('claude_session_id');
  expect(assistantText(targetHistory)).toContain(marker);

  await expect.poll(async () => {
    const status = await getJson<ThreadStatus>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(sourceThreadId)}/status`,
      csrfToken,
    );
    return status.running === false && status.turn_count >= 1;
  }, {
    timeout: 360_000,
    intervals: [1_000, 2_000, 5_000],
  }).toBe(true);

  const sourceHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(sourceThreadId)}/messages`,
    csrfToken,
  );
  const createTools = sourceHistory.messages
    .flatMap((message) => message.parts)
    .filter((part) => part.toolName?.endsWith('create_thread'));
  expect(createTools.length).toBe(1);
  expect(createTools[0].state).toBe('output-available');
  const waitTools = sourceHistory.messages
    .flatMap((message) => message.parts)
    .filter((part) => part.toolName?.endsWith('wait_threads'));
  expect(waitTools.length).toBeGreaterThanOrEqual(1);
  expect(waitTools.at(-1)?.state).toBe('output-available');
  expect(sourceHistory.thread).not.toHaveProperty('claude_session_id');
  expect(haveDistinctPersistedClaudeSessions(sourceThreadId, task.thread_id)).toBe(true);
  expect(assistantText(sourceHistory)).toContain(marker);

  await expect(page.getByText(prompt, { exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('region', { name: /^(此对话创建的任务|Tasks created by this conversation)$/ })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('region', { name: /^(任务结果|Task result)$/ })).toHaveCount(0);
  const createdTasks = page.getByRole('region', { name: /^(此对话创建的任务|Tasks created by this conversation)$/ });
  const openTarget = createdTasks.getByRole('button', { name: /^(打开聊天|Open chat)$/ }).first();
  await openTarget.click();
  await expect(page.getByRole('button', { name: /^(打开来源对话|Open the source conversation)$/ })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(marker, { exact: true })).toBeVisible();
  expect(apiRequests.filter((item) => item === 'POST /api/claude-agent')).toHaveLength(1);
  expect(apiRequests.some((item) => item.endsWith('/task-results'))).toBe(false);
  expect(diagnostics).toEqual([]);
});
