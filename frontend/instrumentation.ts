// [Sync] 2026-11-19: resolve the private trace settings when the ordinary Next Node runtime starts.
// [Input] Next's Node startup hook and opt-in private trace settings.
// [Output] One initialized Web BFF probe per configured Node process.
// [Pos] Next server bootstrap; API trace handling remains in app/api/_trace.ts.
export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { startTracing } = await import('./app/api/_trace');
    await startTracing();
  }
}
