// [Sync] 2026-10-30: keep exact accessible navigation names while qualifying native icon guidance and local theme status.
// [Input] Production sidebar/layout/Modal and native More presentation with existing navigation callbacks.
// [Output] Narrow five-peer menu, desktop preservation, close/focus/draft and exact destination intents.
// [Pos] Provider-free presentation fixture; no real account, database, model or business mutation.
// Impact: route intent/theme presentation change; Project/Episode/Run/Hook/data and underlying draft remain unchanged.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import {AuthProvider} from '/app/_dream/contexts/AuthContext.tsx';
import {StoryWorkspaceSidebar} from '/app/_dream/components/story-workspace/layout/StoryWorkspaceSidebar.tsx';
import {StoryWorkspaceLayout} from '/app/_dream/components/story-workspace/layout/StoryWorkspaceLayout.tsx';
import MoreNative from '/app/_dream/components/story-workspace/layout/MoreNavigationPage.native.tsx';
import i18n from '/app/_dream/i18n.ts';import {initTheme} from '/app/_dream/utils/theme.ts';
import '/app/_dream/styles/tokens.css';import '/app/_dream/index.css';
const query=new URLSearchParams(location.search);await i18n.changeLanguage(query.get('lang')||'zh');initTheme();
const f=window.__moreFixture={paths:[],themes:0,closes:0};
function Harness(){const [path,setPath]=useState('/story-workspace/chat'),[draft,setDraft]=useState('Keep the current unsent input'),[collapsed,setCollapsed]=useState(false);
 const navigate=path=>{f.paths.push(path);setPath(path);};
 return query.has('native')?<div style={{height:'100dvh',display:'flex',flexDirection:'column'}}><MoreNative onNavigate={id=>f.paths.push(id)} onToggleTheme={()=>f.themes++} onClose={()=>f.closes++}/></div>
 :<AuthProvider><StoryWorkspaceLayout sidebar={<StoryWorkspaceSidebar collapsed={collapsed} currentPath={path} onNavigate={navigate} onToggleCollapse={()=>setCollapsed(v=>!v)}/> }>
 <textarea aria-label="Existing unsent input" value={draft} onChange={e=>setDraft(e.target.value)}/><output aria-label="Current route">{path}</output>
 </StoryWorkspaceLayout></AuthProvider>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const errors=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 const root=fileURLToPath(new URL('../',import.meta.url));
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-more-narrow-navigation-20261029/vite',optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next','react-icons/fa']},resolve:{alias:[{find:/^react-native$/,replacement:'react-native-web'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'more-navigation-fixture',enforce:'pre',resolveId(id){if(id==='/more-entry.tsx')return '\0more-entry';},async load(id){if(id==='\0more-entry')return transformWithEsbuild(entry,'more-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/more-navigation')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/more-navigation','<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0;height:100dvh"><div id="root" style="height:100%"></div><script type="module" src="/more-entry.tsx"></script></body></html>'));});}}]});await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('MORE_FIXTURE_LISTENER');base='http://127.0.0.1:'+address.port+'/more-navigation';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const list:string[]=[];errors.set(page,list);page.on('pageerror',e=>list.push(e.message));page.on('console',m=>{if(m.type()==='error')list.push(m.text());});await page.route('**/auth/session',route=>route.fulfill({json:{user:{id:'1',email:'more@example.invalid',display_name:'Fixture reader',avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}}));await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.fallback():route.abort());});
test.afterEach(async({page})=>{expect(errors.get(page)).toEqual([]);});
const nav=(page:Page)=>page.getByRole('navigation',{name:'Story Workspace 导航',exact:true});
const more=(page:Page)=>nav(page).getByRole('button',{name:'更多',exact:true});
async function open(page:Page,width=390,lang='zh'){await page.setViewportSize({width,height:844});await page.goto(base+'?lang='+lang);await expect(page.getByRole('textbox',{name:'Existing unsent input',exact:true})).toHaveValue('Keep the current unsent input');}
test('narrow Web More is one full-page menu with five ordered peer entries',async({page})=>{
 await open(page);await more(page).click();const dialog=page.getByRole('dialog',{name:'更多',exact:true});await expect(dialog).toBeVisible();const list=dialog.getByRole('navigation',{name:'更多',exact:true});await expect(list.getByRole('button')).toHaveText(['写作','时间线','回顾','主题','设置']);
 const box=await dialog.boundingBox();expect(box).not.toBeNull();expect(box!.x).toBe(0);expect(box!.y).toBe(0);expect(box!.width).toBe(390);expect(box!.height).toBe(844);await page.screenshot({path:'/tmp/ink-more-narrow-navigation-20261029/web-more-zh-light.png'});
 await expect(nav(page).getByRole('group',{name:'更多',exact:true})).toHaveCount(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await dialog.getByRole('button',{name:'关闭',exact:true}).click();await expect(dialog).toHaveCount(0);await expect(more(page)).toBeFocused();await expect(page.getByRole('textbox',{name:'Existing unsent input',exact:true})).toHaveValue('Keep the current unsent input');
});
test('narrow destinations use original routes; theme retains the original action on the same menu',async({page})=>{
 await open(page);
 for(const [name,path] of [['写作','/story-workspace/writing'],['时间线','/story-workspace/timeline'],['回顾','/story-workspace/analysis'],['设置','/story-workspace/settings']]){
  await more(page).click();await page.getByRole('dialog',{name:'更多',exact:true}).getByRole('button',{name,exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('status',{name:'Current route',exact:true})).toHaveText(path);
 }
 await more(page).click();const theme=page.getByRole('dialog',{name:'更多',exact:true}).getByRole('button',{name:'主题',exact:true});await theme.click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await expect(page.getByRole('dialog')).toBeVisible();await page.screenshot({path:'/tmp/ink-more-narrow-navigation-20261029/web-more-zh-dark.png'});await theme.click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 expect(await page.evaluate(()=>(window as any).__moreFixture.paths)).toEqual(['/story-workspace/writing','/story-workspace/timeline','/story-workspace/analysis','/story-workspace/settings']);
});
test('desktop More keeps its existing disclosure, theme and Settings while resize closes only narrow menu',async({page})=>{
 await open(page,1280,'en');const button=nav(page).getByRole('button',{name:'More',exact:true});await button.click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(nav(page).getByRole('group',{name:'More',exact:true}).getByRole('button')).toHaveText(['Writing','Timeline','Reflections']);await expect(page.getByRole('button',{name:'设置',exact:true})).toBeVisible();await expect.poll(()=>nav(page).getByRole('group',{name:'More',exact:true}).evaluate(el=>getComputedStyle(el).opacity)).toBe('1');await page.screenshot({path:'/tmp/ink-more-narrow-navigation-20261029/web-more-desktop-en.png'});
 await page.setViewportSize({width:390,height:844});await nav(page).getByRole('button',{name:'More',exact:true}).click();await expect(page.getByRole('dialog',{name:'More',exact:true})).toBeVisible();await page.screenshot({path:'/tmp/ink-more-narrow-navigation-20261029/web-more-en-light.png'});await page.setViewportSize({width:1280,height:844});await expect(page.getByRole('dialog')).toHaveCount(0);await expect(nav(page).getByRole('group',{name:'More',exact:true})).toBeVisible();await expect(page.getByRole('textbox',{name:'Existing unsent input'})).toHaveValue('Keep the current unsent input');
});
test('narrow keyboard close contains focus and restores the original input without navigation',async({page})=>{
 await open(page);await page.getByRole('textbox',{name:'Existing unsent input'}).fill('An unfinished message');await more(page).click();await expect(page.getByRole('button',{name:'关闭',exact:true})).toBeFocused();await page.keyboard.press('Shift+Tab');await expect(page.getByRole('dialog').getByRole('button',{name:'Logout',exact:true})).toBeFocused();await page.keyboard.press('Tab');await expect(page.getByRole('button',{name:'关闭',exact:true})).toBeFocused();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__moreFixture.paths)).toEqual([]);await expect(page.getByRole('textbox',{name:'Existing unsent input'})).toHaveValue('An unfinished message');
 await page.evaluate(()=>history.pushState({},'',location.pathname+'?lang=zh&navigation=1'));await more(page).click();await expect(page.getByRole('dialog')).toBeVisible();await page.goBack();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByRole('textbox',{name:'Existing unsent input'})).toHaveValue('An unfinished message');
});
test('native More renderer uses the same five peers and distinct navigation/theme callbacks',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto(base+'?native=1&lang=zh');expect(await page.getByRole('button').filter({hasNotText:'关闭'}).evaluateAll(nodes=>nodes.map(node=>node.getAttribute('aria-label')))).toEqual(['写作','时间线','回顾','主题','设置']);await expect(page.getByText('记下想法与日常点滴',{exact:true})).toBeVisible();
 for(const name of ['写作','时间线','回顾','主题','设置'])await page.getByRole('button',{name,exact:true}).click();await page.getByRole('button',{name:'关闭',exact:true}).click();expect(await page.evaluate(()=>(window as any).__moreFixture)).toEqual({paths:['writing','timeline','analysis','settings'],themes:1,closes:1});
 for(const [lang,width] of [['zh',390],['zh',320],['en',320]] as const){
  await page.setViewportSize({width,height:844});await page.goto(base+'?native=1&lang='+lang);const writing=page.getByRole('button',{name:lang==='zh'?'写作':'Writing',exact:true});await expect(writing).toBeVisible();
  const labels=lang==='zh'?['写作','时间线','回顾','主题','设置']:['Writing','Timeline','Reflections','Theme','Settings'];
  for(const name of labels){const button=page.getByRole('button',{name,exact:true});await expect(button.locator('svg').first()).toBeVisible();const box=await button.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(width);expect(box!.height).toBeGreaterThanOrEqual(44);}
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'/tmp/ink-more-layout-20261030/native-more-'+lang+'-'+width+'.png'});
 }

});
