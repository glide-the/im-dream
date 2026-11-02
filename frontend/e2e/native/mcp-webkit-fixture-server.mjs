// [Sync] 2026-10-31: persist closed-schema Native qualification phases beside synthetic MCP counters.
// [Input] App-owned production Next origin, original sandbox route and official MCP SDK with synthetic DTOs.
// [Output] Loopback-only technical provider/proxy, request counts and explicit local fault controls.
// [Pos] e2e boundary only; forwards fixed document/static resources, no Dream/Claude business or credentials.
import {createServer} from 'vite';
import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {StreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {RESOURCE_MIME_TYPE} from '@modelcontextprotocol/ext-apps';
import {randomUUID} from 'node:crypto';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../../',import.meta.url));
const [output,appOrigin]=process.argv.slice(2);if(!output||!appOrigin)throw Error('Explicit output directory and App Next origin required');
const app=new URL(appOrigin);if(!['http:','https:'].includes(app.protocol)||!['localhost','127.0.0.1','[::1]'].includes(app.hostname)||app.origin!==appOrigin)throw Error('App origin must be explicit loopback');
await mkdir(output,{recursive:true});const sessions=new Map();let origin,vite,fixture,sandbox;
const state={auth:true,enabled:true,revision:11,documentUnavailable:false,calls:0,restrictedCalls:0,restrictedAttempts:0,deletes:0,initializes:0,resources:0,policyReads:0,requests:[],qualification:[]};
const previous=new Map();
function publicState(){return {...state,requests:state.requests.slice(-100),activeSessions:sessions.size,appOrigin,origin};}
async function persist(){await writeFile(path.join(output,'fixture-state.json'),JSON.stringify(publicState(),null,2)+'\n');}
async function closeSessions(){for(const value of sessions.values())await value.server.close();sessions.clear();}
const flags={INK_MCP_APPS_PHASE1_PREVIEW:'true',INK_MCP_APPS_PHASE2_TOOL_CALLS:'true',INK_MCP_APPS_PHASE2_UI_MESSAGE:'true',INK_MCP_APPS_WINDOW_IM:'true'};
for(const [key,value] of Object.entries(flags)){previous.set(key,process.env[key]);process.env[key]=value;}
vite=await createServer({root,configFile:false,logLevel:'silent',ssr:{noExternal:['@ink-dream/mcp-apps-runtime','server-only']},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{name:'actual-webkit-technical-provider',enforce:'pre',resolveId(id){if(id==='server-only')return '\0server-only';},load(id){if(id==='\0server-only')return 'export {}';},configureServer(server){server.middlewares.use(async(req,res,next)=>{
 try{
  const url=new URL(req.url??'/',origin??'http://127.0.0.1');const json=(value,status=200)=>{res.statusCode=status;res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.end(JSON.stringify(value));};
  if(url.pathname==='/__fixture/state'){json({...publicState(),part:fixture.appPart});return;}
  if(url.pathname==='/__fixture/proof'&&req.method==='POST'){
   const chunks=[];for await(const chunk of req)chunks.push(Buffer.from(chunk));const body=JSON.parse(Buffer.concat(chunks).toString());
   const phases=['closed','reopened','complete','failed'],steps=['runtime','first_session','first_close','reopen','hidden_preservation','second_close'];
   if(Object.keys(body).some(key=>!['phase','step','elapsedMs','nativeThread'].includes(key))||!phases.includes(body.phase)||!steps.includes(body.step)||!Number.isSafeInteger(body.elapsedMs)||body.elapsedMs<0||!['webkit-thread','other-thread'].includes(body.nativeThread)){json({error:'invalid technical proof'},400);return;}
   if(state.qualification.length>=20){json({error:'technical proof limit'},400);return;}
   state.qualification.push({...body,deletes:state.deletes,initializes:state.initializes,resources:state.resources,activeSessions:sessions.size});await persist();json({accepted:true});return;
  }
  if(url.pathname==='/__fixture/control'&&req.method==='POST'){
   const chunks=[];for await(const chunk of req)chunks.push(Buffer.from(chunk));const body=JSON.parse(Buffer.concat(chunks).toString());
   if(body.reset===true){await closeSessions();Object.assign(state,{auth:true,enabled:true,revision:11,documentUnavailable:false,calls:0,restrictedCalls:0,restrictedAttempts:0,deletes:0,initializes:0,resources:0,policyReads:0,requests:[],qualification:[]});}
   for(const key of ['auth','enabled','documentUnavailable'])if(typeof body[key]==='boolean')state[key]=body[key];
   if(body.advanceRevision===true)state.revision++;await persist();json(publicState());return;
  }
  state.requests.push({path:url.pathname,method:req.method});if(state.requests.length>200)state.requests.shift();
  if(url.pathname==='/auth/session'){json(state.auth?{user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}:null,state.auth?200:401);return;}
  if(url.pathname==='/api/mcp-apps/phase1-status'){
   if(req.headers['x-ink-csrf']!=='a'.repeat(43)||url.searchParams.get('serverRef')!==fixture.serverRef||url.searchParams.get('workspaceScope')!==fixture.scope){json({error:'fixture boundary mismatch'},400);return;}
   state.policyReads++;json(fixture.policy(state.enabled,state.revision));return;
  }
  if(url.pathname==='/mcp-apps-sandbox'){
   const response=sandbox.GET(new Request(url));res.statusCode=response.status;response.headers.forEach((value,key)=>res.setHeader(key,value));res.end(Buffer.from(await response.arrayBuffer()));return;
  }
  if(url.pathname===`/api/mcp-apps/${fixture.serverRef}`){
   const chunks=[];for await(const chunk of req)chunks.push(Buffer.from(chunk));const body=chunks.length?JSON.parse(Buffer.concat(chunks).toString()):undefined;
   let session=sessions.get(String(req.headers['mcp-session-id']??''));
   if(!session&&req.method==='POST'&&body?.method==='initialize'){
    const mcp=new McpServer({name:'ios-mcp-webkit-fixture',version:'1.0.0'});
    mcp.registerTool(fixture.tool,{inputSchema:{},annotations:{readOnlyHint:true},_meta:{ui:{resourceUri:fixture.uri}}},async()=>{state.calls++;await persist();return fixture.result;});
    mcp.registerTool('write-page',{inputSchema:{},annotations:{readOnlyHint:false,destructiveHint:true}},async()=>{state.restrictedCalls++;await persist();return {content:[{type:'text',text:'Restricted fixture tool should remain uncalled'}]};});
    mcp.registerResource('fixture-form',fixture.uri,{mimeType:RESOURCE_MIME_TYPE},async()=>{state.resources++;await persist();return {contents:[{uri:fixture.uri,mimeType:RESOURCE_MIME_TYPE,text:fixture.appHtml,_meta:{ui:{csp:{connectDomains:[],resourceDomains:[],frameDomains:[],baseUriDomains:[]},permissions:{}}}}]};});
    const transport=new StreamableHTTPServerTransport({sessionIdGenerator:randomUUID,onsessioninitialized:id=>{sessions.set(id,{server:mcp,transport});state.initializes++;void persist();},onsessionclosed:id=>{sessions.delete(id);void persist();}});await mcp.connect(transport);session={server:mcp,transport};
   }
   if(!session){json({error:'missing technical session'},404);return;}
   // Explicit negative HTTP boundary; the real backend retains its permission classifier.
   if(req.method==='POST'&&body?.method==='tools/call'&&body.params?.name==='write-page'){state.restrictedAttempts++;await persist();json({error:'explicit_technical_tool_denial'},403);return;}
   if(req.method==='DELETE'){state.deletes++;await persist();}
   await session.transport.handleRequest(req,res,body);return;
  }
  const resource=url.pathname==='/native/tool-result'||url.pathname==='/runtime-config.js'||url.pathname.startsWith('/_next/')||url.pathname.startsWith('/fonts/')||url.pathname==='/favicon.ico'||url.pathname==='/placeholder-memory.png';
  if(resource&&req.method==='GET'){
   if(url.pathname==='/native/tool-result'&&state.documentUnavailable){json({error:'explicit technical document fault'},503);return;}
   const response=await fetch(new URL(url.pathname+url.search,appOrigin),{redirect:'manual'});res.statusCode=response.status;
   for(const [key,value] of response.headers)if(!['connection','transfer-encoding','content-encoding','content-length','set-cookie'].includes(key))res.setHeader(key,value);
   res.end(Buffer.from(await response.arrayBuffer()));return;
  }
  json({error:'outside explicit technical boundary'},404);
 }catch(error){res.statusCode=500;res.end('Technical fixture request failed');console.error(error?.name??'Error',error?.message??'Fixture failure');}
});}}]});
fixture=await vite.ssrLoadModule('/e2e/native/mcp-webkit-fixture.ts');
previous.set('INK_MCP_APPS_PLUGIN_MANIFEST_JSON',process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON);process.env.INK_MCP_APPS_PLUGIN_MANIFEST_JSON=JSON.stringify(fixture.plugin);
await vite.listen();const address=vite.httpServer.address();if(!address||typeof address==='string')throw Error('No technical port');origin=`http://127.0.0.1:${address.port}`;
previous.set('INK_DREAM_PUBLIC_ORIGIN',process.env.INK_DREAM_PUBLIC_ORIGIN);process.env.INK_DREAM_PUBLIC_ORIGIN=origin;
sandbox=await vite.ssrLoadModule('/app/mcp-apps-sandbox/route.ts');await persist();await writeFile(path.join(output,'fixture-info.json'),JSON.stringify({origin,appOrigin,provider:'synthetic official SDK server',nextResources:'forwarded from actual Simulator App',modelCalls:0,NotionCalls:0},null,2)+'\n');console.log(JSON.stringify({ready:true,origin,appOrigin}));
let stopping=false;async function stop(){if(stopping)return;stopping=true;await persist();await closeSessions();await vite.close();for(const [key,value] of previous)value===undefined?delete process.env[key]:process.env[key]=value;process.exit(0);}
process.on('SIGINT',()=>void stop());process.on('SIGTERM',()=>void stop());
