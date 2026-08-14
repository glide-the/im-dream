// [Input] Existing local Dream Run, named real actor, shared Agent thread, and canonical character assets.
// [Output] Headless proof that a human read-only turn publishes and renders the complete last-good character document.
// [Pos] Opt-in real-data acceptance for canonical asset -> Hook stage -> actor API -> Execution focus.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CHARACTER_CONTENT_QA === '1';
const WEB_BASE = process.env.INK_REAL_CHARACTER_CONTENT_QA_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = process.env.INK_REAL_CHARACTER_CONTENT_QA_RUN_ID
  ?? 'run_4d3599ecce724aed82af882ada451aae';
const ACTOR_EMAIL = process.env.INK_REAL_CHARACTER_CONTENT_QA_ACTOR_EMAIL
  ?? 'test111@suoxya.com';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Dream business contract and impact scope:
 *
 * | Fact | Authority | Expected impact |
 * | Character details | canonical character Markdown | unchanged; fully published and displayed |
 * | Character list summary | characters stage summary | unchanged and compact |
 * | Character focus document | same stage item's Hook-published content | changes from legacy absence to full document |
 * | Project, Episode, all canonical files | current workspace | must remain byte-identical |
 * | Conversation | bound Chat thread + Claude session | same IDs, one new read-only turn |
 * | Public consumer | actor-scoped dream-files + Execution focus | shows identity, appearance, relations, motivation |
 */
const IMPACT_SCOPE = Object.freeze({
  canonicalWorkspace: 'must-remain-unchanged',
  characterStageDocument: 'legacy-stage-upgrades-after-successful-turn',
  threadAndSession: 'must-remain-unchanged',
  projectAndEpisode: 'must-remain-unchanged',
});

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 800 },
});
test.skip(!ENABLED, 'Set INK_REAL_CHARACTER_CONTENT_QA=1 for this real-data acceptance.');

interface RunFacts {
  readonly threadId: string;
  readonly actorId: string;
  readonly actorEmail: string;
}

interface ThreadFacts {
  readonly assistantId: string | null;
  readonly claudeSessionId: string | null;
  readonly model: string | null;
  readonly text: string;
}

function backendScript(source: string, args: readonly string[]): string {
  return execFileSync(BACKEND_PYTHON, ['-c', source, ...args], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

function resolveRunFacts(): RunFacts {
  return JSON.parse(backendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database,json,sys',
    'db=database.get_db()',
    "row=db.execute(\"select created_by,source_voice_thread_id from workflow_runs where id=%s\",(sys.argv[1],)).fetchone()",
    "actor=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[2],)).fetchone()",
    'db.close()',
    "assert row is not None, 'run not found'",
    "assert actor is not None, 'actor not found'",
    "assert str(actor['id'])==str(row['created_by']), 'run actor mismatch'",
    "print(json.dumps({'threadId':row['source_voice_thread_id'],'actorId':str(row['created_by']),'actorEmail':actor['email']}))",
  ].join(';'), [RUN_ID, ACTOR_EMAIL])) as RunFacts;
}

function createActorToken(email: string): string {
  return backendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import auth,database,sys',
    'db=database.get_db()',
    "user=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'],user['email']))",
  ].join(';'), [email]);
}

function threadFacts(threadId: string): ThreadFacts {
  return JSON.parse(backendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database,json,sys',
    'db=database.get_db()',
    "row=db.execute(\"select id,metadata,parts from chat_message where thread_id=%s and role='assistant' order by created_at desc limit 1\",(sys.argv[1],)).fetchone()",
    "thread=db.execute(\"select claude_session_id from chat_thread where id=%s\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "metadata=json.loads(row['metadata']) if row and isinstance(row['metadata'],str) else (row['metadata'] if row else {})",
    "parts=json.loads(row['parts']) if row and isinstance(row['parts'],str) else (row['parts'] if row else [])",
    "text='\\n'.join(str(p.get('text') or '') for p in parts if isinstance(p,dict) and p.get('type')=='text')",
    "print(json.dumps({'assistantId':row['id'] if row else None,'claudeSessionId':thread['claude_session_id'] if thread else None,'model':metadata.get('chatModel',{}).get('model') if isinstance(metadata,dict) else None,'text':text},ensure_ascii=False))",
  ].join(';'), [threadId])) as ThreadFacts;
}

function canonicalHashes(threadId: string): Record<string, string> {
  return JSON.parse(backendScript([
    'import hashlib,json,pathlib,sys',
    "root=pathlib.Path('data/agent-workspace')/sys.argv[1]",
    "paths=sorted([p for top in ('assets','stories') for p in (root/top).rglob('*') if p.is_file()])",
    "print(json.dumps({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},sort_keys=True))",
  ].join(';'), [threadId])) as Record<string, string>;
}

function diagnosticsFor(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().startsWith('Failed to load resource:')) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  return diagnostics;
}

async function dreamFiles(page: Page, token: string): Promise<Record<string, unknown>> {
  const response = await page.request.get(
    `${WEB_BASE}/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(response.status(), await response.text()).toBe(200);
  return await response.json() as Record<string, unknown>;
}

test('real user reads the complete 老头 character document without changing workspace facts', async ({ browser }) => {
  test.setTimeout(480_000);
  expect(IMPACT_SCOPE).toEqual({
    canonicalWorkspace: 'must-remain-unchanged',
    characterStageDocument: 'legacy-stage-upgrades-after-successful-turn',
    threadAndSession: 'must-remain-unchanged',
    projectAndEpisode: 'must-remain-unchanged',
  });
  const run = resolveRunFacts();
  expect(run.actorEmail).toBe(ACTOR_EMAIL);
  const token = createActorToken(ACTOR_EMAIL);
  const beforeThread = threadFacts(run.threadId);
  const beforeHashes = canonicalHashes(run.threadId);
  expect(beforeThread.claudeSessionId).toBeTruthy();

  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    await expect(page.locator('h1').first()).toBeVisible();
    await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
    const composer = page.getByRole('textbox', { name: '聊天输入' });
    await expect(composer).toBeVisible();
    await expect(composer).toBeEnabled();
    const request = '打开老头（庖丁）的人物资料，告诉我他的身份、外形、人物关系和动机是什么。这次只查看，不要修改故事内容。';
    await composer.fill(request);
    await page.getByRole('button', { name: '发送消息' }).click();
    await expect(page.getByText(request, { exact: true }).last()).toBeVisible();

    let afterThread = beforeThread;
    await expect.poll(() => {
      afterThread = threadFacts(run.threadId);
      return afterThread.assistantId === beforeThread.assistantId ? null : afterThread.assistantId;
    }, {
      message: 'the real read-only turn and successful Hook should settle',
      timeout: 360_000,
      intervals: [500, 1_000, 2_000],
    }).not.toBeNull();
    await expect(page.getByRole('button', { name: /停止生成|Stop generating/ })).toHaveCount(0);
    await expect(composer).toBeEnabled();

    expect(afterThread.claudeSessionId).toBe(beforeThread.claudeSessionId);
    expect(afterThread.model).toBe('deepseek-v4-pro');
    expect(afterThread.text).toContain('老头');
    expect(canonicalHashes(run.threadId)).toEqual(beforeHashes);

    const payload = await dreamFiles(page, token) as {
      stages?: { characters?: { items?: Array<Record<string, unknown>> } };
    };
    const character = payload.stages?.characters?.items?.find(
      (item) => item.entityId === 'lao-tou',
    );
    expect(character).toMatchObject({
      entityId: 'lao-tou',
      displayName: '老头（庖丁）',
      summary: '身份：夏都王宫掌厨，实为商地出身的故人。',
    });
    expect(String(character?.content ?? '')).toContain('外形：满头白发');
    expect(String(character?.content ?? '')).toContain('人物关系：');
    expect(String(character?.content ?? '')).toContain('动机：隐忍多年的商地故人');

    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    await page.getByText('Dream 初稿阶段投影', { exact: true }).click();
    await page.getByRole('tab', { name: /Assets/ }).click();
    await page.getByRole('button').filter({ hasText: '老头（庖丁）' }).click();
    await expect(page.getByText('完整资产资料', { exact: true })).toBeVisible();
    await expect(page.getByText('外形：满头白发，围裙满是油渍，佝偻但有精气神。', { exact: true }))
      .toBeVisible();
    await expect(page.getByText('人物关系：', { exact: true })).toBeVisible();
    await expect(page.getByText('对伊尹：识破其手法来历，暗中协助、传递商地情报。', { exact: true }))
      .toBeVisible();
    await expect(page.getByText('对夏桀：隐忍多年，潜伏于御膳房。', { exact: true })).toBeVisible();
    await expect(page.getByText('动机：隐忍多年的商地故人，等待拨乱反正的一天。', { exact: true }))
      .toBeVisible();
    expect(await page.evaluate(() => (
      document.documentElement.scrollWidth - document.documentElement.clientWidth
    ))).toBeLessThanOrEqual(1);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});
