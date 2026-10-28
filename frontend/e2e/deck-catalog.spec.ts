// [Input] Production Deck catalog client, Voice config loader and browser-session owner with injected HTTP.
// [Output] Single-request hydration, in-flight sharing, fresh rereads and failure/session isolation evidence.
// [Pos] Provider-free transport contract; no database, model, Thread or Dream artifact mutation.
import {expect,test} from '@playwright/test';
import {listDecksWithVoices} from '../app/_dream/api/deckReadApi';
import {loadVoicesFromDecks, type Deck} from '../app/_dream/api/voiceApi';
import {clearBrowserSession,loadBrowserSession} from '../app/_dream/lib/browserSession';

async function session(token='a'.repeat(43)) {
  await loadBrowserSession(async()=>Response.json({user:{id:'42',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:token}));
}
const decks:Deck[]=[{id:'enabled',name:'Enabled',is_system:false,enabled:true,voices:[
  {id:'agent',deck_id:'enabled',name:'Agent',system_prompt:'Prompt',icon:'brain',color:'blue',is_system:false,enabled:true},
  {id:'disabled-agent',deck_id:'enabled',name:'Disabled',system_prompt:'',icon:'brain',color:'blue',is_system:false,enabled:false},
]}, {id:'disabled',name:'Disabled',is_system:false,enabled:false,voices:[
  {id:'hidden-agent',deck_id:'disabled',name:'Hidden',system_prompt:'',icon:'brain',color:'blue',is_system:false,enabled:true},
]}];
test.afterEach(()=>clearBrowserSession());

test('concurrent selector and Voice initialization share one complete catalog request',async()=>{
  await session();
  const original=globalThis.fetch,urls:string[]=[];
  let release!:()=>void;
  const held=new Promise<void>(resolve=>{release=resolve;});
  globalThis.fetch=async(input,init)=>{urls.push(String(input));expect(new Headers(init?.headers).get('x-ink-csrf')).toBe('a'.repeat(43));await held;return Response.json({decks});};
  try {
    const selector=listDecksWithVoices(),strictModeRerender=listDecksWithVoices(),voices=loadVoicesFromDecks();
    expect(strictModeRerender).toBe(selector);expect(urls).toEqual(['/api/decks/catalog']);
    release();expect(await selector).toEqual(decks);
    expect(await voices).toEqual({agent:{name:'Agent',systemPrompt:'Prompt',enabled:true,icon:'brain',color:'blue'}});
  } finally {release();globalThis.fetch=original;}
});

test('settled catalog reads are fresh and never persist Agent prompt data in a client cache',async()=>{
  await session();let reads=0;
  const transport:typeof fetch=async()=>Response.json({decks:[{...decks[0],name:String(++reads)}]});
  expect((await listDecksWithVoices(transport))[0].name).toBe('1');
  expect((await listDecksWithVoices(transport))[0].name).toBe('2');expect(reads).toBe(2);
});

test('failed catalog requests are shared, released and retried only by a new read',async()=>{
  await session();const urls:string[]=[];
  const transport:typeof fetch=async(input)=>{urls.push(String(input));return urls.length===1?Response.json({detail:'Catalog unavailable'},{status:503}):Response.json({decks:[]});};
  const first=listDecksWithVoices(transport),second=listDecksWithVoices(transport);
  expect(second).toBe(first);await expect(first).rejects.toThrow('Catalog unavailable');
  expect(await listDecksWithVoices(transport)).toEqual([]);expect(urls).toEqual(['/api/decks/catalog','/api/decks/catalog']);
});

test('an abandoned session cannot return its catalog to the new session',async()=>{
  await session();let release!:()=>void;
  const held=new Promise<void>(resolve=>{release=resolve;});
  const transport:typeof fetch=async()=>{await held;return Response.json({decks});};
  const old=listDecksWithVoices(transport);clearBrowserSession();await session('b'.repeat(43));
  const current=listDecksWithVoices(transport);expect(current).not.toBe(old);release();
  await expect(old).rejects.toThrow('Not authenticated');expect(await current).toEqual(decks);
});

test('missing authentication stops catalog traffic before transport',async()=>{
  clearBrowserSession();let calls=0;
  await expect(listDecksWithVoices(async()=>{calls++;return Response.json({decks});})).rejects.toThrow('Not authenticated');expect(calls).toBe(0);
});
