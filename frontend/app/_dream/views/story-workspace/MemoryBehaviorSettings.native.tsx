// [Input] Shared Memory responses state, original catalog/options and native HTTP/storage adapters.
// [Output] The original enable, per-theme response, defaults, CAS conflict and same-save recovery controls.
// [Pos] Native Settings content; callers retain navigation and App/backend lifetime.
import {useEffect,useState} from 'react';
import {Modal,Pressable,ScrollView,StyleSheet,Switch,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport';
import {nativeMemoryBehaviorPendingStore,newMemoryBehaviorRequestId} from '../../../../src/platform/memoryBehavior.native';
import useMemoryBehaviorSettings,{cloneMemoryBehavior,MEMORY_BEHAVIOR_ACTIONS as ACTIONS,MEMORY_BEHAVIOR_THEMES as THEMES,type MemoryBehaviorPendingStore,type MemoryThemeId} from '../../hooks/useMemoryBehaviorSettings';
export default function MemoryBehaviorSettings({onBack,transport=clientFetch,pendingStore=nativeMemoryBehaviorPendingStore,newRequestId=newMemoryBehaviorRequestId,onSessionExpired,active=true}:{onBack:()=>void;transport?:typeof fetch;pendingStore?:MemoryBehaviorPendingStore;newRequestId?:()=>string|Promise<string>;onSessionExpired?:()=>void;active?:boolean}) {
  const {t,i18n}=useTranslation(),c=useInkColors(),zh=i18n.language.startsWith('zh'),words=(cn:string,en:string)=>zh?cn:en;
  const {snapshot,draft,setDraft,pending,busy,message,error,conflict,load,submit,save,check,loadCurrent,dirty}=useMemoryBehaviorSettings({zh,transport,pendingStore,newRequestId,onSessionExpired});
  const [choosing,setChoosing]=useState<MemoryThemeId|null>(null),disabled=busy||!!pending;
  useEffect(()=>{if(!active)setChoosing(null);},[active]);
  const picker=snapshot?.catalog.find(theme=>theme.id===choosing),text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']};
  const button=(label:string,onPress:()=>void,unavailable=false)=><Pressable accessibilityRole="button" disabled={unavailable} onPress={onPress} style={[styles.button,{borderColor:c['color-border-paper'],opacity:unavailable?0.5:1}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
  const themeName=(id:MemoryThemeId,label:string)=>zh?label:THEMES[id];
  const actionName=(action:string)=>ACTIONS[action]?.[zh?0:1]??action;
  return <View style={[styles.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={styles.header}>{button(t('settings.workspace.preferences.back'),onBack)}<InkLabel accessibilityRole="header" style={[text,styles.title]}>{words('记忆回应','Memory responses')}</InkLabel></View>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <InkLabel style={secondary}>{words('有可用回顾内容时，根据与你当前任务相关的观察调整回应方式。','Adapt responses using relevant Reflections observations.')}</InkLabel>
      {message?<InkLabel accessibilityRole={error?'alert':undefined} accessibilityLiveRegion="polite" style={{color:error?c['color-state-error']:c['color-text-primary']}}>{message}</InkLabel>:null}
      {!snapshot||!draft?button(busy?words('读取中…','Loading…'):words('重新读取','Reload'),()=>void load(),busy):<>
        <View style={[styles.card,{backgroundColor:c['color-bg-paper'],borderColor:c['color-border-paper']}]}>
          <InkLabel style={text}>{words('使用回顾记忆调整回应','Use Reflections to adapt responses')}</InkLabel>
          <Switch accessibilityLabel={words('使用回顾记忆调整回应','Use Reflections to adapt responses')} value={draft.enabled} disabled={disabled} onValueChange={enabled=>setDraft({...draft,enabled})}/>
          <InkLabel style={secondary}>{words('默认关闭。开启后仍以你当前的任务和明确表达的边界为准。','Off by default. Your current task and stated boundaries take priority.')}</InkLabel>
        </View>
        {conflict?<InkLabel style={secondary}>{`${words('其他位置已保存：','Saved elsewhere: ')}${snapshot.desired.enabled?words('已开启','On'):words('已关闭','Off')} · ${snapshot.catalog.map(theme=>`${themeName(theme.id,theme.label)}：${snapshot.desired.themes[theme.id].enabled?actionName(snapshot.desired.themes[theme.id].action):words('关闭','Off')}`).join('；')}`}</InkLabel>:null}
        {snapshot.catalog.map(theme=><View key={theme.id} style={[styles.card,{backgroundColor:c['color-bg-paper'],borderColor:c['color-border-paper']}]}>
          <InkLabel accessibilityRole="header" style={[text,styles.subtitle]}>{themeName(theme.id,theme.label)}</InkLabel>
          <InkLabel style={text}>{words('启用此主题','Enable this theme')}</InkLabel>
          <Switch accessibilityLabel={`${themeName(theme.id,theme.label)} ${words('启用此主题','Enable this theme')}`} value={draft.themes[theme.id].enabled} disabled={disabled||!draft.enabled} onValueChange={enabled=>setDraft({...draft,themes:{...draft.themes,[theme.id]:{...draft.themes[theme.id],enabled}}})}/>
          <InkLabel style={secondary}>{words('回应方式','Response style')}</InkLabel>
          <Pressable accessibilityRole="button" accessibilityLabel={`${themeName(theme.id,theme.label)} ${words('回应方式','response style')}`} disabled={disabled||!draft.enabled} onPress={()=>setChoosing(theme.id)} style={[styles.button,{borderColor:c['color-border-paper'],opacity:disabled||!draft.enabled?0.5:1}]}><InkLabel style={text}>{actionName(draft.themes[theme.id].action)}</InkLabel></Pressable>
        </View>)}
        <InkLabel style={secondary}>{words('保存不影响正在生成的回应。历史主题只是分析线索，不代表你现在的情绪。','Saving does not change an in-progress response. Historical themes do not describe your current feelings.')}</InkLabel>
        {button(words('恢复默认','Restore defaults'),()=>setDraft(cloneMemoryBehavior(snapshot.default)),disabled)}
        {pending?<>{button(words('核实保存结果','Check save result'),()=>void check(),busy)}{button(words('重试这次保存','Retry this save'),()=>void submit(pending),busy)}</>:button(busy?words('保存中…','Saving…'):words('保存','Save'),()=>void save(),busy||!dirty)}
        {button(words('读取最新设置','Load current settings'),loadCurrent,busy)}
      </>}
    </ScrollView>
    <Modal visible={active&&!!picker} transparent animationType="fade" onRequestClose={()=>setChoosing(null)}>
      <View style={styles.scrim}><View accessibilityViewIsModal style={[styles.sheet,{backgroundColor:c['color-bg-paper']}]}>
        <InkLabel accessibilityRole="header" style={[text,styles.subtitle]}>{picker?`${themeName(picker.id,picker.label)} ${words('回应方式','response style')}`:''}</InkLabel>
        <ScrollView>{picker?.actions.map(action=><Pressable key={action} accessibilityRole="radio" accessibilityState={{checked:draft?.themes[picker.id].action===action}} aria-checked={draft?.themes[picker.id].action===action} disabled={disabled} onPress={()=>{if(draft&&!disabled){setDraft({...draft,themes:{...draft.themes,[picker.id]:{...draft.themes[picker.id],action}}});setChoosing(null);}}} style={[styles.button,{borderColor:c['color-border-paper']}]}><InkLabel style={text}>{actionName(action)}</InkLabel></Pressable>)}</ScrollView>
        {button(t('chat.history.close'),()=>setChoosing(null))}
      </View></View>
    </Modal>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,padding:12},title:{fontSize:22,flexShrink:1},subtitle:{fontSize:18},content:{padding:20,gap:16,paddingBottom:32},card:{gap:10,padding:16,borderWidth:1,borderRadius:16},button:{minHeight:44,padding:12,justifyContent:'center',borderRadius:12,borderWidth:StyleSheet.hairlineWidth},scrim:{flex:1,justifyContent:'center',padding:20,backgroundColor:'rgba(0,0,0,0.35)'},sheet:{maxHeight:'80%',borderRadius:16,padding:16,gap:12}});
