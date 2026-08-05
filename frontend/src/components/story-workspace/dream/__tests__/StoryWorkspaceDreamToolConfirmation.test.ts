// [Input] Dream Agent tool-confirmation component, both interaction surfaces and paper styling.
// [Output] Source contracts that keep confirmation behavior Dream-owned and accessible.
// [Pos] Dream Agent confirmation UI TDD seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';

const CONFIRMATION = readFileSync(new URL('../StoryWorkspaceDreamToolConfirmation.tsx', import.meta.url), 'utf8');
const DIALOG = readFileSync(new URL('../StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');
const PANEL = readFileSync(new URL('../StoryWorkspaceDreamAgentPanel.tsx', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../../../../pages/story-workspace/StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');

test('Dream surfaces replace their composer with one run-bound tool decision', () => {
  for (const source of [DIALOG, PANEL]) {
    expect(source).toContain('<StoryWorkspaceDreamToolConfirmation');
    expect(source).toContain('agent.pendingToolConfirmation ?');
    expect(source).toContain('onResolve={agent.confirmTool}');
  }
});

test('confirmation UI supports questions, safe approvals and network decisions without Chat UI', () => {
  expect(CONFIRMATION).toContain('role="alertdialog"');
  expect(CONFIRMATION).toContain('待你确认');
  expect(CONFIRMATION).toContain("confirmation.kind === 'ask_user'");
  expect(CONFIRMATION).toContain("confirmation.kind === 'sandbox_network'");
  expect(CONFIRMATION).toContain('用户拒绝本次工具操作');
  expect(CONFIRMATION).toContain('aria-busy={isResolving}');
  expect(CONFIRMATION).not.toContain('ToolConfirmationDock');
  expect(CONFIRMATION).not.toContain('AskUserQuestionUI');
  expect(CONFIRMATION).not.toContain('ChatView');
  expect(CONFIRMATION).not.toContain('JSON.stringify(confirmation');
});

test('Dream confirmation styling is an editorial proof slip, not a rounded Chat card', () => {
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation::before');
  expect(CSS).toContain('border-top: 1px solid var(--dream-rule)');
  expect(CSS).toContain('border-bottom: 1px solid var(--dream-rule)');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation__option');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation__actions');
});

