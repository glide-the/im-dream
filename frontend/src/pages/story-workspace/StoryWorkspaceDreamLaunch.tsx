// [Input] Actor-scoped Dream re-entry rows from the production Story Workspace API.
// [Output] Dream home: active Dream context and durable My Dream re-entry list.
// [Pos] Story Workspace Dream no-run surface; all new interactions start in canonical Chat.
// [Sync] 2026-08-14: remove the duplicate creation form and reorganize the no-run page into
//                    active Dream previews and durable user Dream re-entry.
// [Sync] 2026-08-14: restore page-level scrolling, natural-flow run groups, and whole-row links.
// [Sync] 2026-08-14: replace Quick Start with actor-scoped in-progress Dream cards.
// [Sync] 2026-08-14: group My Dream by the real initial/in-progress phase only.
// [Sync] 2026-08-14: simplify the active section to a borderless three-item preview with explicit reveal.
// [Sync] 2026-08-14: include and label the server-projected system default in Community Decks.
// [Sync] 2026-08-14: fall back to the actor's server-identified initialized default
//                    when the shared system template row is not published locally.
// [Sync] 2026-08-16: remove the deferred Deck marketplace/community installation surface.

import { useMemo, useState } from 'react';
import {
  useStoryWorkspaceDreamRuns,
  type StoryWorkspaceDreamReentryItem,
} from '../../hooks/story-workspace';
import {
  storyWorkspaceDreamReentryLifecycleCopy,
  storyWorkspaceDreamReentryOutcomeCopy,
  storyWorkspaceFilterDreamReentryRuns,
  storyWorkspacePaginateDreamReentryRuns,
} from './dreamReentryViewModel';

export interface StoryWorkspaceDreamLaunchProps {
  initialDeckId?: string | null;
  onNavigate?: (path: string) => void;
}

type StoryWorkspaceDreamReentryGroup = StoryWorkspaceDreamReentryItem['outcome'];

/** Presentation-only preview density; it does not affect Dream data or lifecycle policy. */
const STORY_WORKSPACE_ACTIVE_DREAM_PREVIEW_COUNT = 3;

function StoryWorkspaceDreamReentryList({
  runs,
  onNavigate,
}: {
  runs: readonly StoryWorkspaceDreamReentryItem[];
  onNavigate?: (path: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [pages, setPages] = useState<Record<StoryWorkspaceDreamReentryGroup, number>>({
    initial: 1,
    in_progress: 1,
  });
  const filteredRuns = useMemo(
    () => storyWorkspaceFilterDreamReentryRuns(runs, query),
    [query, runs],
  );
  const groups: Array<{
    group: StoryWorkspaceDreamReentryGroup;
    title: string;
    runs: readonly StoryWorkspaceDreamReentryItem[];
  }> = [
    { group: 'in_progress', title: '进行中', runs: filteredRuns.filter((run) => run.outcome === 'in_progress') },
    { group: 'initial', title: '初始状态', runs: filteredRuns.filter((run) => run.outcome === 'initial') },
  ];

  return (
    <div className="story-workspace-dream-home__runs">
      <div className="story-workspace-dream-reentry__search" role="search">
        <label htmlFor="story-workspace-dream-search">搜索我的 Dream</label>
        <input
          id="story-workspace-dream-search"
          onChange={(event) => {
            setQuery(event.currentTarget.value);
            setPages({ initial: 1, in_progress: 1 });
          }}
          placeholder="目标、Deck 或 Run ID"
          type="search"
          value={query}
        />
        <span>{query.trim() ? `${filteredRuns.length} 个结果` : `共 ${runs.length} 个`}</span>
      </div>

      {groups.map(({ group, title, runs: groupRuns }) => {
        if (groupRuns.length === 0) return null;
        const pagination = storyWorkspacePaginateDreamReentryRuns(groupRuns, pages[group]);
        return (
          <section className="story-workspace-dream-reentry__group" key={group}>
            <header><h3>{title}</h3><span>{groupRuns.length}</span></header>
            <div className="story-workspace-dream-reentry__items">
              {pagination.items.map((run) => (
                <a
                  className="story-workspace-dream-reentry__item"
                  data-outcome={run.outcome}
                  href={run.href}
                  key={run.storyWorkspaceRunId}
                  onClick={(event) => {
                    if (
                      !onNavigate
                      || event.button !== 0
                      || event.metaKey
                      || event.ctrlKey
                      || event.shiftKey
                      || event.altKey
                    ) return;
                    event.preventDefault();
                    onNavigate(run.href);
                  }}
                >
                  <span className="story-workspace-dream-reentry__item-copy">
                    <strong>{run.displayTitle}</strong>
                    <small>{run.deckDisplayName} · {storyWorkspaceDreamReentryLifecycleCopy(run.lifecycle)}</small>
                  </span>
                  <span className="story-workspace-dream-reentry__item-status" data-outcome={run.outcome}>
                    {storyWorkspaceDreamReentryOutcomeCopy(run.outcome)}
                  </span>
                  <time dateTime={run.lastActivityAt}>
                    {new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(run.lastActivityAt))}
                  </time>
                  <span className="story-workspace-dream-reentry__item-action" aria-hidden="true">打开工作台 →</span>
                </a>
              ))}
            </div>
            {pagination.totalPages > 1 ? (
              <nav aria-label={`${title}分页`} className="story-workspace-dream-reentry__pagination">
                <button disabled={pagination.page === 1} onClick={() => setPages((current) => ({ ...current, [group]: pagination.page - 1 }))} type="button">上一页</button>
                <span aria-live="polite">{pagination.page} / {pagination.totalPages}</span>
                <button disabled={pagination.page === pagination.totalPages} onClick={() => setPages((current) => ({ ...current, [group]: pagination.page + 1 }))} type="button">下一页</button>
              </nav>
            ) : null}
          </section>
        );
      })}

      {filteredRuns.length === 0 ? (
        <p className="story-workspace-dream-reentry__empty" role="status">
          {runs.length === 0 ? '还没有 Dream。请先前往卡组页选择 Dream Deck。' : '没有匹配的 Dream。'}
        </p>
      ) : null}
    </div>
  );
}

function ActiveDreamCard({
  run,
  onNavigate,
}: {
  run: StoryWorkspaceDreamReentryItem;
  onNavigate?: (path: string) => void;
}) {
  return (
    <a
      aria-label={`${run.displayTitle} · 继续创作`}
      className="story-workspace-dream-home__active-card"
      href={run.href}
      onClick={(event) => {
        if (
          !onNavigate
          || event.button !== 0
          || event.metaKey
          || event.ctrlKey
          || event.shiftKey
          || event.altKey
        ) return;
        event.preventDefault();
        onNavigate(run.href);
      }}
    >
      <span className="story-workspace-dream-home__active-copy">
        <strong>{run.displayTitle}</strong>
        <span>{run.deckDisplayName}</span>
      </span>
      <span className="story-workspace-dream-home__active-action" aria-hidden="true">继续 →</span>
    </a>
  );
}

export function StoryWorkspaceDreamLaunch({
  onNavigate,
}: StoryWorkspaceDreamLaunchProps) {
  const [showAllActiveDreams, setShowAllActiveDreams] = useState(false);
  const reentry = useStoryWorkspaceDreamRuns();
  const activeDreamRuns = useMemo(
    () => reentry.data?.runs.filter((run) => run.outcome === 'in_progress') ?? [],
    [reentry.data?.runs],
  );
  const visibleActiveDreamRuns = showAllActiveDreams
    ? activeDreamRuns
    : activeDreamRuns.slice(0, STORY_WORKSPACE_ACTIVE_DREAM_PREVIEW_COUNT);
  const hiddenActiveDreamCount = Math.max(0, activeDreamRuns.length - visibleActiveDreamRuns.length);

  return (
    <div className="story-workspace-dream-home" aria-labelledby="dream-home-title">
      <header className="story-workspace-dream-home__header">
        <div className="story-workspace-dream-home__header-copy">
          <h1 id="dream-home-title">Dream</h1>
          <span>继续创作，或选择一个 Deck 开始新的 Dream。</span>
        </div>
      </header>

      <div className="story-workspace-dream-home__content">
        <section className="story-workspace-dream-home__section story-workspace-dream-home__section--active" aria-labelledby="dream-active-title">
          <header><h2 id="dream-active-title">进行中的 Dream</h2><span>{activeDreamRuns.length}</span></header>
          {reentry.isLoading ? <p role="status">正在恢复进行中的 Dream…</p> : null}
          {reentry.error ? <div className="story-workspace-dream-home__error" role="alert">进行中的 Dream 暂时无法加载。<button onClick={reentry.refetch} type="button">重试</button></div> : null}
          {!reentry.isLoading && !reentry.error && activeDreamRuns.length === 0 ? <p className="story-workspace-dream-home__empty">当前没有进行中的 Dream。可前往卡组页选择 Dream Deck，并在 Chat 中开始创作。</p> : null}
          <div className="story-workspace-dream-home__active-grid" id="dream-active-list">
            {visibleActiveDreamRuns.map((run) => (
              <ActiveDreamCard key={run.storyWorkspaceRunId} onNavigate={onNavigate} run={run} />
            ))}
          </div>
          {activeDreamRuns.length > STORY_WORKSPACE_ACTIVE_DREAM_PREVIEW_COUNT ? (
            <button
              aria-controls="dream-active-list"
              aria-expanded={showAllActiveDreams}
              className="story-workspace-dream-home__more"
              onClick={() => setShowAllActiveDreams((current) => !current)}
              type="button"
            >
              {showAllActiveDreams ? '收起' : `查看更多（${hiddenActiveDreamCount}）`}
            </button>
          ) : null}
        </section>

        <section className="story-workspace-dream-home__section story-workspace-dream-home__section--runs" aria-labelledby="my-dream-title">
          <header><h2 id="my-dream-title">我的 Dream</h2><span>{reentry.data?.runs.length ?? 0}</span></header>
          {reentry.isLoading ? <p role="status">正在恢复我的 Dream…</p> : null}
          {reentry.error ? <div className="story-workspace-dream-home__error" role="alert">我的 Dream 暂时无法加载。<button onClick={reentry.refetch} type="button">重试</button></div> : null}
          {reentry.data ? <StoryWorkspaceDreamReentryList onNavigate={onNavigate} runs={reentry.data.runs} /> : null}
        </section>
      </div>
    </div>
  );
}
