// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Shared original composer state, attachment/sketch callbacks and the caller's Agent context control.
// [Output] Original attachment choices, Full access or Auto/Manual and one trailing Send/Stop/loading action.
// [Pos] Native AIInputDock action row; rich editor, uploads and HTTP remain owned by their existing adapters.
import {useEffect,useState,type ReactNode} from 'react';
import {ActivityIndicator,BackHandler,Platform,Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import useComposerDraft,{buildToolChoiceOptions} from './useComposerDraft';
import {IconArrowUp,IconStop} from './Icons';

export interface AIInputDockControlsProps {
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
}

export default function AIInputDockControls({draft,disabled,loading,fullAccessEnabled,stopPending=false,loadingLabel,contextControl,onStop,onChooseFiles,onOpenSketch}:AIInputDockControlsProps) {
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
          <InkLabel style={[styles.addLabel,{color:colors['color-text-secondary']}]}>{t('chat.inputDock.addAttachment')}</InkLabel>
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
      {fullAccessEnabled ? <View accessibilityLabel={t('chat.inputDock.toolAccessAria')} style={[styles.fullAccess,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-text-primary']}]}>
        <InkLabel style={[styles.modeLabel,{fontWeight:'600',color:colors['color-bg-paper']}]}>{t('chat.inputDock.fullAccess')}</InkLabel>
      </View> : <View accessibilityLabel={t('chat.inputDock.toolModeAria')} style={[styles.modes,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-app']}]}>
        {buildToolChoiceOptions(t).map(option => {
          const selected = option.value === draft.toolChoice;
          return <Pressable key={option.value} accessibilityRole="button" accessibilityLabel={option.label} accessibilityHint={option.title} accessibilityState={{selected,disabled:disabled || loading}}
            disabled={disabled || loading} hitSlop={{top:8,bottom:8}} onPress={() => draft.setToolChoice(option.value)} style={[styles.mode,{backgroundColor:selected ? colors['color-text-primary'] : 'transparent'}]}>
            <InkLabel style={[styles.modeLabel,{fontWeight:selected ? '600' : '400',color:selected ? colors['color-bg-paper'] : colors['color-text-muted']}]}>{option.label}</InkLabel>
          </Pressable>;
        })}
      </View>}
    </View>
    <Pressable accessibilityRole="button" accessibilityLabel={actionLabel} accessibilityHint={!draft.showStopAction && draft.hasUploadingFiles ? t('chat.inputDock.waitingUpload') : undefined}
      accessibilityState={{disabled:actionDisabled,busy:draft.showStopAction ? stopPending : passiveLoading}} disabled={actionDisabled}
      onPress={() => {if (draft.showStopAction) {void onStop?.();} else if (!passiveLoading) draft.handleSend();}}
      style={[styles.action,{backgroundColor:background}]}>
      {(draft.showStopAction && stopPending) || passiveLoading ? <ActivityIndicator size="small" color={foreground} />
        : draft.showStopAction ? <IconStop width={14.4} height={14.4} color={foreground} /> : <IconArrowUp width={17.6} height={17.6} color={foreground} />}
    </Pressable>
  </View>;
}

const styles = StyleSheet.create({
  row:{flexDirection:'row',alignItems:'flex-end',justifyContent:'space-between',gap:12,marginTop:10.4,minWidth:0},
  leading:{flex:1,flexDirection:'row',alignItems:'center',flexWrap:'wrap',gap:7.2,minWidth:0},add:{maxWidth:'100%'},
  addButton:{minHeight:44,borderWidth:1,borderRadius:999,paddingVertical:6.72,paddingHorizontal:13.6,justifyContent:'center',alignSelf:'flex-start'},
  addLabel:{fontSize:12.8},addOptions:{flexDirection:'row',flexWrap:'wrap',gap:5.6,marginTop:6.4,padding:5.6,borderWidth:1,borderRadius:10.4},
  addOption:{minHeight:44,paddingVertical:6.4,paddingHorizontal:10.4,justifyContent:'center',borderRadius:6.4},
  fullAccess:{minHeight:28,paddingHorizontal:12,borderWidth:1,borderRadius:999,justifyContent:'center'},
  modes:{flexDirection:'row',borderWidth:1,borderRadius:999,overflow:'hidden'},mode:{minHeight:28,paddingVertical:5.6,paddingHorizontal:11.2,justifyContent:'center'},
  modeLabel:{fontSize:12.16},action:{width:44,height:44,flexShrink:0,borderRadius:999,alignItems:'center',justifyContent:'center'},
});
