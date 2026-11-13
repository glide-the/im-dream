// [Sync] 2026-11-13: normal Chat first and later requests preserve and clear the submitted MCP selection.
// [Input] Production StoryWorkspaceRouter/ChatView and explicit synthetic session/catalog/history HTTP boundaries.
// [Output] Desktop/narrow retained Chat mount, draft, catalog refresh and prose-before-status evidence.
// [Pos] Provider-free browser qualification; no normal account, database, model or native runtime writes.
// [Sync] 2026-11-13: qualify the combined Agent/model controls through production ChatView, ChatPanel and retained routing.
// Impact: Chat presentation and fixture preferences change; Thread identity and original send DTO remain.
// Project/Episode, canonical artifacts, Run-private publication, after-turn Hook and PostgreSQL are out of scope.
import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {composerModels,installComposerApi} from './fixtures/chatComposerApi';
test.use({screenshot:'only-on-failure'});

let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-chat-cache-20261103-validation/vite-web-route-real-entry',resolve:{alias:[{find:/^react-native$/,replacement:'react-native-web'}],extensions:['.web.tsx','.tsx','.web.ts','.ts','.web.js','.js','.mjs','.json']},optimizeDeps:{entries:['e2e/fixtures/chat-route-cache.tsx']},server:{host:'127.0.0.1',port:0},plugins:[{name:'chat-route-cache',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(!req.url?.startsWith('/story-workspace/'))return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/story-workspace/chat','<html><head><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/e2e/fixtures/chat-route-cache.tsx"></script></body></html>'));});}}]});await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('PORT');base='http://127.0.0.1:'+address.port;
});

for(const width of [1200,390])test(`normal Chat wires Agent and model selection through first and later turns at ${width}px`,async({page},info)=>{
 await page.setViewportSize({width,height:850});
 const errors:string[]=[],unexpected:string[]=[],creates:Record<string,unknown>[]=[],sends:Record<string,unknown>[]=[],modelPatches:Record<string,unknown>[]=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')errors.push(message.text()+' '+message.location().url);});
 page.on('requestfailed',request=>{if(request.url().startsWith(base)&&request.failure()?.errorText!=='net::ERR_ABORTED')errors.push(request.url());});
 await installComposerApi(page);
 let model='fixture-model-a',persistedVoice='fixture-writer',created=false,legacy=false,configReads=0;
 const voices=[
  {id:'fixture-writer',deck_id:'fixture-deck',thread_id:'fixture-A',name:'Writer',enabled:true,icon:'brain',color:'blue',system_prompt:'Writer role',is_system:false},
  {id:'fixture-reviewer',deck_id:'fixture-deck',name:'Reviewer',enabled:true,icon:'brain',color:'blue',system_prompt:'Reviewer role',is_system:false},
 ];
 const decks=[{id:'fixture-deck',name:'Writing',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,voices},
  {id:'fixture-other-deck',name:'Other',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,voices:[{...voices[0],id:'fixture-other-agent',deck_id:'fixture-other-deck',name:'Other Agent'}]}];
 const thread=()=>({id:'fixture-A',title:'Composer conversation',...(legacy?{}:{deck_id:'fixture-deck',voice_id:persistedVoice}),created_at:'2026-11-13T00:00:00Z',updated_at:'2026-11-13T00:00:00Z'});
 await page.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname;
  const json=(value:unknown)=>route.fulfill({json:value});
  if(url.origin!==base)return route.abort();
  if(path==='/auth/session')return json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
  if(!path.startsWith('/api/'))return route.continue();
  if(path==='/api/system-config'){
   configReads++;
   if(request.method()==='PUT'){const patch=request.postDataJSON();modelPatches.push(patch);model=patch.model;}
   return json({data:{model,workspace_enabled:false,im_full_access_enabled:false}});
  }
  if(path==='/api/decks/catalog')return json({decks});
  if(path==='/api/claude-plugins/installations')return json({installations:[]});
  if(path==='/api/story-workspace/dream-runs')return json({runs:[]});
  if(path==='/api/claude-agent/threads'){
   if(request.method()==='POST'){creates.push(request.postDataJSON());created=true;return json({thread_id:'fixture-A'});}
   return json({threads:created?[thread()]:[]});
  }
  if(path==='/api/claude-agent'&&request.method()==='POST'){
   const body=request.postDataJSON();sends.push(body);
   // The existing router persists ThreadSelectVoice before starting a selected-Agent turn.
   persistedVoice=body.voiceId??persistedVoice;
   return route.fulfill({contentType:'text/event-stream',body:[
    'data: {"type":"text-start","id":"reply-text"}',
    `data: {"type":"message-metadata","sessionId":"fixture-session","turnId":"fixture-turn-${sends.length}","turnIndex":${sends.length-1}}`,
    `data: {"type":"text-delta","id":"reply-text","delta":"Answer ${sends.length}"}`,
    'data: {"type":"text-end","id":"reply-text"}',
    `data: {"type":"message-final","text":"Answer ${sends.length}","sessionId":"fixture-session"}`,
    'data: {"type":"finish","finishReason":"stop"}','data: [DONE]','',
   ].join('\n\n')});
  }
  if(path.endsWith('/plugin-load-receipt'))return json({thread_id:'fixture-A',deck_id:'fixture-deck',workspace_found:false,receipt:null,launch_manifest:null});
  if(path.endsWith('/messages'))return json({thread:thread(),messages:sends.flatMap((send,index)=>[send.message,{id:`fixture-reply-${index+1}`,role:'assistant',metadata:{turnId:`fixture-turn-${index+1}`,sessionId:'fixture-session',turnIndex:index},parts:[{type:'text',text:`Answer ${index+1}`}]}]),has_more:false,next_cursor:null,latest_message_id:sends.length?`fixture-reply-${sends.length}`:null,unchanged:false});
  if(path.endsWith('/status'))return json({running:false,lifecycle:'idle',turn_count:sends.length,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
  if(path.endsWith('/inputs'))return json({entries:[],local_owner:false});
  if(path.endsWith('/turn-navigation'))return json({items:[]});
  if(path.endsWith('/scheduled-tasks')||path.endsWith('/task-links'))return json({source:null,created:[]});
  if(path.endsWith('/subagents'))return json({subagents:[]});
  if(path.endsWith('/turns'))return json({turns:[]});
  if(path.endsWith('/plan')||path.endsWith('/todos'))return json({});
  if(['/api/gateway/models','/api/storage','/api/claude-agent/skill-commands','/api/claude-mcp/capability','/api/claude-mcp/servers'].includes(path))return route.fallback();
  unexpected.push(path);return route.fulfill({status:503,body:'Unexpected fixture API'});
 });
 await page.goto(base+'/story-workspace/chat');
 const agent=()=>page.getByRole('button',{name:/^Agent and tools:/}),picker=page.getByTestId('model-selector-button'),editor=()=>page.getByRole('textbox',{name:'Chat input'});
 await expect(picker).toContainText('IM Model Alpha');
 await expect(agent()).toHaveCount(1);await expect(page.getByRole('button',{name:'Tools',exact:true})).toHaveCount(0);
 await editor().fill('Help me review this idea');
 await agent().click();await page.getByRole('button',{name:'Select Agent',exact:true}).click();await page.getByRole('option',{name:'Writer',exact:false}).click();
 await expect(agent()).toContainText('Writer');
 await agent().click();await page.getByRole('switch',{name:'Research library'}).click();await page.keyboard.press('Escape');
 await picker.click();await page.getByRole('dialog',{name:'Select model',exact:true}).getByRole('option',{name:/IM Model Beta/}).click();
 await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeEnabled();
 expect(modelPatches).toEqual([{model:'fixture-model-b'}]);await expect(editor()).toHaveText('Help me review this idea');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect.poll(()=>sends.length).toBe(1);await expect(page.getByText('Answer 1',{exact:true})).toBeVisible();
 expect(creates).toEqual([{deckId:'fixture-deck',voiceId:'fixture-writer'}]);
 expect(sends[0]).toMatchObject({id:'fixture-A',deckId:'fixture-deck',voiceId:'fixture-writer',resume:true,toolChoice:'auto'});
 expect(sends[0]).not.toHaveProperty('model');expect(sends[0].tools).toEqual([{type:'mcp',server_name:'research'}]);
 await expect(picker).toContainText('IM Model Beta');await editor().fill('Please consider a second approach');
 await agent().click();await page.getByRole('button',{name:'Select Agent',exact:true}).click();
 await expect(page.getByRole('option',{name:'Other Agent',exact:false})).toHaveCount(0);
 await expect(page.getByRole('option',{name:'No Agent',exact:false})).toHaveCount(0);
 await page.getByRole('option',{name:'Reviewer',exact:false}).click();await expect(agent()).toContainText('Reviewer');
 await agent().click();const tools=page.getByRole('dialog',{name:'Agent & tools'});
 await expect(tools.getByRole('switch',{name:'Research library'})).toBeChecked();await tools.getByRole('switch',{name:'Research library'}).click();
 await tools.getByRole('radio',{name:'Confirm each step',exact:true}).check();await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await expect.poll(()=>sends.length).toBe(2);await expect(page.getByText('Answer 2',{exact:true})).toBeVisible();
 expect(sends[1].tools).toEqual([]);expect(creates).toHaveLength(1);expect(sends[1]).toMatchObject({id:'fixture-A',deckId:'fixture-deck',voiceId:'fixture-reviewer',resume:true,toolChoice:'manual'});
 await editor().fill('Keep this draft while I browse');
 for(const menu of ['agent','model']){
  if(menu==='agent')await agent().click();else await picker.click();
  // A host route intent can arrive while a portal is open, including a narrow-screen sheet.
  await page.evaluate(()=>{history.pushState({},'','/story-workspace/timeline');dispatchEvent(new PopStateEvent('popstate'));});
  await expect(page.getByText('Timeline fixture',{exact:true})).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  model='fixture-model-a';const readsBefore=configReads;
  await page.getByRole('button',{name:'Navigate chat',exact:true}).click();
  await expect.poll(()=>configReads).toBeGreaterThan(readsBefore);
  await expect(picker).toContainText('IM Model Alpha');await expect(editor()).toHaveText('Keep this draft while I browse');
  await expect(agent()).toContainText('Reviewer');expect(await page.evaluate(()=>window.__routeCache.mounts)).toBe(1);
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(sends).toHaveLength(2);expect(modelPatches).toEqual([{model:'fixture-model-b'}]);expect(unexpected).toEqual([]);expect(errors).toEqual([]);
 await expect(page.getByText('Answer 1',{exact:true})).toHaveCount(1);await expect(page.getByText('Answer 2',{exact:true})).toHaveCount(1);
 await page.screenshot({path:info.outputPath('normal-chat-agent-model.png'),fullPage:true});
 // Legacy Thread metadata still uses the production Voice.thread_id display fallback.
 legacy=true;await page.getByTitle('New chat',{exact:true}).click();
 await page.getByRole('button',{name:'Composer conversation',exact:true}).click();
 await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeVisible();
 await expect(agent()).toContainText('Writer');await agent().click();
 await page.getByRole('button',{name:'Select Agent',exact:true}).click();
 await expect(page.getByRole('option',{name:'Writer',exact:false})).toHaveAttribute('aria-selected','true');
 await expect(page.getByRole('option',{name:'Reviewer',exact:false})).toBeVisible();
 await expect(page.getByRole('option',{name:'Other Agent',exact:false})).toHaveCount(0);
 await page.keyboard.press('Escape');expect(errors).toEqual([]);expect(unexpected).toEqual([]);
});
test.afterAll(async()=>{await server?.close();});
for(const width of [1200,390])test('retained Chat route and fresh reading at '+width+'px',async({page},testInfo)=>{
 await page.setViewportSize({width,height:800});const calls:string[]=[],errors:string[]=[],unexpected:string[]=[];let releaseStatus:()=>void=()=>{},statusHeld=true;
 page.on('pageerror',cause=>errors.push(cause.message));
 page.on('console',message=>{if(message.type()==='error')console.log('CACHE_ROUTE_CONSOLE '+message.text());});
 page.on('response',async response=>{if(response.url().startsWith(base)&&response.status()>=400)console.log('CACHE_ROUTE_HTTP '+response.status()+' '+response.url()+' '+(await response.text().catch(()=>'' )).slice(0,1200));});
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url()),path=url.pathname;
  const json=(value:unknown)=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(value)});
  if(url.origin!==base)return route.abort();
  if(path==='/auth/session')return json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
  if(!path.startsWith('/api/'))return route.continue();calls.push(path);
  if(path==='/api/storage')return json({type:'unknown',supportsDirectUpload:false,isConfigured:false});
  if(path.endsWith('/plugin-load-receipt'))return json({thread_id:'fixture-A',deck_id:null,workspace_found:false,receipt:null,launch_manifest:null});
  if(path.endsWith('/scheduled-tasks'))return json({source:null,created:[]});
  if(path.endsWith('/turn-navigation'))return json({items:[]});
  if(path==='/api/decks/catalog')return json({decks:[]});
  if(path==='/api/system-config')return json({data:{model:'fixture-model-a',workspace_enabled:false,im_full_access_enabled:false}});
  if(path==='/api/gateway/models')return json({data:composerModels,defaultModelAlias:'fixture-model-a'});
  if(path==='/api/story-workspace/dream-runs')return json({runs:[]});
  if(path==='/api/claude-agent/threads')return json({threads:[{id:'fixture-A',title:'Existing A',created_at:'2026-11-03T00:00:00Z',updated_at:'2026-11-03T00:00:00Z'}]});
  if(path.endsWith('/messages'))return json({thread:{id:'fixture-A',title:'Existing A'},messages:[{id:'a1',role:'assistant',parts:[{type:'text',text:'Saved browser answer\n\n'+Array.from({length:40},(_,index)=>'Saved paragraph '+index+'. A complete reading position stays with this conversation.').join('\n\n')}],created_at:'2026-11-03T00:00:00Z'}],has_more:false,next_cursor:null,latest_message_id:'a1',unchanged:false});
  if(path.endsWith('/status')){if(statusHeld)await new Promise<void>(resolve=>{releaseStatus=resolve;});return json({running:false,lifecycle:'idle',turn_count:1,pending_tool_call_ids:[],tool_confirmation_observation:'known'});}
  if(path.endsWith('/inputs'))return json({entries:[],local_owner:false});
  if(path==='/api/claude-agent/skill-commands')return json({commands:[]});
  if(/\/(turns|task-links|plan|todos|subagents)$/.test(path))return json(path.endsWith('/turns')?{turns:[]}:path.endsWith('/task-links')?{source:null,created:[]}:path.endsWith('/subagents')?{subagents:[]}:{});
  unexpected.push(path);return route.fulfill({status:503,body:'Unexpected fixture API'});
 });
 await page.goto(base+'/story-workspace/chat');
 try {await expect(page.getByRole('button',{name:'Existing A',exact:true})).toBeVisible();}
 catch(cause){console.log('CACHE_ROUTE_DIAGNOSTIC '+JSON.stringify({calls,errors,unexpected,body:await page.locator('body').innerText()}));await page.screenshot({path:testInfo.outputPath('initial-route-failure.png')});throw cause;}
 const editor=page.locator('[contenteditable="true"]').first();await editor.fill('Retained draft text');
 await page.getByRole('button',{name:'Navigate timeline',exact:true}).click();await expect(page.getByText('Timeline fixture',{exact:true})).toBeVisible();await expect(page.getByTestId('retained-chat-route')).toBeHidden();
 const deckReads=calls.filter(path=>path==='/api/decks/catalog').length;
 await page.getByRole('button',{name:'Navigate chat',exact:true}).click();await expect(editor).toContainText('Retained draft text');expect(await page.evaluate(()=>(window as any).__routeCache.mounts)).toBe(1);
 await expect.poll(()=>calls.filter(path=>path==='/api/decks/catalog').length).toBeGreaterThan(deckReads);
 await page.getByRole('button',{name:'Existing A',exact:true}).click();await expect(page.getByTestId('chat-history-preview')).toContainText('Saved browser answer');
 await expect.poll(()=>calls.some(path=>path.endsWith('/status'))).toBe(true);expect(calls.filter(path=>path==='/api/claude-agent').length).toBe(0);
 statusHeld=false;releaseStatus();await expect(page.getByTestId('chat-history-preview')).toHaveCount(0);await expect(page.getByText('Saved browser answer',{exact:true})).toBeVisible();
 const scroller=page.locator('[data-chat-scroll-region="messages"]');
 console.log('CACHE_ROUTE_GEOMETRY '+JSON.stringify(await scroller.evaluate(element=>({scroll:element.scrollHeight,client:element.clientHeight,body:document.body.scrollHeight,viewport:innerHeight}))));
 await expect.poll(()=>scroller.evaluate(element=>element.scrollHeight>element.clientHeight)).toBe(true);
 await page.evaluate(()=>document.fonts.ready);
 await scroller.evaluate(async element=>{await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));element.scrollTo({top:120,behavior:'instant'});element.dispatchEvent(new Event('scroll'));});
 await expect.poll(()=>scroller.evaluate(element=>Math.abs(element.scrollTop-120))).toBeLessThan(3);
 console.log('CACHE_ROUTE_BEFORE_LEAVE '+JSON.stringify(await scroller.evaluate(element=>({top:element.scrollTop,scroll:element.scrollHeight,client:element.clientHeight}))));
 await page.getByRole('button',{name:'Navigate timeline',exact:true}).click();await page.getByRole('button',{name:'Navigate chat',exact:true}).click();
 console.log('CACHE_ROUTE_AFTER_RETURN '+JSON.stringify(await scroller.evaluate(element=>({top:element.scrollTop,scroll:element.scrollHeight,client:element.clientHeight}))));
 await expect.poll(()=>scroller.evaluate(element=>Math.abs(element.scrollTop-120))).toBeLessThan(3);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);expect(unexpected).toEqual([]);
 await page.screenshot({path:testInfo.outputPath('chat-cache-'+width+'.png')});
});
