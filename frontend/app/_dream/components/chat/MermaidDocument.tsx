'use client';
// [Input] Document-bound Mermaid source and concrete native clipboard/PNG acknowledgements.
// [Output] Original strict Mermaid renderer, source fallback and shared immersive zoom controls.
// [Pos] Diagram-only local DOM document; RN owns system operations and application navigation.
import {useCallback,useEffect,useRef,useState} from 'react';
import MermaidBlock from './MermaidBlock';
import i18n from '../../i18n';
import {initTheme,setThemeMode} from '../../utils/theme';
import {readMermaidReply,readMermaidState,type MermaidDocumentEvent,type MermaidDocumentState} from './MermaidDocument.protocol';
import '../../styles/tokens.css';
import '../../index.css';
import './MermaidDocument.css';
type Payload=MermaidDocumentEvent extends infer E?E extends MermaidDocumentEvent?Omit<E,'documentId'|'revision'>:never:never;
export default function MermaidDocument(){
  const [state,setState]=useState<MermaidDocumentState|null>(null),current=useRef(state),documentId=useRef(''),root=useRef<HTMLDivElement>(null);
  current.current=state;
  const pending=useRef(new Map<string,{revision:number;resolve:()=>void;reject:()=>void}>());
  const emit=useCallback((event:Payload)=>{const value=current.current;if(value)window.ReactNativeWebView?.postMessage(JSON.stringify({...event,documentId:documentId.current,revision:value.revision}));},[]);
  useEffect(()=>{
    if(window.top!==window)return;
    documentId.current=crypto.randomUUID();document.documentElement.dataset.mermaidDocument='true';initTheme();
    const receive=(event:MessageEvent)=>{
      if(event.source!==null)return;
      let raw:unknown=event.data;if(typeof raw==='string'){try{raw=JSON.parse(raw);}catch{return;}}
      const next=readMermaidState(raw);
      if(next?.documentId===documentId.current&&next.revision>(current.current?.revision??-1)){
        for(const item of pending.current.values())item.reject();pending.current.clear();
        current.current=next;setState(next);setThemeMode(next.theme);void i18n.changeLanguage(next.language);return;
      }
      const reply=readMermaidReply(raw);if(!reply||reply.documentId!==documentId.current||reply.revision!==current.current?.revision)return;
      const item=pending.current.get(reply.requestId);if(!item||item.revision!==reply.revision)return;
      pending.current.delete(reply.requestId);reply.accepted?item.resolve():item.reject();
    };
    window.addEventListener('message',receive);window.ReactNativeWebView?.postMessage(JSON.stringify({type:'ready',documentId:documentId.current}));
    return()=>{delete document.documentElement.dataset.mermaidDocument;window.removeEventListener('message',receive);for(const item of pending.current.values())item.reject();pending.current.clear();};
  },[]);
  useEffect(()=>{const element=root.current;if(!element||!state)return;const measure=()=>emit({type:'height',height:Math.max(1,element.getBoundingClientRect().height)});const observer=new ResizeObserver(measure);observer.observe(element);measure();return()=>observer.disconnect();},[state?.revision,emit]);
  const request=useCallback((event:Payload)=>new Promise<void>((resolve,reject)=>{
    if(!current.current){reject(Error('MERMAID_DOCUMENT_UNAVAILABLE'));return;}
    const requestId=crypto.randomUUID();pending.current.set(requestId,{revision:current.current.revision,resolve,reject:()=>reject(Error('MERMAID_OPERATION_REJECTED'))});emit({...event,requestId} as Payload);
  }),[emit]);
  const copyText=useCallback((text:string)=>request({type:'copy',requestId:'',text}),[request]);
  const savePNG=useCallback(async(blob:Blob,name:string)=>{
    const revision=current.current?.revision;
    const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(Error('MERMAID_PNG_READ_FAILED'));reader.readAsDataURL(blob);});
    if(current.current?.revision!==revision)throw Error('MERMAID_REVISION_CHANGED');
    await request({type:'png',requestId:'',name,base64:data.split(',')[1]??''});
  },[request]);
  return <div ref={root} className="mermaid-document">{state?<MermaidBlock chart={state.chart} copyText={copyText} savePNG={savePNG} preview={{open:state.expanded,onChange:open=>emit({type:'preview',open})}}/>:null}</div>;
}
