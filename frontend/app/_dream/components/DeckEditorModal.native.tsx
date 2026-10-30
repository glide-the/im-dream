// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-29: retain editor-owned field drafts across section/Agent changes; explicit close releases local drafts.
// [Input] Original Deck/Voice DTOs, mutation callbacks, content-version hook and native HTTP.
// [Output] Native overview/Agent/plugin maintenance, durable draft feedback and explicit content commits.
// [Pos] Native Deck maintenance dialog; Web DOM/CSS and server business rules retain their owners.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,KeyboardAvoidingView,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,Switch,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {Deck,Voice} from '../api/voiceApi';
import {useDeckContentVersions} from '../hooks/useDeckContentVersions';
import type {ActiveChatVoice} from '../lib/chat-schema';
import DeckClaudePluginSelector from './DeckClaudePluginSelector.native';
import DeckAgentIcon,{deckAgentColor} from './deck/DeckAgentIcon.native';
import InkLabel from '../../../src/components/InkLabel.native';
import useInkColors from '../../../src/components/useInkColors.native';
import visuals from '../../../shared/deck-icons.json';
import {DECK_COLORS} from '../constants/deck';

interface Props {
  active?:boolean;
  deck:Deck;isSystem:boolean;creatingVoiceId:string|null;selectedVoiceId:string|null;transport:typeof fetch;
  onSelectVoice:(id:string|null)=>void;onClose:()=>void;onAddVoice:(id:string)=>Promise<void>;
  onUpdateDeck:(id:string,data:Partial<Deck>)=>Promise<void>;onUpdateVoice:(id:string,data:Partial<Voice>)=>Promise<void>;
  onToggleVoice:(id:string,enabled:boolean)=>Promise<void>;onDeleteVoice:(id:string)=>Promise<void>;
  onVersionChanged:()=>Promise<void>;onChatWithDeck?:(deckId:string,voice:ActiveChatVoice)=>void;
}
export default function DeckEditorModal({deck,isSystem,creatingVoiceId,selectedVoiceId,transport,onSelectVoice,onClose,onAddVoice,onUpdateDeck,onUpdateVoice,onToggleVoice,onDeleteVoice,onVersionChanged,onChatWithDeck,active=true}:Props){
  const {t}=useTranslation(),colors=useInkColors();
  const [section,setSection]=useState<'overview'|'agents'|'plugins'>('overview'),[historyOpen,setHistoryOpen]=useState(false);
  const [mutationError,setMutationError]=useState(''),[saving,setSaving]=useState(0),[description,setDescription]=useState('');
  const content=useDeckContentVersions(deck.id,transport),pending=useRef(new Set<Promise<void>>());
  const drafts=useRef(new Map<string,{value:string;failed:boolean}>());
  const voices=deck.voices??[],selectedVoice=voices.find(voice=>voice.id===selectedVoiceId)??voices[0];
  const label=(text:string,muted=false)=><InkLabel style={{color:colors[muted?'color-text-muted':'color-text-primary']}}>{text}</InkLabel>;
  const button=(text:string,action:()=>void,disabled=false)=><Pressable accessibilityRole="button" accessibilityLabel={text} accessibilityState={{disabled}} disabled={disabled} onPress={action}
    style={[styles.button,{borderColor:colors['color-border-paper'],opacity:disabled?0.5:1}]}>{label(text)}</Pressable>;
  const mutation=(action:()=>Promise<void>)=>{
    setMutationError('');setSaving(value=>value+1);
    const operation=(async()=>{try{await action();await content.refresh(historyOpen);}catch(error){setMutationError(error instanceof Error?error.message:'保存失败，请重试。');throw error;}finally{setSaving(value=>value-1);}})();
    pending.current.add(operation);void operation.finally(()=>pending.current.delete(operation)).catch(()=>undefined);return operation;
  };
  const mutate=(action:()=>Promise<void>)=>{void mutation(action).catch(()=>undefined);};
  const disabled=isSystem||saving>0||content.submitting;
  const prepare=async()=>{if(pending.current.size)await Promise.allSettled([...pending.current]);setDescription('');const fresh=await content.refresh(historyOpen);if(fresh)await content.prepare(fresh);};
  const close=()=>{if(content.preview){if(!content.submitting)content.clearPreview();return;}if(historyOpen){setHistoryOpen(false);return;}onClose();};
  const panel=content.preview;
  return <Modal visible={active} animationType="slide" presentationStyle="fullScreen" onRequestClose={close}>
    <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}><KeyboardAvoidingView style={styles.fill} behavior={Platform.OS==='ios'?'padding':undefined}>
      <View style={[styles.header,{borderColor:colors['color-border-paper']}]}>
        <View style={styles.grow}><InkLabel accessibilityRole="header" style={[styles.title,{color:colors['color-text-primary']}]}>{panel?`提交 ${deck.name} 为 v${panel.target_version}`:historyOpen?'版本记录':deck.name}</InkLabel>
          {!panel?label(content.loading?'正在读取内容版本':`${content.state?.latest_version?`内容版本 v${content.state.latest_version}`:'内容版本未提交'}${content.state?.dirty?` · 草稿 r${content.state.draft_revision}`:''}`,true):label(panel.latest_version?`基于 v${panel.latest_version}`:'首次提交',true)}</View>
        {button(panel?'关闭提交版本弹窗':historyOpen?'收起版本记录':'Close',close,content.submitting)}
      </View>
      {panel?<ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled" keyboardDismissMode={Platform.OS==='ios'?'interactive':'on-drag'}>
        {label(t('deck.versions.submitImpact'))}
        <View accessibilityLabel="版本变更摘要" style={styles.body}>{panel.changes.map((change,index)=><View key={`${change.scope}-${change.change_type}-${index}`} style={styles.group}>
          {label(change.label)}{label(`${change.change_type==='added'?'新增':change.change_type==='removed'?'移除':'修改'}${change.fields.length?` · ${change.fields.join('、')}`:''}`,true)}
        </View>)}</View>
        {label('版本说明（可选）')}<TextInput accessibilityLabel="版本说明（可选）" value={description} onChangeText={setDescription} maxLength={200} multiline
          placeholder="说明这次修改的目的" placeholderTextColor={colors['color-text-muted']} style={[styles.input,styles.multiline,{color:colors['color-text-primary'],borderColor:colors['color-border-paper']}]} editable={!content.submitting}/>
        {content.error?<View accessibilityRole="alert">{label(content.error)}</View>:null}
        <View style={styles.wrap}>{button('取消',()=>content.clearPreview(),content.submitting)}{button(content.submitting?'提交中…':`确认提交 v${panel.target_version}`,()=>{void content.commit(description).then(async result=>{if(result)await onVersionChanged();}).catch(error=>setMutationError(String(error)));},content.submitting)}</View>
      </ScrollView>:historyOpen?<ScrollView contentContainerStyle={styles.body}>
        {label(t('deck.versions.description'))}{label(content.state?.latest_version?`v${content.state.latest_version}`:'尚未提交')}
        {label(content.state?.dirty?`存在未提交草稿 · r${content.state.draft_revision}`:'已与当前草稿一致',true)}
        {content.loading?<ActivityIndicator/>:content.history?.versions.length?content.history.versions.map(entry=><View key={entry.version} style={[styles.row,{borderColor:colors['color-border-paper']}]}>
          {label(`v${entry.version}`)}{label(`${entry.description||'未填写版本说明'} · ${new Date(entry.created_at).toLocaleString()}`,true)}
        </View>):label('暂无已提交内容版本。')}
        {label('运行插件版本（随内容快照记录）')}{label(deck.deck_plugin_version?`v${deck.deck_plugin_version}`:'Chat 配置',true)}
        {content.error?<View accessibilityRole="alert">{label(content.error)}{button(t('deck.actions.retry'),()=>{void content.refresh(true);},content.loading)}</View>:null}
      </ScrollView>:<>
        <View style={[styles.wrap,styles.tabs]} accessibilityRole="tablist" accessibilityLabel={t('deck.details.sectionsLabel')}>
          {([['overview','概览'],['agents','Agents'],['plugins','Claude 插件']] as const).map(([value,text])=><Pressable key={value} accessibilityRole="tab" accessibilityState={{selected:section===value}} onPress={()=>setSection(value)} style={[styles.button,{backgroundColor:section===value?colors['color-bg-hover']:'transparent'}]}>{label(value==='agents'?`${text} ${voices.length}`:text)}</Pressable>)}
        </View>
        <View style={styles.wrap}>{!isSystem?button(content.submitting?'准备中…':`提交 v${content.state?.next_version??1}`,()=>{void prepare();},saving>0||content.loading||content.submitting||!content.state?.dirty||content.capabilityUnavailable):null}
          {button('版本记录',()=>{setHistoryOpen(true);void content.refresh(true);},content.submitting)}</View>
        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled" keyboardDismissMode={Platform.OS==='ios'?'interactive':'on-drag'}>
          {section==='overview'?<>
            <InkLabel accessibilityRole="header" style={[styles.heading,{color:colors['color-text-primary']}]}>{t('deck.details.overviewTitle')}</InkLabel>
            {label(t('deck.details.overviewDescription'))}{label(deck.enabled?'已启用':'已停用',true)}
            <DraftField key={`${deck.id}-name`} cache={drafts.current} fieldKey={`${deck.id}-name`} label={t('deck.details.name')} value={deck.name} disabled={disabled} onSave={value=>mutation(()=>onUpdateDeck(deck.id,{name:value}))}/>
            <DraftField key={`${deck.id}-description`} cache={drafts.current} fieldKey={`${deck.id}-description`} label={t('deck.details.description')} value={deck.description??''} multiline disabled={disabled} onSave={value=>mutation(()=>onUpdateDeck(deck.id,{description:value}))}/>
            {label('Agent 类型')}{label(t('deck.labels.agentType.chat'),true)}
          </>:section==='agents'?<>
            <View style={styles.wrap}>{label(`${voices.length} 个配置`)}{!isSystem?button(creatingVoiceId===deck.id?'Adding…':'+ Add',()=>mutate(()=>onAddVoice(deck.id)),disabled||creatingVoiceId===deck.id):null}</View>
            {!voices.length?label('No voices in this deck yet'):voices.map(voice=><View key={voice.id} style={[styles.voiceRow,{borderColor:colors['color-border-paper']}]}>
              <Pressable accessibilityRole="button" accessibilityLabel={voice.name} accessibilityState={{selected:voice.id===selectedVoice?.id}} onPress={()=>onSelectVoice(voice.id)} style={[styles.voiceIdentity,{backgroundColor:voice.id===selectedVoice?.id?colors['color-bg-hover']:'transparent'}]}>
                <DeckAgentIcon name={voice.icon} color={deckAgentColor(voice.color,colors)}/>{label(voice.name)}
              </Pressable><Switch accessibilityLabel={`Toggle ${voice.name}`} value={voice.enabled} disabled={disabled} onValueChange={()=>mutate(()=>onToggleVoice(voice.id,voice.enabled))}/>
            </View>)}
            {selectedVoice?<View style={styles.group}>
              <DraftField key={`${selectedVoice.id}-name`} cache={drafts.current} fieldKey={`${selectedVoice.id}-name`} label="Agent Name" value={selectedVoice.name} disabled={disabled} onSave={value=>mutation(()=>onUpdateVoice(selectedVoice.id,{name:value}))}/>
              {label('Agent Icon')}<View style={styles.wrap}>{Object.keys(visuals.icons).map(icon=><Pressable key={icon} accessibilityRole="radio" accessibilityLabel={`Agent Icon ${icon}`} accessibilityState={{checked:selectedVoice.icon===icon,disabled}} aria-checked={selectedVoice.icon===icon} disabled={disabled}
                onPress={()=>mutate(()=>onUpdateVoice(selectedVoice.id,{icon}))} style={[styles.icon,{backgroundColor:selectedVoice.icon===icon?colors['color-bg-hover']:'transparent'}]}><DeckAgentIcon name={icon} color={colors['color-text-primary']}/></Pressable>)}</View>
              {label('Agent Color')}<View style={styles.wrap}>{Object.entries(DECK_COLORS).map(([color,data])=><Pressable key={color} accessibilityRole="radio" accessibilityLabel={`Agent Color ${data.label}`} accessibilityState={{checked:selectedVoice.color===color,disabled}} aria-checked={selectedVoice.color===color} disabled={disabled}
                onPress={()=>mutate(()=>onUpdateVoice(selectedVoice.id,{color}))} style={[styles.button,{backgroundColor:selectedVoice.color===color?colors['color-bg-hover']:'transparent'}]}>{label(data.label)}</Pressable>)}</View>
              <View style={styles.wrap}>{!isSystem?button('Delete',()=>mutate(()=>onDeleteVoice(selectedVoice.id)),disabled):null}
                {onChatWithDeck?button('在 Chat 中使用 →',()=>onChatWithDeck(deck.id,{id:selectedVoice.id,name:selectedVoice.name,systemPrompt:selectedVoice.system_prompt,icon:selectedVoice.icon,color:selectedVoice.color}),saving>0):null}</View>
              <DraftField key={`${selectedVoice.id}-prompt`} cache={drafts.current} fieldKey={`${selectedVoice.id}-prompt`} label="Agent Prompt" value={selectedVoice.system_prompt} multiline disabled={disabled} onSave={value=>mutation(()=>onUpdateVoice(selectedVoice.id,{system_prompt:value}))}/>
            </View>:label('Select an agent from the list to edit')}
          </>:<DeckClaudePluginSelector deckId={deck.id} disabled={disabled} transport={transport} onSaved={async()=>{await content.refresh(historyOpen);await onVersionChanged();}}/>}
          {saving>0?<View accessibilityLiveRegion="polite">{label('保存中…')}</View>:null}
          {mutationError||content.error?<View accessibilityRole="alert">{label(mutationError||content.error||'')}{content.error?button(t('deck.actions.retry'),()=>{void content.refresh();},content.loading):null}</View>:null}
        </ScrollView>
      </>}
    </KeyboardAvoidingView></SafeAreaView>
  </Modal>;
}

function DraftField({label,value,multiline,disabled,onSave,cache,fieldKey}:{label:string;value:string;multiline?:boolean;disabled:boolean;onSave:(value:string)=>Promise<void>;cache:Map<string,{value:string;failed:boolean}>;fieldKey:string}){
  const colors=useInkColors(),[draft,setDraft]=useState(()=>cache.get(fieldKey)?.value??value),[failure,setFailure]=useState(()=>cache.get(fieldKey)?.failed??false),previous=useRef(value),saving=useRef(false);
  useEffect(()=>{const old=previous.current;previous.current=value;setDraft(current=>current===old?value:current);},[value]);
  useEffect(()=>setFailure(cache.get(fieldKey)?.failed??false),[cache.get(fieldKey)?.failed]);
  const save=async()=>{if(disabled||saving.current||draft===value)return;saving.current=true;setFailure(false);try{await onSave(draft);if(cache.get(fieldKey)?.value===draft)cache.delete(fieldKey);}catch{cache.set(fieldKey,{value:draft,failed:true});setFailure(true);}finally{saving.current=false;}};
  return <View style={styles.group}><InkLabel style={{color:colors['color-text-primary']}}>{label}</InkLabel>
    <TextInput accessibilityLabel={label} value={draft} onChangeText={text=>{cache.set(fieldKey,{value:text,failed:false});setDraft(text);setFailure(false);}} onBlur={()=>void save()} editable={!disabled} multiline={multiline}
      style={[styles.input,multiline?styles.multiline:undefined,{color:colors['color-text-primary'],borderColor:colors['color-border-paper']}]} />
    {failure?<Pressable accessibilityRole="button" accessibilityLabel={`重试保存 ${label}`} onPress={()=>void save()} disabled={disabled} style={styles.button}><InkLabel style={{color:colors['color-text-primary']}}>重试保存</InkLabel></Pressable>:null}
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1},grow:{flex:1,minWidth:0},header:{flexDirection:'row',alignItems:'center',gap:8,paddingHorizontal:16,paddingVertical:8,borderBottomWidth:StyleSheet.hairlineWidth},
  title:{fontSize:22,fontWeight:'600'},heading:{fontSize:20,fontWeight:'600'},body:{padding:16,paddingBottom:40,gap:16},group:{gap:10},tabs:{paddingHorizontal:16},wrap:{flexDirection:'row',flexWrap:'wrap',gap:6,paddingHorizontal:8},
  button:{minHeight:44,paddingHorizontal:12,paddingVertical:10,borderRadius:8,borderWidth:StyleSheet.hairlineWidth,justifyContent:'center'},input:{borderWidth:1,borderRadius:8,padding:12,minHeight:44,fontSize:16,fontFamily:'Excalifont'},multiline:{minHeight:120,textAlignVertical:'top'},
  row:{gap:6,paddingVertical:12,borderBottomWidth:StyleSheet.hairlineWidth},voiceRow:{flexDirection:'row',alignItems:'center',gap:8,borderBottomWidth:StyleSheet.hairlineWidth},voiceIdentity:{flex:1,minWidth:0,minHeight:44,flexDirection:'row',alignItems:'center',gap:10,padding:8},icon:{width:44,height:44,alignItems:'center',justifyContent:'center',borderRadius:8}});
