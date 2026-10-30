// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-28: bind Workspace preview/material actions to the selected Thread, without reading identity from Markdown.
// [Input] Original UIMessage/history/stream state, process HTTP transport and caller-owned non-text parts.
// [Output] Native user/assistant Markdown, reasoning/history disclosure and the original bottom-follow/jump behavior.
// [Pos] Native message presentation; task, confirmation, persistence and submission stay with their original owners.
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,View,type NativeScrollEvent} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {UIMessage} from 'ai';
import {useCopy} from '../../hooks/useCopy';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport.native';
import ChatMarkdown from './ChatMarkdown.native';
import type {WorkspaceAvailability,WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {chatScrollPosition} from './chatScrollPosition';
import {projectHistoricalAssistantTurn} from './assistantTurnHistory';
import {fetchClaudeThreadMessageProcess} from './threadSessionHydration';
import {formatChatDuration} from './chatDuration';
import {isCompactionCompletionText,readContextCompactions} from '../../lib/context-compaction';
import {IconArrowDown,IconCheck,IconChevronRight,IconCopy} from './Icons';
const emptyIds:ReadonlySet<string>=new Set();
type Part=UIMessage['parts'][number];
export interface NativeChatMessageListProps {
  messages:UIMessage[];threadId:string;isLoading:boolean;initialLoading?:boolean;origin?:string;
  historicalMessageIds?:ReadonlySet<string>;historyHasMore?:boolean;historyLoading?:boolean;historyError?:boolean;onLoadOlder?:()=>void;
  transport?:typeof fetch;renderOtherPart?:(part:Part,message:UIMessage,index:number)=>ReactNode;
  onOpenLink?:(url:string)=>void;onOpenWorkspace?:(uri:string)=>void;workspaceAvailability?:WorkspaceAvailability;workspaceResources?:WorkspaceResources;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;
}
function MessageText({text,user,showActions,origin,onOpenLink,onOpenWorkspace,workspaceSessionId,workspaceAvailability,workspaceResources,onAddImageMaterial}:{text:string;user:boolean;showActions:boolean;origin?:string;workspaceSessionId?:string;workspaceAvailability?:WorkspaceAvailability;workspaceResources?:WorkspaceResources;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;onOpenLink?:(url:string)=>void;onOpenWorkspace?:(uri:string)=>void}){
  const {copied,copy}=useCopy(),colors=useInkColors();
  return <View style={{alignItems:user?'flex-end':'stretch',gap:4,minWidth:0}}>
    <View style={user?[styles.bubble,{backgroundColor:colors['color-bg-paper'],shadowColor:colors['color-shadow-soft']}]:styles.assistant}>
      <ChatMarkdown text={text} origin={origin} color={colors[user?'color-text-primary':'color-text-body']} fontSize={user?14.72:15.2} lineHeight={user?25.024:26.6} onOpenLink={onOpenLink} onOpenWorkspace={onOpenWorkspace} workspaceSessionId={workspaceSessionId} workspaceAvailability={workspaceAvailability} workspaceResources={workspaceResources} onAddImageMaterial={onAddImageMaterial}/>
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
type Detail={status:'loading'}|{status:'error'}|{status:'loaded';message:UIMessage};
function MessageRow({message:persisted,index,count,props}:{message:UIMessage;index:number;count:number;props:NativeChatMessageListProps}){
  const {t,i18n}=useTranslation(),colors=useInkColors();
  const [expanded,setExpanded]=useState(false),[detail,setDetail]=useState<Detail>();const reader=useRef<AbortController|undefined>(undefined);
  useEffect(()=>()=>reader.current?.abort(),[]);
  const summary=props.historicalMessageIds?.has(persisted.id)?projectHistoricalAssistantTurn(persisted):null;
  const message=detail?.status==='loaded'?detail.message:persisted;
  const candidate=props.historicalMessageIds?.has(message.id)?projectHistoricalAssistantTurn(message):null;
  const projection=candidate?.processAvailable?candidate:null;
  async function load(){
    if(reader.current||detail?.status==='loaded'||!summary?.deferredProcess)return;
    const controller=new AbortController();reader.current=controller;setDetail({status:'loading'});
    try{
      const next=await fetchClaudeThreadMessageProcess(props.threadId,persisted.id,controller.signal,props.transport??clientFetch),projected=projectHistoricalAssistantTurn(next);
      const a=persisted.parts[summary.finalPartIndex],b=projected?next.parts[projected.finalPartIndex]:undefined;
      if(!projected||projected.deferredProcess||!projected.processAvailable||projected.turnKey!==summary.turnKey||a?.type!=='text'||b?.type!=='text'||a.text!==b.text)throw new Error('HISTORY_PROCESS_MISMATCH');
      if(!controller.signal.aborted)setDetail({status:'loaded',message:next});
    }catch{if(!controller.signal.aborted)setDetail({status:'error'});}finally{if(reader.current===controller)reader.current=undefined;}
  }
  const lastText=message.parts.reduce((last,part,i)=>part.type==='text'&&part.text?i:last,-1);
  function partAt(partIndex:number,process=false){
    const part=message.parts[partIndex],key=`${message.id}-${partIndex}`;if(!part||part.type==='step-start')return null;
    if(part.type==='text'){
      if(!part.text||(message.role==='assistant'&&isCompactionCompletionText(part.text,message.metadata)))return null;
      return <MessageText key={key} text={part.text} user={message.role==='user'} showActions={!process&&partIndex===lastText&&(index<count-1||!props.isLoading)} origin={props.origin} onOpenLink={props.onOpenLink} onOpenWorkspace={props.onOpenWorkspace} workspaceSessionId={props.threadId} workspaceAvailability={props.workspaceAvailability} workspaceResources={props.workspaceResources} onAddImageMaterial={props.onAddImageMaterial}/>;
    }
    if(part.type==='reasoning')return <Reasoning key={key} text={part.text} streaming={part.state==='streaming'} forceExpanded={process}/>;
    return <View key={key}>{props.renderOtherPart?.(part,message,partIndex)}</View>;
  }
  const duration=projection?formatChatDuration(projection.durationMs,i18n.language):'';
  const display=duration?t('chat.historyTurn.duration',{duration}):t('chat.historyTurn.viewProcess');
  const label=t(expanded?(duration?'chat.historyTurn.collapseAria':'chat.historyTurn.collapseAriaNoDuration'):(duration?'chat.historyTurn.expandAria':'chat.historyTurn.expandAriaNoDuration'),{label:display});
  return <View testID={`native-chat-message-${message.id}`} style={styles.message}>
    {projection?<>
      <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{expanded}} onPress={()=>{setExpanded(value=>!value);if(!expanded)void load();}} style={[styles.disclosure,{borderBottomColor:colors['color-border-neutral']}]}>
        <IconChevronRight width={14.4} height={14.4} color={colors['color-text-muted']} style={{transform:[{rotate:expanded?'90deg':'0deg'}]}}/><InkLabel style={{fontSize:13.6,color:colors['color-text-muted']}}>{display}</InkLabel>
      </Pressable>
      {expanded?<View style={styles.process}>{projection.deferredProcess?(detail?.status==='error'?<View><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t('chat.historyTurn.processLoadFailed')}</InkLabel><Pressable accessibilityRole="button" onPress={()=>void load()} style={styles.retry}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.historyTurn.retry')}</InkLabel></Pressable></View>:<ActivityIndicator accessibilityLabel={t('chat.historyTurn.loadingProcess')} color={colors['color-text-muted']}/>):projection.processPartIndexes.map(i=>partAt(i,true))}</View>:null}
      {partAt(projection.finalPartIndex)}
    </>:message.parts.map((_part,i)=>partAt(i))}
    {readContextCompactions(message.metadata).map(row=>{const state=row.state==='running'&&!(index===count-1&&props.isLoading)?'unconfirmed':row.state,key=state==='completed'?(row.trigger==='auto'?'automaticCompleted':'completed'):state;return <InkLabel key={row.id} accessibilityLiveRegion="polite" style={{textAlign:'center',fontSize:12.8,color:colors['color-text-muted']}}>{t(`chat.contextCompaction.${key}`)}</InkLabel>;})}
  </View>;
}
export default function ChatMessageList(props:NativeChatMessageListProps){
  const {t}=useTranslation(),colors=useInkColors();
  const scroll=useRef<ScrollView>(null),nearBottom=useRef(true),dragging=useRef(false),followingLayout=useRef(false),geometry=useRef({content:0,offset:0,viewport:0});
  const [showJump,setShowJump]=useState(false);
  function jump(animated=false){nearBottom.current=true;followingLayout.current=!chatScrollPosition(geometry.current.content,geometry.current.offset,geometry.current.viewport).isNearBottom;setShowJump(false);scroll.current?.scrollToEnd({animated});}
  function update(event:NativeScrollEvent){
    const before=geometry.current,changed=before.content!==event.contentSize.height||before.viewport!==event.layoutMeasurement.height;
    geometry.current={content:event.contentSize.height,offset:event.contentOffset.y,viewport:event.layoutMeasurement.height};
    const position=chatScrollPosition(geometry.current.content,geometry.current.offset,geometry.current.viewport);
    if(!dragging.current&&nearBottom.current&&(followingLayout.current||changed)){
      if(position.isNearBottom)followingLayout.current=false;else if(changed)jump();
      setShowJump(false);return;
    }
    followingLayout.current=false;nearBottom.current=position.isNearBottom;setShowJump(position.showScrollToBottom);
    if(dragging.current&&event.contentOffset.y<=0&&props.historyHasMore&&!props.historyLoading)props.onLoadOlder?.();
  }
  useEffect(()=>{nearBottom.current=true;followingLayout.current=false;setShowJump(false);},[props.threadId]);
  return <View style={[styles.fill,styles.viewport]}>
    <ScrollView ref={scroll} testID="native-chat-messages-scroll" style={styles.fill} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" scrollEventThrottle={16}
      maintainVisibleContentPosition={{minIndexForVisible:1}} onScrollBeginDrag={()=>{dragging.current=true;followingLayout.current=false;}} onScrollEndDrag={()=>{dragging.current=false;}} onMomentumScrollBegin={()=>{dragging.current=true;}} onMomentumScrollEnd={()=>{dragging.current=false;}} onScroll={({nativeEvent})=>update(nativeEvent)}
      onLayout={({nativeEvent})=>{geometry.current.viewport=nativeEvent.layout.height;if(nearBottom.current)jump();}}
      onContentSizeChange={(_width,height)=>{geometry.current.content=height;if(nearBottom.current)jump();else setShowJump(chatScrollPosition(height,geometry.current.offset,geometry.current.viewport).showScrollToBottom);}}>
      <View style={styles.historyHeader}>
        {props.historyError?<View><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t('chat.historyTurn.loadFailed')}</InkLabel><Pressable accessibilityRole="button" onPress={props.onLoadOlder} style={styles.retry}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.historyTurn.retry')}</InkLabel></Pressable></View>:props.historyLoading?<ActivityIndicator accessibilityLabel={t('chat.historyTurn.loadingEarlier')} color={colors['color-text-muted']}/>:props.historyHasMore?<Pressable accessibilityRole="button" onPress={props.onLoadOlder} style={styles.retry}><InkLabel style={{color:colors['color-text-muted']}}>{t('chat.historyTurn.loadEarlier')}</InkLabel></Pressable>:null}
        {props.initialLoading&&props.messages.length===0?<ActivityIndicator accessibilityLabel={t('chat.historyTurn.loading')} color={colors['color-text-muted']}/>:null}
      </View>
      {props.messages.map((message,index)=><MessageRow key={`${props.threadId}:${message.id}`} message={message} index={index} count={props.messages.length} props={{...props,historicalMessageIds:props.historicalMessageIds??emptyIds}}/>)}
    </ScrollView>
    {showJump?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.panel.scrollToBottom')} onPress={()=>jump(true)} style={[styles.jump,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface-solid']}]}><IconArrowDown width={18} height={18} color={colors['color-text-primary']}/></Pressable>:null}
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},viewport:{overflow:'hidden'},content:{padding:16,paddingBottom:24,gap:20},message:{minWidth:0,gap:16},historyHeader:{alignItems:'center'},retry:{minHeight:44,paddingHorizontal:10,justifyContent:'center'},bubble:{maxWidth:'85%',minWidth:0,borderRadius:18,paddingVertical:14.4,paddingHorizontal:16,shadowOpacity:1,shadowRadius:4,shadowOffset:{width:0,height:1}},assistant:{width:'100%',minWidth:0},copy:{width:44,height:44,justifyContent:'center',alignItems:'center'},reasoning:{paddingLeft:13.6,borderLeftWidth:2},reasoningToggle:{minHeight:44,flexDirection:'row',alignItems:'center',gap:8},disclosure:{minHeight:44,flexDirection:'row',alignItems:'center',gap:5.6,borderBottomWidth:1,paddingHorizontal:4,paddingVertical:8.8},process:{gap:16,paddingTop:16},jump:{position:'absolute',bottom:8,alignSelf:'center',width:44,height:44,borderWidth:1,borderRadius:999,alignItems:'center',justifyContent:'center'}});
