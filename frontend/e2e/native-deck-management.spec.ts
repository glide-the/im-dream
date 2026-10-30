// [Input] Production Native Deck manager/editor, original APIs/hooks and public-shape HTTP fixtures.
// [Output] Create/blur-save/Agent/plugin/version/confirmation/recovery and narrow-page contracts.
// [Pos] Provider-free technical UI lane; no normal account, service, database or model writes.
// Impact: Project/Episode/artifact/Run/Hook/DB are out of scope; Chat receives local draft intent only.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';

const entry=String.raw`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';import {Alert} from 'react-native';
import DeckManager from '/app/_dream/components/DeckManager.native.tsx';
import {listDecksWithVoices} from '/app/_dream/api/deckReadApi.ts';
import {loadBrowserSession} from '/app/_dream/lib/browserSession.ts';import i18n from '/app/_dream/i18n.ts';
await i18n.changeLanguage('en');
await loadBrowserSession(async()=>Response.json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const now='2026-10-29T00:00:00Z';
const voice=(deckId,id='writer')=>({id:deckId+'-'+id,deck_id:deckId,name:id==='writer'?'Writer':'New Voice',enabled:true,system_prompt:'Keep the original prompt',icon:'brain',color:'blue',is_system:false});
const deck=(id,name,patch={})=>({id,name,description:'Original notes',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,deck_version_capability:true,deck_version:1,deck_version_dirty:false,deck_version_status:'published',draft_revision:1,updated_at:now,voices:[voice(id)],...patch});
const f=window.__nativeDeckFixture={calls:[],confirmations:[],confirmResult:true,trials:[],expirations:0,failUpdate:false,failPlugins:false,conflict:false,holdRelated:false,held:[],decks:[
deck('notes','Published Notes',{parent_id:'template'}),deck('draft','Unpublished Notes',{deck_version:undefined,deck_version_dirty:true,deck_version_status:'unpublished'}),deck('disabled','Disabled Notes',{enabled:false}),
deck('system','System Notes',{is_system:true,enabled:false}),deck('default','Default Notes',{publish_block_reason:'default_initialized',enabled:false}),deck('dream','Dream Workspace',{agent_type:'dream'}),
...Array.from({length:7},(_,i)=>deck('extra-'+i,'Other Notes '+i))],versions:{},refs:[],threads:Array.from({length:21},(_,i)=>({id:'related-'+i,title:'Existing related Chat '+i,deck_id:'notes',created_at:now,updated_at:now})),created:0};
Alert.alert=(title,message,buttons)=>{f.confirmations.push(message);buttons.find(button=>f.confirmResult?button.style==='destructive':button.style==='cancel')?.onPress?.();};
const state=id=>{const row=f.decks.find(deck=>deck.id===id);return {deck_id:id,draft_revision:row?.draft_revision||1,latest_version:row?.deck_version??null,published_draft_revision:row?.deck_version_dirty?0:row?.draft_revision||1,dirty:row?.deck_version_dirty===true,status:row?.deck_version_status||'unpublished',next_version:(row?.deck_version||0)+1};};
const dirty=id=>{const row=f.decks.find(deck=>deck.id===id);row.draft_revision++;row.deck_version_dirty=true;row.deck_version_status='draft';};
async function transport(input,init={}){
 const url=new URL(String(input),'http://fixture.invalid'),method=init.method||'GET',path=url.pathname,body=init.body?JSON.parse(init.body):undefined;
 f.calls.push({path:url.pathname+url.search,method,body,headers:Object.fromEntries(new Headers(init.headers))});
 if(path==='/api/decks/catalog'&&method==='GET')return Response.json({decks:structuredClone(f.decks)});
 if(path==='/api/decks'&&method==='POST'){const id='created-'+(++f.created);f.decks.push(deck(id,body.name,{...body,voices:[],deck_version:undefined,deck_version_dirty:true,deck_version_status:'unpublished'}));return Response.json({deck_id:id});}
 if(path==='/api/voices'&&method==='POST'){const row=f.decks.find(deck=>deck.id===body.deck_id),record={...voice(row.id,'new-'+row.voices.length),...body};row.voices.push(record);dirty(row.id);return Response.json({voice_id:record.id});}
 const vm=/^\/api\/voices\/([^/]+)$/.exec(path);
 if(vm){const row=f.decks.find(deck=>deck.voices.some(voice=>voice.id===vm[1]));if(method==='PUT')Object.assign(row.voices.find(voice=>voice.id===vm[1]),body);else if(method==='DELETE')row.voices=row.voices.filter(voice=>voice.id!==vm[1]);else throw Error('UNEXPECTED_VOICE_HTTP');dirty(row.id);return new Response(null,{status:204});}
 if(path==='/api/claude-plugins/installations'&&method==='GET')return Response.json({installations:[{id:'ready-plugin',package_name:'notes-tools',requested_package_spec:'notes-tools@1.2.3',resolved_version:'1.2.3',artifact_digest:'sha256:'+'a'.repeat(64),status:'ready'},{id:'installing-plugin',package_name:'unfinished-tools',status:'installing'}]});
 const match=/^\/api\/decks\/([^/]+)(.*)$/.exec(path);
 if(match){const id=decodeURIComponent(match[1]),suffix=match[2],row=f.decks.find(deck=>deck.id===id);
  if(suffix==='/version-state'&&method==='GET')return Response.json(state(id));
  if(suffix==='/versions'&&method==='GET')return Response.json({deck_id:id,current:state(id),versions:f.versions[id]||[]});
  if(suffix==='/versions/preview'&&method==='POST'){if(f.conflict||body.expected_draft_revision!==state(id).draft_revision)return Response.json({error_code:'DECK_DRAFT_REVISION_CONFLICT',message:'Draft changed. Read the current version.'},{status:409});return Response.json({...state(id),target_version:state(id).next_version,changes:[{scope:'deck',change_type:'modified',label:'Deck information',fields:['name']}],impact:['Existing conversations remain unchanged']});}
  if(suffix==='/versions'&&method==='POST'){if(body.expected_draft_revision!==state(id).draft_revision||body.expected_base_version!==state(id).latest_version)return Response.json({error_code:'DECK_DRAFT_REVISION_CONFLICT',message:'Draft changed.'},{status:409});
   const version={version:state(id).next_version,base_version:state(id).latest_version,source_draft_revision:state(id).draft_revision,description:body.description,content_hash:'b'.repeat(64),created_by:1,created_at:now,runtime_plugin_version:null};
   row.deck_version=version.version;row.deck_version_dirty=false;row.deck_version_status='published';f.versions[id]=[version,...(f.versions[id]||[])];return Response.json({deck_id:id,version,state:state(id)});}
  if(suffix==='/claude-plugins'){if(method==='GET')return Response.json({refs:f.refs});if(method==='PUT'){if(f.failPlugins)return Response.json({error:{code:'PLUGIN_REF_SAVE_FAILED',message:'Reference save failed'}},{status:503});f.refs=body.refs.map(ref=>({...ref,enabled:1}));dirty(id);return Response.json({refs:f.refs});}}
  if(suffix==='/sync'&&method==='POST'){dirty(id);return Response.json({success:true,synced_voices:row.voices.length});}
  if(suffix===''&&method==='PUT'){if(f.failUpdate)return Response.json({detail:'Save failed; keep your draft.'},{status:503});Object.assign(row,body);dirty(id);return new Response(null,{status:204});}
  if(suffix===''&&method==='DELETE'){f.decks=f.decks.filter(deck=>deck.id!==id);return new Response(null,{status:204});}
 }
 if(path==='/api/claude-agent/threads'&&method==='GET'){const reply=()=>Response.json({threads:structuredClone(f.threads.filter(row=>row.deck_id===url.searchParams.get('deck_id')).slice(Number(url.searchParams.get('offset')||0),Number(url.searchParams.get('offset')||0)+Number(url.searchParams.get('limit'))))});if(f.holdRelated){const captured=reply();return new Promise(resolve=>f.held.push(()=>resolve(captured)));}return reply();}
 if(path.startsWith('/api/claude-agent/threads/')&&method==='DELETE'){f.threads=f.threads.filter(row=>row.id!==path.split('/').pop());return new Response(null,{status:204});}
 throw Error('UNEXPECTED_FIXTURE_HTTP '+method+' '+path);
}
function Fixture(){const [decks,setDecks]=useState(structuredClone(f.decks));const refresh=async()=>{const next=await listDecksWithVoices(transport);setDecks(next);return next;};return <div style={{height:'100vh',display:'flex',flexDirection:'column'}}><DeckManager decks={decks} active loading={false} onRefresh={refresh} transport={transport} onSessionExpired={()=>f.expirations++} onTryDeck={(deck,voice,input)=>f.trials.push({deckId:deck.id,voiceId:voice.id,input})}/></div>;}
createRoot(document.getElementById('root')).render(<Fixture/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
  const root=fileURLToPath(new URL('../',import.meta.url));
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-deck-management-20261029/vite',
    optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next']},
    resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},
    server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'native-deck-manager-fixture',enforce:'pre',resolveId(id){if(id==='/native-deck-manager-entry.tsx')return '\0native-deck-manager-entry';},
      async load(id){if(id==='\0native-deck-manager-entry')return transformWithEsbuild(entry,'native-deck-manager-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'});},
      configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-deck-manager-fixture')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-deck-manager-fixture','<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/native-deck-manager-entry.tsx"></script></body></html>'));});}}]});
  await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('FIXTURE_LISTENER_MISSING');base='http://127.0.0.1:'+address.port+'/native-deck-manager-fixture';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());await page.setViewportSize({width:390,height:844});await page.goto(base);await expect(page.getByRole('button',{name:'Open Deck settings',exact:true})).toBeVisible();});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
async function work(page:Page){await page.getByRole('button',{name:'Open Deck settings',exact:true}).click();await expect(page.getByTestId('native-deck-management')).toBeVisible();}
async function edit(page:Page){await work(page);await page.getByRole('button',{name:'Edit Published Notes',exact:true}).click();await expect(page.getByRole('textbox',{name:'Deck name',exact:true})).toHaveValue('Published Notes');await expect(page.getByRole('button',{name:'版本记录',exact:true})).toBeEnabled();}
async function calls(page:Page){return page.evaluate(()=>(window as any).__nativeDeckFixture.calls);}

test('native Work preserves full inventory, system locks, filters and pagination without writes',async({page})=>{
  await work(page);await expect(page.getByRole('button',{name:'Edit Unpublished Notes',exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Edit Disabled Notes',exact:true})).toBeVisible();
  for(const name of ['System Notes','Default Notes']){await expect(page.getByRole('button',{name:'Edit '+name,exact:true})).toBeDisabled();await expect(page.getByRole('switch',{name:new RegExp(name)})).toHaveCount(0);}
  await expect(page.getByText('Dream Workspace',{exact:true})).toHaveCount(0);await expect(page.getByText('Page 1 of 2',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('Page 2 of 2',{exact:true})).toBeVisible();
  await page.getByRole('textbox',{name:'Search managed Decks',exact:true}).fill('unpublished');await expect(page.getByRole('button',{name:'Edit Unpublished Notes',exact:true})).toBeVisible();
  await expect(page.getByText('Page 2 of 2',{exact:true})).toHaveCount(0);expect(await calls(page)).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('native create retains original defaults and blur-save failure preserves the local draft for retry',async({page})=>{
  await work(page);await page.getByRole('button',{name:'Create Deck',exact:true}).click();const field=page.getByRole('textbox',{name:'Deck name',exact:true});await expect(field).toHaveValue('New Deck');
  expect((await calls(page)).find((call:any)=>call.path==='/api/decks'&&call.method==='POST').body).toEqual({name:'New Deck',description:'Describe your deck here',icon:'brain',color:'blue'});
  await page.evaluate(()=>(window as any).__nativeDeckFixture.failUpdate=true);await field.fill('Notes for travel');await page.getByRole('heading',{name:'Deck information',exact:true}).click();
  await expect(page.getByRole('button',{name:'重试保存 Deck name',exact:true})).toBeVisible();await expect(field).toHaveValue('Notes for travel');
  await page.getByRole('tab',{name:/^Agents/}).click();await page.getByRole('tab',{name:'概览',exact:true}).click();await expect(field).toHaveValue('Notes for travel');await expect(page.getByRole('button',{name:'重试保存 Deck name',exact:true})).toBeVisible();
  await page.evaluate(()=>(window as any).__nativeDeckFixture.failUpdate=false);await page.getByRole('button',{name:'重试保存 Deck name',exact:true}).click();
  await expect(page.getByRole('button',{name:'重试保存 Deck name',exact:true})).toHaveCount(0);await expect(page.getByText('草稿 r2',{exact:false})).toBeVisible();expect(await page.evaluate(()=>(window as any).__nativeDeckFixture.trials)).toEqual([]);
});
test('native Agent operations retain original default payload, visual options, switch and delete cancellation',async({page})=>{
  await edit(page);await page.getByRole('tab',{name:/^Agents/}).click();await page.getByRole('button',{name:'+ Add',exact:true}).click();const field=page.getByRole('textbox',{name:'Agent Name',exact:true});await expect(field).toHaveValue('New Voice');
  expect((await calls(page)).find((call:any)=>call.path==='/api/voices'&&call.method==='POST').body).toEqual({deck_id:'notes',name:'New Voice',system_prompt:'You are a helpful assistant.',icon:'brain',color:'blue'});
  await field.fill('Travel writer');await page.getByText('Agent Prompt',{exact:true}).click();await expect(page.getByRole('button',{name:'Travel writer',exact:true})).toBeVisible();
  await page.getByRole('radio',{name:'Agent Icon compass',exact:true}).click();await expect(page.getByRole('radio',{name:'Agent Icon compass',exact:true})).toBeChecked();
  await page.getByRole('radio',{name:'Agent Color Green',exact:true}).click();await expect(page.getByRole('radio',{name:'Agent Color Green',exact:true})).toBeChecked();
  await page.getByRole('switch',{name:'Toggle Travel writer',exact:true}).click();await expect(page.getByRole('switch',{name:'Toggle Travel writer',exact:true})).not.toBeChecked();await page.getByRole('button',{name:'Travel writer',exact:true}).click();
  await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=false);await page.getByRole('button',{name:'Delete',exact:true}).click();expect((await calls(page)).some((call:any)=>call.path.startsWith('/api/voices/')&&call.method==='DELETE')).toBe(false);
  await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=true);await page.getByRole('button',{name:'Delete',exact:true}).click();await expect(page.getByRole('button',{name:'Travel writer',exact:true})).toHaveCount(0);
});
test('native plugin refs retain ready eligibility, selection after failure and original retry payload',async({page})=>{
  await edit(page);await page.getByRole('tab',{name:'Claude 插件',exact:true}).click();const plugin=page.getByRole('checkbox',{name:'notes-tools v1.2.3',exact:true});await expect(plugin).toBeVisible();await expect(page.getByText('unfinished-tools',{exact:true})).toHaveCount(0);
  await plugin.click();await page.evaluate(()=>(window as any).__nativeDeckFixture.failPlugins=true);await page.getByRole('button',{name:'保存插件选择',exact:true}).click();await expect(page.getByRole('alert')).toBeVisible();await expect(plugin).toBeChecked();
  await page.evaluate(()=>(window as any).__nativeDeckFixture.failPlugins=false);await page.getByRole('button',{name:'保存插件选择',exact:true}).click();await expect(page.getByText('已保存 ✓',{exact:true})).toBeVisible();
  expect((await calls(page)).filter((call:any)=>call.path.endsWith('/claude-plugins')&&call.method==='PUT').at(-1).body).toEqual({refs:[{plugin_installation_id:'ready-plugin',enabled:true,order_index:0}]});
  expect((await calls(page)).filter((call:any)=>call.path.startsWith('/api/claude-plugins/')&&call.method!=='GET')).toEqual([]);
});
test('native content version requires explicit diff confirmation, exact CAS and original immutable history',async({page})=>{
  await edit(page);await page.getByRole('textbox',{name:'Description',exact:true}).fill('Notes to keep');await page.getByRole('heading',{name:'Deck information',exact:true}).click();
  await expect(page.getByRole('button',{name:'提交 v2',exact:true})).toBeEnabled();await page.getByRole('button',{name:'提交 v2',exact:true}).click();await expect(page.getByRole('button',{name:'确认提交 v2',exact:true})).toBeVisible();
  expect((await calls(page)).filter((call:any)=>call.path==='/api/decks/notes/versions'&&call.method==='POST')).toHaveLength(0);await page.getByRole('button',{name:'取消',exact:true}).click();
  await page.getByRole('button',{name:'提交 v2',exact:true}).click();await page.getByRole('textbox',{name:'版本说明（可选）',exact:true}).fill('First native notes');await page.getByRole('button',{name:'确认提交 v2',exact:true}).click();
  await expect(page.getByRole('textbox',{name:'Deck name',exact:true})).toHaveValue('Published Notes');expect((await calls(page)).find((call:any)=>call.path==='/api/decks/notes/versions'&&call.method==='POST').body).toEqual({expected_draft_revision:2,expected_base_version:1,description:'First native notes'});
  await page.getByRole('button',{name:'版本记录',exact:true}).click();await expect(page.getByText(/First native notes/)).toBeVisible();await expect(page.getByText('v2',{exact:true}).first()).toBeVisible();
  for(const call of await calls(page)){if(call.path.startsWith('/api/decks/')||call.path.startsWith('/api/voices')){expect(call.headers['x-ink-csrf']).toHaveLength(43);expect(call.headers.authorization).toBeUndefined();}}
  expect(await page.evaluate(()=>(window as any).__nativeDeckFixture.trials)).toEqual([]);
});
test('native preview conflict refreshes original state and creates no content version',async({page})=>{
  await edit(page);await page.getByRole('textbox',{name:'Description',exact:true}).fill('Changed draft');await page.getByRole('heading',{name:'Deck information',exact:true}).click();await expect(page.getByRole('button',{name:'提交 v2',exact:true})).toBeEnabled();
  await page.evaluate(()=>(window as any).__nativeDeckFixture.conflict=true);await page.getByRole('button',{name:'提交 v2',exact:true}).click();await expect(page.getByRole('button',{name:'确认提交 v2',exact:true})).toHaveCount(0);await expect(page.getByRole('alert')).toContainText('Draft changed. Read the current version.');
  expect((await calls(page)).filter((call:any)=>call.path==='/api/decks/notes/versions'&&call.method==='POST')).toEqual([]);await expect(page.getByRole('textbox',{name:'Description',exact:true})).toHaveValue('Changed draft');
});
test('native related Chat keeps original Deck filter, paging and delete confirmation',async({page})=>{
  await work(page);await page.getByRole('button',{name:'More actions for Published Notes',exact:true}).click();await page.getByRole('button',{name:'Related conversations',exact:true}).click();await expect(page.getByText('Existing related Chat 0',{exact:true})).toBeVisible();
  expect((await calls(page)).find((call:any)=>call.path.startsWith('/api/claude-agent/threads?')).path).toBe('/api/claude-agent/threads?deck_id=notes&limit=20');
  await page.getByRole('button',{name:'Load more',exact:true}).click();await expect(page.getByText('Existing related Chat 20',{exact:true})).toBeVisible();
  await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=false);await page.getByRole('button',{name:'Delete',exact:true}).first().click();expect((await calls(page)).some((call:any)=>call.method==='DELETE')).toBe(false);
  await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=true);await page.getByRole('button',{name:'Delete',exact:true}).first().click();await expect(page.getByText('Existing related Chat 0',{exact:true})).toHaveCount(0);
});


test('native commit conflict keeps reviewed CAS, requires a new preview and retains the draft',async({page})=>{
  await edit(page);await page.getByRole('textbox',{name:'Description',exact:true}).fill('Draft reviewed before conflict');await page.getByRole('heading',{name:'Deck information',exact:true}).click();
  await expect(page.getByRole('button',{name:'提交 v2',exact:true})).toBeEnabled();await page.getByRole('button',{name:'提交 v2',exact:true}).click();await expect(page.getByRole('button',{name:'确认提交 v2',exact:true})).toBeVisible();
  await page.evaluate(()=>{const row=(window as any).__nativeDeckFixture.decks.find((deck:any)=>deck.id==='notes');row.draft_revision++;});
  await page.getByRole('button',{name:'确认提交 v2',exact:true}).click();await expect(page.getByRole('alert')).toContainText('Draft changed.');await expect(page.getByRole('button',{name:'确认提交 v2',exact:true})).toHaveCount(0);
  await expect(page.getByRole('textbox',{name:'Description',exact:true})).toHaveValue('Draft reviewed before conflict');expect(await page.evaluate(()=>(window as any).__nativeDeckFixture.versions.notes??[])).toEqual([]);
  await page.getByRole('button',{name:'提交 v2',exact:true}).click();await expect(page.getByRole('button',{name:'确认提交 v2',exact:true})).toBeVisible();await page.getByRole('button',{name:'确认提交 v2',exact:true}).click();
  await expect(page.getByRole('textbox',{name:'Deck name',exact:true})).toBeVisible();const commits=(await calls(page)).filter((call:any)=>call.path==='/api/decks/notes/versions'&&call.method==='POST');
  expect(commits.map((call:any)=>call.body)).toEqual([{expected_draft_revision:2,expected_base_version:1,description:null},{expected_draft_revision:3,expected_base_version:1,description:null}]);
});
test('native Deck enable/delete/sync preserve original payloads and destructive cancellation',async({page})=>{
  await work(page);await page.getByRole('switch',{name:'Enable Disabled Notes',exact:true}).click();await expect(page.getByRole('switch',{name:'Disable Disabled Notes',exact:true})).toBeChecked();
  expect((await calls(page)).find((call:any)=>call.path==='/api/decks/disabled'&&call.method==='PUT').body).toEqual({enabled:true});
  await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=false);await page.getByRole('button',{name:'More actions for Published Notes',exact:true}).click();await page.getByRole('button',{name:'Sync with Original',exact:true}).click();
  expect((await calls(page)).some((call:any)=>call.path.endsWith('/sync'))).toBe(false);await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=true);
  await page.getByRole('button',{name:'More actions for Published Notes',exact:true}).click();await page.getByRole('button',{name:'Sync with Original',exact:true}).click();await expect.poll(async()=>(await calls(page)).filter((call:any)=>call.path==='/api/decks/notes/sync').length).toBe(1);
  await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=false);await page.getByRole('button',{name:'More actions for Disabled Notes',exact:true}).click();await page.getByRole('button',{name:'Delete Deck',exact:true}).click();
  expect((await calls(page)).some((call:any)=>call.path==='/api/decks/disabled'&&call.method==='DELETE')).toBe(false);await page.evaluate(()=>(window as any).__nativeDeckFixture.confirmResult=true);
  await page.getByRole('button',{name:'More actions for Disabled Notes',exact:true}).click();await page.getByRole('button',{name:'Delete Deck',exact:true}).click();await expect(page.getByRole('button',{name:'Edit Disabled Notes',exact:true})).toHaveCount(0);
});
test('native related-history close rejects a late response from the old Deck',async({page})=>{
  await work(page);await page.evaluate(()=>(window as any).__nativeDeckFixture.holdRelated=true);await page.getByRole('button',{name:'More actions for Published Notes',exact:true}).click();await page.getByRole('button',{name:'Related conversations',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>(window as any).__nativeDeckFixture.held.length)).toBe(1);await page.getByRole('button',{name:'Close',exact:true}).click();await page.evaluate(()=>(window as any).__nativeDeckFixture.holdRelated=false);
  await page.getByRole('button',{name:'More actions for Disabled Notes',exact:true}).click();await page.getByRole('button',{name:'Related conversations',exact:true}).click();await expect(page.getByText('No related conversations',{exact:true})).toBeVisible();
  await page.evaluate(()=>(window as any).__nativeDeckFixture.held.splice(0).forEach((release:any)=>release()));await expect(page.getByText('Existing related Chat 0',{exact:true})).toHaveCount(0);await expect(page.getByText('No related conversations',{exact:true})).toBeVisible();
});


test('native preview remains on the selected Deck after an edit makes it a dirty draft',async({page})=>{
  await page.getByRole('button',{name:'Edit Published Notes',exact:true}).click();await expect(page.getByTestId('native-deck-preview')).toBeVisible();
  await page.getByRole('button',{name:'Edit',exact:true}).click();await expect(page.getByRole('textbox',{name:'Description',exact:true})).toHaveValue('Original notes');
  await page.getByRole('textbox',{name:'Description',exact:true}).fill('Keep this selected Deck open');await page.getByRole('heading',{name:'Deck information',exact:true}).click();await expect(page.getByRole('button',{name:'提交 v2',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Close',exact:true}).click();await expect(page.getByTestId('native-deck-preview')).toBeVisible();await expect(page.getByText('Published Notes',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:/Back to Decks/}).click();await expect(page.getByTestId('native-deck-home')).toBeVisible();await expect(page.getByRole('button',{name:'Edit Published Notes',exact:true})).toHaveCount(0);
});
