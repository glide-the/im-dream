// [Input] Original analysis-content selection, authenticated expansion and Reflections/Deck catalog readers.
// [Output] Shared mounted Notion scope, Agent candidates, current-selection diagnostics and explicit reload.
// [Pos] State extracted from ReflectionAnalysisContentControls; DOM placement and native presentation stay platform-owned.
// [Sync] 2026-10-29: retain original ready/stale/unavailable rules and copy; opening only reads existing APIs.
import {useEffect,useRef,useState} from 'react';
import {useTranslation} from 'react-i18next';
import {getReflectionAnalysisContent,type ReflectionAnalysisContentCandidates,type ReflectionAnalysisContentOptions} from '../api/reflectionsApi';
import {listDecksWithVoices} from '../api/deckReadApi';
import type {Deck} from '../api/voiceApi';
export default function useReflectionAnalysisContent({value,authenticated,expanded,readCandidates,readDecks}:{value:ReflectionAnalysisContentOptions;authenticated:boolean;expanded:boolean;readCandidates?:typeof getReflectionAnalysisContent;readDecks?:()=>Promise<Deck[]>}) {
  const {i18n}=useTranslation(),zh=i18n.language.startsWith('zh');
  const owners=useRef({getReflectionAnalysisContent:readCandidates??getReflectionAnalysisContent,listDecksWithVoices:readDecks??listDecksWithVoices});
  const {getReflectionAnalysisContent:readContent,listDecksWithVoices:readCatalog}=owners.current;
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(false);
  const [deckLoading, setDeckLoading] = useState(false);
  const [decks, setDecks] = useState<Deck[]>([]);
  const [candidates, setCandidates] = useState<ReflectionAnalysisContentCandidates | null>(null);
  const [notionError, setNotionError] = useState(false);
  const [deckError, setDeckError] = useState(false);
  useEffect(() => {
    if (!expanded || !authenticated) return;
    let disposed = false;
    setLoading(true); setDeckLoading(true); setNotionError(false); setDeckError(false);
    void readContent().then(result => {
      if (!disposed) setCandidates(result);
    }).catch(() => { if (!disposed) setNotionError(true); }).finally(() => { if (!disposed) setLoading(false); });
    void readCatalog()
      .then(items => { if (!disposed) setDecks(items.filter(deck => deck.enabled)); })
      .catch(() => { if (!disposed) setDeckError(true); })
      .finally(() => { if (!disposed) setDeckLoading(false); });
    return () => { disposed = true; };
  }, [authenticated, expanded, revision]);

  const ready = candidates?.status === 'ready' && candidates.selection_available && !notionError && !loading;
  const staleNotion = value.include_notion && ready && (value.connector_id !== candidates?.connector_id
    || value.snapshot_version !== candidates?.snapshot_version);
  const unavailableAgent = !!value.agent_id && !deckLoading && !deckError
    && !decks.some(deck => deck.id === value.deck_id && deck.voices?.some(agent => agent.id === value.agent_id && agent.enabled));
  const status = !authenticated ? (zh ? '请登录后选择分析内容。' : 'Log in to select analysis content.')
    : loading ? (zh ? '正在读取已挂载资源。' : 'Loading linked resources.')
    : notionError ? (zh ? 'Notion 资源读取失败，请重试。' : 'Notion resources could not be loaded. Retry.')
    : candidates?.selection_available === false ? (zh ? '分析内容暂时不可用，请稍后重试。' : 'Analysis content is temporarily unavailable. Retry later.')
    : candidates?.status === 'disconnected' ? (zh ? '尚未连接 Notion，请在设置中连接。' : 'Connect Notion in Settings.')
    : candidates?.status === 'auth_required' ? (zh ? 'Notion 授权已失效，请在设置中重新连接。' : 'Reconnect Notion in Settings.')
    : candidates?.status === 'no_snapshot' ? (zh ? '尚无资源快照，请在设置中完成资源同步。' : 'Sync linked resources in Settings first.')
    : candidates?.status === 'scope_changed' ? (zh ? '已挂载资源已改变，请在设置中重新同步。' : 'Linked resources changed. Sync them again in Settings.')
    : candidates?.status === 'empty' ? (zh ? '没有已挂载的 Notion 页面。' : 'No Notion pages are linked.')
    : staleNotion ? (zh ? 'Notion 资源已更新，请关闭再开启 Notion，选择最新内容。' : 'Notion resources changed. Turn Notion off and on to select the current content.')
    : candidates?.status === 'ready' ? (zh ? `可按需读取 ${candidates.page_count} 个已挂载页面。` : `Read from ${candidates.page_count} linked pages as needed.`) : '';

 return {setRevision,loading,deckLoading,decks,candidates,deckError,ready,status,unavailableAgent};
}
