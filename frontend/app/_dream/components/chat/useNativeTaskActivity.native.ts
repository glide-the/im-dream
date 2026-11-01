// [Input] Current Thread, visible App lifecycle and original task/plan/todo/subagent read functions.
// [Output] Account-instance task snapshots with per-source last-success retention, cancellation and foreground refresh.
// [Pos] Native reader only; original endpoints and server task state retain business ownership.
import {useEffect,useRef,useState} from 'react';
import {AppState} from 'react-native';
import {clientFetch} from '../../../../src/platform/transport.native';
import {readThreadPlan,type ThreadPlanState} from '../../hooks/useThreadPlan';
import {readThreadTodos,type ThreadTodoState} from '../../hooks/useThreadTodos';
import {readThreadSubagents,type ThreadSubagentState} from '../../hooks/useThreadSubagents';
import {getThreadScheduledTasks,type ScheduledTaskThreadSnapshot} from '../../api/scheduledTaskApi';
import {fetchTaskSessionLinks,type TaskSessionLinksSnapshot} from './taskSessionLinks';
import {TASK_ACTIVITY_REFRESH_INTERVAL_MS} from './taskActivityPresentation';
export interface NativeTaskActivityData {links?:TaskSessionLinksSnapshot;scheduled?:ScheduledTaskThreadSnapshot;subagents?:ThreadSubagentState;plan?:ThreadPlanState;todos?:ThreadTodoState}
type Source=keyof NativeTaskActivityData;
interface Snapshot {threadId:string;data:NativeTaskActivityData;failed:ReadonlySet<Source>;loading:boolean;revision:number}
const empty=(threadId:string):Snapshot=>({threadId,data:{},failed:new Set(),loading:false,revision:0});
export default function useNativeTaskActivity(threadId:string|null|undefined,{active,running,onSessionExpired,transport=clientFetch,refreshIntervalMs=TASK_ACTIVITY_REFRESH_INTERVAL_MS}:{active:boolean;running:boolean;onSessionExpired?:()=>void;transport?:typeof fetch;refreshIntervalMs?:number}){
 const [snapshot,setSnapshot]=useState(()=>empty(threadId??'')),[foreground,setForeground]=useState(AppState.currentState==='active'),[retry,setRetry]=useState(0);
 const current=useRef(snapshot),identity=useRef(threadId);current.current=snapshot;identity.current=threadId;
 const expire=useRef(onSessionExpired);expire.current=onSessionExpired;
 useEffect(()=>{const subscription=AppState.addEventListener('change',value=>setForeground(value==='active'));return()=>subscription.remove();},[]);
 useEffect(()=>{
  const id=threadId??'';setSnapshot(value=>value.threadId===id?value:empty(id));
  if(!id||!active||!foreground)return;
  let disposed=false,inFlight=false,expired=false;const controller=new AbortController();
  const request:typeof fetch=async(input,init)=>{const response=await transport(input,{...init,signal:controller.signal});if(response.status===401&&!expired&&!disposed&&!controller.signal.aborted&&identity.current===id){expired=true;expire.current?.();}return response;};
  async function read(){
   if(disposed||inFlight)return;inFlight=true;
   setSnapshot(value=>value.threadId===id?{...value,loading:true}:empty(id));
   const options={transport:request,signal:controller.signal};
   const operations:{[K in Source]:()=>Promise<NativeTaskActivityData[K]>}={
    links:()=>fetchTaskSessionLinks(id,options),scheduled:()=>getThreadScheduledTasks(id,options),
    subagents:()=>readThreadSubagents(id,options),
    plan:()=>readThreadPlan(id,options,()=>current.current.threadId===id?current.current.data.plan?.planMode??'none':'none'),
    todos:()=>readThreadTodos(id,options),
   };
   const keys=Object.keys(operations) as Source[];
   await Promise.allSettled(keys.map(async key=>{
    try {
     const value=await operations[key]();
     if(!disposed&&!controller.signal.aborted&&identity.current===id)setSnapshot(previous=>{
      const same=previous.threadId===id?previous:empty(id),failed=new Set(same.failed);failed.delete(key);
      return {...same,data:{...same.data,[key]:value},failed};
     });
    } catch {
     if(!disposed&&!controller.signal.aborted&&identity.current===id)setSnapshot(previous=>{
      const same=previous.threadId===id?previous:empty(id);return {...same,failed:new Set(same.failed).add(key)};
     });
    }
   }));
   if(!disposed&&!controller.signal.aborted&&identity.current===id)setSnapshot(previous=>({...previous,loading:false,revision:previous.revision+1}));
   inFlight=false;
  }
  void read();const timer=setInterval(()=>void read(),refreshIntervalMs);
  return()=>{disposed=true;controller.abort();clearInterval(timer);};
 },[threadId,active,foreground,running,retry,transport,refreshIntervalMs]);
 const visible=snapshot.threadId===(threadId??'')?snapshot:empty(threadId??'');
 return {...visible,foreground,refresh:()=>setRetry(value=>value+1),transport};
}
export type NativeTaskActivity=ReturnType<typeof useNativeTaskActivity>;
