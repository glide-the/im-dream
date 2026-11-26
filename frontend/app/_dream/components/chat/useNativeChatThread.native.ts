// [Sync] 2026-11-13: native first/ordinary/queued sends carry their own tool descriptor snapshots.
// [Sync] 2026-11-04: retain native drafts and message identity across safe preparation retries.
// [Sync] 2026-11-03: retain running Thread readers across Native navigation and publish only the visible selection.
// [Sync] 2026-11-03: reuse current/previous saved prose during navigation; fresh status exclusively enables execution controls.
// [Sync] 2026-11-02: restore the selected Thread through original GETs; retire background work even before Thread creation completes.
// [Sync] 2026-11-02: bind queued submission receipts to their selection owner across foreground reader replacement.
// [Sync] 2026-10-31: retire an acknowledged Stop reader epoch and schedule canonical recovery independently of cancelled-reader completion.
// [Sync] 2026-11-01: await cancellable Writing context preparation before any native user-message dispatch; selection changes reject late snapshots.
// [Sync] 2026-10-30: expose original multi-part user DTO submission and document-bound editor result/settlement; composer queue behavior remains.
// [Sync] 2026-10-30: recover after an acknowledged reader cancellation and retain Stopping until original idle; unacknowledged transport failures retain their original path.
// [Sync] 2026-10-30: coalesce adjacent deltas within each received HTTP chunk and commit one ordered projection; preserve control barriers and Stop ownership.
// [Sync] 2026-10-28: preserve queue-edit receipts across reader replacement; selection changes and unmount still reject old UI writes.
// [Sync] 2026-10-28: expose persisted message IDs for the original historical process presentation.
// [Input] Original Chat DTO/context, canonical HTTP transport, native foreground events and caller-owned selection.
// [Output] Selected UI snapshot and retained running Thread data using existing hydration, SSE, queue, confirmation and Stop.
// [Pos] Native lifecycle adapter; the server owns tasks and permissions, navigation retains live readers; AppState and explicit lifecycle release local readers.
// [Sync] 2026-10-28: end the local reader on canonical finish, then reconcile persisted messages/status without waiting for HTTP EOF.
// [Sync] 2026-10-28: retain original queue actions/revisions, edited-draft recovery and side-task receipts without changing the main task.
import {useEffect,useState,useSyncExternalStore} from 'react';
import {AppState} from 'react-native';
import {generateId,isToolUIPart,type UIMessage} from 'ai';
import {clientFetch,openResponse,type OpenResponse} from '../../../../src/platform/transport.native';
import {createChatThread} from '../../api/chatHistoryApi';
import {browserRequestHeaders,getBrowserCsrfToken} from '../../lib/browserSession';
import {createThreadHistoryPreview,threadHistoryPreviewMessages} from './threadHistoryPreview';
import {buildClaudeChatRequest,type ClaudeChatRequestContext} from '../../lib/claude-chat-request';
import {applyBackendEventToMessages,coalesceClaudeAgentSseEvents,drainClaudeAgentSseFrames,parseClaudeAgentSseBuffer,type BackendEvent} from '../../lib/claude-agent-sse-utils';
import {toFileProxyUrl} from '../../lib/toFileProxyUrl';
import {readThreadTools,rememberThreadTools} from '../../hooks/useChatToolSelection';
import type {ChatToolDescriptor,ToolChoice} from '../../lib/chat-schema';
import {toAttachment,type UploadedFile} from './AIInputDock.helpers';
import {hydrateClaudeThreadSession,fetchClaudeThreadMessages,claudeThreadHydrationRetryDelayMs,type ClaudeThreadRecord} from './threadSessionHydration';
import {mergeRecoveredLatestPage,prependUniqueOlderMessages} from './chatHistoryWindow';
import {beginClaudeThreadSubmission,observeClaudeThreadSubmission,requestClaudeSubmittedThreadStop,claudeThreadStopPending,type ClaudeThreadSubmission} from './threadStop';
import {chatStopMayAbortLocalReaders} from './chatRuntimeState';
import {fetchThreadInputs,enqueueThreadInput,selectThreadInput,cancelThreadInput,moveThreadInputToSideTask,ThreadInputError,type ThreadInputEntry} from './threadInputQueue';
import type {ChatUserMessage} from './chatUserMessageIngress';
import {confirmToolCall,resolvePendingToolConfirmation,resolveToolName,resolveSandboxNetworkRequest,type PendingToolConfirmation} from './toolConfirmation';
import type {NativeChatRecovery} from './nativeChatRecovery.native';

const empty=()=>({threadId:null as string|null,thread:undefined as ClaudeThreadRecord|undefined,messages:[] as UIMessage[],historicalMessageIds:new Set<string>() as ReadonlySet<string>,running:false,posting:false,preparing:false,recovering:false,stopping:false,previewing:false,unknown:false,error:null as string|null,
  nextCursor:null as string|null,hasMore:false,loadingOlder:false,queue:[] as ThreadInputEntry[],localOwner:false,queueError:null as string|null,queueChecking:false,editDraftRecovery:null as {id:string;text:string}|null,editRetrying:false,settled:new Set<string>() as ReadonlySet<string>,runtimePending:new Set<string>() as ReadonlySet<string>});
function inputFailureKey(error:unknown):string {
  if(error instanceof ThreadInputError){
    if(error.outcomeUnknown)return 'chat.inputQueue.stateUnknown';
    if(error.status===403||error.status===404)return 'chat.inputQueue.accessDenied';
    if(error.code==='CHAT_INPUT_OWNER_UNAVAILABLE')return 'chat.inputQueue.ownerUnavailable';
    if(error.status===409)return 'chat.inputQueue.stateChanged';
    if(error.status===503)return 'chat.inputQueue.unavailable';
  }
  return error instanceof TypeError?'chat.inputQueue.unavailable':'chat.inputQueue.sendFailed';
}
type NativeChatThreadOptions={context:ClaudeChatRequestContext;prepareEditorState?:(threadId:string|null,signal:AbortSignal)=>Promise<Record<string,unknown>|undefined>;onSettled?:()=>void;onSessionExpired?:()=>void;recovery?:NativeChatRecovery;initialThreadId?:string;transport?:typeof fetch;stream?:typeof openResponse;visible?:boolean};
const box=<T,>(current:T)=>({current});
function createNativeChatThreadSession(options:NativeChatThreadOptions,initialId:string|null,preview:ReturnType<typeof createThreadHistoryPreview>) {
  let {context,prepareEditorState,onSettled,onSessionExpired,recovery,transport:rawTransport=clientFetch,stream=openResponse}=options;
  let state={...empty(),threadId:initialId,recovering:Boolean(initialId),previewing:Boolean(initialId),unknown:Boolean(initialId),messages:threadHistoryPreviewMessages(initialId?preview.read(initialId):undefined)};
  const current=box(state),historyPreview=box(preview);
  const listeners=new Set<()=>void>();
  let queueTimer:ReturnType<typeof setInterval>|undefined,queueInFlight=false;
  function setState(patch:typeof state|((value:typeof state)=>typeof state)) {
    const previousId=state.threadId;
    state=typeof patch==='function'?patch(state):patch;current.current=state;snapshotCache=undefined;
    if(previousId!==state.threadId&&mounted.current)restartQueue();
    for(const notify of listeners)notify();
  }
  const continuationIds=box(new Map<string,string>());
  const latest=box({context,prepareEditorState,onSettled,onSessionExpired});latest.current={context,prepareEditorState,onSettled,onSessionExpired};
  const transport:typeof fetch=async(input,init)=>{const response=await rawTransport(input,init);if(response.status===401&&mounted.current){historyPreview.current?.clear();update({messages:[],thread:undefined,unknown:true});latest.current.onSessionExpired?.();}return response;};
  const mounted=box(false),epoch=box(0),selectionEpoch=box(0),connection=box<OpenResponse|null>(null),postLock=box<number|null>(null);
  const livePresentedTurnIds=box(new Set<string>());
  const acknowledgedReaderStops=box(new WeakSet<OpenResponse>());
  const contextPreparations=box(new Set<AbortController>());
  const timer=box<ReturnType<typeof setTimeout>|undefined>(undefined),attempt=box(0),queueIds=box(new Map<string,string>()),olderLock=box(false);
  function update(patch:Partial<typeof state>|((value:typeof state)=>typeof state)) {if(!mounted.current)return;setState(value=>{const next=typeof patch==='function'?patch(value):{...value,...patch};current.current=next;return next;});}
  function active(id:string,version:number) {return mounted.current && epoch.current===version && current.current.threadId===id;}
  function ownsSelection(id:string,version:number) {return mounted.current && selectionEpoch.current===version && current.current.threadId===id;}
  function closeReader(acknowledgedStop=false) {for(const pending of contextPreparations.current)pending.abort();contextPreparations.current.clear();if(acknowledgedStop && connection.current)acknowledgedReaderStops.current.add(connection.current);connection.current?.cancel();connection.current=null;if(timer.current)clearTimeout(timer.current);timer.current=undefined;}
  function newChat() {selectionEpoch.current++;epoch.current++;closeReader();queueIds.current.clear();livePresentedTurnIds.current.clear();recovery?.selectThread(null);update(empty());}
  async function refreshQueue(id=current.current.threadId) {
    if(!id)return;const version=epoch.current;
    const snapshot=await fetchThreadInputs(id,undefined,transport);
    if(active(id,version))update({queue:snapshot.entries,localOwner:snapshot.local_owner});
  }
  function schedule(id:string,version:number) {
    if(!active(id,version) || AppState.currentState==='background')return;
    if(timer.current)clearTimeout(timer.current);
    timer.current=setTimeout(()=>{timer.current=undefined;void recover(id,version);},claudeThreadHydrationRetryDelayMs(attempt.current++));
  }
  async function consume(id:string,version:number,response:OpenResponse,submission?:ClaudeThreadSubmission) {
    if(!active(id,version)){response.cancel();return;}
    if(response.status!==200){response.cancel();if(response.status===401)latest.current.onSessionExpired?.();if(submission)observeClaudeThreadSubmission(submission,'rejected');throw new Error('CHAT_HTTP_REJECTED');}
    connection.current=response;
    let buffer='',terminal=false,preparationRejected=false,submissionFailed=false;
    const dispatch=(frames:string)=>{
      const events:BackendEvent[]=[];
      for(const event of coalesceClaudeAgentSseEvents(parseClaudeAgentSseBuffer(frames))) {
        if(submission)observeClaudeThreadSubmission(submission,event.type==='finish'?'terminal':'accepted');
        if(event.type==='error'){submissionFailed=true;if(event.retryable===true)preparationRejected=true;}
        events.push(event);
        if(event.type==='finish'){terminal=true;break;}
      }
      if(events.length && active(id,version))update(value=>{const projected=events.reduce((next,event)=>({...next,
        messages:applyBackendEventToMessages(next.messages,event),
        ...(event.type==='data-continuation'?{preparing:event.state==='preparing'}:{}),
        ...(event.type==='error'?{error:event.retryable===true?'chat.continuation.failed':'chat.turnNavigation.status.failed',preparing:false}:{}),
        ...(event.type==='finish'?{preparing:false}:{}),
        ...(event.type==='tool-approval-request'?{settled:new Set([...next.settled].filter(toolId=>toolId!==event.toolCallId))}:{}),
      }),value);for(const message of projected.messages){const metadata=message.metadata as {turnId?:unknown}|undefined;if(message.role==='assistant'&&!value.historicalMessageIds.has(message.id)&&typeof metadata?.turnId==='string'&&metadata.turnId)livePresentedTurnIds.current.add(metadata.turnId);}return projected;});
    };
    try {
      for await(const chunk of response.chunks) {
        if(!active(id,version))break;
        const drained=drainClaudeAgentSseFrames(buffer+chunk);buffer=drained.buffer;
        if(drained.frames.length)dispatch(drained.frames.join('\n\n')+'\n\n');
        if(terminal)break;
      }
      if(!terminal && buffer.trim() && active(id,version))dispatch(buffer);
      if(submissionFailed)throw Object.assign(new Error('CHAT_SUBMISSION_FAILED'),{continuationRejected:preparationRejected});
    } catch(error) {if(!acknowledgedReaderStops.current.has(response))throw error;}
    finally {acknowledgedReaderStops.current.delete(response);response.cancel();if(connection.current===response)connection.current=null;}
  }
  async function recover(id:string,version=epoch.current) {
    if(!active(id,version))return;
    update({recovering:true});
    try {
      const requestScope=getBrowserCsrfToken();
      const snapshot=await hydrateClaudeThreadSession(id,transport,{
        previousHistory:historyPreview.current?.read(id),
        onHistory:history=>{
          if(!active(id,version)||requestScope!==getBrowserCsrfToken())return;
          // A live reader retains its richer current projection until reconciliation.
          if(current.current.previewing)update({messages:threadHistoryPreviewMessages(history),thread:history.thread});
        },
      });
      if(!active(id,version))return;
      if(requestScope!==getBrowserCsrfToken()){update({messages:[],thread:undefined});throw Error('CHAT_SESSION_CHANGED');}
      historyPreview.current?.remember(id,snapshot,requestScope);
      const stopPending=claudeThreadStopPending(id);
      update(value=>{const merged=value.previewing?{messages:snapshot.messages,overlapsLoadedWindow:false}:mergeRecoveredLatestPage(value.messages,snapshot.messages,livePresentedTurnIds.current);return {...value,thread:snapshot.thread,messages:merged.messages,historicalMessageIds:new Set([...value.historicalMessageIds,...snapshot.messages.map(message=>message.id)]),running:snapshot.running || stopPending,
        recovering:false,posting:false,previewing:false,unknown:stopPending,error:value.error==='chat.turnNavigation.status.failed'?value.error:null,settled:snapshot.settledToolCallIds,runtimePending:snapshot.runtimePendingToolCallIds,
        nextCursor:!value.previewing&&merged.overlapsLoadedWindow?value.nextCursor:snapshot.nextCursor,hasMore:!value.previewing&&merged.overlapsLoadedWindow?value.hasMore:snapshot.hasMore};});
      void refreshQueue(id).catch(()=>{});
      if(snapshot.running) {
        await consume(id,version,await stream(`/api/claude-agent/threads/${encodeURIComponent(id)}/stream`,{headers:browserRequestHeaders()}));
        schedule(id,version);
      } else if(stopPending) {schedule(id,version);}
      else {attempt.current=0;update({stopping:false});latest.current.onSettled?.();}
    } catch(cause) {
      if(active(id,version)){historyPreview.current?.forget(id);const denied=Boolean(cause&&typeof cause==='object'&&'httpStatus' in cause&&[401,403,404].includes(Number(cause.httpStatus)));update({recovering:false,unknown:true,error:'chat.inputQueue.stateUnknown',...(denied?{messages:[],thread:undefined}:{})});schedule(id,version);}
    }
  }
  async function openThread(id:string) {
    if(current.current.threadId===id && !current.current.unknown)return;
    selectionEpoch.current++;epoch.current++;closeReader();queueIds.current.clear();livePresentedTurnIds.current.clear();const version=epoch.current;
    recovery?.selectThread(id);
    const preview=historyPreview.current?.read(id);
    current.current={...empty(),threadId:id,recovering:true,previewing:true,unknown:true,messages:threadHistoryPreviewMessages(preview)};setState(current.current);
    await recover(id,version);
  }
  async function send(text:string,files:UploadedFile[]=[],toolChoice:ToolChoice='auto',tools:readonly ChatToolDescriptor[]=current.current.threadId?readThreadTools(current.current.threadId):[]) {
    const before=current.current;
    if((postLock.current===epoch.current && !before.threadId) || before.stopping || (before.threadId && claudeThreadStopPending(before.threadId)))throw new Error('CHAT_STOP_PENDING');
    if(before.unknown || before.queue.some(entry=>entry.status==='state_unknown')){update({error:'chat.inputQueue.stateUnknown'});throw new Error('CHAT_OUTCOME_UNKNOWN');}
    const selected={...latest.current.context,currentToolChoice:toolChoice,tools:tools.map(tool=>({...tool}))};
    const effective=selected.imFullAccessEnabled?'auto':toolChoice;
    if(before.threadId && (before.running || before.posting || before.localOwner)) {
      if(files.length){update({error:'chat.inputQueue.textOnly'});throw new Error('CHAT_INPUT_UNSUPPORTED_PAYLOAD');}
      const input=text.trim();if(!input)return;
      const selectionVersion=selectionEpoch.current;
      const messageId=queueIds.current.get(input) ?? generateId();queueIds.current.set(input,messageId);
      try {
        const entry=await enqueueThreadInput(before.threadId,messageId,input,effective,selected.deckId,selected.voiceId,transport,selected.tools);
        if(ownsSelection(before.threadId,selectionVersion)){
          queueIds.current.delete(input);update(value=>({...value,error:null,queue:[...value.queue.filter(item=>item.message_id!==entry.message_id),entry]}));
          void refreshQueue(before.threadId).catch(()=>{});
        }
        return;
      } catch(error){if(ownsSelection(before.threadId,selectionVersion))update({error:error instanceof ThreadInputError && error.outcomeUnknown?'chat.inputQueue.stateUnknown':'chat.inputQueue.sendFailed'});throw error;}
    }
    const parts:UIMessage['parts']=files.filter(file=>file.storageKey).map(file=>({type:'file',url:toFileProxyUrl(file.storageKey!),mediaType:file.mimeType,filename:file.name}));
    if(text)parts.push({type:'text',text});if(!parts.length)return;
    return submitMessage({role:'user',parts},files,toolChoice,tools);
  }
  async function submitMessage(outgoing:ChatUserMessage,files:UploadedFile[]=[],toolChoice:ToolChoice='auto',tools:readonly ChatToolDescriptor[]=current.current.threadId?readThreadTools(current.current.threadId):[]) {
    const before=current.current;
    if(!outgoing.parts?.length)return;
    if((postLock.current===epoch.current&&!before.threadId)||before.stopping||(before.threadId&&claudeThreadStopPending(before.threadId)))throw Error('CHAT_STOP_PENDING');
    if(before.unknown||before.queue.some(entry=>entry.status==='state_unknown'))throw Error('CHAT_OUTCOME_UNKNOWN');
    const selected={...latest.current.context,currentToolChoice:toolChoice,tools:tools.map(tool=>({...tool}))},effective=selected.imFullAccessEnabled?'auto':toolChoice;
    if(before.threadId)historyPreview.current?.forget(before.threadId);
    postLock.current=epoch.current;update({posting:true,error:null});
    let id=before.threadId,dispatched=false,rejected=false,submission:ClaudeThreadSubmission|undefined;const version=epoch.current;
    const preparation=new AbortController();
    try {
      if(latest.current.prepareEditorState){
        contextPreparations.current.add(preparation);
        selected.editorState=await latest.current.prepareEditorState(before.threadId,preparation.signal);
        if(preparation.signal.aborted||epoch.current!==version||!mounted.current)throw new Error('CHAT_SELECTION_CHANGED');
      }
      id ??= await createChatThread(selected.deckId,selected.voiceId,undefined,transport);
      if(!id)throw new Error('CHAT_THREAD_CREATE_FAILED');
      if(epoch.current!==version || !mounted.current)throw new Error('CHAT_SELECTION_CHANGED');
      if(!before.threadId)rememberThreadTools(id,selected.tools);
      const retryKey=JSON.stringify([id,outgoing.parts,files.map(file=>file.storageKey),effective,selected.tools]);
      const message:UIMessage={...outgoing,id:outgoing.id??continuationIds.current.get(retryKey)??generateId(),role:'user'};
      continuationIds.current.set(retryKey,message.id);
      submission=beginClaudeThreadSubmission(id,message.id);
      current.current={...current.current,threadId:id,posting:true,running:true,messages:[...current.current.messages,message]};setState(current.current);
      recovery?.rememberThread(id);
      const body=buildClaudeChatRequest({id,message,context:selected,attachments:files.map(toAttachment),toolChoice:effective});
      submission.dispatched=true;dispatched=true;
      const response=await stream('/api/claude-agent',{method:'POST',headers:{...browserRequestHeaders(),'Content-Type':'application/json'},body:JSON.stringify(body)});
      rejected=response.status!==200;
      await consume(id,version,response,submission);
      continuationIds.current.delete(retryKey);
      if(active(id,version)){update({posting:false});await recover(id,version);}
    } catch(error) {
      if(error && typeof error==='object' && 'continuationRejected' in error && error.continuationRejected===true)rejected=true;
      if(submission)observeClaudeThreadSubmission(submission,rejected || !dispatched?'rejected':'unknown');
      if(epoch.current===version && mounted.current) {
        update({posting:false,preparing:false,running:dispatched && !rejected,unknown:dispatched && !rejected,error:rejected?'chat.continuation.failed':dispatched?'chat.inputQueue.stateUnknown':'chat.history.createFailed'});
        if(id && dispatched && !rejected)schedule(id,version);
        else if(submission)update(value=>({...value,messages:value.messages.filter(message=>message.id!==submission?.messageId)}));
      }
      throw error;
    } finally {contextPreparations.current.delete(preparation);if(postLock.current===version)postLock.current=null;}
  }
  function settleToolCall(toolCallId:string,expectedThreadId=current.current.threadId) {
    update(value=>value.threadId!==expectedThreadId?value:({...value,settled:new Set([...value.settled,toolCallId]),runtimePending:new Set([...value.runtimePending].filter(id=>id!==toolCallId))}));
  }
  function addToolResult({tool,toolCallId,output}:{tool:string;toolCallId:string;output:unknown},expectedThreadId=current.current.threadId) {
    update(value=>value.threadId!==expectedThreadId?value:({...value,messages:value.messages.map(message=>({...message,parts:message.parts.map(part=>isToolUIPart(part)&&part.toolCallId===toolCallId&&resolveToolName(part)===tool&&part.state!=='output-error'&&part.state!=='output-available'?{...part,approval:undefined,errorText:undefined,input:'input' in part?part.input:undefined,state:'output-available' as const,output}:part)}))}));
  }
  async function stop() {
    const id=current.current.threadId;if(!id || current.current.stopping)return;
    const version=epoch.current;update({stopping:true,running:true});
    let waitingForIdle=false,recoveryVersion=version;
    try {
      const receipt=await requestClaudeSubmittedThreadStop(id,transport);
      if(!active(id,version))return;
      waitingForIdle=receipt.running;
      if(!claudeThreadStopPending(id) && chatStopMayAbortLocalReaders(receipt.stopRequested,receipt.running)){
        // An in-flight native read can settle after Stop and after the idle snapshot.
        // Retire its projection owner before independently recovering this Thread.
        recoveryVersion=++epoch.current;closeReader(true);
      }
    } catch {if(active(id,version))update({unknown:true,error:'chat.inputQueue.stateUnknown'});}
    finally {if(active(id,recoveryVersion)){update({stopping:waitingForIdle});schedule(id,recoveryVersion);}}
  }
  async function loadOlder() {
    const before=current.current;if(!before.threadId || !before.nextCursor || olderLock.current)return;
    olderLock.current=true;const version=epoch.current;update({loadingOlder:true});
    try {const page=await fetchClaudeThreadMessages(before.threadId,{cursor:before.nextCursor},transport);
      if(active(before.threadId,version))update(value=>({...value,messages:prependUniqueOlderMessages(value.messages,page.messages),historicalMessageIds:new Set([...value.historicalMessageIds,...page.messages.map(message=>message.id)]),nextCursor:page.nextCursor,hasMore:page.hasMore}));
    } catch {if(active(before.threadId,version))update({error:'chat.activity.historyFailed'});}
    finally {olderLock.current=false;if(active(before.threadId,version))update({loadingOlder:false});}
  }
  function readConfirmation():PendingToolConfirmation|null {

    if(state.unknown)return null;
    for(const message of state.messages)for(const [index,part] of message.parts.entries())if(isToolUIPart(part)) {
      const kind=resolvePendingToolConfirmation(part,latest.current.context.imFullAccessEnabled?'auto':latest.current.context.currentToolChoice,state.settled,state.runtimePending);
      if(kind)return {kind,partKey:`${message.id}-${index}`,toolCallId:part.toolCallId,toolName:resolveToolName(part),input:'input' in part?part.input:undefined,networkRequest:kind==='sandbox-network'?resolveSandboxNetworkRequest(part):undefined};
    }
    return null;
  }
  async function confirm(approved:boolean,reason?:string,answers?:Record<string,unknown>) {
    const confirmation=readConfirmation();const id=current.current.threadId;if(!id || !confirmation)return;
    const version=epoch.current,result=await confirmToolCall(id,confirmation.toolCallId,approved,reason,answers,transport);
    if(!active(id,version))return;
    if(result.state==='error')throw new Error('TOOL_CONFIRMATION_FAILED');
    update(value=>({...value,settled:new Set([...value.settled,confirmation.toolCallId]),runtimePending:new Set([...value.runtimePending].filter(value=>value!==confirmation.toolCallId))}));
  }
  async function checkQueue() {
    const id=current.current.threadId;if(!id)return;const version=epoch.current;update({queueChecking:true});
    try{await refreshQueue(id);if(active(id,version))update({queueError:null});}
    catch(error){if(active(id,version))update({queueError:inputFailureKey(error)});}
    finally{if(active(id,version))update({queueChecking:false});}
  }
  function inputThread(entry:ThreadInputEntry):string {
    const id=current.current.threadId;
    if(!id||entry.thread_id!==id)throw new ThreadInputError('CHAT_INPUT_THREAD_CHANGED',409);
    return id;
  }
  async function guide(entry:ThreadInputEntry) {
    const id=inputThread(entry),version=epoch.current;
    try{const receipt=await selectThreadInput(id,entry,transport);if(active(id,version))update(value=>({...value,queue:value.queue.map(item=>item.message_id===entry.message_id?receipt.entry:item),queueError:receipt.interrupt_signalled?null:'chat.inputQueue.guideFailed'}));await refreshQueue(id);}
    catch(error){if(active(id,version)){update({queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}throw error;}
  }
  async function cancelInput(entry:ThreadInputEntry) {
    const id=inputThread(entry),version=epoch.current;
    try{const receipt=await cancelThreadInput(id,entry,transport);if(active(id,version))update(value=>({...value,queue:value.queue.map(item=>item.message_id===entry.message_id?receipt:item),queueError:null}));await refreshQueue(id);}
    catch(error){if(active(id,version)){update({queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}throw error;}
  }
  async function editInput(entry:ThreadInputEntry,text:string) {
    const id=inputThread(entry),version=selectionEpoch.current,selected={...latest.current.context};
    await cancelInput(entry);
    const messageId=generateId();
    try{await enqueueThreadInput(id,messageId,text,selected.imFullAccessEnabled?'auto':selected.currentToolChoice,selected.deckId,selected.voiceId,transport,readThreadTools(id));if(ownsSelection(id,version))update({editDraftRecovery:null,queueError:null});await refreshQueue(id);}
    catch(error){if(ownsSelection(id,version)){update({editDraftRecovery:{id:messageId,text},queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}throw error;}
  }
  async function retryEditedInput() {
    const id=current.current.threadId,draft=current.current.editDraftRecovery;if(!id||!draft||current.current.editRetrying)return;
    const version=selectionEpoch.current,selected={...latest.current.context};update({editRetrying:true});
    try{await enqueueThreadInput(id,draft.id,draft.text,selected.imFullAccessEnabled?'auto':selected.currentToolChoice,selected.deckId,selected.voiceId,transport,readThreadTools(id));if(ownsSelection(id,version))update({editDraftRecovery:null,queueError:null});await refreshQueue(id);}
    catch(error){if(ownsSelection(id,version)){update({queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}}
    finally{if(ownsSelection(id,version))update({editRetrying:false});}
  }
  async function sideTask(entry:ThreadInputEntry) {
    const id=inputThread(entry),version=epoch.current;
    try{const task=await moveThreadInputToSideTask(id,entry,transport);await refreshQueue(id);if(active(id,version))update({queueError:task.error_code?'chat.inputQueue.sideChatLaunchFailed':null});return task;}
    catch(error){if(active(id,version)){update({queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}throw error;}
  }
  let listener:ReturnType<typeof AppState.addEventListener>|undefined;
  function restartQueue() {
    if(queueTimer)clearInterval(queueTimer);
    const read=async()=>{if(queueInFlight||!mounted.current||AppState.currentState==='background')return;queueInFlight=true;try{await refreshQueue();}catch{/* Keep the last queue snapshot; explicit actions own failure feedback. */}finally{queueInFlight=false;}};
    void read();queueTimer=setInterval(()=>void read(),2000);
  }
  function start() {
    if(mounted.current)return;mounted.current=true;
    const restored=current.current.threadId;if(restored)void recover(restored,epoch.current);
    listener=AppState.addEventListener('change',next=>{const id=current.current.threadId;
      if(next==='active'&&id){epoch.current++;closeReader();void recover(id,epoch.current);}
      else if(next==='background'){epoch.current++;closeReader();update({posting:false,recovering:false,unknown:Boolean(id)});}
    });
    restartQueue();
  }
  function dispose() {mounted.current=false;selectionEpoch.current++;epoch.current++;closeReader();listener?.remove();listener=undefined;if(queueTimer)clearInterval(queueTimer);queueTimer=undefined;}
  function configure(next:NativeChatThreadOptions) {
    const confirmationChanged=context.imFullAccessEnabled!==next.context.imFullAccessEnabled||context.currentToolChoice!==next.context.currentToolChoice;
    ({context,prepareEditorState,onSettled,onSessionExpired,recovery,transport:rawTransport=clientFetch,stream=openResponse}=next);
    latest.current={context,prepareEditorState,onSettled,onSessionExpired};if(confirmationChanged)snapshotCache=undefined;
  }
  const actions={invalidateHistory:(id:string)=>historyPreview.current?.forget(id),newChat,openThread,send,sendUserMessage:(message:ChatUserMessage,expectedThreadId=current.current.threadId)=>{if(current.current.threadId!==expectedThreadId)return Promise.reject(Error('CHAT_THREAD_CHANGED'));return submitMessage(message);},addToolResult,settleToolCall,stop,loadOlder,confirm,guide,cancelInput,editInput,retryEditedInput,checkQueue,sideTask,refreshQueue,retry:()=>{const id=current.current.threadId;if(id){epoch.current++;closeReader();void recover(id,epoch.current);}}};
  type Snapshot=typeof state&typeof actions&{confirmation:PendingToolConfirmation|null};
  let snapshotCache:Snapshot|undefined;
  return {start,dispose,configure,subscribe:(notify:()=>void)=>{listeners.add(notify);return()=>{listeners.delete(notify);};},
    snapshot:():Snapshot=>snapshotCache??=( {...state,confirmation:readConfirmation(),...actions}),
    live:()=>state.running||state.stopping||connection.current!==null,
    departSelection:()=>{selectionEpoch.current++;update({editDraftRecovery:null,editRetrying:false});},
    expire:()=>{closeReader();update({messages:[],thread:undefined,unknown:true});}};
}

function createNativeChatThreadOwner(initial:NativeChatThreadOptions) {
  type Session=ReturnType<typeof createNativeChatThreadSession>;
  let options=initial,visible=initial.visible!==false,started=false,scope=getBrowserCsrfToken();
  const preview=createThreadHistoryPreview(),sessions=new Set<Session>(),listeners=new Set<()=>void>();
  let selected:Session;
  function notify() {for(const listener of listeners)listener();}
  function forget(session:Session) {sessions.delete(session);session.dispose();}
  function owned(session:Session):NativeChatThreadOptions {
    const recovery=options.recovery;
    return {...options,recovery:recovery?{...recovery,selectThread:id=>{if(selected===session)recovery.selectThread(id);},rememberThread:id=>{if(selected===session)recovery.rememberThread(id);}}:undefined,
      onSessionExpired:()=>{if(!sessions.has(session))return;for(const other of sessions)if(other!==selected)forget(other);preview.clear();selected.expire();options.onSessionExpired?.();}};
  }
  function create(id:string|null) {
    const session=createNativeChatThreadSession(options,id,preview);sessions.add(session);session.configure(owned(session));
    session.subscribe(()=>{if(synchronizeScope())return;if(session===selected){if(visible)notify();}else if(!session.live())forget(session);});
    return session;
  }
  selected=create(initial.initialThreadId??initial.recovery?.read().threadId??null);
  let base=selected.snapshot(),published={...base,newChat,openThread,invalidateHistory};
  function synchronizeScope() {
    const next=getBrowserCsrfToken();if(next===scope)return false;scope=next;
    const id=selected.snapshot().threadId;
    for(const session of sessions)session.dispose();sessions.clear();preview.clear();selected=create(id);base=selected.snapshot();published={...base,newChat,openThread,invalidateHistory};
    if(started){const target=selected;queueMicrotask(()=>{if(selected===target&&started)target.start();});}
    notify();return true;
  }
  function select(next:Session) {
    const previous=selected;previous.departSelection();selected=next;
    if(!previous.live())forget(previous);
    if(started)next.start();notify();
  }
  function newChat() {synchronizeScope();select(create(null));options.recovery?.selectThread(null);}
  async function openThread(id:string) {
    synchronizeScope();const current=selected.snapshot();
    if(current.threadId===id)return selected.snapshot().openThread(id);
    const retained=[...sessions].find(session=>session.snapshot().threadId===id);
    select(retained??create(id));options.recovery?.selectThread(id);
  }
  function invalidateHistory(id:string) {preview.forget(id);for(const session of sessions)if(session!==selected&&session.snapshot().threadId===id)forget(session);}
  return {
    configure(next:NativeChatThreadOptions) {options=next;const wasVisible=visible;visible=next.visible!==false;selected.configure(owned(selected));if(wasVisible&&!visible){base=selected.snapshot();published={...base,newChat,openThread,invalidateHistory};}},
    snapshot() {synchronizeScope();if(!visible)return published;const next=selected.snapshot();if(next!==base){base=next;published={...next,newChat,openThread,invalidateHistory};}return published;},
    subscribe(listener:()=>void) {listeners.add(listener);return()=>{listeners.delete(listener);};},
    start() {started=true;selected.start();return()=>{started=false;for(const session of sessions)session.dispose();for(const session of sessions)if(session!==selected)sessions.delete(session);};},
  };
}

export default function useNativeChatThread(options:NativeChatThreadOptions) {
  const [owner]=useState(()=>createNativeChatThreadOwner(options));owner.configure(options);
  const snapshot=useSyncExternalStore(owner.subscribe,owner.snapshot,owner.snapshot);
  useEffect(()=>owner.start(),[owner]);
  return snapshot;
}
