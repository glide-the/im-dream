// [Sync] 2026-11-13: keep resource management within Settings and restore the five navigation peers.
// [Sync] 2026-11-01: reuse the shared RN/RNW cards while retaining native header, scroll and theme ownership.
// [Sync] 2026-10-30: group the same five peers into illustrated journal navigation and preferences; show the actual local theme.
// [Input] Shared ordered More definition and caller-owned navigation/theme callbacks.
// [Output] One native More page with Writing/Timeline/Reflections/Theme/Settings peers.
// [Pos] Narrow navigation presentation; destination pages retain their existing business owners.
// [Sync] 2026-10-29: keep model fields and account actions inside Settings rather than the More item list.
// [Sync] 2026-10-29: display local theme persistence failure on the same menu without changing the active page.
import {Pressable,ScrollView,StyleSheet,View} from 'react-native';
import Svg,{Circle,Line,Path} from 'react-native-svg';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../../src/components/useInkColors.native';
import {getTheme} from '../../../utils/theme.native';
import {IconChevronRight,IconClock,IconEdit} from '../../chat/Icons.native';
import MoreNavigationContent, {type MoreNavigationItem} from './MoreNavigationContent';
import type {MoreNavigationDestination} from './moreNavigation';

function MoreIcon({id,color}:{id:MoreNavigationItem['id'];color:string}) {
  if(id==='writing')return <IconEdit width={26} height={26} color={color}/>;
  if(id==='timeline')return <IconClock width={26} height={26} color={color}/>;
  return <Svg width={26} height={26} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" accessible={false}>
    {id==='analysis'?<><Path d="M4 4v16h16"/><Path d="m7 14 4-4 4 3 5-7"/></>:id==='theme'?<><Circle cx={12} cy={12} r={9}/><Path d="M12 3a9 9 0 0 1 0 18Z" fill={color} stroke="none"/></>:<><Line x1={4} y1={7} x2={20} y2={7}/><Line x1={4} y1={17} x2={20} y2={17}/><Circle cx={9} cy={7} r={3}/><Circle cx={15} cy={17} r={3}/></>}
  </Svg>;
}

export default function MoreNavigationPage({onNavigate,onToggleTheme,onClose}:{onNavigate:(destination:MoreNavigationDestination)=>void;onToggleTheme:()=>void;onClose:()=>void}) {
  const {t}=useTranslation(),c=useInkColors(),mode=useNativeThemeMode();
  const resolved=getTheme();
  const appearance=t(`settings.workspace.theme.options.${mode}`)+(mode==='system'?` · ${t(`settings.workspace.theme.options.${resolved}`)}`:'');
  return <View style={[styles.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={styles.header}><InkLabel accessibilityRole="header" style={{fontSize:30,color:c['color-text-primary']}}>{t('nav.more')}</InkLabel>
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.close')} onPress={onClose} style={styles.close}><InkLabel style={{color:c['color-text-primary']}}>{t('chat.history.close')}</InkLabel></Pressable>
    </View>
    <ScrollView accessibilityLabel={t('nav.more')} contentContainerStyle={styles.list}>
      <MoreNavigationContent colors={c} Label={InkLabel} renderIcon={(id,color)=><MoreIcon id={id} color={color}/>} chevron={<IconChevronRight width={18} height={18} color={c['color-text-muted']}/>} appearance={appearance} nextAppearance={t(`settings.workspace.theme.options.${resolved==='dark'?'light':'dark'}`)} onNavigate={onNavigate} onToggleTheme={onToggleTheme}/>
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({
  fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:12,paddingHorizontal:20,paddingTop:12,paddingBottom:8},
  close:{minHeight:44,minWidth:44,justifyContent:'center',padding:8},list:{paddingHorizontal:20,paddingBottom:28},
});
