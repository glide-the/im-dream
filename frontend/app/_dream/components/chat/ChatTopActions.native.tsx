// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-29: shrink only context slots within the narrow toolbar; original actions keep their touch targets.
// [Input] Original ChatView New/activity/workspace/share actions and caller-owned badge/Plan nodes.
// [Output] Original top-right actions and More disclosure with native touch/back/dismiss behavior.
// [Pos] Native presentation counterpart of ChatView's floating toolbar; no Thread or export ownership.
import {useRef,useState,type ReactNode} from 'react';
import {Modal,Pressable,StyleSheet,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {IconBell,IconClock,IconFolder,IconMoreHorizontal,IconPlus,IconShare} from './Icons';

export interface ChatTopActionsProps {
  creating: boolean;
  activityOpen: boolean;
  workspaceEnabled: boolean;
  workspaceOpen: boolean;
  contextBadge?: ReactNode;
  pluginReceipt?: ReactNode;
  planAction?: ReactNode;
  onNewChat: () => void;
  onToggleActivity: () => void;
  onToggleWorkspace: () => void;
  onShare: () => void;
}
export default function ChatTopActions({creating,activityOpen,workspaceEnabled,workspaceOpen,contextBadge,pluginReceipt,planAction,onNewChat,onToggleActivity,onToggleWorkspace,onShare}: ChatTopActionsProps) {
  const {t} = useTranslation();
  const colors = useInkColors();
  const {width,height} = useWindowDimensions();
  const anchor = useRef<View>(null);
  const [menu,setMenu] = useState<{right:number;top:number}|null>(null);
  function openMenu() {
    anchor.current?.measureInWindow((x,y,w,h) => setMenu({right:Math.max(12,width-x-w),top:Math.min(y+h+6.4,height-160)}));
  }
  function select(action: () => void) {setMenu(null);action();}
  const menuRow = (label: string, Icon: typeof IconClock, selected: boolean, action: () => void) => <Pressable accessibilityRole="button" accessibilityLabel={label}
    accessibilityState={{selected}} onPress={() => select(action)} style={({pressed}) => [styles.menuRow,{backgroundColor:selected || pressed ? colors['color-bg-surface'] : 'transparent'}]}>
    <Icon width={15.2} height={15.2} color={colors['color-text-secondary']} />
    <InkLabel style={{fontSize:13.28,color:colors['color-text-primary']}}>{label}</InkLabel>
  </Pressable>;
  return <View style={styles.toolbar}>
    {contextBadge}{pluginReceipt}
    <Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.newChat')} accessibilityState={{disabled:creating,busy:creating}} disabled={creating} onPress={onNewChat}
      style={({pressed}) => [styles.new,{opacity:creating ? 0.6 : 1,backgroundColor:pressed ? colors['color-bg-surface'] : 'transparent'}]}>
      <IconPlus width={15.2} height={15.2} color={creating ? colors['color-text-muted'] : colors['color-text-secondary']} />
      <InkLabel style={{fontSize:13.12,color:creating ? colors['color-text-muted'] : colors['color-text-secondary']}}>{t(creating ? 'chat.history.creating' : 'chat.history.newShort')}</InkLabel>
    </Pressable>
    <Pressable accessibilityRole="button" accessibilityLabel={t('chat.activity.entry')} accessibilityState={{expanded:activityOpen}} onPress={onToggleActivity}
      style={[styles.iconButton,{backgroundColor:activityOpen ? colors['color-bg-surface'] : 'transparent'}]}><IconBell width={17.6} height={17.6} color={colors[activityOpen ? 'color-text-primary' : 'color-text-secondary']} /></Pressable>
    {planAction}
    <View ref={anchor} collapsable={false}><Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.more')} accessibilityState={{expanded:menu !== null}} onPress={openMenu}
      style={[styles.iconButton,{backgroundColor:menu ? colors['color-bg-surface'] : 'transparent'}]}><IconMoreHorizontal width={17.6} height={17.6} color={colors[menu ? 'color-text-primary' : 'color-text-secondary']} /></Pressable></View>
    <Modal visible={menu !== null} transparent animationType="none" onRequestClose={() => setMenu(null)} supportedOrientations={['portrait','landscape']}>
      <View style={styles.overlay} onAccessibilityEscape={() => setMenu(null)}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={() => setMenu(null)} />
        {menu ? <View accessibilityViewIsModal style={[styles.menu,{top:menu.top,right:menu.right,backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-paper']}]}>
          {menuRow(t('chat.history.title'),IconClock,activityOpen,onToggleActivity)}
          {workspaceEnabled ? menuRow(t('chat.history.workspace'),IconFolder,workspaceOpen,onToggleWorkspace) : null}
          <View style={[styles.separator,{backgroundColor:colors['color-border-paper']}]} />
          {menuRow(t('chat.history.share'),IconShare,false,onShare)}
        </View> : null}
      </View>
    </Modal>
  </View>;
}
const styles = StyleSheet.create({
  toolbar:{flexShrink:1,minWidth:0,flexDirection:'row',alignItems:'center',justifyContent:'flex-end',gap:2.4,minHeight:44},
  new:{minHeight:44,flexDirection:'row',alignItems:'center',gap:5.6,paddingHorizontal:8.8,borderRadius:8.8},
  iconButton:{width:44,height:44,borderRadius:8.8,alignItems:'center',justifyContent:'center'},
  overlay:{flex:1},menu:{position:'absolute',minWidth:160,maxWidth:'95%',padding:5.6,borderWidth:1,borderRadius:13.6,gap:0.8,shadowColor:'#000',shadowOpacity:0.18,shadowRadius:12,shadowOffset:{width:0,height:8}},
  menuRow:{minHeight:44,flexDirection:'row',alignItems:'center',gap:9.6,paddingHorizontal:10.4,borderRadius:8.8},
  separator:{height:1,marginVertical:3.2,marginHorizontal:6.4},
});
