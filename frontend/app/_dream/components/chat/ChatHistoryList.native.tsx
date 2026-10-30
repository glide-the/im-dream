// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original Chat history groups and caller-owned selection/delete/pagination state.
// [Output] Original grouped titles, search excerpts, active marker and loading/retry/empty/end feedback.
// [Pos] Native counterpart of the inline ChatView landing history list; no API or task ownership.
// [Sync] 2026-10-28: allow the original landing actions/search toolbar to share this scroll owner in a keyboard-constrained viewport.
import type {ReactNode} from 'react';
import {ActivityIndicator, Pressable, ScrollView, StyleSheet, View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {IconX} from './Icons';
import type {ChatHistoryGroup} from './chatHistoryPresentation';

export interface ChatHistoryListProps {
  header?: ReactNode;
  groups: ChatHistoryGroup[];
  activeThreadId?: string | null;
  deletingThreadId?: string | null;
  loading: boolean;
  loadingMore: boolean;
  error: boolean;
  moreError: boolean;
  hasMore: boolean;
  onSelectThread: (id: string) => void;
  onDeleteThread: (id: string) => void;
  onReload: () => void;
  onLoadMore: () => void;
}

export default function ChatHistoryList({header, groups, activeThreadId, deletingThreadId, loading, loadingMore, error, moreError, hasMore, onSelectThread, onDeleteThread, onReload, onLoadMore}: ChatHistoryListProps) {
  const {t} = useTranslation();
  const colors = useInkColors();
  const count = groups.reduce((sum, group) => sum + group.threads.length, 0);
  const loadingStatus = () => <ActivityIndicator style={styles.feedback} color={colors['color-text-secondary']} accessibilityLabel={t('chat.activity.historyLoading')} />;
  const failure = (retry: () => void) => <View style={styles.feedback}>
    <InkLabel accessibilityRole="alert" style={{color:colors['color-state-error'],fontSize:12.8}}>{t('chat.activity.historyFailed')}</InkLabel>
    <Pressable accessibilityRole="button" onPress={retry} style={styles.retry}><InkLabel style={{color:colors['color-action-link']}}>{t('chat.activity.retry')}</InkLabel></Pressable>
  </View>;
  return <ScrollView style={styles.list} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled" scrollEventThrottle={100}
    onScroll={({nativeEvent:{contentSize,contentOffset,layoutMeasurement}}) => {
      // Same original 48px remaining-scroll trigger, including the explicit retry gate.
      if (!loading && !loadingMore && hasMore && !moreError && contentSize.height - contentOffset.y - layoutMeasurement.height <= 48) onLoadMore();
    }}>
    {header ? <View style={styles.header}>{header}</View> : null}
    {loading && count === 0 ? loadingStatus() : null}
    {error ? failure(onReload) : null}
    {!loading && !error && count === 0 ? <InkLabel style={[styles.feedback,{color:colors['color-text-muted'],fontSize:12.8}]}>{t('chat.history.empty')}</InkLabel> : null}
    {groups.map(group => <View key={group.label} style={styles.group}>
      <InkLabel accessibilityRole="header" style={[styles.groupLabel,{color:colors['color-text-muted']}]}>{group.label}</InkLabel>
      <View style={styles.rows}>{group.threads.map(thread => {
        const active = thread.id === activeThreadId;
        const deleting = thread.id === deletingThreadId;
        const excerpt = thread.match?.excerpt?.trim();
        const title = thread.title ?? t('chat.history.fallbackTitle');
        return <View key={thread.id} style={styles.row}>
          <Pressable accessibilityRole="button" accessibilityLabel={title} accessibilityState={{selected:active}}
            onPress={() => onSelectThread(thread.id)} style={({pressed}) => [styles.select,{minHeight:excerpt ? 49.6 : 44,borderColor:active ? colors['color-border-paper'] : 'transparent',backgroundColor:active ? colors['color-bg-app'] : pressed ? colors['color-bg-hover'] : 'transparent'}]}>
            <View style={styles.titles}><InkLabel numberOfLines={1} style={[styles.title,{color:colors['color-text-primary']}]}>{title}</InkLabel>
              {excerpt ? <InkLabel numberOfLines={1} style={[styles.excerpt,{color:colors['color-text-muted']}]}>{excerpt}</InkLabel> : null}
            </View>
            {active ? <View style={[styles.marker,{backgroundColor:colors['color-action-link']}]} /> : null}
          </Pressable>
          {/* Touch devices have no persistent hover; expose the same delete action in the trailing target. */}
          <Pressable accessibilityRole="button" accessibilityLabel={`${t('chat.history.deleteThread')}: ${title}`} accessibilityState={{disabled:deleting,busy:deleting}}
            disabled={deleting} onPress={() => onDeleteThread(thread.id)} style={styles.delete}>
            {deleting ? <ActivityIndicator size="small" color={colors['color-text-muted']} /> : <IconX width={12} height={12} color={colors['color-text-secondary']} />}
          </Pressable>
        </View>;
      })}</View>
    </View>)}
    {loadingMore ? loadingStatus() : null}
    {moreError ? failure(onLoadMore) : null}
    {!error && !moreError && !loading && !hasMore && count > 0 ? <InkLabel style={[styles.end,{color:colors['color-text-muted']}]}>{t('chat.history.allShown')}</InkLabel> : null}
  </ScrollView>;
}

const styles = StyleSheet.create({
  list:{flex:1,minHeight:0}, content:{paddingTop:8.8,paddingHorizontal:8.8,paddingBottom:12},
  header:{marginTop:-8.8,marginHorizontal:-8.8,paddingBottom:8.8},
  feedback:{paddingVertical:11.2,paddingHorizontal:7.2}, retry:{minHeight:44,justifyContent:'center',alignSelf:'flex-start'},
  group:{paddingTop:13.6},groupLabel:{paddingHorizontal:6.4,paddingBottom:7.2,fontSize:12.48,fontWeight:'600'},
  rows:{gap:6.4},row:{position:'relative'},select:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:9.6,paddingVertical:7.2,paddingLeft:12,paddingRight:44,borderWidth:1,borderRadius:12.8},
  titles:{flex:1,minWidth:0,gap:2.24},title:{fontSize:13.12,fontWeight:'600'},excerpt:{fontSize:10.88,lineHeight:13.6},
  marker:{width:6.08,height:6.08,borderRadius:999,flexShrink:0},
  delete:{position:'absolute',right:0,top:0,bottom:0,width:44,alignItems:'center',justifyContent:'center'},
  end:{paddingTop:8.8,paddingHorizontal:7.2,paddingBottom:3.2,fontSize:11.52,textAlign:'center'},
});
