// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original scheduled-task identity/snapshot, authenticated read APIs and exact Thread navigation.
// [Output] Native read-only task information, source/execution conversations, cadence and retry feedback.
// [Pos] Native counterpart of ScheduledTaskDetailSidebar; no task mutation or schedule calculation.
import {useEffect,useMemo,useRef,useState} from 'react';
import {ActivityIndicator,AppState,BackHandler,Pressable,ScrollView,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import {getScheduledHistory,getScheduledTask,type ScheduledTask,type ScheduledTrigger} from '../../api/scheduledTaskApi';
import {clientFetch} from '../../../../src/platform/transport.native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {scheduledTaskConversations,scheduledTaskRuleText} from './scheduledTaskDetailPresentation';
import type {ScheduledTaskMarkerSnapshot} from './scheduledTaskMarkerModel';
import {IconClock,IconX} from './Icons';
export default function ScheduledTaskDetailSidebar({taskId,snapshot,onClose,onOpenThread,onSessionExpired,transport=clientFetch}:{taskId:string;snapshot?:ScheduledTaskMarkerSnapshot|null;onClose:()=>void;onOpenThread:(id:string)=>void;onSessionExpired?:()=>void;transport?:typeof fetch}) {
  const {t,i18n}=useTranslation(),colors=useInkColors();
  const [task,setTask]=useState<ScheduledTask|null>(null),[triggers,setTriggers]=useState<ScheduledTrigger[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(false),[retry,setRetry]=useState(0),[foreground,setForeground]=useState(AppState.currentState==='active');
  const expire=useRef(onSessionExpired);expire.current=onSessionExpired;
  useEffect(()=>{const listener=AppState.addEventListener('change',state=>setForeground(state==='active'));return()=>listener.remove();},[]);
  useEffect(()=>{const listener=BackHandler.addEventListener('hardwareBackPress',()=>{onClose();return true;});return()=>listener.remove();},[onClose]);
  useEffect(()=>{
    if(!foreground)return;let active=true;const controller=new AbortController();setLoading(true);setError(false);
    void Promise.all([getScheduledTask(taskId,{signal:controller.signal,transport}),getScheduledHistory(taskId,20,undefined,{signal:controller.signal,transport})]).then(([definition,history])=>{
      if(!active||controller.signal.aborted)return;
      if(!definition.task||definition.task.id!==taskId||!Array.isArray(history.triggers)||history.triggers.some(trigger=>trigger.task_id!==taskId))throw new Error('SCHEDULE_DETAIL_INVALID');
      setTask(definition.task);setTriggers(history.triggers);
    }).catch(reason=>{if(active&&!controller.signal.aborted){setError(true);if(reason?.status===401)expire.current?.();}}).finally(()=>{if(active&&!controller.signal.aborted)setLoading(false);});
    return()=>{active=false;controller.abort();};
  },[taskId,retry,foreground,transport]);
  const currentTask=task?.id===taskId?task:null;
  const conversations=useMemo(()=>scheduledTaskConversations(currentTask?.source_thread_id,currentTask?triggers:[]),[currentTask,triggers]);
  const title=currentTask?.title??snapshot?.title??t('chat.scheduledTask.detailTitle'),ruleText=scheduledTaskRuleText(currentTask?.rule??snapshot?.rule,t),status=currentTask?.status??snapshot?.status;
  const formatDate=(value:string|null|undefined)=>value?new Date(value).toLocaleString(i18n.language):'—';
  const text={color:colors['color-text-primary']},muted={color:colors['color-text-secondary']};
  const field=(label:string,value:string)=><View key={label} style={styles.field}><InkLabel style={[styles.label,muted]}>{label}</InkLabel><InkLabel style={[styles.value,text]}>{value}</InkLabel></View>;
  const conversation=(id:string,label:string,detail:string)=><Pressable key={id} accessibilityRole="button" accessibilityLabel={label} onPress={()=>onOpenThread(id)} style={[styles.conversation,{borderColor:colors['color-border-paper']}]}><View style={styles.fill}><InkLabel style={text}>{label}</InkLabel><InkLabel style={[styles.label,muted]}>{detail}</InkLabel></View><InkLabel style={muted}>›</InkLabel></Pressable>;
  return <View accessibilityViewIsModal accessibilityLabel={t('chat.scheduledTask.detailTitle')} style={[styles.panel,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]} onAccessibilityEscape={onClose}>
    <View style={[styles.header,{borderColor:colors['color-border-paper']}]}><IconClock width={18} height={18} color={colors['color-text-secondary']}/><View style={styles.fill}><InkLabel style={[styles.title,text]}>{title}</InkLabel><InkLabel style={[styles.label,muted]}>{ruleText}</InkLabel></View><Pressable accessibilityRole="button" accessibilityLabel={t('chat.scheduledTask.close')} onPress={onClose} style={styles.icon}><IconX width={17} height={17} color={colors['color-text-secondary']}/></Pressable></View>
    <ScrollView style={styles.fill} contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
      {loading?<ActivityIndicator accessibilityLabel={t('chat.scheduledTask.loading')} color={colors['color-text-muted']}/>:null}
      {error?<View style={styles.section}><InkLabel accessibilityRole="alert" style={{color:colors['color-state-error']}}>{t('chat.scheduledTask.unavailable')}</InkLabel><Pressable accessibilityRole="button" onPress={()=>setRetry(value=>value+1)} style={styles.icon}><InkLabel style={text}>{t('calendar.scheduledRetry')}</InkLabel></Pressable></View>:null}
      {!loading&&!error&&currentTask?<>
        <View style={styles.section}><InkLabel accessibilityRole="header" style={[styles.title,text]}>{t('chat.scheduledTask.taskInfo')}</InkLabel>
          {field(t('calendar.scheduledStatusLabel'),status?t(`calendar.scheduledStatus.${status}`,{defaultValue:status}):'—')}
          {field(t('chat.scheduledTask.runMode'),t(currentTask.run_thread_mode==='new_thread_each_run'?'chat.scheduledTask.newConversation':'chat.scheduledTask.reuseSource'))}
          {field(t('chat.scheduledTask.model'),currentTask.model_alias??t('chat.scheduledTask.legacyModel'))}
          {currentTask.prompt?<InkLabel selectable style={[styles.prompt,text]}>{currentTask.prompt}</InkLabel>:null}
        </View>
        <View style={styles.section}><InkLabel accessibilityRole="header" style={[styles.title,text]}>{t('chat.scheduledTask.conversations')}</InkLabel>
          {currentTask.source_thread_id?conversation(currentTask.source_thread_id,t('chat.scheduledTask.sourceConversation'),title):null}
          {conversations.map(trigger=>conversation(trigger.target_thread_id!,t('chat.scheduledTask.runConversation'),`${formatDate(trigger.scheduled_at??trigger.created_at)} · ${t(`calendar.scheduledStatus.${trigger.status}`,{defaultValue:trigger.status})}`))}
          {!currentTask.source_thread_id&&!conversations.length?<InkLabel style={muted}>{t('chat.scheduledTask.noConversations')}</InkLabel>:null}
        </View>
        <View style={styles.section}><InkLabel accessibilityRole="header" style={[styles.title,text]}>{t('chat.scheduledTask.taskCycle')}</InkLabel>{field(t('calendar.scheduledRule'),ruleText)}{field(t('calendar.scheduledNext'),formatDate(currentTask.next_run_at??snapshot?.nextRunAt))}</View>
      </>:null}
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({panel:{flex:1,minHeight:0,borderLeftWidth:StyleSheet.hairlineWidth},fill:{flex:1,minWidth:0,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:10,padding:12,borderBottomWidth:1},icon:{minWidth:44,minHeight:44,alignItems:'center',justifyContent:'center'},body:{padding:16,gap:20},section:{gap:12},title:{fontSize:15.2,fontWeight:'600'},label:{fontSize:12.16,lineHeight:18},value:{fontSize:14,flexShrink:1},field:{gap:4},prompt:{fontSize:14,lineHeight:21},conversation:{minHeight:52,flexDirection:'row',alignItems:'center',gap:12,padding:12,borderWidth:1,borderRadius:12}});
