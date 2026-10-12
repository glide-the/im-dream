// [Input] Production ModelConfigSection and same-origin session with isolated catalog/preferences HTTP seams.
// [Output] Visible Chrome journeys for independent saves, refresh, native/Images badges and recovery.
// [Pos] Provider-free Settings verification; no normal account, database or model acceptance.
// [Sync] 2026-10-10: exercise independent Image selection without browser defaults or ambiguous capabilities.
import { expect, test, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

test.use({ channel: 'chrome' });
const csrf = 's'.repeat(43);
const off = { generation: false, edit: false, configured: false, entitled: true, callable: false };
const ready = { generation: true, edit: true, configured: true, entitled: true, callable: true };
const model = (alias: string, name: string, extra = {}) => ({
  modelAlias: alias, displayName: name, protocol: 'openai', capabilities: { chat: true, tools: true },
  contextWindow: null, maxOutputTokens: null, enabled: true, callable: true, availability: 'included',
  requiredPlanCode: null, upgradeHint: null, images: off, responsesImage: off, ...extra,
});

async function harness(page: Page, saved: Record<string, unknown> = {}) {
  const state = { saved: { ...saved }, updates: [] as Record<string, unknown>[], configFailure: false,
    catalogFailure: false, reject: false, malformedSave: false, disconnectSave: false, commitBeforeDisconnect: false,
    errors: [] as string[], catalog: {
      data: [model('chat-a', '普通对话'), model('chat-b', '内置图片对话', { responsesImage: ready }),
        model('image-a', 'Images 图片甲', { capabilities: { chat: false }, callable: false, images: ready }),
        model('image-b', 'Images 图片乙', { capabilities: { chat: false }, callable: false, images: ready }),
        model('image-locked', 'Images 未就绪', { capabilities: { chat: false }, callable: false, images: { ...ready, configured: false, callable: false } })],
      defaultModelAlias: 'chat-a',
    } };
  page.on('pageerror', error => state.errors.push(error.message));
  await page.route('**/auth/session', route => route.fulfill({ json: { user: { id: '1', email: 'image-settings@example.test', display_name: 'Fixture', avatar_url: null, role: 'user', created_at: null }, csrf_token: csrf } }));
  await page.route('**/api/gateway/models', route => route.fulfill({ status: state.catalogFailure ? 503 : 200, json: state.catalogFailure ? { error: 'Injected failure' } : state.catalog }));
  await page.route('**/api/system-config', async route => {
    const request = route.request();
    if (request.method() === 'GET') return route.fulfill({ status: state.configFailure ? 503 : 200, json: state.saved });
    expect(request.headers()['x-ink-csrf']).toBe(csrf);
    expect(request.headers().authorization).toBeUndefined();
    const patch = request.postDataJSON();
    state.updates.push(patch);
    if (state.disconnectSave) {
      if (state.commitBeforeDisconnect) Object.assign(state.saved, patch);
      return route.abort('failed');
    }
    if (state.reject) return route.fulfill({ status: 409, json: { error: 'Injected stale model' } });
    if (state.malformedSave) return route.fulfill({ json: { success: true } });
    Object.assign(state.saved, patch);
    return route.fulfill({ json: { success: true, data: state.saved } });
  });
  const source = `
    import React from 'react'; import { createRoot } from 'react-dom/client';
    import { loadBrowserSession } from '/app/_dream/lib/browserSession.ts';
    import ModelConfigSection from '/app/_dream/components/dashboard/ModelConfigSection.tsx';
    import '/app/_dream/styles/tokens.css'; import '/app/_dream/index.css';
    await loadBrowserSession();
    createRoot(document.getElementById('root')).render(React.createElement('main', {style:{maxWidth:760,margin:'0 auto',padding:12}}, React.createElement(ModelConfigSection)));
  `;
  const server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false,
    logLevel: 'silent', server: { host: '127.0.0.1', port: 0, strictPort: true }, plugins: [{
      name: 'image-settings-owned-fixture',
      configureServer(vite) { vite.middlewares.use(async (req, res, next) => {
        if (req.url !== '/image-settings') return next();
        res.setHeader('Content-Type', 'text/html');
        res.end(await vite.transformIndexHtml('/image-settings', '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/image-settings.js"></script></body></html>'));
      }); },
      resolveId: id => id === '/image-settings.js' ? '\0image-settings.js' : null,
      load: id => id === '\0image-settings.js' ? source : null,
    }] });
  await server.listen();
  const address = server.httpServer!.address();
  if (!address || typeof address === 'string') throw new Error('Owned Settings fixture port unavailable');
  await page.goto(`http://127.0.0.1:${address.port}/image-settings`);
  return { state, server };
}

const ai = (page: Page) => page.getByRole('group', { name: '选择 AI 模型', exact: true });
const image = (page: Page) => page.getByRole('group', { name: '选择 Image 模型', exact: true });

test('native badges, independent Image save and AI save persist across refresh', async ({ page }) => {
  const { state, server } = await harness(page);
  try {
    await expect(ai(page).getByRole('radio', { name: /普通对话/ })).toBeChecked();
    await expect(image(page).locator('input:checked')).toHaveCount(0);
    await expect(ai(page).getByText('图片生成', { exact: true })).toHaveCount(1);
    await expect(ai(page).getByText('图片编辑', { exact: true })).toHaveCount(1);
    await expect(ai(page).getByText('Images 图片甲')).toHaveCount(0);
    await expect(image(page).getByRole('radio', { name: /Images 未就绪/ })).toBeDisabled();
    await image(page).getByRole('radio', { name: /Images 图片甲/ }).check();
    await expect(page.getByText('Image 模型已保存，仅用于后续 image_gen 工具调用。')).toBeVisible();
    await expect(ai(page).getByRole('radio', { name: /普通对话/ })).toBeChecked();
    await ai(page).getByRole('radio', { name: /内置图片对话/ }).check();
    await expect(page.getByText('模型已保存，将用于新对话。')).toBeVisible();
    expect(state.updates).toEqual([{ image_model: 'image-a' }, { model: 'chat-b' }]);
    await page.reload();
    await expect(ai(page).getByRole('radio', { name: /内置图片对话/ })).toBeChecked();
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeChecked();
    expect(state.errors).toEqual([]);
  } finally { await server.close(); }
});

test('stale Image selection remains visible, reload and explicit recovery work on narrow screen', async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const { state, server } = await harness(page, { model: 'chat-a', image_model: 'retired-image' });
  try {
    await expect(page.getByRole('alert')).toContainText('retired-image');
    expect(state.updates).toEqual([]);
    await image(page).getByRole('radio', { name: /Images 图片乙/ }).check();
    await expect(page.getByText('Image 模型已保存，仅用于后续 image_gen 工具调用。')).toBeVisible();
    await page.reload();
    await expect(image(page).getByRole('radio', { name: /Images 图片乙/ })).toBeChecked();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath('image-model-settings-narrow.png'), fullPage: true });
    expect(state.saved.model).toBe('chat-a');
  } finally { await server.close(); }
});

test('failed or malformed saves retain the last selection and never claim success', async ({ page }) => {
  const { state, server } = await harness(page, { model: 'chat-a', image_model: 'image-a' });
  try {
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeChecked();
    state.malformedSave = true;
    await image(page).getByRole('radio', { name: /Images 图片乙/ }).check();
    await expect(page.getByText('Image 模型保存结果未确认，请重新加载设置核对。')).toBeVisible();
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeChecked();
    await expect(image(page).getByRole('radio', { name: /Images 图片乙/ })).toBeDisabled();
    state.malformedSave = false; state.disconnectSave = true;
    await page.getByRole('button', { name: '重新加载设置', exact: true }).click();
    await image(page).getByRole('radio', { name: /Images 图片乙/ }).check();
    await expect(page.getByText('网络连接失败，Image 模型保存结果未确认，请重新加载设置核对。')).toBeVisible();
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeChecked();
    state.disconnectSave = false;
    await page.getByRole('button', { name: '重新加载设置', exact: true }).click();
    await image(page).getByRole('radio', { name: /Images 图片乙/ }).check();
    await expect(page.getByText('Image 模型已保存，仅用于后续 image_gen 工具调用。')).toBeVisible();
  } finally { await server.close(); }
});

test('a lost save response is recovered by reading settings without repeating the write', async ({ page }) => {
  const { state, server } = await harness(page, { model: 'chat-a', image_model: 'image-a' });
  try {
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeChecked();
    state.disconnectSave = true; state.commitBeforeDisconnect = true;
    await image(page).getByRole('radio', { name: /Images 图片乙/ }).check();
    await expect(page.getByText('网络连接失败，Image 模型保存结果未确认，请重新加载设置核对。')).toBeVisible();
    expect(state.saved.image_model).toBe('image-b');
    state.disconnectSave = false;
    await page.getByRole('button', { name: '重新加载设置', exact: true }).click();
    await expect(image(page).getByRole('radio', { name: /Images 图片乙/ })).toBeChecked();
    expect(state.updates).toEqual([{ image_model: 'image-b' }]);
    expect(state.saved.model).toBe('chat-a');
  } finally { await server.close(); }
});

test('preferences read failure disables choices until a successful reload', async ({ page }) => {
  const { state, server } = await harness(page);
  try {
    state.configFailure = true;
    await page.reload();
    await expect(page.getByRole('alert')).toContainText('模型设置读取失败');
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeDisabled();
    expect(state.updates).toEqual([]);
    state.configFailure = false;
    await page.getByRole('button', { name: '重新加载设置', exact: true }).click();
    await expect(image(page).getByRole('radio', { name: /Images 图片甲/ })).toBeEnabled();
  } finally { await server.close(); }
});
