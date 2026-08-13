// [Input] Dream page/dialog/panel source, responsive CSS, and shared thread chat adapter.
// [Output] Architectural/layout regression gate: Dream composes ChatPanel and reserves no obsolete dialog row.
// [Sync] 2026-08-13: require the desktop and mobile conversation dialog to allocate
//                    exactly a header row plus one minmax thread row.
// [Sync] 2026-08-13: require Chat auto-scroll to target only its owned message region,
//                    never scrollable Story Workspace ancestors via scrollIntoView.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses a built-in omitted from browser app types.
import { readFileSync } from 'node:fs';
import { storyWorkspaceDreamAgentFocusCycleIndex } from '../../../components/story-workspace/dream/storyWorkspaceDreamAgentFocus';

const PAGE = readFileSync(new URL('../StoryWorkspaceDreamPage.tsx', import.meta.url), 'utf8');
const EXECUTION = readFileSync(new URL('../StoryWorkspaceExecutionPage.tsx', import.meta.url), 'utf8');
const PANEL = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentPanel.tsx', import.meta.url), 'utf8');
const DIALOG = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog.tsx', import.meta.url), 'utf8');
const THREAD_CHAT = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamThreadChat.tsx', import.meta.url), 'utf8');
const CHAT_PANEL = readFileSync(new URL('../../../components/chat/ChatPanel.tsx', import.meta.url), 'utf8');
const DREAM_CSS = readFileSync(new URL('../StoryWorkspaceDreamPage.css', import.meta.url), 'utf8');

test('Dream gets the actor-scoped threadId from dream-files and composes canonical ChatPanel', () => {
  expect(PAGE).toContain('const threadId = files.data?.threadId ?? null');
  expect(EXECUTION).toContain('threadId={files.data.threadId}');
  expect(PANEL).toContain('<StoryWorkspaceDreamThreadChat');
  expect(DIALOG).toContain('<StoryWorkspaceDreamThreadChat');
  expect(THREAD_CHAT).toContain('<ChatPanel');
  expect(THREAD_CHAT).toContain('hydrateClaudeThreadSession');
});

test('Dream adapter owns no transport, useChat, parser, reducer, or run-scoped endpoint', () => {
  const dreamRuntimeSources = `${PAGE}\n${EXECUTION}\n${PANEL}\n${DIALOG}\n${THREAD_CHAT}`;
  expect(dreamRuntimeSources).not.toContain('useChat(');
  expect(dreamRuntimeSources).not.toContain('ClaudeAgentChatTransport');
  expect(dreamRuntimeSources).not.toContain('useReducer(');
  expect(dreamRuntimeSources).not.toMatch(/dream-agent\/(messages|events|tool-confirm)/);
  expect(CHAT_PANEL.match(/useChat\(/g)).toHaveLength(1);
});

test('shared ChatPanel owns confirmation, Stop and subagent seams on both surfaces', () => {
  expect(CHAT_PANEL).toContain('<ToolConfirmationDock');
  expect(CHAT_PANEL).toContain('canStopMainTurn');
  expect(THREAD_CHAT).toContain('<SubagentSidebar');
  expect(PAGE).not.toContain('pendingToolConfirmation');
  expect(CHAT_PANEL).toContain('loading={chatLoading}');
  expect(CHAT_PANEL).toContain('onStop={canStopMainTurn ? handleStop : undefined}');
});

test('Dream initial idle is only a baseline; settlement comes from ChatPanel recovery', () => {
  expect(THREAD_CHAT).toContain('if (expectedMessageId === null) return');
  expect(THREAD_CHAT).not.toContain('baselineTurnCount');
  expect(THREAD_CHAT).not.toContain('status.turn_count > baselineTurnCount');
  expect(THREAD_CHAT).toContain('onConversationSettled={notifySettled}');
  expect(THREAD_CHAT).toContain('claudeThreadExpectedDispatchIsTerminal');
  expect(THREAD_CHAT).toContain('settledExpectedMessageIdsRef');
  expect(THREAD_CHAT).toContain('key={`${threadId}:${terminalHistoryGeneration}`}');
});

test('Dream confirmation keeps the exact accepted message latch through the shared panel', () => {
  expect(PAGE).toContain('const accepted = await confirmation.submit(started.command)');
  expect(PAGE).toContain('setExpectedConfirmationMessageId(accepted.messageId)');
  expect(PAGE).toContain('expectedMessageId={expectedConfirmationMessageId}');
  expect(PANEL).toContain('expectedMessageId={expectedMessageId}');
});

test('mobile focus cycle remains bounded after runtime convergence', () => {
  expect(storyWorkspaceDreamAgentFocusCycleIndex(-1, 3, false)).toBe(-1);
  expect(storyWorkspaceDreamAgentFocusCycleIndex(2, 3, false)).toBe(0);
  expect(storyWorkspaceDreamAgentFocusCycleIndex(0, 3, true)).toBe(2);
});

test('conversation dialog reserves no empty workflow row on desktop or mobile', () => {
  expect(DREAM_CSS.match(
    /\.story-workspace-dream-agent-dialog--conversation\s*\{[^}]*grid-template-rows:\s*auto minmax\(0, 1fr\);/gs,
  )).toHaveLength(2);
});

test('shared Chat auto-scroll never delegates to scrollable page ancestors', () => {
  expect(CHAT_PANEL).not.toContain('scrollIntoView(');
  expect(CHAT_PANEL).toContain("element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })");
  expect(CHAT_PANEL).toContain("overscrollBehaviorY: 'contain'");
});
