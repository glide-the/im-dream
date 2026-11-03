// [Input] Actual bounded performance samples from the original RuntimeSnapshot and a pause/resume action.
// [Output] App CPU trends, measured OS-thread rankings and observed command/request activity bands.
// [Pos] Existing developer-page section; SVG only, no sampling, HTTP, task ownership or invented data.
import {Pressable,StyleSheet,View} from 'react-native';
import Svg,{Circle,Line,Path,Rect} from 'react-native-svg';
import InkLabel from './InkLabel.native';
import useInkColors from './useInkColors.native';
import {PERFORMANCE_POLICY,type PerformancePoint,type PerformanceState} from '../runtime/runtimePerformance';

const thermalNames={nominal:'正常',fair:'略高',serious:'较高',critical:'严重',unknown:'未知'};
const stateNames={closed:'采样已关闭',sampling:'正在采样',paused:'采样已暂停',background:'后台暂停采样',unavailable:'当前平台或安装包不支持CPU采样',failed:'采样读取失败'};
const phaseNames:Record<string,string>={starting:'准备中',executing:'执行中',waiting_head:'等待响应头',reading:'读取响应'};
const pct=(value:number|null|undefined)=>value==null?'未计量':`${value.toFixed(1)}%`;
const ms=(value:number|null|undefined)=>value==null?'未计量':`${value.toFixed(2)} ms`;
function path(points:readonly PerformancePoint[],read:(point:PerformancePoint)=>number|null,maximum:number) {
  const first=points[0]?.tick??0,last=points.at(-1)?.tick??first,span=Math.max(1,last-first);
  let drawing=false,result='';
  for(const point of points){const value=read(point);if(value===null){drawing=false;continue;}const x=8+(point.tick-first)/span*304,y=112-value/maximum*100;result+=`${drawing?'L':'M'}${x.toFixed(2)},${y.toFixed(2)} `;drawing=true;}
  return result;
}
export default function RuntimePerformanceCharts({state,onPause}:{state:PerformanceState;onPause:(paused:boolean)=>void}) {
  const colors=useInkColors(),text={color:colors['color-text-primary']},secondary={color:colors['color-text-secondary']};
  const points=state.points,last=points.at(-1),ranked=last?.threads.filter(item=>item.cpuPercent!==null).sort((a,b)=>b.cpuPercent!-a.cpuPercent!).slice(0,PERFORMANCE_POLICY.displayThreads)??[];
  const series=ranked.slice(0,3),palette=[colors['color-action-link'],colors['color-state-success'],colors['color-state-warning']];
  const maximum=Math.max(100,...points.map(point=>point.cpuPercent??0));
  const byActivity=new Map<string,{id:string;label:string;kind:string;phase:string;cpuPercent:number|null;last:number}>();
  points.forEach((point,index)=>point.activities.forEach(activity=>byActivity.set(activity.id,{...activity,last:index})));
  const activities=[...byActivity.values()].sort((a,b)=>b.last-a.last||Number(b.kind==='command')-Number(a.kind==='command')||(b.cpuPercent??-1)-(a.cpuPercent??-1)).slice(0,PERFORMANCE_POLICY.displayActivities);
  const first=points[0]?.tick??0,span=Math.max(1,(last?.tick??first)-first);
  return <View style={styles.section} testID="runtime-performance-section">
    <View style={styles.heading}><InkLabel accessibilityRole="header" style={[styles.title,text]}>CPU与任务活动</InkLabel>
      <Pressable accessibilityRole="button" disabled={state.status==='unavailable'||state.status==='background'} onPress={()=>onPause(state.status!=='paused')} style={styles.button}><InkLabel style={text}>{state.status==='paused'?'恢复采样':'暂停采样'}</InkLabel></Pressable></View>
    <InkLabel accessibilityLiveRegion="polite" style={secondary}>{`${stateNames[state.status]}${state.error?` · ${state.error}`:''}`}</InkLabel>
    <InkLabel style={secondary}>{`每次读取后间隔${PERFORMANCE_POLICY.intervalMs/1000}秒，最多保留${PERFORMANCE_POLICY.maxSamples}个样本。仅在本页前台采样。`}</InkLabel>
    {!last?<InkLabel style={text}>尚无实际样本</InkLabel>:<>
      <InkLabel style={text}>{`App CPU ${pct(last.cpuPercent)} · 全设备核数归一 ${pct(last.devicePercent)} · ${last.cores}核`}</InkLabel>
      <InkLabel style={secondary}>{`采样 ${new Date(last.at).toLocaleTimeString()} · 区间 ${ms(last.intervalMs)} · 系统热状态：${thermalNames[last.thermal]}${last.simulator?' · Simulator条件':''}`}</InkLabel>
    </>}
    <InkLabel style={secondary}>App进程内累计用户态和内核态CPU增量；100%表示一核满载，可超过100%。WebKit独立进程及GPU未纳入。</InkLabel>
    <View accessible accessibilityLabel={`App CPU趋势，当前${pct(last?.cpuPercent)}`} testID="runtime-cpu-chart">
      <InkLabel style={secondary}>{`CPU趋势 · 顶部${maximum.toFixed(0)}% · ${((last?.tick??first)-first)/1000|0}秒`}</InkLabel>
      <Svg width="100%" height={124} viewBox="0 0 320 124" accessible={false}>
        <Line x1="8" y1="112" x2="312" y2="112" stroke={colors['color-border-paper']}/>
        <Line x1="8" y1="12" x2="312" y2="12" stroke={colors['color-border-paper']}/>
        <Path d={path(points,point=>point.cpuPercent,maximum)} stroke={colors['color-text-primary']} strokeWidth="2" fill="none"/>
        {last?.cpuPercent!=null?<Circle cx={8+(last.tick-(points[0]?.tick??last.tick))/Math.max(1,last.tick-(points[0]?.tick??last.tick))*304} cy={112-last.cpuPercent/maximum*100} r="3" fill={colors['color-text-primary']}/>:null}
        {series.map((item,index)=><Path key={item.id} d={path(points,point=>point.threads.find(thread=>thread.id===item.id)?.cpuPercent??null,maximum)} stroke={palette[index]} strokeWidth="1.5" fill="none"/>)}
      </Svg>
      {!points.some(point=>point.cpuPercent!==null)?<InkLabel style={secondary}>等待两个连续实际样本建立区间，暂停或读取失败处保留断点。</InkLabel>:null}
      <InkLabel style={text}>App总量</InkLabel>{series.map((item,index)=><InkLabel key={item.id} style={{color:palette[index]}}>{`${item.label} #${item.id}`}</InkLabel>)}
    </View>
    <InkLabel accessibilityRole="header" style={[styles.subtitle,text]}>OS线程区间排行</InkLabel>
    {ranked.map(item=><View key={item.id} style={styles.row}><InkLabel style={text}>{`${item.label} #${item.id} · ${pct(item.cpuPercent)}`}</InkLabel>
      <View style={[styles.track,{backgroundColor:colors['color-bg-paper']}]}><View style={{height:6,width:`${Math.min(100,item.cpuPercent!)}%`,backgroundColor:colors['color-action-link']}}/></View></View>)}
    {!ranked.length?<InkLabel style={secondary}>{last?.threadsState==='unavailable'?'OS线程采样不可用，App总量继续显示。':'等待相同OS线程的连续计数。'}</InkLabel>:null}
    {last?.threadsTruncated?<InkLabel style={secondary}>线程明细为部分采样；新建、结束或未读取线程的CPU保持未归因。</InkLabel>:null}
    <InkLabel accessibilityRole="header" style={[styles.subtitle,text]}>原运行实例活动</InkLabel>
    <InkLabel style={secondary}>命令CPU仅对应原命令主执行OS线程，子线程未归因。请求条带表示采样时仍在等待或读取；共享Python/Node中的业务任务CPU未独立计量。</InkLabel>
    {activities.map(activity=><View key={activity.id} style={styles.row}>
      <InkLabel selectable style={text}>{`${activity.label} · ${activity.id}`}</InkLabel>
      <InkLabel style={secondary}>{`${new Date(points[activity.last].at).toLocaleTimeString()}观察 · ${phaseNames[activity.phase]??activity.phase}`}</InkLabel>
      <InkLabel style={secondary}>{activity.kind==='command'?`最近观察的主线程CPU ${pct(activity.cpuPercent)}`:'共享或未归因，CPU未计量'}</InkLabel>
      <Svg width="100%" height={34} viewBox="0 0 320 34" accessible={false}>
        {points.map((point,index)=>{const item=point.activities.find(entry=>entry.id===activity.id);if(!item)return null;const x=8+(point.tick-first)/span*292;return <Rect key={index} x={x} y="23" width={Math.max(2,Math.min(8,292/Math.max(1,points.length)))} height="8" fill={item.kind==='command'?colors['color-state-warning']:colors['color-action-link']}/>;})}
        {activity.kind==='command'?<Path d={path(points,point=>point.activities.find(item=>item.id===activity.id)?.cpuPercent??null,maximum)} transform="translate(0 0) scale(1 0.18)" stroke={colors['color-state-warning']} strokeWidth="5" fill="none"/>:null}
      </Svg>
    </View>)}
    {!activities.length?<InkLabel style={secondary}>{last?.commandsState==='busy'?'原命令活动读取暂忙，当前活动未知。':'当前保留样本未观察到原生命令或请求；后台业务任务状态未单独枚举。'}</InkLabel>:null}
    {last?.commandsState==='busy'?<InkLabel style={secondary}>命令清单暂忙，本次活动未知；旧观察保留其采样时间。</InkLabel>:null}
    {last?.activitiesTruncated||byActivity.size>activities.length?<InkLabel style={secondary}>活动明细按显示上限呈现，未展示项保持未归因。</InkLabel>:null}
    {last?<InkLabel style={secondary}>{`最近原生采样耗时 ${ms(last.collectionWallMs)} / 采样线程CPU ${ms(last.collectionCpuMs)}；桥接往返 ${ms(last.requestWallMs)}。图表渲染开销包含在App总量中，物理能耗尚未测量。`}</InkLabel>:null}
    <InkLabel style={secondary}>热状态沿系统返回值显示，未测量摄氏温度，发热原因需要结合实际样本确认。</InkLabel>
  </View>;
}
const styles=StyleSheet.create({section:{gap:12},heading:{flexDirection:'row',alignItems:'center',flexWrap:'wrap',justifyContent:'space-between',gap:8},title:{fontSize:22},subtitle:{fontSize:18},button:{minHeight:44,padding:10,justifyContent:'center'},row:{gap:5},track:{height:6,borderRadius:3,overflow:'hidden'}});
