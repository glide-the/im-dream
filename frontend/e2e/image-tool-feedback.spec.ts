// [Input] Production image tool rows and pending-confirmation resolver, with isolated stream parts.
// [Output] Visible Chrome checks for error recovery text, interrupted history and native execution ownership.
// [Pos] Provider-free component verification; no model, database or completed image fixture.
// [Sync] 2026-10-11: verify review fixes through actual rendered components and the shared confirmation resolver.
import { expect, test } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

test.use({ channel: 'chrome' });

test('image failures retain actionable feedback and native execution never asks for local approval', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const source = `
    import React from 'react'; import { createRoot } from 'react-dom/client';
    import i18n from '/app/_dream/i18n.ts';
    import { ToolMessagePart } from '/app/_dream/components/chat/ToolMessagePart.tsx';
    import ToolConfirmationDock from '/app/_dream/components/chat/ToolConfirmationDock.tsx';
    import { resolvePendingToolConfirmation } from '/app/_dream/components/chat/toolConfirmation.ts';
    import '/app/_dream/styles/tokens.css'; import '/app/_dream/index.css';
    await i18n.changeLanguage('zh');
    const native = {type:'dynamic-tool',toolName:'image_generation',toolCallId:'ig-owned',
      providerExecuted:true,state:'input-available',input:{operation:'generate'}};
    const explicit = {type:'dynamic-tool',toolName:'mcp__image_gen__imagegen',toolCallId:'tool-owned',
      state:'input-available',input:{prompt:'Edit the current image',reference_images:['workspace-file:owned/current.png']}};
    const cases = [
      ['live-error', {...explicit,state:'output-error',errorText:'当前 AI 模型不可调用图片编辑，请在设置中选择支持图片编辑的 AI 模型后重试。'}],
      ['saved-error', {...explicit,state:'output-error',output:{message:'图片暂时无法访问，请重试查看。',code:'IMAGE_ACCESS_FAILED'}}],
      ['native-error', {...native,state:'output-error',errorText:JSON.stringify({code:'IMAGE_RESULT_INVALID',message:'图片结果未能保存，请核对本会话后再发送。'})}],
      ['interrupted', explicit],
      ['completed', {...explicit,state:'output-available',output:{internal:'internal-only'}}],
      ['running', native],
      ['settled', native],
    ];
    window.confirmationChecks = {
      nativeManual:resolvePendingToolConfirmation(native,'manual'),
      nativePending:resolvePendingToolConfirmation(native,'manual',new Set(),new Set(['ig-owned'])),
      explicitManual:resolvePendingToolConfirmation(explicit,'manual'),
      ordinaryManual:resolvePendingToolConfirmation({...explicit,toolName:'Read'},'manual'),
    };
    createRoot(document.getElementById('root')).render(React.createElement('main',{},
      ...cases.map(([name,part])=>React.createElement('section',{key:name,'aria-label':name},
        React.createElement(ToolMessagePart,{part,threadId:'owned-feedback-thread',
          isLast:name==='running'||name==='settled',isLoading:name==='running'||name==='settled',
          settledToolCallIds:name==='settled'?new Set(['ig-owned']):new Set()}))),
      React.createElement(ToolConfirmationDock,{confirmation:{kind:'confirm',toolCallId:explicit.toolCallId,
        toolName:explicit.toolName,input:explicit.input},threadId:'owned-feedback-thread',onSettled:()=>{}})));
  `;
  const server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false,
    logLevel: 'silent', server: { host: '127.0.0.1', port: 0, strictPort: true }, plugins: [{
      name: 'owned-image-feedback',
      configureServer(vite) { vite.middlewares.use(async (req, res, next) => {
        if (req.url !== '/image-feedback') return next();
        res.setHeader('Content-Type', 'text/html');
        res.end(await vite.transformIndexHtml('/image-feedback', '<!doctype html><html><body><div id="root"></div><script type="module" src="/image-feedback.js"></script></body></html>'));
      }); },
      resolveId: id => id === '/image-feedback.js' ? '\0image-feedback.js' : null,
      load: id => id === '\0image-feedback.js' ? source : null,
    }] });
  try {
    await server.listen();
    const address = server.httpServer!.address();
    if (!address || typeof address === 'string') throw new Error('Owned feedback fixture unavailable');
    await page.goto(`http://127.0.0.1:${address.port}/image-feedback`);
    await expect(page.getByRole('region', { name: 'live-error' }).getByRole('alert')).toContainText('选择支持图片编辑的 AI 模型后重试');
    await expect(page.getByRole('region', { name: 'saved-error' }).getByRole('alert')).toHaveText('图片暂时无法访问，请重试查看。');
    await expect(page.getByRole('region', { name: 'native-error' }).getByRole('alert')).toHaveText('图片结果未能保存，请核对本会话后再发送。');
    await expect(page.getByRole('region', { name: 'interrupted' })).toContainText('未完成');
    await expect(page.getByRole('region', { name: 'completed' })).toContainText('已完成');
    await expect(page.getByRole('region', { name: 'running' })).toContainText('进行中');
    await expect(page.getByRole('region', { name: 'settled' })).toContainText('进行中');
    await expect(page.getByText('internal-only', { exact: false })).toHaveCount(0);
    await expect(page.getByRole('alertdialog')).toHaveAccessibleName(/编辑图片/);
    await expect(page.getByRole('alertdialog')).not.toHaveAccessibleName(/mcp__image_gen/);
    expect(await page.evaluate(() => (window as unknown as { confirmationChecks: unknown }).confirmationChecks))
      .toEqual({ nativeManual: null, nativePending: null, explicitManual: 'confirm', ordinaryManual: 'confirm' });
    expect(errors).toEqual([]);
  } finally { await server.close(); }
});
