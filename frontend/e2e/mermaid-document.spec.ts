// [Input] Original MermaidBlock, the local diagram document and explicit clipboard/export boundaries.
// [Output] Real SVG/source/zoom/PNG and document-revision acknowledgement qualification.
// [Pos] Provider-free browser tests; no backend, account, model, Notion or system-file operations.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild,type ViteDevServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {mermaidDocumentUrl,readMermaidEvent,readMermaidState} from '../app/_dream/components/chat/MermaidDocument.protocol';
const root=fileURLToPath(new URL('../',import.meta.url)),chart='flowchart LR\n  A[Original input] --> B[Saved output]\n';
let server:ViteDevServer,origin:string;
test.beforeAll(async()=>{
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-mermaid-20261030/cache/diagram',optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','i18next','react-i18next','mermaid']},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{name:'original-mermaid-document',enforce:'pre',resolveId(id){if(id==='/mermaid-entry.tsx')return '\0mermaid-entry';},async load(id){if(id==='\0mermaid-entry')return transformWithEsbuild(`import React from 'react';import {createRoot} from 'react-dom/client';import '/app/_dream/i18n.ts';import Document from '/app/_dream/components/chat/MermaidDocument.tsx';import Block from '/app/_dream/components/chat/MermaidBlock.tsx';createRoot(document.querySelector('#root')).render(location.pathname==='/mermaid-web'?<Block chart={${JSON.stringify(chart)}}/>:<Document/>);`,'mermaid-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(!['/native/mermaid','/mermaid-web'].includes(req.url??''))return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml(req.url!,`<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script>window.__diagramEvents=[];window.ReactNativeWebView={postMessage:data=>window.__diagramEvents.push(JSON.parse(data))};</script><script type="module" src="/mermaid-entry.tsx"></script></body></html>`));});}}]});
  await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('No fixture port');origin=`http://127.0.0.1:${address.port}`;
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{page.on('pageerror',error=>{throw error;});await page.addInitScript(()=>{localStorage.setItem('ink-language','en');Object.defineProperty(navigator,'clipboard',{value:{writeText:async(text:string)=>{(window as any).__copied=text;}}});});await page.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());});
async function events(page:Page){return page.evaluate(()=>(window as any).__diagramEvents as any[]);}
async function open(page:Page){await page.goto(origin+'/native/mermaid');await expect.poll(async()=>(await events(page)).find(event=>event.type==='ready')?.documentId).toBeTruthy();return (await events(page)).find(event=>event.type==='ready')!.documentId as string;}
async function state(page:Page,documentId:string,revision=1,source=chart,expanded=false){await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'state',documentId,revision,chart:source,expanded,theme:'light',language:'en'});}
async function ack(page:Page,value:any,accepted=true){await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'result',documentId:value.documentId,revision:value.revision,requestId:value.requestId,accepted});}
test('diagram protocol restricts origin, state shape and operation payloads',()=>{
  expect(mermaidDocumentUrl('http://localhost:5173')).toBe('http://localhost:5173/native/mermaid');expect(()=>mermaidDocumentUrl('https://example.test')).toThrow();
  expect(readMermaidState({type:'state',documentId:'d',revision:1,chart,expanded:false,theme:'light',language:'en'})).not.toBeNull();
  expect(readMermaidState({type:'state',documentId:'d',revision:1.5,chart,expanded:false,theme:'light',language:'en'})).toBeNull();
  expect(readMermaidEvent(JSON.stringify({type:'png',documentId:'d',revision:1,requestId:'p',name:'../../private.png',base64:'iVBORw0KGgo='}))).toBeNull();
});
test('ordinary Web retains real SVG, source, clipboard, zoom and PNG download defaults',async({page})=>{
  await page.goto(origin+'/mermaid-web');await expect(page.locator('.markdown-media-block__preview svg')).toBeVisible();
  await page.getByRole('button',{name:'Source',exact:true}).click();await expect(page.locator('.markdown-media-block__content code')).toHaveText(chart.trim());
  await page.getByRole('button',{name:'Copy Markdown source'}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__copied)).toBe('```mermaid\n'+chart.trimEnd()+'\n```');
  await page.getByRole('button',{name:'Preview',exact:true}).click();await page.getByRole('button',{name:'Enlarge'}).click();const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();await dialog.getByRole('button',{name:'Zoom in'}).click();await expect(dialog.getByText('110%',{exact:true})).toBeVisible();await dialog.getByRole('button',{name:'Close'}).click();await expect(dialog).toHaveCount(0);
  const download=page.waitForEvent('download',{timeout:10000});await page.getByRole('button',{name:'Export PNG'}).click();expect((await download).suggestedFilename()).toMatch(/^mermaid-diagram-\d+\.png$/);
});
test('document copy waits for matching native acknowledgement and retains source across updates',async({page})=>{
  const id=await open(page);await state(page,id);await expect(page.locator('.markdown-media-block__preview svg')).toBeVisible();await page.getByRole('button',{name:'Copy Markdown source'}).click();await expect.poll(async()=>(await events(page)).filter(e=>e.type==='copy').length).toBe(1);
  const copy=(await events(page)).find(e=>e.type==='copy');expect(copy.text).toBe('```mermaid\n'+chart.trimEnd()+'\n```');await ack(page,{...copy,documentId:'foreign'});await expect(page.getByRole('button',{name:'Copy Markdown source'})).toBeVisible();await ack(page,copy);
  await state(page,id,2,'flowchart LR\n C[Updated input] --> D[New result]');await expect(page.locator('.markdown-media-block__preview svg')).toContainText('New result');expect((await events(page)).filter(e=>e.type==='ready')).toHaveLength(1);
});
test('streaming syntax failure shows source and a newer valid revision recovers the same document',async({page})=>{
  const id=await open(page);await state(page,id);await expect(page.locator('.markdown-media-block__preview svg')).toBeVisible();await state(page,id,2,'flowchart LR\n A[');await expect(page.getByText('Mermaid · render failed',{exact:true})).toBeVisible();await expect(page.locator('.markdown-media-block__content code')).toContainText('A[');await expect(page.getByRole('button',{name:'Export PNG'})).toBeDisabled();
  await state(page,'foreign',999,'flowchart LR\n X --> Y');await expect(page.locator('.markdown-media-block__content code')).toContainText('A[');
  await state(page,id,3);await expect(page.locator('.markdown-media-block__preview svg')).toBeVisible();await expect(page.getByText('Mermaid · render failed',{exact:true})).toHaveCount(0);expect((await events(page)).filter(e=>e.type==='ready')).toHaveLength(1);
});
test('native preview intent opens the original full-screen zoom and close intent without application navigation',async({page})=>{
  const id=await open(page);await state(page,id);await expect(page.locator('.markdown-media-block__preview svg')).toBeVisible();await page.getByRole('button',{name:'Enlarge'}).click();expect((await events(page)).filter(e=>e.type==='preview').at(-1)).toMatchObject({documentId:id,revision:1,open:true});await expect(page.getByRole('dialog')).toHaveCount(0);
  await state(page,id,2,chart,true);const dialog=page.getByRole('dialog');await expect(dialog).toBeVisible();await dialog.getByRole('button',{name:'Zoom in'}).click();await expect(dialog.getByText('110%',{exact:true})).toBeVisible();await dialog.getByRole('button',{name:'Close'}).click();expect((await events(page)).filter(e=>e.type==='preview').at(-1)).toMatchObject({documentId:id,revision:2,open:false});
});
test('PNG rasterization uses the native acknowledgement and rejects stale results',async({page})=>{
  const id=await open(page);await state(page,id);await expect(page.locator('.markdown-media-block__preview svg')).toBeVisible();const button=page.getByRole('button',{name:'Export PNG'});await button.click();await expect.poll(async()=>(await events(page)).filter(e=>e.type==='png').length).toBe(1);
  const png=(await events(page)).find(e=>e.type==='png');expect(Buffer.from(png.base64,'base64').subarray(0,8).toString('hex')).toBe('89504e470d0a1a0a');await expect(button).toBeDisabled();await ack(page,{...png,revision:0});await expect(button).toBeDisabled();await ack(page,png);await expect(button).toBeEnabled();
});
