// [Input] Authenticated Claude-thread production endpoints and optional Deck ownership filter.
// [Output] Typed create/list/delete helpers shared by Chat history and Deck related-conversation management.
// [Pos] Chat history transport owner in frontend/src/api.
// [Sync] 2026-08-17: centralize Chat history transport and expose actor-scoped Deck filtering.
// [Sync] 2026-09-01: allow product-owned Thread titles without attaching a Deck or Voice.

import { getAuthToken } from '../contexts/AuthContext';
import { API_BASE } from '../lib/apiBase';

export interface ChatHistoryThread {
  id: string;
  title: string | null;
  deck_id?: string | null;
  voice_id?: string | null;
  created_at: string;
  updated_at: string;
  match?: {
    strategy: string;
    retriever?: string;
    score: number;
    fields: string[];
    excerpt?: string;
  };
}

export interface ChatThreadSearchParams {
  deckId?: string;
  query?: string;
  searchScope?: 'all' | 'title' | 'messages';
  retrievalMode?: 'fuzzy' | 'auto' | 'vector';
  limit?: number;
  offset?: number;
}

function authHeaders(): HeadersInit {
  return { Authorization: `Bearer ${getAuthToken()}` };
}

export async function createChatThread(
  deckId?: string,
  voiceId?: string,
  title?: string,
): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE}/api/claude-agent/threads`, {
      method: 'POST',
      headers: {
        ...authHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...(deckId ? { deckId } : {}),
        ...(voiceId ? { voiceId } : {}),
        ...(title?.trim() ? { title: title.trim() } : {}),
      }),
    });
    if (!response.ok) return null;
    const data = await response.json() as { thread_id?: string };
    return data.thread_id ?? null;
  } catch {
    return null;
  }
}

export async function listChatThreads(
  params: ChatThreadSearchParams = {},
): Promise<ChatHistoryThread[]> {
  const search = new URLSearchParams();
  const query = params.query?.trim() ?? '';
  if (params.deckId) search.set('deck_id', params.deckId);
  if (query) {
    search.set('query', query);
    search.set('search_scope', params.searchScope ?? 'all');
    search.set('retrieval_mode', params.retrievalMode ?? 'fuzzy');
  }
  if (typeof params.limit === 'number') search.set('limit', String(params.limit));
  if (typeof params.offset === 'number' && params.offset > 0) search.set('offset', String(params.offset));

  const suffix = search.size > 0 ? `?${search.toString()}` : '';
  const response = await fetch(`${API_BASE}/api/claude-agent/threads${suffix}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || 'Chat history could not be loaded.');
  }
  const data = await response.json() as { threads?: ChatHistoryThread[] };
  return data.threads ?? [];
}

export async function deleteChatThread(threadId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/claude-agent/threads/${encodeURIComponent(threadId)}`,
    { method: 'DELETE', headers: authHeaders() },
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || 'Chat conversation could not be deleted.');
  }
}
