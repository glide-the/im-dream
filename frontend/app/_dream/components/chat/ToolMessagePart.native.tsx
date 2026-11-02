// [Input] Original tool DTO, execution/confirmation state and local DOM leaf callbacks.
// [Output] Native terminal/Write/image/task cards and persistent original MCP App/editor interfaces.
// [Pos] Native presentation only; original helpers, permission rules and server results define behavior.
import {useState} from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {useCopy} from '../../hooks/useCopy';
import {resolvePendingToolConfirmation,resolveToolName} from './toolConfirmation';
import {getToolStatus,getToolOutputText,readToolInput,parseTerminalOutput,isBuiltInWriteTool,resolveWriteInput,imageFailureMessage,WRITE_PREVIEW_COLLAPSE_CHAR_LIMIT,WRITE_PREVIEW_COLLAPSE_LINE_LIMIT} from './toolPartPresentation';
import {imageToolAction,resolveToolInputSummary,summarizeToolInvocation} from './toolInputSummary';
import {isEditorWriteTool} from './editorWriteTools';
import {parseSavedMcpAppToolCall} from './mcp-apps/result';
import ToolResultSurface,{type ToolResultSurfaceProps} from './ToolResultSurface.native';
import {IconCheck,IconCopy,IconChevronRight} from './Icons';
export interface NativeToolMessagePartProps extends Omit<ToolResultSurfaceProps,'presentation'> {isLast?:boolean;isLoading:boolean;toolChoice?:string;runtimePendingToolCallIds?:ReadonlySet<string>;presentation?:'tool-only'|'app-only'}
export default function ToolMessagePart(props:NativeToolMessagePartProps){
  const {t}=useTranslation(),colors=useInkColors(),{copy,copied}=useCopy(),[expanded,setExpanded]=useState(false);
  const {part}=props,tool=resolveToolName(part),input=readToolInput(part),status=getToolStatus(part,props.isLoading),output=getToolOutputText(part);
  const metadata=part as typeof part&{mcpAppResult?:unknown;toolMetadata?:{mcpAppResult?:unknown}};
  const app=parseSavedMcpAppToolCall({toolName:tool,toolCallId:part.toolCallId,input,output:'output' in part?part.output:undefined,mcpAppResult:metadata.mcpAppResult??metadata.toolMetadata?.mcpAppResult});
  if(props.presentation==='app-only')return app?<ToolResultSurface {...props} presentation="app-only"/>:null;
  if(isEditorWriteTool(tool))return <ToolResultSurface {...props} presentation="editor" editorCompleted={status!=='executing'}/>;
  const pending=resolvePendingToolConfirmation(part,props.toolChoice,props.settledToolCallIds,props.runtimePendingToolCallIds);
  const summary=summarizeToolInvocation(tool,input),title=('title' in part?part.title:undefined)||tool;
  const foreground=colors['color-text-primary'],muted=colors['color-text-muted'],code=colors['color-code-text'];
  const terminalStyle=[styles.terminal,{backgroundColor:colors['color-code-bg']}];
  const copyButton=(value:string)=><Pressable accessibilityRole="button" accessibilityLabel={copied?'Copied!':'Copy'} onPress={()=>copy(value)} style={styles.icon}>{copied?<IconCheck width={16} height={16} color={colors['color-state-success']}/>:<IconCopy width={16} height={16} color={code}/>}</Pressable>;
  const image=imageToolAction(tool,input);
  if(image){
    const completed=part.state==='output-available'||part.state==='output-error',error=part.state==='output-error';
    const value='errorText' in part&&typeof part.errorText==='string'?part.errorText:'error' in part?part.error:'output' in part?part.output:undefined;
    const failure=imageFailureMessage(value);
    return <View style={styles.card}><InkLabel style={{color:foreground}}>{t(`chat.imageTool.${image}`)}</InkLabel><InkLabel style={{color:colors[error?'color-state-error':completed?'color-state-success':'color-action-link']}}>{t(`chat.imageTool.${error?'failed':completed?'completed':props.isLast&&props.isLoading?'running':'incomplete'}`)}</InkLabel>{error&&failure?<InkLabel accessibilityRole="alert" selectable style={{color:colors['color-state-error']}}>{failure}</InkLabel>:null}</View>;
  }
  if(['agent','task'].includes(tool.toLowerCase()))return <View style={[styles.card,{borderLeftWidth:2,borderColor:colors['color-action-link']}]}><InkLabel style={{color:foreground}}>{input&&typeof input==='object'&&'description' in input&&typeof input.description==='string'?input.description:t('chat.subagents.taskFallback')}</InkLabel></View>;
  if(isBuiltInWriteTool(tool)){
    const file=resolveWriteInput(input),content=file.content||(file.partialJson?'Receiving file content…':''),lines=content?content.split('\n').length:0;
    const collapsible=content.length>WRITE_PREVIEW_COLLAPSE_CHAR_LIMIT||lines>WRITE_PREVIEW_COLLAPSE_LINE_LIMIT,isError=status==='error',written=part.state==='output-available';
    const label=isError?'Write failed':written?'Written':part.state==='input-streaming'?'Receiving input':status==='executing'?'Writing':'Ready';
    return <View style={terminalStyle}><View style={styles.header}><InkLabel style={{color:muted}}>‹ Write</InkLabel><InkLabel style={{flex:1,textAlign:'right',color:colors[isError?'color-state-error':written?'color-state-success':'color-action-link']}}>{label}</InkLabel>{copyButton([file.filePath?`$ write ${file.filePath}`:'$ write',content,output||''].filter(Boolean).join('\n\n'))}</View>
      <InkLabel selectable style={[styles.code,{color:code}]}>{`$ write ${file.filePath||'pending-path'}`}</InkLabel><ScrollView style={{maxHeight:collapsible?(expanded?576:WRITE_PREVIEW_COLLAPSE_LINE_LIMIT*21.12):384}} scrollEnabled={!collapsible||expanded}><InkLabel selectable numberOfLines={collapsible&&!expanded?WRITE_PREVIEW_COLLAPSE_LINE_LIMIT:undefined} style={[styles.code,{color:code}]}>{content+(status==='executing'?'▌':'')}</InkLabel></ScrollView>
      {collapsible?<Pressable accessibilityRole="button" accessibilityState={{expanded}} onPress={()=>setExpanded(value=>!value)} style={styles.toggle}><InkLabel style={{color:code}}>{expanded?'Collapse file preview':`Show full file (${lines>1?`${lines} lines`:`${content.length} chars`})`}</InkLabel></Pressable>:null}
      {output?<InkLabel selectable style={[styles.footer,{color:colors[isError?'color-state-error':'color-state-success']}]}>{output}</InkLabel>:null}</View>;
  }
  if(status!=='executing'&&output){const parsed=parseTerminalOutput(output),command=resolveToolInputSummary(input).command||parsed.command;return <View style={terminalStyle}>
    <View style={styles.header}><InkLabel style={{color:muted}}>‹ Terminal</InkLabel><InkLabel numberOfLines={1} style={{flex:1,color:code}}>{summary}</InkLabel>{copyButton(output)}</View>
    {command?<InkLabel selectable style={[styles.code,{color:code}]}>{`$ ${command}`}</InkLabel>:null}<ScrollView style={{maxHeight:320}}><InkLabel selectable style={[styles.code,{color:code}]}>{parsed.output||output}</InkLabel></ScrollView>
    {parsed.exitCode!==null?<InkLabel style={[styles.footer,{color:colors[Number(parsed.exitCode)===0?'color-state-success':'color-state-error']}]}>{`Exit code: ${parsed.exitCode}`}</InkLabel>:status==='error'?<InkLabel style={[styles.footer,{color:colors['color-state-error']}]}>Error</InkLabel>:null}
  </View>;}
  const detail=(label:string,value:unknown)=>value===undefined?null:<View style={styles.detail}><InkLabel style={{color:muted,fontSize:12}}>{label}</InkLabel><InkLabel selectable style={{color:foreground,fontSize:13}}>{typeof value==='string'?value:JSON.stringify(value,null,2)}</InkLabel></View>;
  return <View style={[styles.card,{borderLeftWidth:2,borderColor:colors[pending?'color-state-warning':'color-action-link']}]}>
    <Pressable accessibilityRole="button" accessibilityState={{expanded}} onPress={()=>setExpanded(value=>!value)} style={styles.header}>{status==='executing'?<ActivityIndicator size="small" color={colors['color-action-link']}/>:null}<InkLabel numberOfLines={1} style={{flex:1,color:colors['color-text-secondary'],fontStyle:'italic'}}>{title+(summary?` — ${summary}`:'')}</InkLabel>{pending?<InkLabel style={{color:colors['color-state-warning'],fontSize:12}}>{t(pending==='askuser'?'chat.toolConfirmation.pendingAnswer':'chat.toolConfirmation.pendingConfirm')}</InkLabel>:null}<IconChevronRight width={16} height={16} color={muted} style={{transform:[{rotate:expanded?'90deg':'0deg'}]}}/></Pressable>
    {expanded?<View>{detail('Tool',tool)}{detail('Status',part.state)}{detail('Input',input)}{detail(status==='error'?'Error':'Output','output' in part?part.output:undefined)}</View>:null}
  </View>;
}
const styles=StyleSheet.create({card:{minWidth:0,gap:8,padding:12},header:{flexDirection:'row',alignItems:'center',gap:8,minHeight:44,paddingHorizontal:12},icon:{width:44,height:44,alignItems:'center',justifyContent:'center'},terminal:{minWidth:0,borderRadius:12,overflow:'hidden',paddingBottom:12},code:{fontFamily:'monospace',fontSize:12.8,lineHeight:21.12,paddingHorizontal:16,paddingBottom:8},footer:{fontSize:12,padding:12,borderTopWidth:StyleSheet.hairlineWidth,borderTopColor:'rgba(255,255,255,0.1)'},toggle:{minHeight:44,paddingHorizontal:16,justifyContent:'center'},detail:{padding:12,gap:4}});
