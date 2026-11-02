// [Input] Strict Workspace URI, selected Thread, server-owned Workspace availability and native foreground state.
// [Output] Original access/loading/failure feedback and a private resource lease released on close/change/background.
// [Pos] Native Workspace read lifecycle; no task execution, persisted file copy or automatic business mutation.
import {useEffect,useMemo,useState} from 'react';
import {AppState} from 'react-native';
import {parseWorkspaceUri} from './workspaceUri';
import {WorkspaceFileRequestError,type WorkspaceFileRequestFailure} from './workspaceFileAccess';
import {workspaceResources,type WorkspaceAvailability,type WorkspaceResources} from '../../../../src/platform/workspaceFiles.native';
import type {NativePickedFile} from '../../../../src/platform/fileUpload.native';
type State={kind:'loading'}|{kind:'error';failure:WorkspaceFileRequestFailure}|{kind:'loaded';file:NativePickedFile;text?:string};
export default function useNativeWorkspaceFile({uri,threadId,availability,resources=workspaceResources,download=false,document=false}:{uri:string;threadId?:string;availability:WorkspaceAvailability;resources?:WorkspaceResources;download?:boolean;document?:boolean}){
  const parsed=useMemo(()=>parseWorkspaceUri(uri),[uri]);
  const identity=JSON.stringify([uri,threadId,availability,download,document]);
  const [snapshot,setSnapshot]=useState<{identity:string;state:State}>({identity,state:{kind:'loading'}});
  const setState=(state:State)=>setSnapshot({identity,state});
  const state=snapshot.identity===identity?snapshot.state:{kind:'loading'} as State;
  const [retry,setRetry]=useState(0),[foreground,setForeground]=useState(AppState.currentState==='active');
  useEffect(()=>{const listener=AppState.addEventListener('change',next=>setForeground(next==='active'));return()=>listener.remove();},[]);
  useEffect(()=>{
    if(!parsed.ok){setState({kind:'error',failure:'invalid'});return;}
    if(availability==='disabled'){setState({kind:'error',failure:'disabled'});return;}
    if(availability==='loading'){setState({kind:'loading'});return;}
    if(!threadId){setState({kind:'error',failure:'missing'});return;}
    setState({kind:'loading'});if(!foreground)return;
    const controller=new AbortController();let file:NativePickedFile|undefined,active=true;
    void resources.acquire({threadId,path:parsed.path,download},controller.signal).then(async asset=>{
      file=asset;if(!active){resources.release(asset);file=undefined;return;}
      const text=document?await resources.text(asset):undefined;
      if(active&&!controller.signal.aborted)setState({kind:'loaded',file:asset,text});
    }).catch(reason=>{if(active&&!controller.signal.aborted)setState({kind:'error',failure:reason instanceof WorkspaceFileRequestError?reason.failure:'retryable'});});
    return()=>{active=false;controller.abort();if(file){resources.release(file);file=undefined;}};
  },[parsed,threadId,availability,resources,download,document,foreground,retry]);
  return {parsed,state,retry:()=>setRetry(value=>value+1)};
}
