// [Sync] 2026-10-31: prove document identity and awaited original MCP DELETE before Native disposal acknowledgement.
// [Input] Production local tool document, original MCP Host/AppBridge/sandbox and an isolated official SDK MCP server.
// [Output] Same-document form persistence, two-part Chat ingress, approval/cell intents, session teardown and frame-source rejection.
// [Pos] Provider-free technical browser qualification; all users, policies, tools and HTTP results are explicit fixtures.
import {test,expect} from '@playwright/test';
import {createServer,transformWithEsbuild,type ViteDevServer} from 'vite';
import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {RESOURCE_MIME_TYPE} from '@modelcontextprotocol/ext-apps';
import {fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';
import {MCP_APPS_HOST_MANIFEST as manifest,mcpAppsSandboxUrl} from '../app/_dream/components/chat/mcp-apps/host-policy';
import {readToolResultEvent,readToolResultState,toolResultNavigationAllowed} from '../app/_dream/components/chat/ToolResultDocument.protocol';
const root=fileURLToPath(new URL('../',import.meta.url));
const serverRef='native-tool-fixture',scope='native-tool-workspace',tool='show-form',uri='ui://native-tool/form.html';
const result={content:[{type:'text',text:'Original saved result'}],structuredContent:{value:'saved'}};
const part={type:'dynamic-tool',toolName:`mcp__${serverRef}__${tool}`,toolCallId:'tool-form',state:'output-available',input:{},output:result,mcpAppResult:{version:1,serverRef,toolName:tool,toolCallId:'tool-form',input:{},workspaceScope:scope,resourceUri:uri,result}};
const plugin={manifestVersion:1,pluginId:manifest.pluginId,pluginVersion:manifest.version,revision:7,lifecycle:'enabled',browserEntry:manifest.browserEntry,nodeEntry:manifest.nodeEntry,protocol:{minimum:'2026-01-26',maximum:'2026-01-26'},sdk:{mcp:{minimum:'1.30.0',maximum:'1.30.0'},extApps:{minimum:'1.7.5',maximum:'1.7.5'},mcpUi:{minimum:'7.1.1',maximum:'7.1.1'}},features:{resourceReads:true,lowRiskToolCalls:true,uiMessage:true,windowIm:true}};
const features={readResource:true,appToolCalls:true,uiMessage:true,windowIm:true};
let revision=11,enabled=true,calls=0,deletes=0,authSession=true,holdDeletes=false;const deleteWaiters:(()=>void)[]=[];
function policy(){return {productionAppsEffective:false,manifest,default:{enabled:false,features:{readResource:false,appToolCalls:false,uiMessage:false,windowIm:false}},desired:{enabled:true,features},plugin,effective:{enabled,features},policy:{revision:`7:${revision}`,pluginRevision:'7',runtimePolicyRevision:revision,appSettingsRevision:null,manifestVersion:manifest.version,sandboxUrl:mcpAppsSandboxUrl('7'),sandboxTokens:['allow-scripts'],desiredPermissions:[],effectivePermissions:[],readyTimeoutMs:10000,policyPollMs:2000}};}
const appHtml=`<!doctype html><html><body><label>App draft<input id="draft"/></label><button id="send">Send follow-up</button><button id="call">Call read-only tool</button><output id="status">Starting</output><script>
const pending=new Map();let next=0;const status=document.querySelector('#status');
function request(method,params){const id='fixture-'+(++next);parent.postMessage({jsonrpc:'2.0',id,method,params},'*');return new Promise((resolve,reject)=>pending.set(id,{resolve,reject}));}
window.addEventListener('message',event=>{if(event.source!==parent)return;const message=event.data;if(message?.method==='ui/notifications/tool-result')status.textContent='Result received';if(pending.has(message?.id)){const p=pending.get(message.id);pending.delete(message.id);message.error?p.reject(Error(message.error.message)):p.resolve(message.result);}});
request('ui/initialize',{appInfo:{name:'native-tool-fixture',version:'1.0.0'},appCapabilities:{},protocolVersion:'2026-01-26'}).then(()=>{parent.postMessage({jsonrpc:'2.0',method:'ui/notifications/initialized'},'*');status.textContent='Ready';});
document.querySelector('#send').onclick=()=>request('ui/message',{role:'user',content:[{type:'text',text:document.querySelector('#draft').value},{type:'text',text:'Second text block'}]}).then(()=>status.textContent='Sent').catch(()=>status.textContent='Message failed');
document.querySelector('#call').onclick=()=>request('tools/call',{name:'${tool}',arguments:{}}).then(()=>status.textContent='Tool called').catch(()=>status.textContent='Tool denied');
</script></body></html>`;
const entry=`import React from 'react';import {createRoot} from 'react-dom/client';import '/app/_dream/i18n.ts';import Document from '/app/_dream/components/chat/ToolResultDocument.tsx';createRoot(document.querySelector('#root')).render(<Document/>);`;
let vite:ViteDevServer,origin:string;const sessions=new Map<string,{server:McpServer;transport:StreamableHTTPServerTransport}>();
const previousEnv=new Map<string,string|undefined>();
test.beforeAll(async()=>{
  for(const [key,value] of Object.entries({INK_MCP_APPS_PLUGIN_MANIFEST_JSON:JSON.stringify(plugin),INK_MCP_APPS_PHASE1_PREVIEW:'true',INK_MCP_APPS_PHASE2_TOOL_CALLS:'true',INK_MCP_APPS_PHASE2_UI_MESSAGE:'true',INK_MCP_APPS_WINDOW_IM:'true'})){previousEnv.set(key,process.env[key]);process.env[key]=value;}
  vite=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-native-tools-20261030/cache/tool-document',optimizeDeps:{include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','ai','zod','react-i18next','i18next','@mcp-ui/client','@modelcontextprotocol/ext-apps']},ssr:{noExternal:['@ink-dream/mcp-apps-runtime','server-only']},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{name:'tool-document-qualification',enforce:'pre',resolveId(id){if(id==='server-only')return '\0server-only';if(id==='/tool-document-entry.tsx')return '\0tool-document-entry';},async load(id){if(id==='\0server-only')return 'export {}';if(id==='\0tool-document-entry')return transformWithEsbuild(entry,'tool-document-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(server){server.middlewares.use(async(req,res,next)=>{
    try{
      const url=new URL(req.url??'/',origin??'http://127.0.0.1');
      const json=(data:unknown,status=200)=>{res.statusCode=status;res.setHeader('Content-Type','application/json');res.end(JSON.stringify(data));};
      if(url.pathname==='/auth/session'){json(authSession?{user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}:null,authSession?200:401);return;}
      if(url.pathname==='/api/mcp-apps/phase1-status'){expect(req.headers['x-ink-csrf']).toBe('a'.repeat(43));expect(url.searchParams.get('serverRef')).toBe(serverRef);expect(url.searchParams.get('workspaceScope')).toBe(scope);json(policy());return;}
      if(url.pathname==='/native/tool-result'){
        const html=await server.transformIndexHtml(url.pathname,`<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script>window.__toolEvents=[];window.ReactNativeWebView={postMessage:data=>window.__toolEvents.push(JSON.parse(data))};</script><script type="module" src="/tool-document-entry.tsx"></script></body></html>`);res.setHeader('Content-Type','text/html');res.end(html);return;
      }
      if(url.pathname==='/mcp-apps-sandbox'){
        const route=await server.ssrLoadModule('/app/mcp-apps-sandbox/route.ts'),response=await route.GET(new Request(url));res.statusCode=response.status;response.headers.forEach((value:string,key:string)=>res.setHeader(key,value));res.end(Buffer.from(await response.arrayBuffer()));return;
      }
      if(url.pathname===`/api/mcp-apps/${serverRef}`){
        const chunks:Buffer[]=[];for await(const chunk of req)chunks.push(Buffer.from(chunk));const body=chunks.length?JSON.parse(Buffer.concat(chunks).toString()):undefined;
        let session=sessions.get(String(req.headers['mcp-session-id']??''));
        if(!session&&req.method==='POST'&&body?.method==='initialize'){
          const mcp=new McpServer({name:'native-tool-fixture',version:'1.0.0'});
          mcp.registerTool(tool,{inputSchema:{},annotations:{readOnlyHint:true},_meta:{ui:{resourceUri:uri}}},async()=>{calls++;return result;});
          mcp.registerResource('fixture-form',uri,{mimeType:RESOURCE_MIME_TYPE},async()=>({contents:[{uri,mimeType:RESOURCE_MIME_TYPE,text:appHtml,_meta:{ui:{csp:{connectDomains:[],resourceDomains:[],frameDomains:[],baseUriDomains:[]},permissions:{}}}}]}));
          const transport=new StreamableHTTPServerTransport({sessionIdGenerator:randomUUID,onsessioninitialized:id=>sessions.set(id,{server:mcp,transport}),onsessionclosed:id=>sessions.delete(id)});await mcp.connect(transport);session={server:mcp,transport};
        }
        if(!session){json({error:'missing fixture session'},404);return;}if(req.method==='DELETE'){deletes++;if(holdDeletes)await new Promise<void>(resolve=>deleteWaiters.push(resolve));}
        await session.transport.handleRequest(req,res,body);return;
      }
      if(url.pathname==='/api/claude-agent/tool-confirm'){const chunks=[];for await(const chunk of req)chunks.push(Buffer.from(chunk));const body=JSON.parse(Buffer.concat(chunks).toString());json({ok:true,approved:body.approved});return;}
      next();
    }catch(error){next(error as Error);}
  });}}]});
  await vite.listen();const address=vite.httpServer!.address();if(!address||typeof address==='string')throw Error('No fixture address');origin=`http://127.0.0.1:${address.port}`;
  previousEnv.set('INK_DREAM_PUBLIC_ORIGIN',process.env.INK_DREAM_PUBLIC_ORIGIN);process.env.INK_DREAM_PUBLIC_ORIGIN=origin;
});
test.afterAll(async()=>{for(const release of deleteWaiters.splice(0))release();for(const session of sessions.values())await session.server.close();sessions.clear();await vite?.close();for(const [key,value] of previousEnv)value===undefined?delete process.env[key]:process.env[key]=value;});
test.beforeEach(async({page})=>{for(const release of deleteWaiters.splice(0))release();holdDeletes=false;enabled=true;authSession=true;revision=11;calls=0;deletes=0;await page.addInitScript(()=>localStorage.setItem('ink-language','en'));await page.goto(origin+'/native/tool-result');});
async function state(page:import('@playwright/test').Page,extra:Record<string,unknown>={}){
  await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='ready')?.documentId)).toBeTruthy();
  const documentId=await page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='ready').documentId);
  const value={type:'state',documentId,threadId:'fixture-thread',toolCallId:'tool-form',revision:1,part:structuredClone(part),presentation:'app-only',editorCompleted:false,active:true,settledToolCallIds:[],theme:'dark',language:'en',...extra};
  await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),value);return value;
}
const app=(page:import('@playwright/test').Page)=>page.frameLocator('[data-testid="im-mcp-app-host-frame"]').frameLocator('[data-testid="im-mcp-app-resource-frame"]');
test('original Host preserves an App form across document state refresh and acknowledges one unchanged two-part message',async({page})=>{
  const value=await state(page);await expect(app(page).getByLabel('App draft')).toBeVisible();await app(page).getByLabel('App draft').fill('Keep this draft');
  expect(calls).toBe(0);await state(page,{revision:2,theme:'light'});await expect(app(page).getByLabel('App draft')).toHaveValue('Keep this draft');
  await app(page).getByRole('button',{name:'Send follow-up'}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.filter((row:any)=>row.type==='user-message').length)).toBe(1);
  const event=await page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='user-message'));expect(event.message).toEqual({role:'user',parts:[{type:'text',text:'Keep this draft'},{type:'text',text:'Second text block'}]});
  await page.evaluate(reply=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(reply)})),{type:'result',documentId:value.documentId,threadId:value.threadId,toolCallId:value.toolCallId,requestId:event.requestId,accepted:true});await expect(app(page).getByText('Sent',{exact:true})).toBeVisible();
  await app(page).getByRole('button',{name:'Call read-only tool'}).click();await expect(app(page).getByText('Tool called',{exact:true})).toBeVisible();expect(calls).toBe(1);
  await page.getByTestId('mcp-app-close').click();await expect.poll(()=>deletes).toBe(1);
});
test('iframe messages cannot replace native document state, and a failed Chat acknowledgement returns its original error',async({page})=>{
  const value=await state(page);await expect(app(page).getByLabel('App draft')).toBeVisible();await app(page).getByLabel('App draft').fill('Frame draft');
  const inner=page.frames().find(frame=>frame.url()==='about:srcdoc');expect(inner).toBeTruthy();await inner!.evaluate(value=>parent.parent.postMessage(JSON.stringify({...value,revision:50,active:false}),'*'),value);
  await app(page).getByRole('button',{name:'Send follow-up'}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.some((row:any)=>row.type==='user-message'))).toBe(true);
  const event=await page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='user-message'));
  await page.evaluate(reply=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(reply)})),{type:'result',documentId:value.documentId,threadId:value.threadId,toolCallId:value.toolCallId,requestId:event.requestId,accepted:false});await expect(app(page).getByText('Message failed',{exact:true})).toBeVisible();
});
test('document protocol rejects malformed parts, crossed identities, unknown actions and top-level sandbox navigation',()=>{
  expect(readToolResultState({type:'state',part:{},documentId:'doc'})).toBeNull();
  expect(readToolResultEvent(JSON.stringify({type:'user-message',documentId:'doc',threadId:'thread',toolCallId:'tool',requestId:'request',message:{role:'user',parts:[{type:'text',text:'  '}]}}))).toBeNull();
  expect(readToolResultEvent(JSON.stringify({type:'execute',documentId:'doc',command:'ignored'}))).toBeNull();
  expect(toolResultNavigationAllowed(origin+'/native/tool-result',true,origin)).toBe(true);
  expect(toolResultNavigationAllowed(origin+mcpAppsSandboxUrl('7'),true,origin)).toBe(false);
  expect(toolResultNavigationAllowed(origin+mcpAppsSandboxUrl('7'),false,origin)).toBe(true);
  expect(toolResultNavigationAllowed('https://example.invalid/',false,origin)).toBe(false);
});


test('an expired local document session notifies the existing native login owner without submitting a message',async({page})=>{
  authSession=false;await state(page);await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.filter((row:any)=>row.type==='session-expired').length)).toBe(1);expect(await page.evaluate(()=>(window as any).__toolEvents.filter((row:any)=>row.type==='user-message').length)).toBe(0);
});

const editorPart={type:'dynamic-tool',toolName:'mcp__editor__write_segment',toolCallId:'editor-call',state:'input-available',input:{cellId:'fixture-cell',editor_session_id:'fixture-editor',content:'Original proposed note.'}};
test('the original editor approval posts its original confirmation and returns only matched domain events',async({page})=>{
  await state(page,{part:editorPart,toolCallId:editorPart.toolCallId,presentation:'editor'});
  const request=page.waitForRequest(value=>new URL(value.url()).pathname==='/api/claude-agent/tool-confirm');
  await page.getByRole('button',{name:'Accept change',exact:true}).click();
  expect((await request).postDataJSON()).toMatchObject({thread_id:'fixture-thread',tool_call_id:'editor-call',approved:true});
  await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.filter((value:any)=>value.type==='tool-result').length)).toBe(1);
  const events=await page.evaluate(()=>(window as any).__toolEvents);
  expect(events.find((value:any)=>value.type==='tool-result')).toMatchObject({threadId:'fixture-thread',toolCallId:'editor-call',tool:editorPart.toolName,output:{approved:true}});
  expect(events.filter((value:any)=>value.type==='confirmation-settled')).toHaveLength(1);
  expect(events.filter((value:any)=>value.type==='editor-confirmed')).toHaveLength(1);
  expect(events.filter((value:any)=>value.type==='user-message')).toHaveLength(0);
});
test('a saved editor result preserves its original note target and an incomplete history has no live approval',async({page})=>{
  const value=await state(page,{part:{...editorPart,state:'output-available',output:{ok:true,cellId:'fixture-cell'}},toolCallId:editorPart.toolCallId,presentation:'editor',editorCompleted:true});
  await page.getByRole('button',{name:'Jump to note',exact:true}).click();
  expect(await page.evaluate(()=>(window as any).__toolEvents.find((value:any)=>value.type==='editor-jump'))).toMatchObject({toolCallId:'editor-call',detail:{cellId:'fixture-cell',editorSessionId:'fixture-editor'}});
  await state(page,{revision:value.revision+1,part:editorPart,toolCallId:editorPart.toolCallId,presentation:'editor',editorCompleted:true});
  await expect(page.getByRole('button',{name:'Accept change',exact:true})).toHaveCount(0);
  // Missing output retains the original completed-card compatibility; no new live approval is created.
  await state(page,{revision:value.revision+2,part:{...editorPart,state:'output-error',errorText:JSON.stringify({ok:false,error:'target_missing'})},toolCallId:editorPart.toolCallId,presentation:'editor',editorCompleted:true});
  await expect(page.getByText('The note was not changed',{exact:true})).toBeVisible();
});


test('Native document disposal ignores crossed identity and waits for original MCP DELETE before acknowledgement',async({page})=>{
  const value=await state(page);await expect(app(page).getByLabel('App draft')).toBeVisible();
  await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'dispose',documentId:'other-document',threadId:value.threadId,toolCallId:value.toolCallId,requestId:'crossed'});
  await expect(app(page).getByLabel('App draft')).toBeVisible();expect(deletes).toBe(0);
  holdDeletes=true;
  await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'dispose',documentId:value.documentId,threadId:value.threadId,toolCallId:value.toolCallId,requestId:'dispose-current'});
  await expect.poll(()=>deletes).toBe(1);
  expect(await page.evaluate(()=>(window as any).__toolEvents.filter((event:any)=>event.type==='disposed').length)).toBe(0);
  for(const release of deleteWaiters.splice(0))release();
  await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.filter((event:any)=>event.type==='disposed').length)).toBe(1);
  expect(await page.evaluate(()=>(window as any).__toolEvents.find((event:any)=>event.type==='disposed'))).toEqual({type:'disposed',documentId:value.documentId,threadId:value.threadId,toolCallId:value.toolCallId,requestId:'dispose-current'});
  await expect(page.getByTestId('mcp-app-panel')).toHaveCount(0);
});
