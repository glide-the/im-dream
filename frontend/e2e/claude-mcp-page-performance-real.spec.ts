// [Input] Named existing actor, normal Dream/PostgreSQL/frontend services, and explicit sample/budget policy.
// [Output] Read-only visible MCP Resources fresh-entry/reload/re-entry latency distributions plus zero-discovery/zero-mutation evidence.
// [Pos] Opt-in real-account MCP list performance acceptance; it never opens inventory or changes Server configuration.
// [Sync] 2026-08-25: add database-list-only P50/P95 acceptance with independent first-screen budget.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_MCP_PAGE_PERF_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_MCP_WEB_BASE ?? 'http://127.0.0.1:5173';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_MCP_ACTOR_EMAIL ?? '';
const SAMPLE_COUNT = Number(process.env.INK_REAL_CLAUDE_MCP_PAGE_PERF_SAMPLES ?? '20');
const LIST_P95_BUDGET_MS = Number(process.env.INK_REAL_CLAUDE_MCP_LIST_P95_BUDGET_MS ?? '2000');
const BACKEND_DIR = resolve(process.cwd(), '../backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');
const RESOURCES_URL = `${WEB_BASE}/story-workspace/settings/work?tab=resources`;

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.skip(!ENABLED, 'Set INK_REAL_CLAUDE_MCP_PAGE_PERF_QA=1 for read-only real-page sampling.');

function requireInputs(): void {
  if (!ACTOR_EMAIL) throw new Error('INK_REAL_CLAUDE_MCP_ACTOR_EMAIL is required.');
  if (!Number.isInteger(SAMPLE_COUNT) || SAMPLE_COUNT < 5 || SAMPLE_COUNT > 50) {
    throw new Error('INK_REAL_CLAUDE_MCP_PAGE_PERF_SAMPLES must be an integer from 5 through 50.');
  }
  if (!Number.isFinite(LIST_P95_BUDGET_MS) || LIST_P95_BUDGET_MS <= 0) {
    throw new Error('INK_REAL_CLAUDE_MCP_LIST_P95_BUDGET_MS must be positive.');
  }
}

function createActorToken(email: string): string {
  const source = [
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import os',
    "from persistence.config import load_database_url_from_env_file",
    "load_database_url_from_env_file(override=True) if os.environ.get('INK_LOAD_DATABASE_URL_FROM_ENV_FILE') == '1' else None",
    'import auth,database,sys',
    'db=database.get_db()',
    "user=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'],user['email']))",
  ].join(';');
  return execFileSync(BACKEND_PYTHON, ['-c', source, email], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

function percentile(values: number[], quantile: number): number {
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.max(0, Math.ceil(sorted.length * quantile) - 1)];
}

function distribution(values: number[]) {
  return {
    n: values.length,
    min_ms: Number(Math.min(...values).toFixed(2)),
    p50_ms: Number(percentile(values, 0.5).toFixed(2)),
    p95_ms: Number(percentile(values, 0.95).toFixed(2)),
    max_ms: Number(Math.max(...values).toFixed(2)),
  };
}

async function waitForDatabaseList(page: Page, expectedServerNames: string[]): Promise<void> {
  await expect(page.getByRole('heading', { name: 'Claude MCP 资源' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: '读取 Claude MCP 状态…' })).toHaveCount(0);
  await expect(page.getByText('安全门禁已关闭此能力')).toHaveCount(0);
  for (const name of expectedServerNames) {
    await expect(page.getByRole('article', { name: `MCP 服务 ${name}` })).toBeVisible();
  }
  await expect(page.getByRole('article', { name: /^MCP 服务 / })).toHaveCount(expectedServerNames.length);
}

async function measureNavigation(
  page: Page,
  navigate: () => Promise<unknown>,
  expectedServerNames: string[],
): Promise<number> {
  const started = performance.now();
  await navigate();
  await waitForDatabaseList(page, expectedServerNames);
  return performance.now() - started;
}

test('real MCP Resources list stays on the database-only first-screen budget', async ({ page }) => {
  test.setTimeout(180_000);
  requireInputs();
  const token = createActorToken(ACTOR_EMAIL);
  const headers = { authorization: `Bearer ${token}` };
  const listResponse = await page.request.get(`${WEB_BASE}/api/claude-mcp/servers`, { headers });
  expect(listResponse.status(), await listResponse.text()).toBe(200);
  const listPayload = await listResponse.json() as { servers: Array<{ name: string }> };
  const expectedServerNames = listPayload.servers.map((server) => server.name).sort();

  const diagnostics: string[] = [];
  const mcpMutations: string[] = [];
  const discoveryRequests: string[] = [];
  const context = page.context();
  const attachPageDiagnostics = (target: Page) => {
    target.on('pageerror', (error) => diagnostics.push(`pageerror:${error.message}`));
  };
  attachPageDiagnostics(page);
  context.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http:${response.status()}:${new URL(response.url()).pathname}`);
    }
  });
  context.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path.includes('/discoveries')) discoveryRequests.push(path);
    if (path.startsWith('/api/claude-mcp/') && !['GET', 'HEAD'].includes(request.method())) {
      mcpMutations.push(`${request.method()}:${path}`);
    }
  });
  await context.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  const freshEntry: number[] = [];
  const reload: number[] = [];
  const reentry: number[] = [];
  await page.goto(RESOURCES_URL, { waitUntil: 'domcontentloaded' });
  await waitForDatabaseList(page, expectedServerNames);
  for (let index = 0; index < SAMPLE_COUNT; index += 1) {
    const freshPage = await context.newPage();
    attachPageDiagnostics(freshPage);
    freshEntry.push(await measureNavigation(
      freshPage,
      () => freshPage.goto(RESOURCES_URL, { waitUntil: 'domcontentloaded' }),
      expectedServerNames,
    ));
    await freshPage.close();
    reload.push(await measureNavigation(
      page,
      () => page.reload({ waitUntil: 'domcontentloaded' }),
      expectedServerNames,
    ));
    await page.goto(`${WEB_BASE}/story-workspace/chat`, { waitUntil: 'domcontentloaded' });
    reentry.push(await measureNavigation(
      page,
      () => page.goto(RESOURCES_URL, { waitUntil: 'domcontentloaded' }),
      expectedServerNames,
    ));
  }

  const receipt = {
    server_count: expectedServerNames.length,
    fresh_entry: distribution(freshEntry),
    reload: distribution(reload),
    reentry: distribution(reentry),
    list_p95_budget_ms: LIST_P95_BUDGET_MS,
    discovery_requests: discoveryRequests.length,
    mcp_mutations: mcpMutations.length,
  };
  console.log(`MCP_PAGE_PERFORMANCE ${JSON.stringify(receipt)}`);
  expect(receipt.fresh_entry.p95_ms).toBeLessThan(LIST_P95_BUDGET_MS);
  expect(receipt.reload.p95_ms).toBeLessThan(LIST_P95_BUDGET_MS);
  expect(receipt.reentry.p95_ms).toBeLessThan(LIST_P95_BUDGET_MS);
  expect(discoveryRequests).toEqual([]);
  expect(mcpMutations).toEqual([]);
  expect(diagnostics).toEqual([]);
});
