// [Input] A named existing authenticated actor, installed ntn, connected Notion connector, and normal Dream Settings/Chat services.
// [Output] Real-business proof that visible Notion CLI capability reaches new/resumed Agent Bash, preserves optional-workers semantics, and leaves ordinary Chat healthy.
// [Pos] Opt-in Notion CLI Runtime acceptance; it preserves the connector and three-turn Chat thread for review.
// [Sync] 2026-08-30: verify Settings capability, current actor/thread Bash binding, read-only ntn execution, same-thread resume, and ordinary Chat regression safety.
// [Sync] 2026-09-01: require the live capability catalog's common/platform
//                    package schema v5 before Runtime acceptance.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_NOTION_CLI_QA === '1';
const WEB_BASE = process.env.INK_REAL_NOTION_CLI_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_NOTION_CLI_ACTOR_EMAIL ?? '';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

type ThreadStatus = {
  running: boolean;
  turn_count: number;
};

type PersistedPart = {
  type?: string;
  toolName?: string;
  state?: string;
  text?: string;
  input?: unknown;
  output?: unknown;
};

type ThreadMessages = {
  thread: { id: string; title?: string | null };
  messages: Array<{ role: string; parts: PersistedPart[] }>;
};

type NotionCapabilities = {
  catalog: {
    schema_version: number;
    cli_installation: { status: string };
    skills: Array<{ id: string; availability: string }>;
  };
};

const IMPACT_SCOPE = {
  actorConnector: 'one named existing authenticated actor and connector; unchanged',
  threadProjection: 'one normal thread projection refreshed on every turn',
  remoteOperation: 'doctor and current-user identity reads only; no Notion mutation or response body retention',
  chat: 'one normal persisted thread with new, resumed, and ordinary turns; retained for review',
  subscriptionOtherUsersAndContent: 'unchanged',
} as const;

test.use({
  channel: 'chrome',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.skip(!ENABLED, 'Set INK_REAL_NOTION_CLI_QA=1 with a named connected actor.');

function createActorToken(email: string): string {
  if (!email) throw new Error('INK_REAL_NOTION_CLI_ACTOR_EMAIL is required.');
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

async function getJson<T>(request: APIRequestContext, path: string, token: string): Promise<T> {
  const response = await request.get(`${WEB_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(200);
  return response.json() as Promise<T>;
}

async function approveExpectedBash(page: Page, threadId: string): Promise<boolean> {
  const dialogs = page.locator('[role="alertdialog"]:visible');
  const count = await dialogs.count();
  if (count === 0) return false;
  if (count !== 1) throw new Error('Multiple tool confirmations are visible.');
  const dialog = dialogs.first();
  const label = `${await dialog.getAttribute('aria-label') ?? ''} ${await dialog.textContent() ?? ''}`;
  if (!/(?:Bash|ntn)/i.test(label)) throw new Error('An unexpected tool confirmation blocked Notion CLI QA.');
  if (!/(?:NOTION_(?:API_TOKEN|KEYRING|WORKERS_CONFIG_FILE)|ntn)/.test(label)
    || /(?:\brm\b|\bmv\b|\bcp\b|\bcurl\b|\bwget\b|\bPOST\b|\bPATCH\b|\bDELETE\b|\s>[>|]?\s*[^&/])/.test(label)) {
    throw new Error('The visible Bash confirmation is outside the read-only Notion CLI QA allowlist.');
  }
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/tool-confirm'
  ), { timeout: 20_000 });
  await dialog.getByRole('button', { name: /^(同意|Approve)/ }).click();
  const response = await responsePromise;
  expect(response.status(), await response.text()).toBe(200);
  expect(response.request().postDataJSON()).toMatchObject({ thread_id: threadId, approved: true });
  return true;
}

async function waitForTurn(
  page: Page,
  token: string,
  threadId: string,
  expectedTurnCount: number,
  allowBash: boolean,
): Promise<void> {
  await expect.poll(async () => {
    const dialogs = page.locator('[role="alertdialog"]:visible');
    if (!allowBash && await dialogs.count()) {
      throw new Error('The ordinary Chat regression turn unexpectedly requested tool confirmation.');
    }
    if (allowBash && await approveExpectedBash(page, threadId)) return false;
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

function bashParts(payload: ThreadMessages): PersistedPart[] {
  return payload.messages.flatMap((message) => message.parts).filter((part) => (
    part.toolName === 'Bash'
  ));
}

function bashOutput(parts: PersistedPart[]): string {
  return parts.map((part) => (
    typeof part.output === 'string' ? part.output : JSON.stringify(part.output ?? '')
  )).join('\n');
}

function assertSafeNotionBashReceipt(parts: PersistedPart[]): void {
  expect(parts.length).toBeGreaterThanOrEqual(1);
  expect(parts.every((part) => part.state === 'output-available')).toBe(true);
  const output = bashOutput(parts);
  expect(output).toMatch(/NOTION_API_TOKEN=set/);
  expect(output).toMatch(/NOTION_KEYRING=set/);
  expect(output).toMatch(/NOTION_WORKERS_CONFIG_FILE=unset/);
  expect(output).toMatch(/ntn_version=ntn 0\.15\.1/);
  expect(output).toMatch(/ntn_doctor=ok/);
  expect(output).toMatch(/ntn_identity=ok/);
  expect(output).not.toMatch(/NOTION_API_TOKEN=(?!set\b|unset\b)\S+/);
  expect(output).not.toMatch(/NOTION_KEYRING=(?!set\b|unset\b)\S+/);
  expect(output).not.toMatch(/NOTION_WORKERS_CONFIG_FILE=(?!set\b|unset\b)\S+/);
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

test('visible Notion CLI capability executes a read-only ntn check in Chat', async ({ page }) => {
  test.setTimeout(900_000);
  expect(IMPACT_SCOPE).toEqual({
    actorConnector: 'one named existing authenticated actor and connector; unchanged',
    threadProjection: 'one normal thread projection refreshed on every turn',
    remoteOperation: 'doctor and current-user identity reads only; no Notion mutation or response body retention',
    chat: 'one normal persisted thread with new, resumed, and ordinary turns; retained for review',
    subscriptionOtherUsersAndContent: 'unchanged',
  });
  const token = createActorToken(ACTOR_EMAIL);
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  await page.goto(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
  await expect(page.getByRole('heading', { name: '资源链接', exact: true })).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: /Notion/ }).first().click();
  await expect(page.getByRole('heading', { name: 'Notion CLI', exact: true })).toBeVisible({ timeout: 30_000 });
  const cliSkill = page.getByRole('button', { name: /Notion CLI 工作空间数据助手/ });
  await expect(cliSkill).toContainText('可用', { timeout: 30_000 });

  const capabilities = await getJson<NotionCapabilities>(
    page.request,
    '/api/connectors/notion/capabilities',
    token,
  );
  expect(capabilities.catalog.schema_version).toBe(5);
  expect(capabilities.catalog.cli_installation.status).toBe('installed');
  expect(capabilities.catalog.skills).toContainEqual(expect.objectContaining({
    id: 'notion-cli',
    availability: 'available',
  }));

  await page.getByRole('button', { name: '返回应用' }).click();
  const navigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await navigation.getByRole('button', { name: /^(Chat|对话)$/ }).click();
  await page.waitForURL(`${WEB_BASE}/story-workspace/chat`);
  const newChat = page.getByTitle(/^(New chat|新建对话)$/);
  if (await newChat.isVisible().catch(() => false)) await newChat.click();

  const prompt = '请使用 notion-cli Skill 做一次只读连接验收。在 Bash 中对 NOTION_API_TOKEN、NOTION_KEYRING、NOTION_WORKERS_CONFIG_FILE 分别只输出“变量名=set”或“变量名=unset”，不得输出变量值；再只读执行 ntn --version、ntn doctor 和 ntn api v1/users/me，把后两项响应正文丢弃，只输出 ntn_version=<版本>、ntn_doctor=ok|failed、ntn_identity=ok|failed。不要输出完整环境、内部路径、凭证、API 返回对象或 Notion 页面内容，也不要创建、修改或删除任何 Notion 数据。最终回答不要复述环境变量名或内部实现，只说 Notion CLI 是否可用、系统是否会自动恢复和用户是否需要操作。';
  const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await expect(input).toBeVisible();
  await input.fill(prompt);
  const createPromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/threads'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const createResponse = await createPromise;
  expect(createResponse.status(), await createResponse.text()).toBe(200);
  const threadId = (await createResponse.json() as { thread_id: string }).thread_id;

  await waitForTurn(page, token, threadId, 1, true);
  const firstHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  const firstBashParts = bashParts(firstHistory);
  assertSafeNotionBashReceipt(firstBashParts);
  const firstAnswer = assistantText(firstHistory);
  expect(firstAnswer.length).toBeGreaterThan(0);
  expect(firstAnswer).not.toMatch(/NOTION_(?:API_TOKEN|HOME|KEYRING|WORKERS_CONFIG_FILE)|\.notion-home/);
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
  const resumePrompt = '请在同一对话中重新执行刚才完全相同的只读 Notion CLI 验收，以确认恢复后的 Agent Bash 使用本轮最新连接；Bash 仍然只输出 set/unset、版本和 ok|failed，不输出任何值、路径或 API 正文。最终回答只表达 Notion CLI 是否可用和用户是否需要操作，不复述环境变量名或内部实现。';
  const resumeInput = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await resumeInput.fill(resumePrompt);
  const resumeRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const resumeRequest = await resumeRequestPromise;
  expect(resumeRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
  await waitForTurn(page, token, threadId, 2, true);
  const resumedHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  const resumedBashParts = bashParts(resumedHistory);
  expect(resumedBashParts.length).toBeGreaterThan(firstBashParts.length);
  assertSafeNotionBashReceipt(resumedBashParts.slice(firstBashParts.length));
  expect(assistantText(resumedHistory)).not.toMatch(/NOTION_(?:API_TOKEN|HOME|KEYRING|WORKERS_CONFIG_FILE)|\.notion-home/);

  const ordinaryPrompt = '连接检查已完成。现在不要调用任何工具或访问网络，只回复：普通对话正常。';
  const ordinaryInput = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await ordinaryInput.fill(ordinaryPrompt);
  const ordinaryRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const ordinaryRequest = await ordinaryRequestPromise;
  expect(ordinaryRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
  await waitForTurn(page, token, threadId, 3, false);
  const finalHistory = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  expect(bashParts(finalHistory)).toHaveLength(resumedBashParts.length);
  expect(assistantText(finalHistory)).toContain('普通对话正常');
  expect(unexpectedThreadCreations).toBe(0);
  expect(diagnostics).toEqual([]);
});
