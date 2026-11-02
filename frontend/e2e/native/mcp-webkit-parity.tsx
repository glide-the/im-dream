// [Sync] 2026-10-31: explicit launch argument enables bounded real Hermes/WebKit close/reopen integration; ordinary entry remains excluded.
// [Input] Original Native message/tool surfaces, App-owned runtime and explicit loopback MCP fixture origin.
// [Output] Actual Hermes/WebKit form, history/DTO/visibility persistence and callback/close qualification.
// [Pos] Explicit technical entry only; normal index.native.js, real credentials and Chat submissions remain excluded.
import '../../src/platform/sdkWebApis.native';
import {useEffect,useMemo,useRef,useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,Settings,Text,TextInput,View} from 'react-native';
import {isToolUIPart,type UIMessage} from 'ai';
import '../../app/_dream/i18n';
import {BackendRuntimeManager} from '../../src/runtime/BackendRuntimeManager';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import ChatMessageList from '../../app/_dream/components/chat/ChatMessageList.native';
import {closeToolResultDocuments} from '../../app/_dream/components/chat/ToolResultSurface.native';
import ToolMessagePart from '../../app/_dream/components/chat/ToolMessagePart.native';
import {mergeRecoveredLatestPage} from '../../app/_dream/components/chat/chatHistoryWindow';
import useInkColors from '../../src/components/useInkColors.native';
import {appPart,originalMessage} from './mcp-webkit-fixture';
import {MCP_APPS_HOST_MANIFEST} from '../../app/_dream/components/chat/mcp-apps/host-policy';
import type {ChatUserMessage} from '../../app/_dream/components/chat/chatUserMessageIngress';
const transport:typeof fetch=async input=>String(input)==='/auth/session'?new Response(JSON.stringify({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)})):new Response(JSON.stringify({...originalMessage,id:'stored-message',created_at:'2026-10-31T00:00:00Z'}));
function Entry(){
 const documentOwner=useMemo(()=>({}),[]);
 const c=useInkColors(),[runtime,setRuntime]=useState(''),[candidate,setCandidate]=useState(''),[origin,setOrigin]=useState(''),[error,setError]=useState(''),[ready,setReady]=useState(false);
 const [thread,setThread]=useState('webkit-thread'),[messages,setMessages]=useState<UIMessage[]>([originalMessage]),[historical,setHistorical]=useState(false),[visible,setVisible]=useState(true),[draft,setDraft]=useState('');
 const [sent,setSent]=useState<ChatUserMessage[]>([]),[expired,setExpired]=useState(0);
 useEffect(()=>{void loadBrowserSession(transport).then(()=>setReady(true));},[]);
 const observed=useRef({thread,visible});observed.current={thread,visible};
 const [qualification,setQualification]=useState('manual');
 useEffect(()=>{
  const requested=Settings.get('InkMcpQualificationOrigin');
  if(!ready||typeof requested!=='string'||!requested)return;
  let target:URL;try{target=new URL(requested);if(target.origin!==requested||target.protocol!=='http:'||!['localhost','127.0.0.1','[::1]'].includes(target.hostname))return;}catch{return;}
  let cancelled=false,step='runtime';
  const pause=()=>new Promise<void>(resolve=>setTimeout(resolve,100));
  async function request(path:string,body?:unknown):Promise<any>{
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),MCP_APPS_HOST_MANIFEST.defaults.hostReadyTimeoutMs);
   try{const response=await fetch(requested+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});if(!response.ok)throw Error('FIXTURE_HTTP_FAILED');return await response.json();}finally{clearTimeout(timer);}
  }
  async function waitFor(predicate:()=>Promise<boolean>){const end=Date.now()+MCP_APPS_HOST_MANIFEST.defaults.hostReadyTimeoutMs;while(!cancelled){if(await predicate())return;if(Date.now()>=end)throw Error('FIXTURE_WAIT_EXPIRED');await pause();}throw Error('FIXTURE_CANCELLED');}
  async function report(phase:'closed'|'reopened'|'complete'|'failed',elapsedMs=0){await request('/__fixture/proof',{phase,step,elapsedMs,nativeThread:observed.current.thread});}
  async function close(){const started=Date.now();await closeToolResultDocuments(documentOwner);const elapsed=Date.now()-started;if(elapsed>=MCP_APPS_HOST_MANIFEST.defaults.hostReadyTimeoutMs)throw Error('NATIVE_CLOSE_WAIT_EXPIRED');return elapsed;}
  async function run(){
   setQualification('running');const facts=await BackendRuntimeManager.ensureStarted();if(cancelled)return;
   const initial=await request('/__fixture/state');if(initial.appOrigin!==facts.localWebOrigin||initial.part?.toolCallId!==appPart.toolCallId)throw Error('FIXTURE_IDENTITY_MISMATCH');
   await request('/__fixture/control',{reset:true});setRuntime(facts.localWebOrigin);setCandidate(requested);setOrigin(requested);
   step='first_session';await waitFor(async()=>{const value=await request('/__fixture/state');return value.initializes===1&&value.resources===1&&value.activeSessions===1;});
   step='first_close';const first=await close();const closed=await request('/__fixture/state');if(closed.deletes!==1||closed.activeSessions!==0)throw Error('FIRST_SESSION_REMAINS');await report('closed',first);
   setThread('other-thread');setMessages([{id:'other',role:'assistant',parts:[{type:'text',text:'Other Thread reply.'}]}]);setHistorical(false);
   await waitFor(async()=>observed.current.thread==='other-thread');
   step='reopen';setThread('webkit-thread');setMessages([originalMessage]);
   await waitFor(async()=>{const value=await request('/__fixture/state');return value.initializes===2&&value.resources===2&&value.activeSessions===1;});await report('reopened');
   step='hidden_preservation';setVisible(false);await waitFor(async()=>observed.current.visible===false);setVisible(true);await waitFor(async()=>observed.current.visible===true);
   const retained=await request('/__fixture/state');if(retained.initializes!==2||retained.resources!==2||retained.deletes!==1)throw Error('HIDDEN_DOCUMENT_REPLACED');
   step='second_close';const second=await close();const final=await request('/__fixture/state');if(final.deletes!==2||final.activeSessions!==0)throw Error('SECOND_SESSION_REMAINS');
   await report('complete',second);if(!cancelled){setOrigin('');setQualification('passed');}
  }
  void run().catch(async()=>{if(cancelled)return;setError('Native close qualification failed at '+step);setQualification('failed');await report('failed').catch(()=>undefined);});
  return()=>{cancelled=true;};
 },[ready,documentOwner]);

 async function start(){try{setError('');setRuntime((await BackendRuntimeManager.ensureStarted()).localWebOrigin);}catch{setError('Packaged runtime unavailable');}}
 function open(){try{const value=new URL(candidate.trim());if(!runtime||!['http:','https:'].includes(value.protocol)||!['localhost','127.0.0.1','[::1]'].includes(value.hostname)||value.origin!==candidate.trim())throw Error();setOrigin(value.origin);setError('');}catch{setError('Use the explicit loopback fixture origin after starting the packaged runtime');}}
 const button=(label:string,action:()=>void)=><Pressable key={label} accessibilityRole="button" accessibilityLabel={label} onPress={action} style={{minHeight:44,padding:8,borderWidth:1,borderColor:c['color-border-paper']}}><Text style={{color:c['color-text-primary'],fontSize:12}}>{label}</Text></Pressable>;
 return <SafeAreaView style={{flex:1,backgroundColor:c['color-bg-app']}}><View style={{padding:8,gap:6,flex:1}}>
  <Text style={{color:c['color-text-primary']}}>MCP App — actual WebKit technical fixture</Text>
  <Text style={{color:c['color-text-muted'],fontSize:11}}>Synthetic form. Normal business/model/Notion submissions: 0.</Text>
  <View style={{flexDirection:'row',flexWrap:'wrap',gap:4}}>{button('Start packaged runtime',()=>void start())}{button('Open MCP document',open)}{button('Clone DTO',()=>setMessages(current=>JSON.parse(JSON.stringify(current))))}{button('Hydrate history',()=>{const summary={id:'stored-message',role:'assistant' as const,parts:[{type:'text' as const,text:'Original final reply.'}],metadata:{historyProjectionVersion:1,historyProcessAvailable:true,turnId:'webkit-turn',turnStatus:'completed',finalPartIndex:2,durationMs:1000}};setMessages(current=>mergeRecoveredLatestPage(current,[summary],new Set(['webkit-turn'])).messages);setHistorical(true);})}{button(visible?'Hide Chat':'Show Chat',()=>setVisible(value=>!value))}{button('Other Thread',()=>{void closeToolResultDocuments(documentOwner).then(()=>{setThread('other-thread');setMessages([{id:'other',role:'assistant',parts:[{type:'text',text:'Other Thread reply.'}]}]);setHistorical(false);});})}{button('Restore Thread',()=>{setThread('webkit-thread');setMessages([originalMessage]);setHistorical(false);})}</View>
  <TextInput accessibilityLabel="Technical fixture origin" value={candidate} onChangeText={setCandidate} autoCapitalize="none" autoCorrect={false} placeholder="http://127.0.0.1:fixture-port" style={{minHeight:44,padding:8,borderWidth:1,borderColor:c['color-border-paper'],color:c['color-text-primary']}}/>
  <TextInput accessibilityLabel="Underlying Chat draft" value={draft} onChangeText={setDraft} placeholder="Keep current draft" style={{minHeight:44,padding:8,borderWidth:1,borderColor:c['color-border-paper'],color:c['color-text-primary']}}/>
  {error?<Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{error}</Text>:null}
  <Text testID="webkit-native-inspection" style={{fontSize:10,color:c['color-text-muted']}}>{JSON.stringify({runtime,origin,thread,historical,visible,qualification,sent:sent.map(message=>message.parts),expired})}</Text>
  <View style={{flex:1,minHeight:0,display:visible?'flex':'none'}}>{origin&&ready?<ChatMessageList threadId={thread} origin={origin} messages={messages} isLoading={false} transport={transport} historicalMessageIds={historical?new Set(messages.map(message=>message.id)):new Set()} renderOtherPart={(part,_message,_index,presentation)=>isToolUIPart(part)?<ToolMessagePart documentOwner={documentOwner} part={part} origin={origin} threadId={thread} presentation={presentation} active={visible} isLoading={false} toolChoice="manual" sendUserMessage={async value=>setSent(previous=>[...previous,value])} addToolResult={()=>{}} onConfirmationSettled={()=>{}} onSessionExpired={()=>setExpired(value=>value+1)}/>:null}/>:null}</View>
 </View></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>Entry);
