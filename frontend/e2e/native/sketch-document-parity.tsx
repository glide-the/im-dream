// [Input] Production native sketch surface, PNG file import and the original local browser editor.
// [Output] Isolated opaque-file receipt and retry/close checks with no backend, account or storage upload.
// [Pos] Component-only iOS entry; Mac Next serves the sketch document, excluding independent iOS business acceptance.
import {useState} from 'react';
import {AppRegistry,Pressable,SafeAreaView,Text,View,useColorScheme} from 'react-native';
import '../../app/_dream/i18n';
import SketchInputSurface from '../../app/_dream/components/chat/SketchInputSurface.native';
import {releaseNativeFiles} from '../../src/platform/fileUpload.native';
import {inkColors} from '../../src/components/inkColors';
function SketchParity(){
  const [open,setOpen]=useState(false),[reject,setReject]=useState(false),[receipt,setReceipt]=useState('No PNG');const colors=inkColors('system',useColorScheme()==='dark');
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><View style={{padding:16,gap:16}}>
    <Text style={{color:colors['color-text-primary']}}>Original sketch document / native PNG handle — no backend started</Text>
    <Pressable accessibilityRole="button" style={{minHeight:44}} onPress={()=>setOpen(true)}><Text style={{color:colors['color-text-primary']}}>Open sketch</Text></Pressable>
    <Pressable accessibilityRole="checkbox" accessibilityState={{checked:reject}} style={{minHeight:44}} onPress={()=>setReject(value=>!value)}><Text style={{color:colors['color-text-primary']}}>Reject PNG: {String(reject)}</Text></Pressable>
    <Text accessibilityLabel="Sketch receipt" selectable style={{color:colors['color-text-primary']}}>{receipt}</Text>
  </View><SketchInputSurface origin="http://[::1]:5173" open={open} onClose={()=>setOpen(false)} onAdd={async file=>{setReceipt(JSON.stringify({name:file.name,type:file.type,size:file.size,opaqueId:!!file.id,accepted:!reject}));releaseNativeFiles([file.id]);return !reject;}} />
  </SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',()=>SketchParity);
