// [Sync] 2026-10-31: await document departure on logout/session loss while retaining original public authentication semantics.
// [Input] Production SessionGate, original public session DTO and explicit HTTP/native completion boundaries.
// [Sync] 2026-11-03: qualify existing diagnostics CPU charts with opt-in synthetic counters, pause/resume/failure/release and unchanged business state.
// [Sync] 2026-11-02: prepare diagnostics visibility and same-manager leaf regressions; actual UIWindow/Modal/touch checks require Simulator.
// [Output] Home appears after login dismissal; foreground, cancellation and retry preserve the original session contract.
// [Pos] Provider-free technical fixture; actual UIKit sheet and normal-account login require target acceptance.
// Impact: login presentation changes; Thread, Project/Episode, artifacts, Run publication, Hook and real data remain unchanged.
// [Sync] 2026-11-01: qualify original startup errors, native details, unchanged copying and observer release.
// [Sync] 2026-11-02: reuse RN global and actual shared SVG paths for the themed preparation composition.
// [Sync] 2026-11-03: use controlled foreground time to qualify each one-second entry and retained business drafts.
// Technical impact: startup state/page changes; original authentication is preserved. Project/Episode,
// canonical artifacts, Run-private publication, after-turn Hook, PostgreSQL/API projection are out of scope.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {mkdirSync} from 'node:fs';
const root=fileURLToPath(new URL('../',import.meta.url));
const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import SessionGate from '/src/platform/SessionGate.native.tsx';
import AboutView from '/app/_dream/components/AboutView.native.tsx';
import {RuntimeDiagnosticsWindow} from '/src/components/RuntimeDiagnostics.native.tsx';
import {BackendRuntimeManager} from '/src/runtime/BackendRuntimeManager.ts';
import i18n from '/app/_dream/i18n.ts';await i18n.changeLanguage('zh');
window.__startupManager=BackendRuntimeManager;
window.__mountDiagnosticsLeaf=()=>{const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;display:flex;flex-direction:column';document.body.append(host);const leaf=createRoot(host);window.__sessionPlatform.onDiagnosticsDismiss=()=>{leaf.unmount();host.remove();delete window.__sessionPlatform.onDiagnosticsDismiss;};leaf.render(<RuntimeDiagnosticsWindow/>);};
const documents=window.__releaseDocuments={calls:0,hold:false,pending:[]};async function releaseDocuments(){documents.calls++;if(documents.hold)await new Promise(resolve=>documents.pending.push(resolve));}
function Home({logout,refresh,user}){const [about,setAbout]=useState(false),[draft,setDraft]=useState('');return <div style={{height:'100%',display:'flex',flexDirection:'column'}}><div style={{display:about?'none':'block'}}><h1>Native home</h1><span>{user.display_name}</span><input aria-label="Existing draft" value={draft} onChange={event=>setDraft(event.target.value)}/><button onClick={()=>setAbout(true)}>关于</button><button onClick={()=>void refresh()}>Refresh session</button><button onClick={()=>void logout().catch(()=>{})}>Logout</button></div>{about?<AboutView onBack={()=>setAbout(false)}/>:null}</div>;}
if(new URLSearchParams(location.search).has('cpu-fixture')){const label=document.createElement('div');label.textContent='CPU合成样本 · 隔离技术验证';label.style.cssText='position:fixed;top:0;right:0;background:#fff;color:#111;z-index:10000;pointer-events:none;font:12px sans-serif';document.body.append(label);}
createRoot(document.querySelector('#root')).render(<div style={{height:'100dvh',display:'flex',flexDirection:'column'}}><SessionGate beforeRelease={releaseDocuments}>{(logout,refresh,user)=><Home {...{logout,refresh,user}}/>}</SessionGate></div>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
type Facts={authenticated:boolean;reads:number;failed:boolean;logoutFails:boolean;logoutCalls:number;errors:string[];httpStatuses:{path:string;status:number}[];httpDiagnostics:{path:string;status:number}[]};
const facts=new WeakMap<Page,Facts>();
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',define:{global:'globalThis'},cacheDir:'/tmp/ink-mobile-startup-implementation-20261101/vite-session',optimizeDeps:{force:true,noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next','zod']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/session-platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'native-session-fixture',enforce:'pre',resolveId(id){if(id==='/session-entry.tsx')return '\0session-entry';},async load(id){return id==='\0session-entry'?(await transformWithEsbuild(entry,'session-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code:null;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-session')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-session','<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/session-entry.tsx"></script></body></html>'));});}}]});
 await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('SESSION_FIXTURE_LISTENER');base='http://127.0.0.1:'+address.port+'/native-session';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
 const f:Facts={authenticated:false,reads:0,failed:false,logoutFails:false,logoutCalls:0,errors:[],httpStatuses:[],httpDiagnostics:[]};facts.set(page,f);page.on('pageerror',error=>f.errors.push(error.message));page.on('console',message=>{if(message.type()!=='error')return;const match=message.text().match(/^Failed to load resource: the server responded with a status of (401|503) /);const path=new URL(message.location().url||'about:blank').pathname;if(match&&['/auth/session','/auth/logout'].includes(path))f.httpDiagnostics.push({path,status:Number(match[1])});else f.errors.push(message.text());});
 await page.route('**/auth/session',route=>{f.reads++;f.httpStatuses.push({path:'/auth/session',status:f.failed?503:f.authenticated?200:401});return f.failed?route.fulfill({status:503,json:{error:'Unavailable'}}):f.authenticated?route.fulfill({json:{user:{id:'7',email:'session@example.invalid',display_name:'Original account',avatar_url:null,role:'user',created_at:null},csrf_token:'s'.repeat(43)}}):route.fulfill({status:401,json:{error:'Unauthenticated'}});});
 await page.route('**/auth/logout',route=>{f.logoutCalls++;f.httpStatuses.push({path:'/auth/logout',status:f.logoutFails?503:200});if(!f.logoutFails)f.authenticated=false;return route.fulfill({status:f.logoutFails?503:200,json:f.logoutFails?{error:'Unavailable'}:{success:true}});});
});
test.afterEach(async({page})=>{const f=facts.get(page)!;expect(f.errors).toEqual([]);for(const item of f.httpDiagnostics)expect(f.httpStatuses).toContainEqual(item);});
async function open(page:Page){await page.goto(base);await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();}
async function freezeEntryClock(page:Page){
 await page.clock.install({time:new Date('2026-11-03T00:00:00Z')});
 await page.clock.pauseAt(new Date('2026-11-03T00:00:01Z'));
}
test('login confirmation opens native home after the sheet settles, with no foreground race',async({page})=>{
 await open(page);await page.getByRole('button',{name:'登录',exact:true}).click();expect(await page.evaluate(()=>(window as any).__sessionPlatform.presented)).toBe(1);facts.get(page)!.authenticated=true;
 await page.evaluate(()=>(window as any).__sessionPlatform.active());await expect(page.getByRole('heading',{name:'Native home'})).toHaveCount(0);expect(facts.get(page)!.reads).toBe(1);
 await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();await expect(page.getByText('Original account',{exact:true})).toBeVisible();expect(facts.get(page)!.reads).toBe(2);
});
test('closing the login sheet is silent cancellation and allows a new login',async({page})=>{
 await open(page);await page.getByRole('button',{name:'登录',exact:true}).click();await page.evaluate(()=>(window as any).__sessionPlatform.cancel());await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);expect(facts.get(page)!.reads).toBe(1);
 await page.getByRole('button',{name:'登录',exact:true}).click();expect(await page.evaluate(()=>(window as any).__sessionPlatform.presented)).toBe(2);facts.get(page)!.authenticated=true;await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
});
test('a failed login presentation can be retried through the same public session path',async({page})=>{
 await open(page);await page.getByRole('button',{name:'登录',exact:true}).click();await page.evaluate(()=>(window as any).__sessionPlatform.cancel('LOGIN_UNAVAILABLE'));await expect(page.getByRole('alert')).toHaveText('登录未完成，可重新打开登录页面。');
 await page.getByRole('button',{name:'重新登录',exact:true}).click();facts.get(page)!.authenticated=true;await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
});
test('session-read recovery and failed logout retain the original account ownership',async({page})=>{
 const f=facts.get(page)!;f.failed=true;await page.goto(base);await expect(page.getByRole('alert')).toHaveText('工作区暂时无法打开，请重试。');f.failed=false;f.authenticated=true;await page.getByRole('button',{name:'重试',exact:true}).click();await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 f.logoutFails=true;await page.getByRole('button',{name:'Logout',exact:true}).click();await expect.poll(()=>f.logoutCalls).toBe(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();f.logoutFails=false;await page.getByRole('button',{name:'Logout',exact:true}).click();await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();
});


test('logout waits for current document closure before the original revoke request',async({page})=>{
 const f=facts.get(page)!;f.authenticated=true;await page.goto(base);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.evaluate(()=>(window as any).__releaseDocuments.hold=true);await page.getByRole('button',{name:'Logout',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__releaseDocuments.calls)).toBe(1);expect(f.logoutCalls).toBe(0);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.evaluate(()=>{for(const release of (window as any).__releaseDocuments.pending.splice(0))release();});
 await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();expect(f.logoutCalls).toBe(1);
});
test('session loss closes existing documents before removing the current account view',async({page})=>{
 const f=facts.get(page)!;f.authenticated=true;await page.goto(base);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.evaluate(()=>(window as any).__releaseDocuments.hold=true);f.authenticated=false;await page.getByRole('button',{name:'Refresh session',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__releaseDocuments.calls)).toBe(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.evaluate(()=>{for(const release of (window as any).__releaseDocuments.pending.splice(0))release();});
 await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();expect(f.logoutCalls).toBe(0);
});

test('pending startup leaves diagnostics interactive and shares one native initialization',async({page})=>{
 await page.setViewportSize({width:390,height:844});const f=facts.get(page)!;f.authenticated=true;
 await page.goto(base+'?hold-runtime');await expect(page.getByText('正在准备',{exact:true})).toBeVisible();expect(f.reads).toBe(0);
 await expect(page.getByTestId('startup-artwork')).toBeVisible();
 await expect(page.getByTestId('startup-artwork').locator('svg')).toHaveAttribute('viewBox','0 0 1254 1254');
 await expect(page.getByTestId('startup-artwork').locator('path')).toHaveCount(7);
 await expect(page.getByTestId('startup-artwork').locator('image,rect,img')).toHaveCount(0);
 expect(await page.evaluate(()=>{const manager=(window as any).__startupManager;return manager.ensureStarted()===manager.ensureStarted();})).toBe(true);
 await page.getByRole('button',{name:'开发者控制页',exact:true}).click();await expect(page.getByRole('heading',{name:'开发者控制页'})).toBeVisible();await expect(page.getByText('正在启动',{exact:true})).toBeVisible();
 const updated=await page.evaluate(()=>(window as any).__startupManager.getSnapshot().updatedAt);
 await page.getByRole('button',{name:'刷新',exact:true}).click();await expect(page.getByText('状态已刷新',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>(window as any).__startupManager.getSnapshot().updatedAt)).toBe(updated);expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);expect(f.reads).toBe(0);
 await page.screenshot({path:'/tmp/ink-mobile-startup-implementation-20261101/startup-diagnostics-pending.png'});
 await page.evaluate(()=>(window as any).__sessionPlatform.settleRuntime());await expect(page.getByText('本地服务已就绪',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'开发者控制页'})).toBeVisible();await expect(page.getByRole('heading',{name:'Native home'})).toHaveCount(0);
 await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();await expect(page.getByText('诊断摘要已复制',{exact:true})).toBeVisible();
 const copied=await page.evaluate(()=>(window as any).__sessionPlatform.copies[0]);expect(copied).toContain('启动状态: ready');expect(copied).not.toContain('fixture-private');expect(copied).not.toContain('localhost');
 await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();expect(f.reads).toBe(1);expect(await page.evaluate(()=>(window as any).__sessionPlatform.listeners.size)).toBe(1);
 await expect(page.getByTestId('startup-artwork')).toHaveCount(0);
});

test('fast startup keeps the transparent entry visible for one second before the existing home',async({page})=>{
 await freezeEntryClock(page);facts.get(page)!.authenticated=true;await page.goto(base);
 await expect(page.getByTestId('startup-screen')).toBeVisible();
 await expect.poll(()=>facts.get(page)!.reads).toBe(1);
 await expect(page.getByRole('heading',{name:'Native home'})).toHaveCount(0);
 const artwork=page.getByTestId('startup-artwork');
 await expect(artwork).toHaveCSS('background-color','rgba(0, 0, 0, 0)');await expect(artwork).toHaveCSS('border-top-width','0px');
 await expect(artwork.locator('svg')).toHaveCSS('background-color','rgba(0, 0, 0, 0)');await expect(artwork.locator('image,rect,img')).toHaveCount(0);
 await page.clock.runFor(999);await expect(page.getByTestId('startup-screen')).toBeVisible();
 await page.clock.runFor(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await expect(page.getByTestId('startup-screen')).toHaveCount(0);
 expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('each background return presents one second while retaining the existing home and draft',async({page})=>{
 await freezeEntryClock(page);facts.get(page)!.authenticated=true;await page.goto(base);await expect(page.getByTestId('startup-screen')).toBeVisible();
 await expect.poll(()=>facts.get(page)!.reads).toBe(1);await expect.poll(()=>page.evaluate(()=>(window as any).__startupManager.getSnapshot().sessionRead?.state)).toBe('available');await page.clock.runFor(1000);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.getByRole('textbox',{name:'Existing draft'}).fill('保留已有输入');
 for(let entry=0;entry<2;entry++){
  const readsBefore=facts.get(page)!.reads;
  await page.evaluate(()=>(window as any).__sessionPlatform.change('background'));await page.clock.runFor(5000);
  await page.evaluate(()=>(window as any).__sessionPlatform.active());await expect(page.getByTestId('startup-screen')).toBeVisible();
  await expect.poll(()=>facts.get(page)!.reads).toBe(readsBefore+1);await expect.poll(()=>page.evaluate(()=>(window as any).__startupManager.getSnapshot().sessionRead?.state)).toBe('available');
  await expect(page.getByRole('heading',{name:'Native home'})).toHaveCount(0);
  await page.clock.runFor(999);await expect(page.getByTestId('startup-screen')).toBeVisible();
  await page.clock.runFor(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Existing draft'})).toHaveValue('保留已有输入');
 }
 await page.evaluate(()=>{(window as any).__sessionPlatform.change('inactive');(window as any).__sessionPlatform.active();});
 await expect(page.getByTestId('startup-screen')).toHaveCount(0);
 expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('initial native state becoming active before effects still completes the entry timer',async({page})=>{
 await freezeEntryClock(page);facts.get(page)!.authenticated=true;await page.goto(base+'?initial-state-unknown');
 await expect(page.getByTestId('startup-screen')).toBeVisible();await expect.poll(()=>facts.get(page)!.reads).toBe(1);
 await page.clock.runFor(999);await expect(page.getByTestId('startup-screen')).toBeVisible();
 await page.clock.runFor(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
});

test('opening diagnostics pauses the one-second presentation until its existing return action',async({page})=>{
 await freezeEntryClock(page);facts.get(page)!.authenticated=true;await page.goto(base);await expect(page.getByTestId('startup-screen')).toBeVisible();
 await expect.poll(()=>facts.get(page)!.reads).toBe(1);await page.clock.runFor(300);
 await page.getByRole('button',{name:'开发者控制页',exact:true}).click();await expect(page.getByRole('heading',{name:'开发者控制页'})).toBeVisible();
 await page.clock.runFor(5000);await page.getByRole('button',{name:'返回',exact:true}).click();
 await expect(page.getByTestId('startup-screen')).toBeVisible();await page.clock.runFor(699);await expect(page.getByTestId('startup-screen')).toBeVisible();
 await page.clock.runFor(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
});

test('failed startup exposes the original native cause without automatic restart or session traffic',async({page})=>{
 await page.goto(base+'?hold-runtime');await page.getByRole('button',{name:'开发者控制页',exact:true}).click();
 await page.evaluate(()=>(window as any).__sessionPlatform.settleRuntime({code:'RUNTIME_START_FAILED',message:'本机服务启动失败，请重试。',userInfo:{NSLocalizedDescription:'Error: listen EADDRINUSE: address already in use ::1:5173'},nativeStackIOS:['/private/container/native-startup-frame']}));
 await expect(page.getByText('启动失败',{exact:true})).toBeVisible();await expect(page.getByText('RUNTIME_START_FAILED',{exact:true})).toBeVisible();
 await expect(page.getByText(/Error: listen EADDRINUSE/)).toBeVisible();await expect(page.getByText(/\/private\/container\/native-startup-frame/)).toBeVisible();
 await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();const copied=await page.evaluate(()=>(window as any).__sessionPlatform.copies[0]);expect(copied).toContain('Error: listen EADDRINUSE: address already in use ::1:5173');expect(copied).toContain('/private/container/native-startup-frame');
 await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('本地服务启动失败，请关闭后重新打开应用。');await expect(page.getByRole('button',{name:'重试',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'重新登录',exact:true})).toHaveCount(0);
 await page.evaluate(()=>(window as any).__sessionPlatform.active());expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);expect(facts.get(page)!.reads).toBe(0);
});

test('error logs preserve Error message, stack and cause and retain only the latest error per source',async({page})=>{
 await open(page);await page.getByRole('button',{name:'开发者控制页',exact:true}).click();
 await page.evaluate(()=>{const manager=(window as any).__startupManager;manager.recordError('config',Error('older config error'));const error=new Error('password=original-value /private/config');Object.defineProperty(error,'cause',{value:Error('original cause')});manager.recordError('config',error);manager.recordError('catalog','original catalog error');});
 await expect(page.getByText(/password=original-value \/private\/config/)).toBeVisible();
 await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();const copied=await page.evaluate(()=>(window as any).__sessionPlatform.copies[0]);expect(copied).toContain('original cause');expect(copied).toContain('stack');expect(copied).toContain('original catalog error');expect(copied).not.toContain('older config error');
 expect(await page.evaluate(()=>Object.keys((window as any).__startupManager.getSnapshot().errors).sort())).toEqual(['catalog','config']);
});

test('diagnostic observation pauses in background and reads the latest startup result on return',async({page})=>{
 // SessionGate, pending artwork and the diagnostics page each own one AppState subscription.
 await page.goto(base+'?hold-runtime');await page.getByRole('button',{name:'开发者控制页',exact:true}).click();expect(await page.evaluate(()=>(window as any).__sessionPlatform.listeners.size)).toBe(3);
 await page.evaluate(()=>(window as any).__sessionPlatform.change('background'));await expect(page.getByText('观测已暂停，上次读取',{exact:true})).toBeVisible();
 await page.evaluate(()=>(window as any).__sessionPlatform.settleRuntime());await expect.poll(()=>page.evaluate(()=>(window as any).__startupManager.getSnapshot().state)).toBe('ready');await expect(page.getByText('正在启动',{exact:true})).toBeVisible();
 await page.evaluate(()=>(window as any).__sessionPlatform.active());await expect(page.getByText('本地服务已就绪',{exact:true})).toBeVisible();await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByTestId('startup-screen')).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__sessionPlatform.listeners.size)).toBe(1);expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('the same diagnostics leaf opens from About and preserves the original draft and copy recovery',async({page})=>{
 const f=facts.get(page)!;f.authenticated=true;await page.goto(base);await page.getByRole('textbox',{name:'Existing draft'}).fill('保留已有输入');await page.getByRole('button',{name:'关于',exact:true}).click();await page.getByRole('button',{name:'开发者控制页',exact:true}).click();await expect(page.getByRole('heading',{name:'开发者控制页'})).toBeVisible();
 const reads=f.reads;await page.evaluate(()=>(window as any).__sessionPlatform.copyFails=true);await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();await expect(page.getByText('复制失败，请重试。',{exact:true})).toBeVisible();
 await page.evaluate(()=>(window as any).__sessionPlatform.copyFails=false);await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();await expect(page.getByText('诊断摘要已复制',{exact:true})).toBeVisible();await page.getByRole('button',{name:'刷新',exact:true}).click();expect(f.reads).toBe(reads);
 for(const viewport of [{width:390,height:844},{width:1280,height:800}]){await page.setViewportSize(viewport);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const box=await page.getByRole('button',{name:'刷新',exact:true}).boundingBox();expect(box!.y+box!.height).toBeLessThanOrEqual(viewport.height);}
 await page.screenshot({path:'/tmp/ink-mobile-startup-implementation-20261101/startup-diagnostics-ready.png'});
 await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByRole('button',{name:'开发者控制页',exact:true})).toBeVisible();await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByRole('textbox',{name:'Existing draft'})).toHaveValue('保留已有输入');expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('session failure keeps the local runtime ready and diagnostic refresh does not replay the request',async({page})=>{
 const f=facts.get(page)!;f.failed=true;await page.goto(base);await expect(page.getByRole('alert')).toHaveText('工作区暂时无法打开，请重试。');await page.getByRole('button',{name:'开发者控制页',exact:true}).click();await expect(page.getByText('本地服务已就绪',{exact:true})).toBeVisible();await expect(page.getByText('原会话读取失败',{exact:true})).toBeVisible();const reads=f.reads;
 await page.getByRole('button',{name:'刷新',exact:true}).click();expect(f.reads).toBe(reads);await page.getByRole('button',{name:'返回',exact:true}).click();f.failed=false;f.authenticated=true;await page.getByRole('button',{name:'重试',exact:true}).click();await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('native account and registration failures reach the existing diagnostics without reissuing login',async({page})=>{
 await open(page);
 await page.evaluate(()=>{const platform=(window as any).__sessionPlatform;platform.accountError('google',{phase:'authorization-configuration',code:1,message:'OAuth callback mismatch'});platform.accountError('registration','AUTH_REGISTRATION_INCOMPLETE');platform.accountError('login',{domain:'NSURLErrorDomain',code:-1009,message:'The Internet connection appears to be offline.'});platform.accountError('unknown-source','discard this event');});
 await page.getByRole('button',{name:'开发者控制页',exact:true}).click();
 await expect(page.getByText(/OAuth callback mismatch/)).toBeVisible();
 await expect(page.getByText(/AUTH_REGISTRATION_INCOMPLETE/)).toBeVisible();
 await expect(page.getByText(/NSURLErrorDomain/)).toBeVisible();
 await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();
 const copied=await page.evaluate(()=>(window as any).__sessionPlatform.copies[0]);expect(copied).toContain('authorization-configuration');expect(copied).toContain('AUTH_REGISTRATION_INCOMPLETE');expect(copied).not.toContain('discard this event');
 expect(await page.evaluate(()=>(window as any).__sessionPlatform.presented)).toBe(0);expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

// These cases qualify the production JS/native-call boundary. UIKit window ordering,
// dragging, keyboard geometry and app-owned sheets remain separate Simulator checks.
test('diagnostics access follows login presentation, cancellation, original session and logout',async({page})=>{
 await open(page);
 const enabled=()=>page.evaluate(()=>(window as any).__sessionPlatform.diagnosticsConfigurations.at(-1)?.enabled);
 await expect.poll(enabled).toBe(false);
 await page.getByRole('button',{name:'登录',exact:true}).click();await expect.poll(enabled).toBe(true);
 await page.evaluate(()=>(window as any).__sessionPlatform.cancel());await expect.poll(enabled).toBe(false);
 await page.getByRole('button',{name:'登录',exact:true}).click();facts.get(page)!.authenticated=true;
 await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();await expect.poll(enabled).toBe(true);
 await page.evaluate(()=>(window as any).__appearanceFixture.systemChange('dark'));
 await expect.poll(()=>page.evaluate(()=>(window as any).__sessionPlatform.diagnosticsConfigurations.at(-1)?.background)).toBe('#1f1b16');
 await expect(page.getByText('Original account',{exact:true})).toBeVisible();expect(facts.get(page)!.reads).toBe(2);
 await page.getByRole('button',{name:'Logout',exact:true}).click();await expect.poll(enabled).toBe(false);
 expect(facts.get(page)!.logoutCalls).toBe(1);expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('the native window leaf reuses the original snapshot and closes without replacing business state',async({page})=>{
 const f=facts.get(page)!;f.authenticated=true;await page.goto(base);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.getByRole('textbox',{name:'Existing draft'}).fill('窗口返回保留输入');const reads=f.reads;
 const observers=await page.evaluate(()=>(window as any).__sessionPlatform.listeners.size);
 await page.evaluate(()=>{(window as any).__startupManager.recordError('recovery','APP05 synthetic recovery failure');(window as any).__mountDiagnosticsLeaf();});
 await expect(page.getByRole('heading',{name:'开发者控制页'})).toBeVisible();await expect(page.getByText(/输入恢复 ·/)).toBeVisible();
 await expect(page.getByText('APP05 synthetic recovery failure',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'刷新',exact:true}).click();await expect(page.getByText('状态已刷新',{exact:true})).toBeVisible();
 await page.evaluate(()=>(window as any).__sessionPlatform.copyFails=true);await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();await expect(page.getByText('复制失败，请重试。',{exact:true})).toBeVisible();
 await page.evaluate(()=>(window as any).__sessionPlatform.copyFails=false);await page.getByRole('button',{name:'复制诊断摘要',exact:true}).click();await expect(page.getByText('诊断摘要已复制',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>(window as any).__sessionPlatform.copies.at(-1))).toContain('APP05 synthetic recovery failure');
 await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByRole('heading',{name:'开发者控制页'})).toHaveCount(0);
 await expect(page.getByRole('textbox',{name:'Existing draft'})).toHaveValue('窗口返回保留输入');
 expect(await page.evaluate(()=>(window as any).__sessionPlatform.diagnosticsDismissals)).toBe(1);
 await expect.poll(()=>page.evaluate(()=>(window as any).__sessionPlatform.listeners.size)).toBe(observers);
 expect(f.reads).toBe(reads);expect(f.logoutCalls).toBe(0);expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);
});

test('CPU charts use measured fixture intervals and preserve original state through pause, background and return',async({page})=>{
 const f=facts.get(page)!;f.authenticated=true;await page.clock.install();await page.setViewportSize({width:390,height:1500});
 await page.goto(base+'?cpu-fixture');await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 await page.getByRole('textbox',{name:'Existing draft'}).fill('CPU观察保留原输入');await page.getByRole('button',{name:'关于',exact:true}).click();await page.getByRole('button',{name:'开发者控制页',exact:true}).click();
 await expect(page.getByText('等待两个连续实际样本建立区间，暂停或读取失败处保留断点。',{exact:true})).toBeVisible();
 const reads=f.reads;await page.clock.fastForward(2100);await expect(page.getByText(/App CPU 25.0%/)).toBeVisible();await expect(page.getByText('共享或未归因，CPU未计量',{exact:true})).toBeVisible();await expect(page.getByTestId('runtime-cpu-chart').locator('circle')).toHaveCount(1);await page.clock.fastForward(2100);
 const outputs=process.env.APP05_PERFORMANCE_ARTIFACTS??'/tmp/ink-app05-cpu-20261103';mkdirSync(outputs,{recursive:true});await page.screenshot({path:outputs+'/cpu-fixture-light.png'});
 await page.evaluate(()=>(window as any).__appearanceFixture.systemChange('dark'));await page.screenshot({path:outputs+'/cpu-fixture-dark.png'});
 await page.getByRole('button',{name:'暂停采样',exact:true}).click();const calls=await page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls);await page.clock.fastForward(10000);expect(await page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls)).toBe(calls);
 await page.getByRole('button',{name:'恢复采样',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls)).toBe(calls+1);
 await page.evaluate(()=>(window as any).__sessionPlatform.change('background'));await expect(page.getByText('后台暂停采样',{exact:true})).toBeVisible();const background=await page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls);await page.clock.fastForward(8000);expect(await page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls)).toBe(background);
 await page.evaluate(()=>(window as any).__sessionPlatform.active());await expect.poll(()=>page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls)).toBe(background+1);
 await page.getByRole('button',{name:'返回',exact:true}).click();const closed=await page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls);await page.clock.fastForward(8000);expect(await page.evaluate(()=>(window as any).__sessionPlatform.cpuCalls)).toBe(closed);
 await page.getByRole('button',{name:'返回',exact:true}).click();await expect(page.getByRole('textbox',{name:'Existing draft'})).toHaveValue('CPU观察保留原输入');expect(f.logoutCalls).toBe(0);expect(await page.evaluate(()=>(window as any).__sessionPlatform.starts)).toBe(1);expect(f.reads).toBeGreaterThanOrEqual(reads);
});

test('CPU read failures remain explicit and recover without fabricated zero data',async({page})=>{
 facts.get(page)!.authenticated=true;await page.clock.install();await page.goto(base+'?cpu-fixture');await page.getByRole('button',{name:'关于',exact:true}).click();await page.getByRole('button',{name:'开发者控制页',exact:true}).click();await page.clock.fastForward(2100);
 await page.evaluate(()=>(window as any).__sessionPlatform.cpuFails=true);await page.clock.fastForward(2100);await expect(page.getByText(/采样读取失败/)).toBeVisible();await expect(page.getByText(/App CPU 25.0%/)).toBeVisible();
 await page.evaluate(()=>(window as any).__sessionPlatform.cpuFails=false);await page.clock.fastForward(2100);await expect(page.getByText('正在采样',{exact:true})).toBeVisible();await expect(page.getByText(/App CPU 未计量/)).toBeVisible();
 await page.clock.fastForward(2100);await expect(page.getByText(/App CPU 25.0%/)).toBeVisible();
});
