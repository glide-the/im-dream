// [Input] Real Chromium interactions with the Tiptap Markdown composer and user-message renderer.
// [Output] Browser regression coverage for toolbar-free Markdown serialization, line breaks, and placeholder paths.
// [Pos] markdown-input-editor browser test node in frontend/src/components/chat/__tests__
import { expect, test } from '@playwright/test';
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

test('converts user-authored rich text to Markdown and renders the submitted bubble faithfully', async ({ page }) => {
  const harnessModule = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import MarkdownInputEditor from '/src/components/chat/MarkdownInputEditor.tsx';
    import UserMessagePart from '/src/components/chat/UserMessagePart.tsx';
    import '/src/styles/tokens.css';
    import '/src/styles/markdown.css';

    function Harness() {
      const [markdown, setMarkdown] = useState('');
      const [submitted, setSubmitted] = useState('');
      return React.createElement(
        'main',
        { style: { width: '680px', margin: '32px auto' } },
        React.createElement(MarkdownInputEditor, {
          id: 'chat-input',
          value: markdown,
          placeholder: 'Ask Ink & Memory…',
          ariaLabel: 'Chat input',
          onChange: setMarkdown,
          onKeyDown: (event) => {
            if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return;
            event.preventDefault();
            setSubmitted(markdown);
            setMarkdown('');
          },
        }),
        React.createElement('output', { id: 'markdown-source' }, markdown),
        React.createElement('output', { id: 'submitted-source' }, submitted),
        submitted
          ? React.createElement('section', { 'data-testid': 'submitted-user-message' },
              React.createElement(UserMessagePart, { text: submitted }))
          : null,
      );
    }

    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'markdown-input-editor-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/markdown-input-editor') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><head><link rel="icon" href="data:,"></head><body><div id="root"></div>
              <script type="module" src="/markdown-input-editor-harness.js"></script></body></html>
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
        return id === '/markdown-input-editor-harness.js'
          ? '\0markdown-input-editor-harness.js'
          : null;
      },
      load(id) {
        return id === '\0markdown-input-editor-harness.js' ? harnessModule : null;
      },
    }],
  });
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });

  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (address === null || address === undefined || typeof address === 'string') {
      throw new Error('Markdown editor harness did not bind a TCP port.');
    }
    await page.goto(`http://127.0.0.1:${address.port}/markdown-input-editor`);

    const editor = page.getByRole('textbox', { name: 'Chat input' });
    await expect(editor).toBeVisible();
    await expect(editor).toHaveAttribute('aria-multiline', 'true');
    await expect(page.locator('textarea')).toHaveCount(0);
    await expect(page.getByRole('toolbar')).toHaveCount(0);

    await editor.fill('请恢复第一集关联。');
    await editor.press('Shift+Enter');
    await editor.pressSequentially('先完成 drama-init 的项目初始化语义。');
    await editor.press('Shift+Enter');
    await editor.pressSequentially('先创建 stories/<project_slug>/project.yaml。');

    await expect(page.locator('#markdown-source')).toContainText('stories/&lt;project\\_slug&gt;/project.yaml');
    await editor.press('Enter');

    const submittedSource = page.locator('#submitted-source');
    await expect(submittedSource).toContainText('drama-init');
    await expect(submittedSource).toContainText('stories/&lt;project\\_slug&gt;/project.yaml');
    await expect(editor).toBeEmpty();

    const submittedMessage = page.getByTestId('submitted-user-message');
    await expect(submittedMessage).toContainText('请恢复第一集关联。');
    await expect(submittedMessage).toContainText('stories/<project_slug>/project.yaml');
    expect(await submittedMessage.innerText()).toContain(
      '请恢复第一集关联。\n先完成 drama-init 的项目初始化语义。\n先创建 stories/<project_slug>/project.yaml。',
    );
    await expect(submittedMessage.locator('project_slug')).toHaveCount(0);

    expect(diagnostics).toEqual([]);
  } finally {
    await server.close();
  }
});
