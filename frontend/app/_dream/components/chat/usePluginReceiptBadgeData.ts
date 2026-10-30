// [Input] Original Thread plugin receipt, Deck references and authenticated HTTP transport.
// [Output] Shared receipt polling and ready configured-plugin snapshots for Web and native metadata.
// [Pos] Read-only data lifecycle extracted from PluginReceiptBadge; plugin and Thread ownership stay on the server.
import {useEffect,useState} from 'react';
import {getThreadPluginLoadReceipt,listClaudePluginInstallations,type ClaudePluginInstallation,type PluginLoadReceipt} from '../../api/claudePluginAdminApi';
import type {Deck} from '../../api/voiceApi';

// Web keeps the original stale-result guard; native enables request cancellation.
// Preserve the existing badge's first-run packing observation window.
const RECEIPT_RETRY_MS=3000;
const MAX_RECEIPT_ATTEMPTS=40;

export default function usePluginReceiptBadgeData({threadId,deck,transport=fetch,enabled=true,abortReads=false}:{threadId:string|null;deck?:Deck;transport?:typeof fetch;enabled?:boolean;abortReads?:boolean}) {
  const [receipt,setReceipt]=useState<PluginLoadReceipt|null>(null);
  const [configuredPlugins,setConfiguredPlugins]=useState<ClaudePluginInstallation[]|null>(null);
  useEffect(()=>{setReceipt(null);},[threadId]);
  useEffect(()=>{
    if(!threadId || !enabled)return;
    let cancelled=false,attempts=0;
    let retryTimer:ReturnType<typeof setTimeout>|undefined;
    const controller=abortReads?new AbortController():undefined;
    const read:typeof fetch=(input,init)=>transport(input,controller?{...init,signal:controller.signal}:init);
    const retry=()=>{attempts++;if(!cancelled && attempts<MAX_RECEIPT_ATTEMPTS)retryTimer=setTimeout(load,RECEIPT_RETRY_MS);};
    function load() {
      void getThreadPluginLoadReceipt(threadId!,read).then(payload=>{
        if(cancelled)return;
        const packed=payload?.receipt?.plugins ?? payload?.launch_manifest?.plugins ?? [];
        if(packed.length>0){setReceipt(payload);return;}
        retry();
      }).catch(()=>{if(!cancelled)retry();});
    }
    load();
    return()=>{cancelled=true;controller?.abort();if(retryTimer!==undefined)clearTimeout(retryTimer);};
  },[threadId,transport,enabled,abortReads]);
  const hasReceiptPlugins=(receipt?.receipt?.plugins ?? receipt?.launch_manifest?.plugins ?? []).length>0;
  useEffect(()=>{
    if(!deck || hasReceiptPlugins || !enabled)return;
    let cancelled=false;
    const controller=abortReads?new AbortController():undefined;
    const read:typeof fetch=(input,init)=>transport(input,controller?{...init,signal:controller.signal}:init);
    setConfiguredPlugins(null);
    void listClaudePluginInstallations(read).then(({installations})=>{
      if(!cancelled)setConfiguredPlugins(installations.filter(installation=>installation.status==='ready'
        && (installation.deck_refs ?? []).some(ref=>ref.deck_id===deck.id && ref.enabled)));
    }).catch(()=>{if(!cancelled)setConfiguredPlugins([]);});
    return()=>{cancelled=true;controller?.abort();};
  },[deck,hasReceiptPlugins,transport,enabled,abortReads]);
  return {receipt,configuredPlugins};
}
