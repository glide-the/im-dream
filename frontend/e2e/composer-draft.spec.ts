// [Input] Production useComposerDraft and caller-owned upload/submission results.
// [Output] Browser evidence for running drafts, permission projection, failed-queue recovery and preview ownership.
// [Pos] Provider-free shared Web/native state checks; no accounts, backend, files, models or ledger writes.
// [Sync] 2026-10-28: transform the virtual TSX fixture before Vite import analysis; require HTTP 200 and a mounted main within bounded waits.
import {expect,test} from '@playwright/test';
import {createServer as createNetServer} from 'node:net';
import {fileURLToPath} from 'node:url';
import {createServer,transformWithEsbuild} from 'vite';
test.use({channel:'chrome',actionTimeout:10_000});

const entry = `
import React,{useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import useComposerDraft from '/app/_dream/components/chat/useComposerDraft.ts';
function Harness() {
  const [loading,setLoading]=useState(false),[disabled,setDisabled]=useState(false),[fullAccess,setFullAccess]=useState(false),[stoppable,setStoppable]=useState(true);
  const [outcome,setOutcome]=useState('resolve'),[sent,setSent]=useState([]),[released,setReleased]=useState([]),[notice,setNotice]=useState('');
  const pending=useRef(null);
  const draft=useComposerDraft({loading,disabled,fullAccessEnabled:fullAccess,defaultToolChoice:'auto',onStop:stoppable?()=>setNotice('stopped'):undefined,
    onUploadBlocked:()=>setNotice('waiting-upload'),releasePreview:url=>{if(url)setReleased(current=>[...current,url]);},
    onSendMessage:(message,files,toolChoice)=>{
      setSent(current=>[...current,{message,files:files?.map(file=>file.name),toolChoice}]);
      if(outcome==='throw')throw new Error('fixture rejection');
      if(outcome==='reject')return Promise.reject(new Error('fixture rejection'));
      if(outcome==='hold')return new Promise((resolve,reject)=>{pending.current={resolve,reject};});
    }});
  const addFile=(name,uploading)=>draft.setUploadedFiles(current=>[...current,{id:name,name,mimeType:'text/plain',size:12,previewUrl:'blob:'+name,isUploading:uploading}]);
  return <main>
    <label>Draft<textarea aria-label="Draft" value={draft.query} onChange={event=>draft.setQuery(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'){event.preventDefault();draft.handleSend();}}}/></label>
    <label><input type="checkbox" checked={loading} onChange={event=>setLoading(event.target.checked)}/>Running</label>
    <label><input type="checkbox" checked={disabled} onChange={event=>setDisabled(event.target.checked)}/>Disabled</label>
    <label><input type="checkbox" checked={fullAccess} onChange={event=>setFullAccess(event.target.checked)}/>Existing full access</label>
    <label><input type="checkbox" checked={stoppable} onChange={event=>setStoppable(event.target.checked)}/>Stop available</label>
    <label>Submission result<select aria-label="Submission result" value={outcome} onChange={event=>setOutcome(event.target.value)}>{['resolve','reject','throw','hold'].map(value=><option key={value}>{value}</option>)}</select></label>
    <button onClick={()=>draft.setToolChoice('manual')}>Manual</button>
    <button onClick={()=>addFile('ready.txt',false)}>Add ready file</button><button onClick={()=>addFile('new.txt',false)}>Add new file</button><button onClick={()=>addFile('uploading.txt',true)}>Add uploading file</button>
    <button onClick={()=>draft.setUploadedFiles(current=>current.map(file=>({...file,isUploading:false})))}>Finish upload</button>
    <button onClick={()=>pending.current?.reject(new Error('fixture rejection'))}>Reject pending</button><button onClick={()=>pending.current?.resolve()}>Resolve pending</button>
    <button disabled={draft.showStopAction?false:!draft.canSend} onClick={()=>draft.showStopAction?setNotice('stopped'):draft.handleSend()}>{draft.showStopAction?'Stop':'Send'}</button>
    <output aria-label="Submitted">{JSON.stringify(sent)}</output><output aria-label="Released">{JSON.stringify(released)}</output><output aria-label="Files">{draft.uploadedFiles.map(file=>file.name).join(',')}</output><output aria-label="Notice">{notice}</output>
  </main>;
}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>;
let base:string;
test.beforeAll(async () => {
  const port=await new Promise<number>((resolve,reject)=>{
    const probe=createNetServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{
      const address=probe.address();if(!address||typeof address==='string'){probe.close();reject(new Error('Port unavailable'));return;}
      probe.close(error=>error?reject(error):resolve(address.port));
    });
  });
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',server:{host:'127.0.0.1',port,strictPort:true},plugins:[{
    name:'shared-composer-draft-fixture',enforce:'pre',
    configureServer(vite){vite.middlewares.use(async (request,response,next)=>{
      if(request.url?.split('?')[0]!=='/composer-draft')return next();
      response.setHeader('Content-Type','text/html');response.end(await vite.transformIndexHtml('/composer-draft','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/composer-draft.tsx"></script></body></html>'));
    });},resolveId(id){return id==='/composer-draft.tsx'?'\0composer-draft.tsx':null;},async load(id){return id==='\0composer-draft.tsx'?transformWithEsbuild(entry,'composer-draft.tsx',{loader:'tsx',jsx:'automatic'}):null;},
  }]});await server.listen();base=`http://127.0.0.1:${port}/composer-draft`;
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
  page.on('pageerror',error=>{throw error;});
  await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
  const entryResponse=page.waitForResponse(response=>new URL(response.url()).pathname==='/composer-draft.tsx',{timeout:10_000});
  await page.goto(base);
  const response=await entryResponse;
  expect(response.status(),response.ok()?'':(await response.text()).slice(0,800)).toBe(200);
  await expect(page.getByRole('main')).toBeVisible();
});

test('a running turn accepts the selected permission and returns to Stop after a queued draft is sent',async({page})=>{
  await page.getByRole('button',{name:'Manual',exact:true}).click();await page.getByLabel('Running',{exact:true}).check();
  await expect(page.getByRole('button',{name:'Stop',exact:true})).toBeEnabled();
  await page.getByLabel('Draft',{exact:true}).fill('  Keep this running draft  ');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByLabel('Submitted',{exact:true})).toHaveText(JSON.stringify([{message:'Keep this running draft',toolChoice:'manual'}]));
  await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('');await expect(page.getByRole('button',{name:'Stop',exact:true})).toBeEnabled();
});
for(const result of ['reject','throw'])test(`${result} restores the original draft and files without releasing their previews`,async({page})=>{
  await page.getByLabel('Submission result',{exact:true}).selectOption(result);await page.getByLabel('Draft',{exact:true}).fill('  Original draft  ');await page.getByRole('button',{name:'Add ready file',exact:true}).click();await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Original draft');await expect(page.getByLabel('Files',{exact:true})).toHaveText('ready.txt');await expect(page.getByLabel('Released',{exact:true})).toHaveText('[]');
});
test('a late rejection preserves the newer user draft and attachment',async({page})=>{
  await page.getByLabel('Submission result',{exact:true}).selectOption('hold');await page.getByLabel('Draft',{exact:true}).fill('First draft');await page.getByRole('button',{name:'Add ready file',exact:true}).click();await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('');await page.getByLabel('Draft',{exact:true}).fill('Newer draft');await page.getByRole('button',{name:'Add new file',exact:true}).click();await page.getByRole('button',{name:'Reject pending',exact:true}).click();
  await expect(page.getByLabel('Draft',{exact:true})).toHaveValue('Newer draft');await expect(page.getByLabel('Files',{exact:true})).toHaveText('new.txt');await expect(page.getByLabel('Released',{exact:true})).toHaveText('[]');
});
test('a successful attachment-only submission releases only its submitted preview after settlement',async({page})=>{
  await page.getByLabel('Submission result',{exact:true}).selectOption('hold');await page.getByRole('button',{name:'Add ready file',exact:true}).click();await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByLabel('Submitted',{exact:true})).toHaveText(JSON.stringify([{message:'',files:['ready.txt'],toolChoice:'auto'}]));await expect(page.getByLabel('Released',{exact:true})).toHaveText('[]');
  await page.getByRole('button',{name:'Add new file',exact:true}).click();await page.getByRole('button',{name:'Resolve pending',exact:true}).click();
  await expect(page.getByLabel('Released',{exact:true})).toHaveText('["blob:ready.txt"]');await expect(page.getByLabel('Files',{exact:true})).toHaveText('new.txt');
});
test('full access projects auto without discarding the saved manual choice',async({page})=>{
  await page.getByRole('button',{name:'Manual',exact:true}).click();await page.getByLabel('Existing full access',{exact:true}).check();await page.getByLabel('Draft',{exact:true}).fill('First');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByLabel('Submitted',{exact:true})).toHaveText(JSON.stringify([{message:'First',toolChoice:'auto'}]));
  await page.getByLabel('Existing full access',{exact:true}).uncheck();await page.getByLabel('Draft',{exact:true}).fill('Second');await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.getByLabel('Submitted',{exact:true})).toHaveText(JSON.stringify([{message:'First',toolChoice:'auto'},{message:'Second',toolChoice:'manual'}]));
});
test('uploads, disabled state and passive loading retain the original send guards',async({page})=>{
  const draft=page.getByLabel('Draft',{exact:true});await draft.fill('Pending');await page.getByRole('button',{name:'Add uploading file',exact:true}).click();await draft.press('Enter');
  await expect(page.getByLabel('Notice',{exact:true})).toHaveText('waiting-upload');await expect(page.getByLabel('Submitted',{exact:true})).toHaveText('[]');
  await page.getByRole('button',{name:'Finish upload',exact:true}).click();await page.getByLabel('Disabled',{exact:true}).check();await draft.press('Enter');await expect(page.getByLabel('Submitted',{exact:true})).toHaveText('[]');
  await page.getByLabel('Disabled',{exact:true}).uncheck();await page.getByLabel('Stop available',{exact:true}).uncheck();await page.getByLabel('Running',{exact:true}).check();await draft.press('Enter');await expect(page.getByLabel('Submitted',{exact:true})).toHaveText('[]');
  await page.getByLabel('Running',{exact:true}).uncheck();await draft.press('Enter');await expect(page.getByLabel('Submitted',{exact:true})).toHaveText(JSON.stringify([{message:'Pending',files:['uploading.txt'],toolChoice:'auto'}]));
});
