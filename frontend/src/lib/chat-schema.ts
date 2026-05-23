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
  resume?: boolean;
  message: UIMessage;
  chatModel?: ChatModel;
  toolChoice?: ToolChoice;
  attachments?: ChatAttachment[];
  contextCustomerIds?: string[];
  systemPrompt?: string;
  allowedMcpServers?: Record<string, unknown>;
  allowedAppDefaultToolkit?: string[];
};

export type ChatMetadata = {
  usage?: LanguageModelUsage;
  chatModel?: ChatModel;
  toolChoice?: ToolChoice;
  toolCount?: number;
  agentId?: string;
  workspacePath?: string;
  workspaceSessionId?: string;
};
