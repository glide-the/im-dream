// [Input] Router-parsed `?run=` deep-link param (Task 5 Step 0 unified query
//         parsing) + the existing actor-scoped GET
//         /api/story-workspace/workflow-runs/{id} read.
// [Output] useRunDeepLink(enabled, runId) → {run, notice, dismissNotice}: a
//          resolved deep-linked run as the initial Dream selection, or a toast
//          notice when the run is missing/foreign (design_004 §4.3).
// [Pos] story-workspace hooks node - Dream page run deep-link seam (Task 4
//       Step 5; Task 5 Step 0 absorbed query parsing into the router)
// [Sync] 2026-08-04: Task 5 Step 0 — the hook no longer reads
//                    window.location.search; the router parses `?run=` via
//                    storyWorkspacePath.ts and passes it in. Route switches
//                    (enabled → false) now clear the run and the notice
//                    (Task 4 review leftover: notice persisted across routes).
//                    Deep links only do initial positioning — the resolved run
//                    never freezes selection (stale-review semantics stay with
//                    design_003).
//         2026-08-04: F-2 fix — the resolve-once cursor moved into
//                    createRunDeepLinkResolveGate and now latches only after a
//                    resolution is applied; an aborted attempt (StrictMode dev
//                    double-effect) reopens the gate so the second setup still
//                    resolves fresh-load `?run=` deep links.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getWorkflowRun,
  type WorkflowRun,
} from '../../api/storyWorkspaceApi';

export type StoryWorkspaceRunDeepLinkResolution =
  | { status: 'none' }
  | { status: 'resolved'; run: WorkflowRun }
  | { status: 'missing'; runId: string };

export interface ResolveRunDeepLinkOptions {
  getRun?: (runId: string) => Promise<WorkflowRun>;
}

/**
 * Resolve a `?run=` deep link against the actor-scoped run read: owned runs
 * resolve as the initial selection (replacing the default); unknown/foreign
 * runs (the backend read is actor-scoped, so both surface as failures) degrade
 * to `missing` so the caller can toast and fall back to the default view.
 */
export async function resolveRunDeepLink(
  runId: string | null,
  options: ResolveRunDeepLinkOptions = {},
): Promise<StoryWorkspaceRunDeepLinkResolution> {
  if (!runId) return { status: 'none' };

  const getRun = options.getRun ?? getWorkflowRun;
  try {
    const run = await getRun(runId);
    return run && run.workflow_run_id
      ? { status: 'resolved', run }
      : { status: 'missing', runId };
  } catch {
    return { status: 'missing', runId };
  }
}

export interface StoryWorkspaceRunDeepLinkState {
  /** The deep-linked run selected as initial context; null = default view. */
  run: WorkflowRun | null;
  /** Toast text when the deep-linked run is missing or not viewable. */
  notice: string | null;
  /** The actor-scoped read rejected this exact run; router must remove its query. */
  missingRunId: string | null;
  dismissNotice: () => void;
}

export type StoryWorkspaceRunDeepLinkSnapshot = Pick<
  StoryWorkspaceRunDeepLinkState,
  'run' | 'notice' | 'missingRunId'
>;

/**
 * Resolve-once gate for the deep-link effect (F-2 fix, 2026-08-04). The
 * cursor is latched only after a resolution is *applied*; an aborted attempt
 * (React StrictMode dev double-effect: setup → cleanup → setup) leaves the
 * gate open so the second setup can still resolve instead of early-returning
 * on a cursor that was latched before the async read finished.
 */
export interface RunDeepLinkResolveGate {
  /** true when a resolve attempt should start for runId. */
  begin(runId: string): boolean;
  /** Latch runId as resolved (call only when the attempt is applied). */
  markResolved(runId: string): void;
  /** Abort the in-flight attempt (effect cleanup); the gate stays open. */
  abort(): void;
  /** Clear both slots (route switch / deep link disabled). */
  reset(): void;
}

export function createRunDeepLinkResolveGate(): RunDeepLinkResolveGate {
  let inFlightKey: string | null = null;
  let resolvedKey: string | null = null;
  return {
    begin(runId) {
      if (inFlightKey === runId || resolvedKey === runId) return false;
      inFlightKey = runId;
      return true;
    },
    markResolved(runId) {
      if (inFlightKey !== runId) return;
      resolvedKey = runId;
      inFlightKey = null;
    },
    abort() {
      inFlightKey = null;
    },
    reset() {
      inFlightKey = null;
      resolvedKey = null;
    },
  };
}

export type StoryWorkspaceRunDeepLinkEffectPlan =
  | { kind: 'clear'; state: StoryWorkspaceRunDeepLinkSnapshot }
  | { kind: 'idle' }
  | { kind: 'resolve'; runId: string };

export function storyWorkspacePlanRunDeepLinkEffect(
  enabled: boolean,
  runId: string | null,
  gate: RunDeepLinkResolveGate,
): StoryWorkspaceRunDeepLinkEffectPlan {
  if (!enabled || !runId) {
    gate.reset();
    return {
      kind: 'clear',
      state: { run: null, notice: null, missingRunId: null },
    };
  }
  return gate.begin(runId)
    ? { kind: 'resolve', runId }
    : { kind: 'idle' };
}

/**
 * Resolve the Dream page `?run=` deep link once per distinct run id (initial
 * positioning only — later selection changes are not frozen to this run).
 * `enabled` gates resolution to routes that surface the Dream review flow;
 * leaving such a route, or removing its run id, clears the resolved run,
 * notice, missing id and resolve gate so the default view is restored and the
 * same run can be resolved again later.
 */
export function useRunDeepLink(
  enabled: boolean,
  runId: string | null,
): StoryWorkspaceRunDeepLinkState {
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [missingRunId, setMissingRunId] = useState<string | null>(null);
  const gateRef = useRef<RunDeepLinkResolveGate | null>(null);
  if (gateRef.current === null) {
    gateRef.current = createRunDeepLinkResolveGate();
  }
  const gate = gateRef.current;

  useEffect(() => {
    const plan = storyWorkspacePlanRunDeepLinkEffect(enabled, runId, gate);
    if (plan.kind === 'clear') {
      setRun(plan.state.run);
      setNotice(plan.state.notice);
      setMissingRunId(plan.state.missingRunId);
      return;
    }
    if (plan.kind === 'idle') return;

    setRun(null);
    setMissingRunId(null);

    let cancelled = false;
    void resolveRunDeepLink(plan.runId).then((resolution) => {
      if (cancelled) return;
      gate.markResolved(plan.runId);
      if (resolution.status === 'resolved') {
        setRun(resolution.run);
        setNotice(null);
        setMissingRunId(null);
      } else if (resolution.status === 'missing') {
        setRun(null);
        setMissingRunId(resolution.runId);
        setNotice(`链接指向的运行 ${resolution.runId} 不存在或无权查看，已回退到默认视图。`);
      }
    });
    return () => {
      cancelled = true;
      // StrictMode dev double-effect: the aborted first attempt must not keep
      // the gate closed, or the second setup would early-return (F-2).
      gate.abort();
    };
  }, [enabled, runId, gate]);

  const dismissNotice = useCallback(() => setNotice(null), []);

  return { run, notice, missingRunId, dismissNotice };
}
