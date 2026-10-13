// [Input] A validated API request, explicit server-owned authorization and backend origin.
// [Output] Unbuffered abort-aware HTTP/SSE forwarding with credential/header isolation.
// [Pos] Shared Next-to-Python transport extracted from the existing Claude Agent proxy.
// [Sync] 2026-09-14: preserve stream/body behavior while removing ambient browser/server credentials.
// [Sync] 2026-10-13: source preparation may wait past the fetch header deadline; preserve caller cancellation.
// [Sync] 2026-10-13: sparse Reflections events wait for the task/caller lifetime instead of a response-body idle deadline.
import { Agent, type Dispatcher } from 'undici';

// A finite mounted-page read completes before task creation sends response headers.
// It retains upstream connection/body limits and the original caller AbortSignal.
let reflectionPreparationDispatcher: Agent | undefined;
let reflectionEventDispatcher: Agent | undefined;
const REFLECTION_EVENT_PATH = /^\/api\/reflections\/tasks\/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\/events$/i;

const BACKEND_ORIGIN_KEYS = ['INK_BACKEND_INTERNAL_URL', 'BACKEND_URL'] as const;
const HOP_BY_HOP_HEADERS = new Set([
  'connection', 'content-length', 'keep-alive', 'proxy-authenticate',
  'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade',
]);

export function configuredBackendOrigin(environment: NodeJS.ProcessEnv = process.env): URL | null {
  const configured = BACKEND_ORIGIN_KEYS.map(key => environment[key]?.trim()).find(Boolean);
  if (!configured) return null;
  try {
    const origin = new URL(configured);
    if (!['http:', 'https:'].includes(origin.protocol) || origin.username || origin.password
      || origin.pathname !== '/' || origin.search || origin.hash) return null;
    return origin;
  } catch { return null; }
}

function privateHeader(name: string): boolean {
  return ['cookie', 'set-cookie', 'authorization', 'x-new-access-token', 'forwarded', 'host'].includes(name)
    || /^(?:x-ink-|x-admin-|x-auth-|x-user-|x-forwarded-|x-real-ip$|true-client-ip$)/.test(name);
}

export function forwardRequestHeaders(request: Request, authorization: string): Headers {
  const headers = new Headers();
  const connectionHeaders = new Set((request.headers.get('connection') ?? '').toLowerCase().split(',').map(name => name.trim()));
  for (const [name, value] of request.headers) {
    if (!HOP_BY_HOP_HEADERS.has(name) && !connectionHeaders.has(name) && !privateHeader(name)) headers.set(name, value);
  }
  headers.set('authorization', authorization);
  // Native fetch decodes upstream compression; identity keeps body and metadata aligned.
  headers.set('accept-encoding', 'identity');
  return headers;
}

function forwardResponseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  const connectionHeaders = new Set((upstream.headers.get('connection') ?? '').toLowerCase().split(',').map(name => name.trim()));
  for (const [name, value] of upstream.headers) {
    if (HOP_BY_HOP_HEADERS.has(name) || connectionHeaders.has(name) || privateHeader(name) || name === 'content-encoding') continue;
    headers.append(name, value);
  }
  if (headers.get('content-type')?.toLowerCase().startsWith('text/event-stream')) {
    headers.set('cache-control', 'no-cache, no-transform');
    headers.set('x-accel-buffering', 'no');
  } else { headers.set('cache-control', 'no-store'); }
  return headers;
}

export async function forwardBackendRequest(request: Request, origin: URL, authorization: string, transport: typeof fetch = fetch): Promise<Response> {
  const incoming = new URL(request.url);
  const upstreamUrl = new URL(incoming.pathname + incoming.search, origin);
  const method = request.method.toUpperCase();
  const init: RequestInit & { duplex?: 'half'; dispatcher?: Dispatcher } = {
    method, headers: forwardRequestHeaders(request, authorization), cache: 'no-store',
    redirect: 'manual', signal: request.signal,
  };
  if (method === 'POST' && incoming.pathname === '/api/reflections/tasks') {
    reflectionPreparationDispatcher ??= new Agent({ headersTimeout: 0 });
    init.dispatcher = reflectionPreparationDispatcher;
  } else if (method === 'GET' && REFLECTION_EVENT_PATH.test(incoming.pathname)) {
    reflectionEventDispatcher ??= new Agent({ bodyTimeout: 0 });
    init.dispatcher = reflectionEventDispatcher;
  }
  if (method !== 'GET' && method !== 'HEAD' && request.body !== null) {
    init.body = request.body;
    init.duplex = 'half';
  }
  const upstream = await transport(upstreamUrl, init);
  return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: forwardResponseHeaders(upstream) });
}
