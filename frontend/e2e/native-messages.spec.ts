// [Sync] 2026-11-03: qualify viewport-bound user previews, intrinsic code geometry and layout/reading scroll ownership for APP-06.
// [Input] Production native message renderer/Markdown and public process DTOs with explicit transport/clipboard fixtures.
// [Output] Technical GFM, bottom-follow, user scroll, shared process prefetch/validation/retry/cancellation and copy receipts.
// [Pos] Provider-free browser harness; Native/RNW presentation is real, backend/account/model/clipboard writes are fixtures.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
// RNW emits a browser load Event; the native component consumes iOS ImageLoadEventData.
const native=`export * from 'react-native-web';import {Image as WebImage} from 'react-native-web';import {forwardRef,createElement} from 'react';
export const Image=forwardRef((props,ref)=>createElement(WebImage,{...props,ref,onLoad:event=>props.onLoad?.({nativeEvent:{source:{width:event.nativeEvent.target.naturalWidth,height:event.nativeEvent.target.naturalHeight}}})}));
export const NativeModules={InkRuntime:{copyText:async text=>{window.__messagesFixture.copies.push(text);}}};`;
const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';import {View,Text,Pressable} from 'react-native';
import '/app/_dream/i18n.ts';import List from '/app/_dream/components/chat/ChatMessageList.native.tsx';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';
const f=window.__messagesFixture={copies:[],links:[],reads:[],bad:false,hold:false,pending:[],older:0};
const rich='## Native heading\n\n**Bold text** and *emphasis*, ~~removed~~, 中文🙂.\n\n1. First item\n2. Second item\n   - Nested item\n\n- [x] Finished task\n- [ ] Open task\n\n> Quoted text\n\n| Column A | Column B |\n| --- | --- |\n| Cell A | Cell B |\n\n\x60inline code\x60\n\n\x60\x60\x60js\nconst value = 1;\n\x60\x60\x60\n\n[Docs](https://example.test/docs) [Workspace](workspace://files/note.md) [Unsafe](javascript:alert(1))\n\n<script>window.__htmlExecuted=true</script>';
function rows(){return Array.from({length:24},(_,i)=>({id:'message-'+i,role:i%2?'assistant':'user',parts:[{type:'text',text:i===23?rich:('Reading message '+i+'. ').repeat(18)}]}));}
const summary={id:'history-summary',role:'assistant',parts:[{type:'text',text:'Final authoritative reply.'}],metadata:{historyProjectionVersion:1,historyProcessAvailable:true,turnId:'history-turn',turnStatus:'completed',finalPartIndex:1,durationMs:1200}};
async function transport(input,init={}){
 const path=String(input);if(path==='/auth/session')return new Response(JSON.stringify({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
 f.reads.push({path,method:init.method??'GET',headers:Object.fromEntries(new Headers(init.headers).entries()),signal:init.signal});
 if(!path.endsWith('/messages/history-summary/process'))throw new Error('Unexpected fixture process path');
 if(f.hold)await new Promise(resolve=>f.pending.push(resolve));
 return new Response(JSON.stringify({id:'history-summary',role:'assistant',parts:[{type:'reasoning',text:'Canonical stored reasoning.'},{type:'text',text:f.bad?'Conflicting final.':'Final authoritative reply.'}],metadata:{turnId:'history-turn',turnStatus:'completed',finalPartIndex:1,durationMs:1200},created_at:'2026-10-28T00:00:00Z'}));
}
function Harness(){const [messages,setMessages]=useState(rows),[thread,setThread]=useState('fixture-thread'),[history,setHistory]=useState(false),[more,setMore]=useState(false),[ready,setReady]=useState(false);
 f.present=(rows,thread='fixture-thread')=>{setMessages(rows);setThread(thread);setHistory(false);setMore(false);};
 React.useEffect(()=>{void loadBrowserSession(transport).then(()=>setReady(true));},[]);
 const buttons=[['Append stream',()=>setMessages(current=>current.map((row,i)=>i===current.length-1?{...row,parts:[{type:'text',text:row.parts[0].text+'\n\n'+('Streamed final token. ').repeat(20)}]}:row))],['History summary',()=>{setMessages([summary]);setHistory(true);setMore(true);}],['Long conversation',()=>{setMessages(rows());setHistory(false);setMore(false);setThread(value=>value+'-next');}],['Mismatch process',()=>{f.bad=true;}],['Valid process',()=>{f.bad=false;}],['Hold process',()=>{f.hold=true;}],['Other Thread',()=>{setThread('other-thread');setMessages([{id:'other',role:'assistant',parts:[{type:'text',text:'Other Thread reply.'}]}]);setHistory(false);}]];
 return <View style={{height:'100vh'}}><View style={{flexDirection:'row',flexWrap:'wrap'}}>{buttons.map(([name,action])=><Pressable accessibilityRole="button" key={name} onPress={action} style={{padding:8}}><Text>{name}</Text></Pressable>)}</View>
 {ready?<List messages={messages} threadId={thread} isLoading={false} historicalMessageIds={history?new Set(['history-summary']):new Set()} historyHasMore={more} onLoadOlder={()=>{f.older++;setMore(false);}} transport={transport} onOpenLink={url=>f.links.push(url)}/>:<Text>Preparing fixture</Text>}
 </View>;
}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 const port=await new Promise<number>((resolve,reject)=>{const probe=netServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{const address=probe.address();if(!address||typeof address==='string')return reject(new Error('Port'));probe.close(error=>error?reject(error):resolve(address.port));});});
 server=await createServer({root,configFile:false,logLevel:'silent',server:{host:'127.0.0.1',port,strictPort:true},plugins:[{name:'native-message-presentation',enforce:'pre',resolveId(id,importer){if(id==='react-native')return '\0messages-native';if(id==='/messages-entry.tsx')return '\0messages-entry';if(id==='../../hooks/useCopy'&&importer?.endsWith('/ChatMessageList.native.tsx'))return root+'app/_dream/hooks/useCopy.native.ts';},async load(id){if(id==='\0messages-native')return native;if(id==='\0messages-entry')return transformWithEsbuild(entry,'messages-entry.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-messages')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-messages','<html><head><link rel="icon" href="data:,"><style>html,body{margin:0;height:100%;font-family:Excalifont}#root{height:100%}</style></head><body><div id="root"></div><script type="module" src="/messages-entry.tsx"></script></body></html>'));});}}]});await server.listen();base='http://127.0.0.1:'+port+'/native-messages';
});
test.afterAll(async()=>{await server?.close();});
const errors=new WeakMap<Page,string[]>();
test.beforeEach(async({page})=>{
 const diagnostics:string[]=[];errors.set(page,diagnostics);page.on('pageerror',error=>diagnostics.push(error.message));page.on('console',message=>{if(message.type()==='error')diagnostics.push(message.text());});
 await page.addInitScript(()=>localStorage.setItem('ink-language','en'));
 await page.route('**/*',route=>{if(new URL(route.request().url()).origin===new URL(base).origin)return route.continue();diagnostics.push('Unexpected external request');return route.abort();});
 await page.goto(base);await expect(page.getByTestId('native-chat-messages-scroll')).toBeVisible();
});
test.afterEach(async({page})=>{expect(errors.get(page)??[]).toEqual([]);});
async function position(page:Page){return page.getByTestId('native-chat-messages-scroll').evaluate(element=>({top:element.scrollTop,height:element.scrollHeight,viewport:element.clientHeight}));}
async function bottom(page:Page){const p=await position(page);return p.height-p.viewport-p.top;}
test('long user text has a measured preview, full copy and per-Thread expansion without changing message text',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 const text=Array.from({length:45},(_,i)=>`Paragraph ${i}: A long message preserves its original words and line breaks.`).join('\n\n');
 await page.evaluate(text=>(window as any).__messagesFixture.present([{id:'same-id',role:'user',parts:[{type:'text',text}]},{id:'reply',role:'assistant',parts:[{type:'text',text:'The latest reply.'}]}]),text);
 const row=page.getByTestId('native-chat-message-same-id'),toggle=row.getByRole('button',{name:'Expand message',exact:true});
 await expect(toggle).toBeVisible();await expect(toggle).toHaveAttribute('aria-expanded','false');
 const preview=await row.boundingBox(),viewport=await page.getByTestId('native-chat-messages-scroll').boundingBox();expect(preview!.height).toBeLessThan(viewport!.height*.7);
 await row.getByRole('button',{name:'Copy',exact:true}).click();expect(await page.evaluate(()=>(window as any).__messagesFixture.copies.at(-1))).toBe(text);
 await toggle.click();await expect(row.getByRole('button',{name:'Collapse message',exact:true})).toHaveAttribute('aria-expanded','true');
 await expect.poll(async()=>(await row.boundingBox())!.height).toBeGreaterThan(preview!.height);
 await row.getByRole('button',{name:'Collapse message',exact:true}).click();await expect(toggle).toBeVisible();await expect.poll(()=>bottom(page)).toBeLessThan(2);
 await toggle.click();
 await page.evaluate(text=>(window as any).__messagesFixture.present([{id:'same-id',role:'user',parts:[{type:'text',text}]}],'other-thread'),text);
 await expect(toggle).toHaveAttribute('aria-expanded','false');
 await page.evaluate(()=>(window as any).__messagesFixture.present([{id:'short',role:'user',parts:[{type:'text',text:'A short message.'}]}]));
 await expect(page.getByTestId('native-chat-message-short').getByRole('button',{name:/Expand message|Collapse message/})).toHaveCount(0);
 await page.setViewportSize({width:320,height:200});
 await expect(page.getByTestId('native-chat-message-short').getByRole('button',{name:/Expand message|Collapse message/})).toHaveCount(0);
});
test('code blocks use intrinsic height, contain long lines and retain the latest message after layout changes',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 const code='const longLine = "'+'x'.repeat(240)+'";';
 await page.evaluate(code=>(window as any).__messagesFixture.present([{id:'code-user',role:'user',parts:[{type:'text',text:'```js\n'+code+'\n```'}]},{id:'code-reply',role:'assistant',parts:[{type:'text',text:'Before code.\n\n```\n\n```\n\n- Nested item\n  - Child\n\n```js\nconst small = 1;\n```\n\nLatest visible reply.'}]}]),code);
 await expect(page.getByText('Latest visible reply.',{exact:true})).toBeVisible();await expect.poll(()=>bottom(page)).toBeLessThan(2);
 const small=page.getByText('const small = 1;', {exact:true});
 const codeBox=await small.locator('..').locator('..').boundingBox();expect(codeBox!.height).toBeLessThan(100);
 const long=page.getByText(code,{exact:true}),horizontal=long.locator('..').locator('..');
 expect(await horizontal.evaluate(e=>e.scrollWidth>e.clientWidth)).toBe(true);
 await horizontal.evaluate(e=>{e.scrollLeft=e.scrollWidth;});expect(await horizontal.evaluate(e=>e.scrollLeft)).toBeGreaterThan(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.setViewportSize({width:320,height:480});await expect.poll(()=>bottom(page)).toBeLessThan(2);
 await expect(page.getByText('Latest visible reply.',{exact:true})).toBeInViewport();
});
test('late Markdown image height follows the latest reply and preserves an active historical reading position',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 let release:()=>void=()=>{};const ready=new Promise<void>(resolve=>{release=resolve;});let requested=false;
 await page.route('**/app06-height.svg',async route=>{requested=true;await ready;await route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="80"><rect width="800" height="80" fill="orange"/></svg>'});});
 const image=base.replace('/native-messages','/app06-height.svg');
 await page.evaluate(image=>(window as any).__messagesFixture.present([{id:'late',role:'assistant',parts:[{type:'text',text:'Before image.\n\n![A late diagram]('+image+')\n\nLatest after image.'}]}]),image);
 await expect.poll(()=>requested).toBe(true);await expect.poll(()=>bottom(page)).toBeLessThan(2);release();
 await expect.poll(async()=>(await page.getByRole('img',{name:'A late diagram'}).boundingBox())!.height).toBeLessThan(100);
 await expect.poll(()=>bottom(page)).toBeLessThan(2);
 await page.getByRole('button',{name:'Long conversation',exact:true}).click();await expect.poll(()=>bottom(page)).toBeLessThan(2);
 await page.getByTestId('native-chat-messages-scroll').hover();await page.mouse.wheel(0,-100000);await expect.poll(async()=>(await position(page)).top).toBe(0);
 await page.getByRole('button',{name:'Append stream',exact:true}).click();await expect.poll(async()=>(await position(page)).top).toBe(0);
 await page.setViewportSize({width:320,height:480});await expect.poll(async()=>(await position(page)).top).toBe(0);
 await page.getByRole('button',{name:'Scroll to bottom',exact:true}).click();await expect.poll(()=>bottom(page)).toBeLessThan(2);
});
test('native components retain GFM, literal HTML, safe links, lists/table/code and original Copy text',async({page})=>{
 await expect.poll(()=>bottom(page)).toBeLessThan(2);
 await expect(page.getByRole('heading',{name:'Native heading'})).toBeVisible();
 for(const text of ['Bold text','Second item','Nested item','Finished task','Cell A','Cell B','inline code','const value = 1;'])await expect(page.getByText(text,{exact:true}).first()).toBeVisible();
 await expect(page.getByText('<script>window.__htmlExecuted=true</script>',{exact:true})).toBeVisible();expect(await page.evaluate(()=>(window as any).__htmlExecuted)).toBeUndefined();
 // Table columns must align across header/body after native measurement settles.
 for(const [head,cell] of [['Column A','Cell A'],['Column B','Cell B']])await expect.poll(async()=>{
   const a=await page.getByRole('columnheader',{name:head,exact:true}).boundingBox(),b=await page.getByRole('cell',{name:cell,exact:true}).boundingBox();
   return a&&b?Math.max(Math.abs(a.x-b.x),Math.abs(a.width-b.width)):Number.POSITIVE_INFINITY;
 }).toBeLessThan(1);
 await page.getByRole('link',{name:'Docs',exact:true}).click();expect(await page.evaluate(()=>(window as any).__messagesFixture.links)).toEqual(['https://example.test/docs']);
 await expect(page.getByRole('link',{name:'Workspace',exact:true})).toHaveAttribute('aria-disabled','true');await expect(page.getByRole('link',{name:'Unsafe',exact:true})).toHaveAttribute('aria-disabled','true');
 await page.getByTestId('native-chat-message-message-23').getByRole('button',{name:'Copy',exact:true}).click();
 expect(await page.evaluate(()=>(window as any).__messagesFixture.copies[0])).toContain('## Native heading');await expect(page.getByRole('button',{name:'Copied!',exact:true})).toBeVisible();
});
test('new output follows the bottom while an older reading position is retained until the original jump action',async({page})=>{
 await expect.poll(()=>bottom(page)).toBeLessThan(2);await page.getByRole('button',{name:'Append stream',exact:true}).click();await expect.poll(()=>bottom(page)).toBeLessThan(2);
 await page.getByTestId('native-chat-messages-scroll').hover();await page.mouse.wheel(0,-100000);await expect.poll(async()=>(await position(page)).top).toBe(0);await expect(page.getByRole('button',{name:'Scroll to bottom',exact:true})).toBeVisible();const before=(await position(page)).top;
 await page.getByRole('button',{name:'Append stream',exact:true}).click();await expect.poll(async()=>Math.abs((await position(page)).top-before)).toBeLessThan(2);
 await page.getByRole('button',{name:'Scroll to bottom',exact:true}).click();await expect.poll(()=>bottom(page)).toBeLessThan(2);await expect(page.getByRole('button',{name:'Scroll to bottom',exact:true})).toBeHidden();
 await page.setViewportSize({width:390,height:480});await expect.poll(()=>bottom(page)).toBeLessThan(2);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('shared historical prefetch validates the canonical final and preserves collapsed presentation and pagination',async({page})=>{
 await page.getByRole('button',{name:'History summary',exact:true}).click();await expect(page.getByText('Final authoritative reply.',{exact:true})).toBeVisible();await expect.poll(()=>page.evaluate(()=>(window as any).__messagesFixture.reads.length)).toBe(1);await expect(page.getByText('Canonical stored reasoning.',{exact:true})).toHaveCount(0);
 const disclosure=page.getByRole('button',{name:/Expand|View.*process|展开/i});await disclosure.click();await expect(page.getByText('Canonical stored reasoning.',{exact:true}).last()).toBeVisible();
 const reads=await page.evaluate(()=>(window as any).__messagesFixture.reads.map(({path,method,headers}:any)=>({path,method,headers})));expect(reads).toHaveLength(1);expect(reads[0].path).toBe('/api/claude-agent/threads/fixture-thread/messages/history-summary/process');expect(reads[0].method).toBe('GET');expect(reads[0].headers['x-ink-csrf']).toHaveLength(43);
 await page.getByRole('button',{name:/Collapse/i}).click();await page.getByRole('button',{name:/Expand/i}).click();expect(await page.evaluate(()=>(window as any).__messagesFixture.reads.length)).toBe(1);
 await page.getByRole('button',{name:'Load earlier messages',exact:true}).click();expect(await page.evaluate(()=>(window as any).__messagesFixture.older)).toBe(1);
});
test('mismatched history detail retains the final and the same visible retry recovers',async({page})=>{
 await page.getByRole('button',{name:'Mismatch process',exact:true}).click();await page.getByRole('button',{name:'History summary',exact:true}).click();await page.getByRole('button',{name:/Expand/i}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByText('Conflicting final.',{exact:true})).toHaveCount(0);await expect(page.getByText('Final authoritative reply.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Valid process',exact:true}).click();await page.getByRole('button',{name:'Retry',exact:true}).click();await expect(page.getByText('Canonical stored reasoning.',{exact:true}).last()).toBeVisible();expect(await page.evaluate(()=>(window as any).__messagesFixture.reads.length)).toBe(2);
});
test('Thread navigation aborts a pending process read and rejects its late result',async({page})=>{
 await page.getByRole('button',{name:'Hold process',exact:true}).click();await page.getByRole('button',{name:'History summary',exact:true}).click();await page.getByRole('button',{name:/Expand/i}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__messagesFixture.pending.length)).toBe(1);
 await page.getByRole('button',{name:'Other Thread',exact:true}).click();expect(await page.evaluate(()=>(window as any).__messagesFixture.reads[0].signal.aborted)).toBe(true);await page.evaluate(()=>(window as any).__messagesFixture.pending[0]());await expect(page.getByText('Other Thread reply.',{exact:true})).toBeVisible();await expect(page.getByText('Canonical stored reasoning.',{exact:true})).toHaveCount(0);
});
