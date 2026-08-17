// [Input] Existing local Dream Runs for the named real actor; no model turn or data mutation.
// [Output] Read-only proof that Project titles and creation-goal fallbacks agree across API and Dream UI.
// [Pos] Opt-in real-data Dream display-title acceptance test.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_TITLE_QA === '1';
const WEB_BASE = process.env.INK_REAL_DREAM_TITLE_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_DREAM_TITLE_ACTOR_EMAIL ?? 'dmeck123@suoxya.com';
const PROJECT_RUN_ID = process.env.INK_REAL_DREAM_TITLE_PROJECT_RUN_ID
  ?? 'run_ddb53a9a261d497c98ad9a6c1ec3a1c2';
const PROJECT_TITLE = process.env.INK_REAL_DREAM_TITLE_PROJECT_TITLE ?? '雾中黑海湖';
const FALLBACK_RUN_ID = process.env.INK_REAL_DREAM_TITLE_FALLBACK_RUN_ID
  ?? 'run_1d6380cea6fc4a91b0586c1e79856ec4';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Business impact contract:
 *
 * | Fact | Authority | Expected impact |
 * | Project title | canonical project.yaml -> Story.title | unchanged; API, re-entry and Execution all show PROJECT_TITLE |
 * | Run without Project | immutable launch Source Message goal | unchanged; re-entry shows the first 80 characters only as fallback |
 * | Episode title/content | Episode artifacts | must remain unchanged and is not used as a Project title |
 * | Thread/session/model | ClaudeAgentService | out of scope; this spec sends no message and invokes no model |
 */

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1200, height: 720 },
});
test.skip(!ENABLED, 'Set INK_REAL_DREAM_TITLE_QA=1 for read-only real-data title QA.');

function runBackendScript(source: string, args: readonly string[]): string {
  return execFileSync(BACKEND_PYTHON, ['-c', source, ...args], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

function createActorToken(email: string): string {
  return runBackendScript([
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

function readProjectTitle(runId: string): string | null {
  const output = runBackendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database,json,sys',
    'db=database.get_db()',
    "row=db.execute(\"select title from story_workspace_stories where artifact_source_type='dream_episode' and source_run_id=%s order by updated_at desc,id asc limit 1\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "print(json.dumps(row['title'] if row else None,ensure_ascii=False))",
  ].join(';'), [runId]);
  return JSON.parse(output) as string | null;
}

test('real Dream lists and Execution share one canonical-first display title', async ({ browser }) => {
  test.setTimeout(60_000);
  expect(readProjectTitle(PROJECT_RUN_ID)).toBe(PROJECT_TITLE);
  expect(readProjectTitle(FALLBACK_RUN_ID)).toBeNull();

  const token = createActorToken(ACTOR_EMAIL);
  const context = await browser.newContext({ viewport: { width: 1200, height: 720 } });
  const page = await context.newPage();
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
    ) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    const response = await page.request.get(`${WEB_BASE}/api/story-workspace/dream-runs`, {
      headers: { authorization: `Bearer ${token}` },
    });
    expect(response.status(), await response.text()).toBe(200);
    const payload = await response.json() as {
      runs: Array<{
        storyWorkspaceRunId: string;
        displayTitle: string;
        goalPrefix: string;
      }>;
    };
    const projectRun = payload.runs.find((run) => run.storyWorkspaceRunId === PROJECT_RUN_ID);
    const fallbackRun = payload.runs.find((run) => run.storyWorkspaceRunId === FALLBACK_RUN_ID);
    expect(projectRun?.displayTitle).toBe(PROJECT_TITLE);
    expect(projectRun?.displayTitle).not.toBe(projectRun?.goalPrefix);
    expect(fallbackRun?.displayTitle).toBe(fallbackRun?.goalPrefix);
    expect(fallbackRun?.displayTitle.length).toBeLessThanOrEqual(80);

    await page.goto(`${WEB_BASE}/story-workspace/dream`);
    await expect(page.getByRole('heading', { name: '发起一次 Dream' })).toBeVisible();
    const search = page.getByRole('searchbox', { name: '搜索 Dream' });
    await search.fill(PROJECT_TITLE);
    const projectButton = page.getByRole('button', { name: new RegExp(PROJECT_TITLE) });
    await expect(projectButton).toBeVisible();
    await projectButton.click();
    await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/runs/${PROJECT_RUN_ID}/execution`);
    await expect(page.getByRole('heading', { level: 1, name: PROJECT_TITLE })).toBeVisible();

    await page.goto(`${WEB_BASE}/story-workspace/dream`);
    await expect(page.getByRole('heading', { name: '发起一次 Dream' })).toBeVisible();
    await page.getByRole('searchbox', { name: '搜索 Dream' }).fill(FALLBACK_RUN_ID);
    await expect(page.getByRole('button', { name: new RegExp(fallbackRun!.displayTitle) }))
      .toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1))
      .toBe(true);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});
