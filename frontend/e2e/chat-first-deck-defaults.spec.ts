// [Input] Authenticated root App, Story Workspace navigation, Deck Manager, and
//         deterministic production-shaped Deck/plugin API responses.
// [Output] Provider-free browser journey proving Chat-first entry, consumer Deck
//          handoff, creator management, default repair, plugin edits, and refresh.
// [Pos] Chat-first and Deck-default business E2E in frontend/e2e
// [Sync] 2026-08-15: freeze the complete pre-test impact matrix and cover the
//                    continuous consumer -> Chat -> creator -> refresh journey.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

/*
Business impact brief (provider-free technical lane, frozen before execution):

| Fact/surface | Expected impact |
| --- | --- |
| Login -> Chat -> Decks | visible route/navigation only |
| Consumer mode | enabled Deck/Agent selection and fresh-Chat handoff |
| Creator mode | metadata, Agent type/member, plugin, enable and publication controls |
| Default user Deck + five screenplay roles | missing ref repaired to drama-forge 1.0.1 |
| Newly created Deck | default plugin remains selected after explicit edit and refresh |
| Historical Chat | covered by chat-dream-agent-refactor; top context only, no locked selector |
| Deck revision/snapshot/workspace upgrade | capability missing; no vN or success UI may appear |
| Project/Episode/canonical/.dream/real model/ledger | out of scope; no request or mutation |

The browser exercises normal visible controls and production DTO shapes with
strict unexpected-request diagnostics. backend/tests/test_deck_defaults.py is
an isolated technical contract suite; neither lane is real-account, real-model,
or production PostgreSQL business acceptance.
*/

interface DeckFixture {
  id: string;
  name: string;
  name_zh?: string;
  name_en?: string;
  description: string;
  icon: string;
  color: string;
  is_system: boolean;
  enabled: boolean;
  published?: boolean;
  can_publish?: boolean;
  agent_type: 'chat' | 'dream';
  agent_type_revision: number;
  voice_count: number;
  voices: Array<{
    id: string;
    deck_id: string;
    name: string;
    system_prompt: string;
    icon: string;
    color: string;
    is_system: boolean;
    enabled: boolean;
  }>;
}

const screenplayDeck: DeckFixture = {
  id: 'screenplay-default-user-deck',
  name: '剧本创作团队',
  name_zh: '剧本创作团队',
  name_en: 'Screenplay Creation Team',
  description: '覆盖剧情、结构、人物、对白和连续性的剧本创作角色',
  icon: 'masks',
  color: 'purple',
  is_system: false,
  enabled: true,
  voice_count: 5,
  published: false,
  can_publish: false,
  agent_type: 'chat',
  agent_type_revision: 0,
  voices: ['编剧', '戏剧结构师', '人物塑造师', '对白编辑', '连续性审校'].map((name, index) => ({
    id: `screenplay-role-${index}`,
    deck_id: 'screenplay-default-user-deck',
    name,
    system_prompt: `${name}负责剧本创作。`,
    icon: 'masks',
    color: 'purple',
    is_system: false,
    enabled: true,
  })),
};

const createdDeck: DeckFixture = {
  id: 'created-screenplay-deck',
  name: 'New Deck',
  description: 'Describe your deck here',
  icon: 'brain',
  color: 'blue',
  is_system: false,
  enabled: true,
  voice_count: 0,
  published: false,
  can_publish: true,
  agent_type: 'chat',
  agent_type_revision: 0,
  voices: [],
};

const createdVoice = {
  id: 'created-screenplay-agent',
  deck_id: createdDeck.id,
  name: 'New Voice',
  system_prompt: 'You are a helpful assistant.',
  icon: 'brain',
  color: 'blue',
  is_system: false,
  enabled: true,
};

const dramaInstallation = {
  id: 'installation-drama-forge',
  requested_package_spec: 'drama-forge@drama-studio',
  package_name: 'drama-forge',
  marketplace: 'drama-studio',
  requested_version: null,
  resolved_version: '1.0.1',
  source_type: 'marketplace',
  artifact_digest: 'sha256:drama-forge',
  artifact_path: '/server-managed/redacted',
  claude_cli_version: '2.1.108',
  cli_git_commit_sha: null,
  manifest_json: null,
  component_inventory_json: '{}',
  compatibility_json: '{}',
  status: 'ready',
  operation_id: 'operation-drama-forge',
  error_code: null,
  error_summary: null,
  file_count: 12,
  created_at: '2026-08-14T00:00:00Z',
  updated_at: '2026-08-14T00:00:00Z',
  installed_at: '2026-08-14T00:00:00Z',
};

const secondaryInstallation = {
  ...dramaInstallation,
  id: 'installation-secondary',
  requested_package_spec: 'story-notes@ink-marketplace',
  package_name: 'story-notes',
  marketplace: 'ink-marketplace',
  resolved_version: '2.0.0',
  artifact_digest: 'sha256:story-notes',
  operation_id: 'operation-secondary',
};

test('login → consumer Deck → Chat → creator full lifecycle → refresh', async ({ page }) => {
  const diagnostics: string[] = [];
  const unexpectedApiRequests: string[] = [];
  const isKnownExternal = (url: string) => (
    url.includes('react-grab.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('fonts.gstatic.com')
  );
  page.on('console', (message) => {
    if (message.type() === 'error' && !isKnownExternal(message.text())) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const isExpectedNavigationAbort = (
      request.failure()?.errorText === 'net::ERR_ABORTED'
      && request.url().includes('/api/story-workspace/dream-runs')
    );
    if (!isKnownExternal(request.url()) && !isExpectedNavigationAbort) {
      diagnostics.push(`${request.failure()?.errorText ?? 'request failed'} ${request.url()}`);
    }
  });

  const email = 'chat-first-deck-defaults@example.test';
  const token = 'chat-first-deck-defaults-token';
  let deckCreated = false;
  let createdDeckState: DeckFixture = { ...createdDeck, voices: [] };
  let createdAgentTypeRevision = 0;
  let screenplaySelectedInstallationIds: string[] = [];
  let selectedInstallationIds = [dramaInstallation.id];
  const pluginWrites: string[][] = [];
  let defaultReconcileCalls = 0;
  const deckWrites: Array<Record<string, unknown>> = [];
  const voiceWrites: Array<Record<string, unknown>> = [];
  const agentTypeWrites: Array<Record<string, unknown>> = [];
  let publishWrites = 0;

  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const { pathname } = url;

    if (pathname === '/api/login' && request.method() === 'POST') {
      await route.fulfill({ json: { token } });
      return;
    }
    if (pathname === '/api/me') {
      await route.fulfill({ json: { id: 207, email, display_name: '剧本创作者' } });
      return;
    }
    if (pathname === '/api/preferences') {
      await route.fulfill({ json: { first_login_completed: true, timezone: 'Asia/Shanghai' } });
      return;
    }
    if (pathname === '/api/sessions') {
      await route.fulfill({ json: request.method() === 'GET' ? { sessions: [] } : { ok: true } });
      return;
    }
    if (pathname === '/api/sessions/range') {
      await route.fulfill({ json: { sessions: [] } });
      return;
    }
    if (pathname === '/api/sessions/events') {
      await route.fulfill({ contentType: 'text/event-stream', body: ': connected\n\n' });
      return;
    }
    if (pathname === '/api/pictures/range') {
      await route.fulfill({ json: { pictures: [] } });
      return;
    }
    if (pathname === '/api/default-voices') {
      await route.fulfill({ json: {} });
      return;
    }
    if (pathname === '/api/storage') {
      await route.fulfill({ json: {
        type: 'unknown', supportsDirectUpload: false, isConfigured: true,
      } });
      return;
    }
    if (pathname === '/api/system-config') {
      await route.fulfill({ json: {
        data: { im_full_access_enabled: false, workspace_enabled: false },
      } });
      return;
    }
    if (pathname === '/api/claude-agent/threads') {
      await route.fulfill({ json: { threads: [] } });
      return;
    }
    if (pathname === '/api/story-workspace/dream-runs') {
      await route.fulfill({ json: { runs: [] } });
      return;
    }
    if (pathname === '/api/decks' && request.method() === 'GET') {
      await route.fulfill({ json: { decks: url.searchParams.get('published') === 'true'
        ? []
        : [screenplayDeck, ...(deckCreated ? [createdDeckState] : [])] } });
      return;
    }
    if (pathname === '/api/decks/defaults/reconcile' && request.method() === 'POST') {
      defaultReconcileCalls += 1;
      const reconciled = screenplaySelectedInstallationIds.length === 0;
      if (reconciled) screenplaySelectedInstallationIds = [dramaInstallation.id];
      await route.fulfill({ json: {
        deck_id: screenplayDeck.id,
        reconciled,
        reason: reconciled ? 'missing_ref' : 'refs_preserved',
      } });
      return;
    }
    if (pathname === '/api/decks' && request.method() === 'POST') {
      deckCreated = true;
      await route.fulfill({ json: { deck_id: createdDeck.id } });
      return;
    }
    if (pathname === `/api/decks/${screenplayDeck.id}`) {
      await route.fulfill({ json: screenplayDeck });
      return;
    }
    if (
      pathname === `/api/decks/${screenplayDeck.id}/claude-plugins`
      && request.method() === 'GET'
    ) {
      await route.fulfill({ json: {
        deck_id: screenplayDeck.id,
        refs: screenplaySelectedInstallationIds.map((installationId, orderIndex) => ({
          deck_id: screenplayDeck.id,
          plugin_installation_id: installationId,
          package_spec: 'drama-forge@drama-studio',
          resolved_version: dramaInstallation.resolved_version,
          artifact_digest: dramaInstallation.artifact_digest,
          enabled: 1,
          order_index: orderIndex,
        })),
      } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}` && request.method() === 'GET') {
      await route.fulfill({ json: createdDeckState });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}` && request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>;
      deckWrites.push(body);
      createdDeckState = { ...createdDeckState, ...body } as DeckFixture;
      await route.fulfill({ json: { success: true } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}/publish` && request.method() === 'POST') {
      publishWrites += 1;
      createdDeckState = { ...createdDeckState, published: !createdDeckState.published };
      await route.fulfill({ json: { success: true, published: createdDeckState.published } });
      return;
    }
    if (pathname === `/api/voice-decks/${createdDeck.id}/agent-type` && request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>;
      agentTypeWrites.push(body);
      createdAgentTypeRevision += 1;
      createdDeckState = {
        ...createdDeckState,
        agent_type: body.agent_type as 'chat' | 'dream',
        agent_type_revision: createdAgentTypeRevision,
      };
      await route.fulfill({ json: {
        deck_id: createdDeck.id,
        agent_type: createdDeckState.agent_type,
        binding_revision: createdAgentTypeRevision,
      } });
      return;
    }
    if (pathname === '/api/voices' && request.method() === 'POST') {
      createdDeckState = {
        ...createdDeckState,
        voice_count: 1,
        voices: [{ ...createdVoice }],
      };
      await route.fulfill({ json: { voice_id: createdVoice.id } });
      return;
    }
    if (pathname === `/api/voices/${createdVoice.id}` && request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>;
      voiceWrites.push(body);
      createdDeckState = {
        ...createdDeckState,
        voices: createdDeckState.voices.map((voice) => (
          voice.id === createdVoice.id ? { ...voice, ...body } : voice
        )),
      };
      await route.fulfill({ json: { success: true } });
      return;
    }
    if (pathname === '/api/claude-plugins/installations') {
      await route.fulfill({ json: { installations: [dramaInstallation, secondaryInstallation] } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}/claude-plugins` && request.method() === 'GET') {
      await route.fulfill({ json: {
        deck_id: createdDeck.id,
        refs: selectedInstallationIds.map((installationId, orderIndex) => {
          const installation = installationId === dramaInstallation.id
            ? dramaInstallation
            : secondaryInstallation;
          return {
            deck_id: createdDeck.id,
            plugin_installation_id: installation.id,
            package_spec: `${installation.package_name}@${installation.marketplace}`,
            resolved_version: installation.resolved_version,
            artifact_digest: installation.artifact_digest,
            enabled: 1,
            order_index: orderIndex,
          };
        }),
      } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}/claude-plugins` && request.method() === 'PUT') {
      const body = request.postDataJSON() as {
        refs: Array<{ plugin_installation_id: string }>;
      };
      selectedInstallationIds = body.refs.map((ref) => ref.plugin_installation_id);
      pluginWrites.push([...selectedInstallationIds]);
      await route.fulfill({ json: { deck_id: createdDeck.id, refs: body.refs } });
      return;
    }

    unexpectedApiRequests.push(`${request.method()} ${pathname}`);
    await route.fulfill({ status: 404, json: { detail: 'Unexpected mocked request' } });
  });

  await page.goto(WEB_BASE);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill('chat-first-deck-defaults');
  await page.getByRole('button', { name: 'Login', exact: true }).click();

  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  const navigation = page.getByRole('navigation', { name: 'Story Workspace 导航' });
  await expect(navigation.getByRole('button')).toHaveCount(4);
  await expect(navigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
  await expect(navigation.getByRole('button', { name: /More|更多/ })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('textbox', { name: 'Chat input' })).toBeVisible();

  await navigation.getByRole('button', { name: 'Decks' }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  await expect(navigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
  await page.goForward();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await expect(page.getByText('剧本创作团队', { exact: true })).toBeVisible();
  await expect(page.getByText('内省卡组', { exact: true })).toHaveCount(0);
  await expect(page.getByText('学者卡组', { exact: true })).toHaveCount(0);
  await expect(page.getByText('哲学卡组', { exact: true })).toHaveCount(0);

  const useTab = page.getByRole('tab', { name: /Use Decks|使用 Deck/ });
  await expect(useTab).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('button', { name: /Create New Deck|新建卡组/ })).toHaveCount(0);
  const useCard = page.locator(
    `[data-deck-card-kind="use"][data-deck-card-id="${screenplayDeck.id}"]`,
  );
  await expect(useCard.getByLabel(/Choose an Agent from 剧本创作团队|选择 剧本创作团队 中的 Agent/)).toHaveValue('screenplay-role-0');
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-use-mode-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 640, height: 780 });
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  expect((await useTab.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-use-mode-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1200, height: 760 });
  await useCard.getByLabel(/Choose an Agent from 剧本创作团队|选择 剧本创作团队 中的 Agent/)
    .selectOption('screenplay-role-3');
  await useCard.getByRole('button', { name: /Use in Chat|在 Chat 中使用/ }).click();
  await expect(page).toHaveURL(new RegExp(`/story-workspace/chat\\?deck=${screenplayDeck.id}&agent=screenplay-role-3`));
  await expect(page.getByRole('button', { name: /为本次对话选择一个 Agent|Select an Agent|Choose an Agent/ }))
    .toContainText('对白编辑');
  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);

  await page.getByRole('tab', { name: /Create Decks|创作 Deck/ }).click();
  await expect(page.getByRole('tab', { name: /Create Decks|创作 Deck/ })).toHaveAttribute('aria-selected', 'true');

  await page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${screenplayDeck.id}"]`,
  ).getByRole('button', { name: /Edit|编辑/ }).click();
  await expect(page.getByText('Deck Editor', { exact: true })).toBeVisible();
  for (const role of ['编剧', '戏剧结构师', '人物塑造师', '对白编辑', '连续性审校']) {
    await expect(page.getByText(role, { exact: true }).first()).toBeVisible();
  }
  const defaultDramaLabel = page.locator('label').filter({ hasText: 'drama-forge' });
  await expect(defaultDramaLabel).toContainText('v1.0.1');
  await expect(defaultDramaLabel.getByRole('checkbox')).toBeChecked();
  expect(defaultReconcileCalls).toBeGreaterThanOrEqual(1);
  expect(screenplaySelectedInstallationIds).toEqual([dramaInstallation.id]);
  await page.getByRole('button', { name: 'Close' }).click();

  await page.getByRole('button', { name: /Create New Deck|创建/ }).click();
  await expect(page.getByRole('dialog', { name: 'Deck Editor' })).toBeVisible();
  await expect(page.getByRole('button', { name: /版本记录|提交新版本/ })).toHaveCount(0);
  await expect(page.getByText('修改未提交', { exact: true })).toHaveCount(0);

  await page.getByLabel('Deck Name').fill('雨夜剧作团队');
  await page.getByLabel('Deck Description').click();
  await expect.poll(() => deckWrites.some((write) => write.name === '雨夜剧作团队')).toBe(true);
  await page.getByLabel('Deck Description').fill('用于雨夜剧本创作的协作工作台');
  await page.getByText('Agent 类型', { exact: true }).click();
  await expect.poll(() => deckWrites.some(
    (write) => write.description === '用于雨夜剧本创作的协作工作台',
  )).toBe(true);

  await page.getByRole('radio', { name: /Dream Agent/ }).check();
  await expect.poll(() => agentTypeWrites).toEqual([{
    agent_type: 'dream',
    expected_binding_revision: 0,
  }]);

  await page.getByRole('button', { name: '+ Add' }).click();
  await expect(page.getByLabel('Agent Name')).toHaveValue('New Voice');
  await page.getByLabel('Agent Name').fill('雨夜结构顾问');
  await page.getByLabel('Agent Prompt').click();
  await expect.poll(() => voiceWrites.some((write) => write.name === '雨夜结构顾问')).toBe(true);
  await page.getByLabel('Agent Prompt').fill('检查雨夜剧本的冲突、节拍和场景连续性。');
  await page.getByText('Agent 类型', { exact: true }).click();
  await expect.poll(() => voiceWrites.some(
    (write) => write.system_prompt === '检查雨夜剧本的冲突、节拍和场景连续性。',
  )).toBe(true);

  await page.getByLabel('Toggle 雨夜结构顾问').click();
  await expect.poll(() => createdDeckState.voices[0]?.enabled).toBe(false);
  await expect(page.getByLabel('Toggle 雨夜结构顾问')).not.toBeChecked();
  await page.getByLabel('Toggle 雨夜结构顾问').click();
  await expect.poll(() => createdDeckState.voices[0]?.enabled).toBe(true);
  await expect(page.getByLabel('Toggle 雨夜结构顾问')).toBeChecked();

  const dramaLabel = page.locator('label').filter({ hasText: 'drama-forge' });
  await expect(dramaLabel).toContainText('v1.0.1');
  await expect(dramaLabel.getByRole('checkbox')).toBeChecked();

  const secondaryLabel = page.locator('label').filter({ hasText: 'story-notes' });
  await expect(secondaryLabel.getByRole('checkbox')).toBeEnabled();
  await secondaryLabel.getByRole('checkbox').check();
  await page.getByRole('button', { name: '保存插件选择' }).click();
  await expect(page.getByText('已保存 ✓')).toBeVisible();
  expect(pluginWrites).toEqual([[dramaInstallation.id, secondaryInstallation.id]]);

  await page.getByRole('button', { name: 'Close' }).click();
  let createdCreatorCard = page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${createdDeck.id}"]`,
  );
  await expect(createdCreatorCard).toContainText('雨夜剧作团队');
  await createdCreatorCard.getByRole('switch').click();
  await expect.poll(() => createdDeckState.enabled).toBe(false);
  await page.getByRole('tab', { name: /Use Decks|使用 Deck/ }).click();
  await expect(page.locator(
    `[data-deck-card-kind="use"][data-deck-card-id="${createdDeck.id}"]`,
  )).toHaveCount(0);
  await page.getByRole('tab', { name: /Create Decks|创作 Deck/ }).click();
  createdCreatorCard = page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${createdDeck.id}"]`,
  );
  await createdCreatorCard.getByRole('switch').click();
  await expect.poll(() => createdDeckState.enabled).toBe(true);

  await createdCreatorCard.getByRole('button', { name: /Publish to Community|发布到社区/ }).click();
  await expect(page.getByRole('dialog', { name: /Publish Deck Warning|发布提醒/ })).toBeVisible();
  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByRole('button', { name: /Publish Anyway|仍要发布/ }).click();
  await expect(page.getByRole('heading', { name: /My Published Decks \(1\)|我发布的卡组（1）/ })).toBeVisible();
  expect(publishWrites).toBe(1);
  page.once('dialog', async (dialog) => dialog.accept());
  await page.locator(
    `[data-deck-card-kind="published-by-me"][data-deck-card-id="${createdDeck.id}"]`,
  ).getByRole('button', { name: /Unpublish|取消发布/ }).click();
  await expect(page.getByRole('heading', { name: /My Published Decks \(0\)|我发布的卡组（0）/ })).toBeVisible();
  expect(publishWrites).toBe(2);

  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await expect(page.getByRole('tab', { name: /Use Decks|使用 Deck/ })).toHaveAttribute('aria-selected', 'true');
  const refreshedUseCard = page.locator(
    `[data-deck-card-kind="use"][data-deck-card-id="${createdDeck.id}"]`,
  );
  await expect(refreshedUseCard).toContainText('雨夜剧作团队');
  await expect(refreshedUseCard).toContainText('Dream Agent');
  await expect(refreshedUseCard.getByLabel(/雨夜剧作团队/)).toHaveValue(createdVoice.id);
  await refreshedUseCard.getByRole('button', { name: /Use in Chat|在 Chat 中使用/ }).click();
  await expect(page).toHaveURL(new RegExp(
    `/story-workspace/chat\\?deck=${createdDeck.id}&agent=${createdVoice.id}`,
  ));
  await expect(page.getByRole('button', { name: /为本次对话选择一个 Agent|Select an Agent|Choose an Agent/ }))
    .toContainText('雨夜结构顾问');
  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await page.getByRole('tab', { name: /Create Decks|创作 Deck/ }).click();
  await page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${createdDeck.id}"]`,
  ).getByRole('button', { name: /Edit|编辑/ }).click();
  await expect(page.getByLabel('Deck Name')).toHaveValue('雨夜剧作团队');
  await expect(page.getByLabel('Deck Description')).toHaveValue('用于雨夜剧本创作的协作工作台');
  await expect(page.getByRole('radio', { name: /Dream Agent/ })).toBeChecked();
  await expect(page.getByLabel('Agent Name')).toHaveValue('雨夜结构顾问');
  await expect(page.getByLabel('Agent Prompt')).toHaveValue('检查雨夜剧本的冲突、节拍和场景连续性。');
  await expect(page.locator('label').filter({ hasText: 'drama-forge' }).getByRole('checkbox')).toBeChecked();
  await expect(page.locator('label').filter({ hasText: 'story-notes' }).getByRole('checkbox')).toBeChecked();
  await expect.poll(async () => page.locator('body').evaluate((body) => getComputedStyle(body).fontFamily))
    .toContain('Microsoft YaHei');

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-default-plugin.png',
    fullPage: true,
  });
  await expect.poll(() => diagnostics).toEqual([]);
  expect(deckWrites).toEqual(expect.arrayContaining([
    { name: '雨夜剧作团队' },
    { description: '用于雨夜剧本创作的协作工作台' },
    { enabled: false },
    { enabled: true },
  ]));
  expect(voiceWrites).toEqual(expect.arrayContaining([
    { name: '雨夜结构顾问' },
    { system_prompt: '检查雨夜剧本的冲突、节拍和场景连续性。' },
    { enabled: false },
    { enabled: true },
  ]));
  expect(unexpectedApiRequests).toEqual([]);
});
