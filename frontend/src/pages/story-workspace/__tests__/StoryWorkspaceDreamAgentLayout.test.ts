// [Input] Dream page, rail, dialog and page stylesheet source.
// [Output] Node seam assertions for exclusive Dream UI boundary and responsive/a11y affordances.
// [Pos] Dream Agent workbench layout Red/Green tests (design_008 §15/§20).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import { storyWorkspaceDreamAgentFocusCycleIndex } from '../../../components/story-workspace/dream/storyWorkspaceDreamAgentFocus';
import {
  STORY_WORKSPACE_DREAM_AGENT_BOTTOM_PROXIMITY_PX,
  storyWorkspaceDreamAgentScrollBehavior,
  storyWorkspaceDreamAgentScrollPosition,
} from '../../../components/story-workspace/dream/useStoryWorkspaceDreamAgentScroll';
import {
  storyWorkspaceDreamIsPlainPrimaryActivation,
  storyWorkspaceDreamReturnState,
  storyWorkspaceDreamShouldReturnToHistory,
} from '../storyWorkspaceDreamNavigation';

const PAGE = readFileSync(new URL('../StoryWorkspaceDreamPage.tsx', import.meta.url), 'utf8');
const RAIL = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentRail.tsx', import.meta.url), 'utf8');
const DECK_METADATA = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamDeckMetadata.tsx', import.meta.url), 'utf8');
const DECK_METADATA_CSS = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamDeckMetadata.css', import.meta.url), 'utf8');
const DIALOG = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');
const PANEL = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentPanel.tsx', import.meta.url), 'utf8');
const SCROLL = readFileSync(new URL('../../../components/story-workspace/dream/useStoryWorkspaceDreamAgentScroll.ts', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');
const NAVIGATION = readFileSync(new URL('../storyWorkspaceDreamNavigation.ts', import.meta.url), 'utf8');

test('Dream page integrates the dedicated rail/dialog and never a generic Chat view', () => {
  expect(PAGE).toContain('<StoryWorkspaceDreamAgentRail');
  expect(PAGE).toContain('<StoryWorkspaceDreamAgentPanel');
  expect(PAGE).not.toContain('<StoryWorkspaceDreamAgentDialog');
  expect(`${PAGE}\n${RAIL}\n${DECK_METADATA}\n${DIALOG}`).not.toContain('ChatView');
  expect(`${PAGE}\n${RAIL}\n${DECK_METADATA}\n${DIALOG}`).not.toContain('ChatWidgetUI');
});

test('run-bound Dream keeps its full Agent history inside the editor rail, not in a floating dialog', () => {
  expect(PAGE).toContain('className="story-workspace-dream__agent-panel"');
  expect(PAGE).toContain('{agentPanelOpen && (');
  expect(PAGE).toContain('isOpen={agentPanelOpen}');
  expect(PAGE).toContain('!agentPanelOpen && (selection && dreamState && selectedFileItem ? (');
  expect(PAGE.match(/<StoryWorkspaceDreamAgentPanel/g)).toHaveLength(1);
});

test('Agent previews and Dream content controls switch one owned editor section', () => {
  expect(PAGE).toContain("type DreamRightSection = 'content' | 'agent'");
  expect(PAGE).toContain("const [rightSection, setRightSection] = useState<DreamRightSection>('content')");
  expect(PAGE).toContain("const agentPanelOpen = rightSection === 'agent'");
  expect(PAGE).toContain("setRightSection('agent')");
  expect(PAGE).toContain('const showDreamContent =');
  expect(PAGE.match(/showDreamContent\(/g)?.length ?? 0).toBeGreaterThanOrEqual(2);
  expect(PAGE).toContain("aria-current={selected && rightSection === 'content' || undefined}");
});

test('confirmation footer belongs only to the Dream content section', () => {
  expect(PAGE).toContain(
    '{!agentPanelOpen && (\n        <footer className="story-workspace-dream__confirmation">',
  );
  expect(PAGE).toContain("onClose={() => setRightSection('content')}");
  expect(PAGE).toContain('disabled={!canConfirm}');
  expect(PAGE).toContain('onClick={() => void confirmAndContinue()}');
  expect(PAGE).toContain("confirmation.status === 'confirming' ? '正在确认…' : '确认并继续'");
});

test('masthead activity is a safe Dream Agent preview trigger, never static live lifecycle copy', () => {
  expect(PAGE).toContain('className="story-workspace-dream__activity"');
  expect(PAGE).toContain('onClick={openDreamAgent}');
  expect(PAGE).toContain('agentPreview');
  expect(PAGE).not.toContain('className="story-workspace-dream__activity" aria-live');
});

test('masthead preview and inline panel share one stable controls target', () => {
  expect(PANEL).toContain('STORY_WORKSPACE_DREAM_AGENT_PANEL_ID');
  expect(PANEL).toContain('id={STORY_WORKSPACE_DREAM_AGENT_PANEL_ID}');
  expect(PAGE).toContain('aria-controls={STORY_WORKSPACE_DREAM_AGENT_PANEL_ID}');
});

test('Agent rail belongs exclusively to the Agent section on desktop and narrow layouts', () => {
  expect(PAGE).toContain('{agentPanelOpen && (\n        <div className="story-workspace-dream__mobile-agent">');
  expect(PAGE).toContain('{agentPanelOpen && (\n            <StoryWorkspaceDreamAgentRail');
  expect(PAGE.match(/<StoryWorkspaceDreamAgentRail/g)).toHaveLength(2);
  expect(CSS).toContain('.story-workspace-dream__activity > span:last-child { display: none; }');
});

test('Dream return link preserves native modifiers and only goes back for in-app history state', () => {
  expect(PAGE).toContain('>← 返回上一页</a>');
  expect(PAGE).toContain('storyWorkspaceDreamShouldReturnToHistory(window.history.state)');
  expect(PAGE).toContain('storyWorkspaceDreamIsPlainPrimaryActivation(event)');
  expect(PAGE).toContain('window.history.back()');
  expect(PAGE).toContain("onNavigate('/story-workspace/dream')");
  expect(NAVIGATION).toContain("const STORY_WORKSPACE_RETURN_KIND = 'story-workspace-push'");
  expect(NAVIGATION).not.toContain("state.inkDreamView === 'story-workspace'");
  expect(NAVIGATION).toContain('!event.metaKey');
  expect(NAVIGATION).toContain('!event.ctrlKey');
  expect(NAVIGATION).toContain('!event.shiftKey');
  expect(NAVIGATION).toContain('!event.altKey');
});

test('Dream return navigation predicates distinguish in-app state and native link gestures', () => {
  expect(storyWorkspaceDreamShouldReturnToHistory({ inkDreamView: 'story-workspace' })).toBe(false);
  expect(storyWorkspaceDreamShouldReturnToHistory(null)).toBe(false);
  expect(storyWorkspaceDreamShouldReturnToHistory({ inkDreamView: 'writing' })).toBe(false);

  const pushState = storyWorkspaceDreamReturnState(
    { inkDreamView: 'story-workspace' },
    '/story-workspace/dream',
  );
  expect(pushState).toEqual({
    inkDreamView: 'story-workspace',
    storyWorkspaceReturn: {
      kind: 'story-workspace-push',
      sourceHref: '/story-workspace/dream',
    },
  });
  expect(storyWorkspaceDreamShouldReturnToHistory(pushState)).toBe(true);

  const replaceState = storyWorkspaceDreamReturnState(pushState, null);
  expect(replaceState).toEqual({ inkDreamView: 'story-workspace' });
  expect(storyWorkspaceDreamShouldReturnToHistory(replaceState)).toBe(false);

  const plainActivation = {
    altKey: false,
    button: 0,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
  };
  expect(storyWorkspaceDreamIsPlainPrimaryActivation(plainActivation)).toBe(true);
  expect(storyWorkspaceDreamIsPlainPrimaryActivation({ ...plainActivation, metaKey: true })).toBe(false);
  expect(storyWorkspaceDreamIsPlainPrimaryActivation({ ...plainActivation, ctrlKey: true })).toBe(false);
  expect(storyWorkspaceDreamIsPlainPrimaryActivation({ ...plainActivation, button: 1 })).toBe(false);
});

test('explicit panel collapse restores Agent trigger focus without stealing content-control focus', () => {
  expect(PANEL).toContain('const closePanel = () =>');
  expect(PANEL).toContain('requestAnimationFrame(() => restoreFocusRef.current?.focus())');
  expect(PANEL).toContain('onClick={closePanel}');
  expect(PANEL).not.toContain('if (wasOpenRef.current && !isOpen)');
});

test('hidden Agent panel cannot participate in the content section layout', () => {
  expect(PANEL).toContain('hidden={!isOpen}');
  expect(CSS).toContain('.story-workspace-dream-agent-panel[hidden]');
  expect(CSS).toMatch(/\.story-workspace-dream-agent-panel\[hidden\]\s*{\s*display:\s*none;/);
});

test('Dream Agent scroll position uses the shared 120px near-bottom boundary', () => {
  expect(STORY_WORKSPACE_DREAM_AGENT_BOTTOM_PROXIMITY_PX).toBe(120);
  expect(storyWorkspaceDreamAgentScrollPosition({
    clientHeight: 100,
    scrollHeight: 1000,
    scrollTop: 781,
  })).toEqual({ distanceFromBottom: 119, isNearBottom: true, isScrollable: true });
  expect(storyWorkspaceDreamAgentScrollPosition({
    clientHeight: 100,
    scrollHeight: 1000,
    scrollTop: 780,
  })).toEqual({ distanceFromBottom: 120, isNearBottom: false, isScrollable: true });
  expect(storyWorkspaceDreamAgentScrollPosition({
    clientHeight: 100,
    scrollHeight: 220,
    scrollTop: 0,
  }).isScrollable).toBe(false);
});

test('Dream Agent scrolling targets only its history and respects reduced motion', () => {
  expect(storyWorkspaceDreamAgentScrollBehavior(true)).toBe('auto');
  expect(storyWorkspaceDreamAgentScrollBehavior(false)).toBe('smooth');
  expect(SCROLL).not.toContain('scrollIntoView');
  expect(SCROLL).not.toContain('window.scrollTo');
  expect(SCROLL).not.toContain('document.scrollingElement');
  expect(SCROLL).not.toContain('document.documentElement');
  expect(SCROLL).toContain('const element = historyRef.current;');
  expect(SCROLL.match(/element\.scrollTo\(/g)).toHaveLength(1);
  expect(SCROLL).toContain("window.matchMedia('(prefers-reduced-motion: reduce)').matches");
});

test('Dream Panel and Dialog share Dream-only follow-latest controls', () => {
  for (const surface of [PANEL, DIALOG]) {
    expect(surface).toContain('useStoryWorkspaceDreamAgentScroll');
    expect(surface).toContain('historyRef');
    expect(surface).toContain('bottomRef');
    expect(surface).toContain('onScroll={handleHistoryScroll}');
    expect(surface).toContain('aria-label="前往最新消息"');
    expect(surface).toContain('title="前往最新消息"');
    expect(surface).toContain('scrollToLatest();');
  }
  expect(SCROLL).toContain('const forceFollowRef = useRef(false);');
  expect(SCROLL).toContain('if (forceFollowRef.current && position.isNearBottom)');
  expect(SCROLL).toContain("if (updateMode === 'follow')");
  expect(SCROLL).not.toContain('ChatPanel');
  expect(SCROLL).not.toContain('ChatView');
  expect(CSS).toContain('.story-workspace-dream-agent-scroll-to-latest');
});

test('rail delegates trusted Deck metadata to a dedicated Dream control', () => {
  expect(RAIL).toContain('<div className="story-workspace-dream-agent-rail__summary">');
  expect(RAIL).toContain("import { StoryWorkspaceDreamDeckMetadata } from './StoryWorkspaceDreamDeckMetadata'");
  expect(RAIL).toContain('<StoryWorkspaceDreamDeckMetadata');
  expect(RAIL).toContain('deckName={deckName}');
  expect(RAIL).toContain('runId={runId}');
  expect(RAIL).toContain('runtimeSnapshotId={runtimeSnapshotId}');
  expect(RAIL).toContain('runtimeLockId={runtimeLockId}');
  expect(RAIL).toContain('stageLine={stageLine}');
  expect(RAIL).not.toContain('onOpen');
  expect(RAIL).not.toContain('agent.snapshot?.messages');
  expect(RAIL).not.toContain('agent.streamText');
  expect(RAIL).not.toContain('story-workspace-dream-agent-rail__preview');
  expect(RAIL).not.toContain('Dream Agent 的回复会显示在这里。');
  expect(RAIL).not.toContain('<details');
  expect(RAIL).not.toContain('技术详情');
  expect(PAGE.match(/runtimeLockId={agentRuntimeLockId}/g)).toHaveLength(2);
  expect(PAGE.match(/runtimeSnapshotId={agentRuntimeSnapshotId}/g)).toHaveLength(2);
  expect(PAGE.match(/stageLine={agentStageLine}/g)).toHaveLength(2);
});

test('Dream Deck metadata is an instance-safe accessible disclosure without Chat data ownership', () => {
  expect(DECK_METADATA).toContain('const popoverId = useId()');
  expect(DECK_METADATA).toContain('const popoverTitleId = useId()');
  expect(DECK_METADATA).toContain('const popoverRef = useRef<HTMLDivElement>(null)');
  expect(DECK_METADATA).toContain('aria-controls={popoverId}');
  expect(DECK_METADATA).toContain('aria-expanded={open}');
  expect(DECK_METADATA).toContain('aria-haspopup="dialog"');
  expect(DECK_METADATA).toContain('role="dialog"');
  expect(DECK_METADATA).toContain('aria-modal="false"');
  expect(DECK_METADATA).toContain('aria-labelledby={popoverTitleId}');
  expect(DECK_METADATA).toContain('id={popoverTitleId}');
  expect(DECK_METADATA).toContain('ref={popoverRef}');
  expect(DECK_METADATA).toContain('tabIndex={-1}');
  expect(DECK_METADATA).toContain('popoverRef.current?.focus()');
  expect(DECK_METADATA).toContain("document.addEventListener('pointerdown', handlePointerDown)");
  expect(DECK_METADATA).toContain("event.key !== 'Escape'");
  expect(DECK_METADATA).toContain('triggerRef.current?.focus()');
  const pointerHandler = DECK_METADATA.slice(
    DECK_METADATA.indexOf('const handlePointerDown'),
    DECK_METADATA.indexOf('const handleKeyDown'),
  );
  expect(pointerHandler).not.toContain('triggerRef.current?.focus()');
  expect(DECK_METADATA).not.toContain("event.key === 'Tab'");
  expect(DECK_METADATA).not.toContain('querySelectorAll');
  expect(DECK_METADATA).not.toContain('PluginReceiptBadge');
  expect(DECK_METADATA).not.toContain('threadId');
  expect(DECK_METADATA).not.toContain('getThreadPluginLoadReceipt');
  expect(DECK_METADATA).not.toContain('setInterval');
  expect(DECK_METADATA).not.toContain('setTimeout');
  expect(DECK_METADATA).toContain("import './StoryWorkspaceDreamDeckMetadata.css'");
  expect(DECK_METADATA_CSS).toContain('.story-workspace-dream-deck-metadata__popover');
  expect(DECK_METADATA_CSS).toContain('calc(100vw - 32px)');
  expect(DECK_METADATA_CSS).toContain('@media (prefers-reduced-motion: reduce)');
});

test('dialog keeps its accessibility contracts', () => {
  expect(DIALOG).toContain("event.key === 'Escape'");
  expect(DIALOG).toContain('restoreFocusRef.current?.focus()');
  expect(DIALOG).toContain('aria-modal={isNarrow}');
  expect(DIALOG).toContain('aria-live="polite"');
  expect(DIALOG).toContain('headingRef.current?.focus()');
  expect(DIALOG).toContain('inputRef.current?.focus()');
  expect(DIALOG).toContain('Dream Agent 正在执行');
  expect(DIALOG).toContain('Dream Agent 已完成本轮输出');
  expect(DIALOG).toContain('aria-hidden="true"');
});

test('rail shows compact Agent context without duplicate opening copy', () => {
  expect(RAIL).not.toContain('<span>Dream Agent · {deckName}</span>');
  expect(RAIL).not.toContain('· {workflowName} · {pluginVersion}');
  expect(RAIL).not.toContain('story-workspace-dream-agent-rail__open');
  expect(CSS).not.toContain('.story-workspace-dream-agent-rail__open');
});

test('rail stays silent, while Dream surfaces share throttled announcements and mobile focus cycles in both directions', () => {
  expect(RAIL).not.toContain('aria-live');
  expect(PANEL).toContain('useStoryWorkspaceDreamAgentAnnouncement({');
  expect(DIALOG).toContain('useStoryWorkspaceDreamAgentAnnouncement({');
  expect(storyWorkspaceDreamAgentFocusCycleIndex(0, 3, true)).toBe(2);
  expect(storyWorkspaceDreamAgentFocusCycleIndex(2, 3, false)).toBe(0);
});

test('L3 names the current Dream stage and revisions, isolated from the local draft reducer', () => {
  expect(PAGE).toContain('function storyWorkspaceDreamAgentStageLine');
  expect(PAGE).toContain('当前：${STAGE_LABELS[activeStage].label}');
  const adapter = readFileSync(new URL('../../../hooks/story-workspace/useStoryWorkspaceDreamAgent.ts', import.meta.url), 'utf8');
  expect(adapter).not.toContain('storyWorkspaceHydrateDreamState');
  expect(adapter).not.toContain('storyWorkspaceEditDreamField');
});

test('desktop and narrow layouts keep the dialog inside its Dream workbench boundary', () => {
  expect(CSS).toContain('width: min(420px, calc(100vw - 32px))');
  expect(CSS).toContain('@media (max-width: 767px)');
  expect(CSS).toContain('max-height: min(88dvh, 760px)');
  expect(CSS).toContain('prefers-reduced-motion: reduce');
  expect(PAGE.indexOf('story-workspace-dream__masthead')).toBeLessThan(PAGE.indexOf('<nav className="story-workspace-dream__spine"'));
  expect(PAGE).toContain('story-workspace-dream__mobile-agent');
});
