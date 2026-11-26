// [Sync] 2026-11-03: carry the original note date in the read-only chooser projection.
// [Input] Native display state, original editor navigation intents and Writing chooser presentation.
// [Output] Fixed local document URL and validated identity/revision messages.
// [Pos] Writing document boundary; HTTP, permissions, editor persistence and Agent tasks retain their original owners.
// [Sync] 2026-11-01: add display-only chooser snapshots and a single-use open intent inside the existing boundary.
// [Sync] 2026-11-01: bind on-demand saved Writing context to one document, Session, request and cancellable native submission.
import {parseEditorJumpToCellDetail,type EditorJumpToCellDetail} from '../chat/editorWriteTools';
import {WRITING_CHAT_CONTEXT_TIMEOUT_MS} from '../../constants/sessionSync';
// [Sync] 2026-11-12: bind explicit note clipboard/file actions and receipts to the local document.
import {isWritingShareRequest, isWritingShareResult, type WritingShareRequest, type WritingShareResult} from './WritingShare.protocol';
export const WRITING_DOCUMENT_PATH='/native/writing';
export interface WritingChooserView {loading:boolean;selectedStateId:string|null;name:string;expanded:boolean;createdAt?:string}
export interface WritingContextRequest {requestId:string;sessionId:string}
export type WritingContextResult = WritingContextRequest & ({type:'chat-context';editorState:Record<string,unknown>}|{type:'chat-context-error';code:'session-changed'|'save-failed'});
export interface WritingThreadContext {sessionId:string;prepareEditorState:(signal:AbortSignal)=>Promise<Record<string,unknown>>}
export interface WritingDocumentState {type:'state';documentId:string;revision:number;active:boolean;theme:'light'|'dark'|'system';language:'en'|'zh';showEnergyBar:boolean;editorJump?:{nonce:number;detail:EditorJumpToCellDetail};openChooserNonce?:number;contextRequest?:WritingContextRequest;shareResult?:WritingShareResult}
export type WritingDocumentEvent=
 | {type:'note-share';documentId:string;request:WritingShareRequest}
 | {type:'ready'|'session-expired'|'resources';documentId:string}
 | {type:'open-thread';documentId:string;threadId:string;editorSessionId?:string}
 | {type:'prepare-chat';documentId:string;input:string}
 | {type:'editor-jump-dispatched';documentId:string;nonce:number}
 | ({type:'chooser-view';documentId:string;revision:number}&WritingChooserView)
 | (WritingContextResult & {documentId:string});
function isContextRequest(value:unknown):value is WritingContextRequest {return Boolean(value&&typeof value==='object'&&'requestId' in value&&typeof value.requestId==='string'&&value.requestId&&'sessionId' in value&&typeof value.sessionId==='string'&&value.sessionId);}
export function writingDocumentUrl(origin:string):string {const match=/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(?::([0-9]+))?\/?$/.exec(origin);if(!match||(match[2]&&(Number(match[2])<1||Number(match[2])>65535)))throw Error('WRITING_ORIGIN_INVALID');return origin.replace(/\/$/,'')+WRITING_DOCUMENT_PATH;}
export function readWritingState(raw:unknown):WritingDocumentState|null {
 if(!raw||typeof raw!=='object')return null;
 const r=raw as Record<string,unknown>;
 return r.type==='state'&&typeof r.documentId==='string'&&Number.isSafeInteger(r.revision)&&Number(r.revision)>=0&&typeof r.active==='boolean'&&['light','dark','system'].includes(String(r.theme))&&['en','zh'].includes(String(r.language))&&typeof r.showEnergyBar==='boolean'
  &&(r.openChooserNonce===undefined||(Number.isSafeInteger(r.openChooserNonce)&&Number(r.openChooserNonce)>0))
  &&(r.contextRequest===undefined||isContextRequest(r.contextRequest))
  &&(r.shareResult===undefined||isWritingShareResult(r.shareResult))
  &&(r.editorJump===undefined||(typeof r.editorJump==='object'&&r.editorJump!==null&&'nonce' in r.editorJump&&Number.isSafeInteger(r.editorJump.nonce)&&'detail' in r.editorJump&&parseEditorJumpToCellDetail(r.editorJump.detail)!==null))?r as unknown as WritingDocumentState:null;
}
export function readWritingEvent(raw:string):WritingDocumentEvent|null {
 let r:Record<string,unknown>;try{r=JSON.parse(raw);}catch{return null;}
 if(!r||typeof r.documentId!=='string')return null;
 if(['ready','session-expired','resources'].includes(String(r.type)))return r as WritingDocumentEvent;
 if(r.type==='note-share'&&isWritingShareRequest(r.request))return r as WritingDocumentEvent;
 if(r.type==='chooser-view'&&Number.isSafeInteger(r.revision)&&Number(r.revision)>0&&typeof r.loading==='boolean'&&(r.selectedStateId===null||typeof r.selectedStateId==='string')&&typeof r.name==='string'&&typeof r.expanded==='boolean'&&(r.createdAt===undefined||(typeof r.createdAt==='string'&&Number.isFinite(Date.parse(r.createdAt)))))return r as WritingDocumentEvent;
 if(r.type==='editor-jump-dispatched'&&Number.isSafeInteger(r.nonce))return r as WritingDocumentEvent;
 if(r.type==='open-thread'&&typeof r.threadId==='string'&&r.threadId.length>0&&(r.editorSessionId===undefined||(typeof r.editorSessionId==='string'&&r.editorSessionId.length>0)))return r as WritingDocumentEvent;
 if(isContextRequest(r)){
  if(r.type==='chat-context-error'&&['session-changed','save-failed'].includes(String(r.code)))return r as unknown as WritingDocumentEvent;
  const state=r.editorState;
  if(r.type==='chat-context'&&state&&typeof state==='object'&&!Array.isArray(state)&&'id' in state&&state.id===r.sessionId&&'cells' in state&&Array.isArray(state.cells))return r as unknown as WritingDocumentEvent;
 }
 if(r.type==='prepare-chat'&&typeof r.input==='string')return r as WritingDocumentEvent;
 return null;
}

// One native Writing document owns one pending save/context request; no content is logged or stored globally.
export class WritingContextRequests {
 private documentId='';
 private sequence=0;
 private pending?:{request:WritingContextRequest;documentId:string;resolve:(state:Record<string,unknown>)=>void;reject:(error:Error)=>void;cleanup:()=>void};
 constructor(private send:(request:WritingContextRequest|undefined)=>void,private timeoutMs=WRITING_CHAT_CONTEXT_TIMEOUT_MS){}
 attach(documentId:string){this.cancel();this.documentId=documentId;}
 cancel(){this.finish(new Error('WRITING_CONTEXT_CANCELLED'));}
 private finish(result:Error|Record<string,unknown>){
  const pending=this.pending;if(!pending)return;this.pending=undefined;pending.cleanup();try{this.send(undefined);}catch{/* The document may already be detached. */}
  if(result instanceof Error)pending.reject(result);else pending.resolve(result);
 }
 prepare(documentId:string,sessionId:string,signal:AbortSignal):Promise<Record<string,unknown>>{
  if(!documentId||documentId!==this.documentId||!sessionId||signal.aborted)return Promise.reject(new Error('WRITING_CONTEXT_UNAVAILABLE'));
  if(this.pending)return Promise.reject(new Error('WRITING_CONTEXT_BUSY'));
  return new Promise((resolve,reject)=>{
   const request={requestId:String(++this.sequence),sessionId};
   const abort=()=>this.finish(new Error('WRITING_CONTEXT_CANCELLED'));
   const timer=setTimeout(()=>this.finish(new Error('WRITING_CONTEXT_TIMEOUT')),this.timeoutMs);
   this.pending={request,documentId,resolve,reject,cleanup:()=>{clearTimeout(timer);signal.removeEventListener('abort',abort);}};
   signal.addEventListener('abort',abort,{once:true});
   try{this.send(request);}catch{this.finish(new Error('WRITING_CONTEXT_UNAVAILABLE'));}
  });
 }
 receive(event:WritingDocumentEvent){
  if(event.type!=='chat-context'&&event.type!=='chat-context-error')return;
  const pending=this.pending;
  if(!pending||event.documentId!==pending.documentId||event.requestId!==pending.request.requestId||event.sessionId!==pending.request.sessionId)return;
  this.finish(event.type==='chat-context'?event.editorState:new Error('WRITING_CONTEXT_REJECTED'));
 }
}
