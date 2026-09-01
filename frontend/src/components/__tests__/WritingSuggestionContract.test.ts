// [Input] Writing App wiring, suggestion Cell UI/styles/i18n, text hook, and the existing inline ChatWidgetUI.
// [Output] Lock explicit-only product Writing suggestions, latest-only regeneration, accessible responsive tokens, and ChatWidgetUI layout isolation.
// [Pos] Source-contract regression for the manual Writing suggestion presentation and composition boundary.
// [Sync] 2026-09-01: add the persistent Suggestion Cell and remove automatic/random-Voice inspiration UI.
// [Sync] 2026-09-01: require App to expose Refresh/Retry only on the latest suggestion Cell.

// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

declare const process: { cwd(): string };

const read = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');
const APP = read('src/App.tsx');
const COMPONENT = read('src/components/Editor/WritingSuggestionCell.tsx');
const STYLES = read('src/components/Editor/WritingSuggestionCell.css');
const TEXT_HOOK = read('src/hooks/useTextCells.ts');
const WRITING_HOOK = read('src/hooks/useWritingSuggestions.ts');
const VOICE_API = read('src/api/voiceApi.ts');
const CHAT_WIDGET = read('src/components/ChatWidgetUI.tsx');
const I18N = read('src/i18n.ts');

test('Writing exposes only explicit suggestion actions and keeps ChatWidgetUI isolated', () => {
  expect(APP).toContain('<WritingSuggestionTrigger');
  expect(APP).toContain('<WritingSuggestionCell');
  expect(APP).toContain("cell.type === 'writing-suggestion'");
  expect(APP).toContain('latestWritingSuggestionCellId');
  expect(APP).toContain('isLatestSuggestion={cell.id === latestWritingSuggestionCellId}');
  expect(APP).toContain("candidate.status === 'streaming'");
  expect(APP).toContain('<ChatWidgetUI');
  expect(APP).not.toContain('useInspiration');
  expect(APP).not.toContain('InspirationHint');
  expect(TEXT_HOOK).not.toContain('onInspirationTextChange');
  expect(WRITING_HOOK).not.toContain('setTimeout(');
  expect(VOICE_API).not.toContain('function getSuggestion');
  expect(VOICE_API).not.toContain('enabledVoices.length');
  expect(CHAT_WIDGET).not.toContain('WritingSuggestion');
  expect(CHAT_WIDGET).not.toContain('Go deeper');
});

test('suggestion UI uses accessible semantic-token light/dark/mobile contracts', () => {
  expect(COMPONENT).toContain("aria-busy={isStreaming}");
  expect(COMPONENT).toContain('role="status"');
  expect(COMPONENT).toContain('data-suggestion-cell-id={cell.id}');
  expect(COMPONENT).toContain("t('writingSuggestion.goDeeper')");
  expect(COMPONENT).toContain("'writingSuggestion.refresh'");
  expect(COMPONENT).toContain('isLatestSuggestion: boolean');
  expect(COMPONENT).toContain('const showAction = isLatestSuggestion');
  expect(STYLES).toContain('var(--color-action-link)');
  expect(STYLES).toContain('var(--color-border-focus)');
  expect(STYLES).toContain('@media (max-width: 767px)');
  expect(STYLES).toContain('@media (prefers-reduced-motion: reduce)');
  expect(STYLES).not.toMatch(/#[0-9a-f]{3,8}\b/i);
  expect(I18N).toContain("goDeeper: 'Go deeper'");
  expect(I18N).toContain("goDeeper: '深入一下'");
  expect(I18N).toContain("refresh: 'Refresh'");
  expect(I18N).toContain("refresh: '重新生成'");
});
