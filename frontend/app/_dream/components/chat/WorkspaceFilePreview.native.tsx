// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Existing Workspace URI, selected Thread, availability and native byte/text/export capabilities.
// [Output] Original report/image preview and one user-initiated generic file export with cancellation/retry feedback.
// [Pos] Native Workspace reference surface; no whole-page WebView, task execution or duplicate backend file service.
import {useEffect,useMemo,useRef,useState} from 'react';
import {ActivityIndicator,Modal,Pressable,SafeAreaView,ScrollView,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {workspaceResources,type WorkspaceAvailability,type WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {parseWorkspaceUri} from './workspaceUri';
import useNativeWorkspaceFile from './useNativeWorkspaceFile.native';
import WorkspaceImage from './WorkspaceImage.native';
import ChatMarkdown from './ChatMarkdown.native';
import {IconDownload,IconX} from './Icons';
export interface NativeWorkspaceFilePreviewProps {uri:string;threadId?:string;availability:WorkspaceAvailability;resources?:WorkspaceResources;onClose:()=>void;onOpenWorkspace:(uri:string)=>void;onOpenLink?:(url:string)=>void;onAddImageMaterial?:(file:NativePickedFile)=>Promise<boolean>;}
export default function WorkspaceFilePreview(props:NativeWorkspaceFilePreviewProps){
  const parsed=useMemo(()=>parseWorkspaceUri(props.uri),[props.uri]);
  return <Modal visible animationType="slide" presentationStyle="fullScreen" onRequestClose={props.onClose} supportedOrientations={['portrait','landscape']}>{parsed.ok&&parsed.canPreviewImage?<WorkspaceImage {...props} expandedInitially embedded/>:<DocumentPreview {...props}/>}</Modal>;
}
function DocumentPreview({uri,threadId,availability,resources=workspaceResources,onClose,onOpenWorkspace,onOpenLink,onAddImageMaterial}:NativeWorkspaceFilePreviewProps){
  const {t}=useTranslation(),colors=useInkColors();
  const parsed=useMemo(()=>parseWorkspaceUri(uri),[uri]),document=parsed.ok&&/\.(md|markdown)$/i.test(parsed.fileName);
  const result=useNativeWorkspaceFile({uri,threadId,availability,resources,document,download:!document});
  const [busy,setBusy]=useState(false),[notice,setNotice]=useState<string|null>(null),mounted=useRef(true),pending=useRef(false),automatic=useRef(false);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  const file=result.state.kind==='loaded'?result.state.file:undefined;
  async function exportFile(closeAfter=false){if(!file||pending.current)return;pending.current=true;setBusy(true);setNotice(null);try{const receipt=await resources.export(file);if(mounted.current){if(closeAfter)onClose();else if(receipt.completed)setNotice(t('chat.workspaceFile.downloadStarted'));}}catch{if(mounted.current)setNotice(t('chat.workspaceFile.retryable'));}finally{pending.current=false;if(mounted.current)setBusy(false);}}
  useEffect(()=>{automatic.current=false;setNotice(null);},[uri]);
  useEffect(()=>{if(!document&&file&&!automatic.current){automatic.current=true;void exportFile(true);}},[file?.id,document]);
  return <SafeAreaView accessibilityLabel={parsed.ok?parsed.fileName:t('chat.workspaceFile.invalid')} style={[styles.fill,{backgroundColor:colors['color-bg-app']}]} onAccessibilityEscape={onClose}>
      <View style={[styles.header,{borderColor:colors['color-border-paper']}]}><InkLabel numberOfLines={1} style={{flex:1,color:colors['color-text-primary']}}>{parsed.ok?parsed.fileName:t('chat.workspaceFile.invalid')}</InkLabel>
        <Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.downloadFile')} disabled={!file||busy} onPress={()=>void exportFile(!document)} style={styles.icon}>{busy?<ActivityIndicator/>:<IconDownload width={18} height={18} color={colors['color-text-secondary']}/>}</Pressable>
        <Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.closeDocumentPreview')} onPress={onClose} style={styles.icon}><IconX width={18} height={18} color={colors['color-text-secondary']}/></Pressable>
      </View>
      <ScrollView style={styles.fill} contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
        {result.state.kind==='loading'?<ActivityIndicator accessibilityLabel={t(availability==='loading'?'chat.workspaceFile.checking':'chat.workspaceFile.loading')} color={colors['color-text-muted']}/>:null}
        {result.state.kind==='error'?<View style={styles.feedback}><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t(`chat.workspaceFile.${result.state.failure}`)}</InkLabel>{result.state.failure==='retryable'?<Pressable accessibilityRole="button" onPress={result.retry} style={styles.icon}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.workspaceFile.retry')}</InkLabel></Pressable>:null}</View>:null}
        {document&&result.state.kind==='loaded'?<ChatMarkdown text={result.state.text??''} workspaceSessionId={threadId} workspaceAvailability={availability} workspaceResources={resources} workspaceDocumentPath={result.parsed.ok?result.parsed.path:undefined} onOpenWorkspace={onOpenWorkspace} onOpenLink={onOpenLink} onAddImageMaterial={onAddImageMaterial}/>:null}
        {notice?<InkLabel accessibilityRole="alert" style={{color:colors['color-text-secondary']}}>{notice}</InkLabel>:null}
      </ScrollView>
    </SafeAreaView>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:8,paddingHorizontal:12,borderBottomWidth:1},icon:{minWidth:44,minHeight:44,alignItems:'center',justifyContent:'center'},body:{padding:16},feedback:{gap:8,paddingVertical:12}});
