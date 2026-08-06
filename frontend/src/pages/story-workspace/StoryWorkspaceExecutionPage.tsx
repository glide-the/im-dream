/* eslint-disable react-refresh/only-export-components -- U11 exports deterministic action seams for Node verification. */
// [Input] Confirmed run identity, `.dream` projections, and authoritative Episode artifact surface.
// [Output] Revision-stable Episode workbench with controlled Dream Agent continuation.
// [Pos] /story-workspace/runs/:storyWorkspaceRunId/execution (Task 3 U11)
// [Sync] 2026-08-06: compose Episode artifacts without changing their REST ownership.

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
import { storyWorkspaceReviewDeepLink } from '../../components/story-workspace';
import { useStoryWorkspaceDreamAgent, useStoryWorkspaceDreamFiles } from '../../hooks/story-workspace';
import { storyWorkspaceDreamAgentHasSettledMessage } from '../../hooks/story-workspace/useStoryWorkspaceDreamAgent';
import type {
  StoryWorkspaceEpisodeAssociationCoverage,
  StoryWorkspaceEpisodeArtifactAvailability,
  StoryWorkspaceEpisodeArtifactSurface,
  StoryWorkspaceEpisodeDispatchAction,
  StoryWorkspaceEpisodeActionOptionV2,
} from '../../hooks/story-workspace/contracts';
import { storyWorkspaceEpisodeOptionCanonicalInputs } from '../../hooks/story-workspace/contracts';
import {
  storyWorkspaceContinueEpisodeAction,
  storyWorkspaceRecoverEpisodeBinding,
  useStoryWorkspaceEpisodeArtifacts,
} from '../../hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts';
import { getAuthToken } from '../../contexts/AuthContext';
import {
  StoryWorkspaceDreamAgentDialog,
  type StoryWorkspaceDreamAgentWorkflowActionViewModel,
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

const EPISODE_ACTION_LABELS: Readonly<Record<StoryWorkspaceEpisodeDispatchAction, string>> = {
  plan_episode: '生成第一集大纲',
  write_script: '继续生成剧本',
  review_script: '审阅剧本',
  refresh_assets: '刷新角色与场景资产',
  regenerate_storyboard: '更新详细分镜',
  generate_prompts: '生成镜头 Prompt',
  review_full_chain: '审阅完整第一集',
  validate_episode: '验证第一集产物',
  prepare_render_guide: '生成制作指导',
};

const EPISODE_ARTIFACT_LABELS: Readonly<Record<string, string>> = {
  'episode-outline.md': 'Episode Outline',
  'script.md': 'Script',
  'storyboard.yaml': 'Storyboard',
  'prompts/': 'Prompts',
  'renders/': 'Render Guide',
  'review-report.md': 'Review Report',
};

const EPISODE_ARTIFACT_AVAILABILITY_LABELS:
Readonly<Record<StoryWorkspaceEpisodeArtifactAvailability, string>> = {
  available: '已生成',
  not_generated: '尚未生成',
  invalid: '来源无效',
  unavailable: '当前不可用',
};

const EPISODE_UNAVAILABLE_COVERAGE: StoryWorkspaceEpisodeAssociationCoverage = {
  availability: 'unavailable',
  linked: 0,
  total: 0,
  ratio: null,
};

export function storyWorkspaceEpisodeNextActionLabel(action: string): string | null {
  return Object.prototype.hasOwnProperty.call(EPISODE_ACTION_LABELS, action)
    ? EPISODE_ACTION_LABELS[action as StoryWorkspaceEpisodeDispatchAction]
    : null;
}

interface StoryWorkspaceEpisodePendingActionKey {
  readonly identity: string;
  readonly key: string;
}

/** One mounted page reuses a key only while retrying the same server fact/action. */
export class StoryWorkspaceEpisodeActionSessionKeys {
  private pending: StoryWorkspaceEpisodePendingActionKey | null = null;
  private readonly createKey: () => string;

  constructor(createKey: () => string) {
    this.createKey = createKey;
  }

  keyFor(runId: string, fact: string, action: string): string {
    const identity = `${runId}\u0000${fact}\u0000${action}`;
    if (this.pending?.identity === identity) return this.pending.key;
    const key = this.createKey();
    this.pending = { identity, key };
    return key;
  }

  rotate(runId: string, fact: string, action: string): void {
    const identity = `${runId}\u0000${fact}\u0000${action}`;
    if (this.pending?.identity === identity) this.pending = null;
  }
}

interface StoryWorkspaceEpisodeDispatchedAction {
  readonly identity: string;
  readonly messageId: string;
}

export interface StoryWorkspaceEpisodeActionTicket {
  readonly identity: string;
  readonly generation: number;
}

export function storyWorkspaceEpisodeActionTicketIsFresh(
  ticket: StoryWorkspaceEpisodeActionTicket,
  currentIdentity: string,
  currentGeneration: number,
  mounted: boolean,
): boolean {
  return mounted
    && ticket.identity === currentIdentity
    && ticket.generation === currentGeneration;
}

export function storyWorkspaceNormalizeEpisodeGuidance(value: string): string | null {
  const normalized = value.trim();
  return normalized.length === 0 ? null : normalized;
}

export interface StoryWorkspaceEpisodeCanonicalInput {
  readonly label: string;
  readonly availability: string;
  readonly revision: string | null;
}

export function storyWorkspaceEpisodeCanonicalInputs(
  surface: Pick<StoryWorkspaceEpisodeArtifactSurface, 'artifacts'>,
): readonly StoryWorkspaceEpisodeCanonicalInput[] {
  return surface.artifacts.map((artifact) => ({
    label: EPISODE_ARTIFACT_LABELS[artifact.relativeKey] ?? '受控产物',
    availability: EPISODE_ARTIFACT_AVAILABILITY_LABELS[artifact.availability],
    revision: artifact.contentRevision,
  }));
}

export function storyWorkspaceEpisodeEscapeSelection(
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

export function useStoryWorkspaceEpisodeRevisionSelection(
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

export interface StoryWorkspaceEpisodeContinueDialogProps {
  readonly actionLabel: string;
  readonly targetEpisodeLabel?: string;
  readonly canonicalInputs: readonly StoryWorkspaceEpisodeCanonicalInput[];
  readonly consequences?: readonly string[];
  readonly busy: boolean;
  readonly error: string | null;
  readonly onCancel: () => void;
  readonly onConfirm: (userGuidance: string | null) => Promise<void>;
  readonly restoreFocusRef: RefObject<HTMLButtonElement | null>;
}

export function StoryWorkspaceEpisodeContinueDialog({
  actionLabel,
  targetEpisodeLabel = 'EP01',
  canonicalInputs,
  consequences = [],
  busy,
  error,
  onCancel,
  onConfirm,
  restoreFocusRef,
}: StoryWorkspaceEpisodeContinueDialogProps) {
  const [draft, setDraft] = useState('');
  const dialogRef = useRef<HTMLDivElement>(null);
  const guidanceRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const restoreFocusTarget = restoreFocusRef.current;
    guidanceRef.current?.focus();
    return () => restoreFocusTarget?.focus();
  }, [restoreFocusRef]);

  useEffect(() => {
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [busy, onCancel]);

  return (
    <div
      aria-labelledby="story-workspace-episode-continue-dialog-title"
      aria-modal="true"
      className="story-workspace-dream-agent-dialog story-workspace-episode-action-dialog"
      id="story-workspace-episode-continue-dialog"
      ref={dialogRef}
      role="dialog"
    >
      <header className="story-workspace-dream-agent-dialog__header">
        <div>
          <p>Episode 下一步</p>
          <h2 id="story-workspace-episode-continue-dialog-title">确认 Episode 下一步</h2>
          <span>目标 Episode：{targetEpisodeLabel} · {actionLabel}</span>
        </div>
        <button disabled={busy} onClick={onCancel} type="button">取消</button>
      </header>
      <section aria-label="Canonical 输入快照">
        <h3>Canonical 输入与 revisions</h3>
        <ul>
          {canonicalInputs.map((input) => (
            <li key={input.label}>
              <strong>{input.label}</strong>
              <span> · {input.availability}</span>
              <small> · Revision：{input.revision ?? '尚未生成'}</small>
            </li>
          ))}
        </ul>
      </section>
      {consequences.length > 0 && (
        <section aria-label="下游影响">
          <h3>确认后需要更新</h3>
          <ul>{consequences.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}
      <form
        className="story-workspace-dream-agent-dialog__composer"
        onSubmit={(event) => {
          event.preventDefault();
          if (busy) return;
          void onConfirm(storyWorkspaceNormalizeEpisodeGuidance(draft));
        }}
      >
        <label>
          <span>补充创作要求（可选）</span>
          <textarea
            aria-label="补充创作要求（可选）"
            disabled={busy}
            onChange={(event) => setDraft(event.currentTarget.value)}
            placeholder="例如：保留雨夜场景的克制氛围"
            ref={guidanceRef}
            rows={3}
            value={draft}
          />
        </label>
        {error !== null && <p role="alert">{error}</p>}
        <button disabled={busy} type="submit">
          {busy ? '正在交给 Dream Agent…' : '确认并继续'}
        </button>
      </form>
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
  const [episodeContinueDialogOpen, setEpisodeContinueDialogOpen] = useState(false);
  const [selectedEpisodeWorkflowActionId, setSelectedEpisodeWorkflowActionId] =
    useState<string | null>(null);
  const [dreamAgentInitialWorkflowFocus, setDreamAgentInitialWorkflowFocus] =
    useState<{ readonly actionId: string; readonly wasOverflow: boolean } | null>(null);
  const [focusedArtifact, setFocusedArtifact] =
    useState<StoryWorkspaceEpisodeReadableArtifact>('storyboard.yaml');
  const [pendingArtifactReaderFocus, setPendingArtifactReaderFocus] =
    useState<StoryWorkspaceEpisodeReadableArtifact | null>(null);
  const [episodeExpandedKeys, setEpisodeExpandedKeys] =
    useState<ReadonlySet<string>>(() => new Set());
  const [episodeActionBusy, setEpisodeActionBusy] =
    useState<'recover' | 'continue' | null>(null);
  const [episodeActionError, setEpisodeActionError] = useState<string | null>(null);
  const [episodeActionNotice, setEpisodeActionNotice] = useState<string | null>(null);
  const [episodeDispatchedAction, setEpisodeDispatchedAction] =
    useState<StoryWorkspaceEpisodeDispatchedAction | null>(null);
  const episodeDispatchedIdentity = episodeDispatchedAction?.identity ?? null;
  const [episodeActionKeys] = useState(() => new StoryWorkspaceEpisodeActionSessionKeys(
    () => `story-workspace-episode:${globalThis.crypto.randomUUID()}`,
  ));
  const agentPreviewTriggerRef = useRef<HTMLButtonElement>(null);
  const episodeContinueTriggerRef = useRef<HTMLButtonElement>(null);
  const dreamProjectionDetailsRef = useRef<HTMLDetailsElement>(null);
  const episodeArtifactReaderRef = useRef<HTMLDivElement>(null);
  const { run, selectRun } = useWorkflowRun({ eventsEnabled: true });
  const currentRun = run?.workflow_run_id === runId ? run : null;
  const dreamAgent = useStoryWorkspaceDreamAgent(runId);

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
  const canQueryEpisode = files.data !== null
    && storyWorkspaceCanAccessExecution(files.data);
  const episodeArtifacts = useStoryWorkspaceEpisodeArtifacts(
    canQueryEpisode ? runId : null,
  );
  const refreshEpisodeArtifacts = episodeArtifacts.refresh;
  const episodeSurface = episodeArtifacts.data;
  const episodeViewModel = useMemo(
    () => episodeSurface?.bindingAvailability === 'bound'
      ? storyWorkspaceBuildEpisodeExecutionViewModel(episodeSurface)
      : null,
    [episodeSurface],
  );
  const episodeActionFact = episodeSurface?.bindingAvailability === 'bound'
    ? episodeSurface.etag ?? 'bound-without-etag'
    : episodeSurface === null
      ? 'loading'
      : `unbound:${episodeSurface.bindingRecovery.autoRepairAttempted}`;
  const episodeActionName = episodeSurface?.bindingAvailability === 'unbound'
    ? 'recover_first_episode_binding'
    : episodeSurface?.actionProjection?.recommendedActionId
      ?? episodeSurface?.workflow?.nextAction.action
      ?? 'none_in_scope';
  const episodeActionIdentity = `${runId}\u0000${episodeActionFact}\u0000${episodeActionName}`;
  const episodeActionCurrentIdentityRef = useRef(episodeActionIdentity);
  const episodeActionGenerationRef = useRef(0);
  const episodeActionMountedRef = useRef(false);
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

  useLayoutEffect(() => {
    if (episodeActionCurrentIdentityRef.current === episodeActionIdentity) return;
    episodeActionCurrentIdentityRef.current = episodeActionIdentity;
    episodeActionGenerationRef.current += 1;
  }, [episodeActionIdentity]);

  useLayoutEffect(() => {
    episodeActionMountedRef.current = true;
    return () => {
      episodeActionMountedRef.current = false;
      episodeActionGenerationRef.current += 1;
    };
  }, []);

  useEffect(() => {
    setEpisodeActionBusy(null);
    setEpisodeActionError(null);
    setEpisodeActionNotice(null);
    setEpisodeContinueDialogOpen(false);
    setEpisodeDispatchedAction(null);
  }, [episodeActionIdentity]);

  useEffect(() => {
    if (
      episodeDispatchedAction === null
      || episodeDispatchedAction.identity !== episodeActionIdentity
      || !storyWorkspaceDreamAgentHasSettledMessage(
        dreamAgent.snapshot,
        episodeDispatchedAction.messageId,
      )
    ) return;
    episodeActionKeys.rotate(runId, episodeActionFact, episodeActionName);
    setEpisodeDispatchedAction(null);
    setEpisodeActionNotice('本轮结束但尚未检测到新产物；页面会继续读取服务端 revisions。');
    refreshEpisodeArtifacts();
  }, [
    dreamAgent.snapshot,
    episodeActionFact,
    episodeActionIdentity,
    episodeActionKeys,
    episodeActionName,
    refreshEpisodeArtifacts,
    episodeDispatchedAction,
    runId,
  ]);

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
      : '同一 Dream Agent 正在继续';
  const agentPreview = dreamAgent.streamText
    || dreamAgent.snapshot?.messages.filter((message) => message.role === 'assistant').at(-1)?.text
    || agentStateCopy;
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
  const beginEpisodeAction = (): StoryWorkspaceEpisodeActionTicket => {
    if (episodeActionCurrentIdentityRef.current !== episodeActionIdentity) {
      episodeActionCurrentIdentityRef.current = episodeActionIdentity;
      episodeActionGenerationRef.current += 1;
    }
    episodeActionGenerationRef.current += 1;
    return {
      identity: episodeActionIdentity,
      generation: episodeActionGenerationRef.current,
    };
  };
  const episodeActionTicketIsFresh = (ticket: StoryWorkspaceEpisodeActionTicket) => (
    storyWorkspaceEpisodeActionTicketIsFresh(
      ticket,
      episodeActionCurrentIdentityRef.current,
      episodeActionGenerationRef.current,
      episodeActionMountedRef.current,
    )
  );
  const handleEpisodeRecovery = async () => {
    if (
      episodeSurface === null
      || episodeSurface.bindingAvailability !== 'unbound'
      || !episodeSurface.bindingRecovery.canDispatch
      || episodeDispatchedIdentity === episodeActionIdentity
    ) return;
    const action = 'recover_first_episode_binding';
    const idempotencyKey = episodeActionKeys.keyFor(runId, episodeActionFact, action);
    const ticket = beginEpisodeAction();
    setEpisodeActionBusy('recover');
    setEpisodeActionError(null);
    try {
      const accepted = await storyWorkspaceRecoverEpisodeBinding(runId, episodeSurface, {
        idempotencyKey,
        token: getAuthToken(),
      });
      if (!episodeActionTicketIsFresh(ticket)) return;
      setEpisodeDispatchedAction({
        identity: episodeActionIdentity,
        messageId: accepted.messageId,
      });
      setEpisodeActionNotice('已交给同一 Dream Agent；第一集关联将从服务端事实恢复。');
      setDreamAgentInitialWorkflowFocus(null);
      setAgentDialogOpen(true);
      dreamAgent.refresh();
      refreshEpisodeArtifacts();
    } catch {
      if (!episodeActionTicketIsFresh(ticket)) return;
      setEpisodeActionError('第一集关联暂未恢复，页面会继续读取服务端事实。');
    } finally {
      if (episodeActionTicketIsFresh(ticket)) setEpisodeActionBusy(null);
    }
  };
  const recommendedEpisodeWorkflowAction: StoryWorkspaceEpisodeActionOptionV2 | null =
    episodeSurface?.actionProjection?.actionOptions.find(
      (option) => option.actionId === episodeSurface.actionProjection?.recommendedActionId,
    ) ?? null;
  const selectedEpisodeWorkflowAction: StoryWorkspaceEpisodeActionOptionV2 | null =
    episodeSurface?.actionProjection?.actionOptions.find(
      (option) => option.actionId === selectedEpisodeWorkflowActionId,
    ) ?? null;
  const handleEpisodeContinue = async (userGuidance: string | null) => {
    const action = selectedEpisodeWorkflowAction?.action
      ?? episodeSurface?.workflow?.nextAction.action;
    const actionIdentity = selectedEpisodeWorkflowAction?.actionId ?? action;
    if (
      episodeSurface === null
      || episodeSurface.bindingAvailability !== 'bound'
      || action === undefined
      || actionIdentity === undefined
      || storyWorkspaceEpisodeNextActionLabel(action) === null
      || episodeDispatchedIdentity === episodeActionIdentity
    ) return;
    const idempotencyKey = episodeActionKeys.keyFor(runId, episodeActionFact, actionIdentity);
    const ticket = beginEpisodeAction();
    setEpisodeActionBusy('continue');
    setEpisodeActionError(null);
    try {
      const accepted = await storyWorkspaceContinueEpisodeAction(runId, episodeSurface, {
        actionId: selectedEpisodeWorkflowAction?.actionId,
        idempotencyKey,
        token: getAuthToken(),
        userGuidance,
      });
      if (!episodeActionTicketIsFresh(ticket)) return;
      setEpisodeDispatchedAction({
        identity: episodeActionIdentity,
        messageId: accepted.messageId,
      });
      setEpisodeActionNotice('已交给同一 Dream Agent；新产物仍以 REST revisions 到达为准。');
      setEpisodeContinueDialogOpen(false);
      setSelectedEpisodeWorkflowActionId(null);
      setDreamAgentInitialWorkflowFocus(null);
      dreamAgent.refresh();
      refreshEpisodeArtifacts();
    } catch {
      if (!episodeActionTicketIsFresh(ticket)) return;
      setEpisodeActionError('本次继续操作暂未被接受；页面会读取最新工作流事实。');
      refreshEpisodeArtifacts();
    } finally {
      if (episodeActionTicketIsFresh(ticket)) setEpisodeActionBusy(null);
    }
  };
  const selectedEpisodeShot = episodeSelection?.kind === 'shot'
    ? episodeViewModel?.shotsById[episodeSelection.id] ?? null
    : null;
  const nextEpisodeAction = episodeSurface?.workflow?.nextAction ?? null;
  const nextEpisodeActionLabel = nextEpisodeAction === null
    ? null
    : storyWorkspaceEpisodeNextActionLabel(nextEpisodeAction.action);
  const episodeContinueActionLabel = selectedEpisodeWorkflowAction?.label
    ?? recommendedEpisodeWorkflowAction?.label
    ?? nextEpisodeActionLabel;
  const primaryEpisodeActionLabel = recommendedEpisodeWorkflowAction?.label
    ?? nextEpisodeActionLabel;
  const primaryEpisodeActionCanDispatch = recommendedEpisodeWorkflowAction?.canDispatch
    ?? nextEpisodeAction?.canDispatch
    ?? false;
  const episodeActionBlockedByLastGood = episodeArtifacts.isShowingLastGood
    || episodeArtifacts.diagnostic !== null;
  const dreamAgentWorkflowActions: readonly StoryWorkspaceDreamAgentWorkflowActionViewModel[] =
    episodeSurface?.bindingAvailability === 'unbound'
      ? [{
        id: 'recover_first_episode_binding',
        label: '恢复第一集关联',
        displayCommand: '恢复可信 Episode 关联',
        isCurrent: true,
        canDispatch: episodeSurface.bindingRecovery.canDispatch,
        pending: episodeDispatchedIdentity === episodeActionIdentity,
        disabledReason: episodeSurface.bindingRecovery.canDispatch
          ? null
          : '当前没有可恢复的可信 Episode 关联',
      }]
      : episodeSurface?.bindingAvailability === 'bound'
        ? episodeSurface.actionProjection !== null
          && episodeSurface.actionProjection !== undefined
          ? episodeSurface.actionProjection.actionOptions.map((option) => ({
            id: option.actionId,
            label: option.label,
            displayCommand: option.displayCommand,
            description: option.description,
            targetEpisodeLabel: option.targetEpisode.displayLabel,
            availability: option.availability,
            isRecommended: option.isRecommended,
            isCurrent: option.isRecommended,
            canDispatch: option.canDispatch && !episodeActionBlockedByLastGood,
            pending: selectedEpisodeWorkflowActionId === option.actionId
              && episodeActionBusy === 'continue',
            disabledReason: episodeActionBlockedByLastGood && option.canDispatch
              ? '当前正在展示最近一次有效事实，暂不可派发'
              : option.disabledReason,
          }))
          : (episodeSurface.workflow?.actionOptions ?? []).map((option) => ({
            id: option.action,
            label: option.label,
            displayCommand: option.displayCommand,
            isCurrent: option.isCurrent,
            canDispatch: option.canDispatch && !episodeActionBlockedByLastGood,
            pending: option.isCurrent && episodeDispatchedIdentity === episodeActionIdentity,
            disabledReason: option.isCurrent
              ? episodeActionBlockedByLastGood
                ? '当前正在展示最近一次有效事实，暂不可派发'
                : null
              : '完成当前步骤后可用',
          }))
        : [];
  const handleDreamAgentWorkflowAction = (actionId: string) => {
    const action = dreamAgentWorkflowActions.find((candidate) => candidate.id === actionId);
    if (action === undefined || !action.canDispatch || action.pending) return;
    if (action.id === 'recover_first_episode_binding') {
      void handleEpisodeRecovery();
      return;
    }
    if (
      episodeSurface?.actionProjection === null
      || episodeSurface?.actionProjection === undefined
    ) {
      if (action.id !== nextEpisodeAction?.action) return;
    } else if (!episodeSurface.actionProjection.actionOptions.some(
      (option) => option.actionId === action.id && option.canDispatch,
    )) return;
    setEpisodeActionError(null);
    setDreamAgentInitialWorkflowFocus({
      actionId,
      wasOverflow: dreamAgentWorkflowActions.findIndex(
        (candidate) => candidate.id === actionId,
      ) >= 2,
    });
    setSelectedEpisodeWorkflowActionId(action.id);
    setAgentDialogOpen(false);
    setEpisodeContinueDialogOpen(true);
  };
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
          disabled={episodeContinueDialogOpen}
          onClick={() => {
            setDreamAgentInitialWorkflowFocus(null);
            setAgentDialogOpen(true);
          }}
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
      <section aria-label="第一集产物工作台">
        {episodeSurface === null ? (
          <div role="status">
            {episodeArtifacts.diagnostic !== null ? (
              <p>第一集产物来源无效，暂无法读取。</p>
            ) : episodeArtifacts.error !== null ? (
              <p>第一集产物尚未同步，页面会继续读取。</p>
            ) : (
              <p>正在读取第一集产物…</p>
            )}
          </div>
        ) : episodeSurface.bindingAvailability === 'unbound' ? (
          <main aria-labelledby="story-workspace-episode-unbound-title">
            <h2 id="story-workspace-episode-unbound-title">尚未建立可信的第一集关联</h2>
            <p>页面不会猜测 story、Episode 或目录；恢复结果以服务端绑定事实为准。</p>
            {episodeSurface.bindingRecovery.canDispatch && (
              <button
                disabled={
                  episodeActionBusy !== null
                  || episodeDispatchedIdentity === episodeActionIdentity
                }
                onClick={() => void handleEpisodeRecovery()}
                type="button"
              >
                {episodeDispatchedIdentity === episodeActionIdentity
                  ? '已提交关联恢复'
                  : episodeActionBusy === 'recover'
                    ? '正在恢复…'
                    : '恢复第一集关联'}
              </button>
            )}
            {episodeActionError !== null && <p role="alert">{episodeActionError}</p>}
            {episodeActionNotice !== null && <p aria-live="polite">{episodeActionNotice}</p>}
          </main>
        ) : (
          <main aria-labelledby="story-workspace-episode-title">
            <header>
              <p>EP01 · Episode execution</p>
              <h2 id="story-workspace-episode-title">
                {episodeSurface.narrative?.overview.title ?? '第一集'}
              </h2>
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
              <div aria-label="Episode 下一步">
                {primaryEpisodeActionCanDispatch && primaryEpisodeActionLabel !== null ? (
                  <button
                    aria-controls="story-workspace-episode-continue-dialog"
                    aria-expanded={episodeContinueDialogOpen}
                    disabled={
                      episodeActionBusy !== null
                      || episodeActionBlockedByLastGood
                      || episodeDispatchedIdentity === episodeActionIdentity
                    }
                    onClick={() => {
                      setEpisodeActionError(null);
                      setDreamAgentInitialWorkflowFocus(null);
                      setSelectedEpisodeWorkflowActionId(
                        recommendedEpisodeWorkflowAction?.actionId ?? null,
                      );
                      setEpisodeContinueDialogOpen(true);
                    }}
                    ref={episodeContinueTriggerRef}
                    type="button"
                  >
                    {episodeDispatchedIdentity === episodeActionIdentity
                      ? '已交给 Dream Agent'
                      : primaryEpisodeActionLabel}
                  </button>
                ) : (
                  <p>当前没有可派发的下一步，页面会继续读取工作流事实。</p>
                )}
                {nextEpisodeAction?.diagnostic === 'needs_confirmation' && (
                  <small>下一步需要由同一 Dream Agent 结合现有产物确认。</small>
                )}
                {episodeActionError !== null && <p role="alert">{episodeActionError}</p>}
                {episodeActionNotice !== null && <p aria-live="polite">{episodeActionNotice}</p>}
              </div>
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

      {episodeContinueDialogOpen
        && episodeSurface?.bindingAvailability === 'bound'
        && episodeContinueActionLabel !== null && (
        <StoryWorkspaceEpisodeContinueDialog
          actionLabel={episodeContinueActionLabel}
          busy={episodeActionBusy === 'continue'}
          canonicalInputs={selectedEpisodeWorkflowAction === null
            ? storyWorkspaceEpisodeCanonicalInputs(episodeSurface)
            : storyWorkspaceEpisodeOptionCanonicalInputs(selectedEpisodeWorkflowAction)}
          consequences={selectedEpisodeWorkflowAction?.consequences ?? []}
          error={episodeActionError}
          onCancel={() => {
            if (episodeActionBusy === 'continue') return;
            const returnToAgent = dreamAgentInitialWorkflowFocus !== null;
            setEpisodeActionError(null);
            setEpisodeContinueDialogOpen(false);
            setSelectedEpisodeWorkflowActionId(null);
            if (returnToAgent) setAgentDialogOpen(true);
          }}
          onConfirm={(userGuidance) => handleEpisodeContinue(userGuidance)}
          restoreFocusRef={dreamAgentInitialWorkflowFocus === null
            ? episodeContinueTriggerRef
            : agentPreviewTriggerRef}
          targetEpisodeLabel={selectedEpisodeWorkflowAction?.targetEpisode.displayLabel ?? 'EP01'}
        />
      )}

      {agentDialogOpen && (
        <StoryWorkspaceDreamAgentDialog
          agent={dreamAgent}
          deckName={currentRun?.deck_plugin_display_name ?? '当前 Deck'}
          initialWorkflowFocus={dreamAgentInitialWorkflowFocus}
          onRequestWorkflowAction={handleDreamAgentWorkflowAction}
          onClose={() => setAgentDialogOpen(false)}
          restoreFocusRef={agentPreviewTriggerRef}
          runId={runId}
          workflowActions={dreamAgentWorkflowActions}
        />
      )}
    </section>
  );
}
