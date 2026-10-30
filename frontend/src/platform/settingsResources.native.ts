// [Input] Original connector/MCP APIs, public account owner and existing native HTTP/AppState/Settings facilities.
// [Output] One account-scoped resource API, visible-page observation and system OAuth handoff owner.
// [Pos] Concrete Settings platform adapter; original server/SDK own permissions, task state, PKCE and credentials.
// [Sync] 2026-10-29: persist only the original bounded operation ID; dispose local reads/UI without cancelling server business.
import {AppState,NativeModules,Platform,Settings} from 'react-native';
import {createResourceConnectorApi} from '../../app/_dream/api/resourceConnectorApi';
import {createClaudeMcpApi,type ClaudeMcpOperation} from '../../app/_dream/api/claudeMcpApi';
import type {ConnectorStatusObservation} from '../../app/_dream/hooks/useConnectorStatusRefresh';
import {MCP_OAUTH_OPERATION_STORAGE_KEY as KEY,MCP_OAUTH_OPERATION_ID_MAX_LENGTH as MAX_ID} from '../../app/_dream/components/claude-mcp/oauthHandoff';
import {clientFetch} from './transport';

export function createNativeSettingsResources(ownerId:string,onSessionExpired:()=>void,transport:typeof fetch=clientFetch){
 if(!ownerId)throw Error('RESOURCE_OWNER_REQUIRED');
 let disposed=false,pageVisible=false,appActive=AppState.currentState==='active',pendingAuthorization:string|null=null;
 const readers=new Set<AbortController>(),visibilityListeners=new Set<()=>void>(),observers=new Set<{refresh:()=>void;visible:()=>void}>();
 const isVisible=()=>!disposed&&pageVisible&&appActive;
 const visibilityChanged=()=>{visibilityListeners.forEach(listener=>listener());observers.forEach(observer=>observer.visible());};
 const stateSubscription=AppState.addEventListener('change',state=>{const next=state==='active';if(next!==appActive){appActive=next;visibilityChanged();}});
 function record():{owner_id:string;value:string}|null{
  if(Platform.OS!=='ios'||disposed)return null;
  try{const raw=Settings.get(KEY);if(typeof raw!=='string'||!raw)return null;const value:unknown=JSON.parse(raw);if(typeof value!=='object'||value===null)return null;const item=value as Record<string,unknown>;return item.owner_id===ownerId&&typeof item.value==='string'&&item.value.length>0&&item.value.length<=MAX_ID?{owner_id:ownerId,value:item.value}:null;}catch{return null;}
 }
 const remember=(id:string)=>{if(disposed||Platform.OS!=='ios'||!id||id.length>MAX_ID)return false;try{Settings.set({[KEY]:JSON.stringify({owner_id:ownerId,value:id})});return record()?.value===id;}catch{return false;}};
 const forget=(id?:string)=>{const current=record();if(!current||(id!==undefined&&current.value!==id))return;try{Settings.set({[KEY]:''});}catch{/* Original server operation still owns expiry. */}};
 const read:typeof fetch=async(input,init={})=>{
  if(disposed)throw Error('RESOURCE_OWNER_CLOSED');
  const controller=(init.method??'GET').toUpperCase()==='GET'?new AbortController():null;
  const abort=()=>controller?.abort();
  if(controller){readers.add(controller);init.signal?.addEventListener('abort',abort,{once:true});if(init.signal?.aborted)controller.abort();}
  try{const response=await transport(input,controller?{...init,signal:controller.signal}:init);if(response.status===401&&!disposed)onSessionExpired();return response;}
  finally{if(controller){readers.delete(controller);init.signal?.removeEventListener('abort',abort);}}
 };
 const connector=createResourceConnectorApi(read,()=>{if(!disposed)observers.forEach(observer=>observer.refresh());});
 const mcp=createClaudeMcpApi(read);
 const observation:ConnectorStatusObservation={hidden:()=>!isVisible(),subscribe(refresh,visible){const observer={refresh,visible};if(!disposed)observers.add(observer);return()=>{observers.delete(observer);};}};
 async function authorize(operation:ClaudeMcpOperation){
  if(disposed||pendingAuthorization)throw Error('MCP_AUTH_UNAVAILABLE');
  if(!operation.authorization_url||operation.state!=='waiting_for_user'||!remember(operation.id)||typeof NativeModules.InkRuntime?.presentMcpAuthorization!=='function')throw Error('MCP_AUTH_UNAVAILABLE');
  pendingAuthorization=operation.id;
  try{
   const callback:unknown=await NativeModules.InkRuntime.presentMcpAuthorization({operationId:operation.id,authorizationUrl:operation.authorization_url});
   if(disposed||record()?.value!==operation.id)throw Error('MCP_AUTH_OWNER_CHANGED');
   if(typeof callback!=='string'||!callback)throw Error('MCP_AUTH_CALLBACK_INVALID');
   await mcp.submitClaudeMcpRedirect(operation.id,callback);
   forget(operation.id);
  }catch(error){
   if(!disposed&&typeof error==='object'&&error!==null&&'code' in error&&error.code==='MCP_AUTH_CANCELLED'){
    await mcp.cancelClaudeMcpAuth(operation.id);forget(operation.id);return;
   }
   throw error;
  }finally{if(pendingAuthorization===operation.id)pendingAuthorization=null;}
 }
 return {connector,mcp,observation,remember,forget,authorize,isVisible,
  watchVisibility(listener:()=>void){visibilityListeners.add(listener);return()=>{visibilityListeners.delete(listener);};},
  setVisible(visible:boolean){if(!disposed&&pageVisible!==visible){pageVisible=visible;visibilityChanged();}},
  dispose(){if(disposed)return;disposed=true;stateSubscription.remove();readers.forEach(controller=>controller.abort());readers.clear();if(pendingAuthorization)NativeModules.InkRuntime?.cancelMcpAuthorization?.(pendingAuthorization);visibilityListeners.clear();observers.clear();},
 };
}
export type NativeSettingsResources=ReturnType<typeof createNativeSettingsResources>;
