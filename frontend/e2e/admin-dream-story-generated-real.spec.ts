// [Input] One owned Dream business PostgreSQL clone, its generated Story/Artifact files, and the owned Admin UI.
// [Output] Browser proof that Admin reads the same Dream Story and applies revision-guarded review without exposing paths.

import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_ADMIN_DREAM_STORY_QA === '1';
const ADMIN_BASE = process.env.INK_REAL_ADMIN_BASE_URL ?? '';
const STORY_ID = process.env.INK_REAL_ADMIN_STORY_ID ?? '';
const PROJECT_ID = process.env.INK_REAL_ADMIN_PROJECT_ID ?? '';
const RUN_ID = process.env.INK_REAL_ADMIN_RUN_ID ?? '';
const SCRIPT_REVISION = process.env.INK_REAL_ADMIN_SCRIPT_REVISION ?? '';
const ADMIN_EMAIL = process.env.INK_REAL_ADMIN_EMAIL ?? '';
const ADMIN_PASSWORD = process.env.INK_REAL_ADMIN_PASSWORD ?? '';

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(
  !ENABLED
    || !ADMIN_BASE
    || !STORY_ID
    || !PROJECT_ID
    || !RUN_ID
    || !SCRIPT_REVISION
    || !ADMIN_EMAIL
    || !ADMIN_PASSWORD,
  'Run only through the owned Dream business PostgreSQL E2E runner.',
);

function collectDiagnostics(page: Page): {
  items: string[];
  markAuthenticated: () => void;
} {
  const diagnostics: string[] = [];
  let authenticated = false;
  page.on('console', (message) => {
    if (authenticated && message.type() === 'error') {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    }
  });
  page.on('response', (response) => {
    if (authenticated && response.status() >= 500 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  return {
    items: diagnostics,
    markAuthenticated: () => { authenticated = true; },
  };
}

async function expectNoDocumentOverflow(page: Page): Promise<void> {
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )).toBeLessThanOrEqual(1);
}

test('Admin reads and revision-confirms the Story produced by the same Dream Run', async ({ page }) => {
  test.setTimeout(120_000);
  const diagnosticState = collectDiagnostics(page);
  await page.route('http://unpkg.com/react-grab/dist/index.global.js', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/javascript', body: '' });
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${ADMIN_BASE}/admin/login`);
  await page.getByLabel('管理员邮箱').fill(ADMIN_EMAIL);
  await page.getByLabel('密码').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: '登录控制台' }).click();
  await expect(page).toHaveURL(/\/admin$/);
  diagnosticState.markAuthenticated();

  const list = await page.request.get(
    `${ADMIN_BASE}/api/admin/story-stories?filter[source_project_id][eq]=${encodeURIComponent(PROJECT_ID)}`,
  );
  expect(list.status(), await list.text()).toBe(200);
  const listBody = await list.json() as {
    data: Array<Record<string, unknown>>;
    meta: { total: number };
  };
  expect(listBody.meta.total).toBe(1);
  expect(listBody.data[0]).toMatchObject({
    id: STORY_ID,
    source_run_id: RUN_ID,
    source_project_id: PROJECT_ID,
    artifact_status: 'available',
    artifact_sync_status: 'indexed',
    script_revision: SCRIPT_REVISION,
  });
  expect(listBody.data[0]).not.toHaveProperty('source_thread_ref');
  expect(listBody.data[0]).not.toHaveProperty('content');

  const surface = await page.request.get(
    `${ADMIN_BASE}/api/admin/story-stories/${STORY_ID}/artifact-surface`,
  );
  expect(surface.status(), await surface.text()).toBe(200);
  const surfaceBody = await surface.json() as { data: Record<string, unknown> };
  expect(surfaceBody.data).toMatchObject({
    storyId: STORY_ID,
    projectId: PROJECT_ID,
    sourceRunId: RUN_ID,
  });
  expect(JSON.stringify(surfaceBody)).not.toMatch(/\/Users\/|postgres(?:ql)?:\/\/|Bearer\s|api[_-]?key/i);

  const preview = await page.request.get(
    `${ADMIN_BASE}/api/admin/story-stories/${STORY_ID}/artifacts`
      + `?episodeId=EP01&kind=script&offset=0&limit=65536&revision=${encodeURIComponent(SCRIPT_REVISION)}`,
  );
  expect(preview.status(), await preview.text()).toBe(200);
  const previewBody = await preview.json() as { data: Record<string, unknown> };
  expect(previewBody.data).toMatchObject({
    storyId: STORY_ID,
    projectId: PROJECT_ID,
    episodeId: 'EP01',
    kind: 'script',
    revision: SCRIPT_REVISION,
  });
  expect(String(previewBody.data.content ?? '').length).toBeGreaterThan(0);
  expect(JSON.stringify(previewBody)).not.toMatch(/\/Users\/|postgres(?:ql)?:\/\/|Bearer\s|api[_-]?key/i);

  const origin = new URL(ADMIN_BASE).origin;
  const stale = await page.request.post(
    `${ADMIN_BASE}/api/admin/story-stories/${STORY_ID}/confirm`,
    {
      headers: { origin, 'content-type': 'application/json' },
      data: { expectedScriptRevision: `sha256:${'0'.repeat(64)}` },
    },
  );
  expect(stale.status()).toBe(409);

  const requestId = `dream-business-confirm-${STORY_ID}`;
  const confirmationOptions = {
    headers: {
      origin,
      'content-type': 'application/json',
      'x-request-id': requestId,
    },
    data: { expectedScriptRevision: SCRIPT_REVISION },
  };
  const confirm = await page.request.post(
    `${ADMIN_BASE}/api/admin/story-stories/${STORY_ID}/confirm`,
    confirmationOptions,
  );
  expect(confirm.status(), await confirm.text()).toBe(200);
  expect(confirm.headers()['idempotency-replayed']).toBeUndefined();
  const replay = await page.request.post(
    `${ADMIN_BASE}/api/admin/story-stories/${STORY_ID}/confirm`,
    confirmationOptions,
  );
  expect(replay.status(), await replay.text()).toBe(200);
  expect(replay.headers()['idempotency-replayed']).toBe('true');

  await page.goto(`${ADMIN_BASE}/admin/story/stories?source_project_id=${encodeURIComponent(PROJECT_ID)}`);
  const row = page.locator('tbody tr').filter({ hasText: PROJECT_ID });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: '查看' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByTestId('story-index-rail')).toContainText('indexed');
  await expect(dialog.getByTestId('story-artifact-preview')).not.toBeEmpty();
  await expectNoDocumentOverflow(page);
  await dialog.getByRole('button', { name: '关闭' }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  const mobileRow = page.locator('tbody tr').filter({ hasText: PROJECT_ID });
  await mobileRow.getByRole('button', { name: '查看' }).click();
  await expect(page.getByRole('dialog').getByTestId('story-artifact-preview')).not.toBeEmpty();
  await expectNoDocumentOverflow(page);
  expect(diagnosticState.items).toEqual([]);
});
