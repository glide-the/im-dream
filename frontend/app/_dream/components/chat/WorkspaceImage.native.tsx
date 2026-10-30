// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Strict Workspace image URI, selected Thread, original availability and native resource leases.
// [Output] Original image card/full-size preview, system download and explicit add-material ownership transfer.
// [Pos] Native counterpart of WorkspaceImage; bytes stay native, existing composer owns accepted attachments.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,Image,Modal,Pressable,SafeAreaView,ScrollView,StyleSheet,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {workspaceResources,type WorkspaceAvailability,type WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
import useNativeWorkspaceFile from './useNativeWorkspaceFile.native';
import {IconDownload,IconMaximize,IconX} from './Icons';
const imageTypes=new Set(['image/gif','image/jpeg','image/png','image/webp']);
export interface NativeWorkspaceImageProps {uri:string;threadId?:string;availability:WorkspaceAvailability;alt?:string;resources?:WorkspaceResources;expandedInitially?:boolean;embedded?:boolean;onClose?:()=>void;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;}
export default function WorkspaceImage({uri,threadId,availability,alt,resources=workspaceResources,expandedInitially=false,embedded=false,onClose,onAddImageMaterial}:NativeWorkspaceImageProps){
  const {t}=useTranslation(),colors=useInkColors(),{width,height}=useWindowDimensions();
  const result=useNativeWorkspaceFile({uri,threadId,availability,resources});
  const [expanded,setExpanded]=useState(expandedInitially),[ratio,setRatio]=useState(1),[imageFailed,setImageFailed]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState<string|null>(null);
  const mounted=useRef(true),pending=useRef(false);useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const file=result.state.kind==='loaded'?result.state.file:undefined;
  useEffect(()=>setImageFailed(false),[file?.id]);
  useEffect(()=>setNotice(null),[uri]);
  const failure=result.state.kind==='error'?result.state.failure:file&&!imageTypes.has(file.type)?'unsupported':imageFailed?'retryable':undefined;
  const title=alt||(result.parsed.ok?result.parsed.fileName:t('chat.workspaceFile.imageAlt'));
  const close=()=>{setExpanded(false);onClose?.();};
  async function exportImage(){if(!file||pending.current)return;pending.current=true;setBusy(true);setNotice(null);try{const receipt=await resources.export(file);if(mounted.current&&receipt.completed)setNotice(t('chat.workspaceFile.downloadStarted'));}catch{if(mounted.current)setNotice(t('chat.workspaceFile.retryable'));}finally{pending.current=false;if(mounted.current)setBusy(false);}}
  async function add(){if(!file||pending.current||!onAddImageMaterial)return;pending.current=true;setBusy(true);setNotice(null);let copy:NativePickedFile|undefined,transferred=false;
    try{copy=await resources.copy(file);if(!mounted.current)return;transferred=true;if(!await onAddImageMaterial(copy))throw new Error('MATERIAL_REJECTED');if(mounted.current){setExpanded(false);onClose?.();}}
    catch{if(mounted.current)setNotice(t('chat.inputDock.uploadFailed'));}finally{if(copy&&!transferred)resources.release(copy);pending.current=false;if(mounted.current)setBusy(false);}}
  const feedback=failure?<View style={styles.feedback}><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t(`chat.workspaceFile.${failure}`)}</InkLabel>{failure==='retryable'?<Pressable accessibilityRole="button" onPress={result.retry} style={styles.button}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.workspaceFile.retry')}</InkLabel></Pressable>:null}</View>:!file?<View style={styles.feedback}><ActivityIndicator color={colors['color-text-muted']} accessibilityLabel={t(availability==='loading'?'chat.workspaceFile.checking':'chat.workspaceFile.loadingImage')}/></View>:null;
  const picture=(full:boolean)=><Image accessibilityLabel={title} source={{uri:file!.uri}} resizeMode="contain" onLoad={({nativeEvent})=>{const size=nativeEvent.source;if(size.width>0&&size.height>0)setRatio(size.width/size.height);}} onError={()=>setImageFailed(true)} style={full?{width:Math.max(1,width-32),height:Math.max(1,height-150)}:{width:Math.min(448,width-32),maxWidth:'100%',aspectRatio:ratio,maxHeight:height*.68}}/>;
  const surface=(<SafeAreaView accessibilityLabel={t('chat.workspaceFile.previewTitle',{name:title})} style={[styles.fill,{backgroundColor:colors['color-bg-app']}]} onAccessibilityEscape={close}>
        <View style={[styles.header,{borderColor:colors['color-border-paper']}]}><InkLabel numberOfLines={1} style={{flex:1,color:colors['color-text-primary']}}>{t('chat.workspaceFile.previewTitle',{name:title})}</InkLabel>
          <Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.downloadImage')} disabled={!file||busy} onPress={()=>void exportImage()} style={styles.icon}>{busy?<ActivityIndicator/>:<IconDownload width={18} height={18} color={colors['color-text-secondary']}/>}</Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.closePreview')} onPress={close} style={styles.icon}><IconX width={18} height={18} color={colors['color-text-secondary']}/></Pressable>
        </View>
        {feedback}
        {file&&!failure?<ScrollView style={styles.fill} contentContainerStyle={styles.imageBody} minimumZoomScale={1} maximumZoomScale={4} centerContent>{picture(true)}</ScrollView>:null}
        {notice?<InkLabel accessibilityLiveRegion="polite" style={[styles.feedback,{color:colors['color-text-secondary']}]}>{notice}</InkLabel>:null}
        {file&&!failure&&onAddImageMaterial?<Pressable accessibilityRole="button" disabled={busy} onPress={()=>void add()} style={[styles.button,{borderColor:colors['color-border-paper'],borderWidth:1,margin:12}]}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.workspaceFile.addToMessage')}</InkLabel></Pressable>:null}
      </SafeAreaView>);
  if(embedded)return surface;
  return <View style={styles.card}>
    {!expandedInitially?<>
      {feedback}
      {file&&!failure?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.previewAction',{name:title})} onPress={()=>setExpanded(true)} style={[styles.frame,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>{picture(false)}<View style={styles.badge}><IconMaximize width={16} height={16} color={colors['color-text-primary']}/><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.workspaceFile.previewBadge')}</InkLabel></View></Pressable>:null}
    </>:null}
    <Modal visible={expanded} animationType="fade" presentationStyle="fullScreen" onRequestClose={close} supportedOrientations={['portrait','landscape']}>
      {surface}

    </Modal>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},card:{minWidth:0,marginVertical:8},frame:{alignSelf:'flex-start',maxWidth:'100%',borderWidth:1,borderRadius:14,overflow:'hidden'},badge:{flexDirection:'row',gap:6,padding:10,alignItems:'center'},feedback:{padding:12,gap:8},button:{minHeight:44,padding:10,alignItems:'center',justifyContent:'center',borderRadius:12},header:{flexDirection:'row',alignItems:'center',gap:8,paddingHorizontal:12,borderBottomWidth:1},icon:{width:44,height:44,alignItems:'center',justifyContent:'center'},imageBody:{flexGrow:1,justifyContent:'center',alignItems:'center'}});
