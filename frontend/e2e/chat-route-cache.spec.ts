// [Input] Production StoryWorkspaceRouter/ChatView and explicit synthetic session/catalog/history HTTP boundaries.
// [Output] Desktop/narrow retained Chat mount, draft, catalog refresh and prose-before-status evidence.
// [Pos] Provider-free browser qualification; no normal account, database, model or native runtime writes.
import {test,expect} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';

let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-chat-cache-20261103-validation/vite-web-route-real-entry',resolve:{alias:[{find:/^react-native$/,replacement:'react-native-web'}],extensions:['.web.tsx','.tsx','.web.ts','.ts','.web.js','.js','.mjs','.json']},optimizeDeps:{entries:['e2e/fixtures/chat-route-cache.tsx']},server:{host:'127.0.0.1',port:0},plugins:[{name:'chat-route-cache',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(!req.url?.startsWith('/story-workspace/'))return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/story-workspace/chat','<html><head><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/e2e/fixtures/chat-route-cache.tsx"></script></body></html>'));});}}]});await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('PORT');base='http://127.0.0.1:'+address.port;
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
  if(path==='/api/system-config')return json({data:{workspace_enabled:false,im_full_access_enabled:false}});
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
