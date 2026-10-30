// [Input] Canonical Chat history APIs, native foreground state and an optional HTTP boundary.
// [Output] Original paged history/search/delete reads with cancellation, retry and deleted-row suppression.
// [Pos] Native history view coordinator; task execution, authentication and persistence retain their existing owners.
import {useCallback,useEffect,useRef,useState} from 'react';
import {AppState} from 'react-native';
import {deleteChatThread,listChatThreads,type ChatHistoryThread} from '../../api/chatHistoryApi';
import {clientFetch} from '../../../../src/platform/transport.native';

// Same presentation values as the original ChatView history/search controls.
const PAGE_SIZE=20,SEARCH_DEBOUNCE_MS=180;
const initial=()=>({threads:[] as ChatHistoryThread[],loading:false,loadingMore:false,error:false,moreError:false,hasMore:false,
  searchOpen:false,query:'',results:[] as ChatHistoryThread[],searching:false,searchError:false,deletingId:null as string|null,deleteError:false});
export default function useNativeChatHistory({enabled=true,transport:rawTransport=clientFetch,onSessionExpired}:{enabled?:boolean;transport?:typeof fetch;onSessionExpired?:()=>void}={}) {
  const [state,setState]=useState(initial),current=useRef(state);current.current=state;
  const [foreground,setForeground]=useState(AppState.currentState!=='background' && AppState.currentState!=='inactive');
  const active=useRef(enabled && foreground);active.current=enabled && foreground;
  const mounted=useRef(true),listSequence=useRef(0),searchSequence=useRef(0),offset=useRef(0),moreLock=useRef(false),deleteLock=useRef(false);
  const consumed=useRef(new Set<string>()),deleted=useRef(new Set<string>());
  const listReader=useRef<AbortController|null>(null),searchReader=useRef<AbortController|null>(null),expire=useRef(onSessionExpired);expire.current=onSessionExpired;
  const transport=useCallback<typeof fetch>(async(input,init)=>{const response=await rawTransport(input,init);if(response.status===401)expire.current?.();return response;},[rawTransport]);
  const update=useCallback((patch:Partial<ReturnType<typeof initial>>)=>{if(!mounted.current)return;current.current={...current.current,...patch};setState(current.current);},[]);
  const cancelReads=useCallback(()=>{listSequence.current++;searchSequence.current++;listReader.current?.abort();searchReader.current?.abort();moreLock.current=false;update({loading:false,loadingMore:false,searching:false});},[update]);
  useEffect(()=>{mounted.current=true;const listener=AppState.addEventListener('change',next=>{const visible=next==='active';active.current=enabled && visible;if(!visible)cancelReads();setForeground(visible);});return()=>{mounted.current=false;listSequence.current++;searchSequence.current++;listReader.current?.abort();searchReader.current?.abort();listener.remove();};},[enabled,cancelReads]);
  const reload=useCallback(async()=>{
    if(!active.current)return;listReader.current?.abort();const controller=new AbortController();listReader.current=controller;
    const sequence=++listSequence.current;moreLock.current=false;update({loading:true,loadingMore:false,error:false,moreError:false});
    try {
      const rows=await listChatThreads({limit:PAGE_SIZE+1,offset:0},{signal:controller.signal,transport});
      if(!active.current || controller.signal.aborted || sequence!==listSequence.current)return;
      if(!Array.isArray(rows))throw new Error('CHAT_HISTORY_INVALID');
      const retained=rows.slice(0,PAGE_SIZE).filter(row=>!deleted.current.has(row.id));consumed.current=new Set(retained.map(row=>row.id));offset.current=retained.length;
      update({threads:retained,hasMore:rows.length>PAGE_SIZE});
    }catch{if(active.current && !controller.signal.aborted && sequence===listSequence.current)update({error:true});}
    finally{if(sequence===listSequence.current)update({loading:false});}
  },[transport,update]);
  const loadMore=useCallback(async()=>{
    if(!active.current || current.current.loading || moreLock.current || !current.current.hasMore)return;
    moreLock.current=true;const sequence=listSequence.current,controller=new AbortController();listReader.current=controller;update({loadingMore:true,moreError:false});
    try {
      const rows=await listChatThreads({limit:PAGE_SIZE+1,offset:offset.current},{signal:controller.signal,transport});
      if(!active.current || controller.signal.aborted || sequence!==listSequence.current)return;
      if(!Array.isArray(rows))throw new Error('CHAT_HISTORY_INVALID');
      const page=rows.slice(0,PAGE_SIZE).filter(row=>!deleted.current.has(row.id));offset.current+=page.length;page.forEach(row=>consumed.current.add(row.id));
      const ids=new Set(current.current.threads.map(row=>row.id));update({threads:[...current.current.threads,...page.filter(row=>!ids.has(row.id))],hasMore:rows.length>PAGE_SIZE});
    }catch{if(active.current && !controller.signal.aborted && sequence===listSequence.current)update({moreError:true});}
    finally{if(sequence===listSequence.current){moreLock.current=false;update({loadingMore:false});}}
  },[transport,update]);
  useEffect(()=>{if(enabled && foreground)void reload();else cancelReads();return()=>{listSequence.current++;listReader.current?.abort();moreLock.current=false;};},[enabled,foreground,reload,cancelReads]);
  useEffect(()=>{
    const sequence=++searchSequence.current;searchReader.current?.abort();const query=state.query.trim();
    if(!enabled || !foreground || !state.searchOpen || !query){update({searching:false,...(!query?{results:[],searchError:false}:{})});return;}
    const controller=new AbortController();searchReader.current=controller;update({searching:true,searchError:false});
    const timer=setTimeout(()=>{void(async()=>{
      try {
        const rows=await listChatThreads({query,searchScope:'all',retrievalMode:'fuzzy'},{signal:controller.signal,transport});
        if(!active.current || controller.signal.aborted || sequence!==searchSequence.current)return;
        if(!Array.isArray(rows))throw new Error('CHAT_HISTORY_INVALID');
        update({results:rows.filter(row=>!deleted.current.has(row.id))});
      }catch{if(active.current && !controller.signal.aborted && sequence===searchSequence.current)update({searchError:true});}
      finally{if(sequence===searchSequence.current)update({searching:false});}
    })();},SEARCH_DEBOUNCE_MS);
    return()=>{clearTimeout(timer);controller.abort();};
  },[state.query,state.searchOpen,enabled,foreground,transport,update]);
  async function remove(id:string):Promise<boolean> {
    if(deleteLock.current)return false;deleteLock.current=true;update({deletingId:id,deleteError:false});
    try {
      await deleteChatThread(id,transport);deleted.current.add(id);if(consumed.current.delete(id))offset.current=Math.max(0,offset.current-1);
      update({threads:current.current.threads.filter(row=>row.id!==id),results:current.current.results.filter(row=>row.id!==id)});return true;
    }catch{update({deleteError:true});return false;}
    finally{deleteLock.current=false;update({deletingId:null});}
  }
  return {...state,reload,loadMore,remove,setQuery:(query:string)=>update({query}),openSearch:()=>{update({searchOpen:true,query:'',results:[],searchError:false});void reload();},closeSearch:()=>update({searchOpen:false})};
}
