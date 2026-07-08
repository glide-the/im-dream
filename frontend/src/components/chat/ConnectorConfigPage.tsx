// [Input] ResourceConnectorPage embedded workbench and shared chat icons.
// [Output] Independent connector detail page reachable from the Chat `ResourceConnectorTab`;
//          shows a `← 资源连接器 > Notion Connector` breadcrumb (TopNavigation) above the existing
//          Notion connector workbench (ConnectorHeader / ConnectorOverviewSection / ResourceSourceSection
//          are all implemented inside `ResourceConnectorPage`).
// [Pos] chat connector config page node in frontend/src/components/chat
// [Sync] 2026-07-08: initial ConnectorConfigPage — Chat's `WorkspaceTabBar` → `ResourceConnectorTab`
//                    now drills into this dedicated page instead of redirecting to Settings, aligning
//                    with docs/prd/notion-session/resource-connector.md §3.3 & connector-interaction.md §3.4.
import { IconChevronLeft, IconChevronRight, IconDatabase } from './Icons';
import ResourceConnectorPage from '../dashboard/ResourceConnectorPage';

interface ConnectorConfigPageProps {
  /** Returns to the Chat `ResourceConnectorTab` list. */
  onBack: () => void;
  isMobile?: boolean;
}

export default function ConnectorConfigPage({ onBack, isMobile = false }: ConnectorConfigPageProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <nav
        aria-label="连接器详情页导航"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          flexWrap: 'wrap',
          fontSize: '0.85rem',
          color: 'var(--color-text-secondary)',
          flexShrink: 0,
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
          资源连接器
        </button>
        <IconChevronRight style={{ width: '0.78rem', height: '0.78rem', color: 'var(--color-text-muted)' }} />
        <span style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>Notion Connector</span>
      </nav>

      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '1rem' }}>
          <span
            style={{
              width: '2.2rem',
              height: '2.2rem',
              flexShrink: 0,
              borderRadius: '0.75rem',
              border: '1px solid var(--color-border-paper)',
              background: 'rgba(95, 74, 54, 0.06)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--color-text-primary)',
            }}
          >
            <IconDatabase style={{ width: '1rem', height: '1rem' }} />
          </span>
          <div style={{ minWidth: 0 }}>
            <h1 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              连接器概览
            </h1>
            <p style={{ margin: '0.3rem 0 0', fontSize: '0.82rem', lineHeight: 1.6, color: 'var(--color-text-secondary)' }}>
              管理 Notion 资源链接的认证状态、资源选择和来源列表；下方保留可编辑名称与关闭连接等操作。
            </p>
          </div>
        </div>

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
    </div>
  );
}
