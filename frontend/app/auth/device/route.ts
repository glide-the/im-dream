// [Input] Dream legacy/public device-authorization entry and optional user_code.
// [Output] Redirect to the configured Admin device UI, which owns review/approve/deny.
// [Pos] Next device product entry; no Dream device store or token authority.
// [Sync] 2026-09-14: preserve the device entry through the sole Admin authorization owner.
import { configuredBffHandlers, bffFailure } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request: Request) {
  try { return await configuredBffHandlers().device(request); } catch (error) { return bffFailure(error); }
}
