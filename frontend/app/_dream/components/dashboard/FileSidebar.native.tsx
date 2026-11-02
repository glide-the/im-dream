// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original Workspace file tree/API, selected Thread, platform file selection/batch upload/export and AppState.
// [Output] Original file sidebar operations with one list scroller, current directory, upload queue and explicit failure recovery.
// [Pos] RN presentation of FileSidebar; no new endpoints, workspace ownership rules, task execution or storage service.
// [Sync] 2026-10-28: reuse the original tree and DELETE contract; isolate reader identity from in-flight mutations and file leases.
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {useTranslation} from 'react-i18next';
import {WorkspaceFileRequestError} from '../chat/workspaceFileAccess';
import {ActivityIndicator,AppState,Pressable,SafeAreaView,ScrollView,StyleSheet,View} from 'react-native';
import {readWorkspaceFileTree,deleteWorkspaceFile,flattenVisible,formatFileSize,normalizePath,type FileInfo} from '../../api/workspaceFilesApi';
import {clientFetch} from '../../../../src/platform/transport';
import {createNativeFileUploadAdapter,pickNativeFiles,type NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {workspaceResources,type WorkspaceAvailability,type WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {IconChevronRight,IconDownload,IconFile,IconFolder,IconPlus,IconTrash,IconX} from '../chat/Icons';
type UploadAdapter=Pick<ReturnType<typeof createNativeFileUploadAdapter>,'uploadWorkspaceBatch'|'dispose'>;
type QueueItem={id:string;relativePath:string;size:number;status:'uploading'|'success'|'error'};
interface Props {sessionId?:string;open:boolean;availability:WorkspaceAvailability;onClose:()=>void;onSessionExpired?:()=>void;transport?:typeof fetch;resources?:WorkspaceResources;files?:UploadAdapter;pickFiles?:typeof pickNativeFiles;}
export default function FileSidebar({sessionId,open,availability,onClose,onSessionExpired,transport=clientFetch,resources=workspaceResources,files,pickFiles=pickNativeFiles}:Props){
 const {t}=useTranslation();
 const colors=useInkColors(),text={color:colors['color-text-primary']};
 const identity=JSON.stringify([sessionId,availability]),owner=useRef(identity);owner.current=identity;
 const mounted=useRef(true),sessionExpired=useRef(onSessionExpired);sessionExpired.current=onSessionExpired;
 const adapter=useMemo(()=>files??createNativeFileUploadAdapter(),[files]);
 const accessTransport=useMemo<typeof fetch>(()=>async(input,init)=>{const response=await transport(input,init);if(response.status===401)sessionExpired.current?.();return response;},[transport]);
 const [foreground,setForeground]=useState(AppState.currentState==='active'),[revision,reload]=useState(0);
 const [snapshot,setSnapshot]=useState<{identity:string;tree:FileInfo[];loading:boolean;error:string|null}>({identity,tree:[],loading:false,error:null});
 const [directory,setDirectory]=useState({identity,path:''}),[notice,setNotice]=useState<{identity:string;message:string}|null>(null),[queue,setQueue]=useState<{identity:string;items:QueueItem[]}>({identity,items:[]});
 const [uploading,setUploading]=useState(false),[deleting,setDeleting]=useState<string|null>(null),[downloading,setDownloading]=useState<string|null>(null);
 const picking=useRef(false),deletingRef=useRef(false),download=useRef<{controller:AbortController}|null>(null);
 const currentPath=directory.identity===identity?directory.path:'',state=snapshot.identity===identity?snapshot:{tree:[],loading:false,error:null};
 const enabled=Boolean(sessionId)&&availability==='enabled';
 const alive=(key:string)=>mounted.current&&owner.current===key;
 const tell=(key:string,message:string)=>{if(alive(key))setNotice({identity:key,message});};
 useEffect(()=>{mounted.current=true;const listener=AppState.addEventListener('change',next=>setForeground(next==='active'));return()=>{mounted.current=false;listener.remove();download.current?.controller.abort();adapter.dispose();};},[adapter]);
 useEffect(()=>{
  if(!open||!foreground||!enabled)return;
  const controller=new AbortController();let active=true;
  setSnapshot(previous=>({identity,tree:previous.identity===identity?previous.tree:[],loading:true,error:null}));
  void readWorkspaceFileTree(sessionId!,{transport:accessTransport,signal:controller.signal}).then(tree=>{if(active)setSnapshot({identity,tree,loading:false,error:null});}).catch(error=>{if(active)setSnapshot(previous=>({identity,tree:previous.identity===identity?previous.tree:[],loading:false,error:error instanceof Error?error.message:'目录刷新失败'}));});
  const timer=setInterval(()=>reload(value=>value+1),60_000);
  return()=>{active=false;controller.abort();clearInterval(timer);};
 },[identity,open,foreground,enabled,sessionId,accessTransport,revision]);
 useEffect(()=>{if(!open||!foreground)download.current?.controller.abort();return()=>download.current?.controller.abort();},[identity,open,foreground]);
 async function remove(file:FileInfo){
  if(!sessionId||!enabled||deletingRef.current)return;const key=identity,id=sessionId;deletingRef.current=true;setDeleting(file.path);
  try{await deleteWorkspaceFile(id,file.path,accessTransport);if(alive(key))reload(value=>value+1);}catch(error){tell(key,error instanceof Error?error.message:'删除失败');}
  finally{deletingRef.current=false;if(mounted.current)setDeleting(null);}
 }
 async function choose(directoryMode:boolean){
  if(!sessionId||!enabled||picking.current)return;const key=identity,id=sessionId,path=currentPath;picking.current=true;setUploading(true);setNotice(null);let selected:NativePickedFile[]=[];
  try{
   // The original file sidebar has no client size quota; the picker uses only JS/Swift's shared integer representation limit.
   const result=await pickFiles(Number.MAX_SAFE_INTEGER,directoryMode);selected=result.files;
   if(!alive(key))return;
   if(result.rejected.length)throw Error('文件无法读取。');
   if(!selected.length)return;
   const items=selected.map(file=>({id:file.id,relativePath:normalizePath(file.relativePath||file.name),size:file.size,status:'uploading' as const}));setQueue({identity:key,items});
   const response=await adapter.uploadWorkspaceBatch(selected,id,path);
   if(response.status===401)sessionExpired.current?.();
   if(!response.ok){const body=await response.json().catch(()=>({})) as {error?:string};throw Error(body.error||`上传失败 (${response.status})`);}
   if(alive(key)){setQueue({identity:key,items:items.map(item=>({...item,status:'success'}))});tell(key,`Uploaded ${selected.length} item${selected.length===1?'':'s'}.`);reload(value=>value+1);}
  }catch(error){if(alive(key)){setQueue(previous=>previous.identity===key?{identity:key,items:previous.items.map(item=>({...item,status:'error'}))}:previous);tell(key,error instanceof Error?error.message:'上传失败');}}
  finally{selected.forEach(file=>resources.release(file));picking.current=false;if(mounted.current)setUploading(false);}
 }
 async function save(file:FileInfo){
  if(!sessionId||!enabled||download.current)return;const key=identity,controller=new AbortController(),operation={controller};download.current=operation;setDownloading(file.path);let asset:NativePickedFile|undefined;
  try{asset=await resources.acquire({threadId:sessionId,path:file.path,download:true},controller.signal);if(!alive(key)||controller.signal.aborted)return;const receipt=await resources.export(asset);if(receipt.completed)tell(key,`Started download: ${file.isDirectory?file.name+'.zip':file.name}`);}
  catch(error){if(!controller.signal.aborted)tell(key,error instanceof WorkspaceFileRequestError?t(`chat.workspaceFile.${error.failure}`):error instanceof Error?error.message:'下载失败');}
  finally{if(asset)resources.release(asset);if(download.current===operation)download.current=null;if(mounted.current)setDownloading(null);}
 }
 if(!open)return null;
 const visible=flattenVisible(state.tree,currentPath),breadcrumbs=['workspace',...currentPath.split('/').filter(Boolean)];
 const button=(label:string,action:()=>void,content:ReactNode,disabled=false)=><Pressable accessibilityRole="button" accessibilityLabel={label} disabled={disabled} onPress={action} style={styles.icon}>{content}</Pressable>;
 const color=colors['color-text-muted'];
 return <SafeAreaView accessibilityLabel="Workspace files" accessibilityViewIsModal style={[styles.fill,{backgroundColor:colors['color-bg-app']}]} onAccessibilityEscape={onClose}>
  <View style={[styles.header,{borderColor:colors['color-border-paper']}]}><IconFolder width={17.6} height={17.6} color={colors['color-action-link']}/><InkLabel style={[text,{fontWeight:'600',flex:1}]}>Files</InkLabel>
   {button('Refresh files',()=>reload(value=>value+1),state.loading?<ActivityIndicator/>:<InkLabel style={{color}}>↻</InkLabel>,!enabled)}
   {button('Upload files',()=>void choose(false),<IconPlus width={16} height={16} color={color}/>,!enabled||uploading)}
   {button('Upload folder',()=>void choose(true),<IconFolder width={16} height={16} color={color}/>,!enabled||uploading)}
   {button('Close files',onClose,<IconX width={16} height={16} color={color}/>)}
  </View>
  <ScrollView style={styles.fill} contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
   <View accessibilityLabel="Workspace path" style={styles.breadcrumb}>{breadcrumbs.map((part,index)=><Pressable key={index} accessibilityRole="button" accessibilityLabel={index===0?'Workspace root':part} onPress={()=>setDirectory({identity,path:index===0?'':currentPath.split('/').slice(0,index).join('/')})} style={styles.crumb}><InkLabel style={{color:colors['color-text-secondary']}}>{`${index?'/ ':''}${part}`}</InkLabel></Pressable>)}</View>
   {!enabled?<InkLabel accessibilityRole="alert" style={text}>{availability==='loading'?'Checking Workspace Mode…':!sessionId?'选择一个对话后查看文件。':'Workspace Mode is disabled.'}</InkLabel>:null}
   {state.error?<View><InkLabel accessibilityRole="alert" style={{color:colors['color-state-error']}}>{state.error}</InkLabel>{button('Retry files',()=>reload(value=>value+1),<InkLabel style={text}>重试</InkLabel>)}</View>:null}
   {notice?.identity===identity?<InkLabel accessibilityLiveRegion="polite" style={text}>{notice.message}</InkLabel>:null}
   {enabled&&!state.loading&&!state.error&&!visible.length?<InkLabel style={{color}}>No files yet.</InkLabel>:null}
   {visible.map(file=><View key={file.path} style={[styles.row,{backgroundColor:colors['color-bg-paper']}]}>
    {file.isDirectory?button(`Open ${file.name}`,()=>setDirectory({identity,path:file.path}),<IconChevronRight width={14.4} height={14.4} color={color}/>):<IconFile width={16} height={16} color={color}/>}
    {file.isDirectory?<IconFolder width={16} height={16} color={colors['color-action-link']}/>:null}
    <View style={styles.fill}><InkLabel numberOfLines={1} style={[text,{fontSize:13.28}]}>{file.name}</InkLabel>{!file.isDirectory?<InkLabel style={{color,fontSize:11.2}}>{formatFileSize(file.size)}</InkLabel>:null}</View>
    {button(file.isDirectory?`Download ${file.name} as ZIP`:`Download ${file.name}`,()=>void save(file),downloading===file.path?<ActivityIndicator/>:<IconDownload width={15.2} height={15.2} color={color}/>,Boolean(downloading))}
    {button(`Delete ${file.name}`,()=>void remove(file),deleting===file.path?<ActivityIndicator/>:<IconTrash width={15.2} height={15.2} color={colors['color-state-danger']}/>,Boolean(deleting))}
   </View>)}
   {queue.identity===identity?queue.items.map(item=><View key={item.id} style={styles.queue}><InkLabel style={text}>{item.relativePath}</InkLabel><InkLabel style={{color}}>{`${formatFileSize(item.size)} · ${item.status}`}</InkLabel></View>):null}
  </ScrollView>
 </SafeAreaView>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',paddingHorizontal:12,borderBottomWidth:1,gap:4},icon:{minWidth:36,minHeight:44,justifyContent:'center',alignItems:'center'},body:{padding:12,gap:8},row:{flexDirection:'row',alignItems:'center',gap:7.2,paddingHorizontal:8,paddingVertical:4,borderRadius:10},breadcrumb:{flexDirection:'row',flexWrap:'wrap',alignItems:'center'},crumb:{minHeight:44,justifyContent:'center',paddingHorizontal:4},queue:{paddingVertical:8,gap:4}});
