// [Input] Existing source/API and synthetic browser share specifications with installed Chrome.
// [Output] Focused provider-free share validation with one worker and owned local artifacts.
// [Pos] Technical test orchestration; normal services, accounts, databases and models remain outside this run.
// [Sync] 2026-11-13: include Chat/share parity, settled PNG capture and external-link action/settings journeys.
import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir: '..',
  testMatch: ['**/external-links.spec.ts', '**/chat-share-layout.spec.ts', '**/ExternalShareApi.test.ts', '**/note-share.spec.ts', '**/note-share-boundaries.spec.ts', '**/native-share.spec.ts'],
  fullyParallel: false,
  workers: 1,
  maxFailures: 1,
  timeout: 60_000,
  reporter: 'list',
  use: {channel: 'chrome'},
  outputDir: '../test-results/external-sharing',
});
