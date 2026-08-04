export type StoryWorkspaceReviewStatus = 'pending' | 'confirmed' | 'rejected' | 'archived';

export type StoryWorkspaceSortOrder = 'asc' | 'desc';

export interface StoryWorkspacePaginationData {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface StoryWorkspaceListResponse<T> {
  data: T[];
  pagination: StoryWorkspacePaginationData;
}

export interface StoryWorkspaceListQuery {
  q?: string;
  reviewStatus?: StoryWorkspaceReviewStatus[];
  sort?: string;
  order?: StoryWorkspaceSortOrder;
  page?: number;
  perPage?: number;
}

export interface StoryWorkspaceStoryQuery extends StoryWorkspaceListQuery {
  type?: StoryWorkspaceStoryType[];
}

export interface StoryWorkspaceSceneQuery extends StoryWorkspaceListQuery {
  storyId?: string;
}

export type StoryWorkspaceStoryType = 'short' | 'long' | 'script' | 'outline';

export interface StoryWorkspaceStory {
  id: string;
  identifier: string;
  title: string;
  description: string | null;
  status: 'draft' | 'published' | 'archived';
  review_status: StoryWorkspaceReviewStatus;
  type: StoryWorkspaceStoryType;
  character_count: number;
  scene_count: number;
  created_at: string;
  updated_at: string;
  confirmed_at: string | null;
}

export interface StoryWorkspaceCharacter {
  id: string;
  identifier: string;
  name: string;
  avatar_url: string | null;
  identity: string | null;
  personality: string | null;
  tags: string[];
  story_count: number;
  review_status: StoryWorkspaceReviewStatus;
  created_at: string;
  updated_at: string;
}

export interface StoryWorkspaceScene {
  id: string;
  identifier: string;
  name: string;
  description: string | null;
  story_id: string | null;
  character_count: number;
  order_index: number;
  review_status: StoryWorkspaceReviewStatus;
  created_at: string;
  updated_at: string;
}

/**
 * A workspace surface declared by a Deck plugin's workspace-init profile and
 * materialized by the packer (e.g. the dream surface with its `.dream/`
 * protocol directory). Surfaced to the frontend via the existing
 * plugin-load-receipt endpoint's whole-file passthrough (DEC-026/028).
 */
export interface StoryWorkspaceSurface {
  name: string;
  protocol_dir: string;
  entry_route: string;
}

/**
 * Response of GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt.
 * `receipt` / `launch_manifest` are whole-file passthroughs and may be null
 * (pre-pack window) or lack the `surfaces` key entirely (legacy sessions).
 */
export interface StoryWorkspacePluginLoadReceiptResponse {
  thread_id: string;
  deck_id: string | null;
  workspace_found: boolean;
  receipt: { surfaces?: StoryWorkspaceSurface[] } | null;
  launch_manifest: { surfaces?: StoryWorkspaceSurface[] } | null;
}

/* --------------------------------------------------------------------------
 * Dream file + single-confirmation contracts (design_006 §4/§7, DEC-026).
 * State-only hydration models stay in the pure Dream seam; the command sent
 * to POST .../dream-confirmation is owned here and nowhere else.
 * ------------------------------------------------------------------------ */

export type StoryWorkspaceDreamStage = 'characters' | 'scenes' | 'storyboards';

export type StoryWorkspaceDreamFieldValue =
  | string
  | number
  | boolean
  | null
  | readonly StoryWorkspaceDreamFieldValue[]
  | { readonly [key: string]: StoryWorkspaceDreamFieldValue };

export interface StoryWorkspaceDreamConfirmationEdit {
  readonly stage: StoryWorkspaceDreamStage;
  readonly entityId: string;
  readonly fields: Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
}

/** Request body of the run-scoped Dream single-confirmation endpoint. */
export interface StoryWorkspaceDreamConfirmationCommand {
  readonly storyWorkspaceRunId: string;
  readonly threadId: string;
  readonly baseRevisions: Readonly<Record<StoryWorkspaceDreamStage, number>>;
  readonly edits: readonly StoryWorkspaceDreamConfirmationEdit[];
  readonly idempotencyKey: string;
}

/** 202 response after the hidden confirmation row is durably accepted. */
export interface StoryWorkspaceDreamConfirmationAccepted {
  readonly messageId: string;
  readonly storyWorkspaceRunId: string;
  readonly threadId: string;
  readonly status: 'accepted';
  readonly replayed: boolean;
  readonly dispatched: boolean;
  readonly requestId: string;
}

/** Frozen WorkflowRun provenance returned by the Dream file read endpoint. */
export interface StoryWorkspaceDreamSource {
  readonly deckPluginBindingId: string;
  readonly bindingRevision: number;
  readonly deckPluginVersion: string;
  readonly deckRuntimeSnapshotId: string;
  readonly runtimePluginLockId: string;
}

export interface StoryWorkspaceDreamStagePage {
  readonly title: string;
  readonly entryRoute: string;
}

export interface StoryWorkspaceDreamStageItem {
  readonly entityId: string;
  readonly displayName: string;
  readonly summary: string | null;
  readonly sourceFile: string;
  readonly relations: readonly string[];
}

export interface StoryWorkspaceDreamStageProjection {
  readonly stage: StoryWorkspaceDreamStage;
  readonly revision: number;
  readonly sourceFiles: readonly string[];
  readonly page: StoryWorkspaceDreamStagePage;
  readonly items: readonly StoryWorkspaceDreamStageItem[];
}

/**
 * Response of GET /api/story-workspace/workflow-runs/{runId}/dream-files.
 * A missing run.json is represented by runRevision=0 and an empty stages map;
 * it is a normal "waiting for Agent files" projection, not an error state.
 */
export interface StoryWorkspaceDreamFilesResponse {
  readonly storyWorkspaceRunId: string;
  readonly threadId: string;
  readonly source: StoryWorkspaceDreamSource;
  readonly requiredStages: readonly StoryWorkspaceDreamStage[];
  readonly runRevision: number;
  readonly stages: Readonly<Partial<Record<
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageProjection
  >>>;
  readonly canConfirm: boolean;
  readonly confirmationLabel: '确认并继续';
}

/** Dream's only page lifecycle; it intentionally has no rejection/failure arm. */
export type StoryWorkspaceDreamLifecycleState =
  | 'story-workspace-dream-waiting-files'
  | 'story-workspace-dream-editing'
  | 'story-workspace-dream-confirming'
  | 'story-workspace-dream-continuing'
  | 'story-workspace-dream-completed';

/**
 * Server aggregate compatibility stages. The Dream UI exposes lifecycle
 * links for pending_review/confirmed/continuing/completed only; the two
 * legacy branches remain accepted as transport values but render no action.
 */
export type StoryWorkspaceSurfaceLinkStage =
  | 'pending_review'
  | 'confirmed'
  | 'continuing'
  | 'completed'
  | 'failed'
  | 'rejected';

/**
 * Server-aggregated button state for StoryWorkspaceSurfaceLinkButton.
 * Replaced-attempt fields remain for compatibility and intentionally resolve
 * to a hidden Dream entry under design_007.
 */
export interface StoryWorkspaceSurfaceLinkState {
  stage: StoryWorkspaceSurfaceLinkStage;
  superseded?: boolean;
  latestRunId?: string | null;
}

export interface StoryWorkspaceListState<T> {
  data: T[];
  pagination: StoryWorkspacePaginationData;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

/* --------------------------------------------------------------------------
 * Task 5 — standalone execution page contracts (design_004 §5/§6, DEC-026).
 * These mirror the backend canonical contracts in
 * backend/story_workspace/contracts.py (Task 3); no other frontend path may
 * carry them.
 * ------------------------------------------------------------------------ */

/** Guidance command kinds accepted by POST /api/story-workspace/runs/{id}/guidance. */
export type StoryWorkspaceGuidanceKind = 'retry-step' | 'free-text';

/** Request body of the guidance endpoint (StoryWorkspaceGuidanceCommandPayload). */
export interface StoryWorkspaceGuidanceCommandPayload {
  kind: StoryWorkspaceGuidanceKind;
  /** Required for free-text (non-blank, ≤4000); optional note for retry-step. */
  text?: string;
  /** Required for retry-step. */
  step_id?: string;
  /** Client-generated idempotency key (≤255); message id = guide_<key>. */
  idempotency_key: string;
  /** Must equal the authenticated user id (server enforces, mismatch → 403). */
  actor: string;
}

/**
 * 202 response of the guidance endpoint. `dispatched: false` means the chat
 * thread had an in-flight turn: the guidance row is persisted and waits for
 * the executing Agent to pick it up on the next turn ("已记录待拾取").
 */
export interface StoryWorkspaceGuidanceAccepted {
  message_id: string;
  story_workspace_run_id: string;
  review_action: string;
  status: string;
  replayed: boolean;
  dispatched: boolean;
  request_id: string | null;
}

/**
 * One historical guidance audit entry, reverse-looked from chat_message rows
 * carrying metadata.kind="story-workspace-guidance". The API remains for
 * compatibility; Dream's file-driven execution page does not render it.
 */
export interface StoryWorkspaceGuidanceHistoryEntry {
  messageId: string;
  createdAt: string | null;
  commandKind: string | null;
  stepId: string | null;
  textSummary: string | null;
  requestId: string | null;
  idempotencyKey: string | null;
}
