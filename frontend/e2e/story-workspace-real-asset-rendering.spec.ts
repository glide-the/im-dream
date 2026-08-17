// [Input] Existing local Dream Run owned by dmeck123@suoxya.com and its published asset stages.
// [Output] Read-only wide/narrow proof for structured asset metadata and real storyboard note IDs.
// [Pos] Opt-in real-data visual acceptance for Story Workspace Execution focus rendering.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_ASSET_RENDERING_QA === '1';
const WEB_BASE = process.env.INK_REAL_ASSET_RENDERING_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = process.env.INK_REAL_ASSET_RENDERING_RUN_ID
  ?? 'run_ddb53a9a261d497c98ad9a6c1ec3a1c2';
const ACTOR_EMAIL = process.env.INK_REAL_ASSET_RENDERING_ACTOR_EMAIL
  ?? 'dmeck123@suoxya.com';
const CHARACTER_NAME = process.env.INK_REAL_ASSET_RENDERING_CHARACTER ?? '老板娘';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Dream impact contract:
 *
 * | Surface | Authority | Expected result |
 * | Canonical character/scene/storyboard files | thread workspace | byte-identical |
 * | Run-private stage revision/content | after-turn Hook publication | unchanged |
 * | Asset focus | current stage content | frontmatter metadata and Markdown prose are separate |
 * | Storyboard note | selected Episode shot projection | exact shot ID + visual, never a fixed ordinal or stage summary |
 * | Thread/session/model | shared Chat thread | untouched; this test sends no message |
 */
const IMPACT_SCOPE = Object.freeze({
  canonicalWorkspace: 'must-remain-unchanged',
  stageProjection: 'must-remain-unchanged',
  threadAndSession: 'out-of-scope-and-untouched',
  executionRendering: 'changes-only-in-browser-presentation',
});

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1440, height: 900 },
});
test.skip(!ENABLED, 'Set INK_REAL_ASSET_RENDERING_QA=1 for read-only real-data rendering QA.');

interface RunFacts {
  readonly threadId: string;
  readonly actorEmail: string;
}

interface StageItem {
  readonly entityId: string;
  readonly displayName: string;
  readonly content?: string | null;
}

interface DreamFilesPayload {
  readonly stages: {
    readonly characters?: { readonly revision: number; readonly items: readonly StageItem[] };
    readonly scenes?: { readonly revision: number; readonly items: readonly StageItem[] };
    readonly storyboards?: { readonly revision: number; readonly items: readonly StageItem[] };
  };
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
    ) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
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

function stageSnapshot(payload: DreamFilesPayload): string {
  return JSON.stringify(payload.stages);
}

async function assertNoHorizontalOverflow(page: Page): Promise<void> {
  expect(await page.evaluate(() => (
    document.documentElement.scrollWidth - document.documentElement.clientWidth
  ))).toBeLessThanOrEqual(1);
}

test('real Execution renders complete asset metadata and storyboard notes within the viewport', async ({ browser }) => {
  test.setTimeout(90_000);
  expect(IMPACT_SCOPE).toEqual({
    canonicalWorkspace: 'must-remain-unchanged',
    stageProjection: 'must-remain-unchanged',
    threadAndSession: 'out-of-scope-and-untouched',
    executionRendering: 'changes-only-in-browser-presentation',
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
    const beforeFiles = await readDreamFiles(page, token);
    const character = beforeFiles.stages.characters?.items.find(
      (item) => item.displayName === CHARACTER_NAME,
    );
    const storyboard = beforeFiles.stages.storyboards?.items[0];
    expect(character?.content).toContain('appearance:');
    expect(storyboard).toBeTruthy();

    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await page.evaluate(async () => {
      const theme = await import('/src/utils/theme.ts');
      theme.setThemeMode('dark');
    });

    const projection = page.getByRole('region', { name: 'Dream 初稿工作台' });
    await expect(projection).toBeVisible();
    await expect(page.getByRole('region', { name: 'Episode 产物工作台' })).toHaveCount(0);
    await projection.getByRole('tab', { name: /^Assets/ }).click();
    await projection.getByRole('button').filter({ hasText: CHARACTER_NAME }).click();

    const assetDocument = projection.locator('.story-workspace-collaboration__asset-document');
    await expect(assetDocument.locator('dt').filter({ hasText: /^appearance \/ height$/ })).toBeVisible();
    await expect(assetDocument.getByText('158cm', { exact: true })).toBeVisible();
    await expect(assetDocument.locator('dt').filter({ hasText: /^appearance \/ build$/ })).toBeVisible();
    await expect(assetDocument.getByText('微胖', { exact: true })).toBeVisible();
    await expect(assetDocument.getByText('围裙 + 棉衣', { exact: true })).toBeVisible();
    await expect(assetDocument.getByRole('heading', { name: CHARACTER_NAME, level: 1 })).toBeVisible();
    const largestAssetFont = await assetDocument.locator('*').evaluateAll((elements) => Math.max(
      ...elements.map((element) => Number.parseFloat(getComputedStyle(element).fontSize)),
    ));
    expect(largestAssetFont).toBeLessThanOrEqual(34);
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: 'output/playwright/story-workspace-asset-rendering-dark-wide.png',
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(assetDocument.getByText('围裙 + 棉衣', { exact: true })).toBeVisible();
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: 'output/playwright/story-workspace-asset-rendering-dark-narrow.png',
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await projection.getByRole('button', { name: '← 返回故事线' }).click();
    await projection.getByRole('tab', { name: /^Outline/ }).click();
    await projection.getByRole('button').filter({ hasText: storyboard?.displayName ?? '' }).click();
    const shotNote = projection.locator('.story-workspace-collaboration__shot-note');
    const firstShotId = (await shotNote.locator('code').textContent())?.trim() ?? '';
    expect(firstShotId).toMatch(/^shot-\d+$/);
    await expect(projection.getByText(/^共 \d+ 个镜头 · \d+(?:\.\d+)? 秒$/)).toBeVisible();

    await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
    let agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await agentDialog.getByRole('button', { name: '同步', exact: true }).click();
    await expect(agentDialog.getByRole('button', { name: '同步', exact: true }))
      .toHaveAttribute('aria-pressed', 'true');
    await agentDialog.getByRole('button', { name: '收起 Dream Agent' }).click();
    const sync = page.getByRole('region', { name: 'Episode 产物工作台' });
    await expect(sync).toBeVisible();
    await expect(projection).toHaveCount(0);
    const secondShot = sync.getByRole('button', { name: 'shot-002', exact: true });
    await expect(secondShot).toBeVisible();
    await secondShot.click();

    await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
    agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await agentDialog.getByRole('button', { name: '初稿', exact: true }).click();
    await agentDialog.getByRole('button', { name: '收起 Dream Agent' }).click();
    await expect(projection).toBeVisible();
    await expect(shotNote.locator('code')).toHaveText('shot-002');
    await expect(shotNote.locator('p')).not.toHaveText(/total_shots|shot_id|duration_sec/);
    expect(await shotNote.locator('p').evaluate((element) => (
      Number.parseFloat(getComputedStyle(element).fontSize)
    ))).toBeLessThanOrEqual(13);
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: 'output/playwright/story-workspace-shot-note-dark-wide.png',
      fullPage: true,
    });

    const afterFiles = await readDreamFiles(page, token);
    expect(stageSnapshot(afterFiles)).toBe(stageSnapshot(beforeFiles));
    expect(canonicalHashes(run.threadId)).toEqual(beforeHashes);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});
