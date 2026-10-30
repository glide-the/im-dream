// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Current original Chat snapshot, full-history HTTP and the local DOM export leaf.
// [Output] Native share controls, original partial/final previews and system PNG export with scoped file cleanup.
// [Pos] Native share owner; DOM owns capture only, native owns authentication, lifecycle and file handles.
import {forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {ActivityIndicator,Image,Keyboard,Modal,NativeModules,Pressable,SafeAreaView,ScrollView,StyleSheet,View,useWindowDimensions} from 'react-native';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import type {UIMessage} from 'ai';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport.native';
import {createWorkspaceResources,type WorkspaceAvailability,type WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import {importNativeSketch,releaseNativeFiles,type NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {toExportChatMessage,buildExportPendingConfirmation,type ExportThreadImageOptions} from './chatImageProjection';
import {ClaudeThreadHydrationUnknownError,fetchFullClaudeThreadMessages} from './threadSessionHydration';
import {mergeCompleteHistoryWithLive} from './chatHistoryWindow';
import {chatImageDocumentUrl,readChatImageEvent,type ChatImageCommand,type ChatImageEvent,type ChatImagePNG} from './ChatImageDocument.protocol';
import {parseWorkspaceUri} from './workspaceUri';
import type {PendingToolConfirmation} from './toolConfirmation';
import {IconShare,IconX} from './Icons';

export interface NativeChatShareHandle {open:()=>void;}
interface Snapshot {messages:UIMessage[];pendingConfirmation:PendingToolConfirmation|null;toolChoice:string;}
interface Props {origin:string;threadId:string|null;title:string;availability:WorkspaceAvailability;snapshot:()=>Snapshot;resources?:WorkspaceResources;transport?:typeof fetch;onSessionExpired?:()=>void;}
interface Preview {images:(NativePickedFile&{width:number;height:number})[];fileName:string;partial:boolean;}
interface Job {id:string;threadId:string;theme:'light'|'dark'|'system';controller:AbortController;options?:ExportThreadImageOptions;sentTo?:string;deliveryId?:string;}
const runtime=NativeModules.InkRuntime;
const requestId=()=>`share_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
const defaultResources=createWorkspaceResources();
export default forwardRef<NativeChatShareHandle,Props>(function ChatShareSurface({origin,threadId,title,availability,snapshot,resources=defaultResources,transport=clientFetch,onSessionExpired},ref){
 const {t,i18n}=useTranslation(),colors=useInkColors(),theme=useNativeThemeMode(),{width,height}=useWindowDimensions();
 const text={color:colors['color-text-primary']},muted={color:colors['color-text-muted']};
 const view=useRef<WebView<object>>(null),documentId=useRef(''),active=useRef(true),job=useRef<Job|null>(null),previewRef=useRef<Preview|null>(null),exportingRef=useRef(false),downloadingRef=useRef(false),imageReads=useRef(new Set<AbortController>()),receipts=useRef(Promise.resolve());
 const observedThread=useRef(threadId);
 const latest=useRef({threadId,title,availability,snapshot,resources,transport,onSessionExpired,t,theme,language:i18n.resolvedLanguage??i18n.language});latest.current={threadId,title,availability,snapshot,resources,transport,onSessionExpired,t,theme,language:i18n.resolvedLanguage??i18n.language};
 const [open,setOpen]=useState(false),[exporting,setExporting]=useState(false),[downloading,setDownloading]=useState(false),[failed,setFailed]=useState(false),[preview,setPreview]=useState<Preview|null>(null),[progress,setProgress]=useState<{done:number;total:number}|null>(null);
 let url='';try{url=chatImageDocumentUrl(origin);}catch{/* Runtime readiness remains the origin owner. */}
 function post(message:ChatImageCommand){view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(message))}}));true;`);}
 function valid(owner:Job){return active.current&&job.current===owner&&latest.current.threadId===owner.threadId;}
 function replacePreview(next:Preview|null){const previous=previewRef.current;previewRef.current=next;setPreview(next);if(previous)releaseNativeFiles(previous.images.map(file=>file.id));}
 function reset(){
  const current=job.current;if(current&&documentId.current)post({type:'clear',documentId:documentId.current,requestId:current.id});
  current?.controller.abort();job.current=null;for(const read of imageReads.current)read.abort();imageReads.current.clear();
  replacePreview(null);exportingRef.current=false;downloadingRef.current=false;setExporting(false);setDownloading(false);setProgress(null);setFailed(false);
 }
 function sendRender(owner:Job){if(!valid(owner)||!owner.options||!documentId.current||owner.sentTo)return;owner.sentTo=documentId.current;post({type:'render',documentId:documentId.current,requestId:owner.id,options:owner.options,language:latest.current.language,theme:owner.theme});}
 async function start(){
  if(exportingRef.current||downloadingRef.current||!latest.current.threadId||!url)return;
  reset();const owner:Job={id:requestId(),threadId:latest.current.threadId,theme:latest.current.theme,controller:new AbortController()};job.current=owner;exportingRef.current=true;setExporting(true);setFailed(false);setOpen(true);Keyboard.dismiss();
  const frozen=latest.current.snapshot(),sourceTitle=latest.current.title,translate=latest.current.t;
  try{
   const stored=await fetchFullClaudeThreadMessages(owner.threadId,owner.controller.signal,latest.current.transport);if(!valid(owner))return;
   const messages=mergeCompleteHistoryWithLive(stored.messages,frozen.messages).map(message=>toExportChatMessage(message,frozen.toolChoice,translate)).filter(message=>message!==null);
   if(!messages.length)throw new Error('SHARE_EMPTY');
   owner.options={threadId:owner.threadId,title:sourceTitle,messages,pendingConfirmation:buildExportPendingConfirmation(frozen.pendingConfirmation,translate),labels:{you:translate('chat.share.you'),assistant:translate('chat.share.assistant'),footer:translate('chat.share.footer'),thinking:translate('chat.share.thinking'),truncated:translate('chat.share.truncated'),workspaceImageUnavailable:translate('chat.share.workspaceImageUnavailable')}};sendRender(owner);
  }catch(error){if(valid(owner)){if(error instanceof ClaudeThreadHydrationUnknownError&&error.httpStatus===401)latest.current.onSessionExpired?.();exportingRef.current=false;setExporting(false);setFailed(true);setOpen(true);}}
 }
 function close(){setOpen(false);if(!exportingRef.current&&!downloadingRef.current)reset();}
 useImperativeHandle(ref,()=>({open(){Keyboard.dismiss();setOpen(true);if(!exportingRef.current&&!previewRef.current&&!downloadingRef.current)void start();}}));
 useEffect(()=>{active.current=true;return()=>{active.current=false;job.current?.controller.abort();job.current=null;for(const read of imageReads.current)read.abort();if(previewRef.current)releaseNativeFiles(previewRef.current.images.map(file=>file.id));previewRef.current=null;};},[]);
 useEffect(()=>{if(observedThread.current===threadId)return;observedThread.current=threadId;reset();setOpen(false);},[threadId]);
 async function importImages(images:ChatImagePNG[],owner:Job){
  const files:Preview['images']=[];
  try{for(const image of images){const file=await importNativeSketch(image.base64,image.name,Number.MAX_SAFE_INTEGER);files.push({...file,width:image.width,height:image.height});if(!valid(owner))throw new Error('SHARE_CLOSED');}return files;}
  catch(error){releaseNativeFiles(files.map(file=>file.id));throw error;}
 }
 async function workspaceImage(message:Extract<ChatImageEvent,{type:'workspaceImage'}>,owner:Job){
  const controller=new AbortController();imageReads.current.add(controller);const source=latest.current.resources;let file:NativePickedFile|undefined,image:{type:string;base64:string}|null=null;
  try{const parsed=parseWorkspaceUri(message.uri);if(!parsed.ok||!parsed.canPreviewImage||latest.current.availability!=='enabled')throw new Error('SHARE_IMAGE_UNAVAILABLE');file=await source.acquire({threadId:owner.threadId,path:parsed.path},controller.signal);image=await runtime.readWorkspaceImage(file.id);}
  catch{/* Original renderer retains its inert unavailable-image placeholder. */}
  finally{if(file)source.release(file);imageReads.current.delete(controller);if(valid(owner)&&documentId.current===owner.sentTo)post({type:'workspaceImageResult',documentId:documentId.current,requestId:owner.id,imageId:message.imageId,image});}
 }
 async function apply(message:Extract<ChatImageEvent,{type:'preview'|'prepared'}>,owner:Job){
  if(!valid(owner)||message.documentId!==owner.sentTo)return;
  if(message.type==='preview'){
   if(!exportingRef.current)return;const files=await importImages(message.images,owner);if(!valid(owner)){releaseNativeFiles(files.map(file=>file.id));return;}
   replacePreview({images:files,fileName:message.fileName,partial:message.partial});
   if(!message.partial){exportingRef.current=false;setExporting(false);setOpen(true);}return;
  }
  if(!downloadingRef.current||message.deliveryId!==owner.deliveryId)return;
  let files:Preview['images']=[];
  try{files=await importImages(message.images,owner);const result=await runtime.exportFiles(files.map(file=>file.id)) as {completed:boolean};if(valid(owner)&&result.completed){reset();setOpen(false);}}
  catch{if(valid(owner))setFailed(true);}
  finally{releaseNativeFiles(files.map(file=>file.id));if(valid(owner)){downloadingRef.current=false;owner.deliveryId=undefined;setDownloading(false);}}
 }
 function receive(event:WebViewMessageEvent){
  if(event.nativeEvent.url!==url)return;const message=readChatImageEvent(event.nativeEvent.data);if(!message)return;
  if(message.type==='ready'){
   if(documentId.current&&documentId.current!==message.documentId)documentFailed();documentId.current=message.documentId;
   const owner=job.current;if(owner)sendRender(owner);return;
  }
  const owner=job.current;if(!owner||!valid(owner)||message.documentId!==documentId.current||message.requestId!==owner.id)return;
  if(message.type==='progress'){if(exportingRef.current)setProgress({done:message.done,total:message.total});return;}
  if(message.type==='workspaceImage'){void workspaceImage(message,owner);return;}
  if(message.type==='failed'){
   if(message.deliveryId&&message.deliveryId!==owner.deliveryId)return;
   if(message.deliveryId){downloadingRef.current=false;setDownloading(false);}else{exportingRef.current=false;setExporting(false);}setFailed(true);setOpen(true);return;
  }
  receipts.current=receipts.current.catch(()=>{}).then(()=>apply(message,owner)).catch(()=>{if(valid(owner)){exportingRef.current=false;downloadingRef.current=false;setExporting(false);setDownloading(false);setFailed(true);setOpen(true);}});
 }
 function documentFailed(){documentId.current='';const pending=Boolean(job.current);reset();if(pending){setFailed(true);setOpen(true);}}
 function download(){const owner=job.current;if(!owner||!previewRef.current||previewRef.current.partial||downloadingRef.current||!documentId.current)return;downloadingRef.current=true;setDownloading(true);setFailed(false);owner.deliveryId=requestId();post({type:'prepare',documentId:documentId.current,requestId:owner.id,deliveryId:owner.deliveryId});}
 function retry(){if(!documentId.current)view.current?.reload();void start();}
 const button=(label:string,onPress:()=>void,disabled=false)=><Pressable accessibilityRole="button" accessibilityState={{disabled}} disabled={disabled} onPress={onPress} style={[styles.button,{borderColor:colors['color-border-paper'],opacity:disabled?0.5:1}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
 const cardWidth=Math.max(1,Math.min(preview?384:344,width-32)),imageWidth=Math.max(1,cardWidth-40.4);
 return <>
  {url?<View pointerEvents="none" accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={styles.worker}><WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} onShouldStartLoadWithRequest={request=>request.url===url} onMessage={receive}
   onLoadStart={()=>{if(documentId.current)documentFailed();}} onError={documentFailed} onHttpError={documentFailed} onContentProcessDidTerminate={documentFailed}
   automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" scrollEnabled={false} setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false}/></View>:null}
  <Modal visible={open} transparent animationType="fade" onRequestClose={close} supportedOrientations={['portrait','landscape']}>
   <SafeAreaView style={styles.overlay} accessibilityViewIsModal onAccessibilityEscape={close}>
    <Pressable accessible={false} style={[StyleSheet.absoluteFill,{backgroundColor:colors['color-text-primary'],opacity:0.3}]} onPress={close}/>
    <View style={[styles.card,{width:cardWidth,maxHeight:height-64,backgroundColor:colors['color-bg-surface-solid'],borderColor:colors['color-border-paper']}]}>
    <View style={styles.header}><View style={{flex:1,minWidth:0}}><View style={{flexDirection:'row',alignItems:'center',gap:7.2}}><IconShare width={16} height={16} color={colors['color-text-primary']}/><InkLabel style={[text,{fontSize:16.8}]}>{t(preview?'chat.share.previewTitle':'chat.share.title')}</InkLabel></View><View style={{marginTop:4.8,width:41.6,height:4.48,borderRadius:99,backgroundColor:colors['color-voice-yellow'],transform:[{rotate:'-1deg'}]}}/><InkLabel numberOfLines={1} style={[muted,{fontSize:12.48,marginTop:9.6}]}>{title}</InkLabel></View><Pressable accessibilityRole="button" accessibilityLabel={t('chat.history.close')} onPress={close} style={styles.close}><IconX width={15.2} height={15.2} color={colors['color-text-muted']}/></Pressable></View>
    {preview?<ScrollView style={[styles.previewScroll,{maxHeight:Math.min(height*0.56,416),backgroundColor:colors['color-bg-app'],borderColor:colors['color-border-paper']}]} contentContainerStyle={styles.preview} accessibilityLabel={t('chat.share.previewTitle')}>
     {preview.images.map(file=><Image key={file.id} source={{uri:file.uri}} accessibilityLabel={t('chat.share.previewTitle')} style={{width:imageWidth,height:imageWidth*file.height/file.width}} resizeMode="contain"/>)}
    </ScrollView>:<View style={styles.content}>{exporting?<><ActivityIndicator color={colors['color-text-muted']}/><InkLabel style={text}>{t('chat.share.preparingPreview')}</InkLabel></>:<>
     {button(t('chat.share.copyLink')+' · '+t('chat.share.comingSoon'),()=>{},true)}
     {button(t('chat.share.exportImage'),retry,!threadId||!url)}<InkLabel style={muted}>{t('chat.share.exportImageHint')}</InkLabel>
    </>}</View>}
    {preview?<InkLabel numberOfLines={1} style={[muted,{fontSize:11.52,marginTop:8.8}]}>{preview.fileName+(!preview.partial&&preview.images.length>1?' · '+t('chat.share.partsInfo',{count:preview.images.length}):'')}</InkLabel>:null}
    {exporting&&progress?<View accessibilityRole="progressbar" accessibilityValue={{min:0,max:progress.total,now:progress.done}} style={styles.progress}><InkLabel style={muted}>{t('chat.share.rendering')+' '+Math.round(progress.done/progress.total*100)+'%'}</InkLabel></View>:null}
    {failed?<View accessibilityRole="alert" style={styles.progress}><InkLabel style={{color:colors['color-state-error']}}>{t('chat.share.exportFailed')}</InkLabel></View>:null}
    {preview?<View style={styles.footer}>{button(t(downloading?'chat.share.merging':'chat.share.download'),download,preview.partial||downloading)}{button(t('chat.share.back'),()=>replacePreview(null),downloading)}</View>:null}
    </View>
   </SafeAreaView>
  </Modal>
 </>;
});
const styles=StyleSheet.create({worker:{position:'absolute',width:1,height:1,opacity:0.01,left:0,top:0},overlay:{flex:1,padding:16,alignItems:'center',justifyContent:'center'},card:{paddingHorizontal:19.2,paddingTop:19.2,paddingBottom:17.6,borderWidth:1,borderRadius:17.6,shadowColor:'#000',shadowOpacity:0.18,shadowRadius:18,shadowOffset:{width:0,height:8}},header:{flexDirection:'row',alignItems:'flex-start',gap:8},close:{width:44,height:44,alignItems:'center',justifyContent:'center'},button:{minHeight:44,borderWidth:1,borderRadius:12,paddingHorizontal:16,paddingVertical:10,justifyContent:'center',alignItems:'center'},content:{paddingVertical:24,gap:16,justifyContent:'center'},previewScroll:{marginTop:16,borderWidth:1,borderStyle:'dashed',borderRadius:13.6,flexShrink:1},preview:{alignItems:'center'},progress:{paddingVertical:10,alignItems:'center'},footer:{paddingTop:13.6,flexDirection:'row',justifyContent:'center',gap:9.6}});
