// [Input] Original Deck/Voice mutation DTOs, Cookie/CSRF and optional platform HTTP.
// [Output] Existing create/update/delete/fork/sync requests and original errors.
// [Pos] Shared Deck mutation owner re-exported by voiceApi; native avoids unrelated editor/runtime imports.
// [Sync] 2026-10-29: move original functions unchanged except injected transport; Web defaults to fetch.
import type {DeckDetailsInput} from './voiceApi';
import {API_BASE} from '../lib/apiBase';
import {getBrowserCsrfToken,browserRequestHeaders} from '../lib/browserSession';

function getAuthHeaders():HeadersInit {
  const csrfToken=getBrowserCsrfToken();
  if(!csrfToken)throw new Error('Not authenticated');
  return {'Content-Type':'application/json',...browserRequestHeaders({},csrfToken)};
}

/**
 * Create a new deck
 */
export async function createDeck(data: DeckDetailsInput, transport: typeof fetch = fetch): Promise<{ deck_id: string }> {
  const response = await transport(`${API_BASE}/api/decks`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Create deck failed');
  }

  return await response.json();
}

/**
 * Update a deck (only user-owned decks)
 */
export async function updateDeck(deckId: string, data: {
  name?: string;
  name_zh?: string;
  name_en?: string;
  description?: string;
  description_zh?: string;
  description_en?: string;
  icon?: string;
  color?: string;
  enabled?: boolean;
  order_index?: number;
}, transport: typeof fetch = fetch): Promise<void> {
  const response = await transport(`${API_BASE}/api/decks/${deckId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Update deck failed');
  }
}

/**
 * Delete a deck (only user-owned decks, cascades to voices)
 */
export async function deleteDeck(deckId: string, transport: typeof fetch = fetch): Promise<void> {
  const response = await transport(`${API_BASE}/api/decks/${deckId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Delete deck failed');
  }
}

/**
 * Fork a deck (copy-on-write: creates user-owned copy of system deck)
 */
export async function forkDeck(deckId: string, transport: typeof fetch = fetch): Promise<{ deck_id: string }> {
  const response = await transport(`${API_BASE}/api/decks/${deckId}/fork`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Fork deck failed');
  }

  return await response.json();
}

/**
 * Sync deck with parent template (force overwrites local changes)
 */
export async function syncDeck(deckId: string, transport: typeof fetch = fetch): Promise<{ success: boolean; synced_voices: number }> {
  const response = await transport(`${API_BASE}/api/decks/${deckId}/sync`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Sync deck failed');
  }

  return await response.json();
}

/**
 * Create a new voice in a deck
 */
export async function createVoice(data: {
  deck_id: string;
  name: string;
  name_zh?: string;
  name_en?: string;
  system_prompt: string;
  icon: string;
  color: string;
}, transport: typeof fetch = fetch): Promise<{ voice_id: string }> {
  const response = await transport(`${API_BASE}/api/voices`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Create voice failed');
  }

  return await response.json();
}

/**
 * Update a voice (only voices in user-owned decks)
 */
export async function updateVoice(voiceId: string, data: {
  name?: string;
  name_zh?: string;
  name_en?: string;
  system_prompt?: string;
  icon?: string;
  color?: string;
  enabled?: boolean;
  order_index?: number;
  thread_id?: string;
}, transport: typeof fetch = fetch): Promise<void> {
  const response = await transport(`${API_BASE}/api/voices/${voiceId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Update voice failed');
  }
}

/**
 * Delete a voice (only voices in user-owned decks)
 */
export async function deleteVoice(voiceId: string, transport: typeof fetch = fetch): Promise<void> {
  const response = await transport(`${API_BASE}/api/voices/${voiceId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Delete voice failed');
  }
}

/**
 * Fork a voice to a target deck (copy-on-write: creates user-owned copy)
 */
export async function forkVoice(voiceId: string, targetDeckId: string, transport: typeof fetch = fetch): Promise<{ voice_id: string }> {
  const response = await transport(`${API_BASE}/api/voices/${voiceId}/fork`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ target_deck_id: targetDeckId })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Fork voice failed');
  }

  return await response.json();
}

