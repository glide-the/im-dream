// [Input] Confirmed run identity plus authoritative `.dream` file projections.
// [Output] Assets / Outline collaboration surface and in-place focus context.
// [Pos] /story-workspace/runs/:storyWorkspaceRunId/execution (Task 3 F5)
// [Sync] 2026-08-04: replace legacy status/guidance UI with file-driven collaboration.

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type KeyboardEvent,
} from 'react';
import { storyWorkspaceReviewDeepLink } from '../../components/story-workspace';
import { useStoryWorkspaceDreamFiles } from '../../hooks/story-workspace';
import { useWorkflowRun } from '../../hooks/useWorkflowRun';
import {
  buildStoryWorkspaceExecutionWorkspace,
  canAccessStoryWorkspaceExecution,
  storyWorkspaceExecutionFocusNeighbors,
  type StoryWorkspaceExecutionEntry,
} from './executionViewModel';
import './StoryWorkspaceExecutionPage.css';

type ExecutionModule = 'assets' | 'outline';

const MODULE_COPY: Record<ExecutionModule, { label: string; description: string }> = {
  assets: { label: 'Assets', description: '人物与场景' },
  outline: { label: 'Outline', description: '故事线与叙事点' },
};

export interface StoryWorkspaceExecutionPageProps {
  runId: string;
  episodeId?: string | null;
  onNavigate?: (href: string, notice?: string) => void;
}

function focusListItem(
  event: KeyboardEvent<HTMLButtonElement>,
  index: number,
  itemCount: number,
) {
  if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
  event.preventDefault();
  const nextIndex = event.key === 'ArrowDown'
    ? Math.min(index + 1, itemCount - 1)
    : Math.max(index - 1, 0);
  const list = event.currentTarget.closest('ol');
  list?.querySelectorAll<HTMLButtonElement>(':scope > li > button')[nextIndex]?.focus();
}

function WorkspaceIndexList({
  entries,
  focusKey,
  onFocus,
}: {
  entries: readonly StoryWorkspaceExecutionEntry[];
  focusKey: string | null;
  onFocus: (key: string) => void;
}) {
  return (
    <ol className="story-workspace-collaboration__index-list">
      {entries.map((entry, index) => (
        <li key={entry.key}>
          <button
            aria-current={focusKey === entry.key || undefined}
            onClick={() => onFocus(entry.key)}
            onKeyDown={(event) => focusListItem(event, index, entries.length)}
            type="button"
          >
            <span>{String(index + 1).padStart(2, '0')}</span>
            <span>
              <strong>{entry.title}</strong>
              <small>{entry.summary || entry.sourceFile}</small>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function EmptyWorkspaceModule({ module }: { module: ExecutionModule }) {
  return (
    <div className="story-workspace-collaboration__empty" role="status">
      <span aria-hidden="true" />
      <p>等待 Agent 写入 {MODULE_COPY[module].label}</p>
      <small>页面会沿用最近一次有效内容，并持续读取工作空间。</small>
    </div>
  );
}

export function StoryWorkspaceExecutionPage({
  runId,
  episodeId,
  onNavigate,
}: StoryWorkspaceExecutionPageProps) {
  const [activeModule, setActiveModule] = useState<ExecutionModule>('outline');
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const { run, selectRun } = useWorkflowRun({ eventsEnabled: true });
  const currentRun = run?.workflow_run_id === runId ? run : null;

  const navigate = useCallback((href: string, notice?: string) => {
    if (onNavigate) {
      onNavigate(href, notice);
    } else if (typeof window !== 'undefined') {
      window.location.assign(href);
    }
  }, [onNavigate]);

  useEffect(() => {
    void selectRun(runId).catch(() => {
      // Dream files own the access fact. A run read is optional context for
      // the title/completion indicator and never creates a failure branch.
    });
  }, [runId, selectRun]);

  const files = useStoryWorkspaceDreamFiles(runId, {
    lifecycleState: currentRun?.status === 'completed'
      ? 'story-workspace-dream-completed'
      : 'story-workspace-dream-continuing',
  });

  const workspace = useMemo(
    () => files.data ? buildStoryWorkspaceExecutionWorkspace(files.data) : null,
    [files.data],
  );
  const visibleEntries = activeModule === 'assets'
    ? workspace?.assets ?? []
    : workspace?.outline ?? [];
  const allEntries = useMemo(
    () => [...(workspace?.assets ?? []), ...(workspace?.outline ?? [])],
    [workspace],
  );
  const focusedEntry = focusKey
    ? allEntries.find((entry) => entry.key === focusKey) ?? null
    : null;
  const focusNeighbors = useMemo(() => {
    const focusEntries = focusedEntry?.module === 'Assets'
      ? workspace?.assets ?? []
      : workspace?.outline ?? [];
    return storyWorkspaceExecutionFocusNeighbors(focusEntries, focusKey ?? '');
  }, [focusKey, focusedEntry?.module, workspace?.assets, workspace?.outline]);

  useEffect(() => {
    setActiveModule('outline');
    setFocusKey(null);
  }, [runId]);

  useEffect(() => {
    if (!focusKey || allEntries.some((entry) => entry.key === focusKey)) return;
    setFocusKey(null);
  }, [allEntries, focusKey]);

  useEffect(() => {
    if (!focusedEntry) return;
    const closeFocus = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') setFocusKey(null);
    };
    window.addEventListener('keydown', closeFocus);
    return () => window.removeEventListener('keydown', closeFocus);
  }, [focusedEntry]);

  useEffect(() => {
    if (!files.data || canAccessStoryWorkspaceExecution(files.data)) return;
    navigate(
      storyWorkspaceReviewDeepLink(files.data.storyWorkspaceRunId, episodeId),
      '请先完成本次 Dream 的确认。',
    );
  }, [episodeId, files.data, navigate]);

  if (files.isLoading && !files.data) {
    return (
      <section className="story-workspace-collaboration story-workspace-collaboration--message">
        <p>正在读取 Agent 工作空间…</p>
      </section>
    );
  }

  if (files.data && !canAccessStoryWorkspaceExecution(files.data)) {
    return (
      <section className="story-workspace-collaboration story-workspace-collaboration--message">
        <p>正在返回 Dream 完成本次确认…</p>
      </section>
    );
  }

  if (!files.data && files.error) {
    return (
      <section className="story-workspace-collaboration story-workspace-collaboration--message">
        <p>工作空间内容尚未同步，页面会继续读取。</p>
        <a href={`/story-workspace/dream?run=${encodeURIComponent(runId)}`}>返回 Dream</a>
      </section>
    );
  }

  if (!files.data) {
    return (
      <section className="story-workspace-collaboration story-workspace-collaboration--message">
        <p>正在读取 Agent 工作空间…</p>
      </section>
    );
  }

  const agentStateCopy = !files.data.confirmationDispatched
    ? '命令已保存，等待同一 Agent 接续'
    : currentRun?.status === 'completed'
      ? '同一 Chat Agent 已完成后续执行'
      : '同一 Chat Agent 正在继续';
  const focusByKey = (key: string | null) => {
    if (key) setFocusKey(key);
  };

  return (
    <section
      aria-labelledby="story-workspace-collaboration-title"
      className="story-workspace-collaboration"
    >
      <header className="story-workspace-collaboration__masthead">
        <div>
          <nav aria-label="面包屑">
            <a
              href={`/story-workspace/dream?run=${encodeURIComponent(runId)}`}
              onClick={(event) => {
                if (!onNavigate) return;
                event.preventDefault();
                navigate(`/story-workspace/dream?run=${encodeURIComponent(runId)}`);
              }}
            >Dream</a>
            <span aria-hidden="true"> / </span>
            <span>后续执行</span>
          </nav>
          <h1 id="story-workspace-collaboration-title">
            {currentRun?.workflow_summary?.trim() || '故事协作工作台'}
          </h1>
        </div>
        <div className="story-workspace-collaboration__agent-state" aria-live="polite">
          <span aria-hidden="true" />
          <div>
            <strong>{agentStateCopy}</strong>
            <small>workspace r{workspace?.runRevision ?? 0}</small>
          </div>
        </div>
      </header>

      <div className="story-workspace-collaboration__surface">
        <aside className="story-workspace-collaboration__rail" aria-label="Assets 与 Outline 索引">
          <div className="story-workspace-collaboration__module-switch" role="tablist">
            {(Object.keys(MODULE_COPY) as ExecutionModule[]).map((module) => (
              <button
                aria-selected={activeModule === module}
                key={module}
                onClick={() => {
                  setActiveModule(module);
                  setFocusKey(null);
                }}
                role="tab"
                type="button"
              >
                <strong>{MODULE_COPY[module].label}</strong>
                <small>{MODULE_COPY[module].description}</small>
              </button>
            ))}
          </div>

          <div className="story-workspace-collaboration__rail-body">
            {activeModule === 'assets' ? (
              <>
                {(['characters', 'scenes'] as const).map((stage) => {
                  const entries = visibleEntries.filter((entry) => entry.stage === stage);
                  if (entries.length === 0) return null;
                  return (
                    <section key={stage}>
                      <header>
                        <span>{stage === 'characters' ? '人物' : '场景'}</span>
                        <small>r{entries[0]?.revision}</small>
                      </header>
                      <WorkspaceIndexList
                        entries={entries}
                        focusKey={focusKey}
                        onFocus={setFocusKey}
                      />
                    </section>
                  );
                })}
              </>
            ) : (
              <section>
                <header>
                  <span>故事线 01</span>
                  <small>{visibleEntries[0] ? `r${visibleEntries[0].revision}` : '等待'}</small>
                </header>
                <WorkspaceIndexList
                  entries={visibleEntries}
                  focusKey={focusKey}
                  onFocus={setFocusKey}
                />
              </section>
            )}
            {visibleEntries.length === 0 && <EmptyWorkspaceModule module={activeModule} />}
          </div>
        </aside>

        <main className="story-workspace-collaboration__main">
          {focusedEntry ? (
            <article className="story-workspace-collaboration__focus">
              <header className="story-workspace-collaboration__focus-nav">
                <button onClick={() => setFocusKey(null)} type="button">← 返回故事线</button>
                <div>
                  <button
                    disabled={!focusNeighbors.previousKey}
                    onClick={() => focusByKey(focusNeighbors.previousKey)}
                    type="button"
                  >上一条</button>
                  <button
                    disabled={!focusNeighbors.nextKey}
                    onClick={() => focusByKey(focusNeighbors.nextKey)}
                    type="button"
                  >下一条</button>
                </div>
              </header>

              <div className="story-workspace-collaboration__focus-title">
                <p>{focusedEntry.stageLabel} · r{focusedEntry.revision}</p>
                <h2>{focusedEntry.title}</h2>
                {focusedEntry.relations.length > 0 && (
                  <dl>
                    <dt>关联</dt>
                    <dd>{focusedEntry.relations.join('、')}</dd>
                  </dl>
                )}
              </div>

              <section className="story-workspace-collaboration__prose">
                <span>主要信息</span>
                <p>{focusedEntry.summary || 'Agent 尚未写入摘要。'}</p>
              </section>

              {focusedEntry.stage === 'storyboards' && (
                <section className="story-workspace-collaboration__shot-note">
                  <span>镜头说明</span>
                  <div>
                    <b>01</b>
                    <p>{focusedEntry.summary || '等待镜头说明写入工作空间。'}</p>
                  </div>
                </section>
              )}

              <section className="story-workspace-collaboration__history">
                <header>
                  <span>Agent 工作空间历史</span>
                  <small>来自受控 stage 文件</small>
                </header>
                <ol>
                  <li>
                    <span>当前条目写入 r{focusedEntry.revision}</span>
                    <code>{focusedEntry.sourceFile}</code>
                  </li>
                </ol>
              </section>
            </article>
          ) : (
            <div className="story-workspace-collaboration__overview">
              <header>
                <p>{MODULE_COPY[activeModule].label} · Narrative execution</p>
                <h2>{activeModule === 'assets' ? '故事资产' : '故事线与叙事点'}</h2>
                <span>
                  {activeModule === 'assets'
                    ? 'Agent 持续同步人物与场景；选择条目可查看聚焦上下文。'
                    : '选择一条分镜摘要，进入同一工作面内的聚焦协作层。'}
                </span>
              </header>

              {visibleEntries.length > 0 ? (
                <ol className="story-workspace-collaboration__manuscript">
                  {visibleEntries.map((entry, index) => (
                    <li key={entry.key}>
                      <button onClick={() => setFocusKey(entry.key)} type="button">
                        <span>{String(index + 1).padStart(2, '0')}</span>
                        <span>
                          <small>{entry.stageLabel} · r{entry.revision}</small>
                          <strong>{entry.title}</strong>
                          <p>{entry.summary || '等待 Agent 补充主要信息。'}</p>
                        </span>
                        <b aria-hidden="true">→</b>
                      </button>
                    </li>
                  ))}
                </ol>
              ) : (
                <EmptyWorkspaceModule module={activeModule} />
              )}

              <section className="story-workspace-collaboration__activity">
                <header>
                  <span>工作空间更新流</span>
                  <small>stage revisions</small>
                </header>
                <ol>
                  {(workspace?.activity ?? []).map((entry) => (
                    <li key={entry.key}>
                      <span aria-hidden="true" />
                      <div>
                        <strong>{entry.label}</strong>
                        <small>{entry.sourceCount} 个来源文件</small>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
