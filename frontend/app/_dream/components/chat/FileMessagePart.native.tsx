// [Input] Original file message, App origin and the existing private byte/export owner.
// [Output] Native attachment metadata, image preview and explicit system download/share with cancellable file leases.
// [Pos] File presentation only; Cookie identity and storage ownership remain with the original endpoint.
import {useEffect,useMemo,useRef,useState} from 'react';
import {ActivityIndicator,AppState,Image,Modal,Pressable,SafeAreaView,ScrollView,StyleSheet,View,useWindowDimensions} from 'react-native';
import type {FileUIPart} from 'ai';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {messageFileResources,type MessageFileResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {formatFileSize,messageStoragePath,resolveFileUrl} from './fileMessagePresentation';
import {IconDownload,IconFile,IconX} from './Icons';
export default function FileMessagePart({part,origin,isUserMessage,resources=messageFileResources,onOpenLink}:{part:FileUIPart;origin:string;isUserMessage:boolean;resources?:MessageFileResources;onOpenLink?:(url:string)=>void}){
  const {t}=useTranslation(),colors=useInkColors(),dimensions=useWindowDimensions();
  const url=resolveFileUrl(part.url),path=messageStoragePath(part.url,origin),isImage=part.mediaType.startsWith('image/');
  const direct=!path&&url&&(/^https?:\/\//.test(url)||/^data:image\//.test(url))?url:undefined;
  const [file,setFile]=useState<NativePickedFile>(),[loading,setLoading]=useState(Boolean(path&&isImage)),[failed,setFailed]=useState(false),[busy,setBusy]=useState(false),[expanded,setExpanded]=useState(false),[ratio,setRatio]=useState(1),[retry,setRetry]=useState(0),[foreground,setForeground]=useState(AppState.currentState!=='background');
  const lease=useRef<NativePickedFile|undefined>(undefined),mounted=useRef(true),request=useRef<AbortController|undefined>(undefined);
  const owner=useMemo(()=>({path,resources,foreground}),[path,resources,foreground]),current=useRef(owner);current.current=owner;
  useEffect(()=>{mounted.current=true;const listener=AppState.addEventListener('change',state=>setForeground(state!=='background'));return()=>{mounted.current=false;listener.remove();};},[]);
  useEffect(()=>{
    let active=true;const abort=new AbortController();request.current=abort;setFile(undefined);setFailed(false);setLoading(Boolean(path&&isImage&&foreground));
    if(path&&isImage&&foreground)void resources.acquire(path,abort.signal).then(value=>{if(!active){resources.release(value);return;}lease.current=value;setFile(value);setLoading(false);}).catch(()=>{if(active){setFailed(true);setLoading(false);}});
    return()=>{active=false;abort.abort();if(lease.current){resources.release(lease.current);lease.current=undefined;}};
  },[path,isImage,foreground,resources,retry]);
  const name=part.filename||part.url.split('/').pop()||'Attachment',type=part.filename?.split('.').pop()?.toUpperCase()||part.mediaType.split('/').pop()?.toUpperCase()||'FILE';
  const size=(part as FileUIPart&{size?:number}).size,source=file?.uri??direct;
  const unsupported=!path&&!direct&&!(url&&/^https?:\/\//.test(url));
  async function download(){
    if(busy)return;
    if(!path){if(url&&/^https?:\/\//.test(url))onOpenLink?.(url);return;}
    setBusy(true);setFailed(false);
    try{
      let owned=lease.current;
      if(!owned){owned=await resources.acquire(path,request.current?.signal);if(!mounted.current||current.current!==owner){resources.release(owned);return;}lease.current=owned;setFile(owned);}
      await resources.export(owned);
    }catch{if(mounted.current)setFailed(true);}finally{if(mounted.current)setBusy(false);}
  }
  const photo=(full=false)=><Image key={`${source}:${retry}`} accessibilityLabel={name} source={{uri:source!}} resizeMode="contain" onLoad={({nativeEvent})=>{const value=nativeEvent.source;if(value.width>0&&value.height>0)setRatio(value.width/value.height);}} onError={()=>setFailed(true)} style={full?{width:Math.max(1,dimensions.width-32),height:Math.max(1,dimensions.height-120)}:{width:Math.min(448,dimensions.width-32),maxWidth:'100%',aspectRatio:ratio,maxHeight:dimensions.height*.68}}/>;
  const feedback=unsupported?<View style={styles.feedback}><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t('chat.workspaceFile.unsupported')}</InkLabel></View>:failed?<View style={styles.feedback}><InkLabel accessibilityRole="alert" style={{color:colors['color-text-muted']}}>{t('chat.workspaceFile.retryable')}</InkLabel><Pressable accessibilityRole="button" onPress={()=>setRetry(value=>value+1)} style={styles.button}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.workspaceFile.retry')}</InkLabel></Pressable></View>:loading?<View style={styles.feedback}><ActivityIndicator accessibilityLabel={t('chat.workspaceFile.loadingImage')} color={colors['color-text-muted']}/></View>:null;
  return <View style={[styles.card,{alignSelf:isUserMessage?'flex-end':'flex-start',borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-paper']}]}>
    {isImage?<>{feedback}{source&&!failed?<Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.previewAction',{name})} onPress={()=>setExpanded(true)}>{photo()}</Pressable>:null}<View style={styles.row}><InkLabel style={[styles.name,{flex:1,color:colors['color-text-secondary']}]}>{name}</InkLabel>{path||url&&/^https?:\/\//.test(url)?<Pressable accessibilityRole="button" accessibilityLabel={`Download ${name}`} onPress={()=>void download()} disabled={busy} style={styles.button}>{busy?<ActivityIndicator/>:<IconDownload width={18} height={18} color={colors['color-text-secondary']}/>}</Pressable>:null}</View></>:<View style={styles.row}>
      <IconFile width={24} height={24} color={colors['color-text-muted']}/><View style={{flex:1,minWidth:0}}><InkLabel numberOfLines={1} style={{color:colors['color-text-primary']}}>{name}</InkLabel><InkLabel style={{color:colors['color-text-muted'],fontSize:12}}>{[type,size?formatFileSize(size):'',part.mediaType==='application/octet-stream'?'':part.mediaType].filter(Boolean).join(' · ')}</InkLabel></View>
      {path||url&&/^https?:\/\//.test(url)?<Pressable accessibilityRole="button" accessibilityLabel={`Download ${name}`} onPress={()=>void download()} disabled={busy} style={styles.button}>{busy?<ActivityIndicator/>:<IconDownload width={18} height={18} color={colors['color-text-secondary']}/>}</Pressable>:null}
    </View>}
    {!isImage?feedback:null}
    <Modal visible={expanded} presentationStyle="fullScreen" animationType="fade" onRequestClose={()=>setExpanded(false)} supportedOrientations={['portrait','landscape']}><SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
      <View style={styles.row}><InkLabel numberOfLines={1} style={{flex:1,color:colors['color-text-primary']}}>{name}</InkLabel><Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.downloadImage')} onPress={()=>void download()} disabled={busy||loading} style={styles.button}><IconDownload width={18} height={18} color={colors['color-text-secondary']}/></Pressable><Pressable accessibilityRole="button" accessibilityLabel={t('chat.workspaceFile.closePreview')} onPress={()=>setExpanded(false)} style={styles.button}><IconX width={18} height={18} color={colors['color-text-secondary']}/></Pressable></View>
      {feedback}<ScrollView style={styles.fill} contentContainerStyle={{flexGrow:1,alignItems:'center',justifyContent:'center'}} minimumZoomScale={1} maximumZoomScale={4} centerContent>{source&&!failed?photo(true):null}</ScrollView>
    </SafeAreaView></Modal>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},card:{minWidth:0,maxWidth:'100%',borderWidth:1,borderRadius:14,overflow:'hidden'},row:{flexDirection:'row',alignItems:'center',gap:12,padding:12},button:{minWidth:44,minHeight:44,padding:10,alignItems:'center',justifyContent:'center'},name:{padding:10,fontSize:14},feedback:{padding:12,gap:8}});
