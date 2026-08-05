// [Input] Dream-only Agent message surfaces and their shared renderer source.
// [Output] Static safety and structure contracts for ordered public activity rendering.
// [Pos] Story Workspace Dream Agent message-list Node seam (U3 Red/Green).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam uses built-ins omitted from the browser app types.
import { existsSync, readFileSync } from 'node:fs';

function readSource(url: URL): string {
  return existsSync(url) ? readFileSync(url, 'utf8') : '';
}

const LIST = readSource(new URL('../StoryWorkspaceDreamAgentMessageList.tsx', import.meta.url));
const LIST_CSS = readSource(new URL('../StoryWorkspaceDreamAgentMessageList.css', import.meta.url));
const PANEL = readSource(new URL('../StoryWorkspaceDreamAgentPanel.tsx', import.meta.url));
const DIALOG = readSource(new URL('../StoryWorkspaceDreamAgentDialog.tsx', import.meta.url));

test('Panel and Dialog delegate ordered Dream messages to one shared renderer', () => {
  expect(LIST).toContain('content.map((part, index) =>');
  expect(LIST).toContain('content={message.content}');
  expect(LIST).toContain("import ChatMarkdown from '../../chat/ChatMarkdown'");
  for (const surface of [PANEL, DIALOG]) {
    expect(surface).toContain("import { StoryWorkspaceDreamAgentMessageList } from './StoryWorkspaceDreamAgentMessageList'");
    expect(surface.match(/<StoryWorkspaceDreamAgentMessageList/g)).toHaveLength(1);
    expect(surface).not.toContain('message.content.map');
  }
});

test('safe activities are native collapsed disclosures with fixed status presentation', () => {
  expect(LIST).toContain('<details');
  expect(LIST).toContain('<summary>');
  expect(LIST).not.toMatch(/<details[^>]*\sopen(?:=|\s|>)/);
  expect(LIST).toContain("running: { icon: '◌', label: '进行中'");
  expect(LIST).toContain("completed: { icon: '✓', label: '已完成'");
  expect(LIST).toContain("stopped: { icon: '◇', label: '已停止'");
  expect(LIST).toContain('aria-hidden="true"');
  expect(LIST).toContain('仅展示 Dream Agent 的安全过程摘要。');
});

test('Dream message renderer cannot reach generic Chat surfaces or raw tool data', () => {
  for (const forbidden of [
    'ChatPanel',
    'ChatMessageList',
    'ToolMessagePart',
    'ChatView',
    'ChatWidgetUI',
    'thread transport',
    'toolName',
    'toolCallId',
    'input',
    'output',
    'error',
    'reasoning',
    'command',
    'parameters',
    'args',
    'result',
    'path',
    'filePath',
  ]) {
    expect(LIST).not.toContain(forbidden);
  }
  expect(LIST).toContain("import './StoryWorkspaceDreamAgentMessageList.css'");
});

test('Panel removes its duplicate title while retaining a focus-safe return control', () => {
  expect(PANEL).not.toContain('<header>');
  expect(PANEL).not.toContain('<strong>当前 Dream 对话</strong>');
  expect(PANEL).toContain('className="story-workspace-dream-agent-panel__controls"');
  expect(PANEL).toContain('返回 Dream 内容');
  expect(PANEL).toContain('onClick={closePanel}');
  expect(PANEL).toContain('requestAnimationFrame(() => restoreFocusRef.current?.focus())');
});

test('shared message list keeps streaming and empty states inside a quiet paper log', () => {
  for (const surface of [PANEL, DIALOG]) {
    expect(surface).toContain('messages={agent.snapshot?.messages ?? []}');
    expect(surface).toContain('streamContent={agent.streamContent}');
    expect(surface).toContain('streamText={agent.streamText}');
  }
  expect(LIST).toContain('Dream Agent 正在输出');
  expect(LIST).toContain('正在准备可展示的 Dream Agent 消息。');
  expect(LIST_CSS).toContain('var(--dream-paper)');
  expect(LIST_CSS).toContain('var(--dream-rule)');
  expect(LIST_CSS).toContain(':focus-visible');
  expect(LIST_CSS).toContain('@media (prefers-reduced-motion: reduce)');
});
