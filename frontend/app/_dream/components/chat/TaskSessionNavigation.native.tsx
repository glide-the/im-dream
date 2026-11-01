// [Input] Original owner-filtered direct source relation and canonical Thread navigation callback.
// [Output] Original source marker above the first user message with a touch-sized native action.
// [Pos] Native source navigation only; task creation, status and message data remain server-owned.
import {Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {IconChevronRight,IconMessageCircle} from './Icons';
import type {TaskSessionLinksSnapshot} from './taskSessionLinks';
export function TaskSessionSourceMarker({source,onNavigateThread}:{source:TaskSessionLinksSnapshot['source'];onNavigateThread?:(id:string)=>void}){
 const {t}=useTranslation(),colors=useInkColors();if(!source||!onNavigateThread)return null;
 return <View style={styles.align}><Pressable accessibilityRole="button" accessibilityLabel={t('chat.taskSessionNavigation.backToSourceAria')} onPress={()=>onNavigateThread(source.source_thread_id)} style={styles.button}>
  <IconMessageCircle width={16} height={16} color={colors['color-text-secondary']}/><InkLabel numberOfLines={1} style={{flexShrink:1,color:colors['color-text-secondary']}}>{source.source_title?t('chat.taskSessionNavigation.fromNamedSource',{title:source.source_title}):t('chat.taskSessionNavigation.fromSource')}</InkLabel><IconChevronRight width={15} height={15} color={colors['color-text-secondary']}/>
 </Pressable></View>;
}
const styles=StyleSheet.create({align:{alignSelf:'flex-end',maxWidth:'85%',minWidth:0},button:{minHeight:44,flexDirection:'row',alignItems:'center',gap:8,paddingHorizontal:10}});
