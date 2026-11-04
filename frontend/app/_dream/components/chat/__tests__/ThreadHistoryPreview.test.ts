// [Input] Successful history snapshots, session replacement and the existing history/status hydration primitive.
// [Output] Bounded preview ownership, prose-only projection, conditional reuse and execution-state ordering contracts.
// [Pos] Provider-free source tests; no backend, account or model calls.
import {test,expect} from '@playwright/test';
import {createThreadHistoryPreview,threadHistoryPreviewMessages} from '../threadHistoryPreview';
import {hydrateClaudeThreadSession,type ClaudeThreadHistorySnapshot} from '../threadSessionHydration';
import {clearBrowserSession,loadBrowserSession,getBrowserCsrfToken} from '../../../lib/browserSession';
const history=(id:string):ClaudeThreadHistorySnapshot=>({thread:{id,title:id,created_at:'2026-11-03T00:00:00Z',updated_at:'2026-11-03T00:00:00Z'},messages:[{id:id+'1',role:'assistant',metadata:{historyProjectionVersion:1,historyProcessAvailable:true,turnId:'saved-turn',turnStatus:'completed',finalPartIndex:1},parts:[{type:'text',text:id},{type:'dynamic-tool',toolName:'example',toolCallId:'tool',state:'input-available',input:{}}]}],latestMessageId:id+'1',hasMore:true,nextCursor:'older-'+id,unchanged:false,dispatchStatusByMessageId:{}});
async function session(scope='a',id='1'){await loadBrowserSession(async()=>Response.json({user:{id,email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:scope.repeat(43)}));}
test.afterEach(()=>clearBrowserSession());
test('current and previous Thread previews stay bounded and cannot cross session replacement or late writes',async()=>{
 await session();const cache=createThreadHistoryPreview(),scope=getBrowserCsrfToken();
 cache.remember('A',{...history('A'),...{running:true}},scope);expect(cache.read('A')).not.toHaveProperty('running');cache.remember('B',history('B'),scope);expect(cache.read('A')?.thread?.id).toBe('A');
 cache.remember('C',history('C'),scope);expect(cache.read('A')).toBeUndefined();expect(cache.read('B')?.thread?.id).toBe('B');
 cache.forget('B');expect(cache.read('B')).toBeUndefined();
 await session('b','2');expect(cache.read('C')).toBeUndefined();cache.remember('C',history('C'),scope);expect(cache.read('C')).toBeUndefined();
 cache.remember('C',history('C'),getBrowserCsrfToken());clearBrowserSession();expect(cache.read('C')).toBeUndefined();
});
test('preview exposes saved prose and keeps tool hosts and runtime approvals outside the preview',()=>{
 expect(threadHistoryPreviewMessages(history('A'))).toEqual([{id:'A1',role:'assistant',parts:[{type:'text',text:'A'}]}]);
});
test('fresh conditional history precedes status and idle stabilization; cached running state is never adopted',async()=>{
 const previous=history('A'),order:string[]=[];const pages:string[]=[];
 const result=await hydrateClaudeThreadSession('A',async(input)=>{
  const url=new URL(String(input),'http://fixture.invalid');order.push(url.pathname.endsWith('/status')?'status':'history');
  if(url.pathname.endsWith('/status'))return Response.json({running:false,lifecycle:'idle',turn_count:1,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
  expect(url.searchParams.get('known_latest_message_id')).toBe('A1');
  return Response.json({thread:previous.thread,messages:[],latest_message_id:'A1',has_more:false,next_cursor:null,unchanged:true});
 },{previousHistory:previous,onHistory:page=>{pages.push(page.messages[0].id);order.push('preview');}});
 expect(order).toEqual(['history','preview','status','history']);expect(pages).toEqual(['A1']);expect(result.messages).toEqual(previous.messages);expect(result.running).toBe(false);expect(result.nextCursor).toBe('older-A');
});
test('an unchanged result with a different latest identity fails closed',async()=>{
 await expect(hydrateClaudeThreadSession('A',async()=>Response.json({thread:history('A').thread,messages:[],latest_message_id:'B1',has_more:false,next_cursor:null,unchanged:true}),{previousHistory:history('A')})).rejects.toThrow('revision mismatch');
});
