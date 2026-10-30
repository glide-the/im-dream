// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original persisted queue entry, local owner and caller-owned queue actions.
// [Output] Original guide, remove, edit and side-chat controls with native menu/keyboard dismissal.
// [Pos] Native counterpart of ThreadInputQueueCard; the existing API and lifecycle adapter own mutations.
// [Sync] 2026-10-28: retain queued/selected permissions and keep editing text until the original action succeeds.
// [Sync] 2026-10-28: constrain the detached menu to the viewport when card controls wrap onto a new line.
import {useEffect,useRef,useState} from 'react';
import {Modal,Pressable,StyleSheet,TextInput,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {IconEdit,IconMessageCircle,IconMoreHorizontal,IconTrash,IconX} from './Icons';
import type {ThreadInputEntry} from './threadInputQueue';
export interface NativeThreadInputQueueCardProps {
  entry:ThreadInputEntry;localOwner:boolean;
  onGuide:(entry:ThreadInputEntry)=>Promise<void>;
  onCancel:(entry:ThreadInputEntry)=>Promise<void>;
  onEdit:(entry:ThreadInputEntry,text:string)=>Promise<void>;
  onSideChat:(entry:ThreadInputEntry)=>Promise<void>;
}
export default function ThreadInputQueueCard({entry,localOwner,onGuide,onCancel,onEdit,onSideChat}:NativeThreadInputQueueCardProps){
  const {t}=useTranslation(),colors=useInkColors(),{width,height}=useWindowDimensions();
  const anchor=useRef<View>(null),pendingRef=useRef(false);
  const [menu,setMenu]=useState<{right:number;top:number;width:number}|null>(null),[editing,setEditing]=useState(false),[draft,setDraft]=useState(entry.text),[pending,setPending]=useState(false);
  useEffect(()=>setMenu(null),[width,height]);
  const queued=entry.status==='queued',canGuide=queued&&localOwner&&!pending,canCancel=queued&&!pending;
  const text={color:colors['color-text-primary'],fontSize:13.12},secondary={color:colors['color-text-secondary'],fontSize:13.12};
  const statusLabel=t(`chat.inputQueue.${entry.status}`)+(!localOwner&&['queued','selected','dispatching'].includes(entry.status)?` · ${t('chat.inputQueue.ownerUnverified')}`:'');
  async function run(action:()=>Promise<void>){if(pendingRef.current)return;pendingRef.current=true;setMenu(null);setPending(true);try{await action();}catch{/* The caller preserves the error and recovery draft. */}finally{pendingRef.current=false;setPending(false);}}
  function save(){const value=draft.trim();if(value&&value!==entry.text)void run(async()=>{await onEdit(entry,value);setEditing(false);});}
  function openMenu(){anchor.current?.measureInWindow((x,y,w,h)=>{const menuWidth=Math.min(208,width-16);setMenu({width:menuWidth,right:Math.max(8,Math.min(width-x-w,width-menuWidth-8)),top:Math.max(8,y>=160?y-152:Math.min(y+h+4,height-160))});});}
  const action=(label:string,enabled:boolean,onPress:()=>void,icon?:React.ReactNode,role:'button'|'menuitem'='button')=><Pressable accessibilityRole={role} accessibilityLabel={label} accessibilityState={{disabled:!enabled,busy:pending}} disabled={!enabled} onPress={onPress} style={[styles.control,{opacity:enabled?1:0.5}]}>{icon}<InkLabel style={secondary}>{label}</InkLabel></Pressable>;
  return <View testID="thread-input-queue-card" style={[styles.card,{backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-paper']}]}>
    <InkLabel style={secondary}>↳</InkLabel>
    {editing?<View style={styles.edit}>
      <TextInput autoFocus accessibilityLabel={t('chat.inputQueue.edit')} value={draft} onChangeText={setDraft} onSubmitEditing={save} editable={!pending}
        style={[styles.input,text,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]} />
      {action(t('chat.inputQueue.save'),Boolean(draft.trim())&&!pending,save)}
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputQueue.cancelEdit')} onPress={()=>{setDraft(entry.text);setEditing(false);}} style={styles.icon}><IconX width={16} height={16} color={colors['color-text-secondary']}/></Pressable>
    </View>:<>
      <InkLabel numberOfLines={1} style={[text,styles.message,{fontWeight:'600'}]}>{entry.text}</InkLabel>
      <InkLabel accessibilityLiveRegion="polite" style={[secondary,{fontSize:12.48}]}>{statusLabel}</InkLabel>
      {action(t('chat.inputQueue.guide'),canGuide,()=>void run(()=>onGuide(entry)))}
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputQueue.delete')} accessibilityState={{disabled:!canCancel,busy:pending}} disabled={!canCancel} onPress={()=>void run(()=>onCancel(entry))} style={[styles.icon,{opacity:canCancel?1:0.5}]}><IconTrash width={16} height={16} color={colors['color-text-secondary']}/></Pressable>
      <View ref={anchor} collapsable={false}><Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputQueue.more')} accessibilityState={{expanded:menu!==null}} onPress={openMenu} style={styles.icon}><IconMoreHorizontal width={16} height={16} color={colors['color-text-secondary']}/></Pressable></View>
    </>}
    <Modal visible={menu!==null} transparent animationType="none" onRequestClose={()=>setMenu(null)} supportedOrientations={['portrait','landscape']}>
      <View style={styles.overlay} onAccessibilityEscape={()=>setMenu(null)}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={()=>setMenu(null)}/>
        {menu?<View accessibilityRole="menu" accessibilityLabel={t('chat.inputQueue.more')} accessibilityViewIsModal style={[styles.menu,menu,{backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-paper']}]}>
          {action(t('chat.inputQueue.edit'),canGuide,()=>{setMenu(null);setDraft(entry.text);setEditing(true);},<IconEdit width={16} height={16} color={colors['color-text-secondary']}/>,'menuitem')}
          {action(t('chat.inputQueue.sideChat'),canCancel,()=>void run(()=>onSideChat(entry)),<IconMessageCircle width={16} height={16} color={colors['color-text-secondary']}/>,'menuitem')}
          {action(t('chat.inputQueue.closeQueue'),canCancel,()=>void run(()=>onCancel(entry)),<IconTrash width={16} height={16} color={colors['color-text-secondary']}/>,'menuitem')}
        </View>:null}
      </View>
    </Modal>
  </View>;
}
const styles=StyleSheet.create({card:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',gap:8.8,minHeight:48,paddingVertical:5.6,paddingHorizontal:12.8,borderWidth:1,borderRadius:14.4},message:{flex:1,minWidth:80},control:{minHeight:44,flexDirection:'row',alignItems:'center',gap:5.6,paddingHorizontal:5.6,borderRadius:8},icon:{minWidth:44,minHeight:44,alignItems:'center',justifyContent:'center'},edit:{flex:1,minWidth:0,flexDirection:'row',alignItems:'center',gap:6.4},input:{flex:1,minWidth:0,minHeight:44,padding:6.4,borderWidth:1,borderRadius:7.2,fontFamily:'Excalifont'},overlay:{flex:1},menu:{position:'absolute',maxWidth:'95%',padding:5.6,borderWidth:1,borderRadius:13.6,shadowColor:'#000',shadowOpacity:0.15,shadowRadius:10,shadowOffset:{width:0,height:8}}});
