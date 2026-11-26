// [Input] Exact source identity, idempotent create action and platform clipboard/HTTP owners.
// [Output] Retryable copy state with current server-side revocation checks and manual-copy fallback.
// [Pos] Shared Web/Native link lifecycle; source changes abort pending reads and discard stale receipts.
import {useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {externalShareUrl, getExternalShare, newShareRequestKey, ShareApiError, type SharePublication} from '../api/externalShareApi';
interface Options {sourceId: string; kind?: 'chat' | 'note'; create: (key: string, signal: AbortSignal) => Promise<SharePublication>; origin: string; copyText: (text: string) => Promise<void>; transport?: typeof fetch; requirePublicOrigin?: boolean; onSessionExpired?: () => void}
export function useShareLink(options: Options) {
  const {t} = useTranslation(), latest = useRef(options); latest.current = options;
  const current = useRef<{id: string; key: string; controller: AbortController; busy: boolean; publication: SharePublication | null} | null>(null);
  const [busy, setBusy] = useState(false), [url, setUrl] = useState(''), [copied, setCopied] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    const owner: NonNullable<typeof current.current> = {id: options.sourceId, key: newShareRequestKey(), controller: new AbortController(), busy: false, publication: null};
    current.current = owner; setBusy(false); setUrl(''); setCopied(false); setError('');
    return () => {owner.controller.abort(); if (current.current === owner) current.current = null;};
  }, [options.sourceId]);
  async function copy() {
    const owner = current.current;
    if (!owner || owner.busy || !owner.id) return;
    owner.busy = true; setBusy(true); setCopied(false); setError('');
    const live = () => current.current === owner && !owner.controller.signal.aborted;
    try {
      if (!owner.publication) owner.publication = await latest.current.create(owner.key, owner.controller.signal);
      {
        const saved = await getExternalShare(owner.publication.share.id, latest.current.transport, owner.controller.signal);
        if (saved.status !== 'active') {owner.publication = null; owner.key = newShareRequestKey(); if (live()) setUrl(''); throw Error('SHARE_REVOKED');}
      }
      if (!live()) return;
      const shared = externalShareUrl(owner.publication!, latest.current.origin, latest.current.requirePublicOrigin);
      setUrl(shared);
      try {await latest.current.copyText(shared); if (live()) setCopied(true);}
      catch {if (live()) setError(t('noteShare.copyManually'));}
    } catch (failure) {
      if (!live()) return;
      if (failure instanceof ShareApiError && failure.status === 401) latest.current.onSessionExpired?.();
      const message = failure instanceof Error ? failure.message : '';
      setError(t(message === 'SHARE_REVOKED' ? 'externalShare.revokedCopy' : message === 'NOTE_SHARE_CHANGED' ? latest.current.kind === 'note' ? 'noteShare.changed' : 'externalShare.changed' : message === 'NOTE_SHARE_PUBLIC_URL_REQUIRED' ? 'noteShare.publicUrlRequired' : latest.current.kind === 'note' ? 'noteShare.failed' : 'externalShare.publishFailed'));
    } finally {owner.busy = false; if (live()) setBusy(false);}
  }
  return {busy, url, copied, error, copy};
}
