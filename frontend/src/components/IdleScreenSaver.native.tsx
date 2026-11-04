// [Sync] 2026-11-04: apply v3.1 borderless canvas, project typography and a separate quiet dismissal hint.
// [Sync] 2026-11-03: use the unified v4.2 artwork; the idle leaf owns layout and dismissal only.
// [Input] Shared account Thread presence, existing vector artwork, theme and observed Writing mood.
// [Output] A material-backed clock/expression over the retained business page; the closing press is consumed.
// [Pos] Presentation leaf; clock ticks only while this foreground overlay is mounted.
import {useSyncExternalStore} from 'react';
import {Platform,Pressable,requireNativeComponent,StyleSheet,UIManager,useWindowDimensions,View,type ViewProps} from 'react-native';
import InkLabel from './InkLabel.native';
import useInkColors from './useInkColors.native';
import StartupArtwork from './StartupArtwork.native';
import {BackendRuntimeManager} from '../runtime/BackendRuntimeManager';
import {idleMood} from '../runtime/idleMood';
const Backdrop=Platform.OS==='ios'&&UIManager.getViewManagerConfig?.('InkIdleBackdrop')?requireNativeComponent<ViewProps>('InkIdleBackdrop'):View;
export default function IdleScreenSaver({onClose}:{onClose:()=>void}){
  const c=useInkColors(),presence=useSyncExternalStore(BackendRuntimeManager.subscribeThreadPresence,BackendRuntimeManager.getThreadPresenceSnapshot),mood=useSyncExternalStore(idleMood.subscribe,idleMood.getSnapshot);
  const {width,height}=useWindowDimensions();
  const size=Math.min(300,width-48,height*0.48);
  const sad=mood.sad&&Boolean(mood.date)&&new Date(mood.date!).toDateString()===new Date().toDateString();
  const ink=c['color-text-primary'];
  return <View style={StyleSheet.absoluteFill} testID="idle-screen-saver">
    <Backdrop style={[StyleSheet.absoluteFill,Platform.OS!=='ios'?{backgroundColor:c['color-bg-app']}:undefined]}/>
    <View pointerEvents="none" style={[StyleSheet.absoluteFill,s.wash,{backgroundColor:c['color-bg-app']}]}/>
    <Pressable testID="idle-screen-saver-close" accessibilityRole="button" accessibilityLabel="关闭屏保" accessibilityValue={{text:presence.known?`最近确认 · 活跃 Thread：${presence.hasActiveThread?'有':'无'}`:''}} onPress={onClose} onAccessibilityEscape={onClose} style={s.cover}>
      <View pointerEvents="none" style={s.content}>
        <StartupArtwork visible size={size} mode="clock" expression={sad?'sad':'happy'}/>
        <InkLabel style={[s.brand,{color:ink}]}>Kastention</InkLabel>
        {presence.known?<InkLabel testID="idle-thread-presence" style={[s.presence,{color:c['color-text-secondary']}]}>{`最近确认 · 活跃 Thread：${presence.hasActiveThread?'有':'无'}`}</InkLabel>:null}
      </View>
      <InkLabel style={[s.hint,{color:c['color-text-secondary']}]}>点击任意位置关闭</InkLabel>
    </Pressable>
  </View>;
}
const s=StyleSheet.create({
  wash:{opacity:0.8},
  cover:{flex:1,alignItems:'center',justifyContent:'center',padding:24,paddingBottom:60},
  content:{alignItems:'center',gap:16,maxWidth:'100%'},
  brand:{fontSize:24,lineHeight:32,textAlign:'center'},
  presence:{fontSize:15,lineHeight:22,textAlign:'center'},
  hint:{position:'absolute',bottom:24,left:24,right:24,fontSize:13,lineHeight:20,textAlign:'center'},
});
