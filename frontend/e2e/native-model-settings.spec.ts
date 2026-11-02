// [Input] Original shared model-setting handlers and the production native renderer.
// [Output] Model/configuration save, recovery, hidden-page and secure-input technical evidence.
// [Pos] Provider-free HTTP fixture; no account, Admin, database, runtime or model mutations.
// Impact: configuration changes only in fixture memory; Thread/draft/runtime ownership is unchanged; Dream artifacts/Run/Hook are out of scope.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';

const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import ModelConfigSection from '/app/_dream/components/dashboard/ModelConfigSection.native.tsx';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
await i18n.changeLanguage('en');
await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const off={generation:false,edit:false,configured:false,entitled:true,callable:false},ready={generation:true,edit:true,configured:true,entitled:true,callable:true};
const model=(modelAlias,displayName,extra={})=>({modelAlias,displayName,protocol:'openai',capabilities:{chat:true,tools:true},contextWindow:null,maxOutputTokens:null,enabled:true,callable:true,availability:'included',requiredPlanCode:null,upgradeHint:null,images:off,responsesImage:off,...extra});
const f=window.__modelFixture={calls:[],saves:0,expirations:0,hold:false,held:[],expired:false,configFailure:false,catalogFailure:false,saveStatus:200,malformed:false,disconnect:false,commitBeforeDisconnect:false,
 config:{model:'',image_model:'',system_prompt:'Original prompt',workspace_enabled:true,im_full_access_enabled:false,sandbox_network_mode:'allowlist',sandbox_network_allowed_domains:['original.example.invalid'],sandbox_fs_allowed_write_paths:['/fixture/original'],env_vars:{}},
 catalog:{defaultModelAlias:'chat-a',data:[model('chat-a','Chat A'),model('chat-b','Chat B',{responsesImage:ready}),model('chat-locked','Chat locked',{callable:false,availability:'upgrade_required',requiredPlanCode:'pro'}),model('image-a','Image A',{callable:false,capabilities:{chat:false},images:ready}),model('image-b','Image B',{callable:false,capabilities:{chat:false},images:ready}),model('image-locked','Image locked',{callable:false,capabilities:{chat:false},images:{...ready,callable:false,configured:false}})]}};
async function transport(input,init={}){
 const path=new URL(String(input),'http://fixture.invalid').pathname,method=init.method||'GET',body=init.body?JSON.parse(init.body):undefined;
 f.calls.push({path,method,body,headers:Object.fromEntries(new Headers(init.headers)),signal:init.signal});
 let response;
 if(f.expired)response=new Response(null,{status:401});
 else if(path==='/api/gateway/models'&&method==='GET')response=f.catalogFailure?new Response(null,{status:503}):Response.json(f.catalog);
 else if(path==='/api/system-config'&&method==='GET')response=f.configFailure?new Response(null,{status:503}):Response.json(structuredClone(f.config));
 else if(path==='/api/system-config'&&method==='PUT'){
  if(f.saveStatus!==200)return new Response(null,{status:f.saveStatus});
  if(f.disconnect){if(f.commitBeforeDisconnect)Object.assign(f.config,body);throw Error('fixture disconnected');}
  if(f.malformed)return Response.json({success:true});
  Object.assign(f.config,body);response=Response.json({success:true,data:structuredClone(f.config)});
 }else throw Error('UNEXPECTED_FIXTURE_HTTP '+method+' '+path);
 return f.hold&&method==='GET'?new Promise(resolve=>f.held.push({signal:init.signal,release:()=>resolve(response)})):response;
}
function Harness(){const [visible,setVisible]=useState(true),[mounted,setMounted]=useState(true),[draft,setDraft]=useState('Existing Chat draft');return <div style={{height:844,width:'100%',display:'flex',flexDirection:'column'}}>
 <textarea aria-label="Existing Chat draft" value={draft} onChange={e=>setDraft(e.target.value)}/><button onClick={()=>setVisible(v=>!v)}>Toggle Settings</button><button onClick={()=>setMounted(v=>!v)}>Toggle settings instance</button>
 {mounted?<div style={{flex:1,minHeight:0,display:visible?'flex':'none',flexDirection:'column'}}><ModelConfigSection active={visible} onBack={()=>setVisible(false)} transport={transport} onConfigSaved={()=>f.saves++} onSessionExpired={()=>f.expirations++}/></div>:null}
 </div>;}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
  const root=fileURLToPath(new URL('../',import.meta.url));
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-model-settings-20261029/vite',optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','i18next','react-i18next']},resolve:{alias:{'react-native':'react-native-web'}},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'native-model-settings-fixture',enforce:'pre',resolveId(id){if(id==='/native-model-settings-entry.tsx')return '\0native-model-settings-entry';},async load(id){if(id==='\0native-model-settings-entry')return transformWithEsbuild(entry,'native-model-settings-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-model-settings')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-model-settings','<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/native-model-settings-entry.tsx"></script></body></html>'));});}}]});await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('FIXTURE_LISTENER_MISSING');base='http://127.0.0.1:'+address.port+'/native-model-settings';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.setViewportSize({width:390,height:844});await page.goto(base);await expect(page.getByRole('textbox',{name:'系统提示词',exact:true})).toHaveValue('Original prompt');});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
const ai=(page:Page)=>page.getByRole('radiogroup',{name:'选择 AI 模型',exact:true});
const image=(page:Page)=>page.getByRole('radiogroup',{name:'选择 Image 模型',exact:true});
async function calls(page:Page){return page.evaluate(()=>(window as any).__modelFixture.calls.map(({signal,...call}:any)=>call));}

test('native fields preserve Admin default, independent Image eligibility and read-only entry',async({page})=>{
  await expect(ai(page).getByRole('radio',{name:'Chat A',exact:true})).toBeChecked();await expect(ai(page).getByRole('radio',{name:'Chat locked',exact:true})).toBeDisabled();await expect(image(page).getByRole('radio',{name:'Image locked',exact:true})).toBeDisabled();await expect(image(page).getByRole('radio',{checked:true})).toHaveCount(0);
  await expect(ai(page).getByText('图片生成',{exact:true})).toBeVisible();await expect(ai(page).getByText('Image A',{exact:true})).toHaveCount(0);expect((await calls(page)).every((call:any)=>call.method==='GET')).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('native AI and Image save exactly one original field with CSRF and saved-config notifications',async({page})=>{
  await image(page).getByRole('radio',{name:'Image A',exact:true}).click();await expect(page.getByText('Image 模型已保存，仅用于后续 image_gen 工具调用。',{exact:true})).toBeVisible();await expect(ai(page).getByRole('radio',{name:'Chat A',exact:true})).toBeChecked();
  await ai(page).getByRole('radio',{name:'Chat B',exact:true}).click();await expect(page.getByText('模型已保存，将用于新对话。',{exact:true})).toBeVisible();
  const writes=(await calls(page)).filter((call:any)=>call.method==='PUT');expect(writes.map((call:any)=>call.body)).toEqual([{image_model:'image-a'},{model:'chat-b'}]);expect(await page.evaluate(()=>(window as any).__modelFixture.saves)).toBe(2);
  for(const call of await calls(page)){expect(call.headers['x-ink-csrf']).toHaveLength(43);expect(call.headers.authorization).toBeUndefined();}
});
test('ambiguous model save blocks automatic retries until explicit reload verifies the committed selection',async({page})=>{
  await page.evaluate(()=>{const f=(window as any).__modelFixture;f.disconnect=true;f.commitBeforeDisconnect=true;});await ai(page).getByRole('radio',{name:'Chat B',exact:true}).click();await expect(page.getByText(/网络连接失败，模型保存结果未确认/)).toBeVisible();await expect(ai(page).getByRole('radio',{name:'Chat B',exact:true})).toBeDisabled();
  expect((await calls(page)).filter((call:any)=>call.method==='PUT')).toHaveLength(1);expect(await page.evaluate(()=>(window as any).__modelFixture.saves)).toBe(0);
  await page.evaluate(()=>(window as any).__modelFixture.disconnect=false);await page.getByRole('button',{name:'重新加载设置',exact:true}).click();await expect(ai(page).getByRole('radio',{name:'Chat B',exact:true})).toBeChecked();await expect(ai(page).getByRole('radio',{name:'Chat A',exact:true})).toBeEnabled();expect((await calls(page)).filter((call:any)=>call.method==='PUT')).toHaveLength(1);
});
test('config/catalog read failures retain saved choices and recover through original reload',async({page})=>{
  await page.evaluate(()=>{const f=(window as any).__modelFixture;f.malformed=true;});await ai(page).getByRole('radio',{name:'Chat B',exact:true}).click();await expect(page.getByRole('button',{name:'重新加载设置',exact:true})).toBeVisible();
  await page.evaluate(()=>{const f=(window as any).__modelFixture;f.configFailure=true;f.catalogFailure=true;});await page.getByRole('button',{name:'重新加载设置',exact:true}).click();await expect(page.getByText('模型设置读取失败，请重新加载后再选择。',{exact:true})).toBeVisible();await expect(ai(page).getByRole('radio',{name:'Chat A',exact:true})).toBeDisabled();await expect(ai(page).getByRole('radio',{name:'Chat A',exact:true})).toBeChecked();
  await page.evaluate(()=>{const f=(window as any).__modelFixture;f.configFailure=false;f.catalogFailure=false;f.malformed=false;});await page.getByRole('button',{name:'重新加载设置',exact:true}).click();await expect(ai(page).getByRole('radio',{name:'Chat B',exact:true})).toBeEnabled();
});
test('prompt drafts survive hidden settings and failed save without replacing the Chat draft',async({page})=>{
  const prompt=page.getByRole('textbox',{name:'系统提示词',exact:true});await prompt.fill('Help organize my notes');await page.getByRole('button',{name:'Back to app',exact:true}).click();await page.getByRole('button',{name:'Toggle Settings',exact:true}).click();await expect(prompt).toHaveValue('Help organize my notes');
  await page.evaluate(()=>(window as any).__modelFixture.saveStatus=503);await page.getByRole('button',{name:'保存系统提示词',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('保存结果未确认，请重新读取设置核对。');await expect(prompt).toHaveValue('Help organize my notes');await expect(page.getByRole('textbox',{name:'Existing Chat draft',exact:true})).toHaveValue('Existing Chat draft');
  await page.evaluate(()=>(window as any).__modelFixture.saveStatus=200);await page.getByRole('button',{name:'保存系统提示词',exact:true}).click();await expect(page.getByRole('button',{name:'保存系统提示词',exact:true})).toBeDisabled();expect((await calls(page)).filter((call:any)=>call.method==='PUT').at(-1).body).toEqual({system_prompt:'Help organize my notes'});
});
test('workspace and approval retain original toggles, server failure rollback and save notifications',async({page})=>{
  await page.getByRole('button',{name:'工作区模式',exact:true}).click();await expect(page.getByText('沙箱网络 / Sandbox Network',{exact:true})).toHaveCount(0);await expect(page.getByText('环境变量 / Environment Variables',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'工作区模式',exact:true}).click();await expect(page.getByText('沙箱网络 / Sandbox Network',{exact:true})).toBeVisible();await page.evaluate(()=>(window as any).__modelFixture.saveStatus=403);await page.getByRole('button',{name:'完全访问已关闭',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('设置保存失败，请重试。');await expect(page.getByRole('button',{name:'完全访问已关闭',exact:true})).toBeEnabled();expect(await page.evaluate(()=>(window as any).__modelFixture.saves)).toBe(2);
});
test('domain and path edits retain original normalization and exact patch ownership',async({page})=>{
  await page.getByRole('button',{name:'+ 添加域',exact:true}).click();await page.getByRole('textbox',{name:'添加域',exact:true}).fill('https://NOTES.example.invalid:443/path');await page.getByRole('button',{name:'保存域',exact:true}).click();await expect(page.getByText('域名允许列表已保存。',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'+ 添加可写路径',exact:true}).click();await page.getByRole('textbox',{name:'添加可写路径',exact:true}).fill('/fixture/notes/');await page.getByRole('button',{name:'保存可写路径',exact:true}).click();await expect(page.getByText('可写路径已保存。',{exact:true})).toBeVisible();
  expect((await calls(page)).filter((call:any)=>call.method==='PUT').map((call:any)=>call.body)).toEqual([{sandbox_network_allowed_domains:['original.example.invalid','notes.example.invalid']},{sandbox_fs_allowed_write_paths:['/fixture/original','/fixture/notes']}]);
});
test('tool environment values stay masked and use only the original explicit env_vars save',async({page})=>{
  await page.getByRole('button',{name:'+ 添加',exact:true}).click();await page.getByRole('textbox',{name:'环境变量名称 1',exact:true}).fill(' NOTES_KEY ');const value=page.getByLabel('环境变量值 1',{exact:true});await expect(value).toHaveAttribute('type','password');await value.fill(' fixture-only-value ');expect((await calls(page)).filter((call:any)=>call.method==='PUT')).toHaveLength(0);
  await page.getByRole('button',{name:'保存环境变量',exact:true}).click();await expect(page.getByRole('button',{name:'保存环境变量',exact:true})).toBeDisabled();expect((await calls(page)).filter((call:any)=>call.method==='PUT').at(-1).body).toEqual({env_vars:{NOTES_KEY:'fixture-only-value'}});
  await page.getByRole('button',{name:'删除环境变量 1',exact:true}).click();await page.getByRole('button',{name:'保存环境变量',exact:true}).click();await expect(page.getByRole('button',{name:'保存环境变量',exact:true})).toBeDisabled();expect((await calls(page)).filter((call:any)=>call.method==='PUT').at(-1).body).toEqual({env_vars:{}});
});
test('401 settings reread requests original session refresh and cannot submit config',async({page})=>{
  await page.evaluate(()=>{const f=(window as any).__modelFixture;f.malformed=true;});await ai(page).getByRole('radio',{name:'Chat B',exact:true}).click();await page.evaluate(()=>(window as any).__modelFixture.expired=true);await page.getByRole('button',{name:'重新加载设置',exact:true}).click();await expect(page.getByText('模型设置读取失败，请重新加载后再选择。',{exact:true})).toBeVisible();expect(await page.evaluate(()=>(window as any).__modelFixture.expirations)).toBe(2);await expect(ai(page).getByRole('radio',{name:'Chat A',exact:true})).toBeDisabled();expect((await calls(page)).filter((call:any)=>call.method==='PUT')).toHaveLength(1);
});
