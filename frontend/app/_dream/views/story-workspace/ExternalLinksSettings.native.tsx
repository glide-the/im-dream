// [Sync] 2026-11-13: copy/view/settings overlay and shared-access controls match the Web management flow.
// [Sync] 2026-11-12: format display labels and counts as single strings for the original native typography adapter.
// [Input] Shared link-management hook, native account/visibility and original system actions.
// [Output] Native overview/records, copy/view/settings overlay and access/recovery controls.
// [Pos] Native Settings presenter; it shares the production API and business state with Web.
import {useEffect, useState} from 'react';
import {Modal, NativeModules, Pressable, ScrollView, StyleSheet, View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {openExternalLink} from '../../../../src/platform/externalLinks.native';
import {useExternalLinks} from '../../hooks/useExternalLinks';
import {externalShareUrl, ShareApiError, type ExternalShare, type ShareKind} from '../../api/externalShareApi';
interface Props {ownerId: string; origin: string; active: boolean; transport: typeof fetch; onBack: () => void; onSessionExpired: () => void; onOpenSource?: (share: ExternalShare) => Promise<void>}
export default function ExternalLinksSettings({ownerId, origin, active, transport, onBack, onSessionExpired, onOpenSource}: Props) {
  const {t, i18n} = useTranslation(), c = useInkColors(), model = useExternalLinks(ownerId, active, transport, onSessionExpired);
  const [settings, setSettings] = useState<string | null>(null), [accessOpen, setAccessOpen] = useState(false), [info, setInfo] = useState(false);
  const [menu, setMenu] = useState<string | null>(null), [details, setDetails] = useState<string | null>(null), [notice, setNotice] = useState('');
  const selected = model.shares.find(share => share.id === settings), menuShare = model.shares.find(share => share.id === menu);
  useEffect(() => {setSettings(null); setAccessOpen(false); setInfo(false); setMenu(null); setDetails(null); setNotice('');}, [ownerId, active, model.kind, model.status]);
  const text = {color: c['color-text-primary']}, muted = {color: c['color-text-muted']};
  const label = (kind: ShareKind) => t(kind === 'chat' ? 'externalShare.chat' : 'externalShare.note');
  const address = (share: ExternalShare) => externalShareUrl({path: share.path, url: model.publicOrigin ? model.publicOrigin + share.path : null}, origin, true);
  const button = (title: string, action: () => void, disabled = false) => <Pressable accessibilityRole="button" disabled={disabled} accessibilityState={{disabled}} onPress={action} style={[s.button, {borderColor: c['color-border-paper'], opacity: disabled ? .5 : 1}]}><InkLabel style={text}>{title}</InkLabel></Pressable>;
  async function copyOrOpen(share: ExternalShare, open: boolean) {
    setNotice(''); setMenu(null);
    let addressReady = false;
    try {
      const applied = await model.runActive(share, async saved => {const url = address(saved); addressReady = true; if (open) await openExternalLink(url); else await NativeModules.InkRuntime.copyText(url);});
      if (applied && !open) setNotice(t('noteShare.copied'));
    } catch (failure) {if (addressReady) setDetails(share.id); model.setError(t(failure instanceof ShareApiError && failure.status === 410 ? 'externalShare.noLongerActive' : !open && addressReady ? 'noteShare.copyManually' : 'externalShare.openFailed'));}
  }
  const closeOverlay = () => {if (accessOpen) setAccessOpen(false); else {setMenu(null); setSettings(null);}};
  return <><ScrollView style={s.fill} contentContainerStyle={s.body}>
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
      {details === share.id ? <View style={[s.card, {backgroundColor: c['color-bg-paper'], borderColor: c['color-border-paper']}]}><InkLabel selectable style={text}>{share.title}</InkLabel><InkLabel selectable style={text}>{model.publicOrigin ? model.publicOrigin + share.path : share.path}</InkLabel><InkLabel style={muted}>{`${t('externalShare.published')}: ${new Date(share.created_at).toLocaleString(i18n.language)}`}</InkLabel>{share.revoked_at ? <><InkLabel style={muted}>{`${t('externalShare.revokedAt')}: ${new Date(share.revoked_at).toLocaleString(i18n.language)}`}</InkLabel><InkLabel style={muted}>{t('externalShare.revokedReason')}</InkLabel></> : null}</View> : null}
      {model.pending[share.id] ? <View><InkLabel style={muted}>{t(model.pending[share.id] === 'submitting' ? 'externalShare.revoking' : 'externalShare.unknown')}</InkLabel>{model.pending[share.id] === 'unknown' ? button(t('externalShare.refresh'), () => void model.refreshShare(share)) : null}</View> : null}
    </View>) : null}
    {model.kind && !model.loading && !model.error && !model.shares.length ? <InkLabel style={muted}>{t(model.status === 'active' ? 'externalShare.emptyActive' : 'externalShare.emptyRevoked')}</InkLabel> : null}
    {model.cursor ? button(t('externalShare.loadMore'), () => void model.load(true), model.loading) : null}
  </ScrollView>
    <Modal visible={active && Boolean(menuShare || selected)} transparent animationType="fade" onRequestClose={closeOverlay}>
      <View style={[s.scrim, {backgroundColor: c['color-shadow-medium']}]}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={closeOverlay}/>
        <View accessibilityViewIsModal style={[s.dialog, {backgroundColor: c['color-bg-surface-solid'], borderColor: c['color-border-paper']}, !selected && s.menu]}>
          <View style={s.actions}>
            <InkLabel accessibilityRole="header" style={[text, {flex: 1, fontSize: 20, fontWeight: '600'}]}>{selected ? t('externalShare.shareSettings') : menuShare?.title ?? ''}</InkLabel>
            {button(t('externalShare.close'), closeOverlay)}
          </View>
          <ScrollView contentContainerStyle={s.dialogBody}>
            {menuShare ? <>
              {menuShare.status === 'active' ? <>
                {button(t('externalShare.copy'), () => void copyOrOpen(menuShare, false))}
                {button(t('externalShare.view'), () => void copyOrOpen(menuShare, true))}
                <View style={{height: 1, backgroundColor: c['color-border-paper']}}/>
              </> : null}
              {button(t('externalShare.settings'), () => {setSettings(menuShare.id); setInfo(menuShare.status === 'revoked'); setAccessOpen(false); setMenu(null); model.setError('');})}
            </> : null}
            {selected ? <>
              <InkLabel style={muted}>{selected.title}</InkLabel>
              <InkLabel style={[muted, {fontWeight: '600'}]}>{t('externalShare.generalAccess')}</InkLabel>
              <View style={s.actions}>
                {button(t(selected.status === 'active' ? 'externalShare.anyone' : 'externalShare.accessRevoked') + (selected.status === 'active' ? ' ⌄' : ''), () => setAccessOpen(!accessOpen), selected.status !== 'active' || Boolean(model.pending[selected.id]))}
                <InkLabel style={muted}>{t(selected.status === 'active' ? 'externalShare.canView' : 'externalShare.cannotView')}</InkLabel>
              </View>
              {accessOpen ? <View style={[s.card, {borderColor: c['color-border-paper']}]}>
                {button('✓ ' + t('externalShare.anyone'), () => setAccessOpen(false))}
                {button(t('externalShare.revoke'), () => {setAccessOpen(false); setNotice(''); void model.revoke(selected);})}
                <InkLabel style={muted}>{t('externalShare.revokeHint')}</InkLabel>
              </View> : null}
              <InkLabel style={muted}>{t(selected.status === 'active' ? 'externalShare.accessHint' : 'externalShare.revokedHint')}</InkLabel>
              {!selected.source_available ? <InkLabel style={muted}>{t('externalShare.sourceDeleted')}</InkLabel> : null}
              {model.pending[selected.id] ? <InkLabel accessibilityLiveRegion="polite" style={muted}>{t(model.pending[selected.id] === 'submitting' ? 'externalShare.revoking' : 'externalShare.unknown')}</InkLabel> : null}
              {model.error && model.pending[selected.id] !== 'unknown' ? <InkLabel accessibilityRole="alert" style={{color: c['color-state-error']}}>{model.error}</InkLabel> : null}
              {model.pending[selected.id] === 'unknown' ? button(t('externalShare.refresh'), () => void model.refreshShare(selected)) : null}
              <View style={[s.actions, {borderTopWidth: 1, borderColor: c['color-border-paper'], paddingTop: 12}]}>
                {onOpenSource ? button(t('externalShare.source'), () => {setSettings(null); void onOpenSource(selected).catch(() => model.setError(t('externalShare.openFailed')));}, !selected.source_available) : null}
                {button(t('externalShare.details'), () => setInfo(!info))}
              </View>
              {info ? <View style={[s.card, {borderColor: c['color-border-paper']}]}>
                <InkLabel selectable style={text}>{model.publicOrigin ? model.publicOrigin + selected.path : selected.path}</InkLabel>
                <InkLabel style={muted}>{`${t('externalShare.published')}: ${new Date(selected.created_at).toLocaleString(i18n.language)}`}</InkLabel>
                {selected.revoked_at ? <><InkLabel style={muted}>{`${t('externalShare.revokedAt')}: ${new Date(selected.revoked_at).toLocaleString(i18n.language)}`}</InkLabel><InkLabel style={muted}>{t('externalShare.revokedReason')}</InkLabel></> : null}
              </View> : null}
            </> : null}
          </ScrollView>
        </View>
      </View>
    </Modal>
  </>;
}
const s = StyleSheet.create({scrim: {flex: 1, justifyContent: 'center', alignItems: 'center', padding: 16}, dialog: {width: '100%', maxWidth: 640, maxHeight: '85%', borderWidth: 1, borderRadius: 20, padding: 20, gap: 18}, menu: {maxWidth: 320}, dialogBody: {gap: 16, paddingBottom: 8}, fill: {flex: 1}, body: {padding: 20, gap: 16}, title: {fontSize: 24}, card: {padding: 18, borderWidth: 1, borderRadius: 12, gap: 10}, record: {borderTopWidth: 1, paddingVertical: 16, gap: 10}, actions: {flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 10}, button: {minHeight: 44, borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, justifyContent: 'center'}});
