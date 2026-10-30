// [Input] Isolated native-appearance fixture platform methods installed before module evaluation.
// [Output] React Native Web UI plus explicit iOS Settings and Appearance substitutes.
// [Pos] Test-only module boundary; production native modules and Settings.ios.ts remain unchanged.
export * from 'react-native-web';
import {useSyncExternalStore} from 'react';
// Vite may evaluate this facade through a prebundle and a direct source import.
// Both imports share one explicit fixture device, matching a native module singleton.
const device=(window as any).__appearancePlatform??=((window as any).__appearancePlatform={listeners:new Set<()=>void>(),watches:new Map<number,{key:string;fn:()=>void}>(),watchId:0,override:null as 'light'|'dark'|null});
const listeners:Set<()=>void>=device.listeners,watches:Map<number,{key:string;fn:()=>void}>=device.watches;
const prefix='ink-appearance-fixture:';
const f=(window as any).__appearanceFixture??=((window as any).__appearanceFixture={system:new URLSearchParams(location.search).get('system')||'light',writes:[] as object[],calls:[] as object[],status:200,networkFailure:false,storageFailure:false,expirations:0,paths:[] as string[],read:(key:string)=>JSON.parse(localStorage.getItem(prefix+key)||'null')});
const emit=()=>listeners.forEach(fn=>fn());
export const Appearance={getColorScheme:()=>device.override??f.system,setColorScheme(value:'light'|'dark'|null){device.override=value;emit();},addChangeListener(fn:()=>void){listeners.add(fn);return {remove:()=>listeners.delete(fn)};}};
export function useColorScheme(){return useSyncExternalStore(fn=>{listeners.add(fn);return()=>{listeners.delete(fn);};},Appearance.getColorScheme);}
export const Settings={get:(key:string)=>f.read(key),set(values:Record<string,string>){if(f.storageFailure)throw Error('fixture storage failure');f.writes.push({...values});for(const [key,value] of Object.entries(values))localStorage.setItem(prefix+key,JSON.stringify(value));},watchKeys(key:string,fn:()=>void){const id=++device.watchId;watches.set(id,{key,fn});return id;},clearWatch:(id:number)=>watches.delete(id)};
f.systemChange=(value:string)=>{f.system=value;emit();};
f.externalChange=(key:string,value:string)=>{localStorage.setItem(prefix+key,JSON.stringify(value));for(const watch of watches.values())if(watch.key===key)watch.fn();};
