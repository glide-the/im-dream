// [Input] Dream page/dialog/panel source, responsive CSS, and shared thread chat adapter.
// [Output] Architectural/layout regression gate: Dream composes ChatPanel,
//          exposes the bound-thread Chat handoff, and reserves no obsolete row.
// [Sync] 2026-08-13: require the desktop and mobile conversation dialog to allocate
//                    exactly a header row plus one minmax thread row.
// [Sync] 2026-08-13: require Chat auto-scroll to target only its owned message region,
//                    never scrollable Story Workspace ancestors via scrollIntoView.
// [Sync] 2026-08-13: require both Dream Agent surfaces to open their bound Chat thread.
// [Sync] 2026-08-14: require the Execution draft/sync switch beside Chat.
// [Sync] 2026-09-02: require both Chat hosts to share one paged historical-turn renderer.

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
const MESSAGE_LIST = readFileSync(new URL('../../../components/chat/ChatMessageList.tsx', import.meta.url), 'utf8');
const RAIL = readFileSync(new URL('../../../components/story-workspace/dream/StoryWorkspaceDreamAgentRail.tsx', import.meta.url), 'utf8');
const ROUTER = readFileSync(new URL('../../../router/story-workspace.tsx', import.meta.url), 'utf8');
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

test('Chat and Dream share one paged message list and one historical turn projector', () => {
  expect(THREAD_CHAT).toContain('initialHistoryPage={{');
  expect(CHAT_PANEL).toContain('<ChatMessageList');
  expect(CHAT_PANEL).toContain('loadOlderHistory');
  expect(CHAT_PANEL).toContain('historicalMessageIds={historicalMessageIds}');
  expect(MESSAGE_LIST).toContain('<AssistantTurnGroup');
  expect(MESSAGE_LIST).toContain('projectHistoricalAssistantTurn(message)');
  expect(THREAD_CHAT).not.toContain('projectHistoricalAssistantTurn');
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

test('Dream rail and execution dialog hand the exact bound thread to canonical Chat', () => {
  expect(RAIL).toContain("onOpenChatThread(threadId)");
  expect(DIALOG).toContain("onOpenChatThread(threadId)");
  expect(RAIL).toContain('Chat ↗');
  expect(DIALOG).toContain('Chat ↗');
  expect(ROUTER).toContain('handleNavigate(STORY_WORKSPACE_PATHS.chat, undefined, threadId)');
  expect(ROUTER).toContain('onChatThreadRequest?.(chatThreadId)');
});

test('execution dialog switches the page between default draft and sync views beside Chat', () => {
  const switchStart = DIALOG.indexOf('aria-label="工作台视图"');
  const chatStart = DIALOG.indexOf('aria-label="在 Chat 中打开当前 thread"');
  expect(switchStart).toBeGreaterThan(-1);
  expect(chatStart).toBeGreaterThan(switchStart);
  expect(DIALOG).toContain('aria-controls="story-workspace-draft-surface"');
  expect(DIALOG).toContain('aria-controls="story-workspace-sync-surface"');
  expect(DIALOG).toContain("onWorkspaceViewChange(view)");
  expect(EXECUTION).toContain("useState<StoryWorkspaceExecutionView>('draft')");
  expect(EXECUTION).not.toContain('Dream 初稿阶段投影');
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
