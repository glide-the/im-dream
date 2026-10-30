// [Input] Production sketch-only Next document, original SketchInputDialog and its PNG protocol.
// [Output] Drawing retention, acknowledgement/retry and narrow-screen technical evidence without uploads.
// [Pos] Explicit browser harness; all business/auth/external requests are rejected and no real provider is used.
import {test,expect,type Page} from '@playwright/test';
import {readSketchEvent,readSketchResult,readSketchState,sketchDocumentUrl,type SketchDocumentState} from '../app/_dream/components/chat/SketchInputDocument.protocol';
const base=process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
type Event={type:string;documentId:string;requestId?:string;base64?:string;size?:number;name?:string};
declare global {interface Window {__sketchFixture:{events:Event[];state:SketchDocumentState};}}
const errors=new WeakMap<Page,string[]>();
async function state(page:Page,patch:Partial<SketchDocumentState>) {await page.evaluate(patch=>{const f=window.__sketchFixture;f.state={...f.state,revision:f.state.revision+1,...patch};window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(f.state)}));},patch);}
async function result(page:Page,accepted:boolean,overrides:Record<string,string>={}) {await page.evaluate(({accepted,overrides})=>{const event=window.__sketchFixture.events.filter(event=>event.type==='add').at(-1)!;window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({type:'result',documentId:event.documentId,requestId:event.requestId,accepted,...overrides})}));},{accepted,overrides});}
async function draw(page:Page) {const canvas=page.locator('canvas');await canvas.scrollIntoViewIfNeeded();const box=await canvas.boundingBox();if(!box)throw new Error('CANVAS_MISSING');await page.mouse.move(box.x+box.width*.35,box.y+box.height*.5);await page.mouse.down();await page.mouse.move(box.x+box.width*.6,box.y+box.height*.55,{steps:12});await page.mouse.up();}
async function ink(page:Page) {return page.locator('canvas').evaluate((canvas:HTMLCanvasElement)=>{const bytes=canvas.getContext('2d')!.getImageData(0,0,canvas.width,canvas.height).data;let count=0;for(let i=0;i<bytes.length;i+=4)if(bytes[i]<255 || bytes[i+1]<255 || bytes[i+2]<255)count++;return count;});}
test.beforeEach(async({page})=>{
  const diagnostics:string[]=[];errors.set(page,diagnostics);page.on('pageerror',error=>diagnostics.push(error.message));
  await page.addInitScript(()=>{const f=window.__sketchFixture={events:[],state:{type:'state',documentId:'',revision:0,open:true,disabled:false,theme:'light',language:'en'} as SketchDocumentState};window.ReactNativeWebView={postMessage(raw){const event=JSON.parse(raw);f.events.push(event);if(event.type==='ready'){f.state.documentId=event.documentId;window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(f.state)}));}if(event.type==='close'){f.state={...f.state,revision:f.state.revision+1,open:false};window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(f.state)}));}}};});
  await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin!==new URL(base).origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')){diagnostics.push('Unexpected sketch request: '+url.pathname);return route.abort();}return route.continue();});
  await page.goto(base+'/native/sketch');await expect(page.getByRole('button',{name:'Pen',exact:true})).toBeVisible();
});
test.afterEach(async({page})=>{expect(errors.get(page)).toEqual([]);});
test('closing and reopening preserves the original drawing and undo history; stale state cannot hide it',async({page})=>{
  await draw(page);const before=await ink(page);expect(before).toBeGreaterThan(0);
  await page.getByRole('button',{name:'Back',exact:true}).last().click();await expect(page.locator('canvas')).toHaveCount(0);
  await state(page,{open:true});await expect(page.locator('canvas')).toBeVisible();expect(await ink(page)).toBe(before);
  await state(page,{revision:0,open:false});await expect(page.locator('canvas')).toBeVisible();
  await state(page,{documentId:crypto.randomUUID(),revision:100,open:false});await expect(page.locator('canvas')).toBeVisible();
  await page.getByRole('button',{name:'Undo',exact:true}).click();expect(await ink(page)).toBe(0);
});
test('PNG waits for the matching upload receipt, preserves drawing on rejection and clears only after success',async({page})=>{
  await draw(page);const before=await ink(page);await page.getByRole('button',{name:'Add to message',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>window.__sketchFixture.events.filter(event=>event.type==='add').length)).toBe(1);
  const event=await page.evaluate(()=>window.__sketchFixture.events.find(event=>event.type==='add')!);expect(readSketchEvent(JSON.stringify(event))).not.toBeNull();
  const bytes=Buffer.from(event.base64!,'base64');expect(bytes.subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));expect(bytes.length).toBe(event.size);expect(event.name).toMatch(/\.png$/);
  await result(page,true,{requestId:crypto.randomUUID()});await expect(page.getByRole('button',{name:'Adding…',exact:true})).toBeDisabled();
  await result(page,false);await expect(page.getByRole('button',{name:'Add to message',exact:true})).toBeEnabled();expect(await ink(page)).toBe(before);
  await page.getByRole('button',{name:'Add to message',exact:true}).click();await expect.poll(()=>page.evaluate(()=>window.__sketchFixture.events.filter(event=>event.type==='add').length)).toBe(2);
  await result(page,true);await expect(page.locator('canvas')).toHaveCount(0);
  await state(page,{open:true});expect(await ink(page)).toBe(0);await expect(page.getByRole('button',{name:'Add to message',exact:true})).toBeDisabled();
});
test('native state applies original Chinese labels, dark theme and disabled drawing at narrow size',async({page})=>{
  await page.setViewportSize({width:390,height:844});await state(page,{language:'zh',theme:'dark',disabled:true});
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await expect(page.getByRole('button',{name:'画笔',exact:true})).toBeDisabled();
  await draw(page);expect(await ink(page)).toBe(0);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('sketch protocol rejects malformed identities, paths, lengths and nonlocal document origins',()=>{
  const documentId=crypto.randomUUID(),requestId=crypto.randomUUID();const event={type:'add',documentId,requestId,name:'sketch.png',size:3,base64:'AAAA'};
  expect(readSketchEvent(JSON.stringify(event))).not.toBeNull();
  for(const patch of [{documentId:'old'},{name:'../x.png'},{name:'x.txt'},{size:2},{size:0},{base64:'%%%='}])expect(readSketchEvent(JSON.stringify({...event,...patch}))).toBeNull();
  expect(readSketchState({type:'state',documentId,revision:0,open:true,disabled:false,theme:'system',language:'en'})).not.toBeNull();
  expect(readSketchResult({type:'result',documentId,requestId,accepted:true})).not.toBeNull();
  expect(sketchDocumentUrl('http://[::1]:5173')).toBe('http://[::1]:5173/native/sketch');expect(()=>sketchDocumentUrl('https://example.com')).toThrow();
});
