// [Input] Existing Settings account scope and shared link-management state.
// [Output] Two-category overview, responsive records and single-link revoke/recovery actions.
// [Pos] Browser Settings presenter; server-confirmed results own link status and counts.
import {useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {useAuth} from '../../contexts/AuthContext';
import {useExternalLinks} from '../../hooks/useExternalLinks';
import {externalShareUrl, ShareApiError, type ExternalShare, type ShareKind} from '../../api/externalShareApi';
import './ExternalLinksSettings.css';
export default function ExternalLinksSettings({onOpenSource}: {onOpenSource?: (share: ExternalShare) => Promise<void>}) {
  const {t, i18n} = useTranslation(), {user} = useAuth();
  const model = useExternalLinks(user?.id ?? '', true);
  const [menu, setMenu] = useState<string | null>(null), [detail, setDetail] = useState<string | null>(null), [notice, setNotice] = useState('');
  useEffect(() => {setMenu(null); setDetail(null); setNotice('');}, [user?.id, model.kind, model.status]);
  useEffect(() => {if (detail) document.getElementById('external-share-url-' + detail)?.focus();}, [detail]);
  const label = (kind: ShareKind) => t(kind === 'chat' ? 'externalShare.chat' : 'externalShare.note');
  const url = (share: ExternalShare) => externalShareUrl({path: share.path, url: model.publicOrigin ? model.publicOrigin + share.path : null}, window.location.origin);
  async function copy(share: ExternalShare) {
    setNotice('');
    let address = '';
    try {if (await model.runActive(share, async current => {address = url(current); await navigator.clipboard.writeText(address);})) setNotice(t('noteShare.copied'));}
    catch (failure) {if (address) setDetail(share.id); model.setError(t(address ? 'noteShare.copyManually' : failure instanceof ShareApiError && failure.status === 410 ? 'externalShare.noLongerActive' : 'externalShare.loadFailed'));}
    setMenu(null);
  }
  async function open(share: ExternalShare) {
    setNotice('');
    const tab = window.open('about:blank', '_blank'); if (tab) tab.opener = null;
    try {const applied = await model.runActive(share, async current => {const target = url(current); if (tab) tab.location.href = target; else throw Error();}); if (!applied) tab?.close();}
    catch {tab?.close(); model.setError(t('externalShare.openFailed')); await model.load();}
    setMenu(null);
  }
  return <section className="external-links" aria-label={t('externalShare.title')} onKeyDown={event => {if (event.key === 'Escape' && menu) {event.stopPropagation(); document.getElementById('external-share-actions-' + menu)?.focus(); setMenu(null);}}}>
    <header><h2>{model.kind ? label(model.kind) : t('externalShare.title')}</h2><p>{t('externalShare.description')}</p></header>
    {model.kind ? <div className="external-links__toolbar"><button type="button" onClick={() => {setMenu(null); setDetail(null); model.setKind(null);}}>‹ {t('externalShare.title')}</button>
      <div role="group" aria-label={t('externalShare.status')}><button type="button" aria-pressed={model.status === 'active'} onClick={() => model.setStatus('active')}>{t('externalShare.active')}</button><button type="button" aria-pressed={model.status === 'revoked'} onClick={() => model.setStatus('revoked')}>{t('externalShare.revoked')}</button></div>
      <button type="button" disabled={model.loading} onClick={() => void model.load()}>{t('externalShare.refresh')}</button></div>
      : <div className="external-links__overview">{(['chat', 'note'] as const).map(kind => <button type="button" key={kind} onClick={() => {model.setStatus('active'); model.setKind(kind);}}><strong>{label(kind)} ›</strong><span className="external-links__count">{model.loading ? '…' : model.loaded ? model.counts[kind] : '—'}</span><span>{t('externalShare.activeCount')}</span><span className="external-links__preview">{model.latestTitles[kind] || t('externalShare.emptyActive')}{model.counts[kind] > 1 ? ` +${model.counts[kind] - 1}` : ''}</span></button>)}</div>}
    {model.error ? <p role="alert" className="external-links__error">{model.error} <button type="button" onClick={() => void model.load()}>{t('externalShare.refresh')}</button></p> : null}
    {notice || model.notice ? <p role="status">{notice || model.notice}</p> : null}
    {model.loading ? <p role="status">{t('externalShare.loading')}</p> : null}
    {model.kind ? <>
      <div className="external-links__heading" aria-hidden="true"><span>{t('externalShare.content')}</span><span>{t('externalShare.link')}</span><span>{t('externalShare.published')}</span><span>{t('externalShare.status')}</span><span/></div>
      {model.shares.map(share => <div key={share.id} className="external-links__record"><div className="external-links__row">
        <strong title={share.title}>{share.title}</strong><button type="button" className="external-links__address" onClick={() => setDetail(detail === share.id ? null : share.id)}>{share.path}</button>
        <time dateTime={share.created_at}>{new Date(share.created_at).toLocaleDateString(i18n.language)}</time><span>{t(share.status === 'active' ? 'externalShare.active' : 'externalShare.revoked')}</span>
        <button id={'external-share-actions-' + share.id} type="button" aria-label={t('externalShare.more', {title: share.title})} aria-expanded={menu === share.id} disabled={Boolean(model.pending[share.id])} onClick={() => setMenu(menu === share.id ? null : share.id)}>⋯</button></div>
        {!share.source_available ? <p>{t('externalShare.sourceDeleted')}</p> : null}
        {menu === share.id ? <div className="external-links__menu" role="group" aria-label={share.title}><strong>{share.title}</strong>
          {share.status === 'active' ? <><button type="button" onClick={() => void copy(share)}>{t('chat.share.copyLink')}</button><button type="button" onClick={() => void open(share)}>{t('externalShare.open')}</button></> : null}
          {onOpenSource ? <button type="button" disabled={!share.source_available} onClick={() => {setMenu(null); void onOpenSource(share).catch(() => model.setError(t('externalShare.openFailed')));}}>{t('externalShare.source')}</button> : null}
          {share.status === 'active' ? <button className="external-links__danger" type="button" onClick={() => {setMenu(null); setNotice(''); void model.revoke(share);}}>{t('externalShare.revoke')}</button> : <button type="button" onClick={() => {setDetail(share.id); setMenu(null);}}>{t('externalShare.details')}</button>}
        </div> : null}
        {detail === share.id ? <div className="external-links__detail"><strong>{share.title}</strong><input id={'external-share-url-' + share.id} aria-label={t('externalShare.link')} readOnly value={url(share)} onFocus={event => event.target.select()}/><p>{t('externalShare.published')}: {new Date(share.created_at).toLocaleString(i18n.language)}</p>{share.revoked_at ? <><p>{t('externalShare.revokedAt')}: {new Date(share.revoked_at).toLocaleString(i18n.language)}</p><p>{t('externalShare.revokedReason')}</p></> : null}</div> : null}
        {model.pending[share.id] ? <p role="status">{t(model.pending[share.id] === 'submitting' ? 'externalShare.revoking' : 'externalShare.unknown')} {model.pending[share.id] === 'unknown' ? <button type="button" onClick={() => void model.refreshShare(share)}>{t('externalShare.refresh')}</button> : null}</p> : null}
      </div>)}
      {!model.loading && !model.error && !model.shares.length ? <p>{t(model.status === 'active' ? 'externalShare.emptyActive' : 'externalShare.emptyRevoked')}</p> : null}
      {model.cursor ? <button type="button" disabled={model.loading} onClick={() => void model.load(true)}>{t('externalShare.loadMore')}</button> : null}
    </> : null}
  </section>;
}
