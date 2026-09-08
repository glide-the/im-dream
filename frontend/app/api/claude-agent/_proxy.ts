// [Input] Same-origin Claude Agent HTTP/SSE requests and the server-owned Python backend origin.
// [Output] A cache-free, abort-aware streaming proxy that forwards response bodies without buffering.
// [Pos] Private implementation behind the Claude Agent Next Route Handler; Python remains the API owner.
// [Sync] 2026-09-07: isolate proxy logic so route.ts exports only Next-supported route fields.

const BACKEND_ORIGIN_KEYS = ['INK_BACKEND_INTERNAL_URL', 'BACKEND_URL'] as const;

const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'content-length',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

function backendOrigin(): URL | null {
  const configured = BACKEND_ORIGIN_KEYS
    .map((key) => process.env[key]?.trim())
    .find(Boolean);
  if (!configured) return null;

  try {
    const origin = new URL(configured);
    if (origin.protocol !== 'http:' && origin.protocol !== 'https:') return null;
    return origin;
  } catch {
    return null;
  }
}

function unavailable(status: 502 | 503, message: string): Response {
  return new Response(`${message}\n`, {
    status,
    headers: {
      'cache-control': 'no-store',
      'content-type': 'text/plain; charset=utf-8',
    },
  });
}

function forwardRequestHeaders(request: Request): Headers {
  const headers = new Headers(request.headers);
  for (const name of HOP_BY_HOP_HEADERS) headers.delete(name);
  headers.delete('host');
  // Node fetch decodes compressed upstream bodies. Ask Python for identity so
  // the returned body and response metadata can never disagree.
  headers.set('accept-encoding', 'identity');
  return headers;
}

function forwardResponseHeaders(upstream: Response): Headers {
  const headers = new Headers();
  for (const [name, value] of upstream.headers) {
    const normalized = name.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(normalized) || normalized === 'content-encoding') continue;
    headers.append(name, value);
  }
  const contentType = headers.get('content-type')?.toLowerCase() ?? '';
  if (contentType.startsWith('text/event-stream')) {
    headers.set('cache-control', 'no-cache, no-transform');
    headers.set('x-accel-buffering', 'no');
  } else if (!headers.has('cache-control')) {
    headers.set('cache-control', 'no-store');
  }
  return headers;
}

export async function proxyClaudeAgentRequest(request: Request): Promise<Response> {
  const origin = backendOrigin();
  if (!origin) return unavailable(503, 'Claude Agent backend is not configured.');

  const incoming = new URL(request.url);
  if (
    incoming.pathname !== '/api/claude-agent'
    && !incoming.pathname.startsWith('/api/claude-agent/')
  ) {
    return unavailable(502, 'Claude Agent proxy received an invalid path.');
  }

  const upstreamUrl = new URL(`${incoming.pathname}${incoming.search}`, origin);
  const method = request.method.toUpperCase();
  const hasBody = method !== 'GET' && method !== 'HEAD' && request.body !== null;
  const init: RequestInit & { duplex?: 'half' } = {
    method,
    headers: forwardRequestHeaders(request),
    cache: 'no-store',
    redirect: 'manual',
    signal: request.signal,
  };
  if (hasBody) {
    init.body = request.body;
    init.duplex = 'half';
  }

  try {
    const upstream = await fetch(upstreamUrl, init);
    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: forwardResponseHeaders(upstream),
    });
  } catch {
    return unavailable(502, 'Claude Agent backend is unavailable.');
  }
}
