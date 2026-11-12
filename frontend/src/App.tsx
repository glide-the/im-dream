// [Sync] 2026-11-12: open a managed share's original Chat or Writing entity through the existing native navigation.
import {clientFetch as shareSourceFetch} from './platform/transport';
// [Sync] 2026-11-04: show same-conversation preparation in the existing native composer area.
// [Sync] 2026-11-03: retain business views behind an idle clock and share native account Thread presence.
// [Sync] 2026-11-03: pause hidden Chat UI publication while its live Thread readers remain account-owned.
// [Sync] 2026-11-03: retain the current Thread composer on reselection and discard previews after confirmed deletion.
// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Sync] 2026-11-02: restore one main-owned side Chat; retain Writing source identity until its original editor reopens.
// [Sync] 2026-11-02: bind native Chat restoration to the validated account and each primary/side Thread input owner.
// [Sync] 2026-11-02: confirm the named Chat before deletion; retain one request and recheck the visible Thread after asynchronous cleanup.
// [Sync] 2026-11-01: hand all Chat, Plan, file and workspace external links to the shared native system-browser action.
// [Sync] 2026-11-01: Writing side Chat retains its source Session binding and prepares saved context before native sends.
// [Sync] 2026-10-31: hidden Chat scenes and covering panels release local editor focus while retaining their composer.
// [Sync] 2026-10-31: await scoped MCP document closure before Thread/new Chat/side view changes; SessionGate owns account departure.
// [Sync] 2026-10-30: adopt original task activity sections and source-thread navigation without replacing Chat/runtime owners.
// [Sync] 2026-10-30: adopt original tool/file results and persistent MCP App/editor leaves; preserve message DTOs and route editor jumps to Writing.
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
import { BRAND_NAME } from '../app/_dream/constants/brand';
import {useEffect, useMemo, useRef, useState} from 'react';
import {Alert, KeyboardAvoidingView, Keyboard, Modal, Platform, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View} from 'react-native';
import {openExternalLink} from './platform/externalLinks.native';
import {isToolUIPart} from 'ai';
import {useTranslation} from 'react-i18next';
import type {ToolChoice} from '../app/_dream/lib/chat-schema';
import type {Deck,Voice} from '../app/_dream/api/voiceApi';
import {getDeck} from '../app/_dream/api/deckReadApi';
import useNativeChatSetup,{type NativeChatConfig} from '../app/_dream/components/chat/useNativeChatSetup.native';
import DeckChatSelector,{type DeckAgentSelection} from '../app/_dream/components/deck/DeckChatSelector.native';
import useNativeChatThread from '../app/_dream/components/chat/useNativeChatThread.native';
import {createNativeChatRecovery} from '../app/_dream/components/chat/nativeChatRecovery.native';
import ToolConfirmationDock from '../app/_dream/components/chat/ToolConfirmationDock.native';
import ChatPage from '../app/_dream/components/chat/ChatPage.native';
import ActivitySidebar,{nativeActivityFilters} from '../app/_dream/components/chat/ActivitySidebar.native';
import useNativeActivitySidebarData from '../app/_dream/components/chat/useNativeActivitySidebarData.native';
import ScheduledTaskDetailSidebar from '../app/_dream/components/chat/ScheduledTaskDetailSidebar.native';
import ChatHistorySearch from '../app/_dream/components/chat/ChatHistorySearch.native';
import WorkspaceFilePreview from '../app/_dream/components/chat/WorkspaceFilePreview.native';
import {createWorkspaceResources,createMessageFileResources} from './platform/workspaceFiles.native';
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
import ToolMessagePart from '../app/_dream/components/chat/ToolMessagePart.native';
import FileMessagePart from '../app/_dream/components/chat/FileMessagePart.native';
import PlanButton from '../app/_dream/components/chat/PlanPanel.native';
import {closeToolResultDocuments} from '../app/_dream/components/chat/ToolResultSurface.native';
import useNativeTaskActivity from '../app/_dream/components/chat/useNativeTaskActivity.native';
import type {EditorJumpToCellDetail} from '../app/_dream/components/chat/editorWriteTools';
import SessionGate from './platform/SessionGate';
import ScreenFrame from './components/ScreenFrame';
import {clientFetch} from './platform/transport';
import type {WritingThreadContext} from '../app/_dream/components/Editor/WritingDocument.protocol';
import useIdleScreenSaver from './components/useIdleScreenSaver.native';
import IdleScreenSaver from './components/IdleScreenSaver.native';

function Business({ownerId,logout,refreshSession,initialThreadId,onClose,initialNotice,documentOwner,writingContext,onReturnToWriting,onRecoveryDeparture}: {documentOwner?:object;writingContext?:WritingThreadContext;ownerId:string;logout: () => Promise<void>;refreshSession:()=>Promise<void>;initialThreadId?:string;onClose?:()=>void;initialNotice?:string;onReturnToWriting?:()=>Promise<void>;onRecoveryDeparture?:()=>void}) {
  const {t}=useTranslation();
  const recovery=useMemo(()=>createNativeChatRecovery(ownerId,initialThreadId),[ownerId,initialThreadId]);
  const composer=useRef<NativeAIInputDockHandle>(null),share=useRef<NativeChatShareHandle>(null);
  const [fileSidebarOpen,setFileSidebarOpen]=useState(false);
  const [sketchOpen,setSketchOpen]=useState(false),[composerKey,setComposerKey]=useState(0);
  const setup=useNativeChatSetup({onSessionExpired:()=>void refreshSession()});
  const {origin,decks,configLoaded}=setup;
  const config:Partial<NativeChatConfig>=setup.config ?? {};
  const [contextReadError,setContextReadError]=useState('');
  const [saverVisible,setSaverVisible]=useState(false);
  const [error, setError] = useState(initialNotice ?? '');
  const toolDocumentOwner=useMemo(()=>documentOwner??{},[documentOwner]);
  const [workspaceUri,setWorkspaceUri]=useState<string|null>(null);
  const refreshOwner=useRef(refreshSession);refreshOwner.current=refreshSession;
  const fileResources=useMemo(()=>createWorkspaceResources(undefined,()=>void refreshOwner.current()),[]);
  const messageFiles=useMemo(()=>createMessageFileResources(undefined,()=>void refreshOwner.current()),[]);
  const editorJumpNonce=useRef(0);
  const [editorJump,setEditorJump]=useState<{nonce:number;detail:EditorJumpToCellDetail}>();
  const [activityOpen,setActivityOpen]=useState(false),[activityFilters,setActivityFilters]=useState(nativeActivityFilters),[scheduledDetail,setScheduledDetail]=useState<{taskId:string;snapshot?:ScheduledTaskMarkerSnapshot|null}|null>(null);
  const activity=useNativeActivitySidebarData(activityOpen,{onSessionExpired:()=>void refreshSession()});
  const [sideChat,setSideChat]=useState<{threadId:string;notice?:string;documentOwner:object;writingContext?:WritingThreadContext;restoredWritingSessionId?:string}|null>(()=>{
    const saved=recovery.readSideChat();if(!saved)return null;
    return {threadId:saved.threadId,documentOwner:{},...(saved.writingSessionId?{restoredWritingSessionId:saved.writingSessionId,
      writingContext:{sessionId:saved.writingSessionId,prepareEditorState:async()=>{throw Error('WRITING_CONTEXT_UNAVAILABLE');}}}: {})};
  });
  const currentSideChat=useRef(sideChat);currentSideChat.current=sideChat;
  useEffect(()=>()=>{currentSideChat.current=null;},[]);
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
  const session = useNativeChatThread({recovery,initialThreadId,visible:section==='chat'&&sideChat===null&&!saverVisible,context:{deckId:boundContext.threadId?boundContext.deckId:selection?.deckId,voiceId:boundContext.threadId?boundContext.voiceId:selection?.agentId,
    voiceSystemPrompt:selectedVoice?.system_prompt,settingsSystemPrompt:config.system_prompt,imFullAccessEnabled:config.im_full_access_enabled===true,currentToolChoice:toolChoice},
    prepareEditorState:writingContext?async(id,signal)=>{
      if(id!==initialThreadId)return undefined;
      setError('');
      try{return await writingContext.prepareEditorState(signal);}
      catch(error){if(!signal.aborted)setError(t('chat.writingContextUnavailable'));throw error;}
    }:undefined,onSettled:()=>void history.reload(),onSessionExpired:()=>void refreshSession()});
  const history=useNativeChatHistory({enabled:section==='chat' && (!session.threadId || activityOpen),onSessionExpired:()=>void refreshSession()});
  const writingRecoveryBlocked=Boolean(onReturnToWriting&&session.threadId===initialThreadId);
  const thread=session.threadId,messages=session.messages,running=session.running || session.posting || session.recovering,stopping=session.stopping,
    uncertain=!configLoaded || session.unknown || (session.recovering && !session.thread) || Boolean(session.thread?.deck_id && boundDeck?.id!==session.thread.deck_id);
  const canStop=chatMainTurnCanStop(session.posting?'submitted':'ready',session.running,false) || stopping;
  const colors=useInkColors();
  const foreground=colors['color-text-primary'];
  const taskActivity=useNativeTaskActivity(thread,{active:section==='chat'&&sideChat===null,running:session.running||session.posting,onSessionExpired:()=>void refreshSession()});
  const visibleThread=useRef(thread);visibleThread.current=thread;
  useEffect(()=>{if(initialThreadId&&thread!==initialThreadId)onRecoveryDeparture?.();},[thread,initialThreadId,onRecoveryDeparture]);
  const deleteRequest=useRef<object|null>(null);
  useEffect(()=>()=>{deleteRequest.current=null;},[]);
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
  const selectThread=async(id:string)=>{if(id===session.threadId&&!session.unknown){setActivityOpen(false);setScheduledDetail(null);return;}await closeToolResultDocuments(toolDocumentOwner);setWorkspaceUri(null);setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setSketchOpen(false);setComposerKey(value=>value+1);return session.openThread(id);};
  const deleteThread=(id:string,displayTitle?:string)=>{
    if(deleteRequest.current)return;
    const row=history.threads.find(item=>item.id===id)??activity.chat.data.find(item=>item.id===id);
    const savedDate=row?new Date(row.created_at):null;
    const title=displayTitle?.trim()||row?.title?.trim()||row?.match?.excerpt?.trim()||(id===thread?session.thread?.title?.trim():undefined)||`${t('chat.history.fallbackTitle')}${savedDate&&Number.isFinite(savedDate.getTime())?` · ${savedDate.toLocaleString()}`:''}`;
    const request={};deleteRequest.current=request;let confirmed=false;
    const cancel=()=>{if(!confirmed&&deleteRequest.current===request)deleteRequest.current=null;};
    Alert.alert(t('chat.history.deleteThread'),t('deck.related.confirmDelete',{title}),[
      {text:t('deck.details.cancel'),style:'cancel',onPress:cancel},
      {text:t('deck.related.delete'),style:'destructive',onPress:()=>{
        if(confirmed||deleteRequest.current!==request)return;confirmed=true;
        void history.remove(id).then(async removed=>{
          if(!removed||deleteRequest.current!==request)return;
          session.invalidateHistory(id);
          activity.removeChat(id);
          if(id===visibleThread.current){await closeToolResultDocuments(toolDocumentOwner);if(id!==visibleThread.current||deleteRequest.current!==request)return;session.newChat();setComposerKey(value=>value+1);setSketchOpen(false);}
        }).finally(()=>{if(deleteRequest.current===request)deleteRequest.current=null;});
      }},
    ],{cancelable:true,onDismiss:cancel});
  };
  const workspaceAvailability=!configLoaded?'loading':config.workspace_enabled===false?'disabled':'enabled';
  const openWorkspace=(uri:string)=>{setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setWorkspaceUri(uri);};
  const addWorkspaceImage=async(file:NativePickedFile)=>{if(!composer.current||visibleThread.current!==thread){releaseNativeFiles([file.id]);return false;}return composer.current.addFile(file);};
  const newChat=async()=>{await closeToolResultDocuments(toolDocumentOwner);session.newChat();setBoundContext({});setBoundDeck(undefined);setDeckPrefill(undefined);setError('');setSketchOpen(false);setWorkspaceUri(null);setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setComposerKey(value=>value+1);};
  const openSection=(value:'chat'|'decks'|'more')=>{recovery.clearSideChat();if(value==='more'){if(section!=='more')moreSource.current=section;setMoreVisited(true);setMoreNonce(n=>n+1);}Keyboard.dismiss();setSketchOpen(false);setWorkspaceUri(null);setFileSidebarOpen(false);setActivityOpen(false);setScheduledDetail(null);setSection(value);};
  const tryDeck=async(deck:Deck,voice:Voice,input?:string)=>{if(deck.agent_type==='dream')return;await newChat();setSelection({deckId:deck.id,agentId:voice.id});setDeckPrefill({text:input ?? '',nonce:composerKey+1});openSection('chat');};
  const toggleActivity=()=>{Keyboard.dismiss();setFileSidebarOpen(false);setWorkspaceUri(null);setScheduledDetail(null);setSketchOpen(false);setActivityOpen(value=>!value);};
  const toggleWorkspace=()=>{Keyboard.dismiss();setActivityOpen(false);setWorkspaceUri(null);setScheduledDetail(null);setSketchOpen(false);setFileSidebarOpen(value=>!value);};
  useEffect(()=>{if(configLoaded&&config.workspace_enabled===false)setFileSidebarOpen(false);},[configLoaded,config.workspace_enabled]);
  const retryReads=()=>{setError('');setup.retry();if(session.error)void session.retry();else if(!setup.error&&!contextReadError)void history.reload();};
  const stop=()=>session.stop();
  const openSideChat=async(entry:ThreadInputEntry)=>{const task=await session.sideTask(entry);if(task&&visibleThread.current===entry.thread_id){recovery.rememberSideChat({threadId:task.thread_id});setSideChat({threadId:task.thread_id,documentOwner:{},notice:task.error_code?t('chat.inputQueue.sideChatLaunchFailed'):undefined});}};
  const closeSideChat=async()=>{
    const current=currentSideChat.current;if(!current)return false;
    await closeToolResultDocuments(current.documentOwner);if(currentSideChat.current!==current)return false;
    recovery.clearSideChat({threadId:current.threadId,writingSessionId:current.writingContext?.sessionId});currentSideChat.current=null;setSideChat(null);return true;
  };
  const returnToWriting=async()=>{
    const current=currentSideChat.current;if(!current?.restoredWritingSessionId)return;
    const transport:typeof fetch=async(input,init)=>{const response=await clientFetch(input,init);if(response.status===401)void refreshOwner.current();return response;};
    const target=await recovery.readWritingTarget({threadId:current.threadId,writingSessionId:current.restoredWritingSessionId},transport);
    if(currentSideChat.current!==current)return;
    if(!await closeSideChat())return;
    setEditorJump({nonce:++editorJumpNonce.current,detail:target});openSection('more');
  };
  const closeBusiness=async()=>{await closeToolResultDocuments(toolDocumentOwner);onClose?.();};
  const [writingIdleBlocked,setWritingIdleBlocked]=useState(false);
  const idle=useIdleScreenSaver(writingIdleBlocked||activityOpen||fileSidebarOpen||sketchOpen||scheduledDetail!==null||workspaceUri!==null||sideChat!==null||session.confirmation!==null,Boolean(onClose),setSaverVisible);
  const showSaver=saverVisible&&!idle.blocked;
  return <SafeAreaView style={styles.fill} onStartShouldSetResponderCapture={()=>{idle.activity();return false;}} onMoveShouldSetResponderCapture={()=>{idle.activity();return false;}} onTouchEnd={()=>idle.activity()}><KeyboardAvoidingView pointerEvents={showSaver?'none':'auto'} style={styles.fill} accessibilityElementsHidden={showSaver||activityOpen||fileSidebarOpen||scheduledDetail!==null} importantForAccessibility={showSaver||activityOpen||fileSidebarOpen||scheduledDetail!==null?'no-hide-descendants':'auto'} enabled={Boolean(onClose) || Platform.OS !== 'ios'} behavior={onClose&&Platform.OS==='ios'?'padding':undefined}>
    <View style={[styles.header,section==='more'?styles.hidden:undefined]}>{section!=='chat'?<InkLabel style={[styles.title,{color:foreground}]}>{BRAND_NAME}</InkLabel>:null}<View style={styles.fill}/>
      {onClose?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputQueue.closeSideChat')} onPress={()=>void closeBusiness()} style={styles.action}><InkLabel style={{color:foreground}}>{t('chat.history.close')}</InkLabel></Pressable>:section==='chat'?<ChatTopActions creating={session.posting&&!thread} activityOpen={activityOpen} workspaceEnabled={configLoaded&&config.workspace_enabled!==false} workspaceOpen={fileSidebarOpen}
      contextBadge={selectedVoice && (!thread || boundContext.threadId===thread)?<ChatAgentBadge voice={selectedVoice}/>:undefined}
      planAction={thread?<PlanButton key={thread} threadId={thread} origin={origin} workspaceAvailability={workspaceAvailability} workspaceResources={fileResources} onOpenWorkspace={openWorkspace} onOpenLink={url=>void openExternalLink(url,origin).catch(()=>setError('链接暂时无法打开。'))} activity={taskActivity} active={section==='chat'&&sideChat===null} onNavigateThread={id=>void selectThread(id)} onOpenScheduledTask={snapshot=>{setActivityOpen(false);setFileSidebarOpen(false);setScheduledDetail({taskId:snapshot.id,snapshot});}} onSessionExpired={()=>void refreshSession()}/>:undefined}
      pluginReceipt={<PluginReceiptBadge threadId={thread??null} deck={!thread || boundContext.threadId===thread?selectedDeck:undefined} activeVoiceId={selectedVoice?.id} activeVoiceName={selectedVoice?.name} onSessionExpired={()=>void refreshSession()}
        onSelectAgent={thread?voiceId=>{if(!selectedDeck?.voices?.some(voice=>voice.enabled && voice.id===voiceId))return;setBoundContext(current=>current.threadId===thread?{...current,voiceId}:current);}:undefined}/>}
        onNewChat={newChat} onToggleActivity={toggleActivity} onToggleWorkspace={toggleWorkspace} onShare={()=>{setActivityOpen(false);setFileSidebarOpen(false);setScheduledDetail(null);setWorkspaceUri(null);setSketchOpen(false);share.current?.open();}}/>:null}</View>
    {writingRecoveryBlocked || error || setup.error || contextReadError || session.error ? <View><Text accessibilityRole="alert" style={[styles.error,{color:foreground}]}>{writingRecoveryBlocked?t('chat.writingContextUnavailable'):error || setup.error || contextReadError || '会话状态待核对，请重试读取。'}</Text><Pressable accessibilityRole="button" disabled={Boolean(setup.error)&&setup.loading} style={styles.action} onPress={retryReads}><Text style={{color:foreground}}>{setup.loading?'正在读取…':'重试读取'}</Text></Pressable>{writingRecoveryBlocked?<Pressable accessibilityRole="button" style={styles.action} onPress={()=>void onReturnToWriting?.().catch(()=>setError(t('chat.writingContextUnavailable')))}><Text style={{color:foreground}}>{t('nav.writing')}</Text></Pressable>:null}</View> : null}
    <View style={[styles.fill,section!=='chat'?styles.hidden:undefined]} accessibilityElementsHidden={section!=='chat'} importantForAccessibility={section==='chat'?'auto':'no-hide-descendants'}><ChatPage showSearch={false} hasConversation={Boolean(thread)} history={history} activeThreadId={thread}
      quickActions={buildDefaultLandingQuickActions(t)} quickActionsDisabled={!configLoaded} onSelectThread={id=>void selectThread(id)}
      onDeleteThread={deleteThread}
      onQuickAction={item=>{void session.send(item.prompt,[],'auto').catch(()=>setError(t('chat.history.createFailed')));}}
      conversation={<ChatMessageList messages={messages} threadId={thread ?? ''} isLoading={session.running || session.posting} initialLoading={session.recovering}
        sourceThread={taskActivity.data.links?.source} onNavigateThread={id=>void selectThread(id)}
        origin={origin} workspaceAvailability={workspaceAvailability} workspaceResources={fileResources} onOpenWorkspace={openWorkspace} onAddImageMaterial={addWorkspaceImage} historicalMessageIds={session.historicalMessageIds} historyHasMore={session.hasMore} historyLoading={session.loadingOlder}
        onLoadOlder={()=>void session.loadOlder()} onOpenLink={url=>{void openExternalLink(url,origin).catch(()=>setError('链接暂时无法打开。'));}}
        renderOtherPart={(part,message,_index,presentation)=>isToolUIPart(part)?<ToolMessagePart documentOwner={toolDocumentOwner} part={part} origin={origin} threadId={thread??''} isLoading={session.running||session.posting} isLast={message.id===messages.at(-1)?.id} presentation={presentation}
          toolChoice={config.im_full_access_enabled?'auto':toolChoice} settledToolCallIds={session.settled} runtimePendingToolCallIds={session.runtimePending} active={section==='chat'&&sideChat===null}
          sendUserMessage={value=>{setToolChoice('auto');return session.sendUserMessage(value,thread??null);}} addToolResult={value=>session.addToolResult(value,thread??null)} onConfirmationSettled={id=>session.settleToolCall(id,thread??null)} onSessionExpired={()=>void refreshSession()}
          onEditorJump={detail=>{setEditorJump({nonce:++editorJumpNonce.current,detail});openSection('more');}}/>:part.type==='file'?<FileMessagePart part={part} origin={origin} isUserMessage={message.role==='user'} resources={messageFiles} onOpenLink={url=>void openExternalLink(url).catch(()=>setError('链接暂时无法打开。'))}/>:null} />}
      composer={<View style={styles.shrink}>
      {session.preparing?<InkLabel accessibilityRole="text" style={{color:foreground,padding:8}}>{t('chat.continuation.preparing')}</InkLabel>:null}
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
        <AIInputDock key={composerKey} ref={composer} recovery={recovery} origin={origin} disabled={uncertain} sendBlocked={writingRecoveryBlocked} loading={running}
          active={section==='chat' && !activityOpen && !fileSidebarOpen && scheduledDetail===null && sideChat===null && !sketchOpen && workspaceUri===null}
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
      {moreVisited?<MoreNavigator onIdleBlocked={setWritingIdleBlocked} ownerId={ownerId} origin={origin} decks={decks} editorJump={editorJump} onEditorJumpDispatched={nonce=>setEditorJump(current=>current?.nonce===nonce?undefined:current)} active={section==='more'} resetNonce={moreNonce} onClose={()=>openSection(moreSource.current)} onSessionExpired={()=>void refreshSession()}
        onOpenThread={(id,writingContext)=>{recovery.rememberSideChat({threadId:id,writingSessionId:writingContext?.sessionId});setSideChat({threadId:id,writingContext,documentOwner:{}});}} onPrepareChat={async input=>{await newChat();setDeckPrefill({text:input,nonce:composerKey+1});openSection('chat');}}
        onSettingsOpen={()=>setSettingsNavigation(value=>({nonce:value.nonce+1,target:'menu'}))} onResources={()=>setSettingsNavigation(value=>({nonce:value.nonce+1,target:'resources'}))}
        renderSettings={(back,settingsActive)=><StoryWorkspaceSettingsPage onOpenShareSource={async share=>{if(share.kind==='chat'){await selectThread(share.source_id);openSection('chat');return;}const response=await shareSourceFetch('/api/sessions/'+encodeURIComponent(share.source_id));if(!response.ok)throw Error('SHARE_SOURCE_UNAVAILABLE');const session=await response.json() as {editor_state:{cells:{id:string;type:string}[]}};const cell=session.editor_state.cells.find(value=>value.type==='text');if(!cell)throw Error('SHARE_SOURCE_UNAVAILABLE');setEditorJump({nonce:++editorJumpNonce.current,detail:{cellId:cell.id,editorSessionId:share.source_id}});openSection('more');}} ownerId={ownerId} origin={origin} active={settingsActive} navigation={settingsNavigation}
          decks={decks} loading={setup.loading} error={setup.error} onRefreshDecks={setup.refreshDecks} onTryDeck={tryDeck} onBack={back} logout={logout}
          onSessionExpired={()=>void refreshSession()} onConfigSaved={()=>void setup.refreshConfig().catch(()=>setError('配置暂时无法读取，请重试。'))}/>}/>:null}
    </View>
    {!onClose?<View accessibilityRole="tablist" style={styles.tabs}>{(['chat','decks','more'] as const).map(value => <Pressable key={value} testID={`main-tab-${value}`} accessibilityRole="tab" accessibilityState={{selected:section===value}} style={styles.action} onPress={() => openSection(value)}><InkLabel style={{color:foreground}}>{value==='chat'?t('nav.chat'):value==='decks'?t('nav.decks'):t('nav.more')}</InkLabel></Pressable>)}</View>:null}
  </KeyboardAvoidingView>
    {activityOpen?<View style={styles.overlay}><ActivitySidebar activity={activity} history={history} activeThreadId={thread} filters={activityFilters} onFiltersChange={setActivityFilters} onClose={()=>setActivityOpen(false)} onSelectThread={id=>void selectThread(id)} onDeleteThread={deleteThread} onTask={row=>{setActivityOpen(false);setScheduledDetail({taskId:row.id,snapshot:row.snapshot});}}/></View>:null}
    {scheduledDetail?<View style={styles.overlay}><ScheduledTaskDetailSidebar key={scheduledDetail.taskId} {...scheduledDetail} onSessionExpired={()=>void refreshSession()} onClose={()=>setScheduledDetail(null)} onOpenThread={id=>void selectThread(id)}/></View>:null}
    <View pointerEvents={fileSidebarOpen?'auto':'none'} style={fileSidebarOpen?styles.overlay:undefined}><FileSidebar sessionId={thread??undefined} open={fileSidebarOpen} availability={workspaceAvailability} resources={fileResources} onSessionExpired={()=>void refreshSession()} onClose={()=>setFileSidebarOpen(false)}/></View>
    <ChatShareSurface ref={share} origin={origin} threadId={thread} title={session.thread?.title??history.threads.find(row=>row.id===thread)?.title??t('chat.history.fallbackTitle')} availability={workspaceAvailability} resources={fileResources} onSessionExpired={()=>void refreshSession()}
      snapshot={()=>({messages,pendingConfirmation:session.confirmation??null,toolChoice})}/>
    <ChatHistorySearch history={history} activeThreadId={thread} onSelect={id=>void selectThread(id)}/>
    {workspaceUri?<WorkspaceFilePreview key={thread??'no-thread'} uri={workspaceUri} threadId={thread??undefined} availability={workspaceAvailability} resources={fileResources} onClose={()=>setWorkspaceUri(null)} onOpenWorkspace={openWorkspace} onOpenLink={url=>{void openExternalLink(url,origin).catch(()=>setError('链接暂时无法打开。'));}} onAddImageMaterial={addWorkspaceImage}/>:null}
    {origin && section==='chat'?<SketchInputSurface key={composerKey} origin={origin} open={sketchOpen} disabled={uncertain} onClose={()=>setSketchOpen(false)} onAdd={file=>composer.current?.addFile(file) ?? Promise.resolve(false)} />:null}
    <Modal visible={sideChat!==null} animationType="slide" presentationStyle="pageSheet" onRequestClose={()=>void closeSideChat()} supportedOrientations={['portrait','landscape']}>
      {sideChat?<ScreenFrame><Business key={JSON.stringify([sideChat.threadId,sideChat.writingContext?.sessionId??null])} ownerId={ownerId} logout={logout} refreshSession={refreshSession} initialThreadId={sideChat.threadId} initialNotice={sideChat.notice} documentOwner={sideChat.documentOwner} writingContext={sideChat.writingContext} onClose={()=>void closeSideChat()}
        onReturnToWriting={sideChat.restoredWritingSessionId?returnToWriting:undefined} onRecoveryDeparture={()=>recovery.clearSideChat({threadId:sideChat.threadId,writingSessionId:sideChat.writingContext?.sessionId})}/></ScreenFrame>:null}
    </Modal>
  {showSaver?<IdleScreenSaver onClose={idle.dismiss}/>:null}</SafeAreaView>;
}
export default function App() { return <ScreenFrame><SessionGate beforeRelease={()=>closeToolResultDocuments()}>{(logout,refreshSession,user) => <Business key={user.id} ownerId={user.id} logout={logout} refreshSession={refreshSession} />}</SessionGate></ScreenFrame>; }
const styles = StyleSheet.create({
  hidden:{display:'none'},
  overlay:{...StyleSheet.absoluteFillObject,zIndex:10},toolbarAction:{width:44,height:44,alignItems:'center',justifyContent:'center'},newAction:{minHeight:44,flexDirection:'row',alignItems:'center',gap:5.6,paddingHorizontal:8.8},shrink:{flexShrink:1,minHeight:0},fill:{flex:1},queue:{maxHeight:192,flexShrink:1},queueNotice:{padding:8,gap:4,borderWidth:StyleSheet.hairlineWidth,borderRadius:12},header:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',padding:12},title:{fontSize:22},action:{padding:16,minHeight:48},message:{padding:16,gap:8},error:{padding:12},composer:{flexDirection:'row',alignItems:'flex-end',padding:10,borderTopWidth:StyleSheet.hairlineWidth,borderColor:'#9c8e7c'},input:{flex:1,minHeight:48,maxHeight:180,padding:12,fontSize:16},tabs:{flexDirection:'row',justifyContent:'space-around'}});
