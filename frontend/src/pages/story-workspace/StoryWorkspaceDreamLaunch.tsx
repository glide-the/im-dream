// [Input] Enabled Decks, one creation goal, and the dedicated Dream start hook.
// [Output] Dream-only launch form that navigates to the accepted run projection.
// [Pos] Story Workspace Dream no-run surface (Task 3 U4)

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { listDecks, type Deck } from '../../api/voiceApi';
import {
  storyWorkspaceDreamRunPath,
  useStoryWorkspaceDreamLaunch,
} from '../../hooks/story-workspace';

export interface StoryWorkspaceDreamLaunchProps {
  onNavigate?: (path: string) => void;
}

function deckDisplayName(deck: Deck): string {
  return deck.name_zh?.trim() || deck.name?.trim() || deck.name_en?.trim() || deck.id;
}

export function StoryWorkspaceDreamLaunch({
  onNavigate,
}: StoryWorkspaceDreamLaunchProps) {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState('');
  const [goal, setGoal] = useState('');
  const [isLoadingDecks, setIsLoadingDecks] = useState(true);
  const [deckError, setDeckError] = useState<Error | null>(null);
  const launch = useStoryWorkspaceDreamLaunch();

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
  }, []);

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
        <span>选择创作所使用的 Deck，描述目标。Agent 会在独立工作空间中产出人物、场景与分镜，并逐步同步到 Dream 页面。</span>
      </header>

      <div className="story-workspace-dream-launch__sheet">
        <aside className="story-workspace-dream-launch__guide" aria-label="Dream 页面生命周期">
          <p>Creation flow</p>
          <h2>从目标到可编辑稿件</h2>
          <ol>
            <li><span>01</span><strong>Agent 产出</strong><small>在绑定的工作空间编写创作文件</small></li>
            <li><span>02</span><strong>页面渲染</strong><small>人物、场景与分镜按阶段出现</small></li>
            <li><span>03</span><strong>审阅确认</strong><small>修改页面内容后统一确认一次</small></li>
            <li><span>04</span><strong>后续执行</strong><small>同一 Agent 接续完成创作</small></li>
          </ol>
        </aside>

        <form className="story-workspace-dream-launch__form" onSubmit={handleSubmit}>
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

          <button
            aria-busy={launch.isLaunching}
            className="story-workspace-dream-launch__submit"
            disabled={!canStart}
            type="submit"
          >发起 Dream</button>
        </form>
      </div>
    </section>
  );
}
