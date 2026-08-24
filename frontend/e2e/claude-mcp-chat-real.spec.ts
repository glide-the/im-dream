// [Input] A named existing platform actor, one already-connected user-scope Claude MCP server, and the normal Chat UI/API/runtime.
// [Output] Real-business Resources → live tool inventory → visible Chat turn → MCP result → refresh → same-thread follow-up evidence.
// [Pos] Opt-in read-only Claude MCP Chat acceptance; it preserves the server credential and the created Chat thread for review.
// [Sync] 2026-08-20: prove an authenticated user-scope MCP server is available through the actual Chat composer and after refresh.
// [Sync] 2026-08-20: verify the Resources detail reads live public-SDK tool metadata before Chat uses the same identity.
// [Sync] 2026-08-24: bind visible approval to the exact thread and require a successful canonical confirmation response.
// [Sync] 2026-08-25: consume the authoritative authenticated label, explicit safe-tool input, and Admin-owned database environment.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_MCP_CHAT_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_MCP_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_MCP_ACTOR_EMAIL ?? '';
const SERVER_NAME = process.env.INK_REAL_CLAUDE_MCP_SERVER_NAME ?? '';
const SAFE_INSPECTION_TOOL = process.env.INK_REAL_CLAUDE_MCP_SAFE_TOOL ?? 'get_server_info';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

const IMPACT_SCOPE = {
  actor: 'one named existing platform user',
  mcpConfiguration: 'one existing connected user-scope server, left connected and unchanged',
  remoteOperation: 'read-only server inspection; no create, update, or delete request',
  chat: 'one normal persisted thread with two model turns, retained for review',
  subscriptionAndOtherUsers: 'unchanged',
} as const;

type ThreadStatus = {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
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
test.skip(!ENABLED, 'Set INK_REAL_CLAUDE_MCP_CHAT_QA=1 with the named actor and connected server.');

function requireInputs(): void {
  if (!ACTOR_EMAIL || !SERVER_NAME) {
    throw new Error(
      'INK_REAL_CLAUDE_MCP_ACTOR_EMAIL and INK_REAL_CLAUDE_MCP_SERVER_NAME are required.',
    );
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
    throw new Error('Multiple tool confirmations are visible in the MCP Chat journey.');
  }
  const dialog = dialogs.first();
  const accessibleName = await dialog.getAttribute('aria-label');
  if (!accessibleName?.includes(`mcp__${SERVER_NAME}__${SAFE_INSPECTION_TOOL}`)) {
    throw new Error('An unexpected tool confirmation blocked the MCP Chat journey.');
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

test('connected MCP works in visible Chat and the same thread after refresh', async ({ page }) => {
  test.setTimeout(600_000);
  requireInputs();
  expect(IMPACT_SCOPE).toEqual({
    actor: 'one named existing platform user',
    mcpConfiguration: 'one existing connected user-scope server, left connected and unchanged',
    remoteOperation: 'read-only server inspection; no create, update, or delete request',
    chat: 'one normal persisted thread with two model turns, retained for review',
    subscriptionAndOtherUsers: 'unchanged',
  });

  const token = createActorToken(ACTOR_EMAIL);
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
  const card = page.getByRole('article', { name: `MCP 服务 ${SERVER_NAME}` });
  await expect(card).toContainText('已认证', { timeout: 30_000 });

  await card.getByRole('button', { name: '管理与工具' }).click();
  await expect(page.getByRole('heading', { name: `${SERVER_NAME} MCP Server` })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole('tab', { name: 'Tools 41' })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole('article', {
    name: `MCP 工具 ${SAFE_INSPECTION_TOOL}`,
  })).toBeVisible();
  await page.getByRole('button', { name: '资源连接器' }).click();
  await expect(card).toContainText('已认证', { timeout: 30_000 });

  await page.getByRole('button', { name: '返回应用' }).click();
  const navigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await navigation.getByRole('button', { name: /^(Chat|对话)$/ }).click();
  await page.waitForURL(`${WEB_BASE}/story-workspace/chat`);
  const newChat = page.getByTitle(/^(New chat|新建对话)$/);
  if (await newChat.isVisible().catch(() => false)) await newChat.click();

  const firstPrompt = `请准确使用已连接的 ${SERVER_NAME} MCP 调用只读工具 ${SAFE_INSPECTION_TOOL}，简要告诉我调用是否成功。不要创建、修改或删除任何远端内容。`;
  const firstInput = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await expect(firstInput).toBeVisible();
  await firstInput.fill(firstPrompt);
  const createResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/threads'
  ));
  const firstAgentRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status(), await createResponse.text()).toBe(200);
  const threadId = (await createResponse.json() as { thread_id: string }).thread_id;
  const firstAgentRequest = await firstAgentRequestPromise;
  expect(firstAgentRequest.postDataJSON()).toMatchObject({
    id: threadId,
    resume: true,
  });

  await waitForTurn(page, token, threadId, 1);
  const firstHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  const firstMcpParts = mcpToolParts(firstHistory);
  expect(firstMcpParts.length).toBeGreaterThanOrEqual(1);
  expect(firstMcpParts.every((part) => (
    part.toolName === `mcp__${SERVER_NAME}__${SAFE_INSPECTION_TOOL}`
  ))).toBe(true);
  expect(firstMcpParts.every((part) => part.state === 'output-available')).toBe(true);
  expect(assistantText(firstHistory).length).toBeGreaterThan(0);
  await expect(page.getByText(firstPrompt, { exact: true })).toBeVisible();

  const threadTitle = firstHistory.thread.title?.trim();
  expect(threadTitle).toBeTruthy();
  await page.reload();
  const historyEntry = page.getByTitle(threadTitle!).first();
  await expect(historyEntry).toBeVisible({ timeout: 30_000 });
  await historyEntry.click();
  await expect(page.getByText(firstPrompt, { exact: true })).toBeVisible({ timeout: 30_000 });

  let unexpectedThreadCreations = 0;
  page.on('request', (request) => {
    if (request.method() === 'POST'
      && new URL(request.url()).pathname === '/api/claude-agent/threads') {
      unexpectedThreadCreations += 1;
    }
  });
  const followUp = `继续刚才的连接检查，必须再调用同一个 ${SERVER_NAME} MCP 的只读工具 ${SAFE_INSPECTION_TOOL}，并简短回答。`;
  const followUpInput = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await followUpInput.fill(followUp);
  const followUpRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const followUpRequest = await followUpRequestPromise;
  expect(followUpRequest.postDataJSON()).toMatchObject({
    id: threadId,
    resume: true,
  });

  await waitForTurn(page, token, threadId, 2);
  const finalHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  const finalMcpParts = mcpToolParts(finalHistory);
  expect(finalMcpParts.length).toBeGreaterThan(firstMcpParts.length);
  expect(finalMcpParts.every((part) => (
    part.toolName === `mcp__${SERVER_NAME}__${SAFE_INSPECTION_TOOL}`
  ))).toBe(true);
  expect(finalMcpParts.every((part) => part.state === 'output-available')).toBe(true);
  expect(assistantText(finalHistory).length).toBeGreaterThan(assistantText(firstHistory).length);
  await expect(page.getByText(followUp, { exact: true })).toBeVisible();
  expect(unexpectedThreadCreations).toBe(0);
  expect(diagnostics).toEqual([]);
});
