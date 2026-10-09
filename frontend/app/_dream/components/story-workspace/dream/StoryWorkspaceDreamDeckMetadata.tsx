// [Input] Actor-scoped Dream run and Deck metadata resolved by Story Workspace.
// [Output] A Dream-only Deck metadata disclosure; no Chat thread or polling owner.
// [Pos] Dream Agent rail provenance control (design_008 §5/§16).
// [Sync] 2026-10-09: share localized 思维模式/Deck provenance labels with Chat.

import { useEffect, useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import './StoryWorkspaceDreamDeckMetadata.css';

export interface StoryWorkspaceDreamDeckMetadataProps {
  readonly deckName: string;
  readonly runId: string;
  readonly stageLine: string;
  readonly runtimeSnapshotId: string | null;
  readonly runtimeLockId: string | null;
}

export function StoryWorkspaceDreamDeckMetadata({
  deckName,
  runId,
  stageLine,
  runtimeSnapshotId,
  runtimeLockId,
}: StoryWorkspaceDreamDeckMetadataProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const popoverId = useId();
  const popoverTitleId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    popoverRef.current?.focus();

    const handlePointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      triggerRef.current?.focus();
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div className="story-workspace-dream-deck-metadata" ref={rootRef}>
      <button
        aria-controls={popoverId}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={t('chat.deck.openMetadataAria', { name: deckName })}
        className="story-workspace-dream-deck-metadata__trigger"
        onClick={() => setOpen((current) => !current)}
        ref={triggerRef}
        title={t('chat.deck.metadataTitle')}
        type="button"
      >
        <span aria-hidden="true" className="story-workspace-dream-deck-metadata__sigil">D</span>
        <span className="story-workspace-dream-deck-metadata__name">{deckName}</span>
        <span aria-hidden="true" className="story-workspace-dream-deck-metadata__chevron">⌄</span>
      </button>

      {open && (
        <div
          aria-labelledby={popoverTitleId}
          aria-modal="false"
          className="story-workspace-dream-deck-metadata__popover"
          id={popoverId}
          ref={popoverRef}
          role="dialog"
          tabIndex={-1}
        >
          <h2 id={popoverTitleId}>{t('chat.deck.metadataTitle')}</h2>
          <dl>
            <div><dt>{t('deck.labels.typeName')}</dt><dd>{deckName}</dd></div>
            <div><dt>Dream run</dt><dd>{runId}</dd></div>
            <div><dt>阶段</dt><dd>{stageLine}</dd></div>
            <div><dt>runtime snapshot</dt><dd>{runtimeSnapshotId ?? '—'}</dd></div>
            <div><dt>runtime lock</dt><dd>{runtimeLockId ?? '—'}</dd></div>
          </dl>
        </div>
      )}
    </div>
  );
}
