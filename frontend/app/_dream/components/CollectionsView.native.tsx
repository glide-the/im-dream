// [Sync] 2026-10-29: retain original narrow card typography, size, opacity, dots and placeholder gradient.
// [Sync] 2026-10-29: ignore hidden/report layout events so they cannot overwrite the saved anchor or load earlier days.
// [Input] Original Timeline state, account timezone, authenticated native HTTP and saved-report reader.
// [Output] Native Timeline with the original date/report rows, historical image/comments and earlier-page reads.
// [Pos] More destination; list and report instances persist while hidden, server tasks remain independently owned.
// [Sync] 2026-10-29: share Web data state and card geometry; native scroll/image controls replace DOM access.
import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {ActivityIndicator,Image,Modal,Pressable,SafeAreaView,ScrollView,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../src/components/InkLabel.native';
import Svg,{Defs,LinearGradient,Rect,Stop} from 'react-native-svg';
import {clientFetch} from '../../../src/platform/transport';
import useInkColors from '../../../src/components/useInkColors.native';
import type {ReflectionsApi} from '../api/reflectionsApi';
import type {VoiceConfig} from '../api/voiceApi';
import {getDateLocale} from '../i18n';
import useTimeline,{type TimelineRow} from '../hooks/useTimeline';
import ReflectionBlogPage from './ReflectionBlogPage.native';
import type {AnalysisReport} from './reflectionHistory';
import {CARD_HEIGHT,SLOT_HEIGHT,LOAD_THRESHOLD_PX,makeTimelineDay,formatDate,getTextPreview,extractCompleteSentence,getIconForVoice} from './timelinePresentation';
type Props={timezone:string;authenticated:boolean;api:ReflectionsApi;voiceConfigs:Record<string,VoiceConfig>;onBack:()=>void;active?:boolean;transport?:typeof fetch};
const imageUri=(base64:string)=>`data:image/${base64.startsWith('iVBOR')?'png':'jpeg'};base64,${base64}`;
export default function CollectionsView({timezone,authenticated,api,voiceConfigs,onBack,active=true,transport=clientFetch}:Props){
 const {t,i18n}=useTranslation(),c=useInkColors(),dateLocale=getDateLocale(i18n.language);
 const [report,setReport]=useState<AnalysisReport|null>(null),[pendingInitialScroll,setPendingInitialScroll]=useState(true),[scrollTop,setScrollTop]=useState(0),[viewport,setViewport]=useState(0);
 const scroller=useRef<ScrollView>(null),rows=useRef<TimelineRow[]>([]),top=useRef(0),anchor=useRef<{key:string;delta:number}|null>(null);
 const rememberScroll=useCallback(()=>{const index=Math.max(0,Math.floor((top.current-20)/SLOT_HEIGHT)),row=rows.current[index];if(row)anchor.current={key:row.key,delta:top.current-index*SLOT_HEIGHT};},[]);
 const data=useTimeline({authenticated,timezone,dateLocale,pendingInitialScroll,setPendingInitialScroll,rememberScroll,transport,historyApi:api.getAnalysisHistory});
 rows.current=data.timelineRows;
 useEffect(()=>{if(!active)data.setViewingImage(null);},[active]);
 useLayoutEffect(()=>{if(!active||report){if(!anchor.current)rememberScroll();return;}if(pendingInitialScroll||!anchor.current)return;const saved=anchor.current,index=data.timelineRows.findIndex(row=>row.key===saved.key);if(index>=0){top.current=index*SLOT_HEIGHT+saved.delta;setScrollTop(top.current);scroller.current?.scrollTo({y:top.current,animated:false});}anchor.current=null;},[data.timelineRows,pendingInitialScroll,active,report]);
 const body={color:c['color-text-body']},text={color:c['color-text-primary']},muted={color:c['color-text-muted']},button=[s.button,{borderColor:c['color-border-paper']}];
 const initialBottom=(height:number)=>{if(!active||report||data.initialLoading||data.historyLoading||!pendingInitialScroll||!viewport)return;const y=Math.max(0,height-viewport);top.current=y;setScrollTop(y);scroller.current?.scrollTo({y,animated:false});setPendingInitialScroll(false);};
 useEffect(()=>{if(!active||report||data.initialLoading||data.historyLoading||!pendingInitialScroll||!viewport)return;const frame=requestAnimationFrame(()=>initialBottom(Math.max(80,(data.timelineRows.length-1)*SLOT_HEIGHT+CARD_HEIGHT+44)));return()=>cancelAnimationFrame(frame);},[active,report,data.initialLoading,data.historyLoading,pendingInitialScroll,viewport,data.timelineRows.length]);
 const first=Math.max(0,Math.floor(Math.max(0,scrollTop-20)/SLOT_HEIGHT)-5),last=viewport?Math.min(data.timelineRows.length,first+Math.ceil(viewport/SLOT_HEIGHT)+11):data.timelineRows.length;
 const image=data.viewingImage,comments=image?data.allCommentsByDate.get(image.date)??[]:[];
 const starred=comments.filter(comment=>comment.feedback==='star'),chatted=comments.filter(comment=>comment.chatHistory?.length);
 const visibleComments=starred.length?starred:[...(chatted.length?chatted:comments)].sort((a,b)=>(b.appliedAt||b.computedAt)-(a.appliedAt||a.computedAt)).slice(0,1);
 return <View style={[s.fill,{backgroundColor:c['color-bg-app']}]}>
  <View style={[s.fill,report?s.hidden:undefined]} accessibilityElementsHidden={Boolean(report)} importantForAccessibility={report?'no-hide-descendants':'auto'}>
   <View style={s.header}><Pressable accessibilityRole="button" onPress={onBack} style={button}><InkLabel style={text}>{`← ${t('nav.more')}`}</InkLabel></Pressable><InkLabel accessibilityRole="header" style={[s.heading,text]}>{t('nav.timeline')}</InkLabel></View>
   {data.initialLoading?<ActivityIndicator color={c['color-text-primary']}/>:<ScrollView ref={scroller} accessibilityLabel={t('nav.timeline')} style={s.fill} scrollEventThrottle={32}
    onLayout={event=>{const height=event.nativeEvent.layout.height;if(active&&!report&&height>0)setViewport(height);}} onContentSizeChange={(_width,height)=>initialBottom(height)}
    onScroll={event=>{if(!active||report)return;const y=event.nativeEvent.contentOffset.y;top.current=y;setScrollTop(y);if(active&&!pendingInitialScroll&&y<LOAD_THRESHOLD_PX)void data.loadPastChunk();}}>
    <View style={{height:Math.max(80,(data.timelineRows.length-1)*SLOT_HEIGHT+CARD_HEIGHT+44),position:'relative'}}>
     <View pointerEvents="none" style={{position:'absolute',top:20,bottom:20,left:'50%',width:2,backgroundColor:c['color-border-paper']}}/>
     {data.hasMorePast||data.hasMoreAnalyses||data.historyError?<Pressable accessibilityRole="button" accessibilityLabel={data.historyError?`${t('analysis.history.failed')} ${t('analysis.history.retry')}`:undefined} disabled={data.loadingPast||data.historyLoading}
      onPress={()=>{if(data.historyError)void data.loadAnalysisHistory(data.analysisReports.length===0);else void data.loadPastChunk();}} style={[button,s.earlier,{backgroundColor:c['color-bg-paper']}]}>
      <InkLabel style={muted}>{data.historyError?t('analysis.history.retry'):data.loadingPast||data.historyLoading?'Loading…':'Load earlier days'}</InkLabel>
     </Pressable>:null}
     {data.timelineRows.slice(first,last).map((row,localIndex)=>{const index=first+localIndex,day=row.day??makeTimelineDay(new Date(`${row.date}T12:00:00`)),dayData=data.timelineByDate.get(row.date),picture=dayData?.picture;
      const description=row.report?t('analysis.pastReflections'):day.isToday&&!picture?'':data.firstLineByDate.get(row.date)||getTextPreview(data.textByDate.get(row.date)??'')||(dayData?.comments.length?t('timeline.entryCount',{count:dayData.comments.length}):'');
      return <View key={row.key} style={{position:'absolute',top:index*SLOT_HEIGHT+20,left:'6%',width:'88%',height:CARD_HEIGHT,zIndex:data.timelineRows.length-index}}>
       <View pointerEvents="none" style={{position:'absolute',top:'50%',left:'50%',width:14,height:14,transform:[{translateX:-7},{translateY:-7}],borderRadius:7,borderWidth:3,borderColor:c['color-bg-app'],backgroundColor:row.report||dayData?c['color-state-success']:day.isToday?c['color-text-secondary']:c['color-border-neutral'],zIndex:10}}/>
       <Pressable accessibilityRole={row.report||picture?'button':undefined} disabled={!row.report&&!picture}
        accessibilityLabel={row.report?t('analysis.history.open',{date:new Date(row.report.timestamp).toLocaleString(dateLocale,{timeZone:timezone})}):picture?picture.prompt||formatDate(day.date,dateLocale):undefined}
        onPress={()=>{if(row.report){rememberScroll();setReport(row.report);}else if(picture)void data.handleImageClick(picture);}}
        style={[s.card,{backgroundColor:c['color-bg-app'],opacity:day.isPast&&!row.report&&!dayData?0.5:1}]}>
        <View style={{flex:1,paddingLeft:8}}><InkLabel style={[{color:day.isToday?c['color-text-primary']:c['color-text-secondary']},s.date]}>{day.isToday?t('timeline.today'):formatDate(day.date,dateLocale)}</InkLabel><InkLabel numberOfLines={2} style={{color:c['color-text-secondary'],fontSize:12,lineHeight:16.8}}>{description}</InkLabel></View>
        {picture&&!row.report?<Image source={{uri:imageUri(picture.base64)}} accessibilityLabel={picture.prompt} style={s.thumbnail}/>:<View style={s.thumbnail}><Svg width={64} height={64} style={StyleSheet.absoluteFill}><Defs><LinearGradient id={`timeline-${row.key}`} x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor={day.isFuture?c['color-bg-app']:c['color-bg-paper']}/><Stop offset="1" stopColor={day.isFuture?c['color-bg-surface-solid']:c['color-bg-app']}/></LinearGradient></Defs><Rect x={1} y={1} width={62} height={62} rx={6} stroke={c['color-border-paper']} strokeWidth={2} strokeDasharray="6 4" fill={`url(#timeline-${row.key})`}/></Svg><View style={[StyleSheet.absoluteFill,s.placeholder]}><InkLabel style={muted}>{row.report?'📖':''}</InkLabel></View></View>}
       </Pressable>
      </View>;
     })}
    </View>
   </ScrollView>}
  </View>
  {report?<ReflectionBlogPage key={report.id} report={report} timezone={timezone} backLabel={t('nav.timeline')} onBack={()=>setReport(null)}/>:null}
  <Modal visible={Boolean(image)&&active} animationType="fade" onRequestClose={()=>data.setViewingImage(null)} supportedOrientations={['portrait','landscape']}>
   {image?<SafeAreaView style={[s.fill,{backgroundColor:c['color-bg-app']}]}><View style={s.header}><InkLabel style={[text,{flex:1}]}>{formatDate(image.date,dateLocale)}</InkLabel><Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.close')} onPress={()=>data.setViewingImage(null)} style={button}><InkLabel style={text}>×</InkLabel></Pressable></View>
    <Image source={{uri:imageUri(image.full_base64||image.base64)}} accessibilityLabel={image.prompt} resizeMode="contain" style={{width:'100%',height:'40%'}}/>
    <InkLabel accessibilityRole="header" style={[s.heading,muted,{padding:16}]}>Starred Comments</InkLabel><ScrollView contentContainerStyle={s.comments}>
     {data.loadingCommentsForDate===image.date?<InkLabel style={muted}>Loading comments...</InkLabel>:!visibleComments.length?<InkLabel style={muted}>No comments for this day</InkLabel>:visibleComments.map(comment=><View key={comment.id} style={[s.comment,{borderColor:c['color-border-paper'],backgroundColor:c['color-bg-paper']}]}>
      <InkLabel style={body}>{`${getIconForVoice(comment.icon)} ${voiceConfigs[comment.voice]?.name||comment.voice}${comment.feedback==='star'?' ⭐':''}${comment.chatHistory?.length?' 💬':''}`}</InkLabel><InkLabel style={[muted,{fontStyle:'italic'}]}>{`“${extractCompleteSentence(comment.textSnapshot||'',comment.phrase)}”`}</InkLabel><InkLabel selectable style={body}>{comment.comment}</InkLabel>
     </View>)}
    </ScrollView><InkLabel style={[muted,{padding:16}]}>{t('timeline.entryCount',{count:comments.length})}</InkLabel>
   </SafeAreaView>:null}
  </Modal>
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},hidden:{display:'none'},header:{paddingHorizontal:16,paddingVertical:8,gap:12,flexDirection:'row',alignItems:'center'},heading:{fontSize:22},date:{fontSize:13,fontWeight:'600',marginBottom:4},button:{minHeight:44,minWidth:44,padding:10,justifyContent:'center',alignItems:'center',borderWidth:StyleSheet.hairlineWidth,borderRadius:22},earlier:{position:'absolute',top:0,alignSelf:'center',zIndex:1000},card:{flex:1,padding:8,gap:12,flexDirection:'row',alignItems:'center',borderRadius:8},thumbnail:{width:64,height:64,borderRadius:6},placeholder:{alignItems:'center',justifyContent:'center'},comments:{padding:16,gap:16},comment:{borderWidth:StyleSheet.hairlineWidth,borderRadius:8,padding:16,gap:12}});
