// [Input] Next process liveness request.
// [Output] Cache-free health response without dependency or secret details.
// [Pos] Release/rollback health boundary.
// [Sync] 2026-09-05: move the health receipt to the canonical root App Router.

export const runtime = 'nodejs';

export function GET() {
  return Response.json(
    { status: 'ok', service: 'ink-memory-web', productionAppsEffective: false },
    { headers: { 'cache-control': 'no-store' } },
  );
}
