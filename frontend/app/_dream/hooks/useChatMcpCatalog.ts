// [Input] Authenticated managed-connection read APIs for the current platform.
// [Output] Chat's available MCP connection names, loading/error and explicit reread.
// [Pos] Read-only Chat catalog; Settings owns connection creation, authentication and enabled/revision.
import {useCallback,useEffect,useRef,useState} from 'react';
import * as browserApi from '../api/claudeMcpApi';
import type {ClaudeMcpApi,ClaudeMcpCapability,ClaudeMcpServer} from '../api/claudeMcpApi';
import {safeApiErrorMessage} from '../components/claude-mcp/mcpResourcePresentation';

export default function useChatMcpCatalog(api:Pick<ClaudeMcpApi,'getClaudeMcpCapability'|'listClaudeMcpServers'>=browserApi){
  const generation=useRef(0);
  const [state,setState]=useState<{servers:ClaudeMcpServer[];capability:ClaudeMcpCapability|null;loading:boolean;error:string|null}>({servers:[],capability:null,loading:true,error:null});
  const load=useCallback(async()=>{
    const current=++generation.current;setState(value=>({...value,loading:true,error:null}));
    try{
      const [capability,servers]=await Promise.all([api.getClaudeMcpCapability(),api.listClaudeMcpServers()]);
      if(current===generation.current)setState({capability,servers:capability.enabled?servers:[],loading:false,error:null});
    }catch(error){if(current===generation.current)setState(value=>({...value,loading:false,error:safeApiErrorMessage(error,'Claude MCP 状态读取失败')}));}
  },[api]);
  useEffect(()=>{void load();return()=>{generation.current++;};},[load]);
  return {...state,load};
}
