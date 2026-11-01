// [Input] Original current-Thread task snapshots, exact task-detail GETs and existing Chat/detail navigation callbacks.
// [Output] Native conditional task-activity control with separate scheduled/task/subagent/plan/todo cards and readonly detail.
// [Pos] Native counterpart of PlanPanel; execution, permissions and persistence remain with original server owners.
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,Keyboard,Modal,Pressable,ScrollView,StyleSheet,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {fetchTaskSessionDetail,type TaskSessionStatus} from './taskSessionLinks';
import {TASK_TODO_VISIBLE_COUNT,formatTaskRelativeTime} from './taskActivityPresentation';
import {formatChatDuration} from './chatDuration';
import {scheduledTaskRuleText} from './scheduledTaskDetailPresentation';
import type {ScheduledTaskMarkerSnapshot} from './scheduledTaskMarkerModel';
import type {NativeTaskActivity} from './useNativeTaskActivity.native';
import SubagentMessageTimeline from './SubagentMessageTimeline.native';
import ChatMarkdown,{type NativeChatMarkdownProps} from './ChatMarkdown.native';
import {IconList,IconX,IconChevronRight} from './Icons';
function Card({title,children,collapsible=false}:{title:string;children:ReactNode;collapsible?:boolean}){
 const colors=useInkColors(),[expanded,setExpanded]=useState(true);
 const heading=<InkLabel accessibilityRole="header" style={{fontWeight:'700',color:colors['color-text-primary'],flex:1}}>{title}</InkLabel>;
 return <View style={[s.card,{backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-paper']}]}>{collapsible?<Pressable accessibilityRole="button" accessibilityLabel={title} accessibilityState={{expanded}} onPress={()=>setExpanded(value=>!value)} style={s.row}>{heading}<IconChevronRight width={16} height={16} color={colors['color-text-muted']} style={{transform:[{rotate:expanded?'90deg':'0deg'}]}}/></Pressable>:heading}{!collapsible||expanded?children:null}</View>;
}
export default function PlanButton({threadId,origin,activity,active,onNavigateThread,onOpenScheduledTask,onSessionExpired,...markdown}:{threadId:string;origin?:string;activity:NativeTaskActivity;active:boolean;onNavigateThread:(id:string)=>void;onOpenScheduledTask:(task:ScheduledTaskMarkerSnapshot)=>void;onSessionExpired?:()=>void}&Pick<NativeChatMarkdownProps,'workspaceAvailability'|'workspaceResources'|'onOpenLink'|'onOpenWorkspace'>){
 const {t,i18n}=useTranslation(),c=useInkColors(),{width,height}=useWindowDimensions(),anchor=useRef<View>(null);
 const [open,setOpen]=useState(false),[top,setTop]=useState(60),[taskId,setTaskId]=useState<string|null>(null),[todosExpanded,setTodosExpanded]=useState(false),[statuses,setStatuses]=useState<Record<string,TaskSessionStatus>>({});
 const {data,failed}=activity,links=data.links?.created??[],source=data.scheduled?.source;
 const scheduled=[...new Map([...(source?[source.task]:[]),...(data.scheduled?.created??[])].map(task=>[task.id,task])).values()];
 const agents=data.subagents?.tasks??[],hasPlan=Boolean(data.plan?.exists||data.plan?.planMode&&data.plan.planMode!=='none'),hasTodos=Boolean(data.todos?.exists);
 const available=scheduled.length>0||links.length>0||agents.length>0||hasPlan||hasTodos||failed.size>0;
 const selected=agents.find(task=>task.taskId===taskId),callback=useRef(onSessionExpired);callback.current=onSessionExpired;
 useEffect(()=>{if(!active)setOpen(false);},[active]);
 useEffect(()=>{setOpen(false);setTaskId(null);setTodosExpanded(false);setStatuses({});},[threadId]);
 useEffect(()=>{
  if(!open||!active||!activity.foreground)return;const controller=new AbortController();let current=true;
  const request:typeof fetch=async(input,init)=>{const response=await activity.transport(input,init);if(current&&!controller.signal.aborted&&response.status===401)callback.current?.();return response;};
  void Promise.all(links.map(async(link):Promise<[string,TaskSessionStatus]>=>{
   if(link.launch_status==='failed')return [link.task_id,'failed'];if(link.launch_status==='pending')return [link.task_id,'pending'];
   try{const detail=await fetchTaskSessionDetail(threadId,link.task_id,{transport:request,signal:controller.signal});return [link.task_id,detail.task_id===link.task_id&&detail.thread_id===link.thread_id?detail.status:'state_unknown'];}catch{return [link.task_id,'state_unknown'];}
  })).then(rows=>{if(current&&!controller.signal.aborted)setStatuses(Object.fromEntries(rows));});
  return()=>{current=false;controller.abort();};
 },[open,active,activity.foreground,data.links,threadId,activity.transport]);
 if(!available&&!open)return null;
 const muted={color:c['color-text-muted']},text={color:c['color-text-primary']};
 const close=()=>{setOpen(false);setTaskId(null);};
 const show=()=>{Keyboard.dismiss();anchor.current?.measureInWindow((_x,y,_w,h)=>setTop(Math.max(8,Math.min(y+h+4,height-160))));setOpen(true);};
 const retry=(key:keyof typeof data)=>failed.has(key)?<View><InkLabel accessibilityRole="alert" style={muted}>{t(key==='scheduled'?'chat.taskActivity.scheduledUnavailable':key==='subagents'?'chat.subagents.unavailable':'chat.taskActivity.unavailable')}</InkLabel><Pressable accessibilityRole="button" onPress={activity.refresh} style={s.action}><InkLabel style={text}>{t('chat.taskActivity.retry')}</InkLabel></Pressable></View>:null;
 const stamp=(value:string|null|undefined)=>value&&Number.isFinite(Date.parse(value))?new Intl.DateTimeFormat(i18n.language,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value)):'';
 const panelTop=Math.max(8,Math.min(top,height-160));
 const statusColor=(status:string)=>c[status==='running'?'color-action-link':status==='completed'?'color-state-success':status==='failed'?'color-state-error':'color-text-muted'];
 return <View ref={anchor} collapsable={false}>
  <Pressable accessibilityRole="button" accessibilityLabel={t('chat.taskActivity.activityTitle')} accessibilityState={{expanded:open}} onPress={show} style={s.icon}><IconList width={18} height={18} color={c['color-text-secondary']}/></Pressable>
  <Modal visible={open&&active&&activity.foreground} transparent animationType="none" onRequestClose={()=>taskId?setTaskId(null):close()} supportedOrientations={['portrait','landscape']}>
   <View style={s.fill} onAccessibilityEscape={()=>taskId?setTaskId(null):close()}><Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={close}/>
    <View testID="native-task-activity-panel" accessibilityViewIsModal accessibilityLabel={t('chat.taskActivity.activityTitle')} style={[s.panel,{top:panelTop,right:12,width:Math.min(416,width-24),maxHeight:Math.max(120,height-panelTop-24),backgroundColor:c['color-bg-app'],borderColor:c['color-border-paper']}]}>
     <View style={s.header}>{taskId?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.subagents.backToTasks')} onPress={()=>setTaskId(null)} style={s.icon}><InkLabel style={text}>‹</InkLabel></Pressable>:null}
      <InkLabel accessibilityRole="header" style={[text,{flex:1,fontWeight:'700'}]}>{t(taskId?'chat.subagents.detailTitle':'chat.taskActivity.activityTitle')}</InkLabel>
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.taskActivity.refresh')} onPress={activity.refresh} style={s.icon}>{activity.loading?<ActivityIndicator color={c['color-text-muted']}/>:<InkLabel style={text}>↻</InkLabel>}</Pressable>
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.close')} onPress={close} style={s.icon}><IconX width={18} height={18} color={c['color-text-primary']}/></Pressable>
     </View>
     <ScrollView testID="native-task-activity-scroll" style={{flexShrink:1,minHeight:0}} contentContainerStyle={s.cards} keyboardShouldPersistTaps="handled">
      {taskId?<>{selected?<Card title={selected.description}><InkLabel style={{color:statusColor(selected.status)}}>{`${t(`chat.subagents.status.${selected.status}`)} · ${selected.agentType} · ${formatChatDuration(selected.durationMs,i18n.language)}`}</InkLabel>{selected.error?<InkLabel accessibilityRole="alert" selectable style={{color:c['color-state-error']}}>{selected.error}</InkLabel>:null}<SubagentMessageTimeline messages={selected.messages} taskStatus={selected.status} legacy={selected.messages.some(message=>message.legacy)} truncated={selected.messagesTruncated} origin={origin} workspaceSessionId={threadId} {...markdown} onOpenWorkspace={markdown.onOpenWorkspace?uri=>{close();markdown.onOpenWorkspace?.(uri);}:undefined}/></Card>:<InkLabel style={muted}>{t('chat.subagents.empty')}</InkLabel>}{retry('subagents')}</>:<>
       {scheduled.length>0||failed.has('scheduled')?<Card collapsible title={t('chat.taskActivity.scheduledTasks')}>{scheduled.map(task=><Pressable key={task.id} accessibilityRole="button" accessibilityLabel={t('chat.scheduledTask.openAria',{title:task.title})} style={s.row} onPress={()=>{close();onOpenScheduledTask({id:task.id,title:task.title,rule:task.rule,nextRunAt:task.next_run_at,status:task.status,revision:task.revision});}}>
        <View style={{flex:1,minWidth:0}}><InkLabel numberOfLines={2} style={text}>{task.title}</InkLabel><InkLabel style={muted}>{`${scheduledTaskRuleText(task.rule,t)} · ${t(`calendar.scheduledStatus.${task.status}`,{defaultValue:task.status})}`}</InkLabel>{source?.task.id===task.id?<InkLabel style={muted}>{t('chat.taskActivity.scheduledExecution',{status:t(`calendar.scheduledStatus.${source.trigger.status}`,{defaultValue:source.trigger.status})})}</InkLabel>:null}</View><IconChevronRight width={16} height={16} color={c['color-text-secondary']}/>
       </Pressable>)}{retry('scheduled')}</Card>:null}
       {links.length>0||failed.has('links')?<Card collapsible title={t('chat.taskActivity.createdTasks')}>{links.map(link=>{const status=statuses[link.task_id]??(link.launch_status==='failed'?'failed':link.launch_status==='pending'?'pending':'state_unknown');return <Pressable key={link.task_id} accessibilityRole="button" accessibilityLabel={`${link.title} · ${t('chat.taskActivity.status.'+status)}`} style={s.row} onPress={()=>{close();onNavigateThread(link.thread_id);}}><InkLabel style={{color:statusColor(status)}}>{status==='completed'?'●':status==='running'?'◉':'○'}</InkLabel><View style={{flex:1,minWidth:0}}><InkLabel numberOfLines={2} style={text}>{link.title}</InkLabel><InkLabel style={muted}>{stamp(link.created_at)}</InkLabel></View><InkLabel style={{color:statusColor(status),fontSize:12}}>{t('chat.taskActivity.status.'+status)}</InkLabel><IconChevronRight width={16} height={16} color={c['color-text-secondary']}/></Pressable>})}{retry('links')}</Card>:null}
       {agents.length>0||failed.has('subagents')?<Card title={t('chat.subagents.title')}>{(['running','completed','ended'] as const).map(group=>{const rows=agents.filter(task=>group==='ended'?['failed','cancelled'].includes(task.status):task.status===group);return rows.length?<View key={group} style={{gap:6}}><InkLabel style={muted}>{t(group==='running'?'chat.subagents.activeTitle':group==='completed'?'chat.subagents.completedTitle':'chat.subagents.endedTitle',{count:rows.length})}</InkLabel>{rows.map(task=><Pressable key={task.taskId} accessibilityRole="button" accessibilityLabel={t('chat.subagents.openTask',{task:task.description})} onPress={()=>setTaskId(task.taskId)} style={s.row}><View style={{flex:1,minWidth:0}}><InkLabel numberOfLines={2} style={text}>{task.description}</InkLabel>{task.summary?<InkLabel numberOfLines={2} style={muted}>{task.summary}</InkLabel>:null}<InkLabel style={{color:statusColor(task.status),fontSize:12}}>{`${t(`chat.subagents.status.${task.status}`)} · ${formatChatDuration(task.durationMs,i18n.language)}`}</InkLabel></View><IconChevronRight width={16} height={16} color={c['color-text-secondary']}/></Pressable>)}</View>:null;})}{retry('subagents')}</Card>:null}
       {hasPlan||failed.has('plan')?<Card title={t('chat.planPanel.planTitle')}>{data.plan?<><InkLabel style={muted}>{(data.plan.planMode!=='none'?t('chat.planPanel.'+data.plan.planMode):'')+(data.plan.updatedAt?' · '+formatTaskRelativeTime(data.plan.updatedAt,t,i18n.language):'')}</InkLabel>{data.plan.fileName?<InkLabel style={muted}>{data.plan.fileName}</InkLabel>:null}{data.plan.content?<ChatMarkdown text={data.plan.content} origin={origin} workspaceSessionId={threadId} {...markdown} onOpenWorkspace={markdown.onOpenWorkspace?uri=>{close();markdown.onOpenWorkspace?.(uri);}:undefined}/>:<InkLabel style={muted}>{t(data.plan.planMode==='planning'?'chat.planPanel.waitingContent':'chat.planPanel.noContent')}</InkLabel>}{data.plan.truncated?<Pressable accessibilityRole="button" onPress={activity.refresh} style={s.action}><InkLabel style={text}>{t(activity.loading?'chat.planPanel.loading':'chat.planPanel.loadFull')}</InkLabel></Pressable>:null}</>:null}{retry('plan')}</Card>:null}
       {hasTodos||failed.has('todos')?<Card title={t('chat.planPanel.todosTitle')}>{data.todos?.updatedAt?<InkLabel style={muted}>{formatTaskRelativeTime(data.todos.updatedAt,t,i18n.language)}</InkLabel>:null}{(todosExpanded?data.todos?.todos:data.todos?.todos.slice(0,TASK_TODO_VISIBLE_COUNT))?.map((todo,index)=><View key={todo.id||index} style={s.row}><InkLabel style={{color:statusColor(todo.status==='in_progress'?'running':todo.status)}}>{todo.status==='completed'?'●':todo.status==='in_progress'?'◉':'○'}</InkLabel><View style={{flex:1,minWidth:0}}><InkLabel selectable style={[text,todo.status==='completed'?{textDecorationLine:'line-through'}:undefined]}>{todo.status==='in_progress'&&todo.active_form?todo.active_form:todo.content}</InkLabel>{todo.owner?<InkLabel style={muted}>{todo.owner}</InkLabel>:null}{todo.blocked_by?.length?<InkLabel style={muted}>{`⛔ ${todo.blocked_by.join(', ')}`}</InkLabel>:null}</View></View>)}{data.todos&&data.todos.todos.length>TASK_TODO_VISIBLE_COUNT?<Pressable accessibilityRole="button" accessibilityState={{expanded:todosExpanded}} onPress={()=>setTodosExpanded(value=>!value)} style={s.action}><InkLabel style={text}>{t(todosExpanded?'chat.planPanel.collapse':'chat.planPanel.expandMore',{count:data.todos.todos.length-TASK_TODO_VISIBLE_COUNT})}</InkLabel></Pressable>:null}{retry('todos')}</Card>:null}
      </>}
     </ScrollView>
    </View>
   </View>
  </Modal>
 </View>;
}
const s=StyleSheet.create({fill:{flex:1},icon:{width:44,height:44,alignItems:'center',justifyContent:'center'},panel:{position:'absolute',borderWidth:1,borderRadius:16,overflow:'hidden',shadowOpacity:.18,shadowRadius:12,shadowOffset:{width:0,height:8}},header:{flexDirection:'row',alignItems:'center',paddingLeft:12,minHeight:48},cards:{gap:12,padding:12},card:{borderWidth:1,borderRadius:16,padding:14,gap:10,minWidth:0},row:{flexDirection:'row',alignItems:'center',gap:9,minHeight:56,paddingVertical:8},action:{minHeight:44,justifyContent:'center'}});
