// [Sync] 2026-10-30: qualify native login completion/cancellation before the home session is adopted.
// [Sync] 2026-10-29: register native resource content and original operation/CAS/selection recovery qualification.
// [Sync] 2026-10-29: register native More/Timeline composition and original Writing document technical qualification.
// [Sync] 2026-10-29: qualify shared Reflections state, native source/report controls and original task recovery.
// [Sync] 2026-10-29: qualify shared Work plugin state, native controls and production Next read identity.
// [Sync] 2026-10-29: qualify shared Memory responses and read-only subscription/About platform presentation.
// [Sync] 2026-10-29: qualify native display preferences, real More theme action and original General config ownership.
// [Sync] 2026-10-29: include narrow Web/native More navigation parity and desktop-preservation checks.
// [Sync] 2026-10-29: include shared model-settings Web regression and native configuration save/recovery fixtures.
// [Sync] 2026-10-29: include original Deck maintenance/CAS/confirmation through native UI with fixture-only HTTP.
// [Sync] 2026-10-29: qualify original Deck visibility/preview and native draft-only selection before adoption.
// [Sync] 2026-10-29: include original plugin metadata/read lifecycle parity before native adoption.
// [Sync] 2026-10-28: include the single-request Deck/Agent catalog transport contract.
// [Sync] 2026-10-28: register native HTTP cancellation before headers and existing read/SSE cleanup qualification.
// [Sync] 2026-10-28: register provider-free native startup configuration/catalog retry qualification.
// [Sync] 2026-10-28: include original Workspace URI/media contracts and Native private-resource validation.
// [Sync] 2026-10-28: include original Web activity/detail contracts and native read-only drawer verification.
// [Sync] 2026-10-28: include production native Markdown, history disclosure and scroll/copy boundary regression.
// [Input] Installed Chrome, canonical Next Web origin and existing provider-free regression specs.
// [Output] One bounded Web regression lane with isolated reports and no backend/model execution.
// [Pos] Explicit technical harness configuration; production app configuration remains unchanged.
// [Sync] 2026-10-28: include shared Deck/Chat compatibility and original Skill catalog contracts in the Web gate.
import {defineConfig} from '@playwright/test';
import {fileURLToPath} from 'node:url';
export default defineConfig({
  testDir:fileURLToPath(new URL('../',import.meta.url)),
  testIgnore:['**/ios/**','**/android/**','**/legacy/**','**/node_modules/**'],
  testMatch:[
    'e2e/next-config.test.ts',
    'e2e/chat-image-share.spec.ts',
    'e2e/native-share.spec.ts',
    'e2e/native-chat-setup.spec.ts',
    'e2e/deck-catalog.spec.ts',
    'e2e/deck-presentation.spec.ts',
    'e2e/native-deck-management.spec.ts',
    'e2e/image-model-settings.spec.ts',
    'e2e/native-model-settings.spec.ts',
    'e2e/native-appearance.spec.ts',
    'e2e/native-settings-categories.spec.ts',
    'e2e/native-work-plugins.spec.ts',
    'e2e/native-notion-resources.spec.ts',
    'e2e/native-mcp-resources.spec.ts',
    'e2e/native-reflections.spec.ts',
    'e2e/native-timeline.spec.ts',
    'e2e/native-more-navigation.spec.ts',
    'e2e/writing-document.spec.ts',
    'e2e/reflections-analysis-content.spec.ts',
    'app/_dream/components/__tests__/ReflectionHistory.test.ts',
    'app/_dream/components/__tests__/ClaudePluginMarketplace.test.ts',
    'e2e/memory-behavior.spec.ts',
    'e2e/story-workspace-subscription.spec.ts',
    'app/_dream/views/story-workspace/__tests__/StoryWorkspaceSubscriptionPage.test.ts',
    'e2e/more-navigation.spec.ts',
    'e2e/story-workspace-default-entry.spec.ts',
    'e2e/plugin-receipt-badge.spec.ts',
    'e2e/native-http-cancellation.spec.ts',
    'e2e/workspace-file-sidebar.spec.ts',
    'e2e/native-activity.spec.ts',
    'e2e/native-workspace-files.spec.ts',
    'app/_dream/components/chat/__tests__/WorkspaceUriPreview.test.ts',
    'app/_dream/components/chat/__tests__/ActivitySidebar.browser.test.ts',
    'app/_dream/components/chat/__tests__/ScheduledTaskActivity.browser.test.ts',
    'app/_dream/components/chat/__tests__/ActivitySidebarModel.test.ts',
    'e2e/composer-draft.spec.ts',
    'e2e/composer-document.spec.ts',
    'e2e/sketch-document.spec.ts',
    'e2e/file-upload-adapter.spec.ts',
    'e2e/web-shared-context.spec.ts',
    'e2e/native-chat-session.spec.ts',
    'e2e/native-chat-history.spec.ts',
    'e2e/native-messages.spec.ts',
    'e2e/native-sdk-web-apis.spec.ts',
    'e2e/sketch-input.spec.ts',
    'e2e/native-session-gate.spec.ts',
    'e2e/auth-entry-recovery.spec.ts',
    'e2e/chat-first-deck-defaults.spec.ts',
    'e2e/chat-dream-agent-refactor.spec.ts',
    'app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts',
    'app/_dream/components/chat/__tests__/SlashSkillCommands.test.ts',
    'app/_dream/components/chat/__tests__/ChatStopControl.test.ts',
    'app/_dream/components/chat/__tests__/ThreadInputQueue.test.ts',
    'app/_dream/components/chat/__tests__/ThreadSessionHydration.test.ts',
    'app/_dream/components/chat/__tests__/ToolConfirmationRecovery.test.ts',
    'app/_dream/components/chat/__tests__/AskUserQuestionMultiSelect.test.ts',
  ],
  workers:1,fullyParallel:false,timeout:120_000,expect:{timeout:10_000},
  outputDir:'/tmp/ink-web-rnw-regression-20261028/test-results',
  reporter:[['list'],['json',{outputFile:'/tmp/ink-web-rnw-regression-20261028/results.json'}]],
  use:{
    viewport:{width:1200,height:800},
    launchOptions:{executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'},
    screenshot:'only-on-failure',trace:'retain-on-failure',
  },
});
