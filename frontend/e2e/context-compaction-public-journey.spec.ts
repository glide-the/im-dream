// [Sync] 2026-10-12: validate compact menu percentage, history, no-send selection and narrow layout.
// [Input] Complete production ChatPanel and public isolated SDK/Admin composition.
// [Output] Chrome evidence for visible progress, source, cancellation, refresh/reconnect, recovery and responsive states.
// [Pos] Provider-free technical E2E, distinct from normal CLI/model/Admin acceptance.
// [Sync] 2026-10-12: inject only SDK DTOs; never manufacture frontend SSE or a completed UI message.
// Impact: Chat inputs/replies/metadata change; existing text/session/model are preserved.
// Project/Episode/canonical Artifact/Run-private .dream/Story Hook are outside this Chat-only scenario.
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chrome' });
test.describe.configure({ mode: 'serial' });
test.setTimeout(90_000);
let child: ChildProcess, server: ViteDevServer, ownedRoot: string, url: string;
let backendLog = '';
const source = `
  import React, {useEffect,useState} from 'react'; import {createRoot} from 'react-dom/client';
  import i18n from '/app/_dream/i18n.ts';
  import {loadBrowserSession,browserRequestHeaders} from '/app/_dream/lib/browserSession.ts';
  import ChatPanel from '/app/_dream/components/chat/ChatPanel.tsx';
  import {hydrateClaudeThreadSession} from '/app/_dream/components/chat/threadSessionHydration.ts';
  import {WorkspaceProvider} from '/app/_dream/contexts/WorkspaceContext.tsx';
  import '/app/_dream/styles/tokens.css'; import '/app/_dream/index.css';
  await loadBrowserSession(); await i18n.changeLanguage('en');
  function Chat({thread}) {
    const [snapshot,setSnapshot]=useState(null);
    const recover=async()=>{
      const current=await hydrateClaudeThreadSession(thread);
      return {...current,historyPage:{nextCursor:current.nextCursor,hasMore:current.hasMore,latestMessageId:current.latestMessageId},toolConfirmationKnown:current.status!==null};
    };
    useEffect(()=>{
      let mounted=true;recover().then(current=>{if(mounted)setSnapshot(current);}).catch(console.error);
      return()=>{mounted=false;};
    },[thread]);
    if(!snapshot)return React.createElement('p',{role:'status'},'Loading existing history');
    return React.createElement(ChatPanel,{key:thread,threadId:thread,initialMessages:snapshot.messages,
      initialHistoryPage:snapshot.historyPage,initialRuntimeRunning:snapshot.running,
      initialSettledToolCallIds:snapshot.settledToolCallIds,initialRuntimePendingToolCallIds:snapshot.runtimePendingToolCallIds,
      initialToolConfirmationKnown:true,reconnectStreamNonce:snapshot.running?1:0,onReconnectComplete:recover});
  }
  function Harness(){
    const [thread,setThread]=useState(new URL(location.href).searchParams.get('thread'));
    return React.createElement('main',{style:{maxWidth:760,margin:'0 auto',padding:12,height:'100dvh',boxSizing:'border-box',display:'flex',flexDirection:'column'}},
      !thread?React.createElement('button',{onClick:async()=>{
        const response=await fetch('/api/claude-agent/threads',{method:'POST',headers:{'Content-Type':'application/json',...browserRequestHeaders()},body:JSON.stringify({title:'Isolated context compaction journey'})});
        const data=await response.json();history.replaceState(null,'','?thread='+data.thread_id);setThread(data.thread_id);}},'开始隔离对话'):
        React.createElement(WorkspaceProvider,{},React.createElement(Chat,{thread})));
  }
  createRoot(document.getElementById('root')).render(React.createElement(Harness));
`;

test.beforeAll(async () => {
  ownedRoot = await mkdtemp(join(tmpdir(), 'im-context-compaction-browser-20261012-'));
  const repository = fileURLToPath(new URL('../../', import.meta.url));
  child = spawn(join(repository, 'backend/.venv/bin/python'), ['-m', 'tests.serve_context_compaction_journey', '--root', join(ownedRoot, 'context-compaction-browser-fixture')],
    { cwd: repository, env: { ...process.env, PYTHONPATH: 'backend:.' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const port = await new Promise<number>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Fixture startup failed: '+backendLog)), 15_000);
    child.stdout!.on('data', data => { backendLog+=data.toString();const match=backendLog.match(/\{"port":\s*(\d+)\}/);if(match){clearTimeout(timer);resolve(Number(match[1]));} });
    child.stderr!.on('data', data => { backendLog+=data.toString(); });
    child.once('exit', code => { clearTimeout(timer);reject(new Error('Fixture exit '+code+': '+backendLog)); });
  });
  server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true,
      proxy: { '/api': 'http://127.0.0.1:'+port, '/auth': 'http://127.0.0.1:'+port, '/_fixture': 'http://127.0.0.1:'+port } },
    plugins: [{ name:'context-compaction-public-owned-fixture',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
      if(req.url?.split('?')[0] !== '/compaction-journey') return next();
      res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/compaction-journey',
        '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/compaction-journey.js"></script></body></html>'));});},
      resolveId:id=>id==='/compaction-journey.js'?'\0compaction-journey.js':null,load:id=>id==='\0compaction-journey.js'?source:null }],
  });
  await server.listen();const address=server.httpServer!.address();
  if(!address || typeof address==='string') throw new Error('Owned Vite port unavailable');
  url='http://127.0.0.1:'+address.port+'/compaction-journey';
});
test.afterAll(async () => {
  await server?.close();
  if(child && child.exitCode===null) {
    const stopped=new Promise<void>(resolve=>child.once('exit',()=>resolve()));child.kill('SIGTERM');
    await Promise.race([stopped,new Promise<void>(resolve=>setTimeout(resolve,5_000))]);
    if(child.exitCode===null) child.kill('SIGKILL');
  }
  if(ownedRoot) await rm(ownedRoot,{recursive:true,force:true});
});

async function openChat(page: Page) {
  await page.route('**/api/claude-agent/skill-commands**',route=>route.fulfill({json:{commands:[]}}));
  await page.route('**/plugin-load-receipt',route=>route.fulfill({json:{deck_id:null,workspace_found:false,receipt:null,launch_manifest:null}}));
  await page.route('**/subagents**',route=>route.fulfill({json:{tasks:[]}}));
  await page.goto(url);
  await page.getByRole('button',{name:'开始隔离对话'}).click();
  await expect(page.getByRole('textbox',{name:'Chat input'})).toBeVisible();
}
async function mode(page: Page, selected: string, hold = false) {
  await page.request.post(new URL('/_fixture/mode',url).href,{data:{mode:selected,hold}});
}
async function send(page: Page, text: string) {
  await page.getByRole('textbox',{name:'Chat input'}).fill(text);
  await page.getByRole('button',{name:'Send message',exact:true}).click();
}
const markers = (page: Page) => page.locator('[data-context-compaction-id]');

test('builtin compact shows actual last input usage, survives history and withdraws it after compaction', async ({page}, info) => {
  const verifyDiagnostics = diagnostics(page, info);
  await openChat(page);
  const editor = page.getByRole('textbox', {name:'Chat input'});
  await editor.fill('/compact');
  await expect(page.getByRole('option', {name:'/compact'})).toContainText('Usage unavailable');
  expect((await (await page.request.get(new URL('/_fixture/receipt', url).href)).json()).calls).toHaveLength(0);
  await editor.press('Escape'); await editor.fill('Hello');
  await mode(page, 'ordinary'); await page.getByRole('button', {name:'Send message', exact:true}).click();
  await expect(page.getByText('Continue normally.', {exact:true})).toBeVisible();
  await expect(page.getByRole('button', {name:'Stop generating', exact:true})).toHaveCount(0);
  await editor.fill('/compact');
  await expect(page.getByRole('option', {name:'/compact'})).toContainText('42% used');
  await page.screenshot({path:info.outputPath('desktop-compact-usage-menu.png'),fullPage:true});
  await editor.press('Tab');
  await expect(page.getByRole('listbox')).toHaveCount(0);
  expect((await (await page.request.get(new URL('/_fixture/receipt', url).href)).json()).calls).toHaveLength(1);
  await page.reload(); await expect(editor).toBeVisible(); await editor.fill('/compact');
  await expect(page.getByRole('option', {name:'/compact'})).toContainText('42% used');
  await mode(page, 'manual'); await page.getByRole('button', {name:'Send message',exact:true}).click();
  await expect(page.getByText('Context compacted', {exact:true})).toBeVisible();
  await editor.fill('/compact');
  await expect(page.getByRole('option', {name:'/compact'})).toContainText('Usage unavailable');
  await editor.press('Escape'); await mode(page,'ordinary'); await send(page, 'Continue');
  await expect(page.getByRole('button', {name:'Stop generating',exact:true})).toHaveCount(0);
  await page.setViewportSize({width:375,height:812});
  await page.evaluate(async()=>{const locale='/app/_dream/i18n.ts';await (await import(locale)).default.changeLanguage('zh');});
  await page.getByRole('textbox', {name:'聊天输入'}).fill('/compact');
  const option = page.getByRole('option', {name:'/compact'});
  await expect(option).toContainText('已使用 42%');
  const box = await option.boundingBox(); expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0); expect(box!.x+box!.width).toBeLessThanOrEqual(375);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('narrow-compact-usage-menu.png'),fullPage:true});
  await info.attach('usage-public-receipt', {body:JSON.stringify(await (await page.request.get(new URL('/_fixture/receipt',url).href)).json(),null,2),contentType:'application/json'});
  await verifyDiagnostics();
});

function diagnostics(page: Page, info: TestInfo) {
  const errors: string[] = [], network: string[] = [];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  page.on('response',response=>{if(response.status()>=400)network.push(`${response.status()} ${response.url()}`);});
  page.on('requestfailed',request=>network.push(`${request.failure()?.errorText} ${request.method()} ${request.url()}`));
  return async () => {
    await info.attach('browser-diagnostics',{body:JSON.stringify({errors,network},null,2),contentType:'application/json'});
    expect(errors).toEqual([]);
    // Original ChatPanel aborts GET stream on reload and turn-navigation on
    // latest-message/busy changes (its existing useEffect cleanup). Retain
    // those exact client-cancellation diagnostics; other failures still fail.
    expect(network.filter(entry=>!/^net::ERR_ABORTED GET .*\/(stream|turn-navigation)$/.test(entry))).toEqual([]);
  };
}

test('manual completion survives reconnect; automatic cancellation, retry and subsequent dialogue remain distinct', async ({page}, info) => {
  const verifyDiagnostics=diagnostics(page,info);
  await openChat(page); await mode(page,'manual',true); await send(page,'/compact');
  await expect(markers(page)).toHaveCount(1);
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','running');
  await expect(page.getByText('Compacting context',{exact:true})).toBeVisible();
  await page.reload();
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','running');
  await mode(page,'manual');
  await expect(markers(page)).toHaveCount(1);
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-trigger','manual');
  await expect(page.getByText('Context compacted',{exact:true})).toBeVisible();
  await expect(page.getByText('Compacted',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Stop generating',exact:true})).toHaveCount(0);
  await page.reload(); await expect(markers(page)).toHaveCount(1);
  await mode(page,'ordinary'); await send(page,'继续刚才的对话。');
  await expect(page.getByText('Continue normally.',{exact:true})).toBeVisible();
  await expect(markers(page)).toHaveCount(1);
  await mode(page,'auto',true); await send(page,'再接着讨论。');
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','running');
  await page.getByRole('button',{name:'Stop generating',exact:true}).click();
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','cancelled');
  await page.reload(); await expect(markers(page)).toHaveCount(2);
  await expect(markers(page).last().locator('.context-compaction-marker__spinner')).toHaveCount(0);
  await mode(page,'auto'); await send(page,'继续对话。');
  await expect(markers(page)).toHaveCount(3);
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-trigger','auto');
  await expect(page.getByText('Context automatically compacted',{exact:true})).toBeVisible();
  await page.reload(); await expect(markers(page)).toHaveCount(3);
  const thread = new URL(page.url()).searchParams.get('thread');
  const history = await (await page.request.get(new URL('/api/claude-agent/threads/'+thread+'/messages?full=true',url).href)).json();
  expect(history.messages.filter((m:{role:string})=>m.role==='assistant')).toHaveLength(4);
  expect(history.messages.some((m:{parts:{text?:string}[]})=>m.parts.some(p=>p.text==='Compacted'))).toBe(true);
  expect(history.messages.some((m:{parts:unknown[];metadata?:{contextCompactions?:{state:string}[]}})=>m.parts.length===0 && m.metadata?.contextCompactions?.[0].state==='cancelled')).toBe(true);
  await info.attach('public-history',{body:JSON.stringify(history,null,2),contentType:'application/json'});
  await page.screenshot({path:info.outputPath('desktop-compaction-history.png'),fullPage:true});
  await page.setViewportSize({width:375,height:812});
  await page.evaluate(async()=>{const path='/app/_dream/utils/theme.ts';(await import(path)).setThemeMode('dark');const locale='/app/_dream/i18n.ts';await (await import(locale)).default.changeLanguage('zh');});
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await expect(page.getByText('上下文已自动压缩',{exact:true})).toBeVisible();
  await expect(page.getByRole('textbox')).toBeEnabled();
  await page.getByRole('textbox').click();
  await markers(page).last().scrollIntoViewIfNeeded();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  const box=await markers(page).last().boundingBox();expect(box).not.toBeNull();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(375);
  expect(box!.y).toBeGreaterThanOrEqual(0);expect(box!.y+box!.height).toBeLessThanOrEqual(812);
  await page.screenshot({path:info.outputPath('narrow-dark-chinese-compaction.png'),fullPage:true});
  await page.goto(url); await page.getByRole('button',{name:'开始隔离对话'}).click();
  await expect(markers(page)).toHaveCount(0);await verifyDiagnostics();
  await info.attach('fixture-server-log',{body:backendLog,contentType:'text/plain'});
});

test('failure recovers, a missing boundary stays unknown, ordinary Compacted prose remains visible', async ({page}, info) => {
  const verifyDiagnostics=diagnostics(page,info);
  await openChat(page);await mode(page,'failed');await send(page,'/compact');
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','failed');
  await expect(page.getByRole('button',{name:'Stop generating',exact:true})).toHaveCount(0);
  await page.reload();await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','failed');
  await mode(page,'unconfirmed');await send(page,'继续对话。');
  await expect(markers(page)).toHaveCount(2);
  await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','unconfirmed');
  await expect(markers(page).last().locator('.context-compaction-marker__spinner')).toHaveCount(0);
  await page.reload();await expect(markers(page).last()).toHaveAttribute('data-context-compaction-state','unconfirmed');
  await mode(page,'literal');await send(page,'解释压缩的结果。');
  await expect(page.getByText('Compacted',{exact:true})).toBeVisible();
  await expect(markers(page)).toHaveCount(2);
  await page.reload();await expect(page.getByText('Compacted',{exact:true})).toBeVisible();
  await verifyDiagnostics();
  await info.attach('fixture-receipt',{body:await (await page.request.get(new URL('/_fixture/receipt',url).href)).text(),contentType:'application/json'});
});

test('formal Mermaid sequence and state diagrams parse in Chrome DOM', async ({page}, info) => {
  await page.goto(url);
  const repository=fileURLToPath(new URL('../../',import.meta.url));
  const document=await readFile(join(repository,'docs/design/claude-agent/context-compaction-interaction.md'),'utf8');
  const graphs=[...document.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(match=>match[1]);
  expect(graphs).toHaveLength(3);
  const parsed=await page.evaluate(async graphs=>{const path='/node_modules/mermaid/dist/mermaid.esm.min.mjs';const mermaid=(await import(path)).default;mermaid.initialize({startOnLoad:false});const results=[];for(const graph of graphs)results.push(await mermaid.parse(graph));return results;},graphs);
  expect(parsed).toHaveLength(3);
  await info.attach('mermaid-parser',{body:JSON.stringify(parsed,null,2),contentType:'application/json'});
});
