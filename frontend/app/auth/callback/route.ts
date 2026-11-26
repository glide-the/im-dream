// [Input] Exact registered Admin code callback and the original encrypted login transaction.
// [Output] Web tab credential completion or the native handle callback.
// [Pos] Registered OAuth callback; callback scheme explicitly selects native compatibility.
// [Sync] 2026-11-19: HTTPS/HTTP callbacks use public code/PKCE token exchange and clear legacy handles.
// [Sync] 2026-10-11: select the existing BFF boundary from this request address.
// [Sync] 2026-09-14: delegate to the sole private BFF handler.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
import { BffLoginBoundary } from '../../api/_auth/login-boundary';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request): Promise<Response> {
  try {
    const handlers = configuredBffHandlers(request);
    return /^https?:/.test(BffLoginBoundary.fromRequest(request).callbackUri) ? await handlers.webCallback(request) : await handlers.callback(request);
  } catch (error) { return bffFailure(error); }
}
