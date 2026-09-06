// [Input] Authenticated Deck content-version endpoints and CAS error payloads.
// [Output] Strict client DTOs for draft state, preview, commit, and immutable history.
// [Pos] Deck aggregate version transport; runtime plugin semver stays in deckPluginApi.
// [Sync] 2026-08-16: add CozeLoop-inspired explicit Deck content commits.

import { STORAGE_KEYS } from '../constants/storageKeys';
import { apiUrl } from '../lib/apiBase';

export type DeckContentVersionStatus = 'unpublished' | 'draft' | 'published';

export interface DeckContentVersionState {
  deck_id: string;
  draft_revision: number;
  latest_version: number | null;
  published_draft_revision: number;
  dirty: boolean;
  status: DeckContentVersionStatus;
  next_version: number;
}

export interface DeckContentVersionChange {
  scope: 'deck' | 'agent_type' | 'agents' | 'claude_plugins' | 'runtime_binding';
  change_type: 'added' | 'removed' | 'modified';
  label: string;
  fields: string[];
}

export interface DeckContentVersionPreview extends DeckContentVersionState {
  target_version: number;
  changes: DeckContentVersionChange[];
  impact: string[];
}

export interface DeckContentVersionSummary {
  version: number;
  base_version: number | null;
  source_draft_revision: number;
  description: string | null;
  content_hash: string;
  created_by: number;
  created_at: string;
  runtime_plugin_version: string | null;
}

export interface DeckContentVersionHistory {
  deck_id: string;
  current: DeckContentVersionState;
  versions: DeckContentVersionSummary[];
}

export interface DeckContentVersionCommit {
  deck_id: string;
  version: DeckContentVersionSummary;
  state: DeckContentVersionState;
}

interface ErrorPayload {
  error_code?: string;
  message?: string;
  current_draft_revision?: number;
  current_version?: number | null;
}

export class DeckVersionApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly currentDraftRevision: number | null;
  readonly currentVersion: number | null;

  constructor(status: number, payload: ErrorPayload | null) {
    super(payload?.message || `Deck version request failed (${status})`);
    this.name = 'DeckVersionApiError';
    this.status = status;
    this.code = payload?.error_code ?? null;
    this.currentDraftRevision = payload?.current_draft_revision ?? null;
    this.currentVersion = payload?.current_version ?? null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  if (!token) throw new Error('Not authenticated');
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let payload: ErrorPayload | null = null;
    try { payload = await response.json() as ErrorPayload; } catch { /* structured body unavailable */ }
    throw new DeckVersionApiError(response.status, payload);
  }
  return await response.json() as T;
}

function root(deckId: string): string {
  return `/api/decks/${encodeURIComponent(deckId)}`;
}

export function getDeckContentVersionState(deckId: string): Promise<DeckContentVersionState> {
  return request(`${root(deckId)}/version-state`);
}

export function previewDeckContentVersion(
  deckId: string,
  state: Pick<DeckContentVersionState, 'draft_revision' | 'latest_version'>,
): Promise<DeckContentVersionPreview> {
  return request(`${root(deckId)}/versions/preview`, {
    method: 'POST',
    body: JSON.stringify({
      expected_draft_revision: state.draft_revision,
      expected_base_version: state.latest_version,
    }),
  });
}

export function commitDeckContentVersion(
  deckId: string,
  state: Pick<DeckContentVersionState, 'draft_revision' | 'latest_version'>,
  description: string,
): Promise<DeckContentVersionCommit> {
  return request(`${root(deckId)}/versions`, {
    method: 'POST',
    body: JSON.stringify({
      expected_draft_revision: state.draft_revision,
      expected_base_version: state.latest_version,
      description: description.trim() || null,
    }),
  });
}

export function listDeckContentVersions(deckId: string): Promise<DeckContentVersionHistory> {
  return request(`${root(deckId)}/versions`);
}
