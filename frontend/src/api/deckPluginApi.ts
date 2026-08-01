// [Input] Frozen task_210a Deck Plugin binding/options/validation API responses and browser auth state.
// [Output] Typed frontend-only consumers for the four Deck Plugin binding endpoints.
// [Pos] Deck Editor binding API client in frontend/src/api.

import { STORAGE_KEYS } from '../constants/storageKeys';
import { apiUrl } from '../lib/apiBase';

export type SelectionCompatibility = 'passed' | 'failed' | 'unknown';

export interface DeckPluginRecovery {
  owner: string;
  action: string;
}

export interface DeckPluginSelectionSummary {
  selectable: boolean;
  release_status: string;
  installation_status: string;
  compatibility: SelectionCompatibility;
  runtime_readiness: string;
  reason_code: string | null;
  recovery: DeckPluginRecovery | null;
  capability_summary: string[];
}

export interface DeckPluginOption extends DeckPluginSelectionSummary {
  display_name: string;
  deck_plugin_id: string;
  deck_plugin_version: string;
}

export interface DeckPluginBinding {
  deck_plugin_binding_id: string;
  deck_id: string;
  deck_plugin_id: string;
  deck_plugin_version: string;
  binding_revision: number;
  status: 'active' | 'stale';
  applied_to: 'next_run';
  selection_validation_summary: DeckPluginSelectionSummary;
}

export interface DeckPluginBindingState {
  deck_id: string;
  binding_revision: number;
  applied_to: 'next_run';
  binding: DeckPluginBinding | null;
}

export interface DeckPluginOptionsResponse {
  deck_id: string;
  applied_to: 'next_run';
  options: DeckPluginOption[];
}

export interface DeckPluginSelectionValidationResponse {
  deck_id: string;
  deck_plugin_id: string;
  deck_plugin_version: string;
  applied_to: 'next_run';
  validation: DeckPluginSelectionSummary;
}

export interface DeckPluginBindingUpdate {
  deck_plugin_id: string;
  deck_plugin_version: string;
  expected_binding_revision: number;
  apply_to: 'next_run';
}

interface DeckPluginErrorPayload {
  error_code?: string;
  current_revision?: number;
  validation?: DeckPluginSelectionSummary;
}

export class DeckPluginApiError extends Error {
  readonly status: number;
  readonly errorCode: string | null;
  readonly currentRevision: number | null;
  readonly validation: DeckPluginSelectionSummary | null;

  constructor(status: number, payload: DeckPluginErrorPayload | null) {
    super(`Deck Plugin request failed (${status})`);
    this.name = 'DeckPluginApiError';
    this.status = status;
    this.errorCode = payload?.error_code ?? null;
    this.currentRevision = payload?.current_revision ?? null;
    this.validation = payload?.validation ?? null;
  }
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  if (!token) throw new Error('Not authenticated');
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: 'include',
    headers: {
      ...authHeaders(),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let payload: DeckPluginErrorPayload | null = null;
    try {
      payload = await response.json() as DeckPluginErrorPayload;
    } catch {
      // The UI deliberately does not surface unstructured server content.
    }
    throw new DeckPluginApiError(response.status, payload);
  }

  return await response.json() as T;
}

function deckPath(deckId: string, suffix: string): string {
  return `/api/voice-decks/${encodeURIComponent(deckId)}${suffix}`;
}

export function getDeckPluginOptions(deckId: string): Promise<DeckPluginOptionsResponse> {
  return request(deckPath(deckId, '/plugin-options'));
}

export function getDeckPluginBinding(deckId: string): Promise<DeckPluginBindingState> {
  return request(deckPath(deckId, '/plugin-binding'));
}

export function updateDeckPluginBinding(
  deckId: string,
  input: DeckPluginBindingUpdate,
): Promise<DeckPluginBinding> {
  return request(deckPath(deckId, '/plugin-binding'), {
    method: 'PUT',
    body: JSON.stringify(input),
  });
}

export function validateDeckPluginSelection(
  deckId: string,
  deckPluginId: string,
  deckPluginVersion: string,
): Promise<DeckPluginSelectionValidationResponse> {
  return request(deckPath(deckId, '/plugin-binding/validate'), {
    method: 'POST',
    body: JSON.stringify({
      deck_plugin_id: deckPluginId,
      deck_plugin_version: deckPluginVersion,
      apply_to: 'next_run',
    }),
  });
}
