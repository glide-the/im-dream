// [Input] Original MCP list state/API, operation-ID storage and concrete native authorization action.
// [Output] Native server cards, transport-specific creation, authorization/cancel/logout and removal controls.
// [Pos] Settings Resources presentation; backend capability, auth classification and revisions retain authority.
// [Sync] 2026-10-29: render the shared original state without copying CLI/OAuth or server execution logic.
import {useEffect,useState} from 'react';
import {ActivityIndicator,KeyboardAvoidingView,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,TextInput,View} from 'react-native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import type {ClaudeMcpApi,ClaudeMcpOperation} from '../../api/claudeMcpApi';
import useClaudeMcpResources from '../../hooks/useClaudeMcpResources';
import {canStartClaudeMcpAuth,claudeMcpAuthActionLabel} from './authPolicy';
import {ACTIVE_STATES,SCOPE_LABELS,serverStatusLabel,canLogout,canDetectConnection,safeOperationError,messageForCapability,operationFor} from './mcpResourcePresentation';
interface Props {api:ClaudeMcpApi;active:boolean;remember:(id:string)=>boolean;forget:(id?:string)=>void;onOpenServerDetail:(name:string)=>void;onAuthorize:(operation:ClaudeMcpOperation)=>Promise<void>}
export default function ClaudeMcpResourceSection({api,active,remember,forget,onOpenServerDetail,onAuthorize}:Props){
 const c=useInkColors(),state=useClaudeMcpResources({api,active,remember,forget});
 const {capability,servers,operations,loading,busyServer,serverName,setServerName,serverUrl,setServerUrl,serverTransport,setServerTransport,stdioProfileKey,setStdioProfileKey,addDialogOpen,setAddDialogOpen,configuring,configurationError,setConfigurationError,error,load,start,configure,cancel,logout,remove}=state;
 const [authorizationError,setAuthorizationError]=useState<string|null>(null),[openingAuthorization,setOpeningAuthorization]=useState<string|null>(null);
 useEffect(()=>{if(!active)setAddDialogOpen(false);},[active]);
 const text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']};
 const button=(label:string,onPress:()=>void,disabled=false)=><Pressable accessibilityRole="button" accessibilityLabel={label} disabled={disabled} accessibilityState={{disabled}} onPress={onPress} style={[s.button,{borderColor:c['color-border-paper'],opacity:disabled?0.5:1}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
 async function authorize(operation:ClaudeMcpOperation){if(openingAuthorization)return;setAuthorizationError(null);setOpeningAuthorization(operation.id);try{await onAuthorize(operation);}catch{setAuthorizationError('授权页面未完成，请重试或取消这次认证。');}finally{setOpeningAuthorization(null);}}
 return <View style={s.gap}>
  <View style={s.row}><InkLabel accessibilityRole="header" style={[text,s.heading]}>Claude MCP 资源</InkLabel>{capability?.enabled?button('添加 MCP 服务',()=>{setConfigurationError(null);setAddDialogOpen(true);}):null}</View>
  {loading?<View style={s.row}><ActivityIndicator color={c['color-text-primary']}/><InkLabel style={secondary}>读取 Claude MCP 状态…</InkLabel></View>:null}
  {capability&&!capability.enabled?<InkLabel accessibilityRole="alert" style={secondary}>{messageForCapability(capability)}</InkLabel>:null}
  {capability?.enabled&&!loading&&servers.length===0?<InkLabel style={secondary}>尚未配置 MCP 服务。添加后列表会立即返回；进入详情页后自动加载远端能力清单。</InkLabel>:null}
  {servers.map(server=>{const operation=operationFor(operations,server),state=operation&&ACTIVE_STATES.includes(operation.state)?operation.state:server.state,busy=busyServer===server.name;return <View key={server.name} style={[s.card,{borderColor:c['color-border-paper'],backgroundColor:c['color-bg-surface-solid']}]}>
   {button(`管理与工具 ${server.name}`,()=>onOpenServerDetail(server.name))}<InkLabel style={secondary}>{`${serverStatusLabel(server,state)} · ${SCOPE_LABELS[server.config_scope||'unknown']}`}</InkLabel>
   {server.detail?<InkLabel selectable style={secondary}>{server.detail}</InkLabel>:null}
   <View style={s.row}>
    {canLogout(server,state)?button('退出认证',()=>void logout(server.name),busy):null}
    {canStartClaudeMcpAuth(server,state)&&!ACTIVE_STATES.includes(state)?button(claudeMcpAuthActionLabel(server),()=>void start(server,state),busy):null}
    {canDetectConnection(server,state)&&!ACTIVE_STATES.includes(state)?button('刷新数据库状态',()=>void load(),loading||busy):null}
    {operation&&ACTIVE_STATES.includes(operation.state)?button('取消',()=>void cancel(operation),busy):null}
    {server.removable&&!ACTIVE_STATES.includes(state)?button('移除',()=>void remove(server.name),busy):null}
   </View>
   {!server.removable&&server.config_scope&&server.config_scope!=='unknown'?<InkLabel style={secondary}>{`请从${SCOPE_LABELS[server.config_scope]}来源管理`}</InkLabel>:null}
   {operation?.state==='waiting_for_user'?<View style={s.gap}>{button(openingAuthorization===operation.id?'正在打开授权页面…':'打开授权页面',()=>void authorize(operation),!operation.authorization_url||openingAuthorization!==null)}</View>:null}
   {operation&&safeOperationError(operation)?<InkLabel accessibilityRole="alert" style={{color:c['color-state-error']}}>{safeOperationError(operation)??''}</InkLabel>:null}
  </View>;})}
  {error||authorizationError?<InkLabel accessibilityRole="alert" style={{color:c['color-state-error']}}>{error||authorizationError||''}</InkLabel>:null}
  {addDialogOpen&&capability?.enabled===true?<Modal visible animationType="slide" presentationStyle="pageSheet" onRequestClose={()=>setAddDialogOpen(false)}>
   <SafeAreaView style={[s.fill,{backgroundColor:c['color-bg-app']}]}><KeyboardAvoidingView style={s.fill} behavior={Platform.OS==='ios'?'padding':undefined}>
    <View style={s.header}><InkLabel accessibilityRole="header" style={[text,s.heading]}>添加 MCP 服务</InkLabel>{button('关闭添加 MCP 服务弹窗',()=>setAddDialogOpen(false))}</View>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.content}>
     <InkLabel style={secondary}>配置连接信息后，Dream 会自动判断服务是否需要认证并读取可用能力。</InkLabel>
     <InkLabel style={text}>MCP 服务名称</InkLabel><TextInput accessibilityLabel="MCP 服务名称" autoFocus maxLength={128} autoCapitalize="none" autoCorrect={false} value={serverName} onChangeText={setServerName} style={[s.input,text,{borderColor:c['color-border-paper']}]}/>
     <InkLabel style={text}>传输方式</InkLabel><View accessibilityRole="radiogroup" accessibilityLabel="MCP 传输方式" style={s.row}>{(['streamable_http','sse','stdio'] as const).map(value=><Pressable key={value} accessibilityRole="radio" accessibilityLabel={value==='streamable_http'?'Streamable HTTP':value==='sse'?'Legacy SSE':'stdio profile'} accessibilityState={{checked:serverTransport===value}} aria-checked={serverTransport===value} onPress={()=>{setServerTransport(value);setConfigurationError(null);}} style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:serverTransport===value?c['color-bg-hover']:'transparent'}]}><InkLabel style={text}>{value==='streamable_http'?'Streamable HTTP':value==='sse'?'Legacy SSE':'stdio profile'}</InkLabel></Pressable>)}</View>
     <InkLabel style={text}>{serverTransport==='stdio'?'Stdio profile key':'MCP 服务 URL'}</InkLabel><TextInput accessibilityLabel={serverTransport==='stdio'?'Stdio profile key':'MCP 服务 URL'} autoCapitalize="none" autoCorrect={false} keyboardType={serverTransport==='stdio'?'default':'url'} value={serverTransport==='stdio'?stdioProfileKey:serverUrl} onChangeText={serverTransport==='stdio'?setStdioProfileKey:setServerUrl} style={[s.input,text,{borderColor:c['color-border-paper']}]}/>
     <InkLabel style={secondary}>{serverTransport==='stdio'?'使用服务端预置的 stdio profile key；客户端不接收 command、args、env 或 header。':'填写服务端提供的绝对 HTTP(S) 地址。认证方式由 Dream 自动识别。'}</InkLabel>
    </ScrollView>
    <View style={[s.footer,{borderTopColor:c['color-border-paper']}]}>{configurationError?<InkLabel accessibilityRole="alert" style={{color:c['color-state-error']}}>{configurationError}</InkLabel>:null}<View style={s.row}>{button('取消',()=>setAddDialogOpen(false))}{button(configuring?'正在添加…':'添加 MCP 服务',()=>void configure(),configuring)}</View></View>
   </KeyboardAvoidingView></SafeAreaView>
  </Modal>:null}
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},gap:{gap:12},row:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',gap:8},heading:{fontSize:20},button:{minHeight:44,padding:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:10,justifyContent:'center'},card:{padding:16,gap:12,borderWidth:1,borderRadius:16},header:{padding:16,gap:12},content:{padding:20,gap:16},input:{minHeight:44,borderWidth:1,borderRadius:10,padding:12},footer:{padding:16,gap:12,borderTopWidth:StyleSheet.hairlineWidth}});
