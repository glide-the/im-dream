// [Input] Consume ClaudeAgentChatTransport, WorkspaceContext, chat schema/types, file proxy utilities, AIInputDock/helpers, ChatMessageList, and auth token.
// [Output] Coordinate chat transport, pending attachments/tool choice, message state, scrolling, and input/message layout.
// [Pos] chat-panel component node in frontend/src/components/chat
// [Sync] 2026-05-25: stop forwarding frontend customer context into chat requests.
// [Sync] 2026-05-26: hide the empty message surface until chat content or an error exists.
// [Sync] 2026-05-27: forward currentToolChoice to ChatMessageList so manual-mode tool approvals are shown inline.
// [Sync] 2026-05-29: accept editorState prop and forward as editor_state in prepareSendMessagesRequest body.
// [Sync] 2026-05-29: default resume=true in every claude-agent request body.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useChat } from '@ai-sdk/react';
import {
  isToolUIPart,
  type FileUIPart,
  type TextUIPart,
  type UIMessage,
} from 'ai';
import { ClaudeAgentChatTransport } from '../../lib/claude-agent-transport';
import { useWorkspaceSession } from '../../contexts/WorkspaceContext';
import {
  type ChatApiSchemaRequestBody,
  type ChatAttachment,
  type ChatModel,
  type ToolChoice,
  DEFAULT_CHAT_MODEL,
} from '../../lib/chat-schema';
import { toFileProxyUrl } from '../../lib/toFileProxyUrl';
import {
  type Attachment,
  toAttachment,
} from './AIInputDock.helpers';
import AIInputDock from './AIInputDock';
import ChatMessageList from './ChatMessageList';
import { getAuthToken } from '../../contexts/AuthContext';

const API_BASE = '/ink-and-memory';

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
  initialMessages?: UIMessage[];
  isLoading?: boolean;
  className?: string;
  inputPlaceholder?: string;
  queuedPrompt?: string;
  queuedAttachments?: Attachment[];
  queuedPromptNonce?: number;
  openFileDialogSignal?: number;
  onConversationStart?: () => void;
  /** Current EditorState snapshot forwarded to the backend agent runner via editor_state request field. */
  editorState?: Record<string, unknown> | null;
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
  initialMessages,
  isLoading = false,
  className,
  inputPlaceholder = 'Press i to chat',
  queuedPrompt,
  queuedAttachments = [],
  queuedPromptNonce,
  openFileDialogSignal,
  onConversationStart,
  editorState,
}: ChatPanelProps) {
  const pendingDataRef = useRef<{
    rawAttachments: Attachment[];
    toolChoice: ToolChoice;
  } | null>(null);
  const [currentToolChoice, setCurrentToolChoice] = useState<ToolChoice>('auto');
  const [systemConfig, setSystemConfig] = useState<SystemConfigData>();
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
        const response = await fetch(`${API_BASE}/api/system-config`, {
          headers: { 'Authorization': `Bearer ${getAuthToken()}` },
        });
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

  const getPendingData = () => pendingDataRef.current;

  const { messages, sendMessage, setMessages, status, error, addToolResult, stop } = useChat({
    id: threadId,
    transport: new ClaudeAgentChatTransport({
      api: `${API_BASE}/api/claude-agent`,
      headers: () => ({ 'Authorization': `Bearer ${getAuthToken()}` }),
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
          resume: true,
          message: lastMessage,
          chatModel: resolvedChatModel,
          toolChoice: getPendingData()?.toolChoice ?? currentToolChoice,
          allowedAppDefaultToolkit: [],
          allowedMcpServers: {},
          attachments,
          systemPrompt: systemConfig?.system_prompt,
          ...(editorState != null ? { editor_state: editorState } : {}),
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

  // Initialise the chat with messages provided by the parent (following the
  // better-chatbot pattern: parent fetches history, passes as initialMessages).
  useEffect(() => {
    if (hasInitializedRef.current) {
      return;
    }
    if (!initialMessages) {
      return;
    }
    if (initialMessages.length > 0) {
      setMessages(initialMessages);
    }
    hasInitializedRef.current = true;
  }, [initialMessages, setMessages]);

  useEffect(() => {
    if (!queuedPromptNonce || queuedPromptNonce === lastQueuedNonceRef.current) {
      return;
    }
    if (!queuedPrompt?.trim() && queuedAttachments.length === 0) {
      return;
    }
    lastQueuedNonceRef.current = queuedPromptNonce;

    void (async () => {
      onConversationStart?.();
      setCurrentToolChoice('auto');
      pendingDataRef.current = {
        rawAttachments: queuedAttachments,
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
  }, [onConversationStart, queuedAttachments, queuedPrompt, queuedPromptNonce, sendMessage]);

  const chatLoading = status === 'streaming' || status === 'submitted' || isLoading;
  const shouldShowMessageSurface = messages.length > 0 || Boolean(error);

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
    <div className={className} style={{ display: 'flex', minHeight: 0, flex: 1, flexDirection: 'column', justifyContent: shouldShowMessageSurface ? 'flex-start' : 'flex-end', overflow: 'hidden' }}>
      {shouldShowMessageSurface ? (
        <div ref={chatContainerRef} onScroll={handleScroll} style={{ minHeight: 0, flex: 1, overflowY: 'auto', borderRadius: '1.5rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '1rem 1rem 1.5rem' }}>
          <ChatMessageList
            messages={messages}
            threadId={threadId}
            isLoading={chatLoading}
            error={error}
            addToolResult={addToolResult}
            shouldShowLoadingIndicator={shouldShowLoadingIndicator}
            toolChoice={currentToolChoice}
            setMessages={setMessages}
            sendMessage={sendMessage}
          />
          <div ref={bottomRef} aria-hidden="true" />
        </div>
      ) : null}

      <div style={{ position: 'relative', zIndex: 10, width: '100%', maxWidth: '48rem', margin: '0.75rem auto 0', flexShrink: 0, paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.5rem)' }}>
        <AIInputDock
          openFileDialogSignal={openFileDialogSignal}
          onSendMessage={async (message, uploadedFiles = [], toolChoice = 'auto') => {
            onConversationStart?.();
            setCurrentToolChoice(toolChoice);
            pendingDataRef.current = {
              rawAttachments: uploadedFiles.map(toAttachment),
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
