// [Sync] 2026-10-12: builtin compact survives catalog failure while existing keyboard selection stays intact.
// [Sync] 2026-11-08: cover system Markdown copy/paste, selection undo, plain/code/HTML and unsupported-node source preservation.
// [Input] Real Chrome input against production AIInputDock and UserMessagePart with mocked Skill catalog and system-config APIs.
// [Output] Regression coverage for slash/keyboard behavior and Markdown clipboard round trips, selection undo and literal/rich paste.
// [Pos] AIInputDock slash menu regression contract in frontend/app/_dream/components/chat/__tests__.
// [Sync] 2026-09-18: cover Enter send, Shift+Enter newline, IME composition, disabled/loading states, and mobile send visibility.
// [Sync] 2026-09-26: verify the real composer accepts input beside Stop and restores a rejected queued draft in local Chrome.
// [Sync] 2026-09-27: assert the single trailing action switches between Stop and Send with draft state and stays within narrow columns.

import { expect, test, type Page } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chrome' });

const HARNESS_PATH = '/ai-input-dock-slash-menu';
const COPY_MARKDOWN = [
  '# 复用消息',
  '',
  '**重点**与*补充*，保留 `project_slug`。',
  '',
  '- 第一项',
  '- 第二项',
  '',
  '> 引用内容',
  '',
  '```swift',
  'let path = "stories/<project_slug>/project.yaml"',
  '```',
].join('\n');

// Technical browser scope: only the composer draft and captured onSendMessage payload change.
// Project, Episode, canonical Artifact, Run-private .dream publication, after-turn Hook,
// PostgreSQL/API projections and Agent execution are out of scope; no business service is started.

async function reserveEphemeralPort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createNetServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const address = probe.address();
      if (address === null || typeof address === 'string') {
        probe.close();
        reject(new Error('Could not reserve an ephemeral TCP port.'));
        return;
      }
      const { port } = address;
      probe.close((error?: Error) => {
        if (error) reject(error);
        else resolve(port);
      });
    });
  });
}

function harnessModule(sentLogKey: string): string {
  return `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import i18n from '/app/_dream/i18n.ts';
    import AIInputDock from '/app/_dream/components/chat/AIInputDock.tsx';
    import UserMessagePart from '/app/_dream/components/chat/UserMessagePart.tsx';
    import '/app/_dream/styles/tokens.css';
    import '/app/_dream/styles/markdown.css';
    import '/app/_dream/index.css';

    window.${sentLogKey} = [];
    void i18n.changeLanguage('en');

    function Harness() {
      const [sentCount, setSentCount] = useState(0);
      const [disabled, setDisabled] = useState(false);
      const [loading, setLoading] = useState(false);
      const [activeTurn, setActiveTurn] = useState(false);
      const [rejectSend, setRejectSend] = useState(false);
      return React.createElement(
        'main',
        { style: { width: '100%', maxWidth: '52rem', margin: '0 auto' } },
        React.createElement(AIInputDock, {
          disabled,
          loading,
          onStop: activeTurn ? () => {} : undefined,
          mode: 'full',
          onSendMessage: (message) => {
            if (rejectSend) return Promise.reject(new Error('queue rejected'));
            window.${sentLogKey}.push(message);
            setSentCount((current) => current + 1);
          },
          placeholder: 'Ask Ink & Memory…',
        }),
        React.createElement('output', { 'data-testid': 'sent-count' }, String(sentCount)),
        React.createElement('section', { 'data-testid': 'copy-source' },
          React.createElement(UserMessagePart, { text: window.${sentLogKey}.at(-1) ?? ${JSON.stringify(COPY_MARKDOWN)} })),
        React.createElement('button', { 'data-testid': 'toggle-disabled', onClick: () => setDisabled((value) => !value) }, 'Toggle disabled'),
        React.createElement('button', { 'data-testid': 'toggle-loading', onClick: () => setLoading((value) => !value) }, 'Toggle loading'),
        React.createElement('button', { 'data-testid': 'toggle-active-turn', onClick: () => setActiveTurn((value) => !value) }, 'Toggle active turn'),
        React.createElement('button', { 'data-testid': 'toggle-reject-send', onClick: () => setRejectSend((value) => !value) }, 'Toggle rejection'),
      );
    }

    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
}

async function startHarness(page: Page, options: {
  readonly catalogStatus: number;
  readonly sentLogKey: string;
}): Promise<ViteDevServer> {
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'ai-input-dock-slash-menu-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== HARNESS_PATH) return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head>
              <body><div id="root"></div><script type="module" src="/ai-input-dock-slash-menu-harness.js"></script></body></html>
            `);
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          } catch (error) {
            next(error as Error);
          }
        });
      },
      resolveId(id) {
        return id === '/ai-input-dock-slash-menu-harness.js'
          ? '\0ai-input-dock-slash-menu-harness.js'
          : null;
      },
      load(id) {
        return id === '\0ai-input-dock-slash-menu-harness.js'
          ? harnessModule(options.sentLogKey)
          : null;
      },
    }],
  });

  await page.route('**/api/system-config', async (route) => {
    await route.fulfill({ json: { data: { im_full_access_enabled: false, workspace_enabled: true } } });
  });
  await page.route('**/api/storage', async (route) => {
    await route.fulfill({ json: { type: 's3', supportsDirectUpload: false, isConfigured: true } });
  });
  await page.route('**/api/claude-agent/skill-commands', async (route) => {
    if (options.catalogStatus !== 200) {
      await route.fulfill({
        status: options.catalogStatus,
        json: { detail: { error_code: 'COMMON_SKILL_CATALOG_UNAVAILABLE' } },
      });
      return;
    }
    await route.fulfill({
      json: {
        commands: [
          { command: '/plot-twist', name: 'plot-twist' },
          { command: '/scene-beat', name: 'scene-beat' },
        ],
      },
    });
  });

  await server.listen();
  const address = server.httpServer?.address();
  if (address === null || address === undefined || typeof address === 'string') {
    await server.close();
    throw new Error('AIInputDock slash menu harness did not bind a TCP port.');
  }
  await page.goto(`http://127.0.0.1:${address.port}${HARNESS_PATH}`);
  return server;
}

for (const width of [1440, 390]) {
  test(`copies Markdown from a user bubble and pastes editable formatting at ${width}px`, async ({ page, context }) => {
    const diagnostics: string[] = [];
    page.on('pageerror', (error) => diagnostics.push(error.message));
    page.on('console', (message) => { if (message.type() === 'error') diagnostics.push(message.text()); });
    page.on('requestfailed', (request) => diagnostics.push(`${request.failure()?.errorText} ${request.url()}`));
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.setViewportSize({ width, height: 900 });
    const sentLogKey = 'markdownCopySentMessages';
    const server = await startHarness(page, { catalogStatus: 200, sentLogKey });
    try {
      const editor = page.locator('#chat-input');
      const copy = page.getByTestId('copy-source').getByRole('button', { name: 'Copy', exact: true });
      await copy.click();
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(COPY_MARKDOWN);
      await editor.click();
      await editor.press('ControlOrMeta+V');
      await expect(editor.locator('h1')).toHaveText('复用消息');
      await expect(editor.locator('strong')).toHaveText('重点');
      await expect(editor.locator('em')).toHaveText('补充');
      await expect(editor.locator('ul > li')).toHaveCount(2);
      await expect(editor.locator('blockquote')).toHaveText('引用内容');
      await expect(editor.locator('p > code')).toHaveText('project_slug');
      await expect(editor.locator('pre > code')).toHaveAttribute('class', 'language-swift');
      await expect(editor.locator('pre > code')).toHaveText('let path = "stories/<project_slug>/project.yaml"');
      await page.getByRole('button', { name: 'Send message', exact: true }).click();
      await expect(page.getByTestId('sent-count')).toHaveText('1');
      await expect(editor).toBeEmpty();
      const first = await page.evaluate((key) => (window as unknown as Record<string, string[]>)[key][0], sentLogKey);
      expect(first).toContain('# 复用消息');
      expect(first).toContain('**重点**');
      expect(first).toContain('```swift\nlet path = "stories/<project_slug>/project.yaml"\n```');

      // Copying the serialized result again must retain the same Markdown semantics and source.
      await copy.click();
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(first);
      await editor.click();
      await editor.press('ControlOrMeta+V');
      await expect(editor.locator('h1')).toHaveText('复用消息');
      await page.getByRole('button', { name: 'Send message', exact: true }).click();
      await expect(page.getByTestId('sent-count')).toHaveText('2');
      expect(await page.evaluate((key) => (window as unknown as Record<string, string[]>)[key][1], sentLogKey)).toBe(first);
      expect(diagnostics).toEqual([]);
    } finally {
      await server.close();
    }
  });
}

test('pastes Markdown over the selected draft and undoes it in one step', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey: 'selectionPasteSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await editor.fill('before replace after');
    await editor.press('ControlOrMeta+A');
    await editor.press('ArrowRight');
    for (let index = 0; index < 6; index += 1) await editor.press('ArrowLeft');
    for (let index = 0; index < 7; index += 1) await editor.press('Shift+ArrowLeft');
    await expect.poll(() => page.evaluate(() => window.getSelection()?.toString())).toBe('replace');
    await page.evaluate(() => navigator.clipboard.writeText('**插入**'));
    await editor.press('ControlOrMeta+V');
    await expect(editor).toHaveText('before 插入 after');
    await expect(editor.locator(':scope > p')).toHaveCount(1);
    await expect(editor.locator('strong')).toHaveText('插入');
    await editor.press('ControlOrMeta+Z');
    await expect(editor).toHaveText('before replace after');
    await expect(editor.locator('strong')).toHaveCount(0);
  } finally {
    await server.close();
  }
});

test('keeps rich HTML paste and code-block text in their existing formats', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey: 'literalPasteSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await editor.click();
    await editor.evaluate((element) => {
      const clipboardData = new DataTransfer();
      clipboardData.setData('text/html', '<p><em>网页格式</em></p>');
      clipboardData.setData('text/plain', '**原文标记**');
      element.dispatchEvent(new ClipboardEvent('paste', { clipboardData, bubbles: true, cancelable: true }));
    });
    await expect(editor.locator('em')).toHaveText('网页格式');
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(editor).toBeEmpty();
    await page.evaluate(() => navigator.clipboard.writeText('```swift\nlet value = 1\n```'));
    await editor.click();
    await editor.press('ControlOrMeta+V');
    await expect(editor.locator('pre > code')).toHaveText('let value = 1');
    await editor.locator('pre > code').click();
    await editor.press('End');
    await page.evaluate(() => navigator.clipboard.writeText('\n**原文**\n# 保持代码'));
    await editor.press('ControlOrMeta+V');
    await expect(editor.locator('pre > code')).toHaveText('let value = 1\n**原文**\n# 保持代码');
    await expect(editor.locator('strong, h1')).toHaveCount(0);
  } finally {
    await server.close();
  }
});

test('preserves explicit plain-text paste and literal inline code', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey: 'plainPasteSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await page.evaluate(() => navigator.clipboard.writeText('# 保留原文'));
    await editor.click();
    // Headless macOS Chrome emits no paste event for Mod+Shift+V. Exercise the
    // production plain-text parser with Shift held and the system clipboard payload.
    await page.keyboard.down('Shift');
    try {
      await editor.evaluate(async (element) => {
        const clipboardData = new DataTransfer();
        clipboardData.setData('text/plain', await navigator.clipboard.readText());
        element.dispatchEvent(new ClipboardEvent('paste', { clipboardData, bubbles: true, cancelable: true }));
      });
    } finally {
      await page.keyboard.up('Shift');
    }
    await expect(editor).toHaveText('# 保留原文');
    await expect(editor.locator('h1')).toHaveCount(0);
    await page.getByRole('button', { name: 'Send message', exact: true }).click();
    await expect(editor).toBeEmpty();

    await page.evaluate(() => navigator.clipboard.writeText('`原有代码`'));
    await editor.click();
    await editor.press('ControlOrMeta+V');
    await expect(editor.locator('p > code')).toHaveText('原有代码');
    await editor.press('ControlOrMeta+A');
    await editor.press('ArrowRight');
    await editor.press('ArrowLeft');
    await page.evaluate(() => navigator.clipboard.writeText('**按原文保留**'));
    await editor.press('ControlOrMeta+V');
    await expect(editor.locator('p > code')).toContainText('**按原文保留**');
    await expect(editor.locator('strong')).toHaveCount(0);
  } finally {
    await server.close();
  }
});

test('retains Markdown for nodes absent from the composer schema', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const sentLogKey = 'unsupportedPasteSentMessages';
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey });
  try {
    const editor = page.locator('#chat-input');
    const fragments = [
      '| 名称 | 内容 |\n| --- | --- |\n| 项目 | 保留表格单元格 |',
      '![保留图片说明](https://example.invalid/preview.png)',
      '- [ ] 保留待办状态\n- [x] 保留完成状态',
    ];
    for (const [index, fragment] of fragments.entries()) {
      const source = `# 前文\n\n${fragment}\n\n后文`;
      await page.evaluate((text) => navigator.clipboard.writeText(text), source);
      await editor.click();
      await editor.press('ControlOrMeta+V');
      expect((await editor.innerText()).replace(/\s+/g, ' ').trim()).toBe(source.replace(/\s+/g, ' ').trim());
      await expect(editor.locator('h1, table, img')).toHaveCount(0);
      await page.getByRole('button', { name: 'Send message', exact: true }).click();
      await expect(page.getByTestId('sent-count')).toHaveText(String(index + 1));
      await expect(editor).toBeEmpty();
      const sent = await page.evaluate((key) => (window as unknown as Record<string, string[]>)[key].at(-1), sentLogKey);
      expect(sent).toContain('前文');
      expect(sent).toContain('后文');
    }
  } finally {
    await server.close();
  }
});

test('suggests installed Skills for a standalone slash draft and inserts the selection', async ({ page }) => {
  const sentLogKey = 'slashMenuSentMessages';
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey });
  try {
    const editor = page.locator('#chat-input');
    await expect(editor).toBeVisible();
    await editor.click();

    await editor.fill('/');
    const listbox = page.getByRole('listbox', { name: 'Chat commands' });
    await expect(listbox).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/plot-twist' })).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/scene-beat' })).toBeVisible();

    await editor.press('Enter');
    await expect(listbox).toBeHidden();
    await expect(editor).toContainText('/plot-twist');

    // The selected command is sent as ordinary Chat text through the production path.
    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const sentMessages = await page.evaluate(
      (key) => (window as unknown as Record<string, string[]>)[key] ?? [],
      sentLogKey,
    );
    expect(sentMessages).toEqual(['/plot-twist']);
  } finally {
    await server.close();
  }
});

test('accepts a second draft during an active turn and restores it when queue submission fails', async ({ page }, testInfo) => {
  const server = await startHarness(page, { catalogStatus: 503, sentLogKey: 'runningQueueSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await page.getByTestId('toggle-active-turn').click();
    await page.getByTestId('toggle-loading').click();
    const send = page.getByRole('button', { name: 'Send message' });
    const stop = page.getByRole('button', { name: 'Stop generating' });
    await expect(stop).toBeVisible();
    await expect(send).toHaveCount(0);
    await expect(page.locator('.ai-input-dock__trailing-actions button')).toHaveCount(1);
    await editor.fill('queued while running');
    await expect(send).toBeEnabled();
    await expect(stop).toHaveCount(0);
    for (const width of [2598, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const dock = await page.locator('.ai-input-dock').boundingBox();
      const sendBox = await send.boundingBox();
      expect(dock).not.toBeNull();
      expect(sendBox).not.toBeNull();
      expect(sendBox!.width).toBeGreaterThanOrEqual(44);
      expect(sendBox!.x + sendBox!.width).toBeLessThanOrEqual(dock!.x + dock!.width - 8);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.locator('.ai-input-dock').screenshot({ path: testInfo.outputPath(`active-turn-send-${width}.png`) });
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.locator('main').evaluate((node) => { node.style.maxWidth = '360px'; });
    const narrowDock = await page.locator('.ai-input-dock').boundingBox();
    const narrowSend = await send.boundingBox();
    expect(narrowDock).not.toBeNull();
    expect(narrowSend).not.toBeNull();
    expect(narrowSend!.x + narrowSend!.width).toBeLessThanOrEqual(narrowDock!.x + narrowDock!.width - 8);
    await send.click();
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    await expect(editor).toBeEmpty();
    await expect(stop).toBeVisible();
    await expect(send).toHaveCount(0);
    const narrowStop = await stop.boundingBox();
    expect(narrowStop).not.toBeNull();
    expect(narrowStop!.x + narrowStop!.width).toBeLessThanOrEqual(narrowDock!.x + narrowDock!.width - 8);
    await page.locator('.ai-input-dock').screenshot({ path: testInfo.outputPath('active-turn-stop-narrow.png') });

    await page.getByTestId('toggle-reject-send').click();
    await editor.fill('keep my queued draft');
    await expect(stop).toHaveCount(0);
    await send.click();
    await expect(editor).toHaveText('keep my queued draft');
    await expect(send).toBeVisible();
    await expect(page.locator('.ai-input-dock__trailing-actions button')).toHaveCount(1);
    await expect(page.getByTestId('sent-count')).toHaveText('1');
  } finally {
    await server.close();
  }
});

test('dismisses the slash menu with Escape and restores it when the draft changes', async ({ page }) => {
  const server = await startHarness(page, { catalogStatus: 200, sentLogKey: 'slashMenuDismissSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await expect(editor).toBeVisible();
    await editor.click();

    await editor.fill('/');
    const listbox = page.getByRole('listbox', { name: 'Chat commands' });
    await expect(listbox).toBeVisible();

    await editor.press('Escape');
    await expect(listbox).toBeHidden();

    await editor.fill('/sc');
    await expect(listbox).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/scene-beat' })).toBeVisible();
    await expect(listbox.getByRole('option', { name: '/plot-twist' })).toHaveCount(0);
  } finally {
    await server.close();
  }
});

test('keeps builtin compact usable when the Skill catalog fails', async ({ page }) => {
  const server = await startHarness(page, { catalogStatus: 503, sentLogKey: 'slashMenuFailureSentMessages' });
  try {
    const editor = page.locator('#chat-input');
    await expect(editor).toBeVisible();
    await editor.click();

    await editor.fill('/');
    await expect(page.getByRole('listbox').getByRole('option', { name: '/compact' })).toContainText('Usage unavailable');
    await expect(editor).toContainText('/');
    await expect(page.getByTestId('sent-count')).toHaveText('0');
  } finally {
    await server.close();
  }
});

test('uses Enter to send without breaking newline, IME, empty, loading, disabled, or mobile button rules', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const sentLogKey = 'keyboardPolicySentMessages';
  const server = await startHarness(page, { catalogStatus: 503, sentLogKey });
  try {
    const editor = page.locator('#chat-input');
    const sendButton = page.locator('.ai-input-dock__send-button');
    await expect(editor).toBeVisible();
    await expect(sendButton).toBeVisible();
    await expect(sendButton).toHaveAccessibleName('Send message');
    await expect(sendButton).toBeDisabled();
    await page.screenshot({
      path: fileURLToPath(new URL('../../../../../test-results/mobile-chat-390x844.png', import.meta.url)),
      fullPage: true,
    });

    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('0');

    await editor.fill('first line');
    await editor.press('Shift+Enter');
    await editor.pressSequentially('second line');
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    expect(await editor.innerText()).toContain('first line\nsecond line');

    await editor.dispatchEvent('compositionstart', { data: '拼音' });
    await editor.dispatchEvent('keydown', {
      key: 'Enter',
      code: 'Enter',
      isComposing: true,
      bubbles: true,
      cancelable: true,
    });
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    await editor.dispatchEvent('compositionend', { data: '拼音' });

    await page.getByTestId('toggle-loading').click();
    await expect(sendButton).toBeDisabled();
    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('0');
    await page.getByTestId('toggle-loading').click();

    await page.getByTestId('toggle-disabled').click();
    await expect(editor).toHaveAttribute('aria-disabled', 'true');
    await expect(sendButton).toBeDisabled();
    await page.getByTestId('toggle-disabled').click();

    await editor.press('Enter');
    await expect(page.getByTestId('sent-count')).toHaveText('1');
    const sentMessages = await page.evaluate(
      (key) => (window as unknown as Record<string, string[]>)[key] ?? [],
      sentLogKey,
    );
    expect(sentMessages).toEqual(['first line  \nsecond line']);

    const viewportMetrics = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    }));
    expect(viewportMetrics.documentWidth).toBeLessThanOrEqual(viewportMetrics.viewportWidth);
    const sendBox = await sendButton.boundingBox();
    expect(sendBox).not.toBeNull();
    expect(sendBox!.x + sendBox!.width).toBeLessThanOrEqual(390);
    expect(sendBox!.width).toBeGreaterThanOrEqual(44);
    expect(sendBox!.height).toBeGreaterThanOrEqual(44);

    await page.setViewportSize({ width: 430, height: 932 });
    await expect(sendButton).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(430);
    await page.screenshot({
      path: fileURLToPath(new URL('../../../../../test-results/mobile-chat-430x932.png', import.meta.url)),
      fullPage: true,
    });

    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(sendButton).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440);
    await page.screenshot({
      path: fileURLToPath(new URL('../../../../../test-results/mobile-chat-desktop-1440x900.png', import.meta.url)),
      fullPage: true,
    });
  } finally {
    await server.close();
  }
});
