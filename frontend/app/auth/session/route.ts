// [Sync] 2026-11-19: Web authentication uses explicit OAuth credentials while native retains its platform contract.
// [Input] Web OAuth Bearer or native platform-owned handle Cookie.
// [Output] Strict public Web user fields; native responses retain handle-bound CSRF.
// [Pos] Public profile hydration; Bearer uses Admin principal/profile, native uses resolve/profile.
// [Sync] 2026-10-11: select the existing BFF boundary from this request address.
// [Sync] 2026-09-14: preserve canonical IDs as decimal strings in this new session DTO.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request): Promise<Response> {
  try { return await configuredBffHandlers(request).session(request); } catch (error) { return bffFailure(error); }
}
