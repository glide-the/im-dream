// [Sync] 2026-10-29: expose the local editor to WebKit inspection in an RN debug build for native document failures.
// [Input] Caller-owned Markdown draft and the App-owned local Next origin.
// [Sync] 2026-10-29: synchronize the native preference into the existing document theme field without reloading its draft.
// [Output] The original Tiptap editor inside a narrow native document view, with edit acknowledgements and reload recovery.
// [Pos] Native rich-editor leaf; RN owns composer controls, permissions, submission and runtime lifecycle.
// [Sync] 2026-10-28: dispatch Skill and submit intents after draft commit; clear queued intents when the document ends.
// [Sync] 2026-10-28: shrink the document viewport with its composer while retaining the measured natural draft height.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,Pressable,StyleSheet,View} from 'react-native';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../src/components/useInkColors.native';
import {composerDocumentUrl,readComposerEvent,type ComposerDocumentState} from './MarkdownInputDocument.protocol';
import type {ComposerSkillKey} from './useComposerSkills';

export interface NativeMarkdownInputEditorProps {
  origin:string;value:string;placeholder:string;ariaLabel:string;disabled?:boolean;theme?:'light'|'dark'|'system';
  onChange:(value:string)=>void;onSubmit?:()=>void;onFocus?:()=>void;onBlur?:()=>void;
  skillMenuOpen?:boolean;onSkillKey?:(key:ComposerSkillKey)=>void;
}
export default function MarkdownInputEditor({origin,value,placeholder,ariaLabel,disabled=false,theme:requestedTheme,onChange,onSubmit,onFocus,onBlur,skillMenuOpen=false,onSkillKey}:NativeMarkdownInputEditorProps) {
  const {t}=useTranslation();
  const preferredTheme=useNativeThemeMode(),theme=requestedTheme??preferredTheme,colors=useInkColors(theme);
  const view=useRef<WebView<object>>(null);
  const [url,setUrl]=useState(''),[error,setError]=useState(false),[ready,setReady]=useState(false),[height,setHeight]=useState(72);
  const documentId=useRef(''),lastEdit=useRef(0),revision=useRef(0);
  const latest=useRef({value,placeholder,ariaLabel,disabled,theme,skillMenuOpen});latest.current={value,placeholder,ariaLabel,disabled,theme,skillMenuOpen};
  const callbacks=useRef({onSubmit,onSkillKey});callbacks.current={onSubmit,onSkillKey};
  const keys=useRef<Array<ComposerSkillKey|'submit'>>([]);
  const [keyRevision,setKeyRevision]=useState(0);
  useEffect(()=>{const pending=keys.current.splice(0);if(latest.current.disabled)return;for(const key of pending){if(key==='submit')callbacks.current.onSubmit?.();else callbacks.current.onSkillKey?.(key);}},[keyRevision]);
  function sync() {
    if(!documentId.current)return;
    const state:ComposerDocumentState={...latest.current,type:'state',documentId:documentId.current,revision:++revision.current,eventCount:lastEdit.current};
    view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(state))}}));true;`);
  }
  useEffect(()=>{try {setUrl(composerDocumentUrl(origin));setError(false);} catch {setUrl('');setError(true);}},[origin]);
  useEffect(()=>{sync();},[value,placeholder,ariaLabel,disabled,theme,skillMenuOpen,ready]);
  function receive(event:WebViewMessageEvent) {
    if(event.nativeEvent.url !== url)return;
    const message=readComposerEvent(event.nativeEvent.data);if(!message)return;
    if(message.type === 'ready') {documentId.current=message.documentId;lastEdit.current=0;revision.current=0;setReady(true);setError(false);sync();return;}
    if(message.documentId !== documentId.current)return;
    if(message.type === 'change') {if(message.eventCount <= lastEdit.current)return;lastEdit.current=message.eventCount;onChange(message.value);}
    else if(message.type === 'height')setHeight(Math.max(72,Math.min(320,Math.ceil(message.height))));
    else if(message.type === 'submit') {keys.current.push('submit');setKeyRevision(current=>current+1);}
    else if(message.type === 'keydown') {keys.current.push(message.key);setKeyRevision(current=>current+1);}
    else if(message.type === 'focus')onFocus?.();
    else if(message.type === 'blur')onBlur?.();
  }
  function failed() {documentId.current='';keys.current=[];setReady(false);setError(true);}
  return <View style={{minHeight:72,height,flexShrink:1}}>
    {/* Let the exact-URL veto handle every scheme; the package's whitelist fallback opens rejected origins through Linking. */}
    {url ? <WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} onShouldStartLoadWithRequest={request=>request.url === url}
      onMessage={receive} onLoadStart={()=>{documentId.current='';keys.current=[];setReady(false);}} onError={failed} onHttpError={failed} onContentProcessDidTerminate={failed}
      automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" keyboardDisplayRequiresUserAction scrollEnabled={false} webviewDebuggingEnabled={__DEV__}
      setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false}
      style={{backgroundColor:'transparent'}} containerStyle={{backgroundColor:'transparent'}} /> : null}
    {!ready || error ? <View style={[StyleSheet.absoluteFill,styles.feedback,{backgroundColor:colors['color-bg-paper']}]}>
      {error ? <Pressable accessibilityRole="button" onPress={()=>{if(url){setError(false);setReady(false);view.current?.reload();}}} style={styles.retry}>
        <InkLabel style={{color:colors['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel>
      </Pressable> : <ActivityIndicator color={colors['color-text-muted']} />}
    </View> : null}
  </View>;
}
const styles=StyleSheet.create({feedback:{alignItems:'center',justifyContent:'center'},retry:{minHeight:44,paddingHorizontal:16,justifyContent:'center'}});
