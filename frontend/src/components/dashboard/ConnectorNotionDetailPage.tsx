// [Input] ResourceConnectorPage page mode and shared chat icons.
// [Output] Dedicated "具体配置页面" for the Notion connector: a top breadcrumb navigation
//          bar, a 连接器概览 overview description row (icon/description), followed by the
//          existing ResourceConnectorPage workbench, rendered as a full page that replaces
//          the Settings viewport instead of expanding inline in a card.
// [Pos] connector-notion-detail-page node in frontend/src/components/dashboard
// [Sync] 2026-07-08: initial dedicated navigation page for the Notion "具体配置页面", fixing the
//                    Settings 管理 action so it navigates to a new page instead of an inline toggle.
// [Sync] 2026-07-08: add a 连接器概览 overview description row (icon + one-line description) below
//                    the breadcrumb, aligning with 《链接器概念的交互设计稿》「具体配置页面 / 最上方
//                    导航」骨架屏 which previously had no top text description in this page.
import { IconChevronLeft, IconChevronRight, IconDatabase } from '../chat/Icons';
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
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
        }}
      >
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
            管理 Notion 资源链接的认证状态、资源选择和来源列表；下方保留可编辑名称与断开链接等操作。
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
  );
}
