// [Input] Deck Plugin binding/options/validation and capability-backed Agent-type responses.
// [Output] Typed consumers for binding endpoints plus optimistic Chat/Dream Agent selection.
// [Pos] Deck Editor binding API client in frontend/src/api.
// [Sync] 2026-08-14: add `chat | dream` Agent type update without exposing plugin IDs to UI copy.
// [Sync] 2026-08-16: restore the pre-01a00576 Agent-type and plugin-reference client
//                    used by the full Deck maintenance popup.

import { STORAGE_KEYS } from '../constants/storageKeys';
import { apiUrl } from '../lib/apiBase';

export type SelectionCompatibility = 'passed' | 'failed' | 'unknown';
export type DeckAgentType = 'chat' | 'dream';

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

export interface DeckPluginBindingHistoryEntry {
  deck_plugin_binding_id: string;
  deck_plugin_id: string;
  deck_plugin_version: string;
  binding_revision: number;
  status: 'active' | 'stale';
  applied_to: 'next_run';
  created_at: string;
  updated_at: string;
}

export interface DeckPluginBindingHistoryResponse {
  deck_id: string;
  current_binding_revision: number;
  entries: DeckPluginBindingHistoryEntry[];
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

export interface DeckAgentTypeResponse {
  deck_id: string;
  agent_type: DeckAgentType;
  binding_revision: number;
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

export function getDeckPluginBindingHistory(
  deckId: string,
): Promise<DeckPluginBindingHistoryResponse> {
  return request(deckPath(deckId, '/plugin-binding/history'));
}

export function updateDeckAgentType(
  deckId: string,
  agentType: DeckAgentType,
  expectedBindingRevision: number,
): Promise<DeckAgentTypeResponse> {
  return request(deckPath(deckId, '/agent-type'), {
    method: 'PUT',
    body: JSON.stringify({
      agent_type: agentType,
      expected_binding_revision: expectedBindingRevision,
    }),
  });
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
