// [Input] Existing local Dream Run owned by test111@suoxya.com and its published workspace facts.
// [Output] Read-only Chromium proof for the default Draft surface and the Draft/Sync view switch.
// [Pos] Opt-in real-data acceptance for Story Workspace Execution presentation; sends no Agent turn.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_EXECUTION_VIEW_QA === '1';
const WEB_BASE = process.env.INK_REAL_EXECUTION_VIEW_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = process.env.INK_REAL_EXECUTION_VIEW_RUN_ID
  ?? 'run_4d3599ecce724aed82af882ada451aae';
const ACTOR_EMAIL = process.env.INK_REAL_EXECUTION_VIEW_ACTOR_EMAIL
  ?? 'test111@suoxya.com';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

const IMPACT_SCOPE = Object.freeze({
  canonicalWorkspace: 'must-remain-unchanged',
  publishedStages: 'must-remain-unchanged',
  threadAndSession: 'out-of-scope-and-untouched',
  executionView: 'browser-local-presentation-only',
});

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Set INK_REAL_EXECUTION_VIEW_QA=1 for read-only real-data view QA.');

interface RunFacts {
  readonly actorEmail: string;
  readonly threadId: string;
}

interface DreamFilesPayload {
  readonly stages: Record<string, unknown>;
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
    "run=db.execute(\"select created_by,source_voice_thread_id from workflow_runs where id=%s\",(sys.argv[1],)).fetchone()",
    "actor=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[2],)).fetchone()",
    'db.close()',
    "assert run is not None, 'run not found'",
    "assert actor is not None, 'actor not found'",
    "assert str(actor['id'])==str(run['created_by']), 'run actor mismatch'",
    "print(json.dumps({'threadId':run['source_voice_thread_id'],'actorEmail':actor['email']}))",
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
    if (
      request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)
    ) diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
  });
  return diagnostics;
}

async function readDreamFiles(page: Page, token: string): Promise<DreamFilesPayload> {
  const response = await page.request.get(
    `${WEB_BASE}/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(response.status(), await response.text()).toBe(200);
  return await response.json() as DreamFilesPayload;
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  expect(await page.evaluate(() => (
    document.documentElement.scrollWidth - document.documentElement.clientWidth
  ))).toBeLessThanOrEqual(1);
}

test('real Execution defaults to Draft and exposes Sync beside Chat without mutating facts', async ({
  browser,
}) => {
  test.setTimeout(90_000);
  expect(IMPACT_SCOPE).toEqual({
    canonicalWorkspace: 'must-remain-unchanged',
    publishedStages: 'must-remain-unchanged',
    threadAndSession: 'out-of-scope-and-untouched',
    executionView: 'browser-local-presentation-only',
  });
  const run = resolveRunFacts();
  expect(run.actorEmail).toBe(ACTOR_EMAIL);
  const token = createActorToken(ACTOR_EMAIL);
  const beforeHashes = canonicalHashes(run.threadId);

  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const diagnostics = diagnosticsFor(page);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    const beforeStages = JSON.stringify((await readDreamFiles(page, token)).stages);
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const draft = page.getByRole('region', { name: 'Dream 初稿工作台' });
    const sync = page.getByRole('region', { name: 'Episode 产物工作台' });
    const openAgent = page.getByRole('button', { name: '打开 Dream Agent 消息预览' });
    await expect(draft).toBeVisible();
    await expect(sync).toHaveCount(0);
    await expect(page.getByText('Dream 初稿阶段投影', { exact: true })).toHaveCount(0);

    await openAgent.click();
    let dialog = page.getByRole('dialog', { name: 'Dream Agent' });
    const viewSwitch = dialog.getByRole('group', { name: '工作台视图' });
    await expect(viewSwitch.getByRole('button', { name: '初稿', exact: true }))
      .toHaveAttribute('aria-pressed', 'true');
    await expect(dialog.getByRole('button', { name: '在 Chat 中打开当前 thread' })).toBeVisible();
    await viewSwitch.getByRole('button', { name: '同步', exact: true }).click();
    await expect(viewSwitch.getByRole('button', { name: '同步', exact: true }))
      .toHaveAttribute('aria-pressed', 'true');
    await dialog.getByRole('button', { name: '收起 Dream Agent' }).click();
    await expect(dialog).toBeHidden();
    await expect(draft).toHaveCount(0);
    await expect(sync).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: 'output/playwright/story-workspace-real-execution-sync-wide.png',
      fullPage: true,
    });

    await page.reload();
    await expect(draft).toBeVisible();
    await expect(sync).toHaveCount(0);

    await page.setViewportSize({ width: 390, height: 844 });
    await openAgent.click();
    dialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await dialog.getByRole('button', { name: '同步', exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(sync).toBeVisible();
    await expect(draft).toHaveCount(0);
    await expectNoHorizontalOverflow(page);

    await openAgent.click();
    dialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await dialog.getByRole('button', { name: '初稿', exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(draft).toBeVisible();
    await expect(sync).toHaveCount(0);
    await page.screenshot({
      path: 'output/playwright/story-workspace-real-execution-draft-narrow.png',
      fullPage: true,
    });

    expect(JSON.stringify((await readDreamFiles(page, token)).stages)).toBe(beforeStages);
    expect(canonicalHashes(run.threadId)).toEqual(beforeHashes);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});
