'use client';
// [Input] Original SketchInputDialog and local native visibility/upload acknowledgements.
// [Output] Original drawing/history/import UI plus a PNG callback; uploads and Chat remain native-owned.
// [Pos] Fixed browser-only sketch leaf; closing preserves the mounted document's drawing and undo history.
import {useEffect,useRef,useState} from 'react';
import SketchInputDialog from './SketchInputDialog';
import {MAX_UPLOAD_FILE_SIZE_BYTES} from './AIInputDock.helpers';
import {readSketchResult,readSketchState,type SketchDocumentState} from './SketchInputDocument.protocol';
import i18n from '../../i18n';

export default function SketchInputDocument() {
  const [state,setState]=useState<SketchDocumentState|null>(null);
  const documentId=useRef(''),revision=useRef(-1),active=useRef(false);
  const pending=useRef<{requestId:string;resolve:(accepted:boolean)=>void}|null>(null);
  function emit(event:Record<string,unknown>) {window.ReactNativeWebView?.postMessage(JSON.stringify({...event,documentId:documentId.current}));}
  useEffect(()=>{
    active.current=true;documentId.current=crypto.randomUUID();
    function receive(event:MessageEvent) {
      let raw:unknown=event.data;if(typeof raw==='string'){try {raw=JSON.parse(raw);}catch{return;}}
      const next=readSketchState(raw);
      if(next && next.documentId===documentId.current && next.revision>revision.current){revision.current=next.revision;setState(next);void i18n.changeLanguage(next.language);if(next.theme==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=next.theme;return;}
      const result=readSketchResult(raw);
      if(result?.documentId===documentId.current && result.requestId===pending.current?.requestId){const request=pending.current;pending.current=null;request?.resolve(result.accepted);}
    }
    window.addEventListener('message',receive);emit({type:'ready'});
    return()=>{active.current=false;window.removeEventListener('message',receive);pending.current?.resolve(false);pending.current=null;};
  },[]);
  async function add(file:File):Promise<boolean> {
    if(!active.current || pending.current || !state?.open || state.disabled || file.type!=='image/png' || file.size>MAX_UPLOAD_FILE_SIZE_BYTES)return false;
    const base64=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(new Error('SKETCH_READ_FAILED'));reader.onload=()=>{const result=reader.result;typeof result==='string' && result.startsWith('data:image/png;base64,')?resolve(result.slice(result.indexOf(',')+1)):reject(new Error('SKETCH_READ_FAILED'));};reader.readAsDataURL(file);});
    if(!active.current)return false;
    return new Promise(resolve=>{const requestId=crypto.randomUUID();pending.current={requestId,resolve};emit({type:'add',requestId,name:file.name,size:file.size,base64});});
  }
  return <SketchInputDialog open={state?.open===true} disabled={state?.disabled ?? true} maxFileBytes={MAX_UPLOAD_FILE_SIZE_BYTES}
    onClose={()=>{if(!pending.current)emit({type:'close'});}} onAdd={add} />;
}
