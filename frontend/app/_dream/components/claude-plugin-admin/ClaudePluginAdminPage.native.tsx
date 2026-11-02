// [Input] Original Work plugin state/API, server permissions and caller-supplied native HTTP.
// [Output] Native Claude Code Plugins, create actions, Marketplace confirmation/result, operations and uninstall.
// [Pos] Native Work/Plugins content; Dream workflow administration remains outside the mobile scope.
// [Sync] 2026-10-29: reuse the Web state and original operation/permission contracts; no CLI, policy or backend lifecycle ownership.
import {useEffect,useState,type ReactNode} from 'react';
import {Modal,Pressable,SafeAreaView,ScrollView,StyleSheet,TextInput,View} from 'react-native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport';
import useClaudePluginAdmin from '../../hooks/useClaudePluginAdmin';
import {shortDigest,type ClaudePluginInstallation,type ClaudePluginOperation} from '../../api/claudePluginAdminApi';
import {MARKETPLACE_STEPS,componentSummary} from './claudePluginPresentation';

function labelText(value:ReactNode):string {
  if(Array.isArray(value))return value.map(labelText).join('');
  return typeof value==='string'||typeof value==='number'?String(value):'';
}
function Button({children,onPress,disabled=false,label,primary=false}:{children:ReactNode;onPress:()=>void;disabled?:boolean;label?:string;primary?:boolean}) {
  const c=useInkColors();
  return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled}} disabled={disabled} onPress={onPress}
    style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:primary?c['color-text-primary']:c['color-bg-surface'],opacity:disabled?0.45:1}]}>
    <InkLabel style={{color:primary?c['color-text-on-action']:c['color-text-primary']}}>{labelText(children)}</InkLabel>
  </Pressable>;
}
function Copy({children,error=false,heading=false}:{children:ReactNode;error?:boolean;heading?:boolean}) {
  const c=useInkColors();return <InkLabel accessibilityRole={error?'alert':heading?'header':undefined} selectable style={{color:error?c['color-state-error']:c['color-text-primary'],fontSize:heading?20:14}}>{labelText(children)}</InkLabel>;
}
function Card({children}:{children:ReactNode}) {
  const c=useInkColors();return <View style={[s.card,{borderColor:c['color-border-paper'],backgroundColor:c['color-bg-surface']}]}>{children}</View>;
}
function OperationCard({operation}:{operation:ClaudePluginOperation}) {
  return <Card><Copy>{operation.id}</Copy><Copy>{operation.status} · {operation.requested_package_spec}</Copy>
    <Copy>{operation.message??operation.phase}{typeof operation.exit_code==='number'?` · exit ${operation.exit_code}`:''}{operation.cli_version?` · ${operation.cli_version}`:''}</Copy>
    <View accessibilityRole="progressbar" accessibilityLabel={`安装进度 ${operation.progress}%`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={operation.progress}><Copy>{operation.progress}%</Copy></View>
    {operation.error_summary?<Copy error>{operation.error_code}: {operation.error_summary}</Copy>:null}
  </Card>;
}
function InstallationRow({installation,busy,canManage,onUninstall}:{installation:ClaudePluginInstallation;busy:boolean;canManage:boolean;onUninstall:(id:string)=>void}) {
  const [expanded,setExpanded]=useState(false);
  let inventory:Record<string,unknown>={};try{inventory=JSON.parse(installation.component_inventory_json||'{}');}catch{/* Original invalid inventory presentation is empty. */}
  const skills=Array.isArray(inventory.skills)?inventory.skills as string[]:[];
  return <Card><Copy heading>{installation.package_name}</Copy><Copy>v{installation.resolved_version} · {installation.status}</Copy>
    <Copy>{installation.requested_package_spec} · {shortDigest(installation.artifact_digest)} · {installation.file_count} files</Copy>
    <View style={s.row}><Button onPress={()=>setExpanded(value=>!value)}>{expanded?'收起':'详情'}</Button>
      {canManage&&installation.status==='ready'?<Button disabled={busy} onPress={()=>onUninstall(installation.id)}>卸载</Button>:null}</View>
    {expanded?<View style={s.gap}><Copy>source: {installation.source_type} · CLI {installation.claude_cli_version}</Copy>
      {installation.cli_git_commit_sha?<Copy>commit: {installation.cli_git_commit_sha}</Copy>:null}
      <Copy>digest: {installation.artifact_digest}</Copy><Copy>artifact: {installation.artifact_path}</Copy>
      {skills.length?<Copy>skills ({skills.length}): {skills.join(', ')}</Copy>:null}
      <Copy>decks: {installation.deck_ref_count??0} 个引用</Copy><Copy>installed: {installation.installed_at??'—'}</Copy>
    </View>:null}
  </Card>;
}

export default function ClaudePluginAdminPage({transport,onSessionExpired,active=true}:{transport?:typeof fetch;onSessionExpired?:()=>void;active?:boolean}={}) {
  const p=useClaudePluginAdmin({transport:transport??clientFetch,onSessionExpired}),c=useInkColors();
  const [menuOpen,setMenuOpen]=useState(false);
  useEffect(()=>{if(!active){setMenuOpen(false);p.setActiveDialog(null);}},[active]);
  const close=()=>p.setActiveDialog(null),open=(kind:Exclude<typeof p.activeDialog,null>)=>{setMenuOpen(false);p.openDialog(kind);};
  const selected=p.selectedMarketplaceEntry;
  return <View style={s.fill}>
    <ScrollView contentContainerStyle={s.page} keyboardShouldPersistTaps="handled">
      <View style={s.row}><Copy heading>Claude Code Plugins</Copy>
        <Button label="刷新 Claude 插件" disabled={p.loading||p.refreshing} onPress={()=>void p.refresh()}>{p.refreshing?'正在刷新…':'刷新'}</Button>
        <Button label="创建 Claude 插件" onPress={()=>setMenuOpen(value=>!value)}>创建</Button>
      </View>
      {menuOpen?<Card><Button disabled={!p.canManage||p.loading} onPress={()=>open('install')}>安装</Button>
        <Button onPress={()=>open('marketplace')}>从 Marketplace 添加</Button><Button onPress={()=>open('operations')}>最近操作（{p.operations.length}）</Button></Card>:null}
      <Copy>为 Deck 扩展 Skill、工具和 Agent 能力。在 Deck 创建或维护时选择要使用的插件。下方展示共享安装清单，安装与卸载需要管理权限。</Copy>
      {p.error?<Card><Copy error>{p.error}</Copy><Button onPress={()=>void p.refresh()}>重试</Button></Card>:null}
      {p.successMessage?<View accessibilityLiveRegion="polite"><Copy>{p.successMessage}</Copy></View>:null}
      {!p.loading&&!p.error&&!p.canManage?<Copy>当前账户没有共享插件管理权限；已安装列表保持只读。</Copy>:null}
      <Copy>已安装（{p.installations.length}）</Copy>
      {p.loading?<Copy>正在加载 Claude 插件…</Copy>:p.installations.length===0?<Card><Copy heading>尚未安装任何插件</Copy><Copy>使用“创建 → 安装”输入 package spec 开始。</Copy></Card>:
        p.installations.map(installation=><InstallationRow key={installation.id} installation={installation} busy={p.busy} canManage={p.canManage} onUninstall={id=>void p.handleUninstall(id)}/>)}
    </ScrollView>
    <Modal visible={active&&p.activeDialog!==null} animationType="slide" presentationStyle="pageSheet" onRequestClose={close}>
      <SafeAreaView style={[s.fill,{backgroundColor:c['color-bg-app']}]}>
        <View style={[s.row,s.header]}><Copy heading>{p.activeDialog==='install'?'安装 Claude 插件':p.activeDialog==='marketplace'?'从 Marketplace 添加':'最近操作'}</Copy><Button label="关闭" onPress={close}>关闭</Button></View>
        <ScrollView contentContainerStyle={s.page} keyboardShouldPersistTaps="handled" automaticallyAdjustKeyboardInsets>
          {p.activeDialog==='install'?<>
            <Copy>输入 Claude Code package spec。请求会提交到现有服务端受管安装入口。</Copy><Copy>Package spec</Copy>
            <TextInput accessibilityLabel="Package spec" value={p.spec} onChangeText={p.setSpec} editable={!p.busy} autoCapitalize="none" autoCorrect={false} spellCheck={false}
              placeholder="superpowers@claude-plugins-official" placeholderTextColor={c['color-text-secondary']} style={[s.input,{color:c['color-text-primary'],borderColor:c['color-border-paper']}]} />
            <Copy>格式：&lt;plugin&gt;@&lt;marketplace&gt;[@&lt;version&gt;]</Copy>
            {p.installError?<Copy error>{p.installError}</Copy>:null}
            <View style={s.row}><Button disabled={p.busy} onPress={close}>取消</Button><Button primary disabled={p.busy||!p.spec.trim()||!p.canManage} onPress={()=>void p.handleInstall()}>{p.busy?'安装中…':'开始安装'}</Button></View>
          </>:null}
          {p.activeDialog==='marketplace'?<>
            <Copy>{MARKETPLACE_STEPS.map(step=>`${step.id===p.marketplaceStep?'●':'○'} ${step.label}`).join('  →  ')}</Copy>
            {p.marketplaceStep==='select'?<>
              <Copy>平台全局目录 · 仅展示有效且已批准的远程 revision</Copy>
              {p.marketplaceLoading?<Copy>正在读取 Marketplace…</Copy>:p.marketplaceError?<Card><Copy heading>Marketplace 目录暂不可用</Copy><Copy error>{p.marketplaceError}</Copy><Button onPress={()=>void p.loadMarketplace()}>重新加载</Button></Card>:
                p.marketplaceEntries.length===0?<Card><Copy heading>暂无可添加插件</Copy><Copy>运营者尚未批准任何有效 revision，或已停用全部远程来源。</Copy></Card>:
                  p.marketplaceEntries.map(entry=><Pressable key={entry.id} accessibilityRole="button" accessibilityLabel={entry.display_name} accessibilityState={{selected:p.selectedMarketplaceEntryId===entry.id}} onPress={()=>p.setSelectedMarketplaceEntryId(entry.id)}>
                    <Card><Copy heading>{p.selectedMarketplaceEntryId===entry.id?'● ':''}{entry.display_name}</Copy><Copy>{entry.package_spec} · {entry.installation?'已安装':entry.version?`v${entry.version}`:'可安装'}</Copy>
                      <Copy>{entry.description??'该插件未提供说明。'}</Copy><Copy>{entry.marketplace.display_name} · {componentSummary(entry)}</Copy></Card>
                  </Pressable>)}
              <View style={s.row}><Button onPress={close}>取消</Button><Button primary disabled={!selected||p.marketplaceLoading||!p.canManage} onPress={()=>{p.setMarketplaceError(null);p.setMarketplaceStep('confirm');}}>继续</Button></View>
            </>:null}
            {p.marketplaceStep==='confirm'&&selected?<>
              <Card><Copy heading>{selected.display_name}</Copy><Copy>{selected.package_spec}</Copy><Copy>{selected.description??'该插件未提供说明。'}</Copy>
                <Copy>来源: {selected.marketplace.display_name}</Copy><Copy>版本: {selected.version??'未声明'}</Copy><Copy>组件: {componentSummary(selected)}</Copy>
                <Copy>固定 ref: {selected.revision.requested_ref??'远程默认分支'}</Copy><Copy>批准 commit: {selected.revision.commit_sha}</Copy><Copy>内容摘要: {selected.revision.plugin_digest}</Copy>
                <Copy>重复添加: {selected.installation?'复用并重新验证现有安装':'创建新的共享安装记录'}</Copy>
              </Card>
              <Copy>安装前服务端会再次确认条目仍为 active/approved，并校验 CLI checkout 的 commit 与 manifest 摘要；发生远端漂移时不会继续安装。</Copy>
              {p.marketplaceError?<Copy error>{p.marketplaceError}</Copy>:null}
              <View style={s.row}><Button disabled={p.busy} onPress={()=>p.setMarketplaceStep('select')}>返回选择</Button><Button primary disabled={p.busy||!p.canManage} onPress={()=>void p.handleMarketplaceInstall()}>{p.busy?'提交中…':selected.installation?'验证并复用安装':'确认安装'}</Button></View>
            </>:null}
            {p.marketplaceStep==='installing'?<>
              <Copy heading>正在安装 {selected?.display_name}</Copy><Copy>服务端正在校验已批准 revision、调用真实 Claude CLI，并导入 digest 固定的共享制品。可以关闭窗口，进度会保留在“最近操作”。</Copy>
              {p.activeMarketplaceOperation?<OperationCard operation={p.activeMarketplaceOperation}/>:<Copy>{p.marketplaceOperationId}</Copy>}
              <Button onPress={close}>后台继续</Button>
            </>:null}
            {p.marketplaceStep==='result'&&p.marketplaceResult?<>
              <Copy heading>{p.marketplaceResult.status==='ready'?'插件可以使用':'安装未完成'}</Copy>
              <Copy error={p.marketplaceResult.status==='error'}>{p.marketplaceResult.status==='ready'?`${p.marketplaceResult.requested_package_spec} 已进入共享安装列表，可继续绑定到 Deck。`:`${p.marketplaceResult.error_code??'CLAUDE_PLUGIN_INSTALL_FAILED'}：保留当前选择，可直接重试。`}</Copy>
              <OperationCard operation={p.marketplaceResult}/><View style={s.row}>
                {p.marketplaceResult.status==='error'?<Button onPress={()=>p.setMarketplaceStep('confirm')}>返回并重试</Button>:null}<Button primary onPress={close}>{p.marketplaceResult.status==='ready'?'完成':'关闭'}</Button>
              </View>
            </>:null}
          </>:null}
          {p.activeDialog==='operations'?<>
            <Copy>显示真实 operation ID、阶段、进度、CLI 版本和退出结果。</Copy>
            {p.operations.length===0?<Card><Copy heading>暂无最近操作</Copy><Copy>安装请求提交后会在这里显示进度和结果。</Copy></Card>:p.operations.map(operation=><OperationCard key={operation.id} operation={operation}/>)}
            <Button onPress={close}>关闭</Button>
          </>:null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},page:{padding:20,gap:16,paddingBottom:28},header:{padding:16},gap:{gap:8},row:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',gap:10},card:{padding:16,gap:10,borderWidth:StyleSheet.hairlineWidth,borderRadius:12},button:{minHeight:44,paddingVertical:10,paddingHorizontal:14,borderRadius:7,borderWidth:StyleSheet.hairlineWidth,justifyContent:'center'},input:{fontSize:16,minHeight:48,padding:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:7}});
