// [Input] Original Web FileSidebar, shared Workspace API/model, public-shaped fixtures and installed Chrome.
// [Output] DELETE/CSRF, failure recovery, folder upload/download and shared tree/read contracts without business data writes.
// [Pos] Provider-free Web compatibility gate; Project/Episode/Thread persistence, Hook and actual filesystem remain outside scope.
// [Sync] 2026-10-28: exercise the original visible file controls before native sidebar reuse.
import {expect,test} from '@playwright/test';
import {createServer} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
import {loadBrowserSession,clearBrowserSession} from '../app/_dream/lib/browserSession';
import {readWorkspaceFileTree,deleteWorkspaceFile,buildTree,flattenVisible} from '../app/_dream/api/workspaceFilesApi';
const csrf='f'.repeat(43),file={name:'report.md',path:'files/report.md',isDirectory:false,size:12,modifiedAt:'2026-10-28T00:00:00Z'};
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 const port=await new Promise<number>((resolve,reject)=>{const s=netServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const a=s.address();if(!a||typeof a==='string')return reject(Error('PORT'));s.close(e=>e?reject(e):resolve(a.port));});});
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-workspace-sidebar-web-cache-20261028',esbuild:{jsx:'automatic'},optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime']},server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'original-workspace-sidebar',resolveId(id){if(id==='/workspace-sidebar.js')return '\0workspace-sidebar';},load(id){if(id==='\0workspace-sidebar')return `
 import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
 import FileSidebar from '/app/_dream/components/dashboard/FileSidebar.tsx';import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import '/app/_dream/styles/tokens.css';
 await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'${csrf}'}));
 function Harness(){const [open,setOpen]=useState(true);return React.createElement('div',{style:{display:'flex',height:'100vh'}},React.createElement('textarea',{'aria-label':'Source draft',defaultValue:'Existing draft'}),React.createElement(FileSidebar,{sessionId:'fixture-thread',open,onClose:()=>setOpen(false)}));}
 createRoot(document.querySelector('#root')).render(React.createElement(Harness));`;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/workspace-sidebar')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/workspace-sidebar','<html><head><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/workspace-sidebar.js"></script></body></html>'));});}}]});await server.listen();base=`http://127.0.0.1:${port}/workspace-sidebar`;
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{page.on('pageerror',error=>{throw error;});});
test.afterEach(()=>clearBrowserSession());
test('original delete uses DELETE and CSRF, refreshes only after success and retains the source draft',async({page})=>{
 const writes:unknown[]=[],errors:string[]=[];let removed=false;
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/workspace/files**',async route=>{
  const req=route.request();expect(req.headers()['x-ink-csrf']).toBe(csrf);expect(req.headers().authorization).toBeUndefined();
  if(req.method()==='DELETE'){writes.push(req.postDataJSON());removed=true;return route.fulfill({json:{deleted:true}});}
  expect(req.method()).toBe('GET');return route.fulfill({json:{files:removed?[]:[{...file,path:'report.md'}]}});
 });await page.goto(base);await page.getByRole('button',{name:'Delete report.md',exact:true}).click();await expect(page.getByRole('button',{name:'Delete report.md',exact:true})).toHaveCount(0);
 expect(writes).toEqual([{sessionId:'fixture-thread',path:'report.md'}]);await expect(page.getByRole('textbox',{name:'Source draft'})).toHaveValue('Existing draft');expect(errors).toEqual([]);
});
test('original failed delete retains the file and exposes the actual error before an explicit retry',async({page})=>{
 let attempts=0,removed=false;await page.route('**/api/workspace/files**',route=>{
  if(route.request().method()==='DELETE'){attempts++;if(attempts===1)return route.fulfill({status:503,json:{error:'Fixture delete unavailable'}});removed=true;return route.fulfill({json:{deleted:true}});}
  return route.fulfill({json:{files:removed?[]:[{...file,path:'report.md'}]}});
 });await page.goto(base);const remove=page.getByRole('button',{name:'Delete report.md',exact:true});await remove.click();await expect(page.getByText('Fixture delete unavailable',{exact:true})).toBeVisible();await expect(remove).toBeVisible();expect(attempts).toBe(1);await remove.click();await expect(remove).toHaveCount(0);expect(attempts).toBe(2);
});
test('original folder selection uploads into that path and directory download remains ZIP',async({page})=>{
 const uploads:string[]=[];await page.route('**/api/workspace/files**',route=>{
  const req=route.request(),url=new URL(req.url());expect(req.headers()['x-ink-csrf']).toBe(csrf);
  if(url.pathname.endsWith('/download'))return route.fulfill({contentType:'application/zip',headers:{'Content-Disposition':'attachment; filename="project.zip"'},body:Buffer.from('UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==','base64')});
  if(req.method()==='POST'){uploads.push(req.postDataBuffer()!.toString());return route.fulfill({json:{uploaded:['project/note.txt']}});}
  return route.fulfill({json:{tree:[{name:'project',path:'project',isDirectory:true,size:0,modifiedAt:file.modifiedAt,children:[{...file,path:'project/report.md'}]}]}});
 });await page.goto(base);const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Download project as ZIP',exact:true}).click();expect((await downloadEvent).suggestedFilename()).toBe('project.zip');
 // The original directory expand button is the first control in the project row.
 const directory=page.getByText('project',{exact:true}).locator('..').locator('..');await directory.locator('button').first().click();
 await page.locator('input[type=file]').first().setInputFiles({name:'note.txt',mimeType:'text/plain',buffer:Buffer.from('Fixture note')});
 await expect.poll(()=>uploads.length).toBe(1);expect(uploads[0]).toContain('name="path"\r\n\r\nproject');expect(uploads[0]).toContain('filename="note.txt"');expect(uploads[0]).toContain('name="relativePath"\r\n\r\nnote.txt');
});
test('shared tree/read transport keeps normalization, cancellation, authentication and error semantics',async()=>{
 await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:csrf}));
 const c=new AbortController();let calls=0;const transport:typeof fetch=async(input,init)=>{calls++;expect(new Headers(init?.headers).get('x-ink-csrf')).toBe(csrf);expect(init?.signal).toBe(c.signal);expect(new URL(String(input),'http://fixture.invalid').searchParams.get('recursive')).toBe('1');return Response.json({files:[file]});};
 const tree=await readWorkspaceFileTree('fixture-thread',{transport,signal:c.signal});expect(flattenVisible(tree,'files')[0].path).toBe(file.path);expect(buildTree([{...file,path:'files\\report.md'}])[0].children?.[0].path).toBe(file.path);expect(calls).toBe(1);
 await expect(deleteWorkspaceFile('fixture-thread','files/report.md',async(_,init)=>{expect(init?.method).toBe('DELETE');expect(JSON.parse(String(init?.body))).toEqual({sessionId:'fixture-thread',path:file.path});return Response.json({error:'Original denied'},{status:403});})).rejects.toThrow('Original denied');
});
