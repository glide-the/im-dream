// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Sync] 2026-10-28: retain landing actions while initial server configuration is unreadable; submission readiness follows the caller.
// [Sync] 2026-10-28: allow App-level search ownership outside the hidden underlying scene while activity/detail is open.
// [Input] Original composer/conversation slots, quick actions, history state and business callbacks.
// [Output] Original Chat landing order and conversation scroll/composer ownership with native search.
// [Pos] Native Chat page layout; the same composer slot survives the first Thread creation.
// [Sync] 2026-10-28: share landing actions/history scrolling and let the composer shrink within the keyboard-adjusted scene.
import type {ReactNode} from 'react';
import {Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import ChatHistoryList from './ChatHistoryList.native';
import ChatHistorySearch,{type NativeChatHistory} from './ChatHistorySearch.native';
import QuickActionStrip from './QuickActionStrip.native';
import type {QuickActionStripItem} from './QuickActionStrip.types';
import {groupChatThreadsByDate} from './chatHistoryPresentation';
import {IconClock,IconSearch} from './Icons';
export interface NativeChatPageProps {hasConversation:boolean;composer:ReactNode;conversation:ReactNode;history:NativeChatHistory;quickActions:QuickActionStripItem[];quickActionsDisabled?:boolean;onQuickAction:(item:QuickActionStripItem)=>void;onSelectThread:(id:string)=>void;onDeleteThread:(id:string)=>void;activeThreadId?:string|null;showSearch?:boolean;}
export default function ChatPage({hasConversation,composer,conversation,history,quickActions,quickActionsDisabled=false,onQuickAction,onSelectThread,onDeleteThread,activeThreadId,showSearch=true}:NativeChatPageProps){
  const {t}=useTranslation(),colors=useInkColors();
  return <View style={styles.fill}>
    {/* Flex order changes presentation while React keeps the same composer instance and attachment owner. */}
    <View style={[styles.page,{flexDirection:hasConversation?'column-reverse':'column'}]}>
      <View testID="native-chat-composer" style={styles.composer}>{composer}</View>
      <View style={styles.fill} testID={hasConversation?'native-chat-conversation':'native-chat-landing-content'}>
        {hasConversation?conversation:<ChatHistoryList header={<>
          <View style={styles.quick}><QuickActionStrip items={quickActions} onSelect={onQuickAction} disabled={quickActionsDisabled} /></View>
          <View style={styles.historyToolbar}>
            <View accessibilityRole="tab" accessibilityLabel={t('chat.tabs.history')} accessibilityState={{selected:true}} style={[styles.historyTab,{backgroundColor:colors['color-bg-surface'],borderColor:colors['color-border-paper']}]}>
              <IconClock width={13.6} height={13.6} color={colors['color-text-primary']} /><InkLabel style={{color:colors['color-text-primary'],fontSize:13.12,fontWeight:'700'}}>{t('chat.tabs.history')}</InkLabel>
            </View>
            <Pressable accessibilityRole="button" accessibilityLabel={t('chat.search.button')} onPress={history.openSearch} style={[styles.search,{backgroundColor:colors['color-bg-surface'],borderColor:colors['color-border-paper']}]}>
              <IconSearch width={13.6} height={13.6} color={colors['color-text-secondary']} /><InkLabel style={{fontSize:12.8,fontWeight:'600',color:colors['color-text-secondary']}}>{t('chat.search.button')}</InkLabel>
            </Pressable>
          </View>
          {history.deleteError?<InkLabel accessibilityRole="alert" style={{color:colors['color-state-error'],padding:8}}>{t('chat.activity.historyFailed')}</InkLabel>:null}
          </>} groups={groupChatThreadsByDate(history.threads,t)} activeThreadId={activeThreadId} deletingThreadId={history.deletingId}
            loading={history.loading} loadingMore={history.loadingMore} error={history.error} moreError={history.moreError} hasMore={history.hasMore}
            onSelectThread={onSelectThread} onDeleteThread={onDeleteThread} onReload={()=>void history.reload()} onLoadMore={()=>void history.loadMore()} />}
      </View>
    </View>
    {showSearch?<ChatHistorySearch history={history} activeThreadId={activeThreadId} onSelect={onSelectThread} />:null}
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},page:{flex:1,minHeight:0,width:'100%',maxWidth:832,alignSelf:'center'},composer:{flexShrink:1,minHeight:0,paddingHorizontal:12,paddingVertical:8},quick:{paddingHorizontal:12,paddingTop:8,paddingBottom:16},historyToolbar:{flexDirection:'row',flexWrap:'wrap',alignItems:'center',justifyContent:'space-between',gap:12,paddingHorizontal:12,paddingBottom:8,flexShrink:0},historyTab:{minHeight:44,flexDirection:'row',alignItems:'center',gap:6.4,borderWidth:1,borderRadius:999,paddingVertical:8.8,paddingHorizontal:14.4},search:{minHeight:44,flexDirection:'row',alignItems:'center',gap:6.4,borderWidth:1,borderRadius:999,paddingVertical:8,paddingHorizontal:12}});
