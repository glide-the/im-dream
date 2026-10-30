// [Input] Production native history coordinator/Chat page, original API contracts and synthetic HTTP/AppState boundaries.
// [Output] Technical pagination, stale-read/deletion/search/lifecycle, re-enabled refresh and composer-instance evidence.
// [Pos] Explicit isolated browser harness; RNW renders the actual native layout, no account/backend/model execution.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
const native=`export * from 'react-native-web';export const NativeModules={InkRuntime:{}};export const AppState={currentState:'active',listeners:new Set(),addEventListener(_,fn){this.listeners.add(fn);return {remove:()=>this.listeners.delete(fn)};}};`;
const entry=`
import React,{useEffect,useState} from 'react';import {createRoot} from 'react-dom/client';
import {AppState,Pressable,Text,TextInput,View} from 'react-native';
import useNativeChatHistory from '/app/_dream/components/chat/useNativeChatHistory.native.ts';
import ChatPage from '/app/_dream/components/chat/ChatPage.native.tsx';
import {buildDefaultLandingQuickActions} from '/app/_dream/components/chat/chatLandingActions.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
await i18n.changeLanguage('en');await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const now=Date.now();const f=window.__historyFixture={calls:[],rows:Array.from({length:45},(_,i)=>({id:'fixture-'+i,title:'Conversation '+i,created_at:new Date(now-i*1000).toISOString(),updated_at:new Date(now-i*1000).toISOString()})),holdList:false,holdSearch:false,held:[],failMore:false,failDelete:false,expired:false,expirations:0,mounts:0,selected:null,quick:null,snapshot:null};
async function transport(input,init={}){
 const path=String(input),url=new URL(path,'http://fixture.invalid'),method=init.method||'GET',query=url.searchParams.get('query');
 f.calls.push({path,method,headers:Object.fromEntries(new Headers(init.headers))});if(f.expired)return new Response(null,{status:401});
 if(method==='DELETE'){if(f.failDelete)return new Response(null,{status:503});const id=decodeURIComponent(url.pathname.split('/').at(-1));f.rows=f.rows.filter(row=>row.id!==id);return Response.json({ok:true});}
 if(method!=='GET'||url.pathname!=='/api/claude-agent/threads')throw new Error('Unexpected history request');
 if(f.failMore && Number(url.searchParams.get('offset')||0)>0)return new Response(null,{status:503});
 const rows=query?f.rows.filter(row=>row.title.toLowerCase().includes(query.toLowerCase())).map(row=>({...row,match:{strategy:'fuzzy',score:1,fields:['title'],excerpt:'Match '+query}})):f.rows;
 const payload={threads:rows.slice(Number(url.searchParams.get('offset')||0),url.searchParams.has('limit')?Number(url.searchParams.get('offset')||0)+Number(url.searchParams.get('limit')):undefined)};
 return (query?f.holdSearch:f.holdList)?new Promise(resolve=>f.held.push({query,signal:init.signal,release:()=>resolve(Response.json(payload))})):Response.json(payload);
}
function Composer({onSend}){const [draft,setDraft]=useState('');useEffect(()=>{f.mounts++;},[]);return <View style={{minHeight:180,borderWidth:1,padding:12}}><TextInput accessibilityLabel="Fixture draft" value={draft} onChangeText={setDraft}/><Pressable accessibilityRole="button" onPress={onSend}><Text>Submit fixture</Text></Pressable></View>;}
function Harness(){
 const [conversation,setConversation]=useState(false),[enabled,setEnabled]=useState(true);
 const h=useNativeChatHistory({enabled,transport,onSessionExpired:()=>{f.expirations++;}});
 f.snapshot={threads:h.threads.map(row=>row.id),results:h.results.map(row=>row.id),loading:h.loading,loadingMore:h.loadingMore,error:h.error,moreError:h.moreError,hasMore:h.hasMore,searchOpen:h.searchOpen,query:h.query,searching:h.searching,searchError:h.searchError,deletingId:h.deletingId,deleteError:h.deleteError};
 const buttons=[['Reload history',()=>void h.reload()],['Load more history',()=>void h.loadMore()],['Delete first row',()=>void h.remove('fixture-0')],['Fail more',()=>{f.failMore=true;}],['Restore more',()=>{f.failMore=false;}],['Fail delete',()=>{f.failDelete=true;}],['Restore delete',()=>{f.failDelete=false;}],['Hold list',()=>{f.holdList=true;}],['Hold search',()=>{f.holdSearch=true;}],['Background',()=>{AppState.currentState='background';AppState.listeners.forEach(fn=>fn('background'));}],['Foreground',()=>{AppState.currentState='active';AppState.listeners.forEach(fn=>fn('active'));}],['Expire session',()=>{f.expired=true;}],['Home',()=>setConversation(false)],['Disable reads',()=>setEnabled(false)],['Enable reads',()=>setEnabled(true)]];
 return <View style={{height:'100vh'}}><View style={{flexDirection:'row',flexWrap:'wrap'}}>{buttons.map(([label,action])=><Pressable key={label} accessibilityRole="button" onPress={action} style={{padding:4}}><Text>{label}</Text></Pressable>)}</View>
  <ChatPage hasConversation={conversation} history={h} composer={<Composer onSend={()=>setConversation(true)}/>} conversation={<Text>Existing Thread view</Text>} quickActions={buildDefaultLandingQuickActions(i18n.t.bind(i18n))}
   onQuickAction={item=>{f.quick=item.id;}} onSelectThread={id=>{f.selected=id;}} onDeleteThread={id=>void h.remove(id)} />
 </View>;
}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  const port=await new Promise<number>((resolve,reject)=>{const probe=netServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{const address=probe.address();if(!address || typeof address==='string')return reject(new Error('Port'));probe.close(error=>error?reject(error):resolve(address.port));});});
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'native-history-production',enforce:'pre',resolveId(id){if(id==='react-native')return '\0history-native';if(id==='/history-entry.tsx')return '\0history-entry';},async load(id){if(id==='\0history-native')return native;if(id==='\0history-entry')return transformWithEsbuild(entry,'history-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-history')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-history','<html><head><link rel="icon" href="data:,"><style>html,body{margin:0;height:100%}</style></head><body><div id="root"></div><script type="module" src="/history-entry.tsx"></script></body></html>'));});}}]});await server.listen();base='http://127.0.0.1:'+port+'/native-history';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{page.on('pageerror',error=>{throw error;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.goto(base);await expect.poll(async()=>(await snapshot(page))?.threads?.length).toBe(20);});
async function snapshot(page:Page){return page.evaluate(()=>(window as any).__historyFixture.snapshot);}
async function calls(page:Page){return page.evaluate(()=>(window as any).__historyFixture.calls);}
async function release(page:Page,query:string|null=null){await page.evaluate(query=>{const f=(window as any).__historyFixture,item=f.held.find((item:any)=>item.query===query&&!item.released);if(!item)throw new Error('HELD_READ_MISSING');item.released=true;item.release();},query);}
test('history keeps canonical 21-row reads, CSRF and deduplicated 20-row pages',async({page})=>{
  const first=(await calls(page))[0];expect(first.path).toBe('/api/claude-agent/threads?limit=21');expect(first.headers['x-ink-csrf']).toHaveLength(43);expect(first.headers.authorization).toBeUndefined();
  await page.getByRole('button',{name:'Load more history',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).threads.length).toBe(40);
  await page.getByRole('button',{name:'Load more history',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).threads.length).toBe(45);expect((await snapshot(page)).hasMore).toBe(false);
});
test('a failed next page preserves rows and retries the same offset',async({page})=>{
  await page.getByRole('button',{name:'Fail more',exact:true}).click();await page.getByRole('button',{name:'Load more history',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).moreError).toBe(true);expect((await snapshot(page)).threads).toHaveLength(20);
  await page.getByRole('button',{name:'Restore more',exact:true}).click();await page.getByRole('button',{name:'Load more history',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).threads.length).toBe(40);
  expect((await calls(page)).filter((call:any)=>call.path.includes('offset=20'))).toHaveLength(2);
});
test('deleted rows cannot return through an already pending refresh and pagination adjusts consumed offset',async({page})=>{
  await page.getByRole('button',{name:'Hold list',exact:true}).click();await page.getByRole('button',{name:'Reload history',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.held.length)).toBe(1);
  await page.getByRole('button',{name:'Delete first row',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).threads.includes('fixture-0')).toBe(false);
  await release(page);await expect.poll(async()=>(await snapshot(page)).loading).toBe(false);expect((await snapshot(page)).threads).toHaveLength(19);
  await page.evaluate(()=>{(window as any).__historyFixture.holdList=false;});await page.getByRole('button',{name:'Load more history',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).threads.length).toBe(39);
  expect((await calls(page)).at(-1).path).toContain('offset=19');expect((await snapshot(page)).threads).not.toContain('fixture-0');
});
test('failed deletion keeps history and permits the original DELETE retry',async({page})=>{
  await page.getByRole('button',{name:'Fail delete',exact:true}).click();await page.getByRole('button',{name:'Delete first row',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).deleteError).toBe(true);expect((await snapshot(page)).threads).toContain('fixture-0');
  await page.getByRole('button',{name:'Restore delete',exact:true}).click();await page.getByRole('button',{name:'Delete first row',exact:true}).click();await expect.poll(async()=>(await snapshot(page)).threads.includes('fixture-0')).toBe(false);expect((await calls(page)).filter((call:any)=>call.method==='DELETE')).toHaveLength(2);
});
test('search uses original fuzzy parameters and discards superseded and closed-dialog results',async({page})=>{
  await page.getByRole('button',{name:'Hold search',exact:true}).click();await page.getByRole('button',{name:'Search',exact:true}).click();const input=page.getByRole('textbox',{name:'Search chat history'});await input.fill('Conversation 1');
  await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.held.filter((item:any)=>item.query).length)).toBe(1);
  await input.fill('Conversation 2');await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.held.filter((item:any)=>item.query).length)).toBe(2);await release(page,'Conversation 2');await expect.poll(async()=>(await snapshot(page)).results.length).toBe(11);
  await release(page,'Conversation 1');expect((await snapshot(page)).results.every((id:string)=>id.startsWith('fixture-2'))).toBe(true);
  expect((await calls(page)).find((call:any)=>call.path.includes('query=Conversation+2')).path).toContain('search_scope=all&retrieval_mode=fuzzy');
  await input.fill('Conversation 3');await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.held.filter((item:any)=>item.query).length)).toBe(3);await page.getByRole('button',{name:'Close search'}).click();await release(page,'Conversation 3');expect((await snapshot(page)).results.every((id:string)=>id.startsWith('fixture-2'))).toBe(true);
});
test('foreground rereads history while background invalidates pending results without business mutations',async({page})=>{
  await page.getByRole('button',{name:'Hold list',exact:true}).click();await page.getByRole('button',{name:'Reload history',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.held.length)).toBe(1);
  await page.getByRole('button',{name:'Background',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.held[0].signal.aborted)).toBe(true);await release(page);expect((await snapshot(page)).threads).toHaveLength(20);
  await page.evaluate(()=>{(window as any).__historyFixture.holdList=false;});await page.getByRole('button',{name:'Foreground',exact:true}).click();await expect.poll(async()=>(await calls(page)).length).toBeGreaterThanOrEqual(3);await expect.poll(async()=>(await snapshot(page)).loading).toBe(false);expect((await calls(page)).filter((call:any)=>call.method!=='GET')).toEqual([]);
});
test('reenabling history after a conversation loads the latest persisted row',async({page})=>{
  await page.getByRole('button',{name:'Disable reads',exact:true}).click();
  await page.evaluate(()=>{const f=(window as any).__historyFixture;f.rows.unshift({...f.rows[0],id:'fixture-cancelled-latest',title:'Newly cancelled conversation'});});
  const readsBefore=(await calls(page)).length;
  await page.getByRole('button',{name:'Enable reads',exact:true}).click();
  await expect.poll(async()=>(await snapshot(page)).threads[0]).toBe('fixture-cancelled-latest');
  await expect.poll(async()=>(await snapshot(page)).loading).toBe(false);
  expect((await calls(page)).length).toBeGreaterThan(readsBefore);
  expect((await calls(page)).every((call:any)=>call.method==='GET')).toBe(true);
});
test('landing order and first Thread transition keep the same composer instance and draft',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.getByLabel('Fixture draft',{exact:true}).fill('Preserve the composer instance');
  const composer=await page.getByTestId('native-chat-composer').boundingBox(),content=await page.getByTestId('native-chat-landing-content').boundingBox();expect(composer!.y+composer!.height).toBeLessThanOrEqual(content!.y+1);
  await page.getByRole('button',{name:'Submit fixture',exact:true}).click();await expect(page.getByTestId('native-chat-conversation')).toBeVisible();await expect(page.getByLabel('Fixture draft',{exact:true})).toHaveValue('Preserve the composer instance');expect(await page.evaluate(()=>(window as any).__historyFixture.mounts)).toBe(1);
  const after=await page.getByTestId('native-chat-composer').boundingBox(),messages=await page.getByTestId('native-chat-conversation').boundingBox();expect(after!.y).toBeGreaterThanOrEqual(messages!.y+messages!.height-1);
});
test('HTTP 401 requests normal session refresh and never creates a Thread',async({page})=>{
  await page.getByRole('button',{name:'Expire session',exact:true}).click();await page.getByRole('button',{name:'Reload history',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__historyFixture.expirations)).toBe(1);await expect.poll(async()=>(await snapshot(page)).error).toBe(true);expect((await calls(page)).every((call:any)=>call.method==='GET')).toBe(true);
});
