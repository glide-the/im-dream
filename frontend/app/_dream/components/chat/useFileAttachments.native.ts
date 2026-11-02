// [Input] Native picked files, original storage strategy and optional workspace session.
// [Output] Original attachment metadata/progress, upload failures and selected-file cleanup.
// [Pos] Native input attachment orchestration; no business submission, permissions or runtime startup.
// [Sync] 2026-10-28: selected documents and local sketch PNG handles share the same upload and cleanup sequence.
import {useCallback,useEffect,useMemo,useRef,useState,type Dispatch,type SetStateAction} from 'react';
import {useTranslation} from 'react-i18next';
import {useFileUpload} from '../../hooks/useFileUpload';
import {readWorkspaceUploadResponse} from '../../api/workspaceFileUpload';
import {createNativeFileUploadAdapter,pickNativeFiles,releaseNativeFiles,type NativePickedFile} from '../../../../src/platform/fileUpload.native';
import {MAX_UPLOAD_FILE_SIZE_BYTES,formatFileSize,type UploadedFile} from './AIInputDock.helpers';
type SetFiles=Dispatch<SetStateAction<UploadedFile[]>>;
export default function useFileAttachments(workspaceSessionId?:string) {
  const {t}=useTranslation();
  const adapter=useMemo(()=>createNativeFileUploadAdapter(),[]);
  const {upload,error:storageError,clearError}=useFileUpload(adapter);
  const [error,setError]=useState<string|null>(null);
  const owned=useRef(new Map<string,string>());
  const active=useRef(true),picking=useRef(false);
  const releasePreview=useCallback((uri?:string)=>{
    if(!uri)return;const id=owned.current.get(uri);if(id){owned.current.delete(uri);releaseNativeFiles([id]);}
  },[]);
  useEffect(()=>()=>{active.current=false;adapter.dispose();releaseNativeFiles([...owned.current.values()]);owned.current.clear();},[adapter]);
  async function uploadFiles(files:NativePickedFile[],setFiles:SetFiles):Promise<boolean[]> {
    if(!active.current){releaseNativeFiles(files.map(file=>file.id));return files.map(()=>false);}
    for(const file of files)owned.current.set(file.uri,file.id);
    setFiles(current=>[...current,...files.map(file=>({id:file.id,name:file.name,mimeType:file.type,size:file.size,previewUrl:file.uri,isUploading:true,progress:0,uploadSource:'click' as const}))]);
    return Promise.all(files.map(async file=>{
      try {
        const workspace=workspaceSessionId ? await readWorkspaceUploadResponse(await adapter.uploadWorkspace(file,workspaceSessionId),t('chat.inputDock.workspaceSyncFailed')) : undefined;
        const result=await upload(file,{filename:file.name,contentType:file.type,onProgress:progress=>{if(active.current)setFiles(current=>current.map(entry=>entry.id===file.id?{...entry,progress}:entry));}});
        if(!active.current)return false;
        if(!result){releasePreview(file.uri);setFiles(current=>current.filter(entry=>entry.id!==file.id));return false;}
        setFiles(current=>current.map(entry=>entry.id===file.id?{...entry,url:result.url,storageKey:result.key,isUploading:false,progress:100,...workspace}:entry));
        return true;
      } catch(failure) {
        releasePreview(file.uri);
        if(active.current){setFiles(current=>current.filter(entry=>entry.id!==file.id));setError(failure instanceof Error?failure.message:t('chat.inputDock.uploadFailed'));}
        return false;
      }
    }));
  }
  async function chooseFiles(setFiles:SetFiles) {
    if(picking.current)return;picking.current=true;setError(null);clearError();
    try {
      const selection=await pickNativeFiles(MAX_UPLOAD_FILE_SIZE_BYTES);
      if(!active.current){releaseNativeFiles(selection.files.map(file=>file.id));return;}
      for(const rejected of selection.rejected)setError(t('chat.inputDock.fileTooLarge',{name:rejected.name,max:formatFileSize(MAX_UPLOAD_FILE_SIZE_BYTES)}));
      await uploadFiles(selection.files,setFiles);
    } catch(failure) {if(active.current)setError(failure instanceof Error?failure.message:t('chat.inputDock.uploadFailed'));}
    finally {picking.current=false;}
  }
  function deleteFile(id:string,setFiles:SetFiles) {setFiles(current=>{releasePreview(current.find(file=>file.id===id)?.previewUrl);return current.filter(file=>file.id!==id);});}
  return {chooseFiles,addFiles:async(files:NativePickedFile[],setFiles:SetFiles)=>{setError(null);clearError();return uploadFiles(files,setFiles);},deleteFile,releasePreview,error:error || storageError};
}
