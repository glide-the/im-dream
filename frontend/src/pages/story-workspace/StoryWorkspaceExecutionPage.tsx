// [Input] Confirmed Run, `.dream` projections, registry Episode index, and one
//         explicitly selected Episode artifact surface.
// [Output] Outline-aligned Episode index plus Run+Episode-isolated workbench and return navigation.
// [Pos] /story-workspace/runs/:storyWorkspaceRunId/execution (Task 3 U11)
// [Sync] 2026-08-06: compose Episode artifacts without changing their REST ownership.
// [Sync] 2026-08-13: describe an unbound Episode as a pending artifact-association
//                    build, reserving trust language for server identity checks.
// [Sync] 2026-08-13: keep Episode association state read-only; confirmed turns
//                    publish and bind automatically without a manual UI action.
// [Sync] 2026-08-13: render canonical Project title separately from Episode title.
// [Sync] 2026-08-13: hand the dialog's bound Dream thread to canonical Chat.
// [Sync] 2026-08-14: render Hook-published complete character/scene documents
//                    in the focus layer while keeping index summaries compact.
// [Sync] 2026-08-14: remove the revision-derived workspace update feed; keep
//                    the screenplay workbench focused on current artifacts.
// [Sync] 2026-08-14: separate YAML frontmatter from Markdown prose and bind
//                    storyboard notes to the selected projected shot.
// [Sync] 2026-08-14: make the Dream draft the default full workbench and keep
//                    Episode coordination behind the dialog's draft/sync switch.
// [Sync] 2026-08-31: host the canonical file reader inside its matching draft
//                    Episode focus instead of the sync surface.
// [Sync] 2026-08-31: summarize storyboard shot count and duration in the EP
//                    list description instead of repeating a focus section.
// [Sync] 2026-08-31: add a three-stage creation guide trigger to the Outline
//                    header and open it through the same in-place focus navigation.
// [Sync] 2026-08-31: keep the Outline guide local while Dream uses its static route.
// [Sync] 2026-09-02: make Sync index-first, route selection by Episode UID, and remove storyboard-title ambiguity.

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  StoryWorkspaceStoryIndexStatus,
  storyWorkspaceReviewDeepLink,
  type StoryWorkspaceStoryIndexFileStatus,
} from '../../components/story-workspace';
import {
  StoryWorkspaceStoryIndexHttpError,
  useStoryWorkspaceDreamFiles,
  useStoryWorkspaceDreamRuns,
  useStoryWorkspaceStoryIndex,
} from '../../hooks/story-workspace';
import type {
  StoryWorkspaceEpisodeAssociationCoverage,
  StoryWorkspaceEpisodeArtifactAvailability,
  StoryWorkspaceEpisodeArtifactSurface,
  StoryWorkspaceEpisodeIndexItem,
} from '../../hooks/story-workspace/contracts';
import { useStoryWorkspaceEpisodeArtifacts } from '../../hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts';
import { useStoryWorkspaceEpisodeIndex } from '../../hooks/story-workspace/useStoryWorkspaceEpisodeIndex';
import {
  StoryWorkspaceDreamAgentDialog,
  type StoryWorkspaceExecutionView,
} from '../../components/story-workspace/dream/StoryWorkspaceDreamAgentDialog';
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
import {
  STORY_WORKSPACE_CREATION_GUIDE_FOCUS_KEY,
  StoryWorkspaceCreationGuide,
} from '../../components/story-workspace/StoryWorkspaceCreationGuide';
import { useWorkflowRun } from '../../hooks/useWorkflowRun';
import { storyWorkspaceExecutionEpisodePath } from '../../router/storyWorkspacePath';
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
  storyWorkspaceExecutionEpisodeEntry,
  storyWorkspaceExecutionFocusNeighbors,
  storyWorkspaceResolveDreamDisplayTitle,
} from './executionViewModel';
import { storyWorkspaceBuildAssetDocumentViewModel } from './assetDocumentViewModel';
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

const ASSET_MARKDOWN_COMPONENTS: Components = {
  a({ children, href }) {
    if (href === undefined) return <span>{children}</span>;
    return <a href={href} rel="noreferrer" target="_blank">{children}</a>;
  },
  img({ alt }) {
    return <span role="img" aria-label={alt ?? '资产图片'}>[图片：{alt ?? '未命名'}]</span>;
  },
};

function StoryWorkspaceAssetContent({
  content,
  sourceFile,
}: {
  readonly content: string;
  readonly sourceFile: string;
}) {
  if (!sourceFile.toLowerCase().endsWith('.md')) {
    return <pre><code>{content}</code></pre>;
  }
  const document = storyWorkspaceBuildAssetDocumentViewModel(content);
  return (
    <>
      {document.metadata.length > 0 && (
        <dl aria-label="资产元数据" className="story-workspace-collaboration__asset-metadata">
          {document.metadata.map((entry) => (
            <div key={entry.key}>
              <dt>{entry.label}</dt>
              <dd>{entry.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {document.metadataFallback !== null && (
        <pre aria-label="资产元数据原文"><code>{document.metadataFallback}</code></pre>
      )}
      {document.body && (
        <div className="story-workspace-collaboration__asset-prose">
          <ReactMarkdown
            components={ASSET_MARKDOWN_COMPONENTS}
            remarkPlugins={[remarkGfm]}
            skipHtml
          >
            {document.body}
          </ReactMarkdown>
        </div>
      )}
    </>
  );
}

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
  onOpenChatThread: (threadId: string) => void;
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

interface StoryWorkspaceManuscriptItem {
  readonly key: string;
  readonly ordinal: string;
  readonly eyebrow: string;
  readonly title: string;
  readonly description: string;
  readonly accessibleName?: string;
  readonly dataEpisodeId?: string;
}

function StoryWorkspaceManuscriptIndex({
  items,
  onSelect,
  empty,
}: {
  readonly items: readonly StoryWorkspaceManuscriptItem[];
  readonly onSelect: (item: StoryWorkspaceManuscriptItem) => void;
  readonly empty: ReactNode;
}) {
  if (items.length === 0) return <>{empty}</>;
  return (
    <ol className="story-workspace-collaboration__manuscript">
      {items.map((item, index) => (
        <li key={item.key}>
          <button
            aria-label={item.accessibleName}
            data-episode-id={item.dataEpisodeId}
            onClick={() => onSelect(item)}
            onKeyDown={(event) => focusListItem(event, index, items.length)}
            type="button"
          >
            <span>{item.ordinal}</span>
            <span>
              <small>{item.eyebrow}</small>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
            </span>
            <b aria-hidden="true">→</b>
          </button>
        </li>
      ))}
    </ol>
  );
}

function storyWorkspaceEpisodeIndexStatus(
  episode: StoryWorkspaceEpisodeIndexItem,
  runIsComplete: boolean,
): string {
  if (episode.hasArtifactIssues) return '读取失败';
  if (episode.active && !runIsComplete) return '执行中';
  if (episode.availableArtifactCount > 0) return '已有产物';
  return '暂无产物';
}

function storyWorkspaceEpisodeIndexDescription(
  episode: StoryWorkspaceEpisodeIndexItem,
): string {
  const availability = episode.availableArtifactCount > 0
    ? `${episode.availableArtifactCount} 项产物可查看`
    : '尚无可查看产物';
  if (episode.updatedAt === null) return availability;
  const updated = new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(episode.updatedAt));
  return `${availability} · 更新于 ${updated}`;
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
  onOpenChatThread,
}: StoryWorkspaceExecutionPageProps) {
  const [activeModule, setActiveModule] = useState<ExecutionModule>('outline');
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const [agentDialogOpen, setAgentDialogOpen] = useState(false);
  const [workspaceView, setWorkspaceView] = useState<StoryWorkspaceExecutionView>('draft');
  const [focusedArtifact, setFocusedArtifact] =
    useState<StoryWorkspaceEpisodeReadableArtifact>('storyboard.yaml');
  const [pendingArtifactReaderFocus, setPendingArtifactReaderFocus] =
    useState<StoryWorkspaceEpisodeReadableArtifact | null>(null);
  const [episodeExpandedKeys, setEpisodeExpandedKeys] =
    useState<ReadonlySet<string>>(() => new Set());
  const agentPreviewTriggerRef = useRef<HTMLButtonElement>(null);
  const episodeArtifactReaderRef = useRef<HTMLDivElement>(null);
  const episodeIndexRef = useRef<HTMLElement>(null);
  const pendingEpisodeIndexFocusRef = useRef<string | null>(null);
  const { run, selectRun } = useWorkflowRun({ eventsEnabled: true });
  const currentRun = run?.workflow_run_id === runId ? run : null;
  const dreamRuns = useStoryWorkspaceDreamRuns();
  const currentDreamRun = useMemo(
    () => dreamRuns.data?.runs.find((candidate) => (
      candidate.storyWorkspaceRunId === runId
    )) ?? null,
    [dreamRuns.data, runId],
  );

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
  const episodeIndex = useStoryWorkspaceEpisodeIndex(
    canQueryEpisode ? runId : null,
  );
  const selectedEpisode = useMemo(
    () => episodeId === null || episodeId === undefined
      ? null
      : episodeIndex.data?.episodes.find((episode) => (
        episode.opaqueEpisodeId === episodeId
      )) ?? null,
    [episodeId, episodeIndex.data],
  );
  const artifactEpisodeId = workspaceView === 'sync'
    ? selectedEpisode?.opaqueEpisodeId ?? null
    : episodeIndex.data?.activeEpisodeId ?? null;
  const episodeArtifacts = useStoryWorkspaceEpisodeArtifacts(
    canQueryEpisode ? runId : null,
    artifactEpisodeId,
  );
  const storyIndex = useStoryWorkspaceStoryIndex(runId, {
    enabled: canQueryEpisode,
  });
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
  } = useStoryWorkspaceEpisodeRevisionSelection(
    `${runId}:${artifactEpisodeId ?? 'index'}`,
    episodeViewModel,
  );

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
  const episodeDraftEntry = useMemo(
    () => storyWorkspaceExecutionEpisodeEntry(
      workspace?.outline ?? [],
      episodeSurface?.episodeCode,
    ),
    [episodeSurface?.episodeCode, workspace?.outline],
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
  const creationGuideFocused = focusKey === STORY_WORKSPACE_CREATION_GUIDE_FOCUS_KEY;
  const focusNeighbors = useMemo(() => {
    const focusEntries = focusedEntry?.module === 'Assets'
      ? workspace?.assets ?? []
      : workspace?.outline ?? [];
    return storyWorkspaceExecutionFocusNeighbors(focusEntries, focusKey ?? '');
  }, [focusKey, focusedEntry?.module, workspace?.assets, workspace?.outline]);

  useEffect(() => {
    setWorkspaceView('draft');
    setActiveModule('outline');
    setFocusKey(null);
    setFocusedArtifact('storyboard.yaml');
    setPendingArtifactReaderFocus(null);
    setEpisodeExpandedKeys(new Set());
  }, [runId]);

  useEffect(() => {
    if (episodeId) setWorkspaceView('sync');
  }, [episodeId]);

  useLayoutEffect(() => {
    if (episodeId !== null && episodeId !== undefined) return;
    const pendingEpisodeId = pendingEpisodeIndexFocusRef.current;
    if (pendingEpisodeId === null) return;
    const frame = window.requestAnimationFrame(() => {
      const button = episodeIndexRef.current?.querySelector<HTMLButtonElement>(
        `[data-episode-id="${pendingEpisodeId}"]`,
      );
      if (button === undefined || button === null) return;
      pendingEpisodeIndexFocusRef.current = null;
      button.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [episodeId, episodeIndex.data]);

  const handleEpisodeArtifactRead = useCallback((
    artifact: StoryWorkspaceEpisodeReadableArtifact,
  ) => {
    if (episodeDraftEntry === null) return;
    setWorkspaceView('draft');
    setActiveModule('outline');
    setFocusKey(episodeDraftEntry.key);
    setFocusedArtifact(artifact);
    setPendingArtifactReaderFocus(artifact);
    navigate(storyWorkspaceExecutionEpisodePath(runId));
  }, [episodeDraftEntry, navigate, runId]);
  const episodeArtifactReadAction = episodeSurface?.bindingAvailability === 'bound'
    && episodeDraftEntry !== null
    ? handleEpisodeArtifactRead
    : undefined;

  useEffect(() => {
    if (
      pendingArtifactReaderFocus === null
      || workspaceView !== 'draft'
      || focusKey !== episodeDraftEntry?.key
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
  }, [episodeDraftEntry?.key, focusKey, focusedArtifact, pendingArtifactReaderFocus, workspaceView]);

  useEffect(() => {
    if (
      !focusKey
      || focusKey === STORY_WORKSPACE_CREATION_GUIDE_FOCUS_KEY
      || allEntries.some((entry) => entry.key === focusKey)
    ) return;
    setFocusKey(null);
  }, [allEntries, focusKey]);

  useEffect(() => {
    if (!focusedEntry && !creationGuideFocused) return;
    const closeFocus = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setFocusKey(null);
    };
    window.addEventListener('keydown', closeFocus);
    return () => window.removeEventListener('keydown', closeFocus);
  }, [creationGuideFocused, focusedEntry]);

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
  const storyboardShots = episodeSurface?.bindingAvailability === 'bound'
    ? episodeSurface.narrative?.shots ?? []
    : [];
  const focusedStoryboardShot = selectedEpisodeShot ?? storyboardShots[0] ?? null;
  const storyboardDurationSeconds = storyboardShots.reduce(
    (total, shot) => total + (shot.timing.durationSec ?? 0),
    0,
  );
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
  const episodeIndexItems: readonly StoryWorkspaceManuscriptItem[] = (
    episodeIndex.data?.episodes ?? []
  ).map((episode) => {
    const status = storyWorkspaceEpisodeIndexStatus(
      episode,
      currentRun?.status === 'completed',
    );
    const description = storyWorkspaceEpisodeIndexDescription(episode);
    return {
      key: episode.opaqueEpisodeId,
      ordinal: episode.episodeCode.slice(2),
      eyebrow: `Episode · ${status}`,
      title: episode.episodeCode,
      description,
      accessibleName: `${episode.episodeCode}，${status}，${description}`,
      dataEpisodeId: episode.opaqueEpisodeId,
    };
  });
  const openEpisode = (item: StoryWorkspaceManuscriptItem) => {
    setWorkspaceView('sync');
    navigate(storyWorkspaceExecutionEpisodePath(runId, item.key));
  };
  const returnToEpisodeIndex = () => {
    if (selectedEpisode !== null) {
      pendingEpisodeIndexFocusRef.current = selectedEpisode.opaqueEpisodeId;
    }
    navigate(storyWorkspaceExecutionEpisodePath(runId));
  };
  const episodeReturnButton = (
    <button
      className="story-workspace-collaboration__episode-back"
      onClick={returnToEpisodeIndex}
      type="button"
    >
      ← 返回 Episode 索引
    </button>
  );

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
            {storyWorkspaceResolveDreamDisplayTitle(
              storyIndex.data?.projectTitle,
              currentDreamRun?.goalPrefix,
            )}
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

      {workspaceView === 'draft' && (
      <section
        aria-label="Dream 初稿工作台"
        className="story-workspace-collaboration__draft-surface"
        id="story-workspace-draft-surface"
      >
        <div className="story-workspace-collaboration__surface">
        {creationGuideFocused ? (
          <StoryWorkspaceCreationGuide onBack={() => setFocusKey(null)} />
        ) : focusedEntry ? (
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

              {focusedEntry.stage !== 'storyboards' && (
                <section className="story-workspace-collaboration__prose">
                  <span>{focusedEntry.content ? '完整资产资料' : '主要信息'}</span>
                  {focusedEntry.content ? (
                    <div className="story-workspace-collaboration__asset-document">
                      <StoryWorkspaceAssetContent
                        content={focusedEntry.content}
                        sourceFile={focusedEntry.sourceFile}
                      />
                    </div>
                  ) : (
                    <p>{focusedEntry.summary || 'Agent 尚未写入摘要。'}</p>
                  )}
                </section>
              )}

              {focusedEntry.stage === 'storyboards' && (
                <>
                  <section className="story-workspace-collaboration__shot-note">
                    <span>镜头说明</span>
                    <div>
                      <code>{focusedStoryboardShot?.shotId ?? focusedEntry.entityId}</code>
                      <p>{focusedStoryboardShot?.visual ?? '等待镜头说明写入工作空间。'}</p>
                    </div>
                  </section>
                  {episodeSurface?.bindingAvailability === 'bound'
                    && focusedEntry.key === episodeDraftEntry?.key ? (
                    <div ref={episodeArtifactReaderRef}>
                      <StoryWorkspaceEpisodeArtifactReader
                        activeArtifact={focusedArtifact}
                        artifacts={episodeSurface.artifacts}
                        documents={episodeSurface.documents ?? []}
                        episodeCode={episodeSurface.episodeCode ?? focusedEntry.entityId}
                        onArtifactSelection={setFocusedArtifact}
                        onShotSelection={(shotId) => setEpisodeSelection({ kind: 'shot', id: shotId })}
                        selectedShotId={selectedEpisodeShot?.id ?? null}
                        shots={episodeSurface.narrative?.shots ?? []}
                      />
                    </div>
                  ) : null}
                </>
              )}

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
                {activeModule === 'assets' ? (
                  <span>Agent 持续同步人物与场景；选择条目可查看聚焦上下文。</span>
                ) : (
                  <button
                    className="story-workspace-collaboration__guide-trigger"
                    onClick={() => setFocusKey(STORY_WORKSPACE_CREATION_GUIDE_FOCUS_KEY)}
                    type="button"
                  >
                    查看短剧创作阶段指引
                    <b aria-hidden="true">→</b>
                  </button>
                )}
              </header>

              <section
                aria-label={`${MODULE_COPY[activeModule].label} 索引`}
                id="story-workspace-execution-index"
                role="tabpanel"
              >
                <StoryWorkspaceManuscriptIndex
                  empty={<EmptyWorkspaceModule module={activeModule} />}
                  items={visibleEntries.map((entry, index) => ({
                    key: entry.key,
                    ordinal: String(index + 1).padStart(2, '0'),
                    eyebrow: `${entry.stageLabel} · r${entry.revision}`,
                    title: entry.title,
                    description: entry.stage === 'storyboards'
                      ? entry.key === episodeDraftEntry?.key && storyboardShots.length > 0
                        ? `${storyboardShots.length} 镜、${storyboardDurationSeconds} 秒。`
                        : '分镜概览尚未生成。'
                      : entry.summary || '等待 Agent 补充主要信息。',
                  }))}
                  onSelect={(item) => setFocusKey(item.key)}
                />
              </section>

            </div>
          </main>
        )}
        </div>
      </section>
      )}
      {workspaceView === 'sync' && (
      <section aria-label="Episode 产物工作台" id="story-workspace-sync-surface">
        {episodeId === null || episodeId === undefined ? (
          <main
            aria-labelledby="story-workspace-episode-index-title"
            className="story-workspace-collaboration__overview-layer"
            ref={episodeIndexRef}
          >
            <div className="story-workspace-collaboration__overview">
              <header>
                <p>Sync · Episode index</p>
                <h2 id="story-workspace-episode-index-title">Episodes</h2>
                <span>选择一个 Episode 查看对应状态与产物。</span>
              </header>
              <section aria-label="Episode 索引">
                {episodeIndex.data !== null ? (
                  <StoryWorkspaceManuscriptIndex
                    empty={(
                      <div className="story-workspace-collaboration__empty" role="status">
                        <span aria-hidden="true" />
                        <p>尚无 Episode</p>
                        <small>Agent 创建首个 Episode 后会在这里显示。</small>
                      </div>
                    )}
                    items={episodeIndexItems}
                    onSelect={openEpisode}
                  />
                ) : (
                  <div className="story-workspace-collaboration__empty" role="status">
                    <span aria-hidden="true" />
                    <p>{episodeIndex.error !== null
                      ? 'Episode 索引加载失败'
                      : '正在读取 Episode 索引…'}</p>
                    <small>{episodeIndex.error !== null
                      ? '页面会继续读取；也可稍后重试。'
                      : '正在获取当前任务中的 Episode。'}</small>
                    {episodeIndex.error !== null && (
                      <button onClick={episodeIndex.refresh} type="button">重试</button>
                    )}
                  </div>
                )}
              </section>
            </div>
          </main>
        ) : episodeIndex.data !== null && selectedEpisode === null ? (
          <main aria-labelledby="story-workspace-episode-invalid-title">
            <header>
              {episodeReturnButton}
              <h2 id="story-workspace-episode-invalid-title">Episode 不存在或已失效</h2>
              <p role="status">当前链接不属于这个任务，请返回 Episode 索引重新选择。</p>
            </header>
          </main>
        ) : episodeSurface === null ? (
          <main aria-labelledby="story-workspace-episode-loading-title">
            <header>
              {episodeReturnButton}
              <h2 id="story-workspace-episode-loading-title">
                {selectedEpisode?.episodeCode ?? 'Episode'}
              </h2>
              <p role="status">
                {episodeIndex.error !== null ? 'Episode 索引加载失败，页面会继续读取。'
                  : episodeArtifacts.diagnostic !== null ? 'Episode 产物来源无效，暂无法读取。'
                    : episodeArtifacts.error !== null ? 'Episode 产物尚未同步，页面会继续读取。'
                      : '正在读取 Episode 产物…'}
              </p>
            </header>
          </main>
        ) : episodeSurface.bindingAvailability === 'unbound' ? (
          <main aria-labelledby="story-workspace-episode-unbound-title">
            <header>
              {episodeReturnButton}
              <h2 id="story-workspace-episode-unbound-title">
                {selectedEpisode?.episodeCode ?? 'Episode'}
              </h2>
              <p role="status">暂无产物</p>
            </header>
          </main>
        ) : (
          <main aria-labelledby="story-workspace-episode-title">
            <header>
              {episodeReturnButton}
              <h2 id="story-workspace-episode-title">
                {episodeSurface.episodeCode}
              </h2>
              {episodeSurface.narrative?.overview.title && (
                <p>{episodeSurface.narrative.overview.title}</p>
              )}
              <p role="status">{selectedEpisode?.availableArtifactCount ?? 0} 项产物可查看</p>
              {artifactEpisodeId === episodeIndex.data?.activeEpisodeId && (
                <StoryWorkspaceStoryIndexStatus
                  error={storyIndex.error}
                  fileStatus={storyIndexFileStatus}
                  isLoading={storyIndex.isLoading}
                  isSyncing={storyIndex.isReconciling}
                  onRefresh={storyIndex.refresh}
                  onRetry={() => { void retryStoryIndex(); }}
                  projection={storyIndex.data}
                />
              )}
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
      )}

      {agentDialogOpen && (
        <StoryWorkspaceDreamAgentDialog
          deckName={currentRun?.deck_plugin_display_name ?? '当前 Deck'}
          onClose={() => setAgentDialogOpen(false)}
          onOpenChatThread={onOpenChatThread}
          onWorkspaceViewChange={setWorkspaceView}
          onSettled={() => {
            episodeIndex.refresh();
            refreshEpisodeArtifacts();
            storyIndex.refresh();
          }}
          restoreFocusRef={agentPreviewTriggerRef}
          runId={runId}
          threadId={files.data.threadId}
          workspaceView={workspaceView}
        />
      )}
    </section>
  );
}
