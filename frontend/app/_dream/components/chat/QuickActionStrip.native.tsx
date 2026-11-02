// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-28: reflect initial configuration readiness with the native disabled state; preserve original labels and geometry.
// [Input] The original QuickActionStrip items and onSelect callback.
// [Output] Same wrapped pill strip using RN primitives and original SVG geometry.
// [Pos] Native presentation counterpart; action prompts and submission stay with ChatView.
import {Pressable, StyleSheet, View} from 'react-native';
import InkLabel from '../../../../src/components/InkLabel.native';
import {IconEdit, IconImage, IconSearch} from './Icons';
import type {QuickActionStripProps} from './QuickActionStrip.types';
import useInkColors from '../../../../src/components/useInkColors.native';
export type {QuickActionStripIcon, QuickActionStripItem} from './QuickActionStrip.types';
export default function QuickActionStrip({items, onSelect,disabled=false}: QuickActionStripProps & {disabled?:boolean}) {
  const colors = useInkColors();
  if (!items.length) return null;
  return <View style={styles.strip}>{items.map(item => {
    const Icon = item.icon === 'image' ? IconImage : item.icon === 'edit' ? IconEdit : IconSearch;
    return <Pressable key={item.id} accessibilityRole="button" disabled={disabled} accessibilityState={{disabled}} accessibilityLabel={item.label} accessibilityHint={item.description}
      onPress={() => onSelect(item)} style={({pressed}) => [styles.pill, {
        backgroundColor:pressed ? colors['color-bg-surface'] : colors['color-bg-paper'],
        borderColor:pressed ? colors['color-border-focus'] : colors['color-border-paper'],
        transform:[{translateY:pressed ? 1 : 0}],
      }]}>
      <View style={styles.icon}><Icon color={colors['color-text-primary']} /></View>
      <InkLabel style={[styles.label,{color:colors['color-text-primary']}]}>{item.label}</InkLabel>
    </Pressable>;
  })}</View>;
}
const styles = StyleSheet.create({
  strip:{flexDirection:'row', flexWrap:'wrap', justifyContent:'center', gap:10.4, width:'100%', paddingTop:3.2, paddingBottom:1.6},
  pill:{flexDirection:'row', alignItems:'center', gap:8.8, paddingVertical:11.52, paddingHorizontal:16, borderRadius:999, borderWidth:1, maxWidth:'100%', shadowColor:'#5b452c', shadowOpacity:0.05, shadowRadius:9, shadowOffset:{width:0,height:8}},
  icon:{width:24,height:24,alignItems:'center',justifyContent:'center',borderRadius:999,backgroundColor:'rgba(91, 69, 44, 0.08)',flexShrink:0},
  label:{fontSize:14.08,fontWeight:'600',letterSpacing:0.16,flexShrink:1},
});
