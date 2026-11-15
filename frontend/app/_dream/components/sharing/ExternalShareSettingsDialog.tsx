// [Input] The selected owned share, confirmed status, pending operation and original actions.
// [Output] Shared-access settings, single-link revocation and recoverable status feedback.
// [Pos] Accessible settings dialog; publication, permissions and state remain server-owned.
import {useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {FiGlobe, FiInfo, FiLock} from 'react-icons/fi';
import type {ExternalShare} from '../../api/externalShareApi';
import Modal from '../chat/Modal';
import {IconCheck, IconChevronDown} from '../chat/Icons';

interface Props {
  share: ExternalShare;
  address: string;
  pending?: 'submitting' | 'unknown';
  error: string;
  onClose: () => void;
  onRevoke: () => void;
  onRefresh: () => void;
  onOpenSource?: () => void;
}

export default function ExternalShareSettingsDialog({share, address, pending, error, onClose, onRevoke, onRefresh, onOpenSource}: Props) {
  const {t, i18n} = useTranslation();
  const [accessOpen, setAccessOpen] = useState(false), [details, setDetails] = useState(share.status === 'revoked');
  const accessRef = useRef<HTMLDivElement>(null), accessButton = useRef<HTMLButtonElement>(null);
  const active = share.status === 'active';
  useEffect(() => {
    if (!accessOpen) return;
    accessRef.current?.querySelector<HTMLButtonElement>('[role="menuitemradio"]')?.focus();
    const outside = (event: PointerEvent) => {if (event.target instanceof Node && !accessRef.current?.contains(event.target)) setAccessOpen(false);};
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [accessOpen]);

  return <Modal open title={t('externalShare.shareSettings')} closeLabel={t('externalShare.close')} onClose={onClose} surfaceClassName="external-share-settings">
    <p className="external-share-settings__title">{share.title}</p>
    <h3>{t('externalShare.generalAccess')}</h3>
    <div className="external-share-settings__access">
      <span className="external-share-settings__icon">{active ? <FiGlobe aria-hidden="true"/> : <FiLock aria-hidden="true"/>}</span>
      <div ref={accessRef} className="external-share-settings__scope" onKeyDown={event => {
        if (!accessOpen) return;
        if (event.key === 'Escape') {event.preventDefault(); event.stopPropagation(); setAccessOpen(false); accessButton.current?.focus();}
        if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
          event.preventDefault();
          const items = Array.from(accessRef.current?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]') ?? []);
          const index = items.indexOf(document.activeElement as HTMLButtonElement);
          items[event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + 1) % items.length]?.focus();
        }
        if (event.key === 'Tab') setAccessOpen(false);
      }}>
        <button ref={accessButton} type="button" className="external-share-settings__access-button" aria-haspopup="menu" aria-expanded={accessOpen} disabled={!active || Boolean(pending)} onClick={() => setAccessOpen(!accessOpen)}>
          {t(active ? 'externalShare.anyone' : 'externalShare.accessRevoked')}{active ? <IconChevronDown aria-hidden="true"/> : null}
        </button>
        {accessOpen ? <div role="menu" aria-label={t('externalShare.generalAccess')} className="external-share-settings__access-menu">
          <button type="button" role="menuitemradio" aria-checked tabIndex={-1} onClick={() => {setAccessOpen(false); accessButton.current?.focus();}}>{t('externalShare.anyone')}<IconCheck aria-hidden="true"/></button>
          <button type="button" role="menuitem" tabIndex={-1} className="external-share-settings__danger" onClick={() => {setAccessOpen(false); accessButton.current?.focus(); onRevoke();}}>{t('externalShare.revoke')}<small>{t('externalShare.revokeHint')}</small></button>
        </div> : null}
      </div>
      <span className="external-share-settings__permission">{t(active ? 'externalShare.canView' : 'externalShare.cannotView')}</span>
    </div>
    <p className="external-share-settings__hint"><FiInfo aria-hidden="true"/><span>{t(active ? 'externalShare.accessHint' : 'externalShare.revokedHint')}</span></p>
    {!share.source_available ? <p>{t('externalShare.sourceDeleted')}</p> : null}
    {pending ? <p role="status">{t(pending === 'submitting' ? 'externalShare.revoking' : 'externalShare.unknown')}</p> : null}
    {error && pending !== 'unknown' ? <p role="alert" className="external-share-settings__danger">{error}</p> : null}
    {pending === 'unknown' ? <button type="button" className="external-share-settings__text-button" onClick={onRefresh}>{t('externalShare.refresh')}</button> : null}
    <div className="external-share-settings__footer">
      {onOpenSource ? <button type="button" disabled={!share.source_available} onClick={onOpenSource}>{t('externalShare.source')}</button> : null}
      <button type="button" aria-expanded={details} onClick={() => setDetails(!details)}>{t('externalShare.details')}</button>
    </div>
    {details ? <div className="external-links__detail">
      <label>{t('externalShare.link')}<input aria-label={t('externalShare.link')} readOnly value={address} onFocus={event => event.target.select()}/></label>
      <p>{t('externalShare.published')}: {new Date(share.created_at).toLocaleString(i18n.language)}</p>
      {share.revoked_at ? <><p>{t('externalShare.revokedAt')}: {new Date(share.revoked_at).toLocaleString(i18n.language)}</p><p>{t('externalShare.revokedReason')}</p></> : null}
    </div> : null}
  </Modal>;
}
