import { useMemo, useState } from 'react';
import '../../styles/markdown.css';
import { WorkspaceProvider } from '../../contexts/WorkspaceContext';
import FileSidebar from '../dashboard/FileSidebar';
import QuickActionCard from '../dashboard/QuickActionCard';
import Sidebar from '../dashboard/Sidebar';
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
  quickActions?: QuickActionCardItem[];
}

export default function ChatView({
  title = 'Untitled conversation',
  threadId = 'chat-view',
  contextCustomerId,
  contextCustomers = [],
  onNewChat,
  quickActions = QUICK_ACTION_CARDS,
}: ChatViewProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [fileSidebarOpen, setFileSidebarOpen] = useState(true);
  const [queuedPrompt, setQueuedPrompt] = useState('');
  const [queuedAttachments, setQueuedAttachments] = useState<Attachment[]>([]);
  const [queuedPromptNonce, setQueuedPromptNonce] = useState(0);

  const quickActionsGrid = useMemo(() => quickActions.length > 0, [quickActions.length]);

  return (
    <WorkspaceProvider>
      <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg-app)', color: 'var(--color-text-primary)', fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif" }}>
        <VerticalNav onToggleSidebar={() => setSidebarCollapsed((value) => !value)} onToggleFileSidebar={() => setFileSidebarOpen((value) => !value)} unreadCount={0} />
        <Sidebar open={!sidebarCollapsed} desktopCollapsed={sidebarCollapsed} onClose={() => setSidebarCollapsed(true)} />

        <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', padding: '1rem', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', padding: '0.25rem 0.25rem 0 0.25rem' }}>
            <div>
              <div style={{ fontSize: '0.74rem', letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>Session</div>
              <h1 style={{ margin: '0.2rem 0 0', fontSize: '1.35rem', color: 'var(--color-text-primary)' }}>{title}</h1>
            </div>
            <button type="button" onClick={onNewChat} style={{ border: '1px solid var(--color-border-paper)', borderRadius: '999px', padding: '0.7rem 1rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', fontWeight: 600, cursor: 'pointer' }}>New chat</button>
          </div>

          {quickActionsGrid ? (
            <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {quickActions.map((item) => (
                <QuickActionCard
                  key={item.title}
                  item={item}
                  onClick={(prompt) => {
                    setQueuedPrompt(prompt);
                    setQueuedAttachments([]);
                    setQueuedPromptNonce((value) => value + 1);
                  }}
                />
              ))}
            </div>
          ) : null}

          <section style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <ChatPanel
              threadId={threadId}
              contextCustomerId={contextCustomerId}
              contextCustomers={contextCustomers}
              queuedPrompt={queuedPrompt}
              queuedAttachments={queuedAttachments}
              queuedPromptNonce={queuedPromptNonce}
              inputPlaceholder="Ask Ink & Memory…"
            />
          </section>
        </main>

        <FileSidebar sessionId={threadId} open={fileSidebarOpen} onClose={() => setFileSidebarOpen(false)} />
      </div>
    </WorkspaceProvider>
  );
}
