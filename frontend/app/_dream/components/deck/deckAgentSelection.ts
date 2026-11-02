// [Input] Existing enabled Agent entries, Deck labels and the current query.
// [Output] Original Deck-grouped prefix search, localized labels and selected Agent lookup.
// [Pos] Shared selector model; no catalog loading, eligibility policy or selection persistence.
import type {Deck,Voice} from '../../api/voiceApi';
export interface DeckAgentSelection {deckId:string;agentId:string;}
export interface DeckChatSelectorProps {
  decks:Deck[];selectedAgentId?:string;onChange?:(selection:DeckAgentSelection|undefined)=>void;
  loading?:boolean;error?:string|null;allowNone?:boolean;variant?:'compact'|'dream';
  noneLabel?:string;triggerLabel?:string;unavailableSelectionLabel?:string;
}
export interface AgentGroup {deck:Deck;agents:Voice[];}
export function enabledAgentsOf(deck:Deck):Voice[] {return (deck.voices || []).filter(agent=>agent.enabled);}
export function deckLabel(deck:Deck,language:string):string {return (language==='zh'?deck.name_zh:deck.name_en) || deck.name;}
export function agentLabel(agent:Voice,language:string):string {return (language==='zh'?agent.name_zh:agent.name_en) || agent.name;}
export function groupDeckAgents(decks:Deck[],query:string,language:string):AgentGroup[] {
  const q=query.trim().toLowerCase();
  return decks.flatMap(deck=>{
    const agents=enabledAgentsOf(deck);if(!q)return agents.length?[{deck,agents}]:[];
    const deckMatches=[deckLabel(deck,language),deck.name].map(name=>name.toLowerCase()).some(name=>name.startsWith(q));
    const matchingAgents=deckMatches?agents:agents.filter(agent=>[agentLabel(agent,language),agent.name].map(name=>name.toLowerCase()).some(name=>name.startsWith(q)));
    return matchingAgents.length?[{deck,agents:matchingAgents}]:[];
  });
}
