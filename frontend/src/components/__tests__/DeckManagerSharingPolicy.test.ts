// [Input] DeckManager orchestration, task-mode panels, Deck API DTO, and localized sharing copy.
// [Output] Lock use/create separation, actor-owned publications, and server-derived eligibility use.
// [Pos] Source contract regression for Deck management sharing behavior.
// [Sync] 2026-08-15: add use/create task-mode and no-fake-revision coverage.

// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

declare const process: { cwd(): string };

const COMPONENT = readFileSync(resolve(process.cwd(), 'src/components/DeckManager.tsx'), 'utf8');
const PANELS = readFileSync(resolve(process.cwd(), 'src/components/deck/DeckManagerPanels.tsx'), 'utf8');
const API = readFileSync(resolve(process.cwd(), 'src/api/voiceApi.ts'), 'utf8');
const I18N = readFileSync(resolve(process.cwd(), 'src/i18n.ts'), 'utf8');

test('Deck Manager renders only the actor-owned published subset', () => {
  expect(COMPONENT).toContain('decks.filter((deck) => deck.published)');
  expect(PANELS).toContain("t('deck.sections.publishedByMe'");
  expect(PANELS).toContain("t('deck.publishedByMeEmpty')");
  expect(COMPONENT).not.toContain('listDecks(true)');
  expect(COMPONENT).not.toContain('handleInstallDeck');
});

test('system-default publication state comes from the server DTO', () => {
  expect(API).toContain('can_publish?: boolean;');
  expect(API).toContain("publish_block_reason?: 'default_initialized' | null;");
  expect(PANELS).toContain('deck.can_publish === false');
  expect(PANELS).toContain("t('deck.actions.publishUnavailable')");
  expect(I18N).toContain("publishedByMe: '我发布的卡组（{{count}}）'");
  expect(I18N).toContain("defaultDeckPublishForbidden: '系统默认初始化的 Deck 不能发布。'");
});

test('own publication cards offer unpublish, never collection', () => {
  expect(PANELS).toContain('publishedDecks.map((deck) =>');
  expect(PANELS).toContain('onClick={() => onUnpublishDeck(deck.id)}');
  expect(PANELS).not.toContain('onClick={() => handleInstallDeck(deck.id)}');
});

test('Deck workspace defaults to read-only use mode and isolates creator writes', () => {
  expect(COMPONENT).toContain("useState<DeckManagerMode>('use')");
  expect(COMPONENT).toContain("mode === 'use'");
  expect(PANELS).toContain('role="tablist"');
  expect(PANELS).toContain('data-deck-card-kind="use"');
  expect(PANELS).toContain("t('deck.actions.useInChat')");
  expect(PANELS).toContain('data-deck-card-kind="owned"');
  expect(PANELS).toContain('role="switch"');
  expect(PANELS).not.toMatch(/\bv1\b|deck\.revision|agent_type_revision\s*\}/);
});
