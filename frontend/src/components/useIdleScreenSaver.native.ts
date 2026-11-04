// [Input] Original App visibility, keyboard, modal occupation and genuine native touches.
// [Output] Idle overlay visibility and non-owning interaction observation.
// [Pos] Native presentation lifecycle; never suspends a backend or owns a Thread.
import {createContext,useContext,useEffect,useRef,useState} from 'react';
import {AppState,Keyboard,NativeModules,TextInput} from 'react-native';
import {createIdleScreenSaver} from '../runtime/idleScreenSaver';
export const IdlePresentationBlocked=createContext(false);
export default function useIdleScreenSaver(blocked:boolean,inModal:boolean,onVisible:(visible:boolean)=>void){
  const parentBlocked=useContext(IdlePresentationBlocked),latest=useRef({blocked:blocked||parentBlocked,inModal,onVisible});
  latest.current={blocked:blocked||parentBlocked,inModal,onVisible};
  const [keyboard,setKeyboard]=useState(()=>Keyboard.isVisible?.()??false);
  const [foreground,setForeground]=useState(AppState.currentState==='active');
  const [controller]=useState(()=>createIdleScreenSaver({changed:value=>latest.current.onVisible(value),eligible:async()=>{
    if(latest.current.blocked||TextInput.State.currentlyFocusedInput())return false;
    return typeof NativeModules.InkRuntime?.canShowIdleOverlay==='function'?Boolean(await NativeModules.InkRuntime.canShowIdleOverlay(latest.current.inModal)):true;
  }}));
  useEffect(()=>{const state=AppState.addEventListener('change',next=>setForeground(next==='active'));
    const shown=Keyboard.addListener('keyboardDidShow',()=>setKeyboard(true)),hidden=Keyboard.addListener('keyboardDidHide',()=>setKeyboard(false));
    return()=>{state.remove();shown.remove();hidden.remove();controller.dispose();};},[controller]);
  useEffect(()=>{controller.availability(foreground,blocked||parentBlocked||keyboard);},[controller,foreground,blocked,parentBlocked,keyboard]);
  return {activity:controller.activity,dismiss:controller.dismiss,blocked:blocked||parentBlocked||keyboard||!foreground};
}
