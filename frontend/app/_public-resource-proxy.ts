// [Input] A fixed public crawler-resource path and the server-owned backend origin.
// [Output] A cache-free runtime proxy response that preserves the Python-owned body and safe metadata.
// [Pos] Private App Router helper; it owns no public route or crawler content.
// [Sync] 2026-09-05: keep dynamic crawler resources backend-owned when the container injects its backend origin at runtime.

const BACKEND_ORIGIN_KEYS = ['INK_BACKEND_INTERNAL_URL', 'BACKEND_URL'] as const;

type PublicResourcePath = '/robots.txt' | '/sitemap.xml' | '/llms.txt';

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

function unavailable(status: 502 | 503, message: string) {
  return new Response(`${message}\n`, {
    status,
    headers: {
      'cache-control': 'no-store',
      'content-type': 'text/plain; charset=utf-8',
    },
  });
}

export async function proxyPublicResource(
  resourcePath: PublicResourcePath,
  request: Request,
) {
  const origin = backendOrigin();
  if (!origin) {
    return unavailable(503, 'Public resource backend is not configured.');
  }

  const upstreamUrl = new URL(resourcePath, origin);
  try {
    const upstream = await fetch(upstreamUrl, {
      cache: 'no-store',
      headers: {
        accept: request.headers.get('accept') ?? '*/*',
        'user-agent': request.headers.get('user-agent') ?? 'ink-memory-web',
      },
    });
    const headers = new Headers({ 'cache-control': 'no-store' });
    for (const name of ['content-type', 'etag', 'last-modified'] as const) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers });
  } catch {
    return unavailable(502, 'Public resource backend is unavailable.');
  }
}
