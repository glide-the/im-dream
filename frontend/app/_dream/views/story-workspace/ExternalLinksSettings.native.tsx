// [Sync] 2026-11-12: format display labels and counts as single strings for the original native typography adapter.
// [Input] Shared link-management hook, native account/visibility and original system actions.
// [Output] Native two-category overview, status records and single-link revoke/recovery controls.
// [Pos] Native Settings presenter; it shares the production API and business state with Web.
import {useEffect, useState} from 'react';
import {NativeModules, Pressable, ScrollView, StyleSheet, View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {openExternalLink} from '../../../../src/platform/externalLinks.native';
import {useExternalLinks} from '../../hooks/useExternalLinks';
import {externalShareUrl, ShareApiError, type ExternalShare, type ShareKind} from '../../api/externalShareApi';
interface Props {ownerId: string; origin: string; active: boolean; transport: typeof fetch; onBack: () => void; onSessionExpired: () => void; onOpenSource?: (share: ExternalShare) => Promise<void>}
export default function ExternalLinksSettings({ownerId, origin, active, transport, onBack, onSessionExpired, onOpenSource}: Props) {
  const {t, i18n} = useTranslation(), c = useInkColors(), model = useExternalLinks(ownerId, active, transport, onSessionExpired);
  const [menu, setMenu] = useState<string | null>(null), [details, setDetails] = useState<string | null>(null), [notice, setNotice] = useState('');
  useEffect(() => {setMenu(null); setDetails(null); setNotice('');}, [ownerId, active, model.kind, model.status]);
  const text = {color: c['color-text-primary']}, muted = {color: c['color-text-muted']};
  const label = (kind: ShareKind) => t(kind === 'chat' ? 'externalShare.chat' : 'externalShare.note');
  const address = (share: ExternalShare) => externalShareUrl({path: share.path, url: model.publicOrigin ? model.publicOrigin + share.path : null}, origin, true);
  const button = (title: string, action: () => void, disabled = false) => <Pressable accessibilityRole="button" disabled={disabled} accessibilityState={{disabled}} onPress={action} style={[s.button, {borderColor: c['color-border-paper'], opacity: disabled ? .5 : 1}]}><InkLabel style={text}>{title}</InkLabel></Pressable>;
  async function copyOrOpen(share: ExternalShare, open: boolean) {
    setNotice('');
    let addressReady = false;
    try {
      const applied = await model.runActive(share, async saved => {const url = address(saved); addressReady = true; if (open) await openExternalLink(url); else await NativeModules.InkRuntime.copyText(url);});
      if (applied && !open) setNotice(t('noteShare.copied'));
    } catch (failure) {if (addressReady) setDetails(share.id); model.setError(t(failure instanceof ShareApiError && failure.status === 410 ? 'externalShare.noLongerActive' : !open && addressReady ? 'noteShare.copyManually' : 'externalShare.openFailed'));}
    setMenu(null);
  }
  return <ScrollView style={s.fill} contentContainerStyle={s.body}>
    {button('‹ ' + (model.kind ? t('externalShare.title') : t('nav.settings')), () => {setMenu(null); setDetails(null); if (model.kind) model.setKind(null); else onBack();})}
    <InkLabel accessibilityRole="header" style={[text, s.title]}>{model.kind ? label(model.kind) : t('externalShare.title')}</InkLabel><InkLabel style={muted}>{t('externalShare.description')}</InkLabel>
    {!model.kind ? (['chat', 'note'] as const).map(kind => <Pressable key={kind} accessibilityRole="button" onPress={() => {model.setStatus('active'); model.setKind(kind);}} style={[s.card, {borderColor: c['color-border-paper'], backgroundColor: c['color-bg-paper']}]}><InkLabel style={text}>{`${label(kind)} ›`}</InkLabel><InkLabel style={[text, s.title]}>{model.loading ? '…' : model.loaded ? String(model.counts[kind]) : '—'}</InkLabel><InkLabel style={muted}>{t('externalShare.activeCount')}</InkLabel><InkLabel numberOfLines={1} style={muted}>{`${model.latestTitles[kind] || t('externalShare.emptyActive')}${model.counts[kind] > 1 ? ` +${model.counts[kind] - 1}` : ''}`}</InkLabel></Pressable>) : <View style={s.actions}>{button(t('externalShare.active'), () => model.setStatus('active'), model.status === 'active')}{button(t('externalShare.revoked'), () => model.setStatus('revoked'), model.status === 'revoked')}{button(t('externalShare.refresh'), () => void model.load(), model.loading)}</View>}
    {model.error ? <InkLabel accessibilityRole="alert" style={{color: c['color-state-error']}}>{model.error}</InkLabel> : null}{notice || model.notice ? <InkLabel accessibilityLiveRegion="polite" style={text}>{notice || model.notice}</InkLabel> : null}
    {model.loading ? <InkLabel style={muted}>{t('externalShare.loading')}</InkLabel> : null}
    {model.error ? button(t('externalShare.refresh'), () => void model.load()) : null}
    {model.kind ? model.shares.map(share => <View key={share.id} style={[s.record, {borderColor: c['color-border-paper']}]}>
      <View style={s.actions}><InkLabel numberOfLines={2} style={[text, {flex: 1}]}>{share.title}</InkLabel>{button('⋯', () => setMenu(menu === share.id ? null : share.id), Boolean(model.pending[share.id]))}</View>
      <Pressable accessibilityRole="button" onPress={() => setDetails(details === share.id ? null : share.id)}><InkLabel numberOfLines={1} style={muted}>{share.path}</InkLabel></Pressable>
      <InkLabel style={muted}>{`${new Date(share.created_at).toLocaleDateString(i18n.language)} · ${t(share.status === 'active' ? 'externalShare.active' : 'externalShare.revoked')}`}</InkLabel>
      {!share.source_available ? <InkLabel style={muted}>{t('externalShare.sourceDeleted')}</InkLabel> : null}
      {menu === share.id ? <View style={s.actions}>{share.status === 'active' ? <>{button(t('chat.share.copyLink'), () => void copyOrOpen(share, false))}{button(t('externalShare.open'), () => void copyOrOpen(share, true))}{button(t('externalShare.revoke'), () => {setMenu(null); setNotice(''); void model.revoke(share);})}</> : button(t('externalShare.details'), () => setDetails(share.id))}{onOpenSource ? button(t('externalShare.source'), () => {setMenu(null); void onOpenSource(share).catch(() => model.setError(t('externalShare.openFailed')));}, !share.source_available) : null}</View> : null}
      {details === share.id ? <View style={[s.card, {backgroundColor: c['color-bg-paper'], borderColor: c['color-border-paper']}]}><InkLabel selectable style={text}>{share.title}</InkLabel><InkLabel selectable style={text}>{model.publicOrigin ? model.publicOrigin + share.path : share.path}</InkLabel><InkLabel style={muted}>{`${t('externalShare.published')}: ${new Date(share.created_at).toLocaleString(i18n.language)}`}</InkLabel>{share.revoked_at ? <><InkLabel style={muted}>{`${t('externalShare.revokedAt')}: ${new Date(share.revoked_at).toLocaleString(i18n.language)}`}</InkLabel><InkLabel style={muted}>{t('externalShare.revokedReason')}</InkLabel></> : null}</View> : null}
      {model.pending[share.id] ? <View><InkLabel style={muted}>{t(model.pending[share.id] === 'submitting' ? 'externalShare.revoking' : 'externalShare.unknown')}</InkLabel>{model.pending[share.id] === 'unknown' ? button(t('externalShare.refresh'), () => void model.refreshShare(share)) : null}</View> : null}
    </View>) : null}
    {model.kind && !model.loading && !model.error && !model.shares.length ? <InkLabel style={muted}>{t(model.status === 'active' ? 'externalShare.emptyActive' : 'externalShare.emptyRevoked')}</InkLabel> : null}
    {model.cursor ? button(t('externalShare.loadMore'), () => void model.load(true), model.loading) : null}
  </ScrollView>;
}
const s = StyleSheet.create({fill: {flex: 1}, body: {padding: 20, gap: 16}, title: {fontSize: 24}, card: {padding: 18, borderWidth: 1, borderRadius: 12, gap: 10}, record: {borderTopWidth: 1, paddingVertical: 16, gap: 10}, actions: {flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 10}, button: {minHeight: 44, borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, justifyContent: 'center'}});
