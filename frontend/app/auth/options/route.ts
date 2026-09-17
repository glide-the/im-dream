// [Input] Same-origin Dream browser requesting its configured authentication form targets.
// [Output] Exact Admin password/Google action URLs without client secret or token material.
// [Pos] Public login-card configuration; server env remains the only authority for Admin topology.
// [Sync] 2026-09-17: support the restored Dream form without hard-coded Admin hosts.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request): Promise<Response> {
  try { return await configuredBffHandlers().options(request); }
  catch (error) { return bffFailure(error); }
}
