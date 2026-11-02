// [Sync] 2026-10-28: original file and folder sidebar batches retain per-file relative paths in one Workspace multipart request.
// [Input] User-selected native handles and the existing storage/workspace upload protocol.
// [Output] Native byte transfer adapter for the unchanged useFileUpload strategy and DTO parser.
// [Pos] iOS file transport; no arbitrary file paths, credentials or backend selection are accepted from callers.
// [Sync] 2026-10-28: import the original sketch editor's PNG into the same opaque file/upload owner.
import {NativeEventEmitter,NativeModules} from 'react-native';
import {readStorageUploadResponse,type FileUploadAdapter,type UploadOptions} from '../../app/_dream/hooks/useFileUpload';
import {normalizePath} from '../../app/_dream/api/workspaceFilesApi';
import {browserRequestHeaders} from '../../app/_dream/lib/browserSession';
import {clientFetch,bufferNativeResponse,nativeResponseStream} from './transport.native';
const runtime=NativeModules.InkRuntime;
export interface NativePickedFile {id:string;uri:string;name:string;type:string;size:number;relativePath?:string;}
export interface NativeFileSelection {files:NativePickedFile[];rejected:{name:string}[];}
export async function pickNativeFiles(maxBytes:number,directory=false):Promise<NativeFileSelection> {return runtime.pickFiles({maxBytes,...(directory?{directory:true}:{})});}
export function releaseNativeFiles(ids:string[]) {if(ids.length)runtime.releaseFiles(ids);}
export async function importNativeSketch(base64:string,name:string,maxBytes:number):Promise<NativePickedFile> {return runtime.importSketch({base64,name,maxBytes});}
export function createNativeFileUploadAdapter() {
  const pending=new Set<string>();
  let disposed=false;
  const events=new NativeEventEmitter(runtime);
  async function transfer(file:NativePickedFile|NativePickedFile[],options:Record<string,unknown>,onProgress?:UploadOptions['onProgress']) {
    if(disposed)throw new Error('UPLOAD_CLOSED');
    const id=`upload_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
    pending.add(id);
    const subscription=events.addListener('InkUploadProgress',(event:{id:string;progress:number})=>{if(event.id===id && Number.isFinite(event.progress))onProgress?.(event.progress);});
    try {
      const head=await runtime.openFileUpload({...options,id,...(Array.isArray(file)?{fileIds:file.map(item=>item.id)}:{fileId:file.id})});
      if(disposed)throw new Error('UPLOAD_CLOSED');
      return await bufferNativeResponse(nativeResponseStream(head));
    } finally {subscription.remove();pending.delete(id);runtime.cancelRequest(id);}
  }
  const adapter:FileUploadAdapter<NativePickedFile>={
    isFile:(file:unknown):file is NativePickedFile=>Boolean(file && typeof file==='object' && typeof (file as NativePickedFile).id==='string' && (file as NativePickedFile).id && typeof (file as NativePickedFile).name==='string'),
    request:clientFetch,
    serverUpload:async(file,filename,progress)=>readStorageUploadResponse(await transfer(file,{path:'/api/storage/upload',filename,headers:browserRequestHeaders()},progress)),
    directUpload:(url,file,method,headers)=>transfer(file,{url,method,headers}),
  };
  return {...adapter,
    uploadWorkspace:(file:NativePickedFile,sessionId:string)=>transfer(file,{path:'/api/workspace/files',fields:{sessionId,path:'files'},headers:browserRequestHeaders()}),
    uploadWorkspaceBatch:(files:NativePickedFile[],sessionId:string,path:string)=>transfer(files,{path:'/api/workspace/files',fields:{sessionId,...(path?{path}:{})},relativePaths:files.map(file=>normalizePath(file.relativePath||file.name)),headers:browserRequestHeaders()}),
    dispose:()=>{disposed=true;for(const id of pending)runtime.cancelRequest(id);pending.clear();},
  };
}
