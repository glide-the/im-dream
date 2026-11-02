// [Input] Production native Workspace preview/Markdown, actual iOS file store/export and synthetic report/image resources.
// [Output] Isolated Hermes file-image, relative-reference, material-copy and system-export cancellation qualification.
// [Pos] Explicit technical fixture; no runtime startup, credentials, business HTTP, model or database calls.
// [Sync] 2026-10-28: native bytes originate from a small generated fixture PNG through the existing Sketch import boundary.
import '../../src/platform/sdkWebApis.native';
import {useEffect,useState} from 'react';
import {AppRegistry,NativeModules,Pressable,SafeAreaView,ScrollView,StyleSheet,TextInput,View,useColorScheme} from 'react-native';
import i18n from '../../app/_dream/i18n';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import FileSidebar from '../../app/_dream/components/dashboard/FileSidebar.native';
import WorkspaceFilePreview from '../../app/_dream/components/chat/WorkspaceFilePreview.native';
import ChatMarkdown from '../../app/_dream/components/chat/ChatMarkdown.native';
import {MAX_UPLOAD_FILE_SIZE_BYTES} from '../../app/_dream/components/chat/AIInputDock.helpers';
import type {WorkspaceResources} from '../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../src/platform/fileUpload.native';
import InkLabel from '../../src/components/InkLabel.native';
import {inkColors} from '../../src/components/inkColors';
const png='iVBORw0KGgoAAAANSUhEUgAAAFAAAAAwCAYAAACG5f33AAAAbUlEQVR4nO3QMQ0AIQDAQPxh5FVgHTw8A2lyQ/fmxvrm1v/G64F6AAECTAcQIMB0AAECTAcQIMB0AAECTAcQIMB0AAECTAcQIMB0AAECTAcQIMB0AAECTAcQIMB0AAECTAcQIMB0AAECTAfwsgMdvdHhPNELeAAAAABJRU5ErkJggg==',runtime=NativeModules.InkRuntime;
const counters={reads:0,releases:0,copies:0,exports:0,cancelled:0,added:0,live:new Set<string>()};
const listeners=new Set<()=>void>(),notify=()=>listeners.forEach(listener=>listener());
let serial=0;
const resources:WorkspaceResources={
 async acquire({path},signal){
  if(signal?.aborted)throw Error('Fixture read cancelled');
  const file:NativePickedFile=path.endsWith('.png')?await runtime.importSketch({base64:png,name:'native-fixture.png',maxBytes:MAX_UPLOAD_FILE_SIZE_BYTES}):{id:'fixture-document-'+(++serial),uri:'file:///synthetic-report',name:path.split('/').at(-1)!,type:'text/markdown',size:0};
  counters.reads++;counters.live.add(file.id);notify();return file;
 },
 async text(file){return file.name==='notes.md'?'# Linked notes\n\nThe original report opens its sibling.':'# Workspace report\n\nOriginal report body. [Sibling](notes.md)\n\n[Open image](image.png)\n\n<script>literal content</script>';},
 async copy(file){const copy=await runtime.copyWorkspaceFile(file.id);counters.copies++;counters.live.add(copy.id);notify();return copy;},
 async export(file){if(file.id.startsWith('fixture-document-'))throw Error('Synthetic document export outside this fixture');counters.exports++;notify();const receipt=await runtime.exportFile(file.id);if(!receipt.completed)counters.cancelled++;notify();return receipt;},
 release(file){if(!counters.live.delete(file.id))return;counters.releases++;if(!file.id.startsWith('fixture-document-'))runtime.releaseFiles([file.id]);notify();},
};
const directoryTransport:typeof fetch=async(_input,init)=>{
 if(init?.method==='DELETE')return new Response(JSON.stringify({error:'Synthetic deletion disabled in UI fixture'}),{status:403});
 return new Response(JSON.stringify({tree:[{name:'project',path:'project',isDirectory:true,size:0,modifiedAt:'2026-10-28T00:00:00Z',children:[{name:'report.md',path:'project/report.md',isDirectory:false,size:12,modifiedAt:'2026-10-28T00:00:00Z'}]}]}),{status:200});
};
const directoryUploads={async uploadWorkspaceBatch(){return new Response(JSON.stringify({error:'Business upload outside this component fixture'}),{status:503});},dispose(){}};
function Page(){
 const colors=inkColors('system',useColorScheme()==='dark'),text={color:colors['color-text-primary']};
 const [filesOpen,setFilesOpen]=useState(false);const [uri,setUri]=useState<string|null>(null),[draft,setDraft]=useState('Existing unsent draft'),[,update]=useState(0);
 useEffect(()=>{const listener=()=>update(value=>value+1);listeners.add(listener);return()=>{listeners.delete(listener);};},[]);
 const add=async(file:NativePickedFile)=>{counters.added++;resources.release(file);notify();return true;};
 return <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
  <View style={styles.header}><InkLabel style={text}>Workspace native fixture</InkLabel>
   <InkLabel style={text}>{`reads ${counters.reads} · live ${counters.live.size} · released ${counters.releases}`}</InkLabel>
   <InkLabel style={text}>{`copies ${counters.copies} · added ${counters.added} · exports ${counters.exports} · cancelled ${counters.cancelled}`}</InkLabel>
   <TextInput accessibilityLabel="Source draft" value={draft} onChangeText={setDraft} style={[styles.input,text,{borderColor:colors['color-border-paper']}]} />
   <Pressable accessibilityRole="button" accessibilityLabel="Open report" onPress={()=>setUri('workspace://files/report.md')} style={styles.button}><InkLabel style={text}>Open report</InkLabel></Pressable>
  </View>
  <Pressable accessibilityRole="button" accessibilityLabel="Open files" onPress={()=>setFilesOpen(true)} style={[styles.button,{paddingHorizontal:12}]}><InkLabel style={text}>Open files</InkLabel></Pressable>
  <ScrollView style={styles.fill} contentContainerStyle={styles.body}><ChatMarkdown text={'Before image.\n\n![Native fixture](workspace://files/image.png)\n\nAfter image.'} workspaceSessionId="fixture-thread" workspaceAvailability="enabled" workspaceResources={resources} onOpenWorkspace={setUri} onAddImageMaterial={add}/></ScrollView>
  <View style={StyleSheet.absoluteFill} pointerEvents={filesOpen?'auto':'none'}><FileSidebar sessionId="fixture-thread" open={filesOpen} availability="enabled" onClose={()=>setFilesOpen(false)} transport={directoryTransport} resources={resources} files={directoryUploads}/></View>
  {uri?<WorkspaceFilePreview uri={uri} threadId="fixture-thread" availability="enabled" resources={resources} onClose={()=>setUri(null)} onOpenWorkspace={setUri} onAddImageMaterial={add}/>:null}
 </SafeAreaView>;
}
function Boot(){const [ready,setReady]=useState(false);useEffect(()=>{void Promise.all([i18n.changeLanguage('en'),loadBrowserSession(async()=>new Response(JSON.stringify({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'f'.repeat(43)}),{status:200}))]).then(()=>setReady(true));},[]);return ready?<Page/>:<InkLabel>Preparing fixture</InkLabel>;}
AppRegistry.registerComponent('InkMemory',()=>Boot);
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{padding:12,gap:4},body:{padding:12},input:{minHeight:44,padding:8,borderWidth:1,borderRadius:8,fontFamily:'Excalifont',fontSize:16},button:{minHeight:44,justifyContent:'center'}});
