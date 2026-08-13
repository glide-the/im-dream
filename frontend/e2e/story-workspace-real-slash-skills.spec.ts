// [Input] Real local actor, persisted Dream Run, and installed Deck plugin inventory.
// [Output] Visible-browser evidence that shared Chat suggests installed Skills without sending or workflow controls.
// [Pos] Opt-in non-cloning Story Workspace real-data QA.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const ENABLED = process.env.INK_REAL_SLASH_QA === '1';
const SEND_ENABLED = process.env.INK_REAL_SLASH_SEND === '1';
const WEB_BASE = process.env.INK_REAL_SLASH_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = process.env.INK_REAL_SLASH_RUN_ID
  ?? 'run_21d5990b83ea49f984e56ff068228188';
const ACTOR_EMAIL = process.env.INK_REAL_SLASH_ACTOR_EMAIL
  ?? 'dmeck123@suoxya.com';
const THREAD_ID = process.env.INK_REAL_SLASH_THREAD_ID
  ?? 'b75bab24-dca5-5bf3-8d22-cbc9e972d853';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');
const DRAMA_SKILLS = [
  'drama-asset',
  'drama-doctor',
  'drama-edit',
  'drama-init',
  'drama-payoff',
  'drama-plan',
  'drama-promote',
  'drama-prompt',
  'drama-query',
  'drama-render',
  'drama-script',
  'drama-storyboard',
  'drama-voice',
] as const;

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Set INK_REAL_SLASH_QA=1 to use the persisted local actor and Run.');

function createActorToken(email: string): string {
  const source = [
    "from dotenv import load_dotenv",
    "load_dotenv('.env')",
    'import auth, database, sys',
    'db = database.get_db()',
    "user = db.execute('select id, email from users where email = %s', (sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'], user['email']))",
  ].join('; ');
  return execFileSync(BACKEND_PYTHON, ['-c', source, email], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

interface ThreadFacts {
  readonly messageCount: number;
  readonly latestAssistantId: string | null;
  readonly latestAssistantModel: string | null;
  readonly latestAssistantTextLength: number;
}

function readThreadFacts(threadId: string): ThreadFacts {
  const source = [
    "from dotenv import load_dotenv",
    "load_dotenv('.env')",
    'import database, json, sys',
    'db = database.get_db()',
    "count = db.execute('select count(*) as value from chat_message where thread_id = %s', (sys.argv[1],)).fetchone()['value']",
    "row = db.execute(\"select id, metadata, parts from chat_message where thread_id = %s and role = 'assistant' order by created_at desc limit 1\", (sys.argv[1],)).fetchone()",
    'db.close()',
    "metadata = json.loads(row['metadata']) if row and isinstance(row['metadata'], str) else (row['metadata'] if row else {})",
    "parts = json.loads(row['parts']) if row and isinstance(row['parts'], str) else (row['parts'] if row else [])",
    "text_length = sum(len(str(part.get('text', ''))) for part in parts if isinstance(part, dict))",
    "model = metadata.get('chatModel', {}).get('model') if isinstance(metadata, dict) else None",
    "print(json.dumps({'messageCount': count, 'latestAssistantId': row['id'] if row else None, 'latestAssistantModel': model, 'latestAssistantTextLength': text_length}))",
  ].join('; ');
  return JSON.parse(execFileSync(BACKEND_PYTHON, ['-c', source, threadId], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim()) as ThreadFacts;
}

test('real Dream thread lists installed slash Skills without a recommendation state machine', async ({
  browser,
}) => {
  test.setTimeout(120_000);
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const diagnostics: string[] = [];
  let agentPostCount = 0;
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().startsWith('Failed to load resource:')) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (request.method() === 'POST' && url.pathname === '/api/claude-agent') {
      agentPostCount += 1;
    }
  });

  const token = createActorToken(ACTOR_EMAIL);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    await page.goto(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);
    await expect(page.getByRole('heading', { name: '创作工作空间' })).toBeVisible();
    await expect(page.getByRole('button', { name: '构建第一集产物关联' })).toHaveCount(0);
    await expect(page.getByText(/推荐下一步|更多工作流操作/)).toHaveCount(0);

    await page.getByRole('button', { name: '打开 Dream Agent 消息' }).click();
    const composer = page.getByRole('textbox', { name: '聊天输入' });
    await expect(composer).toBeEnabled();
    await composer.fill('/');

    const listbox = page.getByRole('listbox', { name: '已安装的 Skill 指令' });
    await expect(listbox).toBeVisible();
    for (const skill of DRAMA_SKILLS) {
      await expect(listbox.getByRole('option', { name: new RegExp(`/${skill}\\b`) })).toBeVisible();
    }
    await expect(listbox.getByRole('option')).toHaveCount(14);

    await listbox.getByRole('option', { name: /\/drama-script\b/ }).click();
    await expect(composer).toHaveText('/drama-script ');
    expect(agentPostCount).toBe(0);

    const overflow = await page.evaluate(() => ({
      body: document.body.scrollWidth - window.innerWidth,
      root: document.documentElement.scrollWidth - window.innerWidth,
    }));
    expect(overflow.body).toBeLessThanOrEqual(1);
    expect(overflow.root).toBeLessThanOrEqual(1);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});

test('real deepseek-v4-pro resumes the Dream thread for a read-only drama query', async ({
  browser,
}) => {
  test.skip(!SEND_ENABLED, 'Set INK_REAL_SLASH_SEND=1 to make one real model request.');
  test.setTimeout(300_000);
  const before = readThreadFacts(THREAD_ID);
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const token = createActorToken(ACTOR_EMAIL);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    await page.goto(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);
    await page.getByRole('button', { name: '打开 Dream Agent 消息' }).click();
    const composer = page.getByRole('textbox', { name: '聊天输入' });
    await expect(composer).toBeEnabled();
    const query = '/drama-query 请只读取当前工作台，简要告诉我已经有哪些 Project 和 Episode 产物；不要修改任何文件。';
    await composer.fill(query);
    await page.getByRole('button', { name: '发送消息' }).click();
    await expect(page.getByText(query, { exact: true })).toBeVisible();

    let after = before;
    await expect.poll(() => {
      after = readThreadFacts(THREAD_ID);
      return after.latestAssistantId;
    }, {
      message: 'the resumed real thread should persist a new assistant response',
      timeout: 240_000,
      intervals: [1_000, 2_000, 5_000],
    }).not.toBe(before.latestAssistantId);
    expect(after.messageCount).toBeGreaterThanOrEqual(before.messageCount + 2);
    expect(after.latestAssistantModel).toBe('deepseek-v4-pro');
    expect(after.latestAssistantTextLength).toBeGreaterThan(20);
    await expect(page.getByRole('button', { name: /停止生成|Stop generating/ })).toHaveCount(0);
    await expect(composer).toBeEnabled();
  } finally {
    await context.close();
  }
});
