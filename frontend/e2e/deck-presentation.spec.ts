// [Input] Original Web panels, Native launcher and persisted-shape Deck/Voice fixtures.
// [Output] Home eligibility, preview fields and draft-only Chat handoff regression evidence.
// [Pos] Provider-free UI/selection qualification; no backend, account or model execution.
// Impact: Project/Episode/canonical artifact/Run-private publication/Hook/DB are out of scope.
// Shared conversation remains unchanged; only local preview, search and callback intent change.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
import {isDeckHomeVisible,isSystemDeckDisplay,matchesDeckHomeQuery,deckPreviewVoices,deckExamplePrompt} from '../app/_dream/components/deck/deckPresentation';
import type {Deck,Voice} from '../app/_dream/api/voiceApi';

const voices:Voice[]=[
  {id:'disabled',deck_id:'published',name:'Disabled author',enabled:false,system_prompt:'Disabled example',icon:'brain',color:'blue',is_system:false},
  {id:'writer',deck_id:'published',name:'Writer',enabled:true,system_prompt:'\n  Keep the original first line  \nSecond line',icon:'brain',color:'blue',is_system:false},
  {id:'editor',deck_id:'published',name:'Editor',enabled:true,system_prompt:'',icon:'brain',color:'green',is_system:false},
  {id:'fourth',deck_id:'published',name:'Fourth Agent',enabled:true,system_prompt:'Fourth example',icon:'brain',color:'green',is_system:false},
];
const published:Deck={id:'published',name:'Published Notes',name_zh:'已发布笔记',description:'Published description',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,
  deck_version_capability:true,deck_version:2,deck_version_dirty:false,deck_version_status:'published',deck_plugin_version:'0.1.12',updated_at:'2026-10-28T00:00:00Z',voices};
const decks:Deck[]=[published,{...published,id:'draft',name:'Unpublished Notes',deck_version_dirty:true},{...published,id:'disabled-deck',name:'Disabled Deck',enabled:false},
  {...published,id:'system',name:'System Notes',is_system:true,enabled:false,deck_version:undefined,voices:[]},
  {...published,id:'dream',name:'Dream Workspace',agent_type:'dream'}];

test('home eligibility preserves system defaults and exact published-clean user facts',()=>{
  expect(decks.filter(isDeckHomeVisible).map(deck=>deck.id)).toEqual(['published','system','dream']);
  expect(isSystemDeckDisplay({...published,publish_block_reason:'default_initialized',enabled:false})).toBe(true);
  for(const patch of [{deck_version_capability:false},{deck_version:0},{deck_version_dirty:undefined},{deck_version_status:'draft' as const}])expect(isDeckHomeVisible({...published,...patch})).toBe(false);
  expect(matchesDeckHomeQuery(published,'  NOTES ')).toBe(true);expect(matchesDeckHomeQuery(published,'发布')).toBe(true);expect(matchesDeckHomeQuery(published,'unknown')).toBe(false);
});
test('preview retains original trial fallback, three examples and first nonempty prompt line',()=>{
  expect(deckPreviewVoices(published)).toEqual({voices,trialVoice:voices[1],examples:voices.slice(0,3)});
  expect(deckPreviewVoices({...published,voices:[voices[0]]}).trialVoice).toBe(voices[0]);
  expect(deckPreviewVoices({...published,voices:[]}).trialVoice).toBeNull();
  expect(deckExamplePrompt(published,voices[1],'fallback')).toBe('Keep the original first line');
  expect(deckExamplePrompt(published,voices[2],'fallback')).toBe('Published description');
});

const entry=`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import i18n from '/app/_dream/i18n.ts';import '/app/_dream/styles/tokens.css';
import {DeckLaunchPanel,DeckPreviewPanel} from '/app/_dream/components/deck/DeckManagerPanels.tsx';
import NativeScreen from '/app/_dream/components/deck/DeckLaunchScreen.native.tsx';
const decks=${JSON.stringify(decks)};
const f=window.__deckLaunchFixture={trials:[],refreshes:0,edits:[],creates:0,settings:0};
const native=new URLSearchParams(location.search).has('native');
await i18n.changeLanguage('en');
function Fixture(){const [id,setId]=useState(null),deck=decks.find(deck=>deck.id===id);const trial=(deck,voice,input)=>f.trials.push({deckId:deck.id,voiceId:voice.id,input});
return native?<div style={{height:'100vh',display:'flex',flexDirection:'column'}}><NativeScreen decks={decks} active loading={false} onRefresh={()=>f.refreshes++} onTryDeck={trial}/></div>:
<div style={{padding:16}}>{deck?<DeckPreviewPanel deck={deck} launchError={null} launchingDream={false} onBack={()=>setId(null)} onEditDeck={id=>f.edits.push(id)} onTryDeck={(id,voice,input)=>trial(decks.find(deck=>deck.id===id),voice,input)}/>:
<DeckLaunchPanel decks={decks} creatingDeck={false} refreshingDecks={false} refreshError={null} operationError={null} onCreateDeck={()=>f.creates++} onRefreshDecks={()=>f.refreshes++} onOpenDeck={setId} onOpenSettings={()=>f.settings++}/>}</div>}
createRoot(document.getElementById('root')).render(<Fixture/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const diagnostics=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
  const root=fileURLToPath(new URL('../',import.meta.url));
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-deck-launch-20261029/vite',
    optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next']},
    resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'}]},
    server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'deck-presentation-fixture',enforce:'pre',resolveId(id){if(id==='/deck-presentation-entry.tsx')return '\0deck-presentation-entry';},
      async load(id){if(id==='\0deck-presentation-entry')return transformWithEsbuild(entry,'deck-presentation-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'});},
      configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/deck-presentation-fixture')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/deck-presentation-fixture','<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/deck-presentation-entry.tsx"></script></body></html>'));});}}]});
  await server.listen();const address=server.httpServer?.address();if(!address || typeof address==='string')throw Error('FIXTURE_LISTENER_MISSING');base=`http://127.0.0.1:${address.port}/deck-presentation-fixture`;
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
for(const native of [false,true]) {
  const kind=native?'Native presentation boundary':'original Web';
  test(`${kind} preserves eligibility, search, original preview and draft-only example callback`,async({page})=>{
    await page.setViewportSize({width:390,height:844});await page.goto(base+(native?'?native=1':''));
    await expect(page.getByRole('button',{name:'Edit Published Notes',exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Edit Unpublished Notes',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Edit Disabled Deck',exact:true})).toHaveCount(0);
    if(native)await expect(page.getByText('Dream Workspace',{exact:true})).toHaveCount(0);
    await page.getByRole(native?'textbox':'searchbox',{name:'Search available Decks'}).fill('NOTES');
    await page.getByRole('button',{name:'Edit Published Notes',exact:true}).click();
    await expect(page.getByText('Agents 4',{exact:true})).toBeVisible();await expect(page.getByText('0.1.12',{exact:true})).toBeVisible();
    const example=page.getByRole('button',{name:native?'Writer: Keep the original first line':/Writer.*Keep the original first line/});await example.click();
    expect(await page.evaluate(()=>(window as any).__deckLaunchFixture.trials)).toEqual([{deckId:'published',voiceId:'writer',input:'Keep the original first line'}]);
    await page.getByRole('button',{name:/Try now/}).click();
    expect(await page.evaluate(()=>(window as any).__deckLaunchFixture.trials)).toEqual([{deckId:'published',voiceId:'writer',input:'Keep the original first line'},{deckId:'published',voiceId:'writer'}]);
    await page.getByRole('button',{name:/Back to Decks/}).click();await expect(page.getByRole('button',{name:'Edit Published Notes',exact:true})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  });
}
