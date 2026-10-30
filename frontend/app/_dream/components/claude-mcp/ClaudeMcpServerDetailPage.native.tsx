// [Input] Original server detail/CAS state, native HTTP and concrete OAuth/operation storage actions.
// [Output] Native configuration, authentication, usage-policy switches and read-only tools/resources/prompts inventory.
// [Pos] Settings Resources detail presentation; server permissions and SDK OAuth retain their existing owners.
// [Sync] 2026-10-29: reuse the shared state, original auth predicates and queued revision writes; no tool execution controls.
import {useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,Alert,Pressable,ScrollView,StyleSheet,Switch,TextInput,View} from 'react-native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import type {ClaudeMcpApi,ClaudeMcpOperation} from '../../api/claudeMcpApi';
import useClaudeMcpServer from '../../hooks/useClaudeMcpServer';
import {canStartClaudeMcpAuth,claudeMcpAuthActionLabel} from './authPolicy';
import {ACTIVE_STATES,AUTH_STATE_LABELS,authStateOf,canLogout,connectionSummary,connectionStateLabel,operationErrorMessage,formatDateTime,type CapabilityTab,type ToolFilter} from './mcpServerPresentation';
interface Props {serverName:string;api:ClaudeMcpApi;active:boolean;remember:(id:string)=>boolean;forget:(id?:string)=>void;onBack:()=>void;onAuthorize:(operation:ClaudeMcpOperation)=>Promise<void>;confirmRemove?:(message:string)=>Promise<boolean>}
const confirmNative=(message:string)=>new Promise<boolean>(resolve=>Alert.alert('移除 MCP 服务',message,[{text:'取消',style:'cancel',onPress:()=>resolve(false)},{text:'移除',style:'destructive',onPress:()=>resolve(true)}],{cancelable:true,onDismiss:()=>resolve(false)}));
const FILTERS:readonly [ToolFilter,string][]=[['all','全部'],['read_only','只读'],['destructive','破坏性'],['open_world','开放世界'],['unspecified','未声明']];
export default function ClaudeMcpServerDetailPage({serverName,api,active,remember,forget,onBack,onAuthorize,confirmRemove=confirmNative}:Props){
 const c=useInkColors(),state=useClaudeMcpServer({serverName,api,active,remember,forget,onBack,confirmRemove});
 const {capability,server,inventory,operation,activeTab,setActiveTab,searchQuery,setSearchQuery,toolFilter,setToolFilter,loading,inventoryLoading,busyAction,pageError,inventoryError,appSettings,appSettingsError,appUsagePolicySaving,editAppEnabled,editAppLowRiskToolCalls,editAppUiMessages,editing,setEditing,editDisplayName,setEditDisplayName,editTransport,setEditTransport,editUrl,setEditUrl,editStdioProfile,setEditStdioProfile,editEnabled,setEditEnabled,effectiveState,visibleTools,startAuth,cancelAuth,logout,saveConfiguration,remove,updateAppUsagePolicyDraft,tabCounts}=state;
 const [authorizationError,setAuthorizationError]=useState(''),[opening,setOpening]=useState(false),removeInFlight=useRef(false);
 const text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']},busy=Boolean(busyAction);
 const copy=(value:string|null|undefined,error=false)=>value?<InkLabel selectable accessibilityRole={error?'alert':undefined} style={error?{color:c['color-state-error']}:text}>{value}</InkLabel>:null;
 const button=(label:string,onPress:()=>void,disabled=false)=><Pressable accessibilityRole="button" accessibilityLabel={label} disabled={disabled} accessibilityState={{disabled}} onPress={onPress} style={[s.button,{borderColor:c['color-border-paper'],opacity:disabled?0.5:1}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
 const section=(label:string,body:ReactNode)=><View style={[s.section,{borderTopColor:c['color-border-paper']}]}><InkLabel accessibilityRole="header" style={[text,s.heading]}>{label}</InkLabel>{body}</View>;
 const input=(label:string,value:string,change:(value:string)=>void)=><View style={s.gap}>{copy(label)}<TextInput accessibilityLabel={label} value={value} onChangeText={change} autoCapitalize="none" autoCorrect={false} style={[s.input,text,{borderColor:c['color-border-paper']}]}/></View>;
 async function authorize(){if(!operation||opening)return;setAuthorizationError('');setOpening(true);try{await onAuthorize(operation);}catch{setAuthorizationError('授权页面未完成，请重试或取消这次认证。');}finally{setOpening(false);}}
 async function removeOnce(){if(removeInFlight.current)return;removeInFlight.current=true;try{await remove();}finally{removeInFlight.current=false;}}
 return <View style={[s.fill,{backgroundColor:c['color-bg-app']}]}>
  <View style={s.header}>{button('← 资源',onBack)}<InkLabel accessibilityRole="header" style={[text,s.title]}>{server?.display_name||serverName}</InkLabel></View>
  <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.content}>
   {loading?<ActivityIndicator color={c['color-text-primary']}/>:null}{copy(pageError,true)}
   {server?<>
    {copy(connectionStateLabel(server,effectiveState))}<InkLabel style={secondary}>{connectionSummary(server,effectiveState,inventory?.tool_count)}</InkLabel><InkLabel style={secondary}>{AUTH_STATE_LABELS[authStateOf(server)]}</InkLabel>
    {copy(server.url||server.stdio_profile_key)}
    <View style={s.row}>
     {server.removable?button(editing?'取消编辑':'编辑配置',()=>setEditing(value=>!value),busy):null}
     {effectiveState&&canStartClaudeMcpAuth(server,effectiveState)?button(claudeMcpAuthActionLabel(server),()=>void startAuth(),busy):null}
     {canLogout(server,effectiveState)?button('退出认证',()=>void logout(),busy):null}
     {server.removable?button('移除',()=>void removeOnce(),busy):null}
    </View>
   </>:null}
   {editing&&server?section('编辑配置',<>
    {input('显示名称',editDisplayName,setEditDisplayName)}
    <View accessibilityRole="radiogroup" accessibilityLabel="MCP 传输方式" style={s.row}>{(['streamable_http','sse','stdio'] as const).map(value=><Pressable key={value} accessibilityRole="radio" accessibilityLabel={value} accessibilityState={{checked:editTransport===value}} aria-checked={editTransport===value} onPress={()=>setEditTransport(value)} style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:editTransport===value?c['color-bg-hover']:'transparent'}]}><InkLabel style={text}>{value}</InkLabel></Pressable>)}</View>
    {editTransport==='stdio'?input('Stdio profile key',editStdioProfile,setEditStdioProfile):input('MCP 服务 URL',editUrl,setEditUrl)}
    <View style={s.row}>{copy('启用连接')}<Switch accessibilityLabel="启用连接" value={editEnabled} onValueChange={setEditEnabled}/></View>
    {button(busyAction==='save'?'保存中…':'保存配置',()=>void saveConfiguration(),busy)}
   </>):null}
   {operation&&ACTIVE_STATES.includes(operation.state)?section('认证',<>
    {operation.state==='waiting_for_user'?button(opening?'正在打开授权页面…':'打开授权页面',()=>void authorize(),opening||!operation.authorization_url):copy('正在处理认证结果…')}
    {button('取消认证',()=>void cancelAuth(),busy)}{copy(operationErrorMessage(operation),true)}
   </>):null}{copy(authorizationError,true)}
   {section('MCP 使用策略',<>
    {appSettings?<>
     <View style={s.row}>{copy('启用 App')}<Switch accessibilityLabel="启用 App" disabled={busy} value={editAppEnabled} onValueChange={value=>updateAppUsagePolicyDraft('enabled',value)}/></View>
     <View style={s.row}>{copy('低风险工具调用')}<Switch accessibilityLabel="低风险工具调用" disabled={!editAppEnabled||busy} value={editAppLowRiskToolCalls} onValueChange={value=>updateAppUsagePolicyDraft('lowRiskToolCalls',value)}/></View>
     <View style={s.row}>{copy('Chat 消息交互')}<Switch accessibilityLabel="Chat 消息交互" disabled={!editAppEnabled||busy} value={editAppUiMessages} onValueChange={value=>updateAppUsagePolicyDraft('uiMessages',value)}/></View>
     {appUsagePolicySaving?copy('正在自动保存…'):null}{copy(appSettingsError,true)}
    </>:copy(appSettingsError||'正在读取此连接的 App 设置。',Boolean(appSettingsError))}
   </>)}
   {section('能力清单',<>
    {inventoryLoading?<ActivityIndicator color={c['color-text-primary']}/>:null}{copy(inventoryError,true)}
    {inventory?.server_info?copy(`${inventory.server_info.name} · ${inventory.server_info.version}`):null}
    <View accessibilityRole="tablist" accessibilityLabel="MCP 能力类型" style={s.row}>{(['tools','resources','prompts'] as const).map(tab=><Pressable key={tab} accessibilityRole="tab" accessibilityLabel={tab} accessibilityState={{selected:activeTab===tab}} onPress={()=>setActiveTab(tab)} style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:activeTab===tab?c['color-bg-hover']:'transparent'}]}><InkLabel style={text}>{`${tab} (${tabCounts[tab]??0})`}</InkLabel></Pressable>)}</View>
    {activeTab==='tools'?<>
     <TextInput accessibilityLabel="搜索 MCP 工具" placeholder="搜索工具" placeholderTextColor={c['color-text-secondary']} value={searchQuery} onChangeText={setSearchQuery} style={[s.input,text,{borderColor:c['color-border-paper']}]}/>
     <View accessibilityRole="radiogroup" accessibilityLabel="工具注解筛选" style={s.row}>{FILTERS.map(([value,label])=><Pressable key={value} accessibilityRole="radio" accessibilityLabel={label} accessibilityState={{checked:toolFilter===value}} aria-checked={toolFilter===value} onPress={()=>setToolFilter(value)} style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:toolFilter===value?c['color-bg-hover']:'transparent'}]}><InkLabel style={text}>{label}</InkLabel></Pressable>)}</View>
     {!inventoryLoading&&inventory&&visibleTools.length===0?copy('没有匹配的工具。'):null}
     {visibleTools.map(tool=><View key={tool.name} style={[s.item,{borderBottomColor:c['color-border-paper']}]}>{copy(tool.name)}<InkLabel style={secondary}>{tool.description||'暂无描述'}</InkLabel><InkLabel style={secondary}>{`readOnly ${String(tool.annotations.read_only)} · destructive ${String(tool.annotations.destructive)} · openWorld ${String(tool.annotations.open_world)}`}</InkLabel></View>)}
     {inventory?.tools_truncated?copy('工具清单已截断。'):null}
    </>:activeTab==='resources'?<>
     {!inventoryLoading&&inventory?.resources.length===0?copy('服务未返回资源。'):null}
     {inventory?.resources.map(resource=><View key={resource.uri} style={[s.item,{borderBottomColor:c['color-border-paper']}]}>{copy(resource.name)}<InkLabel selectable style={secondary}>{resource.uri}</InkLabel>{copy(resource.description)}{copy(resource.mime_type)}</View>)}
    </>:<>
     {!inventoryLoading&&inventory?.prompts.length===0?copy('服务未返回提示模板。'):null}
     {inventory?.prompts.map(prompt=><View key={prompt.name} style={[s.item,{borderBottomColor:c['color-border-paper']}]}>{copy(prompt.name)}{copy(prompt.description)}{prompt.arguments?.map(argument=><InkLabel key={argument.name} style={secondary}>{`${argument.name}${argument.required?' *':''}${argument.description?` · ${argument.description}`:''}`}</InkLabel>)}</View>)}
    </>}
    {inventory?<InkLabel style={secondary}>{`最近读取 ${formatDateTime(inventory.refreshed_at)}`}</InkLabel>:null}
   </>)}
  </ScrollView>
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},header:{padding:12,flexDirection:'row',alignItems:'center',gap:12},title:{fontSize:22,flex:1},heading:{fontSize:18},content:{padding:20,gap:16,paddingBottom:32},gap:{gap:8},row:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',gap:10},button:{minHeight:44,padding:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:10,justifyContent:'center'},input:{minHeight:44,padding:12,borderWidth:1,borderRadius:10},section:{paddingTop:20,borderTopWidth:StyleSheet.hairlineWidth,gap:12},item:{paddingVertical:12,borderBottomWidth:StyleSheet.hairlineWidth,gap:8}});
