// [Input] Persisted Thread input entry, local owner state, and server-backed card actions.
// [Output] Screenshot-aligned queue card with guide, edit, side-chat, and per-message cancellation controls.
// [Pos] Chat composer queue-card presentation; ChatPanel owns mutations and refresh.
// [Sync] 2026-09-27: portal the per-card menu outside the capped queue scroller and keep it inside the viewport.
// [Sync] 2026-09-27: expose per-card actions while disabling them outside the queued state.
'use client';

import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { IconEdit, IconMessageCircle, IconMoreHorizontal, IconTrash, IconX } from './Icons';
import type { ThreadInputEntry } from './threadInputQueue';

interface Props {
  entry: ThreadInputEntry;
  localOwner: boolean;
  onGuide: (entry: ThreadInputEntry) => Promise<void>;
  onCancel: (entry: ThreadInputEntry) => Promise<void>;
  onEdit: (entry: ThreadInputEntry, text: string) => Promise<void>;
  onSideChat: (entry: ThreadInputEntry) => Promise<void>;
}

export default function ThreadInputQueueCard({ entry, localOwner, onGuide, onCancel, onEdit, onSideChat }: Props) {
  const { t } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry.text);
  const [pending, setPending] = useState(false);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null);
  const moreButtonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const queued = entry.status === 'queued';
  const canGuide = queued && localOwner && !pending;
  const canEdit = queued && localOwner && !pending;
  const canCancel = queued && !pending;
  useLayoutEffect(() => {
    if (!menuOpen) return;
    const placeMenu = () => {
      const button = moreButtonRef.current;
      const menu = menuRef.current;
      if (!button || !menu) return;
      const anchor = button.getBoundingClientRect();
      const width = menu.offsetWidth;
      const height = menu.offsetHeight;
      const left = Math.max(8, Math.min(anchor.right - width, window.innerWidth - width - 8));
      const above = anchor.top >= height + 12;
      const top = above ? anchor.top - height - 4
        : Math.min(anchor.bottom + 4, window.innerHeight - height - 8);
      setMenuPosition({ left, top: Math.max(8, top) });
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!menuRef.current?.contains(target) && !moreButtonRef.current?.contains(target)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setMenuOpen(false);
        moreButtonRef.current?.focus();
      }
    };
    placeMenu();
    window.addEventListener('resize', placeMenu);
    window.addEventListener('scroll', placeMenu, true);
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('resize', placeMenu);
      window.removeEventListener('scroll', placeMenu, true);
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen]);
  const run = async (action: () => Promise<void>) => {
    setMenuOpen(false);
    moreButtonRef.current?.focus();
    setPending(true);
    try { await action(); } catch { /* ChatPanel renders the server error and refreshes status. */ } finally { setPending(false); }
  };
  const controlStyle = { border: 0, background: 'transparent', color: 'var(--color-text-secondary)', cursor: 'pointer', padding: '0.35rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', borderRadius: '0.5rem' } as const;
  return (
    <div data-testid="thread-input-queue-card" data-status={entry.status} style={{ position: 'relative', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.55rem', minHeight: '3rem', padding: '0.35rem 0.8rem', border: '1px solid var(--color-border-paper)', borderRadius: '0.9rem', background: 'var(--color-bg-surface-solid)', color: 'var(--color-text-primary)' }}>
      <span aria-hidden="true" style={{ color: 'var(--color-text-secondary)', flexShrink: 0 }}>↳</span>
      {editing ? (
        <form onSubmit={(event) => { event.preventDefault(); const text = draft.trim(); if (text && text !== entry.text) void run(async () => { await onEdit(entry, text); setEditing(false); }); }} style={{ display: 'flex', alignItems: 'center', flex: 1, minWidth: 0, gap: '0.4rem' }}>
          <input autoFocus aria-label={t('chat.inputQueue.edit')} value={draft} onChange={(event) => setDraft(event.target.value)} style={{ flex: 1, minWidth: 0, border: '1px solid var(--color-border-paper)', borderRadius: '0.45rem', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', padding: '0.4rem' }} />
          <button type="submit" disabled={!draft.trim() || pending} style={controlStyle}>{t('chat.inputQueue.save')}</button>
          <button type="button" aria-label={t('chat.inputQueue.cancelEdit')} onClick={() => { setDraft(entry.text); setEditing(false); }} style={controlStyle}><IconX style={{ width: '1rem', height: '1rem' }} /></button>
        </form>
      ) : (
        <>
          <span title={entry.text} style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600 }}>{entry.text}</span>
          <span aria-live="polite" style={{ flexShrink: 0, fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>{t(`chat.inputQueue.${entry.status}`)}{!localOwner && ['queued', 'selected', 'dispatching'].includes(entry.status) ? ` · ${t('chat.inputQueue.ownerUnverified')}` : ''}</span>
          <button type="button" disabled={!canGuide} onClick={() => { void run(() => onGuide(entry)); }} style={controlStyle}>{t('chat.inputQueue.guide')}</button>
          <button type="button" disabled={!canCancel} aria-label={t('chat.inputQueue.delete')} title={t('chat.inputQueue.delete')} onClick={() => { void run(() => onCancel(entry)); }} style={controlStyle}><IconTrash style={{ width: '1rem', height: '1rem' }} /></button>
          <button ref={moreButtonRef} type="button" aria-label={t('chat.inputQueue.more')} aria-expanded={menuOpen} aria-haspopup="menu" onClick={() => setMenuOpen(!menuOpen)} style={controlStyle}><IconMoreHorizontal style={{ width: '1rem', height: '1rem' }} /></button>
          {menuOpen && typeof document !== 'undefined' ? createPortal(
            <div ref={menuRef} role="menu" style={{ position: 'fixed', zIndex: 1000,
              top: menuPosition?.top ?? 0, left: menuPosition?.left ?? 0,
              visibility: menuPosition ? 'visible' : 'hidden',
              minWidth: 'min(13rem, calc(100vw - 1rem))', padding: '0.35rem',
              border: '1px solid var(--color-border-paper)', borderRadius: '0.85rem',
              background: 'var(--color-bg-surface-solid)', boxShadow: '0 8px 20px var(--color-shadow-soft)', display: 'grid' }}>
              <button type="button" role="menuitem" disabled={!canEdit} onClick={() => { setMenuOpen(false); setEditing(true); }} style={controlStyle}><IconEdit style={{ width: '1rem', height: '1rem' }} />{t('chat.inputQueue.edit')}</button>
              <button type="button" role="menuitem" disabled={!canCancel} onClick={() => { void run(() => onSideChat(entry)); }} style={controlStyle}><IconMessageCircle style={{ width: '1rem', height: '1rem' }} />{t('chat.inputQueue.sideChat')}</button>
              <button type="button" role="menuitem" disabled={!canCancel} onClick={() => { void run(() => onCancel(entry)); }} style={controlStyle}><IconTrash style={{ width: '1rem', height: '1rem' }} />{t('chat.inputQueue.closeQueue')}</button>
            </div>, document.body,
          ) : null}
        </>
      )}
    </div>
  );
}
