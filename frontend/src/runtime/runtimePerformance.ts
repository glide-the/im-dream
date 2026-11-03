// [Input] Own-process native CPU counters, OS-thread counters and existing execution/request activity snapshots.
// [Output] Bounded measured CPU intervals and one foreground, visible-owner sampling loop.
// [Pos] Diagnostics-only calculation/lifecycle; no runtime startup, HTTP, task registration or persistence.
import {z} from 'zod';

export const PERFORMANCE_POLICY=Object.freeze({intervalMs:2000,timeoutMs:5000,maxSamples:120,retentionMs:240000,maxThreads:256,maxActivities:97,displayThreads:6,displayActivities:8});
const counter=z.number().finite().nonnegative().max(Number.MAX_SAFE_INTEGER);
const activitySchema=z.object({id:z.string().min(1).max(160),kind:z.enum(['command','request','runtime']),label:z.string().max(80),phase:z.string().max(48),threadId:z.string().max(32).optional()});
const rawSchema=z.object({pid:z.number().int().positive(),monotonicMs:counter,timestampMs:counter,cpuMs:counter,cores:z.number().int().positive(),thermal:z.enum(['nominal','fair','serious','critical','unknown']),simulator:z.boolean(),collectionWallMs:counter,collectionCpuMs:counter.nullable(),
  threads:z.array(z.object({id:z.string().min(1).max(32),label:z.string().max(80),cpuMs:counter})).max(PERFORMANCE_POLICY.maxThreads),threadsState:z.enum(['available','unavailable']),threadsTotal:z.number().int().nonnegative(),threadsTruncated:z.boolean(),
  activities:z.array(activitySchema).max(PERFORMANCE_POLICY.maxActivities),commandsState:z.enum(['available','busy']),activitiesTruncated:z.boolean()});
export type RawPerformanceSample=z.infer<typeof rawSchema>;
export type MeasuredThread={id:string;label:string;cpuPercent:number|null;cpuMs:number|null};
export type MeasuredActivity=z.infer<typeof activitySchema>&{cpuPercent:number|null};
export type PerformancePoint={pid:number;at:number;tick:number;intervalMs:number|null;cpuPercent:number|null;devicePercent:number|null;cores:number;thermal:RawPerformanceSample['thermal'];simulator:boolean;collectionWallMs:number;collectionCpuMs:number|null;requestWallMs:number;threads:MeasuredThread[];threadsState:RawPerformanceSample['threadsState'];threadsTotal:number;threadsTruncated:boolean;activities:MeasuredActivity[];commandsState:RawPerformanceSample['commandsState'];activitiesTruncated:boolean};
export type PerformanceState={status:'closed'|'sampling'|'paused'|'background'|'unavailable'|'failed';points:readonly PerformancePoint[];error?:string};
export const initialPerformanceState=():PerformanceState=>({status:'closed',points:[]});

export function measurePerformance(input:unknown,previous:RawPerformanceSample|undefined,requestWallMs:number):{raw:RawPerformanceSample;point:PerformancePoint} {
  const raw=rawSchema.parse(input);
  const elapsed=previous&&raw.pid===previous.pid?raw.monotonicMs-previous.monotonicMs:0;
  const valid=Boolean(previous&&elapsed>0&&raw.cpuMs>=previous.cpuMs);
  const ratio=(cpu:number)=>{const value=cpu/elapsed*100;return Number.isFinite(value)?value:null;};
  const percent=valid?ratio(raw.cpuMs-previous!.cpuMs):null;
  const before=new Map(valid&&previous?.threadsState==='available'?previous.threads.map(item=>[item.id,item.cpuMs]):[]);
  const threads=raw.threadsState==='available'?raw.threads.map(item=>{
    const old=before.get(item.id),delta=old!==undefined&&item.cpuMs>=old?item.cpuMs-old:null;
    return {id:item.id,label:item.label,cpuMs:delta,cpuPercent:delta===null?null:ratio(delta)};
  }):[];
  const byId=new Map(threads.map(item=>[item.id,item]));
  return {raw,point:{pid:raw.pid,at:raw.timestampMs,tick:raw.monotonicMs,intervalMs:valid?elapsed:null,cpuPercent:percent,devicePercent:percent!==null&&raw.cores===previous?.cores?percent/raw.cores:null,cores:raw.cores,thermal:raw.thermal,simulator:raw.simulator,
    collectionWallMs:raw.collectionWallMs,collectionCpuMs:raw.collectionCpuMs,requestWallMs,threads,threadsState:raw.threadsState,threadsTotal:raw.threadsTotal,threadsTruncated:raw.threadsTruncated,
    activities:raw.activities.map(activity=>({...activity,cpuPercent:activity.kind==='command'&&activity.threadId?byId.get(activity.threadId)?.cpuPercent??null:null})),commandsState:raw.commandsState,activitiesTruncated:raw.activitiesTruncated}};
}

export function appendPerformance(points:readonly PerformancePoint[],point:PerformancePoint):readonly PerformancePoint[] {
  const matching=points.filter(item=>item.pid===point.pid&&item.tick<point.tick&&item.tick>=point.tick-PERFORMANCE_POLICY.retentionMs);
  return [...matching,point].slice(-PERFORMANCE_POLICY.maxSamples);
}

export function createPerformanceMonitor(deps:{read:()=>Promise<unknown>;available:()=>boolean;changed:(state:PerformanceState)=>void;now?:()=>number;schedule?:(callback:()=>void,ms:number)=>unknown;cancel?:(timer:unknown)=>void}) {
  const now=deps.now??(()=>performance.now());
  const schedule=deps.schedule??((callback,ms)=>setTimeout(callback,ms));
  const cancel=deps.cancel??(timer=>clearTimeout(timer as ReturnType<typeof setTimeout>));
  const owners=new Map<symbol,boolean>();
  let state=initialPerformanceState(),previous:RawPerformanceSample|undefined,timer:unknown,pending=false,epoch=0,paused=false,running=false,abortRead:(()=>void)|undefined;
  const emit=(next:PerformanceState)=>{state=next;deps.changed(state);};
  const eligible=()=>!paused&&deps.available()&&[...owners.values()].some(Boolean);
  const stop=()=>{epoch++;previous=undefined;if(timer!==undefined)cancel(timer);timer=undefined;abortRead?.();};
  async function tick() {
    timer=undefined;
    if(pending||!eligible())return;
    pending=true;const version=epoch,started=now();
    let deadline:unknown;
    const interrupted=new Promise<never>((_resolve,reject)=>{
      deadline=schedule(()=>{deadline=undefined;reject(Error('CPU_SAMPLE_TIMEOUT'));},PERFORMANCE_POLICY.timeoutMs);
      abortRead=()=>{if(deadline!==undefined)cancel(deadline);deadline=undefined;reject(Error('CPU_SAMPLE_DEPARTED'));};
    });
    try {
      const input=await Promise.race([deps.read(),interrupted]);
      if(version!==epoch||!eligible())return;
      const measured=measurePerformance(input,previous,Math.max(0,now()-started));
      previous=measured.raw;
      emit({status:'sampling',points:appendPerformance(state.points,measured.point)});
    } catch {
      if(version===epoch&&eligible()){previous=undefined;emit({...state,status:'failed',error:'采样失败，等待下一次读取。'});}
    } finally {
      if(deadline!==undefined)cancel(deadline);
      abortRead=undefined;
      pending=false;
      if(eligible())timer=schedule(()=>void tick(),PERFORMANCE_POLICY.intervalMs);
    }
  }
  function reconcile() {
    const next=eligible();
    if(!next&&running)stop();
    const changed=next!==running;running=next;
    if(next){if(changed)emit({...state,status:'sampling',error:undefined});if(!pending&&timer===undefined)void tick();return;}
    emit({...state,status:owners.size===0?'closed':!deps.available()?'unavailable':paused?'paused':'background',error:undefined});
  }
  return {
    getSnapshot:()=>state,
    setPaused(value:boolean){paused=value;reconcile();},
    acquire(active:boolean) {
      const owner=Symbol('diagnostics-view');owners.set(owner,active);reconcile();
      return {setActive(value:boolean){if(owners.has(owner)){owners.set(owner,value);reconcile();}},release(){if(owners.delete(owner))reconcile();}};
    },
  };
}
