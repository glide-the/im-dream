// [Input] ResourceConnectorPage page mode and shared chat icons.
// [Output] Dedicated "具体配置页面" for the Notion connector: a top breadcrumb navigation
//          bar followed by the existing ResourceConnectorPage workbench, rendered as a full
//          page that replaces the Settings viewport instead of expanding inline in a card.
// [Pos] connector-notion-detail-page node in frontend/src/components/dashboard
// [Sync] 2026-07-08: initial dedicated navigation page for the Notion "具体配置页面", fixing the
//                    Settings 管理 action so it navigates to a new page instead of an inline toggle.
import { IconChevronLeft, IconChevronRight } from '../chat/Icons';
import ResourceConnectorPage from './ResourceConnectorPage';

interface ConnectorNotionDetailPageProps {
  onBack: () => void;
  isMobile?: boolean;
}

export default function ConnectorNotionDetailPage({ onBack, isMobile = false }: ConnectorNotionDetailPageProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      <nav
        aria-label="链接器具体配置页面导航"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          flexWrap: 'wrap',
          fontSize: '0.85rem',
          color: 'var(--color-text-secondary)',
        }}
      >
        <button
          type="button"
          onClick={onBack}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            border: '1px solid var(--color-border-paper)',
            borderRadius: '999px',
            padding: '0.45rem 0.8rem',
            background: 'var(--color-bg-paper)',
            color: 'var(--color-text-primary)',
            cursor: 'pointer',
            fontSize: '0.82rem',
            fontWeight: 700,
          }}
        >
          <IconChevronLeft style={{ width: '0.88rem', height: '0.88rem' }} />
          设置
        </button>
        <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        <button
          type="button"
          onClick={onBack}
          style={{
            border: 'none',
            background: 'transparent',
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
            fontSize: '0.82rem',
            fontWeight: 600,
            padding: '0.2rem 0',
          }}
        >
          资源链接
        </button>
        <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>Notion 具体配置页面</span>
      </nav>

      <div
        style={{
          border: '1px solid var(--color-border-paper)',
          borderRadius: '1.5rem',
          overflow: 'hidden',
          background: 'var(--color-bg-paper)',
        }}
      >
        <ResourceConnectorPage isMobile={isMobile} />
      </div>
    </div>
  );
}
