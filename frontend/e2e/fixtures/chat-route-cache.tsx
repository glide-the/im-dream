// [Input] Production Web Router, ChatView and synthetic test session responses.
// [Output] Visible Chat/Timeline navigation and mount evidence for the isolated browser harness.
// [Pos] Physical Vite scan entry; all Chat state and rendering remain owned by production modules.
// [Sync] 2026-11-13: wait for the original AuthProvider session before mounting authenticated Chat consumers.
// [Sync] 2026-11-13: Chinese visual checks use the original App font assets and an explicit fixture locale.
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import {StoryWorkspaceRouter} from '../../app/_dream/router/story-workspace.tsx';
import ChatView from '../../app/_dream/components/chat/ChatView.tsx';
import {AuthProvider,useAuth} from '../../app/_dream/contexts/AuthContext.tsx';
import i18n from '../../app/_dream/i18n.ts';import '../../app/_dream/index.css';
import '../../app/_dream/App.css';
declare global {interface Window {__routeCache:{mounts:number}}}
await i18n.changeLanguage(new URLSearchParams(location.search).get('lang')==='zh'?'zh':'en');window.__routeCache={mounts:0};
function Chat({visible}:{visible:boolean}){React.useEffect(()=>{window.__routeCache.mounts++;},[]);return <ChatView isVisible={visible}/>;}
function Harness(){const [visible,setVisible]=useState(true);return <div style={{height:'100vh',display:'flex',flexDirection:'column'}}><div>{['chat','timeline'].map(route=><button key={route} onClick={()=>{history.pushState({},'','/story-workspace/'+route);dispatchEvent(new PopStateEvent('popstate'));}}>Navigate {route}</button>)}</div><StoryWorkspaceRouter onRouteChange={route=>setVisible(route==='chat')} workspaceContent={{chat:<Chat visible={visible}/>,timeline:<div>Timeline fixture</div>}}/></div>;}
function AuthenticatedHarness(){const auth=useAuth();return auth.isLoading?<p>Loading fixture session</p>:auth.isAuthenticated?<Harness/>:<p role="alert">Fixture session unavailable</p>;}
const root=document.getElementById('root');if(!root)throw Error('CACHE_ROOT_MISSING');createRoot(root).render(<AuthProvider><AuthenticatedHarness/></AuthProvider>);
