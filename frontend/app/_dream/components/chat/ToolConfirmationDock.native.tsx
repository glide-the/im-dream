// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original resolved pending tool kind and canonical confirmation callback.
// [Output] Native approve/reject, reject-only, network detail and question-answer controls in the composer slot.
// [Pos] Presentation counterpart; existing toolConfirmation owns policy and the server owns settlement.
import {useEffect,useMemo,useRef,useState} from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,TextInput,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {normalizeAskUserQuestions,type AskUserQuestionInput} from './askUserQuestionModel';
import {normalizeMultiSelectAnswer,questionAnswerIsPresent,questionOptionValue} from './askUserQuestionAnswers';
import type {PendingToolConfirmation} from './toolConfirmation';
import {summarizeToolInvocation,isShellTool,resolveToolInputSummary} from './toolInputSummary';
export default function ToolConfirmationDock({confirmation,onConfirm}:{confirmation:PendingToolConfirmation;onConfirm:(approved:boolean,reason?:string,answers?:Record<string,unknown>)=>Promise<void>}) {
  const {t}=useTranslation(),colors=useInkColors(),{height}=useWindowDimensions();
  const [pending,setPending]=useState(false),[failed,setFailed]=useState(false),lock=useRef(false);
  const questions=useMemo(()=>normalizeAskUserQuestions(confirmation.input as AskUserQuestionInput|undefined,t),[confirmation.input,t]);
  const [answers,setAnswers]=useState<Record<string,unknown>>({});
  useEffect(()=>{lock.current=false;setPending(false);setFailed(false);setAnswers({});},[confirmation.toolCallId]);
  useEffect(()=>{setAnswers(current=>Object.fromEntries(questions.map(question=>{const key=question.question || question.id || 'answer';return [key,current[key] ?? (question.multiSelect?normalizeMultiSelectAnswer(question.default):question.default ?? (question.type==='checkbox'?false:''))];})));},[questions]);
  const ask=confirmation.kind==='askuser',rejectOnly=confirmation.kind==='reject-only',network=confirmation.kind==='sandbox-network';
  const valid=questions.every(question=>!question.required || questionAnswerIsPresent(answers[question.question || question.id || 'answer'],question.multiSelect===true));
  const title=t(ask?'chat.toolConfirmation.askUserTitle':rejectOnly?'chat.toolConfirmation.rejectOnlyTitle':network?'chat.toolConfirmation.networkConfirmTitle':'chat.toolConfirmation.confirmTitle',{tool:confirmation.toolName});
  const summary=summarizeToolInvocation(confirmation.toolName,confirmation.input);
  const command=isShellTool(confirmation.toolName)?resolveToolInputSummary(confirmation.input).command:'';
  const policyMode=confirmation.networkRequest?.policyMode;
  const policyLabel=policyMode==='allowlist'?t('chat.toolConfirmation.networkPolicyAllowlist'):policyMode==='open'?t('chat.toolConfirmation.networkPolicyOpen'):policyMode || t('chat.toolConfirmation.unknownTool');
  let detail=command;try {if(!detail && confirmation.input!=null)detail=JSON.stringify(confirmation.input).slice(0,240);}catch{}
  async function submit(approved:boolean) {
    if(lock.current || (ask && approved && !valid))return;lock.current=true;setPending(true);setFailed(false);
    try {const cleaned=Object.fromEntries(Object.entries(answers).filter(([,value])=>value!=='' && value!==null && value!==undefined && (!Array.isArray(value) || value.length)));
      await onConfirm(approved,approved?undefined:t(ask?'chat.toolConfirmation.userCancelledAnswer':'chat.toolConfirmation.userRejectedTool'),ask && approved?cleaned:undefined);
    } catch {lock.current=false;setPending(false);setFailed(true);}
  }
  const action=(label:string,approved:boolean,disabled=false)=><Pressable accessibilityRole="button" accessibilityLabel={label} disabled={pending || disabled} accessibilityState={{disabled:pending || disabled,busy:pending}} onPress={()=>void submit(approved)}
    style={[styles.action,{borderColor:colors['color-border-paper'],backgroundColor:approved?colors['color-text-primary']:colors['color-bg-app'],opacity:disabled?0.5:1}]}>
    <InkLabel style={{fontSize:12.8,color:approved?colors['color-bg-paper']:colors['color-text-primary']}}>{label}</InkLabel>
  </Pressable>;
  return <View style={[styles.card,{maxHeight:Math.min(height*0.46,384),backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>
    <InkLabel accessibilityRole="header" style={{fontSize:14.4,fontWeight:'600',color:colors['color-text-primary']}}>{title}</InkLabel>
    <ScrollView keyboardShouldPersistTaps="handled" style={{flexShrink:1}} contentContainerStyle={{gap:10}}>
      {ask?questions.map(question=>{
        const key=question.question || question.id || 'answer',value=answers[key];
        const change=(next:unknown)=>setAnswers(current=>({...current,[key]:next}));
        return <View key={question.id || key} style={{gap:5}}>
          <InkLabel style={{fontSize:13.12,color:colors['color-text-primary']}}>{`${question.question ?? ''}${question.required?' *':''}`}</InkLabel>
          {question.description?<InkLabel style={{fontSize:11.2,color:colors['color-text-muted']}}>{question.description}</InkLabel>:null}
          {question.options?.length?question.options.map((option,index)=>{
            const optionValue=questionOptionValue(option),label=typeof option==='string'?option:option.label;
            const checked=question.multiSelect?normalizeMultiSelectAnswer(value).includes(optionValue):value===optionValue;
            return <Pressable key={`${optionValue}-${index}`} accessibilityRole={question.multiSelect?'checkbox':'radio'} accessibilityLabel={label} accessibilityState={{checked,disabled:pending}} disabled={pending}
              onPress={()=>change(question.multiSelect?(checked?normalizeMultiSelectAnswer(value).filter(item=>item!==optionValue):[...normalizeMultiSelectAnswer(value),optionValue]):optionValue)} style={[styles.option,{borderColor:colors['color-border-paper'],backgroundColor:checked?colors['color-bg-hover']:colors['color-bg-app']}]}>
              <InkLabel style={{fontSize:13.12,color:colors['color-text-primary']}}>{`${checked?'✓ ':''}${label}`}</InkLabel>
              {typeof option!=='string' && 'description' in option && option.description?<InkLabel style={{fontSize:11.2,color:colors['color-text-muted']}}>{option.description}</InkLabel>:null}
            </Pressable>;
          }):question.type==='checkbox'?<Pressable accessibilityRole="checkbox" accessibilityLabel={question.question} accessibilityState={{checked:value===true,disabled:pending}} disabled={pending} onPress={()=>change(value!==true)} style={styles.option}><InkLabel style={{color:colors['color-text-primary']}}>{`${value===true?'✓ ':''}${t('chat.askUser.yes')}`}</InkLabel></Pressable>
          :<TextInput accessibilityLabel={question.question} value={String(value ?? '')} editable={!pending} placeholder={question.placeholder} placeholderTextColor={colors['color-text-muted']} multiline={question.type==='textarea'} keyboardType={question.type==='number'?'numeric':'default'}
            onChangeText={text=>change(question.type==='number' && text!==''?Number(text):text)} style={[styles.field,{color:colors['color-text-primary'],backgroundColor:colors['color-bg-app'],borderColor:colors['color-border-paper']}]} />}
        </View>;
      }):rejectOnly?<InkLabel style={{color:colors['color-text-secondary']}}>{t('chat.toolConfirmation.rejectOnlyDescription')}</InkLabel>:<>
        {summary?<InkLabel style={{fontSize:13.12,color:colors['color-text-secondary']}}>{summary}</InkLabel>:null}
        {network?<InkLabel style={{fontSize:12.8,color:colors['color-text-primary']}}>{`${t('chat.toolConfirmation.networkHostLabel')}${confirmation.networkRequest?.host || t('chat.toolConfirmation.networkHostUnknown')}\n${t('chat.toolConfirmation.networkPolicyLabel')}${policyLabel}`}</InkLabel>:null}
        {detail?<InkLabel selectable style={{fontSize:12.8,color:colors['color-text-primary']}}>{detail}</InkLabel>:null}
      </>}
    </ScrollView>
    {failed?<InkLabel accessibilityRole="alert" style={{color:colors['color-state-error']}}>{t('chat.inputQueue.unavailable')}</InkLabel>:null}
    <View style={styles.actions}>{pending?<ActivityIndicator color={colors['color-text-primary']} />:null}
      {action(t(ask?'chat.toolConfirmation.cancel':rejectOnly?'chat.toolConfirmation.rejectAndContinue':'chat.toolConfirmation.reject'),false)}
      {!rejectOnly?action(t(ask?'chat.toolConfirmation.submit':'chat.toolConfirmation.approve'),true,ask && !valid):null}
    </View>
  </View>;
}
const styles=StyleSheet.create({card:{borderWidth:1,borderRadius:16,padding:12,gap:10,minHeight:0},actions:{flexDirection:'row',justifyContent:'flex-end',alignItems:'center',gap:8},action:{minHeight:44,paddingHorizontal:14,borderRadius:999,borderWidth:1,justifyContent:'center'},option:{minHeight:44,padding:10,borderWidth:1,borderRadius:8,gap:3},field:{minHeight:44,padding:10,borderWidth:1,borderRadius:8,fontSize:13.12,fontFamily:'Excalifont'}});
