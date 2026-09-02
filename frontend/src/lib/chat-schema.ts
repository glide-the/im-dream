// [Input] Consume AI SDK message and usage types for chat request/metadata contracts.
// [Output] Define frontend chat transport request body, attachment, model, tool, and metadata types.
// [Pos] chat-schema type node in frontend/src/lib
// [Sync] 2026-05-25: remove frontend customer-context request fields from the chat schema.
// [Sync] 2026-08-17: expose per-message Deck/Agent provenance used by same-Deck Agent switching.
// [Sync] 2026-09-01: type the visible server-owned Dream auto-repair message metadata.
// [Sync] 2026-09-01: carry canonical trusted/stale cleanup facts on project-root repairs.
// [Sync] 2026-09-02: type server-owned turn completion/final/duration metadata
//                    used by the shared historical assistant turn projector.
// [Sync] 2026-09-02: type read-only final projection flags used to defer process hydration.
import type { LanguageModelUsage, UIMessage } from 'ai';

export type ChatAttachment = {
  type: 'file' | 'source-url';
  url: string;
  storageKey?: string;
  mediaType?: string;
  filename?: string;
  size?: number;
  workspacePath?: string;
  savedAt?: string;
  hash?: string;
};

export type ChatModel = { provider: string; model: string };
export const DEFAULT_CHAT_MODEL: ChatModel = {
  provider: 'anthropic',
  model: 'claude-sonnet-4-20250514',
};

export type ToolChoice = 'auto' | 'none' | 'manual';

export type ChatApiSchemaRequestBody = {
  id: string;
  /** Parent Deck provides the selected Agent's plugin/runtime context. */
  deckId?: string;
  /** Agent within the parent Deck that supplies the persona prompt. */
  voiceId?: string;
  resume?: boolean;
  message: UIMessage;
  chatModel?: ChatModel;
  toolChoice?: ToolChoice;
  attachments?: ChatAttachment[];
  systemPrompt?: string;
  allowedMcpServers?: Record<string, unknown>;
  allowedAppDefaultToolkit?: string[];
  /** Current EditorState snapshot — enables .editor/ virtual index redirect in the agent runner. */
  editor_state?: Record<string, unknown>;
};

export type ChatMetadata = {
  usage?: LanguageModelUsage;
  chatModel?: ChatModel;
  toolChoice?: ToolChoice;
  toolCount?: number;
  agentId?: string;
  workspacePath?: string;
  workspaceSessionId?: string;
  deckId?: string;
  voiceId?: string;
  kind?: string;
  schemaVersion?: string;
  originatingMessageId?: string;
  originatingTurnId?: string;
  workflowRunId?: string;
  repairAttempt?: number;
  validationCode?: string;
  idempotencyKey?: string;
  dispatch_status?: 'dispatching' | 'dispatched' | 'failed';
  is_partial?: boolean;
  turnId?: string;
  turnStatus?: 'completed' | 'cancelled' | 'error';
  finalPartIndex?: number;
  durationMs?: number;
  turnProjectionInvalid?: boolean;
  historyProjectionVersion?: 1;
  historyProcessAvailable?: boolean;
  projectCleanup?: {
    trustedProjectSlug: string;
    staleProjectSlugs: string[];
  };
};

/** Voice / deck info displayed in the Chat view and forwarded to the backend as voice context. */
export interface ActiveChatVoice {
  id?: string;
  name: string;
  systemPrompt: string;
  icon: string;
  color: string;
}
