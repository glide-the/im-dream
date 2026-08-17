// [Input] Chat source, Deck DTO, and shell fallback after Dream Agent unification.
// [Output] Static regression coverage for the red-box tab replacement, two-state horizontal card list,
//          whole-card run links, dispatch split, historical selector removal, same-Deck Agent switching,
//          and workbench navigation.
// [Pos] Chat/Dream Agent Deck integration source seam.
// [Sync] 2026-08-15: historical threads keep top context and omit the immutable composer selector.
// [Sync] 2026-08-17: historical threads switch only among enabled Agents in their bound Deck.

// @ts-expect-error Playwright Node seam reads source only; browser app omits Node types.
import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const CHAT = readFileSync(new URL('../ChatView.tsx', import.meta.url), 'utf8');
const CHAT_CSS = readFileSync(new URL('../ChatView.css', import.meta.url), 'utf8');
const SHELL = readFileSync(new URL('../ChatShellError.tsx', import.meta.url), 'utf8');
const DECK_CONTEXT = readFileSync(new URL('../PluginReceiptBadge.tsx', import.meta.url), 'utf8');
const CHAT_PANEL = readFileSync(new URL('../ChatPanel.tsx', import.meta.url), 'utf8');
const DECK_API = readFileSync(new URL('../../../api/voiceApi.ts', import.meta.url), 'utf8');

test('Chat replaces only the connector peer tab with actor-scoped resumable Dreams', () => {
  expect(SHELL).toContain("export type ChatLandingTab = 'history' | 'dreams'");
  expect(CHAT).toContain("handleSelectWorkspaceTab('dreams')");
  expect(CHAT).toContain('dreamRuns.data?.runs ?? []');
  expect(CHAT).toContain("t('chat.tabs.activeDreams', { count: dreamReentryRuns.length })");
  expect(CHAT).toContain('storyWorkspaceDreamReentryOutcomeCopy(run.outcome)');
  expect(CHAT).toContain('href={run.href}');
  expect(CHAT).toContain('openDreamRun(run.href)');
  expect(CHAT).toMatch(/<article[\s\S]*?<a[\s\S]*?href=\{run\.href\}/);
  expect(CHAT).not.toContain('<ConnectorLandingPanel');
  expect(SHELL).not.toContain("'connector'");
});

test('Chat Dream rows use one adaptive horizontal scroller without vertical nesting', () => {
  expect(CHAT).toContain('className="chat-dream-reentry-scroller"');
  expect(CHAT).toContain('role="list"');
  expect(CHAT_CSS).toMatch(/\.chat-dream-reentry-scroller\s*\{[^}]*grid-auto-flow: column;[^}]*overflow-x: auto;[^}]*overflow-y: hidden;/s);
  expect(CHAT_CSS).toContain('grid-auto-columns: minmax(min(78vw, 17rem), 1fr)');
  expect(CHAT_CSS).toContain('scroll-snap-type: inline proximity');
});

test('Chat trusts server Deck type and reuses the existing Dream launch hook', () => {
  expect(DECK_API).toContain("agent_type: 'chat' | 'dream'");
  expect(CHAT).toContain("selectedDeck?.agent_type !== 'dream'");
  expect(CHAT).toContain('await dreamLaunch.start(selectedDeck.id, selectedAgentId, message)');
  expect(CHAT).toContain('openDreamRun(storyWorkspaceDreamRunPath(accepted.workflowRunId))');
  expect(CHAT).toContain('await startThreadWithQueuedSend(message, uploadedFiles, toolChoice)');
  expect(CHAT).toContain('readStoryWorkspaceDeckParam(query)');
  expect(CHAT).not.toContain('isDream=true');
});

test('historical Chat hides the Deck selector and exposes same-Deck Agent switching in top context', () => {
  const activeThreadStart = CHAT.indexOf("activeThreadId && landingTab === 'history' ?");
  const activeThreadBranch = CHAT.slice(
    activeThreadStart,
    CHAT.indexOf('              ) : (', activeThreadStart),
  );
  expect(activeThreadBranch).not.toContain('inputContextControl');
  expect(activeThreadBranch).not.toContain('<DeckChatSelector');
  expect(CHAT).not.toContain('locked');
  expect(CHAT).toContain('const displayVoice = threadVoiceEntry');
  expect(CHAT).toContain('<PluginReceiptBadge');
  expect(CHAT).toContain('onSelectAgent={activeThreadId ? setSelectedAgentId : undefined}');
  expect(DECK_CONTEXT).toContain('{deckName ?? (hasReceiptPlugins ? (');
  expect(DECK_CONTEXT).toContain("t('chat.deck.metadataPlugins')");
  expect(DECK_CONTEXT).toContain("t('chat.deck.switchAgent'");
  expect(DECK_CONTEXT).toContain('aria-pressed={isCurrent}');
  expect(DECK_CONTEXT).toContain('onSelectAgent?.(voice.id)');
  expect(CHAT_PANEL).toContain('const requestContext = requestContextRef.current');
  expect(CHAT_PANEL).toContain('voiceId: requestContext.voiceId');
});
