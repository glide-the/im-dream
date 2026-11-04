// [Input] Original shared v4.2 face paths, display mode, semantic colors and visible foreground state.
// [Output] One integrated character/clock used by both startup and idle presentation.
// [Pos] Shared artwork boundary; iOS Core Animation owns keyframes without JS frame work.
// [Sync] 2026-11-03: unify the face and dial; remove the independent outer clock and whole-image breathing loop.
import {useEffect,useState} from 'react';
import {AppState,Platform,requireNativeComponent,UIManager,View,type ColorValue,type ViewProps} from 'react-native';
import Svg,{Circle,G,Line,Path} from 'react-native-svg';
import artwork from '../assets/startup-artwork.json';
import useInkColors from './useInkColors.native';
export type ArtworkMode='clock'|'happy'|'sad';
type Props={visible:boolean;size?:number;mode?:ArtworkMode;expression?:'happy'|'sad'};
type NativeProps=ViewProps&{enabled:boolean;clockMode:ArtworkMode;faceMood:'happy'|'sad';colorInk:ColorValue;colorMinute:ColorValue;colorSecond:ColorValue;colorPaper:ColorValue};
const NativeClock=Platform.OS==='ios'&&UIManager.getViewManagerConfig?.('InkKastentionClock')?requireNativeComponent<NativeProps>('InkKastentionClock'):null;
export default function StartupArtwork({visible,size=176,mode='happy',expression='happy'}:Props){
  const c=useInkColors(),[now,setNow]=useState(()=>new Date()),[active,setActive]=useState(AppState.currentState==='active');
  useEffect(()=>{if(NativeClock)return;const listener=AppState.addEventListener('change',state=>setActive(state==='active'));return()=>listener.remove();},[]);
  useEffect(()=>{if(NativeClock||!visible||!active)return;let timer:ReturnType<typeof setTimeout>;let disposed=false;
    const update=()=>{if(disposed)return;setNow(new Date());timer=setTimeout(update,1000-Date.now()%1000+4);};update();
    return()=>{disposed=true;clearTimeout(timer);};},[visible,active]);
  const common={testID:'startup-artwork',accessible:false,accessibilityElementsHidden:true,importantForAccessibility:'no-hide-descendants' as const,style:{width:size,height:size,backgroundColor:'transparent',borderWidth:0}};
  if(NativeClock)return <NativeClock {...common} enabled={visible} clockMode={mode} faceMood={expression} colorInk={c['color-text-primary']} colorMinute={c['color-text-secondary']} colorSecond={c['color-action-link']} colorPaper={c['color-bg-paper']}/>;
  const sad=mode==='sad'||(mode==='clock'&&expression==='sad');
  return <View {...common}><Svg width="100%" height="100%" viewBox={artwork.viewBox} color={c['color-text-primary']} fill="none" strokeLinecap="round" strokeLinejoin="round">
    {artwork.paths.map((shape,index)=><Path key={index} {...shape} d={index===6&&sad?'M 495 746 C 528 680 590 684 648 737':shape.d} opacity={mode==='clock'&&index>=4?0.11:1}/>)}
    {mode==='clock'?<G>{[{angle:now.getHours()%12*30,end:493,width:19,color:c['color-text-primary']},{angle:now.getMinutes()*6,end:401,width:13,color:c['color-text-secondary']},{angle:now.getSeconds()*6,end:359,width:6,color:c['color-action-link']}].map((hand,index)=><Line key={index} x1={625} y1={674} x2={625} y2={hand.end} stroke={hand.color} strokeWidth={hand.width} rotation={hand.angle} origin="625,650"/>)}<Circle cx={625} cy={650} r={13} fill={c['color-text-primary']} stroke={c['color-bg-paper']} strokeWidth={9}/></G>:null}
  </Svg></View>;
}
