// [Sync] 2026-10-29: configuration-only refresh preserves catalog/runtime/draft and rejects older reads.
// [Sync] 2026-10-28: require one complete catalog read per setup cycle and reject per-Deck detail traffic.
// [Input] Production native startup read hook, runtime manager and original Deck/config HTTP contracts.
// [Output] Technical retry, last-successful snapshot, 401 and abandoned-read evidence without business mutation.
// [Pos] Provider-free browser harness; runtime and HTTP boundaries are explicit fixtures.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
const entry=`
import React,{useEffect,useState} from 'react';import {createRoot} from 'react-dom/client';
import {NativeModules} from 'react-native';
import useNativeChatSetup from '/app/_dream/components/chat/useNativeChatSetup.native.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';
const mode=new URLSearchParams(location.search).get('mode');
const f=window.__setupFixture={calls:[],runtimeStarts:0,runtimeFailures:mode==='runtime-error'?1:0,failConfig:mode==='failed',failCatalog:mode==='failed',invalidConfig:false,expired:false,expirations:0,hold:mode==='held',held:[],variant:'original',mounts:0,configRefreshFailures:0};
NativeModules.InkRuntime={ensureStarted:()=>{f.runtimeStarts++;return f.runtimeFailures-->0?Promise.reject(Error('fixture startup failed')):Promise.resolve({state:'ready',localWebOrigin:'http://127.0.0.1:5173'});}};
await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
async function transport(input,init={}){
 const path=new URL(String(input),'http://fixture.invalid').pathname;f.calls.push({path,method:init.method||'GET',headers:Object.fromEntries(new Headers(init.headers)),signal:init.signal});
 if((init.method||'GET')!=='GET')throw Error('UNEXPECTED_BUSINESS_MUTATION');
 const deck={id:'fixture-deck',name:f.variant,enabled:true,agent_type:'chat',voices:[{id:'fixture-agent',deck_id:'fixture-deck',name:f.variant,enabled:true}]};
 let reply;
 if(f.expired)reply=new Response(null,{status:401});
 else if(path==='/api/system-config')reply=f.failConfig?new Response(null,{status:503}):Response.json(f.invalidConfig?{workspace_enabled:'unknown',im_full_access_enabled:true}:{workspace_enabled:false,im_full_access_enabled:true,system_prompt:f.variant});
 else if(path==='/api/decks/catalog')reply=f.failCatalog?Response.json({detail:'fixture catalog unavailable'},{status:503}):Response.json({decks:[deck]});
 else throw Error('UNEXPECTED_FIXTURE_HTTP '+path);
 return f.hold?new Promise(resolve=>f.held.push({signal:init.signal,release:()=>resolve(reply)})):reply;
}
function Source(){const [draft,setDraft]=useState('Existing unsent draft');useEffect(()=>{f.mounts++;},[]);return <textarea aria-label="Source draft" value={draft} onChange={e=>setDraft(e.target.value)}/>;}
function Reads(){const s=useNativeChatSetup({transport,onSessionExpired:()=>f.expirations++});f.snapshot={origin:s.origin,config:s.config,configLoaded:s.configLoaded,decks:s.decks,error:s.error,loading:s.loading,revision:s.revision};return <section><button disabled={s.loading} onClick={s.retry}>Retry reads</button><button onClick={()=>void s.refreshConfig().catch(()=>f.configRefreshFailures++)}>Refresh configuration</button><button disabled={!s.configLoaded}>Send readiness</button><output aria-label="Read state">{JSON.stringify(f.snapshot)}</output></section>;}
function Harness(){const [mounted,setMounted]=useState(true);return <><Source/><button onClick={()=>setMounted(v=>!v)}>Toggle reads</button>{mounted?<Reads/>:null}</>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 const port=await new Promise<number>((resolve,reject)=>{const probe=netServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{const a=probe.address();if(!a||typeof a==='string')return reject(Error('PORT'));probe.close(error=>error?reject(error):resolve(a.port));});});
 const root=fileURLToPath(new URL('../',import.meta.url));
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-chat-setup-vite-20261028',optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','zod']},resolve:{alias:{'react-native':'react-native-web'}},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'native-chat-setup-production',enforce:'pre',resolveId(id){if(id==='/setup-entry.tsx')return '\0setup-entry';},async load(id){if(id==='\0setup-entry')return transformWithEsbuild(entry,'setup-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-setup')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-setup','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/setup-entry.tsx"></script></body></html>'));});}}]});await server.listen();base='http://127.0.0.1:'+port+'/native-setup';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
async function open(page:Page,mode='success'){await page.goto(base+'?mode='+mode);await expect(page.getByRole('button',{name:'Toggle reads',exact:true})).toBeVisible();}
async function state(page:Page){return page.evaluate(()=>(window as any).__setupFixture.snapshot);}
async function settled(page:Page){await expect.poll(async()=>(await state(page))?.loading).toBe(false);}
test('failed initial reads retry original endpoints while preserving the draft and shared runtime',async({page})=>{
 await open(page,'failed');await settled(page);await expect(page.getByRole('button',{name:'Send readiness'})).toBeDisabled();
 await page.getByRole('textbox',{name:'Source draft'}).fill('Keep my edited draft');
 await page.evaluate(()=>{const f=(window as any).__setupFixture;f.failConfig=false;f.failCatalog=false;});await page.getByRole('button',{name:'Retry reads'}).click();await settled(page);
 expect(await state(page)).toMatchObject({configLoaded:true,error:'',config:{workspace_enabled:false,im_full_access_enabled:true},decks:[{id:'fixture-deck'}]});await expect(page.getByRole('textbox',{name:'Source draft'})).toHaveValue('Keep my edited draft');
 expect(await page.evaluate(()=>{const f=(window as any).__setupFixture;return {starts:f.runtimeStarts,mounts:f.mounts,allReads:f.calls.every(c=>c.method==='GET'),csrf:f.calls.every(c=>c.headers['x-ink-csrf']==='a'.repeat(43))};})).toEqual({starts:1,mounts:1,allReads:true,csrf:true});
});
test('failed refresh and malformed config retain the last successful snapshots',async({page})=>{
 await open(page);await settled(page);const before=await state(page);await page.evaluate(()=>{const f=(window as any).__setupFixture;f.invalidConfig=true;f.failCatalog=true;f.variant='changed';});await page.getByRole('button',{name:'Retry reads'}).click();await settled(page);
 const after=await state(page);expect(after.configLoaded).toBe(true);expect(after.config).toEqual(before.config);expect(after.decks).toEqual(before.decks);expect(after.error).toContain('配置');expect(after.error).toContain('Agent');
 expect(await page.evaluate(()=>(window as any).__setupFixture.runtimeStarts)).toBe(1);
});
test('late abandoned reads are aborted and cannot replace a remounted current snapshot',async({page})=>{
 await open(page,'held');await expect.poll(()=>page.evaluate(()=>(window as any).__setupFixture.held.length)).toBe(2);await page.getByRole('button',{name:'Toggle reads'}).click();
 expect(await page.evaluate(()=>(window as any).__setupFixture.held.every(x=>x.signal.aborted))).toBe(true);
 await page.evaluate(()=>{const f=(window as any).__setupFixture;f.hold=false;f.variant='current';});await page.getByRole('button',{name:'Toggle reads'}).click();await settled(page);
 await page.evaluate(()=>{const f=(window as any).__setupFixture;f.held.forEach(x=>x.release());});await expect.poll(async()=>(await state(page)).decks[0]?.name).toBe('current');
 expect((await state(page)).config.system_prompt).toBe('current');expect(await page.evaluate(()=>(window as any).__setupFixture.runtimeStarts)).toBe(1);await expect(page.getByRole('textbox',{name:'Source draft'})).toHaveValue('Existing unsent draft');
});
test('401 refresh is coalesced for the read cycle and never submits business work',async({page})=>{
 await open(page);await settled(page);await page.evaluate(()=>(window as any).__setupFixture.expired=true);await page.getByRole('button',{name:'Retry reads'}).click();await settled(page);
 expect(await page.evaluate(()=>{const f=(window as any).__setupFixture;return {expirations:f.expirations,starts:f.runtimeStarts,methods:[...new Set(f.calls.map(c=>c.method))]};})).toEqual({expirations:1,starts:1,methods:['GET']});expect((await state(page)).configLoaded).toBe(true);
});
test('a failed runtime start retries through the existing manager before any HTTP reads',async({page})=>{
 await open(page,'runtime-error');await settled(page);expect(await page.evaluate(()=>(window as any).__setupFixture.calls.length)).toBe(0);expect((await state(page)).configLoaded).toBe(false);
 await page.getByRole('button',{name:'Retry reads'}).click();await settled(page);expect((await state(page)).error).toBe('');expect((await state(page)).configLoaded).toBe(true);expect(await page.evaluate(()=>(window as any).__setupFixture.runtimeStarts)).toBe(2);
});

test('Agent setup uses one catalog read and no per-Deck detail reads',async({page})=>{
 await open(page);await settled(page);
 expect(await page.evaluate(()=>(window as any).__setupFixture.calls.map(c=>c.path).sort())).toEqual(['/api/decks/catalog','/api/system-config']);
 expect((await state(page)).decks[0].voices[0].id).toBe('fixture-agent');
});


test('Settings refreshes only original config without restarting runtime or replacing catalog/draft',async({page})=>{
 await open(page);await settled(page);await page.getByRole('textbox',{name:'Source draft'}).fill('Keep current Chat input');
 const before=await state(page);await page.evaluate(()=>(window as any).__setupFixture.variant='saved-settings');await page.getByRole('button',{name:'Refresh configuration',exact:true}).click();
 await expect.poll(async()=>(await state(page)).config.system_prompt).toBe('saved-settings');expect((await state(page)).decks).toEqual(before.decks);
 expect(await page.evaluate(()=>{const f=(window as any).__setupFixture;return {starts:f.runtimeStarts,mounts:f.mounts,config:f.calls.filter(c=>c.path==='/api/system-config').length,catalog:f.calls.filter(c=>c.path==='/api/decks/catalog').length};})).toEqual({starts:1,mounts:1,config:2,catalog:1});
 await expect(page.getByRole('textbox',{name:'Source draft'})).toHaveValue('Keep current Chat input');
 await page.evaluate(()=>(window as any).__setupFixture.failConfig=true);await page.getByRole('button',{name:'Refresh configuration',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__setupFixture.configRefreshFailures)).toBe(1);expect((await state(page)).config.system_prompt).toBe('saved-settings');
});
test('a superseded configuration refresh cannot overwrite newer server settings',async({page})=>{
 await open(page);await settled(page);await page.evaluate(()=>{const f=(window as any).__setupFixture;f.hold=true;f.variant='older-settings';});await page.getByRole('button',{name:'Refresh configuration',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__setupFixture.held.length)).toBe(1);
 await page.evaluate(()=>{const f=(window as any).__setupFixture;f.hold=false;f.variant='newer-settings';});await page.getByRole('button',{name:'Refresh configuration',exact:true}).click();await expect.poll(async()=>(await state(page)).config.system_prompt).toBe('newer-settings');
 await page.evaluate(()=>(window as any).__setupFixture.held[0].release());await expect.poll(async()=>(await state(page)).config.system_prompt).toBe('newer-settings');expect(await page.evaluate(()=>(window as any).__setupFixture.runtimeStarts)).toBe(1);
});
