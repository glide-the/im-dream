// [Input] Same-origin JSON refresh credential from the current Web tab.
// [Output] Admin OAuth refresh grant result with no session cookies.
// [Pos] Web OAuth renewal adapter; no token authority or business data.
import { bffFailure, configuredBffHandlers } from '../../api/_auth/handlers';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function POST(request: Request): Promise<Response> {
  try { return await configuredBffHandlers(request).refresh(request); } catch (error) { return bffFailure(error); }
}
