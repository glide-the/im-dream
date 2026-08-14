// [Input] Optional run deep link plus the dedicated Dream launch module.
// [Output] Workspace-file-driven Dream editor or the no-run Dream start surface.
// [Pos] Canonical /story-workspace/dream business page (Task 3 F4)
// [Sync] 2026-08-04: implement Agent files -> render -> edit/one confirm -> continue.
// [Sync] 2026-08-13: hand the bound Dream thread to canonical Chat on request.

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  storyWorkspaceAcceptDreamConfirmation,
  storyWorkspaceBeginDreamConfirmation,
  storyWorkspaceCanConfirmDream,
  storyWorkspaceCreateDreamState,
  storyWorkspaceEditDreamField,
  storyWorkspaceHydrateDreamState,
  storyWorkspaceReadDreamField,
  storyWorkspaceResetDreamField,
  storyWorkspaceResolveDreamRevisionConflict,
  STORY_WORKSPACE_DREAM_STAGES,
  type StoryWorkspaceDreamState,
} from '../../components/story-workspace/dreamState';
import {
  storyWorkspaceNewDreamConfirmationIdempotencyKey,
  useStoryWorkspaceDreamConfirmation,
  useStoryWorkspaceDreamFiles,
  type StoryWorkspaceDreamFieldValue,
  type StoryWorkspaceDreamStage,
} from '../../hooks/story-workspace';
import {
  STORY_WORKSPACE_DREAM_AGENT_PANEL_ID,
  StoryWorkspaceDreamAgentPanel,
} from '../../components/story-workspace/dream/StoryWorkspaceDreamAgentPanel';
import { StoryWorkspaceDreamAgentRail } from '../../components/story-workspace/dream/StoryWorkspaceDreamAgentRail';
import { useWorkflowRun } from '../../hooks/useWorkflowRun';
import type { WorkflowRun } from '../../api/storyWorkspaceApi';
import {
  storyWorkspaceDreamStageSnapshotsFromFiles,
  storyWorkspaceDreamAgentActivityNotice,
  storyWorkspaceParseDreamEditorValue,
  storyWorkspaceDreamEditorValue,
  storyWorkspaceDreamLifecycleFromPersistence,
  storyWorkspaceDreamPersistenceNotice,
  storyWorkspaceDreamRunFailureNotice,
} from './dreamViewModel';
import { StoryWorkspaceDreamLaunch } from './StoryWorkspaceDreamLaunch';
import {
  storyWorkspaceDreamIsPlainPrimaryActivation,
  storyWorkspaceDreamShouldReturnToHistory,
} from './storyWorkspaceDreamNavigation';
import './StoryWorkspaceDreamPage.css';

const STAGE_LABELS: Record<StoryWorkspaceDreamStage, {
  label: string;
  eyebrow: string;
  empty: string;
}> = {
  characters: { label: '人物', eyebrow: 'Assets · Characters', empty: '等待 Agent 写入人物文件' },
  scenes: { label: '场景', eyebrow: 'Assets · Scenes', empty: '等待 Agent 写入场景文件' },
  storyboards: { label: '分镜', eyebrow: 'Outline · Storyboards', empty: '等待 Agent 写入分镜文件' },
};

type DreamSelection = { stage: StoryWorkspaceDreamStage; entityId: string };
type DreamRightSection = 'content' | 'agent';

export interface StoryWorkspaceDreamPageProps {
  initialDeckId?: string | null;
  initialStage?: StoryWorkspaceDreamStage;
  runId?: string | null;
  /** Router-resolved, actor-scoped run context; Dream files remain stage truth. */
  resolvedRun?: Pick<WorkflowRun, 'workflow_run_id' | 'deck_plugin_display_name' | 'deck_plugin_version' | 'workflow_summary' | 'deck_runtime_snapshot_id' | 'runtime_plugin_lock_id'> | null;
  onNavigate?: (path: string) => void;
  onOpenChatThread: (threadId: string) => void;
}

function selectionExists(
  selection: DreamSelection | null,
  state: StoryWorkspaceDreamState | null,
): boolean {
  if (!selection || !state) return false;
  return Boolean(state.stageData[selection.stage]?.items.some(
    (item) => item.entityId === selection.entityId,
  ));
}

function draftIsValid(
  state: StoryWorkspaceDreamState | null,
  files: ReturnType<typeof useStoryWorkspaceDreamFiles>['data'],
): boolean {
  if (!state || !files) return false;
  return STORY_WORKSPACE_DREAM_STAGES.every((stage) => {
    const projected = files.stages[stage];
    const hydrated = state.stageData[stage];
    if (!projected || !hydrated) return false;
    const hydratedIds = new Set(hydrated.items.map((item) => item.entityId));
    return projected.items.every((item) => {
      if (!hydratedIds.has(item.entityId)) return false;
      const displayName = storyWorkspaceReadDreamField(
        state,
        stage,
        item.entityId,
        'displayName',
      );
      return typeof displayName === 'string' && displayName.trim().length > 0;
    });
  });
}

function revisionLine(state: StoryWorkspaceDreamState | null): string {
  if (!state) return '人物 — / 场景 — / 分镜 —';
  return STORY_WORKSPACE_DREAM_STAGES.map((stage) => (
    `${STAGE_LABELS[stage].label} r${state.latestRevisions[stage] ?? '—'}`
  )).join(' / ');
}

/** L3 rail copy combines the user-selected stage with file-derived revisions only. */
function storyWorkspaceDreamAgentStageLine(
  activeStage: StoryWorkspaceDreamStage,
  revisions: string,
): string {
  return `当前：${STAGE_LABELS[activeStage].label} · ${revisions}`;
}

export function StoryWorkspaceDreamPage({
  initialDeckId,
  initialStage = 'characters',
  runId,
  resolvedRun = null,
  onNavigate,
  onOpenChatThread,
}: StoryWorkspaceDreamPageProps) {
  const [dreamState, setDreamState] = useState<StoryWorkspaceDreamState | null>(null);
  const [activeStage, setActiveStage] = useState<StoryWorkspaceDreamStage>(initialStage);
  const [selection, setSelection] = useState<DreamSelection | null>(null);
  const [editorError, setEditorError] = useState<string | null>(null);
  const [rightSection, setRightSection] = useState<DreamRightSection>('content');
  const [threadSessionRefreshNonce, setThreadSessionRefreshNonce] = useState(0);
  const [expectedConfirmationMessageId, setExpectedConfirmationMessageId] = useState<string | null>(null);
  const agentPanelOpen = rightSection === 'agent';
  const mastheadAgentTriggerRef = useRef<HTMLButtonElement>(null);

  const draftLifecycleState = dreamState?.status ?? 'story-workspace-dream-waiting-files';
  const files = useStoryWorkspaceDreamFiles(runId, {
    lifecycleState: draftLifecycleState,
  });
  const confirmation = useStoryWorkspaceDreamConfirmation(runId ?? '');
  const refreshDreamFiles = files.refresh;
  const {
    run: workflowRun,
    error: workflowRunError,
    refreshRun,
    selectRun,
  } = useWorkflowRun({ eventsEnabled: Boolean(runId) });
  const currentWorkflowRun = workflowRun?.workflow_run_id === runId ? workflowRun : null;
  const agentContextRun = resolvedRun?.workflow_run_id === runId ? resolvedRun : currentWorkflowRun;
  const runFailureNotice = storyWorkspaceDreamRunFailureNotice(currentWorkflowRun);

  const confirmationPersistence = useMemo(() => ({
    confirmationAccepted: Boolean(
      files.data?.confirmationAccepted || confirmation.accepted,
    ),
    confirmationDispatched: Boolean(
      files.data?.confirmationDispatched || confirmation.accepted?.dispatched,
    ),
  }), [confirmation.accepted, files.data?.confirmationAccepted, files.data?.confirmationDispatched]);
  const lifecycleState = storyWorkspaceDreamLifecycleFromPersistence(
    confirmationPersistence,
    currentWorkflowRun?.status,
    draftLifecycleState,
  );
  const isReadOnly = lifecycleState === 'story-workspace-dream-running'
    || lifecycleState === 'story-workspace-dream-completed'
    || Boolean(runFailureNotice);
  const observerActivityCopy = storyWorkspaceDreamAgentActivityNotice(
    files.data?.agentActivity,
  );
  const activityCopy = runFailureNotice ?? (lifecycleState === 'story-workspace-dream-completed'
    ? storyWorkspaceDreamPersistenceNotice(confirmationPersistence, 'completed')
    : lifecycleState === 'story-workspace-dream-running'
      ? storyWorkspaceDreamPersistenceNotice(confirmationPersistence, 'running')
      : observerActivityCopy ?? '读取 Agent 工作空间');

  useEffect(() => {
    setDreamState(null);
    setSelection(null);
    setActiveStage(initialStage);
    setEditorError(null);
    setRightSection('content');
    setThreadSessionRefreshNonce(0);
    setExpectedConfirmationMessageId(null);
  }, [initialStage, runId]);

  useEffect(() => {
    if (!runId) return;
    void selectRun(runId).catch(() => {
      // Dream files remain authoritative for confirmation; run read is only
      // used for title/completion observation and never creates a failure UI.
    });
  }, [runId, selectRun]);

  useEffect(() => {
    const data = files.data;
    if (!runId || !data) return;
    const snapshots = storyWorkspaceDreamStageSnapshotsFromFiles(data);
    setDreamState((current) => {
      const base = current
        && current.storyWorkspaceRunId === data.storyWorkspaceRunId
        && current.threadId === data.threadId
        ? current
        : storyWorkspaceCreateDreamState({
          storyWorkspaceRunId: data.storyWorkspaceRunId,
          threadId: data.threadId,
        });
      return storyWorkspaceHydrateDreamState(base, snapshots);
    });
  }, [files.data, runId]);

  useEffect(() => {
    if (!dreamState) return;
    if (selectionExists(selection, dreamState)) return;
    const preferred = dreamState.stageData[activeStage]?.items[0];
    if (preferred) {
      setSelection({ stage: activeStage, entityId: preferred.entityId });
      return;
    }
    if (initialStage === activeStage) {
      setSelection(null);
      return;
    }
    const firstStage = STORY_WORKSPACE_DREAM_STAGES.find(
      (stage) => (dreamState.stageData[stage]?.items.length ?? 0) > 0,
    );
    const first = firstStage ? dreamState.stageData[firstStage]?.items[0] : null;
    setSelection(firstStage && first
      ? { stage: firstStage, entityId: first.entityId }
      : null);
    if (firstStage) setActiveStage(firstStage);
  }, [activeStage, dreamState, initialStage, selection]);

  useEffect(() => {
    const warnBeforeLeave = (event: BeforeUnloadEvent) => {
      if (!dreamState?.dirtyCount) return;
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warnBeforeLeave);
    return () => window.removeEventListener('beforeunload', warnBeforeLeave);
  }, [dreamState?.dirtyCount]);

  const selectedFileItem = useMemo(() => {
    if (!selection || !files.data) return null;
    return files.data.stages[selection.stage]?.items.find(
      (item) => item.entityId === selection.entityId,
    ) ?? null;
  }, [files.data, selection]);

  const activeItems = dreamState?.stageData[activeStage]?.items ?? [];
  const updateField = useCallback((
    field: 'displayName' | 'summary' | 'relations',
    rawValue: string,
  ) => {
    if (!dreamState || !selection) return;
    try {
      const value: StoryWorkspaceDreamFieldValue = field === 'relations'
        ? storyWorkspaceParseDreamEditorValue(field, rawValue)
        : field === 'summary' && rawValue === '' ? null : rawValue;
      setDreamState(storyWorkspaceEditDreamField(
        dreamState,
        selection.stage,
        selection.entityId,
        field,
        value,
      ));
      setEditorError(null);
    } catch (reason) {
      setEditorError(reason instanceof Error ? reason.message : '字段内容无效');
    }
  }, [dreamState, selection]);

  const normalizeField = useCallback((field: 'displayName' | 'summary') => {
    if (!dreamState || !selection) return;
    try {
      const current = storyWorkspaceReadDreamField(
        dreamState,
        selection.stage,
        selection.entityId,
        field,
      );
      const normalized = storyWorkspaceParseDreamEditorValue(
        field,
        storyWorkspaceDreamEditorValue(current),
      );
      setDreamState(storyWorkspaceEditDreamField(
        dreamState,
        selection.stage,
        selection.entityId,
        field,
        normalized,
      ));
      setEditorError(null);
    } catch (reason) {
      setEditorError(reason instanceof Error ? reason.message : '字段内容无效');
    }
  }, [dreamState, selection]);

  const confirmAndContinue = useCallback(async () => {
    if (!runId || !dreamState) return;
    const previous = dreamState;
    try {
      const started = storyWorkspaceBeginDreamConfirmation(
        dreamState,
        storyWorkspaceNewDreamConfirmationIdempotencyKey(),
      );
      setDreamState(started.state);
      const accepted = await confirmation.submit(started.command);
      setExpectedConfirmationMessageId(accepted.messageId);
      setThreadSessionRefreshNonce((value) => value + 1);
      setDreamState((current) => (
        current ? storyWorkspaceAcceptDreamConfirmation(current) : current
      ));
      refreshDreamFiles();
      setEditorError(null);
      onNavigate?.(
        `/story-workspace/runs/${encodeURIComponent(runId)}/execution`,
      );
    } catch (reason) {
      setDreamState(previous);
      setEditorError(reason instanceof Error ? reason.message : '确认命令未提交');
    }
  }, [confirmation, dreamState, onNavigate, refreshDreamFiles, runId]);

  if (!runId) {
    if (initialDeckId) {
      return <StoryWorkspaceDreamLaunch initialDeckId={initialDeckId} onNavigate={onNavigate} />;
    }
    return <StoryWorkspaceDreamLaunch onNavigate={onNavigate} />;
  }

  const canConfirm = Boolean(
    dreamState
    && files.data?.canConfirm
    && draftIsValid(dreamState, files.data)
    && storyWorkspaceCanConfirmDream(dreamState)
    && confirmation.status !== 'confirming'
    && !runFailureNotice
  );
  const deckName = agentContextRun?.deck_plugin_display_name ?? '当前 Deck';
  const agentRuntimeLockId = agentContextRun?.runtime_plugin_lock_id
    ?? files.data?.source.runtimePluginLockId
    ?? null;
  const agentRuntimeSnapshotId = agentContextRun?.deck_runtime_snapshot_id
    ?? files.data?.source.deckRuntimeSnapshotId
    ?? null;
  const agentStageLine = storyWorkspaceDreamAgentStageLine(activeStage, revisionLine(dreamState));
  const threadId = files.data?.threadId ?? null;
  const agentPreview = threadId ? `打开同一 Agent 会话 · ${activityCopy}` : activityCopy;
  const openDreamAgent = () => {
    setRightSection('agent');
  };
  const showDreamContent = (nextSelection: DreamSelection | null) => {
    setSelection(nextSelection);
    setRightSection('content');
  };
  return (
    <section
      className="story-workspace-dream"
      aria-labelledby="story-workspace-dream-title"
      data-lifecycle={lifecycleState}
    >
      <header className="story-workspace-dream__masthead">
        <div>
          <a
            className="story-workspace-dream__return"
            href="/story-workspace/dream"
            onClick={(event) => {
              if (!storyWorkspaceDreamIsPlainPrimaryActivation(event)) return;
              if (
                storyWorkspaceDreamShouldReturnToHistory(window.history.state)
                && window.history.length > 1
              ) {
                event.preventDefault();
                window.history.back();
                return;
              }
              if (!onNavigate) return;
              event.preventDefault();
              onNavigate('/story-workspace/dream');
            }}
          >← 返回上一页</a>
          <p className="story-workspace-dream__folio">Dream manuscript · {runId.slice(-6)}</p>
          <h1 id="story-workspace-dream-title">创作工作空间</h1>
        </div>
        <button
          aria-controls={STORY_WORKSPACE_DREAM_AGENT_PANEL_ID}
          aria-expanded={agentPanelOpen}
          aria-label="打开 Dream Agent 消息"
          className="story-workspace-dream__activity"
          onClick={openDreamAgent}
          ref={mastheadAgentTriggerRef}
          type="button"
        >
          <span className="story-workspace-dream__activity-mark" />
          <span className="story-workspace-dream__activity-copy">{agentPreview}</span>
        </button>
      </header>

      {runFailureNotice ? (
        <div className="story-workspace-dream__run-alert" role="alert">
          <strong>Dream 运行失败</strong>
          <p>{runFailureNotice}</p>
          <div>
            <button onClick={() => { void refreshRun().catch(() => undefined); }} type="button">重新读取运行状态</button>
            <a href="/story-workspace/dream">返回 Dream 重新开始</a>
          </div>
        </div>
      ) : workflowRunError && !currentWorkflowRun ? (
        <div className="story-workspace-dream__run-alert" role="alert">
          <strong>暂时无法读取运行状态</strong>
          <p>页面不会根据本地界面推断工作流结果。</p>
          <button onClick={() => { void selectRun(runId).catch(() => undefined); }} type="button">重新读取运行状态</button>
        </div>
      ) : null}

      {agentPanelOpen && (
        <div className="story-workspace-dream__mobile-agent">
          <StoryWorkspaceDreamAgentRail
            deckName={deckName}
            runId={runId}
            runtimeLockId={agentRuntimeLockId}
            runtimeSnapshotId={agentRuntimeSnapshotId}
            stageLine={agentStageLine}
            threadId={threadId}
            onOpenChatThread={onOpenChatThread}
          />
        </div>
      )}

      <nav className="story-workspace-dream__spine" aria-label="Dream 文件模块">
        {STORY_WORKSPACE_DREAM_STAGES.map((stage, index) => {
          const revision = dreamState?.latestRevisions[stage];
          const dirty = dreamState?.localEdits.some((edit) => edit.stage === stage);
          return (
            <button
              aria-current={activeStage === stage ? 'page' : undefined}
              className="story-workspace-dream__stage"
              data-arrived={revision !== undefined || undefined}
              data-dirty={dirty || undefined}
              disabled={revision === undefined}
              key={stage}
              onClick={() => {
                setActiveStage(stage);
                const first = dreamState?.stageData[stage]?.items[0];
                showDreamContent(first ? { stage, entityId: first.entityId } : null);
              }}
              type="button"
            >
              <span className="story-workspace-dream__stage-index">0{index + 1}</span>
              <span>{STAGE_LABELS[stage].label}</span>
              <small>{revision ? `r${revision}` : '等待写入'}</small>
            </button>
          );
        })}
      </nav>

      <div
        className="story-workspace-dream__body"
        data-agent-open={agentPanelOpen || undefined}
      >
        <main className="story-workspace-dream__manuscript">
          <header className="story-workspace-dream__section-heading">
            <div>
              <p>{STAGE_LABELS[activeStage].eyebrow}</p>
              <h2>{STAGE_LABELS[activeStage].label}</h2>
            </div>
            <span>{activeItems.length} 项 · {dreamState?.dirtyCount ?? 0} 处修改</span>
          </header>

          {files.isLoading && !dreamState && (
            <p className="story-workspace-dream__empty">正在读取工作空间…</p>
          )}
          {files.error && !dreamState && (
            <div className="story-workspace-dream__empty" role="status">
              <p>暂时无法读取工作空间。</p>
              <button onClick={files.refresh} type="button">重新读取</button>
            </div>
          )}
          {activeItems.length === 0 && (
            <div className="story-workspace-dream__empty" role="status">
              <span className="story-workspace-dream__waiting-line" />
              <p>{STAGE_LABELS[activeStage].empty}</p>
              <small>页面会在受控 stage 文件完成后自动刷新。</small>
            </div>
          )}

          <ol className="story-workspace-dream__rows">
            {activeItems.map((item, index) => {
              const displayName = dreamState
                ? storyWorkspaceReadDreamField(dreamState, activeStage, item.entityId, 'displayName')
                : '';
              const summary = dreamState
                ? storyWorkspaceReadDreamField(dreamState, activeStage, item.entityId, 'summary')
                : null;
              const selected = selection?.stage === activeStage && selection.entityId === item.entityId;
              const dirty = dreamState?.localEdits.some(
                (edit) => edit.stage === activeStage && edit.entityId === item.entityId,
              );
              return (
                <li key={item.entityId}>
                  <button
                    aria-current={selected && rightSection === 'content' || undefined}
                    data-dirty={dirty || undefined}
                    onClick={() => showDreamContent({ stage: activeStage, entityId: item.entityId })}
                    type="button"
                  >
                    <span className="story-workspace-dream__row-index">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="story-workspace-dream__row-copy">
                      <strong>{storyWorkspaceDreamEditorValue(displayName)}</strong>
                      <small>{storyWorkspaceDreamEditorValue(summary) || '暂无摘要'}</small>
                    </span>
                    <span className="story-workspace-dream__row-arrow">→</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </main>

        <aside
          aria-label="Dream 内容编辑器"
          className="story-workspace-dream__editor"
          data-agent-open={agentPanelOpen || undefined}
        >
          {agentPanelOpen && (
            <StoryWorkspaceDreamAgentRail
              deckName={deckName}
              runId={runId}
              runtimeLockId={agentRuntimeLockId}
              runtimeSnapshotId={agentRuntimeSnapshotId}
              stageLine={agentStageLine}
              threadId={threadId}
              onOpenChatThread={onOpenChatThread}
            />
          )}
          <div className="story-workspace-dream__agent-panel">
            <StoryWorkspaceDreamAgentPanel
              expectedMessageId={expectedConfirmationMessageId}
              isOpen={agentPanelOpen}
              onClose={() => setRightSection('content')}
              onSettled={() => {
                const settledMessageId = expectedConfirmationMessageId;
                if (settledMessageId !== null) {
                  setExpectedConfirmationMessageId((current) => (
                    current === settledMessageId ? null : current
                  ));
                }
                refreshDreamFiles();
                void selectRun(runId).catch(() => undefined);
              }}
              refreshNonce={threadSessionRefreshNonce}
              restoreFocusRef={mastheadAgentTriggerRef}
              threadId={threadId}
            />
          </div>
          {!agentPanelOpen && (selection && dreamState && selectedFileItem ? (
            <>
              <header>
                <p>{STAGE_LABELS[selection.stage].label} · r{dreamState.latestRevisions[selection.stage]}</p>
                <h2>修改当前内容</h2>
              </header>

              {dreamState.staleStages.includes(selection.stage) && (
                <div className="story-workspace-dream__conflict" role="status">
                  <p>工作空间有新版本，请选择如何合并本地修改。</p>
                  <div>
                    <button onClick={() => setDreamState(storyWorkspaceResolveDreamRevisionConflict(
                      dreamState, selection.stage, 'keep-local',
                    ))} type="button">保留我的修改</button>
                    <button onClick={() => setDreamState(storyWorkspaceResolveDreamRevisionConflict(
                      dreamState, selection.stage, 'accept-server',
                    ))} type="button">使用工作空间版本</button>
                  </div>
                </div>
              )}

              <div className="story-workspace-dream__editor-fields">
                <label>
                  <span>名称</span>
                  <input
                    disabled={isReadOnly}
                    onBlur={() => normalizeField('displayName')}
                    onChange={(event) => updateField('displayName', event.currentTarget.value)}
                    value={storyWorkspaceDreamEditorValue(storyWorkspaceReadDreamField(
                      dreamState, selection.stage, selection.entityId, 'displayName',
                    ))}
                  />
                </label>
                <label>
                  <span>摘要</span>
                  <textarea
                    disabled={isReadOnly}
                    onBlur={() => normalizeField('summary')}
                    onChange={(event) => updateField('summary', event.currentTarget.value)}
                    rows={7}
                    value={storyWorkspaceDreamEditorValue(storyWorkspaceReadDreamField(
                      dreamState, selection.stage, selection.entityId, 'summary',
                    ))}
                  />
                </label>
                <label>
                  <span>关联项</span>
                  <input
                    disabled={isReadOnly}
                    onChange={(event) => updateField('relations', event.currentTarget.value)}
                    placeholder="用逗号分隔"
                    value={storyWorkspaceDreamEditorValue(storyWorkspaceReadDreamField(
                      dreamState, selection.stage, selection.entityId, 'relations',
                    ))}
                  />
                </label>
              </div>

              <div className="story-workspace-dream__editor-footer">
                <dl className="story-workspace-dream__source">
                  <div><dt>来源文件</dt><dd>{selectedFileItem.sourceFile}</dd></div>
                  <div><dt>实体 ID</dt><dd>{selection.entityId}</dd></div>
                </dl>

                {!isReadOnly && (
                  <button
                    className="story-workspace-dream__reset"
                    onClick={() => {
                      let next = dreamState;
                      for (const field of ['displayName', 'summary', 'relations'] as const) {
                        next = storyWorkspaceResetDreamField(
                          next, selection.stage, selection.entityId, field,
                        );
                      }
                      setDreamState(next);
                      setEditorError(null);
                    }}
                    type="button"
                  >撤销本项修改</button>
                )}
              </div>
            </>
          ) : (
            <div className="story-workspace-dream__editor-empty">
              <p>选择一项内容</p>
              <span>人物、场景或分镜文件到达后，可在这里修改允许字段。</span>
            </div>
          ))}
        </aside>
      </div>

      {!agentPanelOpen && (
        <footer className="story-workspace-dream__confirmation">
          <div>
            <strong>{dreamState?.dirtyCount ?? 0} 处本地修改</strong>
            <span>{revisionLine(dreamState)}</span>
            {editorError && <em role="status">{editorError}</em>}
          </div>
          {isReadOnly ? (
            <div className="story-workspace-dream__running-actions">
              <span>{activityCopy}</span>
              {confirmationPersistence.confirmationDispatched && (
                <button
                  onClick={() => onNavigate?.(`/story-workspace/runs/${encodeURIComponent(runId)}/execution`)}
                  type="button"
                >查看后续执行</button>
              )}
            </div>
          ) : (
            <button
              className="story-workspace-dream__confirm"
              disabled={!canConfirm}
              onClick={() => void confirmAndContinue()}
              type="button"
            >
              {confirmation.status === 'confirming' ? '正在确认…' : '确认并继续'}
            </button>
          )}
        </footer>
      )}
    </section>
  );
}
