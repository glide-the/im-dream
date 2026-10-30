// [Input] Original saved report, frozen sources, account timezone and shared report selection.
// [Output] Native report reading with section/result navigation, original source counts and save recovery.
// [Pos] Presentation reused by native Reflections and Timeline; it neither creates nor resumes a task.
// [Sync] 2026-10-29: keep original content, sources and confidence; only the Notion link list is bounded as in Web.
import {useState} from 'react';
import {Linking,Platform,Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import useInkColors from '../../../src/components/useInkColors.native';
import {getDateLocale} from '../i18n';
import type {ReflectionSectionKey} from '../api/reflectionsApi';
import type {AnalysisReport} from './reflectionHistory';
import useReflectionReport from '../hooks/useReflectionReport';
export interface NativeReflectionBlogProps {report:AnalysisReport;timezone:string;initialSection?:ReflectionSectionKey|null;onBack:()=>void;backLabel?:string;saveError?:string;saving?:boolean;onRetrySave?:()=>void;openLink?:(url:string)=>Promise<unknown>}
export default function ReflectionBlogPage({report,timezone,initialSection,onBack,backLabel,saveError,saving,onRetrySave,openLink=Linking.openURL}:NativeReflectionBlogProps) {
  const {t,i18n}=useTranslation(),c=useInkColors(),dateLocale=getDateLocale(i18n.language),zh=dateLocale.startsWith('zh');
  const r=useReflectionReport(report,initialSection),[sourcesOpen,setSourcesOpen]=useState(false),[linkError,setLinkError]=useState(false);
  const date=new Date(report.timestamp),fullDate=date.toLocaleDateString(dateLocale,{weekday:'long',year:'numeric',month:'long',day:'numeric',timeZone:timezone});
  const text={color:c['color-text-primary']},muted={color:c['color-text-muted']};
  const button={...s.button,borderColor:c['color-border-paper']};
  const selected=r.selectedItem;
  const open=async(url:string)=>{setLinkError(false);try{if(!url.startsWith('https://'))throw Error('REFLECTION_LINK_INVALID');await openLink(url);}catch{setLinkError(true);}};
  return <View style={[s.fill,{backgroundColor:c['color-bg-app']}]} accessibilityLabel={t('analysis.history.report')}>
    <View style={s.header}><Pressable accessibilityRole="button" style={button} onPress={onBack}><Text style={text}>← {backLabel??t('analysis.pastReflections')}</Text></Pressable></View>
    {saveError?<View style={s.notice}><Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{saveError}</Text>{onRetrySave?<Pressable accessibilityRole="button" disabled={saving} style={button} onPress={onRetrySave}><Text style={text}>{zh?'重试保存':'Retry save'}</Text></Pressable>:null}</View>:null}
    {!!report.failedSections?.length?<Text accessibilityLiveRegion="polite" style={[s.notice,{color:c['color-state-error']}]}>{zh?'部分章节未完成：':'Some sections did not complete: '}{report.failedSections.map(section=>t(`analysis.papers.${section}.title`)).join('、')}.</Text>:null}
    <View style={s.sources} accessibilityLabel={zh?'本次分析来源':'Analysis sources'}>
      <Text style={muted}>{zh?`日记范围 · ${report.analysisContent?.diary_session_ids?.length??report.stats.entries} 篇`:`Diary scope · ${report.analysisContent?.diary_session_ids?.length??report.stats.entries} entries`}</Text>
      {report.analysisContent?.agent?<Text style={muted}>{zh?'分析 Agent：':'Analysis Agent: '}{report.analysisContent.agent.agent_name}</Text>:null}
      {report.analysisContent?.notion?<View><Pressable accessibilityRole="button" accessibilityState={{expanded:sourcesOpen}} onPress={()=>setSourcesOpen(value=>!value)} style={s.sourceAction}><Text style={text}>{zh?`Notion · 已读取 ${report.analysisContent.notion.pages.length} 个页面`:`Notion · Pages read: ${report.analysisContent.notion.pages.length}`}</Text></Pressable>
        {sourcesOpen?<ScrollView style={{maxHeight:96,flexGrow:0}}>{report.analysisContent.notion.pages.map(page=>page.url?<Pressable key={page.page_id} accessibilityRole="link" onPress={()=>void open(page.url!)} style={s.sourceAction}><Text style={{color:c['color-action-link']}}>{page.title||(zh?'未命名页面':'Untitled page')}</Text></Pressable>:<Text key={page.page_id} style={muted}>{page.title||(zh?'未命名页面':'Untitled page')}</Text>)}</ScrollView>:null}
      </View>:null}
      {linkError?<Text accessibilityRole="alert" style={{color:c['color-state-error']}}>{zh?'链接暂时无法打开，可再次点击。':'The link could not be opened. Try again.'}</Text>:null}
    </View>
    <View style={[s.cover,{borderColor:c['color-border-paper']}]}><View style={[s.date,{backgroundColor:c['color-text-primary']}]}><Text style={{color:c['color-bg-paper'],letterSpacing:3}}>{date.toLocaleDateString('en',{month:'short',timeZone:timezone}).toUpperCase()}</Text><Text style={{color:c['color-bg-paper'],fontFamily:serif,fontSize:36}}>{date.toLocaleDateString('en',{day:'numeric',timeZone:timezone})}</Text><Text style={{color:c['color-bg-paper']}}>{date.toLocaleDateString('en',{year:'numeric',timeZone:timezone})}</Text></View>
      <View style={{flex:1,gap:8}}><Text style={[s.heading,text]}>{fullDate}</Text><Text style={muted}>{t('analysis.statsLabels.daysCount',{count:report.stats.days||0})} · {t('analysis.statsLabels.entriesCount',{count:report.stats.entries||0})} · {t('analysis.statsLabels.wordsCount',{value:(report.stats.words||0).toLocaleString()})}</Text></View></View>
    <View accessibilityRole="tablist" style={s.tabs}>{r.blogSections.map(section=><Pressable key={section.key} accessibilityRole="tab" accessibilityLabel={t(`analysis.papers.${section.key}.title`)} accessibilityState={{selected:r.activeSection===section.key}} onPress={()=>r.handleSectionChange(section.key)} style={[s.tab,{borderBottomColor:r.activeSection===section.key?c['color-text-primary']:'transparent'}]}><Text style={text}>{section.icon} {t(`analysis.papers.${section.key}.title`)} ({section.items.length})</Text></Pressable>)}</View>
    <ScrollView style={[s.fill,selected?{flex:0.45}:null]} contentContainerStyle={s.list}>
      {r.activeItems.map((item,index)=><Pressable key={index} accessibilityRole="button" accessibilityLabel={item.title} accessibilityState={{selected:r.selectedItemIdx===index}} onPress={()=>r.setSelectedItemIdx(r.selectedItemIdx===index?null:index)} style={[s.result,{borderColor:c['color-border-paper'],backgroundColor:r.selectedItemIdx===index?c['color-bg-hover']:c['color-bg-paper']}]}>
        <Text style={muted}>{String(index+1).padStart(2,'0')}</Text><Text style={[s.heading,text,{flex:1}]}>{item.title}</Text><Text style={muted}>›</Text>
      </Pressable>)}
    </ScrollView>
    {selected?<View style={[s.fill,{borderTopWidth:StyleSheet.hairlineWidth,borderTopColor:c['color-border-paper']}]}>
      <View style={s.header}><Text style={[muted,{flex:1}]}>{t(`analysis.papers.${r.activeSection}.title`)} · {r.selectedItemIdx!+1} / {r.activeItems.length}</Text><Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.close')} style={button} onPress={()=>r.setSelectedItemIdx(null)}><Text style={text}>×</Text></Pressable></View>
      <ScrollView contentContainerStyle={s.list} accessibilityLabel={selected.title}><Text style={[s.heading,text]}>{selected.title}</Text><Text selectable style={[s.body,{color:c['color-text-body']}]}>{r.activeSectionObj?.kind==='trait'?selected.evidence:selected.description}</Text>
        {r.activeSectionObj?.kind==='trait'?<><View accessibilityLabel={`Confidence ${selected.confidence}`} style={s.row}>{[1,2,3,4,5].map(index=><View key={index} style={{height:3,flex:1,backgroundColor:index<=r.cfill(selected.confidence)?c['color-text-muted']:c['color-border-paper'],opacity:index<=r.cfill(selected.confidence)?0.8:0.4}}/>)}</View><Text selectable style={muted}>{selected.evidence}</Text></>:<Text style={muted}>Confidence · {selected.confidence}</Text>}
        <View style={[s.related,{borderColor:c['color-border-paper']}]}><Text style={muted}>Related Notes</Text><Text style={[muted,{fontStyle:'italic'}]}>Related notes coming soon</Text></View>
      </ScrollView>
      <View style={[s.player,{backgroundColor:c['color-bg-paper'],borderTopColor:c['color-border-paper']}]}><Text numberOfLines={1} style={[text,{flex:1,fontFamily:serif}]}>{selected.title}</Text><Pressable accessibilityRole="button" accessibilityLabel={zh?'上一条':'Previous result'} disabled={r.selectedItemIdx===0} onPress={r.goToPrev} style={[button,{opacity:r.selectedItemIdx===0?0.4:1}]}><Text style={text}>◀</Text></Pressable><Text style={muted}>{r.selectedItemIdx!+1}/{r.activeItems.length}</Text><Pressable accessibilityRole="button" accessibilityLabel={zh?'下一条':'Next result'} disabled={r.selectedItemIdx===r.activeItems.length-1} onPress={r.goToNext} style={[button,{opacity:r.selectedItemIdx===r.activeItems.length-1?0.4:1}]}><Text style={text}>▶</Text></Pressable></View>
    </View>:null}
  </View>;
}
const serif=Platform.OS==='ios'?'Georgia':'serif';
const s=StyleSheet.create({sourceAction:{minHeight:44,paddingVertical:8,justifyContent:'center'},fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:16,paddingVertical:8},notice:{padding:12,gap:8},sources:{paddingHorizontal:16,paddingBottom:10,gap:6,flexShrink:0},cover:{padding:16,gap:16,flexDirection:'row',alignItems:'center',borderBottomWidth:StyleSheet.hairlineWidth},date:{width:76,borderRadius:12,alignItems:'center',padding:10,gap:3},heading:{fontFamily:serif,fontStyle:'italic',fontSize:18},tabs:{flexDirection:'row',flexWrap:'wrap',paddingHorizontal:12},tab:{minHeight:44,padding:10,borderBottomWidth:2},list:{padding:16,gap:12,paddingBottom:24},result:{padding:14,gap:12,flexDirection:'row',alignItems:'center',borderWidth:StyleSheet.hairlineWidth,borderRadius:10},body:{fontSize:14,lineHeight:25},row:{flexDirection:'row',gap:4},related:{paddingTop:14,gap:8,borderTopWidth:StyleSheet.hairlineWidth},player:{flexDirection:'row',alignItems:'center',gap:8,padding:10,borderTopWidth:StyleSheet.hairlineWidth},button:{minHeight:44,minWidth:44,paddingHorizontal:10,paddingVertical:10,justifyContent:'center',alignItems:'center',borderRadius:22,borderWidth:StyleSheet.hairlineWidth}});
