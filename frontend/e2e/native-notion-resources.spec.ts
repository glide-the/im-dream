// [Input] Production native Notion controls, shared API/state and production-shaped intercepted DTOs.
// [Output] Native overview/Skill/file/resource/source journeys and server-confirmed selection recovery.
// [Pos] Provider-free technical browser qualification; Project/Episode/Run/Hook and real user/provider writes are outside scope.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';

const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import NativeNotion from '/app/_dream/components/dashboard/ConnectorNotionDetailPage.native.tsx';
import {createResourceConnectorApi} from '/app/_dream/api/resourceConnectorApi.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';
import i18n from '/app/_dream/i18n.ts';import '/app/_dream/styles/tokens.css';
await i18n.changeLanguage('zh');await loadBrowserSession();
const f=window.__nativeNotion={links:[],notifications:[],closed:0,active:true,linkFailure:false};
const listeners=new Set();const api=createResourceConnectorApi(globalThis.fetch,detail=>{f.notifications.push(detail);listeners.forEach(listener=>listener());});
const observation={hidden:()=>!f.active,subscribe(onRefresh,onVisible){listeners.add(onRefresh);f.visible=onVisible;return()=>{listeners.delete(onRefresh);};}};
function Harness(){const [active,setActive]=useState(true),[draft,setDraft]=useState('Unsent original Chat draft');return <div style={{height:'100dvh',display:'flex',flexDirection:'column'}}>
<textarea aria-label="Existing Chat draft" value={draft} onChange={event=>setDraft(event.target.value)}/><button onClick={()=>{f.active=!active;setActive(!active);f.visible?.();}}>Toggle resource page</button>
<div style={{display:active?'flex':'none',flex:1,minHeight:0,flexDirection:'column'}}><NativeNotion ownerId="20261029" active={active} api={api} observation={observation} onBack={()=>f.closed++} openLink={async url=>{f.links.push(url);if(f.linkFailure)throw Error('fixture open failed');}}/></div></div>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const errors=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 const root=fileURLToPath(new URL('../',import.meta.url));server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-settings-resources-20261029/vite-native-notion',define:{__DEV__:'false'},
  optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next','zod','react-markdown','remark-gfm','rehype-highlight']},
  resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/reflections-platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},
  plugins:[{name:'native-notion-fixture',enforce:'pre',resolveId(id){if(id==='/native-notion-entry.tsx')return '\0native-notion-entry';},async load(id){return id==='\0native-notion-entry'?(await transformWithEsbuild(entry,'native-notion-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code:null;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-notion')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-notion','<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/native-notion-entry.tsx"></script></body></html>'));});}}]});
 await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('NATIVE_NOTION_LISTENER');base=`http://127.0.0.1:${address.port}/native-notion`;
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const messages:string[]=[];errors.set(page,messages);page.on('pageerror',error=>messages.push(error.message));page.on('console',message=>{if(message.type()==='error'&&!/409 \(Conflict\)/.test(message.text()))messages.push(message.text());});await page.setViewportSize({width:390,height:844});});
test.afterEach(async({page})=>{expect(errors.get(page)).toEqual([]);});
const CSRF='n'.repeat(43),rule={enabled:true,interval_minutes:15,revision:1};
const descriptor={id:'file-search',relative_path:'references/search.md',media_type:'text/markdown',size_bytes:128};
async function fixtures(page:Page,{busy=false}={}){
 let selected=['db-old'],removed=false,saveBusy=busy;const writes:{path:string;method:string;body:any;headers:Record<string,string>}[]=[],reads:string[]=[],unexpected:string[]=[];
 const connector=()=>({id:'notion-native',name:'Notion Resource Connector',platform:'notion',auth_status:'authenticated',created_at:'2026-09-01T00:00:00Z',updated_at:'2026-10-29T00:00:00Z',last_synced_at:'2026-10-28T00:00:00Z',sources:selected.map(id=>({id:`source-${id}`,external_id:id,resource_type:'notion_database',title:id==='db-old'?'原有成功索引':'新增范围',sync_status:'synced',page_count:2,updated_at:'2026-10-28T00:00:00Z'})),sync_policy:{schema_version:1,default:rule,desired:rule,effective:rule,status:'applied',schedule_due:false,allowed_interval_minutes:[15,60]}});
 const skill={id:'native-skill',title:'Notion 工作空间助手',description:'原读取能力',source:'builtin',availability:'available'};
 await page.route('**/auth/session',route=>route.fulfill({json:{user:{id:'20261029',email:'native-notion@example.invalid',display_name:'Fixture reader',avatar_url:null,role:'user',created_at:null},csrf_token:CSRF}}));
 await page.route('**/api/**',async route=>{const request=route.request(),url=new URL(request.url()),path=url.pathname,method=request.method();if(!path.startsWith('/api/'))return route.continue();let body:any=null;try{body=request.postDataJSON();}catch{}
  if(method==='GET')reads.push(path);else writes.push({path,method,body,headers:request.headers()});
  if(path==='/api/connectors'&&method==='GET')return route.fulfill({json:{connectors:removed?[]:[connector()]}});
  if(path==='/api/connectors/notion/capabilities')return route.fulfill({json:{catalog:{schema_version:5,package_revision:'native-package-1',cli_installation:{status:'installed',required_version:'0.15.1',install_command:'npm install -g ntn@0.15.1'},mcp_inventory:{status:'not_integrated',revision:null,read_status:'not_integrated',write_status:'not_integrated'},skills:[skill],operations:[{id:'read-hook',title:'按需读取页面正文',description:'原按需读取',kind:'read',source:'runtime_hook',entrypoint:'apply_notion_page_read_redirect',availability:'available'},{id:'workspace-index',title:'挂载工作区轻量索引',description:'原轻量索引',kind:'write',source:'workspace_materializer',entrypoint:'materialize_workspace_snapshot',availability:'available'}]}}});
  if(path==='/api/connectors/notion/skills/native-skill')return route.fulfill({json:{package_revision:'native-package-1',skill:{...skill,tools:['Read'],body:'# 原 Skill\n\n不读取凭证。'},files:[descriptor]}});
  if(path==='/api/connectors/notion/skills/native-skill/files/file-search'){expect(url.searchParams.get('package_revision')).toBe('native-package-1');return route.fulfill({json:{package_revision:'native-package-1',file:{...descriptor,content:'# 原参考\n\n只读取已挂载索引。'}}});}
  if(path==='/api/connectors/notion-native/databases')return route.fulfill({json:{databases:Array.from({length:11},(_,index)=>({id:index===0?'db-old':`db-${index}`,title:index===0?'原有成功索引':`数据库 ${index}`,selected:index===0,page_count:2}))}});
  if(path==='/api/connectors/notion-native/pages')return route.fulfill({json:{pages:[{id:'page-one',title:'独立页面',selected:false}]}});
  if(path==='/api/connectors/notion-native/resources/select'){selected=body.selected_databases.map((item:any)=>typeof item==='string'?item:item.database_id);if(saveBusy)return route.fulfill({status:409,headers:{'Retry-After':'60'},json:{detail:{code:'NOTION_SYNC_BUSY',message:'sync busy',selection_saved:true}}});return route.fulfill({json:{connector:connector()}});}
  if(path==='/api/connectors/notion-native/sync')return route.fulfill({json:{connector:connector()}});
  if(path==='/api/connectors/notion-native'&&method==='DELETE'){removed=true;return route.fulfill({json:{ok:true}});}
  unexpected.push(`${method} ${path}`);return route.fulfill({status:501,json:{detail:'unexpected fixture request'}});
 });
 return {writes,reads,unexpected,finishBusy:()=>{saveBusy=false;}};
}
async function open(page:Page){await page.goto(base);await expect(page.getByRole('heading',{name:'Notion CLI',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Notion 工作空间助手',exact:true})).toBeVisible();}

test('native Notion preserves the seven sections and original Skill/file/resource/source journeys',async({page})=>{
 const f=await fixtures(page);await open(page);await expect(page.getByRole('heading')).toHaveText(['Notion CLI','权限','Skills','读取操作','写入操作','资源范围','已挂载来源','信息']);
 expect(f.reads.filter(path=>/\/(databases|pages)$/.test(path))).toEqual([]);
 await page.getByRole('button',{name:'Notion 工作空间助手',exact:true}).click();await expect(page.getByText('不读取凭证。',{exact:true})).toBeVisible();await page.getByRole('button',{name:'references/search.md',exact:true}).click();await expect(page.getByText('只读取已挂载索引。',{exact:true})).toBeVisible();await page.getByRole('button',{name:'← Skill',exact:true}).click();await page.getByRole('button',{name:'← Notion',exact:true}).click();
 await page.getByRole('button',{name:'管理资源范围',exact:true}).click();await expect(page.getByRole('checkbox')).toHaveCount(10);await page.getByRole('button',{name:'下一页',exact:true}).click();await expect(page.getByRole('checkbox')).toHaveCount(2);await page.getByRole('textbox',{name:'搜索 Notion 资源',exact:true}).fill('数据库 10');await expect(page.getByRole('checkbox')).toHaveCount(1);
 await page.getByRole('button',{name:'Toggle resource page',exact:true}).click();await page.getByRole('button',{name:'Toggle resource page',exact:true}).click();await expect(page.getByRole('textbox',{name:'搜索 Notion 资源',exact:true})).toHaveValue('数据库 10');
 await page.getByRole('button',{name:'← Notion',exact:true}).click();await page.getByRole('button',{name:'管理已挂载来源',exact:true}).click();await expect(page.getByText('原有成功索引',{exact:true})).toBeVisible();await page.getByRole('button',{name:'← Notion',exact:true}).click();
 await page.getByRole('button',{name:'网站',exact:true}).click();expect(await page.evaluate(()=>(window as any).__nativeNotion.links)).toEqual(['https://developers.notion.com/cli/get-started/overview']);await expect(page.getByRole('textbox',{name:'Existing Chat draft'})).toHaveValue('Unsent original Chat draft');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(f.writes).toEqual([]);expect(f.unexpected).toEqual([]);await page.screenshot({path:'/tmp/ink-native-settings-resources-20261029/native-notion-overview.png'});
});
test('native resource saved-scope recovery retains selection metadata and never automatically repeats a write',async({page})=>{
 await page.clock.install();const f=await fixtures(page,{busy:true});await open(page);await page.getByRole('button',{name:'管理资源范围',exact:true}).click();await page.getByRole('checkbox',{name:'数据库 1',exact:true}).click();await page.getByRole('button',{name:'保存并首次同步',exact:true}).click();await expect(page.getByRole('alert')).toContainText('资源范围已保存，索引更新未完成');
 expect(f.writes).toHaveLength(1);expect(f.writes[0].headers['x-ink-csrf']).toBe(CSRF);expect(f.writes[0].headers.authorization).toBeUndefined();expect(f.writes[0].body.selected_databases).toEqual(expect.arrayContaining([expect.objectContaining({database_id:'db-1',title:'数据库 1',page_count:2})]));
 await expect(page.getByRole('checkbox',{name:'数据库 1',exact:true})).toBeChecked();await expect(page.getByRole('button',{name:'保存并首次同步',exact:true})).toBeDisabled();await page.clock.runFor(60001);expect(f.writes).toHaveLength(1);await expect(page.getByRole('button',{name:'保存并首次同步',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'← Notion',exact:true}).click();await page.getByRole('button',{name:'管理已挂载来源',exact:true}).click();await expect(page.getByText('新增范围',{exact:true})).toBeVisible();f.finishBusy();await page.getByRole('button',{name:'立即同步',exact:true}).click();await expect.poll(()=>f.writes.filter(call=>call.path.endsWith('/sync')).length).toBe(1);expect(f.unexpected).toEqual([]);
});
