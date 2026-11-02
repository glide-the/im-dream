'use client';
// [Input] Native-owned frozen export DTOs and authenticated Workspace image results.
// [Output] Original long-image render/progress and original PNG stitch/fallback artifacts.
// [Pos] Fixed DOM capture leaf; RN owns history reads, modal controls and system export.
import {useEffect,useRef} from 'react';
import {renderThreadImage,releaseThreadImage,type RenderedThreadImage} from './exportThreadImage';
import {prepareThreadImageDownload} from './threadImageDownload';
import {readChatImageCommand,type ChatImageEvent,type ChatImagePNG} from './ChatImageDocument.protocol';
import i18n from '../../i18n';

async function imagePNG(href:string,name:string):Promise<ChatImagePNG> {
 const image=new Image();image.src=href;await image.decode();
 let blob=await(await fetch(href)).blob();
 if(blob.type!=='image/png'){
  const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
  const context=canvas.getContext('2d');if(!context)throw new Error('SHARE_CANVAS_UNAVAILABLE');context.drawImage(image,0,0);
  blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(new Error('SHARE_PNG_FAILED')),'image/png'));
 }
 const base64=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(new Error('SHARE_READ_FAILED'));reader.onload=()=>{const value=reader.result;if(typeof value==='string')resolve(value.slice(value.indexOf(',')+1));else reject(new Error('SHARE_READ_FAILED'));};reader.readAsDataURL(blob);});
 const result={name,base64,size:blob.size,width:image.naturalWidth,height:image.naturalHeight};image.src='';return result;
}
type EventPayload<T=ChatImageEvent>=T extends unknown?Omit<T,'documentId'>:never;
export default function ChatImageDocument(){
 const identity=useRef('');
 useEffect(()=>{
  identity.current=crypto.randomUUID();let active=true,current='',generation=0,rendered:RenderedThreadImage|null=null,serial=Promise.resolve();
  const imageWaiters=new Map<string,(value:Blob)=>void>();
  const imageFailures=new Map<string,()=>void>();
  function emit(value:EventPayload){if(active)window.ReactNativeWebView?.postMessage(JSON.stringify({...value,documentId:identity.current}));}
  function clear(){generation++;current='';releaseThreadImage(rendered);rendered=null;for(const fail of imageFailures.values())fail();imageFailures.clear();imageWaiters.clear();}
  function receive(event:MessageEvent){
   let raw:unknown=event.data;if(typeof raw==='string'){try{raw=JSON.parse(raw);}catch{return;}}
   const message=readChatImageCommand(raw);if(!message||message.documentId!==identity.current)return;
   if(message.type==='workspaceImageResult'){
    if(message.requestId!==current)return;const resolve=imageWaiters.get(message.imageId),fail=imageFailures.get(message.imageId);imageWaiters.delete(message.imageId);imageFailures.delete(message.imageId);
    if(message.image&&resolve){try{const binary=atob(message.image.base64),bytes=Uint8Array.from(binary,char=>char.charCodeAt(0));resolve(new Blob([bytes],{type:message.image.type}));}catch{fail?.();}}else fail?.();return;
   }
   if(message.type==='clear'){if(message.requestId===current)clear();return;}
   if(message.type==='render'){
    clear();current=message.requestId;const epoch=generation;
    const valid=()=>active&&current===message.requestId&&generation===epoch;
    serial=serial.catch(()=>{}).then(async()=>{
     if(!valid())return;await i18n.changeLanguage(message.language);if(message.theme==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=message.theme;
     let partial:RenderedThreadImage|null=null,previewJobs=Promise.resolve();
     try{
      const result=await renderThreadImage(message.options,{
       loadWorkspaceImage:(_parsed,_thread)=>new Promise<Blob>((resolve,reject)=>{if(!valid()){reject(new Error('SHARE_CLOSED'));return;}const imageId=crypto.randomUUID();imageWaiters.set(imageId,resolve);imageFailures.set(imageId,()=>reject(new Error('SHARE_IMAGE_UNAVAILABLE')));emit({type:'workspaceImage',requestId:message.requestId,imageId,uri:'workspace://'+_parsed.path});}),
       onProgress:progress=>{if(valid())emit({type:'progress',requestId:message.requestId,...progress});},
       onPartialPreview:next=>{releaseThreadImage(partial);partial=next;previewJobs=previewJobs.then(async()=>{try{const png=await imagePNG(next.images[0],next.fileName);if(valid())emit({type:'preview',requestId:message.requestId,partial:true,fileName:next.fileName,images:[png]});}catch{/* Final capture still reports its own result. */}});},
      });
      await previewJobs;releaseThreadImage(partial);partial=null;
      if(!valid()){releaseThreadImage(result);return;}rendered=result;
      const images:ChatImagePNG[]=[];for(const href of result.images)images.push(await imagePNG(href,result.fileName));
      if(valid())emit({type:'preview',requestId:message.requestId,partial:false,fileName:result.fileName,images});
     }catch{if(valid())emit({type:'failed',requestId:message.requestId});}
     finally{releaseThreadImage(partial);}
    });return;
   }
   if(message.requestId!==current||!rendered)return;
   const source=rendered,epoch=generation;
   void(async()=>{const artifacts=await prepareThreadImageDownload(source);try{const images:ChatImagePNG[]=[];for(const artifact of artifacts)images.push(await imagePNG(artifact.href,artifact.fileName));if(active&&generation===epoch&&current===message.requestId)emit({type:'prepared',requestId:message.requestId,deliveryId:message.deliveryId,images});}finally{for(const artifact of artifacts)if(artifact.owned)URL.revokeObjectURL(artifact.href);}})().catch(()=>{if(active&&generation===epoch)emit({type:'failed',requestId:message.requestId,deliveryId:message.deliveryId});});
  }
  window.addEventListener('message',receive);emit({type:'ready'});
  return()=>{active=false;clear();window.removeEventListener('message',receive);};
 },[]);
 return <div aria-hidden="true"/>;
}
