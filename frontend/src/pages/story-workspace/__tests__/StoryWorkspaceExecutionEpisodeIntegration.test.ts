// [Input] Execution Page source and its pure Episode action session seam.
// [Output] Deterministic integration guards for U5-U10 composition and revision-stable UI state.
// [Pos] Story Workspace Execution Episode integration Node seam (Task 3 U11).

// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { readFileSync } from 'node:fs';
// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { createServer } from 'vite';

const PAGE_SOURCE = readFileSync(new URL(
  '../StoryWorkspaceExecutionPage.tsx',
  import.meta.url,
), 'utf8');

test('composes the authoritative Episode query, U6 view model and U7-U9 workbench', () => {
  for (const expected of [
    'useStoryWorkspaceEpisodeArtifacts',
    'storyWorkspaceBuildEpisodeExecutionViewModel',
    'storyWorkspaceReconcileEpisodeSelection',
    '<StoryWorkspaceEpisodeNarrativeWorkbench',
    '<StoryWorkspaceEpisodeShotAuxiliary',
    '<StoryWorkspaceEpisodeReviewPanel',
    'promptsByShotViewId',
    'renderQueueByShotViewId',
    'onLocateTarget={setEpisodeSelection}',
  ]) expect(PAGE_SOURCE).toContain(expected);
});

test('keeps Dream confirmation and Agent preview boundaries without browser-owned truth', () => {
  for (const expected of [
    'storyWorkspaceCanAccessExecution',
    '<StoryWorkspaceDreamAgentDialog',
    'Dream Agent 消息预览',
  ]) expect(PAGE_SOURCE).toContain(expected);
  for (const forbidden of [
    '<ChatView',
    'localStorage',
    'sessionStorage',
    'key={episodeSurface.manifestRevision',
    'key={episodeSurface.etag',
  ]) expect(PAGE_SOURCE).not.toContain(forbidden);
});

test('shows honest loading, unbound, invalid and last-good states', () => {
  for (const expected of [
    '正在读取第一集产物…',
    '尚未建立可信的第一集关联',
    '恢复第一集关联',
    '尚未生成',
    '来源无效',
    '最近一次有效内容',
  ]) expect(PAGE_SOURCE).toContain(expected);
});

test('dispatches only U10F recovery and continuation with the current surface', () => {
  expect(PAGE_SOURCE).toContain('storyWorkspaceRecoverEpisodeBinding(runId, episodeSurface');
  expect(PAGE_SOURCE).toContain('storyWorkspaceContinueEpisodeAction(runId, episodeSurface');
  expect(PAGE_SOURCE).not.toMatch(/storyWorkspaceContinueEpisodeAction\([^)]*\{\s*action\s*:/s);
  expect(PAGE_SOURCE).not.toMatch(/storyWorkspaceRecoverEpisodeBinding\([^)]*\{[^}]*\b(?:story|path|episode)\s*:/s);
});

test('opens a dedicated Episode confirmation before continuation and never substitutes Agent chat', () => {
  for (const expected of [
    '<StoryWorkspaceEpisodeContinueDialog',
    'setEpisodeContinueDialogOpen(true)',
    'canonicalInputs={storyWorkspaceEpisodeCanonicalInputs(episodeSurface)}',
    'handleEpisodeContinue(userGuidance)',
    'setEpisodeContinueDialogOpen(false)',
  ]) expect(PAGE_SOURCE).toContain(expected);
  const continueHandler = PAGE_SOURCE.slice(
    PAGE_SOURCE.indexOf('const handleEpisodeContinue'),
    PAGE_SOURCE.indexOf('const selectedEpisodeShot'),
  );
  expect(continueHandler).not.toContain('setAgentDialogOpen(true)');
  expect(continueHandler).not.toContain('markAccepted');
});

test('holds accepted identity until REST facts change and announces reconcile focus movement', () => {
  for (const expected of [
    'episodeDispatchedIdentity === episodeActionIdentity',
    '当前镜头已在新版本中移除',
    'aria-live="polite"',
    'pendingEpisodeFocusKeyRef',
    'querySelector<HTMLButtonElement>',
    'storyWorkspaceEpisodeEscapeSelection(',
    '.navigationParent',
  ]) expect(PAGE_SOURCE).toContain(expected);
});

test('keeps selection and expansion session-only and reconciles instead of remounting by revision', () => {
  expect(PAGE_SOURCE).toContain('useStoryWorkspaceEpisodeRevisionSelection(');
  expect(PAGE_SOURCE).toContain('useState<ReadonlySet<string>>');
  expect(PAGE_SOURCE).toContain('storyWorkspaceReconcileEpisodeSelection(');
  expect(PAGE_SOURCE).not.toMatch(/setEpisodeSelection\(storyWorkspaceEpisodeDefaultSelection[^)]*\).*manifestRevision/s);
});

test('allowlists visible next-action labels and reuses idempotency only for one pending fact', async () => {
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
  try {
    const module = await server.ssrLoadModule(
      '/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx',
    ) as {
      readonly StoryWorkspaceEpisodeActionSessionKeys: new (
        createKey: () => string,
      ) => {
        keyFor(runId: string, fact: string, action: string): string;
      };
      readonly storyWorkspaceNormalizeEpisodeGuidance: (value: string) => string | null;
      readonly storyWorkspaceEpisodeCanonicalInputs: (surface: {
        readonly artifacts: ReadonlyArray<{
          readonly relativeKey: string;
          readonly availability: string;
          readonly contentRevision: string | null;
        }>;
      }) => ReadonlyArray<{
        readonly label: string;
        readonly availability: string;
        readonly revision: string | null;
      }>;
      readonly storyWorkspaceEpisodeEscapeSelection: (
        viewModel: unknown,
        expandedKeys: ReadonlySet<string>,
        selection: { readonly kind: string; readonly id: string },
      ) => { readonly kind: string; readonly id: string };
      readonly storyWorkspaceEpisodeNextActionLabel: (action: string) => string | null;
    };
    const generated = ['key-1', 'key-2', 'key-3'];
    const keys = new module.StoryWorkspaceEpisodeActionSessionKeys(
      () => generated.shift() ?? 'unexpected',
    );

    expect(keys.keyFor('run-a', 'etag-1', 'write_script')).toBe('key-1');
    expect(keys.keyFor('run-a', 'etag-1', 'write_script')).toBe('key-1');
    expect(keys.keyFor('run-a', 'etag-2', 'write_script')).toBe('key-2');
    expect(keys.keyFor('run-a', 'etag-2', 'write_script')).toBe('key-2');
    expect(keys.keyFor('run-a', 'etag-2', 'review_script')).toBe('key-3');

    expect(module.storyWorkspaceNormalizeEpisodeGuidance('  保留克制感  ')).toBe('保留克制感');
    expect(module.storyWorkspaceNormalizeEpisodeGuidance(' \n\t ')).toBeNull();
    expect(module.storyWorkspaceEpisodeCanonicalInputs({
      artifacts: [
        {
          relativeKey: 'episode-outline.md',
          availability: 'available',
          contentRevision: 'sha256:outline',
        },
        {
          relativeKey: 'script.md',
          availability: 'not_generated',
          contentRevision: null,
        },
      ],
    })).toEqual([
      { label: 'Episode Outline', availability: '已生成', revision: 'sha256:outline' },
      { label: 'Script', availability: '尚未生成', revision: null },
    ]);

    const detachedViewModel = {
      episode: {
        kind: 'episode', id: 'episode', sourceArtifact: 'episode-outline.md',
        sourceRevision: 'outline-r1', sourceAvailability: 'available',
      },
      storyArc: {
        kind: 'story-arc', id: 'arc', narrativeBeatIds: [],
        sourceArtifact: 'episode-outline.md', sourceRevision: 'outline-r1',
        sourceAvailability: 'available',
      },
      narrativeBeatsById: {}, scenesById: {}, shotsById: {},
      promptsByShotViewId: {}, renderQueueByShotViewId: {}, reviewTargetsByTargetViewId: {},
      unlinked: {
        scenes: [{
          kind: 'scene', id: 'unlinked-scene', sourceArtifact: 'script.md',
          sourceRevision: 'script-r1', sourceAvailability: 'available',
        }],
        shots: [], prompts: [], renderQueueEntries: [], reviewTargets: [],
      },
      orphans: {
        scenes: [],
        shots: [{
          kind: 'shot', id: 'orphan-shot', sourceArtifact: 'storyboard.yaml',
          sourceRevision: 'storyboard-r1', sourceAvailability: 'available',
        }],
        prompts: [], renderQueueEntries: [], reviewTargets: [],
      },
      coverage: {},
    };
    const expanded = new Set([
      'auxiliary-group:story-workspace-episode-unlinked',
      'auxiliary-group:story-workspace-episode-orphans',
    ]);
    expect(module.storyWorkspaceEpisodeEscapeSelection(
      detachedViewModel,
      expanded,
      { kind: 'scene', id: 'unlinked-scene' },
    )).toEqual({
      kind: 'auxiliary-group', id: 'story-workspace-episode-unlinked',
    });
    expect(module.storyWorkspaceEpisodeEscapeSelection(
      detachedViewModel,
      expanded,
      { kind: 'shot', id: 'orphan-shot' },
    )).toEqual({
      kind: 'auxiliary-group', id: 'story-workspace-episode-orphans',
    });

    expect(module.storyWorkspaceEpisodeNextActionLabel('generate_prompts'))
      .toBe('生成镜头 Prompt');
    expect(module.storyWorkspaceEpisodeNextActionLabel('none_in_scope')).toBeNull();
    expect(module.storyWorkspaceEpisodeNextActionLabel('invent_episode')).toBeNull();
  } finally {
    await server.close();
  }
});

test('dedicated dialog delays confirmation, preserves failed draft and restores trigger focus', async ({
  page,
}) => {
  const harnessModule = `
    import React, { createElement as h, useRef, useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import { StoryWorkspaceEpisodeContinueDialog } from '/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx';

    function Harness() {
      const [open, setOpen] = useState(false);
      const [requests, setRequests] = useState(0);
      const [guidance, setGuidance] = useState('none');
      const [error, setError] = useState(null);
      const triggerRef = useRef(null);
      return h('main', null,
        h('button', { id: 'continue', ref: triggerRef, onClick: () => setOpen(true) }, '继续生成剧本'),
        h('output', { id: 'requests' }, String(requests)),
        h('output', { id: 'guidance' }, guidance),
        open ? h(StoryWorkspaceEpisodeContinueDialog, {
          actionLabel: '继续生成剧本',
          busy: false,
          canonicalInputs: [
            { label: 'Episode Outline', availability: '已生成', revision: 'sha256:outline-r1' },
            { label: 'Script', availability: '尚未生成', revision: null },
          ],
          error,
          onCancel: () => setOpen(false),
          onConfirm: async (value) => {
            setRequests((count) => count + 1);
            setGuidance(value ?? 'null');
            setError('派发未被接受');
          },
          restoreFocusRef: triggerRef,
        }) : null,
      );
    }
    createRoot(document.querySelector('#root')).render(h(Harness));
  `;
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true },
    plugins: [{
      name: 'u11-episode-dialog-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/u11-episode-dialog') return next();
          const html = await vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><body><div id="root"></div>
            <script type="module" src="/u11-dialog-harness.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) {
        return id === '/u11-dialog-harness.js' ? '\\0u11-dialog-harness.js' : null;
      },
      load(id) {
        return id === '\\0u11-dialog-harness.js' ? harnessModule : null;
      },
    }],
  });
  await server.listen();
  const address = server.httpServer?.address();
  if (address === null || address === undefined || typeof address === 'string') {
    await server.close();
    throw new Error('U11 dialog harness did not bind a TCP port.');
  }
  try {
    await page.goto(`http://127.0.0.1:${address.port}/u11-episode-dialog`);
    const trigger = page.locator('#continue');
    const requests = page.locator('#requests');

    await trigger.click();
    await expect(page.getByRole('dialog', { name: '确认 Episode 下一步' })).toBeVisible();
    await expect(requests).toHaveText('0');
    await expect(page.getByRole('dialog')).toContainText('继续生成剧本');
    await expect(page.getByRole('dialog')).toContainText('Episode Outline');
    await expect(page.getByRole('dialog')).toContainText('sha256:outline-r1');
    await page.getByRole('button', { name: '取消' }).click();
    await expect(requests).toHaveText('0');
    await expect(trigger).toBeFocused();

    await trigger.click();
    await page.keyboard.press('Escape');
    await expect(requests).toHaveText('0');
    await expect(trigger).toBeFocused();

    await trigger.click();
    const guidance = page.getByRole('textbox', { name: '补充创作要求（可选）' });
    await expect(guidance).toBeFocused();
    await guidance.fill('  保留克制感  ');
    await page.getByRole('button', { name: '确认并继续' }).click();
    await expect(requests).toHaveText('1');
    await expect(page.locator('#guidance')).toHaveText('保留克制感');
    await expect(guidance).toHaveValue('  保留克制感  ');
    await expect(page.getByRole('alert')).toContainText('派发未被接受');
  } finally {
    await server.close();
  }
});

test('revision deletion moves selection, aria-live copy and DOM focus to the reconciled parent', async ({
  page,
}) => {
  const harnessModule = `
    import React, { createElement as h, useEffect, useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import { StoryWorkspaceEpisodeNarrativeWorkbench } from '/src/components/story-workspace/episode/StoryWorkspaceEpisodeNarrativeWorkbench.tsx';
    import { useStoryWorkspaceEpisodeRevisionSelection } from '/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx';
    const emptyArtifacts = { scenes: [], shots: [], prompts: [], renderQueueEntries: [], reviewTargets: [] };
    const coverage = { availability: 'unavailable', linked: 0, total: 0, ratio: null, label: '尚未生成' };
    const episode = { kind: 'episode', id: 'episode', title: '第一集', storyArcId: 'arc', sourceArtifact: 'episode-outline.md', sourceRevision: 'outline-r1', sourceAvailability: 'available' };
    const storyArc = { kind: 'story-arc', id: 'arc', episodeId: 'episode', narrativeBeatIds: ['beat'], sourceArtifact: 'episode-outline.md', sourceRevision: 'outline-r1', sourceAvailability: 'available' };
    const beat = { kind: 'narrative-beat', id: 'beat', sourceKey: 'SC-01', title: '转折', assetSceneRef: null, narrativeFunction: null, emotionTone: null, summary: null, sceneGoals: [], keyDialogueBeats: [], sourceArtifact: 'episode-outline.md', sourceRevision: 'outline-r1', generatedFrom: null, sceneIds: ['scene'], shotIds: ['shot'], sourceAvailability: 'available' };
    const scene = { kind: 'scene', id: 'scene', sourceKey: 'S01', title: '站台', heading: 'EXT. 站台 - 夜', assetSceneRef: null, narrativeBeatId: 'beat', declaredNarrativeBeatRef: 'SC-01', associationStatus: 'linked', actions: [], dialogue: [], cameraCues: [], sourceArtifact: 'script.md', sourceRevision: 'script-r1', generatedFrom: null, shotIds: ['shot'], sourceAvailability: 'available' };
    const shot = { kind: 'shot', id: 'shot', shotId: 'S01-E01-SH01', assetSceneRef: null, declaredScriptSceneRef: 'S01', declaredNarrativeBeatRef: 'SC-01', scriptSceneId: 'scene', narrativeBeatId: 'beat', associationStatus: 'linked', shotType: null, characters: [], camera: { angle: null, height: null, movement: null, lens: null }, visual: null, dialogue: [], timing: { durationSec: null, transitionIn: null, transitionOut: null }, sourceArtifact: 'storyboard.yaml', sourceRevision: 'storyboard-r1', generatedFrom: null, sourceAvailability: 'available' };
    const base = { episode, storyArc, narrativeBeatsById: { beat }, scenesById: { scene }, shotsById: { shot }, promptsByShotViewId: {}, renderQueueByShotViewId: {}, reviewTargetsByTargetViewId: {}, unlinked: emptyArtifacts, orphans: emptyArtifacts, coverage: { beatScene: coverage, sceneShot: coverage, shotPrompt: coverage, shotRenderQueue: coverage } };
    const revised = { ...base, narrativeBeatsById: { beat: { ...beat, shotIds: [] } }, scenesById: { scene: { ...scene, shotIds: [] } }, shotsById: {} };
    function Harness() {
      const [viewModel, setViewModel] = useState(base);
      const revision = useStoryWorkspaceEpisodeRevisionSelection('run-a', viewModel);
      useEffect(() => {
        revision.onSelection({ kind: 'shot', id: 'shot' });
        window.applyRevision = () => setViewModel(revised);
      }, []);
      return h('main', null,
        h('p', { id: 'announcement', 'aria-live': 'polite' }, revision.announcement),
        h('div', { ref: revision.workbenchRef }, h(StoryWorkspaceEpisodeNarrativeWorkbench, {
          viewModel: revision.viewModel,
          selection: revision.selection ?? { kind: 'episode', id: 'episode' },
          expandedKeys: new Set(['narrative-beat:beat', 'scene:scene']),
          onSelection: revision.onSelection,
          onExpanded: () => undefined,
          onEscape: () => undefined,
        })),
      );
    }
    createRoot(document.querySelector('#root')).render(h(Harness));
  `;
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true },
    plugins: [{
      name: 'u11-revision-focus-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/u11-revision-focus') return next();
          const html = await vite.transformIndexHtml(requestUrl, `
            <!doctype html><html><body><div id="root"></div>
            <script type="module" src="/u11-revision-harness.js"></script></body></html>
          `);
          response.statusCode = 200;
          response.setHeader('Content-Type', 'text/html; charset=utf-8');
          response.end(html);
        });
      },
      resolveId(id) {
        return id === '/u11-revision-harness.js' ? '\\0u11-revision-harness.js' : null;
      },
      load(id) {
        return id === '\\0u11-revision-harness.js' ? harnessModule : null;
      },
    }],
  });
  await server.listen();
  const address = server.httpServer?.address();
  if (address === null || address === undefined || typeof address === 'string') {
    await server.close();
    throw new Error('U11 revision harness did not bind a TCP port.');
  }
  try {
    await page.goto(`http://127.0.0.1:${address.port}/u11-revision-focus`);
    const selectedShot = page.getByRole('treeitem', { name: /S01-E01-SH01/ });
    await expect(selectedShot).toHaveAttribute('aria-selected', 'true');
    await selectedShot.focus();
    await page.evaluate(() => {
      (window as unknown as { applyRevision: () => void }).applyRevision();
    });
    const selectedScene = page.getByRole('treeitem', { name: /S01 站台/ });
    await expect(selectedScene).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('#announcement')).toContainText('当前镜头已在新版本中移除');
    await expect(selectedScene).toBeFocused();
  } finally {
    await server.close();
  }
});
