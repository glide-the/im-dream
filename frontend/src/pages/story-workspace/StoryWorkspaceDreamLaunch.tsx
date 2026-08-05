// [Input] Enabled Decks, one creation goal, and the dedicated Dream start hook.
// [Output] Dream-only launch form that navigates to the accepted run projection.
// [Pos] Story Workspace Dream no-run surface (Task 3 U4)

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { listDecks, type Deck } from '../../api/voiceApi';
import {
  storyWorkspaceDreamRunPath,
  useStoryWorkspaceDreamLaunch,
  useStoryWorkspaceDreamRuns,
  type StoryWorkspaceDreamReentryItem,
} from '../../hooks/story-workspace';

export interface StoryWorkspaceDreamLaunchProps {
  initialDeckId?: string | null;
  onNavigate?: (path: string) => void;
}

const STORY_WORKSPACE_DREAM_REENTRY_COPY: Record<StoryWorkspaceDreamReentryItem['lifecycle'], string> = {
  generating: 'Dream Agent 正在创作',
  waiting_confirmation: '等待你修改并确认',
  continuing: 'Dream Agent 正在继续',
  recent: '最近完成本轮输出',
};

function StoryWorkspaceDreamReentryList({
  runs,
  onNavigate,
}: {
  runs: readonly StoryWorkspaceDreamReentryItem[];
  onNavigate?: (path: string) => void;
}) {
  const inProgress = runs.filter((run) => run.group === 'in_progress');
  const recent = runs.filter((run) => run.group === 'recent');
  const renderRun = (run: StoryWorkspaceDreamReentryItem) => (
    <button
      className="story-workspace-dream-reentry__item"
      key={run.storyWorkspaceRunId}
      onClick={() => onNavigate?.(run.href)}
      type="button"
    >
      <span className="story-workspace-dream-reentry__item-copy">
        <strong>{run.goalPrefix}</strong>
        <small>{run.deckDisplayName} · {STORY_WORKSPACE_DREAM_REENTRY_COPY[run.lifecycle]} · {run.deckPluginVersion} · Run …{run.storyWorkspaceRunId.slice(-6)}</small>
      </span>
      <span aria-hidden="true">打开</span>
    </button>
  );

  return (
    <section className="story-workspace-dream-reentry" aria-label="可恢复的 Dream">
      {inProgress.length > 0 && (
        <div className="story-workspace-dream-reentry__group">
          <h2>进行中的 Dream</h2>
          <div>{inProgress.map(renderRun)}</div>
        </div>
      )}
      {recent.length > 0 && (
        <div className="story-workspace-dream-reentry__group">
          <h2>最近的 Dream</h2>
          <div>{recent.map(renderRun)}</div>
        </div>
      )}
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
  const [goal, setGoal] = useState('');
  const [isLoadingDecks, setIsLoadingDecks] = useState(true);
  const [deckError, setDeckError] = useState<Error | null>(null);
  const launch = useStoryWorkspaceDreamLaunch();
  const reentry = useStoryWorkspaceDreamRuns();

  useEffect(() => {
    let active = true;
    setIsLoadingDecks(true);
    void listDecks().then((availableDecks) => {
      if (!active) return;
      const enabledDecks = availableDecks.filter((deck) => deck.enabled);
      setDecks(enabledDecks);
      setSelectedDeckId((current) => (
        enabledDecks.some((deck) => deck.id === current)
          ? current
          : enabledDecks.some((deck) => deck.id === initialDeckId)
            ? initialDeckId ?? ''
            : enabledDecks[0]?.id ?? ''
      ));
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
  const canStart = Boolean(selectedDeckId && goal.trim() && !launch.isLaunching);
  const visibleError = deckError ?? launch.error;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canStart) return;
    void launch.start(selectedDeckId, goal).then((accepted) => {
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
        <span>选择 Deck 和创作目标。Dream 会逐步写入人物、场景与分镜。</span>
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
              <span>Deck</span>
              <select
                aria-busy={isLoadingDecks}
                disabled={isLoadingDecks || launch.isLaunching}
                onChange={(event) => setSelectedDeckId(event.currentTarget.value)}
                value={selectedDeckId}
              >
                {decks.length === 0 && (
                  <option value="">{isLoadingDecks ? '正在读取 Deck…' : '没有可用的 Deck'}</option>
                )}
                {decks.map((deck) => (
                  <option key={deck.id} value={deck.id}>{deckDisplayName(deck)}</option>
                ))}
              </select>
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

            {selectedDeck && (
              <p className="story-workspace-dream-launch__selection">
                <span>当前 Deck</span>
                <strong>{deckDisplayName(selectedDeck)}</strong>
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
