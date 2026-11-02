// [Sync] 2026-10-29: align the existing Voice-loader fixture with its production single catalog read.
// [Input] Public Web Deck/Voice reads, Agent search and outgoing Chat request contracts.
// [Output] Provider-free regression evidence for shared-module extraction without business changes.
// [Pos] Web compatibility gate; no browser credentials, backend, model or database calls.
import {expect, test} from '@playwright/test';
import {listDecks, getDeck, loadVoicesFromDecks, type Deck, type Voice} from '../app/_dream/api/voiceApi';
import {clearBrowserSession, loadBrowserSession} from '../app/_dream/lib/browserSession';
import {groupDeckAgents, agentLabel, deckLabel} from '../app/_dream/components/deck/deckAgentSelection';
import {buildClaudeChatRequest} from '../app/_dream/lib/claude-chat-request';

const enabledVoice = {id:'fixture-agent', name:'Author', name_en:'Writer', name_zh:'写作', enabled:true, system_prompt:'Original prompt'} as Voice;
const disabledVoice = {...enabledVoice, id:'fixture-disabled', enabled:false};
const deck = {id:'fixture-deck', name:'Notebook', name_en:'Writing', name_zh:'创作', enabled:true, voices:[enabledVoice, disabledVoice]} as Deck;
const csrf = 'a'.repeat(43);
const message = {id:'fixture-message', role:'user' as const, parts:[{type:'text' as const, text:'Keep my request'}]};

async function session() {
  await loadBrowserSession(async () => Response.json({
    user:{id:'1', email:'fixture@example.invalid', display_name:null, avatar_url:null, role:'user', created_at:null},
    csrf_token:csrf,
  }));
}
test.afterEach(() => clearBrowserSession());

test('existing voice loader still reads the shared Deck functions and excludes disabled entries', async () => {
  await session();
  const original = globalThis.fetch;
  const calls:string[] = [];
  globalThis.fetch = async (input, init) => {
    const path = String(input); calls.push(path);
    expect(new Headers(init?.headers).get('x-ink-csrf')).toBe(csrf);
    if(path === '/api/decks/catalog') return Response.json({decks:[deck, {...deck,id:'disabled-deck',enabled:false}]});
    throw new Error(`Unexpected request: ${path}`);
  };
  try {
    const voices = await loadVoicesFromDecks();
    expect(Object.keys(voices)).toEqual(['fixture-agent']);
    expect(voices['fixture-agent']).toMatchObject({name:'Author', systemPrompt:'Original prompt', enabled:true});
    expect(calls).toEqual(['/api/decks/catalog']);
  } finally {globalThis.fetch = original;}
});

test('Deck reads preserve login precondition, same-origin paths and server errors', async () => {
  clearBrowserSession();
  let calls = 0;
  const denied:typeof fetch = async () => {calls++; return Response.json({});};
  await expect(listDecks(denied)).rejects.toThrow('Not authenticated');
  expect(calls).toBe(0);
  await session();
  const transport:typeof fetch = async (input, init) => {
    expect(String(input)).toBe('/api/decks/fixture-deck');
    const headers = new Headers(init?.headers);
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('x-ink-csrf')).toBe(csrf);
    expect(headers.has('Authorization')).toBe(false);
    return Response.json({detail:'Existing server error'}, {status:403});
  };
  await expect(getDeck('fixture-deck',transport)).rejects.toThrow('Existing server error');
});

test('Agent search retains localized prefix matching, grouping and enabled-only choices', () => {
  expect(groupDeckAgents([deck], '  WRIT ', 'en').map(group => group.agents.map(agent => agent.id))).toEqual([['fixture-agent']]);
  expect(groupDeckAgents([deck], '创', 'zh')[0].agents).toEqual([enabledVoice]);
  expect(groupDeckAgents([deck], 'uth', 'en')).toEqual([]);
  expect(groupDeckAgents([{...deck, voices:[disabledVoice]}], '', 'en')).toEqual([]);
  expect(agentLabel(enabledVoice,'zh')).toBe('写作');
  expect(deckLabel({...deck,name_en:undefined},'en')).toBe('Notebook');
});

test('Chat preserves selected Agent, manual approval, original text and only stored attachments', () => {
  const result = buildClaudeChatRequest({id:'fixture-thread',message,context:{
    deckId:deck.id,voiceId:enabledVoice.id,voiceSystemPrompt:'',settingsSystemPrompt:'Settings prompt',
    editorState:{content:'Existing editor'},imFullAccessEnabled:false,currentToolChoice:'auto',
  },toolChoice:'manual',attachments:[
    {name:'ready.txt',type:'text/plain',size:12,storageKey:'fixture-key',workspacePath:'existing/ready.txt',savedAt:'2026-10-28T00:00:00Z',hash:'fixture-hash'},
    {name:'unfinished.txt',type:'text/plain',size:8,url:'blob:unfinished'},
  ]});
  expect(result).toMatchObject({id:'fixture-thread',deckId:deck.id,voiceId:enabledVoice.id,resume:true,
    message,toolChoice:'manual',systemPrompt:'',editor_state:{content:'Existing editor'},allowedAppDefaultToolkit:[],allowedMcpServers:{}});
  expect(result.attachments).toEqual([{type:'file',url:'/api/storage/file/Zml4dHVyZS1rZXk=',storageKey:'fixture-key',mediaType:'text/plain',filename:'ready.txt',size:12,workspacePath:'existing/ready.txt',savedAt:'2026-10-28T00:00:00Z',hash:'fixture-hash'}]);
});

test('Chat retains effective full-access projection and optional context defaults', () => {
  const context = {imFullAccessEnabled:false,currentToolChoice:'manual' as const,settingsSystemPrompt:'Settings prompt'};
  const manual = buildClaudeChatRequest({id:'fixture-thread',message,context});
  expect(manual.toolChoice).toBe('manual');
  expect(manual.systemPrompt).toBe('Settings prompt');
  expect(manual).not.toHaveProperty('deckId');
  expect(manual).not.toHaveProperty('voiceId');
  expect(manual).not.toHaveProperty('editor_state');
  expect(manual.attachments).toEqual([]);
  expect(buildClaudeChatRequest({id:'fixture-thread',message,context:{...context,imFullAccessEnabled:true},toolChoice:'manual'}).toolChoice).toBe('auto');
});
