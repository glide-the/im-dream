// [Input] Original activity coordinator, native AppState and the existing local HTTP adapter.
// [Output] Original Chat/today-task read states while the native drawer is visible and foregrounded.
// [Pos] Native lifecycle adapter; Dream workbench source and background reads remain excluded.
import {useCallback,useEffect,useRef,useState} from 'react';
import {AppState} from 'react-native';
import {clientFetch} from '../../../../src/platform/transport.native';
import {useActivitySidebarData} from './useActivitySidebarData';
export default function useNativeActivitySidebarData(open:boolean,{transport:rawTransport=clientFetch,onSessionExpired}:{transport?:typeof fetch;onSessionExpired?:()=>void}={}) {
  const expire=useRef(onSessionExpired);expire.current=onSessionExpired;
  const transport=useCallback<typeof fetch>(async(input,init)=>{const response=await rawTransport(input,init);if(response.status===401)expire.current?.();return response;},[rawTransport]);
  const [foreground,setForeground]=useState(AppState.currentState==='active');
  useEffect(()=>{const listener=AppState.addEventListener('change',state=>setForeground(state==='active'));return()=>listener.remove();},[]);
  return useActivitySidebarData(open,{transport,foreground,includeDream:false});
}
