// [Input] Original AuthProvider/AuthEntry and isolated public session/options DTOs.
// [Output] Wide/narrow recovery, current-session restoration and original top-level form POST receipts.
// [Pos] Provider-free browser regression; no real credentials, accounts, database or model requests.
// [Sync] 2026-10-25: retry reloads the original page; credential errors retain the normal form interaction.
import { expect, test, type Page } from '@playwright/test';
import { createServer as createNetServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

test.use({ channel: 'chrome' });
let server: Awaited<ReturnType<typeof createServer>>;
let base: string;
const admin = 'https://admin.example.test';
const actions = { password_action: `${admin}/auth/dream/password`, google_action: `${admin}/auth/dream/google` };
const session = { user: { id: '1', email: 'recovery@example.test', display_name: 'Recovery QA', avatar_url: null,
  role: 'user', created_at: null }, csrf_token: 'r'.repeat(43) };
// Scope: AuthProvider public state and AuthEntry navigation change; Project,
// Episode, canonical/private artifacts, Hooks, database and models are out of scope.
const diagnostics = new WeakMap<Page, string[]>();
const entry = `
  import React from 'react';
  import { createRoot } from 'react-dom/client';
  import { AuthProvider, useAuth } from '/app/_dream/contexts/AuthContext.tsx';
  import AuthEntry from '/app/_dream/components/Auth/AuthEntry.tsx';
  import '/app/_dream/styles/tokens.css';
  function Surface() {
    const auth = useAuth();
    if (auth.isLoading) return React.createElement('p', null, 'Loading session');
    if (auth.isAuthenticated) return React.createElement('h1', null, 'Session restored');
    return React.createElement(AuthEntry, {mode:'login', onSwitch:()=>{}});
  }
  createRoot(document.querySelector('#root')).render(React.createElement(AuthProvider, null, React.createElement(Surface)));
`;

test.beforeAll(async () => {
  const port = await new Promise<number>((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (!address || typeof address === 'string') { probe.close(); reject(new Error('Fixture address unavailable')); return; }
      probe.close(error => error ? reject(error) : resolve(address.port));
    });
  });
  server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false,
    logLevel: 'silent', server: {host:'127.0.0.1', port, strictPort:true}, plugins: [{
      name:'auth-entry-recovery-fixture', enforce:'pre',
      configureServer(vite) { vite.middlewares.use(async (request, response, next) => {
        if (request.url?.split('?')[0] !== '/auth-entry-recovery') return next();
        response.setHeader('Content-Type', 'text/html');
        response.end(await vite.transformIndexHtml('/auth-entry-recovery', `<html><head><link rel="icon" href="data:,"></head><body>
          <style>*{box-sizing:border-box}body{margin:0}#root{min-height:100vh;padding:24px;display:flex;align-items:center;justify-content:center}</style>
          <div id="root"></div><script type="module" src="/auth-entry-recovery.js"></script></body></html>`));
      }); },
      resolveId(id) { return id === '/auth-entry-recovery.js' ? '\0auth-entry-recovery.js' : null; },
      load(id) { return id === '\0auth-entry-recovery.js' ? entry : null; },
    }] });
  await server.listen();
  base = `http://127.0.0.1:${port}/auth-entry-recovery`;
});
test.afterAll(async () => { await server?.close(); });
test.beforeEach(async ({page}) => {
  const errors: string[] = [];
  diagnostics.set(page, errors);
  const publicRead = (value: string) => {
    try { return ['/auth/session', '/auth/options'].includes(new URL(value).pathname); }
    catch { return false; }
  };
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => {
    if (message.type() !== 'error') return;
    if (publicRead(message.location().url) && /status of (401|503)/.test(message.text())) return;
    errors.push(`console: ${message.text()}`);
  });
  page.on('requestfailed', request => {
    const failure = request.failure()?.errorText ?? '';
    if (publicRead(request.url()) && failure.includes('ERR_ABORTED')) return;
    errors.push(`requestfailed: ${failure}`);
  });
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.pathname.startsWith('/auth/') && !['/auth/session', '/auth/options', '/auth/dream/password'].includes(url.pathname)) errors.push(`unexpected auth response: ${url.pathname}`);
  });
  await page.route('**/*', route => {
    if (new URL(route.request().url()).origin === new URL(base).origin) return route.continue();
    errors.push('Unexpected external request');
    return route.abort();
  });
});
test.afterEach(async ({page}, info) => {
  const errors = diagnostics.get(page) ?? [];
  await info.attach('auth-recovery-diagnostics', {body:JSON.stringify(errors), contentType:'application/json'});
  if (info.status !== info.expectedStatus) await info.attach('auth-recovery-failure', {body:await page.screenshot(), contentType:'image/png'});
  expect(errors).toEqual([]);
});

for (const width of [1440, 390]) {
  test.describe(`${width}px original auth recovery`, () => {
    test.use({ viewport: {width, height:900} });
    test('options failure reloads original reads and restores the normal forms', async ({page}) => {
      let optionsReads = 0, sessionReads = 0, posts = 0;
      page.on('request', request => { if (request.method() === 'POST') posts++; });
      await page.route('**/auth/session', route => { sessionReads++; return route.fulfill({status:401, json:{}}); });
      await page.route('**/auth/options', route => route.fulfill(++optionsReads === 1
        ? {status:503, json:{detail:'BFF_ADMIN_UNAVAILABLE'}} : {json:actions}));
      await page.goto(base);
      await expect(page.getByRole('alert')).toContainText('Login is temporarily unavailable.');
      await expect(page.getByRole('button', {name:'Login', exact:true})).toBeDisabled();
      await expect(page.getByRole('button', {name:'Continue with Google', exact:true})).toBeDisabled();
      const retry = page.getByRole('button', {name:'Try again', exact:true});
      await expect(retry).toBeInViewport();
      await page.screenshot({path:`output/playwright/ios-auth-recovery-${width}.png`});
      await retry.focus();
      await retry.press('Enter');
      await expect(page.getByRole('button', {name:'Login', exact:true})).toBeEnabled();
      await expect(page.getByRole('button', {name:'Continue with Google', exact:true})).toBeEnabled();
      await expect(page.getByRole('alert')).toHaveCount(0);
      expect(optionsReads).toBe(2); expect(sessionReads).toBe(2); expect(posts).toBe(0);
      await expect(page.locator('form').filter({has:page.locator('input[name=password]')})).toHaveAttribute('action', actions.password_action);
      await expect(page.locator('form').filter({has:page.locator('input[name=password]')})).toHaveAttribute('method', 'post');
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    });

    test('session failure reloads and restores only the validated original session', async ({page}) => {
      let sessionReads = 0, posts = 0;
      page.on('request', request => { if (request.method() === 'POST') posts++; });
      await page.route('**/auth/session', route => route.fulfill(++sessionReads === 1
        ? {status:503, json:{detail:'BFF_ADMIN_UNAVAILABLE'}} : {json:session}));
      await page.route('**/auth/options', route => route.fulfill({json:actions}));
      await page.goto(base);
      await expect(page.getByRole('alert')).toContainText('Unable to check your session.');
      await page.getByRole('button', {name:'Try again', exact:true}).click();
      await expect(page.getByRole('heading', {name:'Session restored', exact:true})).toBeVisible();
      expect(sessionReads).toBe(2); expect(posts).toBe(0);
      await expect(page.locator('form')).toHaveCount(0);
    });

    test('credential feedback preserves original top-level password and Google forms', async ({page}) => {
      await page.route('**/auth/session', route => route.fulfill({status:401, json:{}}));
      await page.route('**/auth/options', route => route.fulfill({json:actions}));
      const submissions: URLSearchParams[] = [];
      await page.route(`${admin}/auth/dream/password`, route => {
        expect(route.request().isNavigationRequest()).toBe(true);
        expect(route.request().method()).toBe('POST');
        submissions.push(new URLSearchParams(route.request().postData() ?? ''));
        return route.fulfill({contentType:'text/html', body:'<html><head><link rel="icon" href="data:,"></head><body><h1>Original form submitted</h1></body></html>'});
      });
      await page.goto(`${base}?auth_error=credentials`);
      await expect(page.getByRole('alert')).toHaveText('Login failed. Check your email and password.');
      await expect(page.getByRole('button', {name:'Try again', exact:true})).toHaveCount(0);
      await expect(page.locator('form').filter({has:page.getByRole('button', {name:'Continue with Google', exact:true})})).toHaveAttribute('action', actions.google_action);
      await page.getByLabel('Email', {exact:true}).fill('recovery@example.test');
      await page.getByLabel('Password', {exact:true}).fill('fixture-password-only');
      await expect(page.getByLabel('Password', {exact:true})).toHaveAttribute('type', 'password');
      await page.getByRole('button', {name:'Login', exact:true}).click();
      await expect(page.getByRole('heading', {name:'Original form submitted', exact:true})).toBeVisible();
      expect(submissions).toHaveLength(1);
      expect(Object.fromEntries(submissions[0])).toEqual({mode:'login', return_to:'/auth-entry-recovery', email:'recovery@example.test', password:'fixture-password-only'});
    });
  });
}
