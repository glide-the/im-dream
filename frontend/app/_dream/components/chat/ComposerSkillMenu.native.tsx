// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original filtered Skill options, current keyboard choice and actual context usage.
// [Output] Native original command labels/help and text-only selection callbacks.
// [Pos] Composer-local presentation; no discovery, command execution or HTTP ownership.
import {Pressable,ScrollView,StyleSheet,View} from 'react-native';
import Svg,{Circle} from 'react-native-svg';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {contextUsagePercentage,type ContextUsageSnapshot} from '../../lib/context-compaction';
import type {AvailableSkillCommand} from './slashSkillCommands';
export default function ComposerSkillMenu({commands,activeIndex,onSelect,contextUsage}:{commands:readonly AvailableSkillCommand[];activeIndex:number;onSelect:(command:AvailableSkillCommand)=>void;contextUsage?:ContextUsageSnapshot}) {
  const {t}=useTranslation(),colors=useInkColors();
  const percent=contextUsagePercentage(contextUsage),circumference=2*Math.PI*7.2;
  if(!commands.length)return null;
  return <ScrollView accessibilityRole="menu" accessibilityLabel={t('chat.inputDock.commandMenu')} keyboardShouldPersistTaps="handled" style={[styles.menu,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface-solid']}]} contentContainerStyle={styles.content}>
    {commands.map((command,index)=>{
      const help=command.command==='/compact'?`${t('chat.inputDock.compactDescription')}（${percent===undefined?t('chat.inputDock.contextUnavailable'):t('chat.inputDock.contextUsed',{percent})}）`:command.sourceLabel;
      return <Pressable key={`${command.sourceLabel}:${command.command}`} accessibilityRole="menuitem" accessibilityLabel={`${command.command} ${help}`} accessibilityState={{selected:index===activeIndex}} onPress={()=>onSelect(command)} style={({pressed})=>[styles.option,{backgroundColor:pressed || index===activeIndex?colors['color-bg-hover']:'transparent'}]}>
        {command.command==='/compact'?<Svg width={17.6} height={17.6} viewBox="0 0 17.6 17.6" accessible={false}>
          <Circle cx={8.8} cy={8.8} r={7.2} fill="none" stroke={colors['color-border-paper']} strokeWidth={3.2} />
          {percent!==undefined?<Circle cx={8.8} cy={8.8} r={7.2} fill="none" stroke={colors['color-text-primary']} strokeWidth={3.2} strokeDasharray={`${circumference*percent/100} ${circumference}`} rotation={-90} origin="8.8, 8.8" />:null}
        </Svg>:null}
        <InkLabel style={{fontSize:13.12,fontWeight:'600',color:colors['color-text-primary']}}>{command.command}</InkLabel>
        <InkLabel style={{fontSize:11.2,color:colors['color-text-muted'],flexShrink:1}}>{help}</InkLabel>
      </Pressable>;
    })}
  </ScrollView>;
}
const styles=StyleSheet.create({menu:{marginTop:8,maxHeight:240,borderWidth:1,borderRadius:12},content:{padding:5.6,gap:4},option:{minHeight:44,paddingVertical:8.8,paddingHorizontal:10.4,borderRadius:8.8,flexDirection:'row',alignItems:'center',flexWrap:'wrap',gap:8}});
