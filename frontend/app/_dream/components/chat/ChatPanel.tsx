// [Sync] 2026-09-28: render created-task links inside the owning assistant reply above its action row.
// [Sync] 2026-09-28: remove dispatched and failed inputs from queue controls; surface uncertain outcomes separately.
// [Sync] 2026-09-27: show task-session source navigation and settled created-task lists.
// [Sync] 2026-09-27: pass the source relation into ChatMessageList so its first user bubble owns the marker.
// [Sync] 2026-09-27: keep shell-level task management and pass contextual created-task links into the assistant reply; retain the target Thread source marker.
// [Sync] 2026-09-28: remove task-result cards; wait_threads returns child completion inside the active parent turn.
// [Sync] 2026-09-27: keep queue failure feedback compact, aligned with the composer, and refreshable without resending.
// [Sync] 2026-09-27: show actionable queue cards and move one queued message to an independent side Chat.
// [Sync] 2026-09-26: running turns submit durable queued text and show server queue states.
// [Sync] 2026-09-14: same-origin Cookie session with in-memory CSRF; no Browser OAuth Bearer/storage.
import { browserRequestHeaders } from '../../lib/browserSession';
import { cancelThreadInput, enqueueThreadInput, fetchThreadInputs, isThreadInputQueueCard, moveThreadInputToSideTask, selectThreadInput, ThreadInputError, type ThreadInputEntry } from './threadInputQueue';
import ThreadInputQueueCard from './ThreadInputQueueCard';
import { TaskSessionLinksFailure } from './TaskSessionNavigation';
import { fetchTaskSessionLinks, type TaskSessionLinksSnapshot } from './taskSessionLinks';
// [Input] Consume ClaudeAgentChatTransport, WorkspaceContext, chat schema/types, file proxy utilities, AIInputDock/helpers, ChatMessageList, and Browser session and CSRF.
//         reconnectStreamNonce from ChatView; claude-agent-sse-utils for stream replay.
// [Output] Coordinate chat transport, pending attachments/tool choice, message state, scrolling, and input/message layout.
// [Pos] chat-panel component node in frontend/app/_dream/components/chat
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
// [Sync] 2026-09-04: forward Workspace Mode to the slash catalog so only executable
//                    workspace-backed Skills are suggested.
// [Sync] 2026-06-25: stop button now calls the backend thread stop endpoint
//                    instead of only aborting the local browser stream.
// [Sync] 2026-09-17: keep an accepted Stop mutation alive across Story Workspace/ChatPanel remounts;
//                    only a strict current-Thread receipt or authoritative idle may close local readers.
// [Sync] 2026-07-20: pass threadId into ClaudeAgentChatTransport so plan-* SSE
//                    frames route to the useThreadPlan store (claude-plan feature).
// [Sync] 2026-07-20: forward todo-updated SSE frames to the useThreadTodos store
//                    on the reconnect path (claude-todo §5.6).
// [Sync] 2026-07-20: derive pendingConfirmation from messages and display
//                    ToolConfirmationDock for pending approvals; inline approval/askuser
//                    UIs were removed from the message list. The 2026-09-26 queue
//                    feature keeps the composer visible beside that dock.
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
// [Sync] 2026-08-13: let pending confirmation docks shrink within short Dream rails while
//                    preserving the normal composer's fixed-height layout.
// [Sync] 2026-08-13: contain message scrolling on the vertical axis so narrow Dream dialogs
//                    never expose a panel-level horizontal scrollbar.
// [Sync] 2026-08-13: keep auto-scroll and wheel overscroll owned by the message region;
//                    never scroll Story Workspace ancestors or move its Agent dialog.
// [Sync] 2026-08-13: await the editor persistence barrier before sending any
//                    Agent turn that carries an editor_state snapshot.
// [Sync] 2026-08-15: historical composers no longer accept a duplicate locked
//                    Deck/Agent context control from ChatView.
// [Sync] 2026-08-17: read Deck/Agent turn context from a live ref so same-Thread selection reaches transport.
// [Sync] 2026-08-31: reload authoritative Thread state from structured turn errors without resending the failed message.
// [Sync] 2026-09-02: own stable older-page loading, anchor-preserving prepend,
//                    historical/live turn identity, and latest-page recovery merging.
// [Sync] 2026-09-06: route composer, queued, and MCP Apps user messages through one coordinated ingress.
// [Sync] 2026-09-06: preserve verified live process/App parts when completion recovery returns a final-only history summary.
// [Sync] 2026-09-06: retain live turn identity only for recovery merging; completed turns use the shared collapsed-process layout.
// [Sync] 2026-09-07: keep live turn identities in a ref so metadata replay cannot
//                    recreate the recovery callback and abort an active reconnect stream.
// [Sync] 2026-09-29: pair a compact full-Thread turn index with the paged message scroller and left navigation rail.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  type ChatMetadata,
  type ToolChoice,
} from '../../lib/chat-schema';
import { toFileProxyUrl } from '../../lib/toFileProxyUrl';
import {
  type Attachment,
  toAttachment,
} from './AIInputDock.helpers';
import AIInputDock from './AIInputDock';
import ChatMessageList from './ChatMessageList';
import TurnNavigation from './TurnNavigation';
import {
  fetchTurnNavigation,
  mergeTurnNavigation,
  projectVisibleTurnNavigation,
  type ChatTurnNavigationItem,
} from './chatTurnNavigationModel';
import ToolConfirmationDock from './ToolConfirmationDock';
import {
  deriveSettledToolCallIdsFromKnownPending,
  resolvePendingToolConfirmation,
  resolveSandboxNetworkRequest,
  resolveToolName,
  type PendingToolConfirmation,
} from './toolConfirmation';

import { registerChatExportSource } from '../../lib/chat-export-registry';
import { subscribeImFullAccessChanged } from '../../lib/system-config-events';
import {
  publishStoryWorkspaceOutput,
  type StoryWorkspaceOutputReceipt,
} from '../../lib/story-workspace-events';
import {
  claudeThreadHydrationRetryDelayMs,
  ClaudeThreadHydrationUnknownError,
  fetchClaudeThreadMessages,
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
} from './chatRuntimeState';
import { requestClaudeThreadStop } from './threadStop';
import {
  captureChatScrollAnchor,
  mergeRecoveredLatestPage,
  prependUniqueOlderMessages,
  restoreChatScrollAnchor,
} from './chatHistoryWindow';
import {
  sendCoordinatedChatUserMessage,
  type ChatUserMessage,
  type CoordinatedChatSendOptions,
} from './chatUserMessageIngress';
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
  initialToolConfirmationKnown?: boolean;
  initialHistoryPage?: ChatPanelHistoryPage;
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
  ensureEditorSessionPersisted?: () => Promise<void>;
  /** Called after an editor write tool is confirmed so the Writing view can reload from the database. */
  onEditorWriteConfirmed?: (toolCallId: string) => void;
  /** Optional task focus action for hosts that keep message-level subagent navigation. */
  onOpenSubagentTask?: (toolCallId: string) => void;
  /** Opens an independently owned task Thread in the right-hand chat. */
  onOpenTaskThread?: (threadId: string) => void;
  /** Replaces the current canonical Chat Thread after following a persisted task relation. */
  onNavigateThread?: (threadId: string) => void;
  /** Voice / deck system prompt injected as voice_context into each user message. */
  voiceSystemPrompt?: string;
  /** Immutable Deck selection for this thread. */
  deckId?: string;
  /** Immutable Agent selection within the Deck. */
  voiceId?: string;
}

export interface ChatPanelRecoverySnapshot {
  messages: UIMessage[];
  settledToolCallIds: ReadonlySet<string>;
  runtimePendingToolCallIds: ReadonlySet<string>;
  running: boolean;
  historyPage?: ChatPanelHistoryPage;
  toolConfirmationKnown?: boolean;
}

export interface ChatPanelHistoryPage {
  nextCursor: string | null;
  hasMore: boolean;
  latestMessageId: string | null;
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
  initialToolConfirmationKnown = false,
  initialHistoryPage = { nextCursor: null, hasMore: false, latestMessageId: null },
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
  ensureEditorSessionPersisted,
  onEditorWriteConfirmed,
  onOpenSubagentTask,
  onOpenTaskThread,
  onNavigateThread,
  voiceSystemPrompt,
  deckId,
  voiceId,
}: ChatPanelProps) {
  const { t } = useTranslation();
  const pendingDataRef = useRef<{
    rawAttachments: Attachment[];
    toolChoice: ToolChoice;
  } | null>(null);
  const [currentToolChoice, setCurrentToolChoice] = useState<ToolChoice>('auto');
  const [threadInputs, setThreadInputs] = useState<ThreadInputEntry[]>([]);
  const queueCardEntries = threadInputs.filter(isThreadInputQueueCard);
  const queueOutcomeUnknown = threadInputs.some((entry) => entry.status === 'state_unknown');
  const [inputOwnerLocal, setInputOwnerLocal] = useState(false);
  const [threadInputError, setThreadInputError] = useState<string | null>(null);
  const [queueCheckPending, setQueueCheckPending] = useState(false);
  const [editDraftRecovery, setEditDraftRecovery] = useState<{ id: string; text: string } | null>(null);
  const pendingInputIdsRef = useRef(new Map<string, string>());
  const [systemConfig, setSystemConfig] = useState<SystemConfigData>();
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const navigationAbortRef = useRef<AbortController | null>(null);
  const navigationHighlightTimerRef = useRef<number | null>(null);
  const [indexedTurns, setIndexedTurns] = useState<ChatTurnNavigationItem[]>([]);
  const [navigationIndexLoading, setNavigationIndexLoading] = useState(false);
  const [navigationIndexError, setNavigationIndexError] = useState(false);
  const [navigationIndexNonce, setNavigationIndexNonce] = useState(0);
  const [activeTurnMessageId, setActiveTurnMessageId] = useState<string | null>(null);
  const [locatingMessageId, setLocatingMessageId] = useState<string | null>(null);
  const [failedLocateMessageId, setFailedLocateMessageId] = useState<string | null>(null);
  const [locatedMessageId, setLocatedMessageId] = useState<string | null>(null);
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
  const messagesRef = useRef<UIMessage[]>([]);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [settledToolCallIds, setSettledToolCallIds] = useState<ReadonlySet<string>>(
    () => new Set(initialSettledToolCallIds),
  );
  const [runtimePendingToolCallIds, setRuntimePendingToolCallIds] = useState<ReadonlySet<string>>(
    () => new Set(initialRuntimePendingToolCallIds),
  );
  const [toolConfirmationKnown, setToolConfirmationKnown] = useState(initialToolConfirmationKnown);
  const [historyPage, setHistoryPage] = useState<ChatPanelHistoryPage>(initialHistoryPage);
  const [historicalMessageIds, setHistoricalMessageIds] = useState<ReadonlySet<string>>(
    () => new Set((initialMessages ?? []).map((message) => message.id)),
  );
  const livePresentedTurnIdsRef = useRef<ReadonlySet<string>>(new Set<string>());
  const [isLoadingOlderHistory, setIsLoadingOlderHistory] = useState(false);
  const [olderHistoryError, setOlderHistoryError] = useState<Error | null>(null);
  const olderHistoryAbortRef = useRef<AbortController | null>(null);
  const [runtimeRunning, setRuntimeRunning] = useState(initialRuntimeRunning);
  const [taskSessionLinks, setTaskSessionLinks] = useState<TaskSessionLinksSnapshot>({ source: null, created: [] });
  const [taskSessionLinksFailed, setTaskSessionLinksFailed] = useState(false);
  const taskSessionLinksRequestRef = useRef(0);
  const [reconnectRetryNonce, setReconnectRetryNonce] = useState(0);
  const reconnectRetryTimerRef = useRef<number | null>(null);
  const reconnectRecoveryAttemptRef = useRef(0);
  const localCompletionRetryTimerRef = useRef<number | null>(null);
  const stopRecoveryTimerRef = useRef<number | null>(null);
  const chatPanelMountedRef = useRef(true);
  const previousChatStatusRef = useRef<string>('ready');
  const reconnectAbortRef = useRef<AbortController | null>(null);
  const { setActiveSessionId, workspaceConfigLoaded, workspaceEnabled } = useWorkspaceSession();

  onReconnectCompleteRef.current = onReconnectComplete;
  onConversationSettledRef.current = onConversationSettled;

  useEffect(() => {
    chatPanelMountedRef.current = true;
    return () => {
      chatPanelMountedRef.current = false;
      reconnectAbortRef.current?.abort();
      reconnectAbortRef.current = null;
      olderHistoryAbortRef.current?.abort();
      olderHistoryAbortRef.current = null;
      navigationAbortRef.current?.abort();
      navigationAbortRef.current = null;
      if (navigationHighlightTimerRef.current !== null) {
        window.clearTimeout(navigationHighlightTimerRef.current);
        navigationHighlightTimerRef.current = null;
      }
      for (const timerRef of [
        reconnectRetryTimerRef,
        localCompletionRetryTimerRef,
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
          headers: { ...browserRequestHeaders() },
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
  const effectiveToolChoice: ToolChoice = imFullAccessEnabled ? 'auto' : currentToolChoice;
  const requestContextRef = useRef({
    deckId,
    voiceId,
    voiceSystemPrompt,
    editorState,
    currentToolChoice,
    imFullAccessEnabled,
    settingsSystemPrompt: systemConfig?.system_prompt,
  });
  requestContextRef.current = {
    deckId,
    voiceId,
    voiceSystemPrompt,
    editorState,
    currentToolChoice,
    imFullAccessEnabled,
    settingsSystemPrompt: systemConfig?.system_prompt,
  };

  const { messages, sendMessage, setMessages, status, error, addToolResult, stop, clearError } = useChat({
    id: threadId,
    transport: new ClaudeAgentChatTransport({
      threadId,
      api: `${API_BASE}/api/claude-agent`,
      headers: () => ({ ...browserRequestHeaders() }),
      prepareSendMessagesRequest: ({ messages: outgoingMessages, body, id }) => {
        const lastMessage = outgoingMessages.at(-1) as UIMessage | undefined;
        if (!lastMessage) {
          return { body: body ?? {} };
        }
        const requestContext = requestContextRef.current;

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

        const requestToolChoice: ToolChoice = requestContext.imFullAccessEnabled
          ? 'auto'
          : getPendingData()?.toolChoice ?? requestContext.currentToolChoice;

        const requestBody: ChatApiSchemaRequestBody = {
          id,
          ...(requestContext.deckId ? { deckId: requestContext.deckId } : {}),
          ...(requestContext.voiceId ? { voiceId: requestContext.voiceId } : {}),
          resume: true,
          message: lastMessage,
          toolChoice: requestToolChoice,
          allowedAppDefaultToolkit: [],
          allowedMcpServers: {},
          attachments,
          systemPrompt: requestContext.voiceSystemPrompt ?? requestContext.settingsSystemPrompt,
          ...(requestContext.editorState != null ? { editor_state: requestContext.editorState } : {}),
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
  messagesRef.current = messages;

  // DEC-032: story-workspace guidance rows persist in chat_message but must
  // never render as Chat bubbles — every render/export seam below consumes
  // visibleMessages instead of the raw useChat list (Task 4 Step 0).
  const visibleMessages = useMemo(
    () => filterClaudeThreadVisibleMessages(messages),
    [messages],
  );

  const sendUserMessage = useCallback(async (
    message: ChatUserMessage,
    options: CoordinatedChatSendOptions<Attachment> = {},
  ) => {
    await sendCoordinatedChatUserMessage(message, options, {
      onConversationStart,
      setToolChoice: setCurrentToolChoice,
      setPendingData: (value) => { pendingDataRef.current = value; },
      ensureEditorSessionPersisted: editorState ? ensureEditorSessionPersisted : undefined,
      incrementTurnGeneration: () => { turnGenerationRef.current += 1; },
      dispatch: sendMessage,
    });
  }, [editorState, ensureEditorSessionPersisted, onConversationStart, sendMessage]);

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
    setToolConfirmationKnown(initialToolConfirmationKnown);
    setReconnectRetryNonce(0);
    reconnectRecoveryAttemptRef.current = 0;
    lastReconnectNonceRef.current = 0;
    lastReconnectCountersRef.current = { external: 0, retry: 0 };
    previousChatStatusRef.current = 'ready';
    turnGenerationRef.current = 0;
    setHistoryPage(initialHistoryPage);
    setHistoricalMessageIds(new Set((initialMessages ?? []).map((message) => message.id)));
    livePresentedTurnIdsRef.current = new Set<string>();
    setOlderHistoryError(null);
    setIsLoadingOlderHistory(false);
    navigationAbortRef.current?.abort();
    navigationAbortRef.current = null;
    if (navigationHighlightTimerRef.current !== null) {
      window.clearTimeout(navigationHighlightTimerRef.current);
      navigationHighlightTimerRef.current = null;
    }
    setIndexedTurns([]);
    setNavigationIndexError(false);
    setActiveTurnMessageId(null);
    setLocatingMessageId(null);
    setFailedLocateMessageId(null);
    setLocatedMessageId(null);
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
    setToolConfirmationKnown(initialToolConfirmationKnown);
  }, [initialToolConfirmationKnown]);

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
    setHistoryPage(initialHistoryPage);
    setHistoricalMessageIds(new Set(initialMessages.map((message) => message.id)));
    hasInitializedRef.current = true;
  }, [initialHistoryPage, initialMessages, setMessages]);

  useEffect(() => {
    if (status !== 'submitted' && status !== 'streaming' && !runtimeRunning) return;
    const current = livePresentedTurnIdsRef.current;
    const next = new Set(current);
    for (const message of messages) {
      if (message.role !== 'assistant' || historicalMessageIds.has(message.id)) continue;
      const metadata = message.metadata as ChatMetadata | undefined;
      if (typeof metadata?.turnId === 'string' && metadata.turnId) next.add(metadata.turnId);
    }
    if (next.size !== current.size) livePresentedTurnIdsRef.current = next;
  }, [historicalMessageIds, messages, runtimeRunning, status]);

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
      await sendUserMessage(
        { role: 'user', parts: queuedMessageParts },
        { rawAttachments: queuedAttachments, toolChoice: queuedToolChoice },
      );
    })();
  }, [claimQueuedPrompt, queuedAttachments, queuedPrompt, queuedPromptNonce, queuedToolChoice, sendUserMessage]);

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
      setToolConfirmationKnown(snapshot.toolConfirmationKnown ?? false);
      const recovered = mergeRecoveredLatestPage(
        messagesRef.current,
        recoveredMessages,
        livePresentedTurnIdsRef.current,
      );
      const recoveredPage = snapshot.historyPage ?? {
        nextCursor: null,
        hasMore: false,
        latestMessageId: null,
      };
      setMessagesRef.current?.(recovered.messages);
      setHistoricalMessageIds((currentIds) => {
        const next = recovered.overlapsLoadedWindow ? new Set(currentIds) : new Set<string>();
        recoveredMessages.forEach((message) => next.add(message.id));
        return next;
      });
      setHistoryPage((currentPage) => recovered.overlapsLoadedWindow
        ? { ...currentPage, latestMessageId: recoveredPage.latestMessageId }
        : recoveredPage);
      if (!snapshot.running) onConversationSettledRef.current?.();
      return snapshot;
    } catch {
      return undefined;
    }
  }, [threadId]);

  const [isReloadingAfterError, setIsReloadingAfterError] = useState(false);
  const handleReloadAfterError = useCallback(async () => {
    if (isReloadingAfterError) return;
    setIsReloadingAfterError(true);
    try {
      const recovered = await recoverAuthoritativeHistory();
      if (recovered !== undefined) clearError();
    } finally {
      if (chatPanelMountedRef.current) setIsReloadingAfterError(false);
    }
  }, [clearError, isReloadingAfterError, recoverAuthoritativeHistory]);

  const loadOlderHistory = useCallback(async () => {
    if (!historyPage.hasMore || !historyPage.nextCursor || olderHistoryAbortRef.current) return;
    const controller = new AbortController();
    olderHistoryAbortRef.current = controller;
    setIsLoadingOlderHistory(true);
    setOlderHistoryError(null);
    const scroller = chatContainerRef.current;
    const anchor = scroller?.querySelector<HTMLElement>('[data-chat-message-id]') ?? null;
    const scrollAnchor = captureChatScrollAnchor(scroller, anchor);
    try {
      const page = await fetchClaudeThreadMessages(threadId, {
        cursor: historyPage.nextCursor,
        signal: controller.signal,
      });
      setMessagesRef.current?.((current) => prependUniqueOlderMessages(current, page.messages));
      setHistoricalMessageIds((current) => {
        const next = new Set(current);
        page.messages.forEach((message) => next.add(message.id));
        return next;
      });
      if (toolConfirmationKnown) {
        const pageSettled = deriveSettledToolCallIdsFromKnownPending(
          page.messages,
          runtimePendingToolCallIds,
        );
        setSettledToolCallIds((current) => {
          const next = new Set(current);
          pageSettled.forEach((toolCallId) => next.add(toolCallId));
          return next.size === current.size ? current : next;
        });
      }
      setHistoryPage({
        nextCursor: page.nextCursor,
        hasMore: page.hasMore,
        latestMessageId: historyPage.latestMessageId ?? page.latestMessageId,
      });
      if (scrollAnchor) {
        requestAnimationFrame(() => {
          restoreChatScrollAnchor(scrollAnchor);
        });
      }
    } catch (reason) {
      if (controller.signal.aborted) return;
      if (reason instanceof ClaudeThreadHydrationUnknownError && reason.httpStatus === 400) {
        const recovered = await recoverAuthoritativeHistory();
        if (recovered === undefined) setOlderHistoryError(reason);
      } else {
        setOlderHistoryError(reason instanceof Error ? reason : new Error('history page failed'));
      }
    } finally {
      if (olderHistoryAbortRef.current === controller) olderHistoryAbortRef.current = null;
      if (chatPanelMountedRef.current) setIsLoadingOlderHistory(false);
    }
  }, [historyPage, recoverAuthoritativeHistory, runtimePendingToolCallIds, threadId, toolConfirmationKnown]);

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
            headers: { ...browserRequestHeaders() },
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
  const visibleTurnNavigation = useMemo(
    () => projectVisibleTurnNavigation(visibleMessages, agentBusy),
    [visibleMessages, agentBusy],
  );
  const turnNavigationItems = useMemo(
    () => mergeTurnNavigation(indexedTurns, visibleTurnNavigation),
    [indexedTurns, visibleTurnNavigation],
  );
  const latestVisibleMessageId = visibleMessages.at(-1)?.id ?? null;
  const partialTurnNavigation = historyPage.hasMore
    && (indexedTurns.length === 0 || navigationIndexError);

  useEffect(() => {
    if (!latestVisibleMessageId) return undefined;
    const controller = new AbortController();
    setNavigationIndexLoading(true);
    setNavigationIndexError(false);
    void fetchTurnNavigation(threadId, controller.signal).then((items) => {
      if (!controller.signal.aborted) setIndexedTurns(items);
    }).catch(() => {
      if (!controller.signal.aborted) setNavigationIndexError(true);
    }).finally(() => {
      if (!controller.signal.aborted) setNavigationIndexLoading(false);
    });
    return () => controller.abort();
  }, [threadId, latestVisibleMessageId, agentBusy, navigationIndexNonce]);

  const refreshTaskSessionLinks = useCallback(async () => {
    const request = taskSessionLinksRequestRef.current + 1;
    taskSessionLinksRequestRef.current = request;
    try {
      const next = await fetchTaskSessionLinks(threadId);
      if (chatPanelMountedRef.current && taskSessionLinksRequestRef.current === request) {
        setTaskSessionLinks(next);
        setTaskSessionLinksFailed(false);
      }
    } catch {
      if (chatPanelMountedRef.current && taskSessionLinksRequestRef.current === request) {
        setTaskSessionLinksFailed(true);
      }
    }
  }, [threadId]);

  useEffect(() => {
    setTaskSessionLinks({ source: null, created: [] });
    setTaskSessionLinksFailed(false);
    void refreshTaskSessionLinks();
  }, [refreshTaskSessionLinks]);

  const previousTaskSessionBusyRef = useRef(agentBusy);
  useEffect(() => {
    const wasBusy = previousTaskSessionBusyRef.current;
    previousTaskSessionBusyRef.current = agentBusy;
    if (wasBusy && !agentBusy) void refreshTaskSessionLinks();
  }, [agentBusy, refreshTaskSessionLinks]);

  const refreshThreadInputs = useCallback(async () => {
    const snapshot = await fetchThreadInputs(threadId);
    setThreadInputs(snapshot.entries);
    setInputOwnerLocal(snapshot.local_owner);
  }, [threadId]);

  const inputFailureText = useCallback((error: unknown) => {
    if (error instanceof ThreadInputError) {
      if (error.outcomeUnknown) return t('chat.inputQueue.stateUnknown');
      if (error.status === 403 || error.status === 404) return t('chat.inputQueue.accessDenied');
      if (error.code === 'CHAT_INPUT_OWNER_UNAVAILABLE') return t('chat.inputQueue.ownerUnavailable');
      if (error.status === 409) return t('chat.inputQueue.stateChanged');
      if (error.status === 503) return t('chat.inputQueue.unavailable');
    }
    if (error instanceof TypeError) return t('chat.inputQueue.unavailable');
    return t('chat.inputQueue.sendFailed');
  }, [t]);

  const checkThreadInputStatus = useCallback(async () => {
    setQueueCheckPending(true);
    try {
      await refreshThreadInputs();
      setThreadInputError(null);
    } catch (error) {
      setThreadInputError(inputFailureText(error));
    } finally {
      setQueueCheckPending(false);
    }
  }, [inputFailureText, refreshThreadInputs]);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const snapshot = await fetchThreadInputs(threadId);
        if (active) {
          setThreadInputs(snapshot.entries);
          setInputOwnerLocal(snapshot.local_owner);
        }
      } catch {
        // The queue capability is deployed separately; ordinary history remains usable.
      }
    };
    void load();
    const timer = window.setInterval(() => { void load(); }, 2000);
    return () => { active = false; window.clearInterval(timer); };
  }, [threadId]);

  const selectQueuedInput = useCallback(async (entry: ThreadInputEntry) => {
    try {
      const receipt = await selectThreadInput(threadId, entry);
      setThreadInputs((current) => current.map((item) => item.message_id === entry.message_id ? receipt.entry : item));
      setThreadInputError(receipt.interrupt_signalled ? null : t('chat.inputQueue.guideFailed'));
      await refreshThreadInputs();
    } catch (error) {
      setThreadInputError(inputFailureText(error));
      void refreshThreadInputs();
    }
  }, [inputFailureText, refreshThreadInputs, t, threadId]);

  const cancelQueuedInput = useCallback(async (entry: ThreadInputEntry) => {
    try {
      const updated = await cancelThreadInput(threadId, entry);
      setThreadInputs((current) => current.map((item) => item.message_id === entry.message_id ? updated : item));
      setThreadInputError(null);
      await refreshThreadInputs();
    } catch (error) {
      setThreadInputError(inputFailureText(error));
      void refreshThreadInputs();
      throw error;
    }
  }, [inputFailureText, refreshThreadInputs, threadId]);

  const editQueuedInput = useCallback(async (entry: ThreadInputEntry, text: string) => {
    await cancelQueuedInput(entry);
    const newMessageId = crypto.randomUUID();
    try {
      await enqueueThreadInput(threadId, newMessageId, text, effectiveToolChoice, deckId, voiceId);
      setEditDraftRecovery(null);
      setThreadInputError(null);
      await refreshThreadInputs();
    } catch (error) {
      setEditDraftRecovery({ id: newMessageId, text });
      setThreadInputError(inputFailureText(error));
      void refreshThreadInputs();
      throw error;
    }
  }, [cancelQueuedInput, deckId, effectiveToolChoice, inputFailureText, refreshThreadInputs, threadId, voiceId]);

  const retryEditedInput = useCallback(async () => {
    if (!editDraftRecovery) return;
    try {
      await enqueueThreadInput(threadId, editDraftRecovery.id, editDraftRecovery.text,
        effectiveToolChoice, deckId, voiceId);
      setEditDraftRecovery(null);
      setThreadInputError(null);
      await refreshThreadInputs();
    } catch (error) {
      setThreadInputError(inputFailureText(error));
      void refreshThreadInputs();
    }
  }, [deckId, editDraftRecovery, effectiveToolChoice, inputFailureText, refreshThreadInputs, threadId, voiceId]);

  const openQueuedInputInSideChat = useCallback(async (entry: ThreadInputEntry) => {
    try {
      const task = await moveThreadInputToSideTask(threadId, entry);
      await refreshThreadInputs();
      setThreadInputError(task.error_code ? t('chat.inputQueue.sideChatLaunchFailed') : null);
      onOpenTaskThread?.(task.thread_id);
    } catch (error) {
      setThreadInputError(inputFailureText(error));
      void refreshThreadInputs();
      throw error;
    }
  }, [inputFailureText, onOpenTaskThread, refreshThreadInputs, t, threadId]);

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
    let stopRequested: boolean | null = null;
    let authoritativeRunning: boolean | null = null;
    try {
      const stopResult = await requestClaudeThreadStop(threadId);
      stopRequested = stopResult.stopRequested;
      authoritativeRunning = stopResult.running;
    } catch {
      // Network/malformed/non-2xx is authoritative-unknown.
    } finally {
      if (chatPanelMountedRef.current) {
        if (chatStopMayAbortLocalReaders(stopRequested, authoritativeRunning)) abortLocalReaders();
        setIsStopping(false);
        if (stopRecoveryTimerRef.current === null) void recoverAfterStop();
      }
    }
  }, [abortLocalReaders, canStopMainTurn, isStopping, recoverAfterStop, threadId]);
  const historyIsEmpty = initialMessages !== undefined && visibleMessages.length === 0 && !chatLoading;
  const shouldShowMessageSurface = visibleMessages.length > 0 || Boolean(error) || chatLoading || historyIsEmpty
    || taskSessionLinks.source !== null || taskSessionLinksFailed;


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

  const updateActiveTurn = useCallback((element: HTMLDivElement) => {
    const nodes = element.querySelectorAll<HTMLElement>('[data-chat-user-message-id]');
    if (nodes.length === 0) return;
    const readingLine = element.getBoundingClientRect().top + Math.min(element.clientHeight * 0.3, 140);
    let next = nodes[0].dataset.chatUserMessageId ?? null;
    nodes.forEach((node) => {
      if (node.getBoundingClientRect().top <= readingLine) {
        next = node.dataset.chatUserMessageId ?? next;
      }
    });
    setActiveTurnMessageId((current) => current === next ? current : next);
  }, []);

  const navigateToTurn = useCallback(async (messageId: string) => {
    navigationAbortRef.current?.abort();
    const controller = new AbortController();
    navigationAbortRef.current = controller;
    setLocatingMessageId(messageId);
    setFailedLocateMessageId(null);
    const findTarget = () => [...(chatContainerRef.current?.querySelectorAll<HTMLElement>('[data-chat-user-message-id]') ?? [])]
      .find((node) => node.dataset.chatUserMessageId === messageId);
    const scrollToTarget = () => {
      const scroller = chatContainerRef.current;
      const target = findTarget();
      if (!scroller || !target || controller.signal.aborted) return false;
      const top = scroller.scrollTop + target.getBoundingClientRect().top
        - scroller.getBoundingClientRect().top - 16;
      isNearBottomRef.current = false;
      scroller.scrollTo({
        top,
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      });
      setActiveTurnMessageId(messageId);
      setLocatedMessageId(messageId);
      if (navigationHighlightTimerRef.current !== null) {
        window.clearTimeout(navigationHighlightTimerRef.current);
      }
      navigationHighlightTimerRef.current = window.setTimeout(() => {
        setLocatedMessageId((current) => current === messageId ? null : current);
        navigationHighlightTimerRef.current = null;
      }, 1800);
      return true;
    };
    try {
      if (scrollToTarget()) return;
      olderHistoryAbortRef.current?.abort();
      olderHistoryAbortRef.current = null;
      let cursor = historyPage.nextCursor;
      let hasMore = historyPage.hasMore;
      let loaded: UIMessage[] = [];
      let found = false;
      while (hasMore && cursor && !controller.signal.aborted) {
        const page = await fetchClaudeThreadMessages(threadId, { cursor, signal: controller.signal });
        loaded = prependUniqueOlderMessages(loaded, page.messages);
        found = page.messages.some((message) => message.id === messageId);
        if (page.hasMore && page.nextCursor === cursor) throw new Error('History cursor did not advance.');
        cursor = page.nextCursor;
        hasMore = page.hasMore;
        if (found) break;
      }
      if (controller.signal.aborted) return;
      if (!found) {
        setFailedLocateMessageId(messageId);
        return;
      }
      isNearBottomRef.current = false;
      setMessagesRef.current?.((current) => prependUniqueOlderMessages(current, loaded));
      setHistoricalMessageIds((current) => {
        const next = new Set(current);
        loaded.forEach((message) => next.add(message.id));
        return next;
      });
      if (toolConfirmationKnown) {
        const settled = deriveSettledToolCallIdsFromKnownPending(
          loaded,
          runtimePendingToolCallIds,
        );
        setSettledToolCallIds((current) => {
          const next = new Set(current);
          settled.forEach((toolCallId) => next.add(toolCallId));
          return next.size === current.size ? current : next;
        });
      }
      setHistoryPage((current) => ({
        nextCursor: cursor,
        hasMore,
        latestMessageId: current.latestMessageId,
      }));
      await new Promise<void>((resolve) => {
        requestAnimationFrame(() => requestAnimationFrame(() => {
          if (!scrollToTarget() && !controller.signal.aborted) setFailedLocateMessageId(messageId);
          resolve();
        }));
      });
    } catch {
      if (!controller.signal.aborted) setFailedLocateMessageId(messageId);
    } finally {
      if (navigationAbortRef.current === controller) {
        navigationAbortRef.current = null;
        setLocatingMessageId(null);
      }
    }
  }, [historyPage.hasMore, historyPage.nextCursor, runtimePendingToolCallIds, threadId, toolConfirmationKnown]);

  const handleScroll = useCallback(() => {
    const element = chatContainerRef.current;
    if (!element) {
      return;
    }
    updateScrollToBottomVisibility(element);
    updateActiveTurn(element);
    if (element.scrollTop <= 0 && navigationAbortRef.current === null) void loadOlderHistory();
  }, [loadOlderHistory, updateActiveTurn, updateScrollToBottomVisibility]);

  const handleScrollToBottom = useCallback(() => {
    const element = chatContainerRef.current;
    if (!element) {
      return;
    }
    isNearBottomRef.current = true;
    setShowScrollToBottom(false);
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
        element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' });
        updateActiveTurn(element);
      });
      return () => cancelAnimationFrame(frameId);
    }
    const frameId = requestAnimationFrame(() => {
      updateScrollToBottomVisibility(element);
      updateActiveTurn(element);
    });
    return () => cancelAnimationFrame(frameId);
  }, [messages, status, shouldShowMessageSurface, updateActiveTurn, updateScrollToBottomVisibility]);

  return (
    <div className={className} style={{ display: 'flex', minHeight: 0, flex: 1, flexDirection: 'column', justifyContent: shouldShowMessageSurface ? 'flex-start' : 'flex-end', overflow: 'hidden' }}>
      {shouldShowMessageSurface ? (
        <div className="chat-turn-reading">
          <div className="chat-turn-reading__layout">
            <TurnNavigation
              items={turnNavigationItems}
              activeMessageId={activeTurnMessageId}
              loadingIndex={navigationIndexLoading}
              partialIndex={partialTurnNavigation}
              locatingMessageId={locatingMessageId}
              failedMessageId={failedLocateMessageId}
              onNavigate={(messageId) => { void navigateToTurn(messageId); }}
              onRetryIndex={() => setNavigationIndexNonce((current) => current + 1)}
            />
            <div
              data-chat-scroll-region="messages"
              ref={chatContainerRef}
              onScroll={handleScroll}
              style={{ minWidth: 0, minHeight: 0, flex: 1, overflowX: 'hidden', overflowY: 'auto', overscrollBehaviorY: 'contain', borderRadius: '1.5rem', background: 'var(--color-bg-app)', padding: '1rem 1rem 1.5rem' }}
            >
              <ChatMessageList
                messages={visibleMessages}
                threadId={threadId}
                sourceThread={taskSessionLinks.source}
                createdTaskLinks={taskSessionLinks.created}
                onNavigateThread={onNavigateThread}
                isLoading={chatLoading}
                error={error}
                onReloadAfterError={handleReloadAfterError}
                isReloadingAfterError={isReloadingAfterError}
                addToolResult={addToolResult}
                shouldShowLoadingIndicator={shouldShowLoadingIndicator}
                toolChoice={effectiveToolChoice}
                setMessages={setMessages}
                sendUserMessage={sendUserMessage}
                onEditorWriteConfirmed={onEditorWriteConfirmed}
                onOpenSubagentTask={onOpenSubagentTask}
                settledToolCallIds={settledToolCallIds}
                onToolConfirmationSettled={markToolConfirmationSettled}
                historicalMessageIds={historicalMessageIds}
                historyHasMore={historyPage.hasMore}
                historyLoading={isLoadingOlderHistory}
                historyError={olderHistoryError}
                historyEmpty={historyIsEmpty}
                onLoadOlder={loadOlderHistory}
                locatedMessageId={locatedMessageId}
              />
              {!agentBusy && taskSessionLinksFailed ? (
                <TaskSessionLinksFailure onRetry={() => { void refreshTaskSessionLinks(); }} />
              ) : null}
              <div aria-hidden="true" />
            </div>
          </div>
        </div>
      ) : null}

      <div
        style={{
          position: 'relative',
          zIndex: 10,
          width: '100%',
          boxSizing: 'border-box',
          margin: '0.75rem 0 0',
          minHeight: pendingConfirmation ? 0 : undefined,
          maxHeight: pendingConfirmation ? 'min(66vh, 40rem)' : undefined,
          flexShrink: pendingConfirmation ? 1 : 0,
          display: pendingConfirmation ? 'flex' : undefined,
          flexDirection: pendingConfirmation ? 'column' : undefined,
          overflowY: pendingConfirmation ? 'auto' : undefined,
          gap: pendingConfirmation ? '0.5rem' : undefined,
          paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.5rem)',
        }}
      >
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
        {queueCardEntries.length > 0 ? (
          <div aria-label={t('chat.inputQueue.region')} style={{ maxHeight: '12rem', overflowY: 'auto', padding: '0 0.75rem', display: 'grid', gap: '0.3rem' }}>
            {queueCardEntries.map((entry) => (
              <ThreadInputQueueCard
                key={entry.message_id}
                entry={entry}
                localOwner={inputOwnerLocal}
                onGuide={selectQueuedInput}
                onCancel={cancelQueuedInput}
                onEdit={editQueuedInput}
                onSideChat={openQueuedInputInSideChat}
              />
            ))}
          </div>
        ) : null}
        {threadInputError || queueOutcomeUnknown ? (
          <div role="alert" className="chat-input-queue-error" style={{
            boxSizing: 'border-box', width: '100%', display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.35rem 0.75rem',
            padding: '0.45rem 0.75rem', border: '1px solid var(--color-state-danger)',
            borderRadius: '0.65rem', color: 'var(--color-state-danger)',
            background: 'var(--color-bg-surface-solid)', fontSize: '0.82rem', lineHeight: 1.4,
          }}>
            <span>{threadInputError ?? t('chat.inputQueue.dispatchedStateUnknown')}</span>
            {threadInputError !== t('chat.inputQueue.accessDenied')
              && threadInputError !== t('chat.inputQueue.textOnly') ? (
              <button type="button" disabled={queueCheckPending} onClick={() => { void checkThreadInputStatus(); }}
                style={{ flexShrink: 0, border: 0, background: 'transparent', color: 'inherit',
                  font: 'inherit', fontWeight: 700, textDecoration: 'underline', cursor: queueCheckPending ? 'wait' : 'pointer' }}>
                {queueCheckPending ? t('chat.inputQueue.checkingStatus') : t('chat.inputQueue.checkStatus')}
              </button>
            ) : null}
          </div>
        ) : null}
        {editDraftRecovery ? <div role="status" style={{ padding: '0.5rem 0.75rem', border: '1px solid var(--color-border-paper)', borderRadius: '0.75rem', color: 'var(--color-text-primary)' }}>
          <span>{t('chat.inputQueue.editDraftSaved')}</span>
          <p style={{ margin: '0.3rem 0', whiteSpace: 'pre-wrap' }}>{editDraftRecovery.text}</p>
          <button type="button" onClick={() => { void retryEditedInput(); }}>{t('chat.inputQueue.retryEdit')}</button>
        </div> : null}
        {pendingConfirmation ? (
          <ToolConfirmationDock
            key={`${pendingConfirmation.partKey}-${pendingConfirmation.toolCallId}`}
            confirmation={pendingConfirmation}
            threadId={threadId}
            addToolResult={addToolResult}
            onSettled={markToolConfirmationSettled}
          />
        ) : null}
        <AIInputDock
            deckId={deckId}
            threadId={threadId}
            workspaceEnabled={workspaceConfigLoaded && workspaceEnabled}
            openFileDialogSignal={openFileDialogSignal}
            fullAccessEnabled={imFullAccessEnabled}
            onSendMessage={async (message, uploadedFiles = [], toolChoice = 'auto') => {
              if (agentBusy || inputOwnerLocal) {
                if (uploadedFiles.length > 0) {
                  setThreadInputError(t('chat.inputQueue.textOnly'));
                  throw new Error('CHAT_INPUT_UNSUPPORTED_PAYLOAD');
                }
                const text = message.trim();
                if (!text) return;
                const id = pendingInputIdsRef.current.get(text) ?? crypto.randomUUID();
                pendingInputIdsRef.current.set(text, id);
                try {
                  const entry = await enqueueThreadInput(threadId, id, text, toolChoice, deckId, voiceId);
                  pendingInputIdsRef.current.delete(text);
                  setThreadInputs((current) => current.some((item) => item.message_id === entry.message_id)
                    ? current.map((item) => item.message_id === entry.message_id ? entry : item)
                    : [...current, entry]);
                  setThreadInputError(null);
                  void refreshThreadInputs();
                  return;
                } catch (error) {
                  setThreadInputError(inputFailureText(error));
                  throw error;
                }
              }
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
              await sendUserMessage(
                { role: 'user', parts },
                { rawAttachments: uploadedFiles.map(toAttachment), toolChoice },
              );
            }}
            placeholder={inputPlaceholder}
            loading={chatLoading}
            onStop={canStopMainTurn ? handleStop : undefined}
            stopPending={isStopping}
            workspaceSessionId={workspaceEnabled ? threadId : undefined}
            mode="full"
        />
      </div>
    </div>
  );
}
