// [Input] Production native context badge, original metadata API DTOs and an in-memory fixture transport.
// [Output] Isolated Hermes metadata, selection, copy and foreground lifecycle qualification.
// [Pos] Explicit component build entry; no backend startup, real account, model, database or mutation calls.
import {useMemo,useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,Text,View,useColorScheme} from 'react-native';
import '../../app/_dream/i18n';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import type {Deck,Voice} from '../../app/_dream/api/voiceApi';
import PluginReceiptBadge,{ChatAgentBadge} from '../../app/_dream/components/chat/PluginReceiptBadge.native';
import ChatTopActions from '../../app/_dream/components/chat/ChatTopActions.native';
import {inkColors} from '../../src/components/inkColors';

const voices:Voice[]=[
  {id:'fixture-author',deck_id:'fixture-deck',name:'Author',name_en:'Author',system_prompt:'Fixture author',enabled:true,is_system:false,icon:'brain',color:'blue'},
  {id:'fixture-editor',deck_id:'fixture-deck',name:'Editor',name_en:'Editor',system_prompt:'Fixture editor',enabled:true,is_system:false,icon:'brain',color:'green'},
];
const fixture={packed:false,reads:0,onRead:(_:number)=>{}};
function reply(body:unknown){return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});}
const transport:typeof fetch=async(input,init)=>{
  if(init?.method && init.method!=='GET')throw Error('UNEXPECTED_FIXTURE_MUTATION');
  if(init?.signal?.aborted)throw Error('HTTP_ABORTED');
  const path=String(input);fixture.onRead(++fixture.reads);
  console.info(`PLUGIN_CONTEXT_FIXTURE_READ count=${fixture.reads} method=GET`);
  if(path==='/api/claude-plugins/installations')return reply({installations:[{id:'fixture-installation',package_name:'Configured plugin',resolved_version:'0.5.0',status:'ready',deck_refs:[{deck_id:'fixture-deck',enabled:true}]}]});
  if(path==='/api/claude-agent/threads/fixture-thread/plugin-load-receipt')return reply({thread_id:'fixture-thread',deck_id:'fixture-deck',workspace_found:true,receipt:{schema_version:'1',workspace:'fixture',deck_id:'fixture-deck',packed_at:null,frozen:true,plugins:fixture.packed?[{package_spec:'Packed plugin@fixture',resolved_version:'1.2.3',artifact_digest:'sha256:'+'b'.repeat(64),relative_path:'plugins/fixture',verified:true}]:[]},launch_manifest:null});
  throw Error('UNEXPECTED_FIXTURE_HTTP');
};
// Fixture session lives only in this explicitly selected JS entry.
void loadBrowserSession(async()=>reply({user:{id:'42',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
function PluginContextFixture(){
  const [agent,setAgent]=useState(voices[0]),[long,setLong]=useState(false),[reads,setReads]=useState(fixture.reads),[event,setEvent]=useState('No context action');
  fixture.onRead=setReads;
  const colors=inkColors('system',useColorScheme()==='dark');
  const deck=useMemo<Deck>(()=>({id:'fixture-deck',name:'Writing',name_en:long?'Writing '.repeat(18):'Writing',is_system:false,enabled:true,voices}),[long]);
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><View style={{padding:12,gap:20,flex:1}}>
    <Text style={{color:colors['color-text-primary']}}>Component validation — no backend started</Text>
    <View style={{flexDirection:'row'}}><View style={{flex:1}}/><ChatTopActions creating={false} activityOpen={false} workspaceOpen={false} workspaceEnabled={false}
      contextBadge={<ChatAgentBadge voice={{...agent,name:long?`${agent.name} `.repeat(18):agent.name}}/>}
      pluginReceipt={<PluginReceiptBadge threadId="fixture-thread" deck={deck} activeVoiceId={agent.id} activeVoiceName={agent.name} transport={transport} onSelectAgent={id=>{const next=voices.find(voice=>voice.id===id);if(next){setAgent(next);setEvent(`Selected ${next.name}`);}}}/>}
      onNewChat={()=>setEvent('New action only')} onToggleActivity={()=>setEvent('Activity action only')} onToggleWorkspace={()=>setEvent('Workspace action only')} onShare={()=>setEvent('Share action only')}/></View>
    <Text testID="context-event" style={{color:colors['color-text-primary']}}>{event}</Text>
    <Text testID="context-reads" style={{color:colors['color-text-primary']}}>{`Metadata reads: ${reads}`}</Text>
    <Pressable accessibilityRole="button" onPress={()=>{fixture.packed=true;setEvent('Packed fixture ready');}} style={{minHeight:44,justifyContent:'center'}}><Text style={{color:colors['color-text-primary']}}>Show packed fixture</Text></Pressable>
    <Pressable accessibilityRole="button" onPress={()=>setLong(value=>!value)} style={{minHeight:44,justifyContent:'center'}}><Text style={{color:colors['color-text-primary']}}>Toggle long names</Text></Pressable>
  </View></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>PluginContextFixture);
