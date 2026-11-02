// [Input] Production native AIInputDockControls and the shared production composer draft hook.
// [Output] Isolated rich-editor/action/callback checks with fixture drafts and file metadata only.
// [Pos] Explicit native component entry; reads the editor-only Mac Next document; no backend, account or model calls.
import {useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,ScrollView,Text,View,useColorScheme} from 'react-native';
import '../../app/_dream/i18n';
import AIInputDockControls from '../../app/_dream/components/chat/AIInputDockControls.native';
import useComposerDraft from '../../app/_dream/components/chat/useComposerDraft';
import MarkdownInputEditor from '../../app/_dream/components/chat/MarkdownInputEditor.native';
import {inkColors} from '../../src/components/inkColors';
import {pickNativeFiles,releaseNativeFiles} from '../../src/platform/fileUpload.native';
import {MAX_UPLOAD_FILE_SIZE_BYTES} from '../../app/_dream/components/chat/AIInputDock.helpers';

function ComposerControlsParity() {
  const [running,setRunning]=useState(false);
  const [fullAccess,setFullAccess]=useState(false);
  const [reject,setReject]=useState(false);
  const [notice,setNotice]=useState('No callback');
  const [receipt,setReceipt]=useState('No submission');
  const colors=inkColors('system',useColorScheme() === 'dark');
  const onStop=()=>{setNotice('stop');setRunning(false);};
  const draft=useComposerDraft({disabled:false,loading:running,onStop,fullAccessEnabled:fullAccess,defaultToolChoice:'auto',
    onUploadBlocked:()=>setNotice('waiting-upload'),releasePreview:()=>{},
    onSendMessage:(message,files,toolChoice)=>{
      setReceipt(`${toolChoice}:${message}:${files?.length ?? 0}`);
      if(reject)return Promise.reject(new Error('fixture rejection'));
    },
  });
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{padding:12,gap:16}}>
    <Text>Production composer controls — no backend started</Text>
    <Text>Original Tiptap document; no backend or application shell in this WebView.</Text>
    <Pressable accessibilityRole="button" accessibilityLabel="System file picker cancel check" onPress={()=>{void pickNativeFiles(MAX_UPLOAD_FILE_SIZE_BYTES).then(selection=>{releaseNativeFiles(selection.files.map(file=>file.id));setNotice(selection.files.length?'picker-returned-files':'picker-cancelled');}).catch(()=>setNotice('picker-failed'));}} style={{minHeight:44,justifyContent:'center'}}><Text>System file picker (cancel check only)</Text></Pressable>
    <View style={{flexDirection:'row',flexWrap:'wrap',gap:12}}>{[
      {name:'Running fixture',value:running,change:()=>setRunning(value=>!value)},
      {name:'Full access fixture',value:fullAccess,change:()=>setFullAccess(value=>!value)},
      {name:'Reject submission fixture',value:reject,change:()=>setReject(value=>!value)},
    ].map(item=><Pressable key={item.name} accessibilityRole="checkbox" accessibilityLabel={item.name} accessibilityState={{checked:item.value}} onPress={item.change} style={{minHeight:44,justifyContent:'center'}}><Text>{item.name}: {String(item.value)}</Text></Pressable>)}</View>
    <View style={{borderWidth:1,borderColor:colors['color-border-paper'],borderRadius:16,padding:12,backgroundColor:colors['color-bg-paper']}}>
      <MarkdownInputEditor origin="http://[::1]:5173" ariaLabel="Fixture draft" value={draft.query} onChange={draft.setQuery} onSubmit={draft.handleSend} placeholder="Ask Ink & Memory…" />
      <AIInputDockControls draft={draft} disabled={false} loading={running} fullAccessEnabled={fullAccess} onStop={onStop}
        onChooseFiles={()=>{setNotice('choose-files');draft.setUploadedFiles(files=>[...files,{id:'fixture-ready',name:'fixture.txt',mimeType:'text/plain',size:1}]);}}
        onOpenSketch={()=>setNotice('open-sketch')} />
    </View>
    <Text accessibilityLabel="Callback result">{notice}</Text>
    <Text accessibilityLabel="Submission receipt">{receipt}</Text>
    <Text accessibilityLabel="Attachment count">{String(draft.uploadedFiles.length)}</Text>
  </ScrollView></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>ComposerControlsParity);
