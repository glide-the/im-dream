// [Input] Existing source/API and synthetic browser share specifications with installed Chrome.
// [Output] Focused provider-free share validation with one worker and owned local artifacts.
// [Pos] Technical test orchestration; normal services, accounts, databases and models remain outside this run.
import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir: '..',
  testMatch: ['**/ExternalShareApi.test.ts', '**/note-share.spec.ts', '**/note-share-boundaries.spec.ts', '**/native-share.spec.ts'],
  fullyParallel: false,
  workers: 1,
  maxFailures: 1,
  timeout: 60_000,
  reporter: 'list',
  use: {channel: 'chrome'},
  outputDir: '../test-results/external-sharing',
});
