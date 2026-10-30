// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original Deck reference lifecycle, ready installations and native HTTP.
// [Output] Native reference selection and original durable-save/retry feedback.
// [Pos] Native presentation of the existing Deck Claude plugin selector.
import {ActivityIndicator,Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import {useDeckClaudePluginRefs} from '../hooks/useDeckClaudePluginRefs';
import {shortDigest} from '../api/claudePluginAdminApi';
import InkLabel from '../../../src/components/InkLabel.native';
import useInkColors from '../../../src/components/useInkColors.native';

export default function DeckClaudePluginSelector({deckId,disabled,onSaved,transport}:{deckId:string;disabled?:boolean;onSaved?:()=>Promise<void>;transport?:typeof fetch}){
  const {t}=useTranslation(),colors=useInkColors();
  const state=useDeckClaudePluginRefs(deckId,onSaved,transport);
  const label=(text:string)=><InkLabel style={{color:colors['color-text-primary']}}>{text}</InkLabel>;
  return <View accessibilityLabel={t('deck.details.pluginsLabel')} style={styles.body}>
    {label(t('deck.details.pluginsInstalledLabel'))}{label(t('deck.details.pluginsDescription'))}{label(t('deck.details.pluginUsageHint'))}
    {state.loading?<ActivityIndicator/>:state.readyInstallations.length?state.readyInstallations.map(installation=><Pressable key={installation.id} accessibilityRole="checkbox"
      accessibilityLabel={`${installation.package_name} v${installation.resolved_version}`} accessibilityState={{checked:state.selected.get(installation.id)===true,disabled:disabled||state.saving}} aria-checked={state.selected.get(installation.id)===true}
      disabled={disabled||state.saving} onPress={()=>state.toggle(installation.id)} style={[styles.row,{borderColor:colors['color-border-paper']}]}>
      {label(state.selected.get(installation.id)?'☑':'☐')}<View style={styles.fill}>{label(`${installation.package_name} v${installation.resolved_version}`)}
        {label(`${installation.requested_package_spec} · ${shortDigest(installation.artifact_digest)}`)}</View>
    </Pressable>):label(t('deck.details.pluginsEmpty'))}
    {state.error?<View accessibilityRole="alert">{label(state.error)}<Pressable accessibilityRole="button" onPress={()=>void state.load()} disabled={state.loading||state.saving} style={styles.row}>{label(t('deck.actions.retry'))}</Pressable></View>:null}
    {!disabled&&state.readyInstallations.length?<Pressable accessibilityRole="button" accessibilityState={{disabled:state.saving||state.loading}} disabled={state.saving||state.loading}
      onPress={()=>void state.handleSave()} style={styles.row}>{label(state.saving?'保存中…':'保存插件选择')}</Pressable>:null}
    {state.saved?<View accessibilityLiveRegion="polite">{label('已保存 ✓')}</View>:null}
  </View>;
}
const styles=StyleSheet.create({body:{gap:12},row:{minHeight:44,paddingVertical:10,borderBottomWidth:StyleSheet.hairlineWidth,flexDirection:'row',gap:12,alignItems:'center'},fill:{flex:1,minWidth:0}});
