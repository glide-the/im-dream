// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Root-owned sketch visibility, local origin and the native composer's upload callback.
// [Output] One persistent local sketch document and request-matched PNG upload results.
// [Pos] Root overlay for a browser-dependent editor; RN retains navigation, file upload and Chat ownership.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,BackHandler,Keyboard,Platform,Pressable,SafeAreaView,StyleSheet,View} from 'react-native';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../src/components/useInkColors.native';
import {importNativeSketch,releaseNativeFiles,type NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {MAX_UPLOAD_FILE_SIZE_BYTES} from './AIInputDock.helpers';
import {readSketchEvent,sketchDocumentUrl,type SketchDocumentResult,type SketchDocumentState} from './SketchInputDocument.protocol';

export interface SketchInputSurfaceProps {origin:string;open:boolean;disabled?:boolean;onClose:()=>void;onAdd:(file:NativePickedFile)=>Promise<boolean>;}
export default function SketchInputSurface({origin,open,disabled=false,onClose,onAdd}:SketchInputSurfaceProps) {
  const {t,i18n}=useTranslation(),colors=useInkColors(),theme=useNativeThemeMode();
  const view=useRef<WebView<object>>(null),documentId=useRef(''),revision=useRef(0),active=useRef(true),request=useRef<string|null>(null),handled=useRef(new Set<string>());
  const [ready,setReady]=useState(false),[error,setError]=useState(false);
  const latest=useRef({open,disabled,onClose,onAdd,theme,language:i18n.resolvedLanguage ?? i18n.language});latest.current={open,disabled,onClose,onAdd,theme,language:i18n.resolvedLanguage ?? i18n.language};
  let url='';try {url=sketchDocumentUrl(origin);}catch{/* The runtime supplies the only valid loopback origin. */}
  function post(message:SketchDocumentState|SketchDocumentResult) {view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(message))}}));true;`);}
  function sync() {if(documentId.current)post({type:'state',documentId:documentId.current,revision:++revision.current,open:latest.current.open,disabled:latest.current.disabled,theme:latest.current.theme,language:latest.current.language});}
  function close() {
    if(request.current)return;
    // The original Modal's saving guard also covers PNG encoding before the handoff reaches native.
    if(documentId.current)view.current?.injectJavaScript("window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));true;");
    else latest.current.onClose();
  }
  useEffect(()=>{active.current=true;return()=>{active.current=false;documentId.current='';};},[]);
  useEffect(()=>{sync();if(open)Keyboard.dismiss();},[open,disabled,ready,theme,i18n.resolvedLanguage,i18n.language]);
  useEffect(()=>{if(!open || Platform.OS!=='android')return;const subscription=BackHandler.addEventListener('hardwareBackPress',()=>{close();return true;});return()=>subscription.remove();},[open]);
  async function receive(event:WebViewMessageEvent) {
    if(event.nativeEvent.url!==url)return;const message=readSketchEvent(event.nativeEvent.data);if(!message)return;
    if(message.type==='ready'){if(documentId.current===message.documentId){sync();return;}documentId.current=message.documentId;revision.current=0;request.current=null;handled.current.clear();setReady(true);setError(false);sync();return;}
    if(message.documentId!==documentId.current)return;
    if(message.type==='close'){if(!request.current)latest.current.onClose();return;}
    if(message.type!=='add' || !latest.current.open || latest.current.disabled || request.current || handled.current.has(message.requestId))return;
    const id=message.documentId;request.current=message.requestId;handled.current.add(message.requestId);
    let accepted=false,file:NativePickedFile|undefined;
    try {
      file=await importNativeSketch(message.base64,message.name,MAX_UPLOAD_FILE_SIZE_BYTES);
      if(!active.current || documentId.current!==id){releaseNativeFiles([file.id]);return;}
      accepted=await latest.current.onAdd(file);
    }catch{if(file)releaseNativeFiles([file.id]);}
    finally {
      if(file && !accepted)releaseNativeFiles([file.id]);
      if(active.current && documentId.current===id){request.current=null;post({type:'result',documentId:id,requestId:message.requestId,accepted});}
    }
  }
  function failed(){documentId.current='';request.current=null;setReady(false);setError(true);}
  // The same WebView stays mounted while hidden, preserving imported image objects, strokes and undo history.
  return <SafeAreaView accessibilityViewIsModal={open} importantForAccessibility={open?'yes':'no-hide-descendants'} pointerEvents={open?'auto':'none'}
    style={[styles.surface,{backgroundColor:colors['color-bg-app']},!open && styles.hidden]} onAccessibilityEscape={close}>
    {url?<WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} onShouldStartLoadWithRequest={request=>request.url===url}
      onMessage={event=>void receive(event)} onLoadStart={()=>{documentId.current='';request.current=null;setReady(false);}} onError={failed} onHttpError={failed} onContentProcessDidTerminate={failed}
      automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" scrollEnabled={false} setSupportMultipleWindows={false}
      javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false} style={{backgroundColor:colors['color-bg-app']}} />:null}
    {!ready || error || !url?<View style={[StyleSheet.absoluteFill,styles.feedback,{backgroundColor:colors['color-bg-app']}]}>
      {error || !url?<Pressable accessibilityRole="button" style={styles.button} onPress={()=>{setError(false);view.current?.reload();}}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel></Pressable>:<ActivityIndicator color={colors['color-text-muted']} />}
      <Pressable accessibilityRole="button" style={styles.button} onPress={close}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.inputDock.sketch.return')}</InkLabel></Pressable>
    </View>:null}
  </SafeAreaView>;
}
const styles=StyleSheet.create({surface:{...StyleSheet.absoluteFillObject,zIndex:100},hidden:{display:'none'},feedback:{alignItems:'center',justifyContent:'center',gap:16},button:{minHeight:44,paddingHorizontal:16,justifyContent:'center'}});
