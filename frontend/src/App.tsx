// [Sync] 2026-10-29: adopt complete native Settings/Work resources and the Writing Calendar resources intent; retain the App-owned runtime and Chat.
// [Sync] 2026-10-29: adopt the one-page five-item More navigator; keep Chat mounted and isolate normal account instances.
// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-29: expose original model settings from More; retain its drafts and refresh the existing App configuration after saves.
// [Sync] 2026-10-29: connect native Deck maintenance to the same App-owned catalog and original authenticated HTTP.
// [Sync] 2026-10-29: connect original Deck launcher/preview to Chat selection and draft prefill; tabs retain the composer instance.
// [Sync] 2026-10-29: restore original Deck/Agent toolbar context and same-Deck next-turn selection; catalog retry retains the pending choice.
// [Sync] 2026-10-28: retry native configuration/catalog reads without resetting the conversation or restarting the runtime.
// [Sync] 2026-10-28: wire original More/workspace/share actions, persistent file sidebar and native-owned long-image export.
// [Sync] 2026-10-28: connect bound Workspace URI previews, native binary export and explicit material copies to the original composer.
// [Sync] 2026-10-28: connect original activity/history and read-only scheduled detail with local HTTP and persistent underlying composer.
// [Sync] 2026-10-28: replace the temporary text-only FlatList with native Markdown, historical process and original bottom-follow presentation.
// [Sync] 2026-10-28: allow composer slot wrappers to shrink with the keyboard-adjusted native viewport.
// [Input] Original BFF session, Thread/message DTOs, SSE projection and Stop ownership.
// [Output] App-level real Chat context, queue, confirmation and recovery wiring; visual parity remains unaccepted.
// [Pos] RN business composition with original Chat landing order; full application parity remains unaccepted.
// [Sync] 2026-10-28: wire original queue editing/recovery and independent side-chat composition; keep the source conversation mounted.
// [Sync] 2026-10-28: keep one composer across landing/conversation layout; reuse original history, search, quick actions and pagination APIs.
// [Sync] 2026-10-28: wire the full native composer, original rich editor and persistent sketch leaf; complete page parity remains pending.
// [Sync] 2026-10-28: replace the fixed-auto prototype transport with canonical native Chat lifecycle and server configuration.
// [Sync] 2026-10-28: SwiftUI supplies the iOS keyboard viewport; disable duplicate RN keyboard avoidance.
import {useEffect, useMemo, useRef, useState} from 'react';
import {KeyboardAvoidingView, Keyboard, Linking, Modal, Platform, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View} from 'react-native';
import {isToolUIPart} from 'ai';
import {useTranslation} from 'react-i18next';
import type {ToolChoice} from '../app/_dream/lib/chat-schema';
import type {Deck,Voice} from '../app/_dream/api/voiceApi';
import {getDeck} from '../app/_dream/api/deckReadApi';
import useNativeChatSetup,{type NativeChatConfig} from '../app/_dream/components/chat/useNativeChatSetup.native';
import DeckChatSelector,{type DeckAgentSelection} from '../app/_dream/components/deck/DeckChatSelector.native';
import useNativeChatThread from '../app/_dream/components/chat/useNativeChatThread.native';
import ToolConfirmationDock from '../app/_dream/components/chat/ToolConfirmationDock.native';
import ChatPage from '../app/_dream/components/chat/ChatPage.native';
import ActivitySidebar,{nativeActivityFilters} from '../app/_dream/components/chat/ActivitySidebar.native';
import useNativeActivitySidebarData from '../app/_dream/components/chat/useNativeActivitySidebarData.native';
import ScheduledTaskDetailSidebar from '../app/_dream/components/chat/ScheduledTaskDetailSidebar.native';
import ChatHistorySearch from '../app/_dream/components/chat/ChatHistorySearch.native';
import WorkspaceFilePreview from '../app/_dream/components/chat/WorkspaceFilePreview.native';
import {createWorkspaceResources} from './platform/workspaceFiles.native';
import {releaseNativeFiles,type NativePickedFile} from './platform/fileUpload.native';
import ChatTopActions from '../app/_dream/components/chat/ChatTopActions.native';
import PluginReceiptBadge,{ChatAgentBadge} from '../app/_dream/components/chat/PluginReceiptBadge.native';
import ChatShareSurface,{type NativeChatShareHandle} from '../app/_dream/components/chat/ChatShareSurface.native';
import FileSidebar from '../app/_dream/components/dashboard/FileSidebar.native';
import type {ScheduledTaskMarkerSnapshot} from '../app/_dream/components/chat/scheduledTaskMarkerModel';
import ChatMessageList from '../app/_dream/components/chat/ChatMessageList.native';
import useNativeChatHistory from '../app/_dream/components/chat/useNativeChatHistory.native';
import {buildDefaultLandingQuickActions} from '../app/_dream/components/chat/chatLandingActions';
import {chatMainTurnCanStop} from '../app/_dream/components/chat/chatRuntimeState';
import AIInputDock,{type NativeAIInputDockHandle} from '../app/_dream/components/chat/AIInputDock.native';
import ThreadInputQueueCard from '../app/_dream/components/chat/ThreadInputQueueCard.native';
import {isThreadInputQueueCard,type ThreadInputEntry} from '../app/_dream/components/chat/threadInputQueue';
import InkLabel from './components/InkLabel.native';
import DeckManager from '../app/_dream/components/DeckManager.native';
import StoryWorkspaceSettingsPage,{type NativeSettingsNavigation} from '../app/_dream/views/story-workspace/StoryWorkspaceSettingsPage.native';
import MoreNavigator from '../app/_dream/components/story-workspace/layout/MoreNavigator.native';
import useInkColors from './components/useInkColors.native';
import SketchInputSurface from '../app/_dream/components/chat/SketchInputSurface.native';
import {resolveToolName} from '../app/_dream/components/chat/toolConfirmation';
import {summarizeToolInvocation} from '../app/_dream/components/chat/toolInputSummary';
import SessionGate from './platform/SessionGate';
import ScreenFrame from './components/ScreenFrame';
import {clientFetch} from './platform/transport';

function Business({ownerId,logout,refreshSession,initialThreadId,onClose,initialNotice}: {ownerId:string;logout: () => Promise<void>;refreshSession:()=>Promise<void>;initialThreadId?:string;onClose?:()=>void;initialNotice?:string}) {
  const {t}=useTranslation();
  const composer=useRef<NativeAIInputDockHandle>(null),share=useRef<NativeChatShareHandle>(null);
  const [fileSidebarOpen,setFileSidebarOpen]=useState(false);
  const [sketchOpen,setSketchOpen]=useState(false),[composerKey,setComposerKey]=useState(0);
  const setup=useNativeChatSetup({onSessionExpired:()=>void refreshSession()});
  const {origin,decks,configLoaded}=setup;
  const config:Partial<NativeChatConfig>=setup.config ?? {};
  const [contextReadError,setContextReadError]=useState('');
  const [error, setError] = useState(initialNotice ?? '');
  const [workspaceUri,setWorkspaceUri]=useState<string|null>(null);
  const refreshOwner=useRef(refreshSession);refreshOwner.current=refreshSession;
  const fileResources=useMemo(()=>createWorkspaceResources(undefined,()=>void refreshOwner.current()),[]);
  const [activityOpen,setActivityOpen]=useState(false),[activityFilters,setActivityFilters]=useState(nativeActivityFilters),[scheduledDetail,setScheduledDetail]=useState<{taskId:string;snapshot?:ScheduledTaskMarkerSnapshot|null}|null>(null);
  const activity=useNativeActivitySidebarData(activityOpen,{onSessionExpired:()=>void refreshSession()});
  const [sideChat,setSideChat]=useState<{threadId:string;notice?:string}|null>(null);
  const [section, setSection] = useState<'chat' | 'decks' | 'more'>('chat');
  const [moreVisited,setMoreVisited]=useState(false),[moreNonce,setMoreNonce]=useState(0),moreSource=useRef<'chat'|'decks'>('chat');
  const [settingsNavigation,setSettingsNavigation]=useState<NativeSettingsNavigation>({nonce:0,target:'menu'});
  const [selection,setSelection] = useState<DeckAgentSelection>();
  const [deckPrefill,setDeckPrefill]=useState<{text:string;nonce:number}>();
  const [toolChoice,setToolChoice] = useState<ToolChoice>('auto');
  const [boundDeck,setBoundDeck] = useState<Deck>();
  const [boundContext,setBoundContext] = useState<{threadId?:string;deckId?:string;voiceId?:string}>({});
  const legacyContext=boundContext.threadId?decks.flatMap(deck=>(deck.voices ?? []).map(voice=>({deck,voice}))).find(({voice})=>voice.thread_id===boundContext.threadId):undefined;
  const selectedDeck = boundContext.threadId?(boundDeck ?? (boundContext.deckId?undefined:legacyContext?.deck)):decks.find(deck=>deck.id===selection?.deckId);
  const selectedVoice = selectedDeck?.voices?.find(voice=>voice.id===(boundContext.threadId?boundContext.voiceId:selection?.agentId)) ?? legacyContext?.voice;
  const session = useNativeChatThread({context:{deckId:boundContext.threadId?boundContext.deckId:selection?.deckId,voiceId:boundContext.threadId?boundContext.voiceId:selection?.agentId,
    voiceSystemPrompt:selectedVoice?.system_prompt,settingsSystemPrompt:config.system_prompt,imFullAccessEnabled:config.im_full_access_enabled===true,currentToolChoice:toolChoice},onSettled:()=>void history.reload(),onSessionExpired:()=>void refreshSession()});
  const history=useNativeChatHistory({enabled:section==='chat' && (!session.threadId || activityOpen),onSessionExpired:()=>void refreshSession()});
  const thread=session.threadId,messages=session.messages,running=session.running || session.posting || session.recovering,stopping=session.stopping,
    uncertain=!configLoaded || session.unknown || (session.recovering && !session.thread) || Boolean(session.thread?.deck_id && boundDeck?.id!==session.thread.deck_id);
  const canStop=chatMainTurnCanStop(session.posting?'submitted':'ready',session.running,false) || stopping;
  const colors=useInkColors();
  const foreground=colors['color-text-primary'];
  const visibleThread=useRef(thread);visibleThread.current=thread;
  useEffect(()=>{if(initialThreadId)void session.openThread(initialThreadId);},[initialThreadId]);
  useEffect(()=>{
    const record=session.thread;
    setBoundContext(record?{threadId:record.id,deckId:record.deck_id ?? undefined,voiceId:record.voice_id ?? undefined}:{});
  },[session.thread?.id,session.thread?.deck_id,session.thread?.voice_id]);
  useEffect(()=>{
    const record=session.thread;
    setContextReadError('');
    if(!record?.deck_id){setBoundDeck(undefined);return;}
    setBoundDeck(undefined);let active=true;void getDeck(record.deck_id,clientFetch).then(deck=>{if(active)setBoundDeck(deck);}).catch(()=>{if(active)setContextReadError('Agent上下文暂时无法读取，请重试读取对话。');});
    return()=>{active=false;};
  },[session.thread?.id,session.thread?.deck_id,setup.revision]);
  const selectThread=(id:string)=>{setWorkspaceUri(null);setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setSketchOpen(false);setComposerKey(value=>value+1);return session.openThread(id);};
  const deleteThread=(id:string)=>{void history.remove(id).then(removed=>{if(!removed)return;activity.removeChat(id);if(id===session.threadId){session.newChat();setComposerKey(value=>value+1);setSketchOpen(false);}});};
  const workspaceAvailability=!configLoaded?'loading':config.workspace_enabled===false?'disabled':'enabled';
  const openWorkspace=(uri:string)=>{setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setWorkspaceUri(uri);};
  const addWorkspaceImage=async(file:NativePickedFile)=>{if(!composer.current||visibleThread.current!==thread){releaseNativeFiles([file.id]);return false;}return composer.current.addFile(file);};
  const newChat=()=>{session.newChat();setBoundContext({});setBoundDeck(undefined);setDeckPrefill(undefined);setError('');setSketchOpen(false);setWorkspaceUri(null);setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setComposerKey(value=>value+1);};
  const openSection=(value:'chat'|'decks'|'more')=>{if(value==='more'){if(section!=='more')moreSource.current=section;setMoreVisited(true);setMoreNonce(n=>n+1);}Keyboard.dismiss();setSketchOpen(false);setWorkspaceUri(null);setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setSection(value);};
  const tryDeck=(deck:Deck,voice:Voice,input?:string)=>{if(deck.agent_type==='dream')return;newChat();setSelection({deckId:deck.id,agentId:voice.id});setDeckPrefill({text:input ?? '',nonce:composerKey+1});openSection('chat');};
  const toggleActivity=()=>{Keyboard.dismiss();setFileSidebarOpen(false);setWorkspaceUri(null);setScheduledDetail(null);setSketchOpen(false);setActivityOpen(value=>!value);};
  const toggleWorkspace=()=>{Keyboard.dismiss();setActivityOpen(false);setWorkspaceUri(null);setScheduledDetail(null);setSketchOpen(false);setFileSidebarOpen(value=>!value);};
  useEffect(()=>{if(configLoaded&&config.workspace_enabled===false)setFileSidebarOpen(false);},[configLoaded,config.workspace_enabled]);
  const retryReads=()=>{setError('');setup.retry();if(session.error)void session.retry();else if(!setup.error&&!contextReadError)void history.reload();};
  const stop=()=>session.stop();
  const openSideChat=async(entry:ThreadInputEntry)=>{const task=await session.sideTask(entry);if(task&&visibleThread.current===entry.thread_id)setSideChat({threadId:task.thread_id,notice:task.error_code?t('chat.inputQueue.sideChatLaunchFailed'):undefined});};
  return <SafeAreaView style={styles.fill}><KeyboardAvoidingView style={styles.fill} accessibilityElementsHidden={activityOpen||fileSidebarOpen||scheduledDetail!==null} importantForAccessibility={activityOpen||fileSidebarOpen||scheduledDetail!==null?'no-hide-descendants':'auto'} enabled={Boolean(onClose) || Platform.OS !== 'ios'} behavior={onClose&&Platform.OS==='ios'?'padding':undefined}>
    <View style={[styles.header,section==='more'?styles.hidden:undefined]}>{section!=='chat'?<InkLabel style={[styles.title,{color:foreground}]}>Ink &amp; Memory</InkLabel>:null}<View style={styles.fill}/>
      {onClose?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputQueue.closeSideChat')} onPress={onClose} style={styles.action}><InkLabel style={{color:foreground}}>{t('chat.history.close')}</InkLabel></Pressable>:section==='chat'?<ChatTopActions creating={session.posting&&!thread} activityOpen={activityOpen} workspaceEnabled={configLoaded&&config.workspace_enabled!==false} workspaceOpen={fileSidebarOpen}
      contextBadge={selectedVoice && (!thread || boundContext.threadId===thread)?<ChatAgentBadge voice={selectedVoice}/>:undefined}
      pluginReceipt={<PluginReceiptBadge threadId={thread??null} deck={!thread || boundContext.threadId===thread?selectedDeck:undefined} activeVoiceId={selectedVoice?.id} activeVoiceName={selectedVoice?.name} onSessionExpired={()=>void refreshSession()}
        onSelectAgent={thread?voiceId=>{if(!selectedDeck?.voices?.some(voice=>voice.enabled && voice.id===voiceId))return;setBoundContext(current=>current.threadId===thread?{...current,voiceId}:current);}:undefined}/>}
        onNewChat={newChat} onToggleActivity={toggleActivity} onToggleWorkspace={toggleWorkspace} onShare={()=>{setActivityOpen(false);setFileSidebarOpen(false);setScheduledDetail(null);setWorkspaceUri(null);setSketchOpen(false);share.current?.open();}}/>:null}</View>
    {error || setup.error || contextReadError || session.error ? <View><Text accessibilityRole="alert" style={[styles.error,{color:foreground}]}>{error || setup.error || contextReadError || '会话状态待核对，请重试读取。'}</Text><Pressable accessibilityRole="button" disabled={Boolean(setup.error)&&setup.loading} style={styles.action} onPress={retryReads}><Text style={{color:foreground}}>{setup.loading?'正在读取…':'重试读取'}</Text></Pressable></View> : null}
    <View style={[styles.fill,section!=='chat'?styles.hidden:undefined]} accessibilityElementsHidden={section!=='chat'} importantForAccessibility={section==='chat'?'auto':'no-hide-descendants'}><ChatPage showSearch={false} hasConversation={Boolean(thread)} history={history} activeThreadId={thread}
      quickActions={buildDefaultLandingQuickActions(t)} quickActionsDisabled={!configLoaded} onSelectThread={id=>void selectThread(id)}
      onDeleteThread={deleteThread}
      onQuickAction={item=>{void session.send(item.prompt,[],'auto').catch(()=>setError(t('chat.history.createFailed')));}}
      conversation={<ChatMessageList messages={messages} threadId={thread ?? ''} isLoading={session.running || session.posting} initialLoading={session.recovering}
        origin={origin} workspaceAvailability={workspaceAvailability} workspaceResources={fileResources} onOpenWorkspace={openWorkspace} onAddImageMaterial={addWorkspaceImage} historicalMessageIds={session.historicalMessageIds} historyHasMore={session.hasMore} historyLoading={session.loadingOlder}
        onLoadOlder={()=>void session.loadOlder()} onOpenLink={url=>{void Linking.openURL(new URL(url,origin).href).catch(()=>setError('链接暂时无法打开。'));}}
        renderOtherPart={part=><Text style={{color:foreground,fontSize:16}}>{isToolUIPart(part)?summarizeToolInvocation(resolveToolName(part),'input' in part?part.input:undefined)||resolveToolName(part):part.type==='file'?part.filename||part.mediaType:''}</Text>} />}
      composer={<View style={styles.shrink}>
      {session.queue.some(isThreadInputQueueCard)?<ScrollView accessibilityLabel={t('chat.inputQueue.region')} style={styles.queue} contentContainerStyle={{gap:4.8}} keyboardShouldPersistTaps="handled">
        {session.queue.filter(isThreadInputQueueCard).map(entry=><ThreadInputQueueCard key={entry.message_id} entry={entry} localOwner={session.localOwner} onGuide={session.guide} onCancel={session.cancelInput} onEdit={session.editInput} onSideChat={openSideChat}/>)}
      </ScrollView>:null}
      {session.queueError?<View accessibilityRole="alert" style={[styles.queueNotice,{borderColor:colors['color-border-paper']}]}><InkLabel style={{color:foreground}}>{t(session.queueError)}</InkLabel>
        {!['chat.inputQueue.accessDenied','chat.inputQueue.textOnly'].includes(session.queueError)?<Pressable accessibilityRole="button" disabled={session.queueChecking} onPress={()=>void session.checkQueue()} style={styles.action}><InkLabel style={{color:foreground}}>{t(session.queueChecking?'chat.inputQueue.checkingStatus':'chat.inputQueue.checkStatus')}</InkLabel></Pressable>:null}
      </View>:null}
      {session.editDraftRecovery?<View accessibilityLiveRegion="polite" style={[styles.queueNotice,{borderColor:colors['color-border-paper']}]}><InkLabel style={{color:foreground}}>{t('chat.inputQueue.editDraftSaved')}</InkLabel><InkLabel style={{color:foreground}}>{session.editDraftRecovery.text}</InkLabel>
        <Pressable accessibilityRole="button" disabled={session.editRetrying} onPress={()=>void session.retryEditedInput()} style={styles.action}><InkLabel style={{color:foreground}}>{t('chat.inputQueue.retryEdit')}</InkLabel></Pressable>
      </View>:null}
      {session.confirmation ? <ToolConfirmationDock key={session.confirmation.partKey} confirmation={session.confirmation} onConfirm={session.confirm} /> : null}
      {origin ? <View style={styles.shrink}>
        <AIInputDock key={composerKey} ref={composer} origin={origin} disabled={uncertain} loading={running}
          onSendMessage={(text,files,choice)=>{setToolChoice(choice ?? 'auto');return session.send(text,files,choice);}}
          fullAccessEnabled={config.im_full_access_enabled===true} defaultToolChoice={toolChoice} prefill={deckPrefill?.text} prefillNonce={deckPrefill?.nonce}
          onStop={thread && canStop?stop:undefined} stopPending={stopping} loadingLabel={t(session.recovering?'chat.historyTurn.loading':'chat.inputDock.generating')} onOpenSketch={()=>setSketchOpen(true)}
          deckId={boundContext.threadId?boundContext.deckId:selection?.deckId} threadId={thread ?? undefined}
          workspaceEnabled={configLoaded && config.workspace_enabled!==false} workspaceSessionId={configLoaded && config.workspace_enabled ? thread ?? undefined : undefined}
          contextControl={!thread?<DeckChatSelector decks={decks.filter(deck=>deck.enabled && deck.agent_type!=='dream')} selectedAgentId={selection?.agentId} onChange={setSelection} />:undefined} />
      </View>:null}
      </View>}
    /></View>
    <View style={[styles.fill,section!=='decks'?styles.hidden:undefined]} accessibilityElementsHidden={section!=='decks'} importantForAccessibility={section==='decks'?'auto':'no-hide-descendants'}>
      <DeckManager decks={decks} active={section==='decks'} loading={setup.loading} error={setup.error} onRefresh={setup.refreshDecks} onSessionExpired={()=>void refreshSession()}
        onTryDeck={tryDeck} />
    </View>
    <View style={[styles.fill,section!=='more'?styles.hidden:undefined]} accessibilityElementsHidden={section!=='more'} importantForAccessibility={section==='more'?'auto':'no-hide-descendants'}>
      {moreVisited?<MoreNavigator ownerId={ownerId} origin={origin} decks={decks} active={section==='more'} resetNonce={moreNonce} onClose={()=>openSection(moreSource.current)} onSessionExpired={()=>void refreshSession()}
        onOpenThread={id=>setSideChat({threadId:id})} onPrepareChat={input=>{newChat();setDeckPrefill({text:input,nonce:composerKey+1});openSection('chat');}}
        onSettingsOpen={()=>setSettingsNavigation(value=>({nonce:value.nonce+1,target:'menu'}))} onResources={()=>setSettingsNavigation(value=>({nonce:value.nonce+1,target:'resources'}))}
        renderSettings={(back,settingsActive)=><StoryWorkspaceSettingsPage ownerId={ownerId} origin={origin} active={settingsActive} navigation={settingsNavigation}
          decks={decks} loading={setup.loading} error={setup.error} onRefreshDecks={setup.refreshDecks} onTryDeck={tryDeck} onBack={back} logout={logout}
          onSessionExpired={()=>void refreshSession()} onConfigSaved={()=>void setup.refreshConfig().catch(()=>setError('配置暂时无法读取，请重试。'))}/>}/>:null}
    </View>
    {!onClose?<View accessibilityRole="tablist" style={styles.tabs}>{(['chat','decks','more'] as const).map(value => <Pressable key={value} accessibilityRole="tab" accessibilityState={{selected:section===value}} style={styles.action} onPress={() => openSection(value)}><InkLabel style={{color:foreground}}>{value==='chat'?t('nav.chat'):value==='decks'?t('nav.decks'):t('nav.more')}</InkLabel></Pressable>)}</View>:null}
  </KeyboardAvoidingView>
    {activityOpen?<View style={styles.overlay}><ActivitySidebar activity={activity} history={history} activeThreadId={thread} filters={activityFilters} onFiltersChange={setActivityFilters} onClose={()=>setActivityOpen(false)} onSelectThread={id=>void selectThread(id)} onDeleteThread={deleteThread} onTask={row=>{setActivityOpen(false);setScheduledDetail({taskId:row.id,snapshot:row.snapshot});}}/></View>:null}
    {scheduledDetail?<View style={styles.overlay}><ScheduledTaskDetailSidebar key={scheduledDetail.taskId} {...scheduledDetail} onSessionExpired={()=>void refreshSession()} onClose={()=>setScheduledDetail(null)} onOpenThread={id=>void selectThread(id)}/></View>:null}
    <View pointerEvents={fileSidebarOpen?'auto':'none'} style={fileSidebarOpen?styles.overlay:undefined}><FileSidebar sessionId={thread??undefined} open={fileSidebarOpen} availability={workspaceAvailability} resources={fileResources} onSessionExpired={()=>void refreshSession()} onClose={()=>setFileSidebarOpen(false)}/></View>
    <ChatShareSurface ref={share} origin={origin} threadId={thread} title={session.thread?.title??history.threads.find(row=>row.id===thread)?.title??t('chat.history.fallbackTitle')} availability={workspaceAvailability} resources={fileResources} onSessionExpired={()=>void refreshSession()}
      snapshot={()=>({messages,pendingConfirmation:session.confirmation??null,toolChoice})}/>
    <ChatHistorySearch history={history} activeThreadId={thread} onSelect={id=>void selectThread(id)}/>
    {workspaceUri?<WorkspaceFilePreview key={thread??'no-thread'} uri={workspaceUri} threadId={thread??undefined} availability={workspaceAvailability} resources={fileResources} onClose={()=>setWorkspaceUri(null)} onOpenWorkspace={openWorkspace} onOpenLink={url=>{void Linking.openURL(new URL(url,origin).href).catch(()=>setError('链接暂时无法打开。'));}} onAddImageMaterial={addWorkspaceImage}/>:null}
    {origin && section==='chat'?<SketchInputSurface key={composerKey} origin={origin} open={sketchOpen} disabled={uncertain} onClose={()=>setSketchOpen(false)} onAdd={file=>composer.current?.addFile(file) ?? Promise.resolve(false)} />:null}
    <Modal visible={sideChat!==null} animationType="slide" presentationStyle="pageSheet" onRequestClose={()=>setSideChat(null)} supportedOrientations={['portrait','landscape']}>
      {sideChat?<ScreenFrame><Business key={sideChat.threadId} ownerId={ownerId} logout={logout} refreshSession={refreshSession} initialThreadId={sideChat.threadId} initialNotice={sideChat.notice} onClose={()=>setSideChat(null)}/></ScreenFrame>:null}
    </Modal>
  </SafeAreaView>;
}
export default function App() { return <ScreenFrame><SessionGate>{(logout,refreshSession,user) => <Business key={user.id} ownerId={user.id} logout={logout} refreshSession={refreshSession} />}</SessionGate></ScreenFrame>; }
const styles = StyleSheet.create({
  hidden:{display:'none'},
  overlay:{...StyleSheet.absoluteFillObject,zIndex:10},toolbarAction:{width:44,height:44,alignItems:'center',justifyContent:'center'},newAction:{minHeight:44,flexDirection:'row',alignItems:'center',gap:5.6,paddingHorizontal:8.8},shrink:{flexShrink:1,minHeight:0},fill:{flex:1},queue:{maxHeight:192,flexShrink:1},queueNotice:{padding:8,gap:4,borderWidth:StyleSheet.hairlineWidth,borderRadius:12},header:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',padding:12},title:{fontSize:22},action:{padding:16,minHeight:48},message:{padding:16,gap:8},error:{padding:12},composer:{flexDirection:'row',alignItems:'flex-end',padding:10,borderTopWidth:StyleSheet.hairlineWidth,borderColor:'#9c8e7c'},input:{flex:1,minHeight:48,maxHeight:180,padding:12,fontSize:16},tabs:{flexDirection:'row',justifyContent:'space-around'}});
