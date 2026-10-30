// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original caller-owned Deck/Agent catalog, selected Agent and selection callback.
// [Output] Native anchored Agent popup with the original grouping, prefix search and labels.
// [Pos] Platform presentation counterpart; no loading, persistence, permissions or business submission ownership.
import {useEffect,useMemo,useRef,useState} from 'react';
import {AccessibilityInfo,findNodeHandle,Keyboard,Modal,Pressable,ScrollView,StyleSheet,TextInput,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {agentLabel,deckLabel,enabledAgentsOf,groupDeckAgents,type DeckAgentSelection,type DeckChatSelectorProps} from './deckAgentSelection';
import DeckAgentIcon,{deckAgentColor} from './DeckAgentIcon.native';
export type {DeckAgentSelection} from './deckAgentSelection';
type Anchor={x:number;y:number;width:number;height:number};
export default function DeckChatSelector({decks,selectedAgentId,onChange,loading=false,error,allowNone=true,variant='compact',noneLabel,triggerLabel,unavailableSelectionLabel}:DeckChatSelectorProps) {
  const {t,i18n}=useTranslation();const language=(i18n.language || 'en').split('-')[0];
  const colors=useInkColors(),window=useWindowDimensions();
  const trigger=useRef<View>(null),search=useRef<TextInput>(null);
  const [anchor,setAnchor]=useState<Anchor|null>(null),[query,setQuery]=useState(''),[active,setActive]=useState(0),[keyboardTop,setKeyboardTop]=useState<number|null>(null);
  const groups=useMemo(()=>groupDeckAgents(decks,query,language),[decks,query,language]);
  const options=useMemo(()=>[...(allowNone?[undefined]:[]),...groups.flatMap(group=>group.agents.map(agent=>({deckId:group.deck.id,agentId:agent.id})))],[allowNone,groups]);
  const selected=decks.flatMap(deck=>enabledAgentsOf(deck).map(agent=>({deck,agent}))).find(item=>item.agent.id===selectedAgentId);
  const selectedLabel=selected?agentLabel(selected.agent,language):selectedAgentId && unavailableSelectionLabel?unavailableSelectionLabel:noneLabel ?? t('chat.deck.noneAgent');
  useEffect(()=>{
    if(!anchor)return;
    const show=Keyboard.addListener('keyboardDidShow',event=>setKeyboardTop(event.endCoordinates.screenY));
    const hide=Keyboard.addListener('keyboardDidHide',()=>setKeyboardTop(null));
    return()=>{show.remove();hide.remove();};
  },[Boolean(anchor)]);
  function close() {
    setAnchor(null);setQuery('');setKeyboardTop(null);
    requestAnimationFrame(()=>{const tag=findNodeHandle(trigger.current);if(tag)AccessibilityInfo.setAccessibilityFocus(tag);});
  }
  function choose(selection:DeckAgentSelection|undefined) {onChange?.(selection);close();}
  function open() {
    setQuery('');setKeyboardTop(Keyboard.metrics()?.screenY ?? null);
    setActive(Math.max(0,options.findIndex(option=>option?.agentId===selectedAgentId)));
    trigger.current?.measureInWindow((x,y,width,height)=>setAnchor({x,y,width,height}));
  }
  const bottom=Math.min(window.height,keyboardTop ?? window.height),margin=8;
  const above=anchor?Math.max(0,Math.min(anchor.y,bottom)-margin):0;
  const below=anchor?Math.max(0,bottom-anchor.y-anchor.height-margin):0;
  const up=above>below,space=up?above:below;
  const width=Math.min(variant==='dream'?Math.max(300,anchor?.width ?? 0):300,window.width-margin*2);
  const maxHeight=Math.max(0,Math.min(384,space-6));
  const optionStyle=(isActive:boolean)=>[styles.option,{backgroundColor:isActive?colors['color-bg-hover']:'transparent'}];
  return <View style={variant==='dream'?{width:'100%'}:styles.root}>
    <Pressable ref={trigger} accessibilityRole="button" accessibilityLabel={triggerLabel ?? t('chat.deck.selectAgentAria')} accessibilityHint={error || t('chat.deck.selectAgentTitle')} accessibilityState={{expanded:!!anchor,disabled:loading}} disabled={loading} onPress={open}
      style={[styles.trigger,variant==='dream'?{width:'100%'}:null,{borderColor:colors[error?'color-state-error':'color-border-paper'],backgroundColor:colors['color-bg-app']}]}>
      <InkLabel style={{fontSize:12.16,color:colors['color-text-muted']}}>{triggerLabel ?? 'Agent'}</InkLabel>
      <InkLabel numberOfLines={1} style={{maxWidth:160,flexShrink:1,fontSize:12.16,color:colors['color-text-primary']}}>{loading?t('chat.deck.loadingAgents'):selectedLabel}</InkLabel>
      <InkLabel style={{fontSize:9.6,color:colors['color-text-muted']}}>▾</InkLabel>
    </Pressable>
    <Modal transparent visible={!!anchor} animationType="none" onRequestClose={close} onShow={()=>search.current?.focus()} supportedOrientations={['portrait','landscape-left','landscape-right']}>
      <View style={styles.overlay} onAccessibilityEscape={close}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={close} />
        {anchor?<View accessibilityViewIsModal accessibilityLabel={t('chat.deck.agentListAria')}
          style={[styles.popup,{left:Math.min(Math.max(margin,anchor.x),window.width-width-margin),width,maxHeight,
            ...(up?{bottom:window.height-Math.min(anchor.y,bottom)+6}:{top:anchor.y+anchor.height+6}),
            backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-neutral'],shadowColor:colors['color-shadow-medium']}]}>
          <TextInput ref={search} accessibilityLabel={t('chat.deck.searchAgentPlaceholder')} placeholder={t('chat.deck.searchAgentPlaceholder')} placeholderTextColor={colors['color-text-muted']}
            value={query} onChangeText={value=>{setQuery(value);setActive(0);}} returnKeyType="done" autoCorrect={false} autoCapitalize="none"
            onSubmitEditing={()=>{if(options.length)choose(options[active] ?? options[0]);}}
            onKeyPress={({nativeEvent})=>{if(nativeEvent.key==='Escape')close();else if(nativeEvent.key==='ArrowDown')setActive(current=>Math.min(current+1,options.length-1));else if(nativeEvent.key==='ArrowUp')setActive(current=>Math.max(current-1,0));}}
            style={[styles.search,{borderColor:colors['color-border-neutral'],backgroundColor:colors['color-bg-paper'],color:colors['color-text-primary']}]} />
          <ScrollView keyboardShouldPersistTaps="handled" style={{flexShrink:1,maxHeight:320}}>
            {allowNone?<Pressable accessibilityRole="button" accessibilityState={{selected:!selectedAgentId}} onPress={()=>choose(undefined)} style={optionStyle(active===0)}>
              <InkLabel style={{width:14,color:!selectedAgentId?colors['color-action-link']:'transparent'}}>✓</InkLabel>
              <InkLabel style={{fontSize:13,fontStyle:'italic',color:colors['color-text-muted']}}>{noneLabel ?? t('chat.deck.noneAgent')}</InkLabel>
            </Pressable>:null}
            {groups.map(({deck,agents})=><View key={deck.id}>
              <InkLabel accessibilityRole="header" style={[styles.group,{color:colors['color-text-muted']}]}>{deckLabel(deck,language).toUpperCase()}</InkLabel>
              {agents.map(agent=>{
                const index=options.findIndex(option=>option?.agentId===agent.id),selected=selectedAgentId===agent.id;
                return <Pressable key={agent.id} accessibilityRole="button" accessibilityLabel={agentLabel(agent,language)} accessibilityState={{selected}} onPress={()=>choose({deckId:deck.id,agentId:agent.id})} style={[...optionStyle(index===active),{marginLeft:8}]}>
                  <InkLabel style={{width:14,color:selected?colors['color-action-link']:'transparent'}}>✓</InkLabel>
                  <DeckAgentIcon name={agent.icon || 'brain'} color={deckAgentColor(agent.color,colors)} />
                  <InkLabel numberOfLines={1} style={{fontSize:13,flexShrink:1,color:colors['color-text-body']}}>{agentLabel(agent,language)}</InkLabel>
                </Pressable>;
              })}
            </View>)}
            {!groups.length && query.trim()?<InkLabel style={[styles.empty,{color:colors['color-text-muted']}]}>{t('chat.deck.noAgentMatch')}</InkLabel>:null}
          </ScrollView>
        </View>:null}
      </View>
    </Modal>
  </View>;
}
const styles=StyleSheet.create({
  root:{alignSelf:'flex-start',maxWidth:'100%'},trigger:{minHeight:44,maxWidth:240,paddingHorizontal:11.2,borderWidth:1,borderRadius:999,flexDirection:'row',alignItems:'center',gap:5.6},
  overlay:{flex:1},popup:{position:'absolute',borderWidth:1,borderRadius:8,padding:6,gap:4,shadowOpacity:1,shadowRadius:12,shadowOffset:{width:0,height:4}},
  search:{minHeight:44,borderWidth:1,borderRadius:6,paddingHorizontal:8,paddingVertical:6,fontSize:12,fontFamily:'Excalifont'},
  option:{minHeight:44,paddingVertical:7,paddingHorizontal:10,borderRadius:6,flexDirection:'row',alignItems:'center',gap:8},
  group:{paddingTop:8,paddingBottom:4,paddingHorizontal:10,fontSize:10,fontWeight:'700',letterSpacing:1.12},empty:{paddingVertical:8,paddingHorizontal:10,fontSize:12,fontStyle:'italic'},
});
