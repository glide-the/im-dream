// [Input] Chat-owned activity rows, independent read states, history groups and original navigation/delete callbacks.
// [Output] Theme-adaptive 20rem sidebar or accessible full-width mobile drawer with one list scroller and display menu.
// [Pos] Chat activity presentation; no task control, notification persistence or Agent transport ownership.
// [Sync] 2026-10-07: preserve source recovery, layered Escape/focus behavior and original Chat history capabilities.

import { useEffect, useLayoutEffect, useRef, useState, type MouseEvent, type UIEvent } from 'react';
import { useTranslation } from 'react-i18next';
import type { ChatHistoryThread } from '../../api/chatHistoryApi';
import { getDateLocale } from '../../i18n';
import { IconCheck, IconMoreHorizontal, IconSearch, IconX } from './Icons';
import type { ActivityFilters, ActivityRow, ActivitySource } from './activitySidebarModel';
import type { ActivityReadState } from './useActivitySidebarData';
import './ActivitySidebar.css';

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),[tabindex]:not([tabindex="-1"])';
function focusableWithin(element: HTMLElement): HTMLElement[] {
  return [...element.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((node) => !node.closest('[inert], [hidden]') && node.getClientRects().length > 0);
}

interface Props {
  isMobile: boolean;
  searchOpen: boolean;
  rows: ActivityRow[];
  filters: ActivityFilters;
  onFiltersChange: (filters: ActivityFilters) => void;
  sources: Record<ActivitySource, Pick<ActivityReadState<unknown>, 'isLoading' | 'error' | 'hasSuccess'>>;
  groups: Array<{ label: string; threads: ChatHistoryThread[] }>;
  activeThreadId: string | null;
  deletingThreadId: string | null;
  historyLoading: boolean;
  historyLoadingMore: boolean;
  historyError: boolean;
  historyMoreError: boolean;
  hasMoreHistory: boolean;
  onHistoryRetry: () => void;
  onHistoryMore: () => void;
  onScroll: (event: UIEvent<HTMLDivElement>) => void;
  onRetry: (source: ActivitySource) => void;
  onRefresh: () => void;
  onSearch: () => void;
  onClose: () => void;
  onSelectThread: (id: string) => void;
  onDeleteThread: (event: MouseEvent, id: string) => void;
  onDream: (href: string) => void;
  onTask: (row: ActivityRow) => void;
}

export default function ActivitySidebar(props: Props) {
  const { t, i18n } = useTranslation();
  const panelRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const searchButtonRef = useRef<HTMLButtonElement>(null);
  const previousSearchOpen = useRef(props.searchOpen);
  const initialSearchOpen = useRef(props.searchOpen);
  const focusedRow = useRef<{ key: string; index: number } | null>(null);
  const [menu, setMenu] = useState<{ top: number; right: number } | null>(null);
  const onCloseRef = useRef(props.onClose);
  onCloseRef.current = props.onClose;
  const closeMenu = () => { setMenu(null); menuButtonRef.current?.focus(); };

  useEffect(() => { if (!initialSearchOpen.current) titleRef.current?.focus(); }, []);
  useLayoutEffect(() => {
    if (previousSearchOpen.current && !props.searchOpen) searchButtonRef.current?.focus();
    previousSearchOpen.current = props.searchOpen;
  }, [props.searchOpen]);
  useEffect(() => {
    if (!props.isMobile || !panelRef.current) return;
    const changed: Array<{ node: HTMLElement; inert: boolean }> = [];
    let node: HTMLElement | null = panelRef.current;
    while (node?.parentElement) {
      for (const sibling of [...node.parentElement.children]) {
        if (!(sibling instanceof HTMLElement) || sibling === node || sibling.hasAttribute('data-chat-history-search') || ['SCRIPT', 'STYLE', 'LINK'].includes(sibling.tagName)) continue;
        changed.push({ node: sibling, inert: sibling.inert });
        sibling.inert = true;
      }
      node = node.parentElement;
      if (node === document.body) break;
    }
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      for (const entry of changed) entry.node.inert = entry.inert;
      document.body.style.overflow = overflow;
    };
  }, [props.isMobile]);

  useEffect(() => {
    if (props.searchOpen) { setMenu(null); return; }
    const handleKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        if (menu) { setMenu(null); menuButtonRef.current?.focus(); }
        else onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab' || !props.isMobile || !panelRef.current) return;
      const items = focusableWithin(panelRef.current);
      const first = items[0]; const last = items.at(-1);
      if (!first) { event.preventDefault(); titleRef.current?.focus(); return; }
      const focused = document.activeElement;
      if (event.shiftKey && (focused === first || focused === titleRef.current || !panelRef.current.contains(focused))) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && (focused === last || !panelRef.current.contains(focused))) {
        event.preventDefault(); first.focus();
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [menu, props.isMobile, props.searchOpen]);

  useEffect(() => {
    if (!menu) return;
    menuRef.current?.querySelector<HTMLElement>('[role="menuitemcheckbox"]')?.focus();
    const handleOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !menuRef.current?.contains(event.target) && !menuButtonRef.current?.contains(event.target)) {
        setMenu(null); menuButtonRef.current?.focus();
      }
    };
    const hide = () => setMenu(null);
    const visibility = () => { if (document.visibilityState === 'hidden') setMenu(null); };
    document.addEventListener('pointerdown', handleOutside);
    window.addEventListener('resize', hide);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      document.removeEventListener('pointerdown', handleOutside);
      window.removeEventListener('resize', hide);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [menu]);

  useLayoutEffect(() => {
    if (!focusedRow.current || !bodyRef.current || props.searchOpen || menu) return;
    const focused = focusedRow.current;
    if (bodyRef.current.querySelector(`[data-activity-key="${CSS.escape(focused.key)}"]`)) return;
    if (document.activeElement !== document.body) return;
    const rows = [...bodyRef.current.querySelectorAll<HTMLElement>('[data-activity-key]')];
    (rows[Math.min(focused.index, rows.length - 1)]?.querySelector<HTMLElement>('button,a') ?? titleRef.current)?.focus();
  }, [props.rows, props.groups, menu, props.searchOpen]);

  const selectedSources = (['scheduled', 'chat', 'dream'] as const).filter((source) => props.filters[source]);
  const title = (value: string | null) => value || t('chat.history.fallbackTitle');
  const time = (at: number) => Number.isFinite(at) ? new Intl.DateTimeFormat(getDateLocale(i18n.language), { hour: '2-digit', minute: '2-digit' }).format(at) : '';
  const deleteButton = (id: string) => <button type="button" className="activity-sidebar__delete" aria-label={t('chat.history.deleteThread')} title={t('chat.history.deleteThread')}
    disabled={props.deletingThreadId === id} onClick={(event) => props.onDeleteThread(event, id)}><IconX /></button>;

  return <aside id="chat-activity-sidebar" ref={panelRef} className={`activity-sidebar${props.isMobile ? ' activity-sidebar--mobile' : ''}`}
    role={props.isMobile ? 'dialog' : undefined} aria-modal={props.isMobile ? true : undefined} aria-labelledby="chat-activity-title" inert={props.searchOpen ? true : undefined}>
    <header className="activity-sidebar__header">
      <h2 id="chat-activity-title" ref={titleRef} tabIndex={-1}>{t('chat.activity.title')}</h2>
      <div className="activity-sidebar__actions">
        <button ref={searchButtonRef} type="button" className="activity-sidebar__icon" aria-label={t('chat.search.ariaLabel')} title={t('chat.search.ariaLabel')} onClick={props.onSearch}><IconSearch /></button>
        <button type="button" className="activity-sidebar__icon" aria-label={t('chat.activity.refresh')} title={t('chat.activity.refresh')} onClick={props.onRefresh}>↻</button>
        <button type="button" className="activity-sidebar__icon" aria-label={t('chat.activity.close')} title={t('chat.activity.close')} onClick={props.onClose}><IconX /></button>
      </div>
    </header>
    <div ref={bodyRef} className="activity-sidebar__body" onScroll={(event) => { if (menu) setMenu(null); props.onScroll(event); }}
      onFocusCapture={(event) => {
        const row = (event.target as HTMLElement).closest<HTMLElement>('[data-activity-key]');
        if (!row) { focusedRow.current = null; return; }
        const all = [...event.currentTarget.querySelectorAll<HTMLElement>('[data-activity-key]')];
        focusedRow.current = { key: row.dataset.activityKey!, index: all.indexOf(row) };
      }}>
      <section aria-labelledby="chat-activity-priority">
        <div className="activity-sidebar__section-heading"><h3 id="chat-activity-priority">{t('chat.activity.priority')}</h3>
          <button ref={menuButtonRef} type="button" className="activity-sidebar__icon" aria-label={t('chat.activity.display')} title={t('chat.activity.display')}
            aria-haspopup="menu" aria-expanded={Boolean(menu)} onClick={() => {
              if (menu) { closeMenu(); return; }
              const rect = menuButtonRef.current!.getBoundingClientRect();
              setMenu({ top: Math.max(8, Math.min(rect.bottom + 4, window.innerHeight - 208)), right: Math.max(8, window.innerWidth - rect.right) });
            }}><IconMoreHorizontal /></button>
        </div>
        {props.filters.priority ? <>
          {props.rows.map((row) => <div key={row.key} data-activity-key={row.key} className="activity-sidebar__row" data-priority={row.priority}>
            {row.source === 'dream' ? <a className="activity-sidebar__row-main" href={row.href} title={title(row.title)} onClick={(event) => {
              if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
              event.preventDefault(); props.onDream(row.href!);
            }}><span className="activity-sidebar__title">{title(row.title)}</span><span className="activity-sidebar__metadata">Dream · {row.stale ? `${t('chat.activity.lastState')}：` : ''}{t(`chat.activity.state.${row.state}`)} · {time(row.activityAt)}</span></a>
              : <button type="button" className="activity-sidebar__row-main" title={title(row.title)} aria-current={row.source === 'chat' && row.id === props.activeThreadId ? 'page' : undefined}
                onClick={() => row.source === 'chat' ? props.onSelectThread(row.id) : props.onTask(row)}>
                <span className="activity-sidebar__title">{title(row.title)}</span><span className="activity-sidebar__metadata">{t(`chat.activity.source.${row.source}`)}{row.source === 'scheduled' ? ` · ${t('chat.activity.today')}` : ''}
                  {row.state ? ` · ${row.stale ? `${t('chat.activity.lastState')}：` : ''}${t(row.state === 'running' ? 'chat.activity.taskRunning' : `chat.activity.state.${row.state}`)}` : ''}{time(row.activityAt) ? ` · ${time(row.activityAt)}` : ''}</span>
              </button>}
            {row.source === 'chat' ? deleteButton(row.id) : null}
          </div>)}
          {selectedSources.map((source) => {
            const state = props.sources[source];
            return state.error ? <div key={source} className="activity-sidebar__feedback activity-sidebar__feedback--error" role="status">
              <span>{t(state.hasSuccess ? 'chat.activity.updateFailed' : 'chat.activity.loadFailed', { source: t(`chat.activity.source.${source}`) })}</span>
              <button type="button" onClick={() => props.onRetry(source)}>{t('chat.activity.retry')}</button>
            </div> : state.isLoading ? <div key={source} className="activity-sidebar__feedback" role="status">{t('chat.activity.loading', { source: t(`chat.activity.source.${source}`) })}</div> : null;
          })}
          {selectedSources.length === 0 ? <p className="activity-sidebar__feedback">{t('chat.activity.chooseTypes')}</p> : null}
          {props.rows.length === 0 && selectedSources.length > 0 && selectedSources.every((source) => props.sources[source].hasSuccess && !props.sources[source].isLoading && !props.sources[source].error)
            ? <p className="activity-sidebar__feedback">{t('chat.activity.empty')}</p> : null}
        </> : null}
      </section>
      {props.historyLoading ? <p className="activity-sidebar__feedback" role="status">{t('chat.activity.historyLoading')}</p> : null}
      {props.historyError ? <div className="activity-sidebar__feedback activity-sidebar__feedback--error" role="status"><span>{t('chat.activity.historyFailed')}</span><button type="button" onClick={props.onHistoryRetry}>{t('chat.activity.retry')}</button></div> : null}
      {!props.historyLoading && !props.historyError && props.groups.length === 0 ? <p className="activity-sidebar__feedback">{t('chat.history.empty')}</p> : null}
      {props.groups.map((group) => <section key={group.label} aria-label={group.label}><h3 className="activity-sidebar__date-heading">{group.label}</h3>
        {group.threads.map((thread) => <div className="activity-sidebar__row" data-activity-key={`history:${thread.id}`} key={thread.id}>
          <button type="button" className="activity-sidebar__row-main" aria-current={thread.id === props.activeThreadId ? 'page' : undefined} onClick={() => props.onSelectThread(thread.id)} title={title(thread.title)}><span className="activity-sidebar__title">{title(thread.title)}</span></button>
          {deleteButton(thread.id)}
        </div>)}
      </section>)}
      {props.historyLoadingMore ? <p className="activity-sidebar__feedback" role="status">{t('chat.activity.historyLoading')}</p> : null}
      {props.historyMoreError ? <div className="activity-sidebar__feedback activity-sidebar__feedback--error" role="status"><span>{t('chat.activity.historyFailed')}</span><button type="button" onClick={props.onHistoryMore}>{t('chat.activity.retry')}</button></div> : null}
      {!props.historyLoading && !props.historyError && !props.historyLoadingMore && !props.historyMoreError && props.groups.length > 0 && !props.hasMoreHistory ? <p className="activity-sidebar__feedback activity-sidebar__end">{t('chat.history.allShown')}</p> : null}
      {props.hasMoreHistory && !props.historyLoadingMore && !props.historyMoreError ? <button type="button" className="activity-sidebar__load-more" onClick={props.onHistoryMore}>{t('chat.activity.moreHistory')}</button> : null}
    </div>
    {menu ? <div ref={menuRef} role="menu" aria-label={t('chat.activity.display')} className="activity-sidebar__menu" style={{ top: menu.top, right: menu.right }} onKeyDown={(event) => {
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
        event.preventDefault(); const items = focusableWithin(event.currentTarget); const index = items.indexOf(document.activeElement as HTMLElement);
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        items[next]?.focus();
      } else if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeMenu(); }
    }}>
      {(['priority', 'scheduled', 'chat', 'dream'] as const).map((key) => <button key={key} type="button" role="menuitemcheckbox" aria-checked={props.filters[key]}
        onClick={() => props.onFiltersChange({ ...props.filters, [key]: !props.filters[key] })}>{t(key === 'priority' ? 'chat.activity.prioritySection' : `chat.activity.source.${key}`)}{props.filters[key] ? <IconCheck /> : <span />}</button>)}
    </div> : null}
  </aside>;
}
