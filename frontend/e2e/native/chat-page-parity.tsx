// [Sync] 2026-10-28: add canonical rich-history/process and long-conversation samples for actual Hermes Markdown, Copy and scroll checks; no business service is used.
// [Sync] 2026-10-28: use the production native message renderer and scroll owner in the Chat page fixture.
// [Input] Production native Chat page, composer, history/Thread coordinators and synthetic public HTTP/SSE replies.
// [Output] Isolated landing/search/selection/first-send layout evidence with the original Tiptap document.
// [Pos] Explicit component entry; only the editor document uses Mac Next; no backend, account, storage upload or model execution.
// [Sync] 2026-10-28: keep the synthetic HTTP connection open after canonical finish to verify native terminal recovery on Hermes.
// [Sync] 2026-10-28: expose received text length and exact synthetic long-draft comparison without changing production submission or SSE behavior.
import '../../src/platform/sdkWebApis.native';
import {useEffect,useRef,useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,StyleSheet,Text,View,useColorScheme} from 'react-native';
import {useTranslation} from 'react-i18next';
import '../../app/_dream/i18n';
import type {UIMessage} from 'ai';
import type {ChatHistoryThread} from '../../app/_dream/api/chatHistoryApi';
import type {Deck,Voice} from '../../app/_dream/api/voiceApi';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import useNativeChatHistory from '../../app/_dream/components/chat/useNativeChatHistory.native';
import useNativeChatThread from '../../app/_dream/components/chat/useNativeChatThread.native';
import ChatPage from '../../app/_dream/components/chat/ChatPage.native';
import ChatMessageList from '../../app/_dream/components/chat/ChatMessageList.native';
import AIInputDock,{type NativeAIInputDockHandle} from '../../app/_dream/components/chat/AIInputDock.native';
import DeckChatSelector,{type DeckAgentSelection} from '../../app/_dream/components/deck/DeckChatSelector.native';
import {buildDefaultLandingQuickActions} from '../../app/_dream/components/chat/chatLandingActions';
import InkLabel from '../../src/components/InkLabel.native';
import {inkColors} from '../../src/components/inkColors';
const now=Date.now();
let rows:ChatHistoryThread[]=Array.from({length:45},(_,index)=>({id:`fixture-history-${index}`,title:`Conversation ${index}`,created_at:new Date(now-index*1000).toISOString(),updated_at:new Date(now-index*1000).toISOString()}));
const messages=new Map<string,UIMessage[]>();let created=0,lastChoice='none',lastInputReceipt='no input';
const expectedLongDraft='Long draft text for viewport parity. '.repeat(20)+'A';
// Controlled Markdown/process samples exercise the production renderer on Hermes.
const richFixtureText=[
  '## Stored reply',
  '**Bold text** and *emphasis*, 中文🙂.',
  '1. First item\n2. Second item\n   - Nested item',
  '- [x] Finished task\n- [ ] Open task',
  '> Quoted text',
  '| Column A | Column B |\n| --- | --- |\n| Cell A | Cell B |',
  '`inline code`',
  '```js\nconst value = 1;\n```',
  'End of stored reply.',
].join('\n\n');
const historyMetadata={turnId:'fixture-history-turn',turnStatus:'completed',finalPartIndex:1,durationMs:1200};
function savedFixture(id:string,title:string):UIMessage[]{
  if(id==='fixture-history-39')return [{id:`${id}-saved`,role:'assistant',parts:[{type:'text',text:richFixtureText}],metadata:{...historyMetadata,historyProjectionVersion:1,historyProcessAvailable:true}} as UIMessage];
  if(id==='fixture-history-38')return Array.from({length:24},(_,index)=>({id:`${id}-${index}`,role:index%2?'assistant':'user',parts:[{type:'text',text:index===23?richFixtureText:(`Reading message ${index}. `).repeat(18)}]} as UIMessage));
  return [{id:`${id}-saved`,role:'assistant',parts:[{type:'text',text:`Saved reply for ${title}`}]} as UIMessage];
}

const decks=[{id:'fixture-writing',name:'Writing',enabled:true,voices:[{id:'fixture-writer',name:'Writer',enabled:true,icon:'brain',color:'purple'} as Voice]} as Deck];
// Native uses the installed fetch Response constructor; static Response.json belongs to newer browser implementations.
const json=(value:unknown)=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
async function transport(input:RequestInfo|URL,init:RequestInit={}) {
  const path=String(input),method=init.method ?? 'GET',query=new URLSearchParams(path.split('?')[1] ?? ''),pathname=path.split('?')[0];
  if(path==='/auth/session')return json({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)});
  if(pathname==='/api/claude-agent/threads' && method==='POST'){
    const id=`fixture-created-${++created}`,context=JSON.parse(String(init.body));rows=[{id,title:`New fixture ${created}`,created_at:new Date().toISOString(),updated_at:new Date().toISOString(),deck_id:context.deckId ?? null,voice_id:context.voiceId ?? null},...rows];return json({thread_id:id});
  }
  if(pathname==='/api/claude-agent/threads'){
    const search=query.get('query')?.toLowerCase(),offset=Number(query.get('offset') ?? 0),limit=Number(query.get('limit') ?? rows.length);
    const filtered=rows.filter(row=>!search || row.title?.toLowerCase().includes(search));return json({threads:filtered.slice(offset,offset+limit).map(row=>search?{...row,match:{strategy:'fuzzy',score:1,fields:['title'],excerpt:'Matched original history API fixture'}}:row)});
  }
  if(pathname==='/api/claude-agent/threads/fixture-history-39/messages/fixture-history-39-saved/process'){
    if(init.signal?.aborted)throw new Error('Fixture process read aborted');
    return json({id:'fixture-history-39-saved',role:'assistant',parts:[{type:'reasoning',text:'Canonical stored reasoning. 中文思考。'},{type:'text',text:richFixtureText}],metadata:historyMetadata,created_at:new Date(now).toISOString()});
  }
  const match=/^\/api\/claude-agent\/threads\/([^/]+)(?:\/(messages|status|inputs))?$/.exec(pathname);
  if(match){
    const id=decodeURIComponent(match[1]),thread=rows.find(row=>row.id===id);if(!thread)return new Response(null,{status:404});
    if(method==='DELETE'){rows=rows.filter(row=>row.id!==id);messages.delete(id);return json({ok:true});}
    if(match[2]==='messages'){const saved=messages.get(id) ?? savedFixture(id,thread.title ?? 'Conversation');return json({thread,messages:saved.map(message=>({...message,created_at:thread.updated_at})),has_more:false,next_cursor:null,latest_message_id:saved.at(-1)?.id ?? null,unchanged:false});}
    if(match[2]==='status')return json({running:false,lifecycle:'idle',turn_count:1,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
    if(match[2]==='inputs')return json({entries:[],local_owner:false});
  }
  throw new Error('Unexpected native page fixture request');
}
const frame=(event:Record<string,unknown>)=>`data: ${JSON.stringify(event)}\n\n`;
async function stream(path:string,init:RequestInit={}) {
  if(path!=='/api/claude-agent' || init.method!=='POST')throw new Error('Unexpected fixture stream');
  const request=JSON.parse(String(init.body)),turnId=`fixture-turn-${created}`,text='Fixture reply through the original SSE reducer';lastChoice=request.toolChoice;
  const submitted=(request.message as UIMessage).parts.filter(part=>part.type==='text').map(part=>part.text).join('');
  lastInputReceipt=`chars=${submitted.length} · longExact=${submitted===expectedLongDraft}`;
  let release=()=>{};const eof=new Promise<void>(resolve=>{release=resolve;});
  return {status:200,cancel(){release();},chunks:(async function*(){yield frame({type:'message-metadata',turnId});yield frame({type:'text-delta',delta:text});messages.set(request.id,[...(messages.get(request.id) ?? []),request.message,{id:`fixture-assistant-${created}`,role:'assistant',parts:[{type:'text',text}],metadata:{turnId,turnStatus:'completed'}}]);yield frame({type:'finish',finishReason:'stop'});await eof;})()};
}
function PageFixture(){
  const {t}=useTranslation(),colors=inkColors('system',useColorScheme()==='dark');
  const [selection,setSelection]=useState<DeckAgentSelection>(),[navigation,setNavigation]=useState(0),[notice,setNotice]=useState('fixture');const composer=useRef<NativeAIInputDockHandle>(null);
  const session=useNativeChatThread({context:{deckId:selection?.deckId,voiceId:selection?.agentId,imFullAccessEnabled:false,currentToolChoice:'manual'},transport,stream});
  const history=useNativeChatHistory({enabled:!session.threadId,transport});
  const reset=()=>{session.newChat();setNavigation(value=>value+1);};
  return <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
    <View style={styles.header}><InkLabel style={{color:colors['color-text-primary'],fontSize:18}}>Ink &amp; Memory</InkLabel><Pressable accessibilityRole="button" accessibilityLabel="New fixture chat" style={styles.button} onPress={reset}><InkLabel style={{color:colors['color-text-secondary']}}>＋ New</InkLabel></Pressable></View>
    <ChatPage hasConversation={Boolean(session.threadId)} history={history} activeThreadId={session.threadId} quickActions={buildDefaultLandingQuickActions(t)}
      onQuickAction={item=>{void session.send(item.prompt,[],'auto');}} onSelectThread={id=>{setNavigation(value=>value+1);void session.openThread(id);}} onDeleteThread={id=>{void history.remove(id);}}
      composer={<AIInputDock key={navigation} ref={composer} origin="http://[::1]:5173" workspaceEnabled={false} fullAccessEnabled={false} defaultToolChoice="manual" loading={session.running || session.posting}
        disabled={session.unknown} onSendMessage={session.send} onStop={session.threadId?session.stop:undefined} stopPending={session.stopping} onOpenSketch={()=>setNotice('sketch callback only')}
        contextControl={!session.threadId?<DeckChatSelector decks={decks} selectedAgentId={selection?.agentId} onChange={setSelection}/>:undefined} />}
      conversation={<ChatMessageList messages={session.messages} threadId={session.threadId ?? ''} isLoading={session.running || session.posting} initialLoading={session.recovering}
        historicalMessageIds={session.historicalMessageIds} origin="http://[::1]:5173" transport={transport} />}/>
    <View style={styles.footer}><Text style={{color:colors['color-text-secondary']}}>{`Fixture only · ${session.threadId ?? 'home'} · ${lastChoice} · ${lastInputReceipt} · ${notice}`}</Text></View>
  </SafeAreaView>;
}
function Boot(){const [ready,setReady]=useState(false);useEffect(()=>{void loadBrowserSession(transport).then(()=>setReady(true));},[]);return ready?<PageFixture/>:<Text>Preparing public fixture</Text>;}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{minHeight:48,paddingHorizontal:12,flexDirection:'row',alignItems:'center',justifyContent:'space-between'},button:{minHeight:44,paddingHorizontal:12,justifyContent:'center'},footer:{minHeight:48,justifyContent:'center',paddingHorizontal:12}});
AppRegistry.registerComponent('InkMemory',()=>Boot);
