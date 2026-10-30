// [Input] Original owner-scoped Memory responses recovery command and iOS Foundation UUID.
// [Output] Concrete iOS pending-record persistence and request ID generation for the shared hook.
// [Pos] One Settings domain adapter; display preferences, credentials and business HTTP remain separate.
import {NativeModules,Platform,Settings} from 'react-native';
import {MEMORY_BEHAVIOR_PENDING_KEY,type MemoryBehaviorPendingStore} from '../../app/_dream/hooks/useMemoryBehaviorSettings';
function requireStorage(){if(Platform.OS!=='ios')throw Error('MEMORY_BEHAVIOR_STORAGE_UNAVAILABLE');}
export const nativeMemoryBehaviorPendingStore:MemoryBehaviorPendingStore={
  read(){requireStorage();const value=Settings.get(MEMORY_BEHAVIOR_PENDING_KEY);return typeof value==='string'&&value?value:null;},
  write(value){requireStorage();Settings.set({[MEMORY_BEHAVIOR_PENDING_KEY]:value});},
  clear(){requireStorage();Settings.set({[MEMORY_BEHAVIOR_PENDING_KEY]:''});},
};
export async function newMemoryBehaviorRequestId():Promise<string>{
  if(typeof NativeModules.InkRuntime?.randomUUID!=='function')throw Error('NATIVE_UUID_UNAVAILABLE');
  return NativeModules.InkRuntime.randomUUID();
}
