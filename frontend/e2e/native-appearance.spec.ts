// [Sync] 2026-10-30: keep exact accessible navigation names while qualifying native icon guidance and local theme status.
// [Sync] 2026-10-29: use a physical platform alias during Vite dependency optimization; native Flow sources remain outside the browser harness.
// [Input] Production native theme store, iOS preference adapter, More and General settings renderers.
// [Output] Exact local/server ownership, explicit/system colors, preference recovery and unchanged draft evidence.
// [Pos] Isolated platform/HTTP fixture; UIKit, UserDefaults durability and ordinary App navigation require target acceptance.
// Impact: synthetic display preferences only; no real accounts, database, backend runtime, model or permissions changed.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import More from '/app/_dream/components/story-workspace/layout/MoreNavigationPage.native.tsx';
import General from '/app/_dream/views/story-workspace/GeneralSettings.native.tsx';
import useInkColors,{useNativeThemeMode} from '/src/components/useInkColors.native.ts';
import {initTheme,toggleTheme} from '/app/_dream/utils/theme.native.ts';
import {initInterfaceLanguage} from '/src/platform/interfacePreferences.native.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
initTheme();initInterfaceLanguage();
await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const f=window.__appearanceFixture;
async function transport(input,init={}){f.calls.push({path:String(input),method:init.method??'GET',body:JSON.parse(init.body||'null'),headers:Object.fromEntries(new Headers(init.headers))});if(f.networkFailure)throw Error('fixture disconnected');return Response.json({}, {status:f.status});}
function Harness(){const [page,setPage]=useState('more'),[draft,setDraft]=useState('Unsent Chat draft');const colors=useInkColors(),theme=useNativeThemeMode();
return <div style={{height:'100dvh',display:'flex',flexDirection:'column',background:colors['color-bg-app']}}>
<output aria-label="Theme snapshot">{JSON.stringify({theme,background:colors['color-bg-app'],language:i18n.language})}</output>
<textarea aria-label="Existing Chat draft" value={draft} onChange={event=>setDraft(event.target.value)}/>
<button onClick={()=>setPage('more')}>Open More</button>
<div style={{flex:1,minHeight:0,display:page==='more'?'flex':'none',flexDirection:'column'}}><More onNavigate={id=>{f.paths.push(id);if(id==='settings')setPage('general');}} onToggleTheme={()=>toggleTheme()} onClose={()=>setPage('chat')}/></div>
<div style={{flex:1,minHeight:0,display:page==='general'?'flex':'none',flexDirection:'column'}}><General transport={transport} onBack={()=>setPage('more')} onSessionExpired={()=>f.expirations++}/></div>
</div>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-appearance-settings-20261029/vite',optimizeDeps:{force:true,noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/appearance-platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{
  name:'native-appearance-platform-fixture',enforce:'pre',resolveId(id,importer){
   if(id==='/appearance-entry.tsx')return '\0appearance-entry';
   if(id.endsWith('/interfaceSettings')&&importer&&!importer.endsWith('interfaceSettings.ios.ts'))return root+'src/platform/interfaceSettings.ios.ts';
  },async load(id){const source=id==='\0appearance-entry'?entry:null;return source?(await transformWithEsbuild(source,'appearance-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code:null;},
  configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-appearance')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-appearance','<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0;height:100dvh"><div id="root" style="height:100%"></div><script type="module" src="/appearance-entry.tsx"></script></body></html>'));});}
 }]});await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('APPEARANCE_FIXTURE_LISTENER');base='http://127.0.0.1:'+address.port+'/native-appearance';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.setViewportSize({width:390,height:844});});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
async function open(page:Page,system='light'){await page.goto(base+'?system='+system);await expect(page.getByRole('button',{name:'Settings',exact:true})).toBeVisible();}
async function general(page:Page){await page.getByRole('button',{name:'Settings',exact:true}).click();await expect(page.getByRole('heading',{name:'General',exact:true})).toBeVisible();}
async function snapshot(page:Page){return JSON.parse(await page.getByRole('status',{name:'Theme snapshot'}).innerText());}
async function facts(page:Page){return page.evaluate(()=>{const f=(window as any).__appearanceFixture;return {calls:f.calls,writes:f.writes,expirations:f.expirations,paths:f.paths};});}

test('More keeps five peers and changes only the local theme while retaining the Chat draft',async({page})=>{
 await open(page);await page.getByRole('textbox',{name:'Existing Chat draft'}).fill('Keep this unfinished message');
 const items=page.getByRole('button').filter({hasNotText:/Open More|Close/});expect(await items.evaluateAll(nodes=>nodes.map(node=>node.getAttribute('aria-label')))).toEqual(['Writing','Timeline','Reflections','Theme','Settings']);await expect(page.getByRole('button',{name:'Theme',exact:true})).toContainText('Current: System · Light');
 await page.getByRole('button',{name:'Theme',exact:true}).click();expect(await snapshot(page)).toMatchObject({theme:'dark',background:'#1d1916'});await expect(page.getByRole('button',{name:'Theme',exact:true})).toContainText('Current: Dark');expect(await facts(page)).toMatchObject({calls:[],writes:[{'ink-theme':'dark'}]});
 await page.getByRole('button',{name:'Close',exact:true}).click();await expect(page.getByRole('button',{name:'Theme',exact:true})).toBeHidden();await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Keep this unfinished message');await page.getByRole('button',{name:'Open More',exact:true}).click();await expect(page.getByRole('button',{name:'Theme',exact:true})).toBeVisible();
 await page.reload();await expect(page.getByRole('button',{name:'Theme',exact:true})).toBeVisible();expect(await snapshot(page)).toMatchObject({theme:'dark',background:'#1d1916'});expect((await facts(page)).calls).toEqual([]);
});
test('system-dark and explicit-dark palettes remain distinct and system changes update mounted views',async({page})=>{
 await open(page,'dark');expect(await snapshot(page)).toMatchObject({theme:'system',background:'#1f1b16'});await general(page);await page.getByRole('radio',{name:'Dark',exact:true}).click();expect(await snapshot(page)).toMatchObject({theme:'dark',background:'#1d1916'});
 await page.evaluate(()=>(window as any).__appearanceFixture.systemChange('light'));expect(await snapshot(page)).toMatchObject({theme:'dark',background:'#1d1916'});await page.getByRole('radio',{name:'System',exact:true}).click();expect(await snapshot(page)).toMatchObject({theme:'system',background:'#f6efe5'});
 await page.evaluate(()=>(window as any).__appearanceFixture.systemChange('dark'));await expect.poll(async()=>(await snapshot(page)).background).toBe('#1f1b16');
});
test('General retains the exact theme PUT and CSRF; an uncertain save keeps the local choice with explicit feedback',async({page})=>{
 await open(page);await general(page);await page.evaluate(()=>(window as any).__appearanceFixture.status=503);await page.getByRole('radio',{name:'Dark',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Appearance is applied on this device. The account save could not be confirmed.');await expect(page.getByRole('radio',{name:'Dark',exact:true})).toBeChecked();
 const calls=(await facts(page)).calls;expect(calls).toHaveLength(1);expect(calls[0]).toMatchObject({path:'/api/system-config',method:'PUT',body:{theme:'dark'}});expect(calls[0].headers['x-ink-csrf']).toHaveLength(43);expect(calls[0].headers.authorization).toBeUndefined();
 await page.getByRole('button',{name:'Back',exact:true}).click();await expect(page.getByRole('button',{name:'Theme',exact:true})).toBeVisible();await general(page);await expect(page.getByRole('radio',{name:'Dark',exact:true})).toBeChecked();expect((await facts(page)).calls).toHaveLength(1);
 await page.evaluate(()=>(window as any).__appearanceFixture.status=200);await page.getByRole('radio',{name:'Light',exact:true}).click();await expect(page.getByRole('alert')).toHaveCount(0);expect((await facts(page)).calls.map((c:any)=>c.body)).toEqual([{theme:'dark'},{theme:'light'}]);
});
test('General 401 and network failure use existing session refresh without changing the local preference or draft',async({page})=>{
 await open(page);await general(page);await page.evaluate(()=>(window as any).__appearanceFixture.status=401);await page.getByRole('radio',{name:'Dark',exact:true}).click();await expect(page.getByRole('alert')).toBeVisible();expect((await facts(page)).expirations).toBe(1);await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Unsent Chat draft');
 await page.evaluate(()=>(window as any).__appearanceFixture.networkFailure=true);await page.getByRole('radio',{name:'Light',exact:true}).click();await expect(page.getByRole('alert')).toBeVisible();expect(await snapshot(page)).toMatchObject({theme:'light'});expect((await facts(page)).calls).toHaveLength(2);
});
test('language and Energy Bar retain local defaults, original keys and reload recovery without HTTP',async({page})=>{
 await open(page);await general(page);await expect(page.getByRole('switch',{name:'Toggle energy bar',exact:true})).toBeChecked();await page.getByRole('switch',{name:'Toggle energy bar',exact:true}).click();await page.getByRole('radio',{name:'中文 (Chinese)',exact:true}).click();await expect(page.getByRole('heading',{name:'常规',exact:true})).toBeVisible();
 expect((await facts(page)).calls).toEqual([]);expect((await facts(page)).writes).toEqual([{'show-energy-bar':'false'},{'ink-language':'zh'}]);await page.reload();await expect(page.getByRole('button',{name:'设置',exact:true})).toBeVisible();await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByRole('radio',{name:'中文',exact:true})).toBeChecked();await expect(page.getByRole('switch',{name:'切换能量条',exact:true})).not.toBeChecked();
});
test('preference storage failure prevents a config PUT and reports the local failure accurately',async({page})=>{
 await open(page);await general(page);await page.evaluate(()=>(window as any).__appearanceFixture.storageFailure=true);await page.getByRole('radio',{name:'Dark',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Display preference could not be saved. Please try again.');expect(await snapshot(page)).toMatchObject({theme:'system',background:'#f6efe5'});expect((await facts(page)).calls).toEqual([]);await page.getByRole('switch',{name:'Toggle energy bar',exact:true}).click();await expect(page.getByRole('switch',{name:'Toggle energy bar',exact:true})).toBeChecked();
});
test('invalid stored mode uses the original System default and external preference changes refresh mounted colors',async({page})=>{
 await page.addInitScript(()=>localStorage.setItem('ink-appearance-fixture:ink-theme',JSON.stringify('invalid-mode')));await open(page,'dark');expect(await snapshot(page)).toMatchObject({theme:'system',background:'#1f1b16'});await page.evaluate(()=>(window as any).__appearanceFixture.externalChange('ink-theme','light'));await expect.poll(async()=>(await snapshot(page)).background).toBe('#f6efe5');expect((await facts(page)).calls).toEqual([]);expect((await facts(page)).writes).toEqual([]);
});
test('More theme storage failure stays on the menu with feedback and no server write',async({page})=>{
 await open(page);await page.evaluate(()=>(window as any).__appearanceFixture.storageFailure=true);await page.getByRole('button',{name:'Theme',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Display preference could not be saved. Please try again.');await expect(page.getByRole('button',{name:'Settings',exact:true})).toBeVisible();expect(await snapshot(page)).toMatchObject({theme:'system'});expect((await facts(page)).calls).toEqual([]);await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Unsent Chat draft');
});
