// [Sync] 2026-11-03: measure viewport-bound user previews and coalesce bottom movement after native layout; expansion retains reading intent.
// [Sync] 2026-10-30: preserve the original source marker above the first user text or at the pagination boundary.
// [Sync] 2026-10-30: share canonical process reads and keep validated MCP App document slots outside process disclosure across history/live projections.
// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-28: bind Workspace preview/material actions to the selected Thread, without reading identity from Markdown.
// [Input] Original UIMessage/history/stream state, process HTTP transport and caller-owned non-text parts.
// [Output] Native user/assistant Markdown, reasoning/history disclosure and the original bottom-follow/jump behavior.
// [Pos] Native message presentation; task, confirmation, persistence and submission stay with their original owners.
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,View,type NativeScrollEvent} from 'react-native';
import {useTranslation} from 'react-i18next';
import {isToolUIPart,type UIMessage} from 'ai';
import {useCopy} from '../../hooks/useCopy';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport.native';
import ChatMarkdown from './ChatMarkdown.native';
import type {WorkspaceAvailability,WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {messageMergeKey} from './chatHistoryWindow';
import {chatScrollPosition} from './chatScrollPosition';
import {projectHistoricalAssistantTurn} from './assistantTurnHistory';
import {useHistoricalChatProcess,type HistoricalProcessDetailState} from './useHistoricalChatProcess';
import {parseSavedMcpAppToolCall} from './mcp-apps/result';
import {resolveToolName} from './toolConfirmation';
import {getToolStatus} from './toolPartPresentation';
import {formatChatDuration} from './chatDuration';
import {isCompactionCompletionText,readContextCompactions} from '../../lib/context-compaction';
import {IconArrowDown,IconCheck,IconChevronRight,IconCopy} from './Icons';
import {TaskSessionSourceMarker} from './TaskSessionNavigation.native';
import type {TaskSessionLinksSnapshot} from './taskSessionLinks';
const emptyIds:ReadonlySet<string>=new Set();
// Presentation allocation from message-reading PRD; original text and submission have no length limit here.
const userMessageLayout={fontSize:14.72,lineHeight:25.024,paddingVertical:14.4,actionHeight:44,previewViewportFraction:0.5};
type Part=UIMessage['parts'][number];
export interface NativeChatMessageListProps {
  messages:UIMessage[];threadId:string;isLoading:boolean;initialLoading?:boolean;origin?:string;
  historicalMessageIds?:ReadonlySet<string>;historyHasMore?:boolean;historyLoading?:boolean;historyError?:boolean;onLoadOlder?:()=>void;
  transport?:typeof fetch;renderOtherPart?:(part:Part,message:UIMessage,index:number,presentation?:'tool-only'|'app-only')=>ReactNode;
  sourceThread?:TaskSessionLinksSnapshot['source'];onNavigateThread?:(id:string)=>void;
  onOpenLink?:(url:string)=>void;onOpenWorkspace?:(uri:string)=>void;workspaceAvailability?:WorkspaceAvailability;workspaceResources?:WorkspaceResources;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;
}
function MessageText({text,user,showActions,origin,onOpenLink,onOpenWorkspace,workspaceSessionId,workspaceAvailability,workspaceResources,onAddImageMaterial,leadingAction,viewportHeight,onExpand}:{text:string;user:boolean;showActions:boolean;origin?:string;workspaceSessionId?:string;workspaceAvailability?:WorkspaceAvailability;workspaceResources?:WorkspaceResources;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;onOpenLink?:(url:string)=>void;onOpenWorkspace?:(uri:string)=>void;leadingAction?:ReactNode;viewportHeight:number;onExpand:()=>void}){
  const {t}=useTranslation(),{copied,copy}=useCopy(),colors=useInkColors();
  const [expanded,setExpanded]=useState(false),[naturalHeight,setNaturalHeight]=useState(0);
  const previewHeight=Math.max(userMessageLayout.lineHeight,viewportHeight*userMessageLayout.previewViewportFraction-userMessageLayout.paddingVertical*2-userMessageLayout.actionHeight);
  const collapsible=user&&viewportHeight>0&&naturalHeight>previewHeight+userMessageLayout.actionHeight;
  return <View style={{alignItems:user?'flex-end':'stretch',gap:4,minWidth:0}}>
    {leadingAction}
    <View style={user?[styles.bubble,{backgroundColor:colors['color-bg-paper'],shadowColor:colors['color-shadow-soft']}]:styles.assistant}>
      <View style={collapsible&&!expanded?{maxHeight:previewHeight,overflow:'hidden'}:undefined}>
        <View onLayout={user?({nativeEvent})=>setNaturalHeight(nativeEvent.layout.height):undefined} style={styles.textBody}>
          <ChatMarkdown text={text} origin={origin} color={colors[user?'color-text-primary':'color-text-body']} fontSize={user?userMessageLayout.fontSize:15.2} lineHeight={user?userMessageLayout.lineHeight:26.6} onOpenLink={onOpenLink} onOpenWorkspace={onOpenWorkspace} workspaceSessionId={workspaceSessionId} workspaceAvailability={workspaceAvailability} workspaceResources={workspaceResources} onAddImageMaterial={onAddImageMaterial}/>
        </View>
      </View>
      {collapsible?<Pressable accessibilityRole="button" accessibilityLabel={t(expanded?'chat.message.collapse':'chat.message.expand')} accessibilityState={{expanded}} aria-expanded={expanded} onPress={()=>{if(!expanded)onExpand();setExpanded(value=>!value);}} style={styles.messageToggle}>
        <InkLabel style={{fontSize:13.6,color:colors['color-action-link']}}>{t(expanded?'chat.message.collapse':'chat.message.expand')}</InkLabel>
      </Pressable>:null}
    </View>
    {user||showActions?<Pressable accessibilityRole="button" accessibilityLabel={copied?'Copied!':'Copy'} onPress={()=>copy(text)} style={styles.copy}>
      {copied?<IconCheck width={15.2} height={15.2} color={colors['color-state-success']}/>:<IconCopy width={15.2} height={15.2} color={colors['color-text-muted']}/>}
    </Pressable>:null}
  </View>;
}
function Reasoning({text,streaming,forceExpanded}:{text:string;streaming:boolean;forceExpanded:boolean}){
  const [expanded,setExpanded]=useState(false),colors=useInkColors();const open=streaming||forceExpanded||expanded;
  return <View style={[styles.reasoning,{borderLeftColor:colors[streaming?'color-action-link':'color-border-paper']}]}>
    <Pressable accessibilityRole="button" accessibilityState={{expanded:open,disabled:streaming||forceExpanded}} disabled={streaming||forceExpanded} onPress={()=>setExpanded(value=>!value)} style={styles.reasoningToggle}>
      {streaming?<ActivityIndicator size="small" color={colors['color-action-link']}/>:null}<InkLabel numberOfLines={1} style={{flex:1,fontSize:13.6,fontStyle:'italic',color:colors['color-text-muted']}}>{text.slice(0,80)||'Thinking…'}</InkLabel>
      {!streaming&&!forceExpanded?<InkLabel style={{color:colors['color-text-muted']}}>{open?'‹':'›'}</InkLabel>:null}
    </Pressable>
    {open?<InkLabel selectable style={{marginTop:8,fontSize:13.6,lineHeight:23.12,color:colors['color-text-secondary']}}>{text}</InkLabel>:null}
  </View>;
}
function MessageRow({message:persisted,index,count,props,detail,load,sourceIndex,viewportHeight,onExpand}:{message:UIMessage;index:number;count:number;props:NativeChatMessageListProps;detail?:HistoricalProcessDetailState;load:()=>void;sourceIndex:number;viewportHeight:number;onExpand:()=>void}){
  const {t,i18n}=useTranslation(),colors=useInkColors();
  const [expanded,setExpanded]=useState(false);
  const message=detail?.status==='loaded'?detail.message:persisted;
  const candidate=props.historicalMessageIds?.has(message.id)?projectHistoricalAssistantTurn(message):null;
  const projection=candidate?.processAvailable?candidate:null;
  const lastText=message.parts.reduce((last,part,i)=>part.type==='text'&&part.text?i:last,-1);
  function partAt(partIndex:number,process=false){
    const part=message.parts[partIndex],key=`${message.id}-${partIndex}`;if(!part||part.type==='step-start')return null;
    if(part.type==='text'){
      if(!part.text||(message.role==='assistant'&&isCompactionCompletionText(part.text,message.metadata)))return null;
      const firstSourceText=index===sourceIndex&&partIndex===message.parts.findIndex(candidate=>candidate.type==='text'&&Boolean(candidate.text));
      return <MessageText key={key} text={part.text} user={message.role==='user'} showActions={!process&&partIndex===lastText&&(index<count-1||!props.isLoading)} origin={props.origin} onOpenLink={props.onOpenLink} onOpenWorkspace={props.onOpenWorkspace} workspaceSessionId={props.threadId} workspaceAvailability={props.workspaceAvailability} workspaceResources={props.workspaceResources} onAddImageMaterial={props.onAddImageMaterial} viewportHeight={viewportHeight} onExpand={onExpand} leadingAction={firstSourceText?<TaskSessionSourceMarker source={props.sourceThread??null} onNavigateThread={props.onNavigateThread}/>:undefined}/>;
    }
    if(part.type==='reasoning')return <Reasoning key={key} text={part.text} streaming={part.state==='streaming'} forceExpanded={process}/>;
    return <View key={key}>{props.renderOtherPart?.(part,message,partIndex,'tool-only')}</View>;
  }
  const duration=projection?formatChatDuration(projection.durationMs,i18n.language):'';
  const display=duration?t('chat.historyTurn.duration',{duration}):t('chat.historyTurn.viewProcess');
  const label=t(expanded?(duration?'chat.historyTurn.collapseAria':'chat.historyTurn.collapseAriaNoDuration'):(duration?'chat.historyTurn.expandAria':'chat.historyTurn.expandAriaNoDuration'),{label:display});
  const outsideApps=message.parts.flatMap((part,partIndex)=>{
    if(!isToolUIPart(part)||getToolStatus(part,props.isLoading)==='executing')return [];
    const saved=part as typeof part&{mcpAppResult?:unknown;toolMetadata?:{mcpAppResult?:unknown}};
    return parseSavedMcpAppToolCall({toolName:resolveToolName(part),toolCallId:part.toolCallId,input:'input' in part?part.input:undefined,output:'output' in part?part.output:undefined,mcpAppResult:saved.mcpAppResult??saved.toolMetadata?.mcpAppResult})?[{part,partIndex}]:[];
  });
  const finalIndex=projection?.finalPartIndex??lastText;
  return <View testID={`native-chat-message-${message.id}`} style={styles.message}>
    <View key="parts" style={styles.parts}>
    {projection?<>
      <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{expanded}} onPress={()=>{setExpanded(value=>!value);if(!expanded&&!detail)load();}} style={[styles.disclosure,{borderBottomColor:colors['color-border-neutral']}]}>
        <IconChevronRight width={14.4} height={14.4} color={colors['color-text-muted']} style={{transform:[{rotate:expanded?'90deg':'0deg'}]}}/><InkLabel style={{fontSize:13.6,color:colors['color-text-muted']}}>{display}</InkLabel>
      </Pressable>
      {expanded?<View style={styles.process}>{projection.deferredProcess?(detail?.status==='error'?<View><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t('chat.historyTurn.processLoadFailed')}</InkLabel><Pressable accessibilityRole="button" onPress={load} style={styles.retry}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.historyTurn.retry')}</InkLabel></Pressable></View>:<ActivityIndicator accessibilityLabel={t('chat.historyTurn.loadingProcess')} color={colors['color-text-muted']}/>):projection.processPartIndexes.map(i=>partAt(i,true))}</View>:null}
    </>:message.parts.map((_part,i)=>i===finalIndex?null:partAt(i))}
    </View>
    <View key="apps" style={styles.parts}>{outsideApps.map(({part,partIndex})=><View key={part.toolCallId}>{props.renderOtherPart?.(part,message,partIndex,'app-only')}</View>)}</View>
    <View key="final">{finalIndex>=0?partAt(finalIndex):null}</View>
    {readContextCompactions(message.metadata).map(row=>{const state=row.state==='running'&&!(index===count-1&&props.isLoading)?'unconfirmed':row.state,key=state==='completed'?(row.trigger==='auto'?'automaticCompleted':'completed'):state;return <InkLabel key={row.id} accessibilityLiveRegion="polite" style={{textAlign:'center',fontSize:12.8,color:colors['color-text-muted']}}>{t(`chat.contextCompaction.${key}`)}</InkLabel>;})}
  </View>;
}
export default function ChatMessageList(props:NativeChatMessageListProps){
  const {t}=useTranslation(),colors=useInkColors();
  const sourceIndex=props.sourceThread&&!props.historyHasMore?props.messages.findIndex(message=>message.role==='user'&&message.parts.some(part=>part.type==='text'&&Boolean(part.text))):-1;
  const process=useHistoricalChatProcess(props.threadId,props.messages,props.historicalMessageIds??emptyIds,props.transport??clientFetch);
  const scroll=useRef<ScrollView>(null),nearBottom=useRef(true),dragging=useRef(false),followingLayout=useRef(false),geometry=useRef({content:0,offset:0,viewport:0});
  const [showJump,setShowJump]=useState(false),[viewportHeight,setViewportHeight]=useState(0);
  const layoutFrame=useRef<number|null>(null);
  function cancelMovement(){if(layoutFrame.current!==null){cancelAnimationFrame(layoutFrame.current);layoutFrame.current=null;}}
  function jump(animated=false){
    nearBottom.current=true;followingLayout.current=true;setShowJump(false);cancelMovement();
    layoutFrame.current=requestAnimationFrame(()=>{layoutFrame.current=null;followingLayout.current=!chatScrollPosition(geometry.current.content,geometry.current.offset,geometry.current.viewport).isNearBottom;scroll.current?.scrollToEnd({animated});});
  }
  function readExpanded(){cancelMovement();nearBottom.current=false;followingLayout.current=false;}
  function beginDrag(){cancelMovement();dragging.current=true;followingLayout.current=false;}
  function update(event:NativeScrollEvent){
    const before=geometry.current,changed=before.content!==event.contentSize.height||before.viewport!==event.layoutMeasurement.height;
    geometry.current={content:event.contentSize.height,offset:event.contentOffset.y,viewport:event.layoutMeasurement.height};
    const position=chatScrollPosition(geometry.current.content,geometry.current.offset,geometry.current.viewport);
    if(!dragging.current&&nearBottom.current&&(followingLayout.current||changed)){
      if(position.isNearBottom)followingLayout.current=false;else jump();
      setShowJump(false);return;
    }
    followingLayout.current=false;nearBottom.current=position.isNearBottom;setShowJump(position.showScrollToBottom);
    if(dragging.current&&event.contentOffset.y<=0&&props.historyHasMore&&!props.historyLoading)props.onLoadOlder?.();
  }
  useEffect(()=>{nearBottom.current=true;followingLayout.current=false;dragging.current=false;setShowJump(false);jump();return cancelMovement;},[props.threadId]);
  return <View style={[styles.fill,styles.viewport]}>
    <ScrollView ref={scroll} testID="native-chat-messages-scroll" style={styles.fill} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" scrollEventThrottle={16}
      maintainVisibleContentPosition={{minIndexForVisible:1}} onScrollBeginDrag={beginDrag} onScrollEndDrag={()=>{dragging.current=false;}} onMomentumScrollBegin={beginDrag} onMomentumScrollEnd={()=>{dragging.current=false;}} onScroll={({nativeEvent})=>update(nativeEvent)}
      onLayout={({nativeEvent})=>{geometry.current.viewport=nativeEvent.layout.height;setViewportHeight(nativeEvent.layout.height);if(nearBottom.current&&!dragging.current)jump();}}
      onContentSizeChange={(_width,height)=>{geometry.current.content=height;if(nearBottom.current&&!dragging.current)jump();else setShowJump(chatScrollPosition(height,geometry.current.offset,geometry.current.viewport).showScrollToBottom);}}>
      <View style={styles.historyHeader}>
        {props.historyError?<View><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t('chat.historyTurn.loadFailed')}</InkLabel><Pressable accessibilityRole="button" onPress={props.onLoadOlder} style={styles.retry}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.historyTurn.retry')}</InkLabel></Pressable></View>:props.historyLoading?<ActivityIndicator accessibilityLabel={t('chat.historyTurn.loadingEarlier')} color={colors['color-text-muted']}/>:props.historyHasMore?<Pressable accessibilityRole="button" onPress={props.onLoadOlder} style={styles.retry}><InkLabel style={{color:colors['color-text-muted']}}>{t('chat.historyTurn.loadEarlier')}</InkLabel></Pressable>:null}
        {props.initialLoading&&props.messages.length===0?<ActivityIndicator accessibilityLabel={t('chat.historyTurn.loading')} color={colors['color-text-muted']}/>:null}
      </View>
      {sourceIndex<0?<TaskSessionSourceMarker source={props.sourceThread??null} onNavigateThread={props.onNavigateThread}/>:null}
      {props.messages.map((message,index)=><MessageRow key={`${props.threadId}:${messageMergeKey(message)}`} message={message} index={index} count={props.messages.length} props={{...props,historicalMessageIds:props.historicalMessageIds??emptyIds}} detail={process.details[`${props.threadId}:${message.id}`]} load={()=>void process.load(message)} sourceIndex={sourceIndex} viewportHeight={viewportHeight} onExpand={readExpanded}/>)}
    </ScrollView>
    {showJump?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.panel.scrollToBottom')} onPress={()=>jump(true)} style={[styles.jump,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface-solid']}]}><IconArrowDown width={18} height={18} color={colors['color-text-primary']}/></Pressable>:null}
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},viewport:{overflow:'hidden'},content:{padding:16,paddingBottom:24,gap:20},message:{minWidth:0,gap:16},parts:{gap:16},historyHeader:{alignItems:'center'},retry:{minHeight:44,paddingHorizontal:10,justifyContent:'center'},bubble:{maxWidth:'85%',minWidth:0,borderRadius:18,paddingVertical:userMessageLayout.paddingVertical,paddingHorizontal:16,shadowOpacity:1,shadowRadius:4,shadowOffset:{width:0,height:1}},assistant:{width:'100%',minWidth:0},textBody:{minWidth:0,flexShrink:0},messageToggle:{minHeight:userMessageLayout.actionHeight,justifyContent:'center',alignItems:'flex-end'},copy:{width:44,height:44,justifyContent:'center',alignItems:'center'},reasoning:{paddingLeft:13.6,borderLeftWidth:2},reasoningToggle:{minHeight:44,flexDirection:'row',alignItems:'center',gap:8},disclosure:{minHeight:44,flexDirection:'row',alignItems:'center',gap:5.6,borderBottomWidth:1,paddingHorizontal:4,paddingVertical:8.8},process:{gap:16,paddingTop:16},jump:{position:'absolute',bottom:8,alignSelf:'center',width:44,height:44,borderWidth:1,borderRadius:999,alignItems:'center',justifyContent:'center'}});
