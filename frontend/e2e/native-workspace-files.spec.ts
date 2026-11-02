// [Input] Production Native Workspace resources/hook/preview/Markdown and explicit native-file/AppState fixtures.
// [Output] URI/permission/identity isolation, binary-handle ownership, document/image/material/export and cancellation contracts.
// [Pos] Provider-free technical lane; native filesystem bytes are separately validated by XCTest, no real account/backend/model calls.
// [Sync] 2026-10-28: encode synthetic Markdown as JavaScript data when embedding the TSX harness.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
const fixtureImage=readFileSync(fileURLToPath(new URL('../public/placeholder-memory.png',import.meta.url))).toString('base64');
const reportMarkdown='# Workspace report\n\nOriginal report body. [Sibling](notes.md)\n\n<script>window.__executed=true</script>';
const inlineMarkdown='Before image.\n\n![Fixture image](workspace://files/image.png)\n\nAfter image.';
// RN Image supplies nativeEvent.source; RNW 0.21 supplies the DOM load Event.
// Adapt only that platform event at the explicitly synthetic browser boundary.
const imagePlatform=`
import React from 'react';import {Image as WebImage} from 'react-native-web';export * from 'react-native-web';
export const Image=React.forwardRef(({onLoad,...props},ref)=><WebImage {...props} ref={ref} onLoad={event=>{
 WebImage.getSize(props.source.uri,(width,height)=>onLoad?.({nativeEvent:{source:{width,height,uri:props.source.uri}}}),props.onError);
}}/>);
`;
const entry=`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';import {AppState} from 'react-native';
import FileSidebar from '/app/_dream/components/dashboard/FileSidebar.native.tsx';
import WorkspaceFilePreview from '/app/_dream/components/chat/WorkspaceFilePreview.native.tsx';
import ChatMarkdown from '/app/_dream/components/chat/ChatMarkdown.native.tsx';
import useNativeWorkspaceFile from '/app/_dream/components/chat/useNativeWorkspaceFile.native.ts';
import {createWorkspaceResources} from '/src/platform/workspaceFiles.native.ts';
import {WorkspaceFileRequestError} from '/app/_dream/components/chat/workspaceFileAccess.ts';
import {loadBrowserSession,clearBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
await i18n.changeLanguage('en');
const restoreSession=()=>loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));await restoreSession();
Object.defineProperty(AppState,'currentState',{value:'active',writable:true,configurable:true});AppState.listeners=new Set();AppState.addEventListener=(_,fn)=>{AppState.listeners.add(fn);return {remove:()=>AppState.listeners.delete(fn)};};
const png='data:image/png;base64,${fixtureImage}';
const f=window.__workspaceFixture={acquired:[],released:[],copies:[],exports:[],added:[],held:[],exportHeld:[],hold:false,holdExport:false,failed:false,serial:0,rawOptions:[],rawReleases:[],rawCancels:[],rawStatus:null,rawHold:false,rawHeld:[],sessionExpirations:0,probe:null,external:[]};
const meta=(path)=>({id:'resource-'+(++f.serial),uri:path.endsWith('.png')?png:'file:///fixture/'+f.serial,name:path.split('/').at(-1)+(path==='files/folder'?'.zip':''),type:path.endsWith('.md')?'text/markdown':path.endsWith('.png')?'image/png':'application/zip',size:12});
const io={
 async acquire(input,signal){f.acquired.push({...input,signal});if(f.failed)throw new WorkspaceFileRequestError('retryable');const file=meta(input.path);return f.hold?new Promise(resolve=>f.held.push({file,signal,release:()=>resolve(file)})):file;},
 async text(file){return file.name==='notes.md'?'# Linked notes':${JSON.stringify(reportMarkdown)};},
 async copy(file){const copy={...file,id:'material-'+(++f.serial)};f.copies.push({source:file.id,copy:copy.id});return copy;},
 async export(file){f.exports.push(file.id);return f.holdExport?new Promise(resolve=>f.exportHeld.push(resolve)):{completed:false};},
 release(file){f.released.push(file.id);},
};
const rawRuntime={
 async readWorkspaceFile(options){f.rawOptions.push(options);if(f.rawStatus)throw Object.assign(new Error('fixture status'),{code:'WORKSPACE_HTTP_'+f.rawStatus});const file={id:'native-'+(++f.serial),uri:'file:///private/fixture-'+f.serial,name:'fixture.zip',type:'application/zip',size:7};return f.rawHold?new Promise(resolve=>f.rawHeld.push(()=>resolve(file))):file;},
 cancelWorkspaceFile(id){f.rawCancels.push(id);},releaseFiles(ids){f.rawReleases.push(...ids);},async readWorkspaceText(){return 'Native fixture text';},async copyWorkspaceFile(id){return {id:'native-copy-'+(++f.serial),uri:'file:///private/copy',name:'copy.png',type:'image/png',size:7};},async exportFile(){return {completed:false};},
};
f.raw=createWorkspaceResources(rawRuntime,()=>f.sessionExpirations++);f.clearSession=clearBrowserSession;f.restoreSession=restoreSession;
f.background=()=>{AppState.currentState='background';AppState.listeners.forEach(fn=>fn('background'));};f.foreground=()=>{AppState.currentState='active';AppState.listeners.forEach(fn=>fn('active'));};
function Probe({thread,availability,uri}){const result=useNativeWorkspaceFile({uri,threadId:thread,availability,resources:io});f.probe=result.state;return <output aria-label="Lease state">{JSON.stringify(result.state)}</output>;}
const directoryFile={name:'report.md',path:'report.md',isDirectory:false,size:12,modifiedAt:'2026-10-28T00:00:00Z'};
f.directoryCalls=[];f.directoryWrites=[];f.directoryPicks=[];f.directoryUploads=[];f.directoryHeld=[];f.holdDirectory=false;f.failDelete=false;f.pickCancelled=false;f.removed=false;f.holdDirectoryUpload=false;f.directoryUploadHeld=[];f.directoryDisposals=0;
const directoryTransport=async(input,init)=>{const url=new URL(String(input),'http://fixture.invalid');f.directoryCalls.push({thread:url.searchParams.get('sessionId'),method:init?.method||'GET',signal:init?.signal});
 if(init?.method==='DELETE'){f.directoryWrites.push({body:JSON.parse(init.body),headers:init.headers});if(f.failDelete)return Response.json({error:'Fixture delete denied'},{status:403});f.removed=true;return Response.json({deleted:true});}
 const thread=url.searchParams.get('sessionId');const body={tree:f.removed?[]:[{...directoryFile,name:thread==='fixture-thread-b'?'other.md':'report.md',path:thread==='fixture-thread-b'?'other.md':'report.md'},{name:'project',path:'project',isDirectory:true,size:0,modifiedAt:directoryFile.modifiedAt,children:[{...directoryFile,path:'project/report.md'}]}]};
 return f.holdDirectory?new Promise(resolve=>f.directoryHeld.push(()=>resolve(Response.json(body)))):Response.json(body);
};
const directoryPicker=async(max,directory)=>{f.directoryPicks.push({max,directory});return {files:f.pickCancelled?[]:directory?[{id:'picked-a',uri:'file:///picked-a',name:'a.txt',type:'text/plain',size:1,relativePath:'Folder/a.txt'},{id:'picked-b',uri:'file:///picked-b',name:'b.txt',type:'text/plain',size:1,relativePath:'Folder/sub/b.txt'}]:[{id:'picked-file',uri:'file:///picked-file',name:'picked.txt',type:'text/plain',size:2}],rejected:[]};};
const directoryUploads={async uploadWorkspaceBatch(files,thread,path){f.directoryUploads.push({files,thread,path});const response=Response.json({uploaded:files.map(file=>file.relativePath||file.name)});return f.holdDirectoryUpload?new Promise(resolve=>f.directoryUploadHeld.push(()=>resolve(response))):response;},dispose(){f.directoryDisposals++;}};
function Harness(){
 const [filesOpen,setFilesOpen]=useState(false);const [uri,setUri]=useState(null),[thread,setThread]=useState('fixture-thread-a'),[availability,setAvailability]=useState('enabled'),[probe,setProbe]=useState(false),[probeUri,setProbeUri]=useState('workspace://files/probe.md'),[draft,setDraft]=useState('Keep the source draft');
 f.setThread=setThread;f.setAvailability=setAvailability;f.setProbe=setProbe;f.setProbeUri=setProbeUri;
 const add=async file=>{f.added.push(file.id);return true;};
 return <div style={{height:'100vh',display:'flex',flexDirection:'column',padding:8,boxSizing:'border-box'}}>
  <textarea aria-label="Source draft" value={draft} onChange={event=>setDraft(event.target.value)}/>
  <div><button onClick={()=>setFilesOpen(true)}>Open files</button><button onClick={()=>setUri('workspace://files/report.md')}>Open report</button><button onClick={()=>setUri('workspace://files/folder')}>Download folder</button><button onClick={()=>setProbe(value=>!value)}>Toggle lease probe</button></div>
  <div style={{flex:1,minHeight:0,overflow:'auto'}}><ChatMarkdown text={${JSON.stringify(inlineMarkdown)}} workspaceSessionId={thread} workspaceAvailability={availability} workspaceResources={io} onOpenWorkspace={setUri} onAddImageMaterial={add}/></div>
  <FileSidebar sessionId={thread} open={filesOpen} availability={availability} onClose={()=>setFilesOpen(false)} transport={directoryTransport} resources={io} files={directoryUploads} pickFiles={directoryPicker}/>
  {probe?<Probe thread={thread} availability={availability} uri={probeUri}/>:null}
  {uri?<WorkspaceFilePreview key={thread} uri={uri} threadId={thread} availability={availability} resources={io} onClose={()=>setUri(null)} onOpenWorkspace={setUri} onOpenLink={url=>f.external.push(url)} onAddImageMaterial={add}/>:null}
 </div>;
}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  const port=await new Promise<number>((resolve,reject)=>{const s=netServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const a=s.address();if(!a||typeof a==='string')return reject(Error('PORT'));s.close(error=>error?reject(error):resolve(a.port));});});
  const root=fileURLToPath(new URL('../',import.meta.url));
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-native-workspace-vite-cache-20261028',optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-markdown','remark-gfm','i18next','react-i18next']},resolve:{alias:[{find:/^react-native$/,replacement:'/workspace-platform.tsx'},{find:/^react-native-svg$/,replacement:root+'node_modules/react-native-svg/lib/module/elements.web.js'}]},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'native-workspace-production',enforce:'pre',resolveId(id,importer){if((id==='./Icons'||id==='../chat/Icons')&&(/\/components\/(chat|dashboard)\//.test(importer||'')))return root+'app/_dream/components/chat/Icons.native.tsx';if(id==='/workspace-entry.tsx')return '\0workspace-entry';if(id==='/workspace-platform.tsx')return '\0workspace-platform';},async load(id){if(id==='\0workspace-platform')return transformWithEsbuild(imagePlatform,'workspace-platform.tsx',{loader:'tsx',jsx:'automatic'});if(id==='\0workspace-entry')return transformWithEsbuild(entry,'workspace-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-workspace')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-workspace','<html><head><link rel="icon" href="data:,"><style>body{margin:0}#root{height:100vh}</style></head><body><div id="root"></div><script type="module" src="/workspace-entry.tsx"></script></body></html>'));});}}]});await server.listen();base='http://127.0.0.1:'+port+'/native-workspace';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{page.on('pageerror',error=>{throw error;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.goto(base);await expect(page.getByRole('button',{name:'Open report',exact:true})).toBeVisible();});
async function data(page:Page){return page.evaluate(()=>{const f=(window as any).__workspaceFixture;return {acquired:f.acquired.map(({signal,...v}:any)=>v),released:f.released,copies:f.copies,exports:f.exports,added:f.added,probe:f.probe,directoryCalls:f.directoryCalls.map(({signal,...value}:any)=>value),directoryWrites:f.directoryWrites,directoryPicks:f.directoryPicks,directoryUploads:f.directoryUploads,directoryHeld:f.directoryHeld.map(()=>true),directoryUploadHeld:f.directoryUploadHeld.map(()=>true),directoryDisposals:f.directoryDisposals};});}
test('native document preview retains original Markdown, relative links and literal HTML without execution',async({page})=>{
  await page.getByRole('button',{name:'Open report',exact:true}).click();await expect(page.getByRole('heading',{name:'Workspace report',exact:true})).toBeVisible();
  await expect(page.getByText('Original report body.',{exact:false})).toBeVisible();expect(await page.evaluate(()=>(window as any).__executed)).toBeUndefined();
  await page.getByRole('link',{name:'Sibling',exact:true}).click();await expect(page.getByRole('heading',{name:'Linked notes',exact:true})).toBeVisible();
  const calls=(await data(page)).acquired;expect(calls.some((call:any)=>call.threadId==='fixture-thread-a'&&call.path==='files/notes.md'&&call.download===false)).toBe(true);
  await page.getByRole('button',{name:'Close report preview',exact:true}).click();await expect(page.getByLabel('Source draft',{exact:true})).toHaveValue('Keep the source draft');
});
test('native Workspace image loads as a separate block and material copy has independent ownership',async({page})=>{
  await expect(page.getByRole('button',{name:'Preview Fixture image at full size',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Preview Fixture image at full size',exact:true}).click();await page.getByRole('button',{name:'Add to current message',exact:true}).click();
  await expect.poll(async()=>(await data(page)).added.length).toBe(1);const facts=await data(page);expect(facts.copies[0].copy).not.toBe(facts.copies[0].source);expect(facts.added[0]).toBe(facts.copies[0].copy);expect(facts.released).not.toContain(facts.added[0]);
});
test('native resource identity rejects late old-Thread results and releases their handles',async({page})=>{
  await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.hold=true;f.setProbe(true);});
  await expect.poll(()=>page.evaluate(()=>(window as any).__workspaceFixture.held.length)).toBeGreaterThan(0);
  await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.hold=false;f.setThread('fixture-thread-b');});
  await expect.poll(async()=>(await data(page)).probe?.kind).toBe('loaded');const newId=(await data(page)).probe.file.id;
  const oldIds=await page.evaluate(()=>{const f=(window as any).__workspaceFixture;const ids=f.held.map((item:any)=>item.file.id);f.held.forEach((item:any)=>item.release());return ids;});
  await expect.poll(async()=>{const d=await data(page);return oldIds.every((id:string)=>d.released.includes(id));}).toBe(true);
  expect((await data(page)).probe.file.id).toBe(newId);
});
test('native background releases the file lease and foreground performs a fresh read without task submission',async({page})=>{
  await page.getByRole('button',{name:'Toggle lease probe',exact:true}).click();await expect.poll(async()=>(await data(page)).probe?.kind).toBe('loaded');const old=(await data(page)).probe.file.id;
  await page.evaluate(()=>(window as any).__workspaceFixture.background());await expect.poll(async()=>(await data(page)).released.includes(old)).toBe(true);
  await page.evaluate(()=>(window as any).__workspaceFixture.foreground());await expect.poll(async()=>(await data(page)).probe?.kind).toBe('loaded');expect((await data(page)).probe.file.id).not.toBe(old);
});
test('native invalid or disabled Workspace references never acquire a resource',async({page})=>{
  await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.setAvailability('disabled');f.setProbe(true);});await expect.poll(async()=>(await data(page)).probe?.failure).toBe('disabled');
  expect((await data(page)).acquired.filter((call:any)=>call.path==='files/probe.md')).toHaveLength(0);await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.setProbeUri('workspace://files/../secret');f.setAvailability('enabled');});await expect.poll(async()=>(await data(page)).probe?.failure).toBe('invalid');
  expect((await data(page)).acquired.filter((call:any)=>call.path.includes('secret'))).toHaveLength(0);expect((await data(page)).acquired.filter((call:any)=>call.path==='files/probe.md')).toHaveLength(0);
});
test('generic directory download uses the original endpoint mode and does not reopen export after foreground recovery',async({page})=>{
  await page.evaluate(()=>(window as any).__workspaceFixture.holdExport=true);await page.getByRole('button',{name:'Download folder',exact:true}).click();
  await expect.poll(async()=>(await data(page)).exports.length).toBe(1);
  const oldId=(await data(page)).exports[0];await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.background();});await expect.poll(async()=>(await data(page)).released.includes(oldId)).toBe(true);await page.evaluate(()=>(window as any).__workspaceFixture.foreground());
  await expect.poll(async()=>(await data(page)).acquired.filter((call:any)=>call.path==='files/folder').length).toBeGreaterThan(1);
  expect((await data(page)).exports).toHaveLength(1);expect((await data(page)).acquired.filter((call:any)=>call.path==='files/folder').every((call:any)=>call.download===true)).toBe(true);
  await page.evaluate(()=>(window as any).__workspaceFixture.exportHeld[0]({completed:false}));await expect(page.getByRole('button',{name:'Close report preview',exact:true})).toHaveCount(0);
});
test('native acquisition preserves Cookie ownership and CSRF while mapping actual status and session expiry',async({page})=>{
  const receipt=await page.evaluate(async()=>{const f=(window as any).__workspaceFixture;const file=await f.raw.acquire({threadId:'fixture-thread',path:'files/中文 image.png',download:true});f.raw.release(file);return {options:f.rawOptions[0],release:f.rawReleases};});
  expect(receipt.options.path).toContain('/api/workspace/files/download?');expect(new URL(receipt.options.path,'http://fixture.invalid').searchParams.get('path')).toBe('files/中文 image.png');expect(receipt.options.method).toBe('GET');expect(receipt.options.headers['x-ink-csrf']).toHaveLength(43);expect(receipt.options.headers.Cookie).toBeUndefined();expect(receipt.options.headers.Authorization).toBeUndefined();
  const failure=await page.evaluate(async()=>{const f=(window as any).__workspaceFixture;f.rawStatus=401;try{await f.raw.acquire({threadId:'fixture-thread',path:'files/a'});}catch(error){return {failure:(error as any).failure,expirations:f.sessionExpirations};}});expect(failure).toEqual({failure:'access',expirations:1});
});
test('native acquisition rejects absent session before calling the platform and releases a late cancelled handle',async({page})=>{
  const missing=await page.evaluate(async()=>{const f=(window as any).__workspaceFixture;f.clearSession();try{await f.raw.acquire({threadId:'fixture-thread',path:'files/a'});}catch(error){return {failure:(error as any).failure,reads:f.rawOptions.length};}});expect(missing).toEqual({failure:'access',reads:0});
  await page.evaluate(async()=>{const f=(window as any).__workspaceFixture;await f.restoreSession();f.rawHold=true;const c=new AbortController();f.rawResult=f.raw.acquire({threadId:'fixture-thread',path:'files/a'},c.signal).then(()=> 'loaded',()=> 'cancelled');c.abort();});
  await expect.poll(()=>page.evaluate(()=>(window as any).__workspaceFixture.rawHeld.length)).toBe(1);await page.evaluate(()=>(window as any).__workspaceFixture.rawHeld[0]());
  expect(await page.evaluate(()=>(window as any).__workspaceFixture.rawResult)).toBe('cancelled');expect(await page.evaluate(()=>(window as any).__workspaceFixture.rawReleases.length)).toBe(1);expect(await page.evaluate(()=>(window as any).__workspaceFixture.rawCancels.length)).toBe(1);
});

test('native original file sidebar preserves folder-relative paths in one upload batch',async({page})=>{
 await page.getByRole('button',{name:'Open files',exact:true}).click();await page.getByRole('button',{name:'Open project',exact:true}).click();
 await page.getByRole('button',{name:'Upload folder',exact:true}).click();await expect.poll(async()=>(await data(page)).directoryUploads.length).toBe(1);
 const result=await data(page);expect(result.directoryUploads[0].thread).toBe('fixture-thread-a');expect(result.directoryUploads[0].path).toBe('project');expect(result.directoryUploads[0].files.map((file:any)=>file.relativePath)).toEqual(['Folder/a.txt','Folder/sub/b.txt']);expect(result.directoryPicks[0]).toEqual({max:Number.MAX_SAFE_INTEGER,directory:true});
 await expect.poll(async()=>{const result=await data(page);return ['picked-a','picked-b'].every(id=>result.released.includes(id));}).toBe(true);await expect(page.getByRole('textbox',{name:'Source draft'})).toHaveValue('Keep the source draft');
});
test('native original file delete retains failures and uses only an explicit retry',async({page})=>{
 await page.evaluate(()=>(window as any).__workspaceFixture.failDelete=true);await page.getByRole('button',{name:'Open files',exact:true}).click();const remove=page.getByRole('button',{name:'Delete report.md',exact:true});await remove.click();await expect(page.getByText('Fixture delete denied',{exact:true})).toBeVisible();await expect(remove).toBeEnabled();expect((await data(page)).directoryWrites).toHaveLength(1);
 await page.evaluate(()=>(window as any).__workspaceFixture.failDelete=false);await remove.click();await expect(remove).toHaveCount(0);const result=await data(page);expect(result.directoryWrites).toHaveLength(2);expect(result.directoryWrites[0].body).toEqual({sessionId:'fixture-thread-a',path:'report.md'});expect(result.directoryWrites[0].headers['x-ink-csrf']).toHaveLength(43);
});
test('native file sidebar directory export uses download mode and releases its private handle on system cancellation',async({page})=>{
 await page.getByRole('button',{name:'Open files',exact:true}).click();await page.getByRole('button',{name:'Download project as ZIP',exact:true}).click();await expect.poll(async()=>(await data(page)).exports.length).toBe(1);const result=await data(page);expect(result.acquired.find((item:any)=>item.path==='project')).toMatchObject({threadId:'fixture-thread-a',download:true});await expect.poll(async()=>(await data(page)).released.includes(result.exports[0])).toBe(true);await expect(page.getByRole('button',{name:'Close files',exact:true})).toBeVisible();
});
test('native directory reader ignores late previous-Thread results and suspends reads in the background',async({page})=>{
 await page.evaluate(()=>(window as any).__workspaceFixture.holdDirectory=true);await page.getByRole('button',{name:'Open files',exact:true}).click();await expect.poll(async()=>(await data(page)).directoryHeld.length).toBe(1);
 await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.holdDirectory=false;f.setThread('fixture-thread-b');});await expect(page.getByRole('button',{name:'Delete other.md',exact:true})).toBeVisible();await page.evaluate(()=>(window as any).__workspaceFixture.directoryHeld[0]());await expect(page.getByRole('button',{name:'Delete report.md',exact:true})).toHaveCount(0);
 await page.evaluate(()=>(window as any).__workspaceFixture.background());const count=(await data(page)).directoryCalls.length;await page.evaluate(()=>(window as any).__workspaceFixture.foreground());await expect.poll(async()=>(await data(page)).directoryCalls.length).toBeGreaterThan(count);await expect(page.getByRole('button',{name:'Delete other.md',exact:true})).toBeVisible();
});
test('native missing selection or disabled Workspace never probes files and a cancelled picker never uploads',async({page})=>{
 await page.evaluate(()=>(window as any).__workspaceFixture.setAvailability('disabled'));await page.getByRole('button',{name:'Open files',exact:true}).click();await expect(page.getByRole('button',{name:'Upload files',exact:true})).toBeDisabled();expect((await data(page)).directoryCalls).toHaveLength(0);
 await page.getByRole('button',{name:'Close files',exact:true}).click();await page.evaluate(()=>{const f=(window as any).__workspaceFixture;f.setAvailability('enabled');f.pickCancelled=true;});await page.getByRole('button',{name:'Open files',exact:true}).click();await page.getByRole('button',{name:'Upload files',exact:true}).click();await expect.poll(async()=>(await data(page)).directoryPicks.length).toBe(1);expect((await data(page)).directoryUploads).toHaveLength(0);expect((await data(page)).directoryWrites).toHaveLength(0);
});

test('closing the original file panel retains its in-flight upload and never replays it when reopened',async({page})=>{
 await page.evaluate(()=>(window as any).__workspaceFixture.holdDirectoryUpload=true);await page.getByRole('button',{name:'Open files',exact:true}).click();await page.getByRole('button',{name:'Open project',exact:true}).click();await page.getByRole('button',{name:'Upload folder',exact:true}).click();await expect.poll(async()=>(await data(page)).directoryUploadHeld.length).toBe(1);
 await page.getByRole('button',{name:'Close files',exact:true}).click();expect((await data(page)).directoryDisposals).toBe(0);await expect(page.getByRole('textbox',{name:'Source draft'})).toHaveValue('Keep the source draft');await page.evaluate(()=>(window as any).__workspaceFixture.directoryUploadHeld[0]());await expect.poll(async()=>{const result=await data(page);return ['picked-a','picked-b'].every(id=>result.released.includes(id));}).toBe(true);
 await page.getByRole('button',{name:'Open files',exact:true}).click();await expect(page.getByText('Uploaded 2 items.',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'project',exact:true})).toBeVisible();expect((await data(page)).directoryUploads).toHaveLength(1);
});
