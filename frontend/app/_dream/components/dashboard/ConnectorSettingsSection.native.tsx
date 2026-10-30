// [Input] Account-scoped resource owner, original summary state and caller-owned Settings navigation.
// [Output] Native resource directory and persistent Notion/current-MCP detail scenes.
// [Pos] Settings Work/Resources coordinator; server business and App/backend lifetime retain their owners.
// [Sync] 2026-10-29: connect original resource state to native content, visibility and operation callbacks.
import {useEffect,useState,useSyncExternalStore} from 'react';
import {ActivityIndicator,BackHandler,Platform,Pressable,ScrollView,StyleSheet,View} from 'react-native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import type {NativeSettingsResources} from '../../../../src/platform/settingsResources.native';
import useConnectorSummary from '../../hooks/useConnectorSummary';
import ClaudeMcpResourceSection from '../claude-mcp/ClaudeMcpResourceSection.native';
import ClaudeMcpServerDetailPage from '../claude-mcp/ClaudeMcpServerDetailPage.native';
import ConnectorNotionDetailPage from './ConnectorNotionDetailPage.native';
interface Props {ownerId:string;resources:NativeSettingsResources;active:boolean;focusNonce:number;origin:string;onDetailChange:(detail:boolean)=>void}
export default function ConnectorSettingsSection({ownerId,resources,active,focusNonce,origin,onDetailChange}:Props){
 const c=useInkColors(),visible=useSyncExternalStore(resources.watchVisibility,resources.isVisible),enabled=active&&visible;
 const [detail,setDetail]=useState<'notion'|'mcp'|null>(null),[notionVisited,setNotionVisited]=useState(false),[server,setServer]=useState<string|null>(null),[readNonce,setReadNonce]=useState(0);
 const summary=useConnectorSummary({ownerId,authenticated:true,api:resources.connector,active:enabled&&detail===null,focusNonce:focusNonce+readNonce,observation:resources.observation});
 useEffect(()=>{setDetail(null);},[focusNonce]);
 useEffect(()=>{onDetailChange(detail!==null);},[detail,onDetailChange]);
 const back=()=>{setDetail(null);setReadNonce(value=>value+1);};
 useEffect(()=>{if(!enabled||detail!=='mcp'||Platform.OS!=='android')return;const listener=BackHandler.addEventListener('hardwareBackPress',()=>{back();return true;});return()=>listener.remove();},[enabled,detail]);
 const text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']};
 const card=(title:string,description:string,status:string,onPress?:()=>void)=><Pressable accessibilityRole="button" accessibilityLabel={title} disabled={!onPress} accessibilityState={{disabled:!onPress}} onPress={onPress} style={[s.card,{borderColor:c['color-border-paper'],backgroundColor:c['color-bg-surface-solid'],opacity:onPress?1:0.6}]}><View style={s.row}><InkLabel style={[text,{fontSize:18}]}>{title}</InkLabel><InkLabel style={secondary}>{status}</InkLabel></View><InkLabel style={secondary}>{description}</InkLabel></Pressable>;
 return <View style={s.fill}>
  <ScrollView style={[s.fill,detail!==null?s.hidden:undefined]} contentContainerStyle={s.content} accessibilityElementsHidden={!enabled||detail!==null} importantForAccessibility={enabled&&detail===null?'auto':'no-hide-descendants'}>
   <InkLabel accessibilityRole="header" style={[text,{fontSize:22}]}>资源链接</InkLabel>
   {summary.loading?<ActivityIndicator color={c['color-text-primary']}/>:null}{summary.error?<InkLabel accessibilityRole="alert" style={{color:c['color-state-error']}}>{summary.error}</InkLabel>:null}
   {card('Notion',`在详情页管理账号授权、数据库、页面和索引同步。${summary.notionConnector?`最近交互 ${summary.notionLastInteraction}`:'暂无交互'} · ${summary.notionConnector?.sources.length??0} 个来源`,summary.notionStatusLabel,()=>{setNotionVisited(true);setDetail('notion');})}
   {card('飞书','飞书资源连接开放后，可从这里管理已授权知识源。','占位 · 暂不可用')}
   <ClaudeMcpResourceSection api={resources.mcp} active={enabled&&detail===null} remember={resources.remember} forget={resources.forget} onAuthorize={resources.authorize} onOpenServerDetail={name=>{setServer(name);setDetail('mcp');}}/>
   {card('CLI 执行器','本地 CLI 连接沿现有资源开放范围。','暂不可用')}
  </ScrollView>
  {notionVisited?<View style={[s.fill,detail!=='notion'?s.hidden:undefined]} accessibilityElementsHidden={!enabled||detail!=='notion'} importantForAccessibility={enabled&&detail==='notion'?'auto':'no-hide-descendants'}><ConnectorNotionDetailPage ownerId={ownerId} api={resources.connector} observation={resources.observation} active={enabled&&detail==='notion'} origin={origin} onBack={back}/></View>:null}
  {server?<View style={[s.fill,detail!=='mcp'?s.hidden:undefined]} accessibilityElementsHidden={!enabled||detail!=='mcp'} importantForAccessibility={enabled&&detail==='mcp'?'auto':'no-hide-descendants'}><ClaudeMcpServerDetailPage key={server} serverName={server} api={resources.mcp} active={enabled&&detail==='mcp'} remember={resources.remember} forget={resources.forget} onAuthorize={resources.authorize} onBack={back}/></View>:null}
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},hidden:{display:'none'},content:{padding:20,gap:20,paddingBottom:32},card:{gap:10,padding:16,borderWidth:1,borderRadius:16,minHeight:56},row:{flexDirection:'row',alignItems:'center',flexWrap:'wrap',gap:12}});
