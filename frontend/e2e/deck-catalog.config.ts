// [Input] Installed Chrome, an explicitly selected Web origin and the focused catalog contracts.
// [Output] Provider-free catalog transport and original Chat/Deck browser verification.
// [Pos] Scoped technical harness; application configuration and real user services remain separate.
import {defineConfig} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

export default defineConfig({
  testDir:fileURLToPath(new URL('.',import.meta.url)),
  testMatch:['deck-catalog.spec.ts','chat-dream-agent-refactor.spec.ts','chat-first-deck-defaults.spec.ts'],
  workers:1,fullyParallel:false,timeout:120_000,expect:{timeout:10_000},
  outputDir:process.env.CATALOG_TEST_OUTPUT ?? join(tmpdir(),'ink-deck-catalog-pr-20261029','test-results'),
  reporter:'list',
  use:{
    viewport:{width:1200,height:800},
    launchOptions:{executablePath:process.env.CHROME_EXECUTABLE_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'},
    screenshot:'only-on-failure',trace:'retain-on-failure',
  },
});
