// [Input] Production native HTTP transport with an injected native-module boundary.
// [Output] Request cancellation before/after headers, concurrency, late-head and EOF cleanup evidence.
// [Pos] Provider-free transport qualification; no business endpoint, backend or model is called.
// [Sync] 2026-10-29: response metadata survives error-body buffering so the shared resource API can honor Retry-After.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const native=`
const f=window.__httpFixture={opened:[],cancelled:[],reads:[],results:{},responseHeaders:{},controllers:{},requests:new Map(),lateHead:false,holdBody:false,legacyIds:false};
export const NativeModules={InkRuntime:{
 openRequest(options){const id=f.legacyIds?'host_'+f.opened.length:options.id||'legacy_'+f.opened.length;const key=options.path.split('/').pop();f.opened.push({...options,id});return new Promise((resolve,reject)=>f.requests.set(id,{id,key,resolve,reject,chunks:[],reader:null}));},
 readResponse(id){f.reads.push(id);const r=f.requests.get(id);if(!r)return Promise.reject(Error('HTTP_RESPONSE_CLOSED'));if(f.holdBody)return new Promise((resolve,reject)=>r.reader={resolve,reject});const text=r.chunks.shift()||'';return Promise.resolve({text,done:r.chunks.length===0});},
 cancelRequest(id){f.cancelled.push(id);const r=f.requests.get(id);if(!r||f.lateHead)return;r.reject(Error('HTTP_CANCELLED'));r.reader?.reject(Error('HTTP_CANCELLED'));}
}};
`;
const entry=`
import {clientFetch} from '/src/platform/transport.native.ts';
const f=window.__httpFixture;
f.start=(key,options={})=>{const controller=new AbortController();f.controllers[key]=controller;if(options.aborted)controller.abort();const {aborted,...init}=options;f.results[key]={state:'pending'};void clientFetch('/api/fixture/'+key,{...init,signal:controller.signal}).then(async response=>{f.responseHeaders[key]=Object.fromEntries(response.headers);f.results[key]={state:'complete',status:response.status,text:await response.text()};}).catch(error=>{f.results[key]={state:'error',message:error.message};});};
f.head=(key,status=200,chunks=['fixture reply'],headers={})=>{const r=Array.from(f.requests.values()).find(r=>r.key===key);if(!r)throw Error('Missing fixture request');r.chunks=[...chunks];r.resolve({id:r.id,status,headers});};
document.querySelector('#root').textContent='Native HTTP transport fixture ready';
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-http-cancel-vite-20261028',optimizeDeps:{noDiscovery:true},server:{host:'127.0.0.1',port:0},plugins:[{
  name:'native-http-cancel-production',enforce:'pre',resolveId(id){if(id==='react-native')return '\0http-native';if(id==='/http-fixture.ts')return '\0http-entry';},
  async load(id){const source=id==='\0http-native'?native:id==='\0http-entry'?entry:null;return source?(await transformWithEsbuild(source,'http-fixture.ts',{loader:'ts'})).code:null;},
  configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/http-fixture')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/http-fixture','<html><head><link rel="icon" href="data:,"></head><body><main id="root"></main><script type="module" src="/http-fixture.ts"></script></body></html>'));});},
 }]});await server.listen();base=server.resolvedUrls!.local[0]+'http-fixture';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.goto(base);await expect(page.getByText('Native HTTP transport fixture ready')).toBeVisible();});
test.afterEach(async({page},info)=>{await info.attach('transport-boundary',{body:JSON.stringify(await facts(page)),contentType:'application/json'});expect(diagnostics.get(page)).toEqual([]);});
async function facts(page:Page){return page.evaluate(()=>{const f=(window as any).__httpFixture;return {opened:f.opened,cancelled:f.cancelled,reads:f.reads,results:f.results};});}
async function result(page:Page,key:string){await expect.poll(async()=>(await facts(page)).results[key]?.state).not.toBe('pending');return (await facts(page)).results[key];}
test('an already-aborted read never creates a native request',async({page})=>{
 await page.evaluate(()=>(window as any).__httpFixture.start('early',{aborted:true}));expect(await result(page,'early')).toEqual({state:'error',message:'HTTP_ABORTED'});expect((await facts(page)).opened).toEqual([]);expect((await facts(page)).cancelled).toEqual([]);
});
test('abort before headers cancels the same native request without waiting for response data',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.start('pending');f.controllers.pending.abort();});expect(await result(page,'pending')).toEqual({state:'error',message:'HTTP_ABORTED'});const f=await facts(page);expect(f.opened).toHaveLength(1);expect(f.cancelled).toEqual([f.opened[0].id]);expect(f.reads).toEqual([]);
});
test('concurrent read cancellation leaves the other response and original request fields intact',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.start('cancel');f.start('keep',{method:'POST',headers:{'x-ink-csrf':'fixture-csrf','content-type':'application/json'},body:'{"text":"中文"}'});f.controllers.cancel.abort();f.head('keep',201,['first ','中文']);});
 expect(await result(page,'cancel')).toMatchObject({state:'error'});expect(await result(page,'keep')).toEqual({state:'complete',status:201,text:'first 中文'});const f=await facts(page);expect(f.opened[0].id).not.toBe(f.opened[1].id);expect(f.opened[1]).toMatchObject({path:'/api/fixture/keep',method:'POST',headers:{'x-ink-csrf':'fixture-csrf','content-type':'application/json'},body:'{"text":"中文"}'});expect(f.reads.every((id:string)=>id===f.opened[1].id)).toBe(true);
});
test('a response head delivered after abort cannot start reading its body',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.lateHead=true;f.start('late');f.controllers.late.abort();});expect((await facts(page)).cancelled).toHaveLength(1);await page.evaluate(()=>(window as any).__httpFixture.head('late'));expect(await result(page,'late')).toEqual({state:'error',message:'HTTP_ABORTED'});expect((await facts(page)).reads).toEqual([]);
});
test('abort during body reading cancels the original native reader',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.holdBody=true;f.start('body');f.head('body');});await expect.poll(async()=>(await facts(page)).reads.length).toBe(1);await page.evaluate(()=>(window as any).__httpFixture.controllers.body.abort());expect(await result(page,'body')).toMatchObject({state:'error'});const f=await facts(page);expect(f.cancelled.every((id:string)=>id===f.opened[0].id)).toBe(true);
});
test('EOF removes abort listeners and retains no future cancellation action',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.start('done');f.head('done');});expect(await result(page,'done')).toEqual({state:'complete',status:200,text:'fixture reply'});const before=(await facts(page)).cancelled;await page.evaluate(()=>(window as any).__httpFixture.controllers.done.abort());expect((await facts(page)).cancelled).toEqual(before);
});
test('a legacy host response ID is cancelled when its head arrives after abort',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.legacyIds=true;f.lateHead=true;f.start('legacy');f.controllers.legacy.abort();f.head('legacy');});expect(await result(page,'legacy')).toEqual({state:'error',message:'HTTP_ABORTED'});const f=await facts(page);expect(f.cancelled).toContain(f.opened[0].id);expect(f.reads).toEqual([]);
});
test('buffered native error responses preserve original Retry-After metadata',async({page})=>{
 await page.evaluate(()=>{const f=(window as any).__httpFixture;f.start('cooldown');f.head('cooldown',409,['{"detail":{"code":"NOTION_SYNC_BUSY"}}'],{'retry-after':'60','content-type':'application/json'});});
 expect(await result(page,'cooldown')).toEqual({state:'complete',status:409,text:'{"detail":{"code":"NOTION_SYNC_BUSY"}}'});
 expect(await page.evaluate(()=>(window as any).__httpFixture.responseHeaders.cooldown)).toEqual({'retry-after':'60','content-type':'application/json'});
});
