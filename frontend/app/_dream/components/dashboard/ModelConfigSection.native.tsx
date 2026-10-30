// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Shared model-settings lifecycle, original model catalog and authenticated native HTTP.
// [Output] Native Settings model, prompt, workspace, approval and tool environment controls.
// [Pos] Platform renderer for existing Settings; configuration remains server-owned.
// [Sync] 2026-10-29: retain original fields, save/reload feedback and independent AI/Image selection.
import {Children,useEffect,type ReactNode} from 'react';
import {BackHandler,Keyboard,Platform,Pressable,ScrollView,StyleSheet,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import useModelConfig,{parseSandboxNetworkDomains,parseSandboxFsWritePaths,type ModelConfigOptions} from '../../hooks/useModelConfig';
import {imageModelAvailabilityMessage,type GatewayModel} from '../../api/gatewayModelsApi';
import {clientFetch} from '../../../../src/platform/transport.native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';

const noBrowserEvent=()=>undefined;
export default function ModelConfigSection({active=true,onBack,onConfigSaved,onSessionExpired,transport=clientFetch}:ModelConfigOptions & {active?:boolean;onBack:()=>void}) {
  const {t}=useTranslation();
  const c=useInkColors();
  const s=useModelConfig({transport,onConfigSaved,onSessionExpired,onWorkspaceModeChanged:noBrowserEvent,onImFullAccessChanged:noBrowserEvent});
  const disabled=s.saving||s.configLoading||!!s.configReadError;
  const modelDisabled=disabled||!!s.modelCatalogError||s.modelSaveUnconfirmed;
  const back=()=>{Keyboard.dismiss();onBack();};
  useEffect(()=>{if(!active||Platform.OS!=='android')return;const sub=BackHandler.addEventListener('hardwareBackPress',()=>{back();return true;});return()=>sub.remove();},[active,onBack]);
  const text={color:c['color-text-primary']};
  const input=[styles.input,{color:c['color-text-primary'],backgroundColor:c['color-bg-paper'],borderColor:c['color-border-paper']}];
  function Button({children,onPress,disabled:locked=false,label,selected}:{children:ReactNode;onPress:()=>void;disabled?:boolean;label?:string;selected?:boolean}) {
    return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled:locked,...(selected===undefined?{}:{selected})}} disabled={locked} onPress={onPress}
      style={[styles.button,{borderColor:selected?c['color-border-focus']:c['color-border-paper'],backgroundColor:selected?c['color-bg-hover']:'transparent',opacity:locked?0.55:1}]}><InkLabel style={text}>{Children.toArray(children).join('')}</InkLabel></Pressable>;
  }
  function Copy({children,title=false,alert=false}:{children:ReactNode;title?:boolean;alert?:boolean}) {
    return <InkLabel accessibilityRole={alert?'alert':title?'header':undefined} style={[title?styles.title:styles.copy,{color:alert?c['color-state-error']:c['color-text-primary']}]}>{Children.toArray(children).join('')}</InkLabel>;
  }
  function Choices({models,kind,selected,onChange}:{models:GatewayModel[];kind:'ai'|'image';selected:string;onChange:(alias:string)=>void}) {
    return <View accessibilityRole="radiogroup" accessibilityLabel={kind==='ai'?'选择 AI 模型':'选择 Image 模型'} style={styles.stack}>
      {models.map(option=>{
        const callable=kind==='ai'?option.callable:option.images?.callable===true;
        const capability=kind==='ai'?option.responsesImage:option.images;
        const availability=kind==='image'?imageModelAvailabilityMessage(option):callable?(s.defaultModelAlias===option.modelAlias?'推荐':null)
          :option.availability==='upgrade_required'?`需要 ${option.requiredPlanCode??'更高'} 套餐`:option.availability==='allowance_exhausted'?'额度已用完':'暂不可用';
        const checked=selected===option.modelAlias,locked=modelDisabled||!callable;
        return <Pressable key={option.modelAlias} accessibilityRole="radio" accessibilityLabel={option.displayName} accessibilityState={{checked,disabled:locked}} aria-checked={checked} disabled={locked} onPress={()=>onChange(option.modelAlias)}
          style={[styles.choice,{opacity:callable?1:0.6,borderColor:checked?c['color-border-focus']:c['color-border-paper'],backgroundColor:checked?c['color-bg-hover']:'transparent'}]}>
          <InkLabel style={text}>{`${checked?'◉':'○'} ${option.displayName}`}</InkLabel>
          {capability?.generation?<Copy>{kind==='ai'?'图片生成':'生成'}</Copy>:null}
          {capability?.edit?<Copy>{kind==='ai'?'图片编辑':'编辑'}</Copy>:null}
          {kind==='ai'&&capability&&(capability.generation||capability.edit)&&!capability.callable?<Copy>图片操作暂不可用</Copy>:null}
          {availability?<Copy>{availability}</Copy>:null}
        </Pressable>;
      })}
    </View>;
  }
  return <View style={styles.fill}>
    <View style={styles.heading}><Button label={t('settings.workspace.backToApp')} onPress={back}>‹ {t('settings.workspace.backToApp')}</Button><Copy title>{t('settings.workspace.navigation.model')}</Copy></View>
    <ScrollView accessibilityLabel={t('settings.workspace.model.title')} style={styles.fill} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" keyboardDismissMode={Platform.OS==='ios'?'interactive':'on-drag'}>
      {s.configSaveError?<View style={styles.stack}><Copy alert>{s.configSaveError}</Copy><Button disabled={s.saving} onPress={()=>s.setModelLoadNonce(v=>v+1)}>重新读取设置</Button></View>:null}
      {s.configLoading?<Copy>Loading config…</Copy>:<>
        <View style={styles.section}>
          <Copy title>AI 模型 / Model</Copy><Copy>选择新对话使用的模型。</Copy>
          {s.configReadError?<><Copy alert>{s.configReadError}</Copy><Button onPress={()=>s.setModelLoadNonce(v=>v+1)}>重新加载设置</Button></>:null}
          {s.modelSaveUnconfirmed&&!s.configReadError?<Button disabled={s.saving} onPress={()=>s.setModelLoadNonce(v=>v+1)}>重新加载设置</Button>:null}
          {s.modelCatalogError?<><Copy alert>{s.modelCatalogError}{s.modelOptions.length?' 当前展示上次成功加载的模型目录。':''}</Copy><Button disabled={s.saving} onPress={()=>s.setModelLoadNonce(v=>v+1)}>重新加载模型</Button></>:null}
          {!s.modelOptions.length&&!s.modelCatalogError?<Copy>平台尚未启用可展示的模型。</Copy>:null}
          {s.selectedModel&&!s.modelOptions.some(m=>m.modelAlias===s.selectedModel)?<Copy alert>已保存的模型 {s.selectedModel} 已停用或不再存在。请选择新的可调用模型。</Copy>:null}
          {s.modelOptions.length&&!s.modelOptions.some(m=>m.callable)?<Copy>当前没有可调用模型。</Copy>:null}
          <Choices models={s.modelOptions} kind="ai" selected={s.selectedModel} onChange={s.handleModelChange}/>
          {s.modelStatus?<Copy>{s.modelStatus}</Copy>:null}
        </View>
        <View style={styles.section}>
          <Copy title>Image 模型</Copy><Copy>仅用于明确要求 image_gen 工具的图片生成和编辑。</Copy>
          {!s.selectedImageModel&&!s.configReadError?<Copy>未选择 Image 模型。请选择后再使用 image_gen。</Copy>:null}
          {s.selectedImageModel&&!s.imageModelOptions.some(m=>m.modelAlias===s.selectedImageModel)&&!s.modelCatalogError?<Copy alert>已保存的 Image 模型 {s.selectedImageModel} 已停用或不再提供图片能力。请选择新的可调用模型。</Copy>:null}
          {!s.imageModelOptions.length&&!s.modelCatalogError?<Copy>平台尚未发布可展示的 Image 模型。</Copy>:null}
          <Choices models={s.imageModelOptions} kind="image" selected={s.selectedImageModel} onChange={s.handleImageModelChange}/>
          {s.imageModelStatus?<Copy>{s.imageModelStatus}</Copy>:null}
        </View>
        <View style={styles.section}>
          <Copy title>系统提示词 / System Prompt</Copy>
          <TextInput accessibilityLabel="系统提示词" multiline textAlignVertical="top" style={[input,styles.multiline]} editable={!disabled} value={s.systemPrompt} onChangeText={value=>{s.setSystemPrompt(value);s.setDirty(true);}}/>
          <View style={styles.row}><Button disabled={disabled} onPress={s.handleResetPrompt}>恢复默认</Button><Button label="保存系统提示词" disabled={disabled||!s.dirty} onPress={s.handleSavePrompt}>{s.saving?'保存中…':'保存'}</Button></View>
        </View>
        <View style={styles.section}>
          <Copy title>工作区模式 / Workspace Mode</Copy><Copy>对话时启用文件侧边栏上下文。</Copy>
          <Button label="工作区模式" selected={s.workspaceMode} disabled={disabled} onPress={s.handleWorkspaceToggle}>{s.workspaceMode?'已开启':'已关闭'}</Button>
        </View>
        {s.workspaceMode?<>
          <View style={styles.section}>
            <Copy title>沙箱网络 / Sandbox Network</Copy><Copy>控制沙箱子进程的出站网络；WebFetch 沿用工具权限和域名规则。</Copy>
            <Copy>代理网络访问</Copy><View style={styles.row}>{[{enabled:false,label:'关闭'},{enabled:true,label:'启用'}].map(item=><Button key={item.label} selected={(s.sandboxNetworkMode!=='disabled')===item.enabled} disabled={disabled} onPress={()=>s.handleSandboxNetworkAccessToggle(item.enabled)}>{item.label}</Button>)}</View>
            {s.sandboxNetworkMode==='disabled'?<Copy>设置完成后将禁用网络访问。</Copy>:<>
              <Copy>域允许列表</Copy><View style={styles.row}>{[{mode:'allowlist',label:'自定义域'},{mode:'open',label:'所有域'}].map(item=><Button key={item.mode} selected={s.sandboxNetworkMode===item.mode} disabled={disabled} onPress={()=>s.handleSandboxNetworkPolicySelect(item.mode)}>{item.label}</Button>)}</View>
              {s.sandboxNetworkMode==='allowlist'?<>
                <Copy>其他允许的域</Copy>{parseSandboxNetworkDomains(s.sandboxNetworkDomains).map(domain=><View key={domain} style={styles.row}><Copy>{domain}</Copy><Button label={`Remove ${domain}`} disabled={disabled||s.sandboxNetworkSaving} onPress={()=>s.handleRemoveSandboxNetworkDomain(domain)}>×</Button></View>)}
                {s.sandboxNetworkAddingDomain?<><TextInput accessibilityLabel="添加域" placeholder="example.com 或 *.example.com" placeholderTextColor={c['color-text-muted']} autoCapitalize="none" autoCorrect={false} style={input} editable={!disabled} value={s.sandboxNetworkNewDomain} onChangeText={s.setSandboxNetworkNewDomain}/><View style={styles.row}><Button label="保存域" disabled={disabled||s.sandboxNetworkSaving} onPress={s.handleAddSandboxNetworkDomain}>保存</Button><Button disabled={disabled} onPress={()=>{s.setSandboxNetworkAddingDomain(false);s.setSandboxNetworkNewDomain('');}}>取消</Button></View></>:<Button disabled={disabled} onPress={s.handleAddSandboxNetworkDomain}>+ 添加域</Button>}
                <Copy>允许的 HTTP 方法：所有方法</Copy>
              </>:null}
              <Copy title>高风险</Copy><Copy>启用互联网访问会使你的环境暴露于安全风险之中。请仅允许必要的域，并检查 Agent 的输出和工作日志。</Copy>
            </>}
            {s.sandboxNetworkStatus?<Copy>{s.sandboxNetworkStatus}</Copy>:null}
          </View>
          <View style={styles.section}>
            <Copy title>沙箱文件写入 / Sandbox File Writes</Copy><Copy>额外允许沙箱内 Bash 写入的绝对路径。线程临时目录由运行库绑定，工作区配置目录继续执行原写入限制。</Copy>
            {parseSandboxFsWritePaths(s.sandboxFsPaths).map(path=><View key={path} style={styles.row}><Copy>{path}</Copy><Button label={`Remove ${path}`} disabled={disabled||s.sandboxFsSaving} onPress={()=>s.handleRemoveSandboxFsPath(path)}>×</Button></View>)}
            {s.sandboxFsAddingPath?<><TextInput accessibilityLabel="添加可写路径" placeholder="/absolute/path" placeholderTextColor={c['color-text-muted']} autoCapitalize="none" autoCorrect={false} style={input} editable={!disabled} value={s.sandboxFsNewPath} onChangeText={s.setSandboxFsNewPath}/><View style={styles.row}><Button label="保存可写路径" disabled={disabled||s.sandboxFsSaving} onPress={s.handleAddSandboxFsPath}>保存</Button><Button disabled={disabled} onPress={()=>{s.setSandboxFsAddingPath(false);s.setSandboxFsNewPath('');}}>取消</Button></View></>:<Button disabled={disabled} onPress={s.handleAddSandboxFsPath}>+ 添加可写路径</Button>}
            {s.sandboxFsStatus?<Copy>{s.sandboxFsStatus}</Copy>:null}
          </View>
        </>:null}
        <View style={styles.section}>
          <Copy title>应如何批准 IM</Copy><Copy>开启后普通工具自动批准，问答表单仍需用户确认。</Copy>
          <Button label={s.imFullAccessEnabled?'完全访问已开启':'完全访问已关闭'} selected={s.imFullAccessEnabled} disabled={disabled} onPress={s.handleImFullAccessToggle}>完全访问</Button>
        </View>
        {s.workspaceMode?<View style={styles.section}>
          <Copy title>环境变量 / Environment Variables</Copy><Copy>为 Skills / MCP 工具配置运行时环境变量。</Copy>
          {s.envVars.map((item,index)=><View key={index} style={styles.stack}>
            <TextInput accessibilityLabel={`环境变量名称 ${index+1}`} autoCapitalize="none" autoCorrect={false} style={input} editable={!disabled} placeholder="KEY" placeholderTextColor={c['color-text-muted']} value={item.key} onChangeText={value=>s.handleUpdateEnvVar(index,'key',value)}/>
            <TextInput accessibilityLabel={`环境变量值 ${index+1}`} autoCapitalize="none" autoCorrect={false} secureTextEntry style={input} editable={!disabled} placeholder="value" placeholderTextColor={c['color-text-muted']} value={item.value} onChangeText={value=>s.handleUpdateEnvVar(index,'value',value)}/>
            <Button label={`删除环境变量 ${index+1}`} disabled={disabled} onPress={()=>s.handleRemoveEnvVar(index)}>×</Button>
          </View>)}
          <View style={styles.row}><Button disabled={disabled} onPress={s.handleAddEnvVar}>+ 添加</Button><Button label="保存环境变量" disabled={disabled||!s.envVarsDirty||s.envVarsSaving} onPress={()=>void s.handleSaveEnvVars()}>{s.envVarsSaving?'保存中…':'保存'}</Button></View>
        </View>:null}
      </>}
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},heading:{padding:12,gap:8},content:{padding:16,gap:24,paddingBottom:24},section:{gap:10},stack:{gap:8},row:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',gap:8},title:{fontSize:18,lineHeight:25},copy:{fontSize:15,lineHeight:22,flexShrink:1},button:{minHeight:44,paddingVertical:10,paddingHorizontal:14,borderWidth:1,borderRadius:12,justifyContent:'center'},choice:{minHeight:48,padding:12,borderWidth:1,borderRadius:10,gap:4},input:{minHeight:44,padding:12,fontSize:16,fontFamily:'Excalifont',borderWidth:1,borderRadius:12},multiline:{minHeight:132,maxHeight:240}});
