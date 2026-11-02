// [Input] Original Reflections API/recovery storage, authenticated state, timezone and native navigation callbacks.
// [Output] Native Reflections dashboard, saved-report reading, same-day rerun choice and original section configuration.
// [Pos] Native presentation over useReflections; the App owns the supplied API/storage instance and backend lifecycle.
// [Sync] 2026-10-29: preserve reachable Web flows and text history navigation; no automatic task launch or whole-page WebView.
import {useEffect,type ReactNode} from 'react';
import {KeyboardAvoidingView,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,Text,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import useInkColors from '../../../src/components/useInkColors.native';
import type {ReflectionsApi,ReflectionsStorage,ReflectionSectionKey} from '../api/reflectionsApi';
import type {StoryWorkspaceAnalysisSection} from '../router/storyWorkspacePath';
import {ANALYSIS_HISTORY_PREVIEW_LIMIT,localDateKey} from './reflectionHistory';
import {PROMPT_FILE_ORDER,PROMPT_FILE_LABELS} from './reflectionConfigPresentation';
import {getDateLocale} from '../i18n';
import useReflections from '../hooks/useReflections';
import ReflectionAnalysisContentControls from './ReflectionAnalysisContentControls.native';
import ReflectionBlogPage from './ReflectionBlogPage.native';
type Props={timezone:string;authenticated:boolean;api:ReflectionsApi;storage:ReflectionsStorage;onBack:()=>void;onTimeline:()=>void;transport?:typeof fetch;initialSection?:StoryWorkspaceAnalysisSection|null;onSectionConsumed?:()=>void;active?:boolean};
function Action({children,onPress,disabled=false,label,primary=false}:{children:ReactNode;onPress:()=>void;disabled?:boolean;label?:string;primary?:boolean}) {
  const c=useInkColors();return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled}} disabled={disabled} onPress={onPress} style={[s.button,{opacity:disabled?0.5:1,borderColor:c['color-border-paper'],backgroundColor:primary?c['color-action-primary']:'transparent'}]}><Text style={{color:primary?c['color-text-on-action']:c['color-text-body'],textAlign:'center'}}>{children}</Text></Pressable>;
}
export default function AnalysisView({timezone,authenticated,api,storage,onBack,onTimeline,transport,initialSection,onSectionConsumed,active=true}:Props) {
  const {t,i18n}=useTranslation(),c=useInkColors(),zh=i18n.language.startsWith('zh'),dateLocale=getDateLocale(i18n.language);
  const r=useReflections({timezone,authenticated,api,storage,readRequestedSection:()=>initialSection??null,consumeRequestedSection:()=>onSectionConsumed?.()});
  useEffect(()=>{if(!active){r.setConfigModal(previous=>({...previous,open:false}));r.setReanalysisDialog(previous=>({...previous,open:false}));}},[active]);
  const text={color:c['color-text-primary']},muted={color:c['color-text-muted']},error={color:c['color-state-error']};
  const reportStats=(stats:{days:number;entries:number;words:number})=>`${t('analysis.statsLabels.daysCount',{count:stats.days||0})} · ${t('analysis.statsLabels.entriesCount',{count:stats.entries||0})} · ${t('analysis.statsLabels.wordsCount',{value:(stats.words||0).toLocaleString()})}`;
  if(r.viewMode==='blog'&&r.selectedReport)return <ReflectionBlogPage key={String(r.selectedReport.id)} report={r.selectedReport} timezone={timezone} initialSection={r.requestedBlogSection}
    saveError={r.selectedReport.taskId===r.reportRetryTaskId?r.reportSaveError:undefined} saving={r.reportSaving}
    onRetrySave={r.selectedReport.taskId===r.reportRetryTaskId&&r.reportRetryTaskId?()=>void r.retryReportSave(r.reportRetryTaskId!):undefined}
    onBack={()=>{r.setRequestedBlogSection(null);r.setViewMode('dashboard');}}/>;
  return <View style={[s.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={s.header}><Action onPress={onBack}>{zh?'返回更多':'Back to More'}</Action></View>
    <ScrollView style={s.fill} contentContainerStyle={s.page} keyboardShouldPersistTaps="handled">
      <View style={s.title}><Text accessibilityRole="header" style={[s.heading,text,{fontSize:30}]}>{t('analysis.title')}</Text><View style={{width:80,height:1,backgroundColor:c['color-text-muted']}}/><Text style={[s.body,muted,{textAlign:'center'}]}>{t('analysis.subtitle')}</Text></View>
      <View style={s.stats}>{[[t('analysis.stats.days'),r.stats.totalDays],[t('analysis.stats.entries'),r.stats.totalEntries],[t('analysis.stats.words'),r.stats.totalWords.toLocaleString()]].map(([label,value])=><View key={label} style={s.stat}><Text style={[s.heading,text,{fontSize:25}]}>{value}</Text><Text style={muted}>{label}</Text></View>)}</View>
      {r.savedReports.length>0||r.historyError?<View style={s.group}>
        <Pressable accessibilityRole="button" onPress={onTimeline} style={[s.button,{borderWidth:0,paddingHorizontal:0}]}><Text accessibilityRole="header" style={[s.heading,text]}>{t('analysis.pastReflections')} →</Text></Pressable>
        {r.historyError?<View accessibilityRole="alert"><Text style={error}>{t('analysis.history.failed')}</Text><Action onPress={()=>void r.reloadSavedReports()}>{t('analysis.history.retry')}</Action></View>:null}
        {r.savedReports.slice(0,ANALYSIS_HISTORY_PREVIEW_LIMIT).map((report,index)=><Pressable key={String(report.id)} accessibilityRole="button" accessibilityLabel={t('analysis.history.open',{date:new Date(report.timestamp).toLocaleString(dateLocale,{timeZone:timezone})})} onPress={()=>r.openReflectionBlogReport(report)} style={[s.report,{borderColor:c['color-border-paper'],backgroundColor:c['color-bg-paper']}]}>
          <View style={s.row}><Text style={[muted,{flex:1}]}>{new Date(report.timestamp).toLocaleDateString(dateLocale,{month:'short',day:'numeric',year:'numeric',timeZone:timezone})}</Text>{index===0?<Text style={{color:c['color-state-success']}}>{t('analysis.report.latest')}</Text>:null}</View>
          <Text style={muted}>{reportStats(report.stats)}</Text><View style={s.row}>{(['echoes','traits','patterns'] as const).filter(section=>report[section].length>0).map(section=><Text key={section} style={[s.badge,{color:c['color-text-body'],backgroundColor:c['color-bg-hover']}]}>{t(`analysis.reportCounts.${section}`,{count:report[section].length})}</Text>)}</View>
        </Pressable>)}
      </View>:null}
      <View style={[s.group,{alignItems:'center'}]}><Action onPress={()=>void r.handleAnalyzeAll()} disabled={r.anyLoading}>{r.anyLoading?t('analysis.actions.generating'):t('analysis.actions.generate')}</Action>
        {!r.reanalysisDialog.open?<ReflectionAnalysisContentControls value={r.analysisContent} onChange={r.setAnalysisContent} authenticated={authenticated} api={api} transport={transport} active={active}/>:null}
        {r.preparedTask&&!r.anyLoading?<View style={s.group}><Text style={muted}>{zh?'有一项分析尚未开始；继续时使用原分析内容。':'An analysis has not started. Continuing uses its original content.'}</Text><Action onPress={r.continuePreparedTask}>{zh?'继续未开始的分析':'Continue unstarted analysis'}</Action></View>:null}
        {r.taskStatus?<View accessibilityLiveRegion="polite" style={[s.report,{borderColor:c['color-border-paper'],backgroundColor:c['color-bg-paper']}]}><Text style={muted}>Live editorial analysis</Text><Text style={[s.heading,text]}>{r.taskStatus}</Text></View>:null}
      </View>
      {authenticated||r.anyLoading||r.anyError?<View style={s.group}>{(['echoes','traits','patterns'] as const).map(section=><View key={section} style={s.group}>
        <View style={[s.row,{justifyContent:'center'}]}><Text style={muted}>{section==='echoes'?'🔄':section==='traits'?'⭐':'🌀'} {t(`analysis.papers.${section}.title`)}</Text>{authenticated?<Action label={`${t(`analysis.papers.${section}.title`)} Configure analysis prompts`} onPress={()=>void r.handleOpenConfig(section)}>⚙</Action>:null}</View>
        {r.loading[section]?<Text style={[s.body,muted]}>{r.streaming[section]?`${r.streaming[section].slice(-800)}▌`:'Waiting for backend Reflections task…'}</Text>:r.errors[section]?<Text style={error}>{r.errors[section]}</Text>:null}
      </View>)}</View>:null}
      {r.anyError&&!r.anyLoading?<Text accessibilityRole="alert" style={[s.body,error]}>{[r.errors.echoes,r.errors.traits,r.errors.patterns].filter(Boolean).join(' | ')}</Text>:null}
      {r.reportSaveError&&!r.anyLoading?<View><Text accessibilityRole="alert" style={error}>{r.reportSaveError}</Text>{r.reportRetryTaskId?<Action disabled={r.reportSaving} onPress={()=>void r.retryReportSave(r.reportRetryTaskId!)}>{zh?'重试保存':'Retry save'}</Action>:null}</View>:null}
      {!r.hasAnyData&&!r.anyLoading?<View style={[s.group,{alignItems:'center',paddingVertical:48}]}><Text style={{fontSize:64,opacity:0.3}}>📖</Text><Text style={[s.heading,text]}>{t('analysis.empty.title')}</Text><Text style={[s.body,muted,{textAlign:'center'}]}>{t('analysis.empty.description')}</Text></View>:null}
    </ScrollView>
    <Modal visible={active&&r.reanalysisDialog.open} animationType="slide" presentationStyle="pageSheet" onRequestClose={()=>r.setReanalysisDialog(previous=>({...previous,open:false}))}>
      <SafeAreaView style={[s.fill,{backgroundColor:c['color-bg-paper']}]}><View style={s.modalHeader}><Text style={muted}>Re-analysis · Editorial choice</Text><Text accessibilityRole="header" style={[s.heading,text,{fontSize:24}]}>Today already has a Reflections analysis.</Text><Text style={[s.body,muted]}>Re-running will create a new analysis. Choose the diary entries and analysis content for this run.</Text></View>
        <ScrollView style={s.fill} contentContainerStyle={s.page} keyboardShouldPersistTaps="handled">
          <ReflectionAnalysisContentControls value={r.analysisContent} onChange={selection=>{r.setAnalysisContent(selection);r.setReanalysisDialog(previous=>({...previous,error:''}));}} authenticated={authenticated} api={api} transport={transport} active={active} inline/>
          <Action onPress={r.handleToggleAllReanalysisSessions}>{r.reanalysisDialog.selectedIds.length===r.reanalysisDialog.sessions.length?'Clear all':'Select all'} · {r.reanalysisDialog.selectedIds.length}/{r.reanalysisDialog.sessions.length}</Action>
          {r.reanalysisDialog.sessions.map(session=>{const checked=r.reanalysisDialog.selectedIds.includes(session.id);return <Pressable key={session.id} accessibilityRole="checkbox" accessibilityLabel={session.first_line||session.name||'Untitled'} accessibilityState={{checked}} onPress={()=>r.handleToggleReanalysisSession(session.id)} style={[s.report,{borderColor:c['color-border-paper'],backgroundColor:checked?c['color-bg-hover']:c['color-bg-surface']}]}><Text style={text}>{checked?'☑':'☐'} {session.first_line||session.name||'Untitled'}</Text><Text style={muted}>{session.date_key||localDateKey(session.updated_at||session.created_at||Date.now())} · {session.word_count??0} words</Text></Pressable>;})}
          {r.reanalysisDialog.error?<Text accessibilityRole="alert" style={error}>{r.reanalysisDialog.error}</Text>:null}
        </ScrollView><View style={s.footer}><Action onPress={()=>r.setReanalysisDialog(previous=>({...previous,open:false}))}>Cancel</Action><Action primary disabled={r.reanalysisDialog.selectedIds.length===0&&!r.analysisContent.include_notion} onPress={()=>void r.handleConfirmReanalysis()}>Re-analyze selected entries</Action></View>
      </SafeAreaView>
    </Modal>
    <Modal visible={active&&r.configModal.open} animationType="slide" presentationStyle="pageSheet" onRequestClose={()=>r.setConfigModal(previous=>({...previous,open:false}))}>
      <SafeAreaView style={[s.fill,{backgroundColor:c['color-bg-paper']}]}><KeyboardAvoidingView style={s.fill} behavior={Platform.OS==='ios'?'padding':undefined}>
        <View style={s.modalHeader}><View style={s.row}><Text style={muted}>CONFIGURE</Text><Text accessibilityRole="header" style={[s.heading,text,{flex:1}]}>{r.configModal.displayName}</Text>{r.configModal.config?.usedCustomConfig?<Text style={{color:c['color-state-warning']}}>CUSTOM</Text>:null}<Action label={zh?'关闭':'Close'} onPress={()=>r.setConfigModal(previous=>({...previous,open:false}))}>×</Action></View></View>
        <ScrollView style={s.fill} contentContainerStyle={s.page} keyboardShouldPersistTaps="handled">
          {r.configModal.loading?<Text style={muted}>Loading…</Text>:PROMPT_FILE_ORDER.map(filename=><View key={filename} style={s.group}><Text style={muted}>{PROMPT_FILE_LABELS[filename]??filename} · {filename}</Text><TextInput accessibilityLabel={filename} multiline value={r.configModal.files[filename]??''} onChangeText={content=>r.setConfigModal(previous=>({...previous,files:{...previous.files,[filename]:content}}))} style={[s.input,{color:c['color-text-body'],borderColor:c['color-border-paper'],backgroundColor:c['color-bg-surface']}]} autoCapitalize="none" autoCorrect={false}/></View>)}
          {r.configModal.error?<Text accessibilityRole="alert" style={error}>{r.configModal.error}</Text>:null}
        </ScrollView><View style={s.footer}><Action onPress={()=>void r.handleResetConfig()}>Reset to Default</Action><Action primary disabled={r.configModal.saving} onPress={()=>void r.handleSaveConfig()}>{r.configModal.saving?'Saving…':'Save Changes'}</Action></View>
      </KeyboardAvoidingView></SafeAreaView>
    </Modal>
  </View>;
}
const serif=Platform.OS==='ios'?'Georgia':'serif';
const s=StyleSheet.create({fill:{flex:1,minHeight:0},header:{paddingHorizontal:16,paddingTop:8,alignItems:'flex-start'},page:{padding:20,paddingBottom:32,gap:28},title:{alignItems:'center',gap:16,paddingVertical:20},heading:{fontFamily:serif,fontStyle:'italic',fontSize:20,fontWeight:'400'},body:{fontSize:14,lineHeight:24},stats:{flexDirection:'row',justifyContent:'space-around',gap:8},stat:{alignItems:'center',gap:6},row:{flexDirection:'row',alignItems:'center',flexWrap:'wrap',gap:8},group:{gap:12},report:{padding:18,gap:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:16},badge:{paddingHorizontal:10,paddingVertical:5,borderRadius:12,fontSize:12},button:{minHeight:44,minWidth:44,paddingHorizontal:16,paddingVertical:12,borderRadius:24,borderWidth:StyleSheet.hairlineWidth,justifyContent:'center'},modalHeader:{padding:20,gap:12},footer:{padding:16,flexDirection:'row',flexWrap:'wrap',justifyContent:'space-between',gap:12},input:{fontSize:14,lineHeight:23,minHeight:128,maxHeight:280,textAlignVertical:'top',padding:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:8}});
