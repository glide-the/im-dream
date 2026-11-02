// [Input] Existing theme key, iOS Settings and React Native application appearance.
// [Output] Persisted native theme mode, effective appearance and change subscriptions.
// [Pos] Native counterpart of theme.ts; More changes the local preference without a server write.
import {Appearance} from 'react-native';
import {readInterfacePreference,writeInterfacePreference,watchInterfacePreference} from '../../../src/platform/interfaceSettings';
import {STORAGE_KEYS} from '../constants/storageKeys';
export type Theme='light'|'dark';
export type ThemeMode=Theme|'system';

type ThemeListener=(resolved:Theme,mode:ThemeMode)=>void;
const listeners=new Set<ThemeListener>();
let initialized=false;
function valid(value:unknown):value is ThemeMode {return value==='light'||value==='dark'||value==='system';}
export function getThemeMode():ThemeMode {
  const stored=readInterfacePreference(STORAGE_KEYS.THEME);
  return valid(stored)?stored:'system';
}
export function getTheme():Theme {
  const mode=getThemeMode();
  return mode==='system'?(Appearance.getColorScheme()==='dark'?'dark':'light'):mode;
}
export function hasExplicitTheme():boolean {return getThemeMode()!=='system';}
function notify():void {const mode=getThemeMode(),resolved=getTheme();listeners.forEach(listener=>listener(resolved,mode));}
function apply():void {const mode=getThemeMode();Appearance.setColorScheme(mode==='system'?null:mode);}
export function setThemeMode(mode:ThemeMode):void {
  if(!valid(mode))throw new Error('THEME_MODE_INVALID');
  writeInterfacePreference(STORAGE_KEYS.THEME,mode);apply();notify();
}
export function setTheme(theme:Theme):void {setThemeMode(theme);}
export function toggleTheme():Theme {const next=getTheme()==='dark'?'light':'dark';setThemeMode(next);return next;}
export function onThemeChange(listener:ThemeListener):()=>void {listeners.add(listener);return()=>{listeners.delete(listener);};}
export function initTheme():void {
  apply();
  if(initialized)return;
  initialized=true;
  Appearance.addChangeListener(()=>notify());
  watchInterfacePreference(STORAGE_KEYS.THEME,()=>{apply();notify();});
}
