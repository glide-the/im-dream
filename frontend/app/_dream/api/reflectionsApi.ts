// [Input] Original Reflections task/config/history DTOs, Cookie/CSRF and explicit platform HTTP/storage/UUID differences.
// [Output] One shared Reflections API including original idempotent creation, SSE-first start, recovery and strict report history.
// [Pos] Domain extraction from voiceApi; voiceApi preserves its existing public exports.
// [Sync] 2026-10-29: preserve Web payloads/parser/policy; native can supply local HTTP streams, original storage keys and Foundation UUID.
import {z} from 'zod';
import {getBrowserCsrfToken,browserRequestHeaders} from '../lib/browserSession';
import {API_BASE} from '../lib/apiBase';
import {STORAGE_KEYS} from '../constants/storageKeys';
export type ReflectionsStorage=Pick<Storage,'getItem'|'setItem'|'removeItem'>;
export interface ReflectionsPlatform {
  transport?:typeof globalThis.fetch;
  storage?:ReflectionsStorage;
  newRequestId?:()=>string|Promise<string>;
  language?:()=>string;
  signal?:AbortSignal;
  openEvents?:(path:string,init:RequestInit)=>Promise<{status:number;chunks:AsyncIterable<string>;cancel:()=>void}>;
}
export interface ReflectionSectionConfig {
  section: string;
  display_name: string;
  display_name_zh: string;
  usedCustomConfig: boolean;
  prompt_files: Record<string, string>;
}

export interface ReflectionResult {
  id?: string;
  task_id?: string;
  section?: 'echoes' | 'traits' | 'patterns';
  title: string;
  description: string;
  related_session_ids: string[];
  evidence: string;
  confidence: 'high' | 'medium' | 'low';
}

export type ReflectionSectionKey = 'echoes' | 'traits' | 'patterns';

export interface ReflectionTask {
  id: string;
  task_id: string;
  status: 'CREATED' | 'ASSEMBLING' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'PARTIAL_FAILED' | 'FAILED';
  sections: ReflectionSectionKey[];
  failed_sections?: ReflectionSectionKey[];
  input_snapshot: Record<string, unknown>;
  analysis_content?: ReflectionAnalysisContentSummary | null;
  workspace_path?: string | null;
  agent_contract_version?: string | null;
  error_summary?: string | null;
  created_at?: string;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at?: string;
  results?: ReflectionResult[];
}

export interface ReflectionTaskEvent {
  id: string;
  task_id: string;
  type: string;
  sequence: number;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface ReflectionAnalysisContentOptions {
  include_notion: boolean;
  connector_id?: string;
  deck_id?: string;
  agent_id?: string;
  snapshot_version?: string;
}

export interface ReflectionAnalysisContentSummary {
  diary_session_ids: string[] | null;
  notion: { connector_id: string; snapshot_version: string;
    pages: { page_id: string; title: string; url: string | null; content_sha256: string; read_at: string }[];
    empty_page_count: number;
  } | null;
  agent: { deck_id: string; agent_id: string; deck_name: string; agent_name: string } | null;
}

export interface ReflectionAnalysisContentCandidates {
  status: 'ready' | 'empty' | 'no_snapshot' | 'disconnected' | 'auth_required' | 'scope_changed';
  page_count: number;
  snapshot_version: string | null;
  connector_id?: string;
  selection_available: boolean;
}

export interface RunReflectionsTaskOptions {
  sections?: ReflectionSectionKey[];
  sessionIds?: string[];
  analysisContent?: ReflectionAnalysisContentOptions;
  language?: string;
  onEvent?: (event: ReflectionTaskEvent) => void;
}

export interface ResumeReflectionsTaskOptions {
  lastEventId?: string;
  startPrepared?: boolean;
  onEvent?: (event: ReflectionTaskEvent) => void;
}

export interface SavedAnalysisReport {
  id: number;
  report_data?: {
    echoes?: ReflectionResult[];
    traits?: ReflectionResult[];
    patterns?: ReflectionResult[];
    stats?: { days: number; entries: number; words: number };
    task_id?: string;
    failed_sections?: ReflectionSectionKey[];
    analysis_content?: ReflectionAnalysisContentSummary;
  };
  created_at: string;
}

export type AnalysisHistoryCursor = { created_at: string; id: string };

export type AnalysisHistoryReport = Omit<SavedAnalysisReport, 'id' | 'created_at'> & {
  id: string; created_at: string | null; analysis_created_at: string; task_id: string | null;
};

export type AnalysisHistoryPage = { reports: AnalysisHistoryReport[]; next_cursor: AnalysisHistoryCursor | null };

export function createReflectionsApi(platform:ReflectionsPlatform={}) {
  const fetch:typeof globalThis.fetch=(input,init)=>(platform.transport??globalThis.fetch)(input,{...init,signal:init?.signal??platform.signal});
  const localStorage:ReflectionsStorage={
    getItem:key=>(platform.storage??globalThis.localStorage).getItem(key),
    setItem:(key,value)=>(platform.storage??globalThis.localStorage).setItem(key,value),
    removeItem:key=>(platform.storage??globalThis.localStorage).removeItem(key),
  };
  const requestId=()=>platform.newRequestId?.()??globalThis.crypto.randomUUID();
  const getAuthHeaders=()=>authHeaders({'Content-Type':'application/json'});
  function isRecord(value:unknown):value is Record<string,unknown>{return typeof value==='object'&&value!==null;}
async function getReflectionsSectionConfig(
  section: 'echoes' | 'traits' | 'patterns'
): Promise<ReflectionSectionConfig> {
  const csrfToken = getBrowserCsrfToken();
  if (!csrfToken) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE}/api/reflections/config/${section}`, {
    headers: { ...browserRequestHeaders({}, csrfToken) },
  });
  if (!res.ok) throw new Error(`Failed to fetch section config (${res.status})`);
  return await res.json() as ReflectionSectionConfig;
}

async function saveReflectionsSectionConfig(
  section: 'echoes' | 'traits' | 'patterns',
  promptFiles: Record<string, string>
): Promise<{ saved: boolean; updatedFiles: string[] }> {
  const csrfToken = getBrowserCsrfToken();
  if (!csrfToken) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE}/api/reflections/config/${section}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...browserRequestHeaders({}, csrfToken) },
    body: JSON.stringify({ prompt_files: promptFiles }),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => '');
    throw new Error(`Failed to save section config (${res.status}): ${err}`);
  }
  return await res.json();
}

async function resetReflectionsSectionConfig(
  section: 'echoes' | 'traits' | 'patterns'
): Promise<void> {
  const csrfToken = getBrowserCsrfToken();
  if (!csrfToken) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE}/api/reflections/config/${section}`, {
    method: 'DELETE',
    headers: { ...browserRequestHeaders({}, csrfToken) },
  });
  if (!res.ok) throw new Error(`Failed to reset section config (${res.status})`);
}

const reflectionAnalysisSummarySchema = z.object({
  diary_session_ids: z.array(z.string()).nullable(),
  agent: z.object({ deck_id: z.string(), agent_id: z.string(), deck_name: z.string(), agent_name: z.string() }).nullable(),
  notion: z.object({ connector_id: z.string(), snapshot_version: z.string(), empty_page_count: z.number().int().nonnegative(),
    pages: z.array(z.object({ page_id: z.string(), title: z.string(), url: z.string().url().startsWith('https://').nullable(),
      content_sha256: z.string().regex(/^[0-9a-f]{64}$/), read_at: z.string() })),
  }).nullable(),
});

function normalizeReflectionAnalysisSummary(value: unknown): ReflectionAnalysisContentSummary | null {
  if (value === undefined || value === null) return null;
  const parsed = reflectionAnalysisSummarySchema.safeParse(value);
  if (!parsed.success) throw new Error('Invalid analysis source response');
  return parsed.data;
}

const reflectionAnalysisCandidatesSchema = z.object({
  status: z.enum(['ready', 'empty', 'no_snapshot', 'disconnected', 'auth_required', 'scope_changed']),
  page_count: z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER), snapshot_version: z.string().nullable(),
  connector_id: z.string().optional(), selection_available: z.boolean(),
}).refine(value => value.status !== 'ready' || value.page_count > 0 && value.snapshot_version !== null);

async function getReflectionAnalysisContent(): Promise<ReflectionAnalysisContentCandidates> {
  const response = await fetch(`${API_BASE}/api/reflections/analysis-content`, { headers: getAuthHeaders() });
  if (!response.ok) throw new Error(`Analysis content could not be loaded (${response.status})`);
    const parsed = reflectionAnalysisCandidatesSchema.safeParse(await response.json());
  if (!parsed.success) throw new Error('Invalid analysis content response');
  return parsed.data;
}

async function ensureReflectionTaskReport(taskId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/reflections/tasks/${taskId}/report`, { method: 'POST', headers: authHeaders() });
  if (!response.ok) throw new Error(currentFrontendLanguage().startsWith('zh')
    ? '分析结果已保留，报告暂未保存。请重试保存。' : 'The analysis result is retained, but its report could not be saved. Retry saving.');
}

function currentFrontendLanguage(): string {
  return platform.language?.() || localStorage.getItem(STORAGE_KEYS.LANGUAGE) || 'en';
}

function authHeaders(extra?: Record<string, string>): HeadersInit {
  const csrfToken = getBrowserCsrfToken();
  if (!csrfToken) throw new Error('Not authenticated');
  return { ...(extra ?? {}), ...browserRequestHeaders({}, csrfToken) };
}

function normalizeReflectionResult(item: unknown): ReflectionResult {
  const record = isRecord(item) ? item : {};
  return {
    id: typeof record.id === 'string' ? record.id : undefined,
    task_id: typeof record.task_id === 'string' ? record.task_id : undefined,
    section: ['echoes', 'traits', 'patterns'].includes(String(record.section))
      ? record.section as ReflectionSectionKey
      : undefined,
    title: String(record.title ?? ''),
    description: String(record.description ?? ''),
    related_session_ids: Array.isArray(record.related_session_ids)
      ? record.related_session_ids.filter((s: unknown): s is string => typeof s === 'string')
      : [],
    evidence: String(record.evidence ?? ''),
    confidence: (['high', 'medium', 'low'].includes(String(record.confidence))
      ? record.confidence
      : 'medium') as 'high' | 'medium' | 'low',
  };
}

function normalizeReflectionTask(raw: unknown): ReflectionTask {
  const record = isRecord(raw) ? raw : {};
  return {
    id: String(record.id ?? record.task_id ?? ''),
    task_id: String(record.task_id ?? record.id ?? ''),
    status: String(record.status ?? 'CREATED') as ReflectionTask['status'],
    sections: Array.isArray(record.sections)
      ? record.sections.filter((s: unknown): s is ReflectionSectionKey =>
          s === 'echoes' || s === 'traits' || s === 'patterns')
      : [],
    failed_sections: Array.isArray(record.section_states) ? record.section_states.filter(isRecord)
      .filter(item => item.status === 'FAILED' && ['echoes', 'traits', 'patterns'].includes(String(item.section)))
      .map(item => item.section as ReflectionSectionKey) : [],
    input_snapshot: isRecord(record.input_snapshot)
      ? record.input_snapshot
      : {},
    analysis_content: normalizeReflectionAnalysisSummary(isRecord(record.input_snapshot) ? record.input_snapshot.analysis_content : null),
    workspace_path: typeof record.workspace_path === 'string' ? record.workspace_path : null,
    agent_contract_version: typeof record.agent_contract_version === 'string' ? record.agent_contract_version : null,
    error_summary: typeof record.error_summary === 'string' ? record.error_summary : null,
    created_at: typeof record.created_at === 'string' ? record.created_at : undefined,
    started_at: typeof record.started_at === 'string' ? record.started_at : null,
    completed_at: typeof record.completed_at === 'string' ? record.completed_at : null,
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : undefined,
    results: Array.isArray(record.results) ? record.results.map(normalizeReflectionResult) : undefined,
  };
}

function reflectionResultsBySection(results: ReflectionResult[]): Record<ReflectionSectionKey, ReflectionResult[]> {
  return {
    echoes: results.filter(r => r.section === 'echoes'),
    traits: results.filter(r => r.section === 'traits'),
    patterns: results.filter(r => r.section === 'patterns'),
  };
}

function reflectionKnownFailure(value: unknown): string | undefined {
  const zh = currentFrontendLanguage().startsWith('zh');
  const code = typeof value === 'string' ? value.match(/^[A-Z][A-Z0-9_]+/)?.[0] : undefined;
  const messages: Record<string, [string, string]> = {
    REFLECTION_AGENT_UNAVAILABLE: ['所选分析 Agent 已不可用，请重新选择。', 'The selected analysis Agent is unavailable. Select it again.'],
    DECK_ACCESS_DENIED: ['无法使用所选 Deck，请重新选择。', 'The selected Deck is unavailable. Select another Deck.'],
    NOTION_AUTH_REQUIRED: ['Notion 授权已失效，请重新连接。', 'Reconnect Notion before analyzing.'],
    NOTION_ANALYSIS_READ_FAILED: ['无法读取完整 Notion 内容，请检查页面权限，或关闭 Notion 后重试。', 'Notion content could not be read. Check page permissions or turn off Notion and retry.'],
    NOTION_RESOURCE_UNAVAILABLE: ['有 Notion 页面已无法访问，请检查授权与挂载范围后重试。', 'A Notion page is unavailable. Check access and linked resources, then retry.'],
    NOTION_MARKDOWN_INCOMPLETE: ['Notion 返回的正文不完整，请稍后重试分析。', 'Notion returned incomplete content. Retry the analysis later.'],
    NOTION_UPSTREAM_UNAVAILABLE: ['Notion 正文服务暂时不可用，请稍后重试分析。', 'Notion content is temporarily unavailable. Retry the analysis later.'],
    NOTION_UPSTREAM_TIMEOUT: ['分析期间读取 Notion 正文超时，请重试分析。', 'Notion content read timed out during analysis. Retry the analysis.'],
    REFLECTION_NOTION_WORKSPACE_REQUIRED: ['请在设置中启用工作区，以使用 Notion 连接器按需读取。', 'Enable Workspace Mode in Settings to read Notion through the connector.'],
    REFLECTION_NOTION_EVIDENCE_UNCONFIRMED: ['Notion 来源证据保存结果尚未确认，请查看原任务后重试。', 'Notion source evidence could not be confirmed. Check the original task before retrying.'],
    NOTION_RATE_LIMITED: ['Notion 请求暂时受限，请稍后重试分析。', 'Notion requests are temporarily limited. Retry the analysis later.'],
    NOTION_PERMISSION_DENIED: ['无法读取选定的 Notion 页面，请检查授权后重试。', 'Check the selected Notion page permissions and retry.'],
    NOTION_CONNECTOR_CHANGED: ['Notion 连接已改变，请重新选择分析内容。', 'The Notion connection changed. Select the analysis content again.'],
    NOTION_SNAPSHOT_CHANGED: ['Notion 资源已更新，请重新选择分析内容。', 'Notion resources changed. Select the analysis content again.'],
    NOTION_ANALYSIS_SCOPE_CHANGED: ['已挂载资源已改变，请重新同步后选择。', 'Linked resources changed. Sync and select them again.'],
    NOTION_SNAPSHOT_UNAVAILABLE: ['尚无可用的 Notion 快照，请先同步资源。', 'Sync Notion resources before analyzing.'],
    REFLECTION_NO_ANALYZABLE_INPUT: ['没有可分析的正文，请选择有内容的日记或 Notion 页面。', 'Select diary entries or Notion pages with text to analyze.'],
    ADMIN_CAPABILITY_UNAVAILABLE: ['分析内容暂时不可用，请稍后重试。', 'Analysis content is temporarily unavailable. Retry later.'],
  };
  return code && messages[code] ? messages[code][zh ? 0 : 1] : undefined;
}

async function reflectionCreateError(response: Response): Promise<string> {
  const zh = currentFrontendLanguage().startsWith('zh');
  const payload = await response.json().catch(() => null);
  const detail = isRecord(payload) ? payload.detail : null;
  const code = typeof detail === 'string' ? detail : isRecord(detail) ? detail.error_code : undefined;
  const known = reflectionKnownFailure(code);
  if (known) return known;
  return response.status === 401 ? (zh ? '请登录后开始分析。' : 'Log in to start an analysis.')
    : (zh ? '分析未能启动，请检查所选内容后重试。' : 'The analysis could not start. Check the selected content and retry.');
}

const pendingReflectionSubmissionSchema = z.strictObject({
  request_key: z.string().uuid(),
  body: z.strictObject({
    sections: z.array(z.enum(['echoes', 'traits', 'patterns'])).optional(),
    auto_start: z.boolean(), language: z.string(), session_ids: z.array(z.string()).optional(),
    analysis_content: z.strictObject({ include_notion: z.boolean(), connector_id: z.string().optional(),
      deck_id: z.string().optional(), agent_id: z.string().optional(), snapshot_version: z.string().optional() }).optional(),
  }),
});

async function createReflectionTask(
  sections?: ReflectionSectionKey[],
  autoStart = true,
  language = currentFrontendLanguage(),
  sessionIds?: string[],
  analysisContent?: ReflectionAnalysisContentOptions,
): Promise<ReflectionTask> {
  const fresh = { sections, auto_start: autoStart, language, session_ids: sessionIds, analysis_content: analysisContent };
  let submission: z.infer<typeof pendingReflectionSubmissionSchema>;
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(STORAGE_KEYS.REFLECTIONS_PENDING_SUBMISSION) || 'null');
    const parsed = pendingReflectionSubmissionSchema.safeParse(stored);
    submission = parsed.success
      ? parsed.data
      : { request_key: await requestId(), body: fresh };
  } catch { submission = { request_key: await requestId(), body: fresh }; }
  localStorage.setItem(STORAGE_KEYS.REFLECTIONS_PENDING_SUBMISSION, JSON.stringify(submission));
  const res = await fetch(`${API_BASE}/api/reflections/tasks`, {
    method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ ...submission.body, request_key: submission.request_key }),
  });
  if (!res.ok) {
    const failure: unknown = await res.clone().json().catch(() => null);
    const detail = isRecord(failure) && isRecord(failure.detail) ? failure.detail : null;
    const outcomeUnknown = detail?.creation_committed === true || detail?.outcome_unknown === true
      || (res.status >= 500 && detail?.outcome_unknown !== false);
    if (!outcomeUnknown) localStorage.removeItem(STORAGE_KEYS.REFLECTIONS_PENDING_SUBMISSION);
    const message = await reflectionCreateError(res);
    throw new Error(outcomeUnknown ? `${message} ${currentFrontendLanguage().startsWith('zh')
      ? '重试会恢复上次提交的分析。' : 'Retry to recover the previous analysis submission.'}` : message);
  }
  const task = normalizeReflectionTask(await res.json());
  if (!task.task_id) throw new Error('Invalid analysis task response');
  localStorage.removeItem(STORAGE_KEYS.REFLECTIONS_PENDING_SUBMISSION);
  return task;
}

async function startReflectionTask(taskId: string): Promise<ReflectionTask> {
  const res = await fetch(`${API_BASE}/api/reflections/tasks/${taskId}/start`, {
    method: 'POST',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Failed to start reflections task (${res.status}): ${text}`);
  }
  return normalizeReflectionTask(await res.json());
}

async function getReflectionTask(taskId: string): Promise<ReflectionTask> {
  const res = await fetch(`${API_BASE}/api/reflections/tasks/${taskId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch reflections task (${res.status})`);
  return normalizeReflectionTask(await res.json());
}

async function getReflectionTaskResults(taskId: string): Promise<ReflectionResult[]> {
  const res = await fetch(`${API_BASE}/api/reflections/tasks/${taskId}/results`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch reflections results (${res.status})`);
  const data = await res.json() as { results?: unknown[] };
  return Array.isArray(data.results) ? data.results.map(normalizeReflectionResult) : [];
}

async function getLatestReflections(): Promise<{ task: ReflectionTask | null; results: ReflectionResult[] }> {
  const res = await fetch(`${API_BASE}/api/reflections/latest`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch latest reflections (${res.status})`);
  const data = await res.json() as { task?: unknown; results?: unknown[] };
  return {
    task: data.task ? normalizeReflectionTask(data.task) : null,
    results: Array.isArray(data.results) ? data.results.map(normalizeReflectionResult) : [],
  };
}

function parseReflectionSseFrame(frame: string): ReflectionTaskEvent | null {
  const dataLine = frame.split('\n').find(line => line.startsWith('data: '));
  if (!dataLine) return null;
  try {
    return JSON.parse(dataLine.slice('data: '.length)) as ReflectionTaskEvent;
  } catch {
    return null;
  }
}

async function streamReflectionTaskEvents(
  taskId: string,
  onEvent?: (event: ReflectionTaskEvent) => void,
  onConnected?: () => Promise<void> | void,
  lastEventId?: string,
): Promise<void> {
  const headers = authHeaders({ Accept: 'text/event-stream' });
  if (lastEventId) {
    (headers as Record<string, string>)['Last-Event-ID'] = lastEventId;
  }
  const path=`${API_BASE}/api/reflections/tasks/${taskId}/events`;
  let chunks:AsyncIterable<string>;
  let close=()=>{};
  if(platform.openEvents){
    const stream=await platform.openEvents(path,{headers,signal:platform.signal});
    if(stream.status<200||stream.status>=300){stream.cancel();return;}
    chunks=stream.chunks;close=stream.cancel;
  }else{
    const res=await fetch(path,{headers});
    if(!res.ok||!res.body)return;
    const reader=res.body.getReader(),decoder=new TextDecoder();
    chunks=(async function*(){while(true){const {done,value}=await reader.read();if(done)break;yield decoder.decode(value,{stream:true});}})();
    close=()=>reader.releaseLock();
  }
  let buffer = '';
  let connected = false;
  try {for await(const value of chunks) {
    buffer += value;
    const frames = buffer.split('\n\n');
    buffer = frames.pop() ?? '';
    for (const frame of frames) {
      const event = parseReflectionSseFrame(frame);
      if (event?.type === 'reflection.stream.connected' && !connected) {
        connected = true;
        await onConnected?.();
      }
      if (event) onEvent?.(event);
    }
  }} finally {close();}
  if (!connected) await onConnected?.();
}

async function waitForReflectionTaskResults(
  taskId: string,
  onEvent?: (event: ReflectionTaskEvent) => void,
  onConnected?: () => Promise<void> | void,
  lastEventId?: string,
): Promise<ReflectionResult[]> {
  const ensureObserving=()=>{if(platform.signal?.aborted)throw Error('REFLECTIONS_OBSERVATION_CLOSED');};
  let connection:Promise<void>|undefined;
  const connectOnce = () => {
    if(!connection)connection=Promise.resolve().then(()=>{ensureObserving();return onConnected?.();});
    return connection;
  };
  const startAfterSseGracePeriod = setTimeout(() => {
    void connectOnce().catch(()=>{/* The same Promise reports this failure to the waiting request. */});
  }, 1200);
  try {await streamReflectionTaskEvents(taskId, onEvent, connectOnce, lastEventId).catch(async err => {
    ensureObserving();
    console.warn('[Reflections] SSE stream failed, falling back to polling:', err);
    await connectOnce();
  });
  await connectOnce();
  } finally {clearTimeout(startAfterSseGracePeriod);}

  for (let i = 0; i < 30; i += 1) {
    ensureObserving();
    const task = await getReflectionTask(taskId);
    if (['COMPLETED', 'PARTIAL_FAILED', 'FAILED'].includes(task.status)) {
      if (task.status === 'FAILED') {
        throw new Error(reflectionKnownFailure(task.error_summary) ?? (task.error_summary || 'Reflections task failed'));
      }
      return task.results ?? await getReflectionTaskResults(taskId);
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  throw new Error('Reflections task did not finish in time');
}

async function runReflectionsTask(
  options: RunReflectionsTaskOptions = {},
): Promise<Record<ReflectionSectionKey, ReflectionResult[]>> {
  const task = await createReflectionTask(options.sections, false, options.language ?? currentFrontendLanguage(), options.sessionIds, options.analysisContent);
  options.onEvent?.({
    id: 'client-task-created',
    task_id: task.task_id,
    type: 'reflection.client.task.created',
    sequence: 0,
    created_at: new Date().toISOString(),
    payload: { sections: task.sections },
  });
  let started = false;
  const startOnce = async () => {
    if (started) return;
    started = true;
    await startReflectionTask(task.task_id);
  };
  const results = await waitForReflectionTaskResults(task.task_id, options.onEvent, startOnce);
  return reflectionResultsBySection(results);
}

async function resumeReflectionsTask(
  taskId: string,
  options: ResumeReflectionsTaskOptions = {},
): Promise<Record<ReflectionSectionKey, ReflectionResult[]>> {
  const task = await getReflectionTask(taskId);
  if (task.status === 'FAILED') {
    throw new Error(task.error_summary || 'Reflections task failed');
  }
  const startPrepared = task.status === 'CREATED' && options.startPrepared
    ? () => startReflectionTask(taskId).then(() => undefined) : undefined;
  const results = ['COMPLETED', 'PARTIAL_FAILED'].includes(task.status)
    ? task.results ?? await getReflectionTaskResults(taskId)
    : await waitForReflectionTaskResults(taskId, options.onEvent, startPrepared, options.lastEventId);
  return reflectionResultsBySection(results);
}

async function analyzeEchoes(onDelta?: (d: string) => void): Promise<ReflectionResult[]> {
  const bySection = await runReflectionsTask({
    sections: ['echoes'],
    onEvent: event => onDelta?.(event.type),
  });
  return bySection.echoes;
}

async function analyzeTraits(onDelta?: (d: string) => void): Promise<ReflectionResult[]> {
  const bySection = await runReflectionsTask({
    sections: ['traits'],
    onEvent: event => onDelta?.(event.type),
  });
  return bySection.traits;
}

async function analyzePatterns(onDelta?: (d: string) => void): Promise<ReflectionResult[]> {
  const bySection = await runReflectionsTask({
    sections: ['patterns'],
    onEvent: event => onDelta?.(event.type),
  });
  return bySection.patterns;
}

async function fetchSessionsAggregate(timezone: string): Promise<{
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

async function saveAnalysisReport(reportType: string, reportData: unknown, allNotesText?: string): Promise<void> {
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

async function getAnalysisReports(limit: number = 10): Promise<SavedAnalysisReport[]> {
  const response = await fetch(`${API_BASE}/api/reports?limit=${limit}`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Get reports failed');
  }

  const data = await response.json() as { reports?: SavedAnalysisReport[] };
  return (data.reports ?? []).map(report => ({ ...report, report_data: report.report_data ? {
    ...report.report_data, analysis_content: normalizeReflectionAnalysisSummary(report.report_data.analysis_content) ?? undefined,
  } : undefined }));
}

const historyIdSchema = z.string().regex(/^[1-9][0-9]{0,18}$/)
  .refine(value => BigInt(value) <= 9223372036854775807n);

const historyTimeSchema = z.iso.datetime({ offset: true });

const historyCursorSchema = z.object({ created_at: historyTimeSchema, id: historyIdSchema }).strict();

const historyResultSchema = z.object({
  title: z.string(), description: z.string(), related_session_ids: z.array(z.string()), evidence: z.string(),
  confidence: z.enum(['high', 'medium', 'low']),
}).passthrough();

const historyPageSchema = z.object({
  reports: z.array(z.object({
    id: historyIdSchema, created_at: z.string().nullable(), analysis_created_at: historyTimeSchema,
    task_id: z.uuid().nullable(),
    report_data: z.object({
      echoes: z.array(historyResultSchema).optional(), traits: z.array(historyResultSchema).optional(),
      patterns: z.array(historyResultSchema).optional(),
      failed_sections: z.array(z.enum(['echoes', 'traits', 'patterns'])).optional(),
      stats: z.object({ days: z.number(), entries: z.number(), words: z.number() }).optional(),
    }).passthrough(),
  }).passthrough()),
  next_cursor: historyCursorSchema.nullable(),
}).strict();

async function getAnalysisHistory(options: { limit?: number; before?: AnalysisHistoryCursor | null; signal?: AbortSignal } = {}): Promise<AnalysisHistoryPage> {
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set('limit', String(options.limit));
  if (options.before) {
    query.set('before_created_at', options.before.created_at);
    query.set('before_id', options.before.id);
  }
  const response = await fetch(`${API_BASE}/api/reports/history?${query}`, { headers: getAuthHeaders(), signal: options.signal });
  if (!response.ok) throw new Error('Analysis history could not be loaded');
  const data = historyPageSchema.parse(await response.json());
  if (options.before && data.next_cursor?.created_at === options.before.created_at && data.next_cursor.id === options.before.id) {
    throw new Error('Analysis history cursor did not advance');
  }
  return {
    reports: data.reports.map(report => ({ ...report, report_data: {
      ...report.report_data,
      analysis_content: normalizeReflectionAnalysisSummary(report.report_data.analysis_content) ?? undefined,
    } } as AnalysisHistoryReport)), next_cursor: data.next_cursor,
  };
}
  return {getReflectionsSectionConfig,saveReflectionsSectionConfig,resetReflectionsSectionConfig,getReflectionAnalysisContent,ensureReflectionTaskReport,createReflectionTask,startReflectionTask,getReflectionTask,getReflectionTaskResults,getLatestReflections,runReflectionsTask,resumeReflectionsTask,analyzeEchoes,analyzeTraits,analyzePatterns,fetchSessionsAggregate,saveAnalysisReport,getAnalysisReports,getAnalysisHistory};
}

export const {getReflectionsSectionConfig,saveReflectionsSectionConfig,resetReflectionsSectionConfig,getReflectionAnalysisContent,ensureReflectionTaskReport,createReflectionTask,startReflectionTask,getReflectionTask,getReflectionTaskResults,getLatestReflections,runReflectionsTask,resumeReflectionsTask,analyzeEchoes,analyzeTraits,analyzePatterns,fetchSessionsAggregate,saveAnalysisReport,getAnalysisReports,getAnalysisHistory}=createReflectionsApi();

export type ReflectionsApi=ReturnType<typeof createReflectionsApi>;
