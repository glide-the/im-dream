// [Input] Production Writing document DTO validation and its cancellable context request owner.
// [Output] Reject stale document/Session/request results, timeout and cancelled saves without accepting a wrong note snapshot.
// [Pos] Provider-free Writing-to-native Chat protocol behavior coverage.
// [Sync] 2026-11-01: qualify A/B/A identities, schema rejection, document replacement and cancellation before native dispatch.
import {expect,test} from '@playwright/test';
import {readWritingEvent,readWritingState,WritingContextRequests,type WritingContextRequest} from '../Editor/WritingDocument.protocol';
const state={type:'state',documentId:'doc',revision:1,active:true,theme:'light',language:'en',showEnergyBar:true};
const event=(sessionId:string,requestId:string,documentId='doc')=>({type:'chat-context' as const,documentId,sessionId,requestId,editorState:{id:sessionId,cells:[]}});
test('Writing context DTOs reject incomplete identities and a snapshot belonging to another note',()=>{
 expect(readWritingState({...state,contextRequest:{requestId:'one',sessionId:'A'}})).not.toBeNull();
 for(const contextRequest of [null,{},'one',{requestId:'',sessionId:'A'},{requestId:'one',sessionId:1}])expect(readWritingState({...state,contextRequest})).toBeNull();
 expect(readWritingEvent(JSON.stringify(event('A','one')))).toMatchObject({editorState:{id:'A'}});
 for(const bad of [{...event('A','one'),editorState:{id:'B',cells:[]}},{...event('A','one'),editorState:{id:'A'}},{...event('A','one'),requestId:''},{type:'open-thread',documentId:'doc',threadId:'t',editorSessionId:5}])expect(readWritingEvent(JSON.stringify(bad))).toBeNull();
 expect(readWritingEvent(JSON.stringify({type:'open-thread',documentId:'doc',threadId:'t'}))).not.toBeNull();
});
test('A/B/A requests reject old receipts even when the Thread is shared',async()=>{
 let request:WritingContextRequest|undefined;
 const bridge=new WritingContextRequests(value=>{request=value;});bridge.attach('doc');
 for(const sessionId of ['A','B','A']){
  const result=bridge.prepare('doc',sessionId,new AbortController().signal);const sent={...request!};let settled=false;void result.then(()=>{settled=true;});
  bridge.receive(event(sessionId,'stale'));bridge.receive(event('other',sent.requestId));bridge.receive(event(sessionId,sent.requestId,'old-document'));
  await Promise.resolve();expect(settled).toBe(false);
  bridge.receive(event(sessionId,sent.requestId));expect(await result).toEqual({id:sessionId,cells:[]});expect(request).toBeUndefined();
 }
 bridge.attach('');
});
test('cancellation, document replacement, save errors and timeout reject the pending send',async()=>{
 let request:WritingContextRequest|undefined;
 const bridge=new WritingContextRequests(value=>{request=value;},10);bridge.attach('doc');
 const abort=new AbortController(),cancelled=bridge.prepare('doc','A',abort.signal);const cancellation=expect(cancelled).rejects.toThrow('CANCELLED');abort.abort();await cancellation;
 const replaced=bridge.prepare('doc','A',new AbortController().signal);const replacement=expect(replaced).rejects.toThrow('CANCELLED');bridge.attach('new-doc');await replacement;
 await expect(bridge.prepare('doc','A',new AbortController().signal)).rejects.toThrow('UNAVAILABLE');
 const failed=bridge.prepare('new-doc','B',new AbortController().signal);const failure=expect(failed).rejects.toThrow('REJECTED');bridge.receive({type:'chat-context-error',documentId:'new-doc',...request!,code:'save-failed'});await failure;
 const timedOut=bridge.prepare('new-doc','B',new AbortController().signal);await expect(timedOut).rejects.toThrow('TIMEOUT');expect(request).toBeUndefined();bridge.attach('');
});
