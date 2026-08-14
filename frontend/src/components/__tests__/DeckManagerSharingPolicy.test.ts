// [Input] DeckManager source, Deck API DTO, and localized sharing copy.
// [Output] Lock actor-owned publication rendering and server-derived eligibility use.
// [Pos] Source contract regression for Deck management sharing behavior.
// [Sync] 2026-08-14: add My Published Decks and no-self-collection coverage.

// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

declare const process: { cwd(): string };

const COMPONENT = readFileSync(resolve(process.cwd(), 'src/components/DeckManager.tsx'), 'utf8');
const API = readFileSync(resolve(process.cwd(), 'src/api/voiceApi.ts'), 'utf8');
const I18N = readFileSync(resolve(process.cwd(), 'src/i18n.ts'), 'utf8');

test('Deck Manager renders only the actor-owned published subset', () => {
  expect(COMPONENT).toContain('decks.filter((deck) => deck.published)');
  expect(COMPONENT).toContain("t('deck.sections.publishedByMe'");
  expect(COMPONENT).toContain("t('deck.publishedByMeEmpty')");
  expect(COMPONENT).not.toContain('listDecks(true)');
  expect(COMPONENT).not.toContain('handleInstallDeck');
});

test('system-default publication state comes from the server DTO', () => {
  expect(API).toContain('can_publish?: boolean;');
  expect(API).toContain("publish_block_reason?: 'default_initialized' | null;");
  expect(COMPONENT).toContain('deck.can_publish === false');
  expect(COMPONENT).toContain("t('deck.actions.publishUnavailable')");
  expect(I18N).toContain("publishedByMe: '我发布的卡组（{{count}}）'");
  expect(I18N).toContain("defaultDeckPublishForbidden: '系统默认初始化的 Deck 不能发布。'");
});

test('own publication cards offer unpublish, never collection', () => {
  expect(COMPONENT).toContain('publishedDecks.map(deck =>');
  expect(COMPONENT).toContain('onClick={() => handlePublishToggle(deck.id)}');
  expect(COMPONENT).not.toContain('onClick={() => handleInstallDeck(deck.id)}');
});
