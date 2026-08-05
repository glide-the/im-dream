// [Input] SubAgent panel and readonly timeline sources.
// [Output] Structural regression tests for compact list/detail and non-nested Chat lifecycle.
// [Pos] Chat SubAgent component seam test.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source only; browser app omits Node types.
import { readFileSync } from 'node:fs';

const PANEL = readFileSync(new URL('../SubagentPanel.tsx', import.meta.url), 'utf8');
const TIMELINE = readFileSync(new URL('../SubagentMessageTimeline.tsx', import.meta.url), 'utf8');

test('task rows remain compact, accessible and switch to a dedicated detail view', () => {
  expect(PANEL).toContain("minHeight: task.summary ? '4.5rem' : '3.75rem'");
  expect(PANEL).toContain('aria-current={focused');
  expect(PANEL).toContain("data-subagent-view={selectedTask ? 'detail' : 'list'}");
  expect(PANEL).toContain('<SubagentMessageTimeline');
  expect(PANEL).not.toContain('<ChatPanel');
});

test('readonly detail reuses Chat message primitives without transport or input controls', () => {
  expect(TIMELINE).toContain("import AssistMessagePart from './AssistMessagePart'");
  expect(TIMELINE).toContain("import UserMessagePart from './UserMessagePart'");
  expect(TIMELINE).toContain('pairSubagentToolMessages');
  expect(TIMELINE).not.toContain('useChat(');
  expect(TIMELINE).not.toContain('AIInputDock');
  expect(TIMELINE).not.toContain('ToolConfirmationDock');
  expect(TIMELINE).not.toContain('sendMessage');
});

