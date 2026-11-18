// [Input] Explicit server tracing switch and the existing BFF/fetch boundaries.
// [Output] Lazy optional metadata tracing without changing request or stream results.
// [Pos] Server-only startup and request bridge; disabled processes skip SDK import.
// [Sync] 2026-11-19: register the web probe through the Next startup hook.
// [Sync] 2026-11-19: load the private Web trace settings from ordinary Next startup.
// [Sync] 2026-11-19: share route and preflight tracing across local API handlers.
import { openSync, closeSync, fstatSync, readFileSync, constants } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { parseEnv } from 'node:util';

type Runtime = typeof import('./_trace-runtime.ts');
let runtime: Promise<Runtime | undefined> | undefined;
function privateWebSettings(): Readonly<Record<string, string | undefined>> {
  // An explicit process switch owns the full deployment configuration.
  if (process.env.INK_TRACE_ENABLED !== undefined) return process.env;
  const path = process.env.INK_DREAM_WEB_TRACE_ENV_FILE || join(homedir(), '.config', 'ink-memory', 'dream-web-trace.env');
  let fd: number | undefined;
  try {
    fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    const stat = fstatSync(fd);
    if (!stat.isFile() || (stat.mode & 0o077) || stat.size > 16384) throw Error('private settings');
    return parseEnv(readFileSync(fd, 'utf8'));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') console.warn('Private Web tracing configuration unavailable');
    return {};
  } finally {
    if (fd !== undefined) closeSync(fd);
  }
}

async function configuredRuntime() {
  runtime ??= (async () => {
    const settings = privateWebSettings();
    if (settings.INK_TRACE_ENABLED !== 'true') return undefined;
    const module = await import('./_trace-runtime.ts');
    module.configureTracing(settings);
    return module;
  })().catch(() => { console.warn('Tracing unavailable; continuing without trace export'); return undefined; });
  return runtime;
}
export async function startTracing() {
  const owner = await configuredRuntime();
  owner?.recordStartup();
}
export async function traceApiRequest(request: Request, handler: () => Response | Promise<Response>, route?: string): Promise<Response> {
  const owner = await configuredRuntime();
  return owner ? owner.traceApiRequest(request, handler, route) : handler();
}
export function withApiTrace<Args extends unknown[]>(route: string, handler: (request: Request, ...args: Args) => Response | Promise<Response>) {
  return (request: Request, ...args: Args) => traceApiRequest(request, () => handler(request, ...args), route);
}
export function tracedOptions(route: string, methods: readonly string[]) {
  const allow = [...methods, 'OPTIONS', ...(methods.includes('GET') ? ['HEAD'] : [])].sort().join(', ');
  return withApiTrace(route, () => new Response(null, { status: 204, headers: { allow } }));
}
export async function traceFetch(transport: typeof fetch, input: URL | RequestInfo, init?: RequestInit, privateBackend = false): Promise<Response> {
  const owner = await configuredRuntime();
  return owner ? owner.traceFetch(transport, input, init, privateBackend) : transport(input, init);
}
export async function traceAuthentication<T>(handler: () => Promise<T>): Promise<T> {
  const owner = await configuredRuntime();
  return owner ? owner.traceOperation('bff.authentication', handler) : handler();
}
