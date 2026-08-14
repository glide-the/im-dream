// [Input] Enabled Decks, durable Dream runs, one creation goal, and the dedicated Dream start hook.
// [Output] Canonical-title-first Dream re-entry plus a launch form that navigates to the accepted run projection.
// [Pos] Story Workspace Dream no-run surface (Task 3 U4)
// [Sync] 2026-08-13: add client-side re-entry search and per-group pagination without changing server order.

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { getDeck, listDecks, type Deck } from '../../api/voiceApi';
import DeckChatSelector from '../../components/deck/DeckChatSelector';
import {
  storyWorkspaceDreamRunPath,
  useStoryWorkspaceDreamLaunch,
  useStoryWorkspaceDreamRuns,
  type StoryWorkspaceDreamReentryItem,
} from '../../hooks/story-workspace';
import {
  storyWorkspaceDreamReentryLifecycleCopy,
  storyWorkspaceFilterDreamReentryRuns,
  storyWorkspacePaginateDreamReentryRuns,
} from './dreamReentryViewModel';

export interface StoryWorkspaceDreamLaunchProps {
  initialDeckId?: string | null;
  onNavigate?: (path: string) => void;
}

type StoryWorkspaceDreamReentryGroup = StoryWorkspaceDreamReentryItem['group'];

function StoryWorkspaceDreamReentryList({
  runs,
  onNavigate,
}: {
  runs: readonly StoryWorkspaceDreamReentryItem[];
  onNavigate?: (path: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [pages, setPages] = useState<Record<StoryWorkspaceDreamReentryGroup, number>>({
    in_progress: 1,
    recent: 1,
  });
  const filteredRuns = useMemo(
    () => storyWorkspaceFilterDreamReentryRuns(runs, query),
    [query, runs],
  );
  const inProgress = filteredRuns.filter((run) => run.group === 'in_progress');
  const recent = filteredRuns.filter((run) => run.group === 'recent');
  const renderRun = (run: StoryWorkspaceDreamReentryItem) => (
    <button
      className="story-workspace-dream-reentry__item"
      key={run.storyWorkspaceRunId}
      onClick={() => onNavigate?.(run.href)}
      type="button"
    >
      <span className="story-workspace-dream-reentry__item-copy">
        <strong>{run.displayTitle}</strong>
        <small>{run.deckDisplayName} · {storyWorkspaceDreamReentryLifecycleCopy(run.lifecycle)} · {run.deckPluginVersion} · Run …{run.storyWorkspaceRunId.slice(-6)}</small>
      </span>
      <span aria-hidden="true">打开</span>
    </button>
  );
  const renderGroup = (
    group: StoryWorkspaceDreamReentryGroup,
    title: string,
    groupRuns: readonly StoryWorkspaceDreamReentryItem[],
  ) => {
    if (groupRuns.length === 0) return null;
    const pagination = storyWorkspacePaginateDreamReentryRuns(groupRuns, pages[group]);
    const setPage = (page: number) => {
      setPages((current) => ({ ...current, [group]: page }));
    };
    return (
      <div className="story-workspace-dream-reentry__group">
        <header>
          <h2>{title}</h2>
          <span>{groupRuns.length}</span>
        </header>
        <div className="story-workspace-dream-reentry__items">
          {pagination.items.map(renderRun)}
        </div>
        {pagination.totalPages > 1 && (
          <nav aria-label={`${title} 分页`} className="story-workspace-dream-reentry__pagination">
            <button
              aria-label={`上一页，当前第 ${pagination.page} 页`}
              disabled={pagination.page === 1}
              onClick={() => setPage(pagination.page - 1)}
              type="button"
            >上一页</button>
            <span aria-live="polite">{pagination.page} / {pagination.totalPages}</span>
            <button
              aria-label={`下一页，当前第 ${pagination.page} 页`}
              disabled={pagination.page === pagination.totalPages}
              onClick={() => setPage(pagination.page + 1)}
              type="button"
            >下一页</button>
          </nav>
        )}
      </div>
    );
  };

  return (
    <section className="story-workspace-dream-reentry" aria-label="可恢复的 Dream">
      <div className="story-workspace-dream-reentry__search" role="search">
        <label htmlFor="story-workspace-dream-search">搜索 Dream</label>
        <input
          id="story-workspace-dream-search"
          onChange={(event) => {
            setQuery(event.currentTarget.value);
            setPages({ in_progress: 1, recent: 1 });
          }}
          placeholder="目标、Deck 或 Run ID"
          type="search"
          value={query}
        />
        <span>{query.trim() ? `${filteredRuns.length} 个结果` : `共 ${runs.length} 个`}</span>
      </div>
      <div className="story-workspace-dream-reentry__groups">
        {renderGroup('in_progress', '进行中的 Dream', inProgress)}
        {renderGroup('recent', '最近的 Dream', recent)}
        {filteredRuns.length === 0 && (
          <p className="story-workspace-dream-reentry__empty" role="status">
            没有匹配的 Dream，试试目标、Deck 名称或 Run ID。
          </p>
        )}
      </div>
    </section>
  );
}

function deckDisplayName(deck: Deck): string {
  return deck.name_zh?.trim() || deck.name?.trim() || deck.name_en?.trim() || deck.id;
}

export function StoryWorkspaceDreamLaunch({
  initialDeckId,
  onNavigate,
}: StoryWorkspaceDreamLaunchProps) {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [goal, setGoal] = useState('');
  const [isLoadingDecks, setIsLoadingDecks] = useState(true);
  const [deckError, setDeckError] = useState<Error | null>(null);
  const launch = useStoryWorkspaceDreamLaunch();
  const reentry = useStoryWorkspaceDreamRuns();

  useEffect(() => {
    let active = true;
    setIsLoadingDecks(true);
    void listDecks().then((availableDecks) => Promise.all(availableDecks.map(async (deck) => {
      try {
        return await getDeck(deck.id);
      } catch {
        return deck;
      }
    }))).then((availableDecks) => {
      if (!active) return;
      const enabledDecks = availableDecks.filter((deck) => deck.enabled);
      setDecks(enabledDecks);
      setSelectedDeckId((currentDeckId) => {
        const nextDeckId = enabledDecks.some((deck) => deck.id === currentDeckId)
          ? currentDeckId
          : enabledDecks.some((deck) => deck.id === initialDeckId)
            ? initialDeckId ?? ''
            : enabledDecks[0]?.id ?? '';
        const nextDeck = enabledDecks.find((deck) => deck.id === nextDeckId);
        setSelectedAgentId((currentAgentId) => {
          const agents = (nextDeck?.voices || []).filter((agent) => agent.enabled);
          return agents.some((agent) => agent.id === currentAgentId)
            ? currentAgentId
            : agents[0]?.id ?? '';
        });
        return nextDeckId;
      });
      setDeckError(null);
    }).catch(() => {
      if (!active) return;
      setDeckError(new Error('暂时无法读取 Deck，请稍后再打开 Dream。'));
    }).finally(() => {
      if (active) setIsLoadingDecks(false);
    });
    return () => {
      active = false;
    };
  }, [initialDeckId]);

  const selectedDeck = useMemo(
    () => decks.find((deck) => deck.id === selectedDeckId) ?? null,
    [decks, selectedDeckId],
  );
  const selectedAgent = selectedDeck?.voices?.find((agent) => agent.id === selectedAgentId) ?? null;
  const canStart = Boolean(selectedDeckId && selectedAgentId && goal.trim() && !launch.isLaunching);
  const visibleError = deckError ?? launch.error;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canStart) return;
    void launch.start(selectedDeckId, selectedAgentId, goal).then((accepted) => {
      onNavigate?.(storyWorkspaceDreamRunPath(accepted.workflowRunId));
    }).catch(() => {
      // The hook keeps the technical error on this surface. There is no Dream
      // rejection/failure branch and the same form remains editable.
    });
  };

  return (
    <section className="story-workspace-dream-launch" aria-labelledby="dream-launch-title">
      <header className="story-workspace-dream-launch__header">
        <p>Dream · Agent workspace</p>
        <h1 id="dream-launch-title">发起一次 Dream</h1>
        <span>选择 Agent 和创作目标。Dream 会逐步写入人物、场景与分镜。</span>
      </header>

      <div className="story-workspace-dream-launch__sheet">
        <div className="story-workspace-dream-launch__reentry">
          {reentry.isLoading && (
            <p className="story-workspace-dream-reentry__loading" role="status">正在恢复可继续的 Dream…</p>
          )}
          {reentry.data && reentry.data.runs.length > 0 && (
            <StoryWorkspaceDreamReentryList onNavigate={onNavigate} runs={reentry.data.runs} />
          )}
          {reentry.error && (
            <p className="story-workspace-dream-reentry__error" role="status">
              暂时无法恢复 Dream 列表，请稍后重新打开。
            </p>
          )}
        </div>
        <form className="story-workspace-dream-launch__form" onSubmit={handleSubmit}>
          <div className="story-workspace-dream-launch__form-body">
            <div className="story-workspace-dream-launch__form-heading">
              <p>New dream</p>
              <h2>创作设置</h2>
            </div>

            <label>
              <span>Agent</span>
              <DeckChatSelector
                allowNone={false}
                decks={decks}
                error={deckError?.message}
                loading={isLoadingDecks}
                onChange={(selection) => {
                  setSelectedDeckId(selection?.deckId ?? '');
                  setSelectedAgentId(selection?.agentId ?? '');
                }}
                selectedAgentId={selectedAgentId}
                variant="dream"
              />
            </label>

            <label>
              <span>创作目标</span>
              <textarea
                disabled={launch.isLaunching}
                maxLength={12000}
                onChange={(event) => setGoal(event.currentTarget.value)}
                placeholder="例如：创作一个发生在雨夜车站的短篇故事，人物关系克制，结尾保留悬念。"
                rows={8}
                value={goal}
              />
            </label>

            {selectedDeck && selectedAgent && (
              <p className="story-workspace-dream-launch__selection">
                <span>当前 Agent</span>
                <strong>{deckDisplayName(selectedDeck)} · {selectedAgent.name_zh || selectedAgent.name}</strong>
              </p>
            )}
            {visibleError && (
              <p className="story-workspace-dream-launch__error" role="alert">
                {visibleError.message}
              </p>
            )}
          </div>

          <div className="story-workspace-dream-launch__form-actions">
            <button
              aria-busy={launch.isLaunching}
              className="story-workspace-dream-launch__submit"
              disabled={!canStart}
              type="submit"
            >发起 Dream</button>
          </div>
        </form>
      </div>
    </section>
  );
}
