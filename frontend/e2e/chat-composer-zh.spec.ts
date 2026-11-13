// [Input] Production ChatView/Router and native controls with explicit Chinese public DTO fixtures.
// [Output] Before/after Chinese menu screenshots, typography/geometry and original Thread tool interaction checks.
// [Pos] Provider-free visual qualification; native uses RNW, with no real account/model/MCP/device or database.
// Impact: menu presentation changes; original Thread/request/permission owners remain. Project/Episode,
// canonical artifacts, Run-private publication, after-turn Hook and PostgreSQL are out of scope.
import {test,expect,type Page,type Locator} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
import {composerModels,installComposerApi} from './fixtures/chatComposerApi';

const before=process.env.CHAT_COMPOSER_ZH_CAPTURE==='before';
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.use({screenshot:'only-on-failure'});
test.beforeAll(async()=>{
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',cacheDir:fileURLToPath(new URL('../output/chat-composer-zh-20261113/vite',import.meta.url)),define:{__DEV__:'false'},resolve:{alias:[{find:/^react-native$/,replacement:fileURLToPath(new URL('./native/reflections-platform-web-boundary.ts',import.meta.url))},{find:/^react-native-svg$/,replacement:fileURLToPath(new URL('./native/svg-web-boundary.tsx',import.meta.url))}],extensions:['.web.tsx','.tsx','.web.ts','.ts','.web.js','.js','.mjs','.json']},server:{host:'127.0.0.1',port:0},plugins:[{name:'chinese-chat-visual',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
  const path=req.url?.split('?')[0],entry=path==='/story-workspace/chat'?'chat-route-cache':path==='/chat-tools'?'chat-tools-harness':null;if(!entry)return next();
  res.setHeader('Content-Type','text/html; charset=utf-8');res.end(await vite.transformIndexHtml(path!,'<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/'+entry+'.tsx"></script></body></html>'));
 });}}]});await server.listen();base=server.resolvedUrls!.local[0];
});
test.afterAll(async()=>{await server?.close();});

async function setup(page:Page,dark:boolean){
 await page.emulateMedia({colorScheme:dark?'dark':'light'});
 const diagnostics:string[]=[],unexpected:string[]=[],writes:string[]=[];
 page.on('pageerror',error=>diagnostics.push(error.message));page.on('console',message=>{if(message.type()==='error')diagnostics.push(message.text()+' '+message.location().url);});
 page.on('requestfailed',request=>{if(request.failure()?.errorText!=='net::ERR_ABORTED')diagnostics.push(request.url());});
 await installComposerApi(page);
 await page.addInitScript(dark=>{localStorage.setItem('ink-theme',dark?'dark':'light');document.addEventListener('DOMContentLoaded',()=>document.documentElement.setAttribute('data-theme',dark?'dark':'light'));},dark);
 const agents=Array.from({length:16},(_,index)=>({id:'zh-agent-'+index,deck_id:'zh-deck',name:'Writer '+index,name_zh:index===0?'中文写作助手 Writer':'研究与创作助手 '+index,enabled:true,icon:'brain',color:'blue',system_prompt:'Fixture role',is_system:false}));
 await page.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname,json=(value:unknown)=>route.fulfill({json:value});
  if(url.origin!==new URL(base).origin)return route.abort();
  if(path==='/auth/session')return json({user:{id:'1',email:'visual@example.invalid',display_name:'中文排版验证',avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
  if(!path.startsWith('/api/'))return route.continue();
  if(request.method()!=='GET'){writes.push(request.method()+' '+path);return route.fallback();}
  if(path==='/api/decks/catalog')return json({decks:[{id:'zh-deck',name:'Writing',name_zh:'写作与研究',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,voices:agents}]});
  if(path==='/api/system-config')return json({data:{model:'fixture-model-a',workspace_enabled:false,im_full_access_enabled:false}});
  if(path==='/api/gateway/models')return json({data:composerModels.map((model,index)=>({...model,displayName:['中文写作模型 Alpha','长名称模型：中文研究与创作 Beta','进阶模型 Pro'][index],upgradeHint:index===2?'当前套餐暂不可用':null})),defaultModelAlias:'fixture-model-a'});
  if(path==='/api/claude-mcp/servers')return json({servers:Array.from({length:10},(_,index)=>({name:'zh-tools-'+index,display_name:index===0?'中文资料检索 Research':'长名称远程资源与资料检索服务 '+index,id:'zh-mcp-'+index,revision:1,enabled:true,transport:'streamable_http',url:'https://example.invalid/mcp',stdio_profile_key:null,workspace_id:null,state:'connected',auth_state:'anonymous',auth_kind:'none',detail:null,active_operation_id:null,config_scope:'user',removable:true,credential_revision:0,credential_ref:null,credential_configured:false}))});
  if(path==='/api/claude-plugins/installations')return json({installations:[]});
  if(path==='/api/claude-agent/threads')return json({threads:[]});
  if(path==='/api/story-workspace/dream-runs')return json({runs:[]});
  if(['/api/claude-mcp/capability','/api/storage','/api/claude-agent/skill-commands'].includes(path))return route.fallback();
  unexpected.push(path);return route.fulfill({status:503,body:'Unexpected Chinese fixture API'});
 });
 return {diagnostics,unexpected,writes};
}
async function bounded(locator:Locator,width:number,height:number){const box=await locator.boundingBox();expect(box).not.toBeNull();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.y).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(width+1);expect(box!.y+box!.height).toBeLessThanOrEqual(height+1);return box!;}

for(const width of [1200,768,390])for(const dark of [false,true])test(`Chinese normal Chat ${width}px ${dark?'dark':'light'}`,async({page},info)=>{
 await page.setViewportSize({width,height:850});const state=await setup(page,dark);
 await page.goto(base+'story-workspace/chat?lang=zh');await page.evaluate(()=>document.fonts.ready);
 const trigger=page.getByRole('button',{name:/^Agent与工具：/}),model=page.getByTestId('model-selector-button');
 await expect(model).toContainText('中文写作模型 Alpha');await page.getByRole('textbox',{name:'聊天输入'}).fill('保留这份中文草稿，继续讨论创作想法。');
 await trigger.click();const tools=page.getByRole('dialog',{name:'Agent与工具',exact:true});await expect(tools.getByRole('switch').first()).toBeVisible();await bounded(tools,width,850);
 await tools.getByRole('switch',{name:'中文资料检索 Research'}).click();await expect(tools.getByRole('switch',{name:'中文资料检索 Research'})).toBeChecked();
 await page.screenshot({path:info.outputPath('tools.png'),fullPage:true,animations:'disabled'});
 await tools.getByRole('button',{name:'选择Agent',exact:true}).click();await expect(page.getByRole('option',{name:/中文写作助手 Writer/})).toBeVisible();
 const list=page.getByRole('listbox',{name:'按卡片结构分组的 Agent'});await bounded(width>767?page.locator('.composer-agent-flyout'):tools,width,850);
 if(width>767){await expect.poll(async()=>{const parent=(await tools.boundingBox())!,child=(await page.locator('.composer-agent-flyout').boundingBox())!;return parent.x+parent.width<=child.x+1||child.x+child.width<=parent.x+1;}).toBe(true);await expect(tools.getByRole('radio').first()).toBeVisible();await page.keyboard.press('ArrowLeft');await expect(page.locator('.composer-agent-flyout')).toHaveCount(0);await expect(tools.getByRole('button',{name:'选择Agent',exact:true})).toBeFocused();await page.keyboard.press('ArrowRight');await expect(list).toBeVisible();await expect.poll(async()=>{const parent=(await tools.boundingBox())!,child=(await page.locator('.composer-agent-flyout').boundingBox())!;return parent.x+parent.width<=child.x+1||child.x+child.width<=parent.x+1;}).toBe(true);}
 await page.screenshot({path:info.outputPath('agents.png'),fullPage:true,animations:'disabled'});await page.getByRole('option',{name:/中文写作助手 Writer/}).click();
 await expect(trigger).toContainText('中文写作助手 Writer');await model.click();const menu=page.getByRole('dialog',{name:'选择模型',exact:true});await bounded(menu,width,850);await expect(menu.getByRole('option',{name:/进阶模型 Pro/})).toBeDisabled();
 await page.screenshot({path:info.outputPath('models.png'),fullPage:true,animations:'disabled'});
 const metrics=await page.evaluate(()=>Object.fromEntries(['.composer-tools-trigger','.composer-popover','.model-selector__trigger','.model-selector__identity strong'].map(selector=>{const node=document.querySelector(selector)!,style=getComputedStyle(node);return [selector,{fontFamily:style.fontFamily,fontSize:style.fontSize,fontWeight:style.fontWeight,lineHeight:style.lineHeight}];})));
 await info.attach('typography.json',{body:JSON.stringify(metrics,null,2),contentType:'application/json'});
 await writeFile(info.outputPath('typography.json'),JSON.stringify(metrics,null,2));
 if(!before){expect(metrics['.composer-popover'].fontFamily).toBe(metrics['.composer-tools-trigger'].fontFamily);expect(metrics['.model-selector__trigger'].fontFamily).toBe(metrics['.composer-tools-trigger'].fontFamily);expect(metrics['.composer-popover'].fontSize).toBe('14px');}
 await menu.getByRole('combobox').fill('不存在的模型');await expect(menu.getByText('没有匹配的模型')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('textbox',{name:'聊天输入'})).toHaveText('保留这份中文草稿，继续讨论创作想法。');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(state.writes).toEqual([]);expect(state.unexpected).toEqual([]);expect(state.diagnostics).toEqual([]);
});

for(const dark of [false,true])test(`Chinese native controls 390px ${dark?'dark':'light'}`,async({page},info)=>{
 await page.setViewportSize({width:390,height:850});const state=await setup(page,dark);await page.goto(base+'chat-tools?native=1&lang=zh&system='+(dark?'dark':'light'));await page.evaluate(()=>document.fonts.ready);
 await expect(page.getByTestId('model-selector-button')).toContainText('中文写作模型 Alpha');await page.getByRole('button',{name:/^Agent与工具：/}).click();
 await expect(page.getByRole('switch',{name:'中文资料检索 Research'})).toBeVisible();
 const panelColor=await page.getByText('Agent与工具',{exact:true}).evaluate(node=>{let current:Element|null=node;while(current){const color=getComputedStyle(current).backgroundColor;if(color!=='rgba(0, 0, 0, 0)'&&color!=='transparent')return color;current=current.parentElement;}return '';});
 const red=Number(panelColor.match(/\d+/)?.[0]);if(dark)expect(red).toBeLessThan(100);else expect(red).toBeGreaterThan(180);
 await page.screenshot({path:info.outputPath('tools.png'),fullPage:true,animations:'disabled'});await expect(page.getByRole('switch',{name:'中文资料检索 Research'})).toBeInViewport();
 await page.getByRole('button',{name:'选择Agent ›',exact:true}).click();await expect(page.getByRole('radio',{name:'中文写作助手 Writer',exact:true})).toBeVisible();await page.screenshot({path:info.outputPath('agents.png'),fullPage:true,animations:'disabled'});await page.getByRole('radio',{name:'中文写作助手 Writer',exact:true}).click();
 await page.getByTestId('model-selector-button').click();await expect(page.getByRole('radio',{name:'进阶模型 Pro',exact:true})).toBeDisabled();await page.screenshot({path:info.outputPath('models.png'),fullPage:true,animations:'disabled'});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(state.writes).toEqual([]);expect(state.unexpected).toEqual([]);expect(state.diagnostics).toEqual([]);
});
