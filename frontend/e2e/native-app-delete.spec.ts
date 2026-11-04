// [Input] Actual App deletion callback, native history/session/activity hooks and explicit HTTP/Alert/visual-leaf fixtures.
// [Output] Confirmation, cancellation, single DELETE, failure retry, selection race, account retirement and browser-reopen assertions.
// [Pos] APP-01 provider-free technical journey; acceptance execution is coordinated by the parent task.
// [Sync] 2026-11-03: use positive decimal fixture account IDs required by the production session DTO.
// [Sync] 2026-11-02: isolate the Vite cache, retain browser diagnostics and check completed UI state after a delayed deletion.
// Project/Episode/canonical artifacts/.dream/after-turn Hook are out of scope.
// History DELETE DTO/CSRF and Thread selection remain production-owned; only synthetic fixture rows may be deleted.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {createServer as netServer} from 'node:net';
import {fileURLToPath} from 'node:url';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

test.use({channel:'chrome'});
const native=`
export * from 'react-native-web';
export const NativeModules={InkRuntime:{}};
export const Settings={get(){return undefined;},set(){}};
export const AppState={currentState:'active',addEventListener(){return {remove(){}};}};
export const BackHandler={addEventListener(){return {remove(){}};}};
export const Alert={alert(title,message,buttons,options){
 const f=window.__appDeleteFixture,panel=document.createElement('div');
 panel.setAttribute('role','alertdialog');panel.setAttribute('aria-label',title);
 Object.assign(panel.style,{position:'fixed',inset:'16px',maxHeight:'80vh',overflow:'auto',zIndex:10000,background:'white',padding:'16px',border:'1px solid black'});
 const heading=document.createElement('h2'),body=document.createElement('p');heading.textContent=title;body.textContent=message;panel.append(heading,body);
 const close=()=>{panel.remove();document.removeEventListener('keydown',key);};
 const key=event=>{if(event.key==='Escape'){close();options?.onDismiss?.();}};
 document.addEventListener('keydown',key);
 buttons.forEach(button=>{const element=document.createElement('button');element.textContent=button.text;element.onclick=()=>{close();button.onPress?.();};panel.append(element);});
 f.alerts.push({title,message,buttons,options});document.body.append(panel);
}};`;
const empty=`export default function Leaf(){return null;}`;
const stubs:Record<string,string>={
  transport:`export const clientFetch=(...args)=>window.fetch(...args);export const openResponse=()=>{throw Error('UNEXPECTED_FIXTURE_STREAM');};`,
  runtime:`export const BackendRuntimeManager={ensureStarted:async()=>({localWebOrigin:'http://fixture.invalid'}),recordError(){}};`,
  frame:`import React from 'react';import {View} from 'react-native';export default function Frame({children}){return <View style={{flex:1}}>{children}</View>;}`,
  gate:`import React,{useState} from 'react';export default function Gate({children}){const [id,setId]=useState('910000001');window.__appDeleteFixture.switchAccount=()=>setId('910000002');return <><div data-testid="fixture-account">{id}</div>{children(async()=>{},async()=>{window.__appDeleteFixture.sessionRefreshes++;},{id})}</>;}`,
  colors:`import {inkColors} from '/src/components/inkColors.ts';export default function colors(){return inkColors('light',false);}`,
  files:`export const createWorkspaceResources=()=>({});export const createMessageFileResources=()=>({});`,
  upload:`export const releaseNativeFiles=()=>{};`,
  close:`export const closeToolResultDocuments=async()=>{window.__appDeleteFixture.closures++;};`,
  task:`export default function activity(){return {data:{links:{}}};}`,
  top:`import React from 'react';import {View,Pressable,Text} from 'react-native';export default function Top({onToggleActivity,onNewChat}){return <View style={{flexDirection:'row'}}><Pressable accessibilityRole="button" onPress={onToggleActivity}><Text>Activity fixture</Text></Pressable><Pressable accessibilityRole="button" onPress={onNewChat}><Text>New fixture Chat</Text></Pressable></View>;}`,
  composer:`import React,{forwardRef,useState} from 'react';import {View,Text,TextInput} from 'react-native';export default forwardRef(function Composer({threadId},ref){const [draft,setDraft]=useState('');return <View><Text testID="fixture-selected-thread">{threadId||'none'}</Text><TextInput accessibilityLabel="Fixture unsent draft" value={draft} onChangeText={setDraft}/></View>;});`,
  messages:`import React from 'react';import {Text} from 'react-native';export default function Messages({messages}){return <Text>{messages.flatMap(message=>message.parts.filter(part=>part.type==='text').map(part=>part.text)).join(' ')}</Text>;}`,
  badge:`export const ChatAgentBadge=()=>null;export default ()=>null;`,
};
const keep=['useNativeChatSetup.native','useNativeChatThread.native','useNativeChatHistory.native','useNativeActivitySidebarData.native','ChatPage.native','ActivitySidebar.native','ChatHistorySearch.native','chatLandingActions','chatRuntimeState','threadInputQueue','nativeChatRecovery.native','InkLabel.native'];
const leaf:Record<string,string>={'SessionGate':'gate','ScreenFrame':'frame','useInkColors.native':'colors','workspaceFiles.native':'files','fileUpload.native':'upload','ToolResultSurface.native':'close','useNativeTaskActivity.native':'task','ChatTopActions.native':'top','AIInputDock.native':'composer','ChatMessageList.native':'messages','PluginReceiptBadge.native':'badge'};
const emptyLeaves=['ToolConfirmationDock.native','DeckChatSelector.native','ScheduledTaskDetailSidebar.native','WorkspaceFilePreview.native','ChatShareSurface.native','FileSidebar.native','ThreadInputQueueCard.native','DeckManager.native','StoryWorkspaceSettingsPage.native','MoreNavigator.native','SketchInputSurface.native','ToolMessagePart.native','FileMessagePart.native','PlanPanel.native'];
let server:Awaited<ReturnType<typeof createServer>>,base:string,cacheRoot:string;
const diagnostics=new WeakMap<Page,{console:string[];page:string[];requests:string[]}>();
test.beforeAll(async()=>{
  const root=fileURLToPath(new URL('../',import.meta.url));
  cacheRoot=await mkdtemp(join(tmpdir(),'ink-app-01-delete-'));
  const port=await new Promise<number>((resolve,reject)=>{const probe=netServer();probe.once('error',reject);probe.listen(0,'127.0.0.1',()=>{const value=probe.address();if(!value||typeof value==='string')return reject(Error('PORT'));probe.close(error=>error?reject(error):resolve(value.port));});});
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:join(cacheRoot,'vite'),server:{host:'127.0.0.1',port,strictPort:true},plugins:[{
    name:'app-01-delete-fixture',enforce:'pre',
    resolveId(id,importer){
      if(id==='react-native')return '\0app-delete-native';
      if(/\/platform\/transport(?:\.native)?$/.test(id))return '\0app-delete-transport';
      if(id.endsWith('/runtime/BackendRuntimeManager'))return '\0app-delete-runtime';
      if(id.endsWith('/useInkColors.native'))return '\0app-delete-colors';
      if(importer?.split('?')[0].endsWith('/src/App.tsx')&&id.startsWith('.')){
        const name=id.split('/').at(-1)!;
        if(keep.includes(name))return;
        if(name==='externalLinks.native')return '\0app-delete-external';
        if(name==='deckReadApi')return '\0app-delete-deck';
        if(leaf[name])return '\0app-delete-'+leaf[name];
        if(emptyLeaves.includes(name))return '\0app-delete-empty';
      }
    },
    async load(id){
      const key=id.replace('\0app-delete-','');
      if(id==='\0app-delete-native')return transformWithEsbuild(native,'app-delete-native.tsx',{loader:'tsx',jsx:'automatic'});
      if(!id.startsWith('\0app-delete-'))return;
      const code=key==='external'?'export const openExternalLink=async()=>{};':key==='deck'?'export const getDeck=async()=>{throw Error("UNEXPECTED_FIXTURE_DECK");};':stubs[key]||empty;
      return transformWithEsbuild(code,'app-delete-'+key+'.tsx',{loader:'tsx',jsx:'automatic'});
    },
    configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/app-01-delete')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/app-01-delete','<html><head><link rel="icon" href="data:,"><style>html,body,#root{margin:0;height:100%}</style></head><body><div id="root"></div><script type="module" src="/e2e/native/app-delete-fixture.tsx"></script></body></html>'));});},
  }]});await server.listen();base='http://127.0.0.1:'+port+'/app-01-delete';
});
test.afterAll(async()=>{try{await server?.close();}finally{if(cacheRoot)await rm(cacheRoot,{recursive:true,force:true});}});
test.beforeEach(async({page})=>{
  const observed={console:[] as string[],page:[] as string[],requests:[] as string[]};diagnostics.set(page,observed);
  page.on('console',message=>{if(message.type()==='error')observed.console.push(message.text());});
  page.on('pageerror',error=>observed.page.push(error.message));
  page.on('requestfailed',request=>{if(new URL(request.url()).origin===new URL(base).origin)observed.requests.push(request.method()+' '+request.url()+' '+request.failure()?.errorText);});
  await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
  await page.goto(base);await expect(page.getByRole('button',{name:'Mountain walk notes',exact:true})).toBeVisible();
});
test.afterEach(async({page},testInfo)=>{
  const observed=diagnostics.get(page);
  await testInfo.attach('app-delete-browser-diagnostics',{body:JSON.stringify(observed,null,2),contentType:'application/json'});
  expect(observed).toEqual({console:[],page:[],requests:[]});
  expect(await page.evaluate(()=>(window as any).__appDeleteFixture?.failClosed)).toEqual([]);
});
async function writes(page:Page){return page.evaluate(()=>(window as any).__appDeleteFixture.calls.filter((call:any)=>call.method!=='GET'));}
const remove=(page:Page,title='Mountain walk notes')=>page.getByRole('button',{name:'Delete conversation: '+title,exact:true}).last();

test('list confirmation names the target; cancel and dismissal perform zero DELETE',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.getByLabel('Fixture unsent draft').fill('Keep the unsubmitted text');
  await remove(page).click();const dialog=page.getByRole('alertdialog');await expect(dialog).toContainText('Delete “Mountain walk notes”?');await expect(dialog).toContainText('permanently');
  await dialog.getByRole('button',{name:'Cancel',exact:true}).click();expect(await writes(page)).toEqual([]);await expect(page.getByLabel('Fixture unsent draft')).toHaveValue('Keep the unsubmitted text');
  await remove(page).click();await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);expect(await writes(page)).toEqual([]);
});
test('confirmed deletion is single, preserves other rows and survives a browser reopen',async({page})=>{
  await remove(page).click();await page.getByRole('alertdialog').getByRole('button',{name:'Delete',exact:true}).click();
  await expect(page.getByRole('button',{name:'Mountain walk notes',exact:true})).toHaveCount(0);
  await page.evaluate(()=>(window as any).__appDeleteFixture.alerts[0].buttons.find((button:any)=>button.style==='destructive').onPress());
  expect(await writes(page)).toHaveLength(1);expect((await writes(page))[0].path).toBe('/api/claude-agent/threads/fixture-delete-a');expect((await writes(page))[0].headers['x-ink-csrf']).toHaveLength(43);
  await expect(page.getByRole('button',{name:'Garden reading notes',exact:true})).toBeVisible();await page.reload();
  await expect(page.getByRole('button',{name:'Garden reading notes',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Mountain walk notes',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Garden reading notes',exact:true}).click();await expect(page.getByText('Saved body: Garden reading notes',{exact:true})).toBeVisible();
});
test('detail activity keeps the current Thread on failure, then clears only that Thread after confirmed retry',async({page})=>{
  await page.getByRole('button',{name:'Mountain walk notes',exact:true}).click();await expect(page.getByText('Saved body: Mountain walk notes',{exact:true})).toBeVisible();
  await page.getByLabel('Fixture unsent draft').fill('Retain on failed deletion');await page.getByRole('button',{name:'Activity fixture',exact:true}).click();
  await page.evaluate(()=>(window as any).__appDeleteFixture.failDelete=true);await remove(page).click();await page.getByRole('alertdialog').getByRole('button',{name:'Delete',exact:true}).click();
  await expect(page.getByText('The conversation could not be deleted.',{exact:true})).toBeVisible();await expect(page.getByTestId('fixture-selected-thread')).toHaveText('fixture-delete-a');
  await page.getByRole('button',{name:'Close activity',exact:true}).click();await expect(page.getByLabel('Fixture unsent draft')).toHaveValue('Retain on failed deletion');
  await page.getByRole('button',{name:'Activity fixture',exact:true}).click();await page.evaluate(()=>(window as any).__appDeleteFixture.failDelete=false);await remove(page).click();await page.getByRole('alertdialog').getByRole('button',{name:'Delete',exact:true}).click();
  await expect(page.getByTestId('fixture-selected-thread')).toHaveText('none');expect(await writes(page)).toHaveLength(2);
});
test('a delayed DELETE preserves the subsequently opened Thread',async({page})=>{
  await page.getByRole('button',{name:'Mountain walk notes',exact:true}).click();await expect(page.getByText('Saved body: Mountain walk notes',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Activity fixture',exact:true}).click();await page.evaluate(()=>(window as any).__appDeleteFixture.holdDelete=true);
  await remove(page).click();await page.getByRole('alertdialog').getByRole('button',{name:'Delete',exact:true}).click();await expect.poll(async()=>(await writes(page)).length).toBe(1);
  await page.getByRole('button',{name:'Garden reading notes',exact:true}).last().click();await expect(page.getByText('Saved body: Garden reading notes',{exact:true})).toBeVisible();
  await page.evaluate(()=>(window as any).__appDeleteFixture.pending[0]());await expect.poll(()=>page.evaluate(()=>(window as any).__appDeleteFixture.rows.length)).toBe(2);
  await page.getByRole('button',{name:'Activity fixture',exact:true}).click();await expect(remove(page)).toHaveCount(0);
  await page.getByRole('button',{name:'Close activity',exact:true}).click();
  await expect(page.getByTestId('fixture-selected-thread')).toHaveText('fixture-delete-b');await expect(page.getByText('Saved body: Garden reading notes',{exact:true})).toBeVisible();
});
test('permission failures retain the target and HTTP 401 requests the original session refresh',async({page})=>{
  for(const status of [403,401]){
    await page.evaluate(status=>(window as any).__appDeleteFixture.deleteStatus=status,status);
    await remove(page).click();await page.getByRole('alertdialog').getByRole('button',{name:'Delete',exact:true}).click();
    await expect(page.getByText('The conversation could not be deleted.',{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Mountain walk notes',exact:true})).toBeVisible();await expect(remove(page)).toBeEnabled();
  }
  expect(await writes(page)).toHaveLength(2);
  expect(await page.evaluate(()=>(window as any).__appDeleteFixture.sessionRefreshes)).toBe(1);
  expect((await writes(page)).every((call:any)=>call.headers['x-ink-csrf']?.length===43&&call.headers.authorization===undefined)).toBe(true);
});
test('untitled confirmation uses the existing creation date, and account retirement prevents the old action',async({page})=>{
  await remove(page,'New conversation').click();await expect(page.getByRole('alertdialog')).toContainText('New conversation ·');
  await page.evaluate(()=>(window as any).__appDeleteFixture.switchAccount());await expect(page.getByTestId('fixture-account')).toHaveText('910000002');
  await page.getByRole('alertdialog').getByRole('button',{name:'Delete',exact:true}).click();expect(await writes(page)).toEqual([]);
});
