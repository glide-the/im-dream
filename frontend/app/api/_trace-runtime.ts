// [Input] Private process OTLP endpoint, service name, queue budget and BFF signing key.
// [Output] W3C parent spans, signed Python handoff and metadata-only batch export.
// [Pos] Dedicated BFF provider; leaves Next/global/preloaded providers untouched.
// [Sync] 2026-11-19: send OTLP HTTP/protobuf and report initialization on Next startup.
// [Sync] 2026-11-19: report Next as its own Web service and identify HTTP dependency targets.
import { AsyncLocalStorage } from 'node:async_hooks';
import { createHmac, randomUUID } from 'node:crypto';
import { ROOT_CONTEXT, trace, SpanKind, SpanStatusCode, type Context, type Span } from '@opentelemetry/api';
import { AlwaysOnSampler, BasicTracerProvider, BatchSpanProcessor, ParentBasedSampler, TraceIdRatioBasedSampler, type SpanExporter } from '@opentelemetry/sdk-trace-base';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-proto';

const contexts = new AsyncLocalStorage<Context>();
let provider: BasicTracerProvider | undefined;
let secret = '';
let pythonService = 'ink-memory-dream-web-python';
let startupRecorded = false;
const probeStarted = Date.now();
const methods = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'CONNECT', 'TRACE']);
function positive(settings: Readonly<Record<string, string | undefined>>, key: string, fallback: number) {
  const value = Number(settings[key] ?? fallback);
  if (!Number.isSafeInteger(value) || value < 1 || value > 2_147_483_647) throw Error('trace budget');
  return value;
}
export function configureTracing(settings: Readonly<Record<string, string | undefined>>) {
  if (provider) return;
  const endpoint = new URL(settings.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT ?? '');
  const configuredName = settings.OTEL_SERVICE_NAME?.trim();
  const name = !configuredName || configuredName === 'ink-memory-dream-web' ? 'ink-memory-dream-web-next' : configuredName;
  pythonService = settings.INK_TRACE_PYTHON_SERVICE_NAME?.trim() || pythonService;
  secret = settings.INK_TRACE_CONTEXT_SECRET ?? '';
  const ratio = Number(settings.OTEL_TRACES_SAMPLER_ARG ?? '0.1');
  const queue = positive(settings, 'OTEL_BSP_MAX_QUEUE_SIZE', 2048);
  const batch = positive(settings, 'OTEL_BSP_MAX_EXPORT_BATCH_SIZE', 512);
  if (!['http:', 'https:'].includes(endpoint.protocol) || endpoint.username || endpoint.password || endpoint.hash
    || !name || Buffer.byteLength(secret) < 32 || !Number.isFinite(ratio) || ratio < 0 || ratio > 1 || batch > queue) throw Error('trace configuration');
  // No global registration or auto-instrumentation: Next and Admin keep their own owners.
  const headers: Record<string, string> = {};
  for (const header of (settings.OTEL_EXPORTER_OTLP_TRACES_HEADERS || settings.OTEL_EXPORTER_OTLP_HEADERS || '').split(',')) {
    const separator = header.indexOf('=');
    if (separator > 0) headers[header.slice(0, separator).trim()] = decodeURIComponent(header.slice(separator + 1).trim());
  }
  const rawExporter = new OTLPTraceExporter({ url: endpoint.href, headers, timeoutMillis: 3000 });
  const exporter: SpanExporter = {
    export(spans, callback) {
      rawExporter.export(spans, result => callback(result.code === 0 ? { code: result.code }
        : { code: result.code, error: new Error('Trace export failed') }));
    },
    shutdown: () => rawExporter.shutdown(),
  };
  const requests = new TraceIdRatioBasedSampler(ratio);
  const startup = new AlwaysOnSampler();
  provider = new BasicTracerProvider({
    resource: resourceFromAttributes({ 'service.name': name, 'service.namespace': 'ink-memory-dream',
      'service.instance.id': randomUUID(), 'ink.dream.platform': 'web',
      ...(settings.INK_TRACE_HOST_NAME?.trim() && { 'host.name': settings.INK_TRACE_HOST_NAME.trim() }) }),
    sampler: new ParentBasedSampler({ root: {
      shouldSample(context, traceId, name) {
        return name === 'dream.startup.web.next' ? startup.shouldSample() : requests.shouldSample(context, traceId);
      },
      toString: () => requests.toString(),
    } }),
    spanLimits: { eventCountLimit: 0, linkCountLimit: 0, attributeCountLimit: 16, attributeValueLengthLimit: 256 },
    spanProcessors: [new BatchSpanProcessor(exporter, {
      maxQueueSize: queue, maxExportBatchSize: batch, scheduledDelayMillis: positive(settings, 'OTEL_BSP_SCHEDULE_DELAY', 5000), exportTimeoutMillis: 3000,
    })],
  });
  process.once('beforeExit', () => { void provider?.shutdown().catch(() => {}); });
}
export function recordStartup() {
  if (startupRecorded || !provider) return;
  startupRecorded = true;
  provider.getTracer('ink-memory-dream-bff').startSpan('dream.startup.web.next', {
    kind: SpanKind.SERVER, startTime: probeStarted,
  }, ROOT_CONTEXT).end();
}
function start(name: string, kind: SpanKind, parent = contexts.getStore() ?? ROOT_CONTEXT) {
  return provider!.getTracer('ink-memory-dream-bff').startSpan(name, { kind }, parent);
}
export async function traceOperation<T>(name: string, handler: () => Promise<T>): Promise<T> {
  if (!provider || !contexts.getStore()) return handler();
  const current = start(name, SpanKind.INTERNAL);
  try { return await contexts.run(trace.setSpan(contexts.getStore()!, current), handler); }
  catch (error) { current.setStatus({ code: SpanStatusCode.ERROR }); throw error; }
  finally { current.end(); }
}
function withBodyLifetime(response: Response, current: Span, finish: () => void): Response {
  if (!response.body) { finish(); return response; }
  const reader = response.body.getReader();
  const body = new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const chunk = await reader.read();
        if (chunk.done) { controller.close(); finish(); } else controller.enqueue(chunk.value);
      } catch (error) { current.setStatus({ code: SpanStatusCode.ERROR }); controller.error(error); finish(); }
    },
    async cancel(reason) { try { await reader.cancel(reason); } finally { finish(); } },
  }, { highWaterMark: 0 });
  return new Response(body, { status: response.status, statusText: response.statusText, headers: response.headers });
}
export async function traceApiRequest(request: Request, handler: () => Promise<Response>): Promise<Response> {
  if (!provider) return handler();
  const method = methods.has(request.method) ? request.method : 'OTHER';
  const reconcile = '/api/decks/defaults/reconcile';
  const route = method === 'POST' && new URL(request.url).pathname === reconcile ? reconcile : '/api/[[...path]]';
  // Public caller headers and ambient Next spans cannot select this root or sampling.
  const current = start(`${method} ${route}`, SpanKind.SERVER, ROOT_CONTEXT);
  current.setAttributes({ 'http.request.method': method, 'http.route': route });
  const identity = current.spanContext();
  const started = performance.now();
  let status = 500;
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    request.signal.removeEventListener('abort', aborted);
    current.setAttribute('http.response.status_code', status);
    current.end();
    console.info(JSON.stringify({ event: 'dream.request', trace_id: identity.traceId, span_id: identity.spanId,
      sampled: identity.traceFlags & 1, method, route, status, duration_ms: performance.now() - started }));
  };
  const aborted = () => { current.setStatus({ code: SpanStatusCode.ERROR }); finish(); };
  request.signal.addEventListener('abort', aborted, { once: true });
  try {
    const response = await contexts.run(trace.setSpan(ROOT_CONTEXT, current), handler);
    status = response.status;
    if (status >= 500) current.setStatus({ code: SpanStatusCode.ERROR });
    const headers = new Headers(response.headers);
    // Python owns its root when handoff verification/configuration is unavailable.
    const downstream = headers.get('x-trace-id');
    headers.set('x-trace-id', identity.traceId);
    headers.set('x-trace-sampled', String(identity.traceFlags & 1));
    headers.set('x-trace-linked', downstream === identity.traceId ? '1' : '0');
    if (request.signal.aborted) aborted();
    return withBodyLifetime(new Response(response.body, { status, statusText: response.statusText, headers }), current, finish);
  } catch (error) { current.setStatus({ code: SpanStatusCode.ERROR }); finish(); throw error; }
}
export async function traceFetch(transport: typeof fetch, input: URL | RequestInfo, init?: RequestInit, privateBackend = false): Promise<Response> {
  if (!provider || !contexts.getStore()) return transport(input, init);
  let url: URL;
  try { url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url); }
  catch { return transport(input, init); }
  const current = start(privateBackend ? 'dream.http' : 'admin.http', SpanKind.CLIENT);
  const identity = current.spanContext();
  const headers = new Headers(init?.headers);
  for (const name of ['traceparent', 'tracestate', 'baggage', 'x-ink-trace-time', 'x-ink-trace-signature']) headers.delete(name);
  const traceparent = `00-${identity.traceId}-${identity.spanId}-${(identity.traceFlags & 1) ? '01' : '00'}`;
  headers.set('traceparent', traceparent);
  const method = (init?.method ?? 'GET').toUpperCase();
  const peerService = privateBackend ? pythonService : 'ink-memory-admin';
  current.setAttributes({ 'http.request.method': methods.has(method) ? method : 'OTHER',
    'server.address': url.hostname, 'server.port': Number(url.port || (url.protocol === 'https:' ? 443 : 80)),
    'server.service.name': peerService, 'peer.service': peerService });
  if (privateBackend) {
    const stamp = String(Math.floor(Date.now() / 1000));
    // ASGI scope.path is decoded. The signature binds method/path, without collecting either URL or query.
    let path = url.pathname;
    try { path = decodeURIComponent(path); } catch { /* Preserve the original transport for malformed public paths. */ }
    const message = [stamp, traceparent, method, path].join('\n');
    headers.set('x-ink-trace-time', stamp);
    headers.set('x-ink-trace-signature', createHmac('sha256', secret).update(message).digest('hex'));
  }
  try {
    const response = await transport(input, { ...init, headers });
    current.setAttribute('http.response.status_code', response.status);
    if (response.status >= 400) current.setStatus({ code: SpanStatusCode.ERROR });
    return withBodyLifetime(response, current, () => current.end());
  } catch (error) { current.setStatus({ code: SpanStatusCode.ERROR }); current.end(); throw error; }
}
