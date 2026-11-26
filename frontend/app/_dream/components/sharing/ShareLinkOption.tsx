// [Input] Current source publication callback, normal HTTP and optional native clipboard action.
// [Output] Explicit link creation/copy, selectable URL and retry feedback inside the original share card.
// [Pos] Shared note/Chat link option; source content and image jobs stay with their original owners.
import {useEffect} from 'react';
import {useTranslation} from 'react-i18next';
import {useShareLink} from '../../hooks/useShareLink';
import type {SharePublication} from '../../api/externalShareApi';
import {IconCopy} from '../chat/Icons';
export default function ShareLinkOption({sourceId, kind = 'chat', create, disabled = false, onBusyChange, copyText}: {sourceId: string; kind?: 'chat' | 'note'; create: (key: string, signal: AbortSignal) => Promise<SharePublication>; disabled?: boolean; onBusyChange?: (busy: boolean) => void; copyText?: (text: string) => Promise<void>}) {
  const {t} = useTranslation();
  const link = useShareLink({sourceId, kind, create, origin: window.location.origin, requirePublicOrigin: Boolean(window.ReactNativeWebView), copyText: copyText ?? (text => navigator.clipboard.writeText(text))});
  useEffect(() => {onBusyChange?.(link.busy);}, [link.busy, onBusyChange]);
  useEffect(() => () => {onBusyChange?.(false);}, [onBusyChange]);
  return <div>
    <button type="button" disabled={disabled || link.busy} onClick={() => void link.copy()} style={{width: '100%', display: 'flex', gap: 12, alignItems: 'center', padding: '13px 14px', border: '1px dashed var(--color-border-paper)', borderRadius: 14, background: 'transparent', color: 'var(--color-text-primary)', font: 'inherit', cursor: disabled || link.busy ? 'not-allowed' : 'pointer'}}>
      <IconCopy style={{width: 18, height: 18}}/><span>{link.busy ? t('noteShare.creating') : link.copied ? t('noteShare.copied') : t('chat.share.copyLink')}</span>
    </button>
    <p style={{fontSize: 12, lineHeight: 1.5, color: 'var(--color-text-muted)'}}>{t('externalShare.linkHint')}</p>
    {link.url ? <input aria-label={t('externalShare.link')} readOnly value={link.url} onFocus={event => event.target.select()} style={{width: '100%', boxSizing: 'border-box', padding: 8, border: '1px solid var(--color-border-paper)', borderRadius: 6, background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)'}}/> : null}
    {link.error ? <p role="alert" style={{fontSize: 12, color: 'var(--color-state-error)'}}>{link.error}</p> : null}
  </div>;
}
