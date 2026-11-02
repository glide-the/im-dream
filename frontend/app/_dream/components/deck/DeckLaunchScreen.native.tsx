// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-29: keep the selected preview from the full catalog after editing; home eligibility remains unchanged.
// [Sync] 2026-10-29: restore original create/settings and user maintenance entry callbacks; keep system preview read-only.
// [Input] Original Deck catalog snapshot, read/retry state and Chat selection callback.
// [Output] Native Deck home and preview using original labels, visibility and draft handoff.
// [Pos] Native launcher/preview presentation; App owns reads, Chat and backend lifecycle.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,BackHandler,Platform,Pressable,ScrollView,StyleSheet,TextInput,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {Deck,Voice} from '../../api/voiceApi';
import {DECK_ENABLED_LAUNCH_LIMIT} from '../../constants/deck';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import DeckAgentIcon,{DeckPlayIcon,deckAgentColor} from './DeckAgentIcon.native';
import {isSystemDeckDisplay,isDeckHomeVisible,matchesDeckHomeQuery,deckPreviewVoices,deckExamplePrompt} from './deckPresentation';

interface Props {
  decks:Deck[];active:boolean;loading:boolean;error?:string;onRefresh:()=>void;
  onTryDeck:(deck:Deck,voice:Voice,input?:string)=>void;
  onOpenSettings?:()=>void;onCreateDeck?:()=>void;creatingDeck?:boolean;onEditDeck?:(id:string)=>void;
}
export default function DeckLaunchScreen({decks,active,loading,error,onRefresh,onTryDeck,onOpenSettings,onCreateDeck,creatingDeck,onEditDeck}:Props) {
  const {t,i18n}=useTranslation();
  const colors=useInkColors(),wide=useWindowDimensions().width>=768;
  const [query,setQuery]=useState(''),[agentType,setAgentType]=useState<'all'|'chat'>('all'),[previewId,setPreviewId]=useState<string|null>(null);
  const homeScroll=useRef<ScrollView>(null),homeOffset=useRef(0);
  const eligible=decks.filter(deck=>deck.agent_type!=='dream' && isDeckHomeVisible(deck));
  const visible=eligible.filter(deck=>matchesDeckHomeQuery(deck,query) && (agentType==='all'||deck.agent_type===agentType));
  const preview=decks.find(deck=>deck.id===previewId&&deck.agent_type!=='dream');
  const back=()=>{const y=homeOffset.current;setPreviewId(null);requestAnimationFrame(()=>homeScroll.current?.scrollTo({y,animated:false}));};
  useEffect(()=>{
    if(Platform.OS!=='android' || !active || !preview)return;
    const subscription=BackHandler.addEventListener('hardwareBackPress',()=>{back();return true;});
    return()=>subscription.remove();
  },[active,preview?.id]);
  const label=(text:string,kind:'primary'|'secondary'|'muted'='secondary',style:object={})=><InkLabel style={[{color:colors[`color-text-${kind}`]},style]}>{text}</InkLabel>;
  const tryDeck=(deck:Deck,voice:Voice,input?:string)=>{if(deck.agent_type!=='dream')onTryDeck(deck,voice,input);};
  if(preview) {
    const {voices,trialVoice,examples}=deckPreviewVoices(preview),system=isSystemDeckDisplay(preview);
    const version=system?t('deck.labels.systemBuiltIn'):(preview.deck_version?t('deck.labels.contentVersion',{version:preview.deck_version}):t('deck.version.unpublished'));
    const updated=preview.updated_at?new Intl.DateTimeFormat(i18n.resolvedLanguage==='zh'?'zh-CN':'en-US',{year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(preview.updated_at)):t('deck.labels.updateUnknown');
    return <ScrollView key={preview.id} testID="native-deck-preview" style={styles.fill} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" onAccessibilityEscape={back}>
      <Pressable accessibilityRole="button" onPress={back} style={styles.back}>{label(`‹ ${t('deck.preview.back')}`)}</Pressable>
      <View style={styles.previewHeader}>
        <View style={[styles.heroIcon,{backgroundColor:colors['color-text-primary'],borderColor:colors['color-border-paper']}]}><DeckAgentIcon name={preview.icon || 'brain'} size={40} color={colors['color-bg-app']}/></View>
        {label(preview.name,'primary',styles.title)}
        {label(preview.description || t('deck.labels.noDescription'))}
        {!system&&onEditDeck?<Pressable accessibilityRole="button" onPress={()=>onEditDeck(preview.id)} style={styles.back}>{label(t('deck.actions.edit'))}</Pressable>:null}
        <Pressable accessibilityRole="button" accessibilityState={{disabled:!trialVoice}} disabled={!trialVoice} onPress={()=>{if(trialVoice)tryDeck(preview,trialVoice);}}
          style={[styles.tryButton,{backgroundColor:colors['color-text-primary'],opacity:trialVoice?1:0.45}]}><DeckPlayIcon color={colors['color-bg-app']}/><InkLabel style={{color:colors['color-bg-app']}}>{t('deck.preview.tryNow')}</InkLabel></Pressable>
      </View>
      <View accessibilityLabel={t('deck.preview.examples')} style={[styles.examples,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>
        {examples.length?examples.map(voice=>{
          const prompt=deckExamplePrompt(preview,voice,t('deck.labels.noDescription'));
          return <Pressable key={voice.id} accessibilityRole="button" accessibilityLabel={`${voice.name}: ${prompt}`} accessibilityState={{disabled:!voice.enabled}} disabled={!voice.enabled}
            onPress={()=>tryDeck(preview,voice,prompt)} style={[styles.example,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface-solid'],opacity:voice.enabled?1:0.45}]}>
            <DeckAgentIcon name={voice.icon || preview.icon || 'brain'} size={17} color={colors['color-text-primary']}/>
            {label(voice.name,'primary',{fontSize:16})}{label(prompt,'secondary',{fontSize:13})}
          </Pressable>;
        }):<View style={styles.example}>{label(preview.name,'primary')}{label(preview.description || t('deck.preview.defaultDescription',{deck:preview.name}))}</View>}
      </View>
      {label(preview.description || t('deck.preview.defaultDescription',{deck:preview.name}))}
      <View style={styles.section}>
        {label(t('deck.preview.agentsTitle',{count:voices.length}),'primary',styles.sectionTitle)}
        {voices.length?voices.map(voice=><View key={voice.id} style={[styles.agent,{borderColor:colors['color-border-paper']}]}>
          <DeckAgentIcon name={voice.icon || 'brain'} size={18} color={colors['color-text-secondary']}/>
          <View style={styles.fill}>{label(voice.name,'primary')}{label(t(voice.enabled?'deck.labels.enabled':'deck.labels.disabled'),'muted',{fontSize:12})}</View>
        </View>):label(t('deck.preview.noAgents'))}
      </View>
      <View style={styles.section}>
        {label(t('deck.preview.infoTitle'),'primary',styles.sectionTitle)}
        {[[t('deck.preview.infoDeveloper'),t(system?'deck.preview.systemDeveloper':'deck.preview.userDeveloper')],[t('deck.preview.infoType'),t('deck.labels.agentType.chat')],
          [t('deck.preview.infoVersion'),version],[t('deck.preview.infoRuntime'),preview.deck_plugin_version || t('deck.labels.updateUnknown')],[t('deck.preview.infoUpdated'),updated]].map(([name,value])=><View key={name} style={[styles.info,{borderColor:colors['color-border-paper']}]}>{label(name,'muted',{flex:1})}{label(value,'primary',{flex:1,textAlign:'right'})}</View>)}
      </View>
    </ScrollView>;
  }
  return <ScrollView ref={homeScroll} testID="native-deck-home" style={styles.fill} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" scrollEventThrottle={100}
    onScroll={event=>{if(active)homeOffset.current=event.nativeEvent.contentOffset.y;}}>
    <View style={styles.topbar}>{label(t('deck.home.sectionLabel'),'primary',{fontSize:12})}
      <View style={styles.topActions}>
      {onOpenSettings?<Pressable accessibilityRole="button" accessibilityLabel={t('deck.home.openSettings')} onPress={onOpenSettings} style={styles.back}>{label('⚙')}</Pressable>:null}
      {onCreateDeck?<Pressable accessibilityRole="button" disabled={creatingDeck} accessibilityState={{disabled:creatingDeck}} onPress={onCreateDeck} style={styles.back}>{label(t(creatingDeck?'deck.actions.creating':'deck.actions.createMenu'))}</Pressable>:null}
      <Pressable accessibilityRole="button" accessibilityLabel={t('deck.actions.refresh')} accessibilityState={{disabled:loading}} disabled={loading} onPress={onRefresh} style={styles.iconButton}>
        {loading?<ActivityIndicator color={colors['color-text-secondary']}/>:label('↻','primary',{fontSize:24})}
      </Pressable>
      </View>
    </View>
    <View style={styles.previewHeader}>{label(t('deck.home.title'),'primary',styles.title)}{label(t('deck.home.launchDescription'))}</View>
    <TextInput accessibilityLabel={t('deck.home.launchSearchLabel')} placeholder={t('deck.creator.searchPlaceholder')} placeholderTextColor={colors['color-text-muted']} value={query} onChangeText={setQuery}
      autoCorrect={false} autoCapitalize="none" returnKeyType="search" style={[styles.search,{color:colors['color-text-primary'],borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-paper']}]} />
    {error?<View accessibilityRole="alert">{label(error,'primary')}<Pressable accessibilityRole="button" onPress={onRefresh} disabled={loading} style={styles.back}>{label(t('deck.actions.retry'))}</Pressable></View>:null}
    <View style={styles.section}>{label(t('deck.home.enabledTitle'),'primary',styles.sectionTitle)}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.shortcuts}>
        {eligible.slice(0,DECK_ENABLED_LAUNCH_LIMIT).map(deck=><Pressable key={deck.id} accessibilityRole="button" accessibilityLabel={t(isSystemDeckDisplay(deck)?'deck.home.systemDeckLabel':'deck.home.openDeck',{deck:deck.name})}
          onPress={()=>setPreviewId(deck.id)} style={[styles.shortcut,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-paper']}]}>
          <DeckAgentIcon name={deck.icon || 'brain'} size={24} color={deckAgentColor(deck.color || 'blue',colors)}/>
        </Pressable>)}
      </ScrollView>
      {!eligible.length && !loading?label(t('deck.home.availableEmpty')):null}
    </View>
    {eligible.length?<>
      <View accessibilityRole="tablist" accessibilityLabel={t('deck.creator.agentTypeFilter')} style={styles.filters}>
        {(['all','chat'] as const).map(type=><Pressable key={type} accessibilityRole="tab" accessibilityState={{selected:type===agentType}} onPress={()=>setAgentType(type)} style={[styles.filter,{backgroundColor:agentType===type?colors['color-bg-hover']:'transparent'}]}>
          {label(`${t(`deck.creator.agentTypeTabs.${type}`)} ${eligible.filter(deck=>type==='all'||deck.agent_type===type).length}`,'primary')}
        </Pressable>)}
      </View>
      {!visible.length?<View style={styles.section}>{label(t('deck.creator.noResults'))}<Pressable accessibilityRole="button" onPress={()=>{setQuery('');setAgentType('all');}} style={styles.back}>{label(t('deck.actions.clearFilters'))}</Pressable></View>:
        [false,true].map(system=><View key={String(system)} style={styles.section}>
          {label(t(system?'deck.home.systemListTitle':'deck.home.availableListTitle'),'primary',styles.sectionTitle)}
          <View style={styles.grid}>{visible.filter(deck=>isSystemDeckDisplay(deck)===system).map(deck=><Pressable key={deck.id} testID={`native-deck-card-${deck.id}`} accessibilityRole="button"
            accessibilityLabel={system?t('deck.home.systemDeckLabel',{deck:deck.name}):`${t('deck.actions.edit')} ${deck.name}`} onPress={()=>setPreviewId(deck.id)}
            style={[styles.card,{width:wide?'48%':'100%',borderColor:colors['color-border-paper']}]}>
            <View style={[styles.shortcut,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}><DeckAgentIcon name={deck.icon || 'brain'} size={24} color={deckAgentColor(deck.color || 'blue',colors)}/></View>
            <View style={styles.fill}>{label(deck.name,'primary',{fontSize:14})}{label(deck.description || t('deck.labels.noDescription'),'secondary',{fontSize:12})}
              {label(`${t('deck.labels.agentType.chat')} · ${system?t('deck.labels.systemBuiltIn'):t('deck.labels.contentVersion',{version:deck.deck_version})}`,'muted',{fontSize:11})}
            </View>{label('›','muted',{fontSize:20})}
          </Pressable>)}</View>
          {!visible.some(deck=>isSystemDeckDisplay(deck)===system)?label(t(system?'deck.home.systemListEmpty':'deck.home.availableListEmpty')):null}
        </View>)}
    </>:null}
  </ScrollView>;
}
const styles=StyleSheet.create({fill:{flex:1,minWidth:0},content:{width:'100%',maxWidth:920,alignSelf:'center',paddingHorizontal:16,paddingBottom:64,gap:16},
  topbar:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',minHeight:56},topActions:{flexDirection:'row',alignItems:'center',gap:4,flexShrink:1},iconButton:{width:44,height:44,alignItems:'center',justifyContent:'center'},
  previewHeader:{gap:16,paddingVertical:20},title:{fontSize:28,fontWeight:'700'},sectionTitle:{fontSize:16,fontWeight:'600'},section:{gap:12},
  search:{minHeight:44,paddingHorizontal:14,paddingVertical:10,borderWidth:1,borderRadius:8,fontFamily:'Excalifont',fontSize:14},shortcuts:{gap:8},shortcut:{width:44,height:44,alignItems:'center',justifyContent:'center',borderWidth:1,borderRadius:10.4},
  filters:{flexDirection:'row',gap:4},filter:{minHeight:44,paddingHorizontal:12,justifyContent:'center',borderRadius:7.2},grid:{flexDirection:'row',flexWrap:'wrap',justifyContent:'space-between'},
  card:{minHeight:96,flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:4,paddingVertical:14.4,borderBottomWidth:StyleSheet.hairlineWidth},
  back:{alignSelf:'flex-start',minHeight:44,paddingHorizontal:11.2,justifyContent:'center'},heroIcon:{width:73.6,height:73.6,borderWidth:1,borderRadius:17.6,alignItems:'center',justifyContent:'center'},
  tryButton:{minHeight:44,paddingVertical:8.8,paddingHorizontal:13.6,borderRadius:10.4,alignSelf:'flex-start',justifyContent:'center',flexDirection:'row',alignItems:'center',gap:6.72},
  examples:{gap:16,padding:16,borderWidth:1,borderRadius:17.6},example:{gap:8,padding:16,borderWidth:1,borderRadius:12,minHeight:96},
  agent:{flexDirection:'row',alignItems:'center',gap:12,paddingVertical:14,borderBottomWidth:StyleSheet.hairlineWidth},info:{flexDirection:'row',gap:16,paddingVertical:12,borderBottomWidth:StyleSheet.hairlineWidth},
});
