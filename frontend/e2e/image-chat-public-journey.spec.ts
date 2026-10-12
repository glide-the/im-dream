// [Input] Production Settings/composer/message/transport/history/file components and isolated public FastAPI composition.
// [Output] Visible Chrome journey from saved selections to Images generation/edit, drawing, download and persisted reopen.
// [Pos] Provider/SDK/storage-injected technical E2E; does not certify real model understanding or native Responses success.
// [Sync] 2026-10-10: call actual public routes and Service; never inject completed frontend images or SSE.
// [Sync] 2026-10-11: stop via the original helper and reopen failed/cancelled image turns before an explicit retry.
// [Sync] 2026-10-11: verify the existing add-material label fits at narrow width before its actual upload operation.
import { expect, test } from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { createServer, type ViteDevServer } from 'vite';

test.use({ channel: 'chrome' });
test.setTimeout(90_000);
let child: ChildProcess, server: ViteDevServer, ownedRoot: string, url: string;
let backendLog = '';
const source = `
  import React, {useEffect,useRef,useState} from 'react'; import {createRoot} from 'react-dom/client';
  import {useChat} from '@ai-sdk/react'; import i18n from '/app/_dream/i18n.ts';
  import {loadBrowserSession,browserRequestHeaders} from '/app/_dream/lib/browserSession.ts';
  import ModelConfigSection from '/app/_dream/components/dashboard/ModelConfigSection.tsx';
  import AIInputDock from '/app/_dream/components/chat/AIInputDock.tsx';
  import {toAttachment} from '/app/_dream/components/chat/AIInputDock.helpers.ts';
  import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.tsx';
  import {ClaudeAgentChatTransport} from '/app/_dream/lib/claude-agent-transport.ts';
  import {fetchClaudeThreadMessages} from '/app/_dream/components/chat/threadSessionHydration.ts';
  import {requestClaudeThreadStop} from '/app/_dream/components/chat/threadStop.ts';
  import {WorkspaceProvider} from '/app/_dream/contexts/WorkspaceContext.tsx';
  import '/app/_dream/styles/tokens.css'; import '/app/_dream/index.css';
  await loadBrowserSession(); await i18n.changeLanguage('en');
  function Chat({thread}) {
    const pending=useRef([]); const [material,setMaterial]=useState(null);
    const {messages,sendMessage,setMessages,status,error,addToolResult}=useChat({id:thread,
      transport:new ClaudeAgentChatTransport({threadId:thread,api:'/api/claude-agent',headers:browserRequestHeaders,
        prepareSendMessagesRequest:({messages})=>({body:{thread_id:thread,id:thread,resume:true,
          message:messages.at(-1),toolChoice:'auto',allowedAppDefaultToolkit:[],allowedMcpServers:{},
          attachments:pending.current}})}),generateId:()=>crypto.randomUUID()});
    useEffect(()=>{fetchClaudeThreadMessages(thread).then(snapshot=>setMessages(snapshot.messages));},[thread]);
    return React.createElement(React.Fragment,{},
      React.createElement(ChatMessageList,{messages,threadId:thread,isLoading:status==='streaming'||status==='submitted',
        error,addToolResult,onAddImageMaterial:setMaterial}),
      React.createElement(AIInputDock,{threadId:thread,workspaceEnabled:true,workspaceSessionId:thread,mode:'full',
        imageMaterial:material,onImageMaterialConsumed:()=>setMaterial(null),loading:status==='streaming'||status==='submitted',onStop:()=>requestClaudeThreadStop(thread),onSendMessage:async(text,files=[])=>{
          pending.current=files.map(toAttachment).map(file=>({type:'file',url:file.url,storageKey:file.storageKey,
            mediaType:file.type,filename:file.name,size:file.size,workspacePath:file.workspacePath,savedAt:file.savedAt,hash:file.hash}));
          await sendMessage({text}); }}));
  }
  function Harness(){
    const [thread,setThread]=useState(new URL(location.href).searchParams.get('thread'));
    return React.createElement('main',{style:{maxWidth:760,margin:'0 auto',padding:12}},
      React.createElement('details',{open:!thread},React.createElement('summary',{},'模型设置'),React.createElement(ModelConfigSection)),
      !thread?React.createElement('button',{onClick:async()=>{
        const response=await fetch('/api/claude-agent/threads',{method:'POST',headers:{'Content-Type':'application/json',...browserRequestHeaders()},body:JSON.stringify({title:'Isolated browser image journey'})});
        const data=await response.json();const id=data.thread_id;history.replaceState(null,'','?thread='+id);setThread(id);}},'开始隔离对话'):
        React.createElement(WorkspaceProvider,{},React.createElement(Chat,{thread})));
  }
  createRoot(document.getElementById('root')).render(React.createElement(Harness));
`;

test.beforeAll(async () => {
  ownedRoot = await mkdtemp(join(tmpdir(), 'im-image-browser-20261010-'));
  const repository = fileURLToPath(new URL('../../', import.meta.url));
  child = spawn(join(repository, 'backend/.venv/bin/python'), ['-m', 'tests.serve_image_chat_journey', '--root', join(ownedRoot, 'image-chat-browser-fixture')],
    { cwd: repository, env: { ...process.env, PYTHONPATH: 'backend:.' }, stdio: ['ignore', 'pipe', 'pipe'] });
  const port = await new Promise<number>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Public fixture startup failed: '+backendLog)), 15_000);
    child.stdout!.on('data', data => { backendLog+=data.toString();const match=backendLog.match(/\{"port":\s*(\d+)\}/);if(match){clearTimeout(timer);resolve(Number(match[1]));} });
    child.stderr!.on('data', data => { backendLog+=data.toString(); });
    child.once('exit', code => { clearTimeout(timer);reject(new Error('Public fixture exit '+code+': '+backendLog)); });
  });
  server = await createServer({ root: fileURLToPath(new URL('../', import.meta.url)), configFile: false, logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true,
      proxy: { '/api': 'http://127.0.0.1:'+port, '/auth': 'http://127.0.0.1:'+port, '/_fixture': 'http://127.0.0.1:'+port } },
    plugins: [{ name:'image-public-owned-fixture',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
      if(req.url?.split('?')[0] !== '/image-journey') return next();
      res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/image-journey',
        '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/image-journey.js"></script></body></html>'));});},
      resolveId:id=>id==='/image-journey.js'?'\0image-journey.js':null,load:id=>id==='\0image-journey.js'?source:null }],
  });
  await server.listen();const address=server.httpServer!.address();
  if(!address || typeof address==='string') throw new Error('Owned Vite port unavailable');
  url='http://127.0.0.1:'+address.port+'/image-journey';
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

test('save, send, generate, preview/download, reopen, draw/send/edit and recover a file read', async ({page}, info) => {
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  // Non-business UI catalogs are isolated seams; Chat/SSE/history/files/settings are real public routers.
  await page.route('**/api/claude-agent/skill-commands**',route=>route.fulfill({json:{commands:[]}}));
  await page.route('**/plugin-load-receipt',route=>route.fulfill({json:{deck_id:null,workspace_found:false,receipt:null,launch_manifest:null}}));
  await page.route('**/subagents**',route=>route.fulfill({json:{tasks:[]}}));
  await page.goto(url);
  const imageGroup=page.getByRole('group',{name:'选择 Image 模型',exact:true});
  await imageGroup.getByRole('radio',{name:/image-second/}).check();
  await expect(page.getByText('Image 模型已保存，仅用于后续 image_gen 工具调用。')).toBeVisible();
  await page.getByRole('button',{name:'开始隔离对话'}).click();
  const input=page.getByRole('textbox',{name:'Chat input'});
  await input.fill('Use image_gen to generate a blue image');
  await page.getByRole('button',{name:'Send message',exact:true}).click();
  const images=page.locator('img[data-workspace-file-state="success"]');
  await expect(images).toHaveCount(1);
  await expect.poll(()=>images.first().evaluate((img:HTMLImageElement)=>img.naturalWidth)).toBe(8);
  await page.getByRole('button',{name:/Preview .* at full size/}).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button',{name:'Close image preview',exact:true}).click();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download image',exact:true}).first().click();
  const output=await download;await output.saveAs(info.outputPath('generated-image.png'));
  expect((await readFile(info.outputPath('generated-image.png'))).subarray(0,8).toString('hex')).toBe('89504e470d0a1a0a');
  let receipt=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(receipt.calls).toEqual([{operation:'generations',model:'image-second',input_hash:null}]);
  expect(receipt.runner_models).toEqual(['available-text']);
  await page.reload();await expect(images).toHaveCount(1);
  await page.getByRole('button',{name:'Add attachment',exact:true}).click();
  await page.getByRole('button',{name:'Draw a sketch',exact:true}).click();
  const canvas=page.locator('canvas');const bounds=await canvas.boundingBox();if(!bounds) throw new Error('Canvas missing');
  await page.mouse.move(bounds.x+bounds.width*.2,bounds.y+bounds.height*.4);await page.mouse.down();
  await page.mouse.move(bounds.x+bounds.width*.8,bounds.y+bounds.height*.6,{steps:12});await page.mouse.up();
  await page.getByRole('button',{name:'Add to message',exact:true}).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(page.getByRole('img',{name:'Sketch.png',exact:true})).toBeVisible();
  receipt=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(receipt.calls).toHaveLength(1); // Adding material did not generate or edit.
  await input.fill('Use image_gen to edit this sketch with red lines');
  await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(images).toHaveCount(2);
  receipt=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(receipt.calls[1]).toEqual({operation:'edits',model:'image-second',input_hash:receipt.upload_hashes[0]});
  expect(receipt.messages).toBe(4);
  // A normal request uses the selected AI model and the image explicitly added from history.
  await page.getByText('模型设置',{exact:true}).click();
  await page.getByRole('group',{name:'选择 AI 模型',exact:true}).getByRole('radio',{name:/available-native/}).check();
  await expect(page.getByText('模型已保存，将用于新对话。',{exact:true})).toBeVisible();
  await page.getByText('模型设置',{exact:true}).click();
  const previousViewport = page.viewportSize();
  await page.setViewportSize({ width: 375, height: 812 });
  const addMaterial = page.getByRole('button',{name:'Add to current message',exact:true}).first();
  await expect(addMaterial).toBeVisible();
  await addMaterial.scrollIntoViewIfNeeded();
  const labelLayout = await addMaterial.evaluate((button) => {
    const range = document.createRange(); range.selectNodeContents(button);
    const box = button.getBoundingClientRect();
    return { box: { left: box.left, right: box.right, top: box.top, bottom: box.bottom },
      rects: Array.from(range.getClientRects(), rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom })) };
  });
  expect(labelLayout.rects.length).toBeGreaterThan(0);
  expect(labelLayout.box.left).toBeGreaterThanOrEqual(0); expect(labelLayout.box.right).toBeLessThanOrEqual(375);
  expect(labelLayout.box.top).toBeGreaterThanOrEqual(0); expect(labelLayout.box.bottom).toBeLessThanOrEqual(812);
  for (const rect of labelLayout.rects) {
    expect(Math.abs(rect.top - labelLayout.rects[0].top)).toBeLessThanOrEqual(1);
    expect(rect.left).toBeGreaterThanOrEqual(labelLayout.box.left - 1); expect(rect.right).toBeLessThanOrEqual(labelLayout.box.right + 1);
    expect(rect.top).toBeGreaterThanOrEqual(labelLayout.box.top - 1); expect(rect.bottom).toBeLessThanOrEqual(labelLayout.box.bottom + 1);
  }
  await addMaterial.click();
  await expect(page.getByRole('img',{name:/\.png$/}).last()).toBeVisible();
  if (previousViewport) await page.setViewportSize(previousViewport);
  const beforeNative=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(beforeNative.calls).toHaveLength(2);expect(beforeNative.native_calls).toHaveLength(0);
  await input.fill('Edit this image with green lines');
  await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(images).toHaveCount(3);
  receipt=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(receipt.calls).toHaveLength(2);expect(receipt.native_calls).toHaveLength(1);
  expect(receipt.native_calls[0]).toMatchObject({operation:'edit',model:'available-native'});
  await page.reload();await expect(images).toHaveCount(3);
  await input.fill('Generate a sunset image');
  await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(images).toHaveCount(4);
  receipt=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(receipt.calls).toHaveLength(2);expect(receipt.native_calls).toHaveLength(2);
  expect(receipt.native_calls[1]).toMatchObject({operation:'generate',model:'available-native'});
  expect(receipt.messages).toBe(8);
  await input.fill('Explain what image_gen does');
  await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(page.getByText('image_gen is an explicit image tool.',{exact:true})).toBeVisible();
  receipt=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(receipt.calls).toHaveLength(2);expect(receipt.native_calls).toHaveLength(2);expect(receipt.messages).toBe(10);
  await page.request.post(new URL('/_fixture/mode',url).href,{data:{fail_image_read:true}});
  await page.reload();await expect(page.getByRole('button',{name:'Retry',exact:true})).toHaveCount(4);
  await page.request.post(new URL('/_fixture/mode',url).href,{data:{fail_image_read:false}});
  await page.getByRole('button',{name:'Retry',exact:true}).first().click();
  await expect(images).toHaveCount(1);
  for(let recovered=2;recovered<=4;recovered++){await page.getByRole('button',{name:'Retry',exact:true}).first().click();await expect(images).toHaveCount(recovered);}
  const final=await (await page.request.get(new URL('/_fixture/receipt',url).href)).json();
  expect(final.calls).toEqual(receipt.calls);expect(final.messages).toBe(10);expect(final.native_calls).toEqual(receipt.native_calls);expect(errors).toEqual([]);
  await info.attach('public-journey-receipt',{body:JSON.stringify(final,null,2),contentType:'application/json'});
  await info.attach('fixture-server-log',{body:backendLog,contentType:'text/plain'});
  await page.screenshot({path:info.outputPath('image-chat-reopened.png'),fullPage:true});
});

test('stop an image turn, reopen, recover unsupported or failed generation, and retain ordinary tool history', async ({ page }, info) => {
  await page.route('**/api/claude-agent/skill-commands**', route => route.fulfill({ json: { commands: [] } }));
  await page.route('**/plugin-load-receipt', route => route.fulfill({ json: { deck_id: null, workspace_found: false, receipt: null, launch_manifest: null } }));
  await page.route('**/subagents**', route => route.fulfill({ json: { tasks: [] } }));
  await page.goto(url);
  await page.getByRole('group', { name: '选择 AI 模型', exact: true }).getByRole('radio', { name: /available-text/ }).check();
  await page.getByRole('group', { name: '选择 Image 模型', exact: true }).getByRole('radio', { name: /image-second/ }).check();
  await page.getByRole('button', { name: '开始隔离对话' }).click();
  const input = page.getByRole('textbox', { name: 'Chat input' });
  const send = page.getByRole('button', { name: 'Send message', exact: true });
  const images = page.locator('img[data-workspace-file-state="success"]');
  const before = await (await page.request.get(new URL('/_fixture/receipt', url).href)).json();
  await page.request.post(new URL('/_fixture/mode', url).href, { data: { hold_image: true } });
  await input.fill('Use image_gen to generate a blue image');
  await send.click();
  await page.getByRole('button', { name: /^Generate image/ }).click();
  await expect(page.getByText('In progress', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Stop generating', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Stop generating', exact: true })).toHaveCount(0);
  await page.request.post(new URL('/_fixture/mode', url).href, { data: { hold_image: false } });
  await page.reload();
  // Interrupted turns retain the original direct tool row; only completed
  // projected turns have an outer process disclosure.
  await page.getByRole('button', { name: /^Generate image/ }).click();
  await expect(page.getByText('Not completed', { exact: true })).toBeVisible();
  await expect(images).toHaveCount(0);
  let receipt = await (await page.request.get(new URL('/_fixture/receipt', url).href)).json();
  expect(receipt.calls).toEqual(before.calls); expect(receipt.native_calls).toEqual(before.native_calls);
  await input.fill('Generate a sunset image');
  await send.click();
  await expect(page.getByRole('alert').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Stop generating', exact: true })).toHaveCount(0);
  receipt = await (await page.request.get(new URL('/_fixture/receipt', url).href)).json();
  expect(receipt.calls).toEqual(before.calls); expect(receipt.native_calls).toEqual(before.native_calls);
  await page.request.post(new URL('/_fixture/mode', url).href, { data: { fail_result: true } });
  await input.fill('Use image_gen to generate a blue image');
  await send.click();
  await expect(page.getByRole('alert').first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Stop generating', exact: true })).toHaveCount(0);
  await expect(images).toHaveCount(0);
  receipt = await (await page.request.get(new URL('/_fixture/receipt', url).href)).json();
  expect(receipt.calls).toHaveLength(before.calls.length + 1);
  expect(receipt.native_calls).toEqual(before.native_calls);
  await page.request.post(new URL('/_fixture/mode', url).href, { data: { fail_result: false } });
  await input.fill('Use image_gen to generate a blue image');
  await send.click();
  await expect(images).toHaveCount(1);
  await input.fill('Run the ordinary fixture tool');
  await send.click();
  await expect(page.getByText('The ordinary tool completed.', { exact: true })).toBeVisible();
  await page.reload();
  await expect(images).toHaveCount(1);
  await expect(page.getByText('The ordinary tool completed.', { exact: true })).toBeVisible();
  await expect(page.getByText('Ordinary fixture tool result', { exact: true })).toBeVisible();
  const final = await (await page.request.get(new URL('/_fixture/receipt', url).href)).json();
  expect(final.calls).toHaveLength(before.calls.length + 2); expect(final.native_calls).toEqual(before.native_calls);
  await info.attach('public-recovery-receipt', { body: JSON.stringify(final, null, 2), contentType: 'application/json' });
  await page.screenshot({ path: info.outputPath('image-chat-recovered-tool-history.png'), fullPage: true });
});
