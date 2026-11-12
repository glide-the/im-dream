// [Input] Opaque token and server-configured Python origin/HTTP transport bounds.
// [Output] One credential-free, bounded, dynamic public snapshot or closed error status.
// [Pos] Shared server reader for the public page and anonymous Next API route.
import {configuredBackendOrigin} from '../api/_http-proxy';
import {publicShareSnapshot, type PublicShareSnapshot} from '../_dream/api/publicShareSchema';
export const publicShareHeaders = {'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow', 'Referrer-Policy': 'no-referrer'};
type Result = {status: 200; snapshot: PublicShareSnapshot} | {status: 404 | 503};
export async function readPublicShare(token: string, signal?: AbortSignal): Promise<Result> {
  if (!/^[A-Za-z0-9_-]{43}$/.test(token)) return {status: 404};
  const origin = configuredBackendOrigin();
  const timeout = Math.ceil(Number(process.env.INK_ADMIN_DREAM_TIMEOUT_SECONDS ?? '10') * 1_000);
  const maximum = Number(process.env.INK_ADMIN_DREAM_MAX_RESPONSE_BYTES ?? '1048576');
  if (!origin || !Number.isSafeInteger(timeout) || timeout < 1 || timeout > 2_147_483_647 || !Number.isSafeInteger(maximum) || maximum < 1) return {status: 503};
  try {
    const deadline = AbortSignal.timeout(timeout);
    const response = await fetch(new URL('/api/public/shares/' + token, origin), {cache: 'no-store', redirect: 'error', signal: signal ? AbortSignal.any([signal, deadline]) : deadline});
    if (response.status === 404 || response.status === 410) {await response.body?.cancel(); return {status: 404};}
    if (!response.ok || !response.body) {await response.body?.cancel(); return {status: 503};}
    const reader = response.body.getReader(), chunks: Uint8Array[] = []; let bytes = 0;
    try {
      while (true) {
        const next = await reader.read(); if (next.done) break;
        bytes += next.value.byteLength;
        if (bytes > maximum) {await reader.cancel(); return {status: 503};}
        chunks.push(next.value);
      }
    } finally {reader.releaseLock();}
    return {status: 200, snapshot: publicShareSnapshot.parse(JSON.parse(Buffer.concat(chunks).toString('utf8')))};
  } catch {return {status: 503};}
}
