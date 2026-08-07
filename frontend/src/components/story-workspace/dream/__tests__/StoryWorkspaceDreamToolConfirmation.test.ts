// [Input] Dream Agent tool-confirmation component, both interaction surfaces and paper styling.
// [Output] Source contracts that keep confirmation behavior Dream-owned and accessible.
// [Pos] Dream Agent confirmation UI TDD seam.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import { storyWorkspaceDreamAgentPanelFocusTarget } from '../storyWorkspaceDreamAgentFocus';
import { storyWorkspaceDreamSubmittedAnswers } from '../StoryWorkspaceDreamToolConfirmation';

const CONFIRMATION = readFileSync(new URL('../StoryWorkspaceDreamToolConfirmation.tsx', import.meta.url), 'utf8');
const DIALOG = readFileSync(new URL('../StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');
const PANEL = readFileSync(new URL('../StoryWorkspaceDreamAgentPanel.tsx', import.meta.url), 'utf8');
const RAIL = readFileSync(new URL('../StoryWorkspaceDreamAgentRail.tsx', import.meta.url), 'utf8');
const PAGE = readFileSync(new URL('../../../../pages/story-workspace/StoryWorkspaceDreamPage.tsx', import.meta.url), 'utf8');
const CSS = readFileSync(new URL('../../../../pages/story-workspace/StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');

test('Dream surfaces replace their composer with one run-bound tool decision', () => {
  for (const source of [DIALOG, PANEL]) {
    expect(source).toContain('<StoryWorkspaceDreamToolConfirmation');
    expect(source).toContain('agent.pendingToolConfirmation ?');
    expect(source).toContain('onResolve={agent.confirmTool}');
  }
});

test('confirmation UI supports questions, safe approvals and network decisions without Chat UI', () => {
  expect(CONFIRMATION).toContain('role="region"');
  expect(CONFIRMATION).not.toContain('role="alertdialog"');
  expect(CONFIRMATION).toContain('待你确认');
  expect(CONFIRMATION).toContain("confirmation.kind === 'ask_user'");
  expect(CONFIRMATION).toContain("confirmation.kind === 'sandbox_network'");
  expect(CONFIRMATION).toContain("confirmation.kind === 'reject_only'");
  expect(CONFIRMATION).toContain('原始请求无法安全展示');
  expect(CONFIRMATION).toContain('拒绝并继续');
  expect(CONFIRMATION).toContain('step={question.type === \'number\' ? 1 : undefined}');
  expect(CONFIRMATION).toContain('Number.isInteger(value)');
  expect(CONFIRMATION).toContain('if (!question.required) return true;');
  expect(CONFIRMATION).toContain('disabled={isResolving || !answersAreValid}');
  expect(CONFIRMATION).toContain('用户拒绝本次工具操作');
  expect(CONFIRMATION).toContain('aria-busy={isResolving}');
  expect(CONFIRMATION).toContain('question.id');
  expect(CONFIRMATION).toContain('maxLength={1000}');
  expect(CONFIRMATION).toContain('role="status"');
  for (const source of [DIALOG, PANEL]) expect(source).toContain('errorMessage={agent.error');
  expect(CONFIRMATION).not.toContain('ToolConfirmationDock');
  expect(CONFIRMATION).not.toContain('AskUserQuestionUI');
  expect(CONFIRMATION).not.toContain('ChatView');
  expect(CONFIRMATION).not.toContain('JSON.stringify(confirmation');
  expect(CONFIRMATION).not.toContain('confirmation.title');
  expect(CONFIRMATION).not.toContain('option.description');
});

test('optional empty answers are omitted before submission', () => {
  const questions = [
    { id: 'number', question: '可选数字', type: 'number', required: false },
    {
      id: 'select',
      question: '可选单选',
      type: 'select',
      required: false,
      options: [{ label: '一', value: 'one' }, { label: '二', value: 'two' }],
    },
    { id: 'text', question: '可选文本', type: 'text', required: false },
    {
      id: 'multiSelect',
      question: '可选多选',
      type: 'select',
      required: false,
      multiSelect: true,
      options: [{ label: '一', value: 'one' }, { label: '二', value: 'two' }],
    },
    { id: 'checkbox', question: '可选确认', type: 'checkbox', required: false },
    { id: 'required', question: '必填文本', type: 'text', required: true },
  ] as const;

  expect(
    storyWorkspaceDreamSubmittedAnswers(questions, {
      number: '',
      select: '',
      text: '',
      multiSelect: [],
      required: '保留',
    }),
  ).toEqual({ required: '保留' });

  expect(
    storyWorkspaceDreamSubmittedAnswers(questions, {
      number: 0,
      select: '',
      text: '',
      multiSelect: [],
      checkbox: false,
      required: '保留',
    }),
  ).toEqual({ number: 0, checkbox: false, required: '保留' });
});

test('narrow Dream dialog makes every background branch inert while open', () => {
  expect(DIALOG).toContain('sibling.inert = true');
  expect(DIALOG).toContain("sibling.setAttribute('aria-hidden', 'true')");
  expect(DIALOG).toContain('previousInert');
});

test('Dream confirmation styling is an editorial proof slip, not a rounded Chat card', () => {
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation::before');
  expect(CSS).toContain('border-top: 1px solid var(--dream-rule)');
  expect(CSS).toContain('border-bottom: 1px solid var(--dream-rule)');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation__option');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation__actions');
});

test('collapsed Dream content announces one safe pending action and keeps an explicit entry point', () => {
  expect(PAGE).toContain('Dream Agent 等待你确认一项操作');
  expect(PAGE).toContain('role="status"');
  expect(PAGE).toContain('aria-live="polite"');
  expect(PAGE).toContain('announcedToolCallIdsRef');
  expect(PAGE).toContain('dreamAgent.pendingToolConfirmation?.toolCallId');
  expect(PAGE).toContain('announcedToolCallIdsRef.current.has(pendingToolCallId)');
  expect(PAGE).toContain('data-pending={Boolean(dreamAgent.pendingToolConfirmation) || undefined}');
  expect(PANEL).not.toContain('key={pendingToolCallId}');
  expect(PANEL).toContain('retainPreviousToolCallId = true');
  expect(PANEL).toContain('[composerCanReceiveFocus, isOpen, pendingToolCallId]');
  expect(RAIL).toContain('if (agent.pendingToolConfirmation)');
  expect(RAIL).toContain("return '等待你确认一项操作'");
  expect(`${PAGE}\n${RAIL}`).not.toContain('ToolConfirmationDock');
  expect(`${PAGE}\n${RAIL}`).not.toContain('ChatPanel');
  expect(`${PAGE}\n${RAIL}`).not.toContain('ChatView');
  expect(`${PAGE}\n${RAIL}\n${PANEL}\n${CONFIRMATION}`).not.toContain('/Users/');
});

test('inline Panel follows every confirmation focus path without stealing reading focus', () => {
  const state = {
    focusFellOut: false,
    isOpen: true,
    lastFocusedZone: 'composer' as const,
    pendingToolCallId: 'tool-a',
    previousToolCallId: null,
    wasOpen: true,
  };
  expect(storyWorkspaceDreamAgentPanelFocusTarget({ ...state, isOpen: false }))
    .toBeNull();
  expect(storyWorkspaceDreamAgentPanelFocusTarget({ ...state, wasOpen: false }))
    .toBe('confirmation');
  expect(storyWorkspaceDreamAgentPanelFocusTarget(state))
    .toBe('confirmation');
  expect(storyWorkspaceDreamAgentPanelFocusTarget({ ...state, lastFocusedZone: 'history' }))
    .toBeNull();
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    lastFocusedZone: 'history',
    pendingToolCallId: 'tool-b',
    previousToolCallId: 'tool-a',
  })).toBe('confirmation');
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    pendingToolCallId: null,
    previousToolCallId: 'tool-a',
  })).toBe('composer');
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    lastFocusedZone: 'history',
    pendingToolCallId: null,
    previousToolCallId: 'tool-a',
  })).toBeNull();
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    lastFocusedZone: 'navigation',
    pendingToolCallId: null,
    previousToolCallId: 'tool-a',
  })).toBeNull();
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    lastFocusedZone: 'outside',
    pendingToolCallId: null,
    previousToolCallId: 'tool-a',
  })).toBeNull();
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    focusFellOut: true,
    lastFocusedZone: 'outside',
    pendingToolCallId: null,
    previousToolCallId: 'tool-a',
  })).toBe('composer');
  expect(storyWorkspaceDreamAgentPanelFocusTarget({
    ...state,
    isOpen: false,
    pendingToolCallId: null,
    previousToolCallId: 'tool-a',
  })).toBeNull();
  expect(CSS).toContain('@media (max-width: 767px)');
  expect(CSS).toContain('.story-workspace-dream-tool-confirmation { max-height: min(52dvh, 420px);');
  expect(CSS).toContain('min-height: 44px;');
});
