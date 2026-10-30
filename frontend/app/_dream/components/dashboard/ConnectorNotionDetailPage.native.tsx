// [Input] Original Notion state/API, authenticated owner and concrete native visibility/link actions.
// [Output] Native seven-section overview, resource selection, sources and read-only Skill/file pages.
// [Pos] Settings Resources presentation; original hook/server own authorization, synchronization and revisions.
// [Sync] 2026-10-29: reuse the existing business state and Markdown renderer; retain child scroll positions and selection drafts.
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,BackHandler,Linking,Platform,Pressable,ScrollView,StyleSheet,Switch,TextInput,View} from 'react-native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import type {ResourceConnectorApi} from '../../api/resourceConnectorApi';
import useNotionConnector from '../../hooks/useNotionConnector';
import type {ConnectorStatusObservation} from '../../hooks/useConnectorStatusRefresh';
import ChatMarkdown from '../chat/ChatMarkdown.native';
import {RESOURCE_PAGE_SIZE,NOTION_WEBSITE,NOTION_PRIVACY,NOTION_TERMS,availabilityLabel,operationSourceLabel,formatDateTime,formatConnectionDate,formatFileSize,formatSyncInterval,formatStatusLabel,shouldShowPageCount,sourceKindLabel,type DetailView} from './notionConnectorPresentation';

interface Props {
  ownerId:string;active:boolean;api:ResourceConnectorApi;observation:ConnectorStatusObservation;
  onBack:()=>void;origin?:string;openLink?:(url:string)=>Promise<unknown>;
}
export default function ConnectorNotionDetailPage({ownerId,active,api,observation,onBack,origin,openLink=Linking.openURL}:Props){
  const c=useInkColors(),state=useNotionConnector({ownerId,authenticated:true,active,api,observation});
  const {view,setView,connector,catalog,catalogLoading,pageError,catalogError,policyError,connecting,disconnecting,syncLoading,policySaving,
    policyEnabled,setPolicyEnabled,policyIntervalMinutes,setPolicyIntervalMinutes,resourceLoading,resourceSaving,resourceError,
    selectedDatabaseIds,setSelectedDatabaseIds,selectedPageIds,setSelectedPageIds,resourceSearchQuery,setResourceSearchQuery,resourcePage,setResourcePage,
    skillDetail,skillLoading,skillError,selectedSkillFile,skillFileContent,skillFileLoading,skillFileError,connectorId,connectorAuthStatus,
    cliInstallation,cliMissing,canEditResources,resourceCoolingDown,syncPolicy,detailStatus,sourceStats,readOperations,writeOperations,
    unifiedResourceOptions,filteredResourceOptions,totalResourcePages,visibleResourceOptions,selectedResourceCount,
    handleStartAuth,handleDisconnect,handleSaveSyncPolicy,handleOpenSkill,handleOpenSkillFile,handleOpenResources,handleSaveResources,
    handleSyncSources,authActionLabel,reloadCatalog}=state;
  const [moreOpen,setMoreOpen]=useState(false),[linkError,setLinkError]=useState(false),[sourceLimit,setSourceLimit]=useState(RESOURCE_PAGE_SIZE);
  const scrolls=useRef<Partial<Record<DetailView,ScrollView|null>>>({}),offsets=useRef<Partial<Record<DetailView,number>>>({});
  const text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']};
  const back=()=>{if(view==='file')setView('skill');else if(view!=='overview')setView('overview');else onBack();};
  useEffect(()=>{if(!active)setMoreOpen(false);},[active]);
  useEffect(()=>{if(!active||Platform.OS!=='android')return;const listener=BackHandler.addEventListener('hardwareBackPress',()=>{back();return true;});return()=>listener.remove();},[active,view,onBack]);
  function link(url:string){setLinkError(false);void openLink(url).catch(()=>setLinkError(true));}
  const copy=(value:string|null|undefined,error=false)=>value?<InkLabel selectable accessibilityRole={error?'alert':undefined} style={error?{color:c['color-state-error']}:text}>{value}</InkLabel>:null;
  const button=(label:string,onPress:()=>void,disabled=false)=> <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled}} disabled={disabled} onPress={onPress} style={[s.button,{borderColor:c['color-border-paper'],opacity:disabled?0.5:1}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
  const section=(title:string,body:ReactNode)=><View style={[s.section,{borderTopColor:c['color-border-paper']}]}><InkLabel accessibilityRole="header" style={[text,s.sectionTitle]}>{title}</InkLabel>{body}</View>;
  const scene=(name:DetailView,body:ReactNode)=><ScrollView key={name} ref={ref=>{scrolls.current[name]=ref;}} style={[s.fill,view!==name?s.hidden:undefined]}
    accessibilityElementsHidden={!active||view!==name} importantForAccessibility={active&&view===name?'auto':'no-hide-descendants'} keyboardShouldPersistTaps="handled"
    onScroll={event=>{if(active&&view===name)offsets.current[name]=event.nativeEvent.contentOffset.y;}} scrollEventThrottle={32}
    onLayout={()=>{if(active&&view===name)scrolls.current[name]?.scrollTo({y:offsets.current[name]??0,animated:false});}} contentContainerStyle={s.content}>{body}</ScrollView>;
  const policyStatus=syncPolicy?.workerErrorCode?'自动同步暂不可用；最近成功索引仍保留。'
    :syncPolicy?.status==='error'?'上次同步失败；最近成功索引仍保留。':syncPolicy?.status==='syncing'?'正在后台同步。'
    :!syncPolicy?'连接后可设置自动同步。':!syncPolicy.effective.enabled?'自动同步已关闭。':sourceStats.total===0?'选择资源后开始自动同步。'
    :syncPolicy.scheduleDue===undefined?'同步状态暂不可用，请稍后刷新。':syncPolicy.scheduleDue?`已到同步时间，等待后台同步。最近成功 ${formatDateTime(syncPolicy.lastSuccessAt)}`:`下次计划 ${formatDateTime(syncPolicy.nextSyncAt)}`;
  const title=view==='overview'?'Notion CLI':view==='skill'?(skillDetail?.skill.title||'Notion Skill'):view==='file'?(selectedSkillFile?.relativePath||'Skill 文件'):view==='resources'?'资源范围':'已挂载来源';
  const markdown=(body:string)=><ChatMarkdown text={body} origin={origin} onOpenLink={link}/>;
  return <View style={[s.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={s.header}>{button(view==='overview'?'← 资源':view==='file'?'← Skill':'← Notion',back)}<InkLabel accessibilityRole="header" style={[text,s.title]}>{title}</InkLabel></View>
    {linkError?<View style={s.notice}>{copy('链接暂时无法打开，请重试。',true)}</View>:null}
    {scene('overview',<>
      <View style={s.row}>{copy(detailStatus.label)}{button(connecting?'连接中':cliMissing?'先安装 ntn':authActionLabel,()=>void handleStartAuth(),catalogLoading||cliMissing||connecting||connectorAuthStatus==='authenticating')}
        {button('更多 Notion 操作',()=>setMoreOpen(value=>!value))}</View>
      {moreOpen?<View>{button(disconnecting?'关闭中':'关闭连接',()=>void handleDisconnect(),!connectorId||disconnecting)}</View>:null}
      {connector?.auth.status==='authenticating'?<View style={s.gap}>{copy('验证码')}{copy(connector.auth.verificationCode||'等待生成')}{copy(connector.auth.message||'在 Notion 中完成确认后，本页会自动刷新。')}{connector.auth.verificationUrl?button('打开验证页',()=>link(connector.auth.verificationUrl!)):null}</View>:null}
      {cliMissing&&cliInstallation?<View style={s.gap}>{copy('连接前需要安装 Notion CLI')}{copy(`在 Dream 服务所在机器运行 ${cliInstallation.installCommand}，安装完成后重新读取。`)}{button('重新读取',()=>void reloadCatalog())}</View>:null}
      {copy(pageError,true)}
      {section('权限',<>
        <View style={s.row}><InkLabel style={text}>自动同步</InkLabel><Switch accessibilityLabel="自动同步" value={policyEnabled} disabled={!syncPolicy||policySaving} onValueChange={setPolicyEnabled}/></View>
        <InkLabel style={secondary}>{syncPolicy?`当前生效：${syncPolicy.effective.enabled?formatSyncInterval(syncPolicy.effective.intervalMinutes):'已关闭'}`:'连接后可设置'}</InkLabel>
        <View accessibilityRole="radiogroup" accessibilityLabel="Notion 自动同步频率" style={s.row}>{syncPolicy?.allowedIntervalMinutes.map(minutes=><Pressable key={minutes} accessibilityRole="radio" accessibilityLabel={formatSyncInterval(minutes)} accessibilityState={{checked:policyIntervalMinutes===minutes,disabled:!policyEnabled||policySaving}} aria-checked={policyIntervalMinutes===minutes} disabled={!policyEnabled||policySaving} onPress={()=>setPolicyIntervalMinutes(minutes)} style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:policyIntervalMinutes===minutes?c['color-bg-hover']:'transparent'}]}><InkLabel style={text}>{formatSyncInterval(minutes)}</InkLabel></Pressable>)}</View>
        {button(policySaving?'保存中':'保存策略',()=>void handleSaveSyncPolicy(),!syncPolicy||policyIntervalMinutes===null||policySaving)}{copy(policyStatus)}{copy(policyError,true)}
      </>)}
      {section('Skills',catalogLoading?<ActivityIndicator color={c['color-text-primary']}/>:catalogError?copy(`${catalogError}；连接和索引不受影响。`,true):catalog?.skills.length?<View style={s.gap}>{catalog.skills.map(skill=><View key={skill.id}>{button(skill.title,()=>void handleOpenSkill(skill.id))}<InkLabel style={secondary}>{`内置 · ${availabilityLabel(skill.availability)}`}</InkLabel></View>)}</View>:copy('当前服务器没有可查看的 Notion Skill。'))}
      {(['read','write'] as const).map(kind=><View key={kind}>{section(kind==='read'?'读取操作':'写入操作',catalogLoading?<ActivityIndicator color={c['color-text-primary']}/>:catalogError?copy('能力说明暂时无法读取；资源管理仍可继续。',true):<View style={s.gap}>{(kind==='read'?readOperations:writeOperations).map(operation=><View key={operation.id} style={s.gap}>{copy(operation.title)}<InkLabel style={secondary}>{operation.description}</InkLabel><InkLabel style={secondary}>{`${operationSourceLabel(operation.source)} · ${availabilityLabel(operation.availability)}`}</InkLabel></View>)}</View>)}</View>)}
      {section('资源范围',button('管理资源范围',handleOpenResources))}
      {section('已挂载来源',button('管理已挂载来源',()=>setView('sources')))}
      {section('信息',<>{copy(`连接时间 ${formatConnectionDate(connector)}`)}<View style={s.row}>{[['网站',NOTION_WEBSITE],['隐私政策',NOTION_PRIVACY],['服务条款',NOTION_TERMS]].map(([label,url])=><View key={label}>{button(label,()=>link(url))}</View>)}</View></>)}
    </>)}
    {scene('skill',skillLoading?<ActivityIndicator color={c['color-text-primary']}/>:skillError?copy(skillError,true):skillDetail?<>
      {copy(skillDetail.skill.description)}<InkLabel style={secondary}>{`内置 · ${availabilityLabel(skillDetail.skill.availability)}`}</InkLabel>
      {section('Skill 说明',markdown(skillDetail.skill.body))}{section('包含的文件',skillDetail.files.length?<View style={s.gap}>{skillDetail.files.map(file=><View key={file.id}>{button(file.relativePath,()=>void handleOpenSkillFile(file))}<InkLabel style={secondary}>{`${file.mediaType} · ${formatFileSize(file.sizeBytes)}`}</InkLabel></View>)}</View>:copy('当前 Skill 没有可公开查看的相关文件。'))}
    </>:null)}
    {scene('file',skillFileLoading?<ActivityIndicator color={c['color-text-primary']}/>:skillFileError?copy(skillFileError,true):skillFileContent?<>{copy(skillFileContent.file.relativePath)}{markdown(skillFileContent.file.content)}</>:null)}
    {scene('resources',!canEditResources?copy('连接后才能管理资源。当前服务器范围保持不变。返回 Notion 详情完成连接后再试。'):<>
      <TextInput accessibilityLabel="搜索 Notion 资源" placeholder="搜索资源" placeholderTextColor={c['color-text-secondary']} value={resourceSearchQuery} onChangeText={setResourceSearchQuery} editable={!resourceLoading} style={[s.input,text,{borderColor:c['color-border-paper']}]}/>
      {copy(`已选择 ${selectedResourceCount} 个${selectedResourceCount!==sourceStats.total?' · 有未保存更改':''}`)}{copy(resourceError,true)}
      {resourceLoading?<ActivityIndicator color={c['color-text-primary']}/>:unifiedResourceOptions.length===0?copy('没有可访问的资源。当前 Notion 授权没有返回可选择的数据库或页面。'):visibleResourceOptions.length===0?copy('没有匹配的资源。调整搜索关键词后再试。'):<View style={s.gap}>{visibleResourceOptions.map(option=>{
        const database=option.kind==='database',checked=(database?selectedDatabaseIds:selectedPageIds).includes(option.id),toggle=()=>{const update=database?setSelectedDatabaseIds:setSelectedPageIds;update(current=>current.includes(option.id)?current.filter(id=>id!==option.id):[...current,option.id]);};
        return <Pressable key={`${option.kind}-${option.id}`} accessibilityRole="checkbox" accessibilityLabel={option.title} accessibilityState={{checked}} aria-checked={checked} onPress={toggle} style={[s.resource,{borderColor:c['color-border-paper']}]}><View style={s.grow}>{copy(option.title)}<InkLabel style={secondary}>{`${database?'数据库':'页面'}${option.subtitle?` · ${option.subtitle}`:''}`}</InkLabel></View><InkLabel style={text}>{checked?'✓':'○'}</InkLabel></Pressable>;
      })}</View>}
      <View style={s.row}>{copy(`共 ${filteredResourceOptions.length} 个 · 第 ${resourcePage} / ${totalResourcePages} 页`)}{button('上一页',()=>setResourcePage(current=>Math.max(1,current-1)),resourcePage<=1)}{button('下一页',()=>setResourcePage(current=>Math.min(totalResourcePages,current+1)),resourcePage>=totalResourcePages)}</View>
      {copy(`服务器当前范围 ${sourceStats.total} 个`)}{button(resourceSaving?'保存并同步中':'保存并首次同步',()=>void handleSaveResources(),resourceSaving||resourceLoading||syncLoading||resourceCoolingDown)}
    </>)}
    {scene('sources',<>
      {copy(`${sourceStats.total} 个来源`)}{copy(`最近成功 ${formatDateTime(connector?.lastSyncedAt)}`)}
      {button(syncLoading?'同步中':syncPolicy?.status==='error'?'立即重试':'立即同步',()=>void handleSyncSources(),!canEditResources||syncLoading||resourceSaving||resourceCoolingDown||sourceStats.total===0)}{copy(resourceError,true)}
      {sourceStats.total===0?copy('还没有挂载来源。前往“资源范围”选择数据库或页面并保存。'):(connector?.sources??[]).slice(0,sourceLimit).map(source=><View key={source.id} style={[s.resource,{borderColor:c['color-border-paper']}]}><View style={s.grow}>{copy(source.title)}<InkLabel style={secondary}>{`${formatStatusLabel(source.status)} · ${sourceKindLabel(source.type)}`}</InkLabel>{copy(source.description)}<InkLabel style={secondary}>{`${formatDateTime(source.syncedAt||source.updatedAt)}${shouldShowPageCount(source.pageCount)?` · ${source.pageCount} 页`:''}`}</InkLabel></View></View>)}
      {sourceLimit<sourceStats.total?button('加载更多',()=>setSourceLimit(value=>value+RESOURCE_PAGE_SIZE)):null}
    </>)}
  </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},hidden:{display:'none'},header:{flexDirection:'row',alignItems:'center',gap:12,padding:12},title:{fontSize:22,flexShrink:1},content:{padding:20,gap:16,paddingBottom:32},row:{flexDirection:'row',alignItems:'center',flexWrap:'wrap',gap:10},gap:{gap:8},grow:{flex:1,minWidth:0},button:{minHeight:44,padding:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:10,justifyContent:'center',alignSelf:'flex-start'},section:{gap:12,paddingTop:20,borderTopWidth:StyleSheet.hairlineWidth},sectionTitle:{fontSize:18},input:{minHeight:44,borderWidth:1,borderRadius:10,padding:12},resource:{minHeight:52,flexDirection:'row',alignItems:'center',gap:12,paddingVertical:12,borderBottomWidth:StyleSheet.hairlineWidth},notice:{paddingHorizontal:20,paddingBottom:12}});
