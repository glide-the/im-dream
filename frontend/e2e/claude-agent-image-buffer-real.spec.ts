// [Input] A named existing platform actor, normal Chat upload/UI/runtime, and one generated non-business PNG.
// [Output] Real-business proof that an image-read CLI message above 1 MiB reaches the persisted Chat result.
// [Pos] Opt-in Claude Agent image-buffer acceptance; it retains the created thread and changes no remote resource.
// [Sync] 2026-08-20: regress the public SDK max_buffer_size path after a 1,202,954-byte image Read message failed.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { Buffer } from 'node:buffer';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_AGENT_IMAGE_BUFFER_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_AGENT_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_AGENT_ACTOR_EMAIL ?? '';
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

const IMPACT_SCOPE = {
  actor: 'one named existing platform user',
  chat: 'one normal persisted thread and one model turn, retained for review',
  attachment: 'one generated non-business PNG stored through the normal visible upload path',
  allowedTool: 'built-in Read only',
  remoteMcpAndBusinessData: 'unchanged',
} as const;

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

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.describe.configure({ mode: 'serial' });
test.skip(
  !ENABLED,
  'Set INK_REAL_CLAUDE_AGENT_IMAGE_BUFFER_QA=1 with the named existing actor.',
);

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

async function generatedPng(page: Page): Promise<Buffer> {
  await page.setContent('<!doctype html><canvas id="fixture" width="896" height="512"></canvas>');
  const encoded = await page.evaluate(() => {
    const canvas = document.getElementById('fixture') as HTMLCanvasElement;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('canvas unavailable');
    const pixels = context.createImageData(canvas.width, canvas.height);
    let seed = 0x1a2b3c4d;
    for (let index = 0; index < pixels.data.length; index += 4) {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      pixels.data[index] = seed & 0xff;
      pixels.data[index + 1] = (seed >>> 8) & 0xff;
      pixels.data[index + 2] = (seed >>> 16) & 0xff;
      pixels.data[index + 3] = 0xff;
    }
    context.putImageData(pixels, 0, 0);
    return canvas.toDataURL('image/png').split(',', 2)[1];
  });
  return Buffer.from(encoded, 'base64');
}

test('visible image Chat accepts a CLI message larger than the SDK 1 MiB default', async ({ page }) => {
  test.setTimeout(600_000);
  if (!ACTOR_EMAIL) throw new Error('INK_REAL_CLAUDE_AGENT_ACTOR_EMAIL is required.');
  expect(IMPACT_SCOPE.remoteMcpAndBusinessData).toBe('unchanged');

  const token = createActorToken(ACTOR_EMAIL);
  const image = await generatedPng(page);
  expect(image.length).toBeGreaterThan(1024 * 1024);
  expect(image.length).toBeLessThan(4 * 1024 * 1024);
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  const newChat = page.getByTitle(/^(New chat|新建对话)$/);
  if (await newChat.isVisible().catch(() => false)) await newChat.click();

  await page.locator('input[type="file"]').setInputFiles({
    name: 'buffer-policy-qa.png',
    mimeType: 'image/png',
    buffer: image,
  });
  await expect(page.getByAltText('buffer-policy-qa.png')).toBeVisible();

  const prompt = '请打开并仔细查看我刚上传的图片附件，然后用一句话描述它的主要视觉特征。';
  const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await input.fill(prompt);
  const send = page.getByRole('button', { name: /^(Send message|发送消息)$/ });
  await expect(send).toBeEnabled({ timeout: 60_000 });
  const createResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/threads'
  ));
  await send.click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status(), await createResponse.text()).toBe(200);
  const threadId = (await createResponse.json() as { thread_id: string }).thread_id;

  await expect.poll(async () => {
    const dialogs = page.locator('[role="alertdialog"]:visible');
    if (await dialogs.count()) {
      throw new Error(`Unexpected confirmation in image-read journey: ${await dialogs.first().getAttribute('aria-label')}`);
    }
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

  const history = await getJson<ThreadMessages>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
    token,
  );
  const parts = history.messages.flatMap((message) => message.parts);
  const readParts = parts.filter((part) => part.toolName === 'Read');
  expect(readParts.length).toBeGreaterThanOrEqual(1);
  expect(readParts.every((part) => part.state === 'output-available')).toBe(true);
  const assistantText = history.messages
    .filter((message) => message.role === 'assistant')
    .flatMap((message) => message.parts)
    .filter((part) => part.type === 'text')
    .map((part) => part.text ?? '')
    .join('\n');
  expect(assistantText.length).toBeGreaterThan(0);
  expect(assistantText).not.toContain('maximum buffer size');
  await expect(page.getByText(prompt, { exact: true })).toBeVisible();
  expect(diagnostics).toEqual([]);
});
