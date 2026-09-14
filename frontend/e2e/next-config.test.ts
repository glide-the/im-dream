// [Input] Actual frontend Next config, launch cwd, backend URL and standalone option.
// [Output] Provider-free project-root, route ownership and cache-header configuration regressions.
// [Pos] Configuration tests in the existing Playwright runner; no browser/server/database required.
// [Sync] 2026-09-14: prevent ancestor lockfiles from changing React Client Manifest module identities.
import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const configUrl = new URL('../next.config.js', import.meta.url);
const projectRoot = dirname(fileURLToPath(configUrl));

function readConfig(cwd = projectRoot, overrides: Record<string, string> = {}) {
  const env = { ...process.env };
  delete env.INK_BACKEND_INTERNAL_URL;
  delete env.INK_NEXT_OUTPUT;
  return JSON.parse(execFileSync(process.execPath, ['--input-type=module', '-e', `
    import config from ${JSON.stringify(configUrl.href)};
    console.log(JSON.stringify({
      root: config.turbopack.root,
      output: config.output,
      reactStrictMode: config.reactStrictMode,
      poweredByHeader: config.poweredByHeader,
      headers: await config.headers(),
      rewrites: await config.rewrites(),
    }));
  `], { cwd, env: { ...env, ...overrides }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }));
}

test('frontend root is absolute and comes from the configuration file', () => {
  expect(readConfig().root).toBe(projectRoot);
});

test('ancestor launch cwd cannot change module identities', () => {
  expect(readConfig(dirname(projectRoot)).root).toBe(projectRoot);
});

test('Python proxy keeps MCP Apps and streaming Agent routes Next-owned', () => {
  expect(readConfig(projectRoot, { INK_BACKEND_INTERNAL_URL: 'http://backend.example.test:8765///' }).rewrites).toEqual({
    beforeFiles: [],
    afterFiles: [
      { source: '/api/:path((?!mcp-apps(?:/|$)|claude-agent(?:/|$)).*)', destination: 'http://backend.example.test:8765/api/:path' },
      { source: '/auth/:path*', destination: 'http://backend.example.test:8765/auth/:path*' },
      { source: '/oauth/google/:path*', destination: 'http://backend.example.test:8765/oauth/google/:path*' },
      { source: '/oauth/device/code', destination: 'http://backend.example.test:8765/oauth/device/code' },
      { source: '/oauth/token', destination: 'http://backend.example.test:8765/oauth/token' },
    ],
    fallback: [],
  });
});

test('missing backend URL retains no generic rewrite or standalone output', () => {
  const config = readConfig();
  expect(config.rewrites).toEqual([]);
  expect(config.output).toBeUndefined();
});

test('standalone, runtime configuration cache headers and shell flags stay intact', () => {
  const config = readConfig(projectRoot, { INK_NEXT_OUTPUT: 'standalone' });
  expect(config.output).toBe('standalone');
  expect(config.reactStrictMode).toBe(true);
  expect(config.poweredByHeader).toBe(false);
  expect(config.headers).toEqual([{
    source: '/runtime-config.js',
    headers: [
      { key: 'Cache-Control', value: 'no-store, no-cache, must-revalidate' },
      { key: 'Pragma', value: 'no-cache' },
      { key: 'Expires', value: '0' },
    ],
  }]);
});
