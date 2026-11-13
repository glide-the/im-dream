// [Sync] 2026-11-13: use native UI text metrics for Chinese menu controls without changing shared content typography.
// SPDX-License-Identifier: MIT
// Copyright (c) 2025 better-chatbot. Native adaptation of tool-select/agent-selector.tsx; notice: frontend/third-party/better-chatbot/LICENSE.
// [Input] Original IM Agent directory, selection and caller callbacks.
// [Output] Native Agent submenu with the migrated grouped selection and original IM labels.
// [Pos] Chat presentation only; no Thread creation, catalog loading or runtime ownership.
import {useMemo,useState} from 'react';
import {Pressable,StyleSheet,Text,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import useInkColors from '../../../../src/components/useInkColors.native';
import DeckAgentIcon from '../deck/DeckAgentIcon.native';
import {agentLabel,deckLabel,groupDeckAgents,type DeckChatSelectorProps,type DeckAgentSelection} from '../deck/deckAgentSelection';
export default function ComposerAgentSelector({selection,onBack,onSelected}:{selection:DeckChatSelectorProps;onBack:()=>void;onSelected:()=>void}){
  const {t,i18n}=useTranslation(),c=useInkColors(),[query,setQuery]=useState('');
  const language=(i18n.language||'en').split('-')[0],groups=useMemo(()=>groupDeckAgents(selection.decks,query,language),[selection.decks,query,language]);
  const choose=(value:DeckAgentSelection|undefined)=>{if(!selection.onChange)return;selection.onChange(value);onSelected();};
  return <View style={s.body}>
    <Pressable accessibilityRole="button" onPress={onBack} style={s.row}><Text style={{color:c['color-text-primary'],fontSize:14,lineHeight:22}}>{'‹ '+t('chat.agentTools.back')}</Text></Pressable>
    <TextInput autoFocus accessibilityLabel={t('chat.deck.searchAgentPlaceholder')} placeholder={t('chat.deck.searchAgentPlaceholder')} placeholderTextColor={c['color-text-muted']} value={query} onChangeText={setQuery} autoCorrect={false} autoCapitalize="none" style={[s.search,{color:c['color-text-primary'],borderColor:c['color-border-paper']}]}/>
    {selection.error?<Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{selection.error}</Text>:null}
    <View accessibilityRole="radiogroup" accessibilityLabel={t('chat.deck.agentListAria')}>
      {selection.allowNone!==false?<Pressable accessibilityRole="radio" accessibilityState={{checked:!selection.selectedAgentId}} onPress={()=>choose(undefined)} style={s.row}><Text style={{color:c['color-text-primary'],fontSize:14,lineHeight:22}}>{(!selection.selectedAgentId?'✓ ':'')+(selection.noneLabel??t('chat.deck.noneAgent'))}</Text></Pressable>:null}
      {groups.map(({deck,agents})=><View key={deck.id}>
        <Text accessibilityRole="header" style={{fontSize:12,lineHeight:20,fontWeight:'500',color:c['color-text-muted'],marginTop:12}}>{deckLabel(deck,language)}</Text>
        {agents.map(agent=><Pressable key={agent.id} accessibilityRole="radio" accessibilityLabel={agentLabel(agent,language)} accessibilityState={{checked:selection.selectedAgentId===agent.id}} onPress={()=>choose({deckId:deck.id,agentId:agent.id})} style={[s.row,{backgroundColor:selection.selectedAgentId===agent.id?c['color-bg-hover']:'transparent'}]}>
          <Text style={{width:14,color:c['color-text-primary']}}>{selection.selectedAgentId===agent.id?'✓':''}</Text><DeckAgentIcon name={agent.icon||'brain'} color={c['color-text-primary']}/><Text numberOfLines={1} style={{flexShrink:1,fontSize:14,lineHeight:22,color:c['color-text-primary']}}>{agentLabel(agent,language)}</Text>
        </Pressable>)}
      </View>)}
      {groups.length===0?<Text style={{color:c['color-text-muted']}}>{t('chat.deck.noAgentMatch')}</Text>:null}
    </View>
  </View>;
}
const s=StyleSheet.create({body:{gap:10},row:{minHeight:44,flexDirection:'row',alignItems:'center',gap:8,paddingHorizontal:10,borderRadius:9},search:{fontSize:14,lineHeight:22,minHeight:44,borderWidth:1,borderRadius:10,padding:12}});
