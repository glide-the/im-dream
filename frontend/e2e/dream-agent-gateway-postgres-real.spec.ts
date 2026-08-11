// [Input] Owned Dream/Account services, disposable PostgreSQL, and a local no-charge Provider.
// [Output] Browser-to-Agent-to-Gateway-to-ledger correlation plus persisted Story bundle evidence.
// [Pos] Opt-in cross-service business E2E; Episode Artifact completion remains a separate release gate.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_BUSINESS_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const API_BASE = process.env.INK_REAL_DREAM_API_BASE ?? 'http://127.0.0.1:18765';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');
const TEST_EMAIL = 'ink-dream-round-20260810@example.invalid';
const MESSAGE_ID = 'dream-business-e2e-turn-001';

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Run only through the owned Dream business PostgreSQL E2E runner.');

function createToken(): string {
  const source = [
    'import auth, database, sys',
    'db = database.get_db()',
    'user = db.execute("SELECT id, email FROM users WHERE email = %s AND status = \'active\'", (sys.argv[1],)).fetchone()',
    'db.close()',
    "assert user is not None, 'isolated E2E actor missing'",
    "print(auth.create_access_token(user['id'], user['email']))",
  ].join('; ');
  return execFileSync(PYTHON, ['-c', source, TEST_EMAIL], {
    cwd: BACKEND_ROOT,
    encoding: 'utf-8',
  }).trim();
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  return diagnostics;
}

test('browser turn persists one correlated Gateway-backed Story bundle', async ({ page }) => {
  test.setTimeout(180_000);
  const diagnostics = diagnosticsFor(page);
  const token = createToken();
  await page.addInitScript((accessToken) => {
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${WEB_BASE}/login`);

  const result = await page.evaluate(async ({ apiBase, accessToken, messageId }) => {
    const headers = {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    };
    const threadResponse = await fetch(`${apiBase}/api/claude-agent/threads`, {
      method: 'POST', headers, body: JSON.stringify({ title: 'Dream business E2E' }),
    });
    const thread = await threadResponse.json() as { thread_id?: string };
    if (!threadResponse.ok || !thread.thread_id) {
      return { stage: 'thread', status: threadResponse.status, body: thread };
    }
    const agentResponse = await fetch(`${apiBase}/api/claude-agent`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        thread_id: thread.thread_id,
        message: {
          id: messageId,
          role: 'user',
          parts: [{ type: 'text', text: '生成一个两人物、两场景的中文短剧 JSON。' }],
        },
        model: 'dream-fast',
        max_turns: 1,
      }),
    });
    const stream = await agentResponse.text();
    const messagesResponse = await fetch(
      `${apiBase}/api/claude-agent/threads/${encodeURIComponent(thread.thread_id)}/messages`,
      { headers: { Authorization: `Bearer ${accessToken}` } },
    );
    const messages = await messagesResponse.json();
    const storiesResponse = await fetch(`${apiBase}/api/story-workspace/stories`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const stories = await storiesResponse.json();
    return {
      stage: 'complete',
      threadId: thread.thread_id,
      agentStatus: agentResponse.status,
      stream,
      messagesStatus: messagesResponse.status,
      messages,
      storiesStatus: storiesResponse.status,
      stories,
    };
  }, { apiBase: API_BASE, accessToken: token, messageId: MESSAGE_ID });

  if (result.stage === 'complete' && result.agentStatus !== 200) {
    throw new Error(`Agent returned ${result.agentStatus}: ${result.stream}`);
  }
  expect(result).toMatchObject({
    stage: 'complete',
    agentStatus: 200,
    messagesStatus: 200,
    storiesStatus: 200,
  });
  if (result.stage !== 'complete') throw new Error(JSON.stringify(result));
  const events = result.stream
    .split('\n')
    .filter((line) => line.startsWith('data: '))
    .map((line) => JSON.parse(line.slice(6)) as Record<string, unknown>);
  expect(events.map((event) => event.type)).toEqual([
    'message-metadata', 'text-start', 'text-delta', 'text-end',
    'message-final', 'story-workspace-output', 'finish',
  ]);
  expect(events.at(-1)).toMatchObject({ type: 'finish', finishReason: 'stop' });
  expect(events.find((event) => event.type === 'story-workspace-output')).toMatchObject({
    story_id: expect.any(String),
    review_status: 'pending',
    chat_thread_id: result.threadId,
  });
  expect(JSON.stringify(result.messages)).toContain(MESSAGE_ID);
  expect(result.stories).toMatchObject({
    data: [expect.objectContaining({
      title: '午夜咖啡馆',
      review_status: 'pending',
      character_count: 2,
      scene_count: 2,
    })],
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  expect(diagnostics).toEqual([]);
});
