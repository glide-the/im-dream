// [Input] Production Native message list/tool renderer and explicitly stepped UIMessage parts.
// [Output] Simulator receipts for live ordering, tool updates, cancellation and historical disclosure.
// [Pos] Isolated presentation fixture; no account, database, backend or model calls.
// [Sync] 2026-11-14: step live text/tools, retained history position and completed/cancelled history through production renderers.
import '../../src/platform/sdkWebApis.native';
import React,{useEffect,useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,StyleSheet,View} from 'react-native';
import {isToolUIPart,type UIMessage} from 'ai';
import i18n from '../../app/_dream/i18n';
import ChatMessageList from '../../app/_dream/components/chat/ChatMessageList.native';
import ToolMessagePart from '../../app/_dream/components/chat/ToolMessagePart.native';
import InkLabel from '../../src/components/InkLabel.native';
import useInkColors from '../../src/components/useInkColors.native';
import {setThemeMode} from '../../app/_dream/utils/theme.native';

const intro='我先读取这份文档，再整理相关设计。';
const middle='文档已读完，接下来搜索相关记录。';
const final='整理完成，已保留原文中的设计依据。';
const noHistory:ReadonlySet<string>=new Set();
const historicalIds=new Set(['order-assistant']);

function Fixture(){
  const colors=useInkColors();
  const [ready,setReady]=useState(false),[step,setStep]=useState(0),[updates,setUpdates]=useState(0),[historical,setHistorical]=useState(false),[cancelled,setCancelled]=useState(false),[long,setLong]=useState(false);
  useEffect(()=>{void i18n.changeLanguage('en').then(()=>setReady(true));},[]);
  const parts:UIMessage['parts']=[{type:'text',text:intro,state:'done'}];
  if(step>=1)parts.push({type:'dynamic-tool',toolName:'Read',toolCallId:'order-read',input:{file_path:'/fixture/design.md'},...(step>=2?{state:'output-available',output:`读取完成 ${updates}`}:{state:'input-available'})});
  if(step>=3)parts.push({type:'text',text:middle,state:'done'});
  if(step>=4)parts.push({type:'dynamic-tool',toolName:'Grep',toolCallId:'order-search',input:{pattern:'设计',path:'/fixture'},...(step>=5?{state:'output-available',output:'搜索完成'}:{state:'input-available'})});
  if(step>=5)parts.push({type:'text',text:final,state:'done'});
  const message:UIMessage={id:'order-assistant',role:'assistant',parts,metadata:{turnId:'order-turn',turnStatus:cancelled?'cancelled':step>=5?'completed':'running',...(step>=5?{finalPartIndex:4,durationMs:1000}:{})}};
  const earlier:UIMessage[]=long?Array.from({length:12},(_,index)=>({id:`earlier-${index}`,role:'assistant',parts:[{type:'text',text:`Earlier note ${index+1}. Keep this reading position.\n\nThe next tool update belongs to the current reply.`}]})):[];
  const reset=()=>{setStep(0);setUpdates(0);setHistorical(false);setCancelled(false);setLong(false);};
  const controls:Record<string,()=>void>={'Next part':()=>setStep(value=>Math.min(value+1,5)),'Tool update':()=>setUpdates(value=>value+1),'History':()=>setHistorical(true),'Cancel':()=>{setCancelled(true);setHistorical(true);},'Reset':reset,'Long history':()=>{reset();setLong(true);},'Light':()=>setThemeMode('light'),'Dark':()=>setThemeMode('dark')};
  return <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
    <View style={styles.controls}>{Object.entries(controls).map(([label,onPress])=><Pressable key={label} accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={styles.control}><InkLabel style={{color:colors['color-text-primary'],fontSize:12}}>{label}</InkLabel></Pressable>)}</View>
    {ready?<ChatMessageList messages={[...earlier,message]} threadId={long?'order-long':'order-short'} isLoading={step<5&&!cancelled} historicalMessageIds={historical?historicalIds:noHistory}
      renderOtherPart={(part,_message,index,presentation)=>isToolUIPart(part)?<View testID={`order-tool-${part.toolCallId}`}><ToolMessagePart part={part} origin="http://fixture.invalid" threadId={long?'order-long':'order-short'} active isLast={index===parts.length-1} isLoading={step<5&&!cancelled} toolChoice="full-access" addToolResult={()=>{}} sendUserMessage={async()=>{}} onConfirmationSettled={()=>{}} onSessionExpired={()=>{}} presentation={presentation}/></View>:null}/>:null}
    <InkLabel testID="order-receipt" style={{color:colors['color-text-secondary'],fontSize:12}}>{`step=${step} updates=${updates} history=${historical} cancelled=${cancelled}`}</InkLabel>
  </SafeAreaView>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},controls:{flexDirection:'row',flexWrap:'wrap',paddingHorizontal:8},control:{minHeight:44,paddingHorizontal:10,justifyContent:'center'}});
AppRegistry.registerComponent('InkMemory',()=>Fixture);
