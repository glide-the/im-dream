// [Sync] 2026-10-28: prebundle the full capture fixture dependency graph so Vite discovery cannot reload an active share job.
// [Input] Production native share owner and actual DOM capture document, with explicit platform/file/HTTP fixtures.
// [Output] Full-history/capture handoff, background-dialog completion, stale ownership and system-cancel cleanup evidence.
// [Pos] Provider-free browser integration; UIKit and private filesystem qualification remain device tests.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
const png=readFileSync(fileURLToPath(new URL('../public/placeholder-memory.png',import.meta.url))).toString('base64');
const native=`
export * from 'react-native-web';
export const NativeModules={InkRuntime:{
 async importSketch(options){const f=window.__shareFixture,id='png-'+(++f.sequence);f.imports.push({id,name:options.name,size:atob(options.base64).length,png:options.base64.startsWith('iVBOR')});const file={id,name:options.name,type:'image/png',size:atob(options.base64).length,uri:'data:image/png;base64,'+options.base64};f.files.set(id,file);return file;},
 releaseFiles(ids){const f=window.__shareFixture;f.released.push(...ids);ids.forEach(id=>f.files.delete(id));},
 async exportFiles(ids){const f=window.__shareFixture;f.exports.push(ids.map(id=>({id,name:f.files.get(id).name})));return {completed:f.completed};},
 async readWorkspaceImage(id){window.__shareFixture.imageReads.push(id);return {type:'image/png',base64:'${png}'};},
}};
export class NativeEventEmitter {addListener(){return {remove(){}};}}
`;
const webview=`
import React,{useEffect,useRef,useImperativeHandle} from 'react';
export const WebView=React.forwardRef((props,ref)=>{
 const frame=useRef(null),latest=useRef(props);latest.current=props;window.__shareFixture.view=props;
 useImperativeHandle(ref,()=>({injectJavaScript(script){frame.current?.contentWindow?.eval(script);},reload(){frame.current?.contentWindow?.location.reload();}}));
 useEffect(()=>{latest.current.onLoadStart?.();const receive=event=>{if(event.source!==frame.current?.contentWindow||event.origin!==location.origin||!event.data?.shareFixture)return;if(event.data.kind==='command')window.__shareFixture.commands.push(JSON.parse(event.data.raw));else {window.__shareFixture.events.push(JSON.parse(event.data.raw));latest.current.onMessage?.({nativeEvent:{url:latest.current.source.uri,data:event.data.raw}});}};window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive);},[]);
 return <iframe title="Capture document" ref={frame} src={props.source.uri} style={{width:1,height:1,border:0}}/>;
});
`;
const entry=`
import React,{useRef,useState} from 'react';import {createRoot} from 'react-dom/client';import ChatShareSurface from '/app/_dream/components/chat/ChatShareSurface.native.tsx';import i18n from '/app/_dream/i18n.ts';await i18n.changeLanguage('en');
const f=window.__shareFixture={sequence:0,imports:[],released:[],exports:[],files:new Map(),commands:[],events:[],requests:[],held:[],hold:false,completed:false,imageReads:[],acquired:[],resourceReleases:[],withImage:false,failImage:false};
const transport=async(input,init)=>{f.requests.push({path:String(input),signal:init.signal});const result=Response.json({messages:[{id:'older',role:'assistant',parts:[{type:'text',text:'Complete older reply'+(f.withImage?'\\n\\n![Material](workspace://files/material.png)':'')}],metadata:{},created_at:'2026-10-28T00:00:00Z'}]});return f.hold?new Promise(resolve=>f.held.push(()=>resolve(result))):result;};
const resources={async acquire(input){f.acquired.push(input);if(f.failImage)throw new Error('missing');return {id:'workspace-image',name:'material.png',type:'image/png',uri:'file:///material.png',size:12};},release(file){f.resourceReleases.push(file.id);},async text(){return '';},async copy(file){return file;},async export(){return {completed:false};}};
function App(){const ref=useRef(null),[thread,setThread]=useState('source-thread'),[draft,setDraft]=useState('Keep source draft');f.setThread=setThread;return <main><textarea aria-label="Source draft" value={draft} onChange={event=>setDraft(event.target.value)}/><button onClick={()=>ref.current.open()}>Open share</button><ChatShareSurface ref={ref} origin={location.origin} threadId={thread} title="Native share fixture" availability="enabled" transport={transport} resources={resources} snapshot={()=>({messages:[{id:'live',role:'user',parts:[{type:'text',text:'Latest live input'}]}],toolChoice:'manual',pendingConfirmation:{kind:'askuser',partKey:'ask',toolCallId:'ask',toolName:'AskUserQuestion',input:{question:'Original pending question',options:['First','Second']}}})}/></main>;}
createRoot(document.querySelector('#root')).render(<App/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
 server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,logLevel:'silent',server:{host:'127.0.0.1',port:0},optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-markdown','remark-gfm','ai','zod','i18next','react-i18next','html-to-image']},plugins:[{
  name:'native-share-integration',enforce:'pre',resolveId(id){if(id==='react-native')return '\0share-native';if(id==='react-native-webview')return '\0share-webview';if(id==='/share-harness.tsx')return '\0share-harness';},
  async load(id){const source=id==='\0share-native'?native:id==='\0share-webview'?webview:id==='\0share-harness'?entry:null;return source?(await transformWithEsbuild(source,'share-harness.tsx',{loader:'tsx',jsx:'automatic'})).code:null;},
  configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
   if(!['/share-harness','/native/chat-export'].includes(req.url??''))return next();const leaf=req.url==='/native/chat-export';
   const bridge=leaf?`<script>window.ReactNativeWebView={postMessage(raw){parent.postMessage({shareFixture:true,kind:'event',raw},location.origin)}};window.addEventListener('message',event=>{if(typeof event.data==='string')parent.postMessage({shareFixture:true,kind:'command',raw:event.data},location.origin)});</script>`:'';
   const script=leaf?`import React from 'react';import {createRoot} from 'react-dom/client';import Component from '/app/_dream/components/chat/ChatImageDocument.tsx';import '/app/_dream/index.css';createRoot(document.querySelector('#root')).render(React.createElement(Component));`:`import '/share-harness.tsx';`;
   res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml(req.url!,`<html><head><link rel="icon" href="data:,"></head><body>${bridge}<div id="root"></div><script type="module">${script}</script></body></html>`));
  });},
 }]});await server.listen();base=server.resolvedUrls!.local[0];
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
 const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin!==new URL(base).origin||url.pathname.startsWith('/api/')||url.pathname.startsWith('/auth/')){errors.push('Unexpected request '+url.pathname);return route.abort();}return route.continue();});
 await page.goto(base+'share-harness');await expect(page.getByRole('button',{name:'Open share',exact:true})).toBeVisible();
});
test.afterEach(async({page},info)=>{await info.attach('share-platform-diagnostics',{body:JSON.stringify(await facts(page)),contentType:'application/json'});expect(diagnostics.get(page)).toEqual([]);});
async function facts(page:Page){return page.evaluate(()=>{const f=(window as any).__shareFixture;return {imports:f.imports,released:f.released,exports:f.exports,commands:f.commands,events:f.events.map(({base64,images,...value}:any)=>({...value,images:images?.map(({base64,...image}:any)=>image)})),requests:f.requests.map(({signal,...value}:any)=>({...value,aborted:signal?.aborted})),acquired:f.acquired,resourceReleases:f.resourceReleases,imageReads:f.imageReads,files:f.files.size};});}
const open=(page:Page)=>page.getByRole('button',{name:'Open share',exact:true}).click();
const download=(page:Page)=>page.getByRole('button',{name:'Download image',exact:true});
test('actual DOM capture receives complete original snapshot and system cancellation preserves retryable preview',async({page})=>{
 await open(page);await expect(download(page)).toBeEnabled({timeout:60000});let data=await facts(page);const render=data.commands.find((event:any)=>event.type==='render');
 expect(render.options.messages.map((message:any)=>message.blocks[0].text)).toEqual(['Complete older reply','Latest live input']);expect(render.options.pendingConfirmation.questions[0].question).toBe('Original pending question');expect(data.requests[0].path).toMatch(/\/source-thread\/messages$/);expect(data.imports.every((file:any)=>file.png&&file.size>0)).toBe(true);
 await download(page).click();await expect.poll(async()=>(await facts(page)).exports.length).toBe(1);await expect(download(page)).toBeEnabled();await expect(page.getByText('Native share fixture',{exact:true})).toBeVisible();
 await page.evaluate(()=>(window as any).__shareFixture.completed=true);await download(page).click();await expect.poll(async()=>(await facts(page)).exports.length).toBe(2);await expect(download(page)).toHaveCount(0);await expect.poll(async()=>(await facts(page)).files).toBe(0);await expect(page.getByLabel('Source draft',{exact:true})).toHaveValue('Keep source draft');
});
test('closing during the original full-history read retains one job and completion reopens its preview',async({page})=>{
 await page.evaluate(()=>(window as any).__shareFixture.hold=true);await open(page);await expect.poll(async()=>(await facts(page)).requests.length).toBe(1);await page.getByRole('button',{name:'Close',exact:true}).click();
 await page.evaluate(()=>{const f=(window as any).__shareFixture;f.hold=false;f.held.shift()();});await expect(download(page)).toBeEnabled({timeout:60000});expect((await facts(page)).requests).toHaveLength(1);await expect(page.getByLabel('Source draft',{exact:true})).toHaveValue('Keep source draft');
});
test('a Thread change cancels pending history and prevents a late old snapshot from rendering or exporting',async({page})=>{
 await page.evaluate(()=>(window as any).__shareFixture.hold=true);await open(page);await expect.poll(async()=>(await facts(page)).requests.length).toBe(1);await page.evaluate(()=>(window as any).__shareFixture.setThread('different-thread'));await expect(page.getByRole('button',{name:'Close',exact:true})).toHaveCount(0);
 await page.evaluate(()=>{const f=(window as any).__shareFixture;f.hold=false;f.held.shift()();});await expect.poll(async()=>(await facts(page)).requests[0].aborted).toBe(true);expect((await facts(page)).imports).toHaveLength(0);expect((await facts(page)).exports).toHaveLength(0);
});
test('Workspace image bytes use the frozen Thread native owner and release the private lease',async({page})=>{
 await page.evaluate(()=>(window as any).__shareFixture.withImage=true);await open(page);await expect(download(page)).toBeEnabled({timeout:60000});const data=await facts(page);expect(data.acquired).toEqual([{threadId:'source-thread',path:'files/material.png'}]);expect(data.imageReads).toEqual(['workspace-image']);expect(data.resourceReleases).toEqual(['workspace-image']);
});
