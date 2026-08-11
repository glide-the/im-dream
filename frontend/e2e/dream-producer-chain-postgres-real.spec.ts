// [Input] Owned PostgreSQL, real Dream/Admin Gateway services, and a local no-charge tool-use Provider.
// [Output] Same-new-run browser evidence from Dream launch through completed Episode/Story facts.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_BUSINESS_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const API_BASE = process.env.INK_REAL_DREAM_API_BASE ?? 'http://127.0.0.1:18765';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');
const TEST_EMAIL = 'ink-dream-round-20260810@example.invalid';

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Run only through the owned Dream business PostgreSQL E2E runner.');

function createToken(): string {
  const source = [
    'import auth, database, sys',
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

function diagnosticsFor(page: Page, phase: () => string): {
  messages: string[];
  settle: () => Promise<void>;
} {
  const diagnostics: string[] = [];
  const pending: Promise<void>[] = [];
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    if (message.text().includes('WebSocket connection to') && message.text().includes('/?token=')) return;
    diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      pending.push(response.text().then((body) => {
        diagnostics.push(`http ${response.status()}: phase=${phase()} ${response.url()} body=${body.slice(0, 500)}`);
      }).catch(() => {
        diagnostics.push(`http ${response.status()}: phase=${phase()} ${response.url()} body=<unavailable>`);
      }));
    }
  });
  return {
    messages: diagnostics,
    settle: async () => { await Promise.allSettled(pending); },
  };
}

async function getJson<T>(request: APIRequestContext, path: string, token: string): Promise<T> {
  const response = await request.get(`${API_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(200);
  return await response.json() as T;
}

type EpisodeSurface = {
  runId: string;
  bindingAvailability: 'bound' | 'unbound';
  etag: string | null;
  artifacts: Array<{ relativeKey: string; availability: string }>;
  auxiliary: null | {
    prompts: { total: number };
    renderGuide: unknown | null;
    review: null | { scope: string; overallVerdict: string | null };
  };
  workflow: null | { nextAction: { action: string }; factsRevision: number };
  actionProjection?: null | {
    recommendedActionId: string | null;
    actionOptions: Array<{
      actionId: string;
      action: string;
      availability: string;
      canDispatch: boolean;
      dispatchState: string;
    }>;
  };
};

type DreamAgentReadySnapshot = {
  lifecycle: 'idle' | 'streaming';
  activeTurnId: string | null;
  canSend: boolean;
};

async function initialDreamSettlementEvidence(
  page: Page,
  runId: string,
  token: string,
  diagnostics: readonly string[],
): Promise<Record<string, unknown>> {
  const [run, files, messages] = await Promise.all([
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}`, token),
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}/dream-files`, token),
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}/dream-agent/messages`, token),
  ]);
  const messageItems = Array.isArray(messages.messages) ? messages.messages : [];
  return {
    workflow: {
      status: run.status,
      statusVersion: run.statusVersion,
      failedStep: run.failedStep,
      errorCode: run.errorCode,
    },
    files: {
      runRevision: files.runRevision,
      canConfirm: files.canConfirm,
      confirmationStatus: files.confirmationStatus,
      stages: files.stages && typeof files.stages === 'object'
        ? Object.entries(files.stages).map(([stage, value]) => ({
          stage,
          revision: value && typeof value === 'object' && 'revision' in value
            ? value.revision
            : undefined,
          itemCount: value && typeof value === 'object' && 'items' in value && Array.isArray(value.items)
            ? value.items.length
            : undefined,
        }))
        : [],
    },
    agent: {
      lifecycle: messages.lifecycle,
      activeTurnId: messages.activeTurnId,
      canSend: messages.canSend,
      sendBlockReason: messages.sendBlockReason,
      messages: messageItems.map((message) => ({
        id: message && typeof message === 'object' ? message.id : undefined,
        role: message && typeof message === 'object' ? message.role : undefined,
        status: message && typeof message === 'object' ? message.status : undefined,
      })),
    },
    browser: await page.evaluate((capturedDiagnostics) => {
      const buttons = [...document.querySelectorAll<HTMLButtonElement>('button')];
      return {
        href: window.location.pathname + window.location.search,
        title: document.title,
        rootChildCount: document.querySelector('#root')?.childElementCount ?? null,
        confirmDisabled: buttons.find((button) => button.textContent?.trim() === '确认并继续')?.disabled ?? null,
        stages: [...document.querySelectorAll<HTMLButtonElement>('.story-workspace-dream__stage')].map((button) => ({
          text: button.textContent?.trim().replace(/\s+/g, ' '),
          disabled: button.disabled,
        })),
        footer: document.querySelector('.story-workspace-dream__confirmation')?.textContent?.trim().replace(/\s+/g, ' ').slice(0, 500) ?? null,
        statuses: [...document.querySelectorAll<HTMLElement>('[role="status"], [role="alert"]')]
          .map((element) => element.textContent?.trim().replace(/\s+/g, ' ').slice(0, 300)),
        diagnostics: capturedDiagnostics,
      };
    }, diagnostics),
  };
}

async function waitForAgentReady(
  request: APIRequestContext,
  runId: string,
  token: string,
): Promise<void> {
  await expect.poll(async () => {
    const snapshot = await getJson<DreamAgentReadySnapshot>(
      request,
      `/api/story-workspace/workflow-runs/${runId}/dream-agent/messages`,
      token,
    );
    return snapshot.lifecycle === 'idle'
      && snapshot.activeTurnId === null
      && snapshot.canSend;
  }, { timeout: 30_000, intervals: [250, 500, 1_000] }).toBe(true);
}

async function waitForSurface(
  request: APIRequestContext,
  runId: string,
  token: string,
  predicate: (surface: EpisodeSurface) => boolean,
): Promise<EpisodeSurface> {
  let latest: EpisodeSurface | null = null;
  try {
    await expect.poll(async () => {
      latest = await getJson<EpisodeSurface>(request, `/api/story-workspace/workflow-runs/${runId}/episode-artifacts`, token);
      return predicate(latest);
    }, { timeout: 90_000, intervals: [500, 1_000, 2_000] }).toBe(true);
  } catch (cause) {
    const evidence = latest as EpisodeSurface | null;
    throw new Error(`Episode surface did not settle: ${JSON.stringify({
      bindingAvailability: evidence?.bindingAvailability,
      etag: evidence?.etag,
      workflow: evidence?.workflow ? {
        factsRevision: evidence.workflow.factsRevision,
        nextAction: evidence.workflow.nextAction,
      } : null,
      actions: evidence?.actionProjection?.actionOptions.map((item) => ({
        action: item.action,
        availability: item.availability,
        canDispatch: item.canDispatch,
        dispatchState: item.dispatchState,
      })),
      artifactAvailability: evidence?.artifacts.map((item) => ({
        relativeKey: item.relativeKey,
        availability: item.availability,
      })),
    })}`, { cause });
  }
  return latest!;
}

test('same new Run reaches Gateway-billed completed Episode and survives reentry', async ({ page }) => {
  test.setTimeout(180_000);
  let diagnosticPhase = 'setup';
  const diagnosticState = diagnosticsFor(page, () => diagnosticPhase);
  const diagnostics = diagnosticState.messages;
  const token = createToken();
  const launchBodies: unknown[] = [];
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().endsWith('/api/story-workspace/dream-runs/start')) {
      launchBodies.push(request.postDataJSON());
    }
  });
  await page.addInitScript((accessToken) => {
    localStorage.setItem('auth_token', accessToken);
    localStorage.setItem('migration_completed', 'true');
  }, token);

  await page.setViewportSize({ width: 1440, height: 1000 });
  diagnosticPhase = 'launch-form';
  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('heading', { name: '发起一次 Dream' })).toBeVisible();
  await expect(page.getByText(/Dream 剧本生产 · 剧本生产 Agent/)).toBeVisible();
  await page.getByRole('textbox', { name: '创作目标' }).fill('创作一个雨夜末班车短剧，并生产完整第一集受控产物。');
  const launchResponse = page.waitForResponse((response) => (
    response.url().endsWith('/api/story-workspace/dream-runs/start')
    && response.request().method() === 'POST'
  ), { timeout: 30_000 });
  await expect(page.getByRole('button', { name: '发起 Dream' })).toBeEnabled();
  await page.getByRole('button', { name: '发起 Dream' }).click();
  diagnosticPhase = 'initial-dream';
  const launched = await launchResponse;
  expect(launched.status(), await launched.text()).toBe(201);
  await page.waitForURL(/\/story-workspace\/dream\?run=run_[0-9a-f]{32}/, { timeout: 30_000 });
  const runId = new URL(page.url()).searchParams.get('run');
  expect(runId).toMatch(/^run_[0-9a-f]{32}$/);
  expect(launchBodies).toHaveLength(1);

  try {
    await expect(page.getByRole('button', { name: '确认并继续' })).toBeEnabled({ timeout: 120_000 });
  } catch (cause) {
    const evidence = await initialDreamSettlementEvidence(page, runId!, token, diagnostics);
    throw new Error(`Initial Dream did not settle: ${JSON.stringify(evidence)}`, { cause });
  }
  await expect(page.getByRole('button', { name: '人物' })).toBeEnabled();
  await expect(page.getByRole('button', { name: '场景' })).toBeEnabled();
  await expect(page.getByRole('button', { name: '分镜' })).toBeEnabled();
  const confirmationResponse = page.waitForResponse((response) => (
    response.url().includes(`/workflow-runs/${runId}/dream-confirmation`)
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: '确认并继续' }).click();
  diagnosticPhase = 'confirmation';
  const confirmed = await confirmationResponse;
  expect(confirmed.status(), await confirmed.text()).toBe(202);
  await expect(page.getByRole('button', { name: '查看后续执行' })).toBeVisible({ timeout: 60_000 });

  let surface = await waitForSurface(page.request, runId!, token, (value) => (
    value.bindingAvailability === 'unbound' && value.runId === runId
  ));
  const recover = await page.request.post(`${API_BASE}/api/story-workspace/workflow-runs/${runId}/episode-binding/recover`, {
    headers: { authorization: `Bearer ${token}` },
    data: { idempotencyKey: 'e2e-recover-binding-001' },
  });
  expect(recover.status(), await recover.text()).toBe(202);
  diagnosticPhase = 'binding-recovery';
  surface = await waitForSurface(page.request, runId!, token, (value) => value.bindingAvailability === 'bound');
  await waitForAgentReady(page.request, runId!, token);
  surface = await getJson<EpisodeSurface>(
    page.request,
    `/api/story-workspace/workflow-runs/${runId}/episode-artifacts`,
    token,
  );

  const actionTimeline: string[] = [];
  for (let index = 0; index < 12; index += 1) {
    const action = surface.workflow?.nextAction.action;
    if (action === 'none_in_scope') break;
    const projection = surface.actionProjection;
    const selected = projection?.actionOptions.find((item) => (
      item.actionId === projection.recommendedActionId
    )) ?? projection?.actionOptions.find((item) => item.availability === 'executable' && item.canDispatch);
    expect(selected, `No executable server action for ${action}`).toBeTruthy();
    diagnosticPhase = `episode:${selected!.action}`;
    actionTimeline.push(selected!.action);
    const previousEtag = surface.etag;
    expect(previousEtag).not.toBeNull();
    const response = await page.request.post(`${API_BASE}/api/story-workspace/workflow-runs/${runId}/episode-actions/continue`, {
      headers: {
        authorization: `Bearer ${token}`,
        'if-match': `"${surface.etag}"`,
      },
      data: {
        actionId: selected!.actionId,
        idempotencyKey: `e2e-action-${String(index + 1).padStart(2, '0')}-${selected!.action}`,
        userGuidance: null,
      },
    });
    expect(response.status(), `${selected!.action}: ${await response.text()}`).toBe(202);
    surface = await waitForSurface(page.request, runId!, token, (value) => (
      value.etag !== previousEtag
      && value.workflow?.nextAction.action !== selected!.action
      && value.actionProjection?.actionOptions.every((item) => item.dispatchState !== 'dispatching') !== false
    ));
    await waitForAgentReady(page.request, runId!, token);
    surface = await getJson<EpisodeSurface>(
      page.request,
      `/api/story-workspace/workflow-runs/${runId}/episode-artifacts`,
      token,
    );
  }

  expect(actionTimeline).toEqual([
    'plan_episode',
    'write_script',
    'review_script',
    'generate_prompts',
    'review_full_chain',
    'validate_episode',
    'prepare_render_guide',
  ]);
  expect(surface.workflow?.nextAction.action).toBe('none_in_scope');
  expect(surface.artifacts.filter((item) => item.availability === 'available').map((item) => item.relativeKey))
    .toEqual(expect.arrayContaining(['episode-outline.md', 'script.md', 'storyboard.yaml']));
  expect(surface.auxiliary).toMatchObject({
    prompts: { total: 3 },
    renderGuide: expect.any(Object),
    review: { scope: 'full-chain', overallVerdict: 'APPROVED' },
  });

  diagnosticPhase = 'terminal-read';

  const [run, files, messages, storyIndex] = await Promise.all([
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}`, token),
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}/dream-files`, token),
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}/dream-agent/messages`, token),
    getJson<Record<string, unknown>>(page.request, `/api/story-workspace/workflow-runs/${runId}/story-index`, token),
  ]);
  expect(run).toMatchObject({ status: 'completed' });
  expect(files).toMatchObject({ storyWorkspaceRunId: runId, canConfirm: false });
  expect(messages).toMatchObject({
    storyWorkspaceRunId: runId,
    lifecycle: 'idle',
    activeTurnId: null,
    canSend: true,
  });
  expect(storyIndex).toMatchObject({
    runId,
    status: 'indexed',
    episodeCount: 1,
    errorCode: null,
    retryable: false,
  });
  expect(storyIndex.indexedManifestRevision).toBe(storyIndex.observedManifestRevision);
  expect(storyIndex.indexedScriptRevision).toBe(storyIndex.observedScriptRevision);

  const replay = await page.request.post(`${API_BASE}/api/story-workspace/dream-runs/start`, {
    headers: { authorization: `Bearer ${token}` },
    data: launchBodies[0],
  });
  expect(replay.status(), await replay.text()).toBe(201);
  expect(await replay.json()).toMatchObject({ workflowRunId: runId });

  await page.goto(`${WEB_BASE}/story-workspace/runs/${runId}/execution`);
  await expect(page.getByRole('region', { name: '第一集产物工作台' })).toBeVisible();
  await expect(page.getByText('分集大纲', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('region', { name: '第一集产物工作台' })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  await expect(page.getByRole('button', { name: '打开故事线' })).toBeVisible();
  diagnosticPhase = 'no-run-reentry';
  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('button', { name: /创作一个雨夜末班车短剧/ })).toBeVisible();
  await diagnosticState.settle();
  expect(diagnostics).toEqual([]);
});
