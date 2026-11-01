// [Input] Production Native task activity/source components and explicit synthetic read-only DTO transport.
// [Output] Actual Hermes presentation/lifecycle qualification with zero account/model/Notion/business operations.
// [Pos] Explicit technical entry; excluded from ordinary index.native.js and normal sessions.
import '../../src/platform/sdkWebApis.native';
import {useEffect,useState} from 'react';
import {AppRegistry,Pressable,Text,TextInput,View} from 'react-native';
import '../../app/_dream/i18n';
import useNativeTaskActivity from '../../app/_dream/components/chat/useNativeTaskActivity.native';
import PlanButton from '../../app/_dream/components/chat/PlanPanel.native';
import ChatMessageList from '../../app/_dream/components/chat/ChatMessageList.native';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import useInkColors from '../../src/components/useInkColors.native';
import {createTaskActivityFixture} from './task-activity-fixture';
export const taskActivityFixture=createTaskActivityFixture();
export function TaskActivityParity({lifecycle}:{lifecycle?:(state:string)=>void}){
 const {f,transport}=taskActivityFixture,c=useInkColors(),[ready,setReady]=useState(false),[thread,setThread]=useState('fixture-thread'),[draft,setDraft]=useState(''),[active,setActive]=useState(true),[more,setMore]=useState(false);
 const activity=useNativeTaskActivity(ready?thread:null,{active,running:false,transport,refreshIntervalMs:f.interval,onSessionExpired:()=>{f.expired++;}});
 useEffect(()=>{void loadBrowserSession(transport).then(()=>setReady(true));},[]);
 const navigate=(id:string)=>{f.navigation.push(id);setThread(id);};
 const button=(name:string,action:()=>void)=><Pressable key={name} accessibilityRole="button" accessibilityLabel={name} onPress={action} style={{padding:8,minHeight:44,borderWidth:1,borderColor:c['color-border-paper']}}><Text style={{color:c['color-text-primary']}}>{name}</Text></Pressable>;
 const mode=(value:string)=>{f.mode=value;activity.refresh();};
 const inspection={threadId:thread,loading:activity.loading,failed:[...activity.failed],revision:activity.revision,source:activity.data.links?.source?.source_thread_id,reads:f.calls.length,links:activity.data.links?.created.map(link=>link.title),plan:activity.data.plan?.content,foreground:activity.foreground};
 if(typeof window!=='undefined')(window as unknown as {__taskFixture:unknown}).__taskFixture={f,activity,inspection};
 return <View style={{flex:1,backgroundColor:c['color-bg-app'],padding:12,gap:8}}><Text style={{color:c['color-text-primary']}}>Task activity — technical fixture</Text><Text style={{color:c['color-text-muted'],fontSize:11}}>Synthetic records. Account, model, Notion and business submissions: 0.</Text>
  <View style={{flexDirection:'row',flexWrap:'wrap',gap:4}}>{button('All sections',()=>mode('all'))}{button('Empty sections',()=>mode('none'))}{(['links','scheduled','agents','plan','todos']).map(value=>button('Only '+value,()=>mode(value)))}{button('Fail plan',()=>{f.fail.add('plan');activity.refresh();})}{button('Restore reads',()=>{f.fail.clear();f.hold.clear();activity.refresh();})}{button('Hold plan',()=>{f.hold.add('plan');f.version++;activity.refresh();})}{button('Switch Thread',()=>setThread(value=>value==='fixture-thread'?'child-thread':'fixture-thread'))}{button(active?'Hide reader':'Show reader',()=>setActive(value=>!value))}{button(more?'First page':'Older pages',()=>setMore(value=>!value))}{lifecycle?<>{button('Background',()=>lifecycle('background'))}{button('Foreground',()=>lifecycle('active'))}</>:null}</View>
  <TextInput accessibilityLabel="Underlying Chat draft" value={draft} onChangeText={setDraft} style={{minHeight:44,padding:10,color:c['color-text-primary'],borderWidth:1,borderColor:c['color-border-paper']}}/>
  <View style={{flexDirection:'row',justifyContent:'flex-end'}}>{ready?<PlanButton key={thread} threadId={thread} activity={activity} active={active} onNavigateThread={navigate} onOpenScheduledTask={task=>{f.scheduled.push(task.id);}}/>:null}</View>
  <View style={{flex:1,minHeight:0}}><ChatMessageList threadId={thread} isLoading={false} messages={[{id:'user',role:'user',parts:[{type:'text',text:'Original user message.'}]},{id:'reply',role:'assistant',parts:[{type:'text',text:'Original saved reply.'}]}]} historyHasMore={more} sourceThread={activity.data.links?.source} onNavigateThread={navigate}/></View>
  <Text testID="task-fixture-inspection" style={{color:c['color-text-muted'],fontSize:10}}>{JSON.stringify(inspection)}</Text>
 </View>;
}
AppRegistry.registerComponent('InkMemory',()=>TaskActivityParity);
