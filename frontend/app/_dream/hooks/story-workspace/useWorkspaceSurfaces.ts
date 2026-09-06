// [Input] Existing GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt
//         responses (whole-file passthrough of launch-manifest / pack-receipt).
// [Output] useWorkspaceSurfaces(threadId) → StoryWorkspaceSurface[] | undefined,
//          manifest-first with receipt fallback; pre-pack / legacy / error cases
//          all degrade to undefined ("no surface", DEC-028).
// [Pos] story-workspace hooks node - dream surface discovery seam (Task 2)
// [Sync] 2026-08-04: initial implementation; pure REST consumption, zero backend
//                    change, no filesystem probing from the frontend.

import { useEffect, useState } from 'react';
import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspacePluginLoadReceiptResponse,
  StoryWorkspaceSurface,
} from './contracts';

/** Path (without API base) of the existing whole-file passthrough endpoint. */
export function workspaceSurfacesEndpoint(threadId: string): string {
  return `/api/claude-agent/threads/${encodeURIComponent(threadId)}/plugin-load-receipt`;
}

function isStoryWorkspaceSurface(value: unknown): value is StoryWorkspaceSurface {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.name === 'string'
    && typeof candidate.protocol_dir === 'string'
    && typeof candidate.entry_route === 'string'
  );
}

function pickSurfaces(raw: unknown): StoryWorkspaceSurface[] | undefined {
  if (!Array.isArray(raw)) return undefined;
  const surfaces = raw.filter(isStoryWorkspaceSurface);
  // An empty list is indistinguishable from "no surface" (DEC-028).
  return surfaces.length > 0 ? surfaces : undefined;
}

/**
 * Resolve surfaces from a plugin-load-receipt payload: launch_manifest first,
 * receipt as fallback. workspace_found !== true (pre-pack window between thread
 * creation and the first agent turn's pack) means "no surface".
 */
export function resolveWorkspaceSurfaces(
  payload: StoryWorkspacePluginLoadReceiptResponse | null | undefined,
): StoryWorkspaceSurface[] | undefined {
  if (!payload || payload.workspace_found !== true) return undefined;
  return (
    pickSurfaces(payload.launch_manifest?.surfaces)
    ?? pickSurfaces(payload.receipt?.surfaces)
  );
}

export interface FetchWorkspaceSurfacesOptions {
  fetchImpl?: typeof fetch;
  token?: string | null;
  signal?: AbortSignal;
}

/**
 * Low-level REST seam. Any transport / HTTP / JSON failure degrades to
 * undefined — surface discovery must never surface an error to the UI.
 */
export async function fetchWorkspaceSurfaces(
  endpoint: string,
  options: FetchWorkspaceSurfacesOptions = {},
): Promise<StoryWorkspaceSurface[] | undefined> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const headers = new Headers({ Accept: 'application/json' });
  if (options.token) headers.set('Authorization', `Bearer ${options.token}`);

  let response: Response;
  try {
    response = await fetchImpl(endpoint, {
      credentials: 'include',
      headers,
      signal: options.signal ?? null,
    });
  } catch {
    return undefined;
  }
  if (!response.ok) return undefined;

  let payload: StoryWorkspacePluginLoadReceiptResponse;
  try {
    payload = await response.json() as StoryWorkspacePluginLoadReceiptResponse;
  } catch {
    return undefined;
  }
  return resolveWorkspaceSurfaces(payload);
}

/**
 * Discover story-workspace surfaces for a chat thread.
 *
 * Returns undefined (not an empty array) whenever the session has no surfaces:
 * legacy sessions, pre-pack threads, unknown threads, or any failure. Consumers
 * treat undefined as "hide the entry point" (DEC-028).
 */
export function useWorkspaceSurfaces(
  threadId: string | null | undefined,
): StoryWorkspaceSurface[] | undefined {
  const [surfaces, setSurfaces] = useState<StoryWorkspaceSurface[] | undefined>(undefined);

  useEffect(() => {
    if (!threadId) {
      setSurfaces(undefined);
      return;
    }
    const controller = new AbortController();
    void fetchWorkspaceSurfaces(apiUrl(workspaceSurfacesEndpoint(threadId)), {
      token: getAuthToken(),
      signal: controller.signal,
    }).then((resolved) => {
      if (!controller.signal.aborted) setSurfaces(resolved);
    });
    return () => controller.abort();
  }, [threadId]);

  return surfaces;
}
