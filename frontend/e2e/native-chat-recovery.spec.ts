// [Input] Production native Chat hook, original composer state, iOS Settings adapter and public HTTP/SSE DTOs.
// [Output] Isolated foreground/reopen/Stop/late-event/no-replay journey specifications.
// [Pos] Provider-free technical fixture; Simulator application-process and account acceptance remain separate.
// [Sync] 2026-11-02: prepared while luna-test-stage is paused; these specifications have not been executed.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../',import.meta.url));
const entry=String.raw`
import React,{useMemo,useState} from 'react';import {createRoot} from 'react-dom/client';
import {Settings} from 'react-native';
import useNativeChatThread from '/app/_dream/components/chat/useNativeChatThread.native.ts';
import useComposerDraft from '/app/_dream/components/chat/useComposerDraft.ts';
import {createNativeChatRecovery} from '/app/_dream/components/chat/nativeChatRecovery.native.ts';
import {BackendRuntimeManager} from '/src/runtime/BackendRuntimeManager.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';
const key='app04-public-service';
const read=()=>JSON.parse(sessionStorage.getItem(key)||'null')??{messages:[],running:false,calls:[]};
const save=value=>sessionStorage.setItem(key,JSON.stringify(value));
const log=(path,method,body)=>{const value=read();value.calls.push({path,method,body});save(value);};
const record={id:'app04-thread',title:'Existing conversation',deck_id:'fixture-deck',voice_id:'fixture-agent',created_at:'2026-11-02T00:00:00Z',updated_at:'2026-11-02T00:00:00Z'};
const f=window.__recoveryFixture={failReads:false,holdCreate:false,releaseCreate:null,holdCancelled:false,readers:[],expirations:0,holdPreparation:false,releasePreparation:null,abortedPreparations:0};
async function transport(input,init={}) {
 const path=String(input),method=init.method||'GET',body=init.body?JSON.parse(init.body):null;log(path,method,body);
 if(path==='/auth/session')return Response.json({user:{id:'owner-A',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
 if(method==='GET'&&f.failReads)throw new TypeError('Explicit fixture network failure');
 if(path==='/api/claude-agent/threads'&&method==='POST'){
  if(f.holdCreate)await new Promise(resolve=>f.releaseCreate=resolve);
  return Response.json({thread_id:record.id});
 }
 const value=read();
 if(path.includes('/messages'))return Response.json({thread:record,messages:value.messages,has_more:false,next_cursor:null,latest_message_id:value.messages.at(-1)?.id??null,unchanged:false});
 if(path.endsWith('/status'))return Response.json({running:value.running,lifecycle:value.running?'running':value.lifecycle??'idle',turn_count:value.messages.length?1:0,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
 if(path.endsWith('/inputs')&&method==='GET')return Response.json({entries:[],local_owner:false});
 if(path.endsWith('/stop')){
  value.running=false;value.lifecycle='idle';value.messages=[...value.messages.filter(message=>message.role==='user'),{id:'app04-reply',role:'assistant',parts:[{type:'text',text:'Saved cancelled reply'}],metadata:{turnId:'app04-turn',turnStatus:'cancelled'}}];save(value);
  return Response.json({ok:true,thread_id:record.id,stop_requested:true,running:false,lifecycle:'idle'});
 }
 throw Error('Unexpected fixture HTTP '+method+' '+path);
}
await loadBrowserSession(transport);
const frame=event=>'data: '+JSON.stringify(event)+String.fromCharCode(10,10);
async function stream(path,init={}) {
 const method=init.method||'GET',body=init.body?JSON.parse(init.body):null;log(path,method,body);
 if(f.failReads)throw new TypeError('Explicit fixture stream failure');
 if(method==='POST'){const value=read();value.messages=[...value.messages,body.message];value.running=true;save(value);}
 let release;const wait=new Promise(resolve=>release=resolve),reader={release,cancelled:false};f.readers.push(reader);
 return {status:200,cancel(){reader.cancelled=true;if(!f.holdCancelled)release();},chunks:(async function*(){
   yield frame({type:'message-metadata',turnId:'app04-turn'});
   yield frame({type:'text-delta',delta:'Live partial reply'});
   await wait;
   yield frame({type:'text-delta',delta:' STALE READER'});
   yield frame({type:'finish',finishReason:'stop'});
 })()};
}
f.complete=()=>{const value=read();value.running=false;value.lifecycle='idle';value.messages=[...value.messages.filter(message=>message.role==='user'),{id:'app04-reply',role:'assistant',parts:[{type:'text',text:'Saved completed reply'}],metadata:{turnId:'app04-turn',turnStatus:'completed'}}];save(value);};
f.loseLocalRuntime=()=>{const value=read();value.running=false;value.lifecycle='not_found';save(value);};
f.releaseReaders=()=>f.readers.forEach(reader=>reader.release());
f.readService=read;f.createRecovery=createNativeChatRecovery;f.readSettings=()=>Settings.get('ink-native-chat-recovery');
f.writeSettings=value=>Settings.set({'ink-native-chat-recovery':value});f.diagnostics=()=>BackendRuntimeManager.getSnapshot();
function Composer({recovery,session}) {
 const [restoration]=useState(()=>recovery.composer());
 const draft=useComposerDraft({onSendMessage:session.send,disabled:session.unknown,loading:session.running,onStop:session.stop,fullAccessEnabled:false,
  defaultToolChoice:restoration.initial?.toolChoice??'manual',initialDraft:restoration.initial?.query,initialFiles:restoration.initial?.uploadedFiles,onDraftChange:restoration.write,onUploadBlocked:()=>{},releasePreview:()=>{}});
 return <section><textarea aria-label="Draft" value={draft.query} onChange={event=>draft.setQuery(event.target.value)}/>
  <button onClick={draft.handleSend}>Send</button><button onClick={()=>draft.setUploadedFiles([{id:'app04-file',name:'photo.png',mimeType:'image/png',size:12,storageKey:'app04-image',workspacePath:'files/photo.png',savedAt:'2026-11-02T00:00:00Z',hash:'fixture-hash',previewUrl:'file:///temporary-handle',isUploading:false}])}>Attach uploaded file</button>
  <button onClick={()=>draft.setUploadedFiles([{id:'app04-incomplete',name:'unfinished.png',mimeType:'image/png',size:12,previewUrl:'file:///temporary-handle',isUploading:true}])}>Attach pending file</button>
  <output aria-label="Files">{JSON.stringify(draft.uploadedFiles)}</output><output aria-label="Interrupted files">{JSON.stringify(restoration.initial?.interruptedFiles??[])}</output>
 </section>;
}
function Thread({owner}) {
 const recovery=useMemo(()=>createNativeChatRecovery(owner),[owner]);const [composerKey,setComposerKey]=useState(0);
 const session=useNativeChatThread({recovery,context:{deckId:'fixture-deck',voiceId:'fixture-agent',currentToolChoice:'manual',imFullAccessEnabled:false},transport,stream,onSessionExpired:()=>f.expirations++,
  prepareEditorState:async(_id,signal)=>{if(f.holdPreparation)await new Promise((resolve,reject)=>{f.releasePreparation=resolve;signal.addEventListener('abort',()=>{f.abortedPreparations++;reject(Error('Preparation cancelled'));},{once:true});});return undefined;}});
 return <main><Composer key={composerKey} recovery={recovery} session={session}/>
 <button onClick={()=>{session.newChat();setComposerKey(value=>value+1);}}>New chat</button><button onClick={()=>void session.stop()}>Stop</button><button onClick={session.retry}>Retry read</button>
 <button onClick={()=>window.__sessionPlatform.change('background')}>Background</button><button onClick={()=>window.__sessionPlatform.change('active')}>Foreground</button>
 <output aria-label="State">{JSON.stringify({threadId:session.threadId,messages:session.messages,running:session.running,posting:session.posting,recovering:session.recovering,unknown:session.unknown,stopping:session.stopping,error:session.error})}</output></main>;
}
function Harness(){const [owner,setOwner]=useState('owner-A');return <><button onClick={()=>setOwner(value=>value==='owner-A'?'owner-B':'owner-A')}>Switch account</button><Thread key={owner} owner={owner}/></>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;

let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',define:{global:'globalThis'},cacheDir:'/tmp/ink-app04-recovery-20261102/vite',
  optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react-native-web','zod','ai']},
  resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/chat-recovery-platform-web-boundary.ts'}]},server:{host:'127.0.0.1',port:0,strictPort:true},
  plugins:[{name:'app04-native-chat-recovery',enforce:'pre',resolveId(id){if(id==='/app04-recovery.tsx')return '\0app04-recovery';},
   async load(id){if(id==='\0app04-recovery')return transformWithEsbuild(entry,'app04-recovery.tsx',{loader:'tsx',jsx:'automatic'});},
   configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/app04-recovery')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/app04-recovery','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/app04-recovery.tsx"></script></body></html>'));});},
  }]});await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('APP04_PORT_UNAVAILABLE');base='http://127.0.0.1:'+address.port+'/app04-recovery';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
 page.on('pageerror',cause=>{throw cause;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
 await page.goto(base);await expect(page.getByRole('main')).toBeVisible();
});
const state=async(page:Page)=>JSON.parse(await page.getByLabel('State',{exact:true}).innerText());
const calls=async(page:Page)=>page.evaluate(()=>(window as any).__recoveryFixture.readService().calls as {path:string;method:string;body:any}[]);
const agentPosts=async(page:Page)=>(await calls(page)).filter(call=>call.path==='/api/claude-agent'&&call.method==='POST');
async function send(page:Page){await page.getByLabel('Draft',{exact:true}).fill('One explicit submission');await page.getByRole('button',{name:'Send',exact:true}).click();await expect.poll(async()=>(await agentPosts(page)).length).toBe(1);}

test('background and failed foreground reads preserve unsent text/files and recover without writing',async({page})=>{
 await send(page);await page.getByLabel('Draft',{exact:true}).fill('Keep this unsent follow-up');await page.getByRole('button',{name:'Attach uploaded file',exact:true}).click();
 await page.getByRole('button',{name:'Background',exact:true}).click();await page.evaluate(()=>{(window as any).__recoveryFixture.failReads=true;});await page.getByRole('button',{name:'Foreground',exact:true}).click();
 await expect.poll(async()=>(await state(page)).unknown).toBe(true);await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Keep this unsent follow-up');
 await page.evaluate(()=>{const f=(window as any).__recoveryFixture;f.complete();f.failReads=false;});await page.getByRole('button',{name:'Retry read',exact:true}).click();
 await expect.poll(async()=>({running:(await state(page)).running,unknown:(await state(page)).unknown})).toEqual({running:false,unknown:false});
 expect((await state(page)).messages.at(-1).parts[0].text).toBe('Saved completed reply');expect(JSON.parse(await page.getByLabel('Files',{exact:true}).innerText())[0].storageKey).toBe('app04-image');
 expect(await agentPosts(page)).toHaveLength(1);expect((await calls(page)).filter(call=>call.path.endsWith('/stop'))).toHaveLength(0);
});
for(const running of [false,true])test('reopening reads the same '+(running?'running':'completed')+' Thread and retains the original input metadata',async({page})=>{
 await send(page);await page.getByLabel('Draft',{exact:true}).fill('Survive application recreation');await page.getByRole('button',{name:'Attach uploaded file',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__recoveryFixture.readSettings())).toContain('Survive application recreation');
 if(!running)await page.evaluate(()=>(window as any).__recoveryFixture.complete());
 await page.reload();await expect.poll(async()=>({id:(await state(page)).threadId,running:(await state(page)).running,unknown:(await state(page)).unknown})).toEqual({id:'app04-thread',running,unknown:false});
 await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Survive application recreation');
 const files=JSON.parse(await page.getByLabel('Files',{exact:true}).innerText());expect(files).toEqual([{id:'app04-file',name:'photo.png',mimeType:'image/png',size:12,storageKey:'app04-image',workspacePath:'files/photo.png',savedAt:'2026-11-02T00:00:00Z',hash:'fixture-hash'}]);
 expect(await agentPosts(page)).toHaveLength(1);expect((await calls(page)).filter(call=>call.path.endsWith('/stream')&&call.method==='GET').length).toBe(running?1:0);
 if(!running)expect((await state(page)).messages.at(-1).parts[0].text).toBe('Saved completed reply');
});
test('reopening after local runtime loss reads a user-only tail without inventing completion or replaying it',async({page})=>{
 await send(page);await page.getByLabel('Draft',{exact:true}).fill('Keep a separate unsent draft');await expect.poll(()=>page.evaluate(()=>(window as any).__recoveryFixture.readSettings())).toContain('Keep a separate unsent draft');
 await page.evaluate(()=>(window as any).__recoveryFixture.loseLocalRuntime());await page.reload();
 await expect.poll(async()=>({id:(await state(page)).threadId,running:(await state(page)).running,unknown:(await state(page)).unknown})).toEqual({id:'app04-thread',running:false,unknown:false});
 expect((await state(page)).messages.map((message:any)=>message.role)).toEqual(['user']);await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Keep a separate unsent draft');expect(await agentPosts(page)).toHaveLength(1);expect((await calls(page)).filter(call=>call.path.endsWith('/stream')&&call.method==='GET')).toHaveLength(0);
});
test('background before Thread creation completes cancels further dispatch and restores the unsent draft',async({page})=>{
 await page.evaluate(()=>{(window as any).__recoveryFixture.holdCreate=true;});await page.getByLabel('Draft',{exact:true}).fill('Keep pre-dispatch input');await page.getByRole('button',{name:'Send',exact:true}).click();
 await expect.poll(async()=>(await calls(page)).filter(call=>call.path==='/api/claude-agent/threads').length).toBe(1);
 await page.getByRole('button',{name:'Background',exact:true}).click();await page.evaluate(()=>(window as any).__recoveryFixture.releaseCreate());
 await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Keep pre-dispatch input');await page.getByRole('button',{name:'Foreground',exact:true}).click();
 expect(await agentPosts(page)).toHaveLength(0);expect((await state(page)).threadId).toBeNull();
});
test('background aborts pending context preparation before any business write',async({page})=>{
 await page.evaluate(()=>{(window as any).__recoveryFixture.holdPreparation=true;});await page.getByLabel('Draft',{exact:true}).fill('Save preparation draft');await page.getByRole('button',{name:'Send',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>Boolean((window as any).__recoveryFixture.releasePreparation))).toBe(true);await page.getByRole('button',{name:'Background',exact:true}).click();
 await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Save preparation draft');expect(await page.evaluate(()=>(window as any).__recoveryFixture.abortedPreparations)).toBe(1);expect((await calls(page)).filter(call=>call.method==='POST')).toHaveLength(0);
});
test('Stop recovers idle independently of a cancelled reader and rejects its late events',async({page})=>{
 await page.evaluate(()=>{(window as any).__recoveryFixture.holdCancelled=true;});await send(page);await page.getByRole('button',{name:'Stop',exact:true}).click();
 await expect.poll(async()=>({running:(await state(page)).running,stopping:(await state(page)).stopping})).toEqual({running:false,stopping:false});
 expect((await state(page)).messages.at(-1).parts[0].text).toBe('Saved cancelled reply');await page.evaluate(()=>(window as any).__recoveryFixture.releaseReaders());
 await expect.poll(async()=>(await state(page)).messages.at(-1).parts[0].text).toBe('Saved cancelled reply');expect(await agentPosts(page)).toHaveLength(1);expect((await calls(page)).filter(call=>call.path.endsWith('/stop'))).toHaveLength(1);
 await page.reload();await expect.poll(async()=>(await state(page)).unknown).toBe(false);expect((await state(page)).messages.at(-1).metadata.turnStatus).toBe('cancelled');expect(await agentPosts(page)).toHaveLength(1);
});
test('new Chat and account replacement retire old input writers and keep Thread recovery owner-scoped',async({page})=>{
 await send(page);await page.getByLabel('Draft',{exact:true}).fill('Owner A draft');await expect.poll(()=>page.evaluate(()=>(window as any).__recoveryFixture.readSettings())).toContain('Owner A draft');
 await page.getByRole('button',{name:'Switch account',exact:true}).click();await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('');expect((await state(page)).threadId).toBeNull();
 expect((await calls(page)).filter(call=>call.path.includes('/messages'))).toHaveLength(0);
 await page.getByLabel('Draft',{exact:true}).fill('Owner B draft');await page.getByRole('button',{name:'New chat',exact:true}).click();await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('');await page.reload();expect((await state(page)).threadId).toBeNull();
 expect(await agentPosts(page)).toHaveLength(1);expect((await calls(page)).filter(call=>call.path.endsWith('/stop'))).toHaveLength(0);
 const result=await page.evaluate(()=>{const store=(window as any).__recoveryFixture.createRecovery('isolated-owner'),old=store.composer();store.selectThread('selected-thread');old.write({query:'late draft',uploadedFiles:[],toolChoice:'manual'});return store.read();});expect(result).toEqual({threadId:'selected-thread'});
});
test('process recreation retains completed references and records interrupted files for explicit reselection',async({page})=>{
 await page.getByLabel('Draft',{exact:true}).fill('Unsent attachment draft');await page.getByRole('button',{name:'Attach pending file',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__recoveryFixture.readSettings())).toContain('unfinished.png');await page.reload();
 await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Unsent attachment draft');expect(JSON.parse(await page.getByLabel('Files',{exact:true}).innerText())).toEqual([]);expect(JSON.parse(await page.getByLabel('Interrupted files',{exact:true}).innerText())).toEqual(['unfinished.png']);expect(await agentPosts(page)).toHaveLength(0);
});

test('main and side input records remain independent under the same account',async({page})=>{
 const result=await page.evaluate(()=>{
  const create=(window as any).__recoveryFixture.createRecovery,main=create('owner-A'),side=create('owner-A','side-thread');
  main.rememberThread('main-thread');main.composer().write({query:'Main input',uploadedFiles:[],toolChoice:'manual'});
  side.composer().write({query:'Side input',uploadedFiles:[],toolChoice:'none'});
  return {main:main.read(),side:side.read()};
 });
 expect(result.main).toMatchObject({threadId:'main-thread',composer:{query:'Main input',toolChoice:'manual'}});expect(result.side).toMatchObject({threadId:'side-thread',composer:{query:'Side input',toolChoice:'none'}});expect((await calls(page)).filter(call=>call.method==='POST')).toHaveLength(0);
});

test('malformed restoration records expose fixed diagnostic categories without input JSON',async({page})=>{
 const result=await page.evaluate(()=>{
  const f=(window as any).__recoveryFixture;f.writeSettings('{"query":"private unsent text"');const json=f.createRecovery('owner-A').read();const jsonError=f.diagnostics().errors.recovery.text;
  f.writeSettings(JSON.stringify({ownerId:'owner-A',slots:{main:{threadId:null,composer:{query:'private unsent text'}}}}));const schema=f.createRecovery('owner-A').read();const schemaError=f.diagnostics().errors.recovery.text;
  return {json,schema,jsonError,schemaError};
 });
 expect(result.json).toEqual({threadId:null});expect(result.schema).toEqual({threadId:null});expect(result.jsonError).toContain('NATIVE_CHAT_RECOVERY_JSON_INVALID');expect(result.schemaError).toContain('NATIVE_CHAT_RECOVERY_SCHEMA_INVALID');expect(result.jsonError+result.schemaError).not.toContain('private unsent text');expect((await calls(page)).filter(call=>call.method==='POST')).toHaveLength(0);
});

test('Settings write failure preserves the active input and records only the fixed failure category',async({page})=>{
 await page.evaluate(()=>{(window as any).__appearanceFixture.storageFailure=true;});await page.getByLabel('Draft',{exact:true}).fill('Keep input when persistence is unavailable');
 await expect.poll(()=>page.evaluate(()=>(window as any).__recoveryFixture.diagnostics().errors?.recovery?.text??'')).toContain('NATIVE_CHAT_RECOVERY_WRITE_FAILED');await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Keep input when persistence is unavailable');expect((await calls(page)).filter(call=>call.method==='POST')).toHaveLength(0);
});

test('inactive leaves the reader intact and background suspends periodic queue reads',async({page})=>{
 await send(page);await expect.poll(()=>page.evaluate(()=>(window as any).__recoveryFixture.readers.length)).toBe(1);
 await page.evaluate(()=>(window as any).__sessionPlatform.change('inactive'));expect(await page.evaluate(()=>(window as any).__recoveryFixture.readers[0].cancelled)).toBe(false);
 await page.getByRole('button',{name:'Background',exact:true}).click();const before=(await calls(page)).filter(call=>call.path.endsWith('/inputs')).length;
 await page.waitForTimeout(2200);expect((await calls(page)).filter(call=>call.path.endsWith('/inputs'))).toHaveLength(before);
 await page.getByRole('button',{name:'Foreground',exact:true}).click();await expect.poll(async()=>(await calls(page)).filter(call=>call.path.endsWith('/inputs')).length).toBeGreaterThan(before);expect(await agentPosts(page)).toHaveLength(1);
});

test('only the primary recovery owner restores a side pointer and stale closure cannot retire its replacement',async({page})=>{
 const result=await page.evaluate(()=>{
  const create=(window as any).__recoveryFixture.createRecovery,main=create('owner-A'),side=create('owner-A','side-thread');
  main.rememberSideChat({threadId:'side-thread',writingSessionId:'original-writing'});
  const mainPointer=main.readSideChat(),sidePointer=side.readSideChat();side.rememberSideChat({threadId:'recursive-side'});
  const afterChildWrite=main.readSideChat();main.rememberSideChat({threadId:'replacement-side'});main.clearSideChat(mainPointer);const afterStaleClose=main.readSideChat();
  main.selectThread('different-main');return {mainPointer,sidePointer,afterChildWrite,afterStaleClose,afterNavigation:main.readSideChat()};
 });
 expect(result).toEqual({mainPointer:{threadId:'side-thread',writingSessionId:'original-writing'},sidePointer:null,afterChildWrite:{threadId:'side-thread',writingSessionId:'original-writing'},afterStaleClose:{threadId:'replacement-side'},afterNavigation:null});expect((await calls(page)).filter(call=>call.method==='POST')).toHaveLength(0);
});

test('Writing source recovery uses its original GET and rejects source or Thread identity changes',async({page})=>{
 const result=await page.evaluate(async()=>{
  const f=(window as any).__recoveryFixture,store=f.createRecovery('owner-A'),pointer={threadId:'writing-thread',writingSessionId:'original-writing'},requests=[];
  const valid={id:'original-writing',editor_state:{id:'original-writing',writingThreadId:'writing-thread',cells:[{id:'first-cell',content:'Private source text'}]}};
  const request=async(input,init)=>{requests.push({path:String(input),method:init?.method??'GET'});return Response.json(valid);};
  const target=await store.readWritingTarget(pointer,request),failures=[];
  for(const response of [Response.json({...valid,id:'other-source'}),Response.json({...valid,editor_state:{...valid.editor_state,id:'other-editor'}}),Response.json({...valid,editor_state:{...valid.editor_state,writingThreadId:'other-thread'}}),Response.json({detail:'Private source text'},{status:403})]){
   try{await store.readWritingTarget(pointer,async()=>response);failures.push(false);}catch{failures.push(true);}
  }
  return {target,requests,failures,stored:f.readSettings(),diagnostic:f.diagnostics().errors.recovery.text};
 });
 expect(result.target).toEqual({editorSessionId:'original-writing',cellId:'first-cell'});expect(result.requests).toEqual([{path:'/api/sessions/original-writing',method:'GET'}]);expect(result.failures).toEqual([true,true,true,true]);expect(result.stored).not.toContain('Private source text');expect(result.diagnostic).toContain('NATIVE_CHAT_WRITING_SOURCE_UNAVAILABLE');expect(result.diagnostic).not.toContain('Private source text');
});
