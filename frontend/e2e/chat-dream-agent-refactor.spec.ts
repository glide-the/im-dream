// [Sync] 2026-10-28: serve complete Agent catalogs and assert the selector creates no per-Deck GET requests.
// [Input] Authenticated Story Workspace routes and production-shaped Deck/Dream/common-Skill API fixtures.
// [Output] Provider-free browser evidence for Dream's two-state home, adaptive horizontal Chat list,
//          whole-card Dream navigation, historical composer provenance, same-Deck Agent switching,
//          common-Skill slash submission, and launch handoff.
// [Pos] Dream/Chat Agent refactor business E2E in frontend/e2e.
// [Sync] 2026-10-28: record known GET lifecycle cancellations and require successful replacement reads under the existing StrictMode Web shell.
// [Sync] 2026-10-28: verify the canonical RNW Web landing retains composer/action/history order, original search, lazy New and narrow viewport; no model/persistence requests.
// [Sync] 2026-08-14: cover initial/in-progress states and adaptive horizontal Chat scrolling.
// [Sync] 2026-08-14: prove Community Decks visibly includes the system default projection.
// [Sync] 2026-08-16: Dream omits deferred community/market Deck discovery.
// [Sync] 2026-08-15: prove historical Chat removes the immutable composer selector
//                    while a fresh conversation keeps Deck -> Agent selection;
//                    a packed plugin receipt cannot replace the visible Deck name.
// [Sync] 2026-08-17: switch the next-turn Agent from the historical Thread Deck metadata popover.
// [Sync] 2026-09-02: serve the paged history contract and visually verify completed-turn
//                    process folding before the same-thread next turn.
// [Sync] 2026-09-04: prove common Skills appear through slash and submit as the ordinary user message.
// [Sync] 2026-09-13: distinguish Edit Session SSE cleanup aborts from failed business requests.
// [Sync] 2026-09-28: address the existing environment-information entry after task controls were embedded there.
// [Sync] 2026-09-28: use the current cookie-session DTO, fixture task navigation, and fail on retired task-results polling.
// [Sync] 2026-10-14: align the historical Deck metadata assertions with the current 思维模式 product label.
// [Sync] 2026-10-14: type the slash trigger through the visible Tiptap composer before asserting its menu.
// [Sync] 2026-10-14: align the slash menu locator and built-in compact option with current Chat commands.
// [Sync] 2026-10-14: serve the current Chat scheduled-task relation and turn-navigation reads in the fixture.

import { expect, test, type Request } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = 'run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const HISTORICAL_THREAD_ID = 'thread-history-deck-context-e2e';
const DREAM_IMPACT_SCOPE = {
  routeAndDefaultPanel: 'changes',
  projectAndEpisodes: 'out-of-scope',
  canonicalAndPrivateFiles: 'out-of-scope',
  realPersistenceModelAndBilling: 'out-of-scope',
} as const;

test.use({ channel: 'chromium' });

const dreamDeck = {
  id: 'dream-deck-e2e',
  name: '雨夜故事 Dream',
  name_zh: '雨夜故事 Dream',
  name_en: 'Rainy Night Dream',
  description: '从 Chat 发起真实 Dream 工作流。',
  icon: 'moon',
  color: 'purple',
  is_system: false,
  enabled: true,
  voice_count: 2,
  agent_type: 'dream',
  agent_type_revision: 3,
  voices: [{
    id: 'dream-agent-e2e',
    deck_id: 'dream-deck-e2e',
    name: '故事导演',
    system_prompt: '负责组织故事 Dream。',
    icon: 'moon',
    color: 'purple',
    is_system: false,
    enabled: true,
  }, {
    id: 'dream-agent-e2e-structure',
    deck_id: 'dream-deck-e2e',
    name: '结构顾问',
    system_prompt: '负责检查故事结构。',
    icon: 'book-open',
    color: 'teal',
    is_system: false,
    enabled: true,
  }],
};

const actorSystemDefaultDeck = {
  ...dreamDeck,
  id: 'screenplay-actor-default-e2e',
  name: '剧本创作团队',
  name_zh: '剧本创作团队',
  description: '覆盖剧情、结构、人物、对白和连续性的剧本创作角色。',
  is_system: false,
  publish_block_reason: 'default_initialized',
  can_publish: false,
  agent_type: 'dream',
  agent_type_revision: 0,
  voices: [],
};

const historicalThread = {
  id: HISTORICAL_THREAD_ID,
  title: '历史版本工作台',
  deck_id: dreamDeck.id,
  voice_id: dreamDeck.voices[0].id,
  created_at: '2026-08-14T07:00:00Z',
  updated_at: '2026-08-14T07:30:00Z',
};

const historicalMessages = [{
  id: 'history-user-message-e2e',
  role: 'user',
  parts: [{ type: 'text', text: '请分析这一段历史内容。' }],
  metadata: {},
  created_at: '2026-08-14T07:10:00Z',
}, {
  id: 'history-assistant-message-e2e',
  role: 'assistant',
  parts: [
    { type: 'reasoning', text: '历史思考链仅在展开后挂载。' },
    { type: 'text', text: '历史中间文本仅在展开后挂载。' },
    { type: 'reasoning', text: '历史收束过程仍属于同一轮。' },
    { type: 'text', text: '这是历史轮次的最终答复。' },
  ],
  metadata: {
    turnId: 'history-completed-turn-e2e',
    turnStatus: 'completed',
    finalPartIndex: 3,
    durationMs: 12_500,
  },
  created_at: '2026-08-14T07:12:00Z',
}];

function dreamRun(
  suffix: string,
  lifecycle: 'generating' | 'waiting_confirmation' | 'running' | 'recent',
  displayTitle: string,
) {
  const storyWorkspaceRunId = `run_${suffix.repeat(32)}`;
  const confirmationAccepted = lifecycle === 'running' || lifecycle === 'recent';
  const confirmationDispatched = lifecycle === 'recent';
  const outcome = confirmationAccepted ? 'in_progress' : 'initial';
  return {
    storyWorkspaceRunId,
    displayTitle,
    goalPrefix: '创作一个克制的短篇故事',
    deckId: dreamDeck.id,
    deckDisplayName: dreamDeck.name,
    workflowDisplayName: 'Dream',
    deckPluginVersion: '1.0.0',
    lifecycle,
    outcome,
    group: lifecycle === 'recent' ? 'recent' : 'in_progress',
    stageRevisions: lifecycle === 'generating' ? {} : { characters: 1, scenes: 1, storyboards: 1 },
    confirmationAccepted,
    confirmationDispatched,
    lastActivityAt: '2026-08-14T09:00:00Z',
    createdAt: '2026-08-14T08:00:00Z',
    sortKey: `${outcome}:${storyWorkspaceRunId}`,
    href: confirmationAccepted
      ? `/story-workspace/runs/${storyWorkspaceRunId}/execution`
      : `/story-workspace/dream?run=${storyWorkspaceRunId}`,
  };
}

const runs = [
  dreamRun('a', 'generating', '初始的雨夜故事'),
  dreamRun('b', 'waiting_confirmation', '待确认的海边来信'),
  dreamRun('c', 'running', '进行中的城市漫游'),
  dreamRun('d', 'recent', '持续创作的山间来客'),
  dreamRun('e', 'running', '进行中的旧城回声'),
  dreamRun('f', 'running', '进行中的南方手记'),
];

test('Dream active Deck context → workbench → Chat active tab → production launch endpoint', async ({ page }, testInfo) => {
  expect(DREAM_IMPACT_SCOPE).toEqual({
    routeAndDefaultPanel: 'changes',
    projectAndEpisodes: 'out-of-scope',
    canonicalAndPrivateFiles: 'out-of-scope',
    realPersistenceModelAndBilling: 'out-of-scope',
  });
  const diagnostics: string[] = [];
  const cancelledLifecycleReads: { path: string; order: number }[] = [];
  const successfulGetReads: { path: string; order: number }[] = [];
  const requestOrder = new WeakMap<Request, number>();
  let nextRequestOrder = 0;
  const lifecycleReadPaths = new Set([
    '/auth/session',
    `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/inputs`,
    '/api/claude-agent/threads/thread-dream-e2e/inputs',
  ]);
  const unexpectedApiRequests: string[] = [];
  let launchBody: Record<string, unknown> | null = null;
  let historicalChatTurnBody: Record<string, unknown> | null = null;
  let releaseDeepLinkRead: (() => void) | null = null;
  let createdThreadRequests = 0;
  const deckDetailReads: string[] = [];
  page.on('request', request => {
    requestOrder.set(request, ++nextRequestOrder);
    const path = new URL(request.url()).pathname;
    if (request.method() === 'GET' && [
      `/api/decks/${dreamDeck.id}`, `/api/decks/${actorSystemDefaultDeck.id}`,
    ].includes(path)) deckDetailReads.push(path);
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/claude-agent/threads') createdThreadRequests++;
  });
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().includes('react-grab.com')) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('response', response => {
    const url = new URL(response.url());
    if (response.request().method() === 'GET' && response.status() === 200 && url.origin === new URL(WEB_BASE).origin) successfulGetReads.push({ path: url.pathname, order: requestOrder.get(response.request()) ?? 0 });
  });
  page.on('requestfailed', (request) => {
    const failedUrl = new URL(request.url());
    const expectedNavigationAbort = request.failure()?.errorText === 'net::ERR_ABORTED'
      && request.method() === 'GET'
      && failedUrl.origin === new URL(WEB_BASE).origin
      && (['/api/story-workspace/dream-runs', '/api/sessions/events'].includes(failedUrl.pathname)
        || (failedUrl.pathname === '/api/claude-agent/threads' && failedUrl.search === '?limit=21')
        || (failedUrl.pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/scheduled-tasks`)
        || lifecycleReadPaths.has(failedUrl.pathname));
    if (expectedNavigationAbort && lifecycleReadPaths.has(failedUrl.pathname)) cancelledLifecycleReads.push({ path: failedUrl.pathname, order: requestOrder.get(request) ?? 0 });
    if (!expectedNavigationAbort && !request.url().includes('react-grab.com') && !request.url().includes('fonts.')) {
      diagnostics.push(`${request.failure()?.errorText ?? 'request failed'} ${request.url()}`);
    }
  });

  await page.addInitScript(() => {
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });

  await page.route(/^https?:\/\/unpkg\.com\/react-grab\/.*/, async (route) => route.fulfill({
    status: 200,
    contentType: 'application/javascript',
    headers: { 'access-control-allow-origin': '*' },
    body: '',
  }));

  await page.route(`${WEB_BASE}/auth/session`, async (route) => route.fulfill({
    json: {
      user: { id: '314', email: 'dream-e2e@example.test', display_name: 'Dream E2E', avatar_url: null, role: 'user', created_at: null },
      csrf_token: 'a'.repeat(43),
    },
  }));

  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const { pathname } = url;
    if (pathname === '/api/me') return route.fulfill({ json: { id: 314, email: 'dream-e2e@example.test', display_name: 'Dream E2E' } });
    if (pathname === '/api/preferences') return route.fulfill({ json: { first_login_completed: true, timezone: 'Asia/Shanghai' } });
    if (pathname === '/api/sessions' || pathname === '/api/sessions/range') return route.fulfill({ json: { sessions: [] } });
    if (pathname === '/api/sessions/events') return route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
    if (pathname === '/api/pictures/range') return route.fulfill({ json: { pictures: [] } });
    if (pathname === '/api/default-voices') return route.fulfill({ json: {} });
    if (pathname === '/api/storage') return route.fulfill({ json: { type: 'unknown', supportsDirectUpload: false, isConfigured: true } });
    if (pathname === '/api/system-config') return route.fulfill({ json: { data: { im_full_access_enabled: false, workspace_enabled: true } } });
    if (pathname === '/api/decks/defaults/reconcile' && request.method() === 'POST') {
      return route.fulfill({ json: { deck_id: actorSystemDefaultDeck.id, reconciled: false, reason: 'refs_preserved' } });
    }
    if ((pathname === '/api/decks' || pathname === '/api/decks/catalog') && request.method() === 'GET') {
      const decks = url.searchParams.get('published') === 'true'
        ? [dreamDeck]
        : [actorSystemDefaultDeck, dreamDeck];
      return route.fulfill({ json: { decks } });
    }
    if (pathname === `/api/decks/${dreamDeck.id}` && request.method() === 'GET') return route.fulfill({ json: dreamDeck });
    if (pathname === `/api/decks/${actorSystemDefaultDeck.id}` && request.method() === 'GET') {
      return route.fulfill({ json: actorSystemDefaultDeck });
    }
    if (pathname === '/api/claude-plugins/installations') return route.fulfill({ json: { installations: [] } });
    if (pathname === `/api/decks/${dreamDeck.id}/claude-plugins`) return route.fulfill({ json: { deck_id: dreamDeck.id, refs: [] } });
    if (pathname === '/api/claude-agent/skill-commands') {
      return route.fulfill({
        json: {
          commands: [
            { command: '/asr', name: 'asr' },
            { command: '/hhxg-market', name: 'hhxg-market' },
            { command: '/investment-data', name: 'investment-data' },
            { command: '/skill-creator', name: 'skill-creator' },
            { command: '/symbolic-board', name: 'symbolic-board' },
          ],
        },
      });
    }
    if (pathname === '/api/claude-agent/threads' && request.method() === 'GET') {
      return route.fulfill({ json: { threads: [historicalThread] } });
    }
    if (pathname === '/api/story-workspace/dream-runs' && request.method() === 'GET') return route.fulfill({ json: { runs } });
    if (pathname === '/api/story-workspace/dream-runs/start' && request.method() === 'POST') {
      launchBody = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({ status: 201, json: { workflowRunId: RUN_ID, threadId: 'thread-dream-e2e' } });
    }
    if (pathname === `/api/story-workspace/workflow-runs/${RUN_ID}`) {
      if (launchBody) {
        return route.fulfill({
          json: {
            workflow_run_id: RUN_ID,
            deck_plugin_id: dreamDeck.id,
            deck_plugin_display_name: dreamDeck.name,
            deck_plugin_version: '1.0.0',
            workflow_definition_ref: 'dream',
            workflow_summary: '创作一个发生在雨夜车站的克制短篇。',
            deck_runtime_snapshot_id: 'snapshot-dream-e2e',
            runtime_plugin_lock_id: 'lock-dream-e2e',
            runtime_load_receipt_id: null,
            workflow_preflight_id: 'preflight-dream-e2e',
            status: 'running',
            status_version: 1,
            failed_step: null,
            error_code: null,
            retry_of_run_id: null,
            source_voice_thread_id: 'thread-dream-e2e',
            created_at: '2026-08-14T08:00:00Z',
            started_at: '2026-08-14T08:00:01Z',
            completed_at: null,
          },
        });
      }
      await new Promise<void>((resolve) => { releaseDeepLinkRead = resolve; });
      return route.fulfill({ json: {} });
    }
    if (pathname === `/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`) {
      return route.fulfill({
        json: {
          storyWorkspaceRunId: RUN_ID,
          threadId: 'thread-dream-e2e',
          source: {
            deckPluginBindingId: 'binding-dream-e2e',
            bindingRevision: 1,
            deckPluginVersion: '1.0.0',
            deckRuntimeSnapshotId: 'snapshot-dream-e2e',
            runtimePluginLockId: 'lock-dream-e2e',
          },
          requiredStages: ['characters', 'scenes', 'storyboards'],
          runRevision: 0,
          stages: {},
          confirmationAccepted: false,
          confirmationDispatched: false,
          canConfirm: false,
          confirmationLabel: '确认并继续',
          agentActivity: null,
        },
      });
    }
    if (pathname === '/api/claude-agent/threads/thread-dream-e2e/messages') {
      return route.fulfill({
        json: {
          messages: [],
          next_cursor: null,
          has_more: false,
          latest_message_id: null,
          unchanged: false,
        },
      });
    }
    if (pathname === '/api/claude-agent/threads/thread-dream-e2e/plugin-load-receipt') {
      return route.fulfill({
        json: {
          thread_id: 'thread-dream-e2e',
          deck_id: dreamDeck.id,
          workspace_found: false,
          receipt: null,
          launch_manifest: null,
        },
      });
    }
    if (pathname === '/api/claude-agent/threads/thread-dream-e2e/status') {
      return route.fulfill({
        json: {
          running: false,
          lifecycle: 'idle',
          turn_count: 0,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/messages`) {
      const unchanged = url.searchParams.get('known_latest_message_id') === 'history-assistant-message-e2e';
      return route.fulfill({
        json: {
          thread: historicalThread,
          messages: unchanged ? [] : historicalMessages,
          next_cursor: null,
          has_more: false,
          latest_message_id: 'history-assistant-message-e2e',
          unchanged,
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/plugin-load-receipt`) {
      return route.fulfill({
        json: {
          thread_id: HISTORICAL_THREAD_ID,
          deck_id: dreamDeck.id,
          workspace_found: true,
          receipt: {
            schema_version: '1',
            workspace: '/server-managed/redacted',
            deck_id: dreamDeck.id,
            packed_at: '2026-08-14T07:20:00Z',
            frozen: true,
            plugins: [{
              package_spec: 'drama-forge@drama-studio',
              resolved_version: '1.0.1',
              artifact_digest: 'sha256:historical-drama-forge',
              relative_path: '.claude/plugins/drama-forge',
              file_count: 12,
              verified: true,
            }],
          },
          launch_manifest: null,
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/status`) {
      return route.fulfill({
        json: {
          running: false,
          lifecycle: 'idle',
          turn_count: 0,
          pending_tool_call_ids: [],
          tool_confirmation_observation: 'known',
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/plan`) {
      return route.fulfill({
        json: {
          exists: false,
          plan_mode: 'none',
          slug: null,
          file_name: null,
          content: null,
          updated_at: null,
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/todos`) {
      return route.fulfill({
        json: {
          exists: false,
          source: null,
          todos: [],
          truncated: false,
          updated_at: null,
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/subagents`) {
      return route.fulfill({
        json: {
          exists: false,
          tasks: [],
          counts: { running: 0, completed: 0, ended: 0, total: 0 },
          updated_at: null,
        },
      });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/task-links`) {
      return route.fulfill({ json: { source: null, created: [] } });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/scheduled-tasks`) {
      return route.fulfill({ json: { created: [], source: null } });
    }
    if (pathname === `/api/claude-agent/threads/${HISTORICAL_THREAD_ID}/turn-navigation`) {
      return route.fulfill({ json: {
        items: [{
          message_id: 'history-user-message-e2e',
          user_preview: '请分析这一段历史内容。',
          has_attachment: false,
          assistant_preview: '这是历史轮次的最终答复。',
          status: 'answered',
        }],
      } });
    }
    if (/^\/api\/claude-agent\/threads\/[^/]+\/inputs$/.test(pathname) && request.method() === 'GET') {
      return route.fulfill({ json: { entries: [], local_owner: false } });
    }
    if (/^\/api\/claude-agent\/threads\/[^/]+\/task-links$/.test(pathname) && request.method() === 'GET') {
      return route.fulfill({ json: { source: null, created: [] } });
    }
    if (pathname === '/api/claude-agent' && request.method() === 'POST') {
      historicalChatTurnBody = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        contentType: 'text/event-stream',
        body: 'event: finish\ndata: {"finishReason":"stop"}\n\n',
      });
    }
    unexpectedApiRequests.push(`${request.method()} ${pathname}`);
    return route.fulfill({ status: 404, json: { detail: 'unexpected provider-free E2E request' } });
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  const activeSection = page.getByRole('region', { name: '进行中的 Dream' });
  await expect(activeSection.getByRole('heading', { name: '进行中的 Dream' })).toBeVisible();
  await expect(page.getByText(/社区卡组|System default Deck|安装并使用/)).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '我的 Dream' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '进行中', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '初始状态', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '已完成' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '失败' })).toHaveCount(0);
  await expect(page.locator('.story-workspace-dream-home__overview')).toHaveCount(0);
  expect(await activeSection.evaluate((element) => getComputedStyle(element).borderTopWidth)).toBe('0px');
  expect(await activeSection.getByRole('link').first().evaluate(
    (element) => getComputedStyle(element).borderTopWidth,
  )).toBe('0px');
  await expect(activeSection.getByRole('link', { name: /进行中的南方手记/ })).toHaveCount(0);
  const showMoreActiveDreams = activeSection.getByRole('button', { name: '查看更多（1）' });
  await expect(showMoreActiveDreams).toHaveAttribute('aria-expanded', 'false');
  await page.screenshot({ path: '../output/playwright/dream-home-active-preview.png' });
  await showMoreActiveDreams.click();
  const collapseActiveDreams = activeSection.getByRole('button', { name: '收起' });
  await expect(collapseActiveDreams).toHaveAttribute('aria-expanded', 'true');
  await expect(activeSection.getByRole('link', { name: /进行中的南方手记/ })).toBeVisible();
  await expect(collapseActiveDreams).toBeVisible();
  await page.screenshot({ path: '../output/playwright/dream-home-active-expanded.png' });
  const layoutMain = page.locator('[data-story-workspace-region="main"]');
  await expect.poll(() => layoutMain.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);
  expect(await layoutMain.evaluate((element) => getComputedStyle(element).overflowY)).toBe('auto');
  expect(await page.locator('.story-workspace-dream-home').evaluate((element) => getComputedStyle(element).overflowY)).toBe('visible');
  await page.screenshot({ path: '../output/playwright/dream-home-wide-top.png' });
  await page.getByRole('link', { name: /初始的雨夜故事/ }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('link', { name: /初始的雨夜故事/ })).toBeVisible();
  await page.screenshot({ path: '../output/playwright/dream-home-wide.png', fullPage: true });

  const promotedDreamLink = activeSection.getByRole('link', { name: /进行中的城市漫游/ });
  await expect(promotedDreamLink).toHaveAttribute('href', '/story-workspace/runs/run_cccccccccccccccccccccccccccccccc/execution');

  await page.goto(`${WEB_BASE}/story-workspace/chat?deck=${dreamDeck.id}`);
  await expect(page.getByRole('tab', { name: '聊天历史' })).toBeVisible();
  const agentSelector = page.getByRole('button', { name: '为本次对话选择一个 Agent' });
  await expect(agentSelector).toBeVisible();
  await expect(agentSelector).toBeEnabled();
  expect(deckDetailReads).toEqual([]);
  // Full production Next entry, original Web components and original DTO fixtures.
  // Project/Episode/canonical/private publication/Hook/database/model/ledger remain out of scope.
  for (const viewport of [{width:1440,height:900},{width:390,height:844}]) {
    await page.setViewportSize(viewport);
    const composer = page.locator('.ai-input-dock');
    const imageAction = page.getByRole('button', {name:'生成图片',exact:true});
    const historyTab = page.getByRole('tab', {name:'聊天历史'});
    await expect(composer).toBeVisible();
    await expect(imageAction).toBeVisible();
    await expect(page.getByRole('button', {name:'撰写或编辑',exact:true})).toBeVisible();
    await expect(page.getByRole('button', {name:'查找资料',exact:true})).toBeVisible();
    await expect(page.getByRole('tab', {name:/^Dream（/})).toBeVisible();
    // Resize starts the original 180ms sidebar padding transition. Measure the settled narrow layout.
    if (viewport.width < 768) await expect.poll(() => page.locator('.story-workspace-sidebar').evaluate(element => getComputedStyle(element).paddingTop)).toBe('0px');
    const [inputBox,actionBox,tabBox] = await Promise.all([composer.boundingBox(),imageAction.boundingBox(),historyTab.boundingBox()]);
    expect(inputBox!.y + inputBox!.height).toBeLessThanOrEqual(actionBox!.y + 1);
    expect(actionBox!.y + actionBox!.height).toBeLessThanOrEqual(tabBox!.y + 1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    if (viewport.width < 768) {
      const labels = await page.locator('.story-workspace-sidebar__nav > .story-workspace-sidebar__nav-button .story-workspace-sidebar__label').evaluateAll(elements => elements.map(element => ({label:element.textContent,bottom:element.getBoundingClientRect().bottom})));
      await testInfo.attach('narrow-navigation-bounds',{body:JSON.stringify(labels),contentType:'application/json'});
      const geometry = await page.locator('.story-workspace-layout__sidebar, .story-workspace-sidebar, .story-workspace-sidebar__nav, .story-workspace-sidebar__nav > .story-workspace-sidebar__nav-button').evaluateAll(elements => elements.map(element => {
        const rect = element.getBoundingClientRect(); const css = getComputedStyle(element);
        return {className:element.className,top:rect.top,bottom:rect.bottom,height:rect.height,boxSizing:css.boxSizing,padding:css.padding,margin:css.margin,minHeight:css.minHeight,display:css.display,flexDirection:css.flexDirection,gap:css.gap,lineHeight:css.lineHeight};
      }));
      await testInfo.attach('narrow-navigation-geometry',{body:JSON.stringify(geometry),contentType:'application/json'});
      for (const label of labels) expect(label.bottom,`navigation label ${label.label} remains inside viewport`).toBeLessThanOrEqual(viewport.height + 1);
    }
    await page.screenshot({path:testInfo.outputPath(`original-web-chat-${viewport.width}.png`)});
  }
  await page.getByRole('button', {name:'搜索',exact:true}).click();
  const searchDialog = page.getByRole('dialog', {name:'搜索历史对话'});
  await expect(searchDialog).toBeVisible();
  const searchRead = page.waitForRequest(request => {
    const url = new URL(request.url());
    return url.pathname === '/api/claude-agent/threads' && url.searchParams.get('query') === '历史内容';
  });
  await searchDialog.getByRole('textbox', {name:'搜索历史对话'}).fill('历史内容');
  const searchRequest = new URL((await searchRead).url());
  expect(searchRequest.searchParams.get('search_scope')).toBe('all');
  expect(searchRequest.searchParams.get('retrieval_mode')).toBe('fuzzy');
  await expect(searchDialog.getByRole('button', {name:historicalThread.title})).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(searchDialog).toBeHidden();
  const beforeNew = createdThreadRequests;
  await page.getByTitle('新建对话',{exact:true}).click();
  await expect(page.locator('.ai-input-dock')).toBeVisible();
  expect(createdThreadRequests).toBe(beforeNew);
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('button', { name: historicalThread.title }).click();
  await expect(page.getByRole('textbox', { name: '聊天输入' })).toBeVisible();
  const historicalAssistantTurn = page.locator('[data-chat-assistant-turn="history-completed-turn-e2e"]');
  const historicalProcessToggle = historicalAssistantTurn.locator('.chat-assistant-turn__toggle');
  await expect(historicalAssistantTurn.getByText('这是历史轮次的最终答复。')).toBeVisible();
  await expect(historicalProcessToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('历史思考链仅在展开后挂载。')).toHaveCount(0);
  await page.screenshot({ path: '../output/playwright/chat-history-process-collapsed.png' });
  await historicalProcessToggle.focus();
  await historicalProcessToggle.press('Enter');
  await expect(historicalProcessToggle).toHaveAttribute('aria-expanded', 'true');
  const historicalProcess = historicalAssistantTurn.locator('[data-turn-process="history-completed-turn-e2e"]');
  await expect(historicalProcess).toContainText('历史思考链仅在展开后挂载。');
  await expect(historicalProcess).toContainText('历史中间文本仅在展开后挂载。');
  await page.screenshot({ path: '../output/playwright/chat-history-process-expanded.png' });
  await historicalProcessToggle.press('Enter');
  await expect(historicalProcessToggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('历史思考链仅在展开后挂载。')).toHaveCount(0);
  await expect(agentSelector).toHaveCount(0);
  const historicalDeckContext = page.getByRole('button', { name: '思维模式信息' });
  await expect(historicalDeckContext).toBeVisible();
  await expect(historicalDeckContext).toContainText(dreamDeck.name);
  await expect(historicalDeckContext).not.toContainText('drama-forge');
  await historicalDeckContext.click();
  const deckMetadataDialog = page.getByRole('dialog', { name: '思维模式信息' });
  await expect(deckMetadataDialog).toContainText('drama-forge@drama-studio');
  await expect(deckMetadataDialog.getByRole('button', { name: '故事导演，当前 Agent' })).toBeDisabled();
  await deckMetadataDialog.getByRole('button', { name: '切换到 结构顾问' }).click();
  await expect(deckMetadataDialog).toHaveCount(0);
  await expect(page.getByTitle('结构顾问')).toContainText('结构顾问');
  await expect(historicalDeckContext).toContainText(dreamDeck.name);
  await historicalDeckContext.click();
  await expect(deckMetadataDialog.getByRole('button', { name: '结构顾问，当前 Agent' })).toHaveAttribute('aria-pressed', 'true');
  await expect(deckMetadataDialog).toContainText('drama-forge@drama-studio');
  await historicalDeckContext.click();
  const historicalComposer = page.getByRole('textbox', { name: '聊天输入' });
  await historicalComposer.click();
  await historicalComposer.press('/');
  const commonSkillListbox = page.getByRole('listbox', { name: '聊天指令' });
  await expect(commonSkillListbox).toBeVisible();
  await expect(commonSkillListbox.getByRole('option')).toHaveCount(6);
  await expect(commonSkillListbox.getByRole('option', { name: /\/asr\b.*Ink & Memory/ })).toBeVisible();
  await expect(commonSkillListbox.getByRole('option', { name: /\/compact\b/ })).toBeVisible();
  await page.screenshot({ path: '../output/playwright/common-skills-slash-menu.png' });
  await commonSkillListbox.getByRole('option', { name: /\/asr\b/ }).click();
  await expect(historicalComposer).toHaveText('/asr ');
  expect(historicalChatTurnBody).toBeNull();
  await historicalComposer.fill('/asr 请从结构角度继续分析。');
  await page.getByRole('button', { name: '发送消息' }).click();
  await expect.poll(() => historicalChatTurnBody).not.toBeNull();
  expect(historicalChatTurnBody).toMatchObject({
    id: HISTORICAL_THREAD_ID,
    deckId: dreamDeck.id,
    voiceId: 'dream-agent-e2e-structure',
    message: {
      role: 'user',
      parts: [{ type: 'text', text: '/asr 请从结构角度继续分析。' }],
    },
  });
  await page.screenshot({ path: '../output/playwright/chat-history-context-wide.png' });
  await page.setViewportSize({ width: 760, height: 780 });
  await expect(agentSelector).toHaveCount(0);
  await expect.poll(async () => (
    (await page.getByRole('textbox', { name: '聊天输入' }).boundingBox())?.width ?? 0
  )).toBeGreaterThan(360);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: '../output/playwright/chat-history-context-narrow.png' });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole('button', { name: '新建' }).click();
  await expect(agentSelector).toBeVisible();
  const activeDreamTab = page.getByRole('tab', { name: 'Dream（6）' });
  await expect(activeDreamTab).toBeVisible();
  await expect(page.getByText('资源连接器', { exact: true })).toHaveCount(0);
  await activeDreamTab.click();
  await expect(page.getByText('初始的雨夜故事', { exact: true })).toBeVisible();
  await expect(page.getByText('雨夜故事 Dream · Dream Agent 正在创作', { exact: true })).toBeVisible();
  await expect(page.getByText('初始状态', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('进行中', { exact: true }).first()).toBeVisible();
  const dreamScroller = page.getByRole('list', { name: '可恢复的 Dream' });
  await expect.poll(() => dreamScroller.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
  expect(await dreamScroller.evaluate((element) => getComputedStyle(element).overflowX)).toBe('auto');
  expect(await dreamScroller.evaluate((element) => getComputedStyle(element).overflowY)).toBe('hidden');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: '../output/playwright/chat-dream-list-wide.png' });
  await page.setViewportSize({ width: 760, height: 560 });
  await expect.poll(() => dreamScroller.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: '../output/playwright/chat-dream-list-narrow.png' });
  await page.setViewportSize({ width: 1440, height: 1000 });
  const activeDreamLink = page.getByRole('link', { name: /初始的雨夜故事/ });
  await expect(activeDreamLink).toHaveAttribute('href', `/story-workspace/dream?run=${RUN_ID}`);
  await activeDreamLink.click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);
  await expect.poll(() => releaseDeepLinkRead).not.toBeNull();
  releaseDeepLinkRead?.();
  releaseDeepLinkRead = null;

  await page.goto(`${WEB_BASE}/story-workspace/chat?deck=${dreamDeck.id}`);
  await expect(page.getByRole('textbox', { name: '聊天输入' })).toBeVisible();

  await page.getByRole('textbox', { name: '聊天输入' }).fill('创作一个发生在雨夜车站的克制短篇。');
  await page.getByRole('button', { name: '发送消息' }).click();
  await expect.poll(() => launchBody).not.toBeNull();
  expect(launchBody).toMatchObject({
    deckId: dreamDeck.id,
    agentId: 'dream-agent-e2e',
    goal: '创作一个发生在雨夜车站的克制短篇。',
  });
  expect(String(launchBody?.idempotencyKey)).toMatch(/^dream_/);
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);
  const dreamEditor = page.getByRole('complementary', { name: 'Dream 内容编辑器' });
  await expect(dreamEditor).toHaveAttribute('data-agent-open', 'true');
  await expect(page.getByRole('region', { name: 'Dream Agent 完整消息' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: '聊天输入' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: '../output/playwright/chat-dream-launch-workbench-open.png', fullPage: true });

  expect(unexpectedApiRequests).toEqual([]);
  await testInfo.attach('lifecycle-read-cancellations', { body: JSON.stringify({ cancelled: cancelledLifecycleReads, successful: successfulGetReads.filter(read => lifecycleReadPaths.has(read.path)) }), contentType: 'application/json' });
  for (const cancelled of cancelledLifecycleReads) expect(successfulGetReads.some(read => read.path === cancelled.path && read.order > cancelled.order), `Replacement GET ${cancelled.path}`).toBe(true);
  expect(diagnostics).toEqual([]);
});

test('Dream home reaches the final run at a narrow low-height viewport', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.route(`${WEB_BASE}/auth/session`, async (route) => route.fulfill({
    json: {
      user: { id: '314', email: 'dream-e2e@example.test', display_name: 'Dream E2E', avatar_url: null, role: 'user', created_at: null },
      csrf_token: 'a'.repeat(43),
    },
  }));
  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === '/api/me') return route.fulfill({ json: { id: 314, email: 'dream-e2e@example.test', display_name: 'Dream E2E' } });
    if (pathname === '/api/preferences') return route.fulfill({ json: { first_login_completed: true } });
    if (pathname === '/api/decks/defaults/reconcile') {
      return route.fulfill({ json: { deck_id: dreamDeck.id, reconciled: false, reason: 'refs_preserved' } });
    }
    if (pathname === '/api/decks' || pathname === '/api/decks/catalog') return route.fulfill({ json: { decks: [dreamDeck] } });
    if (pathname === '/api/story-workspace/dream-runs') return route.fulfill({ json: { runs } });
    if (pathname === '/api/sessions' || pathname === '/api/sessions/range') return route.fulfill({ json: { sessions: [] } });
    if (pathname === '/api/sessions/events') return route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
    if (pathname === '/api/pictures/range') return route.fulfill({ json: { pictures: [] } });
    if (pathname === '/api/default-voices') return route.fulfill({ json: {} });
    if (pathname === '/api/storage') return route.fulfill({ json: { type: 'unknown', supportsDirectUpload: false, isConfigured: true } });
    if (pathname === '/api/system-config') return route.fulfill({ json: { data: {} } });
    return route.fulfill({ json: {} });
  });
  await page.setViewportSize({ width: 760, height: 560 });
  await page.goto(`${WEB_BASE}/story-workspace/dream`);
  await expect(page.getByRole('heading', { name: '进行中的 Dream' })).toBeVisible();
  const layoutMain = page.locator('[data-story-workspace-region="main"]');
  await expect.poll(() => layoutMain.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);
  await page.screenshot({ path: '../output/playwright/dream-home-narrow.png' });
  await page.getByRole('link', { name: /初始的雨夜故事/ }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('link', { name: /初始的雨夜故事/ })).toBeVisible();
  expect(await layoutMain.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: '../output/playwright/dream-home-narrow-low-height.png' });
});
