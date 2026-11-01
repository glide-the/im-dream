'use client';
// [Sync] 2026-10-31: acknowledge Native disposal after original Host session cleanup; iframe messages retain their source boundary.
// [Input] Original tool parts and document-bound native state; same-origin browser session owns authentication.
// [Output] Original MCP App Host or editor confirmation/completion UI with matched Chat message acknowledgements.
// [Pos] Local DOM leaf only; original AppBridge, permissions, MCP cleanup and editor HTTP stay unchanged.
import {useCallback,useEffect,useRef,useState} from 'react';
import {AuthProvider,useAuth} from '../../contexts/AuthContext';
import i18n from '../../i18n';
import {initTheme,setThemeMode} from '../../utils/theme';
import ToolMessagePart from './ToolMessagePart';
import {EditorWriteCompletedCard} from './EditorWriteApprovalUI';
import {getEditorWriteOutput,readToolInput} from './toolPartPresentation';
import {parseEditorJumpToCellDetail} from './editorWriteTools';
import {resolveToolName} from './toolConfirmation';
import type {ChatUserMessage} from './chatUserMessageIngress';
import {readToolResultDispose,readToolResultReply,readToolResultState,type ToolResultEvent,type ToolResultState} from './ToolResultDocument.protocol';
import {closeMcpAppsDocumentSessions} from './mcp-apps/session-cleanup';
import '../../styles/tokens.css';
import '../../index.css';
import './ToolResultDocument.css';
type Payload=ToolResultEvent extends infer E?E extends ToolResultEvent?Omit<E,'documentId'|'threadId'|'toolCallId'>:never:never;
function Content({state,emit,send}:{state:ToolResultState;emit:(event:Payload)=>void;send:(message:ChatUserMessage)=>Promise<void>}){
  const auth=useAuth();
  useEffect(()=>{if(!auth.isLoading&&!auth.isAuthenticated&&!auth.authError)emit({type:'session-expired'});},[auth.isLoading,auth.isAuthenticated,auth.authError,emit]);
  if(auth.isLoading)return <p role="status">{state.language.startsWith('zh')?'正在读取…':'Loading…'}</p>;
  if(!auth.isAuthenticated)return <p role="alert">{state.language.startsWith('zh')?'请重新登录。':'Please sign in again.'}</p>;
  if(state.presentation==='editor'&&state.editorCompleted)return <EditorWriteCompletedCard toolName={resolveToolName(state.part)} input={(readToolInput(state.part)??{}) as Record<string,unknown>} output={getEditorWriteOutput(state.part,state.part.state==='output-error')}/>;
  return <ToolMessagePart part={state.part} threadId={state.threadId} presentation={state.presentation==='app-only'?'app-only':'complete'}
    sendUserMessage={send} settledToolCallIds={new Set(state.settledToolCallIds)}
    addToolResult={value=>{if(value.toolCallId===state.toolCallId&&value.output&&typeof value.output==='object'&&'approved' in value.output&&typeof value.output.approved==='boolean')emit({type:'tool-result',tool:value.tool,output:{approved:value.output.approved}});}}
    onConfirmationSettled={()=>emit({type:'confirmation-settled'})} onEditorWriteConfirmed={()=>emit({type:'editor-confirmed'})}/>;
}
export default function ToolResultDocument(){
  const [state,setState]=useState<ToolResultState|null>(null),documentId=useRef(''),revision=useRef(-1),current=useRef(state),root=useRef<HTMLDivElement>(null);
  current.current=state;
  const disposing=useRef(false);
  const pending=useRef(new Map<string,{resolve:()=>void;reject:()=>void}>());
  const emit=useCallback((event:Payload)=>{const value=current.current;if(!value)return;window.ReactNativeWebView?.postMessage(JSON.stringify({...event,documentId:documentId.current,threadId:value.threadId,toolCallId:value.toolCallId}));},[]);
  useEffect(()=>{
    if(window.top!==window)return;
    documentId.current=crypto.randomUUID();document.documentElement.dataset.toolResultDocument='true';initTheme();
    async function receive(event:MessageEvent){
      // Native injects a local MessageEvent with no Window source. App iframe messages keep their own AppBridge listener.
      if(event.source!==null)return;
      let raw:unknown=event.data;if(typeof raw==='string'){try{raw=JSON.parse(raw);}catch{return;}}
      const disposal=readToolResultDispose(raw),binding=current.current;
      if(disposal&&binding&&disposal.documentId===documentId.current&&disposal.threadId===binding.threadId&&disposal.toolCallId===binding.toolCallId){
        if(disposing.current)return;
        disposing.current=true;current.current={...binding,active:false};
        if(root.current)root.current.style.pointerEvents='none';
        const closed=closeMcpAppsDocumentSessions();
        setState(null);
        await closed;
        window.ReactNativeWebView?.postMessage(JSON.stringify({type:'disposed',documentId:documentId.current,threadId:binding.threadId,toolCallId:binding.toolCallId,requestId:disposal.requestId}));
        return;
      }
      if(disposing.current)return;
      const next=readToolResultState(raw);
      if(next?.documentId===documentId.current&&next.revision>revision.current){
        if(current.current&&(next.threadId!==current.current.threadId||next.toolCallId!==current.current.toolCallId))return;
        revision.current=next.revision;current.current=next;setState(next);setThemeMode(next.theme);void i18n.changeLanguage(next.language);return;
      }
      const reply=readToolResultReply(raw);
      if(!reply||reply.documentId!==documentId.current||reply.threadId!==binding?.threadId||reply.toolCallId!==binding.toolCallId)return;
      const request=pending.current.get(reply.requestId);if(!request)return;pending.current.delete(reply.requestId);reply.accepted?request.resolve():request.reject();
    }
    const jump=(event:Event)=>{const detail=parseEditorJumpToCellDetail((event as CustomEvent).detail);if(detail)emit({type:'editor-jump',detail});};
    window.addEventListener('message',receive);window.addEventListener('editor:jump-to-cell',jump);
    window.ReactNativeWebView?.postMessage(JSON.stringify({type:'ready',documentId:documentId.current}));
    return()=>{delete document.documentElement.dataset.toolResultDocument;window.removeEventListener('message',receive);window.removeEventListener('editor:jump-to-cell',jump);for(const item of pending.current.values())item.reject();pending.current.clear();};
  },[emit]);
  useEffect(()=>{const element=root.current;if(!element||!state)return;const measure=()=>emit({type:'height',height:Math.max(1,element.getBoundingClientRect().height)});const observer=new ResizeObserver(measure);observer.observe(element);measure();return()=>observer.disconnect();},[Boolean(state),emit]);
  const send=useCallback(async(message:ChatUserMessage)=>{
    if(!current.current?.active)throw Error('MCP App message is unavailable.');
    const requestId=crypto.randomUUID();
    await new Promise<void>((resolve,reject)=>{pending.current.set(requestId,{resolve,reject:()=>reject(Error('MCP App message is unavailable.'))});emit({type:'user-message',requestId,message:message as {role:'user';parts:{type:'text';text:string}[]}});});
  },[emit]);
  return <div ref={root} style={{width:'100%',minWidth:0,overflow:'hidden',color:'var(--color-text-primary)',background:'var(--color-bg-app)'}}>{state?<AuthProvider><Content state={state} emit={emit} send={send}/></AuthProvider>:null}</div>;
}
