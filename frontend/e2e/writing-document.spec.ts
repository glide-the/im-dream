// [Input] Current production Next local Writing route, original editor lifecycle and public session DTO fixtures.
// [Output] Original canvas editing/autosave, active-hide continuity and validated display-message evidence.
// [Pos] Provider-free DOM document qualification; native WebKit/cookies, real user data and Agent execution remain separate.
// Impact: synthetic editor session saves only. Project/Episode/Run/private publication/Hook and permissions remain unchanged.
import {expect,test,type Page} from '@playwright/test';
import {installReflectionFixtures} from './fixtures/reflectionsHarness';
const base=process.env.E2E_WEB_BASE;if(!base)throw Error('E2E_WEB_BASE_REQUIRED');
async function open(page:Page){
 const f=await installReflectionFixtures(page),saves:Record<string,any>[]=[];
 await page.route('**/api/sessions',async route=>{if(route.request().method()!=='POST')return route.fallback();saves.push(route.request().postDataJSON());await route.fulfill({json:{success:true}});});
 await page.addInitScript(()=>{const f=(window as any).__writingDocument={events:[],revision:0,documentId:''};f.send=(overrides:Record<string,unknown>={})=>{const state={type:'state',documentId:f.documentId,revision:++f.revision,active:true,theme:'light',language:'en',showEnergyBar:true,...overrides};window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(state)}));};(window as any).ReactNativeWebView={postMessage:(raw:string)=>{const event=JSON.parse(raw);f.events.push(event);if(event.type==='ready'){f.documentId=event.documentId;f.send();}}};});
 await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));await page.setViewportSize({width:390,height:844});await page.goto(base+'/native/writing');
 await expect(page.getByPlaceholder('Start writing...', {exact:true})).toBeVisible();
 const chooser=page.getByText('Happy',{exact:true});await expect(chooser).toBeVisible();await chooser.click();await expect(page.getByText('How are you feeling today?',{exact:true})).toBeHidden();
 return {f,saves};
}
test('original Writing canvas keeps editing, autosave and one editor instance across native active changes',async({page})=>{
 const {f,saves}=await open(page),editor=page.getByPlaceholder('Start writing...', {exact:true});await editor.fill('A quiet morning by the window.');await expect.poll(()=>saves.some(save=>save.editor_state?.cells?.some((cell:any)=>cell.type==='text'&&cell.content==='A quiet morning by the window.'))).toBe(true);
 const saved=saves.findLast(save=>save.editor_state?.cells?.some((cell:any)=>cell.content==='A quiet morning by the window.'));expect(saved?.session_id).toBeTruthy();
 await expect(page.getByRole('navigation')).toHaveCount(0);await expect(page.getByRole('button',{name:'More',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Calendar',exact:true})).toBeVisible();
 await editor.focus();await page.evaluate(()=>(window as any).__writingDocument.send({active:false}));await expect(editor).not.toBeFocused();await page.evaluate(()=>(window as any).__writingDocument.send({active:true}));await expect(editor).toHaveValue('A quiet morning by the window.');
 expect(await page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='ready').length)).toBe(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'/tmp/ink-more-app-navigation-20261029/writing-document.png'});expect(f.errors).toEqual([]);expect(f.createRequests).toEqual([]);
});
test('Writing display changes validate document identity and revision while retaining original content',async({page})=>{
 const {f}=await open(page),editor=page.getByPlaceholder('Start writing...', {exact:true});await editor.fill('Keep this original writing.');
 await page.evaluate(()=>(window as any).__writingDocument.send({theme:'dark',showEnergyBar:false}));await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await expect(page.getByText('Energy:',{exact:true})).toHaveCount(0);await expect(editor).toHaveValue('Keep this original writing.');
 await page.evaluate(()=>(window as any).__writingDocument.send({documentId:'another-document',theme:'light'}));await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.evaluate(()=>{const f=(window as any).__writingDocument;f.send({revision:0,theme:'light'});});await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.evaluate(()=>(window as any).__writingDocument.send({theme:'light',showEnergyBar:true}));await expect(page.locator('html')).toHaveAttribute('data-theme','light');await expect(page.getByText('Energy:',{exact:true})).toBeVisible();await expect(editor).toHaveValue('Keep this original writing.');expect(f.errors).toEqual([]);expect(f.createRequests).toEqual([]);
});
