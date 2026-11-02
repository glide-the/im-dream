// [Input] Original manual Admin JSON requests and ordinary server-owned HTTP configuration.
// [Output] Original fetch Responses using the App's bounded, cancellable URLSession transport.
// [Pos] iOS Next backchannel adapter; local ASGI/SSE, Gateway and browser login retain their transports.
// [Sync] 2026-10-31: correlate bounded authentication reads with native queue/network/callback phases; payloads stay private.
// [Sync] 2026-11-01: pass caller TimeoutError classification through cancellation so failed pools retire without replaying the request.
import { randomUUID } from 'node:crypto';

export function installIOSAdminHTTP(environment = process.env, binding = process._linkedBinding('ink_dream_process')) {
  const origin = environment.INK_ADMIN_DREAM_TRANSPORT_BASE_URL || environment.INK_ADMIN_DREAM_BASE_URL;
  const timeoutSeconds = Number(environment.INK_ADMIN_DREAM_TIMEOUT_SECONDS ?? '10');
  const maxResponseBytes = Number(environment.INK_ADMIN_DREAM_MAX_RESPONSE_BYTES ?? '1048576');
  if (!origin || !Number.isFinite(timeoutSeconds) || timeoutSeconds <= 0 || !Number.isSafeInteger(maxResponseBytes) || maxResponseBytes < 1
      || typeof binding.adminHTTP !== 'function' || typeof binding.cancelAdminHTTP !== 'function') throw new Error('IOS_ADMIN_HTTP_CONFIGURATION_INVALID');
  const selected = new URL(origin);
  if (selected.origin !== origin || selected.username || selected.password || selected.search || selected.hash) throw new Error('IOS_ADMIN_HTTP_CONFIGURATION_INVALID');
  const original = globalThis.fetch;
  const NativeRequest = globalThis.Request;
  globalThis.fetch = async (input, init) => {
    const raw = input instanceof NativeRequest ? input.url : String(input);
    let url;
    try { url = new URL(raw); } catch { return original(input, init); }
    if (url.origin !== origin || !(url.pathname.startsWith('/api/internal/dream/v1/')
      || ['/api/auth/oauth2/token', '/api/auth/jwks'].includes(url.pathname))) return original(input, init);
    if ((init?.redirect ?? (input instanceof NativeRequest ? input.redirect : 'follow')) !== 'manual') return original(input, init);
    const request = new NativeRequest(input, init);
    const operations = new Map([
      ['/api/auth/oauth2/token', 'service-token'],
      ['/api/auth/jwks', 'jwks'],
      ['/api/internal/dream/v1/capabilities', 'capabilities'],
      ['/api/internal/dream/v1/browser-sessions/resolve', 'session-resolve'],
      ['/api/internal/dream/v1/operations/user-profile.current', 'user-profile'],
    ]);
    const operation = operations.get(url.pathname);
    const traceId = operation ? randomUUID() : undefined;
    const requestId = request.headers.get('x-request-id');
    const started = performance.now();
    const observations = [];
    const report = (phase, fields = {}, emit = false) => {
      if (!traceId) return;
      try {
        observations.push('IOS_ADMIN_HTTP ' + JSON.stringify({traceId, operation, phase,
        ...(requestId && /^[A-Za-z0-9_-]{1,160}$/.test(requestId) ? {requestId} : {}),
        timestampMs: Date.now(), elapsedMs: Math.round(performance.now() - started), ...fields}) + '\n');
        if (emit) process.stderr.write(observations.splice(0).join(''));
      }
      catch { /* Diagnostics preserve the original request. */ }
    };
    report('selected-native');
    const signal = request.signal;
    signal.throwIfAborted();
    const body = request.body === null ? null : Buffer.from(await request.arrayBuffer()).toString('base64');
    signal.throwIfAborted();
    const packet = JSON.stringify({url: request.url, method: request.method, headers: Object.fromEntries(request.headers),
      bodyBase64: body, timeoutSeconds, maxResponseBytes, ...(traceId ? {traceId} : {})});
    report('serialized');
    return new Promise((resolve, reject) => {
      let handle, completed = false, recovered = false;
      const cancel = () => { if (!completed && handle) { report('cancel'); binding.cancelAdminHTTP(handle, signal.reason?.name === 'TimeoutError'); } };
      const finish = (error, response) => {
        if (completed) return;
        completed = true; signal.removeEventListener('abort', cancel);
        report('next-result', {failed: Boolean(error), ...(recovered ? {recoveryCount: 1} : {}), ...(response ? {status: response.status} : {})}, Boolean(error) || recovered);
        error ? reject(error) : resolve(response);
      };
      try {
        handle = binding.adminHTTP(packet, rawResponse => {
          report('native-callback');
          try {
            if (signal.aborted) { finish(signal.reason); return; }
            const result = JSON.parse(rawResponse);
            recovered = result.recoveryCount === 1;
            if (['timeout', 'transport', 'cancelled', 'configuration'].includes(result.error)) report('native-error', {code: result.error});
            if (result.ok !== true || !Number.isInteger(result.status) || result.status < 100 || result.status > 599
                || typeof result.bodyBase64 !== 'string' || !result.headers || typeof result.headers !== 'object' || Array.isArray(result.headers)
                || Object.values(result.headers).some(value => typeof value !== 'string')) {
              throw new TypeError('IOS_ADMIN_HTTP_FAILED');
            }
            const bytes = Buffer.from(result.bodyBase64, 'base64');
            if (bytes.toString('base64') !== result.bodyBase64) throw new TypeError('IOS_ADMIN_HTTP_RESPONSE_INVALID');
            const response = new Response([204, 205, 304].includes(result.status) ? null : bytes,
              {status: result.status, headers: result.headers});
            Object.defineProperty(response, 'url', {value: request.url});
            finish(null, response);
          } catch (error) { finish(error); }
        });
        report('enqueued');
        signal.addEventListener('abort', cancel, {once: true});
        if (signal.aborted) cancel();
      } catch (error) { finish(error); }
    });
  };
}
