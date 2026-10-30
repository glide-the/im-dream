// [Input] Production history hook/list, actual AppState and explicit synthetic or normal read-only transport.
// [Output] Separate Hermes lifecycle and normal HTTP qualification; no model request or business mutation.
// [Pos] Explicit validation entry only; the ordinary native and Web entries exclude this module.
// [Sync] 2026-10-29: normal-session mode masks titles and filters only its first local snapshot, then rereads the original GET.
import {useEffect,useState} from 'react';
import {AppRegistry,AppState,Pressable,SafeAreaView,Text,View,useColorScheme} from 'react-native';
import {useTranslation} from 'react-i18next';
import '../../app/_dream/i18n';
import type {ChatHistoryThread} from '../../app/_dream/api/chatHistoryApi';
import useNativeChatHistory from '../../app/_dream/components/chat/useNativeChatHistory.native';
import ChatHistoryList from '../../app/_dream/components/chat/ChatHistoryList.native';
import {groupChatThreadsByDate} from '../../app/_dream/components/chat/chatHistoryPresentation';
import {inkColors} from '../../src/components/inkColors';
import SessionGate from '../../src/platform/SessionGate.native';
import {clientFetch} from '../../src/platform/transport.native';

const row=(id:string,title:string):ChatHistoryThread=>({id,title,created_at:new Date().toISOString(),updated_at:new Date().toISOString()});
const fixture={rows:[row('fixture-original','Original saved fixture')],reads:0,aborted:0,hold:false,pending:[] as Array<()=>void>,lastPath:''};
const reply=(body:unknown)=>new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
const transport:typeof fetch=async(input,init)=>{
  if(init?.method && init.method!=='GET')throw new Error('UNEXPECTED_FIXTURE_MUTATION');
  const path=String(input);
  if(!path.startsWith('/api/claude-agent/threads'))throw new Error('UNEXPECTED_FIXTURE_HTTP');
  fixture.reads++;fixture.lastPath=path;
  const snapshot={threads:[...fixture.rows]};
  if(!fixture.hold)return reply(snapshot);
  return new Promise<Response>((resolve,reject)=>{
    let settled=false;
    const abort=()=>{if(settled)return;settled=true;fixture.aborted++;reject(new Error('FIXTURE_READ_ABORTED'));};
    fixture.pending.push(()=>{if(settled)return;settled=true;init?.signal?.removeEventListener('abort',abort);resolve(reply(snapshot));});
    init?.signal?.addEventListener('abort',abort,{once:true});
    if(init?.signal?.aborted)abort();
  });
};
const liveFixture={reads:0,hideFirst:true,targetId:'',lastStatus:0,sourceCount:0,lastPath:''};
const liveTransport:typeof fetch=async(input,init)=>{
  const path=String(input);
  if((init?.method && init.method!=='GET') || !path.startsWith('/api/claude-agent/threads'))throw new Error('UNEXPECTED_LIVE_FIXTURE_OPERATION');
  liveFixture.reads++;liveFixture.lastPath=path;
  const response=await clientFetch(input,init);liveFixture.lastStatus=response.status;
  if(!response.ok)return response;
  const body=await response.json() as {threads?:ChatHistoryThread[]};
  if(!Array.isArray(body.threads))throw new Error('LIVE_FIXTURE_DTO_INVALID');
  liveFixture.sourceCount=body.threads.length;liveFixture.targetId ||= body.threads[0]?.id ?? '';
  // Only the diagnostic's local initial snapshot is filtered. Server data is unchanged.
  const rows=body.threads.filter(item=>!liveFixture.hideFirst || item.id!==liveFixture.targetId)
    .map(item=>({...item,title:`Saved record ${item.id.slice(0,8)}`}));
  return reply({...body,threads:rows});
};

function HistoryLifecycleFixture({live=false,onSessionExpired}:{live?:boolean;onSessionExpired?:()=>void}){
  const {t}=useTranslation(),colors=inkColors('system',useColorScheme()==='dark');
  const [enabled,setEnabled]=useState(true),[revision,setRevision]=useState(0),[selected,setSelected]=useState('none');
  const [appState,setAppState]=useState(AppState.currentState);
  useEffect(()=>{const listener=AppState.addEventListener('change',setAppState);return()=>listener.remove();},[]);
  const history=useNativeChatHistory({enabled,transport:live?liveTransport:transport,onSessionExpired});
  const button=(label:string,onPress:()=>void)=><Pressable key={label} accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={{minHeight:44,padding:10,borderWidth:1,borderColor:colors['color-border-paper'],borderRadius:10}}><Text style={{color:colors['color-text-primary']}}>{label}</Text></Pressable>;
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}>
    <View style={{padding:12,gap:8}}>
      <Text style={{color:colors['color-text-primary']}}>{live?'Normal session — read-only technical fixture':'Native history lifecycle — fixture only'}</Text>
      <Text testID="fixture-lifecycle-state" style={{color:colors['color-text-primary']}}>{`AppState=${appState}; enabled=${enabled}; reads=${live?liveFixture.reads:fixture.reads}; aborted=${live?'n/a':fixture.aborted}; latest=${history.threads[0]?.id ?? 'none'}; loading=${history.loading}; error=${history.error}; revision=${revision}; selected=${selected}`}</Text>
      <Text style={{color:colors['color-text-muted']}}>{live?`${liveFixture.lastPath}; status=${liveFixture.lastStatus}; sourceCount=${liveFixture.sourceCount}; target=${liveFixture.targetId}; filtered=${liveFixture.hideFirst}`:fixture.lastPath}</Text>
      <View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>
        {button('Enter fixture conversation',()=>setEnabled(false))}
        {button(live?'Use unfiltered GET response':'Save latest fixture',()=>{if(live)liveFixture.hideFirst=false;else fixture.rows=[row('fixture-latest','Newly saved fixture'),...fixture.rows.filter(item=>item.id!=='fixture-latest')];setRevision(value=>value+1);})}
        {button('Return to fixture home',()=>setEnabled(true))}
        {button('Refresh fixture history',()=>{void history.reload();})}
        {!live?button('Hold next fixture read',()=>{fixture.hold=true;setRevision(value=>value+1);}):null}
        {!live?button('Release fixture reads',()=>{fixture.hold=false;fixture.pending.splice(0).forEach(release=>release());setRevision(value=>value+1);}):null}
      </View>
    </View>
    {enabled?<ChatHistoryList groups={groupChatThreadsByDate(history.threads,t)} activeThreadId={selected} loading={history.loading} loadingMore={history.loadingMore}
      error={history.error} moreError={history.moreError} hasMore={history.hasMore} onSelectThread={setSelected} onDeleteThread={()=>{}}
      onReload={()=>void history.reload()} onLoadMore={()=>void history.loadMore()}/>:<View style={{flex:1,padding:16}}><Text style={{color:colors['color-text-primary']}}>Fixture conversation: history reads disabled.</Text></View>}
  </SafeAreaView>;
}
function Entry(){
  const [live,setLive]=useState(false);
  return live?<SessionGate>{(_logout,refreshSession)=><HistoryLifecycleFixture live onSessionExpired={()=>void refreshSession()}/>}</SessionGate>:<View style={{flex:1}}>
    <HistoryLifecycleFixture/>
    <Pressable accessibilityRole="button" accessibilityLabel="Use normal read-only transport" style={{minHeight:48,padding:12,backgroundColor:'#f5efe5'}} onPress={()=>setLive(true)}><Text>Use normal read-only transport</Text></Pressable>
  </View>;
}
AppRegistry.registerComponent('InkMemory',()=>Entry);
