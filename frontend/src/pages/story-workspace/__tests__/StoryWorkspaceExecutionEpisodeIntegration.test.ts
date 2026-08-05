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

test('keeps selection and expansion session-only and reconciles instead of remounting by revision', () => {
  expect(PAGE_SOURCE).toContain('useState<StoryWorkspaceEpisodeSelection | null>');
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
        markAccepted(runId: string, fact: string, action: string): void;
      };
      readonly storyWorkspaceEpisodeNextActionLabel: (action: string) => string | null;
    };
    const generated = ['key-1', 'key-2', 'key-3'];
    const keys = new module.StoryWorkspaceEpisodeActionSessionKeys(
      () => generated.shift() ?? 'unexpected',
    );

    expect(keys.keyFor('run-a', 'etag-1', 'write_script')).toBe('key-1');
    expect(keys.keyFor('run-a', 'etag-1', 'write_script')).toBe('key-1');
    expect(keys.keyFor('run-a', 'etag-2', 'write_script')).toBe('key-2');
    keys.markAccepted('run-a', 'etag-2', 'write_script');
    expect(keys.keyFor('run-a', 'etag-2', 'write_script')).toBe('key-3');

    expect(module.storyWorkspaceEpisodeNextActionLabel('generate_prompts'))
      .toBe('生成镜头 Prompt');
    expect(module.storyWorkspaceEpisodeNextActionLabel('none_in_scope')).toBeNull();
    expect(module.storyWorkspaceEpisodeNextActionLabel('invent_episode')).toBeNull();
  } finally {
    await server.close();
  }
});
