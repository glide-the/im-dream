// [Sync] 2026-11-03: publish only account-owned dated mood and chooser occupation to the idle presentation.
// [Sync] 2026-11-01: open Writing document links through the shared native system-browser action.
// [Sync] 2026-11-01: supply cancellable Session-bound save/context preparation to native Writing side conversations.
// [Sync] 2026-11-01: render the original chooser value in the native Writing header; open intent carries no business write.
// [Sync] 2026-10-30: carry the original Editor jump target to the existing Writing document without remounting its editor.
// [Input] App-owned local Next origin, original display preferences and native navigation callbacks.
// [Output] Native Writing frame containing the original DOM editor document with normal Cookie authentication.
// [Pos] More destination; editor instance persists while hidden, original engine owns autosave and Writing tasks.
import {openExternalLink} from '../../../src/platform/externalLinks.native';
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,Keyboard,Pressable,StyleSheet,View} from 'react-native';
import Svg,{Circle,Line,Path} from 'react-native-svg';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../src/components/useInkColors.native';
import {getShowEnergyBar} from '../../../src/platform/interfacePreferences.native';
import {readWritingEvent,writingDocumentUrl,WritingContextRequests,type WritingDocumentState,type WritingChooserView,type WritingContextRequest,type WritingThreadContext} from './Editor/WritingDocument.protocol';
import type {EditorJumpToCellDetail} from './chat/editorWriteTools';
import {idleMood} from '../../../src/runtime/idleMood';
// [Sync] 2026-11-12: execute original note clipboard/file actions with exact document ownership.
import {performNoteShare} from '../../../src/platform/noteShare.native';
import type {WritingShareResult} from './Editor/WritingShare.protocol';
type Props={ownerId?:string;onIdleBlocked?:(blocked:boolean)=>void;onEditorJumpDispatched?:(nonce:number)=>void;editorJump?:{nonce:number;detail:EditorJumpToCellDetail};origin:string;active:boolean;onBack:()=>void;onOpenThread:(id:string,context?:WritingThreadContext)=>void;onPrepareChat:(input:string)=>void;onOpenResources:()=>void;onSessionExpired:()=>void};
export default function WritingView({ownerId,onIdleBlocked,onEditorJumpDispatched,editorJump,origin,active,onBack,onOpenThread,onPrepareChat,onOpenResources,onSessionExpired}:Props){
 const {t,i18n}=useTranslation(),c=useInkColors(),theme=useNativeThemeMode(),view=useRef<WebView<object>>(null),id=useRef(''),revision=useRef(0);
 const chooserRevision=useRef(0),openChooserNonce=useRef(0);
 const contextRequest=useRef<WritingContextRequest|undefined>(undefined);
 const shareResult=useRef<WritingShareResult|undefined>(undefined),shareBusy=useRef(false);
 const [contextRequests]=useState(()=>new WritingContextRequests(request=>{contextRequest.current=request;sync();}));
 const [chooser,setChooser]=useState<WritingChooserView|null>(null);
 const [ready,setReady]=useState(false),[error,setError]=useState(false);
 useEffect(()=>{onIdleBlocked?.(active&&Boolean(chooser?.expanded));return()=>onIdleBlocked?.(false);},[active,chooser?.expanded,onIdleBlocked]);
 const url=writingDocumentUrl(origin),latest=useRef({active,theme,language:i18n.language.startsWith('zh')?'zh' as const:'en' as const,showEnergyBar:getShowEnergyBar(),editorJump});latest.current={active,theme,language:i18n.language.startsWith('zh')?'zh':'en',showEnergyBar:getShowEnergyBar(),editorJump};
 const callbacks=useRef({onOpenThread,onPrepareChat,onOpenResources,onSessionExpired,onEditorJumpDispatched});callbacks.current={onOpenThread,onPrepareChat,onOpenResources,onSessionExpired,onEditorJumpDispatched};
 function sync(){if(!id.current)return;const state:WritingDocumentState={...latest.current,type:'state',documentId:id.current,revision:++revision.current,...(shareResult.current?{shareResult:shareResult.current}:{}),...(openChooserNonce.current?{openChooserNonce:openChooserNonce.current}:{}),...(contextRequest.current?{contextRequest:contextRequest.current}:{})};view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(state))}}));true;`);}
 useEffect(()=>sync(),[active,theme,i18n.language,latest.current.showEnergyBar,editorJump,ready]);
 useEffect(()=>{if(!active)contextRequests.cancel();},[active,contextRequests]);
 useEffect(()=>()=>contextRequests.attach(''),[contextRequests]);
 function resetDocument(){id.current='';shareResult.current=undefined;contextRequests.attach('');chooserRevision.current=0;openChooserNonce.current=0;setChooser(null);setReady(false);}
 function failed(){resetDocument();setError(true);}
 function receive(event:WebViewMessageEvent){
  if(event.nativeEvent.url!==url)return;
  const message=readWritingEvent(event.nativeEvent.data);if(!message)return;
  if(message.type==='ready'){id.current=message.documentId;revision.current=0;contextRequests.attach(message.documentId);chooserRevision.current=0;openChooserNonce.current=0;setChooser(null);setReady(true);setError(false);sync();return;}
  if(message.documentId!==id.current)return;
  if(message.type==='session-expired'){contextRequests.cancel();setChooser(null);callbacks.current.onSessionExpired();return;}
  if(message.type==='chat-context'||message.type==='chat-context-error'){contextRequests.receive(message);return;}
  if(message.type==='chooser-view'){if(message.revision>chooserRevision.current){chooserRevision.current=message.revision;setChooser(message);if(!message.loading&&latest.current.active)idleMood.observe(ownerId,message.selectedStateId,message.createdAt);}return;}
  if(message.type==='editor-jump-dispatched'){if(message.nonce===latest.current.editorJump?.nonce)callbacks.current.onEditorJumpDispatched?.(message.nonce);return;}
  if(!latest.current.active)return;
  if(message.type==='note-share'){
   if(shareBusy.current)return;
   const documentId=id.current;shareBusy.current=true;
   void performNoteShare(message.request,()=>id.current===documentId&&latest.current.active).then(result=>{if(id.current===documentId){shareResult.current=result;sync();}}).finally(()=>{shareBusy.current=false;});return;
  }
  if(message.type==='open-thread'){
   const documentId=id.current,sessionId=message.editorSessionId;
   callbacks.current.onOpenThread(message.threadId,sessionId?{sessionId,prepareEditorState:signal=>latest.current.active?contextRequests.prepare(documentId,sessionId,signal):Promise.reject(new Error('WRITING_CONTEXT_INACTIVE'))}:undefined);
  }else if(message.type==='prepare-chat')callbacks.current.onPrepareChat(message.input);
  else if(message.type==='resources')callbacks.current.onOpenResources();
 }
 const disabled=!active||!ready||error||!chooser||chooser.loading;
 const chooserLabel=chooser?.name||(i18n.language.startsWith('zh')?'选择心情':'Choose emotion');
 const label=chooser?.loading||!chooser?(i18n.language.startsWith('zh')?'正在读取…':'Loading…'):chooserLabel;
 return <View style={s.fill}><View style={s.header}>
  <Pressable accessibilityRole="button" onPress={onBack} style={s.back}><InkLabel style={{color:c['color-text-primary']}}>{`← ${t('nav.more')}`}</InkLabel></Pressable>
  <InkLabel accessibilityRole="header" numberOfLines={1} style={{fontSize:22,color:c['color-text-primary'],flex:1}}>{t('nav.writing')}</InkLabel>
  <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled,expanded:chooser?.expanded??false,busy:!chooser||chooser.loading}} disabled={disabled} style={s.chooser}
   onPress={()=>{if(disabled)return;Keyboard.dismiss();openChooserNonce.current++;sync();}}>
   {chooser?.selectedStateId?<ChooserIcon id={chooser.selectedStateId}/>:null}
   <InkLabel numberOfLines={1} style={{fontSize:14,color:c['color-text-primary'],flexShrink:1}}>{label}</InkLabel>
  </Pressable>
 </View>
  <View style={s.fill}><WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} sharedCookiesEnabled thirdPartyCookiesEnabled={false}
   onShouldStartLoadWithRequest={request=>{if(request.url===url)return true;if(request.navigationType==='click'&&/^https?:\/\//.test(request.url))void openExternalLink(request.url).catch(()=>setError(true));return false;}}
   onMessage={receive} onLoadStart={resetDocument} onError={failed} onHttpError={failed} onContentProcessDidTerminate={failed}
   automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" keyboardDisplayRequiresUserAction scrollEnabled={false} webviewDebuggingEnabled={__DEV__}
   setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false} style={{backgroundColor:c['color-bg-app']}}/>
   {!ready||error?<View style={[StyleSheet.absoluteFill,s.feedback,{backgroundColor:c['color-bg-app']}]}>{error?<Pressable accessibilityRole="button" onPress={()=>{setError(false);view.current?.reload();}} style={s.back}><InkLabel style={{color:c['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel></Pressable>:<ActivityIndicator color={c['color-text-primary']}/>}</View>:null}
  </View>
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:16,paddingVertical:8},chooser:{flexDirection:'row',alignItems:'center',gap:6,minHeight:44,minWidth:44,maxWidth:'45%',paddingHorizontal:8},back:{minHeight:44,minWidth:44,padding:10,justifyContent:'center'},feedback:{alignItems:'center',justifyContent:'center'}});

// Original StateChooser icon geometry, rendered through the existing native SVG dependency.
function ChooserIcon({id}:{id:string}){
 const key=id.toLowerCase(),color=key==='happy'?'#FFD93D':key==='ok'?'#95D5B2':key==='unhappy'?'#A8DADC':'#999';
 return <Svg width={24} height={24} viewBox="0 0 100 100" accessible={false}>
  <Circle cx={50} cy={50} r={key==='happy'||key==='ok'||key==='unhappy'?40:35} fill="none" stroke={color} strokeWidth={key==='happy'||key==='ok'||key==='unhappy'?6:4}/>
  {key==='happy'||key==='ok'||key==='unhappy'?<><Circle cx={38} cy={40} r={4} fill={color}/><Circle cx={62} cy={40} r={4} fill={color}/>
   {key==='ok'?<Line x1={35} y1={60} x2={65} y2={60} stroke={color} strokeWidth={6} strokeLinecap="round"/>:<Path d={key==='happy'?'M 35 60 Q 50 75 65 60':'M 35 65 Q 50 50 65 65'} fill="none" stroke={color} strokeWidth={6} strokeLinecap="round"/>}</>:null}
 </Svg>;
}
