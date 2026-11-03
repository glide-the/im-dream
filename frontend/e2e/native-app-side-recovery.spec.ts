// [Input] Actual native App composition, original Chat/composer/recovery modules and explicit visual/HTTP boundaries.
// [Output] Main-owned side restoration, Writing send protection, source return and pointer retirement journey specifications.
// [Pos] APP-04 isolated technical fixture; authored while all mechanical validation is paused, never executed here.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

test.use({channel:'chrome'});
const empty='export default function Leaf(){return null;}';
const stubs:Record<string,string>={
 transport:`export const clientFetch=(...args)=>window.fetch(...args);export const openResponse=(...args)=>window.__sideRecoveryFixture.stream(...args);`,
 frame:`import React from 'react';export default function Frame({children}){return <div>{children}</div>;}`,
 gate:`import React from 'react';export default function Gate({children}){return children(async()=>{},async()=>{window.__sideRecoveryFixture.sessionRefreshes++;},{id:'owner-A'});}`,
 colors:`import {inkColors} from '/src/components/inkColors.ts';export default function colors(){return inkColors('light',false);}export const useNativeThemeMode=()=> 'light';`,
 setup:`export default function setup(){return {origin:'http://fixture.invalid',decks:[],configLoaded:true,config:{workspace_enabled:false,im_full_access_enabled:false},loading:false,error:null,revision:0,retry(){},refreshDecks(){},refreshConfig:async()=>{}};}`,
 history:`export default function history(){return {threads:[],loading:false,error:null,hasMore:false,reload:async()=>{},remove:async()=>false,search:async()=>{},loadMore:async()=>{}};}`,
 activity:`export const nativeActivityFilters={};export default ()=>null;`,
 activityData:`export default function data(){return {chat:{data:[]},removeChat(){}};}`,
 task:`export default function task(){return {data:{links:{}}};}`,
 files:`export const createWorkspaceResources=()=>({});export const createMessageFileResources=()=>({});`,
 upload:`export const releaseNativeFiles=()=>{};`,
 attachments:`export default function files(){return {releasePreview(){},chooseFiles:async()=>{},addFiles:async()=>[],deleteFile(){},error:null};}`,
 close:`export const closeToolResultDocuments=async()=>{};`,
 editor:`import React from 'react';export default function Editor({value,onChange,disabled}){return <textarea aria-label="Native draft" value={value} onChange={event=>onChange(event.target.value)} disabled={disabled}/>;}`,
 skills:`export default function skills(){return {matches:[],keyDown:()=>false,resetDismissal(){}};}`,
 controls:`import React from 'react';export default function Controls({draft,disabled}){return <button disabled={disabled||!draft.canSend} onClick={draft.handleSend}>Send fixture input</button>;}`,
 page:`import React from 'react';export default function Page({conversation,composer}){return <>{conversation}{composer}</>;}`,
 messages:`import React from 'react';export default function Messages({messages}){return <div>{messages.flatMap(message=>message.parts.filter(part=>part.type==='text').map(part=>part.text)).join(' ')}</div>;}`,
 badge:`export const ChatAgentBadge=()=>null;export default ()=>null;`,
 more:`import React from 'react';export default function More({editorJump,onOpenThread}){return <><output aria-label="Original writing target">{JSON.stringify(editorJump?.detail??null)}</output><button onClick={()=>onOpenThread('side-thread',{sessionId:'writing-session',prepareEditorState:async()=>{window.__sideRecoveryFixture.preparations++;return window.__sideRecoveryFixture.source.editor_state;}})}>Open original Writing conversation</button></>;}`,
};
const leaves:Record<string,string>={SessionGate:'gate',ScreenFrame:'frame','useInkColors.native':'colors','useNativeChatSetup.native':'setup','useNativeChatHistory.native':'history','useNativeActivitySidebarData.native':'activityData','useNativeTaskActivity.native':'task','ActivitySidebar.native':'activity','workspaceFiles.native':'files','fileUpload.native':'upload','ToolResultSurface.native':'close','ChatPage.native':'page','ChatMessageList.native':'messages','PluginReceiptBadge.native':'badge','MoreNavigator.native':'more'};
const emptyLeaves=new Set(['ToolConfirmationDock.native','DeckChatSelector.native','ScheduledTaskDetailSidebar.native','WorkspaceFilePreview.native','ChatShareSurface.native','FileSidebar.native','ThreadInputQueueCard.native','DeckManager.native','StoryWorkspaceSettingsPage.native','SketchInputSurface.native','ToolMessagePart.native','FileMessagePart.native','PlanPanel.native','ChatTopActions.native','ChatHistorySearch.native']);
const entry=String.raw`
import React from 'react';import {createRoot} from 'react-dom/client';import App from '/src/App.tsx';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
await i18n.changeLanguage('en');await loadBrowserSession(async()=>Response.json({user:{id:'owner-A',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const key='app04-side-service',read=()=>JSON.parse(sessionStorage.getItem(key)||'null')??{calls:[],messages:{}},save=value=>sessionStorage.setItem(key,JSON.stringify(value));
const f=window.__sideRecoveryFixture={sessionRefreshes:0,preparations:0,rejectSource:false,holdSource:false,pendingSource:[],source:{id:'writing-session',editor_state:{id:'writing-session',writingThreadId:'side-thread',cells:[{id:'writing-cell',type:'text',content:'Saved source text'}],commentors:[],tasks:[],weightPath:[],overlappedPhrases:[],notFoundPhrases:[]}},read,
 settings:()=>{const raw=JSON.parse(localStorage.getItem('ink-appearance-fixture:ink-native-chat-recovery')||'null');return typeof raw==='string'?JSON.parse(raw):null;}};
const log=(path,method,body)=>{const value=read();value.calls.push({path,method,body});save(value);};
window.fetch=async(input,init={})=>{
 const url=new URL(String(input),'http://fixture.invalid'),path=url.pathname,method=init.method||'GET';log(path,method,init.body?JSON.parse(init.body):null);
 if(path==='/api/sessions/writing-session'){
  const reply=()=>f.rejectSource?Response.json({detail:'Fixture source denied'},{status:403}):Response.json(f.source);
  return f.holdSource?new Promise(resolve=>f.pendingSource.push(()=>resolve(reply()))):reply();
 }
 const match=/^/api/claude-agent/threads/([^/]+)/(messages|status|inputs)$/.exec(path);
 if(match){const id=decodeURIComponent(match[1]),value=read(),messages=value.messages[id]??[{id:id+'-saved',role:'assistant',parts:[{type:'text',text:'Saved '+id+' reply'}],metadata:{turnStatus:'completed'},created_at:'2026-11-02T00:00:00Z'}];
  if(match[2]==='messages')return Response.json({thread:{id,title:id,deck_id:null,voice_id:null,created_at:'2026-11-02T00:00:00Z',updated_at:'2026-11-02T00:00:00Z'},messages,has_more:false,next_cursor:null,latest_message_id:messages.at(-1)?.id??null,unchanged:false});
  if(match[2]==='status')return Response.json({running:false,lifecycle:'not_found',turn_count:1,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
  if(match[2]==='inputs')return Response.json({entries:[],local_owner:false});
 }
 throw Error('UNEXPECTED_APP04_SIDE_REQUEST '+method+' '+path);
};
f.stream=async(path,init={})=>{
 const body=JSON.parse(init.body);log(path,init.method,body);const value=read();value.messages[body.id]=[body.message,{id:'fixture-new-reply',role:'assistant',parts:[{type:'text',text:'Saved follow-up reply'}],metadata:{turnStatus:'completed'}}];save(value);
 return {status:200,cancel(){},chunks:(async function*(){yield 'data: '+JSON.stringify({type:'finish',finishReason:'stop'})+String.fromCharCode(10,10);})()};
};
createRoot(document.getElementById('root')).render(<App/>);
`;

let server:Awaited<ReturnType<typeof createServer>>,base:string,cacheRoot:string;
test.beforeAll(async()=>{
 const root=fileURLToPath(new URL('../',import.meta.url));cacheRoot=await mkdtemp(join(tmpdir(),'ink-app04-side-recovery-'));
 server=await createServer({root,configFile:false,logLevel:'silent',define:{global:'globalThis'},cacheDir:join(cacheRoot,'vite'),server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{
  name:'app04-original-side-composition',enforce:'pre',resolveId(id,importer){
   if(id==='react-native')return root+'e2e/native/chat-recovery-platform-web-boundary.ts';
   if(/\/platform\/transport(?:\.native)?$/.test(id))return '\0app04-side-transport';
   if(id.endsWith('/useInkColors.native'))return '\0app04-side-colors';
   if(id==='/app04-side.tsx')return '\0app04-side-entry';
   const name=id.split('/').at(-1)!;
   if(importer?.split('?')[0].endsWith('/src/App.tsx')&&id.startsWith('.')){
    if(leaves[name])return '\0app04-side-'+leaves[name];
    if(emptyLeaves.has(name))return '\0app04-side-empty';
    if(name==='externalLinks.native')return '\0app04-side-external';
    if(name==='deckReadApi')return '\0app04-side-deck';
   }
   if(importer?.split('?')[0].endsWith('/AIInputDock.native.tsx')){
    const map:Record<string,string>={MarkdownInputEditor:'editor','useFileAttachments.native':'attachments',useComposerSkills:'skills','ComposerSkillMenu.native':'empty','AIInputDockControls.native':'controls'};
    if(map[name])return '\0app04-side-'+map[name];
   }
  },async load(id){
   if(!id.startsWith('\0app04-side-'))return;
   const key=id.replace('\0app04-side-',''),code=key==='entry'?entry:key==='external'?'export const openExternalLink=async()=>{};':key==='deck'?'export const getDeck=async()=>{throw Error("UNEXPECTED_FIXTURE_DECK");};':stubs[key]??empty;
   return transformWithEsbuild(code,'app04-side-'+key+'.tsx',{loader:'tsx',jsx:'automatic'});
  },configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/app04-side')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/app04-side','<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/app04-side.tsx"></script></body></html>'));});},
 }]});await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('APP04_SIDE_PORT');base='http://127.0.0.1:'+address.port+'/app04-side';
});
test.afterAll(async()=>{try{await server?.close();}finally{if(cacheRoot)await rm(cacheRoot,{recursive:true,force:true});}});
async function open(page:Page,writing=false){
 page.on('pageerror',cause=>{throw cause;});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
 await page.addInitScript(writing=>{const key='ink-appearance-fixture:ink-native-chat-recovery';if(localStorage.getItem(key))return;localStorage.setItem(key,JSON.stringify(JSON.stringify({ownerId:'owner-A',slots:{main:{threadId:'main-thread',sideChat:{threadId:'side-thread',...(writing?{writingSessionId:'writing-session'}:{})}},'thread:side-thread':{threadId:'side-thread',composer:{query:'Retained side draft',uploadedFiles:[],toolChoice:'manual',interruptedFiles:[]}}}})));},writing);
 await page.goto(base);await expect(page.getByText('Saved side-thread reply',{exact:true})).toBeVisible();
}
const draft=(page:Page)=>page.getByRole('textbox',{name:'Native draft'}).last();
const calls=(page:Page)=>page.evaluate(()=>(window as any).__sideRecoveryFixture.read().calls as {path:string;method:string;body:any}[]);
const posts=async(page:Page)=>(await calls(page)).filter(call=>call.method==='POST');

test('ordinary side Chat reopens once with its input and retains its original send ability',async({page})=>{
 await open(page);await expect(draft(page)).toHaveValue('Retained side draft');await expect(draft(page)).toBeEnabled();expect(await posts(page)).toEqual([]);
 await page.getByRole('button',{name:'Send fixture input',exact:true}).last().click();await expect(page.getByText('Saved follow-up reply',{exact:true})).toBeVisible();
 expect(await posts(page)).toHaveLength(1);expect((await posts(page))[0].body.id).toBe('side-thread');
 await page.getByText('Close',{exact:true}).click();await page.reload();await expect(page.getByText('Saved main-thread reply',{exact:true})).toBeVisible();await expect(page.getByText('Saved side-thread reply',{exact:true})).toHaveCount(0);
 expect(await page.evaluate(()=>(window as any).__sideRecoveryFixture.settings().slots.main.sideChat??null)).toBeNull();expect(await posts(page)).toHaveLength(1);
});

test('Writing side restoration keeps input protected until explicit source return and original context reentry',async({page})=>{
 await open(page,true);await expect(draft(page)).toHaveValue('Retained side draft');await expect(draft(page)).toBeEnabled();await expect(page.getByRole('button',{name:'Send fixture input',exact:true}).last()).toBeDisabled();expect(await posts(page)).toEqual([]);
 await page.getByRole('button',{name:'Writing',exact:true}).last().click();
 await expect(page.getByLabel('Original writing target',{exact:true})).toHaveText(JSON.stringify({editorSessionId:'writing-session',cellId:'writing-cell'}));
 expect((await calls(page)).filter(call=>call.path==='/api/sessions/writing-session')).toHaveLength(1);expect(await posts(page)).toEqual([]);
 await page.getByRole('button',{name:'Open original Writing conversation',exact:true}).click();await expect(draft(page)).toHaveValue('Retained side draft');await expect(draft(page)).toBeEnabled();
 await page.getByRole('button',{name:'Send fixture input',exact:true}).last().click();await expect(page.getByText('Saved follow-up reply',{exact:true})).toBeVisible();
 expect(await page.evaluate(()=>(window as any).__sideRecoveryFixture.preparations)).toBe(1);expect(await posts(page)).toHaveLength(1);expect((await posts(page))[0].body).toMatchObject({id:'side-thread',editor_state:{id:'writing-session',writingThreadId:'side-thread'}});
});

test('denied or changed Writing source retains the same protected side pointer and allows source retry',async({page})=>{
 await open(page,true);await page.evaluate(()=>{(window as any).__sideRecoveryFixture.rejectSource=true;});await page.getByRole('button',{name:'Writing',exact:true}).last().click();
 await expect.poll(async()=>(await calls(page)).filter(call=>call.path==='/api/sessions/writing-session').length).toBe(1);await expect(draft(page)).toBeEnabled();await expect(page.getByRole('button',{name:'Send fixture input',exact:true}).last()).toBeDisabled();await expect(draft(page)).toHaveValue('Retained side draft');
 expect(await page.evaluate(()=>(window as any).__sideRecoveryFixture.settings().slots.main.sideChat)).toEqual({threadId:'side-thread',writingSessionId:'writing-session'});expect(await posts(page)).toEqual([]);
 await page.evaluate(()=>{(window as any).__sideRecoveryFixture.rejectSource=false;});await page.getByRole('button',{name:'Writing',exact:true}).last().click();await expect(page.getByLabel('Original writing target',{exact:true})).toContainText('writing-session');expect(await posts(page)).toEqual([]);
});

test('a source GET from a retired side instance cannot close its replacement or navigate to the old source',async({page})=>{
 await open(page,true);await page.evaluate(()=>{(window as any).__sideRecoveryFixture.holdSource=true;});await page.getByRole('button',{name:'Writing',exact:true}).last().click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__sideRecoveryFixture.pendingSource.length)).toBe(1);
 await page.getByText('Close',{exact:true}).click();await page.getByRole('tab',{name:'More',exact:true}).click();await page.getByRole('button',{name:'Open original Writing conversation',exact:true}).click();
 await expect(draft(page)).toBeEnabled();await expect(page.getByRole('button',{name:'Send fixture input',exact:true}).last()).toBeEnabled();
 await page.evaluate(()=>{const f=(window as any).__sideRecoveryFixture;f.pendingSource.splice(0).forEach(resolve=>resolve());});
 await expect(page.getByLabel('Original writing target',{exact:true})).toHaveText('null');await expect(page.getByRole('button',{name:'Send fixture input',exact:true}).last()).toBeEnabled();
 expect(await page.evaluate(()=>(window as any).__sideRecoveryFixture.settings().slots.main.sideChat)).toEqual({threadId:'side-thread',writingSessionId:'writing-session'});expect(await posts(page)).toEqual([]);
});
