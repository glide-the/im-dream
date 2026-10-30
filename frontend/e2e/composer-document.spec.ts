// [Sync] 2026-10-29: cover a nonempty Agent example in the first native ready-state message.
// [Input] Production Next editor-only document and the original MarkdownInputEditor.
// [Output] Technical evidence for rich Markdown, edit acknowledgements, IME/keyboard, theme and document reload.
// [Pos] Native document browser harness; no real account, backend, model, workspace or database writes.
// [Sync] 2026-10-28: active Skill-menu keys emit only selection intents; closing the menu restores normal Enter submission.
// [Sync] 2026-10-28: shrinking/restoring the actual document viewport preserves a long draft and its natural height report.
import {test as baseTest,expect,type Page} from '@playwright/test';
import {composerDocumentUrl,readComposerEvent,readComposerState,type ComposerDocumentState} from '../app/_dream/components/chat/MarkdownInputDocument.protocol';
const base=process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';
const diagnostics=new WeakMap<Page,string[]>();
const test=baseTest.extend<{initialDraft:string}>({initialDraft:['',{option:true}]});
test.use({channel:'chrome',actionTimeout:10_000});
type Event={type:string;documentId:string;eventCount?:number;value?:string;height?:number};
declare global {interface Window {__composerFixture:{events:Event[];state:ComposerDocumentState};}}
async function sendState(page:Page,patch:Partial<ComposerDocumentState>) {
  await page.evaluate(patch=>{
    const fixture=window.__composerFixture;
    fixture.state={...fixture.state,revision:fixture.state.revision+1,...patch};
    window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(fixture.state)}));
  },patch);
}
async function editCount(page:Page) {return page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='change').at(-1)?.eventCount ?? 0);}
test.beforeEach(async({page,initialDraft})=>{
  const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(initialDraft=>{
    const fixture=window.__composerFixture={events:[],state:{type:'state',documentId:'',revision:1,eventCount:0,value:initialDraft,placeholder:'Ask Ink & Memory…',ariaLabel:'Document draft',disabled:false,theme:'light'}};
    window.ReactNativeWebView={postMessage(raw){
      const event=JSON.parse(raw);fixture.events.push(event);
      if(event.type==='ready'){
        fixture.state.documentId=event.documentId;
        window.dispatchEvent(new MessageEvent('message',{data:fixture.state}));
      }
    }};
  },initialDraft);
  await page.route('**/*',route=>{
    const url=new URL(route.request().url());
    if(url.origin!==new URL(base).origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')){errors.push('Unexpected document request: '+url.pathname);return route.abort();}
    return route.continue();
  });
  await page.goto(base+'/native/composer');
  await expect(page.getByRole('textbox',{name:'Document draft'})).toHaveAttribute('contenteditable','true');
  expect(errors).toEqual([]);
});
test.afterEach(async({page})=>{expect(diagnostics.get(page) ?? []).toEqual([]);});
test.describe('first ready-state example',()=>{
  test.use({initialDraft:'You are a helpful assistant.'});
  test('the first nonempty native state renders as a draft without change or submit echoes',async({page})=>{
    await expect(page.getByRole('textbox',{name:'Document draft'})).toHaveText('You are a helpful assistant.');
    expect(await page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='change'||event.type==='submit'))).toEqual([]);
  });
});
test('the original editor renders rich Markdown with original typefaces and bounded desktop/narrow geometry',async({page})=>{
  await sendState(page,{value:'**Bold text**\n\n- First item\n- Second item\n\n`inline code`'});
  const editor=page.getByRole('textbox',{name:'Document draft'});
  await expect(editor.locator('strong')).toHaveText('Bold text');await expect(editor.locator('li')).toHaveCount(2);await expect(editor.locator('code')).toHaveText('inline code');
  for(const width of [1200,390]){
    await page.setViewportSize({width,height:844});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    const geometry=await editor.evaluate(element=>({height:element.getBoundingClientRect().height,font:getComputedStyle(element).fontFamily}));
    expect(geometry.height).toBeGreaterThanOrEqual(72);expect(geometry.height).toBeLessThanOrEqual(320);expect(geometry.font).toContain('Excalifont');expect(geometry.font).toContain('Xiaolai');
  }
  await expect.poll(()=>page.evaluate(()=>window.__composerFixture.events.some(event=>event.type==='height' && (event.height ?? 0)>=72))).toBe(true);
});
test('a long draft scrolls inside a shrinking document and regains height when the viewport expands',async({page})=>{
  const editor=page.getByRole('textbox',{name:'Document draft'});
  await sendState(page,{value:Array.from({length:45},(_,i)=>`Paragraph ${i+1}: retain the original draft while the keyboard changes the viewport.`).join('\n\n')});
  for(const height of [144,320,144]){
    await page.setViewportSize({width:390,height});
    await expect.poll(()=>editor.evaluate(element=>element.clientHeight)).toBeLessThanOrEqual(height);
    await expect.poll(()=>editor.evaluate(element=>element.scrollHeight-element.clientHeight)).toBeGreaterThan(0);
    await expect.poll(()=>page.evaluate(()=>{
      const input=document.querySelector<HTMLElement>('.markdown-input-editor__content')!;
      return (window.__composerFixture.events.filter(event=>event.type==='height').at(-1)?.height ?? 0)>=input.scrollHeight;
    })).toBe(true);
    await expect(editor).toContainText('Paragraph 45:');
    expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);
  }
  await editor.fill('Short draft after resize');
  await expect.poll(()=>page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='height').at(-1)?.height ?? Infinity)).toBeLessThanOrEqual(144);
  expect(await page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='submit').length)).toBe(0);
});
test('a stale native echo preserves newer edits, while acknowledged prefill and clearing retain editor ownership',async({page})=>{
  const editor=page.getByRole('textbox',{name:'Document draft'});await editor.fill('Newer draft');
  await expect.poll(()=>editCount(page)).toBeGreaterThan(0);const count=await editCount(page);
  await sendState(page,{value:'Stale native value',eventCount:0});await expect(editor).toHaveText('Newer draft');
  await sendState(page,{value:'Acknowledged prefill',eventCount:count});await expect(editor).toHaveText('Acknowledged prefill');
  await sendState(page,{value:'',eventCount:count});await expect(editor).toHaveText('');
  expect(await editCount(page)).toBe(count);
});
test('active Skill-menu keys only report selection intent and preserve the original draft',async({page})=>{
  const editor=page.getByRole('textbox',{name:'Document draft'});
  await sendState(page,{value:'/compact',skillMenuOpen:true});
  for(const key of ['ArrowDown','ArrowUp','Enter','Tab','Escape'])await editor.press(key);
  await expect.poll(()=>page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='keydown').map(event=>(event as unknown as {key:string}).key))).toEqual(['ArrowDown','ArrowUp','Enter','Tab','Escape']);
  expect(await page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='submit').length)).toBe(0);
  await expect(editor).toHaveText('/compact');
  await sendState(page,{skillMenuOpen:false,eventCount:await editCount(page)});
  await editor.press('Enter');
  await expect.poll(()=>page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='submit').length)).toBe(1);
});
test('document identity, state revision, disabled feedback and theme survive local document changes',async({page})=>{
  const editor=page.getByRole('textbox',{name:'Document draft'});
  await sendState(page,{value:'Owned draft',revision:5});await expect(editor).toHaveText('Owned draft');
  await sendState(page,{value:'Old revision',revision:4});await expect(editor).toHaveText('Owned draft');
  const documentId=await page.evaluate(()=>window.__composerFixture.state.documentId);
  await sendState(page,{documentId:'old-document',value:'Wrong document',revision:6});await expect(editor).toHaveText('Owned draft');
  await sendState(page,{documentId,revision:7,disabled:true,theme:'dark'});
  await expect(editor).toHaveAttribute('contenteditable','false');await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.reload();await expect(editor).toHaveAttribute('contenteditable','true');
  const nextId=await page.evaluate(()=>window.__composerFixture.state.documentId);expect(nextId).not.toBe(documentId);
});
test('Enter delegates submit intent while Shift+Enter and IME keep the original keyboard rules',async({page})=>{
  const editor=page.getByRole('textbox',{name:'Document draft'});await editor.fill('Hello');await editor.press('Shift+Enter');await page.keyboard.type('Next line');
  expect(await page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='submit').length)).toBe(0);
  await editor.evaluate(element=>element.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true,data:'中'})));
  await editor.press('Enter');
  expect(await page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='submit').length)).toBe(0);
  await editor.evaluate(element=>element.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'中'})));
  await editor.press('Enter');
  await expect.poll(()=>page.evaluate(()=>window.__composerFixture.events.filter(event=>event.type==='submit').length)).toBe(1);
  await expect(editor).toContainText('Next line');
});
test('editor protocol rejects malformed events and accepts only the configured loopback document',()=>{
  for(const raw of ['null','[]','{}','not-json',JSON.stringify({type:'change',documentId:'d',eventCount:-1,value:'x'})])expect(readComposerEvent(raw)).toBeNull();
  expect(readComposerState({type:'state',documentId:'d',revision:1,eventCount:0,value:'x',placeholder:'p',ariaLabel:'a',disabled:false,theme:'system'})).not.toBeNull();
  expect(composerDocumentUrl('http://[::1]:5173')).toBe('http://[::1]:5173/native/composer');
  expect(()=>composerDocumentUrl('https://example.com')).toThrow('COMPOSER_ORIGIN_INVALID');
  expect(()=>composerDocumentUrl('http://user:password@localhost:5173')).toThrow('COMPOSER_ORIGIN_INVALID');
});
