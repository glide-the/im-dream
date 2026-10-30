// [Input] Explicit account-login completion and AppState events owned by the technical harness.
// [Output] RNW presentation with observable native login Promise and runtime-start boundaries.
// [Pos] Test-only platform facade; UIKit dismissal and real account login are separately verified.
export * from './appearance-platform-web-boundary';
const f=(window as any).__sessionPlatform??=((window as any).__sessionPlatform={presented:0,starts:0,listeners:new Set<(state:string)=>void>(),pending:null as null|{resolve:()=>void;reject:(value:{code:string})=>void}});
export const AppState={addEventListener(_event:string,fn:(state:string)=>void){f.listeners.add(fn);return{remove:()=>f.listeners.delete(fn)};}};
f.active=()=>f.listeners.forEach((fn:(state:string)=>void)=>fn('active'));
f.finish=()=>{const pending=f.pending;f.pending=null;pending?.resolve();};
f.cancel=(code='LOGIN_CANCELLED')=>{const pending=f.pending;f.pending=null;pending?.reject({code});};
export const NativeModules={InkRuntime:{ensureStarted:async()=>{f.starts++;return {state:'ready',localWebOrigin:'http://localhost:5173'};},presentLogin:()=>{f.presented++;return new Promise<void>((resolve,reject)=>{f.pending={resolve,reject};});}}};
