// [Input] Original Deck/Agent catalog and caller-owned selected Agent ID.
// [Output] Current enabled Agent for the combined trigger; original catalog eligibility remains authoritative.
// [Pos] Pure presentation projection shared by Web/native migrated Agent selectors.
import {enabledAgentsOf,type DeckChatSelectorProps} from '../deck/deckAgentSelection';
export function selectedComposerAgent(selection?:DeckChatSelectorProps){
  return selection?.decks.flatMap(deck=>enabledAgentsOf(deck)).find(agent=>agent.id===selection.selectedAgentId);
}
