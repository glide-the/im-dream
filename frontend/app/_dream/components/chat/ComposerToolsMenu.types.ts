// [Sync] 2026-11-13: menu receives Thread tools and selection callback independently from connection state.
// [Input] Original tool mode, IM Agent catalog/selection and caller-owned navigation/visibility.
// [Output] Shared Web/native tool panel presentation props.
// [Pos] Chat tools component boundary; Thread choice descriptors stay separate from connection configuration.
import type {ChatToolDescriptor,ToolChoice} from '../../lib/chat-schema';
import type {DeckChatSelectorProps} from '../deck/deckAgentSelection';
export interface ComposerToolsMenuProps {
  tools?:readonly ChatToolDescriptor[];onToolsChange?:(tools:readonly ChatToolDescriptor[])=>void;
  toolChoice:ToolChoice;onToolChoice:(choice:ToolChoice)=>void;
  fullAccessEnabled:boolean;disabled?:boolean;loading?:boolean;onManageTools?:()=>void;active?:boolean;
  /** Existing caller-owned IM catalog and Agent selection; this menu owns presentation only. */
  agentSelection?:DeckChatSelectorProps;
}
