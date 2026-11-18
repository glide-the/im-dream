// [Input] Production Notion presentation contracts, shared Modal/history regressions and installed Chrome.
// [Output] Bounded serial technical validation, excluding native build copies.
// [Pos] Provider-free harness only; no normal services, account writes or model calls.
// [Sync] 2026-11-18: scope NotionRenderer qualification to original source specs.
import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir: '../app/_dream/components/chat/__tests__',
  testMatch: ['NotionWorkspacePreview*.test.ts', 'notionRecordMapAdapter.test.ts', 'WorkspaceReportPreview.test.ts', 'AssistantTurnGroup.browser.test.ts', 'ChatHistoryProcessLazyLoad.browser.test.ts'],
  workers: 1, fullyParallel: false, timeout: 60_000, reporter: 'line',
  use: {channel: 'chrome'}, outputDir: '../output/notion-preview-20261118',
});
