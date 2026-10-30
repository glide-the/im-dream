// [Input] Production Native activity/detail components, original shared coordinators/APIs and explicit HTTP/AppState fixtures.
// [Output] Read-only activity, source-local retry, exact Thread navigation and foreground/stale-response contracts.
// [Pos] Provider-free browser harness; all accounts, tasks and HTTP receipts are synthetic, no backend/model/database execution.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
const entry=`
import React,{useEffect,useState} from 'react';import {createRoot} from 'react-dom/client';
import {AppState} from 'react-native';
import ActivitySidebar,{nativeActivityFilters} from '/app/_dream/components/chat/ActivitySidebar.native.tsx';
import ScheduledTaskDetailSidebar from '/app/_dream/components/chat/ScheduledTaskDetailSidebar.native.tsx';
import ChatHistorySearch from '/app/_dream/components/chat/ChatHistorySearch.native.tsx';
import useNativeActivitySidebarData from '/app/_dream/components/chat/useNativeActivitySidebarData.native.ts';
import useNativeChatHistory from '/app/_dream/components/chat/useNativeChatHistory.native.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
Object.defineProperty(AppState,'currentState',{value:'active',writable:true,configurable:true});AppState.listeners=new Set();AppState.addEventListener=(_,fn)=>{AppState.listeners.add(fn);return {remove:()=>AppState.listeners.delete(fn)};};
await i18n.changeLanguage('en');
await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const at=Date.now(),iso=(offset=0)=>new Date(at+offset).toISOString();
const task={id:'fixture-task',source_thread_id:'fixture-source',title:'Daily fixture task',prompt:'Keep the existing schedule',rule:{kind:'daily',local_time:'09:00',time_zone:'Asia/Shanghai'},run_thread_mode:'new_thread_each_run',model_alias:'fixture-model',next_run_at:iso(86400000),status:'active',revision:3,created_at:iso(-100000),updated_at:iso(-1000)};
const trigger={id:'fixture-trigger',task_id:task.id,kind:'scheduled',scheduled_at:iso(-10000),definition_revision:3,title:task.title,source_thread_id:task.source_thread_id,time_zone:'Asia/Shanghai',status:'running',task_session_id:null,target_thread_id:'fixture-execution',input_message_id:null,target_turn_id:null,final_message_id:null,error_code:null,run_thread_mode_snapshot:'new_thread_each_run',model_alias_snapshot:'fixture-model',skipped_from_at:null,skipped_through_at:null,created_at:iso(-10000),updated_at:iso(-1000)};
const f=window.__activityFixture={calls:[],failDay:false,failDetail:false,holdDay:false,held:[],dayTitle:'Daily fixture task',expired:false,expirations:0,selected:null,mounts:0,snapshot:null,rows:Array.from({length:24},(_,i)=>({id:'fixture-chat-'+i,title:'Existing Chat '+i,created_at:iso(-i*1000-1000),updated_at:iso(-i*1000-1000)}))};
async function transport(input,init={}){
 const path=String(input),url=new URL(path,'http://fixture.invalid'),method=init.method||'GET';f.calls.push({path,method,headers:Object.fromEntries(new Headers(init.headers)),signal:init.signal});
 if(f.expired)return new Response(null,{status:401});
 if(url.pathname==='/api/claude-agent/threads'){
  if(method!=='GET')throw Error('UNEXPECTED_TASK_MUTATION');const query=url.searchParams.get('query'),offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||100);
  const rows=query?f.rows.filter(row=>row.title.includes(query)).map(row=>({...row,match:{strategy:'fuzzy',score:1,fields:['title'],excerpt:'Matching '+query}})):f.rows;
  return Response.json({threads:rows.slice(offset,offset+limit)});
 }
 if(url.pathname==='/api/claude-agent/scheduled-tasks/day'){
  const reply=()=>f.failDay?new Response(null,{status:503}):Response.json({tasks:[{...task,title:f.dayTitle}],triggers:[trigger]});
  if(f.holdDay){const captured=reply();return new Promise(resolve=>f.held.push({signal:init.signal,release:()=>resolve(captured)}));}return reply();
 }
 if(url.pathname==='/api/claude-agent/scheduled-tasks/'+task.id)return f.failDetail?new Response(null,{status:503}):Response.json({task});
 if(url.pathname==='/api/claude-agent/scheduled-tasks/'+task.id+'/history')return Response.json({triggers:[trigger,{...trigger,id:'fixture-reuse',target_thread_id:task.source_thread_id}]});
 throw Error('UNEXPECTED_FIXTURE_HTTP '+method+' '+path);
}
function Source(){const [draft,setDraft]=useState('Existing unsent draft');useEffect(()=>{f.mounts++;},[]);return <textarea aria-label="Source draft" value={draft} onChange={event=>setDraft(event.target.value)}/>;}
function Harness(){
 const [open,setOpen]=useState(false),[detail,setDetail]=useState(null),[filters,setFilters]=useState(nativeActivityFilters);
 const h=useNativeChatHistory({enabled:open,transport,onSessionExpired:()=>f.expirations++}),a=useNativeActivitySidebarData(open,{transport,onSessionExpired:()=>f.expirations++});
 f.snapshot={open,active:a.active,chatCount:a.chat.data.length,scheduledTitle:a.scheduled.data?.tasks?.[0]?.title,chatError:Boolean(a.chat.error),scheduledError:Boolean(a.scheduled.error),detail:detail?.taskId,filters,historyCount:h.threads.length};
 const select=id=>{f.selected=id;setOpen(false);setDetail(null);};
 return <div style={{height:'100vh',display:'flex',flexDirection:'column'}}>
  <div><button onClick={()=>setOpen(true)}>Open activity</button><button onClick={()=>{AppState.currentState='background';AppState.listeners.forEach(fn=>fn('background'));}}>Background</button><button onClick={()=>{AppState.currentState='active';AppState.listeners.forEach(fn=>fn('active'));}}>Foreground</button><Source/></div>
  <div style={{flex:1,minHeight:0,position:'relative'}}>
   {open?<ActivitySidebar activity={a} history={h} activeThreadId="fixture-chat-0" filters={filters} onFiltersChange={setFilters} onClose={()=>setOpen(false)} onSelectThread={select} onDeleteThread={()=>{throw Error('UNEXPECTED_DELETE');}} onTask={row=>{setOpen(false);setDetail({taskId:row.id,snapshot:row.snapshot});}}/>:null}
   {detail?<ScheduledTaskDetailSidebar {...detail} transport={transport} onClose={()=>setDetail(null)} onOpenThread={select}/>:null}
   <ChatHistorySearch history={h} activeThreadId="fixture-chat-0" onSelect={select}/>
  </div>
 </div>;
}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  const port=await new Promise<number>((resolve,reject)=>{const s=netServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const a=s.address();if(!a||typeof a==='string')return reject(Error('PORT'));s.close(error=>error?reject(error):resolve(a.port));});});
  const root=fileURLToPath(new URL('../',import.meta.url));
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-activity-vite-cache-20261028',optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','i18next','react-i18next']},resolve:{alias:[{find:/^react-native$/,replacement:'react-native-web'},{find:/^react-native-svg$/,replacement:root+'node_modules/react-native-svg/lib/module/elements.web.js'}]},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'native-activity-production',enforce:'pre',resolveId(id,importer){if(id==='./Icons'&&importer?.includes('/components/chat/'))return root+'app/_dream/components/chat/Icons.native.tsx';if(id==='/activity-entry.tsx')return '\0activity-entry';},async load(id){if(id==='\0activity-entry')return transformWithEsbuild(entry,'activity-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-activity')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-activity','<html><head><link rel="icon" href="data:,"><style>body{margin:0}#root{height:100vh}</style></head><body><div id="root"></div><script type="module" src="/activity-entry.tsx"></script></body></html>'));});}}]});await server.listen();base='http://127.0.0.1:'+port+'/native-activity';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{page.on('pageerror',error=>{throw error;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.goto(base);await expect(page.getByRole('button',{name:'Open activity',exact:true})).toBeVisible();});
async function snapshot(page:Page){return page.evaluate(()=>(window as any).__activityFixture.snapshot);}
async function open(page:Page){await page.getByRole('button',{name:'Open activity',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).scheduledTitle).toBe('Daily fixture task');}
test('native activity keeps original read-only DTOs, priority ordering and source composer on close',async({page})=>{
  await open(page);const task=page.getByRole('button',{name:'Daily fixture task',exact:true});await expect(task).toBeVisible();
  await expect(page.getByRole('button',{name:'Existing Chat 0',exact:true})).toHaveCount(2);
  const calls=await page.evaluate(()=>(window as any).__activityFixture.calls.map(({path,method,headers}:any)=>({path,method,headers})));
  expect(calls.every((call:any)=>call.method==='GET')).toBe(true);expect(calls.some((call:any)=>call.path.includes('dream'))).toBe(false);
  for(const call of calls){expect(call.headers['x-ink-csrf']).toHaveLength(43);expect(call.headers.authorization).toBeUndefined();}
  expect(calls.some((call:any)=>call.path.includes('scheduled-tasks/day?local_date=')&&call.path.includes('display_time_zone='))).toBe(true);
  const labels=await page.getByRole('button').allTextContents();expect(labels.findIndex(value=>value.includes('Daily fixture task'))).toBeLessThan(labels.findIndex(value=>value.includes('Existing Chat 0')));
  await page.getByRole('button',{name:'Close activity',exact:true}).click();await expect(page.getByLabel('Source draft',{exact:true})).toHaveValue('Existing unsent draft');expect(await page.evaluate(()=>(window as any).__activityFixture.mounts)).toBe(1);
});
test('native scheduled detail preserves original fields and navigates exactly to an execution Thread',async({page})=>{
  await open(page);await page.getByRole('button',{name:'Daily fixture task',exact:true}).click();await expect(page.getByText('fixture-model',{exact:true})).toBeVisible();
  await expect(page.getByText('Keep the existing schedule',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Creation conversation',exact:true})).toHaveCount(1);
  await expect(page.getByRole('button',{name:'Run conversation',exact:true})).toHaveCount(1);
  await page.getByRole('button',{name:'Run conversation',exact:true}).click();expect(await page.evaluate(()=>(window as any).__activityFixture.selected)).toBe('fixture-execution');
  expect(await page.evaluate(()=>(window as any).__activityFixture.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});
test('native activity source retry recovers today tasks while retaining Chat/history',async({page})=>{
  await page.evaluate(()=>(window as any).__activityFixture.failDay=true);await page.getByRole('button',{name:'Open activity',exact:true}).click();
  await expect.poll(async()=>(await snapshot(page)).scheduledError).toBe(true);await expect(page.getByRole('button',{name:'Existing Chat 0',exact:true}).first()).toBeVisible();
  const chatReads=await page.evaluate(()=>(window as any).__activityFixture.calls.filter((call:any)=>call.path.startsWith('/api/claude-agent/threads')).length);
  await page.evaluate(()=>(window as any).__activityFixture.failDay=false);await page.getByRole('button',{name:'Reload',exact:true}).click();await expect(page.getByRole('button',{name:'Daily fixture task',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>(window as any).__activityFixture.calls.filter((call:any)=>call.path.startsWith('/api/claude-agent/threads')).length)).toBe(chatReads);
});
test('native foreground recovery rejects aborted old-day receipts without any mutation',async({page})=>{
  await page.evaluate(()=>(window as any).__activityFixture.holdDay=true);await page.getByRole('button',{name:'Open activity',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__activityFixture.held.length)).toBe(1);
  await page.getByRole('button',{name:'Background',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).active).toBe(false);
  expect(await page.evaluate(()=>(window as any).__activityFixture.held[0].signal.aborted)).toBe(true);
  await page.evaluate(()=>{const f=(window as any).__activityFixture;f.holdDay=false;f.dayTitle='Fresh foreground task';});await page.getByRole('button',{name:'Foreground',exact:true}).click();
  await expect(page.getByRole('button',{name:'Fresh foreground task',exact:true})).toBeVisible();await page.evaluate(()=>(window as any).__activityFixture.held[0].release());
  await expect(page.getByRole('button',{name:'Daily fixture task',exact:true})).toHaveCount(0);expect((await snapshot(page)).scheduledTitle).toBe('Fresh foreground task');
  expect(await page.evaluate(()=>(window as any).__activityFixture.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});

test('native display filters exclude Dream and preserve historical Chat when priority is hidden',async({page})=>{
  await open(page);await page.getByRole('button',{name:'Display activities',exact:true}).click();
  await expect(page.getByRole('checkbox',{name:'Dream',exact:true})).toHaveCount(0);
  await page.getByRole('checkbox',{name:'Scheduled tasks',exact:true}).click();await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Daily fixture task',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Existing Chat 0',exact:true})).toHaveCount(2);
  await page.getByRole('button',{name:'Display activities',exact:true}).click();await page.getByRole('checkbox',{name:'Priority section',exact:true}).click();await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Existing Chat 0',exact:true})).toHaveCount(1);
  expect(await page.evaluate(()=>(window as any).__activityFixture.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});
test('native activity search uses the original query and opens only the selected Thread',async({page})=>{
  await open(page);await page.getByRole('button',{name:'Search chat history',exact:true}).click();
  await page.getByRole('textbox',{name:'Search chat history',exact:true}).fill('23');
  const searchPanel=page.locator('[aria-label="Search chat history"]').filter({has:page.getByRole('textbox',{name:'Search chat history',exact:true})});
  await expect(searchPanel.getByText('Matching 23',{exact:true})).toBeVisible();
  await searchPanel.getByRole('button',{name:'Existing Chat 23',exact:true}).click();
  expect(await page.evaluate(()=>(window as any).__activityFixture.selected)).toBe('fixture-chat-23');
  const calls=await page.evaluate(()=>(window as any).__activityFixture.calls.map((call:any)=>call.path));
  expect(calls.some((path:string)=>path.includes('query=23')&&path.includes('search_scope=all')&&path.includes('retrieval_mode=fuzzy'))).toBe(true);
});
test('native activity 401 requests the existing session refresh without starting business',async({page})=>{
  await page.evaluate(()=>(window as any).__activityFixture.expired=true);await page.getByRole('button',{name:'Open activity',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__activityFixture.expirations)).toBeGreaterThan(0);
  expect(await page.evaluate(()=>(window as any).__activityFixture.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});

test('native task detail read failure preserves the source and retries the original read-only endpoints',async({page})=>{
  await open(page);await page.evaluate(()=>(window as any).__activityFixture.failDetail=true);
  await page.getByRole('button',{name:'Daily fixture task',exact:true}).click();
  await expect(page.getByRole('alert')).toHaveText('Task details are temporarily unavailable.');
  await expect(page.getByText('fixture-model',{exact:true})).toHaveCount(0);
  await page.evaluate(()=>(window as any).__activityFixture.failDetail=false);await page.getByRole('button',{name:'Retry',exact:true}).click();
  await expect(page.getByText('fixture-model',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Close scheduled task details',exact:true}).click();
  await expect(page.getByLabel('Source draft',{exact:true})).toHaveValue('Existing unsent draft');
  expect(await page.evaluate(()=>(window as any).__activityFixture.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});
