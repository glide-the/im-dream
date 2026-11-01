// [Sync] 2026-10-31: retain delayed cancelled readers while qualifying independent acknowledged Stop recovery and late-reader ownership.
// [Sync] 2026-10-31: qualify saved user-only tail recovery with not_found and an unchanged empty probe without replay or invented assistant output.
// [Sync] 2026-10-30: cover original multi-part MCP user ingress and verified live process retention across compact canonical recovery.
// [Sync] 2026-10-30: distinguish an acknowledged native read cancellation from an unacknowledged network failure during recovery.
// [Sync] 2026-10-30: cover long native Markdown output, exact persisted text and the original Stop receipt without a provider.
// [Sync] 2026-10-28: bind Native icon geometry with vendor Web renderer in the isolated RNW harness; assert actual 16px menu icons.
// [Sync] 2026-10-28: hold replacement receipts across AppState changes and reject old selection recovery, using the actual Native adapter.
// [Input] Production native Chat hook and public HTTP/SSE contracts with synthetic transport boundaries.
// [Output] Provider-free submission, queue, confirmation, Stop and navigation receipts from the actual lifecycle adapter.
// [Pos] Explicit technical harness; no native runtime startup, account, database or model calls.
// [Sync] 2026-10-28: exercise the production native queue card, revision actions, recovery draft and side-task receipts.
// [Sync] 2026-10-28: cover canonical finish before HTTP EOF and preserve server-owned running state through recovery.
// [Sync] 2026-10-28: verify HTTP/stream 401 notifications and preserve normal-login/no-resubmission boundaries.
import {expect,test} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {createServer as netServer} from 'node:net';
const entry=`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import {AppState} from 'react-native';
Object.defineProperty(AppState,'currentState',{value:'active',writable:true,configurable:true});
AppState.listeners=new Set();AppState.addEventListener=(_,fn)=>{AppState.listeners.add(fn);return {remove:()=>AppState.listeners.delete(fn)};};
import useNativeChatThread from '/app/_dream/components/chat/useNativeChatThread.native.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';
import '/app/_dream/i18n.ts';
import QueueCard from '/app/_dream/components/chat/ThreadInputQueueCard.native.tsx';
import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.native.tsx';
import {isThreadInputQueueCard} from '/app/_dream/components/chat/threadInputQueue.ts';
const f=window.__nativeChatFixture={calls:[],mode:'complete',messages:[],queue:[],running:false,cancels:0,release:null,resolveStop:null,holdStop:false,expired:false,expiredStream:false,expirations:0,failQueue:false,conflict:false,owner:true,selected:false,interrupt:true,sideLaunchFailed:false,openedSide:null,holdSelect:false,releaseSelect:null,holdQueue:false,releaseQueue:null,editsSettled:0,holdRecovery:false,recoveryWaiters:[],stopped:false,stopStillRunning:false};
const record={id:'fixture-thread',title:'Existing conversation',deck_id:'fixture-deck',voice_id:'fixture-agent',created_at:'2026-10-28T00:00:00Z',updated_at:'2026-10-28T00:00:00Z'};
const status=()=>f.statusOverride??({running:f.running,lifecycle:f.running?'running':'idle',turn_count:f.messages.length?1:0,pending_tool_call_ids:f.mode==='approval'&&f.running?['fixture-tool']:[],tool_confirmation_observation:'known'});
async function transport(input,init={}) {
 const path=String(input),method=init.method||'GET',body=init.body?JSON.parse(init.body):null;f.calls.push({path,method,body,headers:Object.fromEntries(new Headers(init.headers))});
 if(f.expired)return new Response(null,{status:401});
 if(path==='/auth/session')return Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
 if(path==='/api/claude-agent/threads' && method==='POST')return Response.json({thread_id:'fixture-thread'});
 if(path.includes('/messages')){
   if(f.holdRecovery&&f.stopped)await new Promise(resolve=>f.recoveryWaiters.push(resolve));
   const latest=f.messages.at(-1)?.id||null;
   if(f.stableEmptyProbe&&new URL(path,'http://fixture.invalid').searchParams.get('known_latest_message_id')===latest){
     f.emptyProbeReads++;
     return Response.json({thread:record,messages:[],has_more:false,next_cursor:null,latest_message_id:latest,unchanged:true});
   }
   return Response.json({thread:record,messages:f.messages,has_more:false,next_cursor:null,latest_message_id:latest,unchanged:false});
 }
 if(path.endsWith('/status'))return Response.json(status());
 if(path.endsWith('/stop')){
   const reply=()=>{f.running=f.stopStillRunning;f.stopped=true;if(['native-cancel','native-cancel-late'].includes(f.mode))f.messages=[...f.messages,{id:'fixture-cancelled',role:'assistant',parts:[{type:'text',text:'Visible reply'}],metadata:{turnId:'fixture-turn',turnStatus:'cancelled'},created_at:'2026-10-28T00:00:00Z'}];return Response.json({ok:true,thread_id:'fixture-thread',stop_requested:true,running:f.running,lifecycle:f.running?'running':'idle'});};
   return f.holdStop?new Promise(resolve=>{f.resolveStop=()=>resolve(reply());}):reply();
 }
 if(path==='/api/claude-agent/tool-confirm'){f.running=false;f.release?.();return Response.json({ok:true,approved:body.approved});}
 if(path.endsWith('/inputs') && method==='POST'){
   const reply=()=>{
     if(f.failQueue)return Response.json({detail:{error_code:'CHAT_INPUT_UNAVAILABLE'}},{status:503});
     const item={message_id:body.message.id,thread_id:'fixture-thread',queue_sequence:'1',status:'queued',revision:1,dispatch_turn_id:null,created_at:'2026-10-28T00:00:00Z',text:body.message.parts[0].text};f.queue.push(item);return Response.json(item);
   };
   return f.holdQueue?new Promise(resolve=>{f.releaseQueue=()=>resolve(reply());}):reply();
 }
 const action=new RegExp('/inputs/([^/]+)/(select|cancel|side-task)$').exec(path);
 if(action){
   const finish=()=>{
     if(f.conflict)return Response.json({detail:{error_code:'CHAT_INPUT_STATE_CHANGED'}},{status:409});
     const item=f.queue.find(row=>row.message_id===decodeURIComponent(action[1]));
     if(!item||item.revision!==body.expected_revision)return Response.json({detail:{error_code:'CHAT_INPUT_STATE_CHANGED'}},{status:409});
     item.revision++;item.status=action[2]==='select'?'selected':'cancelled';
     if(action[2]==='select')return Response.json({entry:item,interrupt_signalled:f.interrupt});
     if(action[2]==='side-task')return Response.json({task_id:'fixture-side-task',thread_id:'fixture-side-thread',launch_status:f.sideLaunchFailed?'failed':'started',dispatch_started:!f.sideLaunchFailed,...(f.sideLaunchFailed?{error_code:'SIDE_LAUNCH_FAILED'}:{})});
     return Response.json(item);
   };
   return f.holdSelect&&action[2]==='select'?new Promise(resolve=>{f.releaseSelect=()=>resolve(finish());}):finish();
 }
 if(path.endsWith('/inputs'))return Response.json({entries:f.queue,local_owner:f.owner});
 throw new Error('Unexpected fixture HTTP '+method+' '+path);
}
await loadBrowserSession(transport);
const frame=event=>'data: '+JSON.stringify(event)+String.fromCharCode(10,10);
async function stream(path,init={}) {
 const body=init.body?JSON.parse(init.body):null;f.calls.push({path,method:init.method||'GET',body,headers:Object.fromEntries(new Headers(init.headers))});
 if(f.expiredStream)return {status:401,cancel(){f.cancels++;},chunks:(async function*(){})()};
 if(init.method==='POST'){f.messages=[body.message];f.running=true;}
 let released=false,cancelled=false,release;const wait=new Promise(resolve=>{release=()=>{released=true;resolve();};});f.release=release;
 const reply=f.mode==='burst-hold'?'A quiet autumn sea. '.repeat(900):'Visible reply';
 return {status:200,cancel(){f.cancels++;cancelled=true;if(f.mode!=='native-cancel-late')release();},chunks:(async function*(){
   yield frame({type:'message-metadata',turnId:'fixture-turn'});
   if(f.mode==='mcp-complete'){
     const output={content:[{type:'text',text:'Original App result'}]};
     yield frame({type:'tool-input-available',toolCallId:'fixture-app-call',toolName:'mcp__fixture__show',input:{}});
     yield frame({type:'tool-output-available',toolCallId:'fixture-app-call',output,mcpAppResult:{version:1,serverRef:'fixture',toolName:'show',toolCallId:'fixture-app-call',input:{},workspaceScope:null,resourceUri:'ui://fixture/form.html',result:output}});
   }
   if(f.mode==='approval')yield frame({type:'tool-approval-request',toolCallId:'fixture-tool',toolName:'Read',input:{file_path:'notes.txt'}});
   else if(f.mode==='burst-hold')yield Array.from(reply,char=>frame({type:'text-delta',id:'fixture-long-part',delta:char})).join('');
   else yield frame({type:'text-delta',delta:reply});
   if(f.mode==='native-disconnect'){f.stopped=true;throw new Error('HTTP_FAILED');}
   if(f.mode==='finish-running' && init.method==='POST'){yield frame({type:'finish',finishReason:'stop'});return;}
   if(!['complete','finish-open','mcp-complete'].includes(f.mode) && !released)await wait;
   if(['native-cancel','native-cancel-late'].includes(f.mode)&&cancelled){f.cancelledReaderFinished=true;throw new Error('HTTP_CANCELLED');}
   f.running=false;if(!(f.mode==='native-cancel'&&f.stopped))f.messages=[...f.messages,{id:'fixture-assistant',role:'assistant',parts:[{type:'text',text:reply}],metadata:{turnId:'fixture-turn',turnStatus:'completed',...(f.mode==='mcp-complete'?{historyProjectionVersion:1,historyProcessAvailable:true,finalPartIndex:1}:{})},created_at:'2026-10-28T00:00:00Z'}];
   yield frame({type:'finish',finishReason:'stop'});
   if(f.mode==='finish-open' && !released)await wait;
 })()};
}
function Harness(){
 const [draft,setDraft]=useState(''),[notice,setNotice]=useState(''),[mode,setMode]=useState('complete');
 const session=useNativeChatThread({context:{deckId:'fixture-deck',voiceId:'fixture-agent',voiceSystemPrompt:'Original voice prompt',imFullAccessEnabled:false,currentToolChoice:'manual'},transport,stream,onSessionExpired:()=>{f.expirations++;}});
 return <main><textarea aria-label="Draft" value={draft} onChange={e=>setDraft(e.target.value)}/>
  <select aria-label="Fixture stream mode" value={mode} onChange={e=>{setMode(e.target.value);f.mode=e.target.value;}}>{['complete','finish-open','finish-running','hold','approval','burst-hold','native-cancel','native-cancel-late','native-disconnect','mcp-complete'].map(value=><option key={value}>{value}</option>)}</select>
  <button onClick={()=>void session.send(draft,[],'manual').then(()=>setNotice('sent')).catch(()=>setNotice('rejected'))}>Send</button>
  <button onClick={()=>void session.send('',[{id:'fixture-file',name:'picture.png',mimeType:'image/png',size:12,storageKey:'fixture-image',workspacePath:'files/picture.png',savedAt:'2026-10-28T00:00:00Z',hash:'fixture-hash'}],'manual')}>Send stored attachment</button>
  <button onClick={()=>void session.sendUserMessage({role:'user',parts:[{type:'text',text:'First MCP block'},{type:'text',text:'Second MCP block'}]}).then(()=>setNotice('MCP sent')).catch(()=>setNotice('MCP rejected'))}>Send MCP message</button>
  <button onClick={()=>void session.stop()}>Stop</button><button onClick={()=>session.newChat()}>New chat</button>
  <button onClick={()=>void session.openThread('fixture-thread')}>Open existing thread</button><button onClick={()=>f.release?.()}>Release stream</button><button onClick={()=>{f.holdStop=true;}}>Delay Stop receipt</button><button onClick={()=>f.resolveStop?.()}>Release Stop receipt</button>
  <button onClick={()=>{f.stopStillRunning=true;}}>Keep task running after Stop</button><button onClick={()=>{f.holdRecovery=true;}}>Hold recovery reads</button><button onClick={()=>{f.holdRecovery=false;f.recoveryWaiters.splice(0).forEach(resolve=>resolve());}}>Release recovery reads</button>
  <button onClick={()=>void session.confirm(false,'User rejected the tool execution')}>Reject tool</button>
  <button onClick={()=>{AppState.currentState='background';AppState.listeners.forEach(fn=>fn('background'));}}>Background</button>
  <button onClick={()=>{AppState.currentState='active';AppState.listeners.forEach(fn=>fn('active'));}}>Foreground</button>
  <button onClick={()=>{f.expired=true;}}>Expire HTTP session</button><button onClick={()=>{f.expiredStream=true;}}>Expire stream session</button>
  <output aria-label="State">{JSON.stringify({id:session.threadId,running:session.running,posting:session.posting,recovering:session.recovering,unknown:session.unknown,error:session.error,stopping:session.stopping,editRetrying:session.editRetrying,confirmation:session.confirmation?.kind ?? null,queue:session.queue,queueError:session.queueError,editDraftRecovery:session.editDraftRecovery,messages:session.messages})}</output>
  <output aria-label="Notice">{notice}</output>
  {mode==='burst-hold'?<div style={{height:400}}><ChatMessageList messages={session.messages} threadId={session.threadId??''} isLoading={session.running}/></div>:null}
  <div aria-label="Queue controls">{session.queue.filter(isThreadInputQueueCard).map(item=><QueueCard key={item.message_id} entry={item} localOwner={session.localOwner} onGuide={session.guide} onCancel={session.cancelInput} onEdit={async(entry,text)=>{try{await session.editInput(entry,text);}finally{f.editsSettled++;}}} onSideChat={async entry=>{const task=await session.sideTask(entry);f.openedSide=task;}}/>)}</div>
  {session.queueError?<div role="alert">{session.queueError}</div>:null}
  {session.editDraftRecovery?<div role="status" aria-label="Edited draft recovery"><span>{session.editDraftRecovery.text}</span><button disabled={session.editRetrying} onClick={()=>void session.retryEditedInput()}>Retry edited draft</button></div>:null}
  <button onClick={()=>void session.checkQueue()}>Check queue status</button>
  </main>;
}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  const port=await new Promise<number>((resolve,reject)=>{const probe=netServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{const address=probe.address();if(!address || typeof address==='string')return reject(new Error('Port'));probe.close(error=>error?reject(error):resolve(address.port));});});
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-edit-lifecycle-vite-cache-20261028',optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','ai','zod','react-i18next','i18next','react-markdown','remark-gfm']},resolve:{alias:[{find:/^react-native$/,replacement:'react-native-web'},{find:/^react-native-svg$/,replacement:fileURLToPath(new URL('../node_modules/react-native-svg/lib/module/elements.web.js',import.meta.url))}],extensions:['.web.mjs','.mjs','.web.js','.js','.mts','.ts','.jsx','.tsx','.json']},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{
    name:'native-chat-production-hook',enforce:'pre',resolveId(id,importer){if(id==='./Icons'&&importer?.includes('/components/chat/'))return fileURLToPath(new URL('../app/_dream/components/chat/Icons.native.tsx',import.meta.url));if(id==='/native-chat.tsx')return '\0native-chat-entry';},
    async load(id){if(id==='\0native-chat-entry')return transformWithEsbuild(entry,'native-chat.tsx',{loader:'tsx',jsx:'automatic'});},
    configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-chat')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-chat','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/native-chat.tsx"></script></body></html>'));});},
  }]});await server.listen();base='http://127.0.0.1:'+port+'/native-chat';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
  page.on('pageerror',error=>{throw error;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
  await page.addInitScript(()=>localStorage.setItem('ink-language','en'));
  await page.goto(base);await expect(page.getByRole('main')).toBeVisible();
});
async function state(page:import('@playwright/test').Page){return JSON.parse(await page.getByLabel('State',{exact:true}).innerText());}
test('actual native session submits the original context/manual DTO and recovers persisted output',async({page})=>{
  await page.getByLabel('Draft',{exact:true}).fill('Keep existing business');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>({running:(await state(page)).running,posting:(await state(page)).posting})).toEqual({running:false,posting:false});
  await expect(page.getByLabel('Notice',{exact:true})).toHaveText('sent');
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  const create=calls.find((call:any)=>call.path==='/api/claude-agent/threads' && call.method==='POST');
  expect(create.body).toEqual({deckId:'fixture-deck',voiceId:'fixture-agent'});
  const send=calls.find((call:any)=>call.path==='/api/claude-agent' && call.method==='POST');
  expect(send.body).toMatchObject({id:'fixture-thread',deckId:'fixture-deck',voiceId:'fixture-agent',resume:true,toolChoice:'manual',systemPrompt:'Original voice prompt',attachments:[]});
  expect(send.headers['x-ink-csrf']).toHaveLength(43);expect(send.headers.authorization).toBeUndefined();
  expect((await state(page)).messages.at(-1).parts[0].text).toBe('Visible reply');
});
test('canonical finish reconciles persisted state while the HTTP connection remains open',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('finish-open');
  await page.getByLabel('Draft',{exact:true}).fill('Complete this response');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>({running:(await state(page)).running,posting:(await state(page)).posting,unknown:(await state(page)).unknown})).toEqual({running:false,posting:false,unknown:false});
  await expect(page.getByLabel('Notice',{exact:true})).toHaveText('sent');
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
  expect(calls.some((call:any)=>call.path.endsWith('/stop'))).toBe(false);
  expect(calls.some((call:any)=>call.path.endsWith('/status'))).toBe(true);
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.cancels)).toBeGreaterThan(0);
});
test('canonical finish recovers the server-owned running task without another business POST',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('finish-running');
  await page.getByLabel('Draft',{exact:true}).fill('Keep the current task');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.calls.some((call:any)=>call.path.endsWith('/stream')))).toBe(true);
  expect((await state(page)).running).toBe(true);
  expect((await state(page)).posting).toBe(false);
  expect((await state(page)).unknown).toBe(false);
  await page.getByRole('button',{name:'Release stream',exact:true}).click();
  await expect.poll(async()=>({running:(await state(page)).running,posting:(await state(page)).posting})).toEqual({running:false,posting:false});
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
  expect(calls.some((call:any)=>call.path.endsWith('/stop'))).toBe(false);
});
test('a draft during an active POST uses the original queue endpoint and its stable receipt',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('hold');await page.getByLabel('Draft',{exact:true}).fill('First request');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).running).toBe(true);
  await page.getByLabel('Draft',{exact:true}).fill('Follow-up while running');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).queue.length).toBe(1);
  expect((await state(page)).queue[0]).toMatchObject({text:'Follow-up while running',status:'queued'});
  const posts=await page.evaluate(()=>(window as any).__nativeChatFixture.calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST').length);expect(posts).toBe(1);
  await page.getByRole('button',{name:'Release stream',exact:true}).click();
});
test('stored attachment-only input keeps the original file parts and workspace metadata',async({page})=>{
  await page.getByRole('button',{name:'Send stored attachment'}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.calls.some((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST'))).toBe(true);
  const call=await page.evaluate(()=>(window as any).__nativeChatFixture.calls.find((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST'));
  expect(call.body.message.parts).toEqual([{type:'file',url:'/api/storage/file/Zml4dHVyZS1pbWFnZQ==',mediaType:'image/png',filename:'picture.png'}]);
  expect(call.body.attachments).toEqual([{type:'file',url:'/api/storage/file/Zml4dHVyZS1pbWFnZQ==',storageKey:'fixture-image',mediaType:'image/png',filename:'picture.png',size:12,workspacePath:'files/picture.png',savedAt:'2026-10-28T00:00:00Z',hash:'fixture-hash'}]);
  await expect.poll(async()=>(await state(page)).running).toBe(false);
});
test('Stop retains the local stream until the canonical receipt allows cancellation',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('hold');await page.getByLabel('Draft',{exact:true}).fill('Stop this request');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).running).toBe(true);await page.getByRole('button',{name:'Delay Stop receipt'}).click();await page.getByRole('button',{name:'Stop',exact:true}).click();
  await expect.poll(async()=>(await state(page)).stopping).toBe(true);expect(await page.evaluate(()=>(window as any).__nativeChatFixture.cancels)).toBe(0);
  await page.getByRole('button',{name:'Release Stop receipt'}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.cancels)).toBeGreaterThan(0);
  await expect.poll(async()=>(await state(page)).running).toBe(false);
});
test('long native Markdown retains exact text and Stop settles through the original endpoint',async({page})=>{
  const expected='A quiet autumn sea. '.repeat(900);
  await page.getByLabel('Fixture stream mode').selectOption('burst-hold');
  await page.getByLabel('Draft',{exact:true}).fill('Continue the autumn journal');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).messages.at(-1)?.parts.find((part:any)=>part.type==='text')?.text).toBe(expected);
  await expect(page.getByRole('button',{name:'Copy',exact:true})).toHaveCount(1);
  await page.getByRole('button',{name:'Stop',exact:true}).click();
  await expect.poll(async()=>({running:(await state(page)).running,posting:(await state(page)).posting,unknown:(await state(page)).unknown})).toEqual({running:false,posting:false,unknown:false});
  expect((await state(page)).messages.at(-1).parts.find((part:any)=>part.type==='text').text).toBe(expected);
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
  expect(calls.filter((call:any)=>call.path.endsWith('/stop'))).toHaveLength(1);
  expect(calls.some((call:any)=>call.path.endsWith('/status'))).toBe(true);
});
test('acknowledged Stop recovers from a native cancelled reader without an unknown-outcome error',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('native-cancel');
  await page.getByLabel('Draft',{exact:true}).fill('Stop the current reply');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).messages.at(-1)?.parts[0]?.text).toBe('Visible reply');
  await page.getByRole('button',{name:'Hold recovery reads',exact:true}).click();
  await page.getByRole('button',{name:'Stop',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.recoveryWaiters.length)).toBeGreaterThan(0);
  expect((await state(page)).error).toBeNull();
  expect((await state(page)).unknown).toBe(false);
  await page.getByRole('button',{name:'Release recovery reads',exact:true}).click();
  await expect.poll(async()=>({running:(await state(page)).running,posting:(await state(page)).posting,error:(await state(page)).error})).toEqual({running:false,posting:false,error:null});
  expect((await state(page)).messages.at(-1).metadata.turnStatus).toBe('cancelled');
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
  expect(calls.filter((call:any)=>call.path.endsWith('/stop'))).toHaveLength(1);
});
test('acknowledged Stop recovers before a delayed cancelled reader finishes',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('native-cancel-late');
  await page.getByLabel('Draft',{exact:true}).fill('Stop without waiting for the old connection');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).messages.at(-1)?.parts[0]?.text).toBe('Visible reply');
  await page.getByRole('button',{name:'Stop',exact:true}).click();
  await expect.poll(async()=>({running:(await state(page)).running,posting:(await state(page)).posting,stopping:(await state(page)).stopping,unknown:(await state(page)).unknown})).toEqual({running:false,posting:false,stopping:false,unknown:false});
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.cancelledReaderFinished===true)).toBe(false);
  expect((await state(page)).messages.at(-1).metadata.turnStatus).toBe('cancelled');
  await page.getByRole('button',{name:'Release stream',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.cancelledReaderFinished===true)).toBe(true);
  expect((await state(page)).error).toBeNull();
  expect((await state(page)).running).toBe(false);
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
  expect(calls.filter((call:any)=>call.path.endsWith('/stop'))).toHaveLength(1);
  expect(calls.some((call:any)=>call.path.endsWith('/status'))).toBe(true);
});
test('an unacknowledged native stream failure retains unknown-outcome protection',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('native-disconnect');
  await page.getByRole('button',{name:'Hold recovery reads',exact:true}).click();
  await page.getByLabel('Draft',{exact:true}).fill('Keep the current request');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>({unknown:(await state(page)).unknown,error:(await state(page)).error})).toEqual({unknown:true,error:'chat.inputQueue.stateUnknown'});
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
  expect(calls.some((call:any)=>call.path.endsWith('/stop'))).toBe(false);
  await page.getByRole('button',{name:'Release recovery reads',exact:true}).click();
});
test('an acknowledged Stop remains stopping until the original task reports idle',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('native-cancel');
  await page.getByRole('button',{name:'Keep task running after Stop',exact:true}).click();
  await page.getByLabel('Draft',{exact:true}).fill('Wait for the current task to stop');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).messages.length).toBe(2);
  await page.getByRole('button',{name:'Stop',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.calls.some((call:any)=>call.path.endsWith('/stream')))).toBe(true);
  expect((await state(page)).stopping).toBe(true);
  expect((await state(page)).error).toBeNull();
  await page.getByRole('button',{name:'Send',exact:true}).click();
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST').length)).toBe(1);
  await page.getByRole('button',{name:'Release stream',exact:true}).click();
  await expect.poll(async()=>({stopping:(await state(page)).stopping,running:(await state(page)).running,error:(await state(page)).error})).toEqual({stopping:false,running:false,error:null});
  expect((await state(page)).messages.at(-1).metadata.turnStatus).toBe('cancelled');
});
test('backend approval remains manual and rejects through the owned canonical endpoint',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('approval');await page.getByLabel('Draft',{exact:true}).fill('Read the selected note');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).confirmation).toBe('confirm');
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.calls.some((call:any)=>call.path==='/api/claude-agent/tool-confirm'))).toBe(false);
  await page.getByRole('button',{name:'Reject tool'}).click();await expect.poll(async()=>(await state(page)).confirmation).toBe(null);
  const call=await page.evaluate(()=>(window as any).__nativeChatFixture.calls.find((call:any)=>call.path==='/api/claude-agent/tool-confirm'));
  expect(call.body).toMatchObject({thread_id:'fixture-thread',tool_call_id:'fixture-tool',approved:false});
});
test('new-chat navigation cancels only the old reader and rejects late message updates',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('hold');await page.getByLabel('Draft',{exact:true}).fill('Old conversation');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).messages.length).toBeGreaterThan(1);await page.getByRole('button',{name:'New chat',exact:true}).click();
  await expect.poll(async()=>({id:(await state(page)).id,messages:(await state(page)).messages})).toEqual({id:null,messages:[]});
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.calls.some((call:any)=>call.path.endsWith('/stop')))).toBe(false);
});
test('background releases only the reader and foreground restores the same persisted Thread without another POST',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('hold');await page.getByLabel('Draft',{exact:true}).fill('Continue after foreground');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).messages.length).toBeGreaterThan(1);await page.getByRole('button',{name:'Background',exact:true}).click();
  await expect.poll(async()=>(await state(page)).unknown).toBe(true);await page.getByRole('button',{name:'Foreground',exact:true}).click();
  await expect.poll(async()=>({id:(await state(page)).id,unknown:(await state(page)).unknown})).toEqual({id:'fixture-thread',unknown:false});
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent' && call.method==='POST')).toHaveLength(1);
  expect(calls.some((call:any)=>call.path.endsWith('/stop'))).toBe(false);
  expect(calls.some((call:any)=>call.path.includes('/messages'))).toBe(true);
});
for(const boundary of ['HTTP','stream'])test(`401 at the ${boundary} boundary requests normal session refresh without resubmitting business`,async({page})=>{
  await page.getByRole('button',{name:`Expire ${boundary} session`,exact:true}).click();
  await page.getByLabel('Draft',{exact:true}).fill('Preserve normal login');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.expirations)).toBe(1);
  await expect(page.getByLabel('Notice',{exact:true})).toHaveText('rejected');
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(boundary==='HTTP'?0:1);
  expect(calls.some((call:any)=>call.path.endsWith('/stop')||call.path.includes('/oauth/device'))).toBe(false);
  expect((await state(page)).unknown).toBe(false);
});

async function queuedCard(page:import('@playwright/test').Page){
  await page.getByLabel('Fixture stream mode').selectOption('hold');
  await page.getByLabel('Draft',{exact:true}).fill('Main task');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect.poll(async()=>(await state(page)).running).toBe(true);
  await page.getByLabel('Draft',{exact:true}).fill('Original queued draft');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByTestId('thread-input-queue-card')).toBeVisible();
  return page.getByTestId('thread-input-queue-card');
}
test('native queued edit preserves original revision cancellation, context and independent main POST',async({page})=>{
  const card=await queuedCard(page);await card.getByRole('button',{name:'More options'}).click();await page.getByRole('menuitem',{name:'Edit message'}).click();
  await page.getByRole('textbox',{name:'Edit message'}).fill('Edited queued draft');await page.getByRole('button',{name:'Save',exact:true}).click();
  await expect(card.getByText('Edited queued draft',{exact:true})).toBeVisible();
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls),cancellation=calls.find((call:any)=>call.path.endsWith('/cancel'));
  expect(cancellation.body).toEqual({expected_revision:1});
  const posts=calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST');expect(posts).toHaveLength(2);
  expect(posts[1].body).toMatchObject({deckId:'fixture-deck',voiceId:'fixture-agent',toolChoice:'manual',message:{parts:[{type:'text',text:'Edited queued draft'}]}});
  expect(posts[1].body.message.id).not.toBe(posts[0].body.message.id);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
});
test('failed native edit retains the draft and retry reuses the exact original replacement message ID',async({page})=>{
  const card=await queuedCard(page);await card.getByRole('button',{name:'More options'}).click();await page.getByRole('menuitem',{name:'Edit message'}).click();
  await page.getByRole('textbox',{name:'Edit message'}).fill('Keep this edited draft');await page.evaluate(()=>(window as any).__nativeChatFixture.failQueue=true);
  await page.getByRole('button',{name:'Save',exact:true}).click();await expect(page.getByRole('status',{name:'Edited draft recovery'})).toContainText('Keep this edited draft');await expect(page.getByRole('alert')).toHaveText('chat.inputQueue.unavailable');
  await expect(page.getByTestId('thread-input-queue-card')).toHaveCount(0);
  const failed=await page.evaluate(()=>(window as any).__nativeChatFixture.calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST').at(-1).body.message.id);
  await page.evaluate(()=>(window as any).__nativeChatFixture.failQueue=false);await page.getByRole('button',{name:'Retry edited draft'}).click();
  await expect(page.getByTestId('thread-input-queue-card').getByText('Keep this edited draft',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Retry edited draft'})).toHaveCount(0);
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST').at(-1).body.message.id).toBe(failed);
  expect(calls.filter((call:any)=>call.path.endsWith('/cancel'))).toHaveLength(1);
});
test('native queue revision conflict retains the original card and reads status without replacement submission',async({page})=>{
  const card=await queuedCard(page);await page.evaluate(()=>(window as any).__nativeChatFixture.conflict=true);
  await card.getByRole('button',{name:'Remove queued message'}).click();await expect(page.getByRole('alert')).toHaveText('chat.inputQueue.stateChanged');
  await expect(card.getByText('Original queued draft',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Check queue status'}).click();await expect(page.getByRole('alert')).toHaveCount(0);
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST').length)).toBe(1);
});
test('native side-chat transfer returns the owned receipt and launch failure while the main task remains running',async({page})=>{
  const card=await queuedCard(page);await page.evaluate(()=>(window as any).__nativeChatFixture.sideLaunchFailed=true);
  await card.getByRole('button',{name:'More options'}).click();await page.getByRole('menuitem',{name:'Open in side chat'}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.openedSide?.thread_id)).toBe('fixture-side-thread');
  await expect(page.getByRole('alert')).toHaveText('chat.inputQueue.sideChatLaunchFailed');
  expect((await state(page)).id).toBe('fixture-thread');expect((await state(page)).running).toBe(true);
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.find((call:any)=>call.path.endsWith('/side-task')).body).toEqual({expected_revision:1});
  expect(calls.some((call:any)=>call.path.endsWith('/stop'))).toBe(false);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
});
test('native queue retains owner and selected permissions while an unconfirmed interrupt shows the original error',async({page})=>{
  const card=await queuedCard(page);await page.evaluate(()=>(window as any).__nativeChatFixture.owner=false);await page.getByRole('button',{name:'Check queue status'}).click();
  await expect(card.getByRole('button',{name:'Adjust direction'})).toBeDisabled();await card.getByRole('button',{name:'More options'}).click();
  await expect(page.getByRole('menuitem',{name:'Edit message'})).toBeDisabled();await expect(page.getByRole('menuitem',{name:'Open in side chat'})).toBeEnabled();
  await page.keyboard.press('Escape');await page.evaluate(()=>{const f=(window as any).__nativeChatFixture;f.owner=true;f.interrupt=false;});await page.getByRole('button',{name:'Check queue status'}).click();
  await card.getByRole('button',{name:'Adjust direction'}).click();await expect(page.getByRole('alert')).toHaveText('chat.inputQueue.guideFailed');
  await expect(card.getByRole('button',{name:'Adjust direction'})).toBeDisabled();await expect(card.getByRole('button',{name:'Remove queued message'})).toBeDisabled();
});
test('late queue actions cannot overwrite a newly opened native conversation',async({page})=>{
  const card=await queuedCard(page);await page.evaluate(()=>(window as any).__nativeChatFixture.holdSelect=true);await card.getByRole('button',{name:'Adjust direction'}).click();
  await expect(card.getByRole('button',{name:'Adjust direction'})).toBeDisabled();await page.getByRole('button',{name:'New chat',exact:true}).click();
  await page.evaluate(()=>(window as any).__nativeChatFixture.releaseSelect());
  await expect.poll(async()=>({id:(await state(page)).id,queue:(await state(page)).queue,queueError:(await state(page)).queueError})).toEqual({id:null,queue:[],queueError:null});
});
test('native queue menu stays inside the narrow viewport after the card controls wrap',async({page})=>{
  await page.setViewportSize({width:390,height:640});const card=await queuedCard(page);
  await card.getByRole('button',{name:'More options'}).click();const menu=page.getByRole('menu',{name:'More options'});await expect(menu).toBeVisible();
  const iconBoxes=await menu.locator('svg').evaluateAll(nodes=>nodes.map(node=>({width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height})));expect(iconBoxes).toHaveLength(3);for(const icon of iconBoxes){expect(icon.width).toBe(16);expect(icon.height).toBe(16);}
  const box=await menu.boundingBox();expect(box).not.toBeNull();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(390);expect(box!.y).toBeGreaterThanOrEqual(0);expect(box!.y+box!.height).toBeLessThanOrEqual(640);
  await page.setViewportSize({width:640,height:390});await expect(menu).toHaveCount(0);
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.calls.some((call:any)=>call.path.endsWith('/side-task')||call.path.endsWith('/cancel')||call.path.endsWith('/select')))).toBe(false);
});

for(const settleAfterForeground of [false,true])test(`queued edit failure survives ${settleAfterForeground?'background and foreground':'background'} reader replacement`,async({page})=>{
  const card=await queuedCard(page);
  await card.getByRole('button',{name:'More options'}).click();await page.getByRole('menuitem',{name:'Edit message'}).click();
  await page.getByRole('textbox',{name:'Edit message'}).fill('Keep my background edit');
  await page.evaluate(()=>{const f=(window as any).__nativeChatFixture;f.holdQueue=true;f.failQueue=true;});
  await page.getByRole('button',{name:'Save',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>typeof (window as any).__nativeChatFixture.releaseQueue)).toBe('function');
  await page.getByRole('button',{name:'Background',exact:true}).click();
  if(settleAfterForeground)await page.getByRole('button',{name:'Foreground',exact:true}).click();
  await page.evaluate(()=>(window as any).__nativeChatFixture.releaseQueue());
  await expect(page.getByRole('status',{name:'Edited draft recovery'})).toContainText('Keep my background edit');
  if(!settleAfterForeground)await page.getByRole('button',{name:'Foreground',exact:true}).click();
  const failed=await page.evaluate(()=>(window as any).__nativeChatFixture.calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST').at(-1).body.message.id);
  await page.evaluate(()=>{const f=(window as any).__nativeChatFixture;f.holdQueue=false;f.failQueue=false;});
  await page.getByRole('button',{name:'Retry edited draft'}).click();
  await expect(page.getByTestId('thread-input-queue-card').getByText('Keep my background edit',{exact:true})).toBeVisible();
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST').at(-1).body.message.id).toBe(failed);
  expect(calls.filter((call:any)=>call.path.endsWith('/cancel'))).toHaveLength(1);
  expect(calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST')).toHaveLength(1);
});
test('an old edit failure cannot restore a draft after leaving and reopening the same Thread',async({page})=>{
  const card=await queuedCard(page);await card.getByRole('button',{name:'More options'}).click();await page.getByRole('menuitem',{name:'Edit message'}).click();
  await page.getByRole('textbox',{name:'Edit message'}).fill('Old selection edited draft');
  await page.evaluate(()=>{const f=(window as any).__nativeChatFixture;f.holdQueue=true;f.failQueue=true;});
  await page.getByRole('button',{name:'Save',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>typeof (window as any).__nativeChatFixture.releaseQueue)).toBe('function');
  await page.getByRole('button',{name:'New chat',exact:true}).click();
  await page.getByRole('button',{name:'Open existing thread',exact:true}).click();
  await expect.poll(async()=>(await state(page)).id).toBe('fixture-thread');
  await page.evaluate(()=>(window as any).__nativeChatFixture.releaseQueue());
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeChatFixture.editsSettled)).toBe(1);
  expect((await state(page)).editDraftRecovery).toBeNull();
  await expect(page.getByRole('status',{name:'Edited draft recovery'})).toHaveCount(0);
});

for(const failRetry of [false,true])test(`edited-draft retry releases pending across background on ${failRetry?'failure':'success'}`,async({page})=>{
  const card=await queuedCard(page);await card.getByRole('button',{name:'More options'}).click();await page.getByRole('menuitem',{name:'Edit message'}).click();
  await page.getByRole('textbox',{name:'Edit message'}).fill('Retry my edited draft');
  await page.evaluate(()=>(window as any).__nativeChatFixture.failQueue=true);await page.getByRole('button',{name:'Save',exact:true}).click();
  await expect(page.getByRole('status',{name:'Edited draft recovery'})).toBeVisible();
  const replacementId=(await state(page)).editDraftRecovery.id;
  await page.evaluate(failRetry=>{const f=(window as any).__nativeChatFixture;f.holdQueue=true;f.failQueue=failRetry;},failRetry);
  await page.getByRole('button',{name:'Retry edited draft'}).click();
  await expect.poll(()=>page.evaluate(()=>typeof (window as any).__nativeChatFixture.releaseQueue)).toBe('function');
  await expect.poll(async()=>(await state(page)).editRetrying).toBe(true);
  await page.getByRole('button',{name:'Background',exact:true}).click();
  await page.evaluate(()=>(window as any).__nativeChatFixture.releaseQueue());
  await expect.poll(async()=>(await state(page)).editRetrying).toBe(false);
  if(failRetry){
    await expect(page.getByRole('status',{name:'Edited draft recovery'})).toContainText('Retry my edited draft');
    expect((await state(page)).editDraftRecovery.id).toBe(replacementId);
    await page.getByRole('button',{name:'Foreground',exact:true}).click();
    await page.evaluate(()=>{const f=(window as any).__nativeChatFixture;f.holdQueue=false;f.failQueue=false;});
    await page.getByRole('button',{name:'Retry edited draft'}).click();
  }else await page.getByRole('button',{name:'Foreground',exact:true}).click();
  await expect(page.getByRole('status',{name:'Edited draft recovery'})).toHaveCount(0);
  await expect(page.getByTestId('thread-input-queue-card').getByText('Retry my edited draft',{exact:true})).toBeVisible();
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  const replacements=calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST').slice(1);
  expect(replacements.every((call:any)=>call.body.message.id===replacementId)).toBe(true);
  expect(calls.filter((call:any)=>call.path.endsWith('/cancel'))).toHaveLength(1);
});


test('MCP App ingress preserves both original text parts in one canonical POST',async({page})=>{
  await page.getByRole('button',{name:'Send MCP message',exact:true}).click();await expect(page.getByLabel('Notice',{exact:true})).toHaveText('MCP sent');
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls),posts=calls.filter((call:any)=>call.path==='/api/claude-agent'&&call.method==='POST');expect(posts).toHaveLength(1);
  expect(posts[0].body.message.parts).toEqual([{type:'text',text:'First MCP block'},{type:'text',text:'Second MCP block'}]);expect(posts[0].body.toolChoice).toBe('auto');expect(calls.filter((call:any)=>call.path.endsWith('/inputs')&&call.method==='POST')).toHaveLength(0);
});
test('canonical final-only recovery retains the live MCP App result using the original verified-process merge',async({page})=>{
  await page.getByLabel('Fixture stream mode').selectOption('mcp-complete');await page.getByLabel('Draft',{exact:true}).fill('Show the connected App');await page.getByRole('button',{name:'Send',exact:true}).click();await expect(page.getByLabel('Notice',{exact:true})).toHaveText('sent');
  const message=(await state(page)).messages.at(-1);expect(message.id).toBe('fixture-assistant');expect(message.parts).toHaveLength(2);expect(message.parts[0]).toMatchObject({type:'dynamic-tool',toolCallId:'fixture-app-call',state:'output-available',toolMetadata:{mcpAppResult:{resourceUri:'ui://fixture/form.html'}}});expect(message.metadata.historyProjectionVersion).toBeUndefined();
});

test('saved user-only tail recovers with no running owner without replay or invented output',async({page})=>{
  await page.getByLabel('Draft',{exact:true}).fill('Keep this unsent draft');
  await page.evaluate(()=>{
    const fixture=(window as any).__nativeChatFixture;
    fixture.messages=Array.from({length:4},(_,index)=>[
      {id:`saved-user-${index}`,role:'user',parts:[{type:'text',text:`Saved request ${index}`} ]},
      {id:`saved-assistant-${index}`,role:'assistant',parts:[{type:'text',text:`Saved answer ${index}`}],metadata:{turnStatus:'completed'}},
    ]).flat();
    fixture.messages.push({id:'saved-unanswered-user',role:'user',parts:[{type:'text',text:'Saved request before the process exited'}]});
    fixture.statusOverride={running:false,lifecycle:'not_found',turn_count:0,pending_tool_call_ids:[],tool_confirmation_observation:'known'};
    fixture.stableEmptyProbe=true;fixture.emptyProbeReads=0;
  });
  await page.getByRole('button',{name:'Open existing thread',exact:true}).click();
  await expect.poll(async()=>{
    const snapshot=await state(page);
    return {id:snapshot.id,recovering:snapshot.recovering,running:snapshot.running,unknown:snapshot.unknown};
  }).toEqual({id:'fixture-thread',recovering:false,running:false,unknown:false});
  const snapshot=await state(page);
  expect(snapshot.messages).toHaveLength(9);
  expect(snapshot.messages.filter((message:any)=>message.role==='assistant')).toHaveLength(4);
  expect(snapshot.messages.at(-1)).toMatchObject({id:'saved-unanswered-user',role:'user',parts:[{type:'text',text:'Saved request before the process exited'}]});
  expect(snapshot.error).toBeNull();
  await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Keep this unsent draft');
  expect(await page.evaluate(()=>(window as any).__nativeChatFixture.emptyProbeReads)).toBe(1);
  const calls=await page.evaluate(()=>(window as any).__nativeChatFixture.calls);
  expect(calls.filter((call:any)=>call.method==='POST')).toHaveLength(0);
  expect(calls.filter((call:any)=>call.path.endsWith('/stream'))).toHaveLength(0);
});
