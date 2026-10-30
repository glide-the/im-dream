// [Input] Production native composer, selector, shared DTO builder and explicitly synthetic Decks.
// [Output] Context/permission/draft-only Skill checks without backend, account or model execution.
// [Pos] Isolated native component entry; Mac Next serves only the original local editor document.
import {useState} from 'react';
import {AppRegistry,KeyboardAvoidingView,Platform,Pressable,SafeAreaView,ScrollView,Text,View,useColorScheme} from 'react-native';
import i18n from '../../app/_dream/i18n';
import AIInputDock from '../../app/_dream/components/chat/AIInputDock.native';
import DeckChatSelector,{type DeckAgentSelection} from '../../app/_dream/components/deck/DeckChatSelector.native';
import type {Deck,Voice} from '../../app/_dream/api/voiceApi';
import {toAttachment} from '../../app/_dream/components/chat/AIInputDock.helpers';
import {buildClaudeChatRequest} from '../../app/_dream/lib/claude-chat-request';
import {inkColors} from '../../src/components/inkColors';
void i18n.changeLanguage('en');
const decks=[{id:'fixture-writing',name:'Writing',name_en:'Writing',name_zh:'创作',enabled:true,voices:[
  {id:'fixture-writer',name:'Writer',name_en:'Writer',name_zh:'写作',enabled:true,icon:'brain',color:'purple'},
  {id:'fixture-editor',name:'Editor',name_en:'Editor',name_zh:'编辑',enabled:true,icon:'lightbulb',color:'green'},
  {id:'fixture-disabled',name:'Disabled Agent',enabled:false,icon:'heart',color:'pink'},
] as Voice[]}] as Deck[];
function ComposerContextParity() {
  const [selection,setSelection]=useState<DeckAgentSelection>(),[full,setFull]=useState(false),[running,setRunning]=useState(false),[loading,setLoading]=useState(false);
  const [receipt,setReceipt]=useState('No submission'),[prefill,setPrefill]=useState(''),[nonce,setNonce]=useState(0),[notice,setNotice]=useState('No action');
  const colors=inkColors('system',useColorScheme()==='dark');
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><KeyboardAvoidingView style={{flex:1}} enabled={Platform.OS!=='ios'}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:12,gap:12}}>
      <Text style={{color:colors['color-text-primary']}}>Production composer context — no business requests</Text>
      <View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>{[
        {label:'Full access fixture',value:full,onPress:()=>setFull(value=>!value)},
        {label:'Running fixture',value:running,onPress:()=>setRunning(value=>!value)},
        {label:'Catalog loading fixture',value:loading,onPress:()=>setLoading(value=>!value)},
      ].map(item=><Pressable key={item.label} accessibilityRole="checkbox" accessibilityLabel={item.label} accessibilityState={{checked:item.value}} onPress={item.onPress} style={{minHeight:44,justifyContent:'center'}}><Text style={{color:colors['color-text-primary']}}>{`${item.label}: ${item.value}`}</Text></Pressable>)}</View>
      <Pressable accessibilityRole="button" onPress={()=>{setPrefill('/');setNonce(value=>value+1);}} style={{minHeight:44,justifyContent:'center'}}><Text style={{color:colors['color-text-primary']}}>Prefill slash</Text></Pressable>
      <AIInputDock origin="http://[::1]:5173" fullAccessEnabled={full} defaultToolChoice="manual" loading={running} onStop={()=>{setRunning(false);setNotice('stop');}} onOpenSketch={()=>setNotice('sketch callback')}
        prefill={prefill} prefillNonce={nonce} deckId={selection?.deckId} workspaceEnabled={false}
        contextControl={<DeckChatSelector decks={decks} selectedAgentId={selection?.agentId} onChange={setSelection} loading={loading} />}
        onSendMessage={(text,files,toolChoice)=>{
          const request=buildClaudeChatRequest({id:'fixture-thread',message:{id:'fixture-message',role:'user',parts:[{type:'text',text}]},context:{deckId:selection?.deckId,voiceId:selection?.agentId,imFullAccessEnabled:full,currentToolChoice:'manual'},attachments:files?.map(toAttachment),toolChoice});
          setReceipt(JSON.stringify({deckId:request.deckId ?? null,voiceId:request.voiceId ?? null,toolChoice:request.toolChoice,text,files:request.attachments?.length ?? 0}));
        }} />
      <Text accessibilityLabel="Selected Agent" style={{color:colors['color-text-primary']}}>{selection?.agentId ?? 'No Agent'}</Text>
      <Text accessibilityLabel="Submission receipt" style={{color:colors['color-text-primary']}}>{receipt}</Text>
      <Text accessibilityLabel="Action receipt" style={{color:colors['color-text-primary']}}>{notice}</Text>
    </ScrollView>
  </KeyboardAvoidingView></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>ComposerContextParity);
