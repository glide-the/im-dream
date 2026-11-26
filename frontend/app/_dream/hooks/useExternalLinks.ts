// [Sync] 2026-11-12: bind request cleanup to the effect-owned controller collection.
// [Input] Current account/visibility and the original browser/native authenticated transport.
// [Output] Two-category overview, paged records and confirmed or unknown revocation states.
// [Pos] Shared Settings business owner; both presenters consume the same API and state transitions.
import {useCallback, useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {getExternalShare, listExternalShares, revokeExternalShare, newShareRequestKey, ShareApiError, type ExternalShare, type ShareKind, type ShareCursor} from '../api/externalShareApi';
type Pending = Record<string, 'submitting' | 'unknown'>;
export function useExternalLinks(ownerId: string, active: boolean, transport: typeof fetch = fetch, onSessionExpired?: () => void) {
  const {t} = useTranslation();
  const [kind, setKind] = useState<ShareKind | null>(null), [status, setStatus] = useState<ExternalShare['status']>('active');
  const [shares, setShares] = useState<ExternalShare[]>([]), [counts, setCounts] = useState({chat: 0, note: 0});
  const [latestTitles, setLatestTitles] = useState({chat: '', note: ''}), [cursor, setCursor] = useState<ShareCursor | null>(null);
  const [publicOrigin, setPublicOrigin] = useState<string | null>(null), [loading, setLoading] = useState(false), [loaded, setLoaded] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [pending, setPending] = useState<Pending>({});
  const identity = useRef({ownerId, active, generation: 0}), requests = useRef(new Set<AbortController>()), keys = useRef(new Map<string, string>());
  const current = useRef({kind, status, cursor, transport, onSessionExpired}); current.current = {kind, status, cursor, transport, onSessionExpired};
  const expired = (failure: unknown) => {if (failure instanceof ShareApiError && failure.status === 401) current.current.onSessionExpired?.();};
  const load = useCallback(async (more = false) => {
    const owner = identity.current;
    if (!owner.active || !owner.ownerId) return;
    const generation = ++owner.generation, selection = current.current;
    const controller = new AbortController(); requests.current.add(controller); setLoading(true); setError('');
    const valid = () => identity.current === owner && owner.active && generation === owner.generation && !controller.signal.aborted;
    try {
      if (selection.kind) {
        const page = await listExternalShares(selection.kind, selection.status, more ? selection.cursor : null, selection.transport, controller.signal);
        if (!valid()) return;
        setShares(previous => more ? [...previous, ...page.shares.filter(item => !previous.some(existing => existing.id === item.id))] : page.shares);
        setCounts(page.counts); setCursor(page.next_cursor); setPublicOrigin(page.public_origin);
        setLoaded(true);
        if (!more) setPending({});
      } else {
        const [chat, note] = await Promise.all([listExternalShares('chat', 'active', null, selection.transport, controller.signal, 1), listExternalShares('note', 'active', null, selection.transport, controller.signal, 1)]);
        if (!valid()) return;
        setCounts(note.counts); setPublicOrigin(note.public_origin); setLatestTitles({chat: chat.shares[0]?.title ?? '', note: note.shares[0]?.title ?? ''}); setShares([]); setCursor(null);
        setLoaded(true);
      }
    } catch (failure) {if (valid()) {expired(failure); setError(t('externalShare.loadFailed'));}}
    finally {requests.current.delete(controller); if (valid()) setLoading(false);}
  }, [t]);
  useEffect(() => {
    const owner = {ownerId, active, generation: 0}; identity.current = owner; const ownedRequests = requests.current;
    setShares([]); setCursor(null); setCounts({chat: 0, note: 0}); setLatestTitles({chat: '', note: ''}); setPublicOrigin(null); setLoading(false); setLoaded(false); setPending({}); keys.current.clear(); setError(''); setNotice('');
    return () => {owner.active = false; for (const request of ownedRequests) request.abort(); ownedRequests.clear();};
  }, [ownerId, active, load]);
  useEffect(() => {setShares([]); setCursor(null); setPending({}); if (active && ownerId) void load();}, [ownerId, active, kind, status, load]);
  async function revoke(share: ExternalShare) {
    const owner = identity.current;
    if (!owner.active || pending[share.id]) return;
    const key = keys.current.get(share.id) ?? newShareRequestKey(); keys.current.set(share.id, key);
    const controller = new AbortController(); requests.current.add(controller); setPending(previous => ({...previous, [share.id]: 'submitting'})); setError(''); setNotice('');
    try {
      const result = await revokeExternalShare(share.id, key, current.current.transport, controller.signal);
      if (identity.current !== owner || !owner.active) return;
      if (result.status !== 'revoked') throw Error('SHARE_RESULT_INVALID');
      keys.current.delete(share.id); setPending(previous => {const next = {...previous}; delete next[share.id]; return next;}); setShares(previous => previous.filter(item => item.id !== share.id)); setNotice(t('externalShare.revokeSucceeded')); await load();
    } catch (failure) {
      if (identity.current !== owner || !owner.active) return;
      expired(failure);
      const unknown = !(failure instanceof ShareApiError) || failure.status >= 500;
      setPending(previous => {const next = {...previous}; if (unknown) next[share.id] = 'unknown'; else delete next[share.id]; return next;});
      setError(t(unknown ? 'externalShare.unknown' : 'externalShare.revokeFailed'));
    } finally {requests.current.delete(controller);}
  }
  async function refreshShare(share: ExternalShare) {
    const owner = identity.current, controller = new AbortController(); requests.current.add(controller);
    try {
      const result = await getExternalShare(share.id, current.current.transport, controller.signal);
      if (identity.current !== owner || !owner.active) return;
      if (result.status === 'revoked') {keys.current.delete(share.id); await load();}
      else {setPending(previous => {const next = {...previous}; delete next[share.id]; return next;}); setError('');}
    } catch (failure) {if (identity.current === owner && owner.active) {expired(failure); setError(t('externalShare.unknown'));}}
    finally {requests.current.delete(controller);}
  }
  async function runActive(share: ExternalShare, action: (current: ExternalShare) => Promise<void>) {
    const owner = identity.current;
    if (!owner.active || pending[share.id]) return false;
    setError(''); setNotice('');
    const controller = new AbortController(); requests.current.add(controller);
    const live = () => identity.current === owner && owner.active && !controller.signal.aborted;
    try {
      const saved = await getExternalShare(share.id, current.current.transport, controller.signal);
      if (!live()) return false;
      if (saved.status !== 'active') {await load(); throw new ShareApiError(410);}
      await action(saved);
      return live();
    } catch (failure) {if (!live()) return false; expired(failure); throw failure;}
    finally {requests.current.delete(controller);}
  }
  return {kind, setKind, status, setStatus, shares, counts, latestTitles, cursor, publicOrigin, loading, loaded, error, notice, pending, load, revoke, refreshShare, runActive, setError};
}
