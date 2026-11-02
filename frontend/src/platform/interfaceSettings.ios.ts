// [Input] Original local display preference keys and React Native's built-in iOS Settings.
// [Output] Synchronous UserDefaults reads/writes and removable external-change subscriptions.
// [Pos] iOS persistence adapter; no account/session tokens or business data are stored here.
import {Settings} from 'react-native';
import type {InterfacePreferenceKey} from './interfaceSettings';
export function readInterfacePreference(key:InterfacePreferenceKey):unknown {return Settings.get(key);}
export function writeInterfacePreference(key:InterfacePreferenceKey,value:string):void {Settings.set({[key]:value});}
export function watchInterfacePreference(key:InterfacePreferenceKey,changed:()=>void):()=>void {const watch=Settings.watchKeys(key,changed);return()=>Settings.clearWatch(watch);}
