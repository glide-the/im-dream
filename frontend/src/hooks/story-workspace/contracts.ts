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
  stage: StoryWorkspaceDreamStage;
  entityId: string;
  fields: Readonly<Record<string, StoryWorkspaceDreamFieldValue>>;
}

/** Request body of the run-scoped Dream single-confirmation endpoint. */
export interface StoryWorkspaceDreamConfirmationCommand {
  storyWorkspaceRunId: string;
  threadId: string;
  baseRevisions: Readonly<Record<StoryWorkspaceDreamStage, number>>;
  edits: readonly StoryWorkspaceDreamConfirmationEdit[];
  idempotencyKey: string;
}

/**
 * The six Gate / run stages of design_004 §4.2. This value is produced by
 * server-side aggregation ("proposal review status + story-workspace run
 * status"); the frontend must never derive it from local data.
 */
export type StoryWorkspaceSurfaceLinkStage =
  | 'pending_review'
  | 'confirmed'
  | 'continuing'
  | 'completed'
  | 'failed'
  | 'rejected';

/**
 * Server-aggregated button state for StoryWorkspaceSurfaceLinkButton
 * (design_004 §4.1). `superseded` marks a proposal whose attempt was replaced
 * by a newer run (retryOfRunId chain); `latestRunId` points at that newest
 * run for the "查看最新版本" degradation target (§4.4).
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

/** One step of the run's execution facts projection (§5.2 任务进度). */
export interface StoryWorkspaceExecutionStep {
  name?: string;
  status?: string;
  /** Blocked steps mark the awaiting-guidance projection state (D13). */
  blocked?: boolean;
  duration_seconds?: number | null;
  failure_reason?: string | null;
  retry_count?: number | null;
}

/** One event of the run's execution timeline (§5.2 运行记录). */
export interface StoryWorkspaceExecutionEvent {
  type?: string;
  occurred_at?: string | null;
  summary?: string | null;
}

/**
 * Read-side execution facts projection (StoryWorkspaceExecutionProjection,
 * Task 3). `phase` may carry projection states such as `awaiting-guidance` —
 * inferred from `continuing` plus blocked-step markers — which are NOT
 * RunStatus values (audit note D13). No projection endpoint exists yet; the
 * execution page accepts this as an optional injection seam and degrades
 * gracefully when it is absent.
 */
export interface StoryWorkspaceExecutionProjection {
  run_id: string;
  phase: string;
  steps: StoryWorkspaceExecutionStep[];
  assets_ref: string | null;
  events: StoryWorkspaceExecutionEvent[];
}

/**
 * The execution page UI states (design_004 §5.4). `awaiting-guidance` is a
 * projection state; `cancelled` is a post-Gate terminal state the §5.4 table
 * does not enumerate (handled as its own terminal notice, documented in the
 * Task 5 record).
 */
export type StoryWorkspaceExecutionPageState =
  | 'continuing'
  | 'awaiting-guidance'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'not-confirmed';

/**
 * One guidance history entry for the sidebar (§5.3 指导历史), reverse-looked
 * from chat_message rows carrying metadata.kind="story-workspace-guidance".
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
