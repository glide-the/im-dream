// [Input] App-owned local Next origin, original display preferences and native navigation callbacks.
// [Output] Native Writing frame containing the original DOM editor document with normal Cookie authentication.
// [Pos] More destination; editor instance persists while hidden, original engine owns autosave and Writing tasks.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,Linking,Pressable,StyleSheet,View} from 'react-native';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../src/components/useInkColors.native';
import {getShowEnergyBar} from '../../../src/platform/interfacePreferences.native';
import {readWritingEvent,writingDocumentUrl,type WritingDocumentState} from './Editor/WritingDocument.protocol';
type Props={origin:string;active:boolean;onBack:()=>void;onOpenThread:(id:string)=>void;onPrepareChat:(input:string)=>void;onOpenResources:()=>void;onSessionExpired:()=>void};
export default function WritingView({origin,active,onBack,onOpenThread,onPrepareChat,onOpenResources,onSessionExpired}:Props){
 const {t,i18n}=useTranslation(),c=useInkColors(),theme=useNativeThemeMode(),view=useRef<WebView<object>>(null),id=useRef(''),revision=useRef(0);
 const [ready,setReady]=useState(false),[error,setError]=useState(false);
 const url=writingDocumentUrl(origin),latest=useRef({active,theme,language:i18n.language.startsWith('zh')?'zh' as const:'en' as const,showEnergyBar:getShowEnergyBar()});latest.current={active,theme,language:i18n.language.startsWith('zh')?'zh':'en',showEnergyBar:getShowEnergyBar()};
 const callbacks=useRef({onOpenThread,onPrepareChat,onOpenResources,onSessionExpired});callbacks.current={onOpenThread,onPrepareChat,onOpenResources,onSessionExpired};
 function sync(){if(!id.current)return;const state:WritingDocumentState={...latest.current,type:'state',documentId:id.current,revision:++revision.current};view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(state))}}));true;`);}
 useEffect(()=>sync(),[active,theme,i18n.language,latest.current.showEnergyBar,ready]);
 function failed(){id.current='';setReady(false);setError(true);}
 function receive(event:WebViewMessageEvent){if(event.nativeEvent.url!==url)return;const message=readWritingEvent(event.nativeEvent.data);if(!message)return;if(message.type==='ready'){id.current=message.documentId;revision.current=0;setReady(true);setError(false);sync();return;}if(message.documentId!==id.current)return;if(message.type==='session-expired'){callbacks.current.onSessionExpired();return;}if(!latest.current.active)return;if(message.type==='open-thread')callbacks.current.onOpenThread(message.threadId);else if(message.type==='prepare-chat')callbacks.current.onPrepareChat(message.input);else if(message.type==='resources')callbacks.current.onOpenResources();}
 return <View style={s.fill}><View style={s.header}><Pressable accessibilityRole="button" onPress={onBack} style={s.back}><InkLabel style={{color:c['color-text-primary']}}>{`← ${t('nav.more')}`}</InkLabel></Pressable><InkLabel accessibilityRole="header" style={{fontSize:22,color:c['color-text-primary']}}>{t('nav.writing')}</InkLabel></View>
  <View style={s.fill}><WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} sharedCookiesEnabled thirdPartyCookiesEnabled={false}
   onShouldStartLoadWithRequest={request=>{if(request.url===url)return true;if(request.navigationType==='click'&&/^https?:\/\//.test(request.url))void Linking.openURL(request.url).catch(()=>setError(true));return false;}}
   onMessage={receive} onLoadStart={()=>{id.current='';setReady(false);}} onError={failed} onHttpError={failed} onContentProcessDidTerminate={failed}
   automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" keyboardDisplayRequiresUserAction scrollEnabled={false} webviewDebuggingEnabled={__DEV__}
   setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false} style={{backgroundColor:c['color-bg-app']}}/>
   {!ready||error?<View style={[StyleSheet.absoluteFill,s.feedback,{backgroundColor:c['color-bg-app']}]}>{error?<Pressable accessibilityRole="button" onPress={()=>{setError(false);view.current?.reload();}} style={s.back}><InkLabel style={{color:c['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel></Pressable>:<ActivityIndicator color={c['color-text-primary']}/>}</View>:null}
  </View>
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:16,paddingVertical:8},back:{minHeight:44,minWidth:44,padding:10,justifyContent:'center'},feedback:{alignItems:'center',justifyContent:'center'}});
