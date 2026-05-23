import { IconClock, IconFolder, IconGrid, IconSettings, IconUser } from '../chat/Icons';

interface VerticalNavProps {
  onToggleFileSidebar: () => void;
  onNavigateToSettings?: () => void;
  unreadCount?: number;
}

export default function VerticalNav({ onToggleFileSidebar, onNavigateToSettings, unreadCount = 0 }: VerticalNavProps) {
  return (
    <aside style={{ width: '4rem', flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '1.25rem 0.75rem', borderRight: '1px solid var(--color-border-paper)', background: 'var(--color-bg-app)' }}>
      <div style={{ marginBottom: '1.75rem', display: 'grid', placeItems: 'center', width: '2.2rem', height: '2.2rem', borderRadius: '12px', background: 'var(--color-action-link)', color: 'var(--color-text-on-action)' }}>
        <IconGrid style={{ width: '1rem', height: '1rem' }} />
      </div>
      <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', gap: '1.35rem', color: 'var(--color-text-muted)' }}>
        <button type="button" onClick={onToggleFileSidebar} title="Files" style={{ position: 'relative', border: 'none', background: 'transparent', color: 'var(--color-action-link)', cursor: 'pointer' }}>
          <IconFolder style={{ width: '1.2rem', height: '1.2rem' }} />
          {unreadCount > 0 ? <span style={{ position: 'absolute', top: '-0.45rem', right: '-0.6rem', minWidth: '1rem', height: '1rem', padding: '0 0.2rem', borderRadius: '999px', background: 'var(--color-action-link)', color: 'var(--color-text-on-action)', fontSize: '0.6rem', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{unreadCount}</span> : null}
        </button>
        <button type="button" style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer' }}><IconClock style={{ width: '1.2rem', height: '1.2rem' }} /></button>
        <button
          type="button"
          onClick={onNavigateToSettings}
          title="Settings"
          style={{ border: 'none', background: 'transparent', color: onNavigateToSettings ? 'var(--color-text-secondary)' : 'inherit', cursor: onNavigateToSettings ? 'pointer' : 'default', transition: 'color 0.2s ease' }}
        >
          <IconSettings style={{ width: '1.2rem', height: '1.2rem' }} />
        </button>
      </div>
      <div style={{ padding: '0.35rem', borderRadius: '999px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)' }}>
        <IconUser style={{ width: '1rem', height: '1rem', color: 'var(--color-text-secondary)' }} />
      </div>
    </aside>
  );
}
