// [Input] Admin OAuth credentials, origin-persistent refresh state, Bearer profile DTO and normal fetch requests.
// [Output] Memory-only access tokens, reopen recovery, cross-tab serialized rotation and immutable public user state.
// [Pos] Web authentication owner; native platform selection retains cookieSession.ts.
// [Sync] 2026-11-20: persist refresh grants across reopening and serialize refresh/logout with the callback's origin lock.
// [Sync] 2026-11-19: Web login/read/refresh/logout use explicit OAuth credentials with cookies omitted.
import { z } from 'zod';
import { STORAGE_KEYS } from '../constants/storageKeys.ts';
import * as cookieSession from './cookieSession.ts';
export { BrowserSessionError } from './cookieSession.ts';
export type { BrowserSession, BrowserUser } from './cookieSession.ts';
import type { BrowserSession } from './cookieSession.ts';
const { BrowserSessionError } = cookieSession;

const token = z.string().regex(/^[A-Za-z0-9._~-]+$/).max(16_384);
const refreshToken = z.string().min(1).max(16_384);
const storedDto = z.strictObject({ session_id: z.uuid(), refresh_token: refreshToken });
const credentialDto = z.strictObject({ session_id: z.uuid().optional(), access_token: token.optional(), refresh_token: refreshToken.optional(), expires_at: z.number().int().positive().optional() });
const refreshedDto = z.strictObject({ access_token: token, refresh_token: z.string().min(1).max(16_384), expires_at: z.number().int().positive() });
const userDto = z.strictObject({ user: z.strictObject({ id: z.string().regex(/^[1-9]\d{0,18}$/).refine(value => BigInt(value) <= 9_223_372_036_854_775_807n),
  email: z.email(), display_name: z.string().nullable(), avatar_url: z.string().nullable(), role: z.string(), created_at: z.iso.datetime({ offset: true }).nullable() }) });
type Credentials = z.infer<typeof credentialDto>;
let credentials: Credentials | null | undefined;
let currentSession: BrowserSession | null = null;
let generation: object = {};
let readIdentity: object = {};
let refreshFlight: Promise<string | null> | undefined;
let logoutFlight: Promise<void> | undefined;
const nativeHost = () => typeof window !== 'undefined' && (window as Window & { __INK_NATIVE_HOST__?: { framework?: string } }).__INK_NATIVE_HOST__?.framework === 'react-native';

function untilAborted<T>(pending: Promise<T>, signal?: AbortSignal | null): Promise<T> {
  if (!signal) return pending;
  signal.throwIfAborted();
  return new Promise((resolve, reject) => {
    const abort = () => reject(signal.reason);
    signal.addEventListener('abort', abort, { once: true });
    pending.then(resolve, reject).finally(() => signal.removeEventListener('abort', abort));
  });
}

function changed(restore = false) {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('ink:auth-state', { detail: { restore } }));
}

function storedCredentials(): z.infer<typeof storedDto> | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(STORAGE_KEYS.WEB_OAUTH);
  try { return raw ? storedDto.parse(JSON.parse(raw)) : null; } catch { return null; }
}

function saveCredentials(value: Credentials | null) {
  // Persist the rotating refresh and its login identity; Access remains memory-only.
  if (typeof window !== 'undefined') {
    if (value?.refresh_token && value.session_id) window.localStorage.setItem(STORAGE_KEYS.WEB_OAUTH, JSON.stringify({ session_id: value.session_id, refresh_token: value.refresh_token }));
    else window.localStorage.removeItem(STORAGE_KEYS.WEB_OAUTH);
    window.sessionStorage.removeItem(STORAGE_KEYS.WEB_OAUTH);
  }
  credentials = value;
}

function readCredentials(): Credentials | null {
  const saved = storedCredentials();
  if (credentials === undefined) {
    let handoff: Credentials | null = null;
    if (typeof window !== 'undefined') {
      const raw = window.sessionStorage.getItem(STORAGE_KEYS.WEB_OAUTH);
      try { if (raw) handoff = credentialDto.parse(JSON.parse(raw)); } catch { /* Malformed handoff requires normal login. */ }
      window.sessionStorage.removeItem(STORAGE_KEYS.WEB_OAUTH);
    }
    // Consume the callback's one-time Access handoff only for the current login.
    credentials = saved ? { ...(handoff?.session_id === saved.session_id && handoff.refresh_token === saved.refresh_token ? handoff : {}), ...saved }
      : handoff && (!handoff.session_id || !handoff.refresh_token) ? handoff : null;
    return credentials;
  }
  if (saved && credentials?.session_id === saved.session_id) {
    credentials = { ...credentials, refresh_token: saved.refresh_token };
  } else if (saved || credentials?.session_id && credentials.refresh_token) {
    generation = {}; readIdentity = {}; currentSession = null;
    credentials = saved;
    // Notify after the caller establishes its read identity; restore must not re-enter this read.
    queueMicrotask(() => changed(saved !== null));
  }
  return credentials;
}

function withCredentialLock<T>(operation: () => Promise<T>): Promise<T> {
  const locks = typeof window === 'undefined' ? undefined : window.navigator?.locks;
  if (!locks) return Promise.reject(new BrowserSessionError(503, 'Unable to safely restore your session in this browser.'));
  return locks.request(STORAGE_KEYS.WEB_OAUTH, operation);
}

function stillStored(value: Credentials): boolean {
  const saved = storedCredentials();
  return saved?.session_id === value.session_id && saved?.refresh_token === value.refresh_token;
}

export function clearBrowserSession(): void {
  if (nativeHost()) return cookieSession.clearBrowserSession();
  generation = {}; readIdentity = {}; currentSession = null;
  saveCredentials(null); changed();
}

// Historical callers use this value as an account/read scope. Web never sends it as CSRF or OAuth.
export function getBrowserCsrfToken(): string | null { return nativeHost() ? cookieSession.getBrowserCsrfToken() : currentSession?.csrf_token ?? null; }
export function isBrowserSessionCurrent(session: BrowserSession | null): boolean { return nativeHost() ? cookieSession.isBrowserSessionCurrent(session) : currentSession === session; }

export function browserRequestHeaders(extra: Record<string, string> = {}, override?: string | null): Record<string, string> {
  if (nativeHost()) return cookieSession.browserRequestHeaders(extra, override);
  const headers = { ...extra };
  for (const key of Object.keys(headers)) if (/^(?:authorization|cookie|x-ink-csrf)$/i.test(key)) delete headers[key];
  if (override !== undefined && override !== getBrowserCsrfToken()) throw new BrowserSessionError(401, 'Please log in again.');
  const value = readCredentials()?.access_token;
  if (value) headers.Authorization = 'Bearer ' + value;
  return headers;
}

export async function ensureBrowserAccessToken(transport: typeof fetch = fetch, force = false): Promise<string | null> {
  if (logoutFlight) throw new BrowserSessionError(401, 'Please log in again.');
  const value = readCredentials();
  if (!value) return null;
  if (!force && value.session_id && value.access_token && (value.expires_at ?? 0) > Date.now()) return value.access_token;
  if (!value.refresh_token) { clearBrowserSession(); return null; }
  if (refreshFlight) return refreshFlight;
  const pending = withCredentialLock(async () => {
    // A different tab may have rotated or revoked while this tab waited for the lock.
    let latest = readCredentials();
    if (!latest) return null;
    if (!latest.session_id) {
      latest = { ...latest, session_id: crypto.randomUUID() };
      saveCredentials(latest);
    }
    if (!force && latest.access_token && (latest.expires_at ?? 0) > Date.now()) return latest.access_token;
    if (!latest.refresh_token) { clearBrowserSession(); return null; }
    const identity = generation;
    let response: Response;
    try { response = await transport('/auth/refresh', { method: 'POST', credentials: 'omit', cache: 'no-store', redirect: 'error',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ refresh_token: latest.refresh_token }) }); }
    catch { throw new BrowserSessionError(503, 'Unable to renew your session. Please try again.'); }
    if (identity !== generation || !stillStored(latest)) return null;
    if (response.status === 401) { clearBrowserSession(); return null; }
    if (!response.ok) throw new BrowserSessionError(response.status, 'Unable to renew your session. Please try again.');
    const parsed = refreshedDto.safeParse(await response.json().catch(() => null));
    if (identity !== generation || !stillStored(latest)) return null;
    if (!parsed.success || parsed.data.expires_at <= Date.now()) throw new BrowserSessionError(503, 'Unable to renew your session. Please try again.');
    saveCredentials({ ...parsed.data, session_id: latest.session_id });
    return parsed.data.access_token;
  });
  refreshFlight = pending;
  try { return await pending; } finally { if (refreshFlight === pending) refreshFlight = undefined; }
}

export async function loadBrowserSession(transport: typeof fetch = fetch, signal?: AbortSignal): Promise<BrowserSession | null> {
  if (nativeHost()) return cookieSession.loadBrowserSession(transport, signal);
  if (signal?.aborted || logoutFlight) return null;
  readCredentials();
  const identity = {}; readIdentity = identity;
  const isCurrent = () => {
    if (signal?.aborted || logoutFlight) return false;
    // Storage events may still be queued when a profile response arrives.
    readCredentials();
    return readIdentity === identity;
  };
  try {
    const access = await untilAborted(ensureBrowserAccessToken(transport), signal);
    if (!isCurrent() || !access) return null;
    const response = await transport('/auth/session', { credentials: 'omit', cache: 'no-store', redirect: 'error', signal, headers: { Authorization: 'Bearer ' + access } });
    if (!isCurrent()) return null;
    if (response.status === 401) { clearBrowserSession(); return null; }
    if (!response.ok) throw new BrowserSessionError(response.status, 'Unable to check your session. Please try again.');
    const parsed = userDto.safeParse(await response.json().catch(() => null));
    if (!isCurrent()) return null;
    if (!parsed.success) throw new BrowserSessionError(503, 'Unable to check your session. Please try again.');
    // Keep the account scope stable across token rotation and same-account profile reloads.
    const scope = currentSession?.user.id === parsed.data.user.id ? currentSession.csrf_token : crypto.randomUUID();
    currentSession = Object.freeze({ user: Object.freeze(parsed.data.user), csrf_token: scope });
    return currentSession;
  } catch (error) {
    if (!isCurrent()) return null;
    throw error instanceof BrowserSessionError ? error : new BrowserSessionError(503, 'Unable to check your session. Please try again.');
  }
}

export async function revokeBrowserSession(transport: typeof fetch = fetch): Promise<void> {
  if (nativeHost()) return cookieSession.revokeBrowserSession(transport);
  if (logoutFlight) return logoutFlight;
  readIdentity = {};
  const pending = (async () => {
    // Rotation finishes before revocation selects the latest refresh credential.
    if (refreshFlight) await refreshFlight;
    await withCredentialLock(async () => {
      let value = readCredentials();
      if (value?.refresh_token && !value.session_id) {
        value = { ...value, session_id: crypto.randomUUID() };
        saveCredentials(value);
      }
      if (value?.refresh_token) {
        let response: Response;
        try { response = await transport('/auth/logout', { method: 'POST', credentials: 'omit', cache: 'no-store', redirect: 'error',
          headers: { 'content-type': 'application/json' }, body: JSON.stringify({ refresh_token: value.refresh_token }) }); }
        catch { throw new BrowserSessionError(503, 'Unable to log out. Please try again.'); }
        const body = await response.json().catch(() => null);
        if (!response.ok || !z.strictObject({ success: z.literal(true) }).safeParse(body).success) throw new BrowserSessionError(response.status, 'Unable to log out. Please try again.');
      }
      clearBrowserSession();
    });
  })();
  logoutFlight = pending;
  try { await pending; } finally { if (logoutFlight === pending) logoutFlight = undefined; }
}

export function isProtectedBrowserUrl(input: RequestInfo | URL, origin = typeof window === 'undefined' ? undefined : window.location.origin): boolean {
  if (!origin) return false;
  try {
    const url = new URL(input instanceof Request ? input.url : String(input), origin);
    const publicApi = ['/api/health', '/api/login', '/api/register'].includes(url.pathname) || url.pathname.startsWith('/api/public/');
    return url.origin === origin && !url.username && !url.password && !publicApi && (url.pathname.startsWith('/api/') || ['/auth/session', '/auth/me'].includes(url.pathname));
  } catch { return false; }
}

export function createBrowserBearerFetch(transport: typeof fetch, origin: string): typeof fetch {
  return async (input, init) => {
    if (!isProtectedBrowserUrl(input, origin)) return transport(input, init);
    const source = input instanceof Request ? input : undefined;
    const signal = init?.signal ?? source?.signal;
    signal?.throwIfAborted();
    let access = await untilAborted(ensureBrowserAccessToken(transport), signal);
    signal?.throwIfAborted();
    if (!access) throw new BrowserSessionError(401, 'Please log in again.');
    const send = () => {
      const headers = new Headers(init?.headers ?? source?.headers);
      for (const name of ['authorization', 'cookie', 'x-ink-csrf']) headers.delete(name);
      if (access) headers.set('authorization', 'Bearer ' + access);
      return transport(input, { ...init, headers, credentials: 'omit', redirect: 'error' });
    };
    const response = await send();
    if (response.status !== 401 || !access || logoutFlight || signal?.aborted) return response;
    const latest = readCredentials()?.access_token;
    access = latest !== access ? latest ?? null : await untilAborted(ensureBrowserAccessToken(transport, true), signal);
    signal?.throwIfAborted();
    const method = (init?.method ?? source?.method ?? 'GET').toUpperCase();
    let replay = ['GET', 'HEAD'].includes(method);
    // Preserve the existing definite pre-create Notion rejection contract with its original bytes/key.
    if (!replay && method === 'POST' && typeof init?.body === 'string'
      && new URL(source?.url ?? String(input), origin).pathname === '/api/reflections/tasks') {
      try {
        const inputBody = JSON.parse(init.body);
        const detail = (await response.clone().json())?.detail;
        replay = detail?.error_code === 'ACCESS_TOKEN_REQUIRED' && detail.outcome_unknown === false
          && detail.creation_committed !== true && detail.task_id === undefined
          && typeof inputBody?.request_key === 'string' && inputBody.request_key.length > 0
          && inputBody.analysis_content?.include_notion === true;
      } catch { /* Other responses retain their original explicit recovery contract. */ }
    }
    if (!access || !replay) return response;
    await response.body?.cancel();
    return send();
  };
}

export function installBrowserBearerFetch(): void {
  if (typeof window === 'undefined' || nativeHost()) return;
  const owner = globalThis as typeof globalThis & { __inkWebBearerFetch?: typeof fetch };
  if (owner.__inkWebBearerFetch) return;
  window.addEventListener('storage', event => { if (event.key === null || event.key === STORAGE_KEYS.WEB_OAUTH) readCredentials(); });
  window.addEventListener('pageshow', () => { readCredentials(); });
  owner.__inkWebBearerFetch = createBrowserBearerFetch(globalThis.fetch.bind(globalThis), window.location.origin);
  globalThis.fetch = owner.__inkWebBearerFetch;
}
