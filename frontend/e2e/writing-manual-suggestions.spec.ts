// [Input] Real Writing EditorEngine/controller/Cell components mounted with provider-free deterministic Thread and SSE dependencies.
// [Output] Browser evidence for explicit insertion, typewriter completion, latest-only same-Cell Refresh, Session Thread reuse, themes, and mobile layout.
// [Pos] Technical isolated Writing suggestion browser journey; it does not claim real-model or real-business acceptance.
// [Sync] 2026-09-01: add the manual persistent Writing suggestion visual and interaction matrix.
// [Sync] 2026-09-01: prove only the latest suggestion Cell exposes its regeneration action.

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { fileURLToPath } from 'node:url';
// @ts-expect-error Playwright's Node-side harness intentionally imports Node APIs outside the browser tsconfig.
import { createServer as createNetServer } from 'node:net';
import { createServer } from 'vite';

test.use({ channel: 'chromium' });

/*
Business impact brief used by this provider-free browser lane:

| Fact/surface | Baseline | Expected | Classification |
| --- | --- | --- | --- |
| Writing prose | one TextCell | editable continuation TextCells | changes |
| Suggestion data | absent | independent persistent suggestion Cells | changes |
| Session Thread | absent | one lazily created Thread reused by generate/Refresh | changes |
| Text Weight/Energy | prose-only | remains prose-only | must remain unchanged |
| ChatWidgetUI | existing inline widget | no suggestion-owned layout or behavior | must remain unchanged |
*/

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
      probe.close((error?: Error) => {
        if (error) reject(error);
        else resolve(address.port);
      });
    });
  });
}

test('manual Writing suggestions stream, refresh in place, reuse a Thread, and fit theme/viewport variants', async ({ page }) => {
  test.setTimeout(30_000);
  const harnessModule = `
    import React, { useEffect, useMemo, useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import i18n from '/src/i18n.ts';
    import { EditorEngine } from '/src/engine/EditorEngine.ts';
    import { WritingSuggestionController } from '/src/hooks/useWritingSuggestions.ts';
    import { WritingSuggestionCell, WritingSuggestionTrigger } from '/src/components/Editor/WritingSuggestionCell.tsx';
    import '/src/styles/tokens.css';

    const engine = new EditorEngine('writing-browser-session');
    const firstText = engine.getState().cells.find((cell) => cell.type === 'text');
    engine.updateTextCell(firstText.id, '雨落在旧车站的玻璃顶上。');
    window.writingHarness = { createCalls: 0, threadIds: [], snapshots: [], persistedThreads: [] };

    const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

    function Harness() {
      const [state, setState] = useState({ ...engine.getState() });
      const controller = useMemo(() => new WritingSuggestionController({
        getEngine: () => engine,
        createThread: async () => {
          window.writingHarness.createCalls += 1;
          return 'thread-writing-browser';
        },
        persistSession: async (editorState) => {
          window.writingHarness.persistedThreads.push(editorState.writingThreadId ?? null);
        },
        streamTurn: async (request) => {
          window.writingHarness.threadIds.push(request.threadId);
          const snapshot = request.message.match(/<writing_passage>\\n([\\s\\S]*?)\\n<\\/writing_passage>/)?.[1] ?? request.message;
          window.writingHarness.snapshots.push(snapshot);
          await wait(180);
          request.onDelta('试着让雨声');
          await wait(180);
          request.onDelta('触发一个具体的记忆。');
          request.onComplete('试着让雨声触发一个具体的记忆。');
        },
        buildPrompt: (textSnapshot) => ({
          systemPrompt: 'Writing product prompt',
          message: '<writing_passage>\\n' + textSnapshot + '\\n</writing_passage>',
        }),
      }), []);

      useEffect(() => {
        engine.subscribe((nextState) => setState({ ...nextState }));
        return () => controller.dispose();
      }, [controller]);

      const hasStreaming = state.cells.some((cell) => cell.type === 'writing-suggestion' && cell.status === 'streaming');
      const latestSuggestionId = state.cells.reduce(
        (latestId, cell) => cell.type === 'writing-suggestion' ? cell.id : latestId,
        null,
      );
      return React.createElement('main', { className: 'harness-shell' },
        React.createElement('h1', null, i18n.t('writingSuggestion.threadTitle')),
        state.cells.map((cell) => {
          if (cell.type === 'writing-suggestion') {
            return React.createElement(WritingSuggestionCell, {
              key: cell.id,
              cell,
              isLatestSuggestion: cell.id === latestSuggestionId,
              onRetry: () => controller.retry(cell.id),
            });
          }
          if (cell.type !== 'text') return null;
          const anchored = state.cells.some((candidate) => candidate.type === 'writing-suggestion' && candidate.anchor.textCellId === cell.id);
          return React.createElement('section', { key: cell.id, className: 'harness-text-cell' },
            React.createElement('textarea', {
              'aria-label': 'Writing text',
              value: cell.content,
              placeholder: 'Continue writing...',
              onChange: (event) => engine.updateTextCell(cell.id, event.currentTarget.value),
            }),
            cell.content.trim() && !anchored && !hasStreaming
              ? React.createElement(WritingSuggestionTrigger, { onGenerate: () => controller.start(cell.id) })
              : null,
          );
        }),
      );
    }

    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const harnessPort = await reserveEphemeralPort();
  const server = await createServer({
    root: fileURLToPath(new URL('../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: harnessPort, strictPort: true },
    plugins: [{
      name: 'writing-suggestion-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          if (request.url !== '/writing-suggestion-harness') return next();
          try {
            const html = await vite.transformIndexHtml(request.url, `
              <!doctype html><html><head><link rel="icon" href="data:,"><style>
                html, body, #root { min-height: 100%; margin: 0; }
                body { background: var(--color-bg-app); color: var(--color-text-body); }
                .harness-shell { box-sizing: border-box; width: min(100% - 2rem, 680px); margin: 0 auto; padding: 3rem 1rem 5rem; }
                .harness-shell h1 { color: var(--color-text-primary); font: 650 1rem/1.4 system-ui; }
                .harness-text-cell textarea { box-sizing: border-box; width: 100%; min-height: 5rem; border: 0; resize: none; background: transparent; color: var(--color-text-body); font: 1.1rem/1.8 Georgia, serif; }
              </style></head><body><div id="root"></div>
              <script type="module" src="/writing-suggestion-harness.js"></script></body></html>
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
        return id === '/writing-suggestion-harness.js'
          ? '\0writing-suggestion-harness.js'
          : null;
      },
      load(id) {
        return id === '\0writing-suggestion-harness.js' ? harnessModule : null;
      },
    }],
  });

  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });

  try {
    await server.listen();
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`http://127.0.0.1:${harnessPort}/writing-suggestion-harness`);

    const goDeeper = page.getByRole('button', { name: 'Go deeper' });
    await expect(goDeeper).toBeVisible();
    await expect(page.locator('[data-suggestion-cell-id]')).toHaveCount(0);
    await goDeeper.click();

    const firstSuggestion = page.locator('[data-suggestion-cell-id]').first();
    await expect(firstSuggestion).toHaveAttribute('aria-busy', 'true');
    await expect(page.getByRole('button', { name: 'Go deeper' })).toHaveCount(0);
    await page.screenshot({
      path: 'output/playwright/writing-suggestions/streaming-light-desktop.png',
      fullPage: true,
    });
    await expect(firstSuggestion).toContainText('试着让雨声触发一个具体的记忆。');
    await expect(firstSuggestion).toHaveAttribute('aria-busy', 'false');

    const firstCellId = await firstSuggestion.getAttribute('data-suggestion-cell-id');
    await firstSuggestion.getByRole('button', { name: 'Refresh' }).click();
    await expect(firstSuggestion).toHaveAttribute('aria-busy', 'true');
    await expect(firstSuggestion.locator('.writing-suggestion-cell__content--previous')).toBeVisible();
    await expect(firstSuggestion).toContainText('试着让雨声触发一个具体的记忆。');
    await expect(firstSuggestion).toHaveAttribute('aria-busy', 'false');
    await expect(firstSuggestion).toHaveAttribute('data-suggestion-cell-id', firstCellId ?? '');

    const textareas = page.getByRole('textbox', { name: 'Writing text' });
    await expect(textareas).toHaveCount(2);
    await textareas.nth(1).fill('售票员抬头，说出了多年无人提起的名字。');
    await page.getByRole('button', { name: 'Go deeper' }).click();
    const suggestionCells = page.locator('[data-suggestion-cell-id]');
    await expect(suggestionCells).toHaveCount(2);
    await expect(suggestionCells.nth(1)).toHaveAttribute('aria-busy', 'false');
    await expect(suggestionCells.first().getByRole('button', { name: 'Refresh' })).toHaveCount(0);
    await expect(suggestionCells.nth(1).getByRole('button', { name: 'Refresh' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh' })).toHaveCount(1);

    const transportFacts = await page.evaluate(() => (
      (window as unknown as { writingHarness: {
        createCalls: number;
        threadIds: string[];
        snapshots: string[];
        persistedThreads: Array<string | null>;
      } }).writingHarness
    ));
    expect(transportFacts.createCalls).toBe(1);
    expect(transportFacts.threadIds).toEqual([
      'thread-writing-browser',
      'thread-writing-browser',
      'thread-writing-browser',
    ]);
    expect(transportFacts.snapshots).toEqual([
      '雨落在旧车站的玻璃顶上。',
      '雨落在旧车站的玻璃顶上。',
      '售票员抬头，说出了多年无人提起的名字。',
    ]);
    expect(transportFacts.persistedThreads).toEqual([
      'thread-writing-browser',
      'thread-writing-browser',
      'thread-writing-browser',
    ]);

    await page.evaluate(async () => {
      const [{ default: i18n }, theme] = await Promise.all([
        import('/src/i18n.ts'),
        import('/src/utils/theme.ts'),
      ]);
      await i18n.changeLanguage('zh');
      theme.setThemeMode('dark');
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.getByRole('button', { name: '重新生成' })).toHaveCount(1);
    await expect(page.getByRole('button', { name: '重新生成' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    const refreshBox = await page.getByRole('button', { name: '重新生成' }).boundingBox();
    expect(refreshBox?.height ?? 0).toBeGreaterThanOrEqual(44);
    await page.screenshot({
      path: 'output/playwright/writing-suggestions/completed-dark-zh-mobile.png',
      fullPage: true,
    });

    expect(diagnostics).toEqual([]);
  } finally {
    await server.close();
  }
});
