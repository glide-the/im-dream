// [Input] Browser login entry with a restricted relative return location.
// [Output] Admin code/PKCE authorization redirect and a host-only transaction cookie.
// [Pos] Public same-origin Dream authentication entry; Admin owns password/register/Google.
// [Sync] 2026-09-14: delegate to the sole private BFF handler.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request): Promise<Response> {
  try { return await configuredBffHandlers().start(request); } catch (error) { return bffFailure(error); }
}
