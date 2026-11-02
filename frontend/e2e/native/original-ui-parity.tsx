// [Input] Production native QuickActionStrip, original translation keys and typography.
// [Output] Isolated component rendering and callback check; no runtime, account or model calls.
// [Pos] Explicit native visual harness entry, compiled only by the named parity build command.
// [Sync] 2026-10-28: render the production queue card for native menu, edit and owner/selected control qualification.
import {useState} from 'react';
import {AppRegistry, Pressable, SafeAreaView, Text, View} from 'react-native';
import {useTranslation} from 'react-i18next';
import '../../app/_dream/i18n';
import QuickActionStrip from '../../app/_dream/components/chat/QuickActionStrip.native';
import {buildDefaultLandingQuickActions} from '../../app/_dream/components/chat/chatLandingActions';
import InkLabel from '../../src/components/InkLabel.native';
import {inkColors} from '../../src/components/inkColors';
import ChatHistoryList from '../../app/_dream/components/chat/ChatHistoryList.native';
import {groupChatThreadsByDate} from '../../app/_dream/components/chat/chatHistoryPresentation';
import type {ChatHistoryThread} from '../../app/_dream/api/chatHistoryApi';
import ChatTopActions from '../../app/_dream/components/chat/ChatTopActions.native';
import ThreadInputQueueCard from '../../app/_dream/components/chat/ThreadInputQueueCard.native';
import type {ThreadInputEntry} from '../../app/_dream/components/chat/threadInputQueue';
function OriginalUIParity() {
  const {t} = useTranslation();
  const [selected,setSelected] = useState('');
  const [historyEvent,setHistoryEvent] = useState('');
  const [topEvent,setTopEvent] = useState('');
  const [activityOpen,setActivityOpen] = useState(false);
  const [workspaceOpen,setWorkspaceOpen] = useState(false);
  const [queueEvent,setQueueEvent]=useState('No queue action'),[queueOwner,setQueueOwner]=useState(true);
  const [queueEntry,setQueueEntry]=useState<ThreadInputEntry>({message_id:'fixture-queue-message',thread_id:'fixture-source-thread',queue_sequence:'1',status:'queued',revision:1,dispatch_turn_id:null,created_at:'2026-10-28T00:00:00Z',text:'Original queued draft'});
  const [state,setState] = useState<'rows'|'empty'|'error'|'more-error'>('rows');
  const [rows,setRows] = useState<ChatHistoryThread[]>([
    {id:'fixture-selected',title:'Original history title',created_at:'2026-10-28T08:00:00',updated_at:'2026-10-28T08:00:00',match:{strategy:'fuzzy',score:1,fields:['messages'],excerpt:'Original search excerpt'}},
    {id:'fixture-older',title:'Earlier conversation',created_at:'2026-10-27T08:00:00',updated_at:'2026-10-27T08:00:00'},
  ]);
  const colors = inkColors('light',false);
  return <SafeAreaView style={{flex:1,backgroundColor:colors['color-bg-app']}}><View style={{padding:12,gap:24,flex:1}}>
    <Text style={{fontSize:16}}>Component validation — no backend started</Text>
    <ChatTopActions creating={false} activityOpen={activityOpen} workspaceOpen={workspaceOpen} workspaceEnabled
      onNewChat={() => setTopEvent('new')} onToggleActivity={() => {setActivityOpen(value => !value);setTopEvent('activity');}}
      onToggleWorkspace={() => {setWorkspaceOpen(value => !value);setTopEvent('workspace');}} onShare={() => setTopEvent('share')} />
    <Text testID="top-event">{topEvent || 'No top action'}</Text>
    <QuickActionStrip items={buildDefaultLandingQuickActions(t)} onSelect={item => setSelected(item.id)} />
    <View style={{gap:8}}>
      <ThreadInputQueueCard entry={queueEntry} localOwner={queueOwner}
        onGuide={async entry=>{setQueueEvent(`guide:${entry.revision}`);setQueueEntry({...entry,status:'selected',revision:entry.revision+1});}}
        onCancel={async entry=>{setQueueEvent(`cancel:${entry.revision}`);setQueueEntry({...entry,status:'cancelled',revision:entry.revision+1});}}
        onEdit={async(entry,text)=>{setQueueEvent(`edit:${text}`);setQueueEntry({...entry,text,revision:entry.revision+1});}}
        onSideChat={async entry=>{setQueueEvent(`side:${entry.message_id}`);}} />
      <Text testID="queue-event">{queueEvent}</Text>
      <View style={{flexDirection:'row',gap:12}}>
        <Pressable accessibilityRole="button" onPress={()=>setQueueOwner(value=>!value)} style={{minHeight:44,justifyContent:'center'}}><Text>Toggle fixture owner</Text></Pressable>
        <Pressable accessibilityRole="button" onPress={()=>setQueueEntry(value=>({...value,status:'queued'}))} style={{minHeight:44,justifyContent:'center'}}><Text>Reset fixture queue</Text></Pressable>
      </View>
    </View>
    <InkLabel style={{fontSize:20,color:colors['color-text-primary']}}>Ink &amp; Memory · 聊天历史</InkLabel>
    <Text testID="original-action-selection">{selected || 'No action selected'}</Text>
    <View style={{flexDirection:'row',gap:16,flexWrap:'wrap'}}>{(['rows','empty','error','more-error'] as const).map(value => <Pressable key={value} accessibilityRole="button" onPress={() => setState(value)} style={{minHeight:44,justifyContent:'center'}}><Text>{value}</Text></Pressable>)}</View>
    <Text testID="history-event">{historyEvent || 'No history event'}</Text>
    <ChatHistoryList groups={groupChatThreadsByDate(state === 'empty' ? [] : rows,t,'2026-10-28')} activeThreadId="fixture-selected" loading={false} loadingMore={false} error={state === 'error'} moreError={state === 'more-error'} hasMore={state === 'more-error'}
      onSelectThread={id => setHistoryEvent(`select:${id}`)} onDeleteThread={id => {setHistoryEvent(`delete:${id}`);setRows(current => current.filter(row => row.id !== id));}}
      onReload={() => {setHistoryEvent('reload');setState('rows');}} onLoadMore={() => {setHistoryEvent('load-more');setState('rows');}} />
  </View></SafeAreaView>;
}
AppRegistry.registerComponent('InkMemory',() => OriginalUIParity);
