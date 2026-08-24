// [Input] The normal or explicitly technical-isolation Dream launch endpoint and an exact real Gateway model.
// [Output] Headed-browser business proof plus a private content-free lifecycle receipt for failure diagnosis.
// [Pos] Release harness only; it calls public production routes and never installs a test-only business branch.
// [Sync] 2026-08-24: let the Story Index semantic status settle before choosing
//                    an enabled visible recovery action.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { writeFile } from 'node:fs/promises';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_LAUNCH_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const API_BASE = process.env.INK_REAL_DREAM_API_BASE ?? 'http://127.0.0.1:8765';
const TEST_EMAIL = process.env.INK_REAL_DREAM_LAUNCH_EMAIL ?? '';
const TEST_DECK_ID = process.env.INK_REAL_DREAM_LAUNCH_DECK_ID ?? '';
const RUN_RECEIPT_PATH = process.env.INK_REAL_DREAM_LAUNCH_RECEIPT_PATH ?? '';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');

test.use({
  channel: 'chromium',
  launchOptions: {
    args: ['--window-position=20,20', '--window-size=1280,800'],
  },
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1200, height: 720 },
});
test.skip(!ENABLED, 'Run only through an explicitly authorized real-model Dream launch harness.');

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

type EpisodeArtifacts = {
  bindingAvailability: 'bound' | 'unbound';
  artifacts: Array<{
    relativeKey: string;
    availability: 'available' | 'not_generated' | 'invalid' | 'unavailable';
  }>;
};

function createToken(): string {
  if (!TEST_EMAIL) throw new Error('INK_REAL_DREAM_LAUNCH_EMAIL is required.');
  if (!RUN_RECEIPT_PATH) throw new Error('INK_REAL_DREAM_LAUNCH_RECEIPT_PATH is required.');
  const source = [
    'from pathlib import Path',
    'from dotenv import load_dotenv',
    'load_dotenv(Path.cwd() / ".env", override=False)',
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

async function writeRunReceipt(receipt: {
  workflowRunId: string;
  threadId: string;
  runStatus: string;
  runErrorCode: string | null;
  runRevision: number;
  canConfirm: boolean;
  approvedWriteConfirmations: number;
  approvedAgentConfirmations: number;
  stages: Record<string, { revision: number; itemCount: number }>;
}): Promise<void> {
  await writeFile(
    RUN_RECEIPT_PATH,
    `${JSON.stringify(receipt)}\n`,
    { encoding: 'utf8', mode: 0o600 },
  );
}

type ExpectedConfirmationTool = 'Write' | 'Agent';

async function approveExpectedToolConfirmation(
  page: Page,
): Promise<ExpectedConfirmationTool | null> {
  const dialogs = page.locator('[role="alertdialog"]:visible');
  const count = await dialogs.count();
  if (count === 0) return null;
  if (count !== 1) {
    throw new Error('Multiple tool confirmations are visible in the Dream business journey.');
  }
  const dialog = dialogs.first();
  const accessibleName = await dialog.getAttribute('aria-label');
  const tool = (['Write', 'Agent'] as const).find((candidate) => (
    accessibleName?.startsWith(`是否允许 I&M 调用 ${candidate} 工具`)
    || accessibleName?.startsWith(`Allow I&M to call the ${candidate} tool`)
  ));
  if (!tool) {
    throw new Error('An unreviewed tool confirmation blocked the Dream business journey.');
  }
  await dialog.scrollIntoViewIfNeeded();
  await expect(dialog).toBeInViewport();
  const approveButton = dialog.getByRole('button', { name: /^(同意|Approve)/ });
  await expect(approveButton).toBeInViewport();
  await approveButton.click();
  await expect(dialog).toBeHidden({ timeout: 15_000 });
  return tool;
}

async function expectPageFitsViewport(page: Page): Promise<void> {
  await expect.poll(async () => page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    return Math.max(root.scrollWidth, body.scrollWidth) - root.clientWidth;
  }), {
    message: 'The Dream business page must not overflow the visible window horizontally.',
  }).toBeLessThanOrEqual(1);
}

async function showDreamContent(page: Page): Promise<void> {
  const backToContent = page.getByRole('button', { name: '← 返回 Dream 内容' });
  if (await backToContent.isVisible()) {
    await expect(backToContent).toBeInViewport();
    await backToContent.click();
    await expect(backToContent).toBeHidden();
  }
}

async function getJson<T>(request: APIRequestContext, path: string, token: string): Promise<T> {
  const response = await request.get(`${API_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(200);
  return await response.json() as T;
}

function isTransientApiReadFailure(error: unknown): boolean {
  return error instanceof Error
    && /(?:ECONNRESET|ECONNREFUSED|ETIMEDOUT|EPIPE|socket hang up)/.test(error.message);
}

function installDiagnostics(page: Page): {
  readonly errors: string[];
  readonly dreamFileStatuses: number[];
  readonly storyIndexStatuses: number[];
  readonly genericNotFoundConsoleErrors: string[];
  settle: () => Promise<void>;
} {
  const errors: string[] = [];
  const dreamFileStatuses: number[] = [];
  const storyIndexStatuses: number[] = [];
  const genericNotFoundConsoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    if (message.text().includes('WebSocket connection to') && message.text().includes('/?token=')) return;
    if (/^Failed to load resource: the server responded with a status of 404/.test(message.text())) {
      genericNotFoundConsoleErrors.push(message.text());
      return;
    }
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
    if (/\/api\/story-workspace\/workflow-runs\/run_[0-9a-f]{32}\/story-index$/.test(response.url())) {
      storyIndexStatuses.push(response.status());
      if (response.status() === 404) return;
    }
    if (response.status() < 400 || !response.url().includes('/api/')) return;
    errors.push(`http ${response.status()}: ${response.url()}`);
  });
  return {
    errors,
    dreamFileStatuses,
    storyIndexStatuses,
    genericNotFoundConsoleErrors,
    settle: async () => {},
  };
}

test('real Dream launch reaches editable files and reopens one thread in Chat', async ({ page }) => {
  test.setTimeout(900_000);
  const diagnostics = installDiagnostics(page);
  const token = createToken();
  await page.addInitScript((accessToken) => {
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);

  const deckQuery = TEST_DECK_ID
    ? `?deck=${encodeURIComponent(TEST_DECK_ID)}`
    : '';
  await page.goto(`${WEB_BASE}/story-workspace/dream${deckQuery}`);
  await expectPageFitsViewport(page);
  await expect(page.getByRole('heading', { name: '发起一次 Dream' })).toBeInViewport();
  await expect(page.getByText('当前 Agent', { exact: true })).toBeVisible();
  await expect(
    page.locator('.story-workspace-dream-launch__selection strong'),
  ).toContainText('·');
  const humanProjectName = `雨夜末班车·${new Date().toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour12: false,
  }).replace(/[/:\s]/g, '-')}`;
  await page.getByRole('textbox', { name: '创作目标' }).fill(
    `创作短篇《${humanProjectName}》：两位旧友在终点站重逢，人物关系克制，结尾保留悬念。请完成人物、场景和分镜草稿。`,
  );

  const launchResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith('/api/story-workspace/dream-runs/start')
    && response.request().method() === 'POST'
  ), { timeout: 30_000 });
  const launchButton = page.getByRole('button', { name: '发起 Dream' });
  await expect(launchButton).toBeEnabled();
  await expect(launchButton).toBeInViewport();
  await launchButton.click();
  const launchResponse = await launchResponsePromise;
  expect(launchResponse.status(), await launchResponse.text()).toBe(201);
  const accepted = await launchResponse.json() as { workflowRunId: string; threadId: string };
  expect(accepted.workflowRunId).toMatch(/^run_[0-9a-f]{32}$/);
  expect(accepted.threadId).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
  await writeRunReceipt({
    ...accepted,
    runStatus: 'accepted',
    runErrorCode: null,
    runRevision: 0,
    canConfirm: false,
    approvedWriteConfirmations: 0,
    approvedAgentConfirmations: 0,
    stages: {},
  });
  await page.waitForURL(new RegExp(`/story-workspace/dream\\?run=${accepted.workflowRunId}$`));
  await expectPageFitsViewport(page);

  const immediateFiles = await getJson<DreamFiles>(
    page.request,
    `/api/story-workspace/workflow-runs/${accepted.workflowRunId}/dream-files`,
    token,
  );
  expect(immediateFiles.threadId).toBe(accepted.threadId);

  let settledFiles: DreamFiles | null = null;
  let consecutiveReadFailures = 0;
  let approvedWriteConfirmations = 0;
  let approvedAgentConfirmations = 0;
  await expect.poll(async () => {
    try {
      const approvedTool = await approveExpectedToolConfirmation(page);
      if (approvedTool) {
        if (approvedTool === 'Write') approvedWriteConfirmations += 1;
        if (approvedTool === 'Agent') approvedAgentConfirmations += 1;
        return false;
      }
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
      const threadStatus = await getJson<ThreadStatus>(
        page.request,
        `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/status`,
        token,
      );
      consecutiveReadFailures = 0;
      await writeRunReceipt({
        ...accepted,
        runStatus: run.status,
        runErrorCode: run.errorCode ?? run.error_code ?? null,
        runRevision: settledFiles.runRevision,
        canConfirm: settledFiles.canConfirm,
        approvedWriteConfirmations,
        approvedAgentConfirmations,
        stages: Object.fromEntries(Object.entries(settledFiles.stages).map(
          ([stage, value]) => [stage, {
            revision: value.revision,
            itemCount: value.items.length,
          }],
        )),
      });
      const stages = ['characters', 'scenes', 'storyboards'].map((stage) => settledFiles!.stages[stage]);
      const outputComplete = settledFiles.canConfirm
        && settledFiles.runRevision > 0
        && stages.every((stage) => stage?.revision > 0 && stage.items.length > 0);
      if (
        !outputComplete
        && threadStatus.running === false
        && threadStatus.turn_count >= 1
      ) {
        const stageReceipt = Object.fromEntries(
          ['characters', 'scenes', 'storyboards'].map((stage) => [stage, {
            revision: settledFiles!.stages[stage]?.revision ?? 0,
            itemCount: settledFiles!.stages[stage]?.items.length ?? 0,
          }]),
        );
        throw new Error(
          `Dream Agent stopped before required output: runRevision=${settledFiles.runRevision}`
          + ` stages=${JSON.stringify(stageReceipt)}`,
        );
      }
      return outputComplete;
    } catch (error) {
      if (
        error instanceof Error
        && (
          error.message.startsWith('Dream run reached ')
          || error.message.startsWith('Dream Agent stopped ')
        )
      ) throw error;
      consecutiveReadFailures += 1;
      if (consecutiveReadFailures >= 5) throw error;
      return false;
    }
  }, {
    timeout: 720_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(true);

  expect(settledFiles!.storyWorkspaceRunId).toBe(accepted.workflowRunId);
  expect(settledFiles!.threadId).toBe(accepted.threadId);
  await showDreamContent(page);
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
  await page.getByRole('button', { name: /^(对话|Chat)$/ }).click({ noWaitAfter: true });
  await page.waitForURL(`${WEB_BASE}/story-workspace/chat`);
  await expectPageFitsViewport(page);
  await expect(page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ })).toBeVisible();
  const chatHistory = await getJson<{ messages: unknown[] }>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/messages`,
    token,
  );
  expect(chatHistory.messages).toHaveLength(dreamHistory.messages.length);

  await page.evaluate(() => window.history.back());
  await page.waitForURL(new RegExp(`/story-workspace/dream\\?run=${accepted.workflowRunId}$`));
  await expectPageFitsViewport(page);
  await showDreamContent(page);
  await expect(page.getByRole('button', { name: '确认并继续' })).toBeEnabled();

  const confirmationResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith(
      `/api/story-workspace/workflow-runs/${accepted.workflowRunId}/dream-confirmation`,
    ) && response.request().method() === 'POST'
  ), { timeout: 30_000 });
  await page.getByRole('button', { name: '确认并继续' }).click();
  const confirmationResponse = await confirmationResponsePromise;
  expect(confirmationResponse.status(), await confirmationResponse.text()).toBe(202);
  await page.waitForURL(
    `${WEB_BASE}/story-workspace/runs/${accepted.workflowRunId}/execution`,
  );
  await expectPageFitsViewport(page);
  await expect(page.getByText('后续执行', { exact: true })).toBeVisible();

  let episodeArtifacts: EpisodeArtifacts | null = null;
  let consecutiveEpisodeReadFailures = 0;
  await expect.poll(async () => {
    try {
      const approvedTool = await approveExpectedToolConfirmation(page);
      if (approvedTool) return false;
      episodeArtifacts = await getJson<EpisodeArtifacts>(
        page.request,
        `/api/story-workspace/workflow-runs/${accepted.workflowRunId}/episode-artifacts`,
        token,
      );
      const required = new Map(
        episodeArtifacts.artifacts.map((artifact) => [artifact.relativeKey, artifact.availability]),
      );
      const complete = episodeArtifacts.bindingAvailability === 'bound'
        && ['episode-outline.md', 'script.md', 'storyboard.yaml', 'review-report.md']
          .every((key) => required.get(key) === 'available');
      if (!complete) {
        const status = await getJson<ThreadStatus>(
          page.request,
          `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/status`,
          token,
        );
        if (status.running === false && status.turn_count >= 2) {
          throw new Error(
            `Dream confirmation stopped before EP01 workbench: ${JSON.stringify({
              bindingAvailability: episodeArtifacts.bindingAvailability,
              artifacts: Object.fromEntries(required),
            })}`,
          );
        }
      }
      consecutiveEpisodeReadFailures = 0;
      return complete;
    } catch (error) {
      if (
        error instanceof Error
        && error.message.startsWith('Dream confirmation stopped ')
      ) throw error;
      if (!isTransientApiReadFailure(error)) throw error;
      consecutiveEpisodeReadFailures += 1;
      if (consecutiveEpisodeReadFailures >= 5) throw error;
      return false;
    }
  }, {
    timeout: 720_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(true);

  await expect(
    page.getByText('EP01 · Episode execution', { exact: true }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByRole('button', { name: '构建第一集产物关联' }),
  ).toHaveCount(0);
  const storyIndexStatus = page.getByRole('region', { name: '故事文件与索引状态' });
  await expect(storyIndexStatus).toContainText('文件可读');
  const retryStoryIndexButton = storyIndexStatus.getByRole('button', { name: '重试索引同步' });
  let storyIndexRecoveryActions = 0;
  await expect.poll(async () => {
    // A completed index render can briefly retain a visible disabled retry
    // button. Let the semantic status win before considering recovery actions.
    if (await storyIndexStatus.getAttribute('data-index-status') === 'indexed') return true;
    if (storyIndexRecoveryActions >= 3) return false;
    const recheckButton = storyIndexStatus.getByRole('button', { name: '重新检查' });
    if (await recheckButton.isVisible() && await recheckButton.isEnabled()) {
      await expect(recheckButton).toBeInViewport();
      await recheckButton.click();
      storyIndexRecoveryActions += 1;
      return false;
    }
    if (await retryStoryIndexButton.isVisible() && await retryStoryIndexButton.isEnabled()) {
      await expect(retryStoryIndexButton).toBeInViewport();
      await retryStoryIndexButton.click();
      storyIndexRecoveryActions += 1;
    }
    return false;
  }, {
    message: 'A normal user must be able to recover the Story Index with visible actions.',
    timeout: 60_000,
    intervals: [500, 1_000, 2_000, 5_000],
  }).toBe(true);
  await expect(storyIndexStatus).toContainText(/PostgreSQL 索引\s*已就绪/);
  await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  const agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
  await expect(agentDialog).toBeVisible();
  await expect(agentDialog).toContainText('story-workspace-dream-confirmation');
  await expect(agentDialog).toContainText('episode-outline.md');
  await page.getByRole('button', { name: '收起 Dream Agent' }).click();

  const settledHistory = await getJson<{
    messages: Array<{ role: string; parts: Array<{ type: string; text?: string }> }>;
  }>(
    page.request,
    `/api/claude-agent/threads/${encodeURIComponent(accepted.threadId)}/messages`,
    token,
  );
  const confirmationRows = settledHistory.messages.filter((message) => (
    message.role === 'user'
    && message.parts.some((part) => part.type === 'text'
      && part.text?.includes('story-workspace-dream-confirmation'))
  ));
  expect(confirmationRows).toHaveLength(1);

  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('heading', { name: '发起一次 Dream' })).toBeVisible();
  const reentry = page.locator('.story-workspace-dream-reentry__item').filter({
    hasText: `…${accepted.workflowRunId.slice(-6)}`,
  });
  await expect(reentry).toBeVisible();
  await reentry.click();
  await page.waitForURL(
    `${WEB_BASE}/story-workspace/runs/${accepted.workflowRunId}/execution`,
  );

  await diagnostics.settle();
  expect(diagnostics.dreamFileStatuses.length).toBeGreaterThan(0);
  expect(diagnostics.dreamFileStatuses.every((status) => status === 200)).toBe(true);
  expect(diagnostics.storyIndexStatuses).toContain(200);
  expect(diagnostics.genericNotFoundConsoleErrors.length).toBeLessThanOrEqual(
    diagnostics.storyIndexStatuses.filter((status) => status === 404).length,
  );
  expect(diagnostics.errors).toEqual([]);
});
