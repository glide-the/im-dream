// [Input] Production native attachment hook, shared storage strategy and native HTTP adapter.
// [Output] Provider-free upload/workspace/progress/cleanup evidence through a narrow native-module fixture.
// [Pos] Technical bridge harness; no real files, accounts, network storage, backend or database writes.
import {test,expect,type Page} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {createServer as createNetServer} from 'node:net';
test.use({channel:'chrome',actionTimeout:10_000});
const moduleSource=`
const fixture=window.__uploadFixture={mode:'server',requests:[],uploads:[],released:[],cancelled:[],reads:[],responses:new Map(),listeners:new Set()};
let sequence=0;
function head(path,status,body,id='read-'+(++sequence)){fixture.responses.set(id,{path,body:JSON.stringify(body)});return {id,status};}
const runtime={
 async openRequest(options){
  fixture.requests.push(options);
  if(options.path==='/auth/session')return head(options.path,200,{user:{id:'1',email:'fixture@example.test',display_name:'Fixture',avatar_url:null,role:'user',created_at:null},csrf_token:'x'.repeat(43)});
  if(options.path==='/api/storage')return head(options.path,200,{type:'s3',supportsDirectUpload:['direct','fallback','directfail'].includes(fixture.mode),isConfigured:fixture.mode!=='notconfigured'});
  if(options.path==='/api/storage/upload-url')return fixture.mode==='fallback'?head(options.path,503,{}):head(options.path,200,{directUploadSupported:true,key:'fixture-key',url:'https://storage.example/presigned',method:'PUT',headers:{'Content-Type':'text/plain'}});
  throw new Error('Unexpected fixture HTTP path '+options.path);
 },
 async readResponse(id){const response=fixture.responses.get(id);if(!response)throw new Error('Unknown response');fixture.reads.push(response.path);fixture.responses.delete(id);return {text:response.body,done:true};},
 cancelRequest(id){fixture.cancelled.push(id);fixture.responses.delete(id);},
 async pickFiles(){return fixture.mode==='oversize'?{files:[],rejected:[{name:'oversized.txt'}]}:{files:[{id:'fixture-file',uri:'file:///fixture-only/picked.txt',name:'picked.txt',type:'text/plain',size:7}],rejected:[]};},
 releaseFiles(ids){fixture.released.push(...ids);},
 async openFileUpload(options){
  fixture.uploads.push(options);
  for(const listener of fixture.listeners){listener({id:options.id,progress:37});listener({id:options.id,progress:100});}
  if(options.url)return head(options.url,fixture.mode==='directfail'?500:200,{},options.id);
  if(options.path==='/api/workspace/files')return fixture.mode==='workspacefail'?head(options.path,409,{error:'Workspace unavailable',code:'WORKSPACE_DISABLED'},options.id):head(options.path,200,{files:[{workspacePath:'files/picked.txt',savedAt:'2026-10-28T00:00:00Z',hash:'fixture-hash'}]},options.id);
  if(options.path==='/api/storage/upload')return head(options.path,fixture.mode==='serverfail'?500:200,fixture.mode==='nokey'?{}:{key:'fixture-key',url:'/api/storage/file/fixture',metadata:{contentType:'text/plain',size:7}},options.id);
  throw new Error('Unexpected upload path');
 }
};
export const NativeModules={InkRuntime:runtime};
export class NativeEventEmitter{addListener(name,listener){if(name!=='InkUploadProgress')throw new Error('Unexpected event');fixture.listeners.add(listener);return {remove(){fixture.listeners.delete(listener);}};}}
`;
const entry=`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import useFileAttachments from '/app/_dream/components/chat/useFileAttachments.native.ts';
import {createNativeFileUploadAdapter} from '/src/platform/fileUpload.native.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import {clientFetch} from '/src/platform/transport.native.ts';
await loadBrowserSession(clientFetch);
window.__uploadFixture.batch=async()=>{const adapter=createNativeFileUploadAdapter();try{return (await adapter.uploadWorkspaceBatch([{id:'fixture-a',uri:'file:///a',name:'a.txt',type:'text/plain',size:1,relativePath:'Folder/a.txt'},{id:'fixture-b',uri:'file:///b',name:'b.txt',type:'text/plain',size:1,relativePath:['Folder','sub','b.txt'].join(String.fromCharCode(92))}],'fixture-thread','project')).status;}finally{adapter.dispose();}};
function UploadCase({workspace}){
 const [files,setFiles]=useState([]);const upload=useFileAttachments(workspace?'fixture-session':undefined);
 return React.createElement('main',null,
  React.createElement('button',{onClick:()=>upload.chooseFiles(setFiles)},'Choose files'),
  React.createElement('button',{onClick:()=>files.forEach(file=>upload.deleteFile(file.id,setFiles))},'Remove files'),
  React.createElement('output',{'aria-label':'Files'},JSON.stringify(files)),
  React.createElement('output',{'aria-label':'Error'},upload.error ?? ''));
}
function Harness(){const [mode,setMode]=useState('server'),[workspace,setWorkspace]=useState(false),[generation,setGeneration]=useState(0);
 return React.createElement(React.Fragment,null,
 React.createElement('select',{'aria-label':'Strategy',value:mode,onChange:event=>{window.__uploadFixture.mode=event.target.value;setMode(event.target.value);setGeneration(value=>value+1);}},['server','direct','fallback','notconfigured','directfail','workspacefail','nokey','oversize'].map(value=>React.createElement('option',{key:value},value))),
 React.createElement('label',null,'Workspace',React.createElement('input',{type:'checkbox',checked:workspace,onChange:event=>{setWorkspace(event.target.checked);setGeneration(value=>value+1);}})),
 React.createElement(UploadCase,{key:generation,workspace}));}
createRoot(document.querySelector('#root')).render(React.createElement(Harness));
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  const port=await new Promise<number>((resolve,reject)=>{const probe=createNetServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{const address=probe.address();if(!address||typeof address==='string')return reject(new Error('port'));probe.close(error=>error?reject(error):resolve(address.port));});});
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',optimizeDeps:{exclude:['react-native']},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'native-upload-fixture',enforce:'pre',
    configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/upload-fixture')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/upload-fixture','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/upload-fixture.js"></script></body></html>'));});},
    resolveId(id){return id==='react-native'?'\0native-upload-module.js':id==='/upload-fixture.js'?'\0upload-fixture.js':null;},
    load(id){return id==='\0native-upload-module.js'?moduleSource:id==='\0upload-fixture.js'?entry:null;},
  }]});await server.listen();base=`http://127.0.0.1:${port}/upload-fixture`;
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
  page.on('pageerror',error=>{throw error;});
  await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
  await page.goto(base);await expect(page.getByRole('button',{name:'Choose files'})).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>((window as any).__uploadFixture?.reads ?? []).includes('/api/storage'))).toBe(true);
});
async function mode(page:Page,value:string) {
  const count=await page.evaluate(()=>((window as any).__uploadFixture.reads as string[]).filter(path=>path==='/api/storage').length);
  await page.getByLabel('Strategy').selectOption(value);
  await expect.poll(()=>page.evaluate(()=>((window as any).__uploadFixture.reads as string[]).filter(path=>path==='/api/storage').length)).toBeGreaterThan(count);
}
async function snapshot(page:Page) {return page.evaluate(()=>{const fixture=(window as any).__uploadFixture;return {uploads:fixture.uploads,released:fixture.released,requests:fixture.requests};});}
test('server upload retains metadata, progress, CSRF and native copy ownership',async({page})=>{
  await page.getByRole('button',{name:'Choose files'}).click();
  await expect(page.getByLabel('Files')).toContainText('"storageKey":"fixture-key"');await expect(page.getByLabel('Files')).toContainText('"progress":100');
  const value=await snapshot(page);expect(value.uploads[0].fileId).toBe('fixture-file');expect(value.uploads[0].headers['x-ink-csrf']).toHaveLength(43);expect(value.released).toEqual([]);
  await page.getByRole('button',{name:'Remove files'}).click();await expect(page.getByLabel('Files')).toHaveText('[]');expect((await snapshot(page)).released).toContain('fixture-file');
});
test('direct upload uses the issued URL/method/headers without Cookie or CSRF',async({page})=>{
  await mode(page,'direct');await page.getByRole('button',{name:'Choose files'}).click();await expect(page.getByLabel('Files')).toContainText('"storageKey":"fixture-key"');
  const value=await snapshot(page);expect(value.uploads).toHaveLength(1);expect(value.uploads[0].url).toBe('https://storage.example/presigned');expect(value.uploads[0].method).toBe('PUT');expect(value.uploads[0].headers).toEqual({'Content-Type':'text/plain'});
});
test('unavailable direct URL falls back to the same server upload',async({page})=>{
  await mode(page,'fallback');await page.getByRole('button',{name:'Choose files'}).click();await expect(page.getByLabel('Files')).toContainText('"storageKey":"fixture-key"');expect((await snapshot(page)).uploads[0].path).toBe('/api/storage/upload');
});
test('workspace synchronization precedes storage and retains path/time/hash',async({page})=>{
  await page.getByLabel('Workspace').check();await page.getByRole('button',{name:'Choose files'}).click();await expect(page.getByLabel('Files')).toContainText('"hash":"fixture-hash"');
  const value=await snapshot(page);expect(value.uploads.map((item:any)=>item.path)).toEqual(['/api/workspace/files','/api/storage/upload']);expect(value.uploads[0].fields).toEqual({sessionId:'fixture-session',path:'files'});
});
for(const value of ['notconfigured','directfail','workspacefail','nokey'])test(`${value} keeps original error behavior and releases its native copy`,async({page})=>{
  await mode(page,value);if(value==='workspacefail')await page.getByLabel('Workspace').check();await page.getByRole('button',{name:'Choose files'}).click();
  await expect(page.getByLabel('Error')).not.toHaveText('');await expect(page.getByLabel('Files')).toHaveText('[]');await expect.poll(async()=>(await snapshot(page)).released).toContain('fixture-file');
  const uploads=(await snapshot(page)).uploads;if(value==='workspacefail')expect(uploads.map((item:any)=>item.path)).toEqual(['/api/workspace/files']);if(value==='directfail')expect(uploads).toHaveLength(1);
});
test('oversize rejection performs no upload and preserves the original file-size message',async({page})=>{
  await mode(page,'oversize');await page.getByRole('button',{name:'Choose files'}).click();await expect(page.getByLabel('Error')).toContainText('oversized.txt');await expect(page.getByLabel('Files')).toHaveText('[]');expect((await snapshot(page)).uploads).toEqual([]);
});

test('original native Workspace batch keeps file IDs and relative paths in a single authenticated request',async({page})=>{
 expect(await page.evaluate(()=>(window as any).__uploadFixture.batch())).toBe(200);const uploads=await page.evaluate(()=>(window as any).__uploadFixture.uploads);expect(uploads).toHaveLength(1);expect(uploads[0]).toMatchObject({fileIds:['fixture-a','fixture-b'],relativePaths:['Folder/a.txt','Folder/sub/b.txt'],path:'/api/workspace/files',fields:{sessionId:'fixture-thread',path:'project'}});expect(uploads[0].fileId).toBeUndefined();expect(uploads[0].headers['x-ink-csrf']).toHaveLength(43);expect(uploads[0].headers.Authorization).toBeUndefined();
});
