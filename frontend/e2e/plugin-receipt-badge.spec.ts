// [Input] Original Web/native metadata components, shared production read hook and public receipt/installation DTOs.
// [Output] Provider-free provenance, same-Deck selection and stale-read cleanup evidence.
// [Pos] Web-first metadata regression; fixture transport owns all HTTP, credentials and plugin records.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {createServer as netServer} from 'node:net';
const entry=`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import i18n from '/app/_dream/i18n.ts';
import WebBadge from '/app/_dream/components/chat/PluginReceiptBadge.tsx';
import NativeBadge,{ChatAgentBadge} from '/app/_dream/components/chat/PluginReceiptBadge.native.tsx';
import ChatTopActions from '/app/_dream/components/chat/ChatTopActions.native.tsx';
import {AppState,View,NativeModules} from 'react-native';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';
const params=new URLSearchParams(location.search),mode=params.get('mode') || 'active',native=params.has('native'),long=params.has('long');
const Badge=native?NativeBadge:WebBadge;
const f=window.__badgeFixture={calls:[],held:[],packed:mode==='packed',fail:false,choices:[],copied:null,focuses:[],hold:mode==='held'};
Object.defineProperty(AppState,'currentState',{value:'active',writable:true,configurable:true});AppState.listeners=new Set();AppState.addEventListener=(_name,fn)=>{AppState.listeners.add(fn);return {remove:()=>AppState.listeners.delete(fn)};};
NativeModules.InkRuntime={copyText:async text=>{f.copied=text;}};
const voices=[{id:'agent-a',deck_id:'deck-a',name:'Author',name_en:'Author',enabled:true,icon:'brain',color:'blue'},
 {id:'agent-b',deck_id:'deck-a',name:'Editor',name_en:'Editor',enabled:true,icon:'brain',color:'green'},
 {id:'disabled-agent',name:'Disabled Agent',enabled:false}];
const deck={id:'deck-a',name:'Writing',name_en:long?'Writing '.repeat(18):'Writing',enabled:true,voices};
f.emitState=state=>{AppState.currentState=state;AppState.listeners.forEach(fn=>fn(state));};
const plugin={package_spec:'packed-plugin@fixture',resolved_version:'1.2.3',artifact_digest:'sha256:'+'b'.repeat(64),relative_path:'plugins/packed',verified:true};
const receipt=id=>({thread_id:id,deck_id:'deck-a',workspace_found:true,receipt:{schema_version:'1',workspace:'fixture',deck_id:'deck-a',packed_at:null,frozen:true,plugins:f.packed||id==='thread-b'?[{...plugin,package_spec:id==='thread-b'?'current-thread-plugin@fixture':plugin.package_spec}]:[]},launch_manifest:null});
await loadBrowserSession(async()=>Response.json({user:{id:'42',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
window.fetch=async(input,init={})=>{
 const path=new URL(String(input),location.origin).pathname;
 f.calls.push({path,method:init.method || 'GET',csrf:new Headers(init.headers).get('x-ink-csrf'),signal:init.signal});
 if(path==='/api/claude-plugins/installations')return Response.json({installations:[
  {id:'ready',package_name:'configured-plugin',resolved_version:'0.5.0',status:'ready',deck_refs:[{deck_id:'deck-a',enabled:true}]},
  {id:'foreign',package_name:'foreign-plugin',resolved_version:'1',status:'ready',deck_refs:[{deck_id:'other-deck',enabled:true}]},
  {id:'disabled-ref',package_name:'disabled-ref-plugin',resolved_version:'1',status:'ready',deck_refs:[{deck_id:'deck-a',enabled:false}]},
  {id:'pending',package_name:'pending-plugin',resolved_version:'1',status:'installing',deck_refs:[{deck_id:'deck-a',enabled:true}]},
 ]});
 const match=path.match(/^\\/api\\/claude-agent\\/threads\\/([^/]+)\\/plugin-load-receipt$/);
 if(!match)throw Error('UNEXPECTED_FIXTURE_HTTP '+path);
 if(f.fail)return Response.json({error:{code:'FIXTURE_UNAVAILABLE',message:'Fixture unavailable'}},{status:503});
 const payload=receipt(match[1]);
 if(f.hold && match[1]==='thread-a')return new Promise(resolve=>f.held.push({signal:init.signal,release:()=>resolve(Response.json({...payload,receipt:{...payload.receipt,plugins:[plugin]}}))}));
 return Response.json(payload);
};
await i18n.changeLanguage('en');
function Fixture(){const [thread,setThread]=useState(mode==='landing'?null:'thread-a'),[agent,setAgent]=useState('agent-a'),[mounted,setMounted]=useState(true);const badge=mounted?<Badge threadId={thread} deck={deck} activeVoiceId={agent} activeVoiceName={agent==='agent-a'?'Author':'Editor'} onSelectAgent={id=>{f.choices.push(id);setAgent(id);}} {...(native?{transport:window.fetch}:{})}/>:null;return <>
 <button onClick={()=>setThread('thread-b')}>Switch thread</button><button onClick={()=>setMounted(false)}>Unmount badge</button>
 {native?<View style={{flexDirection:'row',padding:12,maxWidth:'100%'}}><View style={{flex:1}}/><ChatTopActions creating={false} activityOpen={false} workspaceEnabled={false} workspaceOpen={false} contextBadge={<ChatAgentBadge voice={{...voices[agent==='agent-a'?0:1],name:long?'Author '.repeat(18):agent==='agent-a'?'Author':'Editor'}}/>} pluginReceipt={badge} onNewChat={()=>{}} onToggleActivity={()=>{}} onToggleWorkspace={()=>{}} onShare={()=>{}}/></View>:badge}
 </>;}
createRoot(document.querySelector('#root')).render(<Fixture/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 const port=await new Promise<number>((resolve,reject)=>{const s=netServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const a=s.address();if(!a||typeof a==='string')return reject(Error('PORT'));s.close(error=>error?reject(error):resolve(a.port));});});
 const root=fileURLToPath(new URL('../',import.meta.url));
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-plugin-badge-vite-cache-20261029',optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'original-metadata-fixture',enforce:'pre',resolveId(id,importer){if(id==='./Icons' && importer?.endsWith('.native.tsx'))return root+'app/_dream/components/chat/Icons.native.tsx';if(id==='/badge-entry.tsx')return '\0badge-entry';},async load(id){if(id==='\0badge-entry')return transformWithEsbuild(entry,'badge-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/badge-fixture')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/badge-fixture','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/badge-entry.tsx"></script></body></html>'));});}}]});await server.listen();base='http://127.0.0.1:'+port+'/badge-fixture';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.clock.install({time:new Date('2026-10-29T00:00:00Z')});});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
async function open(page:Page,mode='active',native=false,extra=''){await page.goto(base+'?mode='+mode+(native?'&native=1':'')+extra);await expect(page.getByRole('button',{name:'Deck metadata',exact:true})).toBeVisible();}
async function calls(page:Page){return page.evaluate(()=>(window as any).__badgeFixture.calls.map(({path,method,csrf,signal}:any)=>({path,method,csrf,aborted:signal?.aborted ?? false})));}
test('Web landing keeps Deck context, ready enabled plugin refs and read-only Agent chips',async({page})=>{
 await open(page,'landing');await page.getByRole('button',{name:'Deck metadata',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Deck metadata'});
 await expect(dialog.getByText('Writing',{exact:true})).toBeVisible();await expect(dialog.getByText('configured-plugin',{exact:false})).toBeVisible();
 await expect(dialog.getByRole('button',{name:'Author, current Agent'})).toBeDisabled();await expect(dialog.getByRole('button',{name:'Switch to Editor'})).toBeDisabled();
 await expect(dialog.getByText(/foreign-plugin|disabled-ref-plugin|pending-plugin|Disabled Agent/)).toHaveCount(0);
 expect((await calls(page)).map(c=>c.path)).toEqual(['/api/claude-plugins/installations']);
});
test('Web receipt keeps Deck identity, frozen provenance and complete digest copy',async({page,context})=>{
 await context.grantPermissions(['clipboard-read','clipboard-write']);await open(page);await page.getByRole('button',{name:'Deck metadata',exact:true}).click();
 await expect(page.getByText('configured-plugin',{exact:false})).toBeVisible();await page.evaluate(()=>(window as any).__badgeFixture.packed=true);await page.clock.runFor(3000);
 await expect(page.getByText('packed-plugin@fixture',{exact:false})).toBeVisible();await expect(page.getByText('configured-plugin',{exact:false})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Deck metadata',exact:true})).toContainText('Writing');await expect(page.getByText('Workspace frozen for this conversation',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Copy digest',exact:true}).click();expect(await page.evaluate(()=>navigator.clipboard.readText())).toBe('sha256:'+'b'.repeat(64));
 expect((await calls(page)).every(c=>c.method==='GET' && c.csrf==='a'.repeat(43))).toBe(true);
});
test('Web active thread selects only its supplied Deck Agent without a mutation',async({page})=>{
 await open(page);await page.getByRole('button',{name:'Deck metadata',exact:true}).click();await page.getByRole('button',{name:'Switch to Editor'}).click();
 await expect(page.getByRole('dialog',{name:'Deck metadata'})).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__badgeFixture.choices)).toEqual(['agent-b']);
 await page.getByRole('button',{name:'Deck metadata',exact:true}).click();await expect(page.getByRole('button',{name:'Editor, current Agent'})).toBeDisabled();
 expect((await calls(page)).every(c=>c.method==='GET')).toBe(true);
});
test('Web abandoned Thread receipt cannot replace the current metadata',async({page})=>{
 await open(page,'held');await expect.poll(()=>page.evaluate(()=>(window as any).__badgeFixture.held.length)).toBe(1);
 await page.getByRole('button',{name:'Switch thread',exact:true}).click();await page.getByRole('button',{name:'Deck metadata',exact:true}).click();
 await expect(page.getByText('current-thread-plugin@fixture',{exact:false})).toBeVisible();await page.evaluate(()=>(window as any).__badgeFixture.held.forEach((x:any)=>x.release()));
 await expect(page.getByText('packed-plugin@fixture',{exact:false})).toHaveCount(0);expect((await calls(page)).find(c=>c.path.includes('thread-a'))?.aborted).toBe(false);
 await page.getByRole('button',{name:'Unmount badge',exact:true}).click();const before=(await calls(page)).length;await page.clock.runFor(130000);expect((await calls(page)).length).toBe(before);
});


test('native metadata reuses original same-Deck selection and cancels reads in background',async({page})=>{
 await open(page,'held',true);await expect.poll(()=>page.evaluate(()=>(window as any).__badgeFixture.held.length)).toBe(1);
 await page.getByRole('button',{name:'Deck metadata',exact:true}).click();await expect(page.getByRole('dialog',{name:'Deck metadata'})).toBeVisible();
 await page.evaluate(()=>(window as any).__badgeFixture.emitState('background'));await expect(page.getByRole('dialog',{name:'Deck metadata'})).toHaveCount(0);
 expect((await calls(page)).find(c=>c.path.includes('thread-a'))?.aborted).toBe(true);const before=(await calls(page)).length;await page.clock.runFor(130000);expect((await calls(page)).length).toBe(before);
 await page.evaluate(()=>{const f=(window as any).__badgeFixture;f.hold=false;f.emitState('active');});await page.getByRole('button',{name:'Deck metadata',exact:true}).click();
 await page.getByRole('button',{name:'Switch to Editor',exact:true}).click();expect(await page.evaluate(()=>(window as any).__badgeFixture.choices)).toEqual(['agent-b']);
 await expect.poll(()=>page.evaluate(()=>(window as any).__badgeFixture.focuses.length)).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Deck metadata',exact:true}).click();await expect(page.getByRole('button',{name:'Editor, current Agent',exact:true})).toBeDisabled();
 expect((await calls(page)).every(c=>c.method==='GET' && c.csrf==='a'.repeat(43))).toBe(true);
});
test('native frozen metadata copies the complete digest through the original clipboard adapter',async({page})=>{
 await open(page,'packed',true);await page.getByRole('button',{name:'Deck metadata',exact:true}).click();
 await expect(page.getByText('packed-plugin@fixture',{exact:false})).toBeVisible();await page.getByRole('button',{name:'Copy digest',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__badgeFixture.copied)).toBe('sha256:'+'b'.repeat(64));await expect(page.getByText('✓ Copied',{exact:true})).toBeVisible();
 await expect(page.getByText('Workspace frozen for this conversation',{exact:false})).toBeVisible();
 await page.keyboard.press('Escape');await expect(page.getByRole('dialog',{name:'Deck metadata'})).toHaveCount(0);
});
test('native original toolbar context and metadata remain reachable on a narrow screen with long names',async({page})=>{
 await page.setViewportSize({width:390,height:844});await open(page,'packed',true,'&long=1');
 const trigger=page.getByRole('button',{name:'Deck metadata',exact:true});const box=await trigger.boundingBox();expect(box).not.toBeNull();expect(box!.width).toBeGreaterThanOrEqual(44);expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(390);
 for(const name of ['New chat','Activity view','More']){const b=await page.getByRole('button',{name,exact:true}).boundingBox();expect(b).not.toBeNull();expect(b!.width).toBeGreaterThanOrEqual(44);expect(b!.x+b!.width).toBeLessThanOrEqual(390);}
 await trigger.click();const panel=await page.getByRole('dialog',{name:'Deck metadata'}).boundingBox();expect(panel).not.toBeNull();expect(panel!.x).toBeGreaterThanOrEqual(0);expect(panel!.x+panel!.width).toBeLessThanOrEqual(390);expect(panel!.y+panel!.height).toBeLessThanOrEqual(844);
});
