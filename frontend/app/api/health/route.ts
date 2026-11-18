// [Input] Next process liveness request.
// [Output] Cache-free health response without dependency or secret details.
// [Pos] Release/rollback health boundary.
// [Sync] 2026-09-05: move the health receipt to the canonical root App Router.
// [Sync] 2026-11-19: trace each health request in the Node route handler.
import { tracedOptions, withApiTrace } from '../_trace';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const route = '/api/health';
export const GET = withApiTrace(route, () => {
  return Response.json(
    { status: 'ok', service: 'ink-memory-web', productionAppsEffective: false },
    { headers: { 'cache-control': 'no-store' } },
  );
});
export const OPTIONS = tracedOptions(route, ['GET']);
