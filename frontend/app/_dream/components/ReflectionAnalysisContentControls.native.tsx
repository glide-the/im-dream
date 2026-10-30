// [Input] Original controlled analysis selection and shared Notion/Agent candidate state.
// [Output] Native analysis-content controls preserving ready/stale rules, scope and Agent selection.
// [Pos] Concrete native presentation; opening only reads existing resource/catalog APIs.
// [Sync] 2026-10-29: reuse the Web state, original Deck selector and local HTTP; no sync or model launch.
import {useEffect,useRef,useState} from 'react';
import {Modal,Pressable,SafeAreaView,ScrollView,StyleSheet,Switch,Text,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import useInkColors from '../../../src/components/useInkColors.native';
import {clientFetch} from '../../../src/platform/transport';
import type {ReflectionAnalysisContentOptions,ReflectionsApi} from '../api/reflectionsApi';
import {listDecksWithVoices} from '../api/deckReadApi';
import useReflectionAnalysisContent from '../hooks/useReflectionAnalysisContent';
import DeckChatSelector from './deck/DeckChatSelector.native';
export default function ReflectionAnalysisContentControls({value,onChange,authenticated,api,transport,inline=false,active=true}:{value:ReflectionAnalysisContentOptions;onChange:(value:ReflectionAnalysisContentOptions)=>void;authenticated:boolean;api:Pick<ReflectionsApi,'getReflectionAnalysisContent'>;transport?:typeof fetch;inline?:boolean;active?:boolean}) {
  const [open,setOpen]=useState(false),{i18n}=useTranslation(),zh=i18n.language.startsWith('zh'),c=useInkColors();
  const readDecks=useRef(()=>listDecksWithVoices(transport??clientFetch)).current;
  const state=useReflectionAnalysisContent({value,authenticated,expanded:active&&(inline||open),readCandidates:api.getReflectionAnalysisContent,readDecks});
  useEffect(()=>{if(!active)setOpen(false);},[active]);
  const body=<View style={s.body}>
    <View style={s.row}><Switch accessibilityLabel={zh?'将 Notion 加入分析':'Include Notion in analysis'} value={value.include_notion} disabled={!state.ready&&!value.include_notion}
      onValueChange={checked=>onChange({...value,include_notion:checked,connector_id:checked?state.candidates?.connector_id:undefined,snapshot_version:checked?state.candidates?.snapshot_version??undefined:undefined})}/><Text style={{color:c['color-text-primary']}}>{zh?'将 Notion 加入分析':'Include Notion in analysis'}</Text></View>
    <Text accessibilityLiveRegion="polite" style={{color:c['color-text-secondary'],lineHeight:21}}>{state.status}</Text>
    <DeckChatSelector decks={state.decks} selectedAgentId={value.agent_id} loading={state.deckLoading}
      error={state.deckError?(zh?'分析 Agent 加载失败':'Analysis Agents could not be loaded'):undefined} unavailableSelectionLabel={zh?'所选 Agent 不可用':'Selected Agent unavailable'} noneLabel={zh?'默认分析':'Default analysis'} triggerLabel={zh?'分析 Agent':'Analysis Agent'}
      onChange={selection=>onChange({...value,deck_id:selection?.deckId,agent_id:selection?.agentId})}/>
    <Text style={{color:c['color-text-secondary']}}>{zh?'所选 Agent 提供本次分析视角。':'The selected Agent provides the perspective for this analysis.'}</Text>
    {state.unavailableAgent?<Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{zh?'所选分析 Agent 已不可用，请重新选择。':'The selected analysis Agent is unavailable. Select it again.'}</Text>:null}
    {state.deckError?<Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{zh?'分析 Agent 加载失败；仍可使用默认分析。':'Analysis Agents could not be loaded. Default analysis remains available.'}</Text>:null}
    {authenticated?<Pressable accessibilityRole="button" disabled={state.loading||state.deckLoading} onPress={()=>state.setRevision(current=>current+1)} style={s.button}><Text style={{color:c['color-action-primary']}}>{zh?'重新加载':'Reload'}</Text></Pressable>:null}
  </View>;
  if(inline)return body;
  return <View><Pressable accessibilityRole="button" accessibilityState={{expanded:open}} onPress={()=>setOpen(true)} style={[s.button,{borderColor:c['color-border-paper'],borderWidth:StyleSheet.hairlineWidth,borderRadius:24}]}><Text style={{color:c['color-text-body']}}>{zh?'分析内容':'Analysis content'} ▾</Text></Pressable>
    <Modal visible={active&&open} animationType="slide" presentationStyle="pageSheet" onRequestClose={()=>setOpen(false)}>
      <SafeAreaView style={{flex:1,backgroundColor:c['color-bg-app']}}><View style={[s.row,{padding:16,justifyContent:'space-between'}]}><Text accessibilityRole="header" style={{fontSize:20,color:c['color-text-primary']}}>{zh?'分析内容':'Analysis content'}</Text><Pressable accessibilityRole="button" onPress={()=>setOpen(false)} style={s.button}><Text style={{color:c['color-text-primary']}}>{zh?'关闭':'Close'}</Text></Pressable></View><ScrollView contentContainerStyle={s.body}>{body}</ScrollView></SafeAreaView>
    </Modal>
  </View>;
}
const s=StyleSheet.create({body:{padding:18,gap:12},row:{flexDirection:'row',alignItems:'center',gap:10,flexWrap:'wrap'},button:{minHeight:44,paddingHorizontal:14,paddingVertical:12,justifyContent:'center'}});
