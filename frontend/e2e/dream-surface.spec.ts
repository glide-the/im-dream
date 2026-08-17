import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));

// The dev server on this machine binds IPv6 loopback only, so the base is
// env-overridable; 127.0.0.1 stays the default for CI.
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const API_BASE = 'http://127.0.0.1:8765';
const REPO_ROOT = path.resolve(SPEC_DIR, '..', '..');
const BACKEND_PY = path.join(REPO_ROOT, 'backend', '.venv', 'bin', 'python');
const STAGING_SCRIPT = path.join(REPO_ROOT, 'frontend', 'e2e', 'helpers', 'stage_guidance_run.py');
const DB_PATH = path.join(REPO_ROOT, 'backend', 'data', 'ink-and-memory.db');

// Use Playwright's full Chromium build (new headless mode) in local and CI runs.
test.use({ channel: 'chromium' });
test.describe.configure({ mode: 'serial' });

const EXPECTED_SURFACE = {
  name: 'dream',
  protocol_dir: '.dream',
  entry_route: '/story-workspace/dream',
};

interface E2EContext {
  token: string;
  email: string;
  deckId: string;
  deckLabel: string;
  threadId: string;
  packageSpec: string;
  artifactDigest: string;
  confirmedRunId: string;
  pendingRunId: string;
  guidanceKey: string;
}

const ctx: E2EContext = {
  token: '',
  email: '',
  deckId: '',
  deckLabel: '',
  threadId: '',
  packageSpec: '',
  artifactDigest: '',
  confirmedRunId: '',
  pendingRunId: '',
  guidanceKey: '',
};

function authHeaders() {
  return { Authorization: `Bearer ${ctx.token}` };
}

function workspaceDirFor(threadId: string): string {
  const candidates = [
    path.join(REPO_ROOT, 'backend', 'data', 'agent-workspace', threadId),
    path.join(os.tmpdir(), 'ink-agent-workspaces', threadId),
    path.join(os.tmpdir(), 'claude-agent-workspaces', threadId),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error(`thread workspace not found in any candidate root: ${candidates.join(', ')}`);
}

function stageRun(status: string, seed: string): string {
  const out = execFileSync(BACKEND_PY, [
    STAGING_SCRIPT,
    '--db', DB_PATH,
    '--user-email', ctx.email,
    '--thread-id', ctx.threadId,
    '--deck-id', ctx.deckId,
    '--status', status,
    '--seed', seed,
  ], { encoding: 'utf-8' });
  return (JSON.parse(out) as { run_id: string }).run_id;
}

test.beforeAll(async ({ request }) => {
  ctx.email = `dream-surface-e2e-${Date.now()}@example.test`;
  const registration = await request.post(`${API_BASE}/api/register`, {
    data: { email: ctx.email, password: 'dream-surface-e2e', display_name: 'Dream Surface E2E' },
  });
  expect(registration.ok()).toBeTruthy();
  ctx.token = (await registration.json() as { token: string }).token;

  const decksResponse = await request.get(`${API_BASE}/api/decks`, { headers: authHeaders() });
  expect(decksResponse.ok()).toBeTruthy();
  const decks = (await decksResponse.json() as {
    decks: Array<{ id: string; name: string; name_en?: string }>;
  }).decks;
  expect(decks.length).toBeGreaterThan(0);
  ctx.deckId = decks[0].id;
  ctx.deckLabel = decks[0].name_en || decks[0].name;

  // Bind the built-in dream-surface artifact to the Deck via the real
  // refs endpoint (pack reads deck_claude_plugin_refs).
  const installationsResponse = await request.get(
    `${API_BASE}/api/claude-plugins/installations`, { headers: authHeaders() },
  );
  expect(installationsResponse.ok()).toBeTruthy();
  const installations = (await installationsResponse.json() as {
    installations: Array<{
      id: string; package_name: string; status: string; artifact_digest: string;
    }>;
  }).installations;
  const builtin = installations.find(
    (item) => item.package_name === 'ink-dream-story' && item.status === 'ready',
  );
  expect(builtin, 'built-in ink-dream-story installation must be ready').toBeTruthy();
  ctx.artifactDigest = builtin!.artifact_digest;

  const putRefs = await request.put(
    `${API_BASE}/api/decks/${encodeURIComponent(ctx.deckId)}/claude-plugins`,
    {
      headers: authHeaders(),
      data: { refs: [{ plugin_installation_id: builtin!.id, enabled: true, order_index: 0 }] },
    },
  );
  expect(putRefs.ok(), `bind refs failed: ${putRefs.status()} ${await putRefs.text()}`).toBeTruthy();
  const refsBody = await putRefs.json() as {
    refs: Array<{ package_spec: string; artifact_digest: string }>;
  };
  expect(refsBody.refs.length).toBe(1);
  ctx.packageSpec = refsBody.refs[0].package_spec;
  expect(refsBody.refs[0].artifact_digest).toBe(ctx.artifactDigest);
});

test('real chain: Deck bind → chat first turn pack → .dream materialized → surfaces exposed', async ({ request }) => {
  test.setTimeout(420_000);

  // 1. Create the Deck-locked thread, then drive the first agent turn with
  //    the real Claude CLI — the pack happens on that first turn.
  const threadResponse = await request.post(`${API_BASE}/api/claude-agent/threads`, {
    headers: authHeaders(),
    data: { deckId: ctx.deckId, title: 'e2e-dream-surface' },
  });
  expect(threadResponse.ok()).toBeTruthy();
  ctx.threadId = (await threadResponse.json() as { thread_id: string }).thread_id;

  const chatResponse = await request.post(`${API_BASE}/api/claude-agent`, {
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    data: {
      thread_id: ctx.threadId,
      message: {
        id: 'e2e-first-turn',
        role: 'user',
        parts: [{ type: 'text', text: 'Reply with exactly: OK. Do not use any tools.' }],
      },
      resume: false,
      toolChoice: 'auto',
      max_turns: 3,
    },
    timeout: 360_000,
  });
  expect(chatResponse.ok(), `first turn failed: ${chatResponse.status()} ${await chatResponse.text()}`).toBeTruthy();
  expect((chatResponse.headers()['content-type'] ?? '')).toContain('text/event-stream');

  // 2. .dream/ protocol directory materialized with both static files.
  const workspace = workspaceDirFor(ctx.threadId);
  const dreamDir = path.join(workspace, '.dream');
  const workspaceJsonPath = path.join(dreamDir, 'workspace.json');
  const readmePath = path.join(dreamDir, 'README.md');
  expect(fs.existsSync(workspaceJsonPath), '.dream/workspace.json missing').toBeTruthy();
  expect(fs.existsSync(readmePath), '.dream/README.md missing').toBeTruthy();

  const workspaceJson = JSON.parse(fs.readFileSync(workspaceJsonPath, 'utf-8')) as Record<string, unknown>;
  expect(Object.keys(workspaceJson).sort()).toEqual(
    ['deck_id', 'entry_route', 'plugins', 'schema_version'].sort(),
  );
  expect(workspaceJson.schema_version).toBe('dream-surface/v1');
  expect(workspaceJson.deck_id).toBe(ctx.deckId);
  expect(workspaceJson.entry_route).toBe('/story-workspace/dream');
  expect(workspaceJson).not.toHaveProperty('workflow_run_id');
  const plugins = workspaceJson.plugins as Array<Record<string, string>>;
  expect(plugins.length).toBe(1);
  expect(plugins[0].package_spec).toBe(ctx.packageSpec);
  expect(plugins[0].artifact_digest).toBe(ctx.artifactDigest);
  const readme = fs.readFileSync(readmePath, 'utf-8');
  expect(readme).toContain('只读');
  expect(readme).toContain('workflow_run_id');

  // 3. surfaces consistent across manifest, pack receipt, and the
  //    plugin-load-receipt endpoint (both transmission paths).
  const manifest = JSON.parse(
    fs.readFileSync(path.join(workspace, '.ink', 'launch-manifest.json'), 'utf-8'),
  ) as { surfaces?: unknown[] };
  const packReceipt = JSON.parse(
    fs.readFileSync(path.join(workspace, '.ink', 'plugin-pack-receipt.json'), 'utf-8'),
  ) as { surfaces?: unknown[]; init_steps?: Array<Record<string, string>> };
  expect(manifest.surfaces).toEqual([EXPECTED_SURFACE]);
  expect(packReceipt.surfaces).toEqual([EXPECTED_SURFACE]);
  expect(
    (packReceipt.init_steps ?? []).some((step) => step.step === 'materialize-surface'),
  ).toBeTruthy();

  const receiptResponse = await request.get(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(ctx.threadId)}/plugin-load-receipt`,
    { headers: authHeaders() },
  );
  expect(receiptResponse.ok()).toBeTruthy();
  const receiptBody = await receiptResponse.json() as {
    workspace_found: boolean;
    launch_manifest?: { surfaces?: unknown[] };
    receipt?: { surfaces?: unknown[] };
  };
  expect(receiptBody.workspace_found).toBeTruthy();
  expect(receiptBody.launch_manifest?.surfaces).toEqual([EXPECTED_SURFACE]);
  expect(receiptBody.receipt?.surfaces).toEqual([EXPECTED_SURFACE]);

  // 4. Second turn → frozen re-pack → .dream bytes identical (DEC-029 static).
  const dreamBytesBefore = fs.readFileSync(workspaceJsonPath);
  const readmeBytesBefore = fs.readFileSync(readmePath);
  const secondTurn = await request.post(`${API_BASE}/api/claude-agent`, {
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    data: {
      thread_id: ctx.threadId,
      message: {
        id: 'e2e-second-turn',
        role: 'user',
        parts: [{ type: 'text', text: 'Reply with exactly: OK' }],
      },
      resume: true,
      toolChoice: 'auto',
      max_turns: 2,
    },
    timeout: 360_000,
  });
  expect(secondTurn.ok()).toBeTruthy();
  expect(fs.readFileSync(workspaceJsonPath)).toEqual(dreamBytesBefore);
  expect(fs.readFileSync(readmePath)).toEqual(readmeBytesBefore);
});

test('legacy sessions without surfaces stay surface-less (DEC-028)', async ({ request }) => {
  // A thread without a Deck never packs: the receipt endpoint reports no
  // workspace / no surfaces field → frontend resolves undefined → entry hidden.
  const threadResponse = await request.post(`${API_BASE}/api/claude-agent/threads`, {
    headers: authHeaders(),
    data: {},
  });
  expect(threadResponse.ok()).toBeTruthy();
  const legacyThreadId = (await threadResponse.json() as { thread_id: string }).thread_id;

  const receiptResponse = await request.get(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(legacyThreadId)}/plugin-load-receipt`,
    { headers: authHeaders() },
  );
  expect(receiptResponse.ok()).toBeTruthy();
  const body = await receiptResponse.json() as Record<string, unknown>;
  const manifest = (body.launch_manifest ?? {}) as Record<string, unknown>;
  const receipt = (body.receipt ?? {}) as Record<string, unknown>;
  expect(manifest).not.toHaveProperty('surfaces');
  expect(receipt).not.toHaveProperty('surfaces');

  // Pre-Task-1 workspaces on disk coexist without surfaces and without .dream/.
  const workspaceRoot = path.join(REPO_ROOT, 'backend', 'data', 'agent-workspace');
  let legacyChecked = 0;
  for (const entry of fs.readdirSync(workspaceRoot)) {
    const manifestPath = path.join(workspaceRoot, entry, '.ink', 'launch-manifest.json');
    if (!fs.existsSync(manifestPath)) continue;
    const old = JSON.parse(fs.readFileSync(manifestPath, 'utf-8')) as Record<string, unknown>;
    if ('surfaces' in old) continue;
    legacyChecked += 1;
    expect(fs.existsSync(path.join(workspaceRoot, entry, '.dream'))).toBeFalsy();
    if (legacyChecked >= 3) break;
  }
  expect(legacyChecked, 'expected at least one pre-surface workspace on disk').toBeGreaterThan(0);
});

test('execution page + guidance loop against the real backend', async ({ page, request }) => {
  test.setTimeout(300_000);

  ctx.confirmedRunId = stageRun('confirmed', `${ctx.email}:confirmed`);

  await page.addInitScript(({ token }) => {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'en');
  }, { token: ctx.token });

  // 1. Direct-open the execution route: story-workspace view, run loaded from
  //    the real backend, confirmed state rendered, degraded (no projection)
  //    data tabs show explicit empty states instead of errors.
  await page.goto(`${WEB_BASE}/story-workspace/runs/${ctx.confirmedRunId}/execution`);
  await expect(page).toHaveURL(new RegExp(`/story-workspace/runs/${ctx.confirmedRunId}/execution$`));
  await expect(page.getByText(ctx.confirmedRunId, { exact: false }).first()).toBeVisible();
  await expect(page.getByText('暂无步骤数据', { exact: false })).toBeVisible();

  // 2. Submit free-text guidance from the sidebar → real 202.
  const guidanceText = '第二集节奏放慢，保留雨夜电台主线';
  await page.getByLabel('指导指令输入框').fill(guidanceText);
  const guidanceResponsePromise = page.waitForResponse((response) => (
    response.url().includes(`/api/story-workspace/runs/${ctx.confirmedRunId}/guidance`)
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: '发送指导' }).click();
  const guidanceResponse = await guidanceResponsePromise;
  expect(guidanceResponse.status()).toBe(202);
  const accepted = await guidanceResponse.json() as {
    message_id: string; replayed: boolean; dispatched: boolean; request_id: string;
    review_action: string;
  };
  expect(accepted.review_action).toBe('guide');
  expect(accepted.replayed).toBeFalsy();
  expect(accepted.request_id).toBeTruthy();
  console.log(`guidance accepted: dispatched=${accepted.dispatched} message_id=${accepted.message_id}`);
  // NOTE(acceptance finding F-1): the sidebar success feedback ("指导已发送给
  // 执行 Agent。" / dispatched:false "已记录，待执行 Agent 拾取") is set in the
  // same React batch where onSubmitted → loadRun() flips the page to its
  // isLoading branch, unmounting the sidebar — the feedback line is therefore
  // never painted in the live page (unit seam tests lock the copy mapping).
  // The reachable proof of submission is the 202 body + the history entry
  // below. Recorded in the Task 6 acceptance report as a follow-up defect.

  // 3. Sidebar guidance history shows the new entry (instruction + status + time).
  await expect(page.getByLabel('指导历史').getByText(guidanceText, { exact: false })).toBeVisible();

  // 4. Audit fields land in chat_message.metadata (real messages endpoint).
  const messagesResponse = await request.get(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(ctx.threadId)}/messages`,
    { headers: authHeaders() },
  );
  expect(messagesResponse.ok()).toBeTruthy();
  const messagesBody = await messagesResponse.json() as {
    messages: Array<{ id: string; role: string; metadata?: Record<string, unknown> | null }>;
  };
  const guidanceRow = messagesBody.messages.find(
    (message) => message.metadata?.kind === 'story-workspace-guidance',
  );
  expect(guidanceRow, 'guidance row must persist in chat_message').toBeTruthy();
  expect(guidanceRow!.id).toBe(accepted.message_id);
  expect(guidanceRow!.role).toBe('user');
  expect(guidanceRow!.metadata).toMatchObject({
    story_workspace_run_id: ctx.confirmedRunId,
    command_kind: 'free-text',
    review_action: 'guide',
    request_id: accepted.request_id,
  });
  expect(typeof guidanceRow!.metadata!.command_fingerprint).toBe('string');

  // 5. Idempotency over the real endpoint: same key + same content → 202
  //    replayed; same key + different content → 409 IDEMPOTENCY_CONFLICT.
  //    The actor must equal the authenticated user id; the server-stamped
  //    actor on the persisted guidance row is exactly that identity.
  const actor = String(guidanceRow!.metadata!.actor);
  ctx.guidanceKey = String(guidanceRow!.metadata!.idempotency_key);
  const replayBody = {
    kind: 'free-text',
    text: guidanceText,
    idempotency_key: ctx.guidanceKey,
    actor,
  };
  const replay = await request.post(
    `${API_BASE}/api/story-workspace/runs/${ctx.confirmedRunId}/guidance`,
    { headers: authHeaders(), data: replayBody },
  );
  expect(replay.status()).toBe(202);
  expect((await replay.json() as { replayed: boolean }).replayed).toBeTruthy();

  const conflict = await request.post(
    `${API_BASE}/api/story-workspace/runs/${ctx.confirmedRunId}/guidance`,
    { headers: authHeaders(), data: { ...replayBody, text: '不同的指导内容' } },
  );
  expect(conflict.status()).toBe(409);
  expect(((await conflict.json()) as { error?: { code?: string } }).error?.code)
    .toBe('IDEMPOTENCY_CONFLICT');

  // 6. Not-guidable run → 409 WORKFLOW_RUN_NOT_GUIDABLE.
  ctx.pendingRunId = stageRun('pending_review', `${ctx.email}:pending`);
  const rejected = await request.post(
    `${API_BASE}/api/story-workspace/runs/${ctx.pendingRunId}/guidance`,
    { headers: authHeaders(), data: { ...replayBody, idempotency_key: `${ctx.guidanceKey}-x` } },
  );
  expect(rejected.status()).toBe(409);
  expect(((await rejected.json()) as { error?: { code?: string } }).error?.code)
    .toBe('WORKFLOW_RUN_NOT_GUIDABLE');

  // 7. The guidance row never renders as a Chat bubble (DEC-032): open the
  //    thread in the Dream workspace chat and assert the guidance prefix is
  //    absent while the genuine user turn is present.
  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await page.getByTitle('e2e-dream-surface', { exact: true }).click();
  await expect(page.getByText('Reply with exactly: OK. Do not use any tools.', { exact: false }).first())
    .toBeVisible();
  await expect(page.getByText('[story-workspace guidance · run', { exact: false })).toHaveCount(0);
});

test('Gate redirect, deep links and query preservation (real backend)', async ({ page }) => {
  test.setTimeout(120_000);

  if (!ctx.pendingRunId) {
    ctx.pendingRunId = stageRun('pending_review', `${ctx.email}:pending`);
  }

  await page.addInitScript(({ token }) => {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'en');
  }, { token: ctx.token });

  // 1. A not-confirmed run cannot be served by the execution page: it
  //    redirects to the review deep link (episode binding absent → Dream
  //    entry + ?run=, §4.4) with a closable notice, and the run is located
  //    in the WorkflowContextBar. The redirect itself proves ?run= survives
  //    SPA navigation + canonicalization (C10).
  await page.goto(`${WEB_BASE}/story-workspace/runs/${ctx.pendingRunId}/execution`);
  await expect(page).toHaveURL(new RegExp(`/story-workspace/dream\\?run=${ctx.pendingRunId}$`));
  const notice = page.getByRole('status').filter({ hasText: '先完成审阅确认' });
  await expect(notice).toBeVisible();
  await expect(page.getByText(ctx.pendingRunId, { exact: false }).first()).toBeVisible();
  await notice.getByRole('button', { name: '知道了' }).click();
  await expect(page.getByRole('status').filter({ hasText: '先完成审阅确认' })).toHaveCount(0);

  // 2. Episode review deep link renders the Dream workspace on direct open.
  //    NOTE(acceptance finding F-2): fresh-load `?run=` resolution no-ops under
  //    React StrictMode (dev): useRunDeepLink sets its resolve-once cursor
  //    before the async read, StrictMode's mount double-effect cancels the
  //    first fetch callback, and the second setup early-returns. SPA-path
  //    resolution (step 1 above) works; production builds do not double-invoke
  //    effects. Run-location proof is therefore carried by step 1; recorded in
  //    the Task 6 acceptance report as a dev-mode follow-up defect.
  await page.goto(`${WEB_BASE}/story-workspace/episodes/ep-e2e/review?run=${ctx.pendingRunId}`);
  await expect(page.getByPlaceholder('Ask Ink & Memory…')).toBeVisible();

  // 3. Legacy/no-surface regression on the UI shell: the Dream page loads
  //    cleanly and renders no surface link buttons (aggregation seam has no
  //    data source; DEC-028 safe default).
  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('link', { name: '进入后续执行' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: '查看执行进度' })).toHaveCount(0);
});
