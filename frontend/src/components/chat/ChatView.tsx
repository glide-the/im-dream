import { useMemo, useState } from 'react';
import '../../styles/markdown.css';
import { WorkspaceProvider } from '../../contexts/WorkspaceContext';
import FileSidebar from '../dashboard/FileSidebar';
import QuickActionCard from '../dashboard/QuickActionCard';
import { QUICK_ACTION_CARDS, type QuickActionCardItem } from '../dashboard/const';
import VerticalNav from '../dashboard/VerticalNav';
import ChatPanel from './ChatPanel';
import type { Attachment, ContextCustomer } from './AIInputDock';

interface ChatViewProps {
  title?: string;
  threadId?: string;
  contextCustomerId?: string;
  contextCustomers?: ContextCustomer[];
  onNewChat?: () => void;
  onNavigateToSettings?: () => void;
  quickActions?: QuickActionCardItem[];
}

export default function ChatView({
  title = 'Untitled conversation',
  threadId = 'chat-view',
  contextCustomerId,
  contextCustomers = [],
  onNewChat,
  onNavigateToSettings,
  quickActions = QUICK_ACTION_CARDS,
}: ChatViewProps) {
  const [fileSidebarOpen, setFileSidebarOpen] = useState(false);
  const [queuedPrompt, setQueuedPrompt] = useState('');
  const [queuedAttachments, setQueuedAttachments] = useState<Attachment[]>([]);
  const [queuedPromptNonce, setQueuedPromptNonce] = useState(0);
  const [hasConversationStarted, setHasConversationStarted] = useState(false);

  const quickActionsGrid = useMemo(() => quickActions.length > 0, [quickActions.length]);

  return (
    <WorkspaceProvider>
      <div style={{ display: 'flex', height: '100%', overflow: 'hidden', background: 'var(--color-bg-app)', color: 'var(--color-text-primary)', fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif" }}>
        <VerticalNav onToggleFileSidebar={() => setFileSidebarOpen((value) => !value)} onNavigateToSettings={onNavigateToSettings} unreadCount={0} />

        <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', padding: '1rem', gap: '1rem', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', padding: '0.25rem 0.25rem 0 0.25rem', flexShrink: 0 }}>
            <div>
              <div style={{ fontSize: '0.74rem', letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>Session</div>
              <h1 style={{ margin: '0.2rem 0 0', fontSize: '1.35rem', color: 'var(--color-text-primary)' }}>{title}</h1>
            </div>
            <button type="button" onClick={onNewChat} style={{ border: '1px solid var(--color-border-paper)', borderRadius: '999px', padding: '0.7rem 1rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', fontWeight: 600, cursor: 'pointer' }}>New chat</button>
          </div>

          {quickActionsGrid && !hasConversationStarted ? (
            <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', flexShrink: 0 }}>
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
              threadId={threadId}
              contextCustomerId={contextCustomerId}
              contextCustomers={contextCustomers}
              queuedPrompt={queuedPrompt}
              queuedAttachments={queuedAttachments}
              queuedPromptNonce={queuedPromptNonce}
              inputPlaceholder="Ask Ink & Memory…"
              onConversationStart={() => setHasConversationStarted(true)}
            />
          </section>
        </main>

        <FileSidebar sessionId={threadId} open={fileSidebarOpen} onClose={() => setFileSidebarOpen(false)} />
      </div>
    </WorkspaceProvider>
  );
}

