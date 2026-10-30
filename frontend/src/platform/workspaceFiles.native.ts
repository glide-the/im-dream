// [Input] Existing Workspace GET query, browser CSRF owner and native opaque file-resource methods.
// [Output] Cancellable binary resource leases, UTF-8 text, independent attachment copies and system export receipts.
// [Pos] Native byte/file adapter; server ownership/path policy and original URLs remain authoritative.
import {NativeModules} from 'react-native';
import {browserRequestHeaders,getBrowserCsrfToken} from '../../app/_dream/lib/browserSession';
import {failureFromStatus,WorkspaceFileRequestError} from '../../app/_dream/components/chat/workspaceFileAccess';
import type {NativePickedFile} from './fileUpload.native';
export type WorkspaceAvailability='loading'|'enabled'|'disabled';
export interface WorkspaceResources {
  acquire:(input:{threadId:string;path:string;download?:boolean},signal?:AbortSignal)=>Promise<NativePickedFile>;
  text:(file:NativePickedFile)=>Promise<string>;
  copy:(file:NativePickedFile)=>Promise<NativePickedFile>;
  export:(file:NativePickedFile)=>Promise<{completed:boolean}>;
  release:(file:NativePickedFile)=>void;
}
function valid(file:NativePickedFile):boolean {return Boolean(file&&typeof file.id==='string'&&file.id&&typeof file.uri==='string'&&file.uri.startsWith('file://')&&typeof file.name==='string'&&file.name&&typeof file.type==='string'&&Number.isSafeInteger(file.size)&&file.size>=0);}
export function createWorkspaceResources(runtime=NativeModules.InkRuntime,onSessionExpired?:()=>void):WorkspaceResources {
  const release=(file:NativePickedFile)=>{if(file?.id)runtime?.releaseFiles([file.id]);};
  return {
    async acquire({threadId,path,download=false},signal){
      if(!threadId||!path)throw new WorkspaceFileRequestError('missing');
      if(!getBrowserCsrfToken())throw new WorkspaceFileRequestError('access');
      if(signal?.aborted)throw new WorkspaceFileRequestError('retryable');
      const id=`workspace_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
      const abort=()=>runtime?.cancelWorkspaceFile(id);signal?.addEventListener('abort',abort,{once:true});
      let file:NativePickedFile|undefined;
      try {
        file=await runtime.readWorkspaceFile({id,path:`/api/workspace/files/${download?'download':'content'}?${new URLSearchParams({sessionId:threadId,path})}`,method:'GET',headers:browserRequestHeaders()});
        if(signal?.aborted||!valid(file!))throw new WorkspaceFileRequestError('retryable');
        return file!;
      }catch(reason){
        if(file)release(file);
        if(reason instanceof WorkspaceFileRequestError)throw reason;
        const code=reason&&typeof reason==='object'&&'code' in reason?String(reason.code):'';
        const status=/^WORKSPACE_HTTP_(\d{3})$/.exec(code);
        if(status&&Number(status[1])===401)onSessionExpired?.();
        throw new WorkspaceFileRequestError(status?failureFromStatus(Number(status[1])):'retryable');
      }finally{signal?.removeEventListener('abort',abort);}
    },
    async text(file){if(!['text/plain','text/markdown'].includes(file.type))throw new WorkspaceFileRequestError('unsupported');try{return await runtime.readWorkspaceText(file.id);}catch{throw new WorkspaceFileRequestError('unsupported');}},
    async copy(file){const copy=await runtime.copyWorkspaceFile(file.id) as NativePickedFile;if(!valid(copy)||copy.id===file.id){if(copy?.id&&copy.id!==file.id)release(copy);throw new WorkspaceFileRequestError('retryable');}return copy;},
    async export(file){return runtime.exportFile(file.id);},release,
  };
}
export const workspaceResources=createWorkspaceResources();
