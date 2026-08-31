// [Input] Deterministic actor-scoped Dream/Episode REST snapshots served at the browser boundary.
// [Output] Chromium evidence for responsive Episode navigation, read-only binding state, and revision-stable selection.
// [Pos] Story Workspace Episode Execution mocked-browser QA (U12); never claims external workflow success.
// [Sync] 2026-08-13: unbound EP01 remains read-only while the turn Hook publishes and binds.
// [Sync] 2026-08-13: Dream Agent dialog uses its full conversation row and contains long
//                    Chat content without page- or message-level horizontal overflow.
// [Sync] 2026-08-13: scrolling the Episode workbench must not move the open Dream Agent
//                    dialog outside the desktop viewport.
// [Sync] 2026-08-31: the canonical file reader opens in the matching draft EP,
//                    while sync read actions navigate back to that focus.
// [Sync] 2026-08-31: the draft EP list replaces raw storyboard summary payloads
//                    with projected shot count and duration.
// [Sync] 2026-08-31: Outline opens an illustrated three-stage creation guide
//                    through the same focus/back interaction as an Episode.
// [Sync] 2026-08-31: Dream's guide entry returns to the originating run workbench.
// [Sync] 2026-08-31: the bound Dream masthead opens that same guide focus below
//                    the “创作工作空间” title.

// @ts-expect-error Playwright E2E has Node built-ins; the browser app tsconfig omits Node types.
import { mkdirSync, readFileSync } from 'node:fs';
// @ts-expect-error Playwright E2E has Node built-ins; the browser app tsconfig omits Node types.
import { resolve } from 'node:path';
import { expect, test, type Page, type Route } from '@playwright/test';
import { storyWorkspaceParseEpisodeArtifactSurface } from '../src/hooks/story-workspace/contracts';

const WEB_BASE = process.env.INK_E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const RUN_ID = `run_${'1'.repeat(32)}`;
const EPISODE_ID = 'e'.repeat(32);
const EPISODE_VIEW_ID = 'a'.repeat(32);
const ARC_ID = 'b'.repeat(32);
const BEAT_ID = 'c'.repeat(32);
const SCENE_ID = 'd'.repeat(32);
const SHOT_VIEW_ID = 'f'.repeat(32);
const PROMPT_ID = '1'.repeat(32);
const QUEUE_ID = '2'.repeat(32);
const RENDER_SECTION_ID = '3'.repeat(32);
const REVIEW_SECTION_ID = '4'.repeat(32);
const REVIEW_TARGET_ID = '5'.repeat(32);
const STORY_INDEX_ID = '123e4567-e89b-52d3-a456-426614174000';
const STORY_INDEX_ETAG = `sha256:${'9'.repeat(64)}`;
const FROZEN_NOW = '2026-08-06T04:00:00.000Z';
const CONTENT_REVISION = `sha256:${'a'.repeat(64)}`;
const MANIFEST_REVISIONS = [
  `sha256:${'1'.repeat(64)}`,
  `sha256:${'2'.repeat(64)}`,
] as const;
const AGGREGATE_ETAGS = [
  `sha256:${'6'.repeat(64)}`,
  `sha256:${'7'.repeat(64)}`,
] as const;
const ALL_ARTIFACTS = [
  ['episode-outline.md', 'plan_episode', ['episode_overview', 'storyline_navigator', 'narrative_workbench']],
  ['script.md', 'write_script', ['narrative_workbench', 'shot_inspector']],
  ['storyboard.yaml', 'regenerate_storyboard', ['narrative_workbench', 'shot_inspector']],
  ['prompts/', 'generate_prompts', ['shot_inspector', 'prompt_view']],
  ['renders/', 'prepare_render_guide', ['shot_inspector', 'render_view']],
  ['review-report.md', 'review_full_chain', ['review_view', 'shot_inspector']],
] as const;
const EVIDENCE_DIR = resolve(
  process.cwd(),
  '../output/playwright/story-workspace-episode-execution-u12',
);

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });

// Provider-free QA impact contract:
// Project title stays unchanged in the mocked Story Index; EP01 identity and
// canonical Artifact DTOs stay unchanged; Run-private publication, Hook writes,
// PostgreSQL materialization, and shared conversation mutations are out of
// scope. Only the final UI consumer ownership changes: the file reader mounts
// in the matching draft EP, sync read actions navigate to it, and the EP list
// projects shot count/duration instead of the raw stage summary. The added
// creation guide is static, read-only UI and performs no workflow mutation.
//
// Concept/fact impact brief for this provider-free browser lane:
// - Project identity/title: mocked Story Index is the authority; unchanged.
// - Episode identity/artifacts: mocked canonical DTO is the authority; unchanged.
// - Run-private publication and Hook/PostgreSQL materialization: not in scope.
// - Shared Thread/session: fixture identity remains unchanged; no new turn.
// - Final UI consumer: Outline gains one header trigger and a local focus guide.

function coverage(linked = 1, total = 1) {
  return { availability: 'available', linked, total, ratio: linked / total };
}

function dreamFiles() {
  return {
    storyWorkspaceRunId: RUN_ID,
    threadId: 'thread-u12-browser',
    source: {
      deckPluginBindingId: 'binding-u12-browser',
      bindingRevision: 1,
      deckPluginVersion: '1.0.0',
      deckRuntimeSnapshotId: 'snapshot-u12-browser',
      runtimePluginLockId: 'lock-u12-browser',
    },
    requiredStages: ['characters', 'scenes', 'storyboards'],
    runRevision: 1,
    stages: {
      storyboards: {
        stage: 'storyboards',
        revision: 1,
        sourceFiles: ['stories/proj-u12/episodes/EP01/storyboard.yaml'],
        page: {
          title: '分镜',
          entryRoute: `/story-workspace/runs/${RUN_ID}/execution`,
        },
        items: [{
          entityId: 'ep01_storyboard',
          displayName: 'EP01: 雨夜重逢',
          summary: '1 镜、3 秒。episode: EP01 total_shots: 1 total_duration_sec: 3',
          sourceFile: 'stories/proj-u12/episodes/EP01/storyboard.yaml',
          relations: ['EP01'],
        }],
      },
    },
    confirmationAccepted: true,
    confirmationDispatched: true,
    canConfirm: false,
    confirmationLabel: '确认并继续',
  };
}

function workflowRun() {
  return {
    workflow_run_id: RUN_ID,
    deck_plugin_id: 'drama-forge',
    deck_plugin_display_name: 'drama-forge',
    deck_plugin_version: '1.0.0',
    workflow_definition_ref: 'drama-init',
    workflow_summary: '雨夜重逢',
    deck_runtime_snapshot_id: 'snapshot-u12-browser',
    runtime_plugin_lock_id: 'lock-u12-browser',
    runtime_load_receipt_id: 'receipt-u12-browser',
    workflow_preflight_id: 'preflight-u12-browser',
    status: 'confirmed',
    status_version: 2,
    failed_step: null,
    error_code: null,
    retry_of_run_id: null,
    created_at: '2026-08-06T01:00:00Z',
    started_at: '2026-08-06T01:00:01Z',
    completed_at: null,
  };
}

function storyIndexProjection() {
  return {
    runId: RUN_ID,
    projectId: 'rainy-night',
    projectTitle: '雨夜归途',
    storyId: STORY_INDEX_ID,
    status: 'indexed',
    observedManifestRevision: MANIFEST_REVISIONS[0],
    observedScriptRevision: CONTENT_REVISION,
    indexedManifestRevision: MANIFEST_REVISIONS[0],
    indexedScriptRevision: CONTENT_REVISION,
    episodeCount: 1,
    lastIndexedAt: FROZEN_NOW,
    errorCode: null,
    retryable: false,
    etag: STORY_INDEX_ETAG,
  };
}

function episodeSurface(revisionIndex: 0 | 1) {
  const revision = MANIFEST_REVISIONS[revisionIndex];
  return {
    runId: RUN_ID,
    opaqueEpisodeId: EPISODE_ID,
    episodeCode: 'EP01',
    manifestRevision: revision,
    etag: AGGREGATE_ETAGS[revisionIndex],
    bindingAvailability: 'bound',
    artifacts: ALL_ARTIFACTS.map(([relativeKey, producerAction, consumers]) => ({
      relativeKey,
      availability: 'available',
      contentRevision: CONTENT_REVISION,
      mtime: '2026-08-06T01:02:03Z',
      size: 128,
      producerAction,
      consumers: [...consumers],
    })),
    narrative: {
      episodeId: EPISODE_VIEW_ID,
      storyArcId: ARC_ID,
      overview: {
        title: '雨夜重逢',
        series: '雨夜故事',
        storyGoals: ['重新建立信任'],
        coreConflict: '信任与隐瞒发生冲突。',
        hook: '电话再次响起。',
        sourceArtifact: 'episode-outline.md',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: null,
        characterBeats: [],
      },
      narrativeBeats: [{
        id: BEAT_ID,
        sourceKey: 'SC-01',
        title: '失去控制',
        assetSceneRef: null,
        narrativeFunction: '建立冲突',
        emotionTone: '克制',
        summary: '车站相遇。',
        sceneGoals: ['重逢'],
        keyDialogueBeats: ['你来了。'],
        sourceArtifact: 'episode-outline.md',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: null,
      }],
      scenes: [{
        id: SCENE_ID,
        sourceKey: 'S01',
        title: '车站外',
        heading: '外景·车站·夜',
        assetSceneRef: null,
        narrativeBeatId: BEAT_ID,
        declaredNarrativeBeatRef: 'SC-01',
        associationStatus: 'linked',
        actions: ['她停下脚步。'],
        dialogue: [{ speaker: '林默', qualifier: null, text: '你来了。' }],
        cameraCues: ['镜头保持稳定'],
        sourceArtifact: 'script.md',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: null,
      }],
      shots: [{
        id: SHOT_VIEW_ID,
        shotId: 'S01-E01-C01-SH001',
        assetSceneRef: null,
        declaredScriptSceneRef: 'S01',
        declaredNarrativeBeatRef: 'SC-01',
        scriptSceneId: SCENE_ID,
        narrativeBeatId: BEAT_ID,
        associationStatus: 'linked',
        shotType: 'medium',
        characters: [{
          ref: 'mc-01',
          displayName: '林默',
          depthPlane: 'front',
          action: '停步',
          emotion: '克制',
        }],
        camera: { angle: 'eye', height: 'eye-level', movement: 'static', lens: '50mm' },
        visual: revisionIndex === 0 ? '雨夜车站。' : '雨夜车站，车灯从背景掠过。',
        dialogue: [{ speaker: '林默', line: '你来了。', type: 'spoken' }],
        timing: { durationSec: 3, transitionIn: 'fade', transitionOut: 'cut' },
        sourceArtifact: 'storyboard.yaml',
        sourceRevision: CONTENT_REVISION,
        generatedFrom: 'script@v1',
      }],
      associations: {
        beatSceneCoverage: coverage(),
        sceneShotCoverage: coverage(),
        missingLinks: [],
        orphanArtifacts: [],
      },
    },
    auxiliary: {
      manifestRevision: revision,
      prompts: {
        items: [{
          id: PROMPT_ID,
          shotId: 'S01-E01-C01-SH001',
          kind: 'video',
          shotViewId: SHOT_VIEW_ID,
          associationStatus: 'linked',
          positive: '雨夜车站，中景。',
          negative: '避免过曝',
          parameters: {
            model: null,
            mode: null,
            durationSec: 3,
            motionStrength: null,
            cameraMotion: 'static',
            aspectRatio: '16:9',
          },
          generability: {
            characterAnchor: null,
            motionFeasibility: null,
            durationBudget: null,
            notes: null,
          },
          sourceArtifact: 'prompts/ep001-prompts.yml',
          sourceRevision: CONTENT_REVISION,
        }],
        total: 1,
        nextCursor: null,
      },
      renderGuide: {
        sections: [{
          id: RENDER_SECTION_ID,
          level: 2,
          title: '制作指导',
          text: '按镜头队列生成。',
          sourceArtifact: 'renders/render-guide.md',
          sourceRevision: CONTENT_REVISION,
        }],
        queue: {
          items: [{
            id: QUEUE_ID,
            shotId: 'S01-E01-C01-SH001',
            shotViewId: SHOT_VIEW_ID,
            associationStatus: 'linked',
            durationSec: 3,
            risk: null,
            priority: 'P1',
            renderer: null,
            status: 'pending',
            sourceArtifact: 'renders/render-guide.md',
            sourceRevision: CONTENT_REVISION,
          }],
          total: 1,
          nextCursor: null,
        },
        sourceArtifact: 'renders/render-guide.md',
        sourceRevision: CONTENT_REVISION,
      },
      review: {
        scope: 'full-chain',
        overallVerdict: 'APPROVED',
        reviewedArtifacts: [
          'episode-outline.md',
          'script.md',
          'storyboard.yaml',
          'prompts/ep001-prompts.yml',
        ],
        sourceRevisions: [{ sourceArtifact: 'script.md', sourceRevision: CONTENT_REVISION }],
        sections: [{
          id: REVIEW_SECTION_ID,
          level: 2,
          title: '结论',
          text: '通过。',
          sourceArtifact: 'review-report.md',
          sourceRevision: CONTENT_REVISION,
        }],
        targets: [{
          id: REVIEW_TARGET_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-C01-SH001',
          targetViewId: SHOT_VIEW_ID,
          associationStatus: 'linked',
          sectionId: REVIEW_SECTION_ID,
          sourceArtifact: 'review-report.md',
          sourceRevision: CONTENT_REVISION,
        }],
        sourceArtifact: 'review-report.md',
        sourceRevision: CONTENT_REVISION,
      },
      associations: {
        shotPromptCoverage: coverage(),
        shotRenderQueueCoverage: coverage(),
        totalPrompts: 1,
        totalQueueEntries: 1,
        orphanPrompts: [],
        orphanQueueEntries: [],
        duplicateQueueShotIds: [],
      },
    },
  };
}

function unboundEpisodeSurface() {
  return {
    runId: RUN_ID,
    opaqueEpisodeId: null,
    episodeCode: null,
    manifestRevision: null,
    etag: null,
    bindingAvailability: 'unbound',
    artifacts: [],
    documents: [],
    narrative: null,
    auxiliary: null,
  };
}

function json(route: Route, body: unknown, status = 200, headers?: Record<string, string>) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    headers,
    body: JSON.stringify(body),
  });
}

type BrowserFixtureState = {
  revisionIndex: 0 | 1;
  artifactReads: number;
  bindingAvailability?: 'bound' | 'unbound';
};

async function installApiFixture(page: Page, state: BrowserFixtureState) {
  await page.route(`${WEB_BASE}/api/**`, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    const matches = (
      expectedMethod: 'GET' | 'POST',
      expectedPath: string,
      expectedSearch = '',
    ) => (
      method === expectedMethod && path === expectedPath && url.search === expectedSearch
    );
    if (/\/dream-agent\//.test(path)) {
      throw new Error(`Legacy Dream Agent API request is forbidden: ${method} ${path}`);
    }
    if (matches('GET', '/api/me')) {
      await json(route, { id: 12, email: 'u12@example.test', display_name: 'U12 QA' });
      return;
    }
    if (matches('GET', '/api/default-voices')) {
      await json(route, {});
      return;
    }
    if (matches('GET', '/api/storage')) {
      await json(route, {});
      return;
    }
    if (matches('GET', '/api/decks')) {
      await json(route, { decks: [] });
      return;
    }
    if (matches('GET', '/api/preferences')) {
      await json(route, {
        first_login_completed: true,
        timezone: 'UTC',
        updated_at: '2026-08-06T01:00:00Z',
      });
      return;
    }
    if (matches('POST', '/api/preferences')) {
      await route.fulfill({ status: 204 });
      return;
    }
    if (matches('GET', '/api/sessions', '?timezone=Asia%2FShanghai')) {
      await json(route, { sessions: [] });
      return;
    }
    if (matches('POST', '/api/sessions')) {
      await json(route, { ok: true });
      return;
    }
    if (
      matches(
        'GET',
        '/api/sessions/range',
        '?timezone=Asia%2FShanghai&start_date=2026-07-23&end_date=2026-08-06',
      )
      || matches(
        'GET',
        '/api/sessions/range',
        '?timezone=UTC&start_date=2026-07-23&end_date=2026-08-06',
      )
    ) {
      await json(route, { sessions: [] });
      return;
    }
    if (
      matches('GET', '/api/sessions/aggregate', '?timezone=Asia%2FShanghai')
      || matches('GET', '/api/sessions/aggregate', '?timezone=UTC')
    ) {
      await json(route, {
        stats: { total_days: 0, total_entries: 0, total_words: 0 },
        sessions: [],
        timezone: 'UTC',
      });
      return;
    }
    if (
      matches('GET', '/api/pictures', '?limit=30')
      || matches(
        'GET',
        '/api/pictures/range',
        '?limit=28&start_date=2026-07-23&end_date=2026-08-06',
      )
    ) {
      await json(route, { pictures: [] });
      return;
    }
    if (matches('GET', '/api/reports')) {
      await json(route, { reports: [] });
      return;
    }
    if (matches('GET', '/api/sessions/events')) {
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': connected\n\n' });
      return;
    }
    if (matches('GET', '/api/story-workspace/dream-runs')) {
      await json(route, { runs: [] });
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}`)) {
      await json(route, workflowRun());
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/story-index`)) {
      await json(route, storyIndexProjection(), 200, { ETag: `"${STORY_INDEX_ETAG}"` });
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/events`)) {
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': ready\n\n' });
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`)) {
      await json(route, dreamFiles());
      return;
    }
    if (matches('GET', '/api/system-config')) {
      await json(route, { data: { im_full_access_enabled: false } });
      return;
    }
    if (matches('GET', '/api/claude-agent/threads/thread-u12-browser/plugin-load-receipt')) {
      await json(route, {
        thread_id: 'thread-u12-browser',
        deck_id: null,
        workspace_found: false,
        receipt: null,
        launch_manifest: null,
      });
      return;
    }
    if (matches('GET', '/api/claude-agent/threads/thread-u12-browser/messages')) {
      await json(route, {
        thread: {
          id: 'thread-u12-browser',
          title: 'Episode Dream thread',
          created_at: '2026-08-06T01:00:00Z',
          updated_at: '2026-08-06T01:04:01Z',
        },
        messages: [{
          id: 'message-u12-browser',
          role: 'assistant',
          parts: [{
            type: 'text',
            text: `第一集产物已同步到工作台。\n\n${'storyboard_payload_'.repeat(80)}`,
          }],
          metadata: {},
          created_at: '2026-08-06T01:04:00Z',
        }],
      });
      return;
    }
    if (matches('GET', '/api/claude-agent/threads/thread-u12-browser/status')) {
      await json(route, {
        running: false,
        lifecycle: 'idle',
        turn_count: 1,
        pending_tool_call_ids: [],
        tool_confirmation_observation: 'known',
      });
      return;
    }
    if (matches('GET', '/api/claude-agent/threads/thread-u12-browser/stream')) {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream; charset=utf-8',
        body: 'data: {"type":"finish","finishReason":"stop"}\n\n',
      });
      return;
    }
    if (matches('POST', '/api/claude-agent/tool-confirm')) {
      await json(route, { ok: true, approved: true });
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/episode-artifacts`)) {
      state.artifactReads += 1;
      if (state.bindingAvailability === 'unbound') {
        await json(route, unboundEpisodeSurface());
        return;
      }
      const etag = AGGREGATE_ETAGS[state.revisionIndex];
      if (request.headers()['if-none-match'] === `"${etag}"`) {
        await route.fulfill({ status: 304, headers: { ETag: `"${etag}"` } });
      } else {
        await json(route, episodeSurface(state.revisionIndex), 200, { ETag: `"${etag}"` });
      }
      return;
    }
    throw new Error(`Unallowlisted API request: ${method} ${path}`);
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => ({
    document: document.documentElement.scrollWidth <= window.innerWidth + 1,
    body: document.body.scrollWidth <= window.innerWidth + 1,
    workbench: (() => {
      const element = document.querySelector<HTMLElement>('[aria-label="Episode 叙事工作台"]');
      return element === null || element.scrollWidth <= element.clientWidth + 1;
    })(),
  }))).toEqual({ document: true, body: true, workbench: true });
}

async function expectDreamAgentConversationLayout(page: Page) {
  const metrics = await page.getByRole('dialog', { name: 'Dream Agent' }).evaluate((dialog) => {
    const header = dialog.querySelector<HTMLElement>('.story-workspace-dream-agent-dialog__header');
    const thread = dialog.querySelector<HTMLElement>('.story-workspace-dream-agent-dialog__thread-chat');
    const messageScroller = dialog.querySelector<HTMLElement>('[data-chat-scroll-region="messages"]');
    if (header === null || thread === null) throw new Error('Dream Agent dialog regions are missing.');
    const dialogRect = dialog.getBoundingClientRect();
    const headerRect = header.getBoundingClientRect();
    const threadRect = thread.getBoundingClientRect();
    return {
      gridRowCount: getComputedStyle(dialog).gridTemplateRows.split(/\s+/).filter(Boolean).length,
      threadTopGap: Math.abs(threadRect.top - headerRect.bottom),
      threadBottomGap: Math.abs(dialogRect.bottom - threadRect.bottom),
      dialogHorizontalOverflow: dialog.scrollWidth - dialog.clientWidth,
      messageHorizontalOverflow: messageScroller === null
        ? null
        : messageScroller.scrollWidth - messageScroller.clientWidth,
      messageOverscrollY: messageScroller === null
        ? null
        : getComputedStyle(messageScroller).overscrollBehaviorY,
      viewportBounds: {
        top: dialogRect.top,
        right: window.innerWidth - dialogRect.right,
        bottom: window.innerHeight - dialogRect.bottom,
        left: dialogRect.left,
      },
    };
  });
  expect(metrics.gridRowCount).toBe(2);
  expect(metrics.threadTopGap).toBeLessThanOrEqual(1);
  expect(metrics.threadBottomGap).toBeLessThanOrEqual(2);
  expect(metrics.dialogHorizontalOverflow).toBeLessThanOrEqual(1);
  expect(metrics.messageHorizontalOverflow).not.toBeNull();
  expect(metrics.messageHorizontalOverflow!).toBeLessThanOrEqual(1);
  expect(metrics.messageOverscrollY).toBe('contain');
  expect(metrics.viewportBounds.top).toBeGreaterThanOrEqual(0);
  expect(metrics.viewportBounds.right).toBeGreaterThanOrEqual(0);
  expect(metrics.viewportBounds.bottom).toBeGreaterThanOrEqual(0);
  expect(metrics.viewportBounds.left).toBeGreaterThanOrEqual(0);
}

async function selectShotWithKeyboard(page: Page) {
  const expectFocusedText = (value: string) => expect.poll(
    () => page.evaluate(() => document.activeElement?.textContent ?? ''),
  ).toContain(value);
  const episode = page.getByRole('treeitem', { name: '雨夜重逢', exact: true });
  await episode.focus();
  await page.keyboard.press('ArrowRight');
  await expect(episode).toHaveAttribute('aria-expanded', 'true');
  await page.keyboard.press('ArrowRight');
  const beat = page.getByRole('treeitem', { name: 'SC-01 失去控制', exact: true });
  await expectFocusedText('SC-01 失去控制');
  await page.keyboard.press('ArrowRight');
  await expect(beat).toHaveAttribute('aria-expanded', 'true');
  await page.keyboard.press('ArrowRight');
  const scene = page.getByRole('treeitem', { name: 'S01 车站外', exact: true });
  await expectFocusedText('S01 车站外');
  await page.keyboard.press('ArrowRight');
  await expect(scene).toHaveAttribute('aria-expanded', 'true');
  await page.keyboard.press('ArrowRight');
  const shot = page.getByRole('treeitem', { name: 'S01-E01-C01-SH001', exact: true });
  await expectFocusedText('S01-E01-C01-SH001');
  await expect(page.getByRole('article', { name: 'Shot Detail' })).toBeVisible();
  return shot;
}

test('keeps an unbound first Episode read-only while automatic publication and binding finish', async ({
  page,
}) => {
  const diagnostics: string[] = [];
  const recoveryRequests: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')
      && !url.includes('react-grab.com')) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  page.on('request', (request) => {
    if (
      request.method() === 'POST'
      && new URL(request.url()).pathname.endsWith('/episode-binding/recover')
    ) recoveryRequests.push(request.url());
  });

  const state: BrowserFixtureState = {
    revisionIndex: 0,
    artifactReads: 0,
    bindingAvailability: 'unbound',
  };
  await page.clock.setFixedTime(FROZEN_NOW);
  await installApiFixture(page, state);
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'u12-browser-token');
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });

  await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
  await expect(page.getByRole('region', { name: 'Dream 初稿工作台' })).toBeVisible();
  await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  let agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
  await agentDialog.getByRole('button', { name: '同步', exact: true }).click();
  await agentDialog.getByRole('button', { name: '收起 Dream Agent' }).click();
  await expect(page.getByRole('heading', { name: '尚未构建 Episode 产物关联' })).toBeVisible();
  await expect(page.getByRole('status').filter({
    hasText: '关联状态：等待主 Agent 成功构建并自动发布',
  })).toBeVisible();
  await expect(page.locator(
    'main[aria-labelledby="story-workspace-episode-unbound-title"] > p',
  ).last()).toContainText('无需手动构建');
  await expect(page.getByRole('button', { name: '构建第一集产物关联' })).toHaveCount(0);

  await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
  await expect(agentDialog).toBeVisible();
  await expect(agentDialog.getByRole('group', { name: 'Episode 工作流操作' })).toHaveCount(0);
  await expect(agentDialog.getByText('构建第一集产物关联', { exact: true })).toHaveCount(0);
  expect(recoveryRequests).toEqual([]);
  expect(diagnostics).toEqual([]);
});

test('Dream run title opens the shared creation guide without adding an index item', async ({ page }) => {
  const diagnostics: string[] = [];
  const state: BrowserFixtureState = {
    revisionIndex: 0,
    artifactReads: 0,
  };
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')
      && !url.includes('react-grab.com')) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  await page.clock.setFixedTime(FROZEN_NOW);
  await installApiFixture(page, state);
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'u12-browser-token');
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);

  const title = page.getByRole('heading', { name: '创作工作空间' });
  const guideTrigger = page.getByRole('button', { name: '查看短剧创作阶段指引' });
  await expect(title).toBeVisible();
  await expect(guideTrigger).toBeVisible();
  const titleBox = await title.boundingBox();
  const triggerBox = await guideTrigger.boundingBox();
  expect(titleBox).not.toBeNull();
  expect(triggerBox).not.toBeNull();
  expect(triggerBox!.y).toBeGreaterThanOrEqual(titleBox!.y + titleBox!.height);

  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'dream-creation-guide-entry-desktop-1440x1000.png'),
  });

  await guideTrigger.click();
  await expect(page).toHaveURL(
    new RegExp(`/story-workspace/runs/${RUN_ID}/execution\\?focus=creation-guide$`),
  );
  await expect(page.getByRole('article', { name: '短剧创作流程' })).toBeVisible();
  await expect(page.getByRole('button').filter({ hasText: 'EP01: 雨夜重逢' })).toHaveCount(0);
  await page.getByRole('button', { name: '← 返回上一页' }).click();
  await expect(page).toHaveURL(
    new RegExp(`/story-workspace/dream\\?run=${RUN_ID}$`),
  );
  await expect(page.getByRole('heading', { name: '创作工作空间' })).toBeVisible();
  await expect(page.getByRole('button', { name: '查看短剧创作阶段指引' })).toBeVisible();
  expect(diagnostics).toEqual([]);
});

test('mocked REST facts recover responsively and preserve the selected shot across revisions', async ({
  context,
  page,
}) => {
  test.setTimeout(60_000);
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const diagnostics: string[] = [];
  const state: BrowserFixtureState = {
    revisionIndex: 0,
    artifactReads: 0,
  };
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')
      && !url.includes('react-grab.com')) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  try {
    expect(() => storyWorkspaceParseEpisodeArtifactSurface(episodeSurface(0))).not.toThrow();
    await page.clock.setFixedTime(FROZEN_NOW);
    await installApiFixture(page, state);
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'u12-browser-token');
      localStorage.setItem('migration_completed', 'true');
      localStorage.setItem('ink-language', 'zh');
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    await expect(page).toHaveURL(new RegExp(`/story-workspace/runs/${RUN_ID}/execution$`));
    expect(await page.evaluate(() => ({
      now: new Date().toISOString(),
      timezoneId: Intl.DateTimeFormat().resolvedOptions().timeZone,
    }))).toEqual({ now: FROZEN_NOW, timezoneId: 'Asia/Shanghai' });
    await expect(page.getByRole('heading', { name: '雨夜归途' }).first()).toBeVisible();
    const executionRoot = page.locator('.story-workspace-collaboration');
    const dreamDraft = page.getByRole('region', { name: 'Dream 初稿工作台' });
    const artifactWorkbench = page.getByRole('region', { name: 'Episode 产物工作台' });
    const openAgent = page.getByRole('button', { name: '打开 Dream Agent 消息预览' });
    const artifactReader = page.getByRole('region', { name: 'EP01 文件阅读器' });
    const creationGuideEntry = dreamDraft.getByRole('button', {
      name: '查看短剧创作阶段指引',
    });
    const draftEpisodeEntry = dreamDraft.getByRole('button')
      .filter({ hasText: 'EP01: 雨夜重逢' });
    await expect(dreamDraft).toBeVisible();
    await expect(artifactWorkbench).toHaveCount(0);
    await expect(artifactReader).toHaveCount(0);
    await expect(creationGuideEntry).toBeVisible();
    expect(await creationGuideEntry.evaluate((guide, episode) => (
      guide.compareDocumentPosition(episode) & Node.DOCUMENT_POSITION_FOLLOWING
    ) !== 0, await draftEpisodeEntry.elementHandle())).toBe(true);
    await creationGuideEntry.click();
    const creationGuide = page.getByRole('article', { name: '短剧创作流程' });
    await expect(creationGuide).toBeVisible();
    await expect(creationGuide.locator(
      '.story-workspace-creation-guide__stages > .story-workspace-creation-guide__stage',
    )).toHaveCount(3);
    await expect(creationGuide.getByRole('heading', { name: '建立项目与共享资产' }))
      .toBeVisible();
    await expect(creationGuide.getByRole('heading', { name: '逐集创作与审查' })).toBeVisible();
    await expect(creationGuide.getByRole('heading', { name: '渲染、后期与宣发' })).toBeVisible();
    await expect(creationGuide.getByText('Creation guide · Three stages')).toHaveCount(0);
    await expect(creationGuide.getByText('从共享资产到逐集成片')).toHaveCount(0);
    await expect(creationGuide.getByText('跨集复用', { exact: true })).toBeVisible();
    await expect(creationGuide.getByText('每个 EP 重复', { exact: true })).toBeVisible();
    await expect(creationGuide.getByText('尚未实现', { exact: true })).toBeVisible();
    for (const command of [
      '/drama-init',
      '/drama-plan',
      '/drama-asset',
      '/drama-script (EP01)',
      '/drama-storyboard (EP01)',
      '/drama-prompt (EP01)',
      '/script-reviewer',
      '/drama-render + /drama-voice',
      '/drama-edit',
      '/drama-promote',
    ]) await expect(creationGuide.getByText(command, { exact: true })).toBeVisible();
    const guideIllustrations = creationGuide.getByRole('img', { name: /Mimo/ });
    await expect(guideIllustrations).toHaveCount(3);
    for (let index = 0; index < 3; index += 1) {
      const illustration = guideIllustrations.nth(index);
      await expect(illustration).toBeVisible();
      expect(await illustration.evaluate((image) => ({
        complete: (image as HTMLImageElement).complete,
        naturalWidth: (image as HTMLImageElement).naturalWidth,
      }))).toEqual({ complete: true, naturalWidth: 887 });
    }
    const guideViewport = await page.locator('[data-execution-depth="focus"]')
      .evaluate((focus) => ({
        clientHeight: focus.clientHeight,
        overflow: focus.scrollHeight - focus.clientHeight,
        scrollHeight: focus.scrollHeight,
      }));
    expect(guideViewport.overflow).toBeLessThanOrEqual(1);
    await expect(artifactReader).toHaveCount(0);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'creation-guide-desktop-1440x1000.png'),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await expectNoHorizontalOverflow(page);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'creation-guide-narrow-390x844.png'),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole('button', { name: '← 返回故事线' }).click();
    await expect(creationGuide).toHaveCount(0);
    await expect(draftEpisodeEntry.locator('p')).toHaveText('1 镜、3 秒。');
    await expect(draftEpisodeEntry.locator('p')).not.toContainText('episode:');
    await draftEpisodeEntry.click();
    await expect(artifactReader).toBeVisible();
    await expect(dreamDraft.getByText('分镜概览', { exact: true })).toHaveCount(0);
    await expect(artifactReader.getByRole('tab', { name: /分镜/ }))
      .toHaveAttribute('aria-selected', 'true');
    await page.getByRole('button', { name: '← 返回故事线' }).click();
    await expect(artifactReader).toHaveCount(0);
    await openAgent.click();
    let agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(agentDialog.getByRole('button', { name: '初稿', exact: true }))
      .toHaveAttribute('aria-pressed', 'true');
    await agentDialog.getByRole('button', { name: '同步', exact: true }).click();
    await expect(agentDialog.getByRole('button', { name: '同步', exact: true }))
      .toHaveAttribute('aria-pressed', 'true');
    await agentDialog.getByRole('button', { name: '收起 Dream Agent' }).click();
    await expect(dreamDraft).toHaveCount(0);
    await expect(artifactWorkbench).toBeVisible();
    await expect(page.getByRole('heading', { name: '雨夜重逢' }).first()).toBeVisible();
    await expect(page.getByRole('status').filter({ hasText: 'EP01 产物关联：已关联' }))
      .toBeVisible();
    await expect(page.getByRole('tree', { name: 'Episode 故事线' })).toBeVisible();
    expect(await executionRoot.evaluate((root) => getComputedStyle(root).overflowY)).toBe('auto');
    const desktopScrollRange = await executionRoot.evaluate((root) => ({
      clientHeight: root.clientHeight,
      scrollHeight: root.scrollHeight,
    }));
    expect(desktopScrollRange.scrollHeight).toBeGreaterThanOrEqual(desktopScrollRange.clientHeight);
    const artifactProgress = page.getByRole('list', { name: 'EP01 产物进度' });
    await expect(artifactProgress.getByRole('button')).toHaveCount(4);
    await expect(artifactProgress.getByRole('button', { name: '阅读Prompts' })).toHaveCount(0);
    await expect(artifactProgress.getByRole('button', { name: '阅读渲染指引' })).toHaveCount(0);
    await expect(artifactProgress.getByText('Prompts', { exact: true })).toBeVisible();
    await expect(artifactProgress.getByText('渲染指引', { exact: true })).toBeVisible();
    await expect(artifactProgress.getByText('Renders', { exact: true })).toHaveCount(0);
    await expect(artifactProgress.locator('li').filter({ hasText: '渲染指引' }))
      .toContainText('已准备');
    await expect(artifactProgress.getByText('审阅报告', { exact: true })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    const columns = await page.locator('[aria-label="Episode 主工作面"] > *')
      .evaluateAll((elements) => elements.map((element) => element.getBoundingClientRect().x));
    expect(columns).toHaveLength(2);
    expect(columns[0]).toBeLessThan(columns[1]);
    await expect(page.locator('[aria-label="Episode 内容工作面"] [aria-label="Episode 辅助视图"]'))
      .toBeVisible();

    await openAgent.click();
    agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(agentDialog).toBeVisible();
    await expect(agentDialog.getByText('Episode 下一步')).toHaveCount(0);
    await expect(agentDialog.getByText('更多工作流操作')).toHaveCount(0);
    await expectDreamAgentConversationLayout(page);
    const workbenchScrollLimit = await executionRoot.evaluate(
      (root) => Math.max(0, root.scrollHeight - root.clientHeight),
    );
    expect(workbenchScrollLimit).toBeGreaterThan(0);
    await executionRoot.evaluate((root) => root.scrollTo({ top: root.scrollHeight }));
    await expect.poll(() => executionRoot.evaluate((root) => root.scrollTop))
      .toBeGreaterThan(0);
    await expectDreamAgentConversationLayout(page);
    await executionRoot.evaluate((root) => root.scrollTo({
      top: Math.max(1, (root.scrollHeight - root.clientHeight) / 2),
    }));
    const scrollTopBeforeMessageOverscroll = await executionRoot.evaluate((root) => root.scrollTop);
    const messageScroller = agentDialog.locator('[data-chat-scroll-region="messages"]');
    await messageScroller.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
    await messageScroller.hover();
    await page.mouse.wheel(0, 1_200);
    expect(await executionRoot.evaluate((root) => root.scrollTop))
      .toBe(scrollTopBeforeMessageOverscroll);
    await expectDreamAgentConversationLayout(page);
    await page.screenshot({ path: resolve(EVIDENCE_DIR, 'dream-agent-desktop-1440x1000.png') });
    await page.getByRole('button', { name: '收起 Dream Agent' }).click();
    await expect(agentDialog).toBeHidden();
    await expect(openAgent).toBeFocused();

    let shot = await selectShotWithKeyboard(page);
    await expect(shot).toHaveAttribute('aria-current', 'true');
    await expect(page.getByText('雨夜车站。', { exact: true })).toBeVisible();
    await page.screenshot({ path: resolve(EVIDENCE_DIR, 'desktop-1440x1000.png'), fullPage: true });

    state.revisionIndex = 1;
    const readsBeforeRevision = state.artifactReads;
    await page.evaluate((runId) => {
      window.dispatchEvent(new CustomEvent('ink:story-workspace-output', {
        detail: { type: 'story-workspace-output', runId },
      }));
    }, RUN_ID);
    await expect.poll(() => state.artifactReads).toBeGreaterThan(readsBeforeRevision);
    shot = page.getByRole('treeitem', { name: 'S01-E01-C01-SH001', exact: true });
    await expect(shot).toHaveAttribute('aria-current', 'true');
    await expect(page.getByRole('article', { name: 'Shot Detail' })
      .getByText('雨夜车站，车灯从背景掠过。', { exact: true })).toBeVisible();

    await shot.press('Escape');
    await expect(page.getByRole('treeitem', { name: 'S01 车站外', exact: true }))
      .toHaveAttribute('aria-current', 'true');

    await page.getByRole('treeitem', { name: '雨夜重逢', exact: true }).click();
    await expect(artifactProgress).toBeVisible();
    const readOutline = artifactProgress.getByRole('button', { name: '阅读分集大纲' });
    await readOutline.focus();
    await readOutline.press('Enter');
    await expect(artifactWorkbench).toHaveCount(0);
    await expect(dreamDraft).toBeVisible();
    await expect(artifactReader).toBeVisible();
    await expect(artifactReader).toBeInViewport();
    await expect(artifactReader.getByRole('tab', { name: /分集大纲/ }))
      .toHaveAttribute('aria-selected', 'true');
    await expect(artifactReader.getByRole('tab', { name: /分集大纲/ })).toBeFocused();
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'draft-episode-reader-desktop-1440x1000.png'),
      fullPage: true,
    });

    const readsBeforeReload = state.artifactReads;
    await page.reload();
    await expect(dreamDraft).toBeVisible();
    await expect(artifactReader).toHaveCount(0);
    await draftEpisodeEntry.click();
    await expect(artifactReader).toBeVisible();
    await expect.poll(() => state.artifactReads).toBeGreaterThan(readsBeforeReload);
    await page.getByRole('button', { name: '← 返回故事线' }).click();
    await openAgent.click();
    agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await agentDialog.getByRole('button', { name: '同步', exact: true }).click();
    await agentDialog.getByRole('button', { name: '收起 Dream Agent' }).click();
    await expect(agentDialog).toBeHidden();
    await expect(openAgent).toBeFocused();
    await expect(page.getByRole('tree', { name: 'Episode 故事线' })).toBeVisible();
    await expect(artifactReader).toHaveCount(0);
    await selectShotWithKeyboard(page);
    await expect(page.getByRole('article', { name: 'Shot Detail' })
      .getByText('雨夜车站，车灯从背景掠过。', { exact: true }))
      .toBeVisible();

    await page.setViewportSize({ width: 390, height: 844 });
    await expectNoHorizontalOverflow(page);
    expect(await executionRoot.evaluate((root) => getComputedStyle(root).overflowY)).toBe('auto');
    const narrowScrollRange = await executionRoot.evaluate((root) => ({
      clientHeight: root.clientHeight,
      scrollHeight: root.scrollHeight,
    }));
    expect(narrowScrollRange.scrollHeight).toBeGreaterThanOrEqual(narrowScrollRange.clientHeight);
    const storylineToggle = page.getByRole('button', { name: '打开故事线' });
    await expect(storylineToggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.getByRole('tree', { name: 'Episode 故事线' })).toBeHidden();
    const visibleActions = page.locator('.story-workspace-collaboration button:visible');
    for (let index = 0; index < await visibleActions.count(); index += 1) {
      const box = await visibleActions.nth(index).boundingBox();
      if (box === null) continue;
      expect(box.width).toBeGreaterThanOrEqual(44);
      expect(box.height).toBeGreaterThanOrEqual(44);
      expect(box.x).toBeGreaterThanOrEqual(71);
      expect(box.x + box.width).toBeLessThanOrEqual(391);
    }
    await page.screenshot({ path: resolve(EVIDENCE_DIR, 'narrow-390x844.png'), fullPage: true });

    await openAgent.click();
    await expect(agentDialog).toBeVisible();
    await expect(agentDialog).toBeInViewport();
    await expectDreamAgentConversationLayout(page);
    await page.screenshot({ path: resolve(EVIDENCE_DIR, 'dream-agent-narrow-390x844.png') });
    await agentDialog.getByRole('button', { name: '初稿', exact: true }).click();
    await expect(agentDialog).toBeHidden();
    await expect(openAgent).toBeFocused();
    await expect(dreamDraft).toBeVisible();
    await expect(artifactWorkbench).toHaveCount(0);
    await openAgent.click();
    await agentDialog.getByRole('button', { name: '同步', exact: true }).click();
    await expect(agentDialog).toBeHidden();
    await expect(artifactWorkbench).toBeVisible();

    await storylineToggle.click();
    const storylineSheet = page.getByRole('dialog', { name: '故事线' });
    await expect(storylineSheet).toBeVisible();
    const activeStorylineItem = storylineSheet.locator('[role="treeitem"][tabindex="0"]');
    await expect(activeStorylineItem).toBeFocused();
    await page.screenshot({ path: resolve(EVIDENCE_DIR, 'narrow-storyline-390x844.png') });
    await page.keyboard.press('Tab');
    await expect(storylineSheet.getByRole('button', { name: '关闭故事线' })).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expect(activeStorylineItem).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(storylineSheet).toBeHidden();
    await expect(storylineToggle).toBeFocused();

    const bodyText = await page.locator('body').innerText();
    for (const forbidden of [
      '/drama-forge:',
      'hidden reasoning',
      '隐藏推理',
      '原始工具参数',
      'ChatView',
    ]) expect(bodyText).not.toContain(forbidden);
    expect(readFileSync(resolve(
      process.cwd(),
      'src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx',
    ), 'utf8')).not.toContain('<ChatView');
    expect(diagnostics).toEqual([]);
  } finally {
    await context.tracing.stop({ path: resolve(EVIDENCE_DIR, 'trace.zip') });
  }
});
