// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original activity read states/model, paged history and caller-owned navigation/deletion callbacks.
// [Output] Native activity drawer with recent Chat/today tasks, original display filters and one body scroller.
// [Pos] Native counterpart of ActivitySidebar; Dream workbench source stays excluded and tasks remain server-owned.
import {useEffect,useMemo,useRef,useState} from 'react';
import {ActivityIndicator,BackHandler,Modal,Pressable,StyleSheet,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {getDateLocale} from '../../i18n';
import {buildActivityRows,DEFAULT_ACTIVITY_FILTERS,type ActivityFilters,type ActivityRow} from './activitySidebarModel';
import {groupChatThreadsByDate} from './chatHistoryPresentation';
import ChatHistoryList from './ChatHistoryList.native';
import type {NativeChatHistory} from './ChatHistorySearch.native';
import type useNativeActivitySidebarData from './useNativeActivitySidebarData.native';
import {IconCheck,IconMoreHorizontal,IconSearch,IconX} from './Icons';
export default function ActivitySidebar({activity,history,activeThreadId,onSelectThread,onDeleteThread,onTask,onClose,filters,onFiltersChange}:{activity:ReturnType<typeof useNativeActivitySidebarData>;history:NativeChatHistory;activeThreadId?:string|null;onSelectThread:(id:string)=>void;onDeleteThread:(id:string)=>void;onTask:(row:ActivityRow)=>void;onClose:()=>void;filters:ActivityFilters;onFiltersChange:(filters:ActivityFilters)=>void}) {
  const {t,i18n}=useTranslation(),colors=useInkColors(),{width,height}=useWindowDimensions();
  const anchor=useRef<View>(null),[menu,setMenu]=useState<{right:number;top:number}|null>(null),[menuHeight,setMenuHeight]=useState(160);
  const rows=useMemo(()=>buildActivityRows({now:activity.now,chats:activity.chat.data,dreams:[],scheduled:activity.scheduled.data,stale:{chat:Boolean(activity.chat.error),scheduled:Boolean(activity.scheduled.error),dream:false},filters:{...filters,dream:false}}),[activity.now,activity.chat,activity.scheduled,filters]);
  const sources=(['scheduled','chat'] as const).filter(source=>filters[source]);
  useEffect(()=>setMenu(null),[width,height]);
  useEffect(()=>{const listener=BackHandler.addEventListener('hardwareBackPress',()=>{onClose();return true;});return()=>listener.remove();},[onClose]);
  const time=(at:number)=>Number.isFinite(at)?new Intl.DateTimeFormat(getDateLocale(i18n.language),{hour:'2-digit',minute:'2-digit'}).format(at):'';
  const icon=(label:string,onPress:()=>void,content:React.ReactNode)=><Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={styles.icon}>{content}</Pressable>;
  const color=colors['color-text-secondary'];
  function openMenu(){anchor.current?.measureInWindow((x,y,w,h)=>setMenu({right:Math.max(8,Math.min(width-x-w,width-Math.min(240,width-16)-8)),top:y+h+4}));}
  return <View accessibilityViewIsModal accessibilityLabel={t('chat.activity.title')} style={[styles.panel,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]} onAccessibilityEscape={onClose}>
    <View style={[styles.header,{borderColor:colors['color-border-paper']}]}><InkLabel accessibilityRole="header" style={[styles.title,{color:colors['color-text-primary']}]}>{t('chat.activity.title')}</InkLabel><View style={styles.actions}>
      {icon(t('chat.search.ariaLabel'),history.openSearch,<IconSearch width={17} height={17} color={color}/>)}
      {icon(t('chat.activity.refresh'),()=>{activity.refresh();void history.reload();},<InkLabel style={{color,fontSize:20}}>↻</InkLabel>)}
      {icon(t('chat.activity.close'),onClose,<IconX width={17} height={17} color={color}/>)}</View></View>
    <ChatHistoryList groups={groupChatThreadsByDate(history.threads,t)} activeThreadId={activeThreadId} deletingThreadId={history.deletingId} loading={history.loading} loadingMore={history.loadingMore} error={history.error} moreError={history.moreError} hasMore={history.hasMore} onSelectThread={onSelectThread} onDeleteThread={onDeleteThread} onReload={()=>void history.reload()} onLoadMore={()=>void history.loadMore()}
      header={<View style={styles.priority}>
        <View style={styles.sectionHeading}><InkLabel style={{color:colors['color-text-muted'],fontSize:13.12,fontWeight:'600'}}>{t('chat.activity.priority')}</InkLabel><View ref={anchor} collapsable={false}>{icon(t('chat.activity.display'),openMenu,<IconMoreHorizontal width={17} height={17} color={color}/>)}</View></View>
        {filters.priority?<>
          {rows.map(row=><View key={row.key} style={styles.row}><Pressable accessibilityRole="button" accessibilityLabel={row.title??t('chat.history.fallbackTitle')} accessibilityState={{selected:row.source==='chat'&&row.id===activeThreadId}} onPress={()=>row.source==='chat'?onSelectThread(row.id):onTask(row)} style={({pressed})=>[styles.main,{backgroundColor:pressed?colors['color-bg-hover']:row.source==='chat'&&row.id===activeThreadId?colors['color-bg-app']:'transparent',borderColor:row.source==='chat'&&row.id===activeThreadId?colors['color-border-paper']:'transparent'}]}>
            <InkLabel numberOfLines={1} style={{color:colors['color-text-primary'],fontSize:13.28}}>{row.title??t('chat.history.fallbackTitle')}</InkLabel>
            <InkLabel style={{color:colors['color-text-muted'],fontSize:11.2,lineHeight:16}}>{`${t(`chat.activity.source.${row.source}`)}${row.source==='scheduled'?` · ${t('chat.activity.today')}`:''}${row.state?` · ${row.stale?`${t('chat.activity.lastState')}：`:''}${t(row.state==='running'?'chat.activity.taskRunning':`chat.activity.state.${row.state}`)}`:''}${time(row.activityAt)?` · ${time(row.activityAt)}`:''}`}</InkLabel>
          </Pressable>{row.source==='chat'?<Pressable accessibilityRole="button" accessibilityLabel={`${t('chat.history.deleteThread')}: ${row.title??t('chat.history.fallbackTitle')}`} disabled={history.deletingId===row.id} onPress={()=>onDeleteThread(row.id)} style={styles.delete}><IconX width={13} height={13} color={color}/></Pressable>:null}</View>)}
          {sources.map(source=>{const state=activity[source];return state.error?<View key={source} style={styles.feedback}><InkLabel accessibilityRole="alert" style={{color:colors['color-state-error'],fontSize:12}}>{t(state.hasSuccess?'chat.activity.updateFailed':'chat.activity.loadFailed',{source:t(`chat.activity.source.${source}`)})}</InkLabel><Pressable accessibilityRole="button" onPress={()=>activity.retry(source)} style={styles.retry}><InkLabel style={{color}}>{t('chat.activity.retry')}</InkLabel></Pressable></View>:state.isLoading?<View key={source} style={styles.feedback}><ActivityIndicator accessibilityLabel={t('chat.activity.loading',{source:t(`chat.activity.source.${source}`)})} color={color}/></View>:null;})}
          {!sources.length?<InkLabel style={[styles.feedback,{color}]}>{t('chat.activity.chooseTypes')}</InkLabel>:null}
          {!rows.length&&sources.length>0&&sources.every(source=>activity[source].hasSuccess&&!activity[source].isLoading&&!activity[source].error)?<InkLabel style={[styles.feedback,{color}]}>{t('chat.activity.empty')}</InkLabel>:null}
        </>:null}
        {history.deleteError?<InkLabel accessibilityRole="alert" style={{color:colors['color-state-error']}}>{t('chat.activity.historyFailed')}</InkLabel>:null}
      </View>}/>
    <Modal visible={menu!==null} transparent animationType="none" onRequestClose={()=>setMenu(null)} supportedOrientations={['portrait','landscape']}><View style={styles.fill} onAccessibilityEscape={()=>setMenu(null)}><Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={()=>setMenu(null)}/>{menu?<View accessibilityRole="menu" accessibilityLabel={t('chat.activity.display')} accessibilityViewIsModal onLayout={event=>setMenuHeight(event.nativeEvent.layout.height)} style={[styles.menu,{width:Math.min(240,width-16),right:menu.right,top:Math.max(8,Math.min(menu.top,height-menuHeight-8)),backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-paper']}]}>{(['priority','scheduled','chat'] as const).map(key=><Pressable key={key} accessibilityRole="checkbox" accessibilityLabel={t(key==='priority'?'chat.activity.prioritySection':`chat.activity.source.${key}`)} accessibilityState={{checked:filters[key]}} onPress={()=>onFiltersChange({...filters,[key]:!filters[key],dream:false})} style={styles.filter}><InkLabel style={{color:colors['color-text-primary'],flex:1}}>{t(key==='priority'?'chat.activity.prioritySection':`chat.activity.source.${key}`)}</InkLabel>{filters[key]?<IconCheck width={16} height={16} color={color}/>:null}</Pressable>)}</View>:null}</View></Modal>
  </View>;
}
export const nativeActivityFilters=():ActivityFilters=>({...DEFAULT_ACTIVITY_FILTERS,dream:false});
const styles=StyleSheet.create({fill:{flex:1},panel:{flex:1,minHeight:0,borderLeftWidth:1},header:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:8,paddingVertical:12,paddingHorizontal:13.6,borderBottomWidth:1},title:{fontSize:15.2,fontWeight:'600',flexShrink:1},actions:{flexDirection:'row',gap:2.4},icon:{width:44,height:44,alignItems:'center',justifyContent:'center'},priority:{paddingHorizontal:8,paddingTop:4},sectionHeading:{flexDirection:'row',alignItems:'center',justifyContent:'space-between'},row:{position:'relative',marginBottom:2.4},main:{minHeight:44,paddingVertical:9.6,paddingLeft:8,paddingRight:44,gap:4,borderWidth:1,borderRadius:8.8},delete:{position:'absolute',right:0,top:0,bottom:0,width:44,alignItems:'center',justifyContent:'center'},feedback:{paddingVertical:8,paddingHorizontal:6.4,flexDirection:'row',alignItems:'center',gap:6.4},retry:{minHeight:44,justifyContent:'center'},menu:{position:'absolute',padding:5.6,borderWidth:1,borderRadius:12},filter:{minHeight:44,flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:10}});
