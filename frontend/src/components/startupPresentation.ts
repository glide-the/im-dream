// [Input] Product requirement for a one-second entry animation on each app opening.
// [Output] Shared presentation duration and one complete breathing cycle.
// [Pos] Startup UI timing policy; independent of backend readiness and session checks.
// [Sync] 2026-11-03: keep the presentation hold and breathing cycle aligned at one second.
export const STARTUP_PRESENTATION_DURATION_MS = 1_000;
export const STARTUP_BREATH_HALF_CYCLE_MS = STARTUP_PRESENTATION_DURATION_MS / 2;
