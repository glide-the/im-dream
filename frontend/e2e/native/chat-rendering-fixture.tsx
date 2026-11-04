// [Input] Production Native Chat page/composer/Hook, original DTO/SSE and explicit in-memory provider boundaries.
// [Output] APP-06 isolated send/stream/Stop/history journey on Hermes and the original composer Web document.
// [Pos] Simulator-only composition; no account, database, runtime service or model execution.
// [Sync] 2026-11-03: add an idle historical turn to measure native scroll stability without network or message updates.
import '../../src/platform/sdkWebApis.native';
import React,{useEffect,useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,Settings,StyleSheet,View} from 'react-native';
import type {UIMessage} from 'ai';
import i18n from '../../app/_dream/i18n';
import ChatPage from '../../app/_dream/components/chat/ChatPage.native';
import ChatMessageList from '../../app/_dream/components/chat/ChatMessageList.native';
import AIInputDock from '../../app/_dream/components/chat/AIInputDock.native';
import useNativeChatThread from '../../app/_dream/components/chat/useNativeChatThread.native';
import useNativeChatHistory from '../../app/_dream/components/chat/useNativeChatHistory.native';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import {setThemeMode} from '../../app/_dream/utils/theme.native';
import InkLabel from '../../src/components/InkLabel.native';
import useInkColors from '../../src/components/useInkColors.native';

const origin=Settings.get('ink-app06-origin') as string|undefined;
const samples={
  Long:Array.from({length:35},(_,i)=>`Paragraph ${i+1}. I would like to understand this experience and preserve every original line.`).join('\n\n'),
  Markdown:['# A long input','> A quoted thought','- First item\n  - Nested item','```js\nconst longLine = "'+'word '.repeat(60)+'";\n```',...Array.from({length:20},(_,i)=>`## Section ${i+1}\n\nPlease keep this complete paragraph and its line break.\nAnother line.`)].join('\n\n'),
  Code:'Please read this short code sample.\n\n```js\nconst small = 1;\n```\n\nEnd of user code.',
};
const reply=['Reply opening.','```js\nconst replyValue = 2;\n```','- First item\n  - Nested reply\n\n> Quoted reply','```\n\n```','```js\n'+('long_'.repeat(80))+'\n```','Reply complete.'].join('\n\n');
const stableMessages:UIMessage[]=[
  {id:'stable-previous',role:'assistant',parts:[{type:'text',text:Array.from({length:18},(_,i)=>`Earlier paragraph ${i+1}. A retained note keeps the original conversation scrollable.`).join('\n\n')}]},
  {id:'stable-user',role:'user',parts:[{type:'text',text:Array.from({length:5},(_,i)=>`第${i+1}段。继续检查同一对话的阅读布局，保留完整内容和原有业务。这里只观察消息位置，包含 Markdown、中文、English 和换行。`).join('\n\n')}]},
  {id:'stable-reply',role:'assistant',parts:[{type:'reasoning',text:'A completed process.'},{type:'text',text:'Stable reply.'}],metadata:{turnId:'stable-turn',turnStatus:'completed',finalPartIndex:1,durationMs:14000}},
];
const stableIds=new Set(stableMessages.map(message=>message.id));
const f={calls:[] as {path:string;method:string;body:unknown}[],rows:[] as {id:string;title:string;created_at:string;updated_at:string}[],saved:new Map<string,UIMessage[]>(),running:false,continue:()=>{},finish:false,stop:false,sequence:0,submitted:'',turns:0};
const json=(value:unknown)=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
const frame=(value:object)=>`data: ${JSON.stringify(value)}\n\n`;
async function transport(input:RequestInfo|URL,init:RequestInit={}){
  const path=String(input),method=init.method??'GET',body=init.body?JSON.parse(String(init.body)):null;
  f.calls.push({path,method,body});
  if(path==='/auth/session')return json({user:{id:'1',email:'app06@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
  const url=new URL(path,'http://fixture.invalid');
  if(url.pathname==='/api/claude-agent/threads'){
    if(method==='POST'){const id=`app06-thread-${++f.sequence}`,now=new Date().toISOString();f.rows.unshift({id,title:`Saved fixture ${f.sequence}`,created_at:now,updated_at:now});f.saved.set(id,[]);return json({thread_id:id});}
    return json({threads:f.rows});
  }
  const match=/\/threads\/([^/]+)\/(messages|status|inputs|stop)$/.exec(url.pathname);
  if(match){
    const id=match[1],messages=f.saved.get(id)??[];
    if(match[2]==='messages')return json({thread:f.rows.find(row=>row.id===id),messages:messages.map(row=>({...row,created_at:'2026-11-03T00:00:00Z'})),has_more:false,next_cursor:null,latest_message_id:messages.at(-1)?.id??null,unchanged:false});
    if(match[2]==='status')return json({running:f.running,lifecycle:f.running?'running':'idle',turn_count:f.turns,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
    if(match[2]==='inputs')return json({entries:[],local_owner:false});
    if(match[2]==='stop'){f.stop=true;f.finish=true;f.running=false;f.continue();return json({ok:true,thread_id:id,stop_requested:true,running:false,lifecycle:'idle'});}
  }
  throw Error(`Unexpected APP-06 fixture request ${method} ${url.pathname}`);
}
async function stream(path:string,init:RequestInit={}){
  if(path!=='/api/claude-agent'||init.method!=='POST')throw Error('Unexpected APP-06 stream');
  const body=JSON.parse(String(init.body));f.calls.push({path,method:'POST',body});f.submitted=body.message.parts.filter((part:{type:string})=>part.type==='text').map((part:{text:string})=>part.text).join('');
  f.running=true;f.finish=false;f.stop=false;f.turns++;const turnId=`app06-turn-${f.turns}`,saved=[...(f.saved.get(body.id)??[]),body.message];f.saved.set(body.id,saved);
  let text='';
  return {status:200,cancel(){f.continue();},chunks:(async function*(){
    yield frame({type:'message-metadata',turnId});
    while(!f.finish){
      text+=(text?'\n\n':'')+reply;
      yield frame({type:'text-delta',delta:(text===reply?'':'\n\n')+reply});
      await new Promise<void>(resolve=>{f.continue=resolve;});
    }
    f.running=false;f.saved.set(body.id,[...saved,{id:`app06-reply-${f.turns}`,role:'assistant',parts:[{type:'text',text}],metadata:{turnId,turnStatus:f.stop?'cancelled':'completed'}}]);
    yield frame({type:'finish',finishReason:'stop'});
  })()};
}
function Fixture(){
  const colors=useInkColors();const [prefill,setPrefill]=useState(''),[nonce,setNonce]=useState(0),[tick,setTick]=useState(0),[editorActive,setEditorActive]=useState(true),[stable,setStable]=useState(false);
  const session=useNativeChatThread({context:{imFullAccessEnabled:false,currentToolChoice:'manual'},transport:transport as typeof fetch,stream});
  const history=useNativeChatHistory({enabled:!session.threadId,transport:transport as typeof fetch});
  const controls:Record<string,()=>void>={...Object.fromEntries(Object.entries(samples).map(([key,value])=>[key,()=>{setStable(false);setEditorActive(true);setPrefill(value);setNonce(n=>n+1);}])),'Stable':()=>setStable(true),'Next':()=>{f.continue();setTick(n=>n+1);},'Finish':()=>{f.finish=true;f.continue();setTick(n=>n+1);},'Hide keyboard':()=>setEditorActive(false),'Back':()=>{setStable(false);session.newChat();},'Light':()=>setThemeMode('light'),'Dark':()=>setThemeMode('dark')};
  return <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
    <View style={styles.controls}>{Object.entries(controls).map(([label,onPress])=><Pressable key={label} accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={styles.control}><InkLabel style={{color:colors['color-text-primary'],fontSize:12}}>{label}</InkLabel></Pressable>)}</View>
    <ChatPage hasConversation={stable||Boolean(session.threadId)} history={history} activeThreadId={session.threadId} quickActions={[]} onQuickAction={()=>{}} onSelectThread={id=>void session.openThread(id)} onDeleteThread={()=>{}}
      composer={<AIInputDock origin={origin!} active={editorActive} onSendMessage={session.send} onStop={session.threadId?session.stop:undefined} stopPending={session.stopping} disabled={session.unknown} loading={session.running||session.posting} fullAccessEnabled={false} defaultToolChoice="manual" workspaceEnabled={false} onOpenSketch={()=>{}} prefill={prefill} prefillNonce={nonce}/>}
      conversation={stable?<ChatMessageList messages={stableMessages} threadId="stable-history" isLoading={false} historicalMessageIds={stableIds} transport={transport as typeof fetch} origin={origin}/>:<ChatMessageList messages={session.messages} threadId={session.threadId??''} isLoading={session.running||session.posting} initialLoading={session.recovering} historicalMessageIds={session.historicalMessageIds} transport={transport as typeof fetch} origin={origin}/>}/>
    <InkLabel testID="app06-receipt" style={{fontSize:10,color:colors['color-text-secondary']}}>{`APP06 ${session.threadId??'home'} ${session.running?'running':'idle'} saved=${f.saved.get(session.threadId??'')?.length??0} exact=${Object.values(samples).includes(f.submitted)} posts=${f.calls.filter(call=>call.path==='/api/claude-agent'&&call.method==='POST').length} stops=${f.calls.filter(call=>call.path.endsWith('/stop')&&call.method==='POST').length} tick=${tick}`}</InkLabel>
    <View style={styles.tabs}><InkLabel style={{color:colors['color-text-secondary']}}>Chat</InkLabel><InkLabel style={{color:colors['color-text-secondary']}}>Decks</InkLabel><InkLabel style={{color:colors['color-text-secondary']}}>More</InkLabel></View>
  </SafeAreaView>;
}
function Boot(){const [ready,setReady]=useState(false);useEffect(()=>{void i18n.changeLanguage('en').then(()=>loadBrowserSession(transport as typeof fetch)).then(()=>setReady(true));},[]);return origin&&ready?<Fixture/>:<InkLabel>Preparing APP-06 fixture</InkLabel>;}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},controls:{flexDirection:'row',flexWrap:'wrap',paddingHorizontal:8},control:{minHeight:44,paddingHorizontal:8,justifyContent:'center'},tabs:{flexDirection:'row',justifyContent:'space-around',height:44,alignItems:'center'}});
AppRegistry.registerComponent('InkMemory',()=>Boot);
