// [Input] Original normalized readonly subagent messages and server redaction/truncation flags.
// [Output] Native conversation timeline, paired tool disclosure and existing historical/status feedback.
// [Pos] Native presentation only; no model, tool invocation or task-control action.
import {useState} from 'react';
import {Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import type {ThreadSubagentMessage,ThreadSubagentStatus} from '../../hooks/useThreadSubagents';
import ChatMarkdown,{type NativeChatMarkdownProps} from './ChatMarkdown.native';
function Tool({call,result}:{call:ThreadSubagentMessage;result:ThreadSubagentMessage|null}){
 const {t}=useTranslation(),c=useInkColors(),[open,setOpen]=useState(false);
 return <View style={[s.tool,{borderColor:c[result?.status==='failed'?'color-state-error':'color-action-link']}]}>
  <Pressable accessibilityRole="button" accessibilityState={{expanded:open}} onPress={()=>setOpen(value=>!value)} style={s.button}><InkLabel style={{color:c['color-text-secondary']}}>{`${t('chat.subagents.timeline.toolUsed',{tool:call.toolName??t('chat.subagents.toolFallback')})} · ${t(`chat.subagents.activityStatus.${result?.status??call.status??'started'}`)}`}</InkLabel></Pressable>
  {open?<View style={s.parts}>{call.redacted||result?.redacted?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.redacted')}</InkLabel>:<>
   {call.input?<InkLabel selectable style={{color:c['color-text-body']}}>{`${t('chat.subagents.timeline.toolInput')}\n${call.input}`}</InkLabel>:null}
   {result?.output?<InkLabel selectable style={{color:c['color-text-body']}}>{`${t('chat.subagents.timeline.toolOutput')}\n${result.output}`}</InkLabel>:null}
  </>}{call.truncated||result?.truncated?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.truncated')}</InkLabel>:null}</View>:null}
 </View>;
}
export default function SubagentMessageTimeline({messages,taskStatus,legacy,truncated,origin,...markdown}:{messages:ThreadSubagentMessage[];taskStatus:ThreadSubagentStatus;legacy:boolean;truncated:boolean;origin?:string}&Pick<NativeChatMarkdownProps,'workspaceSessionId'|'workspaceAvailability'|'workspaceResources'|'onOpenLink'|'onOpenWorkspace'>){
 const {t,i18n}=useTranslation(),c=useInkColors(),results=new Map(messages.filter(row=>row.kind==='tool_result'&&row.toolCallId).map(row=>[row.toolCallId!,row]));
 const paired=new Set(messages.filter(row=>row.kind==='tool_call'&&row.toolCallId&&results.has(row.toolCallId)).map(row=>row.toolCallId));
 const stamp=(value:string|null)=>value&&Number.isFinite(Date.parse(value))?new Intl.DateTimeFormat(i18n.language,{hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value)):'';
 return <View style={s.parts}>
  {legacy?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.legacy')}</InkLabel>:null}
  {truncated?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.projectionTruncated')}</InkLabel>:null}
  {!messages.length?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.empty')}</InkLabel>:null}
  {messages.map(message=>{
   if(message.kind==='tool_result'&&paired.has(message.toolCallId))return null;
   if(message.kind==='tool_call')return <Tool key={message.id} call={message} result={message.toolCallId?results.get(message.toolCallId)??null:null}/>;
   if(message.kind==='tool_result')return <Tool key={message.id} call={{...message,kind:'tool_call',input:null}} result={message}/>;
   if(message.redacted)return <InkLabel key={message.id} style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.redacted')}</InkLabel>;
   const label=message.kind==='task'?'taskDispatch':message.kind==='final'?'finalReply':message.kind==='status'?'statusUpdate':'agentUpdate';
   return <View key={message.id} style={s.parts}><InkLabel style={{fontSize:12,color:c['color-text-muted']}}>{`${t('chat.subagents.timeline.'+label)}${stamp(message.timestamp)?' · '+stamp(message.timestamp):''}`}</InkLabel>
    {message.kind==='system'?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.unknownEvent',{event:message.text||t('chat.subagents.unknown')})}</InkLabel>:message.text?<ChatMarkdown text={message.text} origin={origin} {...markdown}/>:null}
    {message.truncated?<InkLabel style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.truncated')}</InkLabel>:null}
   </View>;
  })}
  {taskStatus==='running'?<InkLabel accessibilityLiveRegion="polite" style={{color:c['color-text-muted']}}>{t('chat.subagents.timeline.running')}</InkLabel>:null}
 </View>;
}
const s=StyleSheet.create({parts:{gap:12,minWidth:0},tool:{borderLeftWidth:2,paddingLeft:12},button:{minHeight:44,justifyContent:'center'}});
