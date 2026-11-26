// [Input] Current Thread ID and composer-owned draft choices.
// [Output] In-memory Thread-scoped tool descriptors, captured by each outgoing message.
// [Pos] Chat selection state; no resource configuration API or persistent account preference.
import {useState,useSyncExternalStore} from 'react';
import type {ChatToolDescriptor} from '../lib/chat-schema';

const empty:readonly ChatToolDescriptor[]=Object.freeze([]);
const selections=new Map<string,readonly ChatToolDescriptor[]>();
const listeners=new Set<()=>void>();
const subscribe=(listener:()=>void)=>{listeners.add(listener);return()=>{listeners.delete(listener);};};
export function rememberThreadTools(threadId:string,tools:readonly ChatToolDescriptor[]){
  selections.set(threadId,tools.map(tool=>({...tool})));
  listeners.forEach(listener=>listener());
}
export function readThreadTools(threadId:string):readonly ChatToolDescriptor[]{return selections.get(threadId)??empty;}
export function useChatToolSelection(threadId?:string){
  const [draft,setDraft]=useState<readonly ChatToolDescriptor[]>(empty);
  const tools=useSyncExternalStore(subscribe,()=>threadId?readThreadTools(threadId):draft,()=>empty);
  return {tools,setTools:(next:readonly ChatToolDescriptor[])=>threadId?rememberThreadTools(threadId,next):setDraft(next)};
}
export function toggleChatMcp(tools:readonly ChatToolDescriptor[],serverName:string):ChatToolDescriptor[]{
  const selected=tools.some(tool=>tool.type==='mcp'&&tool.server_name===serverName);
  return selected?tools.filter(tool=>tool.type!=='mcp'||tool.server_name!==serverName):[...tools,{type:'mcp',server_name:serverName}];
}
