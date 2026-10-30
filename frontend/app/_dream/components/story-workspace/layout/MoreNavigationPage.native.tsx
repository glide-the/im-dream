// [Sync] 2026-10-30: group the same five peers into illustrated journal navigation and preferences; show the actual local theme.
// [Input] Shared five-item More definition and caller-owned navigation/theme callbacks.
// [Output] One native More page with Writing/Timeline/Reflections/Theme/Settings peers.
// [Pos] Narrow navigation presentation; destination pages retain their existing business owners.
// [Sync] 2026-10-29: keep model fields and account actions inside Settings rather than the More item list.
// [Sync] 2026-10-29: display local theme persistence failure on the same menu without changing the active page.
import {useState} from 'react';
import {Pressable,ScrollView,StyleSheet,View} from 'react-native';
import Svg,{Circle,Line,Path} from 'react-native-svg';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../../src/components/useInkColors.native';
import {getTheme} from '../../../utils/theme.native';
import {IconChevronRight,IconClock,IconEdit} from '../../chat/Icons.native';
import {MORE_NAVIGATION_ITEMS,type MoreNavigationDestination} from './moreNavigation';

function MoreIcon({id,color}:{id:(typeof MORE_NAVIGATION_ITEMS)[number]['id'];color:string}) {
  if(id==='writing')return <IconEdit width={26} height={26} color={color}/>;
  if(id==='timeline')return <IconClock width={26} height={26} color={color}/>;
  return <Svg width={26} height={26} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" accessible={false}>
    {id==='analysis'?<><Path d="M4 4v16h16"/><Path d="m7 14 4-4 4 3 5-7"/></>:id==='theme'?<><Circle cx={12} cy={12} r={9}/><Path d="M12 3a9 9 0 0 1 0 18Z" fill={color} stroke="none"/></>:<><Line x1={4} y1={7} x2={20} y2={7}/><Line x1={4} y1={17} x2={20} y2={17}/><Circle cx={9} cy={7} r={3}/><Circle cx={15} cy={17} r={3}/></>}
  </Svg>;
}

export default function MoreNavigationPage({onNavigate,onToggleTheme,onClose}:{onNavigate:(destination:MoreNavigationDestination)=>void;onToggleTheme:()=>void;onClose:()=>void}) {
  const {t}=useTranslation(),c=useInkColors(),mode=useNativeThemeMode();
  const [themeError,setThemeError]=useState(false);
  const resolved=getTheme();
  const appearance=t(`settings.workspace.theme.options.${mode}`)+(mode==='system'?` · ${t(`settings.workspace.theme.options.${resolved}`)}`:'');
  function changeTheme(){setThemeError(false);try{onToggleTheme();}catch{setThemeError(true);}}
  function entry(item:(typeof MORE_NAVIGATION_ITEMS)[number],layout:'writing'|'tile'|'preference') {
    return <Pressable key={item.id} accessibilityRole="button" accessibilityLabel={t(item.labelKey)} accessibilityHint={item.id==='theme'?t('morePage.themeAction',{appearance,next:t(`settings.workspace.theme.options.${resolved==='dark'?'light':'dark'}`)}):t(`morePage.guidance.${item.id}`)} onPress={()=>item.id==='theme'?changeTheme():onNavigate(item.id)} style={({pressed})=>[styles.entry,layout==='tile'?styles.tile:styles.row,{backgroundColor:pressed?c['color-bg-hover']:c['color-bg-paper'],borderColor:c['color-border-paper']}]}>
      <View style={[styles.icon,{backgroundColor:c['color-bg-app']}]}><MoreIcon id={item.id} color={c['color-text-primary']}/></View>
      <View style={styles.copy}><InkLabel style={[styles.label,{color:c['color-text-primary']}]}>{t(item.labelKey)}</InkLabel>
        <InkLabel style={[styles.description,{color:c['color-text-secondary']}]}>{item.id==='theme'?t('morePage.currentTheme',{appearance}):t(`morePage.guidance.${item.id}`)}</InkLabel>
      </View>
      {layout!=='tile'?<IconChevronRight width={18} height={18} color={c['color-text-muted']}/>:null}
    </Pressable>;
  }
  return <View style={[styles.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={styles.header}><InkLabel accessibilityRole="header" style={{fontSize:30,color:c['color-text-primary']}}>{t('nav.more')}</InkLabel>
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.close')} onPress={onClose} style={styles.close}><InkLabel style={{color:c['color-text-primary']}}>{t('chat.history.close')}</InkLabel></Pressable>
    </View>
    <ScrollView accessibilityLabel={t('nav.more')} contentContainerStyle={styles.list}>
      <InkLabel style={[styles.intro,{color:c['color-text-secondary']}]}>{t('morePage.intro')}</InkLabel>
      <View style={styles.section}>
        <InkLabel accessibilityRole="header" style={[styles.sectionTitle,{color:c['color-text-secondary']}]}>{t('morePage.journal')}</InkLabel>
        {MORE_NAVIGATION_ITEMS.filter(item=>item.id==='writing').map(item=>entry(item,'writing'))}
        <View style={styles.tiles}>{MORE_NAVIGATION_ITEMS.filter(item=>item.id==='timeline'||item.id==='analysis').map(item=>entry(item,'tile'))}</View>
      </View>
      <View style={styles.section}>
        <InkLabel accessibilityRole="header" style={[styles.sectionTitle,{color:c['color-text-secondary']}]}>{t('morePage.preferences')}</InkLabel>
        {themeError?<InkLabel accessibilityRole="alert" style={[styles.description,{color:c['color-state-error']}]}>{t('settings.workspace.preferences.localSaveFailed')}</InkLabel>:null}
        {MORE_NAVIGATION_ITEMS.filter(item=>item.id==='theme'||item.id==='settings').map(item=>entry(item,'preference'))}
      </View>
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({
  fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:12,paddingHorizontal:20,paddingTop:12,paddingBottom:8},
  close:{minHeight:44,minWidth:44,justifyContent:'center',padding:8},list:{paddingHorizontal:20,paddingBottom:28,gap:26},intro:{fontSize:14,lineHeight:22},
  section:{gap:12},sectionTitle:{fontSize:14},entry:{minWidth:0,borderWidth:StyleSheet.hairlineWidth,borderRadius:18,padding:16,gap:12},
  row:{flexDirection:'row',alignItems:'center',minHeight:92},tiles:{flexDirection:'row',gap:12},tile:{flex:1,alignItems:'flex-start',minHeight:152},
  icon:{width:44,height:44,borderRadius:13,alignItems:'center',justifyContent:'center'},copy:{flex:1,minWidth:0,gap:6},label:{fontSize:19},description:{fontSize:13,lineHeight:20,flexShrink:1},
});
