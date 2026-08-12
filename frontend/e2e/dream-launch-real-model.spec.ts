// [Input] A private logical clone, the production Dream launch endpoint, and the exact real Gateway model.
// [Output] Headed-browser proof that Dream launch, files, thread history, and Dream↔Chat recovery share one runtime.
// [Pos] Release harness only; it calls public production routes and never installs a test-only business branch.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_LAUNCH_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const API_BASE = process.env.INK_REAL_DREAM_API_BASE ?? 'http://127.0.0.1:8765';
const TEST_EMAIL = process.env.INK_REAL_DREAM_LAUNCH_EMAIL ?? '';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Run only through the private real-model Dream launch harness.');

type ThreadStatus = {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
};

type DreamFiles = {
  storyWorkspaceRunId: string;
  threadId: string;
  runRevision: number;
  canConfirm: boolean;
  stages: Record<string, { revision: number; items: unknown[] }>;
};

function createToken(): string {
  if (!TEST_EMAIL) throw new Error('INK_REAL_DREAM_LAUNCH_EMAIL is required.');
  const source = [
    'import auth,database,sys',
    'db=database.get_db()',
    'user=db.execute("SELECT id,email FROM users WHERE email=%s AND status=\'active\'",(sys.argv[1],)).fetchone()',
    'db.close()',
    'assert user is not None',
    'print(auth.create_access_token(user["id"],user["email"]))',
  ].join(';');
  return execFileSync(PYTHON, ['-c', source, TEST_EMAIL], {
    cwd: BACKEND_ROOT,
    encoding: 'utf8',
  }).trim();
}

async function getJson<T>(request: APIRequestContext, path: string, token: string): Promise<T> {
  const response = await request.get(`${API_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(200);
  return await response.json() as T;
}

function installDiagnostics(page: Page): {
  readonly errors: string[];
  readonly dreamFileStatuses: number[];
  settle: () => Promise<void>;
} {
  const errors: string[] = [];
  const dreamFileStatuses: number[] = [];
  const pending: Promise<void>[] = [];
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    if (message.text().includes('WebSocket connection to') && message.text().includes('/?token=')) return;
    errors.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    errors.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('response', (response) => {
    if (/\/api\/story-workspace\/workflow-runs\/run_[0-9a-f]{32}\/dream-files$/.test(response.url())) {
      dreamFileStatuses.push(response.status());
    }
    if (response.status() < 400 || !response.url().includes('/api/')) return;
    pending.push(response.text().then((body) => {
      errors.push(`http ${response.status()}: ${response.url()} body=${body.slice(0, 300)}`);
    }).catch(() => {
      errors.push(`http ${response.status()}: ${response.url()} body=<unavailable>`);
    }));
  });
  return {
    errors,
    dreamFileStatuses,
    settle: async () => { await Promise.allSettled(pending); },
  };
}

test('real Dream launch reaches editable files and reopens one thread in Chat', async ({ page }) => {
  test.setTimeout(480_000);
  const diagnostics = installDiagnostics(page);
  const token = createToken();
  await page.addInitScript((accessToken) => {
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);
  await page.setViewportSize({ width: 1440, height: 1000 });

  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('heading', { name: '发起一次 Dream' })).toBeVisible();
  await page.getByRole('textbox', { name: '创作目标' }).fill(
    '创作一个雨夜末班车短篇：两位旧友在终点站重逢，人物关系克制，结尾保留悬念。请完成人物、场景和分镜草稿。',
  );

  const launchResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith('/api/story-workspace/dream-runs/start')
    && response.request().method() === 'POST'
  ), { timeout: 30_000 });
  await expect(page.getByRole('button', { name: '发起 Dream' })).toBeEnabled();
  await page.getByRole('button', { name: '发起 Dream' }).click();
  const launchResponse = await launchResponsePromise;
  expect(launchResponse.status(), await launchResponse.text()).toBe(201);
  const accepted = await launchResponse.json() as { workflowRunId: string; threadId: string };
  expect(accepted.workflowRunId).toMatch(/^run_[0-9a-f]{32}$/);
  expect(accepted.threadId).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
  await page.waitForURL(new RegExp(`/story-workspace/dream\\?run=${accepted.workflowRunId}$`));

  const immediateFiles = await getJson<DreamFiles>(
    page.request,
    `/api/story-workspace/workflow-runs/${accepted.workflowRunId}/dream-files`,
    token,
  );
  expect(immediateFiles.threadId).toBe(accepted.threadId);

  let settledFiles: DreamFiles | null = null;
  let consecutiveReadFailures = 0;
  await expect.poll(async () => {
    try {
      const run = await getJson<{
        status: string;
        errorCode?: string | null;
        error_code?: string | null;
        failedStep?: string | null;
        failed_step?: string | null;
      }>(
        page.request,
        `/api/story-workspace/workflow-runs/${accepted.workflowRunId}`,
        token,
      );
      if (['failed', 'cancelled'].includes(run.status)) {
        throw new Error(
          `Dream run reached ${run.status}: ${run.errorCode ?? run.error_code ?? 'UNKNOWN'}`
          + `:${run.failedStep ?? run.failed_step ?? 'UNKNOWN_STEP'}`,
        );
      }
      settledFiles = await getJson<DreamFiles>(
        page.request,
        `/api/story-workspace/workflow-runs/${accepted.workflowRunId}/dream-files`,
        token,
      );
      consecutiveReadFailures = 0;
      const stages = ['characters', 'scenes', 'storyboards'].map((stage) => settledFiles!.stages[stage]);
      return settledFiles.canConfirm
        && settledFiles.runRevision > 0
        && stages.every((stage) => stage?.revision > 0 && stage.items.length > 0);
    } catch (error) {
      if (error instanceof Error && error.message.startsWith('Dream run reached ')) throw error;
      consecutiveReadFailures += 1;
      if (consecutiveReadFailures >= 5) throw error;
      return false;
    }
  }, {
    timeout: 360_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(true);

  expect(settledFiles!.storyWorkspaceRunId).toBe(accepted.workflowRunId);
  expect(settledFiles!.threadId).toBe(accepted.threadId);
  await expect(page.getByRole('button', { name: '确认并继续' })).toBeEnabled();

  await expect.poll(async () => {
    const status = await getJson<ThreadStatus>(
      page.request,
      `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/status`,
      token,
    );
    return status.running === false && status.lifecycle === 'idle' && status.turn_count >= 1;
  }, { timeout: 60_000, intervals: [250, 500, 1_000] }).toBe(true);
  const dreamHistory = await getJson<{ messages: unknown[] }>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/messages`,
    token,
  );
  expect(dreamHistory.messages.length).toBeGreaterThan(0);

  await page.reload();
  await expect(page.getByRole('button', { name: '确认并继续' })).toBeEnabled();
  await page.getByRole('button', { name: '对话', exact: true }).click();
  await page.waitForURL(`${WEB_BASE}/story-workspace/chat`);
  await expect(page.getByPlaceholder('Ask Ink & Memory…')).toBeVisible();
  const chatHistory = await getJson<{ messages: unknown[] }>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/messages`,
    token,
  );
  expect(chatHistory.messages).toHaveLength(dreamHistory.messages.length);

  await page.goBack();
  await page.waitForURL(new RegExp(`/story-workspace/dream\\?run=${accepted.workflowRunId}$`));
  await expect(page.getByRole('button', { name: '确认并继续' })).toBeEnabled();

  await diagnostics.settle();
  expect(diagnostics.dreamFileStatuses.length).toBeGreaterThan(0);
  expect(diagnostics.dreamFileStatuses.every((status) => status === 200)).toBe(true);
  expect(diagnostics.errors).toEqual([]);
});
