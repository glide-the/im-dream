import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useChat } from '@ai-sdk/react';
import {
  DefaultChatTransport,
  isToolUIPart,
  type FileUIPart,
  type TextUIPart,
  type UIMessage,
} from 'ai';
import { useWorkspaceSession } from '../../contexts/WorkspaceContext';
import {
  type ChatApiSchemaRequestBody,
  type ChatAttachment,
  type ChatModel,
  DEFAULT_CHAT_MODEL,
} from '../../lib/chat-schema';
import { toFileProxyUrl } from '../../lib/toFileProxyUrl';
import AIInputDock, {
  type Attachment,
  type ContextCustomer,
  type ToolChoice,
  toAttachment,
} from './AIInputDock';
import ChatMessageList from './ChatMessageList';

interface ConversationMessage {
  id: string;
  role: UIMessage['role'];
  parts: UIMessage['parts'];
  created_at: string;
}

interface ConversationResponse {
  data?: { messages?: ConversationMessage[] };
  messages?: ConversationMessage[];
}

interface SystemConfigData {
  provider?: string;
  model?: string;
  system_prompt?: string;
}

interface SystemConfigResponse {
  data?: SystemConfigData;
  provider?: string;
  model?: string;
  system_prompt?: string;
}

interface ChatPanelProps {
  threadId: string;
  contextCustomerId?: string;
  contextCustomers: ContextCustomer[];
  initialMessages?: ConversationMessage[];
  isLoading?: boolean;
  className?: string;
  inputPlaceholder?: string;
  queuedPrompt?: string;
  queuedAttachments?: Attachment[];
  queuedPromptNonce?: number;
  openFileDialogSignal?: number;
}

function mapConversationToUiMessages(conversationMessages: ConversationMessage[]): UIMessage[] {
  return conversationMessages.map((message) => ({
    id: message.id,
    role: message.role,
    parts: message.parts,
    createdAt: new Date(message.created_at),
  }));
}

function normalizeConversationResponse(payload: ConversationResponse): ConversationMessage[] {
  return payload.data?.messages ?? payload.messages ?? [];
}

function normalizeSystemConfig(payload: SystemConfigResponse): SystemConfigData | undefined {
  if (payload.data) {
    return payload.data;
  }
  if (payload.provider || payload.model || payload.system_prompt) {
    return payload;
  }
  return undefined;
}

export default function ChatPanel({
  threadId,
  contextCustomerId,
  contextCustomers,
  initialMessages,
  isLoading = false,
  className,
  inputPlaceholder = 'Press i to chat',
  queuedPrompt,
  queuedAttachments = [],
  queuedPromptNonce,
  openFileDialogSignal,
}: ChatPanelProps) {
  const pendingDataRef = useRef<{
    rawAttachments: Attachment[];
    contextCustomerIds: string[];
    toolChoice: ToolChoice;
  } | null>(null);
  const [currentToolChoice, setCurrentToolChoice] = useState<ToolChoice>('auto');
  const [systemConfig, setSystemConfig] = useState<SystemConfigData>();
  const [conversationMessages, setConversationMessages] = useState<ConversationMessage[] | null>(null);
  const [isConversationLoading, setIsConversationLoading] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const hasInitializedRef = useRef(false);
  const lastQueuedNonceRef = useRef<number | undefined>(undefined);
  const { setActiveSessionId } = useWorkspaceSession();

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch('/api/system-config');
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as SystemConfigResponse;
        if (active) {
          setSystemConfig(normalizeSystemConfig(payload));
        }
      } catch {
        // ignore config fetch errors
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const targetId = contextCustomerId ?? threadId;
    setIsConversationLoading(true);
    void (async () => {
      try {
        const response = await fetch(`/api/conversations?customerId=${encodeURIComponent(targetId)}`);
        if (!response.ok) {
          if (active) {
            setConversationMessages([]);
          }
          return;
        }
        const payload = (await response.json()) as ConversationResponse;
        if (active) {
          setConversationMessages(normalizeConversationResponse(payload));
        }
      } catch {
        if (active) {
          setConversationMessages([]);
        }
      } finally {
        if (active) {
          setIsConversationLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [contextCustomerId, threadId]);

  const getPendingData = () => pendingDataRef.current;

  const { messages, sendMessage, setMessages, status, error, addToolResult, stop } = useChat({
    id: threadId,
    transport: new DefaultChatTransport({
      api: '/api/claude-agent',
      prepareSendMessagesRequest: ({ messages: outgoingMessages, body, id }) => {
        const lastMessage = outgoingMessages.at(-1) as UIMessage | undefined;
        if (!lastMessage) {
          return { body: body ?? {} };
        }

        const attachments: ChatAttachment[] = (getPendingData()?.rawAttachments ?? [])
          .filter((file) => file.storageKey)
          .map((file) => ({
            type: 'file',
            url: toFileProxyUrl(file.storageKey!),
            storageKey: file.storageKey,
            mediaType: file.type,
            filename: file.name,
            size: file.size,
            workspacePath: file.workspacePath,
            savedAt: file.savedAt,
            hash: file.hash,
          }));

        const resolvedChatModel: ChatModel = systemConfig?.provider && systemConfig?.model
          ? { provider: systemConfig.provider, model: systemConfig.model }
          : DEFAULT_CHAT_MODEL;

        const requestBody: ChatApiSchemaRequestBody = {
          id,
          message: lastMessage,
          chatModel: resolvedChatModel,
          toolChoice: getPendingData()?.toolChoice ?? currentToolChoice,
          allowedAppDefaultToolkit: [],
          allowedMcpServers: {},
          attachments,
          contextCustomerIds: getPendingData()?.contextCustomerIds ?? (contextCustomerId ? [contextCustomerId] : contextCustomers.map((customer) => customer.id)),
          systemPrompt: systemConfig?.system_prompt,
        };

        setTimeout(() => {
          pendingDataRef.current = null;
        }, 0);
        return { body: requestBody };
      },
    }),
    generateId: () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`,
    experimental_throttle: 100,
  });

  useEffect(() => {
    setActiveSessionId(threadId);
    return () => {
      setActiveSessionId((current) => (current === threadId ? null : current));
    };
  }, [setActiveSessionId, threadId]);

  useEffect(() => {
    if (hasInitializedRef.current) {
      return;
    }
    const baseMessages = initialMessages ?? conversationMessages ?? [];
    if (baseMessages.length > 0) {
      setMessages(mapConversationToUiMessages(baseMessages));
      hasInitializedRef.current = true;
    }
  }, [conversationMessages, initialMessages, setMessages]);

  useEffect(() => {
    if (!queuedPromptNonce || queuedPromptNonce === lastQueuedNonceRef.current) {
      return;
    }
    if (!queuedPrompt?.trim() && queuedAttachments.length === 0) {
      return;
    }
    lastQueuedNonceRef.current = queuedPromptNonce;

    void (async () => {
      setCurrentToolChoice('auto');
      pendingDataRef.current = {
        rawAttachments: queuedAttachments,
        contextCustomerIds: contextCustomerId ? [contextCustomerId] : contextCustomers.map((customer) => customer.id),
        toolChoice: 'auto',
      };

      const validFiles = queuedAttachments.filter((file) => file.storageKey);
      const queuedMessageParts: Array<FileUIPart | TextUIPart> = validFiles.map((file) => ({
        type: 'file',
        url: toFileProxyUrl(file.storageKey!),
        mediaType: file.type,
        filename: file.name,
      } as FileUIPart));

      if (queuedPrompt?.trim()) {
        queuedMessageParts.push({ type: 'text', text: queuedPrompt.trim() } as TextUIPart);
      }

      if (queuedMessageParts.length === 0) {
        return;
      }
      await sendMessage({ role: 'user', parts: queuedMessageParts });
    })();
  }, [contextCustomerId, contextCustomers, queuedAttachments, queuedPrompt, queuedPromptNonce, sendMessage]);

  const chatLoading = status === 'streaming' || status === 'submitted' || isLoading || isConversationLoading;

  const shouldShowLoadingIndicator = useMemo(() => {
    if (!chatLoading || messages.length === 0) {
      return false;
    }
    const lastMessage = messages.at(-1);
    const hasVisibleParts = lastMessage?.parts?.some((part) => part.type === 'text' || isToolUIPart(part));
    return !hasVisibleParts;
  }, [chatLoading, messages]);

  const handleScroll = useCallback(() => {
    const element = chatContainerRef.current;
    if (!element) {
      return;
    }
    isNearBottomRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 100;
  }, []);

  useEffect(() => {
    if (isNearBottomRef.current) {
      requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      });
    }
  }, [messages, status]);

  return (
    <div className={className} style={{ display: 'flex', minHeight: 0, flex: 1, flexDirection: 'column', overflow: 'hidden' }}>
      <div ref={chatContainerRef} onScroll={handleScroll} style={{ minHeight: 0, flex: 1, overflowY: 'auto', borderRadius: '1.5rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '1rem 1rem 1.5rem' }}>
        <ChatMessageList
          messages={messages}
          isLoading={chatLoading}
          error={error}
          addToolResult={addToolResult}
          shouldShowLoadingIndicator={shouldShowLoadingIndicator}
          setMessages={setMessages}
          sendMessage={sendMessage}
        />
        <div ref={bottomRef} aria-hidden="true" />
      </div>

      <div style={{ position: 'relative', zIndex: 10, width: '100%', maxWidth: '48rem', margin: '0.75rem auto 0', flexShrink: 0, paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.5rem)' }}>
        <AIInputDock
          contextCustomerId={contextCustomerId}
          contextCustomers={contextCustomers}
          openFileDialogSignal={openFileDialogSignal}
          onSendMessage={async (message, uploadedFiles = [], customerIds = [], toolChoice = 'auto') => {
            setCurrentToolChoice(toolChoice);
            pendingDataRef.current = {
              rawAttachments: uploadedFiles.map(toAttachment),
              contextCustomerIds: customerIds.length > 0 ? customerIds : contextCustomers.map((customer) => customer.id),
              toolChoice,
            };

            const validFiles = uploadedFiles.filter((file) => file.storageKey);
            const parts: Array<FileUIPart | TextUIPart> = validFiles.map((file) => ({
              type: 'file',
              url: toFileProxyUrl(file.storageKey!),
              mediaType: file.mimeType,
              filename: file.name,
            } as FileUIPart));
            if (message) {
              parts.push({ type: 'text', text: message } as TextUIPart);
            }
            if (parts.length === 0) {
              return;
            }
            await sendMessage({ role: 'user', parts });
          }}
          placeholder={inputPlaceholder}
          loading={chatLoading}
          onStop={status === 'streaming' ? stop : undefined}
          workspaceSessionId={threadId}
          mode="full"
        />
      </div>
    </div>
  );
}
