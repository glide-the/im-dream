// [Sync] 2026-11-24: inject a reader failure at the component export independently of its shared data type.
// [Sync] 2026-11-18: replay actual tab-numbered Read envelopes through the production message list and history recovery.
// [Input] Production ChatMessageList/Modal/NotionRenderer and original public tool/history DTOs.
// [Output] Isolated Chrome evidence for reader geometry, JSON/download, failures and history lifecycle.
// [Pos] Web-only provider-free presentation journey; no model, user database, Project/Episode or service mutation.
// [Sync] 2026-11-18: cover desktop/narrow reading and existing bounded history recovery.
// [Sync] 2026-11-18: verify compact borderless previews, icon actions, long titles and state feedback.
import {expect, test} from '@playwright/test';
// @ts-expect-error Node APIs belong to this isolated harness.
import {fileURLToPath} from 'node:url';
// @ts-expect-error Node APIs belong to this isolated harness.
import {readFile} from 'node:fs/promises';
import {createServer} from 'vite';

test.use({channel: 'chrome', viewport: {width: 1100, height: 800}});
test.beforeEach(async ({page}) => {
  await page.route('https://files.example.test/**', route => route.fulfill({contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160"><rect width="320" height="160" fill="#c7b59d"/></svg>'}));
});
const pageId = '41b30b75-47c3-803a-9079-e5c84adc127d';
const payload = {ok: true, page_id: pageId, title: '河边的观察', url: 'https://www.notion.so/' + pageId, markdown: '# 河边的观察\n\n今天读到一段关于时间的记录。\n\n| 时间 | 事件 |\n| --- | --- |\n| 上午 | 观察河流 |\n\n```json\n{"message":"' + 'long-value-'.repeat(60) + '"}\n```\n\n' + '后续观察段落。\n\n'.repeat(100), snapshot: {version: 7}};
const enhanced = '\n\n<file src="https://files.example.test/observations.pdf?signature=saved-value">观察附件.pdf</file>\n\n<mention-page url="https://www.notion.so/observations">关联观察页面</mention-page> 与 <mention-database url="https://www.notion.so/records">观察记录库</mention-database>\n\n<empty-block/>\n<callout icon="💡">\n提示正文\n</callout>\n<details><summary>更多观察</summary>\n折叠后的观察内容\n</details>\n<columns><column>左栏观察</column><column>右栏观察</column></columns>\n<table header-row="true"><tr><td>项目</td><td>说明</td></tr><tr><td>河流</td><td>持续变化</td></tr></table>\n\n![观察照片](https://files.example.test/observation.png)\n\n\\(x^2\\)\n\n```xml\n<file src="literal">代码标签</file>\n```';
payload.markdown = payload.markdown.replace('后续观察段落。', enhanced + '\n\n后续观察段落。');
const moduleSource = `
import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import i18n from '/app/_dream/i18n.ts';
import mermaid from 'mermaid';
window.parseNotionDiagrams = async diagrams => {mermaid.initialize({startOnLoad:false}); for(const diagram of diagrams) await mermaid.parse(diagram); return diagrams.length;};
import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.tsx';
import 'react-notion-x/styles.css';
import '/app/_dream/styles/tokens.css';
import '/app/_dream/styles/markdown.css';
import '/app/_dream/index.css';
import {setThemeMode, initTheme} from '/app/_dream/utils/theme.ts';
initTheme();
window.setNotionTheme=setThemeMode;
void i18n.changeLanguage('zh');
const payload = ${JSON.stringify(payload)};
const metadata = {turnId:'notion-turn',turnStatus:'completed',finalPartIndex:1,durationMs:100};
const tool = output => ({type:'dynamic-tool',toolName:'Read',toolCallId:'read-page',state:'output-available',input:{file_path:'.notion/pages/${pageId}.json'},output:'1\\t'+JSON.stringify(output)+'\\n\\n<system-reminder>tool reminder</system-reminder>'});
const full = output => ({id:'assistant-notion',role:'assistant',parts:[tool(output),{type:'text',text:'已阅读这篇记录。'}],metadata});
window.notionProcessReads=0;
const originalFetch=window.fetch.bind(window);
window.fetch=(input,init)=>{
  if(String(input).includes('/messages/assistant-notion/process')){
    window.notionProcessReads++;
    return Promise.resolve(new Response(JSON.stringify(full(payload)),{headers:{'Content-Type':'application/json'}}));
  }
  return originalFetch(input,init);
};
function Harness(){
 const [thread,setThread]=useState('notion-preview-thread'),[fixture,setFixture]=useState('ready');
 window.switchNotionThread=()=>setThread('other-thread');
 window.setNotionFixture=setFixture;
 const output=fixture==='empty'?{...payload,markdown:''}:fixture==='error'?{ok:false,page_id:payload.page_id,code:'NOTION_PERMISSION_DENIED'}:fixture==='long'?{...payload,title:'关于时间、日记与生活观察的长期记录'.repeat(6)}:payload;
 const message=fixture==='history'?{id:'assistant-notion',role:'assistant',parts:[{type:'text',text:'已阅读这篇记录。'}],metadata:{...metadata,historyProjectionVersion:1,historyProcessAvailable:true}}:full(output);
 return React.createElement('main',{style:{width:'min(900px,100%)',height:'680px',margin:'0 auto',boxSizing:'border-box',padding:'12px'}},
 React.createElement('div',{'data-chat-preview-container':true,style:{position:'relative',height:'100%',minWidth:0,border:'1px solid var(--color-border-paper)',overflow:'hidden'}},
 React.createElement('div',{style:{height:'100%',overflow:'auto',padding:'12px',boxSizing:'border-box'}},React.createElement(ChatMessageList,{messages:[message],threadId:thread,isLoading:false,addToolResult:()=>{},historicalMessageIds:fixture==='history'?new Set(['assistant-notion']):new Set()}))));
}
createRoot(document.querySelector('#root')).render(React.createElement(Harness));
`;

async function harness(rendererFault = false) {
  const server = await createServer({root: fileURLToPath(new URL('../../../../../', import.meta.url)), configFile: false, logLevel: 'error',
    optimizeDeps: {entries: [], include: ['react', 'react-dom/client', 'react/jsx-runtime', 'mermaid', 'react-notion-x', 'react-notion-x/third-party/code', 'htmlparser2', 'mdast-util-from-markdown', 'mdast-util-gfm', 'micromark-extension-gfm']},
    server: {host: '127.0.0.1', port: 0}, plugins: [{name: 'notion-preview-isolated-harness', enforce: 'pre',
      transform(code, id) {
        if (rendererFault && id.endsWith('/NotionPageDocument.tsx')) {
          return code.replace('export default function NotionPageDocument', 'function NotionPageDocument') + `
            export default function FaultableDocument(props: Parameters<typeof NotionPageDocument>[0]) {
              if (!window.notionRendererRecovered) throw Error("Isolated renderer fault");
              return <NotionPageDocument {...props}/>;
            }`;
        }
      },
      configureServer(vite) {vite.middlewares.use((req, res, next) => {
        if (req.url !== '/notion-preview') return next();
        void vite.transformIndexHtml('/notion-preview', '<!doctype html><html><head><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/notion-preview-harness.js"></script></body></html>').then(html => {res.setHeader('Content-Type', 'text/html'); res.end(html);}, next);
      });},
      resolveId(id) {return id === '/notion-preview-harness.js' ? '\0notion-preview-harness.js' : null;},
      load(id) {return id === '\0notion-preview-harness.js' ? moduleSource : null;},
    }]});
  await server.listen();
  const address = server.httpServer?.address();
  if (!address || typeof address === 'string') {await server.close(); throw Error('Missing isolated harness port');}
  return {server, url: `http://127.0.0.1:${address.port}/notion-preview`};
}

test('reads, inspects and downloads one existing result within desktop and narrow conversation bounds', async ({page}, testInfo) => {
  const {server, url} = await harness();
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const fixture = async (value: string) => page.evaluate(value => (window as unknown as {setNotionFixture: (value: string) => void}).setNotionFixture(value), value);
  try {
    await page.goto(url);
    const card = page.locator('[data-notion-page]');
    await expect(card).toHaveCount(1);
    await expect(card).toContainText('今天读到一段关于时间的记录');
    await expect(card.getByRole('heading', {name: '河边的观察', exact: true})).toBeVisible();
    const expand = page.getByRole('button', {name: '展开河边的观察', exact: true});
    await expand.click();
    const dialog = page.getByRole('dialog', {name: '河边的观察', exact: true});
    await expect(dialog.locator('.notion-h1')).toHaveText('河边的观察');
    const container = await page.locator('[data-chat-preview-container]').boundingBox(), box = await dialog.boundingBox();
    expect(Math.abs(box!.width - container!.width)).toBeLessThanOrEqual(2);
    expect(Math.abs(box!.height - container!.height)).toBeLessThanOrEqual(2);
    await dialog.getByRole('button', {name: 'JSON 详情', exact: true}).click();
    await expect(dialog.getByRole('complementary', {name: 'JSON 详情'})).toContainText('"version": 7');
    await page.screenshot({path: testInfo.outputPath('desktop-json.png')});
    const downloadPromise = page.waitForEvent('download');
    await dialog.getByRole('button', {name: '下载 JSON', exact: true}).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`${pageId}.json`);
    expect(JSON.parse(await readFile((await download.path())!, 'utf8'))).toEqual(payload);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(expand).toBeFocused();
    expect(await page.evaluate(() => document.body.style.overflow)).toBe('');
    await page.setViewportSize({width: 360, height: 740});
    await expand.click();
    await dialog.getByRole('button', {name: 'JSON 详情', exact: true}).click();
    await expect(dialog.getByRole('article', {name: '页面正文', exact: true})).toBeHidden();
    await expect(dialog.getByRole('complementary', {name: 'JSON 详情'})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    const close = dialog.getByRole('button', {name: '关闭页面预览'});
    await expect(close).toBeInViewport();
    await close.focus();
    await page.keyboard.press('Tab');
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
    await page.screenshot({path: testInfo.outputPath('narrow-json.png')});
    await dialog.getByRole('button', {name: '页面正文', exact: true}).click();
    await expect(dialog.getByRole('article', {name: '页面正文', exact: true})).toBeVisible();
    await close.click();
    await page.evaluate(() => {
      const state = window as unknown as {notionOriginalBlob: typeof URL.createObjectURL};
      state.notionOriginalBlob = URL.createObjectURL;
      URL.createObjectURL = () => {throw Error('Download fixture failure');};
    });
    await card.getByRole('button', {name: '下载 JSON', exact: true}).click();
    await expect(card.getByRole('alert')).toHaveText('JSON 下载失败，请重试。');
    await page.evaluate(() => {URL.createObjectURL = (window as unknown as {notionOriginalBlob: typeof URL.createObjectURL}).notionOriginalBlob;});
    const retryDownload = page.waitForEvent('download');
    await card.getByRole('button', {name: '下载 JSON', exact: true}).click();
    await retryDownload;
    await expect(card.getByRole('alert')).toHaveCount(0);
    await fixture('empty');
    await expect(card).toContainText('此页面暂无正文。');
    await fixture('error');
    await expect(card.getByRole('alert')).toContainText('恢复 Notion 连接或页面权限');
    await fixture('ready');
    await expand.click();
    await page.evaluate(() => (window as unknown as {switchNotionThread: () => void}).switchNotionThread());
    await expect(dialog).toHaveCount(0);
    expect(await page.evaluate(() => document.body.style.overflow)).toBe('');
    expect(await page.evaluate(() => (window as unknown as {notionProcessReads: number}).notionProcessReads)).toBe(0);
    expect(errors).toEqual([]);
  } finally {await server.close();}
});

test('keeps an automatically recovered historical preview outside the process without duplicate cards', async ({page}) => {
  const {server, url} = await harness();
  try {
    await page.goto(url);
    await page.evaluate(() => (window as unknown as {setNotionFixture: (value: string) => void}).setNotionFixture('history'));
    const card = page.locator('[data-notion-page]');
    await expect(card).toHaveCount(1);
    await expect.poll(() => page.evaluate(() => (window as unknown as {notionProcessReads: number}).notionProcessReads)).toBe(1);
    expect(await card.evaluate(element => Boolean(element.closest('[data-turn-outside-process]')))).toBe(true);
    const disclosure = page.getByRole('button', {name: /展开.*过程|展开.*用时/});
    await disclosure.click();
    await expect(card).toHaveCount(1);
    expect(await page.locator('[data-turn-process] [data-notion-page]').count()).toBe(0);
    await page.getByRole('button', {name: /收起.*过程|收起.*用时/}).click();
    await expect(card).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as {notionProcessReads: number}).notionProcessReads)).toBe(1);
  } finally {await server.close();}
});

test('keeps document cards readable and actions reachable across themes, narrow width and content states', async ({page}, testInfo) => {
  const {server, url} = await harness();
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(url);
    const card = page.locator('[data-notion-page]');
    const read = card.getByRole('button', {name: '展开河边的观察', exact: true});
    await expect(card.getByRole('heading', {name: '河边的观察', exact: true})).toBeVisible();
    await expect(read).toHaveAttribute('title', '展开河边的观察');
    await expect(read).toHaveAttribute('aria-haspopup', 'dialog');
    await expect(card.getByRole('button', {name: '下载 JSON', exact: true})).toBeVisible();
    expect((await card.boundingBox())!.width).toBeLessThanOrEqual(576);
    expect((await card.boundingBox())!.height).toBeLessThanOrEqual(112);
    const hasOverflow = () => card.evaluate(element => element.scrollWidth > element.clientWidth + 1);
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => (window as unknown as {setNotionTheme: (value: string) => void}).setNotionTheme(theme), theme);
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      expect(await hasOverflow()).toBe(false);
      await card.screenshot({path: testInfo.outputPath('card-desktop-' + theme + '.png')});
    }
    await page.setViewportSize({width: 360, height: 740});
    const fixture = async (value: string) => page.evaluate(value => (window as unknown as {setNotionFixture: (value: string) => void}).setNotionFixture(value), value);
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => (window as unknown as {setNotionTheme: (value: string) => void}).setNotionTheme(theme), theme);
      await expect(read).toBeInViewport();
      await expect(card.getByRole('button', {name: '下载 JSON', exact: true})).toBeInViewport();
      expect(await hasOverflow()).toBe(false);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await card.screenshot({path: testInfo.outputPath('card-narrow-' + theme + '.png')});
    }
    await fixture('long');
    await expect(card.getByRole('heading')).toHaveText('关于时间、日记与生活观察的长期记录'.repeat(6));
    await expect(card.getByRole('button', {name: /展开关于时间/})).toBeInViewport();
    expect(await hasOverflow()).toBe(false);
    await card.screenshot({path: testInfo.outputPath('card-narrow-long-title.png')});
    await fixture('empty');
    await expect(card).toContainText('此页面暂无正文。');
    await card.screenshot({path: testInfo.outputPath('card-narrow-empty.png')});
    await fixture('error');
    await expect(card.getByRole('alert')).toContainText('恢复 Notion 连接或页面权限');
    await expect(card.getByRole('button', {name: /展开/})).toBeInViewport();
    expect(await hasOverflow()).toBe(false);
    await card.screenshot({path: testInfo.outputPath('card-narrow-error.png')});
    expect(errors).toEqual([]);
  } finally {await server.close();}
});

test('renders enhanced tags through NotionRenderer with theme, narrow columns and image recovery', async ({page}, testInfo) => {
  const {server, url} = await harness();
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  let moduleRequests = 0, imageAttempts = 0;
  page.on('request', request => {if (request.url().includes('/NotionPageDocument.tsx')) moduleRequests++;});
  await page.route('https://files.example.test/observation.png', route => ++imageAttempts === 1 ? route.abort() : route.fulfill({contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160"><rect width="320" height="160" fill="#c7b59d"/></svg>'}));
  try {
    await page.goto(url);
    await expect(page.locator('[data-notion-page]')).toBeVisible();
    expect(moduleRequests).toBe(0);
    await page.getByRole('button', {name: '展开河边的观察', exact: true}).click();
    const dialog = page.getByRole('dialog');
    const body = dialog.getByRole('article', {name: '页面正文', exact: true});
    await expect(body.locator('.notion-preview__document')).toBeVisible();
    expect(moduleRequests).toBeGreaterThan(0);
    await expect(body.locator('.notion-file').getByRole('link', {name: '观察附件.pdf'})).toHaveAttribute('href', 'https://files.example.test/observations.pdf?signature=saved-value');
    await expect(body.getByRole('link', {name: '关联观察页面', exact: true})).toHaveAttribute('href', 'https://www.notion.so/observations');
    await expect(body.getByRole('link', {name: '观察记录库', exact: true})).toBeVisible();
    await expect(body.locator('.notion-callout')).toContainText('提示正文');
    await expect(body.getByText('折叠后的观察内容', {exact: true})).toBeHidden();
    await body.locator('summary', {hasText: '更多观察'}).click();
    await expect(body.getByText('折叠后的观察内容', {exact: true})).toBeVisible();
    await expect(body.locator('.notion-simple-table')).toHaveCount(2);
    await expect(body.locator('.notion-code').filter({hasText: '代码标签'})).toContainText('<file src="literal">代码标签</file>');
    await expect(body.locator('script, mention-page, file')).toHaveCount(0);
    await expect(body.locator('.chat-math .katex')).toBeVisible();
    await body.locator('.notion-preview__image').scrollIntoViewIfNeeded();
    await expect(body.getByRole('alert')).toContainText('图片暂时无法加载');
    await body.getByRole('button', {name: '重试', exact: true}).click();
    await expect(body.getByRole('img', {name: '观察照片', exact: true})).toBeVisible();
    await expect(body.getByRole('alert')).toHaveCount(0);
    expect(imageAttempts).toBe(2);
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => (window as unknown as {setNotionTheme: (theme: string) => void}).setNotionTheme(theme), theme);
      await expect(body.locator('.notion-preview__document')).toHaveClass(new RegExp(theme + '-mode'));
      const colors = await body.locator('.notion-preview__document').evaluate(element => {
        const style = getComputedStyle(element);
        const rgb = (color: string) => color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(value => {const c = value / 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;});
        const lum = (color: string) => rgb(color).reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
        const fg = lum(style.color), bg = lum(style.backgroundColor);
        return {contrast: (Math.max(fg, bg) + .05) / (Math.min(fg, bg) + .05), color: style.color, background: style.backgroundColor};
      });
      expect(colors.contrast).toBeGreaterThanOrEqual(4.5);
      await testInfo.attach(theme + '-colors', {body: JSON.stringify(colors), contentType: 'application/json'});
      await body.evaluate(element => {element.scrollTop = 0;});
      await page.screenshot({path: testInfo.outputPath('enhanced-' + theme + '.png')});
    }
    await page.evaluate(() => (window as unknown as {setNotionTheme: (theme: string) => void}).setNotionTheme('system'));
    await page.emulateMedia({colorScheme: 'light'});
    await expect(body.locator('.notion-preview__document')).toHaveClass(/light-mode/);
    await page.emulateMedia({colorScheme: 'dark'});
    await expect(body.locator('.notion-preview__document')).toHaveClass(/dark-mode/);
    await page.setViewportSize({width: 360, height: 740});
    await expect(body.locator('.notion-column').first()).toBeVisible();
    const columns = await body.locator('.notion-column').all();
    const left = await columns[0].boundingBox(), right = await columns[1].boundingBox();
    expect(Math.abs(left!.x - right!.x)).toBeLessThan(2);
    expect(right!.y).toBeGreaterThan(left!.y);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await body.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
    await page.screenshot({path: testInfo.outputPath('enhanced-narrow-dark.png')});
    await dialog.getByRole('button', {name: '关闭页面预览'}).click();
    expect(errors).toEqual([]);
  } finally {await server.close();}
});

test('recovers a renderer failure while keeping JSON and close actions available', async ({page}) => {
  const {server, url} = await harness(true);
  try {
    await page.goto(url);
    await page.getByRole('button', {name: '展开河边的观察', exact: true}).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByRole('alert')).toContainText('页面预览暂时无法显示');
    await dialog.getByRole('button', {name: 'JSON 详情', exact: true}).click();
    await expect(dialog.getByRole('complementary', {name: 'JSON 详情'})).toContainText('"version": 7');
    await page.evaluate(() => {(window as unknown as {notionRendererRecovered: boolean}).notionRendererRecovered = true;});
    await dialog.getByRole('button', {name: '重试', exact: true}).click();
    await expect(dialog.locator('.notion-preview__document')).toBeVisible();
    await expect(dialog.getByRole('alert')).toHaveCount(0);
    await dialog.getByRole('button', {name: '关闭页面预览'}).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByRole('button', {name: '展开河边的观察', exact: true})).toBeFocused();
  } finally {await server.close();}
});


test('parses all formal design Mermaid diagrams in the installed browser runtime', async ({page}) => {
  const source = await readFile(fileURLToPath(new URL('../../../../../../docs/design/workspace/notion-workspace-preview.md', import.meta.url)), 'utf8');
  const diagrams = [...source.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(match => match[1]);
  expect(diagrams).toHaveLength(3);
  const {server, url} = await harness();
  try {
    await page.goto(url);
    const parsed = await page.evaluate(async diagrams => {
      return (window as unknown as {parseNotionDiagrams: (diagrams: string[]) => Promise<number>}).parseNotionDiagrams(diagrams);
    }, diagrams);
    expect(parsed).toBe(3);
  } finally {await server.close();}
});
