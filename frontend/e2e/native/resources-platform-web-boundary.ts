// [Input] Existing explicit iOS fixture device and synthetic system-authorization completions.
// [Output] One AppState/NativeModules boundary for resource-owner and Settings navigation qualification.
// [Pos] Technical harness only; UIKit, ASWebAuthenticationSession and UserDefaults need target acceptance.
export * from './reflections-platform-web-boundary';
import {NativeModules as OriginalModules} from './settings-platform-web-boundary';
type Completion={resolve:(value:string)=>void;reject:(error:{code:string})=>void};
const f=(window as any).__resourcePlatform??=((window as any).__resourcePlatform={state:'active',listeners:new Set<(state:string)=>void>(),prompts:[],cancelled:[],pending:new Map<string,Completion>()});
export const AppState={get currentState(){return f.state;},addEventListener(_event:string,listener:(state:string)=>void){f.listeners.add(listener);return{remove:()=>f.listeners.delete(listener)};}};
f.change=(state:string)=>{f.state=state;f.listeners.forEach((listener:(state:string)=>void)=>listener(state));};
f.finish=(id:string,url:string)=>{const completion=f.pending.get(id);f.pending.delete(id);completion?.resolve(url);};
f.cancel=(id:string)=>{const completion=f.pending.get(id);f.pending.delete(id);completion?.reject({code:'MCP_AUTH_CANCELLED'});};
export const NativeModules={InkRuntime:{...OriginalModules.InkRuntime,
 presentMcpAuthorization(options:{operationId:string;authorizationUrl:string}){f.prompts.push({...options});return new Promise<string>((resolve,reject)=>f.pending.set(options.operationId,{resolve,reject}));},
 cancelMcpAuthorization(id:string){f.cancelled.push(id);f.cancel(id);},
}};
