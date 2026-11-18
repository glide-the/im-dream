// [Input] Explicit server tracing switch and the existing BFF/fetch boundaries.
// [Output] Lazy optional metadata tracing without changing request or stream results.
// [Pos] Server-only bridge; disabled processes never import the OpenTelemetry SDK.
type Runtime = typeof import('./_trace-runtime.ts');
let runtime: Promise<Runtime | undefined> | undefined;
async function configuredRuntime() {
  if (process.env.INK_TRACE_ENABLED !== 'true') return undefined;
  runtime ??= import('./_trace-runtime.ts').then(module => { module.configureTracing(); return module; })
    .catch(() => { console.warn('Tracing unavailable; continuing without trace export'); return undefined; });
  return runtime;
}
export async function traceApiRequest(request: Request, handler: () => Promise<Response>): Promise<Response> {
  const owner = await configuredRuntime();
  return owner ? owner.traceApiRequest(request, handler) : handler();
}
export async function traceFetch(transport: typeof fetch, input: URL | RequestInfo, init?: RequestInit, privateBackend = false): Promise<Response> {
  const owner = await configuredRuntime();
  return owner ? owner.traceFetch(transport, input, init, privateBackend) : transport(input, init);
}
export async function traceAuthentication<T>(handler: () => Promise<T>): Promise<T> {
  const owner = await configuredRuntime();
  return owner ? owner.traceOperation('bff.authentication', handler) : handler();
}
