// [Input] Dream page, rail, dialog and page stylesheet source.
// [Output] Node seam assertions for exclusive Dream UI boundary and responsive/a11y affordances.
// [Pos] Dream Agent workbench layout Red/Green tests (design_008 §15/§20).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import { storyWorkspaceDreamAgentFocusCycleIndex } from '../../../components/story-workspace/dream/storyWorkspaceDreamAgentFocus';

const PAGE = readFileSync(new URL('../StoryWorkspaceDreamPage.tsx', import.meta.url), 'utf8');
const RAIL = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentRail.tsx', import.meta.url), 'utf8');
const DIALOG = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');

test('Dream page integrates the dedicated rail/dialog and never a generic Chat view', () => {
  expect(PAGE).toContain('<StoryWorkspaceDreamAgentRail');
  expect(PAGE).toContain('<StoryWorkspaceDreamAgentDialog');
  expect(`${PAGE}\n${RAIL}\n${DIALOG}`).not.toContain('ChatView');
  expect(`${PAGE}\n${RAIL}\n${DIALOG}`).not.toContain('ChatWidgetUI');
});

test('rail is a named button and dialog has Escape focus return plus narrow modal semantics', () => {
  expect(RAIL).toContain('aria-label={`打开 Dream Agent');
  expect(DIALOG).toContain("event.key === 'Escape'");
  expect(DIALOG).toContain('restoreFocusRef.current?.focus()');
  expect(DIALOG).toContain('aria-modal={isNarrow}');
  expect(DIALOG).toContain('aria-live="polite"');
  expect(DIALOG).toContain('headingRef.current?.focus()');
  expect(DIALOG).toContain('inputRef.current?.focus()');
  expect(RAIL).toContain('技术详情');
  expect(RAIL).toContain('runtime snapshot');
});

test('rail stays silent, while dialog owns the throttled announcement and mobile focus cycles in both directions', () => {
  expect(RAIL).not.toContain('aria-live');
  expect(DIALOG).toContain('setTimeout(() => setAnnouncedStreamText(streamText), 500)');
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
