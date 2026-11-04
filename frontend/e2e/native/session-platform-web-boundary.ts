// [Sync] 2026-11-02: connect original account failures to runtime diagnostics and align the packaged native callback.
// [Input] Explicit account-login completion and AppState events owned by the technical harness.
// [Sync] 2026-11-03: opt-in CPU fixture emits explicit synthetic native counters; ordinary session cases keep the capability absent.
// [Sync] 2026-11-02: record diagnostics access/close calls for bridge qualification; native window geometry remains a Simulator acceptance item.
// [Output] RNW presentation with observable native login Promise and runtime-start boundaries.
// [Pos] Test-only platform facade; UIKit dismissal and real account login are separately verified.
// [Sync] 2026-11-01: hold/fail original startup and observe clipboard/lifecycle without business requests.
// [Sync] 2026-11-03: model a single unknown initial AppState read before the real active fixture state.
export * from './appearance-platform-web-boundary';
const f=(window as any).__sessionPlatform??=((window as any).__sessionPlatform={presented:0,starts:0,state:'active',copies:[] as string[],copyFails:false,listeners:new Set<(state:string)=>void>(),runtimePending:null as null|{resolve:(value:unknown)=>void;reject:(value:unknown)=>void},pending:null as null|{resolve:()=>void;reject:(value:{code:string})=>void}});
export const AppState={get currentState(){if(new URLSearchParams(location.search).has('initial-state-unknown')&&!f.initialStateRead){f.initialStateRead=true;return 'unknown';}return f.state;},addEventListener(_event:string,fn:(state:string)=>void){f.listeners.add(fn);return{remove:()=>f.listeners.delete(fn)};}};
f.change=(state:string)=>{f.state=state;f.listeners.forEach((fn:(state:string)=>void)=>fn(state));};
f.active=()=>f.change('active');
f.finish=()=>{const pending=f.pending;f.pending=null;pending?.resolve();};
f.cancel=(code='LOGIN_CANCELLED')=>{const pending=f.pending;f.pending=null;pending?.reject({code});};
const ready=()=>({state:'ready',localWebOrigin:'http://localhost:5173',privateEndpoint:'fixture-private-endpoint',token:'fixture-private-token'});
f.settleRuntime=(error?:unknown)=>{const pending=f.runtimePending;f.runtimePending=null;if(error)pending?.reject(error);else pending?.resolve(ready());};
export const NativeModules={InkRuntime:{ensureStarted:async()=>{f.starts++;if(new URLSearchParams(location.search).has('hold-runtime'))return new Promise((resolve,reject)=>{f.runtimePending={resolve,reject};});return ready();},copyText:async(value:string)=>{if(f.copyFails)throw Error('private-copy-error');f.copies.push(value);},presentLogin:()=>{f.presented++;return new Promise<void>((resolve,reject)=>{f.pending={resolve,reject};});}}};
if(new URLSearchParams(location.search).has('cpu-fixture')) {
  f.cpuCalls??=0;f.cpuTicks??=0;f.cpuFails??=false;
  Object.assign(NativeModules.InkRuntime,{readPerformanceSample:async()=>{
    f.cpuCalls++;if(f.cpuFails)throw Error('synthetic native failure');const n=++f.cpuTicks;
    return {pid:77,monotonicMs:n*2000,timestampMs:Date.now(),cpuMs:n*500,cores:4,thermal:'nominal',simulator:true,collectionWallMs:0.4,collectionCpuMs:0.2,threadsState:'available',threadsTotal:2,threadsTruncated:false,
      threads:[{id:'1',label:'主线程（共享）',cpuMs:n*200},{id:'2',label:'Node主循环（共享）',cpuMs:n*100}],
      activities:n<10?[{id:'guest:41:2',kind:'command',label:'命令实例 41 / 2',phase:'executing',threadId:'2'},{id:'http:fixture',kind:'request',label:'Chat请求',phase:'reading'}]:[],commandsState:'available',activitiesTruncated:false};
  }});
}
// Prebundled and direct imports represent the same explicitly owned fixture device.
const accountObservers:Set<(value:unknown)=>void>=f.accountObservers??=(new Set<(value:unknown)=>void>());
Object.assign(NativeModules.InkRuntime,{addListener:()=>{},removeListeners:()=>{}});
f.diagnosticsConfigurations??=[];
f.diagnosticsDismissals??=0;
Object.assign(NativeModules.InkRuntime,{
  configureDiagnosticsOverlay:(options:Record<string,unknown>)=>f.diagnosticsConfigurations.push({...options}),
  dismissRuntimeDiagnostics:()=>{f.diagnosticsDismissals++;queueMicrotask(()=>f.onDiagnosticsDismiss?.());},
});
export class NativeEventEmitter {
  addListener(name:string,listener:(value:unknown)=>void){if(name==='InkAccountError')accountObservers.add(listener);return{remove:()=>accountObservers.delete(listener)};}
}
Object.assign(f,{accountError:(source:string,error:unknown)=>accountObservers.forEach(listener=>listener({source,error}))});
