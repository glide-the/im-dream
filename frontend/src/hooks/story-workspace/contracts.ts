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
 * Dream launch + file + single-confirmation contracts (design_006 §4/§7,
 * DEC-026). The launch command is the complete client-authored surface;
 * thread/run provenance is returned by the server and cannot be supplied by
 * the browser.
 * State-only hydration models stay in the pure Dream seam; the command sent
 * to POST .../dream-confirmation is owned here and nowhere else.
 * ------------------------------------------------------------------------ */

/** Request body of POST /api/story-workspace/dream-runs/start. */
export interface StoryWorkspaceDreamLaunchCommand {
  readonly deckId: string;
  readonly agentId: string;
  readonly goal: string;
  readonly idempotencyKey: string;
}

/** Trusted identifiers returned after the server creates and dispatches a Dream run. */
export interface StoryWorkspaceDreamLaunchAccepted {
  readonly workflowRunId: string;
  readonly threadId: string;
}

/** One durable, actor-scoped run row rendered by Dream's canonical workbench. */
export interface StoryWorkspaceDreamReentryItem {
  readonly storyWorkspaceRunId: string;
  readonly goalPrefix: string;
  readonly deckId: string;
  readonly deckDisplayName: string;
  readonly workflowDisplayName: 'Dream';
  readonly deckPluginVersion: string;
  readonly lifecycle: 'generating' | 'waiting_confirmation' | 'continuing' | 'recent';
  readonly group: 'in_progress' | 'recent';
  readonly stageRevisions: Readonly<Partial<Record<StoryWorkspaceDreamStage, number>>>;
  readonly confirmationAccepted: boolean;
  readonly confirmationDispatched: boolean;
  readonly lastActivityAt: string;
  readonly createdAt: string;
  /** Server-owned stable ordering evidence. The UI must not recompute it. */
  readonly sortKey: string;
  readonly href: string;
}

/** Response of GET /api/story-workspace/dream-runs. */
export interface StoryWorkspaceDreamReentryCollection {
  readonly runs: readonly StoryWorkspaceDreamReentryItem[];
}

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
  /** Durable audit fact: the one Dream confirmation command was accepted. */
  readonly confirmationAccepted: boolean;
  /** Durable completion fact: the same Chat Agent turn stream was consumed successfully. */
  readonly confirmationDispatched: boolean;
  readonly canConfirm: boolean;
  readonly confirmationLabel: '确认并继续';
}

export type StoryWorkspaceDreamAgentActivityCategory =
  | 'workspace_read'
  | 'dream_write'
  | 'reference_lookup'
  | 'delegation'
  | 'other';

export interface StoryWorkspaceDreamAgentTextContent {
  readonly kind: 'text';
  readonly text: string;
  readonly truncated: boolean;
}

export interface StoryWorkspaceDreamAgentActivityContent {
  readonly kind: 'activity';
  readonly id: string;
  readonly category: StoryWorkspaceDreamAgentActivityCategory;
  readonly label: '读取工作区资料' | '更新 Dream 内容' | '查找参考资料' | '协同处理创作任务' | '处理 Dream 创作任务';
  readonly status: 'running' | 'completed' | 'stopped';
}

export type StoryWorkspaceDreamAgentContent =
  | StoryWorkspaceDreamAgentTextContent
  | StoryWorkspaceDreamAgentActivityContent;

/** Safe message rendered by the Dream Agent workbench. */
export interface StoryWorkspaceDreamAgentMessage {
  readonly id: string;
  readonly role: 'user' | 'assistant';
  readonly text: string;
  readonly truncated: boolean;
  readonly content: readonly StoryWorkspaceDreamAgentContent[];
  readonly createdAt: string;
}

/** Persisted Dream Agent history plus the server-owned send gate. */
export interface StoryWorkspaceDreamAgentMessageSnapshot {
  readonly storyWorkspaceRunId: string;
  readonly lifecycle: 'idle' | 'streaming';
  readonly activeTurnId: string | null;
  readonly canSend: boolean;
  readonly sendBlockReason: 'generating' | 'waiting_confirmation' | 'confirming' | 'continuing' | 'busy' | null;
  readonly messages: readonly StoryWorkspaceDreamAgentMessage[];
  readonly snapshotAt: string;
}

/** The browser submits only text and its idempotency key; all binding stays server-side. */
export interface StoryWorkspaceDreamAgentMessageCommand {
  readonly text: string;
  readonly idempotencyKey: string;
}

export interface StoryWorkspaceDreamAgentMessageAccepted {
  readonly storyWorkspaceRunId: string;
  readonly messageId: string;
  readonly accepted: true;
}

/** User-facing, server-allowlisted description of one pending Dream Agent tool decision. */
export interface StoryWorkspaceDreamAgentToolConfirmationOption {
  readonly label: string;
  readonly value: string;
  readonly description?: string;
}

export interface StoryWorkspaceDreamAgentToolConfirmationQuestion {
  readonly id: string;
  readonly question: string;
  readonly type: 'text' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'number';
  readonly required: boolean;
  readonly multiSelect?: boolean;
  readonly options?: readonly StoryWorkspaceDreamAgentToolConfirmationOption[];
  readonly placeholder?: string;
}

export interface StoryWorkspaceDreamAgentToolConfirmation {
  readonly toolCallId: string;
  readonly kind: 'approval' | 'ask_user' | 'sandbox_network';
  readonly toolName: string;
  readonly title?: string;
  readonly questions?: readonly StoryWorkspaceDreamAgentToolConfirmationQuestion[];
  readonly network?: {
    readonly host: string | null;
    readonly policy: 'allowlist' | 'open' | 'deny' | 'unknown';
  };
}

/** Run-scoped browser command; thread and Deck binding remain server-owned. */
export interface StoryWorkspaceDreamAgentToolConfirmationCommand {
  readonly toolCallId: string;
  readonly approved: boolean;
  readonly reason?: string;
  readonly answers?: Readonly<Record<string, unknown>>;
}

export interface StoryWorkspaceDreamAgentToolConfirmationResolved {
  readonly storyWorkspaceRunId: string;
  readonly toolCallId: string;
  readonly resolved: true;
}

/** Allowlisted event surface emitted by the Story Workspace Dream SSE adapter. */
export type StoryWorkspaceDreamAgentEvent =
  | { readonly type: 'assistant_text_delta'; readonly cursor: string; readonly turnId: string; readonly delta: string }
  | { readonly type: 'agent_activity_started'; readonly cursor: string; readonly turnId: string; readonly activity: StoryWorkspaceDreamAgentActivityContent }
  | { readonly type: 'agent_activity_finished'; readonly cursor: string; readonly turnId: string; readonly activity: StoryWorkspaceDreamAgentActivityContent }
  | { readonly type: 'assistant_message_committed'; readonly turnId: string }
  | { readonly type: 'tool_confirmation_requested'; readonly cursor: string; readonly turnId: string; readonly confirmation: StoryWorkspaceDreamAgentToolConfirmation }
  | { readonly type: 'tool_confirmation_resolved'; readonly cursor: string; readonly turnId: string; readonly toolCallId: string }
  | { readonly type: 'status'; readonly lifecycle: 'idle' | 'streaming' };

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

/* --------------------------------------------------------------------------
 * U5 — Episode artifact read surface (design_009 §§4, 16–17, 20).
 * This is the strict camelCase browser boundary for the backend's
 * StoryWorkspaceEpisodeArtifactSurface. Canonical files remain the content
 * owners; these values are read-only projections.
 * ------------------------------------------------------------------------ */

export type StoryWorkspaceEpisodeBindingAvailability = 'bound' | 'unbound';
export type StoryWorkspaceEpisodeBindingPublicReason = 'episode_binding_unproven';
export type StoryWorkspaceEpisodeArtifactAvailability =
  | 'not_generated'
  | 'available'
  | 'invalid'
  | 'unavailable';
export type StoryWorkspaceEpisodeProducerAction =
  | 'plan_episode'
  | 'write_script'
  | 'review_script'
  | 'build_assets'
  | 'regenerate_storyboard'
  | 'generate_prompts'
  | 'review_full_chain'
  | 'commit_episode'
  | 'prepare_render_guide';
export type StoryWorkspaceEpisodeArtifactConsumer =
  | 'episode_overview'
  | 'storyline_navigator'
  | 'narrative_workbench'
  | 'shot_inspector'
  | 'prompt_view'
  | 'render_view'
  | 'review_view';
export type StoryWorkspaceEpisodeAssociationStatus = 'linked' | 'unlinked' | 'orphan';
export type StoryWorkspaceEpisodeMetricAvailability = 'available' | 'unavailable';
export type StoryWorkspaceEpisodeReviewScope = 'script' | 'full-chain' | 'unknown';

export interface StoryWorkspaceEpisodeBindingRecovery {
  readonly autoRepairAttempted: boolean;
  readonly canDispatch: boolean;
  readonly publicReason: StoryWorkspaceEpisodeBindingPublicReason | null;
}

export interface StoryWorkspaceEpisodeArtifactManifestEntry {
  readonly relativeKey: string;
  readonly availability: StoryWorkspaceEpisodeArtifactAvailability;
  readonly contentRevision: string | null;
  readonly mtime: string | null;
  readonly size: number | null;
  readonly producerAction: StoryWorkspaceEpisodeProducerAction;
  readonly consumers: readonly StoryWorkspaceEpisodeArtifactConsumer[];
}

export interface StoryWorkspaceEpisodeAssociationCoverage {
  readonly availability: StoryWorkspaceEpisodeMetricAvailability;
  readonly linked: number;
  readonly total: number;
  readonly ratio: number | null;
}

export interface StoryWorkspaceEpisodeCharacterBeat {
  readonly id: string;
  readonly sourceKey: string;
  readonly characterId: string | null;
  readonly action: string | null;
  readonly startState: string | null;
  readonly trigger: string | null;
  readonly choice: string | null;
  readonly endState: string | null;
  readonly visibleEvidence: string | null;
}

export interface StoryWorkspaceEpisodeOverview {
  readonly title: string | null;
  readonly series: string | null;
  readonly storyGoals: readonly string[];
  readonly coreConflict: string | null;
  readonly hook: string | null;
  readonly sourceArtifact: 'episode-outline.md' | null;
  readonly sourceRevision: string | null;
  readonly generatedFrom: string | null;
  readonly characterBeats: readonly StoryWorkspaceEpisodeCharacterBeat[];
}

export interface StoryWorkspaceEpisodeNarrativeBeat {
  readonly id: string;
  readonly sourceKey: string;
  readonly title: string;
  readonly assetSceneRef: string | null;
  readonly narrativeFunction: string | null;
  readonly emotionTone: string | null;
  readonly summary: string | null;
  readonly sceneGoals: readonly string[];
  readonly keyDialogueBeats: readonly string[];
  readonly sourceArtifact: 'episode-outline.md';
  readonly sourceRevision: string | null;
  readonly generatedFrom: string | null;
}

export interface StoryWorkspaceEpisodeDialogueLine {
  readonly speaker: string;
  readonly qualifier: string | null;
  readonly text: string;
}

export interface StoryWorkspaceEpisodeScriptScene {
  readonly id: string;
  readonly sourceKey: string;
  readonly title: string;
  readonly heading: string;
  readonly assetSceneRef: string | null;
  readonly narrativeBeatId: string | null;
  readonly declaredNarrativeBeatRef: string | null;
  readonly associationStatus: StoryWorkspaceEpisodeAssociationStatus;
  readonly actions: readonly string[];
  readonly dialogue: readonly StoryWorkspaceEpisodeDialogueLine[];
  readonly cameraCues: readonly string[];
  readonly sourceArtifact: 'script.md';
  readonly sourceRevision: string | null;
  readonly generatedFrom: string | null;
}

export interface StoryWorkspaceEpisodeShotCharacter {
  readonly ref: string;
  readonly displayName: string | null;
  readonly depthPlane: 'front' | 'mid' | 'back' | null;
  readonly action: string | null;
  readonly emotion: string | null;
}

export interface StoryWorkspaceEpisodeStoryboardDialogue {
  readonly speaker: string;
  readonly line: string;
  readonly type: 'spoken' | 'voiceover' | 'os' | 'inner';
}

export interface StoryWorkspaceEpisodeShotCamera {
  readonly angle: string | null;
  readonly height: string | null;
  readonly movement: string | null;
  readonly lens: string | null;
}

export interface StoryWorkspaceEpisodeShotTiming {
  readonly durationSec: number | null;
  readonly transitionIn: string | null;
  readonly transitionOut: string | null;
}

export interface StoryWorkspaceEpisodeStoryboardShot {
  readonly id: string;
  readonly shotId: string;
  readonly assetSceneRef: string | null;
  readonly declaredScriptSceneRef: string | null;
  readonly declaredNarrativeBeatRef: string | null;
  readonly scriptSceneId: string | null;
  readonly narrativeBeatId: string | null;
  readonly associationStatus: StoryWorkspaceEpisodeAssociationStatus;
  readonly shotType: string | null;
  readonly characters: readonly StoryWorkspaceEpisodeShotCharacter[];
  readonly camera: StoryWorkspaceEpisodeShotCamera;
  readonly visual: string | null;
  readonly dialogue: readonly StoryWorkspaceEpisodeStoryboardDialogue[];
  readonly timing: StoryWorkspaceEpisodeShotTiming;
  readonly sourceArtifact: 'storyboard.yaml';
  readonly sourceRevision: string | null;
  readonly generatedFrom: string | null;
}

export interface StoryWorkspaceEpisodeAssociationDiagnostics {
  readonly beatSceneCoverage: StoryWorkspaceEpisodeAssociationCoverage;
  readonly sceneShotCoverage: StoryWorkspaceEpisodeAssociationCoverage;
  readonly missingLinks: readonly string[];
  readonly orphanArtifacts: readonly string[];
}

export interface StoryWorkspaceEpisodeNarrativeProjection {
  readonly episodeId: string;
  readonly storyArcId: string;
  readonly overview: StoryWorkspaceEpisodeOverview;
  readonly narrativeBeats: readonly StoryWorkspaceEpisodeNarrativeBeat[];
  readonly scenes: readonly StoryWorkspaceEpisodeScriptScene[];
  readonly shots: readonly StoryWorkspaceEpisodeStoryboardShot[];
  readonly associations: StoryWorkspaceEpisodeAssociationDiagnostics;
}

export interface StoryWorkspaceEpisodePromptParameters {
  readonly model: string | null;
  readonly mode: string | null;
  readonly durationSec: number | null;
  readonly motionStrength: number | null;
  readonly cameraMotion: string | null;
  readonly aspectRatio: string | null;
}

export interface StoryWorkspaceEpisodePromptGenerability {
  readonly characterAnchor: string | null;
  readonly motionFeasibility: string | null;
  readonly durationBudget: string | null;
  readonly notes: string | null;
}

export interface StoryWorkspaceEpisodePrompt {
  readonly id: string;
  readonly shotId: string;
  readonly kind: string;
  readonly shotViewId: string | null;
  readonly associationStatus: StoryWorkspaceEpisodeAssociationStatus;
  readonly positive: string;
  readonly negative: string | null;
  readonly parameters: StoryWorkspaceEpisodePromptParameters;
  readonly generability: StoryWorkspaceEpisodePromptGenerability;
  readonly sourceArtifact: string;
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodePromptPage {
  readonly items: readonly StoryWorkspaceEpisodePrompt[];
  readonly total: number;
  readonly nextCursor: string | null;
}

export interface StoryWorkspaceEpisodeArtifactSection {
  readonly id: string;
  readonly level: number;
  readonly title: string;
  readonly text: string;
  readonly sourceArtifact: 'renders/render-guide.md' | 'review-report.md';
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodeRenderQueueEntry {
  readonly id: string;
  readonly shotId: string;
  readonly shotViewId: string | null;
  readonly associationStatus: StoryWorkspaceEpisodeAssociationStatus;
  readonly durationSec: number | null;
  readonly risk: string | null;
  readonly priority: string | null;
  readonly renderer: string | null;
  readonly status: string | null;
  readonly sourceArtifact: 'renders/render-guide.md';
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodeRenderQueuePage {
  readonly items: readonly StoryWorkspaceEpisodeRenderQueueEntry[];
  readonly total: number;
  readonly nextCursor: string | null;
}

export interface StoryWorkspaceEpisodeRenderGuide {
  readonly sections: readonly StoryWorkspaceEpisodeArtifactSection[];
  readonly queue: StoryWorkspaceEpisodeRenderQueuePage;
  readonly sourceArtifact: 'renders/render-guide.md';
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodeReviewTarget {
  readonly id: string;
  readonly kind: 'narrative-beat' | 'script-scene' | 'shot';
  readonly sourceKey: string;
  readonly targetViewId: string | null;
  readonly associationStatus: StoryWorkspaceEpisodeAssociationStatus;
  readonly sectionId: string;
  readonly sourceArtifact: 'review-report.md';
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodeReviewedSourceRevision {
  readonly sourceArtifact: string;
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodeReviewReport {
  readonly scope: StoryWorkspaceEpisodeReviewScope;
  readonly overallVerdict: string | null;
  readonly reviewedArtifacts: readonly string[];
  readonly sourceRevisions: readonly StoryWorkspaceEpisodeReviewedSourceRevision[];
  readonly sections: readonly StoryWorkspaceEpisodeArtifactSection[];
  readonly targets: readonly StoryWorkspaceEpisodeReviewTarget[];
  readonly sourceArtifact: 'review-report.md';
  readonly sourceRevision: string;
}

export interface StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics {
  readonly shotPromptCoverage: StoryWorkspaceEpisodeAssociationCoverage;
  readonly shotRenderQueueCoverage: StoryWorkspaceEpisodeAssociationCoverage;
  readonly totalPrompts: number;
  readonly totalQueueEntries: number;
  readonly orphanPrompts: readonly string[];
  readonly orphanQueueEntries: readonly string[];
  readonly duplicateQueueShotIds: readonly string[];
}

export interface StoryWorkspaceEpisodeAuxiliaryProjection {
  readonly manifestRevision: string;
  readonly prompts: StoryWorkspaceEpisodePromptPage;
  readonly renderGuide: StoryWorkspaceEpisodeRenderGuide | null;
  readonly review: StoryWorkspaceEpisodeReviewReport | null;
  readonly associations: StoryWorkspaceEpisodeAuxiliaryAssociationDiagnostics;
}

/** GET /api/story-workspace/workflow-runs/{runId}/episode-artifacts. */
export interface StoryWorkspaceEpisodeArtifactSurface {
  readonly runId: string;
  readonly opaqueEpisodeId: string | null;
  readonly manifestRevision: string | null;
  readonly etag: string | null;
  readonly bindingAvailability: StoryWorkspaceEpisodeBindingAvailability;
  readonly bindingRecovery: StoryWorkspaceEpisodeBindingRecovery;
  readonly artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly narrative: StoryWorkspaceEpisodeNarrativeProjection | null;
  readonly auxiliary: StoryWorkspaceEpisodeAuxiliaryProjection | null;
}

export type StoryWorkspaceEpisodeStringFieldClass =
  | 'machine_enum_or_pattern'
  | 'canonical_relative_key'
  | 'public_text'
  | 'diagnostic';

/** Exhaustive trust class for every string/string[] field in the Episode wire DTO. */
export const storyWorkspaceEpisodeStringFieldClassification = {
  'surface.runId': 'machine_enum_or_pattern',
  'surface.opaqueEpisodeId': 'machine_enum_or_pattern',
  'surface.manifestRevision': 'machine_enum_or_pattern',
  'surface.etag': 'machine_enum_or_pattern',
  'surface.bindingAvailability': 'machine_enum_or_pattern',
  'bindingRecovery.publicReason': 'machine_enum_or_pattern',
  'artifacts[].relativeKey': 'canonical_relative_key',
  'artifacts[].availability': 'machine_enum_or_pattern',
  'artifacts[].contentRevision': 'machine_enum_or_pattern',
  'artifacts[].mtime': 'machine_enum_or_pattern',
  'artifacts[].producerAction': 'machine_enum_or_pattern',
  'artifacts[].consumers[]': 'machine_enum_or_pattern',
  'coverage.availability': 'machine_enum_or_pattern',
  'narrative.episodeId': 'machine_enum_or_pattern',
  'narrative.storyArcId': 'machine_enum_or_pattern',
  'narrative.overview.title': 'public_text',
  'narrative.overview.series': 'public_text',
  'narrative.overview.storyGoals[]': 'public_text',
  'narrative.overview.coreConflict': 'public_text',
  'narrative.overview.hook': 'public_text',
  'narrative.overview.sourceArtifact': 'canonical_relative_key',
  'narrative.overview.sourceRevision': 'machine_enum_or_pattern',
  'narrative.overview.generatedFrom': 'machine_enum_or_pattern',
  'narrative.overview.characterBeats[].id': 'machine_enum_or_pattern',
  'narrative.overview.characterBeats[].sourceKey': 'machine_enum_or_pattern',
  'narrative.overview.characterBeats[].characterId': 'machine_enum_or_pattern',
  'narrative.overview.characterBeats[].action': 'public_text',
  'narrative.overview.characterBeats[].startState': 'public_text',
  'narrative.overview.characterBeats[].trigger': 'public_text',
  'narrative.overview.characterBeats[].choice': 'public_text',
  'narrative.overview.characterBeats[].endState': 'public_text',
  'narrative.overview.characterBeats[].visibleEvidence': 'public_text',
  'narrative.narrativeBeats[].id': 'machine_enum_or_pattern',
  'narrative.narrativeBeats[].sourceKey': 'machine_enum_or_pattern',
  'narrative.narrativeBeats[].title': 'public_text',
  'narrative.narrativeBeats[].assetSceneRef': 'machine_enum_or_pattern',
  'narrative.narrativeBeats[].narrativeFunction': 'public_text',
  'narrative.narrativeBeats[].emotionTone': 'public_text',
  'narrative.narrativeBeats[].summary': 'public_text',
  'narrative.narrativeBeats[].sceneGoals[]': 'public_text',
  'narrative.narrativeBeats[].keyDialogueBeats[]': 'public_text',
  'narrative.narrativeBeats[].sourceArtifact': 'canonical_relative_key',
  'narrative.narrativeBeats[].sourceRevision': 'machine_enum_or_pattern',
  'narrative.narrativeBeats[].generatedFrom': 'machine_enum_or_pattern',
  'narrative.scenes[].id': 'machine_enum_or_pattern',
  'narrative.scenes[].sourceKey': 'machine_enum_or_pattern',
  'narrative.scenes[].title': 'public_text',
  'narrative.scenes[].heading': 'public_text',
  'narrative.scenes[].assetSceneRef': 'machine_enum_or_pattern',
  'narrative.scenes[].narrativeBeatId': 'machine_enum_or_pattern',
  'narrative.scenes[].declaredNarrativeBeatRef': 'machine_enum_or_pattern',
  'narrative.scenes[].associationStatus': 'machine_enum_or_pattern',
  'narrative.scenes[].actions[]': 'public_text',
  'narrative.scenes[].dialogue[].speaker': 'public_text',
  'narrative.scenes[].dialogue[].qualifier': 'public_text',
  'narrative.scenes[].dialogue[].text': 'public_text',
  'narrative.scenes[].cameraCues[]': 'public_text',
  'narrative.scenes[].sourceArtifact': 'canonical_relative_key',
  'narrative.scenes[].sourceRevision': 'machine_enum_or_pattern',
  'narrative.scenes[].generatedFrom': 'machine_enum_or_pattern',
  'narrative.shots[].id': 'machine_enum_or_pattern',
  'narrative.shots[].shotId': 'machine_enum_or_pattern',
  'narrative.shots[].assetSceneRef': 'machine_enum_or_pattern',
  'narrative.shots[].declaredScriptSceneRef': 'machine_enum_or_pattern',
  'narrative.shots[].declaredNarrativeBeatRef': 'machine_enum_or_pattern',
  'narrative.shots[].scriptSceneId': 'machine_enum_or_pattern',
  'narrative.shots[].narrativeBeatId': 'machine_enum_or_pattern',
  'narrative.shots[].associationStatus': 'machine_enum_or_pattern',
  'narrative.shots[].shotType': 'public_text',
  'narrative.shots[].characters[].ref': 'machine_enum_or_pattern',
  'narrative.shots[].characters[].displayName': 'public_text',
  'narrative.shots[].characters[].depthPlane': 'machine_enum_or_pattern',
  'narrative.shots[].characters[].action': 'public_text',
  'narrative.shots[].characters[].emotion': 'public_text',
  'narrative.shots[].camera.angle': 'public_text',
  'narrative.shots[].camera.height': 'public_text',
  'narrative.shots[].camera.movement': 'public_text',
  'narrative.shots[].camera.lens': 'public_text',
  'narrative.shots[].visual': 'public_text',
  'narrative.shots[].dialogue[].speaker': 'public_text',
  'narrative.shots[].dialogue[].line': 'public_text',
  'narrative.shots[].dialogue[].type': 'machine_enum_or_pattern',
  'narrative.shots[].timing.transitionIn': 'public_text',
  'narrative.shots[].timing.transitionOut': 'public_text',
  'narrative.shots[].sourceArtifact': 'canonical_relative_key',
  'narrative.shots[].sourceRevision': 'machine_enum_or_pattern',
  'narrative.shots[].generatedFrom': 'machine_enum_or_pattern',
  'narrative.associations.missingLinks[]': 'diagnostic',
  'narrative.associations.orphanArtifacts[]': 'diagnostic',
  'auxiliary.manifestRevision': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].id': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].shotId': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].kind': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].shotViewId': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].associationStatus': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].positive': 'public_text',
  'auxiliary.prompts.items[].negative': 'public_text',
  'auxiliary.prompts.items[].parameters.model': 'public_text',
  'auxiliary.prompts.items[].parameters.mode': 'public_text',
  'auxiliary.prompts.items[].parameters.cameraMotion': 'public_text',
  'auxiliary.prompts.items[].parameters.aspectRatio': 'machine_enum_or_pattern',
  'auxiliary.prompts.items[].generability.characterAnchor': 'public_text',
  'auxiliary.prompts.items[].generability.motionFeasibility': 'public_text',
  'auxiliary.prompts.items[].generability.durationBudget': 'public_text',
  'auxiliary.prompts.items[].generability.notes': 'public_text',
  'auxiliary.prompts.items[].sourceArtifact': 'canonical_relative_key',
  'auxiliary.prompts.items[].sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.prompts.nextCursor': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.sections[].id': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.sections[].title': 'public_text',
  'auxiliary.renderGuide.sections[].text': 'public_text',
  'auxiliary.renderGuide.sections[].sourceArtifact': 'canonical_relative_key',
  'auxiliary.renderGuide.sections[].sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].id': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].shotId': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].shotViewId': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].associationStatus': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].risk': 'public_text',
  'auxiliary.renderGuide.queue.items[].priority': 'public_text',
  'auxiliary.renderGuide.queue.items[].renderer': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].status': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.items[].sourceArtifact': 'canonical_relative_key',
  'auxiliary.renderGuide.queue.items[].sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.queue.nextCursor': 'machine_enum_or_pattern',
  'auxiliary.renderGuide.sourceArtifact': 'canonical_relative_key',
  'auxiliary.renderGuide.sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.review.scope': 'machine_enum_or_pattern',
  'auxiliary.review.overallVerdict': 'machine_enum_or_pattern',
  'auxiliary.review.reviewedArtifacts[]': 'canonical_relative_key',
  'auxiliary.review.sourceRevisions[].sourceArtifact': 'canonical_relative_key',
  'auxiliary.review.sourceRevisions[].sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.review.sections[].id': 'machine_enum_or_pattern',
  'auxiliary.review.sections[].title': 'public_text',
  'auxiliary.review.sections[].text': 'public_text',
  'auxiliary.review.sections[].sourceArtifact': 'canonical_relative_key',
  'auxiliary.review.sections[].sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].id': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].kind': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].sourceKey': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].targetViewId': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].associationStatus': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].sectionId': 'machine_enum_or_pattern',
  'auxiliary.review.targets[].sourceArtifact': 'canonical_relative_key',
  'auxiliary.review.targets[].sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.review.sourceArtifact': 'canonical_relative_key',
  'auxiliary.review.sourceRevision': 'machine_enum_or_pattern',
  'auxiliary.associations.orphanPrompts[]': 'diagnostic',
  'auxiliary.associations.orphanQueueEntries[]': 'diagnostic',
  'auxiliary.associations.duplicateQueueShotIds[]': 'diagnostic',
} as const satisfies Readonly<Record<string, StoryWorkspaceEpisodeStringFieldClass>>;

const STORY_WORKSPACE_EPISODE_RUN_ID = /^run_[0-9a-f]{32}$/;
const STORY_WORKSPACE_EPISODE_HEX_ID = /^[0-9a-f]{32}$/;
const STORY_WORKSPACE_EPISODE_REVISION = /^sha256:[0-9a-f]{64}$/;
const STORY_WORKSPACE_EPISODE_SOURCE_REVISION = /^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$/;
const STORY_WORKSPACE_EPISODE_SHOT_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const STORY_WORKSPACE_EPISODE_OPAQUE_KEY = /^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$/;
const STORY_WORKSPACE_EPISODE_CURSOR = /^[A-Za-z0-9][A-Za-z0-9._-]{0,2047}$/;
const STORY_WORKSPACE_EPISODE_SCENE_KEY = /^S[0-9]{2,}$/;
const STORY_WORKSPACE_EPISODE_BEAT_KEY = /^SC-[0-9]{2,}$/;
const STORY_WORKSPACE_EPISODE_REVIEWED_ARTIFACT =
  /^(?:episode-outline\.md|script\.md|storyboard\.yaml|prompts\/[A-Za-z0-9][A-Za-z0-9._-]{0,254}\.ya?ml|renders\/render-guide\.md)$/;
const STORY_WORKSPACE_EPISODE_SENSITIVE_PATH =
  /(?:^|[\s('"`=])(?:\/(?!\/)[A-Za-z0-9._~-]+(?:\/[^\s`]+)*|[A-Za-z]:[\\/][^\s`]+|\\\\[^\\\s]+\\[^\s`]+|file:\/\/(?:localhost)?\/[^\s`]+|(?:~|\$HOME|\$\{HOME\}|%(?:USERPROFILE|HOMEPATH)%|\$env:(?:USERPROFILE|HOME))(?=$|[\\/\s`])(?:[\\/][^\s`]*)?|\.\.[\\/])/i;
const STORY_WORKSPACE_EPISODE_HTML = /<!--|<\/?[A-Za-z][^>]*>/;
const STORY_WORKSPACE_EPISODE_CREDENTIAL = /(?:\bbearer\s+[A-Za-z0-9._-]{8,}|(?<![A-Za-z0-9_-])(?:sk-(?:(?:ant|proj)-)?|gh[pousr]_|xox[baprs]-)[A-Za-z0-9_-]{16,}(?![A-Za-z0-9_-])|(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])|(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])|(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9])|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:api[\s_-]*keys?|access[\s_-]*tokens?|refresh[\s_-]*tokens?|tokens?|secrets?|auth(?:orization)?|credentials?|passwords?|private[\s_-]*keys?)\b\s*[:=]\s*[^\s`]+)/i;
const STORY_WORKSPACE_EPISODE_PRIVATE_MODEL_TEXT = /(?:\bchain[\s_-]*(?:of[\s_-]*)?thought\b|\b(?:hidden|internal|private|model)[\s_-]*reasoning\b|\bsystem[\s_-]*prompt\b|隐藏推理|内部推理|思维链|系统提示词)/i;
const STORY_WORKSPACE_EPISODE_RAW_COMMAND = /(?:^|[\s`])(?:\$\s+|sudo\s+|curl\b|wget\b|(?:ba|z|fi)?sh\b|python(?:3(?:\.\d+)?)?\b|node\b|npm\b|npx\b|pnpm\b|yarn\b|git\b|claude\b|rm\s+(?:--recursive(?:\s+--force)?|-[A-Za-z]*r[A-Za-z]*)\s+|cat\s+(?:~?\/\.ssh\/|\/etc\/(?:passwd|shadow)|\S*(?:credential|secret|token|private[_-]?key))|dd\s+[^\n]{0,240}\bif=\S+[^\n]{0,240}\bof=\S+|\/drama-forge:[a-z0-9_-]+|(?:tool(?:_name)?|renderer|raw_command|command(?:_line)?)\s*[:=])/i;
const STORY_WORKSPACE_EPISODE_SENSITIVE_OPTION = /(?<![A-Za-z0-9_-])--(?:api[-_]?key|token|secret|password|credential|authorization)(?:[=\s]|$)/i;
const STORY_WORKSPACE_EPISODE_TOOL_OPTION = /(?<![A-Za-z0-9_-])(?:tool|renderer)\b[^\r\n]*?(?<![A-Za-z0-9_-])--[A-Za-z0-9][A-Za-z0-9_-]*/i;

type StoryWorkspaceEpisodeWireRecord = Record<string, unknown>;

function storyWorkspaceEpisodeRecord(
  value: unknown,
  label: string,
  keys: readonly string[],
): StoryWorkspaceEpisodeWireRecord {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${label} must be an object.`);
  }
  const record = value as StoryWorkspaceEpisodeWireRecord;
  const unknown = Object.keys(record).some((key) => !keys.includes(key));
  if (unknown) throw new Error(`${label} contains an unknown field.`);
  const missing = keys.find((key) => !Object.prototype.hasOwnProperty.call(record, key));
  if (missing) throw new Error(`${label} is missing ${missing}.`);
  return record;
}

function storyWorkspaceEpisodeString(
  value: unknown,
  label: string,
  options: { min?: number; max?: number; pattern?: RegExp; pathAudit?: boolean } = {},
): string {
  if (typeof value !== 'string') throw new Error(`${label} must be a string.`);
  const min = options.min ?? 0;
  const max = options.max ?? Number.MAX_SAFE_INTEGER;
  if (value.length < min || value.length > max || (options.pattern && !options.pattern.test(value))) {
    throw new Error(`${label} has an invalid value.`);
  }
  if ([...value].some((character) => {
    const code = character.charCodeAt(0);
    return code === 127 || (code < 32 && code !== 9 && code !== 10 && code !== 13);
  })) {
    throw new Error(`${label} contains a control character.`);
  }
  if (options.pathAudit !== false && STORY_WORKSPACE_EPISODE_SENSITIVE_PATH.test(value)) {
    throw new Error(`${label} contains a sensitive path.`);
  }
  return value;
}

function storyWorkspaceEpisodeEntropy(value: string): number {
  if (value.length === 0) return 0;
  const counts = new Map<string, number>();
  for (const character of value) counts.set(character, (counts.get(character) ?? 0) + 1);
  let result = 0;
  for (const count of counts.values()) {
    const probability = count / value.length;
    result -= probability * Math.log2(probability);
  }
  return result;
}

function storyWorkspaceEpisodeLooksLikeSecret(value: string): boolean {
  const longHex = value.match(/(?<![A-Fa-f0-9])[A-Fa-f0-9]{32,}(?![A-Fa-f0-9])/g) ?? [];
  if (longHex.some((candidate) => storyWorkspaceEpisodeEntropy(candidate) >= 3)) return true;
  const candidates = value.match(/(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_-]{32,}={0,2}(?![A-Za-z0-9+/_=-])/g) ?? [];
  return candidates.some((candidate) => {
    const token = candidate.replace(/=+$/, '');
    const characterClasses = Number(/[a-z]/.test(token))
      + Number(/[A-Z]/.test(token))
      + Number(/[0-9]/.test(token))
      + Number(/[+/_-]/.test(token));
    return characterClasses >= 2 && storyWorkspaceEpisodeEntropy(token) >= 3.5;
  });
}

function storyWorkspaceEpisodeViolatesPublicTextPolicy(value: string): boolean {
  return STORY_WORKSPACE_EPISODE_HTML.test(value)
    || STORY_WORKSPACE_EPISODE_CREDENTIAL.test(value)
    || STORY_WORKSPACE_EPISODE_PRIVATE_MODEL_TEXT.test(value)
    || STORY_WORKSPACE_EPISODE_RAW_COMMAND.test(value)
    || STORY_WORKSPACE_EPISODE_SENSITIVE_OPTION.test(value)
    || STORY_WORKSPACE_EPISODE_TOOL_OPTION.test(value)
    || storyWorkspaceEpisodeLooksLikeSecret(value);
}

function storyWorkspaceEpisodePublicText(
  value: unknown,
  label: string,
  options: { min?: number; max?: number } = {},
): string {
  const result = storyWorkspaceEpisodeString(value, label, options);
  if (storyWorkspaceEpisodeViolatesPublicTextPolicy(result)) {
    throw new Error(`${label} violates the public text policy.`);
  }
  return result;
}

function storyWorkspaceEpisodeNullablePublicText(
  value: unknown,
  label: string,
  options?: { min?: number; max?: number },
): string | null {
  return value === null ? null : storyWorkspaceEpisodePublicText(value, label, options);
}

function storyWorkspaceEpisodeNullableString(
  value: unknown,
  label: string,
  options?: { min?: number; max?: number; pattern?: RegExp; pathAudit?: boolean },
): string | null {
  return value === null ? null : storyWorkspaceEpisodeString(value, label, options);
}

function storyWorkspaceEpisodeBoolean(value: unknown, label: string): boolean {
  if (typeof value !== 'boolean') throw new Error(`${label} must be a boolean.`);
  return value;
}

function storyWorkspaceEpisodeNumber(
  value: unknown,
  label: string,
  options: { integer?: boolean; min?: number; max?: number } = {},
): number {
  if (
    typeof value !== 'number'
    || !Number.isFinite(value)
    || (options.integer && !Number.isInteger(value))
    || (options.min !== undefined && value < options.min)
    || (options.max !== undefined && value > options.max)
  ) throw new Error(`${label} must be a bounded number.`);
  return value;
}

function storyWorkspaceEpisodeNullableNumber(
  value: unknown,
  label: string,
  options?: { integer?: boolean; min?: number; max?: number },
): number | null {
  return value === null ? null : storyWorkspaceEpisodeNumber(value, label, options);
}

function storyWorkspaceEpisodeDatetime(value: unknown, label: string): string {
  const result = storyWorkspaceEpisodeString(value, label, { min: 20, max: 32 });
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):([0-5]\d):([0-5]\d)(?:\.(\d{1,6}))?Z$/.exec(result);
  if (!match) throw new Error(`${label} must be a UTC RFC3339 datetime.`);
  const [, year, month, day, hour, minute, second, fraction = ''] = match;
  if (Number(hour) > 23) throw new Error(`${label} must be a UTC RFC3339 datetime.`);
  const timestamp = Date.parse(result);
  if (!Number.isFinite(timestamp)) throw new Error(`${label} must be a UTC RFC3339 datetime.`);
  const date = new Date(timestamp);
  if (
    date.getUTCFullYear() !== Number(year)
    || date.getUTCMonth() + 1 !== Number(month)
    || date.getUTCDate() !== Number(day)
    || date.getUTCHours() !== Number(hour)
    || date.getUTCMinutes() !== Number(minute)
    || date.getUTCSeconds() !== Number(second)
    || (fraction.length > 0 && !/^\d{1,6}$/.test(fraction))
  ) throw new Error(`${label} must be a UTC RFC3339 datetime.`);
  return result;
}

function storyWorkspaceEpisodeEnum<T extends string>(
  value: unknown,
  label: string,
  values: readonly T[],
): T {
  if (typeof value !== 'string' || !values.includes(value as T)) {
    throw new Error(`${label} has an invalid enum value.`);
  }
  return value as T;
}

function storyWorkspaceEpisodeArray<T>(
  value: unknown,
  label: string,
  parser: (item: unknown, index: number) => T,
  max: number,
): T[] {
  if (!Array.isArray(value) || value.length > max) {
    throw new Error(`${label} must be a bounded array.`);
  }
  return value.map(parser);
}

function storyWorkspaceEpisodeUnique(values: readonly string[], label: string): void {
  if (new Set(values).size !== values.length) throw new Error(`${label} contains duplicate IDs.`);
}

function storyWorkspaceEpisodeStringList(
  value: unknown,
  label: string,
  max: number,
  unique = false,
  publicText = true,
): string[] {
  const result = storyWorkspaceEpisodeArray(
    value,
    label,
    (item, index) => (publicText ? storyWorkspaceEpisodePublicText : storyWorkspaceEpisodeString)(
      item,
      `${label}[${index}]`,
      { min: 1, max: 4000 },
    ),
    max,
  );
  if (unique) storyWorkspaceEpisodeUnique(result, label);
  return result;
}

function storyWorkspaceEpisodeDiagnosticList(value: unknown, label: string): string[] {
  const result = storyWorkspaceEpisodeArray(
    value,
    label,
    (item, index) => {
      const itemLabel = `${label}[${index}]`;
      const diagnostic = storyWorkspaceEpisodeString(item, itemLabel, { min: 1, max: 512 });
      if ([...diagnostic].some((character) => {
        const code = character.charCodeAt(0);
        return code <= 31 || code === 127;
      })) throw new Error(`${itemLabel} contains a control character.`);
      if (storyWorkspaceEpisodeViolatesPublicTextPolicy(diagnostic)) {
        throw new Error(`${itemLabel} violates the diagnostic policy.`);
      }
      return diagnostic;
    },
    2048,
  );
  storyWorkspaceEpisodeUnique(result, label);
  return result;
}

function storyWorkspaceEpisodeId(value: unknown, label: string): string {
  return storyWorkspaceEpisodeString(value, label, {
    min: 32,
    max: 32,
    pattern: STORY_WORKSPACE_EPISODE_HEX_ID,
  });
}

function storyWorkspaceEpisodeNullableId(value: unknown, label: string): string | null {
  return value === null ? null : storyWorkspaceEpisodeId(value, label);
}

function storyWorkspaceEpisodeSourceRevision(value: unknown, label: string): string {
  return storyWorkspaceEpisodeString(value, label, {
    min: 1,
    max: 128,
    pattern: STORY_WORKSPACE_EPISODE_SOURCE_REVISION,
  });
}

function storyWorkspaceEpisodeNullableSourceRevision(value: unknown, label: string): string | null {
  return value === null ? null : storyWorkspaceEpisodeSourceRevision(value, label);
}

function storyWorkspaceEpisodeGeneratedFrom(value: unknown, label: string): string | null {
  return storyWorkspaceEpisodeNullableString(value, label, {
    min: 1,
    max: 255,
    pattern: /^[A-Za-z0-9][A-Za-z0-9@._:-]{0,254}$/,
  });
}

function storyWorkspaceEpisodeAssociationStatus(
  value: unknown,
  label: string,
): StoryWorkspaceEpisodeAssociationStatus {
  return storyWorkspaceEpisodeEnum(value, label, ['linked', 'unlinked', 'orphan']);
}

function storyWorkspaceParseEpisodeCoverage(
  value: unknown,
  label: string,
): StoryWorkspaceEpisodeAssociationCoverage {
  const record = storyWorkspaceEpisodeRecord(value, label, ['availability', 'linked', 'total', 'ratio']);
  const availability = storyWorkspaceEpisodeEnum(
    record.availability,
    `${label}.availability`,
    ['available', 'unavailable'],
  );
  const linked = storyWorkspaceEpisodeNumber(record.linked, `${label}.linked`, { integer: true, min: 0 });
  const total = storyWorkspaceEpisodeNumber(record.total, `${label}.total`, { integer: true, min: 0 });
  const ratio = storyWorkspaceEpisodeNullableNumber(record.ratio, `${label}.ratio`, { min: 0, max: 1 });
  if (linked > total) throw new Error(`${label} linked exceeds total.`);
  if (total === 0) {
    if (availability !== 'unavailable' || linked !== 0 || ratio !== null) {
      throw new Error(`${label} zero denominator is inconsistent.`);
    }
  } else if (
    availability !== 'available'
    || ratio === null
    || Math.abs(ratio - linked / total) > 1e-12
  ) throw new Error(`${label} ratio is inconsistent.`);
  return { availability, linked, total, ratio };
}

function storyWorkspaceParseEpisodeBindingRecovery(value: unknown): StoryWorkspaceEpisodeBindingRecovery {
  const record = storyWorkspaceEpisodeRecord(value, 'bindingRecovery', [
    'autoRepairAttempted', 'canDispatch', 'publicReason',
  ]);
  const canDispatch = storyWorkspaceEpisodeBoolean(record.canDispatch, 'bindingRecovery.canDispatch');
  const publicReason = record.publicReason === null
    ? null
    : storyWorkspaceEpisodeEnum(
      record.publicReason,
      'bindingRecovery.publicReason',
      ['episode_binding_unproven'],
    );
  if ((canDispatch && publicReason !== null) || (!canDispatch && publicReason === null)) {
    throw new Error('bindingRecovery reason is inconsistent.');
  }
  return {
    autoRepairAttempted: storyWorkspaceEpisodeBoolean(
      record.autoRepairAttempted,
      'bindingRecovery.autoRepairAttempted',
    ),
    canDispatch,
    publicReason,
  };
}

const STORY_WORKSPACE_EPISODE_ARTIFACT_RULES = {
  'episode-outline.md': ['plan_episode', ['episode_overview', 'storyline_navigator', 'narrative_workbench']],
  'script.md': ['write_script', ['narrative_workbench', 'shot_inspector']],
  'storyboard.yaml': ['regenerate_storyboard', ['narrative_workbench', 'shot_inspector']],
  'prompts/': ['generate_prompts', ['shot_inspector', 'prompt_view']],
  'renders/': ['prepare_render_guide', ['shot_inspector', 'render_view']],
  'review-report.md': [['review_script', 'review_full_chain'], ['review_view', 'shot_inspector']],
} as const;

function storyWorkspaceParseEpisodeManifestEntry(
  value: unknown,
  index: number,
): StoryWorkspaceEpisodeArtifactManifestEntry {
  const label = `artifacts[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'relativeKey', 'availability', 'contentRevision', 'mtime', 'size', 'producerAction', 'consumers',
  ]);
  const relativeKey = storyWorkspaceEpisodeEnum(
    record.relativeKey,
    `${label}.relativeKey`,
    Object.keys(STORY_WORKSPACE_EPISODE_ARTIFACT_RULES),
  ) as keyof typeof STORY_WORKSPACE_EPISODE_ARTIFACT_RULES;
  const availability = storyWorkspaceEpisodeEnum(
    record.availability,
    `${label}.availability`,
    ['not_generated', 'available', 'invalid', 'unavailable'],
  );
  const contentRevision = record.contentRevision === null
    ? null
    : storyWorkspaceEpisodeString(record.contentRevision, `${label}.contentRevision`, {
      pattern: STORY_WORKSPACE_EPISODE_REVISION,
    });
  const mtime = record.mtime === null
    ? null
    : storyWorkspaceEpisodeDatetime(record.mtime, `${label}.mtime`);
  const size = storyWorkspaceEpisodeNullableNumber(record.size, `${label}.size`, { integer: true, min: 0 });
  if (availability === 'available') {
    if (contentRevision === null || mtime === null || size === null) {
      throw new Error(`${label} available metadata is incomplete.`);
    }
  } else if (contentRevision !== null || mtime !== null || size !== null) {
    throw new Error(`${label} unavailable metadata must be null.`);
  }
  const [producerRule, consumerRule] = STORY_WORKSPACE_EPISODE_ARTIFACT_RULES[relativeKey];
  const allowedProducers = Array.isArray(producerRule) ? producerRule : [producerRule];
  const producerAction = storyWorkspaceEpisodeEnum(
    record.producerAction,
    `${label}.producerAction`,
    allowedProducers,
  ) as StoryWorkspaceEpisodeProducerAction;
  const consumers = storyWorkspaceEpisodeArray(
    record.consumers,
    `${label}.consumers`,
    (item, consumerIndex): StoryWorkspaceEpisodeArtifactConsumer => storyWorkspaceEpisodeEnum(
      item,
      `${label}.consumers[${consumerIndex}]`,
      ['episode_overview', 'storyline_navigator', 'narrative_workbench', 'shot_inspector', 'prompt_view', 'render_view', 'review_view'],
    ),
    8,
  );
  if (consumers.length !== consumerRule.length || consumers.some((item, i) => item !== consumerRule[i])) {
    throw new Error(`${label}.consumers do not match relativeKey.`);
  }
  return { relativeKey, availability, contentRevision, mtime, size, producerAction, consumers };
}

function storyWorkspaceParseEpisodeCharacterBeat(
  value: unknown,
  index: number,
): StoryWorkspaceEpisodeCharacterBeat {
  const label = `narrative.overview.characterBeats[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'id', 'sourceKey', 'characterId', 'action', 'startState', 'trigger', 'choice', 'endState', 'visibleEvidence',
  ]);
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    sourceKey: storyWorkspaceEpisodeString(record.sourceKey, `${label}.sourceKey`, { max: 128, pattern: STORY_WORKSPACE_EPISODE_OPAQUE_KEY }),
    characterId: storyWorkspaceEpisodeNullableString(record.characterId, `${label}.characterId`, { max: 128, pattern: STORY_WORKSPACE_EPISODE_OPAQUE_KEY }),
    action: storyWorkspaceEpisodeNullablePublicText(record.action, `${label}.action`, { max: 128 }),
    startState: storyWorkspaceEpisodeNullablePublicText(record.startState, `${label}.startState`, { max: 2000 }),
    trigger: storyWorkspaceEpisodeNullablePublicText(record.trigger, `${label}.trigger`, { max: 2000 }),
    choice: storyWorkspaceEpisodeNullablePublicText(record.choice, `${label}.choice`, { max: 2000 }),
    endState: storyWorkspaceEpisodeNullablePublicText(record.endState, `${label}.endState`, { max: 2000 }),
    visibleEvidence: storyWorkspaceEpisodeNullablePublicText(record.visibleEvidence, `${label}.visibleEvidence`, { max: 2000 }),
  };
}

function storyWorkspaceParseEpisodeOverview(value: unknown): StoryWorkspaceEpisodeOverview {
  const label = 'narrative.overview';
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'title', 'series', 'storyGoals', 'coreConflict', 'hook', 'sourceArtifact', 'sourceRevision', 'generatedFrom', 'characterBeats',
  ]);
  const characterBeats = storyWorkspaceEpisodeArray(
    record.characterBeats,
    `${label}.characterBeats`,
    storyWorkspaceParseEpisodeCharacterBeat,
    256,
  );
  storyWorkspaceEpisodeUnique(characterBeats.map((item) => item.id), `${label}.characterBeats`);
  const sourceArtifact = record.sourceArtifact === null
    ? null
    : storyWorkspaceEpisodeEnum(record.sourceArtifact, `${label}.sourceArtifact`, ['episode-outline.md']);
  return {
    title: storyWorkspaceEpisodeNullablePublicText(record.title, `${label}.title`, { max: 500 }),
    series: storyWorkspaceEpisodeNullablePublicText(record.series, `${label}.series`, { max: 500 }),
    storyGoals: storyWorkspaceEpisodeStringList(record.storyGoals, `${label}.storyGoals`, 32),
    coreConflict: storyWorkspaceEpisodeNullablePublicText(record.coreConflict, `${label}.coreConflict`, { max: 4000 }),
    hook: storyWorkspaceEpisodeNullablePublicText(record.hook, `${label}.hook`, { max: 4000 }),
    sourceArtifact,
    sourceRevision: storyWorkspaceEpisodeNullableSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
    generatedFrom: storyWorkspaceEpisodeGeneratedFrom(record.generatedFrom, `${label}.generatedFrom`),
    characterBeats,
  };
}

function storyWorkspaceParseEpisodeNarrativeBeat(
  value: unknown,
  index: number,
): StoryWorkspaceEpisodeNarrativeBeat {
  const label = `narrative.narrativeBeats[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'id', 'sourceKey', 'title', 'assetSceneRef', 'narrativeFunction', 'emotionTone', 'summary', 'sceneGoals', 'keyDialogueBeats', 'sourceArtifact', 'sourceRevision', 'generatedFrom',
  ]);
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    sourceKey: storyWorkspaceEpisodeString(record.sourceKey, `${label}.sourceKey`, { pattern: STORY_WORKSPACE_EPISODE_BEAT_KEY }),
    title: storyWorkspaceEpisodePublicText(record.title, `${label}.title`, { min: 1, max: 500 }),
    assetSceneRef: storyWorkspaceEpisodeNullableString(record.assetSceneRef, `${label}.assetSceneRef`, { pattern: STORY_WORKSPACE_EPISODE_OPAQUE_KEY }),
    narrativeFunction: storyWorkspaceEpisodeNullablePublicText(record.narrativeFunction, `${label}.narrativeFunction`, { max: 500 }),
    emotionTone: storyWorkspaceEpisodeNullablePublicText(record.emotionTone, `${label}.emotionTone`, { max: 500 }),
    summary: storyWorkspaceEpisodeNullablePublicText(record.summary, `${label}.summary`, { max: 4000 }),
    sceneGoals: storyWorkspaceEpisodeStringList(record.sceneGoals, `${label}.sceneGoals`, 32),
    keyDialogueBeats: storyWorkspaceEpisodeStringList(record.keyDialogueBeats, `${label}.keyDialogueBeats`, 32),
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, `${label}.sourceArtifact`, ['episode-outline.md']),
    sourceRevision: storyWorkspaceEpisodeNullableSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
    generatedFrom: storyWorkspaceEpisodeGeneratedFrom(record.generatedFrom, `${label}.generatedFrom`),
  };
}

function storyWorkspaceParseEpisodeDialogueLine(
  value: unknown,
  label: string,
): StoryWorkspaceEpisodeDialogueLine {
  const record = storyWorkspaceEpisodeRecord(value, label, ['speaker', 'qualifier', 'text']);
  return {
    speaker: storyWorkspaceEpisodePublicText(record.speaker, `${label}.speaker`, { min: 1, max: 128 }),
    qualifier: storyWorkspaceEpisodeNullablePublicText(record.qualifier, `${label}.qualifier`, { max: 255 }),
    text: storyWorkspaceEpisodePublicText(record.text, `${label}.text`, { min: 1, max: 2000 }),
  };
}

function storyWorkspaceParseEpisodeScene(value: unknown, index: number): StoryWorkspaceEpisodeScriptScene {
  const label = `narrative.scenes[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'id', 'sourceKey', 'title', 'heading', 'assetSceneRef', 'narrativeBeatId', 'declaredNarrativeBeatRef', 'associationStatus', 'actions', 'dialogue', 'cameraCues', 'sourceArtifact', 'sourceRevision', 'generatedFrom',
  ]);
  const associationStatus = storyWorkspaceEpisodeAssociationStatus(record.associationStatus, `${label}.associationStatus`);
  const narrativeBeatId = storyWorkspaceEpisodeNullableId(record.narrativeBeatId, `${label}.narrativeBeatId`);
  if ((associationStatus === 'linked') !== (narrativeBeatId !== null)) {
    throw new Error(`${label} linked association is inconsistent.`);
  }
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    sourceKey: storyWorkspaceEpisodeString(record.sourceKey, `${label}.sourceKey`, { pattern: STORY_WORKSPACE_EPISODE_SCENE_KEY }),
    title: storyWorkspaceEpisodePublicText(record.title, `${label}.title`, { min: 1, max: 500 }),
    heading: storyWorkspaceEpisodePublicText(record.heading, `${label}.heading`, { min: 1, max: 1000 }),
    assetSceneRef: storyWorkspaceEpisodeNullableString(record.assetSceneRef, `${label}.assetSceneRef`, { pattern: STORY_WORKSPACE_EPISODE_OPAQUE_KEY }),
    narrativeBeatId,
    declaredNarrativeBeatRef: storyWorkspaceEpisodeNullableString(record.declaredNarrativeBeatRef, `${label}.declaredNarrativeBeatRef`, { pattern: STORY_WORKSPACE_EPISODE_BEAT_KEY }),
    associationStatus,
    actions: storyWorkspaceEpisodeStringList(record.actions, `${label}.actions`, 256),
    dialogue: storyWorkspaceEpisodeArray(
      record.dialogue,
      `${label}.dialogue`,
      (item, dialogueIndex) => storyWorkspaceParseEpisodeDialogueLine(item, `${label}.dialogue[${dialogueIndex}]`),
      256,
    ),
    cameraCues: storyWorkspaceEpisodeStringList(record.cameraCues, `${label}.cameraCues`, 256),
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, `${label}.sourceArtifact`, ['script.md']),
    sourceRevision: storyWorkspaceEpisodeNullableSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
    generatedFrom: storyWorkspaceEpisodeGeneratedFrom(record.generatedFrom, `${label}.generatedFrom`),
  };
}

function storyWorkspaceParseEpisodeShotCharacter(value: unknown, label: string): StoryWorkspaceEpisodeShotCharacter {
  const record = storyWorkspaceEpisodeRecord(value, label, ['ref', 'displayName', 'depthPlane', 'action', 'emotion']);
  return {
    ref: storyWorkspaceEpisodeString(record.ref, `${label}.ref`, { max: 128, pattern: STORY_WORKSPACE_EPISODE_OPAQUE_KEY }),
    displayName: storyWorkspaceEpisodeNullablePublicText(record.displayName, `${label}.displayName`, { max: 255 }),
    depthPlane: (record.depthPlane === null
      ? null
      : storyWorkspaceEpisodeEnum(record.depthPlane, `${label}.depthPlane`, ['front', 'mid', 'back'])) as StoryWorkspaceEpisodeShotCharacter['depthPlane'],
    action: storyWorkspaceEpisodeNullablePublicText(record.action, `${label}.action`, { max: 2000 }),
    emotion: storyWorkspaceEpisodeNullablePublicText(record.emotion, `${label}.emotion`, { max: 1000 }),
  };
}

function storyWorkspaceParseEpisodeShot(value: unknown, index: number): StoryWorkspaceEpisodeStoryboardShot {
  const label = `narrative.shots[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'id', 'shotId', 'assetSceneRef', 'declaredScriptSceneRef', 'declaredNarrativeBeatRef', 'scriptSceneId', 'narrativeBeatId', 'associationStatus', 'shotType', 'characters', 'camera', 'visual', 'dialogue', 'timing', 'sourceArtifact', 'sourceRevision', 'generatedFrom',
  ]);
  const associationStatus = storyWorkspaceEpisodeAssociationStatus(record.associationStatus, `${label}.associationStatus`);
  const scriptSceneId = storyWorkspaceEpisodeNullableId(record.scriptSceneId, `${label}.scriptSceneId`);
  if ((associationStatus === 'linked') !== (scriptSceneId !== null)) {
    throw new Error(`${label} linked association is inconsistent.`);
  }
  const camera = storyWorkspaceEpisodeRecord(record.camera, `${label}.camera`, ['angle', 'height', 'movement', 'lens']);
  const timing = storyWorkspaceEpisodeRecord(record.timing, `${label}.timing`, [
    'durationSec', 'transitionIn', 'transitionOut',
  ]);
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    shotId: storyWorkspaceEpisodeString(record.shotId, `${label}.shotId`, { pattern: STORY_WORKSPACE_EPISODE_SHOT_ID }),
    assetSceneRef: storyWorkspaceEpisodeNullableString(record.assetSceneRef, `${label}.assetSceneRef`, { pattern: STORY_WORKSPACE_EPISODE_OPAQUE_KEY }),
    declaredScriptSceneRef: storyWorkspaceEpisodeNullableString(record.declaredScriptSceneRef, `${label}.declaredScriptSceneRef`, { pattern: STORY_WORKSPACE_EPISODE_SCENE_KEY }),
    declaredNarrativeBeatRef: storyWorkspaceEpisodeNullableString(record.declaredNarrativeBeatRef, `${label}.declaredNarrativeBeatRef`, { pattern: STORY_WORKSPACE_EPISODE_BEAT_KEY }),
    scriptSceneId,
    narrativeBeatId: storyWorkspaceEpisodeNullableId(record.narrativeBeatId, `${label}.narrativeBeatId`),
    associationStatus,
    shotType: storyWorkspaceEpisodeNullablePublicText(record.shotType, `${label}.shotType`, { max: 255 }),
    characters: storyWorkspaceEpisodeArray(
      record.characters,
      `${label}.characters`,
      (item, characterIndex) => storyWorkspaceParseEpisodeShotCharacter(item, `${label}.characters[${characterIndex}]`),
      128,
    ),
    camera: {
      angle: storyWorkspaceEpisodeNullablePublicText(camera.angle, `${label}.camera.angle`, { max: 255 }),
      height: storyWorkspaceEpisodeNullablePublicText(camera.height, `${label}.camera.height`, { max: 255 }),
      movement: storyWorkspaceEpisodeNullablePublicText(camera.movement, `${label}.camera.movement`, { max: 255 }),
      lens: storyWorkspaceEpisodeNullablePublicText(camera.lens, `${label}.camera.lens`, { max: 255 }),
    },
    visual: storyWorkspaceEpisodeNullablePublicText(record.visual, `${label}.visual`, { max: 4000 }),
    dialogue: storyWorkspaceEpisodeArray(record.dialogue, `${label}.dialogue`, (item, dialogueIndex) => {
      const dialogueLabel = `${label}.dialogue[${dialogueIndex}]`;
      const dialogue = storyWorkspaceEpisodeRecord(item, dialogueLabel, ['speaker', 'line', 'type']);
      return {
        speaker: storyWorkspaceEpisodePublicText(dialogue.speaker, `${dialogueLabel}.speaker`, { min: 1, max: 128 }),
        line: storyWorkspaceEpisodePublicText(dialogue.line, `${dialogueLabel}.line`, { min: 1, max: 2000 }),
        type: storyWorkspaceEpisodeEnum(dialogue.type, `${dialogueLabel}.type`, ['spoken', 'voiceover', 'os', 'inner']),
      };
    }, 128),
    timing: {
      durationSec: storyWorkspaceEpisodeNullableNumber(timing.durationSec, `${label}.timing.durationSec`, { min: 0, max: 3600 }),
      transitionIn: storyWorkspaceEpisodeNullablePublicText(timing.transitionIn, `${label}.timing.transitionIn`, { max: 255 }),
      transitionOut: storyWorkspaceEpisodeNullablePublicText(timing.transitionOut, `${label}.timing.transitionOut`, { max: 255 }),
    },
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, `${label}.sourceArtifact`, ['storyboard.yaml']),
    sourceRevision: storyWorkspaceEpisodeNullableSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
    generatedFrom: storyWorkspaceEpisodeGeneratedFrom(record.generatedFrom, `${label}.generatedFrom`),
  };
}

function storyWorkspaceParseEpisodeNarrative(value: unknown): StoryWorkspaceEpisodeNarrativeProjection {
  const record = storyWorkspaceEpisodeRecord(value, 'narrative', [
    'episodeId', 'storyArcId', 'overview', 'narrativeBeats', 'scenes', 'shots', 'associations',
  ]);
  const narrativeBeats = storyWorkspaceEpisodeArray(record.narrativeBeats, 'narrative.narrativeBeats', storyWorkspaceParseEpisodeNarrativeBeat, 256);
  const scenes = storyWorkspaceEpisodeArray(record.scenes, 'narrative.scenes', storyWorkspaceParseEpisodeScene, 1000);
  const shots = storyWorkspaceEpisodeArray(record.shots, 'narrative.shots', storyWorkspaceParseEpisodeShot, 1000);
  storyWorkspaceEpisodeUnique(narrativeBeats.map((item) => item.id), 'narrative.narrativeBeats');
  storyWorkspaceEpisodeUnique(scenes.map((item) => item.id), 'narrative.scenes');
  storyWorkspaceEpisodeUnique(shots.map((item) => item.id), 'narrative.shots');
  const beatIds = new Set(narrativeBeats.map((item) => item.id));
  const sceneIds = new Set(scenes.map((item) => item.id));
  if (scenes.some((item) => item.narrativeBeatId !== null && !beatIds.has(item.narrativeBeatId))) {
    throw new Error('narrative.scenes contains an unknown narrativeBeatId.');
  }
  if (shots.some((item) => item.scriptSceneId !== null && !sceneIds.has(item.scriptSceneId))) {
    throw new Error('narrative.shots contains an unknown scriptSceneId.');
  }
  if (shots.some((item) => item.narrativeBeatId !== null && !beatIds.has(item.narrativeBeatId))) {
    throw new Error('narrative.shots contains an unknown narrativeBeatId.');
  }
  const associations = storyWorkspaceEpisodeRecord(record.associations, 'narrative.associations', [
    'beatSceneCoverage', 'sceneShotCoverage', 'missingLinks', 'orphanArtifacts',
  ]);
  return {
    episodeId: storyWorkspaceEpisodeId(record.episodeId, 'narrative.episodeId'),
    storyArcId: storyWorkspaceEpisodeId(record.storyArcId, 'narrative.storyArcId'),
    overview: storyWorkspaceParseEpisodeOverview(record.overview),
    narrativeBeats,
    scenes,
    shots,
    associations: {
      beatSceneCoverage: storyWorkspaceParseEpisodeCoverage(associations.beatSceneCoverage, 'narrative.associations.beatSceneCoverage'),
      sceneShotCoverage: storyWorkspaceParseEpisodeCoverage(associations.sceneShotCoverage, 'narrative.associations.sceneShotCoverage'),
      missingLinks: storyWorkspaceEpisodeDiagnosticList(associations.missingLinks, 'narrative.associations.missingLinks'),
      orphanArtifacts: storyWorkspaceEpisodeDiagnosticList(associations.orphanArtifacts, 'narrative.associations.orphanArtifacts'),
    },
  };
}

function storyWorkspaceParseEpisodePrompt(value: unknown, index: number): StoryWorkspaceEpisodePrompt {
  const label = `auxiliary.prompts.items[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'id', 'shotId', 'kind', 'shotViewId', 'associationStatus', 'positive', 'negative', 'parameters', 'generability', 'sourceArtifact', 'sourceRevision',
  ]);
  const associationStatus = storyWorkspaceEpisodeAssociationStatus(record.associationStatus, `${label}.associationStatus`);
  const shotViewId = storyWorkspaceEpisodeNullableId(record.shotViewId, `${label}.shotViewId`);
  if ((associationStatus === 'linked') !== (shotViewId !== null)) throw new Error(`${label} linked association is inconsistent.`);
  const parameters = storyWorkspaceEpisodeRecord(record.parameters, `${label}.parameters`, [
    'model', 'mode', 'durationSec', 'motionStrength', 'cameraMotion', 'aspectRatio',
  ]);
  const generability = storyWorkspaceEpisodeRecord(record.generability, `${label}.generability`, [
    'characterAnchor', 'motionFeasibility', 'durationBudget', 'notes',
  ]);
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    shotId: storyWorkspaceEpisodeString(record.shotId, `${label}.shotId`, { pattern: STORY_WORKSPACE_EPISODE_SHOT_ID }),
    kind: storyWorkspaceEpisodeString(record.kind, `${label}.kind`, { pattern: /^[a-z0-9][a-z0-9._-]{0,63}$/ }),
    shotViewId,
    associationStatus,
    positive: storyWorkspaceEpisodePublicText(record.positive, `${label}.positive`, { min: 1, max: 8000 }),
    negative: storyWorkspaceEpisodeNullablePublicText(record.negative, `${label}.negative`, { max: 4000 }),
    parameters: {
      model: storyWorkspaceEpisodeNullablePublicText(parameters.model, `${label}.parameters.model`, { max: 128 }),
      mode: storyWorkspaceEpisodeNullablePublicText(parameters.mode, `${label}.parameters.mode`, { max: 128 }),
      durationSec: storyWorkspaceEpisodeNullableNumber(parameters.durationSec, `${label}.parameters.durationSec`, { min: 0, max: 3600 }),
      motionStrength: storyWorkspaceEpisodeNullableNumber(parameters.motionStrength, `${label}.parameters.motionStrength`, { min: 0, max: 100 }),
      cameraMotion: storyWorkspaceEpisodeNullablePublicText(parameters.cameraMotion, `${label}.parameters.cameraMotion`, { max: 255 }),
      aspectRatio: storyWorkspaceEpisodeNullableString(parameters.aspectRatio, `${label}.parameters.aspectRatio`, { pattern: /^[0-9]{1,3}:[0-9]{1,3}$/, max: 32 }),
    },
    generability: {
      characterAnchor: storyWorkspaceEpisodeNullablePublicText(generability.characterAnchor, `${label}.generability.characterAnchor`, { max: 128 }),
      motionFeasibility: storyWorkspaceEpisodeNullablePublicText(generability.motionFeasibility, `${label}.generability.motionFeasibility`, { max: 128 }),
      durationBudget: storyWorkspaceEpisodeNullablePublicText(generability.durationBudget, `${label}.generability.durationBudget`, { max: 128 }),
      notes: storyWorkspaceEpisodeNullablePublicText(generability.notes, `${label}.generability.notes`, { max: 2000 }),
    },
    sourceArtifact: storyWorkspaceEpisodeString(record.sourceArtifact, `${label}.sourceArtifact`, { pattern: /^prompts\/[A-Za-z0-9][A-Za-z0-9._-]{0,254}\.ya?ml$/ }),
    sourceRevision: storyWorkspaceEpisodeSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
  };
}

function storyWorkspaceParseEpisodeSection(
  value: unknown,
  label: string,
  sourceArtifact: 'renders/render-guide.md' | 'review-report.md',
): StoryWorkspaceEpisodeArtifactSection {
  const record = storyWorkspaceEpisodeRecord(value, label, ['id', 'level', 'title', 'text', 'sourceArtifact', 'sourceRevision']);
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    level: storyWorkspaceEpisodeNumber(record.level, `${label}.level`, { integer: true, min: 1, max: 6 }),
    title: storyWorkspaceEpisodePublicText(record.title, `${label}.title`, { min: 1, max: 500 }),
    text: storyWorkspaceEpisodePublicText(record.text, `${label}.text`, { max: 8000 }),
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, `${label}.sourceArtifact`, [sourceArtifact]),
    sourceRevision: storyWorkspaceEpisodeSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
  };
}

function storyWorkspaceParseEpisodeQueueEntry(
  value: unknown,
  index: number,
): StoryWorkspaceEpisodeRenderQueueEntry {
  const label = `auxiliary.renderGuide.queue.items[${index}]`;
  const record = storyWorkspaceEpisodeRecord(value, label, [
    'id', 'shotId', 'shotViewId', 'associationStatus', 'durationSec', 'risk', 'priority', 'renderer', 'status', 'sourceArtifact', 'sourceRevision',
  ]);
  const associationStatus = storyWorkspaceEpisodeAssociationStatus(record.associationStatus, `${label}.associationStatus`);
  const shotViewId = storyWorkspaceEpisodeNullableId(record.shotViewId, `${label}.shotViewId`);
  if ((associationStatus === 'linked') !== (shotViewId !== null)) throw new Error(`${label} linked association is inconsistent.`);
  return {
    id: storyWorkspaceEpisodeId(record.id, `${label}.id`),
    shotId: storyWorkspaceEpisodeString(record.shotId, `${label}.shotId`, { pattern: STORY_WORKSPACE_EPISODE_SHOT_ID }),
    shotViewId,
    associationStatus,
    durationSec: storyWorkspaceEpisodeNullableNumber(record.durationSec, `${label}.durationSec`, { min: 0, max: 3600 }),
    risk: storyWorkspaceEpisodeNullablePublicText(record.risk, `${label}.risk`, { max: 128 }),
    priority: storyWorkspaceEpisodeNullablePublicText(record.priority, `${label}.priority`, { max: 64 }),
    renderer: storyWorkspaceEpisodeNullableString(record.renderer, `${label}.renderer`, { pattern: /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/, max: 128 }),
    status: storyWorkspaceEpisodeNullableString(record.status, `${label}.status`, { pattern: /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/, max: 64 }),
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, `${label}.sourceArtifact`, ['renders/render-guide.md']),
    sourceRevision: storyWorkspaceEpisodeSourceRevision(record.sourceRevision, `${label}.sourceRevision`),
  };
}

function storyWorkspaceParseEpisodeRenderGuide(value: unknown): StoryWorkspaceEpisodeRenderGuide {
  const record = storyWorkspaceEpisodeRecord(value, 'auxiliary.renderGuide', [
    'sections', 'queue', 'sourceArtifact', 'sourceRevision',
  ]);
  const sections = storyWorkspaceEpisodeArray(
    record.sections,
    'auxiliary.renderGuide.sections',
    (item, index) => storyWorkspaceParseEpisodeSection(item, `auxiliary.renderGuide.sections[${index}]`, 'renders/render-guide.md'),
    128,
  );
  const queue = storyWorkspaceEpisodeRecord(record.queue, 'auxiliary.renderGuide.queue', ['items', 'total', 'nextCursor']);
  const items = storyWorkspaceEpisodeArray(queue.items, 'auxiliary.renderGuide.queue.items', storyWorkspaceParseEpisodeQueueEntry, 100);
  storyWorkspaceEpisodeUnique(sections.map((item) => item.id), 'auxiliary.renderGuide.sections');
  storyWorkspaceEpisodeUnique(items.map((item) => item.id), 'auxiliary.renderGuide.queue.items');
  const total = storyWorkspaceEpisodeNumber(queue.total, 'auxiliary.renderGuide.queue.total', { integer: true, min: 0 });
  if (items.length > total) throw new Error('auxiliary.renderGuide.queue exceeds total.');
  return {
    sections,
    queue: {
      items,
      total,
      nextCursor: storyWorkspaceEpisodeNullableString(queue.nextCursor, 'auxiliary.renderGuide.queue.nextCursor', { pattern: STORY_WORKSPACE_EPISODE_CURSOR }),
    },
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, 'auxiliary.renderGuide.sourceArtifact', ['renders/render-guide.md']),
    sourceRevision: storyWorkspaceEpisodeSourceRevision(record.sourceRevision, 'auxiliary.renderGuide.sourceRevision'),
  };
}

function storyWorkspaceParseEpisodeReview(value: unknown): StoryWorkspaceEpisodeReviewReport {
  const record = storyWorkspaceEpisodeRecord(value, 'auxiliary.review', [
    'scope', 'overallVerdict', 'reviewedArtifacts', 'sourceRevisions', 'sections', 'targets', 'sourceArtifact', 'sourceRevision',
  ]);
  const sections = storyWorkspaceEpisodeArray(
    record.sections,
    'auxiliary.review.sections',
    (item, index) => storyWorkspaceParseEpisodeSection(item, `auxiliary.review.sections[${index}]`, 'review-report.md'),
    128,
  );
  const sourceRevisions = storyWorkspaceEpisodeArray(record.sourceRevisions, 'auxiliary.review.sourceRevisions', (item, index) => {
    const label = `auxiliary.review.sourceRevisions[${index}]`;
    const revision = storyWorkspaceEpisodeRecord(item, label, ['sourceArtifact', 'sourceRevision']);
    return {
      sourceArtifact: storyWorkspaceEpisodeString(revision.sourceArtifact, `${label}.sourceArtifact`, {
        pattern: STORY_WORKSPACE_EPISODE_REVIEWED_ARTIFACT,
      }),
      sourceRevision: storyWorkspaceEpisodeSourceRevision(revision.sourceRevision, `${label}.sourceRevision`),
    };
  }, 256);
  const targets = storyWorkspaceEpisodeArray(record.targets, 'auxiliary.review.targets', (item, index) => {
    const label = `auxiliary.review.targets[${index}]`;
    const target = storyWorkspaceEpisodeRecord(item, label, [
      'id', 'kind', 'sourceKey', 'targetViewId', 'associationStatus', 'sectionId', 'sourceArtifact', 'sourceRevision',
    ]);
    const associationStatus = storyWorkspaceEpisodeAssociationStatus(target.associationStatus, `${label}.associationStatus`);
    const targetViewId = storyWorkspaceEpisodeNullableId(target.targetViewId, `${label}.targetViewId`);
    if ((associationStatus === 'linked') !== (targetViewId !== null)) throw new Error(`${label} linked association is inconsistent.`);
    return {
      id: storyWorkspaceEpisodeId(target.id, `${label}.id`),
      kind: storyWorkspaceEpisodeEnum(target.kind, `${label}.kind`, ['narrative-beat', 'script-scene', 'shot']),
      sourceKey: storyWorkspaceEpisodeString(target.sourceKey, `${label}.sourceKey`, { pattern: STORY_WORKSPACE_EPISODE_SHOT_ID }),
      targetViewId,
      associationStatus,
      sectionId: storyWorkspaceEpisodeId(target.sectionId, `${label}.sectionId`),
      sourceArtifact: storyWorkspaceEpisodeEnum(target.sourceArtifact, `${label}.sourceArtifact`, ['review-report.md']),
      sourceRevision: storyWorkspaceEpisodeSourceRevision(target.sourceRevision, `${label}.sourceRevision`),
    };
  }, 2048);
  storyWorkspaceEpisodeUnique(sections.map((item) => item.id), 'auxiliary.review.sections');
  storyWorkspaceEpisodeUnique(targets.map((item) => item.id), 'auxiliary.review.targets');
  const sectionIds = new Set(sections.map((item) => item.id));
  if (targets.some((item) => !sectionIds.has(item.sectionId))) throw new Error('auxiliary.review.targets contains an unknown sectionId.');
  return {
    scope: storyWorkspaceEpisodeEnum(record.scope, 'auxiliary.review.scope', ['script', 'full-chain', 'unknown']),
    overallVerdict: storyWorkspaceEpisodeNullableString(record.overallVerdict, 'auxiliary.review.overallVerdict', { pattern: /^[A-Z][A-Z0-9_ -]{0,63}$/, max: 64 }),
    reviewedArtifacts: (() => {
      const values = storyWorkspaceEpisodeArray(
        record.reviewedArtifacts,
        'auxiliary.review.reviewedArtifacts',
        (item, index) => storyWorkspaceEpisodeString(
          item,
          `auxiliary.review.reviewedArtifacts[${index}]`,
          { pattern: STORY_WORKSPACE_EPISODE_REVIEWED_ARTIFACT },
        ),
        256,
      );
      storyWorkspaceEpisodeUnique(values, 'auxiliary.review.reviewedArtifacts');
      return values;
    })(),
    sourceRevisions,
    sections,
    targets,
    sourceArtifact: storyWorkspaceEpisodeEnum(record.sourceArtifact, 'auxiliary.review.sourceArtifact', ['review-report.md']),
    sourceRevision: storyWorkspaceEpisodeSourceRevision(record.sourceRevision, 'auxiliary.review.sourceRevision'),
  };
}

function storyWorkspaceParseEpisodeAuxiliary(value: unknown): StoryWorkspaceEpisodeAuxiliaryProjection {
  const record = storyWorkspaceEpisodeRecord(value, 'auxiliary', [
    'manifestRevision', 'prompts', 'renderGuide', 'review', 'associations',
  ]);
  const promptsRecord = storyWorkspaceEpisodeRecord(record.prompts, 'auxiliary.prompts', ['items', 'total', 'nextCursor']);
  const prompts = storyWorkspaceEpisodeArray(promptsRecord.items, 'auxiliary.prompts.items', storyWorkspaceParseEpisodePrompt, 100);
  storyWorkspaceEpisodeUnique(prompts.map((item) => item.id), 'auxiliary.prompts.items');
  const promptTotal = storyWorkspaceEpisodeNumber(promptsRecord.total, 'auxiliary.prompts.total', { integer: true, min: 0 });
  if (prompts.length > promptTotal) throw new Error('auxiliary.prompts exceeds total.');
  const associations = storyWorkspaceEpisodeRecord(record.associations, 'auxiliary.associations', [
    'shotPromptCoverage', 'shotRenderQueueCoverage', 'totalPrompts', 'totalQueueEntries', 'orphanPrompts', 'orphanQueueEntries', 'duplicateQueueShotIds',
  ]);
  return {
    manifestRevision: storyWorkspaceEpisodeString(record.manifestRevision, 'auxiliary.manifestRevision', { pattern: STORY_WORKSPACE_EPISODE_REVISION }),
    prompts: {
      items: prompts,
      total: promptTotal,
      nextCursor: storyWorkspaceEpisodeNullableString(promptsRecord.nextCursor, 'auxiliary.prompts.nextCursor', { pattern: STORY_WORKSPACE_EPISODE_CURSOR }),
    },
    renderGuide: record.renderGuide === null ? null : storyWorkspaceParseEpisodeRenderGuide(record.renderGuide),
    review: record.review === null ? null : storyWorkspaceParseEpisodeReview(record.review),
    associations: {
      shotPromptCoverage: storyWorkspaceParseEpisodeCoverage(associations.shotPromptCoverage, 'auxiliary.associations.shotPromptCoverage'),
      shotRenderQueueCoverage: storyWorkspaceParseEpisodeCoverage(associations.shotRenderQueueCoverage, 'auxiliary.associations.shotRenderQueueCoverage'),
      totalPrompts: storyWorkspaceEpisodeNumber(associations.totalPrompts, 'auxiliary.associations.totalPrompts', { integer: true, min: 0 }),
      totalQueueEntries: storyWorkspaceEpisodeNumber(associations.totalQueueEntries, 'auxiliary.associations.totalQueueEntries', { integer: true, min: 0 }),
      orphanPrompts: storyWorkspaceEpisodeDiagnosticList(associations.orphanPrompts, 'auxiliary.associations.orphanPrompts'),
      orphanQueueEntries: storyWorkspaceEpisodeDiagnosticList(associations.orphanQueueEntries, 'auxiliary.associations.orphanQueueEntries'),
      duplicateQueueShotIds: storyWorkspaceEpisodeDiagnosticList(associations.duplicateQueueShotIds, 'auxiliary.associations.duplicateQueueShotIds'),
    },
  };
}

function storyWorkspaceEpisodeAssertLinks(surface: StoryWorkspaceEpisodeArtifactSurface): void {
  const narrative = surface.narrative;
  if (!narrative) return;
  const shotIds = new Set(narrative.shots.map((item) => item.id));
  const beatIds = new Set(narrative.narrativeBeats.map((item) => item.id));
  const sceneIds = new Set(narrative.scenes.map((item) => item.id));
  const auxiliary = surface.auxiliary;
  if (auxiliary?.prompts.items.some((item) => item.shotViewId !== null && !shotIds.has(item.shotViewId))) {
    throw new Error('auxiliary.prompts contains an unknown shotViewId.');
  }
  if (auxiliary?.renderGuide?.queue.items.some((item) => item.shotViewId !== null && !shotIds.has(item.shotViewId))) {
    throw new Error('auxiliary.renderGuide.queue contains an unknown shotViewId.');
  }
  const targetSets = { 'narrative-beat': beatIds, 'script-scene': sceneIds, shot: shotIds };
  if (auxiliary?.review?.targets.some(
    (item) => item.targetViewId !== null && !targetSets[item.kind].has(item.targetViewId),
  )) throw new Error('auxiliary.review contains an unknown targetViewId.');
}

/** Strictly hydrate the backend camelCase Episode surface. */
export function storyWorkspaceParseEpisodeArtifactSurface(
  value: unknown,
): StoryWorkspaceEpisodeArtifactSurface {
  const record = storyWorkspaceEpisodeRecord(value, 'Episode artifact surface', [
    'runId', 'opaqueEpisodeId', 'manifestRevision', 'etag', 'bindingAvailability', 'bindingRecovery', 'artifacts', 'narrative', 'auxiliary',
  ]);
  const runId = storyWorkspaceEpisodeString(record.runId, 'runId', { pattern: STORY_WORKSPACE_EPISODE_RUN_ID });
  const bindingAvailability = storyWorkspaceEpisodeEnum(
    record.bindingAvailability,
    'bindingAvailability',
    ['bound', 'unbound'],
  );
  const opaqueEpisodeId = storyWorkspaceEpisodeNullableId(record.opaqueEpisodeId, 'opaqueEpisodeId');
  const manifestRevision = record.manifestRevision === null
    ? null
    : storyWorkspaceEpisodeString(record.manifestRevision, 'manifestRevision', { pattern: STORY_WORKSPACE_EPISODE_REVISION });
  const etag = record.etag === null
    ? null
    : storyWorkspaceEpisodeString(record.etag, 'etag', { pattern: STORY_WORKSPACE_EPISODE_REVISION });
  const bindingRecovery = storyWorkspaceParseEpisodeBindingRecovery(record.bindingRecovery);
  const artifacts = storyWorkspaceEpisodeArray(record.artifacts, 'artifacts', storyWorkspaceParseEpisodeManifestEntry, 256);
  storyWorkspaceEpisodeUnique(artifacts.map((item) => item.relativeKey), 'artifacts.relativeKey');
  const narrative = record.narrative === null ? null : storyWorkspaceParseEpisodeNarrative(record.narrative);
  const auxiliary = record.auxiliary === null ? null : storyWorkspaceParseEpisodeAuxiliary(record.auxiliary);
  if (bindingAvailability === 'bound') {
    if (opaqueEpisodeId === null || manifestRevision === null || etag === null) {
      throw new Error('bound Episode artifact surface requires identity and revisions.');
    }
    if (etag !== manifestRevision) throw new Error('etag must equal manifestRevision.');
    const expectedKeys = Object.keys(STORY_WORKSPACE_EPISODE_ARTIFACT_RULES);
    if (
      artifacts.length !== expectedKeys.length
      || expectedKeys.some((key) => !artifacts.some((item) => item.relativeKey === key))
    ) throw new Error('bound Episode artifact surface requires all six artifacts.');
    if (auxiliary !== null && auxiliary.manifestRevision !== manifestRevision) {
      throw new Error('auxiliary manifestRevision must equal manifestRevision.');
    }
  } else if (
    opaqueEpisodeId !== null
    || manifestRevision !== null
    || etag !== null
    || artifacts.length > 0
    || narrative !== null
    || auxiliary !== null
    || bindingRecovery.canDispatch
  ) throw new Error('unbound Episode artifact surface cannot contain artifacts.');
  const surface: StoryWorkspaceEpisodeArtifactSurface = {
    runId,
    opaqueEpisodeId,
    manifestRevision,
    etag,
    bindingAvailability,
    bindingRecovery,
    artifacts,
    narrative,
    auxiliary,
  };
  storyWorkspaceEpisodeAssertLinks(surface);
  return surface;
}
