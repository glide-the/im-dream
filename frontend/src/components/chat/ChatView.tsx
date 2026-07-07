// [Input] Consume WorkspaceContext, AIInputDock, ChatPanel, ResourceConnectorPage, auth token, and AI SDK message types.
//         /api/claude-agent/threads/{id}/status, reconnectStreamNonce to ChatPanel.
// [Output] Render the chat workspace with lazy thread creation, app-owned history/connector entry state, history/file sidebars, a single pill quick-action strip, ChatPanel, and the embedded connector workbench.
//          When /status reports running, bump reconnectStreamNonce so ChatPanel attaches SSE stream.
// [Pos] chat-workspace view node in frontend/src/components/chat
// [Sync] 2026-05-25: stop passing a Settings navigation callback to VerticalNav after removing the left-nav Settings button.
// [Sync] 2026-05-25: remove customer-context props from ChatView and ChatPanel composition.
// [Sync] 2026-05-26: mark conversations started when loaded history contains messages.
// [Sync] 2026-05-29: accept editorState prop and forward to ChatPanel for editor_state request injection.
// [Sync] 2026-05-29: add onEditorWriteConfirmed prop; forward to ChatPanel so Writing view reloads after agent writes.
// [Sync] 2026-05-29: keep the original full-height workspace shell so VerticalNav stays flush-left.
// [Sync] 2026-05-29: make status bar and collapsible sidebar-panel chrome theme-adaptive.
// [Sync] 2026-05-29: move thread list into VerticalNav expanded sidebar; remove separate thread sidebar and flyout; remove header bar; float share+more buttons.
// [Sync] 2026-05-30: accept activeVoice prop to display deck/voice badge in top-right and forward system prompt to ChatPanel.
// [Sync] 2026-06-01: stop creating a thread on first Chat view mount; create lazily on first send, quick action, or explicit New Chat.
// [Sync] 2026-06-01: add delete button to thread list items; hover shows × button; calls DELETE /api/claude-agent/threads/{id}; clears workspace when active thread is deleted.
// [Sync] 2026-06-09: SSE reconnect — fetch /status on thread switch; trigger stream reconnect via reconnectStreamNonce.
// [Sync] 2026-06-09: stable onReconnectComplete callback so editorState re-renders do not abort SSE stream.
// [Sync] 2026-06-12: use centralized API_BASE for cross-origin thread APIs.
// [Sync] 2026-06-14: forward editor write toolCallId for event-driven Writing view reload de-duplication.
// [Sync] 2026-06-22: hide the workspace file sidebar entry when Settings
//                    Workspace Mode is disabled.
// [Sync] 2026-06-27: add Chat history search over thread titles and persisted
//                    conversation text via backend retriever params.
// [Sync] 2026-06-28: move history search from sidebar input to centered search
//                    dialog opened by the history header search button.
// [Sync] 2026-06-28: reload default history whenever the history sidebar opens
//                    so initial panel render is never empty because search is
//                    now decoupled into a dialog.
// [Sync] 2026-06-28: remove the New Chat row from the history search dialog;
//                    top-level Chat chrome already owns new thread creation.
// [Sync] 2026-07-07: add the history/connector landing tabs under the AI composer and embed ResourceConnectorPage in the connector tab so the connector workbench sits below the chat entry point.
// [Sync] 2026-07-07: keep the landing connector workbench inside the viewport by tightening the Chat shell flex/min-height chain.
// [Sync] 2026-07-07: remove the duplicate landing tab pill row once the app navigation owns history/connector switching.
import { Component, useMemo, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import '../../styles/markdown.css';
import { WorkspaceProvider, useWorkspaceSession } from '../../contexts/WorkspaceContext';
import FileSidebar from '../dashboard/FileSidebar';
import ResourceConnectorPage from '../dashboard/ResourceConnectorPage';
import AIInputDock from './AIInputDock';
import ChatPanel from './ChatPanel';
import {
  type Attachment,
  type UploadedFile,
  toAttachment,
} from './AIInputDock.helpers';
import type { UIMessage } from 'ai';
import { getAuthToken } from '../../contexts/AuthContext';
import ChatShellError, { type ChatLandingTab } from './ChatShellError';
import QuickActionStrip, { type QuickActionStripItem } from './QuickActionStrip';
import { IconClock, IconFolder, IconMessageCircle, IconMoreHorizontal, IconPlus, IconSearch, IconShare, IconX } from './Icons';
import type { ActiveChatVoice, ToolChoice } from '../../lib/chat-schema';
import { iconMap } from '../deckVisuals';
import { API_BASE } from '../../lib/apiBase';

interface ChatThread {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  match?: {
    strategy: string;
    retriever?: string;
    score: number;
    fields: string[];
    excerpt?: string;
  };
}

interface RawChatMessage {
  id: string;
  role: string;
  /** Parsed UIMessage['parts'] array — returned by the API already deserialized. */
  parts: UIMessage['parts'];
  /** Parsed ChatMetadata — returned by the API already deserialized. */
  metadata?: Record<string, unknown>;
  created_at: string;
}

interface ChatViewProps {
  threadId?: string;
  /** When set, the view switches to this thread (used for external navigation from Deck / editor widgets). */
  requestedThreadId?: string;
  onNewChat?: () => void;
  quickActions?: QuickActionStripItem[];
  /** Current EditorState snapshot passed down to ChatPanel for agent editor_state injection. */
  editorState?: Record<string, unknown> | null;
  /** Called when an editor write tool is confirmed so the Writing view can reload. */
  onEditorWriteConfirmed?: (toolCallId: string) => void;
  /** Active deck / voice info — displayed in the top-right badge and forwarded to the backend as voice context. */
  activeVoice?: ActiveChatVoice;
  /** Mobile layout hint used by the embedded connector panel. */
  isMobile?: boolean;
  /** Controls the default landing tab when no thread is open. */
  landingTab?: ChatLandingTab;
}

type ChatViewContentProps = Omit<ChatViewProps, 'landingTab'> & {
  landingTab: ChatLandingTab;
  onLandingTabChange: (tab: ChatLandingTab) => void;
};

interface ChatShellBoundaryProps {
  children: ReactNode;
  fallback: (error: Error) => ReactNode;
}

interface ChatShellBoundaryState {
  error: Error | null;
}

class ChatShellBoundary extends Component<ChatShellBoundaryProps, ChatShellBoundaryState> {
  constructor(props: ChatShellBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ChatShellBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error('Chat shell render error:', error);
  }

  render() {
    const { children, fallback } = this.props;
    const { error } = this.state;

    if (error) {
      return fallback(error);
    }

    return children;
  }
}

const DEFAULT_LANDING_QUICK_ACTIONS: QuickActionStripItem[] = [
  {
    id: 'generate-image',
    label: '生成图片',
    prompt: '请根据当前内容生成一张风格统一、适合插入文档的图片。',
    icon: 'image',
    description: '根据当前主题快速生成配图。',
  },
  {
    id: 'write-edit',
    label: '撰写或编辑',
    prompt: '请帮我撰写、改写或润色当前内容，保持自然语气和上下文一致。',
    icon: 'edit',
    description: '继续写作、改写或润色。',
  },
  {
    id: 'find-info',
    label: '查找资料',
    prompt: '请围绕当前主题查找相关资料、参考信息和可用线索。',
    icon: 'search',
    description: '检索相关资料和参考。',
  },
];

const THREAD_SEARCH_DEBOUNCE_MS = 180;

function parseThreadDate(value: string): Date | null {
  const date = new Date(value.includes('T') ? value : value.replace(' ', 'T'));
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayDiffFromToday(value: string): number | null {
  const date = parseThreadDate(value);
  if (!date) return null;
  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const dateStart = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  return Math.floor((todayStart - dateStart) / 86400000);
}

function formatThreadDateLabel(value: string): string {
  const diff = dayDiffFromToday(value);
  if (diff === 0) return '今天';
  if (diff === 1) return '昨天';
  if (diff !== null && diff > 1 && diff < 7) return `${diff} 天前`;

  const date = parseThreadDate(value);
  if (!date) return '';
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric' }).format(date);
}

function getThreadDateGroup(value: string): string {
  const diff = dayDiffFromToday(value);
  if (diff === 0) return '今天';
  if (diff === 1) return '昨天';
  if (diff !== null && diff > 1 && diff < 7) return '前 7 天';
  if (diff !== null && diff < 30) return '前 30 天';
  return '更早';
}

async function createThread(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/claude-agent/threads`, { method: 'POST', headers: { 'Authorization': `Bearer ${getAuthToken()}` } });
    if (!res.ok) return null;
    const data = await res.json() as { thread_id: string };
    return data.thread_id ?? null;
  } catch {
    return null;
  }
}

interface ThreadSearchParams {
  query?: string;
  searchScope?: 'all' | 'title' | 'messages';
  retrievalMode?: 'fuzzy' | 'auto' | 'vector';
}

async function fetchThreads(params: ThreadSearchParams = {}): Promise<ChatThread[]> {
  try {
    const search = new URLSearchParams();
    const query = params.query?.trim() ?? '';
    if (query) {
      search.set('query', query);
      search.set('search_scope', params.searchScope ?? 'all');
      search.set('retrieval_mode', params.retrievalMode ?? 'fuzzy');
    }
    const suffix = search.toString() ? `?${search.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/claude-agent/threads${suffix}`, { headers: { 'Authorization': `Bearer ${getAuthToken()}` } });
    if (!res.ok) return [];
    const data = await res.json() as { threads: ChatThread[] };
    return data.threads ?? [];
  } catch {
    return [];
  }
}

async function deleteThread(threadId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getAuthToken()}` },
    });
    return res.ok;
  } catch {
    return false;
  }
}

interface ThreadStatusResult {
  running: boolean;
  lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  turn_count: number;
}

async function fetchThreadStatus(threadId: string): Promise<ThreadStatusResult | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
      { headers: { 'Authorization': `Bearer ${getAuthToken()}` } },
    );
    if (!res.ok) return null;
    return (await res.json()) as ThreadStatusResult;
  } catch {
    return null;
  }
}

async function fetchThreadMessages(threadId: string): Promise<UIMessage[]> {
  try {
    const res = await fetch(`${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`, { headers: { 'Authorization': `Bearer ${getAuthToken()}` } });
    if (!res.ok) return [];
    const data = await res.json() as { messages?: RawChatMessage[] };
    const msgs = data.messages ?? [];
    return msgs.map((m) => {
      // parts is already a parsed list — aligned with better-chatbot
      // ChatRepository.selectMessagesByThreadId which returns parts directly.
      const parts: UIMessage['parts'] = Array.isArray(m.parts) && m.parts.length > 0
        ? m.parts
        : [{ type: 'text', text: '' }];
      const metadata = m.metadata && typeof m.metadata === 'object' ? m.metadata : undefined;
      return {
        id: m.id,
        role: m.role as UIMessage['role'],
        parts,
        metadata,
        createdAt: new Date(m.created_at),
      };
    });
  } catch {
    return [];
  }
}

function ChatViewContent({
  threadId: initialThreadId,
  requestedThreadId,
  onNewChat,
  quickActions = DEFAULT_LANDING_QUICK_ACTIONS,
  editorState,
  onEditorWriteConfirmed,
  activeVoice,
  isMobile = false,
  landingTab,
  onLandingTabChange,
}: ChatViewContentProps) {
  const { workspaceEnabled } = useWorkspaceSession();
  const [fileSidebarOpen, setFileSidebarOpen] = useState(false);
  const [queuedPrompt, setQueuedPrompt] = useState('');
  const [queuedAttachments, setQueuedAttachments] = useState<Attachment[]>([]);
  const [queuedToolChoice, setQueuedToolChoice] = useState<ToolChoice>('auto');
  const [queuedPromptNonce, setQueuedPromptNonce] = useState(0);
  const [hasConversationStarted, setHasConversationStarted] = useState(false);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(initialThreadId ?? null);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [threadSidebarOpen, setThreadSidebarOpen] = useState(false);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [threadMessages, setThreadMessages] = useState<UIMessage[] | null>(null);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [draftInputError, setDraftInputError] = useState<string | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [threadSearchOpen, setThreadSearchOpen] = useState(false);
  const [threadSearchQuery, setThreadSearchQuery] = useState('');
  const [threadSearchResults, setThreadSearchResults] = useState<ChatThread[]>([]);
  const threadFetchRequestSeqRef = useRef(0);
  const threadSearchRequestSeqRef = useRef(0);
  const threadSearchInputRef = useRef<HTMLInputElement | null>(null);
  const [isSearchingThreads, setIsSearchingThreads] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const [hoveredThreadId, setHoveredThreadId] = useState<string | null>(null);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
  // Bump to signal ChatPanel to attach GET /threads/{id}/stream when backend is still running.
  const [reconnectStreamNonce, setReconnectStreamNonce] = useState(0);

  // Load thread list
  const reloadThreads = useCallback(async () => {
    const requestSeq = threadFetchRequestSeqRef.current + 1;
    threadFetchRequestSeqRef.current = requestSeq;
    setIsLoadingThreads(true);
    const list = await fetchThreads();
    if (requestSeq !== threadFetchRequestSeqRef.current) return;
    setThreads(list);
    setIsLoadingThreads(false);
  }, []);

  useEffect(() => {
    if (!threadSidebarOpen) return;
    void reloadThreads();
  }, [threadSidebarOpen, reloadThreads]);

  useEffect(() => {
    if (!threadSearchOpen) {
      threadSearchRequestSeqRef.current += 1;
      setIsSearchingThreads(false);
      return;
    }

    const focusTimeout = window.setTimeout(() => {
      threadSearchInputRef.current?.focus();
    }, 0);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setThreadSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.clearTimeout(focusTimeout);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [threadSearchOpen]);

  useEffect(() => {
    if (!threadSearchOpen) return;

    const trimmedQuery = threadSearchQuery.trim();
    if (!trimmedQuery) {
      threadSearchRequestSeqRef.current += 1;
      setThreadSearchResults([]);
      setIsSearchingThreads(false);
      return;
    }

    setIsSearchingThreads(true);
    const requestSeq = threadSearchRequestSeqRef.current + 1;
    threadSearchRequestSeqRef.current = requestSeq;
    const timeout = window.setTimeout(() => {
      void (async () => {
        const list = await fetchThreads({ query: trimmedQuery, searchScope: 'all', retrievalMode: 'fuzzy' });
        if (requestSeq !== threadSearchRequestSeqRef.current) return;
        setThreadSearchResults(list);
        setIsSearchingThreads(false);
      })();
    }, THREAD_SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timeout);
  }, [threadSearchOpen, threadSearchQuery]);

  useEffect(() => {
    if (!workspaceEnabled) {
      setFileSidebarOpen(false);
    }
  }, [workspaceEnabled]);

  // @@@ External navigation: switch to a specific thread when requestedThreadId changes.
  useEffect(() => {
    if (!requestedThreadId || requestedThreadId === activeThreadId) return;
    setThreadMessages(null);
    setIsLoadingMessages(true);
    setActiveThreadId(requestedThreadId);
    setHasConversationStarted(true);
    onLandingTabChange('history');
    setQueuedPrompt('');
    setQueuedAttachments([]);
    setQueuedToolChoice('auto');
    void reloadThreads();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedThreadId]);

  // Fetch messages for the active thread (following better-chatbot pattern:
  // parent fetches history and passes as initialMessages to the chat component).
  // Load history, then reconnect SSE when the backend turn is still running.
  useEffect(() => {
    if (!activeThreadId) return;
    let cancelled = false;
    setIsLoadingMessages(true);
    setThreadMessages(null);

    void (async () => {
      const msgs = await fetchThreadMessages(activeThreadId);
      if (cancelled) return;
      setThreadMessages(msgs);
      if (msgs.length > 0) setHasConversationStarted(true);
      setIsLoadingMessages(false);

      const status = await fetchThreadStatus(activeThreadId);
      if (cancelled) return;
      if (status?.running) {
        setReconnectStreamNonce((value) => value + 1);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeThreadId]);

  const handleReconnectComplete = useCallback(async () => {
    if (!activeThreadId) return;
    const msgs = await fetchThreadMessages(activeThreadId);
    setThreadMessages(msgs);
  }, [activeThreadId]);

  const notifyReconnectComplete = useCallback(() => {
    void handleReconnectComplete();
  }, [handleReconnectComplete]);

  const queuePromptForThread = useCallback((
    threadId: string,
    prompt: string,
    attachments: Attachment[] = [],
    toolChoice: ToolChoice = 'auto',
  ) => {
    setThreadMessages([]);
    setIsLoadingMessages(false);
    setActiveThreadId(threadId);
    setHasConversationStarted(true);
    onLandingTabChange('history');
    setQueuedPrompt(prompt);
    setQueuedAttachments(attachments);
    setQueuedToolChoice(toolChoice);
    setQueuedPromptNonce((value) => value + 1);
    void reloadThreads();
  }, [onLandingTabChange, reloadThreads]);

  const startThreadWithQueuedSend = useCallback(async (
    message: string,
    uploadedFiles: UploadedFile[] = [],
    toolChoice: ToolChoice = 'auto',
  ) => {
    if (isCreatingThread) return;

    setDraftInputError(null);
    setIsCreatingThread(true);
    const id = await createThread();
    setIsCreatingThread(false);
    if (!id) {
      setDraftInputError('创建对话失败，请稍后再试。');
      return;
    }

    queuePromptForThread(id, message, uploadedFiles.map(toAttachment), toolChoice);
  }, [isCreatingThread, queuePromptForThread]);

  const handleNewChat = useCallback(async () => {
    if (isCreatingThread) return;

    setDraftInputError(null);
    setIsCreatingThread(true);
    const id = await createThread();
    setIsCreatingThread(false);
    if (id) {
      // Reset messages before switching so the new ChatPanel (remounted via
      // key={activeThreadId}) never sees stale messages from the previous thread.
      setThreadMessages(null);
      setIsLoadingMessages(false);
      setActiveThreadId(id);
      setHasConversationStarted(false);
      onLandingTabChange('history');
      setQueuedPrompt('');
      setQueuedAttachments([]);
      setQueuedToolChoice('auto');
      void reloadThreads();
    }
    if (!id) {
      setDraftInputError('创建对话失败，请稍后再试。');
    }
    onNewChat?.();
  }, [isCreatingThread, onLandingTabChange, onNewChat, reloadThreads]);

  const handleSelectThread = useCallback((threadId: string) => {
    // Reset messages synchronously so the incoming ChatPanel (remounted via
    // key={activeThreadId}) starts with initialMessages=undefined and doesn't
    // pick up the previous thread's messages before the fetch completes.
    setThreadMessages(null);
    setIsLoadingMessages(true);
    setActiveThreadId(threadId);
    setHasConversationStarted(true);
    onLandingTabChange('history');
    setThreadSidebarOpen(false);
    setThreadSearchOpen(false);
    // Clear any pending queued prompt so the remounted ChatPanel doesn't
    // replay a previous quick-action when its lastQueuedNonceRef resets to
    // undefined on mount.
    setQueuedPrompt('');
    setQueuedAttachments([]);
    setQueuedToolChoice('auto');
  }, [onLandingTabChange]);

  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareCopied(true);
      window.setTimeout(() => setShareCopied(false), 1600);
    } catch {
      setShareCopied(false);
    }
  }, []);

  const handleDeleteThread = useCallback(async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation();
    if (deletingThreadId) return;
    setDeletingThreadId(threadId);
    const ok = await deleteThread(threadId);
    setDeletingThreadId(null);
    if (!ok) return;
    // If deleting the active thread, clear the workspace
    if (threadId === activeThreadId) {
      setActiveThreadId(null);
      setThreadMessages(null);
      setHasConversationStarted(false);
      setQueuedPrompt('');
      setQueuedAttachments([]);
      setQueuedToolChoice('auto');
    }
    setThreads((prev) => prev.filter((t) => t.id !== threadId));
  }, [deletingThreadId, activeThreadId]);

  const landingQuickActions = quickActions.length > 0 ? quickActions : DEFAULT_LANDING_QUICK_ACTIONS;
  const visibleThreads = threads;
  const trimmedThreadSearchQuery = threadSearchQuery.trim();
  const showLandingQuickActions = landingQuickActions.length > 0 && !hasConversationStarted;
  const defaultThreadGroups = useMemo(() => {
    const groups: Array<{ label: string; threads: ChatThread[] }> = [];
    const byLabel = new Map<string, ChatThread[]>();

    threads.forEach((thread) => {
      const label = getThreadDateGroup(thread.updated_at);
      if (!byLabel.has(label)) {
        byLabel.set(label, []);
        groups.push({ label, threads: byLabel.get(label) ?? [] });
      }
      byLabel.get(label)?.push(thread);
    });

    return groups;
  }, [threads]);

  return (
      <div style={{ position: 'relative', display: 'flex', width: '100%', height: '100%', minHeight: 0, minWidth: 0, overflow: 'hidden', boxSizing: 'border-box', background: 'var(--color-bg-app)', color: 'var(--color-text-primary)', fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif" }}>
        <main style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
          {/* 浮动操作按钮区 – 右上角：卡组信息 / 新建 / 更多（含下拉菜单） */}
          <div style={{ position: 'absolute', top: '0.65rem', right: '0.75rem', zIndex: 20, display: 'flex', alignItems: 'center', gap: '0.15rem' }}>
            {/* 当前 Deck Voice 徽标 */}
            {activeVoice && (() => {
              const colorHex: Record<string, string> = {
                blue: '#4da3ff', pink: '#ff66b3', green: '#52c77e',
                purple: '#9b7ff5', orange: '#f9a875', red: '#f86e6e',
                yellow: '#f5d76e', teal: '#5ec0c0'
              };
              const hex = colorHex[activeVoice.color] ?? '#4da3ff';
              const VoiceIcon = iconMap[activeVoice.icon as keyof typeof iconMap] || iconMap.brain;
              return (
                <div
                  title={activeVoice.name}
                  style={{
                    height: '2rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    padding: '0 0.6rem',
                    borderRadius: '0.55rem',
                    border: `1px solid ${hex}55`,
                    background: `${hex}18`,
                    color: hex,
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    maxWidth: '9rem',
                    overflow: 'hidden',
                  }}
                >
                  <VoiceIcon style={{ width: '0.85rem', height: '0.85rem', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {activeVoice.name}
                  </span>
                </div>
              );
            })()}
            {/* 新建对话 */}
            <button
              type="button"
              onClick={() => void handleNewChat()}
              disabled={isCreatingThread}
              style={{ height: '2rem', border: '1px solid transparent', borderRadius: '0.55rem', background: 'transparent', color: isCreatingThread ? 'var(--color-text-muted)' : 'var(--color-text-secondary)', cursor: isCreatingThread ? 'not-allowed' : 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', padding: '0 0.55rem', fontSize: '0.82rem', opacity: isCreatingThread ? 0.6 : 1, transition: 'background 0.14s ease, color 0.14s ease' }}
              title="新建对话"
              onMouseEnter={(e) => { if (!isCreatingThread) { e.currentTarget.style.background = 'var(--color-bg-surface)'; e.currentTarget.style.color = 'var(--color-text-primary)'; } }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = isCreatingThread ? 'var(--color-text-muted)' : 'var(--color-text-secondary)'; }}
            >
              <IconPlus style={{ width: '0.95rem', height: '0.95rem' }} />
              <span>{isCreatingThread ? '创建中' : '新建'}</span>
            </button>

            {/* 更多 */}
            <div style={{ position: 'relative' }}>
              <button
                type="button"
                onClick={() => setMoreMenuOpen((v) => !v)}
                style={{ width: '2rem', height: '2rem', border: '1px solid transparent', borderRadius: '0.55rem', background: moreMenuOpen ? 'var(--color-bg-surface)' : 'transparent', color: moreMenuOpen ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', cursor: 'pointer', display: 'grid', placeItems: 'center', transition: 'background 0.14s ease, color 0.14s ease' }}
                title="更多"
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-bg-surface)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
                onMouseLeave={(e) => { if (!moreMenuOpen) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; } }}
              >
                <IconMoreHorizontal style={{ width: '1.1rem', height: '1.1rem' }} />
              </button>

              {moreMenuOpen ? (
                <>
                  {/* 点击蒙层关闭菜单 */}
                  <div style={{ position: 'fixed', inset: 0, zIndex: 19 }} onClick={() => setMoreMenuOpen(false)} aria-hidden="true" />
                  {/* 下拉菜单 */}
                  <div style={{ position: 'absolute', top: '2.4rem', right: 0, zIndex: 20, minWidth: '10rem', padding: '0.35rem', border: '1px solid var(--color-border-paper)', borderRadius: '0.85rem', background: 'var(--color-bg-surface-solid)', boxShadow: '0 8px 24px var(--color-shadow-medium)', display: 'flex', flexDirection: 'column', gap: '0.05rem' }}>
                    <button
                      type="button"
                      onClick={() => {
                        if (activeThreadId) {
                          setThreadSidebarOpen((v) => !v);
                        } else {
                          onLandingTabChange('history');
                        }
                        setMoreMenuOpen(false);
                      }}
                      style={{ width: '100%', height: '2.2rem', border: 'none', borderRadius: '0.55rem', background: threadSidebarOpen ? 'var(--color-bg-surface)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0 0.65rem', fontSize: '0.83rem', textAlign: 'left' }}
                    >
                      <IconClock style={{ width: '0.95rem', height: '0.95rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
                      <span>历史对话</span>
                    </button>
                    {workspaceEnabled ? (
                      <button
                        type="button"
                        onClick={() => { setFileSidebarOpen((v) => !v); setMoreMenuOpen(false); }}
                        style={{ width: '100%', height: '2.2rem', border: 'none', borderRadius: '0.55rem', background: fileSidebarOpen ? 'var(--color-bg-surface)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0 0.65rem', fontSize: '0.83rem', textAlign: 'left' }}
                      >
                        <IconFolder style={{ width: '0.95rem', height: '0.95rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
                        <span>工作空间</span>
                      </button>
                    ) : null}
                    <div style={{ height: '1px', background: 'var(--color-border-paper)', margin: '0.2rem 0.4rem' }} />
                    <button
                      type="button"
                      onClick={() => { void handleShare(); setMoreMenuOpen(false); }}
                      style={{ width: '100%', height: '2.2rem', border: 'none', borderRadius: '0.55rem', background: 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0 0.65rem', fontSize: '0.83rem', textAlign: 'left' }}
                    >
                      <IconShare style={{ width: '0.95rem', height: '0.95rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
                      <span>{shareCopied ? '已复制链接' : '分享'}</span>
                    </button>
                  </div>
                </>
              ) : null}
            </div>
          </div>

          <div style={{ flex: 1, minHeight: 0, minWidth: 0, display: 'flex', flexDirection: 'column', padding: '3rem 0.75rem 0.75rem', gap: '0.75rem', overflow: 'hidden', boxSizing: 'border-box' }}>
            <section style={{ flex: 1, minHeight: 0, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {activeThreadId && landingTab === 'history' ? (
                <ChatPanel
                  key={activeThreadId}
                  threadId={activeThreadId}
                  initialMessages={threadMessages ?? undefined}
                  isLoading={isLoadingMessages}
                  reconnectStreamNonce={reconnectStreamNonce}
                  onReconnectComplete={notifyReconnectComplete}
                  queuedPrompt={queuedPrompt}
                  queuedAttachments={queuedAttachments}
                  queuedToolChoice={queuedToolChoice}
                  queuedPromptNonce={queuedPromptNonce}
                  inputPlaceholder="Ask Ink & Memory…"
                  editorState={editorState}
                  onEditorWriteConfirmed={onEditorWriteConfirmed}
                  voiceSystemPrompt={activeVoice?.systemPrompt}
                  onConversationStart={() => {
                    setHasConversationStarted(true);
                    void reloadThreads();
                  }}
                />
              ) : (
                <div style={{ display: 'flex', minHeight: 0, minWidth: 0, flex: 1, flexDirection: 'column', gap: '0.9rem', overflow: 'hidden' }}>
                  <div style={{ display: 'flex', minHeight: 0, minWidth: 0, flex: 1, flexDirection: 'column', gap: '0.75rem', overflow: 'hidden' }}>
                    {draftInputError ? (
                      <div style={{ margin: '0 auto', width: '100%', maxWidth: '52rem', borderRadius: '0.9rem', border: '1px solid color-mix(in srgb, var(--color-state-error) 24%, transparent)', background: 'color-mix(in srgb, var(--color-state-error) 8%, var(--color-bg-paper))', color: 'var(--color-state-error)', padding: '0.7rem 0.9rem', fontSize: '0.84rem' }}>
                        {draftInputError}
                      </div>
                    ) : null}
                    <div style={{ position: 'relative', zIndex: 10, width: '100%', maxWidth: '52rem', margin: '0 auto', flexShrink: 0, paddingBottom: '0.25rem' }}>
                      <AIInputDock
                        onSendMessage={(message, uploadedFiles = [], toolChoice = 'auto') => {
                          void startThreadWithQueuedSend(message, uploadedFiles, toolChoice);
                        }}
                        placeholder="Ask Ink & Memory…"
                        disabled={isCreatingThread}
                        loading={isCreatingThread}
                        mode="full"
                      />
                    </div>

                    {showLandingQuickActions ? (
                      <div style={{ width: '100%', maxWidth: '52rem', margin: '0 auto', flexShrink: 0 }}>
                        <QuickActionStrip
                          items={landingQuickActions}
                          onSelect={(item) => {
                            void startThreadWithQueuedSend(item.prompt);
                          }}
                        />
                      </div>
                    ) : null}

                    <section style={{ flex: 1, minHeight: 0, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      {landingTab === 'history' ? (
                        <div style={{ display: 'flex', minHeight: 0, flex: 1, flexDirection: 'column', overflow: 'hidden', border: '1px solid var(--color-border-paper)', borderRadius: '1.15rem', background: 'var(--color-bg-paper)' }}>
                          <div style={{ padding: '0.8rem 0.95rem', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', borderBottom: '1px solid var(--color-border-paper)' }}>
                            <div>
                              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>历史对话</div>
                              <div style={{ marginTop: '0.22rem', fontSize: '0.74rem', color: 'var(--color-text-secondary)' }}>
                                选择一条对话继续上下文。
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setThreadSearchQuery('');
                                setThreadSearchResults([]);
                                setThreadSearchOpen(true);
                                void reloadThreads();
                              }}
                              style={{ border: '1px solid var(--color-border-paper)', borderRadius: '999px', padding: '0.5rem 0.75rem', background: 'var(--color-bg-surface)', color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', fontWeight: 600 }}
                            >
                              <IconSearch style={{ width: '0.85rem', height: '0.85rem' }} />
                              搜索
                            </button>
                          </div>
                          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0.55rem 0.55rem 0.75rem' }}>
                            {isLoadingThreads && visibleThreads.length === 0 ? (
                              <div style={{ padding: '0.7rem 0.45rem', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>加载历史中...</div>
                            ) : null}
                            {!isLoadingThreads && visibleThreads.length === 0 ? (
                              <div style={{ padding: '0.7rem 0.45rem', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>暂无会话</div>
                            ) : null}
                            {defaultThreadGroups.map((group) => (
                              <div key={group.label} style={{ paddingTop: '0.85rem' }}>
                                <div style={{ padding: '0 0.4rem 0.45rem', color: 'var(--color-text-muted)', fontSize: '0.78rem', fontWeight: 600 }}>{group.label}</div>
                                <div style={{ display: 'grid', gap: '0.4rem' }}>
                                  {group.threads.map((thread) => {
                                    const isActive = thread.id === activeThreadId;
                                    const isHovered = thread.id === hoveredThreadId;
                                    const isDeleting = thread.id === deletingThreadId;
                                    const matchExcerpt = thread.match?.excerpt?.trim();
                                    return (
                                      <div
                                        key={thread.id}
                                        style={{ position: 'relative' }}
                                        onMouseEnter={() => setHoveredThreadId(thread.id)}
                                        onMouseLeave={() => setHoveredThreadId(null)}
                                      >
                                        <button
                                          type="button"
                                          onClick={() => handleSelectThread(thread.id)}
                                          style={{ width: '100%', minHeight: matchExcerpt ? '3.1rem' : '2.4rem', border: isActive ? '1px solid var(--color-border-paper)' : '1px solid transparent', borderRadius: '0.8rem', background: isActive ? 'var(--color-bg-app)' : isHovered ? 'var(--color-bg-hover)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.6rem', padding: '0.45rem 1.9rem 0.45rem 0.75rem', textAlign: 'left', boxSizing: 'border-box', transition: 'background 0.12s ease' }}
                                          title={thread.title ?? '新对话'}
                                        >
                                          <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.14rem', overflow: 'hidden' }}>
                                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.82rem', fontWeight: 600 }}>{thread.title ?? '新对话'}</span>
                                            {matchExcerpt ? (
                                              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.68rem', color: 'var(--color-text-muted)', lineHeight: 1.25 }}>{matchExcerpt}</span>
                                            ) : null}
                                          </span>
                                          {isActive && !isHovered ? <span style={{ width: '0.38rem', height: '0.38rem', borderRadius: '999px', background: 'var(--color-action-link)', flexShrink: 0 }} aria-hidden="true" /> : null}
                                        </button>
                                        {(isHovered || isDeleting) ? (
                                          <button
                                            type="button"
                                            onClick={(e) => void handleDeleteThread(e, thread.id)}
                                            disabled={isDeleting}
                                            title="删除对话"
                                            style={{ position: 'absolute', right: '0.38rem', top: '50%', transform: 'translateY(-50%)', width: '1.4rem', height: '1.4rem', border: 'none', borderRadius: '0.4rem', background: 'transparent', color: isDeleting ? 'var(--color-text-muted)' : 'var(--color-text-secondary)', cursor: isDeleting ? 'not-allowed' : 'pointer', display: 'grid', placeItems: 'center', padding: 0, transition: 'background 0.12s ease, color 0.12s ease', flexShrink: 0 }}
                                            onMouseEnter={(e) => { if (!isDeleting) { e.currentTarget.style.background = 'color-mix(in srgb, var(--color-state-error) 12%, transparent)'; e.currentTarget.style.color = 'var(--color-state-error)'; } }}
                                            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = isDeleting ? 'var(--color-text-muted)' : 'var(--color-text-secondary)'; }}
                                          >
                                            <IconX style={{ width: '0.75rem', height: '0.75rem' }} />
                                          </button>
                                        ) : null}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div style={{ flex: 1, minHeight: 0, minWidth: 0, display: 'flex', overflow: 'hidden' }}>
                          <ResourceConnectorPage isMobile={isMobile} embedded />
                        </div>
                      )}
                    </section>
                  </div>
                </div>
              )}
            </section>
          </div>
        </main>

        {/* 历史对话右侧面板 */}
        <aside style={{ width: threadSidebarOpen ? '16rem' : 0, minWidth: threadSidebarOpen ? '16rem' : 0, flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderLeft: threadSidebarOpen ? '1px solid var(--color-border-paper)' : 'none', background: 'var(--color-bg-paper)', transition: 'width 0.22s ease, min-width 0.22s ease' }}>
          {threadSidebarOpen ? (
            <>
              <div style={{ padding: '0.75rem 0.85rem', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-paper)' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>历史对话</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.1rem' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setThreadSearchQuery('');
                      setThreadSearchResults([]);
                      setThreadSearchOpen(true);
                      void reloadThreads();
                    }}
                    style={{ background: threadSearchOpen ? 'var(--color-bg-app)' : 'none', border: 'none', cursor: 'pointer', color: threadSearchOpen ? 'var(--color-text-primary)' : 'var(--color-text-muted)', display: 'grid', placeItems: 'center', width: '1.5rem', height: '1.5rem', borderRadius: '0.35rem' }}
                    title="搜索历史对话"
                    aria-label="搜索历史对话"
                  >
                    <IconSearch style={{ width: '0.86rem', height: '0.86rem' }} />
                  </button>
                  <button type="button" onClick={() => setThreadSidebarOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)', display: 'grid', placeItems: 'center', width: '1.5rem', height: '1.5rem', borderRadius: '0.35rem' }} title="关闭">
                    <IconX style={{ width: '0.85rem', height: '0.85rem' }} />
                  </button>
                </div>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '0.4rem 0.5rem' }}>
                {isLoadingThreads && visibleThreads.length === 0 ? (
                  <div style={{ padding: '0.55rem 0.35rem', color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>加载历史中...</div>
                ) : null}
                {!isLoadingThreads && visibleThreads.length === 0 ? (
                  <div style={{ padding: '0.55rem 0.35rem', color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>暂无会话</div>
                ) : null}
                {visibleThreads.map((thread) => {
                  const isActive = thread.id === activeThreadId;
                  const isHovered = thread.id === hoveredThreadId;
                  const isDeleting = thread.id === deletingThreadId;
                  const matchExcerpt = thread.match?.excerpt?.trim();
                  return (
                    <div
                      key={thread.id}
                      style={{ position: 'relative', marginBottom: '0.1rem' }}
                      onMouseEnter={() => setHoveredThreadId(thread.id)}
                      onMouseLeave={() => setHoveredThreadId(null)}
                    >
                      <button
                        type="button"
                        onClick={() => handleSelectThread(thread.id)}
                        style={{ width: '100%', minHeight: matchExcerpt ? '3.05rem' : '2.2rem', border: isActive ? '1px solid var(--color-border-paper)' : '1px solid transparent', borderRadius: '0.55rem', background: isActive ? 'var(--color-bg-app)' : isHovered ? 'var(--color-bg-hover)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', padding: '0.3rem 1.8rem 0.3rem 0.5rem', textAlign: 'left', boxSizing: 'border-box', transition: 'background 0.12s ease' }}
                        title={thread.title ?? '新对话'}
                      >
                        <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.12rem', overflow: 'hidden' }}>
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.78rem' }}>{thread.title ?? '新对话'}</span>
                          {matchExcerpt ? (
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.66rem', color: 'var(--color-text-muted)', lineHeight: 1.25 }}>{matchExcerpt}</span>
                          ) : null}
                        </span>
                        {isActive && !isHovered ? <span style={{ width: '0.38rem', height: '0.38rem', borderRadius: '999px', background: 'var(--color-action-link)', flexShrink: 0 }} aria-hidden="true" /> : null}
                      </button>
                      {(isHovered || isDeleting) ? (
                        <button
                          type="button"
                          onClick={(e) => void handleDeleteThread(e, thread.id)}
                          disabled={isDeleting}
                          title="删除对话"
                          style={{ position: 'absolute', right: '0.3rem', top: '50%', transform: 'translateY(-50%)', width: '1.4rem', height: '1.4rem', border: 'none', borderRadius: '0.35rem', background: 'transparent', color: isDeleting ? 'var(--color-text-muted)' : 'var(--color-text-secondary)', cursor: isDeleting ? 'not-allowed' : 'pointer', display: 'grid', placeItems: 'center', padding: 0, transition: 'background 0.12s ease, color 0.12s ease', flexShrink: 0 }}
                          onMouseEnter={(e) => { if (!isDeleting) { e.currentTarget.style.background = 'color-mix(in srgb, var(--color-state-error) 12%, transparent)'; e.currentTarget.style.color = 'var(--color-state-error)'; } }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = isDeleting ? 'var(--color-text-muted)' : 'var(--color-text-secondary)'; }}
                        >
                          <IconX style={{ width: '0.75rem', height: '0.75rem' }} />
                        </button>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </>
          ) : null}
        </aside>

        {threadSearchOpen ? (
          <div
            role="presentation"
            onClick={(event) => {
              if (event.target === event.currentTarget) {
                setThreadSearchOpen(false);
              }
            }}
            style={{ position: 'fixed', inset: 0, zIndex: 60, display: 'grid', placeItems: 'center', padding: 'clamp(1rem, 5vw, 4rem)', background: 'color-mix(in srgb, var(--color-bg-app) 64%, transparent)' }}
          >
            <section
              role="dialog"
              aria-modal="true"
              aria-label="搜索历史对话"
              style={{ width: 'min(48rem, calc(100vw - 2rem))', height: 'min(36rem, calc(100vh - 4rem))', minHeight: '24rem', display: 'flex', flexDirection: 'column', overflow: 'hidden', border: '1px solid color-mix(in srgb, var(--color-border-paper) 84%, var(--color-text-muted))', borderRadius: '1rem', background: 'var(--color-bg-paper)', boxShadow: '0 30px 80px color-mix(in srgb, var(--color-shadow-medium) 72%, transparent)' }}
            >
              <div style={{ height: '4.15rem', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0 1.45rem', borderBottom: '1px solid var(--color-border-paper)' }}>
                <input
                  ref={threadSearchInputRef}
                  value={threadSearchQuery}
                  onChange={(event) => setThreadSearchQuery(event.target.value)}
                  placeholder="搜索聊天..."
                  aria-label="搜索历史对话"
                  autoComplete="off"
                  style={{ minWidth: 0, flex: 1, height: '100%', border: 'none', background: 'transparent', color: 'var(--color-text-primary)', outline: 'none', fontSize: '1.18rem', fontWeight: 600, fontFamily: 'inherit' }}
                />
                <button
                  type="button"
                  title="关闭"
                  aria-label="关闭搜索"
                  onClick={() => setThreadSearchOpen(false)}
                  style={{ width: '2rem', height: '2rem', border: 'none', borderRadius: '0.5rem', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', display: 'grid', placeItems: 'center', flexShrink: 0 }}
                >
                  <IconX style={{ width: '1.05rem', height: '1.05rem' }} />
                </button>
              </div>

              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: trimmedThreadSearchQuery ? '1rem 0.75rem' : '0.75rem' }}>
                {trimmedThreadSearchQuery ? (
                  <>
                    {isSearchingThreads ? (
                      <div style={{ padding: '0.8rem 1rem', color: 'var(--color-text-muted)', fontSize: '0.86rem' }}>搜索中...</div>
                    ) : null}
                    {!isSearchingThreads && threadSearchResults.length === 0 ? (
                      <div style={{ padding: '0.8rem 1rem', color: 'var(--color-text-muted)', fontSize: '0.86rem' }}>未找到匹配会话</div>
                    ) : null}
                    {threadSearchResults.map((thread) => {
                      const matchExcerpt = thread.match?.excerpt?.trim();
                      const isActive = thread.id === activeThreadId;
                      return (
                        <button
                          key={thread.id}
                          type="button"
                          onClick={() => handleSelectThread(thread.id)}
                          style={{ width: '100%', minHeight: matchExcerpt ? '4.35rem' : '3.3rem', border: 'none', borderRadius: '0.75rem', background: isActive ? 'var(--color-bg-hover)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'grid', gridTemplateColumns: '1.8rem minmax(0, 1fr) auto', alignItems: 'center', gap: '0.75rem', padding: '0.68rem 0.9rem', textAlign: 'left', transition: 'background 0.12s ease' }}
                          title={thread.title ?? '新对话'}
                          onMouseEnter={(event) => { event.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                          onMouseLeave={(event) => { event.currentTarget.style.background = isActive ? 'var(--color-bg-hover)' : 'transparent'; }}
                        >
                          <IconMessageCircle style={{ width: '1.28rem', height: '1.28rem', color: 'var(--color-text-primary)' }} />
                          <span style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.18rem' }}>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '1rem', fontWeight: 600 }}>{thread.title ?? '新对话'}</span>
                            {matchExcerpt ? (
                              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-secondary)', fontSize: '0.86rem', lineHeight: 1.35 }}>{matchExcerpt}</span>
                            ) : null}
                          </span>
                          <span style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem', whiteSpace: 'nowrap', alignSelf: matchExcerpt ? 'center' : 'center' }}>{formatThreadDateLabel(thread.updated_at)}</span>
                        </button>
                      );
                    })}
                  </>
                ) : (
                  <>
                    {defaultThreadGroups.length === 0 ? (
                      <div style={{ padding: '1rem 0.25rem', color: 'var(--color-text-muted)', fontSize: '0.86rem' }}>暂无会话</div>
                    ) : null}

                    {defaultThreadGroups.map((group) => (
                      <div key={group.label} style={{ paddingTop: '1rem' }}>
                        <div style={{ padding: '0 1rem 0.45rem', color: 'var(--color-text-muted)', fontSize: '0.82rem', fontWeight: 600 }}>{group.label}</div>
                        {group.threads.map((thread) => {
                          const isActive = thread.id === activeThreadId;
                          return (
                            <button
                              key={thread.id}
                              type="button"
                              onClick={() => handleSelectThread(thread.id)}
                              style={{ width: '100%', height: '2.8rem', border: 'none', borderRadius: '0.75rem', background: isActive ? 'var(--color-bg-hover)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.78rem', padding: '0 1rem', textAlign: 'left', transition: 'background 0.12s ease' }}
                              title={thread.title ?? '新对话'}
                              onMouseEnter={(event) => { event.currentTarget.style.background = 'var(--color-bg-hover)'; }}
                              onMouseLeave={(event) => { event.currentTarget.style.background = isActive ? 'var(--color-bg-hover)' : 'transparent'; }}
                            >
                              <IconMessageCircle style={{ width: '1.18rem', height: '1.18rem', flexShrink: 0, color: 'var(--color-text-primary)' }} />
                              <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.96rem', fontWeight: 600 }}>{thread.title ?? '新对话'}</span>
                            </button>
                          );
                        })}
                      </div>
                    ))}
                  </>
                )}
              </div>
            </section>
          </div>
        ) : null}

        {workspaceEnabled ? (
          <FileSidebar sessionId={activeThreadId ?? ''} open={fileSidebarOpen} onClose={() => setFileSidebarOpen(false)} />
        ) : null}
      </div>
  );
}

function ChatViewShell(props: ChatViewProps) {
  const [landingTab, setLandingTab] = useState<ChatLandingTab>(props.landingTab ?? 'history');
  const [shellRetryNonce, setShellRetryNonce] = useState(0);

  useEffect(() => {
    setLandingTab(props.landingTab ?? 'history');
  }, [props.landingTab]);

  const handleSelectLandingTab = useCallback((tab: ChatLandingTab) => {
    setLandingTab(tab);
  }, []);

  const handleRecoverLandingTab = useCallback((tab: ChatLandingTab) => {
    setLandingTab(tab);
    setShellRetryNonce((value) => value + 1);
  }, []);

  const handleRetryShell = useCallback(() => {
    setShellRetryNonce((value) => value + 1);
  }, []);

  const handleReloadShell = useCallback(() => {
    window.location.reload();
  }, []);

  return (
    <ChatShellBoundary
      key={shellRetryNonce}
      fallback={(error) => (
        <ChatShellError
          error={error}
          landingTab={landingTab}
          isMobile={props.isMobile}
          onSelectLandingTab={handleRecoverLandingTab}
          onRetry={handleRetryShell}
          onReload={handleReloadShell}
        />
      )}
    >
      <ChatViewContent
        {...props}
        landingTab={landingTab}
        onLandingTabChange={handleSelectLandingTab}
      />
    </ChatShellBoundary>
  );
}

export default function ChatView(props: ChatViewProps) {
  return (
    <WorkspaceProvider>
      <ChatViewShell {...props} />
    </WorkspaceProvider>
  );
}
