// [Input] Consume WorkspaceContext, dashboard file/nav/quick-action components, ChatPanel, auth token, and AI SDK message types.
// [Output] Render chat workspace with ChatGPT-style sidebar (thread list inside VerticalNav), file sidebar, quick actions, and ChatPanel.
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
import { useMemo, useState, useEffect, useCallback } from 'react';
import '../../styles/markdown.css';
import { WorkspaceProvider } from '../../contexts/WorkspaceContext';
import FileSidebar from '../dashboard/FileSidebar';
import QuickActionCard from '../dashboard/QuickActionCard';
import { QUICK_ACTION_CARDS, type QuickActionCardItem } from '../dashboard/const';
import ChatPanel from './ChatPanel';
import type { Attachment } from './AIInputDock.helpers';
import type { UIMessage } from 'ai';
import { getAuthToken } from '../../contexts/AuthContext';
import { IconClock, IconFolder, IconMoreHorizontal, IconPlus, IconShare, IconX } from './Icons';
import type { ActiveChatVoice } from '../../lib/chat-schema';
import { iconMap } from '../deckVisuals';

const API_BASE = '/ink-and-memory';

interface ChatThread {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
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
  quickActions?: QuickActionCardItem[];
  /** Current EditorState snapshot passed down to ChatPanel for agent editor_state injection. */
  editorState?: Record<string, unknown> | null;
  /** Called when an editor write tool is confirmed so the Writing view can reload. */
  onEditorWriteConfirmed?: () => void;
  /** Active deck / voice info — displayed in the top-right badge and forwarded to the backend as voice context. */
  activeVoice?: ActiveChatVoice;
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

async function fetchThreads(): Promise<ChatThread[]> {
  try {
    const res = await fetch(`${API_BASE}/api/claude-agent/threads`, { headers: { 'Authorization': `Bearer ${getAuthToken()}` } });
    if (!res.ok) return [];
    const data = await res.json() as { threads: ChatThread[] };
    return data.threads ?? [];
  } catch {
    return [];
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

async function deleteThread(threadId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${getAuthToken()}` } });
    return res.ok;
  } catch {
    return false;
  }
}

export default function ChatView({
  threadId: initialThreadId,
  requestedThreadId,
  onNewChat,
  quickActions = QUICK_ACTION_CARDS,
  editorState,
  onEditorWriteConfirmed,
  activeVoice,
}: ChatViewProps) {
  const [fileSidebarOpen, setFileSidebarOpen] = useState(false);
  const [queuedPrompt, setQueuedPrompt] = useState('');
  const [queuedAttachments, setQueuedAttachments] = useState<Attachment[]>([]);
  const [queuedPromptNonce, setQueuedPromptNonce] = useState(0);
  const [hasConversationStarted, setHasConversationStarted] = useState(false);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(initialThreadId ?? null);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [threadSidebarOpen, setThreadSidebarOpen] = useState(false);
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [threadMessages, setThreadMessages] = useState<UIMessage[] | null>(null);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [threadSearchQuery, setThreadSearchQuery] = useState('');
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);

  // Create an initial thread if none provided
  useEffect(() => {
    if (activeThreadId) return;
    let cancelled = false;
    void (async () => {
      const id = await createThread();
      if (!cancelled && id) setActiveThreadId(id);
    })();
    return () => { cancelled = true; };
  }, [activeThreadId]);

  // Load thread list
  const reloadThreads = useCallback(async () => {
    const list = await fetchThreads();
    setThreads(list);
  }, []);

  useEffect(() => {
    void reloadThreads();
  }, [reloadThreads]);

  // @@@ External navigation: switch to a specific thread when requestedThreadId changes.
  useEffect(() => {
    if (!requestedThreadId || requestedThreadId === activeThreadId) return;
    setThreadMessages(null);
    setIsLoadingMessages(true);
    setActiveThreadId(requestedThreadId);
    setHasConversationStarted(true);
    setQueuedPrompt('');
    setQueuedAttachments([]);
    void reloadThreads();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestedThreadId]);

  // Fetch messages for the active thread (following better-chatbot pattern:
  // parent fetches history and passes as initialMessages to the chat component)
  useEffect(() => {
    if (!activeThreadId) return;
    let cancelled = false;
    setIsLoadingMessages(true);
    setThreadMessages(null);
    void (async () => {
      const msgs = await fetchThreadMessages(activeThreadId);
      if (!cancelled) {
        setThreadMessages(msgs);
        if (msgs.length > 0) {
          setHasConversationStarted(true);
        }
        setIsLoadingMessages(false);
      }
    })();
    return () => { cancelled = true; };
  }, [activeThreadId]);

  const handleNewChat = useCallback(async () => {
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
      setQueuedPrompt('');
      setQueuedAttachments([]);
      void reloadThreads();
    }
    onNewChat?.();
  }, [onNewChat, reloadThreads]);

  const handleSelectThread = useCallback((threadId: string) => {
    // Reset messages synchronously so the incoming ChatPanel (remounted via
    // key={activeThreadId}) starts with initialMessages=undefined and doesn't
    // pick up the previous thread's messages before the fetch completes.
    setThreadMessages(null);
    setIsLoadingMessages(true);
    setActiveThreadId(threadId);
    setHasConversationStarted(true);
    setThreadSidebarOpen(false);
    // Clear any pending queued prompt so the remounted ChatPanel doesn't
    // replay a previous quick-action when its lastQueuedNonceRef resets to
    // undefined on mount.
    setQueuedPrompt('');
    setQueuedAttachments([]);
  }, []);

  const handleDeleteThread = useCallback(async (threadId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const ok = await deleteThread(threadId);
    if (ok) {
      const remaining = threads.filter((t) => t.id !== threadId);
      setThreads(remaining);
      if (threadId === activeThreadId) {
        if (remaining.length > 0) {
          setActiveThreadId(remaining[0].id);
          setHasConversationStarted(true);
        } else {
          setActiveThreadId(null);
          setHasConversationStarted(false);
        }
      }
    }
  }, [activeThreadId, threads]);

  const handleShare = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareCopied(true);
      window.setTimeout(() => setShareCopied(false), 1600);
    } catch {
      setShareCopied(false);
    }
  }, []);

  const quickActionsGrid = useMemo(() => quickActions.length > 0, [quickActions.length]);
  const visibleThreads = useMemo(() => {
    const query = threadSearchQuery.trim().toLowerCase();
    if (!query) return threads;
    return threads.filter((thread) => (thread.title ?? '新对话').toLowerCase().includes(query));
  }, [threadSearchQuery, threads]);

  if (!activeThreadId) {
    return (
      <WorkspaceProvider>
        <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg-app)', color: 'var(--color-text-muted)' }}>
          {isCreatingThread ? 'Starting chat…' : 'Initializing…'}
        </div>
      </WorkspaceProvider>
    );
  }

  return (
    <WorkspaceProvider>
      <div style={{ position: 'relative', display: 'flex', height: '100%', overflow: 'hidden', background: 'var(--color-bg-app)', color: 'var(--color-text-primary)', fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif" }}>
        <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
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
                      onClick={() => { setThreadSidebarOpen((v) => !v); setMoreMenuOpen(false); }}
                      style={{ width: '100%', height: '2.2rem', border: 'none', borderRadius: '0.55rem', background: threadSidebarOpen ? 'var(--color-bg-surface)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0 0.65rem', fontSize: '0.83rem', textAlign: 'left' }}
                    >
                      <IconClock style={{ width: '0.95rem', height: '0.95rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
                      <span>历史对话</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => { setFileSidebarOpen((v) => !v); setMoreMenuOpen(false); }}
                      style={{ width: '100%', height: '2.2rem', border: 'none', borderRadius: '0.55rem', background: fileSidebarOpen ? 'var(--color-bg-surface)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0 0.65rem', fontSize: '0.83rem', textAlign: 'left' }}
                    >
                      <IconFolder style={{ width: '0.95rem', height: '0.95rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
                      <span>工作空间</span>
                    </button>
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

          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', padding: '3rem 0.75rem 0.75rem', gap: '0.75rem', overflow: 'hidden' }}>
            {quickActionsGrid && !hasConversationStarted ? (
              <div style={{ display: 'grid', gap: '0.75rem', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', flexShrink: 0 }}>
                {quickActions.map((item) => (
                  <QuickActionCard
                    key={item.title}
                    item={item}
                    onClick={(prompt) => {
                      setHasConversationStarted(true);
                      setQueuedPrompt(prompt);
                      setQueuedAttachments([]);
                      setQueuedPromptNonce((value) => value + 1);
                    }}
                  />
                ))}
              </div>
            ) : null}

            <section style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <ChatPanel
                key={activeThreadId}
                threadId={activeThreadId}
                initialMessages={threadMessages ?? undefined}
                isLoading={isLoadingMessages}
                queuedPrompt={queuedPrompt}
                queuedAttachments={queuedAttachments}
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
            </section>
          </div>
        </main>

        {/* 历史对话右侧面板 */}
        <aside style={{ width: threadSidebarOpen ? '16rem' : 0, minWidth: threadSidebarOpen ? '16rem' : 0, flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderLeft: threadSidebarOpen ? '1px solid var(--color-border-paper)' : 'none', background: 'var(--color-bg-paper)', transition: 'width 0.22s ease, min-width 0.22s ease' }}>
          {threadSidebarOpen ? (
            <>
              <div style={{ padding: '0.75rem 0.85rem', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-paper)' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>历史对话</span>
                <button type="button" onClick={() => setThreadSidebarOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)', display: 'grid', placeItems: 'center', width: '1.5rem', height: '1.5rem', borderRadius: '0.35rem' }} title="关闭">
                  <IconX style={{ width: '0.85rem', height: '0.85rem' }} />
                </button>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '0.4rem 0.5rem' }}>
                {visibleThreads.length === 0 ? (
                  <div style={{ padding: '0.55rem 0.35rem', color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>暂无会话</div>
                ) : null}
                {visibleThreads.map((thread) => {
                  const isActive = thread.id === activeThreadId;
                  return (
                    <button
                      key={thread.id}
                      type="button"
                      onClick={() => handleSelectThread(thread.id)}
                      style={{ width: '100%', minHeight: '2.2rem', border: isActive ? '1px solid var(--color-border-paper)' : '1px solid transparent', borderRadius: '0.55rem', background: isActive ? 'var(--color-bg-app)' : 'transparent', color: 'var(--color-text-primary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', padding: '0.3rem 0.5rem', textAlign: 'left', boxSizing: 'border-box', marginBottom: '0.1rem', transition: 'background 0.12s ease' }}
                      title={thread.title ?? '新对话'}
                    >
                      <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.78rem' }}>{thread.title ?? '新对话'}</span>
                      {isActive ? <span style={{ width: '0.38rem', height: '0.38rem', borderRadius: '999px', background: 'var(--color-action-link)', flexShrink: 0 }} aria-hidden="true" /> : null}
                    </button>
                  );
                })}
              </div>
            </>
          ) : null}
        </aside>

        <FileSidebar sessionId={activeThreadId} open={fileSidebarOpen} onClose={() => setFileSidebarOpen(false)} />
      </div>
    </WorkspaceProvider>
  );
}
