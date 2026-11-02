// [Input] Original historical message summaries, selected Thread and an optional platform HTTP transport.
// [Output] Bounded canonical process details shared by Web and Native, including MCP App parts outside collapsed history.
// [Pos] Read-only historical process owner; original endpoint, turn/final matching and retry semantics remain.
import {useCallback,useEffect,useRef,useState} from 'react';
import type {UIMessage} from 'ai';
import {projectHistoricalAssistantTurn} from './assistantTurnHistory';
import {fetchClaudeThreadMessageProcess} from './threadSessionHydration';
export type HistoricalProcessDetailState={readonly status:'loading'}|{readonly status:'loaded';readonly message:UIMessage}|{readonly status:'error';readonly error:Error};
export function useHistoricalChatProcess(threadId:string,messages:UIMessage[],historicalMessageIds:ReadonlySet<string>,transport:typeof fetch=fetch){
  const [details,setDetails]=useState<Record<string,HistoricalProcessDetailState>>({});
  const controllers=useRef(new Map<string,AbortController>()),owner=useRef(threadId);owner.current=threadId;
  useEffect(()=>{const readers=controllers.current;setDetails({});return()=>{readers.forEach(controller=>controller.abort());readers.clear();};},[threadId]);
  const load=useCallback(async(summary:UIMessage)=>{
    const key=`${threadId}:${summary.id}`,projection=projectHistoricalAssistantTurn(summary);
    if(!projection?.deferredProcess||controllers.current.has(key)||details[key]?.status==='loaded')return;
    const controller=new AbortController();controllers.current.set(key,controller);setDetails(current=>({...current,[key]:{status:'loading'}}));
    try{
      const detail=await fetchClaudeThreadMessageProcess(threadId,summary.id,controller.signal,transport),next=projectHistoricalAssistantTurn(detail);
      const a=summary.parts[projection.finalPartIndex],b=next?detail.parts[next.finalPartIndex]:undefined;
      if(!next||next.deferredProcess||!next.processAvailable||next.turnKey!==projection.turnKey||a?.type!=='text'||b?.type!=='text'||a.text!==b.text)throw Error('Historical process detail does not match its final message.');
      if(!controller.signal.aborted&&owner.current===threadId)setDetails(current=>({...current,[key]:{status:'loaded',message:detail}}));
    }catch(reason){if(!controller.signal.aborted&&owner.current===threadId)setDetails(current=>({...current,[key]:{status:'error',error:reason instanceof Error?reason:Error('Historical process detail could not be loaded.')}}));}
    finally{if(controllers.current.get(key)===controller)controllers.current.delete(key);}
  },[details,threadId,transport]);
  useEffect(()=>{
    let remaining=4-controllers.current.size;
    for(const message of messages){if(remaining<=0)break;const key=`${threadId}:${message.id}`;
      if(!historicalMessageIds.has(message.id)||details[key]||!projectHistoricalAssistantTurn(message)?.deferredProcess)continue;
      remaining--;void load(message);
    }
  },[historicalMessageIds,details,load,messages,threadId]);
  return {details,load};
}
