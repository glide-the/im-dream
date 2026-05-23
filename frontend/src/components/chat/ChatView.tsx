import { useEffect, useMemo, useState } from 'react';
import type { UIMessage } from 'ai';
import AIInputDock, { type ToolChoice, type UploadedFile } from './AIInputDock';
import ChatMessageList from './ChatMessageList';
import '../../styles/markdown.css';
import Sidebar, { type ThemeMode } from '../dashboard/Sidebar';
import FileSidebar, { type FileInfo } from '../dashboard/FileSidebar';
import QuickActionCard from '../dashboard/QuickActionCard';
import { QUICK_ACTION_CARDS, type QuickActionCardItem } from '../dashboard/const';
import VerticalNav from '../dashboard/VerticalNav';

interface ChatViewProps {
  title?: string;
  messages: UIMessage[];
  isLoading?: boolean;
  error?: Error | null;
  files?: FileInfo[];
  addToolResult?: (args: { tool: string; toolCallId: string; output: unknown }) => void;
  onSendMessage: (message: string, files?: UploadedFile[], customerIds?: string[], toolChoice?: ToolChoice) => void;
  onNewChat?: () => void;
  onFilesChange?: (files: FileInfo[]) => void;
  quickActions?: QuickActionCardItem[];
}

export default function ChatView({ title = 'Untitled conversation', messages, isLoading = false, error, files = [], addToolResult = () => undefined, onSendMessage, onNewChat, onFilesChange, quickActions = QUICK_ACTION_CARDS }: ChatViewProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [fileSidebarOpen, setFileSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<ThemeMode>('light');
  const [systemPrompt, setSystemPrompt] = useState('You are a concise and reflective writing assistant.');
  const [selectedModel, setSelectedModel] = useState('auto');
  const [workspaceMode, setWorkspaceMode] = useState(true);

  const emptyState = useMemo(() => messages.length === 0, [messages.length]);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme === 'dark' ? 'dark' : 'light';
  }, [theme]);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--color-bg-app)', color: 'var(--color-text-primary)', fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif" }}>
      <VerticalNav onToggleSidebar={() => setSidebarCollapsed((value) => !value)} onToggleFileSidebar={() => setFileSidebarOpen((value) => !value)} unreadCount={files.length} />
      <Sidebar open={!sidebarCollapsed} desktopCollapsed={sidebarCollapsed} onClose={() => setSidebarCollapsed(true)} theme={theme} onThemeChange={setTheme} systemPrompt={systemPrompt} onSystemPromptChange={setSystemPrompt} onSavePrompt={setSystemPrompt} workspaceMode={workspaceMode} onWorkspaceToggle={() => setWorkspaceMode((value) => !value)} selectedModel={selectedModel} onModelChange={setSelectedModel} title="Chat sidebar" />

      <main style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', padding: '1rem', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', padding: '0.25rem 0.25rem 0 0.25rem' }}>
          <div>
            <div style={{ fontSize: '0.74rem', letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>Session</div>
            <h1 style={{ margin: '0.2rem 0 0', fontSize: '1.35rem', color: 'var(--color-text-primary)' }}>{title}</h1>
          </div>
          <button type="button" onClick={onNewChat} style={{ border: '1px solid var(--color-border-paper)', borderRadius: '999px', padding: '0.7rem 1rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', fontWeight: 600, cursor: 'pointer' }}>New chat</button>
        </div>

        <section style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', border: '1px solid var(--color-border-paper)', borderRadius: '8px', background: 'var(--color-bg-paper)', overflow: 'hidden' }}>
          <div style={{ flex: 1, overflow: 'auto', padding: '1.25rem' }}>
            {emptyState ? (
              <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
                {quickActions.map((item) => <QuickActionCard key={item.title} item={item} onClick={(prompt) => onSendMessage(prompt)} />)}
              </div>
            ) : (
              <ChatMessageList messages={messages} isLoading={isLoading} error={error} addToolResult={addToolResult} shouldShowLoadingIndicator={isLoading} />
            )}
          </div>
          <AIInputDock onSendMessage={onSendMessage} loading={isLoading} mode="full" />
        </section>
      </main>

      <FileSidebar sessionId="chat-view" open={fileSidebarOpen} onClose={() => setFileSidebarOpen(false)} files={files} onFilesChange={onFilesChange} />
    </div>
  );
}
