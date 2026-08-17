// [Input] Enabled-only Deck home, Settings / Work management, original create flow, maintenance popup, constants, and APIs.
// [Output] Lock home projection, Work ownership, related Chat cleanup, and Deck versions.
// [Pos] Source-contract regression for Deck management scope.
// [Sync] 2026-08-16: require enabled-only Deck launch plus Settings / Work tabs and Work-owned switches.
// [Sync] 2026-08-17: require More → related Chat previews and locale-owned Work labels.
// [Sync] 2026-08-17: require Available/System Deck launcher groups with static system-default behavior.

// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error source-contract tests run in Node outside the frontend tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

declare const process: { cwd(): string };

const read = (path: string) => readFileSync(resolve(process.cwd(), path), 'utf8');
const COMPONENT = read('src/components/DeckManager.tsx');
const PANELS = read('src/components/deck/DeckManagerPanels.tsx');
const DETAILS = read('src/components/DeckEditorModal.tsx');
const DETAILS_STYLES = read('src/components/DeckEditorModal.css');
const VERSION_PANEL = read('src/components/deck/DeckVersionPanel.tsx');
const VERSION_DIALOG = read('src/components/deck/DeckVersionSubmitDialog.tsx');
const VERSION_API = read('src/api/deckVersionApi.ts');
const VERSION_HOOK = read('src/hooks/useDeckContentVersions.ts');
const PLUGIN_API = read('src/api/deckPluginApi.ts');
const API = read('src/api/voiceApi.ts');
const CHAT_API = read('src/api/chatHistoryApi.ts');
const I18N = read('src/i18n.ts');
const STYLES = read('src/components/deck/DeckManagerPanels.css');
const CONSTANTS = read('src/constants/deck.ts');
const APP = read('src/App.tsx');
const SETTINGS = read('src/pages/story-workspace/StoryWorkspaceSettingsPage.tsx');
const PATHS = read('src/router/storyWorkspacePath.ts');
const PDF_TRACE = read('../docs/design/deck/deck-pdf-requirement-trace.md');
const EVALUATOR_DESIGN = read('../docs/design/deck/deck-evaluator-interaction-draft.md');

test('Deck home uses published-clean enabled shortcuts with system markers while full inventory stays in Work', () => {
  const launcher = PANELS.slice(
    PANELS.indexOf('export function DeckLaunchPanel'),
    PANELS.indexOf('export function DeckSettingsPanel'),
  );
  const settingsPanel = PANELS.slice(PANELS.indexOf('export function DeckSettingsPanel'));
  expect(COMPONENT).toContain('<DeckLaunchPanel');
  expect(COMPONENT).toContain('<DeckSettingsPanel');
  expect(COMPONENT).toContain("surface === 'launcher'");
  expect(PDF_TRACE).toContain('5d440adc56e73b4269fcf7886933df021355399ed69854783460cf3e2d1c3671');
  expect(launcher).toContain('deck-manager-home__header');
  expect(launcher).toContain('deck-manager-search--launcher');
  expect(launcher).toContain('deck-manager-enabled__strip');
  expect(launcher).toContain('decks.filter(isDeckHomeVisible)');
  expect(launcher).toContain('visibleHomeDecks.slice(0, DECK_ENABLED_LAUNCH_LIMIT)');
  expect(PANELS).toContain("deck.deck_version_status === 'published'");
  expect(PANELS).toContain('deck.deck_version_dirty === false');
  expect(PANELS).toContain('deck.deck_version > 0');
  expect(launcher).toContain('deck-manager-enabled__item--system');
  expect(launcher).toContain('deck-manager-enabled__system-marker');
  expect(launcher).toContain('deck-manager-launch-card--system');
  expect(launcher).toContain('userVisibleDecks');
  expect(launcher).toContain('systemVisibleDecks');
  expect(launcher).toContain('<DeckLaunchGroup');
  expect(PANELS).toContain('function DeckLaunchGroup');
  expect(PANELS).toContain('isSystemDeckDisplay');
  expect(PANELS).toContain("deck.publish_block_reason === DEFAULT_INITIALIZED_DECK_REASON");
  expect(launcher).toContain("visibleDecks.filter((deck) => !isSystemDeckDisplay(deck))");
  expect(launcher).toContain('visibleDecks.filter(isSystemDeckDisplay)');
  expect(launcher).toContain("t('deck.home.availableListTitle')");
  expect(launcher).toContain("t('deck.home.systemListTitle')");
  expect(launcher).toContain("t('deck.home.availableListLabel')");
  expect(launcher).toContain("t('deck.home.systemListLabel')");
  expect(launcher).toContain('disabled={isSystemDeckDisplay(deck)}');
  expect(launcher).toContain("t('deck.home.systemDeckLabel'");
  expect(launcher).toContain("t('deck.labels.system')");
  expect(launcher).toContain('deck-manager-enabled__settings');
  expect(launcher).toContain('onClick={onOpenSettings}');
  expect(launcher).not.toContain('deck-manager-list');
  expect(launcher).not.toContain('deck-manager-enabled__item--settings');
  expect(launcher).not.toContain('{enabledDecks.length} / {DECK_ENABLED_LAUNCH_LIMIT}');
  expect(launcher).not.toContain('role="switch"');
  expect(settingsPanel).toContain('deck-manager-search');
  expect(settingsPanel).toContain('<ul aria-label={t(\'deck.creator.listLabel\')} className="deck-manager-list">');
  expect(settingsPanel).toContain('role="switch"');
  expect(PANELS).not.toContain('<table');
  expect(settingsPanel).toContain('type="search"');
  expect(settingsPanel).toContain('role="tablist"');
  expect(settingsPanel).toContain("t('deck.creator.statusFilter')");
  expect(PANELS).toContain('DECK_MANAGEMENT_PAGE_SIZE');
  expect(PANELS).toContain("t('deck.pagination.summary'");
  expect(CONSTANTS).toContain('DECK_MANAGEMENT_PAGE_SIZE = 10');
  expect(CONSTANTS).toContain('DECK_ENABLED_LAUNCH_LIMIT = 14');
  expect(STYLES).toContain('max-width: 57.5rem');
  expect(STYLES).toContain('max-width: 52.5rem');
  expect(STYLES).toContain('grid-template-columns: repeat(auto-fill, 44px)');
  expect(STYLES).toContain(".deck-manager-enabled__strip > [role='listitem']");
  expect(STYLES).toContain('aspect-ratio: 1');
  expect(STYLES).toContain('.deck-manager-enabled__settings');
  expect(STYLES).toContain('.deck-manager-launch-catalog__grid');
  expect(STYLES).toContain('.deck-manager-launch-catalog__groups');
  expect(STYLES).toContain('.deck-manager-launch-group h3');
  expect(STYLES).toContain('.deck-manager-enabled__item--system');
  expect(STYLES).toContain('.deck-manager-launch-card--system');
  expect(STYLES).toContain('.deck-manager-list__row');
  expect(STYLES).toContain('@media (max-width: 640px)');
  expect(STYLES).not.toContain('.deck-manager-table');
  expect(SETTINGS).toContain("id: 'settings-work'");
  expect(SETTINGS).toContain("label: t('settings.workspace.navigation.work')");
  expect(SETTINGS).toContain("{t('settings.workspace.work.title')}");
  expect(SETTINGS).not.toContain('工作台 / Work');
  expect(SETTINGS).not.toContain("{ id: 'settings-resources', label: '资源连接'");
  expect(SETTINGS).not.toContain("{ id: 'settings-plugins', label: '插件'");
  expect(SETTINGS).toContain("label: t('settings.workspace.work.tabs.deck')");
  expect(SETTINGS).toContain("label: t('settings.workspace.work.tabs.resources')");
  expect(SETTINGS).toContain("label: t('settings.workspace.work.tabs.plugins')");
  expect(I18N).toContain("work: 'Work'");
  expect(I18N).toContain("work: '工作台'");
  expect(I18N).toContain("title: 'Work'");
  expect(I18N).toContain("title: '工作台'");
  expect(I18N).toContain("availableListTitle: 'Available Decks'");
  expect(I18N).toContain("systemListTitle: 'System Decks'");
  expect(I18N).toContain("availableListTitle: '可用 Deck'");
  expect(I18N).toContain("systemListTitle: '系统 Deck'");
  expect(PATHS).toContain("'settings-work': '/story-workspace/settings/work'");
  expect(APP).toContain('onOpenSettings={handleOpenSettingsFromDeck}');
  expect(APP).toContain("STORY_WORKSPACE_PATHS['settings-work']");
  expect(APP).toContain('workDeckContent={storyWorkspaceDeckSettingsManager}');
});

test('PDF creation menu preserves the original create-then-popup business path', () => {
  expect(PANELS).toContain('aria-haspopup="menu"');
  expect(PANELS).toContain('aria-expanded={createMenuOpen}');
  expect(PANELS).toContain('deck-manager-menu--create');
  expect(PANELS).toContain('onClick={openCreateDialog}');
  expect(COMPONENT).toContain('const created = await createDeck({');
  expect(COMPONENT).toContain('setActiveDeckId(created.deck_id)');
  expect(COMPONENT).not.toContain('createDialogOpen');
  expect(CONSTANTS).toContain('DEFAULT_DECK_CREATE_VISUAL');
  expect(PANELS).not.toMatch(/Add Deck Market|添加 Deck 市场/);
});

test('refresh failure keeps the last list and mutations preserve server ownership', () => {
  expect(COMPONENT).toContain('setRefreshError(message)');
  expect(COMPONENT).toContain('await updateDeck(deckId, { enabled: !currentEnabled })');
  expect(COMPONENT).toContain('await loadDecks({ preserveScroll: true })');
  expect(PANELS).toContain('refreshError &&');
  expect(PANELS).toContain('operationError &&');
  expect(PANELS).toContain('role="switch"');
  expect(PANELS).toContain('const disabled = busyDeckId === deck.id;');
  expect(PANELS).toContain('disabled={disabled}');
});

test('Work More exposes Deck-related Chat previews and deletes through shared Chat transport', () => {
  expect(PANELS).toContain("t('deck.actions.relatedConversations')");
  expect(PANELS).toContain('onLoadRelatedThreads(deck.id, offset)');
  expect(PANELS).toContain('onDeleteRelatedThread(thread.id)');
  expect(PANELS).toContain('deck-manager-related-list__item');
  expect(PANELS).toContain("t('deck.related.readyHint')");
  expect(PANELS).toContain('|| Boolean(relatedThreadsError)');
  expect(PANELS).toContain('|| relatedThreadsHasMore}');
  expect(COMPONENT).toContain('listChatThreads({ deckId, limit: 20, offset })');
  expect(COMPONENT).toContain('await deleteChatThread(threadId)');
  expect(CHAT_API).toContain("search.set('deck_id', params.deckId)");
  expect(CHAT_API).toContain("method: 'DELETE'");
  expect(STYLES).toContain('.deck-manager-related-dialog');
  expect(STYLES).toContain('.deck-manager-related-list__item');
});

test('details popup restores the pre-01a00576 Deck maintenance scope without Workflow', () => {
  expect(API).toContain('export interface DeckDetailsInput');
  expect(COMPONENT).toMatch(/createVoice|updateVoice|deleteVoice|updateDeckAgentType/);
  expect(COMPONENT).toContain('const decksWithVoices = await Promise.all');
  expect(DETAILS).toContain('DeckClaudePluginSelector');
  expect(DETAILS).toContain('Agent Prompt');
  expect(DETAILS).toContain('onAddVoice(deck.id)');
  expect(DETAILS).toContain('onChatWithDeck(deck.id');
  expect(APP).toContain('onChatWithDeck={handleChatWithDeck}');
  expect(DETAILS).not.toMatch(/Workflow|工作流|memory_workspace_config/);
  expect(EVALUATOR_DESIGN).toContain('> 状态：有效并持续维护');
  expect(EVALUATOR_DESIGN).not.toMatch(/已废止|状态：废止/);
  expect(EVALUATOR_DESIGN).toContain('本稿不包含 Workflow');
  expect(EVALUATOR_DESIGN).toContain('a5f3bf3');
});

test('market distribution is absent from current Deck management UI and copy', () => {
  const currentSurface = [COMPONENT, PANELS, DETAILS, I18N].join('\n');
  expect(currentSurface).not.toMatch(/Publish to Community|发布到社区|publishedByMe|communityMeta|publishWarning/);
  expect(COMPONENT).not.toMatch(/publishDeck|handlePublish|publishWarning/);
  expect(PANELS).not.toMatch(/publishedDecks|install_count|is-published|onPublish|onUnpublish|community/);
  expect(COMPONENT).not.toContain('forkDeck');
  expect(PANELS).not.toContain('onForkDeck');
  expect(PANELS).not.toContain("t('deck.actions.fork')");
});

test('Deck content versions use draft preview and explicit immutable commits', () => {
  const currentSurface = [COMPONENT, PANELS, DETAILS, I18N].join('\n');
  expect(PANELS).toContain('deck.deck_plugin_version');
  expect(PANELS).toContain('deck.deck_version');
  expect(PANELS).toContain('deck.deck_version_dirty');
  expect(DETAILS).toContain('aria-expanded={historyOpen}');
  expect(DETAILS).toContain('contentVersions.prepare()');
  expect(DETAILS).toContain('<DeckVersionSubmitDialog');
  expect(DETAILS).toContain('<DeckVersionPanel');
  expect(DETAILS_STYLES).toContain('flex: 0 0 300px');
  expect(DETAILS_STYLES).toContain('@media (max-width: 720px)');
  expect(VERSION_PANEL).toContain('Deck 内容版本');
  expect(VERSION_PANEL).toContain('content.history.versions');
  expect(VERSION_DIALOG).toContain('历史 Thread 不会自动升级');
  expect(VERSION_DIALOG).toContain('确认提交 v');
  expect(VERSION_API).toContain('/versions/preview');
  expect(VERSION_API).toContain('expected_draft_revision');
  expect(VERSION_HOOK).toContain('DECK_VERSION_CAPABILITY_MISSING');
  expect(PLUGIN_API).toContain('getDeckPluginBindingHistory');
  expect(currentSurface).not.toMatch(/upgradeDeck|升级版本/);
  expect(DETAILS).not.toMatch(/Workflow|工作流|memory_workspace_config/);
});
