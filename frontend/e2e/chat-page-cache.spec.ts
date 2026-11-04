// [Sync] 2026-11-03: cover retained running readers and hidden UI publication with controlled SSE.
// [Input] Production Native Chat coordinator, message list and shared hydration with synthetic public HTTP replies.
// [Output] Reading latency/request counts, A/B/A isolation, session rejection, write refresh and retry evidence.
// [Pos] Provider-free technical harness; Project/Episode/Artifact/Hook/database/model writes remain out of scope.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {readFile} from 'node:fs/promises';

type CacheCall={path:string;query?:string;method:string;at?:number};
type CacheMessage={id:string;role:'assistant'|'user'|'system';parts:{type:'text';text:string}[];metadata?:{turnId:string;turnStatus:string}};
type CacheChannel={cancelled:boolean;cancels:number;push(event:Record<string,unknown>):void};
type CacheFixture={
 calls:CacheCall[];delay:number;fail:boolean;denied:number;hold:boolean;held:(()=>void)[];
 holdStatus:boolean;statusWaiters:(()=>void)[];scope:string;running:Record<string,boolean>;
 channels:Record<string,CacheChannel>;delivered:number;commits:number;settled:number;
 selectedAt:number;visibleAt:number;visibleReadCount:number;messages:Record<string,CacheMessage[]>;
 expiredScopes:string[];staleReplies:number;expirations:number;
 snapshot:{stopping:boolean;unknown:boolean};rotateScope():Promise<void>;push(id:string,text:string):void;finish(id:string):void;
};
declare global {interface Window {__cache:CacheFixture;__started:number}}

const baseline=process.env.INK_CHAT_CACHE_BASELINE;
const entry=`
import React,{useState,useLayoutEffect} from 'react';import {createRoot} from 'react-dom/client';
import useNativeChatThread from '/app/_dream/components/chat/useNativeChatThread.native.ts';
import ChatMessageList from '/app/_dream/components/chat/ChatMessageList.native.tsx';
import {loadBrowserSession,clearBrowserSession} from '/app/_dream/lib/browserSession.ts';
import i18n from '/app/_dream/i18n.ts';
await i18n.changeLanguage('en');
const f=window.__cache={calls:[],delay:120,fail:false,denied:0,hold:false,held:[],holdStatus:false,statusWaiters:[],scope:'a',running:{A:false,B:false},channels:{},delivered:0,commits:0,settled:0,selectedAt:0,visibleAt:0,visibleReadCount:0,expiredScopes:[],staleReplies:0,expirations:0,messages:{A:[{id:'a1',role:'assistant',parts:[{type:'text',text:'Saved answer A'}]}],B:[{id:'b1',role:'assistant',parts:[{type:'text',text:'Saved answer B'}]}]},snapshot:null};
const auth=()=>loadBrowserSession(async()=>Response.json({user:{id:f.scope==='a'?'1':'2',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:f.scope.repeat(43)}));
await auth();f.rotateScope=async()=>{f.scope='b';await auth();};
async function transport(input,init={}){
 const url=new URL(String(input),'http://fixture.invalid'),id=/threads\\/([^/]+)/.exec(url.pathname)?.[1];
 const requestScope=f.scope;
 f.calls.push({path:url.pathname,query:url.search,method:init.method||'GET',at:performance.now()});
 if(f.hold)await new Promise(resolve=>f.held.push(resolve));else await new Promise(resolve=>setTimeout(resolve,f.delay));
 if(url.pathname.endsWith('/status')&&f.holdStatus)await new Promise(resolve=>f.statusWaiters.push(resolve));
 if(f.expiredScopes.includes(requestScope)){f.staleReplies++;return new Response(null,{status:401});}
 if(f.denied)return new Response(null,{status:f.denied});
 if(f.fail)throw TypeError('Synthetic network failure');
 if(url.pathname.endsWith('/messages')){const rows=f.messages[id]||[],latest=rows.at(-1)?.id||null,unchanged=url.searchParams.get('known_latest_message_id')===latest;return Response.json({thread:{id,title:'Conversation '+id,created_at:'2026-11-03T00:00:00Z',updated_at:'2026-11-03T00:00:00Z'},messages:unchanged?[]:rows,latest_message_id:latest,has_more:id==='A',next_cursor:id==='A'?'older-A':null,unchanged});}
 if(url.pathname.endsWith('/stop')){f.finish(id);return Response.json({ok:true,thread_id:id,stop_requested:true,running:false,lifecycle:'idle'});}
 if(url.pathname.endsWith('/status'))return Response.json({running:Boolean(f.running[id]),lifecycle:f.running[id]?'running':'idle',turn_count:1,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
 if(url.pathname.endsWith('/inputs'))return Response.json({entries:[],local_owner:false});
 throw Error('Unexpected cache fixture request '+url.pathname);
}
async function stream(input){
 const id=/threads\\/([^/]+)/.exec(String(input))?.[1];if(!id)throw Error('Unexpected model dispatch');
 f.calls.push({path:String(input),method:'GET'});const channel={queue:[],wait:null,cancelled:false,cancels:0};f.channels[id]=channel;
 const enqueue=event=>{channel.queue.push('data: '+JSON.stringify(event)+String.fromCharCode(10,10));channel.wait?.();channel.wait=null;};
 channel.push=enqueue;enqueue({type:'message-metadata',turnId:'turn-'+id});
 return {status:200,cancel(){channel.cancels++;channel.cancelled=true;channel.wait?.();},chunks:(async function*(){while(!channel.cancelled){if(!channel.queue.length)await new Promise(resolve=>channel.wait=resolve);if(channel.cancelled)return;const chunk=channel.queue.shift();if(chunk){yield chunk;f.delivered++;}}})()};
}
f.push=(id,text)=>f.channels[id].push({type:'text-delta',delta:text});
f.finish=id=>{f.running[id]=false;f.messages[id]=[{id:'final-'+id,role:'assistant',parts:[{type:'text',text:'Completed answer '+id}],metadata:{turnId:'turn-'+id,turnStatus:'completed'}}];f.channels[id].push({type:'finish',finishReason:'stop'});};
function Harness(){const [section,setSection]=useState('chat');const h=useNativeChatThread({context:{},transport,stream,visible:section==='chat',onSettled:()=>{f.settled++;},onSessionExpired:()=>{f.expirations++;}});f.snapshot=h;
 useLayoutEffect(()=>{f.commits++;});
 useLayoutEffect(()=>{if(f.selectedAt&&!f.visibleAt&&h.messages.some(row=>row.parts.some(part=>part.type==='text'&&part.text==='Saved answer A'))){f.visibleAt=performance.now();f.visibleReadCount=f.calls.filter(row=>!row.path.endsWith('/inputs')).length;}},[h.messages]);
 return <><button onClick={()=>{f.selectedAt=performance.now();void h.openThread('A');}}>Open A</button><button onClick={()=>void h.openThread('B')}>Open B</button><button onClick={()=>h.newChat()}>Home</button>
 <button onClick={()=>setSection(value=>value==='chat'?'more':'chat')}>Switch page</button>
 <button onClick={()=>{h.invalidateHistory?.('A');f.messages.A=[...f.messages.A,{id:'a2',role:'assistant',parts:[{type:'text',text:'New saved answer A'}]}];}}>Business update</button>
 <button onClick={()=>void h.stop()}>Stop current</button><button onClick={()=>void h.retry()}>Retry read</button><button onClick={async()=>{clearBrowserSession();f.scope='b';f.messages.A=[{id:'other-a',role:'assistant',parts:[{type:'text',text:'Other account answer'}]}];await auth();h.newChat();}}>Switch account</button>
 <div hidden={section!=='chat'}><button disabled={h.unknown||h.recovering}>Send</button><ChatMessageList messages={h.messages} threadId={h.threadId||''} isLoading={false} initialLoading={h.recovering}/></div>
 <output aria-label="Cache state">{JSON.stringify({id:h.threadId,unknown:h.unknown,recovering:h.recovering,nextCursor:h.nextCursor,hasMore:h.hasMore,error:h.error,confirmation:h.confirmation})}</output></>;
}
createRoot(document.getElementById('root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',server:{host:'127.0.0.1',port:0},plugins:[{
  name:'chat-cache-production',enforce:'pre',resolveId(id){if(id==='react-native')return '\0cache-native';if(id==='/cache-entry.tsx')return '\0cache-entry';},
  async load(id){if(baseline && /\/(useNativeChatThread\.native|threadSessionHydration)\.ts$/.test(id))return readFile(baseline+'/'+id.split('/').at(-1),'utf8');
   if(id==='\0cache-native')return `export * from 'react-native-web';export const NativeModules={InkRuntime:{}};export const AppState={currentState:'active',addEventListener(){return {remove(){}}}};`;
   if(id==='\0cache-entry')return transformWithEsbuild(entry,'cache-entry.tsx',{loader:'tsx',jsx:'automatic'});
  },configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/cache')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/cache','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/cache-entry.tsx"></script></body></html>'));});}
 }]});await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('CACHE_PORT');base='http://127.0.0.1:'+address.port+'/cache';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{page.on('pageerror',cause=>{throw cause;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.goto(base);await expect(page.getByRole('button',{name:'Open A',exact:true})).toBeVisible();});
async function state(page:Page){return JSON.parse(await page.getByLabel('Cache state',{exact:true}).innerText());}
async function idle(page:Page){await expect.poll(async()=>(await state(page)).recovering).toBe(false);}

test('first visible answer and reopening request evidence',async({page},testInfo)=>{
 await page.evaluate(()=>{window.__started=performance.now();});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();
 const first=await page.evaluate(()=>({visibleMs:window.__cache.visibleAt-window.__cache.selectedAt,callsAtVisibleCommit:window.__cache.visibleReadCount}));
 if(!baseline){expect((await state(page)).recovering).toBe(true);await expect(page.getByRole('button',{name:'Send',exact:true})).toBeDisabled();}
 await idle(page);const count=await page.evaluate(()=>window.__cache.calls.length);
 await page.getByRole('button',{name:'Open A',exact:true}).click();
 if(!baseline){await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();expect(await page.evaluate(()=>window.__cache.calls.length)).toBe(count);}
 else await idle(page);
 const evidence={lane:'synthetic HTTP, 120ms per phase',baseline:Boolean(baseline),first,reopenAdditionalRequests:await page.evaluate(()=>window.__cache.calls.length)-count};
 console.log('CHAT_CACHE_METRICS '+JSON.stringify(evidence));await testInfo.attach('cache-metrics.json',{body:JSON.stringify(evidence),contentType:'application/json'});
});

test('A B A shows only the target prose while current state is checked and preserves pagination',async({page})=>{
 test.skip(Boolean(baseline));
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await page.getByRole('button',{name:'Open B',exact:true}).click();await idle(page);await expect(page.getByText('Saved answer B',{exact:true})).toBeVisible();
 await page.evaluate(()=>{window.__cache.hold=true;});await page.getByRole('button',{name:'Open A',exact:true}).click();
 await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();await expect(page.getByText('Saved answer B',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Send',exact:true})).toBeDisabled();expect((await state(page)).confirmation).toBeNull();
 const request=await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path==='/api/claude-agent/threads/A/messages').at(-1));expect(request?.query).toContain('known_latest_message_id=a1');
 await page.evaluate(()=>{const f=window.__cache;f.hold=false;f.held.splice(0).forEach((resolve:()=>void)=>resolve());});await idle(page);
 expect(await state(page)).toMatchObject({nextCursor:'older-A',hasMore:true,unknown:false});
});

test('page navigation retains the active reader and a saved mutation refreshes the reopened Thread',async({page})=>{
 test.skip(Boolean(baseline));
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);const count=await page.evaluate(()=>window.__cache.calls.length);
 await page.getByRole('button',{name:'Switch page',exact:true}).click();await page.getByRole('button',{name:'Switch page',exact:true}).click();await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();expect(await page.evaluate(()=>window.__cache.calls.length)).toBe(count);
 await page.getByRole('button',{name:'Business update',exact:true}).click();await page.getByRole('button',{name:'Home',exact:true}).click();await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);await expect(page.getByText('New saved answer A',{exact:true})).toBeVisible();
});

test('network failure retains prose, retry reconciles it, and permission loss removes it',async({page})=>{
 test.skip(Boolean(baseline));
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);await page.getByRole('button',{name:'Home',exact:true}).click();await page.evaluate(()=>{window.__cache.fail=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();await expect.poll(async()=>(await state(page)).error).toBeTruthy();await expect(page.getByRole('button',{name:'Send',exact:true})).toBeDisabled();
 await page.evaluate(()=>{window.__cache.fail=false;});await page.getByRole('button',{name:'Retry read',exact:true}).click();await idle(page);expect((await state(page)).unknown).toBe(false);
 await page.evaluate(()=>{window.__cache.denied=403;});await page.getByRole('button',{name:'Retry read',exact:true}).click();await expect(page.getByText('Saved answer A',{exact:true})).toHaveCount(0);
});

test('a changed login session cannot reuse the earlier account preview',async({page})=>{
 test.skip(Boolean(baseline));
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);await page.getByRole('button',{name:'Switch account',exact:true}).click();await page.evaluate(()=>{window.__cache.hold=true;});await page.getByRole('button',{name:'Open A',exact:true}).click();await expect(page.getByText('Saved answer A',{exact:true})).toHaveCount(0);
 await page.evaluate(()=>{const f=window.__cache;f.hold=false;f.held.splice(0).forEach((resolve:()=>void)=>resolve());});await idle(page);await expect(page.getByText('Other account answer',{exact:true})).toBeVisible();
});


test('the final reconciled page replaces prose removed after the first history read',async({page})=>{
 test.skip(Boolean(baseline));
 await page.evaluate(()=>{window.__cache.holdStatus=true;});await page.getByRole('button',{name:'Open A',exact:true}).click();
 await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();await expect.poll(()=>page.evaluate(()=>window.__cache.statusWaiters.length)).toBe(1);
 await page.evaluate(()=>{const f=window.__cache;f.messages.A=[];f.holdStatus=false;f.statusWaiters.splice(0).forEach((resolve:()=>void)=>resolve());});
 await idle(page);await expect(page.getByText('Saved answer A',{exact:true})).toHaveCount(0);
});


test('session replacement during reconciliation clears the old preview and retries without a stalled loader',async({page})=>{
 test.skip(Boolean(baseline));
 await page.evaluate(()=>{window.__cache.holdStatus=true;});await page.getByRole('button',{name:'Open A',exact:true}).click();
 await expect(page.getByText('Saved answer A',{exact:true})).toBeVisible();await expect.poll(()=>page.evaluate(()=>window.__cache.statusWaiters.length)).toBe(1);
 await page.evaluate(async()=>{const f=window.__cache;await f.rotateScope();f.messages.A=[{id:'rotated-a',role:'assistant',parts:[{type:'text',text:'Rotated session answer'}]}];f.holdStatus=false;f.statusWaiters.splice(0).forEach((resolve:()=>void)=>resolve());});
 await expect(page.getByText('Rotated session answer',{exact:true})).toBeVisible();await idle(page);
 expect((await state(page)).unknown).toBe(false);await expect(page.getByText('Saved answer A',{exact:true})).toHaveCount(0);
});

test('running Thread keeps its reader while a hidden page pauses UI publication',async({page})=>{
 await page.evaluate(()=>{window.__cache.running.A=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.A))).toBe(true);
 await page.getByRole('button',{name:'Switch page',exact:true}).click();
 const before=await page.evaluate(()=>({commits:window.__cache.commits,delivered:window.__cache.delivered,calls:window.__cache.calls.filter((row)=>!row.path.endsWith('/inputs')).length}));
 await page.evaluate(()=>{window.__cache.push('A',' + hidden live A');});
 await expect.poll(()=>page.evaluate(()=>window.__cache.delivered)).toBeGreaterThan(before.delivered);
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 expect(await page.evaluate(()=>window.__cache.commits)).toBe(before.commits);
 expect(await page.evaluate(()=>window.__cache.channels.A.cancels)).toBe(0);
 await page.getByRole('button',{name:'Switch page',exact:true}).click();
 await expect(page.getByText('Saved answer A + hidden live A',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>window.__cache.calls.filter((row)=>!row.path.endsWith('/inputs')).length)).toBe(before.calls);
});

test('A B A restores a running Thread without closing or reopening its stream',async({page})=>{
 await page.evaluate(()=>{window.__cache.running.A=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.A))).toBe(true);
 await page.getByRole('button',{name:'Open B',exact:true}).click();await idle(page);
 await expect(page.getByText('Saved answer B',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>window.__cache.channels.A.cancels)).toBe(0);
 const before=await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path.includes('/threads/A/')&&!row.path.endsWith('/inputs')).length);
 await page.evaluate(()=>{window.__cache.push('A',' + retained A');});
 await page.getByRole('button',{name:'Open A',exact:true}).click();
 await expect(page.getByText('Saved answer A + retained A',{exact:true})).toBeVisible();
 expect((await state(page)).recovering).toBe(false);
 expect(await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path.includes('/threads/A/')&&!row.path.endsWith('/inputs')).length)).toBe(before);
 expect(await page.evaluate(()=>window.__cache.channels.A.cancels)).toBe(0);
});

test('two running Threads remain separate and Stop only targets the visible Thread',async({page})=>{
 await page.evaluate(()=>{const f=window.__cache;f.running.A=true;f.running.B=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.A))).toBe(true);
 await page.getByRole('button',{name:'Open B',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.B))).toBe(true);
 await page.evaluate(()=>{const f=window.__cache;f.push('A',' + separate A');f.push('B',' + separate B');});
 await expect(page.getByText('Saved answer B + separate B',{exact:true})).toBeVisible();
 await expect(page.getByText('Saved answer A + separate A',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Stop current',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>window.__cache.snapshot.stopping)).toBe(false);
 await expect(page.getByText('Completed answer B',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>window.__cache.channels.A.cancels)).toBe(0);
 expect(await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path.endsWith('/stop')).map((row)=>row.path))).toEqual(['/api/claude-agent/threads/B/stop']);
 await page.getByRole('button',{name:'Open A',exact:true}).click();
 await expect(page.getByText('Saved answer A + separate A',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path==='/api/claude-agent/threads/A/stream').length)).toBe(1);
});

test('a completed background Thread releases its reader and reopens persisted final history',async({page})=>{
 await page.evaluate(()=>{window.__cache.running.A=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.A))).toBe(true);
 await page.getByRole('button',{name:'Open B',exact:true}).click();await idle(page);
 const settled=await page.evaluate(()=>window.__cache.settled);
 await page.evaluate(()=>{window.__cache.finish('A');});
 await expect.poll(()=>page.evaluate(()=>window.__cache.settled)).toBeGreaterThan(settled);
 await expect(page.getByText('Saved answer B',{exact:true})).toBeVisible();
 const before=await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path==='/api/claude-agent/threads/A/messages').length);
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect(page.getByText('Completed answer A',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path==='/api/claude-agent/threads/A/messages').length)).toBeGreaterThan(before);
 expect(await page.evaluate(()=>window.__cache.calls.filter((row)=>row.path==='/api/claude-agent/threads/A/stream').length)).toBe(1);
});

test('session replacement releases background readers before another account opens the same Thread',async({page})=>{
 await page.evaluate(()=>{window.__cache.running.A=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.A))).toBe(true);
 await page.getByRole('button',{name:'Open B',exact:true}).click();await idle(page);
 await page.evaluate(()=>{window.__cache.running.A=false;});
 await page.getByRole('button',{name:'Switch account',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>window.__cache.channels.A.cancelled)).toBe(true);
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect(page.getByText('Other account answer',{exact:true})).toBeVisible();
 await expect(page.getByText('Saved answer A',{exact:true})).toHaveCount(0);
 expect(await page.evaluate(()=>window.__cache.calls.some((row)=>row.path.endsWith('/stop')))).toBe(false);
});

test('a late 401 from a retired background Thread cannot expire the new login session',async({page})=>{
 await page.evaluate(()=>{window.__cache.running.A=true;});
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__cache.channels.A))).toBe(true);
 await page.getByRole('button',{name:'Open B',exact:true}).click();await idle(page);
 const reads=await page.evaluate(()=>window.__cache.calls.filter(row=>row.path==='/api/claude-agent/threads/A/messages').length);
 await page.evaluate(()=>{const f=window.__cache;f.hold=true;f.finish('A');});
 await expect.poll(()=>page.evaluate(()=>window.__cache.calls.filter(row=>row.path==='/api/claude-agent/threads/A/messages').length)).toBeGreaterThan(reads);
 await page.getByRole('button',{name:'Switch account',exact:true}).click();
 await page.evaluate(()=>{const f=window.__cache;f.expiredScopes=['a'];f.hold=false;f.held.splice(0).forEach(resolve=>resolve());});
 await expect.poll(()=>page.evaluate(()=>window.__cache.staleReplies)).toBeGreaterThan(0);
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 expect(await page.evaluate(()=>window.__cache.expirations)).toBe(0);
 expect((await state(page)).unknown).toBe(false);
 await page.getByRole('button',{name:'Open A',exact:true}).click();await idle(page);
 await expect(page.getByText('Other account answer',{exact:true})).toBeVisible();
 await expect(page.getByText('Completed answer A',{exact:true})).toHaveCount(0);
});
