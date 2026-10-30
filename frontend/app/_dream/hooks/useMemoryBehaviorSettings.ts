// [Sync] 2026-10-29: retain default adapter identity per hook instance under the production minifier.
// [Input] Original Memory responses DTOs, revision, request ID and receipt HTTP contracts.
// [Output] Shared draft/save/retry state with owner-scoped pending recovery and abort cleanup.
// [Pos] Web/native application hook; platform adapters supply transport, pending storage and UUID only.
// [Sync] 2026-10-29: extract the existing Settings lifecycle without changing backend behavior.
import {useCallback,useEffect,useRef,useState} from 'react';
import {API_BASE} from '../lib/apiBase';
import {browserRequestHeaders} from '../lib/browserSession';
export type MemoryThemeId='THEME_FRUSTRATION'|'THEME_DEFENSE'|'THEME_PRESSURE'|'THEME_VALUE';
export type MemoryBehaviorDesired={enabled:boolean;themes:Record<MemoryThemeId,{enabled:boolean;action:string}>};
export type MemoryBehaviorSnapshot={owner_id:string;revision:number;taxonomy_revision:string;default:MemoryBehaviorDesired;desired:MemoryBehaviorDesired;updated_at:string|null;catalog:{id:MemoryThemeId;label:string;actions:string[];default_action:string}[]};
export type MemoryBehaviorCommand={owner:string;requestId:string;input:{expected_revision:number;desired:MemoryBehaviorDesired}};
export const MEMORY_BEHAVIOR_PENDING_KEY='ink-memory-behavior-pending-v1';
export const MEMORY_BEHAVIOR_ACTIONS:Record<string,[string,string]>={
  acknowledge_then_help:['先回应感受，再提供帮助','Acknowledge, then help'],
  help_only:['直接帮助当前任务','Help with the current task'],
  ask_support_type:['任务不明确时询问需要哪种支持','Ask about support when the task is unclear'],
  respect_distance:['尊重距离，不追问心理话题','Respect distance without probing'],
  prioritize_actions:['梳理优先顺序和下一步','Prioritize actions and next steps'],
  connect_goal_to_choice:['结合目标解释选择与取舍','Connect goals to choices'],
  acknowledge_only:['简短回应当前表达的需要','Briefly acknowledge the expressed need'],
};
export const MEMORY_BEHAVIOR_THEMES:Record<MemoryThemeId,string>={THEME_FRUSTRATION:'Frustration',THEME_DEFENSE:'Defense',THEME_PRESSURE:'Pressure',THEME_VALUE:'Value'};
export function cloneMemoryBehavior(value:MemoryBehaviorDesired):MemoryBehaviorDesired {
  return {...value,themes:Object.fromEntries(Object.entries(value.themes).map(([key,option])=>[key,{...option}])) as MemoryBehaviorDesired['themes']};
}
export interface MemoryBehaviorPendingStore {read:()=>string|null;write:(value:string)=>void;clear:()=>void}
const browserStore:MemoryBehaviorPendingStore={read:()=>sessionStorage.getItem(MEMORY_BEHAVIOR_PENDING_KEY),write:value=>sessionStorage.setItem(MEMORY_BEHAVIOR_PENDING_KEY,value),clear:()=>sessionStorage.removeItem(MEMORY_BEHAVIOR_PENDING_KEY)};
const browserTransport:typeof fetch=(...args)=>fetch(...args);
const browserRequestId=()=>crypto.randomUUID();
function savedCommand(store:MemoryBehaviorPendingStore,owner:string):MemoryBehaviorCommand|null {
  try {const raw=store.read(),command=raw?JSON.parse(raw) as MemoryBehaviorCommand:null;
    return command?.owner===owner&&typeof command.requestId==='string'&&command.input?.desired&&Number.isSafeInteger(command.input.expected_revision)?command:null;
  }catch{return null;}
}
export default function useMemoryBehaviorSettings(options:{zh:boolean;transport?:typeof fetch;pendingStore?:MemoryBehaviorPendingStore;newRequestId?:()=>string|Promise<string>;onSessionExpired?:()=>void}) {
  // Keep default adapter identity across renders, including production builds
  // that inline a single-use function into a default parameter expression.
  const defaults=useRef({transport:browserTransport,pendingStore:browserStore,newRequestId:browserRequestId});
  const {zh,onSessionExpired}=options,transport=options.transport??defaults.current.transport,pendingStore=options.pendingStore??defaults.current.pendingStore,newRequestId=options.newRequestId??defaults.current.newRequestId;
  const words=(cn:string,en:string)=>zh?cn:en;
  const [snapshot,setSnapshot]=useState<MemoryBehaviorSnapshot|null>(null),[draft,setDraft]=useState<MemoryBehaviorDesired|null>(null),[pending,setPending]=useState<MemoryBehaviorCommand|null>(null);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(false),[conflict,setConflict]=useState(false);
  const generation=useRef(0),busyOwner=useRef(false),controllers=useRef(new Set<AbortController>()),sessionExpired=useRef(onSessionExpired);sessionExpired.current=onSessionExpired;
  const request=useCallback(async(path:string,init:RequestInit={})=>{const response=await transport(path,init);if(response.status===401)sessionExpired.current?.();return response;},[transport]);
  const load=useCallback(async()=>{
    const revision=++generation.current;controllers.current.forEach(controller=>controller.abort());controllers.current.clear();
    const controller=new AbortController();controllers.current.add(controller);busyOwner.current=true;setBusy(true);setError(false);setConflict(false);
    try {
      const response=await request(`${API_BASE}/api/memory/behavior`,{headers:browserRequestHeaders(),signal:controller.signal});if(!response.ok)throw Error('read');
      const current=await response.json() as MemoryBehaviorSnapshot;if(revision!==generation.current||controller.signal.aborted)return;
      setSnapshot(current);setDraft(cloneMemoryBehavior(current.desired));const command=savedCommand(pendingStore,current.owner_id);setPending(command);
      setMessage(command?(zh?'上次保存结果尚未核实。可核实保存结果，或读取最新设置。':'The previous save is unverified. Check its result or load current settings.'):'');
    }catch{if(revision===generation.current&&!controller.signal.aborted){setError(true);setMessage(zh?'暂时无法读取设置，请重试。':'Settings could not be loaded. Please retry.');}}
    finally{controllers.current.delete(controller);if(revision===generation.current&&!controller.signal.aborted){busyOwner.current=false;setBusy(false);}}
  },[zh,pendingStore,request]);
  useEffect(()=>{void load();return()=>{generation.current++;controllers.current.forEach(controller=>controller.abort());controllers.current.clear();};},[load]);
  function clearCommand(command:MemoryBehaviorCommand){const stored=savedCommand(pendingStore,command.owner);if(stored?.requestId===command.requestId)pendingStore.clear();}
  function finish(result:MemoryBehaviorSnapshot,command:MemoryBehaviorCommand){
    if(result.owner_id!==command.owner)throw Error('owner');
    setSnapshot(result);setDraft(cloneMemoryBehavior(result.desired));setConflict(false);
    try{clearCommand(command);setPending(null);setError(false);setMessage(words('已保存，下一次回应使用此设置。','Saved. These settings apply to the next response.'));}
    catch{setPending(command);setError(true);setMessage(words('已保存。设备恢复记录未能清除，请核实保存结果。','Saved. The device recovery record could not be cleared. Check the save result.'));}
  }
  async function submit(command:MemoryBehaviorCommand){
    if(busyOwner.current)return;const revision=generation.current,controller=new AbortController();controllers.current.add(controller);busyOwner.current=true;setBusy(true);setError(false);
    try{pendingStore.write(JSON.stringify(command));}catch{controllers.current.delete(controller);busyOwner.current=false;setBusy(false);setError(true);setMessage(words('保存请求未发出，设备恢复记录无法保存。请重试。','The save was not sent because its device recovery record could not be saved. Please retry.'));return;}
    setPending(command);
    const current=()=>revision===generation.current&&!controller.signal.aborted;
    try {
      const response=await request(`${API_BASE}/api/memory/behavior`,{method:'PUT',headers:{'Content-Type':'application/json','X-Request-ID':command.requestId,...browserRequestHeaders()},body:JSON.stringify(command.input),signal:controller.signal});
      if(!current())return;
      if(response.ok){const result=await response.json() as MemoryBehaviorSnapshot;if(current())finish(result,command);}
      else{
        const body=await response.json().catch(()=>({})) as {detail?:{outcome_unknown?:boolean}};if(!current())return;setError(true);
        if(response.status===409){
          clearCommand(command);setPending(null);setConflict(true);
          const latest=await request(`${API_BASE}/api/memory/behavior`,{headers:browserRequestHeaders(),signal:controller.signal}).catch(()=>null);
          if(latest?.ok){const result=await latest.json() as MemoryBehaviorSnapshot;if(current()&&result.owner_id===command.owner)setSnapshot(result);}
          if(current())setMessage(words('设置已在其他位置更新。草稿已保留；核对已保存值后再保存，或读取最新设置。','Settings changed elsewhere. Your draft is preserved; review saved values before saving or load current settings.'));
        }else if(body.detail?.outcome_unknown||response.status>=500){setMessage(words('保存结果尚未核实。请核实结果或重试同一次保存。','The save result is unverified. Check it or retry the same save.'));}
        else{clearCommand(command);setPending(null);setMessage(words('保存未完成，请稍后重试。','Settings were not saved. Please retry.'));}
      }
    }catch{if(current()){setError(true);setMessage(words('连接中断，保存结果尚未核实。请核实结果或重试同一次保存。','Connection interrupted. Check the result or retry the same save.'));}}
    finally{controllers.current.delete(controller);if(current()){busyOwner.current=false;setBusy(false);}}
  }
  async function save(){
    if(!snapshot||!draft||pending||busyOwner.current)return;const revision=generation.current,owner=snapshot.owner_id,input={expected_revision:snapshot.revision,desired:cloneMemoryBehavior(draft)};
    busyOwner.current=true;setBusy(true);setError(false);
    try{const requestId=await newRequestId();if(revision!==generation.current)return;busyOwner.current=false;await submit({owner,requestId,input});}
    catch{if(revision===generation.current){busyOwner.current=false;setBusy(false);setError(true);setMessage(words('保存请求未发出，请重试。','The save was not sent. Please retry.'));}}
  }
  async function check(){
    if(!pending||busyOwner.current)return;const command=pending,revision=generation.current,controller=new AbortController();controllers.current.add(controller);busyOwner.current=true;setBusy(true);
    const current=()=>revision===generation.current&&!controller.signal.aborted;
    try{const response=await request(`${API_BASE}/api/memory/behavior/receipt/${encodeURIComponent(command.requestId)}`,{headers:browserRequestHeaders(),signal:controller.signal});if(!response.ok)throw Error('receipt');
      const receipt=await response.json() as {status:string;result:MemoryBehaviorSnapshot|null};if(!current())return;
      if(receipt.status==='committed'&&receipt.result)finish(receipt.result,command);else{setError(true);setMessage(words('尚未找到保存回执。可以重试同一次保存。','No save receipt was found. You can retry the same save.'));}
    }catch{if(current()){setError(true);setMessage(words('暂时无法核实保存结果。','The save result could not be checked.'));}}
    finally{controllers.current.delete(controller);if(current()){busyOwner.current=false;setBusy(false);}}
  }
  function loadCurrent(){if(busyOwner.current)return;try{if(pending)clearCommand(pending);setPending(null);void load();}catch{setError(true);setMessage(words('设备恢复记录未能清除，请重试。','The device recovery record could not be cleared. Please retry.'));}}
  return {snapshot,draft,setDraft,pending,busy,message,error,conflict,load,submit,save,check,loadCurrent,dirty:Boolean(snapshot&&draft&&JSON.stringify(draft)!==JSON.stringify(snapshot.desired))};
}
