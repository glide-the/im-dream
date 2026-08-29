// [Input] A named existing authenticated actor, installed ntn, connected Notion connector, and normal Dream Settings/Chat services.
// [Output] Real-business proof that visible Notion CLI capability reaches one persisted Chat turn and a successful read-only Bash invocation.
// [Pos] Opt-in Notion CLI Runtime acceptance; it preserves the connector and created Chat thread for review.
// [Sync] 2026-08-30: verify Settings capability, current actor/thread sdk_env binding, and read-only ntn execution through visible Chat.

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

async function waitForTurn(page: Page, token: string, threadId: string): Promise<void> {
  await expect.poll(async () => {
    if (await approveExpectedBash(page, threadId)) return false;
    const status = await getJson<ThreadStatus>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
      token,
    );
    return status.running === false && status.turn_count >= 1;
  }, {
    timeout: 360_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(true);
}

test('visible Notion CLI capability executes a read-only ntn check in Chat', async ({ page }) => {
  test.setTimeout(480_000);
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
  expect(capabilities.catalog.schema_version).toBe(4);
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

  const prompt = '请使用 notion-cli Skill，在 Bash 中只执行 ntn --version 和 ntn api v1/users/me。只告诉我 CLI 是否可运行、当前用户接口是否读取成功；不要输出返回对象、环境变量、凭证或 Notion 页面内容，也不要创建、修改或删除任何 Notion 数据。';
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

  await waitForTurn(page, token, threadId);
  const history = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  const parts = history.messages.flatMap((message) => message.parts);
  const bashParts = parts.filter((part) => part.toolName === 'Bash');
  expect(bashParts.length).toBeGreaterThanOrEqual(1);
  expect(bashParts.every((part) => part.state === 'output-available')).toBe(true);
  const answer = history.messages
    .filter((message) => message.role === 'assistant')
    .flatMap((message) => message.parts)
    .filter((part) => part.type === 'text' && typeof part.text === 'string')
    .map((part) => part.text?.trim() ?? '')
    .filter(Boolean)
    .join('\n');
  expect(answer.length).toBeGreaterThan(0);
  expect(answer).not.toMatch(/NOTION_(?:API_TOKEN|HOME|KEYRING|WORKERS_CONFIG_FILE)/);
  expect(history.thread.title?.trim()).toBeTruthy();
  expect(diagnostics).toEqual([]);
});
