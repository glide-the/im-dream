// [Input] One of the three original local display preference keys.
// [Output] Original defaults for platforms without an installed preference adapter; writes fail explicitly.
// [Pos] Platform boundary; Metro selects interfaceSettings.ios.ts for iOS.
export type InterfacePreferenceKey='ink-theme'|'ink-language'|'show-energy-bar';
export function readInterfacePreference(_key:InterfacePreferenceKey):unknown {return undefined;}
export function writeInterfacePreference(_key:InterfacePreferenceKey,_value:string):void {throw new Error('NATIVE_INTERFACE_STORAGE_UNAVAILABLE');}
export function watchInterfacePreference(_key:InterfacePreferenceKey,_changed:()=>void):()=>void {return()=>undefined;}
