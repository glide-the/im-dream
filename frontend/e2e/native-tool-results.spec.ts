// [Sync] 2026-10-31: hold disposal acknowledgement and prove navigation cannot remove the prior document early.
// [Input] Production native message/tool/file components, real shared helpers and explicit WebView/file/AppState boundaries.
// [Output] Tool content/copy, stable MCP document slots, callback identity, storage leases and canonical process-prefetch evidence.
// [Pos] Provider-free RNW technical qualification; WebKit, filesystem bytes, accounts, DB and model execution are separately verified.
import {test,expect} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const platform=String.raw`
import React,{useEffect} from 'react';import {View,Text} from 'react-native-web';export * from 'react-native-web';
export const AppState={currentState:'active',listeners:new Set(),addEventListener(_,fn){this.listeners.add(fn);return{remove:()=>this.listeners.delete(fn)}}};
export const NativeModules={InkRuntime:{copyText:async text=>window.__nativeTools.copies.push(text),
 async readWorkspaceFile(options){const f=window.__nativeTools;f.reads.push(options);const file={id:'file-'+(++f.fileSerial),uri:'file:///private/file-'+f.fileSerial,name:'attachment.png',type:'image/png',size:8};return f.hold?new Promise(resolve=>f.pending.push(()=>resolve(file))):file;},cancelWorkspaceFile:id=>window.__nativeTools.cancels.push(id),releaseFiles:ids=>window.__nativeTools.released.push(...ids),exportFile:async id=>{window.__nativeTools.exports.push(id);return{completed:true}}}};
export function Image({source,onLoad,onError,accessibilityLabel}){useEffect(()=>window.__nativeTools.imageFailure?onError?.():onLoad?.({nativeEvent:{source:{width:100,height:80}}}),[source?.uri]);return <View role="img" accessibilityLabel={accessibilityLabel}><Text>{'Private image: '+source?.uri}</Text></View>;}
`;
const webview=String.raw`
import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';import {View,Text,TextInput} from 'react-native';
export const WebView=forwardRef(function WebView(props,ref){const [state,setState]=useState(null),[draft,setDraft]=useState('');const latest=useRef(props);latest.current=props;const doc=useRef('leaf-'+(++window.__nativeTools.serial));
 useImperativeHandle(ref,()=>({reload(){latest.current.onLoadStart?.();latest.current.onMessage?.({nativeEvent:{url:props.source.uri,data:JSON.stringify({type:'ready',documentId:doc.current})}})},injectJavaScript(code){new Function('window','MessageEvent',code)({dispatchEvent(event){const message=JSON.parse(event.data);if(message.type==='state')setState(message);else if(message.type==='dispose'){window.__nativeTools.disposals.push(message);const acknowledge=()=>latest.current.onMessage({nativeEvent:{url:props.source.uri,data:JSON.stringify({type:'disposed',documentId:doc.current,threadId:message.threadId,toolCallId:message.toolCallId,requestId:message.requestId})}});if(window.__nativeTools.holdDisposals)window.__nativeTools.pendingDisposals.push(acknowledge);else acknowledge();}else window.__nativeTools.acks.push(message);}},MessageEvent);}}),[]);
 useEffect(()=>{window.__nativeTools.mounts++;latest.current.onMessage?.({nativeEvent:{url:props.source.uri,data:JSON.stringify({type:'ready',documentId:doc.current})}});return()=>{window.__nativeTools.unmounts++;};},[]);
 useEffect(()=>{if(state)window.__nativeTools.docs[state.toolCallId]={id:doc.current,state,emit(value,url=props.source.uri){latest.current.onMessage?.({nativeEvent:{url,data:JSON.stringify({...value,documentId:doc.current,threadId:state.threadId,toolCallId:state.toolCallId})}})}};},[state]);
 return <View style={props.style}>{state?<><Text>{'DOM document '+state.toolCallId}</Text><TextInput accessibilityLabel={'DOM draft '+state.toolCallId} value={draft} onChangeText={setDraft}/></>:null}</View>;
});`;
const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';import {View,Text,Pressable} from 'react-native';
import '/app/_dream/i18n.ts';import List from '/app/_dream/components/chat/ChatMessageList.native.tsx';import Tool from '/app/_dream/components/chat/ToolMessagePart.native.tsx';import File from '/app/_dream/components/chat/FileMessagePart.native.tsx';
import {closeToolResultDocuments} from '/app/_dream/components/chat/ToolResultSurface.native.tsx';
import {isToolUIPart} from 'ai';import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import {createMessageFileResources} from '/src/platform/workspaceFiles.native.ts';import {mergeRecoveredLatestPage} from '/app/_dream/components/chat/chatHistoryWindow.ts';
const f=window.__nativeTools={serial:0,mounts:0,unmounts:0,fileSerial:0,reads:[],released:[],exports:[],cancels:[],copies:[],docs:{},acks:[],messages:[],settled:[],jumps:[],hold:false,pending:[],processReads:0,disposals:[],holdDisposals:false,pendingDisposals:[]};const documentOwner={};
const output={content:[{type:'text',text:'Saved App result'}]};
const app={type:'dynamic-tool',toolName:'mcp__fixture__show',toolCallId:'tool-form',state:'output-available',input:{},output,mcpAppResult:{version:1,serverRef:'fixture',toolName:'show',toolCallId:'tool-form',input:{},workspaceScope:null,resourceUri:'ui://fixture/form.html',result:output}};
const parts=[{type:'dynamic-tool',toolName:'Bash',toolCallId:'tool-bash',state:'output-available',input:{command:'printf original',description:'Read original output'},output:'$ printf original\noriginal\nExit code: 0'},
 {type:'dynamic-tool',toolName:'Write',toolCallId:'tool-write',state:'output-available',input:{file_path:'notes/story.md',content:'Full file preview'},output:'Saved'},
 {type:'dynamic-tool',toolName:'mcp__images__generate_image',toolCallId:'tool-image',state:'output-error',input:{prompt:'A beach'},errorText:'{"message":"Image request failed"}'},app,{type:'text',text:'Final reply.'}];
const complete={id:'live-id',role:'assistant',parts,metadata:{turnId:'same-turn',turnStatus:'completed',finalPartIndex:4,durationMs:1000}};
async function transport(input){if(String(input)==='/auth/session')return Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});f.processReads++;return Response.json({...complete,id:'stored-id',created_at:'2026-10-30T00:00:00Z'});}
await loadBrowserSession(transport);const resources=createMessageFileResources();
function Harness(){const [messages,setMessages]=useState([complete]),[historical,setHistorical]=useState(false),[thread,setThread]=useState('fixture-thread');
 const controls=[['Hydrate history',()=>{const summary={id:'stored-id',role:'assistant',parts:[{type:'text',text:'Final reply.'}],metadata:{historyProjectionVersion:1,historyProcessAvailable:true,turnId:'same-turn',turnStatus:'completed',finalPartIndex:4,durationMs:1000}};setMessages(current=>mergeRecoveredLatestPage(current,[summary],new Set(['same-turn'])).messages);setHistorical(true);}],['Clone current DTO',()=>setMessages(current=>structuredClone(current))],['Deferred history',()=>{setThread('history-thread');setMessages([{id:'stored-id',role:'assistant',parts:[{type:'text',text:'Final reply.'}],metadata:{historyProjectionVersion:1,historyProcessAvailable:true,turnId:'same-turn',turnStatus:'completed',finalPartIndex:4,durationMs:1000}}]);setHistorical(true);}],['Attachments',()=>{setThread('file-thread');setMessages([{id:'files',role:'user',parts:[{type:'file',url:'/api/storage/file/Zml4dHVyZQ==',mediaType:'image/png',filename:'Photo.png'},{type:'file',url:'/api/storage/file/ZG9jdW1lbnQ=',mediaType:'application/pdf',filename:'Report.pdf'}]}]);setHistorical(false);}],['Hold reads',()=>{f.hold=true;}],['Hold document close',()=>{f.holdDisposals=true;}],['Release document close',()=>{for(const release of f.pendingDisposals.splice(0))release();}],['Other Thread',()=>{void closeToolResultDocuments(documentOwner).then(()=>{setThread('other-thread');setMessages([{id:'other',role:'assistant',parts:[{type:'text',text:'Other reply.'}]}]);setHistorical(false);});}]];
 return <View style={{height:'100vh'}}><View style={{flexDirection:'row',flexWrap:'wrap'}}>{controls.map(([name,action])=><Pressable key={name} accessibilityRole="button" onPress={action} style={{padding:8}}><Text>{name}</Text></Pressable>)}</View>
 <List messages={messages} threadId={thread} origin={location.origin} isLoading={false} transport={transport} historicalMessageIds={historical?new Set(messages.map(message=>message.id)):new Set()}
 renderOtherPart={(part,message,index,presentation)=>isToolUIPart(part)?<Tool documentOwner={documentOwner} part={part} origin={location.origin} threadId={thread} presentation={presentation} isLoading={false} active toolChoice="manual" sendUserMessage={async value=>f.messages.push(value)} addToolResult={()=>{}} onConfirmationSettled={id=>f.settled.push(id)} onSessionExpired={()=>{}} onEditorJump={value=>f.jumps.push(value)}/>:part.type==='file'?<File part={part} origin={location.origin} isUserMessage={message.role==='user'} resources={resources}/>:null}/>
 </View>;
}createRoot(document.querySelector('#root')).render(<Harness/>);`;
let vite:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
  vite=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-native-tools-20261030/cache/native-tools',optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','ai','zod','react-i18next','i18next','react-markdown','remark-gfm']},define:{__DEV__:'false'},resolve:{alias:[{find:/^react-native$/,replacement:'/native-tool-platform.tsx'},{find:/^react-native-svg$/,replacement:root+'node_modules/react-native-svg/lib/module/elements.web.js'}]},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{name:'native-tool-boundaries',enforce:'pre',resolveId(id,importer){if(id==='/native-tool-platform.tsx')return '\0native-tool-platform';if(id==='react-native-webview')return '\0native-tool-webview';if(id==='/native-tools-entry.tsx')return '\0native-tools-entry';if(id==='../../hooks/useCopy'&&importer?.includes('/components/chat/'))return root+'app/_dream/hooks/useCopy.native.ts';if(id==='./Icons'&&importer?.includes('/components/chat/'))return root+'app/_dream/components/chat/Icons.native.tsx';},async load(id){const value=id==='\0native-tool-platform'?platform:id==='\0native-tool-webview'?webview:id==='\0native-tools-entry'?entry:null;if(value)return transformWithEsbuild(value,id+'.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(server){server.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-tools')return next();res.setHeader('Content-Type','text/html');res.end(await server.transformIndexHtml('/native-tools','<html><head><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/native-tools-entry.tsx"></script></body></html>'));});}}]});await vite.listen();const address=vite.httpServer!.address();if(!address||typeof address==='string')throw Error('No fixture address');base=`http://127.0.0.1:${address.port}/native-tools`;
});
test.afterAll(async()=>{await vite?.close();});
test.beforeEach(async({page})=>{await page.addInitScript(()=>localStorage.setItem('ink-language','en'));await page.goto(base);await expect(page.getByText('Final reply.',{exact:true})).toBeVisible();});
test('original tool output, Write preview and Copy are visible without exposing the task envelope',async({page})=>{
  await expect(page.getByText('original',{exact:true})).toBeVisible();await expect(page.getByText('Exit code: 0',{exact:true})).toBeVisible();await expect(page.getByText('Full file preview',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Copy',exact:true}).first().click();expect(await page.evaluate(()=>(window as any).__nativeTools.copies[0])).toBe('$ printf original\noriginal\nExit code: 0');
});
test('a completed live App document retains its draft and identity after canonical ID recovery and process collapse',async({page})=>{
  const draft=page.getByRole('textbox',{name:'DOM draft tool-form'});await expect(draft).toBeVisible();await draft.fill('Keep App form');const before=await page.evaluate(()=>(window as any).__nativeTools.docs['tool-form'].id);
  await page.getByRole('button',{name:'Hydrate history'}).click();await expect(draft).toHaveValue('Keep App form');await expect(page.getByText('Full file preview',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:/Expand/}).click();await expect(page.getByText('Full file preview',{exact:true})).toBeVisible();await page.getByRole('button',{name:/Collapse/}).click();await page.getByRole('button',{name:'Clone current DTO'}).click();
  await expect(draft).toHaveValue('Keep App form');expect(await page.evaluate(()=>(window as any).__nativeTools.docs['tool-form'].id)).toBe(before);expect(await page.evaluate(()=>(window as any).__nativeTools.mounts)).toBe(1);
});
test('saved history prefetches canonical process once and promotes its App while process remains collapsed',async({page})=>{
  await page.getByRole('button',{name:'Deferred history'}).click();await expect(page.getByRole('textbox',{name:'DOM draft tool-form'})).toBeVisible();await expect(page.getByText('Full file preview',{exact:true})).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__nativeTools.processReads)).toBe(1);
});
test('document callbacks reject a foreign frame and preserve the two text parts and matched acknowledgement',async({page})=>{
  await expect(page.getByRole('textbox',{name:'DOM draft tool-form'})).toBeVisible();
  await page.evaluate(()=>{const d=(window as any).__nativeTools.docs['tool-form'];d.emit({type:'user-message',requestId:'foreign',message:{role:'user',parts:[{type:'text',text:'Ignore'}]}},'about:srcdoc');d.emit({type:'user-message',requestId:'accepted',message:{role:'user',parts:[{type:'text',text:'First'},{type:'text',text:'Second'}]}});});
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.messages.length)).toBe(1);expect(await page.evaluate(()=>(window as any).__nativeTools.messages[0].parts)).toEqual([{type:'text',text:'First'},{type:'text',text:'Second'}]);await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.acks.length)).toBe(1);
});
test('message attachments keep native private bytes and export only after the original explicit download',async({page})=>{
  await page.getByRole('button',{name:'Attachments',exact:true}).click();await expect(page.getByRole('img',{name:'Photo.png'})).toBeVisible();expect(await page.evaluate(()=>(window as any).__nativeTools.exports.length)).toBe(0);
  await page.getByRole('button',{name:'Download Report.pdf',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.exports.length)).toBe(1);const reads=await page.evaluate(()=>(window as any).__nativeTools.reads);expect(reads.map((value:any)=>value.source)).toEqual(['message','message']);expect(reads.every((value:any)=>value.method==='GET'&&value.path.startsWith('/api/storage/file/'))).toBe(true);
  await page.getByRole('button',{name:'Other Thread'}).click();expect(await page.evaluate(()=>(window as any).__nativeTools.released.length)).toBe(2);
});
test('a cancelled attachment read releases a late native handle after Thread navigation',async({page})=>{
  await page.getByRole('button',{name:'Hold reads'}).click();await page.getByRole('button',{name:'Attachments',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.pending.length)).toBe(1);await page.getByRole('button',{name:'Other Thread'}).click();
  await page.evaluate(()=>(window as any).__nativeTools.pending[0]());await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.released.length)).toBe(1);await expect(page.getByText('Other reply.',{exact:true})).toBeVisible();await expect(page.getByRole('img',{name:'Photo.png'})).toHaveCount(0);
});

test('an image decoder failure retains the original file download and an explicit retry restores preview',async({page})=>{
 await page.evaluate(()=>(window as any).__nativeTools.imageFailure=true);await page.getByRole('button',{name:'Attachments',exact:true}).click();
 await expect(page.getByRole('alert')).toBeVisible();await page.getByRole('button',{name:'Download Photo.png',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.exports.length)).toBe(1);
 await page.evaluate(()=>(window as any).__nativeTools.imageFailure=false);await page.getByRole('button',{name:'Retry',exact:true}).click();await expect(page.getByRole('img',{name:'Photo.png'})).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);
});


test('Native navigation waits for its matched document close acknowledgement',async({page})=>{
  await expect(page.getByRole('textbox',{name:'DOM draft tool-form'})).toBeVisible();
  await page.getByRole('button',{name:'Hold document close',exact:true}).click();await page.getByRole('button',{name:'Other Thread',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeTools.disposals.length)).toBe(1);
  await expect(page.getByText('Other reply.',{exact:true})).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__nativeTools.unmounts)).toBe(0);
  await page.evaluate(()=>{const f=(window as any).__nativeTools;f.docs['tool-form'].emit({type:'disposed',requestId:'unknown-request'});});
  await expect(page.getByText('Other reply.',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Release document close',exact:true}).click();await expect(page.getByText('Other reply.',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>(window as any).__nativeTools.unmounts)).toBe(1);
});
