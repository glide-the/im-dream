// [Input] Original Mermaid source and the existing App runtime origin.
// [Output] Persistent diagram-only document, original full-screen zoom and existing system copy/PNG export.
// [Pos] Native presentation adapter; parser, SVG, toolbar and PNG generation remain in MermaidBlock.tsx.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,Modal,NativeModules,Pressable,SafeAreaView,StyleSheet,View} from 'react-native';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../src/components/useInkColors.native';
import {BackendRuntimeManager} from '../../../../src/runtime/BackendRuntimeManager';
import {importNativeSketch,releaseNativeFiles,type NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {mermaidDocumentUrl,readMermaidEvent,type MermaidDocumentReply,type MermaidDocumentState} from './MermaidDocument.protocol';
interface Props {chart:string;origin?:string;}
function Diagram({chart,origin,expanded=false,onPreview}:{chart:string;origin:string;expanded?:boolean;onPreview:(open:boolean)=>void}){
  const {t,i18n}=useTranslation(),colors=useInkColors(),theme=useNativeThemeMode();
  const view=useRef<WebView<object>>(null),identity=useRef(''),revision=useRef(0),mounted=useRef(true),handled=useRef(new Set<string>()),exporting=useRef(false);
  const [ready,setReady]=useState(false),[failed,setFailed]=useState(false),[height,setHeight]=useState(120);
  const latest=useRef({chart,expanded,theme,language:i18n.language,onPreview});latest.current={chart,expanded,theme,language:i18n.language,onPreview};
  let url='';try{url=mermaidDocumentUrl(origin);}catch{/* Runtime owns the loopback address. */}
  function post(value:MermaidDocumentState|MermaidDocumentReply){view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(value))}}));true;`);}
  function sync(){if(!identity.current)return;const {onPreview:_,...value}=latest.current;post({type:'state',documentId:identity.current,revision:++revision.current,...value});}
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;identity.current='';};},[]);
  useEffect(()=>sync(),[chart,expanded,theme,i18n.language,ready]);
  function fail(){identity.current='';setReady(false);setFailed(true);}
  async function receive(event:WebViewMessageEvent){
    if(!mounted.current||event.nativeEvent.url!==url)return;
    const message=readMermaidEvent(event.nativeEvent.data);if(!message)return;
    if(message.type==='ready'){identity.current=message.documentId;revision.current=0;handled.current.clear();setReady(true);setFailed(false);sync();return;}
    if(message.documentId!==identity.current||message.revision!==revision.current)return;
    if(message.type==='height'){setHeight(Math.max(1,Math.ceil(message.height)));return;}
    if(message.type==='preview'){latest.current.onPreview(message.open);return;}
    if(handled.current.has(message.requestId))return;handled.current.add(message.requestId);
    const valid=()=>mounted.current&&identity.current===message.documentId&&revision.current===message.revision;
    let accepted=false,file:NativePickedFile|undefined,ownsExport=false;
    try{
      if(message.type==='copy'){
        if(message.text!==`\`\`\`mermaid\n${latest.current.chart.replace(/\n+$/,'')}\n\`\`\``)throw Error('MERMAID_COPY_MISMATCH');
        await NativeModules.InkRuntime.copyText(message.text);accepted=true;
      }else{
        if(exporting.current)throw Error('MERMAID_EXPORT_PENDING');exporting.current=true;ownsExport=true;
        file=await importNativeSketch(message.base64,message.name,Number.MAX_SAFE_INTEGER);
        if(!valid())throw Error('MERMAID_DOCUMENT_CHANGED');
        await NativeModules.InkRuntime.exportFile(file.id);accepted=true;
      }
    }catch{/* Original Mermaid toolbar retains its retry action. */}
    finally{if(file)releaseNativeFiles([file.id]);if(ownsExport)exporting.current=false;if(valid())post({type:'result',documentId:message.documentId,revision:message.revision,requestId:message.requestId,accepted});}
  }
  return <View testID="native-mermaid-document" style={expanded?{flex:1,minHeight:0}:{height,minWidth:0}}>
    {url?<WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} onShouldStartLoadWithRequest={request=>request.url===url}
      onMessage={event=>void receive(event)} onLoadStart={()=>{identity.current='';setReady(false);}} onError={fail}
      onHttpError={event=>{if(event.nativeEvent.url===url)fail();}} onContentProcessDidTerminate={fail}
      automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" scrollEnabled={false} webviewDebuggingEnabled={__DEV__}
      setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false}
      style={{backgroundColor:colors['color-bg-app']}}/>:null}
    {!ready||failed||!url?<View style={[StyleSheet.absoluteFill,styles.feedback,{backgroundColor:colors['color-bg-app']}]}>{failed||!url?<Pressable accessibilityRole="button" style={styles.retry} onPress={()=>{setFailed(false);view.current?.reload();}}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel></Pressable>:<ActivityIndicator color={colors['color-text-muted']}/>}</View>:null}
  </View>;
}
export default function MermaidBlock({chart,origin}:Props){
  const {t}=useTranslation(),colors=useInkColors(),[resolved,setResolved]=useState(origin??''),[failed,setFailed]=useState(false),[expanded,setExpanded]=useState(false),[retry,setRetry]=useState(0);
  useEffect(()=>{let active=true;if(origin){setResolved(origin);setFailed(false);}else{void BackendRuntimeManager.ensureStarted().then(facts=>{if(active){setResolved(facts.localWebOrigin);setFailed(false);}}).catch(()=>{if(active)setFailed(true);});}return()=>{active=false;};},[origin,retry]);
  return <View style={{minWidth:0,marginBottom:13.68}}>
    {resolved?<Diagram chart={chart} origin={resolved} onPreview={setExpanded}/>:failed?<Pressable accessibilityRole="button" style={styles.retry} onPress={()=>setRetry(value=>value+1)}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel></Pressable>:<ActivityIndicator/>}
    <Modal visible={expanded} presentationStyle="fullScreen" onRequestClose={()=>setExpanded(false)}>
      <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}>
        <Pressable accessibilityRole="button" accessibilityLabel={t('chat.mediaPreview.close')} style={styles.retry} onPress={()=>setExpanded(false)}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.mediaPreview.close')}</InkLabel></Pressable>
        {expanded&&resolved?<Diagram chart={chart} origin={resolved} expanded onPreview={setExpanded}/>:null}
      </SafeAreaView>
    </Modal>
  </View>;
}
const styles=StyleSheet.create({feedback:{alignItems:'center',justifyContent:'center'},retry:{minHeight:44,paddingHorizontal:12,justifyContent:'center'}});
