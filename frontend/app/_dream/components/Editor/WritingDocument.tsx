'use client';
// [Input] Original authenticated Writing engine/canvas and native-owned display/navigation state.
// [Output] The same editor, autosave, Calendar and Writing suggestions inside one local document.
// [Pos] DOM editor leaf; application navigation and canonical Chat presentation are owned by RN.
import {useCallback,useEffect,useRef,useState} from 'react';
import App from '../../App';
import {AuthProvider,useAuth} from '../../contexts/AuthContext';
import i18n from '../../i18n';
import {initTheme,setThemeMode} from '../../utils/theme';
import {readWritingState,type WritingDocumentEvent,type WritingDocumentState} from './WritingDocument.protocol';
import '../../styles/tokens.css';
import '../../index.css';
import './WritingDocument.css';
type EventPayload=WritingDocumentEvent extends infer E?E extends WritingDocumentEvent?Omit<E,'documentId'>:never:never;
function Canvas({state,emit}:{state:WritingDocumentState;emit:(event:EventPayload)=>void}){
 const auth=useAuth();
 useEffect(()=>{if(!auth.isLoading&&!auth.isAuthenticated)emit({type:'session-expired'});},[auth.isLoading,auth.isAuthenticated,emit]);
 if(auth.isLoading)return <p role="status">{state.language==='zh'?'正在读取…':'Loading…'}</p>;
 if(!auth.isAuthenticated)return <p role="alert">{state.language==='zh'?'请重新登录。':'Please sign in again.'}</p>;
 return <App writingDocument={{active:state.active,showEnergyBar:state.showEnergyBar,onOpenThread:threadId=>emit({type:'open-thread',threadId}),onPrepareChat:input=>emit({type:'prepare-chat',input}),onOpenResources:()=>emit({type:'resources'})}}/>;
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
