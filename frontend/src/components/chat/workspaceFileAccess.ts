// [Input] Strictly parsed Workspace URI, current Chat Thread identity, bearer auth state, and optional abort signal.
// [Output] Shared authenticated Workspace content response/image blob helpers with stable failure classification.
// [Pos] workspace file runtime access utility in frontend/src/components/chat
// [Sync] 2026-08-23: extract the existing file fetch/MIME boundary so live Markdown and long-image export share one authenticated path.

import { getAuthToken } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type { WorkspaceUriParseResult } from './workspaceUri';

const INLINE_IMAGE_MIME_TYPES = new Set([
  'image/gif',
  'image/jpeg',
  'image/png',
  'image/webp',
]);

export type WorkspaceFileRequestFailure =
  | 'access'
  | 'disabled'
  | 'invalid'
  | 'missing'
  | 'retryable'
  | 'unsupported';

export class WorkspaceFileRequestError extends Error {
  readonly failure: WorkspaceFileRequestFailure;

  constructor(failure: WorkspaceFileRequestFailure) {
    super(failure);
    this.failure = failure;
  }
}

function contentUrl(threadId: string, path: string): string {
  const query = new URLSearchParams({ sessionId: threadId, path });
  return apiUrl(`/api/workspace/files/content?${query.toString()}`);
}

function failureFromStatus(status: number): WorkspaceFileRequestFailure {
  if (status === 400) return 'invalid';
  if (status === 401 || status === 403) return 'access';
  if (status === 404) return 'missing';
  if (status === 409) return 'disabled';
  return 'retryable';
}

export async function fetchWorkspaceFile(
  parsed: Extract<WorkspaceUriParseResult, { ok: true }>,
  threadId: string,
  signal?: AbortSignal,
): Promise<Response> {
  const token = getAuthToken();
  if (!token) throw new WorkspaceFileRequestError('access');
  const response = await fetch(contentUrl(threadId, parsed.path), {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });
  if (!response.ok) throw new WorkspaceFileRequestError(failureFromStatus(response.status));
  return response;
}

export async function fetchWorkspaceImageBlob(
  parsed: Extract<WorkspaceUriParseResult, { ok: true }>,
  threadId: string,
  signal?: AbortSignal,
): Promise<Blob> {
  const response = await fetchWorkspaceFile(parsed, threadId, signal);
  const mimeType = (response.headers.get('content-type') ?? '')
    .split(';', 1)[0]
    .trim()
    .toLocaleLowerCase('en-US');
  if (!INLINE_IMAGE_MIME_TYPES.has(mimeType)) {
    throw new WorkspaceFileRequestError('unsupported');
  }
  return response.blob();
}
