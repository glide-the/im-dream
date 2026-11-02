'use client';
// [Input] A local native editor state and the unchanged production Tiptap MarkdownInputEditor.
// [Output] Rich Markdown changes, keyboard submit intent, focus and measured editor height.
// [Pos] DOM-only editor document embedded inside the RN composer; no application shell or business API calls.
// [Sync] 2026-10-28: delegate active Skill-menu keys to its owner while retaining original submit/newline and IME behavior.
// [Sync] 2026-10-28: report natural content height through viewport contractions so native flex can shrink and later restore the editor.
import {useEffect,useRef,useState} from 'react';
import MarkdownInputEditor from './MarkdownInputEditor';
import {shouldSendMessageOnKeyDown} from './interaction-utils';
import {readComposerState,type ComposerDocumentPayload,type ComposerDocumentState} from './MarkdownInputDocument.protocol';
import './MarkdownInputDocument.css';

declare global {interface Window {ReactNativeWebView?:{postMessage:(message:string)=>void};}}
export default function MarkdownInputDocument() {
  const [state,setState]=useState<Omit<ComposerDocumentState,'type'|'documentId'|'revision'|'eventCount'>>({value:'',placeholder:'',ariaLabel:'',disabled:true,theme:'system'});
  const identity=useRef('');
  const editCount=useRef(0),revision=useRef(-1);
  const container=useRef<HTMLDivElement>(null);
  const composing=useRef(false);
  const deferred=useRef<ComposerDocumentState|null>(null);
  function emit(event:ComposerDocumentPayload) {
    window.ReactNativeWebView?.postMessage(JSON.stringify({...event,documentId:identity.current}));
  }
  useEffect(() => {
    identity.current=crypto.randomUUID();
    document.documentElement.dataset.nativeComposer='true';
    function apply(next:ComposerDocumentState) {
      if (next.documentId !== identity.current || next.revision <= revision.current) return;
      if (composing.current) {if(!deferred.current || next.revision > deferred.current.revision)deferred.current=next;return;}
      revision.current=next.revision;
      setState(current=>({...next,value:next.eventCount >= editCount.current ? next.value : current.value}));
      if (next.theme === 'system') document.documentElement.removeAttribute('data-theme');
      else document.documentElement.dataset.theme=next.theme;
    }
    function receive(event:MessageEvent) {
      let raw:unknown=event.data;
      if (typeof raw === 'string') {try {raw=JSON.parse(raw);} catch {return;}}
      const next=readComposerState(raw);if (next) apply(next);
    }
    const endComposition=()=>{composing.current=false;const next=deferred.current;deferred.current=null;if(next)apply(next);};
    const startComposition=()=>{composing.current=true;};
    window.addEventListener('message',receive);
    const element=container.current!;
    element.addEventListener('compositionstart',startComposition,true);element.addEventListener('compositionend',endComposition,true);
    let measurement:number|undefined;
    const measure=()=>{
      if(measurement!==undefined)return;
      measurement=requestAnimationFrame(()=>{
        measurement=undefined;
        const editor=element.querySelector<HTMLElement>('.markdown-input-editor__content');
        emit({type:'height',height:Math.max(element.getBoundingClientRect().height,editor?.scrollHeight ?? 0)});
      });
    };
    const resize=new ResizeObserver(measure);
    resize.observe(element);
    const content=new MutationObserver(measure);
    content.observe(element,{subtree:true,childList:true,characterData:true});
    emit({type:'ready'});
    return ()=>{window.removeEventListener('message',receive);resize.disconnect();content.disconnect();if(measurement!==undefined)cancelAnimationFrame(measurement);element.removeEventListener('compositionstart',startComposition,true);element.removeEventListener('compositionend',endComposition,true);delete document.documentElement.dataset.nativeComposer;};
  },[]);
  return <div ref={container} className="native-composer-document">
    <MarkdownInputEditor id="native-chat-input" value={state.value} placeholder={state.placeholder} ariaLabel={state.ariaLabel} disabled={state.disabled}
      onChange={value=>{editCount.current+=1;setState(current=>({...current,value}));emit({type:'change',value,eventCount:editCount.current});}}
      onFocus={()=>emit({type:'focus'})} onBlur={()=>emit({type:'blur'})}
      onKeyDown={event=>{
        if(state.disabled || event.nativeEvent.isComposing || composing.current)return;
        if(state.skillMenuOpen && ['ArrowDown','ArrowUp','Enter','Tab','Escape'].includes(event.key)){event.preventDefault();emit({type:'keydown',key:event.key as 'ArrowDown'|'ArrowUp'|'Enter'|'Tab'|'Escape'});return;}
        if(shouldSendMessageOnKeyDown({key:event.key,shiftKey:event.shiftKey,isComposing:false})){event.preventDefault();emit({type:'submit'});}
      }} />
  </div>;
}
