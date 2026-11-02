// [Input] Actual Hermes/AppState, production activity/detail/history components and explicit synthetic HTTP DTOs.
// [Output] Isolated native read-only activity/detail controls and lifecycle receipts with the source input retained.
// [Pos] UI qualification entry only; no runtime startup, real credentials, backend, model or database calls.
import '../../src/platform/sdkWebApis.native';
import {useEffect,useState} from 'react';
import {AppRegistry,AppState,Keyboard,Pressable,SafeAreaView,StyleSheet,TextInput,View,useColorScheme} from 'react-native';
import {useTranslation} from 'react-i18next';
import '../../app/_dream/i18n';
import ActivitySidebar,{nativeActivityFilters} from '../../app/_dream/components/chat/ActivitySidebar.native';
import ScheduledTaskDetailSidebar from '../../app/_dream/components/chat/ScheduledTaskDetailSidebar.native';
import ChatHistorySearch from '../../app/_dream/components/chat/ChatHistorySearch.native';
import useNativeActivitySidebarData from '../../app/_dream/components/chat/useNativeActivitySidebarData.native';
import useNativeChatHistory from '../../app/_dream/components/chat/useNativeChatHistory.native';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import type {ScheduledTask,ScheduledTrigger} from '../../app/_dream/api/scheduledTaskApi';
import type {ScheduledTaskMarkerSnapshot} from '../../app/_dream/components/chat/scheduledTaskMarkerModel';
import InkLabel from '../../src/components/InkLabel.native';
import {inkColors} from '../../src/components/inkColors';
const now=Date.now(),iso=(delta=0)=>new Date(now+delta).toISOString();
const task:ScheduledTask={id:'fixture-task',source_thread_id:'fixture-source',title:'Daily native task',prompt:'Keep the existing schedule',rule:{kind:'daily',local_time:'09:00',time_zone:'Asia/Shanghai'},run_thread_mode:'new_thread_each_run',model_alias:'fixture-model',next_run_at:iso(86400000),status:'active',revision:3,created_at:iso(-100000),updated_at:iso(-1000)};
const trigger:ScheduledTrigger={id:'fixture-trigger',task_id:task.id,kind:'scheduled',scheduled_at:iso(-10000),definition_revision:3,title:task.title,source_thread_id:task.source_thread_id,time_zone:'Asia/Shanghai',status:'running',task_session_id:null,target_thread_id:'fixture-execution',input_message_id:null,target_turn_id:null,final_message_id:null,error_code:null,run_thread_mode_snapshot:'new_thread_each_run',model_alias_snapshot:'fixture-model',skipped_from_at:null,skipped_through_at:null,created_at:iso(-10000),updated_at:iso(-1000)};
const rows=Array.from({length:24},(_,i)=>({id:`fixture-chat-${i}`,title:`Existing Chat ${i}`,created_at:iso(-i*1000-1000),updated_at:iso(-i*1000-1000)}));
let calls=0,mutations=0;
const json=(value:unknown)=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
const transport:typeof fetch=async(input,init={})=>{
  const path=String(input),url=new URL(path,'http://fixture.invalid');calls++;if(init.method&&init.method!=='GET'){mutations++;throw Error('Unexpected fixture mutation');}
  if(url.pathname==='/auth/session')return json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
  if(url.pathname==='/api/claude-agent/threads'){
    const query=url.searchParams.get('query'),offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||100);
    const selected=query?rows.filter(row=>row.title.includes(query)).map(row=>({...row,match:{strategy:'fuzzy',score:1,fields:['title'],excerpt:`Matching ${query}`}})):rows;
    return json({threads:selected.slice(offset,offset+limit)});
  }
  if(url.pathname==='/api/claude-agent/scheduled-tasks/day')return json({tasks:[task],triggers:[trigger]});
  if(url.pathname===`/api/claude-agent/scheduled-tasks/${task.id}`)return json({task});
  if(url.pathname===`/api/claude-agent/scheduled-tasks/${task.id}/history`)return json({triggers:[trigger,{...trigger,id:'fixture-reuse',target_thread_id:task.source_thread_id}]});
  throw Error(`Unexpected fixture path ${path}`);
};
function Page(){
  const {t}=useTranslation(),colors=inkColors('system',useColorScheme()==='dark'),text={color:colors['color-text-primary']};
  const [open,setOpen]=useState(false),[detail,setDetail]=useState<{taskId:string;snapshot?:ScheduledTaskMarkerSnapshot|null}|null>(null),[filters,setFilters]=useState(nativeActivityFilters),[draft,setDraft]=useState('Existing unsent draft'),[selected,setSelected]=useState('none'),[state,setState]=useState(AppState.currentState);
  const history=useNativeChatHistory({enabled:open,transport}),activity=useNativeActivitySidebarData(open,{transport});
  useEffect(()=>{const listener=AppState.addEventListener('change',setState);return()=>listener.remove();},[]);
  const select=(id:string)=>{setSelected(id);setOpen(false);setDetail(null);};
  return <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
    <View style={styles.receipt}><InkLabel style={text}>{`Native activity · ${state} · reads ${calls} · mutations ${mutations}`}</InkLabel><InkLabel style={text}>{`Selected ${selected} · active ${String(activity.active)}`}</InkLabel>
      <TextInput accessibilityLabel="Source draft" value={draft} onChangeText={setDraft} style={[styles.input,text,{borderColor:colors['color-border-paper']}]} />
      <Pressable accessibilityRole="button" accessibilityLabel="Open activity" onPress={()=>{Keyboard.dismiss();setDetail(null);setOpen(true);}} style={styles.button}><InkLabel style={text}>{t('chat.activity.entry')}</InkLabel></Pressable>
    </View>
    <View style={styles.fill}>{open?<ActivitySidebar activity={activity} history={history} activeThreadId="fixture-chat-0" filters={filters} onFiltersChange={setFilters} onClose={()=>setOpen(false)} onSelectThread={select} onDeleteThread={()=>{throw Error('Unexpected fixture deletion');}} onTask={row=>{setOpen(false);setDetail({taskId:row.id,snapshot:row.snapshot});}}/>:null}
      {detail?<ScheduledTaskDetailSidebar {...detail} transport={transport} onClose={()=>setDetail(null)} onOpenThread={select}/>:null}
      <ChatHistorySearch history={history} activeThreadId="fixture-chat-0" onSelect={select}/>
    </View>
  </SafeAreaView>;
}
function Boot(){const [ready,setReady]=useState(false);useEffect(()=>{void loadBrowserSession(transport).then(()=>setReady(true));},[]);return ready?<Page/>:<InkLabel>Preparing activity fixture</InkLabel>;}
AppRegistry.registerComponent('InkMemory',()=>Boot);
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},receipt:{padding:12,gap:4},input:{minHeight:44,padding:8,borderWidth:1,borderRadius:8,fontFamily:'Excalifont',fontSize:16},button:{minHeight:44,justifyContent:'center'}});
