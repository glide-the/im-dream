// [Input] Consume ClaudeAgentChatTransport, WorkspaceContext, chat schema/types, file proxy utilities, AIInputDock/helpers, ChatMessageList, and auth token.
//         reconnectStreamNonce from ChatView; claude-agent-sse-utils for stream replay.
// [Output] Coordinate chat transport, pending attachments/tool choice, message state, scrolling, and input/message layout.
// [Pos] chat-panel component node in frontend/src/components/chat
// [Sync] 2026-05-25: stop forwarding frontend customer context into chat requests.
// [Sync] 2026-05-26: hide the empty message surface until chat content or an error exists.
// [Sync] 2026-05-27: forward currentToolChoice to ChatMessageList so manual-mode tool approvals are shown inline.
// [Sync] 2026-05-29: accept editorState prop and forward as editor_state in prepareSendMessagesRequest body.
// [Sync] 2026-05-29: default resume=true in every claude-agent request body.
// [Sync] 2026-05-30: fix shouldShowLoadingIndicator — include reasoning parts as visible so "Thinking…" footer doesn't show alongside inline reasoning block.
// [Sync] 2026-05-29: add onEditorWriteConfirmed prop; forward to ChatMessageList.
// [Sync] 2026-05-29: let the input dock fill the available chat page width.
// [Sync] 2026-06-01: accept queuedToolChoice so lazy-created first-turn ChatView sends preserve the selected tool mode.
// [Sync] 2026-06-09: read system_config.im_full_access_enabled; hide manual
//                    approvals by forcing chat UI tool mode to auto when enabled.
// [Sync] 2026-06-09: subscribe to same-tab IM full-access config events so
//                    Settings changes update active Chat panels immediately.
// [Sync] 2026-06-09: SSE reconnect — subscribe GET /threads/{id}/stream when reconnectStreamNonce bumps.
// [Sync] 2026-06-09: keep reconnect effect deps stable (threadId/nonce only) so parent re-renders do not abort stream.
// [Sync] 2026-06-09: agentBusy drives input dock stop button (streaming/submitted/reconnect).
// [Sync] 2026-06-09: show a floating scroll-to-bottom arrow above AIInputDock when the message list is scrolled away from the bottom.
// [Sync] 2026-06-12: use centralized API_BASE for cross-origin chat transport and SSE reconnect.
// [Sync] 2026-06-14: forward editor write toolCallId for event-driven Writing view reload de-duplication.
// [Sync] 2026-06-22: respect Workspace Mode by withholding workspaceSessionId
//                    from the input dock when workspace is disabled.
// [Sync] 2026-06-25: stop button now calls the backend thread stop endpoint
//                    instead of only aborting the local browser stream.
// [Sync] 2026-07-20: pass threadId into ClaudeAgentChatTransport so plan-* SSE
//                    frames route to the useThreadPlan store (claude-plan feature).
// [Sync] 2026-07-20: forward todo-updated SSE frames to the useThreadTodos store
//                    on the reconnect path (claude-todo §5.6).
// [Sync] 2026-07-20: derive pendingConfirmation from messages and swap AIInputDock for
//                    ToolConfirmationDock while a confirmation is pending (the composer
//                    hides until the user decides); inline approval/askuser UIs removed
//                    from the message list (design: claude-agent-tool-confirmation-flow.md §8).
// [Sync] 2026-07-20: i18n — scroll-to-bottom aria/title resolves through chat.panel.scrollToBottom.
// [Sync] 2026-07-23: SandboxPermissionRequest — pendingConfirmation carries the backend
//                    networkRequest metadata for kind==='sandbox-network' so ToolConfirmationDock
//                    renders the network-variant card (claude-agent-sandbox-network-permission-tool.md §5).
// [Sync] 2026-08-03: register a live message getter in chat-export-registry for the share
//                    dialog long-image export.
// [Sync] 2026-08-04: forward Agent/Task chat-row navigation to ChatView's subagent sidebar.
// [Sync] 2026-08-11: claim parent-owned queued first turns before send so a ChatPanel
//                    history-load remount cannot replay the same /api/claude-agent POST.
// [Sync] 2026-08-11: keep the composer bound to the main thread runtime;
//                    transcript-derived subagent counts are observation-only.
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useChat } from '@ai-sdk/react';
import {
  getToolName,
  isToolUIPart,
  type DynamicToolUIPart,
  type FileUIPart,
  type TextUIPart,
  type ToolUIPart,
  type UIMessage,
} from 'ai';
import { ClaudeAgentChatTransport } from '../../lib/claude-agent-transport';
import { useWorkspaceSession } from '../../contexts/WorkspaceContext';
import {
  type ChatApiSchemaRequestBody,
  type ChatAttachment,
  type ToolChoice,
} from '../../lib/chat-schema';
import { toFileProxyUrl } from '../../lib/toFileProxyUrl';
import {
  type Attachment,
  toAttachment,
} from './AIInputDock.helpers';
import AIInputDock from './AIInputDock';
import ChatMessageList from './ChatMessageList';
import ToolConfirmationDock from './ToolConfirmationDock';
import {
  resolvePendingToolConfirmation,
  resolveSandboxNetworkRequest,
  resolveToolName,
  type PendingToolConfirmation,
} from './toolConfirmation';
import { getAuthToken } from '../../contexts/AuthContext';
import { registerChatExportSource } from '../../lib/chat-export-registry';
import { subscribeImFullAccessChanged } from '../../lib/system-config-events';
import {
  publishStoryWorkspaceOutput,
  type StoryWorkspaceOutputReceipt,
} from '../../lib/story-workspace-events';
import {
  claudeThreadHydrationRetryDelayMs,
  fetchClaudeThreadStatus,
  filterClaudeThreadVisibleMessages,
} from './threadSessionHydration';
import {
  applyBackendEventToMessages,
  coalesceClaudeAgentSseEvents,
  consumeClaudeAgentSseStream,
  type BackendEvent,
} from '../../lib/claude-agent-sse-utils';
import { applyPlanEvent, type ThreadPlanEvent } from '../../hooks/useThreadPlan';
import { applyTodoEvent, type ThreadTodoEvent } from '../../hooks/useThreadTodos';
import { IconArrowDown } from './Icons';
import {
  shouldApplyChatHistoryRecoverySnapshot,
  type ChatHistoryRecoveryCheckpoint,
} from './chatRecovery';
import { API_BASE } from '../../lib/apiBase';
import {
  chatMainTurnCanStop,
  claimChatReconnect,
  chatStopMayAbortLocalReaders,
  parseThreadStopResponse,
} from './chatRuntimeState';
const CHAT_BOTTOM_PROXIMITY_PX = 120;
const EMPTY_TOOL_CALL_IDS: ReadonlySet<string> = new Set<string>();

interface SystemConfigData {
  system_prompt?: string;
  im_full_access_enabled?: boolean;
}

interface SystemConfigResponse {
  data?: SystemConfigData;
  system_prompt?: string;
  im_full_access_enabled?: boolean;
}

interface ChatPanelProps {
  threadId: string;
  initialMessages?: UIMessage[];
  isLoading?: boolean;
  /** Incremented by ChatView when /status reports lifecycle=running — triggers SSE reconnect. */
  reconnectStreamNonce?: number;
  /** Exact historical tool calls proven absent from the runtime confirmation store. */
  initialSettledToolCallIds?: ReadonlySet<string>;
  /** Exact historical tool calls still owned by the active runtime turn. */
  initialRuntimePendingToolCallIds?: ReadonlySet<string>;
  /** Authoritative main-turn status sampled after history hydration. */
  initialRuntimeRunning?: boolean;
  /** Called after reconnect stream finishes so parent can reload persisted messages. */
  onReconnectComplete?: () => (
    Promise<ChatPanelRecoverySnapshot | undefined>
    | ChatPanelRecoverySnapshot
    | undefined
  );
  className?: string;
  inputPlaceholder?: string;
  queuedPrompt?: string;
  queuedAttachments?: Attachment[];
  queuedToolChoice?: ToolChoice;
  queuedPromptNonce?: number;
  /**
   * Parent-owned at-most-once gate for queued sends. ChatPanel-local refs do not
   * survive the history-load remount that follows lazy thread creation.
   */
  claimQueuedPrompt?: (nonce: number) => boolean;
  openFileDialogSignal?: number;
  onConversationStart?: () => void;
  /** Called after direct or reconnected turns settle and persistence is rehydrated. */
  onConversationSettled?: () => void;
  /** Current EditorState snapshot forwarded to the backend agent runner via editor_state request field. */
  editorState?: Record<string, unknown> | null;
  /** Called after an editor write tool is confirmed so the Writing view can reload from the database. */
  onEditorWriteConfirmed?: (toolCallId: string) => void;
  /** Opens the right-side subagent detail panel for a chat tool invocation. */
  onOpenSubagentTask?: (toolCallId: string) => void;
  /** Voice / deck system prompt injected as voice_context into each user message. */
  voiceSystemPrompt?: string;
  /** Immutable Deck selection for this thread. */
  deckId?: string;
  /** Immutable Agent selection within the Deck. */
  voiceId?: string;
  /** Compact Deck provenance control rendered beside the composer controls. */
  inputContextControl?: ReactNode;
}

export interface ChatPanelRecoverySnapshot {
  messages: UIMessage[];
  settledToolCallIds: ReadonlySet<string>;
  runtimePendingToolCallIds: ReadonlySet<string>;
  running: boolean;
}

function normalizeSystemConfig(payload: SystemConfigResponse): SystemConfigData | undefined {
  if (payload.data) {
    return payload.data;
  }
  if (
    payload.system_prompt ||
    payload.im_full_access_enabled !== undefined
  ) {
    return payload;
  }
  return undefined;
}

export default function ChatPanel({
  threadId,
  initialMessages,
  isLoading = false,
  reconnectStreamNonce = 0,
  initialSettledToolCallIds = EMPTY_TOOL_CALL_IDS,
  initialRuntimePendingToolCallIds = EMPTY_TOOL_CALL_IDS,
  initialRuntimeRunning = false,
  onReconnectComplete,
  className,
  inputPlaceholder = 'Press i to chat',
  queuedPrompt,
  queuedAttachments = [],
  queuedToolChoice = 'auto',
  queuedPromptNonce,
  claimQueuedPrompt,
  openFileDialogSignal,
  onConversationStart,
  onConversationSettled,
  editorState,
  onEditorWriteConfirmed,
  onOpenSubagentTask,
  voiceSystemPrompt,
  deckId,
  voiceId,
  inputContextControl,
}: ChatPanelProps) {
  const { t } = useTranslation();
  const pendingDataRef = useRef<{
    rawAttachments: Attachment[];
    toolChoice: ToolChoice;
  } | null>(null);
  const [currentToolChoice, setCurrentToolChoice] = useState<ToolChoice>('auto');
  const [systemConfig, setSystemConfig] = useState<SystemConfigData>();
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const hasInitializedRef = useRef(false);
  const turnGenerationRef = useRef(0);
  const lastQueuedNonceRef = useRef<number | undefined>(undefined);
  const lastReconnectNonceRef = useRef(0);
  const lastReconnectCountersRef = useRef({ external: 0, retry: 0 });
  const onReconnectCompleteRef = useRef(onReconnectComplete);
  const onConversationSettledRef = useRef(onConversationSettled);
  const setMessagesRef = useRef<
    ((value: UIMessage[] | ((messages: UIMessage[]) => UIMessage[])) => void) | null
  >(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [settledToolCallIds, setSettledToolCallIds] = useState<ReadonlySet<string>>(
    () => new Set(initialSettledToolCallIds),
  );
  const [runtimePendingToolCallIds, setRuntimePendingToolCallIds] = useState<ReadonlySet<string>>(
    () => new Set(initialRuntimePendingToolCallIds),
  );
  const [runtimeRunning, setRuntimeRunning] = useState(initialRuntimeRunning);
  const [reconnectRetryNonce, setReconnectRetryNonce] = useState(0);
  const reconnectRetryTimerRef = useRef<number | null>(null);
  const reconnectRecoveryAttemptRef = useRef(0);
  const localCompletionRetryTimerRef = useRef<number | null>(null);
  const stopRequestAbortRef = useRef<AbortController | null>(null);
  const stopRequestTimerRef = useRef<number | null>(null);
  const stopRecoveryTimerRef = useRef<number | null>(null);
  const chatPanelMountedRef = useRef(true);
  const previousChatStatusRef = useRef<string>('ready');
  const reconnectAbortRef = useRef<AbortController | null>(null);
  const { setActiveSessionId, workspaceEnabled } = useWorkspaceSession();

  onReconnectCompleteRef.current = onReconnectComplete;
  onConversationSettledRef.current = onConversationSettled;

  useEffect(() => {
    chatPanelMountedRef.current = true;
    return () => {
      chatPanelMountedRef.current = false;
      stopRequestAbortRef.current?.abort();
      stopRequestAbortRef.current = null;
      reconnectAbortRef.current?.abort();
      reconnectAbortRef.current = null;
      for (const timerRef of [
        reconnectRetryTimerRef,
        localCompletionRetryTimerRef,
        stopRequestTimerRef,
        stopRecoveryTimerRef,
      ]) {
        if (timerRef.current !== null) window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

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

  useEffect(() => {
    return subscribeImFullAccessChanged((enabled) => {
      setSystemConfig((current) => ({
        ...(current ?? {}),
        im_full_access_enabled: enabled,
      }));
      if (enabled) {
        setCurrentToolChoice('auto');
      }
    });
  }, []);

  const getPendingData = () => pendingDataRef.current;
  const imFullAccessEnabled = systemConfig?.im_full_access_enabled === true;

  const { messages, sendMessage, setMessages, status, error, addToolResult, stop } = useChat({
    id: threadId,
    transport: new ClaudeAgentChatTransport({
      threadId,
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

        const requestToolChoice: ToolChoice = imFullAccessEnabled
          ? 'auto'
          : getPendingData()?.toolChoice ?? currentToolChoice;

        const requestBody: ChatApiSchemaRequestBody = {
          id,
          ...(deckId ? { deckId } : {}),
          ...(voiceId ? { voiceId } : {}),
          resume: true,
          message: lastMessage,
          toolChoice: requestToolChoice,
          allowedAppDefaultToolkit: [],
          allowedMcpServers: {},
          attachments,
          systemPrompt: voiceSystemPrompt ?? systemConfig?.system_prompt,
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

  setMessagesRef.current = setMessages;

  // DEC-032: story-workspace guidance rows persist in chat_message but must
  // never render as Chat bubbles — every render/export seam below consumes
  // visibleMessages instead of the raw useChat list (Task 4 Step 0).
  const visibleMessages = useMemo(
    () => filterClaudeThreadVisibleMessages(messages),
    [messages],
  );

  // Share/export — expose the live message snapshot to the chat-export registry so
  // ChatView's share dialog can render the current conversation as a long image
  // without lifting useChat state out of this panel. The snapshot also carries the
  // pending ToolConfirmationDock state and effective tool choice so the exported
  // image can mirror reasoning/tool blocks and the bottom confirmation card.
  const messagesForExportRef = useRef<UIMessage[]>([]);
  const pendingConfirmationForExportRef = useRef<PendingToolConfirmation | null>(null);
  const toolChoiceForExportRef = useRef<ToolChoice>('auto');
  messagesForExportRef.current = visibleMessages;
  useEffect(
    () => registerChatExportSource(threadId, () => ({
      messages: messagesForExportRef.current,
      pendingConfirmation: pendingConfirmationForExportRef.current,
      toolChoice: toolChoiceForExportRef.current,
    })),
    [threadId],
  );

  useEffect(() => {
    setActiveSessionId(threadId);
    return () => {
      setActiveSessionId((current) => (current === threadId ? null : current));
    };
  }, [setActiveSessionId, threadId]);

  // Initialise the chat with messages provided by the parent (following the
  // better-chatbot pattern: parent fetches history, passes as initialMessages).
  useEffect(() => {
    setSettledToolCallIds(new Set(initialSettledToolCallIds));
    setRuntimePendingToolCallIds(new Set(initialRuntimePendingToolCallIds));
    setRuntimeRunning(initialRuntimeRunning);
    setReconnectRetryNonce(0);
    reconnectRecoveryAttemptRef.current = 0;
    lastReconnectNonceRef.current = 0;
    lastReconnectCountersRef.current = { external: 0, retry: 0 };
    previousChatStatusRef.current = 'ready';
    turnGenerationRef.current = 0;
  // ChatView keys panels by threadId; the explicit reset also keeps direct
  // consumers safe if they reuse an instance for another thread.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  useEffect(() => {
    setSettledToolCallIds((current) => {
      const next = new Set(current);
      initialSettledToolCallIds.forEach((toolCallId) => next.add(toolCallId));
      return next.size === current.size ? current : next;
    });
  }, [initialSettledToolCallIds]);

  useEffect(() => {
    setRuntimePendingToolCallIds(new Set(initialRuntimePendingToolCallIds));
  }, [initialRuntimePendingToolCallIds]);

  useEffect(() => {
    setRuntimeRunning(initialRuntimeRunning);
  }, [initialRuntimeRunning]);

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
    if (claimQueuedPrompt && !claimQueuedPrompt(queuedPromptNonce)) {
      lastQueuedNonceRef.current = queuedPromptNonce;
      return;
    }
    lastQueuedNonceRef.current = queuedPromptNonce;

    void (async () => {
      onConversationStart?.();
      setCurrentToolChoice(queuedToolChoice);
      pendingDataRef.current = {
        rawAttachments: queuedAttachments,
        toolChoice: queuedToolChoice,
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
      turnGenerationRef.current += 1;
      await sendMessage({ role: 'user', parts: queuedMessageParts });
    })();
  }, [claimQueuedPrompt, onConversationStart, queuedAttachments, queuedPrompt, queuedPromptNonce, queuedToolChoice, sendMessage]);

  const recoverAuthoritativeHistory = useCallback(async (): Promise<ChatPanelRecoverySnapshot | undefined> => {
    const requestedAt: ChatHistoryRecoveryCheckpoint = {
      threadId,
      reconnectNonce: lastReconnectNonceRef.current,
      turnGeneration: turnGenerationRef.current,
    };
    const recovery = onReconnectCompleteRef.current?.();
    if (recovery === undefined) return undefined;
    try {
      const snapshot = await Promise.resolve(recovery);
      const current: ChatHistoryRecoveryCheckpoint = {
        threadId,
        reconnectNonce: lastReconnectNonceRef.current,
        turnGeneration: turnGenerationRef.current,
      };
      if (!snapshot) return undefined;
      const recoveredMessages = snapshot.messages;
      if (!shouldApplyChatHistoryRecoverySnapshot(requestedAt, current, recoveredMessages)) {
        return undefined;
      }
      setSettledToolCallIds((settled) => {
        const next = new Set(settled);
        snapshot.settledToolCallIds.forEach((toolCallId) => next.add(toolCallId));
        return next.size === settled.size ? settled : next;
      });
      setRuntimePendingToolCallIds(new Set(snapshot.runtimePendingToolCallIds));
      setRuntimeRunning(snapshot.running);
      setMessagesRef.current?.(recoveredMessages);
      if (!snapshot.running) onConversationSettledRef.current?.();
      return snapshot;
    } catch {
      return undefined;
    }
  }, [threadId]);

  const recoverLocalCompletion = useCallback(async (attempt = 0): Promise<void> => {
    const snapshot = await recoverAuthoritativeHistory();
    if (!chatPanelMountedRef.current) return;
    if (snapshot && !snapshot.running) return;
    setRuntimeRunning(true);
    if (snapshot?.running) {
      // The POST reader ended while the canonical turn still owns the thread.
      // Switch immediately to GET /stream instead of polling away deltas.
      setReconnectRetryNonce((value) => value + 1);
      return;
    }
    localCompletionRetryTimerRef.current = window.setTimeout(() => {
      localCompletionRetryTimerRef.current = null;
      void recoverLocalCompletion(attempt + 1);
    }, claudeThreadHydrationRetryDelayMs(attempt));
  }, [recoverAuthoritativeHistory]);

  useEffect(() => {
    const previous = previousChatStatusRef.current;
    const wasBusy = previous === 'submitted' || previous === 'streaming';
    const isBusy = status === 'submitted' || status === 'streaming';
    previousChatStatusRef.current = status;
    if (isBusy) {
      if (localCompletionRetryTimerRef.current !== null) {
        window.clearTimeout(localCompletionRetryTimerRef.current);
        localCompletionRetryTimerRef.current = null;
      }
      setRuntimeRunning(true);
      return;
    }
    if (wasBusy) void recoverLocalCompletion();
  }, [recoverLocalCompletion, status]);

  useEffect(() => {
    const reconnectClaim = claimChatReconnect(
      runtimeRunning,
      reconnectStreamNonce,
      reconnectRetryNonce,
      lastReconnectCountersRef.current,
    );
    // A retry token is meaningful only while this panel still has evidence of
    // a live main turn. Once authoritative recovery says idle, an old retry
    // must not manufacture another GET stream or a transient Stop button.
    if (reconnectClaim === null) return;
    lastReconnectCountersRef.current = reconnectClaim;
    lastReconnectNonceRef.current += 1;

    const abort = new AbortController();
    reconnectAbortRef.current = abort;
    const activeThreadId = threadId;
    let finished = false;
    let replayFrameId: number | null = null;
    let replayEvents: BackendEvent[] = [];

    const flushReplayEvents = () => {
      replayFrameId = null;
      if (replayEvents.length === 0) return;
      const events = coalesceClaudeAgentSseEvents(replayEvents);
      replayEvents = [];
      const messageEvents: BackendEvent[] = [];
      for (const event of events) {
        if (event.type === 'finish') {
          // Persistence becomes authoritative only after stream EOF.
          continue;
        }
        if (event.type === 'plan-mode-changed' || event.type === 'plan-updated') {
          applyPlanEvent(activeThreadId, event as unknown as ThreadPlanEvent);
          continue;
        }
        if (event.type === 'todo-updated') {
          applyTodoEvent(activeThreadId, event as unknown as ThreadTodoEvent);
          continue;
        }
        if (event.type === 'story-workspace-output') {
          publishStoryWorkspaceOutput(event as unknown as StoryWorkspaceOutputReceipt);
          continue;
        }
        if (event.type === 'tool-approval-request') {
          const toolCallId = String(event.toolCallId ?? '');
          if (toolCallId) {
            setSettledToolCallIds((current) => {
              if (!current.has(toolCallId)) return current;
              const next = new Set(current);
              next.delete(toolCallId);
              return next;
            });
          }
        }
        messageEvents.push(event);
      }
      const applyMessages = setMessagesRef.current;
      if (!applyMessages || messageEvents.length === 0) return;
      applyMessages((current) => messageEvents.reduce(
        (next, event) => applyBackendEventToMessages(next, event),
        current,
      ));
    };

    const enqueueReplayEvent = (event: BackendEvent) => {
      replayEvents.push(event);
      if (replayFrameId === null) {
        replayFrameId = window.requestAnimationFrame(flushReplayEvents);
      }
    };

    const finishReconnect = async () => {
      if (finished) return;
      finished = true;
      setIsReconnecting(false);
      const snapshot = await recoverAuthoritativeHistory();
      if (abort.signal.aborted) return;
      if (snapshot?.running === true) {
        reconnectRecoveryAttemptRef.current = 0;
        setReconnectRetryNonce((value) => value + 1);
      } else if (snapshot === undefined) {
        const attempt = reconnectRecoveryAttemptRef.current;
        reconnectRecoveryAttemptRef.current += 1;
        reconnectRetryTimerRef.current = window.setTimeout(() => {
          reconnectRetryTimerRef.current = null;
          setReconnectRetryNonce((value) => value + 1);
        }, claudeThreadHydrationRetryDelayMs(attempt));
      } else {
        reconnectRecoveryAttemptRef.current = 0;
      }
    };

    setRuntimeRunning(true);
    setIsReconnecting(true);

    void (async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(activeThreadId)}/stream`,
          {
            headers: { Authorization: `Bearer ${getAuthToken()}` },
            signal: abort.signal,
          },
        );
        if (!response.ok || !response.body) {
          await finishReconnect();
          return;
        }

        const reader = response.body.getReader();
        await consumeClaudeAgentSseStream(reader, enqueueReplayEvent);
        if (replayFrameId !== null) {
          window.cancelAnimationFrame(replayFrameId);
          replayFrameId = null;
        }
        flushReplayEvents();
        await finishReconnect();
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          setIsReconnecting(false);
          return;
        }
        await finishReconnect();
      } finally {
        if (reconnectAbortRef.current === abort) {
          reconnectAbortRef.current = null;
        }
      }
    })();

    return () => {
      abort.abort();
      if (replayFrameId !== null) {
        window.cancelAnimationFrame(replayFrameId);
        replayFrameId = null;
      }
      replayEvents = [];
      if (reconnectRetryTimerRef.current !== null) {
        window.clearTimeout(reconnectRetryTimerRef.current);
        reconnectRetryTimerRef.current = null;
      }
      if (reconnectAbortRef.current === abort) {
        reconnectAbortRef.current = null;
      }
      if (!finished) {
        setIsReconnecting(false);
      }
    };
  }, [reconnectRetryNonce, reconnectStreamNonce, recoverAuthoritativeHistory, runtimeRunning, threadId]);

  const canStopMainTurn = chatMainTurnCanStop(status, runtimeRunning, isReconnecting);
  const agentBusy = canStopMainTurn || isStopping;
  const chatLoading = agentBusy || isLoading;

  const markToolConfirmationSettled = useCallback((toolCallId: string) => {
    setSettledToolCallIds((current) => {
      if (current.has(toolCallId)) return current;
      const next = new Set(current);
      next.add(toolCallId);
      return next;
    });
  }, []);

  const abortLocalReaders = useCallback(() => {
    reconnectAbortRef.current?.abort();
    reconnectAbortRef.current = null;
    void stop();
  }, [stop]);

  const recoverAfterStop = useCallback(async (attempt = 0): Promise<void> => {
    if (!chatPanelMountedRef.current) return;
    let authoritativeIdle = false;
    try {
      const runtimeStatus = await fetchClaudeThreadStatus(threadId);
      authoritativeIdle = !runtimeStatus.running;
    } catch {
      // Unknown is not idle. Preserve the lock and last-good transcript.
    }
    if (!chatPanelMountedRef.current) return;
    if (chatStopMayAbortLocalReaders(null, !authoritativeIdle)) {
      abortLocalReaders();
      const recovered = await recoverAuthoritativeHistory();
      if (recovered && !recovered.running) return;
    }
    setRuntimeRunning(true);
    stopRecoveryTimerRef.current = window.setTimeout(() => {
      stopRecoveryTimerRef.current = null;
      void recoverAfterStop(attempt + 1);
    }, claudeThreadHydrationRetryDelayMs(attempt));
  }, [abortLocalReaders, recoverAuthoritativeHistory, threadId]);

  const handleStop = useCallback(async () => {
    if (isStopping || !canStopMainTurn) {
      return;
    }
    setIsStopping(true);
    // A failed/ambiguous Stop is not permission to unlock the composer.
    setRuntimeRunning(true);
    const controller = new AbortController();
    stopRequestAbortRef.current?.abort();
    stopRequestAbortRef.current = controller;
    if (stopRequestTimerRef.current !== null) window.clearTimeout(stopRequestTimerRef.current);
    stopRequestTimerRef.current = window.setTimeout(() => controller.abort(), 10_000);
    let acknowledged = false;
    try {
      const response = await fetch(
        `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/stop`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getAuthToken()}` },
          signal: controller.signal,
        },
      );
      if (!response.ok) throw new Error(`Stop failed (${response.status}).`);
      const stopResult = parseThreadStopResponse(await response.json());
      if (stopResult === null) {
        throw new Error('Stop response is malformed.');
      }
      acknowledged = stopResult.stopRequested;
    } catch {
      // Network/malformed/non-2xx is authoritative-unknown.
    } finally {
      if (stopRequestTimerRef.current !== null) {
        window.clearTimeout(stopRequestTimerRef.current);
        stopRequestTimerRef.current = null;
      }
      if (stopRequestAbortRef.current === controller) stopRequestAbortRef.current = null;
      if (chatPanelMountedRef.current) {
        if (chatStopMayAbortLocalReaders(acknowledged, null)) abortLocalReaders();
        setIsStopping(false);
        if (stopRecoveryTimerRef.current === null) void recoverAfterStop();
      }
    }
  }, [abortLocalReaders, canStopMainTurn, isStopping, recoverAfterStop, threadId]);
  const shouldShowMessageSurface = visibleMessages.length > 0 || Boolean(error) || chatLoading;

  const effectiveToolChoice: ToolChoice = imFullAccessEnabled ? 'auto' : currentToolChoice;

  // Derive the earliest tool part that is waiting on a user decision. The
  // confirmation UI (approve/reject or AskUserQuestion form) floats above the
  // input dock instead of rendering inline in the message list.
  const pendingConfirmation = useMemo<PendingToolConfirmation | null>(() => {
    for (const message of visibleMessages) {
      const parts = message.parts ?? [];
      for (let partIndex = 0; partIndex < parts.length; partIndex += 1) {
        const part = parts[partIndex];
        if (!isToolUIPart(part)) continue;
        const toolPart = part as ToolUIPart | DynamicToolUIPart;
        const kind = resolvePendingToolConfirmation(
          toolPart,
          effectiveToolChoice,
          settledToolCallIds,
          runtimePendingToolCallIds,
        );
        if (!kind) continue;
        return {
          kind,
          partKey: `${message.id}-${partIndex}`,
          toolCallId: toolPart.toolCallId,
          toolName: resolveToolName(toolPart) || getToolName(toolPart),
          title: 'title' in toolPart ? (toolPart as { title?: string }).title : undefined,
          input: 'input' in toolPart ? toolPart.input : undefined,
          networkRequest: kind === 'sandbox-network' ? resolveSandboxNetworkRequest(toolPart) : undefined,
        };
      }
    }
    return null;
  }, [visibleMessages, effectiveToolChoice, settledToolCallIds, runtimePendingToolCallIds]);

  // Keep the export snapshot refs in sync with the derived dock state.
  pendingConfirmationForExportRef.current = pendingConfirmation;
  toolChoiceForExportRef.current = effectiveToolChoice;

  const shouldShowLoadingIndicator = useMemo(() => {
    if (!agentBusy || visibleMessages.length === 0) {
      return false;
    }
    const lastMessage = visibleMessages.at(-1);
    const hasVisibleParts = lastMessage?.parts?.some(
      (part) => part.type === 'text' || part.type === 'reasoning' || isToolUIPart(part),
    );
    return !hasVisibleParts;
  }, [agentBusy, visibleMessages]);

  const updateScrollToBottomVisibility = useCallback((element: HTMLDivElement) => {
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
    const isScrollable = element.scrollHeight - element.clientHeight > CHAT_BOTTOM_PROXIMITY_PX;
    const isNearBottom = distanceFromBottom < CHAT_BOTTOM_PROXIMITY_PX;
    isNearBottomRef.current = isNearBottom;
    setShowScrollToBottom(isScrollable && !isNearBottom);
  }, []);

  const handleScroll = useCallback(() => {
    const element = chatContainerRef.current;
    if (!element) {
      return;
    }
    updateScrollToBottomVisibility(element);
  }, [updateScrollToBottomVisibility]);

  const handleScrollToBottom = useCallback(() => {
    const element = chatContainerRef.current;
    if (!element) {
      return;
    }
    isNearBottomRef.current = true;
    setShowScrollToBottom(false);
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
      return;
    }
    element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    const element = chatContainerRef.current;
    if (!element) {
      setShowScrollToBottom(false);
      return undefined;
    }
    if (isNearBottomRef.current) {
      setShowScrollToBottom(false);
      const frameId = requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      });
      return () => cancelAnimationFrame(frameId);
    }
    const frameId = requestAnimationFrame(() => {
      updateScrollToBottomVisibility(element);
    });
    return () => cancelAnimationFrame(frameId);
  }, [messages, status, shouldShowMessageSurface, updateScrollToBottomVisibility]);

  return (
    <div className={className} style={{ display: 'flex', minHeight: 0, flex: 1, flexDirection: 'column', justifyContent: shouldShowMessageSurface ? 'flex-start' : 'flex-end', overflow: 'hidden' }}>
      {shouldShowMessageSurface ? (
        <div ref={chatContainerRef} onScroll={handleScroll} style={{ minHeight: 0, flex: 1, overflowY: 'auto', borderRadius: '1.5rem', background: 'var(--color-bg-app)', padding: '1rem 1rem 1.5rem' }}>
          <ChatMessageList
            messages={visibleMessages}
            threadId={threadId}
            isLoading={chatLoading}
            error={error}
            addToolResult={addToolResult}
            shouldShowLoadingIndicator={shouldShowLoadingIndicator}
            toolChoice={effectiveToolChoice}
            setMessages={setMessages}
            sendMessage={sendMessage}
            onEditorWriteConfirmed={onEditorWriteConfirmed}
            onOpenSubagentTask={onOpenSubagentTask}
            settledToolCallIds={settledToolCallIds}
            onToolConfirmationSettled={markToolConfirmationSettled}
          />
          <div ref={bottomRef} aria-hidden="true" />
        </div>
      ) : null}

      <div style={{ position: 'relative', zIndex: 10, width: '100%', margin: '0.75rem 0 0', flexShrink: 0, paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.5rem)' }}>
        {shouldShowMessageSurface && showScrollToBottom ? (
          <button
            type="button"
            aria-label={t('chat.panel.scrollToBottom')}
            title={t('chat.panel.scrollToBottom')}
            onClick={handleScrollToBottom}
            style={{
              position: 'absolute',
              left: '50%',
              bottom: 'calc(100% + 0.6rem)',
              transform: 'translateX(-50%)',
              width: '2.5rem',
              height: '2.5rem',
              borderRadius: '999px',
              border: '1px solid var(--color-border-paper)',
              background: 'var(--color-bg-surface-solid)',
              color: 'var(--color-text-primary)',
              boxShadow: '0 8px 20px var(--color-shadow-soft)',
              cursor: 'pointer',
              display: 'grid',
              placeItems: 'center',
              transition: 'transform 0.16s ease, box-shadow 0.16s ease, background 0.16s ease',
            }}
          >
            <IconArrowDown style={{ width: '1.05rem', height: '1.05rem' }} />
          </button>
        ) : null}
        {pendingConfirmation ? (
          // While a tool confirmation is pending, the input dock is replaced by
          // the confirmation panel — the composer returns once the user decides.
          <ToolConfirmationDock
            key={`${pendingConfirmation.partKey}-${pendingConfirmation.toolCallId}`}
            confirmation={pendingConfirmation}
            threadId={threadId}
            addToolResult={addToolResult}
            onSettled={markToolConfirmationSettled}
          />
        ) : (
          <AIInputDock
            openFileDialogSignal={openFileDialogSignal}
            fullAccessEnabled={imFullAccessEnabled}
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
              turnGenerationRef.current += 1;
              await sendMessage({ role: 'user', parts });
            }}
            placeholder={inputPlaceholder}
            loading={chatLoading}
            onStop={canStopMainTurn ? handleStop : undefined}
            stopPending={isStopping}
            workspaceSessionId={workspaceEnabled ? threadId : undefined}
            contextControl={inputContextControl}
            mode="full"
          />
        )}
      </div>
    </div>
  );
}
