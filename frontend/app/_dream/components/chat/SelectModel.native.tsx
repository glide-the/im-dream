// [Sync] 2026-11-13: use native UI text metrics for Chinese menu controls without changing shared content typography.
// SPDX-License-Identifier: MIT
// Copyright (c) 2025 better-chatbot. Native adaptation of components/select-model.tsx; full notice: frontend/third-party/better-chatbot/LICENSE.
// [Input] Original IM model catalog, saved alias and save/reload state.
// [Output] Current-model trigger and native searchable grouped sheet with selected and disabled rows.
// [Pos] Native presentation counterpart of migrated SelectModel; model persistence remains IM-owned.
import {useEffect,useMemo,useRef,useState} from 'react';
import {AccessibilityInfo,ActivityIndicator,findNodeHandle,KeyboardAvoidingView,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,Text,TextInput,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import useInkColors from '../../../../src/components/useInkColors.native';
import {modelMenuGroups,type SelectModelProps} from './modelSelection';
export function SelectModel(props:SelectModelProps){
  const {t}=useTranslation(),c=useInkColors(),[open,setOpen]=useState(false),[query,setQuery]=useState(''),[active,setActive]=useState(0),trigger=useRef<View>(null);
  const groups=useMemo(()=>modelMenuGroups(props.models,query),[props.models,query]),eligible=groups.flatMap(group=>group.models).filter(model=>model.callable);
  const compact=useWindowDimensions().width<=767;
  const selected=props.models.find(model=>model.modelAlias===props.currentModel),text={color:c['color-text-primary'],fontSize:14,lineHeight:22,fontWeight:'400' as const},muted={color:c['color-text-muted'],fontSize:12,lineHeight:20};
  const blocked=props.disabled||props.loading||props.saving||!!props.error;
  useEffect(()=>{if(props.active===false)setOpen(false);},[props.active]);
  function close(){setOpen(false);requestAnimationFrame(()=>{const tag=findNodeHandle(trigger.current);if(tag)AccessibilityInfo.setAccessibilityFocus(tag);});}
  function choose(alias:string){if(blocked||!props.models.some(model=>model.modelAlias===alias&&model.callable))return;props.onSelect(alias);close();}
  return <View style={{minWidth:0,maxWidth:compact?120:180,flexShrink:1}}>
    <Pressable ref={trigger} testID="model-selector-button" accessibilityRole="button" accessibilityLabel={t('chat.modelMenu.trigger',{name:selected?.displayName||props.currentModel||t('chat.modelMenu.title')})} accessibilityState={{expanded:open,disabled:props.disabled||props.saving,busy:props.loading||props.saving}} disabled={props.disabled||props.saving} onPress={()=>{setQuery('');setActive(0);setOpen(true);}} style={s.trigger}>
      {props.loading||props.saving?<ActivityIndicator color={c['color-text-primary']} size="small"/>:null}<Text numberOfLines={1} style={[text,{flexShrink:1,fontSize:13,lineHeight:20}]}>{selected?.displayName||props.currentModel||t(props.loading?'chat.modelMenu.loading':'chat.modelMenu.title')}</Text><Text style={text}>⌄</Text>
    </Pressable>
    {props.error?<View style={{gap:4}}><Text accessibilityRole="alert" style={muted}>{props.error}</Text><Pressable accessibilityRole="button" disabled={props.saving} onPress={props.onReload} style={s.row}><Text style={text}>{t('chat.modelMenu.reload')}</Text></Pressable></View>:props.status?<Text accessibilityRole="text" style={muted}>{props.status}</Text>:null}
    <Modal transparent visible={open} animationType="slide" onRequestClose={close}>
      <KeyboardAvoidingView style={s.overlay} behavior={Platform.OS==='ios'?'padding':undefined}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={close}/>
        <SafeAreaView accessibilityViewIsModal onAccessibilityEscape={close} style={[s.sheet,{backgroundColor:c['color-bg-surface-solid'],borderColor:c['color-border-paper']}]}>
          <View style={s.header}><Text accessibilityRole="header" style={[text,{fontSize:16,lineHeight:24,fontWeight:'600'}]}>{t('chat.modelMenu.title')}</Text><Pressable accessibilityRole="button" accessibilityLabel={t('chat.modelMenu.close')} onPress={close} style={s.row}><Text style={text}>×</Text></Pressable></View>
          <TextInput autoFocus accessibilityLabel={t('chat.modelMenu.search')} placeholder={t('chat.modelMenu.search')} placeholderTextColor={c['color-text-muted']} value={query} onChangeText={value=>{setQuery(value);setActive(0);}} autoCorrect={false} autoCapitalize="none" returnKeyType="done" onSubmitEditing={()=>{if(eligible[active])choose(eligible[active].modelAlias);}} onKeyPress={({nativeEvent})=>{if(nativeEvent.key==='ArrowDown')setActive(index=>Math.min(index+1,eligible.length-1));else if(nativeEvent.key==='ArrowUp')setActive(index=>Math.max(index-1,0));else if(nativeEvent.key==='Escape')close();}} style={[s.search,text,{borderColor:c['color-border-paper']}]}/>
          <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.list} accessibilityRole="radiogroup" accessibilityLabel={t('chat.modelMenu.title')}>
            {props.loading?<ActivityIndicator color={c['color-text-primary']} accessibilityLabel={t('chat.modelMenu.loading')}/>:null}
            {props.error?<View><Text accessibilityRole="alert" style={muted}>{props.error}</Text><Pressable accessibilityRole="button" onPress={props.onReload} disabled={props.saving} style={s.row}><Text style={text}>{t('chat.modelMenu.reload')}</Text></Pressable></View>:null}
            {!props.loading&&!props.error&&props.currentModel&&!props.models.some(model=>model.modelAlias===props.currentModel)?<Text style={muted}>{t('chat.modelMenu.savedUnavailable',{model:props.currentModel})}</Text>:null}
            {groups.map(group=><View key={group.provider}>
              <Text accessibilityRole="header" style={[muted,{padding:8}]}>{t(`chat.modelMenu.protocols.${group.provider}`)}</Text>
              {group.models.map(model=><Pressable key={model.modelAlias} accessibilityRole="radio" accessibilityLabel={model.displayName} accessibilityState={{checked:props.currentModel===model.modelAlias,disabled:!model.callable||blocked}} disabled={!model.callable||blocked} onPress={()=>choose(model.modelAlias)} style={[s.row,{backgroundColor:props.currentModel===model.modelAlias?c['color-bg-hover']:'transparent',opacity:model.callable?1:.5}]}>
                <Text style={[text,{width:16}]}>{props.currentModel===model.modelAlias?'✓':''}</Text><View style={{flex:1,minWidth:0,gap:4}}><Text numberOfLines={2} style={text}>{model.displayName}</Text><Text numberOfLines={1} style={muted}>{model.modelAlias}</Text>{!model.callable?<Text style={muted}>{model.upgradeHint||t('chat.modelMenu.unavailable')}</Text>:null}</View>{props.defaultAlias===model.modelAlias?<Text style={[muted,{flexShrink:0}]}>{t('chat.modelMenu.recommended')}</Text>:null}
              </Pressable>)}
            </View>)}
            {!props.loading&&!props.error&&groups.length===0?<Text style={muted}>{t('chat.modelMenu.empty')}</Text>:null}
          </ScrollView>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </Modal>
  </View>;
}
const s=StyleSheet.create({trigger:{minHeight:44,maxWidth:'100%',flexDirection:'row',alignItems:'center',gap:6,paddingHorizontal:10,borderRadius:999},overlay:{flex:1,justifyContent:'flex-end',backgroundColor:'rgba(0,0,0,.2)'},sheet:{maxHeight:'70%',minHeight:160,borderWidth:1,borderTopLeftRadius:20,borderTopRightRadius:20,paddingBottom:20},header:{paddingHorizontal:16,paddingTop:12,flexDirection:'row',alignItems:'center',justifyContent:'space-between'},row:{minHeight:44,flexDirection:'row',alignItems:'center',gap:8,padding:10,borderRadius:9},search:{fontSize:14,lineHeight:22,minHeight:44,borderWidth:1,borderRadius:10,padding:12,margin:12},list:{padding:12,gap:8}});
