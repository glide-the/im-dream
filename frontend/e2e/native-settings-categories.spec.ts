// [Input] Original Web/native Memory responses, strict Product API and About production pages.
// [Output] Save/receipt/CAS/owner/abort recovery and read-only subscription/link parity evidence.
// [Pos] Explicit HTTP/platform fixture; no real account, database, model or App runtime acceptance.
// Impact: synthetic settings commands only; original auth, permission and task lifecycle remain.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import MemoryNative from '/app/_dream/views/story-workspace/MemoryBehaviorSettings.native.tsx';
import MemoryWeb from '/app/_dream/views/story-workspace/MemoryBehaviorSettings.tsx';
import SubscriptionNative from '/app/_dream/views/story-workspace/StoryWorkspaceSubscriptionPage.native.tsx';
import {StoryWorkspaceSubscriptionPage as SubscriptionWeb} from '/app/_dream/views/story-workspace/StoryWorkspaceSubscriptionPage.tsx';
import AboutNative from '/app/_dream/components/AboutView.native.tsx';import AboutWeb from '/app/_dream/components/AboutView.tsx';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
import '/app/_dream/styles/tokens.css';import '/app/_dream/index.css';
const query=new URLSearchParams(location.search),web=query.has('web');await i18n.changeLanguage(query.get('lang')||'zh');
await loadBrowserSession(async()=>Response.json({user:{id:'7',email:'settings@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'c'.repeat(43)}));
import {memorySnapshot as initial,subscriptionContext as context,subscriptionPlans as plans,timestamp} from '/e2e/native/settings-fixture-data.ts';
const f=window.__settingsFixture={calls:[],uuidCalls:[],expirations:0,links:[],linkFailure:false,mode:query.get('mode')||'normal',subscriptionStatus:200,receiptStatus:200,receiptPending:false,invalidProduct:false,emptyProduct:false,
 snapshot:JSON.parse(localStorage.getItem('ink-settings-fixture:server')||'null')||initial};
async function transport(input,init={}){
 const path=new URL(String(input),location.origin).pathname,method=init.method||'GET',body=init.body?JSON.parse(init.body):null;
 f.calls.push({path,method,body,headers:Object.fromEntries(new Headers(init.headers))});
 if(path==='/api/memory/behavior'&&method==='GET'){if(f.mode==='read-fail')return Response.json({detail:'unavailable'},{status:503});if(f.mode==='unauthorized')return Response.json({detail:'expired'},{status:401});return Response.json(f.snapshot);}
 if(path==='/api/memory/behavior'&&method==='PUT'){
  if(f.mode==='unauthorized')return Response.json({detail:'expired'},{status:401});
  if(f.mode==='conflict'){f.snapshot={...f.snapshot,revision:f.snapshot.revision+1};return Response.json({detail:{outcome_unknown:false}},{status:409});}
  f.snapshot={...f.snapshot,revision:f.snapshot.revision+1,desired:body.desired,updated_at:timestamp};localStorage.setItem('ink-settings-fixture:server',JSON.stringify(f.snapshot));
  if(f.mode==='deferred')return await new Promise(resolve=>{f.finish=()=>resolve(Response.json(f.snapshot));init.signal?.addEventListener('abort',()=>{f.aborted=true;},{once:true});});
  if(f.mode==='disconnected')throw Error('fixture disconnect');
  if(f.mode==='unknown')return Response.json({detail:{outcome_unknown:true}},{status:503});
  return Response.json(f.snapshot);
 }
 if(path.startsWith('/api/memory/behavior/receipt/'))return Response.json({status:f.receiptPending?'pending':'committed',result:f.receiptPending?null:f.snapshot},{status:f.receiptStatus});
 if(path.includes('/api/story-workspace/subscription/')){
  if(f.subscriptionStatus!==200)return Response.json({error:{code:'PRODUCT_DEPENDENCY_UNAVAILABLE',message:'fixture unavailable',details:{retryable:true}},meta:{requestId:'error_fixture'}},{status:f.subscriptionStatus});
  if(f.invalidProduct)return Response.json({data:'invalid',meta:{}});
  if(path.endsWith('/context'))return Response.json(f.emptyProduct?{...context,data:{...context.data,subscription:null,planVersion:null,allowance:null}}:context);
  if(path.endsWith('/plans'))return Response.json(f.emptyProduct?{...plans,data:[],meta:{...plans.meta,total:0}}:plans);
 }
 throw Error('UNEXPECTED_SETTINGS_HTTP '+method+' '+path);
}
const originalFetch=globalThis.fetch;globalThis.fetch=(input,init)=>String(input).includes('/api/memory/behavior')||String(input).includes('/api/story-workspace/subscription/')?transport(input,init):originalFetch(input,init);
function Harness(){const [page,setPage]=useState(query.get('page')||'memory'),[memoryMounted,setMemoryMounted]=useState(true),[draft,setDraft]=useState('Unsent Chat draft');
 const expired=()=>f.expirations++;return <div style={{height:'100dvh',display:'flex',flexDirection:'column'}}>
 <textarea aria-label="Existing Chat draft" value={draft} onChange={event=>setDraft(event.target.value)}/>
 <div><button onClick={()=>{setMemoryMounted(true);setPage('memory');}}>Open memory</button><button onClick={()=>setPage('subscription')}>Open subscription</button><button onClick={()=>setPage('about')}>Open about</button><button onClick={()=>{setMemoryMounted(false);setPage('home');}}>Unmount memory</button></div>
 <div style={{display:page==='memory'?'flex':'none',flexDirection:'column',flex:1,minHeight:0}}>{memoryMounted?(web?<MemoryWeb/>:<MemoryNative transport={transport} onBack={()=>setPage('home')} onSessionExpired={expired}/>):null}</div>
 {page==='subscription'?<div style={{display:'flex',flexDirection:'column',flex:1,minHeight:0}}>{web?<SubscriptionWeb/>:<SubscriptionNative transport={transport} onBack={()=>setPage('home')} onSessionExpired={expired}/>}</div>:null}
 {page==='about'?<div style={{display:'flex',flexDirection:'column',flex:1,minHeight:0}}>{web?<AboutWeb/>:<AboutNative onBack={()=>setPage('home')} openLink={async url=>{f.links.push(url);if(f.linkFailure)throw Error('fixture link failure');}}/>}</div>:null}
 </div>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-settings-categories-20261029/vite',optimizeDeps:{force:true,noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next','zod']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/settings-platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'native-settings-fixture',enforce:'pre',resolveId(id){if(id==='/settings-entry.tsx')return '\0settings-entry';},async load(id){return id==='\0settings-entry'?(await transformWithEsbuild(entry,'settings-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code:null;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-settings')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-settings','<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0;height:100dvh"><div id="root" style="height:100%"></div><script type="module" src="/settings-entry.tsx"></script></body></html>'));});}}]});await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('SETTINGS_FIXTURE_LISTENER');base='http://127.0.0.1:'+address.port+'/native-settings';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.setViewportSize({width:390,height:844});});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
async function open(page:Page,query=''){await page.goto(base+query);await expect(page.getByRole('heading',{name:'记忆回应',exact:true})).toBeVisible();}
async function calls(page:Page){return page.evaluate(()=>(window as any).__settingsFixture.calls as {path:string;method:string;body:any;headers:Record<string,string>}[]);}
async function mode(page:Page,value:string){await page.evaluate(value=>(window as any).__settingsFixture.mode=value,value);}
const enabled=(page:Page)=>page.getByRole('switch',{name:'使用回顾记忆调整回应',exact:true});
async function save(page:Page){await enabled(page).check();await page.getByRole('button',{name:'保存',exact:true}).click();}
const writes=async(page:Page)=>(await calls(page)).filter(call=>call.method==='PUT');
test('native memory saves original desired/revision and CSRF, with catalog-only actions and durable reopen',async({page})=>{
 await open(page);await expect(enabled(page)).not.toBeChecked();await enabled(page).check();await page.getByRole('button',{name:'压力 回应方式',exact:true}).click();await page.getByRole('radio',{name:'先回应感受，再提供帮助',exact:true}).click();await expect(page.getByRole('button',{name:'压力 回应方式',exact:true})).toHaveText('先回应感受，再提供帮助');await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByText('已保存，下一次回应使用此设置。',{exact:true})).toBeVisible();
 const put=(await writes(page))[0];expect(put.body.expected_revision).toBe(0);expect(put.body.desired.themes.THEME_PRESSURE.action).toBe('acknowledge_then_help');expect(put.headers['x-request-id']).toMatch(/^[0-9a-f-]{36}$/);expect(put.headers['x-ink-csrf']).toHaveLength(43);expect(put.headers.authorization).toBeUndefined();
 await page.reload();await expect(enabled(page)).toBeChecked();await expect(page.getByRole('button',{name:'压力 回应方式'})).toHaveText('先回应感受，再提供帮助');expect(await writes(page)).toHaveLength(0);await page.screenshot({path:'/tmp/ink-native-settings-categories-20261029/native-memory.png'});
});
test('native memory unknown save survives reload and resolves through the original receipt without another PUT',async({page})=>{
 await open(page,'?mode=unknown');await save(page);await expect(page.getByRole('alert')).toContainText('尚未核实');expect(await writes(page)).toHaveLength(1);await page.reload();await expect(page.getByRole('button',{name:'核实保存结果',exact:true})).toBeVisible();await page.getByRole('button',{name:'核实保存结果',exact:true}).click();await expect(page.getByText('已保存，下一次回应使用此设置。',{exact:true})).toBeVisible();expect(await writes(page)).toHaveLength(0);expect((await calls(page)).filter(c=>c.path.includes('/receipt/'))).toHaveLength(1);
});
test('native memory retries exactly the original command ID/body after disconnect',async({page})=>{
 await open(page,'?mode=disconnected');await save(page);await expect(page.getByRole('alert')).toContainText('连接中断');const original=(await writes(page))[0];await mode(page,'normal');await page.getByRole('button',{name:'重试这次保存',exact:true}).click();await expect(page.getByText('已保存，下一次回应使用此设置。',{exact:true})).toBeVisible();const put=await writes(page);expect(put).toHaveLength(2);expect(put[1]).toEqual(original);
});
test('native memory conflict retains the draft and adopts only the new revision before explicit save',async({page})=>{
 await open(page,'?mode=conflict');await save(page);await expect(page.getByRole('alert')).toContainText('草稿已保留');await expect(enabled(page)).toBeChecked();expect((await writes(page))[0].body.expected_revision).toBe(0);await mode(page,'normal');await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByText('已保存，下一次回应使用此设置。',{exact:true})).toBeVisible();expect((await writes(page))[1].body.expected_revision).toBe(1);
});
test('native memory read retry and expired session preserve the existing Chat draft',async({page})=>{
 await open(page,'?mode=read-fail');await expect(page.getByRole('alert')).toContainText('暂时无法读取');await mode(page,'unauthorized');await page.getByRole('button',{name:'重新读取',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__settingsFixture.expirations)).toBe(1);await mode(page,'normal');await page.getByRole('button',{name:'重新读取',exact:true}).click();await expect(enabled(page)).toBeVisible();await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Unsent Chat draft');expect(await writes(page)).toEqual([]);
});
test('native memory device storage failure prevents a PUT and retains the desired draft',async({page})=>{
 await open(page);await page.evaluate(()=>(window as any).__appearanceFixture.storageFailure=true);await save(page);await expect(page.getByRole('alert')).toContainText('保存请求未发出');expect(await writes(page)).toEqual([]);await expect(enabled(page)).toBeChecked();await expect(page.getByRole('button',{name:'保存',exact:true})).toBeEnabled();
});
test('native memory unmount aborts the reader while preserving an uncertain command for remount',async({page})=>{
 await open(page,'?mode=deferred');await save(page);await expect.poll(async()=>(await writes(page)).length).toBe(1);await page.getByRole('button',{name:'Unmount memory',exact:true}).click();expect(await page.evaluate(()=>(window as any).__settingsFixture.aborted)).toBe(true);await page.evaluate(()=>(window as any).__settingsFixture.finish());await page.getByRole('button',{name:'Open memory',exact:true}).click();await expect(page.getByRole('button',{name:'核实保存结果',exact:true})).toBeVisible();expect(await writes(page)).toHaveLength(1);await page.getByRole('button',{name:'核实保存结果',exact:true}).click();await expect(page.getByText('已保存，下一次回应使用此设置。',{exact:true})).toBeVisible();
});
test('native memory absent receipt retains retry ownership and explicit current read clears only the pending command',async({page})=>{
 await open(page,'?mode=unknown');await save(page);await page.evaluate(()=>(window as any).__settingsFixture.receiptPending=true);await page.getByRole('button',{name:'核实保存结果',exact:true}).click();await expect(page.getByRole('alert')).toContainText('尚未找到保存回执');await expect(page.getByRole('button',{name:'重试这次保存',exact:true})).toBeEnabled();await page.getByRole('button',{name:'读取最新设置',exact:true}).click();await expect(page.getByRole('button',{name:'重试这次保存',exact:true})).toHaveCount(0);await expect(enabled(page)).toBeChecked();expect(await writes(page)).toHaveLength(1);
});
test('native memory pending records are ignored when a different owner loads',async({page})=>{
 await open(page,'?mode=unknown');await save(page);await page.evaluate(()=>{const f=(window as any).__settingsFixture;f.snapshot={...f.snapshot,owner_id:'8'};localStorage.setItem('ink-settings-fixture:server',JSON.stringify(f.snapshot));});await page.reload();await expect(enabled(page)).toBeChecked();await expect(page.getByRole('button',{name:'核实保存结果',exact:true})).toHaveCount(0);expect(await writes(page)).toEqual([]);expect((await calls(page)).some(c=>c.path.includes('/receipt/'))).toBe(false);
});
test('original Web memory uses the same save and receipt contract with unchanged DOM controls',async({page})=>{
 await open(page,'?web=1&mode=unknown');await page.getByRole('checkbox',{name:'使用回顾记忆调整回应'}).check();await page.getByRole('combobox',{name:'压力 回应方式'}).selectOption('acknowledge_then_help');await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByRole('alert')).toContainText('尚未核实');await page.reload();await page.getByRole('button',{name:'核实保存结果',exact:true}).click();await expect(page.getByRole('status')).toContainText('已保存');await expect(page.getByRole('combobox',{name:'压力 回应方式'})).toHaveValue('acknowledge_then_help');expect(await writes(page)).toEqual([]);
});
test('native subscription reads the strict original context/plans, shows three panels and has no purchase entry',async({page})=>{
 await open(page);await page.getByRole('button',{name:'Open subscription',exact:true}).click();await expect(page.getByRole('heading',{name:'Free',exact:true}).first()).toBeVisible();await page.getByRole('tab',{name:'我的额度',exact:true}).click();await expect(page.getByRole('heading',{name:'75,000 Token',exact:true})).toBeVisible();await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow','24000');await page.getByRole('tab',{name:'可选套餐',exact:true}).click();await expect(page.getByText('暂不可开通',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:/购买|支付|开通|续费/})).toHaveCount(0);expect((await calls(page)).every(c=>c.method==='GET')).toBe(true);expect((await calls(page)).filter(c=>c.path.includes('/subscription/')).map(c=>c.path)).toEqual(['/api/story-workspace/subscription/context','/api/story-workspace/subscription/plans']);await page.screenshot({path:'/tmp/ink-native-settings-categories-20261029/native-subscription.png'});
});
test('native subscription retains the last snapshot on failed refresh and restores it through explicit retry',async({page})=>{
 await open(page);await page.getByRole('button',{name:'Open subscription',exact:true}).click();await expect(page.getByRole('heading',{name:'Free',exact:true}).first()).toBeVisible();await page.evaluate(()=>(window as any).__settingsFixture.subscriptionStatus=503);await page.getByRole('button',{name:'重新读取',exact:true}).click();await expect(page.getByRole('alert')).toContainText('订阅服务暂时不可用');await expect(page.getByRole('heading',{name:'Free',exact:true}).first()).toBeVisible();await page.evaluate(()=>(window as any).__settingsFixture.subscriptionStatus=200);await page.getByRole('button',{name:'重新读取',exact:true}).last().click();await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Unsent Chat draft');
});
test('native subscription schema failure shows no fabricated data; empty context/plans use existing empty states',async({page})=>{
 await open(page);await page.evaluate(()=>(window as any).__settingsFixture.invalidProduct=true);await page.getByRole('button',{name:'Open subscription',exact:true}).click();await expect(page.getByRole('alert')).toContainText('订阅服务暂时不可用');await expect(page.getByRole('heading',{name:'Free',exact:true})).toHaveCount(0);await page.evaluate(()=>{const f=(window as any).__settingsFixture;f.invalidProduct=false;f.emptyProduct=true;});await page.getByRole('button',{name:'重新读取',exact:true}).click();await expect(page.getByRole('heading',{name:'当前没有有效订阅',exact:true})).toBeVisible();await page.getByRole('tab',{name:'我的额度',exact:true}).click();await expect(page.getByRole('heading',{name:'额度暂不可用',exact:true})).toBeVisible();await page.getByRole('tab',{name:'可选套餐',exact:true}).click();await expect(page.getByRole('heading',{name:'暂时没有可选套餐',exact:true})).toBeVisible();expect((await calls(page)).every(c=>c.method==='GET')).toBe(true);
});
test('native subscription 401 calls original session refresh once per failed read batch',async({page})=>{
 await open(page);await page.evaluate(()=>(window as any).__settingsFixture.subscriptionStatus=401);await page.getByRole('button',{name:'Open subscription',exact:true}).click();await expect(page.getByRole('alert')).toBeVisible();await expect.poll(()=>page.evaluate(()=>(window as any).__settingsFixture.expirations)).toBe(1);expect((await calls(page)).every(c=>c.method==='GET')).toBe(true);
});
test('native About retains static content and opens only the original repository, with link retry feedback',async({page})=>{
 await open(page);await page.getByRole('button',{name:'Open about',exact:true}).click();for(const name of ['About the Project','The Team','Development Timeline','Links'])await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();for(const name of ['F2J','Sage','glide-the'])await expect(page.getByText(name,{exact:true})).toBeVisible();await page.evaluate(()=>(window as any).__settingsFixture.linkFailure=true);await page.getByRole('link',{name:'GitHub Repository',exact:true}).click();await expect(page.getByRole('alert')).toContainText('链接暂时无法打开');await page.evaluate(()=>(window as any).__settingsFixture.linkFailure=false);await page.getByRole('link',{name:'GitHub Repository',exact:true}).click();await expect(page.getByRole('alert')).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__settingsFixture.links)).toEqual(Array(2).fill('https://github.com/shuxueshuxue/ink-and-memory'));expect((await calls(page)).filter(c=>!c.path.includes('/memory/behavior'))).toEqual([]);await page.screenshot({path:'/tmp/ink-native-settings-categories-20261029/native-about.png'});
});
