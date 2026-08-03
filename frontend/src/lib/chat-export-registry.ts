// [Input] ChatPanel registers a live export snapshot getter per threadId.
// [Output] ChatView share/export flow reads the current in-memory messages, the pending
//          tool confirmation (ToolConfirmationDock state), and the effective tool choice.
// [Pos] chat-export registry node in frontend/src/lib
// [Sync] 2026-08-03: created for the share dialog long-image export — ChatPanel owns the
//                    live useChat message state, so the export flow pulls a snapshot through
//                    this registry instead of lifting message state up to ChatView.
// [Sync] 2026-08-03: snapshot now also carries pendingConfirmation + toolChoice so the
//                    exported long image can render reasoning/tool blocks and the pending
//                    ToolConfirmationDock card at the bottom.
import type { UIMessage } from 'ai';
import type { PendingToolConfirmation } from '../components/chat/toolConfirmation';

export interface ChatExportSnapshot {
  messages: UIMessage[];
  /** The single pending confirmation currently shown in ToolConfirmationDock, if any. */
  pendingConfirmation: PendingToolConfirmation | null;
  /** Effective tool choice — needed to re-derive per-part pending badges on tool rows. */
  toolChoice: string;
}

type ChatExportSource = () => ChatExportSnapshot;

const sources = new Map<string, ChatExportSource>();

/** Register a live snapshot getter for a thread. Returns an unregister cleanup. */
export function registerChatExportSource(threadId: string, getSnapshot: ChatExportSource): () => void {
  sources.set(threadId, getSnapshot);
  return () => {
    if (sources.get(threadId) === getSnapshot) {
      sources.delete(threadId);
    }
  };
}

/** Snapshot the current export state for a thread (empty when no panel is mounted). */
export function getChatExportSnapshot(threadId: string): ChatExportSnapshot {
  return sources.get(threadId)?.() ?? { messages: [], pendingConfirmation: null, toolChoice: 'auto' };
}
