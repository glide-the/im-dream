// [Sync] 2026-11-13: expose localized Agent names for Chinese native visual qualification.
// [Sync] 2026-11-13: native controls receive the production Thread tool-selection owner.
// [Input] Production native action row, original useComposerDraft and simulated public IM APIs.
// [Output] Isolated RNW presentation for Agent/tools and model interactions with original send guards.
// [Pos] Technical fixture only; native keyboard/system surfaces and real runtime remain outside this renderer.
import React,{useState} from 'react';
import AIInputDockControls from '../../app/_dream/components/chat/AIInputDockControls.native';
import {useChatToolSelection} from '../../app/_dream/hooks/useChatToolSelection';
import useComposerDraft from '../../app/_dream/components/chat/useComposerDraft';
import type {Deck} from '../../app/_dream/api/voiceApi';
import type {DeckAgentSelection} from '../../app/_dream/components/deck/deckAgentSelection';
const decks:Deck[]=[{id:'fixture-deck',name:'Writing',name_zh:'写作与研究',enabled:true,is_system:false,agent_type:'chat',agent_type_revision:1,voices:[{id:'fixture-agent',deck_id:'fixture-deck',name:'Writer',name_zh:'中文写作助手 Writer',enabled:true,icon:'brain',color:'blue',system_prompt:'Fixture role',is_system:false}]}];
export default function NativeHarness(){
  const [selection,setSelection]=useState<DeckAgentSelection>(),[blocked,setBlocked]=useState(false),[active,setActive]=useState(true),[sent,setSent]=useState(''),[modelSaves,setModelSaves]=useState(0);
  const toolSelection=useChatToolSelection('native-tools-fixture');
  const draft=useComposerDraft({onSendMessage:message=>setSent(message),disabled:blocked,loading:false,fullAccessEnabled:false,defaultToolChoice:'auto',initialDraft:'Retained native draft',onUploadBlocked:()=>{},releasePreview:()=>{}});
  return <main style={{height:'100dvh',padding:16,boxSizing:'border-box',display:'flex',flexDirection:'column',gap:12}}>
    <button onClick={()=>setActive(value=>!value)}>Toggle native scene</button>
    <textarea aria-label="Native draft" value={draft.query} onChange={event=>draft.setQuery(event.target.value)}/><output data-testid="native-sent">{sent}</output><output data-testid="native-model-saves">{modelSaves}</output>
    <section style={{marginTop:'auto'}}><AIInputDockControls tools={toolSelection.tools} onToolsChange={toolSelection.setTools} draft={draft} disabled={false} loading={false} fullAccessEnabled={false} active={active} onChooseFiles={()=>{}} onOpenSketch={()=>{}} onModelBlocked={setBlocked} onModelConfigSaved={()=>setModelSaves(value=>value+1)} agentSelection={{decks,selectedAgentId:selection?.agentId,onChange:setSelection}}/></section>
  </main>;
}
