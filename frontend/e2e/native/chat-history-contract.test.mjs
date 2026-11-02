// [Input] Production history helpers and an injected, in-memory HTTP recorder.
// [Output] Original route/query/CSRF/error contracts and date-group ordering evidence.
// [Pos] Provider-free native migration checks; no backend, account, storage or model requests.
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {after,test} from 'node:test';
import {build} from 'esbuild';

const frontend = new URL('../../',import.meta.url);
const temporary = await mkdtemp(fileURLToPath(new URL('e2e/native/.history-contract-',frontend)));
after(() => rm(temporary,{recursive:true,force:true}));
await build({
  absWorkingDir:fileURLToPath(frontend),entryPoints:{history:'app/_dream/api/chatHistoryApi.ts',presentation:'app/_dream/components/chat/chatHistoryPresentation.ts'},
  bundle:true,packages:'external',platform:'node',format:'esm',outdir:temporary,logLevel:'silent',
});
const {createChatThread,listChatThreads,deleteChatThread} = await import(pathToFileURL(`${temporary}/history.js`));
const {groupChatThreadsByDate,formatThreadDateLabel} = await import(pathToFileURL(`${temporary}/presentation.js`));
const t = (key,options) => options?.count === undefined ? key : `${key}:${options.count}`;
const thread = (id,date) => ({id,title:id,updated_at:date,created_at:date});
function recorder(status,body) {
  const calls = [];
  return {calls,transport:async (url,init) => {
    calls.push({url:String(url),init});
    return new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json'}});
  }};
}

test('native-injected history uses original filters, trimming, pagination and read cancellation',async () => {
  const read = recorder(200,{threads:[thread('existing','2026-10-28T09:00:00')]});
  const signal = new AbortController().signal;
  const rows = await listChatThreads({deckId:'deck/one',query:'  saved phrase  ',searchScope:'messages',retrievalMode:'auto',limit:21,offset:20},{signal,transport:read.transport});
  assert.equal(rows[0].id,'existing');
  const request = read.calls[0];
  assert.equal(request.url,'/api/claude-agent/threads?deck_id=deck%2Fone&query=saved+phrase&search_scope=messages&retrieval_mode=auto&limit=21&offset=20');
  assert.equal(request.init.signal,signal);
  assert.equal(request.init.headers.authorization,undefined);
  assert.equal(request.init.headers.cookie,undefined);
});
test('original fuzzy/all search defaults and no zero offset remain unchanged',async () => {
  const read = recorder(200,{threads:[]});
  await listChatThreads({query:'x',offset:0},{transport:read.transport});
  assert.equal(read.calls[0].url,'/api/claude-agent/threads?query=x&search_scope=all&retrieval_mode=fuzzy');
});
test('creation preserves optional Deck/Voice/title and thread_id response',async () => {
  const create = recorder(200,{thread_id:'returned-thread'});
  assert.equal(await createChatThread('deck','voice','  User title  ',create.transport),'returned-thread');
  assert.equal(create.calls[0].url,'/api/claude-agent/threads');
  assert.equal(create.calls[0].init.method,'POST');
  assert.deepEqual(JSON.parse(create.calls[0].init.body),{deckId:'deck',voiceId:'voice',title:'User title'});
  const empty = recorder(200,{thread_id:'unbound'});
  await createChatThread(undefined,undefined,undefined,empty.transport);
  assert.deepEqual(JSON.parse(empty.calls[0].init.body),{});
});
test('delete encodes exact Thread identity and retains failure behavior',async () => {
  const remove = recorder(200,{});
  await deleteChatThread('thread/identity',remove.transport);
  assert.equal(remove.calls[0].url,'/api/claude-agent/threads/thread%2Fidentity');
  assert.equal(remove.calls[0].init.method,'DELETE');
  const failure = recorder(403,{detail:'Permission required'});
  await assert.rejects(deleteChatThread('existing',failure.transport),/Permission required/);
  await assert.rejects(listChatThreads({},{transport:failure.transport}),/Permission required/);
  assert.equal(await createChatThread(undefined,undefined,undefined,failure.transport),null);
});
test('Web default fetch path remains available for existing callers',async () => {
  const originalFetch = globalThis.fetch;
  const read = recorder(200,{threads:[]});
  try {
    globalThis.fetch = read.transport;
    await listChatThreads();
    assert.equal(read.calls[0].url,'/api/claude-agent/threads');
  } finally { globalThis.fetch = originalFetch; }
});
test('history groups retain original actor-day boundaries and source order',() => {
  const rows = [thread('today-1','2026-10-28 12:00:00'),thread('yesterday','2026-10-27T23:59:00'),thread('today-2','2026-10-28T08:00:00'),thread('week','2026-10-22T08:00:00'),thread('month','2026-10-20T08:00:00'),thread('earlier','2026-08-01T08:00:00'),thread('invalid','invalid-date')];
  const groups = groupChatThreadsByDate(rows,t,'2026-10-28');
  assert.deepEqual(groups.map(group => [group.label,group.threads.map(row => row.id)]),[
    ['chat.dateGroup.today',['today-1','today-2']],['chat.dateGroup.yesterday',['yesterday']],
    ['chat.dateGroup.last7Days',['week']],['chat.dateGroup.last30Days',['month']],['chat.dateGroup.earlier',['earlier','invalid']],
  ]);
  assert.equal(groups[0].threads[0],rows[0]);
  assert.equal(formatThreadDateLabel('invalid-date',t,'en'),'');
  assert.deepEqual(groupChatThreadsByDate([],t,'2026-10-28'),[]);
});
