// [Sync] 2026-10-28: preserve queue-edit receipts across reader replacement; selection changes and unmount still reject old UI writes.
// [Sync] 2026-10-28: expose persisted message IDs for the original historical process presentation.
// [Input] Original Chat DTO/context, canonical HTTP transport, native foreground events and caller-owned selection.
// [Output] One active Thread using existing hydration, SSE projection, input queue, confirmation and submission-owned Stop.
// [Pos] Native lifecycle adapter; the server owns tasks and permissions, navigation only cancels local readers.
// [Sync] 2026-10-28: end the local reader on canonical finish, then reconcile persisted messages/status without waiting for HTTP EOF.
// [Sync] 2026-10-28: retain original queue actions/revisions, edited-draft recovery and side-task receipts without changing the main task.
import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {AppState} from 'react-native';
import {generateId,isToolUIPart,type UIMessage} from 'ai';
import {clientFetch,openResponse,type OpenResponse} from '../../../../src/platform/transport.native';
import {createChatThread} from '../../api/chatHistoryApi';
import {browserRequestHeaders} from '../../lib/browserSession';
import {buildClaudeChatRequest,type ClaudeChatRequestContext} from '../../lib/claude-chat-request';
import {applyBackendEventToMessages,drainClaudeAgentSseFrames,parseClaudeAgentSseBuffer} from '../../lib/claude-agent-sse-utils';
import {toFileProxyUrl} from '../../lib/toFileProxyUrl';
import type {ToolChoice} from '../../lib/chat-schema';
import {toAttachment,type UploadedFile} from './AIInputDock.helpers';
import {hydrateClaudeThreadSession,fetchClaudeThreadMessages,claudeThreadHydrationRetryDelayMs,type ClaudeThreadRecord} from './threadSessionHydration';
import {mergeRecoveredLatestPage,prependUniqueOlderMessages} from './chatHistoryWindow';
import {beginClaudeThreadSubmission,observeClaudeThreadSubmission,requestClaudeSubmittedThreadStop,claudeThreadStopPending,type ClaudeThreadSubmission} from './threadStop';
import {chatStopMayAbortLocalReaders} from './chatRuntimeState';
import {fetchThreadInputs,enqueueThreadInput,selectThreadInput,cancelThreadInput,moveThreadInputToSideTask,ThreadInputError,type ThreadInputEntry} from './threadInputQueue';
import {confirmToolCall,resolvePendingToolConfirmation,resolveToolName,resolveSandboxNetworkRequest,type PendingToolConfirmation} from './toolConfirmation';

const empty=()=>({threadId:null as string|null,thread:undefined as ClaudeThreadRecord|undefined,messages:[] as UIMessage[],historicalMessageIds:new Set<string>() as ReadonlySet<string>,running:false,posting:false,recovering:false,stopping:false,unknown:false,error:null as string|null,
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
export default function useNativeChatThread({context,onSettled,onSessionExpired,transport:rawTransport=clientFetch,stream=openResponse}:{context:ClaudeChatRequestContext;onSettled?:()=>void;onSessionExpired?:()=>void;transport?:typeof fetch;stream?:typeof openResponse}) {
  const [state,setState]=useState(empty),current=useRef(state);current.current=state;
  const latest=useRef({context,onSettled,onSessionExpired});latest.current={context,onSettled,onSessionExpired};
  const transport=useCallback<typeof fetch>(async(input,init)=>{const response=await rawTransport(input,init);if(response.status===401)latest.current.onSessionExpired?.();return response;},[rawTransport]);
  const mounted=useRef(true),epoch=useRef(0),selectionEpoch=useRef(0),connection=useRef<OpenResponse|null>(null),postLock=useRef<number|null>(null);
  const timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined),attempt=useRef(0),queueIds=useRef(new Map<string,string>()),olderLock=useRef(false);
  function update(patch:Partial<typeof state>|((value:typeof state)=>typeof state)) {if(!mounted.current)return;setState(value=>{const next=typeof patch==='function'?patch(value):{...value,...patch};current.current=next;return next;});}
  function active(id:string,version:number) {return mounted.current && epoch.current===version && current.current.threadId===id;}
  function ownsSelection(id:string,version:number) {return mounted.current && selectionEpoch.current===version && current.current.threadId===id;}
  function closeReader() {connection.current?.cancel();connection.current=null;if(timer.current)clearTimeout(timer.current);timer.current=undefined;}
  function newChat() {selectionEpoch.current++;epoch.current++;closeReader();queueIds.current.clear();update(empty());}
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
    connection.current=response;
    if(response.status!==200){response.cancel();if(response.status===401)latest.current.onSessionExpired?.();if(submission)observeClaudeThreadSubmission(submission,'rejected');throw new Error('CHAT_HTTP_REJECTED');}
    let buffer='',terminal=false;
    const dispatch=(frame:string)=>{
      for(const event of parseClaudeAgentSseBuffer(frame)) {
        if(submission)observeClaudeThreadSubmission(submission,event.type==='finish'?'terminal':'accepted');
        if(active(id,version))update(value=>({...value,messages:applyBackendEventToMessages(value.messages,event),
          ...(event.type==='error'?{error:'chat.turnNavigation.status.failed'}:{}),
          ...(event.type==='tool-approval-request'?{settled:new Set([...value.settled].filter(toolId=>toolId!==event.toolCallId))}:{}),
        }));
        if(event.type==='finish'){terminal=true;break;}
      }
    };
    try {
      for await(const chunk of response.chunks) {
        if(!active(id,version))break;
        const drained=drainClaudeAgentSseFrames(buffer+chunk);buffer=drained.buffer;
        for(const frame of drained.frames){dispatch(frame+'\n\n');if(terminal)break;}
        if(terminal)break;
      }
      if(!terminal && buffer.trim() && active(id,version))dispatch(buffer);
    } finally {response.cancel();if(connection.current===response)connection.current=null;}
  }
  async function recover(id:string,version=epoch.current) {
    if(!active(id,version))return;
    update({recovering:true});
    try {
      const snapshot=await hydrateClaudeThreadSession(id,transport);
      if(!active(id,version))return;
      const stopPending=claudeThreadStopPending(id);
      update(value=>{const merged=mergeRecoveredLatestPage(value.messages,snapshot.messages);return {...value,thread:snapshot.thread,messages:merged.messages,historicalMessageIds:new Set([...value.historicalMessageIds,...snapshot.messages.map(message=>message.id)]),running:snapshot.running || stopPending,
        recovering:false,posting:false,unknown:stopPending,error:value.error==='chat.turnNavigation.status.failed'?value.error:null,settled:snapshot.settledToolCallIds,runtimePending:snapshot.runtimePendingToolCallIds,
        nextCursor:merged.overlapsLoadedWindow?value.nextCursor:snapshot.nextCursor,hasMore:merged.overlapsLoadedWindow?value.hasMore:snapshot.hasMore};});
      void refreshQueue(id).catch(()=>{});
      if(snapshot.running) {
        await consume(id,version,await stream(`/api/claude-agent/threads/${encodeURIComponent(id)}/stream`,{headers:browserRequestHeaders()}));
        schedule(id,version);
      } else if(stopPending) {schedule(id,version);}
      else {attempt.current=0;update({stopping:false});latest.current.onSettled?.();}
    } catch {
      if(active(id,version)){update({recovering:false,unknown:true,error:'chat.inputQueue.stateUnknown'});schedule(id,version);}
    }
  }
  async function openThread(id:string) {
    selectionEpoch.current++;epoch.current++;closeReader();queueIds.current.clear();const version=epoch.current;
    current.current={...empty(),threadId:id,recovering:true};setState(current.current);
    await recover(id,version);
  }
  async function send(text:string,files:UploadedFile[]=[],toolChoice:ToolChoice='auto') {
    const before=current.current;
    if((postLock.current===epoch.current && !before.threadId) || before.stopping || (before.threadId && claudeThreadStopPending(before.threadId)))throw new Error('CHAT_STOP_PENDING');
    if(before.unknown || before.queue.some(entry=>entry.status==='state_unknown')){update({error:'chat.inputQueue.stateUnknown'});throw new Error('CHAT_OUTCOME_UNKNOWN');}
    const selected={...latest.current.context,currentToolChoice:toolChoice};
    const effective=selected.imFullAccessEnabled?'auto':toolChoice;
    if(before.threadId && (before.running || before.posting || before.localOwner)) {
      if(files.length){update({error:'chat.inputQueue.textOnly'});throw new Error('CHAT_INPUT_UNSUPPORTED_PAYLOAD');}
      const input=text.trim();if(!input)return;
      const messageId=queueIds.current.get(input) ?? generateId();queueIds.current.set(input,messageId);
      try {
        const entry=await enqueueThreadInput(before.threadId,messageId,input,effective,selected.deckId,selected.voiceId,transport);
        queueIds.current.delete(input);update(value=>({...value,error:null,queue:[...value.queue.filter(item=>item.message_id!==entry.message_id),entry]}));
        void refreshQueue().catch(()=>{});return;
      } catch(error){update({error:error instanceof ThreadInputError && error.outcomeUnknown?'chat.inputQueue.stateUnknown':'chat.inputQueue.sendFailed'});throw error;}
    }
    const parts:UIMessage['parts']=files.filter(file=>file.storageKey).map(file=>({type:'file',url:toFileProxyUrl(file.storageKey!),mediaType:file.mimeType,filename:file.name}));
    if(text)parts.push({type:'text',text});if(!parts.length)return;
    postLock.current=epoch.current;update({posting:true,error:null});
    let id=before.threadId,dispatched=false,rejected=false,submission:ClaudeThreadSubmission|undefined;const version=epoch.current;
    try {
      id ??= await createChatThread(selected.deckId,selected.voiceId,undefined,transport);
      if(!id)throw new Error('CHAT_THREAD_CREATE_FAILED');
      if(epoch.current!==version || !mounted.current)return;
      const message:UIMessage={id:generateId(),role:'user',parts};
      submission=beginClaudeThreadSubmission(id,message.id);
      current.current={...current.current,threadId:id,posting:true,running:true,messages:[...current.current.messages,message]};setState(current.current);
      const body=buildClaudeChatRequest({id,message,context:selected,attachments:files.map(toAttachment),toolChoice:effective});
      submission.dispatched=true;dispatched=true;
      const response=await stream('/api/claude-agent',{method:'POST',headers:{...browserRequestHeaders(),'Content-Type':'application/json'},body:JSON.stringify(body)});
      rejected=response.status!==200;
      await consume(id,version,response,submission);
      if(active(id,version)){update({posting:false});await recover(id,version);}
    } catch(error) {
      if(submission)observeClaudeThreadSubmission(submission,rejected || !dispatched?'rejected':'unknown');
      if(epoch.current===version && mounted.current) {
        update({posting:false,running:dispatched && !rejected,unknown:dispatched && !rejected,error:dispatched?'chat.inputQueue.stateUnknown':'chat.history.createFailed'});
        if(id && dispatched && !rejected)schedule(id,version);
        else if(submission)update(value=>({...value,messages:value.messages.filter(message=>message.id!==submission?.messageId)}));
      }
      if(!dispatched || rejected)throw error;
    } finally {if(postLock.current===version)postLock.current=null;}
  }
  async function stop() {
    const id=current.current.threadId;if(!id || current.current.stopping)return;
    const version=epoch.current;update({stopping:true,running:true});
    try {
      const receipt=await requestClaudeSubmittedThreadStop(id,transport);
      if(!active(id,version))return;
      if(!claudeThreadStopPending(id) && chatStopMayAbortLocalReaders(receipt.stopRequested,receipt.running))closeReader();
    } catch {if(active(id,version))update({unknown:true,error:'chat.inputQueue.stateUnknown'});}
    finally {if(active(id,version)){update({stopping:false});schedule(id,version);}}
  }
  async function loadOlder() {
    const before=current.current;if(!before.threadId || !before.nextCursor || olderLock.current)return;
    olderLock.current=true;const version=epoch.current;update({loadingOlder:true});
    try {const page=await fetchClaudeThreadMessages(before.threadId,{cursor:before.nextCursor},transport);
      if(active(before.threadId,version))update(value=>({...value,messages:prependUniqueOlderMessages(value.messages,page.messages),historicalMessageIds:new Set([...value.historicalMessageIds,...page.messages.map(message=>message.id)]),nextCursor:page.nextCursor,hasMore:page.hasMore}));
    } catch {if(active(before.threadId,version))update({error:'chat.activity.historyFailed'});}
    finally {olderLock.current=false;if(active(before.threadId,version))update({loadingOlder:false});}
  }
  const confirmation=useMemo<PendingToolConfirmation|null>(()=>{
    for(const message of state.messages)for(const [index,part] of message.parts.entries())if(isToolUIPart(part)) {
      const kind=resolvePendingToolConfirmation(part,latest.current.context.imFullAccessEnabled?'auto':latest.current.context.currentToolChoice,state.settled,state.runtimePending);
      if(kind)return {kind,partKey:`${message.id}-${index}`,toolCallId:part.toolCallId,toolName:resolveToolName(part),input:'input' in part?part.input:undefined,networkRequest:kind==='sandbox-network'?resolveSandboxNetworkRequest(part):undefined};
    }
    return null;
  },[state.messages,state.settled,state.runtimePending,context.imFullAccessEnabled,context.currentToolChoice]);
  async function confirm(approved:boolean,reason?:string,answers?:Record<string,unknown>) {
    const id=current.current.threadId;if(!id || !confirmation)return;
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
    try{await enqueueThreadInput(id,messageId,text,selected.imFullAccessEnabled?'auto':selected.currentToolChoice,selected.deckId,selected.voiceId,transport);if(ownsSelection(id,version))update({editDraftRecovery:null,queueError:null});await refreshQueue(id);}
    catch(error){if(ownsSelection(id,version)){update({editDraftRecovery:{id:messageId,text},queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}throw error;}
  }
  async function retryEditedInput() {
    const id=current.current.threadId,draft=current.current.editDraftRecovery;if(!id||!draft||current.current.editRetrying)return;
    const version=selectionEpoch.current,selected={...latest.current.context};update({editRetrying:true});
    try{await enqueueThreadInput(id,draft.id,draft.text,selected.imFullAccessEnabled?'auto':selected.currentToolChoice,selected.deckId,selected.voiceId,transport);if(ownsSelection(id,version))update({editDraftRecovery:null,queueError:null});await refreshQueue(id);}
    catch(error){if(ownsSelection(id,version)){update({queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}}
    finally{if(ownsSelection(id,version))update({editRetrying:false});}
  }
  async function sideTask(entry:ThreadInputEntry) {
    const id=inputThread(entry),version=epoch.current;
    try{const task=await moveThreadInputToSideTask(id,entry,transport);await refreshQueue(id);if(active(id,version))update({queueError:task.error_code?'chat.inputQueue.sideChatLaunchFailed':null});return task;}
    catch(error){if(active(id,version)){update({queueError:inputFailureKey(error)});void refreshQueue(id).catch(()=>{});}throw error;}
  }
  useEffect(()=>{
    mounted.current=true;
    const listener=AppState.addEventListener('change',next=>{const id=current.current.threadId;if(!id)return;
      if(next==='active'){epoch.current++;closeReader();void recover(id,epoch.current);}
      else if(next==='background'){epoch.current++;closeReader();update({posting:false,recovering:false,unknown:true});}
    });
    return()=>{mounted.current=false;selectionEpoch.current++;epoch.current++;closeReader();listener.remove();};
  },[]);
  useEffect(()=>{
    if(!state.threadId)return;let inFlight=false,live=true;const id=state.threadId;
    const read=async()=>{if(inFlight || !live)return;inFlight=true;try{await refreshQueue(id);}catch{}finally{inFlight=false;}};
    void read();const interval=setInterval(()=>void read(),2000);return()=>{live=false;clearInterval(interval);};
  },[state.threadId]);
  return {...state,confirmation,newChat,openThread,send,stop,loadOlder,confirm,guide,cancelInput,editInput,retryEditedInput,checkQueue,sideTask,refreshQueue,retry:()=>{const id=current.current.threadId;if(id){epoch.current++;closeReader();void recover(id,epoch.current);}}};
}
