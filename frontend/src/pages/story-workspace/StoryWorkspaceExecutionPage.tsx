// [Input] Confirmed run identity, `.dream` projections, and authoritative Episode artifact surface.
// [Output] Revision-stable Episode workbench with the shared Dream Agent thread.
// [Pos] /story-workspace/runs/:storyWorkspaceRunId/execution (Task 3 U11)
// [Sync] 2026-08-06: compose Episode artifacts without changing their REST ownership.
// [Sync] 2026-08-13: describe an unbound EP01 as a pending artifact-association
//                    build, reserving trust language for server identity checks.
// [Sync] 2026-08-13: keep EP01 association state read-only; confirmed turns
//                    publish and bind automatically without a manual UI action.

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from 'react';
import {
  StoryWorkspaceStoryIndexStatus,
  storyWorkspaceReviewDeepLink,
  type StoryWorkspaceStoryIndexFileStatus,
} from '../../components/story-workspace';
import {
  StoryWorkspaceStoryIndexHttpError,
  useStoryWorkspaceDreamFiles,
  useStoryWorkspaceStoryIndex,
} from '../../hooks/story-workspace';
import type {
  StoryWorkspaceEpisodeAssociationCoverage,
  StoryWorkspaceEpisodeArtifactAvailability,
  StoryWorkspaceEpisodeArtifactSurface,
} from '../../hooks/story-workspace/contracts';
import { useStoryWorkspaceEpisodeArtifacts } from '../../hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts';
import { StoryWorkspaceDreamAgentDialog } from '../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog';
import { StoryWorkspaceEpisodeNarrativeWorkbench } from '../../components/story-workspace/episode/StoryWorkspaceEpisodeNarrativeWorkbench';
import {
  StoryWorkspaceEpisodeArtifactReader,
  storyWorkspaceEpisodeArtifactTabId,
  type StoryWorkspaceEpisodeReadableArtifact,
} from '../../components/story-workspace/episode/StoryWorkspaceEpisodeArtifactReader';
import {
  StoryWorkspaceEpisodeReviewPanel,
  type StoryWorkspaceEpisodeReviewLocateSelection,
} from '../../components/story-workspace/episode/StoryWorkspaceEpisodeReviewPanel';
import { StoryWorkspaceEpisodeShotAuxiliary } from '../../components/story-workspace/episode/StoryWorkspaceEpisodeShotAuxiliary';
import { useWorkflowRun } from '../../hooks/useWorkflowRun';
import {
  storyWorkspaceBuildEpisodeExecutionViewModel,
  storyWorkspaceEpisodeNavigationItems,
  storyWorkspaceEpisodeSelectionKey,
  storyWorkspaceReconcileEpisodeSelection,
  type StoryWorkspaceEpisodeExecutionViewModel,
  type StoryWorkspaceEpisodeSelection,
} from './episodeExecutionViewModel';
import {
  storyWorkspaceBuildExecutionWorkspace,
  storyWorkspaceCanAccessExecution,
  storyWorkspaceExecutionFocusNeighbors,
} from './executionViewModel';
import './StoryWorkspaceExecutionPage.css';
import './StoryWorkspaceDreamPage.css';

type ExecutionModule = 'assets' | 'outline';

const MODULE_COPY: Record<ExecutionModule, { label: string; description: string }> = {
  assets: { label: 'Assets', description: '人物与场景' },
  outline: { label: 'Outline', description: '故事线与叙事点' },
};

const EPISODE_ARTIFACT_LABELS: Readonly<Record<string, string>> = {
  'episode-outline.md': 'Episode Outline',
  'script.md': 'Script',
  'storyboard.yaml': 'Storyboard',
  'prompts/': 'Prompts',
  'renders/': 'Render Guide',
  'review-report.md': 'Review Report',
};

const EPISODE_UNAVAILABLE_COVERAGE: StoryWorkspaceEpisodeAssociationCoverage = {
  availability: 'unavailable',
  linked: 0,
  total: 0,
  ratio: null,
};

function storyWorkspaceEpisodeEscapeSelection(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  expandedKeys: ReadonlySet<string>,
  selection: StoryWorkspaceEpisodeSelection,
): StoryWorkspaceEpisodeSelection {
  const selectionKey = storyWorkspaceEpisodeSelectionKey(selection);
  const current = storyWorkspaceEpisodeNavigationItems(viewModel, expandedKeys).find(
    (item) => storyWorkspaceEpisodeSelectionKey(item) === selectionKey,
  );
  return current?.navigationParent ?? selection;
}

function storyWorkspaceEpisodeRemovedSelectionAnnouncement(
  selection: StoryWorkspaceEpisodeSelection,
): string {
  if (selection.kind === 'shot') {
    return '当前镜头已在新版本中移除，已移至仍存在的上级。';
  }
  if (selection.kind === 'scene') {
    return '当前场景已在新版本中移除，已移至仍存在的上级。';
  }
  if (selection.kind === 'narrative-beat') {
    return '当前叙事点已在新版本中移除，已移至仍存在的上级。';
  }
  return '当前选择已在新版本中移除，已移至仍存在的上级。';
}

export interface StoryWorkspaceEpisodeRevisionSelectionState {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel | null;
  readonly selection: StoryWorkspaceEpisodeSelection | null;
  readonly announcement: string;
  readonly workbenchRef: RefObject<HTMLDivElement | null>;
  readonly onSelection: (selection: StoryWorkspaceEpisodeSelection) => void;
  readonly onLocateSelection: (selection: StoryWorkspaceEpisodeSelection) => void;
}

function useStoryWorkspaceEpisodeRevisionSelection(
  runId: string,
  viewModel: StoryWorkspaceEpisodeExecutionViewModel | null,
): StoryWorkspaceEpisodeRevisionSelectionState {
  const [selection, setSelection] = useState<StoryWorkspaceEpisodeSelection | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const selectionRef = useRef<StoryWorkspaceEpisodeSelection | null>(null);
  const previousViewModelRef = useRef<StoryWorkspaceEpisodeExecutionViewModel | null>(null);
  const pendingEpisodeFocusKeyRef = useRef<string | null>(null);
  const pendingLocateFocusKeyRef = useRef<string | null>(null);
  const workbenchRef = useRef<HTMLDivElement>(null);
  const activeRunIdRef = useRef(runId);

  useLayoutEffect(() => {
    if (activeRunIdRef.current !== runId) {
      activeRunIdRef.current = runId;
      selectionRef.current = null;
      previousViewModelRef.current = null;
      pendingEpisodeFocusKeyRef.current = null;
      pendingLocateFocusKeyRef.current = null;
    }
    if (viewModel === null) {
      selectionRef.current = null;
      previousViewModelRef.current = null;
      pendingEpisodeFocusKeyRef.current = null;
      setSelection(null);
      setAnnouncement('');
      return;
    }
    const previousViewModel = previousViewModelRef.current ?? viewModel;
    const previousSelection = selectionRef.current;
    const nextSelection = storyWorkspaceReconcileEpisodeSelection(
      previousSelection,
      previousViewModel,
      viewModel,
    );
    if (
      previousSelection !== null
      && nextSelection !== null
      && storyWorkspaceEpisodeSelectionKey(previousSelection)
        !== storyWorkspaceEpisodeSelectionKey(nextSelection)
    ) {
      pendingEpisodeFocusKeyRef.current = storyWorkspaceEpisodeSelectionKey(nextSelection);
      setAnnouncement(storyWorkspaceEpisodeRemovedSelectionAnnouncement(previousSelection));
    } else {
      setAnnouncement('');
    }
    selectionRef.current = nextSelection;
    previousViewModelRef.current = viewModel;
    setSelection(nextSelection);
  }, [runId, viewModel]);

  useLayoutEffect(() => {
    const pendingKey = pendingEpisodeFocusKeyRef.current;
    if (pendingKey === null || selection === null) return;
    if (pendingKey !== storyWorkspaceEpisodeSelectionKey(selection)) return;
    pendingEpisodeFocusKeyRef.current = null;
    workbenchRef.current?.querySelector<HTMLButtonElement>(
      '[role="treeitem"][aria-selected="true"]',
    )?.focus();
  }, [selection, viewModel]);

  useLayoutEffect(() => {
    const pendingKey = pendingLocateFocusKeyRef.current;
    if (pendingKey === null || selection === null) return;
    if (pendingKey !== storyWorkspaceEpisodeSelectionKey(selection)) return;
    const heading = workbenchRef.current?.querySelector<HTMLElement>(
      '[aria-label="叙事内容工作面"] h2',
    );
    if (heading === undefined || heading === null) return;
    pendingLocateFocusKeyRef.current = null;
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    heading.scrollIntoView({
      behavior: reducedMotion ? 'auto' : 'smooth',
      block: 'start',
    });
  }, [selection, viewModel]);

  const onSelection = useCallback((nextSelection: StoryWorkspaceEpisodeSelection) => {
    pendingEpisodeFocusKeyRef.current = null;
    pendingLocateFocusKeyRef.current = null;
    selectionRef.current = nextSelection;
    setAnnouncement('');
    setSelection(nextSelection);
  }, []);

  const onLocateSelection = useCallback((nextSelection: StoryWorkspaceEpisodeSelection) => {
    pendingEpisodeFocusKeyRef.current = null;
    pendingLocateFocusKeyRef.current = storyWorkspaceEpisodeSelectionKey(nextSelection);
    selectionRef.current = nextSelection;
    setAnnouncement('');
    setSelection(nextSelection);
  }, []);

  return {
    viewModel,
    selection,
    announcement,
    workbenchRef,
    onSelection,
    onLocateSelection,
  };
}

function storyWorkspaceEpisodeArtifactAvailability(
  surface: StoryWorkspaceEpisodeArtifactSurface,
  relativeKey: string,
): StoryWorkspaceEpisodeArtifactAvailability {
  return surface.artifacts.find((artifact) => artifact.relativeKey === relativeKey)
    ?.availability ?? 'not_generated';
}

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
  const [agentDialogOpen, setAgentDialogOpen] = useState(false);
  const [focusedArtifact, setFocusedArtifact] =
    useState<StoryWorkspaceEpisodeReadableArtifact>('storyboard.yaml');
  const [pendingArtifactReaderFocus, setPendingArtifactReaderFocus] =
    useState<StoryWorkspaceEpisodeReadableArtifact | null>(null);
  const [episodeExpandedKeys, setEpisodeExpandedKeys] =
    useState<ReadonlySet<string>>(() => new Set());
  const agentPreviewTriggerRef = useRef<HTMLButtonElement>(null);
  const dreamProjectionDetailsRef = useRef<HTMLDetailsElement>(null);
  const episodeArtifactReaderRef = useRef<HTMLDivElement>(null);
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
      : 'story-workspace-dream-running',
  });
  const canQueryEpisode = files.data !== null
    && storyWorkspaceCanAccessExecution(files.data);
  const episodeArtifacts = useStoryWorkspaceEpisodeArtifacts(
    canQueryEpisode ? runId : null,
  );
  const storyIndex = useStoryWorkspaceStoryIndex(runId, { enabled: canQueryEpisode });
  const refreshEpisodeArtifacts = episodeArtifacts.refresh;
  const retryStoryIndex = useCallback(async () => {
    try {
      await storyIndex.reconcile();
    } catch (reason) {
      if (reason instanceof StoryWorkspaceStoryIndexHttpError && reason.status === 409) {
        refreshEpisodeArtifacts();
        storyIndex.refresh();
      }
    }
  }, [refreshEpisodeArtifacts, storyIndex]);
  const episodeSurface = episodeArtifacts.data;
  const episodeViewModel = useMemo(
    () => episodeSurface?.bindingAvailability === 'bound'
      ? storyWorkspaceBuildEpisodeExecutionViewModel(episodeSurface)
      : null,
    [episodeSurface],
  );
  const {
    announcement: episodeSelectionAnnouncement,
    onLocateSelection: locateEpisodeSelection,
    onSelection: setEpisodeSelection,
    selection: episodeSelection,
    workbenchRef: episodeWorkbenchRef,
  } = useStoryWorkspaceEpisodeRevisionSelection(runId, episodeViewModel);

  const locateEpisodeReviewTarget = useCallback((
    selection: StoryWorkspaceEpisodeReviewLocateSelection,
  ) => {
    if (episodeViewModel === null) return;
    setEpisodeExpandedKeys((current) => {
      const next = new Set(current);
      if (selection.kind === 'scene') {
        const scene = episodeViewModel.scenesById[selection.id];
        if (scene?.narrativeBeatId !== null && scene?.narrativeBeatId !== undefined) {
          next.add(storyWorkspaceEpisodeSelectionKey({
            kind: 'narrative-beat',
            id: scene.narrativeBeatId,
          }));
        }
      } else if (selection.kind === 'shot') {
        const shot = episodeViewModel.shotsById[selection.id];
        if (shot?.narrativeBeatId !== null && shot?.narrativeBeatId !== undefined) {
          next.add(storyWorkspaceEpisodeSelectionKey({
            kind: 'narrative-beat',
            id: shot.narrativeBeatId,
          }));
        }
        if (shot?.scriptSceneId !== null && shot?.scriptSceneId !== undefined) {
          next.add(storyWorkspaceEpisodeSelectionKey({
            kind: 'scene',
            id: shot.scriptSceneId,
          }));
        }
      }
      return next;
    });
    locateEpisodeSelection(selection);
  }, [episodeViewModel, locateEpisodeSelection]);

  const workspace = useMemo(
    () => files.data ? storyWorkspaceBuildExecutionWorkspace(files.data) : null,
    [files.data],
  );
  const visibleEntries = activeModule === 'assets'
    ? workspace?.assets ?? []
    : workspace?.outline ?? [];
  const allEntries = useMemo(
    () => [...(workspace?.assets ?? []), ...(workspace?.outline ?? [])],
    [workspace],
  );
  const storyboardFocusEntry = workspace?.outline.find(
    (entry) => entry.stage === 'storyboards',
  ) ?? null;
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
    setFocusedArtifact('storyboard.yaml');
    setPendingArtifactReaderFocus(null);
    setEpisodeExpandedKeys(new Set());
  }, [runId]);

  const handleEpisodeArtifactRead = useCallback((
    artifact: StoryWorkspaceEpisodeReadableArtifact,
  ) => {
    if (storyboardFocusEntry === null) return;
    if (dreamProjectionDetailsRef.current !== null) {
      dreamProjectionDetailsRef.current.open = true;
    }
    setActiveModule('outline');
    setFocusKey(storyboardFocusEntry.key);
    setFocusedArtifact(artifact);
    setPendingArtifactReaderFocus(artifact);
  }, [storyboardFocusEntry]);
  const episodeArtifactReadAction = storyboardFocusEntry === null
    ? undefined
    : handleEpisodeArtifactRead;

  useEffect(() => {
    if (
      pendingArtifactReaderFocus === null
      || focusedEntry?.stage !== 'storyboards'
      || focusedArtifact !== pendingArtifactReaderFocus
    ) return;
    const frame = window.requestAnimationFrame(() => {
      const reader = episodeArtifactReaderRef.current;
      const tab = reader?.querySelector<HTMLButtonElement>(
        `#${storyWorkspaceEpisodeArtifactTabId(pendingArtifactReaderFocus)}`,
      );
      if (reader === null || tab === undefined || tab === null) return;
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      reader.scrollIntoView({
        behavior: reducedMotion ? 'auto' : 'smooth',
        block: 'start',
      });
      tab.focus({ preventScroll: true });
      setPendingArtifactReaderFocus((current) => (
        current === pendingArtifactReaderFocus ? null : current
      ));
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusedArtifact, focusedEntry?.stage, pendingArtifactReaderFocus]);

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
    if (!files.data || storyWorkspaceCanAccessExecution(files.data)) return;
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

  if (files.data && !storyWorkspaceCanAccessExecution(files.data)) {
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
    ? '命令已保存，等待同一 Dream Agent 接续'
    : currentRun?.status === 'completed'
      ? '同一 Dream Agent 已完成后续执行'
      : '同一 Dream Agent 正在执行';
  const agentPreview = agentStateCopy;
  const focusByKey = (key: string | null) => {
    if (key) setFocusKey(key);
  };
  const handleEpisodeExpanded = (
    selection: StoryWorkspaceEpisodeSelection,
    expanded: boolean,
  ) => {
    const key = storyWorkspaceEpisodeSelectionKey(selection);
    setEpisodeExpandedKeys((current) => {
      const next = new Set(current);
      if (expanded) next.add(key);
      else next.delete(key);
      return next;
    });
  };
  const handleEpisodeEscape = (selection: StoryWorkspaceEpisodeSelection) => {
    if (episodeViewModel === null) return;
    const parent = storyWorkspaceEpisodeEscapeSelection(
      episodeViewModel,
      episodeExpandedKeys,
      selection,
    );
    if (
      storyWorkspaceEpisodeSelectionKey(parent)
      !== storyWorkspaceEpisodeSelectionKey(selection)
    ) {
      setEpisodeSelection(parent);
    }
  };
  const selectedEpisodeShot = episodeSelection?.kind === 'shot'
    ? episodeViewModel?.shotsById[episodeSelection.id] ?? null
    : null;
  const scriptArtifactAvailability = episodeSurface?.bindingAvailability === 'bound'
    ? storyWorkspaceEpisodeArtifactAvailability(episodeSurface, 'script.md')
    : 'not_generated';
  const storyIndexFileStatus: StoryWorkspaceStoryIndexFileStatus =
    episodeArtifacts.diagnostic !== null
      || episodeArtifacts.invalidArtifactKeys.includes('script.md')
      ? 'invalid'
      : episodeArtifacts.error !== null
        || episodeArtifacts.unavailableArtifactKeys.includes('script.md')
        ? 'unavailable'
        : scriptArtifactAvailability === 'available'
          ? 'available'
          : storyIndex.data?.errorCode === 'artifact_missing'
            ? 'missing'
            : scriptArtifactAvailability === 'not_generated'
              ? 'generating'
              : scriptArtifactAvailability === 'invalid'
                ? 'invalid'
                : 'unavailable';
  let currentReviewSelection: StoryWorkspaceEpisodeReviewLocateSelection | null = null;
  if (episodeSelection?.kind === 'narrative-beat') {
    currentReviewSelection = { kind: 'narrative-beat', id: episodeSelection.id };
  } else if (episodeSelection?.kind === 'scene') {
    currentReviewSelection = { kind: 'scene', id: episodeSelection.id };
  } else if (episodeSelection?.kind === 'shot') {
    currentReviewSelection = { kind: 'shot', id: episodeSelection.id };
  }

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
        <button
          aria-controls="story-workspace-dream-agent-dialog"
          aria-expanded={agentDialogOpen}
          aria-label="打开 Dream Agent 消息预览"
          className="story-workspace-collaboration__agent-state"
          onClick={() => setAgentDialogOpen(true)}
          ref={agentPreviewTriggerRef}
          type="button"
        >
          <span aria-hidden="true" />
          <span>
            <strong>Dream Agent 消息预览</strong>
            <small>{agentPreview}</small>
          </span>
        </button>
      </header>

      {episodeSurface?.bindingAvailability === 'bound' && (
      <details ref={dreamProjectionDetailsRef}>
        <summary>Dream 初稿阶段投影</summary>
        <div className="story-workspace-collaboration__surface">
        {focusedEntry ? (
          <main
            className="story-workspace-collaboration__focus-layer"
            data-execution-depth="focus"
          >
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
                <>
                  <section className="story-workspace-collaboration__shot-note">
                    <span>镜头说明</span>
                    <div>
                      <b>01</b>
                      <p>{focusedEntry.summary || '等待镜头说明写入工作空间。'}</p>
                    </div>
                  </section>
                  <div ref={episodeArtifactReaderRef}>
                    <StoryWorkspaceEpisodeArtifactReader
                      activeArtifact={focusedArtifact}
                      artifacts={episodeSurface.artifacts}
                      documents={episodeSurface.documents ?? []}
                      episodeCode={episodeSurface.episodeCode ?? 'Episode'}
                      onArtifactSelection={setFocusedArtifact}
                      onShotSelection={(shotId) => setEpisodeSelection({ kind: 'shot', id: shotId })}
                      selectedShotId={selectedEpisodeShot?.id ?? null}
                      shots={episodeSurface.narrative?.shots ?? []}
                    />
                  </div>
                </>
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
          </main>
        ) : (
          <main
            className="story-workspace-collaboration__overview-layer"
            data-execution-depth="overview"
          >
            <div className="story-workspace-collaboration__overview">
              <div className="story-workspace-collaboration__module-switch" role="tablist">
                {(Object.keys(MODULE_COPY) as ExecutionModule[]).map((module) => (
                  <button
                    aria-controls="story-workspace-execution-index"
                    aria-selected={activeModule === module}
                    key={module}
                    onClick={() => setActiveModule(module)}
                    role="tab"
                    type="button"
                  >
                    <strong>{MODULE_COPY[module].label}</strong>
                    <small>{MODULE_COPY[module].description}</small>
                  </button>
                ))}
              </div>

              <header>
                <p>{MODULE_COPY[activeModule].label} · Narrative execution</p>
                <h2>{activeModule === 'assets' ? '故事资产' : '故事线与叙事点'}</h2>
                <span>
                  {activeModule === 'assets'
                    ? 'Agent 持续同步人物与场景；选择条目可查看聚焦上下文。'
                    : '选择一条分镜摘要，进入同一工作面内的聚焦协作层。'}
                </span>
              </header>

              <section
                aria-label={`${MODULE_COPY[activeModule].label} 索引`}
                id="story-workspace-execution-index"
                role="tabpanel"
              >
                {visibleEntries.length > 0 ? (
                  <ol className="story-workspace-collaboration__manuscript">
                  {visibleEntries.map((entry, index) => (
                    <li key={entry.key}>
                      <button
                        onClick={() => setFocusKey(entry.key)}
                        onKeyDown={(event) => focusListItem(event, index, visibleEntries.length)}
                        type="button"
                      >
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
              </section>

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
          </main>
        )}
        </div>
      </details>
      )}
      <section aria-label="Episode 产物工作台">
        {episodeSurface === null ? (
          <div role="status">
            {episodeArtifacts.diagnostic !== null ? (
              <p>Episode 产物来源无效，暂无法读取。</p>
            ) : episodeArtifacts.error !== null ? (
              <p>Episode 产物尚未同步，页面会继续读取。</p>
            ) : (
              <p>正在读取 Episode 产物…</p>
            )}
          </div>
        ) : episodeSurface.bindingAvailability === 'unbound' ? (
          <main aria-labelledby="story-workspace-episode-unbound-title">
            <h2 id="story-workspace-episode-unbound-title">尚未构建 Episode 产物关联</h2>
            <p role="status">关联状态：等待主 Agent 成功构建并自动发布</p>
            <p>
              确认后的 Dream Agent 成功生成并通过服务端校验后，系统会自动发布产物、
              构建关联并由页面读取更新，无需手动构建。
            </p>
          </main>
        ) : (
          <main aria-labelledby="story-workspace-episode-title">
            <header>
              <p>{episodeSurface.episodeCode} · Episode execution</p>
              <h2 id="story-workspace-episode-title">
                {episodeSurface.narrative?.overview.title
                  ?? `${episodeSurface.episodeCode} 产物`}
              </h2>
              <p role="status">{episodeSurface.episodeCode} 产物关联：已关联</p>
              <StoryWorkspaceStoryIndexStatus
                error={storyIndex.error}
                fileStatus={storyIndexFileStatus}
                isLoading={storyIndex.isLoading}
                isSyncing={storyIndex.isReconciling}
                onRefresh={storyIndex.refresh}
                onRetry={() => { void retryStoryIndex(); }}
                projection={storyIndex.data}
              />
              {episodeArtifacts.isLoading && (
                <p aria-live="polite">正在检查新的 artifact revision…</p>
              )}
              {episodeArtifacts.isShowingLastGood && (
                <p role="status">
                  最新 revision 的部分产物不可用；当前显示最近一次有效内容。
                </p>
              )}
              {episodeArtifacts.invalidArtifactKeys.length > 0 && (
                <p role="status">
                  部分产物来源无效：
                  {episodeArtifacts.invalidArtifactKeys.map(
                    (key) => EPISODE_ARTIFACT_LABELS[key],
                  ).join('、')}
                </p>
              )}
              {episodeArtifacts.unavailableArtifactKeys.length > 0 && (
                <p role="status">
                  部分产物暂时无法同步：
                  {episodeArtifacts.unavailableArtifactKeys.map(
                    (key) => EPISODE_ARTIFACT_LABELS[key],
                  ).join('、')}
                </p>
              )}
              {episodeArtifacts.staleArtifactKeys.length > 0 && (
                <p role="status">部分产物仍沿用最近一次有效 revision。</p>
              )}
              {episodeArtifacts.error !== null && (
                <p role="status">暂时无法检查新 revision；当前内容没有被消息覆盖。</p>
              )}
            </header>

            {episodeViewModel === null || episodeSelection === null ? (
              <section role="status">
                {storyWorkspaceEpisodeArtifactAvailability(
                  episodeSurface,
                  'episode-outline.md',
                ) === 'not_generated'
                  ? '故事线尚未生成'
                  : '正在建立故事线导航…'}
              </section>
            ) : (
              <div ref={episodeWorkbenchRef}>
                <p aria-live="polite">{episodeSelectionAnnouncement}</p>
                <StoryWorkspaceEpisodeNarrativeWorkbench
                  artifactProgress={episodeSurface.artifacts}
                  episodeCode={episodeSurface.episodeCode ?? 'Episode'}
                  auxiliarySlot={(
                    <>
                      {selectedEpisodeShot !== null && (
                        <StoryWorkspaceEpisodeShotAuxiliary
                          associationCoverage={{
                            shotPrompt: episodeSurface.auxiliary?.associations
                              .shotPromptCoverage ?? EPISODE_UNAVAILABLE_COVERAGE,
                            shotRenderQueue: episodeSurface.auxiliary?.associations
                              .shotRenderQueueCoverage ?? EPISODE_UNAVAILABLE_COVERAGE,
                          }}
                          prompts={episodeViewModel.promptsByShotViewId[
                            selectedEpisodeShot.id
                          ] ?? []}
                          renderGuideSections={
                            episodeSurface.auxiliary?.renderGuide?.sections ?? []
                          }
                          renderQueueEntries={episodeViewModel.renderQueueByShotViewId[
                            selectedEpisodeShot.id
                          ] ?? []}
                          selectedShot={selectedEpisodeShot}
                          sourceAvailability={{
                            prompts: storyWorkspaceEpisodeArtifactAvailability(
                              episodeSurface,
                              'prompts/',
                            ),
                            renderGuide: storyWorkspaceEpisodeArtifactAvailability(
                              episodeSurface,
                              'renders/',
                            ),
                          }}
                        />
                      )}
                      <StoryWorkspaceEpisodeReviewPanel
                        availability={storyWorkspaceEpisodeArtifactAvailability(
                          episodeSurface,
                          'review-report.md',
                        )}
                        currentTargetSelection={currentReviewSelection}
                        onLocateTarget={locateEpisodeReviewTarget}
                        review={episodeSurface.auxiliary?.review ?? null}
                      />
                    </>
                  )}
                  episodeOverview={episodeSurface.narrative?.overview ?? null}
                  expandedKeys={episodeExpandedKeys}
                  onEscape={handleEpisodeEscape}
                  onExpanded={handleEpisodeExpanded}
                  onArtifactRead={episodeArtifactReadAction}
                  onSelection={setEpisodeSelection}
                  selection={episodeSelection}
                  viewModel={episodeViewModel}
                />
              </div>
            )}
          </main>
        )}
      </section>

      {agentDialogOpen && (
        <StoryWorkspaceDreamAgentDialog
          deckName={currentRun?.deck_plugin_display_name ?? '当前 Deck'}
          onClose={() => setAgentDialogOpen(false)}
          onSettled={() => {
            refreshEpisodeArtifacts();
            storyIndex.refresh();
          }}
          restoreFocusRef={agentPreviewTriggerRef}
          runId={runId}
          threadId={files.data.threadId}
        />
      )}
    </section>
  );
}
