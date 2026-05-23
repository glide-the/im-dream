import { useCallback, useState, type ReactNode } from 'react';
import { WorkspaceProvider, useWorkspaceSession } from '../contexts/WorkspaceContext';
import FileSidebar from './dashboard/FileSidebar';
import Sidebar from './dashboard/Sidebar';
import VerticalNav from './dashboard/VerticalNav';

function AppLayoutShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [fileSidebarOpen, setFileSidebarOpen] = useState(false);
  const { activeSessionId } = useWorkspaceSession();
  const fileSidebarSessionId = activeSessionId ?? 'shared-workspace';

  const handleToggleSidebar = useCallback(() => {
    setFileSidebarOpen(false);
    if (window.innerWidth >= 768) {
      setDesktopCollapsed((value) => !value);
    } else {
      setSidebarOpen((value) => !value);
    }
  }, []);

  const handleToggleFileSidebar = useCallback(() => {
    const nextOpen = !fileSidebarOpen;
    setFileSidebarOpen(nextOpen);
    if (nextOpen) {
      setSidebarOpen(false);
      if (window.innerWidth >= 768) {
        setDesktopCollapsed(true);
      }
    }
  }, [fileSidebarOpen]);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', overflow: 'hidden', background: 'var(--color-bg-app)' }}>
      <VerticalNav onToggleSidebar={handleToggleSidebar} onToggleFileSidebar={handleToggleFileSidebar} />
      <Sidebar open={sidebarOpen} desktopCollapsed={desktopCollapsed} onClose={() => setSidebarOpen(false)} />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: '1rem 1rem 2rem' }}>{children}</main>
      <FileSidebar sessionId={fileSidebarSessionId} open={fileSidebarOpen} onClose={() => setFileSidebarOpen(false)} />
    </div>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <WorkspaceProvider>
      <AppLayoutShell>{children}</AppLayoutShell>
    </WorkspaceProvider>
  );
}
