/**
 * API client for voice analysis backend - FastAPI sync API version
 * [Sync] 2026-06-01: normalize user_sessions.labels in session API responses for frontend display.
 * [Sync] 2026-06-05: analyzeEchoes/analyzeTraits/analyzePatterns migrated from polycli trigger-sync
 *         to claude-agent SSE stream. Added callAgentAndCollectText + extractJSONArray helpers.
 */

import { STORAGE_KEYS } from '../constants/storageKeys';
import { LANGUAGE_STORAGE_KEY } from '../i18n';

// ========== Inline Types (workaround for Vite bug) ==========
export interface VoiceConfig {
  name: string;
  systemPrompt: string;
  enabled: boolean;
  icon: string;
  color: string;
  thread_id?: string;
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
  editor_state?: any;
  created_at: string;
  updated_at: string;
  date_key?: string | null;
  first_line?: string;
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
  published?: boolean;
  author_name?: string;
  install_count?: number;
}

// nginx proxies /ink-and-memory/api/* to backend (8765)
const API_BASE = '/ink-and-memory';

function getUILanguage(): 'en' | 'zh' {
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return stored === 'zh' ? 'zh' : 'en';
}

export function normalizeSessionLabels(labels: unknown): SessionLabels {
  if (!Array.isArray(labels)) return [];

  return labels
    .map(label => String(label).trim())
    .filter(label => label.length > 0);
}

function normalizeUserSession(session: any): UserSession {
  return {
    ...session,
    labels: normalizeSessionLabels(session?.labels)
  };
}

/**
 * Get auth headers for authenticated requests
 */
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  if (!token) {
    throw new Error('Not authenticated');
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}

/**
 * Get default voices from backend
 */
export async function getDefaultVoices(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/default-voices`);
  return await response.json();
}

interface SyncResponse {
  success: boolean;
  result?: {
    voices?: Array<{
      phrase: string;
      voice_id: string;  // NEW: Voice ID for lookup
      voice: string;     // Display name
      comment: string;
      icon: string;
      color: string;
    }>;
    new_voices_added?: number;
    status?: string;
    response?: string;  // For chat responses
    voice_name?: string;  // For chat responses
    echoes?: any[];  // For echoes analysis
    traits?: any[];  // For traits analysis
    patterns?: any[];  // For patterns analysis
    image_base64?: string;  // For image generation
    thumbnail_base64?: string;  // Thumbnail for image generation
    prompt?: string;  // Image generation prompt
  };
  error?: string;
  exec_id?: string;  // Still included for debugging
}

/**
 * Analyze text and return voices with metadata (PolyCLI direct call)
 * Backend loads voice configs from database using user_id from JWT token
 */
export async function analyzeText(
  text: string,
  sessionId: string,
  appliedComments?: any[],
  metaPrompt?: string,
  statePrompt?: string,
  overlappedPhrases?: string[],
  notFoundPhrases?: string[]
) {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);

  const response = await fetch(`${API_BASE}/polycli/api/trigger-sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      session_id: 'analyze_text',  // Maps to function name in backend (NOT the display name)
      params: {
        text,
        editor_session_id: sessionId,  // Renamed to avoid conflict with PolyCLI routing session_id
        applied_comments: appliedComments || [],
        meta_prompt: metaPrompt || '',
        state_prompt: statePrompt || '',
        overlapped_phrases: overlappedPhrases || [],
        not_found_phrases: notFoundPhrases || []
      },
      timeout: 90
    })
  });

  const data: SyncResponse = await response.json();

  if (!data.success) {
    console.error('❌ Analysis failed:', data);
    throw new Error(data.error || 'Analysis failed');
  }

  // Return both voices and new_voices_added for energy refund mechanism
  return {
    voices: data.result?.voices || [],
    new_voices_added: data.result?.new_voices_added ?? 0
  };
}

/**
 * Chat with a voice via Claude-agent SSE streaming.
 * Calls POST /api/claude-agent with the voice's thread_id and system prompt.
 * Fires onDelta for each text-delta chunk, onComplete with full text, onError on failure.
 */
export async function chatWithVoiceSSE({
  threadId,
  message,
  systemPrompt,
  editorState,
  onDelta,
  onReasoningDelta,
  onReasoningEnd,
  onComplete,
  onError,
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
}): Promise<void> {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/claude-agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        id: threadId,
        resume: true,
        message: {
          id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`,
          role: 'user',
          parts: [{ type: 'text', text: message }],
        },
        chatModel: { provider: 'anthropic', model: 'claude-sonnet-4-20250514' },
        toolChoice: 'auto',
        allowedAppDefaultToolkit: [],
        allowedMcpServers: {},
        attachments: [],
        systemPrompt,
        ...(editorState != null ? { editor_state: editorState } : {}),
      }),
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
  const decoder = new TextDecoder();
  let buffer = '';
  let accumulated = '';
  let accumulatedReasoning = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\n\n+/);
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        for (const line of frame.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          const json = line.slice('data: '.length).trim();
          if (!json) continue;
          let evt: { type: string; delta?: string; errorText?: string };
          try {
            evt = JSON.parse(json);
          } catch {
            continue;
          }
          if (evt.type === 'text-delta' && typeof evt.delta === 'string') {
            accumulated += evt.delta;
            onDelta(evt.delta);
          } else if (evt.type === 'reasoning-delta' && typeof evt.delta === 'string') {
            accumulatedReasoning += evt.delta;
            onReasoningDelta?.(evt.delta);
          } else if (evt.type === 'reasoning-end') {
            onReasoningEnd?.();
          } else if (evt.type === 'error') {
            onError(new Error(evt.errorText ?? 'Claude-agent error'));
            return;
          } else if (evt.type === 'finish') {
            onComplete(accumulated, accumulatedReasoning || undefined);
            return;
          }
        }
      }
    }
    onComplete(accumulated, accumulatedReasoning || undefined);
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

/**
 * Chat with a voice persona (PolyCLI direct call)
 * Backend loads voice config from database using voice_id and user_id from JWT
 */
export async function chatWithVoice(
  voiceId: string,  // Voice ID for database lookup (e.g., "holder", "mirror")
  conversationHistory: Array<{ role: string; content: string }>,
  userMessage: string,
  originalText?: string,
  metaPrompt?: string,
  statePrompt?: string
): Promise<string> {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);

  const response = await fetch(`${API_BASE}/polycli/api/trigger-sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      session_id: 'chat_with_voice',
      params: {
        voice_id: voiceId,
        conversation_history: conversationHistory,
        user_message: userMessage,
        original_text: originalText || '',
        meta_prompt: metaPrompt || '',
        state_prompt: statePrompt || ''
      },
      timeout: 60
    })
  });

  const data: SyncResponse = await response.json();

  if (!data.success) {
    throw new Error(data.error || 'Chat failed');
  }

  return data.result?.response || 'Sorry, I could not respond.';
}

// ─────────────────────────────────────────────────────────────
// Claude-Agent helpers for one-shot analysis calls
// ─────────────────────────────────────────────────────────────

/**
 * Fetch all sessions and format them as a compact text block
 * to embed directly in analysis prompts, so the agent
 * does not need tool calls to access session data.
 */
async function buildSessionsContext(): Promise<string> {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';
    const sessions = await listSessions(tz);
    if (sessions.length === 0) return '(no writing sessions found)';

    return sessions
      .slice(0, 80)
      .map(s => {
        const date = new Date(s.created_at).toLocaleDateString();
        const title = (s.name || s.first_line || '').slice(0, 120);
        const labels = s.labels.length > 0 ? `  labels: [${s.labels.join(', ')}]` : '';
        return `${date}  ${title}${labels}`;
      })
      .join('\n');
  } catch {
    return '(could not fetch sessions)';
  }
}

/**
 * Create a disposable claude-agent thread, send one message with session context
 * already embedded in the prompt, collect the full assistant text via SSE.
 *
 * Uses tool_choice="none" + max_turns=1 because data is provided inline —
 * no tool round-trips needed, making responses fast and predictable.
 */
async function callAgentAndCollectText(prompt: string): Promise<string> {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  if (!token) throw new Error('Not authenticated');

  // 1. Create a fresh thread
  const threadRes = await fetch(`${API_BASE}/api/claude-agent/threads`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!threadRes.ok) {
    throw new Error(`Failed to create agent thread: ${threadRes.status}`);
  }
  const { thread_id } = await threadRes.json() as { thread_id: string };

  // 2. Stream the agent response
  //    message MUST be a UIMessage dict with parts[] — plain string leaves
  //    message_parts=null in the router which causes extract_text_from_parts()
  //    to return "" and the agent receives an empty user turn.
  //    system_prompt (request field) becomes <voice_context> in the user message,
  //    NOT a replacement for the server-built writing-assistant system prompt.
  const agentRes = await fetch(`${API_BASE}/api/claude-agent`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({
      id: thread_id,
      message: {
        id: `analysis-${Date.now()}`,
        role: 'user',
        parts: [{ type: 'text', text: prompt }],
      },
      system_prompt: 'You are a data analyst. When asked to analyze journal entries, respond ONLY with the requested JSON array. No preamble, no explanation, no markdown — raw JSON only.',
      tool_choice: 'none',
      max_turns: 1,
    }),
  });
  if (!agentRes.ok) {
    const errBody = await agentRes.text().catch(() => '');
    throw new Error(`Agent request failed (${agentRes.status}): ${errBody}`);
  }

  // 3. Read SSE stream — collect text-delta events
  //    IMPORTANT: parse JSON first, then check type — never throw inside
  //    the same try-catch used to parse JSON, or the error gets swallowed.
  const reader = agentRes.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';
  let agentErrorText = '';

  outer: while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';

    for (const frame of frames) {
      for (const line of frame.split('\n')) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice('data: '.length).trim();
        if (!raw) continue;

        // Step A: parse JSON (may fail for malformed lines)
        let event: Record<string, unknown>;
        try {
          event = JSON.parse(raw) as Record<string, unknown>;
        } catch {
          continue; // skip malformed SSE line
        }

        // Step B: handle event type — outside the JSON try-catch
        if (event.type === 'text-delta' && typeof event.delta === 'string') {
          fullText += event.delta;
        } else if (event.type === 'message-final' && typeof event.text === 'string') {
          fullText = event.text; // authoritative complete text
        } else if (event.type === 'error') {
          agentErrorText = String(event.errorText ?? 'Agent stream error');
          break outer;
        }
      }
    }
  }

  if (agentErrorText) throw new Error(agentErrorText);
  return fullText;
}

/**
 * Extract the first JSON array from agent response text.
 * The agent may wrap JSON in ```json ... ``` code fences.
 */
function extractJSONArray(text: string): any[] {
  // Try markdown code fence first
  const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidate = fenceMatch ? fenceMatch[1].trim() : text.trim();

  // Try parsing directly if it starts with [
  if (candidate.startsWith('[')) {
    try { return JSON.parse(candidate); } catch { /* fall through */ }
  }

  // Find the outermost [...] span in the text
  const start = text.indexOf('[');
  const end = text.lastIndexOf(']');
  if (start !== -1 && end > start) {
    try { return JSON.parse(text.slice(start, end + 1)); } catch { /* fall through */ }
  }

  return [];
}

// ─────────────────────────────────────────────────────────────
// Analysis prompts (language-aware, session-context-embedded)
// ─────────────────────────────────────────────────────────────

function echoesPrompt(lang: 'zh' | 'en', ctx: string): string {
  if (lang === 'zh') return `以下是我的写作/日记记录列表：

${ctx}

请根据以上内容，找出反复出现的情感主题或思想回响（echoes）。

严格只输出一个 JSON 数组，不要任何额外说明、标题或 markdown 格式。
[
  {"title": "主题名称", "description": "对该主题的2-3句描述", "examples": ["具体例子1", "例子2"]},
  ...
]
要求：找3-6个最重要的主题，examples 每项最多3条。直接输出 JSON，不要任何其他文字。`;
  return `Here is my writing/journal history:

${ctx}

Based on the above, identify recurring emotional themes or thought patterns (echoes).

Output ONLY a raw JSON array. No explanation, no markdown, no code fences.
[
  {"title": "Theme name", "description": "2-3 sentence description", "examples": ["specific example 1", "example 2"]},
  ...
]
Requirements: 3-6 most significant themes, max 3 examples each. Output JSON only.`;
}

function traitsPrompt(lang: 'zh' | 'en', ctx: string): string {
  if (lang === 'zh') return `以下是我的写作/日记记录列表：

${ctx}

请根据以上内容，识别我的性格特质。

严格只输出一个 JSON 数组，不要任何额外说明。
[
  {"trait": "特质名称", "strength": 4, "evidence": "从记录中找到的具体证据（1-2句）"},
  ...
]
要求：找3-6个最突出的特质，strength 是1-5的整数（5最强）。直接输出 JSON，不要任何其他文字。`;
  return `Here is my writing/journal history:

${ctx}

Based on the above, identify personality traits revealed by my writing.

Output ONLY a raw JSON array. No explanation, no markdown, no code fences.
[
  {"trait": "Trait name", "strength": 4, "evidence": "specific evidence from the notes (1-2 sentences)"},
  ...
]
Requirements: 3-6 most prominent traits, strength integer 1-5. Output JSON only.`;
}

function patternsPrompt(lang: 'zh' | 'en', ctx: string): string {
  if (lang === 'zh') return `以下是我的写作/日记记录列表：

${ctx}

请根据以上内容，识别我在写作、思考或行为上的规律性模式。

严格只输出一个 JSON 数组，不要任何额外说明。
[
  {"pattern": "模式名称", "description": "对该模式的描述（1-2句）", "frequency": "出现频率（如：经常、偶尔、每周等）"},
  ...
]
要求：找3-5个最明显的模式。直接输出 JSON，不要任何其他文字。`;
  return `Here is my writing/journal history:

${ctx}

Based on the above, identify recurring behavioral, writing, or thinking patterns.

Output ONLY a raw JSON array. No explanation, no markdown, no code fences.
[
  {"pattern": "Pattern name", "description": "1-2 sentence description", "frequency": "how often (e.g. often, weekly, occasionally)"},
  ...
]
Requirements: 3-5 most notable patterns. Output JSON only.`;
}

// ─────────────────────────────────────────────────────────────
// Public analysis functions — claude-agent with inline session context
// ─────────────────────────────────────────────────────────────

/**
 * Analyze echoes (recurring themes) from all notes via claude-agent
 */
export async function analyzeEchoes(): Promise<any[]> {
  const lang = getUILanguage();
  const ctx = await buildSessionsContext();
  const text = await callAgentAndCollectText(echoesPrompt(lang, ctx));
  return extractJSONArray(text);
}

/**
 * Analyze traits (personality characteristics) from all notes via claude-agent
 */
export async function analyzeTraits(): Promise<any[]> {
  const lang = getUILanguage();
  const ctx = await buildSessionsContext();
  const text = await callAgentAndCollectText(traitsPrompt(lang, ctx));
  return extractJSONArray(text);
}

/**
 * Analyze patterns (behavioral patterns) from all notes via claude-agent
 */
export async function analyzePatterns(): Promise<any[]> {
  const lang = getUILanguage();
  const ctx = await buildSessionsContext();
  const text = await callAgentAndCollectText(patternsPrompt(lang, ctx));
  return extractJSONArray(text);
}

/**
 * Generate a daily picture based on user's notes (PolyCLI direct call)
 */
export async function generateDailyPicture(targetDate?: string, timezone?: string): Promise<{ image_base64: string; thumbnail_base64?: string; prompt: string; date?: string }> {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  const params: Record<string, any> = {};
  if (targetDate) params.target_date = targetDate;
  if (timezone) params.timezone = timezone;

  const response = await fetch(`${API_BASE}/polycli/api/trigger-sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      session_id: 'generate_daily_picture',
      params,
      timeout: 60
    })
  });

  const data: SyncResponse = await response.json();

  if (!data.success) {
    throw new Error(data.error || 'Image generation failed');
  }

  const res: any = data.result || {};
  if (res.image_base64) {
    return {
      image_base64: res.image_base64,
      thumbnail_base64: res.thumbnail_base64,
      prompt: res.prompt || 'Generated from your notes',
      date: res.date
    };
  }

  throw new Error(res.error || res.reason || 'Image generation failed - no image in response');
}

// ========== Authenticated Endpoints (require login) ==========

/**
 * Import localStorage data to database (one-time migration)
 */
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
}): Promise<{ success: boolean; imported: any }> {
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
export async function saveSession(sessionId: string, editorState: any, name?: string): Promise<void> {
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
export async function listSessions(timezone?: string, options: SessionRangeOptions = {}): Promise<UserSession[]> {
  const params = new URLSearchParams();
  if (timezone) params.append('timezone', timezone);
  if (options.startDate) params.append('start_date', options.startDate);
  if (options.endDate) params.append('end_date', options.endDate);
  const endpoint = options.startDate || options.endDate ? '/api/sessions/range' : '/api/sessions';
  const query = params.toString();

  const response = await fetch(`${API_BASE}${endpoint}${query ? `?${query}` : ''}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'List sessions failed');
  }

  const data = await response.json();
  return (data.sessions || []).map(normalizeUserSession);
}

export async function fetchSessionsAggregate(timezone: string): Promise<{
  stats: { total_days: number; total_entries: number; total_words: number };
  sessions: Array<{ id: string; name?: string; created_at?: string; updated_at?: string; has_text: boolean; word_count: number }>;
  timezone: string;
}> {
  const response = await fetch(`${API_BASE}/api/sessions/aggregate?timezone=${encodeURIComponent(timezone)}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Aggregate sessions failed');
  }

  return await response.json();
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
export async function getSessionsBatch(sessionIds: string[]): Promise<UserSession[]> {
  if (!sessionIds || sessionIds.length === 0) return [];

  const response = await fetch(`${API_BASE}/api/sessions/batch`, {
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
 * Save daily picture
 */
export async function saveDailyPicture(date: string, imageBase64: string, prompt: string, thumbnailBase64?: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/pictures`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      date,
      image_base64: imageBase64,
      thumbnail_base64: thumbnailBase64,
      prompt
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Save picture failed');
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

export async function getDailyPictures(limit: number = 30, options: PictureRangeOptions = {}): Promise<any[]> {
  const params = new URLSearchParams();
  params.append('limit', String(options.limit ?? limit));
  if (options.startDate) params.append('start_date', options.startDate);
  if (options.endDate) params.append('end_date', options.endDate);
  const endpoint = options.startDate || options.endDate ? '/api/pictures/range' : '/api/pictures';
  const query = params.toString();

  const response = await fetch(`${API_BASE}${endpoint}${query ? `?${query}` : ''}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get pictures failed');
  }

  const data = await response.json();
  return data.pictures;
}

/**
 * Get full resolution image for a specific date (on-demand loading)
 */
export async function getDailyPictureFull(date: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/pictures/${date}/full`, {
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
export async function savePreferences(preferences: {
  voice_configs?: any;
  meta_prompt?: string;
  state_config?: any;
  selected_state?: string;
  timezone?: string;
}): Promise<void> {
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
export async function getPreferences(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/preferences`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get preferences failed');
  }

  return await response.json();
}

/**
 * Get writing inspiration from a voice persona
 */
export interface VoiceInspiration {
  inspiration: string;
  voice: string;
  voice_key: string;
  icon: string;
  color: string;
}

export async function getSuggestion(text: string, metaPrompt?: string, statePrompt?: string): Promise<VoiceInspiration | null> {
  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);

  const response = await fetch(`${API_BASE}/polycli/api/trigger-sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      session_id: 'get_writing_suggestion',
      params: {
        text,
        meta_prompt: metaPrompt || '',
        state_prompt: statePrompt || ''
      },
      timeout: 60
    })
  });

  if (!response.ok) {
    console.error('Suggestion request failed');
    return null;
  }

  const data = await response.json();

  // PolyCLI returns {success: true, result: {...}}
  if (data.success && data.result?.inspiration) {
    return {
      inspiration: data.result.inspiration,
      voice: data.result.voice,
      voice_key: data.result.voice_key,
      icon: data.result.icon,
      color: data.result.color
    };
  }

  return null;
}

/**
 * Save analysis report
 */
export async function saveAnalysisReport(reportType: string, reportData: any, allNotesText?: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/reports`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      report_type: reportType,
      report_data: reportData,
      all_notes_text: allNotesText
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Save report failed');
  }
}

/**
 * Get analysis reports
 */
export async function getAnalysisReports(limit: number = 10): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/reports?limit=${limit}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get reports failed');
  }

  const data = await response.json();
  return data.reports;
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
export async function listDecks(published?: boolean): Promise<Deck[]> {
  const url = published
    ? `${API_BASE}/api/decks?published=true`
    : `${API_BASE}/api/decks`;

  const response = await fetch(url, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'List decks failed');
  }

  const data = await response.json();
  return data.decks;
}

/**
 * Get a specific deck with all its voices
 */
export async function getDeck(deckId: string): Promise<Deck> {
  const response = await fetch(`${API_BASE}/api/decks/${deckId}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get deck failed');
  }

  return await response.json();
}

/**
 * Create a new deck
 */
export async function createDeck(data: {
  name: string;
  name_zh?: string;
  name_en?: string;
  description?: string;
  description_zh?: string;
  description_en?: string;
  icon?: string;
  color?: string;
}): Promise<{ deck_id: string }> {
  const response = await fetch(`${API_BASE}/api/decks`, {
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
}): Promise<void> {
  const response = await fetch(`${API_BASE}/api/decks/${deckId}`, {
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
export async function deleteDeck(deckId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/decks/${deckId}`, {
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
export async function forkDeck(deckId: string): Promise<{ deck_id: string }> {
  const response = await fetch(`${API_BASE}/api/decks/${deckId}/fork`, {
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
export async function syncDeck(deckId: string): Promise<{ success: boolean; synced_voices: number }> {
  const response = await fetch(`${API_BASE}/api/decks/${deckId}/sync`, {
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
 * Publish/unpublish a deck to community store
 * @@@ Warning: Publishing breaks parent_id chain (deck becomes standalone)
 */
export async function publishDeck(deckId: string): Promise<{ success: boolean; published: boolean }> {
  const response = await fetch(`${API_BASE}/api/decks/${deckId}/publish`, {
    method: 'POST',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Publish deck failed');
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
}): Promise<{ voice_id: string }> {
  const response = await fetch(`${API_BASE}/api/voices`, {
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
}): Promise<void> {
  const response = await fetch(`${API_BASE}/api/voices/${voiceId}`, {
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
 * Create a Claude-agent thread and associate it with a voice (lazy).
 * If the voice already has a thread_id, returns it unchanged.
 * Otherwise creates a new thread, persists it on the voice, and returns the id.
 */
export async function ensureVoiceThread(voiceId: string, existingThreadId?: string): Promise<string> {
  if (existingThreadId) return existingThreadId;

  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  if (!token) throw new Error('Not authenticated');

  // Create a new Claude-agent thread
  const res = await fetch(`${API_BASE}/api/claude-agent/threads`, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + token }
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

/**
 * Delete a voice (only voices in user-owned decks)
 */
export async function deleteVoice(voiceId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/voices/${voiceId}`, {
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
export async function forkVoice(voiceId: string, targetDeckId: string): Promise<{ voice_id: string }> {
  const response = await fetch(`${API_BASE}/api/voices/${voiceId}/fork`, {
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

// ========== Voice Config Loading ==========

/**
 * @@@ Load all enabled voices from all enabled decks and convert to VoiceConfig format
 * This bridges the new deck system with the existing voice analysis system
 */
export async function loadVoicesFromDecks(): Promise<Record<string, VoiceConfig>> {
  try {
    const decks = await listDecks();
    const voiceConfigs: Record<string, VoiceConfig> = {};

    // Load voices from each enabled deck
    for (const deck of decks) {
      if (!deck.enabled) continue;

      try {
        const fullDeck = await getDeck(deck.id);

        if (fullDeck.voices) {
          for (const voice of fullDeck.voices) {
            if (!voice.enabled) continue;

            // @@@ Convert Voice to VoiceConfig format
            // Key by voice.id (UUID) so backend can find it in database
            voiceConfigs[voice.id] = {
              name: voice.name,
              systemPrompt: voice.system_prompt,
              enabled: voice.enabled,
              icon: voice.icon,
              color: voice.color,
              thread_id: voice.thread_id
            };
          }
        }
      } catch (err) {
        console.error(`Failed to load voices from deck ${deck.id}:`, err);
        // Continue loading other decks even if one fails
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
export async function getFriendTimeline(friendId: number, limit: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/friends/${friendId}/timeline?limit=${limit}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get friend timeline failed');
  }

  const data = await response.json();
  return data.pictures;
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
