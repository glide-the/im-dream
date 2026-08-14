// [Input] Authenticated root App, Story Workspace navigation, Deck Manager, and
//         deterministic production-shaped Deck/plugin API responses.
// [Output] Provider-free browser journey proving Chat-first entry, screenplay
//          defaults, legacy default-team repair, default drama-forge selection,
//          editable refs, refresh, and font.
// [Pos] Chat-first and Deck-default business E2E in frontend/e2e
// [Sync] 2026-08-14: cover default-team zero-ref repair before new-Deck behavior.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

/*
Business impact brief (technical isolated lane):

| Fact/surface | Expected impact |
| --- | --- |
| Authenticated root route | changes to /story-workspace/chat |
| Story Workspace primary navigation | changes to Decks/Dream/Chat only |
| Default user Deck + five screenplay roles | plugin ref changes from empty to drama-forge 1.0.1 |
| Newly created Deck plugin refs | changes; drama-forge 1.0.1 selected |
| Project/Episode/canonical files/.dream/Thread/model | out of scope; no request or mutation |

The browser exercises normal visible controls. Production PostgreSQL atomicity
and fail-closed plugin verification are covered by backend/tests/test_deck_defaults.py.
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
  voices: [],
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

test('login → Chat → Decks → create → default plugin → edit → refresh', async ({ page }) => {
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
  let screenplaySelectedInstallationIds: string[] = [];
  let selectedInstallationIds = [dramaInstallation.id];
  const pluginWrites: string[][] = [];
  let defaultReconcileCalls = 0;

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
        : [screenplayDeck, ...(deckCreated ? [createdDeck] : [])] } });
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
    if (pathname === `/api/decks/${createdDeck.id}`) {
      await route.fulfill({ json: createdDeck });
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
  await expect(navigation.getByRole('button')).toHaveCount(3);
  await expect(navigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
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

  await page.getByText('剧本创作团队', { exact: true }).click();
  await expect(page.getByText('Deck Editor', { exact: true })).toBeVisible();
  for (const role of ['编剧', '戏剧结构师', '人物塑造师', '对白编辑', '连续性审校']) {
    await expect(page.getByText(role, { exact: true })).toBeVisible();
  }
  const defaultDramaLabel = page.locator('label').filter({ hasText: 'drama-forge' });
  await expect(defaultDramaLabel).toContainText('v1.0.1');
  await expect(defaultDramaLabel.getByRole('checkbox')).toBeChecked();
  expect(defaultReconcileCalls).toBeGreaterThanOrEqual(1);
  expect(screenplaySelectedInstallationIds).toEqual([dramaInstallation.id]);
  await page.getByRole('button', { name: 'Close' }).click();

  await page.getByRole('button', { name: /Create New Deck|创建/ }).click();
  await expect(page.getByText('Deck Editor', { exact: true })).toBeVisible();
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
  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await page.getByText('New Deck', { exact: true }).click();
  await expect(page.locator('label').filter({ hasText: 'drama-forge' }).getByRole('checkbox')).toBeChecked();
  await expect(page.locator('label').filter({ hasText: 'story-notes' }).getByRole('checkbox')).toBeChecked();
  await expect.poll(async () => page.locator('body').evaluate((body) => getComputedStyle(body).fontFamily))
    .toContain('Microsoft YaHei');

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-default-plugin.png',
    fullPage: true,
  });
  await expect.poll(() => diagnostics).toEqual([]);
  expect(unexpectedApiRequests).toEqual([]);
});
