// [Sync] 2026-10-29: reread the same owned configuration after Settings saves; reject superseded configuration responses.
// [Sync] 2026-10-29: expose the same owned catalog refresh after Deck maintenance; keep configuration and Chat instances.
// [Sync] 2026-10-28: read the complete Agent catalog once through the injected cancellable transport.
// [Input] App-owned runtime readiness, original system configuration and Deck reads, and native HTTP.
// [Output] Retryable read snapshots without replacing the conversation, draft or backend process.
// [Pos] Native Chat startup read lifecycle; server configuration and business endpoints retain ownership.
import {useCallback,useEffect,useRef,useState} from 'react';
import type {Deck} from '../../api/voiceApi';
import {listDecksWithVoices} from '../../api/deckReadApi';
import {browserRequestHeaders} from '../../lib/browserSession';
import {BackendRuntimeManager} from '../../../../src/runtime/BackendRuntimeManager';
import {clientFetch} from '../../../../src/platform/transport.native';

export interface NativeChatConfig {
  system_prompt?:string;
  im_full_access_enabled:boolean;
  workspace_enabled:boolean;
}

export default function useNativeChatSetup({transport=clientFetch,onSessionExpired}:{transport?:typeof fetch;onSessionExpired?:()=>void}={}) {
  const [origin,setOrigin]=useState(''),[config,setConfig]=useState<NativeChatConfig>();
  const [decks,setDecks]=useState<Deck[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const [revision,setRevision]=useState(0);
  const expiredOwner=useRef(onSessionExpired);expiredOwner.current=onSessionExpired;
  const catalogOwner=useRef<()=>Promise<Deck[]>>(async()=>{throw new Error('HTTP_ABORTED');});
  const configOwner=useRef<()=>Promise<NativeChatConfig>>(async()=>{throw new Error('HTTP_ABORTED');});
  const refreshDecks=useCallback(()=>catalogOwner.current(),[]);
  const refreshConfig=useCallback(()=>configOwner.current(),[]);
  const retry=useCallback(()=>setRevision(value=>value+1),[]);
  useEffect(()=>{
    let active=true,expired=false,configRequest=0;
    const controller=new AbortController();
    setLoading(true);
    const read:typeof fetch=async(input,init)=>{
      if(!active || controller.signal.aborted)throw new Error('HTTP_ABORTED');
      const response=await transport(input,{...init,signal:controller.signal});
      if(active && response.status===401 && !expired){expired=true;expiredOwner.current?.();}
      return response;
    };
    const refreshCatalog=async()=>{
      const next=await listDecksWithVoices(read);
      if(!active)throw new Error('HTTP_ABORTED');
      setDecks(next);
      return next;
    };
    catalogOwner.current=refreshCatalog;
    const refreshConfiguration=async()=>{
      const sequence=++configRequest;
      const response=await read('/api/system-config',{headers:browserRequestHeaders()});
      if(!response.ok)throw new Error(`HTTP_${response.status}`);
      const payload=await response.json(),snapshot=payload?.data ?? payload;
      if(!snapshot || typeof snapshot.workspace_enabled!=='boolean' || typeof snapshot.im_full_access_enabled!=='boolean'
        || (snapshot.system_prompt!=null && typeof snapshot.system_prompt!=='string'))throw new Error('SYSTEM_CONFIG_INVALID');
      const next:NativeChatConfig={workspace_enabled:snapshot.workspace_enabled,im_full_access_enabled:snapshot.im_full_access_enabled,
        ...(typeof snapshot.system_prompt==='string'?{system_prompt:snapshot.system_prompt}:{})};
      if(!active)throw new Error('HTTP_ABORTED');
      if(sequence===configRequest)setConfig(next);
      return next;
    };
    configOwner.current=refreshConfiguration;
    void (async()=>{
      try {
        const facts=await BackendRuntimeManager.ensureStarted();
        if(!active)return;
        setOrigin(facts.localWebOrigin);
        const results=await Promise.allSettled([
          refreshConfiguration(),
          refreshCatalog(),
        ]);
        if(active)setError([
          results[0].status==='rejected'?'配置暂时无法读取，请重试。':'',
          results[1].status==='rejected'?'Agent目录暂时无法读取。':'',
        ].filter(Boolean).join(' '));
      } catch {
        if(active)setError('本机服务暂时无法打开，请重试。');
      } finally {
        if(active)setLoading(false);
      }
    })();
    return()=>{active=false;controller.abort();};
  },[revision,transport]);
  return {origin,config,configLoaded:config!==undefined,decks,error,loading,revision,retry,refreshDecks,refreshConfig};
}
