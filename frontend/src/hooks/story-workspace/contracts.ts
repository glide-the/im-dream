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
