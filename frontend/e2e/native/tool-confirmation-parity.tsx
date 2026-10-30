// [Input] Production native ToolConfirmationDock and explicit synthetic pending tool inputs.
// [Output] Approve/reject, question validation and reject-only callback evidence without HTTP or runtime startup.
// [Pos] Isolated native component entry; no normal account, files, backend or model calls.
import {useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,ScrollView,Text,View,useColorScheme} from 'react-native';
import i18n from '../../app/_dream/i18n';
import ToolConfirmationDock from '../../app/_dream/components/chat/ToolConfirmationDock.native';
import type {PendingToolConfirmation} from '../../app/_dream/components/chat/toolConfirmation';
import {inkColors} from '../../src/components/inkColors';
void i18n.changeLanguage('en');
const confirmations:Record<string,PendingToolConfirmation>={
  approve:{kind:'confirm',toolCallId:'fixture-read',partKey:'fixture-read',toolName:'Read',input:{file_path:'notes.txt'}},
  rejectOnly:{kind:'reject-only',toolCallId:'fixture-reject',partKey:'fixture-reject',toolName:'Unknown',input:{}},
  network:{kind:'sandbox-network',toolCallId:'fixture-network',partKey:'fixture-network',toolName:'Bash',input:{command:'echo fixture'},networkRequest:{host:'example.invalid',policyMode:'allowlist',matchedAllowedDomain:null}},
  question:{kind:'askuser',toolCallId:'fixture-question',partKey:'fixture-question',toolName:'AskUserQuestion',input:{questions:[
    {question:'Choose sources',multiSelect:true,options:[{label:'Calendar',description:'Planned events'},{label:'Notes',description:'Saved notes'}],required:true},
    {question:'Describe the focus',type:'text',required:true},
  ]}},
};
function ToolConfirmationParity() {
  const [selected,setSelected]=useState<string|null>('question'),[receipt,setReceipt]=useState('No callback');
  const colors=inkColors('system',useColorScheme()==='dark');
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:12,gap:14}}>
    <Text style={{color:colors['color-text-primary']}}>Production tool confirmation — no runtime started</Text>
    <View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>{Object.keys(confirmations).map(key=><Pressable key={key} accessibilityRole="button" accessibilityLabel={'Show '+key} onPress={()=>{setSelected(key);setReceipt('No callback');}} style={{minHeight:44,padding:8}}><Text style={{color:colors['color-text-primary']}}>{key}</Text></Pressable>)}</View>
    {selected?<ToolConfirmationDock key={selected} confirmation={confirmations[selected]} onConfirm={async(approved,reason,answers)=>{setReceipt(JSON.stringify({toolCallId:confirmations[selected].toolCallId,approved,reason:reason ?? null,answers:answers ?? null}));setSelected(null);}} />:null}
    <Text accessibilityLabel="Confirmation receipt" accessibilityValue={{text:receipt}} style={{color:colors['color-text-primary']}}>{receipt}</Text>
  </ScrollView></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>ToolConfirmationParity);
