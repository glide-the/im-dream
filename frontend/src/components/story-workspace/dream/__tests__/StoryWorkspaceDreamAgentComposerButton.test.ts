// [Input] Dream Agent send gate and lifecycle states shared by Panel and Dialog composers.
// [Output] Deterministic idle/running button marker contracts.
// [Pos] Dream Agent composer state Red/Green seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import {
  storyWorkspaceDreamAgentComposerState,
  type StoryWorkspaceDreamAgentComposerStateInput,
} from '../StoryWorkspaceDreamAgentComposerButton';

const BUTTON_SOURCE = readFileSync(new URL(
  '../StoryWorkspaceDreamAgentComposerButton.tsx',
  import.meta.url,
), 'utf8');
const PANEL_SOURCE = readFileSync(new URL('../StoryWorkspaceDreamAgentPanel.tsx', import.meta.url), 'utf8');
const DIALOG_SOURCE = readFileSync(new URL('../StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');

function agent(
  lifecycle: 'idle' | 'streaming',
  sendBlockReason: NonNullable<
    StoryWorkspaceDreamAgentComposerStateInput['snapshot']
  >['sendBlockReason'],
  isSending = false,
): StoryWorkspaceDreamAgentComposerStateInput {
  return { isSending, snapshot: { lifecycle, sendBlockReason } };
}

test('composer state marks transport and server-owned generation as running', () => {
  expect(storyWorkspaceDreamAgentComposerState(agent('idle', null))).toBe('idle');
  expect(storyWorkspaceDreamAgentComposerState(agent('idle', 'waiting_confirmation'))).toBe('idle');
  expect(storyWorkspaceDreamAgentComposerState(agent('idle', null, true))).toBe('running');
  expect(storyWorkspaceDreamAgentComposerState(agent('streaming', null))).toBe('running');
  for (const reason of ['generating', 'confirming', 'continuing', 'busy'] as const) {
    expect(storyWorkspaceDreamAgentComposerState(agent('idle', reason))).toBe('running');
  }
});

test('Panel and Dialog share the Chat stop glyph as a truthful non-actionable marker', () => {
  expect(BUTTON_SOURCE).toContain("import { IconStop } from '../../chat/Icons'");
  expect(BUTTON_SOURCE).toContain('data-state="running"');
  expect(BUTTON_SOURCE).toContain('aria-label="Dream Agent 正在运行"');
  expect(BUTTON_SOURCE).toContain('<IconStop />');
  expect(BUTTON_SOURCE).toMatch(/data-state="running"[\s\S]*disabled[\s\S]*type="button"/);
  for (const surface of [PANEL_SOURCE, DIALOG_SOURCE]) {
    expect(surface).toContain("import { StoryWorkspaceDreamAgentComposerButton }");
    expect(surface).toContain('<StoryWorkspaceDreamAgentComposerButton agent={agent} canSend={canSend} />');
    expect(surface).not.toContain("agent.isSending ? '发送中…' : '发送'");
  }
});
