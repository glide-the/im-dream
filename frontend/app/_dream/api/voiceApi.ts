// [Sync] 2026-10-29: inject native HTTP into the original Timeline read helpers; Web signatures and defaults remain compatible.
// [Sync] 2026-10-29: re-export the original Reflections domain API for Web/native reuse; remaining session and Chat behavior stays here.
// [Sync] 2026-10-29: re-export the original Deck mutation owner; preserve default Web transport and lazy voice-thread association.
// [Sync] 2026-10-28: load enabled Voice configs from one shared Deck/Agent catalog read.
// [Sync] 2026-10-14: expose strict analysis-created history pages with decimal IDs and exact cursors.
// [Sync] 2026-10-28: share Deck reads while retaining local bindings for the existing voice-list fallback.
// [Sync] 2026-09-14: same-origin Cookie session with in-memory CSRF; no Browser OAuth Bearer/storage.
import { getBrowserCsrfToken, browserRequestHeaders } from '../lib/browserSession';
// [Sync] 2026-10-13: pass per-task analysis selection, read candidates and retry the original task report.
// [Sync] 2026-10-13: prepared tasks start only through an explicit resume action after SSE subscription.
// [Sync] 2026-10-23: task creation selects Notion scope; body-read errors occur during Agent execution.
// [Input] Consume backend REST/SSE endpoints, same-origin session and in-memory CSRF, language storage, and session/deck request data.
// [Output] Provide frontend API helpers for sessions, decks, voices, Claude Agent SSE calls, analysis reports,
//          Reflections section analysis, and Reflections section config (GET/PUT/DELETE).
// [Pos] voice-api client node in frontend/app/_dream/api
// [Sync] 2026-06-06: remove Voice scenario memory workspace initialization (initializeMemoryWorkspace removed).
// [Sync] 2026-06-06: add ReflectionSectionConfig type + getReflectionsSectionConfig /
//         saveReflectionsSectionConfig / resetReflectionsSectionConfig API helpers for
//         frontend prompt-file editing (GET/PUT/DELETE /api/reflections/config/{section}).
// [Sync] 2026-06-12: consume centralized runtime API_BASE for cross-origin deployments.
// [Sync] 2026-06-25: Reflections analysis now uses backend Reflections-agent tasks:
//         POST task(auto_start=false) → subscribe SSE → POST start → stream events → fetch results.
// [Sync] 2026-08-14: add explicit default screenplay Deck plugin reconciliation.
// [Sync] 2026-08-15: reconciliation may create a missing actor default for legacy accounts.
// [Sync] 2026-08-14: consume server-derived Deck Agent type and binding revision
//                    in list/detail DTOs; the browser does not infer Dream capability.
// [Sync] 2026-08-16: centralize the lightweight Deck create/update metadata input used by the
//                    settings-style management surface; remove active marketplace list/publish transports.
// [Sync] 2026-08-16: consume capability-backed Deck content vN and draft state in list/detail DTOs.
// [Sync] 2026-08-17: carry server sharing-policy facts only for system-initialized Deck display.
// [Sync] 2026-08-31: route debounced Writing inspiration through the existing
//                    Claude Agent SSE voice thread instead of the retired PolyCLI session.
// [Sync] 2026-08-31: remove the automatic analyze_text transport retired from EditorEngine.
// [Sync] 2026-08-31: remove the retired daily-picture generation and save transports; Timeline is read-only for historical pictures.
// [Sync] 2026-09-01: expose one product-neutral Claude Agent turn streamer that
//                    reuses the shared SSE parser; remove random-Voice Writing suggestions.
/**
 * API client for voice analysis backend - FastAPI sync API version
 * [Sync] 2026-06-01: normalize user_sessions.labels in session API responses for frontend display.
 * [Sync] 2026-06-25: analyzeEchoes/analyzeTraits/analyzePatterns now use backend
 *         Reflections-agent async tasks with SSE-first start control.
 */

import { STORAGE_KEYS } from '../constants/storageKeys';
import { API_BASE } from '../lib/apiBase';
import {listDecks, getDeck, listDecksWithVoices} from './deckReadApi';
import {updateVoice} from './deckMutationApi';
export {createDeck,updateDeck,deleteDeck,forkDeck,syncDeck,createVoice,updateVoice,deleteVoice,forkVoice} from './deckMutationApi';
import type { EditorState } from '../engine/EditorEngine';
import { consumeClaudeAgentSseStream } from '../lib/claude-agent-sse-utils';
import { ClaudeAgentTransportError } from '../lib/claude-agent-transport';

// ========== Inline Types (workaround for Vite bug) ==========
export interface VoiceConfig {
  name: string;
  systemPrompt: string;
  enabled: boolean;
  icon: string;
  color: string;
  thread_id?: string;
  memory_workspace_config?: Record<string, unknown>;
}

export interface UserState {
  name: string;
  prompt: string;
}

export interface StateConfig {
  greeting: string;
  states: Record<string, UserState>;
}

export type SessionLabels = string[];

export interface UserSession {
  id: string;
  name?: string | null;
  labels: SessionLabels;
  editor_state: EditorState | null;
  created_at: string;
  updated_at: string;
  date_key?: string | null;
  first_line?: string | null;
}

export interface Voice {
  id: string;
  deck_id: string;
  name: string;
  name_zh?: string;
  name_en?: string;
  system_prompt: string;
  icon: string;
  color: string;
  is_system: boolean;
  parent_id?: string;
  owner_id?: number;
  enabled: boolean;
  order_index?: number;
  thread_id?: string;
  memory_workspace_config?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface Deck {
  id: string;
  name: string;
  name_zh?: string;
  name_en?: string;
  description?: string;
  description_zh?: string;
  description_en?: string;
  icon?: string;
  color?: string;
  is_system: boolean;
  parent_id?: string;
  owner_id?: number;
  enabled: boolean;
  order_index?: number;
  voice_count?: number;
  voices?: Voice[];
  created_at?: string;
  updated_at?: string;
  /** Server-derived from the active published Deck Plugin capability. */
  agent_type: 'chat' | 'dream';
  /** Optimistic-lock token for Agent type changes. */
  agent_type_revision: number;
  /** Exact active runtime plugin identity; never an aggregate Deck version. */
  deck_plugin_id?: string | null;
  deck_plugin_version?: string | null;
  /** Admin-capability-backed aggregate content version facts. */
  deck_version_capability?: boolean;
  deck_version?: number | null;
  draft_revision?: number;
  deck_version_dirty?: boolean;
  deck_version_status?: 'unpublished' | 'draft' | 'published';
  next_deck_version?: number;
  /** Server-owned sharing policy facts; used only to distinguish system-initialized defaults. */
  can_publish?: boolean;
  publish_block_reason?: string | null;
}

export interface DeckDetailsInput {
  name: string;
  description?: string;
  icon?: string;
  color?: string;
}

export function normalizeSessionLabels(labels: unknown): SessionLabels {
  if (!Array.isArray(labels)) return [];

  return labels
    .map(label => String(label).trim())
    .filter(label => label.length > 0);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

function optionalNullableString(value: unknown): string | null | undefined {
  return value === null ? null : optionalString(value);
}

function isEditorState(value: unknown): value is EditorState {
  if (!isRecord(value) || typeof value.id !== 'string' || !Array.isArray(value.cells)) return false;
  return Array.isArray(value.commentors)
    && Array.isArray(value.tasks)
    && Array.isArray(value.weightPath)
    && Array.isArray(value.overlappedPhrases)
    && Array.isArray(value.notFoundPhrases);
}

function normalizeUserSession(session: unknown): UserSession {
  const value = isRecord(session) ? session : {};
  return {
    id: optionalString(value.id) ?? '',
    name: optionalNullableString(value.name),
    labels: normalizeSessionLabels(value.labels),
    editor_state: isEditorState(value.editor_state) ? value.editor_state : null,
    created_at: optionalString(value.created_at) ?? '',
    updated_at: optionalString(value.updated_at) ?? '',
    date_key: optionalNullableString(value.date_key),
    first_line: optionalNullableString(value.first_line),
  };
}

/**
 * Get auth headers for authenticated requests
 */
function getAuthHeaders(): HeadersInit {
  const csrfToken = getBrowserCsrfToken();
  if (!csrfToken) {
    throw new Error('Not authenticated');
  }
  return {
    'Content-Type': 'application/json',
    ...browserRequestHeaders({}, csrfToken)
  };
}


/**
 * Get default voices from backend
 */
export async function getDefaultVoices(): Promise<Record<string, Omit<VoiceConfig, 'name' | 'enabled'>>> {
  const response = await fetch(`${API_BASE}/api/default-voices`);
  return await response.json() as Record<string, Omit<VoiceConfig, 'name' | 'enabled'>>;
}

/**
 * Stream one existing Claude Agent Thread through the shared SSE protocol.
 * Callers own the Thread identity and product/Voice system prompt; this transport
 * only projects ordered deltas, terminal completion, and structured failures.
 */
export async function streamClaudeAgentTurn({
  threadId,
  message,
  systemPrompt,
  editorState,
  onDelta,
  onReasoningDelta,
  onReasoningEnd,
  onComplete,
  onError,
  signal,
}: {
  threadId: string;
  message: string;
  systemPrompt: string;
  /** Current EditorState snapshot forwarded to the backend agent runner as editor_state. */
  editorState?: Record<string, unknown> | null;
  onDelta: (delta: string) => void;
  /** Called for each incremental reasoning/thinking chunk. */
  onReasoningDelta?: (delta: string) => void;
  /** Called once when the reasoning block finishes (reasoning-end received). */
  onReasoningEnd?: () => void;
  /** Called with (fullResponseText, fullReasoningText) when the stream completes. */
  onComplete: (fullText: string, reasoning?: string) => void;
  onError: (error: Error) => void;
  signal?: AbortSignal;
}): Promise<void> {
  const csrfToken = getBrowserCsrfToken();

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/claude-agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...browserRequestHeaders({}, csrfToken),
      },
      body: JSON.stringify({
        id: threadId,
        resume: true,
        message: {
          id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}-writing`,
          role: 'user',
          parts: [{ type: 'text', text: message }],
        },
        toolChoice: 'auto',
        allowedAppDefaultToolkit: [],
        allowedMcpServers: {},
        attachments: [],
        systemPrompt,
        ...(editorState != null ? { editor_state: editorState } : {}),
      }),
      signal,
    });
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
    return;
  }

  if (!response.ok || !response.body) {
    onError(new Error(`Claude-agent request failed: ${response.status}`));
    return;
  }

  const reader = response.body.getReader();
  let accumulated = '';
  let accumulatedReasoning = '';
  let settled = false;

  try {
    await consumeClaudeAgentSseStream(reader, (event) => {
      if (event.type === 'text-delta' && typeof event.delta === 'string') {
        accumulated += event.delta;
        onDelta(event.delta);
      } else if (event.type === 'reasoning-delta' && typeof event.delta === 'string') {
        accumulatedReasoning += event.delta;
        onReasoningDelta?.(event.delta);
      } else if (event.type === 'reasoning-end') {
        onReasoningEnd?.();
      } else if (event.type === 'error') {
        settled = true;
        onError(new ClaudeAgentTransportError({
          type: 'error',
          errorText: typeof event.errorText === 'string' ? event.errorText : 'Claude-agent error',
          errorCode: typeof event.errorCode === 'string' ? event.errorCode : undefined,
          retryable: typeof event.retryable === 'boolean' ? event.retryable : undefined,
          retryAfterSeconds: typeof event.retryAfterSeconds === 'number'
            ? event.retryAfterSeconds
            : undefined,
        }));
        return false;
      } else if (event.type === 'finish') {
        settled = true;
        onComplete(accumulated, accumulatedReasoning || undefined);
        return false;
      }
      return true;
    });
    if (!settled) {
      onError(new Error('Claude-agent stream ended before finish'));
    }
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

/** Voice chat compatibility alias; product-neutral Writing calls the generic name. */
export const chatWithVoiceSSE = streamClaudeAgentTurn;

export interface VoiceChatResult {
  response: string;
  thread_id: string;
}

/** Chat with a historical inline comment through the same Voice Claude Thread. */
export async function chatWithVoice(
  voiceId: string,
  voice: VoiceConfig,
  conversationHistory: Array<{ role: string; content: string }>,
  userMessage: string,
  originalText?: string,
  metaPrompt?: string,
  statePrompt?: string,
  resolvedThreadId?: string,
): Promise<VoiceChatResult> {
  const threadId = await ensureVoiceThread(
    voiceId,
    voice.thread_id || resolvedThreadId,
  );
  let systemPrompt = `You are ${voice.name}, an inner voice persona.
Your role: ${voice.systemPrompt}

Respond in character. Be concise and focus on your distinct perspective.`;
  if (originalText?.trim()) {
    systemPrompt += `\n\nThe user is writing this text:\n---\n${originalText.trim()}\n---`;
  }
  if (metaPrompt?.trim()) {
    systemPrompt += `\n\nAdditional writing guidance:\n${metaPrompt.trim()}`;
  }
  if (statePrompt?.trim()) {
    systemPrompt += `\n\nThe user's current state:\n${statePrompt.trim()}`;
  }

  const serializedHistory = conversationHistory
    .map((entry) => `${entry.role === 'assistant' ? voice.name : 'User'}: ${entry.content}`)
    .join('\n');
  const message = serializedHistory
    ? `Previous inline-comment conversation:\n${serializedHistory}\n\nUser: ${userMessage}`
    : userMessage;
  const response = await new Promise<string>((resolve, reject) => {
    void chatWithVoiceSSE({
      threadId,
      message,
      systemPrompt,
      onDelta: () => undefined,
      onComplete: (fullText) => resolve(fullText.trim()),
      onError: reject,
    });
  });
  return {
    response: response || 'Sorry, I could not respond.',
    thread_id: threadId,
  };
}

// ========== Authenticated Endpoints (require login) ==========

/**
 * Import localStorage data to database (one-time migration)
 */
export interface ImportSummary {
  sessions: number;
  pictures: number;
  preferences: number;
  reports: number;
}

export async function importLocalData(data: {
  currentSession?: string;
  calendarEntries?: string;
  dailyPictures?: string;
  voiceCustomizations?: string;
  metaPrompt?: string;
  stateConfig?: string;
  selectedState?: string;
  analysisReports?: string;
  oldDocument?: string;
}): Promise<{ success: boolean; imported: ImportSummary }> {
  const response = await fetch(`${API_BASE}/api/import-local-data`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    // Handle 413 Payload Too Large (nginx returns HTML, not JSON)
    if (response.status === 413) {
      throw new Error('413: Request too large - your data exceeds the server limit');
    }

    // Try to parse JSON error response
    try {
      const error = await response.json();
      throw new Error(error.detail || 'Import failed');
    } catch {
      // If JSON parsing fails, throw generic error with status
      throw new Error(`Import failed with status ${response.status}`);
    }
  }

  return await response.json();
}

/**
 * Save session to database
 */
export async function saveSession(sessionId: string, editorState: EditorState, name?: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      session_id: sessionId,
      editor_state: editorState,
      name
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Save session failed');
  }
}

type SessionRangeOptions = {
  startDate?: string;
  endDate?: string;
  limit?: number;
};

/**
 * List sessions metadata, optionally scoped to a date range.
 */
export async function listSessions(timezone?: string, options: SessionRangeOptions = {}, transport:typeof fetch=fetch): Promise<UserSession[]> {
  const params = new URLSearchParams();
  if (timezone) params.append('timezone', timezone);
  if (options.startDate) params.append('start_date', options.startDate);
  if (options.endDate) params.append('end_date', options.endDate);
  const endpoint = options.startDate || options.endDate ? '/api/sessions/range' : '/api/sessions';
  const query = params.toString();

  const response = await transport(`${API_BASE}${endpoint}${query ? `?${query}` : ''}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'List sessions failed');
  }

  const data = await response.json();
  return (data.sessions || []).map(normalizeUserSession);
}

/**
 * Get a specific session
 */
export async function getSession(sessionId: string): Promise<UserSession> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get session failed');
  }

  return normalizeUserSession(await response.json());
}

/**
 * Fetch multiple sessions (with editor_state) in a single request.
 */
export async function getSessionsBatch(sessionIds: string[], transport:typeof fetch=fetch): Promise<UserSession[]> {
  if (!sessionIds || sessionIds.length === 0) return [];

  const response = await transport(`${API_BASE}/api/sessions/batch`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ ids: sessionIds })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Batch session fetch failed');
  }

  const data = await response.json();
  return (data.sessions || []).map(normalizeUserSession);
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Delete session failed');
  }
}

/**
 * Get daily pictures (thumbnails only for fast timeline loading)
 */
type PictureRangeOptions = {
  startDate?: string;
  endDate?: string;
  limit?: number;
};

export interface DailyPicture {
  date: string;
  base64: string;
  full_base64?: string;
  prompt: string;
}

export async function getDailyPictures(limit: number = 30, options: PictureRangeOptions = {}, transport:typeof fetch=fetch): Promise<DailyPicture[]> {
  const params = new URLSearchParams();
  params.append('limit', String(options.limit ?? limit));
  if (options.startDate) params.append('start_date', options.startDate);
  if (options.endDate) params.append('end_date', options.endDate);
  const endpoint = options.startDate || options.endDate ? '/api/pictures/range' : '/api/pictures';
  const query = params.toString();

  const response = await transport(`${API_BASE}${endpoint}${query ? `?${query}` : ''}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get pictures failed');
  }

  const data = await response.json() as { pictures?: DailyPicture[] };
  return data.pictures ?? [];
}

/**
 * Get full resolution image for a specific date (on-demand loading)
 */
export async function getDailyPictureFull(date: string, transport:typeof fetch=fetch): Promise<string> {
  const response = await transport(`${API_BASE}/api/pictures/${date}/full`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get full picture failed');
  }

  const data = await response.json();
  return data.image_base64;
}

/**
 * Save user preferences
 */
export interface UserPreferences {
  voice_configs?: Record<string, VoiceConfig>;
  meta_prompt?: string;
  state_config?: StateConfig;
  selected_state?: string;
  timezone?: string;
  first_login_completed?: boolean;
  updated_at?: string;
}

export async function savePreferences(preferences: UserPreferences): Promise<void> {
  const response = await fetch(`${API_BASE}/api/preferences`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(preferences)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Save preferences failed');
  }
}

/**
 * Get user preferences
 */
export async function getPreferences(transport:typeof fetch=fetch): Promise<UserPreferences> {
  const response = await transport(`${API_BASE}/api/preferences`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get preferences failed');
  }

  return await response.json() as UserPreferences;
}

/**
 * Mark first login as completed (after migration dialog)
 */
export async function markFirstLoginCompleted(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/mark-first-login-completed`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Mark first login completed failed');
  }
}

// ========== Deck System API ==========

/**
 * List all decks (includes system decks + user's own decks)
 */
export {listDecks, getDeck, listDecksWithVoices};

/**
 * Ensure the actor's screenplay default exists and reconcile empty plugin refs.
 * Existing Decks and user selections are preserved by the backend.
 */
export async function reconcileDefaultDeckPlugin(): Promise<{
  deck_id: string | null;
  reconciled: boolean;
  // `default_not_found` keeps the client compatible with an older backend
  // during a rolling restart; current servers create the missing default.
  reason: 'default_created' | 'missing_ref' | 'refs_preserved' | 'default_not_found';
}> {
  const response = await fetch(`${API_BASE}/api/decks/defaults/reconcile`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Reconcile default Deck plugin failed');
  }

  return await response.json();
}

/**
 * Create a Claude-agent thread and associate it with a voice (lazy).
 * If the voice already has a thread_id, returns it unchanged.
 * Otherwise creates a new thread, persists it on the voice, and returns the id.
 */
export async function ensureVoiceThread(voiceId: string, existingThreadId?: string): Promise<string> {
  if (existingThreadId) {
    return existingThreadId;
  }

  const csrfToken = getBrowserCsrfToken();
  if (!csrfToken) throw new Error('Not authenticated');

  // Create a new Claude-agent thread
  const res = await fetch(`${API_BASE}/api/claude-agent/threads`, {
    method: 'POST',
    headers: { ...browserRequestHeaders({}, csrfToken) }
  });
  if (!res.ok) throw new Error('Failed to create Claude-agent thread');
  const { thread_id } = await res.json() as { thread_id: string };

  // Persist the association on the voice (best-effort; non-system voices only)
  try {
    await updateVoice(voiceId, { thread_id });
  } catch {
    // Ignore if voice update fails (e.g. system voice) - thread_id is still usable
  }

  return thread_id;
}

// ========== Voice Config Loading ==========

/**
 * @@@ Load all enabled voices from all enabled decks and convert to VoiceConfig format
 * This bridges the new deck system with the existing voice analysis system
 */
export async function loadVoicesFromDecks(): Promise<Record<string, VoiceConfig>> {
  try {
    const decks = await listDecksWithVoices();
    const voiceConfigs: Record<string, VoiceConfig> = {};

    for (const deck of decks) {
      if (!deck.enabled) continue;
      for (const voice of deck.voices || []) {
        if (!voice.enabled) continue;
        voiceConfigs[voice.id] = {
          name: voice.name,
          systemPrompt: voice.system_prompt,
          enabled: voice.enabled,
          icon: voice.icon,
          color: voice.color,
          thread_id: voice.thread_id,
          memory_workspace_config: voice.memory_workspace_config,
        };
      }
    }

    return voiceConfigs;
  } catch (err) {
    console.error('Failed to load voices from decks:', err);
    // Return empty object if loading fails - app can fall back to localStorage
    return {};
  }
}

// ========== Friend System API ==========

export interface FriendInvite {
  code: string;
  expires_at: string;
  created_at: string;
}

export interface FriendRequest {
  id: number;
  requester_id: number;
  requester_name: string;
  requester_email: string;
  created_at: string;
}

export interface Friend {
  id: number;
  user_id: number;
  friend_id: number;
  friend_name: string;
  friend_email: string;
  created_at: string;
}

/**
 * Generate a new friend invite code (6 chars, 7 days validity)
 */
export async function generateInviteCode(): Promise<FriendInvite> {
  const response = await fetch(`${API_BASE}/api/friends/invite/generate`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Generate invite code failed');
  }

  return await response.json();
}

/**
 * Use an invite code to send a friend request
 */
export async function useInviteCode(code: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/api/friends/invite/use`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ code })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Use invite code failed');
  }

  return await response.json();
}

/**
 * Get all pending friend requests for current user
 */
export async function getFriendRequests(): Promise<FriendRequest[]> {
  const response = await fetch(`${API_BASE}/api/friends/requests`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get friend requests failed');
  }

  const data = await response.json();
  return data.requests;
}

/**
 * Accept a friend request
 */
export async function acceptFriendRequest(requestId: number): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/api/friends/requests/${requestId}/accept`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Accept friend request failed');
  }

  return await response.json();
}

/**
 * Reject a friend request
 */
export async function rejectFriendRequest(requestId: number): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/api/friends/requests/${requestId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Reject friend request failed');
  }

  return await response.json();
}

/**
 * Get all accepted friends
 */
export async function getFriends(): Promise<Friend[]> {
  const response = await fetch(`${API_BASE}/api/friends`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get friends failed');
  }

  const data = await response.json();
  return data.friends;
}

/**
 * Remove a friend
 */
export async function removeFriend(friendId: number): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/api/friends/${friendId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Remove friend failed');
  }

  return await response.json();
}

/**
 * Get friend's timeline (pictures)
 */
export async function getFriendTimeline(friendId: number, limit: number = 30): Promise<DailyPicture[]> {
  const response = await fetch(`${API_BASE}/api/friends/${friendId}/timeline?limit=${limit}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get friend timeline failed');
  }

  const data = await response.json() as { pictures?: DailyPicture[] };
  return data.pictures ?? [];
}

/**
 * Get friend's full-resolution picture for a specific date
 */
export async function getFriendPictureFull(friendId: number, date: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/friends/${friendId}/pictures/${date}/full`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get friend picture failed');
  }

  const data = await response.json();
  return data.image_base64;
}

// Original Reflections entry points remain available to all existing consumers.
export {getReflectionsSectionConfig,saveReflectionsSectionConfig,resetReflectionsSectionConfig,getReflectionAnalysisContent,ensureReflectionTaskReport,createReflectionTask,startReflectionTask,getReflectionTask,getReflectionTaskResults,getLatestReflections,runReflectionsTask,resumeReflectionsTask,analyzeEchoes,analyzeTraits,analyzePatterns,fetchSessionsAggregate,saveAnalysisReport,getAnalysisReports,getAnalysisHistory} from './reflectionsApi';
export type {ReflectionSectionConfig,ReflectionResult,ReflectionSectionKey,ReflectionTask,ReflectionTaskEvent,ReflectionAnalysisContentOptions,ReflectionAnalysisContentSummary,ReflectionAnalysisContentCandidates,RunReflectionsTaskOptions,ResumeReflectionsTaskOptions,SavedAnalysisReport,AnalysisHistoryCursor,AnalysisHistoryReport,AnalysisHistoryPage} from './reflectionsApi';
