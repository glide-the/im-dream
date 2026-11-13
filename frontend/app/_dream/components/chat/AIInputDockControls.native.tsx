// [Sync] 2026-11-13: keep attachment, truncated Chinese Agent/model and action controls on one line.
// [Sync] 2026-11-13: forward Thread tool selection to the grouped native Agent/tools sheet.
// [Sync] 2026-11-13: one Agent/tools entry and a separate migrated model selector.
// [Sync] 2026-11-13: replace segmented mode controls with the native Chat tools menu.
// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Shared original composer state, attachment/sketch callbacks and the caller's Agent context control.
// [Output] Original attachment choices, Full access or Auto/Manual and one trailing Send/Stop/loading action.
// [Pos] Native AIInputDock action row; rich editor, uploads and HTTP remain owned by their existing adapters.
import {useEffect,useState,type ReactNode} from 'react';
import {ActivityIndicator,BackHandler,Platform,Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import useComposerDraft from './useComposerDraft';
import ComposerToolsMenu from './ComposerToolsMenu.native';
import ComposerModelSelector from './ComposerModelSelector.native';
import type {ComposerToolsMenuProps} from './ComposerToolsMenu.types';
import type {DeckChatSelectorProps} from '../deck/deckAgentSelection';
import {IconArrowUp,IconStop} from './Icons';

export interface AIInputDockControlsProps {
  tools?:ComposerToolsMenuProps['tools'];onToolsChange?:ComposerToolsMenuProps['onToolsChange'];
  draft:Pick<ReturnType<typeof useComposerDraft>,'toolChoice'|'setToolChoice'|'handleSend'|'showStopAction'|'canSend'|'hasUploadingFiles'>;
  disabled:boolean;
  loading:boolean;
  fullAccessEnabled:boolean;
  stopPending?:boolean;
  loadingLabel?:string;
  contextControl?:ReactNode;
  onStop?:() => void | Promise<void>;
  onChooseFiles:() => void;
  onOpenSketch:() => void;
  onManageTools?:()=>void;
  active?:boolean;
  agentSelection?:DeckChatSelectorProps;
  onModelConfigSaved?:()=>void;
  onModelSessionExpired?:()=>void;
  onModelBlocked?:(blocked:boolean)=>void;
}

export default function AIInputDockControls({tools,onToolsChange,draft,disabled,loading,fullAccessEnabled,stopPending=false,loadingLabel,contextControl,onStop,onChooseFiles,onOpenSketch,onManageTools,active,agentSelection,onModelConfigSaved,onModelSessionExpired,onModelBlocked}:AIInputDockControlsProps) {
  const {t} = useTranslation();
  const colors = useInkColors();
  const [addOpen,setAddOpen] = useState(false);
  useEffect(() => {
    if (!addOpen || Platform.OS !== 'android') return;
    const listener = BackHandler.addEventListener('hardwareBackPress',() => {setAddOpen(false);return true;});
    return () => listener.remove();
  },[addOpen]);
  const passiveLoading = loading && !onStop;
  const actionLabel = draft.showStopAction
    ? t(stopPending ? 'chat.inputDock.stopping' : 'chat.inputDock.stopGenerating')
    : passiveLoading ? loadingLabel ?? t('chat.inputDock.generating') : t('chat.inputDock.sendAria');
  const actionDisabled = draft.showStopAction ? stopPending : passiveLoading || !draft.canSend;
  const background = actionDisabled ? colors['color-disabled-bg'] : draft.showStopAction ? colors['color-state-danger'] : colors['color-text-primary'];
  const foreground = actionDisabled ? colors['color-text-muted'] : draft.showStopAction ? colors['color-text-on-action'] : colors['color-bg-paper'];
  return <View style={styles.row}>
    <View style={styles.leading}>
      <View style={styles.add}>
        <Pressable accessibilityRole="button" accessibilityLabel={t('chat.inputDock.addAttachmentAria')} accessibilityState={{expanded:addOpen,disabled}} disabled={disabled}
          onPress={() => setAddOpen(value => !value)} style={[styles.addButton,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-app']}]}>
          <InkLabel style={[styles.addLabel,{color:colors['color-text-secondary']}]}>{'+'}</InkLabel>
        </Pressable>
        {addOpen ? <View accessibilityLabel={t('chat.inputDock.addAttachmentAria')} style={[styles.addOptions,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-app']}]}>
          <Pressable accessibilityRole="button" disabled={disabled} accessibilityState={{disabled}} onPress={() => {setAddOpen(false);onChooseFiles();}} style={styles.addOption}>
            <InkLabel style={{color:colors['color-text-primary']}}>{t('chat.inputDock.sketch.uploadFile')}</InkLabel>
          </Pressable>
          <Pressable accessibilityRole="button" disabled={disabled} accessibilityState={{disabled}} onPress={() => {setAddOpen(false);onOpenSketch();}} style={styles.addOption}>
            <InkLabel style={{color:colors['color-text-primary']}}>{t('chat.inputDock.sketch.title')}</InkLabel>
          </Pressable>
        </View> : null}
      </View>
      {contextControl}
      <ComposerToolsMenu tools={tools} onToolsChange={onToolsChange} agentSelection={agentSelection} toolChoice={draft.toolChoice} onToolChoice={draft.setToolChoice} fullAccessEnabled={fullAccessEnabled} disabled={disabled} loading={loading} onManageTools={onManageTools} active={active}/>

    </View>
    <View style={styles.trailing}><ComposerModelSelector disabled={disabled} active={active} onConfigSaved={onModelConfigSaved} onSessionExpired={onModelSessionExpired} onBlockedChange={onModelBlocked}/>
    <Pressable accessibilityRole="button" accessibilityLabel={actionLabel} accessibilityHint={!draft.showStopAction && draft.hasUploadingFiles ? t('chat.inputDock.waitingUpload') : undefined}
      accessibilityState={{disabled:actionDisabled,busy:draft.showStopAction ? stopPending : passiveLoading}} disabled={actionDisabled}
      onPress={() => {if (draft.showStopAction) {void onStop?.();} else if (!passiveLoading) draft.handleSend();}}
      style={[styles.action,{backgroundColor:background}]}>
      {(draft.showStopAction && stopPending) || passiveLoading ? <ActivityIndicator size="small" color={foreground} />
        : draft.showStopAction ? <IconStop width={14.4} height={14.4} color={foreground} /> : <IconArrowUp width={17.6} height={17.6} color={foreground} />}
    </Pressable></View>
  </View>;
}

const styles = StyleSheet.create({
  trailing:{flexDirection:'row',alignItems:'flex-end',gap:4,maxWidth:'65%'},
  row:{flexDirection:'row',alignItems:'flex-end',justifyContent:'space-between',gap:12,marginTop:10.4,minWidth:0},
  leading:{flex:1,flexDirection:'row',alignItems:'center',flexWrap:'nowrap',gap:7.2,minWidth:0},add:{maxWidth:'100%'},
  addButton:{minHeight:44,borderWidth:1,borderRadius:999,paddingVertical:6.72,paddingHorizontal:13.6,justifyContent:'center',alignSelf:'flex-start'},
  addLabel:{fontSize:22},addOptions:{flexDirection:'row',flexWrap:'wrap',gap:5.6,marginTop:6.4,padding:5.6,borderWidth:1,borderRadius:10.4},
  addOption:{minHeight:44,paddingVertical:6.4,paddingHorizontal:10.4,justifyContent:'center',borderRadius:6.4},
  action:{width:44,height:44,flexShrink:0,borderRadius:999,alignItems:'center',justifyContent:'center'},
});
