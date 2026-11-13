// [Sync] 2026-11-13: include scoped Chinese composer visual coverage.
// [Input] Scoped provider-free Chat tools, normal Chat routing and existing composer/navigation specs with installed Chrome.
// [Output] Serial component verification and owned evidence under output/chat-tools-20261113.
// [Pos] Technical harness only; existing services and normal accounts remain outside this run.
import {defineConfig} from '@playwright/test';
export default defineConfig({
  testDir:'..',
  testIgnore:['**/ios/**','**/android/**','**/node_modules/**','**/.next/**','**/output/**'],
  testMatch:['**/chat-tools.spec.ts','**/chat-composer-zh.spec.ts','**/chat-route-cache.spec.ts','**/AIInputDockSlashMenuRegression.test.ts','**/ThreadInputQueue.test.ts','**/more-navigation.spec.ts','**/native-more-navigation.spec.ts','**/native-mcp-resources.spec.ts'],
  workers:1,fullyParallel:false,maxFailures:1,timeout:60_000,reporter:'list',use:{channel:'chrome'},
  outputDir:'../output/chat-tools-20261113/browser',
});
