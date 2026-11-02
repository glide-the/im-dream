// [Input] Production Writing routes/components, original session/preferences DTO fixture and installed Chrome.
// [Output] Mobile typography, chooser scrolling/navigation/selection/cancellation, retry and desktop preservation evidence.
// [Pos] Provider-free browser interaction; DOM touch dispatch and fake native boundaries do not qualify device gestures or keyboards.
// Impact: synthetic Writing text/selection and intercepted session/preference writes change. Authentication/permissions and
// original persistence owners remain. Project, Episode, canonical Artifact, Run-private publication, Hook and models are out of scope.
import {expect,test,type Page} from '@playwright/test';
import {installReflectionFixtures} from './fixtures/reflectionsHarness';
const base=process.env.E2E_WEB_BASE;
if(!base)throw Error('E2E_WEB_BASE_REQUIRED');
const evidence=process.env.INK_WRITING_EVIDENCE_DIR??'/tmp/ink-writing-mobile-implementation-20261101/validation';
const states={happy:{name:'Happy',prompt:'happy'},ok:{name:'OK',prompt:'ok'},unhappy:{name:'Unhappy',prompt:'unhappy'}};
async function open(page:Page,{width=390,height=844,selected='happy',document=false,long=false,fail=false}:{width?:number;height?:number;selected?:string|null;document?:boolean;long?:boolean;fail?:boolean}={}){
 const f=await installReflectionFixtures(page),writes:any[]=[],saves:any[]=[],errors=f.errors;let failNext=fail;
 if(fail)f.allowHttpError(503,'/api/preferences');
 await page.addInitScript(()=>localStorage.setItem('ink-language','zh'));
 await page.route('**/api/preferences',async route=>{
  if(route.request().method()==='GET')return route.fulfill({json:{first_login_completed:true,timezone:'UTC',selected_state:selected,updated_at:'2026-09-28T12:00:00Z',state_config:{states,greeting:long?'Today is a day to explore how you feel. '.repeat(45):'How are you feeling today?'}}});
  const body=route.request().postDataJSON();if('selected_state' in body){writes.push(body);if(failNext){failNext=false;return route.fulfill({status:503,json:{detail:'fixture preference save failed'}});}}
  return route.fulfill({json:{success:true}});
 });
 await page.route('**/api/sessions',async route=>{if(route.request().method()!=='POST')return route.fallback();saves.push(route.request().postDataJSON());return route.fulfill({json:{success:true}});});
 await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));
 await page.setViewportSize({width,height});
 if(document)await page.addInitScript(()=>{
  const f=(window as any).__writingDocument={events:[],revision:0,documentId:''};
  f.send=(overrides:any={})=>window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({type:'state',documentId:f.documentId,revision:++f.revision,active:true,theme:'light',language:'en',showEnergyBar:true,...overrides})}));
  (window as any).ReactNativeWebView={postMessage:(raw:string)=>{const event=JSON.parse(raw);f.events.push(event);if(event.type==='ready'){f.documentId=event.documentId;f.send();}}};
 });
 await page.goto(base+(document?'/native/writing':'/story-workspace/writing'),{waitUntil:'domcontentloaded'});
 await expect(page.locator('textarea.writing-prose').first()).toBeVisible();
 await expect.poll(()=>page.locator('.state-chooser').count()).toBe(1);
 return {f,writes,saves,errors};
}
async function assertGeometry(page:Page){
 return page.locator('textarea.writing-prose').first().evaluate(el=>{const s=getComputedStyle(el);return {font:parseFloat(s.fontSize),line:parseFloat(s.lineHeight),padding:s.padding,display:s.display,background:s.backgroundImage,height:el.clientHeight,scroll:el.scrollHeight};});
}
test('mobile Writing shares line metrics, resizes long prose and returns through the original More menu',async({page})=>{
 const f=await open(page);const editor=page.locator('textarea.writing-prose').first();
 await editor.fill('');const empty=await assertGeometry(page);expect(Math.abs(empty.height-empty.line)).toBeLessThanOrEqual(1);
 await expect(page.locator('.writing-page-header').getByRole('button',{name:'Happy',exact:true})).toBeVisible();
 const text='An ordinary morning. 中文段落会随着可用宽度自动换行。 '.repeat(45)+'\n\nA final line.\n';await editor.fill(text);
 await expect.poll(async()=>{const g=await assertGeometry(page);return g.scroll-g.height;}).toBeLessThanOrEqual(1);
 let g=await assertGeometry(page);expect(g.font).toBe(18);expect(g.line).toBeCloseTo(28.8,1);expect(g.padding).toBe('0px');expect(g.display).toBe('block');expect(g.background).toContain('28.8px');
 await page.locator('.writing-page').evaluate(el=>(el as HTMLElement).style.setProperty('--writing-font-size','22px'));
 await expect.poll(async()=>Math.round((await assertGeometry(page)).line*10)).toBe(352);
 await page.setViewportSize({width:320,height:568});await expect.poll(async()=>{const g=await assertGeometry(page);return g.scroll-g.height;}).toBeLessThanOrEqual(1);await expect(editor).toHaveValue(text);
 await editor.focus();await page.locator('.writing-page-header').getByRole('button',{name:'Happy',exact:true}).click();await expect(editor).not.toBeFocused();await expect(page.getByRole('dialog',{name:'How are you feeling today?'})).toBeVisible();
 await page.getByRole('button',{name:'← 更多',exact:true}).click();await expect(page.getByRole('dialog',{name:'更多',exact:true})).toBeVisible();expect(f.writes).toEqual([]);
 await page.getByRole('dialog',{name:'更多',exact:true}).getByRole('button',{name:'写作',exact:true}).click();await expect(page.locator('.state-chooser-overlay')).toHaveCount(0);await expect(editor).toHaveValue(text);
 await expect.poll(()=>f.saves.some(save=>save.editor_state?.cells?.some((cell:any)=>cell.content===text))).toBe(true);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(f.errors).toEqual([]);expect(f.f.createRequests).toEqual([]);await page.screenshot({path:evidence+'/writing-mobile.png'});
});
test('short chooser scrolls all content, touch dragging does not select and clicking submits once',async({page})=>{
 const f=await open(page,{height:360,selected:null,long:true});const scroll=page.locator('.state-chooser-scroll');await expect(scroll).toBeVisible();
 expect(await scroll.evaluate(el=>el.scrollHeight>el.clientHeight)).toBe(true);
 const bounds=await scroll.boundingBox();expect(bounds).not.toBeNull();
 const touch=await page.context().newCDPSession(page);
 const x=bounds!.x+bounds!.width/2,y=bounds!.y+bounds!.height-20,distance=Math.min(160,bounds!.height-40);
 await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
 for(let step=1;step<=8;step++){
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-distance*step/8}]});
  await page.waitForTimeout(16); // One gesture frame; no product readiness delay.
 }
 await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await expect.poll(()=>scroll.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);expect(f.writes).toEqual([]);await touch.detach();
 await scroll.evaluate(el=>{el.scrollTop=el.scrollHeight;});await expect(page.getByText('选择心情，开始写作',{exact:true})).toBeInViewport();
 const option=page.getByRole('button',{name:'Happy',exact:true});await option.scrollIntoViewIfNeeded();
 await option.dispatchEvent('pointerdown',{pointerType:'touch',clientX:120,clientY:190});await option.dispatchEvent('pointermove',{pointerType:'touch',clientX:120,clientY:140});await option.dispatchEvent('pointercancel',{pointerType:'touch'});await option.dispatchEvent('click');
 expect(f.writes).toEqual([]);
 await option.click();await expect.poll(()=>f.writes.length).toBe(1);expect(f.writes[0]).toEqual({selected_state:'happy'});await expect(page.locator('.state-chooser-overlay')).toHaveCount(0);await expect(page.locator('textarea.writing-prose').first()).not.toBeFocused();expect(f.errors).toEqual([]);
});
test('page return cancels both pending selection stages without changing the stored choice',async({page})=>{
 const f=await open(page);const action=page.locator('.writing-page-header').getByRole('button',{name:'Happy',exact:true});
 for(const delay of [0,260]){
  await action.click();await page.getByRole('dialog').getByRole('button',{name:'OK',exact:true}).click();
  if(delay)await page.waitForTimeout(delay); // Exercise both sides of the original 200ms callback.
  await page.getByRole('button',{name:'← 更多',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'更多',exact:true})).toBeVisible();
  await page.waitForTimeout(1100); // Exceed the original combined 200ms/800ms submission delay.
  expect(f.writes).toEqual([]);
  await page.getByRole('dialog',{name:'更多',exact:true}).getByRole('button',{name:'写作',exact:true}).click();
  await expect(action).toBeVisible();await expect(page.locator('.state-chooser-overlay')).toHaveCount(0);
 }
 expect(f.errors).toEqual([]);
});
test('failed preference save keeps the value and retries without creating another session',async({page})=>{
 const f=await open(page,{fail:true});await page.locator('.writing-page-header').getByRole('button',{name:'Happy',exact:true}).click();await page.getByRole('dialog').getByRole('button',{name:'OK',exact:true}).click();
 await expect(page.getByRole('alert').filter({hasText:'心情保存失败'})).toBeVisible();await expect(page.locator('.writing-page-header').getByRole('button',{name:'OK',exact:true})).toBeVisible();
 const sessionIds=()=>new Set(f.saves.map(save=>save.session_id));const before=sessionIds();await page.getByRole('alert').getByRole('button').click();await expect.poll(()=>f.writes.length).toBe(2);await expect(page.getByRole('alert').filter({hasText:'心情保存失败'})).toHaveCount(0);
 expect(f.writes).toEqual([{selected_state:'ok'},{selected_state:'ok'}]);expect([...sessionIds()].every(id=>before.has(id))).toBe(true);expect(f.errors.filter(error=>!error.startsWith('console: Failed to save state to database:'))).toEqual([]);expect(f.errors.filter(error=>error.startsWith('console: Failed to save state to database:'))).toHaveLength(1);
});
test('native document stays mobile in landscape and consumes the header open nonce once',async({page})=>{
 const f=await open(page,{document:true,width:844,height:390});await expect(page.locator('.writing-page-header')).toHaveCount(0);await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.some((e:any)=>e.type==='chooser-view'&&!e.loading&&!e.expanded))).toBe(true);
 expect((await assertGeometry(page)).line).toBeCloseTo(28.8,1);
 await page.evaluate(()=>(window as any).__writingDocument.send({openChooserNonce:1}));await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'OK',exact:true}).click();await expect.poll(()=>f.writes.length).toBe(1);await expect(page.locator('.state-chooser-overlay')).toHaveCount(0);
 await page.evaluate(()=>(window as any).__writingDocument.send({openChooserNonce:1}));await expect(page.locator('.state-chooser-overlay')).toHaveCount(0);
 await page.evaluate(()=>(window as any).__writingDocument.send({active:false}));await page.evaluate(()=>(window as any).__writingDocument.send({active:true}));await expect(page.locator('.state-chooser-overlay')).toHaveCount(0);
 expect(await page.evaluate(()=>(window as any).__writingDocument.events.filter((e:any)=>e.type==='ready').length)).toBe(1);expect(f.errors).toEqual([]);
});
test('desktop retains original line height, compact chooser and floating Writing tools',async({page})=>{
 const f=await open(page,{width:1280});await expect(page.locator('.writing-page-header')).toHaveCount(0);await expect(page.locator('.state-chooser').getByText('Happy',{exact:true})).toBeVisible();expect((await assertGeometry(page)).line).toBeCloseTo(32.4,1);
 expect(await page.locator('.notebook-lines').evaluate(el=>getComputedStyle(el).backgroundImage)).toContain('32.4px');await expect(page.locator('.writing-mobile-tools')).toHaveCount(0);expect(f.errors).toEqual([]);await page.screenshot({path:evidence+'/writing-desktop.png'});
});

test('font swap recomputes original textarea height without changing text or selection',async({page})=>{
 let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
 await page.route('**/Excalifont-Regular.woff2',async route=>{await gate;await route.continue();});
 const f=await open(page);const editor=page.locator('textarea.writing-prose').first();
 const text='A long handwritten sentence changes wrapping when its font is ready. '.repeat(45);
 await editor.fill(text);await editor.focus();await editor.evaluate(el=>el.setSelectionRange(12,25));
 release();await page.evaluate(()=>document.fonts.ready);
 await expect.poll(async()=>{const g=await assertGeometry(page);return g.scroll-g.height;}).toBeLessThanOrEqual(1);
 await expect(editor).toHaveValue(text);expect(await editor.evaluate(el=>[el.selectionStart,el.selectionEnd])).toEqual([12,25]);expect(f.errors).toEqual([]);
});
