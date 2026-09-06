// [Input] One user message plus Chat-owned attachment, tool-choice, Editor, and turn callbacks.
// [Output] A single ordered ingress path shared by the composer, queued prompts, and MCP Apps UI messages.
// [Pos] Chat orchestration seam; raw useChat.sendMessage stays behind this module's caller-provided boundary.
// [Sync] 2026-09-06: centralize every user-originated Chat send before transport dispatch.

import type { CreateUIMessage, UIMessage } from 'ai';

import type { ToolChoice } from '../../lib/chat-schema';

export type ChatUserMessage = CreateUIMessage<UIMessage>;

export type CoordinatedChatSendOptions<TAttachment> = Readonly<{
  rawAttachments?: TAttachment[];
  toolChoice?: ToolChoice;
}>;

export type CoordinatedChatSendDependencies<TAttachment> = Readonly<{
  onConversationStart?: () => void;
  setToolChoice: (toolChoice: ToolChoice) => void;
  setPendingData: (value: Readonly<{
    rawAttachments: TAttachment[];
    toolChoice: ToolChoice;
  }>) => void;
  ensureEditorSessionPersisted?: () => Promise<void>;
  incrementTurnGeneration: () => void;
  dispatch: (message: ChatUserMessage) => Promise<void>;
}>;

export async function sendCoordinatedChatUserMessage<TAttachment>(
  message: ChatUserMessage,
  options: CoordinatedChatSendOptions<TAttachment>,
  dependencies: CoordinatedChatSendDependencies<TAttachment>,
): Promise<boolean> {
  if (!Array.isArray(message.parts) || message.parts.length === 0) return false;
  const toolChoice = options.toolChoice ?? 'auto';
  dependencies.onConversationStart?.();
  dependencies.setToolChoice(toolChoice);
  dependencies.setPendingData({
    rawAttachments: options.rawAttachments ?? [],
    toolChoice,
  });
  await dependencies.ensureEditorSessionPersisted?.();
  dependencies.incrementTurnGeneration();
  await dependencies.dispatch(message);
  return true;
}
