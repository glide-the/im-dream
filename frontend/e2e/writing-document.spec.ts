// [Input] Current production Next local Writing route, original editor lifecycle and public session DTO fixtures.
// [Output] Original canvas editing/autosave, active-hide continuity and validated display-message evidence.
// [Pos] Provider-free DOM document qualification; native WebKit/cookies, real user data and Agent execution remain separate.
// Impact: synthetic editor session saves only. Project/Episode/Run/private publication/Hook and permissions remain unchanged.
// [Sync] 2026-11-01: qualify visible A/B/A card navigation, touch entry and saved Session-bound context replies against the original DOM editor.
import {expect,test,type Page} from '@playwright/test';
import {installReflectionFixtures} from './fixtures/reflectionsHarness';
const base=process.env.E2E_WEB_BASE;if(!base)throw Error('E2E_WEB_BASE_REQUIRED');
async function open(page:Page,options:{prepare?:()=>Promise<void>;chooseEmotion?:boolean;onSave?:(body:Record<string,any>)=>void}={}){
 const f=await installReflectionFixtures(page),saves:Record<string,any>[]=[];
 await page.route('**/api/sessions',async route=>{if(route.request().method()!=='POST')return route.fallback();const body=route.request().postDataJSON();saves.push(body);options.onSave?.(body);await route.fulfill({json:{success:true}});});
 await options.prepare?.();
 await page.addInitScript(()=>{const f=(window as any).__writingDocument={events:[],revision:0,documentId:''};f.send=(overrides:Record<string,unknown>={})=>{const state={type:'state',documentId:f.documentId,revision:++f.revision,active:true,theme:'light',language:'en',showEnergyBar:true,...overrides};window.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(state)}));};(window as any).ReactNativeWebView={postMessage:(raw:string)=>{const event=JSON.parse(raw);f.events.push(event);if(event.type==='ready'){f.documentId=event.documentId;f.send();}}};});
 await page.clock.setFixedTime(new Date('2026-09-28T12:00:00Z'));await page.setViewportSize({width:390,height:844});await page.goto(base+'/native/writing');
 await expect(page.getByPlaceholder('Start writing...', {exact:true}).first()).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='chooser-view').at(-1)?.loading)).toBe(false);
 if(options.chooseEmotion!==false){const chooser=page.getByText('Happy',{exact:true});await expect(chooser).toBeVisible();await chooser.click();await expect(page.getByText('How are you feeling today?',{exact:true})).toBeHidden();}
 return {f,saves};
}
test('original Writing canvas keeps editing, autosave and one editor instance across native active changes',async({page})=>{
 const {f,saves}=await open(page),editor=page.getByPlaceholder('Start writing...', {exact:true});await editor.fill('A quiet morning by the window.');await expect.poll(()=>saves.some(save=>save.editor_state?.cells?.some((cell:any)=>cell.type==='text'&&cell.content==='A quiet morning by the window.'))).toBe(true);
 const saved=saves.findLast(save=>save.editor_state?.cells?.some((cell:any)=>cell.content==='A quiet morning by the window.'));expect(saved?.session_id).toBeTruthy();
 await expect(page.getByRole('navigation')).toHaveCount(0);await expect(page.getByRole('button',{name:'More',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Calendar',exact:true})).toBeVisible();
 await editor.focus();await page.evaluate(()=>(window as any).__writingDocument.send({active:false}));await expect(editor).not.toBeFocused();await page.evaluate(()=>(window as any).__writingDocument.send({active:true}));await expect(editor).toHaveValue('A quiet morning by the window.');
 expect(await page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='ready').length)).toBe(1);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'/tmp/ink-more-app-navigation-20261029/writing-document.png'});expect(f.errors).toEqual([]);expect(f.createRequests).toEqual([]);
});

test.describe('linked Writing context',()=>{
 test.use({hasTouch:true,isMobile:true});
 async function linked(page:Page){
  const make=(id:string,threadId:string)=>({id,name:id,first_line:id,date_key:'2026-09-28',created_at:'2026-09-28T11:00:00Z',updated_at:'2026-09-28T11:00:00Z',labels:[],editor_state:{id,createdAt:'2026-09-28T11:00:00Z',selectedState:'happy',commentors:[],tasks:[],weightPath:[],overlappedPhrases:[],notFoundPhrases:[],cells:[{id:id+'-text',type:'text',content:'Original '+id},{id:id+'-widget',type:'widget',widgetType:'chat',data:{id:id+'-widget',threadId,voiceName:'fixture',voiceConfig:{name:'Fixture Agent',tagline:'Fixture',icon:'brain',color:'blue'},messages:[],createdAt:1}}]}});
  const notes:Record<string,any>={'note-A':make('note-A','thread-A'),'note-B':make('note-B','thread-B')};
  const result=await open(page,{chooseEmotion:false,onSave:body=>{if(notes[body.session_id])notes[body.session_id].editor_state=body.editor_state;},prepare:async()=>{
   await page.route(/\/api\/sessions(?:\?|$)/,async route=>route.request().method()==='GET'?route.fulfill({json:{sessions:Object.values(notes).map(note=>({...note,editor_state:null}))}}):route.fallback());
   await page.route(/\/api\/sessions\/note-[AB](?:\?|$)/,route=>route.fulfill({json:notes[new URL(route.request().url()).pathname.split('/').at(-1)!]}));
  }});
  const select=async(id:string)=>{await page.getByRole('button',{name:'Calendar',exact:true}).click();await page.getByRole('tab',{name:'Diary',exact:true}).click();await page.getByRole('button',{name:'Open: '+id,exact:true}).click();await expect(page.locator('.calendar-popup')).toHaveCount(0);await expect(page.locator('textarea.writing-prose').first()).toHaveValue(notes[id].editor_state.cells[0].content);};
  return {...result,notes,select};
 }
 test('touch A/B/A opens each saved card and prepares only that note after persistence',async({page})=>{
  const f=await linked(page);
  for(const [index,id] of ['note-A','note-B','note-A'].entries()){
   await f.select(id);
   const editor=page.locator('textarea.writing-prose').first();await editor.fill('Updated '+id+' '+index);
   const button=page.getByRole('button',{name:'Chat →',exact:true});
   expect(await button.evaluate(el=>({opacity:getComputedStyle(el).opacity,pointerEvents:getComputedStyle(el).pointerEvents}))).toEqual({opacity:'1',pointerEvents:'auto'});
   await button.tap();
   await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='open-thread').length)).toBe(index+1);
   const opened=await page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='open-thread').at(-1));
   expect(opened).toMatchObject({threadId:id==='note-A'?'thread-A':'thread-B',editorSessionId:id});
   await page.evaluate(({id,index})=>(window as any).__writingDocument.send({contextRequest:{requestId:'send-'+index,sessionId:id}}),{id,index});
   await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='chat-context').length)).toBe(index+1);
   const prepared=await page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='chat-context').at(-1));
   expect(prepared).toMatchObject({sessionId:id,requestId:'send-'+index,editorState:{id,cells:expect.any(Array)}});
   expect(prepared.editorState.cells[0].content).toBe('Updated '+id+' '+index);
   expect(f.saves.at(-1)).toMatchObject({session_id:id,editor_state:{id}});
  }
  expect(f.f.createRequests).toEqual([]);
 });
 test('a stale note binding and failed save return errors without exposing a context snapshot',async({page})=>{
  const f=await linked(page);await f.select('note-B');
  await page.evaluate(()=>(window as any).__writingDocument.send({contextRequest:{requestId:'stale-A',sessionId:'note-A'}}));
  await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='chat-context-error').length)).toBe(1);
  expect(await page.evaluate(()=>(window as any).__writingDocument.events.find((event:any)=>event.requestId==='stale-A'))).toMatchObject({type:'chat-context-error',code:'session-changed'});
  await page.locator('textarea.writing-prose').first().fill('Keep note B after save failure');
  f.f.allowHttpError(503,'/api/sessions');
  await page.route('**/api/sessions',route=>route.request().method()==='POST'?route.fulfill({status:503,json:{detail:'Fixture save failure'}}):route.fallback());
  await page.evaluate(()=>(window as any).__writingDocument.send({contextRequest:{requestId:'failed-B',sessionId:'note-B'}}));
  await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='chat-context-error').length)).toBe(2);
  expect(await page.evaluate(()=>(window as any).__writingDocument.events.find((event:any)=>event.requestId==='failed-B'))).toMatchObject({type:'chat-context-error',code:'save-failed'});
  expect(await page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='chat-context'))).toEqual([]);
  await expect(page.locator('textarea.writing-prose').first()).toHaveValue('Keep note B after save failure');expect(f.f.createRequests).toEqual([]);
 });
 test('a late save of A cannot return A context after selecting B',async({page})=>{
  const f=await linked(page);await f.select('note-A');await page.locator('textarea.writing-prose').first().fill('Save A while its context is pending');
  let completeSave:(()=>Promise<void>)|undefined;
  await page.route('**/api/sessions',async route=>{
   if(route.request().method()!=='POST')return route.fallback();
   const body=route.request().postDataJSON();expect(body.session_id).toBe('note-A');
   completeSave=()=>route.fulfill({json:{success:true}});
  });
  await page.evaluate(()=>(window as any).__writingDocument.send({contextRequest:{requestId:'late-save-A',sessionId:'note-A'}}));
  await expect.poll(()=>Boolean(completeSave)).toBe(true);
  await f.select('note-B');await completeSave!();
  await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.requestId==='late-save-A').length)).toBe(1);
  const result=await page.evaluate(()=>(window as any).__writingDocument.events.find((event:any)=>event.requestId==='late-save-A'));
  expect(result).toMatchObject({type:'chat-context-error',code:'session-changed'});
  await expect(page.locator('textarea.writing-prose').first()).toHaveValue('Original note-B');expect(f.f.createRequests).toEqual([]);
 });
});
test('Writing display changes validate document identity and revision while retaining original content',async({page})=>{
 const {f}=await open(page),editor=page.getByPlaceholder('Start writing...', {exact:true});await editor.fill('Keep this original writing.');
 await page.evaluate(()=>(window as any).__writingDocument.send({theme:'dark',showEnergyBar:false}));await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await expect(page.getByText('Energy:',{exact:true})).toHaveCount(0);await expect(editor).toHaveValue('Keep this original writing.');
 await page.evaluate(()=>(window as any).__writingDocument.send({documentId:'another-document',theme:'light'}));await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.evaluate(()=>{const f=(window as any).__writingDocument;f.send({revision:0,theme:'light'});});await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.evaluate(()=>(window as any).__writingDocument.send({theme:'light',showEnergyBar:true}));await expect(page.locator('html')).toHaveAttribute('data-theme','light');await expect(page.getByText('Energy:',{exact:true})).toBeVisible();await expect(editor).toHaveValue('Keep this original writing.');expect(f.errors).toEqual([]);expect(f.createRequests).toEqual([]);
});

test('the original Writing document dispatches a matched native note jump once after the canvas is mounted',async({page})=>{
 const {f,saves}=await open(page),editor=page.getByPlaceholder('Start writing...', {exact:true});await editor.fill('Keep the current note and its identity.');
 await expect.poll(()=>saves.some(save=>save.editor_state?.cells?.some((cell:any)=>cell.content==='Keep the current note and its identity.'))).toBe(true);
 const saved=saves.findLast(save=>save.editor_state?.cells?.some((cell:any)=>cell.content==='Keep the current note and its identity.'));
 const cell=saved!.editor_state.cells.find((cell:any)=>cell.content==='Keep the current note and its identity.');
 await page.evaluate(()=>{(window as any).__writingJumps=[];window.addEventListener('editor:jump-to-cell',event=>(window as any).__writingJumps.push((event as CustomEvent).detail));});
 const detail={cellId:cell.id,editorSessionId:saved!.session_id};
 await page.evaluate(detail=>(window as any).__writingDocument.send({editorJump:{nonce:1,detail}}),detail);
 await expect.poll(()=>page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='editor-jump-dispatched').length)).toBe(1);
 expect(await page.evaluate(()=>(window as any).__writingJumps)).toEqual([detail]);
 await page.evaluate(detail=>(window as any).__writingDocument.send({editorJump:{nonce:1,detail}}),detail);
 await expect(editor).toHaveValue('Keep the current note and its identity.');
 expect(await page.evaluate(()=>(window as any).__writingDocument.events.filter((event:any)=>event.type==='editor-jump-dispatched').length)).toBe(1);expect(f.errors).toEqual([]);expect(f.createRequests).toEqual([]);
});
