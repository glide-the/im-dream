// [Sync] 2026-11-13: expose two isolated Threads and production request serialization for tool scope assertions.
// [Input] Production Chat composer, Agent selector and MCP resource cards with explicit synthetic callbacks.
// [Output] Provider-free component surfaces; all HTTP is intercepted by the owning Playwright spec.
// [Pos] Technical fixture only; Project/Episode/artifacts/Run/Hook/database/model are out of scope.
// [Sync] 2026-11-13: allow explicit Chinese visual fixtures with the production App font faces.
import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import i18n from '../../app/_dream/i18n';
import AIInputDock from '../../app/_dream/components/chat/AIInputDock';
import {buildClaudeChatRequest} from '../../app/_dream/lib/claude-chat-request';

import type {DeckAgentSelection} from '../../app/_dream/components/deck/deckAgentSelection';
import type {Deck} from '../../app/_dream/api/voiceApi';
import ClaudeMcpResourceSection from '../../app/_dream/components/claude-mcp/ClaudeMcpResourceSection';
import '../../app/_dream/styles/tokens.css';
import '../../app/_dream/index.css';
import '../../app/_dream/App.css';
const decks:Deck[]=[{id:'fixture-deck',name:'Writing',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,voices:[{id:'fixture-agent',deck_id:'fixture-deck',name:'Writer',enabled:true,icon:'brain',color:'blue',system_prompt:'Fixture role',is_system:false}]}];
await i18n.changeLanguage(new URLSearchParams(location.search).get('lang')==='zh'?'zh':'en');
document.body.style.margin='0';
document.body.style.background='var(--color-bg-app)';
document.body.style.color='var(--color-text-primary)';
function Harness(){
  const [selection,setSelection]=useState<DeckAgentSelection>(),[running,setRunning]=useState(false),[resources,setResources]=useState(false),[managed,setManaged]=useState(0),[sent,setSent]=useState(''),[threadId,setThreadId]=useState('fixture-A'),[request,setRequest]=useState('');
  return <main style={{maxWidth:840,margin:'0 auto',padding:16,boxSizing:'border-box',minHeight:'100dvh',display:'flex',flexDirection:'column',gap:12}}>
    <div style={{display:'flex',gap:8,flexWrap:'wrap'}}><button onClick={()=>setThreadId('fixture-A')}>Thread A</button><button onClick={()=>setThreadId('fixture-B')}>Thread B</button><button onClick={()=>setRunning(value=>!value)}>Toggle running</button><button onClick={()=>setResources(value=>!value)}>Toggle resources</button><button onClick={()=>document.documentElement.setAttribute('data-theme','dark')}>Dark</button></div>
    <output data-testid="request">{request}</output><output data-testid="sent">{sent}</output><output data-testid="managed">{managed}</output>
    {resources?<ClaudeMcpResourceSection onOpenServerDetail={()=>setManaged(value=>value+1)}/>:null}
    <section style={{marginTop:'auto',paddingBottom:16}}>
      <AIInputDock threadId={threadId} fullAccessEnabled={false} loading={running} onStop={()=>setRunning(false)} mode="full" onSendMessage={(message,_files,mode,tools)=>{setSent(JSON.stringify({message,mode,agent:selection?.agentId}));setRequest(JSON.stringify(buildClaudeChatRequest({id:threadId,message:{id:'fixture-message',role:'user',parts:[{type:'text',text:message}]},context:{currentToolChoice:mode??'auto',imFullAccessEnabled:false,tools}})));}}
        agentSelection={{decks,selectedAgentId:selection?.agentId,onChange:setSelection}}/>
    </section>
  </main>;
}
const root=createRoot(document.getElementById('root')!);
if(new URLSearchParams(location.search).has('native')){void import('./chat-tools-native-harness').then(({default:NativeHarness})=>root.render(<NativeHarness/>));}else root.render(<Harness/>);
