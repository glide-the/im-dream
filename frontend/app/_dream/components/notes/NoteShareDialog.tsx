// [Sync] 2026-11-12: unify note link creation, revocation rechecks and clipboard recovery with Chat.
// [Input] Frozen current-note prose, existing save barrier and optional native clipboard/file actions.
// [Output] Image/link choices, retryable export preview and public link with copy fallback.
// [Pos] Note share job owner; late results and object URLs are discarded after unmount.
import {useEffect, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import {useTranslation} from 'react-i18next';
import ChatShareDialog from '../chat/ChatShareDialog';
import {downloadThreadImage, releaseThreadImage, type RenderedThreadImage} from '../chat/exportThreadImage';
import ShareLinkOption from '../sharing/ShareLinkOption';
import {createNoteShare} from '../../api/noteShareApi';
import {exportNoteImage} from './exportNoteImage';
import type {NoteShareSource} from './noteShare';
export interface NoteShareActions {copyText?: (text: string) => Promise<void>; exportImage?: (image: RenderedThreadImage) => Promise<boolean>}
export default function NoteShareDialog({source, save, onClose, actions}: {source: NoteShareSource; save: () => Promise<void>; onClose: () => void; actions?: NoteShareActions}) {
  const {t} = useTranslation();
  const owner = useRef({alive: true, busy: false, image: null as RenderedThreadImage | null, controller: new AbortController()});
  const [preview, setPreview] = useState<RenderedThreadImage | null>(null);
  const [exporting, setExporting] = useState(false), [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState<{done: number; total: number} | null>(null);
  const [exportFailed, setExportFailed] = useState(false), [linkBusy, setLinkBusy] = useState(false);
  useEffect(() => {const job = owner.current; job.alive = true; job.controller = new AbortController(); return () => {job.alive = false; job.controller.abort(); releaseThreadImage(job.image); job.image = null;};}, []);
  const nonempty = source.snapshot.paragraphs.some(text => text.trim());
  async function image() {
    const job = owner.current;
    if (job.busy || !nonempty) return;
    job.busy = true; setExporting(true); setExportFailed(false);
    try {
      const rendered = await exportNoteImage(source.snapshot, value => {if (job.alive) setProgress(value);});
      if (!job.alive) {releaseThreadImage(rendered); return;}
      releaseThreadImage(job.image); job.image = rendered; setPreview(rendered);
    } catch {if (job.alive) setExportFailed(true);}
    finally {job.busy = false; if (job.alive) setExporting(false);}
  }
  async function download() {
    const job = owner.current;
    if (!job.image || job.busy) return;
    job.busy = true; setDownloading(true); setExportFailed(false);
    try {const complete = actions?.exportImage ? await actions.exportImage(job.image) : (await downloadThreadImage(job.image), true); if (complete && job.alive) onClose();}
    catch {if (job.alive) setExportFailed(true);}
    finally {job.busy = false; if (job.alive) setDownloading(false);}
  }
  const linkOption = <ShareLinkOption kind="note" sourceId={source.sessionId} disabled={!nonempty || exporting || downloading} onBusyChange={setLinkBusy} copyText={actions?.copyText} create={async (key, signal) => {await save(); if (signal.aborted) throw Error('SHARE_CLOSED'); return createNoteShare(source, signal, key);}}/>;
  return createPortal(<ChatShareDialog open manageFocus title={t('noteShare.title')} zIndex={1200} imageHint={t('noteShare.imageHint')} exportCloseLabel={t('chat.history.close')} downloadLabel={actions?.exportImage ? t('noteShare.shareImage') : undefined} threadTitle={source.snapshot.title} exporting={exporting} exportFailed={exportFailed} canExport={nonempty && !linkBusy} preview={preview} downloading={downloading} progress={progress} linkOption={linkOption} onClose={onClose} onExportImage={() => void image()} onDownloadPreview={() => void download()} onDiscardPreview={() => {if (owner.current.busy) return; releaseThreadImage(owner.current.image); owner.current.image = null; setPreview(null); setExportFailed(false);}}/>, document.body);
}
