// [Input] Authenticated root App, Story Workspace navigation, Deck Manager, and
//         deterministic production-shaped Deck CRUD responses.
// [Output] Provider-free browser journey proving Chat-first entry, consumer Deck
//          responsive list management, pagination, resilient refresh, create-then-full-maintenance,
//          Workflow/market removal, Deck content vN iteration, and secondary runtime versions.
// [Pos] Chat-first and Deck-default business E2E in frontend/e2e
// [Sync] 2026-08-17: require published-clean enabled Decks on the home, visible system
//                    markers, and full draft/unpublished inventory only in Settings / Work.
// [Sync] 2026-08-17: cover Work More → related Chat previews and production thread deletion.
// [Sync] 2026-08-17: verify Settings and Work render one locale at a time and switch live.
// [Sync] 2026-08-16: restore pre-01a00576 Agent/Prompt/plugin-ref maintenance and
//                    CozeLoop-inspired durable draft/explicit content commits inside the popup.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chromium' });

/*
Business impact brief (provider-free technical lane, frozen before execution):

| Fact/surface | Expected impact |
| --- | --- |
| Login -> Chat -> Decks | visible route/navigation only |
| Consumer mode | enabled Deck/Agent selection and fresh-Chat handoff |
| Deck launch | stable-order enabled projection, fourteen-item cap, trailing Settings action |
| Settings / Work | one Settings category; Deck/resource/plugin tabs; search/filter/refresh/pagination and enable controls |
| Default user Deck + five screenplay roles | missing ref repaired to drama-forge 1.0.1 |
| Newly created Deck | original default Deck is written first, then its edit popup opens |
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
  agent_type: 'chat' | 'dream';
  agent_type_revision: number;
  deck_plugin_id?: string;
  deck_plugin_version?: string;
  deck_version_capability?: boolean;
  deck_version?: number | null;
  draft_revision?: number;
  deck_version_dirty?: boolean;
  deck_version_status?: 'unpublished' | 'draft' | 'published';
  next_deck_version?: number;
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
  updated_at?: string;
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
  agent_type: 'dream',
  agent_type_revision: 1,
  deck_plugin_id: 'ink.deck.drama-forge',
  deck_plugin_version: '1.0.1',
  deck_version_capability: true,
  deck_version: 2,
  draft_revision: 5,
  deck_version_dirty: false,
  deck_version_status: 'published',
  next_deck_version: 3,
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
  name: '',
  description: '',
  icon: '',
  color: '',
  is_system: false,
  enabled: true,
  voice_count: 0,
  agent_type: 'chat',
  agent_type_revision: 0,
  deck_version_capability: true,
  deck_version: null,
  draft_revision: 1,
  deck_version_dirty: true,
  deck_version_status: 'unpublished',
  next_deck_version: 1,
  voices: [],
};

const fillerDecks: DeckFixture[] = Array.from({ length: 16 }, (_, index) => ({
  ...createdDeck,
  id: `managed-deck-${index + 1}`,
  name: `管理 Deck ${index + 1}`,
  is_system: index === 0,
  enabled: index !== 15,
  description: `分页验证 ${index + 1}`,
  icon: 'brain',
  color: 'blue',
  deck_version: index < 13 || index === 15 ? 1 : index === 14 ? 2 : null,
  deck_version_dirty: index === 13 || index === 14,
  deck_version_status: index < 13 || index === 15 ? 'published' : index === 14 ? 'draft' : 'unpublished',
  next_deck_version: index < 13 || index === 15 ? 2 : index === 14 ? 3 : 1,
  updated_at: `2026-08-${String(index + 1).padStart(2, '0')}T00:00:00Z`,
}));

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

test('login → Deck list → create → Agent/Prompt/plugin maintenance → Chat → reopen', async ({ page }) => {
  const diagnostics: string[] = [];
  const unexpectedApiRequests: string[] = [];
  const expectedHttpFailureDiagnostics: string[] = [];
  const expectedHttpFailures = new Map<number, number>();
  const isKnownExternal = (url: string) => (
    url.includes('react-grab.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('fonts.gstatic.com')
  );
  page.on('console', (message) => {
    if (message.type() === 'error' && !isKnownExternal(message.text())) {
      const status = Number(message.text().match(/status of (\d+)/)?.[1]);
      const remaining = expectedHttpFailures.get(status) ?? 0;
      if (remaining > 0) {
        expectedHttpFailures.set(status, remaining - 1);
        expectedHttpFailureDiagnostics.push(message.text());
        return;
      }
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
  const createWrites: Array<Record<string, unknown>> = [];
  const voiceWrites: Array<Record<string, unknown>> = [];
  const voiceDeletes: string[] = [];
  const agentTypeWrites: Array<Record<string, unknown>> = [];
  const versionWrites: Array<Record<string, unknown>> = [];
  const contentPreviewWrites: Array<Record<string, unknown>> = [];
  const contentCommitWrites: Array<Record<string, unknown>> = [];
  const screenplayContentVersions = [
    { version: 2, base_version: 1, source_draft_revision: 5, description: '调整 Agents', content_hash: `sha256:${'b'.repeat(64)}`, created_by: 207, created_at: '2026-08-15T10:00:00Z', runtime_plugin_version: '1.0.1' },
    { version: 1, base_version: null, source_draft_revision: 2, description: '首次提交', content_hash: `sha256:${'a'.repeat(64)}`, created_by: 207, created_at: '2026-08-14T10:00:00Z', runtime_plugin_version: '1.0.1' },
  ];
  const createdContentVersions: typeof screenplayContentVersions = [];
  const createdVersionHistory: Array<{
    deck_plugin_binding_id: string;
    deck_plugin_id: string;
    deck_plugin_version: string;
    binding_revision: number;
    status: 'active' | 'stale';
    applied_to: 'next_run';
    created_at: string;
    updated_at: string;
  }> = [];
  let deckListReads = 0;
  let failNextDeckRead = false;
  let failNextDeckUpdate = false;
  let failNextRelatedThreadRead = false;
  let relatedThreads = [
    {
      id: 'thread-screenplay-one',
      title: '雨夜开场讨论',
      deck_id: screenplayDeck.id,
      voice_id: screenplayDeck.voices[0].id,
      created_at: '2026-08-15T08:00:00Z',
      updated_at: '2026-08-17T08:00:00Z',
    },
    {
      id: 'thread-screenplay-two',
      title: '第二幕人物关系',
      deck_id: screenplayDeck.id,
      voice_id: screenplayDeck.voices[2].id,
      created_at: '2026-08-14T08:00:00Z',
      updated_at: '2026-08-16T08:00:00Z',
    },
  ];
  const relatedThreadDeletes: string[] = [];

  const advanceCreatedDraft = () => {
    createdDeckState = {
      ...createdDeckState,
      draft_revision: (createdDeckState.draft_revision ?? 1) + 1,
      deck_version_dirty: true,
      deck_version_status: createdDeckState.deck_version ? 'draft' : 'unpublished',
      next_deck_version: (createdDeckState.deck_version ?? 0) + 1,
    };
  };

  const contentState = (deck: DeckFixture) => ({
    deck_id: deck.id,
    draft_revision: deck.draft_revision ?? 1,
    latest_version: deck.deck_version ?? null,
    published_draft_revision: deck.deck_version_dirty ? Math.max(0, (deck.draft_revision ?? 1) - 1) : (deck.draft_revision ?? 1),
    dirty: deck.deck_version_dirty ?? true,
    status: deck.deck_version_status ?? 'unpublished',
    next_version: deck.next_deck_version ?? ((deck.deck_version ?? 0) + 1),
  });

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
    if (pathname === '/api/claude-agent/threads' && request.method() === 'GET') {
      if (url.searchParams.has('deck_id') && failNextRelatedThreadRead) {
        failNextRelatedThreadRead = false;
        expectedHttpFailures.set(503, (expectedHttpFailures.get(503) ?? 0) + 1);
        await route.fulfill({ status: 503, json: { detail: 'Related conversations temporarily unavailable' } });
        return;
      }
      await route.fulfill({ json: {
        threads: url.searchParams.get('deck_id') === screenplayDeck.id ? relatedThreads : [],
      } });
      return;
    }
    if (pathname === '/api/claude-agent/threads' && request.method() === 'POST') {
      await route.fulfill({ json: { thread_id: 'thread-created-by-chat' } });
      return;
    }
    if (pathname.startsWith('/api/claude-agent/threads/') && request.method() === 'DELETE') {
      const threadId = decodeURIComponent(pathname.split('/').at(-1) ?? '');
      relatedThreadDeletes.push(threadId);
      relatedThreads = relatedThreads.filter((thread) => thread.id !== threadId);
      await route.fulfill({ json: { ok: true } });
      return;
    }
    if (pathname === '/api/story-workspace/dream-runs') {
      await route.fulfill({ json: { runs: [] } });
      return;
    }
    if (pathname === '/api/decks' && request.method() === 'GET') {
      deckListReads += 1;
      if (failNextDeckRead) {
        failNextDeckRead = false;
        expectedHttpFailures.set(503, (expectedHttpFailures.get(503) ?? 0) + 1);
        await route.fulfill({ status: 503, json: { detail: 'Deck refresh temporarily unavailable' } });
        return;
      }
      await route.fulfill({ json: { decks: url.searchParams.get('published') === 'true'
        ? []
        : [screenplayDeck, ...fillerDecks, ...(deckCreated ? [createdDeckState] : [])] } });
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
      const body = request.postDataJSON() as Record<string, unknown>;
      createWrites.push(body);
      deckCreated = true;
      createdDeckState = { ...createdDeckState, ...body } as DeckFixture;
      await route.fulfill({ json: { deck_id: createdDeck.id } });
      return;
    }
    if (pathname === `/api/decks/${screenplayDeck.id}`) {
      await route.fulfill({ json: screenplayDeck });
      return;
    }
    const fillerDeck = fillerDecks.find((deck) => pathname === `/api/decks/${deck.id}`);
    if (fillerDeck && request.method() === 'GET') {
      await route.fulfill({ json: fillerDeck });
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
    const versionDeck = pathname.includes(screenplayDeck.id) ? screenplayDeck : createdDeckState;
    if (pathname === `/api/decks/${versionDeck.id}/version-state` && request.method() === 'GET') {
      await route.fulfill({ json: contentState(versionDeck) });
      return;
    }
    if (pathname === `/api/decks/${versionDeck.id}/versions` && request.method() === 'GET') {
      await route.fulfill({ json: {
        deck_id: versionDeck.id,
        current: contentState(versionDeck),
        versions: versionDeck.id === screenplayDeck.id ? screenplayContentVersions : createdContentVersions,
      } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}/versions/preview` && request.method() === 'POST') {
      const body = request.postDataJSON() as Record<string, unknown>;
      contentPreviewWrites.push(body);
      await route.fulfill({ json: {
        ...contentState(createdDeckState),
        target_version: (createdDeckState.deck_version ?? 0) + 1,
        changes: [{ scope: 'deck', change_type: createdDeckState.deck_version ? 'modified' : 'added', label: 'Deck 基础信息', fields: ['name', 'description'] }],
        impact: ['历史 Thread 不会自动升级。'],
      } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}/versions` && request.method() === 'POST') {
      const body = request.postDataJSON() as Record<string, unknown>;
      contentCommitWrites.push(body);
      const target = (createdDeckState.deck_version ?? 0) + 1;
      const summary = {
        version: target,
        base_version: createdDeckState.deck_version ?? null,
        source_draft_revision: createdDeckState.draft_revision ?? 1,
        description: (body.description as string | null) ?? null,
        content_hash: `sha256:${String(target).repeat(64).slice(0, 64)}`,
        created_by: 207,
        created_at: `2026-08-16T10:${String(target).padStart(2, '0')}:00Z`,
        runtime_plugin_version: createdDeckState.deck_plugin_version ?? null,
      };
      createdContentVersions.unshift(summary);
      createdDeckState = {
        ...createdDeckState,
        deck_version: target,
        deck_version_dirty: false,
        deck_version_status: 'published',
        next_deck_version: target + 1,
      };
      await route.fulfill({ json: { deck_id: createdDeck.id, version: summary, state: contentState(createdDeckState) } });
      return;
    }
    if (pathname === `/api/decks/${createdDeck.id}` && request.method() === 'PUT') {
      const body = request.postDataJSON() as Record<string, unknown>;
      if (failNextDeckUpdate) {
        failNextDeckUpdate = false;
        expectedHttpFailures.set(409, (expectedHttpFailures.get(409) ?? 0) + 1);
        await route.fulfill({ status: 409, json: { detail: 'Deck changed concurrently' } });
        return;
      }
      deckWrites.push(body);
      createdDeckState = { ...createdDeckState, ...body } as DeckFixture;
      advanceCreatedDraft();
      await route.fulfill({ json: { success: true } });
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
        deck_plugin_id: 'ink.deck.drama-forge',
        deck_plugin_version: '1.0.1',
      };
      advanceCreatedDraft();
      createdVersionHistory.unshift({
        deck_plugin_binding_id: 'dpb_11111111111111111111111111111111',
        deck_plugin_id: 'ink.deck.drama-forge',
        deck_plugin_version: '1.0.1',
        binding_revision: createdAgentTypeRevision,
        status: 'active',
        applied_to: 'next_run',
        created_at: '2026-08-16T10:00:00Z',
        updated_at: '2026-08-16T10:00:00Z',
      });
      await route.fulfill({ json: {
        deck_id: createdDeck.id,
        agent_type: createdDeckState.agent_type,
        binding_revision: createdAgentTypeRevision,
      } });
      return;
    }
    const runtimeDeck = pathname.includes(screenplayDeck.id) ? screenplayDeck : createdDeckState;
    const runtimeDeckId = runtimeDeck.id;
    if (
      pathname === `/api/voice-decks/${runtimeDeckId}/plugin-options`
      && request.method() === 'GET'
    ) {
      await route.fulfill({ json: {
        deck_id: runtimeDeckId,
        applied_to: 'next_run',
        options: ['1.0.1', '1.1.0'].map((version) => ({
          display_name: 'Drama Forge',
          deck_plugin_id: 'ink.deck.drama-forge',
          deck_plugin_version: version,
          release_status: 'published',
          installation_status: 'ready',
          compatibility: 'compatible',
          runtime_readiness: 'ready',
          selectable: true,
          reason_code: null,
          recovery: null,
          capability_summary: ['story.result.produce', 'workspace.files.read'],
        })),
      } });
      return;
    }
    if (
      pathname === `/api/voice-decks/${runtimeDeckId}/plugin-binding/history`
      && request.method() === 'GET'
    ) {
      const entries = runtimeDeckId === createdDeck.id ? createdVersionHistory : [{
        deck_plugin_binding_id: 'dpb_22222222222222222222222222222222',
        deck_plugin_id: 'ink.deck.drama-forge',
        deck_plugin_version: '1.0.1',
        binding_revision: 1,
        status: 'active',
        applied_to: 'next_run',
        created_at: '2026-08-15T10:00:00Z',
        updated_at: '2026-08-15T10:00:00Z',
      }];
      await route.fulfill({ json: {
        deck_id: runtimeDeckId,
        current_binding_revision: runtimeDeck.agent_type_revision,
        entries,
      } });
      return;
    }
    if (
      pathname === `/api/voice-decks/${runtimeDeckId}/plugin-binding`
      && request.method() === 'GET'
    ) {
      const version = runtimeDeck.deck_plugin_version;
      await route.fulfill({ json: {
        deck_id: runtimeDeckId,
        binding_revision: runtimeDeck.agent_type_revision,
        applied_to: 'next_run',
        binding: version ? {
          deck_plugin_binding_id: runtimeDeckId === createdDeck.id
            ? `dpb_${String(runtimeDeck.agent_type_revision).padStart(32, '1')}`
            : 'dpb_22222222222222222222222222222222',
          deck_id: runtimeDeckId,
          deck_plugin_id: 'ink.deck.drama-forge',
          deck_plugin_version: version,
          binding_revision: runtimeDeck.agent_type_revision,
          status: 'active',
          applied_to: 'next_run',
          selection_validation_summary: {
            release_status: 'published', installation_status: 'ready',
            compatibility: 'compatible', runtime_readiness: 'ready', selectable: true,
            reason_code: null, recovery: null,
            capability_summary: ['story.result.produce', 'workspace.files.read'],
          },
        } : null,
      } });
      return;
    }
    if (
      pathname === `/api/voice-decks/${createdDeck.id}/plugin-binding`
      && request.method() === 'PUT'
    ) {
      const body = request.postDataJSON() as Record<string, unknown>;
      versionWrites.push(body);
      createdVersionHistory.forEach((entry) => { entry.status = 'stale'; });
      createdAgentTypeRevision += 1;
      createdDeckState = {
        ...createdDeckState,
        deck_plugin_id: body.deck_plugin_id as string,
        deck_plugin_version: body.deck_plugin_version as string,
        agent_type_revision: createdAgentTypeRevision,
      };
      advanceCreatedDraft();
      const nextEntry = {
        deck_plugin_binding_id: 'dpb_33333333333333333333333333333333',
        deck_plugin_id: body.deck_plugin_id as string,
        deck_plugin_version: body.deck_plugin_version as string,
        binding_revision: createdAgentTypeRevision,
        status: 'active' as const,
        applied_to: 'next_run' as const,
        created_at: '2026-08-16T10:10:00Z',
        updated_at: '2026-08-16T10:10:00Z',
      };
      createdVersionHistory.unshift(nextEntry);
      await route.fulfill({ json: {
        ...nextEntry,
        deck_id: createdDeck.id,
        selection_validation_summary: {
          release_status: 'published', installation_status: 'ready',
          compatibility: 'compatible', runtime_readiness: 'ready', selectable: true,
          reason_code: null, recovery: null,
          capability_summary: ['story.result.produce', 'workspace.files.read'],
        },
      } });
      return;
    }
    if (pathname === '/api/voices' && request.method() === 'POST') {
      createdDeckState = {
        ...createdDeckState,
        voice_count: 1,
        voices: [{ ...createdVoice }],
      };
      advanceCreatedDraft();
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
      advanceCreatedDraft();
      await route.fulfill({ json: { success: true } });
      return;
    }
    if (pathname === `/api/voices/${createdVoice.id}` && request.method() === 'DELETE') {
      voiceDeletes.push(createdVoice.id);
      createdDeckState = {
        ...createdDeckState,
        voice_count: 0,
        voices: [],
      };
      advanceCreatedDraft();
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
      advanceCreatedDraft();
      await route.fulfill({ json: { deck_id: createdDeck.id, refs: body.refs } });
      return;
    }

    if (pathname === '/api/connectors' && request.method() === 'GET') {
      await route.fulfill({ json: [] });
      return;
    }

    if (pathname === '/api/claude-plugins/installations' && request.method() === 'GET') {
      await route.fulfill({ json: { installations: [] } });
      return;
    }

    if (pathname === '/api/claude-plugins/operations' && request.method() === 'GET') {
      await route.fulfill({ json: { operations: [] } });
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
  const chatAgentSelector = page.getByRole('button', {
    name: /为本次对话选择一个 Agent|Select an Agent|Choose an Agent/,
  });
  await chatAgentSelector.click();
  await page.getByRole('option', { name: '对白编辑' }).click();
  await expect(chatAgentSelector).toContainText('对白编辑');

  await navigation.getByRole('button', { name: 'Decks' }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await page.goBack();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/chat`);
  await expect(navigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
  await page.goForward();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/decks`);
  await expect(page.getByRole('button', { name: /Open 剧本创作团队|打开 剧本创作团队/ })).toBeVisible();
  await expect(page.getByRole('tab', { name: /Use Decks|Create Decks|使用 Deck|创作 Deck/ })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: /Voice Decks|声线卡组|My Decks|我的卡组/ })).toHaveCount(0);
  const deckLauncher = page.locator('[data-deck-manager-launcher]');
  await expect(deckLauncher.getByRole('heading', { name: /^Decks?$|^Deck$/ })).toBeVisible();
  await expect(deckLauncher.getByText(/Open an enabled published Deck|打开已启用且已发布的 Deck/)).toBeVisible();
  await expect(deckLauncher.locator('.deck-manager-enabled__strip')).toBeVisible();
  const enabledShortcutList = deckLauncher.locator('.deck-manager-enabled__strip');
  await expect(enabledShortcutList.getByRole('listitem')).toHaveCount(14);
  await expect(enabledShortcutList.locator('.deck-manager-enabled__item')).toHaveCount(14);
  await expect(enabledShortcutList.locator('.deck-manager-enabled__item--system')).toHaveCount(1);
  await expect(enabledShortcutList.locator('.deck-manager-enabled__system-marker')).toHaveCount(1);
  const wideShortcutRects = await enabledShortcutList.locator('.deck-manager-enabled__item').evaluateAll(
    (items) => items.map((item) => {
      const rect = item.getBoundingClientRect();
      return { height: rect.height, top: rect.top, width: rect.width };
    }),
  );
  expect(wideShortcutRects.every(({ height, width }) => Math.abs(height - width) <= 1 && width === 44)).toBe(true);
  expect(new Set(wideShortcutRects.map(({ top }) => Math.round(top))).size).toBe(1);
  await expect(enabledShortcutList.getByRole('button', { name: /Open Deck settings|打开 Deck 设置/ })).toHaveCount(0);
  await expect(deckLauncher.locator('.deck-manager-section-heading').getByRole('button', { name: /Open Deck settings|打开 Deck 设置/ })).toBeVisible();
  await expect(deckLauncher.getByText(/14\s*\/\s*14/)).toHaveCount(0);
  await expect(deckLauncher.getByRole('switch')).toHaveCount(0);
  await expect(deckLauncher.getByRole('searchbox', { name: /Search available Decks|搜索正式可用的 Deck/ })).toBeVisible();
  await expect(deckLauncher.getByRole('list', { name: /Available Deck list|正式可用 Deck 列表/ })).toBeVisible();
  await expect(deckLauncher.getByRole('list', { name: /Available Deck list|正式可用 Deck 列表/ }).locator(':scope > li')).toHaveCount(14);
  await expect(deckLauncher.locator('.deck-manager-launch-card--system .deck-manager-chip')).toHaveText(/System|系统/);
  await expect(deckLauncher.getByText(/草稿\s*r/)).toHaveCount(0);
  await expect(deckLauncher.locator('.deck-manager-list')).toHaveCount(0);
  await expect(deckLauncher.locator('table')).toHaveCount(0);
  await expect(deckLauncher.getByRole('button', { name: /Open 管理 Deck 16|打开 管理 Deck 16/ })).toHaveCount(0);
  await expect(deckLauncher.getByRole('button', { name: /Edit 管理 Deck 16|编辑 管理 Deck 16/ })).toHaveCount(0);
  await expect(deckLauncher.getByRole('button', { name: /Open 管理 Deck 14|打开 管理 Deck 14/ })).toHaveCount(0);
  await expect(deckLauncher.getByRole('button', { name: /Edit 管理 Deck 14|编辑 管理 Deck 14/ })).toHaveCount(0);
  await expect(deckLauncher.getByRole('button', { name: /Open 管理 Deck 15|打开 管理 Deck 15/ })).toHaveCount(0);
  await expect(deckLauncher.getByRole('button', { name: /Edit 管理 Deck 15|编辑 管理 Deck 15/ })).toHaveCount(0);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-enabled-launcher-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 780 });
  const narrowShortcutRects = await enabledShortcutList.locator('.deck-manager-enabled__item').evaluateAll(
    (items) => items.map((item) => {
      const rect = item.getBoundingClientRect();
      return { height: rect.height, width: rect.width };
    }),
  );
  expect(narrowShortcutRects.every(({ height, width }) => Math.abs(height - width) <= 1 && width === 44)).toBe(true);
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-enabled-launcher-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1200, height: 760 });

  await deckLauncher.getByRole('button', { name: /Open Deck settings|打开 Deck 设置/ }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work`);
  let settingsNavigation = page.getByRole('navigation', { name: 'Settings categories navigation' });
  await expect(settingsNavigation.getByRole('button', { name: 'Work', exact: true })).toBeVisible();
  await expect(settingsNavigation.getByRole('button', { name: 'Resource connection', exact: true })).toHaveCount(0);
  await expect(settingsNavigation.getByRole('button', { name: 'Plugins', exact: true })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Work', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '工作台', exact: true })).toHaveCount(0);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/settings-work-en-wide.png',
    fullPage: true,
  });
  await settingsNavigation.getByRole('button', { name: 'General', exact: true }).click();
  await page.getByRole('button', { name: '中文 (Chinese)', exact: true }).click();
  settingsNavigation = page.getByRole('navigation', { name: '设置分类导航' });
  await settingsNavigation.getByRole('button', { name: '工作台', exact: true }).click();
  await expect(page.getByRole('heading', { name: '工作台', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Work', exact: true })).toHaveCount(0);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/settings-work-zh-wide.png',
    fullPage: true,
  });
  await settingsNavigation.getByRole('button', { name: '常规', exact: true }).click();
  await page.getByRole('button', { name: 'English (英语)', exact: true }).click();
  settingsNavigation = page.getByRole('navigation', { name: 'Settings categories navigation' });
  await settingsNavigation.getByRole('button', { name: 'Work', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Work', exact: true })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Deck' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tab', { name: 'Resource links' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Plugins' })).toBeVisible();
  await page.getByRole('tab', { name: 'Resource links' }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work?tab=resources`);
  await expect(page.getByRole('tabpanel', { name: 'Resource links' })).toBeVisible();
  await expect(page.getByLabel('资源链接设置')).toBeVisible();
  await page.getByRole('tab', { name: 'Plugins' }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work?tab=plugins`);
  await expect(page.getByRole('tabpanel', { name: 'Plugins' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Claude 插件' })).toBeVisible();
  await page.getByRole('tab', { name: 'Deck' }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work?tab=deck`);
  const deckSettingsList = page.getByRole('list', { name: /Deck settings|Deck 设置列表/ });
  await expect(deckSettingsList).toBeVisible();
  await expect(deckSettingsList.locator(':scope > li')).toHaveCount(10);
  await expect(page.getByRole('navigation', { name: /Deck list pages|Deck 列表分页/ })).toBeVisible();
  await expect(page.locator('.deck-manager-home--settings thead, .deck-manager-home--settings [role="columnheader"]')).toHaveCount(0);
  await expect(deckSettingsList.getByRole('switch')).toHaveCount(9);
  await expect(deckSettingsList.locator('.deck-manager-chip').filter({ hasText: /System|系统/ })).toHaveCount(1);
  await expect(screenplayDeck.deck_plugin_version).toBe('1.0.1');
  await expect(page.getByText(/内容 v2/).first()).toBeVisible();
  await expect(page.getByText(/运行插件 v1.0.1/).first()).toBeVisible();
  await expect(page.getByText(/Publish to Community|发布到社区|My Published Decks|我发布的卡组/)).toHaveCount(0);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/settings-work-deck-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 780 });
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/settings-work-deck-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1200, height: 760 });

  await page.getByRole('button', { name: /Next|下一页/ }).click();
  await expect(page.getByText('管理 Deck 11', { exact: true })).toBeVisible();
  await expect(page.getByText('剧本创作团队', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: /Previous|上一页/ }).click();
  await expect(page.getByText('剧本创作团队', { exact: true })).toBeVisible();

  const readsBeforeRefresh = deckListReads;
  await page.getByRole('button', { name: /Refresh|刷新/ }).click();
  await expect.poll(() => deckListReads).toBeGreaterThan(readsBeforeRefresh);
  failNextDeckRead = true;
  await page.getByRole('button', { name: /Refresh|刷新/ }).click();
  await expect(page.getByRole('alert')).toContainText('Deck refresh temporarily unavailable');
  await expect(page.getByText('剧本创作团队', { exact: true })).toBeVisible();

  const creatorSearch = page.getByRole('searchbox', { name: /Search managed Decks|搜索可管理的 Deck/ });
  await creatorSearch.fill('不存在的 Deck');
  await expect(page.getByText(/No Deck matches these filters|没有符合当前条件的 Deck/)).toBeVisible();
  await page.getByRole('button', { name: /Clear filters|清除筛选/ }).click();
  await expect(creatorSearch).toHaveValue('');
  await creatorSearch.fill('管理 Deck 14');
  await expect(page.getByText('管理 Deck 14', { exact: true })).toBeVisible();
  await creatorSearch.fill('');
  await page.getByRole('tab', { name: /Dream\s*1/ }).click();
  await expect(page.getByText('剧本创作团队', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: /All\s*17|全部\s*17/ }).click();
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-pdf-refresh-error-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 640, height: 780 });
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  const screenplayCreatorRow = page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${screenplayDeck.id}"]`,
  );
  await expect(screenplayCreatorRow.locator('.deck-manager-list__description')).toContainText('覆盖剧情');
  expect((await screenplayCreatorRow.getByRole('switch').boundingBox())?.height ?? 0)
    .toBeGreaterThanOrEqual(44);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-pdf-refresh-error-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1200, height: 760 });

  await screenplayCreatorRow.getByRole('button', {
    name: /More actions for 剧本创作团队|剧本创作团队 的更多操作/,
  }).click();
  await page.getByRole('menuitem', { name: /Related conversations|相关对话/ }).click();
  const relatedDialog = page.getByRole('dialog', { name: /Related conversations|相关对话/ });
  await expect(relatedDialog).toBeVisible();
  await expect(relatedDialog.locator('.deck-manager-related-list__item')).toHaveCount(2);
  await expect(relatedDialog.getByText('雨夜开场讨论', { exact: true })).toBeVisible();
  await expect(relatedDialog.getByText('第二幕人物关系', { exact: true })).toBeVisible();
  await expect(relatedDialog.getByRole('button', { name: /Delete Deck|删除 Deck/ })).toBeDisabled();
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-related-conversations-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 780 });
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-related-conversations-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1200, height: 760 });

  const firstRelatedDelete = relatedDialog.getByRole('button', {
    name: /Delete conversation 雨夜开场讨论|删除对话 雨夜开场讨论/,
  });
  page.once('dialog', (dialog) => dialog.dismiss());
  await firstRelatedDelete.click();
  await expect(relatedDialog.locator('.deck-manager-related-list__item')).toHaveCount(2);
  expect(relatedThreadDeletes).toEqual([]);
  page.once('dialog', (dialog) => dialog.accept());
  await firstRelatedDelete.click();
  await expect(relatedDialog.locator('.deck-manager-related-list__item')).toHaveCount(1);
  page.once('dialog', (dialog) => dialog.accept());
  await relatedDialog.getByRole('button', { name: /Delete conversation 第二幕人物关系|删除对话 第二幕人物关系/ }).click();
  await expect(relatedDialog.locator('.deck-manager-related-list__item')).toHaveCount(0);
  await expect(relatedDialog.getByText(/No related conversations|没有相关对话/)).toBeVisible();
  await expect(relatedDialog.getByRole('button', { name: /Delete Deck|删除 Deck/ })).toBeEnabled();
  expect(relatedThreadDeletes).toEqual(['thread-screenplay-one', 'thread-screenplay-two']);
  await relatedDialog.getByRole('button', { name: /Close|关闭/ }).last().click();
  await expect(relatedDialog).toHaveCount(0);
  failNextRelatedThreadRead = true;
  await screenplayCreatorRow.getByRole('button', {
    name: /More actions for 剧本创作团队|剧本创作团队 的更多操作/,
  }).click();
  await page.getByRole('menuitem', { name: /Related conversations|相关对话/ }).click();
  const failedRelatedDialog = page.getByRole('dialog', { name: /Related conversations|相关对话/ });
  await expect(failedRelatedDialog.getByRole('alert')).toContainText('Related conversations temporarily unavailable');
  await expect(failedRelatedDialog.getByRole('button', { name: /Delete Deck|删除 Deck/ })).toBeDisabled();
  await failedRelatedDialog.getByRole('button', { name: /Retry|重试/ }).click();
  await expect(failedRelatedDialog.getByText(/No related conversations|没有相关对话/)).toBeVisible();
  await expect(failedRelatedDialog.getByRole('button', { name: /Delete Deck|删除 Deck/ })).toBeEnabled();
  await failedRelatedDialog.getByRole('button', { name: /Close|关闭/ }).last().click();

  await screenplayCreatorRow.locator('.deck-manager-list__identity').click();
  const detailsDialog = page.locator('.deck-editor');
  await expect(detailsDialog).toBeVisible();
  await expect(detailsDialog.getByLabel('Deck Name')).toHaveValue('剧本创作团队');
  await expect(detailsDialog.locator('.deck-version-panel')).toHaveCount(0);
  await expect(detailsDialog.getByRole('button', { name: '版本记录' })).toHaveAttribute('aria-expanded', 'false');
  await detailsDialog.getByRole('button', { name: '版本记录' }).click();
  await expect(detailsDialog.locator('.deck-version-panel')).toBeVisible();
  await expect(detailsDialog.getByText('当前 Deck 内容', { exact: true })).toBeVisible();
  await expect(detailsDialog.getByText('v2', { exact: true })).toBeVisible();
  await expect(detailsDialog.getByText('v2 · 当前', { exact: true })).toBeVisible();
  await expect(detailsDialog.getByText('v1.0.1', { exact: true })).toBeVisible();
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-version-history-wide.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 780 });
  await expect(detailsDialog.getByRole('button', { name: '收起版本记录' })).toBeVisible();
  expect(await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )).toBe(true);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-version-history-narrow.png',
    fullPage: true,
  });
  await page.setViewportSize({ width: 1200, height: 760 });
  await detailsDialog.getByRole('button', { name: '收起版本记录' }).click();
  await detailsDialog.getByRole('tab', { name: /Agents/ }).click();
  await expect(detailsDialog.getByText('Agent Prompt')).toBeVisible();
  await detailsDialog.getByRole('tab', { name: 'Claude 插件' }).click();
  await expect(detailsDialog.getByLabel('Deck Claude 插件')).toBeVisible();
  await expect(detailsDialog.getByText(/Workflow|工作流/)).toHaveCount(0);
  expect(defaultReconcileCalls).toBeGreaterThanOrEqual(1);
  expect(screenplaySelectedInstallationIds).toEqual([dramaInstallation.id]);
  await detailsDialog.getByRole('button', { name: 'Close' }).click();

  await page.getByRole('button', { name: /^Create$|^创建$/ }).click();
  const createMenu = page.getByRole('menu');
  await expect(createMenu).toBeVisible();
  await expect(createMenu.getByText(/Deck Market|Deck 市场/)).toHaveCount(0);
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-pdf-create-menu-wide.png',
    fullPage: true,
  });
  await createMenu.getByRole('menuitem', { name: /Create Deck|创建 Deck/ }).click();
  const createDialog = page.locator('.deck-editor');
  await expect(createDialog).toBeVisible();
  await expect.poll(() => createWrites.length).toBe(1);
  await expect(createDialog.getByLabel('Deck Name')).toHaveValue(/New Deck|新建 Deck/);
  await expect(createDialog.getByRole('button', { name: '版本记录' })).toBeVisible();
  await expect(createDialog.getByText(/内容版本未提交/)).toBeVisible();
  await createDialog.getByLabel('Deck Name').fill('雨夜剧作团队');
  await createDialog.getByLabel('Deck Name').press('Tab');
  await expect.poll(() => deckWrites.some(
    (write) => write.name === '雨夜剧作团队',
  )).toBe(true);
  await createDialog.getByLabel('Deck Description').fill('用于雨夜剧本创作的完整维护 Deck');
  await createDialog.getByLabel('Deck Description').press('Tab');
  await expect.poll(() => deckWrites.some(
    (write) => write.description === '用于雨夜剧本创作的完整维护 Deck',
  )).toBe(true);

  await createDialog.getByLabel('Dream Agent').check();
  await expect.poll(() => agentTypeWrites).toEqual([{
    agent_type: 'dream',
    expected_binding_revision: 0,
  }]);

  await createDialog.getByRole('button', { name: '版本记录' }).click();
  await expect(createDialog.getByText('尚未提交', { exact: true })).toBeVisible();
  await createDialog.getByRole('button', { name: '选择运行版本' }).click();
  const versionPicker = page.getByRole('dialog', { name: '选择运行版本' });
  await versionPicker.getByRole('radio', { name: /Drama Forge v1\.1\.0/ }).click();
  await versionPicker.getByRole('button', { name: '确认切换' }).click();
  await expect.poll(() => versionWrites).toEqual([{
    deck_plugin_id: 'ink.deck.drama-forge',
    deck_plugin_version: '1.1.0',
    expected_binding_revision: 1,
    apply_to: 'next_run',
  }]);
  await expect(createDialog.getByText('v1.1.0', { exact: true })).toBeVisible();
  await createDialog.getByRole('button', { name: '收起版本记录' }).click();

  await createDialog.getByRole('tab', { name: 'Claude 插件' }).click();
  await expect(createDialog.getByRole('checkbox', { name: /drama-forge/ })).toBeChecked();
  await createDialog.getByRole('checkbox', { name: /story-notes/ }).check();
  await createDialog.getByRole('button', { name: '保存插件选择' }).click();
  await expect.poll(() => pluginWrites).toEqual([[dramaInstallation.id, secondaryInstallation.id]]);

  await createDialog.getByRole('tab', { name: /Agents/ }).click();
  await createDialog.getByRole('button', { name: '+ Add', exact: true }).click();
  await expect.poll(() => createdDeckState.voices).toHaveLength(1);
  const agentName = createDialog.getByLabel('Agent Name');
  await expect(agentName).toHaveValue('New Voice');
  await agentName.fill('雨夜连续性 Agent');
  await agentName.press('Tab');
  await expect.poll(() => voiceWrites.some(
    (write) => write.name === '雨夜连续性 Agent',
  )).toBe(true);
  const agentPrompt = createDialog.getByLabel('Agent Prompt');
  await agentPrompt.fill('检查人物动机、场景时间和对白连续性。');
  await agentPrompt.press('Tab');
  await expect.poll(() => voiceWrites.some(
    (write) => write.system_prompt === '检查人物动机、场景时间和对白连续性。',
  )).toBe(true);
  await createDialog.getByLabel('Agent Color').selectOption('green');
  await expect.poll(() => voiceWrites.some((write) => write.color === 'green')).toBe(true);

  await createDialog.getByRole('button', { name: /提交 v1/ }).click();
  const firstCommitDialog = page.getByRole('dialog', { name: /提交 .* 为 v1/ });
  await expect(firstCommitDialog).toContainText('历史 Thread 不会自动升级');
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-submit-v1-preview-wide.png',
    fullPage: true,
  });
  await firstCommitDialog.getByRole('button', { name: '取消' }).click();
  expect(contentCommitWrites).toHaveLength(0);
  await createDialog.getByRole('button', { name: /提交 v1/ }).click();
  const confirmedFirstCommit = page.getByRole('dialog', { name: /提交 .* 为 v1/ });
  await confirmedFirstCommit.getByPlaceholder('说明这次修改的目的').fill('首次完整配置');
  await confirmedFirstCommit.getByRole('button', { name: '确认提交 v1' }).click();
  await expect.poll(() => contentCommitWrites).toHaveLength(1);
  await expect(createDialog.getByText(/内容版本 v1/)).toBeVisible();

  await createDialog.getByRole('button', { name: '在 Chat 中使用 →' }).click();
  await expect(page).toHaveURL(new RegExp('/story-workspace/chat\\?deck=created-screenplay-deck&agent=created-screenplay-agent'));
  await expect(navigation.getByRole('button', { name: 'Chat' })).toHaveAttribute('aria-current', 'page');
  await navigation.getByRole('button', { name: 'Decks' }).click();
  await expect(page.locator('[data-deck-manager-launcher]')).toBeVisible();
  await expect(page.getByRole('list', { name: /Deck settings|Deck 设置列表/ })).toHaveCount(0);
  await page.getByRole('button', { name: /Open Deck settings|打开 Deck 设置/ }).click();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work`);
  await creatorSearch.fill('雨夜剧作团队');
  const createdCreatorCard = page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${createdDeck.id}"]`,
  );
  await expect(createdCreatorCard).toContainText('雨夜剧作团队');

  await createdCreatorCard.locator('.deck-manager-list__identity').click();
  const editDialog = page.locator('.deck-editor');
  await editDialog.getByRole('tab', { name: /Agents/ }).click();
  await expect(editDialog.getByLabel('Agent Name')).toHaveValue('雨夜连续性 Agent');
  await expect(editDialog.getByLabel('Agent Prompt')).toHaveValue('检查人物动机、场景时间和对白连续性。');
  await editDialog.getByRole('tab', { name: '概览' }).click();
  await editDialog.getByLabel('Deck Description').fill('用于雨夜剧本创作的完整维护');
  await editDialog.getByLabel('Deck Description').press('Tab');
  await expect.poll(() => deckWrites.some(
    (write) => write.description === '用于雨夜剧本创作的完整维护',
  )).toBe(true);
  await editDialog.getByRole('button', { name: /提交 v2/ }).click();
  const secondCommitDialog = page.getByRole('dialog', { name: /提交 .* 为 v2/ });
  await secondCommitDialog.getByPlaceholder('说明这次修改的目的').fill('调整说明');
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-submit-v2-preview-wide.png',
    fullPage: true,
  });
  await secondCommitDialog.getByRole('button', { name: '确认提交 v2' }).click();
  await expect.poll(() => contentCommitWrites).toHaveLength(2);
  await expect(editDialog.getByText(/内容版本 v2/)).toBeVisible();
  await editDialog.getByRole('button', { name: 'Close' }).click();

  await createdCreatorCard.getByRole('switch').click();
  await expect.poll(() => createdDeckState.enabled).toBe(false);
  await expect(createdCreatorCard.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
  await createdCreatorCard.getByRole('switch').click();
  await expect.poll(() => createdDeckState.enabled).toBe(true);
  await expect(createdCreatorCard.getByRole('switch')).toHaveAttribute('aria-checked', 'true');

  failNextDeckUpdate = true;
  await createdCreatorCard.getByRole('switch').click();
  await expect(page.getByRole('alert')).toContainText('Deck changed concurrently');
  await expect(createdCreatorCard.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByText(/Publish to Community|发布到社区|Install|安装/)).toHaveCount(0);

  await page.reload();
  await expect(page).toHaveURL(`${WEB_BASE}/story-workspace/settings/work`);
  await expect(page.getByRole('list', { name: /Deck settings|Deck 设置列表/ })).toBeVisible();
  await expect(page.getByRole('tab', { name: /Use Decks|Create Decks|使用 Deck|创作 Deck/ })).toHaveCount(0);
  const refreshedSearch = page.getByRole('searchbox', { name: /Search managed Decks|搜索可管理的 Deck/ });
  await refreshedSearch.fill('雨夜剧作团队');
  await page.locator(
    `[data-deck-card-kind="owned"][data-deck-card-id="${createdDeck.id}"]`,
  ).locator('.deck-manager-list__identity').click();
  const refreshedDetailsDialog = page.locator('.deck-editor');
  await expect(refreshedDetailsDialog.getByLabel('Deck Name')).toHaveValue('雨夜剧作团队');
  await expect(refreshedDetailsDialog.getByLabel('Deck Description')).toHaveValue('用于雨夜剧本创作的完整维护');
  await refreshedDetailsDialog.getByRole('tab', { name: /Agents/ }).click();
  await expect(refreshedDetailsDialog.getByLabel('Agent Name')).toHaveValue('雨夜连续性 Agent');
  await expect(refreshedDetailsDialog.getByText(/Workflow|工作流/)).toHaveCount(0);
  await expect.poll(async () => page.locator('body').evaluate((body) => getComputedStyle(body).fontFamily))
    .toContain('Microsoft YaHei');

  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-popup-details-wide.png',
    fullPage: true,
  });
  await refreshedDetailsDialog.getByLabel('Agent Prompt').scrollIntoViewIfNeeded();
  await expect(refreshedDetailsDialog.getByLabel('Agent Prompt')).toBeVisible();
  await page.screenshot({
    path: 'output/playwright/story-workspace-chat-first/deck-popup-agent-maintenance-wide.png',
    fullPage: true,
  });
  const agentEnabled = refreshedDetailsDialog.getByLabel('Enabled', { exact: true });
  await agentEnabled.click();
  await expect.poll(() => voiceWrites.some((write) => write.enabled === false)).toBe(true);
  await expect(agentEnabled).not.toBeChecked();
  await agentEnabled.click();
  await expect.poll(() => voiceWrites.some((write) => write.enabled === true)).toBe(true);
  await expect(agentEnabled).toBeChecked();
  page.once('dialog', async (dialog) => {
    expect(dialog.message()).toMatch(/Delete this Agent|确定删除这个 Agent/);
    await dialog.accept();
  });
  await refreshedDetailsDialog.getByRole('button', { name: 'Delete', exact: true }).click();
  await expect.poll(() => voiceDeletes).toEqual([createdVoice.id]);
  await expect(refreshedDetailsDialog.getByText('Select an agent from the list to edit')).toBeVisible();
  await expect.poll(() => diagnostics).toEqual([]);
  expect(expectedHttpFailureDiagnostics).toHaveLength(3);
  expect(expectedHttpFailures.get(503)).toBe(0);
  expect(expectedHttpFailures.get(409)).toBe(0);
  expect(createWrites).toEqual([expect.objectContaining({
    name: expect.stringMatching(/New Deck|新建 Deck/),
    description: expect.stringMatching(/Describe your deck here|请在这里描述你的 Deck/),
    icon: 'brain',
    color: 'blue',
  })]);
  expect(deckWrites).toEqual(expect.arrayContaining([
    expect.objectContaining({ description: '用于雨夜剧本创作的完整维护' }),
    { enabled: false },
    { enabled: true },
  ]));
  expect(agentTypeWrites).toEqual([{
    agent_type: 'dream',
    expected_binding_revision: 0,
  }]);
  expect(versionWrites).toEqual([{
    deck_plugin_id: 'ink.deck.drama-forge',
    deck_plugin_version: '1.1.0',
    expected_binding_revision: 1,
    apply_to: 'next_run',
  }]);
  expect(contentPreviewWrites).toHaveLength(3);
  expect(contentCommitWrites).toEqual([
    expect.objectContaining({ expected_base_version: null, description: '首次完整配置' }),
    expect.objectContaining({ expected_base_version: 1, description: '调整说明' }),
  ]);
  expect(voiceWrites).toEqual(expect.arrayContaining([
    { name: '雨夜连续性 Agent' },
    { system_prompt: '检查人物动机、场景时间和对白连续性。' },
    { color: 'green' },
    { enabled: false },
    { enabled: true },
  ]));
  expect(voiceDeletes).toEqual([createdVoice.id]);
  expect(pluginWrites).toEqual([[dramaInstallation.id, secondaryInstallation.id]]);
  expect(unexpectedApiRequests).toEqual([]);
});
