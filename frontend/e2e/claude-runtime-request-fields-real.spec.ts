// [Input] A named existing actor, the normal Dream/Admin/Gateway/PostgreSQL topology, and the exact Runtime candidate or release under acceptance.
// [Output] Visible two-turn same-Thread Chat/resume proof plus content-free Gateway evidence for max_tokens, output_config.effort, stream, and header redaction.
// [Pos] Opt-in real-business Runtime request-contract acceptance; it preserves the created Thread and never prints request content or credentials.
// [Sync] 2026-08-28: verify Runtime 0.1.2 projects bounded output controls at the final Gateway capture boundary.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_REQUEST_FIELDS_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_REQUEST_FIELDS_WEB_BASE
  ?? 'http://127.0.0.1:5173';
const API_BASE = process.env.INK_REAL_CLAUDE_REQUEST_FIELDS_API_BASE
  ?? 'http://127.0.0.1:8765';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_REQUEST_FIELDS_EMAIL ?? '';
const EXPECTED_EFFORT = process.env.INK_REAL_CLAUDE_REQUEST_FIELDS_EFFORT ?? '';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.skip(!ENABLED, 'Run only with the named real actor, Deck, and expected Runtime effort.');

type ThreadStatus = {
  readonly running: boolean;
  readonly lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  readonly turn_count: number;
};

type ThreadMessages = {
  readonly thread: { readonly id: string; readonly title?: string | null };
  readonly messages: ReadonlyArray<{
    readonly role: string;
    readonly parts: ReadonlyArray<{ readonly type?: string; readonly text?: string }>;
  }>;
};

type GatewayEvidence = {
  readonly requestId: string;
  readonly model: string;
  readonly maxTokens: number;
  readonly effort: string | null;
  readonly stream: boolean;
  readonly authorization: string | null;
};

function requireInputs(): void {
  if (!ACTOR_EMAIL || !EXPECTED_EFFORT) {
    throw new Error('Actor email and expected Runtime effort are required.');
  }
  if (!['low', 'medium', 'high', 'xhigh', 'max'].includes(EXPECTED_EFFORT)) {
    throw new Error('Expected Runtime effort is invalid.');
  }
}

function backendJson(source: string, ...args: string[]): unknown {
  return JSON.parse(execFileSync(BACKEND_PYTHON, ['-c', source, ...args], {
    cwd: BACKEND_DIR,
    encoding: 'utf8',
  }));
}

function databasePrelude(): string[] {
  return [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import json,os,sys',
    'from persistence.config import load_database_url_from_env_file',
    "load_database_url_from_env_file(override=True) if os.environ.get('INK_LOAD_DATABASE_URL_FROM_ENV_FILE') == '1' else None",
    'import database',
  ];
}

function createActorToken(email: string): string {
  const source = [
    ...databasePrelude(),
    'import auth',
    'db=database.get_db()',
    "user=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(json.dumps({'token':auth.create_access_token(user['id'],user['email'])}))",
  ].join(';');
  return (backendJson(source, email) as { token: string }).token;
}

function gatewayBaseline(): string {
  const source = [
    ...databasePrelude(),
    'db=database.get_db()',
    'row=db.execute("select now() as value").fetchone()',
    'db.close()',
    "print(json.dumps({'value':row['value'].isoformat()}))",
  ].join(';');
  return (backendJson(source) as { value: string }).value;
}

function gatewayEvidence(email: string, after: string): GatewayEvidence[] {
  const source = [
    ...databasePrelude(),
    'db=database.get_db()',
    'rows=db.execute("""select r.id, p.requested_model, p.body_json->>\'max_tokens\' as max_tokens, p.body_json->\'output_config\'->>\'effort\' as effort, p.body_json->>\'stream\' as stream, p.headers->>\'authorization\' as authorization from gateway_requests r join platform_users u on u.id=r.platform_user_id join gateway_request_payloads p on p.gateway_request_id=r.id where u.email=%s and r.protocol=\'anthropic\' and r.created_at >= %s::timestamptz order by r.created_at asc""",(sys.argv[1],sys.argv[2])).fetchall()',
    'db.close()',
    "print(json.dumps([{'requestId':row['id'],'model':row['requested_model'],'maxTokens':int(row['max_tokens']),'effort':row['effort'],'stream':row['stream']=='true','authorization':row['authorization']} for row in rows]))",
  ].join(';');
  return backendJson(source, email, after) as GatewayEvidence[];
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    const value = message.text();
    if (message.type() === 'error'
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(value)) {
      diagnostics.push(`console: ${value}`);
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|react-grab\.js|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${new URL(url).pathname}`);
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
  token: string,
  path: string,
): Promise<T> {
  const response = await request.get(`${API_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(200);
  return response.json() as Promise<T>;
}

async function waitForIdle(
  page: Page,
  token: string,
  threadId: string,
  minimumTurns: number,
): Promise<void> {
  await expect.poll(async () => {
    const dialogs = page.locator('[role="alertdialog"]:visible');
    if (await dialogs.count()) {
      throw new Error('The read-only Runtime request acceptance unexpectedly requested tool confirmation.');
    }
    const status = await getJson<ThreadStatus>(
      page.request,
      token,
      `/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
    );
    return status.running === false && status.turn_count >= minimumTurns;
  }, {
    timeout: 240_000,
    intervals: [250, 500, 1_000, 2_000, 5_000],
  }).toBe(true);
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

test('Runtime under acceptance emits bounded output controls in first and resumed Chat turns', async ({
  page,
}) => {
  test.setTimeout(600_000);
  requireInputs();
  const token = createActorToken(ACTOR_EMAIL);
  const baseline = gatewayBaseline();
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  const seededTitle = `Runtime request fields QA ${Date.now()}`;
  const seededThreadResponse = await page.request.post(`${API_BASE}/api/claude-agent/threads`, {
    headers: { authorization: `Bearer ${token}` },
    data: { title: seededTitle },
  });
  expect(seededThreadResponse.status(), await seededThreadResponse.text()).toBe(200);
  const threadId = (await seededThreadResponse.json() as { thread_id: string }).thread_id;
  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  const historyEntry = page.getByTitle(seededTitle).first();
  await expect(historyEntry).toBeVisible({ timeout: 30_000 });
  await historyEntry.click();
  const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await expect(input).toBeVisible();
  const firstPrompt = '请只回复：候选 Runtime 请求验证通过。不要调用工具或访问网络。';
  await input.fill(firstPrompt);
  const firstAgentRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const firstAgentRequest = await firstAgentRequestPromise;
  expect(firstAgentRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
  await waitForIdle(page, token, threadId, 1);

  const firstHistory = await getJson<ThreadMessages>(
    page.request,
    token,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
  );
  expect(assistantText(firstHistory)).toContain('候选 Runtime 请求验证通过');
  await expect(page.getByText(firstPrompt, { exact: true })).toBeVisible({ timeout: 30_000 });
  const followUp = '继续刚才的验证，只回复：同一对话恢复通过。仍然不要调用工具或访问网络。';
  const followUpInput = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await followUpInput.fill(followUp);
  const followUpRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const followUpRequest = await followUpRequestPromise;
  expect(followUpRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
  await waitForIdle(page, token, threadId, 2);
  const finalHistory = await getJson<ThreadMessages>(
    page.request,
    token,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
  );
  expect(assistantText(finalHistory)).toContain('同一对话恢复通过');

  let evidence: GatewayEvidence[] = [];
  await expect.poll(() => {
    evidence = gatewayEvidence(ACTOR_EMAIL, baseline);
    return evidence.length;
  }, {
    timeout: 30_000,
    intervals: [250, 500, 1_000, 2_000],
  }).toBeGreaterThanOrEqual(2);
  expect(evidence.every((request) => Number.isSafeInteger(request.maxTokens)
    && request.maxTokens > 4_096)).toBe(true);
  expect(evidence.every((request) => request.effort === EXPECTED_EFFORT)).toBe(true);
  expect(evidence.every((request) => request.stream === true)).toBe(true);
  expect(evidence.every((request) => request.authorization === '[REDACTED]')).toBe(true);
  expect(evidence.every((request) => request.model.length > 0)).toBe(true);
  expect(diagnostics).toEqual([]);
});
