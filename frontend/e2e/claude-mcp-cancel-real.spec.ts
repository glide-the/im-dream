// [Input] Named existing actor/Deck, normal services, one public OAuth MCP URL, and one server-owned stdio profile.
// [Output] Visible OAuth-operation cancel and live Agent-turn stop receipts with temporary Server cleanup and preserved Thread evidence.
// [Pos] Opt-in real-account cancel acceptance; no provider login, credential creation, remote mutation, shadow account, or fault injection.
// [Sync] 2026-08-25: add explicit Resources OAuth cancel plus Chat stop over the managed-DB MCP path.
// [Sync] 2026-08-25: detect OAuth through detail discovery; the create form no longer accepts an auth policy.
// [Sync] 2026-08-25: rely on automatic cache-first detail discovery and expose no inventory refresh control.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_MCP_CANCEL_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_MCP_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_MCP_ACTOR_EMAIL ?? '';
const DECK_ID = process.env.INK_REAL_CLAUDE_MCP_DECK_ID ?? '';
const OAUTH_SERVER_URL = process.env.INK_REAL_CLAUDE_MCP_OAUTH_SERVER_URL ?? '';
const STDIO_PROFILE_KEY = process.env.INK_REAL_CLAUDE_MCP_STDIO_PROFILE_KEY ?? '';
const OAUTH_SERVER_NAME = process.env.INK_REAL_CLAUDE_MCP_CANCEL_OAUTH_NAME ?? '';
const STDIO_SERVER_NAME = process.env.INK_REAL_CLAUDE_MCP_CANCEL_STDIO_NAME ?? '';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

type ThreadStatus = {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
  pending_tool_call_ids?: string[];
};

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.describe.configure({ mode: 'serial' });
test.skip(!ENABLED, 'Set INK_REAL_CLAUDE_MCP_CANCEL_QA=1 with explicit cancel inputs.');

function requireInputs(): void {
  if (!ACTOR_EMAIL || !DECK_ID || !OAUTH_SERVER_URL || !STDIO_PROFILE_KEY
    || !OAUTH_SERVER_NAME || !STDIO_SERVER_NAME) {
    throw new Error('Actor, Deck, OAuth URL, stdio profile, and both temporary Server names are required.');
  }
  if (!OAUTH_SERVER_URL.startsWith('https://')) {
    throw new Error('OAuth cancel acceptance requires an explicit HTTPS MCP URL.');
  }
  if (OAUTH_SERVER_NAME === STDIO_SERVER_NAME) {
    throw new Error('OAuth and stdio cancel Server names must be distinct.');
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

function databaseFacts(serverName: string): { server: boolean; credential: boolean } {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import os',
    "from persistence.config import load_database_url_from_env_file",
    "load_database_url_from_env_file(override=True) if os.environ.get('INK_LOAD_DATABASE_URL_FROM_ENV_FILE') == '1' else None",
    'import database,json,sys',
    'db=database.get_db()',
    "actor=db.execute(\"select id from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    "server=db.execute('select id from dream_mcp_servers where user_id=%s and server_key=%s',(actor['id'],sys.argv[2])).fetchone() if actor else None",
    "credential=db.execute('select id from dream_mcp_credentials where server_id=%s',(server['id'],)).fetchone() if server else None",
    'db.close()',
    "print(json.dumps({'server':bool(server),'credential':bool(credential)}))",
  ].join(';');
  return JSON.parse(execFileSync(BACKEND_PYTHON, ['-c', source, ACTOR_EMAIL, serverName], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  })) as { server: boolean; credential: boolean };
}

async function getStatus(
  request: APIRequestContext,
  token: string,
  threadId: string,
): Promise<ThreadStatus> {
  const response = await request.get(
    `${WEB_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(response.status(), await response.text()).toBe(200);
  return response.json() as Promise<ThreadStatus>;
}

async function cleanupServer(
  request: APIRequestContext,
  headers: Record<string, string>,
  serverName: string,
): Promise<void> {
  await request.post(`${WEB_BASE}/api/claude-mcp/servers/${encodeURIComponent(serverName)}/logout`, {
    headers,
  }).catch(() => undefined);
  await request.delete(`${WEB_BASE}/api/claude-mcp/servers/${encodeURIComponent(serverName)}`, {
    headers,
  }).catch(() => undefined);
}

async function closeThreadRuntime(
  request: APIRequestContext,
  headers: Record<string, string>,
  threadId: string | null,
): Promise<void> {
  if (!threadId) return;
  await request.delete(`${WEB_BASE}/api/claude-agent/session`, {
    headers,
    params: { session_id: threadId },
  }).catch(() => undefined);
}

async function openResources(page: Page, token: string): Promise<void> {
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);
  await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
  await expect(page.getByRole('heading', { name: 'Claude MCP 资源' })).toBeVisible();
  await expect(page.getByText('安全门禁已关闭此能力')).toHaveCount(0);
}

test('real actor visibly cancels an OAuth operation without creating a credential', async ({ page }) => {
  test.setTimeout(120_000);
  requireInputs();
  expect(databaseFacts(OAUTH_SERVER_NAME)).toEqual({ server: false, credential: false });
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  let removed = false;
  await openResources(page, token);
  try {
    await page.getByLabel('MCP 服务名称').fill(OAUTH_SERVER_NAME);
    await page.getByLabel('MCP 传输方式').selectOption('streamable_http');
    await page.getByLabel('MCP 服务 URL').fill(OAUTH_SERVER_URL);
    await page.getByRole('button', { name: '添加 MCP 服务' }).click();
    const card = page.getByRole('article', { name: `MCP 服务 ${OAUTH_SERVER_NAME}` });
    await expect(card).toContainText('已配置');
    await card.getByRole('button', { name: '管理与工具' }).click();
    await expect(page.getByRole('button', { name: /刷新 inventory|重试 inventory|重试探测/ })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '开始认证' })).toBeVisible({ timeout: 30_000 });

    const startResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && decodeURIComponent(new URL(response.url()).pathname)
        === `/api/claude-mcp/servers/${OAUTH_SERVER_NAME}/auth-operations`
    ));
    await page.getByRole('button', { name: '开始认证' }).click();
    const startResponse = await startResponsePromise;
    expect(startResponse.status(), await startResponse.text()).toBe(202);
    await expect(page.getByText('等待授权')).toBeVisible({ timeout: 30_000 });
    expect(databaseFacts(OAUTH_SERVER_NAME)).toEqual({ server: true, credential: false });

    const cancelResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && /\/api\/claude-mcp\/auth-operations\/[^/]+\/cancel$/.test(new URL(response.url()).pathname)
    ));
    await page.getByRole('button', { name: '取消' }).click();
    const cancelResponse = await cancelResponsePromise;
    expect(cancelResponse.status(), await cancelResponse.text()).toBe(200);
    await expect(page.getByText('等待授权')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '开始认证' })).toBeVisible();
    expect(databaseFacts(OAUTH_SERVER_NAME)).toEqual({ server: true, credential: false });

    await page.getByRole('button', { name: '资源连接器' }).click();
    const refreshedCard = page.getByRole('article', { name: `MCP 服务 ${OAUTH_SERVER_NAME}` });
    await refreshedCard.getByRole('button', { name: '移除' }).click();
    await expect(refreshedCard).toHaveCount(0);
    removed = true;
    expect(databaseFacts(OAUTH_SERVER_NAME)).toEqual({ server: false, credential: false });
  } finally {
    if (!removed) await cleanupServer(page.request, headers, OAUTH_SERVER_NAME);
  }
});

test('real actor visibly stops a running managed-MCP Chat turn', async ({ page }) => {
  test.setTimeout(180_000);
  requireInputs();
  expect(databaseFacts(STDIO_SERVER_NAME)).toEqual({ server: false, credential: false });
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  let threadId: string | null = null;
  let removed = false;
  await openResources(page, token);
  try {
    await page.getByLabel('MCP 服务名称').fill(STDIO_SERVER_NAME);
    await page.getByLabel('MCP 传输方式').selectOption('stdio');
    await page.getByLabel('MCP stdio profile key').fill(STDIO_PROFILE_KEY);
    await page.getByRole('button', { name: '添加 MCP 服务' }).click();
    const card = page.getByRole('article', { name: `MCP 服务 ${STDIO_SERVER_NAME}` });
    await expect(card).toContainText('已配置', { timeout: 30_000 });

    const threadTitle = `MCP visible cancel QA ${Date.now()}`;
    const threadResponse = await page.request.post(`${WEB_BASE}/api/claude-agent/threads`, {
      headers,
      data: { deckId: DECK_ID, title: threadTitle },
    });
    expect(threadResponse.status(), await threadResponse.text()).toBe(200);
    const thread = await threadResponse.json() as { thread_id: string; deck_id: string | null };
    expect(thread.deck_id).toBe(DECK_ID);
    threadId = thread.thread_id;

    await page.goto(`${WEB_BASE}/story-workspace/chat`);
    const historyEntry = page.getByTitle(threadTitle).first();
    await expect(historyEntry).toBeVisible({ timeout: 30_000 });
    await historyEntry.click();
    const prompt = `请通过 ${STDIO_SERVER_NAME} 只读连接检查传输状态；开始后我会手动停止本轮，不要创建、修改或删除任何内容。`;
    const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
    await input.fill(prompt);
    const agentResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname === '/api/claude-agent'
    ));
    await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
    const agentResponse = await agentResponsePromise;
    expect(agentResponse.status()).toBe(200);
    expect(agentResponse.headers()['content-type']).toContain('text/event-stream');
    await expect.poll(async () => (await getStatus(page.request, token, threadId!)).running, {
      timeout: 30_000,
      intervals: [100, 250, 500],
    }).toBe(true);

    const stopButton = page.getByRole('button', { name: /^(停止生成|Stop generating)$/ });
    await expect(stopButton).toBeVisible();
    const stopResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && new URL(response.url()).pathname
        === `/api/claude-agent/threads/${encodeURIComponent(threadId!)}/stop`
    ));
    await stopButton.click();
    const stopResponse = await stopResponsePromise;
    expect(stopResponse.status(), await stopResponse.text()).toBe(200);
    expect(await stopResponse.json()).toMatchObject({
      ok: true,
      thread_id: threadId,
      stop_requested: true,
      running: false,
    });
    await expect.poll(async () => {
      const status = await getStatus(page.request, token, threadId!);
      return {
        running: status.running,
        lifecycle: status.lifecycle,
        pending: status.pending_tool_call_ids ?? [],
      };
    }, { timeout: 30_000, intervals: [100, 250, 500, 1_000] }).toEqual({
      running: false,
      lifecycle: 'idle',
      pending: [],
    });
    await expect(stopButton).toHaveCount(0);
    await expect(page.getByText(prompt, { exact: true })).toBeVisible();

    await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
    const configuredCard = page.getByRole('article', { name: `MCP 服务 ${STDIO_SERVER_NAME}` });
    await expect(configuredCard).toContainText('已配置');
    await configuredCard.getByRole('button', { name: '移除' }).click();
    await expect(configuredCard).toHaveCount(0);
    removed = true;
    expect(databaseFacts(STDIO_SERVER_NAME)).toEqual({ server: false, credential: false });
  } finally {
    await closeThreadRuntime(page.request, headers, threadId);
    if (!removed) await cleanupServer(page.request, headers, STDIO_SERVER_NAME);
  }
});
