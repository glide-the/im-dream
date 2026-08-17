// [Input] Dream workbench and Story Workspace router sources.
// [Output] Regression coverage for the two-state three-section Dream home, re-entry, context ownership,
//          deferred marketplace exclusion, and the popup-scoped Deck metadata boundary.
// [Pos] Story Workspace Dream re-entry Node seam (U2 Red).
// [Sync] 2026-08-14: cover natural-flow re-entry, canonical whole-row links, and pagination.
// [Sync] 2026-08-16: restore pre-01a00576 Deck maintenance and keep its handoff in canonical Chat.

// @ts-expect-error Playwright has Node built-ins; the browser app tsconfig intentionally omits Node types.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import type { StoryWorkspaceDreamReentryItem } from '../../../hooks/story-workspace/contracts';
import { resolveRunDeepLink } from '../../../hooks/story-workspace/useRunDeepLink';
import { storyWorkspaceDreamResolvedRunId } from '../../../router/storyWorkspacePath';
import {
  storyWorkspaceFilterDreamReentryRuns,
  storyWorkspacePaginateDreamReentryRuns,
} from '../dreamReentryViewModel';

const LAUNCH_SOURCE = readFileSync(new URL('../StoryWorkspaceDreamLaunch.tsx', import.meta.url), 'utf8');
const PAGE_SOURCE = readFileSync(new URL('../StoryWorkspaceDreamPage.tsx', import.meta.url), 'utf8');
const DREAM_CSS = readFileSync(new URL('../StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');
const ROUTER_SOURCE = readFileSync(new URL('../../../router/story-workspace.tsx', import.meta.url), 'utf8');
const LAYOUT_SOURCE = readFileSync(new URL('../../../components/story-workspace/layout/StoryWorkspaceLayout.tsx', import.meta.url), 'utf8');
const LAYOUT_CSS = readFileSync(new URL('../../../components/story-workspace/layout/StoryWorkspaceLayout.css', import.meta.url), 'utf8');
const DECK_SOURCE = readFileSync(new URL('../../../components/DeckEditorModal.tsx', import.meta.url), 'utf8');

test('no-run Dream home promotes active runs and durable re-entry without a marketplace or launch form', () => {
  expect(LAUNCH_SOURCE).toContain('useStoryWorkspaceDreamRuns');
  expect(LAUNCH_SOURCE).toContain('进行中的 Dream');
  expect(LAUNCH_SOURCE).toContain("run.outcome === 'in_progress'");
  expect(LAUNCH_SOURCE).toContain('我的 Dream');
  expect(LAUNCH_SOURCE).not.toMatch(/社区卡组|communityDecks|listDecks\(true\)|forkDeck/);
  expect(LAUNCH_SOURCE).toContain('story-workspace-dream-reentry');
  expect(LAUNCH_SOURCE).toContain('<strong>{run.displayTitle}</strong>');
  expect(LAUNCH_SOURCE).toContain('<small>{run.deckDisplayName}');
  expect(LAUNCH_SOURCE).toContain('type="search"');
  expect(LAUNCH_SOURCE).toContain('story-workspace-dream-reentry__pagination');
  expect(LAUNCH_SOURCE).toContain('href={run.href}');
  expect(LAUNCH_SOURCE).toContain('onNavigate(run.href)');
  expect(LAUNCH_SOURCE).not.toContain('创作设置');
  expect(LAUNCH_SOURCE).not.toContain('useStoryWorkspaceDreamLaunch');
  expect(LAUNCH_SOURCE).not.toContain('localStorage');
});

function dreamRun(
  number: number,
  fields: Partial<StoryWorkspaceDreamReentryItem> = {},
): StoryWorkspaceDreamReentryItem {
  const storyWorkspaceRunId = `run_${number.toString(16).padStart(32, '0')}`;
  return {
    storyWorkspaceRunId,
    displayTitle: `雨夜故事 ${number}`,
    goalPrefix: `雨夜故事 ${number}`,
    deckId: 'deck-story',
    deckDisplayName: '故事创作',
    workflowDisplayName: 'Dream',
    deckPluginVersion: 'v1',
    lifecycle: 'recent',
    outcome: 'in_progress',
    group: 'recent',
    stageRevisions: {},
    confirmationAccepted: true,
    confirmationDispatched: true,
    lastActivityAt: '2026-08-13T00:00:00Z',
    createdAt: '2026-08-13T00:00:00Z',
    sortKey: String(number),
    href: `/story-workspace/runs/${storyWorkspaceRunId}/execution`,
    ...fields,
  };
}

test('Dream re-entry search matches user-facing fields without changing server order', () => {
  const runs = [
    dreamRun(1),
    dreamRun(2, { displayTitle: '海边来信', goalPrefix: '旧创作目标', deckDisplayName: '克制叙事' }),
    dreamRun(3, { lifecycle: 'running', outcome: 'in_progress', group: 'in_progress' }),
    dreamRun(4, {
      lifecycle: 'waiting_confirmation',
      outcome: 'initial',
      group: 'in_progress',
      confirmationAccepted: false,
      confirmationDispatched: false,
      href: '/story-workspace/dream?run=run_00000000000000000000000000000004',
    }),
  ];
  expect(storyWorkspaceFilterDreamReentryRuns(runs, '  海边  ')).toEqual([runs[1]]);
  expect(storyWorkspaceFilterDreamReentryRuns(runs, '克制')).toEqual([runs[1]]);
  expect(storyWorkspaceFilterDreamReentryRuns(runs, runs[2].storyWorkspaceRunId.slice(-6))).toEqual([runs[2]]);
  expect(storyWorkspaceFilterDreamReentryRuns(runs, '正在执行')).toEqual([runs[2]]);
  expect(storyWorkspaceFilterDreamReentryRuns(runs, '初始状态')).toEqual([runs[3]]);
  expect(storyWorkspaceFilterDreamReentryRuns(runs, '')).toBe(runs);
});

test('Dream re-entry pagination clamps page bounds and preserves item order', () => {
  const runs = Array.from({ length: 9 }, (_, index) => dreamRun(index + 1));
  expect(storyWorkspacePaginateDreamReentryRuns(runs, 2)).toMatchObject({
    items: runs.slice(4, 8),
    page: 2,
    totalPages: 3,
  });
  expect(storyWorkspacePaginateDreamReentryRuns(runs, 99)).toMatchObject({
    items: runs.slice(8),
    page: 3,
    totalPages: 3,
  });
});

test('accepted confirmation navigates directly to the run execution workbench', () => {
  const confirmationHandler = PAGE_SOURCE.slice(
    PAGE_SOURCE.indexOf('const confirmAndContinue'),
    PAGE_SOURCE.indexOf("if (!runId)", PAGE_SOURCE.indexOf('const confirmAndContinue')),
  );
  expect(confirmationHandler).toContain('const accepted = await confirmation.submit(started.command)');
  expect(confirmationHandler).toContain('onNavigate?.(');
  expect(confirmationHandler).toContain(
    '`/story-workspace/runs/${encodeURIComponent(runId)}/execution`',
  );
  expect(confirmationHandler.indexOf('onNavigate?.(')).toBeGreaterThan(
    confirmationHandler.indexOf('await confirmation.submit(started.command)'),
  );
});

test('Dream workbench opens its bound Agent editor by default for every run', () => {
  expect(PAGE_SOURCE).toContain("useState<DreamRightSection>('agent')");
  const runResetEffect = PAGE_SOURCE.slice(
    PAGE_SOURCE.indexOf('useEffect(() => {\n    setDreamState(null)'),
    PAGE_SOURCE.indexOf('useEffect(() => {\n    if (!runId) return;', PAGE_SOURCE.indexOf('useEffect(() => {\n    setDreamState(null)')),
  );
  expect(runResetEffect).toContain("setRightSection('agent')");
  expect(runResetEffect).toContain('[initialStage, runId]');
  expect(PAGE_SOURCE).toContain('aria-label="Dream 内容编辑器"');
  expect(PAGE_SOURCE).toContain('data-agent-open={agentPanelOpen || undefined}');
});

test('Dream home has one page scroller and no nested re-entry scrollbar', () => {
  expect(LAYOUT_CSS).toMatch(/\.story-workspace-layout__main\s*\{[^}]*overflow-y: auto;/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home\s*\{[^}]*height: auto;[^}]*overflow: visible;/s);
  expect(DREAM_CSS).toMatch(/\.story-workspace-dream-home \.story-workspace-dream-reentry__items\s*\{[^}]*overflow: visible;/s);
  expect(DREAM_CSS).not.toMatch(/\.story-workspace-dream-home\s*\{[^}]*overflow-y: auto;/s);
});

test('Dream route removes the top WorkflowContextBar while non-Dream route support remains', () => {
  expect(ROUTER_SOURCE).toContain('workflowContext={isDreamRoute || isSettingsRoute\n        ? null');
  expect(LAYOUT_SOURCE).toContain('<WorkflowContextBar {...workflowContext} />');
});

test('Deck popup restores Deck-owned maintenance without Workflow', () => {
  expect(DECK_SOURCE).toContain('deck: Deck;');
  expect(DECK_SOURCE).not.toContain('onCreateDeck');
  expect(DECK_SOURCE).toContain('DeckClaudePluginSelector');
  expect(DECK_SOURCE).toContain('Agent Prompt');
  expect(DECK_SOURCE).toContain('onChatWithDeck');
  expect(DECK_SOURCE).not.toMatch(/Workflow|工作流|memory_workspace_config|onOpenDreamWithDeck|ChatView/);
});

test('403/404 deep links resolve to no run so Dream renders the recovery workbench, never a raw run page', async () => {
  for (const status of [403, 404]) {
    const resolution = await resolveRunDeepLink('run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', {
      getRun: async () => { throw new Error(String(status)); },
    });
    expect(resolution.status).toBe('missing');
  }
  expect(storyWorkspaceDreamResolvedRunId(null)).toBeNull();
  expect(storyWorkspaceDreamResolvedRunId({
    workflow_run_id: 'run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  })).toBe('run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
  expect(ROUTER_SOURCE).toContain('storyWorkspaceDreamPathWithoutRun');
});
