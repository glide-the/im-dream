// [Input] Authenticated Story Workspace detail, patch, and review endpoints.
// [Output] Typed review mutations used by Dream's canonical review panel.
// [Pos] Frontend Story Workspace review API adapter.

import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';
import type {
  StoryWorkspaceCharacter,
  StoryWorkspaceScene,
  StoryWorkspaceStory,
} from '../hooks/story-workspace';

export type StoryWorkspaceReviewResourceType = 'story' | 'character' | 'scene';

export interface StoryWorkspaceStoryDetail extends StoryWorkspaceStory {
  review_notes?: string | null;
  characters?: StoryWorkspaceCharacter[];
  scenes?: StoryWorkspaceScene[];
  execution?: {
    action: 'publish_story_bundle';
    status: 'completed';
    completed_at?: string | null;
  };
}

export interface StoryWorkspaceCharacterDetail extends StoryWorkspaceCharacter {
  background?: string | null;
  catchphrase?: string | null;
  review_notes?: string | null;
}

export interface StoryWorkspaceSceneDetail extends StoryWorkspaceScene {
  review_notes?: string | null;
  story?: StoryWorkspaceStory | null;
  characters?: StoryWorkspaceCharacter[];
}

export type StoryWorkspaceReviewResource =
  | StoryWorkspaceStoryDetail
  | StoryWorkspaceCharacterDetail
  | StoryWorkspaceSceneDetail;

export interface BatchReviewResult {
  success: boolean;
  action: 'confirm' | 'reject';
  resource_type: StoryWorkspaceReviewResourceType;
  total_requested: number;
  total_updated: number;
  skipped_ids: string[];
}

const RESOURCE_PATHS: Record<StoryWorkspaceReviewResourceType, string> = {
  story: 'stories',
  character: 'characters',
  scene: 'scenes',
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body !== undefined) headers.set('Content-Type', 'application/json');
  headers.set('Accept', 'application/json');
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
    headers,
  });
  if (!response.ok) {
    // Review surfaces never render arbitrary server detail because it may carry
    // implementation locators. The status is enough for a safe retry message.
    throw new Error(`Story Workspace 请求失败（${response.status}）`);
  }
  return response.json() as Promise<T>;
}

export function getReviewResource(
  resourceType: StoryWorkspaceReviewResourceType,
  resourceId: string,
): Promise<StoryWorkspaceReviewResource> {
  return request(
    `/api/story-workspace/${RESOURCE_PATHS[resourceType]}/${encodeURIComponent(resourceId)}`,
  );
}

export function patchReviewResource(
  resourceType: StoryWorkspaceReviewResourceType,
  resourceId: string,
  patch: Record<string, unknown>,
): Promise<StoryWorkspaceReviewResource> {
  return request(
    `/api/story-workspace/${RESOURCE_PATHS[resourceType]}/${encodeURIComponent(resourceId)}`,
    { method: 'PATCH', body: JSON.stringify(patch) },
  );
}

export function confirmReviewResource(
  resourceType: StoryWorkspaceReviewResourceType,
  resourceId: string,
): Promise<StoryWorkspaceReviewResource> {
  return request(
    `/api/story-workspace/${RESOURCE_PATHS[resourceType]}/${encodeURIComponent(resourceId)}/confirm`,
    { method: 'POST', body: JSON.stringify({}) },
  );
}

export function rejectReviewResource(
  resourceType: StoryWorkspaceReviewResourceType,
  resourceId: string,
  reviewNotes: string,
): Promise<StoryWorkspaceReviewResource> {
  return request(
    `/api/story-workspace/${RESOURCE_PATHS[resourceType]}/${encodeURIComponent(resourceId)}/reject`,
    { method: 'POST', body: JSON.stringify({ review_notes: reviewNotes }) },
  );
}

export function batchReviewResources(
  resourceType: StoryWorkspaceReviewResourceType,
  ids: string[],
  action: 'confirm' | 'reject',
  reviewNotes?: string,
): Promise<BatchReviewResult> {
  return request('/api/story-workspace/batch', {
    method: 'POST',
    body: JSON.stringify({
      action,
      ids,
      resource_type: resourceType,
      ...(reviewNotes ? { review_notes: reviewNotes } : {}),
    }),
  });
}
