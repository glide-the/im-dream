// [Input] Deterministic actor-scoped Dream/Episode REST snapshots served at the browser boundary.
// [Output] Chromium evidence for responsive Episode navigation, recovery, and revision-stable selection.
// [Pos] Story Workspace Episode Execution mocked-browser QA (U12); never claims external workflow success.

// @ts-expect-error Playwright E2E has Node built-ins; the browser app tsconfig omits Node types.
import { mkdirSync, readFileSync } from 'node:fs';
// @ts-expect-error Playwright E2E has Node built-ins; the browser app tsconfig omits Node types.
import { resolve } from 'node:path';
import { expect, test, type Locator, type Page, type Route } from '@playwright/test';
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
const ACTION_IDS = Array.from(
  { length: 7 },
  (_, index) => `episode_action_${String(index + 1).repeat(64)}`,
);
const NEXT_EPISODE_CANDIDATE_ID = `episode_candidate_${'8'.repeat(64)}`;
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
          summary: '第一集详细分镜。',
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
    status: 'continuing',
    status_version: 2,
    failed_step: null,
    error_code: null,
    retry_of_run_id: null,
    created_at: '2026-08-06T01:00:00Z',
    started_at: '2026-08-06T01:00:01Z',
    completed_at: null,
  };
}

function dreamAgentSnapshot(
  pendingToolConfirmations: Array<{
    toolCallId: string;
    kind: 'approval';
    toolName: string;
  }> = [],
  lifecycleOverride?: 'idle' | 'streaming',
) {
  const isWaitingForToolConfirmation = pendingToolConfirmations.length > 0;
  const lifecycle = lifecycleOverride
    ?? (isWaitingForToolConfirmation ? 'streaming' : 'idle');
  const isRunning = lifecycle === 'streaming';
  return {
    storyWorkspaceRunId: RUN_ID,
    lifecycle,
    activeTurnId: isWaitingForToolConfirmation
      ? 'turn-u12-confirmation'
      : isRunning ? 'turn-u12-running' : null,
    canSend: !isWaitingForToolConfirmation && !isRunning,
    sendBlockReason: isWaitingForToolConfirmation || isRunning ? 'busy' : null,
    toolConfirmationObservation: 'known',
    messages: [{
      id: 'message-u12-browser',
      role: 'assistant',
      text: '第一集产物已同步到工作台。',
      truncated: false,
      content: [{ kind: 'text', text: '第一集产物已同步到工作台。', truncated: false }],
      createdAt: '2026-08-06T01:04:00Z',
    }],
    pendingToolConfirmations,
    snapshotAt: '2026-08-06T01:04:01Z',
  };
}

function projectedAction(
  index: number,
  action: 'generate_prompts' | 'regenerate_storyboard' | 'review_full_chain'
    | 'validate_episode' | 'prepare_render_guide' | 'plan_episode' | 'write_script',
  label: string,
  displayCommand: string,
  availability: 'executable' | 'preview' | 'blocked',
  target: 'current' | 'next' = 'current',
) {
  const executable = availability === 'executable';
  return {
    actionId: ACTION_IDS[index],
    action,
    inputRevision: CONTENT_REVISION,
    targetEpisode: target === 'current' ? {
      opaqueEpisodeId: EPISODE_ID,
      candidateId: null,
      displayLabel: 'EP01',
      relation: 'current',
    } : {
      opaqueEpisodeId: null,
      candidateId: NEXT_EPISODE_CANDIDATE_ID,
      displayLabel: 'EP02',
      relation: 'next',
    },
    label,
    description: target === 'current'
      ? '使用服务端确认的 EP01 canonical revisions。'
      : '等待 EP01 完整产物校验后开始 EP02。',
    displayCommand,
    availability,
    isRecommended: index === 0,
    canDispatch: executable,
    disabledReason: executable ? null : target === 'next'
      ? '完成 EP01 完整产物校验后可用'
      : '完成当前 EP01 步骤后可用',
    canonicalInputs: [{
      sourceType: 'episode_artifact',
      artifact: action === 'regenerate_storyboard' ? 'script' : 'storyboard',
      owner: 'episode_artifact_manifest',
      label: target === 'current' ? 'EP01 canonical 输入' : 'EP02 前置输入',
      availability: executable ? 'available' : 'not_generated',
      publicRevision: executable ? CONTENT_REVISION : null,
      revisionKind: 'content',
      requirement: 'required',
    }],
    consequences: action === 'regenerate_storyboard'
      ? ['Prompt 包', '完整产物审阅', '校验提交']
      : [],
    dispatchState: 'idle',
  };
}

function episodeSurface(revisionIndex: 0 | 1) {
  const revision = MANIFEST_REVISIONS[revisionIndex];
  return {
    runId: RUN_ID,
    opaqueEpisodeId: EPISODE_ID,
    manifestRevision: revision,
    etag: AGGREGATE_ETAGS[revisionIndex],
    bindingAvailability: 'bound',
    bindingRecovery: {
      autoRepairAttempted: false,
      canDispatch: false,
      publicReason: null,
    },
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
    workflow: {
      factsRevision: revisionIndex,
      nextAction: { action: 'generate_prompts', diagnostic: 'needs_confirmation', canDispatch: true },
      prerequisites: ['regenerate_storyboard'],
      actionOptions: [
        {
          action: 'generate_prompts',
          label: '生成 EP01 Prompt 包',
          displayCommand: '/drama-prompt (EP01)',
          isCurrent: true,
          canDispatch: true,
        },
        {
          action: 'review_full_chain',
          label: '审阅 EP01 完整产物',
          displayCommand: '完整链路审查',
          isCurrent: false,
          canDispatch: false,
        },
        {
          action: 'validate_episode',
          label: '校验并提交 EP01',
          displayCommand: '校验完整产物',
          isCurrent: false,
          canDispatch: false,
        },
        {
          action: 'prepare_render_guide',
          label: '准备 EP01 渲染与配音指引',
          displayCommand: '/drama-render + /drama-voice',
          isCurrent: false,
          canDispatch: false,
        },
      ],
      legacyPartial: false,
    },
    actionProjection: {
      recommendedActionId: ACTION_IDS[0],
      actionOptions: [
        projectedAction(0, 'generate_prompts', '生成 EP01 Prompt 包', '/drama-prompt (EP01)', 'executable'),
        projectedAction(1, 'regenerate_storyboard', '基于最新剧本更新 EP01 详细分镜', '/drama-storyboard (EP01)', 'executable'),
        projectedAction(2, 'review_full_chain', '审阅 EP01 完整产物', 'script-reviewer · EP01 完整链路', 'preview'),
        projectedAction(3, 'validate_episode', '校验并提交 EP01', '校验并提交 · EP01', 'preview'),
        projectedAction(4, 'prepare_render_guide', '准备 EP01 渲染与配音指引', '/drama-render + /drama-voice · EP01', 'preview'),
        projectedAction(5, 'plan_episode', '开始 EP02 分集规划', '/drama-plan', 'blocked', 'next'),
        projectedAction(6, 'write_script', '创作 EP02 剧本', '/drama-script (EP02)', 'preview', 'next'),
      ],
    },
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
  continueRequests: Array<Record<string, unknown>>;
  dreamAgentLifecycle?: 'idle' | 'streaming';
  pendingToolConfirmations: Array<{
    toolCallId: string;
    kind: 'approval';
    toolName: string;
  }>;
  toolConfirmationRequests: Array<Record<string, unknown>>;
  toolConfirmationTerminal?: {
    readonly wait: Promise<void>;
    readonly resolve: () => void;
  };
};

function deferredBrowserSignal(): { wait: Promise<void>; resolve: () => void } {
  let resolve = () => undefined;
  const wait = new Promise<void>((done) => { resolve = done; });
  return { wait, resolve };
}

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
    if (matches('GET', '/api/me')) {
      await json(route, { id: 12, email: 'u12@example.test', display_name: 'U12 QA' });
      return;
    }
    if (matches('GET', '/api/default-voices')) {
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
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/events`)) {
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': ready\n\n' });
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`)) {
      await json(route, dreamFiles());
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/messages`)) {
      await json(route, dreamAgentSnapshot(
        state.pendingToolConfirmations,
        state.dreamAgentLifecycle,
      ));
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/events`)) {
      if (state.toolConfirmationTerminal) {
        await state.toolConfirmationTerminal.wait;
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'event: status\ndata: {"lifecycle":"idle"}\n\n',
        });
      } else {
        await route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': ready\n\n' });
      }
      return;
    }
    if (matches('POST', `/api/story-workspace/workflow-runs/${RUN_ID}/dream-agent/tool-confirm`)) {
      const payload = request.postDataJSON() as Record<string, unknown>;
      state.toolConfirmationRequests.push(payload);
      state.pendingToolConfirmations = state.pendingToolConfirmations.filter(
        (item) => item.toolCallId !== payload.toolCallId,
      );
      state.toolConfirmationTerminal?.resolve();
      await json(route, {
        storyWorkspaceRunId: RUN_ID,
        toolCallId: payload.toolCallId,
        resolved: true,
      });
      return;
    }
    if (matches('POST', `/api/story-workspace/workflow-runs/${RUN_ID}/episode-actions/continue`)) {
      state.continueRequests.push(request.postDataJSON() as Record<string, unknown>);
      await json(route, {
        runId: RUN_ID,
        episodeId: EPISODE_ID,
        capability: 'generate_prompts',
        messageId: 'dream-agent-u12-continue',
        accepted: true,
        replayed: false,
      }, 202);
      return;
    }
    if (matches('GET', `/api/story-workspace/workflow-runs/${RUN_ID}/episode-artifacts`)) {
      state.artifactReads += 1;
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
      return element !== null && element.scrollWidth <= element.clientWidth + 1;
    })(),
  }))).toEqual({ document: true, body: true, workbench: true });
}

async function expectNoDocumentHorizontalOverflow(page: Page) {
  expect(await page.evaluate(() => ({
    document: document.documentElement.scrollWidth <= window.innerWidth + 1,
    body: document.body.scrollWidth <= window.innerWidth + 1,
  }))).toEqual({ document: true, body: true });
}

async function expectConfirmationActionsInViewport(
  page: Page,
  confirmation: Locator,
  minimumButtonHeight = 0,
) {
  const viewport = page.viewportSize();
  expect(viewport).not.toBeNull();
  for (const buttonName of ['拒绝', '允许本次操作']) {
    const action = confirmation.getByRole('button', { name: buttonName });
    await expect(action).toBeInViewport();
    const box = await action.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.x ?? -1).toBeGreaterThanOrEqual(0);
    expect(box?.y ?? -1).toBeGreaterThanOrEqual(0);
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual((viewport?.width ?? 0) + 1);
    expect((box?.y ?? 0) + (box?.height ?? 0)).toBeLessThanOrEqual((viewport?.height ?? 0) + 1);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(minimumButtonHeight);
  }
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

test('mocked REST facts recover responsively and preserve the selected shot across revisions', async ({
  context,
  page,
}) => {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const diagnostics: string[] = [];
  const state: BrowserFixtureState = {
    revisionIndex: 0,
    artifactReads: 0,
    continueRequests: [],
    pendingToolConfirmations: [],
    toolConfirmationRequests: [],
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
    await expect(page.getByRole('heading', { name: '雨夜重逢' }).first()).toBeVisible();
    await expect(page.getByRole('tree', { name: 'Episode 故事线' })).toBeVisible();
    const executionRoot = page.locator('.story-workspace-collaboration');
    const dreamProjection = page.locator('details').filter({ hasText: 'Dream 初稿阶段投影' });
    const artifactWorkbench = page.locator('section[aria-label="第一集产物工作台"]');
    await expect(dreamProjection).toHaveCount(1);
    await expect(artifactWorkbench).toHaveCount(1);
    expect(await dreamProjection.evaluate((projection) => {
      const artifact = document.querySelector('section[aria-label="第一集产物工作台"]');
      return artifact !== null && Boolean(
        projection.compareDocumentPosition(artifact) & Node.DOCUMENT_POSITION_FOLLOWING
      );
    })).toBe(true);
    expect(await dreamProjection.evaluate((projection) => (
      (projection as HTMLDetailsElement).open
    ))).toBe(false);
    expect(await executionRoot.evaluate((root) => getComputedStyle(root).overflowY)).toBe('auto');
    const desktopScrollRange = await executionRoot.evaluate((root) => ({
      clientHeight: root.clientHeight,
      scrollHeight: root.scrollHeight,
    }));
    expect(desktopScrollRange.scrollHeight).toBeGreaterThanOrEqual(desktopScrollRange.clientHeight);
    const artifactProgress = page.getByRole('list', { name: '第一集产物进度' });
    await expect(artifactProgress.getByRole('button')).toHaveCount(4);
    await expect(artifactProgress.getByRole('button', { name: '阅读Prompts' })).toHaveCount(0);
    await expect(artifactProgress.getByRole('button', { name: '阅读渲染指引' })).toHaveCount(0);
    const readOutline = artifactProgress.getByRole('button', { name: '阅读分集大纲' });
    await readOutline.focus();
    await readOutline.press('Enter');
    expect(await dreamProjection.evaluate((projection) => (
      (projection as HTMLDetailsElement).open
    ))).toBe(true);
    const artifactReader = page.getByRole('region', { name: '第一集文件阅读器' });
    await expect(artifactReader).toBeVisible();
    await expect(artifactReader).toBeInViewport();
    await expect(artifactReader.getByRole('tab', { name: /分集大纲/ }))
      .toHaveAttribute('aria-selected', 'true');
    await expect(artifactReader.getByRole('tab', { name: /分集大纲/ })).toBeFocused();
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

    const openAgent = page.getByRole('button', { name: '打开 Dream Agent 消息预览' });
    await openAgent.click();
    let agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(agentDialog.getByRole('button', { name: /生成 EP01 Prompt 包.*推荐操作.*当前可执行/ }))
      .toBeEnabled();
    const storyboardAction = agentDialog.getByRole('button', {
      name: /基于最新剧本更新 EP01 详细分镜.*当前可执行/,
    });
    await expect(storyboardAction).toBeEnabled();
    const workflowDisclosure = agentDialog.getByRole('button', {
      name: '更多工作流操作（5）',
    });
    await expect(workflowDisclosure).toHaveAttribute('aria-expanded', 'false');
    await workflowDisclosure.click();
    await expect(agentDialog.getByRole('button', {
      name: /开始 EP02 分集规划.*暂不可用/,
    })).toBeDisabled();
    await page.keyboard.press('Escape');
    await storyboardAction.click();
    let continueDialog = page.getByRole('dialog', { name: '确认 Episode 下一步' });
    await expect(continueDialog.getByText('目标 Episode：EP01')).toBeVisible();
    await expect(continueDialog.getByText('EP01 canonical 输入')).toBeVisible();
    await continueDialog.getByRole('button', { name: '取消' }).click();
    agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(agentDialog.getByRole('button', {
      name: /基于最新剧本更新 EP01 详细分镜.*当前可执行/,
    })).toBeFocused();
    await page.keyboard.press('Escape');

    let continueAction = page.getByRole('button', { name: '生成 EP01 Prompt 包' });
    await continueAction.click();
    continueDialog = page.getByRole('dialog', { name: '确认 Episode 下一步' });
    await expect(continueDialog).toBeVisible();
    await expect(continueDialog.getByText('Canonical 输入与 revisions')).toBeVisible();
    const guidance = continueDialog.getByRole('textbox', { name: '补充创作要求（可选）' });
    await expect(guidance).toBeFocused();
    await guidance.press('Escape');
    await expect(continueDialog).toBeHidden();
    await expect(continueAction).toBeFocused();

    await continueAction.click();
    await guidance.fill('  保留克制感  ');
    await continueDialog.getByRole('button', { name: '确认并继续' }).click();
    await expect(continueDialog).toBeHidden();
    expect(state.continueRequests).toHaveLength(1);
    expect(state.continueRequests[0]).toMatchObject({
      actionId: ACTION_IDS[0],
      userGuidance: '保留克制感',
    });
    expect(state.continueRequests[0]).not.toHaveProperty('action');
    expect(state.continueRequests[0]).not.toHaveProperty('episodeId');
    expect(state.continueRequests[0]).not.toHaveProperty('displayCommand');
    continueAction = page.getByRole('button', { name: '已交给 Dream Agent' });
    await expect(continueAction).toBeDisabled();

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
    await expect(page.getByText('雨夜车站，车灯从背景掠过。', { exact: true })).toBeVisible();
    expect(await dreamProjection.evaluate((projection) => (
      (projection as HTMLDetailsElement).open
    ))).toBe(true);
    continueAction = page.getByRole('button', { name: '生成 EP01 Prompt 包' });
    await expect(continueAction).toBeEnabled();

    await shot.press('Escape');
    await expect(page.getByRole('treeitem', { name: 'S01 车站外', exact: true }))
      .toHaveAttribute('aria-current', 'true');

    const readsBeforeReload = state.artifactReads;
    await page.reload();
    await expect(page.getByRole('tree', { name: 'Episode 故事线' })).toBeVisible();
    await expect.poll(() => state.artifactReads).toBeGreaterThan(readsBeforeReload);
    await expect(page.getByText('雨夜车站，车灯从背景掠过。', { exact: true }))
      .toHaveCount(0);
    await selectShotWithKeyboard(page);
    await expect(page.getByText('雨夜车站，车灯从背景掠过。', { exact: true }))
      .toBeVisible();

    await page.setViewportSize({ width: 390, height: 844 });
    await expectNoHorizontalOverflow(page);
    expect(await executionRoot.evaluate((root) => getComputedStyle(root).overflowY)).toBe('auto');
    const narrowScrollRange = await executionRoot.evaluate((root) => ({
      clientHeight: root.clientHeight,
      scrollHeight: root.scrollHeight,
    }));
    expect(narrowScrollRange.scrollHeight).toBeGreaterThanOrEqual(narrowScrollRange.clientHeight);
    await continueAction.scrollIntoViewIfNeeded();
    await expect(continueAction).toBeInViewport();
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

    await continueAction.click();
    await expect(continueDialog).toBeVisible();
    await expect(guidance).toBeFocused();
    const dialogBox = await continueDialog.boundingBox();
    expect(dialogBox).not.toBeNull();
    expect(dialogBox?.x).toBeGreaterThanOrEqual(9);
    expect(dialogBox?.y).toBeGreaterThanOrEqual(9);
    expect((dialogBox?.x ?? 0) + (dialogBox?.width ?? 0)).toBeLessThanOrEqual(381);
    expect((dialogBox?.y ?? 0) + (dialogBox?.height ?? 0)).toBeLessThanOrEqual(835);
    await page.screenshot({ path: resolve(EVIDENCE_DIR, 'narrow-dialog-390x844.png') });
    await guidance.press('Escape');
    await expect(continueDialog).toBeHidden();
    await expect(continueAction).toBeFocused();

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

test('Dream Agent Panel restores a safe Write confirmation without exposing raw paths', async ({
  context,
  page,
}) => {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const diagnostics: string[] = [];
  const toolConfirmationTerminal = deferredBrowserSignal();
  const state: BrowserFixtureState = {
    revisionIndex: 0,
    artifactReads: 0,
    continueRequests: [],
    pendingToolConfirmations: [{
      toolCallId: 'tool-write-ep01',
      kind: 'approval',
      toolName: 'Write',
    }],
    toolConfirmationRequests: [],
    toolConfirmationTerminal,
  };
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    const url = request.url();
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')
      && !url.includes('react-grab.com')) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  try {
    await page.clock.setFixedTime(FROZEN_NOW);
    await installApiFixture(page, state);
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'u12-browser-token');
      localStorage.setItem('migration_completed', 'true');
      localStorage.setItem('ink-language', 'zh');
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);

    const openAgent = page.getByRole('button', {
      name: '打开 Dream Agent：等待你确认一项操作',
    });
    await expect(openAgent).toBeVisible();
    await expect(page.getByRole('status').filter({
      hasText: 'Dream Agent 等待你确认一项操作',
    })).toHaveCount(1);
    await openAgent.click();

    const confirmation = page.getByRole('region', {
      name: '允许 Dream Agent 使用 Write',
    });
    await expect(confirmation).toBeVisible();
    await expect(confirmation.getByRole('button', { name: '拒绝' })).toBeFocused();
    await expect(page.getByLabel('给 Dream Agent 留言')).toHaveCount(0);
    await expect(page.getByRole('alertdialog')).toHaveCount(0);
    await expect(page.locator([
      '[aria-label*="Allow I&M to call"]',
      '[aria-label*="/Users/"]',
      '[aria-label*="script.md"]',
    ].join(','))).toHaveCount(0);
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('/Users/');
    expect(bodyText).not.toContain('script.md');
    expect(bodyText).not.toContain('Allow I&M to call');
    const confirmationMarkup = await confirmation.evaluate((element) => element.outerHTML);
    expect(confirmationMarkup).not.toContain('/Users/');
    expect(confirmationMarkup).not.toContain('script.md');
    expect(confirmationMarkup).not.toContain('Allow I&amp;M to call');
    await expect(confirmation).toBeInViewport();
    await expectNoDocumentHorizontalOverflow(page);
    await expectConfirmationActionsInViewport(page, confirmation);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'dream-confirmation-desktop-1440x1000.png'),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(confirmation).toBeVisible();
    await expect(confirmation).toBeInViewport();
    await expectNoDocumentHorizontalOverflow(page);
    const confirmationBox = await confirmation.boundingBox();
    expect(confirmationBox).not.toBeNull();
    expect(confirmationBox?.x ?? -1).toBeGreaterThanOrEqual(0);
    expect(confirmationBox?.y ?? -1).toBeGreaterThanOrEqual(0);
    expect((confirmationBox?.x ?? 0) + (confirmationBox?.width ?? 0)).toBeLessThanOrEqual(391);
    expect((confirmationBox?.y ?? 0) + (confirmationBox?.height ?? 0)).toBeLessThanOrEqual(845);
    await expectConfirmationActionsInViewport(page, confirmation, 44);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'dream-confirmation-narrow-390x844.png'),
      fullPage: true,
    });

    await confirmation.getByRole('button', { name: '允许本次操作' }).click();
    await expect(confirmation).toHaveCount(0);
    await expect(page.getByLabel('给 Dream Agent 留言')).toBeFocused();
    expect(state.toolConfirmationRequests).toEqual([{
      toolCallId: 'tool-write-ep01',
      approved: true,
    }]);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.tracing.stop({
      path: resolve(EVIDENCE_DIR, 'dream-confirmation-trace.zip'),
    });
  }
});

test('Dream editor uses its proofing rail and both Agent surfaces share the running marker', async ({
  page,
}) => {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const diagnostics: string[] = [];
  const state: BrowserFixtureState = {
    revisionIndex: 0,
    artifactReads: 0,
    continueRequests: [],
    dreamAgentLifecycle: 'streaming',
    pendingToolConfirmations: [],
    toolConfirmationRequests: [],
  };
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    const url = request.url();
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

  const editor = page.locator('aside[aria-label="Dream 内容编辑器"]');
  await page.getByRole('navigation', { name: 'Dream 文件模块' })
    .getByRole('button', { name: /分镜/ })
    .click();
  await expect(editor.getByRole('heading', { name: '修改当前内容' })).toBeVisible();
  await expect(editor.locator('.story-workspace-dream__editor-fields')).toBeVisible();
  await expect(editor.locator('.story-workspace-dream__editor-footer')).toBeVisible();
  const editorBox = await editor.boundingBox();
  expect(editorBox).not.toBeNull();
  expect(editorBox?.width ?? 0).toBeGreaterThanOrEqual(440);
  await expectNoDocumentHorizontalOverflow(page);
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'dream-editor-proofing-desktop-1440x1000.png'),
  });

  await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  const panel = page.getByRole('region', { name: 'Dream Agent 完整消息' });
  const panelRunningMarker = panel.getByRole('button', { name: 'Dream Agent 正在运行' });
  await expect(panel).toBeVisible();
  await expect(panelRunningMarker).toBeVisible();
  await expect(panelRunningMarker).toBeDisabled();
  await expect(panelRunningMarker.locator('svg rect')).toHaveCount(1);
  await expect(editor).toHaveAttribute('data-agent-open', 'true');
  const openEditorBox = await editor.boundingBox();
  expect(openEditorBox).not.toBeNull();
  expect(openEditorBox?.width ?? 0).toBeGreaterThanOrEqual(540);
  expect(await panel.evaluate((element) => {
    const historyShell = element.querySelector<HTMLElement>(
      '.story-workspace-dream-agent-panel__history-shell',
    );
    const history = element.querySelector<HTMLElement>(
      '.story-workspace-dream-agent-panel__history',
    );
    const composer = element.querySelector<HTMLElement>('form');
    return {
      historyHeight: history?.getBoundingClientRect().height ?? 0,
      historyOverflowY: history ? getComputedStyle(history).overflowY : '',
      historyShellMaxHeight: historyShell ? getComputedStyle(historyShell).maxHeight : '',
      composerHeight: composer?.getBoundingClientRect().height ?? 0,
    };
  })).toEqual(expect.objectContaining({
    historyOverflowY: 'auto',
    historyShellMaxHeight: 'none',
  }));
  const desktopPanelMetrics = await panel.evaluate((element) => {
    const history = element.querySelector<HTMLElement>(
      '.story-workspace-dream-agent-panel__history',
    );
    const composer = element.querySelector<HTMLElement>('form');
    return {
      historyHeight: history?.getBoundingClientRect().height ?? 0,
      composerHeight: composer?.getBoundingClientRect().height ?? 0,
    };
  });
  expect(desktopPanelMetrics.historyHeight).toBeGreaterThan(desktopPanelMetrics.composerHeight);
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'dream-agent-running-desktop-1440x1000.png'),
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(panelRunningMarker).toBeVisible();
  await expect(panelRunningMarker).toBeInViewport();
  await expectNoDocumentHorizontalOverflow(page);
  const narrowEditorBox = await editor.boundingBox();
  expect(narrowEditorBox).not.toBeNull();
  expect(narrowEditorBox?.x ?? -1).toBeGreaterThanOrEqual(0);
  expect((narrowEditorBox?.x ?? 0) + (narrowEditorBox?.width ?? 0)).toBeLessThanOrEqual(391);
  const narrowHistoryMaxHeight = await panel.locator(
    '.story-workspace-dream-agent-panel__history-shell',
  ).evaluate((element) => Number.parseFloat(getComputedStyle(element).maxHeight));
  expect(narrowHistoryMaxHeight).toBeLessThanOrEqual(0.42 * 844 + 1);
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'dream-agent-running-narrow-390x844.png'),
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
  await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  const dialog = page.getByRole('dialog', { name: 'Dream Agent' });
  const dialogRunningMarker = dialog.getByRole('button', { name: 'Dream Agent 正在运行' });
  await expect(dialogRunningMarker).toBeVisible();
  await expect(dialogRunningMarker).toBeDisabled();
  await expect(dialogRunningMarker.locator('svg rect')).toHaveCount(1);
  await expectNoDocumentHorizontalOverflow(page);
  await page.screenshot({
    path: resolve(EVIDENCE_DIR, 'dream-agent-dialog-running-desktop-1440x1000.png'),
  });
  expect(diagnostics).toEqual([]);
});
