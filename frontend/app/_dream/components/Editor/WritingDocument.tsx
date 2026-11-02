// [Sync] 2026-11-01: project chooser presentation to the existing native page header; persistence remains in App.
// [Sync] 2026-11-01: relay Session-bound context requests/results through the original App save barrier before native Chat sends.
// [Sync] 2026-10-30: deliver a native historical Editor jump through the original Writing event after authenticated mounting.
'use client';
// [Input] Original authenticated Writing engine/canvas and native-owned display/navigation state.
// [Output] The same editor, autosave, Calendar and Writing suggestions inside one local document.
// [Pos] DOM editor leaf; application navigation and canonical Chat presentation are owned by RN.
import {useCallback,useEffect,useRef,useState} from 'react';
import App from '../../App';
import {AuthProvider,useAuth} from '../../contexts/AuthContext';
import i18n from '../../i18n';
import {initTheme,setThemeMode} from '../../utils/theme';
import {readWritingState,type WritingDocumentEvent,type WritingDocumentState,type WritingChooserView} from './WritingDocument.protocol';
import '../../styles/tokens.css';
import '../../index.css';
import './WritingDocument.css';
type EventPayload=WritingDocumentEvent extends infer E?E extends WritingDocumentEvent?Omit<E,'documentId'>:never:never;
function Canvas({state,emit}:{state:WritingDocumentState;emit:(event:EventPayload)=>void}){
 const auth=useAuth();
 const viewRevision=useRef(0);
 const onChooserView=useCallback((view:WritingChooserView)=>emit({type:'chooser-view',revision:++viewRevision.current,...view}),[emit]);
 const deliveredJump=useRef<number|undefined>(undefined);
 useEffect(()=>{const jump=state.editorJump;if(auth.isLoading||!auth.isAuthenticated||!state.active||!jump||deliveredJump.current===jump.nonce)return;deliveredJump.current=jump.nonce;window.dispatchEvent(new CustomEvent('editor:jump-to-cell',{detail:jump.detail}));emit({type:'editor-jump-dispatched',nonce:jump.nonce});},[auth.isLoading,auth.isAuthenticated,state.active,state.editorJump,emit]);
 useEffect(()=>{if(!auth.isLoading&&!auth.isAuthenticated)emit({type:'session-expired'});},[auth.isLoading,auth.isAuthenticated,emit]);
 if(auth.isLoading)return <p role="status">{state.language==='zh'?'正在读取…':'Loading…'}</p>;
 if(!auth.isAuthenticated)return <p role="alert">{state.language==='zh'?'请重新登录。':'Please sign in again.'}</p>;
 return <App writingDocument={{active:state.active,showEnergyBar:state.showEnergyBar,openChooserNonce:state.openChooserNonce,onChooserView,contextRequest:state.contextRequest,onContextResult:emit,onOpenThread:(threadId,editorSessionId)=>emit({type:'open-thread',threadId,...(editorSessionId?{editorSessionId}:{})}),onPrepareChat:input=>emit({type:'prepare-chat',input}),onOpenResources:()=>emit({type:'resources'})}}/>;
}
export default function WritingDocument(){
 const id=useRef(''),revision=useRef(-1),[state,setState]=useState<WritingDocumentState|null>(null);
 const emit=useCallback((event:EventPayload)=>window.ReactNativeWebView?.postMessage(JSON.stringify({...event,documentId:id.current})),[]);
 useEffect(()=>{id.current=crypto.randomUUID();document.documentElement.dataset.writingDocument='true';initTheme();
  const receive=(event:MessageEvent)=>{let raw:unknown=event.data;if(typeof raw==='string'){try{raw=JSON.parse(raw);}catch{return;}}const next=readWritingState(raw);if(!next||next.documentId!==id.current||next.revision<=revision.current)return;revision.current=next.revision;setThemeMode(next.theme);void i18n.changeLanguage(next.language);setState(next);};
  window.addEventListener('message',receive);emit({type:'ready'});return()=>{window.removeEventListener('message',receive);delete document.documentElement.dataset.writingDocument;};
 },[emit]);
 return state?<AuthProvider><Canvas state={state} emit={emit}/></AuthProvider>:null;
}
