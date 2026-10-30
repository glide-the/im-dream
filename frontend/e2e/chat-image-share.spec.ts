// [Input] Original export projection, full-history API and PNG download preparation.
// [Output] Provider-free evidence for ordered content, current tool confirmation, full reads and stitch/fallback filenames.
// [Pos] Web share regression; no real account, model, database or application service changes.
import {test,expect} from '@playwright/test';
import type {TFunction} from 'i18next';
import type {UIMessage} from 'ai';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {toExportChatMessage,buildExportPendingConfirmation} from '../app/_dream/components/chat/chatImageProjection';
import {readChatImageCommand,readChatImageEvent,chatImageDocumentUrl} from '../app/_dream/components/chat/ChatImageDocument.protocol';
import {fetchFullClaudeThreadMessages} from '../app/_dream/components/chat/threadSessionHydration';
const t=((key:string)=>key) as TFunction;
test('original export retains ordered reasoning, tools, text, file labels and pending questions',()=>{
  const message={id:'reply',role:'assistant',parts:[{type:'reasoning',text:'trace'},{type:'text',text:'**answer**'},{type:'dynamic-tool',toolName:'Bash',toolCallId:'call',state:'output-available',input:{command:'pwd'},output:'$ pwd\n/work\nExit code: 0'},{type:'file',filename:'notes.md',mediaType:'text/markdown',url:'workspace://files/notes.md'}]} as UIMessage;
  const value=toExportChatMessage(message,'auto',t);
  expect(value?.blocks.map(part=>part.kind)).toEqual(['reasoning','text','tool']);
  expect(value?.blocks[2]).toMatchObject({toolName:'Bash',status:'completed',command:'pwd',output:'/work',exitCode:'0'});
  expect(value?.files).toEqual(['notes.md']);
  expect(toExportChatMessage({id:'system',role:'system',parts:[{type:'text',text:'private'}]},'auto',t)).toBeNull();
  expect(buildExportPendingConfirmation({kind:'askuser',partKey:'part',toolCallId:'ask',toolName:'AskUserQuestion',input:{questions:[{question:'Choose',required:true,options:[{label:'First',value:'one',description:'hint'},'Second']}]}} as never,t)).toMatchObject({kind:'askuser',questions:[{question:'Choose',required:true,options:[{label:'First',description:'hint'},{label:'Second'}]}]});
});
test('explicit full-history reads retain cancellation and use the caller HTTP owner',async()=>{
  const abort=new AbortController();const requests:{path:string;signal:AbortSignal|null|undefined}[]=[];
  const transport=(async(input:RequestInfo|URL,init?:RequestInit)=>{requests.push({path:String(input),signal:init?.signal});return Response.json({messages:[{id:'persisted',role:'assistant',parts:[{type:'text',text:'Complete persisted reply'}],metadata:{},created_at:'2026-10-28T00:00:00Z'}]});}) as typeof fetch;
  const result=await fetchFullClaudeThreadMessages('thread share',abort.signal,transport);
  expect(requests).toHaveLength(1);expect(requests[0].path).toMatch(/\/thread%20share\/messages$/);expect(requests[0].signal).toBe(abort.signal);expect(result.messages[0].parts).toEqual([{type:'text',text:'Complete persisted reply'}]);
});
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',server:{host:'127.0.0.1',port:0},plugins:[{name:'share-download-fixture',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/share-download')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/share-download','<html><head><link rel="icon" href="data:,"></head><body><button id="run">Prepare</button><output id="result"></output><script type="module" src="/share-download.js"></script></body></html>'));});},resolveId(id){return id==='/share-download.js'?'\0share-download':null;},load(id){return id==='\0share-download'?`
    import {prepareThreadImageDownload} from '/app/_dream/components/chat/threadImageDownload.ts';
    document.querySelector('#run').onclick=async()=>{try{
      const canvas=document.createElement('canvas');canvas.width=2;canvas.height=3;canvas.getContext('2d').fillRect(0,0,2,3);const png=canvas.toDataURL('image/png');
      const single=await prepareThreadImageDownload({images:[png],fileName:'原对话.png'});
      const merged=await prepareThreadImageDownload({images:[png,png],fileName:'原对话.png'});
      const bytes=new Uint8Array(await(await fetch(merged[0].href)).arrayBuffer());const header=new DataView(bytes.buffer);
      const fallback=await prepareThreadImageDownload({images:['data:text/plain,invalid','data:text/plain,invalid'],fileName:'原对话.png'});
      const result={single:single.map(x=>({fileName:x.fileName,owned:x.owned,same:x.href===png})),merged:merged.map(x=>({fileName:x.fileName,owned:x.owned})),width:header.getUint32(16),height:header.getUint32(20),fallback:fallback.map(x=>({fileName:x.fileName,owned:x.owned}))};merged.filter(x=>x.owned).forEach(x=>URL.revokeObjectURL(x.href));document.querySelector('#result').textContent=JSON.stringify(result);
    }catch(error){document.querySelector('#result').textContent=JSON.stringify({error:String(error)});}};
  `:null;}}]});await server.listen();base=server.resolvedUrls!.local[0]+'share-download';
});
test.afterAll(async()=>{await server?.close();});
test('original PNG preparation preserves single images, binary stitching and numbered fallback',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));await page.goto(base);await page.getByRole('button',{name:'Prepare',exact:true}).click();await expect(page.locator('#result')).not.toBeEmpty();
  expect(JSON.parse(await page.locator('#result').innerText())).toEqual({single:[{fileName:'原对话.png',owned:false,same:true}],merged:[{fileName:'原对话.png',owned:true}],width:2,height:6,fallback:[{fileName:'原对话-part-1-of-2.png',owned:false},{fileName:'原对话-part-2-of-2.png',owned:false}]});expect(errors).toEqual([]);
});

test('capture protocol rejects arbitrary document origins, unsafe PNG metadata and unsupported commands',()=>{
  expect(chatImageDocumentUrl('http://[::1]:5173')).toBe('http://[::1]:5173/native/chat-export');
  for(const origin of ['https://example.test','http://localhost:5173/other','file:///private'])expect(()=>chatImageDocumentUrl(origin)).toThrow();
  expect(readChatImageCommand({type:'prepare',documentId:'document',requestId:'job',deliveryId:'delivery'})).not.toBeNull();
  expect(readChatImageCommand({type:'exec',documentId:'document',requestId:'job',command:'arbitrary'})).toBeNull();
  expect(readChatImageEvent(JSON.stringify({type:'progress',documentId:'document',requestId:'job',done:2,total:1}))).toBeNull();
  expect(readChatImageEvent(JSON.stringify({type:'preview',documentId:'document',requestId:'job',partial:false,fileName:'share.png',images:[{name:'../share.png',size:3,base64:'AAAA',width:1,height:1}]}))).toBeNull();
  expect(readChatImageCommand({type:'workspaceImageResult',documentId:'document',requestId:'job',imageId:'image',image:{type:'text/html',base64:'AAAA'}})).toBeNull();
});
