// [Input] Owned disposable PostgreSQL, real Dream/Admin services, local Provider,
//         and a fresh browser session without saved user preferences.
// [Output] Full registration journey proving default Free subscription, live
//          Admin default-model selection, and the first settled Agent turn.
// [Pos] Opt-in isolated full-business Playwright acceptance in frontend/e2e
// [Sync] 2026-08-14: cover registration -> subscription -> Settings -> first
//                    turn with a default model that had no prior entitlement.

// Impact brief (must remain above browser mutation):
// - Writes: canonical users, Admin billing projection, Free Subscription,
//   current-period Allowance, activation Event, forked built-in Decks, one Chat
//   Thread/turn, one Gateway Request, and its Token ledger entries.
// - Reads: Product subscription context/plans, Gateway model catalog, and
//   system_config. The default model stays Admin-owned and is not copied into a
//   user preference until the user explicitly changes it.
// - Unchanged: Story Workspace Project/Episode/Artifact/Run state. The test uses
//   only its runner-owned disposable database/processes and a local Provider.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_DREAM_REGISTRATION_QA === '1';
const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:4177';
const BACKEND_ROOT = resolve(process.cwd(), '../backend');
const PYTHON = resolve(BACKEND_ROOT, '.venv/bin/python');
const TEST_EMAIL = process.env.INK_E2E_REGISTRATION_EMAIL ?? '';
const DEFAULT_ALIAS = process.env.INK_E2E_REGISTRATION_ALIAS ?? 'dream-balanced';
const DEFAULT_MODEL_NAME = process.env.INK_E2E_REGISTRATION_MODEL_NAME ?? 'Dream Balanced';

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(
  !ENABLED || !TEST_EMAIL,
  'Run through scripts/run-dream-business-e2e.mjs with an owned disposable database.',
);

function collectDiagnostics(page: Page): string[] {
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (
      message.type() === 'error'
      && !message.text().startsWith('Failed to load resource:')
    ) diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/')) {
      diagnostics.push(`http ${response.status()}: ${response.url()}`);
    }
  });
  return diagnostics;
}

function persistedReceipt(): {
  userId: number;
  planCode: string;
  subscriptionStatus: string;
  defaultModelAlias: string;
  grantedTokens: number;
  activationEvents: number;
  savedModel: string | null;
  gatewayRequests: number;
  requestedModel: string;
  gatewayOutcome: string;
  gatewayStatus: string;
  reserveTokens: number;
  terminalTokens: number;
  reservedTokens: number;
} {
  const source = [
    'import json, os, psycopg, sys',
    'with psycopg.connect(os.environ["DATABASE_URL"]) as c:',
    ' user=c.execute("SELECT id FROM users WHERE email=%s",(sys.argv[1],)).fetchone()',
    ' assert user is not None, "registered user missing"',
    ' row=c.execute("""SELECT plan.code,s.status,m.code,a.granted_tokens,a.reserved_tokens,COUNT(DISTINCT e.id),p.system_config_json FROM platform_users pu JOIN subscriptions s ON s.platform_user_id=pu.id JOIN subscription_plan_versions v ON v.id=s.plan_version_id JOIN subscription_plans plan ON plan.id=v.plan_id JOIN subscription_plan_entitlements ent ON ent.plan_version_id=v.id AND ent.enabled=TRUE AND ent.is_default=TRUE JOIN ai_models m ON m.id=ent.model_id AND m.enabled=TRUE JOIN subscription_usage_allowances a ON a.subscription_id=s.id AND a.period_number=s.current_period_number JOIN subscription_events e ON e.subscription_id=s.id AND e.event_type=\'activated\' LEFT JOIN user_preferences p ON p.user_id=%s WHERE pu.source=\'ink-dream\' AND pu.external_user_id=%s AND s.status=\'active\' GROUP BY plan.code,s.status,m.code,a.granted_tokens,a.reserved_tokens,p.system_config_json""",(user[0],str(user[0]))).fetchone()',
    ' assert row is not None, "default Free postcondition missing"',
    ' config=json.loads(row[6]) if isinstance(row[6],str) else (row[6] or {})',
    ' requests=c.execute("""SELECT r.id,r.requested_model,r.outcome,r.status FROM gateway_requests r JOIN platform_users pu ON pu.id=r.platform_user_id WHERE pu.source=\'ink-dream\' AND pu.external_user_id=%s ORDER BY r.created_at""",(str(user[0]),)).fetchall()',
    ' assert len(requests)==1, f"expected one first-turn Gateway Request, got {len(requests)}"',
    ' ledger=c.execute("SELECT entry_type,amount_tokens FROM subscription_token_ledger_entries WHERE gateway_request_id=%s",(requests[0][0],)).fetchall()',
    ' reserve=sum(int(item[1]) for item in ledger if item[0]=="reserve")',
    ' terminal=sum(int(item[1]) for item in ledger if item[0] in ("capture","release"))',
    ' print(json.dumps({"userId":int(user[0]),"planCode":row[0],"subscriptionStatus":row[1],"defaultModelAlias":row[2],"grantedTokens":int(row[3]),"reservedTokens":int(row[4]),"activationEvents":int(row[5]),"savedModel":config.get("model"),"gatewayRequests":len(requests),"requestedModel":requests[0][1],"gatewayOutcome":requests[0][2],"gatewayStatus":requests[0][3],"reserveTokens":reserve,"terminalTokens":terminal},separators=(",",":")))',
  ].join('\n');
  return JSON.parse(execFileSync(PYTHON, ['-c', source, TEST_EMAIL], {
    cwd: BACKEND_ROOT,
    encoding: 'utf-8',
  })) as ReturnType<typeof persistedReceipt>;
}

test('new user receives Free, sees the live default model, and completes the first Agent turn', async ({ page }) => {
  test.setTimeout(120_000);
  const diagnostics = collectDiagnostics(page);
  const systemConfigWrites: unknown[] = [];
  page.on('request', (request) => {
    if (request.method() === 'PUT' && request.url().endsWith('/api/system-config')) {
      systemConfigWrites.push(request.postDataJSON());
    }
  });
  await page.addInitScript(() => {
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${WEB_BASE}/story-workspace/subscription`);
  await page.getByRole('button', { name: 'Register', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible();
  await page.locator('input[type="email"]').fill(TEST_EMAIL);
  await page.locator('input[type="password"]').fill('Dream-registration-E2E-2026!');
  await page.locator('input[type="text"]').fill('Fresh Free User');
  const registrationResponse = page.waitForResponse((response) => (
    response.url().endsWith('/api/register')
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: 'Register', exact: true }).click();
  expect((await registrationResponse).status()).toBe(200);

  await expect(page.getByRole('heading', { level: 1, name: 'Free', exact: true })).toBeVisible();
  await expect(page.getByText('当前套餐', { exact: true }).first()).toBeVisible();
  await page.getByRole('tab', { name: '我的额度' }).click();
  await expect(page.getByText(/100,000\s+Token/)).toBeVisible();

  const token = await page.evaluate(() => localStorage.getItem('auth_token'));
  expect(token).toBeTruthy();
  const contextResponse = await page.request.get(
    `${WEB_BASE}/api/story-workspace/subscription/context`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(contextResponse.status()).toBe(200);
  expect(await contextResponse.json()).toMatchObject({
    data: {
      subscription: { status: 'active' },
      planVersion: { planCode: 'free', planName: 'Free' },
      allowance: { granted: 100_000 },
    },
  });

  await page.goto(`${WEB_BASE}/story-workspace/settings/model`);
  const defaultModel = page.getByRole('radio', { name: DEFAULT_MODEL_NAME });
  await expect(defaultModel).toBeChecked();
  await expect(page.getByText('推荐', { exact: true })).toBeVisible();
  expect(systemConfigWrites).toEqual([]);

  await page.goto(`${WEB_BASE}/story-workspace/chat`);
  const prompt = '请用一句话确认新账户的第一次默认模型调用。';
  await page.getByRole('textbox', { name: /聊天输入|Chat input/i }).fill(prompt);
  await page.getByRole('button', { name: /发送消息|Send message/i }).click();
  await expect(page.getByText('当前唯一授权步骤已完成，等待服务端重新读取权威状态。')).toBeVisible({ timeout: 90_000 });

  const receipt = persistedReceipt();
  expect(receipt).toMatchObject({
    planCode: 'free',
    subscriptionStatus: 'active',
    defaultModelAlias: DEFAULT_ALIAS,
    grantedTokens: 100_000,
    activationEvents: 1,
    savedModel: null,
    gatewayRequests: 1,
    requestedModel: DEFAULT_ALIAS,
    gatewayOutcome: 'succeeded',
    gatewayStatus: 'settled',
    reservedTokens: 0,
  });
  expect(receipt.reserveTokens).toBeGreaterThan(0);
  expect(receipt.terminalTokens).toBe(receipt.reserveTokens);
  expect(systemConfigWrites).toEqual([]);
  expect(diagnostics).toEqual([]);
});
