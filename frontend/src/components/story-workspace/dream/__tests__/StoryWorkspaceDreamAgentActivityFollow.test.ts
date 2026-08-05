// [Input] Safe Dream Agent stream content and the shared Panel/Dialog scroll module.
// [Output] Pure revision, follow-mode and aria-live safety contracts for activity-only updates.
// [Pos] Dream Agent activity follow/announcement Node seam (U6 Red/Green).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import {
  storyWorkspaceDreamAgentContentRevision,
  storyWorkspaceDreamAgentNextActivityAnnouncement,
  storyWorkspaceDreamAgentScrollUpdateMode,
} from '../useStoryWorkspaceDreamAgentScroll';

const SCROLL = readFileSync(new URL('../useStoryWorkspaceDreamAgentScroll.ts', import.meta.url), 'utf8');
const PANEL = readFileSync(new URL('../StoryWorkspaceDreamAgentPanel.tsx', import.meta.url), 'utf8');
const DIALOG = readFileSync(new URL('../StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');

const running = [{
  kind: 'activity',
  id: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  category: 'workspace_read',
  label: '读取工作区资料',
  status: 'running',
}] as const;

const completed = [{ ...running[0], status: 'completed' }] as const;

test('activity start and same-id finish produce distinct stable content revisions', () => {
  expect(storyWorkspaceDreamAgentContentRevision(running)).toBe(
    storyWorkspaceDreamAgentContentRevision([...running]),
  );
  expect(storyWorkspaceDreamAgentContentRevision(running)).not.toBe(
    storyWorkspaceDreamAgentContentRevision(completed),
  );
  expect(storyWorkspaceDreamAgentContentRevision([
    ...running,
    { kind: 'text', text: '继续', truncated: false },
  ])).not.toBe(storyWorkspaceDreamAgentContentRevision(running));
});

test('activity-only revisions follow near the bottom and remeasure while reading above', () => {
  expect(storyWorkspaceDreamAgentScrollUpdateMode(false, true)).toBe('follow');
  expect(storyWorkspaceDreamAgentScrollUpdateMode(true, false)).toBe('follow');
  expect(storyWorkspaceDreamAgentScrollUpdateMode(false, false)).toBe('measure');
  expect(SCROLL).toContain('readonly contentRevision: string;');
  expect(SCROLL).toContain('contentRevision,');
  expect(SCROLL).toContain('contentRevision, messageCount');
});

test('activity announcement exposes only a fixed safe label and status transition', () => {
  expect(storyWorkspaceDreamAgentNextActivityAnnouncement([], running)).toEqual({
    key: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:running',
    text: '读取工作区资料，进行中',
  });
  expect(storyWorkspaceDreamAgentNextActivityAnnouncement(running, completed)).toEqual({
    key: 'dream_activity_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:completed',
    text: '读取工作区资料，已完成',
  });
  expect(storyWorkspaceDreamAgentNextActivityAnnouncement(completed, completed)).toBeNull();
  for (const forbidden of ['toolName', 'toolCallId', 'input', 'output', 'reasoning', 'command', 'path']) {
    expect(SCROLL).not.toContain(forbidden);
  }
});

test('Panel and Dialog share one activity-aware revision and throttled aria-live hook', () => {
  for (const surface of [PANEL, DIALOG]) {
    expect(surface).toContain('storyWorkspaceDreamAgentContentRevision(agent.streamContent)');
    expect(surface).toContain('contentRevision,');
    expect(surface).toContain('useStoryWorkspaceDreamAgentAnnouncement({');
    expect(surface).toContain('streamContent: agent.streamContent');
    expect(surface).toContain('streamText: agent.streamText');
    expect(surface).not.toContain('setTimeout(() => setAnnouncedStreamText(streamText), 500)');
  }
  expect(SCROLL).toContain('const timer = setTimeout(');
  expect(SCROLL).toContain('500');
  expect(SCROLL).toContain('pendingActivity?.text ?? streamText');
});
