// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-28: apply the original attachment-size policy to explicit Workspace material copies as well as picker/sketch input.
// [Input] Original send/Stop/context callbacks, effective permissions and the App-owned local origin.
// [Output] Native composer card with original Tiptap document, native file upload and original action controls.
// [Pos] Native AIInputDock counterpart; ordinary Web DOM and service-side business owners remain unchanged.
// [Sync] 2026-10-28: pass actual Deck/Thread/workspace context into shared Skill discovery and preserve draft-only menu selection.
// [Sync] 2026-10-28: expose the existing attachment uploader to the root-owned sketch overlay through a component ref.
// [Sync] 2026-10-28: let the editor shrink inside the current scene viewport while retaining native action controls.
import {forwardRef,useEffect,useImperativeHandle,useRef,useState,type ForwardedRef,type ReactNode} from 'react';
import {ActivityIndicator,Image,Pressable,StyleSheet,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import type {ToolChoice} from '../../lib/chat-schema';
import type {UploadedFile} from './AIInputDock.helpers';
import {formatFileSize,shouldShowUploadHint,MAX_UPLOAD_FILE_SIZE_BYTES} from './AIInputDock.helpers';
import useComposerDraft from './useComposerDraft';
import useFileAttachments from './useFileAttachments.native';
import MarkdownInputEditor from './MarkdownInputEditor';
import AIInputDockControls from './AIInputDockControls.native';
import {IconFile,IconX} from './Icons';
import useComposerSkills from './useComposerSkills';
import ComposerSkillMenu from './ComposerSkillMenu.native';
import {clientFetch} from '../../../../src/platform/transport';
import type {ContextUsageSnapshot} from '../../lib/context-compaction';
import {releaseNativeFiles,type NativePickedFile} from '../../../../src/platform/fileUpload.native';
export interface NativeAIInputDockHandle {addFile:(file:NativePickedFile)=>Promise<boolean>;}
export interface NativeAIInputDockProps {
  origin:string;onSendMessage:(message:string,files?:UploadedFile[],toolChoice?:ToolChoice)=>void|Promise<void>;
  fullAccessEnabled:boolean;onOpenSketch:()=>void;contextControl?:ReactNode;
  disabled?:boolean;loading?:boolean;onStop?:()=>void|Promise<void>;stopPending?:boolean;loadingLabel?:string;
  defaultToolChoice?:ToolChoice;workspaceSessionId?:string;prefill?:string;prefillNonce?:number;placeholder?:string;
  deckId?:string;threadId?:string;workspaceEnabled?:boolean;contextUsage?:ContextUsageSnapshot;
}
function AIInputDock({origin,onSendMessage,fullAccessEnabled,onOpenSketch,contextControl,disabled=false,loading=false,onStop,stopPending=false,loadingLabel,defaultToolChoice='auto',workspaceSessionId,prefill,prefillNonce,placeholder='Ask Ink & Memory…',deckId,threadId,workspaceEnabled,contextUsage}:NativeAIInputDockProps,ref:ForwardedRef<NativeAIInputDockHandle>) {
  const {t}=useTranslation();const colors=useInkColors();
  const narrow=useWindowDimensions().width<=767;
  const uploads=useFileAttachments(workspaceSessionId);
  const [notice,setNotice]=useState<string|null>(null);
  const [focused,setFocused]=useState(false);
  const draft=useComposerDraft({onSendMessage,disabled,loading,onStop,fullAccessEnabled,defaultToolChoice,initialDraft:prefill,onUploadBlocked:()=>setNotice(t('chat.inputDock.waitForUpload')),releasePreview:uploads.releasePreview});
  useImperativeHandle(ref,()=>({addFile:async file=>{if(disabled){releaseNativeFiles([file.id]);return false;}if(file.size>MAX_UPLOAD_FILE_SIZE_BYTES){setNotice(t('chat.inputDock.fileTooLarge',{name:file.name,max:formatFileSize(MAX_UPLOAD_FILE_SIZE_BYTES)}));releaseNativeFiles([file.id]);return false;}return (await uploads.addFiles([file],draft.setUploadedFiles))[0]===true;}}));
  const skills=useComposerSkills({query:draft.query,setQuery:draft.setQuery,focused,deckId,threadId,workspaceEnabled,transport:clientFetch});
  const nonce=useRef<number|undefined>(undefined);
  useEffect(()=>{if(prefillNonce===undefined || prefillNonce===nonce.current)return;nonce.current=prefillNonce;draft.setQuery(prefill ?? '');skills.resetDismissal();},[prefill,prefillNonce]);
  return <View style={[styles.card,{paddingVertical:narrow?11.2:13.6,paddingHorizontal:narrow?12:16,borderRadius:narrow?16:20,backgroundColor:colors['color-bg-paper'],borderColor:colors[focused?'color-border-focus':'color-border-paper'],shadowColor:colors['color-shadow-soft'],shadowOpacity:1,shadowRadius:4,shadowOffset:{width:0,height:2}}]}>
    {notice || uploads.error ? <InkLabel accessibilityRole="alert" style={[styles.error,{color:colors['color-state-error']}]}>{notice || uploads.error || ''}</InkLabel> : null}
    {draft.uploadedFiles.length ? <View style={styles.files}>{draft.uploadedFiles.map(file=><View key={file.id} style={[styles.file,{backgroundColor:colors['color-bg-app'],borderColor:colors['color-border-paper']}]}>
      {file.mimeType.startsWith('image/') && file.previewUrl ? <Image source={{uri:file.previewUrl}} accessibilityLabel={file.name} style={styles.image} /> : <View style={styles.fileText}>
        <IconFile width={22.4} height={22.4} color={colors['color-text-muted']} />
        <InkLabel numberOfLines={1} style={{fontSize:10.88,color:colors['color-text-secondary']}}>{file.name}</InkLabel>
        <InkLabel style={{fontSize:9.6,color:colors['color-text-muted']}}>{`${file.name.split('.').pop()?.toUpperCase() || 'FILE'} · ${formatFileSize(file.size)}`}</InkLabel>
      </View>}
      {file.isUploading ? <View style={[StyleSheet.absoluteFill,styles.progress,{backgroundColor:colors['color-bg-surface']}]}><ActivityIndicator size="small" color={colors['color-action-link']} /><InkLabel style={{fontSize:9.6,color:colors['color-text-muted']}}>{`${Math.round(file.progress ?? 0)}%`}</InkLabel></View> : null}
      <Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputDock.deleteFileAria',{name:file.name})} disabled={file.isUploading} accessibilityState={{disabled:file.isUploading}} onPress={()=>uploads.deleteFile(file.id,draft.setUploadedFiles)} style={styles.delete}>
        <View style={[styles.deleteCircle,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface-solid']}]}><IconX width={13.6} height={13.6} color={colors['color-state-danger']} /></View>
      </Pressable>
    </View>)}</View> : null}
    <View style={styles.hints}>{shouldShowUploadHint(draft.query,focused)?<InkLabel style={{fontSize:11.68,color:colors['color-text-muted']}}>{t('chat.inputDock.uploadHint')}</InkLabel>:null}<InkLabel style={{fontSize:11.68,color:colors['color-text-muted']}}>{t('chat.inputDock.sendShortcut')}</InkLabel></View>
    <MarkdownInputEditor origin={origin} value={draft.query} onChange={draft.setQuery} onSubmit={()=>{if(!skills.keyDown('Enter'))draft.handleSend();}} skillMenuOpen={skills.matches.length>0} onSkillKey={key=>{if(!skills.keyDown(key) && key==='Enter')draft.handleSend();}} onFocus={()=>setFocused(true)} onBlur={()=>setFocused(false)} disabled={disabled} placeholder={placeholder} ariaLabel={t('chat.inputDock.inputAria')} />
    <ComposerSkillMenu commands={skills.matches} activeIndex={skills.activeIndex} onSelect={skills.select} contextUsage={contextUsage} />
    <AIInputDockControls draft={draft} disabled={disabled} loading={loading} onStop={onStop} stopPending={stopPending} loadingLabel={loadingLabel} fullAccessEnabled={fullAccessEnabled} contextControl={contextControl}
      onChooseFiles={()=>{setNotice(null);void uploads.chooseFiles(draft.setUploadedFiles);}} onOpenSketch={onOpenSketch} />
  </View>;
}
export default forwardRef(AIInputDock);
const styles=StyleSheet.create({card:{flexShrink:1,minHeight:0,borderWidth:1,borderRadius:16,padding:12},error:{marginBottom:12,fontSize:13.12},files:{flexDirection:'row',flexWrap:'wrap',gap:8,marginBottom:12},file:{borderWidth:1,borderRadius:10.4,overflow:'hidden'},fileText:{width:112,height:80,padding:8,justifyContent:'center',alignItems:'center',gap:4},image:{width:80,height:80},progress:{justifyContent:'center',alignItems:'center',gap:4},delete:{position:'absolute',right:0,top:0,width:44,height:44,alignItems:'center',justifyContent:'center'},deleteCircle:{width:24,height:24,borderRadius:999,borderWidth:1,alignItems:'center',justifyContent:'center'},hints:{gap:6.4,marginBottom:6.4}});
