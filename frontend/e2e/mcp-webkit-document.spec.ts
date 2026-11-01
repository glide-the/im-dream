// [Sync] 2026-10-31: compiled production disposal acknowledgement follows original MCP DELETE and zero active synthetic sessions.
// [Input] Explicit loopback fixture server and production document/chunks from the actual Simulator App.
// [Output] Browser baseline for original SDK handshake, form persistence and unchanged two-part message ingress.
// [Pos] Provider-free qualification; actual WebKit/Hermes is a separate platform gate.
import {test,expect,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
const info=JSON.parse(readFileSync('/tmp/ink-ios-mcp-webkit-20261031/fixture-info.json','utf8')) as {origin:string};
const origin=info.origin;
const app=(page:Page)=>page.frameLocator('[data-testid="im-mcp-app-host-frame"]').frameLocator('[data-testid="im-mcp-app-resource-frame"]');
const errors=new WeakMap<Page,string[]>(),expectedDenials=new WeakMap<Page,string[]>();
test.beforeEach(async({page,request})=>{
 const diagnostics:string[]=[],denials:string[]=[];errors.set(page,diagnostics);expectedDenials.set(page,denials);page.on('pageerror',error=>diagnostics.push(error.message));page.on('console',message=>{if(message.type()==='error'){if(message.location().url===origin+'/api/mcp-apps/ios-mcp-webkit-fixture'&&message.text()==='Failed to load resource: the server responded with a status of 403 (Forbidden)')denials.push(message.text());else diagnostics.push(message.text());}});
 await request.post(origin+'/__fixture/control',{data:{reset:true}});
 await page.addInitScript(()=>{if(window.top!==window)return;localStorage.setItem('ink-language','en');(window as any).__toolEvents=[];(window as any).ReactNativeWebView={postMessage:(data:string)=>(window as any).__toolEvents.push(JSON.parse(data))};});
 await page.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();diagnostics.push('Unexpected external request');return route.abort();});
 await page.goto(origin+'/native/tool-result');
 await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='ready')?.documentId)).toBeTruthy();
 const fixture=await(await request.get(origin+'/__fixture/state')).json();const documentId=await page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='ready').documentId);
 await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'state',documentId,threadId:'webkit-thread',toolCallId:fixture.part.toolCallId,revision:1,part:fixture.part,presentation:'app-only',editorCompleted:false,active:true,settledToolCallIds:[],theme:'light',language:'en'});
 await expect(app(page).getByLabel('App draft')).toBeVisible();
});
test.afterEach(async({page},info)=>{expect(errors.get(page)??[]).toEqual([]);expect(expectedDenials.get(page)??[]).toHaveLength(info.title.includes('returns server refusal')?1:0);});
test('production document/SDK retains form after new state and returns unchanged two-part message',async({page,request})=>{
 await app(page).getByLabel('App draft').fill('Keep WebKit form');
 const fixture=await(await request.get(origin+'/__fixture/state')).json();const documentId=await page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='ready').documentId);
 await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'state',documentId,threadId:'webkit-thread',toolCallId:fixture.part.toolCallId,revision:2,part:fixture.part,presentation:'app-only',editorCompleted:false,active:true,settledToolCallIds:[],theme:'dark',language:'en'});
 await expect(app(page).getByLabel('App draft')).toHaveValue('Keep WebKit form');await app(page).getByRole('button',{name:'Send follow-up',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.filter((value:any)=>value.type==='user-message').length)).toBe(1);
 const event=await page.evaluate(()=>(window as any).__toolEvents.find((value:any)=>value.type==='user-message'));expect(event.message.parts).toEqual([{type:'text',text:'Keep WebKit form'},{type:'text',text:'Second text block'}]);
 await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'result',documentId,threadId:event.threadId,toolCallId:event.toolCallId,requestId:event.requestId,accepted:true});await expect(app(page).getByText('Sent',{exact:true})).toBeVisible();
});
test('original Host returns server refusal, limits external links and closes its own MCP session',async({page,request})=>{
 await app(page).getByRole('button',{name:'Call read-only tool',exact:true}).click();await expect(app(page).getByText('Tool called',{exact:true})).toBeVisible();
 const denial=page.waitForResponse(response=>response.url()===origin+'/api/mcp-apps/ios-mcp-webkit-fixture'&&response.status()===403);await app(page).getByRole('button',{name:'Call restricted tool',exact:true}).click();expect((await denial).status()).toBe(403);await expect(app(page).getByText('Restricted tool denied',{exact:true})).toBeVisible();
 await app(page).getByRole('button',{name:'Open external link',exact:true}).click();await expect(app(page).getByText('External link denied',{exact:true})).toBeVisible();
 let state=await(await request.get(origin+'/__fixture/state')).json();expect(state.calls).toBe(1);expect(state.restrictedCalls).toBe(0);expect(state.restrictedAttempts).toBe(1);
 await page.getByTestId('mcp-app-close').click();await expect.poll(async()=>{state=await(await request.get(origin+'/__fixture/state')).json();return state.deletes;}).toBe(1);
});

test('compiled production document closes its original MCP session before disposal acknowledgement',async({page,request})=>{
 const fixture=await(await request.get(origin+'/__fixture/state')).json();const documentId=await page.evaluate(()=>(window as any).__toolEvents.find((row:any)=>row.type==='ready').documentId);
 await page.evaluate(value=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(value)})),{type:'dispose',documentId,threadId:'webkit-thread',toolCallId:fixture.part.toolCallId,requestId:'production-close'});
 await expect.poll(()=>page.evaluate(()=>(window as any).__toolEvents.filter((value:any)=>value.type==='disposed').length)).toBe(1);
 const state=await(await request.get(origin+'/__fixture/state')).json();expect(state.deletes).toBe(1);expect(state.activeSessions).toBe(0);
});
