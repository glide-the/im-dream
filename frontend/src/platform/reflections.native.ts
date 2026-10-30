// [Input] Validated public user ID, original Reflections keys/API and existing native HTTP/UUID facilities.
// [Output] Per-owner native recovery storage and one disposable Reflections API instance with incremental SSE.
// [Pos] Concrete iOS adapter; server tasks, authentication and permission decisions remain with their original owners.
// [Sync] 2026-10-29: use built-in Settings and Foundation UUID; no database, server process or new business endpoint.
import {NativeModules,Platform,Settings} from 'react-native';
import i18n from '../../app/_dream/i18n';
import {STORAGE_KEYS} from '../../app/_dream/constants/storageKeys';
import {createReflectionsApi,type ReflectionsStorage} from '../../app/_dream/api/reflectionsApi';
import {clientFetch,openResponse} from './transport';
const keys=new Set<string>([STORAGE_KEYS.ANALYSIS_REPORTS,STORAGE_KEYS.REFLECTIONS_ACTIVE_TASK,STORAGE_KEYS.REFLECTIONS_PENDING_SUBMISSION,STORAGE_KEYS.REFLECTIONS_ANALYSIS_CLICKED_DATE]);
export function createNativeReflections(ownerId:string,onSessionExpired?:()=>void) {
  if(!ownerId)throw Error('REFLECTIONS_OWNER_REQUIRED');
  const abort=new AbortController();
  function check(key:string){if(Platform.OS!=='ios')throw Error('REFLECTIONS_STORAGE_UNAVAILABLE');if(abort.signal.aborted)throw Error('REFLECTIONS_OBSERVATION_CLOSED');if(!keys.has(key))throw Error('REFLECTIONS_STORAGE_KEY_INVALID');}
  const storage:ReflectionsStorage={
    getItem(key){check(key);const raw=Settings.get(key);if(typeof raw!=='string'||!raw)return null;try{const record:unknown=JSON.parse(raw);if(typeof record!=='object'||record===null)return null;const value=record as Record<string,unknown>;return value.owner_id===ownerId&&typeof value.value==='string'?value.value:null;}catch{return null;}},
    setItem(key,value){check(key);Settings.set({[key]:JSON.stringify({owner_id:ownerId,value})});},
    removeItem(key){check(key);Settings.set({[key]:''});},
  };
  const transport:typeof fetch=async(input,init)=>{const response=await clientFetch(input,init);if(response.status===401)onSessionExpired?.();return response;};
  const api=createReflectionsApi({transport,storage,signal:abort.signal,language:()=>i18n.language||'en',
    newRequestId:async()=>{if(typeof NativeModules.InkRuntime?.randomUUID!=='function')throw Error('NATIVE_UUID_UNAVAILABLE');return NativeModules.InkRuntime.randomUUID();},
    openEvents:async(path,init)=>{const stream=await openResponse(path,init);if(stream.status===401)onSessionExpired?.();return stream;},
  });
  return {api,storage,dispose:()=>abort.abort()};
}
