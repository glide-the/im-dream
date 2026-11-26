// [Sync] 2026-11-13: use native UI text metrics for Chinese menu controls without changing shared content typography.
// [Sync] 2026-11-13: grouped native navigation changes Thread tool choices without connection PATCH.
// SPDX-License-Identifier: MIT
// Copyright (c) 2025 better-chatbot. Native adaptation of tool-select/index.tsx; full notice: frontend/third-party/better-chatbot/LICENSE.
// [Sync] 2026-11-13: current-Agent trigger opens the migrated Agent/tools menu.
// [Input] Original composer mode, native transport and caller-owned resource navigation.
// [Output] Native searchable tools sheet with read-only connection state and Thread tool switches.
// [Pos] Chat tools presentation; native host, permissions and media execution retain their owners.
// [Sync] 2026-11-13: share service state with Web and close the sheet when its scene becomes inactive.
import {useEffect,useMemo,useState} from 'react';
import {ActivityIndicator,KeyboardAvoidingView,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,Text,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport';
import {createClaudeMcpApi} from '../../api/claudeMcpApi';
import useChatMcpCatalog from '../../hooks/useChatMcpCatalog';
import {toggleChatMcp} from '../../hooks/useChatToolSelection';
import {serverStatusLabel} from '../claude-mcp/mcpResourcePresentation';
import {buildToolChoiceOptions} from './useComposerDraft';
import type {ComposerToolsMenuProps} from './ComposerToolsMenu.types';
import ComposerAgentSelector from './ComposerAgentSelector.native';
import {selectedComposerAgent} from './composerAgentSelection';
import {agentLabel} from '../deck/deckAgentSelection';
import DeckAgentIcon from '../deck/DeckAgentIcon.native';

export default function ComposerToolsMenu(props:ComposerToolsMenuProps) {
  const {t,i18n}=useTranslation(),c=useInkColors(),[open,setOpen]=useState(false);
  const agent=selectedComposerAgent(props.agentSelection),label=props.agentSelection?.loading?t('chat.deck.loadingAgents'):agent?agentLabel(agent,(i18n.language||'en').split('-')[0]):props.agentSelection?.selectedAgentId?t('chat.agentTools.unavailable'):props.agentSelection?.noneLabel??t('chat.deck.noneAgent');
  useEffect(()=>{if(props.active===false)setOpen(false);},[props.active]);
  return <>
    <Pressable accessibilityRole="button" accessibilityLabel={t('chat.agentTools.trigger',{name:label})} accessibilityState={{expanded:open,disabled:props.disabled}} disabled={props.disabled} onPress={()=>setOpen(true)} style={[s.trigger,{backgroundColor:c['color-bg-app']}]}>
      <DeckAgentIcon name={agent?.icon||'brain'} color={c['color-text-secondary']}/><Text numberOfLines={1} style={{fontSize:13,lineHeight:20,flexShrink:1,color:c['color-text-secondary']}}>{label}</Text><Text style={{color:c['color-text-muted']}}>⌄</Text>
    </Pressable>
    {open?<ToolsSheet {...props} onClose={()=>setOpen(false)}/>:null}
  </>;
}
function ToolsSheet({toolChoice,onToolChoice,fullAccessEnabled,disabled,loading,onManageTools,agentSelection,tools=[],onToolsChange,onClose}:ComposerToolsMenuProps&{onClose:()=>void}) {
  const {t}=useTranslation(),c=useInkColors(),[query,setQuery]=useState(''),[choosingAgent,setChoosingAgent]=useState(false);
  const api=useMemo(()=>createClaudeMcpApi(clientFetch),[]);
  const state=useChatMcpCatalog(api);
  const text={color:c['color-text-primary'],fontSize:14,lineHeight:22,fontWeight:'400' as const},muted={color:c['color-text-muted'],fontSize:12,lineHeight:20};
  const button=(label:string,action:()=>void,blocked=false)=><Pressable accessibilityRole="button" disabled={blocked} accessibilityState={{disabled:blocked}} onPress={action} style={[s.button,{backgroundColor:c['color-bg-hover'],opacity:blocked ? 0.5 : 1}]}><Text style={text}>{label}</Text></Pressable>;
  return <Modal transparent animationType="slide" visible onRequestClose={onClose}>
    <KeyboardAvoidingView style={s.overlay} behavior={Platform.OS==='ios'?'padding':undefined}>
      <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={onClose}/>
      <SafeAreaView accessibilityViewIsModal onAccessibilityEscape={onClose} style={[s.sheet,{backgroundColor:c['color-bg-surface-solid'],borderColor:c['color-border-paper']}]}>
        <View style={s.header}><Text accessibilityRole="header" style={[text,{fontSize:16,lineHeight:24,fontWeight:'600'}]}>{t('chat.agentTools.title')}</Text>{button(t('chat.toolsMenu.close'),onClose)}</View>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.body}>
          {choosingAgent&&agentSelection?<ComposerAgentSelector selection={agentSelection} onBack={()=>setChoosingAgent(false)} onSelected={onClose}/>:<>
          {button(t('chat.agentTools.select')+' ›',()=>setChoosingAgent(true),!agentSelection?.onChange||!!agentSelection.loading||!!disabled)}
          <Text style={muted}>{t('chat.inputDock.toolModeAria')}</Text>
          {fullAccessEnabled?<Text style={text}>{t('chat.inputDock.fullAccess')}</Text>:<View accessibilityRole="radiogroup" style={s.row}>{buildToolChoiceOptions(t).map(option=><Pressable key={option.value} accessibilityRole="radio" accessibilityState={{checked:toolChoice===option.value,disabled:disabled||loading}} disabled={disabled||loading} onPress={()=>onToolChoice(option.value)} style={[s.button,{backgroundColor:c[toolChoice===option.value?'color-bg-hover':'color-bg-app']}]}><Text style={text}>{(toolChoice===option.value?'✓ ':'')+option.label}</Text></Pressable>)}</View>}
          <Text style={text}>{t('chat.toolsMenu.services')+(state.capability?.enabled&&!state.loading?` · ${tools.filter(tool=>tool.type==='mcp').length}`:'')}</Text>
          <TextInput accessibilityLabel={t('chat.toolsMenu.search')} placeholder={t('chat.toolsMenu.search')} placeholderTextColor={c['color-text-muted']} value={query} onChangeText={setQuery} autoCorrect={false} autoCapitalize="none" style={[s.search,text,{borderColor:c['color-border-paper']}]}/>
          <Text style={muted}>{t('chat.toolsMenu.scope')}</Text>
          {state.loading?<ActivityIndicator accessibilityLabel={t('chat.toolsMenu.loading')} color={c['color-text-primary']}/>:null}
          {state.capability&&!state.capability.enabled?<Text style={muted}>{t('chat.toolsMenu.unavailable')}</Text>:null}
          {state.capability?.enabled?state.servers.filter(server=>(server.display_name+' '+server.name).toLowerCase().includes(query.trim().toLowerCase())).map(server=>{
            const checked=tools.some(tool=>tool.type==='mcp'&&tool.server_name===server.name);
            const available=server.enabled&&(server.auth_state==='anonymous'||server.auth_state==='authenticated');
            const blocked=disabled||state.loading||!onToolsChange||(!available&&!checked);
            return <View key={server.name} style={[s.service,{borderColor:c['color-border-paper']}]}>
              <View style={{flex:1,minWidth:0,gap:4}}><Text numberOfLines={1} style={text}>{server.display_name||server.name}</Text>{!available?<Text style={muted}>{serverStatusLabel(server,server.state)}</Text>:null}</View>
              <Pressable accessibilityRole="switch" accessibilityLabel={server.display_name||server.name} accessibilityState={{checked,disabled:blocked}} disabled={blocked} onPress={()=>onToolsChange?.(toggleChatMcp(tools,server.name))} style={s.switchTarget}><View style={[s.switchTrack,{backgroundColor:c[checked?'color-text-primary':'color-text-muted']}]}><View style={[s.switchThumb,{backgroundColor:c['color-bg-paper'],transform:[{translateX:checked?14:0}]}]}/></View></Pressable>
            </View>;
          }):null}
          {!state.loading&&!state.error&&state.capability?.enabled&&!state.servers.some(server=>(server.display_name+' '+server.name).toLowerCase().includes(query.trim().toLowerCase()))?<Text style={muted}>{t(query?'chat.toolsMenu.noMatch':'chat.toolsMenu.empty')}</Text>:null}
          {state.error?<View style={{gap:8}}><Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{state.error}</Text>{button(t('chat.toolsMenu.retry'),()=>void state.load(),state.loading)}</View>:null}
          <Pressable accessibilityRole="switch" accessibilityLabel={t('chat.toolsMenu.audio')} accessibilityState={{checked:false,disabled:true}} disabled style={[s.button,{opacity:0.5,backgroundColor:c['color-bg-app']}]}><Text style={text}>{t('chat.toolsMenu.audio')}</Text></Pressable><Text style={muted}>{t('chat.toolsMenu.audioUnavailable')}</Text>
          </>}
        </ScrollView>
        {onManageTools?<View style={s.footer}>{button(t('chat.toolsMenu.manage'),()=>{onClose();onManageTools();})}</View>:null}
      </SafeAreaView>
    </KeyboardAvoidingView>
  </Modal>;
}
const s=StyleSheet.create({trigger:{minHeight:44,maxWidth:'100%',flexShrink:1,paddingHorizontal:12,borderRadius:999,flexDirection:'row',alignItems:'center',gap:6},overlay:{flex:1,justifyContent:'flex-end',backgroundColor:'rgba(0,0,0,.2)'},sheet:{maxHeight:'82%',minHeight:180,borderTopLeftRadius:20,borderTopRightRadius:20,borderWidth:1,paddingBottom:20},header:{padding:16,flexDirection:'row',alignItems:'center',justifyContent:'space-between'},body:{padding:16,gap:12},row:{flexDirection:'row',alignItems:'center',flexWrap:'wrap',gap:8},button:{minHeight:44,paddingHorizontal:12,paddingVertical:8,borderRadius:10,justifyContent:'center'},switchTarget:{width:44,minHeight:44,flexShrink:0,alignItems:'center',justifyContent:'center'},switchTrack:{width:36,height:22,padding:3,borderRadius:11},switchThumb:{width:16,height:16,borderRadius:8},search:{fontSize:14,lineHeight:22,borderWidth:1,borderRadius:10,minHeight:44,padding:12},service:{flexDirection:'row',gap:12,alignItems:'center',paddingVertical:12,borderBottomWidth:StyleSheet.hairlineWidth},footer:{padding:16}});
