// [Input] Real Chromium input against the production MarkdownInputEditor module.
// [Output] Regression coverage for standalone slash serialization and Tiptap SSR configuration.
// [Pos] Markdown editor slash regression contract in frontend/app/_dream/components/chat/__tests__.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { readFileSync } from 'node:fs';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chromium' });

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

test('serializes a standalone slash as a slash draft after real Tiptap input', async ({ page }) => {
  const harnessModule = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import MarkdownInputEditor from '/app/_dream/components/chat/MarkdownInputEditor.tsx';

    function Harness() {
      const [markdown, setMarkdown] = useState('');
      return React.createElement(
        'main',
        React.createElement(MarkdownInputEditor, {
          id: 'chat-input',
          value: markdown,
          placeholder: 'Ask Ink & Memory…',
          ariaLabel: 'Chat input',
          onChange: setMarkdown,
        }),
        React.createElement('output', { 'data-testid': 'markdown-value' }, markdown),
      );
    }

    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'markdown-input-editor-slash-regression-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/markdown-input-editor-slash') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><body><div id="root"></div>
              <script type="module" src="/markdown-input-editor-slash-harness.js"></script></body></html>
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
        return id === '/markdown-input-editor-slash-harness.js'
          ? '\\0markdown-input-editor-slash-harness.js'
          : null;
      },
      load(id) {
        return id === '\\0markdown-input-editor-slash-harness.js' ? harnessModule : null;
      },
    }],
  });

  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (address === null || address === undefined || typeof address === 'string') {
      throw new Error('Markdown editor slash harness did not bind a TCP port.');
    }
    await page.goto(`http://127.0.0.1:${address.port}/markdown-input-editor-slash`);
    const editor = page.getByRole('textbox', { name: 'Chat input' });
    await expect(editor).toBeVisible();
    await editor.fill('/');
    await expect(page.getByTestId('markdown-value')).toHaveText(/^\/[^\s]*$/);
  } finally {
    await server.close();
  }
});

test('configures Tiptap for client-only rendering under Next SSR', () => {
  const source = readFileSync(fileURLToPath(new URL('../MarkdownInputEditor.tsx', import.meta.url)), 'utf8');
  expect(source).toMatch(/useEditor\(\{[\s\S]*?immediatelyRender\s*:\s*false/);
});
