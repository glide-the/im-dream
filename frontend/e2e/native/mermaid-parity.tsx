// [Input] Production Native Markdown/Mermaid and the existing App-owned runtime.
// [Output] Actual Hermes/WebKit diagram, source, zoom, clipboard and PNG export qualification.
// [Pos] Explicit technical entry only; synthetic source, no account, model, Notion or business submissions.
import {useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,ScrollView,Text,View} from 'react-native';
import '../../app/_dream/i18n';
import {BackendRuntimeManager} from '../../src/runtime/BackendRuntimeManager';
import ChatMarkdown from '../../app/_dream/components/chat/ChatMarkdown.native';
import useInkColors from '../../src/components/useInkColors.native';
const original='flowchart LR\n A[Original input] --> B[Saved output]\n';
function Entry(){
  const colors=useInkColors(),[origin,setOrigin]=useState(''),[error,setError]=useState(false),[chart,setChart]=useState(original),[visible,setVisible]=useState(true);
  const action=(label:string,run:()=>void)=><Pressable key={label} accessibilityRole="button" accessibilityLabel={label} onPress={run} style={{minHeight:44,padding:12,borderWidth:1,borderColor:colors['color-border-paper']}}><Text style={{color:colors['color-text-primary']}}>{label}</Text></Pressable>;
  async function start(){try{setError(false);setOrigin((await BackendRuntimeManager.ensureStarted()).localWebOrigin);}catch{setError(true);}}
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><ScrollView contentContainerStyle={{padding:12,gap:12}}>
    <Text style={{color:colors['color-text-primary']}}>Mermaid — technical fixture</Text>
    <Text style={{color:colors['color-text-muted']}}>Synthetic diagram; account, model, Notion and business submissions: 0.</Text>
    {!origin?action('Start packaged diagram document',()=>void start()):null}
    {error?<Text accessibilityRole="alert">Packaged runtime unavailable; retry the original start.</Text>:null}
    <View style={{flexDirection:'row',flexWrap:'wrap'}}>{action('Update diagram',()=>setChart('sequenceDiagram\n participant U as Reader\n participant D as Diagram\n U->>D: View saved source\n D-->>U: Original result\n'))}{action('Incomplete diagram',()=>setChart('flowchart LR\n A['))}{action('Restore diagram',()=>setChart(original))}{action(visible?'Leave diagram':'Return to diagram',()=>setVisible(value=>!value))}</View>
    {origin&&visible?<ChatMarkdown origin={origin} text={'Native paragraph.\n\n```js\nconst value = 1;\n```\n\n```mermaid\n'+chart+'```'}/>:null}
  </ScrollView></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>Entry);
