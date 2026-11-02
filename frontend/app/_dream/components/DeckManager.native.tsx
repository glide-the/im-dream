// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] App-owned Deck catalog, original CRUD/defaults, native HTTP and Chat draft callback.
// [Output] Native launcher, Settings/Work inventory and original maintenance workflows.
// [Pos] Native Deck UI coordinator; App owns backend/session/catalog and business APIs retain authority.
import {useEffect,useMemo,useRef,useState} from 'react';
import {ActivityIndicator,Alert,BackHandler,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,Switch,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {Deck,Voice} from '../api/voiceApi';
import {createDeck,createVoice,deleteDeck,deleteVoice,syncDeck,updateDeck,updateVoice} from '../api/deckMutationApi';
import {listChatThreads,deleteChatThread,type ChatHistoryThread} from '../api/chatHistoryApi';
import {DEFAULT_DECK_CREATE_VISUAL,DECK_MANAGEMENT_PAGE_SIZE,DECK_RELATED_THREADS_PAGE_SIZE} from '../constants/deck';
import type {ActiveChatVoice} from '../lib/chat-schema';
import {clientFetch} from '../../../src/platform/transport.native';
import DeckLaunchScreen from './deck/DeckLaunchScreen.native';
import DeckEditorModal from './DeckEditorModal.native';
import DeckAgentIcon,{deckAgentColor} from './deck/DeckAgentIcon.native';
import {isSystemDeckDisplay,matchesDeckHomeQuery} from './deck/deckPresentation';
import InkLabel from '../../../src/components/InkLabel.native';
import useInkColors from '../../../src/components/useInkColors.native';

interface Props {
  decks:Deck[];active:boolean;loading:boolean;error?:string;transport?:typeof fetch;
  onRefresh:()=>Promise<Deck[]>;onSessionExpired?:()=>void;onTryDeck:(deck:Deck,voice:Voice,input?:string)=>void;
  managementOnly?:boolean;
}
function confirmMutation(message:string):Promise<boolean>{
  return new Promise(resolve=>Alert.alert('',message,[{text:'取消',style:'cancel',onPress:()=>resolve(false)},{text:'确认',style:'destructive',onPress:()=>resolve(true)}],{cancelable:true,onDismiss:()=>resolve(false)}));
}
export default function DeckManager({decks,active,loading,error,onRefresh,onSessionExpired,onTryDeck,transport=clientFetch,managementOnly=false}:Props){
  const {t,i18n}=useTranslation(),colors=useInkColors();
  const [work,setWork]=useState(managementOnly),[editorId,setEditorId]=useState<string|null>(null),[selected,setSelected]=useState<Record<string,string|null>>({});
  const [creating,setCreating]=useState(false),[creatingVoice,setCreatingVoice]=useState<string|null>(null),[busy,setBusy]=useState<string|null>(null),[refreshing,setRefreshing]=useState(false),[operationError,setOperationError]=useState('');
  const [query,setQuery]=useState(''),[type,setType]=useState<'all'|'chat'>('all'),[status,setStatus]=useState<'all'|'enabled'|'disabled'>('all'),[page,setPage]=useState(1),[menu,setMenu]=useState<string|null>(null);
  const [related,setRelated]=useState<Deck|null>(null),[threads,setThreads]=useState<ChatHistoryThread[]>([]),[relatedLoading,setRelatedLoading]=useState(false),[relatedError,setRelatedError]=useState(''),[hasMore,setHasMore]=useState(false),[deletingThread,setDeletingThread]=useState<string|null>(null);
  const expired=useRef(onSessionExpired);expired.current=onSessionExpired;
  const read=useMemo<typeof fetch>(()=>async(input,init)=>{const response=await transport(input,init);if(response.status===401)expired.current?.();return response;},[transport]);
  const relatedGeneration=useRef(0),relatedController=useRef<AbortController|null>(null),mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;relatedGeneration.current++;relatedController.current?.abort();};},[]);
  const catalog=decks.filter(deck=>deck.agent_type!=='dream'),editor=catalog.find(deck=>deck.id===editorId);
  useEffect(()=>setSelected(previous=>{
    let changed=false;const next={...previous};
    decks.forEach(deck=>{const ids=(deck.voices??[]).filter(voice=>voice.enabled).map(voice=>voice.id),current=next[deck.id];
      if(!ids.length){if(current!==null){next[deck.id]=null;changed=true;}}
      else if(!current||!ids.includes(current)){next[deck.id]=ids[0];changed=true;}
    });return changed?next:previous;
  }),[decks]);
  const filtered=catalog.filter(deck=>matchesDeckHomeQuery(deck,query)&&(type==='all'||deck.agent_type===type)&&(status==='all'||(status==='enabled'?deck.enabled:!deck.enabled)));
  const pages=Math.max(1,Math.ceil(filtered.length/DECK_MANAGEMENT_PAGE_SIZE)),visible=filtered.slice((page-1)*DECK_MANAGEMENT_PAGE_SIZE,page*DECK_MANAGEMENT_PAGE_SIZE);
  useEffect(()=>setPage(value=>Math.min(value,pages)),[pages]);
  useEffect(()=>{
    if(Platform.OS!=='android'||!active||!work||editor||related||managementOnly)return;
    const handle=BackHandler.addEventListener('hardwareBackPress',()=>{setWork(false);setMenu(null);return true;});return()=>handle.remove();
  },[active,work,editor?.id,related?.id,managementOnly]);
  const label=(text:string,muted=false)=><InkLabel style={{color:colors[muted?'color-text-muted':'color-text-primary']}}>{text}</InkLabel>;
  const button=(text:string,action:()=>void,disabled=false)=><Pressable accessibilityRole="button" accessibilityLabel={text} disabled={disabled} accessibilityState={{disabled}} onPress={action}
    style={[styles.button,{borderColor:colors['color-border-paper'],opacity:disabled?0.5:1}]}>{label(text)}</Pressable>;
  const formatDate=(value?:string)=>!value||Number.isNaN(new Date(value).getTime())?t('deck.labels.updateUnknown'):new Intl.DateTimeFormat(i18n.resolvedLanguage==='zh'?'zh-CN':'en-US',{year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));
  const owned=(id:string)=>{const deck=catalog.find(item=>item.id===id);if(!deck||isSystemDeckDisplay(deck))throw new Error(t('deck.labels.systemDeck'));return deck;};
  const refresh=async()=>{setRefreshing(true);setOperationError('');try{await onRefresh();}catch(cause){setOperationError(cause instanceof Error?cause.message:t('deck.messages.loadFailed'));}finally{if(mounted.current)setRefreshing(false);}};
  const mutate=async(id:string,action:()=>Promise<unknown>)=>{owned(id);setBusy(id);setOperationError('');try{await action();await onRefresh();}catch(cause){setOperationError(cause instanceof Error?cause.message:t('deck.messages.updateFailed'));throw cause;}finally{if(mounted.current)setBusy(null);}};
  const create=async()=>{if(creating)return;setCreating(true);setOperationError('');try{const result=await createDeck({name:t('deck.defaults.newName'),description:t('deck.defaults.newDescription'),...DEFAULT_DECK_CREATE_VISUAL},read);await onRefresh();if(mounted.current){setEditorId(result.deck_id);}}catch(cause){setOperationError(cause instanceof Error?cause.message:t('deck.messages.createFailed'));}finally{if(mounted.current)setCreating(false);}};
  const saveDeck=(id:string,data:Partial<Deck>)=>mutate(id,()=>updateDeck(id,data,read));
  const voiceOwner=(id:string)=>{const deck=catalog.find(item=>item.voices?.some(voice=>voice.id===id));if(!deck)throw new Error(t('deck.messages.updateAgentFailed'));owned(deck.id);return deck;};
  const saveVoice=(id:string,data:Partial<Voice>)=>{const deck=voiceOwner(id);return mutate(deck.id,()=>updateVoice(id,data,read));};
  const addVoice=async(id:string)=>{owned(id);setCreatingVoice(id);try{await mutate(id,async()=>{const result=await createVoice({deck_id:id,name:'New Voice',system_prompt:'You are a helpful assistant.',icon:'brain',color:'blue'},read);setSelected(current=>({...current,[id]:result.voice_id}));});}finally{if(mounted.current)setCreatingVoice(null);}};
  const removeVoice=async(id:string)=>{const deck=voiceOwner(id);if(await confirmMutation(t('deck.confirm.deleteAgent')))await mutate(deck.id,()=>deleteVoice(id,read));};
  const removeDeck=async(id:string)=>{owned(id);if(await confirmMutation(t('deck.confirm.delete')))await mutate(id,async()=>{await deleteDeck(id,read);if(editorId===id)setEditorId(null);});};
  const sync=async(id:string)=>{owned(id);if(await confirmMutation(t('deck.confirm.sync')))await mutate(id,()=>syncDeck(id,read));};
  const closeRelated=()=>{relatedGeneration.current++;relatedController.current?.abort();setRelated(null);setThreads([]);setRelatedError('');setDeletingThread(null);setRelatedLoading(false);};
  const loadRelated=async(deck:Deck,offset=0)=>{
    relatedController.current?.abort();const controller=new AbortController();relatedController.current=controller;const generation=++relatedGeneration.current;
    setRelatedLoading(true);setRelatedError('');try{const rows=await listChatThreads({deckId:deck.id,limit:DECK_RELATED_THREADS_PAGE_SIZE,offset},{transport:read,signal:controller.signal});
      if(!mounted.current||generation!==relatedGeneration.current)return;setThreads(current=>offset?[...current,...rows]:rows);setHasMore(rows.length===DECK_RELATED_THREADS_PAGE_SIZE);
    }catch(cause){if(mounted.current&&generation===relatedGeneration.current&&!controller.signal.aborted)setRelatedError(cause instanceof Error?cause.message:t('deck.related.loadFailed'));}finally{if(mounted.current&&generation===relatedGeneration.current)setRelatedLoading(false);}
  };
  const openRelated=(deck:Deck)=>{setMenu(null);setRelated(deck);setThreads([]);setHasMore(false);void loadRelated(deck);};
  const removeThread=async(row:ChatHistoryThread)=>{if(deletingThread||!related)return;const generation=relatedGeneration.current;
    if(!await confirmMutation(t('deck.related.confirmDelete',{title:row.title||t('chat.history.fallbackTitle')})))return;
    if(generation!==relatedGeneration.current)return;setDeletingThread(row.id);setRelatedError('');try{await deleteChatThread(row.id,read);if(mounted.current&&generation===relatedGeneration.current)setThreads(current=>current.filter(item=>item.id!==row.id));}
    catch(cause){if(mounted.current&&generation===relatedGeneration.current)setRelatedError(cause instanceof Error?cause.message:t('deck.related.deleteFailed'));}finally{if(mounted.current&&generation===relatedGeneration.current)setDeletingThread(null);}
  };
  const useVoice=(deckId:string,voice:ActiveChatVoice)=>{const deck=catalog.find(item=>item.id===deckId),record=deck?.voices?.find(item=>item.id===voice.id);if(deck&&record){setEditorId(null);onTryDeck(deck,record);}};
  return <View style={styles.fill}>
    {work?<ScrollView style={styles.fill} contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled" testID="native-deck-management">
      {!managementOnly?<View style={styles.wrap}>{button(`‹ ${t('settings.workspace.backToApp')}`,()=>{setWork(false);setMenu(null);})}{label(`${t('nav.settings')} / ${t('settings.workspace.navigation.work')}`)}</View>:null}
      <InkLabel accessibilityRole="header" style={[styles.title,{color:colors['color-text-primary']}]}>{t('deck.home.allTitle')}</InkLabel>
      <View style={styles.wrap}>{button(creating?t('deck.actions.creating'):t('deck.actions.create'),()=>{void create();},creating)}{button(t('deck.actions.refresh'),()=>{void refresh();},refreshing||loading)}</View>
      {operationError||error?<View accessibilityRole="alert">{label(operationError||error||'')}</View>:null}
      <TextInput accessibilityLabel={t('deck.creator.searchLabel')} placeholder={t('deck.creator.searchPlaceholder')} value={query} onChangeText={value=>{setQuery(value);setPage(1);}} autoCorrect={false} autoCapitalize="none"
        placeholderTextColor={colors['color-text-muted']} style={[styles.input,{color:colors['color-text-primary'],borderColor:colors['color-border-paper']}]} />
      <View style={styles.wrap} accessibilityRole="tablist" accessibilityLabel={t('deck.creator.agentTypeFilter')}>{(['all','chat'] as const).map(value=><Pressable key={value} accessibilityRole="tab" accessibilityState={{selected:type===value}} onPress={()=>{setType(value);setPage(1);}} style={[styles.button,{backgroundColor:type===value?colors['color-bg-hover']:'transparent'}]}>
        {label(`${t(`deck.creator.agentTypeTabs.${value}`)} ${catalog.filter(deck=>value==='all'||deck.agent_type===value).length}`)}</Pressable>)}</View>
      <View style={styles.wrap} accessibilityLabel={t('deck.creator.statusFilter')}>{(['all','enabled','disabled'] as const).map(value=><Pressable key={value} accessibilityRole="radio" accessibilityState={{checked:status===value}} aria-checked={status===value} onPress={()=>{setStatus(value);setPage(1);}} style={styles.button}>
        {label(t(value==='all'?'deck.creator.statusAll':`deck.labels.${value}`))}</Pressable>)}</View>
      {query||type!=='all'||status!=='all'?button(t('deck.actions.clearFilters'),()=>{setQuery('');setType('all');setStatus('all');setPage(1);}):null}
      {!filtered.length&&!loading?label(t(catalog.length?'deck.creator.noResults':'deck.creator.empty')):null}
      {visible.map(deck=>{const system=isSystemDeckDisplay(deck),disabled=busy===deck.id;return <View key={deck.id} testID={`native-deck-work-${deck.id}`} style={[styles.row,{borderColor:colors['color-border-paper']}]}>
        <View style={styles.identity}><DeckAgentIcon name={deck.icon||'brain'} color={deckAgentColor(deck.color||'blue',colors)}/><Pressable accessibilityRole="button" accessibilityLabel={`${t('deck.actions.edit')} ${deck.name}`} disabled={system||disabled} accessibilityState={{disabled:system||disabled}} style={styles.grow} onPress={()=>setEditorId(deck.id)}>
          {label(`${deck.name}${system?` · ${t('deck.labels.system')}`:''}`)}{label(deck.description||t('deck.labels.noDescription'),true)}{label(`${t('deck.labels.agentType.chat')} · ${t('deck.labels.agentCount',{count:deck.voice_count||deck.voices?.length||0})}`,true)}
          {deck.deck_version_capability?label(`${deck.deck_version?`内容 v${deck.deck_version}`:'未提交版本'}${deck.deck_version_dirty?` · 草稿 r${deck.draft_revision}`:''}`,true):null}{label(formatDate(deck.updated_at),true)}
        </Pressable>{!system?<Switch accessibilityLabel={t(deck.enabled?'deck.actions.disableDeck':'deck.actions.enableDeck',{deck:deck.name})} value={deck.enabled} disabled={disabled} onValueChange={()=>{void saveDeck(deck.id,{enabled:!deck.enabled}).catch(()=>undefined);}}/>:null}</View>
        {!system?<>{button(t('deck.actions.more',{deck:deck.name}),()=>setMenu(current=>current===deck.id?null:deck.id),disabled)}{menu===deck.id?<View style={styles.wrap}>
          {button(t('deck.actions.edit'),()=>{setMenu(null);setEditorId(deck.id);},disabled)}{deck.parent_id?button(t('deck.actions.sync'),()=>{setMenu(null);void sync(deck.id).catch(()=>undefined);},disabled):null}
          {button(t('deck.actions.relatedConversations'),()=>openRelated(deck),disabled)}{button(t('deck.actions.delete'),()=>{setMenu(null);void removeDeck(deck.id).catch(()=>undefined);},disabled)}
        </View>:null}</>:null}
      </View>;})}
      {pages>1?<View style={styles.wrap} accessibilityLabel={t('deck.pagination.ariaLabel')}>{button(t('deck.pagination.previous'),()=>setPage(value=>Math.max(1,value-1)),page===1)}{label(t('deck.pagination.summary',{page,pages}))}{button(t('deck.pagination.next'),()=>setPage(value=>Math.min(pages,value+1)),page===pages)}</View>:null}
      {refreshing||loading?<ActivityIndicator/>:null}
    </ScrollView>:<>
      {operationError?<View accessibilityRole="alert">{label(operationError)}</View>:null}
      <DeckLaunchScreen decks={decks} active={active} loading={loading||refreshing} error={error} onRefresh={()=>{void refresh();}} onTryDeck={onTryDeck}
        onOpenSettings={()=>setWork(true)} onCreateDeck={()=>{void create();}} creatingDeck={creating} onEditDeck={id=>{owned(id);setEditorId(id);}}/>
    </>}
    {editor?<DeckEditorModal key={editor.id} active={active} deck={editor} isSystem={isSystemDeckDisplay(editor)} creatingVoiceId={creatingVoice} selectedVoiceId={selected[editor.id]??editor.voices?.find(voice=>voice.enabled)?.id??editor.voices?.[0]?.id??null}
      onSelectVoice={id=>setSelected(current=>({...current,[editor.id]:id}))} transport={read} onClose={()=>setEditorId(null)} onAddVoice={addVoice} onUpdateDeck={saveDeck} onUpdateVoice={saveVoice} onToggleVoice={(id,enabled)=>saveVoice(id,{enabled:!enabled})}
      onDeleteVoice={removeVoice} onVersionChanged={async()=>{await onRefresh();}} onChatWithDeck={useVoice}/>:null}
    <Modal visible={active&&related!==null} animationType="slide" presentationStyle="fullScreen" onRequestClose={closeRelated}>
      <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}><ScrollView contentContainerStyle={styles.body}>
        <View style={styles.wrap}>{label(related?.name??'')}{button(t('deck.related.close'),closeRelated)}</View><InkLabel accessibilityRole="header" style={[styles.title,{color:colors['color-text-primary']}]}>{t('deck.related.title')}</InkLabel>
        {label(t('deck.related.description'))}{relatedError?<View accessibilityRole="alert">{label(relatedError)}{button(t('deck.actions.retry'),()=>{if(related)void loadRelated(related);},relatedLoading)}</View>:null}
        {threads.map(row=><View key={row.id} style={[styles.row,{borderColor:colors['color-border-paper']}]}>{label(row.title||t('chat.history.fallbackTitle'))}{label(formatDate(row.updated_at),true)}
          {button(t('deck.related.delete'),()=>{void removeThread(row);},deletingThread!==null)}</View>)}
        {relatedLoading?<ActivityIndicator/>:!threads.length?label(t('deck.related.emptyTitle')):null}
        {hasMore?button(t('deck.related.loadMore'),()=>{if(related)void loadRelated(related,threads.length);},relatedLoading):null}
      </ScrollView></SafeAreaView>
    </Modal>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minWidth:0},grow:{flex:1,minWidth:0},body:{padding:16,paddingBottom:64,gap:14,maxWidth:920,width:'100%',alignSelf:'center'},title:{fontSize:24,fontWeight:'600'},
  wrap:{flexDirection:'row',flexWrap:'wrap',gap:8,alignItems:'center'},button:{minHeight:44,paddingHorizontal:12,paddingVertical:10,borderWidth:StyleSheet.hairlineWidth,borderRadius:8,justifyContent:'center'},input:{minHeight:44,borderWidth:1,borderRadius:8,padding:12,fontFamily:'Excalifont',fontSize:16},
  row:{paddingVertical:12,gap:10,borderBottomWidth:StyleSheet.hairlineWidth},identity:{flexDirection:'row',alignItems:'center',gap:12}});
