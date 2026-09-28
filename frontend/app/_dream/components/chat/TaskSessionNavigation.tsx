// [Input] Owner-filtered taskSessionLinks.ts projection and the existing canonical Thread navigation callback.
// [Output] User-bubble-anchored source marker, reply-width created-task list, and compact retry feedback.
// [Pos] Shared Chat relation UI; it does not own task creation, model execution or route state.
// [Sync] 2026-09-27: implement screenshot-led source navigation and created-task list layouts.
// [Sync] 2026-09-27: fit the source marker above its owning user bubble in ChatMessageList.
// [Sync] 2026-09-27: compact the created-task list for placement above assistant message actions.
'use client';

import { useTranslation } from 'react-i18next';
import { IconChevronRight, IconMessageCircle } from './Icons';
import type { TaskSessionLink, TaskSessionLinksSnapshot } from './taskSessionLinks';

interface NavigateProps {
  onNavigateThread?: (threadId: string) => void;
}

function taskStatus(link: TaskSessionLink, t: ReturnType<typeof useTranslation>['t']): string {
  return link.launch_status === 'failed'
    ? t('chat.taskSessionNavigation.failed')
    : t('chat.taskSessionNavigation.created');
}

export function TaskSessionSourceMarker({
  source,
  onNavigateThread,
}: { source: TaskSessionLinksSnapshot['source'] } & NavigateProps) {
  const { t } = useTranslation();
  if (!source || !onNavigateThread) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', alignSelf: 'flex-end', maxWidth: '85%', minWidth: 0 }}>
      <button
        type="button"
        onClick={() => onNavigateThread(source.source_thread_id)}
        aria-label={t('chat.taskSessionNavigation.backToSourceAria')}
        style={{
          minHeight: '2.75rem', maxWidth: '100%', display: 'inline-flex', alignItems: 'center',
          gap: '0.55rem', padding: '0.55rem 0.75rem', border: '1px solid transparent',
          borderRadius: '0.8rem', background: 'transparent', color: 'var(--color-text-secondary)',
          font: 'inherit', cursor: 'pointer', textAlign: 'left',
        }}
      >
        <IconMessageCircle style={{ width: '1rem', height: '1rem', flexShrink: 0 }} />
        <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {source.source_title
            ? t('chat.taskSessionNavigation.fromNamedSource', { title: source.source_title })
            : t('chat.taskSessionNavigation.fromSource')}
        </span>
        <IconChevronRight style={{ width: '0.95rem', height: '0.95rem', flexShrink: 0 }} />
      </button>
    </div>
  );
}

export function CreatedTaskSessionList({
  links,
  onNavigateThread,
}: { links: TaskSessionLink[] } & NavigateProps) {
  const { t, i18n } = useTranslation();
  if (!onNavigateThread || links.length === 0) return null;
  const dateFormatter = new Intl.DateTimeFormat(i18n.language.startsWith('zh') ? 'zh-CN' : 'en', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
  return (
    <section
      aria-label={t('chat.taskSessionNavigation.listTitle')}
      style={{ width: '100%', boxSizing: 'border-box', minWidth: 0, overflow: 'hidden', border: '1px solid var(--color-border-paper)', borderRadius: '0.75rem', background: 'color-mix(in srgb, var(--color-bg-paper) 76%, transparent)' }}
    >
      <div style={{ padding: '0.55rem 0.75rem 0.4rem', color: 'var(--color-text-secondary)', fontSize: '0.78rem', fontWeight: 700 }}>
        {t('chat.taskSessionNavigation.listCount', { count: links.length })}
      </div>
      {links.map((link) => (
        <article
          key={link.task_id}
          style={{ minHeight: '3.5rem', display: 'grid', gridTemplateColumns: '2rem minmax(0, 1fr) auto', alignItems: 'center', gap: '0.6rem', padding: '0.4rem 0.65rem', borderTop: '1px solid var(--color-border-paper)' }}
        >
          <span aria-hidden="true" style={{ width: '2rem', height: '2rem', display: 'grid', placeItems: 'center', borderRadius: '0.6rem', background: 'var(--color-bg-surface-solid)', color: 'var(--color-text-secondary)' }}>
            <IconMessageCircle style={{ width: '1rem', height: '1rem' }} />
          </span>
          <div style={{ minWidth: 0 }}>
            <strong style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-text-primary)', fontSize: '0.88rem' }}>{link.title}</strong>
            <span style={{ display: 'block', marginTop: '0.1rem', color: link.launch_status === 'failed' ? 'var(--color-state-danger)' : 'var(--color-text-secondary)', fontSize: '0.72rem' }}>
              {taskStatus(link, t)} · {dateFormatter.format(new Date(link.created_at))}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onNavigateThread(link.thread_id)}
            style={{ minHeight: '2.75rem', padding: '0 0.7rem', border: '1px solid var(--color-border-paper)', borderRadius: '0.65rem', background: 'transparent', color: 'var(--color-text-primary)', font: 'inherit', fontSize: '0.84rem', fontWeight: 700, cursor: 'pointer' }}
          >
            {t('chat.taskSessionNavigation.openChat')}
          </button>
        </article>
      ))}
    </section>
  );
}

export function TaskSessionLinksFailure({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div role="status" style={{ width: '100%', maxWidth: '52rem', margin: '0.75rem auto 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', padding: '0.55rem 0.75rem', color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>
      <span>{t('chat.taskSessionNavigation.unavailable')}</span>
      <button type="button" onClick={onRetry} style={{ border: 0, background: 'transparent', color: 'inherit', font: 'inherit', fontWeight: 700, textDecoration: 'underline', cursor: 'pointer' }}>
        {t('chat.taskSessionNavigation.retry')}
      </button>
    </div>
  );
}
