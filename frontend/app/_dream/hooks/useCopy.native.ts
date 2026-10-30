// [Input] User-selected message text and the original copy reset delay.
// [Output] Native clipboard completion and the same copied/copy interface as Web.
// [Pos] Clipboard-only platform hook; user text is written only after the original Copy action.
import {useCallback,useEffect,useRef,useState} from 'react';
import {NativeModules} from 'react-native';
export function useCopy(resetDelay=2000){
  const [copied,setCopied]=useState(false),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined),mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;if(timer.current)clearTimeout(timer.current);};},[]);
  const copy=useCallback((text:string)=>{
    const write=NativeModules.InkRuntime?.copyText;
    if(typeof write!=='function'){setCopied(false);return;}
    void Promise.resolve(write(text)).then(()=>{if(!mounted.current)return;setCopied(true);if(timer.current)clearTimeout(timer.current);timer.current=setTimeout(()=>setCopied(false),resetDelay);}).catch(()=>{if(mounted.current)setCopied(false);});
  },[resetDelay]);
  return {copied,copy};
}
