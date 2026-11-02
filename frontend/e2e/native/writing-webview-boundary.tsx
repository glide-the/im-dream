// [Input] Production WritingView WebView callbacks and an explicit synthetic local document.
// [Output] Observable document URL/state and navigation messages for native frame qualification.
// [Pos] Technical facade only; original DOM editor and real WKWebView require separate checks.
// [Sync] 2026-11-01: decode actual injected Writing state for context-request identity assertions; DOM replies remain explicit fixture events.
import {forwardRef,useEffect,useImperativeHandle,useRef} from 'react';
export const WebView=forwardRef(function FixtureWebView(props:any,ref:any){
 const current=useRef(props);current.current=props;
 const f=(window as any).__writingFrame??=((window as any).__writingFrame={urls:[],scripts:[],states:[],documentId:'fixture-writing-document'});
 function emit(event:any){current.current.onMessage?.({nativeEvent:{url:current.current.source.uri,data:JSON.stringify({documentId:f.documentId,...event})}});}
 f.emit=emit;
 useImperativeHandle(ref,()=>({injectJavaScript:(script:string)=>{f.scripts.push(script);const start=script.indexOf('{data:')+6,end=script.lastIndexOf('}));true;');f.states.push(JSON.parse(JSON.parse(script.slice(start,end))));},reload:()=>emit({type:'ready'})}),[]);
 useEffect(()=>{f.urls.push(props.source.uri);props.onLoadStart?.();emit({type:'ready'});},[props.source.uri]);
 return <div role="status" aria-label="Synthetic Writing document" style={{flex:1}}>Original editor document boundary</div>;
});
