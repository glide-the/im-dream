// [Sync] 2026-10-31: close the scoped original MCP session before Native navigation removes its WebView.
// [Input] One selected Thread/tool call, original persisted part and App-owned callbacks.
// [Output] Persistent local MCP App/editor document, measured height and identity-matched domain events.
// [Pos] Native DOM leaf; original Host owns MCP/approval HTTP and RN owns Chat submission/navigation.
import {useEffect,useRef,useState} from 'react';
import {ActivityIndicator,Pressable,StyleSheet,View} from 'react-native';
import {WebView,type WebViewMessageEvent} from 'react-native-webview';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../src/components/useInkColors.native';
import {getEditorWriteOutput,readToolInput} from './toolPartPresentation';
import {isEditorWriteTool,resolveEditorWriteJumpTarget,type EditorJumpToCellDetail} from './editorWriteTools';
import {resolveToolName} from './toolConfirmation';
import type {ChatUserMessage} from './chatUserMessageIngress';
import {MCP_APPS_HOST_MANIFEST} from './mcp-apps/host-policy';
import {readToolResultEvent,toolResultDocumentUrl,toolResultNavigationAllowed,type ToolPart,type ToolResultReply,type ToolResultState,type ToolResultDispose} from './ToolResultDocument.protocol';
const documents=new Set<{owner?:object;close:()=>Promise<void>}>();
export async function closeToolResultDocuments(owner?:object):Promise<void>{
  await Promise.allSettled([...documents].filter(document=>owner===undefined||document.owner===owner).map(document=>document.close()));
}
export interface ToolResultSurfaceProps {
  documentOwner?:object;origin:string;threadId:string;part:ToolPart;presentation:'app-only'|'editor';editorCompleted?:boolean;active:boolean;settledToolCallIds?:ReadonlySet<string>;
  sendUserMessage:(message:ChatUserMessage)=>Promise<void>;
  addToolResult:(value:{tool:string;toolCallId:string;output:unknown})=>void;
  onConfirmationSettled:(toolCallId:string)=>void;onSessionExpired:()=>void;
  onEditorWriteConfirmed?:(toolCallId:string)=>void;onEditorJump?:(detail:EditorJumpToCellDetail)=>void;
}
export default function ToolResultSurface(props:ToolResultSurfaceProps){
  const {t,i18n}=useTranslation(),colors=useInkColors(),theme=useNativeThemeMode(),view=useRef<WebView<object>>(null);
  const latest=useRef(props);latest.current=props;
  const id=useRef(''),revision=useRef(0),mounted=useRef(true),handled=useRef(new Set<string>());
  const disposal=useRef<{requestId:string;promise:Promise<void>;resolve:()=>void;timer:ReturnType<typeof setTimeout>}|null>(null);
  const [ready,setReady]=useState(false),[error,setError]=useState(false),[height,setHeight]=useState(64);
  let url='';try{url=toolResultDocumentUrl(props.origin);}catch{/* The App runtime owns the loopback origin. */}
  function post(value:ToolResultState|ToolResultReply|ToolResultDispose){view.current?.injectJavaScript(`window.dispatchEvent(new MessageEvent('message',{data:${JSON.stringify(JSON.stringify(value))}}));true;`);}
  function sync(){const current=latest.current;if(!id.current||disposal.current)return;post({type:'state',documentId:id.current,revision:++revision.current,threadId:current.threadId,toolCallId:current.part.toolCallId,part:current.part,presentation:current.presentation,editorCompleted:current.editorCompleted??false,settledToolCallIds:[...(current.settledToolCallIds??[])],active:current.active,theme,language:i18n.language});}
  function finishDisposal(){const pending=disposal.current;if(!pending)return;clearTimeout(pending.timer);disposal.current=null;pending.resolve();}
  function closeDocument():Promise<void>{
    if(disposal.current)return disposal.current.promise;
    if(!id.current||!mounted.current)return Promise.resolve();
    const current=latest.current,requestId='dispose-'+(++revision.current);let resolve!:()=>void;
    const promise=new Promise<void>(done=>{resolve=done;});
    const timer=setTimeout(()=>{id.current='';setError(true);finishDisposal();},MCP_APPS_HOST_MANIFEST.defaults.hostReadyTimeoutMs);
    disposal.current={requestId,promise,resolve,timer};setReady(false);
    post({type:'dispose',documentId:id.current,threadId:current.threadId,toolCallId:current.part.toolCallId,requestId});return promise;
  }
  useEffect(()=>{mounted.current=true;const document={owner:props.documentOwner,close:closeDocument};documents.add(document);return()=>{documents.delete(document);mounted.current=false;id.current='';finishDisposal();};},[props.documentOwner]);
  useEffect(()=>sync(),[props.part,props.settledToolCallIds,props.active,props.presentation,props.editorCompleted,theme,i18n.language,ready]);
  function failed(){id.current='';setReady(false);setError(true);finishDisposal();}
  async function receive(event:WebViewMessageEvent){
    if(!mounted.current||event.nativeEvent.url!==url)return;
    const message=readToolResultEvent(event.nativeEvent.data);if(!message)return;
    if(message.type==='ready'){
      if(message.documentId!==id.current){id.current=message.documentId;revision.current=0;handled.current.clear();}
      setReady(true);setError(false);sync();return;
    }
    const current=latest.current;
    if(message.documentId!==id.current||message.threadId!==current.threadId||message.toolCallId!==current.part.toolCallId)return;
    if(message.type==='disposed'){if(disposal.current?.requestId===message.requestId){id.current='';setReady(false);setError(true);finishDisposal();}return;}
    if(message.type==='height'){setHeight(Math.max(1,Math.ceil(message.height)));return;}
    if(message.type==='session-expired'){current.onSessionExpired();return;}
    if(message.type==='user-message'){
      if(handled.current.has(message.requestId))return;
      handled.current.add(message.requestId);const documentId=id.current;let accepted=false;
      try{if(!current.active||disposal.current)throw Error('TOOL_DOCUMENT_INACTIVE');await current.sendUserMessage(message.message);accepted=true;}catch{/* The original AppBridge displays its message failure. */}
      if(mounted.current&&id.current===documentId&&latest.current.threadId===message.threadId&&latest.current.part.toolCallId===message.toolCallId)post({type:'result',documentId,threadId:message.threadId,toolCallId:message.toolCallId,requestId:message.requestId,accepted});
      return;
    }
    const tool=resolveToolName(current.part);
    if(current.presentation!=='editor'||!isEditorWriteTool(tool))return;
    if(message.type==='tool-result'){if(message.tool===tool)current.addToolResult({tool,toolCallId:message.toolCallId,output:message.output});}
    else if(message.type==='confirmation-settled')current.onConfirmationSettled(message.toolCallId);
    else if(message.type==='editor-confirmed')current.onEditorWriteConfirmed?.(message.toolCallId);
    else if(message.type==='editor-jump'&&current.active){
      const expected=resolveEditorWriteJumpTarget(tool,(readToolInput(current.part)??{}) as Record<string,unknown>,getEditorWriteOutput(current.part,current.part.state==='output-error'));
      if(expected&&expected.cellId===message.detail.cellId&&expected.editorSessionId===message.detail.editorSessionId)current.onEditorJump?.(expected);
    }
  }
  return <View style={{height,minWidth:0}} testID={`native-tool-document-${props.part.toolCallId}`}>
    {url?<WebView<object> ref={view} source={{uri:url}} originWhitelist={['*']} sharedCookiesEnabled thirdPartyCookiesEnabled={false}
      onShouldStartLoadWithRequest={request=>toolResultNavigationAllowed(request.url,request.isTopFrame,props.origin)}
      onMessage={event=>void receive(event)} onLoadStart={()=>{id.current='';setReady(false);}} onError={failed}
      onHttpError={event=>{if(event.nativeEvent.url===url)failed();}} onContentProcessDidTerminate={failed}
      automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never" scrollEnabled={false} keyboardDisplayRequiresUserAction
      setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false} webviewDebuggingEnabled={__DEV__}
      style={{backgroundColor:colors['color-bg-app']}} />:null}
    {!ready||error||!url?<View style={[StyleSheet.absoluteFill,styles.feedback,{backgroundColor:colors['color-bg-app']}]}>{error?<Pressable accessibilityRole="button" style={styles.retry} onPress={()=>{setError(false);view.current?.reload();}}><InkLabel style={{color:colors['color-text-primary']}}>{t('chat.activity.retry')}</InkLabel></Pressable>:<ActivityIndicator color={colors['color-text-muted']}/>}</View>:null}
  </View>;
}
const styles=StyleSheet.create({feedback:{alignItems:'center',justifyContent:'center'},retry:{minHeight:44,paddingHorizontal:12,justifyContent:'center'}});
