// [Input] Production Native Timeline, shared Web data state and original report/session/picture DTO fixtures.
// [Output] Read-only report/picture/comment navigation, read retry and retained-page evidence.
// [Pos] Explicit RNW/platform fixture; normal accounts, backend, database, CLI and models remain outside this lane.
// Impact: synthetic Reflections task/report only; Chat draft unchanged. Project/Episode/canonical artifacts,
// Run-private publication and after-turn Hook are out of scope. HTTP fixtures reuse the original Web harness.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {installReflectionFixtures,TASK_ID} from './fixtures/reflectionsHarness';
const root=fileURLToPath(new URL('../',import.meta.url));
const entry=String.raw`
import React,{useEffect,useState} from 'react';import {createRoot} from 'react-dom/client';
import Timeline from '/app/_dream/components/CollectionsView.native.tsx';
import {createNativeReflections} from '/src/platform/reflections.native.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
import '/app/_dream/styles/tokens.css';import '/app/_dream/index.css';
await i18n.changeLanguage(new URLSearchParams(location.search).get('lang')||'en');
await loadBrowserSession(async()=>Response.json({user:{id:'7',email:'timeline@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'s'.repeat(43)}));
window.__settingsFixture={uuidCalls:[]};const f=window.__nativeTimeline={backs:0};
function Harness(){const [shown,setShown]=useState(true),[draft,setDraft]=useState('Existing Chat draft');const [resource]=useState(()=>createNativeReflections('7'));useEffect(()=>()=>resource.dispose(),[resource]);
 return <div style={{height:'100dvh',display:'flex',flexDirection:'column'}}><textarea aria-label="Existing Chat draft" value={draft} onChange={event=>setDraft(event.target.value)}/><button onClick={()=>setShown(value=>!value)}>{shown?'Hide Timeline':'Show Timeline'}</button>
 <div style={{flex:1,minHeight:0,display:shown?'flex':'none',flexDirection:'column'}}><Timeline timezone="UTC" authenticated active={shown} api={resource.api} voiceConfigs={{reader:{name:'Original reader'}}} onBack={()=>{f.backs++;setShown(false);}}/></div></div>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
type HttpCall={path:string;method:string;body:any;headers:Record<string,string>};
const observed=new WeakMap<Page,HttpCall[]>();
test.beforeEach(async({page})=>{const calls:HttpCall[]=[];observed.set(page,calls);page.on('request',request=>{const url=new URL(request.url());if(!url.pathname.startsWith('/api/'))return;let body:unknown=null;try{body=request.postDataJSON();}catch{/* GET and empty-body requests keep null. */}calls.push({path:url.pathname+url.search,method:request.method(),body,headers:request.headers()});});});
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-more-app-navigation-20261029/vite-timeline',optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next','zod','ai']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/reflections-platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'native-timeline-fixture',enforce:'pre',resolveId(id){if(id==='/reflections-entry.tsx')return '\0reflections-entry';},async load(id){return id==='\0reflections-entry'?(await transformWithEsbuild(entry,'reflections-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code:null;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-timeline')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-timeline','<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/reflections-entry.tsx"></script></body></html>'));});}}]});await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('TIMELINE_FIXTURE_LISTENER');base='http://127.0.0.1:'+address.port+'/native-timeline';
});
test.afterAll(async()=>{await server?.close();});
async function open(page:Page,query=''){await page.clock.setFixedTime(new Date('2026-10-14T12:00:00Z'));await page.route('**/app/_dream/**',route=>route.continue());await page.route('**/node_modules/**',route=>route.continue());await page.setViewportSize({width:390,height:844});await page.goto(base+query);await expect(page.getByRole('heading',{name:'Timeline',exact:true})).toBeVisible();}
const pixel='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==';
async function timelineFixture(page:Page,options:Parameters<typeof installReflectionFixtures>[1]={}){
 const f=await installReflectionFixtures(page,options),reads:{path:string;method:string;body:unknown}[]=[];
 await page.route(/\/api\/(sessions\/(range|batch)|pictures\/range|pictures\/2026-10-13\/full)(?:\?|$)/,async route=>{const req=route.request(),url=new URL(req.url());let body:unknown=null;try{body=req.postDataJSON();}catch{}reads.push({path:url.pathname+url.search,method:req.method(),body});
  if(url.pathname==='/api/sessions/range')return route.fulfill({json:{sessions:[{id:'diary-reflection-1',date_key:'2026-10-13',first_line:'Original diary title',created_at:'2026-10-13T03:00:00Z',updated_at:'2026-10-13T03:00:00Z',editor_state:null,labels:[]}]}});
  if(url.pathname==='/api/pictures/range')return route.fulfill({json:{pictures:[{date:'2026-10-13',base64:pixel,prompt:'Historical drawing'}]}});
  if(url.pathname.endsWith('/full'))return route.fulfill({json:{image_base64:pixel}});
  if(url.pathname==='/api/sessions/batch')return route.fulfill({json:{sessions:[{id:'diary-reflection-1',created_at:'2026-10-13T03:00:00Z',updated_at:'2026-10-13T03:00:00Z',labels:[],editor_state:{id:'diary-reflection-1',createdAt:'2026-10-13T03:00:00Z',tasks:[],weightPath:[],overlappedPhrases:[],notFoundPhrases:[],cells:[],commentors:[{id:'comment1',voice:'reader',icon:'brain',color:'blue',feedback:'star',phrase:'rain',textSnapshot:'I watched the rain.',comment:'Original starred comment',appliedAt:Date.parse('2026-10-13T03:00:00Z'),computedAt:Date.parse('2026-10-13T03:00:00Z')}]}}]}});
 });
 return Object.assign(f,{reads});
}

test('native Timeline opens the original saved report and returns to the same list and Chat draft',async({page})=>{
 const f=await timelineFixture(page,{seedReport:true});await open(page);const report=page.getByRole('button',{name:/Open analysis created/});await expect(report).toHaveCount(1);await report.click();await expect(page.getByText('Diary scope · 1 entries',{exact:true})).toBeVisible();await page.getByRole('tab',{name:'Recurring Themes',exact:true}).click();await page.getByRole('button',{name:'Repeated concern',exact:true}).click();await expect(page.getByText('A stable provider-free reflection result.',{exact:true})).toBeVisible();await page.getByRole('button',{name:'← Timeline',exact:true}).click();await expect(report).toBeInViewport({ratio:1});await expect(page.getByRole('button',{name:'← More',exact:true})).toBeInViewport({ratio:1});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Existing Chat draft');expect(f.createRequests).toEqual([]);expect(f.startRequests).toEqual([]);expect(f.errors).toEqual([]);await page.screenshot({path:'/tmp/ink-more-app-navigation-20261029/native-timeline.png'});
});
test('native Timeline historical picture reads full image and applied comments through the original endpoints',async({page})=>{
 const f=await timelineFixture(page);await open(page);await page.getByRole('button',{name:'Historical drawing',exact:true}).click();await expect(page.getByText('Original starred comment',{exact:true})).toBeVisible();await expect(page.getByText('🧠 Original reader ⭐',{exact:true})).toBeVisible();expect(f.reads.find(read=>read.path==='/api/sessions/batch')).toMatchObject({method:'POST',body:{ids:['diary-reflection-1']}});expect(f.reads.some(read=>read.path==='/api/pictures/2026-10-13/full')).toBe(true);await page.getByRole('button',{name:'Close',exact:true}).click();await expect(page.getByText('Original starred comment')).toHaveCount(0);expect(f.createRequests).toEqual([]);expect(f.errors).toEqual([]);
});
test('native Timeline history failure retries the same read without generating analysis',async({page})=>{
 const f=await timelineFixture(page,{seedReport:true});f.historyReadFailureOnce=true;await open(page);await expect(page.getByRole('button',{name:'Analysis history could not be loaded. Retry',exact:true})).toHaveCount(1);await page.getByRole('button',{name:'Analysis history could not be loaded. Retry',exact:true}).click();await expect(page.getByRole('button',{name:/Open analysis created/})).toHaveCount(1);expect(f.historyRequests).toHaveLength(2);expect(f.historyRequests[0]).toBe(f.historyRequests[1]);expect(f.createRequests).toEqual([]);expect(f.startRequests).toEqual([]);expect(f.errors).toEqual([]);
});
test('native Timeline hide and menu return preserve the selected report and current list reads',async({page})=>{
 const f=await timelineFixture(page,{seedReport:true});await open(page);await page.getByRole('button',{name:/Open analysis created/}).click();await page.getByRole('button',{name:'Hide Timeline',exact:true}).click();await page.getByRole('button',{name:'Show Timeline',exact:true}).click();await expect(page.getByText('Diary scope · 1 entries',{exact:true})).toBeVisible();await page.getByRole('button',{name:'← Timeline',exact:true}).click();const count=f.reads.length;await page.getByRole('button',{name:'← More',exact:true}).click();await expect(page.getByRole('button',{name:'Show Timeline',exact:true})).toBeVisible();await page.getByRole('button',{name:'Show Timeline',exact:true}).click();expect(f.reads).toHaveLength(count);expect(await page.evaluate(()=>(window as any).__nativeTimeline.backs)).toBe(1);expect(f.createRequests).toEqual([]);expect(f.errors).toEqual([]);
});
